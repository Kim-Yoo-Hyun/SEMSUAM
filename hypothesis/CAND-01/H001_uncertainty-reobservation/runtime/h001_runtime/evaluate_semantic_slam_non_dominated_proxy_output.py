import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_non_dominated_proxy_output_evaluation.v1"
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_non_dominated_proxy_redesign_v1"
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_non_dominated_proxy_output_evaluation_v1"


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


def join_key(row: Mapping[str, Any]) -> Tuple[str, ...]:
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


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]]:
    groups: Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(join_key(row), {})[str(row.get("policy_name") or "")] = row
    return groups


def row_float(row: Mapping[str, Any], key: str) -> float:
    return safe_float(row.get(key), 0.0) or 0.0


def component_winner(semantic_utility: float, slam_utility: float) -> str:
    if semantic_utility > slam_utility:
        return "SemanticOnly"
    if slam_utility > semantic_utility:
        return "SLAMOnly"
    return "tie"


def row_identity(*rows: Mapping[str, Any]) -> Dict[str, Any]:
    for row in rows:
        if row:
            return {
                "join_key": row.get("join_key"),
                "source_name": row.get("source_name"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "request_id": row.get("request_id"),
                "episode_key": row.get("episode_key"),
                "semantic_uncertainty_family": row.get("semantic_uncertainty_family"),
            }
    return {}


def evaluate_groups(groups: Mapping[Tuple[str, ...], Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    eval_rows: List[Dict[str, Any]] = []
    for _key, policies in sorted(groups.items()):
        semantic = policies.get("SemanticOnly") or {}
        slam = policies.get("SLAMOnly") or {}
        interaction = policies.get("SemanticSLAMInteraction") or {}
        reference = policies.get("NoReobserveReference") or {}
        semantic_utility = row_float(semantic, "policy_proxy_utility")
        slam_utility = row_float(slam, "policy_proxy_utility")
        interaction_utility = row_float(interaction, "policy_proxy_utility")
        component_max = max(semantic_utility, slam_utility)
        winner = component_winner(semantic_utility, slam_utility)
        interaction_rank = safe_int(interaction.get("utility_rank_score_only"), 0)
        interaction_bonus_over_semantic = interaction_utility - semantic_utility
        interaction_margin_over_slam = interaction_utility - slam_utility
        interaction_margin_over_component = interaction_utility - component_max
        semantic_shadowed = interaction_bonus_over_semantic > 1e-9
        non_dominated = interaction_margin_over_component > 1e-9
        if not semantic or not slam or not interaction:
            diagnostic_class = "incomplete_policy_group"
        elif not non_dominated:
            diagnostic_class = "interaction_loses_to_component"
        elif winner == "SemanticOnly" and semantic_shadowed:
            diagnostic_class = "semantic_first_bonus_shadows_semantic_only"
        elif winner == "SLAMOnly":
            diagnostic_class = "interaction_overrides_slam_component"
        else:
            diagnostic_class = "interaction_non_dominated_other"
        identity = row_identity(interaction, semantic, slam, reference)
        eval_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "semantic_slam_non_dominated_proxy_group_evaluation",
                **identity,
                "component_winner": winner,
                "diagnostic_class": diagnostic_class,
                "semantic_only_utility": semantic_utility,
                "slam_only_utility": slam_utility,
                "semantic_slam_interaction_utility": interaction_utility,
                "no_reobserve_utility": row_float(reference, "policy_proxy_utility"),
                "component_max_utility": component_max,
                "interaction_bonus_over_semantic": interaction_bonus_over_semantic,
                "interaction_margin_over_slam": interaction_margin_over_slam,
                "interaction_margin_over_component": interaction_margin_over_component,
                "semantic_only_shadowed_by_interaction": semantic_shadowed,
                "interaction_non_dominated_by_component": non_dominated,
                "interaction_rank": interaction_rank,
                "semantic_only_rank": safe_int(semantic.get("utility_rank_score_only"), 0),
                "slam_only_rank": safe_int(slam.get("utility_rank_score_only"), 0),
                "semantic_pressure": row_float(interaction, "semantic_pressure"),
                "map_pose_pressure": row_float(interaction, "map_pose_pressure"),
                "interaction_score": row_float(interaction, "interaction_score"),
                "slam_gap_score": row_float(interaction, "slam_gap_score"),
                "loop_missing_indicator": row_float(interaction, "loop_missing_indicator"),
                "canonical_proxy_ready": interaction.get("canonical_proxy_ready") is True,
                "loop_edge_available": safe_int(interaction.get("loop_edge_count"), 0) > 0,
                "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in policies.values()),
                "paper_claim_allowed": False,
                "step_4_5_promotion_satisfied": False,
            }
        )
    return eval_rows


def nested_gate(source_summary: Mapping[str, Any], *keys: str) -> Any:
    current: Any = source_summary.get("gate")
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def build_summary(
    *,
    source_summary: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    input_root: Path,
    out_root: Path,
) -> Dict[str, Any]:
    total = len(group_rows)
    interaction_rank1_rows = sum(1 for row in group_rows if row.get("interaction_rank") == 1)
    semantic_only_rank1_rows = sum(1 for row in group_rows if row.get("semantic_only_rank") == 1)
    slam_only_rank1_rows = sum(1 for row in group_rows if row.get("slam_only_rank") == 1)
    semantic_shadowed_rows = sum(1 for row in group_rows if row.get("semantic_only_shadowed_by_interaction") is True)
    interaction_bonus_positive_rows = sum(1 for row in group_rows if row_float(row, "interaction_bonus_over_semantic") > 1e-9)
    interaction_loses_rows = sum(1 for row in group_rows if row.get("diagnostic_class") == "interaction_loses_to_component")
    interaction_overrides_slam_rows = sum(
        1 for row in group_rows if row.get("diagnostic_class") == "interaction_overrides_slam_component"
    )
    semantic_first_shadow_rows = sum(
        1 for row in group_rows if row.get("diagnostic_class") == "semantic_first_bonus_shadows_semantic_only"
    )
    high_rank1_without_outcome = ratio(interaction_rank1_rows, total) > 0.75
    semantic_first_additive_shadowing = (
        total > 0
        and semantic_shadowed_rows == total
        and interaction_bonus_positive_rows == total
        and semantic_only_rank1_rows == 0
    )
    source_gate_passed = bool(nested_gate(source_summary, "semantic_slam_non_dominated_proxy_redesign_gate_passed"))
    if source_gate_passed is False:
        source_gate_passed = bool(
            nested_gate(source_summary, "non_dominated_redesign", "non_dominated_redesign_gate_passed")
        )
    no_gt_action_leakage = not any(row.get("uses_gt_for_action") is True for row in group_rows) and not bool(
        source_summary.get("uses_gt_for_action")
    )
    integrity_gate = {
        "source_non_dominated_proxy_gate_passed": source_gate_passed,
        "request_group_count_passed": total == safe_int(source_summary.get("request_groups"), total),
        "no_gt_action_leakage_passed": no_gt_action_leakage,
        "source_paper_claim_blocked_passed": source_summary.get("paper_claim_allowed") is False,
    }
    reviewer_defense_gate = {
        "semantic_only_not_structurally_shadowed_passed": not semantic_first_additive_shadowing,
        "interaction_rank1_not_high_without_outcome_passed": not high_rank1_without_outcome,
        "task_or_map_outcome_link_required_passed": False,
    }
    integrity_gate["output_evaluation_integrity_gate_passed"] = all(integrity_gate.values())
    reviewer_defense_gate["reviewer_defense_gate_passed"] = all(reviewer_defense_gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-04",
        "status": "completed_semantic_slam_non_dominated_proxy_output_evaluation",
        "input_root": str(input_root),
        "out_root": str(out_root),
        "source_summary": str(input_root / "semantic_slam_non_dominated_proxy_redesign_summary.json"),
        "output_files": {
            "group_evaluation_rows": "semantic_slam_non_dominated_proxy_output_evaluation_rows.jsonl",
            "summary": "semantic_slam_non_dominated_proxy_output_evaluation_summary.json",
        },
        "request_groups": total,
        "interaction_rank1_rows": interaction_rank1_rows,
        "interaction_rank1_rate": ratio(interaction_rank1_rows, total),
        "semantic_only_rank1_rows": semantic_only_rank1_rows,
        "semantic_only_rank1_rate": ratio(semantic_only_rank1_rows, total),
        "slam_only_rank1_rows": slam_only_rank1_rows,
        "slam_only_rank1_rate": ratio(slam_only_rank1_rows, total),
        "semantic_only_shadowed_by_interaction_rows": semantic_shadowed_rows,
        "semantic_only_shadowed_by_interaction_rate": ratio(semantic_shadowed_rows, total),
        "interaction_bonus_positive_rows": interaction_bonus_positive_rows,
        "interaction_bonus_positive_rate": ratio(interaction_bonus_positive_rows, total),
        "interaction_loses_to_component_rows": interaction_loses_rows,
        "interaction_overrides_slam_component_rows": interaction_overrides_slam_rows,
        "semantic_first_bonus_shadows_semantic_only_rows": semantic_first_shadow_rows,
        "component_winner_counts": compact_counter(row.get("component_winner") for row in group_rows),
        "diagnostic_class_counts": compact_counter(row.get("diagnostic_class") for row in group_rows),
        "interaction_rank_by_component_winner_counts": compact_counter(
            f"{row.get('component_winner')}::rank{row.get('interaction_rank')}" for row in group_rows
        ),
        "family_diagnostic_class_counts": compact_counter(
            f"{row.get('semantic_uncertainty_family')}::{row.get('diagnostic_class')}" for row in group_rows
        ),
        "interaction_bonus_over_semantic_stats": stats(row.get("interaction_bonus_over_semantic") for row in group_rows),
        "interaction_margin_over_component_stats": stats(
            row.get("interaction_margin_over_component") for row in group_rows
        ),
        "interaction_margin_over_slam_stats": stats(row.get("interaction_margin_over_slam") for row in group_rows),
        "semantic_pressure_stats": stats(row.get("semantic_pressure") for row in group_rows),
        "map_pose_pressure_stats": stats(row.get("map_pose_pressure") for row in group_rows),
        "interaction_score_stats": stats(row.get("interaction_score") for row in group_rows),
        "canonical_proxy_ready_rate": ratio(sum(1 for row in group_rows if row.get("canonical_proxy_ready") is True), total),
        "loop_edge_availability_rate": ratio(sum(1 for row in group_rows if row.get("loop_edge_available") is True), total),
        "source_policy_rank1_rows": source_summary.get("policy_rank1_rows"),
        "source_policy_rank1_rates": source_summary.get("policy_rank1_rates"),
        "semantic_first_additive_shadowing_detected": semantic_first_additive_shadowing,
        "high_interaction_rank1_without_outcome_detected": high_rank1_without_outcome,
        "gate": {
            "integrity": integrity_gate,
            "reviewer_defense": reviewer_defense_gate,
            "output_evaluation_gate_passed": integrity_gate["output_evaluation_integrity_gate_passed"],
            "step_4_5_promotion_allowed": False,
            "paper_claim_allowed": False,
        },
        "step_4_5_promotion_satisfied": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "decision": {
            "promotion_decision": "do_not_promote",
            "utility_revision_required": True,
            "richer_slam_or_outcome_proxy_required": True,
            "recommended_next_task": "decide_stricter_cap_richer_slam_proxy_or_task_map_outcome_validation",
        },
        "interpretation": {
            "fact": "SemanticSLAMInteraction is rank-1 on most groups and strictly exceeds SemanticOnly on every evaluated group.",
            "agent_inference": "The redesigned proxy removes midpoint dominance but introduces a semantic-first additive shadowing risk: without task/map outcomes, high rank-1 rate is not yet evidence of semantic-SLAM complementarity.",
            "paper_claim": "No SemanticSLAM complementarity, ObjectNav benefit, or SLAM benefit claim is allowed from this proxy output evaluation.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()
    input_root = Path(args.input_root)
    out_root = Path(args.out_root)
    comparison_rows = load_jsonl(input_root / "semantic_slam_non_dominated_proxy_redesign_rows.jsonl")
    source_summary = load_json(input_root / "semantic_slam_non_dominated_proxy_redesign_summary.json")
    group_rows = evaluate_groups(group_by_request(comparison_rows))
    summary = build_summary(
        source_summary=source_summary,
        group_rows=group_rows,
        input_root=input_root,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_non_dominated_proxy_output_evaluation_rows.jsonl", group_rows)
    write_json(out_root / "semantic_slam_non_dominated_proxy_output_evaluation_summary.json", summary)


if __name__ == "__main__":
    main()
