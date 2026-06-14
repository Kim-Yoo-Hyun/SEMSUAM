import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


SCHEMA_VERSION = "h001.semantic_slam_reviewer_defense_output_evaluation.v1"
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_reviewer_defense_v1"
VERIFY_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_reviewer_defense_contract_v1.verify.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_reviewer_defense_output_evaluation_v1"


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


def row_float(row: Mapping[str, Any], key: str) -> float:
    return safe_float(row.get(key), 0.0) or 0.0


def row_int(row: Mapping[str, Any], key: str) -> int:
    return safe_int(row.get(key), 0)


def classify_blocker(row: Mapping[str, Any]) -> str:
    component_winner = str(row.get("component_winner") or "")
    diagnostic_class = str(row.get("diagnostic_class") or "")
    slam_rank = row_int(row, "slam_rank")
    interaction_rank = row_int(row, "interaction_rank")
    semantic_rank = row_int(row, "semantic_rank")
    map_pose_proxy = row_float(row, "map_pose_outcome_proxy")
    semantic_utility = row_float(row, "semantic_only_utility")
    slam_utility = row_float(row, "slam_only_rich_utility")
    interaction_utility = row_float(row, "semantic_slam_interaction_guarded_utility")
    if slam_rank == 1:
        return "slam_only_wins_but_insufficient_count"
    if component_winner == "SLAMOnlyRich" and interaction_rank == 1:
        return "interaction_overrides_slam_component"
    if component_winner == "SLAMOnlyRich":
        return "slam_component_present_but_interaction_loses_to_component"
    if component_winner == "SemanticOnly" and map_pose_proxy <= 0.25:
        return "semantic_wins_with_weak_map_pose_proxy"
    if component_winner == "SemanticOnly" and semantic_utility > slam_utility and interaction_rank == 1:
        return "semantic_wins_but_guarded_interaction_adds_small_map_pose_bonus"
    if component_winner == "SemanticOnly" and semantic_rank == 1:
        return "semantic_wins_without_interaction_override"
    if diagnostic_class:
        return diagnostic_class
    if interaction_utility > max(semantic_utility, slam_utility):
        return "interaction_non_dominated_other"
    return "unclassified"


def make_evaluation_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    eval_rows: List[Dict[str, Any]] = []
    for row in rows:
        semantic_utility = row_float(row, "semantic_only_utility")
        slam_utility = row_float(row, "slam_only_rich_utility")
        interaction_utility = row_float(row, "semantic_slam_interaction_guarded_utility")
        component_max = max(semantic_utility, slam_utility)
        map_pose_proxy = row_float(row, "map_pose_outcome_proxy")
        eval_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "semantic_slam_reviewer_defense_output_evaluation",
                "join_key": row.get("join_key"),
                "source_name": row.get("source_name"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "request_id": row.get("request_id"),
                "episode_key": row.get("episode_key"),
                "semantic_uncertainty_family": row.get("semantic_uncertainty_family"),
                "component_winner": row.get("component_winner"),
                "diagnostic_class": row.get("diagnostic_class"),
                "blocker_class": classify_blocker(row),
                "semantic_only_utility": semantic_utility,
                "slam_only_rich_utility": slam_utility,
                "semantic_slam_interaction_guarded_utility": interaction_utility,
                "slam_minus_semantic_utility": slam_utility - semantic_utility,
                "interaction_margin_over_component": interaction_utility - component_max,
                "map_pose_outcome_proxy": map_pose_proxy,
                "semantic_score": row_float(row, "semantic_score"),
                "semantic_pressure": row_float(row, "semantic_pressure"),
                "map_pose_pressure": row_float(row, "map_pose_pressure"),
                "interaction_gain": row_float(row, "interaction_gain"),
                "fragmentation_score": row_float(row, "fragmentation_score"),
                "largest_component_gap": row_float(row, "largest_component_gap"),
                "loop_gap": row_float(row, "loop_gap"),
                "source_coverage_gap": row_float(row, "source_coverage_gap"),
                "context_gap": row_float(row, "context_gap"),
                "canonical_proxy_ready": row.get("canonical_proxy_ready") is True,
                "loop_edge_available": row.get("loop_edge_available") is True,
                "semantic_only_shadowed_by_interaction": row.get("semantic_only_shadowed_by_interaction") is True,
                "map_pose_explained_interaction": row.get("map_pose_explained_interaction") is True,
                "unexplained_positive_bonus": row.get("unexplained_positive_bonus") is True,
                "candidate_overlap_used_as_pose_evidence": row.get("candidate_overlap_used_as_pose_evidence") is True,
                "component_max_shortcut_used": row.get("component_max_shortcut_used") is True,
                "semantic_rank": row_int(row, "semantic_rank"),
                "slam_rank": row_int(row, "slam_rank"),
                "interaction_rank": row_int(row, "interaction_rank"),
                "uses_gt_for_action": row.get("uses_gt_for_action") is True,
                "paper_claim_allowed": False,
                "step_4_5_promotion_satisfied": False,
            }
        )
    return eval_rows


