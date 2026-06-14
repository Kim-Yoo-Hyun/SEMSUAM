import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "h001.instance_arbitration_pair_graph_branch_closure.v1"
POLICY_NAME = "instance_arbitration_pair_graph_branch_closure_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_instance_arbitration_pair_graph_branch_closure_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_pair_graph_branch_closure_v1"

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
    "evaluation_only_correct_candidate_count",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_wrong_candidate_count",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "is_correct",
    "oracle_action",
    "shortest_path_distance",
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


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


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


def prefixed_status(prefix: str, status: Any) -> str:
    text = str(status or "unknown")
    if text.startswith("closed_as_"):
        return text
    return f"{prefix}{text}"


def requested_outputs(contract: Mapping[str, Any]) -> Dict[str, str]:
    outputs = contract.get("expected_outputs") or {}
    return {
        "branch_status_rows": str(
            outputs.get("branch_status_rows", "instance_arbitration_pair_graph_branch_status_rows.jsonl")
        ),
        "request_closure_rows": str(
            outputs.get("request_closure_rows", "instance_arbitration_pair_graph_branch_request_rows.jsonl")
        ),
        "candidate_closure_rows": str(
            outputs.get("candidate_closure_rows", "instance_arbitration_pair_graph_branch_candidate_rows.jsonl")
        ),
        "pair_closure_rows": str(
            outputs.get("pair_closure_rows", "instance_arbitration_pair_graph_branch_pair_rows.jsonl")
        ),
        "shortcut_closure_rows": str(
            outputs.get("shortcut_closure_rows", "instance_arbitration_pair_graph_branch_shortcut_rows.jsonl")
        ),
        "summary": str(
            outputs.get("summary", "instance_arbitration_pair_graph_branch_closure_summary.json")
        ),
    }


def sort_request_id(request_id: Any) -> tuple[int, str]:
    text = str(request_id or "")
    tail = text.rsplit(":", 1)[-1]
    if tail.isdigit():
        return (safe_int(tail, 999999), text)
    return (999999, text)


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def row_candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("target_candidate_id") or "")


def build_branch_status_rows(
    *,
    contract: Mapping[str, Any],
    followup_summary: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    shortcut_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    scope = contract.get("closure_scope") or {}
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "action_instance_arbitration_pair_graph_branch_status_closure",
            "row_type": "branch_status",
            "policy": POLICY_NAME,
            "branch_family": scope.get("branch_family"),
            "closure_status": "closed_as_nonpromotable_shortcut_audit",
            "closure_reason": (
                "pair_graph_followup_has_zero_promotable_outcomes_and_all_shortcut_commit_or_rejection_rules_are_blocked"
            ),
            "request_graph_rows": len(request_rows),
            "candidate_graph_rows": len(candidate_rows),
            "pair_graph_rows": len(pair_rows),
            "shortcut_audit_rows": len(shortcut_rows),
            "candidate_graph_status_counts": followup_summary.get("candidate_graph_status_counts") or {},
            "pair_graph_status_counts": followup_summary.get("pair_graph_status_counts") or {},
            "request_graph_status_counts": followup_summary.get("request_graph_status_counts") or {},
            "shortcut_blocked_reason_counts": followup_summary.get("shortcut_blocked_reason_counts") or {},
            "promotable_branch_outcome_rows": 0,
            "terminal_commit": False,
            "candidate_commit": False,
            "candidate_rejection": False,
            "uses_gt_for_action": False,
            "terminal_utility_validation_allowed": False,
            "paper_claim_allowed": False,
        }
    ]


