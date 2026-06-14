import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    load_json,
    load_jsonl,
    safe_int,
)


SCHEMA_VERSION = "h001.residual_branch_promotion_requirement.v1"
POLICY_NAME = "residual_branch_promotion_requirement_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_residual_branch_promotion_requirement_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_residual_branch_promotion_requirement_v1"


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


def as_int_dict(payload: Mapping[str, Any] | None) -> Dict[str, int]:
    return dict(sorted((str(key), safe_int(value, 0)) for key, value in dict(payload or {}).items()))


def count_values(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "") for row in rows).items()))


def row_by_family(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        family = str(row.get("branch_family") or "")
        if family:
            output[family] = dict(row)
    return output


def priority_rank(family: str, priority_order: Sequence[str]) -> int:
    try:
        return list(priority_order).index(family) + 1
    except ValueError:
        return len(priority_order) + 1


def build_requirement_rows(
    *,
    contract: Mapping[str, Any],
    synthesis_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    family_contracts = dict(contract.get("family_requirements") or {})
    priority_order = [str(value) for value in (contract.get("promotion_policy") or {}).get("next_family_priority") or []]
    synthesis_by_family = row_by_family(synthesis_rows)
    output: List[Dict[str, Any]] = []
    for family in sorted(family_contracts, key=lambda item: priority_rank(item, priority_order)):
        family_contract = dict(family_contracts[family])
        source = synthesis_by_family.get(family, {})
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_residual_branch_promotion_requirement",
                "policy": POLICY_NAME,
                "branch_family": family,
                "priority_rank": priority_rank(family, priority_order),
                "source_request_status": source.get("source_request_status"),
                "source_branch_action": source.get("source_branch_action"),
                "source_request_rows": safe_int(source.get("request_rows"), 0),
                "source_branch_rows": safe_int(source.get("source_branch_rows"), 0),
                "source_materialized_output_rows": safe_int(source.get("materialized_output_rows"), 0),
                "source_branch_signal": source.get("branch_signal"),
                "source_next_evidence_need": source.get("next_evidence_need"),
                "required_extra_evidence": list(family_contract.get("required_extra_evidence") or []),
                "simpler_alternatives_to_test": list(family_contract.get("simpler_alternatives_to_test") or []),
                "first_probe_shape": family_contract.get("first_probe_shape"),
                "promotion_blocker_now": family_contract.get("promotion_blocker_now"),
                "requirement_status": "defined_not_satisfied",
                "promotable_terminal_outcome": False,
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def summarize(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    synthesis_summary: Mapping[str, Any],
    synthesis_rows: Sequence[Mapping[str, Any]],
    requirement_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    promotion_policy = contract.get("promotion_policy") or {}
    synthesis_gate = synthesis_summary.get("gate") or {}
    forbidden = action_forbidden_keys(requirement_rows)
    terminal_rows = [
        row
        for row in requirement_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    candidate_commit_rows = [
        row for row in requirement_rows if row.get("candidate_commit_allowed") is True
    ]
    candidate_rejection_rows = [
        row for row in requirement_rows if row.get("candidate_rejection_allowed") is True
    ]
    promotable_rows = [
        row for row in requirement_rows if row.get("promotable_terminal_outcome") is True
    ]
    priority_order = [
        str(value) for value in (promotion_policy.get("next_family_priority") or [])
    ]
    required_families = sorted((contract.get("family_requirements") or {}).keys())
    output_families = sorted(str(row.get("branch_family") or "") for row in requirement_rows)

    gate = {
        "source_synthesis_gate_passed": synthesis_gate.get("residual_branch_synthesis_gate_passed")
        is source_gate.get("residual_branch_synthesis_gate_passed"),
        "expected_family_rows_passed": len(synthesis_rows)
        == safe_int(source_gate.get("expected_family_rows"), -1),
        "expected_request_rows_passed": safe_int(synthesis_summary.get("family_request_rows"), 0)
        == safe_int(source_gate.get("expected_request_rows"), -1),
        "expected_source_branch_rows_passed": safe_int(
            synthesis_summary.get("family_source_branch_rows"), 0
        )
        == safe_int(source_gate.get("expected_source_branch_rows"), -1),
        "source_promotable_rows_passed": safe_int(
            synthesis_summary.get("promotable_terminal_outcome_rows"), 0
        )
        == safe_int(source_gate.get("expected_promotable_terminal_outcome_rows"), -1),
        "source_terminal_commit_rows_passed": safe_int(
            synthesis_summary.get("terminal_commit_rows"), 0
        )
        == safe_int(source_gate.get("expected_terminal_commit_rows"), -1),
        "source_candidate_commit_rows_passed": safe_int(
            synthesis_summary.get("candidate_commit_rows"), 0
        )
        == safe_int(source_gate.get("expected_candidate_commit_rows"), -1),
        "source_candidate_rejection_rows_passed": safe_int(
            synthesis_summary.get("candidate_rejection_rows"), 0
        )
        == safe_int(source_gate.get("expected_candidate_rejection_rows"), -1),
        "required_families_defined_passed": output_families == required_families,
        "priority_order_valid_passed": all(family in required_families for family in priority_order),
        "all_requirements_defined_passed": all(
            row.get("required_extra_evidence") and row.get("simpler_alternatives_to_test")
            for row in requirement_rows
        ),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        == safe_int(source_gate.get("expected_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        == safe_int(source_gate.get("expected_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        == safe_int(source_gate.get("expected_candidate_rejection_rows"), -1),
        "promotable_family_rows_passed": len(promotable_rows)
        == safe_int(promotion_policy.get("current_promotable_family_rows"), -1),
        "terminal_utility_blocked_passed": len(promotable_rows) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in requirement_rows),
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["promotion_requirement_gate_passed"] = all(gate[key] is True for key in pass_keys)

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "synthesis_summary": str(args.synthesis_summary),
            "synthesis_rows": str(args.synthesis_rows),
        },
        "source_family_rows": len(synthesis_rows),
        "source_request_rows": safe_int(synthesis_summary.get("family_request_rows"), 0),
        "source_branch_rows": safe_int(synthesis_summary.get("family_source_branch_rows"), 0),
        "source_family_output_rows": as_int_dict(synthesis_summary.get("family_output_rows")),
        "source_synthesis_status_counts": as_int_dict(
            synthesis_summary.get("family_synthesis_status_counts")
        ),
        "requirement_rows": len(requirement_rows),
        "requirement_status_counts": count_values(requirement_rows, "requirement_status"),
        "branch_family_priority": priority_order,
        "top_priority_family": priority_order[0] if priority_order else None,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "promotable_family_rows": len(promotable_rows),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "promotion_requirement_ready": gate["promotion_requirement_gate_passed"],
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
            "recommended_next_task": "design_repeated_object_relation_anchor_consistency_evidence_contract",
        },
        "blocked_downstream_tasks": list(contract.get("blocked_downstream_tasks") or []),
        "output_files": {
            "requirement_rows": "residual_branch_promotion_requirement_rows.jsonl",
            "summary": "residual_branch_promotion_requirement_summary.json",
        },
        "interpretation": {
            "fact": (
                "The requirement contract defines family-specific extra evidence for all residual "
                "branch families while preserving zero terminal commits and zero candidate commit/rejection rows."
            ),
            "agent_inference": (
                "The most useful next probe is repeated-object relation-anchor consistency because it "
                "covers the dominant residual source rows and directly tests repeated-instance ambiguity."
            ),
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.synthesis_summary = source_path(args, contract, "synthesis_summary", "synthesis_summary")
    args.synthesis_rows = source_path(args, contract, "synthesis_rows", "synthesis_rows")
    synthesis_summary = load_json(args.synthesis_summary)
    synthesis_rows = load_jsonl(args.synthesis_rows)
    requirement_rows = build_requirement_rows(contract=contract, synthesis_rows=synthesis_rows)
    summary = summarize(
        args=args,
        contract=contract,
        synthesis_summary=synthesis_summary,
        synthesis_rows=synthesis_rows,
        requirement_rows=requirement_rows,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "residual_branch_promotion_requirement_rows.jsonl", requirement_rows)
    write_json(out_root / "residual_branch_promotion_requirement_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--synthesis-summary", type=Path)
    parser.add_argument("--synthesis-rows", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
