import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    candidate_target_position,
    horizontal_distance,
    parse_float_list,
    plan_standoff_viewpoint,
    safe_float,
    vector,
)


SCHEMA_VERSION = "h001.expanded_retrieval_detector_observation_plan.v2"
POLICY_NAME = "ExpandedRetrievalDetectorObservation"
PLANNER_NAME = "expanded_retrieval_detector_standoff_projection_anchor_v1"
PROJECTION_ANCHOR_POLICY = "projection_anchor_height_sweep_v1"
FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "selected_for_goal",
    "wrong_goal_visit",
    "success",
    "evaluation_only_candidate_correct",
    "evaluation_only_goal_visit",
    "evaluation_only_wrong_goal_visit",
    "evaluation_only_wasted_path_from_candidate",
    "analysis_only_target_route",
    "analysis_only_target_taxonomy",
    "analysis_only_proxy_matches_target_route",
}


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


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def candidate_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return str(row.get("episode_key")), str(row.get("query"))


def candidate_set_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {candidate_key(row): row for row in rows}


def detector_allowed(proxy_row: Dict[str, Any]) -> bool:
    decision = proxy_row.get("proxy_decision") or {}
    return (
        decision.get("detector_evidence_allowed_by_proxy") is True
        and decision.get("terminal_commit_allowed_by_proxy") is not True
        and str(decision.get("proxy_route")) == "request_detector_guarded_observation_proxy"
    )


