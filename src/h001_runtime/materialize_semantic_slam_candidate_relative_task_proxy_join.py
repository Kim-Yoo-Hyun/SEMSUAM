import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_candidate_relative_task_proxy_join.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_candidate_relative_task_proxy_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_candidate_relative_task_proxy_join_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
SOURCE_REQUEST_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")

FORBIDDEN_ACTION_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
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
    "target_detector_evidence_score",
    "target_positive_support",
    "target_semantic_score",
    "target_support_score",
    "wasted_path_proxy_m",
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
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


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


def request_payload(key: Tuple[str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def label_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("episode_key") or ""),
        str(row.get("request_id") or ""),
        str(row.get("query") or ""),
        str(row.get("scene_key") or ""),
    )


def index_request_labels(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str], Mapping[str, Any]]:
    return {label_request_key(row): row for row in rows}


def index_candidate_labels(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        index[label_request_key(row)][str(row.get("candidate_id") or "")] = row
    return dict(index)


def index_candidates_by_source_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        index[source_request_key(row)][candidate_id(row)] = row
    return dict(index)


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


def target_distance_mean(row: Mapping[str, Any]) -> Optional[float]:
    value = row.get("target_distance_from_viewpoint_m")
    if isinstance(value, Mapping):
        return safe_float(value.get("mean"))
    return safe_float(value)


def selected_candidate_label(
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
    req_key: Tuple[str, str, str, str],
    selected_id: Optional[str],
) -> Optional[Mapping[str, Any]]:
    if not selected_id:
        return None
    return (candidate_labels.get(req_key) or {}).get(str(selected_id))


def label_payload(
    *,
    req_label: Optional[Mapping[str, Any]],
    cand_label: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    return {
        "evaluation_only_label_join_available": req_label is not None,
        "evaluation_only_candidate_label_join_available": cand_label is not None,
        "candidate_label_count": safe_int((req_label or {}).get("candidate_label_count"), 0),
        "correct_candidate_count": safe_int((req_label or {}).get("correct_candidate_count"), 0),
        "wrong_candidate_count": safe_int((req_label or {}).get("wrong_candidate_count"), 0),
        "no_valid_candidate_pool": (req_label or {}).get("no_valid_candidate_pool") if req_label else None,
        "candidate_correctness_label": cand_label.get("candidate_correctness_label") if cand_label else None,
        "candidate_wrong_label": cand_label.get("candidate_wrong_label") if cand_label else None,
        "label_usage": "evaluation_only_after_action_freeze",
    }


def proxy_payload(
    *,
    req_label: Optional[Mapping[str, Any]],
    cand_label: Optional[Mapping[str, Any]],
    would_commit: bool,
    travel_cost_m: Optional[float],
) -> Dict[str, Any]:
    correct = bool(cand_label and cand_label.get("candidate_correctness_label") is True)
    wrong = bool(cand_label and cand_label.get("candidate_wrong_label") is True)
    no_valid = bool(req_label and req_label.get("no_valid_candidate_pool") is True)
    success = bool(would_commit and correct)
    wrong_goal = bool(would_commit and wrong)
    no_valid_commit = bool(would_commit and no_valid)
    wasted = travel_cost_m if wrong_goal and travel_cost_m is not None else 0.0
    return {
        "task_proxy_decision_evaluable": req_label is not None,
        "task_proxy_commit_evaluable": bool(would_commit and cand_label is not None),
        "success_commit_proxy_if_committed": success,
        "wrong_goal_visit_proxy_if_committed": wrong_goal,
        "no_valid_commit_proxy_if_committed": no_valid_commit,
        "wasted_path_proxy_m_if_committed": wasted,
    }


def materialize_candidate_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in candidate_rows:
        src_key = source_request_key(row)
        req_key = evaluation_request_key(row)
        req_label = request_labels.get(req_key)
        cand_label = selected_candidate_label(candidate_labels, req_key, candidate_id(row))
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_after_candidate_relative_map_pose_evidence",
                "row_type": "semantic_slam_candidate_relative_task_proxy_candidate",
                "join_key": {**source_request_payload(src_key), "candidate_id": candidate_id(row)},
                **source_request_payload(src_key),
                "candidate_id": candidate_id(row),
                "candidate_count": safe_int(row.get("candidate_count"), 0),
                "ready_candidate_count": safe_int(row.get("ready_candidate_count"), 0),
                "strict_candidate_map_pose_ready": bool(row.get("strict_candidate_map_pose_ready") is True),
                "candidate_map_pose_score_tuple": row.get("candidate_map_pose_score_tuple"),
                "map_pose_score_tuple_rank": row.get("map_pose_score_tuple_rank"),
                "map_pose_score_tuple_tie_count": row.get("map_pose_score_tuple_tie_count"),
                "projection_visible_heading_rank": row.get("projection_visible_heading_rank"),
                "projection_visible_heading_gap_to_best_rival": row.get(
                    "projection_visible_heading_gap_to_best_rival"
                ),
                "pose_heading_rank": row.get("pose_heading_rank"),
                "pose_heading_gap_to_best_rival": row.get("pose_heading_gap_to_best_rival"),
                "target_distance_advantage_m_against_closest_rival": row.get(
                    "target_distance_advantage_m_against_closest_rival"
                ),
                "projection_visible_fraction": row.get("projection_visible_fraction"),
                "projection_status_entropy_proxy": row.get("projection_status_entropy_proxy"),
                "axis_failure_diversity_proxy": row.get("axis_failure_diversity_proxy"),
                "strict_pose_spatial_or_loop_request_ready": row.get("strict_pose_spatial_or_loop_request_ready"),
                "strict_pose_loop_request_ready": row.get("strict_pose_loop_request_ready"),
                "strict_context_request_ready": row.get("strict_context_request_ready"),
                "candidate_overlap_only_request_flag": row.get("candidate_overlap_only_request_flag"),
                "request_candidate_overlap_only_risk": row.get("request_candidate_overlap_only_risk"),
                "separability_tag": row.get("separability_tag"),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
                **label_payload(req_label=req_label, cand_label=cand_label),
                **proxy_payload(
                    req_label=req_label,
                    cand_label=cand_label,
                    would_commit=False,
                    travel_cost_m=target_distance_mean(row),
                ),
            }
        )
    return out


