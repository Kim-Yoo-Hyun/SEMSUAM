import argparse
import gzip
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.split_manifest.v1"
DEFAULT_SEED = 20260508

SMOKE_SCENES = ["TEEsavR23oF", "wcojb4TFT35"]
CALIBRATION_SCENES = ["HkseAnWCgqk", "vLpv2VX547B", "qk9eeNeR4vw", "oEPjPNSPmzL", "XYyR54sxe6b"]
FIRST_EVAL_SCENES = [
    "TEEsavR23oF",
    "wcojb4TFT35",
    "k1cupFYWXJ6",
    "y9hTuugGdiq",
    "CrMo8WxCyVb",
    "svBbv1Pavdk",
    "p53SfW6mjZe",
    "h1zeeAwLh9Z",
    "mL8ThkuaVTM",
    "eF36g7L6Z9M",
]


def load_json_gz(path: Path) -> Dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True), encoding="utf-8")


def data_path(data_root: Path, dataset: str) -> Path:
    if dataset == "hm3d_objectnav_v2":
        return data_root / "datasets" / "objectnav" / "hm3d" / "v2" / "objectnav_hm3d_v2"
    if dataset == "hm3d_ovon":
        return data_root / "datasets" / "ovon" / "hm3d"
    raise ValueError(f"unsupported dataset: {dataset}")


def scene_token_from_path(path: Path) -> str:
    name = path.name
    for suffix in [".json.gz", ".json", ".gz"]:
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    return name


def source_shard(data_root: Path, dataset: str, split: str, scene_key: str) -> Path:
    return data_path(data_root, dataset) / split / "content" / f"{scene_key}.json.gz"


def source_shard_rel(data_root: Path, path: Path) -> str:
    try:
        return str(path.relative_to(data_root))
    except ValueError:
        return str(path)


def normalize_scene_id(scene_id: str) -> List[str]:
    parts = [part for part in scene_id.split("/") if part]
    if parts and parts[0] in {"hm3d", "hm3d_v0.2"}:
        parts = parts[1:]
    return parts


def scene_asset_path(data_root: Path, scene_id: str) -> Path:
    return data_root / "scene_datasets" / "hm3d" / Path(*normalize_scene_id(scene_id))


def navmesh_path(scene_path: Path) -> Path:
    if scene_path.name.endswith(".basis.glb"):
        return scene_path.with_name(scene_path.name.replace(".basis.glb", ".basis.navmesh"))
    return scene_path.with_suffix(".navmesh")


def target_for_episode(episode: Dict[str, Any]) -> str:
    return str(
        episode.get("object_category")
        or episode.get("object_name")
        or episode.get("goal_name")
        or episode.get("query")
        or "unknown"
    )


def episode_key(benchmark: str, split: str, scene_key: str, row_index: int, episode: Dict[str, Any]) -> str:
    source_episode_id = str(episode.get("episode_id"))
    return f"{benchmark}:{split}:{scene_key}:{row_index}:{source_episode_id}:{target_for_episode(episode)}"


def stable_hash(seed: int, key: str) -> str:
    return hashlib.sha256(f"{seed}:{key}".encode("utf-8")).hexdigest()


def row_from_episode(
    *,
    data_root: Path,
    benchmark: str,
    dataset: str,
    source_split: str,
    selected_split: str,
    scene_key: str,
    source_file: Path,
    row_index: int,
    episode: Dict[str, Any],
    seed: int,
    selection_rank: int,
) -> Dict[str, Any]:
    key = episode_key(benchmark, source_split, scene_key, row_index, episode)
    return {
        "manifest_schema_version": SCHEMA_VERSION,
        "benchmark": benchmark,
        "dataset": dataset,
        "source_split": source_split,
        "selected_split": selected_split,
        "scene_key": scene_key,
        "scene_id": episode.get("scene_id"),
        "source_file": source_shard_rel(data_root, source_file),
        "row_index": int(row_index),
        "source_episode_id": str(episode.get("episode_id")),
        "target_or_query": target_for_episode(episode),
        "episode_key": key,
        "deterministic_hash": stable_hash(seed, key),
        "selection_seed": int(seed),
        "selection_rank": int(selection_rank),
        "start_position": episode.get("start_position"),
        "start_rotation": episode.get("start_rotation"),
        "geodesic_distance": episode.get("info", {}).get("geodesic_distance"),
    }


def round_robin_select(rows: Sequence[Tuple[int, Dict[str, Any], str]], quota: int, seed: int) -> List[Tuple[int, Dict[str, Any]]]:
    groups: Dict[str, List[Tuple[int, Dict[str, Any], str]]] = defaultdict(list)
    for row in rows:
        groups[row[2]].append(row)

    for key, values in groups.items():
        values.sort(key=lambda item: stable_hash(seed, item[2] + ":" + str(item[0]) + ":" + str(item[1].get("episode_id"))))

    selected: List[Tuple[int, Dict[str, Any]]] = []
    group_names = sorted(groups)
    while len(selected) < quota and group_names:
        next_group_names: List[str] = []
        for group_name in group_names:
            values = groups[group_name]
            if values and len(selected) < quota:
                row_index, episode, _target = values.pop(0)
                selected.append((row_index, episode))
            if values:
                next_group_names.append(group_name)
        group_names = next_group_names
    return selected


