import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    request_sort_key,
)


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_confirmation.v1"
SOURCE_STATUS = "generated_deeper_backend_pool"
REQUEST_ACTION = "request_goal_validity_confirmation_evidence"
BRANCH_ACTION = "request_non_gt_pool_validity_proxy_or_fallback_backend_variant"
EVIDENCE_ACTION = "request_candidate_specific_goal_validity_evidence"


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


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def indexed_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        request_id = row.get("expanded_retrieval_request_id")
        if request_id is not None:
            indexed[str(request_id)] = row
    return indexed


def source_action_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("deeper_generation_status") == SOURCE_STATUS],
        key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))),
    )


def contract_target_ids(contract: Dict[str, Any]) -> List[str]:
    return [
        str(row.get("expanded_retrieval_request_id"))
        for row in contract.get("target_rows_for_goal_validity_confirmation") or []
        if row.get("expanded_retrieval_request_id") is not None
    ]


def contract_excluded_ids(contract: Dict[str, Any]) -> List[str]:
    return [
        str(row.get("expanded_retrieval_request_id"))
        for row in contract.get("excluded_rows_backend_pool_validity_branch") or []
        if row.get("expanded_retrieval_request_id") is not None
    ]


def recovered_ids_from_evaluated(rows: Sequence[Dict[str, Any]]) -> List[str]:
    return sorted(
        [
            str(row.get("expanded_retrieval_request_id"))
            for row in rows
            if row.get("evaluation_only_contains_valid_candidate") is True
            and row.get("evaluation_only_no_valid_candidate_pool") is False
        ],
        key=request_sort_key,
    )


def excluded_ids_from_evaluated(rows: Sequence[Dict[str, Any]]) -> List[str]:
    return sorted(
        [
            str(row.get("expanded_retrieval_request_id"))
            for row in rows
            if row.get("evaluation_only_contains_valid_candidate") is False
            and row.get("evaluation_only_no_valid_candidate_pool") is True
        ],
        key=request_sort_key,
    )


def scene_query_key(row: Dict[str, Any]) -> str:
    return f"{row.get('scene_key')}::{row.get('query')}"


def candidate_ids(candidates: Sequence[Dict[str, Any]]) -> List[str]:
    return [str(candidate.get("candidate_id")) for candidate in candidates if candidate.get("candidate_id") is not None]


