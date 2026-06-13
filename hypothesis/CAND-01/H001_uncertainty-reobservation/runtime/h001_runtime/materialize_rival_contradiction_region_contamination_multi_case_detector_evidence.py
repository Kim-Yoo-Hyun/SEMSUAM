import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_multi_case_detector_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_multi_case_detector_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_detector_evidence_v1"

OUTPUT_FILES = {
    "candidate_view_rows": "rival_contradiction_region_contamination_multi_case_detector_candidate_view_rows.jsonl",
    "role_rows": "rival_contradiction_region_contamination_multi_case_detector_role_rows.jsonl",
    "pair_rows": "rival_contradiction_region_contamination_multi_case_detector_pair_rows.jsonl",
    "request_rows": "rival_contradiction_region_contamination_multi_case_detector_request_rows.jsonl",
    "audit_rows": "rival_contradiction_region_contamination_multi_case_detector_audit_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_multi_case_detector_evidence_summary.json",
}

FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "candidate_pair_label_pattern_for_evaluation_only",
    "correct_candidate",
    "evaluation_only",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_instance_id",
    "gt_label",
    "gt_object_id",
    "ground_truth",
    "map_pose_consistency_delta",
    "oracle_object_id",
    "oracle_shortest_path",
    "success_label",
    "valid_candidate",
    "wasted_path_m",
    "wrong_goal",
    "wrong_goal_visit",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
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


def resolve_path(path_like: str) -> Path:
    path = Path(path_like)
    if path.exists():
        return path
    if path_like.startswith("local_dataset/runs/"):
        runs_path = Path("/runs") / path_like.removeprefix("local_dataset/runs/")
        if runs_path.exists():
            return runs_path
    workspace_path = Path("/workspace") / path
    if workspace_path.exists():
        return workspace_path
    return path


def path_from_contract(contract: Mapping[str, Any], key: str) -> Path:
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"missing source path: {key}")
    return resolve_path(str(source[key]))


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(nums),
        "min": min(nums),
        "mean": sum(nums) / len(nums),
        "max": max(nums),
    }


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        str(row.get("expanded_retrieval_request_id") or row.get("request_id") or ""),
        str(row.get("episode_key") or ""),
    )


def role_name(row: Mapping[str, Any]) -> str:
    return str(row.get("role") or row.get("view_role") or row.get("rival_observation_role") or "")


def candidate_view_state(rows: Sequence[Mapping[str, Any]]) -> str:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    if associated and any(str(row.get("depth_check_status")) == "consistent" for row in associated):
        return "associated_depth_consistent"
    if associated:
        return "associated_depth_mixed"
    if any(row.get("projected_pixel_inside_box") is True or row.get("projected_pixel_inside_mask") is True for row in rows):
        return "visible_without_candidate_association"
    return "not_observed_in_role"


def role_evidence_state(role: str, candidate_rows: Sequence[Mapping[str, Any]]) -> str:
    by_pair_role = {str(row.get("candidate_pair_role")): row for row in candidate_rows}
    a_assoc = int(by_pair_role.get("candidate_a", {}).get("associated_rows") or 0) > 0
    b_assoc = int(by_pair_role.get("candidate_b", {}).get("associated_rows") or 0) > 0
    if role == "shared_region_or_relation_anchor_view" and a_assoc and b_assoc:
        return "shared_region_overlap_observed"
    if role == "cross_candidate_challenge_view" and a_assoc and b_assoc:
        return "cross_candidate_contamination_observed"
    if a_assoc and b_assoc:
        return "both_candidates_associated"
    if a_assoc:
        return "candidate_a_only_associated"
    if b_assoc:
        return "candidate_b_only_associated"
    return "neither_candidate_associated"


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row.get("action_evidence_inputs", {}))
        scan(row.get("action_route_inputs", {}))
    return sorted(found)


