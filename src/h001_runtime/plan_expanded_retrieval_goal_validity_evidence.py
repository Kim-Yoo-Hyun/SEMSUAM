import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys
from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    candidate_target_position,
    horizontal_distance,
    parse_float_list,
    plan_standoff_viewpoint,
    safe_float,
)


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_evidence_plan.v1"
POLICY_NAME = "ExpandedRetrievalGoalValidityEvidence"
PLANNER_NAME = "candidate_specific_goal_validity_standoff_v1"
OBJECTIVE_NAME = "candidate_specific_goal_validity_evidence_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"
REQUEST_ACTION = "request_goal_validity_confirmation_evidence"
EVIDENCE_ACTION = "request_candidate_specific_goal_validity_evidence"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def request_sort_key(request_id: str) -> Tuple[int, str]:
    suffix = str(request_id).split(":")[-1]
    return (int(suffix), str(request_id)) if suffix.isdigit() else (999999, str(request_id))


def candidate_rank_key(candidate: Dict[str, Any]) -> Tuple[int, int, float, str]:
    score = safe_float(candidate.get("score"))
    if score is None:
        score = safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score")) or -math.inf
    return (
        safe_int(candidate.get("generated_rank")),
        safe_int(candidate.get("semantic_rank")),
        -float(score),
        str(candidate.get("candidate_id")),
    )


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        request_id = row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")
        if request_id is not None:
            grouped[str(request_id)].append(dict(row))
    for request_rows in grouped.values():
        request_rows.sort(key=candidate_rank_key)
    return grouped


def request_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if row.get("handoff_action") != REQUEST_ACTION:
            continue
        request_id = row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")
        if request_id is None:
            continue
        indexed[str(request_id)] = dict(row)
    return indexed


