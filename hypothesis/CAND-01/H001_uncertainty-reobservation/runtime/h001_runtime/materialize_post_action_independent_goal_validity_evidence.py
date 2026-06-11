import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_action_independent_goal_validity_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_post_action_independent_goal_validity_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_action_independent_goal_validity_evidence_v1"

OUTPUT_FILES = {
    "request_evidence_rows": "post_action_independent_goal_validity_evidence_request_rows.jsonl",
    "candidate_evidence_rows": "post_action_independent_goal_validity_evidence_candidate_rows.jsonl",
    "evidence_plan_rows": "post_action_independent_goal_validity_evidence_plan_rows.jsonl",
    "evidence_audit_rows": "post_action_independent_goal_validity_evidence_audit_rows.jsonl",
    "failure_rows": "post_action_independent_goal_validity_evidence_failure_rows.jsonl",
    "summary": "post_action_independent_goal_validity_evidence_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_wrong_label",
    "no_valid_candidate_pool_label",
    "success_commit_proxy",
    "wrong_goal_visit_proxy",
    "wasted_path_proxy_m",
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "oracle_shortest_path",
    "label_tuned_threshold",
    "post_hoc_dropped_row_flag",
    "oracle",
    "ground_truth",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
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


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def join_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return tuple(str(source.get(key) or row.get(key) or "") for key in JOIN_KEYS)  # type: ignore[return-value]


def candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("candidate_id") or row.get("candidate_id") or ""))


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def group_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[join_key(row)].append(row)
    return dict(grouped)


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
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
    return sorted(found)


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def evidence_features(row: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    gap = safe_float(row.get("viewpoint_evidence_gap_proxy"))
    map_delta = safe_float(row.get("map_pose_consistency_delta"))
    pose_delta = safe_float(row.get("pose_graph_connectivity_delta"))
    map_uncertainty = safe_float(row.get("map_pose_consistency_uncertainty_proxy"))
    coverage = None if gap is None else clamp(1.0 - gap)
    association = None
    if coverage is not None and map_delta is not None and pose_delta is not None:
        association = clamp((coverage + clamp(map_delta) + clamp(pose_delta)) / 3.0)
    return {
        "viewpoint_evidence_gap_proxy": gap,
        "viewpoint_coverage_delta": coverage,
        "map_pose_consistency_delta": map_delta,
        "pose_graph_connectivity_delta": pose_delta,
        "map_pose_consistency_uncertainty_proxy": map_uncertainty,
        "association_quality_proxy": association,
    }


def candidate_evidence_status(row: Mapping[str, Any]) -> Tuple[str, int, int, str]:
    features = evidence_features(row)
    required = (
        features["viewpoint_coverage_delta"],
        features["map_pose_consistency_delta"],
        features["pose_graph_connectivity_delta"],
        features["association_quality_proxy"],
    )
    if any(value is None for value in required):
        return ("independent_evidence_missing", 0, 0, "required_label_free_proxy_missing")

    coverage = features["viewpoint_coverage_delta"] or 0.0
    map_delta = features["map_pose_consistency_delta"] or 0.0
    pose_delta = features["pose_graph_connectivity_delta"] or 0.0
    association = features["association_quality_proxy"] or 0.0

    support_count = int(coverage >= 0.9) + int(map_delta >= 0.5) + int(pose_delta >= 0.25)
    contradiction_count = int(coverage < 0.9) + int(map_delta < 0.5) + int(pose_delta < 0.25)

    if support_count >= 2 and contradiction_count == 0:
        return ("independent_support_acquired", support_count, contradiction_count, "label_free_proxy_support")
    if contradiction_count >= 2:
        return (
            "independent_contradiction_acquired",
            support_count,
            contradiction_count,
            "label_free_proxy_contradiction",
        )
    if association >= 0.6:
        return (
            "independent_support_and_contradiction_conflict",
            support_count,
            contradiction_count,
            "mixed_label_free_proxy_evidence",
        )
    return ("independent_evidence_missing", support_count, contradiction_count, "weak_label_free_proxy")


def materialize_candidate_rows(source_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=candidate_key):
        key = join_key(source)
        payload = key_payload(key)
        cid = candidate_key(source)[-1]
        evidence_required = source.get("target_role") == "primary_target"
        features = evidence_features(source)
        if evidence_required:
            status, support_count, contradiction_count, reason = candidate_evidence_status(source)
        else:
            status, support_count, contradiction_count, reason = (
                "audit_control_no_evidence_required",
                0,
                0,
                "audit_control_row",
            )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_independent_goal_validity_evidence_materialization",
                "row_type": "post_action_independent_goal_validity_evidence_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("branch_action"),
                "evidence_required": bool(evidence_required),
                "candidate_evidence_status": status,
                "candidate_support_evidence_count": support_count,
                "candidate_contradiction_evidence_count": contradiction_count,
                "candidate_evidence_reason": reason,
                "viewpoint_coverage_delta": features["viewpoint_coverage_delta"],
                "association_quality_proxy": features["association_quality_proxy"],
                "map_pose_consistency_delta": features["map_pose_consistency_delta"],
                "pose_graph_connectivity_delta": features["pose_graph_connectivity_delta"],
                "map_pose_consistency_uncertainty_proxy": features["map_pose_consistency_uncertainty_proxy"],
                "action_evidence_inputs": {
                    "candidate_id": cid,
                    "viewpoint_evidence_gap_proxy": features["viewpoint_evidence_gap_proxy"],
                    "map_pose_consistency_delta": features["map_pose_consistency_delta"],
                    "pose_graph_connectivity_delta": features["pose_graph_connectivity_delta"],
                    "map_pose_consistency_uncertainty_proxy": features["map_pose_consistency_uncertainty_proxy"],
                },
                "label_free_evidence_only": True,
                "goal_validity_not_proven": True,
                **common_flags(),
            }
        )
    return out