def select_scene_rows(
    *,
    data_root: Path,
    benchmark: str,
    dataset: str,
    source_split: str,
    selected_split: str,
    scene_key: str,
    quota: int,
    seed: int,
    start_rank: int,
) -> List[Dict[str, Any]]:
    source_file = source_shard(data_root, dataset, source_split, scene_key)
    if not source_file.exists():
        raise FileNotFoundError(source_file)
    shard = load_json_gz(source_file)
    raw_rows = [
        (idx, episode, target_for_episode(episode))
        for idx, episode in enumerate(shard.get("episodes", []))
    ]
    selected = round_robin_select(raw_rows, quota, seed)
    return [
        row_from_episode(
            data_root=data_root,
            benchmark=benchmark,
            dataset=dataset,
            source_split=source_split,
            selected_split=selected_split,
            scene_key=scene_key,
            source_file=source_file,
            row_index=row_index,
            episode=episode,
            seed=seed,
            selection_rank=start_rank + offset,
        )
        for offset, (row_index, episode) in enumerate(selected)
    ]


def scene_quota(total: int, scene_count: int) -> List[int]:
    base = total // scene_count
    extra = total % scene_count
    return [base + (1 if idx < extra else 0) for idx in range(scene_count)]


def select_split(
    *,
    data_root: Path,
    benchmark: str,
    dataset: str,
    source_split: str,
    selected_split: str,
    scene_keys: Sequence[str],
    total_episodes: int,
    seed: int,
) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    rank = 0
    for scene_key, quota in zip(scene_keys, scene_quota(total_episodes, len(scene_keys))):
        scene_rows = select_scene_rows(
            data_root=data_root,
            benchmark=benchmark,
            dataset=dataset,
            source_split=source_split,
            selected_split=selected_split,
            scene_key=scene_key,
            quota=quota,
            seed=seed,
            start_rank=rank,
        )
        selected.extend(scene_rows)
        rank += len(scene_rows)
    return selected


def build_manifest(
    data_root: Path,
    seed: int,
    creation_command: str,
    calibration_scenes: Optional[Sequence[str]] = None,
) -> Dict[str, Any]:
    calibration_scene_keys = list(calibration_scenes or CALIBRATION_SCENES)
    rows: List[Dict[str, Any]] = []
    rows.extend(
        select_split(
            data_root=data_root,
            benchmark="HM3D ObjectNav v2",
            dataset="hm3d_objectnav_v2",
            source_split="val_mini",
            selected_split="smoke",
            scene_keys=SMOKE_SCENES,
            total_episodes=10,
            seed=seed,
        )
    )
    rows.extend(
        select_split(
            data_root=data_root,
            benchmark="HM3D ObjectNav v2",
            dataset="hm3d_objectnav_v2",
            source_split="train",
            selected_split="calibration",
            scene_keys=calibration_scene_keys,
            total_episodes=50,
            seed=seed,
        )
    )
    first_eval = select_split(
        data_root=data_root,
        benchmark="HM3D ObjectNav v2",
        dataset="hm3d_objectnav_v2",
        source_split="val",
        selected_split="first_eval",
        scene_keys=FIRST_EVAL_SCENES,
        total_episodes=100,
        seed=seed,
    )
    rows.extend(first_eval)
    for split_name, source_split in [
        ("ovon_seen", "val_seen"),
        ("ovon_unseen", "val_unseen"),
        ("ovon_synonyms", "val_seen_synonyms"),
    ]:
        rows.extend(
            select_split(
                data_root=data_root,
                benchmark="HM3D-OVON",
                dataset="hm3d_ovon",
                source_split=source_split,
                selected_split=split_name,
                scene_keys=FIRST_EVAL_SCENES,
                total_episodes=100,
                seed=seed,
            )
        )

    split_counts: Dict[str, int] = defaultdict(int)
    scene_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        split_counts[row["selected_split"]] += 1
        scene_counts[row["selected_split"]][row["scene_key"]] += 1

    return {
        "manifest_schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "selection_seed": int(seed),
        "creation_command": creation_command,
        "source_data_root": str(data_root),
        "split_counts": dict(sorted(split_counts.items())),
        "scene_counts": {split: dict(sorted(counts.items())) for split, counts in sorted(scene_counts.items())},
        "rows": rows,
    }


