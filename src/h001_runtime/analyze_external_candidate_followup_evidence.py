import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.analyze_object_node_evidence_objective import PROPERTY_GROUP_BY_QUERY
from h001_runtime.analyze_external_candidate_observation_evidence_v3 import (
    candidate_support,
    load_json_optional,
    load_jsonl,
    load_jsonl_optional,
    plan_index,
    ranked_candidates,
    ratio,
    safe_float,
    strong_depth_evidence,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.external_candidate_followup_evidence.v1"


def feature_index(path: Optional[Path]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_jsonl(path):
        indexed[(str(row.get("episode_key")), str(row.get("candidate_id")))] = row
    return indexed


def artifact_index(path: Optional[Path]) -> Dict[Tuple[str, str], Dict[str, Dict[str, Any]]]:
    if path is None or not path.exists():
        return {}
    indexed: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        indexed[(str(row.get("scene_id")), str(row.get("query")))] = {
            str(candidate.get("candidate_id")): candidate
            for candidate in row.get("candidates") or []
            if candidate.get("candidate_id") is not None
        }
    return indexed


def source_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in rows}


def source_candidate_index(source: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("candidate_id")): row
        for row in source.get("candidate_evidence") or []
        if row.get("candidate_id") is not None
    }


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def branch_observed_ids(frame_rows: List[Dict[str, Any]], association_rows: List[Dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for row in frame_rows:
        branch_id = row.get("external_branch_id")
        if branch_id is not None:
            ids.add(str(branch_id))
    for row in association_rows:
        branch_id = row.get("external_branch_id")
        if branch_id is not None:
            ids.add(str(branch_id))
    return ids


def candidate_label(
    source: Dict[str, Any],
    source_candidates: Dict[str, Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    candidate_id: str,
) -> Dict[str, Any]:
    source_row = source_candidates.get(candidate_id) or {}
    feature_row = labels.get((str(source.get("episode_key")), candidate_id)) or {}
    return {
        "candidate_correct": source_row.get("candidate_correct", feature_row.get("candidate_correct")),
        "candidate_reachable": source_row.get("candidate_reachable", feature_row.get("candidate_reachable")),
        "semantic_score": source_row.get("semantic_score", feature_row.get("score")),
        "S_sem": source_row.get("S_sem", feature_row.get("S_sem")),
        "N2_projection_support_no_depth": source_row.get(
            "N2_projection_support_no_depth",
            feature_row.get("N2_projection_support_no_depth"),
        ),
        "N5_object_node_evidence_full": source_row.get(
            "N5_object_node_evidence_full",
            feature_row.get("N5_object_node_evidence_full"),
        ),
        "external_branch_rank": source_row.get("external_branch_rank"),
        "external_pool_rank": source_row.get("external_pool_rank"),
        "semantic_rank": source_row.get("semantic_rank"),
    }


def rank_from_role(role: Any) -> Optional[int]:
    text = str(role)
    if "_" not in text:
        return None
    try:
        return int(text.rsplit("_", 1)[-1])
    except ValueError:
        return None


def candidate_position(candidate_id: str, artifact_candidates: Dict[str, Dict[str, Any]]) -> Optional[List[float]]:
    candidate = artifact_candidates.get(candidate_id)
    if not candidate:
        return None
    value = candidate.get("position")
    if not isinstance(value, list) or len(value) != 3:
        return None
    return [safe_float(item) or 0.0 for item in value]


def distance_xz(a: List[float], b: List[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def support_rows_by_branch_candidate(
    plan_rows: List[Dict[str, Any]],
    association_rows: List[Dict[str, Any]],
) -> Tuple[Dict[Tuple[str, str], List[Dict[str, Any]]], int]:
    decision_to_plan = plan_index(plan_rows)
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    unmatched = 0
    for row in association_rows:
        plan = decision_to_plan.get(str(row.get("decision_id")))
        branch_id = str((plan or row).get("external_branch_id"))
        candidate_id = str(row.get("candidate_id"))
        if plan is None:
            unmatched += 1
        grouped[(branch_id, candidate_id)].append(row)
    return grouped, unmatched


def plan_rows_by_branch(plan_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        grouped[str(row.get("external_branch_id"))].append(row)
    return grouped


def association_candidate_ids(rows: List[Dict[str, Any]]) -> List[str]:
    return ordered_unique(row.get("candidate_id") for row in rows)


def make_candidate_rows(
    source: Dict[str, Any],
    plan_rows: List[Dict[str, Any]],
    association_rows: List[Dict[str, Any]],
    rows_by_branch_candidate: Dict[Tuple[str, str], List[Dict[str, Any]]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    branch_id = str(source.get("external_branch_id"))
    source_candidates = source_candidate_index(source)
    observed_candidate_ids = association_candidate_ids(association_rows)
    if not observed_candidate_ids:
        observed_candidate_ids = ordered_unique(row.get("candidate_id") for row in plan_rows)

    rows: List[Dict[str, Any]] = []
    for candidate_id in observed_candidate_ids:
        support_rows = rows_by_branch_candidate.get((branch_id, candidate_id), [])
        support = candidate_support(support_rows)
        plan_for_candidate = [row for row in plan_rows if str(row.get("candidate_id")) == candidate_id]
        roles = ordered_unique(row.get("followup_role") for row in plan_for_candidate)
        actions = ordered_unique(row.get("followup_action") for row in plan_for_candidate)
        viewpoint_sources = ordered_unique(row.get("followup_viewpoint_source") for row in plan_for_candidate)
        label = candidate_label(source, source_candidates, labels, candidate_id)
        row = {
            "candidate_id": candidate_id,
            "followup_actions": actions,
            "followup_roles": roles,
            "followup_role_rank": min([rank for role in roles if (rank := rank_from_role(role)) is not None], default=None),
            "followup_viewpoint_sources": viewpoint_sources,
            "followup_observation_count": len(plan_for_candidate),
            **label,
            **support,
        }
        row["followup_strong_depth_evidence"] = strong_depth_evidence(row, args)
        rows.append(row)
    return rows


def selected_local_cluster_margin_guard(
    selected: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    artifact_candidates: Dict[str, Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[bool, str, Dict[str, Any]]:
    selected_id = str(selected.get("candidate_id"))
    selected_score = safe_float(selected.get("S_ext")) or 0.0
    selected_pos = candidate_position(selected_id, artifact_candidates)
    if selected_pos is None:
        return False, "defer_identity_selected_cluster_position_missing", {
            "identity_objective": "selected_local_cluster_margin",
            "selected_candidate_id": selected_id,
            "selected_position_available": False,
        }

    local: List[Dict[str, Any]] = []
    outside: List[Dict[str, Any]] = []
    skipped_position = 0
    radius_m = float(args.identity_cluster_radius_m)
    for candidate in candidates:
        if candidate.get("positive_support") is not True:
            continue
        if candidate.get("followup_strong_depth_evidence") is not True:
            continue
        if (safe_float(candidate.get("S_ext")) or 0.0) < float(args.min_commit_score):
            continue
        candidate_id = str(candidate.get("candidate_id"))
        pos = candidate_position(candidate_id, artifact_candidates)
        if pos is None:
            skipped_position += 1
            continue
        if distance_xz(selected_pos, pos) <= radius_m:
            local.append(candidate)
        else:
            outside.append(candidate)

    local_scores = [
        safe_float(candidate.get("S_ext")) or 0.0
        for candidate in local
        if str(candidate.get("candidate_id")) != selected_id
    ]
    outside_scores = [safe_float(candidate.get("S_ext")) or 0.0 for candidate in outside]
    guard = {
        "identity_objective": "selected_local_cluster_margin",
        "selected_candidate_id": selected_id,
        "selected_score": selected_score,
        "selected_position_available": True,
        "identity_cluster_radius_m": radius_m,
        "identity_min_local_strong_count": int(args.identity_min_local_strong_count),
        "identity_local_score_tolerance": float(args.identity_local_score_tolerance),
        "identity_outside_score_margin": float(args.identity_outside_score_margin),
        "local_strong_candidate_count": len(local),
        "outside_strong_candidate_count": len(outside),
        "position_skipped_strong_candidate_count": skipped_position,
        "local_strong_candidate_ids": [row.get("candidate_id") for row in local],
        "outside_strong_candidate_ids": [row.get("candidate_id") for row in outside],
        "best_local_other_score": max(local_scores) if local_scores else None,
        "best_outside_score": max(outside_scores) if outside_scores else None,
    }

    if len(local) < int(args.identity_min_local_strong_count):
        return False, "defer_identity_selected_local_cluster_too_small", guard
    if local_scores and max(local_scores) > selected_score + float(args.identity_local_score_tolerance):
        return False, "defer_identity_selected_local_rival_stronger", guard
    if outside_scores and max(outside_scores) >= selected_score - float(args.identity_outside_score_margin):
        return False, "defer_identity_selected_outside_rival_near_tie", guard
    return True, "commit_selected_identity_confirmed_local_cluster_margin_after_followup", guard


def select_identity_confirmation(
    source: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    artifact_candidates: Dict[str, Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], Optional[float], float, str, Dict[str, Any]]:
    selected_id = str(source.get("selected_candidate_id"))
    selected = next((row for row in candidates if row.get("candidate_id") == selected_id), None)
    ranked = ranked_candidates(candidates)
    if selected is None:
        return None, None, 0.0, "defer_identity_selected_not_observed", {"selected_candidate_id": selected_id}
    rivals = [row for row in ranked if row.get("candidate_id") != selected_id]
    best_rival = rivals[0] if rivals else None
    selected_score = safe_float(selected.get("S_ext")) or 0.0
    rival_score = safe_float(best_rival.get("S_ext")) if best_rival else None
    margin = selected_score - (rival_score if rival_score is not None else 0.0)
    strong_rivals = [row for row in rivals if row.get("followup_strong_depth_evidence") is True]
    guard = {
        "selected_candidate_id": selected_id,
        "selected_strong_depth_evidence": selected.get("followup_strong_depth_evidence") is True,
        "selected_positive_support": selected.get("positive_support") is True,
        "selected_score": selected_score,
        "best_rival_candidate_id": None if best_rival is None else best_rival.get("candidate_id"),
        "best_rival_score": rival_score,
        "strong_rival_count": len(strong_rivals),
    }

    if selected.get("positive_support") is not True:
        return selected, rival_score, margin, "defer_identity_selected_has_no_positive_support", guard
    if selected_score < float(args.min_commit_score):
        return selected, rival_score, margin, "defer_identity_selected_evidence_weak", guard
    if selected.get("followup_strong_depth_evidence") is not True:
        return selected, rival_score, margin, "defer_identity_selected_without_strong_depth_association", guard
    if str(args.objective_version) in {"v4", "v5"}:
        accepted, reason, cluster_guard = selected_local_cluster_margin_guard(
            selected,
            candidates,
            artifact_candidates,
            args,
        )
        guard.update(cluster_guard)
        if accepted:
            return selected, rival_score, margin, reason, guard
        if str(args.objective_version) == "v5" and reason == "defer_identity_selected_local_rival_stronger":
            guard["heldout_local_rival_route"] = {
                "route": "request_identity_confirmation",
                "reason": "local_rival_stronger_after_followup",
                "uses_gt_for_action": False,
            }
            return (
                selected,
                rival_score,
                margin,
                "request_identity_confirmation_after_local_rival_stronger",
                guard,
            )
        return selected, rival_score, margin, reason, guard
    if strong_rivals:
        return selected, rival_score, margin, "defer_identity_ambiguous_rival_supported", guard
    if margin < float(args.min_identity_followup_margin):
        return selected, rival_score, margin, "defer_identity_not_contrastive_after_followup", guard
    return selected, rival_score, margin, "commit_selected_identity_confirmed_after_followup", guard


def select_expanded_retrieval(
    source: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], Optional[float], float, str, Dict[str, Any]]:
    if not candidates:
        return None, None, 0.0, "defer_expanded_retrieval_no_observed_candidates", {}
    ranked = ranked_candidates(candidates)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    best_score = safe_float(best.get("S_ext")) or 0.0
    second_score = safe_float(second.get("S_ext")) if second else None
    margin = best_score - (second_score if second_score is not None else 0.0)
    property_group = PROPERTY_GROUP_BY_QUERY.get(str(source.get("query")), "unknown")
    strong_candidates = [row for row in ranked if row.get("followup_strong_depth_evidence") is True]
    large_repeated_guard = str(args.large_repeated_expanded_retrieval_guard)
    objective_version = str(args.objective_version)
    if objective_version in {"v2", "v3", "v4", "v5"} and large_repeated_guard == "auto":
        large_repeated_guard = "request_identity"
    small_or_cluttered_guard = str(args.small_or_cluttered_expanded_retrieval_guard)
    if objective_version in {"v3", "v4", "v5"} and small_or_cluttered_guard == "auto":
        small_or_cluttered_guard = "request_identity"
    guard = {
        "property_group": property_group,
        "best_candidate_id": best.get("candidate_id"),
        "best_strong_depth_evidence": best.get("followup_strong_depth_evidence") is True,
        "best_positive_support": best.get("positive_support") is True,
        "strong_candidate_count": len(strong_candidates),
        "large_repeated_expanded_retrieval_guard": large_repeated_guard,
        "small_or_cluttered_expanded_retrieval_guard": small_or_cluttered_guard,
    }

    if best.get("positive_support") is not True:
        return best, second_score, margin, "defer_expanded_retrieval_no_positive_support", guard
    if best_score < float(args.min_commit_score):
        return best, second_score, margin, "defer_expanded_retrieval_weak_evidence", guard
    if best.get("followup_strong_depth_evidence") is not True:
        return best, second_score, margin, "defer_expanded_retrieval_without_strong_depth_association", guard
    if len(strong_candidates) > 1 and margin < float(args.min_identity_followup_margin):
        return best, second_score, margin, "request_identity_confirmation_after_expanded_retrieval_multiple_strong", guard
    if property_group == "large_repeated_furniture" and large_repeated_guard != "allow":
        if large_repeated_guard == "defer":
            return best, second_score, margin, "defer_expanded_retrieval_large_repeated_instance_guard", guard
        return best, second_score, margin, "request_identity_confirmation_after_expanded_retrieval_large_repeated_instance_guard", guard
    if property_group == "small_or_cluttered":
        if margin < float(args.min_small_or_cluttered_followup_margin):
            return best, second_score, margin, "defer_expanded_retrieval_small_or_cluttered_not_contrastive", guard
        if small_or_cluttered_guard != "allow":
            if small_or_cluttered_guard == "defer":
                return best, second_score, margin, "defer_expanded_retrieval_small_or_cluttered_instance_guard", guard
            return (
                best,
                second_score,
                margin,
                "request_identity_confirmation_after_expanded_retrieval_small_or_cluttered_instance_guard",
                guard,
            )
    elif margin < float(args.min_expanded_retrieval_margin):
        return best, second_score, margin, "defer_expanded_retrieval_not_contrastive", guard
    return best, second_score, margin, "commit_expanded_candidate_after_followup", guard


def action_for_reason(reason: str) -> str:
    if reason.startswith("commit_selected_identity_confirmed"):
        return "followup_evidence_v1_commit_selected_candidate"
    if reason.startswith("commit_expanded_candidate"):
        return "followup_evidence_v1_commit_expanded_candidate"
    if reason.startswith("request_identity_confirmation"):
        return "followup_evidence_v1_request_identity_confirmation"
    return "followup_evidence_v1_defer"


def summarize(rows: List[Dict[str, Any]], detector_summary: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    commit_rows = [row for row in rows if row["followup_evidence_v1_commits"]]
    success_commits = [row for row in commit_rows if row["followup_evidence_v1_success_commit"]]
    wrong_commits = [row for row in commit_rows if row["followup_evidence_v1_wrong_goal_commit"]]
    no_valid_commits = [row for row in commit_rows if row["followup_evidence_v1_no_valid_commit"]]
    request_identity_rows = [
        row for row in rows
        if row["followup_evidence_v1_action"] == "followup_evidence_v1_request_identity_confirmation"
    ]
    evidence_available = [
        row for row in rows
        if any((candidate.get("S_ext") or 0.0) > 0.0 for candidate in row.get("followup_candidate_evidence") or [])
    ]
    positive_evidence = [
        row for row in rows
        if any(candidate.get("positive_support") is True for candidate in row.get("followup_candidate_evidence") or [])
    ]
    strong_depth_rows = [
        row for row in rows
        if any(candidate.get("followup_strong_depth_evidence") is True for candidate in row.get("followup_candidate_evidence") or [])
    ]
    rows_with_labels = [row for row in rows if row.get("selected_candidate_correct") is not None]
    action_counts = Counter(row["followup_evidence_v1_action"] for row in rows)
    reason_counts = Counter(row["followup_evidence_v1_reason"] for row in rows)
    action_by_source: Dict[str, Counter[str]] = defaultdict(Counter)
    action_by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    action_by_property: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        action_by_source[str(row.get("source_external_evidence_v4_action"))][str(row["followup_evidence_v1_action"])] += 1
        action_by_label[str(row.get("label_case"))][str(row["followup_evidence_v1_action"])] += 1
        action_by_property[str(row.get("property_group"))][str(row["followup_evidence_v1_action"])] += 1

    detector_box_rate = detector_summary.get("rows_with_detector_box_rate")
    sam2_mask_rate = detector_summary.get("rows_with_sam2_mask_rate")
    candidate_association_rate = detector_summary.get("rows_with_candidate_association_rate")
    gate = {
        "min_detector_box_rate": float(args.min_detector_box_rate),
        "min_sam2_mask_rate": float(args.min_sam2_mask_rate),
        "min_followup_evidence_available_rate": float(args.min_followup_evidence_available_rate),
        "min_followup_positive_evidence_rate": float(args.min_followup_positive_evidence_rate),
        "min_followup_strong_depth_evidence_rate": float(args.min_followup_strong_depth_evidence_rate),
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_no_valid_commit_rate": float(args.max_no_valid_commit_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_success_commit_rate": float(args.min_success_commit_rate),
        "detector_box_rate": detector_box_rate,
        "sam2_mask_rate": sam2_mask_rate,
        "candidate_association_rate_diagnostic": candidate_association_rate,
        "followup_evidence_available_rate": ratio(len(evidence_available), len(rows)),
        "followup_positive_evidence_rate": ratio(len(positive_evidence), len(rows)),
        "followup_strong_depth_evidence_rate": ratio(len(strong_depth_rows), len(rows)),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "success_commit_rate": ratio(len(success_commits), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_commits), len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commits), len(commit_rows)),
        "no_valid_commit_rate": ratio(len(no_valid_commits), len(rows)),
        "request_identity_confirmation_rate": ratio(len(request_identity_rows), len(rows)),
        "labeled_row_rate": ratio(len(rows_with_labels), len(rows)),
    }
    gate["passes_followup_detector_substrate_gate_v1"] = bool(
        (safe_float(detector_box_rate) or 0.0) >= float(args.min_detector_box_rate)
        and (safe_float(sam2_mask_rate) or 0.0) >= float(args.min_sam2_mask_rate)
        and (gate["followup_evidence_available_rate"] or 0.0) >= float(args.min_followup_evidence_available_rate)
        and (gate["followup_positive_evidence_rate"] or 0.0) >= float(args.min_followup_positive_evidence_rate)
        and (gate["followup_strong_depth_evidence_rate"] or 0.0) >= float(args.min_followup_strong_depth_evidence_rate)
    )
    gate["passes_followup_evidence_safety_gate_v1"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["no_valid_commit_rate"] or 0.0) <= float(args.max_no_valid_commit_rate)
    )
    gate["passes_followup_evidence_full_gate_v1"] = bool(
        gate["passes_followup_detector_substrate_gate_v1"]
        and gate["passes_followup_evidence_safety_gate_v1"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and (gate["success_commit_rate"] or 0.0) >= float(args.min_success_commit_rate)
    )
    return {
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "action_by_source_external_evidence_v4_action": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(action_by_source.items())
        },
        "action_by_label_case": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(action_by_label.items())
        },
        "action_by_property_group": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(action_by_property.items())
        },
        "gate": gate,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    source_rows = load_jsonl(Path(args.external_evidence_v4_rows))
    sources = source_index(source_rows)
    plan_rows = load_jsonl(Path(args.followup_observation_plan))
    plans_by_branch = plan_rows_by_branch(plan_rows)
    detector_root = Path(args.detector_root)
    detector_summary = load_json_optional(detector_root / "summary.json")
    frame_rows = load_jsonl_optional(detector_root / "frame_summary.jsonl")
    association_rows = load_jsonl_optional(detector_root / "detector_candidate_associations.jsonl")
    observed_branch_ids = branch_observed_ids(frame_rows, association_rows)
    rows_by_branch_candidate, unmatched_association_rows = support_rows_by_branch_candidate(plan_rows, association_rows)
    labels = feature_index(Path(args.object_node_features) if args.object_node_features else None)
    artifacts = artifact_index(Path(args.candidate_artifact) if args.candidate_artifact else None)

    request_actions = {
        "external_evidence_v4_request_identity_confirmation",
        "external_evidence_v4_request_expanded_retrieval",
    }
    source_request_rows = [
        row for row in source_rows
        if row.get("external_evidence_v4_action") in request_actions
    ]
    source_rows_for_analysis = [
        row for row in source_request_rows
        if not args.observed_only or str(row.get("external_branch_id")) in observed_branch_ids
    ]

    evidence_rows: List[Dict[str, Any]] = []
    for source in source_rows_for_analysis:
        branch_id = str(source.get("external_branch_id"))
        branch_plan_rows = plans_by_branch.get(branch_id, [])
        branch_association_rows = [
            row for row in association_rows
            if str(row.get("external_branch_id")) == branch_id
        ]
        candidate_rows = make_candidate_rows(
            source,
            branch_plan_rows,
            branch_association_rows,
            rows_by_branch_candidate,
            labels,
            args,
        )
        source_action = str(source.get("external_evidence_v4_action"))
        if source_action == "external_evidence_v4_request_identity_confirmation":
            artifact_candidates = artifacts.get((str(source.get("scene_id")), str(source.get("query"))), {})
            selected, second_score, margin, reason, guard = select_identity_confirmation(
                source,
                candidate_rows,
                artifact_candidates,
                args,
            )
        else:
            selected, second_score, margin, reason, guard = select_expanded_retrieval(source, candidate_rows, args)
        selected = selected or {}
        action = action_for_reason(reason)
        commits = action in {
            "followup_evidence_v1_commit_selected_candidate",
            "followup_evidence_v1_commit_expanded_candidate",
        }
        contains_correct = any(row.get("candidate_correct") is True for row in candidate_rows)
        selected_correct = selected.get("candidate_correct")
        evidence_rows.append(
            {
                "schema_version": (
                    SCHEMA_VERSION
                    if str(args.objective_version) == "v1"
                    else f"h001.external_candidate_followup_evidence.{args.objective_version}"
                ),
                "objective_version": str(args.objective_version),
                "external_branch_id": branch_id,
                "episode_key": source.get("episode_key"),
                "scene_id": source.get("scene_id"),
                "query": source.get("query"),
                "property_group": source.get("property_group") or PROPERTY_GROUP_BY_QUERY.get(str(source.get("query")), "unknown"),
                "label_case": source.get("label_case"),
                "source_external_evidence_v4_action": source_action,
                "source_external_evidence_v4_reason": source.get("external_evidence_v4_reason"),
                "source_selected_candidate_id": source.get("selected_candidate_id"),
                "source_selected_candidate_correct": source.get("selected_candidate_correct"),
                "followup_plan_rows": len(branch_plan_rows),
                "followup_association_rows": len(branch_association_rows),
                "followup_observed_candidate_count": len(candidate_rows),
                "followup_candidate_ids": [row.get("candidate_id") for row in candidate_rows],
                "followup_set_contains_correct": contains_correct,
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_candidate_correct": selected_correct,
                "selected_score": selected.get("S_ext"),
                "second_score": second_score,
                "score_margin": margin,
                "followup_evidence_v1_action": action,
                "followup_evidence_v1_reason": reason,
                "followup_evidence_v1_commits": commits,
                "followup_evidence_v1_success_commit": bool(commits and selected_correct is True),
                "followup_evidence_v1_wrong_goal_commit": bool(commits and selected_correct is False),
                "followup_evidence_v1_no_valid_commit": bool(commits and not contains_correct),
                "followup_guard": guard,
                "followup_candidate_evidence": candidate_rows,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": any(row.get("candidate_correct") is not None for row in candidate_rows),
            }
        )

    write_jsonl(out_root / "external_candidate_followup_evidence_rows.jsonl", evidence_rows)
    stats = summarize(evidence_rows, detector_summary, args)
    summary = {
        "schema_version": (
            SCHEMA_VERSION
            if str(args.objective_version) == "v1"
            else f"h001.external_candidate_followup_evidence.{args.objective_version}"
        ),
        "objective_version": str(args.objective_version),
        "large_repeated_expanded_retrieval_guard": str(args.large_repeated_expanded_retrieval_guard),
        "small_or_cluttered_expanded_retrieval_guard": str(args.small_or_cluttered_expanded_retrieval_guard),
        "external_evidence_v4_rows": str(args.external_evidence_v4_rows),
        "followup_observation_plan": str(args.followup_observation_plan),
        "detector_root": str(args.detector_root),
        "object_node_features": args.object_node_features,
        "candidate_artifact": args.candidate_artifact,
        "out_root": str(out_root),
        "source_rows_total": len(source_rows),
        "source_request_rows": len(source_request_rows),
        "source_rows_analyzed": len(source_rows_for_analysis),
        "observed_only": bool(args.observed_only),
        "observed_branch_ids": sorted(observed_branch_ids),
        "skipped_unobserved_source_rows": max(0, len(source_request_rows) - len(source_rows_for_analysis)),
        "plan_rows": len(plan_rows),
        "frame_rows": len(frame_rows),
        "association_rows": len(association_rows),
        "unmatched_association_rows": unmatched_association_rows,
        **stats,
        "thresholds": {
            "min_commit_score": float(args.min_commit_score),
            "min_expanded_retrieval_margin": float(args.min_expanded_retrieval_margin),
            "min_identity_followup_margin": float(args.min_identity_followup_margin),
            "min_small_or_cluttered_followup_margin": float(args.min_small_or_cluttered_followup_margin),
            "min_strong_strict_association_count": float(args.min_strong_strict_association_count),
            "min_strong_mask_hit_count": float(args.min_strong_mask_hit_count),
            "min_strong_visible_count": float(args.min_strong_visible_count),
            "identity_cluster_radius_m": float(args.identity_cluster_radius_m),
            "identity_min_local_strong_count": int(args.identity_min_local_strong_count),
            "identity_local_score_tolerance": float(args.identity_local_score_tolerance),
            "identity_outside_score_margin": float(args.identity_outside_score_margin),
        },
        "objective_design": {
            "role": "convert V4 mobility requests into post-follow-up commit/request/defer decisions",
            "not_threshold_only": [
                "identity confirmation checks selected-vs-rival support after targeted standoff observations",
                "expanded retrieval checks whether newly observed semantic candidates create a valid commit candidate",
                "large repeated furniture can remain in identity-confirmation state rather than forcing a commit",
            ],
            "v2_revision": [
                "large repeated furniture expanded-retrieval rows do not directly commit from detector/depth support alone",
                "strong depth association is treated as observation evidence, not instance-validity proof",
                "identity-confirmation defer behavior is preserved for rival-supported repeated-object rows",
            ] if str(args.objective_version) in {"v2", "v3", "v4", "v5"} else [],
            "v3_revision": [
                "small or cluttered object expanded-retrieval rows do not directly commit from a single strong visible distractor",
                "positive detector support plus strong depth association is not treated as instance-safe for compact repeated objects",
                "compact-object expanded retrieval is routed to identity confirmation or defer before any first_eval rerun",
            ] if str(args.objective_version) in {"v3", "v4", "v5"} else [],
            "v4_revision": [
                "identity confirmation can commit only the source selected candidate",
                "selected candidate must have positive support, strong depth association, and pass a non-GT local spatial cluster margin",
                "nearby strong candidates are treated as local identity support only when they do not materially outscore the selected candidate",
                "outside-cluster strong candidates block commit when they are near-tied with the selected candidate",
            ] if str(args.objective_version) in {"v4", "v5"} else [],
            "v5_revision": [
                "local-rival-stronger identity ambiguity is routed to second-stage identity confirmation instead of terminal defer",
                "outside-cluster near-tie rows remain deferred because they may require broader retrieval rather than identity arbitration",
                "the routing decision uses the non-GT local spatial cluster guard, not candidate correctness labels",
            ] if str(args.objective_version) == "v5" else [],
            "failure_modes_addressed": [
                "over-deferral after retrieval-invalid external evidence",
                "wrong repeated-object commit after identity-ambiguous evidence",
                "no-valid external candidate set after expanded retrieval",
                "visible small-object distractor commit despite correct candidate in the follow-up candidate set",
            ],
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row["uses_gt_for_analysis"] for row in evidence_rows),
        "output_files": {
            "rows": "external_candidate_followup_evidence_rows.jsonl",
            "summary": "external_candidate_followup_evidence_summary.json",
        },
    }
    write_json(out_root / "external_candidate_followup_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze H001 external-candidate follow-up observation evidence.")
    parser.add_argument("--external-evidence-v4-rows", required=True)
    parser.add_argument("--followup-observation-plan", required=True)
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--object-node-features", default=None)
    parser.add_argument("--candidate-artifact", default=None)
    parser.add_argument("--observed-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--objective-version", choices=["v1", "v2", "v3", "v4", "v5"], default="v1")
    parser.add_argument(
        "--large-repeated-expanded-retrieval-guard",
        choices=["auto", "allow", "request_identity", "defer"],
        default="auto",
    )
    parser.add_argument(
        "--small-or-cluttered-expanded-retrieval-guard",
        choices=["auto", "allow", "request_identity", "defer"],
        default="auto",
    )
    parser.add_argument("--min-commit-score", type=float, default=0.35)
    parser.add_argument("--min-expanded-retrieval-margin", type=float, default=0.10)
    parser.add_argument("--min-identity-followup-margin", type=float, default=0.20)
    parser.add_argument("--min-small-or-cluttered-followup-margin", type=float, default=0.20)
    parser.add_argument("--min-strong-strict-association-count", type=float, default=2.0)
    parser.add_argument("--min-strong-mask-hit-count", type=float, default=2.0)
    parser.add_argument("--min-strong-visible-count", type=float, default=3.0)
    parser.add_argument("--identity-cluster-radius-m", type=float, default=2.0)
    parser.add_argument("--identity-min-local-strong-count", type=int, default=2)
    parser.add_argument("--identity-local-score-tolerance", type=float, default=0.002)
    parser.add_argument("--identity-outside-score-margin", type=float, default=0.005)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-followup-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-followup-positive-evidence-rate", type=float, default=0.30)
    parser.add_argument("--min-followup-strong-depth-evidence-rate", type=float, default=0.20)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-no-valid-commit-rate", type=float, default=0.10)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-success-commit-rate", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
