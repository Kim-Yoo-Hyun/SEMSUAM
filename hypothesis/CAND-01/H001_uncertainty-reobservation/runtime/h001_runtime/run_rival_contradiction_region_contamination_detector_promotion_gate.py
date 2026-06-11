import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_detector_promotion_gate.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_detector_promotion_gate_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_detector_promotion_gate_v1"
OUTPUT_FILES = {
    "gate_rows": "rival_contradiction_region_contamination_detector_promotion_gate_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_detector_promotion_gate_summary.json",
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


def path_from_contract(contract: Mapping[str, Any], key: str) -> Path:
    path = Path(str((contract.get("source") or {}).get(key) or ""))
    if path.exists():
        return path
    if str(path).startswith("local_dataset/runs/"):
        runs_path = Path("/runs") / str(path).removeprefix("local_dataset/runs/")
        if runs_path.exists():
            return runs_path
    workspace_path = Path("/workspace") / path
    if workspace_path.exists():
        return workspace_path
    return path


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
    target = contract["target_scope"]
    summary = load_json(path_from_contract(contract, "evaluation_join_summary"))
    probe_rows = load_jsonl(path_from_contract(contract, "evaluation_join_promotion_probe_rows"))
    if len(probe_rows) != 1:
        raise RuntimeError({"unexpected_promotion_probe_rows": len(probe_rows)})
    probe = probe_rows[0]
    checks = {
        "evaluation_join_gate_passed": bool((summary.get("gate") or {}).get("evaluation_join_gate_passed")),
        "detector_evidence_state_pass": probe.get("detector_pair_evidence_state")
        == gate_contract["required_detector_pair_evidence_state"],
        "wrong_provisional_support_flagged_pass": probe.get("wrong_provisional_support_flagged_for_evaluation_only")
        is bool(gate_contract["wrong_provisional_support_flagged_for_evaluation_only"]),
        "wrong_goal_baseline_count_pass": int(probe.get("wrong_goal_baseline_count") or 0)
        >= int(gate_contract["minimum_wrong_goal_baseline_count"]),
        "wasted_path_exposure_pass": float(probe.get("max_wasted_path_exposure_m") or 0.0)
        >= float(gate_contract["minimum_wasted_path_exposure_m"]),
        "map_pose_consistency_delta_pass": float(probe.get("map_pose_consistency_delta") or 0.0)
        >= float(gate_contract["minimum_map_pose_consistency_delta"]),
        "terminal_commit_rows_pass": int(summary.get("terminal_commit_rows") or 0)
        <= int(gate_contract["maximum_terminal_commit_rows"]),
        "candidate_commit_rows_pass": int(summary.get("candidate_commit_rows") or 0)
        <= int(gate_contract["maximum_candidate_commit_rows"]),
        "candidate_rejection_rows_pass": int(summary.get("candidate_rejection_rows") or 0)
        <= int(gate_contract["maximum_candidate_rejection_rows"]),
        "uses_gt_for_action_pass": summary.get("uses_gt_for_action") is False and probe.get("uses_gt_for_action") is False,
        "paper_claim_blocked": summary.get("paper_claim_allowed") is False and probe.get("paper_claim_allowed") is False,
    }
    passed = all(checks.values())
    blockers = [key for key, value in checks.items() if not value]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_promotion_gate",
        "validation_stage": "bounded_single_case_promotion_gate_after_evaluation_join",
        "request_id": target["request_id"],
        "scene_key": target["scene_key"],
        "query": target["query"],
        "episode_key": target["episode_key"],
        "scope": target["scope"],
        "detector_pair_evidence_state": probe.get("detector_pair_evidence_state"),
        "wrong_provisional_support_flagged_for_evaluation_only": probe.get(
            "wrong_provisional_support_flagged_for_evaluation_only"
        ),
        "wrong_goal_baseline_count": probe.get("wrong_goal_baseline_count"),
        "max_wasted_path_exposure_m": probe.get("max_wasted_path_exposure_m"),
        "map_pose_consistency_delta": probe.get("map_pose_consistency_delta"),
        "map_pose_consistency_uncertainty_proxy": probe.get("map_pose_consistency_uncertainty_proxy"),
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

    contract = load_json(Path(args.contract))
    gate_row = build_gate_row(contract)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "gate_rows": 1,
        "promotion_gate_passed": gate_row["promotion_gate_passed"],
        "promotion_gate_blockers": gate_row["promotion_gate_blockers"],
        "wrong_goal_baseline_count": gate_row["wrong_goal_baseline_count"],
        "max_wasted_path_exposure_m": gate_row["max_wasted_path_exposure_m"],
        "map_pose_consistency_delta": gate_row["map_pose_consistency_delta"],
        "allowed_after_pass": gate_row["allowed_after_pass"],
        "terminal_selector_allowed_after_pass": False,
        "policy_scale_claim_allowed_after_pass": False,
        "paper_claim_allowed_after_pass": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "next_task": "scale_or_freeze_terminal_utility_contract_only_after_multi_case_evidence"
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / OUTPUT_FILES["gate_rows"], [gate_row])
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not gate_row["promotion_gate_passed"]:
        raise RuntimeError({"promotion_gate_blockers": gate_row["promotion_gate_blockers"]})


if __name__ == "__main__":
    main()