def build_request_closure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted(request_rows, key=lambda item: sort_request_id(row_request_id(item))):
        status = str(row.get("pair_graph_followup_status") or "unknown")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_instance_arbitration_pair_graph_request_closure",
                "row_type": "request_branch_closure",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_count": safe_int(row.get("candidate_count"), 0),
                "pair_count": safe_int(row.get("pair_count"), 0),
                "lossless_pair_graph_candidate_count": safe_int(
                    row.get("lossless_pair_graph_candidate_count"), 0
                ),
                "lossless_pair_graph_candidate_ids": list(row.get("lossless_pair_graph_candidate_ids") or []),
                "max_pair_win_candidate_count": safe_int(row.get("max_pair_win_candidate_count"), 0),
                "max_pair_win_candidate_ids": list(row.get("max_pair_win_candidate_ids") or []),
                "unique_lossless_pair_graph_candidate_id": row.get("unique_lossless_pair_graph_candidate_id"),
                "common_view_overlap_pair_count": safe_int(row.get("common_view_overlap_pair_count"), 0),
                "no_candidate_support_pair_count": safe_int(row.get("no_candidate_support_pair_count"), 0),
                "one_sided_nonterminal_pair_count": safe_int(row.get("one_sided_nonterminal_pair_count"), 0),
                "source_pair_graph_followup_status": status,
                "request_closure_status": prefixed_status("closed_as_", status),
                "closure_reason": "pair_graph_signal_is_nonpromotable_goal_validity_evidence",
                "recommended_nonterminal_action": "close_instance_arbitration_pair_graph_request_as_nonterminal",
                "promotable_terminal_outcome": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_candidate_closure_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        candidate_rows,
        key=lambda item: (sort_request_id(row_request_id(item)), row_candidate_id(item)),
    ):
        status = str(row.get("pair_graph_consistency_status") or "unknown")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_instance_arbitration_pair_graph_candidate_closure",
                "row_type": "candidate_branch_closure",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": row_candidate_id(row),
                "source_candidate_evidence_status": row.get("source_candidate_evidence_status"),
                "source_residual_failure_class": row.get("residual_failure_class"),
                "source_pair_graph_consistency_status": status,
                "candidate_closure_status": prefixed_status("closed_as_", status),
                "closure_reason": "candidate_pair_graph_state_is_nonpromotable_shortcut_evidence",
                "source_top_candidate": row.get("source_top_candidate") is True,
                "strong_own_view_candidate": row.get("strong_own_view_candidate") is True,
                "detector_strong_candidate": row.get("detector_strong_candidate") is True,
                "local_context_candidate": row.get("local_context_candidate") is True,
                "is_lossless_pair_graph_candidate": row.get("is_lossless_pair_graph_candidate") is True,
                "is_max_pair_win_candidate": row.get("is_max_pair_win_candidate") is True,
                "pair_graph_win_count": safe_int(row.get("pair_graph_win_count"), 0),
                "pair_graph_loss_count": safe_int(row.get("pair_graph_loss_count"), 0),
                "ambiguous_pair_incident_count": safe_int(row.get("ambiguous_pair_incident_count"), 0),
                "has_common_view_overlap_incident": row.get("has_common_view_overlap_incident") is True,
                "has_no_candidate_support_incident": row.get("has_no_candidate_support_incident") is True,
                "has_rival_leakage": row.get("has_rival_leakage") is True,
                "has_pair_or_contrast_contradiction": row.get("has_pair_or_contrast_contradiction") is True,
                "recommended_nonterminal_action": "close_instance_arbitration_pair_graph_candidate_as_nonterminal",
                "promotable_terminal_outcome": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_pair_closure_rows(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        pair_rows,
        key=lambda item: (
            sort_request_id(row_request_id(item)),
            str(item.get("candidate_a_id") or item.get("candidate_id_a") or ""),
            str(item.get("candidate_b_id") or item.get("candidate_id_b") or ""),
        ),
    ):
        status = str(row.get("pair_graph_status") or row.get("pair_graph_consistency_status") or "unknown")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_instance_arbitration_pair_graph_pair_closure",
                "row_type": "pair_branch_closure",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_a_id": row.get("candidate_a_id") or row.get("candidate_id_a"),
                "candidate_b_id": row.get("candidate_b_id") or row.get("candidate_id_b"),
                "source_pair_graph_status": status,
                "pair_closure_status": prefixed_status("closed_as_", status),
                "closure_reason": "pair_relation_does_not_authorize_candidate_commit_or_rejection",
                "pair_graph_winner_candidate_id": row.get("pair_graph_winner_candidate_id"),
                "common_view_overlap": row.get("common_view_overlap") is True
                or str(row.get("pair_probe_type") or "") == "pair_common_view",
                "candidate_a_supported": row.get("candidate_a_supported") is True
                or safe_int(row.get("candidate_a_support_count"), 0) > 0,
                "candidate_b_supported": row.get("candidate_b_supported") is True
                or safe_int(row.get("candidate_b_support_count"), 0) > 0,
                "recommended_nonterminal_action": "close_instance_arbitration_pair_graph_pair_as_nonterminal",
                "promotable_terminal_outcome": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_shortcut_closure_rows(shortcut_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        shortcut_rows,
        key=lambda item: (
            sort_request_id(row_request_id(item)),
            str(item.get("shortcut_rule") or item.get("shortcut_rule_name") or ""),
            row_candidate_id(item),
        ),
    ):
        blocked_reason = str(
            row.get("shortcut_blocked_reason") or row.get("shortcut_rule_blocked_reason") or "unknown"
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_instance_arbitration_pair_graph_shortcut_closure",
                "row_type": "shortcut_branch_closure",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": row_candidate_id(row),
                "shortcut_rule": row.get("shortcut_rule") or row.get("shortcut_rule_name"),
                "shortcut_would_select": row.get("shortcut_would_select") is True
                or row.get("shortcut_rule_would_select_candidate") is True,
                "source_shortcut_blocked_reason": blocked_reason,
                "shortcut_closure_status": prefixed_status("closed_as_", blocked_reason),
                "closure_reason": "shortcut_rule_is_not_allowed_to_commit_or_reject_without_goal_validity_evidence",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    followup_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    selector_summary: Mapping[str, Any],
    branch_status_rows: Sequence[Mapping[str, Any]],
    request_closure_rows: Sequence[Mapping[str, Any]],
    candidate_closure_rows: Sequence[Mapping[str, Any]],
    pair_closure_rows: Sequence[Mapping[str, Any]],
    shortcut_closure_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    source_gate = contract.get("source_gate") or {}
    scope = contract.get("closure_scope") or {}
    action_rows = [
        *branch_status_rows,
        *request_closure_rows,
        *candidate_closure_rows,
        *pair_closure_rows,
        *shortcut_closure_rows,
    ]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commit_rows = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejection_rows = [row for row in action_rows if row.get("candidate_rejection") is True]
    promotable_rows = [row for row in action_rows if row.get("promotable_terminal_outcome") is True]

    request_status_counts = compact_counter(row.get("request_closure_status") for row in request_closure_rows)
    candidate_status_counts = compact_counter(row.get("candidate_closure_status") for row in candidate_closure_rows)
    pair_status_counts = compact_counter(row.get("pair_closure_status") for row in pair_closure_rows)
    shortcut_reason_counts = compact_counter(
        row.get("source_shortcut_blocked_reason") for row in shortcut_closure_rows
    )

    gate = {
        "pair_graph_consistency_followup_gate_passed": gate_value(
            followup_summary, "pair_graph_consistency_followup_gate_passed"
        )
        is source_gate.get("pair_graph_consistency_followup_gate_passed"),
        "source_residual_diagnostic_gate_passed": gate_value(
            followup_summary, "source_residual_diagnostic_gate_passed"
        )
        is source_gate.get("source_residual_diagnostic_gate_passed"),
        "expected_candidate_graph_rows_passed": len(candidate_closure_rows)
        == safe_int(source_gate.get("expected_candidate_graph_rows"), -1),
        "expected_pair_graph_rows_passed": len(pair_closure_rows)
        == safe_int(source_gate.get("expected_pair_graph_rows"), -1),
        "expected_request_graph_rows_passed": len(request_closure_rows)
        == safe_int(source_gate.get("expected_request_graph_rows"), -1),
        "expected_shortcut_audit_rows_passed": len(shortcut_closure_rows)
        == safe_int(source_gate.get("expected_shortcut_audit_rows"), -1),
        "expected_branch_status_rows_passed": len(branch_status_rows)
        == safe_int(scope.get("expected_branch_status_rows"), -1),
        "expected_request_closure_status_counts_passed": request_status_counts
        == dict(scope.get("expected_request_closure_status_counts") or {}),
        "expected_candidate_closure_status_counts_passed": candidate_status_counts
        == dict(scope.get("expected_candidate_closure_status_counts") or {}),
        "expected_pair_closure_status_counts_passed": pair_status_counts
        == dict(scope.get("expected_pair_closure_status_counts") or {}),
        "expected_shortcut_blocked_reason_counts_passed": shortcut_reason_counts
        == dict(scope.get("expected_shortcut_blocked_reason_counts") or {}),
        "expected_lossless_candidate_membership_rows_passed": safe_int(
            followup_summary.get("lossless_candidate_membership_rows"), 0
        )
        == safe_int(source_gate.get("expected_lossless_candidate_membership_rows"), -1),
        "expected_max_pair_winner_candidate_membership_rows_passed": safe_int(
            followup_summary.get("max_pair_winner_candidate_membership_rows"), 0
        )
        == safe_int(source_gate.get("expected_max_pair_winner_candidate_membership_rows"), -1),
        "expected_unique_lossless_request_rows_passed": safe_int(
            followup_summary.get("unique_lossless_request_rows"), 0
        )
        == safe_int(source_gate.get("expected_unique_lossless_request_rows"), -1),
        "expected_multiple_lossless_request_rows_passed": safe_int(
            followup_summary.get("multiple_lossless_request_rows"), 0
        )
        == safe_int(source_gate.get("expected_multiple_lossless_request_rows"), -1),
        "expected_promotable_branch_outcome_rows_passed": len(promotable_rows)
        == safe_int(source_gate.get("expected_promotable_branch_outcome_rows"), -1),
        "terminal_commit_rows_passed": len(terminal_rows)
        == safe_int(source_gate.get("expected_terminal_commit_rows"), -1),
        "candidate_commit_rows_passed": len(candidate_commit_rows)
        == safe_int(source_gate.get("expected_candidate_commit_rows"), -1),
        "candidate_rejection_rows_passed": len(candidate_rejection_rows)
        == safe_int(source_gate.get("expected_candidate_rejection_rows"), -1),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), -1),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows)
        and source_gate.get("requires_uses_gt_for_action") is False,
        "paper_claim_allowed": False,
    }
    gate["instance_arbitration_pair_graph_branch_closure_gate_passed"] = all(
        value is True for key, value in gate.items() if key.endswith("_passed")
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "pair_graph_followup_summary": str(args.pair_graph_followup_summary),
            "pair_graph_candidate_rows": str(args.pair_graph_candidate_rows),
            "pair_graph_pair_rows": str(args.pair_graph_pair_rows),
            "pair_graph_request_rows": str(args.pair_graph_request_rows),
            "pair_graph_shortcut_audit_rows": str(args.pair_graph_shortcut_audit_rows),
            "instance_arbitration_residual_summary": str(args.instance_arbitration_residual_summary),
            "post_object_relation_selector_summary": str(args.post_object_relation_selector_summary),
        },
        "context_gates": {
            "residual_diagnostic_gate_passed": gate_value(
                residual_summary, "instance_arbitration_residual_diagnostic_gate_passed"
            )
            or gate_value(residual_summary, "residual_diagnostic_gate_passed"),
            "post_object_relation_selector_gate_passed": gate_value(
                selector_summary, "next_evidence_family_after_object_relation_selector_gate_passed"
            )
            or gate_value(selector_summary, "selection_gate_passed"),
        },
        "branch_family": (contract.get("closure_scope") or {}).get("branch_family"),
        "branch_status_rows": len(branch_status_rows),
        "request_closure_rows": len(request_closure_rows),
        "candidate_closure_rows": len(candidate_closure_rows),
        "pair_closure_rows": len(pair_closure_rows),
        "shortcut_closure_rows": len(shortcut_closure_rows),
        "request_closure_status_counts": request_status_counts,
        "candidate_closure_status_counts": candidate_status_counts,
        "pair_closure_status_counts": pair_status_counts,
        "shortcut_blocked_reason_counts": shortcut_reason_counts,
        "source_shortcut_rule_would_select_counts": followup_summary.get("shortcut_rule_would_select_counts") or {},
        "lossless_candidate_membership_rows": safe_int(
            followup_summary.get("lossless_candidate_membership_rows"), 0
        ),
        "max_pair_winner_candidate_membership_rows": safe_int(
            followup_summary.get("max_pair_winner_candidate_membership_rows"), 0
        ),
        "unique_lossless_request_rows": safe_int(followup_summary.get("unique_lossless_request_rows"), 0),
        "multiple_lossless_request_rows": safe_int(
            followup_summary.get("multiple_lossless_request_rows"), 0
        ),
        "promotable_branch_outcome_rows": len(promotable_rows),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commit_rows),
        "candidate_rejection_rows": len(candidate_rejection_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "instance_arbitration_pair_graph_branch_closed": gate[
                "instance_arbitration_pair_graph_branch_closure_gate_passed"
            ],
            "recommended_next_task": (
                "select_next_label_free_evidence_family_after_instance_arbitration_pair_graph_closure"
                if gate["instance_arbitration_pair_graph_branch_closure_gate_passed"]
                else "diagnose_instance_arbitration_pair_graph_branch_closure_mismatch"
            ),
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "blocked_actions": list(contract.get("blocked_actions") or []),
        "output_files": {
            key: str(Path(str(args.out_root)) / value)
            for key, value in requested_outputs(contract).items()
        },
        "interpretation": {
            "fact": "The closure analyzer writes branch, request, candidate, pair, and shortcut closure rows from the Docker-verified pair-graph follow-up output.",
            "agent_inference": "Pair-graph evidence is now closed as terminal-blocking shortcut taxonomy, not as ObjectNav goal-validity utility.",
            "paper_claim": "No paper claim is allowed from this analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.pair_graph_followup_summary = source_path(
        args, contract, "pair_graph_followup_summary", "pair_graph_followup_summary"
    )
    args.pair_graph_candidate_rows = source_path(
        args, contract, "pair_graph_candidate_rows", "pair_graph_candidate_rows"
    )
    args.pair_graph_pair_rows = source_path(args, contract, "pair_graph_pair_rows", "pair_graph_pair_rows")
    args.pair_graph_request_rows = source_path(
        args, contract, "pair_graph_request_rows", "pair_graph_request_rows"
    )
    args.pair_graph_shortcut_audit_rows = source_path(
        args, contract, "pair_graph_shortcut_audit_rows", "pair_graph_shortcut_audit_rows"
    )
    args.instance_arbitration_residual_summary = source_path(
        args,
        contract,
        "instance_arbitration_residual_summary",
        "instance_arbitration_residual_summary",
    )
    args.post_object_relation_selector_summary = source_path(
        args,
        contract,
        "post_object_relation_selector_summary",
        "post_object_relation_selector_summary",
    )

    followup_summary = load_json(args.pair_graph_followup_summary)
    candidate_rows = load_jsonl(args.pair_graph_candidate_rows)
    pair_rows = load_jsonl(args.pair_graph_pair_rows)
    request_rows = load_jsonl(args.pair_graph_request_rows)
    shortcut_rows = load_jsonl(args.pair_graph_shortcut_audit_rows)
    residual_summary = load_json(args.instance_arbitration_residual_summary)
    selector_summary = load_json(args.post_object_relation_selector_summary)

    branch_status_rows = build_branch_status_rows(
        contract=contract,
        followup_summary=followup_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        shortcut_rows=shortcut_rows,
    )
    request_closure_rows = build_request_closure_rows(request_rows)
    candidate_closure_rows = build_candidate_closure_rows(candidate_rows)
    pair_closure_rows = build_pair_closure_rows(pair_rows)
    shortcut_closure_rows = build_shortcut_closure_rows(shortcut_rows)
    summary = build_summary(
        args=args,
        contract=contract,
        followup_summary=followup_summary,
        residual_summary=residual_summary,
        selector_summary=selector_summary,
        branch_status_rows=branch_status_rows,
        request_closure_rows=request_closure_rows,
        candidate_closure_rows=candidate_closure_rows,
        pair_closure_rows=pair_closure_rows,
        shortcut_closure_rows=shortcut_closure_rows,
    )

    out_root = Path(args.out_root)
    outputs = requested_outputs(contract)
    write_jsonl(out_root / outputs["branch_status_rows"], branch_status_rows)
    write_jsonl(out_root / outputs["request_closure_rows"], request_closure_rows)
    write_jsonl(out_root / outputs["candidate_closure_rows"], candidate_closure_rows)
    write_jsonl(out_root / outputs["pair_closure_rows"], pair_closure_rows)
    write_jsonl(out_root / outputs["shortcut_closure_rows"], shortcut_closure_rows)
    write_json(out_root / outputs["summary"], summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Close nonpromotable instance-arbitration pair-graph branch evidence."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--pair-graph-followup-summary")
    parser.add_argument("--pair-graph-candidate-rows")
    parser.add_argument("--pair-graph-pair-rows")
    parser.add_argument("--pair-graph-request-rows")
    parser.add_argument("--pair-graph-shortcut-audit-rows")
    parser.add_argument("--instance-arbitration-residual-summary")
    parser.add_argument("--post-object-relation-selector-summary")
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(
        json.dumps(
            {
                "gate": summary["gate"]["instance_arbitration_pair_graph_branch_closure_gate_passed"],
                "branch_status_rows": summary["branch_status_rows"],
                "request_closure_rows": summary["request_closure_rows"],
                "candidate_closure_rows": summary["candidate_closure_rows"],
                "pair_closure_rows": summary["pair_closure_rows"],
                "shortcut_closure_rows": summary["shortcut_closure_rows"],
                "promotable_branch_outcome_rows": summary["promotable_branch_outcome_rows"],
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
    if not summary["gate"]["instance_arbitration_pair_graph_branch_closure_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
