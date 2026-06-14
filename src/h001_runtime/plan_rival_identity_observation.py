import argparse
import json
import math
from collections import Counter
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys
from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    candidate_target_position,
    horizontal_distance,
    parse_float_list,
    plan_standoff_viewpoint,
    quaternion_xyzw_from_yaw,
    safe_float,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.rival_identity_observation_plan.v1"
POLICY_NAME = "RivalIdentityPairProbe"


def active_planner_name(args: argparse.Namespace) -> str:
    if str(args.viewpoint_mode) == "standoff":
        return "rival_identity_pair_probe_standoff_v1"
    return "rival_identity_pair_probe_v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def resolve_path(path_text: str, runs_root: Path, workspace_root: Path) -> Path:
    path = Path(path_text)
    if path.exists():
        return path
    if path_text.startswith("local_dataset/runs/"):
        return runs_root / path_text[len("local_dataset/runs/") :]
    workspace_path = workspace_root / path_text
    if workspace_path.exists():
        return workspace_path
    return path


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


def evidence_by_candidate_id(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(candidate.get("candidate_id")): candidate
        for candidate in row.get("candidate_evidence") or []
        if candidate.get("candidate_id") is not None
    }


def action_row_index(rows: Sequence[Dict[str, Any]], role: str, source_name: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        row = dict(row)
        row["source_role"] = role
        row["source_name"] = source_name
        index[(role, str(row.get("episode_key")))] = row
    return index


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def target_candidate_ids(request: Dict[str, Any], max_targets: int, max_rivals: int) -> List[str]:
    focus_id = None if request.get("focus_candidate_id") is None else str(request.get("focus_candidate_id"))
    rivals = ordered_unique(str(candidate_id) for candidate_id in request.get("rival_candidate_ids") or [])
    rivals = [candidate_id for candidate_id in rivals if candidate_id != focus_id]
    return ordered_unique([focus_id, *rivals[:max_rivals]])[:max_targets]


def viewpoint_from_candidate(candidate: Dict[str, Any]) -> Optional[Tuple[List[float], List[float], str]]:
    viewpoint = vector(candidate.get("visit_position"))
    source = "candidate_visit_position"
    if viewpoint is None:
        viewpoint = vector(candidate.get("position"))
        source = "candidate_position_fallback"
    target = candidate_target_position(candidate)
    if viewpoint is None or target is None:
        return None
    yaw = yaw_to_point(viewpoint, target)
    if yaw is None:
        rotation = candidate.get("visit_rotation")
        if not (isinstance(rotation, list) and len(rotation) == 4 and all(safe_float(item) is not None for item in rotation)):
            rotation = [0.0, 0.0, 0.0, 1.0]
        return viewpoint, [float(item) for item in rotation], f"{source}_rotation_fallback"
    return viewpoint, quaternion_xyzw_from_yaw(yaw), f"{source}_heading_to_target"


def alternate_candidate_id(
    candidate_id: str,
    candidate_ids: Sequence[str],
    candidates: Dict[str, Dict[str, Any]],
) -> Optional[str]:
    for other_id in candidate_ids:
        if other_id != candidate_id and other_id in candidates:
            return other_id
    for other_id in candidates:
        if other_id != candidate_id:
            return other_id
    return None


def standoff_viewpoint_from_candidate(
    *,
    args: argparse.Namespace,
    action_row: Dict[str, Any],
    candidate_id: str,
    candidate_ids: Sequence[str],
    candidate: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    snapper: Optional[NavmeshSnapper],
) -> Tuple[Optional[Tuple[List[float], List[float], str, Dict[str, Any]]], Optional[str], Dict[str, Any]]:
    if snapper is None:
        return None, "standoff_snapper_required", {}
    alt_id = alternate_candidate_id(candidate_id, candidate_ids, candidates)
    viewpoint = plan_standoff_viewpoint(action_row, candidate, candidates, alt_id, snapper, args)
    if viewpoint is None:
        return None, "standoff_unavailable", {"standoff_alt_candidate_id": alt_id}

    metadata = {
        "standoff_alt_candidate_id": alt_id,
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
    }
    viewpoint_source = str(viewpoint.get("viewpoint_source") or "")
    target_distance = safe_float(viewpoint.get("target_horizontal_distance"))
    if "fallback" in viewpoint_source:
        return None, "standoff_unavailable", metadata
    if bool(args.require_navmesh_standoff) and (
        viewpoint_source != "standoff_navmesh" or viewpoint.get("navmesh_navigable") is not True
    ):
        return None, "standoff_navmesh_required", metadata
    if target_distance is None:
        return None, "standoff_missing_target_distance", metadata
    if target_distance < float(args.min_standoff_distance_m):
        return None, "standoff_all_too_close", metadata
    if target_distance > float(args.max_standoff_distance_m):
        return None, "standoff_all_too_far", metadata
    if viewpoint.get("projection_sane") is not True:
        return None, "standoff_no_valid_yaw", metadata
    return (
        (
            [float(item) for item in viewpoint["position"]],
            [float(item) for item in viewpoint["rotation"]],
            viewpoint_source,
            metadata,
        ),
        None,
        metadata,
    )


def copy_candidate_fields(candidate: Dict[str, Any], prefix: str) -> Dict[str, Any]:
    fields = [
        "semantic_rank",
        "semantic_score",
        "support_score",
        "detector_score_max",
        "associated_heading_count",
        "mask_hit_count",
        "box_hit_count",
        "visible_count",
        "min_depth_error_m",
        "positive_support",
    ]
    return {f"{prefix}_{field}": candidate.get(field) for field in fields if field in candidate}


def candidate_from_plan_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": row.get("target_candidate_id"),
        "category": row.get("query"),
        "score": row.get("target_semantic_score"),
        "semantic_rank": row.get("target_semantic_rank"),
        "semantic_score": row.get("target_semantic_score"),
        "support_score": row.get("target_support_score"),
        "detector_score_max": row.get("target_detector_score_max"),
        "associated_heading_count": row.get("target_associated_heading_count"),
        "mask_hit_count": row.get("target_mask_hit_count"),
        "box_hit_count": row.get("target_box_hit_count"),
        "visible_count": row.get("target_visible_count"),
        "min_depth_error_m": row.get("target_min_depth_error_m"),
        "positive_support": row.get("target_positive_support"),
        "position": row.get("target_position"),
        "visit_position": row.get("target_visit_position"),
        "source": "rival_identity_observation_plan",
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(plan_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    for row in plan_rows:
        scene_id = str(row.get("scene_id") or "")
        query = str(row.get("query") or "")
        candidate_id = str(row.get("target_candidate_id") or "")
        if not scene_id or not query or not candidate_id:
            continue
        key = (scene_id, query)
        scene_keys[key] = str(row.get("scene_key") or "")
        grouped[key][candidate_id] = candidate_from_plan_row(row)

    artifact_rows: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda candidate: (
                safe_float(candidate.get("score")) or -math.inf,
                -int(candidate.get("semantic_rank") or 9999),
            ),
            reverse=True,
        )
        artifact_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "rival_identity_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return artifact_rows


def make_plan_row(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    request: Dict[str, Any],
    action_row: Dict[str, Any],
    request_index: int,
    target_index: int,
    candidate_id: str,
    candidate_ids: List[str],
    candidate: Dict[str, Any],
    focus_candidate: Optional[Dict[str, Any]],
    viewpoint_position: List[float],
    viewpoint_rotation: List[float],
    viewpoint_source: str,
    viewpoint_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    target_position = candidate_target_position(candidate)
    focus_position = candidate_target_position(focus_candidate or {})
    role = "focus" if candidate_id == str(request.get("focus_candidate_id")) else f"rival_{target_index}"
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "policy": POLICY_NAME,
        "viewpoint_policy": active_planner_name(args),
        "planner_name": active_planner_name(args),
        "viewpoint_mode": str(args.viewpoint_mode),
        "request_index": request_index,
        "target_index": target_index,
        "source_schema_version": action_row.get("schema_version"),
        "source_name": action_row.get("source_name"),
        "role": request.get("role"),
        "episode_key": request.get("episode_key"),
        "scene_key": request.get("scene_key") or action_row.get("scene_key"),
        "scene_id": action_row.get("scene_id"),
        "query": request.get("query"),
        "request_reason": request.get("request_reason"),
        "rival_identity_request_id": f"rival_identity:{request_index}",
        "rival_identity_target_role": role,
        "viewpoint_id": f"rival_identity:{request_index}:{role}:{candidate_id.rsplit(':', 1)[-1]}",
        "candidate_id": candidate_id,
        "candidate_ids": candidate_ids,
        "focus_candidate_id": request.get("focus_candidate_id"),
        "rival_candidate_ids": request.get("rival_candidate_ids"),
        "target_candidate_id": candidate_id,
        "viewpoint_position": viewpoint_position,
        "viewpoint_rotation": viewpoint_rotation,
        "viewpoint_source": viewpoint_source,
        "target_position": target_position,
        "target_visit_position": candidate.get("visit_position"),
        "focus_position": focus_position,
        "pair_span_m": None if focus_position is None or target_position is None else horizontal_distance(focus_position, target_position),
        "target_distance_from_viewpoint_m": None
        if target_position is None
        else horizontal_distance(viewpoint_position, target_position),
        "focus_distance_from_viewpoint_m": None
        if focus_position is None
        else horizontal_distance(viewpoint_position, focus_position),
        "candidate_count": action_row.get("candidate_count"),
        "positive_support_candidate_count": action_row.get("positive_support_candidate_count"),
        "semantic_top_candidate_id": action_row.get("semantic_top_candidate_id"),
        "semantic_top2_score_gap": action_row.get("semantic_top2_score_gap"),
        "source_manifest_split": action_row.get("source_manifest_split"),
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "contract_name": contract.get("contract_name"),
    }
    row.update(copy_candidate_fields(candidate, "target"))
    if focus_candidate is not None:
        row.update(copy_candidate_fields(focus_candidate, "focus"))
    if viewpoint_metadata:
        row.update(viewpoint_metadata)
    return row


def plan_request(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    request: Dict[str, Any],
    request_index: int,
    action_row: Dict[str, Any],
    snapper: Optional[NavmeshSnapper],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selection = contract.get("observation_contract", {}).get("target_selection", {})
    max_targets = int(args.max_target_candidates_per_request or selection.get("max_target_candidates_per_request") or 5)
    max_rivals = int(args.max_rivals_per_request or selection.get("max_rivals_per_request") or 4)
    candidate_ids = target_candidate_ids(request, max_targets=max_targets, max_rivals=max_rivals)
    candidates = evidence_by_candidate_id(action_row)
    focus_id = str(request.get("focus_candidate_id"))
    focus_candidate = candidates.get(focus_id)
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    if focus_candidate is None:
        skipped.append(
            {
                "schema_version": SCHEMA_VERSION,
                "request_index": request_index,
                "episode_key": request.get("episode_key"),
                "candidate_id": focus_id,
                "skip_reason": "missing_focus_candidate",
                "uses_gt_for_action": False,
            }
        )
    for target_index, candidate_id in enumerate(candidate_ids):
        candidate = candidates.get(candidate_id)
        if candidate is None:
            skipped.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "request_index": request_index,
                    "target_index": target_index,
                    "role": request.get("role"),
                    "episode_key": request.get("episode_key"),
                    "scene_key": request.get("scene_key"),
                    "query": request.get("query"),
                    "candidate_id": candidate_id,
                    "focus_candidate_id": focus_id,
                    "skip_reason": "missing_target_candidate",
                    "uses_gt_for_action": False,
                }
            )
            continue
        viewpoint_metadata: Dict[str, Any] = {}
        skip_reason = "no_non_gt_candidate_viewpoint"
        if str(args.viewpoint_mode) == "standoff":
            standoff_viewpoint, standoff_skip_reason, viewpoint_metadata = standoff_viewpoint_from_candidate(
                args=args,
                action_row=action_row,
                candidate_id=candidate_id,
                candidate_ids=candidate_ids,
                candidate=candidate,
                candidates=candidates,
                snapper=snapper,
            )
            viewpoint = None if standoff_viewpoint is None else standoff_viewpoint[:3]
            skip_reason = standoff_skip_reason or skip_reason
        else:
            viewpoint = viewpoint_from_candidate(candidate)
        if viewpoint is None:
            skipped_row = {
                "schema_version": SCHEMA_VERSION,
                "request_index": request_index,
                "target_index": target_index,
                "role": request.get("role"),
                "episode_key": request.get("episode_key"),
                "scene_key": request.get("scene_key"),
                "query": request.get("query"),
                "candidate_id": candidate_id,
                "focus_candidate_id": focus_id,
                "skip_reason": skip_reason,
                "uses_gt_for_action": False,
            }
            skipped_row.update(viewpoint_metadata)
            skipped.append(skipped_row)
            continue
        viewpoint_position, viewpoint_rotation, viewpoint_source = viewpoint
        rows.append(
            make_plan_row(
                args=args,
                contract=contract,
                request=request,
                action_row=action_row,
                request_index=request_index,
                target_index=target_index,
                candidate_id=candidate_id,
                candidate_ids=candidate_ids,
                candidate=candidate,
                focus_candidate=focus_candidate,
                viewpoint_position=viewpoint_position,
                viewpoint_rotation=viewpoint_rotation,
                viewpoint_source=viewpoint_source,
                viewpoint_metadata=viewpoint_metadata,
            )
        )
    return rows, skipped


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract_path = Path(args.contract)
    contract = load_json(contract_path)
    workspace_root = Path(args.workspace_root)
    runs_root = Path(args.runs_root)
    evidence = contract.get("source_evidence", {})
    primary_path = resolve_path(str(evidence.get("primary_action_evidence")), runs_root, workspace_root)
    secondary_path = resolve_path(str(evidence.get("secondary_action_evidence")), runs_root, workspace_root)
    primary_rows = load_jsonl(primary_path)
    secondary_rows = load_jsonl(secondary_path)
    all_action_rows = [*primary_rows, *secondary_rows]
    forbidden = action_forbidden_keys(all_action_rows)

    action_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    action_index.update(action_row_index(primary_rows, "primary", "primary_independent"))
    action_index.update(action_row_index(secondary_rows, "secondary_stress", "secondary_stress"))

    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    missing_action_rows: List[Dict[str, Any]] = []
    request_rows = list(contract.get("request_rows") or [])
    snapper = NavmeshSnapper(args.data_root) if str(args.viewpoint_mode) == "standoff" else None
    try:
        for request_index, request in enumerate(request_rows):
            key = (str(request.get("role")), str(request.get("episode_key")))
            action_row = action_index.get(key)
            if action_row is None:
                missing = {
                    "schema_version": SCHEMA_VERSION,
                    "request_index": request_index,
                    "role": request.get("role"),
                    "episode_key": request.get("episode_key"),
                    "scene_key": request.get("scene_key"),
                    "query": request.get("query"),
                    "skip_reason": "missing_action_evidence_row",
                    "uses_gt_for_action": False,
                }
                missing_action_rows.append(missing)
                skipped_rows.append(missing)
                continue
            rows, skipped = plan_request(
                args=args,
                contract=contract,
                request=request,
                request_index=request_index,
                action_row=action_row,
                snapper=snapper,
            )
            plan_rows.extend(rows)
            skipped_rows.extend(skipped)
    finally:
        if snapper is not None:
            snapper.close()

    out_root = Path(args.out_root)
    write_jsonl(out_root / "rival_identity_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "rival_identity_observation_skipped.jsonl", skipped_rows)
    artifact_rows = candidate_artifact_rows(plan_rows)
    write_jsonl(out_root / "rival_identity_candidate_artifact.jsonl", artifact_rows)

    request_keys_planned = {(row["role"], row["episode_key"]) for row in plan_rows}
    minimum = contract.get("evaluation_contract", {}).get("minimum_plan_gate", {})
    role_counts = Counter(str(row.get("role")) for row in plan_rows)
    viewpoint_source_counts = Counter(str(row.get("viewpoint_source")) for row in plan_rows)
    target_role_counts = Counter(str(row.get("rival_identity_target_role")) for row in plan_rows)
    skipped_reason_counts = Counter(str(row.get("skip_reason")) for row in skipped_rows)
    planned_scenes = {
        str(row.get("scene_key") or row.get("scene_id"))
        for row in plan_rows
        if row.get("scene_key") or row.get("scene_id")
    }
    planned_queries = {str(row.get("query")) for row in plan_rows if row.get("query")}
    target_distances = [
        float(distance)
        for distance in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if distance is not None
    ]
    target_distance_stats = number_stats(target_distances)
    zero_standoff_plan_rows = sum(1 for distance in target_distances if distance < 1e-4)
    near_standoff_plan_rows = sum(1 for distance in target_distances if distance < float(args.min_standoff_distance_m))
    missing_target_distance_plan_rows = len(plan_rows) - len(target_distances)
    rotation_fallback_plan_rows = sum(1 for row in plan_rows if "rotation_fallback" in str(row.get("viewpoint_source") or ""))
    candidate_fallback_plan_rows = sum(1 for row in plan_rows if "fallback" in str(row.get("viewpoint_source") or ""))
    valid_standoff_rows = sum(
        1
        for row in plan_rows
        if str(row.get("viewpoint_source")) in {"standoff_navmesh", "standoff_geometry"}
        and row.get("standoff_projection_sane") is True
        and (
            not bool(args.require_navmesh_standoff)
            or (str(row.get("viewpoint_source")) == "standoff_navmesh" and row.get("standoff_navmesh_navigable") is True)
        )
        and (safe_float(row.get("target_distance_from_viewpoint_m")) or -1.0) >= float(args.min_standoff_distance_m)
        and (safe_float(row.get("target_distance_from_viewpoint_m")) or math.inf) <= float(args.max_standoff_distance_m)
    )
    valid_standoff_rate = ratio(valid_standoff_rows, len(plan_rows))
    geometry_gate = {
        "enabled": str(args.viewpoint_mode) == "standoff",
        "planned_request_rows_minimum": int(args.min_planned_request_rows),
        "planned_request_rows_minimum_passed": len(request_keys_planned) >= int(args.min_planned_request_rows),
        "planned_scene_count_minimum": int(args.min_planned_scene_count),
        "planned_scene_count_minimum_passed": len(planned_scenes) >= int(args.min_planned_scene_count),
        "planned_query_count_minimum": int(args.min_planned_query_count),
        "planned_query_count_minimum_passed": len(planned_queries) >= int(args.min_planned_query_count),
        "zero_standoff_plan_rows_passed": zero_standoff_plan_rows == 0,
        "near_standoff_plan_rows_passed": near_standoff_plan_rows == 0 and missing_target_distance_plan_rows == 0,
        "rotation_fallback_plan_rows_passed": rotation_fallback_plan_rows == 0 and candidate_fallback_plan_rows == 0,
        "target_distance_minimum_passed": target_distance_stats["min"] is not None
        and target_distance_stats["min"] >= float(args.min_standoff_distance_m),
        "target_distance_maximum_passed": target_distance_stats["max"] is not None
        and target_distance_stats["max"] <= float(args.max_standoff_distance_m),
        "navmesh_snapped_or_geometry_valid_row_rate_minimum": float(args.min_navmesh_snapped_or_geometry_valid_row_rate),
        "navmesh_snapped_or_geometry_valid_row_rate_passed": (valid_standoff_rate or 0.0)
        >= float(args.min_navmesh_snapped_or_geometry_valid_row_rate),
    }
    geometry_checks = [
        value
        for key, value in geometry_gate.items()
        if key.endswith("_passed")
    ]
    geometry_gate["passed"] = (not geometry_gate["enabled"]) or all(bool(value) for value in geometry_checks)
    plan_gate = {
        "request_rows_match": len(request_rows) == int(minimum.get("request_rows") or len(request_rows)),
        "primary_request_rows_match": sum(1 for row in request_rows if row.get("role") == "primary")
        == int(minimum.get("primary_request_rows") or 0),
        "secondary_stress_request_rows_match": sum(1 for row in request_rows if row.get("role") == "secondary_stress")
        == int(minimum.get("secondary_stress_request_rows") or 0),
        "planned_rows_minimum_passed": len(plan_rows) >= int(minimum.get("planned_rows_minimum") or 1),
        "all_request_rows_have_plan": len(request_keys_planned) == len(request_rows),
        "no_missing_action_rows": len(missing_action_rows) == 0,
        "no_forbidden_action_keys": len(forbidden) == int(minimum.get("action_evidence_forbidden_key_count") or 0),
        "standoff_geometry_gate_passed": bool(geometry_gate["passed"]),
    }
    if str(args.viewpoint_mode) == "standoff":
        plan_gate["smoke_passed"] = (
            bool(plan_gate["request_rows_match"])
            and bool(plan_gate["primary_request_rows_match"])
            and bool(plan_gate["secondary_stress_request_rows_match"])
            and bool(plan_gate["planned_rows_minimum_passed"])
            and bool(plan_gate["no_missing_action_rows"])
            and bool(plan_gate["no_forbidden_action_keys"])
            and bool(geometry_gate["passed"])
        )
    else:
        plan_gate["smoke_passed"] = all(bool(value) for value in plan_gate.values())
    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": str(contract_path),
        "contract_name": contract.get("contract_name"),
        "primary_action_evidence": str(primary_path),
        "secondary_action_evidence": str(secondary_path),
        "out_root": str(out_root),
        "run_id": str(args.run_id),
        "policy": POLICY_NAME,
        "planner_name": active_planner_name(args),
        "viewpoint_mode": str(args.viewpoint_mode),
        "request_rows": len(request_rows),
        "primary_request_rows": sum(1 for row in request_rows if row.get("role") == "primary"),
        "secondary_stress_request_rows": sum(1 for row in request_rows if row.get("role") == "secondary_stress"),
        "planned_request_rows": len(request_keys_planned),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_candidates": sum(int(row.get("candidate_count") or 0) for row in artifact_rows),
        "missing_action_rows": len(missing_action_rows),
        "role_counts": dict(sorted(role_counts.items())),
        "target_role_counts": dict(sorted(target_role_counts.items())),
        "viewpoint_source_counts": dict(sorted(viewpoint_source_counts.items())),
        "skipped_reason_counts": dict(sorted(skipped_reason_counts.items())),
        "planned_scene_count": len(planned_scenes),
        "planned_query_count": len(planned_queries),
        "mean_plan_rows_per_request": ratio(len(plan_rows), len(request_rows)),
        "target_distance_from_viewpoint_min_m": target_distance_stats["min"],
        "target_distance_from_viewpoint_mean_m": target_distance_stats["mean"],
        "target_distance_from_viewpoint_max_m": target_distance_stats["max"],
        "zero_standoff_plan_rows": zero_standoff_plan_rows,
        "near_standoff_plan_rows": near_standoff_plan_rows,
        "missing_target_distance_plan_rows": missing_target_distance_plan_rows,
        "rotation_fallback_plan_rows": rotation_fallback_plan_rows,
        "candidate_fallback_plan_rows": candidate_fallback_plan_rows,
        "navmesh_snapped_or_geometry_valid_rows": valid_standoff_rows,
        "navmesh_snapped_or_geometry_valid_row_rate": valid_standoff_rate,
        "standoff_distances": [float(value) for value in args.standoff_distances],
        "preferred_standoff_distance_m": float(args.preferred_standoff_distance_m),
        "min_standoff_distance_m": float(args.min_standoff_distance_m),
        "max_standoff_distance_m": float(args.max_standoff_distance_m),
        "require_navmesh_standoff": bool(args.require_navmesh_standoff),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "max_target_candidates_per_request": int(args.max_target_candidates_per_request or 0)
        or int(contract.get("observation_contract", {}).get("target_selection", {}).get("max_target_candidates_per_request") or 5),
        "max_rivals_per_request": int(args.max_rivals_per_request or 0)
        or int(contract.get("observation_contract", {}).get("target_selection", {}).get("max_rivals_per_request") or 4),
        "geometry_gate": geometry_gate,
        "plan_gate": plan_gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "paper_claim_status": "plan_smoke_only_requires_frame_detector_association_and_fresh_or_predeclared_validation",
        "output_files": {
            "plan_rows": "rival_identity_observation_plan.jsonl",
            "skipped_rows": "rival_identity_observation_skipped.jsonl",
            "candidate_artifact": "rival_identity_candidate_artifact.jsonl",
            "summary": "rival_identity_observation_plan_summary.json",
        },
        "next_expected_files": [
            "rival_identity_frame_summary.jsonl",
            "rival_identity_detector_associations.jsonl",
            "rival_identity_post_observation_evidence.jsonl",
            "rival_identity_observation_validation_summary.json",
        ],
    }
    write_json(out_root / "rival_identity_observation_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan H001 rival-identity active re-observation rows.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--runs-root", default="/runs")
    parser.add_argument("--workspace-root", default="/workspace")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--run-id", default="h001_rival_identity_pair_probe_v1")
    parser.add_argument("--max-target-candidates-per-request", type=int, default=0)
    parser.add_argument("--max-rivals-per-request", type=int, default=0)
    parser.add_argument("--viewpoint-mode", choices=["candidate", "standoff"], default="candidate")
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--min-planned-request-rows", type=int, default=0)
    parser.add_argument("--min-planned-scene-count", type=int, default=0)
    parser.add_argument("--min-planned-query-count", type=int, default=0)
    parser.add_argument("--min-navmesh-snapped-or-geometry-valid-row-rate", type=float, default=0.8)
    parser.add_argument("--require-navmesh-standoff", action="store_true")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
