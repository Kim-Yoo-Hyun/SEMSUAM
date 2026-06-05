import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.missing_own_view_recheck_plan.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_missing_own_view_recheck_observation_v1.json"
)
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_missing_own_view_recheck_observation_v1"
OUT_ROOT_DEFAULT = INPUT_ROOT_DEFAULT
POLICY_NAME = "MissingOwnViewRecheckObservation"
PLANNER_NAME = "missing_own_view_recheck_candidate_centered_v1"
VIEWPOINT_POLICY = "candidate_centered_multiview_standoff_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        text = str(value).split(":")[-1]
        try:
            return int(text)
        except (TypeError, ValueError):
            return default


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) != 3:
        return None
    values = [safe_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return [float(item) for item in values]


def horizontal_distance(a: Any, b: Any) -> Optional[float]:
    avec = vector3(a)
    bvec = vector3(b)
    if avec is None or bvec is None:
        return None
    return math.sqrt((avec[0] - bvec[0]) ** 2 + (avec[2] - bvec[2]) ** 2)


def request_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    if ":" in text:
        prefix, suffix = text.rsplit(":", 1)
        return prefix, safe_int(suffix), text
    return text, -1, text


def candidate_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    return text.rsplit(":", 1)[0], safe_int(text.rsplit(":", 1)[-1]), text


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("target_candidate_id") or "")


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def unique_preserve_order(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def rows_by_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        key = row_key(row)
        if all(key):
            grouped[key].append(dict(row))
    return grouped


def scan_forbidden_keys(value: Any, prefix: str = "") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if lowered != "uses_gt_for_action" and any(term in lowered for term in ("correct", "wrong_goal", "evaluation_only", "gt_")):
                findings.append(child_path)
            findings.extend(scan_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_forbidden_keys(child, f"{prefix}[{index}]"))
    return findings


def count_forbidden(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def make_skip_row(target: Dict[str, Any], reason: str, request_index: int) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_missing_own_view_recheck_observation_skipped",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "request_index": request_index,
        "episode_key": target.get("episode_key"),
        "scene_id": target.get("scene_id"),
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "expanded_retrieval_request_id": request_id(target),
        "rival_identity_request_id": target.get("rival_identity_request_id") or request_id(target),
        "candidate_id": candidate_id(target),
        "target_candidate_id": candidate_id(target),
        "skip_reason": reason,
        "terminal_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_plan_row(
    *,
    args: argparse.Namespace,
    target: Dict[str, Any],
    source_plan: Dict[str, Any],
    request_index: int,
    observation_index: int,
    recheck_index: int,
) -> Optional[Dict[str, Any]]:
    viewpoint_position = vector3(source_plan.get("source_viewpoint_position"))
    viewpoint_rotation = source_plan.get("source_viewpoint_rotation")
    target_position = vector3(target.get("target_position")) or vector3(source_plan.get("target_position"))
    target_visit_position = vector3(target.get("target_visit_position")) or vector3(source_plan.get("target_visit_position"))
    if viewpoint_position is None or not isinstance(viewpoint_rotation, list) or len(viewpoint_rotation) != 4:
        return None
    if target_position is None:
        return None
    target_distance = horizontal_distance(viewpoint_position, target_position)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "validation_stage": "action_missing_own_view_recheck_observation_target",
        "contract_name": "missing_own_view_recheck_observation_v1",
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_index": request_index,
        "observation_index": observation_index,
        "recheck_index": recheck_index,
        "episode_key": target.get("episode_key"),
        "scene_id": target.get("scene_id"),
        "scene_key": target.get("scene_key"),
        "query": target.get("query"),
        "expanded_retrieval_request_id": request_id(target),
        "rival_identity_request_id": target.get("rival_identity_request_id") or request_id(target),
        "candidate_id": candidate_id(target),
        "target_candidate_id": candidate_id(target),
        "candidate_ids": [candidate_id(target)],
        "view_role": "candidate_own_view_recheck",
        "target_candidate_role": target.get("target_candidate_role"),
        "target_generated_rank": target.get("target_generated_rank"),
        "target_semantic_rank": target.get("target_semantic_rank"),
        "target_semantic_score": target.get("target_semantic_score"),
        "target_support_score": target.get("target_support_score"),
        "target_score": target.get("target_score"),
        "target_position": target_position,
        "target_visit_position": target_visit_position,
        "target_distance_from_viewpoint_m": target_distance,
        "base_candidate_evidence_class": target.get("base_candidate_evidence_class"),
        "base_candidate_specific_support": target.get("base_candidate_specific_support"),
        "base_strong_own_view_evidence": target.get("base_strong_own_view_evidence"),
        "base_has_candidate_association": target.get("base_has_candidate_association"),
        "base_visible_count": target.get("base_visible_count"),
        "base_mask_hit_count": target.get("base_mask_hit_count"),
        "base_consistent_depth_count": target.get("base_consistent_depth_count"),
        "relation_depth_evidence_status": target.get("relation_depth_evidence_status"),
        "relation_associated_heading_count": target.get("relation_associated_heading_count"),
        "relation_depth_consistent_count": target.get("relation_depth_consistent_count"),
        "missing_own_view_recheck_action": "collect_candidate_centered_own_view_recheck_evidence",
        "missing_own_view_recheck_reason": "relation_depth_resolved_but_independent_own_view_support_missing",
        "companion_guard_branch": target.get("companion_guard_branch"),
        "companion_guard_role": target.get("companion_guard_role"),
        "source_plan_index": source_plan.get("source_plan_index"),
        "source_viewpoint_id": source_plan.get("source_viewpoint_id"),
        "source_contract_name": source_plan.get("source_contract_name"),
        "source_plan_reference_only": True,
        "source_relation_depth_evidence_not_reused": True,
        "source_standoff_direction_source": source_plan.get("source_standoff_direction_source"),
        "source_standoff_distance_requested": source_plan.get("source_standoff_distance_requested"),
        "source_standoff_relation_anchor_candidate_id": source_plan.get("source_standoff_relation_anchor_candidate_id"),
        "source_standoff_target_horizontal_distance": source_plan.get("source_standoff_target_horizontal_distance"),
        "viewpoint_id": f"missing_own_view:{request_id(target)}:{candidate_id(target).split(':')[-1]}:{recheck_index:02d}",
        "viewpoint_position": viewpoint_position,
        "viewpoint_rotation": [float(value) for value in viewpoint_rotation],
        "viewpoint_source": "candidate_centered_navmesh_standoff_from_source_metadata",
        "standoff_direction_source": source_plan.get("source_standoff_direction_source"),
        "standoff_distance_requested": source_plan.get("source_standoff_distance_requested"),
        "standoff_relation_anchor_candidate_id": source_plan.get("source_standoff_relation_anchor_candidate_id"),
        "standoff_target_horizontal_distance": target_distance,
        "standoff_navmesh_navigable": bool(source_plan.get("source_standoff_navmesh_navigable")),
        "standoff_navmesh_snapped": bool(source_plan.get("source_standoff_navmesh_snapped")),
        "standoff_snap_distance": source_plan.get("source_standoff_snap_distance"),
        "standoff_projection_sane": source_plan.get("source_standoff_projection_sane"),
        "standoff_viewpoint_yaw_rad": source_plan.get("source_standoff_viewpoint_yaw_rad"),
        "standoff_score": source_plan.get("source_standoff_score"),
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": list(args.projection_anchor_height_offsets_m),
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_label_free": True,
        "terminal_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "commit_after_missing_own_view_recheck": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def candidate_artifact_payload(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": candidate_id(candidate),
        "category": candidate.get("query"),
        "score": candidate.get("target_score") or candidate.get("target_support_score") or candidate.get("target_semantic_score") or 0.0,
        "semantic_rank": candidate.get("target_semantic_rank"),
        "semantic_score": candidate.get("target_semantic_score"),
        "support_score": candidate.get("target_support_score"),
        "candidate_backend": "missing_own_view_recheck_observation",
        "candidate_role": "missing_own_view_recheck_target",
        "generated_rank": candidate.get("target_generated_rank"),
        "position": candidate.get("target_position"),
        "visit_position": candidate.get("target_visit_position"),
        "source": "missing_own_view_recheck_plan",
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(target_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    request_ids: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    for row in target_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        request_ids[key].add(request_id(row))
        grouped[key][candidate_id(row)] = candidate_artifact_payload(row)

    output: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda row: (
                -(safe_float(row.get("score")) or 0.0),
                safe_int(row.get("semantic_rank")),
                candidate_sort_key(row.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "missing_own_view_recheck_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "expanded_retrieval_request_ids": sorted(request_ids[(scene_id, query)], key=request_sort_key),
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def materialize_plan(
    *,
    args: argparse.Namespace,
    target_rows: Sequence[Dict[str, Any]],
    source_plan_rows: Sequence[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source_by_target = rows_by_key(source_plan_rows)
    request_index_by_id: Dict[str, int] = {}
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    for target in sorted(
        target_rows,
        key=lambda row: (
            request_sort_key(request_id(row)),
            safe_int(row.get("target_generated_rank")),
            candidate_sort_key(candidate_id(row)),
        ),
    ):
        rid = request_id(target)
        if rid not in request_index_by_id:
            request_index_by_id[rid] = len(request_index_by_id)
        request_index = request_index_by_id[rid]
        source_rows = sorted(
            source_by_target.get(row_key(target), []),
            key=lambda row: (safe_int(row.get("source_plan_index")), str(row.get("source_viewpoint_id") or "")),
        )
        if not source_rows:
            skipped_rows.append(make_skip_row(target, "source_plan_rows_unavailable", request_index))
            continue
        for recheck_index, source in enumerate(source_rows):
            plan_row = make_plan_row(
                args=args,
                target=target,
                source_plan=source,
                request_index=request_index,
                observation_index=len(plan_rows),
                recheck_index=recheck_index,
            )
            if plan_row is None:
                skipped_rows.append(make_skip_row(target, "candidate_centered_viewpoint_metadata_unavailable", request_index))
                continue
            plan_rows.append(plan_row)
    return plan_rows, skipped_rows


def summarize(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    input_summary: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    target_rows: Sequence[Dict[str, Any]],
    source_plan_rows: Sequence[Dict[str, Any]],
    base_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    gates = contract.get("evaluation_gates") or {}
    all_action_rows = [*plan_rows, *skipped_rows, *artifact_rows]
    forbidden = count_forbidden(all_action_rows)
    terminal_rows = [
        row
        for row in all_action_rows
        if row.get("terminal_commit") is True
        or row.get("terminal_commit_allowed") is True
        or row.get("commit_after_reobserve") is True
        or row.get("commit_after_missing_own_view_recheck") is True
    ]
    rejection_rows = [row for row in all_action_rows if row.get("candidate_rejection_allowed") is True]
    plan_by_target = Counter(row_key(row) for row in plan_rows)
    request_ids = sorted({request_id(row) for row in request_rows}, key=request_sort_key)
    target_distances = [
        float(value)
        for value in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if value is not None
    ]
    skipped_request_rows = len({request_id(row) for row in skipped_rows})
    gate = {
        "input_materializer_gate_passed": bool((input_summary.get("gate") or {}).get("missing_own_view_input_gate_passed")),
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows")),
        "expected_target_candidate_rows_passed": len(target_rows) == safe_int(gates.get("expected_target_candidate_rows")),
        "expected_base_support_rows_passed": len(base_rows) == safe_int(gates.get("expected_base_support_rows")),
        "expected_source_plan_rows_passed": len(source_plan_rows) == safe_int(gates.get("expected_existing_plan_rows")),
        "minimum_plan_rows_passed": len(plan_rows) >= safe_int(gates.get("minimum_plan_rows")),
        "minimum_plan_rows_per_target_candidate_passed": bool(plan_by_target)
        and min(plan_by_target.values()) >= safe_int(gates.get("minimum_plan_rows_per_target_candidate")),
        "skipped_request_rows_maximum_passed": skipped_request_rows <= safe_int(gates.get("skipped_request_rows_maximum")),
        "skipped_rows_empty_passed": len(skipped_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "candidate_rejection_rows_passed": len(rejection_rows) <= safe_int(gates.get("candidate_rejection_rows_maximum")),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in all_action_rows),
        "paper_claim_allowed": False,
    }
    gate["missing_own_view_observation_plan_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "input_root": str(args.input_root),
        "out_root": str(args.out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": VIEWPOINT_POLICY,
        "request_rows": len(request_rows),
        "target_candidate_rows": len(target_rows),
        "base_support_rows": len(base_rows),
        "source_plan_rows": len(source_plan_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "skipped_request_rows": skipped_request_rows,
        "request_ids": request_ids,
        "plan_rows_by_request": dict(sorted(Counter(request_id(row) for row in plan_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "plan_rows_by_target": {
            f"{key[0]}::{key[1]}": value
            for key, value in sorted(plan_by_target.items(), key=lambda item: (request_sort_key(item[0][0]), candidate_sort_key(item[0][1])))
        },
        "view_role_counts": compact_counter(row.get("view_role") for row in plan_rows),
        "viewpoint_source_counts": compact_counter(row.get("viewpoint_source") for row in plan_rows),
        "source_direction_counts": compact_counter(row.get("source_standoff_direction_source") for row in plan_rows),
        "standoff_distance_counts": compact_counter(row.get("standoff_distance_requested") for row in plan_rows),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "candidate_artifact_rows": len(artifact_rows),
        "candidate_artifact_unique_candidate_count": sum(safe_int(row.get("candidate_count")) for row in artifact_rows),
        "terminal_commit_rows": len(terminal_rows),
        "candidate_rejection_rows": len(rejection_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "plan": "missing_own_view_observation_plan.jsonl",
            "skipped": "missing_own_view_observation_skipped.jsonl",
            "candidate_artifact": "missing_own_view_candidate_artifact.jsonl",
            "summary": "missing_own_view_observation_plan_summary.json",
        },
        "interpretation": {
            "fact": "The planner writes nonterminal candidate-centered own-view recheck observation rows from source standoff metadata and target candidate rows.",
            "agent_inference": "Passing this smoke means the branch can proceed to frame/projection; it does not reuse prior detector evidence and does not unlock terminal utility.",
        },
    }


def parse_float_list(text: str) -> List[float]:
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--input-root", type=Path, default=Path(INPUT_ROOT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--run-id", default="missing_own_view_recheck_observation_v1")
    parser.add_argument(
        "--projection-anchor-height-offsets-m",
        type=parse_float_list,
        default=parse_float_list("0.0,0.4,0.8,1.2,1.6,2.0,2.4"),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    input_root = Path(args.input_root)
    request_rows = load_jsonl(input_root / "missing_own_view_request_rows.jsonl")
    target_rows = load_jsonl(input_root / "missing_own_view_target_candidate_rows.jsonl")
    source_plan_rows = load_jsonl(input_root / "missing_own_view_source_plan_rows.jsonl")
    base_rows = load_jsonl(input_root / "missing_own_view_base_support_rows.jsonl")
    input_summary = load_json(input_root / "missing_own_view_input_summary.json")
    plan_rows, skipped_rows = materialize_plan(
        args=args,
        target_rows=target_rows,
        source_plan_rows=source_plan_rows,
    )
    artifact_rows = candidate_artifact_rows(target_rows)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "missing_own_view_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "missing_own_view_observation_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "missing_own_view_candidate_artifact.jsonl", artifact_rows)
    summary = summarize(
        args=args,
        contract=contract,
        input_summary=input_summary,
        request_rows=request_rows,
        target_rows=target_rows,
        source_plan_rows=source_plan_rows,
        base_rows=base_rows,
        plan_rows=plan_rows,
        skipped_rows=skipped_rows,
        artifact_rows=artifact_rows,
    )
    write_json(out_root / "missing_own_view_observation_plan_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["missing_own_view_observation_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
