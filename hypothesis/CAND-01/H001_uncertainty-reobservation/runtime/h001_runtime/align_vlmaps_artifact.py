import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def as_matrix4(value: Any) -> List[List[float]]:
    if not isinstance(value, list):
        raise ValueError("world_from_vlmaps_origin must be a list")
    if len(value) == 16:
        return [[float(value[r * 4 + c]) for c in range(4)] for r in range(4)]
    if len(value) == 4 and all(isinstance(row, list) and len(row) == 4 for row in value):
        return [[float(value[r][c]) for c in range(4)] for r in range(4)]
    raise ValueError("world_from_vlmaps_origin must be a 4x4 matrix or flat 16-vector")


def validate_alignment(alignment: Dict[str, Any]) -> Dict[str, Any]:
    if alignment.get("uses_gt_for_action") is not False:
        raise ValueError("alignment must declare uses_gt_for_action=false")
    if alignment.get("coordinate_frame") != "habitat_world":
        raise ValueError("alignment coordinate_frame must be habitat_world")

    grid_size = float(alignment["grid_size"])
    cell_size = float(alignment["cell_size"])
    origin = alignment.get("grid_origin_cell", [grid_size / 2.0, grid_size / 2.0])
    if not isinstance(origin, list) or len(origin) != 2:
        raise ValueError("grid_origin_cell must be [col, row]")

    return {
        "coordinate_frame": "habitat_world",
        "alignment_source": str(alignment.get("alignment_source", "unknown")),
        "alignment_id": str(alignment.get("alignment_id", "unnamed")),
        "uses_gt_for_action": False,
        "vlmaps_commit": alignment.get("vlmaps_commit"),
        "grid_size": grid_size,
        "cell_size": cell_size,
        "origin_col": float(origin[0]),
        "origin_row": float(origin[1]),
        "world_from_vlmaps_origin": as_matrix4(alignment["world_from_vlmaps_origin"]),
        "y_strategy": str(alignment.get("y_strategy", "snap_to_habitat_navmesh")),
    }


def matvec4(matrix: List[List[float]], vec: List[float]) -> List[float]:
    return [sum(matrix[r][c] * vec[c] for c in range(4)) for r in range(4)]


def grid_triplet_to_local(position: List[float], spec: Dict[str, Any]) -> List[float]:
    if len(position) != 3:
        raise ValueError(f"expected [grid_col, y, grid_row], got {position}")
    grid_col = float(position[0])
    grid_row = float(position[2])
    x_local = (grid_col - spec["origin_col"]) * spec["cell_size"]
    z_local = (spec["origin_row"] - grid_row) * spec["cell_size"]
    return [x_local, 0.0, z_local]


def grid_triplet_to_world(position: List[float], spec: Dict[str, Any]) -> List[float]:
    x_local, y_local, z_local = grid_triplet_to_local(position, spec)
    out = matvec4(spec["world_from_vlmaps_origin"], [x_local, y_local, z_local, 1.0])
    w = out[3]
    if abs(w) <= 1e-8:
        raise ValueError("world transform produced near-zero homogeneous scale")
    return [float(out[0] / w), float(out[1] / w), float(out[2] / w)]


def norm_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        return None
    return value


class HabitatSnapper:
    def __init__(self, scene: Path) -> None:
        import habitat_sim

        self._habitat_sim = habitat_sim
        sim_cfg = habitat_sim.SimulatorConfiguration()
        sim_cfg.scene_id = str(scene)
        sim_cfg.enable_physics = False

        agent_cfg = habitat_sim.agent.AgentConfiguration()
        agent_cfg.sensor_specifications = []

        self._sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
        navmesh = navmesh_path(scene)
        if navmesh.exists() and not self._sim.pathfinder.is_loaded:
            self._sim.pathfinder.load_nav_mesh(str(navmesh))
        if not self._sim.pathfinder.is_loaded:
            raise RuntimeError(f"navmesh is not loaded for scene: {scene}")

    def close(self) -> None:
        self._sim.close()

    def snap(self, point: List[float]) -> Tuple[List[float], bool]:
        import numpy as np

        arr = np.array(point, dtype=np.float32)
        snapped = self._sim.pathfinder.snap_point(arr)
        snapped_list = [float(v) for v in snapped]
        return snapped_list, bool(self._sim.pathfinder.is_navigable(snapped))

    def distance(self, start: List[float], end: List[float]) -> Optional[float]:
        import numpy as np

        path = self._habitat_sim.ShortestPath()
        path.requested_start = np.array(start, dtype=np.float32)
        path.requested_end = np.array(end, dtype=np.float32)
        if not self._sim.pathfinder.find_path(path):
            return None
        return norm_float(path.geodesic_distance)


