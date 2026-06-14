import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.pair_observation_objective.v2"


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


def pair_key(row: Dict[str, Any]) -> str:
    value = row.get("pair_observation_id")
    if value is not None:
        return str(value)
    return f"{row.get('episode_key')}|{row.get('pair_top_candidate_id')}|{row.get('pair_alt_candidate_id')}"


def plan_index(plan_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in plan_rows:
        out.setdefault(pair_key(row), row)
    return out


def feature(row: Dict[str, Any], side: str, name: str, default: float = 0.0) -> float:
    value = safe_float(row.get(f"pair_{side}_{name}"))
    return default if value is None else value


def candidate_features(row: Dict[str, Any], side: str, args: argparse.Namespace) -> Dict[str, Any]:
    visible = feature(row, side, "visible_count")
    strict = feature(row, side, "strict_association_count")
    mask = feature(row, side, "mask_hit_count")
    box = feature(row, side, "box_hit_count")
    det = feature(row, side, "detector_score_max")
    visible_denom = max(1.0, visible)
    strict_rate = strict / visible_denom
    mask_rate = mask / visible_denom
    box_rate = box / visible_denom
    detector_norm = min(1.0, det / float(args.detector_score_norm_cap)) if det > 0.0 else 0.0
    view_quality = min(1.0, visible / float(args.min_visible_count_for_comparable_view))
    confirm = view_quality * (
        0.65 * strict_rate
        + 0.20 * mask_rate
        + 0.15 * detector_norm
    )
    disconfirm = view_quality * (1.0 - max(strict_rate, 0.50 * mask_rate))
    return {
        "visible_count": visible,
        "strict_association_count": strict,
        "mask_hit_count": mask,
        "box_hit_count": box,
        "detector_score_max": det,
        "strict_association_rate": strict_rate,
        "mask_hit_rate": mask_rate,
        "box_hit_rate": box_rate,
        "detector_score_norm": detector_norm,
        "view_quality": view_quality,
        "confirm_score": max(0.0, min(1.0, confirm)),
        "disconfirm_score": max(0.0, min(1.0, disconfirm)),
    }


def v2_decision(row: Dict[str, Any], plan: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    top = candidate_features(row, "top", args)
    alt = candidate_features(row, "alt", args)
    mode = str(row.get("pair_observation_mode"))
    arb_gap = safe_float(plan.get("arbitration_support_gap_alt_minus_top"))
    if arb_gap is None:
        arb_gap = 0.0

    strict_rate_gap_alt_minus_top = alt["strict_association_rate"] - top["strict_association_rate"]
    confirm_gap_alt_minus_top = alt["confirm_score"] - top["confirm_score"]
    view_quality_gap = abs(alt["view_quality"] - top["view_quality"])
    alt_has_strict = alt["strict_association_count"] >= 1.0
    top_has_strict = top["strict_association_count"] >= 1.0
    alt_rejection_evidence = bool(
        alt_has_strict
        and arb_gap >= float(args.min_prior_alt_gap_for_reject)
        and strict_rate_gap_alt_minus_top >= float(args.min_alt_strict_rate_advantage)
        and confirm_gap_alt_minus_top >= float(args.min_alt_confirm_advantage)
    )
    top_rejection_evidence = bool(
        top["disconfirm_score"] >= float(args.min_top_disconfirm_score)
        or top["strict_association_count"] == 0.0
    )

    if top["view_quality"] <= 0.0 and alt["view_quality"] <= 0.0:
        action = "pair_v2_defer_no_pair_evidence"
        reason = "no_visible_candidate_opportunity"
    elif view_quality_gap > float(args.max_view_quality_gap):
        action = "pair_v2_defer_view_not_comparable"
        reason = f"{mode}_view_opportunity_imbalance"
    elif alt_rejection_evidence and top_rejection_evidence:
        action = "pair_v2_reject_top_confirm_alt"
        reason = "prior_alt_gap_plus_view_normalized_alt_confirmation"
    elif not args.allow_support_top:
        if top_has_strict and not alt_has_strict and arb_gap < float(args.min_prior_alt_gap_for_reject):
            action = "pair_v2_defer_no_valid_candidate_or_external_search"
            reason = "top_supported_but_pair_branch_disallows_recommit"
        elif top["confirm_score"] >= float(args.min_ambiguous_confirm_score) and alt["confirm_score"] >= float(args.min_ambiguous_confirm_score):
            action = "pair_v2_defer_rank_ambiguous"
            reason = "both_candidates_have_confirmation_evidence"
        else:
            action = "pair_v2_defer_insufficient_disconfirmation"
            reason = "no_strong_alt_confirmation_or_top_disconfirmation"
    elif (
        top_has_strict
        and top["confirm_score"] >= float(args.min_support_top_confirm_score)
        and alt["confirm_score"] <= float(args.max_alt_confirm_for_support_top)
        and arb_gap < 0.0
    ):
        action = "pair_v2_support_top_confirm_top"
        reason = "top_confirmation_with_prior_top_advantage"
    else:
        action = "pair_v2_defer_insufficient_disconfirmation"
        reason = "no_commit_rule_satisfied"

    return {
        "pair_v2_action": action,
        "pair_v2_reason": reason,
        "pair_v2_prior_alt_gap": arb_gap,
        "pair_v2_strict_rate_gap_alt_minus_top": strict_rate_gap_alt_minus_top,
        "pair_v2_confirm_gap_alt_minus_top": confirm_gap_alt_minus_top,
        "pair_v2_view_quality_gap": view_quality_gap,
        "pair_v2_alt_rejection_evidence": alt_rejection_evidence,
        "pair_v2_top_rejection_evidence": top_rejection_evidence,
        "pair_v2_top_features": top,
        "pair_v2_alt_features": alt,
    }


def committed_candidate_correct(row: Dict[str, Any]) -> Optional[bool]:
    action = row.get("pair_v2_action")
    if action == "pair_v2_support_top_confirm_top":
        return row.get("top_candidate_correct")
    if action == "pair_v2_reject_top_confirm_alt":
        return row.get("alt_candidate_correct")
    return None


def label_case(row: Dict[str, Any]) -> str:
    top = row.get("top_candidate_correct")
    alt = row.get("alt_candidate_correct")
    if top is True and alt is True:
        return "both_candidates_correct"
    if top is True and alt is False:
        return "top_only_correct"
    if top is False and alt is True:
        return "alt_only_correct"
    if top is False and alt is False:
        return "neither_candidate_correct"
    if top is False:
        return "top_wrong_alt_unknown"
    if top is True:
        return "top_correct_alt_unknown"
    return "unknown_labels"


def run(args: argparse.Namespace) -> Dict[str, Any]:
    pair_rows = load_jsonl(Path(args.pair_evidence_rows))
    plans = plan_index(load_jsonl(Path(args.pair_observation_plan)))
    out_rows: List[Dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    action_by_label_case: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in pair_rows:
        key = pair_key(row)
        decision = v2_decision(row, plans.get(key, {}), args)
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
        out["pair_v2_commits"] = committed is not None
        out["pair_v2_committed_candidate_correct"] = committed
        out["pair_v2_wrong_goal_commit"] = committed is False
        out["pair_v2_success_commit"] = committed is True
        out["pair_v2_defer"] = committed is None
        out_rows.append(out)
        action_counts[out["pair_v2_action"]] += 1
        reason_counts[out["pair_v2_reason"]] += 1
        action_by_label_case[out["label_case"]][out["pair_v2_action"]] += 1

    rows_with_labels = [row for row in out_rows if row.get("top_candidate_correct") is not None]
    commit_rows = [row for row in out_rows if row["pair_v2_commits"]]
    wrong_commit_rows = [row for row in out_rows if row["pair_v2_wrong_goal_commit"]]
    success_commit_rows = [row for row in out_rows if row["pair_v2_success_commit"]]
    alt_only = [row for row in out_rows if row["label_case"] == "alt_only_correct"]
    neither = [row for row in out_rows if row["label_case"] == "neither_candidate_correct"]
    both_correct = [row for row in out_rows if row["label_case"] == "both_candidates_correct"]
    support_wrong_top_rows = [
        row for row in out_rows
        if row["pair_v2_action"] == "pair_v2_support_top_confirm_top"
        and row.get("top_candidate_correct") is False
    ]
    gate = {
        "max_wrong_goal_commit_rate": float(args.max_wrong_goal_commit_rate),
        "max_neither_candidate_commit_rate": float(args.max_neither_candidate_commit_rate),
        "max_support_wrong_top_rate": float(args.max_support_wrong_top_rate),
        "min_alt_only_reject_or_defer_rate": float(args.min_alt_only_reject_or_defer_rate),
        "min_commit_rate": float(args.min_commit_rate),
        "min_alt_only_rows_for_reject_top_gate": int(args.min_alt_only_rows_for_reject_top_gate),
        "min_alt_only_reject_top_rate": float(args.min_alt_only_reject_top_rate),
        "wrong_goal_commit_rate": ratio(len(wrong_commit_rows), len(rows_with_labels)),
        "commit_rate": ratio(len(commit_rows), len(out_rows)),
        "success_commit_rate": ratio(len(success_commit_rows), len(rows_with_labels)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_commit_rows), len(commit_rows)),
        "support_wrong_top_rate": ratio(len(support_wrong_top_rows), len(rows_with_labels)),
        "neither_candidate_commit_rate": ratio(
            sum(row["pair_v2_commits"] for row in neither),
            len(neither),
        ),
        "alt_only_reject_or_defer_rate": ratio(
            sum(row["pair_v2_action"] != "pair_v2_support_top_confirm_top" for row in alt_only),
            len(alt_only),
        ),
        "alt_only_reject_top_rate": ratio(
            sum(row["pair_v2_action"] == "pair_v2_reject_top_confirm_alt" for row in alt_only),
            len(alt_only),
        ),
        "alt_only_reject_top_gate_applies": len(alt_only) >= int(args.min_alt_only_rows_for_reject_top_gate),
        "both_correct_commit_or_defer_rate": ratio(
            sum(
                row["pair_v2_action"] in {
                    "pair_v2_reject_top_confirm_alt",
                    "pair_v2_support_top_confirm_top",
                }
                or row["pair_v2_defer"]
                for row in both_correct
            ),
            len(both_correct),
        ),
    }
    alt_only_reject_top_ok = True
    if gate["alt_only_reject_top_gate_applies"]:
        alt_only_reject_top_ok = (gate["alt_only_reject_top_rate"] or 0.0) >= float(args.min_alt_only_reject_top_rate)
    gate["passes_pair_objective_v2_gate"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["neither_candidate_commit_rate"] or 0.0) <= float(args.max_neither_candidate_commit_rate)
        and (gate["support_wrong_top_rate"] or 0.0) <= float(args.max_support_wrong_top_rate)
        and (gate["alt_only_reject_or_defer_rate"] or 0.0) >= float(args.min_alt_only_reject_or_defer_rate)
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and alt_only_reject_top_ok
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "pair_observation_objective_v2_rows.jsonl", out_rows)
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
            "allow_support_top": bool(args.allow_support_top),
            "paired_branch_role": "reject_top_or_defer_after_top_was_marked_unsafe",
            "not_threshold_only": [
                "uses prior arbitration alt gap",
                "uses view-normalized strict association advantage",
                "requires top disconfirmation or weak top association",
                "defers instead of forcing a top-vs-alt choice",
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
        },
        "gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "pair_observation_objective_v2_rows.jsonl",
            "summary": "pair_observation_objective_v2_summary.json",
        },
    }
    write_json(out_root / "pair_observation_objective_v2_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply H001 paired top-vs-alt objective v2.")
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
    parser.add_argument("--allow-support-top", action="store_true")
    parser.add_argument("--min-support-top-confirm-score", type=float, default=0.50)
    parser.add_argument("--max-alt-confirm-for-support-top", type=float, default=0.20)
    parser.add_argument("--max-wrong-goal-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-neither-candidate-commit-rate", type=float, default=0.10)
    parser.add_argument("--max-support-wrong-top-rate", type=float, default=0.0)
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