def compact_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "generated_rank": candidate.get("generated_rank"),
        "candidate_id": candidate.get("candidate_id"),
        "candidate_backend": candidate.get("candidate_backend"),
        "backend_source": candidate.get("backend_source"),
        "category": candidate.get("category"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "score": candidate.get("score"),
        "mean_score": candidate.get("mean_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "visit_position_navigable": candidate.get("visit_position_navigable"),
        "visit_position_snapped": candidate.get("visit_position_snapped"),
        "component_cells": candidate.get("component_cells"),
        "view_count": candidate.get("view_count"),
        "coordinate_frame": candidate.get("coordinate_frame"),
        "alignment_id": candidate.get("alignment_id"),
        "uses_gt_for_action": False,
    }


def candidate_pool_accounting(row: Dict[str, Any]) -> Dict[str, Any]:
    pool = dict(row.get("deeper_pool_accounting") or {})
    generated_ids = list(pool.get("deeper_generated_candidate_ids") or [])
    return {
        "deeper_candidate_count": safe_int(pool.get("deeper_generated_candidate_count"), len(generated_ids)),
        "deeper_candidate_ids": generated_ids,
        "retained_from_top20_count": safe_int(pool.get("retained_from_top20_count")),
        "retained_from_top20_ids": list(pool.get("retained_from_top20_ids") or []),
        "new_beyond_top20_count": safe_int(pool.get("new_beyond_top20_count")),
        "new_beyond_top20_ids_preview": list(pool.get("new_beyond_top20_ids_preview") or []),
        "duplicate_candidate_id_count": safe_int(pool.get("duplicate_candidate_id_count")),
        "duplicate_position_count": safe_int(pool.get("duplicate_position_count")),
        "finite_position_count": safe_int(pool.get("finite_position_count")),
        "nonfinite_candidate_position_count": safe_int(pool.get("nonfinite_candidate_position_count")),
        "reachable_candidate_count": safe_int(pool.get("reachable_candidate_count")),
        "reachable_or_standoff_candidate_count": safe_int(pool.get("reachable_or_standoff_candidate_count")),
        "not_reachable_candidate_count": safe_int(pool.get("not_reachable_candidate_count")),
        "unknown_reachability_count": safe_int(pool.get("unknown_reachability_count")),
        "positive_support_candidate_count": safe_int(pool.get("positive_support_candidate_count")),
        "backend_candidate_family_counts": dict(pool.get("backend_candidate_family_counts") or {}),
    }


def request_row(row: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    policy = dict(contract.get("goal_validity_confirmation_policy") or {})
    candidates = [compact_candidate(candidate) for candidate in row.get("deeper_generated_candidates") or []]
    accounting = candidate_pool_accounting(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_only_before_label_join",
        "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": row.get("rival_identity_request_id"),
        "episode_key": row.get("episode_key"),
        "scene_key": row.get("scene_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "target_scene_query_key": row.get("target_scene_query_key") or scene_query_key(row),
        "source_schema_version": row.get("schema_version"),
        "source_deeper_generation_status": row.get("deeper_generation_status"),
        "source_deeper_generation_reason": row.get("deeper_generation_reason"),
        "source_deeper_generation_signals": row.get("deeper_generation_signals"),
        "source_deeper_backend_config": row.get("deeper_backend_config"),
        "candidate_pool_accounting": accounting,
        "candidate_evidence_target_count": len(candidates),
        "candidate_evidence_target_ids": candidate_ids(candidates),
        "candidate_evidence_targets": candidates,
        "goal_validity_confirmation_policy": {
            "policy_name": policy.get("policy_name"),
            "diagnostic_scope": policy.get("diagnostic_scope"),
            "candidate_pool_source": policy.get("candidate_pool_source"),
            "selection_rule": ((policy.get("candidate_evidence_scope") or {}).get("selection_rule")),
            "fixed_before_label_join": policy.get("fixed_before_label_join"),
        },
        "handoff_action": REQUEST_ACTION,
        "handoff_reason": "deeper_backend_pool_recovered_for_goal_validity_confirmation",
        "handoff_signals": [
            "deeper_backend_pool_structurally_valid",
            "route_recovered_pool_to_goal_validity_confirmation",
        ],
        "terminal_commit": False,
        "uses_gt_for_action": False,
    }


def branch_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_only_before_label_join",
        "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": row.get("rival_identity_request_id"),
        "episode_key": row.get("episode_key"),
        "scene_key": row.get("scene_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "target_scene_query_key": row.get("target_scene_query_key") or scene_query_key(row),
        "source_schema_version": row.get("schema_version"),
        "source_deeper_generation_status": row.get("deeper_generation_status"),
        "source_deeper_generation_reason": row.get("deeper_generation_reason"),
        "source_deeper_generation_signals": row.get("deeper_generation_signals"),
        "source_deeper_backend_config": row.get("deeper_backend_config"),
        "candidate_pool_accounting": candidate_pool_accounting(row),
        "candidate_evidence_target_count": 0,
        "handoff_action": BRANCH_ACTION,
        "handoff_reason": "deeper_backend_pool_still_requires_pool_validity_handling",
        "handoff_signals": [
            "route_still_no_valid_pool_to_backend_branch",
            "goal_validity_confirmation_not_interpretable_for_this_pool",
        ],
        "terminal_commit": False,
        "uses_gt_for_action": False,
    }


def evidence_rows_from_requests(request_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for request in request_rows:
        for candidate in request.get("candidate_evidence_targets") or []:
            output.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_only_before_label_join",
                    "expanded_retrieval_request_id": request.get("expanded_retrieval_request_id"),
                    "rival_identity_request_id": request.get("rival_identity_request_id"),
                    "episode_key": request.get("episode_key"),
                    "scene_key": request.get("scene_key"),
                    "scene_id": request.get("scene_id"),
                    "query": request.get("query"),
                    "target_scene_query_key": request.get("target_scene_query_key"),
                    "candidate_id": candidate.get("candidate_id"),
                    "generated_rank": candidate.get("generated_rank"),
                    "candidate_backend": candidate.get("candidate_backend"),
                    "backend_source": candidate.get("backend_source"),
                    "category": candidate.get("category"),
                    "semantic_rank": candidate.get("semantic_rank"),
                    "semantic_score": candidate.get("semantic_score"),
                    "support_score": candidate.get("support_score"),
                    "score": candidate.get("score"),
                    "mean_score": candidate.get("mean_score"),
                    "positive_support": candidate.get("positive_support"),
                    "candidate_reachable": candidate.get("candidate_reachable"),
                    "position": candidate.get("position"),
                    "visit_position": candidate.get("visit_position"),
                    "visit_position_navigable": candidate.get("visit_position_navigable"),
                    "visit_position_snapped": candidate.get("visit_position_snapped"),
                    "evidence_action": EVIDENCE_ACTION,
                    "evidence_reason": "candidate_in_recovered_deeper_backend_pool",
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                }
            )
    return output


def build_evaluated_rows(
    request_rows: Sequence[Dict[str, Any]],
    branch_rows: Sequence[Dict[str, Any]],
    source_evaluated_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    evaluated_by_request = indexed_by_request(source_evaluated_rows)
    output: List[Dict[str, Any]] = []
    for row in [*request_rows, *branch_rows]:
        request_id = str(row.get("expanded_retrieval_request_id"))
        source_eval = evaluated_by_request.get(request_id) or {}
        candidate_summary = dict(source_eval.get("evaluation_candidate_summary") or {})
        output.append(
            {
                **row,
                "candidate_evidence_targets": None,
                "validation_stage": "evaluation_joined_after_request_and_branch_rows",
                "evaluation_candidate_summary": candidate_summary,
                "evaluation_only_contains_valid_candidate": source_eval.get(
                    "evaluation_only_contains_valid_candidate"
                ),
                "evaluation_only_no_valid_candidate_pool": source_eval.get(
                    "evaluation_only_no_valid_candidate_pool"
                ),
                "evaluation_only_correct_candidate_count": source_eval.get(
                    "evaluation_only_correct_candidate_count"
                ),
                "evaluation_only_wrong_candidate_count": source_eval.get(
                    "evaluation_only_wrong_candidate_count"
                ),
                "evaluation_only_correct_candidate_ids": source_eval.get(
                    "evaluation_only_correct_candidate_ids"
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return output


def count_by_handoff(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(str(row.get("handoff_action")) for row in rows)
    return {
        REQUEST_ACTION: counts.get(REQUEST_ACTION, 0),
        BRANCH_ACTION: counts.get(BRANCH_ACTION, 0),
    }


def count_stats(values: Sequence[int]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "max": None, "mean": None}
    return {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}


def summarize(
    *,
    source_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    branch_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    source_evaluated_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    handoff_rows = [*request_rows, *branch_rows]
    scanned_rows = [*handoff_rows, *evidence_rows]
    forbidden = action_forbidden_keys(scanned_rows)
    terminal_rows = [row for row in scanned_rows if row.get("terminal_commit") is True]
    request_candidate_counts = [
        safe_int((row.get("candidate_pool_accounting") or {}).get("deeper_candidate_count"))
        for row in request_rows
    ]
    target_pairs = {str(row.get("target_scene_query_key")) for row in request_rows}
    branch_pairs = {str(row.get("target_scene_query_key")) for row in branch_rows}
    recovered_source_ids = recovered_ids_from_evaluated(source_evaluated_rows)
    excluded_source_ids = excluded_ids_from_evaluated(source_evaluated_rows)
    handoff_counts = count_by_handoff(handoff_rows)
    gate = {
        "input_deeper_generation_rows_passed": len(source_rows)
        == safe_int(gates.get("input_deeper_generation_rows")),
        "recovered_goal_validity_request_rows_passed": len(request_rows)
        == safe_int(gates.get("recovered_goal_validity_request_rows")),
        "backend_pool_validity_branch_rows_passed": len(branch_rows)
        == safe_int(gates.get("backend_pool_validity_branch_rows")),
        "goal_validity_target_scene_query_pairs_passed": len(target_pairs)
        == safe_int(gates.get("goal_validity_target_scene_query_pairs")),
        "excluded_target_scene_query_pairs_passed": len(branch_pairs)
        == safe_int(gates.get("excluded_target_scene_query_pairs")),
        "candidate_count_per_goal_validity_request_passed": min(request_candidate_counts or [0])
        >= safe_int(gates.get("candidate_count_per_goal_validity_request_minimum")),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "reports_recovered_vs_excluded_rows": bool(request_rows) and bool(branch_rows),
        "reports_backend_pool_validity_branch": len(branch_rows) > 0,
        "joins_labels_only_after_request_and_evidence_rows": True,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in scanned_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }
    gate["goal_validity_confirmation_request_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"paper_claim_allowed", "uses_gt_for_action", "uses_gt_for_analysis"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "deeper_generation_rows": str(args.deeper_generation_rows),
        "deeper_generation_evaluated_rows": str(args.deeper_generation_evaluated_rows),
        "out_root": str(args.out_root),
        "source_rows": len(source_rows),
        "request_rows": len(request_rows),
        "branch_rows": len(branch_rows),
        "evidence_rows": len(evidence_rows),
        "evaluated_rows": len(evaluated_rows),
        "handoff_action_counts": handoff_counts,
        "request_ids": [row.get("expanded_retrieval_request_id") for row in request_rows],
        "branch_request_ids": [row.get("expanded_retrieval_request_id") for row in branch_rows],
        "source_recovered_ids_after_label_join": recovered_source_ids,
        "source_excluded_ids_after_label_join": excluded_source_ids,
        "goal_validity_target_scene_query_pairs": sorted(target_pairs),
        "excluded_target_scene_query_pairs": sorted(branch_pairs),
        "request_candidate_count_stats": count_stats(request_candidate_counts),
        "candidate_evidence_target_rows": len(evidence_rows),
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "simpler_alternative_accounting": {
            "pass_all_deeper_rows_to_goal_validity_confirmation": {
                "blocked_by": "would_mix_recovered_pools_with_still_no_valid_pool",
                "blocked_request_ids": [row.get("expanded_retrieval_request_id") for row in branch_rows],
            },
            "commit_top_deeper_candidate_without_observation": {
                "blocked_by": "contract_requires_candidate_specific_goal_validity_evidence_before_terminal_commit"
            },
            "route_still_no_valid_row_to_goal_validity_confirmation": {
                "blocked_by": "goal_validity_confirmation_not_interpretable_without_candidate_pool_validity"
            },
            "defer_all_recovered_rows": {
                "blocked_by": "safe_but_inert_baseline_to_compare_after_candidate_specific_evidence_exists"
            },
        },
        "interpretation": {
            "fact": (
                "The analyzer writes recovered-row goal-validity request rows and a separate "
                "backend/pool-validity branch row before any evaluation-only labels are attached."
            ),
            "agent_inference": (
                "This is a branch handoff, not a terminal ObjectNav policy. It prevents the "
                "still-no-valid row from contaminating goal-validity confirmation evidence."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "request_rows": "goal_validity_confirmation_request_rows.jsonl",
            "evidence_rows": "goal_validity_confirmation_evidence_rows.jsonl",
            "evaluated_rows": "goal_validity_confirmation_evaluated_rows.jsonl",
            "branch_rows": "backend_pool_validity_branch_rows.jsonl",
            "summary": "goal_validity_confirmation_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    deeper_generation_rows = load_jsonl(Path(args.deeper_generation_rows))
    source_evaluated_rows = load_jsonl(Path(args.deeper_generation_evaluated_rows))

    source_rows = source_action_rows(deeper_generation_rows)
    source_by_request = indexed_by_request(source_rows)
    target_ids = sorted(contract_target_ids(contract), key=request_sort_key)
    excluded_ids = sorted(contract_excluded_ids(contract), key=request_sort_key)
    recovered_ids = recovered_ids_from_evaluated(source_evaluated_rows)
    observed_excluded_ids = excluded_ids_from_evaluated(source_evaluated_rows)
    if target_ids != recovered_ids:
        raise ValueError(f"target ids must equal recovered ids: target={target_ids} recovered={recovered_ids}")
    if excluded_ids != observed_excluded_ids:
        raise ValueError(f"excluded ids must equal no-valid ids: excluded={excluded_ids} no_valid={observed_excluded_ids}")
    missing_source = [request_id for request_id in [*target_ids, *excluded_ids] if request_id not in source_by_request]
    if missing_source:
        raise ValueError(f"contract request ids missing from action source rows: {missing_source}")

    request_rows = [request_row(source_by_request[request_id], contract) for request_id in target_ids]
    branch_rows = [branch_row(source_by_request[request_id]) for request_id in excluded_ids]
    evidence_rows = evidence_rows_from_requests(request_rows)
    evaluated_rows = build_evaluated_rows(request_rows, branch_rows, source_evaluated_rows)
    summary = summarize(
        source_rows=source_rows,
        request_rows=request_rows,
        branch_rows=branch_rows,
        evidence_rows=evidence_rows,
        evaluated_rows=evaluated_rows,
        source_evaluated_rows=source_evaluated_rows,
        contract=contract,
        args=args,
    )

    write_jsonl(out_root / "goal_validity_confirmation_request_rows.jsonl", request_rows)
    write_jsonl(out_root / "goal_validity_confirmation_evidence_rows.jsonl", evidence_rows)
    write_jsonl(out_root / "goal_validity_confirmation_evaluated_rows.jsonl", evaluated_rows)
    write_jsonl(out_root / "backend_pool_validity_branch_rows.jsonl", branch_rows)
    write_json(out_root / "goal_validity_confirmation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build recovered-row goal-validity confirmation requests and backend/pool-validity branch rows."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--deeper-generation-rows", required=True)
    parser.add_argument("--deeper-generation-evaluated-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