def navmesh_path(scene: Path) -> Path:
    if scene.name.endswith(".basis.glb"):
        return scene.with_name(scene.name.replace(".basis.glb", ".basis.navmesh"))
    return scene.with_suffix(".navmesh")


def align_candidate(candidate: Dict[str, Any], spec: Dict[str, Any], snapper: Optional[HabitatSnapper]) -> Dict[str, Any]:
    row = deepcopy(candidate)
    raw_position = [float(v) for v in row["position"]]
    raw_visit = [float(v) for v in row.get("visit_position", raw_position)]
    world_position = grid_triplet_to_world(raw_position, spec)
    world_visit = grid_triplet_to_world(raw_visit, spec)

    row["vlmaps_grid_position"] = raw_position
    row["vlmaps_grid_visit_position"] = raw_visit
    row["position"] = world_position
    row["visit_position_unsnapped"] = world_visit
    row["coordinate_frame"] = "habitat_world"
    row["alignment_source"] = spec["alignment_source"]
    row["alignment_id"] = spec["alignment_id"]

    if snapper is not None:
        snapped, is_navigable = snapper.snap(world_visit)
        row["visit_position"] = snapped
        row["visit_position_snapped"] = True
        row["visit_position_navigable"] = is_navigable
    else:
        row["visit_position"] = world_visit
        row["visit_position_snapped"] = False
        row["visit_position_navigable"] = None
    return row


def align_row(row: Dict[str, Any], spec: Dict[str, Any], snapper: Optional[HabitatSnapper]) -> Dict[str, Any]:
    out = deepcopy(row)
    metadata = dict(out.get("metadata") or {})
    input_frame = metadata.get("coordinate_frame") or out.get("coordinate_frame")
    if input_frame != "vlmaps_grid":
        raise ValueError(f"expected input coordinate_frame=vlmaps_grid, got {input_frame}")

    candidates = out.get("candidates")
    if candidates is None:
        out = align_candidate(out, spec, snapper)
    else:
        out["candidates"] = [align_candidate(candidate, spec, snapper) for candidate in candidates]

    metadata.update(
        {
            "input_coordinate_frame": input_frame,
            "coordinate_frame": "habitat_world",
            "alignment_source": spec["alignment_source"],
            "alignment_id": spec["alignment_id"],
            "grid_size": spec["grid_size"],
            "cell_size": spec["cell_size"],
            "grid_origin_cell": [spec["origin_col"], spec["origin_row"]],
            "y_strategy": spec["y_strategy"],
            "uses_gt_for_action": False,
        }
    )
    out["metadata"] = metadata
    return out


def align_artifact(
    artifact: Path,
    alignment: Path,
    out: Path,
    scene: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    spec = validate_alignment(read_json(alignment))
    snapper = HabitatSnapper(scene) if scene is not None else None
    try:
        rows = [align_row(row, spec, snapper) for row in read_jsonl(artifact)]
    finally:
        if snapper is not None:
            snapper.close()
    write_jsonl(out, rows)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Align VLMaps grid artifact_jsonl candidates to Habitat world coordinates.")
    parser.add_argument("--artifact", required=True)
    parser.add_argument("--alignment", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--scene", default=None, help="Habitat scene path used for navmesh snapping.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = align_artifact(
        artifact=Path(args.artifact),
        alignment=Path(args.alignment),
        out=Path(args.out),
        scene=Path(args.scene) if args.scene else None,
    )
    candidate_count = sum(len(row.get("candidates") or [row]) for row in rows)
    print(
        json.dumps(
            {
                "out": args.out,
                "rows": len(rows),
                "candidates": candidate_count,
                "coordinate_frame": "habitat_world",
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
