import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import torch
from PIL import Image, ImageDraw
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from transformers import AutoProcessor, GroundingDinoForObjectDetection

from h001_runtime.score_postview_v2 import load_heading_assets
from h001_runtime.score_postview_vlm import (
    artifact_index,
    candidate_point,
    candidate_rank_lookup,
    depth_check,
    load_jsonl,
    project_point,
    select_candidate_set,
)


SCHEMA_VERSION = "h001.postview_detector.v3c_groundingdino_sam2"


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def passthrough_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    prefixes = (
        "pair_",
        "arbitration_",
        "external_",
        "followup_",
        "source_objective_",
        "source_followup_",
        "second_stage_",
        "rival_identity_",
        "revision_",
        "expanded_",
        "proxy_",
        "source_pool_",
        "focus_",
        "goal_validity_",
        "object_relation_",
        "rival_",
        "standoff_",
        "target_",
    )
    keys = {
        "contract_name",
        "planner_name",
        "request_index",
        "request_reason",
        "role",
        "scene_key",
        "source_name",
        "target_index",
        "viewpoint_pair_role",
        "viewpoint_source",
    }
    return {key: value for key, value in row.items() if key.startswith(prefixes) or key in keys}


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


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
            trimmed = selected[:max_candidates]
            if frame_candidate_id is not None and all(
                str(candidate.get("candidate_id")) != frame_candidate_id for candidate in trimmed
            ):
                frame_candidate = next(
                    (candidate for candidate in selected if str(candidate.get("candidate_id")) == frame_candidate_id),
                    None,
                )
                if frame_candidate is not None:
                    trimmed[-1] = frame_candidate
            selected = trimmed
        if selected:
            return selected, "explicit_candidate_ids"
    return (
        select_candidate_set(all_candidates, frame_candidate_id, semantic_tie_band, max_candidates),
        "semantic_tie_band",
    )


def choose_device(device: str) -> str:
    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    return device


def format_detector_query(query: str, query_template: str) -> str:
    normalized_query = query.replace("_", " ").strip()
    if "{query}" not in query_template:
        raise ValueError("--query-template must contain '{query}'")
    return query_template.format(query=normalized_query)


