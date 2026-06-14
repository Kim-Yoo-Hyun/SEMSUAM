import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SCHEMA_VERSION = "h001.pairwise_goal_region_map_pose_rule_failure_diagnostic.v1"
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_v1"
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_pairwise_goal_region_map_pose_rule_failure_diagnostic_v1"
VERIFY_DEFAULT = (
    "configs/h001/manifests/"
    "h001_pairwise_goal_region_map_pose_rule_failure_diagnostic_v1.verify.json"
)

INPUT_FILES = {
    "pair_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_pair_rows.jsonl",
    "request_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_request_rows.jsonl",
    "summary": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_summary.json",
}

OUTPUT_FILES = {
    "pair_diagnostic_rows": "pairwise_goal_region_map_pose_rule_failure_diagnostic_pair_rows.jsonl",
    "request_diagnostic_rows": "pairwise_goal_region_map_pose_rule_failure_diagnostic_request_rows.jsonl",
    "next_family_rows": "pairwise_goal_region_map_pose_rule_failure_diagnostic_next_family_rows.jsonl",
    "summary": "pairwise_goal_region_map_pose_rule_failure_diagnostic_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
PROVISIONAL_STATES = {
    "candidate_a_provisionally_supported_by_non_gt_pairwise_rule",
    "candidate_b_provisionally_supported_by_non_gt_pairwise_rule",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def join_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return tuple(str(source.get(key) or row.get(key) or "") for key in JOIN_KEYS)  # type: ignore[return-value]


def pair_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        *join_key(row),
        str(source.get("candidate_a_id") or row.get("candidate_a_id") or ""),
        str(source.get("candidate_b_id") or row.get("candidate_b_id") or ""),
    )


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def diagnose_pair(row: Mapping[str, Any]) -> Dict[str, Any]:
    state = str(row.get("non_gt_pairwise_rule_state") or "")
    goal_state = str(row.get("goal_region_contrast_state") or "")
    relation_state = str(row.get("object_relation_anchor_consistency_state") or "")
    pattern = str(row.get("candidate_pair_label_pattern_for_evaluation_only") or "")

    if state in PROVISIONAL_STATES and row.get("provisional_rule_candidate_wrong_for_evaluation_only") is True:
        return {
            "failure_class": "provisional_positive_evidence_selects_wrong_instance",
            "failure_mechanism": "goal_region_and_object_relation_agree_on_wrong_candidate",
            "diagnostic_reason": (
                "Positive goal-region and object-relation consistency can still cohere on the wrong instance."
            ),
            "recommended_next_family": "rival_contradiction_or_region_contamination_evidence_v1",
            "terminal_utility_blocker": "provisional_rule_wrong_evaluation_only",
        }
    if state == "missing_evidence_second_view_followup_required":
        return {
            "failure_class": "missing_second_view_evidence",
            "failure_mechanism": "candidate_specific_evidence_missing_before_arbitration",
            "diagnostic_reason": "The row cannot be arbitrated because the requested second-view evidence is missing.",
            "recommended_next_family": "missing_evidence_second_view_followup_v1",
            "terminal_utility_blocker": "missing_evidence_second_view_followup_required",
        }
    if goal_state == "goal_region_pair_evidence_missing" and relation_state == "object_relation_evidence_missing":
        return {
            "failure_class": "dual_evidence_coverage_gap",
            "failure_mechanism": "goal_region_and_object_relation_both_missing",
            "diagnostic_reason": "Most unresolved pairs lack both goal-region and object-relation evidence.",
            "recommended_next_family": "goal_region_object_relation_coverage_completion_v1",
            "terminal_utility_blocker": "pairwise_goal_region_map_pose_arbitration_unresolved",
        }
    if goal_state == "goal_region_pair_evidence_missing" and "contradicted" in relation_state:
        return {
            "failure_class": "relation_contradiction_without_goal_region_context",
            "failure_mechanism": "object_relation_signal_has_no_goal_region_context",
            "diagnostic_reason": "Object-relation contradiction alone cannot resolve candidate goal validity.",
            "recommended_next_family": "goal_region_conditioned_relation_recheck_v1",
            "terminal_utility_blocker": "pairwise_goal_region_map_pose_arbitration_unresolved",
        }
    if goal_state == "both_candidates_have_goal_region_support":
        return {
            "failure_class": "noncontrastive_goal_region_support",
            "failure_mechanism": "goal_region_support_is_not_candidate_discriminative",
            "diagnostic_reason": "Goal-region support for both candidates is not sufficient for instance arbitration.",
            "recommended_next_family": "contrastive_goal_region_rival_support_audit_v1",
            "terminal_utility_blocker": "pairwise_goal_region_map_pose_arbitration_unresolved",
        }
    return {
        "failure_class": "unclassified_pairwise_rule_failure",
        "failure_mechanism": f"{state}:{goal_state}:{relation_state}:{pattern}",
        "diagnostic_reason": "The row remains unresolved under the current diagnostic taxonomy.",
        "recommended_next_family": "manual_failure_inspection_v1",
        "terminal_utility_blocker": "pairwise_goal_region_map_pose_arbitration_unresolved",
    }


def materialize_pair_diagnostics(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in sorted(pair_rows, key=pair_key):
        key = join_key(row)
        payload = key_payload(key)
        diag = diagnose_pair(row)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "pairwise_goal_region_map_pose_rule_failure_diagnostic_pair",
                "join_key": {
                    **payload,
                    "candidate_a_id": row.get("candidate_a_id"),
                    "candidate_b_id": row.get("candidate_b_id"),
                },
                **payload,
                "candidate_a_id": row.get("candidate_a_id"),
                "candidate_b_id": row.get("candidate_b_id"),
                "non_gt_pairwise_rule_state": row.get("non_gt_pairwise_rule_state"),
                "goal_region_contrast_state": row.get("goal_region_contrast_state"),
                "object_relation_anchor_consistency_state": row.get(
                    "object_relation_anchor_consistency_state"
                ),
                "map_pose_non_contradiction_state": row.get("map_pose_non_contradiction_state"),
                "rule_input_complete": row.get("rule_input_complete") is True,
                "rule_defer_reason": row.get("rule_defer_reason"),
                "candidate_pair_label_pattern_for_evaluation_only": row.get(
                    "candidate_pair_label_pattern_for_evaluation_only"
                ),
                "pair_label_is_action_forbidden": True,
                "label_fields_used_for_action": False,
                "provisionally_supported_candidate_id": row.get("provisionally_supported_candidate_id"),
                "provisional_rule_candidate_correct_for_evaluation_only": row.get(
                    "provisional_rule_candidate_correct_for_evaluation_only"
                ),
                "provisional_rule_candidate_wrong_for_evaluation_only": row.get(
                    "provisional_rule_candidate_wrong_for_evaluation_only"
                ),
                "goal_region_pair_evidence_available": row.get("goal_region_pair_evidence_available") is True,
                "object_relation_candidate_a_available": row.get("object_relation_candidate_a_available") is True,
                "object_relation_candidate_b_available": row.get("object_relation_candidate_b_available") is True,
                "map_pose_consistency_abs_delta": row.get("map_pose_consistency_abs_delta"),
                "pose_graph_connectivity_abs_delta": row.get("pose_graph_connectivity_abs_delta"),
                **diag,
                **common_flags(),
            }
        )
    return out


