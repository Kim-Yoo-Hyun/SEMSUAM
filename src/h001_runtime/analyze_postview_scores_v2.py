import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.postview_score_calibration.v2"


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


def bool_to_float(value: Optional[bool]) -> Optional[float]:
    if value is None:
        return None
    return 1.0 if value else 0.0


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


def candidate_label_index(rows: List[Dict[str, Any]], policy: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is not None and candidate_id is not None:
            index[(str(episode_key), str(candidate_id))] = row
    return index


def episode_index(rows: List[Dict[str, Any]], policy: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        if episode_key is not None:
            index[str(episode_key)] = row
    return index


def rank_score(rank: Optional[int], count: int) -> Optional[float]:
    if rank is None or count <= 0:
        return None
    if count == 1:
        return 1.0
    return 1.0 - (rank - 1) / (count - 1)


def top_mean(values: List[float], k: int) -> Optional[float]:
    if not values:
        return None
    return float(statistics.mean(sorted(values, reverse=True)[: max(1, k)]))


def score_value(score: Dict[str, Any]) -> Optional[float]:
    raw = safe_float(score.get("raw_image_text_score"))
    if raw is not None:
        return raw
    return safe_float(score.get("score_after"))


def build_candidate_score_table(
    postview_rows: List[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    table: List[Dict[str, Any]] = []
    for row in postview_rows:
        episode_key = str(row.get("episode_key"))
        action_scores = [
            score
            for score in row.get("candidate_scores", [])
            if score.get("action_eligible") is True and safe_float(score_value(score)) is not None
        ]
        action_sorted = sorted(action_scores, key=lambda score: safe_float(score_value(score)) or -math.inf, reverse=True)
        action_rank = {str(score.get("candidate_id")): idx + 1 for idx, score in enumerate(action_sorted)}
        action_count = len(action_sorted)
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
            aggregate = score_value(score) if score.get("action_eligible") is True else None
            rank = action_rank.get(candidate_id)
            frame_evidence = list(score.get("frame_evidence") or [])
            crop_score_count = sum(len(item.get("crop_scores") or []) for item in frame_evidence)
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
                    "projection_status": score.get("projection_status"),
                    "score_source": score.get("score_source"),
                    "score_calibration": score.get("score_calibration"),
                    "aggregate_raw_clip_cosine": aggregate,
                    "score_before": safe_float(score.get("score_before")),
                    "score_after": safe_float(score.get("score_after")),
                    "score_delta_artifact": safe_float(score.get("score_delta")),
                    "U_sem_before": safe_float(score.get("U_sem_before")),
                    "U_sem_after": safe_float(score.get("U_sem_after")),
                    "support_before": safe_float(score.get("support_before")),
                    "support_after": safe_float(score.get("support_after")),
                    "support_delta": safe_float(score.get("support_delta")),
                    "action_eligible": score.get("action_eligible") is True,
                    "center_fallback_used_for_action": score.get("center_fallback_used_for_action") is True,
                    "heading_visible_count": int(score.get("heading_visible_count") or 0),
                    "depth_consistent_count": int(score.get("depth_consistent_count") or 0),
                    "valid_crop_count": int(score.get("valid_crop_count") or 0),
                    "frame_evidence_count": len(frame_evidence),
                    "crop_score_count": crop_score_count,
                    "best_local_raw_clip_cosine": safe_float(score.get("best_local_raw_clip_cosine")),
                    "mean_top2_local_raw_clip_cosine": safe_float(score.get("mean_top2_local_raw_clip_cosine")),
                    "best_heading_id": score.get("best_heading_id"),
                    "best_crop_radius_px": score.get("best_crop_radius_px"),
                    "action_rank_by_aggregate": rank,
                    "action_rank_score": rank_score(rank, action_count),
                    "action_eligible_count_in_row": action_count,
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


def query_stats(table: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    grouped: Dict[str, List[float]] = defaultdict(list)
    for row in table:
        score = safe_float(row.get("aggregate_raw_clip_cosine"))
        if row.get("action_eligible") is True and score is not None:
            grouped[str(row.get("query"))].append(score)
    stats: Dict[str, Dict[str, float]] = {}
    for query, values in grouped.items():
        stats[query] = {
            "mean": float(statistics.mean(values)),
            "std": float(stdev(values)),
            "count": float(len(values)),
        }
    return stats


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
            safe_float(row.get("aggregate_raw_clip_cosine"))
            for row in rows
            if row.get("action_eligible") is True and row.get("candidate_correct") is False
        ]
        wrong_scores = [value for value in wrong_scores if value is not None]
        best_wrong_by_episode[episode_key] = max(wrong_scores) if wrong_scores else None

    for row in table:
        query = str(row.get("query"))
        aggregate = safe_float(row.get("aggregate_raw_clip_cosine"))
        query_mean = stats.get(query, {}).get("mean")
        query_std = stats.get(query, {}).get("std", 1.0)
        query_z = None if aggregate is None or query_mean is None else (aggregate - query_mean) / query_std
        row["query_aggregate_mean"] = query_mean
        row["query_aggregate_std"] = query_std
        row["query_zscore"] = query_z

        top = top_by_episode.get(str(row.get("episode_key")))
        top_aggregate = safe_float(top.get("aggregate_raw_clip_cosine")) if top else None
        top_z = safe_float(top.get("query_zscore")) if top else None
        top_rank_score = safe_float(top.get("action_rank_score")) if top else None
        row["agg_delta_to_top_before"] = None if aggregate is None or top_aggregate is None else aggregate - top_aggregate
        row["query_zscore_delta_to_top_before"] = None if query_z is None or top_z is None else query_z - top_z
        row["row_rank_delta_to_top_before"] = (
            None
            if row.get("action_rank_score") is None or top_rank_score is None
            else float(row["action_rank_score"]) - top_rank_score
        )
        best_wrong = best_wrong_by_episode.get(str(row.get("episode_key")))
        row["margin_to_best_action_wrong"] = None if aggregate is None or best_wrong is None else aggregate - best_wrong


def best_action(rows: List[Dict[str, Any]], field: str) -> Optional[Dict[str, Any]]:
    eligible = [row for row in rows if row.get("action_eligible") is True and safe_float(row.get(field)) is not None]
    if not eligible:
        return None
    return max(eligible, key=lambda row: (safe_float(row.get(field)) or -math.inf, -(row.get("candidate_rank_before") or 9999)))


def build_row_summary(
    table: List[Dict[str, Any]],
    noreobserve_episodes: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in table:
        by_episode[str(row.get("episode_key"))].append(row)

    summaries: List[Dict[str, Any]] = []
    for episode_key, rows in sorted(by_episode.items()):
        action_rows = [row for row in rows if row.get("action_eligible") is True]
        action_correct = [row for row in action_rows if row.get("candidate_correct") is True]
        action_wrong = [row for row in action_rows if row.get("candidate_correct") is False]
        top = next((row for row in rows if row.get("is_top_before")), None)
        agg_best = best_action(rows, "aggregate_raw_clip_cosine")
        z_best = best_action(rows, "query_zscore")
        rank_best = best_action(rows, "action_rank_score")
        no_row = noreobserve_episodes.get(episode_key, {})
        summaries.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "decision_id": rows[0].get("decision_id"),
                "scene_id": rows[0].get("scene_id"),
                "query": rows[0].get("query"),
                "candidate_score_count": len(rows),
                "action_eligible_count": len(action_rows),
                "action_eligible_correct_count": len(action_correct),
                "action_eligible_wrong_count": len(action_wrong),
                "has_action_eligible_candidate": bool(action_rows),
                "has_action_eligible_correct": bool(action_correct),
                "top_before_candidate_id": top.get("candidate_id") if top else None,
                "top_before_action_eligible": top.get("action_eligible") if top else None,
                "top_before_correct": top.get("candidate_correct") if top else None,
                "top_before_aggregate_raw_clip_cosine": top.get("aggregate_raw_clip_cosine") if top else None,
                "agg_best_candidate_id": agg_best.get("candidate_id") if agg_best else None,
                "agg_best_correct": agg_best.get("candidate_correct") if agg_best else None,
                "agg_best_score": agg_best.get("aggregate_raw_clip_cosine") if agg_best else None,
                "agg_best_delta_to_top_before": agg_best.get("agg_delta_to_top_before") if agg_best else None,
                "query_zscore_best_candidate_id": z_best.get("candidate_id") if z_best else None,
                "query_zscore_best_correct": z_best.get("candidate_correct") if z_best else None,
                "query_zscore_best_delta_to_top_before": z_best.get("query_zscore_delta_to_top_before") if z_best else None,
                "row_rank_best_candidate_id": rank_best.get("candidate_id") if rank_best else None,
                "row_rank_best_correct": rank_best.get("candidate_correct") if rank_best else None,
                "row_rank_best_delta_to_top_before": rank_best.get("row_rank_delta_to_top_before") if rank_best else None,
                "max_valid_crop_count": max((int(row.get("valid_crop_count") or 0) for row in rows), default=0),
                "max_heading_visible_count": max((int(row.get("heading_visible_count") or 0) for row in rows), default=0),
                "center_fallback_used_for_action": any(row.get("center_fallback_used_for_action") is True for row in rows),
                "no_reobserve_success": no_row.get("success"),
                "no_reobserve_wrong_goal_visit": no_row.get("wrong_goal_visit"),
                "no_reobserve_final_goal_candidate_id": no_row.get("final_goal_candidate_id"),
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
        action_rows = [row for row in rows if row.get("action_eligible") is True]
        correct_scores = [
            float(row["aggregate_raw_clip_cosine"])
            for row in action_rows
            if row.get("candidate_correct") is True and safe_float(row.get("aggregate_raw_clip_cosine")) is not None
        ]
        wrong_scores = [
            float(row["aggregate_raw_clip_cosine"])
            for row in action_rows
            if row.get("candidate_correct") is False and safe_float(row.get("aggregate_raw_clip_cosine")) is not None
        ]
        summaries = summaries_by_query.get(query, [])
        wrong_goal_rows = [row for row in summaries if row.get("no_reobserve_wrong_goal_visit") is True]
        out[query] = {
            "rows": len(summaries),
            "candidate_scores": len(rows),
            "action_eligible_candidate_scores": len(action_rows),
            "action_eligible_correct_candidates": len(correct_scores),
            "action_eligible_wrong_candidates": len(wrong_scores),
            "correct_vs_wrong_auc": pairwise_auc(correct_scores, wrong_scores),
            "correct_mean_aggregate_raw_clip_cosine": mean(correct_scores),
            "wrong_mean_aggregate_raw_clip_cosine": mean(wrong_scores),
            "rows_with_action_eligible_candidate": sum(1 for row in summaries if row.get("has_action_eligible_candidate")),
            "rows_with_action_eligible_correct": sum(1 for row in summaries if row.get("has_action_eligible_correct")),
            "aggregated_top_correct_rows": sum(1 for row in summaries if row.get("agg_best_correct") is True),
            "top_before_action_eligible_correct_rows": sum(
                1 for row in summaries if row.get("top_before_action_eligible") is True and row.get("top_before_correct") is True
            ),
            "no_reobserve_wrong_goal_rows": len(wrong_goal_rows),
            "wrong_goal_rows_with_action_eligible_correct": sum(
                1 for row in wrong_goal_rows if row.get("has_action_eligible_correct")
            ),
            "aggregated_top_correct_on_wrong_goal_rows": sum(
                1 for row in wrong_goal_rows if row.get("agg_best_correct") is True
            ),
            "projection_status_counts": dict(Counter(str(row.get("projection_status")) for row in rows)),
            "score_source_counts": dict(Counter(str(row.get("score_source")) for row in rows)),
        }
    return out


def threshold_values(rule: str) -> List[float]:
    if rule == "agg_local_delta":
        return [-0.02, -0.015, -0.01, -0.005, 0.0, 0.005, 0.01, 0.015, 0.02, 0.025, 0.03, 0.04, 0.05]
    if rule == "query_zscore_delta":
        return [-1.0, -0.75, -0.5, -0.25, 0.0, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
    if rule == "row_rank_delta":
        return [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    raise ValueError(f"unknown rule: {rule}")


def rule_fields(rule: str) -> Tuple[str, str]:
    if rule == "agg_local_delta":
        return "aggregate_raw_clip_cosine", "agg_delta_to_top_before"
    if rule == "query_zscore_delta":
        return "query_zscore", "query_zscore_delta_to_top_before"
    if rule == "row_rank_delta":
        return "action_rank_score", "row_rank_delta_to_top_before"
    raise ValueError(f"unknown rule: {rule}")


def threshold_sweep(table: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in table:
        by_episode[str(row.get("episode_key"))].append(row)

    rows: List[Dict[str, Any]] = []
    for rule in ["agg_local_delta", "query_zscore_delta", "row_rank_delta"]:
        score_field, delta_field = rule_fields(rule)
        for threshold in threshold_values(rule):
            selected_rows: List[Dict[str, Any]] = []
            top_rows: List[Dict[str, Any]] = []
            switch_eligible_rows = 0
            switches = 0
            beneficial = 0
            harmful = 0
            neutral = 0
            top_not_action_eligible = 0
            for episode_rows in by_episode.values():
                top = next((row for row in episode_rows if row.get("is_top_before")), None)
                if top is None:
                    continue
                top_rows.append(top)
                best = best_action(episode_rows, score_field)
                selected = top
                if top.get("action_eligible") is not True:
                    top_not_action_eligible += 1
                elif best is not None:
                    switch_eligible_rows += 1
                    delta = safe_float(best.get(delta_field))
                    if best.get("candidate_id") != top.get("candidate_id") and delta is not None and delta >= threshold:
                        selected = best
                        switches += 1
                        if top.get("candidate_correct") is False and selected.get("candidate_correct") is True:
                            beneficial += 1
                        elif top.get("candidate_correct") is True and selected.get("candidate_correct") is False:
                            harmful += 1
                        else:
                            neutral += 1
                selected_rows.append(selected)

            selected_correct = [bool_to_float(row.get("candidate_correct")) for row in selected_rows]
            top_correct = [bool_to_float(row.get("candidate_correct")) for row in top_rows]
            selected_mean = mean(selected_correct)
            top_mean_correct = mean(top_correct)
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "rule": rule,
                    "threshold": threshold,
                    "rows": len(top_rows),
                    "switch_eligible_rows": switch_eligible_rows,
                    "top_not_action_eligible_rows": top_not_action_eligible,
                    "switch_count": switches,
                    "switch_rate": switches / switch_eligible_rows if switch_eligible_rows else None,
                    "beneficial_switch_count": beneficial,
                    "harmful_switch_count": harmful,
                    "neutral_switch_count": neutral,
                    "selected_correct_rate": selected_mean,
                    "top_before_correct_rate": top_mean_correct,
                    "correct_rate_delta_vs_top_before": (
                        None if selected_mean is None or top_mean_correct is None else float(selected_mean) - float(top_mean_correct)
                    ),
                    "wrong_goal_proxy_rate": None if selected_mean is None else 1.0 - float(selected_mean),
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
    action_rows = [row for row in table if row.get("action_eligible") is True]
    correct_scores = [
        float(row["aggregate_raw_clip_cosine"])
        for row in action_rows
        if row.get("candidate_correct") is True and safe_float(row.get("aggregate_raw_clip_cosine")) is not None
    ]
    wrong_scores = [
        float(row["aggregate_raw_clip_cosine"])
        for row in action_rows
        if row.get("candidate_correct") is False and safe_float(row.get("aggregate_raw_clip_cosine")) is not None
    ]
    auc = pairwise_auc(correct_scores, wrong_scores)
    action_rows_with_correct = sum(1 for row in row_summaries if row.get("has_action_eligible_correct"))
    agg_top_correct = sum(1 for row in row_summaries if row.get("agg_best_correct") is True)
    top_before_action_correct = sum(
        1
        for row in row_summaries
        if row.get("top_before_action_eligible") is True and row.get("top_before_correct") is True
    )
    rows_with_action = sum(1 for row in row_summaries if row.get("has_action_eligible_candidate"))
    wrong_goal_rows = [row for row in row_summaries if row.get("no_reobserve_wrong_goal_visit") is True]
    wrong_goal_with_action_correct = sum(1 for row in wrong_goal_rows if row.get("has_action_eligible_correct"))
    wrong_goal_agg_top_correct = sum(1 for row in wrong_goal_rows if row.get("agg_best_correct") is True)
    center_action_count = sum(1 for row in table if row.get("center_fallback_used_for_action") is True)
    action_eligible_row_rate = rows_with_action / len(row_summaries) if row_summaries else 0.0

    if len(row_summaries) < int(args.expected_rows):
        gate = "needs_full_calibration_artifact"
    elif (
        wrong_goal_with_action_correct > int(args.baseline_wrong_goal_visible_correct)
        and wrong_goal_agg_top_correct >= int(args.min_wrong_goal_agg_top_correct)
        and center_action_count == 0
        and action_eligible_row_rate >= float(args.min_action_eligible_row_rate)
    ):
        gate = "passes_v2_calibration_diagnostic_gate"
    else:
        gate = "fails_v2_calibration_diagnostic_gate"

    best_sweep = None
    if sweep:
        best_sweep = max(
            sweep,
            key=lambda row: (
                row.get("correct_rate_delta_vs_top_before")
                if row.get("correct_rate_delta_vs_top_before") is not None
                else -math.inf,
                row.get("selected_correct_rate") if row.get("selected_correct_rate") is not None else -math.inf,
                row.get("beneficial_switch_count") or 0,
                -(row.get("harmful_switch_count") or 0),
                -abs(float(row.get("threshold") or 0.0)),
            ),
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "postview_scores": str(args.postview_scores),
        "candidate_decisions": str(args.candidate_decisions),
        "episodes": str(args.episodes),
        "out_root": str(args.out_root),
        "policy": args.policy,
        "baseline_policy": args.baseline_policy,
        "split_role": "calibration",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "expected_rows": int(args.expected_rows),
        "score_rows": len(row_summaries),
        "candidate_score_rows": len(table),
        "action_eligible_candidate_scores": len(action_rows),
        "action_eligible_candidate_scores_with_labels": len(correct_scores) + len(wrong_scores),
        "action_eligible_correct_candidates": len(correct_scores),
        "action_eligible_wrong_candidates": len(wrong_scores),
        "rows_with_action_eligible_candidate": rows_with_action,
        "action_eligible_row_rate": action_eligible_row_rate,
        "rows_with_action_eligible_correct_candidate": action_rows_with_correct,
        "aggregated_top_correct_rows": agg_top_correct,
        "top_before_action_eligible_correct_rows": top_before_action_correct,
        "rank_improvement_over_top_before": agg_top_correct - top_before_action_correct,
        "no_reobserve_wrong_goal_rows": len(wrong_goal_rows),
        "wrong_goal_rows_with_action_eligible_correct_candidate": wrong_goal_with_action_correct,
        "wrong_goal_rows_without_action_eligible_correct_candidate": len(wrong_goal_rows) - wrong_goal_with_action_correct,
        "aggregated_top_correct_on_wrong_goal_rows": wrong_goal_agg_top_correct,
        "baseline_wrong_goal_visible_correct": int(args.baseline_wrong_goal_visible_correct),
        "baseline_wrong_goal_rows": int(args.baseline_wrong_goal_rows),
        "correct_vs_wrong_auc": auc,
        "correct_mean_aggregate_raw_clip_cosine": mean(correct_scores),
        "wrong_mean_aggregate_raw_clip_cosine": mean(wrong_scores),
        "center_fallback_used_for_action_count": center_action_count,
        "projection_status_counts": dict(Counter(str(row.get("projection_status")) for row in table)),
        "score_source_counts": dict(Counter(str(row.get("score_source")) for row in table)),
        "max_valid_crop_count": max((int(row.get("valid_crop_count") or 0) for row in table), default=0),
        "max_heading_visible_count": max((int(row.get("heading_visible_count") or 0) for row in table), default=0),
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
    episode_rows = load_jsonl(Path(args.episodes))
    labels = candidate_label_index(candidate_rows, args.policy)
    noreobserve_episodes = episode_index(episode_rows, args.baseline_policy)

    table = build_candidate_score_table(postview_rows, labels)
    add_calibration_fields(table)
    row_summaries = build_row_summary(table, noreobserve_episodes)
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
    parser = argparse.ArgumentParser(description="Analyze H001 post-view v2 evidence calibration.")
    parser.add_argument("--postview-scores", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="EvidenceGatedSemanticOnly")
    parser.add_argument("--baseline-policy", default="NoReobserve")
    parser.add_argument("--expected-rows", type=int, default=50)
    parser.add_argument("--baseline-wrong-goal-visible-correct", type=int, default=6)
    parser.add_argument("--baseline-wrong-goal-rows", type=int, default=19)
    parser.add_argument("--min-wrong-goal-agg-top-correct", type=int, default=1)
    parser.add_argument("--min-action-eligible-row-rate", type=float, default=0.70)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