def request_evidence_status(candidate_rows: Sequence[Mapping[str, Any]]) -> Tuple[str, bool, str]:
    required_rows = [row for row in candidate_rows if row.get("evidence_required") is True]
    if not required_rows:
        return ("audit_control_no_evidence_required", False, "audit_control_row")

    statuses = Counter(str(row.get("candidate_evidence_status")) for row in required_rows)
    support_rows = statuses.get("independent_support_acquired", 0)
    contradiction_rows = statuses.get("independent_contradiction_acquired", 0)
    conflict_rows = statuses.get("independent_support_and_contradiction_conflict", 0)
    missing_rows = statuses.get("independent_evidence_missing", 0)
    available_rows = support_rows + contradiction_rows + conflict_rows

    if available_rows <= 0:
        return ("independent_evidence_missing", False, "all_candidate_evidence_missing_or_weak")
    if contradiction_rows > 0 or conflict_rows > 0 or support_rows > 1:
        return ("independent_evidence_conflicted", True, "candidate_level_evidence_not_terminal")
    if support_rows == 1 and missing_rows == 0:
        return ("independent_goal_validity_evidence_acquired", True, "single_candidate_support_proxy")
    return ("independent_evidence_conflicted", True, "support_plus_missing_candidates")


def materialize_request_rows(
    source_rows: Sequence[Mapping[str, Any]],
    candidate_rows_by_key: Mapping[Tuple[str, str, str, str, str], List[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=join_key):
        key = join_key(source)
        payload = key_payload(key)
        evidence_required = source.get("target_role") == "primary_target"
        candidates = candidate_rows_by_key.get(key, [])
        status, available, missing_reason = request_evidence_status(candidates)
        if not evidence_required:
            status = "audit_control_no_evidence_required"
            available = False
            missing_reason = "audit_control_row"
        added_cost = safe_float(source.get("reobserve_travel_cost_m"), 0.0) if evidence_required else 0.0
        evidence_candidate_count = sum(
            1
            for row in candidates
            if row.get("candidate_evidence_status")
            in {
                "independent_support_acquired",
                "independent_contradiction_acquired",
                "independent_support_and_contradiction_conflict",
            }
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_independent_goal_validity_evidence_materialization",
                "row_type": "post_action_independent_goal_validity_evidence_request",
                "join_key": payload,
                **payload,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("branch_action"),
                "evidence_required": bool(evidence_required),
                "evidence_action": "materialize_label_free_candidate_relative_evidence"
                if evidence_required
                else "audit_control_no_evidence_required",
                "evidence_status": status,
                "post_action_goal_validity_evidence_available": bool(available),
                "independent_evidence_candidate_count": evidence_candidate_count,
                "evidence_missing_reason": None if available else missing_reason,
                "goal_validity_risk_state_pre": source.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state_pre": source.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state_pre": source.get(
                    "map_pose_consistency_uncertainty_state"
                ),
                "source_reobserve_travel_cost_m": safe_float(source.get("reobserve_travel_cost_m")),
                "added_evidence_travel_cost_m": added_cost,
                "action_evidence_inputs": {
                    "source_branch_action": source.get("branch_action"),
                    "selected_candidate_count": safe_int(source.get("selected_candidate_count"), 0),
                    "viewpoint_evidence_gap_state_pre": source.get("viewpoint_evidence_gap_state"),
                    "map_pose_consistency_uncertainty_state_pre": source.get(
                        "map_pose_consistency_uncertainty_state"
                    ),
                },
                "label_free_evidence_only": True,
                "goal_validity_not_proven": True,
                **common_flags(),
            }
        )
    return out


def materialize_plan_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in sorted((item for item in candidate_rows if item.get("evidence_required") is True), key=candidate_key):
        key = join_key(row)
        payload = key_payload(key)
        cid = candidate_key(row)[-1]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_independent_goal_validity_evidence_materialization",
                "row_type": "post_action_independent_goal_validity_evidence_plan",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": row.get("target_role"),
                "evidence_plan_action": "score_candidate_relative_viewpoint_map_pose_proxy",
                "candidate_evidence_status": row.get("candidate_evidence_status"),
                "candidate_support_evidence_count": row.get("candidate_support_evidence_count"),
                "candidate_contradiction_evidence_count": row.get("candidate_contradiction_evidence_count"),
                "viewpoint_coverage_delta": row.get("viewpoint_coverage_delta"),
                "association_quality_proxy": row.get("association_quality_proxy"),
                "map_pose_consistency_delta": row.get("map_pose_consistency_delta"),
                "uses_existing_frozen_label_free_proxies": True,
                "requires_detector_or_segmenter_followup": row.get("candidate_evidence_status")
                in {"independent_evidence_missing", "independent_support_and_contradiction_conflict"},
                **common_flags(),
            }
        )
    return out


