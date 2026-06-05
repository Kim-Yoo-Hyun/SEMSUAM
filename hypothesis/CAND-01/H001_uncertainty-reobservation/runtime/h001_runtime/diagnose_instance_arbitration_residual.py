import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.instance_arbitration_residual_diagnostic.v1"
SOURCE_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_detector_evidence_v1"
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_residual_diagnostic_v1"


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


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


def classify_candidate(row: Mapping[str, Any]) -> str:
    status = str(row.get("candidate_evidence_status") or "")
    rival_leakage = safe_int(row.get("rival_leakage_count"), 0)
    pair_contradiction = safe_int(row.get("pair_contradiction_count"), 0)
    pair_support = safe_int(row.get("pair_support_count"), 0)
    own_view = row.get("own_view_support") is True
    source_top = row.get("source_top_candidate") is True
    if status == "contradicted_by_pair_or_contrast_evidence" and pair_contradiction > 0:
        return "pair_or_contrast_contradiction"
    if status == "ambiguous_rival_leakage_candidate" and source_top and rival_leakage > 0:
        return "source_top_shortcut_rival_leakage"
    if status == "ambiguous_rival_leakage_candidate" and own_view and rival_leakage > 0:
        return "own_view_support_with_rival_leakage"
    if status == "ambiguous_rival_leakage_candidate" and pair_support > 0 and rival_leakage > 0:
        return "pair_support_with_rival_leakage"
    if status == "ambiguous_rival_leakage_candidate" and rival_leakage > 0:
        return "contrast_support_with_rival_leakage"
    if status == "partial_instance_support":
        return "partial_support_without_pair_resolution"
    return "manual_review_unclassified_candidate_residual"


def candidate_tags(row: Mapping[str, Any], residual_class: str) -> List[str]:
    tags = {residual_class}
    bool_fields = [
        "source_top_candidate",
        "strong_own_view_candidate",
        "detector_strong_candidate",
        "local_context_candidate",
        "own_view_support",
        "source_top_contrast_support",
        "local_context_contrast_support",
    ]
    for key in bool_fields:
        if row.get(key) is True:
            tags.add(key)
    if safe_int(row.get("rival_leakage_count"), 0) > 0:
        tags.add("rival_leakage_positive")
    if safe_int(row.get("pair_contradiction_count"), 0) > 0:
        tags.add("pair_contradiction_positive")
    if safe_int(row.get("pair_support_count"), 0) > 0:
        tags.add("pair_support_positive")
    if safe_int(row.get("pair_both_support_count"), 0) > 0:
        tags.add("pair_both_support_positive")
    if safe_int(row.get("pair_no_support_count"), 0) > 0:
        tags.add("pair_no_support_positive")
    if row.get("own_view_support") is not True:
        tags.add("own_view_support_absent")
    return sorted(tags)


def candidate_action(residual_class: str) -> str:
    if residual_class in {
        "source_top_shortcut_rival_leakage",
        "own_view_support_with_rival_leakage",
        "pair_support_with_rival_leakage",
        "contrast_support_with_rival_leakage",
    }:
        return "route_to_pair_graph_consistency_audit"
    if residual_class == "pair_or_contrast_contradiction":
        return "route_to_pair_graph_contradiction_audit"
    if residual_class == "partial_support_without_pair_resolution":
        return "route_to_partial_support_audit"
    return "defer_instance_arbitration_manual_review"


