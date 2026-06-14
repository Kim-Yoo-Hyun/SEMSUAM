import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_slam_only_rich_underpowered_diagnostic.v1"
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_reviewer_defense_v1"
EVAL_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_reviewer_defense_output_evaluation_v1"
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_slam_only_rich_underpowered_diagnostic_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def row_float(row: Mapping[str, Any], key: str) -> float:
    return safe_float(row.get(key), 0.0) or 0.0


def row_int(row: Mapping[str, Any], key: str) -> int:
    return safe_int(row.get(key), 0)


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def join_key_tuple(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    key = row.get("join_key")
    if isinstance(key, Mapping):
        return (
            str(key.get("source_name") or ""),
            str(key.get("scene_key") or ""),
            str(key.get("query") or ""),
            str(key.get("request_id") or ""),
            str(key.get("episode_key") or ""),
        )
    return (
        str(row.get("source_name") or ""),
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        str(row.get("request_id") or ""),
        str(row.get("episode_key") or ""),
    )


def index_policy_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[join_key_tuple(row)][str(row.get("policy_name") or "")] = row
    return grouped


def scalar_scale_needed(semantic_score: float, map_pose_proxy: float) -> Optional[float]:
    if map_pose_proxy <= 1e-9:
        return None
    return semantic_score / map_pose_proxy


def dominant_cause(row: Mapping[str, Any], policy: Mapping[str, Any]) -> str:
    blocker = str(row.get("blocker_class") or "")
    scale_needed = safe_float(row.get("slam_scale_needed_to_match_semantic_score"))
    source_coverage_gap = row_float(row, "source_coverage_gap")
    context_gap = row_float(row, "context_gap")
    loop_gap = row_float(row, "loop_gap")
    map_pose_proxy = row_float(row, "map_pose_outcome_proxy")
    semantic_score = row_float(row, "semantic_score")
    slam_minus_semantic = row_float(row, "slam_minus_semantic_utility")
    candidate_id_count = row_int(policy, "candidate_id_count")

    if blocker == "slam_only_wins_but_insufficient_count":
        return "positive_slam_cases_too_sparse"
    if map_pose_proxy <= 0.25:
        return "weak_map_pose_proxy"
    if scale_needed is not None and scale_needed <= 1.35 and slam_minus_semantic < 0:
        return "near_miss_scale"
    if context_gap <= 0.05 and source_coverage_gap <= 0.05 and loop_gap <= 0.05:
        return "map_pose_terms_saturated"
    if semantic_score >= 0.66 and candidate_id_count >= 6:
        return "semantic_score_dominates_dense_candidate_pool"
    if scale_needed is not None and scale_needed > 1.8:
        return "large_scale_gap"
    return "mixed_or_request_pool_effect"


def make_diagnostic_rows(
    eval_rows: Sequence[Mapping[str, Any]],
    policy_index: Mapping[Tuple[str, str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    diagnostic_rows: List[Dict[str, Any]] = []
    for row in eval_rows:
        key = join_key_tuple(row)
        policies = policy_index.get(key) or {}
        policy = policies.get("SemanticSLAMInteractionGuarded") or policies.get("SemanticOnly") or {}
        semantic_score = row_float(row, "semantic_score")
        map_pose_proxy = row_float(row, "map_pose_outcome_proxy")
        scale_needed = scalar_scale_needed(semantic_score, map_pose_proxy)
        travel_penalty = row_float(policy, "travel_penalty")
        context_gap = row_float(row, "context_gap")
        source_coverage_gap = row_float(row, "source_coverage_gap")
        loop_gap = row_float(row, "loop_gap")
        saturated_terms = sum(1 for value in [context_gap, source_coverage_gap, loop_gap] if value <= 0.05)
        out = {
            "schema_version": SCHEMA_VERSION,
            "row_type": "semantic_slam_slam_only_rich_underpowered_diagnostic",
            "join_key": row.get("join_key"),
            "source_name": row.get("source_name"),
            "scene_key": row.get("scene_key"),
            "query": row.get("query"),
            "request_id": row.get("request_id"),
            "episode_key": row.get("episode_key"),
            "semantic_uncertainty_family": row.get("semantic_uncertainty_family"),
            "blocker_class": row.get("blocker_class"),
            "dominant_cause": "",
            "component_winner": row.get("component_winner"),
            "semantic_rank": row_int(row, "semantic_rank"),
            "slam_rank": row_int(row, "slam_rank"),
            "interaction_rank": row_int(row, "interaction_rank"),
            "semantic_score": semantic_score,
            "map_pose_outcome_proxy": map_pose_proxy,
            "semantic_only_utility": row_float(row, "semantic_only_utility"),
            "slam_only_rich_utility": row_float(row, "slam_only_rich_utility"),
            "semantic_slam_interaction_guarded_utility": row_float(row, "semantic_slam_interaction_guarded_utility"),
            "slam_minus_semantic_utility": row_float(row, "slam_minus_semantic_utility"),
            "slam_scale_needed_to_match_semantic_score": scale_needed,
            "travel_penalty": travel_penalty,
            "normalized_travel_cost_proxy": row_float(policy, "normalized_travel_cost_proxy"),
            "candidate_id_count": row_int(policy, "candidate_id_count"),
            "unique_viewpoint_count": row_int(policy, "unique_viewpoint_count"),
            "frame_row_count": row_int(policy, "frame_row_count"),
            "canonical_proxy_ready": row.get("canonical_proxy_ready") is True,
            "canonical_edge_count": row_int(policy, "canonical_edge_count"),
            "canonical_connected_component_count": row_int(policy, "canonical_connected_component_count"),
            "canonical_largest_component_fraction": row_float(policy, "canonical_largest_component_fraction"),
            "loop_edge_available": row.get("loop_edge_available") is True,
            "loop_edge_count": row_int(policy, "loop_edge_count"),
            "fragmentation_score": row_float(row, "fragmentation_score"),
            "largest_component_gap": row_float(row, "largest_component_gap"),
            "loop_gap": loop_gap,
            "source_coverage_gap": source_coverage_gap,
            "context_gap": context_gap,
            "saturated_term_count": saturated_terms,
            "map_pose_explained_interaction": row.get("map_pose_explained_interaction") is True,
            "semantic_only_shadowed_by_interaction": row.get("semantic_only_shadowed_by_interaction") is True,
            "uses_gt_for_action": row.get("uses_gt_for_action") is True,
            "paper_claim_allowed": False,
            "step_4_5_promotion_satisfied": False,
        }
        out["dominant_cause"] = dominant_cause(out, policy)
        diagnostic_rows.append(out)
    return diagnostic_rows


def summarize_by_key(rows: Sequence[Mapping[str, Any]], key_name: str) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key_name) or "")].append(row)
    summaries: List[Dict[str, Any]] = []
    for key, items in sorted(grouped.items()):
        total = len(items)
        summaries.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": f"semantic_slam_slam_only_rich_underpowered_{key_name}_summary",
                key_name: key,
                "rows": total,
                "slam_rank1_rows": sum(1 for row in items if row.get("slam_rank") == 1),
                "semantic_rank1_rows": sum(1 for row in items if row.get("semantic_rank") == 1),
                "interaction_rank1_rows": sum(1 for row in items if row.get("interaction_rank") == 1),
                "blocker_class_counts": compact_counter(row.get("blocker_class") for row in items),
                "dominant_cause_counts": compact_counter(row.get("dominant_cause") for row in items),
                "slam_minus_semantic_utility_stats": stats(row.get("slam_minus_semantic_utility") for row in items),
                "map_pose_outcome_proxy_stats": stats(row.get("map_pose_outcome_proxy") for row in items),
                "semantic_score_stats": stats(row.get("semantic_score") for row in items),
                "scale_needed_stats": stats(row.get("slam_scale_needed_to_match_semantic_score") for row in items),
            }
        )
    return summaries


