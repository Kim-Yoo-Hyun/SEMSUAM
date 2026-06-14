import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from h001_runtime.analyze_pair_observation_design import PAIR_ACTIONS, common_pair_view
from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    artifact_index,
    candidate_target_position,
    horizontal_distance,
    parse_float_list,
    plan_standoff_viewpoint,
)


SCHEMA_VERSION = "h001.pair_observation_plan.v1"
POLICY_NAME = "PairTopAltObservation"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def copy_source_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: row.get(key)
        for key in [
            "episode_id",
            "episode_key",
            "scene_id",
            "query",
            "arbitration_action",
            "arbitration_reason",
            "arbitration_top_score",
            "arbitration_alt_score",
            "arbitration_support_gap_alt_minus_top",
            "arbitration_R_after2",
            "arbitration_R_after2_no_evidence",
            "arbitration_R_after2_contradiction",
            "arbitration_R_after2_ambiguity",
            "arbitration_R_after2_property_weakness",
            "association_recovered_after_second",
            "top_positive_support_after_second",
        ]
        if key in row
    }


def base_plan(
    row: Dict[str, Any],
    args: argparse.Namespace,
    source_index: int,
    pair_id: str,
    mode: str,
    role: str,
    candidate_id: str,
    top_id: str,
    alt_id: str,
    candidate_ids: List[str],
    pair_budget_views: Optional[int] = None,
) -> Dict[str, Any]:
    plan = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "source_index": source_index,
        "source_schema_version": row.get("schema_version"),
        "policy": str(args.policy_name),
        "viewpoint_policy": str(args.policy_name),
        "candidate_id": candidate_id,
        "candidate_ids": candidate_ids,
        "viewpoint_id": f"{pair_id}:{role}",
        "pair_observation_id": pair_id,
        "pair_observation_mode": mode,
        "pair_observation_role": role,
        "pair_top_candidate_id": top_id,
        "pair_alt_candidate_id": alt_id,
        "pair_budget_views": pair_budget_views if pair_budget_views is not None else (1 if mode == "common_pair_view" else 2),
        "pair_direct_goal_switch_allowed": False,
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
    }
    plan.update(copy_source_fields(row))
    return plan


def add_pair_geometry(
    plan: Dict[str, Any],
    top_candidate: Dict[str, Any],
    alt_candidate: Dict[str, Any],
) -> None:
    top_position = candidate_target_position(top_candidate)
    alt_position = candidate_target_position(alt_candidate)
    plan["pair_top_position"] = top_position
    plan["pair_alt_position"] = alt_position
    plan["pair_span_m"] = (
        None if top_position is None or alt_position is None else horizontal_distance(top_position, alt_position)
    )


def make_common_plan(
    row: Dict[str, Any],
    args: argparse.Namespace,
    source_index: int,
    pair_id: str,
    top_id: str,
    alt_id: str,
    top_candidate: Dict[str, Any],
    alt_candidate: Dict[str, Any],
    common: Dict[str, Any],
    mode: str = "common_pair_view",
    pair_budget_views: Optional[int] = None,
    dual_fallback_for_common: bool = False,
) -> Dict[str, Any]:
    plan = base_plan(
        row,
        args,
        source_index,
        pair_id,
        mode,
        "common",
        top_id,
        top_id,
        alt_id,
        [top_id, alt_id],
        pair_budget_views=pair_budget_views,
    )
    plan["viewpoint_position"] = common["pair_common_viewpoint_position"]
    plan["viewpoint_rotation"] = common["pair_common_viewpoint_rotation"]
    plan["pair_common_view_feasible"] = True
    plan["pair_dual_standoff_feasible"] = True
    plan["pair_dual_fallback_for_common"] = dual_fallback_for_common
    plan["pair_viewpoint_source"] = "common_pair_navmesh" if common.get("pair_common_viewpoint_navmesh_snapped") else "common_pair_geometry"
    for key, value in common.items():
        plan[key] = value
    add_pair_geometry(plan, top_candidate, alt_candidate)
    return plan


