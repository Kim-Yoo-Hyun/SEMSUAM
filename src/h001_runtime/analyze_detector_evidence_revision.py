import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.detector_evidence_revision.v1"


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


def box_area_ratio(box: Any, image_area: float = 160.0 * 120.0) -> Optional[float]:
    if not isinstance(box, list) or len(box) != 4:
        return None
    left, top, right, bottom = [safe_float(value) for value in box]
    if left is None or top is None or right is None or bottom is None:
        return None
    width = max(0.0, right - left)
    height = max(0.0, bottom - top)
    return min(1.0, (width * height) / image_area) if image_area > 0.0 else None


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


def candidate_labels(rows: List[Dict[str, Any]], policy: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    labels: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        labels[(str(episode_key), str(candidate_id))] = row
    return labels


def semantic_rank_prior(rank: Any, count: int) -> Optional[float]:
    try:
        rank_int = int(rank)
    except (TypeError, ValueError):
        return None
    if count <= 1:
        return 1.0
    return 1.0 - ((rank_int - 1) / (count - 1))


def build_candidate_table(
    association_rows: List[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        grouped[(str(episode_key), str(candidate_id))].append(row)

    episode_counts: Dict[str, int] = defaultdict(int)
    for episode_key, _candidate_id in labels:
        episode_counts[episode_key] += 1

    table: List[Dict[str, Any]] = []
    for key in sorted(labels):
        label = labels[key]
        episode_key, candidate_id = key
        rows = grouped.get(key, [])
        scores = [safe_float(row.get("best_box_score")) for row in rows]
        scores = [value for value in scores if value is not None]
        visible_box_or_mask = [
            row
            for row in rows
            if row.get("projection_status") == "visible"
            and (row.get("projected_pixel_inside_box") is True or row.get("projected_pixel_inside_mask") is True)
        ]
        visible_mask = [
            row
            for row in rows
            if row.get("projection_status") == "visible" and row.get("projected_pixel_inside_mask") is True
        ]
        proximity_values = [projection_proximity(row) for row in rows]
        compact_values = [
            projection_proximity(row) * compactness(box_area_ratio(row.get("best_box_xyxy")))
            for row in rows
        ]
        score_compact_values = [
            (safe_float(row.get("best_box_score")) or 0.0)
            * projection_proximity(row)
            * compactness(box_area_ratio(row.get("best_box_xyxy")))
            for row in rows
        ]
        score_box_no_depth_values = [
            safe_float(row.get("best_box_score")) or 0.0
            for row in visible_box_or_mask
        ]
        score_mask_no_depth_values = [
            safe_float(row.get("best_box_score")) or 0.0
            for row in visible_mask
        ]
        semantic_prior = semantic_rank_prior(label.get("candidate_rank"), episode_counts.get(episode_key, 0))
        table.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "episode_id": label.get("episode_id"),
                "scene_id": label.get("scene_id"),
                "query": label.get("query"),
                "candidate_id": candidate_id,
                "candidate_rank_before": label.get("candidate_rank"),
                "candidate_score_before": safe_float(label.get("candidate_score")),
                "candidate_correct": label.get("candidate_correct"),
                "candidate_correct_source": label.get("candidate_correct_source"),
                "candidate_reachable": label.get("candidate_reachable"),
                "is_top_before": label.get("selected_for_goal") is True,
                "wrong_goal_visit_before": label.get("wrong_goal_visit"),
                "semantic_rank_prior": semantic_prior,
                "best_box_score_max": max(scores) if scores else 0.0,
                "soft_box_no_depth_count": len(visible_box_or_mask),
                "soft_mask_no_depth_count": len(visible_mask),
                "proximity_sum": sum(proximity_values),
                "proximity_max": max(proximity_values) if proximity_values else 0.0,
                "compact_proximity_sum": sum(compact_values),
                "score_compact_proximity_sum": sum(score_compact_values),
                "score_box_no_depth_sum": sum(score_box_no_depth_values),
                "score_mask_no_depth_sum": sum(score_mask_no_depth_values),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": label.get("candidate_correct") is not None,
            }
        )
    return table


def score_value(row: Dict[str, Any], field: str) -> Optional[float]:
    value = row.get(field)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int):
        return float(value)
    return safe_float(value)


def evaluate_auc(rows: List[Dict[str, Any]], field: str) -> Optional[float]:
    positives: List[float] = []
    negatives: List[float] = []
    for row in rows:
        value = score_value(row, field)
        if value is None:
            continue
        if row.get("candidate_correct") is True:
            positives.append(value)
        elif row.get("candidate_correct") is False:
            negatives.append(value)
    return pairwise_auc(positives, negatives)


def per_query_auc(rows: List[Dict[str, Any]], fields: List[str]) -> Dict[str, Dict[str, Dict[str, Any]]]:
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for field in fields:
        grouped: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: {"positive": [], "negative": []})
        for row in rows:
            value = score_value(row, field)
            if value is None:
                continue
            if row.get("candidate_correct") is True:
                grouped[str(row.get("query"))]["positive"].append(value)
            elif row.get("candidate_correct") is False:
                grouped[str(row.get("query"))]["negative"].append(value)
        out[field] = {
            query: {
                "positive_count": len(values["positive"]),
                "negative_count": len(values["negative"]),
                "auc": pairwise_auc(values["positive"], values["negative"]),
            }
            for query, values in sorted(grouped.items())
        }
    return out


