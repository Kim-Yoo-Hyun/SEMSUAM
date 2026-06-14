import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.dense_conflict_validation.v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_optional(path: Optional[Path]) -> Dict[str, Any]:
    if path is None or not path.exists():
        return {}
    return load_json(path)


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


def role_allowed(role: str, allowed: List[str]) -> bool:
    return "all" in allowed or role in allowed


def source_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return str(row.get("episode_key")), str(row.get("external_branch_id"))


def manifest_source_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return str(row.get("episode_key")), str(row.get("dense_conflict_source_external_branch_id"))


def recall_key(row: Dict[str, Any]) -> str:
    return str(row.get("episode_key"))


def positive_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        dict(candidate)
        for candidate in row.get("second_stage_candidate_evidence") or []
        if candidate.get("positive_support") is True
    ]


def candidate_by_id(row: Dict[str, Any], candidate_id: Optional[str]) -> Dict[str, Any]:
    if candidate_id is None:
        return {}
    for candidate in row.get("second_stage_candidate_evidence") or []:
        if str(candidate.get("candidate_id")) == str(candidate_id):
            return dict(candidate)
    return {}


def dense_row(manifest_row: Dict[str, Any], source_row: Dict[str, Any], recall_row: Dict[str, Any]) -> Dict[str, Any]:
    positives = positive_candidates(source_row)
    correct_positive = [candidate for candidate in positives if candidate.get("candidate_correct") is True]
    wrong_positive = [candidate for candidate in positives if candidate.get("candidate_correct") is False]
    action = source_row.get("second_stage_identity_v1_action")
    commits = source_row.get("second_stage_identity_v1_commits") is True
    committed_id = source_row.get("committed_candidate_id")
    committed = candidate_by_id(source_row, committed_id)
    selected_id = source_row.get("decision_candidate_id")
    selected = candidate_by_id(source_row, selected_id)
    source_selected_correct = source_row.get("source_selected_candidate_correct")
    decision_correct = source_row.get("decision_candidate_correct")
    committed_correct = source_row.get("committed_candidate_correct")
    selected_improves_source = decision_correct is True and source_selected_correct is False
    correct_commit_with_wrong_positive = bool(commits and committed_correct is True and wrong_positive)
    return {
        "schema_version": SCHEMA_VERSION,
        "episode_key": manifest_row.get("episode_key"),
        "scene_id": manifest_row.get("scene_id"),
        "scene_key": manifest_row.get("scene_key"),
        "query": manifest_row.get("dense_conflict_source_query") or source_row.get("query"),
        "dense_conflict_role": manifest_row.get("dense_conflict_role"),
        "dense_conflict_class": manifest_row.get("dense_conflict_class"),
        "external_branch_id": manifest_row.get("dense_conflict_source_external_branch_id"),
        "source_action": manifest_row.get("dense_conflict_source_action"),
        "source_reason": manifest_row.get("dense_conflict_source_reason"),
        "second_stage_action": action,
        "second_stage_reason": source_row.get("second_stage_identity_v1_reason"),
        "source_selected_candidate_id": source_row.get("source_selected_candidate_id"),
        "source_selected_candidate_correct": source_selected_correct,
        "decision_candidate_id": selected_id,
        "decision_candidate_correct": decision_correct,
        "committed_candidate_id": committed_id,
        "committed_candidate_correct": committed_correct,
        "commits": commits,
        "success_commit": bool(source_row.get("second_stage_identity_v1_success_commit")),
        "wrong_goal_commit": bool(source_row.get("second_stage_identity_v1_wrong_goal_commit")),
        "no_valid_commit": bool(source_row.get("second_stage_identity_v1_no_valid_commit")),
        "visit_position_only_commit": bool(source_row.get("second_stage_identity_v1_visit_position_only_commit")),
        "followup_set_contains_correct": source_row.get("followup_set_contains_correct"),
        "selected_improves_over_source_selected": selected_improves_source,
        "correct_commit_with_wrong_positive_support": correct_commit_with_wrong_positive,
        "recall_contains_correct": recall_row.get("contains_correct"),
        "recall_first_correct_rank": recall_row.get("first_correct_rank"),
        "recall_candidate_count": recall_row.get("candidate_count"),
        "positive_support_candidate_count": len(positives),
        "correct_positive_support_candidate_count": len(correct_positive),
        "wrong_positive_support_candidate_count": len(wrong_positive),
        "correct_and_wrong_positive_support": bool(correct_positive and wrong_positive),
        "positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in positives),
        "correct_positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in correct_positive),
        "wrong_positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in wrong_positive),
        "decision_candidate_score": selected.get("S_ext"),
        "committed_candidate_score": committed.get("S_ext"),
        "uses_gt_for_action": bool(source_row.get("uses_gt_for_action") or recall_row.get("uses_gt_for_action")),
        "uses_gt_for_analysis": True,
    }


