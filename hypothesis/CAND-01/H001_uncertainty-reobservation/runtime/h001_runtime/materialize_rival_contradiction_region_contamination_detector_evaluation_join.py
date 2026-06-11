import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_detector_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_detector_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_detector_evaluation_join_v1"

OUTPUT_FILES = {
    "request_rows": "rival_contradiction_region_contamination_detector_evaluation_join_request_rows.jsonl",
    "candidate_rows": "rival_contradiction_region_contamination_detector_evaluation_join_candidate_rows.jsonl",
    "pair_rows": "rival_contradiction_region_contamination_detector_evaluation_join_pair_rows.jsonl",
    "baseline_rows": "rival_contradiction_region_contamination_detector_evaluation_join_baseline_rows.jsonl",
    "promotion_probe_rows": "rival_contradiction_region_contamination_detector_evaluation_join_promotion_probe_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_detector_evaluation_join_summary.json",
}

POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")


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


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def common_eval_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def target_match(row: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    return (
        str(row.get("request_id") or row.get("expanded_retrieval_request_id") or "") == target["request_id"]
        and str(row.get("scene_key") or "") == target["scene_key"]
        and str(row.get("query") or "") == target["query"]
        and str(row.get("episode_key") or "") == target["episode_key"]
        and str(row.get("source_name") or "") == target["source_name"]
    )


def policy_name(row: Mapping[str, Any]) -> str:
    nested = row.get("join_key")
    if isinstance(nested, Mapping) and nested.get("policy_name"):
        return str(nested["policy_name"])
    return str(row.get("policy_name") or "")


def candidate_row(
    candidate_eval: Mapping[str, Any],
    detector_candidate_rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> Dict[str, Any]:
    candidate_id = str(candidate_eval.get("candidate_id") or "")
    role_rows = [row for row in detector_candidate_rows if str(row.get("candidate_id") or "") == candidate_id]
    associated_rows = sum(int(row.get("associated_rows") or 0) for row in role_rows)
    depth_consistent_rows = sum(int(row.get("depth_consistent_rows") or 0) for row in role_rows)
    role_states = {str(row.get("role")): row.get("candidate_evidence_state") for row in role_rows}
    role = "provisionally_supported_candidate"
    if candidate_id == target["rival_candidate_id"]:
        role = "rival_candidate"
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_evaluation_join_candidate",
        "validation_stage": "evaluation_only_join_after_detector_evidence_freeze",
        "request_id": target["request_id"],
        "scene_key": target["scene_key"],
        "query": target["query"],
        "episode_key": target["episode_key"],
        "source_name": target["source_name"],
        "candidate_id": candidate_id,
        "candidate_role": role,
        "detector_role_rows": len(role_rows),
        "detector_associated_rows": associated_rows,
        "detector_depth_consistent_rows": depth_consistent_rows,
        "detector_candidate_evidence_states_by_role": role_states,
        "evaluation_only_candidate_label_join": True,
        "candidate_correctness_label_for_evaluation_only": candidate_eval.get("candidate_correctness_label_for_evaluation_only"),
        "candidate_wrong_label_for_evaluation_only": candidate_eval.get("candidate_wrong_label_for_evaluation_only"),
        "goal_validity_risk_state": candidate_eval.get("goal_validity_risk_state"),
        "goal_validity_risk_proxy": candidate_eval.get("goal_validity_risk_proxy"),
        "map_pose_consistency_delta": candidate_eval.get("map_pose_consistency_delta"),
        "map_pose_consistency_uncertainty_proxy": candidate_eval.get("map_pose_consistency_uncertainty_proxy"),
        "pose_graph_connectivity_delta": candidate_eval.get("pose_graph_connectivity_delta"),
        "viewpoint_coverage_delta": candidate_eval.get("viewpoint_coverage_delta"),
        "rule_output_frozen_before_evaluation_join": candidate_eval.get("rule_output_frozen_before_evaluation_join"),
        "detector_evidence_frozen_before_evaluation_join": True,
        "terminal_selector_allowed_from_this_join": False,
        **common_eval_flags(),
    }


def pair_row(
    detector_pair: Mapping[str, Any],
    pair_eval: Mapping[str, Any],
    request_eval: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> Dict[str, Any]:
    wrong_candidate = next((row for row in candidate_rows if row.get("candidate_wrong_label_for_evaluation_only") is True), {})
    correct_candidate = next((row for row in candidate_rows if row.get("candidate_correctness_label_for_evaluation_only") is True), {})
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_evaluation_join_pair",
        "validation_stage": "evaluation_only_join_after_detector_evidence_freeze",
        "request_id": target["request_id"],
        "scene_key": target["scene_key"],
        "query": target["query"],
        "episode_key": target["episode_key"],
        "source_name": target["source_name"],
        "candidate_a_id": target["provisionally_supported_candidate_id"],
        "candidate_b_id": target["rival_candidate_id"],
        "provisionally_supported_candidate_id": target["provisionally_supported_candidate_id"],
        "rival_candidate_id": target["rival_candidate_id"],
        "detector_pair_evidence_state": detector_pair.get("pair_evidence_state"),
        "detector_contamination_or_contradiction_evidence_available": detector_pair.get(
            "contamination_or_contradiction_evidence_available"
        ),
        "detector_dual_candidate_association_role_count": detector_pair.get("dual_candidate_association_role_count"),
        "detector_single_candidate_isolation_role_count": detector_pair.get("single_candidate_isolation_role_count"),
        "candidate_pair_label_pattern_for_evaluation_only": pair_eval.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "wrong_provisional_support_flagged_for_evaluation_only": (
            wrong_candidate.get("candidate_id") == target["provisionally_supported_candidate_id"]
            and detector_pair.get("contamination_or_contradiction_evidence_available") is True
        ),
        "correct_rival_candidate_id_for_evaluation_only": correct_candidate.get("candidate_id"),
        "provisional_rule_candidate_wrong_for_evaluation_only": pair_eval.get(
            "provisional_rule_candidate_wrong_for_evaluation_only"
        ),
        "provisional_rule_candidate_correct_for_evaluation_only": pair_eval.get(
            "provisional_rule_candidate_correct_for_evaluation_only"
        ),
        "goal_validity_risk_state": request_eval.get("goal_validity_risk_state"),
        "viewpoint_evidence_gap_state": request_eval.get("viewpoint_evidence_gap_state"),
        "viewpoint_evidence_gap_proxy": request_eval.get("viewpoint_evidence_gap_proxy"),
        "map_pose_consistency_delta": request_eval.get("map_pose_consistency_delta"),
        "map_pose_consistency_uncertainty_proxy": request_eval.get("map_pose_consistency_uncertainty_proxy"),
        "map_pose_consistency_uncertainty_state": request_eval.get("map_pose_consistency_uncertainty_state"),
        "pose_graph_connectivity_delta": request_eval.get("pose_graph_connectivity_delta"),
        "pairwise_map_pose_consistency_abs_delta": pair_eval.get("map_pose_consistency_abs_delta"),
        "pairwise_pose_graph_connectivity_abs_delta": pair_eval.get("pose_graph_connectivity_abs_delta"),
        "rule_output_frozen_before_evaluation_join": pair_eval.get("rule_output_frozen_before_evaluation_join"),
        "detector_evidence_frozen_before_evaluation_join": True,
        "labels_are_evaluation_only": True,
        "terminal_selector_allowed_from_this_join": False,
        **common_eval_flags(),
    }


def baseline_row(source: Mapping[str, Any], target: Mapping[str, Any], detector_pair: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_evaluation_join_baseline",
        "validation_stage": "evaluation_only_join_after_detector_evidence_freeze",
        "request_id": target["request_id"],
        "scene_key": target["scene_key"],
        "query": target["query"],
        "episode_key": target["episode_key"],
        "source_name": target["source_name"],
        "policy_name": policy_name(source),
        "policy_selected_candidate_id": source.get("policy_selected_candidate_id"),
        "selector_action": source.get("selector_action"),
        "selector_id": source.get("selector_id"),
        "wrong_goal_visit_proxy": source.get("wrong_goal_visit_proxy"),
        "wasted_path_proxy_m": source.get("wasted_path_proxy_m"),
        "success_commit_proxy": source.get("success_commit_proxy"),
        "terminal_commit_proxy": source.get("terminal_commit_proxy"),
        "map_pose_consistency_delta": source.get("map_pose_consistency_delta"),
        "pose_graph_connectivity_delta": source.get("pose_graph_connectivity_delta"),
        "evaluation_only_baseline_context": True,
        "detector_pair_evidence_state": detector_pair.get("pair_evidence_state"),
        "not_used_for_action": True,
        **common_eval_flags(),
    }


def request_row(
    request_eval: Mapping[str, Any],
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    target: Mapping[str, Any],
) -> Dict[str, Any]:
    wrong_goal_count = sum(1 for row in baseline_rows if row.get("wrong_goal_visit_proxy") is True)
    wasted_path_values = [float(row.get("wasted_path_proxy_m") or 0.0) for row in baseline_rows]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_evaluation_join_request",
        "validation_stage": "evaluation_only_join_after_detector_evidence_freeze",
        "request_id": target["request_id"],
        "scene_key": target["scene_key"],
        "query": target["query"],
        "episode_key": target["episode_key"],
        "source_name": target["source_name"],
        "detector_pair_evidence_state_counts": compact_counter(row.get("detector_pair_evidence_state") for row in pair_rows),
        "candidate_label_counts": compact_counter(
            "correct" if row.get("candidate_correctness_label_for_evaluation_only") is True else "wrong"
            for row in candidate_rows
        ),
        "wrong_goal_baseline_count": wrong_goal_count,
        "baseline_wrong_goal_exposure": {
            str(row.get("policy_name")): row.get("wrong_goal_visit_proxy") for row in baseline_rows
        },
        "baseline_wasted_path_exposure_m": {
            str(row.get("policy_name")): row.get("wasted_path_proxy_m") for row in baseline_rows
        },
        "max_wasted_path_exposure_m": max(wasted_path_values) if wasted_path_values else 0.0,
        "goal_validity_risk_state": request_eval.get("goal_validity_risk_state"),
        "goal_validity_risk_proxy": request_eval.get("goal_validity_risk_proxy"),
        "viewpoint_evidence_gap_state": request_eval.get("viewpoint_evidence_gap_state"),
        "viewpoint_evidence_gap_proxy": request_eval.get("viewpoint_evidence_gap_proxy"),
        "map_pose_consistency_delta": request_eval.get("map_pose_consistency_delta"),
        "map_pose_consistency_uncertainty_proxy": request_eval.get("map_pose_consistency_uncertainty_proxy"),
        "map_pose_consistency_uncertainty_state": request_eval.get("map_pose_consistency_uncertainty_state"),
        "pose_graph_connectivity_delta": request_eval.get("pose_graph_connectivity_delta"),
        "evaluation_labels_joined_after_detector_evidence_freeze": True,
        "terminal_selector_allowed_from_this_join": False,
        **common_eval_flags(),
    }


