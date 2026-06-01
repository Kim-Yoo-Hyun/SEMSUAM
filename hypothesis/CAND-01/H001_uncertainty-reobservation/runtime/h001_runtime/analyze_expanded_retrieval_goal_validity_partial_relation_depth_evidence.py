import argparse
import json
import math
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    request_sort_key,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_partial_relation_depth_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1"
)
RESOLVED = "relation_depth_completion_resolved"
PARTIAL = "relation_depth_completion_partial"
UNRESOLVED = "relation_depth_completion_unresolved"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def decision_id(row: Dict[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def finite_stats(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(clean), "mean": sum(clean) / len(clean), "max": max(clean)}


def mean(values: Sequence[Optional[float]]) -> Optional[float]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return None
    return sum(clean) / len(clean)


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def rounded_float(value: Any, digits: int = 4) -> Optional[float]:
    number = safe_float(value)
    return None if number is None else round(number, digits)


def rounded_vec(value: Any, digits: int = 4) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not isinstance(value, list) or len(value) < 3:
        return (None, None, None)
    return (rounded_float(value[0], digits), rounded_float(value[1], digits), rounded_float(value[2], digits))


def join_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
    return (
        request_id(row),
        candidate_id(row),
        str(row.get("standoff_direction_source") or ""),
        str(row.get("standoff_relation_anchor_candidate_id") or ""),
        rounded_float(row.get("standoff_distance_requested")),
        rounded_float(row.get("standoff_target_horizontal_distance")),
        rounded_float(row.get("target_distance_from_viewpoint_m")),
        rounded_vec(row.get("standoff_desired_position")),
    )


def index_plans_by_join_key(plan_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[Any, ...], Deque[Dict[str, Any]]]:
    indexed: Dict[Tuple[Any, ...], Deque[Dict[str, Any]]] = defaultdict(deque)
    for row in sorted(
        plan_rows,
        key=lambda item: (
            request_sort_key(request_id(item)),
            safe_int(item.get("target_generated_rank")),
            candidate_id(item),
            safe_int(item.get("completion_index")),
        ),
    ):
        indexed[join_key(row)].append(dict(row))
    return indexed


def attach_plan_rows(
    plan_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    plans_by_key = index_plans_by_join_key(plan_rows)
    attached: List[Dict[str, Any]] = []
    missing: List[Tuple[Any, ...]] = []
    for frame in frame_rows:
        key = join_key(frame)
        queue = plans_by_key.get(key)
        if not queue:
            missing.append(key)
            continue
        plan = queue.popleft()
        attached.append({"plan": plan, "frame": dict(frame)})
    leftovers = sum(len(queue) for queue in plans_by_key.values())
    if missing or leftovers:
        raise RuntimeError({"missing_frame_plan_matches": len(missing), "leftover_plan_rows": leftovers})
    return attached


def group_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[decision_id(row)].append(dict(row))
    return grouped


def failed_index(row: Dict[str, Any]) -> Optional[int]:
    value = row.get("failed_evidence_index")
    if value is None:
        return None
    return safe_int(value)


def failed_index_map(rows: Sequence[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    indexed: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        index = failed_index(row)
        if index is not None:
            indexed[index] = dict(row)
    return indexed


def association_stats(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    depth_consistent = [
        row for row in rows if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    associated_depth_consistent = [
        row
        for row in associated
        if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    associated_depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
    depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in rows]
    associated_depth_agreements = [safe_float(row.get("depth_agreement_m")) for row in associated]
    box_scores = [safe_float(row.get("best_box_score")) for row in rows]
    mask_depths = [safe_float(row.get("mask_depth_median")) for row in rows]
    camera_forward = [safe_float(row.get("camera_forward_m")) for row in rows]
    return {
        "association_rows": len(rows),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(depth_consistent),
        "associated_depth_consistent_count": len(associated_depth_consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_offset_counts": compact_counter(row.get("projection_anchor_height_offset_m") for row in rows),
        "best_box_score_max": max([score for score in box_scores if score is not None], default=None),
        "best_box_score_mean": mean(box_scores),
        "depth_error_stats_m": finite_stats(depth_errors),
        "associated_depth_error_stats_m": finite_stats(associated_depth_errors),
        "depth_agreement_stats_m": finite_stats(depth_agreements),
        "associated_depth_agreement_stats_m": finite_stats(associated_depth_agreements),
        "mask_depth_stats_m": finite_stats(mask_depths),
        "camera_forward_stats_m": finite_stats(camera_forward),
    }


def completion_status(stats: Dict[str, Any], prior: Optional[Dict[str, Any]]) -> str:
    prior_consistent = safe_int((prior or {}).get("depth_consistent_count"), 0)
    associated = safe_int(stats.get("associated_heading_count"), 0)
    associated_consistent = safe_int(stats.get("associated_depth_consistent_count"), 0)
    depth_consistent = safe_int(stats.get("depth_consistent_count"), 0)
    inside_mask = safe_int(stats.get("inside_mask_count"), 0)
    if associated > 0 and associated_consistent > prior_consistent:
        return RESOLVED
    if associated > 0 or depth_consistent > 0 or inside_mask > 0:
        return PARTIAL
    return UNRESOLVED


def evidence_row(
    *,
    plan: Dict[str, Any],
    frame: Dict[str, Any],
    associations: Sequence[Dict[str, Any]],
    prior_failed: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    stats = association_stats(associations)
    index = failed_index(plan)
    status = completion_status(stats, prior_failed)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_partial_relation_depth_detector_evidence",
        "expanded_retrieval_request_id": request_id(plan),
        "rival_identity_request_id": plan.get("rival_identity_request_id"),
        "episode_key": plan.get("episode_key"),
        "scene_key": plan.get("scene_key"),
        "scene_id": plan.get("scene_id"),
        "query": plan.get("query"),
        "request_index": plan.get("request_index"),
        "observation_index": plan.get("observation_index"),
        "completion_index": plan.get("completion_index"),
        "decision_id": decision_id(frame),
        "candidate_id": candidate_id(plan),
        "target_candidate_id": candidate_id(plan),
        "target_candidate_role": plan.get("target_candidate_role"),
        "target_generated_rank": plan.get("target_generated_rank"),
        "target_semantic_rank": plan.get("target_semantic_rank"),
        "target_score": plan.get("target_score"),
        "target_semantic_score": plan.get("target_semantic_score"),
        "target_support_score": plan.get("target_support_score"),
        "target_positive_support": plan.get("target_positive_support"),
        "target_position": plan.get("target_position"),
        "target_visit_position": plan.get("target_visit_position"),
        "failed_evidence_index": index,
        "prior_relation_depth_evidence_status": None if prior_failed is None else prior_failed.get("relation_depth_evidence_status"),
        "prior_candidate_association_count": None if prior_failed is None else prior_failed.get("candidate_association_count"),
        "prior_depth_consistent_count": None if prior_failed is None else prior_failed.get("depth_consistent_count"),
        "prior_depth_mismatch_count": None if prior_failed is None else prior_failed.get("depth_mismatch_count"),
        "prior_inside_mask_count": None if prior_failed is None else prior_failed.get("inside_mask_count"),
        "prior_standoff_direction_source": None if prior_failed is None else prior_failed.get("standoff_direction_source"),
        "requested_direction_source": plan.get("requested_direction_source"),
        "failed_standoff_direction_source": plan.get("failed_standoff_direction_source"),
        "standoff_direction_source": plan.get("standoff_direction_source"),
        "standoff_relation_anchor_candidate_id": plan.get("standoff_relation_anchor_candidate_id"),
        "context_candidate_id": plan.get("context_candidate_id"),
        "relation_anchor_candidate_ids": list(plan.get("relation_anchor_candidate_ids") or []),
        "viewpoint_source": plan.get("viewpoint_source"),
        "standoff_distance_requested": plan.get("standoff_distance_requested"),
        "target_distance_from_viewpoint_m": plan.get("target_distance_from_viewpoint_m"),
        "standoff_target_horizontal_distance": plan.get("standoff_target_horizontal_distance"),
        "rendered_heading_count": frame.get("rendered_heading_count"),
        "detector_box_count": frame.get("detector_box_count"),
        "sam2_mask_count": frame.get("sam2_mask_count"),
        "has_detector_box": frame.get("has_detector_box"),
        "has_sam2_mask": frame.get("has_sam2_mask"),
        "has_candidate_association": frame.get("has_candidate_association"),
        **stats,
        "relation_depth_completion_status": status,
        "evidence_status": status,
        "recommended_nonterminal_action": "aggregate_partial_relation_depth_evidence",
        "terminal_policy_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_evidence_rows(
    attached_rows: Sequence[Dict[str, Dict[str, Any]]],
    association_rows: Sequence[Dict[str, Any]],
    failed_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    associations_by_decision = group_by_decision(association_rows)
    failed_by_index = failed_index_map(failed_rows)
    rows = []
    for attached in attached_rows:
        plan = attached["plan"]
        frame = attached["frame"]
        index = failed_index(plan)
        rows.append(
            evidence_row(
                plan=plan,
                frame=frame,
                associations=associations_by_decision.get(decision_id(frame), []),
                prior_failed=failed_by_index.get(index) if index is not None else None,
            )
        )
    rows.sort(
        key=lambda row: (
            request_sort_key(request_id(row)),
            safe_int(row.get("target_generated_rank")),
            candidate_id(row),
            safe_int(row.get("completion_index")),
        )
    )
    return rows


def failed_summary_status(rows: Sequence[Dict[str, Any]]) -> str:
    statuses = [row.get("relation_depth_completion_status") for row in rows]
    if any(status == RESOLVED for status in statuses):
        return RESOLVED
    if any(status == PARTIAL for status in statuses):
        return PARTIAL
    return UNRESOLVED


def failed_summary_rows(
    failed_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    evidence_by_failed: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        index = failed_index(row)
        if index is not None:
            evidence_by_failed[index].append(row)

    output: List[Dict[str, Any]] = []
    for prior in sorted(failed_rows, key=lambda row: safe_int(row.get("failed_evidence_index"))):
        index = safe_int(prior.get("failed_evidence_index"))
        rows = evidence_by_failed.get(index, [])
        status = failed_summary_status(rows) if rows else UNRESOLVED
        associated = sum(safe_int(row.get("associated_heading_count"), 0) for row in rows)
        associated_consistent = sum(safe_int(row.get("associated_depth_consistent_count"), 0) for row in rows)
        depth_consistent = sum(safe_int(row.get("depth_consistent_count"), 0) for row in rows)
        inside_mask = sum(safe_int(row.get("inside_mask_count"), 0) for row in rows)
        if status == RESOLVED:
            next_action = "keep_nonterminal_goal_validity_evidence_for_later_arbitration"
        elif status == PARTIAL:
            next_action = "keep_deferred_or_request_additional_relation_depth_evidence"
        else:
            next_action = "defer_goal_validity_terminal_policy"
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_failed_evidence_summary",
                "expanded_retrieval_request_id": request_id(prior),
                "rival_identity_request_id": prior.get("rival_identity_request_id"),
                "episode_key": prior.get("episode_key"),
                "scene_key": prior.get("scene_key"),
                "scene_id": prior.get("scene_id"),
                "query": prior.get("query"),
                "candidate_id": candidate_id(prior),
                "target_candidate_id": candidate_id(prior),
                "failed_evidence_index": index,
                "prior_relation_depth_evidence_status": prior.get("relation_depth_evidence_status"),
                "prior_standoff_direction_source": prior.get("standoff_direction_source"),
                "prior_candidate_association_count": prior.get("candidate_association_count"),
                "prior_depth_consistent_count": prior.get("depth_consistent_count"),
                "prior_depth_mismatch_count": prior.get("depth_mismatch_count"),
                "prior_inside_mask_count": prior.get("inside_mask_count"),
                "completion_evidence_rows": len(rows),
                "completion_direction_sources": sorted({str(row.get("standoff_direction_source")) for row in rows}),
                "completion_associated_heading_count": associated,
                "completion_associated_depth_consistent_count": associated_consistent,
                "completion_depth_consistent_count": depth_consistent,
                "completion_inside_mask_count": inside_mask,
                "completion_status": status,
                "evidence_status": status,
                "next_evidence_action": next_action,
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def request_summary_rows(
    request_rows: Sequence[Dict[str, Any]],
    target_rows: Sequence[Dict[str, Any]],
    failed_summary: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    targets_by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    failed_by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    evidence_by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in target_rows:
        targets_by_request[request_id(row)].append(row)
    for row in failed_summary:
        failed_by_request[request_id(row)].append(row)
    for row in evidence_rows:
        evidence_by_request[request_id(row)].append(row)

    rows: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=lambda row: request_sort_key(request_id(row))):
        rid = request_id(request)
        failed = failed_by_request.get(rid, [])
        evidence = evidence_by_request.get(rid, [])
        status_counts = Counter(str(row.get("completion_status")) for row in failed)
        if status_counts.get(PARTIAL, 0) or status_counts.get(UNRESOLVED, 0):
            action = "defer_terminal_goal_validity_pending_remaining_relation_depth_uncertainty"
        else:
            action = "keep_nonterminal_relation_depth_completion_evidence"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_request_summary",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": request.get("rival_identity_request_id"),
                "episode_key": request.get("episode_key"),
                "scene_key": request.get("scene_key"),
                "scene_id": request.get("scene_id"),
                "query": request.get("query"),
                "target_candidate_rows": len(targets_by_request.get(rid, [])),
                "failed_evidence_rows": len(failed),
                "evidence_rows": len(evidence),
                "resolved_failed_evidence_rows": status_counts.get(RESOLVED, 0),
                "partial_failed_evidence_rows": status_counts.get(PARTIAL, 0),
                "unresolved_failed_evidence_rows": status_counts.get(UNRESOLVED, 0),
                "associated_heading_count": sum(safe_int(row.get("associated_heading_count"), 0) for row in evidence),
                "associated_depth_consistent_count": sum(safe_int(row.get("associated_depth_consistent_count"), 0) for row in evidence),
                "inside_mask_count": sum(safe_int(row.get("inside_mask_count"), 0) for row in evidence),
                "request_evidence_status_counts": dict(sorted(status_counts.items())),
                "next_evidence_action": action,
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def unresolved_rows(failed_summary: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = []
    for row in failed_summary:
        if row.get("completion_status") == RESOLVED:
            continue
        rows.append(
            {
                **row,
                "validation_stage": "action_partial_relation_depth_unresolved_or_partial",
                "unresolved_reason": (
                    "no_candidate_associated_depth_improvement"
                    if row.get("completion_status") == PARTIAL
                    else "no_usable_detector_association"
                ),
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    *,
    contract: Dict[str, Any],
    input_summary: Dict[str, Any],
    plan_summary: Dict[str, Any],
    projection_summary: Dict[str, Any],
    detector_summary: Dict[str, Any],
    association_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
    failed_summary: Sequence[Dict[str, Any]],
    request_summary: Sequence[Dict[str, Any]],
    unresolved: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_evidence_gate") or {}
    action_rows = [*evidence_rows, *failed_summary, *request_summary, *unresolved]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True or row.get("terminal_policy_allowed") is True]
    detector_gate = detector_summary.get("gate") or {}
    input_gate = input_summary.get("gate") or {}
    plan_gate = plan_summary.get("gate") or {}
    projection_gate = projection_summary.get("gate") or {}
    associated = [row for row in association_rows if row.get("associated_to_candidate") is True]
    inside_mask = [row for row in association_rows if row.get("projected_pixel_inside_mask") is True]
    failed_indices = {failed_index(row) for row in failed_summary}
    failed_indices.discard(None)
    expected_failed_indices = set(range(safe_int(minimum.get("expected_failed_relation_depth_evidence_rows"), 0)))
    status_counts = Counter(str(row.get("completion_status")) for row in failed_summary)
    gate = {
        "input_gate_passed": bool(input_gate.get("partial_relation_depth_input_gate_passed")) is bool(minimum.get("input_gate_passed", True)),
        "plan_gate_passed": bool(plan_gate.get("partial_relation_depth_observation_plan_gate_passed")) is bool(minimum.get("plan_gate_passed", True)),
        "projection_gate_passed": bool(projection_gate.get("projection_anchor_smoke_passed")) is bool(minimum.get("projection_gate_passed", True)),
        "detector_substrate_gate_passed": bool(detector_gate.get("passes_detector_substrate_gate")) is bool(minimum.get("detector_substrate_gate_passed", True)),
        "expected_request_rows_passed": len(request_summary) == safe_int(minimum.get("expected_request_rows"), 0),
        "expected_target_candidate_rows_passed": safe_int(input_summary.get("target_candidate_rows"), -1)
        == safe_int(minimum.get("expected_target_candidate_rows"), 0),
        "expected_failed_relation_depth_evidence_rows_passed": len(failed_summary)
        == safe_int(minimum.get("expected_failed_relation_depth_evidence_rows"), 0),
        "expected_plan_rows_passed": len(evidence_rows) == safe_int(minimum.get("expected_plan_rows"), 0),
        "expected_detector_rows_passed": safe_int(detector_summary.get("detector_rows"), -1)
        == safe_int(minimum.get("expected_detector_rows"), 0),
        "expected_detector_association_rows_passed": len(association_rows)
        == safe_int(minimum.get("expected_detector_association_rows"), 0),
        "minimum_rows_with_candidate_association_passed": safe_int(detector_summary.get("rows_with_candidate_association"), 0)
        >= safe_int(minimum.get("minimum_rows_with_candidate_association"), 0),
        "minimum_candidate_association_rate_passed": (safe_float(detector_summary.get("candidate_association_rate")) or 0.0)
        >= float(minimum.get("minimum_candidate_association_rate", 0.0)),
        "minimum_associated_candidate_heading_count_passed": len(associated)
        >= safe_int(minimum.get("minimum_associated_candidate_heading_count"), 0),
        "minimum_projected_pixel_inside_mask_count_passed": len(inside_mask)
        >= safe_int(minimum.get("minimum_projected_pixel_inside_mask_count"), 0),
        "failed_evidence_rows_mapped_or_explicitly_unresolved_passed": expected_failed_indices == failed_indices,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(minimum.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows)
        and detector_summary.get("uses_gt_for_action") is False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["partial_relation_depth_detector_evidence_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    if status_counts.get(PARTIAL, 0) or status_counts.get(UNRESOLVED, 0):
        recommended = "inspect_remaining_partial_relation_depth_rows"
        reason = "some failed relation-depth rows remain partial or unresolved after detector-backed completion"
    else:
        recommended = "design_nonterminal_relation_depth_to_goal_validity_interpretation_gate"
        reason = "all failed relation-depth rows are detector-depth resolved, but terminal utility is still blocked"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "input_summary": str(args.input_summary),
            "plan_summary": str(args.plan_summary),
            "projection_summary": str(args.projection_summary),
            "detector_summary": str(args.detector_summary),
            "detector_associations": str(args.detector_associations),
            "detector_frame_summary": str(args.detector_frame_summary),
        },
        "request_rows": len(request_summary),
        "target_candidate_rows": input_summary.get("target_candidate_rows"),
        "failed_relation_depth_evidence_rows": len(failed_summary),
        "evidence_rows": len(evidence_rows),
        "unresolved_or_partial_rows": len(unresolved),
        "detector_rows": detector_summary.get("detector_rows"),
        "association_rows": len(association_rows),
        "rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
        "candidate_association_rate": detector_summary.get("candidate_association_rate"),
        "associated_candidate_heading_count": len(associated),
        "projected_pixel_inside_mask_count": len(inside_mask),
        "completion_status_counts": dict(sorted(status_counts.items())),
        "evidence_status_counts": compact_counter(row.get("relation_depth_completion_status") for row in evidence_rows),
        "failed_direction_counts": compact_counter(row.get("prior_standoff_direction_source") for row in failed_summary),
        "completion_direction_counts": compact_counter(row.get("standoff_direction_source") for row in evidence_rows),
        "request_profiles": {
            request_id(row): {
                "target_candidate_rows": row.get("target_candidate_rows"),
                "failed_evidence_rows": row.get("failed_evidence_rows"),
                "resolved_failed_evidence_rows": row.get("resolved_failed_evidence_rows"),
                "partial_failed_evidence_rows": row.get("partial_failed_evidence_rows"),
                "unresolved_failed_evidence_rows": row.get("unresolved_failed_evidence_rows"),
                "associated_heading_count": row.get("associated_heading_count"),
                "next_evidence_action": row.get("next_evidence_action"),
            }
            for row in request_summary
        },
        "diagnostic_conclusion": {
            "partial_relation_depth_evidence_signal_ready": gate["partial_relation_depth_detector_evidence_gate_passed"],
            "recommended_next_action": recommended,
            "reason": reason,
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "evidence_rows": "partial_relation_depth_detector_evidence_rows.jsonl",
            "failed_evidence_summary_rows": "partial_relation_depth_failed_evidence_summary_rows.jsonl",
            "request_summary_rows": "partial_relation_depth_request_summary_rows.jsonl",
            "unresolved_rows": "partial_relation_depth_unresolved_rows.jsonl",
            "summary": "partial_relation_depth_detector_evidence_summary.json",
        },
        "interpretation": {
            "fact": "The analyzer aggregates detector/SAM2 evidence for partial relation-depth completion before any evaluation-label join.",
            "agent_inference": "The branch can now distinguish detector-depth resolved rows from remaining relation-depth uncertainty, but it still cannot authorize a terminal ObjectNav goal.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--input-summary", type=Path)
    parser.add_argument("--request-rows", type=Path)
    parser.add_argument("--target-candidate-rows", type=Path)
    parser.add_argument("--failed-evidence-rows", type=Path)
    parser.add_argument("--context-anchor-rows", type=Path)
    parser.add_argument("--plan-rows", type=Path)
    parser.add_argument("--plan-summary", type=Path)
    parser.add_argument("--projection-summary", type=Path)
    parser.add_argument("--detector-summary", type=Path)
    parser.add_argument("--detector-associations", type=Path)
    parser.add_argument(
        "--detector-frame-summary",
        type=Path,
        default=Path(
            "local_dataset/runs/"
            "h001_expanded_retrieval_goal_validity_partial_relation_depth_detector_substrate_v1/"
            "expanded_retrieval_detector_frame_summary.jsonl"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.input_summary = source_path(args, contract, "input_summary", "input_summary")
    args.request_rows = source_path(args, contract, "request_rows", "request_rows")
    args.target_candidate_rows = source_path(args, contract, "target_candidate_rows", "target_candidate_rows")
    args.failed_evidence_rows = source_path(args, contract, "failed_evidence_rows", "failed_evidence_rows")
    args.context_anchor_rows = source_path(args, contract, "context_anchor_rows", "context_anchor_rows")
    args.plan_rows = source_path(args, contract, "plan_rows", "plan_rows")
    args.plan_summary = source_path(args, contract, "plan_summary", "plan_summary")
    args.projection_summary = source_path(args, contract, "projection_summary", "projection_summary")
    args.detector_summary = source_path(args, contract, "detector_summary", "detector_summary")
    args.detector_associations = source_path(args, contract, "detector_associations", "detector_associations")

    input_summary = load_json(args.input_summary)
    plan_summary = load_json(args.plan_summary)
    projection_summary = load_json(args.projection_summary)
    detector_summary = load_json(args.detector_summary)
    request_rows_data = load_jsonl(args.request_rows)
    target_rows_data = load_jsonl(args.target_candidate_rows)
    failed_rows_data = load_jsonl(args.failed_evidence_rows)
    plan_rows_data = load_jsonl(args.plan_rows)
    frame_rows_data = load_jsonl(args.detector_frame_summary)
    association_rows_data = load_jsonl(args.detector_associations)

    attached = attach_plan_rows(plan_rows_data, frame_rows_data)
    evidence_rows_data = build_evidence_rows(attached, association_rows_data, failed_rows_data)
    failed_summary_data = failed_summary_rows(failed_rows_data, evidence_rows_data)
    request_summary_data = request_summary_rows(
        request_rows_data,
        target_rows_data,
        failed_summary_data,
        evidence_rows_data,
    )
    unresolved_data = unresolved_rows(failed_summary_data)
    summary = summarize(
        contract=contract,
        input_summary=input_summary,
        plan_summary=plan_summary,
        projection_summary=projection_summary,
        detector_summary=detector_summary,
        association_rows=association_rows_data,
        evidence_rows=evidence_rows_data,
        failed_summary=failed_summary_data,
        request_summary=request_summary_data,
        unresolved=unresolved_data,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "partial_relation_depth_detector_evidence_rows.jsonl", evidence_rows_data)
    write_jsonl(args.out_root / "partial_relation_depth_failed_evidence_summary_rows.jsonl", failed_summary_data)
    write_jsonl(args.out_root / "partial_relation_depth_request_summary_rows.jsonl", request_summary_data)
    write_jsonl(args.out_root / "partial_relation_depth_unresolved_rows.jsonl", unresolved_data)
    write_json(args.out_root / "partial_relation_depth_detector_evidence_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["partial_relation_depth_detector_evidence_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
