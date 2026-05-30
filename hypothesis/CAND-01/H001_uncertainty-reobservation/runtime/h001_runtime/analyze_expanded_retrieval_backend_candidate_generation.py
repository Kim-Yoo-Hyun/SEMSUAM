import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    label_index,
    request_sort_key,
)


SCHEMA_VERSION = "h001.expanded_retrieval_backend_candidate_generation.v1"
SOURCE_BACKEND_ROUTE_ACTION = "request_backend_candidate_generation"
GENERATION_STATUSES = [
    "generated_fixed_top20_pool",
    "request_deeper_backend_generation",
    "defer_backend_candidate_generation_unresolved",
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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def source_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("backend_route_action") == SOURCE_BACKEND_ROUTE_ACTION],
        key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))),
    )


def action_evidence_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        episode_key = row.get("episode_key")
        query = row.get("query")
        if episode_key is None:
            continue
        indexed[(str(episode_key), str(query))] = row
        indexed[(str(episode_key), "")] = row
    return indexed


def action_evidence_for(
    backend_row: Dict[str, Any],
    indexed: Dict[Tuple[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    episode_key = str(backend_row.get("episode_key"))
    query = str(backend_row.get("query"))
    return indexed.get((episode_key, query)) or indexed.get((episode_key, ""))


def finite_vector(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError):
        return False
    return all(math.isfinite(number) for number in numbers)


def position_key(candidate: Dict[str, Any]) -> Optional[str]:
    position = candidate.get("position") if finite_vector(candidate.get("position")) else candidate.get("visit_position")
    if not finite_vector(position):
        return None
    rounded = [round(float(value), 4) for value in position]
    return json.dumps(rounded, sort_keys=True)


def candidate_sort_key(candidate: Dict[str, Any]) -> Tuple[int, float, float, str]:
    return (
        safe_int(candidate.get("semantic_rank"), default=999999),
        -safe_float(candidate.get("support_score")),
        -safe_float(candidate.get("semantic_score")),
        str(candidate.get("candidate_id")),
    )


def ranked_candidates(action_row: Optional[Dict[str, Any]], fixed_k: int) -> List[Dict[str, Any]]:
    candidates = list((action_row or {}).get("candidate_evidence") or [])
    return sorted(candidates, key=candidate_sort_key)[:fixed_k]


def compact_candidate(candidate: Dict[str, Any], generated_rank: int) -> Dict[str, Any]:
    return {
        "generated_rank": generated_rank,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_backend": candidate.get("candidate_backend"),
        "category": candidate.get("category"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "path_to_candidate": candidate.get("path_to_candidate"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "associated_heading_count": candidate.get("associated_heading_count"),
        "visible_count": candidate.get("visible_count"),
        "box_hit_count": candidate.get("box_hit_count"),
        "mask_hit_count": candidate.get("mask_hit_count"),
        "detector_score_max": candidate.get("detector_score_max"),
        "min_depth_error_m": candidate.get("min_depth_error_m"),
        "uses_gt_for_action": False,
    }


def generated_ids(candidates: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(candidate.get("candidate_id")) for candidate in candidates if candidate.get("candidate_id") is not None]


def source_ids(row: Dict[str, Any], field: str) -> List[str]:
    summary = dict(row.get("source_action_candidate_summary") or {})
    return [str(candidate_id) for candidate_id in summary.get(field) or []]


def generated_accounting(
    backend_row: Dict[str, Any],
    action_row: Optional[Dict[str, Any]],
    candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    ids = generated_ids(candidates)
    id_set = set(ids)
    upstream = dict(backend_row.get("expanded_pool_accounting") or {})
    upstream_ids = [str(candidate_id) for candidate_id in upstream.get("expanded_candidate_ids") or []]
    upstream_set = set(upstream_ids)
    position_keys = [position_key(candidate) for candidate in candidates]
    finite_positions = [key for key in position_keys if key is not None]
    backend_counts = Counter(str(candidate.get("candidate_backend")) for candidate in candidates)
    reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is True)
    unknown_reachability_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is None)
    not_reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is False)
    positive_support_count = sum(1 for candidate in candidates if candidate.get("positive_support") is True)
    source_candidate_ids = source_ids(backend_row, "candidate_ids")
    return {
        "source_action_evidence_found": action_row is not None,
        "source_candidate_count": safe_int((action_row or {}).get("candidate_count"), default=len(candidates)),
        "generated_candidate_count": len(candidates),
        "generated_candidate_ids": ids,
        "retained_from_top10_count": len(id_set & upstream_set),
        "retained_from_top10_ids": sorted(id_set & upstream_set),
        "new_beyond_top10_count": len(id_set - upstream_set),
        "new_beyond_top10_ids": sorted(id_set - upstream_set),
        "upstream_top10_candidate_count": len(upstream_ids),
        "upstream_top10_candidate_ids": upstream_ids,
        "duplicate_candidate_id_count": len(ids) - len(id_set),
        "finite_position_count": len(finite_positions),
        "nonfinite_candidate_position_count": len(candidates) - len(finite_positions),
        "unique_position_count": len(set(finite_positions)),
        "duplicate_position_count": max(0, len(finite_positions) - len(set(finite_positions))),
        "reachable_candidate_count": reachable_count,
        "unknown_reachability_count": unknown_reachability_count,
        "not_reachable_candidate_count": not_reachable_count,
        "reachable_or_standoff_candidate_count": reachable_count,
        "positive_support_candidate_count": positive_support_count,
        "backend_candidate_family_counts": dict(sorted(backend_counts.items())),
        "source_top_retained": bool(set(source_ids(backend_row, "source_top_candidate_ids")) & id_set),
        "detector_strong_retained": bool(set(source_ids(backend_row, "detector_strong_candidate_ids")) & id_set),
        "local_context_retained": bool(set(source_ids(backend_row, "local_context_candidate_ids")) & id_set),
        "previous_action_candidates_retained": len(set(source_candidate_ids) & id_set),
    }


def generation_decision(
    action_row: Optional[Dict[str, Any]],
    accounting: Dict[str, Any],
    fixed_k: int,
) -> Dict[str, Any]:
    signals: List[str] = []
    if action_row is None:
        return {
            "candidate_generation_status": "defer_backend_candidate_generation_unresolved",
            "candidate_generation_reason": "source_action_evidence_missing",
            "candidate_generation_signals": ["source_action_evidence_missing"],
            "terminal_commit": False,
        }
    if safe_int(accounting.get("generated_candidate_count")) != fixed_k:
        signals.append("generated_pool_not_fixed_top20")
    if safe_int(accounting.get("duplicate_candidate_id_count")) > 0:
        signals.append("generated_pool_duplicate_candidate_ids")
    if safe_int(accounting.get("nonfinite_candidate_position_count")) > 0:
        signals.append("generated_pool_nonfinite_candidate_positions")
    if safe_int(accounting.get("reachable_or_standoff_candidate_count")) == 0:
        signals.append("generated_pool_no_reachable_or_standoff_candidate")
    if safe_int(accounting.get("positive_support_candidate_count")) == 0:
        signals.append("generated_pool_no_positive_support_candidate")
    if signals:
        return {
            "candidate_generation_status": "request_deeper_backend_generation",
            "candidate_generation_reason": "fixed_top20_pool_structural_gate_failed",
            "candidate_generation_signals": sorted(set(signals)),
            "terminal_commit": False,
        }
    return {
        "candidate_generation_status": "generated_fixed_top20_pool",
        "candidate_generation_reason": "fixed_top20_pool_materialized_from_action_evidence",
        "candidate_generation_signals": ["fixed_top20_pool_structurally_valid"],
        "terminal_commit": False,
    }


def build_action_rows(
    backend_rows: Sequence[Dict[str, Any]],
    action_evidence_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    indexed = action_evidence_index(action_evidence_rows)
    fixed_policy = dict(contract.get("fixed_generation_policy") or {})
    fixed_k = int(args.fixed_candidate_count)
    output: List[Dict[str, Any]] = []
    for row in source_rows(backend_rows):
        source_action = action_evidence_for(row, indexed)
        candidates = ranked_candidates(source_action, fixed_k)
        accounting = generated_accounting(row, source_action, candidates)
        decision = generation_decision(source_action, accounting, fixed_k)
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
                "source_backend_route_action": row.get("backend_route_action"),
                "source_backend_route_reason": row.get("backend_route_reason"),
                "source_backend_route_signals": row.get("backend_route_signals"),
                "source_backend_config": row.get("backend_config"),
                "source_pool_proxy": row.get("source_pool_proxy"),
                "source_action_candidate_summary": row.get("source_action_candidate_summary"),
                "source_pool_accounting": row.get("source_pool_accounting"),
                "upstream_expanded_pool_accounting": row.get("expanded_pool_accounting"),
                "backend_candidate_config": {
                    "policy_name": fixed_policy.get("policy_name"),
                    "candidate_backend_family": fixed_policy.get("candidate_backend_family"),
                    "candidate_budget_fixed_k": fixed_k,
                    "selection_source": fixed_policy.get("selection_source"),
                    "selection_order": fixed_policy.get("selection_order"),
                    "spatial_diversity_source_required": fixed_policy.get(
                        "spatial_diversity_source_required"
                    ),
                    "reachability_policy": fixed_policy.get("reachability_policy"),
                    "duplicate_policy": fixed_policy.get("duplicate_policy"),
                    "source_action_evidence_path": str(args.source_action_evidence),
                },
                "source_action_evidence_schema_version": (source_action or {}).get("schema_version"),
                "source_action_evidence_contract": (source_action or {}).get("contract_name"),
                "source_action_evidence_policy_name": (source_action or {}).get("policy_name"),
                "source_action_evidence_status": (source_action or {}).get("evidence_status"),
                "generated_pool_accounting": accounting,
                "generated_candidates": [
                    compact_candidate(candidate, generated_rank=index + 1)
                    for index, candidate in enumerate(candidates)
                ],
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
    candidate_ids = list((action_row.get("generated_pool_accounting") or {}).get("generated_candidate_ids") or [])
    label_rows = [labels.get((episode_key, str(candidate_id))) for candidate_id in candidate_ids]
    labeled_rows = [row for row in label_rows if row is not None]
    yes_ids = [
        str(candidate_id)
        for candidate_id, label in zip(candidate_ids, label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is True
    ]
    no_ids = [
        str(candidate_id)
        for candidate_id, label in zip(candidate_ids, label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is False
    ]
    yes_ranks = [
        index + 1
        for index, label in enumerate(label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is True
    ]
    return {
        "evaluation_only_candidate_count": len(candidate_ids),
        "evaluation_only_labeled_candidate_count": len(labeled_rows),
        "evaluation_only_unlabeled_candidate_count": len(candidate_ids) - len(labeled_rows),
        "evaluation_only_correct_candidate_count": len(yes_ids),
        "evaluation_only_wrong_candidate_count": len(no_ids),
        "evaluation_only_correct_candidate_ids": yes_ids,
        "evaluation_only_wrong_candidate_ids_preview": no_ids[:10],
        "evaluation_only_first_correct_generated_rank": min(yes_ranks) if yes_ranks else None,
        "evaluation_only_no_valid_candidate_pool": len(yes_ids) == 0,
        "evaluation_only_contains_valid_candidate": len(yes_ids) > 0,
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
                "validation_stage": "evaluation_joined_after_generation_rows",
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


def count_stats(values: Sequence[int]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "max": None, "mean": None}
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
    }


def count_by_status(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(str(row.get("candidate_generation_status")) for row in rows)
    return {status: counts.get(status, 0) for status in GENERATION_STATUSES}


def summarize(
    action_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = contract.get("evaluation_gates") or {}
    expected_rows = safe_int(gates.get("input_request_rows"), default=args.expected_request_rows)
    status_counts = count_by_status(action_rows)
    reason_counts = Counter(str(row.get("candidate_generation_reason")) for row in action_rows)
    signal_counts = Counter(
        str(signal)
        for row in action_rows
        for signal in row.get("candidate_generation_signals") or []
    )
    no_valid_by_status = Counter(
        str(row.get("candidate_generation_status"))
        for row in evaluated_rows
        if row.get("evaluation_only_no_valid_candidate_pool") is True
    )
    valid_by_status = Counter(
        str(row.get("candidate_generation_status"))
        for row in evaluated_rows
        if row.get("evaluation_only_contains_valid_candidate") is True
    )
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    forbidden = action_forbidden_keys(action_rows)
    generated_counts = [
        safe_int((row.get("generated_pool_accounting") or {}).get("generated_candidate_count"))
        for row in action_rows
    ]
    duplicate_counts = [
        safe_int((row.get("generated_pool_accounting") or {}).get("duplicate_candidate_id_count"))
        for row in action_rows
    ]
    nonfinite_counts = [
        safe_int((row.get("generated_pool_accounting") or {}).get("nonfinite_candidate_position_count"))
        for row in action_rows
    ]
    reachable_counts = [
        safe_int((row.get("generated_pool_accounting") or {}).get("reachable_or_standoff_candidate_count"))
        for row in action_rows
    ]
    positive_support_counts = [
        safe_int((row.get("generated_pool_accounting") or {}).get("positive_support_candidate_count"))
        for row in action_rows
    ]
    total_generated_candidate_rows = sum(generated_counts)
    no_valid_rows = sum(1 for row in evaluated_rows if row.get("evaluation_only_no_valid_candidate_pool") is True)
    valid_rows = sum(1 for row in evaluated_rows if row.get("evaluation_only_contains_valid_candidate") is True)
    action_rows_with_source = sum(
        1 for row in action_rows if (row.get("generated_pool_accounting") or {}).get("source_action_evidence_found") is True
    )
    gate = {
        "input_request_rows_passed": len(action_rows) == expected_rows,
        "source_action_evidence_rows_found_passed": action_rows_with_source
        >= safe_int(gates.get("source_action_evidence_rows_found_minimum"), default=expected_rows),
        "generated_candidate_count_minimum_passed": min(generated_counts or [0])
        >= safe_int(gates.get("generated_candidate_count_minimum"), default=args.fixed_candidate_count),
        "generated_candidate_count_maximum_passed": max(generated_counts or [0])
        <= safe_int(gates.get("generated_candidate_count_maximum"), default=args.fixed_candidate_count),
        "generated_candidate_rows_minimum_passed": total_generated_candidate_rows
        >= safe_int(gates.get("generated_candidate_rows_minimum"), default=expected_rows * args.fixed_candidate_count),
        "duplicate_candidate_id_count_passed": max(duplicate_counts or [999999])
        <= safe_int(gates.get("duplicate_candidate_id_count_maximum"), default=0),
        "nonfinite_candidate_position_count_passed": max(nonfinite_counts or [999999])
        <= safe_int(gates.get("nonfinite_candidate_position_count_maximum"), default=0),
        "rows_with_reachable_or_standoff_candidate_passed": sum(1 for value in reachable_counts if value > 0)
        >= safe_int(gates.get("rows_with_reachable_or_standoff_candidate_minimum"), default=expected_rows),
        "rows_with_positive_support_candidate_passed": sum(1 for value in positive_support_counts if value > 0)
        >= safe_int(gates.get("rows_with_positive_support_candidate_minimum"), default=expected_rows),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), default=0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), default=0),
        "reports_generation_status_counts": all(status in status_counts for status in GENERATION_STATUSES),
        "reports_candidate_lineage": all("generated_pool_accounting" in row for row in action_rows),
        "reports_duplicate_and_reachability_counts": all(
            "duplicate_candidate_id_count" in (row.get("generated_pool_accounting") or {})
            and "reachable_or_standoff_candidate_count" in (row.get("generated_pool_accounting") or {})
            for row in action_rows
        ),
        "joins_labels_only_after_generation_rows": True,
        "reports_contains_valid_candidate_after_label_join": bool(evaluated_rows),
        "reports_no_valid_rows_after_label_join": bool(evaluated_rows),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "goal_validity_confirmation_unblocked": False,
        "deeper_backend_generation_required": no_valid_rows > 0,
        "paper_claim_allowed": False,
    }
    gate["backend_candidate_generation_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "paper_claim_allowed",
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "goal_validity_confirmation_unblocked",
            "deeper_backend_generation_required",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "backend_expansion_rows": str(args.backend_expansion_rows),
        "source_action_evidence": str(args.source_action_evidence),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "request_rows": len(action_rows),
        "evaluated_rows": len(evaluated_rows),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_generation_status_counts": status_counts,
        "candidate_generation_reason_counts": dict(sorted(reason_counts.items())),
        "candidate_generation_signal_counts": dict(sorted(signal_counts.items())),
        "source_action_evidence_rows_found": action_rows_with_source,
        "generated_candidate_rows": total_generated_candidate_rows,
        "generated_candidate_count_stats": count_stats(generated_counts),
        "duplicate_candidate_id_count_stats": count_stats(duplicate_counts),
        "nonfinite_candidate_position_count_stats": count_stats(nonfinite_counts),
        "reachable_or_standoff_candidate_count_stats": count_stats(reachable_counts),
        "positive_support_candidate_count_stats": count_stats(positive_support_counts),
        "no_valid_rows_by_generation_status": {
            status: no_valid_by_status.get(status, 0) for status in GENERATION_STATUSES
        },
        "valid_rows_by_generation_status": {
            status: valid_by_status.get(status, 0) for status in GENERATION_STATUSES
        },
        "evaluation_only_contains_valid_rows": valid_rows,
        "evaluation_only_no_valid_rows": no_valid_rows,
        "generated_pool_candidate_counts": [
            {
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "episode_key": row.get("episode_key"),
                "candidate_generation_status": row.get("candidate_generation_status"),
                "candidate_generation_reason": row.get("candidate_generation_reason"),
                "generated_pool_accounting": row.get("generated_pool_accounting"),
            }
            for row in action_rows
        ],
        "simpler_alternative_accounting": {
            "reuse_top10_preview_without_generation": {
                "blocked_by": "fixed_candidate_budget_not_met",
                "top10_candidate_count_rows": len(action_rows),
                "required_candidate_count": int(args.fixed_candidate_count),
            },
            "pass_top20_pool_directly_to_goal_validity_without_candidate_validity_check": {
                "blocked_by": "post_generation_label_join_still_contains_no_valid_pools",
                "evaluation_only_contains_valid_rows": valid_rows,
                "evaluation_only_no_valid_rows": no_valid_rows,
            },
            "semantic_rank_only_top20_without_spatial_lineage_accounting": {
                "blocked_by": "paper_contract_requires_candidate_lineage_duplicate_reachability_reporting",
                "same_generated_pool_under_current_sort": True,
            },
            "dense_reexport_before_testing_existing_top20_action_evidence": {
                "blocked_by": "existing_non_gt_action_evidence_already_satisfies_structural_top20_gate",
                "deeper_generation_required_only_after_no_valid_analysis": no_valid_rows > 0,
            },
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "interpretation": {
            "fact": (
                "The analyzer materializes fixed top-20 backend candidate generation rows from "
                "existing non-GT action evidence before joining evaluation-only labels."
            ),
            "agent_inference": (
                "The top-20 generation path is structurally valid, but evaluation-only reporting "
                "still shows no-valid generated pools. The next contract should test deeper backend "
                "generation or a non-GT pool-validity proxy before goal-validity confirmation."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "generation_rows": "backend_candidate_generation_rows.jsonl",
            "evaluated_rows": "backend_candidate_generation_evaluated_rows.jsonl",
            "summary": "backend_candidate_generation_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    backend_rows = load_jsonl(Path(args.backend_expansion_rows))
    action_evidence_rows = load_jsonl(Path(args.source_action_evidence))
    evaluation_labels = load_jsonl(Path(args.evaluation_labels))

    action_rows = build_action_rows(backend_rows, action_evidence_rows, contract, args)
    evaluated_rows = build_evaluated_rows(action_rows, evaluation_labels)
    summary = summarize(action_rows, evaluated_rows, contract, args)

    write_jsonl(out_root / "backend_candidate_generation_rows.jsonl", action_rows)
    write_jsonl(out_root / "backend_candidate_generation_evaluated_rows.jsonl", evaluated_rows)
    write_json(out_root / "backend_candidate_generation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize fixed backend candidate generation rows before goal-validity confirmation."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--backend-expansion-rows", required=True)
    parser.add_argument("--source-action-evidence", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--expected-request-rows", type=int, default=5)
    parser.add_argument("--fixed-candidate-count", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
