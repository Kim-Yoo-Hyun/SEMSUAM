import json
import os
import subprocess
import zipfile
from pathlib import Path

import gdown
import numpy as np


FILE_ID = "1wjuiVcO92Rqer5gLk-X7hINfe4PCMQmu"
SCENE_NAME = "5LpN3gDmAk7_1"
REPO_DIR = Path("/opt/vlmaps")
DATA_ROOT = Path(os.environ.get("VLMAPS_DATA_DIR", "/datasets/vlmaps"))


def run(cmd):
    return subprocess.check_output(cmd, cwd=REPO_DIR, text=True).strip()


def ensure_demo_data():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    zip_path = DATA_ROOT / f"{SCENE_NAME}.zip"
    scene_dir = DATA_ROOT / SCENE_NAME

    if not zip_path.exists():
        url = f"https://drive.google.com/uc?id={FILE_ID}"
        gdown.download(url, str(zip_path), quiet=False)

    if not scene_dir.exists():
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(DATA_ROOT)

    return scene_dir, zip_path


def array_summary(path):
    arr = np.load(path)
    return {
        "path": str(path),
        "shape": list(arr.shape),
        "dtype": str(arr.dtype),
        "min": float(np.nanmin(arr)) if arr.size else None,
        "max": float(np.nanmax(arr)) if arr.size else None,
    }


def main():
    commit = run(["git", "rev-parse", "HEAD"])
    scene_dir, zip_path = ensure_demo_data()

    required_dirs = ["rgb", "depth", "pose", "semantic", "map_correct"]
    dir_counts = {}
    for name in required_dirs:
        path = scene_dir / name
        if not path.exists():
            raise FileNotFoundError(path)
        dir_counts[name] = len(list(path.iterdir()))

    map_dir = scene_dir / "map_correct"
    map_files = [
        map_dir / "color_top_down_1.npy",
        map_dir / "grid_lseg_1.npy",
        map_dir / "obstacles.npy",
    ]
    summaries = [array_summary(path) for path in map_files]

    result = {
        "status": "ok",
        "repo": "vlmaps/vlmaps",
        "branch": "demo",
        "commit": commit,
        "data_root": str(DATA_ROOT),
        "zip_path": str(zip_path),
        "scene_dir": str(scene_dir),
        "dir_counts": dir_counts,
        "map_summaries": summaries,
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
