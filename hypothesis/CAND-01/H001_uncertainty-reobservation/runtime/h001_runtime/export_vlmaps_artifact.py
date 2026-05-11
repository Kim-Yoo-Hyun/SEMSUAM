import argparse
import json
import math
from collections import deque
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np


def load_query_embedding(path: Path) -> np.ndarray:
    if path.suffix == ".npy":
        emb = np.load(path)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        emb = np.asarray(data, dtype=np.float32)
    emb = np.asarray(emb, dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(emb))
    if norm <= 1e-8:
        raise ValueError("query embedding has near-zero norm")
    return emb / norm


def parse_optional_int(value: Optional[int], default: int) -> int:
    return default if value is None else int(value)


def connected_components(mask: np.ndarray) -> Iterable[List[Tuple[int, int]]]:
    visited = np.zeros(mask.shape, dtype=bool)
    height, width = mask.shape
    for row in range(height):
        for col in range(width):
            if visited[row, col] or not bool(mask[row, col]):
                continue
            queue: deque[Tuple[int, int]] = deque([(row, col)])
            visited[row, col] = True
            cells: List[Tuple[int, int]] = []
            while queue:
                r, c = queue.popleft()
                cells.append((r, c))
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if 0 <= nr < height and 0 <= nc < width and not visited[nr, nc] and bool(mask[nr, nc]):
                        visited[nr, nc] = True
                        queue.append((nr, nc))
            yield cells


def score_grid(features: np.ndarray, query_embedding: np.ndarray) -> np.ndarray:
    if features.ndim != 3:
        raise ValueError(f"expected feature grid with shape HxWxC, got {features.shape}")
    if features.shape[-1] != query_embedding.shape[0]:
        raise ValueError(
            f"feature dim {features.shape[-1]} does not match query embedding dim {query_embedding.shape[0]}"
        )
    features = np.asarray(features, dtype=np.float32)
    norms = np.linalg.norm(features, axis=-1)
    scores = np.tensordot(features, query_embedding, axes=([-1], [0]))
    scores = np.divide(scores, norms, out=np.zeros_like(scores, dtype=np.float32), where=norms > 1e-8)
    return scores


def load_crop(path: Path, row_start: int, row_end: Optional[int], col_start: int, col_end: Optional[int]) -> np.ndarray:
    arr = np.load(path, mmap_mode="r")
    r_end = parse_optional_int(row_end, arr.shape[0])
    c_end = parse_optional_int(col_end, arr.shape[1])
    return np.asarray(arr[row_start:r_end, col_start:c_end])


def valid_mask_from_inputs(
    scores: np.ndarray,
    weight_path: Optional[Path],
    obstacles_path: Optional[Path],
    row_start: int,
    row_end: Optional[int],
    col_start: int,
    col_end: Optional[int],
    use_obstacle_mask: bool,
    free_space_value: int,
) -> np.ndarray:
    valid = np.isfinite(scores)
    if weight_path is not None and weight_path.exists():
        weight = load_crop(weight_path, row_start, row_end, col_start, col_end)
        if weight.ndim == 3:
            weight = np.max(weight, axis=-1)
        valid &= weight > 0
    if use_obstacle_mask and obstacles_path is not None and obstacles_path.exists():
        obstacles = load_crop(obstacles_path, row_start, row_end, col_start, col_end)
        valid &= obstacles == free_space_value
    return valid


def candidate_position(
    row: float,
    col: float,
    row_start: int,
    col_start: int,
    grid_scale: float,
    scene_floor_y: float,
) -> List[float]:
    return [
        float((col_start + col) * grid_scale),
        float(scene_floor_y),
        float((row_start + row) * grid_scale),
    ]


def components_to_candidates(
    scores: np.ndarray,
    mask: np.ndarray,
    scene_name: str,
    query: str,
    row_start: int,
    col_start: int,
    grid_scale: float,
    scene_floor_y: float,
    min_component_cells: int,
    max_candidates: int,
) -> List[Dict[str, Any]]:
    candidates: List[Dict[str, Any]] = []
    for cells in connected_components(mask):
        if len(cells) < min_component_cells:
            continue
        rows = np.asarray([cell[0] for cell in cells], dtype=np.float32)
        cols = np.asarray([cell[1] for cell in cells], dtype=np.float32)
        cell_scores = np.asarray([scores[cell] for cell in cells], dtype=np.float32)
        best_idx = int(np.argmax(cell_scores))
        best_row = float(rows[best_idx])
        best_col = float(cols[best_idx])
        centroid_row = float(np.mean(rows))
        centroid_col = float(np.mean(cols))
        candidates.append(
            {
                "candidate_id": f"vlmaps:{scene_name}:{query}:{len(candidates)}",
                "category": query,
                "position": candidate_position(centroid_row, centroid_col, row_start, col_start, grid_scale, scene_floor_y),
                "visit_position": candidate_position(best_row, best_col, row_start, col_start, grid_scale, scene_floor_y),
                "score": float(np.max(cell_scores)),
                "mean_score": float(np.mean(cell_scores)),
                "view_count": int(len(cells)),
                "component_cells": int(len(cells)),
                "backend_source": "vlmaps_feature_grid",
            }
        )
    candidates.sort(key=lambda row: (float(row["score"]), int(row["component_cells"])), reverse=True)
    return candidates[:max_candidates]