def promotion_probe_row(request: Mapping[str, Any], pair: Mapping[str, Any], target: Mapping[str, Any], gate: Mapping[str, bool]) -> Dict[str, Any]:
    gate_passed = all(gate.values())
    blockers = [key for key, value in gate.items() if not value]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_detector_evaluation_join_promotion_probe",
        "validation_stage": "evaluation_only_join_after_detector_evidence_freeze",
        "request_id": target["request_id"],
        "scene_key": target["scene_key"],
        "query": target["query"],
        "episode_key": target["episode_key"],
        "source_name": target["source_name"],
        "detector_pair_evidence_state": pair.get("detector_pair_evidence_state"),
        "wrong_provisional_support_flagged_for_evaluation_only": pair.get(
            "wrong_provisional_support_flagged_for_evaluation_only"
        ),
        "wrong_goal_baseline_count": request.get("wrong_goal_baseline_count"),
        "max_wasted_path_exposure_m": request.get("max_wasted_path_exposure_m"),
        "map_pose_consistency_delta": request.get("map_pose_consistency_delta"),
        "map_pose_consistency_uncertainty_proxy": request.get("map_pose_consistency_uncertainty_proxy"),
        "promotion_probe_gate_passed": gate_passed,
        "promotion_probe_blockers": blockers,
        "bounded_single_case_only": True,
        "terminal_selector_allowed_from_this_probe": False,
        **common_eval_flags(),
    }