def build_candidate_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            candidate_sort_key(row_candidate_id(item)),
        ),
    ):
        residual_class = classify_candidate(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "candidate_residual_diagnostic",
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or row_request_id(row),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": row_candidate_id(row),
                "source_candidate_evidence_status": row.get("candidate_evidence_status"),
                "source_recommended_nonterminal_action": row.get("recommended_nonterminal_action"),
                "residual_failure_class": residual_class,
                "residual_failure_tags": candidate_tags(row, residual_class),
                "source_top_candidate": row.get("source_top_candidate") is True,
                "strong_own_view_candidate": row.get("strong_own_view_candidate") is True,
                "detector_strong_candidate": row.get("detector_strong_candidate") is True,
                "local_context_candidate": row.get("local_context_candidate") is True,
                "own_view_support": row.get("own_view_support") is True,
                "source_top_contrast_support": row.get("source_top_contrast_support") is True,
                "local_context_contrast_support": row.get("local_context_contrast_support") is True,
                "pair_support_count": safe_int(row.get("pair_support_count"), 0),
                "pair_both_support_count": safe_int(row.get("pair_both_support_count"), 0),
                "pair_no_support_count": safe_int(row.get("pair_no_support_count"), 0),
                "pair_contradiction_count": safe_int(row.get("pair_contradiction_count"), 0),
                "rival_leakage_count": safe_int(row.get("rival_leakage_count"), 0),
                "recommended_nonterminal_action": candidate_action(residual_class),
                "branch_promotable": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "terminal_utility_validation_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def classify_pair(row: Mapping[str, Any]) -> str:
    status = str(row.get("pair_evidence_status") or "")
    probe = str(row.get("pair_probe_type") or "")
    if status == "ambiguous_both_candidates_supported":
        if probe == "pair_common_view":
            return "common_view_both_candidates_supported"
        return "standoff_both_candidates_supported"
    if status == "ambiguous_no_candidate_support":
        if probe == "pair_dual_standoff_fallback":
            return "dual_standoff_no_candidate_support"
        return "common_view_no_candidate_support"
    if status in {
        "resolved_in_favor_of_candidate_a_nonterminal",
        "resolved_in_favor_of_candidate_b_nonterminal",
    }:
        if safe_int(row.get("candidate_a_leakage_count"), 0) or safe_int(row.get("candidate_b_leakage_count"), 0):
            return "one_sided_pair_support_with_leakage"
        return "one_sided_pair_support_nonterminal"
    return "manual_review_unclassified_pair_residual"


def pair_tags(row: Mapping[str, Any], residual_class: str) -> List[str]:
    tags = {residual_class, str(row.get("pair_probe_type") or "missing_pair_probe_type")}
    if safe_int(row.get("candidate_a_support_count"), 0) > 0:
        tags.add("candidate_a_support_positive")
    if safe_int(row.get("candidate_b_support_count"), 0) > 0:
        tags.add("candidate_b_support_positive")
    if safe_int(row.get("candidate_a_leakage_count"), 0) > 0:
        tags.add("candidate_a_leakage_positive")
    if safe_int(row.get("candidate_b_leakage_count"), 0) > 0:
        tags.add("candidate_b_leakage_positive")
    return sorted(tags)


def pair_winner(row: Mapping[str, Any]) -> str:
    status = str(row.get("pair_evidence_status") or "")
    if status == "resolved_in_favor_of_candidate_a_nonterminal":
        return str(row.get("candidate_id_a") or "")
    if status == "resolved_in_favor_of_candidate_b_nonterminal":
        return str(row.get("candidate_id_b") or "")
    return ""


def build_pair_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("request_pair_index"), 999999),
            candidate_sort_key(item.get("candidate_id_a")),
            candidate_sort_key(item.get("candidate_id_b")),
        ),
    ):
        residual_class = classify_pair(row)
        winner = pair_winner(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "pair_residual_diagnostic",
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
                "source_pair_evidence_status": row.get("pair_evidence_status"),
                "pair_probe_type": row.get("pair_probe_type"),
                "residual_failure_class": residual_class,
                "residual_failure_tags": pair_tags(row, residual_class),
                "pair_graph_winner_candidate_id": winner,
                "candidate_a_support_count": safe_int(row.get("candidate_a_support_count"), 0),
                "candidate_b_support_count": safe_int(row.get("candidate_b_support_count"), 0),
                "candidate_a_leakage_count": safe_int(row.get("candidate_a_leakage_count"), 0),
                "candidate_b_leakage_count": safe_int(row.get("candidate_b_leakage_count"), 0),
                "recommended_nonterminal_action": "aggregate_pair_graph_residual",
                "branch_promotable": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "terminal_utility_validation_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def pair_graph_summary(pair_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    candidates = sorted(
        {
            str(row.get("candidate_id_a") or "")
            for row in pair_rows
        }
        | {
            str(row.get("candidate_id_b") or "")
            for row in pair_rows
        },
        key=candidate_sort_key,
    )
    wins = Counter()
    losses = Counter()
    ambiguous_incidents = Counter()
    for row in pair_rows:
        a = str(row.get("candidate_id_a") or "")
        b = str(row.get("candidate_id_b") or "")
        status = str(row.get("source_pair_evidence_status") or row.get("pair_evidence_status") or "")
        winner = str(row.get("pair_graph_winner_candidate_id") or "")
        if winner == a:
            wins[a] += 1
            losses[b] += 1
        elif winner == b:
            wins[b] += 1
            losses[a] += 1
        elif status.startswith("ambiguous"):
            ambiguous_incidents[a] += 1
            ambiguous_incidents[b] += 1
    lossless = [candidate_id for candidate_id in candidates if wins[candidate_id] > 0 and losses[candidate_id] == 0]
    max_wins = max([wins[candidate_id] for candidate_id in candidates], default=0)
    max_win_candidates = [candidate_id for candidate_id in candidates if wins[candidate_id] == max_wins and max_wins > 0]
    return {
        "candidate_ids": candidates,
        "win_counts": {candidate_id: wins[candidate_id] for candidate_id in candidates},
        "loss_counts": {candidate_id: losses[candidate_id] for candidate_id in candidates},
        "ambiguous_pair_incident_counts": {
            candidate_id: ambiguous_incidents[candidate_id] for candidate_id in candidates
        },
        "lossless_pair_graph_candidate_ids": lossless,
        "lossless_pair_graph_candidate_count": len(lossless),
        "unique_lossless_pair_graph_candidate_id": lossless[0] if len(lossless) == 1 else None,
        "max_pair_win_count": max_wins,
        "max_pair_win_candidate_ids": max_win_candidates,
    }


