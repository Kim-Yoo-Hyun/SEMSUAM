import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw
from transformers import OwlViTForObjectDetection, OwlViTProcessor

from h001_runtime.score_postview_v2 import load_heading_assets
from h001_runtime.score_postview_vlm import (
    artifact_index,
    candidate_point,
    candidate_rank_lookup,
    depth_check,
    finite_float,
    load_jsonl,
    project_point,
    select_candidate_set,
)


SCHEMA_VERSION = "h001.postview_detector.v3b_owlvit_box"


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def choose_device(device: str) -> str:
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    return device


def box_area(box: List[float]) -> float:
    left, top, right, bottom = box
    return max(0.0, right - left) * max(0.0, bottom - top)


def point_inside_box(pixel: Optional[List[float]], box: List[float], padding: float) -> bool:
    if pixel is None:
        return False
    x, y = float(pixel[0]), float(pixel[1])
    left, top, right, bottom = [float(v) for v in box]
    return (left - padding) <= x <= (right + padding) and (top - padding) <= y <= (bottom + padding)


def box_center_distance(pixel: Optional[List[float]], box: List[float]) -> Optional[float]:
    if pixel is None:
        return None
    x, y = float(pixel[0]), float(pixel[1])
    left, top, right, bottom = [float(v) for v in box]
    cx = (left + right) / 2.0
    cy = (top + bottom) / 2.0
    return float(math.hypot(x - cx, y - cy))


def box_depth_median(depth: Optional[np.ndarray], box: List[float]) -> Optional[float]:
    if depth is None:
        return None
    height, width = depth.shape[:2]
    left = max(0, min(width, int(math.floor(box[0]))))
    top = max(0, min(height, int(math.floor(box[1]))))
    right = max(0, min(width, int(math.ceil(box[2]))))
    bottom = max(0, min(height, int(math.ceil(box[3]))))
    if left >= right or top >= bottom:
        return None
    patch = np.asarray(depth[top:bottom, left:right], dtype=np.float32)
    valid = patch[np.isfinite(patch) & (patch > 0)]
    if valid.size == 0:
        return None
    return float(np.median(valid))


def detect_boxes(
    image: Image.Image,
    detector_query: str,
    processor: OwlViTProcessor,
    model: OwlViTForObjectDetection,
    device: str,
    threshold: float,
) -> List[Dict[str, Any]]:
    text = [[detector_query]]
    inputs = processor(text=text, images=image, return_tensors="pt")
    inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    target_sizes = torch.tensor([[image.height, image.width]], device=device)
    results = processor.post_process_object_detection(outputs=outputs, target_sizes=target_sizes, threshold=threshold)[0]
    boxes: List[Dict[str, Any]] = []
    for idx, (score, label, box) in enumerate(zip(results["scores"], results["labels"], results["boxes"])):
        box_values = [float(value) for value in box.detach().cpu().tolist()]
        boxes.append(
            {
                "box_index": idx,
                "box_xyxy": box_values,
                "detector_score": float(score.detach().cpu().item()),
                "label_index": int(label.detach().cpu().item()),
                "label_text": detector_query,
                "box_area_px": float(box_area(box_values)),
            }
        )
    boxes.sort(key=lambda row: float(row["detector_score"]), reverse=True)
    return boxes


def format_detector_query(query: str, query_template: str) -> str:
    normalized_query = query.replace("_", " ").strip()
    if "{query}" not in query_template:
        raise ValueError("--query-template must contain '{query}'")
    return query_template.format(query=normalized_query)


def best_association(
    pixel: Optional[List[float]],
    boxes: List[Dict[str, Any]],
    padding: float,
) -> Tuple[Optional[Dict[str, Any]], bool, Optional[float]]:
    if not boxes:
        return None, False, None
    inside = [box for box in boxes if point_inside_box(pixel, box["box_xyxy"], padding)]
    if inside:
        best = max(inside, key=lambda row: float(row["detector_score"]))
        return best, True, box_center_distance(pixel, best["box_xyxy"])
    distances = [(box_center_distance(pixel, box["box_xyxy"]), box) for box in boxes]
    distances = [(dist, box) for dist, box in distances if dist is not None]
    if not distances:
        return None, False, None
    dist, box = min(distances, key=lambda item: float(item[0]))
    return box, False, float(dist)


