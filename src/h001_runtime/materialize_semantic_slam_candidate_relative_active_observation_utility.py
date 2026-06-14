import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_candidate_relative_active_observation_utility.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_candidate_relative_active_observation_utility_v1.json"
)
MAP_POSE_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_candidate_relative_map_pose_evidence_v1"
TASK_PROXY_SUMMARY_DEFAULT = (
    "local_dataset/runs/h001_semantic_slam_candidate_relative_task_proxy_join_v1/"
    "semantic_slam_candidate_relative_task_proxy_summary.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_utility_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
SOURCE_REQUEST_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

REQUIRED_ALTERNATIVES = (
    "defer_all",
    "current_unique_ready",
    "top_map_pose_tuple",
    "top_projection_visible_heading",
    "semantic_rank_fallback_forbidden",
    "detector_score_fallback_forbidden",
)

REQUIRED_FAILURE_TAGS = (
    "candidate_relative_top_rule_closed",
    "active_observation_required_before_terminal_utility",
    "candidate_overlap_only_context_gap",
    "tie_or_saturation_requires_observation",
    "wrong_or_no_valid_risk_requires_evaluation_join",
)

FORBIDDEN_ACTION_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "top_candidate_correctness_label",
    "top_candidate_wrong_label",
    "correct_candidate_count",
    "wrong_candidate_count",
    "candidate_label_count",
    "no_valid_candidate_pool",
    "success_commit_proxy_if_committed",
    "wrong_goal_visit_proxy_if_committed",
    "no_valid_commit_proxy_if_committed",
    "wasted_path_proxy_m_if_committed",
    "task_proxy_commit_evaluable",
    "task_proxy_decision_evaluable",
    "evaluation_only_label_join_available",
    "evaluation_only_candidate_label_join_available",
    "evaluation_only_variant_outcomes",
    "oracle",
    "ground_truth",
    "gt",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "detector_score",
    "semantic_rank",
    "semantic_score",
    "shortest_path_distance",
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


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


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


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def target_distance_mean(row: Mapping[str, Any]) -> Optional[float]:
    value = row.get("target_distance_from_viewpoint_m")
    if isinstance(value, Mapping):
        return safe_float(value.get("mean"))
    return safe_float(value)


def projection_visible_fraction(row: Mapping[str, Any]) -> float:
    counts = row.get("projection_status_counts")
    if not isinstance(counts, Mapping):
        return safe_float(row.get("projection_visible_fraction"), 0.0) or 0.0
    total = sum(safe_int(value, 0) for value in counts.values())
    return ratio(safe_int(counts.get("visible"), 0), total)


def normalized_entropy(row: Mapping[str, Any]) -> float:
    value = safe_float(row.get("projection_status_entropy_proxy"))
    if value is not None:
        return clamp(value / 2.0)
    counts = row.get("projection_status_counts")
    if not isinstance(counts, Mapping):
        return 0.0
    values = [safe_int(value, 0) for value in counts.values()]
    total = sum(value for value in values if value > 0)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in values:
        if value <= 0:
            continue
        p = value / total
        entropy -= p * math.log(p, 2)
    return clamp(entropy / 2.0)


def strict_fraction(row: Mapping[str, Any], name: str) -> float:
    fractions = row.get("strict_edge_variant_largest_component_fraction")
    if not isinstance(fractions, Mapping):
        return 0.0
    return safe_float(fractions.get(name), 0.0) or 0.0


def score_tuple(row: Mapping[str, Any]) -> Tuple[float, ...]:
    values = row.get("candidate_map_pose_score_tuple")
    if not isinstance(values, list):
        return ()
    return tuple(safe_float(value, 0.0) or 0.0 for value in values)


def index_by_source_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        index[source_request_key(row)].append(row)
    return dict(index)


def index_one_by_source_request(
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


def candidate_sort_key(row: Mapping[str, Any]) -> Tuple[Tuple[float, ...], int, int, str]:
    return (
        score_tuple(row),
        safe_int(row.get("projection_visible_heading_count"), 0),
        safe_int(row.get("pose_heading_count"), 0),
        candidate_id(row),
    )


def top_candidates_for_action(rows: Sequence[Mapping[str, Any]], count: int) -> List[str]:
    ordered = sorted(rows, key=candidate_sort_key, reverse=True)
    return [candidate_id(row) for row in ordered[:count] if candidate_id(row)]


def request_has_context_gap(request_row: Mapping[str, Any]) -> bool:
    return bool(
        request_row.get("candidate_overlap_only_request_flag") is True
        or request_row.get("request_candidate_overlap_only_risk") is True
        or request_row.get("pose_graph_candidate_overlap_only_request_flag") is True
        or request_row.get("strict_pose_spatial_or_loop_request_ready") is not True
        or request_row.get("strict_context_request_ready") is not True
    )


def rival_ambiguity(row: Mapping[str, Any], request_row: Mapping[str, Any]) -> float:
    status = str(request_row.get("separability_status") or "")
    tag = str(row.get("separability_tag") or "")
    rank = safe_int(row.get("map_pose_score_tuple_rank"), 999)
    tie_count = safe_int(row.get("map_pose_score_tuple_tie_count"), 0)
    projection_gap = safe_float(row.get("projection_visible_heading_gap_to_best_rival"), 0.0) or 0.0
    pose_gap = safe_float(row.get("pose_heading_gap_to_best_rival"), 0.0) or 0.0
    distance_gap = safe_float(row.get("target_distance_advantage_m_against_closest_rival"), 0.0) or 0.0
    if "tie_or_saturation" in status or tie_count > 1:
        base = 1.0
    elif rank <= 2:
        base = 0.82
    elif "weak_or_partial" in tag:
        base = 0.58
    else:
        base = 0.45
    weak_gap_count = sum(1 for value in (projection_gap, pose_gap, distance_gap) if value <= 0.0)
    return clamp(base + 0.06 * weak_gap_count)


def pose_context_gap(row: Mapping[str, Any], request_row: Mapping[str, Any]) -> float:
    if request_has_context_gap(request_row):
        best_non_candidate_fraction = max(
            strict_fraction(row, "pose_spatial_or_loop"),
            strict_fraction(row, "pose_loop"),
            strict_fraction(row, "target_context"),
            strict_fraction(row, "map_pose_context_no_candidate"),
        )
        return clamp(max(0.70, 1.0 - best_non_candidate_fraction))
    return 0.15


def projection_uncertainty(row: Mapping[str, Any]) -> float:
    visible_fraction = projection_visible_fraction(row)
    entropy = normalized_entropy(row)
    axis_diversity = clamp((safe_int(row.get("axis_failure_diversity_proxy"), 0)) / 4.0)
    heading_gap = safe_float(row.get("projection_visible_heading_gap_to_best_rival"), 0.0) or 0.0
    gap_risk = 1.0 if heading_gap <= 0.0 else clamp(1.0 / (1.0 + heading_gap))
    return clamp(0.40 * (1.0 - visible_fraction) + 0.25 * entropy + 0.20 * axis_diversity + 0.15 * gap_risk)


def saturation_risk(request_row: Mapping[str, Any]) -> float:
    candidate_count = safe_int(request_row.get("candidate_count"), 0)
    ready_count = safe_int(request_row.get("ready_candidate_count"), 0)
    if request_row.get("multi_candidate_all_ready") is True:
        return 1.0
    if request_row.get("all_candidates_ready") is True:
        return 0.80
    if candidate_count > 0:
        return clamp(ready_count / candidate_count)
    return 0.0


def observation_cost_proxy(row: Mapping[str, Any]) -> float:
    distance = target_distance_mean(row)
    if distance is None:
        return 1.0
    readiness_penalty = 0.0 if row.get("physical_viewpoint_position_ready") is True else 0.25
    return clamp(distance / 5.0 + readiness_penalty)


def utility_terms(row: Mapping[str, Any], request_row: Mapping[str, Any]) -> Dict[str, float]:
    return {
        "RivalAmbiguity": rival_ambiguity(row, request_row),
        "PoseContextGap": pose_context_gap(row, request_row),
        "ProjectionUncertainty": projection_uncertainty(row),
        "SaturationRisk": saturation_risk(request_row),
        "ObservationCostProxy": observation_cost_proxy(row),
    }


def utility_score(terms: Mapping[str, float]) -> float:
    raw = (
        0.30 * terms["RivalAmbiguity"]
        + 0.25 * terms["PoseContextGap"]
        + 0.25 * terms["ProjectionUncertainty"]
        + 0.20 * terms["SaturationRisk"]
        - 0.10 * terms["ObservationCostProxy"]
    )
    return round(clamp(raw), 6)


def request_risk_tags(request_row: Mapping[str, Any]) -> List[str]:
    tags = [
        "candidate_relative_top_rule_closed",
        "active_observation_required_before_terminal_utility",
        "wrong_or_no_valid_risk_requires_evaluation_join",
    ]
    if request_has_context_gap(request_row):
        tags.append("candidate_overlap_only_context_gap")
    if request_row.get("multi_candidate_all_ready") is True or "tie_or_saturation" in str(
        request_row.get("separability_status") or ""
    ):
        tags.append("tie_or_saturation_requires_observation")
    if request_row.get("all_candidates_ready") is True:
        tags.append("all_candidates_ready_saturation")
    if request_row.get("separability_status"):
        tags.append(str(request_row.get("separability_status")))
    return sorted(set(tags))


def candidate_risk_tags(
    candidate_row: Mapping[str, Any], request_row: Mapping[str, Any], terms: Mapping[str, float]
) -> List[str]:
    tags = request_risk_tags(request_row)
    if safe_int(candidate_row.get("map_pose_score_tuple_rank"), 999) <= 2:
        tags.append("top_or_rival_candidate_for_reobservation")
    if terms["ProjectionUncertainty"] >= 0.65:
        tags.append("projection_uncertainty_high")
    if terms["PoseContextGap"] >= 0.70:
        tags.append("pose_context_gap_high")
    if terms["ObservationCostProxy"] >= 0.60:
        tags.append("observation_cost_high")
    return sorted(set(tags))


def selected_request_action(request_row: Mapping[str, Any], candidate_rows: Sequence[Mapping[str, Any]]) -> Tuple[str, List[str]]:
    candidate_count = safe_int(request_row.get("candidate_count"), len(candidate_rows))
    if request_has_context_gap(request_row):
        return "observe_request_context", top_candidates_for_action(candidate_rows, min(2, candidate_count))
    if "tie_or_saturation" in str(request_row.get("separability_status") or ""):
        return "observe_candidate_pair", top_candidates_for_action(candidate_rows, min(2, candidate_count))
    if candidate_count > 1:
        return "observe_candidate_pair", top_candidates_for_action(candidate_rows, 2)
    if candidate_count == 1:
        return "observe_candidate", top_candidates_for_action(candidate_rows, 1)
    return "defer_observation", []


def candidate_observation_action(
    candidate_row: Mapping[str, Any], request_action: str, selected_ids: Sequence[str], score: float
) -> str:
    cid = candidate_id(candidate_row)
    if request_action == "observe_request_context":
        return "observe_request_context"
    if cid in selected_ids and request_action == "observe_candidate_pair":
        return "observe_candidate_pair"
    if cid in selected_ids and request_action == "observe_candidate":
        return "observe_candidate"
    if score >= 0.60:
        return "observe_candidate"
    return "audit_only"


def alternative_selection(
    alternative_id: str, request_row: Mapping[str, Any], candidate_rows: Sequence[Mapping[str, Any]]
) -> Tuple[Optional[str], str]:
    ordered = sorted(candidate_rows, key=candidate_sort_key, reverse=True)
    if alternative_id == "defer_all":
        return None, "safety_lower_bound"
    if alternative_id == "current_unique_ready":
        if request_row.get("current_selector_action") == "commit" and len(ordered) == 1:
            return candidate_id(ordered[0]), "single_candidate_unique_ready"
        return None, str(request_row.get("current_selector_missing_reason") or "not_unique_ready")
    if alternative_id == "top_map_pose_tuple":
        return str(request_row.get("top_map_pose_tuple_candidate_id") or candidate_id(ordered[0] if ordered else {})), (
            "closed_unsafe_terminal_selector_audit_only"
        )
    if alternative_id == "top_projection_visible_heading":
        projection_ordered = sorted(
            candidate_rows,
            key=lambda row: (
                safe_int(row.get("projection_visible_heading_count"), 0),
                safe_int(row.get("pose_heading_count"), 0),
                score_tuple(row),
                candidate_id(row),
            ),
            reverse=True,
        )
        return candidate_id(projection_ordered[0] if projection_ordered else {}), (
            "closed_projection_only_terminal_selector_audit_only"
        )
    if alternative_id == "semantic_rank_fallback_forbidden":
        return None, "forbidden_semantic_shortcut"
    if alternative_id == "detector_score_fallback_forbidden":
        return None, "forbidden_detector_shortcut"
    return None, "unknown_alternative"


def build_rows(
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    candidates_by_request = index_by_source_request(candidate_rows)
    priority_out: List[Dict[str, Any]] = []
    request_out: List[Dict[str, Any]] = []
    alternative_out: List[Dict[str, Any]] = []
    failure_out: List[Dict[str, Any]] = []

    for request_row in sorted(request_rows, key=source_request_key):
        key = source_request_key(request_row)
        payload = source_request_payload(key)
        candidates = sorted(candidates_by_request.get(key, []), key=candidate_id)
        action, selected_ids = selected_request_action(request_row, candidates)
        request_tags = request_risk_tags(request_row)
        scored_candidates: List[Tuple[float, Mapping[str, Any], Dict[str, float]]] = []
        for candidate_row in candidates:
            terms = utility_terms(candidate_row, request_row)
            score = utility_score(terms)
            scored_candidates.append((score, candidate_row, terms))

        selected_scores = {
            candidate_id(row): score
            for score, row, _terms in sorted(scored_candidates, key=lambda item: item[0], reverse=True)
        }
        for score, candidate_row, terms in sorted(
            scored_candidates, key=lambda item: (item[0], candidate_sort_key(item[1])), reverse=True
        ):
            cid = candidate_id(candidate_row)
            priority_out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "candidate_relative_active_observation_utility_nonterminal",
                    "row_type": "semantic_slam_candidate_relative_active_observation_priority",
                    "join_key": {**payload, "candidate_id": cid},
                    **payload,
                    "candidate_id": cid,
                    "candidate_count": safe_int(request_row.get("candidate_count"), len(candidates)),
                    "ready_candidate_count": safe_int(request_row.get("ready_candidate_count"), 0),
                    "separability_status": request_row.get("separability_status"),
                    "separability_tag": candidate_row.get("separability_tag"),
                    "selected_for_request_action": cid in selected_ids,
                    "request_selected_candidate_ids": list(selected_ids),
                    "observation_action": candidate_observation_action(candidate_row, action, selected_ids, score),
                    "utility_score": score,
                    "utility_terms": terms,
                    "risk_tags": candidate_risk_tags(candidate_row, request_row, terms),
                    "map_pose_score_tuple_rank": candidate_row.get("map_pose_score_tuple_rank"),
                    "map_pose_score_tuple_tie_count": candidate_row.get("map_pose_score_tuple_tie_count"),
                    "projection_visible_fraction": round(projection_visible_fraction(candidate_row), 6),
                    "projection_visible_heading_rank": candidate_row.get("projection_visible_heading_rank"),
                    "pose_heading_rank": candidate_row.get("pose_heading_rank"),
                    "target_distance_mean_m": target_distance_mean(candidate_row),
                    "terminal_commit": False,
                    "candidate_commit": False,
                    "candidate_rejection": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )

        request_out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "candidate_relative_active_observation_utility_nonterminal",
                "row_type": "semantic_slam_candidate_relative_active_observation_request",
                "join_key": payload,
                **payload,
                "selected_observation_action": action,
                "selected_candidate_count": len(selected_ids),
                "selected_candidate_ids": list(selected_ids),
                "selected_candidate_utility_scores": {
                    cid: selected_scores.get(cid) for cid in selected_ids if cid in selected_scores
                },
                "candidate_count": safe_int(request_row.get("candidate_count"), len(candidates)),
                "ready_candidate_count": safe_int(request_row.get("ready_candidate_count"), 0),
                "separability_status": request_row.get("separability_status"),
                "request_risk_tags": request_tags,
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )

        for alternative_id in REQUIRED_ALTERNATIVES:
            selected_id, reason = alternative_selection(alternative_id, request_row, candidates)
            alternative_out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "candidate_relative_active_observation_utility_nonterminal",
                    "row_type": "semantic_slam_candidate_relative_active_observation_alternative_audit",
                    "join_key": {**payload, "alternative_id": alternative_id},
                    **payload,
                    "alternative_id": alternative_id,
                    "alternative_role": "simpler_alternative_audit",
                    "audit_selected_candidate_id": selected_id,
                    "audit_selection_reason": reason,
                    "alternative_allowed_as_nonterminal_audit": True,
                    "alternative_allowed_as_terminal_action": False,
                    "fallback_shortcut_forbidden": alternative_id.endswith("_forbidden"),
                    "terminal_commit": False,
                    "candidate_commit": False,
                    "candidate_rejection": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )

        failure_tags = list(request_tags)
        if "candidate_overlap_only_context_gap" not in failure_tags and request_has_context_gap(request_row):
            failure_tags.append("candidate_overlap_only_context_gap")
        if "tie_or_saturation_requires_observation" not in failure_tags and safe_int(
            request_row.get("candidate_count"), 0
        ) > 1:
            failure_tags.append("tie_or_saturation_requires_observation")
        failure_tags.append("terminal_commit_blocked_by_contract")
        failure_out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "candidate_relative_active_observation_utility_nonterminal",
                "row_type": "semantic_slam_candidate_relative_active_observation_failure_taxonomy",
                "join_key": payload,
                **payload,
                "failure_tags": sorted(set(failure_tags)),
                "primary_failure_or_blocker": "active_observation_required_before_terminal_utility",
                "selected_observation_action": action,
                "selected_candidate_count": len(selected_ids),
                "separability_status": request_row.get("separability_status"),
                "candidate_count": safe_int(request_row.get("candidate_count"), len(candidates)),
                "ready_candidate_count": safe_int(request_row.get("ready_candidate_count"), 0),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return priority_out, request_out, alternative_out, failure_out