def ordered_unique(values: Iterable[Optional[str]]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        output.append(text)
        seen.add(text)
    return output


def contract_expected_ids(contract: Dict[str, Any]) -> List[str]:
    target = contract.get("target_rows") or {}
    return sorted([str(value) for value in target.get("expected_request_ids") or []], key=request_sort_key)


def finite_candidate(candidate: Dict[str, Any]) -> bool:
    return candidate_target_position(candidate) is not None


def candidate_score(candidate: Dict[str, Any]) -> float:
    score = safe_float(candidate.get("score"))
    if score is None:
        score = safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score"))
    return float(score) if score is not None else -math.inf


def nearest_candidate_id(
    target: Dict[str, Any],
    candidates: Sequence[Dict[str, Any]],
    *,
    predicate: Optional[Any] = None,
) -> Optional[str]:
    target_id = str(target.get("candidate_id"))
    target_position = candidate_target_position(target)
    if target_position is None:
        return None
    best: Optional[Tuple[float, Tuple[int, int, float, str], str]] = None
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id == target_id or not finite_candidate(candidate):
            continue
        if predicate is not None and not predicate(candidate):
            continue
        position = candidate_target_position(candidate)
        if position is None:
            continue
        distance = horizontal_distance(target_position, position)
        item = (float(distance), candidate_rank_key(candidate), candidate_id)
        if best is None or item < best:
            best = item
    return None if best is None else best[2]


def context_candidates(
    target: Dict[str, Any],
    request_candidates: Sequence[Dict[str, Any]],
    max_context_candidates: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    by_id = {
        str(candidate.get("candidate_id")): dict(candidate)
        for candidate in request_candidates
        if candidate.get("candidate_id") is not None and finite_candidate(candidate)
    }
    target_id = str(target.get("candidate_id"))
    roles: Dict[str, List[str]] = defaultdict(list)
    selected_ids: List[str] = []

    def add(candidate_id: Optional[str], role: str) -> None:
        if candidate_id is None or candidate_id not in by_id:
            return
        if candidate_id not in selected_ids:
            selected_ids.append(candidate_id)
        if role not in roles[candidate_id]:
            roles[candidate_id].append(role)

    ranked = sorted(by_id.values(), key=candidate_rank_key)
    source_top_id = str(ranked[0].get("candidate_id")) if ranked else None
    target_score = candidate_score(target)
    nearest_any = nearest_candidate_id(target, ranked)
    nearest_higher = nearest_candidate_id(
        target,
        ranked,
        predicate=lambda candidate: candidate_score(candidate) > target_score,
    )
    nearest_positive = nearest_candidate_id(
        target,
        ranked,
        predicate=lambda candidate: candidate.get("positive_support") is True,
    )
    positive_ranked = [candidate for candidate in ranked if candidate.get("positive_support") is True]
    strongest_positive_id = str(positive_ranked[0].get("candidate_id")) if positive_ranked else None

    add(target_id, "target_candidate")
    add(source_top_id, "source_top_candidate")
    add(nearest_any, "nearest_spatial_rival")
    add(nearest_higher, "nearest_higher_score_rival")
    add(nearest_positive, "nearest_positive_support_rival")
    add(strongest_positive_id, "strongest_positive_support_rival")

    selected_ids = selected_ids[: max(1, int(max_context_candidates))]
    selected = [by_id[candidate_id] for candidate_id in selected_ids]
    role_map = {candidate_id: "+".join(roles[candidate_id]) for candidate_id in selected_ids}
    return selected, role_map


def candidate_snapshot(candidate: Dict[str, Any], role: str) -> Dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "candidate_role": role,
        "category": candidate.get("category"),
        "generated_rank": candidate.get("generated_rank"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "score": candidate.get("score"),
        "mean_score": candidate.get("mean_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_backend": candidate.get("candidate_backend"),
        "backend_source": candidate.get("backend_source"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "visit_position_navigable": candidate.get("visit_position_navigable"),
        "visit_position_snapped": candidate.get("visit_position_snapped"),
        "uses_gt_for_action": False,
    }


def artifact_candidate(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    score = safe_float(snapshot.get("score"))
    if score is None:
        score = safe_float(snapshot.get("support_score")) or safe_float(snapshot.get("semantic_score"))
    return {
        "candidate_id": str(snapshot.get("candidate_id")),
        "category": snapshot.get("category"),
        "score": score,
        "semantic_rank": snapshot.get("semantic_rank"),
        "semantic_score": snapshot.get("semantic_score"),
        "support_score": snapshot.get("support_score"),
        "positive_support": snapshot.get("positive_support"),
        "candidate_backend": snapshot.get("candidate_backend"),
        "candidate_reachable": snapshot.get("candidate_reachable"),
        "position": snapshot.get("position"),
        "visit_position": snapshot.get("visit_position"),
        "source": "expanded_retrieval_goal_validity_evidence_plan",
        "candidate_role": snapshot.get("candidate_role"),
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(plan_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    for row in plan_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        for snapshot in row.get("goal_validity_context_candidate_snapshots") or []:
            grouped[key][str(snapshot.get("candidate_id"))] = artifact_candidate(snapshot)

    output: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda candidate: (
                safe_int(candidate.get("semantic_rank")),
                -(safe_float(candidate.get("score")) or -math.inf),
                str(candidate.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "expanded_retrieval_goal_validity_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def count_output_forbidden(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def make_plan_row(
    *,
    args: argparse.Namespace,
    request: Dict[str, Any],
    target: Dict[str, Any],
    request_index: int,
    target_index: int,
    context: Sequence[Dict[str, Any]],
    roles: Dict[str, str],
    viewpoint: Dict[str, Any],
) -> Dict[str, Any]:
    target_id = str(target.get("candidate_id"))
    context_ids = [str(candidate.get("candidate_id")) for candidate in context if candidate.get("candidate_id") is not None]
    snapshots = [candidate_snapshot(candidate, roles.get(str(candidate.get("candidate_id")), "context_candidate")) for candidate in context]
    target_position = candidate_target_position(target)
    position = [float(item) for item in viewpoint["position"]]
    rival_ids = [candidate_id for candidate_id in context_ids if candidate_id != target_id]
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "contract_name": "expanded_retrieval_goal_validity_evidence_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": PLANNER_NAME,
        "goal_validity_objective": OBJECTIVE_NAME,
        "request_index": request_index,
        "target_index": target_index,
        "episode_key": target.get("episode_key") or request.get("episode_key"),
        "scene_id": target.get("scene_id") or request.get("scene_id"),
        "scene_key": target.get("scene_key") or request.get("scene_key"),
        "query": target.get("query") or request.get("query"),
        "target_scene_query_key": target.get("target_scene_query_key") or request.get("target_scene_query_key"),
        "rival_identity_request_id": target.get("rival_identity_request_id") or request.get("rival_identity_request_id"),
        "expanded_retrieval_request_id": target.get("expanded_retrieval_request_id")
        or request.get("expanded_retrieval_request_id"),
        "viewpoint_id": f"goal_validity:{target.get('expanded_retrieval_request_id')}:{target_id}",
        "candidate_id": target_id,
        "target_candidate_id": target_id,
        "candidate_ids": context_ids,
        "goal_validity_context_candidate_ids": context_ids,
        "goal_validity_rival_candidate_ids": rival_ids,
        "goal_validity_context_candidate_snapshots": snapshots,
        "target_candidate_role": roles.get(target_id, "target_candidate"),
        "target_generated_rank": target.get("generated_rank"),
        "target_semantic_rank": target.get("semantic_rank"),
        "target_semantic_score": target.get("semantic_score"),
        "target_support_score": target.get("support_score"),
        "target_score": target.get("score"),
        "target_mean_score": target.get("mean_score"),
        "target_positive_support": target.get("positive_support"),
        "target_candidate_reachable": target.get("candidate_reachable"),
        "target_position": target_position,
        "target_visit_position": target.get("visit_position"),
        "target_visit_position_navigable": target.get("visit_position_navigable"),
        "viewpoint_position": position,
        "viewpoint_rotation": [float(item) for item in viewpoint["rotation"]],
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_distance_from_viewpoint_m": None if target_position is None else horizontal_distance(position, target_position),
        "standoff_target_position": viewpoint.get("target_position"),
        "standoff_desired_position": viewpoint.get("desired_position"),
        "standoff_target_horizontal_distance": viewpoint.get("target_horizontal_distance"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "candidate_specific_evidence_action": "collect_candidate_specific_goal_validity_evidence",
        "candidate_specific_evidence_reason": "recovered_deeper_candidate_pool_requires_goal_validity_evidence",
        "terminal_commit_allowed": False,
        "commit_after_goal_validity_evidence": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def skip_row(
    *,
    request: Dict[str, Any],
    target: Dict[str, Any],
    request_index: int,
    target_index: int,
    reason: str,
    context_ids: Sequence[str],
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_name": "expanded_retrieval_goal_validity_evidence_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "target_index": target_index,
        "episode_key": target.get("episode_key") or request.get("episode_key"),
        "scene_id": target.get("scene_id") or request.get("scene_id"),
        "scene_key": target.get("scene_key") or request.get("scene_key"),
        "query": target.get("query") or request.get("query"),
        "expanded_retrieval_request_id": target.get("expanded_retrieval_request_id")
        or request.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": target.get("rival_identity_request_id") or request.get("rival_identity_request_id"),
        "candidate_id": target.get("candidate_id"),
        "target_candidate_id": target.get("candidate_id"),
        "target_generated_rank": target.get("generated_rank"),
        "target_semantic_rank": target.get("semantic_rank"),
        "candidate_ids": list(context_ids),
        "skip_reason": reason,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def plan_candidate(
    *,
    args: argparse.Namespace,
    request: Dict[str, Any],
    target: Dict[str, Any],
    request_candidates: Sequence[Dict[str, Any]],
    request_index: int,
    target_index: int,
    snapper: NavmeshSnapper,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    context, roles = context_candidates(target, request_candidates, int(args.max_context_candidates_per_plan))
    context_ids = [str(candidate.get("candidate_id")) for candidate in context if candidate.get("candidate_id") is not None]
    if not finite_candidate(target):
        return None, skip_row(
            request=request,
            target=target,
            request_index=request_index,
            target_index=target_index,
            reason="nonfinite_target_position",
            context_ids=context_ids,
        )
    if not context or str(target.get("candidate_id")) not in context_ids:
        return None, skip_row(
            request=request,
            target=target,
            request_index=request_index,
            target_index=target_index,
            reason="missing_target_context_candidate",
            context_ids=context_ids,
        )

    candidates_by_id = {str(candidate.get("candidate_id")): candidate for candidate in context}
    alt_id = next((candidate_id for candidate_id in context_ids if candidate_id != str(target.get("candidate_id"))), None)
    source_row = {
        "scene_id": target.get("scene_id") or request.get("scene_id"),
        "viewpoint_position": None,
    }
    viewpoint = plan_standoff_viewpoint(source_row, target, candidates_by_id, alt_id, snapper, args)
    reason: Optional[str] = None
    if viewpoint is None:
        reason = "standoff_unavailable"
    elif "fallback" in str(viewpoint.get("viewpoint_source") or ""):
        reason = "standoff_fallback_forbidden"
    elif bool(args.require_navmesh_standoff) and (
        viewpoint.get("viewpoint_source") != "standoff_navmesh" or viewpoint.get("navmesh_navigable") is not True
    ):
        reason = "standoff_navmesh_required"
    elif viewpoint.get("projection_sane") is not True:
        reason = "standoff_no_valid_yaw"
    else:
        distance = safe_float(viewpoint.get("target_horizontal_distance"))
        if distance is None:
            reason = "standoff_missing_target_distance"
        elif distance < float(args.min_standoff_distance_m):
            reason = "standoff_all_too_close"
        elif distance > float(args.max_standoff_distance_m):
            reason = "standoff_all_too_far"

    if reason is not None:
        return None, skip_row(
            request=request,
            target=target,
            request_index=request_index,
            target_index=target_index,
            reason=reason,
            context_ids=context_ids,
        )
    return make_plan_row(
        args=args,
        request=request,
        target=target,
        request_index=request_index,
        target_index=target_index,
        context=context,
        roles=roles,
        viewpoint=viewpoint,
    ), None


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    expected = contract.get("target_rows") or {}
    minimum = contract.get("minimum_plan_gate") or {}
    planned_request_ids = sorted(
        {
            str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
            for row in plan_rows
        },
        key=request_sort_key,
    )
    evidence_request_ids = sorted(
        {
            str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
            for row in evidence_rows
        },
        key=request_sort_key,
    )
    plan_rows_by_request = Counter(
        str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")) for row in plan_rows
    )
    context_sizes = [len(row.get("goal_validity_context_candidate_ids") or []) for row in plan_rows]
    target_distances = [
        float(value)
        for value in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if value is not None
    ]
    fallback_rows = [row for row in plan_rows if "fallback" in str(row.get("viewpoint_source") or "")]
    terminal_rows = [row for row in [*plan_rows, *skipped_rows] if row.get("terminal_commit_allowed") is True]
    forbidden = count_output_forbidden([*plan_rows, *skipped_rows])
    gate = {
        "request_rows_passed": len(request_rows) == int(minimum.get("request_rows", expected.get("expected_request_rows", 0))),
        "candidate_evidence_target_rows_passed": len(evidence_rows)
        == int(minimum.get("candidate_evidence_target_rows", expected.get("expected_candidate_evidence_rows", 0))),
        "request_ids_passed": evidence_request_ids == contract_expected_ids(contract),
        "planned_request_rows_passed": len(planned_request_ids)
        == int(minimum.get("planned_request_rows", len(contract_expected_ids(contract)))),
        "plan_rows_minimum_passed": len(plan_rows) >= int(minimum.get("plan_rows_minimum", 0)),
        "plan_rows_per_request_minimum_passed": bool(plan_rows_by_request)
        and min(plan_rows_by_request.values()) >= int(minimum.get("plan_rows_per_request_minimum", 0)),
        "candidate_artifact_rows_minimum_passed": len(artifact_rows)
        >= int(minimum.get("candidate_artifact_rows_minimum", 1)),
        "fallback_rows_passed": len(fallback_rows) == int(minimum.get("fallback_rows", 0)),
        "output_forbidden_action_fields_passed": len(forbidden)
        == int(minimum.get("output_forbidden_action_fields", 0)),
        "terminal_commit_rows_passed": len(terminal_rows) == int(minimum.get("terminal_commit_rows", 0)),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in [*plan_rows, *skipped_rows]),
        "paper_claim_allowed": False,
    }
    gate["goal_validity_evidence_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "request_rows": str(args.request_rows),
        "candidate_evidence_rows": str(args.candidate_evidence_rows),
        "out_root": str(args.out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "goal_validity_objective": OBJECTIVE_NAME,
        "request_rows_count": len(request_rows),
        "candidate_evidence_target_rows": len(evidence_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "planned_request_ids": planned_request_ids,
        "evidence_request_ids": evidence_request_ids,
        "plan_rows_by_request": dict(sorted(plan_rows_by_request.items())),
        "plan_rows_per_request_min": min(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "plan_rows_per_request_max": max(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "skipped_reason_counts": dict(sorted(Counter(str(row.get("skip_reason")) for row in skipped_rows).items())),
        "viewpoint_source_counts": dict(sorted(Counter(str(row.get("viewpoint_source")) for row in plan_rows).items())),
        "context_size_stats": number_stats([float(value) for value in context_sizes]),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_candidate_count": sum(int(row.get("candidate_count") or 0) for row in artifact_rows),
        "fallback_rows": len(fallback_rows),
        "terminal_commit_rows": len(terminal_rows),
        "output_forbidden_action_field_count": len(forbidden),
        "output_forbidden_action_fields": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "interpretation": {
            "facts": (
                "Planner consumes recovered-row candidate evidence targets and writes candidate-specific "
                "standoff observations without evaluation labels."
            ),
            "inference": (
                "This is an evidence-planning substrate. It tests whether later detector/SAM2 evidence can "
                "separate candidate-specific goal validity from category visibility."
            ),
        },
        "output_files": {
            "plan": "goal_validity_evidence_plan.jsonl",
            "skipped": "goal_validity_evidence_skipped.jsonl",
            "candidate_artifact": "goal_validity_evidence_candidate_artifact.jsonl",
            "summary": "goal_validity_evidence_plan_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    requests = request_index(load_jsonl(Path(args.request_rows)))
    evidence_by_request = group_by_request(load_jsonl(Path(args.candidate_evidence_rows)))
    expected_ids = contract_expected_ids(contract)
    observed_ids = sorted(evidence_by_request.keys(), key=request_sort_key)
    if observed_ids != expected_ids:
        raise ValueError(f"unexpected evidence request ids: observed={observed_ids} expected={expected_ids}")
    missing_requests = [request_id for request_id in expected_ids if request_id not in requests]
    if missing_requests:
        raise ValueError(f"missing request rows: {missing_requests}")

    out_root = Path(args.out_root)
    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    try:
        for request_index_value, request_id in enumerate(expected_ids):
            request = requests[request_id]
            candidates = evidence_by_request[request_id]
            if int(args.max_candidates_per_request) > 0:
                candidates = candidates[: int(args.max_candidates_per_request)]
            for target_index, target in enumerate(candidates):
                row, skipped = plan_candidate(
                    args=args,
                    request=request,
                    target=target,
                    request_candidates=candidates,
                    request_index=request_index_value,
                    target_index=target_index,
                    snapper=snapper,
                )
                if row is not None:
                    plan_rows.append(row)
                if skipped is not None:
                    skipped_rows.append(skipped)
    finally:
        snapper.close()

    artifact_rows = candidate_artifact_rows(plan_rows)
    write_jsonl(out_root / "goal_validity_evidence_plan.jsonl", plan_rows)
    write_jsonl(out_root / "goal_validity_evidence_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "goal_validity_evidence_candidate_artifact.jsonl", artifact_rows)
    summary = summarize(
        args=args,
        contract=contract,
        request_rows=[requests[request_id] for request_id in expected_ids],
        evidence_rows=[row for request_id in expected_ids for row in evidence_by_request[request_id]],
        plan_rows=plan_rows,
        skipped_rows=skipped_rows,
        artifact_rows=artifact_rows,
    )
    write_json(out_root / "goal_validity_evidence_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan candidate-specific goal-validity evidence observations for recovered expanded-retrieval rows."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--request-rows", required=True)
    parser.add_argument("--candidate-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--run-id", default="h001_expanded_retrieval_goal_validity_evidence_v1")
    parser.add_argument("--max-candidates-per-request", type=int, default=0)
    parser.add_argument("--max-context-candidates-per-plan", type=int, default=5)
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25, 2.75])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--require-navmesh-standoff", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--projection-anchor-height-offsets-m",
        type=parse_float_list,
        default=[0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4],
    )
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["goal_validity_evidence_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
