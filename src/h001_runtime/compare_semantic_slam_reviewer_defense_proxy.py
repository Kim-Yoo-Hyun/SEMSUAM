import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_reviewer_defense.v1"
POLICY_NAME = "semantic_slam_reviewer_defense_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_reviewer_defense_contract_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_reviewer_defense_v1"

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


def join_key(row: Mapping[str, Any], keys: Sequence[str]) -> Tuple[str, ...]:
    return tuple(str(row.get(key) or "") for key in keys)


def mean_from_stats(value: Any) -> Optional[float]:
    if isinstance(value, Mapping):
        return safe_float(value.get("mean"))
    return safe_float(value)


def policy_names(contract: Mapping[str, Any]) -> List[str]:
    return [str(item.get("policy_name")) for item in contract.get("policy_definitions") or []]


def group_request_rows(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Dict[Tuple[str, ...], Mapping[str, Any]]:
    grouped: Dict[Tuple[str, ...], Mapping[str, Any]] = {}
    for row in rows:
        grouped[join_key(row, keys)] = row
    return grouped


def variant_index(rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> Dict[Tuple[Tuple[str, ...], str], Mapping[str, Any]]:
    index: Dict[Tuple[Tuple[str, ...], str], Mapping[str, Any]] = {}
    for row in rows:
        index[(join_key(row, keys), str(row.get("edge_variant") or ""))] = row
    return index


def base_group_features(
    *,
    key: Tuple[str, ...],
    keys: Sequence[str],
    request_row: Mapping[str, Any],
    variants: Mapping[str, Mapping[str, Any]],
    semantic_weights: Mapping[str, Any],
    max_travel_mean: float,
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
    context_edge_count = safe_int(context.get("edge_count"), 0)
    loop_edge_count = safe_int(loop.get("edge_count"), 0)
    shortcut_edge_count = safe_int(shortcut.get("edge_count"), 0)
    connected_component_count = safe_int(canonical.get("connected_component_count"), 0)
    largest_component_fraction = safe_float(canonical.get("largest_component_fraction"), 0.0) or 0.0
    unique_viewpoint_count = safe_int(request_row.get("unique_viewpoint_count"), 0)

    fragmentation_score = clip((connected_component_count - 1) / 4.0)
    largest_component_gap = clip(1.0 - largest_component_fraction)
    loop_gap = 1.0 if loop_edge_count <= 0 else 0.0
    source_coverage_gap = clip(1.0 - min(unique_viewpoint_count / 4.0, 1.0))
    context_gap = clip(1.0 - (context_edge_count / max(canonical_edge_count, 1)))
    map_pose_outcome_proxy = (
        0.30 * fragmentation_score
        + 0.25 * largest_component_gap
        + 0.20 * loop_gap
        + 0.15 * source_coverage_gap
        + 0.10 * context_gap
    )

    semantic_pressure = clip((semantic_score - 0.55) / 0.35)
    map_pose_pressure = clip(map_pose_outcome_proxy / 0.8)
    explanation_terms = {
        "fragmentation_score": fragmentation_score,
        "largest_component_gap": largest_component_gap,
        "loop_gap": loop_gap,
        "source_coverage_gap": source_coverage_gap,
        "context_gap": context_gap,
    }
    map_pose_explanation_gate = map_pose_pressure >= 0.25 and any(value >= 0.25 for value in explanation_terms.values())
    raw_interaction_gain = 0.30 * semantic_pressure * map_pose_pressure * map_pose_outcome_proxy
    interaction_gain = raw_interaction_gain if map_pose_explanation_gate else 0.0

    semantic_only_utility = semantic_score - travel_penalty
    slam_only_rich_utility = map_pose_outcome_proxy - travel_penalty
    raw_guarded_utility = semantic_only_utility + interaction_gain
    non_shadowing_cap = semantic_only_utility + 0.75 * max(0.0, slam_only_rich_utility - semantic_only_utility) + interaction_gain
    guarded_utility = min(raw_guarded_utility, non_shadowing_cap)
    component_max_utility = max(semantic_only_utility, slam_only_rich_utility)

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
        "unique_viewpoint_count": unique_viewpoint_count,
        "frame_row_count": safe_int(request_row.get("frame_row_count"), 0),
        "semantic_score": semantic_score,
        "fragmentation_score": fragmentation_score,
        "largest_component_gap": largest_component_gap,
        "loop_gap": loop_gap,
        "source_coverage_gap": source_coverage_gap,
        "context_gap": context_gap,
        "map_pose_outcome_proxy": map_pose_outcome_proxy,
        "semantic_pressure": semantic_pressure,
        "map_pose_pressure": map_pose_pressure,
        "map_pose_explanation_gate": map_pose_explanation_gate,
        "raw_interaction_gain": raw_interaction_gain,
        "interaction_gain": interaction_gain,
        "semantic_only_utility": semantic_only_utility,
        "slam_only_rich_utility": slam_only_rich_utility,
        "raw_guarded_utility": raw_guarded_utility,
        "non_shadowing_cap": non_shadowing_cap,
        "guarded_utility": guarded_utility,
        "component_max_utility": component_max_utility,
        "travel_cost_proxy_m_mean": travel_mean,
        "normalized_travel_cost_proxy": normalized_travel,
        "travel_penalty": travel_penalty,
        "canonical_proxy_ready": canonical.get("proxy_ready") is True,
        "canonical_edge_count": canonical_edge_count,
        "canonical_connected_component_count": connected_component_count,
        "canonical_largest_component_fraction": largest_component_fraction,
        "canonical_mean_degree": safe_float(canonical.get("mean_degree"), 0.0) or 0.0,
        "loop_edge_count": loop_edge_count,
        "context_edge_count": context_edge_count,
        "candidate_overlap_only_edge_count": shortcut_edge_count,
        "candidate_overlap_used_as_pose_evidence": False,
        "uses_gt_for_action": request_row.get("uses_gt_for_action") is True
        or any(row.get("uses_gt_for_action") is True for row in variants.values()),
    }


def policy_row(policy_name: str, base: Mapping[str, Any]) -> Dict[str, Any]:
    semantic_score = safe_float(base.get("semantic_score"), 0.0) or 0.0
    map_pose_proxy = safe_float(base.get("map_pose_outcome_proxy"), 0.0) or 0.0
    semantic_pressure = safe_float(base.get("semantic_pressure"), 0.0) or 0.0
    map_pose_pressure = safe_float(base.get("map_pose_pressure"), 0.0) or 0.0
    interaction_gain = safe_float(base.get("interaction_gain"), 0.0) or 0.0
    travel_penalty = safe_float(base.get("travel_penalty"), 0.0) or 0.0
    semantic_only_utility = safe_float(base.get("semantic_only_utility"), 0.0) or 0.0
    slam_only_rich_utility = safe_float(base.get("slam_only_rich_utility"), 0.0) or 0.0
    component_max_utility = safe_float(base.get("component_max_utility"), 0.0) or 0.0
    map_pose_gate = base.get("map_pose_explanation_gate") is True
    uses_semantic = policy_name in {"SemanticOnly", "SemanticSLAMInteractionGuarded"}
    uses_slam = policy_name in {"SLAMOnlyRich", "SemanticSLAMInteractionGuarded"}
    if policy_name == "NoReobserveReference":
        utility = 0.0
        row_semantic_score = 0.0
        row_map_pose_proxy = 0.0
        row_semantic_pressure = 0.0
        row_map_pose_pressure = 0.0
        row_interaction_gain = 0.0
        row_travel_penalty = 0.0
    elif policy_name == "SemanticOnly":
        utility = semantic_only_utility
        row_semantic_score = semantic_score
        row_map_pose_proxy = 0.0
        row_semantic_pressure = semantic_pressure
        row_map_pose_pressure = 0.0
        row_interaction_gain = 0.0
        row_travel_penalty = travel_penalty
    elif policy_name == "SLAMOnlyRich":
        utility = slam_only_rich_utility
        row_semantic_score = 0.0
        row_map_pose_proxy = map_pose_proxy
        row_semantic_pressure = 0.0
        row_map_pose_pressure = map_pose_pressure
        row_interaction_gain = 0.0
        row_travel_penalty = travel_penalty
    elif policy_name == "SemanticSLAMInteractionGuarded":
        utility = safe_float(base.get("guarded_utility"), 0.0) or 0.0
        row_semantic_score = semantic_score
        row_map_pose_proxy = map_pose_proxy
        row_semantic_pressure = semantic_pressure
        row_map_pose_pressure = map_pose_pressure
        row_interaction_gain = interaction_gain
        row_travel_penalty = travel_penalty
    else:
        utility = 0.0
        row_semantic_score = 0.0
        row_map_pose_proxy = 0.0
        row_semantic_pressure = 0.0
        row_map_pose_pressure = 0.0
        row_interaction_gain = 0.0
        row_travel_penalty = 0.0
    interaction_gain_over_semantic = utility - semantic_only_utility
    unexplained_positive_bonus = (
        policy_name == "SemanticSLAMInteractionGuarded"
        and interaction_gain_over_semantic > 1e-9
        and not map_pose_gate
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_semantic_slam_reviewer_defense_proxy",
        "row_type": "semantic_slam_reviewer_defense",
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
        "unique_viewpoint_count": base.get("unique_viewpoint_count"),
        "frame_row_count": base.get("frame_row_count"),
        "semantic_score": row_semantic_score,
        "map_pose_outcome_proxy": row_map_pose_proxy,
        "fragmentation_score": base.get("fragmentation_score"),
        "largest_component_gap": base.get("largest_component_gap"),
        "loop_gap": base.get("loop_gap"),
        "source_coverage_gap": base.get("source_coverage_gap"),
        "context_gap": base.get("context_gap"),
        "semantic_pressure": row_semantic_pressure,
        "map_pose_pressure": row_map_pose_pressure,
        "map_pose_explanation_gate": map_pose_gate,
        "raw_interaction_gain": base.get("raw_interaction_gain"),
        "interaction_gain": row_interaction_gain,
        "non_shadowing_cap": base.get("non_shadowing_cap"),
        "non_shadowing_cap_active": policy_name == "SemanticSLAMInteractionGuarded"
        and (safe_float(base.get("raw_guarded_utility"), 0.0) or 0.0) > utility + 1e-9,
        "travel_penalty": row_travel_penalty,
        "policy_proxy_utility": utility,
        "utility_rank_score_only": None,
        "uses_semantic_channel_for_utility": uses_semantic,
        "uses_slam_channel_for_utility": uses_slam,
        "semantic_only_utility": semantic_only_utility,
        "slam_only_rich_utility": slam_only_rich_utility,
        "component_max_utility": component_max_utility,
        "interaction_gain_over_semantic": interaction_gain_over_semantic,
        "interaction_margin_over_component": utility - component_max_utility,
        "semantic_only_shadowed_by_interaction": policy_name == "SemanticSLAMInteractionGuarded"
        and utility > semantic_only_utility + 1e-9,
        "map_pose_explained_interaction": policy_name == "SemanticSLAMInteractionGuarded"
        and interaction_gain_over_semantic > 1e-9
        and map_pose_gate,
        "unexplained_positive_bonus": unexplained_positive_bonus,
        "component_max_shortcut_used": False,
        "candidate_overlap_used_as_pose_evidence": False,
        "canonical_proxy_ready": base.get("canonical_proxy_ready"),
        "canonical_edge_count": base.get("canonical_edge_count"),
        "canonical_connected_component_count": base.get("canonical_connected_component_count"),
        "canonical_largest_component_fraction": base.get("canonical_largest_component_fraction"),
        "canonical_mean_degree": base.get("canonical_mean_degree"),
        "loop_edge_count": base.get("loop_edge_count"),
        "context_edge_count": base.get("context_edge_count"),
        "candidate_overlap_only_edge_count": base.get("candidate_overlap_only_edge_count"),
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
        "row_type": "semantic_slam_reviewer_defense_policy_summary",
        "policy": POLICY_NAME,
        "policy_name": policy_name_value,
        "policy_rows": len(subset),
        "request_groups": len(unique_groups),
        "policy_proxy_utility_stats": number_stats(row.get("policy_proxy_utility") for row in subset),
        "semantic_score_stats": number_stats(row.get("semantic_score") for row in subset),
        "map_pose_outcome_proxy_stats": number_stats(row.get("map_pose_outcome_proxy") for row in subset),
        "fragmentation_score_stats": number_stats(row.get("fragmentation_score") for row in subset),
        "largest_component_gap_stats": number_stats(row.get("largest_component_gap") for row in subset),
        "loop_gap_stats": number_stats(row.get("loop_gap") for row in subset),
        "source_coverage_gap_stats": number_stats(row.get("source_coverage_gap") for row in subset),
        "context_gap_stats": number_stats(row.get("context_gap") for row in subset),
        "semantic_pressure_stats": number_stats(row.get("semantic_pressure") for row in subset),
        "map_pose_pressure_stats": number_stats(row.get("map_pose_pressure") for row in subset),
        "interaction_gain_stats": number_stats(row.get("interaction_gain") for row in subset),
        "travel_penalty_stats": number_stats(row.get("travel_penalty") for row in subset),
        "interaction_margin_over_component_stats": number_stats(
            row.get("interaction_margin_over_component") for row in subset
        ),
        "canonical_proxy_ready_rate": ratio(sum(1 for row in subset if row.get("canonical_proxy_ready") is True), len(subset)),
        "loop_edge_availability_rate": ratio(sum(1 for row in subset if safe_int(row.get("loop_edge_count"), 0) > 0), len(subset)),
        "rank1_rows": sum(1 for row in subset if row.get("utility_rank_score_only") == 1),
        "rank1_rate": ratio(sum(1 for row in subset if row.get("utility_rank_score_only") == 1), len(subset)),
        "semantic_only_shadowed_by_interaction_rows": sum(
            1 for row in subset if row.get("semantic_only_shadowed_by_interaction") is True
        ),
        "semantic_only_shadowed_by_interaction_rate": ratio(
            sum(1 for row in subset if row.get("semantic_only_shadowed_by_interaction") is True), len(subset)
        ),
        "map_pose_explained_interaction_rows": sum(1 for row in subset if row.get("map_pose_explained_interaction") is True),
        "unexplained_positive_bonus_rows": sum(1 for row in subset if row.get("unexplained_positive_bonus") is True),
        "component_max_shortcut_rows": sum(1 for row in subset if row.get("component_max_shortcut_used") is True),
        "candidate_overlap_pose_evidence_rows": sum(
            1 for row in subset if row.get("candidate_overlap_used_as_pose_evidence") is True
        ),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in subset),
        "terminal_commit_rows": sum(1 for row in subset if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in subset if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in subset if row.get("candidate_rejection") is True),
        "paper_claim_allowed": False,
    }


def diagnostic_rows(comparison_rows: Sequence[Mapping[str, Any]], keys: Sequence[str]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]] = {}
    for row in comparison_rows:
        grouped.setdefault(join_key(row, keys), {})[str(row.get("policy_name") or "")] = row
    rows: List[Dict[str, Any]] = []
    for _key, policies in sorted(grouped.items()):
        semantic = policies.get("SemanticOnly") or {}
        slam = policies.get("SLAMOnlyRich") or {}
        interaction = policies.get("SemanticSLAMInteractionGuarded") or {}
        semantic_utility = safe_float(semantic.get("policy_proxy_utility"), 0.0) or 0.0
        slam_utility = safe_float(slam.get("policy_proxy_utility"), 0.0) or 0.0
        interaction_utility = safe_float(interaction.get("policy_proxy_utility"), 0.0) or 0.0
        component_max = max(semantic_utility, slam_utility)
        if semantic_utility > slam_utility:
            component_winner = "SemanticOnly"
        elif slam_utility > semantic_utility:
            component_winner = "SLAMOnlyRich"
        else:
            component_winner = "tie"
        shadowed = interaction_utility > semantic_utility + 1e-9
        unexplained = interaction.get("unexplained_positive_bonus") is True
        map_pose_explained = interaction.get("map_pose_explained_interaction") is True
        if not semantic or not slam or not interaction:
            diagnostic_class = "incomplete_policy_group"
        elif unexplained:
            diagnostic_class = "unexplained_positive_bonus"
        elif interaction_utility <= component_max + 1e-9:
            diagnostic_class = "interaction_loses_to_component"
        elif component_winner == "SemanticOnly" and shadowed and map_pose_explained:
            diagnostic_class = "semantic_shadowed_with_map_pose_explanation"
        elif component_winner == "SLAMOnlyRich" and map_pose_explained:
            diagnostic_class = "interaction_overrides_slam_with_map_pose_explanation"
        else:
            diagnostic_class = "interaction_non_dominated_other"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "semantic_slam_reviewer_defense_diagnostic",
                "policy": POLICY_NAME,
                "join_key": interaction.get("join_key") or semantic.get("join_key") or slam.get("join_key"),
                "source_name": interaction.get("source_name") or semantic.get("source_name") or slam.get("source_name"),
                "scene_key": interaction.get("scene_key") or semantic.get("scene_key") or slam.get("scene_key"),
                "query": interaction.get("query") or semantic.get("query") or slam.get("query"),
                "request_id": interaction.get("request_id") or semantic.get("request_id") or slam.get("request_id"),
                "episode_key": interaction.get("episode_key") or semantic.get("episode_key") or slam.get("episode_key"),
                "semantic_uncertainty_family": interaction.get("semantic_uncertainty_family")
                or semantic.get("semantic_uncertainty_family")
                or slam.get("semantic_uncertainty_family"),
                "component_winner": component_winner,
                "diagnostic_class": diagnostic_class,
                "semantic_only_utility": semantic_utility,
                "slam_only_rich_utility": slam_utility,
                "semantic_slam_interaction_guarded_utility": interaction_utility,
                "component_max_utility": component_max,
                "interaction_margin_over_component": interaction_utility - component_max,
                "semantic_only_shadowed_by_interaction": shadowed,
                "map_pose_explained_interaction": map_pose_explained,
                "unexplained_positive_bonus": unexplained,
                "semantic_rank": safe_int(semantic.get("utility_rank_score_only"), 0),
                "slam_rank": safe_int(slam.get("utility_rank_score_only"), 0),
                "interaction_rank": safe_int(interaction.get("utility_rank_score_only"), 0),
                "semantic_score": safe_float(interaction.get("semantic_score"), 0.0) or 0.0,
                "map_pose_outcome_proxy": safe_float(interaction.get("map_pose_outcome_proxy"), 0.0) or 0.0,
                "fragmentation_score": safe_float(interaction.get("fragmentation_score"), 0.0) or 0.0,
                "largest_component_gap": safe_float(interaction.get("largest_component_gap"), 0.0) or 0.0,
                "loop_gap": safe_float(interaction.get("loop_gap"), 0.0) or 0.0,
                "source_coverage_gap": safe_float(interaction.get("source_coverage_gap"), 0.0) or 0.0,
                "context_gap": safe_float(interaction.get("context_gap"), 0.0) or 0.0,
                "semantic_pressure": safe_float(interaction.get("semantic_pressure"), 0.0) or 0.0,
                "map_pose_pressure": safe_float(interaction.get("map_pose_pressure"), 0.0) or 0.0,
                "map_pose_explanation_gate": interaction.get("map_pose_explanation_gate") is True,
                "interaction_gain": safe_float(interaction.get("interaction_gain"), 0.0) or 0.0,
                "canonical_proxy_ready": interaction.get("canonical_proxy_ready") is True,
                "loop_edge_available": safe_int(interaction.get("loop_edge_count"), 0) > 0,
                "component_max_shortcut_used": interaction.get("component_max_shortcut_used") is True,
                "candidate_overlap_used_as_pose_evidence": interaction.get("candidate_overlap_used_as_pose_evidence") is True,
                "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in policies.values()),
                "paper_claim_allowed": False,
                "step_4_5_promotion_satisfied": False,
            }
        )
    return rows


