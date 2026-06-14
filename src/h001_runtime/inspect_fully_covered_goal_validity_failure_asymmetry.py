import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


SCHEMA_VERSION = "h001.fully_covered_goal_validity_failure_asymmetry_inspection.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_fully_covered_goal_validity_failure_asymmetry_inspection_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_fully_covered_goal_validity_failure_asymmetry_inspection_v1"

OUTPUT_FILES = {
    "candidate_asymmetry_rows": "fully_covered_goal_validity_failure_candidate_asymmetry_rows.jsonl",
    "pair_inspection_rows": "fully_covered_goal_validity_failure_pair_inspection_rows.jsonl",
    "alternative_audit_rows": "fully_covered_goal_validity_failure_alternative_audit_rows.jsonl",
    "summary": "fully_covered_goal_validity_failure_asymmetry_inspection_summary.json",
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

GOAL_REGION_ROLES = {
    "candidate_a": "candidate_a_goal_region_context_view",
    "candidate_b": "candidate_b_goal_region_context_view",
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


def compact_counter(values: Iterable[Any]) -> dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result


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


def common_flags(uses_gt_for_analysis: bool = False) -> dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": uses_gt_for_analysis,
        "paper_claim_allowed": False,
    }


def view_role(row: Mapping[str, Any]) -> str:
    return str(row.get("role") or row.get("view_role") or "")


def candidate_role(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_pair_role") or "")


def mean_best_box_score(rows: Sequence[Mapping[str, Any]]) -> Optional[float]:
    values: list[float] = []
    for row in rows:
        stats = row.get("best_box_score_stats") or {}
        value = safe_float(stats.get("mean"))
        if value is not None:
            values.append(value)
    if not values:
        return None
    return sum(values) / len(values)


def role_state_by_role(rows: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    return {view_role(row): str(row.get("candidate_view_evidence_state") or "") for row in rows}


def candidate_label(row: Mapping[str, Any]) -> str:
    if row.get("candidate_correctness_label_for_evaluation_only") is True:
        return "correct"
    if row.get("candidate_wrong_label_for_evaluation_only") is True:
        return "wrong"
    return "unknown"


def build_candidate_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    candidate_view_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in sorted(candidate_rows, key=lambda row: str(row.get("candidate_pair_role"))):
        cid = str(candidate.get("candidate_id"))
        role = candidate_role(candidate)
        views = [row for row in candidate_view_rows if str(row.get("candidate_id")) == cid]
        states = role_state_by_role(views)
        associated_roles = [
            role_name for role_name, state in states.items() if state == "associated_depth_consistent"
        ]
        unsupported_visible_roles = [
            role_name for role_name, state in states.items() if state == "visible_without_candidate_association"
        ]
        own_role = GOAL_REGION_ROLES.get(role)
        peer_role = next((value for key, value in GOAL_REGION_ROLES.items() if key != role), None)
        all_role_associated = len(associated_roles) == 4 and len(states) == 4
        peer_goal_region_associated = peer_role is not None and states.get(peer_role) == "associated_depth_consistent"
        diagnostic_state = (
            "candidate_conditioned_all_role_support"
            if all_role_associated
            else "candidate_conditioned_support_incomplete"
        )
        if unsupported_visible_roles:
            blocker = "visible_without_depth_association_in_goal_region_context"
        elif not all_role_associated:
            blocker = "missing_candidate_conditioned_role_support"
        else:
            blocker = "none"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "fully_covered_goal_validity_failure_candidate_asymmetry",
                "validation_stage": "candidate_conditioned_asymmetry_inspection_after_materialization",
                "scene_key": candidate.get("scene_key"),
                "query": candidate.get("query"),
                "episode_key": candidate.get("episode_key"),
                "source_name": candidate.get("source_name"),
                "request_id": candidate.get("request_id"),
                "coverage_completion_pair_id": candidate.get("coverage_completion_pair_id"),
                "candidate_id": cid,
                "candidate_pair_role": role,
                "candidate_view_rows": len(views),
                "associated_role_count": len(associated_roles),
                "associated_roles": associated_roles,
                "unsupported_visible_role_count": len(unsupported_visible_roles),
                "unsupported_visible_roles": unsupported_visible_roles,
                "own_goal_region_role": own_role,
                "own_goal_region_state": states.get(own_role or ""),
                "peer_goal_region_role": peer_role,
                "peer_goal_region_state": states.get(peer_role or ""),
                "peer_goal_region_associated": peer_goal_region_associated,
                "object_relation_state": states.get("candidate_pair_object_relation_context_view"),
                "shared_goal_region_anchor_state": states.get("shared_goal_region_anchor_view"),
                "all_role_associated": all_role_associated,
                "total_associated_rows": sum(int(row.get("associated_rows") or 0) for row in views),
                "total_depth_consistent_rows": sum(int(row.get("depth_consistent_rows") or 0) for row in views),
                "total_depth_mismatch_rows": sum(int(row.get("depth_mismatch_rows") or 0) for row in views),
                "total_inside_mask_rows": sum(int(row.get("inside_mask_rows") or 0) for row in views),
                "mean_best_box_score": mean_best_box_score(views),
                "candidate_conditioned_diagnostic_state": diagnostic_state,
                "candidate_conditioned_blocker": blocker,
                "candidate_label_for_audit_only": candidate_label(candidate),
                "evaluation_only_label_is_action_forbidden": True,
                "terminal_selector_allowed_from_this_inspection": False,
                **common_flags(uses_gt_for_analysis=True),
            }
        )
    return rows


def best_by_metric(rows: Sequence[Mapping[str, Any]], field: str) -> tuple[Optional[str], str]:
    values: list[tuple[str, float]] = []
    for row in rows:
        value = safe_float(row.get(field))
        if value is not None:
            values.append((str(row.get("candidate_id")), value))
    if not values:
        return None, "no_value"
    max_value = max(value for _, value in values)
    winners = [cid for cid, value in values if value == max_value]
    if len(winners) != 1:
        return None, "tie"
    return winners[0], "unique"


def audit_label(rows: Sequence[Mapping[str, Any]], candidate_id: Optional[str]) -> str:
    if not candidate_id:
        return "none"
    for row in rows:
        if str(row.get("candidate_id")) == candidate_id:
            return str(row.get("candidate_label_for_audit_only") or "unknown")
    return "missing"


def alternative_row(
    *,
    name: str,
    decision: str,
    selected_candidate_id: Optional[str],
    selected_label: str,
    reason: str,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "row_type": "fully_covered_goal_validity_failure_alternative_audit",
        "validation_stage": "candidate_conditioned_asymmetry_inspection_after_materialization",
        "alternative_name": name,
        "decision": decision,
        "selected_candidate_id_for_audit_only": selected_candidate_id,
        "selected_candidate_label_for_audit_only": selected_label,
        "evaluation_only_label_is_action_forbidden": True,
        "reason": reason,
        "terminal_selector_allowed_from_this_inspection": False,
        **common_flags(uses_gt_for_analysis=True),
    }
    if extra:
        payload.update(dict(extra))
    return payload


def build_alternative_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    all_role_candidates = [
        str(row.get("candidate_id")) for row in candidate_rows if row.get("all_role_associated") is True
    ]
    associated_best, associated_status = best_by_metric(candidate_rows, "total_associated_rows")
    depth_best, depth_status = best_by_metric(candidate_rows, "total_depth_consistent_rows")
    score_best, score_status = best_by_metric(candidate_rows, "mean_best_box_score")
    all_role_selected = all_role_candidates[0] if len(all_role_candidates) == 1 else None
    return [
        alternative_row(
            name="binary_coverage_completion_as_terminal_support",
            decision="rejected_as_terminal_rule",
            selected_candidate_id=None,
            selected_label="none",
            reason="binary fully covered state does not distinguish candidates inside the pair",
        ),
        alternative_row(
            name="association_count_best",
            decision="rejected_as_terminal_rule",
            selected_candidate_id=associated_best,
            selected_label=audit_label(candidate_rows, associated_best),
            reason="association-count rule is tied or non-discriminative on this row",
            extra={"selector_status": associated_status},
        ),
        alternative_row(
            name="depth_consistency_count_best",
            decision="rejected_as_terminal_rule",
            selected_candidate_id=depth_best,
            selected_label=audit_label(candidate_rows, depth_best),
            reason="depth-consistency count favors the evaluation-wrong candidate on this row",
            extra={"selector_status": depth_status},
        ),
        alternative_row(
            name="detector_score_mean_best",
            decision="rejected_as_terminal_rule",
            selected_candidate_id=score_best,
            selected_label=audit_label(candidate_rows, score_best),
            reason="detector-score mean is not a reliable goal-validity selector on this row",
            extra={"selector_status": score_status},
        ),
        alternative_row(
            name="all_role_association_best",
            decision="diagnostic_only_promising_blocker_not_terminal_rule",
            selected_candidate_id=all_role_selected,
            selected_label=audit_label(candidate_rows, all_role_selected),
            reason="exactly one candidate has all-role association, but one row is insufficient for terminal-rule promotion",
            extra={"selector_status": "unique" if all_role_selected else "not_unique"},
        ),
        alternative_row(
            name="defer_all_fully_covered_pairs",
            decision="safe_but_inert",
            selected_candidate_id=None,
            selected_label="none",
            reason="defer-all avoids unsafe commit but does not explain which evidence term should drive active utility",
        ),
    ]


def build_pair_row(
    target_rows: Sequence[Mapping[str, Any]],
    candidate_asymmetry_rows: Sequence[Mapping[str, Any]],
    alternative_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(target_rows) != 1:
        raise ValueError(f"expected one target pair row, got {len(target_rows)}")
    target = target_rows[0]
    all_role_candidates = [
        row for row in candidate_asymmetry_rows if row.get("all_role_associated") is True
    ]
    incomplete_candidates = [
        row for row in candidate_asymmetry_rows if row.get("all_role_associated") is not True
    ]
    unsafe_alternatives = [
        row
        for row in alternative_rows
        if row.get("decision") == "rejected_as_terminal_rule"
        and row.get("selected_candidate_label_for_audit_only") in {"wrong", "none"}
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "fully_covered_goal_validity_failure_pair_inspection",
        "validation_stage": "candidate_conditioned_asymmetry_inspection_after_materialization",
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "episode_key": target.get("episode_key"),
        "source_name": target.get("source_name"),
        "request_id": target.get("request_id"),
        "coverage_completion_pair_id": target.get("coverage_completion_pair_id"),
        "pair_evidence_state": target.get("pair_evidence_state"),
        "binary_coverage_completion_too_coarse": True,
        "candidate_conditioned_asymmetry_present": bool(all_role_candidates and incomplete_candidates),
        "all_role_associated_candidate_ids": [row.get("candidate_id") for row in all_role_candidates],
        "candidate_conditioned_incomplete_candidate_ids": [row.get("candidate_id") for row in incomplete_candidates],
        "unsafe_simple_alternative_count_for_audit_only": len(unsafe_alternatives),
        "unsafe_simple_alternatives_for_audit_only": [row.get("alternative_name") for row in unsafe_alternatives],
        "candidate_conditioned_blocker_ready_for_this_row": bool(all_role_candidates and incomplete_candidates),
        "terminal_arbitration_rule_ready": False,
        "primary_blocker": "fixed_rule_needs_fully_covered_contrast_validation",
        "recommended_next_task": "freeze_fully_covered_candidate_conditioned_contrast_contract",
        "terminal_selector_allowed_from_this_inspection": False,
        **common_flags(uses_gt_for_analysis=True),
    }


def materialize(contract_path: Path, out_root: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    target_rows = load_jsonl(path_from_contract(contract, "target_pair_rows"))
    candidate_rows = load_jsonl(path_from_contract(contract, "candidate_rows"))
    candidate_view_rows = load_jsonl(path_from_contract(contract, "candidate_view_rows"))
    role_rows = load_jsonl(path_from_contract(contract, "role_rows"))
    audit_rows = load_jsonl(path_from_contract(contract, "evaluation_audit_rows"))

    candidate_asymmetry_rows = build_candidate_rows(candidate_rows, candidate_view_rows)
    alternative_rows = build_alternative_rows(candidate_asymmetry_rows)
    pair_rows = [build_pair_row(target_rows, candidate_asymmetry_rows, alternative_rows)]
    action_rows = candidate_asymmetry_rows + pair_rows + alternative_rows
    forbidden_keys = scan_forbidden_action_inputs(action_rows)
    terminal_commit_rows = sum(1 for row in action_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in action_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in action_rows if row.get("candidate_rejection") is True)
    uses_gt_for_action_true_rows = sum(1 for row in action_rows if row.get("uses_gt_for_action") is True)
    paper_claim_allowed_true_rows = sum(1 for row in action_rows if row.get("paper_claim_allowed") is True)

    expected = contract.get("expected_outputs") or {}
    all_role_support_rows = [
        row for row in candidate_asymmetry_rows if row.get("all_role_associated") is True
    ]
    incomplete_support_rows = [
        row for row in candidate_asymmetry_rows if row.get("all_role_associated") is not True
    ]
    unsafe_depth_rows = [
        row
        for row in alternative_rows
        if row.get("alternative_name") == "depth_consistency_count_best"
        and row.get("selected_candidate_label_for_audit_only") == "wrong"
    ]

    gate = {
        "candidate_asymmetry_rows_match": len(candidate_asymmetry_rows) == int(expected.get("candidate_asymmetry_rows", -1)),
        "pair_inspection_rows_match": len(pair_rows) == int(expected.get("pair_inspection_rows", -1)),
        "alternative_audit_rows_match": len(alternative_rows) == int(expected.get("alternative_audit_rows", -1)),
        "candidate_conditioned_asymmetry_present": bool(all_role_support_rows and incomplete_support_rows),
        "simple_depth_count_shortcut_rejected": len(unsafe_depth_rows) == 1,
        "fixed_blocker_ready_for_this_row": pair_rows[0].get("candidate_conditioned_blocker_ready_for_this_row") is True,
        "terminal_rule_not_promoted": pair_rows[0].get("terminal_arbitration_rule_ready") is False,
        "forbidden_action_keys_absent": forbidden_keys == [],
        "no_terminal_commit_pass": terminal_commit_rows == 0,
        "no_candidate_commit_pass": candidate_commit_rows == 0,
        "no_candidate_rejection_pass": candidate_rejection_rows == 0,
        "no_gt_action_pass": uses_gt_for_action_true_rows == 0,
        "paper_claim_blocked_pass": paper_claim_allowed_true_rows == 0,
    }
    gate["asymmetry_inspection_gate_passed"] = all(gate.values())

    write_jsonl(out_root / OUTPUT_FILES["candidate_asymmetry_rows"], candidate_asymmetry_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_inspection_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["alternative_audit_rows"], alternative_rows)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "contract": str(contract_path),
        "source_target_pair_rows": len(target_rows),
        "source_candidate_rows": len(candidate_rows),
        "source_role_rows": len(role_rows),
        "source_candidate_view_rows": len(candidate_view_rows),
        "source_evaluation_audit_rows": len(audit_rows),
        "candidate_asymmetry_rows": len(candidate_asymmetry_rows),
        "pair_inspection_rows": len(pair_rows),
        "alternative_audit_rows": len(alternative_rows),
        "candidate_conditioned_asymmetry_present": bool(all_role_support_rows and incomplete_support_rows),
        "all_role_associated_candidate_ids": [row.get("candidate_id") for row in all_role_support_rows],
        "candidate_conditioned_incomplete_candidate_ids": [row.get("candidate_id") for row in incomplete_support_rows],
        "candidate_conditioned_blocker_ready_for_this_row": pair_rows[0].get(
            "candidate_conditioned_blocker_ready_for_this_row"
        ),
        "terminal_arbitration_rule_ready": False,
        "candidate_label_counts_for_audit_only": compact_counter(
            row.get("candidate_label_for_audit_only") for row in candidate_asymmetry_rows
        ),
        "candidate_blocker_counts": compact_counter(
            row.get("candidate_conditioned_blocker") for row in candidate_asymmetry_rows
        ),
        "alternative_decision_counts": compact_counter(row.get("decision") for row in alternative_rows),
        "unsafe_simple_alternatives_for_audit_only": pair_rows[0].get("unsafe_simple_alternatives_for_audit_only"),
        "action_evidence_forbidden_keys_found": forbidden_keys,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action_true_rows": uses_gt_for_action_true_rows,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed_true_rows": paper_claim_allowed_true_rows,
        "gate": gate,
        "asymmetry_inspection_gate_passed": gate["asymmetry_inspection_gate_passed"],
        "promotion_gate_after_inspection_passed": False,
        "primary_blocker": "fixed_rule_needs_fully_covered_contrast_validation",
        "next_task": "freeze_fully_covered_candidate_conditioned_contrast_contract",
        "paper_claim_allowed_after_inspection": False,
    }
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    summary = materialize(resolve_path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
