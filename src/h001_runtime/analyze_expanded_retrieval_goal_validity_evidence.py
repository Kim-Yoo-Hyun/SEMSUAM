import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys, request_sort_key


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_objective.v1"
PROPOSED_VARIANT = "candidate_specific_goal_validity_objective_v1"
ALTERNATIVE_VARIANTS = [
    "defer_all",
    "semantic_top_observed",
    "detector_score_best_observed",
    "positive_support_best_observed",
    "candidate_specific_support_best_observed",
]
ALL_VARIANTS = [PROPOSED_VARIANT, *ALTERNATIVE_VARIANTS]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("target_candidate_id"))


def plan_sort_key(row: Dict[str, Any]) -> Tuple[Tuple[int, str], int, int, str]:
    request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
    return (
        request_sort_key(request_id),
        safe_int(row.get("target_generated_rank")),
        safe_int(row.get("target_semantic_rank")),
        candidate_id(row),
    )


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        grouped[request_id].append(dict(row))
    for request_rows in grouped.values():
        request_rows.sort(key=plan_sort_key)
    return grouped


def index_by_request_candidate(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        cid = candidate_id(row)
        if request_id and cid:
            indexed[(request_id, cid)] = dict(row)
    return indexed


def group_associations(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        cid = candidate_id(row)
        if request_id and cid:
            grouped[(request_id, cid)].append(dict(row))
    return grouped


def label_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        cid = candidate_id(row)
        if request_id and cid:
            indexed[(request_id, cid)] = dict(row)
    return indexed


def label_groups(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        if request_id:
            grouped[request_id].append(dict(row))
    for request_rows in grouped.values():
        request_rows.sort(key=lambda row: safe_int(row.get("evaluation_only_candidate_rank")))
    return grouped


def number_stats(values: Sequence[int]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def evidence_metrics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    box_hits = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    mask_hits = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    consistent = [
        row
        for row in rows
        if str(row.get("depth_check_status")) in {"consistent", "depth_match"}
    ]
    depth_mismatch = [row for row in rows if str(row.get("depth_check_status")) == "depth_mismatch"]
    detector_scores = [safe_float(row.get("best_box_score")) for row in rows]
    detector_scores = [score for score in detector_scores if score is not None]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
    depth_errors = [value for value in depth_errors if value is not None]
    return {
        "heading_rows": len(rows),
        "associated_heading_count": len(associated),
        "visible_count": len(visible),
        "box_hit_count": len(box_hits),
        "mask_hit_count": len(mask_hits),
        "consistent_depth_count": len(consistent),
        "depth_mismatch_count": len(depth_mismatch),
        "best_box_score": max(detector_scores, default=None),
        "min_depth_error_m": min(depth_errors, default=None),
    }


def support_class(
    frame_row: Optional[Dict[str, Any]],
    metrics: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> str:
    if frame_row is None:
        return "not_scored_in_bounded_substrate"
    has_visual = bool(frame_row.get("has_detector_box") or frame_row.get("has_sam2_mask"))
    if not has_visual:
        return "no_visual_support"
    associated = safe_int(metrics.get("associated_heading_count"), default=0)
    mask_hits = safe_int(metrics.get("mask_hit_count"), default=0)
    visible = safe_int(metrics.get("visible_count"), default=0)
    consistent = safe_int(metrics.get("consistent_depth_count"), default=0)
    strict = (
        associated >= safe_int(thresholds.get("min_associated_heading_count"), default=1)
        and mask_hits >= safe_int(thresholds.get("min_mask_hit_count"), default=1)
        and visible >= safe_int(thresholds.get("min_visible_count"), default=1)
        and consistent >= safe_int(thresholds.get("min_consistent_depth_count"), default=1)
    )
    if strict:
        return "candidate_specific_support"
    if associated > 0 or mask_hits > 0:
        return "weak_or_partial_candidate_specific_support"
    return "category_only_visibility"


def candidate_row(
    plan_row: Dict[str, Any],
    frame_row: Optional[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    metrics = evidence_metrics(association_rows)
    cls = support_class(frame_row, metrics, thresholds)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_evidence_only",
        "expanded_retrieval_request_id": plan_row.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": plan_row.get("rival_identity_request_id"),
        "episode_key": plan_row.get("episode_key"),
        "scene_key": plan_row.get("scene_key"),
        "scene_id": plan_row.get("scene_id"),
        "query": plan_row.get("query"),
        "candidate_id": candidate_id(plan_row),
        "target_generated_rank": plan_row.get("target_generated_rank"),
        "target_semantic_rank": plan_row.get("target_semantic_rank"),
        "target_semantic_score": plan_row.get("target_semantic_score"),
        "target_support_score": plan_row.get("target_support_score"),
        "target_score": plan_row.get("target_score"),
        "target_positive_support": plan_row.get("target_positive_support"),
        "target_candidate_reachable": plan_row.get("target_candidate_reachable"),
        "target_visit_position_navigable": plan_row.get("target_visit_position_navigable"),
        "goal_validity_rival_candidate_ids": plan_row.get("goal_validity_rival_candidate_ids") or [],
        "observed_in_bounded_detector_substrate": frame_row is not None,
        "detector_observation_status": "observed" if frame_row is not None else "not_scored_in_bounded_substrate",
        "candidate_evidence_class": cls,
        "candidate_specific_support": cls == "candidate_specific_support",
        "category_only_visibility": cls == "category_only_visibility",
        "weak_or_partial_candidate_specific_support": cls == "weak_or_partial_candidate_specific_support",
        "rendered_heading_count": None if frame_row is None else frame_row.get("rendered_heading_count"),
        "detector_box_count": None if frame_row is None else frame_row.get("detector_box_count"),
        "sam2_mask_count": None if frame_row is None else frame_row.get("sam2_mask_count"),
        "has_detector_box": None if frame_row is None else frame_row.get("has_detector_box"),
        "has_sam2_mask": None if frame_row is None else frame_row.get("has_sam2_mask"),
        "has_candidate_association": None if frame_row is None else frame_row.get("has_candidate_association"),
        **metrics,
        "terminal_commit": False,
        "uses_gt_for_action": False,
    }


def build_candidate_rows(
    plan_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    frame_index = index_by_request_candidate(frame_rows)
    association_index = group_associations(association_rows)
    thresholds = dict(((contract.get("objective") or {}).get("support_thresholds")) or {})
    output = []
    for plan_row in sorted(plan_rows, key=plan_sort_key):
        key = (
            str(plan_row.get("expanded_retrieval_request_id") or plan_row.get("rival_identity_request_id")),
            candidate_id(plan_row),
        )
        output.append(candidate_row(plan_row, frame_index.get(key), association_index.get(key, []), thresholds))
    return output


def best_by(rows: Sequence[Dict[str, Any]], fields: Sequence[str]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None

    def sort_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
        values: List[Any] = []
        for field in fields:
            if field == "target_semantic_rank_ascending":
                values.append(-safe_int(row.get("target_semantic_rank")))
            elif field == "target_generated_rank_ascending":
                values.append(-safe_int(row.get("target_generated_rank")))
            elif field == "candidate_id":
                values.append(str(row.get("candidate_id")))
            elif field == "target_positive_support":
                values.append(1 if row.get("target_positive_support") is True else 0)
            else:
                values.append(safe_float(row.get(field), default=0.0) or 0.0)
        return tuple(values)

    return max(rows, key=sort_key)


def select_candidate(rows: Sequence[Dict[str, Any]], variant: str) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]:
    observed = [row for row in rows if row.get("observed_in_bounded_detector_substrate") is True]
    support_rows = [row for row in observed if row.get("candidate_specific_support") is True]
    guard: Dict[str, Any] = {
        "variant": variant,
        "planned_candidate_count": len(rows),
        "observed_candidate_count": len(observed),
        "candidate_specific_support_count": len(support_rows),
        "bounded_detector_substrate_incomplete": len(observed) < len(rows),
    }
    if variant == PROPOSED_VARIANT:
        if len(observed) < len(rows):
            return None, "request_full_candidate_specific_scoring", guard
        if not support_rows:
            return None, "defer_no_candidate_specific_support", guard
        if len(support_rows) > 1:
            return None, "defer_candidate_specific_support_ambiguous", guard
        return None, "defer_terminal_commit_blocked_by_contract", guard
    if variant == "defer_all":
        return None, "defer_all_baseline", guard
    if variant == "semantic_top_observed":
        selected = best_by(observed, ["target_semantic_rank_ascending", "target_score", "candidate_id"])
        if selected is None:
            return None, "defer_no_observed_candidate", guard
        return selected, "counterfactual_commit_semantic_top_observed", guard
    if variant == "detector_score_best_observed":
        selected = best_by(
            observed,
            [
                "best_box_score",
                "associated_heading_count",
                "mask_hit_count",
                "visible_count",
                "target_score",
                "candidate_id",
            ],
        )
        if selected is None:
            return None, "defer_no_observed_candidate", guard
        return selected, "counterfactual_commit_detector_score_best_observed", guard
    if variant == "positive_support_best_observed":
        positive = [row for row in observed if row.get("target_positive_support") is True]
        selected = best_by(positive, ["target_semantic_rank_ascending", "target_score", "candidate_id"])
        if selected is None:
            return None, "defer_no_observed_positive_support_candidate", guard
        return selected, "counterfactual_commit_positive_support_best_observed", guard
    if variant == "candidate_specific_support_best_observed":
        selected = best_by(
            support_rows,
            [
                "associated_heading_count",
                "mask_hit_count",
                "consistent_depth_count",
                "best_box_score",
                "target_score",
                "candidate_id",
            ],
        )
        if selected is None:
            return None, "defer_no_candidate_specific_support_candidate", guard
        return selected, "counterfactual_commit_candidate_specific_support_best_observed", guard
    raise ValueError(f"unknown variant: {variant}")


def request_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = group_by_request(candidate_rows)
    output = []
    for request_id in sorted(grouped, key=request_sort_key):
        rows = grouped[request_id]
        exemplar = rows[0]
        class_counts = Counter(str(row.get("candidate_evidence_class")) for row in rows)
        observed = [row for row in rows if row.get("observed_in_bounded_detector_substrate") is True]
        support_rows = [row for row in observed if row.get("candidate_specific_support") is True]
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_request_summary_only",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "planned_candidate_count": len(rows),
                "observed_candidate_count": len(observed),
                "unscored_candidate_count": len(rows) - len(observed),
                "candidate_specific_support_count": len(support_rows),
                "category_only_visibility_count": class_counts.get("category_only_visibility", 0),
                "weak_or_partial_candidate_specific_support_count": class_counts.get(
                    "weak_or_partial_candidate_specific_support", 0
                ),
                "not_scored_in_bounded_substrate_count": class_counts.get("not_scored_in_bounded_substrate", 0),
                "candidate_evidence_class_counts": dict(sorted(class_counts.items())),
                "bounded_detector_substrate_incomplete": len(observed) < len(rows),
                "full_detector_substrate_required": len(observed) < len(rows),
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return output


def decision_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped = group_by_request(candidate_rows)
    decisions: List[Dict[str, Any]] = []
    for request_id in sorted(grouped, key=request_sort_key):
        rows = grouped[request_id]
        exemplar = rows[0]
        for variant in ALL_VARIANTS:
            selected, reason, guard = select_candidate(rows, variant)
            action = "defer" if selected is None else "counterfactual_commit_candidate"
            if variant == PROPOSED_VARIANT:
                action = reason
            decisions.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_decision_only",
                    "objective_variant": variant,
                    "expanded_retrieval_request_id": request_id,
                    "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                    "episode_key": exemplar.get("episode_key"),
                    "scene_key": exemplar.get("scene_key"),
                    "scene_id": exemplar.get("scene_id"),
                    "query": exemplar.get("query"),
                    "action": action,
                    "reason": reason,
                    "selected_candidate_id": None if selected is None else selected.get("candidate_id"),
                    "selected_target_generated_rank": None if selected is None else selected.get("target_generated_rank"),
                    "selected_target_semantic_rank": None if selected is None else selected.get("target_semantic_rank"),
                    "selected_candidate_evidence_class": None
                    if selected is None
                    else selected.get("candidate_evidence_class"),
                    "selected_associated_heading_count": None
                    if selected is None
                    else selected.get("associated_heading_count"),
                    "selected_mask_hit_count": None if selected is None else selected.get("mask_hit_count"),
                    "selected_visible_count": None if selected is None else selected.get("visible_count"),
                    "selected_best_box_score": None if selected is None else selected.get("best_box_score"),
                    "planned_candidate_count": len(rows),
                    "observed_candidate_count": guard["observed_candidate_count"],
                    "candidate_specific_support_count": guard["candidate_specific_support_count"],
                    "decision_guard": guard,
                    "counterfactual_only": variant != PROPOSED_VARIANT,
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                }
            )
    return decisions


def request_label_profile(label_rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped = label_groups(label_rows)
    output: Dict[str, Dict[str, Any]] = {}
    for request_id, rows in grouped.items():
        correct_rows = [row for row in rows if row.get("evaluation_only_candidate_correct") is True]
        false_rows = [row for row in rows if row.get("evaluation_only_candidate_correct") is False]
        null_rows = [row for row in rows if row.get("evaluation_only_candidate_correct") is None]
        output[request_id] = {
            "evaluation_only_candidate_rows": len(rows),
            "evaluation_only_correct_candidate_count": len(correct_rows),
            "evaluation_only_wrong_candidate_count": len(false_rows),
            "evaluation_only_unlabeled_candidate_count": len(null_rows),
            "evaluation_only_first_correct_rank": min(
                [safe_int(row.get("evaluation_only_candidate_rank")) for row in correct_rows],
                default=None,
            ),
            "evaluation_only_correct_candidate_ids": [row.get("candidate_id") for row in correct_rows],
        }
    return output


def evaluated_decision_rows(
    decisions: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    request_profiles: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in decisions:
        selected_id = row.get("selected_candidate_id")
        request_id = str(row.get("expanded_retrieval_request_id"))
        profile = request_profiles.get(request_id) or {}
        label = labels.get((request_id, str(selected_id))) if selected_id else None
        selected_is_commit = bool(selected_id)
        selected_correct = None if label is None else label.get("evaluation_only_candidate_correct")
        request_has_valid = safe_int(profile.get("evaluation_only_correct_candidate_count"), default=0) > 0
        out = {
            **row,
            "validation_stage": "evaluation_joined_after_action_decision",
            "evaluation_only_request_has_valid_candidate": request_has_valid,
            "evaluation_only_request_first_correct_rank": profile.get("evaluation_only_first_correct_rank"),
            "evaluation_only_selected_has_label": bool(label) if selected_is_commit else None,
            "evaluation_only_selected_candidate_rank": None
            if label is None
            else label.get("evaluation_only_candidate_rank"),
            "evaluation_only_selected_correct": selected_correct if selected_is_commit else None,
            "evaluation_only_success_commit": bool(selected_is_commit and selected_correct is True),
            "evaluation_only_wrong_goal_commit": bool(selected_is_commit and selected_correct is False),
            "evaluation_only_no_valid_commit": bool(selected_is_commit and not request_has_valid),
            "evaluation_only_no_label_commit": bool(selected_is_commit and label is None),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
        }
        output.append(out)
    return output


def summarize_alternatives(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    by_variant: Dict[str, Dict[str, Any]] = {}
    for variant in ALL_VARIANTS:
        variant_rows = [row for row in rows if row.get("objective_variant") == variant]
        commits = [row for row in variant_rows if row.get("selected_candidate_id") is not None]
        success = [row for row in commits if row.get("evaluation_only_success_commit") is True]
        wrong = [row for row in commits if row.get("evaluation_only_wrong_goal_commit") is True]
        no_valid = [row for row in commits if row.get("evaluation_only_no_valid_commit") is True]
        no_label = [row for row in commits if row.get("evaluation_only_no_label_commit") is True]
        by_variant[variant] = {
            "request_rows": len(variant_rows),
            "counterfactual_commit_rows": len(commits),
            "evaluation_only_success_commit_rows": len(success),
            "evaluation_only_wrong_goal_commit_rows": len(wrong),
            "evaluation_only_no_valid_commit_rows": len(no_valid),
            "evaluation_only_no_label_commit_rows": len(no_label),
            "counterfactual_commit_rate": ratio(len(commits), len(variant_rows)),
            "evaluation_only_success_commit_rate": ratio(len(success), len(variant_rows)),
            "evaluation_only_wrong_goal_commit_rate": ratio(len(wrong), len(variant_rows)),
            "selected_candidate_ids": [row.get("selected_candidate_id") for row in commits],
            "reason_counts": dict(sorted(Counter(str(row.get("reason")) for row in variant_rows).items())),
        }
    return by_variant


def summarize(
    *,
    contract: Dict[str, Any],
    plan_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
    detector_summary: Dict[str, Any],
    candidate_rows: Sequence[Dict[str, Any]],
    req_rows: Sequence[Dict[str, Any]],
    decisions: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    label_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    planned_request_rows = len(group_by_request(plan_rows))
    planned_candidate_rows = len(plan_rows)
    observed_candidate_rows = sum(1 for row in candidate_rows if row.get("observed_in_bounded_detector_substrate") is True)
    unscored_candidate_rows = planned_candidate_rows - observed_candidate_rows
    observed_request_rows = sum(1 for row in req_rows if safe_int(row.get("observed_candidate_count"), default=0) > 0)
    bounded_incomplete = observed_candidate_rows < planned_candidate_rows or observed_request_rows < planned_request_rows
    expected_bounded_incomplete = gates.get("bounded_detector_substrate_incomplete_expected")
    if expected_bounded_incomplete is None:
        expected_bounded_incomplete = True
    expected_full_required = gates.get("full_detector_substrate_required_expected")
    if expected_full_required is None:
        expected_full_required = True
    expected_full_complete = gates.get("full_detector_substrate_complete_expected")
    if expected_full_complete is None:
        expected_full_complete = not bool(expected_bounded_incomplete)
    detector_box_rate = safe_float(detector_summary.get("detector_box_rate"), default=0.0) or 0.0
    sam2_mask_rate = safe_float(detector_summary.get("sam2_mask_rate"), default=0.0) or 0.0
    candidate_association_rate = safe_float(detector_summary.get("candidate_association_rate"), default=0.0) or 0.0
    labels = label_index(label_rows)
    request_profiles = request_label_profile(label_rows)
    observed_eval_labels = [
        labels.get((str(row.get("expanded_retrieval_request_id")), str(row.get("candidate_id"))))
        for row in candidate_rows
        if row.get("observed_in_bounded_detector_substrate") is True
    ]
    observed_eval_labels = [row for row in observed_eval_labels if row is not None]
    observed_eval_correct = [row for row in observed_eval_labels if row.get("evaluation_only_candidate_correct") is True]
    observed_eval_wrong = [row for row in observed_eval_labels if row.get("evaluation_only_candidate_correct") is False]
    observed_eval_null = [row for row in observed_eval_labels if row.get("evaluation_only_candidate_correct") is None]
    action_rows = [*candidate_rows, *req_rows, *decisions]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    class_counts = Counter(str(row.get("candidate_evidence_class")) for row in candidate_rows)
    gate = {
        "planned_request_rows_passed": planned_request_rows == safe_int(gates.get("planned_request_rows")),
        "planned_candidate_rows_passed": planned_candidate_rows == safe_int(gates.get("planned_candidate_rows")),
        "observed_detector_candidate_rows_minimum_passed": observed_candidate_rows
        >= safe_int(gates.get("observed_detector_candidate_rows_minimum"), default=0),
        "observed_detector_request_rows_minimum_passed": observed_request_rows
        >= safe_int(gates.get("observed_detector_request_rows_minimum"), default=0),
        "unscored_candidate_rows_maximum_passed": unscored_candidate_rows
        <= safe_int(gates.get("unscored_candidate_rows_maximum"), default=planned_candidate_rows),
        "detector_box_rate_passed": detector_box_rate >= float(gates.get("detector_box_rate_minimum") or 0.0),
        "sam2_mask_rate_passed": sam2_mask_rate >= float(gates.get("sam2_mask_rate_minimum") or 0.0),
        "candidate_association_rate_passed": candidate_association_rate
        >= float(gates.get("candidate_association_rate_minimum") or 0.0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), default=0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), default=0),
        "reports_bounded_detector_substrate_incomplete": bounded_incomplete is expected_bounded_incomplete,
        "reports_full_detector_substrate_required": bounded_incomplete is expected_full_required,
        "full_detector_substrate_complete_expected_passed": (bounded_incomplete is False)
        is expected_full_complete,
        "reports_post_action_label_join": bool(evaluated_rows),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["objective_analyzer_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "plan": str(args.plan),
        "detector_associations": str(args.detector_associations),
        "detector_frame_summary": str(args.detector_frame_summary),
        "detector_summary": str(args.detector_summary),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "planned_request_rows": planned_request_rows,
        "planned_candidate_rows": planned_candidate_rows,
        "observed_detector_candidate_rows": observed_candidate_rows,
        "observed_detector_request_rows": observed_request_rows,
        "unscored_candidate_rows": unscored_candidate_rows,
        "bounded_detector_substrate_incomplete": bounded_incomplete,
        "full_detector_substrate_required": bounded_incomplete,
        "terminal_utility_validation_allowed": False,
        "request_rows": len(req_rows),
        "decision_rows": len(decisions),
        "evaluated_rows": len(evaluated_rows),
        "evaluation_label_rows": len(label_rows),
        "candidate_evidence_class_counts": dict(sorted(class_counts.items())),
        "observed_candidate_evaluation": {
            "evaluation_only_observed_label_rows": len(observed_eval_labels),
            "evaluation_only_observed_correct_candidate_count": len(observed_eval_correct),
            "evaluation_only_observed_wrong_candidate_count": len(observed_eval_wrong),
            "evaluation_only_observed_unlabeled_candidate_count": len(observed_eval_null),
            "evaluation_only_observed_correct_candidate_ids": [
                row.get("candidate_id") for row in observed_eval_correct
            ],
        },
        "request_label_profile": dict(sorted(request_profiles.items())),
        "detector_substrate_rates": {
            "detector_rows": detector_summary.get("detector_rows"),
            "detector_box_rate": detector_box_rate,
            "sam2_mask_rate": sam2_mask_rate,
            "candidate_association_rate": candidate_association_rate,
            "rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
        },
        "plan_rows_by_request": {
            request_id: len(rows) for request_id, rows in sorted(group_by_request(plan_rows).items())
        },
        "observed_rows_by_request": {
            row.get("expanded_retrieval_request_id"): row.get("observed_candidate_count") for row in req_rows
        },
        "unscored_rows_by_request": {
            row.get("expanded_retrieval_request_id"): row.get("unscored_candidate_count") for row in req_rows
        },
        "simpler_alternative_accounting": summarize_alternatives(evaluated_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": (contract.get("interpretation_rule") or {}).get(
                "fact",
                "The detector/SAM2 substrate is evaluated after action-evidence rows are fixed.",
            ),
            "agent_inference": (contract.get("interpretation_rule") or {}).get(
                "agent_inference",
                "This analyzer validates schema separation and detector evidence accounting, but it still blocks terminal utility validation.",
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "candidate_rows": "goal_validity_objective_candidate_rows.jsonl",
            "request_rows": "goal_validity_objective_request_rows.jsonl",
            "decision_rows": "goal_validity_objective_decision_rows.jsonl",
            "evaluated_rows": "goal_validity_objective_evaluated_rows.jsonl",
            "summary": "goal_validity_objective_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    plan_rows = load_jsonl(Path(args.plan))
    detector_associations = load_jsonl(Path(args.detector_associations))
    detector_frame_summary = load_jsonl(Path(args.detector_frame_summary))
    detector_summary = load_json(Path(args.detector_summary))
    evaluation_labels = load_jsonl(Path(args.evaluation_labels))

    candidates = build_candidate_rows(plan_rows, detector_frame_summary, detector_associations, contract)
    requests = request_rows(candidates)
    decisions = decision_rows(candidates)
    labels = label_index(evaluation_labels)
    profiles = request_label_profile(evaluation_labels)
    evaluated = evaluated_decision_rows(decisions, labels, profiles)
    summary = summarize(
        contract=contract,
        plan_rows=plan_rows,
        frame_rows=detector_frame_summary,
        association_rows=detector_associations,
        detector_summary=detector_summary,
        candidate_rows=candidates,
        req_rows=requests,
        decisions=decisions,
        evaluated_rows=evaluated,
        label_rows=evaluation_labels,
        args=args,
    )

    write_jsonl(out_root / "goal_validity_objective_candidate_rows.jsonl", candidates)
    write_jsonl(out_root / "goal_validity_objective_request_rows.jsonl", requests)
    write_jsonl(out_root / "goal_validity_objective_decision_rows.jsonl", decisions)
    write_jsonl(out_root / "goal_validity_objective_evaluated_rows.jsonl", evaluated)
    write_json(out_root / "goal_validity_objective_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze candidate-specific goal-validity detector evidence before terminal utility validation."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--detector-frame-summary", required=True)
    parser.add_argument("--detector-summary", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