def select_with_weak_category_rule(rows: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_episode[str(row.get("episode_key"))].append(row)

    rule = {
        "plant": {"field": "soft_box_no_depth_count", "margin": 0.1},
        "tv_monitor": {"field": "score_box_no_depth_sum", "margin": 1.0},
        # Current sofa detector evidence is not reliable enough to switch.
        "sofa": {"field": None, "margin": None},
    }
    decisions: List[Dict[str, Any]] = []
    baseline_correct = selected_correct = fixes = new_wrong = switches = 0
    by_query: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"rows": 0, "selected_correct": 0, "fixes_wrong_goal": 0, "new_wrong_goal": 0, "switches": 0}
    )
    for episode_key, candidates in sorted(by_episode.items()):
        top = next((row for row in candidates if row.get("is_top_before") is True), None)
        if top is None:
            top = min(candidates, key=lambda row: int(row.get("candidate_rank_before") or 9999))
        query = str(top.get("query"))
        selected = top
        reason = "keep_semantic_prior"
        rule_spec = rule.get(query, {})
        field = rule_spec.get("field")
        margin = safe_float(rule_spec.get("margin")) or 0.0
        if field:
            top_score = score_value(top, field)
            alternatives = [
                row
                for row in candidates
                if row.get("candidate_id") != top.get("candidate_id") and score_value(row, field) is not None
            ]
            if top_score is not None and alternatives:
                best_alt = max(
                    alternatives,
                    key=lambda row: (score_value(row, field) or 0.0, -int(row.get("candidate_rank_before") or 9999)),
                )
                alt_score = score_value(best_alt, field)
                if alt_score is not None and (alt_score - top_score) >= margin:
                    selected = best_alt
                    reason = f"switch_{query}_{field}_margin_{margin:g}"

        base_ok = top.get("candidate_correct") is True
        selected_ok = selected.get("candidate_correct") is True
        baseline_correct += int(base_ok)
        selected_correct += int(selected_ok)
        fixes += int((not base_ok) and selected_ok)
        new_wrong += int(base_ok and not selected_ok)
        switched = selected.get("candidate_id") != top.get("candidate_id")
        switches += int(switched)
        by_query[query]["rows"] += 1
        by_query[query]["selected_correct"] += int(selected_ok)
        by_query[query]["fixes_wrong_goal"] += int((not base_ok) and selected_ok)
        by_query[query]["new_wrong_goal"] += int(base_ok and not selected_ok)
        by_query[query]["switches"] += int(switched)
        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "episode_id": top.get("episode_id"),
                "scene_id": top.get("scene_id"),
                "query": query,
                "baseline_candidate_id": top.get("candidate_id"),
                "baseline_candidate_correct": top.get("candidate_correct"),
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_candidate_correct": selected.get("candidate_correct"),
                "selection_reason": reason,
                "switched": switched,
                "fixes_wrong_goal": (not base_ok) and selected_ok,
                "creates_wrong_goal": base_ok and not selected_ok,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    row_count = len(by_episode)
    summary = {
        "rule": rule,
        "rows": row_count,
        "baseline_selected_correct": baseline_correct,
        "selected_correct": selected_correct,
        "selected_correct_delta_on_all_rows": ratio(selected_correct - baseline_correct, row_count),
        "wrong_goal_fixes": fixes,
        "new_wrong_goals": new_wrong,
        "switches": switches,
        "switch_rate": ratio(switches, row_count),
        "by_query": {
            query: {
                **values,
                "selected_correct_rate": ratio(values["selected_correct"], values["rows"]),
            }
            for query, values in sorted(by_query.items())
        },
    }
    return decisions, summary


def run(args: argparse.Namespace) -> Dict[str, Any]:
    detector_root = Path(args.detector_root)
    out = Path(args.out)
    association_rows = load_jsonl(detector_root / "detector_candidate_associations.jsonl")
    decision_rows = load_jsonl(Path(args.candidate_decisions))
    labels = candidate_labels(decision_rows, args.policy)
    candidate_table = build_candidate_table(association_rows, labels)
    fields = [
        "semantic_rank_prior",
        "best_box_score_max",
        "soft_box_no_depth_count",
        "soft_mask_no_depth_count",
        "compact_proximity_sum",
        "score_compact_proximity_sum",
        "score_box_no_depth_sum",
        "score_mask_no_depth_sum",
    ]
    decisions, selector = select_with_weak_category_rule(candidate_table)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "detector_root": str(detector_root),
        "candidate_decisions": str(args.candidate_decisions),
        "policy": args.policy,
        "candidate_rows": len(candidate_table),
        "feature_auc": {field: evaluate_auc(candidate_table, field) for field in fields},
        "per_query_auc": per_query_auc(candidate_table, fields),
        "selector": selector,
        "gate": {
            "min_selected_correct_delta": args.min_selected_correct_delta,
            "max_new_wrong_goals": args.max_new_wrong_goals,
            "passes_evidence_revision_gate": (
                selector["selected_correct_delta_on_all_rows"] is not None
                and selector["selected_correct_delta_on_all_rows"] >= float(args.min_selected_correct_delta)
                and selector["new_wrong_goals"] <= int(args.max_new_wrong_goals)
                and selector["wrong_goal_fixes"] > 0
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", summary)
    write_jsonl(out / "candidate_features.jsonl", candidate_table)
    write_jsonl(out / "weak_category_decisions.jsonl", decisions)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose category-aware detector-object evidence on an existing v3c artifact.")
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="NoReobserve")
    parser.add_argument("--min-selected-correct-delta", type=float, default=0.02)
    parser.add_argument("--max-new-wrong-goals", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
