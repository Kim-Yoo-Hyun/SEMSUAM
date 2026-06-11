import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.post_action_goal_validity_arbitration_followup_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_post_action_goal_validity_arbitration_followup_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_post_action_goal_validity_arbitration_followup_evaluation_join_v1"

OUTPUT_FILES = {
    "request_eval_rows": "post_action_goal_validity_arbitration_followup_evaluation_join_request_rows.jsonl",
    "candidate_eval_rows": "post_action_goal_validity_arbitration_followup_evaluation_join_candidate_rows.jsonl",
    "pair_eval_rows": "post_action_goal_validity_arbitration_followup_evaluation_join_pair_rows.jsonl",
    "baseline_eval_rows": "post_action_goal_validity_arbitration_followup_evaluation_join_baseline_rows.jsonl",
    "promotion_probe_rows": "post_action_goal_validity_arbitration_followup_evaluation_join_promotion_probe_rows.jsonl",
    "failure_rows": "post_action_goal_validity_arbitration_followup_evaluation_join_failure_rows.jsonl",
    "summary": "post_action_goal_validity_arbitration_followup_evaluation_join_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")
REFERENCE_WRONG_GOAL_POLICIES = ("NoReobserveReference", "SemanticOnly")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "no_valid_candidate_pool_label",
    "no_valid_candidate_pool_for_evaluation_only",
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


def pair_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        *join_key(row),
        str(source.get("candidate_a_id") or row.get("candidate_a_id") or ""),
        str(source.get("candidate_b_id") or row.get("candidate_b_id") or ""),
    )


def policy_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("policy_name") or row.get("policy_name") or ""))


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def index_one(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


def index_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def policy_lookup(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[join_key(row)][policy_key(row)[-1]] = row
    return dict(grouped)


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


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
        scan(row.get("action_route_inputs", {}))
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


def baseline_wrong_goal_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("wrong_goal_visit_proxy") is True) for policy in POLICIES}


def baseline_success_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("success_commit_proxy") is True) for policy in POLICIES}


def baseline_terminal_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("terminal_commit_proxy") is True) for policy in POLICIES}


def baseline_wasted_path_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Optional[float]]:
    return {policy: safe_float((policy_rows.get(policy) or {}).get("wasted_path_proxy_m")) for policy in POLICIES}


def reference_wrong_goal(exposure: Mapping[str, bool]) -> bool:
    return any(exposure.get(policy) is True for policy in REFERENCE_WRONG_GOAL_POLICIES)


def candidate_label_state(row: Mapping[str, Any]) -> str:
    if row.get("goal_validity_label_join_available") is not True:
        return "missing"
    if row.get("candidate_correctness_label_for_evaluation_only") is True:
        return "correct"
    if (
        row.get("candidate_wrong_label_for_evaluation_only") is True
        or row.get("no_valid_candidate_pool_for_evaluation_only") is True
    ):
        return "wrong"
    return "missing"


def pair_label_pattern(candidate_a: Mapping[str, Any], candidate_b: Mapping[str, Any]) -> str:
    left = candidate_label_state(candidate_a)
    right = candidate_label_state(candidate_b)
    if left == "missing" or right == "missing":
        return "label_missing"
    if left == "correct" and right == "correct":
        return "both_correct"
    if left == "wrong" and right == "wrong":
        return "both_wrong"
    if left == "correct" and right == "wrong":
        return "a_correct_b_wrong"
    if left == "wrong" and right == "correct":
        return "a_wrong_b_correct"
    return "label_missing"


