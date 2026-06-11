import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_detector_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_detector_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_detector_evidence_v1"

OUTPUT_FILES = {
    "candidate_role_rows": "rival_contradiction_region_contamination_detector_candidate_role_rows.jsonl",
    "role_rows": "rival_contradiction_region_contamination_detector_role_rows.jsonl",
    "pair_rows": "rival_contradiction_region_contamination_detector_pair_rows.jsonl",
    "audit_rows": "rival_contradiction_region_contamination_detector_audit_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_detector_evidence_summary.json",
}

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "candidate_pair_label_pattern_for_evaluation_only",
    "success_label",
    "wrong_goal_visit_proxy",
    "success_commit_proxy",
    "terminal_commit_proxy",
    "wasted_path_proxy_m",
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "oracle_shortest_path",
    "ground_truth",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "post_hoc_label_tuned_threshold",
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


def path_from_contract(contract: Mapping[str, Any], key: str) -> Path:
    path = Path(str((contract.get("source") or {}).get(key) or ""))
    if not path:
        raise KeyError(f"missing source path: {key}")
    if path.exists():
        return path
    if str(path).startswith("local_dataset/runs/"):
        runs_path = Path("/runs") / str(path).removeprefix("local_dataset/runs/")
        if runs_path.exists():
            return runs_path
    workspace_path = Path("/workspace") / path
    if workspace_path.exists():
        return workspace_path
    return path


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
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def role_sort_key(role: str, required_roles: Sequence[str]) -> int:
    try:
        return required_roles.index(role)
    except ValueError:
        return len(required_roles)


def association_group_key(row: Mapping[str, Any]) -> Tuple[str, str]:
    return str(row.get("role") or row.get("view_role") or ""), str(row.get("candidate_id") or "")


def role_key(row: Mapping[str, Any]) -> str:
    return str(row.get("role") or row.get("view_role") or "")


def candidate_evidence_state(rows: Sequence[Mapping[str, Any]]) -> str:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    if associated and any(str(row.get("depth_check_status")) == "consistent" for row in associated):
        return "associated_depth_consistent"
    if associated:
        return "associated_depth_mixed"
    if any(row.get("projected_pixel_inside_box") is True or row.get("projected_pixel_inside_mask") is True for row in rows):
        return "visible_without_candidate_association"
    return "not_observed_in_role"


def role_evidence_state(
    role: str,
    candidate_rows: Sequence[Mapping[str, Any]],
    supported_id: str,
    rival_id: str,
) -> str:
    by_candidate = {str(row.get("candidate_id")): row for row in candidate_rows}
    supported_associated = int(by_candidate.get(supported_id, {}).get("associated_rows") or 0) > 0
    rival_associated = int(by_candidate.get(rival_id, {}).get("associated_rows") or 0) > 0
    if supported_associated and rival_associated:
        return "supported_and_rival_both_associated"
    if supported_associated:
        return "supported_only_associated"
    if rival_associated:
        return "rival_only_associated"
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