def make_dual_plan(
    row: Dict[str, Any],
    args: argparse.Namespace,
    source_index: int,
    pair_id: str,
    role: str,
    target_id: str,
    other_id: str,
    target_candidate: Dict[str, Any],
    other_candidate: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    mode: str = "matched_dual_standoff",
    pair_budget_views: Optional[int] = None,
    common_view_feasible: bool = False,
    dual_fallback_for_common: bool = False,
) -> Optional[Dict[str, Any]]:
    viewpoint = plan_standoff_viewpoint(
        {"scene_id": row.get("scene_id"), "viewpoint_position": row.get("viewpoint_position")},
        target_candidate,
        candidates,
        other_id,
        snapper,
        args,
    )
    if viewpoint is None:
        return None
    plan = base_plan(
        row,
        args,
        source_index,
        pair_id,
        mode,
        role,
        target_id,
        str(row.get("risk_top_candidate_id") or ""),
        str(row.get("risk_best_alt_candidate_id_after_second") or ""),
        [target_id, other_id],
        pair_budget_views=pair_budget_views,
    )
    plan["viewpoint_position"] = viewpoint["position"]
    plan["viewpoint_rotation"] = viewpoint["rotation"]
    plan["pair_common_view_feasible"] = common_view_feasible
    plan["pair_dual_standoff_feasible"] = True
    plan["pair_dual_fallback_for_common"] = dual_fallback_for_common
    plan["pair_viewpoint_source"] = viewpoint.get("viewpoint_source")
    plan["pair_standoff_target_position"] = viewpoint.get("target_position")
    plan["pair_standoff_desired_position"] = viewpoint.get("desired_position")
    plan["pair_standoff_target_horizontal_distance"] = viewpoint.get("target_horizontal_distance")
    plan["pair_standoff_snap_distance"] = viewpoint.get("snap_distance")
    plan["pair_standoff_navmesh_snapped"] = viewpoint.get("navmesh_snapped")
    plan["pair_standoff_navmesh_navigable"] = viewpoint.get("navmesh_navigable")
    plan["pair_standoff_direction_source"] = viewpoint.get("direction_source")
    plan["pair_standoff_distance_requested"] = viewpoint.get("standoff_distance_requested")
    plan["pair_standoff_projection_sane"] = viewpoint.get("projection_sane")
    plan["pair_standoff_viewpoint_yaw_rad"] = viewpoint.get("yaw")
    add_pair_geometry(plan, target_candidate if role == "top" else other_candidate, other_candidate if role == "top" else target_candidate)
    return plan


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    rows = load_jsonl(Path(args.arbitration_rows))
    candidates_by_episode = artifact_index(Path(args.candidate_artifact))
    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    pair_count = 0
    mode_counts: Counter[str] = Counter()
    common_dual_fallback_unavailable = 0

    try:
        for source_index, row in enumerate(rows):
            action = str(row.get("arbitration_action"))
            if action not in PAIR_ACTIONS:
                continue
            if int(args.max_pairs) > 0 and pair_count >= int(args.max_pairs):
                break
            scene_id = str(row.get("scene_id"))
            query = str(row.get("query"))
            top_id = str(row.get("risk_top_candidate_id") or "")
            alt_id = str(row.get("risk_best_alt_candidate_id_after_second") or "")
            pair_id = f"pair_top_alt:{source_index}"
            candidates = candidates_by_episode.get((scene_id, query), {})
            top_candidate = candidates.get(top_id)
            alt_candidate = candidates.get(alt_id)
            if top_candidate is None or alt_candidate is None:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "source_index": source_index,
                        "episode_key": row.get("episode_key"),
                        "scene_id": scene_id,
                        "query": query,
                        "arbitration_action": action,
                        "pair_observation_id": pair_id,
                        "pair_top_candidate_id": top_id,
                        "pair_alt_candidate_id": alt_id,
                        "skip_reason": "missing_top_or_alt_candidate",
                        "uses_gt_for_action": False,
                    }
                )
                continue
            common = common_pair_view(scene_id, top_candidate, alt_candidate, snapper, args)
            if common is not None:
                if bool(args.include_dual_fallback_for_common):
                    top_plan = make_dual_plan(
                        row,
                        args,
                        source_index,
                        pair_id,
                        "top",
                        top_id,
                        alt_id,
                        top_candidate,
                        alt_candidate,
                        candidates,
                        snapper,
                        mode="common_with_dual_fallback",
                        pair_budget_views=3,
                        common_view_feasible=True,
                        dual_fallback_for_common=True,
                    )
                    alt_plan = make_dual_plan(
                        row,
                        args,
                        source_index,
                        pair_id,
                        "alt",
                        alt_id,
                        top_id,
                        alt_candidate,
                        top_candidate,
                        candidates,
                        snapper,
                        mode="common_with_dual_fallback",
                        pair_budget_views=3,
                        common_view_feasible=True,
                        dual_fallback_for_common=True,
                    )
                    if top_plan is not None and alt_plan is not None:
                        common_plan = make_common_plan(
                            row,
                            args,
                            source_index,
                            pair_id,
                            top_id,
                            alt_id,
                            top_candidate,
                            alt_candidate,
                            common,
                            mode="common_with_dual_fallback",
                            pair_budget_views=3,
                            dual_fallback_for_common=True,
                        )
                        plan_rows.extend([common_plan, top_plan, alt_plan])
                        mode_counts["common_with_dual_fallback"] += 1
                        pair_count += 1
                        continue
                    common_dual_fallback_unavailable += 1

                plan_rows.append(
                    make_common_plan(
                        row,
                        args,
                        source_index,
                        pair_id,
                        top_id,
                        alt_id,
                        top_candidate,
                        alt_candidate,
                        common,
                    )
                )
                mode_counts["common_pair_view"] += 1
                pair_count += 1
                continue

            top_plan = make_dual_plan(
                row,
                args,
                source_index,
                pair_id,
                "top",
                top_id,
                alt_id,
                top_candidate,
                alt_candidate,
                candidates,
                snapper,
            )
            alt_plan = make_dual_plan(
                row,
                args,
                source_index,
                pair_id,
                "alt",
                alt_id,
                top_id,
                alt_candidate,
                top_candidate,
                candidates,
                snapper,
            )
            if top_plan is None or alt_plan is None:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "source_index": source_index,
                        "episode_key": row.get("episode_key"),
                        "scene_id": scene_id,
                        "query": query,
                        "arbitration_action": action,
                        "pair_observation_id": pair_id,
                        "pair_top_candidate_id": top_id,
                        "pair_alt_candidate_id": alt_id,
                        "skip_reason": "missing_dual_standoff_viewpoint",
                        "top_plan_available": top_plan is not None,
                        "alt_plan_available": alt_plan is not None,
                        "uses_gt_for_action": False,
                    }
                )
                continue
            plan_rows.extend([top_plan, alt_plan])
            mode_counts["matched_dual_standoff"] += 1
            pair_count += 1
    finally:
        snapper.close()

    write_jsonl(out_root / "pair_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "pair_observation_skipped.jsonl", skipped_rows)
    role_counts = Counter(str(row.get("pair_observation_role")) for row in plan_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "arbitration_rows": str(args.arbitration_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "policy": str(args.policy_name),
        "run_id": str(args.run_id),
        "pair_count": pair_count,
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "mode_counts": dict(sorted(mode_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "include_dual_fallback_for_common": bool(args.include_dual_fallback_for_common),
        "common_dual_fallback_unavailable_pairs": common_dual_fallback_unavailable,
        "common_pair_row_count": sum(row.get("pair_observation_mode") == "common_pair_view" for row in plan_rows),
        "matched_dual_row_count": sum(row.get("pair_observation_mode") == "matched_dual_standoff" for row in plan_rows),
        "common_with_dual_fallback_row_count": sum(
            row.get("pair_observation_mode") == "common_with_dual_fallback" for row in plan_rows
        ),
        "navmesh_snapped_row_rate": ratio(
            sum(bool(row.get("pair_common_viewpoint_navmesh_snapped") or row.get("pair_standoff_navmesh_snapped")) for row in plan_rows),
            len(plan_rows),
        ),
        "max_pair_bearing_separation_deg": float(args.max_pair_bearing_separation_deg),
        "standoff_distances": [float(value) for value in args.standoff_distances],
        "uses_gt_for_action": False,
        "next_expected_file": "pair_observation_frames.jsonl",
    }
    write_json(out_root / "pair_observation_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan paired top-vs-alt observation rows for H001.")
    parser.add_argument("--arbitration-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--run-id", default="h001_pair_top_alt_observation_v1")
    parser.add_argument("--policy-name", default=POLICY_NAME)
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--max-pair-bearing-separation-deg", type=float, default=70.0)
    parser.add_argument("--min-common-view-distance-m", type=float, default=1.75)
    parser.add_argument("--max-common-view-distance-m", type=float, default=4.0)
    parser.add_argument("--min-target-distance-m", type=float, default=0.75)
    parser.add_argument("--max-target-distance-m", type=float, default=6.0)
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    parser.add_argument(
        "--include-dual-fallback-for-common",
        action="store_true",
        help="For common-pair views, also emit top/alt standoff views so common-view one-sided visibility does not dominate pair evidence.",
    )
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