def draw_debug(
    image: Image.Image,
    boxes: List[Dict[str, Any]],
    associations: List[Dict[str, Any]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = image.convert("RGB").copy()
    draw = ImageDraw.Draw(canvas)
    for box in boxes:
        left, top, right, bottom = [float(v) for v in box["box_xyxy"]]
        draw.rectangle((left, top, right, bottom), outline=(0, 255, 0), width=2)
        draw.text((left, max(0, top - 12)), f"{box['detector_score']:.2f}", fill=(0, 255, 0))
    for row in associations:
        pixel = row.get("projected_pixel")
        if pixel is None:
            continue
        x, y = float(pixel[0]), float(pixel[1])
        color = (255, 0, 0) if row.get("projected_pixel_inside_box") else (255, 255, 0)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=2)
    canvas.save(out_path)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    frames_path = Path(args.frames)
    frame_root = frames_path.parent
    frames = load_jsonl(frames_path)
    if int(args.max_frames) > 0:
        frames = frames[: int(args.max_frames)]
    candidate_rows = artifact_index(Path(args.candidate_artifact))
    device = choose_device(args.device)
    processor = OwlViTProcessor.from_pretrained(str(args.model_dir), local_files_only=True)
    model = OwlViTForObjectDetection.from_pretrained(str(args.model_dir), local_files_only=True).to(device)
    model.eval()

    detector_rows: List[Dict[str, Any]] = []
    association_rows: List[Dict[str, Any]] = []
    frame_summaries: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    detector_box_counts: List[int] = []
    associated_row_count = 0
    projected_inside_count = 0
    debug_count = 0

    for frame in frames:
        scene_id = str(frame.get("scene_id"))
        query = str(frame.get("query"))
        all_candidates = candidate_rows.get((scene_id, query), [])
        ranks = candidate_rank_lookup(all_candidates)
        selected_candidates = select_candidate_set(
            all_candidates,
            str(frame.get("candidate_id")) if frame.get("candidate_id") is not None else None,
            float(args.semantic_tie_band),
            int(args.max_candidates_per_frame),
        )
        frame_detector_count = 0
        frame_associated_count = 0

        for heading in frame.get("rendered_headings", []):
            heading_id = str(heading.get("heading_id"))
            assets = load_heading_assets(frame_root, heading)
            if assets is None:
                continue
            detector_query = format_detector_query(query, str(args.query_template))
            boxes = detect_boxes(assets["image"], detector_query, processor, model, device, float(args.box_threshold))
            detector_box_counts.append(len(boxes))
            frame_detector_count += len(boxes)
            for box in boxes:
                depth_median = box_depth_median(assets["depth"], box["box_xyxy"])
                detector_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "decision_id": frame.get("decision_id"),
                        "episode_id": frame.get("episode_id"),
                        "episode_key": frame.get("episode_key"),
                        "scene_id": scene_id,
                        "query": query,
                        "detector_query": detector_query,
                        "heading_id": heading_id,
                        "box_index": box["box_index"],
                        "box_xyxy": box["box_xyxy"],
                        "detector_score": box["detector_score"],
                        "label_index": box["label_index"],
                        "label_text": box["label_text"],
                        "box_area_px": box["box_area_px"],
                        "box_depth_median": depth_median,
                        "uses_gt_for_action": False,
                    }
                )

            heading_associations: List[Dict[str, Any]] = []
            for candidate in selected_candidates:
                candidate_id = str(candidate.get("candidate_id"))
                point = candidate_point(candidate, args.candidate_point_field)
                projection = (
                    {"projection_status": "missing_candidate_point", "projected_pixel": None, "camera_forward_m": None}
                    if point is None
                    else project_point(
                        point,
                        assets["world_from_camera"],
                        int(assets["width"]),
                        int(assets["height"]),
                        float(assets["hfov"]),
                        float(args.min_projection_depth_m),
                    )
                )
                projected_pixel = projection.get("projected_pixel")
                projection_status = str(projection.get("projection_status"))
                depth_info = depth_check(
                    assets["depth"],
                    projected_pixel,
                    projection.get("camera_forward_m"),
                    float(args.depth_tolerance_m),
                    int(args.depth_window_px),
                )
                best_box, inside_box, center_dist = best_association(projected_pixel, boxes, float(args.box_padding_px))
                box_depth = box_depth_median(assets["depth"], best_box["box_xyxy"]) if best_box else None
                projected_depth = projection.get("camera_forward_m")
                depth_agreement_m = (
                    None
                    if box_depth is None or projected_depth is None
                    else abs(float(box_depth) - float(projected_depth))
                )
                associated = bool(
                    best_box is not None
                    and projection_status == "visible"
                    and inside_box
                    and (
                        depth_agreement_m is None
                        or depth_agreement_m <= float(args.association_depth_tolerance_m)
                    )
                )
                associated_row_count += int(associated)
                projected_inside_count += int(bool(inside_box and projection_status == "visible"))
                frame_associated_count += int(associated)
                status_counts[projection_status] += 1
                row = {
                    "schema_version": SCHEMA_VERSION,
                    "decision_id": frame.get("decision_id"),
                    "episode_id": frame.get("episode_id"),
                    "episode_key": frame.get("episode_key"),
                    "scene_id": scene_id,
                    "query": query,
                    "detector_query": detector_query,
                    "heading_id": heading_id,
                    "candidate_id": candidate_id,
                    "candidate_rank_before": ranks.get(candidate_id),
                    "point_field": args.candidate_point_field,
                    "projected_pixel": projected_pixel,
                    "projection_status": projection_status,
                    "camera_forward_m": projection.get("camera_forward_m"),
                    "depth_check_status": depth_info.get("depth_check_status"),
                    "depth_error_m": depth_info.get("depth_error_m"),
                    "best_box_index": best_box.get("box_index") if best_box else None,
                    "best_box_xyxy": best_box.get("box_xyxy") if best_box else None,
                    "best_box_score": best_box.get("detector_score") if best_box else None,
                    "projected_pixel_inside_box": bool(inside_box and projection_status == "visible"),
                    "box_center_distance_px": center_dist,
                    "box_depth_median": box_depth,
                    "depth_agreement_m": depth_agreement_m,
                    "associated_to_candidate": associated,
                    "uses_gt_for_action": False,
                }
                association_rows.append(row)
                heading_associations.append(row)

            if args.debug_root and debug_count < int(args.max_debug_images):
                debug_root = Path(args.debug_root)
                out_path = debug_root / str(frame.get("decision_id")) / f"{heading_id}_owlvit_boxes.png"
                draw_debug(assets["image"], boxes, heading_associations, out_path)
                debug_count += 1

        frame_summaries.append(
            {
                "schema_version": SCHEMA_VERSION,
                "decision_id": frame.get("decision_id"),
                "episode_id": frame.get("episode_id"),
                "episode_key": frame.get("episode_key"),
                "scene_id": scene_id,
                "query": query,
                "query_template": str(args.query_template),
                "rendered_heading_count": len(frame.get("rendered_headings", [])),
                "selected_candidate_count": len(selected_candidates),
                "detector_box_count": frame_detector_count,
                "associated_candidate_heading_count": frame_associated_count,
                "has_detector_box": frame_detector_count > 0,
                "has_candidate_association": frame_associated_count > 0,
                "uses_gt_for_action": False,
            }
        )

    out = Path(args.out_root)
    write_jsonl(out / "detector_boxes.jsonl", detector_rows)
    write_jsonl(out / "detector_candidate_associations.jsonl", association_rows)
    write_jsonl(out / "frame_summary.jsonl", frame_summaries)
    rows_with_box = sum(1 for row in frame_summaries if row["has_detector_box"])
    rows_with_association = sum(1 for row in frame_summaries if row["has_candidate_association"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "frames": str(frames_path),
        "candidate_artifact": str(args.candidate_artifact),
        "model_dir": str(args.model_dir),
        "out_root": str(out),
        "device": device,
        "box_threshold": float(args.box_threshold),
        "query_template": str(args.query_template),
        "rows": len(frame_summaries),
        "detector_box_rows": len(detector_rows),
        "association_rows": len(association_rows),
        "rows_with_detector_box": rows_with_box,
        "rows_with_detector_box_rate": rows_with_box / len(frame_summaries) if frame_summaries else 0.0,
        "rows_with_candidate_association": rows_with_association,
        "rows_with_candidate_association_rate": rows_with_association / len(frame_summaries) if frame_summaries else 0.0,
        "associated_candidate_heading_count": associated_row_count,
        "projected_pixel_inside_box_count": projected_inside_count,
        "projection_status_counts": dict(sorted(status_counts.items())),
        "detector_box_count_per_heading": {
            "min": min(detector_box_counts) if detector_box_counts else 0,
            "max": max(detector_box_counts) if detector_box_counts else 0,
            "mean": float(sum(detector_box_counts) / len(detector_box_counts)) if detector_box_counts else 0.0,
        },
        "debug_images_written": debug_count,
        "uses_gt_for_action": False,
        "output_files": {
            "detector_boxes": "detector_boxes.jsonl",
            "detector_candidate_associations": "detector_candidate_associations.jsonl",
            "frame_summary": "frame_summary.jsonl",
            "summary": "summary.json",
        },
    }
    write_json(out / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run OWL-ViT box detector on H001 post-view frames.")
    parser.add_argument("--frames", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--debug-root", default=None)
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-frame", type=int, default=5)
    parser.add_argument("--candidate-point-field", default="position", choices=["position", "visit_position"])
    parser.add_argument("--box-threshold", type=float, default=0.05)
    parser.add_argument("--query-template", default="{query}")
    parser.add_argument("--box-padding-px", type=float, default=4.0)
    parser.add_argument("--depth-tolerance-m", type=float, default=0.75)
    parser.add_argument("--depth-window-px", type=int, default=2)
    parser.add_argument("--association-depth-tolerance-m", type=float, default=1.0)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    parser.add_argument("--max-debug-images", type=int, default=20)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