def candidate_role_row(
    *,
    role: str,
    candidate_id: str,
    candidate_role: str,
    rows: Sequence[Mapping[str, Any]],
    frame_row: Optional[Mapping[str, Any]],
    target_pair: Mapping[str, Any],
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
    action_inputs = {
        "role": role,
        "candidate_id": candidate_id,
        "candidate_role": candidate_role,
        "association_rows": len(rows),
        "associated_rows": len(associated),
        "inside_mask_rows": len(inside_mask),
        "depth_consistent_rows": len(consistent),
        "depth_mismatch_rows": len(mismatch),
        "out_of_fov_rows": len(out_of_fov),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_candidate_role",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "request_id": str(target_pair.get("request_id") or exemplar.get("expanded_retrieval_request_id") or ""),
        "expanded_retrieval_request_id": str(target_pair.get("request_id") or exemplar.get("expanded_retrieval_request_id") or ""),
        "scene_key": str(target_pair.get("scene_key") or exemplar.get("scene_key") or ""),
        "scene_id": exemplar.get("scene_id"),
        "query": str(target_pair.get("query") or exemplar.get("query") or ""),
        "episode_key": str(target_pair.get("episode_key") or exemplar.get("episode_key") or ""),
        "source_name": str(target_pair.get("source_name") or exemplar.get("source_name") or ""),
        "role": role,
        "rival_observation_role": role,
        "candidate_id": candidate_id,
        "candidate_role": candidate_role,
        "provisionally_supported_candidate_id": target_pair.get("provisionally_supported_candidate_id"),
        "rival_candidate_id": target_pair.get("rival_candidate_id"),
        "target_candidate_id": exemplar.get("target_candidate_id"),
        "role_target_candidate_id": (frame_row or {}).get("target_candidate_id") if frame_row else exemplar.get("target_candidate_id"),
        "rival_evidence_axis": (frame_row or {}).get("rival_evidence_axis") or exemplar.get("rival_evidence_axis"),
        "heading_rows": len(rows),
        "association_rows": len(rows),
        "associated_rows": len(associated),
        "visible_rows": len(visible),
        "inside_box_rows": len(inside_box),
        "inside_mask_rows": len(inside_mask),
        "depth_consistent_rows": len(consistent),
        "depth_mismatch_rows": len(mismatch),
        "out_of_fov_rows": len(out_of_fov),
        "projection_status_counts": compact_counter(row.get("projection_status") for row in rows),
        "depth_check_status_counts": compact_counter(row.get("depth_check_status") for row in rows),
        "projection_anchor_selected_offset_profile": sorted(
            [value for value in (safe_float(row.get("projection_anchor_height_offset_m")) for row in rows) if value is not None]
        ),
        "best_box_score_stats": number_stats(row.get("best_box_score") for row in rows),
        "depth_error_stats_m": number_stats(row.get("depth_error_m") for row in rows),
        "associated_depth_error_stats_m": number_stats(row.get("depth_error_m") for row in associated),
        "detector_box_count": (frame_row or {}).get("detector_box_count"),
        "sam2_mask_count": (frame_row or {}).get("sam2_mask_count"),
        "candidate_evidence_state": candidate_evidence_state(rows),
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def role_row(
    *,
    role: str,
    rows: Sequence[Mapping[str, Any]],
    frame_row: Mapping[str, Any],
    target_pair: Mapping[str, Any],
    supported_id: str,
    rival_id: str,
) -> Dict[str, Any]:
    by_candidate = {str(row.get("candidate_id")): row for row in rows}
    supported = by_candidate.get(supported_id, {})
    rival = by_candidate.get(rival_id, {})
    state = role_evidence_state(role, rows, supported_id, rival_id)
    dual = state == "supported_and_rival_both_associated"
    action_inputs = {
        "role": role,
        "supported_associated_rows": supported.get("associated_rows", 0),
        "rival_associated_rows": rival.get("associated_rows", 0),
        "role_evidence_state": state,
        "dual_candidate_association": dual,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_role",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "request_id": target_pair.get("request_id"),
        "expanded_retrieval_request_id": target_pair.get("request_id"),
        "scene_key": target_pair.get("scene_key"),
        "scene_id": frame_row.get("scene_id"),
        "query": target_pair.get("query"),
        "episode_key": target_pair.get("episode_key"),
        "source_name": target_pair.get("source_name"),
        "role": role,
        "rival_evidence_axis": frame_row.get("rival_evidence_axis"),
        "provisionally_supported_candidate_id": supported_id,
        "rival_candidate_id": rival_id,
        "selected_candidate_ids": frame_row.get("selected_candidate_ids"),
        "rendered_heading_count": frame_row.get("rendered_heading_count"),
        "detector_box_count": frame_row.get("detector_box_count"),
        "sam2_mask_count": frame_row.get("sam2_mask_count"),
        "supported_associated_rows": supported.get("associated_rows", 0),
        "rival_associated_rows": rival.get("associated_rows", 0),
        "supported_depth_consistent_rows": supported.get("depth_consistent_rows", 0),
        "rival_depth_consistent_rows": rival.get("depth_consistent_rows", 0),
        "candidate_evidence_states": {str(row.get("candidate_role")): row.get("candidate_evidence_state") for row in rows},
        "role_evidence_state": state,
        "dual_candidate_association": dual,
        "single_candidate_isolation": state in {"supported_only_associated", "rival_only_associated"},
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def pair_row(
    *,
    role_rows: Sequence[Mapping[str, Any]],
    target_pair: Mapping[str, Any],
) -> Dict[str, Any]:
    dual_roles = [row for row in role_rows if row.get("dual_candidate_association") is True]
    isolation_roles = [row for row in role_rows if row.get("single_candidate_isolation") is True]
    role_state_counts = compact_counter(row.get("role_evidence_state") for row in role_rows)
    if dual_roles:
        state = "rival_region_contamination_or_same_category_overlap_observed"
    elif isolation_roles:
        state = "rival_contradiction_or_isolation_observed"
    else:
        state = "insufficient_post_detector_evidence"
    supported_own = next((row for row in role_rows if row.get("role") == "supported_candidate_own_view"), {})
    rival_own = next((row for row in role_rows if row.get("role") == "rival_candidate_own_view"), {})
    action_inputs = {
        "role_support_matrix": {
            str(row.get("role")): {
                "state": row.get("role_evidence_state"),
                "supported_associated_rows": row.get("supported_associated_rows"),
                "rival_associated_rows": row.get("rival_associated_rows"),
            }
            for row in role_rows
        },
        "dual_candidate_association_role_count": len(dual_roles),
        "single_candidate_isolation_role_count": len(isolation_roles),
        "pair_evidence_state": state,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_pair",
        "validation_stage": "post_detector_label_free_evidence_materialization",
        "request_id": target_pair.get("request_id"),
        "expanded_retrieval_request_id": target_pair.get("request_id"),
        "scene_key": target_pair.get("scene_key"),
        "query": target_pair.get("query"),
        "episode_key": target_pair.get("episode_key"),
        "source_name": target_pair.get("source_name"),
        "provisionally_supported_candidate_id": target_pair.get("provisionally_supported_candidate_id"),
        "rival_candidate_id": target_pair.get("rival_candidate_id"),
        "candidate_a_id": target_pair.get("provisionally_supported_candidate_id"),
        "candidate_b_id": target_pair.get("rival_candidate_id"),
        "role_evidence_state_counts": role_state_counts,
        "dual_candidate_association_role_count": len(dual_roles),
        "single_candidate_isolation_role_count": len(isolation_roles),
        "supported_own_view_state": supported_own.get("role_evidence_state"),
        "rival_own_view_state": rival_own.get("role_evidence_state"),
        "pair_evidence_state": state,
        "contamination_or_contradiction_evidence_available": state != "insufficient_post_detector_evidence",
        "terminal_selector_allowed_from_this_evidence": False,
        "evaluation_join_required": True,
        "action_evidence_inputs": action_inputs,
        **common_flags(),
    }


def build_rows(
    contract: Mapping[str, Any],
    associations: Sequence[Mapping[str, Any]],
    frames: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    target_pair = contract["target_pair"]
    supported_id = str(target_pair["provisionally_supported_candidate_id"])
    rival_id = str(target_pair["rival_candidate_id"])
    candidate_roles = dict(target_pair["candidate_roles"])
    roles = list(target_pair["required_observation_roles"])

    assoc_by_role_candidate: Dict[Tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in associations:
        assoc_by_role_candidate[association_group_key(row)].append(row)
    frame_by_role = {role_key(row): row for row in frames}

    candidate_rows: List[Dict[str, Any]] = []
    for role in roles:
        frame = frame_by_role.get(role)
        for candidate_id in (supported_id, rival_id):
            candidate_rows.append(
                candidate_role_row(
                    role=role,
                    candidate_id=candidate_id,
                    candidate_role=str(candidate_roles[candidate_id]),
                    rows=assoc_by_role_candidate.get((role, candidate_id), []),
                    frame_row=frame,
                    target_pair=target_pair,
                )
            )

    rows_by_role: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        rows_by_role[str(row["role"])].append(row)

    role_rows = [
        role_row(
            role=role,
            rows=sorted(rows_by_role.get(role, []), key=lambda row: str(row.get("candidate_id"))),
            frame_row=frame_by_role[role],
            target_pair=target_pair,
            supported_id=supported_id,
            rival_id=rival_id,
        )
        for role in roles
    ]
    pair_rows = [pair_row(role_rows=role_rows, target_pair=target_pair)]
    audit_rows = [
        {
            "schema_version": SCHEMA_VERSION,
            "row_type": "rival_contradiction_region_contamination_detector_audit",
            "validation_stage": "post_detector_label_free_evidence_materialization",
            "request_id": target_pair.get("request_id"),
            "scene_key": target_pair.get("scene_key"),
            "query": target_pair.get("query"),
            "episode_key": target_pair.get("episode_key"),
            "source_name": target_pair.get("source_name"),
            "audit_status": "evaluation_join_required_before_utility_claim",
            "detector_evidence_rows_frozen": True,
            "action_evidence_forbidden_keys_found": scan_forbidden_action_inputs(candidate_rows + role_rows + pair_rows),
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
    ]
    return candidate_rows, role_rows, pair_rows, audit_rows


def summarize(
    *,
    contract: Mapping[str, Any],
    detector_summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    role_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    expected = contract["minimum_evidence_gate"]
    forbidden = scan_forbidden_action_inputs(candidate_rows + role_rows + pair_rows + audit_rows)
    dual_roles = [row for row in role_rows if row.get("dual_candidate_association") is True]
    associated_candidates = {
        str(row.get("candidate_id"))
        for row in candidate_rows
        if int(row.get("associated_rows") or 0) > 0
    }
    terminal_rows = sum(1 for row in candidate_rows + role_rows + pair_rows + audit_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in candidate_rows + role_rows + pair_rows + audit_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in candidate_rows + role_rows + pair_rows + audit_rows if row.get("candidate_rejection") is True)
    gate = {
        "source_detector_substrate_gate_passed": bool((detector_summary.get("gate") or {}).get("passes_detector_substrate_gate")),
        "candidate_role_rows_match": len(candidate_rows) == int(expected["expected_candidate_role_rows"]),
        "role_rows_match": len(role_rows) == int(expected["expected_role_rows"]),
        "pair_rows_match": len(pair_rows) == int(expected["expected_pair_rows"]),
        "required_role_count_pass": len({row.get("role") for row in role_rows}) == int(expected["required_role_count"]),
        "minimum_dual_candidate_association_role_count_pass": len(dual_roles) >= int(expected["minimum_dual_candidate_association_role_count"]),
        "minimum_candidate_with_association_count_pass": len(associated_candidates) >= int(expected["minimum_candidate_with_association_count"]),
        "action_evidence_forbidden_key_count_pass": len(forbidden) <= int(expected["action_evidence_forbidden_key_count_maximum"]),
        "terminal_commit_rows_pass": terminal_rows <= int(expected["terminal_commit_rows_maximum"]),
        "candidate_commit_rows_pass": candidate_commit_rows <= int(expected["candidate_commit_rows_maximum"]),
        "candidate_rejection_rows_pass": candidate_rejection_rows <= int(expected["candidate_rejection_rows_maximum"]),
        "uses_gt_for_action_pass": not any(row.get("uses_gt_for_action") is True for row in candidate_rows + role_rows + pair_rows + audit_rows),
        "paper_claim_blocked": not any(row.get("paper_claim_allowed") is True for row in candidate_rows + role_rows + pair_rows + audit_rows),
    }
    gate["detector_evidence_materializer_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "source_detector_summary": "local_dataset/runs/h001_rival_contradiction_region_contamination_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json",
        "candidate_role_rows": len(candidate_rows),
        "role_rows": len(role_rows),
        "pair_rows": len(pair_rows),
        "audit_rows": len(audit_rows),
        "candidate_evidence_state_counts": compact_counter(row.get("candidate_evidence_state") for row in candidate_rows),
        "role_evidence_state_counts": compact_counter(row.get("role_evidence_state") for row in role_rows),
        "pair_evidence_state_counts": compact_counter(row.get("pair_evidence_state") for row in pair_rows),
        "dual_candidate_association_role_count": len(dual_roles),
        "single_candidate_isolation_role_count": sum(1 for row in role_rows if row.get("single_candidate_isolation") is True),
        "associated_candidate_ids": sorted(associated_candidates),
        "action_evidence_forbidden_keys_found": forbidden,
        "terminal_commit_rows": terminal_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "next_task": "freeze_rival_contradiction_region_contamination_detector_evaluation_join_contract",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--detector-root", default=None)
    args = parser.parse_args()

    contract = load_json(Path(args.contract))
    source = contract.get("source") or {}
    detector_root = Path(args.detector_root) if args.detector_root else None
    if detector_root:
        detector_summary_path = detector_root / "expanded_retrieval_detector_substrate_summary.json"
        associations_path = detector_root / "expanded_retrieval_detector_associations.jsonl"
        frames_path = detector_root / "expanded_retrieval_detector_frame_summary.jsonl"
    else:
        detector_summary_path = path_from_contract(contract, "detector_substrate_summary")
        associations_path = path_from_contract(contract, "detector_associations")
        frames_path = path_from_contract(contract, "detector_frame_summary")

    detector_summary = load_json(detector_summary_path)
    if not (detector_summary.get("gate") or {}).get("passes_detector_substrate_gate"):
        raise RuntimeError("source detector substrate gate did not pass")

    associations = load_jsonl(associations_path)
    frames = load_jsonl(frames_path)
    candidate_rows, role_rows, pair_rows, audit_rows = build_rows(contract, associations, frames)
    summary = summarize(
        contract=contract,
        detector_summary=detector_summary,
        candidate_rows=candidate_rows,
        role_rows=role_rows,
        pair_rows=pair_rows,
        audit_rows=audit_rows,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / OUTPUT_FILES["candidate_role_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["role_rows"], role_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if not summary["gate"]["detector_evidence_materializer_gate_passed"]:
        raise RuntimeError("detector evidence materializer gate failed")


if __name__ == "__main__":
    main()
