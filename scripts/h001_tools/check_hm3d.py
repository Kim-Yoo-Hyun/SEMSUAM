import json
import sys
from pathlib import Path


def count_files(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob(pattern))


def sample_dirs(root: Path, limit: int = 5):
    if not root.exists():
        return []
    return [p.name for p in sorted(root.iterdir()) if p.is_dir()][:limit]


def main() -> None:
    data_root = Path(sys.argv[1]).resolve()
    hm3d = data_root / "scene_datasets" / "hm3d"
    objectnav = data_root / "datasets" / "objectnav" / "hm3d" / "v2"

    summary = {
        "data_root": str(data_root),
        "hm3d_path": str(hm3d),
        "objectnav_hm3d_v2_path": str(objectnav),
        "hm3d_exists": hm3d.exists(),
        "objectnav_exists": objectnav.exists(),
        "scene_dataset_configs": {
            "hm3d_basis": (hm3d / "hm3d_basis.scene_dataset_config.json").exists(),
            "hm3d_annotated_basis": (
                hm3d / "hm3d_annotated_basis.scene_dataset_config.json"
            ).exists(),
        },
        "splits": {},
        "objectnav_files": {
            "json_gz": count_files(objectnav, "*.json.gz"),
            "json": count_files(objectnav, "*.json"),
            "sample": [str(p.relative_to(objectnav)) for p in sorted(objectnav.rglob("*")) if p.is_file()][:10]
            if objectnav.exists()
            else [],
        },
    }

    for split in ["train", "val", "minival"]:
        split_root = hm3d / split
        summary["splits"][split] = {
            "exists": split_root.exists(),
            "scene_dirs_sample": sample_dirs(split_root),
            "basis_glb_count": count_files(split_root, "*.basis.glb"),
            "basis_navmesh_count": count_files(split_root, "*.basis.navmesh"),
            "semantic_glb_count": count_files(split_root, "*.semantic.glb"),
            "semantic_txt_count": count_files(split_root, "*.semantic.txt"),
        }

    print(json.dumps(summary, indent=2, sort_keys=True))

    required = [
        summary["hm3d_exists"],
        summary["objectnav_exists"],
        summary["scene_dataset_configs"]["hm3d_annotated_basis"],
        summary["splits"]["val"]["basis_glb_count"] > 0,
        summary["splits"]["val"]["semantic_glb_count"] > 0,
        summary["objectnav_files"]["json_gz"] > 0,
    ]
    if not all(required):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
