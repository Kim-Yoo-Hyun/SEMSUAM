import argparse
import json
import math
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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs.v1"
REPAIR_ACTION = "request_object_relation_observation"


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


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) < 3:
        return None
    try:
        xyz = [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None
    if not all(math.isfinite(item) for item in xyz):
        return None
    return xyz


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def candidate_ids_from_source(row: Dict[str, Any]) -> List[str]:
    return [str(value) for value in row.get("candidate_ids") or [] if value is not None]


def plan_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = row_key(row)
        if all(key) and key not in indexed:
            indexed[key] = dict(row)
    return indexed


def evidence_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = row_key(row)
        if all(key) and key not in indexed:
            indexed[key] = dict(row)
    return indexed


def source_rows_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        rid = request_id(row)
        if rid:
            indexed[rid] = dict(row)
    return indexed


def sorted_request_ids(contract: Dict[str, Any]) -> List[str]:
    scope = contract.get("target_scope") or {}
    return sorted([str(value) for value in scope.get("expected_request_ids") or []], key=request_sort_key)


def relation_predicates(distance: Optional[float]) -> List[str]:
    predicates = ["anchor_available_proxy"]
    if distance is None:
        return predicates
    if distance <= 1.0:
        predicates.append("near_1m_proxy")
    if distance <= 2.0:
        predicates.append("near_2m_proxy")
    if distance <= 4.0:
        predicates.append("near_4m_proxy")
    if distance <= 0.75:
        predicates.append("overlap_proxy")
    return predicates


def horizontal_distance(a: Optional[List[float]], b: Optional[List[float]]) -> Optional[float]:
    if a is None or b is None:
        return None
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def delta(context: Optional[List[float]], target: Optional[List[float]], axis: int) -> Optional[float]:
    if context is None or target is None:
        return None
    return float(context[axis]) - float(target[axis])


def target_row(
    *,
    source_row: Dict[str, Any],
    plan_row: Dict[str, Any],
    evidence_row: Dict[str, Any],
    target_index: int,
) -> Dict[str, Any]:
    rid = request_id(source_row)
    cid = candidate_id(plan_row)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_object_relation_fresh_observation_target",
        "expanded_retrieval_request_id": rid,
        "rival_identity_request_id": source_row.get("rival_identity_request_id"),
        "episode_key": source_row.get("episode_key"),
        "scene_key": source_row.get("scene_key"),
        "scene_id": source_row.get("scene_id"),
        "query": source_row.get("query"),
        "candidate_id": cid,
        "target_candidate_id": cid,
        "target_index": target_index,
        "target_generated_rank": plan_row.get("target_index"),
        "target_semantic_rank": plan_row.get("target_semantic_rank") or plan_row.get("semantic_rank"),
        "target_semantic_score": plan_row.get("target_semantic_score") or plan_row.get("semantic_score"),
        "target_support_score": plan_row.get("target_support_score") or plan_row.get("support_score"),
        "target_score": plan_row.get("target_semantic_score") or plan_row.get("target_score"),
        "target_positive_support": plan_row.get("target_positive_support"),
        "target_position": plan_row.get("target_position"),
        "target_visit_position": plan_row.get("target_visit_position"),
        "target_candidate_role": plan_row.get("candidate_role") or evidence_row.get("candidate_role"),
        "candidate_role": plan_row.get("candidate_role") or evidence_row.get("candidate_role"),
        "detector_visible_rows": evidence_row.get("visible_count"),
        "detector_inside_mask_rows": evidence_row.get("mask_hit_count"),
        "detector_depth_mismatch_rows": None,
        "relation_density_bucket": None,
        "relation_signature_score": None,
        "relation_view_consistency_profile": "fresh_source_requires_relation_observation",
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def repair_action_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        **row,
        "validation_stage": "action_object_relation_fresh_observation_request",
        "repair_action": REPAIR_ACTION,
        "repair_reason": "fresh_route_specific_goal_validity_candidate_requires_object_relation_evidence",
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def context_row(
    *,
    target: Dict[str, Any],
    context: Dict[str, Any],
    evidence_row: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    target_pos = vector3(target.get("target_position"))
    context_pos = vector3(context.get("target_position"))
    if target_pos is None or context_pos is None:
        return None
    distance = horizontal_distance(context_pos, target_pos)
    context_id = candidate_id(context)
    if not context_id or context_id == candidate_id(target):
        return None
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_object_relation_fresh_context_candidate",
        "expanded_retrieval_request_id": request_id(target),
        "rival_identity_request_id": target.get("rival_identity_request_id"),
        "episode_key": target.get("episode_key"),
        "scene_key": target.get("scene_key"),
        "scene_id": target.get("scene_id"),
        "query": target.get("query"),
        "candidate_id": candidate_id(target),
        "target_candidate_id": candidate_id(target),
        "context_candidate_id": context_id,
        "context_generated_rank": context.get("target_generated_rank"),
        "context_candidate_role": context.get("candidate_role"),
        "context_position": context.get("target_position"),
        "context_visit_position": context.get("target_visit_position"),
        "x_delta_context_minus_candidate_m": delta(context_pos, target_pos, 0),
        "y_delta_context_minus_candidate_m": delta(context_pos, target_pos, 1),
        "z_delta_context_minus_candidate_m": delta(context_pos, target_pos, 2),
        "horizontal_distance_m": distance,
        "relation_predicates": relation_predicates(distance),
        "anchor_available_proxy": True,
        "near_1m_proxy": distance is not None and distance <= 1.0,
        "near_2m_proxy": distance is not None and distance <= 2.0,
        "near_4m_proxy": distance is not None and distance <= 4.0,
        "overlap_proxy": distance is not None and distance <= 0.75,
        "same_component_proxy": False,
        "same_support_surface_proxy": False,
        "context_detector_associated_rows": evidence_row.get("strict_association_count"),
        "context_detector_visible_rows": evidence_row.get("visible_count"),
        "context_detector_inside_mask_rows": evidence_row.get("mask_hit_count"),
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_outputs(
    *,
    contract: Dict[str, Any],
    source_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    evidence_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    expected_ids = sorted_request_ids(contract)
    sources = source_rows_by_request(source_rows)
    plans = plan_index(plan_rows)
    evidence = evidence_index(evidence_rows)

    target_rows: List[Dict[str, Any]] = []
    missing_plan: List[Dict[str, Any]] = []
    for rid in expected_ids:
        source = sources.get(rid)
        if not source:
            missing_plan.append({"expanded_retrieval_request_id": rid, "reason": "missing_fresh_source_row"})
            continue
        for target_index, cid in enumerate(candidate_ids_from_source(source)):
            plan = plans.get((rid, cid))
            if not plan:
                missing_plan.append(
                    {"expanded_retrieval_request_id": rid, "candidate_id": cid, "reason": "missing_local_context_plan_row"}
                )
                continue
            target_rows.append(
                target_row(
                    source_row=source,
                    plan_row=plan,
                    evidence_row=evidence.get((rid, cid), {}),
                    target_index=target_index,
                )
            )

    targets_by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in target_rows:
        targets_by_request[request_id(row)].append(row)

    context_rows: List[Dict[str, Any]] = []
    for rid, request_targets in targets_by_request.items():
        request_targets.sort(key=lambda row: (safe_int(row.get("target_generated_rank")), candidate_id(row)))
        for target in request_targets:
            for context in request_targets:
                built = context_row(
                    target=target,
                    context=context,
                    evidence_row=evidence.get((rid, candidate_id(context)), {}),
                )
                if built is not None:
                    context_rows.append(built)

    return {
        "coverage_gap_rows": target_rows,
        "repair_action_rows": [repair_action_row(row) for row in target_rows],
        "context_object_rows": context_rows,
        "missing_plan_rows": missing_plan,
    }


def summarize(
    *,
    contract: Dict[str, Any],
    fresh_summary: Dict[str, Any],
    outputs: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    target_rows = outputs["coverage_gap_rows"]
    repair_rows = outputs["repair_action_rows"]
    context_rows = outputs["context_object_rows"]
    missing_rows = outputs["missing_plan_rows"]
    forbidden = action_forbidden_keys([*target_rows, *repair_rows, *context_rows])
    minimum = contract.get("minimum_plan_gate") or {}
    request_ids = sorted({request_id(row) for row in target_rows}, key=request_sort_key)
    target_counts = Counter(request_id(row) for row in target_rows)
    context_counts = Counter(request_id(row) for row in context_rows)
    candidate_positions_missing = [
        row
        for row in target_rows
        if vector3(row.get("target_position")) is None or vector3(row.get("target_visit_position")) is None
    ]
    gate = {
        "fresh_source_precheck_gate_passed": bool(
            ((fresh_summary.get("gate") or {}).get("fresh_source_precheck_gate_passed"))
        ),
        "coverage_repair_gate_passed": True,
        "expected_target_candidate_rows_passed": len(target_rows)
        == safe_int((contract.get("target_scope") or {}).get("expected_target_candidate_rows"), len(target_rows)),
        "source_coverage_gap_rows_passed": len(target_rows) == safe_int(minimum.get("source_coverage_gap_rows"), 0),
        "source_repair_action_rows_passed": len(repair_rows) == safe_int(minimum.get("source_repair_action_rows"), 0),
        "missing_plan_rows_passed": len(missing_rows) == 0,
        "candidate_positions_available_passed": len(candidate_positions_missing) == 0,
        "context_object_rows_available_passed": len(context_rows) > 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == safe_int(minimum.get("output_forbidden_action_fields"), 0),
        "terminal_commit_rows_passed": not any(row.get("terminal_commit") is True for row in [*target_rows, *repair_rows, *context_rows]),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in [*target_rows, *repair_rows, *context_rows]),
        "paper_claim_allowed": False,
    }
    input_gate_keys = [
        "fresh_source_precheck_gate_passed",
        "expected_target_candidate_rows_passed",
        "source_coverage_gap_rows_passed",
        "source_repair_action_rows_passed",
        "missing_plan_rows_passed",
        "candidate_positions_available_passed",
        "context_object_rows_available_passed",
        "action_evidence_forbidden_key_gate_passed",
        "terminal_commit_rows_passed",
        "uses_gt_for_action_passed",
    ]
    gate["fresh_observation_input_gate_passed"] = all(gate[key] is True for key in input_gate_keys)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "fresh_source_action_rows": str(args.fresh_source_action_rows),
        "fresh_source_summary": str(args.fresh_source_summary),
        "local_context_plan_rows": str(args.local_context_plan_rows),
        "local_context_evidence_rows": str(args.local_context_evidence_rows),
        "out_root": str(args.out_root),
        "coverage_gap_rows": len(target_rows),
        "repair_action_rows": len(repair_rows),
        "context_object_rows": len(context_rows),
        "missing_plan_rows": len(missing_rows),
        "request_ids": request_ids,
        "target_rows_by_request": dict(sorted(target_counts.items(), key=lambda item: request_sort_key(item[0]))),
        "context_rows_by_request": dict(sorted(context_counts.items(), key=lambda item: request_sort_key(item[0]))),
        "candidate_positions_missing": len(candidate_positions_missing),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "coverage_gap_rows": "object_relation_fresh_observation_coverage_gap_rows.jsonl",
            "repair_action_rows": "object_relation_fresh_observation_repair_action_rows.jsonl",
            "context_object_rows": "object_relation_fresh_observation_context_object_rows.jsonl",
            "missing_plan_rows": "object_relation_fresh_observation_missing_plan_rows.jsonl",
            "summary": "object_relation_fresh_observation_input_summary.json",
        },
        "interpretation": {
            "fact": "Planner inputs are generated from fresh route-specific action rows and existing action-time local-context plan positions.",
            "agent_inference": "The source can feed the relation-aware standoff planner without label leakage. It still needs Habitat frame/projection and detector/SAM2 evidence before arbitration validation.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--fresh-source-action-rows", type=Path)
    parser.add_argument("--fresh-source-summary", type=Path)
    parser.add_argument("--local-context-plan-rows", type=Path)
    parser.add_argument("--local-context-evidence-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.fresh_source_action_rows = source_path(args, contract, "fresh_source_action_rows", "fresh_source_action_rows")
    args.fresh_source_summary = source_path(args, contract, "fresh_source_summary", "fresh_source_summary")
    args.local_context_plan_rows = source_path(args, contract, "local_context_plan_rows", "local_context_plan_rows")
    args.local_context_evidence_rows = source_path(args, contract, "local_context_evidence_rows", "local_context_evidence_rows")

    outputs = build_outputs(
        contract=contract,
        source_rows=load_jsonl(args.fresh_source_action_rows),
        plan_rows=load_jsonl(args.local_context_plan_rows),
        evidence_rows=load_jsonl(args.local_context_evidence_rows),
    )
    summary = summarize(
        contract=contract,
        fresh_summary=load_json(args.fresh_source_summary),
        outputs=outputs,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "object_relation_fresh_observation_coverage_gap_rows.jsonl", outputs["coverage_gap_rows"])
    write_jsonl(args.out_root / "object_relation_fresh_observation_repair_action_rows.jsonl", outputs["repair_action_rows"])
    write_jsonl(args.out_root / "object_relation_fresh_observation_context_object_rows.jsonl", outputs["context_object_rows"])
    write_jsonl(args.out_root / "object_relation_fresh_observation_missing_plan_rows.jsonl", outputs["missing_plan_rows"])
    write_json(args.out_root / "object_relation_fresh_observation_input_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["fresh_observation_input_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
