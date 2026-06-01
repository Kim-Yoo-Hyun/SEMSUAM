import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_partial_relation_depth_inputs.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1"
)
TARGET_BRANCH = "partial_relation_depth_true_goal"
TARGET_ACTION = "request_additional_relation_depth_evidence"
FAILED_EVIDENCE_STATUSES = {
    "relation_depth_recheck_partial",
    "relation_depth_recheck_unresolved",
}


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


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("target_candidate_id") or "")


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def context_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), str(row.get("target_candidate_id") or row.get("candidate_id") or ""))


def unique_preserve_order(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        item = str(value)
        if not item or item in seen:
            continue
        output.append(item)
        seen.add(item)
    return output


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def target_request_ids(contract: Dict[str, Any]) -> List[str]:
    scope = contract.get("target_scope") or {}
    return sorted(
        [str(row.get("expanded_retrieval_request_id")) for row in scope.get("target_requests") or []],
        key=request_sort_key,
    )


def target_candidate_keys(candidate_rows: Sequence[Dict[str, Any]]) -> List[Tuple[str, str]]:
    keys: List[Tuple[str, str]] = []
    for row in candidate_rows:
        if str(row.get("selected_next_branch")) != TARGET_BRANCH:
            continue
        if str(row.get("selected_next_action")) != TARGET_ACTION:
            continue
        key = row_key(row)
        if all(key):
            keys.append(key)
    return sorted(set(keys), key=lambda item: (request_sort_key(item[0]), safe_int(item[1].split(":")[-1]), item[1]))


def first_by_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = row_key(row)
        if all(key) and key not in indexed:
            indexed[key] = dict(row)
    return indexed


def rows_by_key(rows: Sequence[Dict[str, Any]], key_fn=row_key) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = key_fn(row)
        if all(key):
            grouped[key].append(dict(row))
    return grouped


def request_rows(branch_request_rows: Sequence[Dict[str, Any]], expected_ids: Sequence[str]) -> List[Dict[str, Any]]:
    by_request = {request_id(row): row for row in branch_request_rows if request_id(row)}
    output: List[Dict[str, Any]] = []
    for request_index, rid in enumerate(expected_ids):
        source = by_request.get(rid)
        if source is None:
            continue
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_request",
                "policy": "ExpandedRetrievalGoalValidityPartialRelationDepthObservation",
                "builder_name": "partial_relation_depth_observation_inputs_v1",
                "request_index": request_index,
                "episode_key": source.get("episode_key"),
                "scene_id": source.get("scene_id"),
                "scene_key": source.get("scene_key"),
                "query": source.get("query"),
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": source.get("rival_identity_request_id") or rid,
                "selected_next_branch": source.get("selected_next_branch"),
                "selected_next_action": source.get("selected_next_action"),
                "remaining_request_branch_names": list(source.get("remaining_request_branch_names") or []),
                "terminal_arbitration_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def target_candidate_row(
    *,
    source: Dict[str, Any],
    evidence: Optional[Dict[str, Any]],
    plan: Optional[Dict[str, Any]],
    target_index: int,
) -> Dict[str, Any]:
    evidence = evidence or {}
    plan = plan or {}
    cid = candidate_id(source)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_partial_relation_depth_target_candidate",
        "policy": "ExpandedRetrievalGoalValidityPartialRelationDepthObservation",
        "builder_name": "partial_relation_depth_observation_inputs_v1",
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "expanded_retrieval_request_id": request_id(source),
        "rival_identity_request_id": source.get("rival_identity_request_id"),
        "candidate_id": cid,
        "target_candidate_id": cid,
        "target_index": target_index,
        "target_generated_rank": source.get("target_generated_rank") or evidence.get("target_generated_rank"),
        "target_semantic_rank": source.get("target_semantic_rank") or evidence.get("target_semantic_rank"),
        "target_semantic_score": evidence.get("target_semantic_score"),
        "target_support_score": evidence.get("target_support_score"),
        "target_score": evidence.get("target_score"),
        "target_positive_support": evidence.get("target_positive_support"),
        "candidate_branch_names": list(source.get("candidate_branch_names") or []),
        "selected_next_branch": source.get("selected_next_branch"),
        "selected_next_action": source.get("selected_next_action"),
        "target_position": evidence.get("target_position") or plan.get("target_position"),
        "target_visit_position": evidence.get("target_visit_position") or plan.get("target_visit_position"),
        "target_candidate_role": evidence.get("target_candidate_role") or plan.get("target_candidate_role"),
        "prior_relation_depth_status": evidence.get("evidence_status"),
        "prior_depth_consistent_count": evidence.get("depth_consistent_count"),
        "prior_depth_mismatch_count": evidence.get("depth_mismatch_count"),
        "prior_visible_count": evidence.get("visible_count"),
        "prior_candidate_association_count": evidence.get("candidate_association_count"),
        "prior_relation_anchor_candidate_ids": list(evidence.get("relation_anchor_candidate_ids") or []),
        "prior_relation_anchor_count": evidence.get("relation_anchor_count"),
        "terminal_arbitration_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def failed_evidence_row(row: Dict[str, Any], failed_evidence_index: int) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_partial_relation_depth_failed_evidence",
        "policy": "ExpandedRetrievalGoalValidityPartialRelationDepthObservation",
        "builder_name": "partial_relation_depth_observation_inputs_v1",
        "failed_evidence_index": failed_evidence_index,
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "scene_key": row.get("scene_key"),
        "query": row.get("query"),
        "expanded_retrieval_request_id": request_id(row),
        "rival_identity_request_id": row.get("rival_identity_request_id"),
        "candidate_id": candidate_id(row),
        "target_candidate_id": candidate_id(row),
        "relation_depth_evidence_status": row.get("evidence_status"),
        "standoff_direction_source": row.get("standoff_direction_source"),
        "standoff_relation_anchor_candidate_id": row.get("standoff_relation_anchor_candidate_id"),
        "standoff_distance_requested": row.get("standoff_distance_requested"),
        "standoff_target_horizontal_distance": row.get("standoff_target_horizontal_distance"),
        "target_distance_from_viewpoint_m": row.get("target_distance_from_viewpoint_m"),
        "target_position": row.get("target_position"),
        "target_visit_position": row.get("target_visit_position"),
        "relation_anchor_candidate_ids": list(row.get("relation_anchor_candidate_ids") or []),
        "relation_anchor_count": row.get("relation_anchor_count"),
        "depth_consistent_count": row.get("depth_consistent_count"),
        "depth_mismatch_count": row.get("depth_mismatch_count"),
        "depth_match_count": row.get("depth_match_count"),
        "visible_count": row.get("visible_count"),
        "inside_mask_count": row.get("inside_mask_count"),
        "inside_box_count": row.get("inside_box_count"),
        "candidate_association_count": row.get("candidate_association_count"),
        "direction_source_coverage_count": row.get("direction_source_coverage_count"),
        "projection_status_counts": dict(row.get("projection_status_counts") or {}),
        "depth_check_status_counts": dict(row.get("depth_check_status_counts") or {}),
        "projection_anchor_offset_counts": dict(row.get("projection_anchor_offset_counts") or {}),
        "relation_depth_completion_action": TARGET_ACTION,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def context_anchor_row(row: Dict[str, Any], context_index: int) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_partial_relation_depth_context_anchor",
        "policy": "ExpandedRetrievalGoalValidityPartialRelationDepthObservation",
        "builder_name": "partial_relation_depth_observation_inputs_v1",
        "context_anchor_index": context_index,
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "scene_key": row.get("scene_key"),
        "query": row.get("query"),
        "expanded_retrieval_request_id": request_id(row),
        "rival_identity_request_id": row.get("rival_identity_request_id"),
        "candidate_id": str(row.get("target_candidate_id") or row.get("candidate_id")),
        "target_candidate_id": str(row.get("target_candidate_id") or row.get("candidate_id")),
        "context_candidate_id": row.get("context_candidate_id"),
        "context_candidate_role": row.get("context_candidate_role"),
        "context_generated_rank": row.get("context_generated_rank"),
        "context_position": row.get("context_position"),
        "context_visit_position": row.get("context_visit_position"),
        "horizontal_distance_m": row.get("horizontal_distance_m"),
        "relation_predicates": list(row.get("relation_predicates") or []),
        "anchor_available_proxy": bool(row.get("anchor_available_proxy")),
        "near_1m_proxy": row.get("near_1m_proxy"),
        "near_2m_proxy": row.get("near_2m_proxy"),
        "near_4m_proxy": row.get("near_4m_proxy"),
        "overlap_proxy": row.get("overlap_proxy"),
        "same_component_proxy": row.get("same_component_proxy"),
        "same_support_surface_proxy": row.get("same_support_surface_proxy"),
        "x_delta_context_minus_candidate_m": row.get("x_delta_context_minus_candidate_m"),
        "y_delta_context_minus_candidate_m": row.get("y_delta_context_minus_candidate_m"),
        "z_delta_context_minus_candidate_m": row.get("z_delta_context_minus_candidate_m"),
        "context_detector_associated_rows": row.get("context_detector_associated_rows"),
        "context_detector_visible_rows": row.get("context_detector_visible_rows"),
        "context_detector_inside_mask_rows": row.get("context_detector_inside_mask_rows"),
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_outputs(
    *,
    contract: Dict[str, Any],
    branch_request_rows: Sequence[Dict[str, Any]],
    branch_candidate_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
    existing_plan_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    expected_ids = target_request_ids(contract)
    requests = request_rows(branch_request_rows, expected_ids)
    candidate_source_rows = [
        dict(row)
        for row in branch_candidate_rows
        if request_id(row) in set(expected_ids)
        and str(row.get("selected_next_branch")) == TARGET_BRANCH
        and str(row.get("selected_next_action")) == TARGET_ACTION
    ]
    candidate_source_rows.sort(
        key=lambda row: (
            request_sort_key(request_id(row)),
            safe_int(row.get("target_generated_rank")),
            candidate_id(row),
        )
    )
    candidate_keys = set(target_candidate_keys(candidate_source_rows))
    evidence_grouped = rows_by_key(evidence_rows)
    existing_plan_first = first_by_key(existing_plan_rows)
    target_rows = [
        target_candidate_row(
            source=row,
            evidence=(evidence_grouped.get(row_key(row)) or [{}])[0],
            plan=existing_plan_first.get(row_key(row)),
            target_index=index,
        )
        for index, row in enumerate(candidate_source_rows)
    ]

    failed_rows: List[Dict[str, Any]] = []
    for row in evidence_rows:
        if row_key(row) not in candidate_keys:
            continue
        if str(row.get("evidence_status")) not in FAILED_EVIDENCE_STATUSES:
            continue
        failed_rows.append(failed_evidence_row(row, len(failed_rows)))
    failed_rows.sort(
        key=lambda row: (
            request_sort_key(request_id(row)),
            safe_int(row.get("target_generated_rank")),
            candidate_id(row),
            safe_int(row.get("failed_evidence_index")),
        )
    )
    for index, row in enumerate(failed_rows):
        row["failed_evidence_index"] = index

    context_anchor_rows: List[Dict[str, Any]] = []
    for row in context_rows:
        if context_key(row) not in candidate_keys:
            continue
        if row.get("anchor_available_proxy") is not True:
            continue
        context_anchor_rows.append(context_anchor_row(row, len(context_anchor_rows)))
    context_anchor_rows.sort(
        key=lambda row: (
            request_sort_key(request_id(row)),
            candidate_id(row),
            safe_int(row.get("context_generated_rank")),
            str(row.get("context_candidate_id")),
        )
    )
    for index, row in enumerate(context_anchor_rows):
        row["context_anchor_index"] = index

    existing_plan_matches = [row for row in existing_plan_rows if row_key(row) in candidate_keys]
    return {
        "request_rows": requests,
        "target_candidate_rows": target_rows,
        "failed_evidence_rows": failed_rows,
        "context_anchor_rows": context_anchor_rows,
        "existing_plan_rows": existing_plan_matches,
    }


def summarize(
    *,
    contract: Dict[str, Any],
    branch_summary: Dict[str, Any],
    outputs: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    request_rows_out = outputs["request_rows"]
    candidate_rows = outputs["target_candidate_rows"]
    failed_rows = outputs["failed_evidence_rows"]
    context_rows = outputs["context_anchor_rows"]
    existing_plan_rows = outputs["existing_plan_rows"]
    all_action_rows = [*request_rows_out, *candidate_rows, *failed_rows, *context_rows]
    forbidden = action_forbidden_keys(all_action_rows)
    gates = contract.get("evaluation_gates") or {}
    scope = contract.get("target_scope") or {}
    closure_gate = (branch_summary.get("gate") or {}).get("unique_support_branch_closure_gate_passed")
    context_by_target = Counter(row_key(row) for row in context_rows)
    failed_by_target = Counter(row_key(row) for row in failed_rows)
    candidate_position_missing = [
        row for row in candidate_rows if not row.get("target_position") or not row.get("target_visit_position")
    ]
    gate = {
        "source_branch_closure_gate_passed": bool(closure_gate),
        "expected_request_rows_passed": len(request_rows_out) == safe_int(scope.get("expected_request_rows"), 0),
        "expected_target_candidate_rows_passed": len(candidate_rows) == safe_int(scope.get("expected_target_candidate_rows"), 0),
        "expected_failed_relation_depth_evidence_rows_passed": len(failed_rows)
        == safe_int(scope.get("expected_failed_relation_depth_evidence_rows"), 0),
        "expected_partial_relation_depth_rows_passed": sum(
            1 for row in failed_rows if row.get("relation_depth_evidence_status") == "relation_depth_recheck_partial"
        )
        == safe_int(scope.get("expected_partial_relation_depth_rows"), 0),
        "expected_unresolved_relation_depth_rows_passed": sum(
            1 for row in failed_rows if row.get("relation_depth_evidence_status") == "relation_depth_recheck_unresolved"
        )
        == safe_int(scope.get("expected_unresolved_relation_depth_rows"), 0),
        "expected_context_anchor_rows_passed": len(context_rows) == safe_int(scope.get("expected_context_anchor_rows"), 0),
        "expected_existing_plan_rows_for_same_targets_passed": len(existing_plan_rows)
        == safe_int(scope.get("expected_existing_plan_rows_for_same_targets"), 0),
        "minimum_context_anchor_rows_per_target_candidate_passed": bool(context_by_target)
        and min(context_by_target.values()) >= safe_int(
            ((contract.get("input_builder_contract") or {}).get("context_anchor_rule") or {}).get(
                "minimum_context_anchor_rows_per_target_candidate"
            ),
            0,
        ),
        "all_target_candidates_have_failed_evidence_passed": bool(failed_by_target)
        and len(failed_by_target) == len(candidate_rows),
        "candidate_positions_available_passed": len(candidate_position_missing) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": all(row.get("terminal_commit") is not True for row in all_action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in all_action_rows),
        "paper_claim_allowed": False,
    }
    gate["partial_relation_depth_input_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    request_ids = sorted({request_id(row) for row in request_rows_out}, key=request_sort_key)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "branch_closure_summary": str(args.branch_closure_summary),
            "next_branch_request_rows": str(args.next_branch_request_rows),
            "next_branch_candidate_rows": str(args.next_branch_candidate_rows),
            "fresh_object_relation_evidence_rows": str(args.fresh_object_relation_evidence_rows),
            "fresh_object_relation_context_rows": str(args.fresh_object_relation_context_rows),
            "fresh_object_relation_plan_rows": str(args.fresh_object_relation_plan_rows),
        },
        "target_branch": TARGET_BRANCH,
        "target_action": TARGET_ACTION,
        "request_rows": len(request_rows_out),
        "target_candidate_rows": len(candidate_rows),
        "failed_relation_depth_evidence_rows": len(failed_rows),
        "context_anchor_rows": len(context_rows),
        "existing_plan_rows_for_same_targets": len(existing_plan_rows),
        "request_ids": request_ids,
        "target_candidate_rows_by_request": dict(sorted(Counter(request_id(row) for row in candidate_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "failed_evidence_rows_by_request": dict(sorted(Counter(request_id(row) for row in failed_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "failed_evidence_rows_by_target": {
            f"{key[0]}::{key[1]}": value
            for key, value in sorted(failed_by_target.items(), key=lambda item: (request_sort_key(item[0][0]), item[0][1]))
        },
        "context_anchor_rows_by_target": {
            f"{key[0]}::{key[1]}": value
            for key, value in sorted(context_by_target.items(), key=lambda item: (request_sort_key(item[0][0]), item[0][1]))
        },
        "relation_depth_evidence_status_counts": compact_counter(row.get("relation_depth_evidence_status") for row in failed_rows),
        "failed_direction_counts": compact_counter(row.get("standoff_direction_source") for row in failed_rows),
        "candidate_positions_missing": len(candidate_position_missing),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "request_rows": "partial_relation_depth_request_rows.jsonl",
            "target_candidate_rows": "partial_relation_depth_target_candidate_rows.jsonl",
            "failed_evidence_rows": "partial_relation_depth_failed_evidence_rows.jsonl",
            "context_anchor_rows": "partial_relation_depth_context_anchor_rows.jsonl",
            "summary": "partial_relation_depth_input_summary.json",
        },
        "interpretation": {
            "fact": "The materializer writes action-time partial relation-depth rows before any evaluation-label join.",
            "agent_inference": "The route is ready for a nonterminal relation-depth completion planner if the input gate passes.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--branch-closure-summary", type=Path)
    parser.add_argument("--next-branch-request-rows", type=Path)
    parser.add_argument("--next-branch-candidate-rows", type=Path)
    parser.add_argument("--fresh-object-relation-evidence-rows", type=Path)
    parser.add_argument("--fresh-object-relation-context-rows", type=Path)
    parser.add_argument("--fresh-object-relation-plan-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.branch_closure_summary = source_path(args, contract, "branch_closure_summary", "branch_closure_summary")
    args.next_branch_request_rows = source_path(args, contract, "next_branch_request_rows", "next_branch_request_rows")
    args.next_branch_candidate_rows = source_path(args, contract, "next_branch_candidate_rows", "next_branch_candidate_rows")
    args.fresh_object_relation_evidence_rows = source_path(
        args,
        contract,
        "fresh_object_relation_evidence_rows",
        "fresh_object_relation_evidence_rows",
    )
    args.fresh_object_relation_context_rows = source_path(
        args,
        contract,
        "fresh_object_relation_context_rows",
        "fresh_object_relation_context_rows",
    )
    args.fresh_object_relation_plan_rows = source_path(
        args,
        contract,
        "fresh_object_relation_plan_rows",
        "fresh_object_relation_plan_rows",
    )
    outputs = build_outputs(
        contract=contract,
        branch_request_rows=load_jsonl(args.next_branch_request_rows),
        branch_candidate_rows=load_jsonl(args.next_branch_candidate_rows),
        evidence_rows=load_jsonl(args.fresh_object_relation_evidence_rows),
        context_rows=load_jsonl(args.fresh_object_relation_context_rows),
        existing_plan_rows=load_jsonl(args.fresh_object_relation_plan_rows),
    )
    summary = summarize(
        contract=contract,
        branch_summary=load_json(args.branch_closure_summary),
        outputs=outputs,
        args=args,
    )
    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "partial_relation_depth_request_rows.jsonl", outputs["request_rows"])
    write_jsonl(args.out_root / "partial_relation_depth_target_candidate_rows.jsonl", outputs["target_candidate_rows"])
    write_jsonl(args.out_root / "partial_relation_depth_failed_evidence_rows.jsonl", outputs["failed_evidence_rows"])
    write_jsonl(args.out_root / "partial_relation_depth_context_anchor_rows.jsonl", outputs["context_anchor_rows"])
    write_json(args.out_root / "partial_relation_depth_input_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["partial_relation_depth_input_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
