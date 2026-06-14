import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.association_recovery_observation_plan.v1"
POLICY_NAME = "AssociationRecoveryObservation"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def finite_vector(value: Any, size: int) -> bool:
    if not isinstance(value, list) or len(value) != size:
        return False
    return all(safe_float(item) is not None for item in value)


def vector(value: Any) -> Optional[List[float]]:
    if finite_vector(value, 3):
        return [float(item) for item in value]
    return None


def euclidean(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def horizontal_distance(a: List[float], b: List[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def normalize_xz(dx: float, dz: float) -> Optional[Tuple[float, float]]:
    norm = math.hypot(dx, dz)
    if norm < 1e-6:
        return None
    return dx / norm, dz / norm


def yaw_to_point(base_position: List[float], target_position: List[float]) -> Optional[float]:
    dx = float(target_position[0]) - float(base_position[0])
    dz = float(target_position[2]) - float(base_position[2])
    if math.hypot(dx, dz) < 1e-4:
        return None
    # Same convention as export_hm3d_vlmaps: yaw 0 faces +Z.
    return math.atan2(dx, dz)


def quaternion_xyzw_from_yaw(yaw: float) -> List[float]:
    half = float(yaw) / 2.0
    return [0.0, math.sin(half), 0.0, math.cos(half)]


def parse_float_list(text: str) -> List[float]:
    values = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated float")
    return values


def artifact_index(path: Path) -> Dict[Tuple[str, str], Dict[str, Dict[str, Any]]]:
    index: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        scene_id = str(row.get("scene_id"))
        query = str(row.get("query"))
        candidates = {}
        for candidate in row.get("candidates") or []:
            candidate_id = candidate.get("candidate_id")
            if candidate_id is not None:
                candidates[str(candidate_id)] = candidate
        index[(scene_id, query)] = candidates
    return index


def feature_index(path: Optional[Path]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if path is None:
        return {}
    return {
        (str(row.get("episode_key")), str(row.get("candidate_id"))): row
        for row in load_jsonl(path)
        if row.get("episode_key") is not None and row.get("candidate_id") is not None
    }


def positive_support(feature: Optional[Dict[str, Any]]) -> bool:
    if not feature:
        return False
    s_det = safe_float(feature.get("S_det")) or safe_float(feature.get("N1_detector_score_only")) or 0.0
    s_proj = safe_float(feature.get("S_proj")) or 0.0
    s_depth = safe_float(feature.get("S_depth")) or 0.0
    s_prop = safe_float(feature.get("S_prop")) or 0.0
    aux = max(s_proj, s_depth, s_prop)
    return bool(s_det > 0.0 and aux > 0.0 and (s_det * aux) > 0.0)


def after_reason(row: Dict[str, Any]) -> str:
    no_evidence = safe_float(row.get("R_after_no_evidence")) or 0.0
    contradiction = safe_float(row.get("R_after_contradiction")) or 0.0
    ambiguity = safe_float(row.get("R_after_ambiguity")) or 0.0
    property_weakness = safe_float(row.get("R_after_property_weakness")) or 0.0
    if contradiction >= 0.6 and contradiction >= max(no_evidence, ambiguity, property_weakness):
        return "contradiction"
    if no_evidence >= 0.5:
        return "no_evidence"
    if property_weakness >= 0.5:
        return "property_weakness"
    if ambiguity >= 0.5:
        return "ambiguity"
    terms = {
        "no_evidence": no_evidence,
        "property_weakness": property_weakness,
        "ambiguity": ambiguity,
        "contradiction": contradiction,
    }
    return max(terms, key=lambda key: terms[key])


def candidate_viewpoint(candidate: Dict[str, Any]) -> Optional[Tuple[List[float], List[float]]]:
    position = vector(candidate.get("visit_position")) or vector(candidate.get("position"))
    if position is None:
        return None
    rotation = candidate.get("visit_rotation")
    if not finite_vector(rotation, 4):
        rotation = [0.0, 0.0, 0.0, 1.0]
    return position, [float(value) for value in rotation]


class NavmeshSnapper:
    def __init__(self, data_root: Optional[str]) -> None:
        self.data_root = Path(data_root) if data_root else None
        self._sim = None
        self._scene_id = None
        self._available = self.data_root is not None

    @property
    def available(self) -> bool:
        return bool(self._available)

    def close(self) -> None:
        if self._sim is not None:
            self._sim.close()
        self._sim = None
        self._scene_id = None

    def _ensure(self, scene_id: str) -> Any:
        if not self._available or self.data_root is None:
            raise RuntimeError("navmesh snapper is unavailable")
        if self._scene_id == scene_id and self._sim is not None:
            return self._sim
        self.close()
        try:
            import habitat_sim

            from h001_runtime.export_hm3d_vlmaps import navmesh_path, scene_path
        except Exception:
            self._available = False
            raise
        scene = scene_path(self.data_root, scene_id)
        sim_cfg = habitat_sim.SimulatorConfiguration()
        sim_cfg.scene_id = str(scene)
        sim_cfg.enable_physics = False

        agent_cfg = habitat_sim.agent.AgentConfiguration()
        agent_cfg.sensor_specifications = []

        self._sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
        navmesh = navmesh_path(scene)
        if navmesh.exists() and not self._sim.pathfinder.is_loaded:
            self._sim.pathfinder.load_nav_mesh(str(navmesh))
        if not self._sim.pathfinder.is_loaded:
            self.close()
            raise RuntimeError(f"navmesh is not loaded for scene: {scene}")
        self._scene_id = scene_id
        return self._sim

    def snap(self, scene_id: str, point: List[float]) -> Tuple[List[float], bool, Optional[float]]:
        if not self._available:
            return point, False, None
        try:
            import numpy as np

            sim = self._ensure(scene_id)
            desired = np.asarray(point, dtype=np.float32)
            snapped = sim.pathfinder.snap_point(desired)
            snapped_list = [float(value) for value in snapped]
            if not finite_vector(snapped_list, 3):
                return point, False, None
            is_navigable = bool(sim.pathfinder.is_navigable(snapped))
            snap_distance = euclidean(point, snapped_list)
            return snapped_list, is_navigable, snap_distance
        except Exception:
            self._available = False
            return point, False, None


def candidate_target_position(candidate: Dict[str, Any]) -> Optional[List[float]]:
    return vector(candidate.get("position")) or vector(candidate.get("visit_position"))


def candidate_floor_y(candidate: Dict[str, Any], source_row: Dict[str, Any]) -> Optional[float]:
    visit = vector(candidate.get("visit_position"))
    if visit is not None:
        return float(visit[1])
    source = vector(source_row.get("viewpoint_position"))
    if source is not None:
        return float(source[1])
    target = candidate_target_position(candidate)
    return None if target is None else float(target[1])


def standoff_directions(
    source_row: Dict[str, Any],
    target_position: List[float],
    candidates: Dict[str, Dict[str, Any]],
    alt_id: Optional[str],
) -> List[Tuple[float, float, str]]:
    directions: List[Tuple[float, float, str]] = []

    def add(dx: float, dz: float, source: str) -> None:
        unit = normalize_xz(dx, dz)
        if unit is None:
            return
        ux, uz = unit
        if any(abs(ux - old_x) < 1e-3 and abs(uz - old_z) < 1e-3 for old_x, old_z, _ in directions):
            return
        directions.append((ux, uz, source))

    source_view = vector(source_row.get("viewpoint_position"))
    if source_view is not None:
        add(source_view[0] - target_position[0], source_view[2] - target_position[2], "source_viewpoint_to_target")

    if alt_id and alt_id in candidates:
        alt_position = candidate_target_position(candidates[alt_id])
        if alt_position is not None:
            add(alt_position[0] - target_position[0], alt_position[2] - target_position[2], "alt_candidate_to_target")
            add(target_position[0] - alt_position[0], target_position[2] - alt_position[2], "target_to_alt_candidate")

    for degrees in (0, 45, 90, 135, 180, 225, 270, 315):
        radians = math.radians(degrees)
        add(math.sin(radians), math.cos(radians), f"compass_{degrees}")
    return directions


def plan_standoff_viewpoint(
    row: Dict[str, Any],
    target: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    alt_id: Optional[str],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Dict[str, Any]]:
    target_position = candidate_target_position(target)
    floor_y = candidate_floor_y(target, row)
    if target_position is None or floor_y is None:
        return None

    source_position = vector(row.get("viewpoint_position"))
    scene_id = str(row.get("scene_id"))
    best: Optional[Tuple[float, Dict[str, Any]]] = None
    for distance in args.standoff_distances:
        for dx, dz, direction_source in standoff_directions(row, target_position, candidates, alt_id):
            desired = [
                float(target_position[0]) + dx * float(distance),
                float(floor_y),
                float(target_position[2]) + dz * float(distance),
            ]
            snapped, navigable, snap_distance = snapper.snap(scene_id, desired)
            target_horizontal_distance = horizontal_distance(snapped, target_position)
            if target_horizontal_distance < float(args.min_standoff_distance_m):
                continue
            if target_horizontal_distance > float(args.max_standoff_distance_m):
                continue
            yaw = yaw_to_point(snapped, target_position)
            if yaw is None:
                continue
            travel_proxy = horizontal_distance(source_position, snapped) if source_position is not None else 0.0
            snap_penalty = snap_distance if snap_distance is not None else 0.0
            navigable_bonus = -0.25 if navigable else 0.0
            score = (
                abs(target_horizontal_distance - float(args.preferred_standoff_distance_m))
                + 0.20 * snap_penalty
                + 0.03 * travel_proxy
                + navigable_bonus
            )
            item = {
                "position": snapped,
                "rotation": quaternion_xyzw_from_yaw(yaw),
                "yaw": float(yaw),
                "target_position": target_position,
                "target_horizontal_distance": float(target_horizontal_distance),
                "desired_position": desired,
                "snap_distance": snap_distance,
                "navmesh_snapped": snap_distance is not None,
                "navmesh_navigable": navigable,
                "direction_source": direction_source,
                "standoff_distance_requested": float(distance),
                "viewpoint_source": "standoff_navmesh" if snap_distance is not None else "standoff_geometry",
                "projection_sane": True,
                "score": float(score),
            }
            if best is None or score < best[0]:
                best = (score, item)
    if best is not None:
        return best[1]

    fallback = candidate_viewpoint(target)
    if fallback is None:
        return None
    position, _rotation = fallback
    yaw = yaw_to_point(position, target_position)
    rotation = quaternion_xyzw_from_yaw(yaw) if yaw is not None else [0.0, 0.0, 0.0, 1.0]
    return {
        "position": position,
        "rotation": rotation,
        "yaw": yaw,
        "target_position": target_position,
        "target_horizontal_distance": horizontal_distance(position, target_position),
        "desired_position": position,
        "snap_distance": None,
        "navmesh_snapped": False,
        "navmesh_navigable": bool(target.get("visit_position_navigable")),
        "direction_source": "candidate_visit_position_fallback",
        "standoff_distance_requested": None,
        "viewpoint_source": "candidate_visit_position_fallback",
        "projection_sane": yaw is not None,
        "score": None,
    }


def select_target(
    row: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    features: Dict[Tuple[str, str], Dict[str, Any]],
    pair_view_max_distance_m: float,
) -> Tuple[Optional[str], Optional[str], List[str], str]:
    episode_key = str(row.get("episode_key"))
    top_id = str(row.get("risk_top_candidate_id") or row.get("candidate_id") or "")
    alt_id = str(row.get("risk_best_alt_candidate_id") or "")
    reason = after_reason(row)
    candidate_ids = [candidate_id for candidate_id in [top_id, alt_id] if candidate_id and candidate_id in candidates]
    top_feature = features.get((episode_key, top_id))
    top_supported = positive_support(top_feature)

    if top_id not in candidates:
        return None, alt_id if alt_id in candidates else None, candidate_ids, "no_feasible_viewpoint"

    if reason in {"no_evidence", "property_weakness"}:
        return top_id, alt_id if alt_id in candidates else None, candidate_ids or [top_id], reason

    if reason == "ambiguity":
        if not top_supported:
            return top_id, alt_id if alt_id in candidates else None, candidate_ids or [top_id], reason
        if alt_id in candidates:
            return alt_id, top_id, candidate_ids, reason
        return top_id, None, candidate_ids or [top_id], reason

    if reason == "contradiction":
        top_view = candidate_viewpoint(candidates[top_id])
        alt_view = candidate_viewpoint(candidates[alt_id]) if alt_id in candidates else None
        if top_view is None or alt_view is None:
            return None, alt_id if alt_id in candidates else None, candidate_ids, "no_feasible_viewpoint"
        if euclidean(top_view[0], alt_view[0]) > pair_view_max_distance_m:
            return None, alt_id, candidate_ids, "travel_cost_blocked"
        current = vector(row.get("viewpoint_position"))
        if current is None:
            return top_id, alt_id, candidate_ids, reason
        top_distance = euclidean(current, top_view[0])
        alt_distance = euclidean(current, alt_view[0])
        return (top_id if top_distance <= alt_distance else alt_id), (alt_id if top_distance <= alt_distance else top_id), candidate_ids, reason

    return top_id, alt_id if alt_id in candidates else None, candidate_ids or [top_id], reason


def expected_gain(reason: str, row: Dict[str, Any], target_feature: Optional[Dict[str, Any]]) -> float:
    gain = 0.2
    if reason == "no_evidence":
        gain += 0.5
    elif reason == "property_weakness":
        gain += 0.4
    elif reason == "ambiguity":
        gain += 0.3
    elif reason == "contradiction":
        gain += 0.2
    if not positive_support(target_feature):
        gain += 0.2
    if (safe_float(row.get("R_after")) or 0.0) >= 0.9:
        gain += 0.1
    return max(0.0, min(1.0, gain))


def copy_manifest_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if key.startswith("manifest_")
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    candidates_by_episode = artifact_index(Path(args.candidate_artifact))
    features = feature_index(Path(args.object_node_features) if args.object_node_features else None)
    viewpoint_rows = load_jsonl(Path(args.viewpoint_decisions))
    snapper = NavmeshSnapper(args.data_root)
    unresolved = [
        row
        for row in viewpoint_rows
        if str(row.get("policy")) == str(args.policy)
        and row.get("risk_unresolved_no_commit") is True
        and row.get("risk_resolved_after_reobserve") is not True
    ]

    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    projection_sane_count = 0
    navmesh_snapped_count = 0
    try:
        for source_index, row in enumerate(unresolved):
            if int(args.max_rows) > 0 and len(plan_rows) >= int(args.max_rows):
                break
            scene_id = str(row.get("scene_id"))
            query = str(row.get("query"))
            episode_key = str(row.get("episode_key"))
            candidates = candidates_by_episode.get((scene_id, query), {})
            target_id, alt_id, candidate_ids, reason = select_target(
                row,
                candidates,
                features,
                float(args.pair_view_max_distance_m),
            )
            if target_id is None or target_id not in candidates:
                skipped = {
                    "schema_version": SCHEMA_VERSION,
                    "source_index": source_index,
                    "episode_key": episode_key,
                    "scene_id": scene_id,
                    "query": query,
                    "risk_top_candidate_id": row.get("risk_top_candidate_id"),
                    "risk_best_alt_candidate_id": row.get("risk_best_alt_candidate_id"),
                    "second_observation_reason": reason,
                    "skip_reason": "no_renderable_target_candidate",
                    "uses_gt_for_action": False,
                }
                skipped.update(copy_manifest_fields(row))
                skipped_rows.append(skipped)
                reason_counts[reason] += 1
                continue

            target = candidates[target_id]
            viewpoint = plan_standoff_viewpoint(row, target, candidates, alt_id, snapper, args)
            if viewpoint is None:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "source_index": source_index,
                        "episode_key": episode_key,
                        "scene_id": scene_id,
                        "query": query,
                        "second_observation_candidate_id": target_id,
                        "second_observation_reason": "no_feasible_viewpoint",
                        "skip_reason": "missing_standoff_viewpoint",
                        "uses_gt_for_action": False,
                        **copy_manifest_fields(row),
                    }
                )
                reason_counts["no_feasible_viewpoint"] += 1
                continue

            viewpoint_position = viewpoint["position"]
            viewpoint_rotation = viewpoint["rotation"]
            target_feature = features.get((episode_key, target_id))
            top_id = str(row.get("risk_top_candidate_id") or row.get("candidate_id"))
            ordered_ids: List[str] = []
            for candidate_id in [top_id, target_id, alt_id, *candidate_ids]:
                if candidate_id and candidate_id in candidates and candidate_id not in ordered_ids:
                    ordered_ids.append(candidate_id)

            plan = {
                "schema_version": SCHEMA_VERSION,
                "run_id": str(args.run_id),
                "source_run_id": row.get("run_id"),
                "source_viewpoint_id": row.get("viewpoint_id"),
                "source_index": source_index,
                "episode_id": row.get("episode_id"),
                "episode_key": episode_key,
                "policy": POLICY_NAME,
                "decision_step": int(row.get("decision_step") or 0) + 1,
                "scene_id": scene_id,
                "query": query,
                "candidate_id": target_id,
                "candidate_ids": ordered_ids[: max(1, int(args.max_candidate_ids))],
                "viewpoint_id": f"association_recovery:{source_index}:2",
                "viewpoint_position": viewpoint_position,
                "viewpoint_rotation": viewpoint_rotation,
                "viewpoint_policy": POLICY_NAME,
                "semantic_gain_pred": None,
                "slam_gain_pred": None,
                "travel_cost_pred": None,
                "travel_cost_actual": None,
                "observation_success": True,
                "commit_after_reobserve": False,
                "final_candidate_changed": False,
                "final_candidate_id_before": top_id,
                "final_candidate_id_after": None,
                "risk_evidence_resolution_policy": POLICY_NAME,
                "second_observation_triggered": True,
                "second_observation_reason": reason,
                "second_observation_candidate_id": target_id,
                "second_observation_alt_candidate_id": alt_id,
                "second_observation_viewpoint_id": f"association_recovery:{source_index}:2",
                "second_observation_expected_association_gain": expected_gain(reason, row, target_feature),
                "second_observation_viewpoint_source": viewpoint.get("viewpoint_source"),
                "second_observation_target_position": viewpoint.get("target_position"),
                "second_observation_desired_position": viewpoint.get("desired_position"),
                "second_observation_target_horizontal_distance": viewpoint.get("target_horizontal_distance"),
                "second_observation_snap_distance": viewpoint.get("snap_distance"),
                "second_observation_navmesh_snapped": viewpoint.get("navmesh_snapped"),
                "second_observation_navmesh_navigable": viewpoint.get("navmesh_navigable"),
                "second_observation_direction_source": viewpoint.get("direction_source"),
                "second_observation_standoff_distance_requested": viewpoint.get("standoff_distance_requested"),
                "second_observation_projection_sane": viewpoint.get("projection_sane"),
                "second_observation_viewpoint_yaw_rad": viewpoint.get("yaw"),
                "risk_direct_goal_switch_allowed": False,
                "uses_gt_for_action": False,
            }
            for key in [
                "risk_top_candidate_id",
                "risk_best_alt_candidate_id",
                "R_before",
                "R_after",
                "R_after_no_evidence",
                "R_after_contradiction",
                "R_after_ambiguity",
                "R_after_property_weakness",
                "risk_delta_after_reobserve",
                "risk_resolution_commit",
                "risk_resolution_commit_reason",
                "risk_resolution_top_positive_support",
                "risk_total_trigger",
                "risk_resolution_delta_trigger",
                "risk_resolution_max_risk",
                "risk_resolution_max_contradiction",
                "risk_resolution_require_positive_support",
                "dominant_risk_term",
                "success_lost_by_defer",
                "wrong_goal_avoided_by_defer",
            ]:
                plan[key] = row.get(key)
            plan.update(copy_manifest_fields(row))
            plan_rows.append(plan)
            reason_counts[reason] += 1
            projection_sane_count += int(bool(viewpoint.get("projection_sane")))
            navmesh_snapped_count += int(bool(viewpoint.get("navmesh_snapped")))
    finally:
        snapper.close()

    write_jsonl(out_root / "second_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "second_observation_skipped.jsonl", skipped_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(out_root),
        "viewpoint_decisions": str(args.viewpoint_decisions),
        "candidate_artifact": str(args.candidate_artifact),
        "object_node_features": str(args.object_node_features) if args.object_node_features else None,
        "policy": str(args.policy),
        "run_id": str(args.run_id),
        "unresolved_input_rows": len(unresolved),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "max_rows": int(args.max_rows),
        "reason_counts": dict(sorted(reason_counts.items())),
        "projection_sane_rows": projection_sane_count,
        "projection_sane_rate": ratio(projection_sane_count, len(plan_rows)),
        "navmesh_snapped_rows": navmesh_snapped_count,
        "navmesh_snapped_rate": ratio(navmesh_snapped_count, len(plan_rows)),
        "standoff_distances": [float(value) for value in args.standoff_distances],
        "preferred_standoff_distance_m": float(args.preferred_standoff_distance_m),
        "min_standoff_distance_m": float(args.min_standoff_distance_m),
        "max_standoff_distance_m": float(args.max_standoff_distance_m),
        "uses_gt_for_action": False,
        "next_expected_file": "second_observation_frames.jsonl",
    }
    write_json(out_root / "second_observation_plan_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan second observations for unresolved H001 risk rows.")
    parser.add_argument("--viewpoint-decisions", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--object-node-features", default=None)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="RiskResolutionReobserve")
    parser.add_argument("--run-id", default="h001_association_recovery_observation_v1")
    parser.add_argument("--max-rows", type=int, default=20)
    parser.add_argument("--max-candidate-ids", type=int, default=5)
    parser.add_argument("--pair-view-max-distance-m", type=float, default=4.0)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--standoff-distances", type=parse_float_list, default=[1.25, 1.75, 2.25])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
