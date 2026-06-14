import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
from PIL import Image


SCHEMA_VERSION = "h001.postview_score.v1"
LOCAL_CROP_SOURCE = "openai_clip_local_crop"
CENTER_FALLBACK_SOURCE = "openai_clip_center_crop_fallback"
DEFAULT_GROUNDED_POINT_HEIGHT_M = 0.8
DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M = 2.0


def slug(text: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return value or "query"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def finite_vector(value: Any, length: int) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) != length:
        return None
    out = [finite_float(v) for v in value]
    if any(v is None for v in out):
        return None
    return [float(v) for v in out]


def load_query_embedding(query_embeddings: Path, query: str) -> np.ndarray:
    path = query_embeddings / f"{slug(query)}.npy"
    if not path.exists():
        manifest_path = query_embeddings / "manifest.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            for row in manifest.get("queries", []):
                if str(row.get("query", "")).lower() == query.lower():
                    candidate_path = Path(str(row.get("embedding_path")))
                    path = query_embeddings / candidate_path.name
                    break
    if not path.exists():
        raise FileNotFoundError(f"missing query embedding for {query!r}: {path}")

    emb = np.asarray(np.load(path), dtype=np.float32).reshape(-1)
    norm = float(np.linalg.norm(emb))
    if norm <= 1e-8:
        raise ValueError(f"query embedding has near-zero norm: {path}")
    return emb / norm


def choose_device(device: str) -> str:
    import torch

    if device == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but not available")
    return device


def load_clip_model(model_name: str, device_arg: str) -> Tuple[Any, Any, str]:
    import clip

    device = choose_device(device_arg)
    model, preprocess = clip.load(model_name, device=device, jit=False)
    model.eval()
    return model, preprocess, device


def encode_crop_score(
    model: Any,
    preprocess: Any,
    device: str,
    crop: Image.Image,
    query_embedding: np.ndarray,
) -> float:
    import torch

    image_input = preprocess(crop.convert("RGB")).unsqueeze(0).to(device)
    with torch.no_grad():
        feats = model.encode_image(image_input).float()
        feats = feats / feats.norm(dim=-1, keepdim=True)
    image_embedding = feats.detach().cpu().numpy().astype(np.float32).reshape(-1)
    if image_embedding.shape[0] != query_embedding.shape[0]:
        raise ValueError(
            f"image embedding dim {image_embedding.shape[0]} does not match query dim {query_embedding.shape[0]}"
        )
    return float(np.dot(image_embedding, query_embedding))


def artifact_index(path: Path) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    indexed: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        scene_id = str(row.get("scene_id"))
        query = str(row.get("query"))
        candidates = list(row.get("candidates") or [])
        candidates.sort(key=lambda cand: finite_float(cand.get("score")) or -math.inf, reverse=True)
        indexed[(scene_id, query)] = candidates
    return indexed


def select_candidate_set(
    candidates: List[Dict[str, Any]],
    frame_candidate_id: Optional[str],
    tie_band: float,
    max_candidates: int,
) -> List[Dict[str, Any]]:
    if not candidates:
        return []
    top_score = finite_float(candidates[0].get("score")) or 0.0
    selected = [
        cand
        for cand in candidates
        if (finite_float(cand.get("score")) or -math.inf) >= top_score - tie_band
    ]

    if frame_candidate_id is not None and all(str(c.get("candidate_id")) != frame_candidate_id for c in selected):
        for cand in candidates:
            if str(cand.get("candidate_id")) == frame_candidate_id:
                selected.append(cand)
                break

    if max_candidates > 0 and len(selected) > max_candidates:
        trimmed = selected[:max_candidates]
        if frame_candidate_id is not None and all(str(c.get("candidate_id")) != frame_candidate_id for c in trimmed):
            frame_candidate = next((c for c in selected if str(c.get("candidate_id")) == frame_candidate_id), None)
            if frame_candidate is not None:
                trimmed[-1] = frame_candidate
        selected = trimmed
    return selected