def materialize_request_diagnostics(pair_diag_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in pair_diag_rows:
        grouped[join_key(row)].append(row)

    out: List[Dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        payload = key_payload(key)
        classes = [row.get("failure_class") for row in rows]
        blockers = [row.get("terminal_utility_blocker") for row in rows]
        families = [row.get("recommended_next_family") for row in rows]
        if "provisional_positive_evidence_selects_wrong_instance" in classes:
            request_status = "blocked_by_wrong_provisional_support"
        elif "dual_evidence_coverage_gap" in classes:
            request_status = "blocked_by_evidence_coverage_gap"
        elif "missing_second_view_evidence" in classes:
            request_status = "blocked_by_missing_second_view_evidence"
        else:
            request_status = "blocked_by_pairwise_arbitration_unresolved"
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "pairwise_goal_region_map_pose_rule_failure_diagnostic_request",
                "join_key": payload,
                **payload,
                "pair_diagnostic_rows": len(rows),
                "failure_class_counts": compact_counter(classes),
                "terminal_utility_blocker_counts": compact_counter(blockers),
                "recommended_next_family_counts": compact_counter(families),
                "request_failure_status": request_status,
                "terminal_utility_allowed": False,
                "label_fields_used_for_action": False,
                **common_flags(),
            }
        )
    return out


