import argparse
import json
import os
import sys
from pathlib import Path

import gdown
import torch


VLMAPS_REPO = Path(os.environ.get("VLMAPS_REPO", "/opt/vlmaps"))
DEFAULT_CHECKPOINT_ID = "1ayk6NXURI_vIPlym16f_RG3ffxBWHxvb"
DEFAULT_REPO_CHECKPOINT = VLMAPS_REPO / "lseg" / "checkpoints" / "demo_e200.ckpt"


def ensure_checkpoint(path: Path, file_id: str, download: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        if not download:
            raise FileNotFoundError(f"missing LSeg checkpoint: {path}")
        url = f"https://drive.google.com/uc?id={file_id}"
        gdown.download(url, str(path), quiet=False)
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"checkpoint download failed or empty: {path}")

    DEFAULT_REPO_CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    if DEFAULT_REPO_CHECKPOINT.resolve() != path.resolve():
        if DEFAULT_REPO_CHECKPOINT.exists() or DEFAULT_REPO_CHECKPOINT.is_symlink():
            DEFAULT_REPO_CHECKPOINT.unlink()
        DEFAULT_REPO_CHECKPOINT.symlink_to(path)
    return path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--camera-height", type=float, default=1.5)
    parser.add_argument("--depth-sample-rate", type=int, default=100)
    parser.add_argument("--checkpoint", default=os.environ.get("VLMAPS_CHECKPOINT", str(DEFAULT_REPO_CHECKPOINT)))
    parser.add_argument("--checkpoint-file-id", default=DEFAULT_CHECKPOINT_ID)
    parser.add_argument("--download-checkpoint", action="store_true")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        raise FileNotFoundError(data_dir)
    if not torch.cuda.is_available():
        raise RuntimeError("VLMaps full LSeg map generation requires CUDA for this smoke.")

    checkpoint = ensure_checkpoint(Path(args.checkpoint), args.checkpoint_file_id, args.download_checkpoint)

    sys.path.insert(0, str(VLMAPS_REPO))
    os.chdir(VLMAPS_REPO)
    original_torch_load = torch.load

    def torch_load_compat(*load_args, **load_kwargs):
        load_kwargs.setdefault("weights_only", False)
        return original_torch_load(*load_args, **load_kwargs)

    torch.load = torch_load_compat
    from examples.clip_mapping_lseg_from_scratch_batch import create_lseg_map_batch

    create_lseg_map_batch(
        str(data_dir),
        camera_height=args.camera_height,
        depth_sample_rate=args.depth_sample_rate,
    )

    summary = {
        "status": "completed",
        "data_dir": str(data_dir),
        "checkpoint": str(checkpoint),
        "cuda_device": torch.cuda.get_device_name(0),
        "map_dir": str(data_dir / "map"),
        "expected_files": [
            "map/grid_lseg_1.npy",
            "map/weight_lseg_1.npy",
            "map/obstacles.npy",
        ],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