def candidate_rank_lookup(candidates: List[Dict[str, Any]]) -> Dict[str, int]:
    return {str(candidate.get("candidate_id")): idx + 1 for idx, candidate in enumerate(candidates)}


def uncertainty_for(
    candidate: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    score_overrides: Optional[Dict[str, float]] = None,
    support_overrides: Optional[Dict[str, int]] = None,
) -> Dict[str, float]:
    score_overrides = score_overrides or {}
    support_overrides = support_overrides or {}

    scores = []
    for cand in candidates:
        candidate_id = str(cand.get("candidate_id"))
        score = score_overrides.get(candidate_id, finite_float(cand.get("score")) or 0.0)
        scores.append(float(score))
    scores.sort(reverse=True)

    candidate_id = str(candidate.get("candidate_id"))
    candidate_score = float(score_overrides.get(candidate_id, finite_float(candidate.get("score")) or 0.0))
    view_count = int(support_overrides.get(candidate_id, int(finite_float(candidate.get("view_count")) or 0)))
    top1 = scores[0] if scores else candidate_score
    top2 = scores[1] if len(scores) > 1 else 0.0
    score_uncertainty = max(0.0, min(1.0, 1.0 - candidate_score))
    margin_uncertainty = max(0.0, min(1.0, 1.0 - max(0.0, top1 - top2)))
    support_uncertainty = max(0.0, min(1.0, 1.0 - min(max(view_count, 0), 25) / 25.0))
    u_sem = (score_uncertainty + margin_uncertainty + support_uncertainty) / 3.0
    return {
        "top1_score": float(top1),
        "top2_score": float(top2),
        "score_uncertainty": float(score_uncertainty),
        "margin_uncertainty": float(margin_uncertainty),
        "view_count_uncertainty": float(support_uncertainty),
        "U_sem": float(u_sem),
    }


def grounded_candidate_point(
    candidate: Dict[str, Any],
    grounded_point_height_m: float = DEFAULT_GROUNDED_POINT_HEIGHT_M,
    grounded_point_max_vertical_gap_m: float = DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M,
) -> Optional[np.ndarray]:
    position = finite_vector(candidate.get("position"), 3)
    visit_position = finite_vector(candidate.get("visit_position"), 3)
    if position is None and visit_position is None:
        return None
    if position is None:
        return np.asarray(
            [
                float(visit_position[0]),
                float(visit_position[1]) + float(grounded_point_height_m),
                float(visit_position[2]),
            ],
            dtype=np.float64,
        )
    if visit_position is None:
        return np.asarray(position, dtype=np.float64)
    if abs(float(position[1]) - float(visit_position[1])) > float(grounded_point_max_vertical_gap_m):
        return np.asarray(
            [
                float(position[0]),
                float(visit_position[1]) + float(grounded_point_height_m),
                float(position[2]),
            ],
            dtype=np.float64,
        )
    return np.asarray(position, dtype=np.float64)


def candidate_point(
    candidate: Dict[str, Any],
    field: str,
    grounded_point_height_m: float = DEFAULT_GROUNDED_POINT_HEIGHT_M,
    grounded_point_max_vertical_gap_m: float = DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M,
) -> Optional[np.ndarray]:
    if field == "grounded_position":
        return grounded_candidate_point(
            candidate,
            grounded_point_height_m,
            grounded_point_max_vertical_gap_m,
        )
    fields = [field]
    for fallback in ("position", "visit_position"):
        if fallback not in fields:
            fields.append(fallback)
    for name in fields:
        values = finite_vector(candidate.get(name), 3)
        if values is not None:
            return np.asarray(values, dtype=np.float64)
    return None


