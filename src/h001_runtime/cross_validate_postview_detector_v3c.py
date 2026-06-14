import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.postview_detector_cross_validation.v3c"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def scene_key(row: Dict[str, Any]) -> str:
    scene_id = str(row.get("scene_id") or "unknown")
    parts = scene_id.split("/")
    if len(parts) >= 3:
        return parts[2]
    return scene_id


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


def score_value(row: Optional[Dict[str, Any]], field: str) -> Optional[float]:
    if row is None:
        return None
    return safe_float(row.get(field))


def candidate_auc(rows: List[Dict[str, Any]], field: str) -> Tuple[Optional[float], int, int]:
    positives = [
        score_value(row, field)
        for row in rows
        if row.get("candidate_correct") is True and score_value(row, field) is not None
    ]
    negatives = [
        score_value(row, field)
        for row in rows
        if row.get("candidate_correct") is False and score_value(row, field) is not None
    ]
    positives = [value for value in positives if value is not None]
    negatives = [value for value in negatives if value is not None]
    return pairwise_auc(positives, negatives), len(positives), len(negatives)


def choose_category_modes(
    train_rows: List[Dict[str, Any]],
    feature_fields: List[str],
    min_auc: float,
    min_positive: int,
    min_negative: int,
) -> Dict[str, Dict[str, Any]]:
    modes: Dict[str, Dict[str, Any]] = {}
    for query in sorted({str(row.get("query")) for row in train_rows}):
        query_rows = [row for row in train_rows if str(row.get("query")) == query]
        candidates: List[Tuple[float, str, int, int]] = []
        for field in feature_fields:
            auc, positive_count, negative_count = candidate_auc(query_rows, field)
            if (
                auc is not None
                and auc >= min_auc
                and positive_count >= min_positive
                and negative_count >= min_negative
            ):
                candidates.append((float(auc), field, positive_count, negative_count))
        if candidates:
            auc, field, positive_count, negative_count = max(candidates, key=lambda item: item[0])
            modes[query] = {
                "mode": field,
                "train_auc": auc,
                "positive_count": positive_count,
                "negative_count": negative_count,
            }
        else:
            modes[query] = {
                "mode": "semantic_rank_prior",
                "train_auc": None,
                "positive_count": 0,
                "negative_count": 0,
            }
    return modes


