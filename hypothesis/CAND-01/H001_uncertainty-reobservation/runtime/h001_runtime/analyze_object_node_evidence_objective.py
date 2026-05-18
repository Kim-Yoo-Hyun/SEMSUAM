import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.object_node_evidence_objective.v1"


PROPERTY_GROUP_BY_QUERY = {
    "plant": "small_or_cluttered",
    "tv_monitor": "wall_mounted_or_planar",
    "bed": "large_repeated_furniture",
    "chair": "large_repeated_furniture",
    "sofa": "large_repeated_furniture",
    "toilet": "standard_furniture_or_fixture",
}


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def box_area_ratio(box: Any, image_area: float = 160.0 * 120.0) -> Optional[float]:
    if not isinstance(box, list) or len(box) != 4:
        return None
    left, top, right, bottom = [safe_float(value) for value in box]
    if left is None or top is None or right is None or bottom is None:
        return None
    return min(1.0, max(0.0, right - left) * max(0.0, bottom - top) / image_area)


def compactness(area_ratio: Optional[float]) -> float:
    if area_ratio is None:
        return 0.0
    if area_ratio <= 0.35:
        return 1.0
    return max(0.0, 1.0 - ((area_ratio - 0.35) / 0.65))


def box_diagonal(box: Any) -> Optional[float]:
    if not isinstance(box, list) or len(box) != 4:
        return None
    left, top, right, bottom = [safe_float(value) for value in box]
    if left is None or top is None or right is None or bottom is None:
        return None
    return math.hypot(max(0.0, right - left), max(0.0, bottom - top))


def projection_proximity(row: Dict[str, Any]) -> float:
    if row.get("projection_status") != "visible":
        return 0.0
    distance = safe_float(row.get("box_center_distance_px"))
    box = row.get("best_box_xyxy")
    if distance is None or box is None:
        return 0.0
    scale = max(18.0, (box_diagonal(box) or 0.0) * 0.35)
    value = math.exp(-distance / scale)
    if row.get("projected_pixel_inside_mask") is True:
        value = 1.0
    elif row.get("projected_pixel_inside_box") is True:
        value = max(value, 0.85)
    return max(0.0, min(1.0, value))


def pairwise_auc(positives: List[float], negatives: List[float]) -> Optional[float]:
    if not positives or not negatives:
        return None
    wins = 0.0
    pairs = 0
    for pos in positives:
        for neg in negatives:
            pairs += 1
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / pairs if pairs else None


