import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source.v1"
SOURCE_ROUTE_ACTION = "request_goal_validity_confirmation_evidence"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(explicit)
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def candidate_summary(row: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(row.get("action_candidate_summary") or {})
    return {
        "candidate_count": safe_int(summary.get("candidate_count"), 0),
        "candidate_ids": list(summary.get("candidate_ids") or []),
        "detector_strong_candidate_count": safe_int(summary.get("detector_strong_candidate_count"), 0),
        "detector_strong_candidate_ids": list(summary.get("detector_strong_candidate_ids") or []),
        "local_context_candidate_count": safe_int(summary.get("local_context_candidate_count"), 0),
        "local_context_candidate_ids": list(summary.get("local_context_candidate_ids") or []),
        "source_top_candidate_count": safe_int(summary.get("source_top_candidate_count"), 0),
        "source_top_candidate_ids": list(summary.get("source_top_candidate_ids") or []),
        "strong_own_view_candidate_count": safe_int(summary.get("strong_own_view_candidate_count"), 0),
        "strong_own_view_candidate_ids": list(summary.get("strong_own_view_candidate_ids") or []),
    }


def request_id(row: Dict[str, Any]) -> str:
    value = row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id")
    return str(value or "")


def sorted_route_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows if row.get("route_action") == SOURCE_ROUTE_ACTION],
        key=lambda row: (
            request_sort_key(request_id(row)),
            str(row.get("scene_key") or ""),
            str(row.get("query") or ""),
        ),
    )


def compact_source_pool_proxy(row: Dict[str, Any]) -> Dict[str, Any]:
    proxy = dict(row.get("source_pool_proxy") or {})
    allowed_keys = [
        "available",
        "candidate_count",
        "consumed_forbidden_key_count",
        "detector_evidence_allowed_by_proxy",
        "feature_source",
        "known_reachability_count",
        "positive_support_candidate_count",
        "positive_support_top4_count",
        "proxy_reason",
        "proxy_route",
        "reachable_candidate_count",
        "score_ge_0_91_count",
        "semantic_top2_score_gap",
        "source_pool_invalid_proxy",
        "top4_score_range",
        "top_candidate_score",
        "top_score_uncertainty",
    ]
    return {key: proxy.get(key) for key in allowed_keys if key in proxy}


