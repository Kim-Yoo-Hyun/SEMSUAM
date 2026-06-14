import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.pair_observation_v2_overdeferral.v1"


def load_json(path: Optional[str]) -> Dict[str, Any]:
    if not path:
        return {}
    file_path = Path(path)
    if not file_path.exists():
        return {}
    return json.loads(file_path.read_text(encoding="utf-8"))


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def ceil_count(rate: float, rows: int) -> int:
    return int(math.ceil(rate * rows))


def pair_key(row: Dict[str, Any]) -> str:
    value = row.get("pair_observation_id")
    if value is not None:
        return str(value)
    return f"{row.get('episode_key')}|{row.get('pair_top_candidate_id')}|{row.get('pair_alt_candidate_id')}"


def index_by_pair(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        out.setdefault(pair_key(row), row)
    return out


def has_pair_correct_candidate(row: Dict[str, Any]) -> bool:
    return row.get("top_candidate_correct") is True or row.get("alt_candidate_correct") is True


def revision_tags(row: Dict[str, Any], failure_row: Dict[str, Any]) -> List[str]:
    if row.get("pair_v2_defer") is not True:
        return ["not_overdeferred_committed"]

    action = str(row.get("pair_v2_action"))
    label_case = str(row.get("label_case"))
    tags: List[str] = []

    if label_case == "neither_candidate_correct":
        tags.append("external_candidate_branch_needed")
    if label_case in {"top_only_correct", "both_candidates_correct"}:
        tags.append("success_preserving_pair_commit_rule_needed")
    if label_case == "alt_only_correct":
        tags.append("alt_confirmation_reject_top_rule_needed")

    if action == "pair_v2_defer_view_not_comparable":
        tags.append("paired_view_geometry_revision_needed")
    if action == "pair_v2_defer_rank_ambiguous":
        tags.append("rank_ambiguity_resolution_needed")
    if action == "pair_v2_defer_insufficient_disconfirmation":
        tags.append("top_disconfirmation_or_alt_confirmation_needed")
    if action == "pair_v2_defer_no_valid_candidate_or_external_search":
        tags.append("no_valid_pair_external_search_needed")

    failure_tags = failure_row.get("failure_tags") or []
    if "matched_dual_standoff_view_opportunity_imbalance" in failure_tags:
        tags.append("paired_view_geometry_revision_needed")
    if "neither_candidate_correct_pair_forces_choice" in failure_tags:
        tags.append("external_candidate_branch_needed")
    if "both_candidates_correct_rank_ambiguity" in failure_tags:
        tags.append("rank_ambiguity_resolution_needed")

    return sorted(set(tags)) or ["uncategorized_overdefer"]


def primary_overdeferral_mode(row: Dict[str, Any], tags: List[str]) -> str:
    if row.get("pair_v2_defer") is not True:
        return "not_overdeferred_committed"
    action = str(row.get("pair_v2_action"))
    label_case = str(row.get("label_case"))

    if action == "pair_v2_defer_view_not_comparable":
        return "paired_view_not_comparable"
    if label_case == "neither_candidate_correct":
        return "external_candidate_needed"
    if label_case in {"top_only_correct", "both_candidates_correct"}:
        return "safe_pair_candidate_deferred"
    if label_case == "alt_only_correct":
        return "alt_correct_rejection_missed"
    if action == "pair_v2_defer_rank_ambiguous":
        return "rank_ambiguity_unresolved"
    if action == "pair_v2_defer_insufficient_disconfirmation":
        return "insufficient_disconfirmation"
    if tags:
        return tags[0]
    return "uncategorized_overdefer"


def recommended_next(summary: Dict[str, Any]) -> Dict[str, Any]:
    rows = int(summary["rows"])
    commits = int(summary["commit_rows"])
    additional_needed = int(summary["commit_gate_gap_rows"])
    safe_deferred = int(summary["pair_correct_candidate_deferred_rows"])
    neither_deferred = int(summary["neither_candidate_deferred_rows"])
    view_deferred = int(summary["view_not_comparable_deferred_rows"])

    if additional_needed > 0 and safe_deferred >= additional_needed:
        priority = "success_preserving_pair_objective_revision"
        reason = (
            "commit gate failed, but deferred rows with a correct top/alt candidate are enough "
            "to close the gate without committing neither-candidate pairs"
        )
    elif neither_deferred >= max(safe_deferred, view_deferred):
        priority = "external_candidate_branch"
        reason = "neither-candidate-correct rows dominate the deferred set"
    elif view_deferred > 0:
        priority = "paired_view_geometry_revision"
        reason = "view comparability blocks a large part of the deferred set"
    else:
        priority = "objective_evidence_diagnostic"
        reason = "no single over-deferral source dominates"

    return {
        "priority": priority,
        "reason": reason,
        "do_not_do_next": [
            "do not lower held-out thresholds",
            "do not enable top support without a fixed non-GT safety gate",
            "do not move to policy-scale integration before a held-out objective gate passes",
        ],
        "secondary_priority": [
            "external_candidate_branch for neither-candidate-correct cases",
            "paired_view_geometry_revision for view-not-comparable cases",
            "rank-ambiguity handling for both-correct cases",
        ],
        "minimum_next_gate": {
            "wrong_goal_commit_rate": "<= 0.10",
            "support_wrong_top_rate": "0.0",
            "neither_candidate_commit_rate": "<= 0.10",
            "commit_rate": ">= 0.15",
            "rows": rows,
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    objective_rows = load_jsonl(Path(args.objective_v2_rows))
    failure_rows = index_by_pair(load_jsonl(Path(args.failure_mode_rows)))
    objective_summary = load_json(args.objective_v2_summary)
    failure_summary = load_json(args.failure_mode_summary)
    substrate_summary = load_json(args.substrate_summary)

    out_rows: List[Dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    deferred_action_counts: Counter[str] = Counter()
    deferred_label_counts: Counter[str] = Counter()
    primary_counts: Counter[str] = Counter()
    revision_counts: Counter[str] = Counter()
    revision_by_action: Dict[str, Counter[str]] = defaultdict(Counter)
    revision_by_label: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in objective_rows:
        key = pair_key(row)
        failure_row = failure_rows.get(key, {})
        tags = revision_tags(row, failure_row)
        primary = primary_overdeferral_mode(row, tags)
        action = str(row.get("pair_v2_action"))
        label_case = str(row.get("label_case"))
        out = {
            "schema_version": SCHEMA_VERSION,
            "pair_observation_id": row.get("pair_observation_id"),
            "episode_key": row.get("episode_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "pair_observation_mode": row.get("pair_observation_mode"),
            "pair_top_candidate_id": row.get("pair_top_candidate_id"),
            "pair_alt_candidate_id": row.get("pair_alt_candidate_id"),
            "pair_v2_action": row.get("pair_v2_action"),
            "pair_v2_reason": row.get("pair_v2_reason"),
            "pair_v2_defer": row.get("pair_v2_defer"),
            "pair_v2_commits": row.get("pair_v2_commits"),
            "pair_v2_success_commit": row.get("pair_v2_success_commit"),
            "pair_v2_wrong_goal_commit": row.get("pair_v2_wrong_goal_commit"),
            "label_case": label_case,
            "top_candidate_correct": row.get("top_candidate_correct"),
            "alt_candidate_correct": row.get("alt_candidate_correct"),
            "pair_contains_correct_candidate": has_pair_correct_candidate(row),
            "pair_v2_view_quality_gap": row.get("pair_v2_view_quality_gap"),
            "pair_v2_prior_alt_gap": row.get("pair_v2_prior_alt_gap"),
            "pair_v2_strict_rate_gap_alt_minus_top": row.get("pair_v2_strict_rate_gap_alt_minus_top"),
            "pair_v2_confirm_gap_alt_minus_top": row.get("pair_v2_confirm_gap_alt_minus_top"),
            "pair_v2_top_rejection_evidence": row.get("pair_v2_top_rejection_evidence"),
            "pair_v2_alt_rejection_evidence": row.get("pair_v2_alt_rejection_evidence"),
            "v1_primary_failure_mode": failure_row.get("primary_failure_mode"),
            "v1_failure_tags": failure_row.get("failure_tags"),
            "primary_overdeferral_mode": primary,
            "revision_tags": tags,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
        }
        out_rows.append(out)
        action_counts[action] += 1
        label_counts[label_case] += 1
        primary_counts[primary] += 1
        for tag in tags:
            revision_counts[tag] += 1
            revision_by_action[action][tag] += 1
            revision_by_label[label_case][tag] += 1
        if row.get("pair_v2_defer") is True:
            deferred_action_counts[action] += 1
            deferred_label_counts[label_case] += 1

    rows = len(out_rows)
    commit_rows = [row for row in out_rows if row["pair_v2_commits"] is True]
    deferred_rows = [row for row in out_rows if row["pair_v2_defer"] is True]
    success_commits = [row for row in commit_rows if row["pair_v2_success_commit"] is True]
    wrong_commits = [row for row in commit_rows if row["pair_v2_wrong_goal_commit"] is True]
    pair_correct_deferred = [row for row in deferred_rows if row["pair_contains_correct_candidate"]]
    neither_deferred = [row for row in deferred_rows if row["label_case"] == "neither_candidate_correct"]
    view_deferred = [row for row in deferred_rows if row["pair_v2_action"] == "pair_v2_defer_view_not_comparable"]
    min_commit_rate = float(args.min_commit_rate)
    min_commit_rows = ceil_count(min_commit_rate, rows)
    commit_gap = max(0, min_commit_rows - len(commit_rows))

    summary = {
        "schema_version": SCHEMA_VERSION,
        "objective_v2_rows": str(args.objective_v2_rows),
        "failure_mode_rows": str(args.failure_mode_rows),
        "rows": rows,
        "commit_rows": len(commit_rows),
        "deferred_rows": len(deferred_rows),
        "success_commit_rows": len(success_commits),
        "wrong_goal_commit_rows": len(wrong_commits),
        "commit_rate": ratio(len(commit_rows), rows),
        "defer_rate": ratio(len(deferred_rows), rows),
        "min_commit_rate": min_commit_rate,
        "min_commit_rows": min_commit_rows,
        "commit_gate_gap_rows": commit_gap,
        "pair_correct_candidate_deferred_rows": len(pair_correct_deferred),
        "pair_correct_candidate_deferred_rate": ratio(len(pair_correct_deferred), len(deferred_rows)),
        "pair_correct_commit_ceiling_rows": len(commit_rows) + len(pair_correct_deferred),
        "pair_correct_commit_ceiling_rate": ratio(len(commit_rows) + len(pair_correct_deferred), rows),
        "neither_candidate_deferred_rows": len(neither_deferred),
        "neither_candidate_deferred_rate": ratio(len(neither_deferred), len(deferred_rows)),
        "view_not_comparable_deferred_rows": len(view_deferred),
        "view_not_comparable_deferred_rate": ratio(len(view_deferred), len(deferred_rows)),
        "action_counts": dict(sorted(action_counts.items())),
        "label_case_counts": dict(sorted(label_counts.items())),
        "deferred_action_counts": dict(sorted(deferred_action_counts.items())),
        "deferred_label_case_counts": dict(sorted(deferred_label_counts.items())),
        "primary_overdeferral_mode_counts": dict(sorted(primary_counts.items())),
        "revision_need_counts": dict(sorted(revision_counts.items())),
        "revision_need_by_action": {
            action: dict(sorted(counts.items()))
            for action, counts in sorted(revision_by_action.items())
        },
        "revision_need_by_label_case": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(revision_by_label.items())
        },
        "source_gate_snapshot": {
            "substrate_passed": (substrate_summary.get("gate") or {}).get("passes_substrate_validity_gate"),
            "objective_v2_passed": (objective_summary.get("gate") or {}).get("passes_pair_objective_v2_gate"),
            "failure_primary_counts": failure_summary.get("primary_failure_mode_counts"),
        },
        "diagnosis": {
            "safety_status": "passed" if len(wrong_commits) == 0 else "failed",
            "utility_status": "failed_overdeferral" if commit_gap > 0 else "passed",
            "threshold_change_allowed": False,
            "policy_scale_integration": "blocked",
            "key_interpretation": [
                "detector and mask substrate are not the immediate blocker",
                "objective v2 avoids wrong-goal commits by deferring almost all paired cases",
                "the held-out commit-rate failure can be closed only by a fixed non-GT rule that safely accepts some correct top/alt pair cases or by a wider external-candidate branch",
            ],
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "pair_observation_v2_overdeferral_rows.jsonl",
            "summary": "pair_observation_v2_overdeferral_summary.json",
        },
    }
    summary["recommended_next_action"] = recommended_next(summary)

    out_root = Path(args.out_root)
    write_jsonl(out_root / "pair_observation_v2_overdeferral_rows.jsonl", out_rows)
    write_json(out_root / "pair_observation_v2_overdeferral_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose H001 pair objective v2 over-deferral.")
    parser.add_argument("--objective-v2-rows", required=True)
    parser.add_argument("--failure-mode-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--objective-v2-summary")
    parser.add_argument("--failure-mode-summary")
    parser.add_argument("--substrate-summary")
    parser.add_argument("--min-commit-rate", type=float, default=0.15)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
