import gzip
import json
import sys
from pathlib import Path


def count_files(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob(pattern))


def load_episode_count(path: Path) -> int | None:
    if not path.exists():
        return None
    with gzip.open(path, "rt", encoding="utf-8") as f:
        data = json.load(f)
    episodes = data.get("episodes")
    if isinstance(episodes, list):
        return len(episodes)
    return None


def main() -> None:
    data_root = Path(sys.argv[1]).resolve()
    ovon = data_root / "datasets" / "ovon" / "hm3d"

    split_files = {}
    for split in ["train", "val_seen", "val_unseen", "val_seen_synonyms"]:
        split_root = ovon / split
        files = sorted(split_root.rglob("*.json.gz")) if split_root.exists() else []
        content_files = sorted((split_root / "content").glob("*.json.gz")) if (split_root / "content").exists() else []
        split_files[split] = {
            "exists": split_root.exists(),
            "json_gz": len(files),
            "content_json_gz": len(content_files),
            "main_file": str((split_root / f"{split}.json.gz").relative_to(ovon))
            if (split_root / f"{split}.json.gz").exists()
            else None,
            "sample": [str(p.relative_to(ovon)) for p in files[:5]],
            "sample_content_file": str(content_files[0].relative_to(ovon))
            if content_files
            else None,
        }

    sample_episode_counts = {}
    for split, info in split_files.items():
        main_file = info["main_file"]
        if main_file:
            sample_episode_counts[f"{split}_main"] = load_episode_count(ovon / main_file)
        sample_content_file = info["sample_content_file"]
        if sample_content_file:
            sample_episode_counts[f"{split}_content_sample"] = load_episode_count(
                ovon / sample_content_file
            )

    summary = {
        "data_root": str(data_root),
        "ovon_path": str(ovon),
        "ovon_exists": ovon.exists(),
        "total_json_gz": count_files(ovon, "*.json.gz"),
        "splits": split_files,
        "sample_episode_counts": sample_episode_counts,
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    required = [
        summary["ovon_exists"],
        summary["total_json_gz"] > 0,
        split_files["train"]["exists"],
        split_files["val_seen"]["exists"],
        split_files["val_unseen"]["exists"],
        split_files["train"]["content_json_gz"] > 0,
        split_files["val_seen"]["content_json_gz"] > 0,
        split_files["val_unseen"]["content_json_gz"] > 0,
    ]
    if not all(required):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
