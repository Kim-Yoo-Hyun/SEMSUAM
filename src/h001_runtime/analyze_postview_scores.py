import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.postview_score_calibration.v1"


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
    if not math.isfinite(number):
        return None
    return number


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    valid = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    return statistics.mean(valid) if valid else None


def stdev(values: Iterable[Optional[float]]) -> float:
    valid = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if len(valid) < 2:
        return 1.0
    value = statistics.pstdev(valid)
    return value if value > 1e-8 else 1.0


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


def bool_to_float(value: Optional[bool]) -> Optional[float]:
    if value is None:
        return None
    return 1.0 if value else 0.0


def candidate_label_index(rows: List[Dict[str, Any]], policy: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        index[(str(episode_key), str(candidate_id))] = row
    return index


def viewpoint_index(rows: List[Dict[str, Any]], policy: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        if episode_key is not None:
            index[str(episode_key)] = row
    return index


def query_stats(candidate_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    for row in candidate_rows:
        raw = safe_float(row.get("raw_clip_cosine"))
        if raw is not None and row.get("projection_status") == "visible":
            grouped[str(row.get("query"))].append(raw)
    stats: Dict[str, Dict[str, float]] = {}
    for query, values in grouped.items():
        stats[query] = {
            "mean": float(statistics.mean(values)),
            "std": float(stdev(values)),
            "count": float(len(values)),
        }
    return stats


def rank_score(rank: Optional[int], count: int) -> Optional[float]:
    if rank is None or count <= 0:
        return None
    if count == 1:
        return 1.0
    return 1.0 - (rank - 1) / (count - 1)


def build_candidate_score_table(
    postview_rows: List[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    table: List[Dict[str, Any]] = []
    for row in postview_rows:
        episode_key = str(row.get("episode_key"))
        visible_scores = [
            score
            for score in row.get("candidate_scores", [])
            if score.get("projection_status") == "visible" and safe_float(score.get("raw_image_text_score")) is not None
        ]
        visible_sorted = sorted(
            visible_scores,
            key=lambda score: safe_float(score.get("raw_image_text_score")) or -math.inf,
            reverse=True,
        )
        visible_rank = {str(score.get("candidate_id")): idx + 1 for idx, score in enumerate(visible_sorted)}
        visible_count = len(visible_sorted)
        top_before_score = next(
            (
                score
                for score in row.get("candidate_scores", [])
                if int(score.get("candidate_rank_before") or -1) == 1
            ),
            None,
        )
        top_before_id = str(top_before_score.get("candidate_id")) if top_before_score else None

        for score in row.get("candidate_scores", []):
            candidate_id = str(score.get("candidate_id"))
            label = labels.get((episode_key, candidate_id), {})
            raw = safe_float(score.get("raw_image_text_score"))
            projection_status = str(score.get("projection_status") or "missing")
            is_visible = projection_status == "visible" and raw is not None
            rank = visible_rank.get(candidate_id)
            table.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "decision_id": row.get("decision_id"),
                    "episode_id": row.get("episode_id"),
                    "episode_key": episode_key,
                    "scene_id": row.get("scene_id"),
                    "query": row.get("query"),
                    "candidate_id": candidate_id,
                    "candidate_rank_before": score.get("candidate_rank_before"),
                    "is_top_before": candidate_id == top_before_id,
                    "projection_status": projection_status,
                    "score_source": score.get("score_source"),
                    "score_calibration": score.get("score_calibration"),
                    "raw_clip_cosine": raw,
                    "score_before": safe_float(score.get("score_before")),
                    "score_after": safe_float(score.get("score_after")),
                    "score_delta_artifact": safe_float(score.get("score_delta")),
                    "U_sem_before": safe_float(score.get("U_sem_before")),
                    "U_sem_after": safe_float(score.get("U_sem_after")),
                    "support_before": safe_float(score.get("support_before")),
                    "support_after": safe_float(score.get("support_after")),
                    "support_delta": safe_float(score.get("support_delta")),
                    "visible_rank_by_raw": rank,
                    "visible_rank_score": rank_score(rank, visible_count),
                    "visible_count_in_row": visible_count,
                    "candidate_correct": label.get("candidate_correct"),
                    "candidate_correct_source": label.get("candidate_correct_source"),
                    "selected_for_goal_before": label.get("selected_for_goal"),
                    "selected_for_reobserve_before": label.get("selected_for_reobserve"),
                    "explicit_commit_before": label.get("explicit_commit"),
                    "wrong_goal_visit_before": label.get("wrong_goal_visit"),
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": label.get("candidate_correct") is not None,
                }
            )
    return table


def add_calibration_fields(table: List[Dict[str, Any]]) -> None:
    stats = query_stats(table)
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in table:
        by_episode[str(row.get("episode_key"))].append(row)

    top_by_episode: Dict[str, Dict[str, Any]] = {}
    best_wrong_by_episode: Dict[str, Optional[float]] = {}
    for episode_key, rows in by_episode.items():
        top = next((row for row in rows if row.get("is_top_before")), None)
        if top is not None:
            top_by_episode[episode_key] = top
        wrong_scores = [
            safe_float(row.get("raw_clip_cosine"))
            for row in rows
            if row.get("projection_status") == "visible" and row.get("candidate_correct") is False
        ]
        wrong_scores = [value for value in wrong_scores if value is not None]
        best_wrong_by_episode[episode_key] = max(wrong_scores) if wrong_scores else None

    for row in table:
        query = str(row.get("query"))
        raw = safe_float(row.get("raw_clip_cosine"))
        query_mean = stats.get(query, {}).get("mean")
        query_std = stats.get(query, {}).get("std", 1.0)
        query_z = None if raw is None or query_mean is None else (raw - query_mean) / query_std
        row["query_raw_mean"] = query_mean
        row["query_raw_std"] = query_std
        row["query_zscore"] = query_z

        top = top_by_episode.get(str(row.get("episode_key")))
        top_raw = safe_float(top.get("raw_clip_cosine")) if top else None
        top_z = safe_float(top.get("query_zscore")) if top else None
        top_rank_score = safe_float(top.get("visible_rank_score")) if top else None
        row["raw_delta_to_top_before"] = None if raw is None or top_raw is None else raw - top_raw
        row["query_zscore_delta_to_top_before"] = None if query_z is None or top_z is None else query_z - top_z
        row["row_rank_delta_to_top_before"] = (
            None
            if row.get("visible_rank_score") is None or top_rank_score is None
            else float(row["visible_rank_score"]) - top_rank_score
        )

        best_wrong = best_wrong_by_episode.get(str(row.get("episode_key")))
        row["margin_to_best_visible_wrong"] = None if raw is None or best_wrong is None else raw - best_wrong


def best_visible(rows: List[Dict[str, Any]], field: str) -> Optional[Dict[str, Any]]:
    visible = [
        row
        for row in rows
        if row.get("projection_status") == "visible" and safe_float(row.get(field)) is not None
    ]
    if not visible:
        return None
    return max(visible, key=lambda row: (safe_float(row.get(field)) or -math.inf, -(row.get("candidate_rank_before") or 9999)))


def build_row_summary(table: List[Dict[str, Any]], viewpoints: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in table:
        by_episode[str(row.get("episode_key"))].append(row)

    summaries: List[Dict[str, Any]] = []
    for episode_key, rows in sorted(by_episode.items()):
        visible = [row for row in rows if row.get("projection_status") == "visible"]
        visible_correct = [row for row in visible if row.get("candidate_correct") is True]
        visible_wrong = [row for row in visible if row.get("candidate_correct") is False]
        top_before = next((row for row in rows if row.get("is_top_before")), None)
        raw_best = best_visible(rows, "raw_clip_cosine")
        z_best = best_visible(rows, "query_zscore")
        rank_best = best_visible(rows, "visible_rank_score")
        viewpoint = viewpoints.get(episode_key, {})
        summaries.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "decision_id": rows[0].get("decision_id"),
                "scene_id": rows[0].get("scene_id"),
                "query": rows[0].get("query"),
                "visible_count": len(visible),
                "visible_correct_count": len(visible_correct),
                "visible_wrong_count": len(visible_wrong),
                "has_visible_correct": bool(visible_correct),
                "top_before_candidate_id": top_before.get("candidate_id") if top_before else None,
                "top_before_visible": top_before in visible if top_before else False,
                "top_before_correct": top_before.get("candidate_correct") if top_before else None,
                "top_before_raw_clip_cosine": top_before.get("raw_clip_cosine") if top_before else None,
                "raw_best_candidate_id": raw_best.get("candidate_id") if raw_best else None,
                "raw_best_correct": raw_best.get("candidate_correct") if raw_best else None,
                "raw_best_score": raw_best.get("raw_clip_cosine") if raw_best else None,
                "raw_best_delta_to_top_before": raw_best.get("raw_delta_to_top_before") if raw_best else None,
                "query_zscore_best_candidate_id": z_best.get("candidate_id") if z_best else None,
                "query_zscore_best_correct": z_best.get("candidate_correct") if z_best else None,
                "query_zscore_best_delta_to_top_before": z_best.get("query_zscore_delta_to_top_before") if z_best else None,
                "row_rank_best_candidate_id": rank_best.get("candidate_id") if rank_best else None,
                "row_rank_best_correct": rank_best.get("candidate_correct") if rank_best else None,
                "row_rank_best_delta_to_top_before": rank_best.get("row_rank_delta_to_top_before") if rank_best else None,
                "raw_rank_gain_over_top_before": (
                    None
                    if top_before is None or raw_best is None
                    else (bool_to_float(raw_best.get("candidate_correct")) or 0.0)
                    - (bool_to_float(top_before.get("candidate_correct")) or 0.0)
                ),
                "support_proxy_switch_gate_reason": viewpoint.get("switch_gate_reason"),
                "support_proxy_final_candidate_changed": viewpoint.get("final_candidate_changed"),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return summaries


def query_breakdown(table: List[Dict[str, Any]], row_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    rows_by_query: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in table:
        rows_by_query[str(row.get("query"))].append(row)
    summaries_by_query: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in row_summaries:
        summaries_by_query[str(row.get("query"))].append(row)

    out: Dict[str, Any] = {}
    for query, rows in sorted(rows_by_query.items()):
        visible = [row for row in rows if row.get("projection_status") == "visible"]
        correct_scores = [
            float(row["raw_clip_cosine"])
            for row in visible
            if row.get("candidate_correct") is True and safe_float(row.get("raw_clip_cosine")) is not None
        ]
        wrong_scores = [
            float(row["raw_clip_cosine"])
            for row in visible
            if row.get("candidate_correct") is False and safe_float(row.get("raw_clip_cosine")) is not None
        ]
        summaries = summaries_by_query.get(query, [])
        out[query] = {
            "rows": len(summaries),
            "candidate_scores": len(rows),
            "visible_candidate_scores": len(visible),
            "visible_correct_candidates": len(correct_scores),
            "visible_wrong_candidates": len(wrong_scores),
            "correct_vs_wrong_auc": pairwise_auc(correct_scores, wrong_scores),
            "correct_mean_raw_clip_cosine": mean(correct_scores),
            "wrong_mean_raw_clip_cosine": mean(wrong_scores),
            "rows_with_visible_correct": sum(1 for row in summaries if row.get("has_visible_correct")),
            "raw_visible_top_correct_rows": sum(1 for row in summaries if row.get("raw_best_correct") is True),
            "top_before_visible_correct_rows": sum(1 for row in summaries if row.get("top_before_correct") is True),
            "projection_status_counts": dict(Counter(str(row.get("projection_status")) for row in rows)),
            "score_source_counts": dict(Counter(str(row.get("score_source")) for row in rows)),
        }
    return out


def threshold_values(rule: str) -> List[float]:
    if rule == "raw_delta":
        return [-0.02, -0.015, -0.01, -0.005, 0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
    if rule == "query_zscore_delta":
        return [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
    if rule == "row_rank_delta":
        return [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    raise ValueError(f"unknown rule: {rule}")


def rule_fields(rule: str) -> Tuple[str, str]:
    if rule == "raw_delta":
        return "raw_clip_cosine", "raw_delta_to_top_before"
    if rule == "query_zscore_delta":
        return "query_zscore", "query_zscore_delta_to_top_before"
    if rule == "row_rank_delta":
        return "visible_rank_score", "row_rank_delta_to_top_before"
    raise ValueError(f"unknown rule: {rule}")


def threshold_sweep(table: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in table:
        by_episode[str(row.get("episode_key"))].append(row)

    rows: List[Dict[str, Any]] = []
    for rule in ["raw_delta", "query_zscore_delta", "row_rank_delta"]:
        score_field, delta_field = rule_fields(rule)
        for threshold in threshold_values(rule):
            selected_rows: List[Dict[str, Any]] = []
            top_rows: List[Dict[str, Any]] = []
            switches = 0
            beneficial = 0
            harmful = 0
            neutral = 0
            eligible = 0
            for episode_rows in by_episode.values():
                top = next((row for row in episode_rows if row.get("is_top_before")), None)
                best = best_visible(episode_rows, score_field)
                if top is None or best is None:
                    continue
                top_rows.append(top)
                eligible += 1
                delta = safe_float(best.get(delta_field))
                selected = best if best.get("candidate_id") != top.get("candidate_id") and delta is not None and delta >= threshold else top
                selected_rows.append(selected)
                if selected.get("candidate_id") != top.get("candidate_id"):
                    switches += 1
                    if top.get("candidate_correct") is False and selected.get("candidate_correct") is True:
                        beneficial += 1
                    elif top.get("candidate_correct") is True and selected.get("candidate_correct") is False:
                        harmful += 1
                    else:
                        neutral += 1

            selected_correct = [bool_to_float(row.get("candidate_correct")) for row in selected_rows]
            top_correct = [bool_to_float(row.get("candidate_correct")) for row in top_rows]
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "rule": rule,
                    "threshold": threshold,
                    "eligible_rows": eligible,
                    "switch_count": switches,
                    "switch_rate": switches / eligible if eligible else None,
                    "beneficial_switch_count": beneficial,
                    "harmful_switch_count": harmful,
                    "neutral_switch_count": neutral,
                    "selected_correct_rate": mean(selected_correct),
                    "top_before_correct_rate": mean(top_correct),
                    "correct_rate_delta_vs_top_before": (
                        None
                        if mean(selected_correct) is None or mean(top_correct) is None
                        else float(mean(selected_correct)) - float(mean(top_correct))
                    ),
                    "wrong_goal_proxy_rate": (
                        None
                        if mean(selected_correct) is None
                        else 1.0 - float(mean(selected_correct))
                    ),
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                }
            )
    return rows


def build_summary(
    table: List[Dict[str, Any]],
    row_summaries: List[Dict[str, Any]],
    qbreakdown: Dict[str, Any],
    sweep: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    visible = [row for row in table if row.get("projection_status") == "visible"]
    correct_scores = [
        float(row["raw_clip_cosine"])
        for row in visible
        if row.get("candidate_correct") is True and safe_float(row.get("raw_clip_cosine")) is not None
    ]
    wrong_scores = [
        float(row["raw_clip_cosine"])
        for row in visible
        if row.get("candidate_correct") is False and safe_float(row.get("raw_clip_cosine")) is not None
    ]
    auc = pairwise_auc(correct_scores, wrong_scores)
    rows_with_visible_correct = sum(1 for row in row_summaries if row.get("has_visible_correct"))
    raw_top_correct = sum(1 for row in row_summaries if row.get("raw_best_correct") is True)
    top_before_correct = sum(1 for row in row_summaries if row.get("top_before_correct") is True)
    rows_at_least_two_visible = sum(1 for row in row_summaries if int(row.get("visible_count") or 0) >= 2)
    visible_top1_correct_rate_when_correct_visible = (
        raw_top_correct / rows_with_visible_correct if rows_with_visible_correct else None
    )
    collapsed_queries = sum(
        1
        for data in qbreakdown.values()
        if data.get("correct_vs_wrong_auc") is not None and float(data["correct_vs_wrong_auc"]) < 0.55
    )
    center_fallback_count = sum(1 for row in visible if row.get("score_source") == "openai_clip_center_crop_fallback")
    center_fallback_rate = center_fallback_count / len(visible) if visible else None

    if auc is not None and auc >= 0.70 and (visible_top1_correct_rate_when_correct_visible or 0.0) >= 0.60 and collapsed_queries <= 1:
        gate = "direct_raw_score_usable"
    elif auc is not None and auc >= 0.60 and rows_at_least_two_visible >= 25:
        gate = "needs_calibrated_or_rank_evidence"
    else:
        gate = "needs_scorer_or_viewpoint_revision"

    best_sweep = None
    if sweep:
        best_sweep = max(
            sweep,
            key=lambda row: (
                row.get("correct_rate_delta_vs_top_before") if row.get("correct_rate_delta_vs_top_before") is not None else -math.inf,
                row.get("selected_correct_rate") if row.get("selected_correct_rate") is not None else -math.inf,
                -abs(float(row.get("threshold") or 0.0)),
            ),
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "postview_scores": str(args.postview_scores),
        "candidate_decisions": str(args.candidate_decisions),
        "viewpoint_decisions": str(args.viewpoint_decisions),
        "out_root": str(args.out_root),
        "policy": args.policy,
        "split_role": "calibration",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "score_rows": len(row_summaries),
        "candidate_score_rows": len(table),
        "visible_candidate_scores": len(visible),
        "visible_candidate_scores_with_labels": len(correct_scores) + len(wrong_scores),
        "visible_correct_candidates": len(correct_scores),
        "visible_wrong_candidates": len(wrong_scores),
        "rows_with_at_least_1_visible_candidate": sum(1 for row in row_summaries if int(row.get("visible_count") or 0) >= 1),
        "rows_with_at_least_2_visible_candidates": rows_at_least_two_visible,
        "rows_with_visible_correct_candidate": rows_with_visible_correct,
        "correct_vs_wrong_auc": auc,
        "correct_mean_raw_clip_cosine": mean(correct_scores),
        "wrong_mean_raw_clip_cosine": mean(wrong_scores),
        "visible_top1_correct_rate_when_correct_visible": visible_top1_correct_rate_when_correct_visible,
        "raw_visible_top_correct_rows": raw_top_correct,
        "top_before_visible_correct_rows": top_before_correct,
        "rank_improvement_over_top_before": raw_top_correct - top_before_correct,
        "center_fallback_rate_visible": center_fallback_rate,
        "projection_status_counts": dict(Counter(str(row.get("projection_status")) for row in table)),
        "score_source_counts": dict(Counter(str(row.get("score_source")) for row in table)),
        "collapsed_query_count_auc_lt_0_55": collapsed_queries,
        "decision_gate": gate,
        "best_threshold_sweep_row": best_sweep,
        "output_files": {
            "candidate_score_table": "candidate_score_table.jsonl",
            "row_summary": "row_summary.jsonl",
            "query_breakdown": "query_breakdown.json",
            "threshold_sweep": "threshold_sweep.jsonl",
            "summary": "summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    postview_rows = load_jsonl(Path(args.postview_scores))
    candidate_rows = load_jsonl(Path(args.candidate_decisions))
    viewpoint_rows = load_jsonl(Path(args.viewpoint_decisions))
    labels = candidate_label_index(candidate_rows, args.policy)
    viewpoints = viewpoint_index(viewpoint_rows, args.policy)

    table = build_candidate_score_table(postview_rows, labels)
    add_calibration_fields(table)
    row_summaries = build_row_summary(table, viewpoints)
    qbreakdown = query_breakdown(table, row_summaries)
    sweep = threshold_sweep(table)
    summary = build_summary(table, row_summaries, qbreakdown, sweep, args)

    out = Path(args.out_root)
    write_jsonl(out / "candidate_score_table.jsonl", table)
    write_jsonl(out / "row_summary.jsonl", row_summaries)
    write_json(out / "query_breakdown.json", qbreakdown)
    write_jsonl(out / "threshold_sweep.jsonl", sweep)
    write_json(out / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze H001 post-view image-feature score calibration.")
    parser.add_argument("--postview-scores", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--viewpoint-decisions", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="EvidenceGatedSemanticOnly")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