def gate(summary_rows: List[Dict[str, Any]], detector_summary: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    rows = len(summary_rows)
    commit_rows = [row for row in summary_rows if row["commits"]]
    success_rows = [row for row in summary_rows if row["success_commit"]]
    wrong_rows = [row for row in summary_rows if row["wrong_goal_commit"]]
    no_valid_rows = [row for row in summary_rows if row["no_valid_commit"]]
    visit_only_rows = [row for row in summary_rows if row["visit_position_only_commit"]]
    conflict_rows = [row for row in summary_rows if row["correct_and_wrong_positive_support"]]
    improve_rows = [row for row in summary_rows if row["selected_improves_over_source_selected"]]
    correct_commit_with_wrong = [
        row for row in summary_rows if row["correct_commit_with_wrong_positive_support"]
    ]
    detector_box_rate = detector_summary.get("rows_with_detector_box_rate")
    sam2_mask_rate = detector_summary.get("rows_with_sam2_mask_rate")
    association_rate = detector_summary.get("rows_with_candidate_association_rate")
    substrate_gate = bool(
        rows >= int(args.min_primary_rows)
        and (detector_box_rate or 0.0) >= float(args.min_detector_box_rate)
        and (sam2_mask_rate or 0.0) >= float(args.min_sam2_mask_rate)
        and (association_rate or 0.0) >= float(args.min_candidate_association_rate)
        and len(conflict_rows) >= int(args.min_rows_with_correct_wrong_positive_support)
        and all(row["recall_contains_correct"] is True for row in summary_rows)
        and all(row["uses_gt_for_action"] is False for row in summary_rows)
    )
    safety_gate = bool(
        len(wrong_rows) == 0
        and len(no_valid_rows) == 0
        and len(visit_only_rows) == 0
    )
    utility_gate = bool(
        len(success_rows) >= int(args.min_success_commit_rows)
        and len(improve_rows) >= int(args.min_selected_correct_improvement_rows)
        and len(correct_commit_with_wrong) >= int(args.min_correct_commit_with_wrong_positive_rows)
        and len(commit_rows) > 0
    )
    return {
        "thresholds": {
            "min_primary_rows": int(args.min_primary_rows),
            "min_detector_box_rate": float(args.min_detector_box_rate),
            "min_sam2_mask_rate": float(args.min_sam2_mask_rate),
            "min_candidate_association_rate": float(args.min_candidate_association_rate),
            "min_rows_with_correct_wrong_positive_support": int(args.min_rows_with_correct_wrong_positive_support),
            "min_success_commit_rows": int(args.min_success_commit_rows),
            "min_selected_correct_improvement_rows": int(args.min_selected_correct_improvement_rows),
            "min_correct_commit_with_wrong_positive_rows": int(args.min_correct_commit_with_wrong_positive_rows),
        },
        "detector_box_rate": detector_box_rate,
        "sam2_mask_rate": sam2_mask_rate,
        "candidate_association_rate": association_rate,
        "primary_rows": rows,
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "no_valid_commit_rows": len(no_valid_rows),
        "visit_position_only_commit_rows": len(visit_only_rows),
        "rows_with_correct_and_wrong_positive_support": len(conflict_rows),
        "selected_correct_improvement_over_source_selected_rows": len(improve_rows),
        "correct_commit_with_wrong_positive_support_rows": len(correct_commit_with_wrong),
        "commit_rate": ratio(len(commit_rows), rows),
        "success_commit_rate": ratio(len(success_rows), rows),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), rows),
        "no_valid_commit_rate": ratio(len(no_valid_rows), rows),
        "visit_position_only_commit_rate": ratio(len(visit_only_rows), rows),
        "passes_dense_detector_association_substrate_gate": substrate_gate,
        "passes_dense_conflict_safety_gate": safety_gate,
        "passes_dense_conflict_utility_gate": utility_gate,
        "passes_dense_conflict_validation_gate": bool(substrate_gate and safety_gate and utility_gate),
    }


