import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys
from h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy import (
    load_json,
    safe_int,
)


SCHEMA_VERSION = "h001.residual_partial_relation_depth_branch_synthesis.v1"
POLICY_NAME = "residual_partial_relation_depth_branch_synthesis_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_residual_partial_relation_depth_branch_synthesis_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_residual_partial_relation_depth_branch_synthesis_v1"


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def gate_value(summary: Mapping[str, Any], key: str, default: Any = None) -> Any:
    gate = summary.get("gate") or {}
    return gate.get(key, default)


def as_counter(payload: Mapping[str, Any] | None) -> Dict[str, int]:
    return {
        str(key): safe_int(value, 0)
        for key, value in dict(payload or {}).items()
        if safe_int(value, 0) != 0
    }


def merge_counts(*items: Mapping[str, Any] | None) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(as_counter(item))
    return dict(sorted(counter.items()))


def family_common(
    *,
    family: str,
    source_status: str,
    source_branch_action: str,
    request_rows: int,
    source_branch_rows: int,
    output_rows: int,
    nonterminal_actions: Mapping[str, Any],
    gate_states: Mapping[str, bool],
    branch_signal: str,
    next_evidence_need: str,
    summaries: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    terminal_commit_rows = sum(safe_int(summary.get("terminal_commit_rows"), 0) for summary in summaries)
    candidate_commit_rows = sum(safe_int(summary.get("candidate_commit_rows"), 0) for summary in summaries)
    candidate_rejection_rows = sum(
        safe_int(summary.get("candidate_rejection_rows"), 0) for summary in summaries
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_residual_branch_synthesis_family",
        "policy": POLICY_NAME,
        "branch_family": family,
        "source_request_status": source_status,
        "source_branch_action": source_branch_action,
        "request_rows": request_rows,
        "source_branch_rows": source_branch_rows,
        "materialized_output_rows": output_rows,
        "nonterminal_action_counts": dict(sorted(as_counter(nonterminal_actions).items())),
        "gate_states": dict(sorted(gate_states.items())),
        "all_family_gates_passed": all(value is True for value in gate_states.values()),
        "branch_signal": branch_signal,
        "synthesis_status": "nonterminal_audit_or_repair_only",
        "next_evidence_need": next_evidence_need,
        "promotable_terminal_outcome": False,
        "terminal_arbitration_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "terminal_commit_rows_from_sources": terminal_commit_rows,
        "candidate_commit_rows_from_sources": candidate_commit_rows,
        "candidate_rejection_rows_from_sources": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_family_rows(summaries: Mapping[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    branch = summaries["branch"]
    association = summaries["association_geometry_repair"]
    followup = summaries["association_geometry_followup"]
    relation_anchor = summaries["relation_anchor_selection"]
    direction = summaries["direction_specific"]
    repeated = summaries["repeated_object"]
    depth = summaries["depth_stagnation"]

    rows = [
        {
            **family_common(
                family="association_geometry_underlink",
                source_status="association_geometry_underlink",
                source_branch_action="route_to_association_geometry_repair_branch",
                request_rows=safe_int(followup.get("followup_request_rows"), 0),
                source_branch_rows=safe_int(association.get("repair_rows"), 0),
                output_rows=(
                    safe_int(followup.get("followup_rows"), 0)
                    + safe_int(relation_anchor.get("probe_rows"), 0)
                    + safe_int(direction.get("probe_rows"), 0)
                ),
                nonterminal_actions=merge_counts(
                    followup.get("followup_repair_action_counts"),
                    relation_anchor.get("nonterminal_probe_action_counts"),
                    direction.get("nonterminal_probe_action_counts"),
                ),
                gate_states={
                    "source_branch_handling_gate": gate_value(
                        branch, "partial_relation_depth_branch_handling_gate_passed"
                    )
                    is True,
                    "association_geometry_repair_gate": gate_value(
                        association, "association_geometry_repair_diagnostic_gate_passed"
                    )
                    is True,
                    "association_geometry_followup_gate": gate_value(
                        followup, "association_geometry_followup_repair_gate_passed"
                    )
                    is True,
                    "relation_anchor_selection_probe_gate": gate_value(
                        relation_anchor, "relation_anchor_selection_repair_probe_gate_passed"
                    )
                    is True,
                    "direction_specific_reobservation_probe_gate": gate_value(
                        direction, "direction_specific_reobservation_repair_probe_gate_passed"
                    )
                    is True,
                },
                branch_signal=(
                    "mask projection exists, but exact failed completion views have no candidate "
                    "association or depth-consistent support; follow-up probes show anchor/direction "
                    "repair evidence only"
                ),
                next_evidence_need=(
                    "a label-free rule that distinguishes repairable anchor/direction geometry from "
                    "ObjectNav goal validity"
                ),
                summaries=[association, followup, relation_anchor, direction],
            ),
            "query_counts": association.get("query_counts") or {},
            "candidate_ids": association.get("candidate_ids") or [],
            "same_requested_direction_associated_heading_count": association.get(
                "same_requested_direction_associated_heading_count"
            ),
            "other_requested_direction_associated_heading_count": association.get(
                "other_requested_direction_associated_heading_count"
            ),
        },
        {
            **family_common(
                family="repeated_object_relation_anchor_ambiguity",
                source_status="repeated_object_relation_anchor_ambiguity",
                source_branch_action="route_to_repeated_object_relation_anchor_ambiguity_branch",
                request_rows=safe_int(repeated.get("request_rows"), 0),
                source_branch_rows=safe_int(repeated.get("branch_rows"), 0),
                output_rows=safe_int(repeated.get("branch_rows"), 0),
                nonterminal_actions=repeated.get("nonterminal_branch_action_counts"),
                gate_states={
                    "source_branch_handling_gate": gate_value(
                        branch, "partial_relation_depth_branch_handling_gate_passed"
                    )
                    is True,
                    "repeated_object_relation_anchor_ambiguity_gate": gate_value(
                        repeated, "repeated_object_relation_anchor_ambiguity_branch_gate_passed"
                    )
                    is True,
                },
                branch_signal=(
                    "same repeated-object scene/query contains mixed association-positive, "
                    "association-zero, depth-consistent, and mask-only rows across candidates"
                ),
                next_evidence_need=(
                    "instance and relation-anchor arbitration evidence that is not derived from labels"
                ),
                summaries=[repeated],
            ),
            "request_ids": repeated.get("request_ids") or [],
            "scene_query": repeated.get("scene_query") or [],
            "candidate_ids": repeated.get("candidate_ids") or [],
            "residual_failure_class_counts": repeated.get("residual_failure_class_counts") or {},
            "direction_counts": repeated.get("direction_counts") or {},
            "rows_with_completion_association": repeated.get("rows_with_completion_association"),
            "rows_with_zero_completion_association": repeated.get(
                "rows_with_zero_completion_association"
            ),
            "rows_with_completion_depth_consistent": repeated.get(
                "rows_with_completion_depth_consistent"
            ),
        },
        {
            **family_common(
                family="depth_stagnation",
                source_status="association_present_but_depth_not_improved",
                source_branch_action="route_to_depth_stagnation_branch",
                request_rows=safe_int(depth.get("request_rows"), 0),
                source_branch_rows=safe_int(depth.get("branch_rows"), 0),
                output_rows=safe_int(depth.get("branch_rows"), 0),
                nonterminal_actions=depth.get("nonterminal_branch_action_counts"),
                gate_states={
                    "source_branch_handling_gate": gate_value(
                        branch, "partial_relation_depth_branch_handling_gate_passed"
                    )
                    is True,
                    "depth_stagnation_branch_gate": gate_value(
                        depth, "depth_stagnation_branch_gate_passed"
                    )
                    is True,
                },
                branch_signal=(
                    "candidate association and depth consistency are present, but depth evidence "
                    "does not improve over prior relation-depth evidence"
                ),
                next_evidence_need=(
                    "independent support or temporal/map-side evidence that can separate stagnant "
                    "positive evidence from goal validity"
                ),
                summaries=[depth],
            ),
            "request_ids": depth.get("request_ids") or [],
            "scene_query": depth.get("scene_query") or [],
            "candidate_ids": depth.get("candidate_ids") or [],
            "residual_failure_class_counts": depth.get("residual_failure_class_counts") or {},
            "direction_counts": depth.get("direction_counts") or {},
            "prior_counts": depth.get("prior_counts") or {},
            "completion_counts": depth.get("completion_counts") or {},
            "depth_consistency_delta": depth.get("depth_consistency_delta"),
            "association_delta": depth.get("association_delta"),
        },
    ]
    return rows


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    summaries: Mapping[str, Dict[str, Any]],
    family_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    branch = summaries["branch"]
    branch_gate = branch.get("gate") or {}
    forbidden = action_forbidden_keys(family_rows)
    family_request_rows = sum(safe_int(row.get("request_rows"), 0) for row in family_rows)
    family_source_branch_rows = sum(safe_int(row.get("source_branch_rows"), 0) for row in family_rows)
    family_output_rows = {
        str(row.get("branch_family")): safe_int(row.get("materialized_output_rows"), 0)
        for row in family_rows
    }
    family_request_row_counts = {
        str(row.get("branch_family")): safe_int(row.get("request_rows"), 0) for row in family_rows
    }
    family_source_branch_row_counts = {
        str(row.get("branch_family")): safe_int(row.get("source_branch_rows"), 0)
        for row in family_rows
    }
    terminal_rows = [
        row
        for row in family_rows
        if row.get("terminal_commit") is True or row.get("terminal_arbitration_allowed") is True
    ]
    candidate_commit_rows = [
        row
        for row in family_rows
        if row.get("candidate_commit_allowed") is True
        or safe_int(row.get("candidate_commit_rows_from_sources"), 0) > 0
    ]
    candidate_rejection_rows = [
        row
        for row in family_rows
        if row.get("candidate_rejection_allowed") is True
        or safe_int(row.get("candidate_rejection_rows_from_sources"), 0) > 0
    ]
    promotable_rows = [row for row in family_rows if row.get("promotable_terminal_outcome") is True]
    terminal_utility_allowed = bool(promotable_rows) and not terminal_rows
    required_families = sorted((contract.get("synthesis_contract") or {}).get("required_branch_families") or [])

    gate = {
        "source_branch_handling_gate_passed": branch_gate.get(
            "partial_relation_depth_branch_handling_gate_passed"
        )
        is True,
        "expected_residual_request_rows_passed": safe_int(branch.get("request_branch_rows"), 0)
        == safe_int(source_gate.get("expected_residual_request_rows"), -1),
        "expected_residual_source_branch_rows_passed": safe_int(branch.get("branch_rows"), 0)
        == safe_int(source_gate.get("expected_residual_source_branch_rows"), -1),
        "expected_request_status_counts_passed": dict(branch.get("request_status_counts") or {})
        == dict(source_gate.get("expected_request_status_counts") or {}),
        "expected_branch_action_counts_passed": dict(branch.get("branch_action_counts") or {})
        == dict(source_gate.get("expected_branch_action_counts") or {}),
        "required_branch_families_present_passed": sorted(
            str(row.get("branch_family")) for row in family_rows
        )
        == required_families,
        "family_request_rows_accounted_passed": family_request_rows
        == safe_int(source_gate.get("expected_residual_request_rows"), -1),
        "family_source_branch_rows_accounted_passed": family_source_branch_rows
        == safe_int(source_gate.get("expected_residual_source_branch_rows"), -1),
        "expected_family_request_rows_passed": family_request_row_counts
        == dict(source_gate.get("expected_family_request_rows") or {}),
        "expected_family_source_branch_rows_passed": family_source_branch_row_counts
        == dict(source_gate.get("expected_family_source_branch_rows") or {}),
        "expected_family_output_rows_passed": family_output_rows
        == dict(source_gate.get("expected_family_output_rows") or {}),
        "all_family_gates_passed": all(row.get("all_family_gates_passed") is True for row in family_rows),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(source_gate.get("max_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        <= safe_int(source_gate.get("max_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), -1),
        "promotable_terminal_outcome_rows_passed": len(promotable_rows)
        == safe_int((contract.get("synthesis_contract") or {}).get("current_promotable_terminal_outcome_rows"), -1),
        "terminal_utility_blocked_passed": terminal_utility_allowed is False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in family_rows),
        "paper_claim_allowed": False,
    }
    pass_keys = [key for key in gate if key.endswith("_passed")]
    gate["residual_branch_synthesis_gate_passed"] = all(gate[key] is True for key in pass_keys)

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "branch_handling_summary": str(args.branch_handling_summary),
            "association_geometry_repair_summary": str(args.association_geometry_repair_summary),
            "association_geometry_followup_summary": str(args.association_geometry_followup_summary),
            "relation_anchor_selection_repair_summary": str(
                args.relation_anchor_selection_repair_summary
            ),
            "direction_specific_reobservation_repair_summary": str(
                args.direction_specific_reobservation_repair_summary
            ),
            "repeated_object_relation_anchor_ambiguity_summary": str(
                args.repeated_object_relation_anchor_ambiguity_summary
            ),
            "depth_stagnation_branch_summary": str(args.depth_stagnation_branch_summary),
        },
        "source_residual_request_rows": safe_int(branch.get("request_branch_rows"), 0),
        "source_residual_branch_rows": safe_int(branch.get("branch_rows"), 0),
        "source_request_status_counts": branch.get("request_status_counts") or {},
        "source_branch_action_counts": branch.get("branch_action_counts") or {},
        "family_count": len(family_rows),
        "family_request_rows": family_request_rows,
        "family_source_branch_rows": family_source_branch_rows,
        "family_output_rows": family_output_rows,
        "family_request_row_counts": family_request_row_counts,
        "family_source_branch_row_counts": family_source_branch_row_counts,
        "family_synthesis_status_counts": merge_counts(
            Counter(str(row.get("synthesis_status")) for row in family_rows)
        ),
        "family_nonterminal_action_counts": merge_counts(
            *(row.get("nonterminal_action_counts") for row in family_rows)
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "promotable_terminal_outcome_rows": len(promotable_rows),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "residual_branch_synthesis_ready": gate["residual_branch_synthesis_gate_passed"],
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
            "recommended_next_task": (
                "define_extra_evidence_requirement_for_promotable_branch_outcome_before_terminal_utility"
            ),
        },
        "blocked_downstream_tasks": list(contract.get("blocked_downstream_tasks") or []),
        "output_files": {
            "family_rows": "residual_partial_relation_depth_branch_synthesis_rows.jsonl",
            "summary": "residual_partial_relation_depth_branch_synthesis_summary.json",
        },
        "interpretation": {
            "fact": (
                "All six residual partial relation-depth requests and fifteen source branch rows "
                "are accounted for by association-geometry underlink, repeated-object relation-anchor "
                "ambiguity, and depth-stagnation branch families."
            ),
            "agent_inference": (
                "The completed branches are useful mechanism evidence, but none creates a label-free "
                "commit or rejection authority. Terminal utility, first_eval, policy-scale comparison, "
                "and paper claims remain blocked."
            ),
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(args.contract)
    args.branch_handling_summary = source_path(
        args, contract, "branch_handling_summary", "branch_handling_summary"
    )
    args.association_geometry_repair_summary = source_path(
        args, contract, "association_geometry_repair_summary", "association_geometry_repair_summary"
    )
    args.association_geometry_followup_summary = source_path(
        args, contract, "association_geometry_followup_summary", "association_geometry_followup_summary"
    )
    args.relation_anchor_selection_repair_summary = source_path(
        args, contract, "relation_anchor_selection_repair_summary", "relation_anchor_selection_repair_summary"
    )
    args.direction_specific_reobservation_repair_summary = source_path(
        args, contract, "direction_specific_reobservation_repair_summary", "direction_specific_reobservation_repair_summary"
    )
    args.repeated_object_relation_anchor_ambiguity_summary = source_path(
        args,
        contract,
        "repeated_object_relation_anchor_ambiguity_summary",
        "repeated_object_relation_anchor_ambiguity_summary",
    )
    args.depth_stagnation_branch_summary = source_path(
        args, contract, "depth_stagnation_branch_summary", "depth_stagnation_branch_summary"
    )

    summaries = {
        "branch": load_json(args.branch_handling_summary),
        "association_geometry_repair": load_json(args.association_geometry_repair_summary),
        "association_geometry_followup": load_json(args.association_geometry_followup_summary),
        "relation_anchor_selection": load_json(args.relation_anchor_selection_repair_summary),
        "direction_specific": load_json(args.direction_specific_reobservation_repair_summary),
        "repeated_object": load_json(args.repeated_object_relation_anchor_ambiguity_summary),
        "depth_stagnation": load_json(args.depth_stagnation_branch_summary),
    }
    family_rows = build_family_rows(summaries)
    summary = summarize(args=args, contract=contract, summaries=summaries, family_rows=family_rows)

    out_root = Path(args.out_root)
    write_jsonl(
        out_root / "residual_partial_relation_depth_branch_synthesis_rows.jsonl",
        family_rows,
    )
    write_json(
        out_root / "residual_partial_relation_depth_branch_synthesis_summary.json",
        summary,
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--branch-handling-summary", type=Path)
    parser.add_argument("--association-geometry-repair-summary", type=Path)
    parser.add_argument("--association-geometry-followup-summary", type=Path)
    parser.add_argument("--relation-anchor-selection-repair-summary", type=Path)
    parser.add_argument("--direction-specific-reobservation-repair-summary", type=Path)
    parser.add_argument("--repeated-object-relation-anchor-ambiguity-summary", type=Path)
    parser.add_argument("--depth-stagnation-branch-summary", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