def request_status(
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    graph: Mapping[str, Any],
) -> str:
    candidate_classes = Counter(str(row.get("residual_failure_class")) for row in candidate_rows)
    pair_classes = Counter(str(row.get("residual_failure_class")) for row in pair_rows)
    lossless_count = safe_int(graph.get("lossless_pair_graph_candidate_count"), 0)
    if lossless_count == 1 and pair_classes.get("common_view_both_candidates_supported", 0):
        return "unique_lossless_pair_graph_candidate_blocked_by_common_view_overlap"
    if lossless_count == 1 and pair_classes.get("dual_standoff_no_candidate_support", 0):
        return "unique_lossless_pair_graph_candidate_with_missing_pair_support"
    if lossless_count > 1:
        return "multiple_lossless_pair_graph_candidates"
    if candidate_classes.get("source_top_shortcut_rival_leakage", 0):
        return "source_top_shortcut_contaminated_by_rival_leakage"
    if pair_classes.get("common_view_both_candidates_supported", 0):
        return "common_view_overlap_without_graph_winner"
    return "manual_review_unclassified_request_residual"


def request_action(status: str) -> str:
    if status in {
        "unique_lossless_pair_graph_candidate_blocked_by_common_view_overlap",
        "unique_lossless_pair_graph_candidate_with_missing_pair_support",
        "multiple_lossless_pair_graph_candidates",
    }:
        return "freeze_pair_graph_consistency_followup_contract"
    if status == "source_top_shortcut_contaminated_by_rival_leakage":
        return "defer_to_source_top_shortcut_failure_closure"
    return "defer_instance_arbitration_residual_manual_review"


