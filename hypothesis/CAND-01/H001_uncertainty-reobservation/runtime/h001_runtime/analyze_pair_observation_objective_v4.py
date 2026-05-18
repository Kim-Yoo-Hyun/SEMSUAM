import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from h001_runtime.analyze_pair_observation_objective_v2 import (
    candidate_features,
    label_case,
    load_jsonl,
    pair_key,
    plan_index,
    ratio,
    safe_float,
)
from h001_runtime.analyze_pair_observation_objective_v3 import (
    alt_rejection_evidence,
    strict_rate,
    top_rejection_evidence,
    top_survival_evidence,
)


SCHEMA_VERSION = "h001.pair_observation_objective.v4"


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def top_verified_evidence(
    top: Dict[str, Any],
    alt: Dict[str, Any],
    arb_gap: float,
    view_quality_gap: float,
    args: argparse.Namespace,
) -> bool:
    top_strict_rate = strict_rate(top)
    alt_strict_rate = strict_rate(alt)
    return bool(
        view_quality_gap <= float(args.max_view_quality_gap)
        and float(top["strict_association_count"]) >= float(args.min_top_verified_strict_count)
        and float(top["confirm_score"]) >= float(args.min_top_verified_confirm_score)
        and top_strict_rate - alt_strict_rate >= float(args.min_top_verified_strict_rate_advantage)
        and float(alt["strict_association_count"]) <= float(args.max_alt_strict_count_for_top_verified)
        and float(alt["confirm_score"]) <= float(args.max_alt_confirm_for_top_verified)
        and arb_gap <= float(args.max_prior_alt_gap_for_top_verified)
    )


