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


SCHEMA_VERSION = "h001.instance_arbitration_evidence_plan.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_instance_arbitration_evidence_v1.json"
)
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_evidence_v1"
OUT_ROOT_DEFAULT = INPUT_ROOT_DEFAULT
POLICY_NAME = "InstanceArbitrationPairEvidence"
PLANNER_NAME = "instance_arbitration_pair_evidence_v1"
VIEWPOINT_POLICY = "candidate_pair_standoff_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        text = str(value).rsplit(":", 1)[-1]
        try:
            return int(text)
        except (TypeError, ValueError):
            return default


def request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    return text.rsplit(":", 1)[0], safe_int(text.rsplit(":", 1)[-1], 999999), text


def request_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    if ":" in text:
        prefix, suffix = text.rsplit(":", 1)
        return prefix, safe_int(suffix, 999999), text
    return text, 999999, text


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def parse_float_list(text: str) -> List[float]:
    values = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated float")
    return values


def scan_forbidden_keys(value: Any, prefix: str = "") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if lowered != "uses_gt_for_action" and any(
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


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_id(row)].append(dict(row))
    return grouped


def source_row_for_request(request_row: Mapping[str, Any], candidate_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    source_top = next((row for row in candidate_rows if row.get("source_top_candidate") is True), None)
    exemplar = source_top or (candidate_rows[0] if candidate_rows else request_row)
    return {
        "scene_id": request_row.get("scene_id") or exemplar.get("scene_id"),
        "scene_key": request_row.get("scene_key") or exemplar.get("scene_key"),
        "query": request_row.get("query") or exemplar.get("query"),
        "episode_key": request_row.get("episode_key") or exemplar.get("episode_key"),
        "viewpoint_position": exemplar.get("visit_position") or exemplar.get("position"),
        "uses_gt_for_action": False,
    }


def common_pair_viewpoint(
    *,
    source: Mapping[str, Any],
    a: Mapping[str, Any],
    b: Mapping[str, Any],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    a_position = candidate_target_position(dict(a))
    b_position = candidate_target_position(dict(b))
    if a_position is None or b_position is None:
        return None
    unit = normalize_xz(b_position[0] - a_position[0], b_position[2] - a_position[2])
    if unit is None:
        return None
    ux, uz = unit
    perpendiculars = [(-uz, ux, "pair_perpendicular_left"), (uz, -ux, "pair_perpendicular_right")]
    a_visit = vector(a.get("visit_position"))
    midpoint = [
        (float(a_position[0]) + float(b_position[0])) / 2.0,
        float(a_visit[1]) if a_visit is not None else float(a_position[1]),
        (float(a_position[2]) + float(b_position[2])) / 2.0,
    ]
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in args.common_pair_distances:
        for dx, dz, direction_source in perpendiculars:
            desired = [
                float(midpoint[0]) + dx * float(distance),
                float(midpoint[1]),
                float(midpoint[2]) + dz * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(str(source.get("scene_id")), desired)
            if snap_distance is None or not navigable:
                continue
            a_distance = horizontal_distance(snapped, a_position)
            b_distance = horizontal_distance(snapped, b_position)
            if a_distance < float(args.min_standoff_distance_m) or b_distance < float(args.min_standoff_distance_m):
                continue
            if a_distance > float(args.max_standoff_distance_m) or b_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, midpoint)
            if yaw is None:
                continue
            score = abs(a_distance - b_distance) + 0.20 * (snap_distance or 0.0) - (0.25 if navigable else 0.0)
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
                "navmesh_snapped": True,
                "navmesh_navigable": navigable,
                "direction_source": direction_source,
                "standoff_distance_requested": float(distance),
                "viewpoint_source": "common_pair_navmesh",
                "projection_sane": True,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, item)
    return None if best is None else best[1]


def standoff_for_candidate(
    *,
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    candidates: Mapping[str, Dict[str, Any]],
    alt_id: Optional[str],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    if candidate_target_position(dict(target)) is None or candidate_floor_y(dict(target), dict(source)) is None:
        return None
    viewpoint = plan_standoff_viewpoint(dict(source), dict(target), dict(candidates), alt_id, snapper, args)
    if viewpoint is None:
        return None
    distance = safe_float(viewpoint.get("target_horizontal_distance"))
    if distance is None:
        return None
    if distance < float(args.min_standoff_distance_m) or distance > float(args.max_standoff_distance_m):
        return None
    return viewpoint


def candidate_observation_row(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    request: Mapping[str, Any],
    candidate: Mapping[str, Any],
    source: Mapping[str, Any],
    viewpoint: Mapping[str, Any],
    observation_index: int,
) -> Dict[str, Any]:
    cid = str(candidate.get("candidate_id"))
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "action_instance_arbitration_observation_target",
        "contract_name": contract.get("contract_name"),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "observation_index": observation_index,
        "request_index": request.get("request_index"),
        "candidate_index": candidate.get("candidate_index"),
        "episode_key": request.get("episode_key"),
        "scene_id": request.get("scene_id"),
        "scene_key": request.get("scene_key"),
        "query": request.get("query"),
        "expanded_retrieval_request_id": request_id(request),
        "rival_identity_request_id": request.get("rival_identity_request_id") or request_id(request),
        "view_role": "candidate_own_view_refresh",
        "pair_probe_type": None,
        "candidate_id": cid,
        "target_candidate_id": cid,
        "candidate_ids": [cid],
        "candidate_action_roles": list(candidate.get("candidate_action_roles") or []),
        "target_position": viewpoint.get("target_position") or candidate.get("position"),
        "target_visit_position": candidate.get("visit_position"),
        "viewpoint_id": f"instance_arbitration:{request_id(request)}:candidate:{cid.rsplit(':', 1)[-1]}",
        "viewpoint_position": viewpoint.get("position"),
        "viewpoint_rotation": viewpoint.get("rotation"),
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_distance_from_viewpoint_m": viewpoint.get("target_horizontal_distance"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": list(args.projection_anchor_height_offsets_m),
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "terminal_commit_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def pair_observation_row(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    request: Mapping[str, Any],
    pair: Mapping[str, Any],
    target: Mapping[str, Any],
    viewpoint: Mapping[str, Any],
    observation_index: int,
    pair_probe_type: str,
    pair_fallback_reason: Optional[str],
) -> Dict[str, Any]:
    candidate_ids = [str(value) for value in pair.get("candidate_ids") or []]
    target_id = str(target.get("candidate_id"))
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "action_instance_arbitration_observation_target",
        "contract_name": contract.get("contract_name"),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "observation_index": observation_index,
        "request_index": request.get("request_index"),
        "pair_index": pair.get("pair_index"),
        "request_pair_index": pair.get("request_pair_index"),
        "episode_key": request.get("episode_key"),
        "scene_id": request.get("scene_id"),
        "scene_key": request.get("scene_key"),
        "query": request.get("query"),
        "expanded_retrieval_request_id": request_id(request),
        "rival_identity_request_id": request.get("rival_identity_request_id") or request_id(request),
        "view_role": pair.get("view_role") or "pair_common_view_or_dual_standoff",
        "pair_probe_type": pair_probe_type,
        "pair_fallback_reason": pair_fallback_reason,
        "candidate_id": target_id,
        "target_candidate_id": target_id,
        "candidate_ids": candidate_ids,
        "candidate_id_a": pair.get("candidate_id_a"),
        "candidate_id_b": pair.get("candidate_id_b"),
        "pair_distance_m": pair.get("pair_distance_m"),
        "candidate_a_roles": list(pair.get("candidate_a_roles") or []),
        "candidate_b_roles": list(pair.get("candidate_b_roles") or []),
        "target_position": viewpoint.get("target_position") or target.get("position"),
        "target_visit_position": target.get("visit_position"),
        "pair_midpoint": viewpoint.get("pair_midpoint"),
        "viewpoint_id": f"instance_arbitration:{request_id(request)}:pair:{pair.get('request_pair_index')}:{pair_probe_type}",
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
        "revision_projection_anchor_height_offsets_m": list(args.projection_anchor_height_offsets_m),
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "terminal_commit_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_skip_row(
    *,
    request: Mapping[str, Any],
    row_type: str,
    reason: str,
    candidate_id: Optional[str] = None,
    pair: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_instance_arbitration_observation_skipped",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "row_type": row_type,
        "skip_reason": reason,
        "episode_key": request.get("episode_key"),
        "scene_id": request.get("scene_id"),
        "scene_key": request.get("scene_key"),
        "query": request.get("query"),
        "expanded_retrieval_request_id": request_id(request),
        "rival_identity_request_id": request.get("rival_identity_request_id") or request_id(request),
        "candidate_id": candidate_id,
        "pair_index": None if pair is None else pair.get("pair_index"),
        "candidate_ids": [] if pair is None else list(pair.get("candidate_ids") or []),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def choose_pair_fallback_target(pair: Mapping[str, Any], candidates: Mapping[str, Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    candidate_ids = [str(value) for value in pair.get("candidate_ids") or []]
    rows = [candidates[cid] for cid in candidate_ids if cid in candidates]
    if not rows:
        return None
    rows.sort(
        key=lambda row: (
            0 if row.get("source_top_candidate") is True else 1,
            0 if row.get("local_context_candidate") is True else 1,
            safe_int(row.get("semantic_rank"), 999999),
            candidate_sort_key(row.get("candidate_id")),
        )
    )
    return rows[0]


def plan_request(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    request: Mapping[str, Any],
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    snapper: NavmeshSnapper,
    observation_start: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source = source_row_for_request(request, candidate_rows)
    candidates = {str(row.get("candidate_id")): dict(row) for row in candidate_rows}
    observation_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    observation_index = observation_start

    for candidate in sorted(candidate_rows, key=lambda row: candidate_sort_key(row.get("candidate_id"))):
        cid = str(candidate.get("candidate_id"))
        alt_ids = [value for value in candidates.keys() if value != cid]
        viewpoint = standoff_for_candidate(
            source=source,
            target=candidate,
            candidates=candidates,
            alt_id=alt_ids[0] if alt_ids else None,
            snapper=snapper,
            args=args,
        )
        if viewpoint is None:
            skipped_rows.append(make_skip_row(request=request, row_type="candidate", reason="missing_candidate_standoff", candidate_id=cid))
            continue
        observation_rows.append(
            candidate_observation_row(
                args=args,
                contract=contract,
                request=request,
                candidate=candidate,
                source=source,
                viewpoint=viewpoint,
                observation_index=observation_index,
            )
        )
        observation_index += 1

    for pair in sorted(pair_rows, key=lambda row: safe_int(row.get("request_pair_index"), 999999)):
        candidate_ids = [str(value) for value in pair.get("candidate_ids") or []]
        if len(candidate_ids) != 2 or any(cid not in candidates for cid in candidate_ids):
            skipped_rows.append(make_skip_row(request=request, row_type="pair", reason="missing_pair_candidate", pair=pair))
            continue
        a = candidates[candidate_ids[0]]
        b = candidates[candidate_ids[1]]
        viewpoint = common_pair_viewpoint(source=source, a=a, b=b, snapper=snapper, args=args)
        pair_probe_type = "pair_common_view"
        fallback_reason = None
        target = a
        if viewpoint is None:
            target = choose_pair_fallback_target(pair, candidates)
            if target is None:
                skipped_rows.append(make_skip_row(request=request, row_type="pair", reason="missing_pair_fallback_target", pair=pair))
                continue
            alt_id = candidate_ids[1] if str(target.get("candidate_id")) == candidate_ids[0] else candidate_ids[0]
            viewpoint = standoff_for_candidate(
                source=source,
                target=target,
                candidates=candidates,
                alt_id=alt_id,
                snapper=snapper,
                args=args,
            )
            pair_probe_type = "pair_dual_standoff_fallback"
            fallback_reason = "pair_common_view_unavailable"
        if viewpoint is None:
            skipped_rows.append(make_skip_row(request=request, row_type="pair", reason="missing_pair_standoff", pair=pair))
            continue
        observation_rows.append(
            pair_observation_row(
                args=args,
                contract=contract,
                request=request,
                pair=pair,
                target=target,
                viewpoint=viewpoint,
                observation_index=observation_index,
                pair_probe_type=pair_probe_type,
                pair_fallback_reason=fallback_reason,
            )
        )
        observation_index += 1
    return observation_rows, skipped_rows


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    input_summary: Mapping[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    observation_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    all_action_rows: List[Mapping[str, Any]] = [*observation_rows, *skipped_rows]
    forbidden = forbidden_findings(all_action_rows)
    planner_contract = contract.get("planner_contract") or {}
    gates = contract.get("evaluation_gates") or {}
    target_distances = [
        float(value)
        for value in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in observation_rows)
        if value is not None
    ]
    candidate_observation_rows = [row for row in observation_rows if row.get("view_role") == "candidate_own_view_refresh"]
    pair_observation_rows = [row for row in observation_rows if row.get("pair_probe_type")]
    skipped_request_ids = {request_id(row) for row in skipped_rows}
    terminal_rows = [
        row
        for row in all_action_rows
        if row.get("terminal_commit_allowed") is True
        or row.get("candidate_commit_allowed") is True
        or row.get("candidate_rejection_allowed") is True
    ]
    gate = {
        "input_gate_passed": bool((input_summary.get("gate") or {}).get("instance_arbitration_input_gate_passed")),
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_rows_passed": len(candidate_rows) == safe_int(gates.get("expected_candidate_rows")),
        "expected_pair_rows_passed": len(pair_rows) == safe_int(gates.get("expected_pair_rows")),
        "minimum_candidate_observation_rows_passed": len(candidate_observation_rows) >= safe_int(planner_contract.get("minimum_candidate_observation_rows")),
        "minimum_pair_observation_rows_passed": len(pair_observation_rows) >= safe_int(planner_contract.get("minimum_pair_observation_rows")),
        "minimum_observation_rows_passed": len(observation_rows) >= safe_int(planner_contract.get("minimum_observation_rows")),
        "skipped_request_rows_passed": len(skipped_request_ids) <= safe_int(planner_contract.get("maximum_skipped_request_rows")),
        "skipped_candidate_rows_passed": sum(1 for row in skipped_rows if row.get("row_type") == "candidate") <= safe_int(planner_contract.get("maximum_skipped_candidate_rows")),
        "unreported_pair_rows_passed": sum(1 for row in skipped_rows if row.get("row_type") == "pair") <= safe_int(planner_contract.get("maximum_unreported_pair_rows")),
        "action_evidence_forbidden_key_gate_passed": len(forbidden) <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "candidate_commit_rows_passed": 0 <= safe_int(gates.get("candidate_commit_rows_maximum")),
        "candidate_rejection_rows_passed": 0 <= safe_int(gates.get("candidate_rejection_rows_maximum")),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in all_action_rows),
        "paper_claim_allowed": False,
    }
    gate["instance_arbitration_observation_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_root": str(args.input_root),
        "run_id": str(args.run_id),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_rows": len(request_rows),
        "candidate_rows": len(candidate_rows),
        "pair_rows": len(pair_rows),
        "observation_plan_rows": len(observation_rows),
        "candidate_observation_rows": len(candidate_observation_rows),
        "pair_observation_rows": len(pair_observation_rows),
        "skipped_rows": len(skipped_rows),
        "skipped_reason_counts": compact_counter(row.get("skip_reason") for row in skipped_rows),
        "view_role_counts": compact_counter(row.get("view_role") for row in observation_rows),
        "pair_probe_type_counts": compact_counter(row.get("pair_probe_type") for row in pair_observation_rows),
        "viewpoint_source_counts": compact_counter(row.get("viewpoint_source") for row in observation_rows),
        "request_observation_counts": dict(sorted(Counter(request_id(row) for row in observation_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "common_pair_distances": [float(value) for value in args.common_pair_distances],
        "standoff_distances": [float(value) for value in args.standoff_distances],
        "projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": 0,
        "candidate_rejection_rows": 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "observation_plan": "instance_arbitration_observation_plan.jsonl",
            "skipped_rows": "instance_arbitration_skipped_rows.jsonl",
            "summary": "instance_arbitration_evidence_summary.json",
        },
        "interpretation": {
            "fact": "The planner writes nonterminal candidate and pair observation targets from frozen label-free instance-arbitration inputs.",
            "agent_inference": "Passing this gate means the branch has a reproducible observation plan; it does not establish terminal ObjectNav utility.",
            "paper_claim": "No paper claim is allowed from this planner output alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    input_root = Path(args.input_root)
    out_root = Path(args.out_root)
    request_rows = load_jsonl(input_root / "instance_arbitration_request_rows.jsonl")
    candidate_rows = load_jsonl(input_root / "instance_arbitration_candidate_rows.jsonl")
    pair_rows = load_jsonl(input_root / "instance_arbitration_pair_rows.jsonl")
    input_summary = load_json(input_root / "instance_arbitration_input_summary.json")

    candidates_by_request = group_by_request(candidate_rows)
    pairs_by_request = group_by_request(pair_rows)
    snapper = NavmeshSnapper(args.data_root)
    observation_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    try:
        for request in sorted(request_rows, key=lambda row: request_sort_key(request_id(row))):
            rid = request_id(request)
            rows, skipped = plan_request(
                args=args,
                contract=contract,
                request=request,
                candidate_rows=candidates_by_request.get(rid, []),
                pair_rows=pairs_by_request.get(rid, []),
                snapper=snapper,
                observation_start=len(observation_rows),
            )
            observation_rows.extend(rows)
            skipped_rows.extend(skipped)
    finally:
        snapper.close()

    summary = build_summary(
        args=args,
        contract=contract,
        input_summary=input_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        observation_rows=observation_rows,
        skipped_rows=skipped_rows,
    )
    write_jsonl(out_root / "instance_arbitration_observation_plan.jsonl", observation_rows)
    write_jsonl(out_root / "instance_arbitration_skipped_rows.jsonl", skipped_rows)
    write_json(out_root / "instance_arbitration_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan label-free instance-arbitration evidence observations.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--run-id", default="h001_instance_arbitration_evidence_v1")
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
    if not summary["gate"]["instance_arbitration_observation_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
