import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


SCHEMA_VERSION = "h001.goal_region_object_relation_coverage_completion_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_goal_region_object_relation_coverage_completion_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_goal_region_object_relation_coverage_completion_evaluation_join_v1"

OUTPUT_FILES = {
    "pair_rows": "goal_region_object_relation_coverage_completion_evaluation_join_pair_rows.jsonl",
    "candidate_rows": "goal_region_object_relation_coverage_completion_evaluation_join_candidate_rows.jsonl",
    "baseline_rows": "goal_region_object_relation_coverage_completion_evaluation_join_baseline_rows.jsonl",
    "request_rows": "goal_region_object_relation_coverage_completion_evaluation_join_request_rows.jsonl",
    "promotion_probe_rows": "goal_region_object_relation_coverage_completion_evaluation_join_promotion_probe_rows.jsonl",
    "summary": "goal_region_object_relation_coverage_completion_evaluation_join_summary.json",
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


def join_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        str(row.get("request_id") or row.get("expanded_retrieval_request_id") or ""),
        str(row.get("episode_key") or ""),
    )


def common_eval_flags() -> dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_selector_allowed_from_this_join": False,
        "paper_claim_allowed": False,
    }


def build_pair_row(evidence_pair: Mapping[str, Any], source_pair: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_evaluation_join_pair",
        "validation_stage": "evaluation_only_join_after_coverage_completion_evidence_freeze",
        "scene_key": evidence_pair.get("scene_key"),
        "query": evidence_pair.get("query"),
        "episode_key": evidence_pair.get("episode_key"),
        "source_name": evidence_pair.get("source_name"),
        "request_id": evidence_pair.get("request_id"),
        "coverage_completion_pair_id": evidence_pair.get("coverage_completion_pair_id"),
        "candidate_a_id": evidence_pair.get("candidate_a_id"),
        "candidate_b_id": evidence_pair.get("candidate_b_id"),
        "coverage_completion_pair_evidence_state": evidence_pair.get("pair_evidence_state"),
        "coverage_completion_role_evidence_states": evidence_pair.get("role_evidence_states"),
        "candidate_pair_label_pattern_for_evaluation_only": source_pair.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "candidate_a_correctness_label_for_evaluation_only": source_pair.get(
            "candidate_a_correctness_label_for_evaluation_only"
        ),
        "candidate_b_correctness_label_for_evaluation_only": source_pair.get(
            "candidate_b_correctness_label_for_evaluation_only"
        ),
        "candidate_a_wrong_label_for_evaluation_only": source_pair.get("candidate_a_wrong_label_for_evaluation_only"),
        "candidate_b_wrong_label_for_evaluation_only": source_pair.get("candidate_b_wrong_label_for_evaluation_only"),
        "correct_candidate_ids_for_evaluation_only": source_pair.get("correct_candidate_ids_for_evaluation_only"),
        "wrong_candidate_ids_for_evaluation_only": source_pair.get("wrong_candidate_ids_for_evaluation_only"),
        "pairwise_map_pose_consistency_abs_delta_for_evaluation_only": source_pair.get(
            "pairwise_map_pose_consistency_abs_delta_for_evaluation_only"
        ),
        "pairwise_pose_graph_connectivity_abs_delta_for_evaluation_only": source_pair.get(
            "pairwise_pose_graph_connectivity_abs_delta_for_evaluation_only"
        ),
        "evaluation_only_pair_label_join": True,
        "pair_label_is_action_forbidden": True,
        **common_eval_flags(),
    }


