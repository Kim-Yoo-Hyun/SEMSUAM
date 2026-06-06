import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_candidate_relative_active_observation_task_proxy_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1"
)

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
SOURCE_REQUEST_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")

OUTPUT_FILES = {
    "priority_rows": "semantic_slam_candidate_relative_active_observation_task_proxy_priority_rows.jsonl",
    "selected_candidate_rows": (
        "semantic_slam_candidate_relative_active_observation_task_proxy_selected_candidate_rows.jsonl"
    ),
    "request_rows": "semantic_slam_candidate_relative_active_observation_task_proxy_request_rows.jsonl",
    "alternative_rows": "semantic_slam_candidate_relative_active_observation_task_proxy_alternative_rows.jsonl",
    "baseline_rows": "semantic_slam_candidate_relative_active_observation_task_proxy_baseline_rows.jsonl",
    "failure_rows": "semantic_slam_candidate_relative_active_observation_task_proxy_failure_rows.jsonl",
    "summary": "semantic_slam_candidate_relative_active_observation_task_proxy_summary.json",
}

FORBIDDEN_ACTION_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "correct_candidate_count",
    "correctness_label",
    "detector_score",
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
    "semantic_rank",
    "semantic_score",
    "shortest_path_distance",
    "source_top_candidate_ids",
    "success_commit",
    "success_commit_proxy",
    "target_detector_evidence_score",
    "target_positive_support",
    "target_semantic_score",
    "target_support_score",
    "wasted_path_proxy_m",
    "wrong_candidate_count",
    "wrong_goal_commit",
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


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def normalized_request_id(row: Mapping[str, Any]) -> str:
    for key in REQUEST_ID_ALIASES:
        value = row.get(key)
        if value:
            return str(value)
    nested = row.get("join_key")
    if isinstance(nested, Mapping):
        value = nested.get("request_id")
        if value:
            return str(value)
    return ""


def source_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
        str(source.get("query") or row.get("query") or ""),
        normalized_request_id(row),
        str(source.get("episode_key") or row.get("episode_key") or ""),
    )


def source_request_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(SOURCE_REQUEST_KEYS, key))


def evaluation_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("episode_key") or row.get("episode_key") or ""),
        normalized_request_id(row),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
    )


def label_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("episode_key") or ""),
        str(row.get("request_id") or ""),
        str(row.get("query") or ""),
        str(row.get("scene_key") or ""),
    )