def build_outputs(contract: Mapping[str, Any]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    target = contract["target_pair"]
    min_gate = contract["minimum_join_gate"]
    evidence_summary = load_json(path_from_contract(contract, "detector_evidence_summary"))
    detector_pair_rows = [row for row in load_jsonl(path_from_contract(contract, "detector_pair_rows")) if target_match(row, target)]
    detector_candidate_role_rows = [
        row for row in load_jsonl(path_from_contract(contract, "detector_candidate_role_rows")) if target_match(row, target)
    ]
    request_eval_rows = [
        row for row in load_jsonl(path_from_contract(contract, "pairwise_eval_request_rows")) if target_match(row, target)
    ]
    candidate_eval_rows = [
        row for row in load_jsonl(path_from_contract(contract, "pairwise_eval_candidate_rows")) if target_match(row, target)
    ]
    pair_eval_rows = [row for row in load_jsonl(path_from_contract(contract, "pairwise_eval_pair_rows")) if target_match(row, target)]
    baseline_source_rows = [
        row for row in load_jsonl(path_from_contract(contract, "pairwise_eval_baseline_rows")) if target_match(row, target)
    ]
    if len(detector_pair_rows) != 1 or len(request_eval_rows) != 1 or len(pair_eval_rows) != 1:
        raise RuntimeError(
            {
                "detector_pair_rows": len(detector_pair_rows),
                "request_eval_rows": len(request_eval_rows),
                "pair_eval_rows": len(pair_eval_rows),
            }
        )
    detector_pair = detector_pair_rows[0]
    request_eval = request_eval_rows[0]
    pair_eval = pair_eval_rows[0]
    candidate_rows = [candidate_row(row, detector_candidate_role_rows, target) for row in sorted(candidate_eval_rows, key=lambda row: str(row.get("candidate_id")))]
    pair_rows = [pair_row(detector_pair, pair_eval, request_eval, candidate_rows, target)]
    baseline_rows = [
        baseline_row(row, target, detector_pair)
        for row in sorted(baseline_source_rows, key=lambda row: POLICIES.index(policy_name(row)) if policy_name(row) in POLICIES else 999)
    ]
    request_rows = [request_row(request_eval, pair_rows, candidate_rows, baseline_rows, target)]

    gate = {
        "source_detector_evidence_gate_passed": bool(
            (evidence_summary.get("gate") or {}).get("detector_evidence_materializer_gate_passed")
        ),
        "request_rows_match": len(request_rows) == int(min_gate["expected_request_rows"]),
        "candidate_rows_match": len(candidate_rows) == int(min_gate["expected_candidate_rows"]),
        "pair_rows_match": len(pair_rows) == int(min_gate["expected_pair_rows"]),
        "baseline_rows_match": len(baseline_rows) == int(min_gate["expected_baseline_rows"]),
        "pair_label_pattern_match": pair_eval.get("candidate_pair_label_pattern_for_evaluation_only")
        == min_gate["expected_pair_label_pattern"],
        "wrong_provisional_candidate_match": any(
            row.get("candidate_id") == min_gate["expected_wrong_provisional_candidate_id"]
            and row.get("candidate_wrong_label_for_evaluation_only") is True
            for row in candidate_rows
        ),
        "correct_rival_candidate_match": any(
            row.get("candidate_id") == min_gate["expected_correct_rival_candidate_id"]
            and row.get("candidate_correctness_label_for_evaluation_only") is True
            for row in candidate_rows
        ),
        "wrong_goal_baseline_count_pass": request_rows[0]["wrong_goal_baseline_count"]
        >= int(min_gate["minimum_wrong_goal_baseline_count"]),
        "wasted_path_exposure_pass": request_rows[0]["max_wasted_path_exposure_m"]
        >= float(min_gate["minimum_wasted_path_exposure_m"]),
        "map_pose_consistency_delta_pass": float(request_rows[0]["map_pose_consistency_delta"] or 0.0)
        >= float(min_gate["minimum_map_pose_consistency_delta"]),
        "terminal_commit_rows_pass": not any(row.get("terminal_commit") is True for row in request_rows + candidate_rows + pair_rows + baseline_rows),
        "candidate_commit_rows_pass": not any(row.get("candidate_commit") is True for row in request_rows + candidate_rows + pair_rows + baseline_rows),
        "candidate_rejection_rows_pass": not any(row.get("candidate_rejection") is True for row in request_rows + candidate_rows + pair_rows + baseline_rows),
        "uses_gt_for_action_pass": not any(row.get("uses_gt_for_action") is True for row in request_rows + candidate_rows + pair_rows + baseline_rows),
        "paper_claim_blocked": not any(row.get("paper_claim_allowed") is True for row in request_rows + candidate_rows + pair_rows + baseline_rows),
    }
    promotion_rows = [promotion_probe_row(request_rows[0], pair_rows[0], target, gate)]
    gate["promotion_probe_rows_match"] = len(promotion_rows) == int(min_gate["expected_promotion_probe_rows"])
    gate["evaluation_join_gate_passed"] = all(gate.values())

    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "request_rows": len(request_rows),
        "candidate_rows": len(candidate_rows),
        "pair_rows": len(pair_rows),
        "baseline_rows": len(baseline_rows),
        "promotion_probe_rows": len(promotion_rows),
        "candidate_label_counts": request_rows[0]["candidate_label_counts"],
        "pair_label_pattern_counts": compact_counter(row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_rows),
        "detector_pair_evidence_state_counts": request_rows[0]["detector_pair_evidence_state_counts"],
        "wrong_goal_baseline_count": request_rows[0]["wrong_goal_baseline_count"],
        "max_wasted_path_exposure_m": request_rows[0]["max_wasted_path_exposure_m"],
        "map_pose_consistency_delta": request_rows[0]["map_pose_consistency_delta"],
        "map_pose_consistency_uncertainty_proxy": request_rows[0]["map_pose_consistency_uncertainty_proxy"],
        "terminal_commit_rows": 0,
        "candidate_commit_rows": 0,
        "candidate_rejection_rows": 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "gate": gate,
        "next_task": "run_rival_contradiction_region_contamination_detector_promotion_gate",
    }
    return request_rows, candidate_rows, pair_rows, baseline_rows, promotion_rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(Path(args.contract))
    request_rows, candidate_rows, pair_rows, baseline_rows, promotion_rows, summary = build_outputs(contract)
    out_root = Path(args.out_root)
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["promotion_probe_rows"], promotion_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["evaluation_join_gate_passed"]:
        raise RuntimeError("evaluation join gate failed")


if __name__ == "__main__":
    main()