def materialize_request_rows(
    request_rows: Sequence[Mapping[str, Any]],
    candidate_by_source: Mapping[Tuple[str, str, str, str, str], Mapping[str, Mapping[str, Any]]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in request_rows:
        src_key = source_request_key(row)
        req_key = evaluation_request_key(row)
        req_label = request_labels.get(req_key)
        top_id = str(row.get("top_map_pose_tuple_candidate_id") or "")
        top_label = selected_candidate_label(candidate_labels, req_key, top_id)
        top_candidate = (candidate_by_source.get(src_key) or {}).get(top_id)
        top_proxy = proxy_payload(
            req_label=req_label,
            cand_label=top_label,
            would_commit=bool(top_id),
            travel_cost_m=target_distance_mean(top_candidate or {}),
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_after_candidate_relative_map_pose_evidence",
                "row_type": "semantic_slam_candidate_relative_task_proxy_request",
                "join_key": source_request_payload(src_key),
                **source_request_payload(src_key),
                "candidate_count": safe_int(row.get("candidate_count"), 0),
                "ready_candidate_count": safe_int(row.get("ready_candidate_count"), 0),
                "all_candidates_ready": bool(row.get("all_candidates_ready") is True),
                "multi_candidate_all_ready": bool(row.get("multi_candidate_all_ready") is True),
                "top_map_pose_tuple_candidate_id": top_id,
                "top_map_pose_tuple": row.get("top_map_pose_tuple"),
                "top_map_pose_tuple_tie_count": safe_int(row.get("top_map_pose_tuple_tie_count"), 0),
                "top_map_pose_tuple_would_commit_if_terminal_policy_existed": bool(top_id),
                "separability_status": row.get("separability_status"),
                "candidate_separability_tag_counts": row.get("candidate_separability_tag_counts"),
                "pose_graph_proxy_ready": bool(row.get("pose_graph_proxy_ready") is True),
                "pose_graph_edge_reason_counts": row.get("pose_graph_edge_reason_counts"),
                "request_candidate_overlap_only_risk": bool(row.get("request_candidate_overlap_only_risk") is True),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
                "top_candidate_label_usage": "evaluation_only_after_action_freeze",
                "top_candidate_label_join_available": top_label is not None,
                "top_candidate_correctness_label": top_label.get("candidate_correctness_label") if top_label else None,
                "top_candidate_wrong_label": top_label.get("candidate_wrong_label") if top_label else None,
                **label_payload(req_label=req_label, cand_label=top_label),
                **top_proxy,
            }
        )
    return out


def materialize_alternative_rows(
    alternative_rows: Sequence[Mapping[str, Any]],
    candidate_by_source: Mapping[Tuple[str, str, str, str, str], Mapping[str, Mapping[str, Any]]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in alternative_rows:
        src_key = source_request_key(row)
        req_key = evaluation_request_key(row)
        req_label = request_labels.get(req_key)
        selected_id = row.get("audit_selected_candidate_id")
        selected_id = str(selected_id) if selected_id else None
        selected = (candidate_by_source.get(src_key) or {}).get(selected_id or "")
        cand_label = selected_candidate_label(candidate_labels, req_key, selected_id)
        would_commit = bool(row.get("audit_would_commit_if_terminal_policy_existed") is True)
        proxy = proxy_payload(
            req_label=req_label,
            cand_label=cand_label,
            would_commit=would_commit,
            travel_cost_m=target_distance_mean(selected or {}),
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_after_candidate_relative_map_pose_evidence",
                "row_type": "semantic_slam_candidate_relative_task_proxy_alternative_audit",
                "join_key": dict(row.get("join_key") or {}),
                **source_request_payload(src_key),
                "alternative_id": row.get("alternative_id"),
                "alternative_role": "evaluation_only_diagnostic_after_action_freeze",
                "alternative_allowed_as_terminal_action": False,
                "fallback_shortcut_forbidden": bool(row.get("fallback_shortcut_forbidden") is True),
                "audit_selection_reason": row.get("audit_selection_reason"),
                "audit_selected_candidate_id": selected_id,
                "audit_would_commit_if_terminal_policy_existed": would_commit,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
                **label_payload(req_label=req_label, cand_label=cand_label),
                **proxy,
            }
        )
    return out


def materialize_baseline_policy_rows(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        copied = dict(row)
        copied["schema_version"] = SCHEMA_VERSION
        copied["validation_stage"] = "baseline_policy_context_for_candidate_relative_task_proxy_join"
        copied["row_type"] = "semantic_slam_candidate_relative_task_proxy_baseline_policy_context"
        copied["baseline_context_only"] = True
        copied["candidate_relative_action_source"] = False
        copied["terminal_commit"] = False
        copied["candidate_commit"] = False
        copied["candidate_rejection"] = False
        copied["uses_gt_for_action"] = False
        copied["uses_gt_for_analysis"] = True
        copied["paper_claim_allowed"] = False
        out.append(copied)
    return out


def failure_tags_for_request(row: Mapping[str, Any]) -> List[str]:
    tags = ["terminal_commit_blocked_by_contract", "formula_revision_blocked_by_task_proxy_risk"]
    if row.get("evaluation_only_label_join_available") is not True:
        tags.append("request_label_missing")
    if row.get("top_candidate_label_join_available") is not True:
        tags.append("top_map_pose_candidate_label_missing")
    if row.get("wrong_goal_visit_proxy_if_committed") is True:
        tags.append("top_map_pose_wrong_goal_risk")
    if row.get("no_valid_commit_proxy_if_committed") is True:
        tags.append("top_map_pose_no_valid_risk")
    if row.get("success_commit_proxy_if_committed") is True:
        tags.append("top_map_pose_success_if_committed_but_terminal_blocked")
    if row.get("separability_status") == "candidate_relative_unique_top_nonterminal":
        tags.append("candidate_relative_unique_top_audited")
        if row.get("wrong_goal_visit_proxy_if_committed") is True or row.get("no_valid_commit_proxy_if_committed") is True:
            tags.append("unique_top_still_wrong_or_no_valid")
    else:
        tags.append("tie_or_saturation_requires_revision")
    if row.get("request_candidate_overlap_only_risk") is True:
        tags.append("candidate_overlap_only_pose_graph_context")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "request_label_missing",
        "top_map_pose_candidate_label_missing",
        "top_map_pose_no_valid_risk",
        "top_map_pose_wrong_goal_risk",
        "unique_top_still_wrong_or_no_valid",
        "tie_or_saturation_requires_revision",
    ):
        if tag in tags:
            return tag
    return "terminal_commit_blocked_by_contract"


def materialize_failure_rows(request_join_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in request_join_rows:
        src_key = source_request_key(row)
        tags = failure_tags_for_request(row)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_task_proxy_after_candidate_relative_map_pose_evidence",
                "row_type": "semantic_slam_candidate_relative_task_proxy_failure",
                "join_key": source_request_payload(src_key),
                **source_request_payload(src_key),
                "primary_failure_or_blocker": primary_failure(tags),
                "failure_tags": tags,
                "separability_status": row.get("separability_status"),
                "top_map_pose_tuple_candidate_id": row.get("top_map_pose_tuple_candidate_id"),
                "top_candidate_correctness_label": row.get("top_candidate_correctness_label"),
                "top_candidate_wrong_label": row.get("top_candidate_wrong_label"),
                "wrong_goal_visit_proxy_if_committed": row.get("wrong_goal_visit_proxy_if_committed"),
                "no_valid_commit_proxy_if_committed": row.get("no_valid_commit_proxy_if_committed"),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return out


def alternative_outcomes(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for alt_id in sorted({str(row.get("alternative_id") or "") for row in rows}):
        subset = [row for row in rows if row.get("alternative_id") == alt_id]
        result[alt_id] = {
            "rows": len(subset),
            "would_commit_rows": sum(
                1 for row in subset if row.get("audit_would_commit_if_terminal_policy_existed") is True
            ),
            "success_rows": sum(1 for row in subset if row.get("success_commit_proxy_if_committed") is True),
            "wrong_rows": sum(1 for row in subset if row.get("wrong_goal_visit_proxy_if_committed") is True),
            "no_valid_rows": sum(1 for row in subset if row.get("no_valid_commit_proxy_if_committed") is True),
            "forbidden_shortcut_rows": sum(1 for row in subset if row.get("fallback_shortcut_forbidden") is True),
        }
    return result


def counts_by_request_status(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}
    for status in sorted({str(row.get("separability_status") or "") for row in rows}):
        subset = [row for row in rows if row.get("separability_status") == status]
        result[status] = {
            "rows": len(subset),
            "top_correct_rows": sum(1 for row in subset if row.get("success_commit_proxy_if_committed") is True),
            "top_wrong_rows": sum(1 for row in subset if row.get("wrong_goal_visit_proxy_if_committed") is True),
            "top_no_valid_rows": sum(1 for row in subset if row.get("no_valid_commit_proxy_if_committed") is True),
        }
    return result


def counts_by_candidate_tag(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, int]]:
    result: Dict[str, Dict[str, int]] = {}
    for tag in sorted({str(row.get("separability_tag") or "") for row in rows}):
        subset = [row for row in rows if row.get("separability_tag") == tag]
        result[tag] = {
            "rows": len(subset),
            "correct_rows": sum(1 for row in subset if row.get("candidate_correctness_label") is True),
            "wrong_rows": sum(1 for row in subset if row.get("candidate_wrong_label") is True),
            "no_valid_rows": sum(1 for row in subset if row.get("no_valid_candidate_pool") is True),
        }
    return result


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


def build_summary(
    *,
    contract: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    alternative_rows: Sequence[Mapping[str, Any]],
    baseline_policy_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    request_label_rows: Sequence[Mapping[str, Any]],
    candidate_label_rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
    out_root: Path,
) -> Dict[str, Any]:
    expected = contract.get("expected_future_outputs")
    expected = expected if isinstance(expected, Mapping) else {}
    join_gate_contract = contract.get("join_gate")
    join_gate_contract = join_gate_contract if isinstance(join_gate_contract, Mapping) else {}
    promotion_contract = contract.get("promotion_gate_after_join")
    promotion_contract = promotion_contract if isinstance(promotion_contract, Mapping) else {}

    source_candidate_label_missing = sum(
        1 for row in candidate_rows if row.get("evaluation_only_candidate_label_join_available") is not True
    )
    source_request_label_missing = sum(
        1 for row in request_rows if row.get("evaluation_only_label_join_available") is not True
    )
    top_wrong_rows = sum(1 for row in request_rows if row.get("wrong_goal_visit_proxy_if_committed") is True)
    top_no_valid_rows = sum(1 for row in request_rows if row.get("no_valid_commit_proxy_if_committed") is True)
    unique_subset = [
        row for row in request_rows if row.get("separability_status") == "candidate_relative_unique_top_nonterminal"
    ]
    unique_wrong_rows = sum(1 for row in unique_subset if row.get("wrong_goal_visit_proxy_if_committed") is True)
    unique_no_valid_rows = sum(1 for row in unique_subset if row.get("no_valid_commit_proxy_if_committed") is True)
    action_rows = [*candidate_rows, *request_rows, *alternative_rows, *failure_rows]
    terminal_commit_rows = sum(1 for row in action_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in action_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in action_rows if row.get("candidate_rejection") is True)

    actual_counts = {
        "candidate_rows": len(candidate_rows),
        "request_rows": len(request_rows),
        "alternative_rows": len(alternative_rows),
        "baseline_policy_rows": len(baseline_policy_rows),
        "failure_taxonomy_rows": len(failure_rows),
        "request_label_rows": len(request_label_rows),
        "candidate_label_rows": len(candidate_label_rows),
        "source_request_label_join_rows": len(request_rows) - source_request_label_missing,
        "source_request_label_missing_rows": source_request_label_missing,
        "source_candidate_label_join_rows": len(candidate_rows) - source_candidate_label_missing,
        "source_candidate_label_missing_rows": source_candidate_label_missing,
        "source_candidate_label_correct_rows": sum(
            1 for row in candidate_rows if row.get("candidate_correctness_label") is True
        ),
        "source_candidate_label_wrong_rows": sum(1 for row in candidate_rows if row.get("candidate_wrong_label") is True),
        "source_candidate_no_valid_rows": sum(1 for row in candidate_rows if row.get("no_valid_candidate_pool") is True),
        "source_request_no_valid_rows": sum(1 for row in request_rows if row.get("no_valid_candidate_pool") is True),
        "top_map_pose_tuple_label_available_rows": sum(
            1 for row in request_rows if row.get("top_candidate_label_join_available") is True
        ),
        "top_map_pose_tuple_correct_rows": sum(
            1 for row in request_rows if row.get("success_commit_proxy_if_committed") is True
        ),
        "top_map_pose_tuple_wrong_rows": top_wrong_rows,
        "top_map_pose_tuple_no_valid_request_rows": top_no_valid_rows,
        "candidate_relative_unique_top_rows": len(unique_subset),
        "candidate_relative_unique_top_correct_rows": sum(
            1 for row in unique_subset if row.get("success_commit_proxy_if_committed") is True
        ),
        "candidate_relative_unique_top_wrong_rows": unique_wrong_rows,
        "candidate_relative_unique_top_no_valid_rows": unique_no_valid_rows,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
    }
    expected_count_mismatches = {
        "candidate_rows": {
            "expected": expected.get("expected_candidate_rows"),
            "actual": actual_counts["candidate_rows"],
        }
        if expected.get("expected_candidate_rows") != actual_counts["candidate_rows"]
        else None,
        "request_rows": {
            "expected": expected.get("expected_request_rows"),
            "actual": actual_counts["request_rows"],
        }
        if expected.get("expected_request_rows") != actual_counts["request_rows"]
        else None,
        "alternative_rows": {
            "expected": expected.get("expected_alternative_rows"),
            "actual": actual_counts["alternative_rows"],
        }
        if expected.get("expected_alternative_rows") != actual_counts["alternative_rows"]
        else None,
        "baseline_policy_rows": {
            "expected": expected.get("expected_baseline_policy_rows"),
            "actual": actual_counts["baseline_policy_rows"],
        }
        if expected.get("expected_baseline_policy_rows") != actual_counts["baseline_policy_rows"]
        else None,
    }
    expected_count_mismatches = {key: value for key, value in expected_count_mismatches.items() if value}

    join_gate = {
        "candidate_rows_match_expected": actual_counts["candidate_rows"]
        == safe_int(expected.get("expected_candidate_rows"), actual_counts["candidate_rows"]),
        "request_rows_match_expected": actual_counts["request_rows"]
        == safe_int(expected.get("expected_request_rows"), actual_counts["request_rows"]),
        "alternative_rows_match_expected": actual_counts["alternative_rows"]
        == safe_int(expected.get("expected_alternative_rows"), actual_counts["alternative_rows"]),
        "baseline_policy_rows_match_expected": actual_counts["baseline_policy_rows"]
        == safe_int(expected.get("expected_baseline_policy_rows"), actual_counts["baseline_policy_rows"]),
        "failure_taxonomy_rows_minimum_passed": actual_counts["failure_taxonomy_rows"]
        >= safe_int(expected.get("expected_failure_taxonomy_rows_minimum"), 0),
        "source_candidate_label_join_rows_min_passed": actual_counts["source_candidate_label_join_rows"]
        >= safe_int(join_gate_contract.get("source_candidate_label_join_rows_min"), 0),
        "source_request_label_join_rows_min_passed": actual_counts["source_request_label_join_rows"]
        >= safe_int(join_gate_contract.get("source_request_label_join_rows_min"), 0),
        "source_candidate_label_missing_rows_passed": source_candidate_label_missing
        <= safe_int(join_gate_contract.get("source_candidate_label_missing_rows_max"), source_candidate_label_missing),
        "source_request_label_missing_rows_passed": source_request_label_missing
        <= safe_int(join_gate_contract.get("source_request_label_missing_rows_max"), source_request_label_missing),
        "action_evidence_forbidden_keys_passed": len(action_forbidden_keys)
        <= safe_int(join_gate_contract.get("action_evidence_forbidden_key_count_max"), len(action_forbidden_keys)),
        "uses_gt_for_action_passed": not any(row.get("uses_gt_for_action") is True for row in action_rows),
        "uses_gt_for_analysis_passed": all(row.get("uses_gt_for_analysis") is True for row in action_rows),
        "terminal_commit_rows_passed": terminal_commit_rows
        <= safe_int(join_gate_contract.get("terminal_commit_rows_max"), terminal_commit_rows),
        "candidate_commit_rows_passed": candidate_commit_rows
        <= safe_int(join_gate_contract.get("candidate_commit_rows_max"), candidate_commit_rows),
        "candidate_rejection_rows_passed": candidate_rejection_rows
        <= safe_int(join_gate_contract.get("candidate_rejection_rows_max"), candidate_rejection_rows),
        "paper_claim_allowed_passed": not any(row.get("paper_claim_allowed") is True for row in action_rows),
    }
    join_gate_passed = all(join_gate.values()) and not expected_count_mismatches
    promotion_gate = {
        "join_gate_must_pass": join_gate_passed,
        "top_candidate_wrong_rows_passed": top_wrong_rows
        <= safe_int(promotion_contract.get("top_candidate_wrong_rows_max"), top_wrong_rows),
        "top_candidate_no_valid_request_rows_passed": top_no_valid_rows
        <= safe_int(promotion_contract.get("top_candidate_no_valid_request_rows_max"), top_no_valid_rows),
        "candidate_relative_unique_top_wrong_rows_passed": unique_wrong_rows
        <= safe_int(promotion_contract.get("candidate_relative_unique_top_wrong_rows_max"), unique_wrong_rows),
        "candidate_relative_unique_top_no_valid_rows_passed": unique_no_valid_rows
        <= safe_int(promotion_contract.get("candidate_relative_unique_top_no_valid_rows_max"), unique_no_valid_rows),
        "simpler_alternatives_wrong_rows_reported": True,
        "heldout_or_fresh_validation_required_before_paper_claim": False,
        "revised_slam_formula_allowed_from_contract_only": False,
    }
    promotion_gate_passed = all(promotion_gate.values())
    primary_blocker = None
    if not join_gate_passed:
        primary_blocker = "candidate_relative_task_proxy_join_gate_failed"
    elif not promotion_gate_passed:
        if not promotion_gate["top_candidate_wrong_rows_passed"]:
            primary_blocker = "candidate_relative_top_rule_wrong_goal_risk"
        elif not promotion_gate["top_candidate_no_valid_request_rows_passed"]:
            primary_blocker = "candidate_relative_top_rule_no_valid_risk"
        elif not promotion_gate["candidate_relative_unique_top_wrong_rows_passed"]:
            primary_blocker = "candidate_relative_unique_top_wrong_goal_risk"
        else:
            primary_blocker = "candidate_relative_task_proxy_promotion_gate_failed"

    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "task_proxy_join_gate_passed_promotion_blocked"
        if join_gate_passed and not promotion_gate_passed
        else "completed"
        if join_gate_passed
        else "failed",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "candidate_rows": "semantic_slam_candidate_relative_task_proxy_candidate_rows.jsonl",
            "request_rows": "semantic_slam_candidate_relative_task_proxy_request_rows.jsonl",
            "alternative_rows": "semantic_slam_candidate_relative_task_proxy_alternative_rows.jsonl",
            "baseline_policy_rows": "semantic_slam_candidate_relative_task_proxy_baseline_policy_rows.jsonl",
            "failure_taxonomy_rows": "semantic_slam_candidate_relative_task_proxy_failure_rows.jsonl",
            "summary": "semantic_slam_candidate_relative_task_proxy_summary.json",
        },
        "source_files": contract.get("source", {}),
        "actual_counts": actual_counts,
        "expected_count_mismatches": expected_count_mismatches,
        "request_separability_task_proxy_counts": counts_by_request_status(request_rows),
        "candidate_separability_task_proxy_counts": counts_by_candidate_tag(candidate_rows),
        "alternative_outcomes": alternative_outcomes(alternative_rows),
        "baseline_policy_counts": baseline_policy_counts(baseline_policy_rows),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "task_proxy_join_gate": join_gate,
        "task_proxy_join_gate_passed": join_gate_passed,
        "promotion_gate_after_join": promotion_gate,
        "promotion_gate_after_join_passed": promotion_gate_passed,
        "revised_slam_formula_allowed": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": primary_blocker,
        "recommended_next_task": "close_or_revise_candidate_relative_semantic_slam_map_pose_path"
        if join_gate_passed and not promotion_gate_passed
        else "repair_candidate_relative_task_proxy_join_materializer",
        "interpretation": {
            "fact": (
                "Candidate-relative map/pose evidence rows are joined to evaluation-only task labels with full "
                "source-row coverage while preserving zero terminal commits in the candidate-relative action rows."
            ),
            "agent_inference": (
                "The top candidate-relative map/pose rule is unsafe for terminal use because it still selects "
                "wrong or no-valid candidates after the evaluation-only join."
            ),
            "paper_claim": (
                "No Semantic-SLAM complementarity, ObjectNav utility, SLAM benefit, terminal utility, first_eval, "
                "policy-scale comparison, or paper claim is allowed from this artifact."
            ),
        },
        "next_task": "close_or_revise_candidate_relative_semantic_slam_map_pose_path",
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")

    candidate_source_rows = load_jsonl(Path(str(source["candidate_relative_candidate_rows"])))
    request_source_rows = load_jsonl(Path(str(source["candidate_relative_request_rows"])))
    alternative_source_rows = load_jsonl(Path(str(source["candidate_relative_alternative_rows"])))
    request_label_rows = load_jsonl(Path(str(source["task_label_request_rows"])))
    candidate_label_rows = load_jsonl(Path(str(source["task_label_candidate_rows"])))
    baseline_policy_source_rows = load_jsonl(Path(str(source["candidate_task_proxy_policy_rows"])))

    request_labels = index_request_labels(request_label_rows)
    candidate_labels = index_candidate_labels(candidate_label_rows)
    candidate_by_source = index_candidates_by_source_request(candidate_source_rows)

    candidate_rows = materialize_candidate_rows(candidate_source_rows, request_labels, candidate_labels)
    request_rows = materialize_request_rows(
        request_source_rows, candidate_by_source, request_labels, candidate_labels
    )
    alternative_rows = materialize_alternative_rows(
        alternative_source_rows, candidate_by_source, request_labels, candidate_labels
    )
    baseline_policy_rows = materialize_baseline_policy_rows(baseline_policy_source_rows)
    failure_rows = materialize_failure_rows(request_rows)
    action_forbidden_keys = scan_forbidden_keys([*candidate_source_rows, *request_source_rows, *alternative_source_rows])
    summary = build_summary(
        contract=contract,
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        alternative_rows=alternative_rows,
        baseline_policy_rows=baseline_policy_rows,
        failure_rows=failure_rows,
        request_label_rows=request_label_rows,
        candidate_label_rows=candidate_label_rows,
        action_forbidden_keys=action_forbidden_keys,
        out_root=out_root,
    )

    write_jsonl(out_root / "semantic_slam_candidate_relative_task_proxy_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "semantic_slam_candidate_relative_task_proxy_request_rows.jsonl", request_rows)
    write_jsonl(out_root / "semantic_slam_candidate_relative_task_proxy_alternative_rows.jsonl", alternative_rows)
    write_jsonl(out_root / "semantic_slam_candidate_relative_task_proxy_baseline_policy_rows.jsonl", baseline_policy_rows)
    write_jsonl(out_root / "semantic_slam_candidate_relative_task_proxy_failure_rows.jsonl", failure_rows)
    write_json(out_root / "semantic_slam_candidate_relative_task_proxy_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join candidate-relative Semantic-SLAM map/pose evidence rows to evaluation-only task proxies."
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