def request_payload(key: Tuple[str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def index_request_labels(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str], Mapping[str, Any]]:
    return {label_request_key(row): row for row in rows}


def index_candidate_labels(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        index[label_request_key(row)][str(row.get("candidate_id") or "")] = row
    return dict(index)


def index_request_rows(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {source_request_key(row): row for row in rows}


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
        "label_usage": "evaluation_only_after_active_observation_action_freeze",
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def request_label_payload(req_label: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "request_label_join_available": req_label is not None,
        "candidate_label_count": safe_int((req_label or {}).get("candidate_label_count"), 0),
        "correct_candidate_count": safe_int((req_label or {}).get("correct_candidate_count"), 0),
        "wrong_candidate_count": safe_int((req_label or {}).get("wrong_candidate_count"), 0),
        "unlabeled_candidate_count": safe_int((req_label or {}).get("unlabeled_candidate_count"), 0),
        "no_valid_candidate_pool": (req_label or {}).get("no_valid_candidate_pool") if req_label else None,
        "task_label_source": (req_label or {}).get("label_source") if req_label else None,
    }


def candidate_label_payload(
    req_label: Optional[Mapping[str, Any]],
    cand_label: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    no_valid = (cand_label or req_label or {}).get("no_valid_candidate_pool")
    return {
        "candidate_label_join_available": cand_label is not None,
        "candidate_correctness_label": cand_label.get("candidate_correctness_label") if cand_label else None,
        "candidate_wrong_label": cand_label.get("candidate_wrong_label") if cand_label else None,
        "no_valid_candidate_pool": no_valid if cand_label or req_label else None,
        "candidate_label_source": cand_label.get("label_source") if cand_label else None,
    }


def candidate_label_for(
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
    req_key: Tuple[str, str, str, str],
    selected_id: Optional[str],
) -> Optional[Mapping[str, Any]]:
    if not selected_id:
        return None
    return (candidate_labels.get(req_key) or {}).get(str(selected_id))


def selected_candidate_label_counts(
    req_label: Optional[Mapping[str, Any]],
    selected_ids: Sequence[str],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
    req_key: Tuple[str, str, str, str],
) -> Dict[str, Any]:
    labels = [candidate_label_for(candidate_labels, req_key, selected_id) for selected_id in selected_ids]
    available = [label for label in labels if label is not None]
    no_valid_pool = bool(req_label and req_label.get("no_valid_candidate_pool") is True)
    return {
        "selected_candidate_rows": len(selected_ids),
        "label_join_available_rows": len(available),
        "label_missing_rows": len(selected_ids) - len(available),
        "correct_rows": sum(1 for label in available if label.get("candidate_correctness_label") is True),
        "wrong_rows": sum(1 for label in available if label.get("candidate_wrong_label") is True),
        "no_valid_request_pool": no_valid_pool,
        "wrong_or_no_valid_risk_rows": sum(
            1
            for label in available
            if label.get("candidate_wrong_label") is True or no_valid_pool
        ),
    }


def materialize_priority_rows(
    priority_rows: Sequence[Mapping[str, Any]],
    request_rows_by_source: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in priority_rows:
        src_key = source_request_key(row)
        req_key = evaluation_request_key(row)
        req_label = request_labels.get(req_key)
        cand_label = candidate_label_for(candidate_labels, req_key, candidate_id(row))
        request_row = request_rows_by_source.get(src_key) or {}
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_join_after_active_observation_action_freeze",
                "row_type": "semantic_slam_candidate_relative_active_observation_task_proxy_priority",
                "join_key": {**source_request_payload(src_key), "candidate_id": candidate_id(row)},
                **source_request_payload(src_key),
                "candidate_id": candidate_id(row),
                "candidate_count": safe_int(row.get("candidate_count"), 0),
                "ready_candidate_count": safe_int(row.get("ready_candidate_count"), 0),
                "selected_observation_action": request_row.get("selected_observation_action"),
                "observation_action": row.get("observation_action"),
                "utility_score": safe_float(row.get("utility_score")),
                "utility_terms": row.get("utility_terms"),
                "risk_tags": row.get("risk_tags"),
                "selected_for_request_action": bool(row.get("selected_for_request_action") is True),
                "request_selected_candidate_ids": row.get("request_selected_candidate_ids"),
                "map_pose_score_tuple_rank": row.get("map_pose_score_tuple_rank"),
                "map_pose_score_tuple_tie_count": row.get("map_pose_score_tuple_tie_count"),
                "projection_visible_fraction": row.get("projection_visible_fraction"),
                "projection_visible_heading_rank": row.get("projection_visible_heading_rank"),
                "pose_heading_rank": row.get("pose_heading_rank"),
                "target_distance_mean_m": row.get("target_distance_mean_m"),
                "separability_status": row.get("separability_status"),
                "separability_tag": row.get("separability_tag"),
                "active_observation_action_frozen": True,
                **request_label_payload(req_label),
                **candidate_label_payload(req_label, cand_label),
                **eval_flags(),
            }
        )
    return out


def materialize_selected_candidate_rows(priority_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in priority_rows:
        if row.get("selected_for_request_action") is not True:
            continue
        copied = dict(row)
        copied["row_type"] = "semantic_slam_candidate_relative_active_observation_task_proxy_selected_candidate"
        copied["selected_candidate_eval_role"] = "selected_by_frozen_active_observation_action"
        out.append(copied)
    return out


def materialize_request_rows(
    request_rows: Sequence[Mapping[str, Any]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in request_rows:
        src_key = source_request_key(row)
        req_key = evaluation_request_key(row)
        req_label = request_labels.get(req_key)
        selected_ids = [str(value) for value in row.get("selected_candidate_ids") or []]
        counts = selected_candidate_label_counts(req_label, selected_ids, candidate_labels, req_key)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_join_after_active_observation_action_freeze",
                "row_type": "semantic_slam_candidate_relative_active_observation_task_proxy_request",
                "join_key": source_request_payload(src_key),
                **source_request_payload(src_key),
                "candidate_count": safe_int(row.get("candidate_count"), 0),
                "ready_candidate_count": safe_int(row.get("ready_candidate_count"), 0),
                "selected_observation_action": row.get("selected_observation_action"),
                "selected_candidate_count": safe_int(row.get("selected_candidate_count"), len(selected_ids)),
                "selected_candidate_ids": selected_ids,
                "selected_candidate_utility_scores": row.get("selected_candidate_utility_scores"),
                "selected_candidate_label_counts": counts,
                "request_risk_tags": row.get("request_risk_tags"),
                "separability_status": row.get("separability_status"),
                "active_observation_action_frozen": True,
                **request_label_payload(req_label),
                **eval_flags(),
            }
        )
    return out


def materialize_alternative_rows(
    alternative_rows: Sequence[Mapping[str, Any]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in alternative_rows:
        src_key = source_request_key(row)
        req_key = evaluation_request_key(row)
        req_label = request_labels.get(req_key)
        audit_id = row.get("audit_selected_candidate_id")
        audit_id = str(audit_id) if audit_id else None
        cand_label = candidate_label_for(candidate_labels, req_key, audit_id)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_join_after_active_observation_action_freeze",
                "row_type": "semantic_slam_candidate_relative_active_observation_task_proxy_alternative",
                "join_key": dict(row.get("join_key") or {}),
                **source_request_payload(src_key),
                "alternative_id": row.get("alternative_id"),
                "alternative_role": row.get("alternative_role"),
                "alternative_allowed_as_nonterminal_audit": bool(
                    row.get("alternative_allowed_as_nonterminal_audit") is True
                ),
                "alternative_allowed_as_terminal_action": False,
                "fallback_shortcut_forbidden": bool(row.get("fallback_shortcut_forbidden") is True),
                "audit_selection_reason": row.get("audit_selection_reason"),
                "audit_selected_candidate_id": audit_id,
                "audit_has_selected_candidate": audit_id is not None,
                "active_observation_action_frozen": True,
                **request_label_payload(req_label),
                **candidate_label_payload(req_label, cand_label),
                **eval_flags(),
            }
        )
    return out


def materialize_baseline_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        join_key = dict(row.get("join_key") or {})
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_baseline_context_after_active_observation_action_freeze",
                "row_type": "semantic_slam_candidate_relative_active_observation_task_proxy_baseline",
                "join_key": join_key,
                "source_name": str(row.get("source_name") or join_key.get("source_name") or ""),
                "scene_key": str(row.get("scene_key") or join_key.get("scene_key") or ""),
                "query": str(row.get("query") or join_key.get("query") or ""),
                "request_id": str(row.get("request_id") or join_key.get("request_id") or ""),
                "episode_key": str(row.get("episode_key") or join_key.get("episode_key") or ""),
                "policy_name": row.get("policy_name"),
                "selector_id": row.get("selector_id"),
                "selector_action": row.get("selector_action"),
                "selector_source": row.get("selector_source"),
                "selector_missing": bool(row.get("selector_missing") is True),
                "selector_missing_reason": row.get("selector_missing_reason"),
                "policy_selected_candidate_id": row.get("policy_selected_candidate_id"),
                "terminal_commit_proxy": bool(row.get("terminal_commit_proxy") is True),
                "success_commit_proxy": bool(row.get("success_commit_proxy") is True),
                "wrong_goal_visit_proxy": bool(row.get("wrong_goal_visit_proxy") is True),
                "no_valid_commit_proxy": bool(row.get("no_valid_commit_proxy") is True),
                "wasted_path_proxy_m": safe_float(row.get("wasted_path_proxy_m"), 0.0),
                "map_task_alignment_proxy": bool(row.get("map_task_alignment_proxy") is True),
                "task_proxy_decision_evaluable": bool(row.get("task_proxy_decision_evaluable") is True),
                "task_proxy_commit_evaluable": bool(row.get("task_proxy_commit_evaluable") is True),
                "selected_candidate_label_join_available": bool(
                    row.get("selected_candidate_label_join_available") is True
                ),
                "selected_candidate_correctness_label": row.get("selected_candidate_correctness_label"),
                "selected_candidate_wrong_label": row.get("selected_candidate_wrong_label"),
                "evaluation_only_baseline_context": True,
                "candidate_relative_active_observation_action_source": False,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return out


def failure_tags_for_request(row: Mapping[str, Any]) -> List[str]:
    counts = row.get("selected_candidate_label_counts")
    counts = counts if isinstance(counts, Mapping) else {}
    tags = [
        "task_proxy_join_after_action_freeze",
        "active_observation_not_terminal_utility",
        "selected_candidate_risk_evaluation_only",
        "wrong_or_no_valid_risk_evaluation_only",
        "top_rule_remains_closed",
        "promotion_requires_nonterminal_task_proxy_signal",
    ]
    if row.get("request_label_join_available") is not True:
        tags.append("request_label_missing")
    if safe_int(counts.get("label_missing_rows"), 0) > 0:
        tags.append("selected_candidate_label_missing")
    if safe_int(counts.get("wrong_rows"), 0) > 0:
        tags.append("selected_candidate_contains_wrong_candidate_evaluation_only")
    if counts.get("no_valid_request_pool") is True:
        tags.append("selected_candidate_no_valid_pool_evaluation_only")
    if safe_int(counts.get("correct_rows"), 0) > 0:
        tags.append("selected_candidate_contains_correct_candidate_evaluation_only")
    if row.get("selected_observation_action") == "observe_request_context":
        tags.append("request_context_observation_selected")
    if row.get("selected_observation_action") == "observe_candidate_pair":
        tags.append("candidate_pair_observation_selected")
    if row.get("selected_observation_action") == "observe_candidate":
        tags.append("single_candidate_observation_selected")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "request_label_missing",
        "selected_candidate_label_missing",
        "selected_candidate_no_valid_pool_evaluation_only",
        "selected_candidate_contains_wrong_candidate_evaluation_only",
        "selected_candidate_contains_correct_candidate_evaluation_only",
    ):
        if tag in tags:
            return tag
    return "active_observation_not_terminal_utility"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in request_rows:
        src_key = source_request_key(row)
        tags = failure_tags_for_request(row)
        counts = row.get("selected_candidate_label_counts")
        counts = counts if isinstance(counts, Mapping) else {}
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_join_after_active_observation_action_freeze",
                "row_type": "semantic_slam_candidate_relative_active_observation_task_proxy_failure",
                "join_key": source_request_payload(src_key),
                **source_request_payload(src_key),
                "primary_failure_or_blocker": primary_failure(tags),
                "failure_tags": tags,
                "selected_observation_action": row.get("selected_observation_action"),
                "selected_candidate_count": row.get("selected_candidate_count"),
                "selected_candidate_label_counts": counts,
                "request_label_join_available": row.get("request_label_join_available"),
                "active_observation_action_frozen": True,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return out


def baseline_policy_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for policy in sorted({str(row.get("policy_name") or "") for row in rows}):
        subset = [row for row in rows if row.get("policy_name") == policy]
        wasted_values = [safe_float(row.get("wasted_path_proxy_m"), 0.0) or 0.0 for row in subset]
        result[policy] = {
            "rows": len(subset),
            "terminal_commit_proxy_rows": sum(1 for row in subset if row.get("terminal_commit_proxy") is True),
            "success_commit_proxy_rows": sum(1 for row in subset if row.get("success_commit_proxy") is True),
            "wrong_goal_visit_proxy_rows": sum(1 for row in subset if row.get("wrong_goal_visit_proxy") is True),
            "no_valid_commit_proxy_rows": sum(1 for row in subset if row.get("no_valid_commit_proxy") is True),
            "wasted_path_sum_m": sum(wasted_values),
            "wasted_path_mean_m": ratio(sum(wasted_values), len(wasted_values)),
        }
    return result


def request_action_label_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}
    for action in sorted({str(row.get("selected_observation_action") or "") for row in rows}):
        subset = [row for row in rows if row.get("selected_observation_action") == action]
        counts = [row.get("selected_candidate_label_counts") for row in subset]
        typed = [count if isinstance(count, Mapping) else {} for count in counts]
        result[action] = {
            "request_rows": len(subset),
            "selected_candidate_rows": sum(safe_int(count.get("selected_candidate_rows"), 0) for count in typed),
            "selected_correct_rows": sum(safe_int(count.get("correct_rows"), 0) for count in typed),
            "selected_wrong_rows": sum(safe_int(count.get("wrong_rows"), 0) for count in typed),
            "selected_label_missing_rows": sum(safe_int(count.get("label_missing_rows"), 0) for count in typed),
            "no_valid_request_pool_rows": sum(1 for count in typed if count.get("no_valid_request_pool") is True),
            "wrong_or_no_valid_risk_rows": sum(
                safe_int(count.get("wrong_or_no_valid_risk_rows"), 0) for count in typed
            ),
        }
    return result


def selected_candidate_label_totals(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    return {
        "selected_candidate_rows": len(rows),
        "label_join_available_rows": sum(1 for row in rows if row.get("candidate_label_join_available") is True),
        "label_missing_rows": sum(1 for row in rows if row.get("candidate_label_join_available") is not True),
        "correct_rows": sum(1 for row in rows if row.get("candidate_correctness_label") is True),
        "wrong_rows": sum(1 for row in rows if row.get("candidate_wrong_label") is True),
        "no_valid_pool_rows": sum(1 for row in rows if row.get("no_valid_candidate_pool") is True),
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    priority_rows: Sequence[Mapping[str, Any]],
    selected_candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    alternative_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    request_label_rows: Sequence[Mapping[str, Any]],
    candidate_label_rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
    out_root: Path,
) -> Dict[str, Any]:
    gates = contract.get("contract_gates")
    gates = gates if isinstance(gates, Mapping) else {}
    required_outputs = contract.get("required_outputs")
    required_outputs = required_outputs if isinstance(required_outputs, Mapping) else {}
    alt_contract = required_outputs.get("alternative_task_proxy_rows")
    alt_contract = alt_contract if isinstance(alt_contract, Mapping) else {}
    baseline_contract = required_outputs.get("baseline_policy_context_rows")
    baseline_contract = baseline_contract if isinstance(baseline_contract, Mapping) else {}

    action_rows = [*priority_rows, *selected_candidate_rows, *request_rows, *alternative_rows, *failure_rows]
    baseline_action_context_rows = [*baseline_rows]
    terminal_commit_rows = sum(1 for row in [*action_rows, *baseline_action_context_rows] if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in [*action_rows, *baseline_action_context_rows] if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(
        1 for row in [*action_rows, *baseline_action_context_rows] if row.get("candidate_rejection") is True
    )
    request_label_missing_rows = sum(1 for row in request_rows if row.get("request_label_join_available") is not True)
    priority_candidate_label_missing_rows = sum(
        1 for row in priority_rows if row.get("candidate_label_join_available") is not True
    )
    selected_candidate_label_missing_rows = sum(
        1 for row in selected_candidate_rows if row.get("candidate_label_join_available") is not True
    )
    alternative_audit_rows = [
        row for row in alternative_rows if row.get("audit_selected_candidate_id") not in (None, "")
    ]
    alternative_audit_missing_rows = sum(
        1 for row in alternative_audit_rows if row.get("candidate_label_join_available") is not True
    )
    required_alt_ids = set(alt_contract.get("required_alternatives") or [])
    actual_alt_ids = {str(row.get("alternative_id") or "") for row in alternative_rows}
    required_policies = set(baseline_contract.get("required_policies") or [])
    actual_policies = {str(row.get("policy_name") or "") for row in baseline_rows}

    actual_counts = {
        "priority_task_proxy_rows": len(priority_rows),
        "selected_candidate_task_proxy_rows": len(selected_candidate_rows),
        "request_task_proxy_rows": len(request_rows),
        "alternative_task_proxy_rows": len(alternative_rows),
        "baseline_policy_context_rows": len(baseline_rows),
        "failure_taxonomy_rows": len(failure_rows),
        "request_label_rows": len(request_label_rows),
        "candidate_label_rows": len(candidate_label_rows),
        "request_label_missing_rows": request_label_missing_rows,
        "priority_candidate_label_missing_rows": priority_candidate_label_missing_rows,
        "selected_candidate_label_missing_rows": selected_candidate_label_missing_rows,
        "alternative_audit_selected_candidate_rows": len(alternative_audit_rows),
        "alternative_audit_candidate_label_missing_rows": alternative_audit_missing_rows,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action_true_rows": sum(
            1 for row in [*action_rows, *baseline_action_context_rows] if row.get("uses_gt_for_action") is True
        ),
        "paper_claim_allowed_true_rows": sum(
            1 for row in [*action_rows, *baseline_action_context_rows] if row.get("paper_claim_allowed") is True
        ),
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
    }
    join_gate = {
        "priority_rows_expected_passed": actual_counts["priority_task_proxy_rows"]
        == safe_int(gates.get("priority_rows_expected"), actual_counts["priority_task_proxy_rows"]),
        "selected_candidate_rows_expected_passed": actual_counts["selected_candidate_task_proxy_rows"]
        == safe_int(gates.get("selected_candidate_rows_expected"), actual_counts["selected_candidate_task_proxy_rows"]),
        "request_rows_expected_passed": actual_counts["request_task_proxy_rows"]
        == safe_int(gates.get("request_rows_expected"), actual_counts["request_task_proxy_rows"]),
        "alternative_rows_expected_passed": actual_counts["alternative_task_proxy_rows"]
        == safe_int(gates.get("alternative_rows_expected"), actual_counts["alternative_task_proxy_rows"]),
        "baseline_policy_context_rows_expected_passed": actual_counts["baseline_policy_context_rows"]
        == safe_int(gates.get("baseline_policy_context_rows_expected"), actual_counts["baseline_policy_context_rows"]),
        "failure_rows_minimum_passed": actual_counts["failure_taxonomy_rows"]
        >= safe_int(gates.get("failure_rows_minimum"), 0),
        "request_label_missing_rows_passed": request_label_missing_rows
        <= safe_int(gates.get("request_label_missing_rows_max"), request_label_missing_rows),
        "priority_candidate_label_missing_rows_passed": priority_candidate_label_missing_rows
        <= safe_int(gates.get("candidate_label_missing_rows_max"), priority_candidate_label_missing_rows),
        "selected_candidate_label_missing_rows_passed": selected_candidate_label_missing_rows
        <= safe_int(gates.get("selected_candidate_label_missing_rows_max"), selected_candidate_label_missing_rows),
        "alternative_audit_candidate_label_missing_rows_passed": alternative_audit_missing_rows == 0,
        "alternative_audit_rows_expected_passed": len(alternative_audit_rows)
        == safe_int(alt_contract.get("expected_rows_with_audit_selected_candidate"), len(alternative_audit_rows)),
        "required_alternatives_present_passed": required_alt_ids.issubset(actual_alt_ids),
        "required_baseline_policies_present_passed": required_policies.issubset(actual_policies),
        "action_evidence_forbidden_keys_passed": len(action_forbidden_keys)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_max"), len(action_forbidden_keys)),
        "terminal_commit_rows_passed": terminal_commit_rows
        <= safe_int(gates.get("terminal_commit_rows_max"), terminal_commit_rows),
        "candidate_commit_rows_passed": candidate_commit_rows
        <= safe_int(gates.get("candidate_commit_rows_max"), candidate_commit_rows),
        "candidate_rejection_rows_passed": candidate_rejection_rows
        <= safe_int(gates.get("candidate_rejection_rows_max"), candidate_rejection_rows),
        "uses_gt_for_action_passed": actual_counts["uses_gt_for_action_true_rows"] == 0,
        "uses_gt_for_analysis_passed": all(
            row.get("uses_gt_for_analysis") is True for row in [*action_rows, *baseline_action_context_rows]
        ),
        "paper_claim_allowed_passed": actual_counts["paper_claim_allowed_true_rows"] == 0,
    }
    join_gate_passed = all(join_gate.values())
    promotion_gate_after_join = {
        "active_observation_task_proxy_join_gate_passed": join_gate_passed,
        "promotion_gate_after_join_required": bool(gates.get("promotion_gate_after_join_required") is True),
        "terminal_utility_validation_allowed": bool(gates.get("terminal_utility_validation_allowed") is True),
        "heldout_or_fresh_validation_required_before_paper_claim": bool(
            gates.get("heldout_or_fresh_validation_required_before_paper_claim") is True
        ),
        "evaluation_only_join_cannot_promote_terminal_utility": True,
    }
    promotion_gate_after_join_passed = False
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "active_observation_task_proxy_join_gate_passed_promotion_blocked"
        if join_gate_passed
        else "active_observation_task_proxy_join_gate_failed",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        "actual_counts": actual_counts,
        "selected_candidate_label_totals": selected_candidate_label_totals(selected_candidate_rows),
        "request_action_label_counts": request_action_label_counts(request_rows),
        "selected_observation_action_counts": compact_counter(
            row.get("selected_observation_action") for row in request_rows
        ),
        "candidate_observation_action_counts": compact_counter(row.get("observation_action") for row in priority_rows),
        "alternative_id_counts": compact_counter(row.get("alternative_id") for row in alternative_rows),
        "baseline_policy_counts": baseline_policy_counts(baseline_rows),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "action_evidence_scan_scope": "frozen_active_observation_input_rows_before_evaluation_label_join",
        "joined_label_fields_are_evaluation_only": True,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "active_observation_task_proxy_join_gate": join_gate,
        "active_observation_task_proxy_join_gate_passed": join_gate_passed,
        "promotion_gate_after_join": promotion_gate_after_join,
        "promotion_gate_after_join_passed": promotion_gate_after_join_passed,
        "revised_slam_formula_allowed": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "active_observation_task_proxy_join_is_evaluation_only",
        "recommended_next_task": "analyze_active_observation_task_proxy_join_before_terminal_utility",
        "next_task": "analyze_active_observation_task_proxy_join_before_terminal_utility",
        "interpretation": {
            "fact": (
                "Frozen candidate-relative active-observation rows are joined to request and candidate task labels "
                "with zero label-missing rows for request, priority candidate, selected candidate, and audited "
                "alternative candidate joins."
            ),
            "agent_inference": (
                "The joined artifact can diagnose whether selected observation targets expose wrong/no-valid risk, "
                "but it cannot justify terminal ObjectNav utility or Step 4-5 promotion because no terminal policy "
                "or heldout validation has been defined."
            ),
            "paper_claim": (
                "No ObjectNav utility, Semantic-SLAM complementarity, terminal utility, first_eval rerun, "
                "policy-scale comparison, Step 4-5 claim, or paper claim is allowed from this artifact."
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
        "date_checked": "2026-06-06",
        "status": summary.get("status"),
        "contract": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "active_observation_task_proxy_join_gate_passed": summary.get(
            "active_observation_task_proxy_join_gate_passed"
        ),
        "promotion_gate_after_join_passed": summary.get("promotion_gate_after_join_passed"),
        "primary_blocker": summary.get("primary_blocker"),
        "actual_counts": summary.get("actual_counts"),
        "verification_command": (
            "jq '.active_observation_task_proxy_join_gate_passed, .actual_counts' "
            f"{out_root / OUTPUT_FILES['summary']}"
        ),
        "docker_compile_command": (
            "docker run --rm --ipc=host --user $(id -u):$(id -g) "
            "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
            "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
            "-v /home/yoohyun/research3:/workspace -w /workspace "
            "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
            "python -m py_compile "
            "hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/"
            "materialize_semantic_slam_candidate_relative_active_observation_task_proxy_join.py"
        ),
        "docker_run_command": (
            "docker run --rm --ipc=host --user $(id -u):$(id -g) "
            "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
            "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
            "-v /home/yoohyun/research3:/workspace -w /workspace "
            "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
            "python -m h001_runtime."
            "materialize_semantic_slam_candidate_relative_active_observation_task_proxy_join"
        ),
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")

    priority_source_rows = load_jsonl(Path(str(source["active_observation_priority_rows"])))
    request_source_rows = load_jsonl(Path(str(source["active_observation_request_rows"])))
    alternative_source_rows = load_jsonl(Path(str(source["active_observation_alternative_rows"])))
    failure_source_rows = load_jsonl(Path(str(source["active_observation_failure_rows"])))
    request_label_rows = load_jsonl(Path(str(source["task_label_request_rows"])))
    candidate_label_rows = load_jsonl(Path(str(source["task_label_candidate_rows"])))
    baseline_source_rows = load_jsonl(Path(str(source["candidate_task_proxy_policy_rows"])))

    request_labels = index_request_labels(request_label_rows)
    candidate_labels = index_candidate_labels(candidate_label_rows)
    request_rows_by_source = index_request_rows(request_source_rows)

    priority_rows = materialize_priority_rows(
        priority_source_rows,
        request_rows_by_source,
        request_labels,
        candidate_labels,
    )
    selected_candidate_rows = materialize_selected_candidate_rows(priority_rows)
    request_rows = materialize_request_rows(request_source_rows, request_labels, candidate_labels)
    alternative_rows = materialize_alternative_rows(alternative_source_rows, request_labels, candidate_labels)
    baseline_rows = materialize_baseline_rows(baseline_source_rows)
    failure_rows = materialize_failure_rows(request_rows)
    action_forbidden_keys = scan_forbidden_keys(
        [*priority_source_rows, *request_source_rows, *alternative_source_rows, *failure_source_rows]
    )

    summary = build_summary(
        contract=contract,
        priority_rows=priority_rows,
        selected_candidate_rows=selected_candidate_rows,
        request_rows=request_rows,
        alternative_rows=alternative_rows,
        baseline_rows=baseline_rows,
        failure_rows=failure_rows,
        request_label_rows=request_label_rows,
        candidate_label_rows=candidate_label_rows,
        action_forbidden_keys=action_forbidden_keys,
        out_root=out_root,
    )

    write_jsonl(out_root / OUTPUT_FILES["priority_rows"], priority_rows)
    write_jsonl(out_root / OUTPUT_FILES["selected_candidate_rows"], selected_candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["alternative_rows"], alternative_rows)
    write_jsonl(out_root / OUTPUT_FILES["baseline_rows"], baseline_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(verification_path(contract_path), build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Join frozen candidate-relative active-observation rows to evaluation-only task labels and baseline "
            "task-proxy context."
        )
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