def build_candidate_row(
    source_candidate: Mapping[str, Any],
    evidence_views: Sequence[Mapping[str, Any]],
    evidence_pair_by_key: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    key = join_key(source_candidate)
    evidence_pair = evidence_pair_by_key[key]
    states_by_role = {str(row.get("role")): row.get("candidate_view_evidence_state") for row in evidence_views}
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_evaluation_join_candidate",
        "validation_stage": "evaluation_only_join_after_coverage_completion_evidence_freeze",
        "scene_key": source_candidate.get("scene_key"),
        "query": source_candidate.get("query"),
        "episode_key": source_candidate.get("episode_key"),
        "source_name": source_candidate.get("source_name"),
        "request_id": source_candidate.get("request_id"),
        "coverage_completion_pair_id": evidence_pair.get("coverage_completion_pair_id"),
        "candidate_id": source_candidate.get("candidate_id"),
        "candidate_pair_role": next((row.get("candidate_pair_role") for row in evidence_views), None),
        "coverage_completion_pair_evidence_state": evidence_pair.get("pair_evidence_state"),
        "coverage_completion_candidate_view_rows": len(evidence_views),
        "coverage_completion_candidate_view_states_by_role": states_by_role,
        "coverage_completion_associated_rows": sum(int(row.get("associated_rows") or 0) for row in evidence_views),
        "coverage_completion_depth_consistent_rows": sum(int(row.get("depth_consistent_rows") or 0) for row in evidence_views),
        "candidate_correctness_label_for_evaluation_only": source_candidate.get(
            "candidate_correctness_label_for_evaluation_only"
        ),
        "candidate_wrong_label_for_evaluation_only": source_candidate.get("candidate_wrong_label_for_evaluation_only"),
        "goal_validity_risk_state_for_evaluation_only": source_candidate.get("goal_validity_risk_state"),
        "goal_validity_risk_proxy_for_evaluation_only": source_candidate.get("goal_validity_risk_proxy"),
        "map_pose_consistency_delta_for_evaluation_only": source_candidate.get(
            "map_pose_consistency_delta_for_evaluation_only"
        ),
        "pose_graph_connectivity_delta_for_evaluation_only": source_candidate.get(
            "pose_graph_connectivity_delta_for_evaluation_only"
        ),
        "viewpoint_coverage_delta_for_evaluation_only": source_candidate.get("viewpoint_coverage_delta_for_evaluation_only"),
        "evaluation_only_candidate_label_join": True,
        **common_eval_flags(),
    }


def build_baseline_row(source_baseline: Mapping[str, Any], evidence_pair_by_key: Mapping[tuple[str, str, str, str], Mapping[str, Any]]) -> dict[str, Any]:
    evidence_pair = evidence_pair_by_key[join_key(source_baseline)]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_evaluation_join_baseline",
        "validation_stage": "evaluation_only_join_after_coverage_completion_evidence_freeze",
        "scene_key": source_baseline.get("scene_key"),
        "query": source_baseline.get("query"),
        "episode_key": source_baseline.get("episode_key"),
        "source_name": source_baseline.get("source_name"),
        "request_id": source_baseline.get("request_id"),
        "coverage_completion_pair_id": evidence_pair.get("coverage_completion_pair_id"),
        "coverage_completion_pair_evidence_state": evidence_pair.get("pair_evidence_state"),
        "policy_name": source_baseline.get("policy_name"),
        "selector_id": source_baseline.get("selector_id"),
        "selector_action": source_baseline.get("selector_action"),
        "policy_selected_candidate_id": source_baseline.get("policy_selected_candidate_id"),
        "terminal_commit_proxy_for_evaluation_only": source_baseline.get("terminal_commit_proxy_for_evaluation_only"),
        "success_commit_proxy_for_evaluation_only": source_baseline.get("success_commit_proxy_for_evaluation_only"),
        "wrong_goal_visit_proxy_for_evaluation_only": source_baseline.get("wrong_goal_visit_proxy_for_evaluation_only"),
        "wasted_path_proxy_m_for_evaluation_only": source_baseline.get("wasted_path_proxy_m_for_evaluation_only"),
        "map_pose_consistency_delta_for_evaluation_only": source_baseline.get("map_pose_consistency_delta_for_evaluation_only"),
        "pose_graph_connectivity_delta_for_evaluation_only": source_baseline.get(
            "pose_graph_connectivity_delta_for_evaluation_only"
        ),
        "evaluation_only_baseline_context": True,
        "not_used_for_action": True,
        **common_eval_flags(),
    }


