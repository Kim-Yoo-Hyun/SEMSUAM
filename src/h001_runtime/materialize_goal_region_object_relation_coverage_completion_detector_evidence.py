import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


SCHEMA_VERSION = "h001.goal_region_object_relation_coverage_completion_detector_evidence.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_goal_region_object_relation_coverage_completion_detector_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_goal_region_object_relation_coverage_completion_detector_evidence_v1"

OUTPUT_FILES = {
    "candidate_view_rows": "goal_region_object_relation_coverage_completion_detector_candidate_view_rows.jsonl",
    "role_rows": "goal_region_object_relation_coverage_completion_detector_role_rows.jsonl",
    "pair_rows": "goal_region_object_relation_coverage_completion_detector_pair_rows.jsonl",
    "request_rows": "goal_region_object_relation_coverage_completion_detector_request_rows.jsonl",
    "audit_rows": "goal_region_object_relation_coverage_completion_detector_audit_rows.jsonl",
    "summary": "goal_region_object_relation_coverage_completion_detector_evidence_summary.json",
}

FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "candidate_correctness_label",
    "candidate_pair_label_pattern_for_evaluation_only",
    "candidate_wrong_label",
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def compact_counter(values: Iterable[Any]) -> dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def number_stats(values: Iterable[Any]) -> dict[str, Optional[float]]:
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


def common_flags() -> dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> list[str]:
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


def candidate_view_state(rows: Sequence[Mapping[str, Any]]) -> str:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    if associated and any(str(row.get("depth_check_status")) == "consistent" for row in associated):
        return "associated_depth_consistent"
    if associated:
        return "associated_depth_mixed"
    if any(row.get("projected_pixel_inside_box") is True or row.get("projected_pixel_inside_mask") is True for row in rows):
        return "visible_without_candidate_association"
    return "not_observed_in_role"


def role_state(role: str, candidate_view_rows: Sequence[Mapping[str, Any]]) -> str:
    by_pair_role = {str(row.get("candidate_pair_role")): row for row in candidate_view_rows}
    a_assoc = int(by_pair_role.get("candidate_a", {}).get("associated_rows") or 0) > 0
    b_assoc = int(by_pair_role.get("candidate_b", {}).get("associated_rows") or 0) > 0

    if role == "candidate_a_goal_region_context_view":
        if a_assoc and b_assoc:
            return "both_goal_region_candidates_supported"
        if a_assoc:
            return "goal_region_candidate_a_supported"
        return "insufficient_role_evidence"
    if role == "candidate_b_goal_region_context_view":
        if a_assoc and b_assoc:
            return "both_goal_region_candidates_supported"
        if b_assoc:
            return "goal_region_candidate_b_supported"
        return "insufficient_role_evidence"
    if role == "shared_goal_region_anchor_view":
        if a_assoc and b_assoc:
            return "shared_goal_region_anchor_overlap_observed"
        return "insufficient_role_evidence"
    if role == "candidate_pair_object_relation_context_view":
        if a_assoc and b_assoc:
            return "object_relation_context_supported"
        return "object_relation_context_missing_after_observation"
    return "insufficient_role_evidence"


def pair_state(role_rows: Sequence[Mapping[str, Any]]) -> str:
    states = {str(row.get("role")): str(row.get("role_evidence_state")) for row in role_rows}
    a_goal = states.get("candidate_a_goal_region_context_view") in {
        "goal_region_candidate_a_supported",
        "both_goal_region_candidates_supported",
    }
    b_goal = states.get("candidate_b_goal_region_context_view") in {
        "goal_region_candidate_b_supported",
        "both_goal_region_candidates_supported",
    }
    shared = states.get("shared_goal_region_anchor_view") == "shared_goal_region_anchor_overlap_observed"
    obj_rel = states.get("candidate_pair_object_relation_context_view") == "object_relation_context_supported"
    if a_goal and b_goal and obj_rel:
        return "goal_region_both_candidates_supported_object_relation_supported"
    if a_goal and b_goal:
        return "goal_region_both_candidates_supported_object_relation_missing"
    if a_goal:
        return "goal_region_candidate_a_support_only"
    if b_goal:
        return "goal_region_candidate_b_support_only"
    if shared:
        return "shared_anchor_ambiguous_goal_region_support"
    if obj_rel:
        return "object_relation_context_available_nonterminal"
    return "insufficient_post_detector_evidence"


