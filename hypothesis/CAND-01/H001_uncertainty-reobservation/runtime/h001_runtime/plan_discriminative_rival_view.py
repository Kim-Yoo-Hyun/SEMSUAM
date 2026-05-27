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
    normalize_xz,
    plan_standoff_viewpoint,
    quaternion_xyzw_from_yaw,
    safe_float,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.discriminative_rival_view_plan.v1"
POLICY_NAME = "DiscriminativeRivalView"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def request_sort_key(request_id: str) -> Tuple[int, str]:
    suffix = request_id.split(":")[-1]
    return (int(suffix), request_id) if suffix.isdigit() else (999999, request_id)


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["rival_identity_request_id"])].append(row)
    return grouped


def router_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        request_id = str(row["rival_identity_request_id"])
        if request_id in output:
            raise ValueError(f"duplicate router row: {request_id}")
        output[request_id] = row
    return output


def evidence_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": row.get("candidate_id"),
        "category": row.get("query"),
        "score": row.get("semantic_score"),
        "semantic_rank": row.get("semantic_rank"),
        "semantic_score": row.get("semantic_score"),
        "support_score": row.get("support_score"),
        "position": row.get("target_position"),
        "visit_position": row.get("target_visit_position"),
        "post_own_associated_heading_count": row.get("post_own_associated_heading_count"),
        "post_cross_associated_heading_count": row.get("post_cross_associated_heading_count"),
        "post_identity_margin": row.get("post_identity_margin"),
        "post_best_box_score": row.get("post_best_box_score"),
        "post_min_depth_error_m": row.get("post_min_depth_error_m"),
        "strong_identity_evidence": row.get("strong_identity_evidence"),
        "uses_gt_for_action": False,
    }


