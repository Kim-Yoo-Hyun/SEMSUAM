import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_task_map_outcome_probe.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_task_map_outcome_probe_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_task_map_outcome_probe_v1"
UNDERPOWERED_ROWS_DEFAULT = (
    "local_dataset/runs/h001_semantic_slam_slam_only_rich_underpowered_diagnostic_v1/"
    "semantic_slam_slam_only_rich_underpowered_diagnostic_rows.jsonl"
)
REQUEST_ROWS_DEFAULT = (
    "local_dataset/runs/h001_semantic_slam_map_pose_consistency_probe_v1/"
    "semantic_slam_map_pose_probe_request_rows.jsonl"
)
STRICT_EDGE_ROWS_DEFAULT = (
    "local_dataset/runs/h001_semantic_slam_strict_edge_variant_proxy_v1/"
    "semantic_slam_strict_edge_variant_proxy_rows.jsonl"
)

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "candidate_correctness_label",
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
    "posthoc_outcome_delta",
    "shortest_path_distance",
    "success_or_failure_label",
    "target_label",
    "wrong_goal_label",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
REQUIRED_POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")


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


def clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


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


def join_key(row: Mapping[str, Any]) -> Tuple[str, ...]:
    nested = row.get("join_key")
    if isinstance(nested, Mapping):
        return tuple(str(nested.get(key) or "") for key in JOIN_KEYS)
    return tuple(str(row.get(key) or "") for key in JOIN_KEYS)


def key_payload(row: Mapping[str, Any]) -> Dict[str, str]:
    key = join_key(row)
    return dict(zip(JOIN_KEYS, key))


def mean_from_stats(value: Any) -> Optional[float]:
    if isinstance(value, Mapping):
        return safe_float(value.get("mean"))
    return safe_float(value)


def index_by_key(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, ...], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


def index_variants(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(join_key(row), {})[str(row.get("edge_variant") or "")] = row
    return grouped


def task_label_index(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, ...], Mapping[str, Any]]:
    indexed: Dict[Tuple[str, ...], Mapping[str, Any]] = {}
    for row in rows:
        key = join_key(row)
        has_wrong_goal = (
            row.get("wrong_goal_visit_proxy") is not None
            or row.get("wrong_goal_visit") is not None
            or row.get("wrong_goal") is not None
        )
        has_wasted_path = row.get("wasted_path_proxy_m") is not None or row.get("wasted_path_m") is not None
        if has_wrong_goal or has_wasted_path:
            indexed[key] = row
    return indexed


def edge_reason_count(row: Mapping[str, Any], reason: str) -> int:
    counts = row.get("selected_edge_reason_counts")
    if not isinstance(counts, Mapping):
        return 0
    return safe_int(counts.get(reason), 0)


