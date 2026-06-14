import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image

from h001_runtime.score_postview_v2 import load_heading_assets, parse_int_list, top_mean
from h001_runtime.score_postview_vlm import (
    artifact_index,
    candidate_point,
    candidate_rank_lookup,
    depth_check,
    encode_crop_score,
    finite_float,
    load_clip_model,
    load_jsonl,
    load_query_embedding,
    project_point,
    select_candidate_set,
    uncertainty_for,
)


SCHEMA_VERSION = "h001.postview_score.v3a_depth_mask"
SCORE_SOURCE = "openai_clip_depth_mask_object_crop"
SCORE_CALIBRATION = "object_mask_aggregate_raw_clip_cosine"


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def update_summary(out: Path, score_summary: Dict[str, Any]) -> None:
    summary_path = out.parent / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {}
    summary["postview_scoring_v3a_depth_mask"] = score_summary
    summary["next_expected_file"] = "postview_evidence_v3a_depth_mask_diagnostic/summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def valid_depth_values(depth: np.ndarray, left: int, top: int, right: int, bottom: int) -> np.ndarray:
    patch = np.asarray(depth[top:bottom, left:right], dtype=np.float32)
    return patch[np.isfinite(patch) & (patch > 0)]


def seed_depth(depth: np.ndarray, u: int, v: int, seed_window_px: int) -> Tuple[Optional[float], Optional[Tuple[int, int]]]:
    height, width = depth.shape[:2]
    if not (0 <= u < width and 0 <= v < height):
        return None, None

    for radius in [seed_window_px, seed_window_px * 2, seed_window_px * 4]:
        left = max(0, u - radius)
        right = min(width, u + radius + 1)
        top = max(0, v - radius)
        bottom = min(height, v + radius + 1)
        patch = np.asarray(depth[top:bottom, left:right], dtype=np.float32)
        valid = np.isfinite(patch) & (patch > 0)
        if not np.any(valid):
            continue

        yy, xx = np.nonzero(valid)
        abs_y = yy + top
        abs_x = xx + left
        distances = (abs_x - u) ** 2 + (abs_y - v) ** 2
        nearest = int(np.argmin(distances))
        seed_u = int(abs_x[nearest])
        seed_v = int(abs_y[nearest])

        values = patch[valid]
        return float(np.median(values)), (seed_u, seed_v)
    return None, None


