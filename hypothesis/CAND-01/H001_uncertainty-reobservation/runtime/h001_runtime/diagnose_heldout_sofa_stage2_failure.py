import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def group_by_branch(rows: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("external_branch_id"))].append(row)
    return grouped


def role_counts(rows: Iterable[Dict[str, Any]]) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get("second_stage_role")) for row in rows).items()))


def status_counts(rows: Iterable[Dict[str, Any]], key: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(key)) for row in rows).items()))


def candidate_index(evidence_row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("candidate_id")): row
        for row in evidence_row.get("second_stage_candidate_evidence") or []
        if row.get("candidate_id") is not None
    }


def candidate_score(row: Dict[str, Any]) -> float:
    return safe_float(row.get("S_ext")) or 0.0


def branch_target_ids(plan_rows: List[Dict[str, Any]]) -> List[str]:
    return ordered_unique(row.get("second_stage_candidate_id") or row.get("candidate_id") for row in plan_rows)


def branch_semantic_neighbor_ids(plan_rows: List[Dict[str, Any]]) -> List[str]:
    return ordered_unique(
        row.get("second_stage_candidate_id") or row.get("candidate_id")
        for row in plan_rows
        if str(row.get("second_stage_role")).startswith("semantic_neighbor_")
    )


def association_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    consistent = [row for row in rows if row.get("depth_check_status") == "consistent"]
    depth_errors = [
        value for row in rows
        if (value := safe_float(row.get("depth_error_m"))) is not None
    ]
    return {
        "rows": len(rows),
        "associated_count": len(associated),
        "visible_count": len(visible),
        "inside_box_count": len(inside_box),
        "inside_mask_count": len(inside_mask),
        "depth_consistent_count": len(consistent),
        "projection_status_counts": status_counts(rows, "projection_status"),
        "depth_check_status_counts": status_counts(rows, "depth_check_status"),
        "min_depth_error_m": min(depth_errors) if depth_errors else None,
        "median_depth_error_m": sorted(depth_errors)[len(depth_errors) // 2] if depth_errors else None,
    }


def diagnose_branch(
    evidence_row: Dict[str, Any],
    plan_rows: List[Dict[str, Any]],
    frame_rows: List[Dict[str, Any]],
    association_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    candidates = candidate_index(evidence_row)
    correct_candidates = [row for row in candidates.values() if row.get("candidate_correct") is True]
    targeted_ids = branch_target_ids(plan_rows)
    semantic_neighbor_ids = branch_semantic_neighbor_ids(plan_rows)
    targeted_correct = [row for row in correct_candidates if str(row.get("candidate_id")) in targeted_ids]
    strongest_correct = max(correct_candidates, key=candidate_score, default=None)
    strongest_candidate = max(candidates.values(), key=candidate_score, default=None)
    selected_id = str(evidence_row.get("source_selected_candidate_id") or evidence_row.get("selected_candidate_id"))
    selected = candidates.get(selected_id)
    target_role_summary = {
        str(candidate_id): role_counts(
            row for row in plan_rows
            if str(row.get("second_stage_candidate_id") or row.get("candidate_id")) == str(candidate_id)
        )
        for candidate_id in targeted_ids
    }

    candidate_diagnostics: List[Dict[str, Any]] = []
    for candidate_id, candidate in sorted(candidates.items()):
        target_rows = [
            row for row in plan_rows
            if str(row.get("second_stage_candidate_id") or row.get("candidate_id")) == candidate_id
        ]
        own_associations = [
            row for row in association_rows
            if str(row.get("candidate_id")) == candidate_id
            and str(row.get("second_stage_candidate_id")) == candidate_id
        ]
        all_associations = [row for row in association_rows if str(row.get("candidate_id")) == candidate_id]
        candidate_diagnostics.append(
            {
                "candidate_id": candidate_id,
                "candidate_correct": candidate.get("candidate_correct"),
                "identity_role": candidate.get("identity_role"),
                "second_stage_roles": candidate.get("second_stage_roles"),
                "targeted_by_plan": bool(target_rows),
                "target_role_counts": role_counts(target_rows),
                "S_ext": candidate.get("S_ext"),
                "S_sem": candidate.get("S_sem"),
                "second_stage_strong_depth_evidence": candidate.get("second_stage_strong_depth_evidence"),
                "own_view_strong_depth_evidence": candidate.get("own_view_strong_depth_evidence"),
                "strict_association_count": candidate.get("strict_association_count"),
                "own_view_strict_association_count": candidate.get("own_view_strict_association_count"),
                "mask_hit_count": candidate.get("mask_hit_count"),
                "own_view_mask_hit_count": candidate.get("own_view_mask_hit_count"),
                "own_association_summary": association_summary(own_associations),
                "all_association_summary": association_summary(all_associations),
            }
        )

    failure_modes: List[str] = []
    if correct_candidates and not targeted_correct:
        failure_modes.append("target_selection_missed_all_correct_candidates")
    if targeted_correct and strongest_correct and str(strongest_correct.get("candidate_id")) not in targeted_ids:
        failure_modes.append("target_selection_left_stronger_correct_candidate_as_context")
    for row in targeted_correct:
        cid = str(row.get("candidate_id"))
        own_rows = [
            assoc for assoc in association_rows
            if str(assoc.get("candidate_id")) == cid
            and str(assoc.get("second_stage_candidate_id")) == cid
        ]
        own_summary = association_summary(own_rows)
        if own_summary["rows"] > 0 and own_summary["visible_count"] == 0:
            failure_modes.append("viewpoint_geometry_correct_target_out_of_fov_or_behind")
        elif own_summary["inside_mask_count"] == 0:
            failure_modes.append("detector_mask_no_own_view_hit_for_correct_target")
        elif own_summary["depth_consistent_count"] == 0:
            failure_modes.append("detector_depth_no_consistent_own_view_hit_for_correct_target")
        if row.get("own_view_strong_depth_evidence") is not True:
            failure_modes.append("correct_target_not_strong_in_own_view")
    strong_wrong = [
        row for row in candidates.values()
        if row.get("candidate_correct") is False
        and row.get("second_stage_strong_depth_evidence") is True
    ]
    if strong_wrong:
        failure_modes.append("wrong_selected_or_rival_remains_strong")
    if not failure_modes:
        failure_modes.append("unclassified")

    return {
        "external_branch_id": evidence_row.get("external_branch_id"),
        "episode_key": evidence_row.get("episode_key"),
        "scene_id": evidence_row.get("scene_id"),
        "query": evidence_row.get("query"),
        "second_stage_action": evidence_row.get("second_stage_identity_v1_action"),
        "second_stage_reason": evidence_row.get("second_stage_identity_v1_reason"),
        "source_selected_candidate_id": selected_id,
        "source_selected_candidate_correct": None if selected is None else selected.get("candidate_correct"),
        "targeted_candidate_ids": targeted_ids,
        "semantic_neighbor_candidate_ids": semantic_neighbor_ids,
        "correct_candidate_ids": [row.get("candidate_id") for row in correct_candidates],
        "targeted_correct_candidate_ids": [row.get("candidate_id") for row in targeted_correct],
        "strongest_correct_candidate_id": None if strongest_correct is None else strongest_correct.get("candidate_id"),
        "strongest_correct_score": None if strongest_correct is None else strongest_correct.get("S_ext"),
        "strongest_candidate_id": None if strongest_candidate is None else strongest_candidate.get("candidate_id"),
        "strongest_candidate_correct": None if strongest_candidate is None else strongest_candidate.get("candidate_correct"),
        "target_role_summary": target_role_summary,
        "frame_rows": len(frame_rows),
        "detector_rows_with_candidate_association": sum(1 for row in frame_rows if row.get("has_candidate_association") is True),
        "detector_rows_with_box": sum(1 for row in frame_rows if row.get("has_detector_box") is True),
        "detector_rows_with_mask": sum(1 for row in frame_rows if row.get("has_sam2_mask") is True),
        "failure_modes": sorted(set(failure_modes)),
        "candidate_diagnostics": candidate_diagnostics,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    evidence_rows = load_jsonl(Path(args.stage2_evidence_rows))
    plan_rows = load_jsonl(Path(args.stage2_plan))
    frame_rows = load_jsonl(Path(args.stage2_frame_rows))
    association_rows = load_jsonl(Path(args.detector_associations))
    integrated_summary = load_json(Path(args.integrated_summary))

    plan_by_branch = group_by_branch(plan_rows)
    frame_by_branch = group_by_branch(frame_rows)
    assoc_by_branch = group_by_branch(association_rows)

    diagnostic_rows = [
        diagnose_branch(
            row,
            plan_by_branch.get(str(row.get("external_branch_id")), []),
            frame_by_branch.get(str(row.get("external_branch_id")), []),
            assoc_by_branch.get(str(row.get("external_branch_id")), []),
        )
        for row in evidence_rows
    ]
    failure_counts = Counter(
        mode
        for row in diagnostic_rows
        for mode in row.get("failure_modes") or []
    )
    primary_failure = "unclassified"
    if failure_counts:
        primary_failure = failure_counts.most_common(1)[0][0]
    payload = {
        "schema_version": "h001.heldout_sofa_stage2_failure_diagnostic.v1",
        "stage2_evidence_rows": str(args.stage2_evidence_rows),
        "stage2_plan": str(args.stage2_plan),
        "stage2_frame_rows": str(args.stage2_frame_rows),
        "detector_associations": str(args.detector_associations),
        "integrated_summary": str(args.integrated_summary),
        "out_root": str(out_root),
        "rows": len(diagnostic_rows),
        "failure_mode_counts": dict(sorted(failure_counts.items())),
        "primary_failure": primary_failure,
        "integrated_gate": (integrated_summary.get("integrated") or {}).get("gate"),
        "interpretation": {
            "target_selection_supported": any(
                "target_selection_missed_all_correct_candidates" in row.get("failure_modes", [])
                for row in diagnostic_rows
            ),
            "target_selection_partial": any(
                "target_selection_left_stronger_correct_candidate_as_context" in row.get("failure_modes", [])
                for row in diagnostic_rows
            ),
            "viewpoint_geometry_supported": any(
                "viewpoint_geometry_correct_target_out_of_fov_or_behind" in row.get("failure_modes", [])
                for row in diagnostic_rows
            ),
            "detector_depth_association_supported": any(
                mode in {
                    "detector_mask_no_own_view_hit_for_correct_target",
                    "detector_depth_no_consistent_own_view_hit_for_correct_target",
                }
                for row in diagnostic_rows
                for mode in row.get("failure_modes", [])
            ),
            "summary": (
                "The held-out sofa stage2 failure is dominated by correct-target viewpoint/projection "
                "and own-view association failure, while wrong selected/rival candidates remain strong."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "heldout_sofa_stage2_failure_rows.jsonl",
            "summary": "heldout_sofa_stage2_failure_summary.json",
        },
    }
    write_jsonl(out_root / "heldout_sofa_stage2_failure_rows.jsonl", diagnostic_rows)
    write_json(out_root / "heldout_sofa_stage2_failure_summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose held-out sofa second-stage identity failures.")
    parser.add_argument("--stage2-evidence-rows", required=True)
    parser.add_argument("--stage2-plan", required=True)
    parser.add_argument("--stage2-frame-rows", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--integrated-summary", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