def materialize_next_family_rows(pair_diag_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for row in pair_diag_rows:
        grouped[str(row.get("recommended_next_family") or "manual_failure_inspection_v1")].append(row)

    priority = {
        "rival_contradiction_or_region_contamination_evidence_v1": 1,
        "goal_region_object_relation_coverage_completion_v1": 2,
        "missing_evidence_second_view_followup_v1": 3,
        "goal_region_conditioned_relation_recheck_v1": 4,
        "contrastive_goal_region_rival_support_audit_v1": 5,
        "manual_failure_inspection_v1": 9,
    }
    descriptions = {
        "rival_contradiction_or_region_contamination_evidence_v1": (
            "Acquire label-free negative/rival evidence because positive goal-region and relation evidence can agree "
            "on the wrong instance."
        ),
        "goal_region_object_relation_coverage_completion_v1": (
            "Acquire missing goal-region and object-relation evidence for unresolved pairs before any arbitration rule."
        ),
        "missing_evidence_second_view_followup_v1": (
            "Execute the already requested second-view candidate-specific evidence path for missing rows."
        ),
        "goal_region_conditioned_relation_recheck_v1": (
            "Condition relation contradiction on goal-region evidence because relation contradiction alone is not enough."
        ),
        "contrastive_goal_region_rival_support_audit_v1": (
            "Audit noncontrastive goal-region support when both candidates are supported."
        ),
        "manual_failure_inspection_v1": "Inspect residual rows not covered by the current diagnostic taxonomy.",
    }
    out: List[Dict[str, Any]] = []
    for family, rows in sorted(grouped.items(), key=lambda item: (priority.get(item[0], 99), item[0])):
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "pairwise_goal_region_map_pose_rule_failure_diagnostic_next_family",
                "recommended_next_family": family,
                "priority": priority.get(family, 99),
                "pair_rows": len(rows),
                "request_rows": len({join_key(row) for row in rows}),
                "failure_class_counts": compact_counter(row.get("failure_class") for row in rows),
                "label_pattern_counts_for_evaluation_only": compact_counter(
                    row.get("candidate_pair_label_pattern_for_evaluation_only") for row in rows
                ),
                "design_reason": descriptions.get(family, "Residual diagnostic family."),
                "terminal_utility_allowed": False,
                "contract_freeze_required_before_implementation": True,
                "label_fields_used_for_action": False,
                **common_flags(),
            }
        )
    return out


def build_summary(
    *,
    input_root: Path,
    out_root: Path,
    pair_diag_rows: Sequence[Mapping[str, Any]],
    request_diag_rows: Sequence[Mapping[str, Any]],
    next_family_rows: Sequence[Mapping[str, Any]],
    source_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    provisional_wrong = sum(
        1
        for row in pair_diag_rows
        if row.get("failure_class") == "provisional_positive_evidence_selects_wrong_instance"
    )
    gate_passed = (
        len(pair_diag_rows) == 21
        and len(request_diag_rows) == 21
        and provisional_wrong == 1
        and all(row.get("label_fields_used_for_action") is False for row in pair_diag_rows)
        and all(row.get("terminal_commit") is False for row in pair_diag_rows)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "failure_diagnostic_gate_passed_terminal_blocked" if gate_passed else "failure_diagnostic_gate_failed",
        "input_root": str(input_root),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_join_status": source_summary.get("status"),
        "source_primary_blocker": source_summary.get("primary_blocker"),
        "pair_diagnostic_rows": len(pair_diag_rows),
        "request_diagnostic_rows": len(request_diag_rows),
        "next_family_rows": len(next_family_rows),
        "failure_class_counts": compact_counter(row.get("failure_class") for row in pair_diag_rows),
        "failure_mechanism_counts": compact_counter(row.get("failure_mechanism") for row in pair_diag_rows),
        "terminal_utility_blocker_counts": compact_counter(
            row.get("terminal_utility_blocker") for row in pair_diag_rows
        ),
        "recommended_next_family_counts": compact_counter(row.get("recommended_next_family") for row in pair_diag_rows),
        "request_failure_status_counts": compact_counter(row.get("request_failure_status") for row in request_diag_rows),
        "pair_label_pattern_counts_for_evaluation_only": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_diag_rows
        ),
        "provisional_wrong_rows": provisional_wrong,
        "terminal_commit_rows": sum(1 for row in pair_diag_rows if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in pair_diag_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in pair_diag_rows if row.get("candidate_rejection") is True),
        "label_fields_used_for_action_true_rows": sum(
            1 for row in pair_diag_rows if row.get("label_fields_used_for_action") is True
        ),
        "uses_gt_for_action_true_rows": sum(1 for row in pair_diag_rows if row.get("uses_gt_for_action") is True),
        "paper_claim_allowed_true_rows": sum(1 for row in pair_diag_rows if row.get("paper_claim_allowed") is True),
        "diagnostic_gate_passed": gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "selected_next_family_candidate": next_family_rows[0].get("recommended_next_family") if next_family_rows else None,
        "next_task": "freeze_next_non_gt_evidence_family_contract_from_pairwise_failure_diagnostic",
        "interpretation": {
            "fact": (
                "The diagnostic classifies the 21 frozen pairwise evaluation-join pair rows without changing "
                "rule states or using labels for action."
            ),
            "agent_inference": (
                "The primary method lesson is that positive goal-region/object-relation agreement can select a "
                "wrong same-category instance; a new family should add negative/rival or contamination evidence "
                "rather than tune the existing rule."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM complementarity, terminal utility, formula revision, "
                "first_eval rerun, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed."
            ),
        },
    }