def strict_map_metrics(
    *,
    request: Mapping[str, Any],
    diagnostic: Mapping[str, Any],
    variants: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    canonical = variants.get("pose_spatial_or_loop") or {}
    context = variants.get("map_pose_context_no_candidate") or {}
    loop = variants.get("pose_loop") or {}
    candidate_count = max(
        safe_int(request.get("candidate_id_count"), 0),
        safe_int(diagnostic.get("candidate_id_count"), 0),
        safe_int(canonical.get("node_count"), 0),
        1,
    )
    unique_viewpoints = max(
        safe_int(request.get("unique_viewpoint_count"), 0),
        safe_int(diagnostic.get("unique_viewpoint_count"), 0),
    )
    connected_components = safe_int(canonical.get("connected_component_count"), candidate_count)
    largest_component_fraction = safe_float(canonical.get("largest_component_fraction"), 0.0) or 0.0
    mean_degree = safe_float(canonical.get("mean_degree"), 0.0) or 0.0
    spatial_edges = edge_reason_count(canonical, "spatial_proximity")
    loop_edges = max(edge_reason_count(canonical, "loop_closure_opportunity"), safe_int(loop.get("edge_count"), 0))
    context_edges = safe_int(context.get("edge_count"), 0)
    canonical_ready = canonical.get("proxy_ready") is True
    context_ready = context.get("proxy_ready") is True

    connected_component_count_delta = max(0.0, float(candidate_count - connected_components))
    largest_component_fraction_delta = max(0.0, largest_component_fraction)
    spatial_edge_count_delta = float(spatial_edges)
    loop_edge_count_delta = float(loop_edges)
    mean_degree_delta = max(0.0, mean_degree)
    component_reduction = clip(connected_component_count_delta / max(float(candidate_count - 1), 1.0))
    mean_degree_norm = clip(mean_degree_delta / max(float(candidate_count - 1), 1.0))
    pose_graph_connectivity_delta = clip(
        0.35 * largest_component_fraction_delta
        + 0.25 * component_reduction
        + 0.20 * (1.0 if spatial_edges > 0 else 0.0)
        + 0.10 * (1.0 if loop_edges > 0 else 0.0)
        + 0.10 * mean_degree_norm
    )

    source_coverage_gap = safe_float(diagnostic.get("source_coverage_gap"), 1.0)
    context_gap = safe_float(diagnostic.get("context_gap"), 1.0)
    source_coverage_gap_delta = clip(1.0 - (source_coverage_gap if source_coverage_gap is not None else 1.0))
    context_gap_delta = clip(1.0 - (context_gap if context_gap is not None else 1.0))
    viewpoint_coverage_delta = clip(unique_viewpoints / max(float(candidate_count), 1.0))
    depth_pose_consistency_proxy_delta = clip(
        0.45 * (1.0 if canonical_ready else 0.0)
        + 0.25 * (1.0 if context_ready else 0.0)
        + 0.20 * (1.0 if spatial_edges > 0 else 0.0)
        + 0.10 * (1.0 if loop_edges > 0 else 0.0)
    )
    map_pose_consistency_delta = clip(
        0.30 * source_coverage_gap_delta
        + 0.25 * context_gap_delta
        + 0.25 * viewpoint_coverage_delta
        + 0.20 * depth_pose_consistency_proxy_delta
    )
    map_side_delta = clip(0.60 * pose_graph_connectivity_delta + 0.40 * map_pose_consistency_delta)
    return {
        "canonical_proxy_ready": canonical_ready,
        "context_proxy_ready": context_ready,
        "connected_component_count_delta": connected_component_count_delta,
        "largest_component_fraction_delta": largest_component_fraction_delta,
        "spatial_edge_count_delta": spatial_edge_count_delta,
        "loop_edge_count_delta": loop_edge_count_delta,
        "mean_degree_delta": mean_degree_delta,
        "pose_graph_connectivity_delta": pose_graph_connectivity_delta,
        "source_coverage_gap_delta": source_coverage_gap_delta,
        "context_gap_delta": context_gap_delta,
        "viewpoint_coverage_delta": viewpoint_coverage_delta,
        "depth_pose_consistency_proxy_delta": depth_pose_consistency_proxy_delta,
        "map_pose_consistency_delta": map_pose_consistency_delta,
        "map_side_delta": map_side_delta,
        "strict_edge_node_count": safe_int(canonical.get("node_count"), 0),
        "strict_edge_count": safe_int(canonical.get("edge_count"), 0),
        "strict_connected_component_count": connected_components,
        "strict_largest_component_fraction": largest_component_fraction,
        "strict_mean_degree": mean_degree,
        "strict_spatial_edge_count": spatial_edges,
        "strict_loop_edge_count": loop_edges,
        "strict_context_edge_count": context_edges,
    }


def base_risk_proxy(request: Mapping[str, Any], diagnostic: Mapping[str, Any]) -> Dict[str, float]:
    candidate_count = max(safe_int(request.get("candidate_id_count"), 0), safe_int(diagnostic.get("candidate_id_count"), 0))
    unique_viewpoints = max(
        safe_int(request.get("unique_viewpoint_count"), 0),
        safe_int(diagnostic.get("unique_viewpoint_count"), 0),
    )
    semantic_score = safe_float(diagnostic.get("semantic_score"), 0.0) or 0.0
    semantic_pressure = clip((semantic_score - 0.50) / 0.40)
    candidate_pressure = clip(candidate_count / 8.0)
    viewpoint_pressure = clip(1.0 - (unique_viewpoints / max(float(candidate_count), 1.0)))
    map_pose_proxy = safe_float(diagnostic.get("map_pose_outcome_proxy"), 0.0) or 0.0
    weak_map_pressure = clip(1.0 - map_pose_proxy)
    wrong_goal_risk = clip(
        0.40 * semantic_pressure
        + 0.25 * candidate_pressure
        + 0.20 * weak_map_pressure
        + 0.15 * viewpoint_pressure
    )
    travel_mean = mean_from_stats(request.get("travel_cost_proxy_m")) or 0.0
    return {
        "label_free_wrong_goal_risk_proxy": wrong_goal_risk,
        "label_free_wasted_path_risk_proxy_m": wrong_goal_risk * travel_mean,
        "semantic_pressure": semantic_pressure,
        "candidate_pressure": candidate_pressure,
        "viewpoint_pressure": viewpoint_pressure,
        "weak_map_pressure": weak_map_pressure,
        "reobserve_travel_cost_m": travel_mean,
    }


def label_metrics(label_row: Optional[Mapping[str, Any]]) -> Dict[str, Optional[float]]:
    if not label_row:
        return {"wrong_goal_visit_proxy": None, "wasted_path_proxy_m": None}
    wrong_goal = safe_float(
        label_row.get("wrong_goal_visit_proxy", label_row.get("wrong_goal_visit", label_row.get("wrong_goal")))
    )
    wasted_path = safe_float(label_row.get("wasted_path_proxy_m", label_row.get("wasted_path_m")))
    return {"wrong_goal_visit_proxy": wrong_goal, "wasted_path_proxy_m": wasted_path}


def policy_map_delta(policy: str, map_metrics: Mapping[str, Any]) -> float:
    if policy == "SLAMOnlyRich_current":
        return safe_float(map_metrics.get("map_side_delta"), 0.0) or 0.0
    return 0.0


def build_probe_rows(
    *,
    contract: Mapping[str, Any],
    diagnostics: Sequence[Mapping[str, Any]],
    request_index: Mapping[Tuple[str, ...], Mapping[str, Any]],
    variant_index_map: Mapping[Tuple[str, ...], Mapping[str, Mapping[str, Any]]],
    label_index_map: Mapping[Tuple[str, ...], Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    probe_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    for diagnostic in sorted(diagnostics, key=join_key):
        key = join_key(diagnostic)
        request = request_index.get(key) or diagnostic
        variants = variant_index_map.get(key) or {}
        map_metrics = strict_map_metrics(request=request, diagnostic=diagnostic, variants=variants)
        risk_metrics = base_risk_proxy(request, diagnostic)
        label_row = label_index_map.get(key)
        labels = label_metrics(label_row)
        label_join_available = labels["wrong_goal_visit_proxy"] is not None or labels["wasted_path_proxy_m"] is not None
        key_data = key_payload(diagnostic)
        base = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "semantic_slam_task_map_outcome_probe",
            "row_type": "semantic_slam_task_map_outcome_probe",
            "join_key": key_data,
            "source_name": key_data["source_name"],
            "scene_key": key_data["scene_key"],
            "query": key_data["query"],
            "request_id": key_data["request_id"],
            "episode_key": key_data["episode_key"],
            "semantic_uncertainty_family": diagnostic.get("semantic_uncertainty_family"),
            "candidate_id_count": safe_int(diagnostic.get("candidate_id_count"), 0),
            "frame_row_count": safe_int(diagnostic.get("frame_row_count"), 0),
            "unique_viewpoint_count": safe_int(diagnostic.get("unique_viewpoint_count"), 0),
            "semantic_score": safe_float(diagnostic.get("semantic_score"), 0.0) or 0.0,
            "current_semantic_only_utility": safe_float(diagnostic.get("semantic_only_utility"), 0.0) or 0.0,
            "current_slam_only_rich_utility": safe_float(diagnostic.get("slam_only_rich_utility"), 0.0) or 0.0,
            "current_interaction_guarded_utility": safe_float(
                diagnostic.get("semantic_slam_interaction_guarded_utility"), 0.0
            )
            or 0.0,
            "current_blocker_class": diagnostic.get("blocker_class"),
            "current_dominant_cause": diagnostic.get("dominant_cause"),
            "saturated_term_count": safe_int(diagnostic.get("saturated_term_count"), 0),
            "uses_gt_for_action": False,
            "terminal_commit": False,
            "candidate_commit": False,
            "candidate_rejection": False,
            "paper_claim_allowed": False,
            "step_4_5_promotion_satisfied": False,
            "map_side_metric_name": "pose_graph_connectivity_delta+map_pose_consistency_delta",
            "task_side_metric_name": "wrong_goal_visit_proxy_delta+wasted_path_proxy_delta",
            "label_join_available": label_join_available,
            "task_proxy_evaluable": label_join_available,
            "task_label_source": "provided_task_label_rows" if label_join_available else None,
            "wrong_goal_visit_proxy": labels["wrong_goal_visit_proxy"],
            "wasted_path_proxy_m": labels["wasted_path_proxy_m"],
            "reobserve_travel_cost_m": risk_metrics["reobserve_travel_cost_m"],
            "label_free_wrong_goal_risk_proxy": risk_metrics["label_free_wrong_goal_risk_proxy"],
            "label_free_wasted_path_risk_proxy_m": risk_metrics["label_free_wasted_path_risk_proxy_m"],
            "label_free_risk_proxy_for_gate": False,
            "label_free_risk_proxy_note": "diagnostic_only_not_a_task_outcome_label",
        }
        for metric_key, metric_value in map_metrics.items():
            base[metric_key] = metric_value
        for metric_key, metric_value in risk_metrics.items():
            if metric_key not in base:
                base[metric_key] = metric_value

        policy_rows: Dict[str, Dict[str, Any]] = {}
        for policy in REQUIRED_POLICIES:
            map_delta = policy_map_delta(policy, map_metrics)
            row = dict(base)
            row["policy_name"] = policy
            row["map_side_delta"] = map_delta
            row["pose_graph_connectivity_delta"] = (
                map_metrics["pose_graph_connectivity_delta"] if policy == "SLAMOnlyRich_current" else 0.0
            )
            row["map_pose_consistency_delta"] = (
                map_metrics["map_pose_consistency_delta"] if policy == "SLAMOnlyRich_current" else 0.0
            )
            if label_join_available:
                row["task_side_delta"] = 0.0
                row["wrong_goal_visit_proxy_delta_vs_no_reobserve"] = 0.0
                row["wrong_goal_visit_proxy_delta_vs_semantic_only"] = 0.0
                row["wasted_path_proxy_delta_vs_no_reobserve_m"] = 0.0
                row["wasted_path_proxy_delta_vs_semantic_only_m"] = 0.0
            else:
                row["task_side_delta"] = None
                row["wrong_goal_visit_proxy_delta_vs_no_reobserve"] = None
                row["wrong_goal_visit_proxy_delta_vs_semantic_only"] = None
                row["wasted_path_proxy_delta_vs_no_reobserve_m"] = None
                row["wasted_path_proxy_delta_vs_semantic_only_m"] = None
            row["map_task_alignment"] = bool(label_join_available and map_delta > 0.0 and row["task_side_delta"] is not None)
            row["failure_tag"] = None
            row["failure_detail"] = None
            if policy == "SLAMOnlyRich_current":
                if not label_join_available:
                    row["failure_tag"] = "map_delta_not_task_aligned"
                    row["failure_detail"] = "task_proxy_label_join_missing"
                elif map_delta <= 0.0:
                    row["failure_tag"] = "no_independent_map_pose_delta"
                elif safe_int(diagnostic.get("saturated_term_count"), 0) >= 2:
                    row["failure_tag"] = "measurement_proxy_saturated"
            elif policy == "SemanticOnly" and diagnostic.get("blocker_class") == "semantic_wins_with_weak_map_pose_proxy":
                row["failure_tag"] = "semantic_score_dominance_persists"
            policy_rows[policy] = row
            probe_rows.append(row)

        slam_row = policy_rows["SLAMOnlyRich_current"]
        if slam_row.get("failure_tag"):
            failure_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "semantic_slam_task_map_outcome_probe",
                    "row_type": "semantic_slam_task_map_outcome_failure",
                    "join_key": key_data,
                    "source_name": key_data["source_name"],
                    "scene_key": key_data["scene_key"],
                    "query": key_data["query"],
                    "request_id": key_data["request_id"],
                    "episode_key": key_data["episode_key"],
                    "policy_name": "SLAMOnlyRich_current",
                    "failure_tag": slam_row.get("failure_tag"),
                    "failure_detail": slam_row.get("failure_detail"),
                    "map_side_delta": slam_row.get("map_side_delta"),
                    "pose_graph_connectivity_delta": slam_row.get("pose_graph_connectivity_delta"),
                    "map_pose_consistency_delta": slam_row.get("map_pose_consistency_delta"),
                    "label_join_available": label_join_available,
                    "task_proxy_evaluable": label_join_available,
                    "map_task_alignment": slam_row.get("map_task_alignment"),
                    "uses_gt_for_action": False,
                    "terminal_commit": False,
                    "candidate_commit": False,
                    "candidate_rejection": False,
                    "paper_claim_allowed": False,
                }
            )
    return probe_rows, failure_rows


