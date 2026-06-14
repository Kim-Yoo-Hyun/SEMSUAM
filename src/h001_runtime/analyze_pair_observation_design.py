import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    artifact_index,
    candidate_floor_y,
    candidate_target_position,
    finite_vector,
    horizontal_distance,
    normalize_xz,
    quaternion_xyzw_from_yaw,
    safe_float,
    vector,
    yaw_to_point,
)


SCHEMA_VERSION = "h001.pair_observation_design.v1"
PAIR_ACTIONS = {"reject_top_or_request_pair_view", "request_paired_top_alt_view"}


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


def angle_deg(a: float, b: float) -> float:
    diff = math.atan2(math.sin(a - b), math.cos(a - b))
    return abs(math.degrees(diff))


def target_distance_range_ok(position: List[float], top: List[float], alt: List[float], args: argparse.Namespace) -> bool:
    top_distance = horizontal_distance(position, top)
    alt_distance = horizontal_distance(position, alt)
    return (
        float(args.min_target_distance_m) <= top_distance <= float(args.max_target_distance_m)
        and float(args.min_target_distance_m) <= alt_distance <= float(args.max_target_distance_m)
    )


def pair_directions(top: List[float], alt: List[float]) -> List[Tuple[float, float, str]]:
    directions: List[Tuple[float, float, str]] = []

    def add(dx: float, dz: float, source: str) -> None:
        unit = normalize_xz(dx, dz)
        if unit is None:
            return
        ux, uz = unit
        if any(abs(ux - old_x) < 1e-3 and abs(uz - old_z) < 1e-3 for old_x, old_z, _ in directions):
            return
        directions.append((ux, uz, source))

    axis = normalize_xz(alt[0] - top[0], alt[2] - top[2])
    if axis is not None:
        ax, az = axis
        add(-az, ax, "pair_axis_perpendicular_left")
        add(az, -ax, "pair_axis_perpendicular_right")
        add(ax, az, "pair_axis_from_top_to_alt")
        add(-ax, -az, "pair_axis_from_alt_to_top")
    for degrees in (0, 45, 90, 135, 180, 225, 270, 315):
        radians = math.radians(degrees)
        add(math.sin(radians), math.cos(radians), f"compass_{degrees}")
    return directions