def build_verify_payload(
    *,
    input_root: Path,
    out_root: Path,
    verify_path: Path,
    summary: Mapping[str, Any],
) -> Dict[str, Any]:
    script_path = (
        "src/h001_runtime/"
        "diagnose_pairwise_goal_region_map_pose_rule_failure.py"
    )
    return {
        "schema_version": f"{SCHEMA_VERSION}.verify",
        "date_checked": "2026-06-11",
        "ok": summary.get("diagnostic_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(verify_path),
        "input_root": str(input_root),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "pair_diagnostic_rows": summary.get("pair_diagnostic_rows"),
            "request_diagnostic_rows": summary.get("request_diagnostic_rows"),
            "next_family_rows": summary.get("next_family_rows"),
            "provisional_wrong_rows": summary.get("provisional_wrong_rows"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "label_fields_used_for_action_true_rows": summary.get("label_fields_used_for_action_true_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "failure_class_counts": summary.get("failure_class_counts"),
        "recommended_next_family_counts": summary.get("recommended_next_family_counts"),
        "selected_next_family_candidate": summary.get("selected_next_family_candidate"),
        "next_task": summary.get("next_task"),
        "paper_claim_allowed": False,
        "verified_output_files": {name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()},
        "verification_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                f"python -m py_compile {script_path}"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.diagnose_pairwise_goal_region_map_pose_rule_failure"
            ),
            (
                "jq '{status, pair_diagnostic_rows, request_diagnostic_rows, failure_class_counts, "
                "recommended_next_family_counts, selected_next_family_candidate, diagnostic_gate_passed, "
                f"next_task}}' {out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "interpretation": summary.get("interpretation"),
    }


def run(input_root: Path, out_root: Path, verify_path: Path) -> Dict[str, Any]:
    pair_rows = load_jsonl(input_root / INPUT_FILES["pair_rows"])
    source_summary = load_json(input_root / INPUT_FILES["summary"])

    pair_diag_rows = materialize_pair_diagnostics(pair_rows)
    request_diag_rows = materialize_request_diagnostics(pair_diag_rows)
    next_family_rows = materialize_next_family_rows(pair_diag_rows)
    summary = build_summary(
        input_root=input_root,
        out_root=out_root,
        pair_diag_rows=pair_diag_rows,
        request_diag_rows=request_diag_rows,
        next_family_rows=next_family_rows,
        source_summary=source_summary,
    )

    write_jsonl(out_root / OUTPUT_FILES["pair_diagnostic_rows"], pair_diag_rows)
    write_jsonl(out_root / OUTPUT_FILES["request_diagnostic_rows"], request_diag_rows)
    write_jsonl(out_root / OUTPUT_FILES["next_family_rows"], next_family_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verify_path,
        build_verify_payload(input_root=input_root, out_root=out_root, verify_path=verify_path, summary=summary),
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Diagnose the frozen pairwise goal-region/map-pose rule failure.")
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--verify", default=VERIFY_DEFAULT)
    args = parser.parse_args()
    summary = run(Path(args.input_root), Path(args.out_root), Path(args.verify))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