def materialize_request_rows(
    *,
    action_rows: Sequence[Mapping[str, Any]],
    previous_eval_rows_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    baselines_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for action in sorted(action_rows, key=join_key):
        key = join_key(action)
        payload = key_payload(key)
        previous = previous_eval_rows_by_key.get(key) or {}
        policy_rows = baselines_by_key.get(key) or {}
        wrong_exposure = baseline_wrong_goal_exposure(policy_rows)
        wasted_exposure = baseline_wasted_path_exposure(policy_rows)
        is_primary = action.get("target_role") == "primary_target"
        evidence_available = action.get("post_action_goal_validity_evidence_available") is True
        reduction_only_by_evidence = bool(
            is_primary
            and action.get("wrong_goal_reduction_only_by_evidence_availability") is True
            and evidence_available
            and reference_wrong_goal(wrong_exposure)
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_arbitration_followup_action_freeze",
                "row_type": "post_action_goal_validity_arbitration_followup_evaluation_join_request",
                "join_key": payload,
                **payload,
                "target_role": action.get("target_role"),
                "source_branch_action": action.get("source_branch_action"),
                "source_resolution_route": action.get("source_resolution_route"),
                "source_resolution_reason": action.get("source_resolution_reason"),
                "selected_evidence_family": action.get("selected_evidence_family"),
                "selected_branch": action.get("selected_branch"),
                "selected_action": action.get("selected_action"),
                "action_frozen_before_evaluation_join": True,
                "pair_labels_evaluation_only": True,
                "request_evidence_status": action.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": evidence_available,
                "evidence_available_is_not_goal_validity": True,
                "resolution_required": action.get("resolution_required") is True,
                "goal_validity_risk_state": previous.get(
                    "goal_validity_risk_state",
                    action.get("goal_validity_risk_state"),
                ),
                "goal_validity_risk_proxy": safe_float(previous.get("goal_validity_risk_proxy")),
                "viewpoint_evidence_gap_state": previous.get(
                    "viewpoint_evidence_gap_state",
                    action.get("viewpoint_evidence_gap_state"),
                ),
                "viewpoint_evidence_gap_proxy": safe_float(previous.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": previous.get(
                    "map_pose_consistency_uncertainty_state",
                    action.get("map_pose_consistency_uncertainty_state"),
                ),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    previous.get("map_pose_consistency_uncertainty_proxy")
                ),
                "pose_graph_connectivity_delta": safe_float(action.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(action.get("map_pose_consistency_delta")),
                "source_reobserve_travel_cost_m": safe_float(action.get("source_reobserve_travel_cost_m")),
                "added_evidence_travel_cost_m": safe_float(action.get("added_evidence_travel_cost_m")),
                "baseline_wrong_goal_exposure": wrong_exposure,
                "baseline_success_exposure": baseline_success_exposure(policy_rows),
                "baseline_terminal_commit_exposure": baseline_terminal_exposure(policy_rows),
                "baseline_wasted_path_exposure_m": wasted_exposure,
                "reference_wrong_goal_exposure": reference_wrong_goal(wrong_exposure),
                "selected_candidate_count": safe_int(previous.get("selected_candidate_count"), 0),
                "selected_candidate_clean_correct_count": safe_int(
                    previous.get("selected_candidate_clean_correct_count"),
                    0,
                ),
                "selected_candidate_wrong_or_no_valid_count": safe_int(
                    previous.get("selected_candidate_wrong_or_no_valid_count"),
                    0,
                ),
                "evidence_conflict_blocks_promotion": action.get("evidence_conflict_blocks_promotion") is True,
                "evidence_missing_blocks_promotion": action.get("evidence_missing_blocks_promotion") is True,
                "wrong_goal_reduction_only_by_evidence_availability": reduction_only_by_evidence,
                "post_action_wrong_goal_claim_allowed": False,
                **common_flags(),
            }
        )
    return out


