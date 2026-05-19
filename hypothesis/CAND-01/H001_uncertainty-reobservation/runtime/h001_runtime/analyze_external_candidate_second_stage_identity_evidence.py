import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.analyze_external_candidate_observation_evidence_v2 import (
    candidate_support,
    load_json_optional,
    load_jsonl,
    load_jsonl_optional,
    plan_index,
    ratio,
    safe_float,
    strong_depth_evidence,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.external_candidate_second_stage_identity_evidence.v1"
REQUEST_ACTION = "followup_evidence_v1_request_identity_confirmation"


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def source_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in rows}


def source_candidate_index(source: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("candidate_id")): row
        for row in source.get("followup_candidate_evidence") or []
        if row.get("candidate_id") is not None
    }


def frame_rows_optional(root: Path) -> List[Dict[str, Any]]:
    frame_summary = root / "frame_summary.jsonl"
    if frame_summary.exists():
        return load_jsonl(frame_summary)
    return load_jsonl_optional(root / "postview_frames_v2.jsonl")


def observed_branch_ids(frame_rows: List[Dict[str, Any]], association_rows: List[Dict[str, Any]]) -> set[str]:
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


def plan_rows_by_branch(plan_rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        grouped[str(row.get("external_branch_id"))].append(row)
    return grouped


def candidate_ids_for_branch(source: Dict[str, Any], plan_rows: List[Dict[str, Any]]) -> List[str]:
    selected_id = source.get("selected_candidate_id") or source.get("second_stage_selected_candidate_id")
    values: List[Any] = [selected_id]
    for row in plan_rows:
        values.append(row.get("second_stage_candidate_id"))
        values.append(row.get("candidate_id"))
        values.extend(row.get("second_stage_rival_candidate_ids") or [])
        values.extend(row.get("candidate_ids") or [])
    return ordered_unique(values)


def rows_by_branch_candidate_role(
    plan_rows: List[Dict[str, Any]],
    association_rows: List[Dict[str, Any]],
) -> Tuple[
    Dict[Tuple[str, str], List[Dict[str, Any]]],
    Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    int,
]:
    decision_to_plan = plan_index(plan_rows)
    by_candidate: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    by_role: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    unmatched = 0
    for row in association_rows:
        plan = decision_to_plan.get(str(row.get("decision_id")))
        if plan is None:
            unmatched += 1
            branch_id = str(row.get("external_branch_id"))
            role = str(row.get("second_stage_role") or row.get("source_second_stage_role") or "unknown")
        else:
            branch_id = str(plan.get("external_branch_id"))
            role = str(plan.get("second_stage_role"))
        candidate_id = str(row.get("candidate_id"))
        by_candidate[(branch_id, candidate_id)].append(row)
        by_role[(branch_id, candidate_id, role)].append(row)
    return by_candidate, by_role, unmatched


def support_with_prefix(prefix: str, rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    support = candidate_support(rows)
    support["strong_depth_evidence"] = strong_depth_evidence(support, args)
    return {f"{prefix}_{key}": value for key, value in support.items()}


def candidate_label(source_candidates: Dict[str, Dict[str, Any]], candidate_id: str) -> Dict[str, Any]:
    source_row = source_candidates.get(candidate_id) or {}
    return {
        "candidate_correct": source_row.get("candidate_correct"),
        "candidate_reachable": source_row.get("candidate_reachable"),
        "semantic_score": source_row.get("semantic_score"),
        "S_sem": source_row.get("S_sem"),
        "prior_S_ext": source_row.get("S_ext"),
        "prior_positive_support": source_row.get("positive_support"),
        "prior_followup_strong_depth_evidence": source_row.get("followup_strong_depth_evidence"),
        "prior_strict_association_count": source_row.get("strict_association_count"),
        "prior_mask_hit_count": source_row.get("mask_hit_count"),
    }


def candidate_role_for_id(candidate_id: str, selected_id: str, rival_ids: List[str]) -> str:
    if candidate_id == selected_id:
        return "selected"
    if candidate_id in rival_ids:
        return "rival"
    return "context"


def candidate_evidence_rows(
    source: Dict[str, Any],
    branch_plan_rows: List[Dict[str, Any]],
    rows_by_candidate: Dict[Tuple[str, str], List[Dict[str, Any]]],
    rows_by_role: Dict[Tuple[str, str, str], List[Dict[str, Any]]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    branch_id = str(source.get("external_branch_id"))
    selected_id = str(source.get("selected_candidate_id"))
    rival_ids = ordered_unique(
        rival
        for row in branch_plan_rows
        for rival in (row.get("second_stage_rival_candidate_ids") or [])
    )
    source_candidates = source_candidate_index(source)
    rows: List[Dict[str, Any]] = []
    for candidate_id in candidate_ids_for_branch(source, branch_plan_rows):
        plan_for_candidate = [
            row
            for row in branch_plan_rows
            if str(row.get("second_stage_candidate_id") or row.get("candidate_id")) == candidate_id
        ]
        roles = ordered_unique(row.get("second_stage_role") for row in plan_for_candidate)
        viewpoint_sources = ordered_unique(row.get("second_stage_viewpoint_source") for row in plan_for_candidate)
        total_rows = rows_by_candidate.get((branch_id, candidate_id), [])
        own_rows: List[Dict[str, Any]] = []
        other_rows: List[Dict[str, Any]] = []
        for role in roles:
            role_rows = rows_by_role.get((branch_id, candidate_id, role), [])
            own_rows.extend(role_rows)
        own_ids = {id(row) for row in own_rows}
        for row in total_rows:
            if id(row) not in own_ids:
                other_rows.append(row)

        total_support = candidate_support(total_rows)
        row = {
            "candidate_id": candidate_id,
            "identity_role": candidate_role_for_id(candidate_id, selected_id, rival_ids),
            "second_stage_roles": roles,
            "second_stage_viewpoint_sources": viewpoint_sources,
            "second_stage_observation_count": len(plan_for_candidate),
            **candidate_label(source_candidates, candidate_id),
            **total_support,
            "second_stage_strong_depth_evidence": strong_depth_evidence(total_support, args),
            **support_with_prefix("own_view", own_rows, args),
            **support_with_prefix("other_view", other_rows, args),
        }
        row["visit_position_only_evidence"] = bool(
            viewpoint_sources
            and all(source == "candidate_visit_position_fallback" for source in viewpoint_sources)
        )
        rows.append(row)
    return rows


def select_second_stage_action(
    source: Dict[str, Any],
    candidates: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[float], float, str, Dict[str, Any]]:
    selected_id = str(source.get("selected_candidate_id"))
    selected = next((row for row in candidates if row.get("candidate_id") == selected_id), None)
    rivals = [row for row in candidates if row.get("identity_role") == "rival"]
    ranked_rivals = sorted(
        rivals,
        key=lambda row: (
            safe_float(row.get("S_ext")) or 0.0,
            safe_float(row.get("strict_association_count")) or 0.0,
            safe_float(row.get("mask_hit_count")) or 0.0,
        ),
        reverse=True,
    )
    best_rival = ranked_rivals[0] if ranked_rivals else None
    selected_score = safe_float(selected.get("S_ext")) if selected else None
    rival_score = safe_float(best_rival.get("S_ext")) if best_rival else None
    margin = (selected_score or 0.0) - (rival_score or 0.0)
    selected_strong = bool(selected and selected.get("second_stage_strong_depth_evidence") is True)
    selected_own_strong = bool(selected and selected.get("own_view_strong_depth_evidence") is True)
    rival_positive = [
        row for row in rivals
        if row.get("positive_support") is True or row.get("second_stage_strong_depth_evidence") is True
    ]
    strong_rivals = [row for row in rivals if row.get("second_stage_strong_depth_evidence") is True]
    weak_positive_rivals = [
        row
        for row in rivals
        if row.get("positive_support") is True
        and row.get("second_stage_strong_depth_evidence") is not True
    ]
    guard = {
        "objective_version": args.objective_version,
        "selected_candidate_id": selected_id,
        "selected_score": selected_score,
        "selected_positive_support": None if selected is None else selected.get("positive_support") is True,
        "selected_strong_depth_evidence": selected_strong,
        "selected_own_view_strong_depth_evidence": selected_own_strong,
        "selected_visit_position_only_evidence": None if selected is None else selected.get("visit_position_only_evidence") is True,
        "best_rival_candidate_id": None if best_rival is None else best_rival.get("candidate_id"),
        "best_rival_score": rival_score,
        "rival_positive_or_strong_count": len(rival_positive),
        "rival_strong_count": len(strong_rivals),
        "rival_weak_positive_count": len(weak_positive_rivals),
        "identity_margin": margin,
        "allow_direct_commit": bool(args.allow_direct_commit),
    }

    if selected is None:
        return None, best_rival, rival_score, margin, "defer_selected_not_observed", guard
    if selected.get("positive_support") is not True:
        return selected, best_rival, rival_score, margin, "defer_selected_no_positive_support", guard
    if (selected_score or 0.0) < float(args.min_identity_score):
        return selected, best_rival, rival_score, margin, "defer_selected_evidence_weak", guard
    if not selected_strong:
        return selected, best_rival, rival_score, margin, "defer_selected_without_strong_depth_evidence", guard
    if not selected_own_strong:
        return selected, best_rival, rival_score, margin, "request_further_identity_confirmation_selected_not_strong_in_own_view", guard
    if selected.get("visit_position_only_evidence") is True:
        return selected, best_rival, rival_score, margin, "request_further_identity_confirmation_visit_position_only_blocked", guard
    if args.objective_version == "v2":
        if strong_rivals:
            return selected, best_rival, rival_score, margin, "request_further_identity_confirmation_strong_rival_supported", guard
        if margin < float(args.min_identity_margin):
            return selected, best_rival, rival_score, margin, "request_further_identity_confirmation_not_contrastive", guard
        if weak_positive_rivals:
            return selected, best_rival, rival_score, margin, "commit_selected_identity_confirmed_weak_rival_margin", guard
        return selected, best_rival, rival_score, margin, "commit_selected_identity_confirmed", guard
    if rival_positive:
        return selected, best_rival, rival_score, margin, "request_further_identity_confirmation_rival_supported", guard
    if margin < float(args.min_identity_margin):
        return selected, best_rival, rival_score, margin, "request_further_identity_confirmation_not_contrastive", guard
    if not bool(args.allow_direct_commit):
        return selected, best_rival, rival_score, margin, "request_commit_review_identity_ready_direct_commit_disabled", guard
    return selected, best_rival, rival_score, margin, "commit_selected_identity_confirmed", guard


def action_for_reason(reason: str) -> str:
    if reason.startswith("commit_selected_identity_confirmed"):
        return "second_stage_identity_v1_commit_selected_candidate"
    if reason.startswith("request_"):
        return "second_stage_identity_v1_request_further_identity_confirmation"
    return "second_stage_identity_v1_defer"


def summarize(rows: List[Dict[str, Any]], detector_summary: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    commit_rows = [row for row in rows if row.get("second_stage_identity_v1_commits") is True]
    success_commits = [row for row in commit_rows if row.get("second_stage_identity_v1_success_commit") is True]
    wrong_commits = [row for row in commit_rows if row.get("second_stage_identity_v1_wrong_goal_commit") is True]
    no_valid_commits = [row for row in commit_rows if row.get("second_stage_identity_v1_no_valid_commit") is True]
    visit_position_commits = [
        row for row in commit_rows
        if row.get("second_stage_identity_v1_visit_position_only_commit") is True
    ]
    request_rows = [
        row for row in rows
        if row.get("second_stage_identity_v1_action") == "second_stage_identity_v1_request_further_identity_confirmation"
    ]
    evidence_available = [
        row for row in rows
        if any((candidate.get("S_ext") or 0.0) > 0.0 for candidate in row.get("second_stage_candidate_evidence") or [])
    ]
    positive_evidence = [
        row for row in rows
        if any(candidate.get("positive_support") is True for candidate in row.get("second_stage_candidate_evidence") or [])
    ]
    strong_depth_rows = [
        row for row in rows
        if any(candidate.get("second_stage_strong_depth_evidence") is True for candidate in row.get("second_stage_candidate_evidence") or [])
    ]
    action_counts = Counter(str(row.get("second_stage_identity_v1_action")) for row in rows)
    reason_counts = Counter(str(row.get("second_stage_identity_v1_reason")) for row in rows)
    by_property: Dict[str, Counter[str]] = defaultdict(Counter)
    by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_property[str(row.get("property_group"))][str(row.get("second_stage_identity_v1_action"))] += 1
        by_label[str(row.get("label_case"))][str(row.get("second_stage_identity_v1_action"))] += 1

    detector_box_rate = detector_summary.get("rows_with_detector_box_rate")
    sam2_mask_rate = detector_summary.get("rows_with_sam2_mask_rate")
    candidate_association_rate = detector_summary.get("rows_with_candidate_association_rate")
    gate = {
        "min_detector_box_rate": float(args.min_detector_box_rate),
        "min_sam2_mask_rate": float(args.min_sam2_mask_rate),
        "min_second_stage_evidence_available_rate": float(args.min_second_stage_evidence_available_rate),
        "min_second_stage_positive_evidence_rate": float(args.min_second_stage_positive_evidence_rate),
        "min_second_stage_strong_depth_evidence_rate": float(args.min_second_stage_strong_depth_evidence_rate),
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_no_valid_commit_rate": float(args.max_no_valid_commit_rate),
        "max_visit_position_only_commit_rate": float(args.max_visit_position_only_commit_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_success_commit_rate": float(args.min_success_commit_rate),
        "detector_box_rate": detector_box_rate,
        "sam2_mask_rate": sam2_mask_rate,
        "candidate_association_rate_diagnostic": candidate_association_rate,
        "second_stage_evidence_available_rate": ratio(len(evidence_available), len(rows)),
        "second_stage_positive_evidence_rate": ratio(len(positive_evidence), len(rows)),
        "second_stage_strong_depth_evidence_rate": ratio(len(strong_depth_rows), len(rows)),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "success_commit_rate": ratio(len(success_commits), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_commits), len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commits), len(commit_rows)),
        "no_valid_commit_rate": ratio(len(no_valid_commits), len(rows)),
        "visit_position_only_commit_rate": ratio(len(visit_position_commits), len(rows)),
        "request_further_identity_confirmation_rate": ratio(len(request_rows), len(rows)),
    }
    gate["passes_second_stage_identity_schema_gate_v1"] = bool(
        len(rows) > 0
        and all(row.get("uses_gt_for_action") is False for row in rows)
    )
    gate["passes_second_stage_identity_detector_substrate_gate_v1"] = bool(
        (safe_float(detector_box_rate) or 0.0) >= float(args.min_detector_box_rate)
        and (safe_float(sam2_mask_rate) or 0.0) >= float(args.min_sam2_mask_rate)
        and (gate["second_stage_evidence_available_rate"] or 0.0)
        >= float(args.min_second_stage_evidence_available_rate)
        and (gate["second_stage_positive_evidence_rate"] or 0.0)
        >= float(args.min_second_stage_positive_evidence_rate)
        and (gate["second_stage_strong_depth_evidence_rate"] or 0.0)
        >= float(args.min_second_stage_strong_depth_evidence_rate)
    )
    gate["passes_second_stage_identity_safety_gate_v1"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["no_valid_commit_rate"] or 0.0) <= float(args.max_no_valid_commit_rate)
        and (gate["visit_position_only_commit_rate"] or 0.0)
        <= float(args.max_visit_position_only_commit_rate)
    )
    gate["passes_second_stage_identity_full_gate_v1"] = bool(
        gate["passes_second_stage_identity_detector_substrate_gate_v1"]
        and gate["passes_second_stage_identity_safety_gate_v1"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and (gate["success_commit_rate"] or 0.0) >= float(args.min_success_commit_rate)
    )
    return {
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "action_by_property_group": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(by_property.items())
        },
        "action_by_label_case": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(by_label.items())
        },
        "gate": gate,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    source_rows = load_jsonl(Path(args.followup_evidence_rows))
    request_rows = [row for row in source_rows if row.get("followup_evidence_v1_action") == REQUEST_ACTION]
    sources = source_index(request_rows)
    plan_rows = load_jsonl(Path(args.second_stage_plan))
    plans_by_branch = plan_rows_by_branch(plan_rows)
    detector_root = Path(args.detector_root)
    detector_summary = load_json_optional(detector_root / "summary.json")
    frame_rows = frame_rows_optional(detector_root)
    association_rows = load_jsonl_optional(detector_root / "detector_candidate_associations.jsonl")
    observed_ids = observed_branch_ids(frame_rows, association_rows)
    rows_by_candidate, rows_by_role, unmatched_association_rows = rows_by_branch_candidate_role(plan_rows, association_rows)

    source_rows_for_analysis = [
        row for row in request_rows
        if str(row.get("external_branch_id")) in plans_by_branch
        and (not args.observed_only or str(row.get("external_branch_id")) in observed_ids)
    ]

    evidence_rows: List[Dict[str, Any]] = []
    for source in source_rows_for_analysis:
        branch_id = str(source.get("external_branch_id"))
        branch_plan_rows = plans_by_branch.get(branch_id, [])
        candidate_rows = candidate_evidence_rows(source, branch_plan_rows, rows_by_candidate, rows_by_role, args)
        selected, best_rival, rival_score, margin, reason, guard = select_second_stage_action(source, candidate_rows, args)
        selected = selected or {}
        action = action_for_reason(reason)
        commits = action == "second_stage_identity_v1_commit_selected_candidate"
        contains_correct = source.get("followup_set_contains_correct")
        if contains_correct is None:
            contains_correct = any(row.get("candidate_correct") is True for row in candidate_rows)
        selected_correct = selected.get("candidate_correct")
        visit_position_only_commit = bool(commits and selected.get("visit_position_only_evidence") is True)
        evidence_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "external_branch_id": branch_id,
                "episode_key": source.get("episode_key"),
                "scene_id": source.get("scene_id"),
                "query": source.get("query"),
                "property_group": source.get("property_group"),
                "label_case": source.get("label_case"),
                "source_followup_evidence_v1_action": source.get("followup_evidence_v1_action"),
                "source_followup_evidence_v1_reason": source.get("followup_evidence_v1_reason"),
                "source_external_evidence_v4_action": source.get("source_external_evidence_v4_action"),
                "source_external_evidence_v4_reason": source.get("source_external_evidence_v4_reason"),
                "second_stage_plan_rows": len(branch_plan_rows),
                "second_stage_association_rows": sum(
                    len(rows_by_candidate.get((branch_id, str(row.get("candidate_id"))), []))
                    for row in candidate_rows
                ),
                "second_stage_candidate_ids": [row.get("candidate_id") for row in candidate_rows],
                "second_stage_rival_candidate_ids": ordered_unique(
                    rival
                    for row in branch_plan_rows
                    for rival in (row.get("second_stage_rival_candidate_ids") or [])
                ),
                "followup_set_contains_correct": contains_correct,
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_candidate_correct": selected_correct,
                "selected_score": selected.get("S_ext"),
                "best_rival_candidate_id": None if best_rival is None else best_rival.get("candidate_id"),
                "best_rival_score": rival_score,
                "score_margin": margin,
                "second_stage_identity_v1_action": action,
                "second_stage_identity_v1_reason": reason,
                "second_stage_identity_v1_commits": commits,
                "second_stage_identity_v1_success_commit": bool(commits and selected_correct is True),
                "second_stage_identity_v1_wrong_goal_commit": bool(commits and selected_correct is False),
                "second_stage_identity_v1_no_valid_commit": bool(commits and contains_correct is False),
                "second_stage_identity_v1_visit_position_only_commit": visit_position_only_commit,
                "second_stage_identity_guard": guard,
                "second_stage_candidate_evidence": candidate_rows,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": any(row.get("candidate_correct") is not None for row in candidate_rows),
            }
        )

    write_jsonl(out_root / "external_candidate_second_stage_identity_evidence_rows.jsonl", evidence_rows)
    stats = summarize(evidence_rows, detector_summary, args)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "second_stage_plan": str(args.second_stage_plan),
        "detector_root": str(args.detector_root),
        "out_root": str(out_root),
        "source_rows_total": len(source_rows),
        "source_request_rows": len(request_rows),
        "source_rows_with_plan": sum(1 for row in request_rows if str(row.get("external_branch_id")) in plans_by_branch),
        "source_rows_analyzed": len(source_rows_for_analysis),
        "observed_only": bool(args.observed_only),
        "observed_branch_ids": sorted(observed_ids),
        "skipped_unobserved_or_unplanned_rows": max(0, len(request_rows) - len(source_rows_for_analysis)),
        "plan_rows": len(plan_rows),
        "frame_rows": len(frame_rows),
        "association_rows": len(association_rows),
        "unmatched_association_rows": unmatched_association_rows,
        **stats,
        "thresholds": {
            "objective_version": args.objective_version,
            "allow_direct_commit": bool(args.allow_direct_commit),
            "min_identity_score": float(args.min_identity_score),
            "min_identity_margin": float(args.min_identity_margin),
            "min_strong_strict_association_count": float(args.min_strong_strict_association_count),
            "min_strong_mask_hit_count": float(args.min_strong_mask_hit_count),
            "min_strong_visible_count": float(args.min_strong_visible_count),
        },
        "objective_design": {
            "role": "convert V2 identity-confirmation requests into detector-backed selected-vs-rival identity decisions",
            "default_safety_contract": [
                "v1 direct commit is disabled unless --allow-direct-commit is explicitly set",
                "candidate_visit_position_fallback evidence cannot authorize commit",
                "rival positive or strong evidence keeps the branch in identity-confirmation state",
            ],
            "v2_recovery_contract": [
                "selected candidate can commit when it is positive and strong in its own view",
                "high score margin can override weak rival-positive evidence",
                "strong rival evidence still blocks direct commit",
            ],
            "failure_modes_addressed": [
                "large repeated furniture false commit from detector-supported but identity-invalid instance",
                "selected-vs-rival ambiguity after expanded retrieval",
                "visit-position-only evidence being treated as instance identity proof",
            ],
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row["uses_gt_for_analysis"] for row in evidence_rows),
        "output_files": {
            "rows": "external_candidate_second_stage_identity_evidence_rows.jsonl",
            "summary": "external_candidate_second_stage_identity_evidence_summary.json",
        },
    }
    write_json(out_root / "external_candidate_second_stage_identity_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze H001 second-stage identity-confirmation evidence.")
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--second-stage-plan", required=True)
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--observed-only", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--objective-version", choices=["v1", "v2"], default="v1")
    parser.add_argument("--allow-direct-commit", action=argparse.BooleanOptionalAction, default=False)
    parser.add_argument("--min-identity-score", type=float, default=0.35)
    parser.add_argument("--min-identity-margin", type=float, default=0.20)
    parser.add_argument("--min-strong-strict-association-count", type=float, default=2.0)
    parser.add_argument("--min-strong-mask-hit-count", type=float, default=2.0)
    parser.add_argument("--min-strong-visible-count", type=float, default=3.0)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-second-stage-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-second-stage-positive-evidence-rate", type=float, default=0.30)
    parser.add_argument("--min-second-stage-strong-depth-evidence-rate", type=float, default=0.20)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.0)
    parser.add_argument("--max-no-valid-commit-rate", type=float, default=0.0)
    parser.add_argument("--max-visit-position-only-commit-rate", type=float, default=0.0)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-success-commit-rate", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
