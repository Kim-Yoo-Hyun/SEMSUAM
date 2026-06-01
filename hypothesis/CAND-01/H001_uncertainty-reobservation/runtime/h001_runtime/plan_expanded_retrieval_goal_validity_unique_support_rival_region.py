import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_rival_region_plan.v1"
CONTRACT_NAME = "expanded_retrieval_goal_validity_unique_support_rival_region_v1"
POLICY_NAME = "ExpandedRetrievalGoalValidityUniqueSupportRivalRegion"
PLANNER_NAME = "unique_support_rival_region_v1"
VIEWPOINT_POLICY = "swapped_candidate_view_matrix_v1"
SOURCE_PLANNER_NAME = "unique_support_goal_region_v1"

CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1.json"
)
SOURCE_PLAN_ROOT_DEFAULT = (
    "local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1"
)
SOURCE_INSPECTION_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_goal_region_inspection_v1"
)
SOURCE_FRAME_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1"
)

SECOND_PASS_ROLE_MAP = [
    {
        "second_pass_view_role": "rival_from_common_pair_view",
        "source_view_role": "common_pair_view",
        "target_role": "rival",
        "reason": "score_rival_from_shared_pair_view",
    },
    {
        "second_pass_view_role": "rival_from_focus_own_view",
        "source_view_role": "focus_own_view",
        "target_role": "rival",
        "reason": "score_rival_from_focus_region",
    },
    {
        "second_pass_view_role": "focus_from_rival_own_view",
        "source_view_role": "rival_own_view",
        "target_role": "focus",
        "reason": "score_focus_from_rival_region",
    },
]


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def request_sort_key(value: str) -> Tuple[int, str]:
    suffix = str(value).split(":")[-1]
    return (int(suffix), str(value)) if suffix.isdigit() else (999999, str(value))


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) != 3:
        return None
    values = [safe_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return [float(item) for item in values]


def horizontal_distance(a: Any, b: Any) -> Optional[float]:
    left = vector3(a)
    right = vector3(b)
    if left is None or right is None:
        return None
    return math.hypot(float(left[0]) - float(right[0]), float(left[2]) - float(right[2]))


def unique_preserve_order(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        item = str(value)
        if not item or item in seen:
            continue
        output.append(item)
        seen.add(item)
    return output


def source_view_role(row: Dict[str, Any]) -> str:
    explicit = str(row.get("view_role") or "")
    if explicit in {"focus_own_view", "rival_own_view", "common_pair_view"}:
        return explicit
    if str(row.get("viewpoint_source")) == "common_pair_navmesh":
        return "common_pair_view"
    target = str(row.get("target_candidate_id") or row.get("candidate_id") or "")
    if target and target == str(row.get("focus_candidate_id")):
        return "focus_own_view"
    if target and target == str(row.get("rival_candidate_id")):
        return "rival_own_view"
    return "unknown_source_view"


def pair_key(row: Dict[str, Any]) -> Tuple[str, int, str]:
    return (request_id(row), safe_int(row.get("pair_index")), str(row.get("pair_id") or ""))


def index_rows_by_pair(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        pair_id = str(row.get("pair_id") or "")
        if pair_id:
            indexed[pair_id] = dict(row)
    return indexed


def index_observations_by_pair_role(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        pair_id = str(row.get("pair_id") or "")
        role = source_view_role(row)
        if pair_id and role:
            indexed[(pair_id, role)] = dict(row)
    return indexed


def index_frames_by_pair_role(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        pair_id = str(row.get("pair_id") or "")
        role = source_view_role(row)
        if pair_id and role:
            indexed[(pair_id, role)] = dict(row)
    return indexed


def index_candidates(candidate_rows: Sequence[Dict[str, Any]], artifact_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in candidate_rows:
        rid = request_id(row)
        candidate_id = str(row.get("candidate_id") or row.get("target_candidate_id") or "")
        if rid and candidate_id:
            indexed[(rid, candidate_id)] = dict(row)
    for artifact in artifact_rows:
        rid = request_id(artifact)
        for candidate in artifact.get("candidates") or []:
            candidate_id = str(candidate.get("candidate_id") or "")
            if rid and candidate_id and (rid, candidate_id) not in indexed:
                row = dict(candidate)
                row.update(
                    {
                        "expanded_retrieval_request_id": rid,
                        "rival_identity_request_id": artifact.get("rival_identity_request_id") or rid,
                        "episode_key": artifact.get("episode_key"),
                        "scene_id": artifact.get("scene_id"),
                        "scene_key": artifact.get("scene_key"),
                        "query": artifact.get("query"),
                    }
                )
                indexed[(rid, candidate_id)] = row
    return indexed


def role_rank(role: str) -> int:
    order = {
        "focus_unique_support": 0,
        "ambiguous_rival_region": 1,
        "contrastive_rival": 2,
    }
    return order.get(role, 99)


def candidate_position(candidate: Dict[str, Any]) -> Optional[List[float]]:
    return vector3(candidate.get("position")) or vector3(candidate.get("visit_position"))


def candidate_payload(candidate: Dict[str, Any], role: str) -> Dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id") or candidate.get("target_candidate_id"))
    return {
        "candidate_id": candidate_id,
        "category": candidate.get("category") or candidate.get("query"),
        "score": candidate.get("score"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_backend": "unique_support_rival_region",
        "candidate_role": role,
        "source_goal_region_candidate_role": candidate.get("goal_region_candidate_role") or candidate.get("candidate_role"),
        "generated_rank": candidate.get("generated_rank"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "detector_visible_rows": candidate.get("detector_visible_rows"),
        "detector_inside_mask_rows": candidate.get("detector_inside_mask_rows"),
        "detector_depth_mismatch_rows": candidate.get("detector_depth_mismatch_rows"),
        "source": "expanded_retrieval_goal_validity_unique_support_rival_region_plan",
        "uses_gt_for_action": False,
    }


def make_request_row(
    request: Dict[str, Any],
    pairs: Sequence[Dict[str, Any]],
    request_index: int,
) -> Dict[str, Any]:
    rival_ids = unique_preserve_order(row.get("rival_candidate_id") for row in pairs)
    focus_ids = unique_preserve_order(row.get("focus_candidate_id") for row in pairs)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_rival_region_request",
        "contract_name": CONTRACT_NAME,
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "episode_key": request.get("episode_key") or (pairs[0].get("episode_key") if pairs else None),
        "scene_id": request.get("scene_id") or (pairs[0].get("scene_id") if pairs else None),
        "scene_key": request.get("scene_key") or (pairs[0].get("scene_key") if pairs else None),
        "query": request.get("query") or (pairs[0].get("query") if pairs else None),
        "expanded_retrieval_request_id": request_id(request) or (request_id(pairs[0]) if pairs else None),
        "rival_identity_request_id": request.get("rival_identity_request_id") or (request_id(pairs[0]) if pairs else None),
        "focus_candidate_ids": focus_ids,
        "focus_candidate_id": focus_ids[0] if focus_ids else None,
        "ambiguous_rival_candidate_ids": rival_ids,
        "ambiguous_pair_ids": [row.get("pair_id") for row in pairs],
        "ambiguous_pair_count": len(pairs),
        "second_pass_observation_rows_expected": len(pairs) * len(SECOND_PASS_ROLE_MAP),
        "second_pass_view_roles": [item["second_pass_view_role"] for item in SECOND_PASS_ROLE_MAP],
        "rival_region_observation_action": "collect_second_pass_rival_region_evidence",
        "request_reason": "rival_own_view_supported_pairs_block_terminal_goal_region_arbitration",
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_candidate_row(
    *,
    request: Dict[str, Any],
    candidate: Dict[str, Any],
    role: str,
    request_index: int,
    candidate_index: int,
) -> Dict[str, Any]:
    payload = candidate_payload(candidate, role)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_rival_region_request_candidate",
        "contract_name": CONTRACT_NAME,
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "candidate_index": candidate_index,
        "episode_key": request.get("episode_key"),
        "scene_id": request.get("scene_id"),
        "scene_key": request.get("scene_key"),
        "query": request.get("query"),
        "expanded_retrieval_request_id": request_id(request),
        "rival_identity_request_id": request.get("rival_identity_request_id") or request_id(request),
        "target_candidate_id": payload["candidate_id"],
        "rival_region_candidate_role": role,
        **payload,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_pair_row(
    *,
    pair: Dict[str, Any],
    source_pair: Optional[Dict[str, Any]],
    source_views: Dict[str, Optional[Dict[str, Any]]],
    request_index: int,
) -> Dict[str, Any]:
    focus_position = pair.get("focus_position") or (source_pair or {}).get("focus_position")
    rival_position = pair.get("rival_position") or (source_pair or {}).get("rival_position")
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_rival_region_pair",
        "contract_name": CONTRACT_NAME,
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "pair_index": pair.get("pair_index"),
        "pair_id": pair.get("pair_id"),
        "episode_key": pair.get("episode_key"),
        "scene_id": pair.get("scene_id"),
        "scene_key": pair.get("scene_key"),
        "query": pair.get("query"),
        "expanded_retrieval_request_id": request_id(pair),
        "rival_identity_request_id": pair.get("rival_identity_request_id") or request_id(pair),
        "focus_candidate_id": pair.get("focus_candidate_id"),
        "rival_candidate_id": pair.get("rival_candidate_id"),
        "candidate_ids": [str(pair.get("focus_candidate_id")), str(pair.get("rival_candidate_id"))],
        "focus_position": focus_position,
        "rival_position": rival_position,
        "focus_rival_span_m": pair.get("focus_rival_span_m")
        if pair.get("focus_rival_span_m") is not None
        else horizontal_distance(focus_position, rival_position),
        "first_pass_goal_region_evidence_status": pair.get("goal_region_evidence_status"),
        "first_pass_inspection_blocker": pair.get("inspection_blocker"),
        "first_pass_focus_own_support": pair.get("focus_own_support"),
        "first_pass_rival_own_support": pair.get("rival_own_support"),
        "first_pass_common_focus_support": pair.get("common_focus_support"),
        "first_pass_focus_own_associated_heading_count": pair.get("focus_own_associated_heading_count"),
        "first_pass_rival_own_associated_heading_count": pair.get("rival_own_associated_heading_count"),
        "first_pass_common_focus_associated_heading_count": pair.get("common_focus_associated_heading_count"),
        "source_view_roles_available": sorted(role for role, row in source_views.items() if row is not None),
        "source_decision_ids": {
            role: None if row is None else row.get("decision_id") for role, row in sorted(source_views.items())
        },
        "rival_region_pair_action": "collect_second_pass_rival_region_evidence",
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def copy_view_geometry(source: Dict[str, Any]) -> Dict[str, Any]:
    keys = [
        "viewpoint_position",
        "viewpoint_rotation",
        "viewpoint_source",
        "viewpoint_policy",
        "pair_midpoint",
        "standoff_desired_position",
        "standoff_target_position",
        "standoff_target_horizontal_distance",
        "standoff_snap_distance",
        "standoff_navmesh_snapped",
        "standoff_navmesh_navigable",
        "standoff_direction_source",
        "standoff_distance_requested",
        "standoff_projection_sane",
        "standoff_viewpoint_yaw_rad",
        "standoff_score",
        "revision_projection_anchor_policy",
        "revision_projection_anchor_height_offsets_m",
        "revision_projection_anchor_source",
        "revision_projection_anchor_label_free",
    ]
    return {key: source.get(key) for key in keys if key in source}


def make_observation_row(
    *,
    args: argparse.Namespace,
    pair: Dict[str, Any],
    source_pair: Optional[Dict[str, Any]],
    source_observation: Dict[str, Any],
    source_frame: Optional[Dict[str, Any]],
    focus_candidate: Dict[str, Any],
    rival_candidate: Dict[str, Any],
    role_spec: Dict[str, str],
    request_index: int,
    observation_index: int,
) -> Dict[str, Any]:
    target_candidate = rival_candidate if role_spec["target_role"] == "rival" else focus_candidate
    target_candidate_id = str(target_candidate.get("candidate_id") or target_candidate.get("target_candidate_id"))
    focus_id = str(pair.get("focus_candidate_id"))
    rival_id = str(pair.get("rival_candidate_id"))
    source_position = source_observation.get("viewpoint_position")
    target_position = candidate_position(target_candidate)
    focus_position = candidate_position(focus_candidate) or pair.get("focus_position") or (source_pair or {}).get("focus_position")
    rival_position = candidate_position(rival_candidate) or pair.get("rival_position") or (source_pair or {}).get("rival_position")
    second_role = role_spec["second_pass_view_role"]
    source_role = role_spec["source_view_role"]
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "action_unique_support_rival_region_observation_plan",
        "contract_name": CONTRACT_NAME,
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "source_planner_name": SOURCE_PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_index": request_index,
        "observation_index": observation_index,
        "pair_index": pair.get("pair_index"),
        "pair_id": pair.get("pair_id"),
        "episode_key": pair.get("episode_key"),
        "scene_id": pair.get("scene_id"),
        "scene_key": pair.get("scene_key"),
        "query": pair.get("query"),
        "expanded_retrieval_request_id": request_id(pair),
        "rival_identity_request_id": pair.get("rival_identity_request_id") or request_id(pair),
        "focus_candidate_id": focus_id,
        "rival_candidate_id": rival_id,
        "candidate_id": target_candidate_id,
        "target_candidate_id": target_candidate_id,
        "target_candidate_role": role_spec["target_role"],
        "candidate_ids": [target_candidate_id],
        "selected_candidate_ids": [target_candidate_id],
        "selected_candidate_count": 1,
        "second_observation_candidate_ids": [target_candidate_id],
        "source_view_role": source_role,
        "second_pass_view_role": second_role,
        "second_stage_view_role": second_role,
        "second_stage_source_view_role": source_role,
        "role": second_role,
        "view_role": second_role,
        "viewpoint_pair_role": second_role,
        "viewpoint_id": f"unique_support_rival_region:{request_id(pair)}:{safe_int(pair.get('pair_index')):02d}:{second_role}",
        "source_viewpoint_id": source_observation.get("viewpoint_id"),
        "source_decision_id": None if source_frame is None else source_frame.get("decision_id"),
        "source_target_candidate_id": source_observation.get("target_candidate_id") or source_observation.get("candidate_id"),
        "source_selected_candidate_ids": None if source_frame is None else source_frame.get("selected_candidate_ids"),
        "source_associated_candidate_heading_count": None
        if source_frame is None
        else source_frame.get("associated_candidate_heading_count"),
        "source_has_candidate_association": None if source_frame is None else source_frame.get("has_candidate_association"),
        "source_detector_box_count": None if source_frame is None else source_frame.get("detector_box_count"),
        "source_sam2_mask_count": None if source_frame is None else source_frame.get("sam2_mask_count"),
        "target_position": target_candidate.get("position"),
        "target_visit_position": target_candidate.get("visit_position"),
        "focus_position": focus_position,
        "rival_position": rival_position,
        "focus_rival_span_m": pair.get("focus_rival_span_m")
        if pair.get("focus_rival_span_m") is not None
        else horizontal_distance(focus_position, rival_position),
        "target_distance_from_viewpoint_m": horizontal_distance(source_position, target_position),
        "focus_distance_from_viewpoint_m": horizontal_distance(source_position, focus_position),
        "rival_distance_from_viewpoint_m": horizontal_distance(source_position, rival_position),
        "first_pass_goal_region_evidence_status": pair.get("goal_region_evidence_status"),
        "first_pass_inspection_blocker": pair.get("inspection_blocker"),
        "first_pass_focus_own_support": pair.get("focus_own_support"),
        "first_pass_rival_own_support": pair.get("rival_own_support"),
        "first_pass_common_focus_support": pair.get("common_focus_support"),
        "first_pass_focus_own_associated_heading_count": pair.get("focus_own_associated_heading_count"),
        "first_pass_rival_own_associated_heading_count": pair.get("rival_own_associated_heading_count"),
        "first_pass_common_focus_associated_heading_count": pair.get("common_focus_associated_heading_count"),
        "rival_region_observation_action": "collect_second_pass_rival_region_evidence",
        "rival_region_observation_reason": role_spec["reason"],
        "viewpoint_reuse_allowed_by_contract": True,
        "viewpoint_reused_from_first_pass": True,
        "terminal_commit_allowed": False,
        "commit_after_rival_region_observation": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    row.update(copy_view_geometry(source_observation))
    return row


def make_skip_row(
    *,
    pair: Dict[str, Any],
    request_index: int,
    reason: str,
    source_view_role_name: Optional[str] = None,
    second_pass_view_role: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_unique_support_rival_region_skipped",
        "contract_name": CONTRACT_NAME,
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "episode_key": pair.get("episode_key"),
        "scene_id": pair.get("scene_id"),
        "scene_key": pair.get("scene_key"),
        "query": pair.get("query"),
        "expanded_retrieval_request_id": request_id(pair),
        "rival_identity_request_id": pair.get("rival_identity_request_id") or request_id(pair),
        "pair_id": pair.get("pair_id"),
        "pair_index": pair.get("pair_index"),
        "focus_candidate_id": pair.get("focus_candidate_id"),
        "rival_candidate_id": pair.get("rival_candidate_id"),
        "source_view_role": source_view_role_name,
        "second_pass_view_role": second_pass_view_role,
        "skip_reason": reason,
        "terminal_commit_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_candidate_artifacts(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        key = (str(row.get("scene_id")), str(row.get("query")), request_id(row))
        grouped[key].append(dict(row))

    output: List[Dict[str, Any]] = []
    for (scene_id, query, rid), rows in sorted(grouped.items(), key=lambda item: request_sort_key(item[0][2])):
        exemplar = rows[0]
        candidates = [candidate_payload(row, str(row.get("rival_region_candidate_role"))) for row in rows]
        candidates.sort(
            key=lambda row: (
                role_rank(str(row.get("candidate_role"))),
                safe_int(row.get("semantic_rank")),
                str(row.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "unique_support_rival_region_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": exemplar.get("scene_key"),
                "query": query,
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id") or rid,
                "episode_key": exemplar.get("episode_key"),
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def group_ambiguous_pairs_by_request(pair_rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in pair_rows:
        if str(row.get("goal_region_evidence_status")) != "ambiguous_goal_region_pair":
            continue
        grouped[request_id(row)].append(dict(row))
    for rid in grouped:
        grouped[rid].sort(key=lambda row: (safe_int(row.get("pair_index")), str(row.get("pair_id"))))
    return grouped


def count_forbidden(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        for finding in scan_forbidden_keys(row):
            findings.append(f"row[{index}].{finding}")
    return findings


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    inspection_summary: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    observation_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    action_rows = [*request_rows, *pair_rows, *candidate_rows, *observation_rows, *skipped_rows]
    forbidden = count_forbidden(action_rows)
    terminal_rows = [
        row
        for row in action_rows
        if row.get("terminal_commit") is True
        or row.get("terminal_commit_allowed") is True
        or row.get("commit_after_rival_region_observation") is True
    ]
    required = contract.get("required_gates") or {}
    required_roles = set((contract.get("row_contract") or {}).get("required_second_pass_view_roles") or [])
    roles_by_pair: Dict[str, set[str]] = defaultdict(set)
    for row in observation_rows:
        roles_by_pair[str(row.get("pair_id"))].add(str(row.get("second_pass_view_role")))
    role_set_failures = {
        pair_id: sorted(roles)
        for pair_id, roles in roles_by_pair.items()
        if roles != required_roles
    }
    target_scope = contract.get("target_scope") or {}
    gate = {
        "source_evidence_gate_passed": bool((contract.get("source_metrics") or {}).get("source_evidence_gate_passed"))
        == bool(required.get("source_evidence_gate_passed", True)),
        "source_inspection_gate_passed": bool((inspection_summary.get("gate") or {}).get("inspection_gate_passed"))
        == bool(required.get("source_inspection_gate_passed", True)),
        "expected_request_rows_passed": len(request_rows) == int(required.get("expected_request_rows", 0)),
        "expected_pair_rows_passed": len(pair_rows) == int(required.get("expected_pair_rows", 0)),
        "expected_request_candidate_rows_passed": len(candidate_rows)
        == int(required.get("expected_request_candidate_rows", 0)),
        "expected_observation_plan_rows_passed": len(observation_rows)
        == int(required.get("expected_observation_plan_rows", 0)),
        "required_second_pass_roles_per_pair_passed": bool(pair_rows)
        and len(role_set_failures) == 0
        and all(len(roles_by_pair.get(str(row.get("pair_id")), set())) == int(required.get("required_second_pass_roles_per_pair", 0)) for row in pair_rows),
        "skipped_rows_passed": len(skipped_rows) == 0,
        "action_evidence_forbidden_key_count_passed": len(forbidden)
        == int(required.get("action_evidence_forbidden_key_count", 0)),
        "terminal_commit_rows_passed": len(terminal_rows) == int(required.get("terminal_commit_rows", 0)),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["unique_support_rival_region_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    request_ids = sorted({request_id(row) for row in request_rows}, key=request_sort_key)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "source_plan_root": str(args.source_plan_root),
        "source_inspection_root": str(args.source_inspection_root),
        "source_frame_root": str(args.source_frame_root),
        "out_root": str(args.out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "source_evidence_gate_passed": bool((contract.get("source_metrics") or {}).get("source_evidence_gate_passed")),
        "source_inspection_gate_passed": bool((inspection_summary.get("gate") or {}).get("inspection_gate_passed")),
        "request_rows": len(request_rows),
        "pair_rows": len(pair_rows),
        "request_candidate_rows": len(candidate_rows),
        "observation_plan_rows": len(observation_rows),
        "skipped_rows": len(skipped_rows),
        "request_ids": request_ids,
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_candidate_count": sum(int(row.get("candidate_count") or 0) for row in artifact_rows),
        "pair_rows_by_request": dict(sorted(Counter(request_id(row) for row in pair_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "candidate_rows_by_request": dict(sorted(Counter(request_id(row) for row in candidate_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "observation_rows_by_request": dict(sorted(Counter(request_id(row) for row in observation_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "second_pass_view_role_counts": dict(sorted(Counter(str(row.get("second_pass_view_role")) for row in observation_rows).items())),
        "source_view_role_counts": dict(sorted(Counter(str(row.get("source_view_role")) for row in observation_rows).items())),
        "target_candidate_role_counts": dict(sorted(Counter(str(row.get("target_candidate_role")) for row in observation_rows).items())),
        "scene_counts": dict(sorted(Counter(str(row.get("scene_key")) for row in pair_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in pair_rows).items())),
        "role_set_failures": role_set_failures,
        "target_scope": {
            "target_request_rows": target_scope.get("target_request_rows"),
            "target_ambiguous_pair_rows": target_scope.get("target_ambiguous_pair_rows"),
            "target_request_candidate_rows": target_scope.get("target_request_candidate_rows"),
            "target_observation_rows": target_scope.get("target_observation_rows"),
        },
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "request_rows": "unique_support_rival_region_request_rows.jsonl",
            "pair_rows": "unique_support_rival_region_pair_rows.jsonl",
            "request_candidate_rows": "unique_support_rival_region_request_candidate_rows.jsonl",
            "candidate_artifact": "unique_support_rival_region_candidate_artifact.jsonl",
            "observation_plan": "unique_support_rival_region_observation_plan.jsonl",
            "skipped_rows": "unique_support_rival_region_skipped.jsonl",
            "summary": "unique_support_rival_region_plan_summary.json",
        },
        "interpretation": {
            "fact": "The planner materializes only ambiguous first-pass goal-region pairs and reuses first-pass viewpoint geometry with swapped target candidates.",
            "agent_inference": "Passing this gate means the next evidence step can render second-pass rival-region frames, not authorize terminal goal-validity arbitration.",
            "paper_claim": "No paper claim is allowed from this planner alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    source_plan_root = Path(args.source_plan_root)
    source_inspection_root = Path(args.source_inspection_root)
    source_frame_root = Path(args.source_frame_root)
    inspection_summary = load_json(source_inspection_root / "unique_support_goal_region_inspection_summary.json")
    request_inspections = load_jsonl(source_inspection_root / "unique_support_goal_region_request_inspection_rows.jsonl")
    pair_inspections = load_jsonl(source_inspection_root / "unique_support_goal_region_pair_inspection_rows.jsonl")
    source_pairs = load_jsonl(source_plan_root / "unique_support_goal_region_pair_rows.jsonl")
    source_candidates = load_jsonl(source_plan_root / "unique_support_goal_region_candidate_targets.jsonl")
    source_artifacts = load_jsonl(source_plan_root / "unique_support_goal_region_candidate_artifact.jsonl")
    source_observations = load_jsonl(source_plan_root / "unique_support_goal_region_observation_targets.jsonl")
    source_frame_summary_path = source_frame_root / "expanded_retrieval_detector_frame_summary.jsonl"
    source_frames = load_jsonl(source_frame_summary_path) if source_frame_summary_path.exists() else []

    requests_by_id = {request_id(row): dict(row) for row in request_inspections if request_id(row)}
    ambiguous_by_request = group_ambiguous_pairs_by_request(pair_inspections)
    source_pair_by_id = index_rows_by_pair(source_pairs)
    source_observation_by_pair_role = index_observations_by_pair_role(source_observations)
    source_frame_by_pair_role = index_frames_by_pair_role(source_frames)
    candidate_by_request_id = index_candidates(source_candidates, source_artifacts)

    request_rows: List[Dict[str, Any]] = []
    pair_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []
    observation_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []

    for request_index, rid in enumerate(sorted(ambiguous_by_request, key=request_sort_key)):
        if int(args.max_requests) > 0 and request_index >= int(args.max_requests):
            break
        pairs = ambiguous_by_request[rid]
        request = requests_by_id.get(rid, pairs[0])
        request_rows.append(make_request_row(request, pairs, request_index))

        role_by_candidate_id: Dict[str, str] = {}
        for pair in pairs:
            focus_id = str(pair.get("focus_candidate_id"))
            rival_id = str(pair.get("rival_candidate_id"))
            role_by_candidate_id.setdefault(focus_id, "focus_unique_support")
            role_by_candidate_id.setdefault(rival_id, "ambiguous_rival_region")

        candidate_ids = sorted(
            role_by_candidate_id,
            key=lambda candidate_id: (
                role_rank(role_by_candidate_id[candidate_id]),
                safe_int((candidate_by_request_id.get((rid, candidate_id)) or {}).get("semantic_rank")),
                candidate_id,
            ),
        )
        for candidate_index, candidate_id in enumerate(candidate_ids):
            candidate = candidate_by_request_id.get((rid, candidate_id))
            if candidate is None:
                skipped_rows.append(
                    make_skip_row(
                        pair=pairs[0],
                        request_index=request_index,
                        reason=f"missing_candidate_geometry:{candidate_id}",
                    )
                )
                continue
            candidate_rows.append(
                make_candidate_row(
                    request=request,
                    candidate=candidate,
                    role=role_by_candidate_id[candidate_id],
                    request_index=request_index,
                    candidate_index=candidate_index,
                )
            )

        for pair in pairs:
            source_pair = source_pair_by_id.get(str(pair.get("pair_id") or ""))
            source_views = {
                role_spec["source_view_role"]: source_frame_by_pair_role.get((str(pair.get("pair_id")), role_spec["source_view_role"]))
                for role_spec in SECOND_PASS_ROLE_MAP
            }
            pair_rows.append(
                make_pair_row(
                    pair=pair,
                    source_pair=source_pair,
                    source_views=source_views,
                    request_index=request_index,
                )
            )
            focus_candidate = candidate_by_request_id.get((rid, str(pair.get("focus_candidate_id"))))
            rival_candidate = candidate_by_request_id.get((rid, str(pair.get("rival_candidate_id"))))
            if focus_candidate is None or rival_candidate is None:
                skipped_rows.append(
                    make_skip_row(
                        pair=pair,
                        request_index=request_index,
                        reason="missing_focus_or_rival_candidate_geometry",
                    )
                )
                continue
            for role_spec in SECOND_PASS_ROLE_MAP:
                source_role_name = role_spec["source_view_role"]
                source_observation = source_observation_by_pair_role.get((str(pair.get("pair_id")), source_role_name))
                source_frame = source_frame_by_pair_role.get((str(pair.get("pair_id")), source_role_name))
                if source_observation is None:
                    skipped_rows.append(
                        make_skip_row(
                            pair=pair,
                            request_index=request_index,
                            reason="missing_source_viewpoint_geometry",
                            source_view_role_name=source_role_name,
                            second_pass_view_role=role_spec["second_pass_view_role"],
                        )
                    )
                    continue
                observation_rows.append(
                    make_observation_row(
                        args=args,
                        pair=pair,
                        source_pair=source_pair,
                        source_observation=source_observation,
                        source_frame=source_frame,
                        focus_candidate=focus_candidate,
                        rival_candidate=rival_candidate,
                        role_spec=role_spec,
                        request_index=request_index,
                        observation_index=len(observation_rows),
                    )
                )

    artifact_rows = build_candidate_artifacts(candidate_rows)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "unique_support_rival_region_request_rows.jsonl", request_rows)
    write_jsonl(out_root / "unique_support_rival_region_pair_rows.jsonl", pair_rows)
    write_jsonl(out_root / "unique_support_rival_region_request_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "unique_support_rival_region_candidate_artifact.jsonl", artifact_rows)
    write_jsonl(out_root / "unique_support_rival_region_observation_plan.jsonl", observation_rows)
    write_jsonl(out_root / "unique_support_rival_region_skipped.jsonl", skipped_rows)
    summary = summarize(
        args=args,
        contract=contract,
        inspection_summary=inspection_summary,
        request_rows=request_rows,
        pair_rows=pair_rows,
        candidate_rows=candidate_rows,
        observation_rows=observation_rows,
        skipped_rows=skipped_rows,
        artifact_rows=artifact_rows,
    )
    write_json(out_root / "unique_support_rival_region_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan second-pass rival-region evidence for ambiguous unique-support goal-region pairs."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--source-plan-root", default=SOURCE_PLAN_ROOT_DEFAULT)
    parser.add_argument("--source-inspection-root", default=SOURCE_INSPECTION_ROOT_DEFAULT)
    parser.add_argument("--source-frame-root", default=SOURCE_FRAME_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--run-id", default="unique_support_rival_region_v1")
    parser.add_argument("--max-requests", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