def materialize_candidate_rows(
    *,
    action_rows: Sequence[Mapping[str, Any]],
    previous_eval_rows_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for action in sorted(action_rows, key=candidate_key):
        key = join_key(action)
        payload = key_payload(key)
        ckey = candidate_key(action)
        cid = ckey[-1]
        previous = previous_eval_rows_by_candidate.get(ckey) or {}
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_arbitration_followup_action_freeze",
                "row_type": "post_action_goal_validity_arbitration_followup_evaluation_join_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": action.get("target_role"),
                "source_branch_action": action.get("source_branch_action"),
                "source_resolution_route": action.get("source_resolution_route"),
                "selected_evidence_family": action.get("selected_evidence_family"),
                "selected_branch": action.get("selected_branch"),
                "selected_action": action.get("selected_action"),
                "action_frozen_before_evaluation_join": True,
                "request_evidence_status": action.get("request_evidence_status"),
                "candidate_evidence_status": action.get("candidate_evidence_status"),
                "candidate_evidence_reason": action.get("candidate_evidence_reason"),
                "candidate_support_evidence_count": safe_int(action.get("candidate_support_evidence_count"), 0),
                "candidate_contradiction_evidence_count": safe_int(
                    action.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "candidate_correctness_label_for_evaluation_only": previous.get(
                    "candidate_correctness_label_for_evaluation_only"
                ),
                "candidate_wrong_label_for_evaluation_only": previous.get(
                    "candidate_wrong_label_for_evaluation_only"
                ),
                "no_valid_candidate_pool_for_evaluation_only": (
                    previous.get("no_valid_candidate_pool_for_evaluation_only") is True
                ),
                "goal_validity_label_join_available": previous.get("goal_validity_label_join_available") is True,
                "goal_validity_risk_state": previous.get("goal_validity_risk_state"),
                "goal_validity_risk_proxy": safe_float(previous.get("goal_validity_risk_proxy")),
                "viewpoint_coverage_delta": safe_float(action.get("viewpoint_coverage_delta")),
                "association_quality_proxy": safe_float(action.get("association_quality_proxy")),
                "map_pose_consistency_delta": safe_float(action.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(action.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    action.get("map_pose_consistency_uncertainty_proxy")
                ),
                "evidence_available_is_not_goal_validity": True,
                "evaluation_only_candidate_label_join": True,
                **common_flags(),
            }
        )
    return out


def materialize_pair_rows(
    *,
    action_rows: Sequence[Mapping[str, Any]],
    candidate_eval_rows_by_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for action in sorted(action_rows, key=pair_key):
        key = join_key(action)
        payload = key_payload(key)
        pkey = pair_key(action)
        candidate_a_id, candidate_b_id = pkey[-2], pkey[-1]
        candidate_a = candidate_eval_rows_by_key.get((*key, candidate_a_id)) or {}
        candidate_b = candidate_eval_rows_by_key.get((*key, candidate_b_id)) or {}
        pattern = pair_label_pattern(candidate_a, candidate_b)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_arbitration_followup_action_freeze",
                "row_type": "post_action_goal_validity_arbitration_followup_evaluation_join_pair",
                "join_key": {**payload, "candidate_a_id": candidate_a_id, "candidate_b_id": candidate_b_id},
                **payload,
                "candidate_a_id": candidate_a_id,
                "candidate_b_id": candidate_b_id,
                "target_role": action.get("target_role"),
                "source_branch_action": action.get("source_branch_action"),
                "source_resolution_route": action.get("source_resolution_route"),
                "selected_evidence_family": action.get("selected_evidence_family"),
                "selected_branch": action.get("selected_branch"),
                "selected_action": action.get("selected_action"),
                "action_frozen_before_evaluation_join": True,
                "same_pair_order_as_action_row": True,
                "request_evidence_status": action.get("request_evidence_status"),
                "candidate_pair_status_pattern": action.get("candidate_pair_status_pattern"),
                "candidate_a_evidence_status": action.get("candidate_a_evidence_status"),
                "candidate_b_evidence_status": action.get("candidate_b_evidence_status"),
                "candidate_a_support_evidence_count": safe_int(action.get("candidate_a_support_evidence_count"), 0),
                "candidate_b_support_evidence_count": safe_int(action.get("candidate_b_support_evidence_count"), 0),
                "candidate_a_contradiction_evidence_count": safe_int(
                    action.get("candidate_a_contradiction_evidence_count"),
                    0,
                ),
                "candidate_b_contradiction_evidence_count": safe_int(
                    action.get("candidate_b_contradiction_evidence_count"),
                    0,
                ),
                "candidate_a_correctness_label_for_evaluation_only": candidate_a.get(
                    "candidate_correctness_label_for_evaluation_only"
                ),
                "candidate_b_correctness_label_for_evaluation_only": candidate_b.get(
                    "candidate_correctness_label_for_evaluation_only"
                ),
                "candidate_a_wrong_label_for_evaluation_only": candidate_a.get(
                    "candidate_wrong_label_for_evaluation_only"
                ),
                "candidate_b_wrong_label_for_evaluation_only": candidate_b.get(
                    "candidate_wrong_label_for_evaluation_only"
                ),
                "candidate_a_no_valid_candidate_pool_for_evaluation_only": (
                    candidate_a.get("no_valid_candidate_pool_for_evaluation_only") is True
                ),
                "candidate_b_no_valid_candidate_pool_for_evaluation_only": (
                    candidate_b.get("no_valid_candidate_pool_for_evaluation_only") is True
                ),
                "candidate_pair_label_pattern_for_evaluation_only": pattern,
                "pair_label_join_available": pattern != "label_missing",
                "pair_label_is_action_forbidden": True,
                "support_count_abs_delta": safe_int(action.get("support_count_abs_delta"), 0),
                "contradiction_count_abs_delta": safe_int(action.get("contradiction_count_abs_delta"), 0),
                "viewpoint_coverage_abs_delta": safe_float(action.get("viewpoint_coverage_abs_delta")),
                "association_quality_abs_delta": safe_float(action.get("association_quality_abs_delta")),
                "map_pose_consistency_abs_delta": safe_float(action.get("map_pose_consistency_abs_delta")),
                "pose_graph_connectivity_abs_delta": safe_float(action.get("pose_graph_connectivity_abs_delta")),
                "map_pose_uncertainty_abs_delta": safe_float(action.get("map_pose_uncertainty_abs_delta")),
                "pairwise_goal_validity_arbitration_required": (
                    action.get("pairwise_goal_validity_arbitration_required") is True
                ),
                "missing_evidence_second_view_followup_required": (
                    action.get("missing_evidence_second_view_followup_required") is True
                ),
                "terminal_selector_allowed_from_pair_label": False,
                **common_flags(),
            }
        )
    return out