def build_policy_summary_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    summary_rows: List[Dict[str, Any]] = []
    for policy in REQUIRED_POLICIES:
        policy_rows = [row for row in rows if row.get("policy_name") == policy]
        request_count = len(policy_rows)
        summary_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "semantic_slam_task_map_outcome_probe",
                "row_type": "semantic_slam_task_map_outcome_policy_summary",
                "policy_name": policy,
                "request_groups": request_count,
                "map_side_delta_stats": number_stats(row.get("map_side_delta") for row in policy_rows),
                "pose_graph_connectivity_delta_stats": number_stats(
                    row.get("pose_graph_connectivity_delta") for row in policy_rows
                ),
                "map_pose_consistency_delta_stats": number_stats(
                    row.get("map_pose_consistency_delta") for row in policy_rows
                ),
                "map_metric_positive_rows": sum(1 for row in policy_rows if (safe_float(row.get("map_side_delta"), 0.0) or 0.0) > 0.0),
                "task_proxy_evaluable_rows": sum(1 for row in policy_rows if row.get("task_proxy_evaluable") is True),
                "label_join_available_rows": sum(1 for row in policy_rows if row.get("label_join_available") is True),
                "label_free_risk_proxy_rows": sum(
                    1 for row in policy_rows if row.get("label_free_wrong_goal_risk_proxy") is not None
                ),
                "map_task_alignment_rows": sum(1 for row in policy_rows if row.get("map_task_alignment") is True),
                "failure_tag_counts": compact_counter(row.get("failure_tag") for row in policy_rows),
                "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in policy_rows),
                "terminal_commit_rows": sum(1 for row in policy_rows if row.get("terminal_commit") is True),
                "candidate_commit_rows": sum(1 for row in policy_rows if row.get("candidate_commit") is True),
                "candidate_rejection_rows": sum(1 for row in policy_rows if row.get("candidate_rejection") is True),
                "paper_claim_allowed": False,
            }
        )
    return summary_rows


