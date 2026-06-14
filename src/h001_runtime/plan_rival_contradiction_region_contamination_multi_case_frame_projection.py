import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    candidate_floor_y,
    candidate_target_position,
    horizontal_distance,
    normalize_xz,
    plan_standoff_viewpoint,
    quaternion_xyzw_from_yaw,
    safe_float,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_multi_case_frame_plan.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_rival_contradiction_region_contamination_multi_case_frame_projection_v1.json"
)
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_source_v1"
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_frame_plan_v1"
GEOMETRY_ARTIFACT_DEFAULT = (
    "local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/"
    "expanded_retrieval_local_context_candidate_artifact.jsonl"
)
POLICY_NAME = "RivalContradictionRegionContaminationEvidenceMultiCase"
PLANNER_NAME = "rival_contradiction_region_contamination_multi_case_frame_projection_v1"
VIEWPOINT_POLICY = "multi_case_pairwise_rival_region_contamination_probe_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def parse_float_list(text: str) -> List[float]:
    values = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated float")
    return values


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def finite_vector(value: Any, size: int) -> bool:
    if not isinstance(value, list) or len(value) != size:
        return False
    return all(safe_float(item) is not None for item in value)


def unique_ordered(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        output.append(text)
        seen.add(text)
    return output


def candidate_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    prefix, _, suffix = text.rpartition(":")
    try:
        index = int(suffix)
    except ValueError:
        index = 999999
    return prefix, index, text


def source_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("request_id") or row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def copy_candidate(candidate: Mapping[str, Any], role: str) -> Dict[str, Any]:
    copied = dict(candidate)
    copied["candidate_id"] = str(candidate.get("candidate_id"))
    copied["candidate_role"] = role
    copied["uses_gt_for_action"] = False
    copied["paper_claim_allowed"] = False
    return copied


def geometry_index(path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_jsonl(path):
        scene_key = str(row.get("scene_key"))
        query = str(row.get("query"))
        indexed[(scene_key, query)] = row
    return indexed


def make_source_row(scene_id: str, candidate: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "scene_id": scene_id,
        "viewpoint_position": candidate.get("visit_position") or candidate.get("position"),
        "uses_gt_for_action": False,
    }


def pair_midpoint(a: Mapping[str, Any], b: Mapping[str, Any]) -> Optional[List[float]]:
    a_position = candidate_target_position(dict(a))
    b_position = candidate_target_position(dict(b))
    a_visit = vector(a.get("visit_position"))
    if a_position is None or b_position is None:
        return None
    return [
        (float(a_position[0]) + float(b_position[0])) / 2.0,
        float(a_visit[1]) if a_visit is not None else float(a_position[1]),
        (float(a_position[2]) + float(b_position[2])) / 2.0,
    ]


def planned_pair_viewpoint(
    *,
    scene_id: str,
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
    preferred_side: str,
) -> Optional[Dict[str, Any]]:
    a_position = candidate_target_position(dict(a))
    b_position = candidate_target_position(dict(b))
    midpoint = pair_midpoint(a, b)
    if a_position is None or b_position is None or midpoint is None:
        return None
    unit = normalize_xz(float(b_position[0]) - float(a_position[0]), float(b_position[2]) - float(a_position[2]))
    if unit is None:
        return None
    ux, uz = unit
    left = (-uz, ux, "pair_perpendicular_left")
    right = (uz, -ux, "pair_perpendicular_right")
    directions = [left, right] if preferred_side == "left" else [right, left]
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in args.common_pair_distances:
        for dx, dz, direction_source in directions:
            desired = [
                float(midpoint[0]) + float(dx) * float(distance),
                float(midpoint[1]),
                float(midpoint[2]) + float(dz) * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            a_distance = horizontal_distance(snapped, a_position)
            b_distance = horizontal_distance(snapped, b_position)
            if a_distance < float(args.min_standoff_distance_m) or b_distance < float(args.min_standoff_distance_m):
                continue
            if a_distance > float(args.max_standoff_distance_m) or b_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, midpoint)
            if yaw is None:
                continue
            side_penalty = 0.0 if direction_source.endswith(preferred_side) else 0.25
            score = abs(a_distance - b_distance) + 0.20 * (snap_distance or 0.0) + side_penalty - (0.25 if navigable else 0.0)
            item = {
                "position": snapped,
                "rotation": quaternion_xyzw_from_yaw(yaw),
                "yaw": float(yaw),
                "target_position": midpoint,
                "pair_midpoint": midpoint,
                "target_horizontal_distance": float(max(a_distance, b_distance)),
                "candidate_a_distance_m": float(a_distance),
                "candidate_b_distance_m": float(b_distance),
                "desired_position": desired,
                "snap_distance": snap_distance,
                "navmesh_snapped": snap_distance is not None,
                "navmesh_navigable": navigable,
                "direction_source": direction_source,
                "standoff_distance_requested": float(distance),
                "viewpoint_source": "pair_region_navmesh" if snap_distance is not None else "pair_region_geometry",
                "projection_sane": True,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, item)
    return None if best is None else best[1]


def candidate_viewpoint(
    *,
    scene_id: str,
    target: Mapping[str, Any],
    context: Mapping[str, Any],
    candidates: Mapping[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    if candidate_target_position(dict(target)) is None or candidate_floor_y(dict(target), make_source_row(scene_id, target)) is None:
        return None
    viewpoint = plan_standoff_viewpoint(
        make_source_row(scene_id, target),
        dict(target),
        dict(candidates),
        str(context.get("candidate_id")),
        snapper,
        args,
    )
    if viewpoint is None:
        return None
    distance = safe_float(viewpoint.get("target_horizontal_distance"))
    if distance is None:
        return None
    if distance < float(args.min_standoff_distance_m) or distance > float(args.max_standoff_distance_m):
        return None
    return viewpoint


def select_viewpoint(
    *,
    observation: Mapping[str, Any],
    scene_id: str,
    candidates: Mapping[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    target_id = str(observation.get("target_candidate_id"))
    context_id = str(observation.get("context_candidate_id"))
    candidate_a_id = str(observation.get("candidate_a_id"))
    candidate_b_id = str(observation.get("candidate_b_id"))
    if target_id not in candidates or context_id not in candidates:
        return None
    role = str(observation.get("observation_role"))
    if role in {"candidate_a_own_view", "candidate_b_own_view"}:
        return candidate_viewpoint(
            scene_id=scene_id,
            target=candidates[target_id],
            context=candidates[context_id],
            candidates=candidates,
            snapper=snapper,
            args=args,
        )
    if candidate_a_id not in candidates or candidate_b_id not in candidates:
        return None
    preferred_side = "left" if role == "shared_region_or_relation_anchor_view" else "right"
    viewpoint = planned_pair_viewpoint(
        scene_id=scene_id,
        a=candidates[candidate_a_id],
        b=candidates[candidate_b_id],
        snapper=snapper,
        args=args,
        preferred_side=preferred_side,
    )
    if viewpoint is not None:
        return viewpoint
    return candidate_viewpoint(
        scene_id=scene_id,
        target=candidates[target_id],
        context=candidates[context_id],
        candidates=candidates,
        snapper=snapper,
        args=args,
    )


def candidate_role_for(candidate_id: str, pair_roles: Sequence[Mapping[str, Any]], original_role: Any) -> str:
    roles = []
    for row in pair_roles:
        if str(row.get("candidate_id")) == candidate_id:
            role = str(row.get("candidate_role") or row.get("role_scope") or "")
            if role and role not in roles:
                roles.append(role)
    original = str(original_role or "")
    if original and original not in roles:
        roles.append(original)
    return "+".join(roles) if roles else "multi_case_pair_candidate"


def build_candidate_artifacts(
    *,
    observations: Sequence[Mapping[str, Any]],
    geometry: Mapping[Tuple[str, str], Mapping[str, Any]],
    candidate_role_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[Tuple[str, str], List[str]], List[Dict[str, Any]]]:
    needed_by_key: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    pair_roles_by_key: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in observations:
        key = (str(row.get("scene_key")), str(row.get("query")))
        for candidate_id in row.get("candidate_ids") or [row.get("target_candidate_id"), row.get("context_candidate_id")]:
            for value in unique_ordered([candidate_id]):
                if value not in needed_by_key[key]:
                    needed_by_key[key].append(value)
    for row in candidate_role_rows:
        key = (str(row.get("scene_key")), str(row.get("query")))
        pair_roles_by_key[key].append(row)

    artifacts: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []
    for key in sorted(needed_by_key):
        source = geometry.get(key)
        if source is None:
            missing.append({"scene_key": key[0], "query": key[1], "reason": "missing_geometry_source"})
            continue
        by_id = {str(candidate.get("candidate_id")): candidate for candidate in source.get("candidates") or []}
        candidates: List[Dict[str, Any]] = []
        for candidate_id in sorted(needed_by_key[key], key=candidate_sort_key):
            candidate = by_id.get(candidate_id)
            if candidate is None:
                missing.append({"scene_key": key[0], "query": key[1], "candidate_id": candidate_id, "reason": "missing_geometry_candidate"})
                continue
            candidates.append(copy_candidate(candidate, candidate_role_for(candidate_id, pair_roles_by_key.get(key, []), candidate.get("candidate_role"))))
        artifacts.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "rival_contradiction_region_contamination_multi_case_candidate_artifact",
                "scene_id": source.get("scene_id"),
                "scene_key": source.get("scene_key"),
                "query": source.get("query"),
                "candidate_count": len(candidates),
                "candidate_ids": [str(candidate.get("candidate_id")) for candidate in candidates],
                "candidates": candidates,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return artifacts, dict(needed_by_key), missing


def candidate_lookup_by_scene_query(artifacts: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Dict[str, Any]]]:
    lookup: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
    for artifact in artifacts:
        key = (str(artifact.get("scene_key")), str(artifact.get("query")))
        lookup[key] = {str(candidate.get("candidate_id")): dict(candidate) for candidate in artifact.get("candidates") or []}
    return lookup


def geometry_lookup_by_scene_query(artifacts: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str], Mapping[str, Any]]:
    return {(str(artifact.get("scene_key")), str(artifact.get("query"))): artifact for artifact in artifacts}


def plan_row(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    observation: Mapping[str, Any],
    source: Mapping[str, Any],
    candidates: Mapping[str, Dict[str, Any]],
    viewpoint: Mapping[str, Any],
    row_index: int,
) -> Dict[str, Any]:
    target_id = str(observation.get("target_candidate_id"))
    context_id = str(observation.get("context_candidate_id"))
    target = candidates[target_id]
    context = candidates[context_id]
    candidate_ids = unique_ordered(observation.get("candidate_ids") or [target_id, context_id])
    midpoint = pair_midpoint(candidates[str(observation.get("candidate_a_id"))], candidates[str(observation.get("candidate_b_id"))])
    request_id = source_request_id(observation)
    role = str(observation.get("observation_role"))
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "rival_contradiction_region_contamination_multi_case_frame_ready_plan",
        "contract_name": contract.get("contract_name"),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "viewpoint_id": f"rival_contamination_multi_case:{request_id}:{role}:{row_index}",
        "multi_case_source_id": observation.get("multi_case_source_id"),
        "observation_index": observation.get("observation_index"),
        "frame_plan_index": row_index,
        "episode_key": observation.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": observation.get("scene_key") or source.get("scene_key"),
        "query": observation.get("query") or source.get("query"),
        "request_id": request_id,
        "expanded_retrieval_request_id": request_id,
        "rival_identity_request_id": request_id,
        "source_name": observation.get("source_name"),
        "role": role,
        "role_scope": observation.get("role_scope"),
        "view_role": role,
        "observation_role": role,
        "rival_observation_role": role,
        "evidence_axis": observation.get("evidence_axis"),
        "rival_evidence_axis": observation.get("evidence_axis"),
        "viewpoint_pair_role": "multi_case_rival_contradiction_region_contamination_candidate_pair",
        "candidate_id": target_id,
        "target_candidate_id": target_id,
        "context_candidate_id": context_id,
        "candidate_ids": candidate_ids,
        "candidate_a_id": observation.get("candidate_a_id"),
        "candidate_b_id": observation.get("candidate_b_id"),
        "candidate_ordering_source": observation.get("candidate_ordering_source"),
        "candidate_pair_preserved": True,
        "target_position": viewpoint.get("target_position") or target.get("position"),
        "target_visit_position": target.get("visit_position"),
        "context_position": context.get("position"),
        "context_visit_position": context.get("visit_position"),
        "pair_midpoint": viewpoint.get("pair_midpoint") or midpoint,
        "viewpoint_position": viewpoint.get("position"),
        "viewpoint_rotation": viewpoint.get("rotation"),
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_distance_from_viewpoint_m": viewpoint.get("target_horizontal_distance"),
        "candidate_a_distance_from_viewpoint_m": viewpoint.get("candidate_a_distance_m"),
        "candidate_b_distance_from_viewpoint_m": viewpoint.get("candidate_b_distance_m"),
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
        "goal_validity_risk": None,
        "viewpoint_evidence_gap": None,
        "map_pose_consistency_uncertainty": None,
        "map_pose_consistency_delta": None,
        "task_evidence_join_ready": False,
        "terminal_commit_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def skip_row(observation: Mapping[str, Any], reason: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "rival_contradiction_region_contamination_multi_case_frame_plan_skipped",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "skip_reason": reason,
        "multi_case_source_id": observation.get("multi_case_source_id"),
        "episode_key": observation.get("episode_key"),
        "scene_key": observation.get("scene_key"),
        "query": observation.get("query"),
        "request_id": source_request_id(observation),
        "observation_role": observation.get("observation_role"),
        "target_candidate_id": observation.get("target_candidate_id"),
        "context_candidate_id": observation.get("context_candidate_id"),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def scan_forbidden_keys(value: Any, prefix: str = "") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            allowed = {
                "uses_gt_for_action",
                "uses_gt_for_analysis",
                "goal_validity_risk",
                "map_pose_consistency_uncertainty",
                "map_pose_consistency_delta",
            }
            if lowered not in allowed and any(
                term in lowered for term in ("candidate_correct", "correct_candidate", "valid_candidate", "wrong_goal", "evaluation_only", "gt_")
            ):
                findings.append(child_path)
            findings.extend(scan_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_forbidden_keys(child, f"{prefix}[{index}]"))
    return findings


def forbidden_findings(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{item}" for item in scan_forbidden_keys(dict(row))])
    return findings


def candidate_tuple_set_from_observations(observations: Sequence[Mapping[str, Any]]) -> set[Tuple[str, str, str]]:
    return {
        (str(row.get("scene_key")), str(row.get("query")), str(candidate_id))
        for row in observations
        for candidate_id in (row.get("candidate_ids") or [row.get("target_candidate_id"), row.get("context_candidate_id")])
        if candidate_id is not None
    }


def candidate_tuple_set_from_artifacts(artifacts: Sequence[Mapping[str, Any]]) -> set[Tuple[str, str, str]]:
    return {
        (str(row.get("scene_key")), str(row.get("query")), str(candidate.get("candidate_id")))
        for row in artifacts
        for candidate in row.get("candidates") or []
    }


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    plan_rows: Sequence[Mapping[str, Any]],
    skipped_rows: Sequence[Mapping[str, Any]],
    candidate_artifacts: Sequence[Mapping[str, Any]],
    artifact_missing: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    frame_contract = contract.get("frame_projection_contract") or {}
    source_gate = contract.get("source_gate") or {}
    expected_rows = int(frame_contract.get("expected_symbolic_observation_seed_rows") or frame_contract.get("minimum_frame_plan_rows") or 72)
    expected_source_rows = int(frame_contract.get("expected_source_rows") or source_gate.get("source_rows") or 18)
    expected_scene_query_pairs = int(source_gate.get("scene_query_pairs") or len({(row.get("scene_key"), row.get("query")) for row in observations}))
    required_roles = set(frame_contract.get("required_observation_roles") or [])
    expected_role_count = expected_rows // max(len(required_roles), 1)
    required_axes = set(frame_contract.get("required_evidence_axes") or [])
    required_tuples = candidate_tuple_set_from_observations(observations)
    covered_tuples = candidate_tuple_set_from_artifacts(candidate_artifacts)
    missing_tuples = sorted(required_tuples - covered_tuples)
    forbidden = forbidden_findings([*plan_rows, *skipped_rows, *candidate_artifacts])
    plan_roles = {str(row.get("observation_role")) for row in plan_rows}
    plan_axes = {str(row.get("evidence_axis")) for row in plan_rows}
    terminal_rows = [
        row
        for row in plan_rows
        if row.get("terminal_commit_allowed") is True
        or row.get("candidate_commit_allowed") is True
        or row.get("candidate_rejection_allowed") is True
        or row.get("terminal_commit") is True
        or row.get("candidate_commit") is True
        or row.get("candidate_rejection") is True
    ]
    finite_rows = [
        row
        for row in plan_rows
        if finite_vector(row.get("viewpoint_position"), 3) and finite_vector(row.get("viewpoint_rotation"), 4)
    ]
    explicit_pair_rows = [
        row
        for row in plan_rows
        if isinstance(row.get("candidate_ids"), list) and len(row.get("candidate_ids") or []) == 2
    ]
    role_counts = compact_counter(row.get("observation_role") for row in plan_rows)
    gate = {
        "expected_source_rows_passed": len({row.get("multi_case_source_id") for row in observations}) == expected_source_rows,
        "expected_decision_rows_passed": len(plan_rows) == expected_rows,
        "skipped_rows_passed": len(skipped_rows) == 0,
        "required_observation_roles_passed": required_roles.issubset(plan_roles),
        "required_evidence_axes_passed": required_axes.issubset(plan_axes),
        "observation_role_counts_expected_passed": all(role_counts.get(role) == expected_role_count for role in required_roles),
        "finite_viewpoint_rows_passed": len(finite_rows) == len(plan_rows),
        "explicit_candidate_pair_rows_passed": len(explicit_pair_rows) == len(plan_rows),
        "candidate_artifact_rows_passed": len(candidate_artifacts) == expected_scene_query_pairs,
        "candidate_artifact_candidate_tuple_coverage_passed": not missing_tuples and not artifact_missing,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "terminal_commit_rows_passed": len(terminal_rows) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in [*plan_rows, *skipped_rows, *candidate_artifacts]),
        "paper_claim_allowed_true_rows_passed": all(row.get("paper_claim_allowed") is False for row in [*plan_rows, *skipped_rows, *candidate_artifacts]),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    gate["rival_contradiction_region_contamination_multi_case_frame_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "input_root": str(args.input_root),
        "geometry_candidate_artifact": str(args.geometry_candidate_artifact),
        "out_root": str(args.out_root),
        "run_id": str(args.run_id),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "source_observation_rows": len(observations),
        "multi_case_source_rows": len({row.get("multi_case_source_id") for row in observations}),
        "frame_plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "candidate_artifact_rows": len(candidate_artifacts),
        "candidate_tuple_required": len(required_tuples),
        "candidate_tuple_covered": len(covered_tuples & required_tuples),
        "candidate_tuple_missing": len(missing_tuples),
        "candidate_tuple_missing_examples": missing_tuples[:20],
        "candidate_artifact_missing_rows": list(artifact_missing)[:20],
        "observation_role_counts": role_counts,
        "evidence_axis_counts": compact_counter(row.get("evidence_axis") for row in plan_rows),
        "viewpoint_source_counts": compact_counter(row.get("viewpoint_source") for row in plan_rows),
        "standoff_direction_source_counts": compact_counter(row.get("standoff_direction_source") for row in plan_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": sum(1 for row in plan_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in plan_rows if row.get("candidate_rejection") is True),
        "uses_gt_for_action_true_rows": sum(1 for row in plan_rows if row.get("uses_gt_for_action") is True),
        "paper_claim_allowed_true_rows": sum(1 for row in plan_rows if row.get("paper_claim_allowed") is True),
        "projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "gate": gate,
        "output_files": {
            "frame_plan_rows": "rival_contradiction_region_contamination_multi_case_frame_plan_rows.jsonl",
            "candidate_artifact": "rival_contradiction_region_contamination_multi_case_candidate_artifact.jsonl",
            "skipped_rows": "rival_contradiction_region_contamination_multi_case_frame_plan_skipped_rows.jsonl",
            "summary": "rival_contradiction_region_contamination_multi_case_frame_plan_summary.json",
        },
        "interpretation": {
            "fact": "The planner resolves 72 symbolic multi-case observation roles into frame-ready Habitat viewpoints using local-context candidate geometry.",
            "agent_inference": "Passing this gate means the frozen multi-case nonterminal observation roles are renderable inputs for a frame/projection smoke; it does not establish detector evidence, wrong-goal reduction, wasted-path reduction, or map/pose consistency utility.",
            "paper_claim": "No paper claim is allowed from this planner output alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    input_root = Path(args.input_root)
    out_root = Path(args.out_root)
    observations = load_jsonl(input_root / "rival_contradiction_region_contamination_multi_case_observation_seed_rows.jsonl")
    candidate_role_rows = load_jsonl(input_root / "rival_contradiction_region_contamination_multi_case_candidate_role_rows.jsonl")
    geometry = geometry_index(Path(args.geometry_candidate_artifact))
    candidate_artifacts, _, artifact_missing = build_candidate_artifacts(
        observations=observations,
        geometry=geometry,
        candidate_role_rows=candidate_role_rows,
    )
    candidates_by_key = candidate_lookup_by_scene_query(candidate_artifacts)
    source_by_key = geometry_lookup_by_scene_query(candidate_artifacts)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    snapper = NavmeshSnapper(args.data_root)
    try:
        for row_index, observation in enumerate(observations, start=1):
            key = (str(observation.get("scene_key")), str(observation.get("query")))
            source = source_by_key.get(key)
            candidates = candidates_by_key.get(key, {})
            if source is None:
                skipped_rows.append(skip_row(observation, "missing_scene_query_candidate_artifact"))
                continue
            if not all(str(candidate_id) in candidates for candidate_id in (observation.get("candidate_ids") or [])):
                skipped_rows.append(skip_row(observation, "missing_pair_candidate_in_artifact"))
                continue
            viewpoint = select_viewpoint(
                observation=observation,
                scene_id=str(source.get("scene_id")),
                candidates=candidates,
                snapper=snapper,
                args=args,
            )
            if viewpoint is None:
                skipped_rows.append(skip_row(observation, "missing_frame_ready_viewpoint"))
                continue
            plan_rows.append(
                plan_row(
                    args=args,
                    contract=contract,
                    observation=observation,
                    source=source,
                    candidates=candidates,
                    viewpoint=viewpoint,
                    row_index=row_index,
                )
            )
    finally:
        snapper.close()

    summary = build_summary(
        args=args,
        contract=contract,
        observations=observations,
        plan_rows=plan_rows,
        skipped_rows=skipped_rows,
        candidate_artifacts=candidate_artifacts,
        artifact_missing=artifact_missing,
    )
    write_jsonl(out_root / "rival_contradiction_region_contamination_multi_case_frame_plan_rows.jsonl", plan_rows)
    write_jsonl(out_root / "rival_contradiction_region_contamination_multi_case_candidate_artifact.jsonl", candidate_artifacts)
    write_jsonl(out_root / "rival_contradiction_region_contamination_multi_case_frame_plan_skipped_rows.jsonl", skipped_rows)
    write_json(out_root / "rival_contradiction_region_contamination_multi_case_frame_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Resolve multi-case rival contradiction / region contamination rows into frame-ready Habitat viewpoints.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--geometry-candidate-artifact", default=GEOMETRY_ARTIFACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--run-id", default="h001_rival_contradiction_region_contamination_multi_case_frame_projection_v1")
    parser.add_argument("--common-pair-distances", type=parse_float_list, default=[1.5, 2.0, 2.5, 3.0])
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25, 2.75])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--projection-anchor-height-offsets-m", type=parse_float_list, default=[0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4])
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["rival_contradiction_region_contamination_multi_case_frame_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
