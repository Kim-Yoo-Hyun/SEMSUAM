import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from PIL import Image


VLMAPS_COMMIT = "bc79b26a577e5a9408f86e45e5c16530ca80f867"
ROT_RO_CAM = np.diag([1.0, -1.0, -1.0]).astype(np.float64)


def normalize_scene_id(scene_id: str) -> str:
    parts = [part for part in scene_id.split("/") if part]
    if parts and parts[0] in {"hm3d", "hm3d_v0.2"}:
        parts = parts[1:]
    return "/".join(parts)


def scene_path(data_root: Path, scene_id: str) -> Path:
    return data_root / "scene_datasets" / "hm3d" / normalize_scene_id(scene_id)


def navmesh_path(scene: Path) -> Path:
    if scene.name.endswith(".basis.glb"):
        return scene.with_name(scene.name.replace(".basis.glb", ".basis.navmesh"))
    return scene.with_suffix(".navmesh")


def scene_key(scene_id: str) -> str:
    name = Path(normalize_scene_id(scene_id)).name
    return name.replace(".basis.glb", "").replace(".glb", "")


def ensure_dirs(out_dir: Path) -> None:
    for name in ("rgb", "depth", "pose", "semantic"):
        (out_dir / name).mkdir(parents=True, exist_ok=True)


def quaternion_from_yaw(yaw: float) -> Any:
    import quaternion

    return quaternion.from_rotation_vector(np.array([0.0, yaw, 0.0], dtype=np.float64))


def quaternion_xyzw(q: Any) -> List[float]:
    return [float(q.x), float(q.y), float(q.z), float(q.w)]


def rotation_matrix(q: Any) -> np.ndarray:
    import quaternion

    return np.asarray(quaternion.as_rotation_matrix(q), dtype=np.float64)


def vlmaps_camera_pose(base_position: np.ndarray, base_rotation: Any, camera_height: float) -> np.ndarray:
    pose = np.eye(4, dtype=np.float64)
    pose[:3, :3] = rotation_matrix(base_rotation) @ ROT_RO_CAM
    pose[:3, 3] = np.asarray(base_position, dtype=np.float64)
    pose[1, 3] += float(camera_height)
    return pose


def finite_matrix(matrix: np.ndarray) -> bool:
    return matrix.shape == (4, 4) and bool(np.all(np.isfinite(matrix)))


def make_sim(scene: Path, width: int, height: int, camera_height: float, hfov: float) -> Any:
    import habitat_sim

    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = str(scene)
    sim_cfg.enable_physics = False

    color = habitat_sim.CameraSensorSpec()
    color.uuid = "color"
    color.sensor_type = habitat_sim.SensorType.COLOR
    color.resolution = [height, width]
    color.position = [0.0, camera_height, 0.0]
    color.hfov = hfov

    depth = habitat_sim.CameraSensorSpec()
    depth.uuid = "depth"
    depth.sensor_type = habitat_sim.SensorType.DEPTH
    depth.resolution = [height, width]
    depth.position = [0.0, camera_height, 0.0]
    depth.hfov = hfov

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = [color, depth]

    sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
    navmesh = navmesh_path(scene)
    if navmesh.exists() and not sim.pathfinder.is_loaded:
        sim.pathfinder.load_nav_mesh(str(navmesh))
    if not sim.pathfinder.is_loaded:
        sim.close()
        raise RuntimeError(f"navmesh is not loaded for scene: {scene}")
    return sim


def sample_random_base_poses(sim: Any, frames: int, seed: int) -> List[Tuple[np.ndarray, Any, float, Dict[str, Any]]]:
    sim.seed(seed)
    poses: List[Tuple[np.ndarray, Any, float, Dict[str, Any]]] = []
    for idx in range(frames):
        point = np.asarray(sim.pathfinder.get_random_navigable_point(), dtype=np.float64)
        yaw = (2.0 * math.pi * idx) / max(1, frames)
        poses.append((point, quaternion_from_yaw(yaw), yaw, {"sample_source": "random"}))
    return poses


def load_manifest_anchor_rows(args: argparse.Namespace, key: str) -> List[Dict[str, Any]]:
    if not args.manifest:
        raise ValueError("--manifest is required for trajectory-mode=manifest_starts")
    data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    rows: List[Dict[str, Any]] = []
    for row in data.get("rows", []):
        if str(row.get("selected_split")) != str(args.manifest_split):
            continue
        if str(row.get("scene_key")) != key:
            continue
        position = row.get("start_position")
        if not isinstance(position, list) or len(position) != 3:
            continue
        y = float(position[1])
        if args.anchor_y_min is not None and y < args.anchor_y_min:
            continue
        if args.anchor_y_max is not None and y > args.anchor_y_max:
            continue
        rows.append(row)
    rows.sort(key=lambda row: int(row.get("selection_rank", row.get("row_index", 0))))
    if args.max_anchors > 0:
        rows = rows[: args.max_anchors]
    if not rows:
        raise ValueError(f"no manifest anchor rows for split={args.manifest_split}, scene_key={key}")
    return rows


