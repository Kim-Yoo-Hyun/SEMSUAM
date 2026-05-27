import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_detector_association_failure_diagnostic.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def counter_dict(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def numeric_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    numeric_values: List[float] = []
    for value in values:
        if isinstance(value, (int, float)):
            numeric_values.append(float(value))
    if not numeric_values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(numeric_values),
        "min": min(numeric_values),
        "max": max(numeric_values),
        "mean": mean(numeric_values),
        "median": median(numeric_values),
    }


def group_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (str(row.get("decision_id")), str(row.get("target_candidate_id") or row.get("candidate_id")))


def request_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (str(row.get("rival_identity_request_id")), str(row.get("episode_key")), str(row.get("query")))


def index_rows(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[group_key(row)] = row
    return indexed


def heading_index(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        base_key = group_key(row)
        for heading in row.get("rendered_headings") or []:
            indexed[(base_key[0], base_key[1], str(heading.get("heading_id")))] = heading
    return indexed


def validity_index(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[request_key(row)] = row
    return indexed


def candidate_label(validity_row: Optional[Dict[str, Any]], candidate_id: str) -> Dict[str, Any]:
    if not validity_row:
        return {
            "analysis_only_candidate_correct": None,
            "analysis_only_wrong_goal_visit": None,
            "analysis_only_candidate_set_taxonomy": None,
        }
    for candidate in validity_row.get("analysis_only_candidates") or []:
        if str(candidate.get("candidate_id")) == candidate_id:
            return {
                "analysis_only_candidate_correct": candidate.get("analysis_only_candidate_correct"),
                "analysis_only_wrong_goal_visit": candidate.get("analysis_only_wrong_goal_visit"),
                "analysis_only_candidate_set_taxonomy": validity_row.get("analysis_only_candidate_set_taxonomy"),
            }
    return {
        "analysis_only_candidate_correct": None,
        "analysis_only_wrong_goal_visit": None,
        "analysis_only_candidate_set_taxonomy": validity_row.get("analysis_only_candidate_set_taxonomy"),
    }


def classify_group(rows: List[Dict[str, Any]], frame_row: Optional[Dict[str, Any]]) -> str:
    if frame_row and frame_row.get("has_detector_box") is False:
        return "detector_box_missing"
    if frame_row and frame_row.get("has_sam2_mask") is False:
        return "sam2_mask_missing"
    if any(row.get("associated_to_candidate") is True for row in rows):
        return "associated_success"

    visible = [row for row in rows if row.get("projection_status") == "visible"]
    if not visible:
        return "projection_never_visible"

    inside_mask = [row for row in visible if row.get("projected_pixel_inside_mask") is True]
    inside_box = [row for row in visible if row.get("projected_pixel_inside_box") is True]
    if inside_mask and all(row.get("depth_check_status") == "depth_mismatch" for row in inside_mask):
        return "mask_overlap_depth_mismatch_only"
    if inside_box and not inside_mask:
        return "box_overlap_mask_reject"
    if not inside_box and not inside_mask:
        return "visible_projection_no_detector_overlap"
    return "visible_unassociated_other"


def summarize_heading_alignment(
    rows: List[Dict[str, Any]],
    headings: Dict[Tuple[str, str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    rotation_sources: Counter[str] = Counter()
    yaw_offsets: List[float] = []
    visible_by_rotation: Counter[str] = Counter()
    associated_by_rotation: Counter[str] = Counter()
    for row in rows:
        key = (group_key(row)[0], group_key(row)[1], str(row.get("heading_id")))
        heading = headings.get(key, {})
        rotation_source = str(heading.get("rotation_source") or "unknown")
        rotation_sources[rotation_source] += 1
        if isinstance(heading.get("yaw_offset_deg"), (int, float)):
            yaw_offsets.append(float(heading["yaw_offset_deg"]))
        if row.get("projection_status") == "visible":
            visible_by_rotation[rotation_source] += 1
        if row.get("associated_to_candidate") is True:
            associated_by_rotation[rotation_source] += 1
    return {
        "rotation_source_counts": dict(sorted(rotation_sources.items())),
        "visible_by_rotation_source": dict(sorted(visible_by_rotation.items())),
        "associated_by_rotation_source": dict(sorted(associated_by_rotation.items())),
        "yaw_offset_deg": numeric_stats(yaw_offsets),
    }


def build_diagnostic_rows(
    associations: List[Dict[str, Any]],
    frame_rows: Dict[Tuple[str, str], Dict[str, Any]],
    plan_rows: Dict[Tuple[str, str], Dict[str, Any]],
    headings: Dict[Tuple[str, str, str], Dict[str, Any]],
    validity_rows: Dict[Tuple[str, str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in associations:
        grouped[group_key(row)].append(row)

    diagnostic_rows: List[Dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        sample = rows[0]
        frame_row = frame_rows.get(key)
        plan_row = plan_rows.get(key)
        validity_row = validity_rows.get(request_key(sample))
        label = candidate_label(validity_row, key[1])
        mechanism = classify_group(rows, frame_row)
        visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
        associated_rows = [row for row in rows if row.get("associated_to_candidate") is True]
        inside_box_rows = [row for row in rows if row.get("projected_pixel_inside_box") is True]
        inside_mask_rows = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
        depth_mismatch_rows = [row for row in rows if row.get("depth_check_status") == "depth_mismatch"]
        strict_depth_rows = [row for row in rows if row.get("depth_check_status") == "consistent"]
        heading_info = summarize_heading_alignment(rows, headings)

        diagnostic_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "decision_id": key[0],
                "candidate_id": key[1],
                "target_candidate_id": sample.get("target_candidate_id"),
                "rival_identity_request_id": sample.get("rival_identity_request_id"),
                "expanded_retrieval_request_id": sample.get("expanded_retrieval_request_id"),
                "episode_key": sample.get("episode_key"),
                "scene_key": sample.get("scene_key"),
                "query": sample.get("query"),
                "expanded_candidate_rank": sample.get("expanded_candidate_rank"),
                "target_semantic_rank": sample.get("target_semantic_rank"),
                "target_semantic_score": sample.get("target_semantic_score"),
                "target_support_score": sample.get("target_support_score"),
                "target_positive_support": sample.get("target_positive_support"),
                "analysis_only_candidate_correct": label["analysis_only_candidate_correct"],
                "analysis_only_wrong_goal_visit": label["analysis_only_wrong_goal_visit"],
                "analysis_only_candidate_set_taxonomy": label["analysis_only_candidate_set_taxonomy"],
                "failure_mechanism": mechanism,
                "has_detector_box": None if frame_row is None else frame_row.get("has_detector_box"),
                "has_sam2_mask": None if frame_row is None else frame_row.get("has_sam2_mask"),
                "has_candidate_association": bool(associated_rows),
                "heading_rows": len(rows),
                "visible_heading_rows": len(visible_rows),
                "associated_heading_rows": len(associated_rows),
                "inside_box_heading_rows": len(inside_box_rows),
                "inside_mask_heading_rows": len(inside_mask_rows),
                "depth_mismatch_heading_rows": len(depth_mismatch_rows),
                "depth_consistent_heading_rows": len(strict_depth_rows),
                "projection_status_counts": counter_dict(row.get("projection_status") for row in rows),
                "depth_check_status_counts": counter_dict(row.get("depth_check_status") for row in rows),
                "depth_error_m": numeric_stats(row.get("depth_error_m") for row in rows),
                "box_center_distance_px": numeric_stats(row.get("box_center_distance_px") for row in rows),
                "best_box_score": numeric_stats(row.get("best_box_score") for row in rows),
                "standoff_direction_source": sample.get("standoff_direction_source"),
                "target_distance_from_viewpoint_m": sample.get("target_distance_from_viewpoint_m"),
                "standoff_snap_distance": sample.get("standoff_snap_distance"),
                "standoff_target_horizontal_distance": sample.get("standoff_target_horizontal_distance"),
                "viewpoint_source": sample.get("viewpoint_source"),
                "plan_viewpoint_id": None if plan_row is None else plan_row.get("viewpoint_id"),
                "heading_alignment": heading_info,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": bool(validity_rows),
            }
        )
    return diagnostic_rows


def summarize(rows: List[Dict[str, Any]], association_rows: List[Dict[str, Any]], has_validity: bool) -> Dict[str, Any]:
    total = len(rows)
    associated = [row for row in rows if row.get("failure_mechanism") == "associated_success"]
    failed = [row for row in rows if row.get("failure_mechanism") != "associated_success"]
    no_projection = [row for row in rows if row.get("failure_mechanism") == "projection_never_visible"]
    depth_blocked = [row for row in rows if row.get("failure_mechanism") == "mask_overlap_depth_mismatch_only"]
    detector_available = [
        row for row in rows if row.get("has_detector_box") is True and row.get("has_sam2_mask") is True
    ]
    failed_with_detector_available = [
        row
        for row in failed
        if row.get("has_detector_box") is True and row.get("has_sam2_mask") is True
    ]
    correct_rows = [row for row in rows if row.get("analysis_only_candidate_correct") is True]
    wrong_goal_rows = [row for row in rows if row.get("analysis_only_wrong_goal_visit") is True]
    associated_correct_rows = [
        row
        for row in associated
        if row.get("analysis_only_candidate_correct") is True
    ]
    associated_wrong_goal_rows = [
        row
        for row in associated
        if row.get("analysis_only_wrong_goal_visit") is True
    ]
    failure_mechanism_counts = Counter(str(row.get("failure_mechanism")) for row in rows)
    by_query: Dict[str, Dict[str, int]] = defaultdict(dict)
    for query, query_rows in sorted(group_by(rows, "query").items()):
        by_query[query] = counter_dict(row.get("failure_mechanism") for row in query_rows)
    by_scene: Dict[str, Dict[str, int]] = defaultdict(dict)
    for scene, scene_rows in sorted(group_by(rows, "scene_key").items()):
        by_scene[scene] = counter_dict(row.get("failure_mechanism") for row in scene_rows)

    frame_gate_passed = total > 0 and len(association_rows) == total * 4
    failure_rows_accounted = sum(failure_mechanism_counts.values()) == total
    detector_box_missing = failure_mechanism_counts.get("detector_box_missing", 0)
    mask_missing = failure_mechanism_counts.get("sam2_mask_missing", 0)
    dominant_no_projection = ratio(len(no_projection), total) or 0.0
    depth_revision_rate = ratio(len(depth_blocked), total) or 0.0

    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_observation_rows": total,
        "association_heading_rows": len(association_rows),
        "expected_heading_rows": total * 4,
        "associated_candidate_rows": len(associated),
        "failed_candidate_rows": len(failed),
        "candidate_association_rate": ratio(len(associated), total),
        "failure_mechanism_counts": dict(sorted(failure_mechanism_counts.items())),
        "projection_status_counts": counter_dict(row.get("projection_status") for row in association_rows),
        "depth_check_status_counts": counter_dict(row.get("depth_check_status") for row in association_rows),
        "query_failure_mechanism_counts": dict(by_query),
        "scene_failure_mechanism_counts": dict(by_scene),
        "detector_available_rows": len(detector_available),
        "failed_rows_with_detector_available": len(failed_with_detector_available),
        "detector_box_missing_rows": detector_box_missing,
        "sam2_mask_missing_rows": mask_missing,
        "analysis_only_correct_candidate_rows": len(correct_rows) if has_validity else None,
        "analysis_only_wrong_goal_candidate_rows": len(wrong_goal_rows) if has_validity else None,
        "analysis_only_associated_correct_rows": len(associated_correct_rows) if has_validity else None,
        "analysis_only_associated_wrong_goal_rows": len(associated_wrong_goal_rows) if has_validity else None,
        "gate": {
            "diagnostic_gate_passed": frame_gate_passed and failure_rows_accounted,
            "heading_rows_match_four_per_candidate": frame_gate_passed,
            "failure_rows_accounted": failure_rows_accounted,
            "threshold_tuning_allowed": False,
            "viewpoint_revision_required": dominant_no_projection >= 0.5,
            "association_depth_revision_required": depth_revision_rate >= 0.05,
            "detector_availability_is_primary_blocker": detector_box_missing > 0 or mask_missing > 0,
            "fresh_validation_allowed": False,
        },
        "interpretation": {
            "facts": [
                "This diagnostic reads already generated detector/SAM2 association rows, frame summaries, and observation plans.",
                "It does not rerun detector, segmenter, navigation, or ObjectNav evaluation.",
                "The optional candidate-set validity file is used only for analysis-only labels.",
            ],
            "agent_inference": [
                "If projection_never_visible dominates while detector boxes and masks are available, the next change should target viewpoint or projection geometry before threshold tuning.",
                "If mask_overlap_depth_mismatch_only appears, a separate depth-association tolerance or point-height diagnostic is needed before changing the policy objective.",
            ],
            "user_decision_needed": [],
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": has_validity,
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "expanded_retrieval_detector_failure_rows.jsonl",
            "summary": "expanded_retrieval_detector_failure_summary.json",
        },
    }


def group_by(rows: List[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key))].append(row)
    return grouped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    associations = load_jsonl(Path(args.associations))
    detector_frame_summary = load_jsonl(Path(args.detector_frame_summary))
    plan = load_jsonl(Path(args.plan))
    rendered_frame_summary = load_jsonl(Path(args.frame_summary)) if args.frame_summary else []
    validity = load_jsonl(Path(args.candidate_set_validity)) if args.candidate_set_validity else []

    diagnostic_rows = build_diagnostic_rows(
        associations=associations,
        frame_rows=index_rows(detector_frame_summary),
        plan_rows=index_rows(plan),
        headings=heading_index(rendered_frame_summary),
        validity_rows=validity_index(validity),
    )
    summary = summarize(diagnostic_rows, associations, bool(validity))
    summary.update(
        {
            "input_files": {
                "associations": str(args.associations),
                "detector_frame_summary": str(args.detector_frame_summary),
                "frame_summary": str(args.frame_summary) if args.frame_summary else None,
                "plan": str(args.plan),
                "candidate_set_validity": str(args.candidate_set_validity) if args.candidate_set_validity else None,
            },
            "out_root": str(out_root),
        }
    )
    write_jsonl(out_root / "expanded_retrieval_detector_failure_rows.jsonl", diagnostic_rows)
    write_json(out_root / "expanded_retrieval_detector_failure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose expanded-retrieval detector candidate-association failures before rule changes."
    )
    parser.add_argument("--associations", required=True)
    parser.add_argument("--detector-frame-summary", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--frame-summary")
    parser.add_argument("--candidate-set-validity")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
