import argparse
import json
import math
from collections import Counter
from itertools import product
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.dense_conflict_terminal_guard_design.v1"


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], bool]:
    lookup: Dict[Tuple[str, str], bool] = {}
    for row in label_rows:
        lookup[(str(row["episode_key"]), str(row["candidate_id"]))] = bool(
            row.get("evaluation_only_candidate_correct")
        )
    return lookup


def candidate_passes(candidate: Dict[str, Any], guard: Dict[str, Any]) -> Tuple[bool, str]:
    if candidate.get("positive_support") is not True:
        return False, "no_positive_support"
    if safe_int(candidate.get("semantic_rank"), 9999) > int(guard["max_semantic_rank"]):
        return False, "semantic_rank_above_guard"
    if safe_int(candidate.get("associated_heading_count")) < int(guard["min_associated_heading_count"]):
        return False, "associated_heading_count_below_guard"
    if safe_int(candidate.get("mask_hit_count")) < int(guard["min_mask_hit_count"]):
        return False, "mask_hit_count_below_guard"
    if safe_int(candidate.get("box_hit_count")) < int(guard["min_box_hit_count"]):
        return False, "box_hit_count_below_guard"
    if safe_int(candidate.get("visible_count")) < int(guard["min_visible_count"]):
        return False, "visible_count_below_guard"

    support_score = safe_float(candidate.get("support_score")) or 0.0
    if support_score < float(guard["min_support_score"]):
        return False, "support_score_below_guard"

    max_depth = guard.get("max_depth_error_m")
    if max_depth is not None:
        depth_error = safe_float(candidate.get("min_depth_error_m"))
        if depth_error is None:
            return False, "missing_depth_error"
        if depth_error > float(max_depth):
            return False, "depth_error_above_guard"

    return True, "eligible"


def support_margin(candidate: Optional[Dict[str, Any]], competitors: Sequence[Dict[str, Any]]) -> Optional[float]:
    if candidate is None:
        return None
    selected_score = safe_float(candidate.get("support_score")) or 0.0
    other_scores = [
        safe_float(item.get("support_score")) or 0.0
        for item in competitors
        if str(item.get("candidate_id")) != str(candidate.get("candidate_id"))
    ]
    return selected_score - max(other_scores, default=0.0)


def depth_advantage(candidate: Optional[Dict[str, Any]], competitors: Sequence[Dict[str, Any]]) -> Optional[float]:
    if candidate is None:
        return None
    selected_depth = safe_float(candidate.get("min_depth_error_m"))
    other_depths = [
        safe_float(item.get("min_depth_error_m"))
        for item in competitors
        if str(item.get("candidate_id")) != str(candidate.get("candidate_id"))
    ]
    other_depths = [value for value in other_depths if value is not None]
    if selected_depth is None or not other_depths:
        return None
    return min(other_depths) - selected_depth