def candidate_dict(evidence_rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    candidates: Dict[str, Dict[str, Any]] = {}
    for row in evidence_rows:
        candidate_id = row.get("candidate_id")
        if candidate_id is not None:
            candidates[str(candidate_id)] = evidence_candidate(row)
    return candidates


def rank_candidate_for_focus(row: Dict[str, Any]) -> Tuple[int, int, float, float]:
    return (
        safe_int(row.get("strong_identity_evidence") is True, 0),
        safe_int(row.get("post_own_associated_heading_count")),
        safe_float(row.get("post_best_box_score")) or 0.0,
        -safe_int(row.get("semantic_rank"), 999999),
    )


def select_focus(router: Dict[str, Any], evidence_rows: Sequence[Dict[str, Any]]) -> Optional[str]:
    for candidate_id in router.get("strong_identity_candidate_ids") or []:
        if any(str(row.get("candidate_id")) == str(candidate_id) for row in evidence_rows):
            return str(candidate_id)
    if evidence_rows:
        return str(max(evidence_rows, key=rank_candidate_for_focus).get("candidate_id"))
    return None


def rank_candidate_for_rival(row: Dict[str, Any], focus_id: str) -> Tuple[int, int, int, float]:
    if str(row.get("candidate_id")) == focus_id:
        return (-1, -1, -999999, 0.0)
    return (
        safe_int(row.get("post_cross_associated_heading_count")),
        safe_int(row.get("post_own_associated_heading_count")),
        -safe_int(row.get("semantic_rank"), 999999),
        safe_float(row.get("post_best_box_score")) or 0.0,
    )


def select_rival(focus_id: str, evidence_rows: Sequence[Dict[str, Any]]) -> Optional[str]:
    rivals = [row for row in evidence_rows if str(row.get("candidate_id")) != focus_id]
    if not rivals:
        return None
    return str(max(rivals, key=lambda row: rank_candidate_for_rival(row, focus_id)).get("candidate_id"))


def scene_row(evidence_rows: Sequence[Dict[str, Any]], router: Dict[str, Any]) -> Dict[str, Any]:
    exemplar = evidence_rows[0] if evidence_rows else router
    return {
        "scene_id": exemplar.get("scene_id"),
        "scene_key": exemplar.get("scene_key"),
        "episode_key": exemplar.get("episode_key"),
        "query": exemplar.get("query"),
        "viewpoint_position": None,
        "uses_gt_for_action": False,
    }


def common_pair_viewpoint(
    *,
    row: Dict[str, Any],
    focus: Dict[str, Any],
    rival: Dict[str, Any],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    focus_position = candidate_target_position(focus)
    rival_position = candidate_target_position(rival)
    if focus_position is None or rival_position is None:
        return None
    dx = rival_position[0] - focus_position[0]
    dz = rival_position[2] - focus_position[2]
    unit = normalize_xz(dx, dz)
    if unit is None:
        return None
    ux, uz = unit
    perpendiculars = [(-uz, ux, "pair_perpendicular_left"), (uz, -ux, "pair_perpendicular_right")]
    midpoint = [
        (float(focus_position[0]) + float(rival_position[0])) / 2.0,
        float(vector(focus.get("visit_position"))[1]) if vector(focus.get("visit_position")) is not None else float(focus_position[1]),
        (float(focus_position[2]) + float(rival_position[2])) / 2.0,
    ]
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in args.common_pair_distances:
        for px, pz, source in perpendiculars:
            desired = [
                midpoint[0] + px * float(distance),
                midpoint[1],
                midpoint[2] + pz * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(str(row.get("scene_id")), desired)
            if snap_distance is None or not navigable:
                continue
            focus_distance = horizontal_distance(snapped, focus_position)
            rival_distance = horizontal_distance(snapped, rival_position)
            if focus_distance < float(args.min_standoff_distance_m) or rival_distance < float(args.min_standoff_distance_m):
                continue
            if focus_distance > float(args.max_standoff_distance_m) or rival_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, midpoint)
            if yaw is None:
                continue
            balance_penalty = abs(focus_distance - rival_distance)
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            navigable_bonus = -0.25 if navigable else 0.0
            score = balance_penalty + 0.20 * snap_penalty + navigable_bonus
            viewpoint = {
                "position": snapped,
                "rotation": quaternion_xyzw_from_yaw(yaw),
                "yaw": float(yaw),
                "desired_position": desired,
                "snap_distance": snap_distance,
                "navmesh_snapped": True,
                "navmesh_navigable": navigable,
                "direction_source": source,
                "standoff_distance_requested": float(distance),
                "viewpoint_source": "common_pair_navmesh",
                "projection_sane": True,
                "focus_distance_m": float(focus_distance),
                "rival_distance_m": float(rival_distance),
                "target_horizontal_distance": float(max(focus_distance, rival_distance)),
                "pair_midpoint": midpoint,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, viewpoint)
    return None if best is None else best[1]


def standoff_for(
    *,
    source: Dict[str, Any],
    target_id: str,
    alt_id: str,
    candidates: Dict[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    target = candidates.get(target_id)
    if target is None:
        return None
    viewpoint = plan_standoff_viewpoint(source, target, candidates, alt_id, snapper, args)
    if viewpoint is None:
        return None
    source_name = str(viewpoint.get("viewpoint_source") or "")
    if "fallback" in source_name:
        return None
    distance = safe_float(viewpoint.get("target_horizontal_distance"))
    if distance is None or distance < float(args.min_standoff_distance_m) or distance > float(args.max_standoff_distance_m):
        return None
    if viewpoint.get("projection_sane") is not True:
        return None
    return viewpoint


def make_row(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    router: Dict[str, Any],
    source: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
    focus_id: str,
    rival_id: str,
    target_id: str,
    pair_role: str,
    viewpoint: Dict[str, Any],
    row_index: int,
) -> Dict[str, Any]:
    candidates = candidate_dict(evidence_rows)
    target = candidates[target_id]
    focus = candidates[focus_id]
    rival = candidates[rival_id]
    target_position = candidate_target_position(target)
    focus_position = candidate_target_position(focus)
    rival_position = candidate_target_position(rival)
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "policy": POLICY_NAME,
        "planner_name": "discriminative_rival_view_planner_v1",
        "contract_name": contract.get("contract_name"),
        "source_router_output": str(args.router_rows),
        "source_evidence_output": str(args.evidence),
        "row_index": row_index,
        "rival_identity_request_id": router.get("rival_identity_request_id"),
        "episode_key": source.get("episode_key"),
        "scene_key": source.get("scene_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "revision_branch": router.get("revision_branch"),
        "revision_action": router.get("revision_action"),
        "source_reason": router.get("source_reason"),
        "viewpoint_id": f"discriminative_rival:{router.get('rival_identity_request_id')}:{pair_role}:{row_index}",
        "viewpoint_position": viewpoint.get("position"),
        "viewpoint_rotation": viewpoint.get("rotation"),
        "viewpoint_source": viewpoint.get("viewpoint_source"),
        "viewpoint_pair_role": pair_role,
        "candidate_id": target_id,
        "target_candidate_id": target_id,
        "candidate_ids": [focus_id, rival_id],
        "focus_candidate_id": focus_id,
        "rival_candidate_id": rival_id,
        "target_position": target_position,
        "focus_position": focus_position,
        "rival_position": rival_position,
        "target_visit_position": target.get("visit_position"),
        "target_semantic_rank": target.get("semantic_rank"),
        "target_semantic_score": target.get("semantic_score"),
        "target_support_score": target.get("support_score"),
        "target_post_own_associated_heading_count": target.get("post_own_associated_heading_count"),
        "target_post_cross_associated_heading_count": target.get("post_cross_associated_heading_count"),
        "focus_post_own_associated_heading_count": focus.get("post_own_associated_heading_count"),
        "focus_post_cross_associated_heading_count": focus.get("post_cross_associated_heading_count"),
        "rival_post_own_associated_heading_count": rival.get("post_own_associated_heading_count"),
        "rival_post_cross_associated_heading_count": rival.get("post_cross_associated_heading_count"),
        "focus_rival_span_m": None
        if focus_position is None or rival_position is None
        else horizontal_distance(focus_position, rival_position),
        "target_distance_from_viewpoint_m": viewpoint.get("target_horizontal_distance"),
        "focus_distance_from_viewpoint_m": viewpoint.get("focus_distance_m"),
        "rival_distance_from_viewpoint_m": viewpoint.get("rival_distance_m"),
        "standoff_snap_distance": viewpoint.get("snap_distance"),
        "standoff_navmesh_snapped": viewpoint.get("navmesh_snapped"),
        "standoff_navmesh_navigable": viewpoint.get("navmesh_navigable"),
        "standoff_direction_source": viewpoint.get("direction_source"),
        "standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
        "standoff_projection_sane": viewpoint.get("projection_sane"),
        "standoff_viewpoint_yaw_rad": viewpoint.get("yaw"),
        "standoff_score": viewpoint.get("score"),
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def plan_request(
    *,
    args: argparse.Namespace,
    contract: Dict[str, Any],
    router: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
    snapper: NavmeshSnapper,
    row_start: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    source = scene_row(evidence_rows, router)
    candidates = candidate_dict(evidence_rows)
    focus_id = select_focus(router, evidence_rows)
    if focus_id is None or focus_id not in candidates:
        return [], [{
            "schema_version": SCHEMA_VERSION,
            "rival_identity_request_id": router.get("rival_identity_request_id"),
            "skip_reason": "missing_focus_candidate",
            "uses_gt_for_action": False,
        }]
    rival_id = select_rival(focus_id, evidence_rows)
    if rival_id is None or rival_id not in candidates:
        return [], [{
            "schema_version": SCHEMA_VERSION,
            "rival_identity_request_id": router.get("rival_identity_request_id"),
            "focus_candidate_id": focus_id,
            "skip_reason": "missing_rival_candidate",
            "uses_gt_for_action": False,
        }]

    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    common = common_pair_viewpoint(
        row=source,
        focus=candidates[focus_id],
        rival=candidates[rival_id],
        snapper=snapper,
        args=args,
    )
    row_index = row_start
    if common is not None:
        rows.append(
            make_row(
                args=args,
                contract=contract,
                router=router,
                source=source,
                evidence_rows=evidence_rows,
                focus_id=focus_id,
                rival_id=rival_id,
                target_id=focus_id,
                pair_role="common",
                viewpoint=common,
                row_index=row_index,
            )
        )
        row_index += 1
    else:
        skipped.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": router.get("rival_identity_request_id"),
                "focus_candidate_id": focus_id,
                "rival_candidate_id": rival_id,
                "skip_reason": "common_pair_view_unavailable",
                "uses_gt_for_action": False,
            }
        )

    for role, target_id, alt_id in [("focus", focus_id, rival_id), ("rival", rival_id, focus_id)]:
        viewpoint = standoff_for(
            source=source,
            target_id=target_id,
            alt_id=alt_id,
            candidates=candidates,
            snapper=snapper,
            args=args,
        )
        if viewpoint is None:
            skipped.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "rival_identity_request_id": router.get("rival_identity_request_id"),
                    "focus_candidate_id": focus_id,
                    "rival_candidate_id": rival_id,
                    "target_candidate_id": target_id,
                    "skip_reason": f"{role}_matched_standoff_unavailable",
                    "uses_gt_for_action": False,
                }
            )
            continue
        rows.append(
            make_row(
                args=args,
                contract=contract,
                router=router,
                source=source,
                evidence_rows=evidence_rows,
                focus_id=focus_id,
                rival_id=rival_id,
                target_id=target_id,
                pair_role=role,
                viewpoint=viewpoint,
                row_index=row_index,
            )
        )
        row_index += 1
    return rows, skipped


def number_stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    router_rows_all = load_jsonl(Path(args.router_rows))
    evidence_by_request = group_by_request(load_jsonl(Path(args.evidence)))
    routers = [
        row for row in router_rows_all
        if row.get("revision_action") == "request_discriminative_rival_view"
    ]
    if int(args.max_requests) > 0:
        routers = routers[: int(args.max_requests)]

    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    try:
        for router in sorted(routers, key=lambda row: request_sort_key(str(row["rival_identity_request_id"]))):
            request_id = str(router["rival_identity_request_id"])
            evidence_rows = evidence_by_request.get(request_id, [])
            rows, skipped = plan_request(
                args=args,
                contract=contract,
                router=router,
                evidence_rows=evidence_rows,
                snapper=snapper,
                row_start=len(plan_rows),
            )
            plan_rows.extend(rows)
            skipped_rows.extend(skipped)
    finally:
        snapper.close()

    out_root = Path(args.out_root)
    write_jsonl(out_root / "discriminative_rival_view_plan.jsonl", plan_rows)
    write_jsonl(out_root / "discriminative_rival_view_skipped.jsonl", skipped_rows)

    planned_requests = {str(row.get("rival_identity_request_id")) for row in plan_rows}
    target_distances = [
        float(distance)
        for distance in (safe_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if distance is not None
    ]
    zero_standoff = sum(1 for value in target_distances if value < 1e-4)
    near_standoff = sum(1 for value in target_distances if value < float(args.min_standoff_distance_m))
    rotation_fallback = sum(1 for row in plan_rows if "fallback" in str(row.get("viewpoint_source") or ""))
    query_count = len({str(row.get("query")) for row in plan_rows if row.get("query")})
    common_pair_rows = [row for row in plan_rows if row.get("viewpoint_pair_role") == "common"]
    dual_rows = [row for row in plan_rows if row.get("viewpoint_pair_role") in {"focus", "rival"}]
    gate = {
        "target_request_rows_minimum_passed": len(planned_requests) >= int(args.min_planned_requests),
        "zero_standoff_rows_passed": zero_standoff == 0,
        "near_standoff_rows_passed": near_standoff == 0,
        "rotation_fallback_rows_passed": rotation_fallback == 0,
        "planned_pair_rows_minimum_passed": len(plan_rows) >= int(args.min_plan_rows),
        "planned_query_count_minimum_passed": query_count >= int(args.min_planned_queries),
        "uses_gt_for_action": False,
    }
    gate["plan_smoke_passed"] = all(
        bool(value) for key, value in gate.items() if key.endswith("_passed")
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(out_root),
        "contract": str(args.contract),
        "router_rows": str(args.router_rows),
        "evidence": str(args.evidence),
        "run_id": str(args.run_id),
        "source_router_rows": len(routers),
        "planned_request_rows": len(planned_requests),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "common_pair_view_rows": len(common_pair_rows),
        "matched_dual_standoff_rows": len(dual_rows),
        "viewpoint_source_counts": dict(sorted(Counter(str(row.get("viewpoint_source")) for row in plan_rows).items())),
        "viewpoint_pair_role_counts": dict(sorted(Counter(str(row.get("viewpoint_pair_role")) for row in plan_rows).items())),
        "skip_reason_counts": dict(sorted(Counter(str(row.get("skip_reason")) for row in skipped_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in plan_rows).items())),
        "target_distance_from_viewpoint_m": number_stats(target_distances),
        "zero_standoff_rows": zero_standoff,
        "near_standoff_rows": near_standoff,
        "rotation_fallback_rows": rotation_fallback,
        "gate": gate,
        "paper_claim_allowed": False,
        "paper_claim_status": "plan_smoke_only_no_detector_or_terminal_utility_claim",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "output_files": {
            "plan_rows": "discriminative_rival_view_plan.jsonl",
            "skipped_rows": "discriminative_rival_view_skipped.jsonl",
            "summary": "discriminative_rival_view_plan_summary.json",
        },
    }
    write_json(out_root / "discriminative_rival_view_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan contrastive focus-rival observations.")
    parser.add_argument("--router-rows", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--run-id", default="h001_discriminative_rival_view_planner_v1")
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--common-pair-distances", type=float, nargs="+", default=[1.5, 2.0, 2.5, 3.0])
    parser.add_argument("--standoff-distances", type=float, nargs="+", default=[1.25, 1.75, 2.25, 2.75])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument("--min-planned-requests", type=int, default=10)
    parser.add_argument("--min-plan-rows", type=int, default=10)
    parser.add_argument("--min-planned-queries", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
