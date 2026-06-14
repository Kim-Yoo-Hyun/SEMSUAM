import argparse
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
from PIL import Image

from h001_runtime.score_postview_vlm import (
    artifact_index,
    candidate_point,
    candidate_rank_lookup,
    crop_around,
    depth_check,
    encode_crop_score,
    finite_float,
    load_clip_model,
    load_depth,
    load_jsonl,
    load_query_embedding,
    project_point,
    select_candidate_set,
    uncertainty_for,
)


SCHEMA_VERSION = "h001.postview_score.v2"
SCORE_SOURCE = "openai_clip_multiview_local_crop"
SCORE_CALIBRATION = "aggregate_raw_clip_cosine"


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def parse_int_list(text: str) -> List[int]:
    values = [int(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one comma-separated integer")
    if any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("crop radii must be positive")
    return values


def top_mean(values: List[float], k: int) -> Optional[float]:
    if not values:
        return None
    chosen = sorted(values, reverse=True)[: max(1, k)]
    return float(statistics.mean(chosen))


def projection_status_from_evidence(frame_evidence: List[Dict[str, Any]], action_eligible: bool) -> str:
    if action_eligible:
        return "visible"
    statuses = [str(row.get("projection_status")) for row in frame_evidence]
    if "depth_mismatch" in statuses:
        return "depth_mismatch"
    if "visible" in statuses:
        return "depth_mismatch"
    if "out_of_fov" in statuses:
        return "out_of_fov"
    if "behind_camera" in statuses:
        return "behind_camera"
    if "missing_frame" in statuses:
        return "missing_frame"
    return "not_used"


def load_heading_assets(frame_root: Path, heading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rgb_path = frame_root / str(heading.get("rgb"))
    depth_path = frame_root / str(heading.get("depth"))
    metadata_path = frame_root / str(heading.get("metadata"))
    if not rgb_path.exists() or not metadata_path.exists():
        return None
    image = Image.open(rgb_path).convert("RGB")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    resolution = metadata.get("camera_resolution")
    width, height = image.size
    if isinstance(resolution, list) and len(resolution) == 2:
        height = int(resolution[0])
        width = int(resolution[1])
    return {
        "image": image,
        "depth": load_depth(depth_path),
        "metadata": metadata,
        "width": width,
        "height": height,
        "hfov": float(metadata.get("camera_hfov", 90.0)),
        "world_from_camera": np.asarray(metadata.get("vlmaps_camera_pose"), dtype=np.float64),
    }


def score_candidate_v2(
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
) -> Dict[str, Any]:
    candidate_id = str(candidate.get("candidate_id"))
    score_before = finite_float(candidate.get("score")) or 0.0
    support_before = int(finite_float(candidate.get("view_count")) or 0)
    before_fields = uncertainty_for(candidate, candidates)
    point = candidate_point(candidate, args.candidate_point_field)

    frame_evidence: List[Dict[str, Any]] = []
    valid_scores: List[float] = []
    valid_crop_count = 0
    heading_visible_count = 0
    depth_consistent_count = 0
    best_record: Optional[Dict[str, Any]] = None

    if point is None:
        frame_evidence.append(
            {
                "heading_id": None,
                "projection_status": "missing_candidate_point",
                "crop_scores": [],
                "action_valid": False,
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
                if depth_info.get("depth_check_status") == "consistent":
                    depth_consistent_count += 1

            action_valid_heading = projection_status == "visible" and projected_pixel is not None
            if args.strict_depth_check and depth_info.get("depth_check_status") != "consistent":
                action_valid_heading = False
                if projection_status == "visible":
                    projection_status = "depth_mismatch"

            crop_scores: List[Dict[str, Any]] = []
            if action_valid_heading and projected_pixel is not None:
                for radius in args.crop_radii_px:
                    crop, crop_box = crop_around(assets["image"], projected_pixel, int(radius))
                    raw = encode_crop_score(model, preprocess, device, crop, query_embedding)
                    crop_row = {
                        "crop_radius_px": int(radius),
                        "crop_box_xyxy": crop_box,
                        "raw_clip_cosine": float(raw),
                    }
                    crop_scores.append(crop_row)
                    valid_scores.append(float(raw))
                    valid_crop_count += 1
                    if best_record is None or raw > float(best_record["raw_clip_cosine"]):
                        best_record = {
                            "heading_id": heading_id,
                            "crop_radius_px": int(radius),
                            "crop_box_xyxy": crop_box,
                            "projected_pixel": projected_pixel,
                            "raw_clip_cosine": float(raw),
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
                    "action_valid": bool(crop_scores),
                }
            )

    aggregate_score = max(valid_scores) if valid_scores else None
    action_eligible = aggregate_score is not None and valid_crop_count > 0
    support_after = support_before + valid_crop_count if action_eligible else support_before
    score_after = float(aggregate_score) if aggregate_score is not None else float(score_before)
    after_fields = uncertainty_for(
        candidate,
        candidates,
        score_overrides={candidate_id: score_after} if aggregate_score is not None else None,
        support_overrides={candidate_id: support_after},
    )

    return {
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
        "depth_consistent_count": int(depth_consistent_count),
        "valid_crop_count": int(valid_crop_count),
        "best_local_raw_clip_cosine": float(max(valid_scores)) if valid_scores else None,
        "mean_top2_local_raw_clip_cosine": top_mean(valid_scores, 2),
        "best_heading_id": best_record.get("heading_id") if best_record else None,
        "best_crop_box_xyxy": best_record.get("crop_box_xyxy") if best_record else None,
        "best_crop_radius_px": best_record.get("crop_radius_px") if best_record else None,
        "frame_evidence": frame_evidence,
    }


def score_frame_v2(
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
    heading_assets: Dict[str, Dict[str, Any]] = {}
    for heading in frame.get("rendered_headings", []):
        heading_id = str(heading.get("heading_id"))
        assets = load_heading_assets(frame_root, heading)
        if assets is not None:
            heading_assets[heading_id] = assets
    return [
        score_candidate_v2(
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
        )
        for candidate in candidates
    ]


def update_summary(out: Path, score_summary: Dict[str, Any]) -> None:
    summary_path = out.parent / "summary.json"
    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    else:
        summary = {}
    summary["postview_scoring_v2"] = score_summary
    summary["next_expected_file"] = "postview_evidence_v2_diagnostic/summary.json"
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")


def score_postview_v2(args: argparse.Namespace) -> Dict[str, Any]:
    frames_path = Path(args.frames)
    frame_root = frames_path.parent
    candidate_rows = artifact_index(Path(args.candidate_artifact))
    frames = load_jsonl(frames_path)
    model, preprocess, device = load_clip_model(args.model, args.device)
    embedding_cache: Dict[str, np.ndarray] = {}

    output_rows: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    action_eligible_count = 0
    valid_crop_count = 0
    errors: List[Dict[str, Any]] = []

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
            candidate_scores = score_frame_v2(
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
            action_eligible_count += int(bool(row.get("action_eligible")))
            valid_crop_count += int(row.get("valid_crop_count") or 0)

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
        "valid_crop_count": int(valid_crop_count),
        "projection_status_counts": dict(sorted(status_counts.items())),
        "score_source_counts": dict(sorted(source_counts.items())),
        "score_calibration": SCORE_CALIBRATION,
        "center_fallback_used_for_action": False,
        "uses_gt_for_action": False,
        "errors": errors,
    }
    update_summary(out, summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score H001 post-view v2 multi-heading local crops with CLIP.")
    parser.add_argument("--frames", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--query-embeddings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--model", default="ViT-B/32")
    parser.add_argument("--device", default="auto", choices=["auto", "cpu", "cuda"])
    parser.add_argument("--semantic-tie-band", type=float, default=0.01)
    parser.add_argument("--max-candidates-per-frame", type=int, default=10)
    parser.add_argument("--crop-radii-px", type=parse_int_list, default=[12, 24, 36])
    parser.add_argument("--depth-tolerance-m", type=float, default=0.75)
    parser.add_argument("--depth-window-px", type=int, default=2)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    parser.add_argument("--candidate-point-field", default="position", choices=["position", "visit_position"])
    parser.add_argument("--strict-depth-check", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--center-fallback-for-action", action=argparse.BooleanOptionalAction, default=False)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.center_fallback_for_action:
        raise ValueError("postview_evidence_v2 does not allow center fallback for action-facing scores")
    summary = score_postview_v2(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