def project_point(
    point_world: np.ndarray,
    world_from_camera: np.ndarray,
    width: int,
    height: int,
    hfov_deg: float,
    min_depth: float,
) -> Dict[str, Any]:
    if world_from_camera.shape != (4, 4):
        return {"projection_status": "missing_frame", "projected_pixel": None}
    camera_from_world = np.linalg.inv(world_from_camera)
    point_cam = camera_from_world @ np.asarray([point_world[0], point_world[1], point_world[2], 1.0])
    x, y, z = [float(v) for v in point_cam[:3]]
    forward = -z
    if forward <= min_depth:
        return {
            "projection_status": "behind_camera",
            "projected_pixel": None,
            "camera_point": [x, y, z],
            "camera_forward_m": float(forward),
        }

    focal = width / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))
    cx = (width - 1.0) / 2.0
    cy = (height - 1.0) / 2.0
    u = cx + focal * (x / forward)
    v = cy - focal * (y / forward)
    if not (0.0 <= u < width and 0.0 <= v < height):
        return {
            "projection_status": "out_of_fov",
            "projected_pixel": [float(u), float(v)],
            "camera_point": [x, y, z],
            "camera_forward_m": float(forward),
        }
    return {
        "projection_status": "visible",
        "projected_pixel": [float(u), float(v)],
        "camera_point": [x, y, z],
        "camera_forward_m": float(forward),
    }


def depth_check(
    depth: Optional[np.ndarray],
    pixel: Optional[List[float]],
    expected_depth: Optional[float],
    tolerance_m: float,
    window_px: int,
) -> Dict[str, Any]:
    if depth is None or pixel is None or expected_depth is None:
        return {"depth_check_status": "unavailable"}
    height, width = depth.shape[:2]
    u, v = int(round(pixel[0])), int(round(pixel[1]))
    if not (0 <= u < width and 0 <= v < height):
        return {"depth_check_status": "out_of_fov"}
    left = max(0, u - window_px)
    right = min(width, u + window_px + 1)
    top = max(0, v - window_px)
    bottom = min(height, v + window_px + 1)
    patch = np.asarray(depth[top:bottom, left:right], dtype=np.float32)
    valid = patch[np.isfinite(patch) & (patch > 0)]
    if valid.size == 0:
        return {"depth_check_status": "unavailable"}
    observed = float(np.median(valid))
    error = abs(observed - float(expected_depth))
    return {
        "depth_check_status": "consistent" if error <= tolerance_m else "depth_mismatch",
        "depth_observed_m": observed,
        "depth_expected_m": float(expected_depth),
        "depth_error_m": float(error),
    }


def crop_around(image: Image.Image, pixel: List[float], radius_px: int) -> Tuple[Image.Image, List[int]]:
    width, height = image.size
    u = int(round(pixel[0]))
    v = int(round(pixel[1]))
    left = max(0, u - radius_px)
    right = min(width, u + radius_px + 1)
    top = max(0, v - radius_px)
    bottom = min(height, v + radius_px + 1)
    if left >= right or top >= bottom:
        left, top, right, bottom = 0, 0, width, height
    return image.crop((left, top, right, bottom)), [int(left), int(top), int(right), int(bottom)]


def load_depth(path: Path) -> Optional[np.ndarray]:
    if not path.exists():
        return None
    depth = np.load(path)
    if depth.ndim == 3:
        depth = depth[:, :, 0]
    return np.asarray(depth, dtype=np.float32)


