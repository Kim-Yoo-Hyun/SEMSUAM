import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from h001_runtime.align_vlmaps_artifact import HabitatSnapper, align_artifact


def scene_path(data_root: Path, scene_id: str) -> Path:
    return data_root / "scene_datasets" / "hm3d" / scene_id


def sample_connected_points(scene: Path, seed: int) -> Tuple[List[float], List[float], float]:
    snapper = HabitatSnapper(scene)
    try:
        sim = snapper._sim
        sim.seed(seed)
        for _ in range(100):
            start = [float(v) for v in sim.pathfinder.get_random_navigable_point()]
            target = [float(v) for v in sim.pathfinder.get_random_navigable_point()]
            distance = snapper.distance(start, target)
            if distance is not None and distance > 0.0:
                return start, target, distance
    finally:
        snapper.close()
    raise RuntimeError("failed to sample connected navigable points")


def write_fixture(root: Path, scene_id: str, target: List[float]) -> Tuple[Path, Path]:
    root.mkdir(parents=True, exist_ok=True)
    artifact = root / "vlmaps_grid_fixture.jsonl"
    alignment = root / "alignment.json"

    artifact_row: Dict[str, Any] = {
        "scene_id": scene_id,
        "query": "chair",
        "candidates": [
            {
                "candidate_id": "vlmaps:alignment-smoke:chair:0",
                "category": "chair",
                "position": [500.0, 0.0, 500.0],
                "visit_position": [500.0, 0.0, 500.0],
                "score": 0.9,
                "view_count": 4,
                "backend_source": "alignment_smoke_fixture",
            }
        ],
        "metadata": {
            "backend": "vlmaps_feature_grid",
            "coordinate_frame": "vlmaps_grid",
            "uses_gt_for_action": False,
        },
    }
    artifact.write_text(json.dumps(artifact_row, sort_keys=True) + "\n", encoding="utf-8")

    alignment_data = {
        "coordinate_frame": "habitat_world",
        "alignment_source": "synthetic_habitat_navmesh_smoke",
        "alignment_id": "h001_vlmaps_alignment_smoke",
        "uses_gt_for_action": False,
        "vlmaps_commit": "bc79b26a577e5a9408f86e45e5c16530ca80f867",
        "grid_size": 1000,
        "cell_size": 0.05,
        "grid_origin_cell": [500.0, 500.0],
        "axis_mapping": {"grid_col": "local +x", "grid_row": "local -z"},
        "world_from_vlmaps_origin": [
            [1.0, 0.0, 0.0, target[0]],
            [0.0, 1.0, 0.0, target[1]],
            [0.0, 0.0, 1.0, target[2]],
            [0.0, 0.0, 0.0, 1.0],
        ],
        "y_strategy": "snap_to_habitat_navmesh",
    }
    alignment.write_text(json.dumps(alignment_data, indent=2, sort_keys=True), encoding="utf-8")
    return artifact, alignment


def load_first_candidate(path: Path) -> Dict[str, Any]:
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    return row["candidates"][0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test VLMaps grid to Habitat alignment and navigability.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--scene-id", default="val/00800-TEEsavR23oF/TEEsavR23oF.basis.glb")
    parser.add_argument("--out-dir", default="/runs/vlmaps_alignment_smoke")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    data_root = Path(args.data_root)
    scene = scene_path(data_root, args.scene_id)
    out_dir = Path(args.out_dir)
    start, target, reference_distance = sample_connected_points(scene, args.seed)
    artifact, alignment = write_fixture(out_dir, args.scene_id, target)
    aligned = out_dir / "aligned_artifact.jsonl"
    align_artifact(artifact, alignment, aligned, scene=scene)

    candidate = load_first_candidate(aligned)
    snapper = HabitatSnapper(scene)
    try:
        distance = snapper.distance(start, candidate["visit_position"])
    finally:
        snapper.close()

    ok = distance is not None and candidate.get("visit_position_navigable") is True
    summary = {
        "ok": ok,
        "scene": str(scene),
        "artifact": str(artifact),
        "alignment": str(alignment),
        "aligned_artifact": str(aligned),
        "start_position": start,
        "target_position": target,
        "candidate_position": candidate["position"],
        "candidate_visit_position": candidate["visit_position"],
        "candidate_visit_position_navigable": candidate.get("visit_position_navigable"),
        "reference_geodesic_distance": reference_distance,
        "candidate_geodesic_distance": distance,
        "coordinate_frame": candidate.get("coordinate_frame"),
        "alignment_source": candidate.get("alignment_source"),
        "uses_gt_for_action": False,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
