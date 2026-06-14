import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from h001_runtime.analyze_object_node_evidence_objective import PROPERTY_GROUP_BY_QUERY
from h001_runtime.analyze_external_candidate_observation_evidence_v3 import (
    SCHEMA_VERSION as V3_SCHEMA_VERSION,
    branch_index,
    candidate_snapshot_index,
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


SCHEMA_VERSION = "h001.external_candidate_observation_evidence.v4"


def action_for_reason(reason: str) -> str:
    if reason == "commit_identity_confirmed_candidate":
        return "external_evidence_v4_commit_candidate"
    if reason.startswith("request_identity_confirmation"):
        return "external_evidence_v4_request_identity_confirmation"
    if reason.startswith("request_expanded_retrieval"):
        return "external_evidence_v4_request_expanded_retrieval"
    return "external_evidence_v4_defer"


def select_branch_candidate_v4(
    candidates: List[Dict[str, Any]],
    query: str,
    source_reason: str,
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], Optional[float], float, str, Dict[str, Any]]:
    if not candidates:
        return None, None, 0.0, "request_expanded_retrieval_no_external_candidates", {}
    ranked = ranked_candidates(candidates)
    best = ranked[0]
    second = ranked[1] if len(ranked) > 1 else None
    second_score = safe_float(second.get("S_ext")) if second else None
    best_score = safe_float(best.get("S_ext")) or 0.0
    margin = best_score - (second_score if second_score is not None else 0.0)
    property_group = PROPERTY_GROUP_BY_QUERY.get(query, "unknown")
    best_strong = strong_depth_evidence(best, args)
    strong_candidates = [row for row in candidates if strong_depth_evidence(row, args)]
    positive_count = sum(row.get("positive_support") is True for row in candidates)
    best_rank = int(best.get("external_branch_rank") or 9999)
    guard = {
        "property_group": property_group,
        "source_objective_reason": source_reason,
        "best_strong_depth_evidence": best_strong,
        "best_external_branch_rank": best_rank,
        "strong_candidate_count": len(strong_candidates),
        "positive_candidate_count": positive_count,
        "identity_confirmed_single_instance": False,
        "retrieval_validity_confirmed": False,
    }

    if best.get("positive_support") is not True:
        return best, second_score, margin, "request_expanded_retrieval_no_positive_external_evidence", guard
    if best_score < float(args.min_commit_score):
        return best, second_score, margin, "request_expanded_retrieval_weak_external_evidence", guard
    if not best_strong:
        return best, second_score, margin, "request_expanded_retrieval_without_strong_depth_association", guard

    if property_group == "large_repeated_furniture":
        identity_confirmed = bool(
            best_rank <= int(args.max_identity_confirmed_rank)
            and margin >= float(args.min_identity_confirmed_margin)
            and len(strong_candidates) == 1
        )
        guard["identity_confirmed_single_instance"] = identity_confirmed
        guard["retrieval_validity_confirmed"] = bool(best_rank <= int(args.max_identity_confirmed_rank))
        if identity_confirmed:
            return best, second_score, margin, "commit_identity_confirmed_candidate", guard
        if len(strong_candidates) > 1:
            return best, second_score, margin, "request_identity_confirmation_multiple_strong_instances", guard
        if best_rank > int(args.max_identity_confirmed_rank):
            return best, second_score, margin, "request_identity_confirmation_low_retrieval_rank", guard
        return best, second_score, margin, "request_identity_confirmation_not_contrastive", guard

    if property_group == "small_or_cluttered":
        if margin < float(args.min_small_or_cluttered_commit_margin):
            return best, second_score, margin, "defer_small_or_cluttered_not_contrastive", guard
        if float(best.get("strict_association_count") or 0.0) < float(args.min_small_or_cluttered_strict_count):
            return best, second_score, margin, "defer_small_or_cluttered_weak_depth", guard
        guard["identity_confirmed_single_instance"] = True
        return best, second_score, margin, "commit_identity_confirmed_candidate", guard

    if margin < float(args.min_commit_margin):
        return best, second_score, margin, "defer_not_contrastive", guard
    guard["identity_confirmed_single_instance"] = True
    return best, second_score, margin, "commit_identity_confirmed_candidate", guard