def build_request_rows(
    source_request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    candidates_by_request = group_by_request(candidate_rows)
    pairs_by_request = group_by_request(pair_rows)
    output: List[Dict[str, Any]] = []
    for source in sorted(source_request_rows, key=lambda row: request_sort_key(row_request_id(row))):
        rid = row_request_id(source)
        candidates = sorted(
            candidates_by_request.get(rid, []),
            key=lambda row: candidate_sort_key(row.get("candidate_id")),
        )
        pairs = sorted(
            pairs_by_request.get(rid, []),
            key=lambda row: safe_int(row.get("request_pair_index"), 999999),
        )
        graph = pair_graph_summary(pairs)
        status = request_status(candidates, pairs, graph)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "request_residual_diagnostic",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source.get("rival_identity_request_id") or rid,
                "episode_key": source.get("episode_key"),
                "scene_key": source.get("scene_key"),
                "scene_id": source.get("scene_id"),
                "query": source.get("query"),
                "candidate_count": len(candidates),
                "pair_count": len(pairs),
                "source_supported_candidate_count": source.get("supported_candidate_count"),
                "source_contradicted_candidate_count": source.get("contradicted_candidate_count"),
                "source_ambiguous_candidate_count": source.get("ambiguous_candidate_count"),
                "source_unresolved_pair_count": source.get("unresolved_pair_count"),
                "candidate_residual_class_counts": compact_counter(
                    row.get("residual_failure_class") for row in candidates
                ),
                "pair_residual_class_counts": compact_counter(
                    row.get("residual_failure_class") for row in pairs
                ),
                "pair_graph": graph,
                "request_residual_status": status,
                "promotable_branch_outcome": False,
                "recommended_nonterminal_action": request_action(status),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "terminal_utility_validation_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_summary(
    args: argparse.Namespace,
    source_summary: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    action_rows = [*candidate_rows, *pair_rows, *request_rows]
    forbidden = action_forbidden_keys([dict(row) for row in action_rows])
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    candidate_commits = [row for row in action_rows if row.get("candidate_commit") is True]
    candidate_rejections = [row for row in action_rows if row.get("candidate_rejection") is True]
    promotable_rows = [row for row in request_rows if row.get("promotable_branch_outcome") is True]
    graph_followup_rows = [
        row
        for row in request_rows
        if str(row.get("recommended_nonterminal_action")) == "freeze_pair_graph_consistency_followup_contract"
    ]
    source_gate = (source_summary.get("gate") or {}).get(
        "instance_arbitration_detector_evidence_gate_passed"
    )
    gate = {
        "source_detector_evidence_gate_passed": source_gate is True,
        "source_zero_promotable_outcomes_passed": safe_int(
            source_summary.get("promotable_branch_outcome_rows"), -1
        ) == 0,
        "expected_candidate_rows_passed": len(candidate_rows) == 51,
        "expected_pair_rows_passed": len(pair_rows) == 121,
        "expected_request_rows_passed": len(request_rows) == 9,
        "all_requests_diagnosed_passed": all(
            str(row.get("request_residual_status")) != "manual_review_unclassified_request_residual"
            for row in request_rows
        ),
        "pair_graph_followup_signal_passed": len(graph_followup_rows) >= 5,
        "no_promotable_branch_outcome_passed": len(promotable_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "terminal_commit_rows_passed": len(terminal_rows) == 0,
        "candidate_commit_rows_passed": len(candidate_commits) == 0,
        "candidate_rejection_rows_passed": len(candidate_rejections) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed_passed": all(row.get("paper_claim_allowed") is False for row in action_rows),
    }
    gate["instance_arbitration_residual_diagnostic_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "source_root": str(args.source_root),
        "out_root": str(args.out_root),
        "source_summary": str(args.source_summary),
        "candidate_rows": len(candidate_rows),
        "pair_rows": len(pair_rows),
        "request_rows": len(request_rows),
        "source_candidate_status_counts": source_summary.get("candidate_evidence_status_counts"),
        "source_pair_status_counts": source_summary.get("pair_evidence_status_counts"),
        "candidate_residual_class_counts": compact_counter(
            row.get("residual_failure_class") for row in candidate_rows
        ),
        "candidate_residual_tag_counts": compact_counter(
            tag for row in candidate_rows for tag in row.get("residual_failure_tags", [])
        ),
        "pair_residual_class_counts": compact_counter(
            row.get("residual_failure_class") for row in pair_rows
        ),
        "pair_residual_tag_counts": compact_counter(
            tag for row in pair_rows for tag in row.get("residual_failure_tags", [])
        ),
        "request_residual_status_counts": compact_counter(
            row.get("request_residual_status") for row in request_rows
        ),
        "recommended_request_action_counts": compact_counter(
            row.get("recommended_nonterminal_action") for row in request_rows
        ),
        "lossless_pair_graph_candidate_count_by_request": {
            str(row.get("expanded_retrieval_request_id")): safe_int(
                (row.get("pair_graph") or {}).get("lossless_pair_graph_candidate_count"), 0
            )
            for row in request_rows
        },
        "unique_lossless_pair_graph_candidate_request_rows": sum(
            1
            for row in request_rows
            if safe_int((row.get("pair_graph") or {}).get("lossless_pair_graph_candidate_count"), 0) == 1
        ),
        "multiple_lossless_pair_graph_candidate_request_rows": sum(
            1
            for row in request_rows
            if safe_int((row.get("pair_graph") or {}).get("lossless_pair_graph_candidate_count"), 0) > 1
        ),
        "pair_graph_followup_request_rows": len(graph_followup_rows),
        "promotable_branch_outcome_rows": len(promotable_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": len(candidate_commits),
        "candidate_rejection_rows": len(candidate_rejections),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in action_rows),
        "terminal_utility_validation_allowed": any(
            row.get("terminal_utility_validation_allowed") is True for row in action_rows
        ),
        "paper_claim_allowed": any(row.get("paper_claim_allowed") is True for row in action_rows),
        "gate": gate,
        "next_allowed_task": "freeze_instance_arbitration_pair_graph_consistency_followup_contract"
        if len(graph_followup_rows) >= 5
        else "close_instance_arbitration_branch_without_promotion",
        "interpretation": {
            "fact": "The residual diagnostic classifies candidate, pair, and request-level failures after the instance-arbitration post-detector analyzer produced zero promotable outcomes.",
            "agent_inference": "Pairwise evidence has a label-free graph signal in most requests, but common-view overlap and no-support pairs block direct promotion. A follow-up should test pair-graph consistency as nonterminal evidence, not as a commit rule.",
            "paper_claim": "No paper claim is allowed from this residual diagnostic alone.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    source_root = Path(args.source_root)
    out_root = Path(args.out_root)
    args.source_summary = Path(args.source_summary) if args.source_summary else (
        source_root / "instance_arbitration_detector_evidence_summary.json"
    )
    args.candidate_rows = Path(args.candidate_rows) if args.candidate_rows else (
        source_root / "instance_arbitration_candidate_evidence.jsonl"
    )
    args.pair_rows = Path(args.pair_rows) if args.pair_rows else (
        source_root / "instance_arbitration_pair_evidence.jsonl"
    )
    args.request_rows = Path(args.request_rows) if args.request_rows else (
        source_root / "instance_arbitration_request_evidence.jsonl"
    )
    source_summary = load_json(args.source_summary)
    candidate_rows = build_candidate_rows(load_jsonl(args.candidate_rows))
    pair_rows = build_pair_rows(load_jsonl(args.pair_rows))
    request_rows = build_request_rows(load_jsonl(args.request_rows), candidate_rows, pair_rows)
    summary = build_summary(args, source_summary, candidate_rows, pair_rows, request_rows)

    write_jsonl(out_root / "instance_arbitration_residual_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "instance_arbitration_residual_pair_rows.jsonl", pair_rows)
    write_jsonl(out_root / "instance_arbitration_residual_request_rows.jsonl", request_rows)
    write_json(out_root / "instance_arbitration_residual_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose residual instance-arbitration detector evidence failures."
    )
    parser.add_argument("--source-root", default=SOURCE_ROOT_DEFAULT)
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
                "gate": summary["gate"]["instance_arbitration_residual_diagnostic_gate_passed"],
                "candidate_rows": summary["candidate_rows"],
                "pair_rows": summary["pair_rows"],
                "request_rows": summary["request_rows"],
                "candidate_residual_class_counts": summary["candidate_residual_class_counts"],
                "pair_residual_class_counts": summary["pair_residual_class_counts"],
                "request_residual_status_counts": summary["request_residual_status_counts"],
                "pair_graph_followup_request_rows": summary["pair_graph_followup_request_rows"],
                "promotable_branch_outcome_rows": summary["promotable_branch_outcome_rows"],
                "next_allowed_task": summary["next_allowed_task"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    if not summary["gate"]["instance_arbitration_residual_diagnostic_gate_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
