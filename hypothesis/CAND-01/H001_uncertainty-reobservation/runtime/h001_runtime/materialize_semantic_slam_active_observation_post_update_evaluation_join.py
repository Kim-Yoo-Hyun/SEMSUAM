import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_active_observation_post_update_evaluation_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_active_observation_post_update_evaluation_join_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_semantic_slam_active_observation_post_update_evaluation_join_v1"
)

OUTPUT_FILES = {
    "request_rows": "active_observation_post_update_evaluation_join_request_rows.jsonl",
    "selected_candidate_rows": "active_observation_post_update_evaluation_join_selected_candidate_rows.jsonl",
    "candidate_state_rows": "active_observation_post_update_evaluation_join_candidate_state_rows.jsonl",
    "baseline_rows": "active_observation_post_update_evaluation_join_baseline_rows.jsonl",
    "failure_rows": "active_observation_post_update_evaluation_join_failure_rows.jsonl",
    "summary": "active_observation_post_update_evaluation_join_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")

FORBIDDEN_ACTION_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "correct_candidate_count",
    "correctness_label",
    "evaluation_candidate_summary",
    "evaluation_label",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_variant_outcomes",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "no_valid_candidate_pool",
    "oracle_action",
    "shortest_path_distance",
    "success_commit_proxy",
    "task_proxy_commit_evaluable",
    "wasted_path_proxy_m",
    "wrong_goal_visit_proxy",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


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


def ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def clip(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(value, high))


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def join_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return tuple(str(source.get(key) or row.get(key) or "") for key in JOIN_KEYS)  # type: ignore[return-value]


def candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    return (*join_key(row), str(row.get("candidate_id") or ""))


