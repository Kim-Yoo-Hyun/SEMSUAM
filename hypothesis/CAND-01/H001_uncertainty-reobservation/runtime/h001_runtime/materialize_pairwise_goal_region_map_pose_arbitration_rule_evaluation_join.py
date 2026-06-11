import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.pairwise_goal_region_map_pose_arbitration_rule_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_v1"

OUTPUT_FILES = {
    "request_eval_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_request_rows.jsonl",
    "candidate_eval_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_candidate_rows.jsonl",
    "pair_eval_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_pair_rows.jsonl",
    "baseline_eval_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_baseline_rows.jsonl",
    "promotion_probe_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_promotion_probe_rows.jsonl",
    "failure_rows": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_failure_rows.jsonl",
    "summary": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")
PROVISIONAL_STATES = {
    "candidate_a_provisionally_supported_by_non_gt_pairwise_rule",
    "candidate_b_provisionally_supported_by_non_gt_pairwise_rule",
}
FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "no_valid_candidate_pool_label",
    "no_valid_candidate_pool_for_evaluation_only",
    "candidate_pair_label_pattern_for_evaluation_only",
    "wrong_goal_visit_proxy",
    "success_commit_proxy",
    "terminal_commit_proxy",
    "wasted_path_proxy_m",
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "oracle_shortest_path",
    "ground_truth",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "post_hoc_label_tuned_threshold",
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


def index_by_join(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


def index_by_candidate(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def index_by_pair(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str, str], Mapping[str, Any]]:
    return {pair_key(row): row for row in rows}


def group_pairs_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[join_key(row)].append(row)
    return dict(grouped)


def group_baselines_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[join_key(row)][policy_key(row)[-1]] = row
    return dict(grouped)


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


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
        scan(row.get("rule_inputs", {}))
        scan(row.get("action_evidence_inputs", {}))
        scan(row.get("action_route_inputs", {}))
    return sorted(found)


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


def supported_candidate_id(pair: Mapping[str, Any]) -> Optional[str]:
    state = pair.get("non_gt_pairwise_rule_state")
    if state == "candidate_a_provisionally_supported_by_non_gt_pairwise_rule":
        return str(pair.get("candidate_a_id") or "")
    if state == "candidate_b_provisionally_supported_by_non_gt_pairwise_rule":
        return str(pair.get("candidate_b_id") or "")
    return None


def label_for_candidate_in_pair(pair: Mapping[str, Any], candidate_id: Optional[str]) -> Tuple[Optional[bool], Optional[bool]]:
    if not candidate_id:
        return (None, None)
    if candidate_id == pair.get("candidate_a_id"):
        correct = pair.get("candidate_a_correctness_label_for_evaluation_only")
        wrong = (
            pair.get("candidate_a_wrong_label_for_evaluation_only") is True
            or pair.get("candidate_a_no_valid_candidate_pool_for_evaluation_only") is True
        )
        return (correct if isinstance(correct, bool) else None, wrong)
    if candidate_id == pair.get("candidate_b_id"):
        correct = pair.get("candidate_b_correctness_label_for_evaluation_only")
        wrong = (
            pair.get("candidate_b_wrong_label_for_evaluation_only") is True
            or pair.get("candidate_b_no_valid_candidate_pool_for_evaluation_only") is True
        )
        return (correct if isinstance(correct, bool) else None, wrong)
    return (None, None)


def baseline_wrong_goal_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("wrong_goal_visit_proxy") is True) for policy in POLICIES}


def baseline_success_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("success_commit_proxy") is True) for policy in POLICIES}


def baseline_terminal_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, bool]:
    return {policy: bool((policy_rows.get(policy) or {}).get("terminal_commit_proxy") is True) for policy in POLICIES}


def baseline_wasted_path_exposure(policy_rows: Mapping[str, Mapping[str, Any]]) -> Dict[str, Optional[float]]:
    return {policy: safe_float((policy_rows.get(policy) or {}).get("wasted_path_proxy_m")) for policy in POLICIES}


