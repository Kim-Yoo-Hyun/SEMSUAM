import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_multi_case_promotion_gate.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_rival_contradiction_region_contamination_multi_case_promotion_gate_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_promotion_gate_v1"
OUTPUT_FILES = {
    "gate_rows": "rival_contradiction_region_contamination_multi_case_promotion_gate_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_multi_case_promotion_gate_summary.json",
}

CONTAMINATION_STATES = {
    "cross_candidate_contamination_observed",
    "rival_region_contamination_or_same_category_overlap_observed",
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


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def build_gate_row(contract: Mapping[str, Any]) -> Dict[str, Any]:
    gate_contract = contract["promotion_gate"]
    scope = contract["target_scope"]
    summary = load_json(path_from_contract(contract, "evaluation_join_summary"))
    pair_rows = load_jsonl(path_from_contract(contract, "evaluation_join_pair_rows"))
    probe_rows = load_jsonl(path_from_contract(contract, "evaluation_join_promotion_probe_rows"))

    contamination_rows = [
        row for row in pair_rows if row.get("detector_pair_evidence_state") in CONTAMINATION_STATES
    ]
    wrong_labeled_rows = [
        row
        for row in pair_rows
        if row.get("candidate_pair_label_pattern_for_evaluation_only") in {"a_wrong_b_correct", "both_wrong"}
    ]
    wrong_labeled_contamination_rows = [
        row
        for row in wrong_labeled_rows
        if row.get("detector_pair_evidence_state") in CONTAMINATION_STATES
    ]

    checks = {
        "evaluation_join_gate_passed": bool((summary.get("gate") or {}).get("multi_case_evaluation_join_gate_passed")),
        "pair_rows_pass": len(pair_rows) >= int(gate_contract["minimum_pair_rows"]),
        "contamination_or_contradiction_pair_rows_pass": len(contamination_rows)
        >= int(gate_contract["minimum_contamination_or_contradiction_pair_rows"]),
        "wrong_labeled_pair_rows_pass": len(wrong_labeled_rows)
        >= int(gate_contract["minimum_wrong_labeled_pair_rows"]),
        "wrong_labeled_contamination_pair_rows_pass": len(wrong_labeled_contamination_rows)
        >= int(gate_contract["minimum_wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence"]),
        "wrong_goal_baseline_rows_pass": int(summary.get("total_wrong_goal_baseline_rows") or 0)
        >= int(gate_contract["minimum_wrong_goal_baseline_rows"]),
        "wasted_path_exposure_pass": float(summary.get("max_wasted_path_exposure_m") or 0.0)
        >= float(gate_contract["minimum_max_wasted_path_exposure_m"]),
        "slam_map_pose_delta_rows_pass": int(summary.get("slam_map_pose_delta_rows") or 0)
        >= int(gate_contract["minimum_slam_map_pose_delta_rows"]),
        "slam_map_pose_delta_maximum_pass": float(summary.get("slam_map_pose_delta_maximum") or 0.0)
        >= float(gate_contract["minimum_slam_map_pose_delta_maximum"]),
        "promotion_ready_rows_remain_blocked_pass": int(summary.get("promotion_ready_rows") or 0)
        == int(gate_contract["promotion_ready_rows_must_remain"]),
        "terminal_commit_rows_pass": int(summary.get("terminal_commit_rows") or 0)
        <= int(gate_contract["maximum_terminal_commit_rows"]),
        "candidate_commit_rows_pass": int(summary.get("candidate_commit_rows") or 0)
        <= int(gate_contract["maximum_candidate_commit_rows"]),
        "candidate_rejection_rows_pass": int(summary.get("candidate_rejection_rows") or 0)
        <= int(gate_contract["maximum_candidate_rejection_rows"]),
        "uses_gt_for_action_pass": summary.get("uses_gt_for_action") is False
        and not any(row.get("uses_gt_for_action") is True for row in probe_rows),
        "paper_claim_blocked": summary.get("paper_claim_allowed") is False
        and not any(row.get("paper_claim_allowed") is True for row in probe_rows),
    }
    passed = all(checks.values())
    blockers = [key for key, value in checks.items() if not value]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_promotion_gate",
        "validation_stage": "bounded_multi_case_diagnostic_readiness_after_evaluation_join",
        "scope": scope["scope"],
        "source_pair_rows": len(pair_rows),
        "scene_count": scope["scene_count"],
        "query_count": scope["query_count"],
        "contamination_or_contradiction_pair_rows": len(contamination_rows),
        "wrong_labeled_pair_rows": len(wrong_labeled_rows),
        "wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence": len(
            wrong_labeled_contamination_rows
        ),
        "total_wrong_goal_baseline_rows": summary.get("total_wrong_goal_baseline_rows"),
        "max_wasted_path_exposure_m": summary.get("max_wasted_path_exposure_m"),
        "slam_map_pose_delta_rows": summary.get("slam_map_pose_delta_rows"),
        "slam_map_pose_delta_maximum": summary.get("slam_map_pose_delta_maximum"),
        "promotion_ready_rows": summary.get("promotion_ready_rows"),
        "promotion_gate_checks": checks,
        "promotion_gate_passed": passed,
        "promotion_gate_blockers": blockers,
        "allowed_after_pass": contract["claim_boundary"]["allowed_after_pass"] if passed else "not_promoted",
        "terminal_selector_allowed_after_pass": False,
        "policy_scale_claim_allowed_after_pass": False,
        "paper_claim_allowed_after_pass": False,
        "next_valid_research_step": contract["claim_boundary"]["next_valid_research_step"],
        **common_flags(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(resolve_path(args.contract))
    gate_row = build_gate_row(contract)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "gate_rows": 1,
        "promotion_gate_passed": gate_row["promotion_gate_passed"],
        "promotion_gate_blockers": gate_row["promotion_gate_blockers"],
        "allowed_after_pass": gate_row["allowed_after_pass"],
        "source_pair_rows": gate_row["source_pair_rows"],
        "contamination_or_contradiction_pair_rows": gate_row["contamination_or_contradiction_pair_rows"],
        "wrong_labeled_pair_rows": gate_row["wrong_labeled_pair_rows"],
        "wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence": gate_row[
            "wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence"
        ],
        "total_wrong_goal_baseline_rows": gate_row["total_wrong_goal_baseline_rows"],
        "max_wasted_path_exposure_m": gate_row["max_wasted_path_exposure_m"],
        "slam_map_pose_delta_rows": gate_row["slam_map_pose_delta_rows"],
        "slam_map_pose_delta_maximum": gate_row["slam_map_pose_delta_maximum"],
        "promotion_ready_rows": gate_row["promotion_ready_rows"],
        "terminal_selector_allowed_after_pass": False,
        "policy_scale_claim_allowed_after_pass": False,
        "paper_claim_allowed_after_pass": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "next_task": "freeze_nonterminal_diagnostic_report_or_separate_terminal_utility_contract",
    }
    out_root = resolve_path(args.out_root)
    write_jsonl(out_root / OUTPUT_FILES["gate_rows"], [gate_row])
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not gate_row["promotion_gate_passed"]:
        raise RuntimeError({"promotion_gate_blockers": gate_row["promotion_gate_blockers"]})


if __name__ == "__main__":
    main()
