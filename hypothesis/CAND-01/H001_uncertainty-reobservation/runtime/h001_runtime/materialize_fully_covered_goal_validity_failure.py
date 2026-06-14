import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "h001.fully_covered_goal_validity_failure.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_fully_covered_goal_validity_failure_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_fully_covered_goal_validity_failure_v1"

OUTPUT_FILES = {
    "target_pair_rows": "fully_covered_goal_validity_failure_target_pair_rows.jsonl",
    "candidate_rows": "fully_covered_goal_validity_failure_candidate_rows.jsonl",
    "role_rows": "fully_covered_goal_validity_failure_role_rows.jsonl",
    "candidate_view_rows": "fully_covered_goal_validity_failure_candidate_view_rows.jsonl",
    "evaluation_audit_rows": "fully_covered_goal_validity_failure_evaluation_audit_rows.jsonl",
    "summary": "fully_covered_goal_validity_failure_summary.json",
}

FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "candidate_correctness_label",
    "candidate_pair_label_pattern_for_evaluation_only",
    "candidate_wrong_label",
    "correct_candidate",
    "evaluation_only",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_instance_id",
    "gt_label",
    "gt_object_id",
    "ground_truth",
    "map_pose_consistency_delta",
    "oracle_object_id",
    "oracle_shortest_path",
    "success_label",
    "valid_candidate",
    "wasted_path_m",
    "wrong_goal",
    "wrong_goal_visit",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def resolve_path(path_like: str) -> Path:
    path = Path(path_like)
    if path.exists():
        return path
    if path_like.startswith("local_dataset/runs/"):
        runs_path = Path("/runs") / path_like.removeprefix("local_dataset/runs/")
        if runs_path.exists():
            return runs_path
    workspace_path = Path("/workspace") / path
    if workspace_path.exists():
        return workspace_path
    return path


def path_from_contract(contract: Mapping[str, Any], key: str) -> Path:
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"missing source path: {key}")
    return resolve_path(str(source[key]))


def compact_counter(values: Iterable[Any]) -> dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row.get("action_evidence_inputs", {}))
        scan(row.get("action_route_inputs", {}))
    return sorted(found)


def target_row(contract: Mapping[str, Any]) -> dict[str, Any]:
    rows = list(contract.get("target_rows") or [])
    if len(rows) != 1:
        raise ValueError(f"expected one frozen target row, got {len(rows)}")
    return dict(rows[0])


def target_matches(row: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    return (
        str(row.get("coverage_completion_pair_id") or "") == str(target["coverage_completion_pair_id"])
        and str(row.get("request_id") or row.get("expanded_retrieval_request_id") or "") == str(target["request_id"])
        and str(row.get("scene_key") or "") == str(target["scene_key"])
        and str(row.get("query") or "") == str(target["query"])
        and str(row.get("episode_key") or "") == str(target["episode_key"])
    )


def common_flags(uses_gt_for_analysis: bool = False) -> dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": uses_gt_for_analysis,
        "paper_claim_allowed": False,
    }


def build_target_pair_row(detector_pair: Mapping[str, Any], eval_pair: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "fully_covered_goal_validity_failure_target_pair",
        "validation_stage": "fully_covered_goal_validity_failure_diagnostic_after_contract_freeze",
        "scene_key": detector_pair.get("scene_key"),
        "query": detector_pair.get("query"),
        "episode_key": detector_pair.get("episode_key"),
        "source_name": detector_pair.get("source_name"),
        "request_id": detector_pair.get("request_id"),
        "coverage_completion_pair_id": detector_pair.get("coverage_completion_pair_id"),
        "candidate_a_id": detector_pair.get("candidate_a_id"),
        "candidate_b_id": detector_pair.get("candidate_b_id"),
        "pair_evidence_state": detector_pair.get("pair_evidence_state"),
        "role_evidence_states": detector_pair.get("role_evidence_states"),
        "role_rows_with_any_candidate_association": detector_pair.get("role_rows_with_any_candidate_association"),
        "diagnostic_state": "fully_covered_but_goal_validity_unproven",
        "evaluation_only_pair_label_pattern": eval_pair.get("candidate_pair_label_pattern_for_evaluation_only"),
        "evaluation_only_pair_label_is_action_forbidden": True,
        "terminal_selector_allowed_from_this_branch": False,
        **common_flags(uses_gt_for_analysis=True),
    }