def summarize(rows: List[Dict[str, Any]], detector_summary: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    commit_rows = [row for row in rows if row["external_evidence_v4_commits"]]
    wrong_commits = [row for row in commit_rows if row["external_evidence_v4_wrong_goal_commit"]]
    success_commits = [row for row in commit_rows if row["external_evidence_v4_success_commit"]]
    no_valid_commits = [row for row in commit_rows if row["external_evidence_v4_no_valid_external_commit"]]
    identity_requests = [row for row in rows if row["external_evidence_v4_action"] == "external_evidence_v4_request_identity_confirmation"]
    retrieval_requests = [row for row in rows if row["external_evidence_v4_action"] == "external_evidence_v4_request_expanded_retrieval"]
    evidence_available = [
        row for row in rows
        if any((candidate.get("S_ext") or 0.0) > 0.0 for candidate in row.get("candidate_evidence") or [])
    ]
    positive_evidence = [
        row for row in rows
        if any(candidate.get("positive_support") is True for candidate in row.get("candidate_evidence") or [])
    ]
    strong_depth_rows = [
        row for row in rows
        if any(candidate.get("v4_strong_depth_evidence") is True for candidate in row.get("candidate_evidence") or [])
    ]
    first_correct = [row for row in rows if row.get("first_external_correct") is True]
    selected_correct = [row for row in rows if row.get("selected_candidate_correct") is True]
    action_counts = Counter(row["external_evidence_v4_action"] for row in rows)
    reason_counts = Counter(row["external_evidence_v4_reason"] for row in rows)
    by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    by_property: Dict[str, Counter[str]] = defaultdict(Counter)
    by_source_reason: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        by_label[str(row.get("label_case"))][str(row["external_evidence_v4_action"])] += 1
        by_property[str(row.get("property_group"))][str(row["external_evidence_v4_action"])] += 1
        by_source_reason[str(row.get("source_objective_reason"))][str(row["external_evidence_v4_action"])] += 1

    detector_box_rate = detector_summary.get("rows_with_detector_box_rate")
    sam2_mask_rate = detector_summary.get("rows_with_sam2_mask_rate")
    candidate_association_rate = detector_summary.get("rows_with_candidate_association_rate")
    gate = {
        "min_detector_box_rate": float(args.min_detector_box_rate),
        "min_sam2_mask_rate": float(args.min_sam2_mask_rate),
        "min_external_evidence_available_rate": float(args.min_external_evidence_available_rate),
        "min_external_positive_evidence_rate": float(args.min_external_positive_evidence_rate),
        "min_branch_strong_depth_evidence_rate": float(args.min_branch_strong_depth_evidence_rate),
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_no_valid_external_commit_rate": float(args.max_no_valid_external_commit_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_success_commit_rate": float(args.min_success_commit_rate),
        "detector_box_rate": detector_box_rate,
        "sam2_mask_rate": sam2_mask_rate,
        "candidate_association_rate_diagnostic": candidate_association_rate,
        "external_evidence_available_rate": ratio(len(evidence_available), len(rows)),
        "external_positive_evidence_rate": ratio(len(positive_evidence), len(rows)),
        "branch_strong_depth_evidence_rate": ratio(len(strong_depth_rows), len(rows)),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "success_commit_rate": ratio(len(success_commits), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_commits), len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commits), len(commit_rows)),
        "no_valid_external_commit_rate": ratio(len(no_valid_commits), len(rows)),
        "identity_confirmation_request_rate": ratio(len(identity_requests), len(rows)),
        "expanded_retrieval_request_rate": ratio(len(retrieval_requests), len(rows)),
        "external_set_contains_correct_rate": ratio(
            sum(row.get("external_set_contains_correct") is True for row in rows),
            len(rows),
        ),
        "first_external_correct_rate": ratio(len(first_correct), len(rows)),
        "selected_correct_rate_if_forced": ratio(len(selected_correct), len(rows)),
        "selected_correct_improvement_over_first": ratio(len(selected_correct) - len(first_correct), len(rows)),
    }
    gate["passes_external_detector_substrate_gate_v4"] = bool(
        (safe_float(detector_box_rate) or 0.0) >= float(args.min_detector_box_rate)
        and (safe_float(sam2_mask_rate) or 0.0) >= float(args.min_sam2_mask_rate)
        and (gate["external_evidence_available_rate"] or 0.0) >= float(args.min_external_evidence_available_rate)
        and (gate["external_positive_evidence_rate"] or 0.0) >= float(args.min_external_positive_evidence_rate)
        and (gate["branch_strong_depth_evidence_rate"] or 0.0) >= float(args.min_branch_strong_depth_evidence_rate)
    )
    gate["passes_external_evidence_safety_gate_v4"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["no_valid_external_commit_rate"] or 0.0) <= float(args.max_no_valid_external_commit_rate)
    )
    gate["passes_external_evidence_full_gate_v4"] = bool(
        gate["passes_external_detector_substrate_gate_v4"]
        and gate["passes_external_evidence_safety_gate_v4"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and (gate["success_commit_rate"] or 0.0) >= float(args.min_success_commit_rate)
    )
    return {
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "action_by_label_case": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(by_label.items())
        },
        "action_by_property_group": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(by_property.items())
        },
        "action_by_source_objective_reason": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(by_source_reason.items())
        },
        "gate": gate,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.external_observation_plan))
    branch_rows = load_jsonl(Path(args.external_branch_rows))
    branches = branch_index(branch_rows)
    detector_root = Path(args.detector_root)
    detector_summary = load_json_optional(detector_root / "summary.json")
    association_rows = load_jsonl_optional(detector_root / "detector_candidate_associations.jsonl")
    decision_to_plan = plan_index(plan_rows)

    rows_by_branch_candidate: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    unmatched_association_rows = 0
    for row in association_rows:
        plan = decision_to_plan.get(str(row.get("decision_id")))
        if plan is None:
            unmatched_association_rows += 1
            continue
        rows_by_branch_candidate[(str(plan.get("external_branch_id")), str(row.get("candidate_id")))].append(row)

    evidence_rows: List[Dict[str, Any]] = []
    for branch_id, branch in sorted(branches.items()):
        query = str(branch.get("query"))
        source_reason = str(branch.get("source_objective_reason"))
        snapshots = candidate_snapshot_index(branch)
        candidate_rows: List[Dict[str, Any]] = []
        for candidate_id in branch.get("external_candidate_ids") or []:
            snapshot = snapshots.get(str(candidate_id), {})
            support = candidate_support(rows_by_branch_candidate.get((branch_id, str(candidate_id)), []))
            candidate_row = {
                "candidate_id": str(candidate_id),
                "external_branch_rank": snapshot.get("selection_rank"),
                "external_pool_rank": snapshot.get("external_pool_rank"),
                "semantic_rank": snapshot.get("semantic_rank"),
                "candidate_correct": snapshot.get("candidate_correct"),
                "candidate_reachable": snapshot.get("candidate_reachable"),
                "semantic_score": snapshot.get("score"),
                **support,
            }
            candidate_row["v4_strong_depth_evidence"] = strong_depth_evidence(candidate_row, args)
            candidate_rows.append(candidate_row)

        selected, second_score, margin, reason, guard = select_branch_candidate_v4(
            candidate_rows,
            query,
            source_reason,
            args,
        )
        selected = selected or {}
        action = action_for_reason(reason)
        contains_correct = any(row.get("candidate_correct") is True for row in candidate_rows)
        first = min(candidate_rows, key=lambda row: int(row.get("external_branch_rank") or 9999), default={})
        selected_correct = selected.get("candidate_correct")
        evidence_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "v3_schema_version": V3_SCHEMA_VERSION,
                "external_branch_id": branch_id,
                "episode_key": branch.get("episode_key"),
                "scene_id": branch.get("scene_id"),
                "query": query,
                "property_group": guard.get("property_group"),
                "label_case": branch.get("label_case"),
                "source_objective_prefix": branch.get("source_objective_prefix"),
                "source_objective_action": branch.get("source_objective_action"),
                "source_objective_reason": branch.get("source_objective_reason"),
                "external_branch_trigger_reason": branch.get("external_branch_trigger_reason"),
                "external_budget": branch.get("external_budget"),
                "external_pool_size": branch.get("external_pool_size"),
                "external_candidate_ids": branch.get("external_candidate_ids"),
                "external_set_contains_correct": contains_correct,
                "first_external_candidate_id": first.get("candidate_id"),
                "first_external_correct": first.get("candidate_correct"),
                "selected_candidate_id": selected.get("candidate_id"),
                "selected_candidate_correct": selected_correct,
                "selected_candidate_external_branch_rank": selected.get("external_branch_rank"),
                "selected_score": selected.get("S_ext"),
                "second_score": second_score,
                "score_margin": margin,
                "external_evidence_v4_action": action,
                "external_evidence_v4_reason": reason,
                "external_evidence_v4_commits": action == "external_evidence_v4_commit_candidate",
                "external_evidence_v4_success_commit": bool(action == "external_evidence_v4_commit_candidate" and selected_correct is True),
                "external_evidence_v4_wrong_goal_commit": bool(action == "external_evidence_v4_commit_candidate" and selected_correct is False),
                "external_evidence_v4_no_valid_external_commit": bool(action == "external_evidence_v4_commit_candidate" and not contains_correct),
                "v4_guard": guard,
                "candidate_evidence": candidate_rows,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": any(row.get("candidate_correct") is not None for row in candidate_rows),
            }
        )

    write_jsonl(out_root / "external_candidate_evidence_v4_rows.jsonl", evidence_rows)
    stats = summarize(evidence_rows, detector_summary, args)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "external_observation_plan": str(args.external_observation_plan),
        "external_branch_rows": str(args.external_branch_rows),
        "detector_root": str(args.detector_root),
        "rows": len(evidence_rows),
        "plan_rows": len(plan_rows),
        "association_rows": len(association_rows),
        "unmatched_association_rows": unmatched_association_rows,
        **stats,
        "thresholds": {
            "min_commit_score": float(args.min_commit_score),
            "min_commit_margin": float(args.min_commit_margin),
            "min_strong_strict_association_count": float(args.min_strong_strict_association_count),
            "min_strong_mask_hit_count": float(args.min_strong_mask_hit_count),
            "min_strong_visible_count": float(args.min_strong_visible_count),
            "min_small_or_cluttered_strict_count": float(args.min_small_or_cluttered_strict_count),
            "min_small_or_cluttered_commit_margin": float(args.min_small_or_cluttered_commit_margin),
            "max_identity_confirmed_rank": int(args.max_identity_confirmed_rank),
            "min_identity_confirmed_margin": float(args.min_identity_confirmed_margin),
        },
        "objective_design": {
            "not_threshold_only": [
                "large repeated furniture is routed through identity-confirmed, identity-ambiguous, or retrieval-invalid states",
                "external observation can request a follow-up identity confirmation instead of forcing commit/defer",
                "commit is allowed only for single strong external instance with high retrieval rank and high contrast",
            ],
            "failure_modes_addressed": [
                "wrong repeated bed instance selected despite strong depth evidence",
                "no-valid external candidate set with strong-looking detector evidence",
                "correct hard bed recovery suppressed by over-conservative V3",
            ],
        },
        "diagnosis": {
            "branch_role": "external_view_identity_confirmation_gate_v4",
            "paper_claim_status": "design_candidate_requires independent validation and actual follow-up identity-observation planner",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row["uses_gt_for_analysis"] for row in evidence_rows),
        "output_files": {
            "rows": "external_candidate_evidence_v4_rows.jsonl",
            "summary": "external_candidate_evidence_v4_summary.json",
        },
    }
    write_json(out_root / "external_candidate_evidence_v4_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze H001 external-candidate identity-confirmation objective v4.")
    parser.add_argument("--external-observation-plan", required=True)
    parser.add_argument("--external-branch-rows", required=True)
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-commit-score", type=float, default=0.35)
    parser.add_argument("--min-commit-margin", type=float, default=0.10)
    parser.add_argument("--min-strong-strict-association-count", type=float, default=2.0)
    parser.add_argument("--min-strong-mask-hit-count", type=float, default=2.0)
    parser.add_argument("--min-strong-visible-count", type=float, default=3.0)
    parser.add_argument("--min-small-or-cluttered-strict-count", type=float, default=2.0)
    parser.add_argument("--min-small-or-cluttered-commit-margin", type=float, default=0.20)
    parser.add_argument("--max-identity-confirmed-rank", type=int, default=2)
    parser.add_argument("--min-identity-confirmed-margin", type=float, default=0.70)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-external-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-external-positive-evidence-rate", type=float, default=0.30)
    parser.add_argument("--min-branch-strong-depth-evidence-rate", type=float, default=0.20)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-no-valid-external-commit-rate", type=float, default=0.10)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-success-commit-rate", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
