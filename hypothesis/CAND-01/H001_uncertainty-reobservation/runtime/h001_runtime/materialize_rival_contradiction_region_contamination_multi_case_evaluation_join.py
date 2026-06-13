import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_multi_case_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_multi_case_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_evaluation_join_v1"

OUTPUT_FILES = {
    "request_rows": "rival_contradiction_region_contamination_multi_case_evaluation_join_request_rows.jsonl",
    "candidate_rows": "rival_contradiction_region_contamination_multi_case_evaluation_join_candidate_rows.jsonl",
    "pair_rows": "rival_contradiction_region_contamination_multi_case_evaluation_join_pair_rows.jsonl",
    "baseline_rows": "rival_contradiction_region_contamination_multi_case_evaluation_join_baseline_rows.jsonl",
    "promotion_probe_rows": "rival_contradiction_region_contamination_multi_case_evaluation_join_promotion_probe_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_multi_case_evaluation_join_summary.json",
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


def key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    join_key = row.get("join_key") if isinstance(row.get("join_key"), Mapping) else {}
    return (
        str(row.get("scene_key") or join_key.get("scene_key") or ""),
        str(row.get("query") or join_key.get("query") or ""),
        str(row.get("request_id") or row.get("expanded_retrieval_request_id") or join_key.get("request_id") or ""),
        str(row.get("episode_key") or join_key.get("episode_key") or ""),
        str(row.get("source_name") or join_key.get("source_name") or ""),
    )


def candidate_key(row: Mapping[str, Any]) -> Tuple[Tuple[str, str, str, str, str], str]:
    join_key = row.get("join_key") if isinstance(row.get("join_key"), Mapping) else {}
    return key(row), str(row.get("candidate_id") or join_key.get("candidate_id") or "")


def policy_name(row: Mapping[str, Any]) -> str:
    join_key = row.get("join_key") if isinstance(row.get("join_key"), Mapping) else {}
    return str(row.get("policy_name") or join_key.get("policy_name") or "")


def first(rows: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
    return rows[0] if rows else {}


def build_candidate_row(
    eval_row: Mapping[str, Any],
    detector_candidate_views: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    associated_rows = sum(int(row.get("associated_rows") or 0) for row in detector_candidate_views)
    depth_consistent_rows = sum(int(row.get("depth_consistent_rows") or 0) for row in detector_candidate_views)
    view_states = {str(row.get("role")): row.get("candidate_view_evidence_state") for row in detector_candidate_views}
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_evaluation_join_candidate",
        "validation_stage": "evaluation_only_join_after_multi_case_evidence_freeze",
        "scene_key": eval_row.get("scene_key"),
        "query": eval_row.get("query"),
        "episode_key": eval_row.get("episode_key"),
        "source_name": eval_row.get("source_name"),
        "request_id": eval_row.get("request_id"),
        "candidate_id": eval_row.get("candidate_id"),
        "candidate_pair_role": eval_row.get("candidate_pair_role"),
        "detector_candidate_view_rows": len(detector_candidate_views),
        "detector_associated_rows": associated_rows,
        "detector_depth_consistent_rows": depth_consistent_rows,
        "detector_candidate_view_states_by_role": view_states,
        "evaluation_only_candidate_label_join": True,
        "candidate_correctness_label_for_evaluation_only": eval_row.get("candidate_correctness_label_for_evaluation_only"),
        "candidate_wrong_label_for_evaluation_only": eval_row.get("candidate_wrong_label_for_evaluation_only"),
        "goal_validity_risk_state": eval_row.get("goal_validity_risk_state"),
        "goal_validity_risk_proxy": eval_row.get("goal_validity_risk_proxy"),
        "viewpoint_coverage_delta_for_evaluation_only": eval_row.get("viewpoint_coverage_delta"),
        "map_pose_consistency_delta_for_evaluation_only": eval_row.get("map_pose_consistency_delta"),
        "map_pose_consistency_uncertainty_proxy_for_evaluation_only": eval_row.get(
            "map_pose_consistency_uncertainty_proxy"
        ),
        "pose_graph_connectivity_delta_for_evaluation_only": eval_row.get("pose_graph_connectivity_delta"),
        "detector_evidence_frozen_before_evaluation_join": True,
        "terminal_selector_allowed_from_this_join": False,
        **common_eval_flags(),
    }


def build_pair_row(
    detector_pair: Mapping[str, Any],
    eval_pair: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    wrong_candidates = [row for row in candidate_rows if row.get("candidate_wrong_label_for_evaluation_only") is True]
    correct_candidates = [row for row in candidate_rows if row.get("candidate_correctness_label_for_evaluation_only") is True]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_evaluation_join_pair",
        "validation_stage": "evaluation_only_join_after_multi_case_evidence_freeze",
        "scene_key": eval_pair.get("scene_key"),
        "query": eval_pair.get("query"),
        "episode_key": eval_pair.get("episode_key"),
        "source_name": eval_pair.get("source_name"),
        "request_id": eval_pair.get("request_id"),
        "candidate_a_id": eval_pair.get("candidate_a_id"),
        "candidate_b_id": eval_pair.get("candidate_b_id"),
        "detector_pair_evidence_state": detector_pair.get("pair_evidence_state"),
        "detector_contamination_or_contradiction_evidence_available": detector_pair.get(
            "contamination_or_contradiction_evidence_available"
        ),
        "detector_role_evidence_state_counts": detector_pair.get("role_evidence_state_counts"),
        "candidate_pair_label_pattern_for_evaluation_only": eval_pair.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "candidate_a_correctness_label_for_evaluation_only": eval_pair.get(
            "candidate_a_correctness_label_for_evaluation_only"
        ),
        "candidate_a_wrong_label_for_evaluation_only": eval_pair.get("candidate_a_wrong_label_for_evaluation_only"),
        "candidate_b_correctness_label_for_evaluation_only": eval_pair.get(
            "candidate_b_correctness_label_for_evaluation_only"
        ),
        "candidate_b_wrong_label_for_evaluation_only": eval_pair.get("candidate_b_wrong_label_for_evaluation_only"),
        "wrong_candidate_ids_for_evaluation_only": [row.get("candidate_id") for row in wrong_candidates],
        "correct_candidate_ids_for_evaluation_only": [row.get("candidate_id") for row in correct_candidates],
        "pair_label_is_action_forbidden": True,
        "evaluation_only_pair_label_join": True,
        "pairwise_map_pose_consistency_abs_delta_for_evaluation_only": eval_pair.get(
            "map_pose_consistency_abs_delta"
        ),
        "pairwise_pose_graph_connectivity_abs_delta_for_evaluation_only": eval_pair.get(
            "pose_graph_connectivity_abs_delta"
        ),
        "detector_evidence_frozen_before_evaluation_join": True,
        "terminal_selector_allowed_from_this_join": False,
        **common_eval_flags(),
    }


def build_baseline_row(source: Mapping[str, Any], detector_pair: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_evaluation_join_baseline",
        "validation_stage": "evaluation_only_join_after_multi_case_evidence_freeze",
        "scene_key": source.get("scene_key"),
        "query": source.get("query"),
        "episode_key": source.get("episode_key"),
        "source_name": source.get("source_name"),
        "request_id": source.get("request_id"),
        "policy_name": policy_name(source),
        "policy_selected_candidate_id": source.get("policy_selected_candidate_id"),
        "selector_action": source.get("selector_action"),
        "selector_id": source.get("selector_id"),
        "wrong_goal_visit_proxy_for_evaluation_only": source.get("wrong_goal_visit_proxy"),
        "wasted_path_proxy_m_for_evaluation_only": source.get("wasted_path_proxy_m"),
        "success_commit_proxy_for_evaluation_only": source.get("success_commit_proxy"),
        "terminal_commit_proxy_for_evaluation_only": source.get("terminal_commit_proxy"),
        "map_pose_consistency_delta_for_evaluation_only": source.get("map_pose_consistency_delta"),
        "pose_graph_connectivity_delta_for_evaluation_only": source.get("pose_graph_connectivity_delta"),
        "detector_pair_evidence_state": detector_pair.get("pair_evidence_state"),
        "evaluation_only_baseline_context": True,
        "not_used_for_action": True,
        **common_eval_flags(),
    }


def build_request_row(
    request_key: Tuple[str, str, str, str, str],
    pair_row: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    wrong_goal_count = sum(1 for row in baseline_rows if row.get("wrong_goal_visit_proxy_for_evaluation_only") is True)
    wasted_values = [float(row.get("wasted_path_proxy_m_for_evaluation_only") or 0.0) for row in baseline_rows]
    slam_rows = [row for row in baseline_rows if row.get("policy_name") == "SLAMOnlyRich_current"]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_evaluation_join_request",
        "validation_stage": "evaluation_only_join_after_multi_case_evidence_freeze",
        "scene_key": request_key[0],
        "query": request_key[1],
        "request_id": request_key[2],
        "episode_key": request_key[3],
        "source_name": request_key[4],
        "detector_pair_evidence_state": pair_row.get("detector_pair_evidence_state"),
        "candidate_pair_label_pattern_for_evaluation_only": pair_row.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "candidate_label_counts_for_evaluation_only": compact_counter(
            "correct" if row.get("candidate_correctness_label_for_evaluation_only") is True else "wrong"
            for row in candidate_rows
        ),
        "wrong_goal_baseline_count_for_evaluation_only": wrong_goal_count,
        "baseline_wrong_goal_exposure_for_evaluation_only": {
            str(row.get("policy_name")): row.get("wrong_goal_visit_proxy_for_evaluation_only") for row in baseline_rows
        },
        "baseline_wasted_path_exposure_m_for_evaluation_only": {
            str(row.get("policy_name")): row.get("wasted_path_proxy_m_for_evaluation_only") for row in baseline_rows
        },
        "max_wasted_path_exposure_m_for_evaluation_only": max(wasted_values) if wasted_values else 0.0,
        "slam_map_pose_consistency_delta_for_evaluation_only": first(slam_rows).get(
            "map_pose_consistency_delta_for_evaluation_only"
        ),
        "slam_pose_graph_connectivity_delta_for_evaluation_only": first(slam_rows).get(
            "pose_graph_connectivity_delta_for_evaluation_only"
        ),
        "terminal_selector_allowed_from_this_join": False,
        "promotion_gate_required": True,
        **common_eval_flags(),
    }


def build_promotion_probe_row(request_row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "rival_contradiction_region_contamination_multi_case_evaluation_join_promotion_probe",
        "validation_stage": "evaluation_only_join_after_multi_case_evidence_freeze",
        "scene_key": request_row.get("scene_key"),
        "query": request_row.get("query"),
        "request_id": request_row.get("request_id"),
        "episode_key": request_row.get("episode_key"),
        "source_name": request_row.get("source_name"),
        "detector_pair_evidence_state": request_row.get("detector_pair_evidence_state"),
        "candidate_pair_label_pattern_for_evaluation_only": request_row.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "wrong_goal_baseline_count_for_evaluation_only": request_row.get(
            "wrong_goal_baseline_count_for_evaluation_only"
        ),
        "max_wasted_path_exposure_m_for_evaluation_only": request_row.get(
            "max_wasted_path_exposure_m_for_evaluation_only"
        ),
        "slam_map_pose_consistency_delta_for_evaluation_only": request_row.get(
            "slam_map_pose_consistency_delta_for_evaluation_only"
        ),
        "promotion_ready": False,
        "promotion_blocker": "bounded_multi_case_promotion_gate_contract_required",
        "terminal_selector_allowed_from_this_join": False,
        **common_eval_flags(),
    }


def build_rows(
    contract: Mapping[str, Any],
    detector_candidate_views: Sequence[Mapping[str, Any]],
    detector_pair_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    eval_candidate_rows: Sequence[Mapping[str, Any]],
    eval_pair_rows: Sequence[Mapping[str, Any]],
    eval_baseline_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    source_keys = {key(row) for row in source_rows}
    detector_pair_by_key = {key(row): row for row in detector_pair_rows}
    candidate_views_by_key = defaultdict(list)
    eval_candidates_by_key = defaultdict(list)
    eval_pairs_by_key = {key(row): row for row in eval_pair_rows if key(row) in source_keys}
    eval_baselines_by_key = defaultdict(list)

    for row in detector_candidate_views:
        candidate_views_by_key[candidate_key(row)].append(row)
    for row in eval_candidate_rows:
        if key(row) in source_keys:
            eval_candidates_by_key[key(row)].append(row)
    for row in eval_baseline_rows:
        if key(row) in source_keys:
            eval_baselines_by_key[key(row)].append(row)

    candidate_rows: List[Dict[str, Any]] = []
    pair_rows: List[Dict[str, Any]] = []
    baseline_rows: List[Dict[str, Any]] = []
    request_rows: List[Dict[str, Any]] = []
    promotion_probe_rows: List[Dict[str, Any]] = []

    for req_key in sorted(source_keys):
        detector_pair = detector_pair_by_key.get(req_key)
        eval_pair = eval_pairs_by_key.get(req_key)
        if detector_pair is None or eval_pair is None:
            raise RuntimeError({"missing_join_key": req_key, "detector_pair": detector_pair is not None, "eval_pair": eval_pair is not None})
        request_candidate_rows: List[Dict[str, Any]] = []
        for eval_candidate in sorted(eval_candidates_by_key.get(req_key, []), key=lambda row: str(row.get("candidate_id"))):
            row = build_candidate_row(
                eval_candidate,
                candidate_views_by_key.get(candidate_key(eval_candidate), []),
            )
            candidate_rows.append(row)
            request_candidate_rows.append(row)
        if len(request_candidate_rows) != 2:
            raise RuntimeError({"request": req_key, "candidate_rows": len(request_candidate_rows)})
        pair = build_pair_row(detector_pair, eval_pair, request_candidate_rows)
        pair_rows.append(pair)

        request_baseline_rows: List[Dict[str, Any]] = []
        for baseline_source in sorted(eval_baselines_by_key.get(req_key, []), key=policy_name):
            row = build_baseline_row(baseline_source, detector_pair)
            baseline_rows.append(row)
            request_baseline_rows.append(row)
        if len(request_baseline_rows) != 3:
            raise RuntimeError({"request": req_key, "baseline_rows": len(request_baseline_rows)})
        request = build_request_row(req_key, pair, request_candidate_rows, request_baseline_rows)
        request_rows.append(request)
        promotion_probe_rows.append(build_promotion_probe_row(request))

    return request_rows, candidate_rows, pair_rows, baseline_rows, promotion_probe_rows


def summarize(
    *,
    contract: Mapping[str, Any],
    detector_summary: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    promotion_probe_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    expected = contract["minimum_join_gate"]
    all_rows = list(request_rows) + list(candidate_rows) + list(pair_rows) + list(baseline_rows) + list(promotion_probe_rows)
    pair_label_counts = compact_counter(row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_rows)
    candidate_label_counts = compact_counter(
        "correct" if row.get("candidate_correctness_label_for_evaluation_only") is True else "wrong"
        for row in candidate_rows
    )
    baseline_policy_counts = compact_counter(row.get("policy_name") for row in baseline_rows)
    baseline_wrong_goal_counts = {
        policy: sum(
            1
            for row in baseline_rows
            if row.get("policy_name") == policy and row.get("wrong_goal_visit_proxy_for_evaluation_only") is True
        )
        for policy in sorted(baseline_policy_counts)
    }
    total_wrong_goal_baseline_rows = sum(baseline_wrong_goal_counts.values())
    wasted_values = [float(row.get("wasted_path_proxy_m_for_evaluation_only") or 0.0) for row in baseline_rows]
    slam_deltas = [
        float(row.get("map_pose_consistency_delta_for_evaluation_only") or 0.0)
        for row in baseline_rows
        if row.get("policy_name") == "SLAMOnlyRich_current"
    ]
    terminal_rows = sum(1 for row in all_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in all_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in all_rows if row.get("candidate_rejection") is True)

    gate = {
        "source_detector_evidence_gate_passed": bool(
            (detector_summary.get("gate") or {}).get("multi_case_detector_evidence_materializer_gate_passed")
        ),
        "request_rows_match": len(request_rows) == int(expected["expected_request_rows"]),
        "candidate_rows_match": len(candidate_rows) == int(expected["expected_candidate_rows"]),
        "pair_rows_match": len(pair_rows) == int(expected["expected_pair_rows"]),
        "baseline_rows_match": len(baseline_rows) == int(expected["expected_baseline_rows"]),
        "promotion_probe_rows_match": len(promotion_probe_rows) == int(expected["expected_promotion_probe_rows"]),
        "pair_label_counts_match": pair_label_counts == expected["expected_pair_label_counts"],
        "candidate_label_counts_match": candidate_label_counts == expected["expected_candidate_label_counts"],
        "baseline_policy_counts_match": baseline_policy_counts == expected["expected_baseline_policy_counts"],
        "minimum_total_wrong_goal_baseline_rows_pass": total_wrong_goal_baseline_rows
        >= int(expected["minimum_total_wrong_goal_baseline_rows"]),
        "minimum_max_wasted_path_exposure_pass": (max(wasted_values) if wasted_values else 0.0)
        >= float(expected["minimum_max_wasted_path_exposure_m"]),
        "minimum_slam_map_pose_delta_rows_pass": len(slam_deltas) >= int(expected["minimum_slam_map_pose_delta_rows"]),
        "minimum_slam_map_pose_delta_maximum_pass": (max(slam_deltas) if slam_deltas else 0.0)
        >= float(expected["minimum_slam_map_pose_delta_maximum"]),
        "terminal_commit_rows_pass": terminal_rows <= int(expected["terminal_commit_rows_maximum"]),
        "candidate_commit_rows_pass": candidate_commit_rows <= int(expected["candidate_commit_rows_maximum"]),
        "candidate_rejection_rows_pass": candidate_rejection_rows <= int(expected["candidate_rejection_rows_maximum"]),
        "uses_gt_for_action_pass": not any(row.get("uses_gt_for_action") is True for row in all_rows),
        "paper_claim_blocked": not any(row.get("paper_claim_allowed") is True for row in all_rows),
    }
    gate["multi_case_evaluation_join_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "request_rows": len(request_rows),
        "candidate_rows": len(candidate_rows),
        "pair_rows": len(pair_rows),
        "baseline_rows": len(baseline_rows),
        "promotion_probe_rows": len(promotion_probe_rows),
        "pair_label_counts": pair_label_counts,
        "candidate_label_counts": candidate_label_counts,
        "baseline_policy_counts": baseline_policy_counts,
        "baseline_wrong_goal_counts": baseline_wrong_goal_counts,
        "total_wrong_goal_baseline_rows": total_wrong_goal_baseline_rows,
        "max_wasted_path_exposure_m": max(wasted_values) if wasted_values else 0.0,
        "slam_map_pose_delta_rows": len(slam_deltas),
        "slam_map_pose_delta_maximum": max(slam_deltas) if slam_deltas else 0.0,
        "detector_pair_evidence_state_counts": compact_counter(row.get("detector_pair_evidence_state") for row in pair_rows),
        "promotion_ready_rows": sum(1 for row in promotion_probe_rows if row.get("promotion_ready") is True),
        "terminal_commit_rows": terminal_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "gate": gate,
        "next_task": "freeze_multi_case_promotion_gate_contract",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(resolve_path(args.contract))
    detector_summary = load_json(path_from_contract(contract, "detector_evidence_summary"))
    if not (detector_summary.get("gate") or {}).get("multi_case_detector_evidence_materializer_gate_passed"):
        raise RuntimeError("source detector evidence materializer gate did not pass")

    detector_candidate_views = load_jsonl(path_from_contract(contract, "detector_candidate_view_rows"))
    detector_pair_rows = load_jsonl(path_from_contract(contract, "detector_pair_rows"))
    source_rows = load_jsonl(path_from_contract(contract, "source_rows"))
    eval_candidate_rows = load_jsonl(path_from_contract(contract, "evaluation_candidate_rows"))
    eval_pair_rows = load_jsonl(path_from_contract(contract, "evaluation_pair_rows"))
    eval_baseline_rows = load_jsonl(path_from_contract(contract, "evaluation_baseline_rows"))

    request_rows, candidate_rows, pair_rows, baseline_rows, promotion_probe_rows = build_rows(
        contract,
        detector_candidate_views,
        detector_pair_rows,
        source_rows,
        eval_candidate_rows,
        eval_pair_rows,
        eval_baseline_rows,
    )
    summary = summarize(
        contract=contract,
        detector_summary=detector_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        baseline_rows=baseline_rows,
        promotion_probe_rows=promotion_probe_rows,
    )

    out_root = resolve_path(args.out_root)
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["promotion_probe_rows"], promotion_probe_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    print(json.dumps(summary, indent=2, sort_keys=True))

    if not summary["gate"]["multi_case_evaluation_join_gate_passed"]:
        raise RuntimeError("multi-case evaluation join gate failed")


if __name__ == "__main__":
    main()