def parse_float_list(text: str) -> List[float]:
    values = [float(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated float")
    return values


def coerce_float_list(value: Any, default: List[float]) -> List[float]:
    if value is None:
        return list(default)
    if isinstance(value, str):
        return parse_float_list(value)
    if isinstance(value, list):
        parsed: List[float] = []
        for item in value:
            try:
                parsed.append(float(item))
            except (TypeError, ValueError):
                return list(default)
        return parsed if parsed else list(default)
    return list(default)


def candidate_anchor_points(
    candidate: Dict[str, Any],
    field: str,
    height_offsets_m: List[float],
    grounded_point_height_m: float,
    grounded_point_max_vertical_gap_m: float,
) -> Tuple[Optional[np.ndarray], List[Dict[str, Any]]]:
    base_point = candidate_point(
        candidate,
        field,
        grounded_point_height_m,
        grounded_point_max_vertical_gap_m,
    )
    if base_point is None:
        return None, []
    anchors = []
    for offset in height_offsets_m:
        point = np.asarray(
            [float(base_point[0]), float(base_point[1]) + float(offset), float(base_point[2])],
            dtype=np.float64,
        )
        anchors.append(
            {
                "projection_anchor_height_offset_m": float(offset),
                "projection_anchor_point": [float(value) for value in point.tolist()],
                "point": point,
            }
        )
    return base_point, anchors


def box_area(box: List[float]) -> float:
    left, top, right, bottom = box
    return max(0.0, right - left) * max(0.0, bottom - top)


def point_inside_box(pixel: Optional[List[float]], box: List[float], padding: float) -> bool:
    if pixel is None:
        return False
    x, y = float(pixel[0]), float(pixel[1])
    left, top, right, bottom = [float(v) for v in box]
    return (left - padding) <= x <= (right + padding) and (top - padding) <= y <= (bottom + padding)


def point_inside_mask(pixel: Optional[List[float]], mask: Optional[np.ndarray]) -> bool:
    if pixel is None or mask is None:
        return False
    height, width = mask.shape[:2]
    x = int(round(float(pixel[0])))
    y = int(round(float(pixel[1])))
    if x < 0 or x >= width or y < 0 or y >= height:
        return False
    return bool(mask[y, x])


def box_center_distance(pixel: Optional[List[float]], box: List[float]) -> Optional[float]:
    if pixel is None:
        return None
    x, y = float(pixel[0]), float(pixel[1])
    left, top, right, bottom = [float(v) for v in box]
    return float(math.hypot(x - ((left + right) / 2.0), y - ((top + bottom) / 2.0)))


def depth_median_for_box(depth: Optional[np.ndarray], box: List[float]) -> Optional[float]:
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


def depth_median_for_mask(depth: Optional[np.ndarray], mask: Optional[np.ndarray]) -> Optional[float]:
    if depth is None or mask is None:
        return None
    mask_bool = np.asarray(mask, dtype=bool)
    if mask_bool.shape[:2] != depth.shape[:2] or not mask_bool.any():
        return None
    values = np.asarray(depth, dtype=np.float32)[mask_bool]
    valid = values[np.isfinite(values) & (values > 0)]
    if valid.size == 0:
        return None
    return float(np.median(valid))


def anchor_choice_key(row: Dict[str, Any]) -> Tuple[int, float, float, float, float]:
    depth = row.get("depth_agreement_m")
    distance = row.get("box_center_distance_px")
    score = row.get("best_box_score")
    if row.get("associated_to_candidate"):
        bucket = 0
    elif row.get("projection_status") == "visible" and row.get("projected_pixel_inside_mask"):
        bucket = 1
    elif row.get("projection_status") == "visible" and row.get("projected_pixel_inside_box"):
        bucket = 2
    elif row.get("projection_status") == "visible":
        bucket = 3
    else:
        bucket = 4
    return (
        bucket,
        float(depth) if depth is not None else math.inf,
        float(distance) if distance is not None else math.inf,
        -(float(score) if score is not None else -math.inf),
        abs(float(row.get("projection_anchor_height_offset_m") or 0.0)),
    )


def detect_boxes(
    image: Image.Image,
    detector_query: str,
    processor: AutoProcessor,
    model: GroundingDinoForObjectDetection,
    device: str,
    box_threshold: float,
    text_threshold: float,
) -> List[Dict[str, Any]]:
    inputs = processor(images=image, text=detector_query, return_tensors="pt")
    inputs = {key: value.to(device) if hasattr(value, "to") else value for key, value in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
    target_sizes = torch.tensor([[image.height, image.width]], device=device)
    results = processor.post_process_grounded_object_detection(
        outputs,
        input_ids=inputs.get("input_ids"),
        threshold=box_threshold,
        text_threshold=text_threshold,
        target_sizes=target_sizes,
    )[0]
    boxes: List[Dict[str, Any]] = []
    for idx, (score, box) in enumerate(zip(results["scores"], results["boxes"])):
        box_values = [float(value) for value in box.detach().cpu().tolist()]
        labels = results.get("text_labels") or results.get("labels") or []
        label_text = labels[idx] if idx < len(labels) else detector_query
        boxes.append(
            {
                "box_index": idx,
                "box_xyxy": box_values,
                "detector_score": float(score.detach().cpu().item()),
                "label_text": str(label_text),
                "box_area_px": float(box_area(box_values)),
            }
        )
    boxes.sort(key=lambda row: float(row["detector_score"]), reverse=True)
    for new_idx, box in enumerate(boxes):
        box["box_index"] = new_idx
    return boxes


def predict_masks(
    image: Image.Image,
    boxes: List[Dict[str, Any]],
    predictor: SAM2ImagePredictor,
    max_boxes: int,
) -> Tuple[List[Dict[str, Any]], Dict[int, np.ndarray]]:
    masks_by_box: Dict[int, np.ndarray] = {}
    mask_rows: List[Dict[str, Any]] = []
    if not boxes:
        return mask_rows, masks_by_box
    predictor.set_image(np.asarray(image.convert("RGB")))
    for box in boxes[:max_boxes]:
        box_array = np.asarray(box["box_xyxy"], dtype=np.float32)
        masks, scores, _ = predictor.predict(box=box_array, multimask_output=True)
        if masks is None or len(masks) == 0:
            continue
        best_index = int(np.argmax(scores))
        mask = np.asarray(masks[best_index], dtype=bool)
        masks_by_box[int(box["box_index"])] = mask
        mask_rows.append(
            {
                "box_index": int(box["box_index"]),
                "mask_index": best_index,
                "sam2_score": float(scores[best_index]),
                "mask_area_px": int(mask.sum()),
                "mask_coverage": float(mask.sum() / mask.size) if mask.size else 0.0,
            }
        )
    return mask_rows, masks_by_box


def best_box_for_pixel(
    pixel: Optional[List[float]],
    boxes: List[Dict[str, Any]],
    masks_by_box: Dict[int, np.ndarray],
    padding: float,
) -> Tuple[Optional[Dict[str, Any]], bool, bool, Optional[float]]:
    if not boxes:
        return None, False, False, None
    mask_hits = [
        box for box in boxes if point_inside_mask(pixel, masks_by_box.get(int(box["box_index"])))
    ]
    if mask_hits:
        best = max(mask_hits, key=lambda row: float(row["detector_score"]))
        return best, point_inside_box(pixel, best["box_xyxy"], padding), True, box_center_distance(pixel, best["box_xyxy"])
    box_hits = [box for box in boxes if point_inside_box(pixel, box["box_xyxy"], padding)]
    if box_hits:
        best = max(box_hits, key=lambda row: float(row["detector_score"]))
        return best, True, False, box_center_distance(pixel, best["box_xyxy"])
    distances = [(box_center_distance(pixel, box["box_xyxy"]), box) for box in boxes]
    distances = [(dist, box) for dist, box in distances if dist is not None]
    if not distances:
        return None, False, False, None
    dist, box = min(distances, key=lambda item: float(item[0]))
    return box, False, False, float(dist)


def draw_debug(
    image: Image.Image,
    boxes: List[Dict[str, Any]],
    masks_by_box: Dict[int, np.ndarray],
    associations: List[Dict[str, Any]],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = image.convert("RGB").copy()
    overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    overlay_arr = np.asarray(overlay).copy()
    for mask in masks_by_box.values():
        mask_bool = np.asarray(mask, dtype=bool)
        overlay_arr[mask_bool, 0] = 0
        overlay_arr[mask_bool, 1] = 160
        overlay_arr[mask_bool, 2] = 255
        overlay_arr[mask_bool, 3] = 70
    canvas = Image.alpha_composite(canvas.convert("RGBA"), Image.fromarray(overlay_arr)).convert("RGB")
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
        color = (255, 0, 0) if row.get("projected_pixel_inside_mask") else (255, 255, 0)
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), outline=color, width=2)
    canvas.save(out_path)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    frames_path = Path(args.frames)
    frame_root = Path(args.frame_root) if args.frame_root else frames_path.parent
    frames = load_jsonl(frames_path)
    if int(args.max_frames) > 0:
        frames = frames[: int(args.max_frames)]
    candidate_rows = artifact_index(Path(args.candidate_artifact))
    device = choose_device(args.device)

    processor = AutoProcessor.from_pretrained(str(args.groundingdino_dir), local_files_only=True)
    detector = GroundingDinoForObjectDetection.from_pretrained(
        str(args.groundingdino_dir),
        local_files_only=True,
    ).to(device)
    detector.eval()
    sam2_model = build_sam2(str(args.sam2_config), str(args.sam2_checkpoint), device=device, mode="eval")
    mask_predictor = SAM2ImagePredictor(sam2_model)

    detector_rows: List[Dict[str, Any]] = []
    mask_rows_all: List[Dict[str, Any]] = []
    association_rows: List[Dict[str, Any]] = []
    frame_summaries: List[Dict[str, Any]] = []
    projection_counts: Counter[str] = Counter()
    projection_anchor_counts: Counter[str] = Counter()
    projection_anchor_policy_counts: Counter[str] = Counter()
    projection_anchor_offset_counts: Counter[str] = Counter()
    candidate_selection_counts: Counter[str] = Counter()
    detector_box_counts: List[int] = []
    associated_heading_count = 0
    projected_inside_mask_count = 0
    debug_count = 0

    for frame in frames:
        scene_id = str(frame.get("scene_id"))
        query = str(frame.get("query"))
        frame_passthrough = passthrough_fields(frame)
        detector_query = format_detector_query(query, str(args.query_template))
        all_candidates = candidate_rows.get((scene_id, query), [])
        ranks = candidate_rank_lookup(all_candidates)
        selected_candidates, candidate_selection_source = select_candidate_set_for_frame(
            all_candidates,
            frame,
            float(args.semantic_tie_band),
            int(args.max_candidates_per_frame),
        )
        candidate_selection_counts[candidate_selection_source] += 1
        selected_candidate_ids = [str(candidate.get("candidate_id")) for candidate in selected_candidates]
        frame_anchor_offsets = coerce_float_list(
            frame.get("revision_projection_anchor_height_offsets_m"),
            [float(value) for value in args.projection_anchor_height_offsets_m],
        )
        frame_anchor_policy = str(
            frame.get("revision_projection_anchor_policy")
            or ("single_point_projection" if frame_anchor_offsets == [0.0] else "projection_anchor_height_sweep_v1")
        )
        projection_anchor_policy_counts[frame_anchor_policy] += 1
        frame_detector_count = 0
        frame_mask_count = 0
        frame_associated_count = 0

        rendered_headings = list(frame.get("rendered_headings", []))
        if int(args.max_headings_per_frame) > 0:
            rendered_headings = rendered_headings[: int(args.max_headings_per_frame)]

        for heading in rendered_headings:
            heading_id = str(heading.get("heading_id"))
            assets = load_heading_assets(frame_root, heading)
            if assets is None:
                continue
            boxes = detect_boxes(
                assets["image"],
                detector_query,
                processor,
                detector,
                device,
                float(args.box_threshold),
                float(args.text_threshold),
            )
            if int(args.max_detector_boxes_per_heading) > 0:
                boxes = boxes[: int(args.max_detector_boxes_per_heading)]
            detector_box_counts.append(len(boxes))
            frame_detector_count += len(boxes)
            heading_mask_rows, masks_by_box = predict_masks(
                assets["image"],
                boxes,
                mask_predictor,
                int(args.max_masks_per_heading),
            )
            frame_mask_count += len(heading_mask_rows)

            for box in boxes:
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
                        "label_text": box["label_text"],
                        "box_area_px": box["box_area_px"],
                        "box_depth_median": depth_median_for_box(assets["depth"], box["box_xyxy"]),
                        "uses_gt_for_action": False,
                        **frame_passthrough,
                    }
                )

            for mask_row in heading_mask_rows:
                box = next(row for row in boxes if int(row["box_index"]) == int(mask_row["box_index"]))
                mask = masks_by_box.get(int(mask_row["box_index"]))
                mask_rows_all.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "decision_id": frame.get("decision_id"),
                        "episode_id": frame.get("episode_id"),
                        "episode_key": frame.get("episode_key"),
                        "scene_id": scene_id,
                        "query": query,
                        "detector_query": detector_query,
                        "heading_id": heading_id,
                        "box_index": mask_row["box_index"],
                        "box_xyxy": box["box_xyxy"],
                        "detector_score": box["detector_score"],
                        "sam2_score": mask_row["sam2_score"],
                        "mask_area_px": mask_row["mask_area_px"],
                        "mask_coverage": mask_row["mask_coverage"],
                        "mask_depth_median": depth_median_for_mask(assets["depth"], mask),
                        "uses_gt_for_action": False,
                        **frame_passthrough,
                    }
                )

            heading_associations: List[Dict[str, Any]] = []
            for candidate in selected_candidates:
                candidate_id = str(candidate.get("candidate_id"))
                base_point, anchor_points = candidate_anchor_points(
                    candidate,
                    args.candidate_point_field,
                    frame_anchor_offsets,
                    float(args.grounded_point_height_m),
                    float(args.grounded_point_max_vertical_gap_m),
                )
                anchor_rows: List[Dict[str, Any]] = []
                if not anchor_points:
                    anchor_rows.append(
                        {
                            "projection_anchor_height_offset_m": None,
                            "projection_anchor_point": None,
                            "projected_pixel": None,
                            "projection_status": "missing_candidate_point",
                            "camera_forward_m": None,
                            "depth_check_status": "missing_candidate_point",
                            "depth_error_m": None,
                            "best_box_index": None,
                            "best_box_xyxy": None,
                            "best_box_score": None,
                            "projected_pixel_inside_box": False,
                            "projected_pixel_inside_mask": False,
                            "box_center_distance_px": None,
                            "mask_depth_median": None,
                            "depth_agreement_m": None,
                            "associated_to_candidate": False,
                        }
                    )
                for anchor in anchor_points:
                    projection = project_point(
                        anchor["point"],
                        assets["world_from_camera"],
                        int(assets["width"]),
                        int(assets["height"]),
                        float(assets["hfov"]),
                        float(args.min_projection_depth_m),
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
                    best_box, inside_box, inside_mask, center_dist = best_box_for_pixel(
                        projected_pixel,
                        boxes,
                        masks_by_box,
                        float(args.box_padding_px),
                    )
                    best_mask = masks_by_box.get(int(best_box["box_index"])) if best_box else None
                    mask_depth = depth_median_for_mask(assets["depth"], best_mask)
                    projected_depth = projection.get("camera_forward_m")
                    depth_agreement_m = (
                        None
                        if mask_depth is None or projected_depth is None
                        else abs(float(mask_depth) - float(projected_depth))
                    )
                    associated = bool(
                        best_box is not None
                        and projection_status == "visible"
                        and inside_mask
                        and (
                            depth_agreement_m is None
                            or depth_agreement_m <= float(args.association_depth_tolerance_m)
                        )
                    )
                    anchor_rows.append(
                        {
                            "projection_anchor_height_offset_m": anchor["projection_anchor_height_offset_m"],
                            "projection_anchor_point": anchor["projection_anchor_point"],
                            "projected_pixel": projected_pixel,
                            "projection_status": projection_status,
                            "camera_forward_m": projection.get("camera_forward_m"),
                            "depth_check_status": depth_info.get("depth_check_status"),
                            "depth_error_m": depth_info.get("depth_error_m"),
                            "best_box_index": best_box.get("box_index") if best_box else None,
                            "best_box_xyxy": best_box.get("box_xyxy") if best_box else None,
                            "best_box_score": best_box.get("detector_score") if best_box else None,
                            "projected_pixel_inside_box": bool(inside_box and projection_status == "visible"),
                            "projected_pixel_inside_mask": bool(inside_mask and projection_status == "visible"),
                            "box_center_distance_px": center_dist,
                            "mask_depth_median": mask_depth,
                            "depth_agreement_m": depth_agreement_m,
                            "associated_to_candidate": associated,
                        }
                    )
                selected_anchor = min(anchor_rows, key=anchor_choice_key)
                associated = bool(selected_anchor.get("associated_to_candidate"))
                associated_heading_count += int(associated)
                projected_inside_mask_count += int(bool(selected_anchor.get("projected_pixel_inside_mask")))
                frame_associated_count += int(associated)
                projection_counts[str(selected_anchor.get("projection_status"))] += 1
                for anchor_row in anchor_rows:
                    projection_anchor_counts[str(anchor_row.get("projection_status"))] += 1
                projection_anchor_offset_counts[str(selected_anchor.get("projection_anchor_height_offset_m"))] += 1
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
                    "candidate_selection_source": candidate_selection_source,
                    "point_field": args.candidate_point_field,
                    "projection_anchor_policy": frame_anchor_policy,
                    "projection_anchor_height_offsets_m": frame_anchor_offsets,
                    "projection_anchor_base_point": None if base_point is None else [float(value) for value in base_point.tolist()],
                    "projection_anchor_height_offset_m": selected_anchor.get("projection_anchor_height_offset_m"),
                    "projection_anchor_point": selected_anchor.get("projection_anchor_point"),
                    "projection_anchor_candidate_count": len(anchor_rows),
                    "projection_anchor_results": anchor_rows,
                    "projected_pixel": selected_anchor.get("projected_pixel"),
                    "projection_status": selected_anchor.get("projection_status"),
                    "camera_forward_m": selected_anchor.get("camera_forward_m"),
                    "depth_check_status": selected_anchor.get("depth_check_status"),
                    "depth_error_m": selected_anchor.get("depth_error_m"),
                    "best_box_index": selected_anchor.get("best_box_index"),
                    "best_box_xyxy": selected_anchor.get("best_box_xyxy"),
                    "best_box_score": selected_anchor.get("best_box_score"),
                    "projected_pixel_inside_box": bool(selected_anchor.get("projected_pixel_inside_box")),
                    "projected_pixel_inside_mask": bool(selected_anchor.get("projected_pixel_inside_mask")),
                    "box_center_distance_px": selected_anchor.get("box_center_distance_px"),
                    "mask_depth_median": selected_anchor.get("mask_depth_median"),
                    "depth_agreement_m": selected_anchor.get("depth_agreement_m"),
                    "associated_to_candidate": associated,
                    "uses_gt_for_action": False,
                    **frame_passthrough,
                }
                association_rows.append(row)
                heading_associations.append(row)

            if args.debug_root and debug_count < int(args.max_debug_images):
                debug_root = Path(args.debug_root)
                out_path = debug_root / str(frame.get("decision_id")) / f"{heading_id}_gdino_sam2.png"
                draw_debug(assets["image"], boxes, masks_by_box, heading_associations, out_path)
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
                "rendered_heading_count": len(rendered_headings),
                "selected_candidate_count": len(selected_candidates),
                "selected_candidate_ids": selected_candidate_ids,
                "candidate_selection_source": candidate_selection_source,
                "projection_anchor_policy": frame_anchor_policy,
                "projection_anchor_height_offsets_m": frame_anchor_offsets,
                "detector_box_count": frame_detector_count,
                "sam2_mask_count": frame_mask_count,
                "associated_candidate_heading_count": frame_associated_count,
                "has_detector_box": frame_detector_count > 0,
                "has_sam2_mask": frame_mask_count > 0,
                "has_candidate_association": frame_associated_count > 0,
                "uses_gt_for_action": False,
                **frame_passthrough,
            }
        )

    out = Path(args.out_root)
    write_jsonl(out / "detector_boxes.jsonl", detector_rows)
    write_jsonl(out / "detector_masks.jsonl", mask_rows_all)
    write_jsonl(out / "detector_candidate_associations.jsonl", association_rows)
    write_jsonl(out / "frame_summary.jsonl", frame_summaries)
    rows_with_box = sum(1 for row in frame_summaries if row["has_detector_box"])
    rows_with_mask = sum(1 for row in frame_summaries if row["has_sam2_mask"])
    rows_with_association = sum(1 for row in frame_summaries if row["has_candidate_association"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "frames": str(frames_path),
        "candidate_artifact": str(args.candidate_artifact),
        "groundingdino_dir": str(args.groundingdino_dir),
        "sam2_checkpoint": str(args.sam2_checkpoint),
        "out_root": str(out),
        "device": device,
        "query_template": str(args.query_template),
        "box_threshold": float(args.box_threshold),
        "text_threshold": float(args.text_threshold),
        "candidate_point_field": str(args.candidate_point_field),
        "projection_anchor_height_offsets_m": [float(value) for value in args.projection_anchor_height_offsets_m],
        "projection_anchor_policy_counts": dict(sorted(projection_anchor_policy_counts.items())),
        "grounded_point_height_m": float(args.grounded_point_height_m),
        "grounded_point_max_vertical_gap_m": float(args.grounded_point_max_vertical_gap_m),
        "max_headings_per_frame": int(args.max_headings_per_frame),
        "max_detector_boxes_per_heading": int(args.max_detector_boxes_per_heading),
        "max_masks_per_heading": int(args.max_masks_per_heading),
        "candidate_selection_counts": dict(sorted(candidate_selection_counts.items())),
        "rows": len(frame_summaries),
        "detector_box_rows": len(detector_rows),
        "detector_mask_rows": len(mask_rows_all),
        "association_rows": len(association_rows),
        "rows_with_detector_box": rows_with_box,
        "rows_with_detector_box_rate": rows_with_box / len(frame_summaries) if frame_summaries else 0.0,
        "rows_with_sam2_mask": rows_with_mask,
        "rows_with_sam2_mask_rate": rows_with_mask / len(frame_summaries) if frame_summaries else 0.0,
        "rows_with_candidate_association": rows_with_association,
        "rows_with_candidate_association_rate": rows_with_association / len(frame_summaries) if frame_summaries else 0.0,
        "associated_candidate_heading_count": associated_heading_count,
        "projected_pixel_inside_mask_count": projected_inside_mask_count,
        "projection_status_counts": dict(sorted(projection_counts.items())),
        "projection_anchor_status_counts": dict(sorted(projection_anchor_counts.items())),
        "projection_anchor_selected_offset_counts": dict(sorted(projection_anchor_offset_counts.items())),
        "detector_box_count_per_heading": {
            "min": min(detector_box_counts) if detector_box_counts else 0,
            "max": max(detector_box_counts) if detector_box_counts else 0,
            "mean": float(sum(detector_box_counts) / len(detector_box_counts)) if detector_box_counts else 0.0,
        },
        "debug_images_written": debug_count,
        "uses_gt_for_action": False,
        "output_files": {
            "detector_boxes": "detector_boxes.jsonl",
            "detector_masks": "detector_masks.jsonl",
            "detector_candidate_associations": "detector_candidate_associations.jsonl",
            "frame_summary": "frame_summary.jsonl",
            "summary": "summary.json",
        },
    }
    write_json(out / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run GroundingDINO + SAM2 on H001 post-view frames.")
    parser.add_argument("--frames", required=True)
    parser.add_argument("--frame-root", default=None)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--groundingdino-dir", required=True)
    parser.add_argument("--sam2-checkpoint", required=True)
    parser.add_argument("--sam2-config", default="configs/sam2.1/sam2.1_hiera_t.yaml")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--debug-root", default=None)
    parser.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-frame", type=int, default=5)
    parser.add_argument(
        "--candidate-point-field",
        default="position",
        choices=["position", "visit_position", "grounded_position"],
    )
    parser.add_argument("--grounded-point-height-m", type=float, default=0.8)
    parser.add_argument("--grounded-point-max-vertical-gap-m", type=float, default=2.0)
    parser.add_argument("--projection-anchor-height-offsets-m", type=parse_float_list, default=[0.0])
    parser.add_argument("--box-threshold", type=float, default=0.15)
    parser.add_argument("--text-threshold", type=float, default=0.15)
    parser.add_argument("--query-template", default="a {query}.")
    parser.add_argument("--max-headings-per-frame", type=int, default=0)
    parser.add_argument("--max-detector-boxes-per-heading", type=int, default=0)
    parser.add_argument("--max-masks-per-heading", type=int, default=5)
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
