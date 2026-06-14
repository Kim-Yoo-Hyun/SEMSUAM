import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.analyze_object_node_evidence_objective import projection_proximity
from h001_runtime.export_postview_frames_v2 import decision_id


SCHEMA_VERSION = "h001.external_candidate_observation_evidence.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_jsonl_optional(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return load_jsonl(path)


def load_json_optional(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def plan_index(plan_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {decision_id(row): row for row in plan_rows}


def branch_index(branch_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in branch_rows}


def candidate_snapshot_index(branch: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(candidate.get("candidate_id")): candidate
        for candidate in branch.get("external_candidates") or []
    }


def candidate_support(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    detector_scores = [safe_float(row.get("best_box_score")) for row in rows]
    detector_scores = [value for value in detector_scores if value is not None]
    visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
    box_hits = [row for row in visible_rows if row.get("projected_pixel_inside_box") is True]
    mask_hits = [row for row in visible_rows if row.get("projected_pixel_inside_mask") is True]
    strict_hits = [row for row in rows if row.get("associated_to_candidate") is True]
    proximity = [projection_proximity(row) for row in rows]

    s_det = max(detector_scores) if detector_scores else 0.0
    s_proj = min(1.0, (len(mask_hits) + 0.5 * max(0, len(box_hits) - len(mask_hits))) / 3.0)
    s_depth = min(1.0, len(strict_hits) / 2.0)
    s_mask = min(1.0, len(mask_hits) / 2.0)
    s_prox = max(proximity, default=0.0)
    score = max(
        0.0,
        min(1.0, 0.25 * s_det + 0.20 * s_proj + 0.30 * s_depth + 0.15 * s_mask + 0.10 * s_prox),
    )
    return {
        "detector_score_max": s_det,
        "visible_count": len(visible_rows),
        "box_hit_count": len(box_hits),
        "mask_hit_count": len(mask_hits),
        "strict_association_count": len(strict_hits),
        "S_ext_proj": s_proj,
        "S_ext_depth": s_depth,
        "S_ext_mask": s_mask,
        "S_ext_proximity": s_prox,
        "S_ext": score,
        "positive_support": bool(len(strict_hits) > 0 or len(mask_hits) > 0),
    }


def select_branch_candidate(
    candidates: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], Optional[float], float, str]:
    if not candidates:
        return None, None, 0.0, "no_external_candidates"
    ranked = sorted(
        candidates,
        key=lambda row: (
            safe_float(row.get("S_ext")) or 0.0,
            safe_float(row.get("detector_score_max")) or 0.0,
            -int(row.get("external_branch_rank") or 9999),
        ),
        reverse=True,
    )
    best = ranked[0]
    second_score = safe_float(ranked[1].get("S_ext")) if len(ranked) > 1 else None
    best_score = safe_float(best.get("S_ext")) or 0.0
    margin = best_score - (second_score if second_score is not None else 0.0)
    if best.get("positive_support") is not True:
        return best, second_score, margin, "defer_no_positive_external_evidence"
    if best_score < float(args.min_commit_score):
        return best, second_score, margin, "defer_weak_external_evidence"
    if margin < float(args.min_commit_margin):
        return best, second_score, margin, "defer_ambiguous_external_evidence"
    if float(best.get("strict_association_count") or 0.0) < float(args.min_strict_association_count):
        return best, second_score, margin, "defer_insufficient_strict_association"
    return best, second_score, margin, "commit_external_candidate"


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
        branch_id = str(plan.get("external_branch_id"))
        candidate_id = str(row.get("candidate_id"))
        rows_by_branch_candidate[(branch_id, candidate_id)].append(row)

    evidence_rows: List[Dict[str, Any]] = []
    for branch_id, branch in sorted(branches.items()):
        snapshots = candidate_snapshot_index(branch)
        candidate_rows: List[Dict[str, Any]] = []
        for candidate_id in branch.get("external_candidate_ids") or []:
            snapshot = snapshots.get(str(candidate_id), {})
            support = candidate_support(rows_by_branch_candidate.get((branch_id, str(candidate_id)), []))
            candidate_rows.append(
                {
                    "candidate_id": str(candidate_id),
                    "external_branch_rank": snapshot.get("selection_rank"),
                    "external_pool_rank": snapshot.get("external_pool_rank"),
                    "semantic_rank": snapshot.get("semantic_rank"),
                    "candidate_correct": snapshot.get("candidate_correct"),
                    "candidate_reachable": snapshot.get("candidate_reachable"),
                    "semantic_score": snapshot.get("score"),
                    **support,
                }
            )

        selected, second_score, margin, decision = select_branch_candidate(candidate_rows, args)
        selected = selected or {}
        action = "external_evidence_v1_commit_candidate" if decision == "commit_external_candidate" else "external_evidence_v1_defer"
        contains_correct = any(row.get("candidate_correct") is True for row in candidate_rows)
        first = min(candidate_rows, key=lambda row: int(row.get("external_branch_rank") or 9999), default={})
        selected_correct = selected.get("candidate_correct")
        row = {
            "schema_version": SCHEMA_VERSION,
            "external_branch_id": branch_id,
            "episode_key": branch.get("episode_key"),
            "scene_id": branch.get("scene_id"),
            "query": branch.get("query"),
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
            "external_evidence_v1_action": action,
            "external_evidence_v1_reason": decision,
            "external_evidence_v1_commits": action == "external_evidence_v1_commit_candidate",
            "external_evidence_v1_success_commit": bool(action == "external_evidence_v1_commit_candidate" and selected_correct is True),
            "external_evidence_v1_wrong_goal_commit": bool(action == "external_evidence_v1_commit_candidate" and selected_correct is False),
            "external_evidence_v1_no_valid_external_commit": bool(action == "external_evidence_v1_commit_candidate" and not contains_correct),
            "candidate_evidence": candidate_rows,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": any(row.get("candidate_correct") is not None for row in candidate_rows),
        }
        evidence_rows.append(row)

    write_jsonl(out_root / "external_candidate_evidence_rows.jsonl", evidence_rows)

    commit_rows = [row for row in evidence_rows if row["external_evidence_v1_commits"]]
    wrong_commits = [row for row in commit_rows if row["external_evidence_v1_wrong_goal_commit"]]
    success_commits = [row for row in commit_rows if row["external_evidence_v1_success_commit"]]
    no_valid_commits = [row for row in commit_rows if row["external_evidence_v1_no_valid_external_commit"]]
    evidence_available = [
        row for row in evidence_rows
        if any((candidate.get("S_ext") or 0.0) > 0.0 for candidate in row.get("candidate_evidence") or [])
    ]
    positive_evidence = [
        row for row in evidence_rows
        if any(candidate.get("positive_support") is True for candidate in row.get("candidate_evidence") or [])
    ]
    first_correct = [row for row in evidence_rows if row.get("first_external_correct") is True]
    selected_correct = [row for row in evidence_rows if row.get("selected_candidate_correct") is True]
    action_counts = Counter(row["external_evidence_v1_action"] for row in evidence_rows)
    reason_counts = Counter(row["external_evidence_v1_reason"] for row in evidence_rows)
    by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in evidence_rows:
        by_label[str(row.get("label_case"))][str(row["external_evidence_v1_action"])] += 1

    detector_box_rate = detector_summary.get("rows_with_detector_box_rate")
    sam2_mask_rate = detector_summary.get("rows_with_sam2_mask_rate")
    candidate_association_rate = detector_summary.get("rows_with_candidate_association_rate")
    gate = {
        "min_detector_box_rate": float(args.min_detector_box_rate),
        "min_sam2_mask_rate": float(args.min_sam2_mask_rate),
        "min_candidate_association_rate": float(args.min_candidate_association_rate),
        "min_external_evidence_available_rate": float(args.min_external_evidence_available_rate),
        "min_external_positive_evidence_rate": float(args.min_external_positive_evidence_rate),
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_no_valid_external_commit_rate": float(args.max_no_valid_external_commit_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_selected_correct_improvement_over_first": float(args.min_selected_correct_improvement_over_first),
        "detector_box_rate": detector_box_rate,
        "sam2_mask_rate": sam2_mask_rate,
        "candidate_association_rate": candidate_association_rate,
        "external_evidence_available_rate": ratio(len(evidence_available), len(evidence_rows)),
        "external_positive_evidence_rate": ratio(len(positive_evidence), len(evidence_rows)),
        "commit_rate": ratio(len(commit_rows), len(evidence_rows)),
        "success_commit_rate": ratio(len(success_commits), len(evidence_rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_commits), len(evidence_rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commits), len(commit_rows)),
        "no_valid_external_commit_rate": ratio(len(no_valid_commits), len(evidence_rows)),
        "external_set_contains_correct_rate": ratio(
            sum(row.get("external_set_contains_correct") is True for row in evidence_rows),
            len(evidence_rows),
        ),
        "first_external_correct_rate": ratio(len(first_correct), len(evidence_rows)),
        "selected_correct_rate_if_forced": ratio(len(selected_correct), len(evidence_rows)),
        "selected_correct_improvement_over_first": ratio(len(selected_correct) - len(first_correct), len(evidence_rows)),
    }
    gate["passes_external_detector_substrate_gate"] = bool(
        (safe_float(detector_box_rate) or 0.0) >= float(args.min_detector_box_rate)
        and (safe_float(sam2_mask_rate) or 0.0) >= float(args.min_sam2_mask_rate)
        and (safe_float(candidate_association_rate) or 0.0) >= float(args.min_candidate_association_rate)
    )
    gate["passes_external_evidence_safety_gate"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["no_valid_external_commit_rate"] or 0.0) <= float(args.max_no_valid_external_commit_rate)
    )
    gate["passes_external_evidence_full_gate"] = bool(
        gate["passes_external_detector_substrate_gate"]
        and gate["passes_external_evidence_safety_gate"]
        and (gate["external_evidence_available_rate"] or 0.0) >= float(args.min_external_evidence_available_rate)
        and (gate["external_positive_evidence_rate"] or 0.0) >= float(args.min_external_positive_evidence_rate)
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and (gate["selected_correct_improvement_over_first"] or 0.0)
        >= float(args.min_selected_correct_improvement_over_first)
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "external_observation_plan": str(args.external_observation_plan),
        "external_branch_rows": str(args.external_branch_rows),
        "detector_root": str(args.detector_root),
        "rows": len(evidence_rows),
        "plan_rows": len(plan_rows),
        "association_rows": len(association_rows),
        "unmatched_association_rows": unmatched_association_rows,
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "action_by_label_case": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(by_label.items())
        },
        "thresholds": {
            "min_commit_score": float(args.min_commit_score),
            "min_commit_margin": float(args.min_commit_margin),
            "min_strict_association_count": float(args.min_strict_association_count),
        },
        "gate": gate,
        "diagnosis": {
            "branch_role": "actual_external_view_detector_evidence_gate",
            "commit_status": "allowed_only_when_external_view_evidence_is_positive_margin_safe",
            "paper_claim_status": "blocked_until_this_gate_passes_on_heldout_detector_artifact",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row["uses_gt_for_analysis"] for row in evidence_rows),
        "output_files": {
            "rows": "external_candidate_evidence_rows.jsonl",
            "summary": "external_candidate_evidence_summary.json",
        },
    }
    write_json(out_root / "external_candidate_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze H001 actual external-candidate detector evidence.")
    parser.add_argument("--external-observation-plan", required=True)
    parser.add_argument("--external-branch-rows", required=True)
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-commit-score", type=float, default=0.35)
    parser.add_argument("--min-commit-margin", type=float, default=0.10)
    parser.add_argument("--min-strict-association-count", type=float, default=1.0)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-candidate-association-rate", type=float, default=0.20)
    parser.add_argument("--min-external-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-external-positive-evidence-rate", type=float, default=0.30)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-no-valid-external-commit-rate", type=float, default=0.10)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-selected-correct-improvement-over-first", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