def choose_candidate(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    candidates = list(action_row.get("candidate_evidence") or [])
    positive_candidates = [candidate for candidate in candidates if candidate.get("positive_support") is True]
    eligible_with_reasons = [(candidate, candidate_passes(candidate, guard)) for candidate in positive_candidates]
    eligible = [candidate for candidate, (passes, _) in eligible_with_reasons if passes]
    best = max(
        eligible,
        key=lambda item: (
            safe_float(item.get("support_score")) or 0.0,
            safe_float(item.get("detector_score_max")) or 0.0,
            safe_float(item.get("semantic_score")) or 0.0,
            -safe_int(item.get("semantic_rank"), 9999),
        ),
        default=None,
    )
    margin_all_positive = support_margin(best, positive_candidates)
    margin_eligible = support_margin(best, eligible)
    advantage = depth_advantage(best, positive_candidates)

    if best is None:
        reasons = Counter(reason for _, (_, reason) in eligible_with_reasons)
        reason = "no_eligible_candidate" if positive_candidates else "no_positive_support"
        if reasons:
            reason = str(reasons.most_common(1)[0][0])
        return {
            "action": "defer",
            "reason": reason,
            "selected_candidate_id": None,
            "selected_support_score": None,
            "selected_min_depth_error_m": None,
            "selected_semantic_rank": None,
            "all_positive_support_margin": None,
            "eligible_support_margin": None,
            "depth_advantage_m": None,
            "eligible_candidate_count": len(eligible),
            "positive_support_candidate_count": len(positive_candidates),
            "uses_gt_for_action": False,
        }

    if (margin_all_positive or 0.0) < float(guard["min_all_positive_support_margin"]):
        return {
            "action": "defer",
            "reason": "all_positive_support_margin_below_guard",
            "selected_candidate_id": None,
            "selected_support_score": None,
            "selected_min_depth_error_m": None,
            "selected_semantic_rank": None,
            "all_positive_support_margin": margin_all_positive,
            "eligible_support_margin": margin_eligible,
            "depth_advantage_m": advantage,
            "eligible_candidate_count": len(eligible),
            "positive_support_candidate_count": len(positive_candidates),
            "uses_gt_for_action": False,
        }

    return {
        "action": "commit_candidate",
        "reason": "commit_strict_depth_consistent_support",
        "selected_candidate_id": str(best.get("candidate_id")),
        "selected_support_score": safe_float(best.get("support_score")),
        "selected_min_depth_error_m": safe_float(best.get("min_depth_error_m")),
        "selected_semantic_rank": safe_int(best.get("semantic_rank"), 9999),
        "all_positive_support_margin": margin_all_positive,
        "eligible_support_margin": margin_eligible,
        "depth_advantage_m": advantage,
        "eligible_candidate_count": len(eligible),
        "positive_support_candidate_count": len(positive_candidates),
        "uses_gt_for_action": False,
    }


def evaluate_guard(
    action_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], bool],
    guard_name: str,
    guard: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    rows: List[Dict[str, Any]] = []
    for action_row in action_rows:
        decision = choose_candidate(action_row, guard)
        selected_id = decision.get("selected_candidate_id")
        selected_correct = labels.get((str(action_row["episode_key"]), str(selected_id))) if selected_id else None
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "guard_name": guard_name,
                "episode_key": action_row["episode_key"],
                "scene_key": action_row.get("scene_key"),
                "query": action_row.get("query"),
                "evidence_status": action_row.get("evidence_status"),
                **decision,
                "evaluation_only_selected_correct": selected_correct,
                "evaluation_only_success_commit": bool(decision["action"] == "commit_candidate" and selected_correct),
                "evaluation_only_wrong_goal_commit": bool(decision["action"] == "commit_candidate" and not selected_correct),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )

    commit_rows = [row for row in rows if row["action"] == "commit_candidate"]
    success_rows = [row for row in rows if row["evaluation_only_success_commit"]]
    wrong_rows = [row for row in rows if row["evaluation_only_wrong_goal_commit"]]
    associated_rows = [row for row in rows if row["evidence_status"] == "associated"]
    summary = {
        "guard_name": guard_name,
        "guard": guard,
        "rows": len(rows),
        "associated_rows": len(associated_rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "associated_commit_rate": ratio(len([row for row in commit_rows if row["evidence_status"] == "associated"]), len(associated_rows)),
        "success_commit_rate": ratio(len(success_rows), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), len(rows)),
        "action_counts": dict(sorted(Counter(str(row["action"]) for row in rows).items())),
        "reason_counts": dict(sorted(Counter(str(row["reason"]) for row in rows).items())),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    return summary, rows


def sweep_guards(action_rows: Sequence[Dict[str, Any]], labels: Dict[Tuple[str, str], bool]) -> List[Dict[str, Any]]:
    sweep_rows: List[Dict[str, Any]] = []
    max_depth_values: List[Optional[float]] = [0.20, 0.25, 0.30, 0.33, 0.35, 0.40, 0.50, 0.75, 1.00, None]
    for max_depth, min_assoc, min_mask, min_box, min_visible, min_support, min_margin, max_rank in product(
        max_depth_values,
        [1, 2, 3, 4],
        [1, 2, 3, 4],
        [0, 1, 2],
        [0, 2, 4],
        [0.0, 0.50, 0.65, 0.75, 0.85],
        [0.0, 0.10, 0.20, 0.30],
        [1, 2, 3, 5],
    ):
        guard = {
            "max_depth_error_m": max_depth,
            "min_associated_heading_count": min_assoc,
            "min_mask_hit_count": min_mask,
            "min_box_hit_count": min_box,
            "min_visible_count": min_visible,
            "min_support_score": min_support,
            "min_all_positive_support_margin": min_margin,
            "max_semantic_rank": max_rank,
        }
        summary, _ = evaluate_guard(action_rows, labels, "sweep", guard)
        sweep_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                **guard,
                "rows": summary["rows"],
                "associated_rows": summary["associated_rows"],
                "commit_rows": summary["commit_rows"],
                "success_commit_rows": summary["success_commit_rows"],
                "wrong_goal_commit_rows": summary["wrong_goal_commit_rows"],
                "associated_commit_rate": summary["associated_commit_rate"],
                "commit_rate": summary["commit_rate"],
                "success_commit_rate": summary["success_commit_rate"],
                "wrong_goal_commit_rate": summary["wrong_goal_commit_rate"],
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return sweep_rows


def fixed_guards() -> Dict[str, Dict[str, Any]]:
    return {
        "strict_depth_consistency_v1": {
            "max_depth_error_m": 0.33,
            "min_associated_heading_count": 2,
            "min_mask_hit_count": 2,
            "min_box_hit_count": 0,
            "min_visible_count": 0,
            "min_support_score": 0.0,
            "min_all_positive_support_margin": 0.0,
            "max_semantic_rank": 5,
        },
        "rank1_depth_consistency_v1": {
            "max_depth_error_m": 0.33,
            "min_associated_heading_count": 2,
            "min_mask_hit_count": 2,
            "min_box_hit_count": 0,
            "min_visible_count": 0,
            "min_support_score": 0.0,
            "min_all_positive_support_margin": 0.0,
            "max_semantic_rank": 1,
        },
        "support_only_conservative_depth_v1": {
            "max_depth_error_m": 0.40,
            "min_associated_heading_count": 2,
            "min_mask_hit_count": 2,
            "min_box_hit_count": 0,
            "min_visible_count": 0,
            "min_support_score": 0.65,
            "min_all_positive_support_margin": 0.10,
            "max_semantic_rank": 5,
        },
    }


def select_promising_sweep_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    zero_wrong = [row for row in rows if row["wrong_goal_commit_rows"] == 0 and row["success_commit_rows"] > 0]
    zero_wrong.sort(
        key=lambda row: (
            -int(row["success_commit_rows"]),
            int(row["commit_rows"]),
            row["max_depth_error_m"] is None,
            safe_float(row["max_depth_error_m"]) if row["max_depth_error_m"] is not None else 999.0,
            int(row["min_associated_heading_count"]),
            int(row["min_mask_hit_count"]),
            int(row["max_semantic_rank"]),
        )
    )
    return list(zero_wrong[:20])


def run(args: argparse.Namespace) -> Dict[str, Any]:
    action_rows = load_jsonl(Path(args.action_evidence))
    evaluation_rows = load_jsonl(Path(args.evaluation_labels))
    labels = label_lookup(evaluation_rows)

    guard_summaries: Dict[str, Any] = {}
    guard_rows: List[Dict[str, Any]] = []
    for name, guard in fixed_guards().items():
        summary, rows = evaluate_guard(action_rows, labels, name, guard)
        guard_summaries[name] = summary
        guard_rows.extend(rows)

    sweep_rows = sweep_guards(action_rows, labels)
    promising_sweep_rows = select_promising_sweep_rows(sweep_rows)
    selected_guard_name = "strict_depth_consistency_v1"
    selected_summary = guard_summaries[selected_guard_name]
    selected_rows = [row for row in guard_rows if row["guard_name"] == selected_guard_name]
    selected_wrong = [row for row in selected_rows if row["evaluation_only_wrong_goal_commit"]]
    selected_success = [row for row in selected_rows if row["evaluation_only_success_commit"]]
    v0_failure_rows = [
        {
            "episode_key": "HM3D ObjectNav v2:val:5cdEh9F2hJL:14:2:toilet",
            "failure_class": "strict_depth_guard_blocks_wrong_single_positive",
        },
        {
            "episode_key": "HM3D ObjectNav v2:val:mL8ThkuaVTM:2:4:bed",
            "failure_class": "strict_depth_guard_blocks_wrong_high_support_depth_inconsistent",
        },
        {
            "episode_key": "HM3D ObjectNav v2:val:mL8ThkuaVTM:18:0:bed",
            "failure_class": "strict_depth_guard_blocks_wrong_high_support_depth_inconsistent",
        },
        {
            "episode_key": "HM3D ObjectNav v2:val:CrMo8WxCyVb:1:2:toilet",
            "failure_class": "strict_depth_guard_blocks_wrong_single_positive",
        },
    ]

    summary = {
        "schema_version": SCHEMA_VERSION,
        "action_evidence": str(args.action_evidence),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "rows": len(action_rows),
        "associated_rows": sum(1 for row in action_rows if row.get("evidence_status") == "associated"),
        "unassociated_rows": sum(1 for row in action_rows if row.get("evidence_status") == "unassociated"),
        "fixed_guard_summaries": guard_summaries,
        "sweep_rows": len(sweep_rows),
        "promising_zero_wrong_sweep_rows": promising_sweep_rows,
        "selected_guard_name": selected_guard_name,
        "selected_guard_summary": selected_summary,
        "selected_guard_success_rows": selected_success,
        "selected_guard_wrong_rows": selected_wrong,
        "v0_failure_rows_addressed_by_guard": v0_failure_rows,
        "design_decision": {
            "recommended_next_guard": selected_guard_name,
            "terminal_validation_ready": bool(selected_summary["wrong_goal_commit_rows"] == 0 and selected_summary["success_commit_rows"] > 0),
            "terminal_utility_claim_allowed": False,
            "reason": (
                "The selected guard produces nonzero success and zero wrong-goal commits on the same diagnostic split, "
                "but it is calibrated on the failure rows and must be rerun as a fixed rule before promotion."
            ),
            "next_validation_contract": [
                "freeze strict_depth_consistency_v1 before running validation",
                "consume action_evidence_rows.jsonl only for decisions",
                "join evaluation_labels.jsonl only after actions are frozen",
                "report associated and unassociated rows separately",
                "treat unassociated rows as detector/association coverage limits, not terminal failures",
            ],
        },
        "interpretation": {
            "fact": (
                "The v0 wrong commits include high support-score candidates, and strict_depth_consistency_v1 blocks "
                "them through action-time depth, association-count, or mask-count constraints."
            ),
            "paper_claim_status": "same_split_guard_design_not_method_claim",
            "agent_inference": (
                "A strict depth-consistency guard is a safer next fixed-rule candidate than support-score arbitration "
                "because support and support margin alone do not separate success commits from wrong-goal commits."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "summary": "terminal_guard_design_summary.json",
            "fixed_guard_rows": "terminal_guard_diagnostic_rows.jsonl",
            "sweep_rows": "terminal_guard_sweep_rows.jsonl",
        },
    }

    out_root = Path(args.out_root)
    write_json(out_root / "terminal_guard_design_summary.json", summary)
    write_jsonl(out_root / "terminal_guard_diagnostic_rows.jsonl", guard_rows)
    write_jsonl(out_root / "terminal_guard_sweep_rows.jsonl", sweep_rows)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design a safer terminal guard for dense conflict rows.")
    parser.add_argument("--action-evidence", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
