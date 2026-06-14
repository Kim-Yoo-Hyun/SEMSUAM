import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from h001_runtime.score_postview_v2 import load_heading_assets
from h001_runtime.score_postview_vlm import artifact_index, candidate_point, project_point, select_candidate_set


SCHEMA_VERSION = "h001.expanded_retrieval_projection_anchor_smoke.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def parse_float_list(text: str) -> List[float]:
    values = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated float")
    return values


def coerce_float_list(value: Any, default: Sequence[float]) -> List[float]:
    if isinstance(value, list):
        try:
            parsed = [float(item) for item in value]
        except (TypeError, ValueError):
            return [float(item) for item in default]
        return parsed if parsed else [float(item) for item in default]
    if isinstance(value, str):
        return parse_float_list(value)
    return [float(item) for item in default]


def ordered_unique(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        output.append(text)
    return output


def select_candidate_set_for_frame(
    all_candidates: List[Dict[str, Any]],
    frame: Dict[str, Any],
    semantic_tie_band: float,
    max_candidates: int,
) -> Tuple[List[Dict[str, Any]], str]:
    frame_candidate_id = str(frame.get("candidate_id")) if frame.get("candidate_id") is not None else None
    explicit_ids = ordered_unique(frame.get("candidate_ids") or frame.get("second_observation_candidate_ids") or [])
    if explicit_ids:
        by_id = {str(candidate.get("candidate_id")): candidate for candidate in all_candidates}
        if frame_candidate_id is not None and frame_candidate_id not in explicit_ids:
            explicit_ids.insert(0, frame_candidate_id)
        selected = [by_id[candidate_id] for candidate_id in explicit_ids if candidate_id in by_id]
        if max_candidates > 0 and len(selected) > max_candidates:
            selected = selected[:max_candidates]
        if selected:
            return selected, "explicit_candidate_ids"
    return (
        select_candidate_set(all_candidates, frame_candidate_id, semantic_tie_band, max_candidates),
        "semantic_tie_band",
    )


def projection_axis_status(pixel: Optional[List[float]], width: int, height: int) -> str:
    if not isinstance(pixel, list) or len(pixel) != 2:
        return "missing_pixel"
    x, y = float(pixel[0]), float(pixel[1])
    x_in = 0.0 <= x < float(width)
    y_in = 0.0 <= y < float(height)
    if x_in and y < 0.0:
        return "x_in_y_above"
    if x_in and y >= float(height):
        return "x_in_y_below"
    if y_in and x < 0.0:
        return "y_in_x_left"
    if y_in and x >= float(width):
        return "y_in_x_right"
    if x_in and y_in:
        return "visible"
    return "both_axes_or_unknown"


def anchor_projection_rows(
    *,
    frame: Dict[str, Any],
    frame_root: Path,
    candidate: Dict[str, Any],
    candidate_point_field: str,
    height_offsets_m: Sequence[float],
    min_projection_depth_m: float,
) -> List[Dict[str, Any]]:
    base_point = candidate_point(candidate, candidate_point_field)
    if base_point is None:
        return [
            {
                "height_offset_m": None,
                "projection_status": "missing_candidate_point",
                "projected_pixel": None,
                "heading_id": None,
            }
        ]

    rows: List[Dict[str, Any]] = []
    for heading in frame.get("rendered_headings") or []:
        assets = load_heading_assets(frame_root, heading)
        if assets is None:
            continue
        for offset in height_offsets_m:
            point = np.asarray(
                [float(base_point[0]), float(base_point[1]) + float(offset), float(base_point[2])],
                dtype=np.float64,
            )
            projection = project_point(
                point,
                assets["world_from_camera"],
                int(assets["width"]),
                int(assets["height"]),
                float(assets["hfov"]),
                min_projection_depth_m,
            )
            rows.append(
                {
                    "heading_id": heading.get("heading_id"),
                    "height_offset_m": float(offset),
                    "projection_anchor_point": [float(value) for value in point.tolist()],
                    "projection_status": projection.get("projection_status"),
                    "projection_axis_status": projection_axis_status(
                        projection.get("projected_pixel"),
                        int(assets["width"]),
                        int(assets["height"]),
                    ),
                    "projected_pixel": projection.get("projected_pixel"),
                    "camera_forward_m": projection.get("camera_forward_m"),
                }
            )
    return rows


def run(args: argparse.Namespace) -> Dict[str, Any]:
    frames = load_jsonl(Path(args.frames))
    if int(args.max_frames) > 0:
        frames = frames[: int(args.max_frames)]
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    frame_root = Path(args.frame_root)
    default_offsets = [float(value) for value in args.projection_anchor_height_offsets_m]
    out_root = Path(args.out_root)

    row_outputs: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    axis_counts: Counter[str] = Counter()
    selected_source_counts: Counter[str] = Counter()
    visible_rows = 0
    missing_candidate_rows = 0
    gt_action_rows = 0
    frame_revision_metadata_rows = 0

    for frame in frames:
        gt_action_rows += int(frame.get("uses_gt_for_action") is True)
        if frame.get("revision_projection_anchor_height_offsets_m") is not None:
            frame_revision_metadata_rows += 1
        scene_id = str(frame.get("scene_id"))
        query = str(frame.get("query"))
        selected_candidates, source = select_candidate_set_for_frame(
            candidates_by_key.get((scene_id, query), []),
            frame,
            float(args.semantic_tie_band),
            int(args.max_candidates_per_frame),
        )
        selected_source_counts[source] += 1
        offsets = coerce_float_list(frame.get("revision_projection_anchor_height_offsets_m"), default_offsets)
        candidate_id = str(frame.get("candidate_id")) if frame.get("candidate_id") is not None else None
        target_candidate = next(
            (candidate for candidate in selected_candidates if str(candidate.get("candidate_id")) == candidate_id),
            selected_candidates[0] if selected_candidates else None,
        )
        if target_candidate is None:
            missing_candidate_rows += 1
            projection_rows: List[Dict[str, Any]] = []
        else:
            projection_rows = anchor_projection_rows(
                frame=frame,
                frame_root=frame_root,
                candidate=target_candidate,
                candidate_point_field=str(args.candidate_point_field),
                height_offsets_m=offsets,
                min_projection_depth_m=float(args.min_projection_depth_m),
            )
        for projection_row in projection_rows:
            status_counts[str(projection_row.get("projection_status"))] += 1
            axis_counts[str(projection_row.get("projection_axis_status"))] += 1
        visible = any(row.get("projection_status") == "visible" for row in projection_rows)
        visible_rows += int(visible)
        row_outputs.append(
            {
                "schema_version": SCHEMA_VERSION,
                "decision_id": frame.get("decision_id"),
                "episode_key": frame.get("episode_key"),
                "scene_id": scene_id,
                "scene_key": frame.get("scene_key"),
                "query": query,
                "candidate_id": candidate_id,
                "candidate_selection_source": source,
                "projection_anchor_height_offsets_m": offsets,
                "projection_anchor_visible": visible,
                "projection_anchor_visible_heading_rows": len(
                    {str(row.get("heading_id")) for row in projection_rows if row.get("projection_status") == "visible"}
                ),
                "projection_anchor_rows": projection_rows,
                "uses_gt_for_action": False,
            }
        )

    rows = len(row_outputs)
    visible_rate = visible_rows / rows if rows else 0.0
    gate = {
        "expected_rows_pass": rows == int(args.expected_rows),
        "projection_anchor_visible_rate_pass": visible_rate >= float(args.min_visible_row_rate),
        "missing_candidate_rows_pass": missing_candidate_rows == 0,
        "no_gt_action_pass": gt_action_rows == 0,
    }
    gate["projection_anchor_smoke_passed"] = all(gate.values())
    summary = {
        "schema_version": SCHEMA_VERSION,
        "frames": str(args.frames),
        "frame_root": str(args.frame_root),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "rows": rows,
        "expected_rows": int(args.expected_rows),
        "projection_anchor_visible_rows": visible_rows,
        "projection_anchor_visible_rate": visible_rate,
        "projection_anchor_status_counts": dict(sorted(status_counts.items())),
        "projection_anchor_axis_counts": dict(sorted(axis_counts.items())),
        "candidate_selection_source_counts": dict(sorted(selected_source_counts.items())),
        "frame_revision_metadata_rows": frame_revision_metadata_rows,
        "missing_candidate_rows": missing_candidate_rows,
        "gt_action_rows": gt_action_rows,
        "projection_anchor_height_offsets_m": default_offsets,
        "candidate_point_field": str(args.candidate_point_field),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "rows": "projection_anchor_smoke_rows.jsonl",
            "summary": "projection_anchor_smoke_summary.json",
        },
    }
    write_jsonl(out_root / "projection_anchor_smoke_rows.jsonl", row_outputs)
    write_json(out_root / "projection_anchor_smoke_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke-test expanded-retrieval projection anchors without detector/SAM2.")
    parser.add_argument("--frames", required=True)
    parser.add_argument("--frame-root", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--projection-anchor-height-offsets-m", type=parse_float_list, default=[0.0, 0.4, 0.8, 1.2, 1.6])
    parser.add_argument("--candidate-point-field", default="grounded_position")
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-frame", type=int, default=1)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--expected-rows", type=int, default=42)
    parser.add_argument("--min-visible-row-rate", type=float, default=0.95)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["projection_anchor_smoke_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
