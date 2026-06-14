import argparse
import json
from pathlib import Path
from typing import Any, Dict

import numpy as np


def count_files(path: Path) -> int:
    return len([p for p in path.iterdir() if p.is_file()]) if path.exists() else 0


def array_summary(path: Path) -> Dict[str, Any]:
    arr = np.load(path, mmap_mode="r")
    return {
        "path": str(path),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "finite_sample": bool(np.isfinite(arr.reshape(-1)[: min(arr.size, 1024)]).all()),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene-dir", required=True)
    args = parser.parse_args()

    scene_dir = Path(args.scene_dir)
    map_dir = scene_dir / "map"
    alignment_path = scene_dir / "alignment.json"
    required_map_files = {
        "grid": map_dir / "grid_lseg_1.npy",
        "weight": map_dir / "weight_lseg_1.npy",
        "obstacles": map_dir / "obstacles.npy",
    }

    if not alignment_path.exists():
        raise FileNotFoundError(alignment_path)
    alignment = json.loads(alignment_path.read_text(encoding="utf-8"))

    counts = {name: count_files(scene_dir / name) for name in ("rgb", "depth", "pose", "semantic")}
    missing = [str(path) for path in required_map_files.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing map files: {missing}")

    summaries = {name: array_summary(path) for name, path in required_map_files.items()}
    weight = np.load(required_map_files["weight"], mmap_mode="r")
    obstacles = np.load(required_map_files["obstacles"], mmap_mode="r")
    summary = {
        "ok": True,
        "scene_dir": str(scene_dir),
        "counts": counts,
        "uses_gt_for_action": bool(alignment.get("uses_gt_for_action")),
        "alignment_source": alignment.get("alignment_source"),
        "coordinate_frame": alignment.get("coordinate_frame"),
        "map_summaries": summaries,
        "weight_nonzero": int(np.count_nonzero(weight)),
        "obstacle_free_cells": int(np.count_nonzero(obstacles == 0)),
    }

    if summary["uses_gt_for_action"]:
        raise RuntimeError("alignment uses GT for action")
    if len(set(counts.values())) != 1 or not counts:
        raise RuntimeError(f"frame counts are inconsistent: {counts}")

    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