def policy_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("policy_name") or row.get("policy_name") or ""))


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def index_one(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {join_key(row): row for row in rows}


def index_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def index_policy_rows(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {policy_key(row): row for row in rows}


def group_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    groups: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[join_key(row)].append(row)
    return dict(groups)


def scan_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def eval_flags() -> Dict[str, Any]:
    return {
        "evaluation_only_task_proxy_join": True,
        "label_usage": "evaluation_only_after_post_update_action_freeze",
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def selected_label_counts(row: Mapping[str, Any]) -> Dict[str, int]:
    counts = row.get("selected_candidate_label_counts")
    counts = counts if isinstance(counts, Mapping) else {}
    no_valid_rows = safe_int(counts.get("selected_candidate_rows"), 0) if counts.get("no_valid_request_pool") is True else 0
    return {
        "selected_candidate_rows": safe_int(counts.get("selected_candidate_rows"), 0),
        "label_join_available_rows": safe_int(counts.get("label_join_available_rows"), 0),
        "label_missing_rows": safe_int(counts.get("label_missing_rows"), 0),
        "correct_rows": safe_int(counts.get("correct_rows"), 0),
        "wrong_rows": safe_int(counts.get("wrong_rows"), 0),
        "no_valid_rows": no_valid_rows,
        "wrong_or_no_valid_risk_rows": safe_int(counts.get("wrong_or_no_valid_risk_rows"), 0),
    }


def goal_validity_request_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    counts = selected_label_counts(row)
    selected_count = max(counts["selected_candidate_rows"], safe_int(row.get("selected_candidate_count"), 0), 1)
    no_valid = row.get("no_valid_candidate_pool") is True
    wrong_or_no_valid = counts["wrong_or_no_valid_risk_rows"]
    correct = counts["correct_rows"]
    label_available = row.get("request_label_join_available") is True and counts["label_missing_rows"] == 0
    if not label_available:
        state = "goal_validity_label_missing"
    elif no_valid:
        state = "no_valid_candidate_pool_risk"
    elif wrong_or_no_valid > 0 and correct > 0:
        state = "mixed_goal_validity_risk"
    elif wrong_or_no_valid > 0:
        state = "wrong_goal_candidate_risk"
    elif correct > 0:
        state = "clean_correct_candidate_support"
    else:
        state = "goal_validity_unknown"
    return {
        "goal_validity_risk_state": state,
        "goal_validity_risk_proxy": round(ratio(float(wrong_or_no_valid), float(selected_count)), 6),
        "goal_validity_label_join_available": label_available,
        "selected_candidate_clean_correct_count": correct,
        "selected_candidate_wrong_or_no_valid_count": wrong_or_no_valid,
        "no_valid_pool_proxy": no_valid,
    }


def goal_validity_candidate_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    label_available = row.get("candidate_label_join_available") is True
    no_valid = row.get("no_valid_candidate_pool") is True
    is_correct = row.get("candidate_correctness_label") is True
    is_wrong = row.get("candidate_wrong_label") is True
    if not label_available:
        state = "goal_validity_label_missing"
        risk = None
    elif no_valid:
        state = "no_valid_candidate_pool_risk"
        risk = 1.0
    elif is_wrong:
        state = "wrong_goal_candidate_risk"
        risk = 1.0
    elif is_correct:
        state = "clean_correct_candidate_support"
        risk = 0.0
    else:
        state = "goal_validity_unknown"
        risk = None
    return {
        "goal_validity_risk_state": state,
        "goal_validity_risk_proxy": risk,
        "goal_validity_label_join_available": label_available,
        "selected_candidate_clean_correct_count": 1 if is_correct else 0,
        "selected_candidate_wrong_or_no_valid_count": 1 if is_wrong or no_valid else 0,
        "no_valid_pool_proxy": no_valid,
        "candidate_correctness_label": row.get("candidate_correctness_label") if label_available else None,
        "candidate_wrong_label": row.get("candidate_wrong_label") if label_available else None,
    }


def evidence_delta(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("evidence_delta")
    return value if isinstance(value, Mapping) else {}


def net_evidence_delta(row: Mapping[str, Any]) -> Optional[float]:
    return safe_float(evidence_delta(row).get("net_evidence_delta_proxy"))


def viewpoint_gap_payload(row: Mapping[str, Any]) -> Dict[str, Any]:
    delta = evidence_delta(row)
    net = safe_float(delta.get("net_evidence_delta_proxy"))
    if net is None:
        request_delta = row.get("request_evidence_delta")
        if isinstance(request_delta, Mapping):
            net = safe_float(request_delta.get("mean_net_evidence_delta_proxy"))
    gap = None if net is None else round(clip(1.0 - net), 6)
    state = str(row.get("post_observation_state") or row.get("post_update_request_state") or "")
    if state == "needs_goal_validity_confirmation":
        gap_state = "viewpoint_gap_reduced_goal_validity_unresolved"
    elif state == "ambiguity_reduced":
        gap_state = "viewpoint_gap_reduced_ambiguity_reduced"
    elif state == "support_acquired":
        gap_state = "viewpoint_gap_reduced_support_acquired"
    elif state == "defer_after_update":
        gap_state = "viewpoint_gap_unobserved_carry_forward"
    else:
        gap_state = "viewpoint_gap_partial_or_unknown"
    evidence = row.get("observation_evidence")
    evidence = evidence if isinstance(evidence, Mapping) else {}
    return {
        "viewpoint_evidence_gap_state": gap_state,
        "viewpoint_evidence_gap_proxy": gap,
        "evidence_delta_available": row.get("evidence_delta_available") is True or bool(delta.get("evidence_delta_available") is True),
        "reobserve_travel_cost_m": safe_float(
            evidence.get("target_distance_mean_m"),
            safe_float(delta.get("observation_cost_proxy"), 0.0),
        ),
    }


def mean_selected_travel_cost(rows: Sequence[Mapping[str, Any]]) -> Optional[float]:
    values = [safe_float(row.get("target_distance_mean_m")) for row in rows]
    values = [value for value in values if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def map_delta_payload(
    *,
    map_row: Optional[Mapping[str, Any]],
    outcome_row: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    outcome_row = outcome_row or {}
    map_row = map_row or {}
    map_side_delta = safe_float(outcome_row.get("map_side_delta"))
    pose_delta = safe_float(outcome_row.get("pose_graph_connectivity_delta"))
    consistency_delta = safe_float(outcome_row.get("map_pose_consistency_delta"))
    if map_side_delta is None:
        largest = safe_float(map_row.get("pose_graph_largest_component_fraction"), 0.0) or 0.0
        consistency = safe_float(map_row.get("projection_visible_fraction"), 0.0) or 0.0
        pose_delta = largest
        consistency_delta = consistency
        map_side_delta = clip(0.60 * pose_delta + 0.40 * consistency_delta)
    uncertainty = round(clip(1.0 - (map_side_delta or 0.0)), 6)
    if map_row.get("strict_candidate_map_pose_ready") is True or map_row.get("pose_graph_proxy_ready") is True:
        state = "map_pose_ready_uncertainty_measured"
    elif map_row:
        state = "map_pose_partial_uncertainty_measured"
    else:
        state = "map_pose_evidence_missing"
    return {
        "map_pose_consistency_uncertainty_state": state,
        "map_pose_consistency_uncertainty_proxy": uncertainty,
        "pose_graph_connectivity_delta": pose_delta,
        "map_pose_consistency_delta": consistency_delta,
        "map_side_delta": map_side_delta,
        "map_task_alignment": bool(outcome_row.get("map_task_alignment") is True),
    }


def common_request_row(
    *,
    row_type: str,
    key: Tuple[str, str, str, str, str],
    selected_observation_action: Any,
    post_update_request_state: Any,
) -> Dict[str, Any]:
    payload = key_payload(key)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "semantic_slam_active_observation_post_update_evaluation_join_after_action_freeze",
        "row_type": row_type,
        "join_key": payload,
        **payload,
        "selected_observation_action": selected_observation_action,
        "post_update_request_state": post_update_request_state,
        **eval_flags(),
    }


def materialize_request_rows(
    *,
    post_requests: Sequence[Mapping[str, Any]],
    task_requests_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    selected_task_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
    map_requests_by_key: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    outcome_by_policy_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    baselines_by_policy_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for post in sorted(post_requests, key=join_key):
        key = join_key(post)
        task = task_requests_by_key.get(key) or {}
        selected_task_rows = selected_task_by_key.get(key) or []
        slam_outcome = outcome_by_policy_key.get((*key, "SLAMOnlyRich_current"))
        slam_baseline = baselines_by_policy_key.get((*key, "SLAMOnlyRich_current")) or {}
        row = common_request_row(
            row_type="active_observation_post_update_evaluation_join_request",
            key=key,
            selected_observation_action=post.get("selected_observation_action"),
            post_update_request_state=post.get("post_update_request_state"),
        )
        row.update(
            {
                "selected_candidate_count": safe_int(post.get("selected_candidate_count"), 0),
                "selected_candidate_ids": post.get("selected_candidate_ids") or [],
                "pre_update_request_risk_tags": post.get("pre_update_request_risk_tags") or task.get("request_risk_tags"),
                "request_evidence_delta": post.get("request_evidence_delta"),
                "active_observation_action_frozen": True,
                "wrong_goal_visit_proxy": None,
                "wrong_goal_visit_proxy_note": "nonterminal_active_reobservation_no_commit",
                "wrong_goal_visit_proxy_delta_vs_no_reobserve": None,
                "wrong_goal_visit_proxy_delta_vs_semantic_only": None,
                "wasted_path_proxy_m": mean_selected_travel_cost(selected_task_rows),
                "wasted_path_proxy_delta_vs_no_reobserve_m": None,
                "wasted_path_proxy_delta_vs_semantic_only_m": None,
                "baseline_slam_only_terminal_commit_proxy": slam_baseline.get("terminal_commit_proxy"),
                "baseline_slam_only_wrong_goal_visit_proxy": slam_baseline.get("wrong_goal_visit_proxy"),
                "baseline_slam_only_wasted_path_proxy_m": slam_baseline.get("wasted_path_proxy_m"),
            }
        )
        row.update(goal_validity_request_payload(task))
        row.update(viewpoint_gap_payload(post))
        row["reobserve_travel_cost_m"] = row["wasted_path_proxy_m"]
        row.update(map_delta_payload(map_row=map_requests_by_key.get(key), outcome_row=slam_outcome))
        out.append(row)
    return out


def materialize_selected_candidate_rows(
    *,
    post_selected: Sequence[Mapping[str, Any]],
    task_selected_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    map_candidates_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    outcome_by_policy_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for post in sorted(post_selected, key=candidate_key):
        key = join_key(post)
        ckey = candidate_key(post)
        payload = key_payload(key)
        task = task_selected_by_candidate.get(ckey) or {}
        map_row = map_candidates_by_candidate.get(ckey)
        slam_outcome = outcome_by_policy_key.get((*key, "SLAMOnlyRich_current"))
        row = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "semantic_slam_active_observation_post_update_evaluation_join_after_action_freeze",
            "row_type": "active_observation_post_update_evaluation_join_selected_candidate",
            "join_key": {**payload, "candidate_id": candidate_id(post)},
            **payload,
            "candidate_id": candidate_id(post),
            "selected_observation_action": post.get("selected_observation_action"),
            "post_update_request_state": None,
            "post_observation_state": post.get("post_observation_state"),
            "pre_observation_state": post.get("pre_observation_state"),
            "observation_evidence": post.get("observation_evidence"),
            "evidence_delta": post.get("evidence_delta"),
            "active_observation_action_frozen": True,
            "wrong_goal_visit_proxy": None,
            "wrong_goal_visit_proxy_note": "selected_candidate_is_not_terminal_commit",
            "wrong_goal_visit_proxy_delta_vs_no_reobserve": None,
            "wrong_goal_visit_proxy_delta_vs_semantic_only": None,
            "wasted_path_proxy_m": safe_float(task.get("target_distance_mean_m")),
            "wasted_path_proxy_delta_vs_no_reobserve_m": None,
            "wasted_path_proxy_delta_vs_semantic_only_m": None,
            **eval_flags(),
        }
        row.update(goal_validity_candidate_payload(task))
        row.update(viewpoint_gap_payload(post))
        row["reobserve_travel_cost_m"] = safe_float(task.get("target_distance_mean_m"), row.get("reobserve_travel_cost_m"))
        row.update(map_delta_payload(map_row=map_row, outcome_row=slam_outcome))
        out.append(row)
    return out


def materialize_candidate_state_rows(
    *,
    post_candidates: Sequence[Mapping[str, Any]],
    task_priority_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    map_candidates_by_candidate: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    outcome_by_policy_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for post in sorted(post_candidates, key=candidate_key):
        key = join_key(post)
        ckey = candidate_key(post)
        payload = key_payload(key)
        task = task_priority_by_candidate.get(ckey) or {}
        map_row = map_candidates_by_candidate.get(ckey)
        slam_outcome = outcome_by_policy_key.get((*key, "SLAMOnlyRich_current"))
        row = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "semantic_slam_active_observation_post_update_evaluation_join_after_action_freeze",
            "row_type": "active_observation_post_update_evaluation_join_candidate_state",
            "join_key": {**payload, "candidate_id": candidate_id(post)},
            **payload,
            "candidate_id": candidate_id(post),
            "selected_observation_action": post.get("selected_observation_action"),
            "post_update_request_state": None,
            "post_observation_state": post.get("post_observation_state"),
            "pre_observation_state": post.get("pre_observation_state"),
            "selected_for_observation_update": post.get("selected_for_observation_update") is True,
            "observation_evidence": post.get("observation_evidence"),
            "evidence_delta": post.get("evidence_delta"),
            "active_observation_action_frozen": True,
            "wrong_goal_visit_proxy": None,
            "wrong_goal_visit_proxy_note": "candidate_state_is_not_terminal_commit",
            "wrong_goal_visit_proxy_delta_vs_no_reobserve": None,
            "wrong_goal_visit_proxy_delta_vs_semantic_only": None,
            "wasted_path_proxy_m": safe_float(task.get("target_distance_mean_m")),
            "wasted_path_proxy_delta_vs_no_reobserve_m": None,
            "wasted_path_proxy_delta_vs_semantic_only_m": None,
            **eval_flags(),
        }
        row.update(goal_validity_candidate_payload(task))
        row.update(viewpoint_gap_payload(post))
        row["reobserve_travel_cost_m"] = safe_float(task.get("target_distance_mean_m"), row.get("reobserve_travel_cost_m"))
        row.update(map_delta_payload(map_row=map_row, outcome_row=slam_outcome))
        out.append(row)
    return out


def bool_delta(value: Any, reference: Any) -> Optional[int]:
    if value is None or reference is None:
        return None
    return int(bool(value)) - int(bool(reference))


def float_delta(value: Any, reference: Any) -> Optional[float]:
    left = safe_float(value)
    right = safe_float(reference)
    if left is None or right is None:
        return None
    return left - right


def materialize_baseline_rows(
    *,
    baseline_rows: Sequence[Mapping[str, Any]],
    outcome_by_policy_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    baselines_by_policy_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for base in sorted(baseline_rows, key=policy_key):
        key = join_key(base)
        pkey = policy_key(base)
        policy_name = str(base.get("policy_name") or "")
        no_reobserve = baselines_by_policy_key.get((*key, "NoReobserveReference")) or {}
        semantic = baselines_by_policy_key.get((*key, "SemanticOnly")) or {}
        outcome = outcome_by_policy_key.get(pkey)
        payload = key_payload(key)
        row = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "semantic_slam_active_observation_post_update_evaluation_join_after_action_freeze",
            "row_type": "active_observation_post_update_evaluation_join_baseline",
            "join_key": {**payload, "policy_name": policy_name},
            **payload,
            "policy_name": policy_name,
            "selector_id": base.get("selector_id"),
            "selector_action": base.get("selector_action"),
            "selector_source": base.get("selector_source"),
            "selector_missing": base.get("selector_missing") is True,
            "policy_selected_candidate_id": base.get("policy_selected_candidate_id"),
            "selected_observation_action": None,
            "post_update_request_state": "baseline_policy_context_not_post_update_action",
            "goal_validity_risk_state": "baseline_commit_wrong_goal" if base.get("wrong_goal_visit_proxy") is True else "baseline_commit_not_wrong_goal",
            "goal_validity_risk_proxy": 1.0 if base.get("wrong_goal_visit_proxy") is True else 0.0,
            "goal_validity_label_join_available": base.get("selected_candidate_label_join_available") is True,
            "selected_candidate_clean_correct_count": 1 if base.get("selected_candidate_correctness_label") is True else 0,
            "selected_candidate_wrong_or_no_valid_count": 1
            if base.get("selected_candidate_wrong_label") is True or base.get("no_valid_commit_proxy") is True
            else 0,
            "no_valid_pool_proxy": base.get("no_valid_commit_proxy") is True,
            "viewpoint_evidence_gap_state": "baseline_policy_no_active_post_update_gap",
            "viewpoint_evidence_gap_proxy": None,
            "evidence_delta_available": False,
            "reobserve_travel_cost_m": 0.0,
            "terminal_commit_proxy": base.get("terminal_commit_proxy"),
            "success_commit_proxy": base.get("success_commit_proxy"),
            "wrong_goal_visit_proxy": base.get("wrong_goal_visit_proxy"),
            "wrong_goal_visit_proxy_delta_vs_no_reobserve": bool_delta(
                base.get("wrong_goal_visit_proxy"),
                no_reobserve.get("wrong_goal_visit_proxy"),
            ),
            "wrong_goal_visit_proxy_delta_vs_semantic_only": bool_delta(
                base.get("wrong_goal_visit_proxy"),
                semantic.get("wrong_goal_visit_proxy"),
            ),
            "wasted_path_proxy_m": base.get("wasted_path_proxy_m"),
            "wasted_path_proxy_delta_vs_no_reobserve_m": float_delta(
                base.get("wasted_path_proxy_m"),
                no_reobserve.get("wasted_path_proxy_m"),
            ),
            "wasted_path_proxy_delta_vs_semantic_only_m": float_delta(
                base.get("wasted_path_proxy_m"),
                semantic.get("wasted_path_proxy_m"),
            ),
            "task_proxy_decision_evaluable": base.get("task_proxy_decision_evaluable") is True,
            "task_proxy_commit_evaluable": base.get("task_proxy_commit_evaluable") is True,
            "map_task_alignment": base.get("map_task_alignment_proxy") is True,
            "evaluation_only_baseline_context": True,
            **eval_flags(),
        }
        row.update(map_delta_payload(map_row=None, outcome_row=outcome))
        row["map_task_alignment"] = base.get("map_task_alignment_proxy") is True
        out.append(row)
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "post_update_evaluation_join_only",
        "active_reobservation_not_terminal_utility",
        "semantic_slam_centered_task_map_evidence_required",
    ]
    if row.get("goal_validity_label_join_available") is not True:
        tags.append("goal_validity_label_join_missing")
    if row.get("goal_validity_risk_proxy") not in (None, 0, 0.0):
        tags.append("goal_validity_risk_present")
    if row.get("post_update_request_state") == "needs_goal_validity_confirmation":
        tags.append("viewpoint_gap_reduced_but_goal_validity_unresolved")
    if row.get("map_side_delta") in (None, 0, 0.0):
        tags.append("map_pose_delta_missing")
    if row.get("wrong_goal_visit_proxy") is None:
        tags.append("wrong_goal_proxy_missing_for_nonterminal_active_action")
    if row.get("wasted_path_proxy_m") is None:
        tags.append("wasted_path_proxy_missing")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "goal_validity_label_join_missing",
        "wrong_goal_proxy_missing_for_nonterminal_active_action",
        "viewpoint_gap_reduced_but_goal_validity_unresolved",
        "goal_validity_risk_present",
        "map_pose_delta_missing",
    ):
        if tag in tags:
            return tag
    return "post_update_evaluation_join_only"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in request_rows:
        key = join_key(row)
        tags = failure_tags(row)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "semantic_slam_active_observation_post_update_evaluation_join_after_action_freeze",
                "row_type": "active_observation_post_update_evaluation_join_failure",
                "join_key": key_payload(key),
                **key_payload(key),
                "selected_observation_action": row.get("selected_observation_action"),
                "post_update_request_state": row.get("post_update_request_state"),
                "goal_validity_risk_state": row.get("goal_validity_risk_state"),
                "goal_validity_risk_proxy": row.get("goal_validity_risk_proxy"),
                "viewpoint_evidence_gap_state": row.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": row.get("map_pose_consistency_uncertainty_state"),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                "wrong_goal_visit_proxy": row.get("wrong_goal_visit_proxy"),
                "wasted_path_proxy_m": row.get("wasted_path_proxy_m"),
                "pose_graph_connectivity_delta": row.get("pose_graph_connectivity_delta"),
                "map_pose_consistency_delta": row.get("map_pose_consistency_delta"),
                "map_side_delta": row.get("map_side_delta"),
                "map_task_alignment": row.get("map_task_alignment"),
                **eval_flags(),
            }
        )
    return out


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    selected_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    minimum = contract.get("minimum_success_gate_for_future_implementation")
    minimum = minimum if isinstance(minimum, Mapping) else {}
    all_rows = [*request_rows, *selected_rows, *candidate_rows, *baseline_rows, *failure_rows]
    request_label_missing = sum(1 for row in request_rows if row.get("goal_validity_label_join_available") is not True)
    selected_label_missing = sum(1 for row in selected_rows if row.get("goal_validity_label_join_available") is not True)
    goal_validity_rows = sum(1 for row in request_rows if row.get("goal_validity_label_join_available") is True)
    viewpoint_rows = sum(1 for row in request_rows if row.get("viewpoint_evidence_gap_proxy") is not None)
    map_pose_rows = sum(1 for row in request_rows if row.get("map_side_delta") is not None)
    wrong_goal_evaluable = sum(1 for row in baseline_rows if row.get("wrong_goal_visit_proxy") is not None)
    wasted_evaluable = sum(1 for row in baseline_rows if row.get("wasted_path_proxy_m") is not None)
    map_delta_evaluable = sum(1 for row in request_rows if row.get("map_side_delta") is not None)
    actual_counts = {
        "request_rows": len(request_rows),
        "selected_candidate_rows": len(selected_rows),
        "candidate_state_rows": len(candidate_rows),
        "baseline_rows": len(baseline_rows),
        "failure_rows": len(failure_rows),
        "request_label_missing_rows": request_label_missing,
        "selected_candidate_label_missing_rows": selected_label_missing,
        "goal_validity_risk_join_available_rows": goal_validity_rows,
        "viewpoint_evidence_gap_available_rows": viewpoint_rows,
        "map_pose_consistency_join_available_rows": map_pose_rows,
        "wrong_goal_proxy_evaluable_rows": wrong_goal_evaluable,
        "wasted_path_proxy_evaluable_rows": wasted_evaluable,
        "map_pose_delta_evaluable_rows": map_delta_evaluable,
        "terminal_commit_rows": count_true(all_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_rows, "paper_claim_allowed"),
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
    }
    gate = {
        "request_rows_passed": actual_counts["request_rows"] == safe_int(minimum.get("request_rows"), 50),
        "selected_candidate_rows_passed": actual_counts["selected_candidate_rows"]
        == safe_int(minimum.get("selected_candidate_rows"), 97),
        "candidate_state_rows_passed": actual_counts["candidate_state_rows"]
        == safe_int(minimum.get("candidate_state_rows"), 232),
        "baseline_rows_passed": actual_counts["baseline_rows"] == safe_int(minimum.get("baseline_rows"), 150),
        "failure_rows_minimum_passed": actual_counts["failure_rows"] >= safe_int(minimum.get("failure_rows_minimum"), 50),
        "request_label_missing_rows_passed": request_label_missing <= safe_int(minimum.get("request_label_missing_rows"), 0),
        "selected_candidate_label_missing_rows_passed": selected_label_missing
        <= safe_int(minimum.get("selected_candidate_label_missing_rows"), 0),
        "goal_validity_risk_join_available_rows_passed": goal_validity_rows
        >= safe_int(minimum.get("goal_validity_risk_join_available_rows_min"), 50),
        "viewpoint_evidence_gap_available_rows_passed": viewpoint_rows
        >= safe_int(minimum.get("viewpoint_evidence_gap_available_rows_min"), 50),
        "map_pose_consistency_join_available_rows_passed": map_pose_rows
        >= safe_int(minimum.get("map_pose_consistency_join_available_rows_min"), 50),
        "wrong_goal_proxy_evaluable_rows_passed": wrong_goal_evaluable
        >= safe_int(minimum.get("wrong_goal_proxy_evaluable_rows_min"), 35),
        "wasted_path_proxy_evaluable_rows_passed": wasted_evaluable
        >= safe_int(minimum.get("wasted_path_proxy_evaluable_rows_min"), 35),
        "map_pose_delta_evaluable_rows_passed": map_delta_evaluable
        >= safe_int(minimum.get("map_pose_delta_evaluable_rows_min"), 50),
        "action_evidence_forbidden_key_count_passed": len(action_forbidden_keys)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": actual_counts["terminal_commit_rows"] == 0,
        "candidate_commit_rows_passed": actual_counts["candidate_commit_rows"] == 0,
        "candidate_rejection_rows_passed": actual_counts["candidate_rejection_rows"] == 0,
        "uses_gt_for_action_passed": actual_counts["uses_gt_for_action_true_rows"] == 0,
        "paper_claim_allowed_passed": actual_counts["paper_claim_allowed_true_rows"] == 0,
    }
    gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "post_update_evaluation_join_gate_passed_promotion_blocked"
        if gate_passed
        else "post_update_evaluation_join_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        "request_rows": actual_counts["request_rows"],
        "selected_candidate_rows": actual_counts["selected_candidate_rows"],
        "candidate_state_rows": actual_counts["candidate_state_rows"],
        "baseline_rows": actual_counts["baseline_rows"],
        "failure_rows": actual_counts["failure_rows"],
        "goal_validity_risk_join_available_rows": goal_validity_rows,
        "viewpoint_evidence_gap_available_rows": viewpoint_rows,
        "map_pose_consistency_join_available_rows": map_pose_rows,
        "wrong_goal_proxy_evaluable_rows": wrong_goal_evaluable,
        "wasted_path_proxy_evaluable_rows": wasted_evaluable,
        "map_pose_delta_evaluable_rows": map_delta_evaluable,
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
        "terminal_commit_rows": actual_counts["terminal_commit_rows"],
        "candidate_commit_rows": actual_counts["candidate_commit_rows"],
        "candidate_rejection_rows": actual_counts["candidate_rejection_rows"],
        "uses_gt_for_action_true_rows": actual_counts["uses_gt_for_action_true_rows"],
        "post_update_evaluation_join_gate_passed": gate_passed,
        "promotion_gate_after_evaluation_join_passed": False,
        "primary_blocker": "evaluation_join_only_nonterminal_goal_validity_arbitration_required",
        "next_task": "freeze_semantic_slam_centered_task_map_evidence_contract",
        "paper_claim_allowed": False,
        "actual_counts": actual_counts,
        "post_update_evaluation_join_gate": gate,
        "request_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in request_rows
        ),
        "request_viewpoint_evidence_gap_state_counts": compact_counter(
            row.get("viewpoint_evidence_gap_state") for row in request_rows
        ),
        "request_map_pose_uncertainty_state_counts": compact_counter(
            row.get("map_pose_consistency_uncertainty_state") for row in request_rows
        ),
        "selected_candidate_goal_validity_risk_state_counts": compact_counter(
            row.get("goal_validity_risk_state") for row in selected_rows
        ),
        "baseline_policy_counts": {
            policy: {
                "rows": sum(1 for row in baseline_rows if row.get("policy_name") == policy),
                "terminal_commit_proxy_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("terminal_commit_proxy") is True
                ),
                "success_commit_proxy_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("success_commit_proxy") is True
                ),
                "wrong_goal_visit_proxy_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("wrong_goal_visit_proxy") is True
                ),
                "wasted_path_proxy_m_stats": number_stats(
                    row.get("wasted_path_proxy_m") for row in baseline_rows if row.get("policy_name") == policy
                ),
                "map_task_alignment_rows": sum(
                    1
                    for row in baseline_rows
                    if row.get("policy_name") == policy and row.get("map_task_alignment") is True
                ),
            }
            for policy in POLICIES
        },
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "promotion_gate_after_evaluation_join": {
            "post_update_evaluation_join_gate_must_pass": gate_passed,
            "terminal_utility_validation_allowed": False,
            "formula_revision_allowed": False,
            "first_eval_rerun_allowed": False,
            "policy_scale_comparison_allowed": False,
            "step_4_5_promotion_allowed": False,
            "non_gt_goal_validity_arbitration_required": True,
        },
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "interpretation": {
            "fact": (
                "Frozen post-update active-observation rows are joined to evaluation-only task proxies, "
                "baseline task proxies, and candidate-relative map/pose evidence."
            ),
            "agent_inference": (
                "The artifact now exposes goal-validity risk, viewpoint evidence gap, and map/pose consistency "
                "uncertainty on the same rows, but it is still measurement plumbing rather than terminal utility."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM complementarity, SLAM benefit, formula revision, "
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
        "ok": bool(summary.get("post_update_evaluation_join_gate_passed") is True),
        "verified_artifact": str(contract_path),
        "status": summary.get("status"),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": summary.get("actual_counts"),
        "output_state_counts": {
            "request_goal_validity_risk_state_counts": summary.get("request_goal_validity_risk_state_counts"),
            "request_viewpoint_evidence_gap_state_counts": summary.get("request_viewpoint_evidence_gap_state_counts"),
            "request_map_pose_uncertainty_state_counts": summary.get("request_map_pose_uncertainty_state_counts"),
            "selected_candidate_goal_validity_risk_state_counts": summary.get(
                "selected_candidate_goal_validity_risk_state_counts"
            ),
        },
        "baseline_policy_counts": summary.get("baseline_policy_counts"),
        "post_update_evaluation_join_gate_passed": summary.get("post_update_evaluation_join_gate_passed"),
        "promotion_gate_after_evaluation_join_passed": summary.get("promotion_gate_after_evaluation_join_passed"),
        "primary_blocker": summary.get("primary_blocker"),
        "next_task": summary.get("next_task"),
        "paper_claim_allowed": summary.get("paper_claim_allowed"),
        "verified_output_files": {
            name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()
        },
        "verification_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m py_compile "
                "hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/"
                "materialize_semantic_slam_active_observation_post_update_evaluation_join.py"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime."
                "materialize_semantic_slam_active_observation_post_update_evaluation_join"
            ),
            (
                "jq '{status, actual_counts, post_update_evaluation_join_gate_passed, "
                "promotion_gate_after_evaluation_join_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "post_update_rows_frozen_before_label_join": True,
            "evaluation_join_allowed_only_after_freeze": True,
            "semantic_slam_centered_task_map_schema": True,
            "objectnav_wrong_goal_is_task_failure_surface": True,
            "terminal_commit_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "formula_revision_allowed": False,
            "terminal_utility_validation_allowed": False,
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

    post_request_rows = load_jsonl(Path(str(source["post_update_request_rows"])))
    post_selected_rows = load_jsonl(Path(str(source["post_update_selected_candidate_rows"])))
    post_candidate_rows = load_jsonl(Path(str(source["post_update_candidate_state_rows"])))
    task_request_rows = load_jsonl(Path(str(source["active_observation_task_proxy_request_rows"])))
    task_selected_rows = load_jsonl(Path(str(source["active_observation_task_proxy_selected_candidate_rows"])))
    task_priority_rows = load_jsonl(Path(str(source["active_observation_task_proxy_priority_rows"])))
    task_baseline_rows = load_jsonl(Path(str(source["active_observation_task_proxy_baseline_rows"])))
    map_request_rows = load_jsonl(Path(str(source["candidate_relative_map_pose_request_rows"])))
    map_candidate_rows = load_jsonl(Path(str(source["candidate_relative_map_pose_candidate_rows"])))
    outcome_rows = load_jsonl(Path(str(source["task_map_outcome_probe_rows"])))

    task_requests_by_key = index_one(task_request_rows)
    selected_task_by_key = group_by_request(task_selected_rows)
    task_selected_by_candidate = index_candidates(task_selected_rows)
    task_priority_by_candidate = index_candidates(task_priority_rows)
    map_requests_by_key = index_one(map_request_rows)
    map_candidates_by_candidate = index_candidates(map_candidate_rows)
    outcome_by_policy_key = index_policy_rows(outcome_rows)
    baselines_by_policy_key = index_policy_rows(task_baseline_rows)

    request_rows = materialize_request_rows(
        post_requests=post_request_rows,
        task_requests_by_key=task_requests_by_key,
        selected_task_by_key=selected_task_by_key,
        map_requests_by_key=map_requests_by_key,
        outcome_by_policy_key=outcome_by_policy_key,
        baselines_by_policy_key=baselines_by_policy_key,
    )
    selected_rows = materialize_selected_candidate_rows(
        post_selected=post_selected_rows,
        task_selected_by_candidate=task_selected_by_candidate,
        map_candidates_by_candidate=map_candidates_by_candidate,
        outcome_by_policy_key=outcome_by_policy_key,
    )
    candidate_rows = materialize_candidate_state_rows(
        post_candidates=post_candidate_rows,
        task_priority_by_candidate=task_priority_by_candidate,
        map_candidates_by_candidate=map_candidates_by_candidate,
        outcome_by_policy_key=outcome_by_policy_key,
    )
    baseline_rows = materialize_baseline_rows(
        baseline_rows=task_baseline_rows,
        outcome_by_policy_key=outcome_by_policy_key,
        baselines_by_policy_key=baselines_by_policy_key,
    )
    failure_rows = materialize_failure_rows(request_rows)

    action_forbidden_keys = scan_forbidden_keys([*post_request_rows, *post_selected_rows, *post_candidate_rows, *map_request_rows, *map_candidate_rows])
    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        selected_rows=selected_rows,
        candidate_rows=candidate_rows,
        baseline_rows=baseline_rows,
        failure_rows=failure_rows,
        action_forbidden_keys=action_forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["selected_candidate_rows"], selected_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_state_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(verification_path(contract_path), build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary))

    if summary.get("post_update_evaluation_join_gate_passed") is not True:
        raise SystemExit("post-update evaluation join gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize the Semantic-SLAM active-observation post-update evaluation join."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