def rank_candidates(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (dict(candidate) for candidate in candidates),
        key=lambda candidate: (
            safe_int(candidate.get("selection_rank")),
            safe_int(candidate.get("semantic_rank")),
            -(safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score")) or -math.inf),
            str(candidate.get("candidate_id")),
        ),
    )


def select_candidates(row: Dict[str, Any], max_candidates: int) -> List[Dict[str, Any]]:
    candidates = rank_candidates(row.get("expanded_candidates") or [])
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        if candidate_id is None:
            continue
        candidate_id = str(candidate_id)
        if candidate_id in seen:
            continue
        position = candidate_target_position(candidate)
        if position is None:
            continue
        selected.append(candidate)
        seen.add(candidate_id)
        if len(selected) >= max_candidates:
            break
    return selected


def artifact_candidate(candidate: Dict[str, Any]) -> Dict[str, Any]:
    score = safe_float(candidate.get("score"))
    if score is None:
        score = safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score"))
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "category": candidate.get("category"),
        "score": score,
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "candidate_backend": candidate.get("candidate_backend"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "path_to_candidate": candidate.get("path_to_candidate"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "source": "expanded_retrieval_detector_observation_plan",
        "uses_gt_for_action": False,
    }


def candidate_artifact_rows(plan_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    scene_keys: Dict[Tuple[str, str], str] = {}
    for row in plan_rows:
        key = (str(row.get("scene_id")), str(row.get("query")))
        scene_keys[key] = str(row.get("scene_key") or "")
        for candidate in row.get("expanded_retrieval_candidate_snapshots") or []:
            candidate_id = str(candidate.get("candidate_id"))
            grouped[key][candidate_id] = artifact_candidate(candidate)

    output: List[Dict[str, Any]] = []
    for (scene_id, query), candidates_by_id in sorted(grouped.items()):
        candidates = list(candidates_by_id.values())
        candidates.sort(
            key=lambda candidate: (
                safe_int(candidate.get("semantic_rank")),
                -(safe_float(candidate.get("score")) or -math.inf),
                str(candidate.get("candidate_id")),
            )
        )
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "expanded_retrieval_detector_candidate_artifact",
                "scene_id": scene_id,
                "scene_key": scene_keys.get((scene_id, query)),
                "query": query,
                "candidates": candidates,
                "candidate_count": len(candidates),
                "uses_gt_for_action": False,
            }
        )
    return output


def alternative_id(candidate_id: str, candidate_ids: Sequence[str]) -> Optional[str]:
    for other_id in candidate_ids:
        if other_id != candidate_id:
            return other_id
    return None


def proxy_action_fields(proxy_row: Dict[str, Any]) -> Dict[str, Any]:
    decision = proxy_row.get("proxy_decision") or {}
    features = proxy_row.get("source_pool_features") or {}
    return {
        "source_pool_proxy_route": decision.get("proxy_route"),
        "source_pool_proxy_reason": decision.get("proxy_reason"),
        "source_pool_invalid_proxy": decision.get("source_pool_invalid_proxy"),
        "source_pool_saturated": decision.get("saturated_source_pool"),
        "source_pool_low_absolute_evidence": decision.get("low_absolute_evidence"),
        "source_pool_no_high_confidence_candidate": decision.get("no_high_confidence_candidate"),
        "source_pool_top_candidate_score": features.get("top_candidate_score"),
        "source_pool_top4_score_range": features.get("top4_score_range"),
        "source_pool_score_ge_0_91_count": features.get("score_ge_0_91_count"),
        "source_pool_positive_support_candidate_count": features.get("positive_support_candidate_count"),
        "source_pool_semantic_top2_score_gap": features.get("semantic_top2_score_gap"),
        "source_pool_top_score_uncertainty": features.get("top_score_uncertainty"),
    }


def count_consumed_forbidden_fields() -> int:
    consumed = set(proxy_action_fields({"proxy_decision": {}, "source_pool_features": {}}).keys())
    consumed.update(
        {
            "episode_key",
            "scene_id",
            "scene_key",
            "query",
            "rival_identity_request_id",
            "expanded_candidates.candidate_id",
            "expanded_candidates.selection_rank",
            "expanded_candidates.semantic_rank",
            "expanded_candidates.semantic_score",
            "expanded_candidates.support_score",
            "expanded_candidates.position",
            "expanded_candidates.visit_position",
            "expanded_candidates.positive_support",
            "expanded_candidates.candidate_reachable",
        }
    )
    return sum(1 for key in consumed if key in FORBIDDEN_ACTION_KEYS or key.startswith("analysis_only_"))


def make_plan_row(
    *,
    args: argparse.Namespace,
    proxy_row: Dict[str, Any],
    candidate_set_row: Dict[str, Any],
    request_index: int,
    target_index: int,
    candidate: Dict[str, Any],
    selected_candidates: Sequence[Dict[str, Any]],
    viewpoint: Dict[str, Any],
) -> Dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id"))
    selected_ids = [str(item.get("candidate_id")) for item in selected_candidates if item.get("candidate_id") is not None]
    target_position = candidate_target_position(candidate)
    position = [float(item) for item in viewpoint["position"]]
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "viewpoint_policy": PLANNER_NAME,
        "request_index": request_index,
        "target_index": target_index,
        "episode_key": proxy_row.get("episode_key"),
        "scene_id": candidate_set_row.get("scene_id") or proxy_row.get("scene_id"),
        "scene_key": candidate_set_row.get("scene_key") or proxy_row.get("scene_key"),
        "query": proxy_row.get("query"),
        "rival_identity_request_id": proxy_row.get("rival_identity_request_id"),
        "expanded_retrieval_request_id": proxy_row.get("rival_identity_request_id"),
        "viewpoint_id": f"expanded_detector:{proxy_row.get('rival_identity_request_id')}:{target_index + 1}",
        "candidate_id": candidate_id,
        "target_candidate_id": candidate_id,
        "candidate_ids": [candidate_id],
        "expanded_retrieval_candidate_set_ids": selected_ids,
        "expanded_retrieval_candidate_snapshots": [dict(item) for item in selected_candidates],
        "expanded_candidate_rank": candidate.get("selection_rank"),
        "target_semantic_rank": candidate.get("semantic_rank"),
        "target_semantic_score": candidate.get("semantic_score"),
        "target_support_score": candidate.get("support_score"),
        "target_positive_support": candidate.get("positive_support"),
        "target_candidate_reachable": candidate.get("candidate_reachable"),
        "target_position": target_position,
        "target_visit_position": candidate.get("visit_position"),
        "viewpoint_position": position,
        "viewpoint_rotation": [float(item) for item in viewpoint["rotation"]],
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "target_distance_from_viewpoint_m": None if target_position is None else horizontal_distance(position, target_position),
        "standoff_target_position": viewpoint.get("target_position"),
        "standoff_desired_position": viewpoint.get("desired_position"),
        "standoff_target_horizontal_distance": viewpoint.get("target_horizontal_distance"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "revision_contract_name": "expanded_retrieval_detector_viewpoint_revision_v1",
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "revision_projection_anchor_source": "fixed_category_agnostic_offsets",
        "revision_projection_anchor_uses_gt_for_action": False,
        "detector_evidence_allowed_by_proxy": True,
        "terminal_commit_allowed": False,
        "commit_after_reobserve": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }
    row.update(proxy_action_fields(proxy_row))
    return row


def plan_request(
    *,
    args: argparse.Namespace,
    proxy_row: Dict[str, Any],
    candidate_set_row: Dict[str, Any],
    request_index: int,
    snapper: NavmeshSnapper,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selected = select_candidates(candidate_set_row, int(args.max_candidates_per_request))
    selected_ids = [str(candidate.get("candidate_id")) for candidate in selected]
    candidates_by_id = {str(candidate.get("candidate_id")): candidate for candidate in selected}
    source_row = {
        "scene_id": candidate_set_row.get("scene_id") or proxy_row.get("scene_id"),
        "viewpoint_position": None,
    }
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for target_index, candidate in enumerate(selected):
        candidate_id = str(candidate.get("candidate_id"))
        alt_id = alternative_id(candidate_id, selected_ids)
        viewpoint = plan_standoff_viewpoint(source_row, candidate, candidates_by_id, alt_id, snapper, args)
        skip_reason: Optional[str] = None
        if viewpoint is None:
            skip_reason = "standoff_unavailable"
        elif "fallback" in str(viewpoint.get("viewpoint_source") or ""):
            skip_reason = "standoff_fallback_forbidden"
        elif bool(args.require_navmesh_standoff) and (
            viewpoint.get("viewpoint_source") != "standoff_navmesh" or viewpoint.get("navmesh_navigable") is not True
        ):
            skip_reason = "standoff_navmesh_required"
        elif viewpoint.get("projection_sane") is not True:
            skip_reason = "standoff_no_valid_yaw"
        else:
            target_distance = safe_float(viewpoint.get("target_horizontal_distance"))
            if target_distance is None:
                skip_reason = "standoff_missing_target_distance"
            elif target_distance < float(args.min_standoff_distance_m):
                skip_reason = "standoff_all_too_close"
            elif target_distance > float(args.max_standoff_distance_m):
                skip_reason = "standoff_all_too_far"

        if skip_reason:
            skipped.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "episode_key": proxy_row.get("episode_key"),
                    "scene_id": candidate_set_row.get("scene_id") or proxy_row.get("scene_id"),
                    "scene_key": candidate_set_row.get("scene_key") or proxy_row.get("scene_key"),
                    "query": proxy_row.get("query"),
                    "rival_identity_request_id": proxy_row.get("rival_identity_request_id"),
                    "candidate_id": candidate_id,
                    "target_index": target_index,
                    "skip_reason": skip_reason,
                    "uses_gt_for_action": False,
                }
            )
            continue

        rows.append(
            make_plan_row(
                args=args,
                proxy_row=proxy_row,
                candidate_set_row=candidate_set_row,
                request_index=request_index,
                target_index=target_index,
                candidate=candidate,
                selected_candidates=selected,
                viewpoint=viewpoint,
            )
        )
    return rows, skipped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    candidate_rows = load_jsonl(Path(args.candidate_set))
    proxy_rows = load_jsonl(Path(args.proxy_rows))
    candidate_by_key = candidate_set_index(candidate_rows)
    detector_proxy_rows = [row for row in proxy_rows if detector_allowed(row)]
    detector_proxy_rows.sort(key=lambda row: str(row.get("rival_identity_request_id")))

    out_root = Path(args.out_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    missing_candidate_set_rows: List[Dict[str, Any]] = []
    snapper = NavmeshSnapper(args.data_root)
    try:
        for request_index, proxy_row in enumerate(detector_proxy_rows):
            key = candidate_key(proxy_row)
            candidate_set_row = candidate_by_key.get(key)
            if candidate_set_row is None:
                missing = {
                    "schema_version": SCHEMA_VERSION,
                    "episode_key": proxy_row.get("episode_key"),
                    "scene_id": proxy_row.get("scene_id"),
                    "scene_key": proxy_row.get("scene_key"),
                    "query": proxy_row.get("query"),
                    "rival_identity_request_id": proxy_row.get("rival_identity_request_id"),
                    "skip_reason": "missing_candidate_set_row",
                    "uses_gt_for_action": False,
                }
                missing_candidate_set_rows.append(missing)
                skipped_rows.append(missing)
                continue
            rows, skipped = plan_request(
                args=args,
                proxy_row=proxy_row,
                candidate_set_row=candidate_set_row,
                request_index=request_index,
                snapper=snapper,
            )
            plan_rows.extend(rows)
            skipped_rows.extend(skipped)
    finally:
        snapper.close()

    artifact_rows = candidate_artifact_rows(plan_rows)
    write_jsonl(out_root / "expanded_retrieval_detector_plan.jsonl", plan_rows)
    write_jsonl(out_root / "expanded_retrieval_detector_skipped.jsonl", skipped_rows)
    write_jsonl(out_root / "expanded_retrieval_detector_candidate_artifact.jsonl", artifact_rows)

    request_keys = {str(row.get("episode_key")) for row in detector_proxy_rows}
    planned_request_keys = {str(row.get("episode_key")) for row in plan_rows}
    target_distances = [
        float(distance)
        for distance in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if distance is not None
    ]
    plan_rows_by_request = Counter(str(row.get("episode_key")) for row in plan_rows)
    viewpoint_sources = Counter(str(row.get("viewpoint_source")) for row in plan_rows)
    skipped_reasons = Counter(str(row.get("skip_reason")) for row in skipped_rows)
    zero_standoff = sum(1 for distance in target_distances if distance < 1e-4)
    near_standoff = sum(1 for distance in target_distances if distance < float(args.min_standoff_distance_m))
    rotation_fallback = sum(1 for row in plan_rows if "rotation_fallback" in str(row.get("viewpoint_source") or ""))
    fallback_rows = sum(1 for row in plan_rows if "fallback" in str(row.get("viewpoint_source") or ""))
    consumed_forbidden = count_consumed_forbidden_fields()
    gate = {
        "detector_proxy_request_rows_min_pass": len(detector_proxy_rows) >= int(args.min_detector_proxy_request_rows),
        "missing_candidate_set_rows_pass": len(missing_candidate_set_rows) == 0,
        "planned_request_rows_min_pass": len(planned_request_keys) >= int(args.min_planned_request_rows),
        "plan_rows_min_pass": len(plan_rows) >= int(args.min_plan_rows),
        "min_plan_rows_per_request_pass": bool(plan_rows_by_request)
        and min(plan_rows_by_request.values()) >= int(args.min_plan_rows_per_request),
        "zero_standoff_rows_pass": zero_standoff == 0,
        "near_standoff_rows_pass": near_standoff == 0,
        "rotation_fallback_rows_pass": rotation_fallback == 0,
        "fallback_rows_pass": fallback_rows == 0,
        "consumed_forbidden_action_fields_pass": consumed_forbidden == 0,
        "no_terminal_commit_pass": not any(row.get("terminal_commit_allowed") is True for row in plan_rows),
        "no_gt_action_pass": not any(row.get("uses_gt_for_action") is True for row in plan_rows),
    }
    gate["expanded_retrieval_detector_plan_gate_passed"] = all(gate.values())
    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_set": str(args.candidate_set),
        "proxy_rows": str(args.proxy_rows),
        "out_root": str(out_root),
        "policy": POLICY_NAME,
        "planner_name": PLANNER_NAME,
        "proxy_rows_total": len(proxy_rows),
        "detector_proxy_request_rows": len(detector_proxy_rows),
        "detector_proxy_request_keys": len(request_keys),
        "planned_request_rows": len(planned_request_keys),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "missing_candidate_set_rows": len(missing_candidate_set_rows),
        "plan_rows_per_request_min": min(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "plan_rows_per_request_max": max(plan_rows_by_request.values()) if plan_rows_by_request else 0,
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "zero_standoff_rows": zero_standoff,
        "near_standoff_rows": near_standoff,
        "rotation_fallback_rows": rotation_fallback,
        "fallback_rows": fallback_rows,
        "viewpoint_source_counts": dict(sorted(viewpoint_sources.items())),
        "skipped_reason_counts": dict(sorted(skipped_reasons.items())),
        "revision_contract_name": "expanded_retrieval_detector_viewpoint_revision_v1",
        "revision_projection_anchor_policy": PROJECTION_ANCHOR_POLICY,
        "revision_projection_anchor_height_offsets_m": [
            float(value) for value in args.projection_anchor_height_offsets_m
        ],
        "revision_projection_anchor_uses_gt_for_action": False,
        "candidate_artifact_rows": len(artifact_rows),
        "consumed_forbidden_action_field_count": consumed_forbidden,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "interpretation": {
            "facts": "Planner consumes proxy detector-eligible rows and non-GT expanded candidate geometry only.",
            "inference": (
                "This is a detector substrate gate, not terminal ObjectNav utility. It permits frame export and "
                "detector/SAM2 scoring only for source-pool-valid rows."
            ),
        },
        "output_files": {
            "plan": "expanded_retrieval_detector_plan.jsonl",
            "skipped": "expanded_retrieval_detector_skipped.jsonl",
            "candidate_artifact": "expanded_retrieval_detector_candidate_artifact.jsonl",
            "summary": "expanded_retrieval_detector_plan_summary.json",
        },
    }
    write_json(out_root / "expanded_retrieval_detector_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan detector observations for source-pool-valid expanded retrieval rows.")
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--proxy-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--run-id", default="h001_expanded_retrieval_detector_observation_v1")
    parser.add_argument("--max-candidates-per-request", type=int, default=10)
    parser.add_argument("--min-detector-proxy-request-rows", type=int, default=6)
    parser.add_argument("--min-planned-request-rows", type=int, default=6)
    parser.add_argument("--min-plan-rows", type=int, default=36)
    parser.add_argument("--min-plan-rows-per-request", type=int, default=5)
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25, 2.75])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--require-navmesh-standoff", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--projection-anchor-height-offsets-m",
        type=parse_float_list,
        default=[0.0, 0.4, 0.8, 1.2, 1.6],
    )
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["expanded_retrieval_detector_plan_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