def v4_decision(row: Dict[str, Any], plan: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    top = candidate_features(row, "top", args)
    alt = candidate_features(row, "alt", args)
    mode = str(row.get("pair_observation_mode"))
    arb_gap = safe_float(plan.get("arbitration_support_gap_alt_minus_top"))
    if arb_gap is None:
        arb_gap = 0.0

    strict_rate_gap_alt_minus_top = strict_rate(alt) - strict_rate(top)
    confirm_gap_alt_minus_top = float(alt["confirm_score"]) - float(top["confirm_score"])
    view_quality_gap = abs(float(alt["view_quality"]) - float(top["view_quality"]))
    alt_has_strict = float(alt["strict_association_count"]) >= 1.0
    top_has_strict = float(top["strict_association_count"]) >= 1.0
    reject_alt = alt_rejection_evidence(top, alt, arb_gap, args)
    reject_top = top_rejection_evidence(top, args)
    top_survives = top_survival_evidence(row, top, alt, arb_gap, view_quality_gap, reject_top, args)
    top_verified = top_verified_evidence(top, alt, arb_gap, view_quality_gap, args)
    both_confirmed = bool(
        float(top["confirm_score"]) >= float(args.min_ambiguous_confirm_score)
        and float(alt["confirm_score"]) >= float(args.min_ambiguous_confirm_score)
    )

    if float(top["view_quality"]) <= 0.0 and float(alt["view_quality"]) <= 0.0:
        action = "pair_v4_defer_no_pair_evidence"
        reason = "no_visible_candidate_opportunity"
    elif top_survives:
        action = "pair_v4_defer_top_survival_untrusted"
        reason = "top_survival_without_comparable_alt_is_not_commit_safe"
    elif view_quality_gap > float(args.max_view_quality_gap):
        action = "pair_v4_defer_view_not_comparable"
        reason = f"{mode}_view_opportunity_imbalance"
    elif reject_alt and reject_top:
        action = "pair_v4_reject_top_confirm_alt"
        reason = "prior_alt_gap_plus_view_normalized_alt_confirmation"
    elif top_verified and not both_confirmed:
        action = "pair_v4_commit_top_verified_pair_evidence"
        reason = "comparable_view_top_confirmed_alt_disconfirmed"
    elif top_has_strict and not alt_has_strict:
        action = "pair_v4_request_external_candidate_search"
        reason = "top_supported_but_pair_set_may_be_incomplete"
    elif both_confirmed:
        action = "pair_v4_defer_rank_ambiguous_or_duplicate_goal"
        reason = "both_candidates_have_confirmation_evidence"
    else:
        action = "pair_v4_defer_insufficient_disconfirmation"
        reason = "no_strong_alt_confirmation_or_verified_top"

    return {
        "pair_v4_action": action,
        "pair_v4_reason": reason,
        "pair_v4_prior_alt_gap": arb_gap,
        "pair_v4_strict_rate_gap_alt_minus_top": strict_rate_gap_alt_minus_top,
        "pair_v4_confirm_gap_alt_minus_top": confirm_gap_alt_minus_top,
        "pair_v4_view_quality_gap": view_quality_gap,
        "pair_v4_alt_rejection_evidence": reject_alt,
        "pair_v4_top_rejection_evidence": reject_top,
        "pair_v4_top_survival_evidence": top_survives,
        "pair_v4_top_verified_evidence": top_verified,
        "pair_v4_both_confirmed": both_confirmed,
        "pair_v4_top_features": top,
        "pair_v4_alt_features": alt,
    }


def committed_candidate_correct(row: Dict[str, Any]) -> Optional[bool]:
    action = row.get("pair_v4_action")
    if action == "pair_v4_commit_top_verified_pair_evidence":
        return row.get("top_candidate_correct")
    if action == "pair_v4_reject_top_confirm_alt":
        return row.get("alt_candidate_correct")
    return None


def run(args: argparse.Namespace) -> Dict[str, Any]:
    pair_rows = load_jsonl(Path(args.pair_evidence_rows))
    plans = plan_index(load_jsonl(Path(args.pair_observation_plan)))
    out_rows: List[Dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    action_by_label_case: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in pair_rows:
        key = pair_key(row)
        decision = v4_decision(row, plans.get(key, {}), args)
        out = {
            "schema_version": SCHEMA_VERSION,
            "pair_observation_id": row.get("pair_observation_id"),
            "episode_key": row.get("episode_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "pair_observation_mode": row.get("pair_observation_mode"),
            "pair_top_candidate_id": row.get("pair_top_candidate_id"),
            "pair_alt_candidate_id": row.get("pair_alt_candidate_id"),
            "pair_v1_action": row.get("pair_evidence_action"),
            "pair_v1_reason": row.get("pair_evidence_reason"),
            "pair_v1_top_score": row.get("pair_top_score"),
            "pair_v1_alt_score": row.get("pair_alt_score"),
            "top_candidate_correct": row.get("top_candidate_correct"),
            "alt_candidate_correct": row.get("alt_candidate_correct"),
            "label_case": label_case(row),
            **decision,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": row.get("uses_gt_for_analysis"),
        }
        committed = committed_candidate_correct(out)
        out["pair_v4_commits"] = committed is not None
        out["pair_v4_committed_candidate_correct"] = committed
        out["pair_v4_wrong_goal_commit"] = committed is False
        out["pair_v4_success_commit"] = committed is True
        out["pair_v4_defer"] = committed is None
        out_rows.append(out)
        action_counts[out["pair_v4_action"]] += 1
        reason_counts[out["pair_v4_reason"]] += 1
        action_by_label_case[out["label_case"]][out["pair_v4_action"]] += 1

    rows_with_labels = [row for row in out_rows if row.get("top_candidate_correct") is not None]
    commit_rows = [row for row in out_rows if row["pair_v4_commits"]]
    wrong_commit_rows = [row for row in out_rows if row["pair_v4_wrong_goal_commit"]]
    success_commit_rows = [row for row in out_rows if row["pair_v4_success_commit"]]
    alt_only = [row for row in out_rows if row["label_case"] == "alt_only_correct"]
    neither = [row for row in out_rows if row["label_case"] == "neither_candidate_correct"]
    both_correct = [row for row in out_rows if row["label_case"] == "both_candidates_correct"]
    top_survival_signals = [row for row in out_rows if row["pair_v4_top_survival_evidence"]]
    top_verified_commits = [
        row for row in out_rows
        if row["pair_v4_action"] == "pair_v4_commit_top_verified_pair_evidence"
    ]
    top_verified_wrong = [
        row for row in top_verified_commits
        if row.get("top_candidate_correct") is False
    ]
    top_survival_commits = [
        row for row in out_rows
        if row["pair_v4_action"] == "pair_v4_commit_top_common_view_survival"
    ]

    gate = {
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_neither_candidate_commit_rate": float(args.max_neither_candidate_commit_rate),
        "max_support_wrong_top_rate": float(args.max_support_wrong_top_rate),
        "max_top_survival_commit_rate": float(args.max_top_survival_commit_rate),
        "min_alt_only_reject_or_defer_rate": float(args.min_alt_only_reject_or_defer_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_alt_only_rows_for_reject_top_gate": int(args.min_alt_only_rows_for_reject_top_gate),
        "min_alt_only_reject_top_rate": float(args.min_alt_only_reject_top_rate),
        "wrong_goal_commit_rate": ratio(len(wrong_commit_rows), len(rows_with_labels)),
        "commit_rate": ratio(len(commit_rows), len(out_rows)),
        "success_commit_rate": ratio(len(success_commit_rows), len(rows_with_labels)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commit_rows), len(commit_rows)),
        "support_wrong_top_rate": ratio(len(top_verified_wrong), len(rows_with_labels)),
        "top_verified_wrong_commit_rate": ratio(len(top_verified_wrong), len(top_verified_commits)),
        "top_survival_signal_rate": ratio(len(top_survival_signals), len(out_rows)),
        "top_survival_commit_rate": ratio(len(top_survival_commits), len(out_rows)),
        "top_survival_blocked_rate": ratio(
            sum(row["pair_v4_action"] == "pair_v4_defer_top_survival_untrusted" for row in top_survival_signals),
            len(top_survival_signals),
        ),
        "neither_candidate_commit_rate": ratio(
            sum(row["pair_v4_commits"] for row in neither),
            len(neither),
        ),
        "alt_only_reject_or_defer_rate": ratio(
            sum(row["pair_v4_action"] != "pair_v4_commit_top_verified_pair_evidence" for row in alt_only),
            len(alt_only),
        ),
        "alt_only_reject_top_rate": ratio(
            sum(row["pair_v4_action"] == "pair_v4_reject_top_confirm_alt" for row in alt_only),
            len(alt_only),
        ),
        "both_correct_ambiguous_or_success_rate": ratio(
            sum(
                row["pair_v4_action"] in {
                    "pair_v4_defer_rank_ambiguous_or_duplicate_goal",
                    "pair_v4_commit_top_verified_pair_evidence",
                    "pair_v4_reject_top_confirm_alt",
                }
                for row in both_correct
            ),
            len(both_correct),
        ),
        "alt_only_reject_top_gate_applies": len(alt_only) >= int(args.min_alt_only_rows_for_reject_top_gate),
    }
    alt_only_reject_top_ok = True
    if gate["alt_only_reject_top_gate_applies"]:
        alt_only_reject_top_ok = (gate["alt_only_reject_top_rate"] or 0.0) >= float(args.min_alt_only_reject_top_rate)
    gate["passes_pair_objective_v4_safety_gate"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["neither_candidate_commit_rate"] or 0.0) <= float(args.max_neither_candidate_commit_rate)
        and (gate["support_wrong_top_rate"] or 0.0) <= float(args.max_support_wrong_top_rate)
        and (gate["top_survival_commit_rate"] or 0.0) <= float(args.max_top_survival_commit_rate)
        and (gate["alt_only_reject_or_defer_rate"] or 0.0) >= float(args.min_alt_only_reject_or_defer_rate)
    )
    gate["passes_pair_objective_v4_full_gate"] = bool(
        gate["passes_pair_objective_v4_safety_gate"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and alt_only_reject_top_ok
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "pair_observation_objective_v4_rows.jsonl", out_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "pair_evidence_rows": str(args.pair_evidence_rows),
        "pair_observation_plan": str(args.pair_observation_plan),
        "rows": len(out_rows),
        "rows_with_labels": len(rows_with_labels),
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "action_by_label_case": {
            case: dict(sorted(counts.items()))
            for case, counts in sorted(action_by_label_case.items())
        },
        "objective_design": {
            "paired_branch_role": "commit_alt_or_verified_top_only_when_evidence_is_comparable_else_defer_or_request_external_search",
            "not_threshold_only": [
                "removes top-survival commit and turns it into a blocked safety state",
                "separates incomplete pair candidate set from ordinary rank ambiguity",
                "treats both-confirmed candidates as duplicate-goal or rank ambiguity unless one side is disconfirmed",
                "allows top commit only under comparable top evidence and explicit alt disconfirmation",
            ],
            "new_actions": [
                "pair_v4_defer_top_survival_untrusted",
                "pair_v4_request_external_candidate_search",
                "pair_v4_defer_rank_ambiguous_or_duplicate_goal",
                "pair_v4_commit_top_verified_pair_evidence",
            ],
        },
        "thresholds": {
            "detector_score_norm_cap": float(args.detector_score_norm_cap),
            "min_visible_count_for_comparable_view": float(args.min_visible_count_for_comparable_view),
            "max_view_quality_gap": float(args.max_view_quality_gap),
            "min_prior_alt_gap_for_reject": float(args.min_prior_alt_gap_for_reject),
            "min_alt_strict_rate_advantage": float(args.min_alt_strict_rate_advantage),
            "min_alt_confirm_advantage": float(args.min_alt_confirm_advantage),
            "min_top_disconfirm_score": float(args.min_top_disconfirm_score),
            "min_ambiguous_confirm_score": float(args.min_ambiguous_confirm_score),
            "min_top_survival_visible_count": float(args.min_top_survival_visible_count),
            "min_top_survival_confirm_score": float(args.min_top_survival_confirm_score),
            "min_top_survival_strict_rate": float(args.min_top_survival_strict_rate),
            "max_top_survival_disconfirm_score": float(args.max_top_survival_disconfirm_score),
            "max_alt_visible_count_for_top_survival": float(args.max_alt_visible_count_for_top_survival),
            "max_alt_confirm_for_top_survival": float(args.max_alt_confirm_for_top_survival),
            "min_top_survival_strict_rate_advantage": float(args.min_top_survival_strict_rate_advantage),
            "max_prior_alt_gap_for_top_survival": float(args.max_prior_alt_gap_for_top_survival),
            "allow_matched_dual_standoff_top_survival": bool(args.allow_matched_dual_standoff_top_survival),
            "min_top_verified_strict_count": float(args.min_top_verified_strict_count),
            "min_top_verified_confirm_score": float(args.min_top_verified_confirm_score),
            "min_top_verified_strict_rate_advantage": float(args.min_top_verified_strict_rate_advantage),
            "max_alt_strict_count_for_top_verified": float(args.max_alt_strict_count_for_top_verified),
            "max_alt_confirm_for_top_verified": float(args.max_alt_confirm_for_top_verified),
            "max_prior_alt_gap_for_top_verified": float(args.max_prior_alt_gap_for_top_verified),
        },
        "gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "pair_observation_objective_v4_rows.jsonl",
            "summary": "pair_observation_objective_v4_summary.json",
        },
    }
    write_json(out_root / "pair_observation_objective_v4_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply H001 paired top-vs-alt objective v4.")
    parser.add_argument("--pair-evidence-rows", required=True)
    parser.add_argument("--pair-observation-plan", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--detector-score-norm-cap", type=float, default=0.25)
    parser.add_argument("--min-visible-count-for-comparable-view", type=float, default=4.0)
    parser.add_argument("--max-view-quality-gap", type=float, default=0.25)
    parser.add_argument("--min-prior-alt-gap-for-reject", type=float, default=0.01)
    parser.add_argument("--min-alt-strict-rate-advantage", type=float, default=0.10)
    parser.add_argument("--min-alt-confirm-advantage", type=float, default=0.02)
    parser.add_argument("--min-top-disconfirm-score", type=float, default=0.55)
    parser.add_argument("--min-ambiguous-confirm-score", type=float, default=0.30)
    parser.add_argument("--min-top-survival-visible-count", type=float, default=4.0)
    parser.add_argument("--min-top-survival-confirm-score", type=float, default=0.55)
    parser.add_argument("--min-top-survival-strict-rate", type=float, default=0.50)
    parser.add_argument("--max-top-survival-disconfirm-score", type=float, default=0.50)
    parser.add_argument("--max-alt-visible-count-for-top-survival", type=float, default=0.0)
    parser.add_argument("--max-alt-confirm-for-top-survival", type=float, default=0.10)
    parser.add_argument("--min-top-survival-strict-rate-advantage", type=float, default=0.50)
    parser.add_argument("--max-prior-alt-gap-for-top-survival", type=float, default=0.01)
    parser.add_argument("--allow-matched-dual-standoff-top-survival", action="store_true")
    parser.add_argument("--min-top-verified-strict-count", type=float, default=2.0)
    parser.add_argument("--min-top-verified-confirm-score", type=float, default=0.50)
    parser.add_argument("--min-top-verified-strict-rate-advantage", type=float, default=0.25)
    parser.add_argument("--max-alt-strict-count-for-top-verified", type=float, default=0.0)
    parser.add_argument("--max-alt-confirm-for-top-verified", type=float, default=0.20)
    parser.add_argument("--max-prior-alt-gap-for-top-verified", type=float, default=0.0)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-neither-candidate-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-support-wrong-top-rate", type=float, default=0.0)
    parser.add_argument("--max-top-survival-commit-rate", type=float, default=0.0)
    parser.add_argument("--min-alt-only-reject-or-defer-rate", type=float, default=1.0)
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    parser.add_argument("--min-alt-only-rows-for-reject-top-gate", type=int, default=3)
    parser.add_argument("--min-alt-only-reject-top-rate", type=float, default=0.30)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
