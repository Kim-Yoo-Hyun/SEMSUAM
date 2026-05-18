import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from h001_runtime.score_postview_vlm import artifact_index, depth_check, finite_float, load_depth, project_point


SCHEMA_VERSION = "h001.postview_visibility_diagnostic.v2.1"
POINT_FIELDS = ("position", "visit_position")


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def finite_vector(value: Any, length: int) -> Optional[np.ndarray]:
    if not isinstance(value, list) or len(value) != length:
        return None
    values = [finite_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return np.asarray(values, dtype=np.float64)


def exact_candidate_point(candidate: Dict[str, Any], field: str) -> Optional[np.ndarray]:
    return finite_vector(candidate.get(field), 3)


def label_index(rows: List[Dict[str, Any]], policy: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is not None and candidate_id is not None:
            index[(str(episode_key), str(candidate_id))] = row
    return index


def episode_index(rows: List[Dict[str, Any]], policy: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        if episode_key is not None:
            index[str(episode_key)] = row
    return index


def frame_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        decision_id = row.get("decision_id")
        if decision_id is not None:
            out[str(decision_id)] = row
    return out


def load_heading_asset(frame_root: Path, heading: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    metadata_path = frame_root / str(heading.get("metadata"))
    depth_path = frame_root / str(heading.get("depth"))
    if not metadata_path.exists():
        return None
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    resolution = metadata.get("camera_resolution")
    if isinstance(resolution, list) and len(resolution) == 2:
        height = int(resolution[0])
        width = int(resolution[1])
    else:
        width = int(metadata.get("width") or 0)
        height = int(metadata.get("height") or 0)
    if width <= 0 or height <= 0:
        width, height = 640, 480
    return {
        "depth": load_depth(depth_path),
        "width": width,
        "height": height,
        "hfov": float(metadata.get("camera_hfov", 90.0)),
        "world_from_camera": np.asarray(metadata.get("vlmaps_camera_pose"), dtype=np.float64),
    }


def summarize_status(frame_evidence: List[Dict[str, Any]], key: str) -> str:
    statuses = [str(row.get(key)) for row in frame_evidence]
    if "visible" in statuses:
        return "visible"
    if "depth_mismatch" in statuses:
        return "depth_mismatch"
    if "out_of_fov" in statuses:
        return "out_of_fov"
    if "behind_camera" in statuses:
        return "behind_camera"
    if "missing_frame" in statuses:
        return "missing_frame"
    if "missing_candidate_point" in statuses:
        return "missing_candidate_point"
    return "not_visible"


def stats(values: Iterable[Optional[float]]) -> Dict[str, Any]:
    valid = sorted(float(value) for value in values if value is not None and math.isfinite(float(value)))
    if not valid:
        return {"count": 0}
    mid = len(valid) // 2
    if len(valid) % 2:
        median = valid[mid]
    else:
        median = (valid[mid - 1] + valid[mid]) / 2.0
    return {
        "count": len(valid),
        "min": valid[0],
        "max": valid[-1],
        "mean": float(statistics.mean(valid)),
        "median": float(median),
        "p90": float(valid[min(len(valid) - 1, math.floor(0.9 * (len(valid) - 1)))]),
    }


def bool_label(value: Any) -> str:
    if value is True:
        return "correct"
    if value is False:
        return "wrong"
    return "unknown"


def candidate_projection_rows(
    score_row: Dict[str, Any],
    frame: Dict[str, Any],
    candidates_by_id: Dict[str, Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    baseline_episodes: Dict[str, Dict[str, Any]],
    frame_root: Path,
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    heading_assets: Dict[str, Optional[Dict[str, Any]]] = {}
    for heading in frame.get("rendered_headings", []):
        heading_id = str(heading.get("heading_id"))
        heading_assets[heading_id] = load_heading_asset(frame_root, heading)

    episode_key = str(score_row.get("episode_key"))
    baseline_episode = baseline_episodes.get(episode_key, {})
    candidate_rows: List[Dict[str, Any]] = []
    heading_rows: List[Dict[str, Any]] = []

    for score in score_row.get("candidate_scores", []):
        candidate_id = str(score.get("candidate_id"))
        candidate = candidates_by_id.get(candidate_id)
        label = labels.get((episode_key, candidate_id), {})
        candidate_correct = label.get("candidate_correct")
        is_top_before = int(score.get("candidate_rank_before") or -1) == 1

        for point_field in POINT_FIELDS:
            evidence_rows: List[Dict[str, Any]] = []
            point = exact_candidate_point(candidate or {}, point_field)
            if candidate is None or point is None:
                evidence_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "decision_id": score_row.get("decision_id"),
                        "episode_key": episode_key,
                        "scene_id": score_row.get("scene_id"),
                        "query": score_row.get("query"),
                        "candidate_id": candidate_id,
                        "candidate_rank_before": score.get("candidate_rank_before"),
                        "point_field": point_field,
                        "heading_id": None,
                        "target_candidate_id": None,
                        "yaw_offset_deg": None,
                        "relaxed_projection_status": "missing_candidate_point",
                        "strict_projection_status": "missing_candidate_point",
                        "projected_pixel": None,
                        "camera_forward_m": None,
                        "depth_check_status": "unavailable",
                        "depth_error_m": None,
                        "relaxed_action_valid": False,
                        "strict_action_valid": False,
                        "candidate_correct": candidate_correct,
                        "is_top_before": is_top_before,
                        "no_reobserve_wrong_goal_visit": baseline_episode.get("wrong_goal_visit"),
                        "uses_gt_for_action": False,
                        "uses_gt_for_analysis": candidate_correct is not None,
                    }
                )
            else:
                for heading in frame.get("rendered_headings", []):
                    heading_id = str(heading.get("heading_id"))
                    assets = heading_assets.get(heading_id)
                    if assets is None:
                        projection_status = "missing_frame"
                        projection: Dict[str, Any] = {"projected_pixel": None, "camera_forward_m": None}
                        depth_info = {"depth_check_status": "unavailable"}
                    else:
                        projection = project_point(
                            point,
                            assets["world_from_camera"],
                            int(assets["width"]),
                            int(assets["height"]),
                            float(assets["hfov"]),
                            float(args.min_projection_depth_m),
                        )
                        projection_status = str(projection.get("projection_status"))
                        depth_info = depth_check(
                            assets["depth"],
                            projection.get("projected_pixel"),
                            projection.get("camera_forward_m"),
                            float(args.depth_tolerance_m),
                            int(args.depth_window_px),
                        )

                    relaxed_action_valid = projection_status == "visible"
                    strict_action_valid = (
                        relaxed_action_valid and depth_info.get("depth_check_status") == "consistent"
                    )
                    strict_status = projection_status
                    if projection_status == "visible" and not strict_action_valid:
                        strict_status = "depth_mismatch"

                    evidence_rows.append(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "decision_id": score_row.get("decision_id"),
                            "episode_key": episode_key,
                            "scene_id": score_row.get("scene_id"),
                            "query": score_row.get("query"),
                            "candidate_id": candidate_id,
                            "candidate_rank_before": score.get("candidate_rank_before"),
                            "point_field": point_field,
                            "heading_id": heading_id,
                            "target_candidate_id": heading.get("target_candidate_id"),
                            "yaw_offset_deg": heading.get("yaw_offset_deg"),
                            "relaxed_projection_status": projection_status,
                            "strict_projection_status": strict_status,
                            "projected_pixel": projection.get("projected_pixel"),
                            "camera_forward_m": projection.get("camera_forward_m"),
                            "depth_check_status": depth_info.get("depth_check_status"),
                            "depth_error_m": depth_info.get("depth_error_m"),
                            "relaxed_action_valid": bool(relaxed_action_valid),
                            "strict_action_valid": bool(strict_action_valid),
                            "candidate_correct": candidate_correct,
                            "is_top_before": is_top_before,
                            "no_reobserve_wrong_goal_visit": baseline_episode.get("wrong_goal_visit"),
                            "uses_gt_for_action": False,
                            "uses_gt_for_analysis": candidate_correct is not None,
                        }
                    )

            heading_rows.extend(evidence_rows)
            depth_errors = [finite_float(row.get("depth_error_m")) for row in evidence_rows]
            strict_count = sum(1 for row in evidence_rows if row.get("strict_action_valid") is True)
            relaxed_count = sum(1 for row in evidence_rows if row.get("relaxed_action_valid") is True)
            candidate_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "decision_id": score_row.get("decision_id"),
                    "episode_key": episode_key,
                    "scene_id": score_row.get("scene_id"),
                    "query": score_row.get("query"),
                    "candidate_id": candidate_id,
                    "candidate_rank_before": score.get("candidate_rank_before"),
                    "is_top_before": is_top_before,
                    "point_field": point_field,
                    "current_v2_action_eligible": score.get("action_eligible") is True,
                    "strict_action_eligible": strict_count > 0,
                    "relaxed_action_eligible": relaxed_count > 0,
                    "strict_action_valid_heading_count": strict_count,
                    "relaxed_action_valid_heading_count": relaxed_count,
                    "heading_count": len(evidence_rows),
                    "strict_projection_status": summarize_status(evidence_rows, "strict_projection_status"),
                    "relaxed_projection_status": summarize_status(evidence_rows, "relaxed_projection_status"),
                    "strict_status_counts": dict(Counter(str(row.get("strict_projection_status")) for row in evidence_rows)),
                    "relaxed_status_counts": dict(
                        Counter(str(row.get("relaxed_projection_status")) for row in evidence_rows)
                    ),
                    "depth_check_status_counts": dict(Counter(str(row.get("depth_check_status")) for row in evidence_rows)),
                    "depth_error_stats_m": stats(depth_errors),
                    "candidate_correct": candidate_correct,
                    "candidate_correct_source": label.get("candidate_correct_source"),
                    "selected_for_goal_before": label.get("selected_for_goal"),
                    "wrong_goal_visit_before": label.get("wrong_goal_visit"),
                    "no_reobserve_wrong_goal_visit": baseline_episode.get("wrong_goal_visit"),
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": candidate_correct is not None,
                }
            )

    return candidate_rows, heading_rows


def build_row_summaries(candidate_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        grouped[(str(row.get("episode_key")), str(row.get("point_field")))].append(row)

    out: List[Dict[str, Any]] = []
    for (episode_key, point_field), rows in sorted(grouped.items()):
        strict_rows = [row for row in rows if row.get("strict_action_eligible") is True]
        relaxed_rows = [row for row in rows if row.get("relaxed_action_eligible") is True]
        strict_correct = [row for row in strict_rows if row.get("candidate_correct") is True]
        relaxed_correct = [row for row in relaxed_rows if row.get("candidate_correct") is True]
        top = next((row for row in rows if row.get("is_top_before") is True), None)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "decision_id": rows[0].get("decision_id"),
                "scene_id": rows[0].get("scene_id"),
                "query": rows[0].get("query"),
                "point_field": point_field,
                "candidate_count": len(rows),
                "strict_action_eligible_candidate_count": len(strict_rows),
                "relaxed_action_eligible_candidate_count": len(relaxed_rows),
                "strict_action_eligible_correct_count": len(strict_correct),
                "relaxed_action_eligible_correct_count": len(relaxed_correct),
                "has_strict_action_eligible_candidate": bool(strict_rows),
                "has_relaxed_action_eligible_candidate": bool(relaxed_rows),
                "has_strict_action_eligible_correct": bool(strict_correct),
                "has_relaxed_action_eligible_correct": bool(relaxed_correct),
                "top_before_candidate_id": top.get("candidate_id") if top else None,
                "top_before_correct": top.get("candidate_correct") if top else None,
                "top_before_strict_action_eligible": top.get("strict_action_eligible") if top else None,
                "top_before_relaxed_action_eligible": top.get("relaxed_action_eligible") if top else None,
                "no_reobserve_wrong_goal_visit": rows[0].get("no_reobserve_wrong_goal_visit"),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return out


def summarize_candidate_rows(candidate_rows: List[Dict[str, Any]], row_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    summary: Dict[str, Any] = {}
    for point_field in POINT_FIELDS:
        rows = [row for row in candidate_rows if row.get("point_field") == point_field]
        summaries = [row for row in row_summaries if row.get("point_field") == point_field]
        wrong_goal_rows = [row for row in summaries if row.get("no_reobserve_wrong_goal_visit") is True]
        strict_action = [row for row in rows if row.get("strict_action_eligible") is True]
        relaxed_action = [row for row in rows if row.get("relaxed_action_eligible") is True]
        strict_position_mismatches = [
            row
            for row in rows
            if point_field == "position"
            and bool(row.get("current_v2_action_eligible")) != bool(row.get("strict_action_eligible"))
        ]
        summary[point_field] = {
            "candidate_rows": len(rows),
            "score_rows": len(summaries),
            "strict_action_eligible_candidate_count": len(strict_action),
            "relaxed_action_eligible_candidate_count": len(relaxed_action),
            "strict_action_eligible_correct_candidate_count": sum(
                1 for row in strict_action if row.get("candidate_correct") is True
            ),
            "relaxed_action_eligible_correct_candidate_count": sum(
                1 for row in relaxed_action if row.get("candidate_correct") is True
            ),
            "rows_with_strict_action_eligible_candidate": sum(
                1 for row in summaries if row.get("has_strict_action_eligible_candidate") is True
            ),
            "rows_with_relaxed_action_eligible_candidate": sum(
                1 for row in summaries if row.get("has_relaxed_action_eligible_candidate") is True
            ),
            "strict_action_eligible_row_rate": (
                sum(1 for row in summaries if row.get("has_strict_action_eligible_candidate") is True) / len(summaries)
                if summaries
                else 0.0
            ),
            "relaxed_action_eligible_row_rate": (
                sum(1 for row in summaries if row.get("has_relaxed_action_eligible_candidate") is True) / len(summaries)
                if summaries
                else 0.0
            ),
            "rows_with_strict_action_eligible_correct_candidate": sum(
                1 for row in summaries if row.get("has_strict_action_eligible_correct") is True
            ),
            "rows_with_relaxed_action_eligible_correct_candidate": sum(
                1 for row in summaries if row.get("has_relaxed_action_eligible_correct") is True
            ),
            "no_reobserve_wrong_goal_rows": len(wrong_goal_rows),
            "wrong_goal_rows_with_strict_action_eligible_correct_candidate": sum(
                1 for row in wrong_goal_rows if row.get("has_strict_action_eligible_correct") is True
            ),
            "wrong_goal_rows_with_relaxed_action_eligible_correct_candidate": sum(
                1 for row in wrong_goal_rows if row.get("has_relaxed_action_eligible_correct") is True
            ),
            "strict_projection_status_counts": dict(Counter(str(row.get("strict_projection_status")) for row in rows)),
            "relaxed_projection_status_counts": dict(Counter(str(row.get("relaxed_projection_status")) for row in rows)),
            "strict_position_current_action_mismatch_count": len(strict_position_mismatches),
        }
    return summary


def query_breakdown(candidate_rows: List[Dict[str, Any]], row_summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for point_field in POINT_FIELDS:
        rows_by_query: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        summaries_by_query: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for row in candidate_rows:
            if row.get("point_field") == point_field:
                rows_by_query[str(row.get("query"))].append(row)
        for row in row_summaries:
            if row.get("point_field") == point_field:
                summaries_by_query[str(row.get("query"))].append(row)

        out[point_field] = {}
        for query, rows in sorted(rows_by_query.items()):
            summaries = summaries_by_query.get(query, [])
            wrong_goal_rows = [row for row in summaries if row.get("no_reobserve_wrong_goal_visit") is True]
            out[point_field][query] = {
                "candidate_rows": len(rows),
                "score_rows": len(summaries),
                "strict_action_eligible_candidate_count": sum(
                    1 for row in rows if row.get("strict_action_eligible") is True
                ),
                "relaxed_action_eligible_candidate_count": sum(
                    1 for row in rows if row.get("relaxed_action_eligible") is True
                ),
                "rows_with_strict_action_eligible_candidate": sum(
                    1 for row in summaries if row.get("has_strict_action_eligible_candidate") is True
                ),
                "rows_with_relaxed_action_eligible_candidate": sum(
                    1 for row in summaries if row.get("has_relaxed_action_eligible_candidate") is True
                ),
                "rows_with_strict_action_eligible_correct_candidate": sum(
                    1 for row in summaries if row.get("has_strict_action_eligible_correct") is True
                ),
                "rows_with_relaxed_action_eligible_correct_candidate": sum(
                    1 for row in summaries if row.get("has_relaxed_action_eligible_correct") is True
                ),
                "no_reobserve_wrong_goal_rows": len(wrong_goal_rows),
                "wrong_goal_rows_with_strict_action_eligible_correct_candidate": sum(
                    1 for row in wrong_goal_rows if row.get("has_strict_action_eligible_correct") is True
                ),
                "wrong_goal_rows_with_relaxed_action_eligible_correct_candidate": sum(
                    1 for row in wrong_goal_rows if row.get("has_relaxed_action_eligible_correct") is True
                ),
                "strict_projection_status_counts": dict(
                    Counter(str(row.get("strict_projection_status")) for row in rows)
                ),
                "relaxed_projection_status_counts": dict(
                    Counter(str(row.get("relaxed_projection_status")) for row in rows)
                ),
                "depth_error_stats_by_correctness": depth_error_stats(rows),
            }
    return out


def depth_error_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Optional[float]]] = defaultdict(list)
    for row in rows:
        label = bool_label(row.get("candidate_correct"))
        values = row.get("depth_error_stats_m") or {}
        if values.get("count", 0):
            grouped[label].append(finite_float(values.get("median")))
    return {label: stats(values) for label, values in sorted(grouped.items())}


def heading_depth_error_stats(heading_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[Optional[float]]] = defaultdict(list)
    for row in heading_rows:
        if row.get("relaxed_projection_status") != "visible":
            continue
        key = f"{row.get('point_field')}:{bool_label(row.get('candidate_correct'))}:{row.get('depth_check_status')}"
        grouped[key].append(finite_float(row.get("depth_error_m")))
    return {key: stats(values) for key, values in sorted(grouped.items())}


def recommendations(field_summary: Dict[str, Any], args: argparse.Namespace) -> List[str]:
    out: List[str] = []
    position = field_summary.get("position", {})
    visit = field_summary.get("visit_position", {})
    min_row_rate = float(args.min_action_eligible_row_rate)
    baseline_wrong_goal_correct = int(args.baseline_wrong_goal_visible_correct)

    if (
        position.get("relaxed_action_eligible_row_rate", 0.0) >= min_row_rate
        or position.get("wrong_goal_rows_with_relaxed_action_eligible_correct_candidate", 0)
        >= baseline_wrong_goal_correct
    ):
        out.append("run_relaxed_position_rescoring")

    if (
        visit.get("strict_action_eligible_row_rate", 0.0) > position.get("strict_action_eligible_row_rate", 0.0)
        or visit.get("wrong_goal_rows_with_strict_action_eligible_correct_candidate", 0)
        > position.get("wrong_goal_rows_with_strict_action_eligible_correct_candidate", 0)
    ):
        out.append("run_strict_visit_rescoring")

    if (
        visit.get("relaxed_action_eligible_row_rate", 0.0) >= min_row_rate
        or visit.get("wrong_goal_rows_with_relaxed_action_eligible_correct_candidate", 0)
        >= baseline_wrong_goal_correct
    ):
        out.append("consider_relaxed_visit_rescoring_after_first_two")

    if not out:
        out.append("do_not_rescore_yet_review_viewpoint_or_heading_export")
    return out


def run(args: argparse.Namespace) -> Dict[str, Any]:
    postview_scores = load_jsonl(Path(args.postview_scores))
    postview_frames = load_jsonl(Path(args.postview_frames))
    candidate_decisions = load_jsonl(Path(args.candidate_decisions))
    episodes = load_jsonl(Path(args.episodes))
    candidates = artifact_index(Path(args.candidate_artifact))
    frames = frame_index(postview_frames)
    labels = label_index(candidate_decisions, args.policy)
    baseline_episodes = episode_index(episodes, args.baseline_policy)
    frame_root = Path(args.frame_root) if args.frame_root else Path(args.postview_frames).parent

    candidate_rows: List[Dict[str, Any]] = []
    heading_rows: List[Dict[str, Any]] = []
    missing_frame_count = 0
    for score_row in postview_scores:
        frame = frames.get(str(score_row.get("decision_id")))
        if frame is None:
            missing_frame_count += 1
            continue
        candidate_list = candidates.get((str(score_row.get("scene_id")), str(score_row.get("query"))), [])
        candidates_by_id = {str(candidate.get("candidate_id")): candidate for candidate in candidate_list}
        crows, hrows = candidate_projection_rows(
            score_row,
            frame,
            candidates_by_id,
            labels,
            baseline_episodes,
            frame_root,
            args,
        )
        candidate_rows.extend(crows)
        heading_rows.extend(hrows)

    row_summaries = build_row_summaries(candidate_rows)
    field_summary = summarize_candidate_rows(candidate_rows, row_summaries)
    qbreakdown = query_breakdown(candidate_rows, row_summaries)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "postview_scores": str(args.postview_scores),
        "postview_frames": str(args.postview_frames),
        "candidate_artifact": str(args.candidate_artifact),
        "candidate_decisions": str(args.candidate_decisions),
        "episodes": str(args.episodes),
        "out_root": str(args.out_root),
        "policy": args.policy,
        "baseline_policy": args.baseline_policy,
        "split_role": "calibration",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "score_rows": len(postview_scores),
        "frame_rows": len(postview_frames),
        "missing_frame_count": missing_frame_count,
        "candidate_visibility_rows": len(candidate_rows),
        "heading_visibility_rows": len(heading_rows),
        "depth_tolerance_m": float(args.depth_tolerance_m),
        "depth_window_px": int(args.depth_window_px),
        "min_projection_depth_m": float(args.min_projection_depth_m),
        "field_summary": field_summary,
        "heading_depth_error_stats": heading_depth_error_stats(heading_rows),
        "recommended_next_variants": recommendations(field_summary, args),
        "output_files": {
            "candidate_visibility_table": "candidate_visibility_table.jsonl",
            "heading_visibility_table": "heading_visibility_table.jsonl",
            "row_visibility_summary": "row_visibility_summary.jsonl",
            "query_visibility_breakdown": "query_visibility_breakdown.json",
            "summary": "summary.json",
        },
    }

    out = Path(args.out_root)
    write_jsonl(out / "candidate_visibility_table.jsonl", candidate_rows)
    write_jsonl(out / "heading_visibility_table.jsonl", heading_rows)
    write_jsonl(out / "row_visibility_summary.jsonl", row_summaries)
    write_json(out / "query_visibility_breakdown.json", qbreakdown)
    write_json(out / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze H001 post-view v2.1 projection and depth coverage.")
    parser.add_argument("--postview-scores", required=True)
    parser.add_argument("--postview-frames", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--episodes", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--frame-root", default=None)
    parser.add_argument("--policy", default="EvidenceGatedSemanticOnly")
    parser.add_argument("--baseline-policy", default="NoReobserve")
    parser.add_argument("--depth-tolerance-m", type=float, default=0.75)
    parser.add_argument("--depth-window-px", type=int, default=2)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    parser.add_argument("--baseline-wrong-goal-visible-correct", type=int, default=6)
    parser.add_argument("--min-action-eligible-row-rate", type=float, default=0.70)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
