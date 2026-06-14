import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_proxy_comparison.v1"
POLICY_NAME = "semantic_slam_proxy_comparison_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_proxy_comparison_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_proxy_comparison_v1"

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
    "evaluation_only_correct_candidate_count",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_unlabeled_candidate_count",
    "evaluation_only_wrong_candidate_count",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "is_correct",
    "oracle_action",
    "shortest_path_distance",
    "target_label",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


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


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def action_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def join_key(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    return tuple(str(row.get(key) or "") for key in keys)


def mean_from_stats(value: Any) -> Optional[float]:
    if isinstance(value, Mapping):
        return safe_float(value.get("mean"))
    return safe_float(value)


def variant_index(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Dict[Tuple[Tuple[str, ...], str], Mapping[str, Any]]:
    index: Dict[Tuple[Tuple[str, ...], str], Mapping[str, Any]] = {}
    for row in rows:
        index[(join_key(row, keys), str(row.get("edge_variant") or ""))] = row
    return index


def policy_names(contract: Mapping[str, Any]) -> List[str]:
    return [str(item.get("policy_name")) for item in contract.get("policy_definitions") or []]


def group_request_rows(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Dict[Tuple[str, ...], Mapping[str, Any]]:
    grouped: Dict[Tuple[str, ...], Mapping[str, Any]] = {}
    for row in rows:
        grouped[join_key(row, keys)] = row
    return grouped


def selected_edge_count(row: Mapping[str, Any], reason: str) -> int:
    counts = row.get("selected_edge_reason_counts") or {}
    if not isinstance(counts, Mapping):
        return 0
    return safe_int(counts.get(reason), 0)


def base_group_features(
    *,
    key: Tuple[str, ...],
    keys: Sequence[str],
    request_row: Mapping[str, Any],
    variants: Mapping[str, Mapping[str, Any]],
    semantic_weights: Mapping[str, Any],
    max_travel_mean: float,
    max_canonical_edge_count: int,
) -> Dict[str, Any]:
    canonical = variants.get("pose_spatial_or_loop") or {}
    context = variants.get("map_pose_context_no_candidate") or {}
    loop = variants.get("pose_loop") or {}
    shortcut = variants.get("candidate_overlap_only") or {}
    semantic_family = str(request_row.get("semantic_uncertainty_family") or "unknown_semantic_uncertainty_family")
    semantic_weight = safe_float(semantic_weights.get(semantic_family), 0.5) or 0.5
    candidate_id_count = safe_int(request_row.get("candidate_id_count"), 0)
    semantic_score = 0.6 * semantic_weight + 0.4 * min(candidate_id_count / 10.0, 1.0)
    travel_mean = mean_from_stats(request_row.get("travel_cost_proxy_m")) or 0.0
    normalized_travel = 0.0 if max_travel_mean <= 0 else min(travel_mean / max_travel_mean, 1.0)
    travel_penalty = 0.1 * normalized_travel
    canonical_edge_count = safe_int(canonical.get("edge_count"), 0)
    loop_edge_count = safe_int(loop.get("edge_count"), 0)
    context_edge_count = safe_int(context.get("edge_count"), 0)
    shortcut_edge_count = safe_int(shortcut.get("edge_count"), 0)
    largest_component_fraction = safe_float(canonical.get("largest_component_fraction"), 0.0) or 0.0
    loop_missing_indicator = 1.0 if loop_edge_count <= 0 else 0.0
    edge_sparsity_proxy = 1.0 - min(canonical_edge_count / max(max_canonical_edge_count, 1), 1.0)
    slam_gap_score = (
        0.5 * (1.0 - largest_component_fraction)
        + 0.3 * loop_missing_indicator
        + 0.2 * edge_sparsity_proxy
    )
    return {
        "join_key": dict(zip(keys, key)),
        "source_name": request_row.get("source_name"),
        "scene_key": request_row.get("scene_key"),
        "scene_id": request_row.get("scene_id"),
        "query": request_row.get("query"),
        "request_id": request_row.get("request_id"),
        "episode_key": request_row.get("episode_key"),
        "semantic_uncertainty_family": semantic_family,
        "semantic_family_weight": semantic_weight,
        "candidate_id_count": candidate_id_count,
        "semantic_score": semantic_score,
        "slam_gap_score": slam_gap_score,
        "travel_cost_proxy_m_mean": travel_mean,
        "normalized_travel_cost_proxy": normalized_travel,
        "travel_penalty": travel_penalty,
        "canonical_proxy_ready": canonical.get("proxy_ready") is True,
        "canonical_edge_count": canonical_edge_count,
        "canonical_connected_component_count": safe_int(canonical.get("connected_component_count"), 0),
        "canonical_largest_component_fraction": largest_component_fraction,
        "canonical_mean_degree": safe_float(canonical.get("mean_degree"), 0.0) or 0.0,
        "loop_edge_count": loop_edge_count,
        "context_edge_count": context_edge_count,
        "candidate_overlap_only_edge_count": shortcut_edge_count,
        "loop_missing_indicator": loop_missing_indicator,
        "edge_sparsity_proxy": edge_sparsity_proxy,
        "uses_gt_for_action": request_row.get("uses_gt_for_action") is True
        or any(row.get("uses_gt_for_action") is True for row in variants.values()),
    }


def policy_row(policy_name: str, base: Mapping[str, Any]) -> Dict[str, Any]:
    semantic_score = safe_float(base.get("semantic_score"), 0.0) or 0.0
    slam_gap_score = safe_float(base.get("slam_gap_score"), 0.0) or 0.0
    travel_penalty = safe_float(base.get("travel_penalty"), 0.0) or 0.0
    uses_semantic = policy_name in {"SemanticOnly", "SemanticSLAM"}
    uses_slam = policy_name in {"SLAMOnly", "SemanticSLAM"}
    if policy_name == "NoReobserveReference":
        utility = 0.0
        row_semantic_score = 0.0
        row_slam_gap_score = 0.0
        row_travel_penalty = 0.0
    elif policy_name == "SemanticOnly":
        utility = semantic_score - travel_penalty
        row_semantic_score = semantic_score
        row_slam_gap_score = 0.0
        row_travel_penalty = travel_penalty
    elif policy_name == "SLAMOnly":
        utility = slam_gap_score - travel_penalty
        row_semantic_score = 0.0
        row_slam_gap_score = slam_gap_score
        row_travel_penalty = travel_penalty
    elif policy_name == "SemanticSLAM":
        utility = 0.5 * semantic_score + 0.5 * slam_gap_score - travel_penalty
        row_semantic_score = semantic_score
        row_slam_gap_score = slam_gap_score
        row_travel_penalty = travel_penalty
    else:
        utility = 0.0
        row_semantic_score = 0.0
        row_slam_gap_score = 0.0
        row_travel_penalty = 0.0
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_semantic_slam_proxy_comparison",
        "row_type": "semantic_slam_proxy_comparison",
        "policy": POLICY_NAME,
        "policy_name": policy_name,
        "source_name": base.get("source_name"),
        "scene_key": base.get("scene_key"),
        "scene_id": base.get("scene_id"),
        "query": base.get("query"),
        "request_id": base.get("request_id"),
        "episode_key": base.get("episode_key"),
        "join_key": base.get("join_key"),
        "semantic_uncertainty_family": base.get("semantic_uncertainty_family"),
        "semantic_family_weight": base.get("semantic_family_weight"),
        "candidate_id_count": base.get("candidate_id_count"),
        "semantic_score": row_semantic_score,
        "slam_gap_score": row_slam_gap_score,
        "travel_penalty": row_travel_penalty,
        "policy_proxy_utility": utility,
        "utility_rank_score_only": None,
        "uses_semantic_channel_for_utility": uses_semantic,
        "uses_slam_channel_for_utility": uses_slam,
        "uses_candidate_overlap_as_pose_evidence": False,
        "canonical_proxy_ready": base.get("canonical_proxy_ready"),
        "canonical_edge_count": base.get("canonical_edge_count"),
        "canonical_connected_component_count": base.get("canonical_connected_component_count"),
        "canonical_largest_component_fraction": base.get("canonical_largest_component_fraction"),
        "canonical_mean_degree": base.get("canonical_mean_degree"),
        "loop_edge_count": base.get("loop_edge_count"),
        "context_edge_count": base.get("context_edge_count"),
        "candidate_overlap_only_edge_count": base.get("candidate_overlap_only_edge_count"),
        "loop_missing_indicator": base.get("loop_missing_indicator"),
        "edge_sparsity_proxy": base.get("edge_sparsity_proxy"),
        "travel_cost_proxy_m_mean": base.get("travel_cost_proxy_m_mean"),
        "normalized_travel_cost_proxy": base.get("normalized_travel_cost_proxy"),
        "uses_gt_for_action": base.get("uses_gt_for_action") is True,
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "step_4_5_promotion_satisfied": False,
        "paper_claim_allowed": False,
    }


def add_ranks(rows: List[Dict[str, Any]], keys: Sequence[str]) -> None:
    grouped: Dict[Tuple[str, ...], List[Dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(join_key(row, keys), []).append(row)
    for group_rows in grouped.values():
        ordered = sorted(group_rows, key=lambda item: safe_float(item.get("policy_proxy_utility"), 0.0) or 0.0, reverse=True)
        for rank, row in enumerate(ordered, start=1):
            row["utility_rank_score_only"] = rank


def policy_summary(rows: Sequence[Mapping[str, Any]], policy_name_value: str, keys: Sequence[str]) -> Dict[str, Any]:
    subset = [row for row in rows if row.get("policy_name") == policy_name_value]
    unique_groups = {join_key(row, keys) for row in subset}
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "semantic_slam_proxy_comparison_policy_summary",
        "policy": POLICY_NAME,
        "policy_name": policy_name_value,
        "policy_rows": len(subset),
        "request_groups": len(unique_groups),
        "policy_proxy_utility_stats": number_stats(row.get("policy_proxy_utility") for row in subset),
        "semantic_score_stats": number_stats(row.get("semantic_score") for row in subset),
        "slam_gap_score_stats": number_stats(row.get("slam_gap_score") for row in subset),
        "travel_penalty_stats": number_stats(row.get("travel_penalty") for row in subset),
        "canonical_proxy_ready_rate": ratio(sum(1 for row in subset if row.get("canonical_proxy_ready") is True), len(subset)),
        "mean_canonical_edge_count": (number_stats(row.get("canonical_edge_count") for row in subset)).get("mean"),
        "mean_largest_component_fraction": (
            number_stats(row.get("canonical_largest_component_fraction") for row in subset)
        ).get("mean"),
        "loop_edge_availability_rate": ratio(sum(1 for row in subset if safe_int(row.get("loop_edge_count"), 0) > 0), len(subset)),
        "mean_travel_penalty": (number_stats(row.get("travel_penalty") for row in subset)).get("mean"),
        "rank1_rows": sum(1 for row in subset if row.get("utility_rank_score_only") == 1),
        "rank1_rate": ratio(sum(1 for row in subset if row.get("utility_rank_score_only") == 1), len(subset)),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in subset),
        "terminal_commit_rows": sum(1 for row in subset if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in subset if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in subset if row.get("candidate_rejection") is True),
        "paper_claim_allowed": False,
    }


def build_rows(contract: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    source = contract.get("source") or {}
    scope = contract.get("comparison_scope") or {}
    keys = [str(key) for key in scope.get("join_key") or []]
    request_rows = load_jsonl(Path(str(source.get("source_audit_probe_request_rows"))))
    variant_rows = load_jsonl(Path(str(source.get("strict_edge_variant_rows"))))
    request_by_key = group_request_rows(request_rows, keys)
    variant_by_key = variant_index(variant_rows, keys)
    canonical_variant = str(scope.get("canonical_pose_variant") or "pose_spatial_or_loop")
    context_variant = str(scope.get("context_pose_variant") or "map_pose_context_no_candidate")
    loop_variant = str(scope.get("loop_variant") or "pose_loop")
    shortcut_variant = str(scope.get("shortcut_diagnostic_variant") or "candidate_overlap_only")
    all_group_keys = sorted(request_by_key.keys())
    max_travel_mean = max([mean_from_stats(row.get("travel_cost_proxy_m")) or 0.0 for row in request_rows] or [0.0])
    max_canonical_edge_count = max(
        [
            safe_int((variant_by_key.get((key, canonical_variant)) or {}).get("edge_count"), 0)
            for key in all_group_keys
        ]
        or [0]
    )
    semantic_weights = contract.get("fixed_semantic_family_weights") or {}
    rows: List[Dict[str, Any]] = []
    missing_variant_rows: List[Dict[str, str]] = []
    for key in all_group_keys:
        variants = {
            canonical_variant: variant_by_key.get((key, canonical_variant)) or {},
            context_variant: variant_by_key.get((key, context_variant)) or {},
            loop_variant: variant_by_key.get((key, loop_variant)) or {},
            shortcut_variant: variant_by_key.get((key, shortcut_variant)) or {},
        }
        for name, variant in variants.items():
            if not variant:
                missing_variant_rows.append(dict(zip(keys, key)) | {"missing_variant": name})
        base = base_group_features(
            key=key,
            keys=keys,
            request_row=request_by_key[key],
            variants=variants,
            semantic_weights=semantic_weights,
            max_travel_mean=max_travel_mean,
            max_canonical_edge_count=max_canonical_edge_count,
        )
        for policy in policy_names(contract):
            rows.append(policy_row(policy, base))
    add_ranks(rows, keys)
    diagnostics = {
        "request_group_count": len(all_group_keys),
        "max_travel_cost_proxy_m_mean": max_travel_mean,
        "max_canonical_edge_count": max_canonical_edge_count,
        "missing_variant_rows": missing_variant_rows[:20],
        "missing_variant_row_count": len(missing_variant_rows),
    }
    return rows, diagnostics


def build_summary(
    *,
    contract: Mapping[str, Any],
    comparison_rows: Sequence[Mapping[str, Any]],
    policy_summary_rows: Sequence[Mapping[str, Any]],
    diagnostics: Mapping[str, Any],
    out_root: Path,
) -> Dict[str, Any]:
    scope = contract.get("comparison_scope") or {}
    thresholds = contract.get("gate_thresholds") or {}
    keys = [str(key) for key in scope.get("join_key") or []]
    forbidden_keys = action_forbidden_keys(list(comparison_rows) + list(policy_summary_rows))
    request_groups = {join_key(row, keys) for row in comparison_rows}
    policy_set = {str(row.get("policy_name")) for row in comparison_rows}
    expected_policy_count = safe_int(thresholds.get("expected_policy_count"), 0)
    expected_request_groups = safe_int(thresholds.get("expected_request_groups"), 0)
    expected_rows = safe_int(thresholds.get("expected_comparison_rows"), 0)
    policy_group_sets = {
        policy: {join_key(row, keys) for row in comparison_rows if row.get("policy_name") == policy}
        for policy in policy_set
    }
    same_request_groups = bool(policy_group_sets) and all(groups == request_groups for groups in policy_group_sets.values())
    semantic_only = next((row for row in policy_summary_rows if row.get("policy_name") == "SemanticOnly"), {})
    slam_only = next((row for row in policy_summary_rows if row.get("policy_name") == "SLAMOnly"), {})
    comparison_gate = {
        "policy_count_passed": len(policy_set) == expected_policy_count,
        "request_group_count_passed": len(request_groups) == expected_request_groups,
        "comparison_row_count_passed": len(comparison_rows) == expected_rows,
        "same_request_groups_gate_passed": same_request_groups,
        "canonical_proxy_ready_rate_passed": safe_float(semantic_only.get("canonical_proxy_ready_rate"), 0.0)
        >= safe_float(thresholds.get("min_canonical_proxy_ready_rate"), 0.0),
        "loop_proxy_ready_rate_passed": safe_float(slam_only.get("loop_edge_availability_rate"), 0.0)
        >= safe_float(thresholds.get("min_loop_proxy_ready_rate"), 0.0),
        "missing_variant_rows_passed": safe_int(diagnostics.get("missing_variant_row_count"), 0) == 0,
    }
    comparison_gate["semantic_slam_proxy_comparison_gate_passed"] = all(comparison_gate.values())
    action_safety_gate = {
        "action_evidence_forbidden_key_gate_passed": len(forbidden_keys)
        <= safe_int(thresholds.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": sum(1 for row in comparison_rows if row.get("terminal_commit") is True)
        <= safe_int(thresholds.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": sum(1 for row in comparison_rows if row.get("candidate_commit") is True)
        <= safe_int(thresholds.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": sum(1 for row in comparison_rows if row.get("candidate_rejection") is True)
        <= safe_int(thresholds.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": any(row.get("uses_gt_for_action") is True for row in comparison_rows)
        is bool(thresholds.get("requires_uses_gt_for_action", False)),
    }
    action_safety_gate["action_safety_gate_passed"] = all(action_safety_gate.values())
    gate_passed = comparison_gate["semantic_slam_proxy_comparison_gate_passed"] and action_safety_gate["action_safety_gate_passed"]
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-04",
        "status": "implemented_and_docker_verified_semantic_slam_proxy_comparison",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "comparison_rows": "semantic_slam_proxy_comparison_rows.jsonl",
            "policy_summary_rows": "semantic_slam_proxy_comparison_policy_summary_rows.jsonl",
            "summary": "semantic_slam_proxy_comparison_summary.json",
        },
        "policy_rows": len(comparison_rows),
        "request_groups": len(request_groups),
        "policy_count": len(policy_set),
        "policies": sorted(policy_set),
        "same_request_groups_gate": same_request_groups,
        "policy_proxy_utility_stats": {
            row.get("policy_name"): row.get("policy_proxy_utility_stats") for row in policy_summary_rows
        },
        "policy_rank1_rows": {row.get("policy_name"): row.get("rank1_rows") for row in policy_summary_rows},
        "policy_rank1_rates": {row.get("policy_name"): row.get("rank1_rate") for row in policy_summary_rows},
        "canonical_proxy_ready_rate": semantic_only.get("canonical_proxy_ready_rate"),
        "mean_canonical_edge_count": semantic_only.get("mean_canonical_edge_count"),
        "mean_largest_component_fraction": semantic_only.get("mean_largest_component_fraction"),
        "loop_edge_availability_rate": semantic_only.get("loop_edge_availability_rate"),
        "mean_travel_penalty": semantic_only.get("mean_travel_penalty"),
        "normalization": {
            "max_travel_cost_proxy_m_mean": diagnostics.get("max_travel_cost_proxy_m_mean"),
            "max_canonical_edge_count": diagnostics.get("max_canonical_edge_count"),
        },
        "gate": {
            "comparison": comparison_gate,
            "action_safety": action_safety_gate,
            "semantic_slam_proxy_comparison_gate_passed": gate_passed,
        },
        "diagnostic_conclusion": {
            "semantic_slam_proxy_comparison_gate_passed": gate_passed,
            "recommended_next_task": "evaluate_proxy_comparison_output_before_step_4_5_promotion",
            "step_4_5_promotion_allowed": False,
            "terminal_policy_allowed": False,
            "paper_claim_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "action_evidence_forbidden_keys": forbidden_keys,
        "terminal_commit_rows": sum(1 for row in comparison_rows if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in comparison_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in comparison_rows if row.get("candidate_rejection") is True),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in comparison_rows),
        "blocked_task_behavior_metrics": (contract.get("metric_contract") or {}).get("blocked_task_behavior_metrics") or [],
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_satisfied": False,
        "paper_claim_allowed": False,
        "interpretation": {
            "fact": "This implementation applies fixed proxy utility formulas to the same request groups for four policy roles.",
            "agent_inference": "The output can be inspected for whether SemanticSLAM has a nontrivial proxy pattern, but it is not a task result or SLAM benefit proof.",
            "paper_claim": "No SLAM benefit, navigation utility, or SemanticSLAM complementarity claim is allowed from this comparison alone.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()
    contract = load_json(Path(args.contract))
    comparison_rows, diagnostics = build_rows(contract)
    keys = [str(key) for key in (contract.get("comparison_scope") or {}).get("join_key") or []]
    policy_summary_rows = [policy_summary(comparison_rows, name, keys) for name in policy_names(contract)]
    summary = build_summary(
        contract=contract,
        comparison_rows=comparison_rows,
        policy_summary_rows=policy_summary_rows,
        diagnostics=diagnostics,
        out_root=Path(args.out_root),
    )
    out_root = Path(args.out_root)
    outputs = contract.get("required_future_outputs") or {}
    write_jsonl(out_root / str(outputs.get("comparison_rows", "semantic_slam_proxy_comparison_rows.jsonl")), comparison_rows)
    write_jsonl(
        out_root / str(outputs.get("policy_summary_rows", "semantic_slam_proxy_comparison_policy_summary_rows.jsonl")),
        policy_summary_rows,
    )
    write_json(out_root / str(outputs.get("summary", "semantic_slam_proxy_comparison_summary.json")), summary)


if __name__ == "__main__":
    main()
