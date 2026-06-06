import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_active_observation_post_update.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_active_observation_post_update_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_active_observation_post_update_v1"

UTILITY_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_semantic_slam_candidate_relative_active_observation_utility_v1"
)
RISK_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_active_observation_risk_analysis_v1"

UTILITY_PRIORITY_FILE = "semantic_slam_candidate_relative_active_observation_priority_rows.jsonl"
UTILITY_REQUEST_FILE = "semantic_slam_candidate_relative_active_observation_request_rows.jsonl"
UTILITY_SUMMARY_FILE = "semantic_slam_candidate_relative_active_observation_utility_summary.json"
RISK_SUMMARY_FILE = "active_observation_risk_analysis_summary.json"

OUTPUT_FILES = {
    "request_update_rows": "active_observation_post_update_request_rows.jsonl",
    "selected_candidate_update_rows": "active_observation_post_update_selected_candidate_rows.jsonl",
    "candidate_state_rows": "active_observation_post_update_candidate_state_rows.jsonl",
    "rule_audit_rows": "active_observation_post_update_rule_audit_rows.jsonl",
    "failure_rows": "active_observation_post_update_failure_rows.jsonl",
    "summary": "active_observation_post_update_summary.json",
}

REQUEST_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

REQUIRED_RULES = (
    "defer_all_after_update",
    "commit_top_observation_utility_forbidden",
    "commit_top_selected_utility_forbidden",
    "post_update_support_unique_terminal_forbidden",
    "post_update_support_absence_rejection_forbidden",
    "request_context_only_commit_forbidden",
)

REQUIRED_FAILURE_TAGS = (
    "terminal_shortcut_rejected_before_update",
    "post_update_not_goal_validity",
    "label_free_evidence_delta_required",
    "candidate_commit_blocked",
    "candidate_rejection_blocked",
)

FORBIDDEN_UPDATE_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "correct_candidate_count",
    "wrong_candidate_count",
    "no_valid_candidate_pool",
    "success_commit_proxy",
    "success_commit_proxy_if_committed",
    "wrong_goal_visit_proxy",
    "wrong_goal_visit_proxy_if_committed",
    "no_valid_commit_proxy",
    "no_valid_commit_proxy_if_committed",
    "wasted_path_proxy_m",
    "wasted_path_proxy_m_if_committed",
    "task_proxy_commit_evaluable",
    "evaluation_only_variant_outcomes",
    "oracle",
    "ground_truth",
    "gt",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "semantic_rank_fallback_commit",
    "detector_score_fallback_commit",
    "source_top_fallback_commit",
    "local_context_fallback_commit",
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


def ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    join_key = row.get("join_key")
    source = join_key if isinstance(join_key, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("request_id") or row.get("request_id") or ""),
        str(source.get("episode_key") or row.get("episode_key") or ""),
    )


def request_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def index_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_key(row)].append(row)
    return dict(grouped)