def build_request_row(
    evidence_request: Mapping[str, Any],
    source_request: Mapping[str, Any],
    pair_row: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_evaluation_join_request",
        "validation_stage": "evaluation_only_join_after_coverage_completion_evidence_freeze",
        "scene_key": evidence_request.get("scene_key"),
        "query": evidence_request.get("query"),
        "episode_key": evidence_request.get("episode_key"),
        "source_name": evidence_request.get("source_name"),
        "request_id": evidence_request.get("request_id"),
        "coverage_completion_pair_id": evidence_request.get("coverage_completion_pair_id"),
        "candidate_a_id": evidence_request.get("candidate_a_id"),
        "candidate_b_id": evidence_request.get("candidate_b_id"),
        "coverage_completion_pair_evidence_state": evidence_request.get("pair_evidence_state"),
        "coverage_completion_request_evidence_state": evidence_request.get("request_evidence_state"),
        "candidate_pair_label_pattern_for_evaluation_only": source_request.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "candidate_label_counts_for_evaluation_only": source_request.get("candidate_label_counts_for_evaluation_only"),
        "baseline_wrong_goal_exposure_for_evaluation_only": source_request.get(
            "baseline_wrong_goal_exposure_for_evaluation_only"
        ),
        "baseline_wasted_path_exposure_m_for_evaluation_only": source_request.get(
            "baseline_wasted_path_exposure_m_for_evaluation_only"
        ),
        "wrong_goal_baseline_count_for_evaluation_only": source_request.get("wrong_goal_baseline_count_for_evaluation_only"),
        "max_wasted_path_exposure_m_for_evaluation_only": source_request.get("max_wasted_path_exposure_m_for_evaluation_only"),
        "slam_map_pose_consistency_delta_for_evaluation_only": source_request.get(
            "slam_map_pose_consistency_delta_for_evaluation_only"
        ),
        "slam_pose_graph_connectivity_delta_for_evaluation_only": source_request.get(
            "slam_pose_graph_connectivity_delta_for_evaluation_only"
        ),
        "pair_label_is_action_forbidden": True,
        "baseline_context_is_action_forbidden": True,
        "promotion_gate_required": True,
        "terminal_selector_allowed_from_this_join": False,
        "pair_row_ref": pair_row.get("coverage_completion_pair_id"),
        **common_eval_flags(),
    }


def build_promotion_probe_row(
    source_probe: Mapping[str, Any],
    evidence_pair_by_key: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
    request_by_key: Mapping[tuple[str, str, str, str], Mapping[str, Any]],
) -> dict[str, Any]:
    key = join_key(source_probe)
    evidence_pair = evidence_pair_by_key[key]
    evidence_request = request_by_key[key]
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "goal_region_object_relation_coverage_completion_evaluation_join_promotion_probe",
        "validation_stage": "evaluation_only_join_after_coverage_completion_evidence_freeze",
        "scene_key": source_probe.get("scene_key"),
        "query": source_probe.get("query"),
        "episode_key": source_probe.get("episode_key"),
        "source_name": source_probe.get("source_name"),
        "request_id": source_probe.get("request_id"),
        "coverage_completion_pair_id": evidence_pair.get("coverage_completion_pair_id"),
        "coverage_completion_pair_evidence_state": evidence_pair.get("pair_evidence_state"),
        "coverage_completion_request_evidence_state": evidence_request.get("request_evidence_state"),
        "candidate_pair_label_pattern_for_evaluation_only": source_probe.get(
            "candidate_pair_label_pattern_for_evaluation_only"
        ),
        "wrong_goal_baseline_count_for_evaluation_only": source_probe.get("wrong_goal_baseline_count_for_evaluation_only"),
        "max_wasted_path_exposure_m_for_evaluation_only": source_probe.get("max_wasted_path_exposure_m_for_evaluation_only"),
        "slam_map_pose_consistency_delta_for_evaluation_only": source_probe.get(
            "slam_map_pose_consistency_delta_for_evaluation_only"
        ),
        "promotion_ready": False,
        "promotion_blocker": "coverage_completion_promotion_gate_contract_required",
        **common_eval_flags(),
    }


