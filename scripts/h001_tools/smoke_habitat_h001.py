import argparse
import gzip
import json
from pathlib import Path
from typing import Optional


def count_files(root: Path, pattern: str) -> int:
    if not root.exists():
        return 0
    return sum(1 for _ in root.rglob(pattern))


def load_json_gz(path: Path) -> dict:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)


def first_file(root: Path, pattern: str) -> Optional[Path]:
    if not root.exists():
        return None
    for path in sorted(root.rglob(pattern)):
        if path.is_file():
            return path
    return None


def scene_summary(hm3d: Path) -> dict:
    scene = first_file(hm3d / "val", "*.basis.glb") or first_file(
        hm3d / "minival", "*.basis.glb"
    )
    if scene is None:
        return {"scene_found": False}

    navmesh = scene.with_suffix(".navmesh")
    if scene.name.endswith(".basis.glb"):
        navmesh = scene.with_name(scene.name.replace(".basis.glb", ".basis.navmesh"))

    return {
        "scene_found": True,
        "scene": str(scene),
        "navmesh": str(navmesh),
        "navmesh_exists": navmesh.exists(),
    }


def episode_summary(root: Path) -> dict:
    sample = first_file(root, "content/*.json.gz")
    if sample is None:
        return {"exists": root.exists(), "json_gz": count_files(root, "*.json.gz")}
    data = load_json_gz(sample)
    episodes = data.get("episodes", [])
    first_episode = episodes[0] if episodes else {}
    return {
        "exists": root.exists(),
        "json_gz": count_files(root, "*.json.gz"),
        "sample": str(sample),
        "sample_episode_count": len(episodes),
        "sample_episode_keys": sorted(first_episode.keys())[:40],
        "sample_scene_id": first_episode.get("scene_id"),
        "sample_object_category": first_episode.get("object_category"),
    }


def habitat_sim_smoke(hm3d: Path) -> dict:
    import habitat_sim

    scene_info = scene_summary(hm3d)
    if not scene_info.get("scene_found"):
        return {"ok": False, "reason": "no HM3D basis scene found"}

    sim_cfg = habitat_sim.SimulatorConfiguration()
    sim_cfg.scene_id = scene_info["scene"]
    sim_cfg.enable_physics = False

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = []

    sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
    try:
        navmesh_loaded = bool(sim.pathfinder.is_loaded)
        navmesh_path = Path(scene_info["navmesh"])
        if not navmesh_loaded and navmesh_path.exists():
            navmesh_loaded = bool(sim.pathfinder.load_nav_mesh(str(navmesh_path)))

        random_point = None
        geodesic_distance = None
        if navmesh_loaded:
            p0 = sim.pathfinder.get_random_navigable_point()
            p1 = sim.pathfinder.get_random_navigable_point()
            random_point = [float(x) for x in p0]
            path = habitat_sim.ShortestPath()
            path.requested_start = p0
            path.requested_end = p1
            found_path = sim.pathfinder.find_path(path)
            geodesic_distance = float(path.geodesic_distance) if found_path else None

        return {
            "ok": True,
            "habitat_sim_version": getattr(habitat_sim, "__version__", None),
            "scene": scene_info["scene"],
            "navmesh_loaded": navmesh_loaded,
            "random_navigable_point": random_point,
            "geodesic_distance": geodesic_distance,
        }
    finally:
        sim.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", default="/data")
    args = parser.parse_args()

    data_root = Path(args.data_root).resolve()
    hm3d = data_root / "scene_datasets" / "hm3d"
    objectnav = data_root / "datasets" / "objectnav" / "hm3d" / "v2"
    ovon = data_root / "datasets" / "ovon" / "hm3d"

    import habitat

    summary = {
        "data_root": str(data_root),
        "habitat_import": str(getattr(habitat, "__file__", "")),
        "hm3d": {
            "exists": hm3d.exists(),
            "basis_glb": count_files(hm3d, "*.basis.glb"),
            "basis_navmesh": count_files(hm3d, "*.basis.navmesh"),
            "semantic_glb": count_files(hm3d, "*.semantic.glb"),
        },
        "objectnav_hm3d_v2": episode_summary(objectnav),
        "hm3d_ovon": episode_summary(ovon),
        "habitat_sim_smoke": habitat_sim_smoke(hm3d),
    }

    print(json.dumps(summary, indent=2, sort_keys=True))

    required = [
        summary["hm3d"]["exists"],
        summary["hm3d"]["basis_glb"] > 0,
        summary["objectnav_hm3d_v2"]["json_gz"] > 0,
        summary["hm3d_ovon"]["json_gz"] > 0,
        summary["habitat_sim_smoke"]["ok"],
        summary["habitat_sim_smoke"]["navmesh_loaded"],
    ]
    if not all(required):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