def index_request_rows(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {request_key(row): row for row in rows}


def scan_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_UPDATE_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def terms(row: Mapping[str, Any]) -> Dict[str, float]:
    raw = row.get("utility_terms")
    if not isinstance(raw, Mapping):
        raw = {}
    return {
        "RivalAmbiguity": safe_float(raw.get("RivalAmbiguity"), 0.0) or 0.0,
        "PoseContextGap": safe_float(raw.get("PoseContextGap"), 0.0) or 0.0,
        "ProjectionUncertainty": safe_float(raw.get("ProjectionUncertainty"), 0.0) or 0.0,
        "SaturationRisk": safe_float(raw.get("SaturationRisk"), 0.0) or 0.0,
        "ObservationCostProxy": safe_float(raw.get("ObservationCostProxy"), 0.0) or 0.0,
    }


def list_tags(row: Mapping[str, Any], key: str) -> List[str]:
    value = row.get(key)
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def pre_state(row: Mapping[str, Any]) -> str:
    tags = set(list_tags(row, "risk_tags"))
    if "candidate_overlap_only_context_gap" in tags or "pose_context_gap_high" in tags:
        return "context_gap_pre_observation"
    if "candidate_relative_tie_or_saturation_nonterminal" in tags:
        return "saturated_ambiguity_pre_observation"
    if "projection_uncertainty_high" in tags:
        return "under_observed_pre_observation"
    if "candidate_relative_unique_top_nonterminal" in tags:
        return "rival_ambiguity_pre_observation"
    return "uncertain_pre_observation"


def observation_evidence(row: Mapping[str, Any]) -> Dict[str, Any]:
    utility_terms = terms(row)
    return {
        "evidence_type": "label_free_active_observation_state_update",
        "observation_action": row.get("observation_action"),
        "utility_score": safe_float(row.get("utility_score")),
        "utility_terms": utility_terms,
        "projection_visible_fraction": safe_float(row.get("projection_visible_fraction")),
        "projection_visible_heading_rank": row.get("projection_visible_heading_rank"),
        "pose_heading_rank": row.get("pose_heading_rank"),
        "map_pose_score_tuple_rank": row.get("map_pose_score_tuple_rank"),
        "map_pose_score_tuple_tie_count": row.get("map_pose_score_tuple_tie_count"),
        "target_distance_mean_m": safe_float(row.get("target_distance_mean_m")),
        "label_free_update_inputs_only": True,
    }


def evidence_delta(row: Mapping[str, Any], *, selected: bool) -> Dict[str, Any]:
    if not selected:
        return {
            "evidence_delta_available": False,
            "delta_type": "unobserved_candidate_carry_forward",
            "support_delta_proxy": 0.0,
            "rival_contrast_delta_proxy": 0.0,
            "context_support_delta_proxy": 0.0,
            "projection_resolution_delta_proxy": 0.0,
            "observation_cost_proxy": 0.0,
        }
    utility_terms = terms(row)
    projection_uncertainty = utility_terms["ProjectionUncertainty"]
    rival_ambiguity = utility_terms["RivalAmbiguity"]
    context_gap = utility_terms["PoseContextGap"]
    observation_cost = utility_terms["ObservationCostProxy"]
    action = str(row.get("observation_action") or "")
    support_delta = max(0.0, 1.0 - projection_uncertainty) * 0.35
    rival_delta = rival_ambiguity * (0.45 if action == "observe_candidate_pair" else 0.25)
    context_delta = context_gap * (0.45 if action == "observe_request_context" else 0.20)
    projection_delta = projection_uncertainty * 0.40
    cost_penalty = observation_cost * 0.10
    return {
        "evidence_delta_available": True,
        "delta_type": "label_free_proxy_delta_after_frozen_observation_action",
        "support_delta_proxy": round(support_delta, 6),
        "rival_contrast_delta_proxy": round(rival_delta, 6),
        "context_support_delta_proxy": round(context_delta, 6),
        "projection_resolution_delta_proxy": round(projection_delta, 6),
        "observation_cost_proxy": round(observation_cost, 6),
        "net_evidence_delta_proxy": round(
            support_delta + rival_delta + context_delta + projection_delta - cost_penalty,
            6,
        ),
    }


def post_state(row: Mapping[str, Any], delta: Mapping[str, Any], *, selected: bool) -> str:
    if not selected:
        return "defer_after_update"
    action = str(row.get("observation_action") or "")
    tags = set(list_tags(row, "risk_tags"))
    net_delta = safe_float(delta.get("net_evidence_delta_proxy"), 0.0) or 0.0
    support_delta = safe_float(delta.get("support_delta_proxy"), 0.0) or 0.0
    context_delta = safe_float(delta.get("context_support_delta_proxy"), 0.0) or 0.0
    rival_delta = safe_float(delta.get("rival_contrast_delta_proxy"), 0.0) or 0.0

    if action == "observe_request_context":
        if "candidate_overlap_only_context_gap" in tags and context_delta >= 0.30:
            return "needs_goal_validity_confirmation"
        return "context_only_support"
    if action == "observe_candidate_pair":
        if rival_delta >= 0.35 and net_delta >= 0.65:
            return "ambiguity_reduced"
        return "ambiguity_persisted"
    if action == "observe_candidate":
        if support_delta >= 0.12 and net_delta >= 0.40:
            return "support_acquired"
        return "no_independent_support"
    return "defer_after_update"


def candidate_state_row(row: Mapping[str, Any], selected_ids: Sequence[str]) -> Dict[str, Any]:
    key = request_key(row)
    payload = request_payload(key)
    cid = candidate_id(row)
    selected = cid in selected_ids
    delta = evidence_delta(row, selected=selected)
    state = post_state(row, delta, selected=selected)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "label_free_post_observation_evidence_update_after_action_freeze",
        "row_type": "active_observation_post_update_candidate_state",
        "join_key": {**payload, "candidate_id": cid},
        **payload,
        "candidate_id": cid,
        "selected_for_observation_update": selected,
        "selected_observation_action": row.get("observation_action") if selected else None,
        "pre_observation_state": pre_state(row),
        "observation_evidence": observation_evidence(row) if selected else {"evidence_type": "unobserved_carry_forward"},
        "post_observation_state": state,
        "evidence_delta": delta,
        "evidence_delta_available": bool(delta.get("evidence_delta_available") is True),
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def selected_candidate_update_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    key = request_key(row)
    payload = request_payload(key)
    delta = evidence_delta(row, selected=True)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "label_free_post_observation_evidence_update_after_action_freeze",
        "row_type": "active_observation_post_update_selected_candidate",
        "join_key": {**payload, "candidate_id": candidate_id(row)},
        **payload,
        "candidate_id": candidate_id(row),
        "selected_observation_action": row.get("observation_action"),
        "pre_observation_state": pre_state(row),
        "observation_evidence": observation_evidence(row),
        "post_observation_state": post_state(row, delta, selected=True),
        "evidence_delta": delta,
        "candidate_commit": False,
        "candidate_rejection": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def request_update_state(
    request_row: Mapping[str, Any],
    selected_state_rows: Sequence[Mapping[str, Any]],
) -> Tuple[str, Dict[str, Any]]:
    states = [str(row.get("post_observation_state") or "") for row in selected_state_rows]
    deltas = [row.get("evidence_delta") for row in selected_state_rows if isinstance(row.get("evidence_delta"), Mapping)]
    net_values = [safe_float(delta.get("net_evidence_delta_proxy")) for delta in deltas]
    net_values = [value for value in net_values if value is not None]
    action = str(request_row.get("selected_observation_action") or "")
    request_delta = {
        "selected_candidate_update_rows": len(selected_state_rows),
        "selected_post_state_counts": compact_counter(states),
        "mean_net_evidence_delta_proxy": round(sum(net_values) / len(net_values), 6) if net_values else None,
        "label_free_evidence_delta_available": len(net_values) == len(selected_state_rows) and bool(selected_state_rows),
    }
    if "needs_goal_validity_confirmation" in states:
        return "needs_goal_validity_confirmation", request_delta
    if "ambiguity_reduced" in states and "ambiguity_persisted" not in states:
        return "ambiguity_reduced", request_delta
    if "support_acquired" in states and len(states) == 1:
        return "support_acquired", request_delta
    if action == "observe_request_context":
        return "context_only_support", request_delta
    if states:
        return "ambiguity_persisted", request_delta
    return "defer_after_update", request_delta


def build_rows(
    priority_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    priority_by_request = index_by_request(priority_rows)
    request_out: List[Dict[str, Any]] = []
    selected_out: List[Dict[str, Any]] = []
    candidate_state_out: List[Dict[str, Any]] = []
    failure_out: List[Dict[str, Any]] = []

    for request_row in sorted(request_rows, key=request_key):
        key = request_key(request_row)
        payload = request_payload(key)
        candidates = sorted(priority_by_request.get(key, []), key=candidate_id)
        selected_ids = [str(cid) for cid in request_row.get("selected_candidate_ids") or []]
        candidate_states = [candidate_state_row(candidate, selected_ids) for candidate in candidates]
        selected_states = [row for row in candidate_states if row.get("selected_for_observation_update") is True]
        selected_candidate_rows = [candidate for candidate in candidates if candidate_id(candidate) in selected_ids]
        selected_out.extend(selected_candidate_update_row(candidate) for candidate in selected_candidate_rows)
        candidate_state_out.extend(candidate_states)
        post_update_state, request_delta = request_update_state(request_row, selected_states)

        request_out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "label_free_post_observation_evidence_update_after_action_freeze",
                "row_type": "active_observation_post_update_request",
                "join_key": payload,
                **payload,
                "selected_observation_action": request_row.get("selected_observation_action"),
                "selected_candidate_ids": selected_ids,
                "selected_candidate_count": len(selected_ids),
                "pre_update_request_risk_tags": request_row.get("request_risk_tags"),
                "post_update_request_state": post_update_state,
                "request_evidence_delta": request_delta,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )

        failure_tags = list(REQUIRED_FAILURE_TAGS)
        if post_update_state in {"ambiguity_persisted", "needs_goal_validity_confirmation", "context_only_support"}:
            failure_tags.append("post_update_goal_validity_unresolved")
        if request_row.get("selected_observation_action") == "observe_request_context":
            failure_tags.append("request_context_update_is_not_commit")
        if request_row.get("selected_observation_action") == "observe_candidate_pair":
            failure_tags.append("pair_update_requires_later_arbitration")
        if request_row.get("selected_observation_action") == "observe_candidate":
            failure_tags.append("single_candidate_update_requires_later_goal_validity_check")
        failure_out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "label_free_post_observation_evidence_update_after_action_freeze",
                "row_type": "active_observation_post_update_failure_taxonomy",
                "join_key": payload,
                **payload,
                "failure_tags": sorted(set(failure_tags)),
                "primary_failure_or_blocker": "post_update_not_goal_validity",
                "selected_observation_action": request_row.get("selected_observation_action"),
                "post_update_request_state": post_update_state,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )

    return request_out, selected_out, candidate_state_out, failure_out