def task_proxy_reference(summary: Mapping[str, Any]) -> Dict[str, Any]:
    counts = summary.get("actual_counts")
    alternatives = summary.get("alternative_outcomes")
    request_counts = summary.get("request_separability_task_proxy_counts")
    if not isinstance(counts, Mapping):
        counts = {}
    if not isinstance(alternatives, Mapping):
        alternatives = {}
    if not isinstance(request_counts, Mapping):
        request_counts = {}
    return {
        "usage": "evaluation_only_after_action_freeze_summary_reference",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "top_map_pose_tuple": alternatives.get("top_map_pose_tuple", {}),
        "top_projection_visible_heading": alternatives.get("top_projection_visible_heading", {}),
        "current_unique_ready": alternatives.get("current_unique_ready", {}),
        "request_separability_task_proxy_counts": request_counts,
        "source_actual_counts": {
            "top_map_pose_tuple_correct_rows": counts.get("top_map_pose_tuple_correct_rows"),
            "top_map_pose_tuple_wrong_rows": counts.get("top_map_pose_tuple_wrong_rows"),
            "top_map_pose_tuple_no_valid_request_rows": counts.get("top_map_pose_tuple_no_valid_request_rows"),
            "candidate_relative_unique_top_correct_rows": counts.get("candidate_relative_unique_top_correct_rows"),
            "candidate_relative_unique_top_wrong_rows": counts.get("candidate_relative_unique_top_wrong_rows"),
            "candidate_relative_unique_top_no_valid_rows": counts.get("candidate_relative_unique_top_no_valid_rows"),
        },
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    task_summary: Mapping[str, Any],
    priority_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    alternative_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
    out_root: Path,
    map_pose_root: Path,
) -> Dict[str, Any]:
    actual_counts = {
        "observation_priority_rows": len(priority_rows),
        "request_risk_summary_rows": len(request_rows),
        "simpler_alternative_audit_rows": len(alternative_rows),
        "failure_taxonomy_rows": len(failure_rows),
        "terminal_commit_rows": sum(
            1 for row in [*priority_rows, *request_rows, *alternative_rows, *failure_rows] if row.get("terminal_commit") is True
        ),
        "candidate_commit_rows": sum(
            1
            for row in [*priority_rows, *request_rows, *alternative_rows, *failure_rows]
            if row.get("candidate_commit") is True
        ),
        "candidate_rejection_rows": sum(
            1
            for row in [*priority_rows, *request_rows, *alternative_rows, *failure_rows]
            if row.get("candidate_rejection") is True
        ),
        "uses_gt_for_action_true_rows": sum(
            1
            for row in [*priority_rows, *request_rows, *alternative_rows, *failure_rows]
            if row.get("uses_gt_for_action") is True
        ),
        "paper_claim_allowed_true_rows": sum(
            1
            for row in [*priority_rows, *request_rows, *alternative_rows, *failure_rows]
            if row.get("paper_claim_allowed") is True
        ),
        "action_forbidden_key_count": len(action_forbidden_keys),
    }
    required_alternative_set = set(REQUIRED_ALTERNATIVES)
    actual_alternative_set = {str(row.get("alternative_id")) for row in alternative_rows}
    failure_tag_set = {str(tag) for row in failure_rows for tag in row.get("failure_tags", [])}
    materializer_gate = {
        "request_rows_expected_passed": actual_counts["request_risk_summary_rows"] == 50,
        "observation_priority_rows_minimum_passed": actual_counts["observation_priority_rows"] >= 50,
        "simpler_alternative_rows_minimum_passed": actual_counts["simpler_alternative_audit_rows"] >= 250,
        "failure_taxonomy_rows_minimum_passed": actual_counts["failure_taxonomy_rows"] >= 50,
        "required_alternatives_present_passed": required_alternative_set.issubset(actual_alternative_set),
        "required_failure_tags_present_passed": set(REQUIRED_FAILURE_TAGS).issubset(failure_tag_set),
        "terminal_commit_rows_max_passed": actual_counts["terminal_commit_rows"] == 0,
        "candidate_commit_rows_max_passed": actual_counts["candidate_commit_rows"] == 0,
        "candidate_rejection_rows_max_passed": actual_counts["candidate_rejection_rows"] == 0,
        "uses_gt_for_action_required_passed": actual_counts["uses_gt_for_action_true_rows"] == 0,
        "action_evidence_forbidden_key_count_passed": actual_counts["action_forbidden_key_count"] == 0,
        "paper_claim_allowed_required_passed": actual_counts["paper_claim_allowed_true_rows"] == 0,
    }
    materializer_gate_passed = all(materializer_gate.values())
    promotion_gate = {
        "active_observation_materializer_gate_must_pass": materializer_gate_passed,
        "task_proxy_join_after_action_freeze_required": False,
        "terminal_utility_contract_required": False,
        "heldout_or_fresh_validation_required_before_paper_claim": False,
    }
    primary_blocker = (
        "task_proxy_join_after_active_observation_action_freeze_required"
        if materializer_gate_passed
        else "active_observation_materializer_gate_failed"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "active_observation_materializer_gate_passed_promotion_blocked"
        if materializer_gate_passed
        else "failed",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "observation_priority_rows": "semantic_slam_candidate_relative_active_observation_priority_rows.jsonl",
            "request_risk_summary_rows": "semantic_slam_candidate_relative_active_observation_request_rows.jsonl",
            "simpler_alternative_audit_rows": "semantic_slam_candidate_relative_active_observation_alternative_rows.jsonl",
            "failure_taxonomy_rows": "semantic_slam_candidate_relative_active_observation_failure_rows.jsonl",
            "summary": "semantic_slam_candidate_relative_active_observation_utility_summary.json",
        },
        "source_files": {
            "contract": CONTRACT_DEFAULT,
            "map_pose_root": str(map_pose_root),
            "task_proxy_summary": TASK_PROXY_SUMMARY_DEFAULT,
        },
        "source_gate": contract.get("source_gate", {}),
        "actual_counts": actual_counts,
        "selected_observation_action_counts": compact_counter(
            row.get("selected_observation_action") for row in request_rows
        ),
        "candidate_observation_action_counts": compact_counter(row.get("observation_action") for row in priority_rows),
        "separability_status_counts": compact_counter(row.get("separability_status") for row in request_rows),
        "risk_tag_counts": compact_counter(tag for row in priority_rows for tag in row.get("risk_tags", [])),
        "request_risk_tag_counts": compact_counter(tag for row in request_rows for tag in row.get("request_risk_tags", [])),
        "alternative_counts": compact_counter(row.get("alternative_id") for row in alternative_rows),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "task_proxy_reference_after_action_freeze": task_proxy_reference(task_summary),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "contract_gate_passed": materializer_gate_passed,
        "active_observation_materializer_gate": materializer_gate,
        "active_observation_materializer_gate_passed": materializer_gate_passed,
        "promotion_gate_after_materialization": promotion_gate,
        "promotion_gate_after_materialization_passed": False,
        "terminal_utility_validation_allowed": False,
        "revised_slam_formula_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": primary_blocker,
        "recommended_next_task": "freeze_active_observation_task_proxy_join_contract"
        if materializer_gate_passed
        else "repair_active_observation_materializer",
        "interpretation": {
            "fact": (
                "The output rows convert candidate-relative map/pose evidence into nonterminal active-observation "
                "priority, request risk, simpler-alternative audit, and failure-taxonomy rows."
            ),
            "paper_claim": "No ObjectNav, SLAM, navigation, or policy-scale improvement claim is allowed from this artifact.",
            "agent_inference": (
                "The next useful gate is a task-proxy join after action freeze, so wrong-goal/no-valid risk can be "
                "measured without letting labels define the active-observation action."
            ),
        },
        "next_task": "freeze_active_observation_task_proxy_join_contract"
        if materializer_gate_passed
        else "repair_active_observation_materializer",
    }