def build_candidate_row(eval_candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "fully_covered_goal_validity_failure_candidate",
        "validation_stage": "fully_covered_goal_validity_failure_diagnostic_after_contract_freeze",
        "scene_key": eval_candidate.get("scene_key"),
        "query": eval_candidate.get("query"),
        "episode_key": eval_candidate.get("episode_key"),
        "source_name": eval_candidate.get("source_name"),
        "request_id": eval_candidate.get("request_id"),
        "coverage_completion_pair_id": eval_candidate.get("coverage_completion_pair_id"),
        "candidate_id": eval_candidate.get("candidate_id"),
        "candidate_pair_role": eval_candidate.get("candidate_pair_role"),
        "coverage_completion_pair_evidence_state": eval_candidate.get("coverage_completion_pair_evidence_state"),
        "coverage_completion_candidate_view_rows": eval_candidate.get("coverage_completion_candidate_view_rows"),
        "coverage_completion_candidate_view_states_by_role": eval_candidate.get(
            "coverage_completion_candidate_view_states_by_role"
        ),
        "coverage_completion_associated_rows": eval_candidate.get("coverage_completion_associated_rows"),
        "coverage_completion_depth_consistent_rows": eval_candidate.get("coverage_completion_depth_consistent_rows"),
        "candidate_conditioned_diagnostic_state": "candidate_conditioned_coverage_available",
        "candidate_correctness_label_for_evaluation_only": eval_candidate.get(
            "candidate_correctness_label_for_evaluation_only"
        ),
        "candidate_wrong_label_for_evaluation_only": eval_candidate.get("candidate_wrong_label_for_evaluation_only"),
        "evaluation_only_label_is_action_forbidden": True,
        "terminal_selector_allowed_from_this_branch": False,
        **common_flags(uses_gt_for_analysis=True),
    }


def retag_row(row: Mapping[str, Any], row_type: str, uses_gt_for_analysis: bool = False) -> dict[str, Any]:
    output = dict(row)
    output["schema_version"] = SCHEMA_VERSION
    output["row_type"] = row_type
    output["validation_stage"] = "fully_covered_goal_validity_failure_diagnostic_after_contract_freeze"
    output["diagnostic_branch"] = "fully_covered_goal_validity_failure_v1"
    output["terminal_selector_allowed_from_this_branch"] = False
    output.update(common_flags(uses_gt_for_analysis=uses_gt_for_analysis))
    return output