def export_candidates(args: argparse.Namespace) -> Dict[str, Any]:
    scene_dir = Path(args.scene_dir)
    grid_path = Path(args.grid) if args.grid else scene_dir / "map_correct" / "grid_lseg_1.npy"
    weight_path = Path(args.weight) if args.weight else scene_dir / "map_correct" / "weight_lseg_1.npy"
    obstacles_path = Path(args.obstacles) if args.obstacles else scene_dir / "map_correct" / "obstacles.npy"
    query_embedding = load_query_embedding(Path(args.query_embedding))

    feature_grid = load_crop(grid_path, args.row_start, args.row_end, args.col_start, args.col_end)
    scores = score_grid(feature_grid, query_embedding)
    valid = valid_mask_from_inputs(
        scores,
        weight_path,
        obstacles_path,
        args.row_start,
        args.row_end,
        args.col_start,
        args.col_end,
        args.use_obstacle_mask,
        args.free_space_value,
    )
    if not np.any(valid):
        raise ValueError("no valid cells after applying masks")

    threshold = float(np.percentile(scores[valid], args.top_percentile))
    mask = valid & (scores >= threshold)
    scene_name = scene_dir.name
    candidates = components_to_candidates(
        scores,
        mask,
        scene_name,
        args.query,
        args.row_start,
        args.col_start,
        args.grid_scale,
        args.scene_floor_y,
        args.min_component_cells,
        args.max_candidates,
    )
    if not candidates:
        valid_scores = np.where(valid, scores, -math.inf)
        flat_indices = np.argsort(valid_scores.ravel())[::-1][: args.max_candidates]
        height, width = scores.shape
        candidates = []
        for rank, flat_idx in enumerate(flat_indices):
            row = int(flat_idx // width)
            col = int(flat_idx % width)
            if not np.isfinite(valid_scores[row, col]):
                continue
            candidates.append(
                {
                    "candidate_id": f"vlmaps:{scene_name}:{args.query}:{rank}",
                    "category": args.query,
                    "position": candidate_position(row, col, args.row_start, args.col_start, args.grid_scale, args.scene_floor_y),
                    "visit_position": candidate_position(row, col, args.row_start, args.col_start, args.grid_scale, args.scene_floor_y),
                    "score": float(scores[row, col]),
                    "mean_score": float(scores[row, col]),
                    "view_count": 1,
                    "component_cells": 1,
                    "backend_source": "vlmaps_feature_grid_top_cell",
                }
            )

    return {
        "scene_id": args.scene_id,
        "query": args.query,
        "candidates": candidates,
        "metadata": {
            "backend": "vlmaps_feature_grid",
            "grid": str(grid_path),
            "query_embedding": str(args.query_embedding),
            "top_percentile": args.top_percentile,
            "crop": [args.row_start, args.row_end, args.col_start, args.col_end],
            "uses_gt_for_action": False,
            "coordinate_frame": "vlmaps_grid",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export non-GT VLMaps-derived candidates as artifact_jsonl.")
    parser.add_argument("--scene-dir", required=True)
    parser.add_argument("--scene-id", required=True)
    parser.add_argument("--query", required=True)
    parser.add_argument("--query-embedding", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--grid", default=None)
    parser.add_argument("--weight", default=None)
    parser.add_argument("--obstacles", default=None)
    parser.add_argument("--row-start", type=int, default=0)
    parser.add_argument("--row-end", type=int, default=None)
    parser.add_argument("--col-start", type=int, default=0)
    parser.add_argument("--col-end", type=int, default=None)
    parser.add_argument("--top-percentile", type=float, default=99.5)
    parser.add_argument("--min-component-cells", type=int, default=10)
    parser.add_argument("--max-candidates", type=int, default=10)
    parser.add_argument("--grid-scale", type=float, default=1.0)
    parser.add_argument("--scene-floor-y", type=float, default=0.0)
    parser.add_argument("--use-obstacle-mask", action="store_true")
    parser.add_argument("--free-space-value", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    row = export_candidates(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")
    print(json.dumps({"out": str(out), "num_candidates": len(row["candidates"])}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