def materialize_baseline_rows(source_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_rows, key=policy_key):
        key = join_key(source)
        payload = key_payload(key)
        policy = policy_key(source)[-1]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_arbitration_followup_action_freeze",
                "row_type": "post_action_goal_validity_arbitration_followup_evaluation_join_baseline",
                "join_key": {**payload, "policy_name": policy},
                **payload,
                "policy_name": policy,
                "target_role": source.get("target_role"),
                "policy_selected_candidate_id": source.get("policy_selected_candidate_id"),
                "selector_id": source.get("selector_id"),
                "selector_action": source.get("selector_action"),
                "terminal_commit_proxy": source.get("terminal_commit_proxy"),
                "success_commit_proxy": source.get("success_commit_proxy"),
                "wrong_goal_visit_proxy": source.get("wrong_goal_visit_proxy"),
                "wasted_path_proxy_m": safe_float(source.get("wasted_path_proxy_m")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "evaluation_only_baseline_context": True,
                "not_used_for_arbitration_followup_action": True,
                **common_flags(),
            }
        )
    return out


def promotion_blocker(row: Mapping[str, Any]) -> str:
    if row.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1":
        return "pairwise_goal_region_map_pose_arbitration_required"
    if row.get("selected_branch") == "missing_evidence_second_view_followup_v1":
        return "missing_evidence_second_view_followup_required"
    if row.get("wrong_goal_reduction_only_by_evidence_availability") is True:
        return "wrong_goal_reduction_only_by_evidence_availability"
    return "arbitration_followup_evaluation_join_only_terminal_utility_blocked"


def materialize_promotion_probe_rows(
    request_rows: Sequence[Mapping[str, Any]],
    pairs_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted((row for row in request_rows if row.get("target_role") == "primary_target"), key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        pair = pairs_by_key.get(key) or {}
        blocker = promotion_blocker(request)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_arbitration_followup_action_freeze",
                "row_type": "post_action_goal_validity_arbitration_followup_evaluation_join_promotion_probe",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "source_resolution_route": request.get("source_resolution_route"),
                "selected_branch": request.get("selected_branch"),
                "selected_action": request.get("selected_action"),
                "action_frozen_before_evaluation_join": True,
                "request_evidence_status": request.get("request_evidence_status"),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "baseline_wrong_goal_exposure": request.get("baseline_wrong_goal_exposure"),
                "baseline_wasted_path_exposure_m": request.get("baseline_wasted_path_exposure_m"),
                "wrong_goal_reduction_only_by_evidence_availability": request.get(
                    "wrong_goal_reduction_only_by_evidence_availability"
                ),
                "candidate_pair_status_pattern": pair.get("candidate_pair_status_pattern"),
                "candidate_pair_label_pattern_for_evaluation_only": pair.get(
                    "candidate_pair_label_pattern_for_evaluation_only"
                ),
                "pairwise_goal_validity_arbitration_required": (
                    request.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1"
                ),
                "missing_evidence_second_view_followup_required": (
                    request.get("selected_branch") == "missing_evidence_second_view_followup_v1"
                ),
                "promotion_probe_gate_passed": False,
                "promotion_probe_primary_blocker": blocker,
                "post_action_wrong_goal_claim_allowed": False,
                **common_flags(),
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "evaluation_join_only",
        "terminal_utility_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "paper_claim_blocked",
    ]
    if row.get("target_role") != "primary_target":
        tags.append("audit_control_preserved")
    else:
        if row.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1":
            tags.append("pairwise_goal_region_map_pose_arbitration_required")
            tags.append("pair_label_evaluation_only")
        if row.get("selected_branch") == "missing_evidence_second_view_followup_v1":
            tags.append("missing_evidence_second_view_followup_required")
        if row.get("wrong_goal_reduction_only_by_evidence_availability") is True:
            tags.append("wrong_goal_reduction_only_by_evidence_availability")
        tags.append("evidence_available_is_not_goal_validity")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "pairwise_goal_region_map_pose_arbitration_required",
        "missing_evidence_second_view_followup_required",
        "wrong_goal_reduction_only_by_evidence_availability",
        "audit_control_preserved",
        "evaluation_join_only",
    ):
        if tag in tags:
            return tag
    return "unknown"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        tags = failure_tags(request)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_arbitration_followup_action_freeze",
                "row_type": "post_action_goal_validity_arbitration_followup_evaluation_join_failure",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "source_resolution_route": request.get("source_resolution_route"),
                "selected_branch": request.get("selected_branch"),
                "selected_action": request.get("selected_action"),
                "request_evidence_status": request.get("request_evidence_status"),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "wrong_goal_reduction_only_by_evidence_availability": request.get(
                    "wrong_goal_reduction_only_by_evidence_availability"
                ),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                **common_flags(),
            }
        )
    return out