def verify_manifest(manifest: Dict[str, Any], data_root: Path, sim_scene_limit: int = 0) -> Dict[str, Any]:
    rows = list(manifest.get("rows", []))
    seen_keys = set()
    duplicates = []
    split_counts: Dict[str, int] = defaultdict(int)
    source_cache: Dict[Path, Dict[str, Any]] = {}
    scene_paths = []
    errors = []

    for row in rows:
        key = row.get("episode_key")
        if key in seen_keys:
            duplicates.append(key)
        seen_keys.add(key)
        split_counts[str(row.get("selected_split"))] += 1

        source = data_root / str(row.get("source_file"))
        if source not in source_cache:
            if not source.exists():
                errors.append(f"missing source file: {source}")
                continue
            source_cache[source] = load_json_gz(source)
        episodes = source_cache[source].get("episodes", [])
        row_index = int(row.get("row_index"))
        if row_index < 0 or row_index >= len(episodes):
            errors.append(f"row index out of range: {source}:{row_index}")
            continue
        episode = episodes[row_index]
        if str(episode.get("episode_id")) != str(row.get("source_episode_id")):
            errors.append(f"episode_id mismatch: {row.get('episode_key')}")
        if target_for_episode(episode) != row.get("target_or_query"):
            errors.append(f"target mismatch: {row.get('episode_key')}")

        scene = scene_asset_path(data_root, str(episode.get("scene_id")))
        navmesh = navmesh_path(scene)
        if not scene.exists():
            errors.append(f"missing scene asset: {scene}")
        if not navmesh.exists():
            errors.append(f"missing navmesh: {navmesh}")
        if scene.exists() and scene not in scene_paths:
            scene_paths.append(scene)

    calibration_keys = {row["episode_key"] for row in rows if row.get("selected_split") == "calibration"}
    first_eval_keys = {row["episode_key"] for row in rows if row.get("selected_split") == "first_eval"}
    overlap = sorted(calibration_keys & first_eval_keys)
    if overlap:
        errors.append(f"calibration/first_eval overlap: {len(overlap)}")

    sim_checks = []
    if sim_scene_limit > 0:
        sim_checks = verify_sim_scenes(scene_paths[:sim_scene_limit])

    ok = not errors and not duplicates and all(check["ok"] for check in sim_checks)
    return {
        "ok": ok,
        "manifest_schema_version": manifest.get("manifest_schema_version"),
        "rows": len(rows),
        "split_counts": dict(sorted(split_counts.items())),
        "unique_episode_keys": len(seen_keys),
        "duplicate_episode_keys": duplicates[:20],
        "source_files_loaded": len(source_cache),
        "scene_assets_checked": len(scene_paths),
        "sim_scene_checks": sim_checks,
        "errors": errors[:50],
    }


def verify_sim_scenes(scene_paths: Sequence[Path]) -> List[Dict[str, Any]]:
    import habitat_sim

    checks = []
    for scene in scene_paths:
        sim = None
        try:
            sim_cfg = habitat_sim.SimulatorConfiguration()
            sim_cfg.scene_id = str(scene)
            sim_cfg.enable_physics = False
            agent_cfg = habitat_sim.agent.AgentConfiguration()
            agent_cfg.sensor_specifications = []
            sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
            navmesh = navmesh_path(scene)
            if navmesh.exists() and not sim.pathfinder.is_loaded:
                sim.pathfinder.load_nav_mesh(str(navmesh))
            point = sim.pathfinder.get_random_navigable_point()
            checks.append(
                {
                    "scene": str(scene),
                    "ok": bool(sim.pathfinder.is_loaded),
                    "navmesh": str(navmesh),
                    "sample_navigable_point": [float(value) for value in point],
                }
            )
        except Exception as exc:
            checks.append({"scene": str(scene), "ok": False, "error": repr(exc)})
        finally:
            if sim is not None:
                sim.close()
    return checks


def generate_command(args: argparse.Namespace) -> None:
    command = "python -m h001_runtime.split_manifest generate"
    manifest = build_manifest(
        Path(args.data_root).resolve(),
        int(args.seed),
        command,
        calibration_scenes=args.calibration_scenes,
    )
    out = Path(args.out)
    write_json(out, manifest)
    summary = verify_manifest(manifest, Path(args.data_root).resolve(), sim_scene_limit=0)
    print(json.dumps({"out": str(out), "summary": summary}, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


def verify_command(args: argparse.Namespace) -> None:
    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    summary = verify_manifest(manifest, Path(args.data_root).resolve(), sim_scene_limit=int(args.sim_scene_limit))
    out = Path(args.out) if args.out else manifest_path.with_suffix(".verify.json")
    write_json(out, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or verify H001 fixed split manifests.")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate")
    gen.add_argument("--data-root", default="/data")
    gen.add_argument("--out", required=True)
    gen.add_argument("--seed", type=int, default=DEFAULT_SEED)
    gen.add_argument("--calibration-scenes", nargs="+", default=None)
    gen.set_defaults(func=generate_command)

    verify = sub.add_parser("verify")
    verify.add_argument("--data-root", default="/data")
    verify.add_argument("--manifest", required=True)
    verify.add_argument("--out", default=None)
    verify.add_argument("--sim-scene-limit", type=int, default=0)
    verify.set_defaults(func=verify_command)

    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