def connected_depth_mask(
    depth: Optional[np.ndarray],
    projected_pixel: Optional[List[float]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    if depth is None or projected_pixel is None:
        return {"object_mask_valid": False, "mask_reject_reason": "missing_depth_or_projection"}

    height, width = depth.shape[:2]
    u = int(round(float(projected_pixel[0])))
    v = int(round(float(projected_pixel[1])))
    if not (0 <= u < width and 0 <= v < height):
        return {"object_mask_valid": False, "mask_reject_reason": "projected_pixel_outside_image"}

    seed, seed_pixel = seed_depth(depth, u, v, int(args.seed_window_px))
    if seed is None or seed_pixel is None:
        return {"object_mask_valid": False, "mask_reject_reason": "missing_seed_depth"}

    radius = int(args.mask_search_radius_px)
    left = max(0, u - radius)
    right = min(width, u + radius + 1)
    top = max(0, v - radius)
    bottom = min(height, v + radius + 1)
    patch = np.asarray(depth[top:bottom, left:right], dtype=np.float32)
    valid = np.isfinite(patch) & (patch > 0) & (np.abs(patch - seed) <= float(args.mask_depth_band_m))

    seed_u, seed_v = seed_pixel
    local_seed = (seed_v - top, seed_u - left)
    if not (0 <= local_seed[0] < valid.shape[0] and 0 <= local_seed[1] < valid.shape[1]):
        return {"object_mask_valid": False, "mask_reject_reason": "seed_outside_search_window"}
    if not bool(valid[local_seed]):
        valid[local_seed] = True

    component = np.zeros_like(valid, dtype=bool)
    stack = [local_seed]
    component[local_seed] = True
    while stack:
        cy, cx = stack.pop()
        for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
            if 0 <= ny < valid.shape[0] and 0 <= nx < valid.shape[1] and bool(valid[ny, nx]) and not bool(component[ny, nx]):
                component[ny, nx] = True
                stack.append((ny, nx))

    area = int(component.sum())
    image_area = int(width * height)
    area_ratio = float(area / image_area) if image_area else 0.0
    if area < int(args.min_mask_area_px):
        return {
            "object_mask_valid": False,
            "mask_reject_reason": "mask_too_small",
            "object_mask_area_px": area,
            "object_mask_area_ratio": area_ratio,
            "object_mask_depth_median": seed,
        }
    if area_ratio > float(args.max_mask_area_ratio):
        return {
            "object_mask_valid": False,
            "mask_reject_reason": "mask_too_large",
            "object_mask_area_px": area,
            "object_mask_area_ratio": area_ratio,
            "object_mask_depth_median": seed,
        }

    ys, xs = np.nonzero(component)
    crop_left = max(0, int(xs.min()) + left - int(args.mask_box_padding_px))
    crop_right = min(width, int(xs.max()) + left + int(args.mask_box_padding_px) + 1)
    crop_top = max(0, int(ys.min()) + top - int(args.mask_box_padding_px))
    crop_bottom = min(height, int(ys.max()) + top + int(args.mask_box_padding_px) + 1)

    full_mask = np.zeros((height, width), dtype=bool)
    full_mask[top:bottom, left:right] = component
    component_depth = np.asarray(depth[top:bottom, left:right], dtype=np.float32)[component]
    component_depth = component_depth[np.isfinite(component_depth) & (component_depth > 0)]
    depth_median = float(np.median(component_depth)) if component_depth.size else seed
    depth_mad = float(np.median(np.abs(component_depth - depth_median))) if component_depth.size else None

    return {
        "object_mask_valid": True,
        "mask_reject_reason": None,
        "object_mask": full_mask,
        "object_mask_box_xyxy": [int(crop_left), int(crop_top), int(crop_right), int(crop_bottom)],
        "object_mask_area_px": area,
        "object_mask_area_ratio": area_ratio,
        "object_mask_depth_median": depth_median,
        "object_mask_depth_mad": depth_mad,
        "object_mask_component_radius_px": radius,
        "object_mask_projection_in_component": bool(full_mask[v, u]),
        "seed_pixel": [int(seed_u), int(seed_v)],
        "seed_depth_m": seed,
    }


def masked_crop(image: Image.Image, mask: np.ndarray, box: List[int], background_value: int) -> Image.Image:
    left, top, right, bottom = [int(v) for v in box]
    rgb = np.asarray(image.convert("RGB"), dtype=np.uint8)
    crop_rgb = rgb[top:bottom, left:right].copy()
    crop_mask = mask[top:bottom, left:right]
    bg = np.full_like(crop_rgb, int(background_value), dtype=np.uint8)
    bg[crop_mask] = crop_rgb[crop_mask]
    return Image.fromarray(bg, mode="RGB")


def box_crop(image: Image.Image, box: List[int]) -> Image.Image:
    left, top, right, bottom = [int(v) for v in box]
    return image.crop((left, top, right, bottom)).convert("RGB")


def save_debug_images(
    debug_root: Optional[Path],
    debug_counter: int,
    max_debug_images: int,
    frame: Dict[str, Any],
    candidate_id: str,
    heading_id: str,
    mask: np.ndarray,
    masked: Image.Image,
) -> int:
    if debug_root is None or debug_counter >= max_debug_images:
        return debug_counter
    safe_candidate = candidate_id.replace("/", "_").replace(":", "_")
    out_dir = debug_root / str(frame.get("decision_id")) / safe_candidate
    out_dir.mkdir(parents=True, exist_ok=True)
    mask_image = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    mask_image.save(out_dir / f"{heading_id}_mask.png")
    masked.save(out_dir / f"{heading_id}_masked_crop.png")
    return debug_counter + 1


def projection_status_from_evidence(frame_evidence: List[Dict[str, Any]], action_eligible: bool) -> str:
    if action_eligible:
        return "visible"
    statuses = [str(row.get("projection_status")) for row in frame_evidence]
    if "mask_invalid" in statuses:
        return "mask_invalid"
    if "visible" in statuses:
        return "mask_invalid"
    if "out_of_fov" in statuses:
        return "out_of_fov"
    if "behind_camera" in statuses:
        return "behind_camera"
    if "missing_frame" in statuses:
        return "missing_frame"
    if "missing_candidate_point" in statuses:
        return "missing_candidate_point"
    return "not_used"


def score_candidate_v3a(
    candidate: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    rank: Optional[int],
    frame: Dict[str, Any],
    heading_assets: Dict[str, Dict[str, Any]],
    model: Any,
    preprocess: Any,
    device: str,
    query_embedding: np.ndarray,
    args: argparse.Namespace,
    debug_root: Optional[Path],
    debug_counter: int,
) -> Tuple[Dict[str, Any], int]:
    candidate_id = str(candidate.get("candidate_id"))
    score_before = finite_float(candidate.get("score")) or 0.0
    support_before = int(finite_float(candidate.get("view_count")) or 0)
    before_fields = uncertainty_for(candidate, candidates)
    point = candidate_point(candidate, args.candidate_point_field)

    frame_evidence: List[Dict[str, Any]] = []
    valid_scores: List[float] = []
    masked_scores: List[float] = []
    box_scores: List[float] = []
    valid_mask_count = 0
    heading_visible_count = 0
    object_mask_valid_count = 0
    best_record: Optional[Dict[str, Any]] = None

    if point is None:
        frame_evidence.append(
            {
                "heading_id": None,
                "projection_status": "missing_candidate_point",
                "crop_scores": [],
                "action_valid": False,
                "object_mask_valid": False,
            }
        )
    else:
        for heading in frame.get("rendered_headings", []):
            heading_id = str(heading.get("heading_id"))
            assets = heading_assets.get(heading_id)
            if assets is None:
                frame_evidence.append(
                    {
                        "heading_id": heading_id,
                        "target_candidate_id": heading.get("target_candidate_id"),
                        "rotation_source": heading.get("rotation_source"),
                        "projection_status": "missing_frame",
                        "crop_scores": [],
                        "action_valid": False,
                        "object_mask_valid": False,
                    }
                )
                continue

            projection = project_point(
                point,
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

            if projection_status == "visible":
                heading_visible_count += 1

            mask_info: Dict[str, Any] = {"object_mask_valid": False, "mask_reject_reason": "not_visible"}
            crop_scores: List[Dict[str, Any]] = []
            action_valid = False
            if projection_status == "visible":
                mask_info = connected_depth_mask(assets["depth"], projected_pixel, args)
                if mask_info.get("object_mask_valid") is True:
                    object_mask_valid_count += 1
                    mask = mask_info["object_mask"]
                    box = mask_info["object_mask_box_xyxy"]
                    masked = masked_crop(assets["image"], mask, box, int(args.mask_background_value))
                    boxed = box_crop(assets["image"], box)
                    masked_raw = encode_crop_score(model, preprocess, device, masked, query_embedding)
                    box_raw = encode_crop_score(model, preprocess, device, boxed, query_embedding)
                    valid_scores.append(float(masked_raw))
                    masked_scores.append(float(masked_raw))
                    box_scores.append(float(box_raw))
                    valid_mask_count += 1
                    action_valid = True
                    crop_scores.append(
                        {
                            "crop_type": "depth_mask_object",
                            "crop_box_xyxy": box,
                            "raw_clip_cosine": float(masked_raw),
                        }
                    )
                    crop_scores.append(
                        {
                            "crop_type": "depth_mask_box",
                            "crop_box_xyxy": box,
                            "raw_clip_cosine": float(box_raw),
                        }
                    )
                    debug_counter = save_debug_images(
                        debug_root,
                        debug_counter,
                        int(args.max_debug_images),
                        frame,
                        candidate_id,
                        heading_id,
                        mask,
                        masked,
                    )
                    if best_record is None or masked_raw > float(best_record["masked_raw_clip_cosine"]):
                        best_record = {
                            "heading_id": heading_id,
                            "crop_box_xyxy": box,
                            "projected_pixel": projected_pixel,
                            "masked_raw_clip_cosine": float(masked_raw),
                            "box_raw_clip_cosine": float(box_raw),
                            "object_mask_area_px": int(mask_info.get("object_mask_area_px") or 0),
                            "object_mask_area_ratio": float(mask_info.get("object_mask_area_ratio") or 0.0),
                        }
                else:
                    projection_status = "mask_invalid"

            evidence_mask_info = {
                key: value
                for key, value in mask_info.items()
                if key != "object_mask"
            }
            frame_evidence.append(
                {
                    "heading_id": heading_id,
                    "target_candidate_id": heading.get("target_candidate_id"),
                    "rotation_source": heading.get("rotation_source"),
                    "yaw_offset_deg": heading.get("yaw_offset_deg"),
                    "projection_status": projection_status,
                    "projected_pixel": projected_pixel,
                    "camera_forward_m": projection.get("camera_forward_m"),
                    "depth_check_status": depth_info.get("depth_check_status"),
                    "depth_error_m": depth_info.get("depth_error_m"),
                    "crop_scores": crop_scores,
                    "action_valid": bool(action_valid),
                    **evidence_mask_info,
                }
            )

    aggregate_score = max(valid_scores) if valid_scores else None
    action_eligible = aggregate_score is not None and valid_mask_count > 0
    support_after = support_before + valid_mask_count if action_eligible else support_before
    score_after = float(aggregate_score) if aggregate_score is not None else float(score_before)
    after_fields = uncertainty_for(
        candidate,
        candidates,
        score_overrides={candidate_id: score_after} if aggregate_score is not None else None,
        support_overrides={candidate_id: support_after},
    )
    mask_score_std = float(statistics.pstdev(masked_scores)) if len(masked_scores) > 1 else 0.0
    box_mean = float(statistics.mean(box_scores)) if box_scores else None
    masked_mean = float(statistics.mean(masked_scores)) if masked_scores else None
    mask_score_margin_to_box = None if masked_mean is None or box_mean is None else float(masked_mean - box_mean)

    return (
        {
            "candidate_id": candidate_id,
            "candidate_rank_before": rank,
            "score_before": float(score_before),
            "score_after": float(score_after),
            "score_delta": float(score_after - score_before) if aggregate_score is not None else 0.0,
            "raw_image_text_score": float(aggregate_score) if aggregate_score is not None else None,
            "score_calibration": SCORE_CALIBRATION,
            "U_sem_before": before_fields["U_sem"],
            "U_sem_after": after_fields["U_sem"],
            "support_before": support_before,
            "support_after": int(support_after),
            "support_delta": float(support_after - support_before),
            "projected_pixel": best_record.get("projected_pixel") if best_record else None,
            "projection_status": projection_status_from_evidence(frame_evidence, bool(action_eligible)),
            "score_source": SCORE_SOURCE if action_eligible else "not_used",
            "action_eligible": bool(action_eligible),
            "center_fallback_score_diagnostic": None,
            "center_fallback_used_for_action": False,
            "heading_visible_count": int(heading_visible_count),
            "depth_consistent_count": sum(
                1 for row in frame_evidence if row.get("depth_check_status") == "consistent"
            ),
            "valid_crop_count": int(valid_mask_count),
            "object_mask_valid": bool(action_eligible),
            "object_mask_valid_count": int(object_mask_valid_count),
            "object_mask_area_px": best_record.get("object_mask_area_px") if best_record else None,
            "object_mask_area_ratio": best_record.get("object_mask_area_ratio") if best_record else None,
            "mask_view_count": int(valid_mask_count),
            "mask_score_std": float(mask_score_std),
            "mask_score_margin_to_box": mask_score_margin_to_box,
            "masked_raw_clip_cosine": float(max(masked_scores)) if masked_scores else None,
            "box_raw_clip_cosine": float(max(box_scores)) if box_scores else None,
            "background_suppressed_raw_clip_cosine": float(max(masked_scores)) if masked_scores else None,
            "best_local_raw_clip_cosine": float(max(masked_scores)) if masked_scores else None,
            "mean_top2_local_raw_clip_cosine": top_mean(masked_scores, 2),
            "best_heading_id": best_record.get("heading_id") if best_record else None,
            "best_crop_box_xyxy": best_record.get("crop_box_xyxy") if best_record else None,
            "best_crop_radius_px": None,
            "frame_evidence": frame_evidence,
        },
        debug_counter,
    )


def score_frame_v3a(
    frame: Dict[str, Any],
    frame_root: Path,
    candidates: List[Dict[str, Any]],
    ranks: Dict[str, int],
    model: Any,
    preprocess: Any,
    device: str,
    query_embedding: np.ndarray,
    args: argparse.Namespace,
    debug_root: Optional[Path],
    debug_counter: int,
) -> Tuple[List[Dict[str, Any]], int]:
    heading_assets: Dict[str, Dict[str, Any]] = {}
    for heading in frame.get("rendered_headings", []):
        heading_id = str(heading.get("heading_id"))
        assets = load_heading_assets(frame_root, heading)
        if assets is not None:
            heading_assets[heading_id] = assets

    out: List[Dict[str, Any]] = []
    for candidate in candidates:
        row, debug_counter = score_candidate_v3a(
            candidate,
            candidates,
            ranks.get(str(candidate.get("candidate_id"))),
            frame,
            heading_assets,
            model,
            preprocess,
            device,
            query_embedding,
            args,
            debug_root,
            debug_counter,
        )
        out.append(row)
    return out, debug_counter


def score_postview_v3a(args: argparse.Namespace) -> Dict[str, Any]:
    frames_path = Path(args.frames)
    frame_root = frames_path.parent
    candidate_rows = artifact_index(Path(args.candidate_artifact))
    frames = load_jsonl(frames_path)
    if int(args.max_frames) > 0:
        frames = frames[: int(args.max_frames)]
    model, preprocess, device = load_clip_model(args.model, args.device)
    embedding_cache: Dict[str, np.ndarray] = {}
    debug_root = Path(args.debug_root) if args.debug_root else Path(args.out).parent / "mask_debug"

    output_rows: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    action_eligible_count = 0
    valid_mask_count = 0
    errors: List[Dict[str, Any]] = []
    debug_counter = 0

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

        try:
            if query not in embedding_cache:
                embedding_cache[query] = load_query_embedding(Path(args.query_embeddings), query)
            candidate_scores, debug_counter = score_frame_v3a(
                frame,
                frame_root,
                selected_candidates,
                ranks,
                model,
                preprocess,
                device,
                embedding_cache[query],
                args,
                debug_root,
                debug_counter,
            )
        except Exception as exc:
            errors.append({"decision_id": frame.get("decision_id"), "error": repr(exc)})
            candidate_scores = []

        for row in candidate_scores:
            status_counts[str(row.get("projection_status"))] += 1
            source_counts[str(row.get("score_source"))] += 1
            action_eligible_count += int(bool(row.get("action_eligible")))
            valid_mask_count += int(row.get("valid_crop_count") or 0)

        output_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "decision_id": frame.get("decision_id"),
                "run_id": frame.get("run_id"),
                "episode_id": frame.get("episode_id"),
                "episode_key": frame.get("episode_key"),
                "policy": frame.get("policy"),
                "scene_id": scene_id,
                "query": query,
                "evidence_update_mode": "image_feature",
                "uses_gt_for_action": False,
                "frame_schema_version": frame.get("schema_version"),
                "rendered_heading_count": len(frame.get("rendered_headings", [])),
                "candidate_scores": candidate_scores,
            }
        )

    out = Path(args.out)
    write_jsonl(out, output_rows)

    rows_with_action_eligible = sum(
        1
        for row in output_rows
        if any(score.get("action_eligible") is True for score in row.get("candidate_scores", []))
    )
    rows_with_object_mask_valid = sum(
        1
        for row in output_rows
        if any(score.get("object_mask_valid") is True for score in row.get("candidate_scores", []))
    )
    total_candidate_scores = sum(len(row.get("candidate_scores", [])) for row in output_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "ok": len(errors) == 0 and len(output_rows) == len(frames),
        "frames": str(frames_path),
        "candidate_artifact": str(args.candidate_artifact),
        "query_embeddings": str(args.query_embeddings),
        "out": str(out),
        "model": str(args.model),
        "device": device,
        "rows_requested": len(frames),
        "rows_scored": len(output_rows),
        "candidate_score_count": total_candidate_scores,
        "action_eligible_candidate_count": int(action_eligible_count),
        "rows_with_action_eligible_candidate": int(rows_with_action_eligible),
        "action_eligible_row_rate": float(rows_with_action_eligible / len(output_rows)) if output_rows else 0.0,
        "rows_with_object_mask_valid_candidate": int(rows_with_object_mask_valid),
        "object_mask_valid_row_rate": float(rows_with_object_mask_valid / len(output_rows)) if output_rows else 0.0,
        "valid_crop_count": int(valid_mask_count),
        "valid_mask_count": int(valid_mask_count),
        "object_mask_valid_count": int(valid_mask_count),
        "projection_status_counts": dict(sorted(status_counts.items())),
        "score_source_counts": dict(sorted(source_counts.items())),
        "score_calibration": SCORE_CALIBRATION,
        "center_fallback_used_for_action": False,
        "uses_gt_for_action": False,
        "debug_images_written": int(debug_counter),
        "errors": errors,
    }
    update_summary(out, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score H001 post-view v3a depth-mask object crops with CLIP.")
    parser.add_argument("--frames", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--query-embeddings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--debug-root", default=None)
    parser.add_argument("--model", default="ViT-B/32")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-frame", type=int, default=10)
    parser.add_argument("--max-frames", type=int, default=0)
    parser.add_argument("--depth-tolerance-m", type=float, default=0.75)
    parser.add_argument("--depth-window-px", type=int, default=2)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    parser.add_argument("--candidate-point-field", default="position", choices=["position", "visit_position"])
    parser.add_argument("--seed-window-px", type=int, default=2)
    parser.add_argument("--mask-search-radius-px", type=int, default=48)
    parser.add_argument("--mask-depth-band-m", type=float, default=0.45)
    parser.add_argument("--mask-box-padding-px", type=int, default=8)
    parser.add_argument("--min-mask-area-px", type=int, default=80)
    parser.add_argument("--max-mask-area-ratio", type=float, default=0.35)
    parser.add_argument("--mask-background-value", type=int, default=127)
    parser.add_argument("--max-debug-images", type=int, default=40)
    parser.add_argument("--crop-radii-px", type=parse_int_list, default=[12, 24, 36])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = score_postview_v3a(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