def sample_manifest_start_poses(
    sim: Any,
    args: argparse.Namespace,
    key: str,
) -> List[Tuple[np.ndarray, Any, float, Dict[str, Any]]]:
    rows = load_manifest_anchor_rows(args, key)
    poses: List[Tuple[np.ndarray, Any, float, Dict[str, Any]]] = []
    frames_per_anchor = max(1, int(args.frames_per_anchor))
    for anchor_index, row in enumerate(rows):
        anchor = np.asarray(row["start_position"], dtype=np.float64)
        if args.snap_anchors:
            snapped = np.asarray(sim.pathfinder.snap_point(anchor.astype(np.float32)), dtype=np.float64)
            if np.all(np.isfinite(snapped)):
                anchor = snapped
        for view_index in range(frames_per_anchor):
            if len(poses) >= args.frames:
                return poses
            yaw = (2.0 * math.pi * view_index) / frames_per_anchor
            metadata = {
                "sample_source": "manifest_start",
                "manifest_episode_key": row.get("episode_key"),
                "manifest_selection_rank": row.get("selection_rank"),
                "manifest_row_index": row.get("row_index"),
                "manifest_target_or_query": row.get("target_or_query"),
                "anchor_index": anchor_index,
                "anchor_view_index": view_index,
            }
            poses.append((anchor, quaternion_from_yaw(yaw), yaw, metadata))
    return poses


def sample_base_poses(sim: Any, args: argparse.Namespace, key: str) -> List[Tuple[np.ndarray, Any, float, Dict[str, Any]]]:
    if args.trajectory_mode == "random":
        return sample_random_base_poses(sim, args.frames, args.seed)
    if args.trajectory_mode == "manifest_starts":
        return sample_manifest_start_poses(sim, args, key)
    raise ValueError(f"unsupported trajectory mode: {args.trajectory_mode}")


def write_pose(path: Path, base_position: np.ndarray, base_rotation: Any) -> None:
    quat = quaternion_xyzw(base_rotation)
    values = [float(v) for v in base_position] + quat
    path.write_text("\t".join(f"{value:.9f}" for value in values), encoding="utf-8")


def write_obj2cls(path: Path) -> None:
    # Dummy semantic compatibility file. H001 candidate generation must not use this.
    path.write_text("0: 40, misc\n", encoding="utf-8")


def write_alignment(
    path: Path,
    scene_id: str,
    trajectory_id: str,
    first_camera_pose: np.ndarray,
    grid_size: int,
    cell_size: float,
    camera_height: float,
    width: int,
    height: int,
    hfov: float,
) -> Dict[str, Any]:
    if not finite_matrix(first_camera_pose):
        raise ValueError("first camera pose is not a finite 4x4 matrix")
    alignment = {
        "coordinate_frame": "habitat_world",
        "alignment_source": "hm3d_habitat_preexploration",
        "alignment_id": trajectory_id,
        "uses_gt_for_action": False,
        "scene_id": scene_id,
        "trajectory_id": trajectory_id,
        "vlmaps_commit": VLMAPS_COMMIT,
        "grid_size": int(grid_size),
        "cell_size": float(cell_size),
        "grid_origin_cell": [float(grid_size) / 2.0, float(grid_size) / 2.0],
        "axis_mapping": {
            "grid_col": "vlmaps_local +x",
            "grid_row": "vlmaps_local -z",
        },
        "world_from_vlmaps_origin": first_camera_pose.tolist(),
        "y_strategy": "snap_to_habitat_navmesh",
        "camera_height": float(camera_height),
        "camera_resolution": [int(height), int(width)],
        "camera_hfov": float(hfov),
    }
    path.write_text(json.dumps(alignment, indent=2, sort_keys=True), encoding="utf-8")
    return alignment