def build_summary(
    *,
    source_summary: Mapping[str, Any],
    eval_summary: Mapping[str, Any],
    diagnostic_rows: Sequence[Mapping[str, Any]],
    query_rows: Sequence[Mapping[str, Any]],
    scene_rows: Sequence[Mapping[str, Any]],
    input_root: Path,
    eval_root: Path,
    out_root: Path,
) -> Dict[str, Any]:
    total = len(diagnostic_rows)
    slam_rank1_rows = sum(1 for row in diagnostic_rows if row.get("slam_rank") == 1)
    semantic_rank1_rows = sum(1 for row in diagnostic_rows if row.get("semantic_rank") == 1)
    interaction_rank1_rows = sum(1 for row in diagnostic_rows if row.get("interaction_rank") == 1)
    scale_values = [row.get("slam_scale_needed_to_match_semantic_score") for row in diagnostic_rows]
    scale_values = [value for value in scale_values if safe_float(value) is not None]
    scale_near_miss_rows = sum(1 for row in diagnostic_rows if (safe_float(row.get("slam_scale_needed_to_match_semantic_score")) or 999.0) <= 1.35)
    weak_map_pose_rows = sum(1 for row in diagnostic_rows if row_float(row, "map_pose_outcome_proxy") <= 0.25)
    saturated_term_rows = sum(1 for row in diagnostic_rows if row_int(row, "saturated_term_count") >= 2)
    high_semantic_score_rows = sum(1 for row in diagnostic_rows if row_float(row, "semantic_score") >= 0.66)
    action_gt_rows = sum(1 for row in diagnostic_rows if row.get("uses_gt_for_action") is True)
    gate = {
        "input_output_evaluation_completed_passed": eval_summary.get("status") == "completed_reviewer_defense_output_evaluation",
        "diagnostic_row_count_passed": total == safe_int(eval_summary.get("request_groups"), total),
        "primary_blocker_matches_passed": eval_summary.get("primary_blocker") == "slam_only_rich_underpowered",
        "no_gt_action_rows_passed": action_gt_rows == 0,
        "downstream_blocked_passed": source_summary.get("paper_claim_allowed") is False
        and eval_summary.get("paper_claim_allowed") is False
        and eval_summary.get("step_4_5_promotion_satisfied") is False,
    }
    gate["diagnostic_gate_passed"] = all(gate.values())

    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-05",
        "status": "completed_slam_only_rich_underpowered_diagnostic",
        "input_root": str(input_root),
        "eval_root": str(eval_root),
        "out_root": str(out_root),
        "output_files": {
            "diagnostic_rows": "semantic_slam_slam_only_rich_underpowered_diagnostic_rows.jsonl",
            "query_summary_rows": "semantic_slam_slam_only_rich_underpowered_query_summary_rows.jsonl",
            "scene_summary_rows": "semantic_slam_slam_only_rich_underpowered_scene_summary_rows.jsonl",
            "summary": "semantic_slam_slam_only_rich_underpowered_diagnostic_summary.json",
        },
        "request_groups": total,
        "source_primary_blocker": eval_summary.get("primary_blocker"),
        "slam_rank1_rows": slam_rank1_rows,
        "semantic_rank1_rows": semantic_rank1_rows,
        "interaction_rank1_rows": interaction_rank1_rows,
        "slam_rank1_rate": ratio(slam_rank1_rows, total),
        "semantic_rank1_rate": ratio(semantic_rank1_rows, total),
        "interaction_rank1_rate": ratio(interaction_rank1_rows, total),
        "blocker_class_counts": compact_counter(row.get("blocker_class") for row in diagnostic_rows),
        "dominant_cause_counts": compact_counter(row.get("dominant_cause") for row in diagnostic_rows),
        "query_count": len(query_rows),
        "scene_count": len(scene_rows),
        "query_summary_rows": len(query_rows),
        "scene_summary_rows": len(scene_rows),
        "weak_map_pose_proxy_rows": weak_map_pose_rows,
        "weak_map_pose_proxy_rate": ratio(weak_map_pose_rows, total),
        "saturated_map_pose_term_rows": saturated_term_rows,
        "saturated_map_pose_term_rate": ratio(saturated_term_rows, total),
        "high_semantic_score_rows": high_semantic_score_rows,
        "high_semantic_score_rate": ratio(high_semantic_score_rows, total),
        "scale_near_miss_rows": scale_near_miss_rows,
        "scale_near_miss_rate": ratio(scale_near_miss_rows, total),
        "slam_scale_needed_to_match_semantic_score_stats": stats(scale_values),
        "slam_minus_semantic_utility_stats": stats(row.get("slam_minus_semantic_utility") for row in diagnostic_rows),
        "map_pose_outcome_proxy_stats": stats(row.get("map_pose_outcome_proxy") for row in diagnostic_rows),
        "semantic_score_stats": stats(row.get("semantic_score") for row in diagnostic_rows),
        "travel_penalty_stats": stats(row.get("travel_penalty") for row in diagnostic_rows),
        "candidate_id_count_stats": stats(row.get("candidate_id_count") for row in diagnostic_rows),
        "unique_viewpoint_count_stats": stats(row.get("unique_viewpoint_count") for row in diagnostic_rows),
        "canonical_proxy_ready_rate": ratio(sum(1 for row in diagnostic_rows if row.get("canonical_proxy_ready") is True), total),
        "loop_edge_availability_rate": ratio(sum(1 for row in diagnostic_rows if row.get("loop_edge_available") is True), total),
        "gate": gate,
        "diagnostic_conclusion": {
            "primary_cause": "semantic_score_dominates_current_map_pose_proxy",
            "secondary_cause": "map_pose_terms_often_saturated_or_weak_without_task_map_outcome",
            "formula_change_allowed": False,
            "step_4_5_promotion_allowed": False,
            "recommended_next_task": "freeze_slam_only_rich_revision_contract_or_add_outcome_metric_probe",
        },
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "interpretation": {
            "fact": "SLAMOnlyRich remains underpowered because map_pose_outcome_proxy is below semantic_score on most rows, while action safety and comparison plumbing already pass.",
            "agent_inference": "This is not a reason to tune weights immediately. The next step should freeze a revision contract that either adds an outcome-linked map/pose term or predeclares a task/map probe to test whether SLAM-side uncertainty has independent utility.",
            "paper_claim": "No SemanticSLAM complementarity, ObjectNav benefit, SLAM benefit, terminal utility, first_eval, or policy-scale comparison claim is allowed from this diagnostic.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--eval-root", default=EVAL_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    input_root = Path(args.input_root)
    eval_root = Path(args.eval_root)
    out_root = Path(args.out_root)
    source_summary = load_json(input_root / "semantic_slam_reviewer_defense_summary.json")
    eval_summary = load_json(eval_root / "semantic_slam_reviewer_defense_output_evaluation_summary.json")
    eval_rows = load_jsonl(eval_root / "semantic_slam_reviewer_defense_output_evaluation_rows.jsonl")
    policy_rows = load_jsonl(input_root / "semantic_slam_reviewer_defense_rows.jsonl")
    policy_index = index_policy_rows(policy_rows)
    diagnostic_rows = make_diagnostic_rows(eval_rows, policy_index)
    query_rows = summarize_by_key(diagnostic_rows, "query")
    scene_rows = summarize_by_key(diagnostic_rows, "scene_key")
    summary = build_summary(
        source_summary=source_summary,
        eval_summary=eval_summary,
        diagnostic_rows=diagnostic_rows,
        query_rows=query_rows,
        scene_rows=scene_rows,
        input_root=input_root,
        eval_root=eval_root,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_slam_only_rich_underpowered_diagnostic_rows.jsonl", diagnostic_rows)
    write_jsonl(out_root / "semantic_slam_slam_only_rich_underpowered_query_summary_rows.jsonl", query_rows)
    write_jsonl(out_root / "semantic_slam_slam_only_rich_underpowered_scene_summary_rows.jsonl", scene_rows)
    write_json(out_root / "semantic_slam_slam_only_rich_underpowered_diagnostic_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