def request_state(pair_evidence_state: str) -> str:
    if pair_evidence_state == "goal_region_both_candidates_supported_object_relation_supported":
        return "coverage_completed_for_goal_region_and_object_relation"
    if pair_evidence_state in {
        "goal_region_both_candidates_supported_object_relation_missing",
        "goal_region_candidate_a_support_only",
        "goal_region_candidate_b_support_only",
        "object_relation_context_available_nonterminal",
    }:
        return "goal_region_completed_object_relation_gap_remains"
    if pair_evidence_state == "shared_anchor_ambiguous_goal_region_support":
        return "shared_goal_region_anchor_ambiguous"
    return "insufficient_evidence_after_observation"


def build_candidate_view_row(
    *,
    context: Mapping[str, Any],
    plan: Mapping[str, Any],
    frame: Mapping[str, Any],
    candidate_id: str,
    candidate_pair_role: str,
    paired_candidate_id: str,
    assoc_rows: Sequence[Mapping[str, Any]],
    source_candidate: Optional[Mapping[str, Any]],
) -> dict[str, Any]:
    associated = [row for row in assoc_rows if row.get("associated_to_candidate") is True]
    visible = [row for row in assoc_rows if row.get("projection_status") == "visible"]
    inside_box = [row for row in assoc_rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in assoc_rows if row.get("projected_pixel_inside_mask") is True]
    consistent = [row for row in associated if str(row.get("depth_check_status")) == "consistent"]
    mismatch = [row for row in assoc_rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    out_of_fov = [
        row
        for row in assoc_rows
        if str(row.get("projection_status")) == "out_of_fov" or str(row.get("depth_check_status")) == "out_of_fov"
    ]
    unavailable = [row for row in assoc_rows if str(row.get("depth_check_status")) == "unavailable"]
    state = candidate_view_state(assoc_rows)
    action_inputs = {
        "role": plan.get("observation_role"),
        "evidence_axis": plan.get("evidence_axis"),
        "selected_nonterminal_action": plan.get("selected_nonterminal_action"),
        "candidate_id": candidate_id,
        "candidate_pair_role": candidate_pair_role,
        "association_rows": len(assoc_rows),
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
        "row_type": "goal_region_object_relation_coverage_completion_detector_candidate_view",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "scene_id": frame.get("scene_id"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "coverage_completion_pair_id": context.get("coverage_completion_pair_id"),
        "role": plan.get("observation_role"),
        "view_role": plan.get("observation_role"),
        "evidence_axis": plan.get("evidence_axis"),
        "selected_nonterminal_action": plan.get("selected_nonterminal_action"),
        "candidate_id": candidate_id,
        "paired_candidate_id": paired_candidate_id,
        "candidate_pair_role": candidate_pair_role,
        "candidate_role_is_not_correctness": True,
        "source_candidate_goal_region_evidence_required": None
        if source_candidate is None
        else source_candidate.get("candidate_goal_region_evidence_required"),
        "source_candidate_object_relation_context_required": None
        if source_candidate is None
        else source_candidate.get("candidate_object_relation_context_required"),
        "target_candidate_id": plan.get("target_candidate_id") or frame.get("target_candidate_id"),
        "context_candidate_id": plan.get("context_candidate_id"),
        "decision_id": frame.get("decision_id"),
        "viewpoint_id": plan.get("viewpoint_id"),
        "association_rows": len(assoc_rows),
        "associated_rows": len(associated),
        "visible_rows": len(visible),
        "inside_box_rows": len(inside_box),
        "inside_mask_rows": len(inside_mask),
        "depth_consistent_rows": len(consistent),
        "depth_mismatch_rows": len(mismatch),
        "out_of_fov_rows": len(out_of_fov),
        "unavailable_rows": len(unavailable),
        "best_box_score_stats": number_stats(row.get("best_box_score") for row in assoc_rows),
        "depth_error_m_stats": number_stats(row.get("depth_error_m") for row in assoc_rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in assoc_rows),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in assoc_rows),
        "candidate_view_evidence_state": state,
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_role_row(
    *,
    context: Mapping[str, Any],
    plan: Mapping[str, Any],
    candidate_view_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    state = role_state(str(plan.get("observation_role")), candidate_view_rows)
    by_pair_role = {str(row.get("candidate_pair_role")): row for row in candidate_view_rows}
    a = by_pair_role.get("candidate_a", {})
    b = by_pair_role.get("candidate_b", {})
    action_inputs = {
        "role": plan.get("observation_role"),
        "evidence_axis": plan.get("evidence_axis"),
        "selected_nonterminal_action": plan.get("selected_nonterminal_action"),
        "candidate_a_associated_rows": a.get("associated_rows", 0),
        "candidate_b_associated_rows": b.get("associated_rows", 0),
        "candidate_a_evidence_state": a.get("candidate_view_evidence_state"),
        "candidate_b_evidence_state": b.get("candidate_view_evidence_state"),
        "role_evidence_state": state,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_detector_role",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "coverage_completion_pair_id": context.get("coverage_completion_pair_id"),
        "role": plan.get("observation_role"),
        "view_role": plan.get("observation_role"),
        "evidence_axis": plan.get("evidence_axis"),
        "selected_nonterminal_action": plan.get("selected_nonterminal_action"),
        "candidate_a_id": context.get("candidate_a_id"),
        "candidate_b_id": context.get("candidate_b_id"),
        "candidate_a_associated_rows": a.get("associated_rows", 0),
        "candidate_b_associated_rows": b.get("associated_rows", 0),
        "candidate_a_evidence_state": a.get("candidate_view_evidence_state"),
        "candidate_b_evidence_state": b.get("candidate_view_evidence_state"),
        "role_association_rows": sum(int(row.get("associated_rows") or 0) for row in candidate_view_rows),
        "role_visible_rows": sum(int(row.get("visible_rows") or 0) for row in candidate_view_rows),
        "role_evidence_state": state,
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_pair_row(context: Mapping[str, Any], role_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    state = pair_state(role_rows)
    role_states = {str(row.get("role")): row.get("role_evidence_state") for row in role_rows}
    action_inputs = {
        "coverage_completion_pair_id": context.get("coverage_completion_pair_id"),
        "role_evidence_states": role_states,
        "pair_evidence_state": state,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_detector_pair",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": context.get("scene_key"),
        "query": context.get("query"),
        "episode_key": context.get("episode_key"),
        "source_name": context.get("source_name"),
        "request_id": context.get("request_id"),
        "expanded_retrieval_request_id": context.get("request_id"),
        "coverage_completion_pair_id": context.get("coverage_completion_pair_id"),
        "candidate_a_id": context.get("candidate_a_id"),
        "candidate_b_id": context.get("candidate_b_id"),
        "role_evidence_states": role_states,
        "role_rows_with_any_candidate_association": sum(
            1
            for row in role_rows
            if int(row.get("candidate_a_associated_rows") or 0) > 0 or int(row.get("candidate_b_associated_rows") or 0) > 0
        ),
        "object_relation_context_role_state": role_states.get("candidate_pair_object_relation_context_view"),
        "shared_anchor_role_state": role_states.get("shared_goal_region_anchor_view"),
        "pair_evidence_state": state,
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_request_row(pair_row: Mapping[str, Any]) -> dict[str, Any]:
    state = request_state(str(pair_row.get("pair_evidence_state")))
    action_inputs = {
        "coverage_completion_pair_id": pair_row.get("coverage_completion_pair_id"),
        "pair_evidence_state": pair_row.get("pair_evidence_state"),
        "request_evidence_state": state,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_detector_request",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "scene_key": pair_row.get("scene_key"),
        "query": pair_row.get("query"),
        "episode_key": pair_row.get("episode_key"),
        "source_name": pair_row.get("source_name"),
        "request_id": pair_row.get("request_id"),
        "expanded_retrieval_request_id": pair_row.get("request_id"),
        "coverage_completion_pair_id": pair_row.get("coverage_completion_pair_id"),
        "candidate_a_id": pair_row.get("candidate_a_id"),
        "candidate_b_id": pair_row.get("candidate_b_id"),
        "pair_evidence_state": pair_row.get("pair_evidence_state"),
        "request_evidence_state": state,
        "recommended_next_nonterminal_action": "freeze_evaluation_only_join_after_evidence_rows"
        if state != "insufficient_evidence_after_observation"
        else "inspect_remaining_evidence_gap_before_join",
        "action_route_inputs": action_inputs,
        **common_flags(),
    }


def context_from_target_pair(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "scene_key": row.get("scene_key"),
        "query": row.get("query"),
        "episode_key": row.get("episode_key"),
        "source_name": row.get("source_name"),
        "request_id": row.get("request_id"),
        "coverage_completion_pair_id": row.get("coverage_completion_pair_id"),
        "candidate_a_id": row.get("candidate_a_id"),
        "candidate_b_id": row.get("candidate_b_id"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(resolve_path(args.contract))
    out_root = resolve_path(args.out_root)

    detector_summary = load_json(path_from_contract(contract, "detector_substrate_summary"))
    detector_diagnostic = load_json(path_from_contract(contract, "detector_substrate_diagnostic"))
    detector_frame_rows = load_jsonl(path_from_contract(contract, "detector_frame_summary"))
    association_rows = load_jsonl(path_from_contract(contract, "detector_associations"))
    target_pair_rows = load_jsonl(path_from_contract(contract, "target_pair_rows"))
    source_candidate_rows = load_jsonl(path_from_contract(contract, "source_candidate_rows"))
    frame_plan_rows = load_jsonl(path_from_contract(contract, "frame_plan_rows"))
    source_frame_rows = load_jsonl(path_from_contract(contract, "source_frame_rows"))

    source_frame_by_decision = {str(row.get("decision_id")): row for row in source_frame_rows}
    plan_by_viewpoint = {str(row.get("viewpoint_id")): row for row in frame_plan_rows}
    target_by_pair = {str(row.get("coverage_completion_pair_id")): row for row in target_pair_rows}
    candidate_by_pair_id = {
        (str(row.get("coverage_completion_pair_id")), str(row.get("candidate_id"))): row for row in source_candidate_rows
    }
    assoc_by_decision_candidate: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        assoc_by_decision_candidate[(str(row.get("decision_id")), str(row.get("candidate_id")))].append(row)

    frame_plan_pairs: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for frame in detector_frame_rows:
        source_frame = source_frame_by_decision.get(str(frame.get("decision_id")), {})
        viewpoint_id = source_frame.get("viewpoint_id") or frame.get("viewpoint_id")
        plan = plan_by_viewpoint.get(str(viewpoint_id), {})
        if not plan:
            raise RuntimeError(f"missing plan row for decision_id={frame.get('decision_id')}")
        target = target_by_pair.get(str(plan.get("coverage_completion_pair_id")), {})
        if not target:
            raise RuntimeError(f"missing target pair for pair_id={plan.get('coverage_completion_pair_id')}")
        frame_plan_pairs.append((frame, plan, target))

    candidate_view_rows: list[dict[str, Any]] = []
    role_groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for frame, plan, target in frame_plan_pairs:
        context = context_from_target_pair(target)
        candidate_ids = [str(value) for value in frame.get("selected_candidate_ids") or []]
        pair_roles = {
            str(target.get("candidate_a_id")): "candidate_a",
            str(target.get("candidate_b_id")): "candidate_b",
        }
        for candidate_id in candidate_ids:
            pair_role = pair_roles.get(candidate_id, "unknown_candidate_pair_role")
            paired = str(target.get("candidate_b_id") if pair_role == "candidate_a" else target.get("candidate_a_id"))
            assoc_rows = assoc_by_decision_candidate.get((str(frame.get("decision_id")), candidate_id), [])
            source_candidate = candidate_by_pair_id.get((str(context.get("coverage_completion_pair_id")), candidate_id))
            row = build_candidate_view_row(
                context=context,
                plan=plan,
                frame=frame,
                candidate_id=candidate_id,
                candidate_pair_role=pair_role,
                paired_candidate_id=paired,
                assoc_rows=assoc_rows,
                source_candidate=source_candidate,
            )
            candidate_view_rows.append(row)
            role_groups[(str(context.get("coverage_completion_pair_id")), str(plan.get("observation_role")))].append(row)

    role_rows: list[dict[str, Any]] = []
    pair_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for frame, plan, target in frame_plan_pairs:
        context = context_from_target_pair(target)
        key = (str(context.get("coverage_completion_pair_id")), str(plan.get("observation_role")))
        row = build_role_row(context=context, plan=plan, candidate_view_rows=role_groups[key])
        role_rows.append(row)
        pair_groups[str(context.get("coverage_completion_pair_id"))].append(row)

    pair_rows = [build_pair_row(context_from_target_pair(target_by_pair[pair_id]), rows) for pair_id, rows in sorted(pair_groups.items())]
    request_rows = [build_request_row(row) for row in pair_rows]
    audit_rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "row_type": "goal_region_object_relation_coverage_completion_detector_audit",
            "validation_stage": "post_detector_label_free_evidence_materialization",
            "scene_key": row.get("scene_key"),
            "query": row.get("query"),
            "episode_key": row.get("episode_key"),
            "source_name": row.get("source_name"),
            "request_id": row.get("request_id"),
            "coverage_completion_pair_id": row.get("coverage_completion_pair_id"),
            "pair_evidence_state": row.get("pair_evidence_state"),
            "request_evidence_state": request_state(str(row.get("pair_evidence_state"))),
            "terminal_utility_allowed": False,
            "evaluation_join_allowed_after_evidence_freeze": True,
            **common_flags(),
        }
        for row in pair_rows
    ]

    all_output_rows: list[Mapping[str, Any]] = []
    for rows in [candidate_view_rows, role_rows, pair_rows, request_rows, audit_rows]:
        all_output_rows.extend(rows)
    forbidden = scan_forbidden_action_inputs(all_output_rows)

    min_gate = contract["minimum_evidence_gate"]
    role_rows_with_assoc = sum(
        1 for row in role_rows if int(row.get("candidate_a_associated_rows") or 0) > 0 or int(row.get("candidate_b_associated_rows") or 0) > 0
    )
    object_relation_assoc = sum(
        1
        for row in role_rows
        if row.get("role") == "candidate_pair_object_relation_context_view"
        and (int(row.get("candidate_a_associated_rows") or 0) > 0 or int(row.get("candidate_b_associated_rows") or 0) > 0)
    )
    pair_rows_with_assoc = sum(1 for row in pair_rows if int(row.get("role_rows_with_any_candidate_association") or 0) > 0)
    associated_scene_count = len({row.get("scene_key") for row in role_rows if row.get("role_association_rows", 0) > 0})
    associated_query_count = len({row.get("query") for row in role_rows if row.get("role_association_rows", 0) > 0})

    gate = {
        "source_detector_substrate_gate_passed": bool(
            detector_summary.get("coverage_completion_gate", {}).get("passes_coverage_completion_detector_substrate_gate")
        ),
        "candidate_view_rows_match": len(candidate_view_rows) == int(min_gate["expected_candidate_view_rows"]),
        "role_rows_match": len(role_rows) == int(min_gate["expected_role_rows"]),
        "pair_rows_match": len(pair_rows) == int(min_gate["expected_pair_rows"]),
        "request_rows_match": len(request_rows) == int(min_gate["expected_request_rows"]),
        "audit_rows_match": len(audit_rows) == int(min_gate["expected_audit_rows"]),
        "pair_rows_with_any_candidate_association_pass": pair_rows_with_assoc >= int(
            min_gate["minimum_pair_rows_with_any_candidate_association"]
        ),
        "role_rows_with_candidate_association_pass": role_rows_with_assoc >= int(
            min_gate["minimum_role_rows_with_candidate_association"]
        ),
        "object_relation_context_rows_with_association_pass": object_relation_assoc >= int(
            min_gate["minimum_object_relation_context_rows_with_association"]
        ),
        "associated_scene_count_pass": associated_scene_count >= int(min_gate["minimum_associated_scene_count"]),
        "associated_query_count_pass": associated_query_count >= int(min_gate["minimum_associated_query_count"]),
        "forbidden_action_keys_absent": not forbidden,
        "no_terminal_commit_pass": not any(row.get("terminal_commit") for row in all_output_rows),
        "no_candidate_commit_pass": not any(row.get("candidate_commit") for row in all_output_rows),
        "no_candidate_rejection_pass": not any(row.get("candidate_rejection") for row in all_output_rows),
        "no_gt_action_pass": not any(row.get("uses_gt_for_action") for row in all_output_rows),
        "paper_claim_blocked_pass": not any(row.get("paper_claim_allowed") for row in all_output_rows),
    }
    gate["goal_region_object_relation_coverage_completion_detector_evidence_gate_passed"] = all(gate.values())

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed" if gate["goal_region_object_relation_coverage_completion_detector_evidence_gate_passed"] else "failed",
        "contract": args.contract,
        "source_detector_substrate": str(path_from_contract(contract, "detector_substrate_summary")),
        "candidate_view_rows": len(candidate_view_rows),
        "role_rows": len(role_rows),
        "pair_rows": len(pair_rows),
        "request_rows": len(request_rows),
        "audit_rows": len(audit_rows),
        "candidate_view_evidence_state_counts": compact_counter(
            row.get("candidate_view_evidence_state") for row in candidate_view_rows
        ),
        "role_evidence_state_counts": compact_counter(row.get("role_evidence_state") for row in role_rows),
        "pair_evidence_state_counts": compact_counter(row.get("pair_evidence_state") for row in pair_rows),
        "request_evidence_state_counts": compact_counter(row.get("request_evidence_state") for row in request_rows),
        "role_rows_with_any_candidate_association": role_rows_with_assoc,
        "object_relation_context_rows_with_association": object_relation_assoc,
        "pair_rows_with_any_candidate_association": pair_rows_with_assoc,
        "associated_scene_count": associated_scene_count,
        "associated_query_count": associated_query_count,
        "source_detector_box_rate": detector_summary.get("detector_box_rate"),
        "source_sam2_mask_rate": detector_summary.get("sam2_mask_rate"),
        "source_candidate_association_rate": detector_summary.get("candidate_association_rate"),
        "source_rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
        "source_associated_candidate_heading_count": detector_summary.get("associated_candidate_heading_count"),
        "source_failure_taxonomy": detector_diagnostic.get("failure_taxonomy", []),
        "gate": gate,
        "terminal_commit_rows": sum(1 for row in all_output_rows if row.get("terminal_commit")),
        "candidate_commit_rows": sum(1 for row in all_output_rows if row.get("candidate_commit")),
        "candidate_rejection_rows": sum(1 for row in all_output_rows if row.get("candidate_rejection")),
        "action_evidence_forbidden_keys_found": forbidden,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "next_task": "freeze_goal_region_object_relation_coverage_completion_evaluation_only_join_contract",
    }

    write_jsonl(out_root / OUTPUT_FILES["candidate_view_rows"], candidate_view_rows)
    write_jsonl(out_root / OUTPUT_FILES["role_rows"], role_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)

    print(json.dumps(summary, indent=2, sort_keys=True))
    if not gate["goal_region_object_relation_coverage_completion_detector_evidence_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
