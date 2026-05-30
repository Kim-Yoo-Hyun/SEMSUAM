import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image

from h001_runtime.export_hm3d_vlmaps import (
    make_sim,
    quaternion_from_yaw,
    quaternion_xyzw,
    scene_path,
    vlmaps_camera_pose,
    write_pose,
)
from h001_runtime.export_postview_frames import finite_vector, quaternion_from_xyzw


SCHEMA_VERSION = "h001.postview.v2"
DEFAULT_GROUNDED_POINT_HEIGHT_M = 0.8
DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M = 2.0


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return value or "value"


def decision_id(row: Dict[str, Any]) -> str:
    key = "|".join(
        [
            str(row.get("run_id")),
            str(row.get("episode_key") or row.get("episode_id")),
            str(row.get("policy")),
            str(row.get("viewpoint_id")),
            str(row.get("candidate_id")),
            "postview_v2",
        ]
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    scene = Path(str(row.get("scene_id") or "scene")).name.replace(".basis.glb", "").replace(".glb", "")
    query = slug(str(row.get("query") or "query"))
    return f"{scene}_{query}_{digest}"


def parse_float_list(text: str) -> List[float]:
    values = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated float")
    return values


def finite_float(value: Any) -> Optional[float]:
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
    values = [finite_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return [float(item) for item in values]


def artifact_index(path: Path) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    indexed: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        scene_id = str(row.get("scene_id"))
        query = str(row.get("query"))
        candidates = list(row.get("candidates") or [])
        candidates.sort(key=lambda cand: finite_float(cand.get("score")) or -math.inf, reverse=True)
        indexed[(scene_id, query)] = candidates
    return indexed


def select_candidate_set(
    candidates: List[Dict[str, Any]],
    frame_candidate_id: Optional[str],
    tie_band: float,
    max_candidates: int,
) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    top_score = finite_float(candidates[0].get("score")) or 0.0
    selected = [
        cand
        for cand in candidates
        if (finite_float(cand.get("score")) or -math.inf) >= top_score - tie_band
    ]
    if frame_candidate_id is not None and all(str(c.get("candidate_id")) != frame_candidate_id for c in selected):
        frame_candidate = next((c for c in candidates if str(c.get("candidate_id")) == frame_candidate_id), None)
        if frame_candidate is not None:
            selected.insert(0, frame_candidate)

    if max_candidates > 0 and len(selected) > max_candidates:
        trimmed = selected[:max_candidates]
        if frame_candidate_id is not None and all(str(c.get("candidate_id")) != frame_candidate_id for c in trimmed):
            frame_candidate = next((c for c in selected if str(c.get("candidate_id")) == frame_candidate_id), None)
            if frame_candidate is not None:
                trimmed[-1] = frame_candidate
        selected = trimmed
    return selected


def select_candidate_set_for_row(
    row: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    frame_candidate_id: Optional[str],
    tie_band: float,
    max_candidates: int,
) -> Tuple[List[Dict[str, Any]], str]:
    explicit_ids = [
        str(value)
        for value in (
            row.get("candidate_ids")
            or row.get("second_observation_candidate_ids")
            or []
        )
        if value is not None
    ]
    if not explicit_ids:
        return select_candidate_set(candidates, frame_candidate_id, tie_band, max_candidates), "semantic_tie_band"

    by_id = {str(candidate.get("candidate_id")): candidate for candidate in candidates}
    ordered_ids: List[str] = []
    for candidate_id in explicit_ids:
        if candidate_id not in ordered_ids:
            ordered_ids.append(candidate_id)
    if frame_candidate_id is not None and frame_candidate_id not in ordered_ids:
        ordered_ids.insert(0, frame_candidate_id)

    selected = [by_id[candidate_id] for candidate_id in ordered_ids if candidate_id in by_id]
    if max_candidates > 0:
        selected = selected[:max_candidates]
    if not selected:
        return select_candidate_set(candidates, frame_candidate_id, tie_band, max_candidates), "semantic_tie_band_fallback"
    return selected, "explicit_candidate_ids"


def passthrough_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    prefixes = (
        "pair_",
        "arbitration_",
        "external_",
        "followup_",
        "source_objective_",
        "source_followup_",
        "second_stage_",
        "rival_identity_",
        "revision_",
        "expanded_",
        "proxy_",
        "source_pool_",
        "focus_",
        "goal_validity_",
        "object_relation_",
        "rival_",
        "standoff_",
        "target_",
    )
    keys = {
        "contract_name",
        "planner_name",
        "request_index",
        "request_reason",
        "role",
        "scene_key",
        "source_name",
        "target_index",
        "viewpoint_pair_role",
        "viewpoint_source",
    }
    return {key: value for key, value in row.items() if key.startswith(prefixes) or key in keys}


def grounded_candidate_point(
    candidate: Dict[str, Any],
    grounded_point_height_m: float,
    grounded_point_max_vertical_gap_m: float,
) -> Optional[np.ndarray]:
    position = vector3(candidate.get("position"))
    visit_position = vector3(candidate.get("visit_position"))
    if position is None and visit_position is None:
        return None
    if position is None:
        return np.asarray(
            [
                float(visit_position[0]),
                float(visit_position[1]) + float(grounded_point_height_m),
                float(visit_position[2]),
            ],
            dtype=np.float64,
        )
    if visit_position is None:
        return np.asarray(position, dtype=np.float64)
    if abs(float(position[1]) - float(visit_position[1])) > float(grounded_point_max_vertical_gap_m):
        return np.asarray(
            [
                float(position[0]),
                float(visit_position[1]) + float(grounded_point_height_m),
                float(position[2]),
            ],
            dtype=np.float64,
        )
    return np.asarray(position, dtype=np.float64)


def candidate_point(
    candidate: Dict[str, Any],
    field: str,
    grounded_point_height_m: float,
    grounded_point_max_vertical_gap_m: float,
) -> Optional[np.ndarray]:
    if field == "grounded_position":
        return grounded_candidate_point(candidate, grounded_point_height_m, grounded_point_max_vertical_gap_m)
    fields = [field]
    for fallback in ("position", "visit_position"):
        if fallback not in fields:
            fields.append(fallback)
    for name in fields:
        values = vector3(candidate.get(name))
        if values is not None:
            return np.asarray(values, dtype=np.float64)
    return None


def yaw_to_point(base_position: np.ndarray, point_world: np.ndarray) -> Optional[float]:
    dx = float(point_world[0] - base_position[0])
    dz = float(point_world[2] - base_position[2])
    if math.hypot(dx, dz) < 1e-4:
        return None
    # In the Habitat camera convention used by export_hm3d_vlmaps, yaw 0 faces +Z.
    return math.atan2(dx, dz)


def normalize_angle(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


def angular_distance(a: float, b: float) -> float:
    return abs(normalize_angle(a - b))


def build_heading_specs(
    row: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    base_position: np.ndarray,
    yaw_offsets_deg: List[float],
    dedupe_degrees: float,
    include_stored_heading: bool,
    candidate_point_field: str,
    grounded_point_height_m: float,
    grounded_point_max_vertical_gap_m: float,
) -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    used_yaws: List[float] = []

    if include_stored_heading:
        specs.append(
            {
                "target_candidate_id": str(row.get("candidate_id")),
                "rotation_source": "stored_viewpoint_rotation",
                "yaw_offset_deg": None,
                "yaw_rad": None,
                "rotation": quaternion_from_xyzw(row.get("viewpoint_rotation")),
            }
        )

    min_distance = math.radians(max(0.0, dedupe_degrees))
    for candidate in candidates:
        point = candidate_point(
            candidate,
            candidate_point_field,
            grounded_point_height_m,
            grounded_point_max_vertical_gap_m,
        )
        if point is None:
            continue
        yaw = yaw_to_point(base_position, point)
        if yaw is None:
            continue
        for offset_deg in yaw_offsets_deg:
            yaw_with_offset = normalize_angle(yaw + math.radians(offset_deg))
            if any(angular_distance(yaw_with_offset, used) < min_distance for used in used_yaws):
                continue
            used_yaws.append(yaw_with_offset)
            specs.append(
                {
                    "target_candidate_id": str(candidate.get("candidate_id")),
                    "rotation_source": "bearing_to_candidate",
                    "yaw_offset_deg": float(offset_deg),
                    "yaw_rad": float(yaw_with_offset),
                    "rotation": quaternion_from_yaw(yaw_with_offset),
                }
            )
    return specs


def filter_rows(rows: List[Dict[str, Any]], policy: str, max_decisions: int) -> List[Dict[str, Any]]:
    selected = [
        row
        for row in rows
        if str(row.get("policy")) == policy
        and finite_vector(row.get("viewpoint_position"), 3)
        and finite_vector(row.get("viewpoint_rotation"), 4)
    ]
    if max_decisions > 0:
        selected = selected[:max_decisions]
    return selected


def render_rows(args: argparse.Namespace) -> Dict[str, Any]:
    data_root = Path(args.data_root)
    out_root = Path(args.out_root)
    frames_root = out_root / "frames"
    viewpoint_rows = filter_rows(load_jsonl(Path(args.viewpoint_decisions)), args.policy, int(args.max_decisions))
    candidate_rows = artifact_index(Path(args.candidate_artifact))

    output_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    sim = None
    active_scene_id = None
    active_scene_path = None

    try:
        import habitat_sim

        for row_index, row in enumerate(viewpoint_rows):
            scene_id = str(row.get("scene_id"))
            query = str(row.get("query"))
            if active_scene_id != scene_id:
                if sim is not None:
                    sim.close()
                active_scene_id = scene_id
                active_scene_path = scene_path(data_root, scene_id)
                sim = make_sim(active_scene_path, args.width, args.height, args.camera_height, args.hfov)

            assert sim is not None
            all_candidates = candidate_rows.get((scene_id, query), [])
            frame_candidate_id = str(row.get("candidate_id")) if row.get("candidate_id") is not None else None
            selected_candidates, candidate_set_rule = select_candidate_set_for_row(
                row,
                all_candidates,
                frame_candidate_id,
                float(args.semantic_tie_band),
                int(args.max_candidates_per_decision),
            )
            base_position = np.asarray(row["viewpoint_position"], dtype=np.float64)
            heading_specs = build_heading_specs(
                row,
                selected_candidates,
                base_position,
                args.yaw_offsets,
                float(args.dedupe_degrees),
                bool(args.include_stored_heading),
                str(args.candidate_point_field),
                float(args.grounded_point_height_m),
                float(args.grounded_point_max_vertical_gap_m),
            )

            did = decision_id(row)
            rendered_headings: List[Dict[str, Any]] = []
            for heading_index, spec in enumerate(heading_specs):
                heading_id = f"h{heading_index:03d}"
                rotation = spec["rotation"]
                state = habitat_sim.AgentState()
                state.position = base_position
                state.rotation = rotation
                agent = sim.initialize_agent(0)
                agent.set_state(state, reset_sensors=True)
                obs = sim.get_sensor_observations()

                rgb = np.asarray(obs["color"])
                if rgb.ndim == 3 and rgb.shape[-1] == 4:
                    rgb = rgb[:, :, :3]
                rgb = np.asarray(rgb, dtype=np.uint8)
                depth = np.asarray(obs["depth"], dtype=np.float32)
                if depth.ndim == 3:
                    depth = depth[:, :, 0]

                heading_dir = frames_root / did / heading_id
                heading_dir.mkdir(parents=True, exist_ok=True)
                rgb_rel = Path("frames") / did / heading_id / "rgb.png"
                depth_rel = Path("frames") / did / heading_id / "depth.npy"
                pose_rel = Path("frames") / did / heading_id / "pose.txt"
                metadata_rel = Path("frames") / did / heading_id / "metadata.json"

                Image.fromarray(rgb).save(out_root / rgb_rel)
                np.save(out_root / depth_rel, depth)
                write_pose(out_root / pose_rel, base_position, rotation)
                camera_pose = vlmaps_camera_pose(base_position, rotation, args.camera_height)
                metadata = {
                    "schema_version": SCHEMA_VERSION,
                    "decision_id": did,
                    "heading_id": heading_id,
                    "source_viewpoint_index": row_index,
                    "scene_path": str(active_scene_path),
                    "camera_height": float(args.camera_height),
                    "camera_resolution": [int(args.height), int(args.width)],
                    "camera_hfov": float(args.hfov),
                    "vlmaps_camera_pose": camera_pose.tolist(),
                    "physical_viewpoint_position": [float(value) for value in base_position],
                    "target_candidate_id": spec.get("target_candidate_id"),
                    "rotation_source": spec.get("rotation_source"),
                    "yaw_offset_deg": spec.get("yaw_offset_deg"),
                    "yaw_rad": spec.get("yaw_rad"),
                    "rotation_xyzw": quaternion_xyzw(rotation),
                    "uses_gt_for_action": False,
                }
                (out_root / metadata_rel).write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

                rendered_headings.append(
                    {
                        "heading_id": heading_id,
                        "target_candidate_id": spec.get("target_candidate_id"),
                        "rotation_source": spec.get("rotation_source"),
                        "yaw_offset_deg": spec.get("yaw_offset_deg"),
                        "yaw_rad": spec.get("yaw_rad"),
                        "rgb": str(rgb_rel),
                        "depth": str(depth_rel),
                        "pose": str(pose_rel),
                        "metadata": str(metadata_rel),
                    }
                )

            output_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "decision_id": did,
                    "run_id": row.get("run_id"),
                    "episode_id": row.get("episode_id"),
                    "episode_key": row.get("episode_key"),
                    "policy": row.get("policy"),
                    "scene_id": scene_id,
                    "query": query,
                    "candidate_id": row.get("candidate_id"),
                    "viewpoint_id": row.get("viewpoint_id"),
                    "physical_viewpoint_position": [float(value) for value in base_position],
                    "physical_viewpoint_source": row.get("viewpoint_policy") or "EvidenceGatedSemanticOnly",
                    "candidate_set_rule": candidate_set_rule,
                    "candidate_ids": [str(c.get("candidate_id")) for c in selected_candidates],
                    "second_observation_reason": row.get("second_observation_reason"),
                    "second_observation_candidate_id": row.get("second_observation_candidate_id"),
                    "second_observation_alt_candidate_id": row.get("second_observation_alt_candidate_id"),
                    "heading_policy": "candidate_bearing_offsets",
                    "yaw_offsets_deg": [float(value) for value in args.yaw_offsets],
                    "rendered_headings": rendered_headings,
                    "uses_gt_for_action": False,
                    **passthrough_fields(row),
                }
            )
    except Exception as exc:
        errors.append({"error": repr(exc), "scene_id": active_scene_id})
        raise
    finally:
        if sim is not None:
            sim.close()

    out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_root / "postview_frames_v2.jsonl", output_rows)
    if any(row.get("rival_identity_request_id") is not None for row in output_rows):
        write_jsonl(out_root / "rival_identity_frame_summary.jsonl", output_rows)
    heading_counts = [len(row.get("rendered_headings", [])) for row in output_rows]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "ok": len(errors) == 0 and len(output_rows) == len(viewpoint_rows),
        "viewpoint_decisions": str(args.viewpoint_decisions),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "policy": args.policy,
        "rows_requested": len(viewpoint_rows),
        "rows_exported": len(output_rows),
        "rendered_heading_count": int(sum(heading_counts)),
        "min_headings_per_row": int(min(heading_counts)) if heading_counts else 0,
        "max_headings_per_row": int(max(heading_counts)) if heading_counts else 0,
        "unique_scenes": sorted({str(row.get("scene_id")) for row in output_rows}),
        "width": int(args.width),
        "height": int(args.height),
        "camera_height": float(args.camera_height),
        "hfov": float(args.hfov),
        "candidate_point_field": str(args.candidate_point_field),
        "grounded_point_height_m": float(args.grounded_point_height_m),
        "grounded_point_max_vertical_gap_m": float(args.grounded_point_max_vertical_gap_m),
        "yaw_offsets_deg": [float(value) for value in args.yaw_offsets],
        "uses_gt_for_action": False,
        "errors": errors,
        "next_expected_file": "postview_scores.jsonl",
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render multi-heading post-view RGB-D frames for H001 v2 evidence.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--viewpoint-decisions", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="EvidenceGatedSemanticOnly")
    parser.add_argument("--max-decisions", type=int, default=0)
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-decision", type=int, default=5)
    parser.add_argument("--yaw-offsets", type=parse_float_list, default=[-30.0, 0.0, 30.0])
    parser.add_argument("--dedupe-degrees", type=float, default=10.0)
    parser.add_argument(
        "--candidate-point-field",
        default="position",
        choices=["position", "visit_position", "grounded_position"],
    )
    parser.add_argument("--grounded-point-height-m", type=float, default=DEFAULT_GROUNDED_POINT_HEIGHT_M)
    parser.add_argument(
        "--grounded-point-max-vertical-gap-m",
        type=float,
        default=DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M,
    )
    parser.add_argument("--include-stored-heading", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument("--camera-height", type=float, default=1.5)
    parser.add_argument("--hfov", type=float, default=90.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = render_rows(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