def build_summary(
    *,
    contract: Mapping[str, Any],
    probe_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    underpowered_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    strict_edge_rows: Sequence[Mapping[str, Any]],
    out_root: Path,
    label_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    groups = {join_key(row) for row in underpowered_rows}
    required_policy_names = set(contract.get("minimum_success_gate_for_future_implementation", {}).get("required_policy_names") or REQUIRED_POLICIES)
    present_policy_names = {str(row.get("policy_name")) for row in probe_rows}
    slam_rows = [row for row in probe_rows if row.get("policy_name") == "SLAMOnlyRich_current"]
    gate_minimum = contract.get("minimum_success_gate_for_future_implementation") or {}
    map_metric_positive_rows = sum(1 for row in slam_rows if (safe_float(row.get("map_side_delta"), 0.0) or 0.0) > 0.0)
    task_proxy_evaluable_rows = sum(1 for row in slam_rows if row.get("task_proxy_evaluable") is True)
    label_join_available_rows = sum(1 for row in slam_rows if row.get("label_join_available") is True)
    label_free_risk_proxy_rows = sum(1 for row in slam_rows if row.get("label_free_wrong_goal_risk_proxy") is not None)
    map_task_alignment_rows = sum(1 for row in slam_rows if row.get("map_task_alignment") is True)
    forbidden_keys = action_forbidden_keys(probe_rows)
    terminal_commit_rows = sum(1 for row in probe_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in probe_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in probe_rows if row.get("candidate_rejection") is True)
    uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in probe_rows)
    paper_claim_allowed = any(row.get("paper_claim_allowed") is True for row in probe_rows)
    failure_taxonomy_counts = compact_counter(row.get("failure_tag") for row in failure_rows)
    secondary_failure_counts = compact_counter(row.get("failure_detail") for row in failure_rows)
    gate = {
        "same_request_groups_passed": len(groups) == safe_int(gate_minimum.get("request_groups"), len(groups)),
        "required_policies_passed": required_policy_names.issubset(present_policy_names),
        "map_metric_positive_rows_passed": map_metric_positive_rows >= safe_int(gate_minimum.get("map_metric_positive_rows_min"), 0),
        "task_proxy_evaluable_rows_passed": task_proxy_evaluable_rows >= safe_int(gate_minimum.get("task_proxy_evaluable_rows_min"), 0),
        "map_task_alignment_rows_passed": map_task_alignment_rows >= safe_int(gate_minimum.get("map_task_alignment_rows_min"), 0),
        "action_evidence_forbidden_keys_passed": len(forbidden_keys) == safe_int(
            gate_minimum.get("action_evidence_forbidden_key_count"), 0
        ),
        "terminal_commit_rows_passed": terminal_commit_rows == safe_int(gate_minimum.get("terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": candidate_commit_rows == safe_int(gate_minimum.get("candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": candidate_rejection_rows == safe_int(
            gate_minimum.get("candidate_rejection_rows"), 0
        ),
        "uses_gt_for_action_passed": uses_gt_for_action is bool(gate_minimum.get("uses_gt_for_action", False)),
        "paper_claim_allowed_passed": paper_claim_allowed is bool(gate_minimum.get("paper_claim_allowed", False)),
    }
    outcome_probe_gate_passed = all(gate.values())
    if task_proxy_evaluable_rows < safe_int(gate_minimum.get("task_proxy_evaluable_rows_min"), 0):
        primary_blocker = "task_proxy_label_join_missing"
        recommended_next_task = "freeze_label_backed_task_proxy_join_contract_before_revising_slam_only_rich"
    elif map_task_alignment_rows < safe_int(gate_minimum.get("map_task_alignment_rows_min"), 0):
        primary_blocker = "map_delta_not_task_aligned"
        recommended_next_task = "refine_task_map_alignment_metric_before_revising_slam_only_rich"
    elif map_metric_positive_rows < safe_int(gate_minimum.get("map_metric_positive_rows_min"), 0):
        primary_blocker = "no_independent_map_pose_delta"
        recommended_next_task = "refine_map_pose_metric_or_request_pool_before_revising_slam_only_rich"
    else:
        primary_blocker = None
        recommended_next_task = "revise_slam_only_rich_formula_under_frozen_outcome_gate"
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-05",
        "status": "completed_task_map_outcome_probe_gate_failed"
        if not outcome_probe_gate_passed
        else "completed_task_map_outcome_probe_gate_passed",
        "contract": str(CONTRACT_DEFAULT),
        "out_root": str(out_root),
        "output_files": {
            "probe_rows": "semantic_slam_task_map_outcome_probe_rows.jsonl",
            "policy_summary_rows": "semantic_slam_task_map_outcome_policy_summary_rows.jsonl",
            "failure_rows": "semantic_slam_task_map_outcome_failure_rows.jsonl",
            "summary": "semantic_slam_task_map_outcome_probe_summary.json",
        },
        "source_files": {
            "underpowered_rows": UNDERPOWERED_ROWS_DEFAULT,
            "request_rows": REQUEST_ROWS_DEFAULT,
            "strict_edge_rows": STRICT_EDGE_ROWS_DEFAULT,
            "task_label_rows": None if not label_rows else "provided_by_cli",
        },
        "request_groups": len(groups),
        "policy_count": len(present_policy_names),
        "present_policy_names": sorted(present_policy_names),
        "expected_probe_rows": len(groups) * len(REQUIRED_POLICIES),
        "probe_rows": len(probe_rows),
        "policy_summary_rows": len(REQUIRED_POLICIES),
        "failure_rows": len(failure_rows),
        "source_row_counts": {
            "underpowered_rows": len(underpowered_rows),
            "request_rows": len(request_rows),
            "strict_edge_variant_rows": len(strict_edge_rows),
            "task_label_rows": len(label_rows),
        },
        "map_metric_positive_rows": map_metric_positive_rows,
        "map_metric_positive_rate": ratio(map_metric_positive_rows, len(slam_rows)),
        "task_proxy_evaluable_rows": task_proxy_evaluable_rows,
        "task_proxy_evaluable_rate": ratio(task_proxy_evaluable_rows, len(slam_rows)),
        "label_join_available_rows": label_join_available_rows,
        "label_join_available_rate": ratio(label_join_available_rows, len(slam_rows)),
        "label_free_risk_proxy_rows": label_free_risk_proxy_rows,
        "label_free_risk_proxy_rate": ratio(label_free_risk_proxy_rows, len(slam_rows)),
        "map_task_alignment_rows": map_task_alignment_rows,
        "map_task_alignment_rate": ratio(map_task_alignment_rows, len(slam_rows)),
        "slam_independent_value_rows": map_metric_positive_rows,
        "failure_taxonomy_counts": failure_taxonomy_counts,
        "secondary_failure_counts": secondary_failure_counts,
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "action_evidence_forbidden_keys": forbidden_keys,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": uses_gt_for_action,
        "paper_claim_allowed": paper_claim_allowed,
        "outcome_probe_gate_passed": outcome_probe_gate_passed,
        "revised_slam_formula_allowed": outcome_probe_gate_passed,
        "step_4_5_promotion_satisfied": False,
        "gate": gate,
        "primary_blocker": primary_blocker,
        "recommended_next_task": recommended_next_task,
        "interpretation": {
            "fact": "The same request groups, strict map/pose proxy rows, and underpowered SLAM diagnostic rows can be joined without action-time GT labels.",
            "agent_inference": "Current artifacts are enough to show independent map-side deltas, but not enough to validate task-side wrong-goal or wasted-path outcome deltas.",
            "paper_claim": "No ObjectNav, SLAM, SemanticSLAM complementarity, or revised SLAMOnlyRich formula claim is allowed from this failed gate.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate the frozen SemanticSLAM task/map outcome probe.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--underpowered-rows", default=UNDERPOWERED_ROWS_DEFAULT)
    parser.add_argument("--request-rows", default=REQUEST_ROWS_DEFAULT)
    parser.add_argument("--strict-edge-rows", default=STRICT_EDGE_ROWS_DEFAULT)
    parser.add_argument("--task-label-rows", default=None)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(Path(args.contract))
    underpowered_rows = load_jsonl(Path(args.underpowered_rows))
    request_rows = load_jsonl(Path(args.request_rows))
    strict_edge_rows = load_jsonl(Path(args.strict_edge_rows))
    label_rows = load_jsonl(Path(args.task_label_rows)) if args.task_label_rows else []
    request_index = index_by_key(request_rows)
    variant_index_map = index_variants(strict_edge_rows)
    label_index_map = task_label_index(label_rows)
    probe_rows, failure_rows = build_probe_rows(
        contract=contract,
        diagnostics=underpowered_rows,
        request_index=request_index,
        variant_index_map=variant_index_map,
        label_index_map=label_index_map,
    )
    policy_summary_rows = build_policy_summary_rows(probe_rows)
    out_root = Path(args.out_root)
    summary = build_summary(
        contract=contract,
        probe_rows=probe_rows,
        failure_rows=failure_rows,
        underpowered_rows=underpowered_rows,
        request_rows=request_rows,
        strict_edge_rows=strict_edge_rows,
        out_root=out_root,
        label_rows=label_rows,
    )
    write_jsonl(out_root / "semantic_slam_task_map_outcome_probe_rows.jsonl", probe_rows)
    write_jsonl(out_root / "semantic_slam_task_map_outcome_policy_summary_rows.jsonl", policy_summary_rows)
    write_jsonl(out_root / "semantic_slam_task_map_outcome_failure_rows.jsonl", failure_rows)
    write_json(out_root / "semantic_slam_task_map_outcome_probe_summary.json", summary)


if __name__ == "__main__":
    main()