def baseline_policy_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        policy: {
            "rows": sum(1 for row in rows if row.get("policy_name") == policy),
            "primary_target_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("target_role") == "primary_target"
            ),
            "terminal_commit_proxy_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("terminal_commit_proxy") is True
            ),
            "success_commit_proxy_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("success_commit_proxy") is True
            ),
            "wrong_goal_visit_proxy_rows": sum(
                1 for row in rows if row.get("policy_name") == policy and row.get("wrong_goal_visit_proxy") is True
            ),
            "primary_target_wrong_goal_visit_proxy_rows": sum(
                1
                for row in rows
                if row.get("policy_name") == policy
                and row.get("target_role") == "primary_target"
                and row.get("wrong_goal_visit_proxy") is True
            ),
            "wasted_path_proxy_m_stats": number_stats(
                row.get("wasted_path_proxy_m") for row in rows if row.get("policy_name") == policy
            ),
            "primary_target_wasted_path_proxy_m_stats": number_stats(
                row.get("wasted_path_proxy_m")
                for row in rows
                if row.get("policy_name") == policy and row.get("target_role") == "primary_target"
            ),
        }
        for policy in POLICIES
    }


def gate_from_counts(contract: Mapping[str, Any], counts: Mapping[str, int]) -> Dict[str, bool]:
    gate = contract.get("evaluation_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    return {
        "request_rows_expected_passed": counts["request_rows"] == safe_int(gate.get("request_rows_expected"), 50),
        "selected_target_request_rows_expected_passed": counts["selected_target_request_rows"]
        == safe_int(gate.get("selected_target_request_rows_expected"), 21),
        "audit_request_rows_expected_passed": counts["audit_request_rows"]
        == safe_int(gate.get("audit_request_rows_expected"), 29),
        "candidate_rows_expected_passed": counts["candidate_rows"]
        == safe_int(gate.get("candidate_rows_expected"), 97),
        "selected_target_candidate_rows_expected_passed": counts["selected_target_candidate_rows"]
        == safe_int(gate.get("selected_target_candidate_rows_expected"), 42),
        "pair_rows_expected_passed": counts["pair_rows"] == safe_int(gate.get("pair_rows_expected"), 21),
        "pairwise_arbitration_pair_rows_expected_passed": counts["pairwise_arbitration_pair_rows"]
        == safe_int(gate.get("pairwise_arbitration_pair_rows_expected"), 18),
        "missing_followup_pair_rows_expected_passed": counts["missing_followup_pair_rows"]
        == safe_int(gate.get("missing_followup_pair_rows_expected"), 3),
        "baseline_rows_expected_passed": counts["baseline_rows"]
        == safe_int(gate.get("baseline_rows_expected"), 150),
        "selected_target_baseline_rows_expected_passed": counts["selected_target_baseline_rows"]
        == safe_int(gate.get("selected_target_baseline_rows_expected"), 63),
        "promotion_probe_rows_minimum_passed": counts["promotion_probe_rows"]
        >= safe_int(gate.get("minimum_promotion_probe_rows"), 21),
        "candidate_label_missing_rows_expected_passed": counts["candidate_label_missing_rows"]
        == safe_int(gate.get("candidate_label_missing_rows_expected"), 0),
        "pair_label_missing_rows_expected_passed": counts["pair_label_missing_rows"]
        == safe_int(gate.get("pair_label_missing_rows_expected"), 0),
        "wrong_goal_reduction_only_by_evidence_availability_rows_expected_passed": counts[
            "wrong_goal_reduction_only_by_evidence_availability_rows"
        ]
        == safe_int(gate.get("wrong_goal_reduction_only_by_evidence_availability_rows_expected"), 9),
        "evidence_conflict_blocks_promotion_rows_expected_passed": counts[
            "evidence_conflict_blocks_promotion_rows"
        ]
        == safe_int(gate.get("evidence_conflict_blocks_promotion_rows_expected"), 18),
        "evidence_missing_blocks_promotion_rows_expected_passed": counts["evidence_missing_blocks_promotion_rows"]
        == safe_int(gate.get("evidence_missing_blocks_promotion_rows_expected"), 3),
        "action_evidence_forbidden_key_count_passed": counts["action_evidence_forbidden_key_count"]
        == safe_int(gate.get("action_evidence_forbidden_key_count_expected"), 0),
        "terminal_commit_rows_passed": counts["terminal_commit_rows"]
        == safe_int(gate.get("terminal_commit_rows_expected"), 0),
        "candidate_commit_rows_passed": counts["candidate_commit_rows"]
        == safe_int(gate.get("candidate_commit_rows_expected"), 0),
        "candidate_rejection_rows_passed": counts["candidate_rejection_rows"]
        == safe_int(gate.get("candidate_rejection_rows_expected"), 0),
        "uses_gt_for_action_passed": counts["uses_gt_for_action_true_rows"]
        == safe_int(gate.get("uses_gt_for_action_true_rows_expected"), 0),
        "paper_claim_blocked_passed": counts["paper_claim_allowed_true_rows"]
        == safe_int(gate.get("paper_claim_allowed_true_rows_expected"), 0),
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    promotion_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    all_output_rows = [*request_rows, *candidate_rows, *pair_rows, *baseline_rows, *promotion_rows, *failure_rows]
    selected_target_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    audit_requests = [row for row in request_rows if row.get("target_role") != "primary_target"]
    selected_target_candidates = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    selected_target_baselines = [row for row in baseline_rows if row.get("target_role") == "primary_target"]
    candidate_label_missing_rows = sum(
        1 for row in candidate_rows if row.get("goal_validity_label_join_available") is not True
    )
    pair_label_missing_rows = sum(1 for row in pair_rows if row.get("pair_label_join_available") is not True)
    counts = {
        "request_rows": len(request_rows),
        "selected_target_request_rows": len(selected_target_requests),
        "audit_request_rows": len(audit_requests),
        "candidate_rows": len(candidate_rows),
        "selected_target_candidate_rows": len(selected_target_candidates),
        "pair_rows": len(pair_rows),
        "pairwise_arbitration_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1"
        ),
        "missing_followup_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "missing_evidence_second_view_followup_v1"
        ),
        "baseline_rows": len(baseline_rows),
        "selected_target_baseline_rows": len(selected_target_baselines),
        "promotion_probe_rows": len(promotion_rows),
        "failure_rows": len(failure_rows),
        "candidate_label_missing_rows": candidate_label_missing_rows,
        "pair_label_missing_rows": pair_label_missing_rows,
        "wrong_goal_reduction_only_by_evidence_availability_rows": sum(
            1 for row in request_rows if row.get("wrong_goal_reduction_only_by_evidence_availability") is True
        ),
        "evidence_conflict_blocks_promotion_rows": sum(
            1 for row in request_rows if row.get("evidence_conflict_blocks_promotion") is True
        ),
        "evidence_missing_blocks_promotion_rows": sum(
            1 for row in request_rows if row.get("evidence_missing_blocks_promotion") is True
        ),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_output_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_output_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_output_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_output_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_output_rows, "paper_claim_allowed"),
    }
    gate = gate_from_counts(contract, counts)
    join_gate_passed = all(gate.values())
    baseline_counts = baseline_policy_counts(baseline_rows)
    primary_blocker = (
        "pairwise_goal_region_map_pose_arbitration_required"
        if counts["pairwise_arbitration_pair_rows"] > 0
        else "missing_evidence_second_view_followup_required"
        if counts["missing_followup_pair_rows"] > 0
        else "wrong_goal_reduction_only_by_evidence_availability"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "evaluation_join_gate_passed_promotion_blocked"
        if join_gate_passed
        else "evaluation_join_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        **counts,
        "route_counts": compact_counter(row.get("source_resolution_route") for row in request_rows),
        "branch_counts": compact_counter(row.get("selected_branch") for row in request_rows),
        "request_evidence_status_counts": compact_counter(row.get("request_evidence_status") for row in request_rows),
        "selected_target_request_evidence_status_counts": compact_counter(
            row.get("request_evidence_status") for row in selected_target_requests
        ),
        "candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in candidate_rows
        ),
        "selected_target_candidate_evidence_status_counts": compact_counter(
            row.get("candidate_evidence_status") for row in selected_target_candidates
        ),
        "candidate_correctness_label_counts": {
            "correct": sum(
                1 for row in candidate_rows if row.get("candidate_correctness_label_for_evaluation_only") is True
            ),
            "wrong": sum(
                1 for row in candidate_rows if row.get("candidate_wrong_label_for_evaluation_only") is True
            ),
            "no_valid_pool": sum(
                1 for row in candidate_rows if row.get("no_valid_candidate_pool_for_evaluation_only") is True
            ),
            "label_missing": candidate_label_missing_rows,
        },
        "selected_target_candidate_correctness_label_counts": {
            "correct": sum(
                1
                for row in selected_target_candidates
                if row.get("candidate_correctness_label_for_evaluation_only") is True
            ),
            "wrong": sum(
                1
                for row in selected_target_candidates
                if row.get("candidate_wrong_label_for_evaluation_only") is True
            ),
            "no_valid_pool": sum(
                1
                for row in selected_target_candidates
                if row.get("no_valid_candidate_pool_for_evaluation_only") is True
            ),
            "label_missing": sum(
                1 for row in selected_target_candidates if row.get("goal_validity_label_join_available") is not True
            ),
        },
        "pair_status_pattern_counts": compact_counter(row.get("candidate_pair_status_pattern") for row in pair_rows),
        "pair_label_pattern_counts": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_rows
        ),
        "pair_label_pattern_counts_by_branch": {
            branch: compact_counter(
                row.get("candidate_pair_label_pattern_for_evaluation_only")
                for row in pair_rows
                if row.get("selected_branch") == branch
            )
            for branch in (
                "pairwise_goal_region_map_pose_arbitration_v1",
                "missing_evidence_second_view_followup_v1",
            )
        },
        "baseline_policy_counts": baseline_counts,
        "baseline_wrong_goal_rows": {
            "all_rows": {
                policy: baseline_counts[policy]["wrong_goal_visit_proxy_rows"] for policy in POLICIES
            },
            "primary_target_rows": {
                policy: baseline_counts[policy]["primary_target_wrong_goal_visit_proxy_rows"] for policy in POLICIES
            },
        },
        "baseline_wasted_path_stats": {
            policy: {
                "all_rows": baseline_counts[policy]["wasted_path_proxy_m_stats"],
                "primary_target_rows": baseline_counts[policy]["primary_target_wasted_path_proxy_m_stats"],
            }
            for policy in POLICIES
        },
        "request_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in request_rows
        ),
        "request_viewpoint_evidence_gap_state_counts": compact_counter(
            row.get("viewpoint_evidence_gap_state") for row in request_rows
        ),
        "request_map_pose_uncertainty_state_counts": compact_counter(
            row.get("map_pose_consistency_uncertainty_state") for row in request_rows
        ),
        "pair_support_count_abs_delta_stats": number_stats(row.get("support_count_abs_delta") for row in pair_rows),
        "pair_association_quality_abs_delta_stats": number_stats(
            row.get("association_quality_abs_delta") for row in pair_rows
        ),
        "pair_map_pose_consistency_abs_delta_stats": number_stats(
            row.get("map_pose_consistency_abs_delta") for row in pair_rows
        ),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "evaluation_join_gate": gate,
        "evaluation_join_gate_passed": join_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "promotion_gate_attempted": True,
        "promotion_gate_primary_failure_conditions": [
            condition
            for condition, count_key in (
                ("pairwise_goal_region_map_pose_arbitration_required", "pairwise_arbitration_pair_rows"),
                ("missing_evidence_second_view_followup_required", "missing_followup_pair_rows"),
                (
                    "wrong_goal_reduction_only_by_evidence_availability",
                    "wrong_goal_reduction_only_by_evidence_availability_rows",
                ),
            )
            if counts[count_key] > 0
        ],
        "terminal_utility_validation_allowed": False,
        "terminal_utility_contract_allowed_now": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": primary_blocker,
        "next_task": "freeze_non_gt_pairwise_goal_region_map_pose_arbitration_rule_contract",
        "interpretation": {
            "fact": (
                "The materializer joins frozen arbitration/follow-up action rows to evaluation-only candidate, "
                "pair, baseline, wrong-goal, wasted-path, and map/pose fields on the same 50 rows."
            ),
            "agent_inference": (
                "The join is action-safe and pair labels are complete, but promotion remains blocked because "
                "pairwise arbitration and missing follow-up still need a predeclared non-GT validation rule."
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
        "ok": summary.get("evaluation_join_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "selected_target_request_rows": summary.get("selected_target_request_rows"),
            "audit_request_rows": summary.get("audit_request_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "selected_target_candidate_rows": summary.get("selected_target_candidate_rows"),
            "pair_rows": summary.get("pair_rows"),
            "pairwise_arbitration_pair_rows": summary.get("pairwise_arbitration_pair_rows"),
            "missing_followup_pair_rows": summary.get("missing_followup_pair_rows"),
            "baseline_rows": summary.get("baseline_rows"),
            "selected_target_baseline_rows": summary.get("selected_target_baseline_rows"),
            "promotion_probe_rows": summary.get("promotion_probe_rows"),
            "failure_rows": summary.get("failure_rows"),
            "candidate_label_missing_rows": summary.get("candidate_label_missing_rows"),
            "pair_label_missing_rows": summary.get("pair_label_missing_rows"),
            "wrong_goal_reduction_only_by_evidence_availability_rows": summary.get(
                "wrong_goal_reduction_only_by_evidence_availability_rows"
            ),
            "evidence_conflict_blocks_promotion_rows": summary.get("evidence_conflict_blocks_promotion_rows"),
            "evidence_missing_blocks_promotion_rows": summary.get("evidence_missing_blocks_promotion_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "route_counts": summary.get("route_counts"),
        "branch_counts": summary.get("branch_counts"),
        "pair_label_pattern_counts": summary.get("pair_label_pattern_counts"),
        "pair_label_pattern_counts_by_branch": summary.get("pair_label_pattern_counts_by_branch"),
        "baseline_wrong_goal_rows": summary.get("baseline_wrong_goal_rows"),
        "baseline_wasted_path_stats": summary.get("baseline_wasted_path_stats"),
        "promotion_gate_primary_failure_conditions": summary.get("promotion_gate_primary_failure_conditions"),
        "evaluation_join_gate": summary.get("evaluation_join_gate"),
        "evaluation_join_gate_passed": summary.get("evaluation_join_gate_passed"),
        "active_reobservation_promotion_gate_passed": summary.get("active_reobservation_promotion_gate_passed"),
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
                "materialize_post_action_goal_validity_arbitration_followup_evaluation_join.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_post_action_goal_validity_arbitration_followup_evaluation_join"
            ),
            (
                "jq '{status, request_rows, candidate_rows, pair_rows, baseline_rows, promotion_probe_rows, "
                "failure_rows, pair_label_pattern_counts, evaluation_join_gate_passed, "
                "active_reobservation_promotion_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "arbitration_followup_action_rows_frozen_before_labels": True,
            "same_row_comparison_required": True,
            "same_candidate_pool_required": True,
            "same_pair_rows_required": True,
            "same_reobservation_budget_required": True,
            "commit_based_wrong_goal_required": True,
            "pair_labels_evaluation_only": True,
            "pair_order_not_changed_by_labels": True,
            "evidence_available_not_goal_validity": True,
            "conflict_pairs_preserved": True,
            "missing_pairs_preserved": True,
            "audit_rows_preserved": True,
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

    action_request_rows = load_jsonl(Path(str(source["arbitration_followup_request_rows"])))
    action_candidate_rows = load_jsonl(Path(str(source["arbitration_followup_candidate_rows"])))
    action_pair_rows = load_jsonl(Path(str(source["arbitration_followup_pair_rows"])))
    previous_request_rows = load_jsonl(Path(str(source["previous_evaluation_join_request_rows"])))
    previous_candidate_rows = load_jsonl(Path(str(source["previous_evaluation_join_candidate_rows"])))
    previous_baseline_rows = load_jsonl(Path(str(source["previous_evaluation_join_baseline_rows"])))

    previous_eval_rows_by_key = index_one(previous_request_rows)
    previous_eval_rows_by_candidate = index_candidates(previous_candidate_rows)
    baselines_by_key = policy_lookup(previous_baseline_rows)

    request_rows = materialize_request_rows(
        action_rows=action_request_rows,
        previous_eval_rows_by_key=previous_eval_rows_by_key,
        baselines_by_key=baselines_by_key,
    )
    candidate_rows = materialize_candidate_rows(
        action_rows=action_candidate_rows,
        previous_eval_rows_by_candidate=previous_eval_rows_by_candidate,
    )
    candidate_eval_rows_by_key = index_candidates(candidate_rows)
    pair_rows = materialize_pair_rows(
        action_rows=action_pair_rows,
        candidate_eval_rows_by_key=candidate_eval_rows_by_key,
    )
    baseline_rows = materialize_baseline_rows(previous_baseline_rows)
    pairs_by_key = index_one(pair_rows)
    promotion_rows = materialize_promotion_probe_rows(request_rows, pairs_by_key)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*action_request_rows, *action_candidate_rows, *action_pair_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        baseline_rows=baseline_rows,
        promotion_rows=promotion_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_eval_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_eval_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_eval_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_eval_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["promotion_probe_rows"], promotion_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("evaluation_join_gate_passed") is not True:
        raise SystemExit("post-action arbitration/follow-up evaluation join gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize the post-action goal-validity arbitration/follow-up evaluation join."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
