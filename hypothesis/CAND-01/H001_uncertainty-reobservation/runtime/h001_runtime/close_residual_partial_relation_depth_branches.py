import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    compact_counter,
    load_json,
    load_jsonl,
    safe_int,
)


SCHEMA_VERSION = "h001.residual_branch_closure.v1"
POLICY_NAME = "residual_branch_closure_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_residual_branch_closure_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_residual_branch_closure_v1"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Mapping[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def gate_value(summary: Mapping[str, Any], key: str) -> Any:
    return (summary.get("gate") or {}).get(key)


def row_by_family(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        family = str(row.get("branch_family") or "")
        if family:
            output[family] = dict(row)
    return output


def count_values(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "") for row in rows).items()))


def family_output_rows(synthesis_rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    return dict(
        sorted(
            (
                str(row.get("branch_family")),
                safe_int(row.get("materialized_output_rows"), 0),
            )
            for row in synthesis_rows
        )
    )


def family_mechanisms(
    family: str,
    *,
    repeated_summary: Mapping[str, Any],
    association_summary: Mapping[str, Any],
    depth_summary: Mapping[str, Any],
) -> List[str]:
    if family == "repeated_object_relation_anchor_ambiguity":
        classes = repeated_summary.get("residual_failure_class_counts") or {}
        mechanisms = []
        if safe_int(classes.get("same_request_stable_rule_tie"), 0):
            mechanisms.append("same_request_repeated_object_stable_tie_with_own_view_context_leakage")
        if safe_int(classes.get("own_view_context_leakage"), 0):
            mechanisms.append("own_view_context_leakage")
        if safe_int(classes.get("missing_own_view_target_support"), 0):
            mechanisms.append("missing_own_view_target_support")
        return mechanisms
    if family == "association_geometry_underlink":
        outcomes = association_summary.get("request_outcome_counts") or {}
        mechanisms = []
        if safe_int(outcomes.get("anchor_selection_repair_supported_but_nonterminal"), 0):
            mechanisms.append("anchor_selection_underlink_repairable_but_nonterminal")
        if safe_int(outcomes.get("direction_specific_reobservation_supported_but_nonterminal"), 0):
            mechanisms.append("direction_specific_reobservation_repairable_but_nonterminal")
        return mechanisms
    if family == "depth_stagnation":
        if (
            safe_int(depth_summary.get("request_rows"), 0) == 1
            and safe_int(depth_summary.get("association_delta"), 999999) == 0
            and safe_int(depth_summary.get("depth_consistency_delta"), 999999) == 0
        ):
            return ["association_present_depth_stagnant_without_evidence_delta"]
    return ["manual_review_unexpected_residual_branch_closure"]


def family_evidence_summary(
    family: str,
    *,
    repeated_summary: Mapping[str, Any],
    association_summary: Mapping[str, Any],
    depth_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    if family == "repeated_object_relation_anchor_ambiguity":
        return {
            "candidate_rows": safe_int(repeated_summary.get("candidate_rows"), 0),
            "request_rows": safe_int(repeated_summary.get("request_rows"), 0),
            "residual_failure_class_counts": repeated_summary.get("residual_failure_class_counts") or {},
            "request_residual_status_counts": repeated_summary.get("request_residual_status_counts") or {},
            "stable_rule_candidate_count_by_request": repeated_summary.get(
                "stable_rule_candidate_count_by_request"
            )
            or {},
            "promotable_branch_outcome_rows": safe_int(
                repeated_summary.get("promotable_branch_outcome_rows"), 0
            ),
        }
    if family == "association_geometry_underlink":
        return {
            "evidence_rows": safe_int(association_summary.get("evidence_rows"), 0),
            "request_rows": safe_int(association_summary.get("request_rows"), 0),
            "evidence_class_counts": association_summary.get("evidence_class_counts") or {},
            "evidence_status_counts": association_summary.get("evidence_status_counts") or {},
            "request_outcome_counts": association_summary.get("request_outcome_counts") or {},
            "recovered_associated_heading_count": safe_int(
                association_summary.get("recovered_associated_heading_count"), 0
            ),
            "recovered_associated_depth_consistent_count": safe_int(
                association_summary.get("recovered_associated_depth_consistent_count"), 0
            ),
            "promotable_branch_outcome_rows": safe_int(
                association_summary.get("promotable_branch_outcome_rows"), 0
            ),
        }
    if family == "depth_stagnation":
        return {
            "request_rows": safe_int(depth_summary.get("request_rows"), 0),
            "branch_rows": safe_int(depth_summary.get("branch_rows"), 0),
            "request_ids": depth_summary.get("request_ids") or [],
            "scene_query": depth_summary.get("scene_query") or [],
            "candidate_ids": depth_summary.get("candidate_ids") or [],
            "prior_counts": depth_summary.get("prior_counts") or {},
            "completion_counts": depth_summary.get("completion_counts") or {},
            "association_delta": safe_int(depth_summary.get("association_delta"), 0),
            "depth_consistency_delta": safe_int(depth_summary.get("depth_consistency_delta"), 0),
            "nonterminal_branch_action_counts": depth_summary.get("nonterminal_branch_action_counts")
            or {},
        }
    return {}


def build_closure_rows(
    *,
    contract: Mapping[str, Any],
    synthesis_rows: Sequence[Mapping[str, Any]],
    requirement_rows: Sequence[Mapping[str, Any]],
    repeated_summary: Mapping[str, Any],
    association_summary: Mapping[str, Any],
    depth_summary: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    closure_contract = contract.get("closure_contract") or {}
    design = contract.get("design_decision") or {}
    synthesis_by_family = row_by_family(synthesis_rows)
    requirement_by_family = row_by_family(requirement_rows)
    target_families = [str(item) for item in closure_contract.get("target_branch_families") or []]
    required_status = closure_contract.get("required_branch_status") or {}
    rows: List[Dict[str, Any]] = []
    for family in target_families:
        synthesis = synthesis_by_family.get(family, {})
        requirement = requirement_by_family.get(family, {})
        mechanisms = family_mechanisms(
            family,
            repeated_summary=repeated_summary,
            association_summary=association_summary,
            depth_summary=depth_summary,
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_residual_branch_closure_family",
                "policy": POLICY_NAME,
                "branch_family": family,
                "closure_status": required_status.get(family),
                "closure_decision": design.get("selected_path"),
                "deferred_path": design.get("rejected_path_now"),
                "source_request_status": synthesis.get("source_request_status"),
                "source_branch_action": synthesis.get("source_branch_action"),
                "source_request_rows": safe_int(synthesis.get("request_rows"), 0),
                "source_branch_rows": safe_int(synthesis.get("source_branch_rows"), 0),
                "source_materialized_output_rows": safe_int(
                    synthesis.get("materialized_output_rows"), 0
                ),
                "source_branch_signal": synthesis.get("branch_signal"),
                "source_next_evidence_need": synthesis.get("next_evidence_need"),
                "requirement_status": requirement.get("requirement_status"),
                "required_extra_evidence": list(requirement.get("required_extra_evidence") or []),
                "simpler_alternatives_to_test": list(
                    requirement.get("simpler_alternatives_to_test") or []
                ),
                "promotion_blocker_now": requirement.get("promotion_blocker_now"),
                "failure_mechanisms": mechanisms,
                "evidence_summary": family_evidence_summary(
                    family,
                    repeated_summary=repeated_summary,
                    association_summary=association_summary,
                    depth_summary=depth_summary,
                ),
                "blocked_shortcuts": list(closure_contract.get("blocked_shortcuts") or []),
                "allowed_next_claim_type": closure_contract.get("allowed_next_claim_type"),
                "depth_stagnation_probe_deferred_until": (
                    list(design.get("depth_stagnation_probe_deferred_until") or [])
                    if family == "depth_stagnation"
                    else []
                ),
                "closure_promotable": False,
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    synthesis_summary: Mapping[str, Any],
    synthesis_rows: Sequence[Mapping[str, Any]],
    promotion_summary: Mapping[str, Any],
    requirement_rows: Sequence[Mapping[str, Any]],
    repeated_summary: Mapping[str, Any],
    association_summary: Mapping[str, Any],
    depth_summary: Mapping[str, Any],
    closure_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    closure_contract = contract.get("closure_contract") or {}
    forbidden = action_forbidden_keys(closure_rows)
    terminal_rows = [
        row
        for row in closure_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    candidate_commit_rows = [
        row for row in closure_rows if row.get("candidate_commit_allowed") is True
    ]
    candidate_rejection_rows = [
        row for row in closure_rows if row.get("candidate_rejection_allowed") is True
    ]
    closure_promotable_rows = [row for row in closure_rows if row.get("closure_promotable") is True]
    actual_family_output_rows = family_output_rows(synthesis_rows)
    actual_requirement_status_counts = count_values(requirement_rows, "requirement_status")
    expected_families = [str(item) for item in closure_contract.get("target_branch_families") or []]
    actual_families = [str(row.get("branch_family") or "") for row in closure_rows]
    closure_status_counts = compact_counter(row.get("closure_status") for row in closure_rows)
    mechanism_counts = compact_counter(
        mechanism for row in closure_rows for mechanism in row.get("failure_mechanisms", [])
    )
    repeated_promotable = safe_int(repeated_summary.get("promotable_branch_outcome_rows"), 0)
    association_promotable = safe_int(association_summary.get("promotable_branch_outcome_rows"), 0)

    gate = {
        "residual_branch_synthesis_gate_passed": gate_value(
            synthesis_summary, "residual_branch_synthesis_gate_passed"
        )
        is source_gate.get("residual_branch_synthesis_gate_passed"),
        "promotion_requirement_gate_passed": gate_value(
            promotion_summary, "promotion_requirement_gate_passed"
        )
        is source_gate.get("promotion_requirement_gate_passed"),
        "repeated_object_residual_diagnostic_gate_passed": gate_value(
            repeated_summary, "residual_diagnostic_gate_passed"
        )
        is source_gate.get("repeated_object_residual_diagnostic_gate_passed"),
        "association_geometry_underlink_repair_followup_evidence_gate_passed": gate_value(
            association_summary,
            "association_geometry_underlink_repair_followup_evidence_gate_passed",
        )
        is source_gate.get("association_geometry_underlink_repair_followup_evidence_gate_passed"),
        "depth_stagnation_branch_gate_passed": gate_value(
            depth_summary, "depth_stagnation_branch_gate_passed"
        )
        is source_gate.get("depth_stagnation_branch_gate_passed"),
        "expected_family_rows_passed": len(synthesis_rows)
        == safe_int(source_gate.get("expected_family_rows"), -1),
        "expected_request_rows_passed": safe_int(synthesis_summary.get("family_request_rows"), 0)
        == safe_int(source_gate.get("expected_request_rows"), -1),
        "expected_source_branch_rows_passed": safe_int(
            synthesis_summary.get("family_source_branch_rows"), 0
        )
        == safe_int(source_gate.get("expected_source_branch_rows"), -1),
        "expected_family_output_rows_passed": actual_family_output_rows
        == dict(source_gate.get("expected_family_output_rows") or {}),
        "expected_requirement_status_counts_passed": actual_requirement_status_counts
        == dict(source_gate.get("expected_requirement_status_counts") or {}),
        "expected_repeated_object_promotable_branch_outcome_rows_passed": repeated_promotable
        == safe_int(source_gate.get("expected_repeated_object_promotable_branch_outcome_rows"), -1),
        "expected_association_geometry_promotable_branch_outcome_rows_passed": association_promotable
        == safe_int(source_gate.get("expected_association_geometry_promotable_branch_outcome_rows"), -1),
        "expected_depth_stagnation_request_rows_passed": safe_int(
            depth_summary.get("request_rows"), 0
        )
        == safe_int(source_gate.get("expected_depth_stagnation_request_rows"), -1),
        "expected_depth_stagnation_association_delta_passed": safe_int(
            depth_summary.get("association_delta"), 999999
        )
        == safe_int(source_gate.get("expected_depth_stagnation_association_delta"), -1),
        "expected_depth_stagnation_depth_consistency_delta_passed": safe_int(
            depth_summary.get("depth_consistency_delta"), 999999
        )
        == safe_int(source_gate.get("expected_depth_stagnation_depth_consistency_delta"), -1),
        "target_branch_families_passed": actual_families == expected_families,
        "closure_rows_passed": len(closure_rows) == len(expected_families),
        "required_branch_status_passed": all(row.get("closure_status") for row in closure_rows),
        "required_failure_mechanisms_present_passed": all(
            row.get("failure_mechanisms") for row in closure_rows
        ),
        "closure_promotable_rows_passed": len(closure_promotable_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        <= safe_int(source_gate.get("max_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in closure_rows),
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["residual_branch_closure_gate_passed"] = all(gate[key] is True for key in pass_keys)

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "residual_branch_synthesis_summary": str(args.residual_branch_synthesis_summary),
            "residual_branch_synthesis_rows": str(args.residual_branch_synthesis_rows),
            "promotion_requirement_summary": str(args.promotion_requirement_summary),
            "promotion_requirement_rows": str(args.promotion_requirement_rows),
            "repeated_object_residual_summary": str(args.repeated_object_residual_summary),
            "association_geometry_evidence_summary": str(args.association_geometry_evidence_summary),
            "depth_stagnation_summary": str(args.depth_stagnation_summary),
        },
        "selected_path": (contract.get("design_decision") or {}).get("selected_path"),
        "deferred_path": (contract.get("design_decision") or {}).get("rejected_path_now"),
        "closure_rows": len(closure_rows),
        "target_branch_families": expected_families,
        "closure_status_counts": closure_status_counts,
        "closure_failure_mechanism_counts": mechanism_counts,
        "source_family_rows": len(synthesis_rows),
        "source_request_rows": safe_int(synthesis_summary.get("family_request_rows"), 0),
        "source_branch_rows": safe_int(synthesis_summary.get("family_source_branch_rows"), 0),
        "source_family_output_rows": actual_family_output_rows,
        "requirement_status_counts": actual_requirement_status_counts,
        "repeated_object_promotable_branch_outcome_rows": repeated_promotable,
        "association_geometry_promotable_branch_outcome_rows": association_promotable,
        "depth_stagnation_request_rows": safe_int(depth_summary.get("request_rows"), 0),
        "depth_stagnation_association_delta": safe_int(depth_summary.get("association_delta"), 0),
        "depth_stagnation_depth_consistency_delta": safe_int(
            depth_summary.get("depth_consistency_delta"), 0
        ),
        "closure_promotable_rows": len(closure_promotable_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "residual_branch_closure_ready": gate["residual_branch_closure_gate_passed"],
            "selected_path": (contract.get("design_decision") or {}).get("selected_path"),
            "deferred_path": (contract.get("design_decision") or {}).get("rejected_path_now"),
            "recommended_next_task": "keep_terminal_utility_blocked_until_new_label_free_promotable_branch",
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_downstream_tasks": list(contract.get("blocked_downstream_tasks") or []),
        "output_files": dict(contract.get("required_future_outputs") or {}),
        "interpretation": {
            "fact": (
                "The closure analyzer writes one closure row per residual partial relation-depth family "
                "and preserves zero terminal commits and zero candidate commit/rejection rows."
            ),
            "agent_inference": (
                "The current residual branch family is better used as terminal-blocking failure taxonomy "
                "than as terminal utility evidence. A depth-stagnation independent-support probe should "
                "wait for broader rows or map/pose-side support."
            ),
            "paper_claim": "No paper claim is allowed from this closure analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.residual_branch_synthesis_summary = source_path(
        args, contract, "residual_branch_synthesis_summary", "residual_branch_synthesis_summary"
    )
    args.residual_branch_synthesis_rows = Path(args.residual_branch_synthesis_rows) if args.residual_branch_synthesis_rows else Path(
        str(contract.get("source", {}).get("residual_branch_synthesis_output"))
    ) / "residual_partial_relation_depth_branch_synthesis_rows.jsonl"
    args.promotion_requirement_summary = source_path(
        args, contract, "promotion_requirement_summary", "promotion_requirement_summary"
    )
    args.promotion_requirement_rows = source_path(
        args, contract, "promotion_requirement_rows", "promotion_requirement_rows"
    )
    args.repeated_object_residual_summary = source_path(
        args, contract, "repeated_object_residual_summary", "repeated_object_residual_summary"
    )
    args.association_geometry_evidence_summary = source_path(
        args, contract, "association_geometry_evidence_summary", "association_geometry_evidence_summary"
    )
    args.depth_stagnation_summary = source_path(
        args, contract, "depth_stagnation_summary", "depth_stagnation_summary"
    )

    synthesis_summary = load_json(args.residual_branch_synthesis_summary)
    synthesis_rows = load_jsonl(args.residual_branch_synthesis_rows)
    promotion_summary = load_json(args.promotion_requirement_summary)
    requirement_rows = load_jsonl(args.promotion_requirement_rows)
    repeated_summary = load_json(args.repeated_object_residual_summary)
    association_summary = load_json(args.association_geometry_evidence_summary)
    depth_summary = load_json(args.depth_stagnation_summary)

    closure_rows = build_closure_rows(
        contract=contract,
        synthesis_rows=synthesis_rows,
        requirement_rows=requirement_rows,
        repeated_summary=repeated_summary,
        association_summary=association_summary,
        depth_summary=depth_summary,
    )
    summary = summarize(
        args=args,
        contract=contract,
        synthesis_summary=synthesis_summary,
        synthesis_rows=synthesis_rows,
        promotion_summary=promotion_summary,
        requirement_rows=requirement_rows,
        repeated_summary=repeated_summary,
        association_summary=association_summary,
        depth_summary=depth_summary,
        closure_rows=closure_rows,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "residual_branch_closure_rows.jsonl", closure_rows)
    write_json(out_root / "residual_branch_closure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close nonpromotable residual partial relation-depth branch families."
    )
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--residual-branch-synthesis-summary", type=Path)
    parser.add_argument("--residual-branch-synthesis-rows", type=Path)
    parser.add_argument("--promotion-requirement-summary", type=Path)
    parser.add_argument("--promotion-requirement-rows", type=Path)
    parser.add_argument("--repeated-object-residual-summary", type=Path)
    parser.add_argument("--association-geometry-evidence-summary", type=Path)
    parser.add_argument("--depth-stagnation-summary", type=Path)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(
        json.dumps(
            {
                "gate": summary["gate"]["residual_branch_closure_gate_passed"],
                "closure_rows": summary["closure_rows"],
                "closure_status_counts": summary["closure_status_counts"],
                "closure_failure_mechanism_counts": summary["closure_failure_mechanism_counts"],
                "terminal_commit_rows": summary["terminal_commit_rows"],
                "candidate_commit_rows": summary["candidate_commit_rows"],
                "candidate_rejection_rows": summary["candidate_rejection_rows"],
                "uses_gt_for_action": summary["uses_gt_for_action"],
                "paper_claim_allowed": summary["paper_claim_allowed"],
                "next": summary["diagnostic_conclusion"]["recommended_next_task"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
