import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.external_candidate_scoring.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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


def feature_index(path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_jsonl(path):
        indexed[(str(row.get("episode_key")), str(row.get("candidate_id")))] = row
    return indexed


def score_from_snapshot(snapshot: Dict[str, Any], feature: Dict[str, Any], field: str) -> float:
    if field == "E0_external_plan_order":
        rank = safe_float(snapshot.get("selection_rank")) or 9999.0
        return 1.0 / max(1.0, rank)
    if field == "E1_semantic_prior":
        value = safe_float(feature.get("S_sem"))
        if value is not None:
            return value
        rank = safe_float(snapshot.get("semantic_rank")) or 9999.0
        return 1.0 / max(1.0, rank)
    if field == "E2_detector_score":
        return safe_float(feature.get("N1_detector_score_only")) or safe_float(feature.get("S_det")) or 0.0
    if field == "E3_projection_support":
        return safe_float(feature.get("N2_projection_support_no_depth")) or safe_float(feature.get("S_proj")) or 0.0
    if field == "E4_object_node_full":
        return safe_float(feature.get("N5_object_node_evidence_full")) or 0.0
    if field == "E5_positive_support_then_semantic":
        support = 1.0 if feature.get("object_node_positive_support") is True else 0.0
        detector = safe_float(feature.get("object_node_supported_score")) or safe_float(feature.get("S_det")) or 0.0
        semantic = safe_float(feature.get("S_sem")) or 0.0
        return support + 0.25 * detector + 0.05 * semantic
    raise ValueError(f"unknown scoring field: {field}")


def feature_for_candidate(
    branch: Dict[str, Any],
    snapshot: Dict[str, Any],
    features: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    episode_key = str(branch.get("episode_key"))
    candidate_id = str(snapshot.get("candidate_id"))
    feature = dict(features.get((episode_key, candidate_id)) or {})
    if not feature:
        feature = {
            "episode_key": episode_key,
            "candidate_id": candidate_id,
            "candidate_correct": snapshot.get("candidate_correct"),
            "candidate_reachable": snapshot.get("candidate_reachable"),
            "S_sem": snapshot.get("S_sem"),
            "N2_projection_support_no_depth": snapshot.get("N2_projection_support_no_depth"),
            "N5_object_node_evidence_full": snapshot.get("N5_object_node_evidence_full"),
        }
    return feature


def select_candidate(
    branch: Dict[str, Any],
    features: Dict[Tuple[str, str], Dict[str, Any]],
    variant: str,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    candidates = list(branch.get("external_candidates") or [])
    scored: List[Dict[str, Any]] = []
    for snapshot in candidates:
        feature = feature_for_candidate(branch, snapshot, features)
        score = score_from_snapshot(snapshot, feature, variant)
        scored.append(
            {
                "candidate_id": str(snapshot.get("candidate_id")),
                "selection_rank": snapshot.get("selection_rank"),
                "external_pool_rank": snapshot.get("external_pool_rank"),
                "semantic_rank": snapshot.get("semantic_rank"),
                "score": score,
                "candidate_correct": feature.get("candidate_correct"),
                "candidate_reachable": feature.get("candidate_reachable"),
                "object_node_positive_support": feature.get("object_node_positive_support"),
                "S_sem": feature.get("S_sem"),
                "S_det": feature.get("S_det"),
                "S_proj": feature.get("S_proj"),
                "S_depth": feature.get("S_depth"),
                "S_prop": feature.get("S_prop"),
                "R_amb": feature.get("R_amb"),
                "N1_detector_score_only": feature.get("N1_detector_score_only"),
                "N2_projection_support_no_depth": feature.get("N2_projection_support_no_depth"),
                "N5_object_node_evidence_full": feature.get("N5_object_node_evidence_full"),
            }
        )
    scored.sort(key=lambda row: (safe_float(row.get("score")) or 0.0, -int(row.get("selection_rank") or 9999)), reverse=True)
    selected = scored[0] if scored else {}
    second_score = safe_float(scored[1].get("score")) if len(scored) > 1 else None
    selected_score = safe_float(selected.get("score")) or 0.0
    margin = selected_score - (second_score if second_score is not None else 0.0)
    support_ok = selected.get("object_node_positive_support") is True
    if not bool(args.require_positive_support_for_commit):
        support_ok = True
    commit = bool(
        scored
        and support_ok
        and selected_score >= float(args.min_commit_score)
        and margin >= float(args.min_commit_margin)
    )
    return {
        "selected": selected,
        "scored_candidates": scored,
        "selected_score": selected_score,
        "second_score": second_score,
        "score_margin": margin,
        "commit": commit,
        "defer_reason": None if commit else "external_score_not_commit_safe",
    }


def summarize_variant(rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    total = len(rows)
    commit_rows = [row for row in rows if row["external_v1_commits"]]
    wrong_commits = [row for row in commit_rows if row.get("selected_candidate_correct") is False]
    success_commits = [row for row in commit_rows if row.get("selected_candidate_correct") is True]
    contains_correct = [row for row in rows if row.get("external_set_contains_correct") is True]
    first_correct = [row for row in rows if row.get("first_external_correct") is True]
    selected_correct = [row for row in rows if row.get("selected_candidate_correct") is True]
    contains_correct_but_deferred = [
        row for row in rows
        if row.get("external_set_contains_correct") is True and row["external_v1_commits"] is False
    ]
    by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        label = str(row.get("label_case"))
        if row["external_v1_commits"]:
            bucket = "commit_success" if row.get("selected_candidate_correct") is True else "commit_wrong"
        else:
            bucket = "defer"
        by_label[label][bucket] += 1
    gate = {
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_selected_correct_improvement_over_first": float(args.min_selected_correct_improvement_over_first),
        "commit_rate": ratio(len(commit_rows), total),
        "wrong_goal_commit_rate": ratio(len(wrong_commits), total),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commits), len(commit_rows)),
        "success_commit_rate": ratio(len(success_commits), total),
        "external_set_contains_correct_rate": ratio(len(contains_correct), total),
        "first_external_correct_rate": ratio(len(first_correct), total),
        "selected_correct_rate_if_forced": ratio(len(selected_correct), total),
        "selected_correct_improvement_over_first": ratio(len(selected_correct) - len(first_correct), total),
        "contains_correct_but_deferred_rate": ratio(len(contains_correct_but_deferred), total),
    }
    gate["passes_external_scoring_safety_gate"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
    )
    gate["passes_external_scoring_full_gate"] = bool(
        gate["passes_external_scoring_safety_gate"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and (gate["selected_correct_improvement_over_first"] or 0.0)
        >= float(args.min_selected_correct_improvement_over_first)
    )
    return {
        "variant": rows[0]["scoring_variant"] if rows else None,
        "rows": total,
        "action_counts": {
            "external_v1_commit_candidate": len(commit_rows),
            "external_v1_defer": total - len(commit_rows),
        },
        "action_by_label_case": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(by_label.items())
        },
        "gate": gate,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    branch_rows = load_jsonl(Path(args.external_branch_rows))
    features = feature_index(Path(args.object_node_features))
    variants = [
        "E0_external_plan_order",
        "E1_semantic_prior",
        "E2_detector_score",
        "E3_projection_support",
        "E4_object_node_full",
        "E5_positive_support_then_semantic",
    ]
    out_root = Path(args.out_root)
    all_rows: List[Dict[str, Any]] = []
    variant_summaries: List[Dict[str, Any]] = []
    for variant in variants:
        variant_rows: List[Dict[str, Any]] = []
        for source_index, branch in enumerate(branch_rows):
            candidates = branch.get("external_candidates") or []
            flags = [candidate.get("candidate_correct") is True for candidate in candidates]
            selected = select_candidate(branch, features, variant, args)
            selected_candidate = selected["selected"]
            row = {
                "schema_version": SCHEMA_VERSION,
                "source_index": source_index,
                "external_branch_id": branch.get("external_branch_id"),
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
                "external_set_contains_correct": any(flags),
                "first_external_correct": bool(flags[0]) if flags else False,
                "scoring_variant": variant,
                "selected_candidate_id": selected_candidate.get("candidate_id"),
                "selected_candidate_correct": selected_candidate.get("candidate_correct"),
                "selected_candidate_selection_rank": selected_candidate.get("selection_rank"),
                "selected_candidate_external_pool_rank": selected_candidate.get("external_pool_rank"),
                "selected_score": selected["selected_score"],
                "second_score": selected["second_score"],
                "score_margin": selected["score_margin"],
                "external_v1_action": "external_v1_commit_candidate" if selected["commit"] else "external_v1_defer",
                "external_v1_reason": "score_margin_with_positive_object_node_support" if selected["commit"] else selected["defer_reason"],
                "external_v1_commits": selected["commit"],
                "external_v1_wrong_goal_commit": bool(selected["commit"] and selected_candidate.get("candidate_correct") is False),
                "external_v1_success_commit": bool(selected["commit"] and selected_candidate.get("candidate_correct") is True),
                "scored_candidates": selected["scored_candidates"],
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
            variant_rows.append(row)
            all_rows.append(row)
        variant_summaries.append(summarize_variant(variant_rows, args))
    best = max(
        variant_summaries,
        key=lambda row: (
            row["gate"]["passes_external_scoring_full_gate"] is True,
            row["gate"]["passes_external_scoring_safety_gate"] is True,
            row["gate"]["selected_correct_improvement_over_first"] or -1.0,
            row["gate"]["commit_rate"] or -1.0,
            -(row["gate"]["wrong_goal_commit_rate"] or 0.0),
        ),
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "external_branch_rows": str(args.external_branch_rows),
        "object_node_features": str(args.object_node_features),
        "feature_source_role": str(args.feature_source_role),
        "rows": len(branch_rows),
        "variants": variants,
        "best_variant": best["variant"],
        "best_variant_gate": best["gate"],
        "variant_summaries": variant_summaries,
        "thresholds": {
            "min_commit_score": float(args.min_commit_score),
            "min_commit_margin": float(args.min_commit_margin),
            "require_positive_support_for_commit": bool(args.require_positive_support_for_commit),
            "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
            "min_commit_rate": float(args.min_commit_rate),
            "min_selected_correct_improvement_over_first": float(args.min_selected_correct_improvement_over_first),
        },
        "diagnosis": {
            "branch_role": "score_v4b_external_search_cases_before_detector_scale_rerun",
            "commit_status": "diagnostic_only_not_policy_commit",
            "paper_claim_status": "blocked_until_external_observation_detector_scoring_passes_heldout_gate",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "external_candidate_scoring_v1_rows.jsonl",
            "summary": "external_candidate_scoring_v1_summary.json",
        },
    }
    write_jsonl(out_root / "external_candidate_scoring_v1_rows.jsonl", all_rows)
    write_json(out_root / "external_candidate_scoring_v1_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score H001 V4b external-candidate search branches.")
    parser.add_argument("--external-branch-rows", required=True)
    parser.add_argument("--object-node-features", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--feature-source-role", default="proxy_object_node_features_not_external_observation")
    parser.add_argument("--min-commit-score", type=float, default=0.15)
    parser.add_argument("--min-commit-margin", type=float, default=0.05)
    parser.add_argument("--require-positive-support-for-commit", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.10)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-selected-correct-improvement-over-first", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
