import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    distance_stats,
    group_by_request,
    horizontal_distance,
    load_json,
    load_jsonl,
    number_stats,
    ratio,
    request_sort_key,
    row_request_id,
    safe_float,
    safe_int,
    visual_support_score,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_relation_spatial_context.v1"
ANCHOR_ROLES = [
    "source_top_candidate",
    "nearest_spatial_rival",
    "nearest_higher_score_rival",
    "nearest_positive_support_rival",
    "strongest_positive_support_rival",
]


class UnionFind:
    def __init__(self, items: Sequence[str]) -> None:
        self.parent = {item: item for item in items}

    def find(self, item: str) -> str:
        parent = self.parent[item]
        if parent != item:
            self.parent[item] = self.find(parent)
        return self.parent[item]

    def union(self, a: str, b: str) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a != root_b:
            self.parent[root_b] = root_a


def role_tokens(role: Any) -> List[str]:
    return [token for token in str(role or "").split("+") if token]


def role_has(role: Any, token: str) -> bool:
    return token in set(role_tokens(role))


def role_index(plan_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in plan_rows:
        request_id = row_request_id(row)
        cid = str(row.get("target_candidate_id") or row.get("candidate_id") or "")
        if not request_id or not cid:
            continue
        indexed.setdefault(
            (request_id, cid),
            {
                "target_candidate_role": row.get("target_candidate_role"),
                "goal_validity_rival_candidate_ids": row.get("goal_validity_rival_candidate_ids") or [],
                "goal_validity_context_candidate_ids": row.get("goal_validity_context_candidate_ids") or [],
                "viewpoint_source": row.get("viewpoint_source"),
                "standoff_distance_requested": row.get("standoff_distance_requested"),
                "standoff_target_horizontal_distance": row.get("standoff_target_horizontal_distance"),
            },
        )
    return indexed


def candidate_sort_key(row: Dict[str, Any]) -> Tuple[int, int, str]:
    return (
        safe_int(row.get("target_generated_rank"), 999999),
        safe_int(row.get("target_semantic_rank"), 999999),
        candidate_id(row),
    )


def finite_distance(a: Any, b: Any) -> Optional[float]:
    value = horizontal_distance(a, b)
    return value if value is not None and math.isfinite(value) else None


def build_components(
    request_rows: Sequence[Dict[str, Any]], radius_m: float
) -> Tuple[Dict[str, str], Dict[str, int], Dict[str, List[str]]]:
    ids = [candidate_id(row) for row in request_rows]
    uf = UnionFind(ids)
    for i, row_a in enumerate(request_rows):
        for row_b in request_rows[i + 1 :]:
            distance = finite_distance(row_a.get("target_position"), row_b.get("target_position"))
            if distance is not None and distance <= radius_m:
                uf.union(candidate_id(row_a), candidate_id(row_b))

    by_root: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in request_rows:
        by_root[uf.find(candidate_id(row))].append(row)

    sorted_components = sorted(
        by_root.values(),
        key=lambda rows: (
            min(safe_int(row.get("target_generated_rank"), 999999) for row in rows),
            min(candidate_id(row) for row in rows),
        ),
    )
    component_by_candidate: Dict[str, str] = {}
    size_by_component: Dict[str, int] = {}
    members_by_component: Dict[str, List[str]] = {}
    request_id = row_request_id(request_rows[0]) if request_rows else "unknown"
    for index, rows in enumerate(sorted_components):
        component_id = f"{request_id}:component:{index}"
        members = sorted([candidate_id(row) for row in rows])
        size_by_component[component_id] = len(rows)
        members_by_component[component_id] = members
        for row in rows:
            component_by_candidate[candidate_id(row)] = component_id
    return component_by_candidate, size_by_component, members_by_component


def local_count(row: Dict[str, Any], rows: Sequence[Dict[str, Any]], radius_m: float) -> int:
    count = 0
    for other in rows:
        if candidate_id(other) == candidate_id(row):
            continue
        distance = finite_distance(row.get("target_position"), other.get("target_position"))
        if distance is not None and distance <= radius_m:
            count += 1
    return count


def nearest_distance(row: Dict[str, Any], rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    values = [
        finite_distance(row.get("target_position"), other.get("target_position"))
        for other in rows
        if candidate_id(other) != candidate_id(row)
    ]
    clean = [value for value in values if value is not None]
    return min(clean) if clean else None


def nearest_role_distance(row: Dict[str, Any], rows: Sequence[Dict[str, Any]], role: str) -> Optional[float]:
    anchors = [other for other in rows if role_has(other.get("target_candidate_role"), role)]
    values = [finite_distance(row.get("target_position"), anchor.get("target_position")) for anchor in anchors]
    clean = [value for value in values if value is not None]
    return min(clean) if clean else None


def density_bucket(neighbors_2m: int) -> str:
    if neighbors_2m >= 8:
        return "dense_context"
    if neighbors_2m >= 3:
        return "medium_context"
    return "sparse_context"


def context_score(row: Dict[str, Any]) -> float:
    return (
        safe_int(row.get("local_neighbor_count_1m"), 0) * 1.0
        + safe_int(row.get("local_neighbor_count_2m"), 0) * 0.5
        + safe_int(row.get("spatial_component_size"), 0) * 0.1
        + (1.0 if row.get("source_top_anchor") else 0.0)
        + (0.5 if row.get("strongest_positive_support_anchor") else 0.0)
    )


def enrich_candidate_rows(
    candidates: Sequence[Dict[str, Any]],
    plans: Sequence[Dict[str, Any]],
    component_radius_m: float,
) -> List[Dict[str, Any]]:
    plan_roles = role_index(plans)
    grouped = group_by_request(candidates)
    output_rows: List[Dict[str, Any]] = []
    for request_id, request_rows in sorted(grouped.items(), key=lambda item: request_sort_key(item[0])):
        enriched_base: List[Dict[str, Any]] = []
        for row in request_rows:
            role_info = plan_roles.get((request_id, candidate_id(row))) or {}
            enriched_base.append(
                {
                    **row,
                    "target_candidate_role": role_info.get("target_candidate_role"),
                    "goal_validity_rival_candidate_ids": role_info.get("goal_validity_rival_candidate_ids") or [],
                    "goal_validity_context_candidate_ids": role_info.get("goal_validity_context_candidate_ids") or [],
                    "viewpoint_source": role_info.get("viewpoint_source"),
                    "standoff_distance_requested": role_info.get("standoff_distance_requested"),
                    "standoff_target_horizontal_distance": role_info.get("standoff_target_horizontal_distance"),
                }
            )
        component_by_candidate, size_by_component, members_by_component = build_components(enriched_base, component_radius_m)
        for row in sorted(enriched_base, key=candidate_sort_key):
            cid = candidate_id(row)
            component_id = component_by_candidate.get(cid)
            role = row.get("target_candidate_role")
            role_list = role_tokens(role)
            near_1 = local_count(row, enriched_base, 1.0)
            near_2 = local_count(row, enriched_base, 2.0)
            near_4 = local_count(row, enriched_base, 4.0)
            distances_to_roles = {
                f"distance_to_{anchor}_m": nearest_role_distance(row, enriched_base, anchor)
                for anchor in ANCHOR_ROLES
            }
            context_row = {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_candidate_context",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": cid,
                "target_generated_rank": row.get("target_generated_rank"),
                "target_semantic_rank": row.get("target_semantic_rank"),
                "target_score": row.get("target_score"),
                "target_semantic_score": row.get("target_semantic_score"),
                "target_support_score": row.get("target_support_score"),
                "target_positive_support": row.get("target_positive_support"),
                "candidate_evidence_class": row.get("candidate_evidence_class"),
                "candidate_specific_support": row.get("candidate_specific_support"),
                "visual_support_score": row.get("visual_support_score", visual_support_score(row)),
                "associated_heading_count": row.get("associated_heading_count"),
                "mask_hit_count": row.get("mask_hit_count"),
                "consistent_depth_count": row.get("consistent_depth_count"),
                "best_box_score": row.get("best_box_score"),
                "simple_selector_selected": row.get("simple_selector_selected"),
                "simple_selector_variants": row.get("simple_selector_variants") or [],
                "target_position": row.get("target_position"),
                "target_visit_position": row.get("target_visit_position"),
                "target_candidate_role": role,
                "target_candidate_role_tokens": role_list,
                "source_top_anchor": role_has(role, "source_top_candidate"),
                "nearest_spatial_rival_anchor": role_has(role, "nearest_spatial_rival"),
                "nearest_higher_score_rival_anchor": role_has(role, "nearest_higher_score_rival"),
                "nearest_positive_support_rival_anchor": role_has(role, "nearest_positive_support_rival"),
                "strongest_positive_support_anchor": role_has(role, "strongest_positive_support_rival"),
                "goal_validity_rival_candidate_count": len(row.get("goal_validity_rival_candidate_ids") or []),
                "goal_validity_context_candidate_count": len(row.get("goal_validity_context_candidate_ids") or []),
                "spatial_component_id": component_id,
                "spatial_component_size": size_by_component.get(component_id or "", 0),
                "spatial_component_member_count": len(members_by_component.get(component_id or "", [])),
                "local_neighbor_count_1m": near_1,
                "local_neighbor_count_2m": near_2,
                "local_neighbor_count_4m": near_4,
                "local_density_bucket": density_bucket(near_2),
                "nearest_candidate_distance_m": nearest_distance(row, enriched_base),
                "viewpoint_source": row.get("viewpoint_source"),
                "standoff_distance_requested": row.get("standoff_distance_requested"),
                "standoff_target_horizontal_distance": row.get("standoff_target_horizontal_distance"),
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
            context_row.update(distances_to_roles)
            context_row["spatial_context_score"] = context_score(context_row)
            output_rows.append(context_row)
    return output_rows


def candidate_context_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {(row_request_id(row), candidate_id(row)): row for row in rows}


def delta(a: Any, b: Any) -> Optional[float]:
    va = safe_float(a)
    vb = safe_float(b)
    if va is None or vb is None:
        return None
    return va - vb


def delta_sign(value: Optional[float], positive_label: str, negative_label: str) -> str:
    if value is None:
        return "unknown"
    if value > 0:
        return positive_label
    if value < 0:
        return negative_label
    return "tie"


def pair_context_rows(
    pairs: Sequence[Dict[str, Any]], context_rows: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    indexed = candidate_context_index(context_rows)
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        pairs,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("selector_generated_rank"), 999999),
            safe_int(item.get("contrast_generated_rank"), 999999),
            str(item.get("contrast_candidate_id")),
        ),
    ):
        request_id = row_request_id(row)
        selector = indexed.get((request_id, str(row.get("selector_candidate_id")))) or {}
        contrast = indexed.get((request_id, str(row.get("contrast_candidate_id")))) or {}
        same_component = (
            selector.get("spatial_component_id") is not None
            and selector.get("spatial_component_id") == contrast.get("spatial_component_id")
        )
        density_delta = safe_int(contrast.get("local_neighbor_count_2m"), 0) - safe_int(
            selector.get("local_neighbor_count_2m"), 0
        )
        component_size_delta = safe_int(contrast.get("spatial_component_size"), 0) - safe_int(
            selector.get("spatial_component_size"), 0
        )
        context_delta = delta(contrast.get("spatial_context_score"), selector.get("spatial_context_score"))
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_pair_context",
                "expanded_retrieval_request_id": request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "selector_candidate_id": row.get("selector_candidate_id"),
                "contrast_candidate_id": row.get("contrast_candidate_id"),
                "selector_candidate_variants": row.get("selector_candidate_variants") or [],
                "selector_generated_rank": row.get("selector_generated_rank"),
                "contrast_generated_rank": row.get("contrast_generated_rank"),
                "rank_delta_contrast_minus_selector": row.get("rank_delta_contrast_minus_selector"),
                "visual_delta_sign": row.get("visual_delta_sign"),
                "visual_support_delta_contrast_minus_selector": row.get(
                    "visual_support_delta_contrast_minus_selector"
                ),
                "target_horizontal_distance_m": row.get("target_horizontal_distance_m"),
                "visit_horizontal_distance_m": row.get("visit_horizontal_distance_m"),
                "goal_region_overlap_proxy": row.get("goal_region_overlap_proxy"),
                "selector_spatial_component_id": selector.get("spatial_component_id"),
                "contrast_spatial_component_id": contrast.get("spatial_component_id"),
                "same_spatial_component": same_component,
                "selector_component_size": selector.get("spatial_component_size"),
                "contrast_component_size": contrast.get("spatial_component_size"),
                "component_size_delta_contrast_minus_selector": component_size_delta,
                "selector_local_neighbor_count_2m": selector.get("local_neighbor_count_2m"),
                "contrast_local_neighbor_count_2m": contrast.get("local_neighbor_count_2m"),
                "local_density_delta_contrast_minus_selector": density_delta,
                "local_density_delta_sign": delta_sign(
                    float(density_delta),
                    "contrast_denser",
                    "selector_denser",
                ),
                "selector_context_score": selector.get("spatial_context_score"),
                "contrast_context_score": contrast.get("spatial_context_score"),
                "context_score_delta_contrast_minus_selector": context_delta,
                "context_score_delta_sign": delta_sign(
                    context_delta,
                    "contrast_context_higher",
                    "selector_context_higher",
                ),
                "selector_role_tokens": selector.get("target_candidate_role_tokens") or [],
                "contrast_role_tokens": contrast.get("target_candidate_role_tokens") or [],
                "selector_distance_to_source_top_candidate_m": selector.get(
                    "distance_to_source_top_candidate_m"
                ),
                "contrast_distance_to_source_top_candidate_m": contrast.get(
                    "distance_to_source_top_candidate_m"
                ),
                "selector_distance_to_nearest_positive_support_rival_m": selector.get(
                    "distance_to_nearest_positive_support_rival_m"
                ),
                "contrast_distance_to_nearest_positive_support_rival_m": contrast.get(
                    "distance_to_nearest_positive_support_rival_m"
                ),
                "relation_context_profile": (
                    "same_component"
                    if same_component
                    else "distinct_component"
                ),
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def request_context_rows(
    candidates: Sequence[Dict[str, Any]], pairs: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    candidate_groups = group_by_request(candidates)
    pair_groups = group_by_request(pairs)
    for request_id, request_candidates in sorted(candidate_groups.items(), key=lambda item: request_sort_key(item[0])):
        request_pairs = pair_groups.get(request_id, [])
        component_counts = Counter(str(row.get("spatial_component_id")) for row in request_candidates)
        density_counts = Counter(str(row.get("local_density_bucket")) for row in request_candidates)
        context_counts = Counter(str(row.get("context_score_delta_sign")) for row in request_pairs)
        component_count = len(component_counts)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_request_context",
                "expanded_retrieval_request_id": request_id,
                "episode_key": request_candidates[0].get("episode_key") if request_candidates else None,
                "scene_key": request_candidates[0].get("scene_key") if request_candidates else None,
                "scene_id": request_candidates[0].get("scene_id") if request_candidates else None,
                "query": request_candidates[0].get("query") if request_candidates else None,
                "candidate_rows": len(request_candidates),
                "pair_rows": len(request_pairs),
                "spatial_component_count": component_count,
                "spatial_component_size_counts": dict(sorted(Counter(component_counts.values()).items())),
                "local_density_bucket_counts": dict(sorted(density_counts.items())),
                "pair_same_component_rows": sum(1 for row in request_pairs if row.get("same_spatial_component")),
                "pair_distinct_component_rows": sum(1 for row in request_pairs if not row.get("same_spatial_component")),
                "pair_context_delta_sign_counts": dict(sorted(context_counts.items())),
                "target_horizontal_distance_stats": distance_stats(
                    [safe_float(row.get("target_horizontal_distance_m")) for row in request_pairs]
                ),
                "context_score_delta_stats": distance_stats(
                    [safe_float(row.get("context_score_delta_contrast_minus_selector")) for row in request_pairs]
                ),
                "next_context_action": "profile_relation_spatial_context",
                "next_context_reason": "relation_spatial_context_diagnostic_before_terminal_policy",
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def evaluated_candidate_rows(
    action_rows: Sequence[Dict[str, Any]], evaluated_candidates: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    labels = {
        (row_request_id(row), candidate_id(row)): {
            "evaluation_only_candidate_correct": row.get("evaluation_only_candidate_correct"),
            "evaluation_only_candidate_rank": row.get("evaluation_only_candidate_rank"),
        }
        for row in evaluated_candidates
    }
    rows: List[Dict[str, Any]] = []
    for row in action_rows:
        label = labels.get((row_request_id(row), candidate_id(row))) or {}
        rows.append(
            {
                **row,
                "validation_stage": "evaluated_candidate_context_after_action_rows",
                "evaluation_only_candidate_correct": label.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def evaluated_pair_rows(
    action_rows: Sequence[Dict[str, Any]], evaluated_pairs: Sequence[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    labels = {
        (
            row_request_id(row),
            str(row.get("selector_candidate_id")),
            str(row.get("contrast_candidate_id")),
        ): {
            "evaluation_only_selector_candidate_correct": row.get(
                "evaluation_only_selector_candidate_correct"
            ),
            "evaluation_only_contrast_candidate_correct": row.get(
                "evaluation_only_contrast_candidate_correct"
            ),
            "evaluation_only_target_contrast_pair": row.get("evaluation_only_target_contrast_pair"),
        }
        for row in evaluated_pairs
    }
    rows: List[Dict[str, Any]] = []
    for row in action_rows:
        label = labels.get(
            (
                row_request_id(row),
                str(row.get("selector_candidate_id")),
                str(row.get("contrast_candidate_id")),
            )
        ) or {}
        rows.append(
            {
                **row,
                "validation_stage": "evaluated_pair_context_after_action_rows",
                "evaluation_only_selector_candidate_correct": label.get(
                    "evaluation_only_selector_candidate_correct"
                ),
                "evaluation_only_contrast_candidate_correct": label.get(
                    "evaluation_only_contrast_candidate_correct"
                ),
                "evaluation_only_target_contrast_pair": label.get(
                    "evaluation_only_target_contrast_pair"
                ),
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def failure_taxonomy(row: Dict[str, Any]) -> str:
    if row.get("evaluation_only_target_contrast_pair") is not True:
        return "not_target_contrast_pair"
    if row.get("same_spatial_component") is True and row.get("visual_delta_sign") == "selector_visual_higher":
        return "same_component_selector_visual_dominates"
    if row.get("same_spatial_component") is True:
        return "same_component_context_not_discriminative"
    if row.get("context_score_delta_sign") == "selector_context_higher":
        return "distinct_component_selector_context_higher"
    if row.get("visual_delta_sign") == "selector_visual_higher":
        return "distinct_component_selector_visual_higher"
    return "context_candidate_for_followup"


def summarize(
    *,
    contract: Dict[str, Any],
    discriminative_summary: Dict[str, Any],
    candidate_context: Sequence[Dict[str, Any]],
    pair_context: Sequence[Dict[str, Any]],
    request_context: Sequence[Dict[str, Any]],
    eval_candidate_context: Sequence[Dict[str, Any]],
    eval_pair_context: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    action_rows = [*candidate_context, *pair_context, *request_context]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    request_ids = sorted({row_request_id(row) for row in candidate_context}, key=request_sort_key)
    support_rows = [row for row in candidate_context if row.get("candidate_specific_support") is True]
    target_pairs = [
        {**row, "failure_taxonomy": failure_taxonomy(row)}
        for row in eval_pair_context
        if row.get("evaluation_only_target_contrast_pair") is True
    ]
    target_context_counts = Counter(str(row.get("context_score_delta_sign")) for row in target_pairs)
    target_density_counts = Counter(str(row.get("local_density_delta_sign")) for row in target_pairs)
    target_component_counts = Counter(
        "same_component" if row.get("same_spatial_component") else "distinct_component"
        for row in target_pairs
    )
    taxonomy_counts = Counter(str(row.get("failure_taxonomy")) for row in target_pairs)
    context_ready = (
        len(target_pairs)
        >= safe_int(gates.get("target_contrast_pair_rows_minimum_after_label_join"), 0)
        and target_context_counts.get("selector_context_higher", 0) == 0
        and target_component_counts.get("same_component", 0) == 0
        and target_context_counts.get("contrast_context_higher", 0) > 0
    )
    recommended = (
        "request_relation_spatial_context_observation"
        if context_ready
        else "request_scene_graph_or_object_relation_evidence"
    )
    component_group_count = len({row.get("spatial_component_id") for row in candidate_context})
    gate = {
        "input_discriminative_evidence_gate_passed": discriminative_summary.get("gate", {}).get(
            "discriminative_evidence_gate_passed"
        )
        is bool(gates.get("input_discriminative_evidence_gate_passed", True)),
        "expected_request_rows_passed": len(request_ids) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_rows_passed": len(candidate_context) == safe_int(gates.get("expected_candidate_rows")),
        "expected_pair_rows_passed": len(pair_context) == safe_int(gates.get("expected_pair_rows")),
        "candidate_specific_support_count_minimum_passed": len(support_rows)
        >= safe_int(gates.get("candidate_specific_support_count_minimum"), 0),
        "target_contrast_pair_rows_minimum_after_label_join_passed": len(target_pairs)
        >= safe_int(gates.get("target_contrast_pair_rows_minimum_after_label_join"), 0),
        "target_pairs_with_selector_visual_advantage_minimum_after_label_join_passed": (
            discriminative_summary.get("post_label_analysis", {}).get(
                "evaluation_only_target_pairs_with_selector_visual_advantage", 0
            )
            >= safe_int(gates.get("target_pairs_with_selector_visual_advantage_minimum_after_label_join"), 0)
        ),
        "spatial_context_group_rows_minimum_passed": component_group_count
        >= safe_int(gates.get("spatial_context_group_rows_minimum"), 0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["relation_spatial_context_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "discriminative_summary": str(args.discriminative_summary),
        "candidate_rows": str(args.candidate_rows),
        "pair_rows": str(args.pair_rows),
        "request_rows_source": str(args.request_rows),
        "plan_rows": str(args.plan_rows),
        "out_root": str(args.out_root),
        "request_rows": len(request_context),
        "candidate_context_rows": len(candidate_context),
        "pair_context_rows": len(pair_context),
        "candidate_specific_support_count": len(support_rows),
        "spatial_context_group_count": component_group_count,
        "spatial_component_count_by_request": {
            request_id: len({row.get("spatial_component_id") for row in rows})
            for request_id, rows in group_by_request(candidate_context).items()
        },
        "candidate_context_profile": {
            "local_density_bucket_counts": dict(
                sorted(Counter(str(row.get("local_density_bucket")) for row in candidate_context).items())
            ),
            "role_counts": dict(
                sorted(
                    Counter(
                        role
                        for row in candidate_context
                        for role in (row.get("target_candidate_role_tokens") or ["no_role"])
                    ).items()
                )
            ),
            "component_size_stats": number_stats(
                [safe_int(row.get("spatial_component_size"), 0) for row in candidate_context]
            ),
            "nearest_candidate_distance_stats": distance_stats(
                [safe_float(row.get("nearest_candidate_distance_m")) for row in candidate_context]
            ),
        },
        "action_time_pair_context_profile": {
            "component_relation_counts": dict(sorted(Counter(
                "same_component" if row.get("same_spatial_component") else "distinct_component"
                for row in pair_context
            ).items())),
            "context_score_delta_sign_counts": dict(
                sorted(Counter(str(row.get("context_score_delta_sign")) for row in pair_context).items())
            ),
            "local_density_delta_sign_counts": dict(
                sorted(Counter(str(row.get("local_density_delta_sign")) for row in pair_context).items())
            ),
            "context_score_delta_stats": distance_stats(
                [safe_float(row.get("context_score_delta_contrast_minus_selector")) for row in pair_context]
            ),
        },
        "post_label_context_analysis": {
            "evaluation_only_candidate_context_rows": len(eval_candidate_context),
            "evaluation_only_pair_context_rows": len(eval_pair_context),
            "evaluation_only_target_contrast_pair_rows": len(target_pairs),
            "evaluation_only_target_pair_context_score_delta_sign_counts": dict(
                sorted(target_context_counts.items())
            ),
            "evaluation_only_target_pair_local_density_delta_sign_counts": dict(
                sorted(target_density_counts.items())
            ),
            "evaluation_only_target_pair_component_relation_counts": dict(
                sorted(target_component_counts.items())
            ),
            "evaluation_only_target_pair_failure_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        },
        "diagnostic_conclusion": {
            "relation_spatial_context_signal_ready": context_ready,
            "recommended_next_action": recommended,
            "reason": (
                "target_pairs_have_consistent_context_advantage"
                if context_ready
                else "static_relation_spatial_context_not_consistent_terminal_separator"
            ),
            "terminal_policy_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": "The analyzer materializes relation/spatial context rows before joining correctness labels.",
            "agent_inference": (
                "If static context cannot separate selector failures, the next evidence should be richer object relation or scene-graph context rather than detector/support threshold tuning."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "candidate_context_rows": "goal_validity_relation_spatial_candidate_context_rows.jsonl",
            "pair_context_rows": "goal_validity_relation_spatial_pair_context_rows.jsonl",
            "request_context_rows": "goal_validity_relation_spatial_request_context_rows.jsonl",
            "evaluated_candidate_context_rows": "goal_validity_relation_spatial_evaluated_candidate_context_rows.jsonl",
            "evaluated_pair_context_rows": "goal_validity_relation_spatial_evaluated_pair_context_rows.jsonl",
            "summary": "goal_validity_relation_spatial_context_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    discriminative_summary = load_json(Path(args.discriminative_summary))
    candidates = load_jsonl(Path(args.candidate_rows))
    pairs = load_jsonl(Path(args.pair_rows))
    _requests = load_jsonl(Path(args.request_rows))
    plans = load_jsonl(Path(args.plan_rows))
    eval_candidates = load_jsonl(Path(args.evaluated_candidate_rows))
    eval_pairs = load_jsonl(Path(args.evaluated_pair_rows))
    candidate_context = enrich_candidate_rows(candidates, plans, float(args.component_radius_m))
    pair_context = pair_context_rows(pairs, candidate_context)
    requests = request_context_rows(candidate_context, pair_context)
    evaluated_candidates = evaluated_candidate_rows(candidate_context, eval_candidates)
    evaluated_pairs = evaluated_pair_rows(pair_context, eval_pairs)
    summary = summarize(
        contract=contract,
        discriminative_summary=discriminative_summary,
        candidate_context=candidate_context,
        pair_context=pair_context,
        request_context=requests,
        eval_candidate_context=evaluated_candidates,
        eval_pair_context=evaluated_pairs,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "goal_validity_relation_spatial_candidate_context_rows.jsonl", candidate_context)
    write_jsonl(out_root / "goal_validity_relation_spatial_pair_context_rows.jsonl", pair_context)
    write_jsonl(out_root / "goal_validity_relation_spatial_request_context_rows.jsonl", requests)
    write_jsonl(
        out_root / "goal_validity_relation_spatial_evaluated_candidate_context_rows.jsonl",
        evaluated_candidates,
    )
    write_jsonl(
        out_root / "goal_validity_relation_spatial_evaluated_pair_context_rows.jsonl",
        evaluated_pairs,
    )
    write_json(out_root / "goal_validity_relation_spatial_context_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze relation/spatial context evidence after discriminative separability failure."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--discriminative-summary", required=True)
    parser.add_argument("--candidate-rows", required=True)
    parser.add_argument("--pair-rows", required=True)
    parser.add_argument("--request-rows", required=True)
    parser.add_argument("--evaluated-candidate-rows", required=True)
    parser.add_argument("--evaluated-pair-rows", required=True)
    parser.add_argument("--plan-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--component-radius-m", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
