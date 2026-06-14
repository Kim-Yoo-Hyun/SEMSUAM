import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "h001.goal_region_object_relation_coverage_completion_promotion_gate.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_goal_region_object_relation_coverage_completion_promotion_gate_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_goal_region_object_relation_coverage_completion_promotion_gate_v1"
SUMMARY_NAME = "goal_region_object_relation_coverage_completion_promotion_gate_summary.json"


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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(resolve_path(args.contract))
    out_root = resolve_path(args.out_root)

    join_summary = load_json(path_from_contract(contract, "evaluation_join_summary"))
    pair_rows = load_jsonl(path_from_contract(contract, "evaluation_join_pair_rows"))
    request_rows = load_jsonl(path_from_contract(contract, "evaluation_join_request_rows"))
    promotion_rows = load_jsonl(path_from_contract(contract, "evaluation_join_promotion_probe_rows"))

    req = contract["promotion_gate_contract"]["diagnostic_requirements"]
    evidence_label_cross = Counter(
        (row.get("coverage_completion_pair_evidence_state"), row.get("candidate_pair_label_pattern_for_evaluation_only"))
        for row in pair_rows
    )
    fully_covered_rows = sum(
        1
        for row in pair_rows
        if row.get("coverage_completion_pair_evidence_state")
        == "goal_region_both_candidates_supported_object_relation_supported"
    )
    fully_covered_wrong_or_ambiguous_rows = sum(
        1
        for row in pair_rows
        if row.get("coverage_completion_pair_evidence_state")
        == "goal_region_both_candidates_supported_object_relation_supported"
        and row.get("candidate_pair_label_pattern_for_evaluation_only") != "both_correct"
    )
    object_relation_gap_rows = sum(
        1
        for row in pair_rows
        if row.get("coverage_completion_pair_evidence_state")
        == "goal_region_both_candidates_supported_object_relation_missing"
    )
    wrong_goal_baseline_rows = sum(int(row.get("wrong_goal_baseline_count_for_evaluation_only") or 0) for row in request_rows)
    max_wasted = max(float(row.get("max_wasted_path_exposure_m_for_evaluation_only") or 0.0) for row in request_rows)
    slam_rows = sum(1 for row in request_rows if row.get("slam_map_pose_consistency_delta_for_evaluation_only") is not None)
    terminal_commit_rows = sum(1 for row in pair_rows + request_rows + promotion_rows if row.get("terminal_commit"))
    candidate_commit_rows = sum(1 for row in pair_rows + request_rows + promotion_rows if row.get("candidate_commit"))
    candidate_rejection_rows = sum(1 for row in pair_rows + request_rows + promotion_rows if row.get("candidate_rejection"))

    gate = {
        "source_evaluation_join_gate_passed": bool(
            join_summary.get("gate", {}).get("goal_region_object_relation_coverage_completion_evaluation_join_gate_passed")
        ),
        "wrong_goal_baseline_rows_pass": wrong_goal_baseline_rows >= int(req["wrong_goal_baseline_rows_minimum"]),
        "max_wasted_path_exposure_pass": max_wasted >= float(req["max_wasted_path_exposure_m_minimum"]),
        "slam_map_pose_delta_rows_pass": slam_rows >= int(req["slam_map_pose_delta_rows_minimum"]),
        "fully_covered_evidence_rows_pass": fully_covered_rows >= int(req["fully_covered_evidence_rows_minimum"]),
        "fully_covered_wrong_or_ambiguous_rows_pass": fully_covered_wrong_or_ambiguous_rows
        >= int(req["fully_covered_wrong_or_ambiguous_rows_minimum"]),
        "object_relation_gap_rows_pass": object_relation_gap_rows >= int(req["object_relation_gap_rows_minimum"]),
        "no_terminal_commit_pass": terminal_commit_rows <= int(req["terminal_commit_rows_maximum"]),
        "no_candidate_commit_pass": candidate_commit_rows <= int(req["candidate_commit_rows_maximum"]),
        "no_candidate_rejection_pass": candidate_rejection_rows <= int(req["candidate_rejection_rows_maximum"]),
        "no_gt_action_pass": not any(row.get("uses_gt_for_action") for row in pair_rows + request_rows + promotion_rows),
        "paper_claim_blocked_pass": not any(row.get("paper_claim_allowed") for row in pair_rows + request_rows + promotion_rows),
    }
    gate["goal_region_object_relation_coverage_completion_promotion_gate_passed"] = all(gate.values())

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed" if gate["goal_region_object_relation_coverage_completion_promotion_gate_passed"] else "failed",
        "contract": args.contract,
        "source_evaluation_join_summary": str(path_from_contract(contract, "evaluation_join_summary")),
        "pair_rows": len(pair_rows),
        "request_rows": len(request_rows),
        "promotion_probe_rows": len(promotion_rows),
        "pair_label_counts_for_evaluation_only": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_rows
        ),
        "evidence_label_cross_counts_for_evaluation_only": {
            f"{key[0]}|{key[1]}": value for key, value in sorted(evidence_label_cross.items())
        },
        "fully_covered_rows": fully_covered_rows,
        "fully_covered_wrong_or_ambiguous_rows": fully_covered_wrong_or_ambiguous_rows,
        "object_relation_gap_rows": object_relation_gap_rows,
        "wrong_goal_baseline_rows_for_evaluation_only": wrong_goal_baseline_rows,
        "max_wasted_path_exposure_m_for_evaluation_only": max_wasted,
        "slam_map_pose_delta_rows_for_evaluation_only": slam_rows,
        "slam_map_pose_delta_max_for_evaluation_only": max(
            float(row.get("slam_map_pose_consistency_delta_for_evaluation_only") or 0.0) for row in request_rows
        ),
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "gate": gate,
        "promotion_gate_passed": gate["goal_region_object_relation_coverage_completion_promotion_gate_passed"],
        "promotion_gate_blockers": [key for key, value in gate.items() if key != "goal_region_object_relation_coverage_completion_promotion_gate_passed" and not value],
        "allowed_after_pass": contract["promotion_gate_contract"]["allowed_outcomes_after_pass"]
        if gate["goal_region_object_relation_coverage_completion_promotion_gate_passed"]
        else [],
        "terminal_selector_allowed_after_pass": False,
        "terminal_utility_validation_allowed_after_pass": False,
        "policy_scale_claim_allowed_after_pass": False,
        "paper_claim_allowed_after_pass": False,
        "failure_taxonomy": contract["promotion_gate_contract"]["failure_taxonomy"],
        "next_task": "close_goal_region_object_relation_coverage_completion_branch_as_diagnostic_only",
    }

    write_json(out_root / SUMMARY_NAME, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not gate["goal_region_object_relation_coverage_completion_promotion_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
