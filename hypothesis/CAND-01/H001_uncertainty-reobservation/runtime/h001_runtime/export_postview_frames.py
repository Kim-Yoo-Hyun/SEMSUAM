import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from PIL import Image

from h001_runtime.export_hm3d_vlmaps import (
    make_sim,
    scene_path,
    vlmaps_camera_pose,
    write_pose,
)


SCHEMA_VERSION = "h001.postview.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def decision_id(row: Dict[str, Any]) -> str:
    key = "|".join(
        [
            str(row.get("run_id")),
            str(row.get("episode_key") or row.get("episode_id")),
            str(row.get("policy")),
            str(row.get("viewpoint_id")),
            str(row.get("candidate_id")),
        ]
    )
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]
    scene = Path(str(row.get("scene_id") or "scene")).name.replace(".basis.glb", "").replace(".glb", "")
    query = str(row.get("query") or "query").replace("/", "-")
    return f"{scene}_{query}_{digest}"


def quaternion_from_xyzw(values: Any) -> Any:
    import quaternion

    if not isinstance(values, list) or len(values) != 4:
        return quaternion.quaternion(1.0, 0.0, 0.0, 0.0)
    x, y, z, w = [float(value) for value in values]
    return quaternion.quaternion(w, x, y, z)


def finite_vector(values: Any, length: int) -> bool:
    if not isinstance(values, list) or len(values) != length:
        return False
    try:
        arr = np.asarray(values, dtype=np.float64)
    except Exception:
        return False
    return bool(np.all(np.isfinite(arr)))


def load_candidate_ids(path: Optional[Path]) -> set[str]:
    if path is None or not path.exists():
        return set()
    ids: set[str] = set()
    for row in load_jsonl(path):
        for candidate in row.get("candidates") or []:
            candidate_id = candidate.get("candidate_id")
            if candidate_id is not None:
                ids.add(str(candidate_id))
    return ids


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
    candidate_ids = load_candidate_ids(Path(args.candidate_artifact) if args.candidate_artifact else None)

    output_rows: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    sim = None
    active_scene_id = None
    active_scene_path = None

    try:
        import habitat_sim

        for index, row in enumerate(viewpoint_rows):
            scene_id = str(row.get("scene_id"))
            if active_scene_id != scene_id:
                if sim is not None:
                    sim.close()
                active_scene_id = scene_id
                active_scene_path = scene_path(data_root, scene_id)
                sim = make_sim(active_scene_path, args.width, args.height, args.camera_height, args.hfov)

            assert sim is not None
            base_position = np.asarray(row["viewpoint_position"], dtype=np.float64)
            base_rotation = quaternion_from_xyzw(row.get("viewpoint_rotation"))
            state = habitat_sim.AgentState()
            state.position = base_position
            state.rotation = base_rotation
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

            did = decision_id(row)
            frame_dir = frames_root / did
            frame_dir.mkdir(parents=True, exist_ok=True)
            rgb_rel = Path("frames") / did / "rgb.png"
            depth_rel = Path("frames") / did / "depth.npy"
            pose_rel = Path("frames") / did / "pose.txt"
            metadata_rel = Path("frames") / did / "metadata.json"

            Image.fromarray(rgb).save(out_root / rgb_rel)
            np.save(out_root / depth_rel, depth)
            write_pose(out_root / pose_rel, base_position, base_rotation)
            camera_pose = vlmaps_camera_pose(base_position, base_rotation, args.camera_height)

            metadata = {
                "schema_version": SCHEMA_VERSION,
                "decision_id": did,
                "source_viewpoint_index": index,
                "source_viewpoint_row": row,
                "scene_path": str(active_scene_path),
                "camera_height": float(args.camera_height),
                "camera_resolution": [int(args.height), int(args.width)],
                "camera_hfov": float(args.hfov),
                "vlmaps_camera_pose": camera_pose.tolist(),
                "candidate_id_exists_in_artifact": str(row.get("candidate_id")) in candidate_ids if candidate_ids else None,
                "uses_gt_for_action": False,
            }
            (out_root / metadata_rel).write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")

            output_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "decision_id": did,
                    "run_id": row.get("run_id"),
                    "episode_id": row.get("episode_id"),
                    "episode_key": row.get("episode_key"),
                    "policy": row.get("policy"),
                    "scene_id": scene_id,
                    "query": row.get("query"),
                    "candidate_id": row.get("candidate_id"),
                    "viewpoint_id": row.get("viewpoint_id"),
                    "viewpoint_position": [float(value) for value in base_position],
                    "viewpoint_rotation": row.get("viewpoint_rotation"),
                    "rgb": str(rgb_rel),
                    "depth": str(depth_rel),
                    "pose": str(pose_rel),
                    "metadata": str(metadata_rel),
                    "uses_gt_for_action": False,
                }
            )
    except Exception as exc:
        errors.append({"error": repr(exc), "scene_id": active_scene_id})
        raise
    finally:
        if sim is not None:
            sim.close()

    write_jsonl(out_root / "postview_frames.jsonl", output_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "ok": len(errors) == 0 and len(output_rows) == len(viewpoint_rows),
        "viewpoint_decisions": str(args.viewpoint_decisions),
        "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
        "out_root": str(out_root),
        "policy": args.policy,
        "rows_requested": len(viewpoint_rows),
        "rows_exported": len(output_rows),
        "unique_scenes": sorted({str(row.get("scene_id")) for row in output_rows}),
        "width": int(args.width),
        "height": int(args.height),
        "camera_height": float(args.camera_height),
        "hfov": float(args.hfov),
        "uses_gt_for_action": False,
        "errors": errors,
        "next_expected_file": "postview_scores.jsonl",
    }
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render post-view RGB-D frames for H001 re-observation decisions.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--viewpoint-decisions", required=True)
    parser.add_argument("--candidate-artifact", default=None)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="EvidenceGatedSemanticOnly")
    parser.add_argument("--max-decisions", type=int, default=0)
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
