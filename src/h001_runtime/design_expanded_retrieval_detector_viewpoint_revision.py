import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

from h001_runtime.score_postview_v2 import load_heading_assets
from h001_runtime.score_postview_vlm import candidate_point, project_point


SCHEMA_VERSION = "h001.expanded_retrieval_detector_viewpoint_revision_design.v1"


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
    return [float(item.strip()) for item in text.split(",") if item.strip()]


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def group_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (str(row.get("decision_id")), str(row.get("candidate_id") or row.get("target_candidate_id")))


def index_frame_rows(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {(str(row.get("decision_id")), str(row.get("target_candidate_id") or row.get("candidate_id"))): row for row in rows}


def select_candidate(frame: Dict[str, Any], candidate_id: str) -> Optional[Dict[str, Any]]:
    for candidate in frame.get("expanded_retrieval_candidate_snapshots") or []:
        if str(candidate.get("candidate_id")) == candidate_id:
            return candidate
    return None


def projection_axis_counts(association_rows: Sequence[Dict[str, Any]], width: int, height: int) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in association_rows:
        if row.get("projection_status") != "out_of_fov":
            continue
        pixel = row.get("projected_pixel")
        if not isinstance(pixel, list) or len(pixel) != 2:
            counts["missing_pixel"] += 1
            continue
        x, y = float(pixel[0]), float(pixel[1])
        x_in = 0.0 <= x < float(width)
        y_in = 0.0 <= y < float(height)
        if x_in and y < 0.0:
            counts["x_in_y_above"] += 1
        elif x_in and y >= float(height):
            counts["x_in_y_below"] += 1
        elif y_in and x < 0.0:
            counts["y_in_x_left"] += 1
        elif y_in and x >= float(width):
            counts["y_in_x_right"] += 1
        else:
            counts["both_axes_or_unknown"] += 1
    return dict(sorted(counts.items()))


def project_with_offsets(
    *,
    frame: Dict[str, Any],
    frame_root: Path,
    candidate: Dict[str, Any],
    candidate_point_field: str,
    height_offsets: Sequence[float],
    min_projection_depth_m: float,
) -> Dict[str, Any]:
    base_point = candidate_point(candidate, candidate_point_field)
    if base_point is None:
        return {
            "has_base_point": False,
            "offset_results": [],
        }
    offset_results: List[Dict[str, Any]] = []
    for offset in height_offsets:
        point = np.asarray([base_point[0], base_point[1] + float(offset), base_point[2]], dtype=np.float64)
        visible_headings = 0
        projection_counts: Counter[str] = Counter()
        y_values: List[float] = []
        x_values: List[float] = []
        for heading in frame.get("rendered_headings") or []:
            assets = load_heading_assets(frame_root, heading)
            projection = project_point(
                point,
                assets["world_from_camera"],
                int(assets["width"]),
                int(assets["height"]),
                float(assets["hfov"]),
                float(min_projection_depth_m),
            )
            status = str(projection.get("projection_status"))
            projection_counts[status] += 1
            if status == "visible":
                visible_headings += 1
            pixel = projection.get("projected_pixel")
            if isinstance(pixel, list) and len(pixel) == 2:
                x_values.append(float(pixel[0]))
                y_values.append(float(pixel[1]))
        offset_results.append(
            {
                "height_offset_m": float(offset),
                "visible": visible_headings > 0,
                "visible_heading_rows": visible_headings,
                "projection_status_counts": dict(sorted(projection_counts.items())),
                "projected_x_min_max": [min(x_values), max(x_values)] if x_values else None,
                "projected_y_min_max": [min(y_values), max(y_values)] if y_values else None,
            }
        )
    return {
        "has_base_point": True,
        "base_point": [float(value) for value in base_point.tolist()],
        "offset_results": offset_results,
    }


def prefix_results(offset_results: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    any_visible = False
    offsets: List[float] = []
    visible_heading_rows = 0
    for item in offset_results:
        offsets.append(float(item.get("height_offset_m")))
        any_visible = any_visible or bool(item.get("visible"))
        visible_heading_rows = max(visible_heading_rows, int(item.get("visible_heading_rows") or 0))
        out.append(
            {
                "height_offsets_m": list(offsets),
                "visible": any_visible,
                "max_visible_heading_rows": visible_heading_rows,
            }
        )
    return out


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    frame_root = Path(args.frame_root)
    failure_rows = load_jsonl(Path(args.failure_rows))
    frame_rows = load_jsonl(Path(args.frame_summary))
    association_rows = load_jsonl(Path(args.associations))
    frame_by_key = index_frame_rows(frame_rows)
    height_offsets = parse_float_list(args.height_offsets)

    design_rows: List[Dict[str, Any]] = []
    mechanism_counts: Counter[str] = Counter()
    single_offset_recovery: Dict[float, Counter[str]] = {offset: Counter() for offset in height_offsets}
    prefix_recovery: Dict[Tuple[float, ...], Counter[str]] = {}

    for failure in failure_rows:
        mechanism = str(failure.get("failure_mechanism"))
        mechanism_counts[mechanism] += 1
        key = group_key(failure)
        frame = frame_by_key.get(key)
        candidate = select_candidate(frame, key[1]) if frame else None
        projection_probe = (
            {"has_base_point": False, "offset_results": []}
            if frame is None or candidate is None
            else project_with_offsets(
                frame=frame,
                frame_root=frame_root,
                candidate=candidate,
                candidate_point_field=str(args.candidate_point_field),
                height_offsets=height_offsets,
                min_projection_depth_m=float(args.min_projection_depth_m),
            )
        )
        row_prefix_results = prefix_results(projection_probe["offset_results"])
        for result in projection_probe["offset_results"]:
            offset = float(result["height_offset_m"])
            single_offset_recovery[offset]["total"] += 1
            single_offset_recovery[offset]["visible"] += int(bool(result.get("visible")))
            if mechanism == "projection_never_visible":
                single_offset_recovery[offset]["projection_never_visible_total"] += 1
                single_offset_recovery[offset]["projection_never_visible_visible"] += int(bool(result.get("visible")))
        for result in row_prefix_results:
            prefix = tuple(float(value) for value in result["height_offsets_m"])
            prefix_recovery.setdefault(prefix, Counter())
            prefix_recovery[prefix]["total"] += 1
            prefix_recovery[prefix]["visible"] += int(bool(result.get("visible")))
            if mechanism == "projection_never_visible":
                prefix_recovery[prefix]["projection_never_visible_total"] += 1
                prefix_recovery[prefix]["projection_never_visible_visible"] += int(bool(result.get("visible")))
        design_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "decision_id": failure.get("decision_id"),
                "candidate_id": failure.get("candidate_id"),
                "scene_key": failure.get("scene_key"),
                "query": failure.get("query"),
                "expanded_candidate_rank": failure.get("expanded_candidate_rank"),
                "failure_mechanism": mechanism,
                "current_visible_heading_rows": failure.get("visible_heading_rows"),
                "projection_anchor_probe": projection_probe,
                "projection_anchor_prefix_results": row_prefix_results,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": bool(failure.get("uses_gt_for_analysis")),
            }
        )

    single_offset_summary = []
    for offset, counts in sorted(single_offset_recovery.items()):
        single_offset_summary.append(
            {
                "height_offset_m": offset,
                "visible_rows": counts["visible"],
                "rows": counts["total"],
                "visible_rate": ratio(counts["visible"], counts["total"]),
                "projection_never_visible_recovered_rows": counts["projection_never_visible_visible"],
                "projection_never_visible_rows": counts["projection_never_visible_total"],
                "projection_never_visible_recovery_rate": ratio(
                    counts["projection_never_visible_visible"],
                    counts["projection_never_visible_total"],
                ),
            }
        )
    prefix_summary = []
    selected_prefix: Optional[Tuple[float, ...]] = None
    for prefix, counts in sorted(prefix_recovery.items(), key=lambda item: (len(item[0]), item[0])):
        recovery_rate = ratio(
            counts["projection_never_visible_visible"],
            counts["projection_never_visible_total"],
        )
        prefix_summary.append(
            {
                "height_offsets_m": list(prefix),
                "visible_rows": counts["visible"],
                "rows": counts["total"],
                "visible_rate": ratio(counts["visible"], counts["total"]),
                "projection_never_visible_recovered_rows": counts["projection_never_visible_visible"],
                "projection_never_visible_rows": counts["projection_never_visible_total"],
                "projection_never_visible_recovery_rate": recovery_rate,
            }
        )
        if selected_prefix is None and recovery_rate is not None and recovery_rate >= float(args.min_projection_recovery_rate):
            selected_prefix = prefix

    if selected_prefix is None:
        selected_prefix = tuple(height_offsets)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "input_files": {
            "failure_rows": str(args.failure_rows),
            "frame_summary": str(args.frame_summary),
            "frame_root": str(args.frame_root),
            "associations": str(args.associations),
        },
        "out_root": str(out_root),
        "failure_mechanism_counts": dict(sorted(mechanism_counts.items())),
        "current_projection_axis_counts": projection_axis_counts(
            association_rows,
            int(args.image_width),
            int(args.image_height),
        ),
        "single_height_offset_projection_recovery": single_offset_summary,
        "height_sweep_projection_recovery": prefix_summary,
        "selected_revision": {
            "name": "projection_anchor_height_sweep_v1",
            "height_offsets_m": list(selected_prefix),
            "reason": (
                "Dominant failures keep x inside the image while y is above the frame; "
                "a non-GT candidate-anchor height sweep directly tests projection geometry before detector thresholds."
            ),
            "requires_detector_threshold_change": False,
            "requires_terminal_objective_change": False,
            "requires_depth_tolerance_change_before_projection_smoke": False,
        },
        "simpler_alternatives": [
            {
                "alternative": "detector_threshold_tuning",
                "status": "rejected_for_next_step",
                "reason": "Detector boxes and SAM2 masks are already available on all candidate observation rows.",
            },
            {
                "alternative": "yaw_widen_only",
                "status": "rejected_for_next_step",
                "reason": "Out-of-FOV projections have x inside the image and y above the image, so horizontal yaw is not the dominant axis.",
            },
            {
                "alternative": "depth_tolerance_only",
                "status": "deferred",
                "reason": "Depth tolerance cannot repair rows whose candidate anchor never projects into the image.",
            },
            {
                "alternative": "single_height_anchor",
                "status": "weaker_than_sweep",
                "reason": "A sweep preserves category-agnostic vertical uncertainty instead of hard-coding one object height.",
            },
        ],
        "gate": {
            "design_gate_passed": selected_prefix is not None,
            "threshold_tuning_allowed": False,
            "viewpoint_projection_revision_required": True,
            "fresh_validation_allowed": False,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") is True for row in failure_rows),
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "expanded_retrieval_detector_viewpoint_revision_design_rows.jsonl",
            "summary": "expanded_retrieval_detector_viewpoint_revision_design_summary.json",
        },
    }
    write_jsonl(out_root / "expanded_retrieval_detector_viewpoint_revision_design_rows.jsonl", design_rows)
    write_json(out_root / "expanded_retrieval_detector_viewpoint_revision_design_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design expanded-retrieval detector viewpoint/projection revision.")
    parser.add_argument("--failure-rows", required=True)
    parser.add_argument("--frame-summary", required=True)
    parser.add_argument("--frame-root", required=True)
    parser.add_argument("--associations", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--candidate-point-field", default="grounded_position")
    parser.add_argument("--height-offsets", default="0.0,0.4,0.8,1.2,1.6")
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    parser.add_argument("--min-projection-recovery-rate", type=float, default=0.95)
    parser.add_argument("--image-width", type=int, default=160)
    parser.add_argument("--image-height", type=int, default=120)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["design_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