def labels_for_policy(rows: List[Dict[str, Any]], policy: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is not None and candidate_id is not None:
            out[(str(episode_key), str(candidate_id))] = row
    return out


def semantic_rank_prior(rank: Any, count: int) -> float:
    try:
        rank_int = int(rank)
    except (TypeError, ValueError):
        return 0.0
    if count <= 1:
        return 1.0
    return max(0.0, min(1.0, 1.0 - ((rank_int - 1) / (count - 1))))


def build_candidate_table(
    association_rows: List[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is not None and candidate_id is not None:
            grouped[(str(episode_key), str(candidate_id))].append(row)

    episode_counts: Dict[str, int] = defaultdict(int)
    for episode_key, _candidate_id in labels:
        episode_counts[episode_key] += 1

    table: List[Dict[str, Any]] = []
    for key in sorted(labels):
        label = labels[key]
        rows = grouped.get(key, [])
        episode_key, candidate_id = key
        query = str(label.get("query"))
        group = PROPERTY_GROUP_BY_QUERY.get(query, "unknown")
        detector_scores = [safe_float(row.get("best_box_score")) for row in rows]
        detector_scores = [value for value in detector_scores if value is not None]
        visible_box_or_mask = [
            row
            for row in rows
            if row.get("projection_status") == "visible"
            and (row.get("projected_pixel_inside_box") is True or row.get("projected_pixel_inside_mask") is True)
        ]
        strict_associations = [row for row in rows if row.get("associated_to_candidate") is True]
        proximity = [projection_proximity(row) for row in rows]
        compact_scores = [
            projection_proximity(row) * compactness(box_area_ratio(row.get("best_box_xyxy")))
            for row in rows
        ]
        score_box_support = [
            safe_float(row.get("best_box_score")) or 0.0
            for row in visible_box_or_mask
        ]
        large_box_hits = [
            row for row in visible_box_or_mask if (box_area_ratio(row.get("best_box_xyxy")) or 0.0) >= 0.50
        ]
        s_sem = semantic_rank_prior(label.get("candidate_rank"), episode_counts.get(episode_key, 0))
        s_det = max(detector_scores) if detector_scores else 0.0
        s_proj = min(1.0, len(visible_box_or_mask) / 3.0)
        s_depth = min(1.0, len(strict_associations) / 2.0)
        compact_support = min(1.0, sum(compact_scores) / 3.0)
        score_box = min(1.0, sum(score_box_support))
        if group == "small_or_cluttered":
            s_prop = 0.60 * compact_support + 0.40 * s_proj
        elif group == "wall_mounted_or_planar":
            s_prop = 0.70 * score_box + 0.30 * max(proximity, default=0.0)
        elif group == "large_repeated_furniture":
            s_prop = 0.50 * s_depth + 0.30 * compact_support + 0.20 * s_proj
        else:
            s_prop = 0.45 * s_depth + 0.35 * s_proj + 0.20 * s_det
        r_amb = min(1.0, (len(large_box_hits) / 3.0) + max(0.0, s_proj - s_depth) * 0.25)
        table.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "episode_id": label.get("episode_id"),
                "scene_id": label.get("scene_id"),
                "query": query,
                "property_group": group,
                "candidate_id": candidate_id,
                "candidate_rank_before": label.get("candidate_rank"),
                "candidate_correct": label.get("candidate_correct"),
                "candidate_reachable": label.get("candidate_reachable"),
                "is_top_before": label.get("selected_for_goal") is True,
                "wrong_goal_visit_before": label.get("wrong_goal_visit") is True,
                "S_sem": s_sem,
                "S_det": s_det,
                "S_proj": s_proj,
                "S_depth": s_depth,
                "S_prop": max(0.0, min(1.0, s_prop)),
                "R_amb": r_amb,
                "N0_semantic_prior_only": s_sem,
                "N1_detector_score_only": s_det,
                "N2_projection_support_no_depth": s_proj,
                "N3_strict_depth_association": 0.55 * s_proj + 0.45 * s_depth,
                "N4_property_conditioned_depth_reliability": max(0.0, min(1.0, s_prop - 0.15 * r_amb)),
                "N5_object_node_evidence_full": max(
                    0.0,
                    min(1.0, 0.35 * s_sem + 0.15 * s_det + 0.15 * s_proj + 0.10 * s_depth + 0.35 * s_prop - 0.20 * r_amb),
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": label.get("candidate_correct") is not None,
            }
        )
    return table


def score_value(row: Dict[str, Any], field: str) -> Optional[float]:
    return safe_float(row.get(field))


def candidate_auc(rows: List[Dict[str, Any]], field: str) -> Optional[float]:
    positives: List[float] = []
    negatives: List[float] = []
    for row in rows:
        score = score_value(row, field)
        if score is None or row.get("candidate_correct") is None:
            continue
        if row.get("candidate_correct") is True:
            positives.append(score)
        else:
            negatives.append(score)
    return pairwise_auc(positives, negatives)


def scene_short_id(scene_id: Any) -> str:
    return Path(str(scene_id)).stem.replace(".basis", "")


def select_variant(rows: List[Dict[str, Any]], field: str, margin: float) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_episode[str(row.get("episode_key"))].append(row)

    decisions: List[Dict[str, Any]] = []
    scene_summary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    property_summary: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    baseline_correct = selected_correct = fixes = new_wrong = switches = 0

    for episode_key, candidates in sorted(by_episode.items()):
        top = next((row for row in candidates if row.get("is_top_before") is True), None)
        if top is None:
            top = max(candidates, key=lambda row: (row.get("S_sem") or 0.0, -int(row.get("candidate_rank_before") or 9999)))
        top_score = score_value(top, field)
        best = max(candidates, key=lambda row: (score_value(row, field) or 0.0, -int(row.get("candidate_rank_before") or 9999)))
        best_score = score_value(best, field)
        selected = top
        if best.get("candidate_id") != top.get("candidate_id") and top_score is not None and best_score is not None:
            if (best_score - top_score) >= margin and best_score > 0.0:
                selected = best
        base_ok = top.get("candidate_correct") is True
        selected_ok = selected.get("candidate_correct") is True
        switched = selected.get("candidate_id") != top.get("candidate_id")
        fix = (not base_ok) and selected_ok
        new = base_ok and not selected_ok
        baseline_correct += int(base_ok)
        selected_correct += int(selected_ok)
        fixes += int(fix)
        new_wrong += int(new)
        switches += int(switched)
        scene = scene_short_id(top.get("scene_id"))
        prop = str(top.get("property_group"))
        for bucket in (scene_summary[scene], property_summary[prop]):
            bucket["rows"] += 1
            bucket["baseline_correct"] += int(base_ok)
            bucket["selected_correct"] += int(selected_ok)
            bucket["delta"] += int(selected_ok) - int(base_ok)
            bucket["fixes"] += int(fix)
            bucket["new_wrong"] += int(new)
            bucket["switches"] += int(switched)
        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "variant": field,
                "episode_key": episode_key,
                "episode_id": top.get("episode_id"),
                "scene_id": top.get("scene_id"),
                "query": top.get("query"),
                "property_group": top.get("property_group"),
                "baseline_candidate_id": top.get("candidate_id"),
                "baseline_candidate_correct": top.get("candidate_correct"),
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_candidate_correct": selected.get("candidate_correct"),
                "baseline_score": top_score,
                "selected_score": score_value(selected, field),
                "switched": switched,
                "fixes_wrong_goal": fix,
                "creates_wrong_goal": new,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    rows_n = len(by_episode)
    scene_rows = [{"key": key, **dict(value)} for key, value in sorted(scene_summary.items())]
    property_rows = [{"key": key, **dict(value)} for key, value in sorted(property_summary.items())]
    positive_scene_count = sum(row["delta"] > 0 for row in scene_rows)
    negative_scene_count = sum(row["delta"] < 0 for row in scene_rows)
    positive_property_count = sum(row["delta"] > 0 for row in property_rows)
    negative_property_count = sum(row["delta"] < 0 for row in property_rows)
    summary = {
        "variant": field,
        "margin": margin,
        "rows": rows_n,
        "candidate_auc": candidate_auc(rows, field),
        "baseline_selected_correct": baseline_correct,
        "selected_correct": selected_correct,
        "selected_correct_delta_on_all_rows": ratio(selected_correct - baseline_correct, rows_n),
        "wrong_goal_fixes": fixes,
        "new_wrong_goals": new_wrong,
        "switches": switches,
        "switch_rate": ratio(switches, rows_n),
        "positive_scene_count": positive_scene_count,
        "negative_scene_count": negative_scene_count,
        "positive_property_count": positive_property_count,
        "negative_property_count": negative_property_count,
        "passes_minimal_gate": (selected_correct > baseline_correct and new_wrong == 0 and positive_scene_count >= 2 and negative_scene_count == 0),
        "scene_rows": scene_rows,
        "property_rows": property_rows,
    }
    return decisions, summary


def run(args: argparse.Namespace) -> Dict[str, Any]:
    detector_root = Path(args.detector_root)
    association_rows = load_jsonl(detector_root / "detector_candidate_associations.jsonl")
    decision_rows = load_jsonl(Path(args.candidate_decisions))
    labels = labels_for_policy(decision_rows, args.policy)
    candidate_table = build_candidate_table(association_rows, labels)
    variants = [
        "N0_semantic_prior_only",
        "N1_detector_score_only",
        "N2_projection_support_no_depth",
        "N3_strict_depth_association",
        "N4_property_conditioned_depth_reliability",
        "N5_object_node_evidence_full",
    ]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    variant_summaries: List[Dict[str, Any]] = []
    all_decisions: List[Dict[str, Any]] = []
    for field in variants:
        decisions, summary = select_variant(candidate_table, field, float(args.switch_margin))
        variant_summaries.append(summary)
        all_decisions.extend(decisions)
    best = max(
        variant_summaries,
        key=lambda row: (
            row["passes_minimal_gate"] is True,
            row["selected_correct_delta_on_all_rows"] or -1.0,
            -row["new_wrong_goals"],
            row["candidate_auc"] or -1.0,
        ),
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "detector_root": str(detector_root),
        "candidate_decisions": str(args.candidate_decisions),
        "policy": args.policy,
        "switch_margin": float(args.switch_margin),
        "property_groups": PROPERTY_GROUP_BY_QUERY,
        "candidate_rows": len(candidate_table),
        "best_variant": best["variant"],
        "best_variant_summary": {key: value for key, value in best.items() if key not in {"scene_rows", "property_rows"}},
        "variant_summaries": [{key: value for key, value in row.items() if key not in {"scene_rows", "property_rows"}} for row in variant_summaries],
        "promotion_ready": best["variant"] == "N5_object_node_evidence_full" and best["passes_minimal_gate"] is True,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    write_json(out / "summary.json", report)
    write_jsonl(out / "candidate_object_node_features.jsonl", candidate_table)
    write_jsonl(out / "objective_variant_decisions.jsonl", all_decisions)
    write_jsonl(out / "variant_summaries.jsonl", variant_summaries)
    for row in variant_summaries:
        name = str(row["variant"])
        write_jsonl(out / f"{name}_scene_summary.jsonl", row["scene_rows"])
        write_jsonl(out / f"{name}_property_group_summary.jsonl", row["property_rows"])
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate property-conditioned object-node detector evidence objectives.")
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="NoReobserve")
    parser.add_argument("--switch-margin", type=float, default=0.05)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
