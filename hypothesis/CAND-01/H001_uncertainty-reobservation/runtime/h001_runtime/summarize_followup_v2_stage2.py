import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.external_candidate_followup_v2_stage2_validation.v1"
REQUEST_IDENTITY_ACTION = "followup_evidence_v1_request_identity_confirmation"


def load_json(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def bool_value(value: Any) -> bool:
    return value is True


def stage2_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in rows}


def terminal_row(
    v2_row: Dict[str, Any],
    stage2_by_branch: Dict[str, Dict[str, Any]],
    schema_version: str,
    followup_label: str,
) -> Dict[str, Any]:
    branch_id = str(v2_row.get("external_branch_id"))
    v2_action = str(v2_row.get("followup_evidence_v1_action"))
    stage2_row = stage2_by_branch.get(branch_id)
    uses_stage2 = v2_action == REQUEST_IDENTITY_ACTION and stage2_row is not None
    if uses_stage2:
        terminal_action = stage2_row.get("second_stage_identity_v1_action")
        terminal_reason = stage2_row.get("second_stage_identity_v1_reason")
        terminal_commits = bool_value(stage2_row.get("second_stage_identity_v1_commits"))
        terminal_success = bool_value(stage2_row.get("second_stage_identity_v1_success_commit"))
        terminal_wrong = bool_value(stage2_row.get("second_stage_identity_v1_wrong_goal_commit"))
        terminal_no_valid = bool_value(stage2_row.get("second_stage_identity_v1_no_valid_commit"))
        terminal_visit_position_only = bool_value(stage2_row.get("second_stage_identity_v1_visit_position_only_commit"))
        selected_candidate_id = stage2_row.get("selected_candidate_id")
        selected_candidate_correct = stage2_row.get("selected_candidate_correct")
        source_selected_candidate_id = stage2_row.get("source_selected_candidate_id")
        source_selected_candidate_correct = stage2_row.get("source_selected_candidate_correct")
        committed_candidate_id = stage2_row.get("committed_candidate_id")
        committed_candidate_correct = stage2_row.get("committed_candidate_correct")
        terminal_source = "second_stage_identity"
    else:
        terminal_action = v2_row.get("followup_evidence_v1_action")
        terminal_reason = v2_row.get("followup_evidence_v1_reason")
        terminal_commits = bool_value(v2_row.get("followup_evidence_v1_commits"))
        terminal_success = bool_value(v2_row.get("followup_evidence_v1_success_commit"))
        terminal_wrong = bool_value(v2_row.get("followup_evidence_v1_wrong_goal_commit"))
        terminal_no_valid = bool_value(v2_row.get("followup_evidence_v1_no_valid_commit"))
        terminal_visit_position_only = False
        selected_candidate_id = v2_row.get("selected_candidate_id")
        selected_candidate_correct = v2_row.get("selected_candidate_correct")
        source_selected_candidate_id = v2_row.get("selected_candidate_id")
        source_selected_candidate_correct = v2_row.get("selected_candidate_correct")
        committed_candidate_id = selected_candidate_id if terminal_commits else None
        committed_candidate_correct = selected_candidate_correct if terminal_commits else None
        terminal_source = followup_label
    row = {
        "schema_version": schema_version,
        "external_branch_id": branch_id,
        "episode_key": v2_row.get("episode_key"),
        "scene_id": v2_row.get("scene_id"),
        "query": v2_row.get("query"),
        "property_group": v2_row.get("property_group"),
        "label_case": v2_row.get("label_case"),
        "source_followup_action": v2_action,
        "source_followup_reason": v2_row.get("followup_evidence_v1_reason"),
        "terminal_source": terminal_source,
        "terminal_action": terminal_action,
        "terminal_reason": terminal_reason,
        "terminal_commits": terminal_commits,
        "terminal_success_commit": terminal_success,
        "terminal_wrong_goal_commit": terminal_wrong,
        "terminal_no_valid_commit": terminal_no_valid,
        "terminal_visit_position_only_commit": terminal_visit_position_only,
        "selected_candidate_id": selected_candidate_id,
        "selected_candidate_correct": selected_candidate_correct,
        "source_selected_candidate_id": source_selected_candidate_id,
        "source_selected_candidate_correct": source_selected_candidate_correct,
        "committed_candidate_id": committed_candidate_id,
        "committed_candidate_correct": committed_candidate_correct,
        "followup_set_contains_correct": v2_row.get("followup_set_contains_correct"),
        "stage2_available": stage2_row is not None,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool_value(v2_row.get("uses_gt_for_analysis"))
        or bool(stage2_row and stage2_row.get("uses_gt_for_analysis") is True),
    }
    row[f"source_{followup_label}_action"] = v2_action
    row[f"source_{followup_label}_reason"] = v2_row.get("followup_evidence_v1_reason")
    return row