def build_rows(contract: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    source = contract.get("source") or {}
    scope = contract.get("reviewer_defense_scope") or {}
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
        )
        for policy in policy_names(contract):
            rows.append(policy_row(policy, base))
    add_ranks(rows, keys)
    diagnostics = {
        "request_group_count": len(all_group_keys),
        "max_travel_cost_proxy_m_mean": max_travel_mean,
        "missing_variant_rows": missing_variant_rows[:20],
        "missing_variant_row_count": len(missing_variant_rows),
    }
    return rows, diagnostics


def build_summary(
    *,
    contract: Mapping[str, Any],
    comparison_rows: Sequence[Mapping[str, Any]],
    policy_summary_rows: Sequence[Mapping[str, Any]],
    diagnostic_rows_value: Sequence[Mapping[str, Any]],
    diagnostics: Mapping[str, Any],
    out_root: Path,
) -> Dict[str, Any]:
    scope = contract.get("reviewer_defense_scope") or {}
    thresholds = contract.get("gate_thresholds") or {}
    keys = [str(key) for key in scope.get("join_key") or []]
    forbidden_keys = action_forbidden_keys(list(comparison_rows) + list(policy_summary_rows) + list(diagnostic_rows_value))
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
    slam_only = next((row for row in policy_summary_rows if row.get("policy_name") == "SLAMOnlyRich"), {})
    interaction = next((row for row in policy_summary_rows if row.get("policy_name") == "SemanticSLAMInteractionGuarded"), {})
    interaction_rank1_rows = safe_int(interaction.get("rank1_rows"), 0)
    interaction_rank1_rate = safe_float(interaction.get("rank1_rate"), 0.0) or 0.0
    semantic_shadow_rows = safe_int(interaction.get("semantic_only_shadowed_by_interaction_rows"), 0)
    semantic_shadow_rate = safe_float(interaction.get("semantic_only_shadowed_by_interaction_rate"), 0.0) or 0.0
    map_pose_explained_rows = safe_int(interaction.get("map_pose_explained_interaction_rows"), 0)
    unexplained_positive_bonus_rows = safe_int(interaction.get("unexplained_positive_bonus_rows"), 0)
    component_max_shortcut_rows = sum(1 for row in diagnostic_rows_value if row.get("component_max_shortcut_used") is True)
    candidate_overlap_pose_evidence_rows = sum(
        1 for row in diagnostic_rows_value if row.get("candidate_overlap_used_as_pose_evidence") is True
    )
    component_reference_rank1_rows = sum(
        safe_int(row.get("rank1_rows"), 0)
        for row in policy_summary_rows
        if row.get("policy_name") in {"SemanticOnly", "SLAMOnlyRich"}
    )
    map_pose_positive_rows = sum(1 for row in diagnostic_rows_value if (safe_float(row.get("map_pose_outcome_proxy"), 0.0) or 0.0) > 1e-9)
    comparison_gate = {
        "policy_count_passed": len(policy_set) == expected_policy_count,
        "request_group_count_passed": len(request_groups) == expected_request_groups,
        "comparison_row_count_passed": len(comparison_rows) == expected_rows,
        "diagnostic_row_count_passed": len(diagnostic_rows_value) == expected_request_groups,
        "same_request_groups_gate_passed": same_request_groups,
        "canonical_proxy_ready_rate_passed": safe_float(semantic_only.get("canonical_proxy_ready_rate"), 0.0)
        >= safe_float(thresholds.get("min_canonical_proxy_ready_rate"), 0.0),
        "loop_proxy_ready_rate_passed": safe_float(slam_only.get("loop_edge_availability_rate"), 0.0)
        >= safe_float(thresholds.get("min_loop_proxy_ready_rate"), 0.0),
        "missing_variant_rows_passed": safe_int(diagnostics.get("missing_variant_row_count"), 0) == 0,
    }
    reviewer_defense_gate = {
        "component_max_shortcut_rows_passed": component_max_shortcut_rows
        <= safe_int(thresholds.get("max_component_max_shortcut_rows"), 0),
        "candidate_overlap_pose_evidence_rows_passed": candidate_overlap_pose_evidence_rows
        <= safe_int(thresholds.get("max_candidate_overlap_pose_evidence_rows"), 0),
        "unexplained_positive_bonus_rows_passed": unexplained_positive_bonus_rows
        <= safe_int(thresholds.get("max_unexplained_positive_bonus_rows"), 0),
        "semantic_only_shadow_rate_passed": semantic_shadow_rate
        <= (safe_float(thresholds.get("max_semantic_only_shadowed_by_interaction_rate_without_outcome"), 1.0) or 1.0),
        "interaction_rank1_rate_passed": interaction_rank1_rate
        <= (safe_float(thresholds.get("max_interaction_rank1_rate_without_outcome"), 1.0) or 1.0),
        "map_pose_explained_interaction_rows_passed": map_pose_explained_rows
        >= safe_int(thresholds.get("min_map_pose_explained_interaction_rows"), 0),
        "slam_only_rich_rank1_rows_passed": safe_int(slam_only.get("rank1_rows"), 0)
        >= safe_int(thresholds.get("min_slam_only_rich_rank1_rows"), 0),
        "component_reference_rank1_rows_passed": component_reference_rank1_rows
        >= safe_int(thresholds.get("min_component_reference_rank1_rows"), 0),
        "map_pose_outcome_proxy_positive_rows_passed": map_pose_positive_rows
        >= safe_int(thresholds.get("min_map_pose_outcome_proxy_positive_rows"), 0),
    }
    action_safety_gate = {
        "action_evidence_forbidden_key_gate_passed": len(forbidden_keys)
        <= safe_int(thresholds.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": sum(1 for row in comparison_rows if row.get("terminal_commit") is True)
        <= safe_int(thresholds.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": sum(1 for row in comparison_rows if row.get("candidate_commit") is True)
        <= safe_int(thresholds.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": sum(1 for row in comparison_rows if row.get("candidate_rejection") is True)
        <= safe_int(thresholds.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": (
            any(row.get("uses_gt_for_action") is True for row in comparison_rows)
            is bool(thresholds.get("requires_uses_gt_for_action", False))
        ),
    }
    comparison_gate["comparison_gate_passed"] = all(comparison_gate.values())
    reviewer_defense_gate["reviewer_defense_gate_passed"] = all(reviewer_defense_gate.values())
    action_safety_gate["action_safety_gate_passed"] = all(action_safety_gate.values())
    gate_passed = (
        comparison_gate["comparison_gate_passed"]
        and reviewer_defense_gate["reviewer_defense_gate_passed"]
        and action_safety_gate["action_safety_gate_passed"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-05",
        "status": "implemented_and_docker_verified_semantic_slam_reviewer_defense_proxy",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "comparison_rows": "semantic_slam_reviewer_defense_rows.jsonl",
            "policy_summary_rows": "semantic_slam_reviewer_defense_policy_summary_rows.jsonl",
            "diagnostic_rows": "semantic_slam_reviewer_defense_diagnostic_rows.jsonl",
            "summary": "semantic_slam_reviewer_defense_summary.json",
        },
        "policy_rows": len(comparison_rows),
        "policy_summary_rows": len(policy_summary_rows),
        "diagnostic_rows": len(diagnostic_rows_value),
        "request_groups": len(request_groups),
        "policy_count": len(policy_set),
        "policies": sorted(policy_set),
        "same_request_groups_gate": same_request_groups,
        "policy_proxy_utility_stats": {
            row.get("policy_name"): row.get("policy_proxy_utility_stats") for row in policy_summary_rows
        },
        "policy_rank1_rows": {row.get("policy_name"): row.get("rank1_rows") for row in policy_summary_rows},
        "policy_rank1_rates": {row.get("policy_name"): row.get("rank1_rate") for row in policy_summary_rows},
        "diagnostic_class_counts": compact_counter(row.get("diagnostic_class") for row in diagnostic_rows_value),
        "component_winner_counts": compact_counter(row.get("component_winner") for row in diagnostic_rows_value),
        "semantic_only_shadowed_by_interaction_rows": semantic_shadow_rows,
        "semantic_only_shadowed_by_interaction_rate": semantic_shadow_rate,
        "interaction_rank1_rows": interaction_rank1_rows,
        "interaction_rank1_rate": interaction_rank1_rate,
        "map_pose_explained_interaction_rows": map_pose_explained_rows,
        "map_pose_explained_interaction_rate": ratio(map_pose_explained_rows, len(diagnostic_rows_value)),
        "unexplained_positive_bonus_rows": unexplained_positive_bonus_rows,
        "component_max_shortcut_rows": component_max_shortcut_rows,
        "candidate_overlap_pose_evidence_rows": candidate_overlap_pose_evidence_rows,
        "component_reference_rank1_rows": component_reference_rank1_rows,
        "map_pose_outcome_proxy_positive_rows": map_pose_positive_rows,
        "map_pose_outcome_proxy_stats": number_stats(row.get("map_pose_outcome_proxy") for row in diagnostic_rows_value),
        "fragmentation_score_stats": number_stats(row.get("fragmentation_score") for row in diagnostic_rows_value),
        "largest_component_gap_stats": number_stats(row.get("largest_component_gap") for row in diagnostic_rows_value),
        "loop_gap_stats": number_stats(row.get("loop_gap") for row in diagnostic_rows_value),
        "source_coverage_gap_stats": number_stats(row.get("source_coverage_gap") for row in diagnostic_rows_value),
        "context_gap_stats": number_stats(row.get("context_gap") for row in diagnostic_rows_value),
        "interaction_gain_stats": number_stats(row.get("interaction_gain") for row in diagnostic_rows_value),
        "interaction_margin_over_component_stats": number_stats(
            row.get("interaction_margin_over_component") for row in diagnostic_rows_value
        ),
        "canonical_proxy_ready_rate": ratio(
            sum(1 for row in diagnostic_rows_value if row.get("canonical_proxy_ready") is True),
            len(diagnostic_rows_value),
        ),
        "loop_edge_availability_rate": ratio(
            sum(1 for row in diagnostic_rows_value if row.get("loop_edge_available") is True),
            len(diagnostic_rows_value),
        ),
        "action_evidence_forbidden_keys": forbidden_keys,
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": sum(1 for row in comparison_rows if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in comparison_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in comparison_rows if row.get("candidate_rejection") is True),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in comparison_rows),
        "gate": {
            "comparison": comparison_gate,
            "reviewer_defense": reviewer_defense_gate,
            "action_safety": action_safety_gate,
            "semantic_slam_reviewer_defense_gate_passed": gate_passed,
        },
        "step_4_5_promotion_satisfied": False,
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "diagnostic_conclusion": {
            "proxy_gate_passed": gate_passed,
            "recommended_next_task": "evaluate_richer_slam_reviewer_defense_output_before_step_4_5_promotion",
            "step_4_5_promotion_allowed": False,
            "terminal_policy_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": {
            "fact": "SemanticSLAMInteractionGuarded uses map/pose explanation terms and a non-shadowing guard defined by the frozen reviewer-defense contract.",
            "agent_inference": "If the gate passes, the proxy avoids the previous all-row SemanticOnly shadowing failure and can be evaluated as a stricter P4-design diagnostic, but it is still not task or SLAM benefit evidence.",
            "paper_claim": "No SemanticSLAM complementarity, ObjectNav benefit, or SLAM benefit claim is allowed from this proxy output alone.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()
    contract = load_json(Path(args.contract))
    out_root = Path(args.out_root)
    comparison_rows, diagnostics = build_rows(contract)
    keys = [str(key) for key in (contract.get("reviewer_defense_scope") or {}).get("join_key") or []]
    policy_summary_rows = [policy_summary(comparison_rows, policy, keys) for policy in policy_names(contract)]
    diagnostic_rows_value = diagnostic_rows(comparison_rows, keys)
    summary = build_summary(
        contract=contract,
        comparison_rows=comparison_rows,
        policy_summary_rows=policy_summary_rows,
        diagnostic_rows_value=diagnostic_rows_value,
        diagnostics=diagnostics,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_reviewer_defense_rows.jsonl", comparison_rows)
    write_jsonl(out_root / "semantic_slam_reviewer_defense_policy_summary_rows.jsonl", policy_summary_rows)
    write_jsonl(out_root / "semantic_slam_reviewer_defense_diagnostic_rows.jsonl", diagnostic_rows_value)
    write_json(out_root / "semantic_slam_reviewer_defense_summary.json", summary)


if __name__ == "__main__":
    main()