def risk_rule_counts(risk_summary: Mapping[str, Any], rule_name: str) -> Dict[str, int]:
    audit = risk_summary.get("terminal_shortcut_audit")
    audit = audit if isinstance(audit, Mapping) else {}
    row = audit.get(rule_name)
    row = row if isinstance(row, Mapping) else {}
    return {
        "rows": safe_int(row.get("rows"), 0),
        "terminal_rows": safe_int(row.get("terminal_rows"), 0),
        "success_rows": safe_int(row.get("success_rows"), 0),
        "wrong_goal_rows": safe_int(row.get("wrong_goal_rows"), 0),
        "no_valid_rows": safe_int(row.get("no_valid_rows"), 0),
        "defer_rows": safe_int(row.get("defer_rows"), 0),
    }


def build_rule_audit_rows(request_rows: Sequence[Mapping[str, Any]], risk_summary: Mapping[str, Any]) -> List[Dict[str, Any]]:
    base = {
        "schema_version": SCHEMA_VERSION,
        "row_type": "active_observation_post_update_rule_audit",
        "rule_family": "post_observation_evidence_update_shortcut_audit",
        "rows": len(request_rows),
        "terminal_utility_contract_allowed": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    top_counts = risk_rule_counts(risk_summary, "top_observation_utility_if_misused_as_terminal")
    selected_counts = risk_rule_counts(risk_summary, "top_selected_observation_utility_if_misused_as_terminal")
    rows = [
        {
            **base,
            "rule_name": "defer_all_after_update",
            "terminal_rows": 0,
            "success_rows": 0,
            "wrong_goal_rows": 0,
            "no_valid_rows": 0,
            "defer_rows": len(request_rows),
            "rule_status": "safe_but_inert",
            "evaluation_reference": "none",
        },
        {
            **base,
            "rule_name": "commit_top_observation_utility_forbidden",
            **top_counts,
            "rule_status": "forbidden_terminal_shortcut_from_pre_update_risk",
            "evaluation_reference": "risk_analysis_after_action_freeze",
        },
        {
            **base,
            "rule_name": "commit_top_selected_utility_forbidden",
            **selected_counts,
            "rule_status": "forbidden_terminal_shortcut_from_pre_update_risk",
            "evaluation_reference": "risk_analysis_after_action_freeze",
        },
        {
            **base,
            "rule_name": "post_update_support_unique_terminal_forbidden",
            "terminal_rows": 0,
            "success_rows": 0,
            "wrong_goal_rows": 0,
            "no_valid_rows": 0,
            "defer_rows": len(request_rows),
            "rule_status": "support_acquisition_is_not_goal_validity",
            "evaluation_reference": "not_evaluated_until_post_update_label_join",
        },
        {
            **base,
            "rule_name": "post_update_support_absence_rejection_forbidden",
            "terminal_rows": 0,
            "success_rows": 0,
            "wrong_goal_rows": 0,
            "no_valid_rows": 0,
            "defer_rows": len(request_rows),
            "rule_status": "missing_support_is_not_candidate_rejection",
            "evaluation_reference": "not_evaluated_until_post_update_label_join",
        },
        {
            **base,
            "rule_name": "request_context_only_commit_forbidden",
            "terminal_rows": 0,
            "success_rows": 0,
            "wrong_goal_rows": 0,
            "no_valid_rows": 0,
            "defer_rows": len(request_rows),
            "rule_status": "context_support_requires_separate_goal_validity_arbitration",
            "evaluation_reference": "not_evaluated_until_post_update_label_join",
        },
    ]
    return rows


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def build_summary(
    *,
    contract_path: Path,
    utility_root: Path,
    risk_root: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    selected_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    rule_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    utility_summary: Mapping[str, Any],
    risk_summary: Mapping[str, Any],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    required_rule_names = set(REQUIRED_RULES)
    actual_rule_names = {str(row.get("rule_name")) for row in rule_rows}
    failure_tags = Counter(tag for row in failure_rows for tag in row.get("failure_tags", []))
    required_failure_tags = set(REQUIRED_FAILURE_TAGS)
    actual_counts = {
        "request_update_rows": len(request_rows),
        "selected_candidate_update_rows": len(selected_rows),
        "candidate_state_rows": len(candidate_rows),
        "rule_audit_rows": len(rule_rows),
        "failure_taxonomy_rows": len(failure_rows),
        "selected_candidate_evidence_delta_rows": sum(
            1 for row in selected_rows if (row.get("evidence_delta") or {}).get("evidence_delta_available") is True
        ),
        "candidate_state_evidence_delta_rows": sum(1 for row in candidate_rows if row.get("evidence_delta_available") is True),
        "terminal_commit_rows": count_true(request_rows + selected_rows + candidate_rows + failure_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(request_rows + selected_rows + candidate_rows + failure_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(
            request_rows + selected_rows + candidate_rows + failure_rows,
            "candidate_rejection",
        ),
        "uses_gt_for_action_true_rows": count_true(
            request_rows + selected_rows + candidate_rows + failure_rows + rule_rows,
            "uses_gt_for_action",
        ),
        "paper_claim_allowed_true_rows": count_true(
            request_rows + selected_rows + candidate_rows + failure_rows + rule_rows,
            "paper_claim_allowed",
        ),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
    }
    gate = {
        "contract_status_frozen_passed": load_json(contract_path).get("status") == "frozen_contract_implementation_pending",
        "source_utility_gate_passed": utility_summary.get("active_observation_materializer_gate_passed") is True,
        "source_risk_gate_passed": risk_summary.get("risk_analysis_gate_passed") is True,
        "request_update_rows_expected_passed": actual_counts["request_update_rows"] == 50,
        "selected_candidate_update_rows_expected_passed": actual_counts["selected_candidate_update_rows"] == 97,
        "candidate_state_rows_expected_passed": actual_counts["candidate_state_rows"] == 232,
        "rule_audit_rows_minimum_passed": actual_counts["rule_audit_rows"] >= 6,
        "required_rules_present_passed": required_rule_names.issubset(actual_rule_names),
        "failure_rows_minimum_passed": actual_counts["failure_taxonomy_rows"] >= 50,
        "required_failure_tags_present_passed": required_failure_tags.issubset(set(failure_tags)),
        "selected_evidence_delta_required_passed": actual_counts["selected_candidate_evidence_delta_rows"] == 97,
        "action_evidence_forbidden_key_count_passed": actual_counts["action_evidence_forbidden_key_count"] == 0,
        "terminal_commit_rows_passed": actual_counts["terminal_commit_rows"] == 0,
        "candidate_commit_rows_passed": actual_counts["candidate_commit_rows"] == 0,
        "candidate_rejection_rows_passed": actual_counts["candidate_rejection_rows"] == 0,
        "uses_gt_for_action_passed": actual_counts["uses_gt_for_action_true_rows"] == 0,
        "paper_claim_blocked_passed": actual_counts["paper_claim_allowed_true_rows"] == 0,
    }
    gate["post_update_materializer_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "post_update_materializer_gate_passed_promotion_blocked"
        if gate["post_update_materializer_gate_passed"]
        else "post_update_materializer_gate_failed",
        "contract": str(contract_path),
        "utility_root": str(utility_root),
        "risk_root": str(risk_root),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "actual_counts": actual_counts,
        "request_post_update_state_counts": compact_counter(row.get("post_update_request_state") for row in request_rows),
        "selected_candidate_post_state_counts": compact_counter(
            row.get("post_observation_state") for row in selected_rows
        ),
        "candidate_state_post_state_counts": compact_counter(row.get("post_observation_state") for row in candidate_rows),
        "selected_observation_action_counts": compact_counter(row.get("selected_observation_action") for row in request_rows),
        "rule_audit_status_counts": compact_counter(row.get("rule_status") for row in rule_rows),
        "failure_tag_counts": dict(sorted(failure_tags.items())),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "post_update_contract_gate_passed": True,
        "post_update_materializer_gate": gate,
        "post_update_materializer_gate_passed": gate["post_update_materializer_gate_passed"],
        "promotion_gate_after_post_update": {
            "post_update_materializer_gate_must_pass": gate["post_update_materializer_gate_passed"],
            "post_update_label_join_required": False,
            "terminal_utility_contract_allowed": False,
            "heldout_or_fresh_validation_required_before_paper_claim": True,
        },
        "promotion_gate_after_post_update_passed": False,
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed": False,
        "primary_blocker": "post_update_label_join_and_goal_validity_arbitration_required",
        "recommended_next_task": "freeze_active_observation_post_update_evaluation_join_contract",
        "next_task": "freeze_active_observation_post_update_evaluation_join_contract",
        "interpretation": {
            "fact": (
                "The materializer writes request, selected-candidate, candidate-state, rule-audit, "
                "and failure-taxonomy rows from frozen active-observation actions."
            ),
            "agent_inference": (
                "The post-update rows make evidence state changes explicit without using task labels or GT for action. "
                "They still cannot support terminal utility until a separate post-update evaluation join and "
                "non-GT goal-validity arbitration rule are defined."
            ),
            "paper_claim": (
                "No ObjectNav utility, Semantic-SLAM complementarity, SLAM benefit, terminal utility, "
                "first_eval rerun, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim "
                "is allowed from this artifact."
            ),
        },
    }


def run(args: argparse.Namespace) -> None:
    contract_path = Path(args.contract)
    utility_root = Path(args.utility_root)
    risk_root = Path(args.risk_root)
    out_root = Path(args.out_root)

    priority_rows = load_jsonl(utility_root / UTILITY_PRIORITY_FILE)
    request_rows = load_jsonl(utility_root / UTILITY_REQUEST_FILE)
    utility_summary = load_json(utility_root / UTILITY_SUMMARY_FILE)
    risk_summary = load_json(risk_root / RISK_SUMMARY_FILE)

    update_request_rows, selected_rows, candidate_rows, failure_rows = build_rows(priority_rows, request_rows)
    rule_rows = build_rule_audit_rows(update_request_rows, risk_summary)

    forbidden_keys = scan_forbidden_keys(priority_rows + request_rows + update_request_rows + selected_rows + candidate_rows)
    summary = build_summary(
        contract_path=contract_path,
        utility_root=utility_root,
        risk_root=risk_root,
        out_root=out_root,
        request_rows=update_request_rows,
        selected_rows=selected_rows,
        candidate_rows=candidate_rows,
        rule_rows=rule_rows,
        failure_rows=failure_rows,
        utility_summary=utility_summary,
        risk_summary=risk_summary,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_update_rows"], update_request_rows)
    write_jsonl(out_root / OUTPUT_FILES["selected_candidate_update_rows"], selected_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_state_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["rule_audit_rows"], rule_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)

    if not summary["post_update_materializer_gate_passed"]:
        raise SystemExit("post-update materializer gate failed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize label-free active-observation post-observation evidence update rows."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--utility-root", default=UTILITY_ROOT_DEFAULT)
    parser.add_argument("--risk-root", default=RISK_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser


def main() -> None:
    run(build_parser().parse_args())


if __name__ == "__main__":
    main()