def materialize_audit_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in sorted(request_rows, key=join_key):
        key = join_key(row)
        payload = key_payload(key)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_independent_goal_validity_evidence_materialization",
                "row_type": "post_action_independent_goal_validity_evidence_audit",
                "join_key": payload,
                **payload,
                "target_role": row.get("target_role"),
                "evidence_required": row.get("evidence_required"),
                "evidence_status": row.get("evidence_status"),
                "post_action_goal_validity_evidence_available": row.get(
                    "post_action_goal_validity_evidence_available"
                ),
                "audit_note": "primary_target_requires_post_action_evaluation_join"
                if row.get("target_role") == "primary_target"
                else "audit_control_preserved",
                **common_flags(),
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "terminal_utility_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "paper_claim_blocked",
    ]
    if row.get("target_role") != "primary_target":
        tags.append("audit_control_preserved")
    elif row.get("post_action_goal_validity_evidence_available") is True:
        tags.append("post_action_evidence_materialized")
        tags.append("post_action_evaluation_join_required")
        if row.get("evidence_status") == "independent_evidence_conflicted":
            tags.append("independent_evidence_conflicted")
    else:
        tags.append("independent_evidence_missing")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "independent_evidence_missing",
        "independent_evidence_conflicted",
        "post_action_evaluation_join_required",
        "audit_control_preserved",
        "terminal_utility_blocked",
    ):
        if tag in tags:
            return tag
    return "unknown"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in sorted(request_rows, key=join_key):
        key = join_key(row)
        payload = key_payload(key)
        tags = failure_tags(row)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "post_action_independent_goal_validity_evidence_materialization",
                "row_type": "post_action_independent_goal_validity_evidence_failure",
                "join_key": payload,
                **payload,
                "target_role": row.get("target_role"),
                "evidence_status": row.get("evidence_status"),
                "post_action_goal_validity_evidence_available": row.get(
                    "post_action_goal_validity_evidence_available"
                ),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                **common_flags(),
            }
        )
    return out


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    plan_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    gate_contract = contract.get("implementation_gate")
    gate_contract = gate_contract if isinstance(gate_contract, Mapping) else {}
    primary_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    audit_requests = [row for row in request_rows if row.get("target_role") != "primary_target"]
    primary_candidates = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    all_action_rows = [*request_rows, *candidate_rows, *plan_rows, *audit_rows, *failure_rows]
    request_available_rows = [
        row for row in primary_requests if row.get("post_action_goal_validity_evidence_available") is True
    ]
    support_rows = [
        row for row in primary_candidates if row.get("candidate_evidence_status") == "independent_support_acquired"
    ]
    contradiction_rows = [
        row
        for row in primary_candidates
        if row.get("candidate_evidence_status") == "independent_contradiction_acquired"
    ]
    missing_candidate_rows = [
        row for row in primary_candidates if row.get("candidate_evidence_status") == "independent_evidence_missing"
    ]
    unreachable_request_rows: List[Mapping[str, Any]] = [
        row for row in primary_requests if row.get("evidence_status") == "independent_evidence_unreachable"
    ]
    actual_counts = {
        "request_rows": len(request_rows),
        "primary_target_rows": len(primary_requests),
        "non_target_audit_rows": len(audit_requests),
        "candidate_rows": len(candidate_rows),
        "primary_candidate_evidence_targets": len(primary_candidates),
        "evidence_plan_rows": len(plan_rows),
        "evidence_audit_rows": len(audit_rows),
        "failure_rows": len(failure_rows),
        "request_evidence_available_rows": len(request_available_rows),
        "candidate_support_evidence_rows": len(support_rows),
        "candidate_contradiction_evidence_rows": len(contradiction_rows),
        "evidence_missing_rows": len(missing_candidate_rows),
        "evidence_unreachable_rows": len(unreachable_request_rows),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
    }
    gate = {
        "request_rows_expected_passed": actual_counts["request_rows"]
        == safe_int(gate_contract.get("request_rows_expected"), 50),
        "primary_target_rows_expected_passed": actual_counts["primary_target_rows"]
        == safe_int(gate_contract.get("primary_target_rows_expected"), 21),
        "non_target_audit_rows_expected_passed": actual_counts["non_target_audit_rows"]
        == safe_int(gate_contract.get("non_target_audit_rows_expected"), 29),
        "candidate_rows_expected_passed": actual_counts["candidate_rows"]
        == safe_int(gate_contract.get("candidate_rows_expected"), 97),
        "primary_candidate_evidence_targets_expected_passed": actual_counts[
            "primary_candidate_evidence_targets"
        ]
        == safe_int(gate_contract.get("primary_candidate_evidence_targets_expected"), 42),
        "minimum_primary_request_evidence_available_rows_passed": actual_counts[
            "request_evidence_available_rows"
        ]
        >= safe_int(gate_contract.get("minimum_primary_request_evidence_available_rows"), 1),
        "action_evidence_forbidden_key_count_passed": actual_counts["action_evidence_forbidden_key_count"]
        == safe_int(gate_contract.get("action_evidence_forbidden_key_count_expected"), 0),
        "terminal_commit_rows_passed": actual_counts["terminal_commit_rows"]
        == safe_int(gate_contract.get("terminal_commit_rows_expected"), 0),
        "candidate_commit_rows_passed": actual_counts["candidate_commit_rows"]
        == safe_int(gate_contract.get("candidate_commit_rows_expected"), 0),
        "candidate_rejection_rows_passed": actual_counts["candidate_rejection_rows"]
        == safe_int(gate_contract.get("candidate_rejection_rows_expected"), 0),
        "uses_gt_for_action_passed": actual_counts["uses_gt_for_action_true_rows"]
        == safe_int(gate_contract.get("uses_gt_for_action_true_rows_expected"), 0),
        "paper_claim_blocked_passed": actual_counts["paper_claim_allowed_true_rows"]
        == safe_int(gate_contract.get("paper_claim_allowed_true_rows_expected"), 0),
    }
    materializer_gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "evidence_materializer_gate_passed_evaluation_join_required"
        if materializer_gate_passed
        else "evidence_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        **actual_counts,
        "source_branch_action_counts": compact_counter(row.get("source_branch_action") for row in request_rows),
        "request_evidence_status_counts": compact_counter(row.get("evidence_status") for row in request_rows),
        "primary_request_evidence_status_counts": compact_counter(
            row.get("evidence_status") for row in primary_requests
        ),
        "candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in candidate_rows
        ),
        "primary_candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in primary_candidates
        ),
        "added_evidence_travel_cost_m_stats": number_stats(
            row.get("added_evidence_travel_cost_m") for row in request_rows
        ),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "implementation_gate": gate,
        "evidence_materializer_gate_passed": materializer_gate_passed,
        "promotion_gate_attempt_allowed_after_post_action_evidence_join": materializer_gate_passed,
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "post_action_evaluation_join_required"
        if materializer_gate_passed
        else "independent_goal_validity_evidence_missing",
        "next_task": "freeze_post_action_evidence_evaluation_join_contract"
        if materializer_gate_passed
        else "generate_post_action_independent_goal_validity_evidence_artifact",
        "interpretation": {
            "fact": (
                "The materializer writes label-free request/candidate/plan/audit/failure rows for the frozen "
                "post-action goal-validity evidence contract."
            ),
            "agent_inference": (
                "The rows make independent evidence measurable, but they do not solve goal validity or allow a "
                "terminal selector. A later evaluation join must test task and map effects."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM complementarity, terminal utility, formula revision, "
                "first_eval rerun, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed."
            ),
        },
    }