def export_scene(args: argparse.Namespace) -> Dict[str, Any]:
    data_root = Path(args.data_root)
    scene_id = args.scene_id
    scene = scene_path(data_root, scene_id)
    if not scene.exists():
        raise FileNotFoundError(f"scene does not exist: {scene}")

    out_dir = Path(args.out_dir)
    ensure_dirs(out_dir)
    prefix = scene_key(scene_id)
    trajectory_id = args.trajectory_id or f"{prefix}_seed{args.seed}_n{args.frames}"

    sim = make_sim(scene, args.width, args.height, args.camera_height, args.hfov)
    agent = sim.initialize_agent(0)
    poses = sample_base_poses(sim, args, prefix)
    frame_rows: List[Dict[str, Any]] = []
    first_camera_pose: Optional[np.ndarray] = None

    try:
        import habitat_sim

        for idx, (base_position, base_rotation, yaw, pose_metadata) in enumerate(poses):
            state = habitat_sim.AgentState()
            state.position = base_position
            state.rotation = base_rotation
            agent.set_state(state, reset_sensors=True)
            obs = sim.get_sensor_observations()

            rgb = np.asarray(obs["color"])
            if rgb.ndim == 3 and rgb.shape[-1] == 4:
                rgb = rgb[:, :, :3]
            rgb = np.asarray(rgb, dtype=np.uint8)
            depth = np.asarray(obs["depth"], dtype=np.float32)
            if depth.ndim == 3:
                depth = depth[:, :, 0]
            semantic = np.zeros(depth.shape, dtype=np.int32)

            stem = f"{prefix}_{idx}"
            Image.fromarray(rgb).save(out_dir / "rgb" / f"{stem}.png")
            np.save(out_dir / "depth" / f"{stem}.npy", depth)
            np.save(out_dir / "semantic" / f"{stem}.npy", semantic)
            write_pose(out_dir / "pose" / f"{stem}.txt", base_position, base_rotation)

            camera_pose = vlmaps_camera_pose(base_position, base_rotation, args.camera_height)
            if first_camera_pose is None:
                first_camera_pose = camera_pose
            frame_rows.append(
                {
                    "frame_index": idx,
                    "rgb": f"rgb/{stem}.png",
                    "depth": f"depth/{stem}.npy",
                    "pose": f"pose/{stem}.txt",
                    "semantic": f"semantic/{stem}.npy",
                    "base_position": [float(v) for v in base_position],
                    "base_rotation_xyzw": quaternion_xyzw(base_rotation),
                    "yaw": float(yaw),
                    "vlmaps_camera_pose": camera_pose.tolist(),
                    "uses_gt_for_action": False,
                    "pose_metadata": pose_metadata,
                }
            )
    finally:
        sim.close()

    if first_camera_pose is None:
        raise RuntimeError("no frames exported")

    write_obj2cls(out_dir / "obj2cls_dict.txt")
    alignment = write_alignment(
        out_dir / "alignment.json",
        scene_id=scene_id,
        trajectory_id=trajectory_id,
        first_camera_pose=first_camera_pose,
        grid_size=args.grid_size,
        cell_size=args.cell_size,
        camera_height=args.camera_height,
        width=args.width,
        height=args.height,
        hfov=args.hfov,
    )
    manifest = {
        "scene_id": scene_id,
        "scene": str(scene),
        "trajectory_id": trajectory_id,
        "frames": frame_rows,
        "frame_count": len(frame_rows),
        "width": int(args.width),
        "height": int(args.height),
        "camera_height": float(args.camera_height),
        "hfov": float(args.hfov),
        "grid_size": int(args.grid_size),
        "cell_size": float(args.cell_size),
        "trajectory_mode": args.trajectory_mode,
        "alignment": "alignment.json",
        "semantic_policy": "dummy_compatibility_only",
        "uses_gt_for_action": False,
    }
    (out_dir / "trajectory_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")

    counts = {
        name: len(list((out_dir / name).glob("*")))
        for name in ("rgb", "depth", "pose", "semantic")
    }
    ok = (
        counts["rgb"] == args.frames
        and counts["depth"] == args.frames
        and counts["pose"] == args.frames
        and counts["semantic"] == args.frames
        and alignment["uses_gt_for_action"] is False
        and finite_matrix(np.asarray(alignment["world_from_vlmaps_origin"], dtype=np.float64))
    )
    summary = {
        "ok": ok,
        "out_dir": str(out_dir),
        "scene_id": scene_id,
        "trajectory_id": trajectory_id,
        "counts": counts,
        "alignment": str(out_dir / "alignment.json"),
        "manifest": str(out_dir / "trajectory_manifest.json"),
        "uses_gt_for_action": False,
        "next_expected_files": [
            "map/grid_lseg_1.npy",
            "map/weight_lseg_1.npy",
            "map/obstacles.npy",
        ],
    }
    (out_dir / "export_summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export HM3D Habitat RGB-D/pose frames in VLMaps-compatible format.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--scene-id", default="val/00800-TEEsavR23oF/TEEsavR23oF.basis.glb")
    parser.add_argument("--out-dir", default="/runs/hm3d_vlmaps_export_smoke")
    parser.add_argument("--frames", type=int, default=6)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--trajectory-mode", default="random", choices=["random", "manifest_starts"])
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--manifest-split", default="smoke")
    parser.add_argument("--frames-per-anchor", type=int, default=4)
    parser.add_argument("--max-anchors", type=int, default=0)
    parser.add_argument("--anchor-y-min", type=float, default=None)
    parser.add_argument("--anchor-y-max", type=float, default=None)
    parser.add_argument("--snap-anchors", action="store_true")
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument("--camera-height", type=float, default=1.5)
    parser.add_argument("--hfov", type=float, default=90.0)
    parser.add_argument("--grid-size", type=int, default=1000)
    parser.add_argument("--cell-size", type=float, default=0.05)
    parser.add_argument("--trajectory-id", default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.frames <= 0:
        raise ValueError("--frames must be positive")
    summary = export_scene(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
