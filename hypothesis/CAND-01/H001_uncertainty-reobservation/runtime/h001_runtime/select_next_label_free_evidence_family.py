import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "h001.next_label_free_evidence_family.v1"
POLICY_NAME = "next_label_free_evidence_family_selector_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_next_label_free_evidence_family_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_next_label_free_evidence_family_v1"


FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
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


def count_request_branches(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for item in row.get("branch_count_items") or []:
            branch = str(item.get("branch_name") or "")
            if branch:
                counts[branch] += 1
    return dict(sorted(counts.items()))


def count_request_branch_candidates(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for item in row.get("branch_count_items") or []:
            branch = str(item.get("branch_name") or "")
            if branch:
                counts[branch] += safe_int(item.get("candidate_count"), 0)
    return dict(sorted(counts.items()))


def count_candidate_branches(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        for branch in row.get("candidate_branch_names") or []:
            counts[str(branch)] += 1
    return dict(sorted(counts.items()))


def count_preferred_candidate_branches(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    return dict(
        sorted(
            Counter(
                str(row.get("preferred_candidate_branch") or "")
                for row in rows
                if row.get("preferred_candidate_branch")
            ).items()
        )
    )


def count_preferred_candidate_actions(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    return dict(
        sorted(
            Counter(
                str(row.get("preferred_candidate_action") or "")
                for row in rows
                if row.get("preferred_candidate_action")
            ).items()
        )
    )


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


def build_selection_rows(
    *,
    contract: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    unique_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    decision = contract.get("selection_decision") or {}
    selected_branch = str(decision.get("selected_branch"))
    companion_branch = str(decision.get("companion_guard_branch"))
    request_branch_counts = count_request_branches(request_rows)
    request_branch_candidate_counts = count_request_branch_candidates(request_rows)
    candidate_branch_counts = count_candidate_branches(candidate_rows)
    preferred_branch_counts = count_preferred_candidate_branches(candidate_rows)
    preferred_action_counts = count_preferred_candidate_actions(candidate_rows)
    closed = decision.get("closed_or_deferred_branches") or {}
    all_branches = sorted(
        set(request_branch_counts)
        | set(candidate_branch_counts)
        | set(closed)
        | {selected_branch, companion_branch}
    )
    rows: List[Dict[str, Any]] = []
    for branch in all_branches:
        if branch == selected_branch:
            status = decision.get("selected_output_status")
            next_action = decision.get("selected_action")
            reason = "largest_remaining_active_observation_branch_with_preferred_missing_own_view_recheck"
        elif branch == companion_branch:
            status = decision.get("companion_guard_status")
            next_action = decision.get("companion_guard_action")
            reason = "paired_guard_branch_deferred_to_avoid_candidate_rejection_shortcut"
        elif branch == "unique_support_visibility_not_goal_validity":
            status = closed.get(branch)
            next_action = "none_branch_closed"
            reason = f"unique_support_closed_requests={safe_int(unique_summary.get('closed_request_rows'), 0)}"
        elif branch == "partial_relation_depth_true_goal":
            status = closed.get(branch)
            next_action = "none_branch_closed"
            reason = (
                "residual_branch_closure_promotable_rows="
                f"{safe_int(residual_summary.get('closure_promotable_rows'), 0)}"
            )
        else:
            status = closed.get(branch, "not_selected_for_immediate_next_family")
            next_action = "none_deferred"
            reason = "not_immediate_best_label_free_family_after_residual_closure"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_next_label_free_evidence_family_selection",
                "policy": POLICY_NAME,
                "branch_name": branch,
                "selection_status": status,
                "next_action": next_action,
                "selection_reason": reason,
                "request_rows_with_branch": safe_int(request_branch_counts.get(branch), 0),
                "candidate_rows_with_branch_from_request_counts": safe_int(
                    request_branch_candidate_counts.get(branch), 0
                ),
                "candidate_rows_with_branch": safe_int(candidate_branch_counts.get(branch), 0),
                "preferred_candidate_branch_rows": safe_int(preferred_branch_counts.get(branch), 0),
                "preferred_action_counts": preferred_action_counts,
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
    branch_summary: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    fresh_summary: Mapping[str, Any],
    unique_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    selection_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    decision = contract.get("selection_decision") or {}
    source_gate = contract.get("source_gate") or {}
    selected_branch = str(decision.get("selected_branch"))
    companion_branch = str(decision.get("companion_guard_branch"))
    request_branch_counts = count_request_branches(request_rows)
    request_branch_candidate_counts = count_request_branch_candidates(request_rows)
    candidate_branch_counts = count_candidate_branches(candidate_rows)
    preferred_branch_counts = count_preferred_candidate_branches(candidate_rows)
    selected_request_rows = safe_int(request_branch_counts.get(selected_branch), 0)
    selected_candidate_rows = safe_int(candidate_branch_counts.get(selected_branch), 0)
    selected_preferred_rows = safe_int(preferred_branch_counts.get(selected_branch), 0)
    terminal_commit_rows = sum(1 for row in selection_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in selection_rows if row.get("candidate_commit_allowed") is True)
    candidate_rejection_rows = sum(
        1 for row in selection_rows if row.get("candidate_rejection_allowed") is True
    )
    forbidden = action_forbidden_keys(selection_rows)
    gate = {
        "object_relation_branch_router_gate_passed": gate_value(
            branch_summary, "branch_evidence_router_gate_passed"
        )
        is source_gate.get("object_relation_branch_router_gate_passed"),
        "unique_support_branch_closure_gate_passed": gate_value(
            unique_summary, "unique_support_branch_closure_gate_passed"
        )
        is source_gate.get("unique_support_branch_closure_gate_passed"),
        "residual_branch_closure_gate_passed": gate_value(
            residual_summary, "residual_branch_closure_gate_passed"
        )
        is source_gate.get("residual_branch_closure_gate_passed"),
        "selected_request_rows_passed": selected_request_rows
        >= safe_int(decision.get("minimum_selected_request_rows"), 0),
        "selected_candidate_rows_passed": selected_candidate_rows
        >= safe_int(decision.get("minimum_selected_candidate_rows"), 0),
        "selected_preferred_action_rows_passed": selected_preferred_rows
        >= safe_int(decision.get("minimum_selected_preferred_action_rows"), 0),
        "remaining_request_branches_passed": {
            branch: safe_int(request_branch_counts.get(branch), 0) == safe_int(expected, 0)
            for branch, expected in (decision.get("expected_remaining_request_branches") or {}).items()
        },
        "remaining_candidate_branches_passed": {
            branch: safe_int(candidate_branch_counts.get(branch), 0) == safe_int(expected, 0)
            for branch, expected in (decision.get("expected_remaining_candidate_branches") or {}).items()
        },
        "companion_guard_same_candidate_rows_passed": selected_candidate_rows
        == safe_int(candidate_branch_counts.get(companion_branch), -1),
        "unique_support_closed_passed": safe_int(unique_summary.get("unclosed_unique_support_request_rows"), -1)
        == 0,
        "residual_closure_promotable_rows_passed": safe_int(
            residual_summary.get("closure_promotable_rows"), -1
        )
        == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": terminal_commit_rows
        <= safe_int(source_gate.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": candidate_commit_rows
        <= safe_int(source_gate.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": candidate_rejection_rows
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in selection_rows),
        "paper_claim_allowed": False,
    }
    nested_gate_values = []
    for key, value in gate.items():
        if key == "paper_claim_allowed":
            continue
        if isinstance(value, dict):
            nested_gate_values.extend(value.values())
        else:
            nested_gate_values.append(value)
    gate["next_label_free_evidence_family_selection_gate_passed"] = all(
        item is True for item in nested_gate_values if isinstance(item, bool)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": args.contract,
        "out_root": str(args.out_root),
        "source_files": {
            "object_relation_branch_summary": str(args.branch_summary),
            "object_relation_branch_request_rows": str(args.branch_request_rows),
            "object_relation_branch_candidate_rows": str(args.branch_candidate_rows),
            "fresh_arbitration_failure_summary": str(args.fresh_summary),
            "unique_support_branch_closure_summary": str(args.unique_summary),
            "residual_branch_closure_summary": str(args.residual_summary),
        },
        "selected_family": decision.get("selected_family"),
        "selected_branch": selected_branch,
        "selected_action": decision.get("selected_action"),
        "companion_guard_branch": companion_branch,
        "companion_guard_action": decision.get("companion_guard_action"),
        "request_branch_counts": request_branch_counts,
        "request_branch_candidate_counts": request_branch_candidate_counts,
        "candidate_branch_counts": candidate_branch_counts,
        "preferred_candidate_branch_counts": preferred_branch_counts,
        "fresh_request_failure_tag_counts": fresh_summary.get("request_failure_tag_counts") or {},
        "fresh_primary_failure_class_counts": fresh_summary.get("primary_failure_class_counts") or {},
        "unique_support_closed_request_rows": safe_int(unique_summary.get("closed_request_rows"), 0),
        "unique_support_unclosed_request_rows": safe_int(
            unique_summary.get("unclosed_unique_support_request_rows"), 0
        ),
        "residual_closure_rows": safe_int(residual_summary.get("closure_rows"), 0),
        "residual_closure_promotable_rows": safe_int(
            residual_summary.get("closure_promotable_rows"), 0
        ),
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
            "selected_branch": selected_branch,
            "selected_action": decision.get("selected_action"),
            "terminal_policy_allowed": False,
            "candidate_rejection_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": {
            "fact": (
                "The selected branch comes from existing branch rows and closure summaries; "
                "the selector writes no terminal commit or candidate rejection rows."
            ),
            "agent_inference": (
                "Missing own-view support is the best next label-free evidence family because it "
                "keeps the research on active observation utility, while the paired negative guard "
                "would otherwise become an unsupported rejection shortcut."
            ),
            "paper_claim": "No paper claim is allowed from this selection output alone.",
        },
        "output_files": {
            "selection_rows": "next_label_free_evidence_family_rows.jsonl",
            "summary": "next_label_free_evidence_family_summary.json",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--branch-summary")
    parser.add_argument("--branch-request-rows")
    parser.add_argument("--branch-candidate-rows")
    parser.add_argument("--fresh-summary")
    parser.add_argument("--unique-summary")
    parser.add_argument("--residual-summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(Path(args.contract))
    args.out_root = Path(args.out_root)
    args.branch_summary = source_path(args, contract, "branch_summary", "object_relation_branch_summary")
    args.branch_request_rows = source_path(
        args, contract, "branch_request_rows", "object_relation_branch_request_rows"
    )
    args.branch_candidate_rows = source_path(
        args, contract, "branch_candidate_rows", "object_relation_branch_candidate_rows"
    )
    args.fresh_summary = source_path(
        args, contract, "fresh_summary", "fresh_arbitration_failure_summary"
    )
    args.unique_summary = source_path(
        args, contract, "unique_summary", "unique_support_branch_closure_summary"
    )
    args.residual_summary = source_path(
        args, contract, "residual_summary", "residual_branch_closure_summary"
    )
    branch_summary = load_json(args.branch_summary)
    request_rows = load_jsonl(args.branch_request_rows)
    candidate_rows = load_jsonl(args.branch_candidate_rows)
    fresh_summary = load_json(args.fresh_summary)
    unique_summary = load_json(args.unique_summary)
    residual_summary = load_json(args.residual_summary)
    selection_rows = build_selection_rows(
        contract=contract,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        unique_summary=unique_summary,
        residual_summary=residual_summary,
    )
    summary = summarize(
        args=args,
        contract=contract,
        branch_summary=branch_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        fresh_summary=fresh_summary,
        unique_summary=unique_summary,
        residual_summary=residual_summary,
        selection_rows=selection_rows,
    )
    write_jsonl(args.out_root / "next_label_free_evidence_family_rows.jsonl", selection_rows)
    write_json(args.out_root / "next_label_free_evidence_family_summary.json", summary)


if __name__ == "__main__":
    main()
