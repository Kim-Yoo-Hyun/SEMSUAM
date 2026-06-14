import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "h001.next_label_free_evidence_family_after_object_relation.v1"
POLICY_NAME = "next_evidence_family_after_object_relation_selector_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_next_label_free_evidence_family_after_object_relation_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_next_label_free_evidence_family_after_object_relation_v1"


FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
    "evaluation_only_correct_candidate_count",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_unlabeled_candidate_count",
    "evaluation_only_wrong_candidate_count",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "is_correct",
    "oracle_action",
    "target_label",
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


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


def count_by(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "") for row in rows if row.get(key)).items()))


def action_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def route_rows_for(rows: Sequence[Mapping[str, Any]], route_branch: str) -> List[Mapping[str, Any]]:
    return [row for row in rows if row.get("route_branch") == route_branch]


def route_stats(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    scenes = sorted({str(row.get("scene_key")) for row in rows if row.get("scene_key")})
    queries = sorted({str(row.get("query")) for row in rows if row.get("query")})
    candidate_count_sum = sum(safe_int((row.get("action_candidate_summary") or {}).get("candidate_count")) for row in rows)
    strong_own_view_sum = sum(
        safe_int((row.get("action_candidate_summary") or {}).get("strong_own_view_candidate_count"))
        for row in rows
    )
    detector_strong_sum = sum(
        safe_int((row.get("action_candidate_summary") or {}).get("detector_strong_candidate_count"))
        for row in rows
    )
    return {
        "request_rows": len(rows),
        "unique_scene_count": len(scenes),
        "unique_query_count": len(queries),
        "scenes": scenes,
        "queries": queries,
        "route_action_counts": count_by(rows, "route_action"),
        "route_reason_counts": count_by(rows, "route_reason"),
        "candidate_count_sum": candidate_count_sum,
        "strong_own_view_candidate_count_sum": strong_own_view_sum,
        "detector_strong_candidate_count_sum": detector_strong_sum,
    }


def build_selection_rows(
    *,
    contract: Mapping[str, Any],
    route_rows: Sequence[Mapping[str, Any]],
    route_summary: Mapping[str, Any],
    object_relation_summary: Mapping[str, Any],
    unique_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    missing_summary: Mapping[str, Any],
    source_pool_summary: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    decision = contract.get("selection_decision") or {}
    selected = str(decision.get("selected_branch"))
    route_branch_counts = route_summary.get("route_branch_counts") or count_by(route_rows, "route_branch")
    route_action_counts = route_summary.get("route_action_counts") or count_by(route_rows, "route_action")
    route_reason_counts = route_summary.get("route_reason_counts") or count_by(route_rows, "route_reason")
    object_relation_request_counts = object_relation_summary.get("request_branch_counts") or {}
    object_relation_candidate_counts = object_relation_summary.get("candidate_branch_counts") or {}

    families = [
        "source_pool_repair_v1",
        "goal_validity_confirmation_v1",
        "object_relation_branch_family",
        "instance_arbitration_defer_v1",
    ]
    rows: List[Dict[str, Any]] = []
    for family in families:
        family_route_rows = route_rows_for(route_rows, family)
        stats = route_stats(family_route_rows)
        if family == selected:
            status = decision.get("selected_output_status")
            next_action = decision.get("selected_action")
            reason = "largest_unprocessed_action_time_branch_after_object_relation_family_closure"
        elif family == "source_pool_repair_v1":
            status = (decision.get("closed_or_not_selected_families") or {}).get(family)
            next_action = "none_record_backend_source_map_blind_spot"
            reason = "source_pool_second_fallback_gate_passed_and_blind_spot_recorded"
        elif family == "goal_validity_confirmation_v1":
            status = (decision.get("closed_or_not_selected_families") or {}).get(family)
            next_action = "none_object_relation_family_already_followed"
            reason = "goal_validity_route_followed_into_object_relation_branch_family"
        else:
            status = (decision.get("closed_or_not_selected_families") or {}).get(family)
            next_action = "none_family_closed"
            reason = "unique_support_partial_relation_depth_missing_own_view_and_guard_branches_closed"

        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_next_label_free_evidence_family_after_object_relation_closure",
                "policy": POLICY_NAME,
                "family_name": family,
                "selection_status": status,
                "next_action": next_action,
                "selection_reason": reason,
                "route_branch_rows": safe_int(route_branch_counts.get(family), 0),
                "route_action_counts": route_action_counts,
                "route_reason_counts": route_reason_counts,
                "family_route_stats": stats,
                "object_relation_request_branch_counts": object_relation_request_counts,
                "object_relation_candidate_branch_counts": object_relation_candidate_counts,
                "unique_support_closed_request_rows": safe_int(unique_summary.get("closed_request_rows"), 0),
                "unique_support_unclosed_request_rows": safe_int(
                    unique_summary.get("unclosed_unique_support_request_rows"), 0
                ),
                "residual_closure_rows": safe_int(residual_summary.get("closure_rows"), 0),
                "residual_closure_promotable_rows": safe_int(residual_summary.get("closure_promotable_rows"), 0),
                "missing_own_view_closed_request_rows": safe_int(missing_summary.get("closed_request_rows"), 0),
                "missing_own_view_promotable_terminal_outcome_rows": safe_int(
                    missing_summary.get("promotable_terminal_outcome_rows"), 0
                ),
                "source_pool_second_fallback_gate_passed": gate_value(
                    source_pool_summary, "second_fallback_gate_passed"
                ),
                "backend_source_map_blind_spot_after_second_fallback": gate_value(
                    source_pool_summary, "backend_source_map_blind_spot_after_second_fallback"
                ),
                "terminal_commit": False,
                "terminal_utility_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    route_summary: Mapping[str, Any],
    route_rows: Sequence[Mapping[str, Any]],
    object_relation_summary: Mapping[str, Any],
    unique_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    missing_summary: Mapping[str, Any],
    source_pool_summary: Mapping[str, Any],
    selection_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    decision = contract.get("selection_decision") or {}
    source_gate = contract.get("source_gate") or {}
    selected = str(decision.get("selected_branch"))
    selected_rows = route_rows_for(route_rows, selected)
    selected_stats = route_stats(selected_rows)
    route_branch_counts = route_summary.get("route_branch_counts") or count_by(route_rows, "route_branch")
    expected_counts = decision.get("expected_route_branch_counts") or {}
    terminal_commit_rows = sum(1 for row in selection_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in selection_rows if row.get("candidate_commit_allowed") is True)
    candidate_rejection_rows = sum(1 for row in selection_rows if row.get("candidate_rejection_allowed") is True)
    forbidden = sorted(set(action_forbidden_keys(selection_rows)) | set(action_forbidden_keys(selected_rows)))
    gate = {
        "route_contract_gate_passed": gate_value(route_summary, "route_contract_gate_passed")
        is source_gate.get("route_contract_gate_passed"),
        "expected_route_branch_counts_passed": {
            branch: safe_int(route_branch_counts.get(branch), 0) == safe_int(expected, 0)
            for branch, expected in expected_counts.items()
        },
        "object_relation_branch_router_gate_passed": gate_value(
            object_relation_summary, "branch_evidence_router_gate_passed"
        )
        is source_gate.get("object_relation_branch_router_gate_passed"),
        "unique_support_branch_closure_gate_passed": gate_value(
            unique_summary, "unique_support_branch_closure_gate_passed"
        )
        is source_gate.get("unique_support_branch_closure_gate_passed"),
        "unique_support_fully_closed_passed": safe_int(
            unique_summary.get("unclosed_unique_support_request_rows"), -1
        )
        == 0,
        "residual_branch_closure_gate_passed": gate_value(
            residual_summary, "residual_branch_closure_gate_passed"
        )
        is source_gate.get("residual_branch_closure_gate_passed"),
        "residual_closure_promotable_rows_passed": safe_int(
            residual_summary.get("closure_promotable_rows"), -1
        )
        == 0,
        "missing_own_view_guard_branch_closure_gate_passed": gate_value(
            missing_summary, "missing_own_view_guard_branch_closure_gate_passed"
        )
        is source_gate.get("missing_own_view_guard_branch_closure_gate_passed"),
        "missing_own_view_promotable_rows_passed": safe_int(
            missing_summary.get("promotable_terminal_outcome_rows"), -1
        )
        == 0,
        "source_pool_second_fallback_gate_passed": gate_value(
            source_pool_summary, "second_fallback_gate_passed"
        )
        is source_gate.get("source_pool_second_fallback_gate_passed"),
        "source_pool_blind_spot_recorded_passed": gate_value(
            source_pool_summary, "backend_source_map_blind_spot_after_second_fallback"
        )
        is source_gate.get("source_pool_blind_spot_recorded"),
        "selected_request_rows_passed": selected_stats["request_rows"]
        >= safe_int(decision.get("minimum_selected_request_rows"), 0),
        "selected_unique_scenes_passed": selected_stats["unique_scene_count"]
        >= safe_int(decision.get("minimum_selected_unique_scenes"), 0),
        "selected_unique_queries_passed": selected_stats["unique_query_count"]
        >= safe_int(decision.get("minimum_selected_unique_queries"), 0),
        "selected_candidate_count_sum_passed": selected_stats["candidate_count_sum"]
        >= safe_int(decision.get("minimum_selected_candidate_count_sum"), 0),
        "selected_action_is_nonterminal_defer_passed": selected_stats["route_action_counts"]
        == {"defer_instance_arbitration_unresolved": selected_stats["request_rows"]},
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": terminal_commit_rows
        <= safe_int(source_gate.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": candidate_commit_rows
        <= safe_int(source_gate.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": candidate_rejection_rows
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in selection_rows)
        and all(row.get("uses_gt_for_action") is False for row in selected_rows),
        "paper_claim_allowed": False,
    }
    nested_gate_values: List[Any] = []
    for key, value in gate.items():
        if key == "paper_claim_allowed":
            continue
        if isinstance(value, dict):
            nested_gate_values.extend(value.values())
        else:
            nested_gate_values.append(value)
    gate["next_label_free_evidence_family_after_object_relation_gate_passed"] = all(
        item is True for item in nested_gate_values if isinstance(item, bool)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source_files": {
            "route_specific_summary": str(args.route_summary),
            "route_specific_rows": str(args.route_rows),
            "object_relation_branch_summary": str(args.object_relation_summary),
            "unique_support_branch_closure_summary": str(args.unique_summary),
            "residual_branch_closure_summary": str(args.residual_summary),
            "missing_own_view_guard_branch_closure_summary": str(args.missing_summary),
            "source_pool_second_fallback_summary": str(args.source_pool_summary),
        },
        "selected_family": decision.get("selected_family"),
        "selected_branch": selected,
        "selected_action": decision.get("selected_action"),
        "route_branch_counts": route_branch_counts,
        "route_action_counts": route_summary.get("route_action_counts") or count_by(route_rows, "route_action"),
        "route_reason_counts": route_summary.get("route_reason_counts") or count_by(route_rows, "route_reason"),
        "selected_family_stats": selected_stats,
        "object_relation_family_closure": {
            "request_branch_counts": object_relation_summary.get("request_branch_counts") or {},
            "candidate_branch_counts": object_relation_summary.get("candidate_branch_counts") or {},
            "unique_support_closed_request_rows": safe_int(unique_summary.get("closed_request_rows"), 0),
            "unique_support_unclosed_request_rows": safe_int(
                unique_summary.get("unclosed_unique_support_request_rows"), 0
            ),
            "residual_closure_rows": safe_int(residual_summary.get("closure_rows"), 0),
            "residual_closure_promotable_rows": safe_int(residual_summary.get("closure_promotable_rows"), 0),
            "missing_own_view_closed_request_rows": safe_int(missing_summary.get("closed_request_rows"), 0),
            "missing_own_view_promotable_terminal_outcome_rows": safe_int(
                missing_summary.get("promotable_terminal_outcome_rows"), 0
            ),
        },
        "source_pool_status": {
            "route_branch_rows": safe_int(route_branch_counts.get("source_pool_repair_v1"), 0),
            "second_fallback_gate_passed": gate_value(source_pool_summary, "second_fallback_gate_passed"),
            "backend_source_map_blind_spot_after_second_fallback": gate_value(
                source_pool_summary, "backend_source_map_blind_spot_after_second_fallback"
            ),
            "goal_validity_confirmation_unblocked": gate_value(
                source_pool_summary, "goal_validity_confirmation_unblocked"
            ),
            "terminal_commit_rows": safe_int(source_pool_summary.get("terminal_commit_rows"), 0),
        },
        "selection_rows": len(selection_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "analysis_label_fields_allowed": True,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "recommended_next_task": contract.get("next_research_task_after_selection"),
            "selected_family": decision.get("selected_family"),
            "selected_action": decision.get("selected_action"),
            "terminal_policy_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": {
            "fact": (
                "The selected family is read from existing action-time route rows after object-relation "
                "sub-branches and source-pool fallback status are checked."
            ),
            "agent_inference": (
                "Instance arbitration is the next label-free evidence family because it is the largest "
                "remaining unprocessed branch and directly tests multi-candidate semantic ambiguity."
            ),
            "paper_claim": "No paper claim is allowed from this selection output alone.",
        },
        "output_files": {
            "selection_rows": "next_label_free_evidence_family_after_object_relation_rows.jsonl",
            "summary": "next_label_free_evidence_family_after_object_relation_summary.json",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--route-summary")
    parser.add_argument("--route-rows")
    parser.add_argument("--object-relation-summary")
    parser.add_argument("--unique-summary")
    parser.add_argument("--residual-summary")
    parser.add_argument("--missing-summary")
    parser.add_argument("--source-pool-summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(Path(args.contract))
    args.out_root = Path(args.out_root)
    args.route_summary = source_path(args, contract, "route_summary", "route_specific_summary")
    args.route_rows = source_path(args, contract, "route_rows", "route_specific_rows")
    args.object_relation_summary = source_path(
        args, contract, "object_relation_summary", "object_relation_branch_summary"
    )
    args.unique_summary = source_path(
        args, contract, "unique_summary", "unique_support_branch_closure_summary"
    )
    args.residual_summary = source_path(args, contract, "residual_summary", "residual_branch_closure_summary")
    args.missing_summary = source_path(
        args, contract, "missing_summary", "missing_own_view_guard_branch_closure_summary"
    )
    args.source_pool_summary = source_path(
        args, contract, "source_pool_summary", "source_pool_second_fallback_summary"
    )

    route_summary = load_json(args.route_summary)
    route_rows = load_jsonl(args.route_rows)
    object_relation_summary = load_json(args.object_relation_summary)
    unique_summary = load_json(args.unique_summary)
    residual_summary = load_json(args.residual_summary)
    missing_summary = load_json(args.missing_summary)
    source_pool_summary = load_json(args.source_pool_summary)
    selection_rows = build_selection_rows(
        contract=contract,
        route_rows=route_rows,
        route_summary=route_summary,
        object_relation_summary=object_relation_summary,
        unique_summary=unique_summary,
        residual_summary=residual_summary,
        missing_summary=missing_summary,
        source_pool_summary=source_pool_summary,
    )
    summary = summarize(
        args=args,
        contract=contract,
        route_summary=route_summary,
        route_rows=route_rows,
        object_relation_summary=object_relation_summary,
        unique_summary=unique_summary,
        residual_summary=residual_summary,
        missing_summary=missing_summary,
        source_pool_summary=source_pool_summary,
        selection_rows=selection_rows,
    )
    write_jsonl(args.out_root / "next_label_free_evidence_family_after_object_relation_rows.jsonl", selection_rows)
    write_json(args.out_root / "next_label_free_evidence_family_after_object_relation_summary.json", summary)


if __name__ == "__main__":
    main()