def compact_detector_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "rows": summary.get("rows"),
        "rows_with_detector_box_rate": summary.get("rows_with_detector_box_rate"),
        "rows_with_sam2_mask_rate": summary.get("rows_with_sam2_mask_rate"),
        "rows_with_candidate_association_rate": summary.get("rows_with_candidate_association_rate"),
        "association_rows": summary.get("association_rows"),
        "uses_gt_for_action": summary.get("uses_gt_for_action"),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    v2_summary = load_json(Path(args.followup_v2_summary))
    v2_rows = load_jsonl(Path(args.followup_v2_rows))
    stage2_plan_summary = load_json(Path(args.second_stage_plan_summary))
    stage2_frame_summary = load_json(Path(args.second_stage_frame_summary))
    stage2_detector_summary = load_json(Path(args.second_stage_detector_summary))
    stage2_evidence_summary = load_json(Path(args.second_stage_evidence_summary))
    stage2_rows = load_jsonl(Path(args.second_stage_evidence_rows))
    base_validation = load_json(Path(args.base_validation_summary) if args.base_validation_summary else None)

    stage2_by_branch = stage2_index(stage2_rows)
    terminal_rows = [
        terminal_row(row, stage2_by_branch, str(args.schema_version), str(args.followup_label))
        for row in v2_rows
    ]
    write_jsonl(out_root / str(args.terminal_rows_file), terminal_rows)

    request_identity_rows = [row for row in v2_rows if row.get("followup_evidence_v1_action") == REQUEST_IDENTITY_ACTION]
    stage2_required = len(request_identity_rows)
    stage2_resolved = sum(1 for row in request_identity_rows if str(row.get("external_branch_id")) in stage2_by_branch)
    commit_rows = [row for row in terminal_rows if row["terminal_commits"]]
    success_commits = [row for row in terminal_rows if row["terminal_success_commit"]]
    wrong_commits = [row for row in terminal_rows if row["terminal_wrong_goal_commit"]]
    no_valid_commits = [row for row in terminal_rows if row["terminal_no_valid_commit"]]
    visit_position_commits = [row for row in terminal_rows if row["terminal_visit_position_only_commit"]]
    terminal_action_counts = Counter(str(row.get("terminal_action")) for row in terminal_rows)
    terminal_reason_counts = Counter(str(row.get("terminal_reason")) for row in terminal_rows)
    terminal_source_counts = Counter(str(row.get("terminal_source")) for row in terminal_rows)
    any_gt_action = bool(
        v2_summary.get("uses_gt_for_action")
        or stage2_plan_summary.get("uses_gt_for_action")
        or stage2_frame_summary.get("uses_gt_for_action")
        or stage2_detector_summary.get("uses_gt_for_action")
        or stage2_evidence_summary.get("uses_gt_for_action")
        or any(row.get("uses_gt_for_action") for row in terminal_rows)
    )
    any_gt_analysis = bool(
        v2_summary.get("uses_gt_for_analysis")
        or stage2_evidence_summary.get("uses_gt_for_analysis")
        or any(row.get("uses_gt_for_analysis") for row in terminal_rows)
    )
    v2_gate = v2_summary.get("gate") or {}
    stage2_gate = stage2_evidence_summary.get("gate") or {}
    gate = {
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_no_valid_commit_rate": float(args.max_no_valid_commit_rate),
        "max_visit_position_only_commit_rate": float(args.max_visit_position_only_commit_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_success_commit_rate": float(args.min_success_commit_rate),
        "stage2_request_coverage_rate": ratio(stage2_resolved, stage2_required),
        "commit_rate": ratio(len(commit_rows), len(terminal_rows)),
        "success_commit_rate": ratio(len(success_commits), len(terminal_rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_commits), len(terminal_rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commits), len(commit_rows)),
        "no_valid_commit_rate": ratio(len(no_valid_commits), len(terminal_rows)),
        "visit_position_only_commit_rate": ratio(len(visit_position_commits), len(terminal_rows)),
        "passes_followup_v2_detector_substrate": v2_gate.get("passes_followup_detector_substrate_gate_v1"),
        "passes_followup_v2_safety": v2_gate.get("passes_followup_evidence_safety_gate_v1"),
        "passes_followup_v2_full": v2_gate.get("passes_followup_evidence_full_gate_v1"),
        "passes_stage2_schema": stage2_gate.get("passes_second_stage_identity_schema_gate_v1"),
        "passes_stage2_detector_substrate": stage2_gate.get("passes_second_stage_identity_detector_substrate_gate_v1"),
        "passes_stage2_safety": stage2_gate.get("passes_second_stage_identity_safety_gate_v1"),
        "passes_stage2_full": stage2_gate.get("passes_second_stage_identity_full_gate_v1"),
    }
    gate["passes_integrated_stage2_coverage"] = bool(stage2_required == 0 or stage2_resolved == stage2_required)
    gate["passes_integrated_detector_substrate"] = bool(
        gate["passes_followup_v2_detector_substrate"]
        and (stage2_required == 0 or gate["passes_stage2_detector_substrate"])
    )
    gate["passes_integrated_stage2_full"] = bool(stage2_required == 0 or gate["passes_stage2_full"])
    gate["passes_integrated_safety_gate"] = bool(
        not any_gt_action
        and gate["passes_followup_v2_safety"]
        and (stage2_required == 0 or gate["passes_stage2_safety"])
        and (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["no_valid_commit_rate"] or 0.0) <= float(args.max_no_valid_commit_rate)
        and (gate["visit_position_only_commit_rate"] or 0.0) <= float(args.max_visit_position_only_commit_rate)
    )
    gate["passes_integrated_full_gate"] = bool(
        gate["passes_integrated_stage2_coverage"]
        and gate["passes_integrated_detector_substrate"]
        and gate["passes_integrated_stage2_full"]
        and gate["passes_integrated_safety_gate"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and (gate["success_commit_rate"] or 0.0) >= float(args.min_success_commit_rate)
    )
    validation_scope_blocks_rerun = args.validation_scope in {
        "same_artifact_diagnostic",
        "v4_fixed_terminal_diagnostic",
        "v4_semantic_neighbor_diagnostic",
    }
    utility_proof_passed = bool(gate["passes_integrated_full_gate"] and not validation_scope_blocks_rerun)
    first_eval_rerun_blocked = bool(not gate["passes_integrated_full_gate"] or validation_scope_blocks_rerun)
    next_required = "inspect integrated failure before rerun"
    if validation_scope_blocks_rerun and gate["passes_integrated_full_gate"]:
        next_required = "validate the objective on held-out fresh rows before first_eval or policy-scale rerun"
    elif gate["passes_integrated_safety_gate"] and not gate["passes_integrated_full_gate"]:
        next_required = "find or rerun a validation split where second-stage identity requests include valid/correct targets"

    payload = {
        "schema_version": str(args.schema_version),
        "out_root": str(out_root),
        "followup_label": str(args.followup_label),
        "paths": {
            "base_validation_summary": args.base_validation_summary,
            "followup_v2_summary": args.followup_v2_summary,
            "followup_v2_rows": args.followup_v2_rows,
            "second_stage_plan_summary": args.second_stage_plan_summary,
            "second_stage_frame_summary": args.second_stage_frame_summary,
            "second_stage_detector_summary": args.second_stage_detector_summary,
            "second_stage_evidence_summary": args.second_stage_evidence_summary,
            "second_stage_evidence_rows": args.second_stage_evidence_rows,
        },
        "base_validation_schema_version": base_validation.get("schema_version"),
        "validation_scope": args.validation_scope,
        "followup_v2": {
            "schema_version": v2_summary.get("schema_version"),
            "source_request_rows": v2_summary.get("source_request_rows"),
            "source_rows_analyzed": v2_summary.get("source_rows_analyzed"),
            "plan_rows": v2_summary.get("plan_rows"),
            "frame_rows": v2_summary.get("frame_rows"),
            "association_rows": v2_summary.get("association_rows"),
            "action_counts": v2_summary.get("action_counts"),
            "reason_counts": v2_summary.get("reason_counts"),
            "gate": v2_gate,
        },
        "source_followup": {
            "label": str(args.followup_label),
            "schema_version": v2_summary.get("schema_version"),
            "objective_version": v2_summary.get("objective_version"),
            "source_request_rows": v2_summary.get("source_request_rows"),
            "source_rows_analyzed": v2_summary.get("source_rows_analyzed"),
            "action_counts": v2_summary.get("action_counts"),
            "reason_counts": v2_summary.get("reason_counts"),
            "gate": v2_gate,
        },
        "second_stage": {
            "plan": {
                "request_rows": stage2_plan_summary.get("request_rows"),
                "plan_rows": stage2_plan_summary.get("plan_rows"),
                "skipped_rows": stage2_plan_summary.get("skipped_rows"),
                "role_counts": stage2_plan_summary.get("role_counts"),
                "viewpoint_source_counts": stage2_plan_summary.get("viewpoint_source_counts"),
            },
            "frames": {
                "rows_exported": stage2_frame_summary.get("rows_exported"),
                "rendered_heading_count": stage2_frame_summary.get("rendered_heading_count"),
                "uses_gt_for_action": stage2_frame_summary.get("uses_gt_for_action"),
            },
            "detector": compact_detector_summary(stage2_detector_summary),
            "evidence": {
                "schema_version": stage2_evidence_summary.get("schema_version"),
                "source_request_rows": stage2_evidence_summary.get("source_request_rows"),
                "source_rows_analyzed": stage2_evidence_summary.get("source_rows_analyzed"),
                "plan_rows": stage2_evidence_summary.get("plan_rows"),
                "frame_rows": stage2_evidence_summary.get("frame_rows"),
                "association_rows": stage2_evidence_summary.get("association_rows"),
                "action_counts": stage2_evidence_summary.get("action_counts"),
                "reason_counts": stage2_evidence_summary.get("reason_counts"),
                "gate": stage2_gate,
            },
        },
        "integrated": {
            "terminal_rows": len(terminal_rows),
            "stage2_required_rows": stage2_required,
            "stage2_resolved_rows": stage2_resolved,
            "stage2_unresolved_rows": max(0, stage2_required - stage2_resolved),
            "terminal_action_counts": dict(sorted(terminal_action_counts.items())),
            "terminal_reason_counts": dict(sorted(terminal_reason_counts.items())),
            "terminal_source_counts": dict(sorted(terminal_source_counts.items())),
            "commit_rows": len(commit_rows),
            "success_commit_rows": len(success_commits),
            "wrong_goal_commit_rows": len(wrong_commits),
            "no_valid_commit_rows": len(no_valid_commits),
            "visit_position_only_commit_rows": len(visit_position_commits),
            "gate": gate,
        },
        "interpretation": {
            "first_eval_rerun_blocked": first_eval_rerun_blocked,
            "policy_scale_comparison_blocked": first_eval_rerun_blocked,
            "safety_diagnostic_passed": gate["passes_integrated_safety_gate"],
            "local_integrated_gate_passed": gate["passes_integrated_full_gate"],
            "utility_proof_passed": utility_proof_passed,
            "next_required": next_required,
        },
        "uses_gt_for_action": any_gt_action,
        "uses_gt_for_analysis": any_gt_analysis,
        "output_files": {
            "terminal_rows": str(args.terminal_rows_file),
            "summary": str(args.summary_file),
        },
    }
    write_json(out_root / str(args.summary_file), payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize H001 follow-up V2 with second-stage identity outputs.")
    parser.add_argument("--followup-v2-summary", required=True)
    parser.add_argument("--followup-v2-rows", required=True)
    parser.add_argument("--second-stage-plan-summary", required=True)
    parser.add_argument("--second-stage-frame-summary", required=True)
    parser.add_argument("--second-stage-detector-summary", required=True)
    parser.add_argument("--second-stage-evidence-summary", required=True)
    parser.add_argument("--second-stage-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--base-validation-summary", default=None)
    parser.add_argument(
        "--validation-scope",
        choices=[
            "unspecified",
            "same_artifact_diagnostic",
            "heldout_validation",
            "heldout_semantic_neighbor_v3_validation",
            "heldout_explicit_candidate_diagnostic",
            "v4_fixed_terminal_diagnostic",
            "v4_semantic_neighbor_diagnostic",
        ],
        default="unspecified",
    )
    parser.add_argument("--schema-version", default=SCHEMA_VERSION)
    parser.add_argument("--followup-label", default="followup_v2")
    parser.add_argument("--terminal-rows-file", default="external_candidate_followup_v2_stage2_terminal_rows.jsonl")
    parser.add_argument("--summary-file", default="external_candidate_followup_v2_stage2_validation_summary.json")
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.0)
    parser.add_argument("--max-no-valid-commit-rate", type=float, default=0.0)
    parser.add_argument("--max-visit-position-only-commit-rate", type=float, default=0.0)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-success-commit-rate", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