def select_rows(rows: Sequence[Mapping[str, Any]], keys: set[tuple[str, str, str, str]]) -> list[dict[str, Any]]:
    return [dict(row) for row in rows if join_key(row) in keys]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(resolve_path(args.contract))
    out_root = resolve_path(args.out_root)

    evidence_summary = load_json(path_from_contract(contract, "detector_evidence_summary"))
    evidence_candidate_views = load_jsonl(path_from_contract(contract, "detector_evidence_candidate_view_rows"))
    evidence_pairs = load_jsonl(path_from_contract(contract, "detector_evidence_pair_rows"))
    evidence_requests = load_jsonl(path_from_contract(contract, "detector_evidence_request_rows"))
    target_pairs = load_jsonl(path_from_contract(contract, "target_pair_rows"))
    source_pairs = load_jsonl(path_from_contract(contract, "source_evaluation_join_pair_rows"))
    source_candidates = load_jsonl(path_from_contract(contract, "source_evaluation_join_candidate_rows"))
    source_baselines = load_jsonl(path_from_contract(contract, "source_evaluation_join_baseline_rows"))
    source_requests = load_jsonl(path_from_contract(contract, "source_evaluation_join_request_rows"))
    source_probes = load_jsonl(path_from_contract(contract, "source_evaluation_join_promotion_probe_rows"))

    keys = {join_key(row) for row in target_pairs}
    source_pairs_sel = select_rows(source_pairs, keys)
    source_candidates_sel = select_rows(source_candidates, keys)
    source_baselines_sel = select_rows(source_baselines, keys)
    source_requests_sel = select_rows(source_requests, keys)
    source_probes_sel = select_rows(source_probes, keys)

    evidence_pair_by_key = {join_key(row): row for row in evidence_pairs}
    evidence_request_by_key = {join_key(row): row for row in evidence_requests}
    source_pair_by_key = {join_key(row): row for row in source_pairs_sel}
    source_request_by_key = {join_key(row): row for row in source_requests_sel}
    source_probe_by_key = {join_key(row): row for row in source_probes_sel}

    missing_pair_labels = [key for key in keys if key not in source_pair_by_key]
    missing_request_labels = [key for key in keys if key not in source_request_by_key]
    missing_probe_labels = [key for key in keys if key not in source_probe_by_key]
    if missing_pair_labels or missing_request_labels or missing_probe_labels:
        raise RuntimeError(
            "missing evaluation rows: "
            f"pair={len(missing_pair_labels)} request={len(missing_request_labels)} probe={len(missing_probe_labels)}"
        )

    candidate_views_by_key_candidate: dict[tuple[tuple[str, str, str, str], str], list[dict[str, Any]]] = defaultdict(list)
    for row in evidence_candidate_views:
        candidate_views_by_key_candidate[(join_key(row), str(row.get("candidate_id")))].append(row)

    pair_rows = [build_pair_row(evidence_pair_by_key[key], source_pair_by_key[key]) for key in sorted(keys)]
    candidate_rows = [
        build_candidate_row(
            row,
            candidate_views_by_key_candidate[(join_key(row), str(row.get("candidate_id")))],
            evidence_pair_by_key,
        )
        for row in source_candidates_sel
    ]
    baseline_rows = [build_baseline_row(row, evidence_pair_by_key) for row in source_baselines_sel]
    pair_by_key = {join_key(row): row for row in pair_rows}
    request_rows = [
        build_request_row(evidence_request_by_key[join_key(row)], row, pair_by_key[join_key(row)])
        for row in source_requests_sel
    ]
    request_by_key = {join_key(row): row for row in request_rows}
    promotion_probe_rows = [build_promotion_probe_row(row, evidence_pair_by_key, request_by_key) for row in source_probes_sel]

    min_gate = contract["minimum_join_gate"]
    pair_label_missing = sum(1 for row in pair_rows if row.get("candidate_pair_label_pattern_for_evaluation_only") is None)
    candidate_label_missing = sum(
        1
        for row in candidate_rows
        if row.get("candidate_correctness_label_for_evaluation_only") is None
        and row.get("candidate_wrong_label_for_evaluation_only") is None
    )
    baseline_policy_missing = sum(1 for row in baseline_rows if not row.get("policy_name"))
    all_rows: list[Mapping[str, Any]] = []
    for rows in [pair_rows, candidate_rows, baseline_rows, request_rows, promotion_probe_rows]:
        all_rows.extend(rows)

    gate = {
        "source_evidence_gate_passed": bool(
            evidence_summary.get("gate", {}).get(
                "goal_region_object_relation_coverage_completion_detector_evidence_gate_passed"
            )
        ),
        "pair_rows_match": len(pair_rows) == int(min_gate["pair_rows"]),
        "candidate_rows_match": len(candidate_rows) == int(min_gate["candidate_rows"]),
        "baseline_rows_match": len(baseline_rows) == int(min_gate["baseline_rows"]),
        "request_rows_match": len(request_rows) == int(min_gate["request_rows"]),
        "promotion_probe_rows_match": len(promotion_probe_rows) == int(min_gate["promotion_probe_rows"]),
        "pair_label_missing_rows_pass": pair_label_missing == int(min_gate["pair_label_missing_rows"]),
        "candidate_label_missing_rows_pass": candidate_label_missing == int(min_gate["candidate_label_missing_rows"]),
        "baseline_policy_missing_rows_pass": baseline_policy_missing == int(min_gate["baseline_policy_missing_rows"]),
        "no_terminal_commit_pass": not any(row.get("terminal_commit") for row in all_rows),
        "no_candidate_commit_pass": not any(row.get("candidate_commit") for row in all_rows),
        "no_candidate_rejection_pass": not any(row.get("candidate_rejection") for row in all_rows),
        "no_gt_action_pass": not any(row.get("uses_gt_for_action") for row in all_rows),
        "uses_gt_for_analysis_pass": all(row.get("uses_gt_for_analysis") is True for row in all_rows),
        "terminal_selector_blocked_pass": not any(row.get("terminal_selector_allowed_from_this_join") for row in all_rows),
        "paper_claim_blocked_pass": not any(row.get("paper_claim_allowed") for row in all_rows),
    }
    gate["goal_region_object_relation_coverage_completion_evaluation_join_gate_passed"] = all(gate.values())

    baseline_wrong_by_policy = Counter(
        row.get("policy_name") for row in baseline_rows if row.get("wrong_goal_visit_proxy_for_evaluation_only") is True
    )
    baseline_success_by_policy = Counter(
        row.get("policy_name") for row in baseline_rows if row.get("success_commit_proxy_for_evaluation_only") is True
    )
    evidence_label_cross = Counter(
        (row.get("coverage_completion_pair_evidence_state"), row.get("candidate_pair_label_pattern_for_evaluation_only"))
        for row in pair_rows
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed" if gate["goal_region_object_relation_coverage_completion_evaluation_join_gate_passed"] else "failed",
        "contract": args.contract,
        "pair_rows": len(pair_rows),
        "candidate_rows": len(candidate_rows),
        "baseline_rows": len(baseline_rows),
        "request_rows": len(request_rows),
        "promotion_probe_rows": len(promotion_probe_rows),
        "pair_label_counts_for_evaluation_only": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_rows
        ),
        "candidate_label_counts_for_evaluation_only": {
            "correct": sum(1 for row in candidate_rows if row.get("candidate_correctness_label_for_evaluation_only") is True),
            "wrong": sum(1 for row in candidate_rows if row.get("candidate_wrong_label_for_evaluation_only") is True),
        },
        "baseline_policy_rows": compact_counter(row.get("policy_name") for row in baseline_rows),
        "baseline_wrong_goal_rows_for_evaluation_only": dict(sorted(baseline_wrong_by_policy.items())),
        "baseline_success_rows_for_evaluation_only": dict(sorted(baseline_success_by_policy.items())),
        "total_wrong_goal_baseline_rows_for_evaluation_only": sum(
            int(row.get("wrong_goal_baseline_count_for_evaluation_only") or 0) for row in request_rows
        ),
        "max_wasted_path_exposure_m_for_evaluation_only": max(
            float(row.get("max_wasted_path_exposure_m_for_evaluation_only") or 0.0) for row in request_rows
        ),
        "slam_map_pose_delta_rows_for_evaluation_only": sum(
            1 for row in request_rows if row.get("slam_map_pose_consistency_delta_for_evaluation_only") is not None
        ),
        "slam_map_pose_delta_max_for_evaluation_only": max(
            float(row.get("slam_map_pose_consistency_delta_for_evaluation_only") or 0.0) for row in request_rows
        ),
        "evidence_label_cross_counts_for_evaluation_only": {
            f"{key[0]}|{key[1]}": value for key, value in sorted(evidence_label_cross.items())
        },
        "pair_label_missing_rows": pair_label_missing,
        "candidate_label_missing_rows": candidate_label_missing,
        "baseline_policy_missing_rows": baseline_policy_missing,
        "terminal_commit_rows": sum(1 for row in all_rows if row.get("terminal_commit")),
        "candidate_commit_rows": sum(1 for row in all_rows if row.get("candidate_commit")),
        "candidate_rejection_rows": sum(1 for row in all_rows if row.get("candidate_rejection")),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_selector_allowed_from_this_join": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "next_task": "freeze_goal_region_object_relation_coverage_completion_promotion_gate_contract",
    }

    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["promotion_probe_rows"], promotion_probe_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)

    print(json.dumps(summary, indent=2, sort_keys=True))
    if not gate["goal_region_object_relation_coverage_completion_evaluation_join_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