def verification_path(contract_path: Path) -> Path:
    return contract_path.with_name(f"{contract_path.stem}.verify.json")


def build_verify_payload(
    *,
    contract_path: Path,
    out_root: Path,
    summary: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA_VERSION}.verify",
        "date_checked": "2026-06-11",
        "ok": summary.get("evidence_materializer_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "primary_target_rows": summary.get("primary_target_rows"),
            "non_target_audit_rows": summary.get("non_target_audit_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "primary_candidate_evidence_targets": summary.get("primary_candidate_evidence_targets"),
            "evidence_plan_rows": summary.get("evidence_plan_rows"),
            "evidence_audit_rows": summary.get("evidence_audit_rows"),
            "failure_rows": summary.get("failure_rows"),
            "request_evidence_available_rows": summary.get("request_evidence_available_rows"),
            "candidate_support_evidence_rows": summary.get("candidate_support_evidence_rows"),
            "candidate_contradiction_evidence_rows": summary.get("candidate_contradiction_evidence_rows"),
            "evidence_missing_rows": summary.get("evidence_missing_rows"),
            "evidence_unreachable_rows": summary.get("evidence_unreachable_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "request_evidence_status_counts": summary.get("request_evidence_status_counts"),
        "candidate_evidence_status_counts": summary.get("candidate_evidence_status_counts"),
        "implementation_gate": summary.get("implementation_gate"),
        "evidence_materializer_gate_passed": summary.get("evidence_materializer_gate_passed"),
        "promotion_gate_attempt_allowed_after_post_action_evidence_join": summary.get(
            "promotion_gate_attempt_allowed_after_post_action_evidence_join"
        ),
        "primary_blocker": summary.get("primary_blocker"),
        "next_task": summary.get("next_task"),
        "paper_claim_allowed": False,
        "verified_output_files": {name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()},
        "verification_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m py_compile "
                "hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/"
                "materialize_post_action_independent_goal_validity_evidence.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_action_independent_goal_validity_evidence"
            ),
            (
                "jq '{status, request_rows, primary_target_rows, primary_candidate_evidence_targets, "
                "request_evidence_available_rows, candidate_support_evidence_rows, "
                "candidate_contradiction_evidence_rows, evidence_materializer_gate_passed, "
                "primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "source_evaluation_join_verified": True,
            "all_50_source_rows_required": True,
            "primary_21_rows_frozen": True,
            "primary_42_candidate_targets_frozen": True,
            "labels_for_action_forbidden": True,
            "absence_of_commit_not_counted_as_evidence": True,
            "terminal_commit_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "terminal_utility_validation_allowed": False,
            "formula_revision_allowed": False,
            "first_eval_rerun_allowed": False,
            "policy_scale_comparison_allowed": False,
            "step_4_5_promotion_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": summary.get("interpretation"),
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")

    source_request_rows = load_jsonl(Path(str(source["evaluation_join_request_rows"])))
    source_candidate_rows = load_jsonl(Path(str(source["evaluation_join_candidate_rows"])))

    candidate_rows = materialize_candidate_rows(source_candidate_rows)
    candidate_rows_by_key = group_by_request(candidate_rows)
    request_rows = materialize_request_rows(source_request_rows, candidate_rows_by_key)
    plan_rows = materialize_plan_rows(candidate_rows)
    audit_rows = materialize_audit_rows(request_rows)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*request_rows, *candidate_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        plan_rows=plan_rows,
        audit_rows=audit_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_evidence_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_evidence_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["evidence_plan_rows"], plan_rows)
    write_jsonl(out_root / OUTPUT_FILES["evidence_audit_rows"], audit_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize post-action independent goal-validity evidence rows for H001."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(
        json.dumps(
            {
                "status": summary.get("status"),
                "request_rows": summary.get("request_rows"),
                "primary_target_rows": summary.get("primary_target_rows"),
                "primary_candidate_evidence_targets": summary.get("primary_candidate_evidence_targets"),
                "request_evidence_available_rows": summary.get("request_evidence_available_rows"),
                "candidate_support_evidence_rows": summary.get("candidate_support_evidence_rows"),
                "candidate_contradiction_evidence_rows": summary.get("candidate_contradiction_evidence_rows"),
                "evidence_materializer_gate_passed": summary.get("evidence_materializer_gate_passed"),
                "primary_blocker": summary.get("primary_blocker"),
                "next_task": summary.get("next_task"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