def source_pair_context(source_row: Mapping[str, Any], candidate_roles: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    roles_by_name = {str(row.get("candidate_pair_role")): row for row in candidate_roles}
    a = roles_by_name.get("candidate_a", {})
    b = roles_by_name.get("candidate_b", {})
    return {
        "scene_key": source_row.get("scene_key"),
        "query": source_row.get("query"),
        "episode_key": source_row.get("episode_key"),
        "source_name": source_row.get("source_name"),
        "request_id": source_row.get("request_id"),
        "expanded_retrieval_request_id": source_row.get("request_id"),
        "multi_case_source_id": source_row.get("multi_case_source_id"),
        "candidate_a_id": a.get("candidate_id") or source_row.get("candidate_a_id"),
        "candidate_b_id": b.get("candidate_id") or source_row.get("candidate_b_id"),
        "candidate_ids": [
            value
            for value in [a.get("candidate_id") or source_row.get("candidate_a_id"), b.get("candidate_id") or source_row.get("candidate_b_id")]
            if value
        ],
    }


def build_candidate_view_row(
    *,
    context: Mapping[str, Any],
    role: str,
    candidate_id: str,
    candidate_pair_role: str,
    paired_candidate_id: str,
    rows: Sequence[Mapping[str, Any]],
    frame_row: Optional[Mapping[str, Any]],
    source_candidate_role: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    exemplar = rows[0] if rows else frame_row or {}
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    consistent = [row for row in associated if str(row.get("depth_check_status")) == "consistent"]
    mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    out_of_fov = [
        row
        for row in rows
        if str(row.get("projection_status")) == "out_of_fov" or str(row.get("depth_check_status")) == "out_of_fov"
    ]
    unavailable = [row for row in rows if str(row.get("depth_check_status")) == "unavailable"]
    state = candidate_view_state(rows)
    action_inputs = {
        "role": role,
        "candidate_id": candidate_id,
        "candidate_pair_role": candidate_pair_role,
        "association_rows": len(rows),
        "associated_rows": len(associated),
        "inside_box_rows": len(inside_box),
        "inside_mask_rows": len(inside_mask),
        "depth_consistent_rows": len(consistent),
        "depth_mismatch_rows": len(mismatch),
        "out_of_fov_rows": len(out_of_fov),
        "unavailable_rows": len(unavailable),
        "candidate_view_evidence_state": state,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_detector_candidate_view",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "scene_id": exemplar.get("scene_id"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "multi_case_source_id": context.get("multi_case_source_id"),
        "role": role,
        "view_role": role,
        "rival_observation_role": role,
        "rival_evidence_axis": (frame_row or {}).get("rival_evidence_axis") or exemplar.get("rival_evidence_axis"),
        "candidate_id": candidate_id,
        "paired_candidate_id": paired_candidate_id,
        "candidate_pair_role": candidate_pair_role,
        "candidate_role_is_not_correctness": True,
        "source_candidate_evidence_status": None if source_candidate_role is None else source_candidate_role.get("candidate_evidence_status"),
        "target_candidate_id": (frame_row or {}).get("target_candidate_id") or exemplar.get("target_candidate_id"),
        "association_rows": len(rows),
        "associated_rows": len(associated),
        "visible_rows": len(visible),
        "inside_box_rows": len(inside_box),
        "inside_mask_rows": len(inside_mask),
        "depth_consistent_rows": len(consistent),
        "depth_mismatch_rows": len(mismatch),
        "out_of_fov_rows": len(out_of_fov),
        "unavailable_rows": len(unavailable),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_selected_offset_profile": sorted(
            value
            for value in (safe_float(row.get("projection_anchor_height_offset_m")) for row in rows)
            if value is not None
        ),
        "best_box_score_stats": number_stats(row.get("best_box_score") for row in rows),
        "depth_error_stats_m": number_stats(row.get("depth_error_m") for row in rows),
        "associated_depth_error_stats_m": number_stats(row.get("depth_error_m") for row in associated),
        "detector_box_count": (frame_row or {}).get("detector_box_count"),
        "sam2_mask_count": (frame_row or {}).get("sam2_mask_count"),
        "candidate_view_evidence_state": state,
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_role_row(
    *,
    context: Mapping[str, Any],
    role: str,
    rows: Sequence[Mapping[str, Any]],
    frame_row: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    by_pair_role = {str(row.get("candidate_pair_role")): row for row in rows}
    a_row = by_pair_role.get("candidate_a", {})
    b_row = by_pair_role.get("candidate_b", {})
    state = role_evidence_state(role, rows)
    a_assoc = int(a_row.get("associated_rows") or 0)
    b_assoc = int(b_row.get("associated_rows") or 0)
    action_inputs = {
        "role": role,
        "candidate_a_associated_rows": a_assoc,
        "candidate_b_associated_rows": b_assoc,
        "role_evidence_state": state,
        "both_candidates_associated": a_assoc > 0 and b_assoc > 0,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_detector_role",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "scene_id": (frame_row or {}).get("scene_id"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "multi_case_source_id": context.get("multi_case_source_id"),
        "role": role,
        "view_role": role,
        "rival_observation_role": role,
        "rival_evidence_axis": (frame_row or {}).get("rival_evidence_axis"),
        "candidate_a_id": context.get("candidate_a_id"),
        "candidate_b_id": context.get("candidate_b_id"),
        "candidate_a_associated_rows": a_assoc,
        "candidate_b_associated_rows": b_assoc,
        "candidate_a_depth_consistent_rows": a_row.get("depth_consistent_rows", 0),
        "candidate_b_depth_consistent_rows": b_row.get("depth_consistent_rows", 0),
        "candidate_view_evidence_states": {
            str(row.get("candidate_pair_role")): row.get("candidate_view_evidence_state")
            for row in rows
        },
        "role_evidence_state": state,
        "both_candidates_associated": a_assoc > 0 and b_assoc > 0,
        "single_candidate_isolation": (a_assoc > 0) != (b_assoc > 0),
        "rendered_heading_count": (frame_row or {}).get("rendered_heading_count"),
        "detector_box_count": (frame_row or {}).get("detector_box_count"),
        "sam2_mask_count": (frame_row or {}).get("sam2_mask_count"),
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_pair_row(context: Mapping[str, Any], role_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_role = {str(row.get("role")): row for row in role_rows}
    shared = by_role.get("shared_region_or_relation_anchor_view", {})
    cross = by_role.get("cross_candidate_challenge_view", {})
    a_own = by_role.get("candidate_a_own_view", {})
    b_own = by_role.get("candidate_b_own_view", {})
    role_state_counts = compact_counter(row.get("role_evidence_state") for row in role_rows)
    if cross.get("role_evidence_state") == "cross_candidate_contamination_observed":
        state = "cross_candidate_contamination_observed"
    elif shared.get("role_evidence_state") == "shared_region_overlap_observed":
        state = "rival_region_contamination_or_same_category_overlap_observed"
    elif a_own.get("candidate_a_associated_rows", 0) and b_own.get("candidate_b_associated_rows", 0):
        state = "both_candidates_own_view_supported"
    elif a_own.get("candidate_a_associated_rows", 0):
        state = "candidate_a_region_support_only"
    elif b_own.get("candidate_b_associated_rows", 0):
        state = "candidate_b_region_support_only"
    else:
        state = "insufficient_post_detector_evidence"
    action_inputs = {
        "role_support_matrix": {
            str(row.get("role")): {
                "state": row.get("role_evidence_state"),
                "candidate_a_associated_rows": row.get("candidate_a_associated_rows"),
                "candidate_b_associated_rows": row.get("candidate_b_associated_rows"),
            }
            for row in role_rows
        },
        "candidate_tuple_association_profile": {
            "role_rows_with_any_association": sum(
                1
                for row in role_rows
                if int(row.get("candidate_a_associated_rows") or 0) > 0
                or int(row.get("candidate_b_associated_rows") or 0) > 0
            ),
            "role_rows_with_both_candidates_associated": sum(1 for row in role_rows if row.get("both_candidates_associated") is True),
        },
        "pair_evidence_state": state,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_detector_pair",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "multi_case_source_id": context.get("multi_case_source_id"),
        "candidate_a_id": context.get("candidate_a_id"),
        "candidate_b_id": context.get("candidate_b_id"),
        "candidate_a_and_b_are_not_correctness_roles": True,
        "role_evidence_state_counts": role_state_counts,
        "pair_evidence_state": state,
        "contamination_or_contradiction_evidence_available": state
        in {
            "cross_candidate_contamination_observed",
            "rival_region_contamination_or_same_category_overlap_observed",
            "candidate_a_region_support_only",
            "candidate_b_region_support_only",
        },
        "terminal_selector_allowed_from_this_evidence": False,
        "evaluation_join_required": True,
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_request_row(context: Mapping[str, Any], pair_row: Mapping[str, Any]) -> Dict[str, Any]:
    pair_state = str(pair_row.get("pair_evidence_state"))
    if pair_state in {"cross_candidate_contamination_observed", "rival_region_contamination_or_same_category_overlap_observed"}:
        request_state = "contradiction_or_contamination_evidence_available"
    elif pair_state in {"candidate_a_region_support_only", "candidate_b_region_support_only", "both_candidates_own_view_supported"}:
        request_state = "ambiguous_shared_or_cross_region_evidence"
    else:
        request_state = "insufficient_evidence_after_observation"
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_detector_request",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "multi_case_source_id": context.get("multi_case_source_id"),
        "candidate_a_id": context.get("candidate_a_id"),
        "candidate_b_id": context.get("candidate_b_id"),
        "request_evidence_state": request_state,
        "pair_evidence_state": pair_state,
        "evaluation_join_required": True,
        "terminal_selector_allowed_from_this_evidence": False,
        "action_evidence_inputs": {
            "request_evidence_state": request_state,
            "pair_evidence_state": pair_state,
        },
        **common_flags(),
    }


def build_audit_row(context: Mapping[str, Any], request_row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_detector_audit",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "multi_case_source_id": context.get("multi_case_source_id"),
        "audit_status": "evaluation_join_required_before_utility_claim",
        "request_evidence_state": request_row.get("request_evidence_state"),
        "blocked_next_claims": [
            "terminal_goal_commit",
            "candidate_rejection",
            "wrong_goal_reduction",
            "wasted_path_reduction",
            "map_pose_consistency_improvement",
            "paper_claim",
        ],
        **common_flags(),
    }


def build_rows(
    contract: Mapping[str, Any],
    source_rows: Sequence[Mapping[str, Any]],
    source_candidate_roles: Sequence[Mapping[str, Any]],
    associations: Sequence[Mapping[str, Any]],
    frame_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    roles = list((contract.get("analyzer_contract") or {}).get("required_observation_roles") or [])
    role_rows_by_request = defaultdict(list)
    candidate_roles_by_request = defaultdict(list)
    associations_by_request_role_candidate = defaultdict(list)
    frames_by_request_role: Dict[Tuple[Tuple[str, str, str, str], str], Mapping[str, Any]] = {}

    for row in source_candidate_roles:
        candidate_roles_by_request[request_key(row)].append(row)
    for row in associations:
        associations_by_request_role_candidate[(request_key(row), role_name(row), str(row.get("candidate_id") or ""))].append(row)
    for row in frame_rows:
        frames_by_request_role[(request_key(row), role_name(row))] = row

    candidate_view_rows: List[Dict[str, Any]] = []
    detector_role_rows: List[Dict[str, Any]] = []
    pair_rows: List[Dict[str, Any]] = []
    request_rows: List[Dict[str, Any]] = []
    audit_rows: List[Dict[str, Any]] = []

    for source_row in sorted(source_rows, key=lambda row: (str(row.get("scene_key")), str(row.get("query")), str(row.get("request_id")))):
        key = request_key(source_row)
        source_roles = candidate_roles_by_request.get(key, [])
        if len(source_roles) != 2:
            raise RuntimeError({"request": key, "source_candidate_role_rows": len(source_roles)})
        context = source_pair_context(source_row, source_roles)
        source_by_candidate = {str(row.get("candidate_id")): row for row in source_roles}
        candidate_pair_roles = {
            "candidate_a": str(context.get("candidate_a_id")),
            "candidate_b": str(context.get("candidate_b_id")),
        }

        per_request_candidate_rows: List[Dict[str, Any]] = []
        for role in roles:
            frame = frames_by_request_role.get((key, role))
            if frame is None:
                raise RuntimeError({"request": key, "missing_frame_role": role})
            for pair_role, candidate_id in candidate_pair_roles.items():
                paired_id = candidate_pair_roles["candidate_b" if pair_role == "candidate_a" else "candidate_a"]
                row = build_candidate_view_row(
                    context=context,
                    role=role,
                    candidate_id=candidate_id,
                    candidate_pair_role=pair_role,
                    paired_candidate_id=paired_id,
                    rows=associations_by_request_role_candidate.get((key, role, candidate_id), []),
                    frame_row=frame,
                    source_candidate_role=source_by_candidate.get(candidate_id),
                )
                candidate_view_rows.append(row)
                per_request_candidate_rows.append(row)

        for role in roles:
            role_candidate_rows = [row for row in per_request_candidate_rows if row.get("role") == role]
            role_row = build_role_row(
                context=context,
                role=role,
                rows=role_candidate_rows,
                frame_row=frames_by_request_role.get((key, role)),
            )
            detector_role_rows.append(role_row)
            role_rows_by_request[key].append(role_row)

        pair = build_pair_row(context, role_rows_by_request[key])
        request = build_request_row(context, pair)
        audit = build_audit_row(context, request)
        pair_rows.append(pair)
        request_rows.append(request)
        audit_rows.append(audit)

    return candidate_view_rows, detector_role_rows, pair_rows, request_rows, audit_rows


def summarize(
    *,
    contract: Mapping[str, Any],
    detector_summary: Mapping[str, Any],
    detector_diagnostic: Mapping[str, Any],
    candidate_view_rows: Sequence[Mapping[str, Any]],
    role_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    expected = contract["minimum_evidence_gate"]
    all_rows = list(candidate_view_rows) + list(role_rows) + list(pair_rows) + list(request_rows) + list(audit_rows)
    forbidden = scan_forbidden_action_inputs(all_rows)
    terminal_rows = sum(1 for row in all_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in all_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in all_rows if row.get("candidate_rejection") is True)
    role_rows_with_any_association = sum(
        1
        for row in role_rows
        if int(row.get("candidate_a_associated_rows") or 0) > 0 or int(row.get("candidate_b_associated_rows") or 0) > 0
    )
    pair_rows_with_any_association = sum(
        1
        for row in pair_rows
        if (row.get("action_evidence_inputs") or {}).get("candidate_tuple_association_profile", {}).get(
            "role_rows_with_any_association", 0
        )
        > 0
    )
    associated_scene_count = len(
        {
            str(row.get("scene_key"))
            for row in role_rows
            if int(row.get("candidate_a_associated_rows") or 0) > 0 or int(row.get("candidate_b_associated_rows") or 0) > 0
        }
    )
    associated_query_count = len(
        {
            str(row.get("query"))
            for row in role_rows
            if int(row.get("candidate_a_associated_rows") or 0) > 0 or int(row.get("candidate_b_associated_rows") or 0) > 0
        }
    )
    gate = {
        "source_detector_substrate_gate_passed": bool(
            (detector_summary.get("multi_case_gate") or {}).get("passes_multi_case_detector_substrate_gate")
        ),
        "candidate_view_rows_match": len(candidate_view_rows) == int(expected["expected_candidate_view_rows"]),
        "role_rows_match": len(role_rows) == int(expected["expected_role_rows"]),
        "pair_rows_match": len(pair_rows) == int(expected["expected_pair_rows"]),
        "request_rows_match": len(request_rows) == int(expected["expected_request_rows"]),
        "required_role_count_pass": len({row.get("role") for row in role_rows}) == int(expected["expected_required_roles"]),
        "minimum_pair_rows_with_any_candidate_association_pass": pair_rows_with_any_association
        >= int(expected["minimum_pair_rows_with_any_candidate_association"]),
        "minimum_role_rows_with_candidate_association_pass": role_rows_with_any_association
        >= int(expected["minimum_role_rows_with_candidate_association"]),
        "minimum_associated_scene_count_pass": associated_scene_count >= int(expected["minimum_associated_scene_count"]),
        "minimum_associated_query_count_pass": associated_query_count >= int(expected["minimum_associated_query_count"]),
        "action_evidence_forbidden_key_count_pass": len(forbidden)
        <= int(expected["action_evidence_forbidden_key_count_maximum"]),
        "terminal_commit_rows_pass": terminal_rows <= int(expected["terminal_commit_rows_maximum"]),
        "candidate_commit_rows_pass": candidate_commit_rows <= int(expected["candidate_commit_rows_maximum"]),
        "candidate_rejection_rows_pass": candidate_rejection_rows <= int(expected["candidate_rejection_rows_maximum"]),
        "uses_gt_for_action_pass": not any(row.get("uses_gt_for_action") is True for row in all_rows),
        "paper_claim_blocked": not any(row.get("paper_claim_allowed") is True for row in all_rows),
    }
    gate["multi_case_detector_evidence_materializer_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "source_detector_summary": "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json",
        "source_detector_diagnostic": "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_detector_substrate_v1/rival_contradiction_region_contamination_multi_case_detector_substrate_diagnostic.json",
        "candidate_view_rows": len(candidate_view_rows),
        "role_rows": len(role_rows),
        "pair_rows": len(pair_rows),
        "request_rows": len(request_rows),
        "audit_rows": len(audit_rows),
        "candidate_view_evidence_state_counts": compact_counter(row.get("candidate_view_evidence_state") for row in candidate_view_rows),
        "role_evidence_state_counts": compact_counter(row.get("role_evidence_state") for row in role_rows),
        "pair_evidence_state_counts": compact_counter(row.get("pair_evidence_state") for row in pair_rows),
        "request_evidence_state_counts": compact_counter(row.get("request_evidence_state") for row in request_rows),
        "role_rows_with_any_candidate_association": role_rows_with_any_association,
        "pair_rows_with_any_candidate_association": pair_rows_with_any_association,
        "associated_scene_count": associated_scene_count,
        "associated_query_count": associated_query_count,
        "source_substrate_failure_taxonomy": detector_diagnostic.get("failure_taxonomy", []),
        "action_evidence_forbidden_keys_found": forbidden,
        "terminal_commit_rows": terminal_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "next_task": "freeze_multi_case_evaluation_only_join_contract",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(resolve_path(args.contract))
    detector_summary = load_json(path_from_contract(contract, "detector_substrate_summary"))
    detector_diagnostic = load_json(path_from_contract(contract, "detector_substrate_diagnostic"))
    if not (detector_summary.get("multi_case_gate") or {}).get("passes_multi_case_detector_substrate_gate"):
        raise RuntimeError("source multi-case detector substrate gate did not pass")

    associations = load_jsonl(path_from_contract(contract, "detector_associations"))
    frame_rows = load_jsonl(path_from_contract(contract, "detector_frame_summary"))
    source_rows = load_jsonl(path_from_contract(contract, "source_rows"))
    source_candidate_roles = load_jsonl(path_from_contract(contract, "source_candidate_role_rows"))

    candidate_view_rows, role_rows, pair_rows, request_rows, audit_rows = build_rows(
        contract, source_rows, source_candidate_roles, associations, frame_rows
    )
    summary = summarize(
        contract=contract,
        detector_summary=detector_summary,
        detector_diagnostic=detector_diagnostic,
        candidate_view_rows=candidate_view_rows,
        role_rows=role_rows,
        pair_rows=pair_rows,
        request_rows=request_rows,
        audit_rows=audit_rows,
    )

    out_root = resolve_path(args.out_root)
    write_jsonl(out_root / OUTPUT_FILES["candidate_view_rows"], candidate_view_rows)
    write_jsonl(out_root / OUTPUT_FILES["role_rows"], role_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if not summary["gate"]["multi_case_detector_evidence_materializer_gate_passed"]:
        raise RuntimeError("multi-case detector evidence materializer gate failed")


if __name__ == "__main__":
    main()
