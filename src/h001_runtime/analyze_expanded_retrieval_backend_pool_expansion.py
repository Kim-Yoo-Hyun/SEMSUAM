import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    label_index,
    request_sort_key,
)


SCHEMA_VERSION = "h001.expanded_retrieval_backend_pool_expansion.v1"
SOURCE_REPAIR_ACTION = "request_backend_pool_expansion"
BACKEND_ROUTE_ACTIONS = [
    "request_backend_candidate_generation",
    "route_to_goal_validity_confirmation_after_expansion",
    "defer_backend_pool_unresolved",
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def source_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("repair_action") == SOURCE_REPAIR_ACTION],
        key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))),
    )


def candidate_set_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        request_id = row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")
        episode_key = row.get("episode_key")
        if request_id is not None:
            indexed[(str(request_id), "")] = row
        if episode_key is not None:
            indexed[("", str(episode_key))] = row
    return indexed


def compact_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "candidate_backend": candidate.get("candidate_backend"),
        "category": candidate.get("category"),
        "selection_rank": candidate.get("selection_rank"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "path_to_candidate": candidate.get("path_to_candidate"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "uses_gt_for_action": False,
    }


def candidate_row_for(
    repair_row: Dict[str, Any],
    candidate_index: Dict[Tuple[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    request_id = str(repair_row.get("expanded_retrieval_request_id"))
    episode_key = str(repair_row.get("episode_key"))
    return candidate_index.get((request_id, "")) or candidate_index.get(("", episode_key))


def candidate_ids(candidate_row: Optional[Dict[str, Any]]) -> List[str]:
    if not candidate_row:
        return []
    ids = candidate_row.get("expanded_candidate_ids")
    if ids is not None:
        return [str(candidate_id) for candidate_id in ids]
    return [str(candidate.get("candidate_id")) for candidate in candidate_row.get("expanded_candidates") or []]


def original_ids(repair_row: Dict[str, Any]) -> List[str]:
    accounting = dict(repair_row.get("pool_accounting") or {})
    summary = dict(repair_row.get("action_candidate_summary") or {})
    ids = accounting.get("original_candidate_ids") or summary.get("candidate_ids") or []
    return [str(candidate_id) for candidate_id in ids]


def source_role_ids(repair_row: Dict[str, Any], field: str) -> List[str]:
    summary = dict(repair_row.get("action_candidate_summary") or {})
    return [str(candidate_id) for candidate_id in summary.get(field) or []]


def expanded_pool_accounting(
    repair_row: Dict[str, Any],
    candidate_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    originals = original_ids(repair_row)
    expanded = candidate_ids(candidate_row)
    expanded_set = set(expanded)
    original_set = set(originals)
    candidates = list((candidate_row or {}).get("expanded_candidates") or [])
    reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is True)
    positive_support_count = sum(1 for candidate in candidates if candidate.get("positive_support") is True)
    backend_counts = Counter(str(candidate.get("candidate_backend")) for candidate in candidates)
    position_keys = [
        json.dumps(candidate.get("visit_position") or candidate.get("position"), sort_keys=True)
        for candidate in candidates
        if candidate.get("visit_position") is not None or candidate.get("position") is not None
    ]
    previous_action_ids = source_role_ids(repair_row, "candidate_ids")
    return {
        "original_candidate_count": len(originals),
        "original_candidate_ids": originals,
        "expanded_candidate_count": len(expanded),
        "expanded_candidate_ids": expanded,
        "retained_candidate_count": len(original_set & expanded_set),
        "retained_candidate_ids": sorted(original_set & expanded_set),
        "new_candidate_count": len(expanded_set - original_set),
        "new_candidate_ids": sorted(expanded_set - original_set),
        "removed_candidate_count": len(original_set - expanded_set),
        "removed_candidate_ids": sorted(original_set - expanded_set),
        "duplicated_candidate_id_count": len(expanded) - len(expanded_set),
        "unique_position_count": len(set(position_keys)),
        "duplicate_position_count": max(0, len(position_keys) - len(set(position_keys))),
        "reachable_candidate_count": reachable_count,
        "unreachable_or_unknown_candidate_count": max(0, len(expanded) - reachable_count),
        "positive_support_candidate_count": positive_support_count,
        "backend_candidate_family_counts": dict(sorted(backend_counts.items())),
        "source_top_retained": bool(set(source_role_ids(repair_row, "source_top_candidate_ids")) & expanded_set),
        "detector_strong_retained": bool(
            set(source_role_ids(repair_row, "detector_strong_candidate_ids")) & expanded_set
        ),
        "local_context_retained": bool(set(source_role_ids(repair_row, "local_context_candidate_ids")) & expanded_set),
        "previous_action_candidates_retained": len(set(previous_action_ids) & expanded_set),
    }


def backend_decision(
    candidate_row: Optional[Dict[str, Any]],
    accounting: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    expanded_count = safe_int(accounting.get("expanded_candidate_count"))
    reachable_count = safe_int(accounting.get("reachable_candidate_count"))
    positive_support_count = safe_int(accounting.get("positive_support_candidate_count"))
    duplicate_ids = safe_int(accounting.get("duplicated_candidate_id_count"))
    signals: List[str] = []

    if candidate_row is None:
        return {
            "backend_route_action": "request_backend_candidate_generation",
            "backend_route_reason": "backend_candidate_set_missing",
            "backend_route_signals": ["backend_candidate_artifact_missing"],
            "terminal_commit": False,
        }

    if expanded_count < int(args.min_expanded_candidates):
        signals.append("expanded_pool_below_fixed_candidate_budget")
    if reachable_count < int(args.min_reachable_candidates):
        signals.append("expanded_pool_reachability_insufficient")
    if positive_support_count == 0:
        signals.append("expanded_pool_has_no_positive_support")
    if duplicate_ids > 0:
        signals.append("expanded_pool_contains_duplicate_ids")

    if expanded_count < int(args.min_expanded_candidates):
        return {
            "backend_route_action": "request_backend_candidate_generation",
            "backend_route_reason": "expanded_pool_below_fixed_candidate_budget",
            "backend_route_signals": sorted(set(signals)),
            "terminal_commit": False,
        }
    if reachable_count < int(args.min_reachable_candidates) or positive_support_count == 0:
        return {
            "backend_route_action": "defer_backend_pool_unresolved",
            "backend_route_reason": "expanded_pool_not_reachable_or_supported",
            "backend_route_signals": sorted(set(signals)),
            "terminal_commit": False,
        }
    if duplicate_ids >= expanded_count and expanded_count > 0:
        return {
            "backend_route_action": "defer_backend_pool_unresolved",
            "backend_route_reason": "expanded_pool_duplicate_only",
            "backend_route_signals": sorted(set(signals)),
            "terminal_commit": False,
        }
    return {
        "backend_route_action": "route_to_goal_validity_confirmation_after_expansion",
        "backend_route_reason": "expanded_pool_meets_fixed_candidate_budget_and_reachability_floor",
        "backend_route_signals": ["expanded_pool_ready_for_goal_validity_confirmation"],
        "terminal_commit": False,
    }


def build_action_rows(
    repair_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    indexed = candidate_set_index(candidate_rows)
    policy = dict(contract.get("candidate_generation_policy") or {})
    output: List[Dict[str, Any]] = []
    for row in source_rows(repair_rows):
        candidate_row = candidate_row_for(row, indexed)
        accounting = expanded_pool_accounting(row, candidate_row)
        decision = backend_decision(candidate_row, accounting, args)
        candidates = list((candidate_row or {}).get("expanded_candidates") or [])
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_only_before_label_join",
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "source_schema_version": row.get("schema_version"),
                "source_repair_action": row.get("repair_action"),
                "source_repair_reason": row.get("repair_reason"),
                "source_repair_signals": row.get("repair_signals"),
                "source_pool_proxy": row.get("source_pool_proxy"),
                "source_action_candidate_summary": row.get("action_candidate_summary"),
                "source_pool_accounting": row.get("pool_accounting"),
                "backend_config": {
                    "backend_family": "existing_vlmaps_artifact_jsonl",
                    "candidate_budget_candidates": policy.get("candidate_budget_candidates"),
                    "candidate_budget_minimum": int(args.min_expanded_candidates),
                    "candidate_set_path": str(args.candidate_set),
                    "candidate_set_contract": (candidate_row or {}).get("contract_name"),
                    "candidate_set_budget_min": (candidate_row or {}).get("candidate_budget_min"),
                    "candidate_set_budget_max": (candidate_row or {}).get("candidate_budget_max"),
                    "spatial_diversity_required": policy.get("spatial_diversity_required"),
                    "reachability_filter_required": policy.get("reachability_filter_required"),
                    "duplicate_accounting_required": policy.get("duplicate_accounting_required"),
                },
                "expanded_pool_accounting": accounting,
                "candidate_preview": [compact_candidate(candidate) for candidate in candidates[: int(args.preview_candidates)]],
                "uses_gt_for_action": False,
                **decision,
            }
        )
    return output


def candidate_label_summary(
    action_row: Dict[str, Any],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    episode_key = str(action_row.get("episode_key"))
    expanded_ids = list((action_row.get("expanded_pool_accounting") or {}).get("expanded_candidate_ids") or [])
    label_rows = [labels.get((episode_key, str(candidate_id))) for candidate_id in expanded_ids]
    labeled_rows = [row for row in label_rows if row is not None]
    correct_ids = [
        str(candidate_id)
        for candidate_id, label in zip(expanded_ids, label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is True
    ]
    wrong_ids = [
        str(candidate_id)
        for candidate_id, label in zip(expanded_ids, label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is False
    ]
    return {
        "evaluation_only_candidate_count": len(expanded_ids),
        "evaluation_only_labeled_candidate_count": len(labeled_rows),
        "evaluation_only_unlabeled_candidate_count": len(expanded_ids) - len(labeled_rows),
        "evaluation_only_correct_candidate_count": len(correct_ids),
        "evaluation_only_wrong_candidate_count": len(wrong_ids),
        "evaluation_only_correct_candidate_ids": correct_ids,
        "evaluation_only_wrong_candidate_ids_preview": wrong_ids[:10],
        "evaluation_only_no_valid_candidate_pool": len(correct_ids) == 0,
        "evaluation_only_contains_valid_candidate": len(correct_ids) > 0,
    }


def build_evaluated_rows(
    action_rows: Sequence[Dict[str, Any]],
    evaluation_labels: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    labels = label_index(evaluation_labels)
    output: List[Dict[str, Any]] = []
    for row in action_rows:
        summary = candidate_label_summary(row, labels)
        output.append(
            {
                **row,
                "validation_stage": "evaluation_joined_after_expansion_rows",
                "evaluation_candidate_summary": summary,
                "evaluation_only_contains_valid_candidate": summary.get(
                    "evaluation_only_contains_valid_candidate"
                ),
                "evaluation_only_no_valid_candidate_pool": summary.get(
                    "evaluation_only_no_valid_candidate_pool"
                ),
                "evaluation_only_correct_candidate_count": summary.get(
                    "evaluation_only_correct_candidate_count"
                ),
                "evaluation_only_wrong_candidate_count": summary.get(
                    "evaluation_only_wrong_candidate_count"
                ),
                "evaluation_only_correct_candidate_ids": summary.get(
                    "evaluation_only_correct_candidate_ids"
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return output


def count_by_action(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts = Counter(str(row.get(key)) for row in rows)
    return {action: counts.get(action, 0) for action in BACKEND_ROUTE_ACTIONS}


def count_stats(values: Sequence[int]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "max": None, "mean": None}
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def repair_eval_summary(repair_evaluated_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    rows = source_rows(repair_evaluated_rows)
    no_valid_rows = [
        row
        for row in rows
        if (row.get("evaluation_candidate_summary") or {}).get("evaluation_only_no_valid_candidate_pool")
        is True
    ]
    contains_valid_rows = [
        row
        for row in rows
        if (row.get("evaluation_candidate_summary") or {}).get("evaluation_only_no_valid_candidate_pool")
        is False
    ]
    return {
        "source_repair_evaluated_rows": len(rows),
        "source_repair_eval_no_valid_rows": len(no_valid_rows),
        "source_repair_eval_contains_valid_rows": len(contains_valid_rows),
    }


def summarize(
    action_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    repair_evaluated_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    action_counts = count_by_action(action_rows, "backend_route_action")
    reason_counts = Counter(str(row.get("backend_route_reason")) for row in action_rows)
    signal_counts = Counter(
        str(signal)
        for row in action_rows
        for signal in row.get("backend_route_signals") or []
    )
    no_valid_by_route = Counter(
        str(row.get("backend_route_action"))
        for row in evaluated_rows
        if row.get("evaluation_only_no_valid_candidate_pool") is True
    )
    valid_by_route = Counter(
        str(row.get("backend_route_action"))
        for row in evaluated_rows
        if row.get("evaluation_only_contains_valid_candidate") is True
    )
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    expanded_counts = [
        safe_int((row.get("expanded_pool_accounting") or {}).get("expanded_candidate_count"))
        for row in action_rows
    ]
    new_counts = [
        safe_int((row.get("expanded_pool_accounting") or {}).get("new_candidate_count"))
        for row in action_rows
    ]
    duplicate_counts = [
        safe_int((row.get("expanded_pool_accounting") or {}).get("duplicated_candidate_id_count"))
        for row in action_rows
    ]
    reachable_counts = [
        safe_int((row.get("expanded_pool_accounting") or {}).get("reachable_candidate_count"))
        for row in action_rows
    ]
    gates = contract.get("evaluation_gates") or {}
    expected_rows = safe_int(gates.get("input_request_rows"), default=args.expected_request_rows)
    goal_ready_rows = action_counts.get("route_to_goal_validity_confirmation_after_expansion", 0)
    generation_rows = action_counts.get("request_backend_candidate_generation", 0)
    gate = {
        "input_request_rows_passed": len(action_rows) == expected_rows,
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(
            gates.get("terminal_commit_rows_maximum"), default=0
        ),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), default=0),
        "reports_backend_route_action_counts": all(action in action_counts for action in BACKEND_ROUTE_ACTIONS),
        "reports_expanded_candidate_counts": len(expanded_counts) == len(action_rows),
        "reports_new_candidate_counts": len(new_counts) == len(action_rows),
        "reports_duplicate_and_reachability_counts": len(duplicate_counts) == len(action_rows)
        and len(reachable_counts) == len(action_rows),
        "reports_backend_config": all("backend_config" in row for row in action_rows),
        "reports_goal_validity_ready_rows": "route_to_goal_validity_confirmation_after_expansion" in action_counts,
        "reports_defer_backend_pool_unresolved_rows": "defer_backend_pool_unresolved" in action_counts,
        "joins_labels_only_after_expansion_rows": True,
        "reports_contains_valid_candidate_after_label_join": bool(evaluated_rows),
        "reports_no_valid_rows_by_backend_route_after_label_join": bool(no_valid_by_route or evaluated_rows),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "goal_validity_confirmation_unblocked": goal_ready_rows > 0,
        "backend_candidate_generation_required": generation_rows > 0,
        "paper_claim_allowed": False,
    }
    gate["backend_pool_expansion_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "paper_claim_allowed",
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "goal_validity_confirmation_unblocked",
            "backend_candidate_generation_required",
        }
    )
    topk_eval_valid_rows = sum(
        1 for row in evaluated_rows if row.get("evaluation_only_contains_valid_candidate") is True
    )
    topk_eval_no_valid_rows = sum(
        1 for row in evaluated_rows if row.get("evaluation_only_no_valid_candidate_pool") is True
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "repair_rows": str(args.repair_rows),
        "repair_evaluated_rows": str(args.repair_evaluated_rows),
        "candidate_set": str(args.candidate_set),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "request_rows": len(action_rows),
        "evaluated_rows": len(evaluated_rows),
        "terminal_commit_rows": len(terminal_rows),
        "backend_route_action_counts": action_counts,
        "backend_route_reason_counts": dict(sorted(reason_counts.items())),
        "backend_route_signal_counts": dict(sorted(signal_counts.items())),
        "no_valid_rows_by_backend_route": {
            action: no_valid_by_route.get(action, 0) for action in BACKEND_ROUTE_ACTIONS
        },
        "valid_rows_by_backend_route": {action: valid_by_route.get(action, 0) for action in BACKEND_ROUTE_ACTIONS},
        "backend_candidate_generation_rows": generation_rows,
        "goal_validity_ready_rows": goal_ready_rows,
        "defer_backend_pool_unresolved_rows": action_counts.get("defer_backend_pool_unresolved", 0),
        "expanded_candidate_count_stats": count_stats(expanded_counts),
        "new_candidate_count_stats": count_stats(new_counts),
        "duplicate_candidate_id_count_stats": count_stats(duplicate_counts),
        "reachable_candidate_count_stats": count_stats(reachable_counts),
        "expanded_pool_candidate_counts": [
            {
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "backend_route_action": row.get("backend_route_action"),
                "backend_route_reason": row.get("backend_route_reason"),
                "expanded_pool_accounting": row.get("expanded_pool_accounting"),
            }
            for row in action_rows
        ],
        "simpler_alternative_accounting": {
            "defer_all_backend_expansion_rows": {
                "terminal_commit_rows": 0,
                "blocked_by": "no_candidate_pool_repair_evidence",
            },
            "pass_through_to_goal_validity_without_expansion": {
                **repair_eval_summary(repair_evaluated_rows),
                "blocked_by": "mixes_no_valid_pool_failures_with_goal_validity_confirmation",
            },
            "topk_semantic_expansion_without_spatial_diversity": {
                "candidate_count_rows_below_fixed_budget": sum(
                    1 for value in expanded_counts if value < int(args.min_expanded_candidates)
                ),
                "evaluation_only_contains_valid_rows": topk_eval_valid_rows,
                "evaluation_only_no_valid_rows": topk_eval_no_valid_rows,
                "blocked_by": "topk_preview_does_not_satisfy_fixed_backend_expansion_budget",
            },
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "interpretation": {
            "fact": (
                "The analyzer materializes backend expansion rows from the five source-pool repair "
                "rows before joining evaluation-only labels."
            ),
            "agent_inference": (
                "The available paper-scale candidate artifact is a top-10 preview and does not "
                "satisfy the fixed backend expansion candidate budget. The safe next branch is fixed "
                "backend candidate generation, not goal-validity confirmation."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "expansion_rows": "backend_pool_expansion_rows.jsonl",
            "evaluated_rows": "backend_pool_expansion_evaluated_rows.jsonl",
            "summary": "backend_pool_expansion_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    repair_rows = load_jsonl(Path(args.repair_rows))
    repair_evaluated_rows = load_jsonl(Path(args.repair_evaluated_rows))
    candidate_rows = load_jsonl(Path(args.candidate_set))
    evaluation_labels = load_jsonl(Path(args.evaluation_labels))

    action_rows = build_action_rows(repair_rows, candidate_rows, contract, args)
    evaluated_rows = build_evaluated_rows(action_rows, evaluation_labels)
    summary = summarize(action_rows, evaluated_rows, repair_evaluated_rows, contract, args)

    write_jsonl(out_root / "backend_pool_expansion_rows.jsonl", action_rows)
    write_jsonl(out_root / "backend_pool_expansion_evaluated_rows.jsonl", evaluated_rows)
    write_json(out_root / "backend_pool_expansion_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route backend pool expansion rows before goal-validity confirmation."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--repair-rows", required=True)
    parser.add_argument("--repair-evaluated-rows", required=True)
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--expected-request-rows", type=int, default=5)
    parser.add_argument("--min-expanded-candidates", type=int, default=20)
    parser.add_argument("--min-reachable-candidates", type=int, default=1)
    parser.add_argument("--preview-candidates", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