def failure_taxonomy(gate_payload: Dict[str, Any]) -> Dict[str, Any]:
    failures: List[Dict[str, str]] = []
    if not gate_payload["passes_dense_detector_association_substrate_gate"]:
        failures.append(
            {
                "code": "F2_detector_association_substrate_fail",
                "meaning": "dense recall passed, but detector/mask/association substrate or conflict support is insufficient",
            }
        )
    if not gate_payload["passes_dense_conflict_safety_gate"]:
        failures.append(
            {
                "code": "F7_terminal_safety_fail",
                "meaning": "the active observation objective commits a wrong, no-valid, or visit-position-only target",
            }
        )
    if not gate_payload["passes_dense_conflict_utility_gate"]:
        failures.append(
            {
                "code": "F8_overdeferral_or_no_utility",
                "meaning": "the objective is safe but does not create enough correct commits or source-selected repairs",
            }
        )
    return {"failures": failures, "active_failure_codes": [item["code"] for item in failures]}


def run(args: argparse.Namespace) -> Dict[str, Any]:
    manifest = load_json(Path(args.manifest))
    manifest_rows = [
        row
        for row in manifest.get("rows", [])
        if role_allowed(str(row.get("dense_conflict_role")), args.roles)
    ]
    source_rows = load_jsonl(Path(args.source_evidence_rows))
    recall_rows = load_jsonl(Path(args.recall_rows))
    source_by_key = {source_key(row): row for row in source_rows}
    recall_by_episode = {recall_key(row): row for row in recall_rows}

    output_rows: List[Dict[str, Any]] = []
    missing_source: List[Dict[str, Any]] = []
    missing_recall: List[Dict[str, Any]] = []
    for manifest_row in manifest_rows:
        key = manifest_source_key(manifest_row)
        source_row = source_by_key.get(key)
        recall_row = recall_by_episode.get(str(manifest_row.get("episode_key")))
        if source_row is None:
            missing_source.append({"episode_key": key[0], "external_branch_id": key[1]})
            continue
        if recall_row is None:
            missing_recall.append({"episode_key": key[0], "external_branch_id": key[1]})
            continue
        output_rows.append(dense_row(manifest_row, source_row, recall_row))

    detector_summary = load_json_optional(Path(args.detector_summary) if args.detector_summary else None)
    recall_summary = load_json_optional(Path(args.recall_summary) if args.recall_summary else None)
    gate_payload = gate(output_rows, detector_summary, args)
    action_counts = Counter(str(row["second_stage_action"]) for row in output_rows)
    reason_counts = Counter(str(row["second_stage_reason"]) for row in output_rows)
    scene_counts = Counter(str(row["scene_key"]) for row in output_rows)
    query_counts = Counter(str(row["query"]) for row in output_rows)
    failures = failure_taxonomy(gate_payload)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "manifest": str(args.manifest),
        "source_evidence_rows": str(args.source_evidence_rows),
        "recall_rows": str(args.recall_rows),
        "recall_summary": str(args.recall_summary) if args.recall_summary else None,
        "detector_summary": str(args.detector_summary) if args.detector_summary else None,
        "roles": args.roles,
        "rows": len(output_rows),
        "missing_source_rows": missing_source,
        "missing_recall_rows": missing_recall,
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "gate": gate_payload,
        "failure_taxonomy": failures,
        "decision": {
            "detector_association_validation_blocked": not gate_payload["passes_dense_conflict_validation_gate"],
            "next_step": (
                "treat this selected artifact as detector/association validated for dense conflict terminal analysis"
                if gate_payload["passes_dense_conflict_validation_gate"]
                else "do not promote; inspect failure taxonomy before rerunning detector or changing the backend"
            ),
        },
        "interpretation": {
            "fact": "This analysis materializes existing second-stage detector/association evidence for the frozen dense conflict rows.",
            "agent_inference": "A pass means the detector/association blocker is lifted for this selected artifact, not for failed p95/p90 dense re-export substrates.",
            "paper_claim_status": "diagnostic_gate_passed_not_full_policy_claim",
        },
        "uses_gt_for_action": any(row["uses_gt_for_action"] for row in output_rows),
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "dense_terminal_arbitration_rows.jsonl",
            "summary": "dense_terminal_arbitration_summary.json",
            "manifest": "dense_conflict_manifest.json",
            "recall_summary": "dense_recall_summary.json",
            "detector_summary": "dense_detector_summary.json",
            "association_variant_summary": "dense_association_variant_summary.json",
            "evaluation_labels": "evaluation_labels.jsonl",
            "failure_taxonomy": "failure_taxonomy.json",
        },
    }

    out_root = Path(args.out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    write_json(out_root / "dense_conflict_manifest.json", manifest)
    write_json(out_root / "dense_recall_summary.json", recall_summary)
    write_json(out_root / "dense_detector_summary.json", detector_summary)
    write_json(
        out_root / "dense_association_variant_summary.json",
        {
            "schema_version": SCHEMA_VERSION,
            "variants": [
                {
                    "name": str(args.source_name),
                    "candidate_association_rate": detector_summary.get("rows_with_candidate_association_rate"),
                    "detector_box_rate": detector_summary.get("rows_with_detector_box_rate"),
                    "sam2_mask_rate": detector_summary.get("rows_with_sam2_mask_rate"),
                    "source": str(args.detector_summary) if args.detector_summary else None,
                }
            ],
            "selected_variant": str(args.source_name),
        },
    )
    write_jsonl(out_root / "dense_terminal_arbitration_rows.jsonl", output_rows)
    write_json(out_root / "dense_terminal_arbitration_summary.json", summary)
    write_jsonl(
        out_root / "evaluation_labels.jsonl",
        [
            {
                "episode_key": row["episode_key"],
                "external_branch_id": row["external_branch_id"],
                "decision_candidate_id": row["decision_candidate_id"],
                "decision_candidate_correct": row["decision_candidate_correct"],
                "committed_candidate_id": row["committed_candidate_id"],
                "committed_candidate_correct": row["committed_candidate_correct"],
                "success_commit": row["success_commit"],
                "wrong_goal_commit": row["wrong_goal_commit"],
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
            for row in output_rows
        ],
    )
    write_json(out_root / "failure_taxonomy.json", failures)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize dense conflict validation from existing detector evidence.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--source-evidence-rows", required=True)
    parser.add_argument("--recall-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--recall-summary")
    parser.add_argument("--detector-summary")
    parser.add_argument("--source-name", default="source_detector_association")
    parser.add_argument("--roles", default="primary")
    parser.add_argument("--min-primary-rows", type=int, default=6)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-candidate-association-rate", type=float, default=0.30)
    parser.add_argument("--min-rows-with-correct-wrong-positive-support", type=int, default=3)
    parser.add_argument("--min-success-commit-rows", type=int, default=2)
    parser.add_argument("--min-selected-correct-improvement-rows", type=int, default=2)
    parser.add_argument("--min-correct-commit-with-wrong-positive-rows", type=int, default=2)
    args = parser.parse_args()
    args.roles = [role.strip() for role in str(args.roles).split(",") if role.strip()]
    return args


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
