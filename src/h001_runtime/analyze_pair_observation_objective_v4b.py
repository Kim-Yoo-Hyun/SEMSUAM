import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from h001_runtime.analyze_pair_observation_objective_v2 import (
    load_jsonl,
    pair_key,
    plan_index,
    ratio,
    safe_float,
)
from h001_runtime import analyze_pair_observation_objective_v4 as v4


SCHEMA_VERSION = "h001.pair_observation_objective.v4b"


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def feature(row: Dict[str, Any], side: str, name: str) -> float:
    value = ((row.get(f"pair_v4_{side}_features") or {}).get(name))
    number = safe_float(value)
    return 0.0 if number is None else number


def alt_commit_completeness_guard(row: Dict[str, Any], plan: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    ambiguity = safe_float(plan.get("arbitration_R_after2_ambiguity"))
    if ambiguity is None:
        ambiguity = 1.0
    prior_alt_gap = safe_float(row.get("pair_v4_prior_alt_gap")) or 0.0
    confirm_gap = safe_float(row.get("pair_v4_confirm_gap_alt_minus_top")) or 0.0
    strict_rate_gap = safe_float(row.get("pair_v4_strict_rate_gap_alt_minus_top")) or 0.0
    alt_visible = feature(row, "alt", "visible_count")
    alt_strict = feature(row, "alt", "strict_association_count")
    alt_strict_rate = alt_strict / max(1.0, alt_visible)
    pair_complete = ambiguity <= float(args.max_alt_commit_ambiguity)
    strong_alt = bool(
        prior_alt_gap >= float(args.min_alt_commit_prior_gap)
        and confirm_gap >= float(args.min_alt_commit_confirm_gap)
        and strict_rate_gap >= float(args.min_alt_commit_strict_rate_gap)
        and alt_strict_rate >= float(args.min_alt_commit_strict_rate)
    )
    return {
        "pair_v4b_alt_commit_pair_complete": pair_complete,
        "pair_v4b_alt_commit_strong_alt_evidence": strong_alt,
        "pair_v4b_alt_commit_allowed": bool(pair_complete and strong_alt),
        "pair_v4b_alt_commit_ambiguity": ambiguity,
        "pair_v4b_alt_commit_prior_alt_gap": prior_alt_gap,
        "pair_v4b_alt_commit_confirm_gap_alt_minus_top": confirm_gap,
        "pair_v4b_alt_commit_strict_rate_gap_alt_minus_top": strict_rate_gap,
        "pair_v4b_alt_commit_alt_strict_rate": alt_strict_rate,
    }


def v4_to_v4b_action(row: Dict[str, Any], plan: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    base_action = str(row.get("pair_v4_action"))
    guard = alt_commit_completeness_guard(row, plan, args)
    if base_action == "pair_v4_reject_top_confirm_alt":
        if guard["pair_v4b_alt_commit_allowed"]:
            action = "pair_v4b_reject_top_confirm_alt"
            reason = "alt_confirmed_with_complete_pair_set"
        else:
            action = "pair_v4b_request_external_candidate_search_alt_confirm_untrusted"
            reason = "alt_confirmation_without_pair_set_completeness"
    elif base_action.startswith("pair_v4_"):
        action = "pair_v4b_" + base_action[len("pair_v4_"):]
        reason = str(row.get("pair_v4_reason"))
    else:
        action = base_action
        reason = str(row.get("pair_v4_reason"))
    return {
        "pair_v4b_action": action,
        "pair_v4b_reason": reason,
        **guard,
    }


def committed_candidate_correct(row: Dict[str, Any]) -> Optional[bool]:
    action = row.get("pair_v4b_action")
    if action == "pair_v4b_commit_top_verified_pair_evidence":
        return row.get("top_candidate_correct")
    if action == "pair_v4b_reject_top_confirm_alt":
        return row.get("alt_candidate_correct")
    return None


def run(args: argparse.Namespace) -> Dict[str, Any]:
    # Keep the exact V4 computation as the base evidence contract, then apply only
    # the V4b candidate-set completeness guard to alt-confirmation commits.
    v4.run(args)
    out_root = Path(args.out_root)
    v4_rows = load_jsonl(out_root / "pair_observation_objective_v4_rows.jsonl")
    plans = plan_index(load_jsonl(Path(args.pair_observation_plan)))
    out_rows: List[Dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    action_by_label_case: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in v4_rows:
        key = pair_key(row)
        decision = v4_to_v4b_action(row, plans.get(key, {}), args)
        out = {
            "schema_version": SCHEMA_VERSION,
            **row,
            **decision,
            "uses_gt_for_action": False,
        }
        committed = committed_candidate_correct(out)
        out["pair_v4b_commits"] = committed is not None
        out["pair_v4b_committed_candidate_correct"] = committed
        out["pair_v4b_wrong_goal_commit"] = committed is False
        out["pair_v4b_success_commit"] = committed is True
        out["pair_v4b_defer"] = committed is None
        out_rows.append(out)
        action_counts[out["pair_v4b_action"]] += 1
        reason_counts[out["pair_v4b_reason"]] += 1
        action_by_label_case[str(out.get("label_case"))][out["pair_v4b_action"]] += 1

    rows_with_labels = [row for row in out_rows if row.get("top_candidate_correct") is not None]
    commit_rows = [row for row in out_rows if row["pair_v4b_commits"]]
    wrong_commit_rows = [row for row in out_rows if row["pair_v4b_wrong_goal_commit"]]
    success_commit_rows = [row for row in out_rows if row["pair_v4b_success_commit"]]
    alt_only = [row for row in out_rows if row["label_case"] == "alt_only_correct"]
    neither = [row for row in out_rows if row["label_case"] == "neither_candidate_correct"]
    both_correct = [row for row in out_rows if row["label_case"] == "both_candidates_correct"]
    top_verified_commits = [
        row for row in out_rows
        if row["pair_v4b_action"] == "pair_v4b_commit_top_verified_pair_evidence"
    ]
    top_verified_wrong = [
        row for row in top_verified_commits
        if row.get("top_candidate_correct") is False
    ]
    top_survival_commits = [
        row for row in out_rows
        if row["pair_v4b_action"] == "pair_v4b_commit_top_common_view_survival"
    ]
    blocked_alt_commits = [
        row for row in out_rows
        if row["pair_v4b_action"] == "pair_v4b_request_external_candidate_search_alt_confirm_untrusted"
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
        "top_survival_commit_rate": ratio(len(top_survival_commits), len(out_rows)),
        "neither_candidate_commit_rate": ratio(
            sum(row["pair_v4b_commits"] for row in neither),
            len(neither),
        ),
        "alt_only_reject_or_defer_rate": ratio(
            sum(row["pair_v4b_action"] != "pair_v4b_commit_top_verified_pair_evidence" for row in alt_only),
            len(alt_only),
        ),
        "alt_only_reject_top_rate": ratio(
            sum(row["pair_v4b_action"] == "pair_v4b_reject_top_confirm_alt" for row in alt_only),
            len(alt_only),
        ),
        "both_correct_ambiguous_or_success_rate": ratio(
            sum(
                row["pair_v4b_action"] in {
                    "pair_v4b_defer_rank_ambiguous_or_duplicate_goal",
                    "pair_v4b_commit_top_verified_pair_evidence",
                    "pair_v4b_reject_top_confirm_alt",
                }
                for row in both_correct
            ),
            len(both_correct),
        ),
        "blocked_alt_commit_count": len(blocked_alt_commits),
        "alt_only_reject_top_gate_applies": len(alt_only) >= int(args.min_alt_only_rows_for_reject_top_gate),
    }
    alt_only_reject_top_ok = True
    if gate["alt_only_reject_top_gate_applies"]:
        alt_only_reject_top_ok = (gate["alt_only_reject_top_rate"] or 0.0) >= float(args.min_alt_only_reject_top_rate)
    gate["passes_pair_objective_v4b_safety_gate"] = bool(
        (gate["wrong_goal_commit_rate"] or 0.0) <= float(args.max_wrong_goal_commit_rate)
        and (gate["neither_candidate_commit_rate"] or 0.0) <= float(args.max_neither_candidate_commit_rate)
        and (gate["support_wrong_top_rate"] or 0.0) <= float(args.max_support_wrong_top_rate)
        and (gate["top_survival_commit_rate"] or 0.0) <= float(args.max_top_survival_commit_rate)
        and (gate["alt_only_reject_or_defer_rate"] or 0.0) >= float(args.min_alt_only_reject_or_defer_rate)
    )
    gate["passes_pair_objective_v4b_full_gate"] = bool(
        gate["passes_pair_objective_v4b_safety_gate"]
        and (gate["commit_rate"] or 0.0) >= float(args.min_commit_rate)
        and alt_only_reject_top_ok
    )

    write_jsonl(out_root / "pair_observation_objective_v4b_rows.jsonl", out_rows)
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
            "paired_branch_role": "v4_plus_candidate_set_completeness_guard_before_alt_commit",
            "not_threshold_only": [
                "keeps V4 evidence computation unchanged",
                "blocks alt commit when association recovery still reports unresolved ambiguity",
                "routes alt-confirmed but pair-incomplete cases to external candidate search",
            ],
            "new_action": "pair_v4b_request_external_candidate_search_alt_confirm_untrusted",
        },
        "thresholds": {
            "max_alt_commit_ambiguity": float(args.max_alt_commit_ambiguity),
            "min_alt_commit_prior_gap": float(args.min_alt_commit_prior_gap),
            "min_alt_commit_confirm_gap": float(args.min_alt_commit_confirm_gap),
            "min_alt_commit_strict_rate_gap": float(args.min_alt_commit_strict_rate_gap),
            "min_alt_commit_strict_rate": float(args.min_alt_commit_strict_rate),
        },
        "gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "pair_observation_objective_v4b_rows.jsonl",
            "summary": "pair_observation_objective_v4b_summary.json",
        },
    }
    write_json(out_root / "pair_observation_objective_v4b_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = v4.build_parser("Apply H001 paired top-vs-alt objective v4b.")
    parser.add_argument("--max-alt-commit-ambiguity", type=float, default=0.0)
    parser.add_argument("--min-alt-commit-prior-gap", type=float, default=0.01)
    parser.add_argument("--min-alt-commit-confirm-gap", type=float, default=0.02)
    parser.add_argument("--min-alt-commit-strict-rate-gap", type=float, default=0.10)
    parser.add_argument("--min-alt-commit-strict-rate", type=float, default=0.50)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