def score_frame_candidates(
    frame: Dict[str, Any],
    frame_root: Path,
    candidates: List[Dict[str, Any]],
    ranks: Dict[str, int],
    model: Any,
    preprocess: Any,
    device: str,
    query_embedding: np.ndarray,
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    rgb_path = frame_root / str(frame.get("rgb"))
    depth_path = frame_root / str(frame.get("depth"))
    metadata_path = frame_root / str(frame.get("metadata"))
    frame_candidate_id = str(frame.get("candidate_id")) if frame.get("candidate_id") is not None else None

    if not rgb_path.exists() or not metadata_path.exists():
        out = []
        for candidate in candidates:
            score_before = finite_float(candidate.get("score")) or 0.0
            fields = uncertainty_for(candidate, candidates)
            out.append(
                {
                    "candidate_id": str(candidate.get("candidate_id")),
                    "candidate_rank_before": ranks.get(str(candidate.get("candidate_id"))),
                    "score_before": float(score_before),
                    "score_after": float(score_before),
                    "score_delta": 0.0,
                    "U_sem_before": fields["U_sem"],
                    "U_sem_after": fields["U_sem"],
                    "support_before": int(finite_float(candidate.get("view_count")) or 0),
                    "support_after": int(finite_float(candidate.get("view_count")) or 0),
                    "support_delta": 0.0,
                    "projected_pixel": None,
                    "projection_status": "missing_frame",
                    "score_source": "not_used",
                }
            )
        return out

    image = Image.open(rgb_path).convert("RGB")
    width, height = image.size
    depth = load_depth(depth_path)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    resolution = metadata.get("camera_resolution")
    if isinstance(resolution, list) and len(resolution) == 2:
        height = int(resolution[0])
        width = int(resolution[1])
    hfov = float(metadata.get("camera_hfov", args.hfov))
    world_from_camera = np.asarray(metadata.get("vlmaps_camera_pose"), dtype=np.float64)

    rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        score_before = finite_float(candidate.get("score")) or 0.0
        support_before = int(finite_float(candidate.get("view_count")) or 0)
        before_fields = uncertainty_for(candidate, candidates)
        point = candidate_point(
            candidate,
            args.candidate_point_field,
            float(args.grounded_point_height_m),
            float(args.grounded_point_max_vertical_gap_m),
        )

        projection = {"projection_status": "missing_frame", "projected_pixel": None}
        if point is not None:
            projection = project_point(point, world_from_camera, width, height, hfov, args.min_projection_depth_m)

        score_source = LOCAL_CROP_SOURCE
        projection_note = None
        if (
            projection.get("projection_status") != "visible"
            and args.center_fallback_for_selected
            and frame_candidate_id is not None
            and candidate_id == frame_candidate_id
        ):
            projection = {
                "projection_status": "visible",
                "projected_pixel": [(width - 1.0) / 2.0, (height - 1.0) / 2.0],
                "camera_point": None,
                "camera_forward_m": None,
            }
            score_source = CENTER_FALLBACK_SOURCE
            projection_note = "center_fallback_for_observed_candidate"

        depth_info = depth_check(
            depth,
            projection.get("projected_pixel"),
            projection.get("camera_forward_m"),
            args.depth_tolerance_m,
            args.depth_window_px,
        )
        projection_status = str(projection.get("projection_status"))
        if (
            args.strict_depth_check
            and projection_status == "visible"
            and depth_info.get("depth_check_status") == "depth_mismatch"
        ):
            projection_status = "depth_mismatch"

        score_after = score_before
        raw_image_text_score = None
        crop_box = None
        if projection_status == "visible" and projection.get("projected_pixel") is not None:
            crop, crop_box = crop_around(image, projection["projected_pixel"], args.crop_radius_px)
            raw_image_text_score = encode_crop_score(model, preprocess, device, crop, query_embedding)
            score_after = raw_image_text_score

        support_after = support_before + 1 if projection_status == "visible" else support_before
        after_fields = uncertainty_for(
            candidate,
            candidates,
            score_overrides={candidate_id: float(score_after)},
            support_overrides={candidate_id: support_after},
        )

        row = {
            "candidate_id": candidate_id,
            "candidate_rank_before": ranks.get(candidate_id),
            "score_before": float(score_before),
            "score_after": float(score_after),
            "score_delta": float(score_after - score_before),
            "raw_image_text_score": raw_image_text_score,
            "score_calibration": "raw_clip_cosine",
            "U_sem_before": before_fields["U_sem"],
            "U_sem_after": after_fields["U_sem"],
            "support_before": support_before,
            "support_after": int(support_after),
            "support_delta": float(support_after - support_before),
            "projected_pixel": projection.get("projected_pixel"),
            "projection_status": projection_status,
            "score_source": score_source if projection_status == "visible" else "not_used",
            "crop_box_xyxy": crop_box,
            **depth_info,
        }
        if projection_note:
            row["projection_note"] = projection_note
        if args.include_camera_point and projection.get("camera_point") is not None:
            row["camera_point"] = projection.get("camera_point")
        rows.append(row)
    return rows


def update_summary(out: Path, score_summary: Dict[str, Any]) -> None:
    summary_path = out.parent / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {}
    summary["postview_scoring"] = score_summary
    summary["next_expected_file"] = "policy_revision_image_feature/summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def score_postview(args: argparse.Namespace) -> Dict[str, Any]:
    frames_path = Path(args.frames)
    frame_root = frames_path.parent
    candidate_rows = artifact_index(Path(args.candidate_artifact))
    frames = load_jsonl(frames_path)
    model, preprocess, device = load_clip_model(args.model, args.device)
    embedding_cache: Dict[str, np.ndarray] = {}

    output_rows: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    errors: List[Dict[str, Any]] = []

    for frame in frames:
        scene_id = str(frame.get("scene_id"))
        query = str(frame.get("query"))
        all_candidates = candidate_rows.get((scene_id, query), [])
        ranks = candidate_rank_lookup(all_candidates)
        selected_candidates = select_candidate_set(
            all_candidates,
            str(frame.get("candidate_id")) if frame.get("candidate_id") is not None else None,
            args.semantic_tie_band,
            args.max_candidates_per_frame,
        )

        try:
            if query not in embedding_cache:
                embedding_cache[query] = load_query_embedding(Path(args.query_embeddings), query)
            candidate_scores = score_frame_candidates(
                frame,
                frame_root,
                selected_candidates,
                ranks,
                model,
                preprocess,
                device,
                embedding_cache[query],
                args,
            )
        except Exception as exc:
            errors.append({"decision_id": frame.get("decision_id"), "error": repr(exc)})
            candidate_scores = []

        for row in candidate_scores:
            status_counts[str(row.get("projection_status"))] += 1
            source_counts[str(row.get("score_source"))] += 1

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
                "frame_rgb": frame.get("rgb"),
                "frame_depth": frame.get("depth"),
                "frame_metadata": frame.get("metadata"),
                "candidate_scores": candidate_scores,
            }
        )

    out = Path(args.out)
    write_jsonl(out, output_rows)

    rows_with_visible = sum(
        1
        for row in output_rows
        if any(score.get("projection_status") == "visible" for score in row.get("candidate_scores", []))
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
        "rows_with_visible_candidate": rows_with_visible,
        "visible_row_rate": float(rows_with_visible / len(output_rows)) if output_rows else 0.0,
        "projection_status_counts": dict(sorted(status_counts.items())),
        "score_source_counts": dict(sorted(source_counts.items())),
        "score_calibration": "raw_clip_cosine",
        "candidate_point_field": str(args.candidate_point_field),
        "grounded_point_height_m": float(args.grounded_point_height_m),
        "grounded_point_max_vertical_gap_m": float(args.grounded_point_max_vertical_gap_m),
        "uses_gt_for_action": False,
        "errors": errors,
    }
    update_summary(out, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score H001 post-view RGB crops with CLIP image-text features.")
    parser.add_argument("--frames", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--query-embeddings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="ViT-B/32")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-frame", type=int, default=10)
    parser.add_argument("--crop-radius-px", type=int, default=12)
    parser.add_argument("--depth-tolerance-m", type=float, default=0.75)
    parser.add_argument("--depth-window-px", type=int, default=2)
    parser.add_argument("--hfov", type=float, default=90.0)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    parser.add_argument(
        "--candidate-point-field",
        default="position",
        choices=["position", "visit_position", "grounded_position"],
    )
    parser.add_argument("--grounded-point-height-m", type=float, default=DEFAULT_GROUNDED_POINT_HEIGHT_M)
    parser.add_argument(
        "--grounded-point-max-vertical-gap-m",
        type=float,
        default=DEFAULT_GROUNDED_POINT_MAX_VERTICAL_GAP_M,
    )
    parser.add_argument("--strict-depth-check", action="store_true")
    parser.add_argument("--center-fallback-for-selected", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--include-camera-point", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = score_postview(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