def run(contract_path: Path, map_pose_root: Path, task_proxy_summary_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    task_summary = load_json(task_proxy_summary_path)
    candidate_rows = load_jsonl(map_pose_root / "semantic_slam_candidate_relative_map_pose_evidence_candidate_rows.jsonl")
    request_rows = load_jsonl(map_pose_root / "semantic_slam_candidate_relative_map_pose_evidence_request_rows.jsonl")
    priority_out, request_out, alternative_out, failure_out = build_rows(candidate_rows, request_rows)
    action_forbidden_keys = scan_forbidden_keys([*priority_out, *request_out, *alternative_out, *failure_out])
    summary = build_summary(
        contract=contract,
        task_summary=task_summary,
        priority_rows=priority_out,
        request_rows=request_out,
        alternative_rows=alternative_out,
        failure_rows=failure_out,
        action_forbidden_keys=action_forbidden_keys,
        out_root=out_root,
        map_pose_root=map_pose_root,
    )
    write_jsonl(out_root / "semantic_slam_candidate_relative_active_observation_priority_rows.jsonl", priority_out)
    write_jsonl(out_root / "semantic_slam_candidate_relative_active_observation_request_rows.jsonl", request_out)
    write_jsonl(out_root / "semantic_slam_candidate_relative_active_observation_alternative_rows.jsonl", alternative_out)
    write_jsonl(out_root / "semantic_slam_candidate_relative_active_observation_failure_rows.jsonl", failure_out)
    write_json(out_root / "semantic_slam_candidate_relative_active_observation_utility_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize candidate-relative Semantic-SLAM active-observation utility rows."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--map-pose-root", default=MAP_POSE_ROOT_DEFAULT)
    parser.add_argument("--task-proxy-summary", default=TASK_PROXY_SUMMARY_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(
        contract_path=Path(args.contract),
        map_pose_root=Path(args.map_pose_root),
        task_proxy_summary_path=Path(args.task_proxy_summary),
        out_root=Path(args.out_root),
    )
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