def evaluate_fold(
    test_rows: List[Dict[str, Any]],
    modes: Dict[str, Dict[str, Any]],
    switch_margin: float,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in test_rows:
        by_episode[str(row.get("episode_key"))].append(row)

    summary = {
        "rows": 0,
        "baseline_correct": 0,
        "selected_correct": 0,
        "selected_correct_delta": 0,
        "wrong_goal_fixes": 0,
        "new_wrong_goals": 0,
        "switches": 0,
    }
    decisions: List[Dict[str, Any]] = []
    for episode_key, rows in sorted(by_episode.items()):
        top = next((row for row in rows if row.get("is_top_before") is True), None)
        if top is None:
            continue
        query = str(top.get("query"))
        mode = str(modes.get(query, {}).get("mode", "semantic_rank_prior"))
        top_score = score_value(top, mode)
        alternatives = [row for row in rows if row is not top and score_value(row, mode) is not None]
        best_alternative = max(alternatives, key=lambda row: score_value(row, mode) or -math.inf) if alternatives else None
        alt_score = score_value(best_alternative, mode)
        selected = (
            best_alternative
            if best_alternative is not None
            and top_score is not None
            and alt_score is not None
            and (alt_score - top_score) >= switch_margin
            else top
        )
        baseline_correct = top.get("candidate_correct") is True
        selected_correct = selected.get("candidate_correct") is True
        fixes = top.get("candidate_correct") is False and selected.get("candidate_correct") is True
        creates = top.get("candidate_correct") is True and selected.get("candidate_correct") is False
        switched = selected.get("candidate_id") != top.get("candidate_id")
        summary["rows"] += 1
        summary["baseline_correct"] += int(baseline_correct)
        summary["selected_correct"] += int(selected_correct)
        summary["wrong_goal_fixes"] += int(fixes)
        summary["new_wrong_goals"] += int(creates)
        summary["switches"] += int(switched)
        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "episode_id": top.get("episode_id"),
                "scene": scene_key(top),
                "query": query,
                "mode": mode,
                "switch_margin": switch_margin,
                "baseline_candidate_id": top.get("candidate_id"),
                "baseline_candidate_correct": baseline_correct,
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_candidate_correct": selected_correct,
                "switched": switched,
                "wrong_goal_fix": fixes,
                "new_wrong_goal": creates,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    summary["selected_correct_delta"] = summary["selected_correct"] - summary["baseline_correct"]
    return summary, decisions


def add_counts(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    for key, value in source.items():
        if isinstance(value, int):
            target[key] = int(target.get(key, 0)) + value


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.candidate_calibration))
    feature_fields = [field.strip() for field in str(args.feature_fields).split(",") if field.strip()]
    margins = [float(item) for item in str(args.switch_margins).split(",") if item.strip()]
    scenes = sorted({scene_key(row) for row in rows})
    fold_rows: List[Dict[str, Any]] = []
    decision_rows: List[Dict[str, Any]] = []
    aggregate_by_margin: Dict[str, Dict[str, Any]] = {}

    for margin in margins:
        aggregate = {
            "switch_margin": margin,
            "rows": 0,
            "baseline_correct": 0,
            "selected_correct": 0,
            "selected_correct_delta": 0,
            "wrong_goal_fixes": 0,
            "new_wrong_goals": 0,
            "switches": 0,
            "folds": len(scenes),
            "folds_with_positive_delta": 0,
            "folds_with_negative_delta": 0,
        }
        for scene in scenes:
            train_rows = [row for row in rows if scene_key(row) != scene]
            test_rows = [row for row in rows if scene_key(row) == scene]
            modes = choose_category_modes(
                train_rows,
                feature_fields,
                float(args.min_auc),
                int(args.min_positive),
                int(args.min_negative),
            )
            fold_summary, fold_decisions = evaluate_fold(test_rows, modes, margin)
            fold_summary.update(
                {
                    "schema_version": SCHEMA_VERSION,
                    "heldout_scene": scene,
                    "switch_margin": margin,
                    "mode_by_query": modes,
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                }
            )
            fold_rows.append(fold_summary)
            decision_rows.extend(fold_decisions)
            add_counts(aggregate, fold_summary)
            aggregate["folds_with_positive_delta"] += int(fold_summary["selected_correct_delta"] > 0)
            aggregate["folds_with_negative_delta"] += int(fold_summary["selected_correct_delta"] < 0)
        aggregate["selected_correct_delta"] = aggregate["selected_correct"] - aggregate["baseline_correct"]
        aggregate["passes_minimal_safety_gate"] = (
            aggregate["selected_correct_delta"] > 0
            and aggregate["wrong_goal_fixes"] > aggregate["new_wrong_goals"]
            and aggregate["folds_with_negative_delta"] == 0
        )
        aggregate["passes_robust_gate"] = (
            aggregate["passes_minimal_safety_gate"]
            and aggregate["folds_with_positive_delta"] >= max(3, math.ceil(len(scenes) / 2))
        )
        aggregate_by_margin[f"{margin:.3f}"] = aggregate

    best_margin = max(
        aggregate_by_margin.values(),
        key=lambda row: (
            int(row["passes_minimal_safety_gate"]),
            row["selected_correct_delta"],
            row["wrong_goal_fixes"] - row["new_wrong_goals"],
            -row["switches"],
        ),
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_calibration": str(args.candidate_calibration),
        "feature_fields": feature_fields,
        "fold_strategy": "leave_one_scene_out",
        "fold_count": len(scenes),
        "scenes": scenes,
        "min_auc": float(args.min_auc),
        "min_positive": int(args.min_positive),
        "min_negative": int(args.min_negative),
        "aggregate_by_margin": aggregate_by_margin,
        "best_margin": best_margin,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }

    out = Path(args.out_root)
    write_json(out / "summary.json", summary)
    write_jsonl(out / "folds.jsonl", fold_rows)
    write_jsonl(out / "decisions.jsonl", decision_rows)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cross-validate v3c detector category-best objective.")
    parser.add_argument("--candidate-calibration", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--feature-fields", default="O1_detector_max,O5_node_extent,O6_compact_extent")
    parser.add_argument("--switch-margins", default="0.0,0.02,0.05,0.08,0.10,0.12,0.15,0.20")
    parser.add_argument("--min-auc", type=float, default=0.65)
    parser.add_argument("--min-positive", type=int, default=3)
    parser.add_argument("--min-negative", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