def build_summary(
    *,
    source_summary: Mapping[str, Any],
    verify: Mapping[str, Any],
    eval_rows: Sequence[Mapping[str, Any]],
    input_root: Path,
    verify_path: Path,
    out_root: Path,
) -> Dict[str, Any]:
    total = len(eval_rows)
    verified_contract = verify.get("verified_contract") if isinstance(verify.get("verified_contract"), Mapping) else {}
    min_slam_rank1 = safe_int(verified_contract.get("min_slam_only_rich_rank1_rows"), 5)
    max_shadow_rate = safe_float(verified_contract.get("max_semantic_only_shadowed_by_interaction_rate_without_outcome"), 0.85)
    max_interaction_rank1_rate = safe_float(verified_contract.get("max_interaction_rank1_rate_without_outcome"), 0.75)
    min_map_pose_explained = safe_int(verified_contract.get("min_map_pose_explained_interaction_rows"), 10)

    slam_rank1_rows = sum(1 for row in eval_rows if row.get("slam_rank") == 1)
    interaction_rank1_rows = sum(1 for row in eval_rows if row.get("interaction_rank") == 1)
    semantic_rank1_rows = sum(1 for row in eval_rows if row.get("semantic_rank") == 1)
    semantic_shadowed_rows = sum(1 for row in eval_rows if row.get("semantic_only_shadowed_by_interaction") is True)
    map_pose_explained_rows = sum(1 for row in eval_rows if row.get("map_pose_explained_interaction") is True)
    unexplained_bonus_rows = sum(1 for row in eval_rows if row.get("unexplained_positive_bonus") is True)
    component_shortcut_rows = sum(1 for row in eval_rows if row.get("component_max_shortcut_used") is True)
    overlap_pose_rows = sum(1 for row in eval_rows if row.get("candidate_overlap_used_as_pose_evidence") is True)
    gt_action_rows = sum(1 for row in eval_rows if row.get("uses_gt_for_action") is True)

    semantic_shadow_rate = ratio(semantic_shadowed_rows, total)
    interaction_rank1_rate = ratio(interaction_rank1_rows, total)

    action_safety_gate = {
        "source_action_safety_gate_passed": bool(
            (((source_summary.get("gate") or {}).get("action_safety") or {}).get("action_safety_gate_passed"))
        ),
        "no_gt_action_rows_passed": gt_action_rows == 0,
        "no_terminal_or_candidate_action_passed": safe_int(source_summary.get("terminal_commit_rows"), 0) == 0
        and safe_int(source_summary.get("candidate_commit_rows"), 0) == 0
        and safe_int(source_summary.get("candidate_rejection_rows"), 0) == 0,
    }
    comparison_gate = {
        "source_comparison_gate_passed": bool(
            (((source_summary.get("gate") or {}).get("comparison") or {}).get("comparison_gate_passed"))
        ),
        "row_count_passed": total == safe_int(source_summary.get("diagnostic_rows"), total),
        "policy_rows_passed": safe_int(source_summary.get("policy_rows"), 0) == 200,
        "policy_summary_rows_passed": safe_int(source_summary.get("policy_summary_rows"), 0) == 4,
    }
    reviewer_defense_gate = {
        "semantic_shadow_rate_passed": semantic_shadow_rate <= (max_shadow_rate or 0.85),
        "interaction_rank1_rate_passed": interaction_rank1_rate <= (max_interaction_rank1_rate or 0.75),
        "map_pose_explained_interaction_rows_passed": map_pose_explained_rows >= min_map_pose_explained,
        "unexplained_positive_bonus_rows_passed": unexplained_bonus_rows == 0,
        "component_max_shortcut_rows_passed": component_shortcut_rows == 0,
        "candidate_overlap_pose_evidence_rows_passed": overlap_pose_rows == 0,
        "slam_only_rich_rank1_rows_passed": slam_rank1_rows >= min_slam_rank1,
        "task_or_map_outcome_validation_attached_passed": False,
    }
    action_safety_gate["action_safety_gate_passed"] = all(action_safety_gate.values())
    comparison_gate["comparison_gate_passed"] = all(comparison_gate.values())
    reviewer_defense_gate["reviewer_defense_output_gate_passed"] = all(reviewer_defense_gate.values())
    output_evaluation_gate = (
        action_safety_gate["action_safety_gate_passed"]
        and comparison_gate["comparison_gate_passed"]
        and reviewer_defense_gate["reviewer_defense_output_gate_passed"]
    )

    failed_reviewer_gates = [key for key, value in reviewer_defense_gate.items() if key.endswith("_passed") and value is False]
    primary_blocker = "none"
    if "slam_only_rich_rank1_rows_passed" in failed_reviewer_gates:
        primary_blocker = "slam_only_rich_underpowered"
    elif "task_or_map_outcome_validation_attached_passed" in failed_reviewer_gates:
        primary_blocker = "task_map_outcome_validation_missing"
    elif failed_reviewer_gates:
        primary_blocker = failed_reviewer_gates[0].replace("_passed", "")

    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-05",
        "status": "completed_reviewer_defense_output_evaluation",
        "input_root": str(input_root),
        "verify": str(verify_path),
        "out_root": str(out_root),
        "source_summary": str(input_root / "semantic_slam_reviewer_defense_summary.json"),
        "output_files": {
            "evaluation_rows": "semantic_slam_reviewer_defense_output_evaluation_rows.jsonl",
            "summary": "semantic_slam_reviewer_defense_output_evaluation_summary.json",
        },
        "request_groups": total,
        "policy_rows": source_summary.get("policy_rows"),
        "policy_summary_rows": source_summary.get("policy_summary_rows"),
        "diagnostic_rows": source_summary.get("diagnostic_rows"),
        "policy_rank1_rows": source_summary.get("policy_rank1_rows"),
        "policy_rank1_rates": source_summary.get("policy_rank1_rates"),
        "component_winner_counts": compact_counter(row.get("component_winner") for row in eval_rows),
        "diagnostic_class_counts": compact_counter(row.get("diagnostic_class") for row in eval_rows),
        "blocker_class_counts": compact_counter(row.get("blocker_class") for row in eval_rows),
        "semantic_rank1_rows": semantic_rank1_rows,
        "slam_only_rich_rank1_rows": slam_rank1_rows,
        "slam_only_rich_rank1_required": min_slam_rank1,
        "slam_only_rich_rank1_deficit": max(0, min_slam_rank1 - slam_rank1_rows),
        "interaction_rank1_rows": interaction_rank1_rows,
        "interaction_rank1_rate": interaction_rank1_rate,
        "semantic_only_shadowed_by_interaction_rows": semantic_shadowed_rows,
        "semantic_only_shadowed_by_interaction_rate": semantic_shadow_rate,
        "map_pose_explained_interaction_rows": map_pose_explained_rows,
        "unexplained_positive_bonus_rows": unexplained_bonus_rows,
        "slam_minus_semantic_utility_stats": stats(row.get("slam_minus_semantic_utility") for row in eval_rows),
        "interaction_margin_over_component_stats": stats(row.get("interaction_margin_over_component") for row in eval_rows),
        "map_pose_outcome_proxy_stats": stats(row.get("map_pose_outcome_proxy") for row in eval_rows),
        "semantic_score_stats": stats(row.get("semantic_score") for row in eval_rows),
        "fragmentation_score_stats": stats(row.get("fragmentation_score") for row in eval_rows),
        "largest_component_gap_stats": stats(row.get("largest_component_gap") for row in eval_rows),
        "loop_gap_stats": stats(row.get("loop_gap") for row in eval_rows),
        "source_coverage_gap_stats": stats(row.get("source_coverage_gap") for row in eval_rows),
        "context_gap_stats": stats(row.get("context_gap") for row in eval_rows),
        "canonical_proxy_ready_rate": ratio(sum(1 for row in eval_rows if row.get("canonical_proxy_ready") is True), total),
        "loop_edge_availability_rate": ratio(sum(1 for row in eval_rows if row.get("loop_edge_available") is True), total),
        "gate": {
            "action_safety": action_safety_gate,
            "comparison": comparison_gate,
            "reviewer_defense_output": reviewer_defense_gate,
            "output_evaluation_gate_passed": output_evaluation_gate,
        },
        "primary_blocker": primary_blocker,
        "recommended_next_task": "diagnose_slam_only_rich_underpowered_before_proxy_formula_change",
        "step_4_5_promotion_satisfied": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "interpretation": {
            "fact": "The guarded reviewer-defense output passes action-safety and comparison gates, and fails the reviewer-defense output gate because SLAMOnlyRich rank-1 rows are below the frozen minimum.",
            "agent_inference": "The current proxy weakens the previous semantic-first shadowing shortcut but does not yet establish independent SLAM-side utility. The next step is a diagnostic of SLAMOnlyRich scale, map/pose terms, and request-pool composition before any formula change.",
            "paper_claim": "No SemanticSLAM complementarity, ObjectNav benefit, SLAM benefit, terminal utility, first_eval, or policy-scale comparison claim is allowed from this output evaluation.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--verify", default=VERIFY_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    input_root = Path(args.input_root)
    verify_path = Path(args.verify)
    out_root = Path(args.out_root)
    source_summary = load_json(input_root / "semantic_slam_reviewer_defense_summary.json")
    verify = load_json(verify_path)
    diagnostic_rows = load_jsonl(input_root / "semantic_slam_reviewer_defense_diagnostic_rows.jsonl")
    eval_rows = make_evaluation_rows(diagnostic_rows)
    summary = build_summary(
        source_summary=source_summary,
        verify=verify,
        eval_rows=eval_rows,
        input_root=input_root,
        verify_path=verify_path,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_reviewer_defense_output_evaluation_rows.jsonl", eval_rows)
    write_json(out_root / "semantic_slam_reviewer_defense_output_evaluation_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