def action_row(row: Dict[str, Any]) -> Dict[str, Any]:
    summary = candidate_summary(row)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_source_before_label_join",
        "expanded_retrieval_request_id": request_id(row),
        "rival_identity_request_id": row.get("rival_identity_request_id"),
        "episode_key": row.get("episode_key"),
        "scene_key": row.get("scene_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "source_schema_version": row.get("schema_version"),
        "source_variant": row.get("source_variant"),
        "source_action": row.get("source_action"),
        "source_reason": row.get("source_reason"),
        "route_action": row.get("route_action"),
        "route_branch": row.get("route_branch"),
        "route_reason": row.get("route_reason"),
        "route_signals": list(row.get("route_signals") or []),
        "pool_guard_status": row.get("pool_guard_status"),
        "pool_guard_reason": row.get("pool_guard_reason"),
        "instance_guard_status": row.get("instance_guard_status"),
        "instance_guard_reason": row.get("instance_guard_reason"),
        "candidate_count": summary["candidate_count"],
        "candidate_ids": summary["candidate_ids"],
        "detector_strong_candidate_count": summary["detector_strong_candidate_count"],
        "detector_strong_candidate_ids": summary["detector_strong_candidate_ids"],
        "local_context_candidate_count": summary["local_context_candidate_count"],
        "local_context_candidate_ids": summary["local_context_candidate_ids"],
        "source_top_candidate_count": summary["source_top_candidate_count"],
        "source_top_candidate_ids": summary["source_top_candidate_ids"],
        "strong_own_view_candidate_count": summary["strong_own_view_candidate_count"],
        "strong_own_view_candidate_ids": summary["strong_own_view_candidate_ids"],
        "source_pool_proxy": compact_source_pool_proxy(row),
        "arbitration_source_status": "fresh_object_relation_evidence_generation_required",
        "object_relation_evidence_available": False,
        "planned_next_action": "request_object_relation_observation_for_fresh_goal_validity_rows",
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def evaluated_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {request_id(row): dict(row) for row in rows if request_id(row)}


def evaluated_row(row: Dict[str, Any], label_row: Dict[str, Any]) -> Dict[str, Any]:
    label_summary = dict(label_row.get("evaluation_candidate_summary") or {})
    return {
        **row,
        "validation_stage": "evaluation_only_fresh_source_after_label_join",
        "evaluation_candidate_summary": label_summary,
        "evaluation_route_has_valid_candidate": label_row.get("evaluation_only_route_has_valid_candidate"),
        "evaluation_previous_success_lost_by_route": label_row.get("evaluation_only_previous_success_lost_by_route"),
        "evaluation_unsafe_previous_commit_prevented": label_row.get("evaluation_only_unsafe_previous_commit_prevented"),
        "evaluation_any_simpler_alternative_unsafe": label_row.get("evaluation_only_any_simpler_alternative_unsafe"),
        "uses_gt_for_analysis": bool(label_row),
    }


def request_id_set(rows: Sequence[Dict[str, Any]]) -> Set[str]:
    return {request_id(row) for row in rows if request_id(row)}


def counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def build_rows(route_rows: Sequence[Dict[str, Any]], evaluated_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    source_rows = sorted_route_rows(route_rows)
    label_rows = evaluated_index(sorted_route_rows(evaluated_rows))
    action_rows = [action_row(row) for row in source_rows]
    analysis_rows = [evaluated_row(row, label_rows.get(str(row.get("expanded_retrieval_request_id")) or "", {})) for row in action_rows]
    return {
        "source_rows": source_rows,
        "action_rows": action_rows,
        "analysis_rows": analysis_rows,
    }


def summarize(
    *,
    contract: Dict[str, Any],
    route_summary: Dict[str, Any],
    bounded_summary: Dict[str, Any],
    bounded_rows: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
    analysis_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_source_gate") or {}
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    request_ids = sorted(request_id_set(action_rows), key=request_sort_key)
    bounded_request_ids = sorted(request_id_set(bounded_rows), key=request_sort_key)
    overlap = sorted(set(request_ids) & set(bounded_request_ids), key=request_sort_key)
    unique_scenes = sorted({str(row.get("scene_key")) for row in action_rows if row.get("scene_key")})
    unique_queries = sorted({str(row.get("query")) for row in action_rows if row.get("query")})
    candidate_counts = [safe_int(row.get("candidate_count"), 0) for row in action_rows]
    evaluation_summaries = [dict(row.get("evaluation_candidate_summary") or {}) for row in analysis_rows]
    gate = {
        "source_route_contract_passed": bool(((route_summary.get("gate") or {}).get("route_contract_gate_passed"))),
        "expected_source_rows_passed": len(action_rows) == safe_int(minimum.get("expected_source_rows"), len(action_rows)),
        "minimum_source_rows_passed": len(action_rows) >= safe_int(minimum.get("minimum_source_rows"), 0),
        "minimum_unique_scenes_passed": len(unique_scenes) >= safe_int(minimum.get("minimum_unique_scenes"), 0),
        "minimum_unique_queries_passed": len(unique_queries) >= safe_int(minimum.get("minimum_unique_queries"), 0),
        "bounded_request_overlap_passed": len(overlap) <= safe_int(minimum.get("bounded_request_overlap_maximum"), 0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(minimum.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_analysis": bool(analysis_rows),
        "object_relation_evidence_generation_required": True,
        "object_relation_arbitration_validation_ready": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    source_gate_keys = [
        "source_route_contract_passed",
        "expected_source_rows_passed",
        "minimum_source_rows_passed",
        "minimum_unique_scenes_passed",
        "minimum_unique_queries_passed",
        "bounded_request_overlap_passed",
        "action_evidence_forbidden_key_gate_passed",
        "terminal_commit_rows_passed",
        "uses_gt_for_action_passed",
    ]
    gate["fresh_source_precheck_gate_passed"] = all(gate[key] is True for key in source_gate_keys)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "route_specific_rows": str(args.route_specific_rows),
            "route_specific_evaluated_rows": str(args.route_specific_evaluated_rows),
            "route_specific_summary": str(args.route_specific_summary),
            "bounded_arbitration_decision_rows": str(args.bounded_arbitration_decision_rows),
            "bounded_arbitration_summary": str(args.bounded_arbitration_summary),
        },
        "route_action_filter": SOURCE_ROUTE_ACTION,
        "source_rows": len(action_rows),
        "evaluated_rows": len(analysis_rows),
        "request_ids": request_ids,
        "unique_scene_count": len(unique_scenes),
        "unique_query_count": len(unique_queries),
        "scene_keys": unique_scenes,
        "queries": unique_queries,
        "candidate_count_sum": sum(candidate_counts),
        "candidate_count_min": min(candidate_counts, default=0),
        "candidate_count_max": max(candidate_counts, default=0),
        "detector_strong_candidate_count_sum": sum(safe_int(row.get("detector_strong_candidate_count"), 0) for row in action_rows),
        "strong_own_view_candidate_count_sum": sum(safe_int(row.get("strong_own_view_candidate_count"), 0) for row in action_rows),
        "local_context_candidate_count_sum": sum(safe_int(row.get("local_context_candidate_count"), 0) for row in action_rows),
        "source_top_candidate_count_sum": sum(safe_int(row.get("source_top_candidate_count"), 0) for row in action_rows),
        "bounded_arbitration_request_ids": bounded_request_ids,
        "bounded_arbitration_overlap_count": len(overlap),
        "bounded_arbitration_overlap_request_ids": overlap,
        "bounded_arbitration_rule_gate_passed": bool(
            ((bounded_summary.get("gate") or {}).get("object_relation_arbitration_rule_gate_passed"))
        ),
        "terminal_commit_rows": len(terminal_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden,
        "route_branch_counts": counter(row.get("route_branch") for row in action_rows),
        "route_reason_counts": counter(row.get("route_reason") for row in action_rows),
        "evaluation_route_has_valid_candidate_counts": counter(
            row.get("evaluation_route_has_valid_candidate") for row in analysis_rows
        ),
        "evaluation_candidate_count_sum": {
            "contains_valid_rows": sum(
                1
                for item in evaluation_summaries
                if item.get("evaluation_only_no_valid_candidate_pool") is False
                and safe_int(item.get("evaluation_only_correct_candidate_count"), 0) > 0
            ),
            "no_valid_rows": sum(
                1 for item in evaluation_summaries if item.get("evaluation_only_no_valid_candidate_pool") is True
            ),
            "candidate_total": sum(candidate_counts),
            "positive_label_candidates": sum(
                safe_int(item.get("evaluation_only_correct_candidate_count"), 0) for item in evaluation_summaries
            ),
            "negative_label_candidates": sum(
                safe_int(item.get("evaluation_only_wrong_candidate_count"), 0) for item in evaluation_summaries
            ),
        },
        "missing_evidence_for_actual_arbitration_validation": list(
            contract.get("missing_evidence_for_actual_arbitration_validation") or []
        ),
        "gate": gate,
        "diagnostic_conclusion": {
            "fresh_predeclared_source_frozen": gate["fresh_source_precheck_gate_passed"],
            "object_relation_evidence_generation_required": True,
            "object_relation_arbitration_validation_allowed_now": False,
            "terminal_policy_allowed": False,
            "recommended_next_action": "plan_and_generate_fresh_object_relation_evidence_for_route_specific_goal_validity_rows",
        },
        "interpretation": {
            "fact": "The source rows are route-specific goal-validity confirmation requests written before evaluation labels are joined.",
            "agent_inference": "The source is fresh relative to the bounded relation-depth guarded arbitration smoke because request-id overlap is zero. It can define the next validation set, but the actual arbitration rule cannot be validated until object-relation evidence is generated for these rows.",
        },
        "output_files": {
            "action_rows": "object_relation_arbitration_fresh_source_action_rows.jsonl",
            "evaluated_rows": "object_relation_arbitration_fresh_source_evaluated_rows.jsonl",
            "summary": "object_relation_arbitration_fresh_source_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(analysis_rows),
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--route-specific-rows", type=Path)
    parser.add_argument("--route-specific-evaluated-rows", type=Path)
    parser.add_argument("--route-specific-summary", type=Path)
    parser.add_argument("--bounded-arbitration-decision-rows", type=Path)
    parser.add_argument("--bounded-arbitration-summary", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.route_specific_rows = source_path(args, contract, "route_specific_rows", "route_specific_rows")
    args.route_specific_evaluated_rows = source_path(
        args,
        contract,
        "route_specific_evaluated_rows",
        "route_specific_evaluated_rows",
    )
    args.route_specific_summary = source_path(args, contract, "route_specific_summary", "route_specific_summary")
    args.bounded_arbitration_decision_rows = source_path(
        args,
        contract,
        "bounded_arbitration_decision_rows",
        "bounded_arbitration_decision_rows",
    )
    args.bounded_arbitration_summary = source_path(
        args,
        contract,
        "bounded_arbitration_summary",
        "bounded_arbitration_summary",
    )

    route_rows = load_jsonl(args.route_specific_rows)
    route_evaluated_rows = load_jsonl(args.route_specific_evaluated_rows)
    route_summary = load_json(args.route_specific_summary)
    bounded_rows = load_jsonl(args.bounded_arbitration_decision_rows)
    bounded_summary = load_json(args.bounded_arbitration_summary)
    rows = build_rows(route_rows, route_evaluated_rows)
    summary = summarize(
        contract=contract,
        route_summary=route_summary,
        bounded_summary=bounded_summary,
        bounded_rows=bounded_rows,
        action_rows=rows["action_rows"],
        analysis_rows=rows["analysis_rows"],
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "object_relation_arbitration_fresh_source_action_rows.jsonl", rows["action_rows"])
    write_jsonl(args.out_root / "object_relation_arbitration_fresh_source_evaluated_rows.jsonl", rows["analysis_rows"])
    write_json(args.out_root / "object_relation_arbitration_fresh_source_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