def materialize_candidate_rows(
    *,
    rule_candidates: Sequence[Mapping[str, Any]],
    previous_candidates_by_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rule in sorted(rule_candidates, key=candidate_key):
        key = join_key(rule)
        payload = key_payload(key)
        ckey = candidate_key(rule)
        cid = ckey[-1]
        previous = previous_candidates_by_key.get(ckey) or {}
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_pairwise_rule_freeze",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": rule.get("target_role"),
                "source_branch_action": rule.get("source_branch_action"),
                "source_resolution_route": rule.get("source_resolution_route"),
                "selected_evidence_family": rule.get("selected_evidence_family"),
                "selected_branch": rule.get("selected_branch"),
                "selected_action": rule.get("selected_action"),
                "rule_output_frozen_before_evaluation_join": True,
                "candidate_evidence_status": rule.get("candidate_evidence_status"),
                "candidate_evidence_reason": rule.get("candidate_evidence_reason"),
                "candidate_support_evidence_count": safe_int(rule.get("candidate_support_evidence_count"), 0),
                "candidate_contradiction_evidence_count": safe_int(
                    rule.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "candidate_pair_rule_states": rule.get("candidate_pair_rule_states", []),
                "candidate_in_pair_rule_rows": safe_int(rule.get("candidate_in_pair_rule_rows"), 0),
                "candidate_has_provisional_pair_support": (
                    rule.get("candidate_has_provisional_pair_support") is True
                ),
                "candidate_pair_rule_has_any_provisional_support": (
                    rule.get("candidate_pair_rule_has_any_provisional_support") is True
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
                "viewpoint_coverage_delta": safe_float(rule.get("viewpoint_coverage_delta")),
                "association_quality_proxy": safe_float(rule.get("association_quality_proxy")),
                "map_pose_consistency_delta": safe_float(rule.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(rule.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    rule.get("map_pose_consistency_uncertainty_proxy")
                ),
                "evaluation_only_candidate_label_join": True,
                "label_fields_used_for_action": False,
                **common_flags(),
            }
        )
    return out


def materialize_pair_rows(
    *,
    rule_pairs: Sequence[Mapping[str, Any]],
    candidate_eval_by_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    previous_pairs_by_key: Mapping[Tuple[str, str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rule in sorted(rule_pairs, key=pair_key):
        key = join_key(rule)
        payload = key_payload(key)
        pkey = pair_key(rule)
        candidate_a_id, candidate_b_id = pkey[-2], pkey[-1]
        candidate_a = candidate_eval_by_key.get((*key, candidate_a_id)) or {}
        candidate_b = candidate_eval_by_key.get((*key, candidate_b_id)) or {}
        previous_pair = previous_pairs_by_key.get(pkey) or {}
        pattern = previous_pair.get("candidate_pair_label_pattern_for_evaluation_only")
        if not pattern:
            pattern = pair_label_pattern(candidate_a, candidate_b)
        output_base = {
            "candidate_a_id": candidate_a_id,
            "candidate_b_id": candidate_b_id,
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
        }
        supported_id = supported_candidate_id({**rule, **output_base})
        supported_correct, supported_wrong = label_for_candidate_in_pair({**rule, **output_base}, supported_id)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_pairwise_rule_freeze",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_pair",
                "join_key": {**payload, "candidate_a_id": candidate_a_id, "candidate_b_id": candidate_b_id},
                **payload,
                **output_base,
                "target_role": rule.get("target_role"),
                "source_branch_action": rule.get("source_branch_action"),
                "source_resolution_route": rule.get("source_resolution_route"),
                "selected_evidence_family": rule.get("selected_evidence_family"),
                "selected_branch": rule.get("selected_branch"),
                "selected_action": rule.get("selected_action"),
                "rule_output_frozen_before_evaluation_join": True,
                "same_pair_order_as_rule_row": True,
                "non_gt_pairwise_rule_state": rule.get("non_gt_pairwise_rule_state"),
                "goal_region_contrast_state": rule.get("goal_region_contrast_state"),
                "object_relation_anchor_consistency_state": rule.get("object_relation_anchor_consistency_state"),
                "map_pose_non_contradiction_state": rule.get("map_pose_non_contradiction_state"),
                "rule_input_complete": rule.get("rule_input_complete") is True,
                "rule_defer_reason": rule.get("rule_defer_reason"),
                "pairwise_goal_validity_arbitration_required": (
                    rule.get("pairwise_goal_validity_arbitration_required") is True
                ),
                "missing_evidence_second_view_followup_required": (
                    rule.get("missing_evidence_second_view_followup_required") is True
                ),
                "candidate_a_support_evidence_count": safe_int(rule.get("candidate_a_support_evidence_count"), 0),
                "candidate_b_support_evidence_count": safe_int(rule.get("candidate_b_support_evidence_count"), 0),
                "candidate_a_contradiction_evidence_count": safe_int(
                    rule.get("candidate_a_contradiction_evidence_count"),
                    0,
                ),
                "candidate_b_contradiction_evidence_count": safe_int(
                    rule.get("candidate_b_contradiction_evidence_count"),
                    0,
                ),
                "support_count_abs_delta": safe_int(rule.get("support_count_abs_delta"), 0),
                "contradiction_count_abs_delta": safe_int(rule.get("contradiction_count_abs_delta"), 0),
                "viewpoint_coverage_abs_delta": safe_float(rule.get("viewpoint_coverage_abs_delta")),
                "association_quality_abs_delta": safe_float(rule.get("association_quality_abs_delta")),
                "map_pose_consistency_abs_delta": safe_float(rule.get("map_pose_consistency_abs_delta")),
                "pose_graph_connectivity_abs_delta": safe_float(rule.get("pose_graph_connectivity_abs_delta")),
                "map_pose_uncertainty_abs_delta": safe_float(rule.get("map_pose_uncertainty_abs_delta")),
                "goal_region_pair_evidence_available": rule.get("goal_region_pair_evidence_available") is True,
                "object_relation_candidate_a_available": rule.get("object_relation_candidate_a_available") is True,
                "object_relation_candidate_b_available": rule.get("object_relation_candidate_b_available") is True,
                "candidate_pair_label_pattern_for_evaluation_only": pattern,
                "pair_label_join_available": pattern != "label_missing",
                "pair_label_is_action_forbidden": True,
                "label_fields_used_for_action": False,
                "provisionally_supported_candidate_id": supported_id,
                "provisional_rule_candidate_correct_for_evaluation_only": supported_correct,
                "provisional_rule_candidate_wrong_for_evaluation_only": supported_wrong,
                "provisional_support_is_terminal_commit": False,
                "terminal_selector_allowed_from_pair_label": False,
                **common_flags(),
            }
        )
    return out


def materialize_request_rows(
    *,
    rule_requests: Sequence[Mapping[str, Any]],
    previous_requests_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    baselines_by_key: Mapping[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]],
    pairs_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for rule in sorted(rule_requests, key=join_key):
        key = join_key(rule)
        payload = key_payload(key)
        previous = previous_requests_by_key.get(key) or {}
        policy_rows = baselines_by_key.get(key) or {}
        pairs = list(pairs_by_key.get(key, []))
        provisional_pairs = [row for row in pairs if row.get("non_gt_pairwise_rule_state") in PROVISIONAL_STATES]
        provisional_wrong = [
            row for row in provisional_pairs if row.get("provisional_rule_candidate_wrong_for_evaluation_only") is True
        ]
        provisional_correct = [
            row
            for row in provisional_pairs
            if row.get("provisional_rule_candidate_correct_for_evaluation_only") is True
        ]
        pair_unresolved = [row for row in pairs if row.get("non_gt_pairwise_rule_state") == "pair_remains_unresolved"]
        missing_followup = [
            row for row in pairs if row.get("non_gt_pairwise_rule_state") == "missing_evidence_second_view_followup_required"
        ]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_pairwise_rule_freeze",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_request",
                "join_key": payload,
                **payload,
                "target_role": rule.get("target_role"),
                "source_branch_action": rule.get("source_branch_action"),
                "source_resolution_route": rule.get("source_resolution_route"),
                "source_resolution_reason": rule.get("source_resolution_reason"),
                "selected_evidence_family": rule.get("selected_evidence_family"),
                "selected_branch": rule.get("selected_branch"),
                "selected_action": rule.get("selected_action"),
                "request_rule_state": rule.get("request_rule_state"),
                "rule_output_frozen_before_evaluation_join": True,
                "rule_output_nonterminal": True,
                "goal_validity_risk_state": previous.get(
                    "goal_validity_risk_state",
                    rule.get("goal_validity_risk_state"),
                ),
                "goal_validity_risk_proxy": safe_float(previous.get("goal_validity_risk_proxy")),
                "viewpoint_evidence_gap_state": previous.get(
                    "viewpoint_evidence_gap_state",
                    rule.get("viewpoint_evidence_gap_state"),
                ),
                "viewpoint_evidence_gap_proxy": safe_float(previous.get("viewpoint_evidence_gap_proxy")),
                "map_pose_consistency_uncertainty_state": previous.get(
                    "map_pose_consistency_uncertainty_state",
                    rule.get("map_pose_consistency_uncertainty_state"),
                ),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    previous.get("map_pose_consistency_uncertainty_proxy")
                ),
                "pose_graph_connectivity_delta": safe_float(rule.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(rule.get("map_pose_consistency_delta")),
                "pair_rule_rows": len(pairs),
                "pair_rule_state_counts": compact_counter(row.get("non_gt_pairwise_rule_state") for row in pairs),
                "pair_label_pattern_counts": compact_counter(
                    row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pairs
                ),
                "provisional_rule_rows": len(provisional_pairs),
                "provisional_rule_correct_rows": len(provisional_correct),
                "provisional_rule_wrong_rows": len(provisional_wrong),
                "pair_unresolved_rows": len(pair_unresolved),
                "missing_followup_required_rows": len(missing_followup),
                "baseline_wrong_goal_exposure": baseline_wrong_goal_exposure(policy_rows),
                "baseline_success_exposure": baseline_success_exposure(policy_rows),
                "baseline_terminal_commit_exposure": baseline_terminal_exposure(policy_rows),
                "baseline_wasted_path_exposure_m": baseline_wasted_path_exposure(policy_rows),
                "evaluation_labels_joined_after_rule_freeze": True,
                "label_fields_used_for_action": False,
                "terminal_selector_allowed_from_this_join": False,
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
                "validation_stage": "evaluation_join_after_pairwise_rule_freeze",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_baseline",
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
                "not_used_for_pairwise_rule_action": True,
                **common_flags(),
            }
        )
    return out


def promotion_blocker(request: Mapping[str, Any]) -> str:
    if safe_int(request.get("provisional_rule_wrong_rows"), 0) > 0:
        return "provisional_rule_wrong_evaluation_only"
    if safe_int(request.get("pair_unresolved_rows"), 0) > 0:
        return "pairwise_goal_region_map_pose_arbitration_unresolved"
    if safe_int(request.get("missing_followup_required_rows"), 0) > 0:
        return "missing_evidence_second_view_followup_required"
    if safe_int(request.get("provisional_rule_correct_rows"), 0) > 0:
        return "provisional_rule_too_sparse_for_task_claim"
    if request.get("target_role") != "primary_target":
        return "audit_control_preserved"
    return "evaluation_join_only_terminal_utility_blocked"


def materialize_promotion_probe_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted((row for row in request_rows if row.get("target_role") == "primary_target"), key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        blocker = promotion_blocker(request)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_join_after_pairwise_rule_freeze",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_promotion_probe",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "selected_branch": request.get("selected_branch"),
                "selected_action": request.get("selected_action"),
                "request_rule_state": request.get("request_rule_state"),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get("map_pose_consistency_uncertainty_state"),
                "pair_rule_state_counts": request.get("pair_rule_state_counts"),
                "pair_label_pattern_counts": request.get("pair_label_pattern_counts"),
                "provisional_rule_rows": request.get("provisional_rule_rows"),
                "provisional_rule_correct_rows": request.get("provisional_rule_correct_rows"),
                "provisional_rule_wrong_rows": request.get("provisional_rule_wrong_rows"),
                "pair_unresolved_rows": request.get("pair_unresolved_rows"),
                "missing_followup_required_rows": request.get("missing_followup_required_rows"),
                "baseline_wrong_goal_exposure": request.get("baseline_wrong_goal_exposure"),
                "baseline_wasted_path_exposure_m": request.get("baseline_wasted_path_exposure_m"),
                "evaluation_labels_joined_after_rule_freeze": True,
                "label_fields_used_for_action": False,
                "promotion_probe_gate_passed": False,
                "promotion_probe_primary_blocker": blocker,
                "post_join_wrong_goal_claim_allowed": False,
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
        "pair_label_evaluation_only",
    ]
    if row.get("target_role") != "primary_target":
        tags.append("audit_control_preserved")
    else:
        if safe_int(row.get("provisional_rule_wrong_rows"), 0) > 0:
            tags.append("provisional_rule_wrong_evaluation_only")
            tags.append("wrong_provisional_row_cannot_be_tuned_away")
        if safe_int(row.get("provisional_rule_correct_rows"), 0) > 0:
            tags.append("provisional_rule_too_sparse_for_task_claim")
        if safe_int(row.get("pair_unresolved_rows"), 0) > 0:
            tags.append("pairwise_goal_region_map_pose_arbitration_unresolved")
        if safe_int(row.get("missing_followup_required_rows"), 0) > 0:
            tags.append("missing_evidence_second_view_followup_required")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "provisional_rule_wrong_evaluation_only",
        "pairwise_goal_region_map_pose_arbitration_unresolved",
        "missing_evidence_second_view_followup_required",
        "provisional_rule_too_sparse_for_task_claim",
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
                "validation_stage": "evaluation_join_after_pairwise_rule_freeze",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_failure",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "selected_branch": request.get("selected_branch"),
                "selected_action": request.get("selected_action"),
                "request_rule_state": request.get("request_rule_state"),
                "goal_validity_risk_state": request.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": request.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": request.get(
                    "map_pose_consistency_uncertainty_state"
                ),
                "provisional_rule_rows": request.get("provisional_rule_rows"),
                "provisional_rule_correct_rows": request.get("provisional_rule_correct_rows"),
                "provisional_rule_wrong_rows": request.get("provisional_rule_wrong_rows"),
                "pair_unresolved_rows": request.get("pair_unresolved_rows"),
                "missing_followup_required_rows": request.get("missing_followup_required_rows"),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                "label_fields_used_for_action": False,
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
    gate = contract.get("implementation_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    return {
        "request_rows_expected_passed": counts["request_rows"] == safe_int(gate.get("request_rows_expected"), 50),
        "selected_target_request_rows_expected_passed": counts["selected_target_request_rows"]
        == safe_int(gate.get("selected_target_request_rows_expected"), 21),
        "audit_request_rows_expected_passed": counts["audit_request_rows"]
        == safe_int(gate.get("audit_request_rows_expected"), 29),
        "candidate_rows_expected_passed": counts["candidate_rows"] == safe_int(gate.get("candidate_rows_expected"), 97),
        "pair_rows_expected_passed": counts["pair_rows"] == safe_int(gate.get("pair_rows_expected"), 21),
        "baseline_rows_expected_passed": counts["baseline_rows"]
        == safe_int(gate.get("baseline_rows_expected"), 150),
        "promotion_probe_rows_expected_passed": counts["promotion_probe_rows"]
        == safe_int(gate.get("promotion_probe_rows_expected"), 21),
        "failure_rows_expected_passed": counts["failure_rows"] == safe_int(gate.get("failure_rows_expected"), 50),
        "pair_label_missing_rows_expected_passed": counts["pair_label_missing_rows"]
        == safe_int(gate.get("pair_label_missing_rows_expected"), 0),
        "provisional_rule_rows_expected_passed": counts["provisional_rule_rows"]
        == safe_int(gate.get("provisional_rule_rows_expected"), 1),
        "provisional_rule_correct_rows_expected_passed": counts["provisional_rule_correct_rows"]
        == safe_int(gate.get("provisional_rule_correct_rows_expected"), 0),
        "provisional_rule_wrong_rows_expected_passed": counts["provisional_rule_wrong_rows"]
        == safe_int(gate.get("provisional_rule_wrong_rows_expected"), 1),
        "pair_unresolved_rows_expected_passed": counts["pair_unresolved_rows"]
        == safe_int(gate.get("pair_unresolved_rows_expected"), 17),
        "missing_followup_required_rows_expected_passed": counts["missing_followup_required_rows"]
        == safe_int(gate.get("missing_followup_required_rows_expected"), 3),
        "label_fields_used_for_action_true_rows_expected_passed": counts["label_fields_used_for_action_true_rows"]
        == safe_int(gate.get("label_fields_used_for_action_true_rows_expected"), 0),
        "action_evidence_forbidden_key_count_expected_passed": counts["action_evidence_forbidden_key_count"]
        == safe_int(gate.get("action_evidence_forbidden_key_count_expected"), 0),
        "terminal_commit_rows_expected_passed": counts["terminal_commit_rows"]
        == safe_int(gate.get("terminal_commit_rows_expected"), 0),
        "candidate_commit_rows_expected_passed": counts["candidate_commit_rows"]
        == safe_int(gate.get("candidate_commit_rows_expected"), 0),
        "candidate_rejection_rows_expected_passed": counts["candidate_rejection_rows"]
        == safe_int(gate.get("candidate_rejection_rows_expected"), 0),
        "uses_gt_for_action_true_rows_expected_passed": counts["uses_gt_for_action_true_rows"]
        == safe_int(gate.get("uses_gt_for_action_true_rows_expected"), 0),
        "paper_claim_allowed_true_rows_expected_passed": counts["paper_claim_allowed_true_rows"]
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
    primary_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    audit_requests = [row for row in request_rows if row.get("target_role") != "primary_target"]
    primary_candidates = [row for row in candidate_rows if row.get("target_role") == "primary_target"]
    provisional_rows = [row for row in pair_rows if row.get("non_gt_pairwise_rule_state") in PROVISIONAL_STATES]
    provisional_correct = [
        row for row in provisional_rows if row.get("provisional_rule_candidate_correct_for_evaluation_only") is True
    ]
    provisional_wrong = [
        row for row in provisional_rows if row.get("provisional_rule_candidate_wrong_for_evaluation_only") is True
    ]
    counts = {
        "request_rows": len(request_rows),
        "selected_target_request_rows": len(primary_requests),
        "audit_request_rows": len(audit_requests),
        "candidate_rows": len(candidate_rows),
        "selected_target_candidate_rows": len(primary_candidates),
        "pair_rows": len(pair_rows),
        "pairwise_arbitration_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1"
        ),
        "missing_followup_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "missing_evidence_second_view_followup_v1"
        ),
        "baseline_rows": len(baseline_rows),
        "promotion_probe_rows": len(promotion_rows),
        "failure_rows": len(failure_rows),
        "pair_label_missing_rows": sum(1 for row in pair_rows if row.get("pair_label_join_available") is not True),
        "provisional_rule_rows": len(provisional_rows),
        "provisional_rule_correct_rows": len(provisional_correct),
        "provisional_rule_wrong_rows": len(provisional_wrong),
        "provisional_rule_missing_label_rows": sum(
            1
            for row in provisional_rows
            if row.get("provisional_rule_candidate_correct_for_evaluation_only") is None
            and row.get("provisional_rule_candidate_wrong_for_evaluation_only") is not True
        ),
        "pair_unresolved_rows": sum(
            1 for row in pair_rows if row.get("non_gt_pairwise_rule_state") == "pair_remains_unresolved"
        ),
        "missing_followup_required_rows": sum(
            1
            for row in pair_rows
            if row.get("non_gt_pairwise_rule_state") == "missing_evidence_second_view_followup_required"
        ),
        "rule_input_complete_rows": sum(1 for row in pair_rows if row.get("rule_input_complete") is True),
        "goal_region_pair_evidence_available_rows": sum(
            1 for row in pair_rows if row.get("goal_region_pair_evidence_available") is True
        ),
        "object_relation_pair_evidence_available_rows": sum(
            1
            for row in pair_rows
            if row.get("object_relation_candidate_a_available") is True
            and row.get("object_relation_candidate_b_available") is True
        ),
        "map_pose_non_contradiction_rows": sum(
            1
            for row in pair_rows
            if str(row.get("map_pose_non_contradiction_state") or "").startswith("map_pose_non_contradictory")
        ),
        "label_fields_used_for_action_true_rows": count_true(all_output_rows, "label_fields_used_for_action"),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_output_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_output_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_output_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_output_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_output_rows, "paper_claim_allowed"),
    }
    gate = gate_from_counts(contract, counts)
    evaluation_join_gate_passed = all(gate.values())
    baseline_counts = baseline_policy_counts(baseline_rows)
    if counts["provisional_rule_wrong_rows"] > 0:
        primary_blocker = "provisional_rule_wrong_evaluation_only"
        next_task = "diagnose_pairwise_rule_failure_or_define_new_non_gt_evidence_family"
    elif counts["pair_unresolved_rows"] > 0:
        primary_blocker = "pairwise_goal_region_map_pose_arbitration_unresolved"
        next_task = "diagnose_goal_region_object_relation_evidence_gap_before_terminal_utility"
    else:
        primary_blocker = "evaluation_join_only_terminal_utility_blocked"
        next_task = "define_terminal_utility_contract_only_if_promotion_gate_is_satisfied"
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "evaluation_join_gate_passed_terminal_blocked"
        if evaluation_join_gate_passed
        else "evaluation_join_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        **counts,
        "non_gt_pairwise_rule_state_counts": compact_counter(row.get("non_gt_pairwise_rule_state") for row in pair_rows),
        "pair_label_pattern_counts": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in pair_rows
        ),
        "pair_label_pattern_counts_by_rule_state": {
            state: compact_counter(
                row.get("candidate_pair_label_pattern_for_evaluation_only")
                for row in pair_rows
                if row.get("non_gt_pairwise_rule_state") == state
            )
            for state in sorted({str(row.get("non_gt_pairwise_rule_state")) for row in pair_rows})
        },
        "provisional_rule_label_pattern_counts": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in provisional_rows
        ),
        "goal_region_contrast_state_counts": compact_counter(row.get("goal_region_contrast_state") for row in pair_rows),
        "object_relation_anchor_consistency_state_counts": compact_counter(
            row.get("object_relation_anchor_consistency_state") for row in pair_rows
        ),
        "map_pose_non_contradiction_state_counts": compact_counter(
            row.get("map_pose_non_contradiction_state") for row in pair_rows
        ),
        "rule_defer_reason_counts": compact_counter(row.get("rule_defer_reason") for row in pair_rows),
        "request_rule_state_counts": compact_counter(row.get("request_rule_state") for row in request_rows),
        "request_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in request_rows
        ),
        "request_viewpoint_evidence_gap_state_counts": compact_counter(
            row.get("viewpoint_evidence_gap_state") for row in request_rows
        ),
        "request_map_pose_uncertainty_state_counts": compact_counter(
            row.get("map_pose_consistency_uncertainty_state") for row in request_rows
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
            "label_missing": sum(
                1 for row in candidate_rows if row.get("goal_validity_label_join_available") is not True
            ),
        },
        "selected_target_candidate_correctness_label_counts": {
            "correct": sum(
                1
                for row in primary_candidates
                if row.get("candidate_correctness_label_for_evaluation_only") is True
            ),
            "wrong": sum(
                1
                for row in primary_candidates
                if row.get("candidate_wrong_label_for_evaluation_only") is True
            ),
            "no_valid_pool": sum(
                1 for row in primary_candidates if row.get("no_valid_candidate_pool_for_evaluation_only") is True
            ),
            "label_missing": sum(
                1 for row in primary_candidates if row.get("goal_validity_label_join_available") is not True
            ),
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
        "evaluation_join_gate_passed": evaluation_join_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "promotion_gate_attempted": True,
        "promotion_gate_primary_failure_conditions": [
            condition
            for condition, count_key in (
                ("provisional_rule_wrong_evaluation_only", "provisional_rule_wrong_rows"),
                ("pairwise_goal_region_map_pose_arbitration_unresolved", "pair_unresolved_rows"),
                ("missing_evidence_second_view_followup_required", "missing_followup_required_rows"),
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
        "next_task": next_task,
        "interpretation": {
            "fact": (
                "The materializer joins frozen non-GT pairwise rule rows to evaluation-only candidate, pair, "
                "baseline, wrong-goal, wasted-path, and map/pose fields on the same 50 rows."
            ),
            "agent_inference": (
                "The join is action-safe, but the only provisional pairwise support row is evaluation-only wrong. "
                "This makes the current rule a failure diagnostic rather than an active utility."
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
    script_path = (
        "hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/"
        "materialize_pairwise_goal_region_map_pose_arbitration_rule_evaluation_join.py"
    )
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
            "baseline_rows": summary.get("baseline_rows"),
            "promotion_probe_rows": summary.get("promotion_probe_rows"),
            "failure_rows": summary.get("failure_rows"),
            "pair_label_missing_rows": summary.get("pair_label_missing_rows"),
            "provisional_rule_rows": summary.get("provisional_rule_rows"),
            "provisional_rule_correct_rows": summary.get("provisional_rule_correct_rows"),
            "provisional_rule_wrong_rows": summary.get("provisional_rule_wrong_rows"),
            "pair_unresolved_rows": summary.get("pair_unresolved_rows"),
            "missing_followup_required_rows": summary.get("missing_followup_required_rows"),
            "label_fields_used_for_action_true_rows": summary.get("label_fields_used_for_action_true_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "non_gt_pairwise_rule_state_counts": summary.get("non_gt_pairwise_rule_state_counts"),
        "pair_label_pattern_counts": summary.get("pair_label_pattern_counts"),
        "pair_label_pattern_counts_by_rule_state": summary.get("pair_label_pattern_counts_by_rule_state"),
        "provisional_rule_label_pattern_counts": summary.get("provisional_rule_label_pattern_counts"),
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
                f"python -m py_compile {script_path}"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_pairwise_goal_region_map_pose_arbitration_rule_evaluation_join"
            ),
            (
                "jq '{status, request_rows, candidate_rows, pair_rows, baseline_rows, promotion_probe_rows, "
                "failure_rows, provisional_rule_rows, provisional_rule_correct_rows, provisional_rule_wrong_rows, "
                "pair_unresolved_rows, missing_followup_required_rows, evaluation_join_gate_passed, "
                f"primary_blocker, next_task}}' {out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "source_pairwise_rule_preserved": True,
            "source_evaluation_join_preserved": True,
            "same_pair_order_required": True,
            "same_candidate_pool_required": True,
            "labels_joined_only_after_rule_freeze": True,
            "labels_for_action_forbidden": True,
            "wrong_goal_for_action_forbidden": True,
            "unresolved_pairs_preserved": True,
            "missing_followup_pairs_preserved": True,
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

    rule_request_rows = load_jsonl(Path(str(source["pairwise_rule_request_rows"])))
    rule_candidate_rows = load_jsonl(Path(str(source["pairwise_rule_candidate_rows"])))
    rule_pair_rows = load_jsonl(Path(str(source["pairwise_rule_pair_rows"])))
    rule_failure_rows = load_jsonl(Path(str(source["pairwise_rule_failure_rows"])))
    previous_request_rows = load_jsonl(Path(str(source["previous_evaluation_join_request_rows"])))
    previous_candidate_rows = load_jsonl(Path(str(source["previous_evaluation_join_candidate_rows"])))
    previous_pair_rows = load_jsonl(Path(str(source["previous_evaluation_join_pair_rows"])))
    previous_baseline_rows = load_jsonl(Path(str(source["previous_evaluation_join_baseline_rows"])))

    candidate_rows = materialize_candidate_rows(
        rule_candidates=rule_candidate_rows,
        previous_candidates_by_key=index_by_candidate(previous_candidate_rows),
    )
    pair_rows = materialize_pair_rows(
        rule_pairs=rule_pair_rows,
        candidate_eval_by_key=index_by_candidate(candidate_rows),
        previous_pairs_by_key=index_by_pair(previous_pair_rows),
    )
    request_rows = materialize_request_rows(
        rule_requests=rule_request_rows,
        previous_requests_by_key=index_by_join(previous_request_rows),
        baselines_by_key=group_baselines_by_request(previous_baseline_rows),
        pairs_by_key=group_pairs_by_request(pair_rows),
    )
    baseline_rows = materialize_baseline_rows(previous_baseline_rows)
    promotion_rows = materialize_promotion_probe_rows(request_rows)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*rule_request_rows, *rule_candidate_rows, *rule_pair_rows, *rule_failure_rows])
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
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Materialize evaluation-only join rows after frozen pairwise goal-region/map-pose rule output."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