def materialize(contract_path: Path, out_root: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    target = target_row(contract)

    detector_pair_rows = [row for row in load_jsonl(path_from_contract(contract, "detector_pair_rows")) if target_matches(row, target)]
    detector_role_rows = [row for row in load_jsonl(path_from_contract(contract, "detector_role_rows")) if target_matches(row, target)]
    detector_candidate_view_rows = [
        row for row in load_jsonl(path_from_contract(contract, "detector_candidate_view_rows")) if target_matches(row, target)
    ]
    eval_pair_rows = [row for row in load_jsonl(path_from_contract(contract, "evaluation_join_pair_rows")) if target_matches(row, target)]
    eval_candidate_rows = [
        row for row in load_jsonl(path_from_contract(contract, "evaluation_join_candidate_rows")) if target_matches(row, target)
    ]
    eval_baseline_rows = [
        row for row in load_jsonl(path_from_contract(contract, "evaluation_join_baseline_rows")) if target_matches(row, target)
    ]

    if len(detector_pair_rows) != 1:
        raise ValueError(f"expected 1 detector pair row, got {len(detector_pair_rows)}")
    if len(eval_pair_rows) != 1:
        raise ValueError(f"expected 1 evaluation pair row, got {len(eval_pair_rows)}")

    target_pair_rows = [build_target_pair_row(detector_pair_rows[0], eval_pair_rows[0])]
    candidate_rows = [build_candidate_row(row) for row in sorted(eval_candidate_rows, key=lambda item: str(item.get("candidate_id")))]
    role_rows = [retag_row(row, "fully_covered_goal_validity_failure_role") for row in detector_role_rows]
    candidate_view_rows = [
        retag_row(row, "fully_covered_goal_validity_failure_candidate_view") for row in detector_candidate_view_rows
    ]
    evaluation_audit_rows = [
        retag_row(row, "fully_covered_goal_validity_failure_evaluation_audit", uses_gt_for_analysis=True)
        for row in eval_baseline_rows
    ]

    all_rows = target_pair_rows + candidate_rows + role_rows + candidate_view_rows + evaluation_audit_rows
    expected = contract.get("minimum_implementation_gates") or {}
    forbidden_keys = scan_forbidden_action_inputs(all_rows)
    terminal_commit_rows = sum(1 for row in all_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in all_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in all_rows if row.get("candidate_rejection") is True)
    uses_gt_for_action_true_rows = sum(1 for row in all_rows if row.get("uses_gt_for_action") is True)
    paper_claim_allowed_true_rows = sum(1 for row in all_rows if row.get("paper_claim_allowed") is True)

    gate = {
        "target_pair_rows_match": len(target_pair_rows) == int(expected.get("target_pair_rows", -1)),
        "target_candidate_rows_match": len(candidate_rows) == int(expected.get("target_candidate_rows", -1)),
        "target_role_rows_match": len(role_rows) == int(expected.get("target_role_rows", -1)),
        "target_candidate_view_rows_match": len(candidate_view_rows) == int(expected.get("target_candidate_view_rows", -1)),
        "target_baseline_audit_rows_match": len(evaluation_audit_rows) == int(expected.get("target_baseline_audit_rows", -1)),
        "forbidden_action_keys_absent": forbidden_keys == [],
        "no_terminal_commit_pass": terminal_commit_rows == 0,
        "no_candidate_commit_pass": candidate_commit_rows == 0,
        "no_candidate_rejection_pass": candidate_rejection_rows == 0,
        "no_gt_action_pass": uses_gt_for_action_true_rows == 0,
        "paper_claim_blocked_pass": paper_claim_allowed_true_rows == 0,
    }
    gate["fully_covered_goal_validity_failure_materializer_gate_passed"] = all(gate.values())

    write_jsonl(out_root / OUTPUT_FILES["target_pair_rows"], target_pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["role_rows"], role_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_view_rows"], candidate_view_rows)
    write_jsonl(out_root / OUTPUT_FILES["evaluation_audit_rows"], evaluation_audit_rows)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "contract": str(contract_path),
        "target_pair_rows": len(target_pair_rows),
        "candidate_rows": len(candidate_rows),
        "role_rows": len(role_rows),
        "candidate_view_rows": len(candidate_view_rows),
        "evaluation_audit_rows": len(evaluation_audit_rows),
        "target_pair_id": target.get("coverage_completion_pair_id"),
        "target_request_id": target.get("request_id"),
        "target_scene_key": target.get("scene_key"),
        "target_query": target.get("query"),
        "pair_evidence_state_counts": compact_counter(row.get("pair_evidence_state") for row in target_pair_rows),
        "candidate_role_counts": compact_counter(row.get("candidate_pair_role") for row in candidate_rows),
        "candidate_evaluation_label_counts_for_audit_only": compact_counter(
            "correct" if row.get("candidate_correctness_label_for_evaluation_only") is True else "wrong"
            for row in candidate_rows
        ),
        "candidate_view_state_counts": compact_counter(
            row.get("candidate_view_evidence_state") for row in candidate_view_rows
        ),
        "role_evidence_state_counts": compact_counter(row.get("role_evidence_state") for row in role_rows),
        "baseline_policy_counts_for_audit_only": compact_counter(row.get("policy_name") for row in evaluation_audit_rows),
        "action_evidence_forbidden_keys_found": forbidden_keys,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action_true_rows": uses_gt_for_action_true_rows,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed_true_rows": paper_claim_allowed_true_rows,
        "terminal_selector_allowed_from_this_branch": False,
        "terminal_utility_validation_allowed_after_materialization": False,
        "policy_scale_claim_allowed_after_materialization": False,
        "paper_claim_allowed_after_materialization": False,
        "gate": gate,
        "materializer_gate_passed": gate["fully_covered_goal_validity_failure_materializer_gate_passed"],
        "primary_blocker": "candidate_conditioned_goal_validity_rule_required",
        "next_task": "inspect_fully_covered_goal_validity_failure_candidate_conditioned_asymmetry",
    }
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    summary = materialize(resolve_path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