def common_pair_view(
    scene_id: str,
    top_candidate: Dict[str, Any],
    alt_candidate: Dict[str, Any],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    top = candidate_target_position(top_candidate)
    alt = candidate_target_position(alt_candidate)
    if top is None or alt is None:
        return None
    pair_span = horizontal_distance(top, alt)
    max_sep_rad = math.radians(float(args.max_pair_bearing_separation_deg))
    if max_sep_rad <= 0.0:
        return None
    required_distance = (pair_span / 2.0) / max(math.tan(max_sep_rad / 2.0), 1e-6)
    required_distance = max(float(args.min_common_view_distance_m), required_distance)
    if required_distance > float(args.max_common_view_distance_m):
        return None

    midpoint = [
        (float(top[0]) + float(alt[0])) / 2.0,
        (float(top[1]) + float(alt[1])) / 2.0,
        (float(top[2]) + float(alt[2])) / 2.0,
    ]
    floor_y = candidate_floor_y(top_candidate, {}) or candidate_floor_y(alt_candidate, {}) or midpoint[1]
    distances = sorted(
        {
            required_distance,
            min(float(args.max_common_view_distance_m), required_distance + 0.5),
            float(args.max_common_view_distance_m),
        }
    )
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in distances:
        for dx, dz, direction_source in pair_directions(top, alt):
            desired = [
                float(midpoint[0]) + dx * distance,
                float(floor_y),
                float(midpoint[2]) + dz * distance,
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            if not target_distance_range_ok(snapped, top, alt, args):
                continue
            yaw_top = yaw_to_point(snapped, top)
            yaw_alt = yaw_to_point(snapped, alt)
            if yaw_top is None or yaw_alt is None:
                continue
            separation = angle_deg(yaw_top, yaw_alt)
            if separation > float(args.max_pair_bearing_separation_deg):
                continue
            yaw_mid = yaw_to_point(snapped, midpoint)
            if yaw_mid is None:
                continue
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            score = separation + 2.0 * abs(distance - required_distance) + 0.25 * snap_penalty
            item = {
                "pair_common_viewpoint_position": snapped,
                "pair_common_viewpoint_rotation": quaternion_xyzw_from_yaw(yaw_mid),
                "pair_common_viewpoint_yaw_rad": float(yaw_mid),
                "pair_common_viewpoint_direction_source": direction_source,
                "pair_common_viewpoint_desired_position": desired,
                "pair_common_viewpoint_snap_distance": snap_distance,
                "pair_common_viewpoint_navmesh_snapped": snap_distance is not None,
                "pair_common_viewpoint_navmesh_navigable": navigable,
                "pair_common_required_distance_m": float(required_distance),
                "pair_common_chosen_distance_m": float(distance),
                "pair_common_bearing_separation_deg": float(separation),
                "pair_common_top_distance_m": float(horizontal_distance(snapped, top)),
                "pair_common_alt_distance_m": float(horizontal_distance(snapped, alt)),
                "pair_common_score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, item)
    return None if best is None else best[1]


def dual_standoff_feasible(top_candidate: Dict[str, Any], alt_candidate: Dict[str, Any]) -> bool:
    return candidate_target_position(top_candidate) is not None and candidate_target_position(alt_candidate) is not None


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.arbitration_rows))
    candidates_by_episode = artifact_index(Path(args.candidate_artifact))
    snapper = NavmeshSnapper(args.data_root)
    out_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    try:
        for row in rows:
            action = str(row.get("arbitration_action"))
            if action not in PAIR_ACTIONS:
                continue
            scene_id = str(row.get("scene_id"))
            query = str(row.get("query"))
            top_id = str(row.get("risk_top_candidate_id") or "")
            alt_id = str(row.get("risk_best_alt_candidate_id_after_second") or "")
            candidates = candidates_by_episode.get((scene_id, query), {})
            top = candidates.get(top_id)
            alt = candidates.get(alt_id)
            if top is None or alt is None:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "episode_key": row.get("episode_key"),
                        "scene_id": scene_id,
                        "query": query,
                        "arbitration_action": action,
                        "risk_top_candidate_id": top_id,
                        "risk_best_alt_candidate_id_after_second": alt_id,
                        "skip_reason": "missing_top_or_alt_candidate",
                        "uses_gt_for_action": False,
                    }
                )
                continue
            top_position = candidate_target_position(top)
            alt_position = candidate_target_position(alt)
            if top_position is None or alt_position is None:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "episode_key": row.get("episode_key"),
                        "scene_id": scene_id,
                        "query": query,
                        "arbitration_action": action,
                        "risk_top_candidate_id": top_id,
                        "risk_best_alt_candidate_id_after_second": alt_id,
                        "skip_reason": "missing_top_or_alt_position",
                        "uses_gt_for_action": False,
                    }
                )
                continue
            common = common_pair_view(scene_id, top, alt, snapper, args)
            dual_ok = dual_standoff_feasible(top, alt)
            if common is not None:
                mode = "common_pair_view"
                next_gate = "plan_common_pair_view"
            elif dual_ok:
                mode = "matched_dual_standoff"
                next_gate = "plan_matched_dual_standoff"
            else:
                mode = "infeasible"
                next_gate = "defer_no_pair_observation"
            out = {
                "schema_version": SCHEMA_VERSION,
                "episode_key": row.get("episode_key"),
                "scene_id": scene_id,
                "query": query,
                "arbitration_action": action,
                "arbitration_reason": row.get("arbitration_reason"),
                "risk_top_candidate_id": top_id,
                "risk_best_alt_candidate_id_after_second": alt_id,
                "pair_observation_mode": mode,
                "pair_observation_next_gate": next_gate,
                "pair_common_view_feasible": common is not None,
                "pair_dual_standoff_feasible": dual_ok,
                "pair_span_m": float(horizontal_distance(top_position, alt_position)),
                "pair_top_position": top_position,
                "pair_alt_position": alt_position,
                "pair_top_score": row.get("arbitration_top_score"),
                "pair_alt_score": row.get("arbitration_alt_score"),
                "pair_support_gap_alt_minus_top": row.get("arbitration_support_gap_alt_minus_top"),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": False,
            }
            if common is not None:
                out.update(common)
            out_rows.append(out)
    finally:
        snapper.close()

    out_root = Path(args.out_root)
    write_jsonl(out_root / "pair_observation_design_rows.jsonl", out_rows)
    write_jsonl(out_root / "pair_observation_design_skipped.jsonl", skipped_rows)
    mode_counts = Counter(row["pair_observation_mode"] for row in out_rows)
    action_counts = Counter(row["arbitration_action"] for row in out_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "arbitration_rows": str(args.arbitration_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "pair_trigger_rows": len(out_rows),
        "skipped_rows": len(skipped_rows),
        "mode_counts": dict(sorted(mode_counts.items())),
        "arbitration_action_counts": dict(sorted(action_counts.items())),
        "common_pair_view_feasible_rate": ratio(sum(row["pair_common_view_feasible"] for row in out_rows), len(out_rows)),
        "dual_standoff_feasible_rate": ratio(sum(row["pair_dual_standoff_feasible"] for row in out_rows), len(out_rows)),
        "max_pair_bearing_separation_deg": float(args.max_pair_bearing_separation_deg),
        "min_common_view_distance_m": float(args.min_common_view_distance_m),
        "max_common_view_distance_m": float(args.max_common_view_distance_m),
        "min_target_distance_m": float(args.min_target_distance_m),
        "max_target_distance_m": float(args.max_target_distance_m),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "output_files": {
            "rows": "pair_observation_design_rows.jsonl",
            "skipped": "pair_observation_design_skipped.jsonl",
            "summary": "pair_observation_design_summary.json",
        },
    }
    write_json(out_root / "pair_observation_design_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Assess non-GT paired top-vs-alt observation design feasibility.")
    parser.add_argument("--arbitration-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--max-pair-bearing-separation-deg", type=float, default=70.0)
    parser.add_argument("--min-common-view-distance-m", type=float, default=1.75)
    parser.add_argument("--max-common-view-distance-m", type=float, default=4.0)
    parser.add_argument("--min-target-distance-m", type=float, default=0.75)
    parser.add_argument("--max-target-distance-m", type=float, default=6.0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
