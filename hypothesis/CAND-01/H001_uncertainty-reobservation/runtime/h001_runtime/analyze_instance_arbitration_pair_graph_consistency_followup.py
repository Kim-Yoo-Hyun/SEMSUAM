import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.instance_arbitration_pair_graph_consistency_followup.v1"
POLICY_NAME = "pair_graph_consistency_followup_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_instance_arbitration_pair_graph_consistency_followup_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_pair_graph_consistency_followup_v1"

SHORTCUT_RULES = (
    "graph_winner_commit",
    "lossless_candidate_commit",
    "max_pair_win_count_commit",
    "source_top_lossless_commit",
    "detector_strong_lossless_commit",
    "reject_candidate_with_pair_loss",
    "defer_all_pair_graph_rows",
)


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


def row_request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def row_candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def candidate_sort_key(candidate_id: Any) -> Tuple[str, int, str]:
    text = str(candidate_id or "")
    head, _, tail = text.rpartition(":")
    return head, safe_int(tail, 999999), text


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[str, List[Mapping[str, Any]]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(row)
    return grouped


def pair_graph(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("pair_graph")
    return value if isinstance(value, Mapping) else {}


def graph_counts(request_row: Mapping[str, Any], candidate_id: str) -> Dict[str, int]:
    graph = pair_graph(request_row)
    wins = graph.get("win_counts") if isinstance(graph.get("win_counts"), Mapping) else {}
    losses = graph.get("loss_counts") if isinstance(graph.get("loss_counts"), Mapping) else {}
    ambiguous = (
        graph.get("ambiguous_pair_incident_counts")
        if isinstance(graph.get("ambiguous_pair_incident_counts"), Mapping)
        else {}
    )
    return {
        "wins": safe_int(wins.get(candidate_id), 0),
        "losses": safe_int(losses.get(candidate_id), 0),
        "ambiguous": safe_int(ambiguous.get(candidate_id), 0),
    }


def graph_list(request_row: Mapping[str, Any], key: str) -> List[str]:
    value = pair_graph(request_row).get(key)
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def pair_involves(row: Mapping[str, Any], candidate_id: str) -> bool:
    return str(row.get("candidate_id_a") or "") == candidate_id or str(row.get("candidate_id_b") or "") == candidate_id


def involving_pairs(
    pair_rows: Sequence[Mapping[str, Any]], candidate_id: str, residual_class: Optional[str] = None
) -> List[Mapping[str, Any]]:
    rows = [row for row in pair_rows if pair_involves(row, candidate_id)]
    if residual_class is not None:
        rows = [row for row in rows if str(row.get("residual_failure_class") or "") == residual_class]
    return rows


def has_pair_class(pair_rows: Sequence[Mapping[str, Any]], candidate_id: str, residual_class: str) -> bool:
    return bool(involving_pairs(pair_rows, candidate_id, residual_class))


def has_pair_leakage(pair_rows: Sequence[Mapping[str, Any]], candidate_id: str) -> bool:
    for row in pair_rows:
        if str(row.get("candidate_id_a") or "") == candidate_id and safe_int(row.get("candidate_a_leakage_count"), 0) > 0:
            return True
        if str(row.get("candidate_id_b") or "") == candidate_id and safe_int(row.get("candidate_b_leakage_count"), 0) > 0:
            return True
    return False


def independent_non_source_top_support(candidate_row: Mapping[str, Any]) -> bool:
    if candidate_row.get("own_view_support") is True and candidate_row.get("source_top_candidate") is not True:
        return True
    if candidate_row.get("local_context_contrast_support") is True:
        return True
    if safe_int(candidate_row.get("pair_support_count"), 0) > 0:
        return True
    return False


def candidate_status(
    *,
    candidate_row: Mapping[str, Any],
    request_row: Mapping[str, Any],
    request_pair_rows: Sequence[Mapping[str, Any]],
) -> Tuple[str, str, bool]:
    candidate_id = row_candidate_id(candidate_row)
    lossless_ids = set(graph_list(request_row, "lossless_pair_graph_candidate_ids"))
    max_win_ids = set(graph_list(request_row, "max_pair_win_candidate_ids"))
    lossless_count = safe_int(pair_graph(request_row).get("lossless_pair_graph_candidate_count"), 0)
    common_overlap = has_pair_class(request_pair_rows, candidate_id, "common_view_both_candidates_supported")
    rival_leakage = safe_int(candidate_row.get("rival_leakage_count"), 0) > 0 or has_pair_leakage(
        request_pair_rows, candidate_id
    )
    contradiction = (
        str(candidate_row.get("residual_failure_class") or "") == "pair_or_contrast_contradiction"
        or safe_int(candidate_row.get("pair_contradiction_count"), 0) > 0
    )
    independent_support = independent_non_source_top_support(candidate_row)
    is_lossless = candidate_id in lossless_ids
    is_max = candidate_id in max_win_ids

    if (
        is_lossless
        and lossless_count == 1
        and not common_overlap
        and not rival_leakage
        and not contradiction
        and independent_support
    ):
        return (
            "pair_graph_consistency_promotable_for_later_terminal_contract",
            "promote_pair_graph_consistency_for_later_terminal_contract_only",
            True,
        )
    if is_lossless and lossless_count > 1:
        return "lossless_but_multiple_graph_candidates", "keep_multiple_lossless_pair_graph_candidates_unresolved", False
    if is_lossless and common_overlap:
        return "lossless_blocked_by_common_view_overlap", "request_common_view_overlap_audit", False
    if is_lossless and (rival_leakage or contradiction):
        return "lossless_blocked_by_residual_conflict", "block_lossless_candidate_shortcut", False
    if is_max and not is_lossless:
        return "max_pair_win_nonterminal_due_pair_losses", "block_max_pair_win_candidate_shortcut", False
    if contradiction:
        return "pair_or_contrast_contradiction_nonterminal", "route_to_pair_graph_contradiction_audit", False
    if rival_leakage:
        return "rival_leakage_nonterminal", "route_to_pair_graph_consistency_audit", False
    return "non_graph_candidate_unresolved", "defer_candidate_pair_graph_audit", False


def build_candidate_graph_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    pairs_by_request = group_by_request(pair_rows)
    requests_by_id = {row_request_id(row): row for row in request_rows}
    output: List[Dict[str, Any]] = []
    for row in sorted(
        candidate_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            candidate_sort_key(row_candidate_id(item)),
        ),
    ):
        request_id = row_request_id(row)
        candidate_id = row_candidate_id(row)
        request_row = requests_by_id.get(request_id, {})
        request_pair_rows = pairs_by_request.get(request_id, [])
        counts = graph_counts(request_row, candidate_id)
        lossless_ids = set(graph_list(request_row, "lossless_pair_graph_candidate_ids"))
        max_win_ids = set(graph_list(request_row, "max_pair_win_candidate_ids"))
        common_overlap = has_pair_class(request_pair_rows, candidate_id, "common_view_both_candidates_supported")
        no_support_incident = bool(
            involving_pairs(request_pair_rows, candidate_id, "common_view_no_candidate_support")
            or involving_pairs(request_pair_rows, candidate_id, "dual_standoff_no_candidate_support")
        )
        rival_leakage = safe_int(row.get("rival_leakage_count"), 0) > 0 or has_pair_leakage(
            request_pair_rows, candidate_id
        )
        contradiction = (
            str(row.get("residual_failure_class") or "") == "pair_or_contrast_contradiction"
            or safe_int(row.get("pair_contradiction_count"), 0) > 0
        )
        status, action, promotable = candidate_status(
            candidate_row=row,
            request_row=request_row,
            request_pair_rows=request_pair_rows,
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "candidate_graph",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id") or request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": candidate_id,
                "residual_failure_class": row.get("residual_failure_class"),
                "source_candidate_evidence_status": row.get("source_candidate_evidence_status"),
                "pair_graph_loss_count": counts["losses"],
                "pair_graph_win_count": counts["wins"],
                "ambiguous_pair_incident_count": counts["ambiguous"],
                "is_lossless_pair_graph_candidate": candidate_id in lossless_ids,
                "is_max_pair_win_candidate": candidate_id in max_win_ids,
                "has_common_view_overlap_incident": common_overlap,
                "has_no_candidate_support_incident": no_support_incident,
                "has_rival_leakage": rival_leakage,
                "has_pair_or_contrast_contradiction": contradiction,
                "has_independent_non_source_top_support": independent_non_source_top_support(row),
                "source_top_candidate": row.get("source_top_candidate") is True,
                "strong_own_view_candidate": row.get("strong_own_view_candidate") is True,
                "detector_strong_candidate": row.get("detector_strong_candidate") is True,
                "local_context_candidate": row.get("local_context_candidate") is True,
                "pair_graph_consistency_status": status,
                "promotable_branch_outcome": promotable,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def pair_graph_status(row: Mapping[str, Any]) -> Tuple[str, str]:
    residual = str(row.get("residual_failure_class") or "")
    winner = str(row.get("pair_graph_winner_candidate_id") or "")
    if residual == "common_view_both_candidates_supported":
        return "common_view_overlap_blocks_pair_resolution", "audit_common_view_overlap_pair"
    if residual in {"common_view_no_candidate_support", "dual_standoff_no_candidate_support"}:
        return "no_candidate_support_blocks_pair_resolution", "audit_pair_no_support"
    if residual == "one_sided_pair_support_with_leakage":
        return "one_sided_support_with_leakage_nonterminal", "block_one_sided_pair_support_shortcut"
    if residual == "one_sided_pair_support_nonterminal" and winner:
        return "one_sided_support_nonterminal_graph_edge", "keep_pair_graph_edge_nonterminal"
    return "pair_graph_unresolved", "defer_pair_graph_manual_review"


def build_pair_graph_rows(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sorted(
        pair_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("request_pair_index"), 999999),
            candidate_sort_key(item.get("candidate_id_a")),
            candidate_sort_key(item.get("candidate_id_b")),
        ),
    ):
        status, action = pair_graph_status(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "pair_graph",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "pair_index": row.get("pair_index"),
                "request_pair_index": row.get("request_pair_index"),
                "candidate_id_a": row.get("candidate_id_a"),
                "candidate_id_b": row.get("candidate_id_b"),
                "pair_probe_type": row.get("pair_probe_type"),
                "residual_failure_class": row.get("residual_failure_class"),
                "source_pair_evidence_status": row.get("source_pair_evidence_status"),
                "pair_graph_winner_candidate_id": row.get("pair_graph_winner_candidate_id"),
                "candidate_a_support_count": safe_int(row.get("candidate_a_support_count"), 0),
                "candidate_b_support_count": safe_int(row.get("candidate_b_support_count"), 0),
                "candidate_a_leakage_count": safe_int(row.get("candidate_a_leakage_count"), 0),
                "candidate_b_leakage_count": safe_int(row.get("candidate_b_leakage_count"), 0),
                "pair_graph_consistency_status": status,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def request_graph_status(
    request_row: Mapping[str, Any],
    request_candidate_rows: Sequence[Mapping[str, Any]],
    request_pair_rows: Sequence[Mapping[str, Any]],
) -> Tuple[str, str, int]:
    graph = pair_graph(request_row)
    lossless_count = safe_int(graph.get("lossless_pair_graph_candidate_count"), 0)
    common_overlap = sum(
        1
        for row in request_pair_rows
        if str(row.get("residual_failure_class") or "") == "common_view_both_candidates_supported"
    )
    no_support = sum(
        1
        for row in request_pair_rows
        if str(row.get("residual_failure_class") or "")
        in {"common_view_no_candidate_support", "dual_standoff_no_candidate_support"}
    )
    one_sided = sum(
        1
        for row in request_pair_rows
        if str(row.get("residual_failure_class") or "")
        in {"one_sided_pair_support_nonterminal", "one_sided_pair_support_with_leakage"}
    )
    promotable = sum(1 for row in request_candidate_rows if row.get("promotable_branch_outcome") is True)
    if promotable:
        return "pair_graph_consistency_promotable_for_later_terminal_contract", (
            "freeze_terminal_utility_contract_after_separate_review"
        ), promotable
    if lossless_count > 1:
        return "multiple_lossless_pair_graph_candidates_unresolved", (
            "keep_multiple_lossless_pair_graph_candidates_unresolved"
        ), 0
    if lossless_count == 1 and common_overlap:
        return "unique_lossless_candidate_blocked_by_common_view_overlap", (
            "request_common_view_overlap_audit"
        ), 0
    if lossless_count == 1 and no_support:
        return "unique_lossless_candidate_blocked_by_no_support_pairs", "audit_pair_no_support", 0
    if one_sided:
        return "one_sided_graph_edges_nonterminal", "keep_pair_graph_edge_nonterminal", 0
    return "pair_graph_unresolved_manual_review", "defer_pair_graph_manual_review", 0


def build_request_graph_rows(
    request_rows: Sequence[Mapping[str, Any]],
    candidate_graph_rows: Sequence[Mapping[str, Any]],
    pair_graph_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    candidates_by_request = group_by_request(candidate_graph_rows)
    pairs_by_request = group_by_request(pair_graph_rows)
    output: List[Dict[str, Any]] = []
    for row in sorted(request_rows, key=lambda item: request_sort_key(row_request_id(item))):
        request_id = row_request_id(row)
        request_candidate_rows = candidates_by_request.get(request_id, [])
        request_pair_rows = pairs_by_request.get(request_id, [])
        graph = pair_graph(row)
        lossless_ids = graph_list(row, "lossless_pair_graph_candidate_ids")
        max_win_ids = graph_list(row, "max_pair_win_candidate_ids")
        common_overlap = sum(
            1
            for item in request_pair_rows
            if str(item.get("residual_failure_class") or "") == "common_view_both_candidates_supported"
        )
        no_support = sum(
            1
            for item in request_pair_rows
            if str(item.get("residual_failure_class") or "")
            in {"common_view_no_candidate_support", "dual_standoff_no_candidate_support"}
        )
        one_sided = sum(
            1
            for item in request_pair_rows
            if str(item.get("residual_failure_class") or "")
            in {"one_sided_pair_support_nonterminal", "one_sided_pair_support_with_leakage"}
        )
        status, action, promotable = request_graph_status(row, request_candidate_rows, request_pair_rows)
        lossless_count = safe_int(graph.get("lossless_pair_graph_candidate_count"), 0)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "request_graph",
                "policy": POLICY_NAME,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id") or request_id,
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_count": safe_int(row.get("candidate_count"), len(request_candidate_rows)),
                "pair_count": safe_int(row.get("pair_count"), len(request_pair_rows)),
                "lossless_pair_graph_candidate_count": lossless_count,
                "lossless_pair_graph_candidate_ids": lossless_ids,
                "max_pair_win_candidate_count": len(max_win_ids),
                "max_pair_win_candidate_ids": max_win_ids,
                "unique_lossless_pair_graph_candidate_id": graph.get("unique_lossless_pair_graph_candidate_id"),
                "multiple_lossless_pair_graph_candidate_count": lossless_count if lossless_count > 1 else 0,
                "common_view_overlap_pair_count": common_overlap,
                "no_candidate_support_pair_count": no_support,
                "one_sided_nonterminal_pair_count": one_sided,
                "pair_graph_followup_status": status,
                "promotable_branch_outcome_count": promotable,
                "recommended_nonterminal_action": action,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "terminal_utility_validation_allowed": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def shortcut_would_select(rule: str, row: Mapping[str, Any]) -> bool:
    if rule == "graph_winner_commit":
        return row.get("is_max_pair_win_candidate") is True
    if rule == "lossless_candidate_commit":
        return row.get("is_lossless_pair_graph_candidate") is True
    if rule == "max_pair_win_count_commit":
        return row.get("is_max_pair_win_candidate") is True
    if rule == "source_top_lossless_commit":
        return row.get("is_lossless_pair_graph_candidate") is True and row.get("source_top_candidate") is True
    if rule == "detector_strong_lossless_commit":
        return row.get("is_lossless_pair_graph_candidate") is True and row.get("detector_strong_candidate") is True
    if rule == "reject_candidate_with_pair_loss":
        return safe_int(row.get("pair_graph_loss_count"), 0) > 0
    return False


def shortcut_blocked_reason(rule: str, row: Mapping[str, Any], request_row: Mapping[str, Any]) -> str:
    if rule == "defer_all_pair_graph_rows":
        return "defer_all_is_control_baseline_not_utility_evidence"
    if not shortcut_would_select(rule, row):
        return "shortcut_rule_not_applicable_to_candidate"
    if rule == "reject_candidate_with_pair_loss":
        return "candidate_rejection_by_pair_loss_forbidden_without_goal_validity_evidence"
    if safe_int(request_row.get("lossless_pair_graph_candidate_count"), 0) > 1:
        return "multiple_lossless_pair_graph_candidates_block_shortcut_commit"
    if row.get("has_common_view_overlap_incident") is True:
        return "common_view_overlap_blocks_shortcut_commit"
    if row.get("has_rival_leakage") is True:
        return "rival_leakage_blocks_shortcut_commit"
    if row.get("has_pair_or_contrast_contradiction") is True:
        return "pair_or_contrast_contradiction_blocks_shortcut_commit"
    if row.get("has_independent_non_source_top_support") is not True:
        return "independent_non_source_top_support_missing"
    return "terminal_commit_forbidden_by_contract"


def build_shortcut_audit_rows(
    candidate_graph_rows: Sequence[Mapping[str, Any]],
    request_graph_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    requests_by_id = {row_request_id(row): row for row in request_graph_rows}
    output: List[Dict[str, Any]] = []
    for candidate_row in sorted(
        candidate_graph_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            candidate_sort_key(row_candidate_id(item)),
        ),
    ):
        request_id = row_request_id(candidate_row)
        request_row = requests_by_id.get(request_id, {})
        for rule in SHORTCUT_RULES:
            would_select = shortcut_would_select(rule, candidate_row)
            output.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "row_type": "shortcut_audit",
                    "policy": POLICY_NAME,
                    "expanded_retrieval_request_id": request_id,
                    "rival_identity_request_id": candidate_row.get("rival_identity_request_id") or request_id,
                    "episode_key": candidate_row.get("episode_key"),
                    "scene_key": candidate_row.get("scene_key"),
                    "query": candidate_row.get("query"),
                    "candidate_id": row_candidate_id(candidate_row),
                    "shortcut_rule_name": rule,
                    "shortcut_rule_would_select_candidate": would_select,
                    "shortcut_rule_blocked_reason": shortcut_blocked_reason(rule, candidate_row, request_row),
                    "terminal_commit": False,
                    "candidate_commit": False,
                    "candidate_rejection": False,
                    "uses_gt_for_action": False,
                    "terminal_utility_validation_allowed": False,
                    "paper_claim_allowed": False,
                }
            )
    return output


def build_summary(
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    source_summary: Mapping[str, Any],
    candidate_graph_rows: Sequence[Mapping[str, Any]],
    pair_graph_rows: Sequence[Mapping[str, Any]],
    request_graph_rows: Sequence[Mapping[str, Any]],
    shortcut_audit_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    action_rows = [*candidate_graph_rows, *pair_graph_rows, *request_graph_rows, *shortcut_audit_rows]
    forbidden = action_forbidden_keys([dict(row) for row in action_rows])
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commits = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejections = [row for row in action_rows if row.get("candidate_rejection") is True]
    promotable_rows = [
        row for row in candidate_graph_rows if row.get("promotable_branch_outcome") is True
    ]
    lossless_memberships = [
        row for row in candidate_graph_rows if row.get("is_lossless_pair_graph_candidate") is True
    ]
    max_pair_winner_memberships = [
        row for row in candidate_graph_rows if row.get("is_max_pair_win_candidate") is True
    ]
    source_gate = contract.get("source_gate") or {}
    minimum_gate = contract.get("minimum_rule_gate") or {}
    gate = {
        "source_residual_diagnostic_gate_passed": (source_summary.get("gate") or {}).get(
            "instance_arbitration_residual_diagnostic_gate_passed"
        )
        is True,
        "expected_candidate_graph_rows_passed": len(candidate_graph_rows)
        == safe_int(minimum_gate.get("expected_candidate_graph_rows"), 51),
        "expected_pair_graph_rows_passed": len(pair_graph_rows)
        == safe_int(minimum_gate.get("expected_pair_graph_rows"), 121),
        "expected_request_graph_rows_passed": len(request_graph_rows)
        == safe_int(minimum_gate.get("expected_request_graph_rows"), 9),
        "expected_lossless_candidate_membership_rows_passed": len(lossless_memberships)
        == safe_int(minimum_gate.get("expected_lossless_candidate_membership_rows"), 17),
        "expected_max_pair_winner_candidate_membership_rows_passed": len(max_pair_winner_memberships)
        == safe_int(minimum_gate.get("expected_max_pair_winner_candidate_membership_rows"), 14),
        "expected_shortcut_audit_rows_passed": len(shortcut_audit_rows)
        >= safe_int((contract.get("row_contract") or {}).get("shortcut_audit_rows_minimum"), 17),
        "expected_promotable_branch_outcome_rows_passed": len(promotable_rows)
        == safe_int(source_gate.get("expected_promotable_branch_outcome_rows"), 0),
        "terminal_commit_rows_passed": len(terminal_rows) == 0,
        "candidate_commit_rows_passed": len(candidate_commits) == 0,
        "candidate_rejection_rows_passed": len(candidate_rejections) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed_passed": all(row.get("paper_claim_allowed") is False for row in action_rows),
    }
    gate["pair_graph_consistency_followup_gate_passed"] = all(gate.values())
    shortcut_would_select_rows = [
        row for row in shortcut_audit_rows if row.get("shortcut_rule_would_select_candidate") is True
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "source_root": str(args.source_root),
        "out_root": str(args.out_root),
        "candidate_graph_rows": len(candidate_graph_rows),
        "pair_graph_rows": len(pair_graph_rows),
        "request_graph_rows": len(request_graph_rows),
        "shortcut_audit_rows": len(shortcut_audit_rows),
        "lossless_candidate_membership_rows": len(lossless_memberships),
        "max_pair_winner_candidate_membership_rows": len(max_pair_winner_memberships),
        "unique_lossless_request_rows": sum(
            1 for row in request_graph_rows if safe_int(row.get("lossless_pair_graph_candidate_count"), 0) == 1
        ),
        "multiple_lossless_request_rows": sum(
            1 for row in request_graph_rows if safe_int(row.get("lossless_pair_graph_candidate_count"), 0) > 1
        ),
        "pair_graph_winner_pair_rows": sum(
            1 for row in pair_graph_rows if str(row.get("pair_graph_winner_candidate_id") or "")
        ),
        "pair_graph_no_winner_pair_rows": sum(
            1 for row in pair_graph_rows if not str(row.get("pair_graph_winner_candidate_id") or "")
        ),
        "candidate_graph_status_counts": compact_counter(
            row.get("pair_graph_consistency_status") for row in candidate_graph_rows
        ),
        "pair_graph_status_counts": compact_counter(
            row.get("pair_graph_consistency_status") for row in pair_graph_rows
        ),
        "request_graph_status_counts": compact_counter(
            row.get("pair_graph_followup_status") for row in request_graph_rows
        ),
        "recommended_request_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in request_graph_rows
        ),
        "shortcut_rule_would_select_counts": compact_counter(
            row.get("shortcut_rule_name") for row in shortcut_would_select_rows
        ),
        "shortcut_blocked_reason_counts": compact_counter(
            row.get("shortcut_rule_blocked_reason") for row in shortcut_audit_rows
        ),
        "promotable_branch_outcome_rows": len(promotable_rows),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commits),
        "candidate_rejection_rows": len(candidate_rejections),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in action_rows),
        "terminal_utility_validation_allowed": any(
            row.get("terminal_utility_validation_allowed") is True for row in action_rows
        ),
        "paper_claim_allowed": any(row.get("paper_claim_allowed") is True for row in action_rows),
        "gate": gate,
        "next_allowed_task": (
            "freeze_terminal_utility_contract_after_separate_review"
            if len(promotable_rows) > 0
            else "close_instance_arbitration_pair_graph_branch_or_select_next_label_free_evidence_family"
        ),
        "interpretation": {
            "fact": "The analyzer audits pair-graph consistency from frozen residual candidate, pair, and request rows.",
            "agent_inference": "Graph winners and lossless candidates remain nonterminal because multiple lossless candidates, common-view overlap, rival leakage, or pair losses block shortcut goal commitment.",
            "paper_claim": "No paper claim is allowed from this follow-up analyzer alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    args.contract = Path(args.contract)
    contract = load_json(args.contract)
    args.source_root = Path(args.source_root) if args.source_root else Path(
        str((contract.get("source") or {}).get("residual_diagnostic_output"))
    )
    args.out_root = Path(args.out_root)
    args.source_summary = source_path(args, contract, "source_summary", "residual_diagnostic_summary")
    args.candidate_rows = source_path(args, contract, "candidate_rows", "residual_candidate_rows")
    args.pair_rows = source_path(args, contract, "pair_rows", "residual_pair_rows")
    args.request_rows = source_path(args, contract, "request_rows", "residual_request_rows")

    source_summary = load_json(args.source_summary)
    residual_candidate_rows = load_jsonl(args.candidate_rows)
    residual_pair_rows = load_jsonl(args.pair_rows)
    residual_request_rows = load_jsonl(args.request_rows)

    candidate_graph_rows = build_candidate_graph_rows(
        residual_candidate_rows,
        residual_pair_rows,
        residual_request_rows,
    )
    pair_graph_rows = build_pair_graph_rows(residual_pair_rows)
    request_graph_rows = build_request_graph_rows(
        residual_request_rows,
        candidate_graph_rows,
        pair_graph_rows,
    )
    shortcut_audit_rows = build_shortcut_audit_rows(candidate_graph_rows, request_graph_rows)
    summary = build_summary(
        args,
        contract,
        source_summary,
        candidate_graph_rows,
        pair_graph_rows,
        request_graph_rows,
        shortcut_audit_rows,
    )

    write_jsonl(args.out_root / "instance_arbitration_pair_graph_candidate_rows.jsonl", candidate_graph_rows)
    write_jsonl(args.out_root / "instance_arbitration_pair_graph_pair_rows.jsonl", pair_graph_rows)
    write_jsonl(args.out_root / "instance_arbitration_pair_graph_request_rows.jsonl", request_graph_rows)
    write_jsonl(args.out_root / "instance_arbitration_pair_graph_shortcut_audit_rows.jsonl", shortcut_audit_rows)
    write_json(args.out_root / "instance_arbitration_pair_graph_consistency_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze nonterminal pair-graph consistency follow-up for instance arbitration."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--source-root", default=None)
    parser.add_argument("--source-summary", default=None)
    parser.add_argument("--candidate-rows", default=None)
    parser.add_argument("--pair-rows", default=None)
    parser.add_argument("--request-rows", default=None)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(
        json.dumps(
            {
                "gate": summary["gate"]["pair_graph_consistency_followup_gate_passed"],
                "candidate_graph_rows": summary["candidate_graph_rows"],
                "pair_graph_rows": summary["pair_graph_rows"],
                "request_graph_rows": summary["request_graph_rows"],
                "shortcut_audit_rows": summary["shortcut_audit_rows"],
                "candidate_graph_status_counts": summary["candidate_graph_status_counts"],
                "request_graph_status_counts": summary["request_graph_status_counts"],
                "promotable_branch_outcome_rows": summary["promotable_branch_outcome_rows"],
                "next_allowed_task": summary["next_allowed_task"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not summary["gate"]["pair_graph_consistency_followup_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
