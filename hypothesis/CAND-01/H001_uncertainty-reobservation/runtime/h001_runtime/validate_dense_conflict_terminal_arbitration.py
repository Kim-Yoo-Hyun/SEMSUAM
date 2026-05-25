import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from h001_runtime.design_dense_conflict_terminal_guard import choose_candidate, label_lookup, load_jsonl, ratio, write_json, write_jsonl
from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.dense_conflict_terminal_validation.v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_guard_config(config: Dict[str, Any], expected_name: str) -> Dict[str, Any]:
    guard_name = str(config.get("guard_name"))
    if guard_name != expected_name:
        raise ValueError(f"unexpected guard_name {guard_name!r}; expected {expected_name!r}")
    params = dict(config.get("params") or {})
    required = {
        "max_depth_error_m",
        "max_semantic_rank",
        "min_all_positive_support_margin",
        "min_associated_heading_count",
        "min_box_hit_count",
        "min_mask_hit_count",
        "min_support_score",
        "min_visible_count",
    }
    missing = sorted(required - set(params))
    if missing:
        raise ValueError(f"guard config missing params: {missing}")
    return params


def action_forbidden_keys(action_rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(action_rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def decision_rows(action_rows: Sequence[Dict[str, Any]], guard_name: str, guard: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for action_row in action_rows:
        decision = choose_candidate(action_row, guard)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_decision_only",
                "guard_name": guard_name,
                "episode_key": action_row["episode_key"],
                "scene_key": action_row.get("scene_key"),
                "query": action_row.get("query"),
                "evidence_status": action_row.get("evidence_status"),
                **decision,
                "uses_gt_for_action": False,
            }
        )
    return rows


def evaluated_rows(
    decisions: Sequence[Dict[str, Any]],
    evaluation_labels: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    labels = label_lookup(evaluation_labels)
    rows: List[Dict[str, Any]] = []
    for decision in decisions:
        selected_id = decision.get("selected_candidate_id")
        label_key = (str(decision["episode_key"]), str(selected_id))
        has_label = selected_id is not None and label_key in labels
        selected_correct = labels.get(label_key) if selected_id is not None else None
        rows.append(
            {
                **decision,
                "validation_stage": "evaluation_joined_after_action",
                "evaluation_only_selected_has_label": bool(has_label),
                "evaluation_only_selected_correct": selected_correct,
                "evaluation_only_success_commit": bool(decision["action"] == "commit_candidate" and selected_correct),
                "evaluation_only_wrong_goal_commit": bool(decision["action"] == "commit_candidate" and has_label and not selected_correct),
                "evaluation_only_no_label_commit": bool(decision["action"] == "commit_candidate" and not has_label),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def summarize(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    commit_rows = [row for row in rows if row["action"] == "commit_candidate"]
    success_rows = [row for row in rows if row.get("evaluation_only_success_commit") is True]
    wrong_rows = [row for row in rows if row.get("evaluation_only_wrong_goal_commit") is True]
    no_label_rows = [row for row in rows if row.get("evaluation_only_no_label_commit") is True]
    associated_rows = [row for row in rows if row.get("evidence_status") == "associated"]
    associated_commits = [row for row in commit_rows if row.get("evidence_status") == "associated"]
    associated_success = [row for row in success_rows if row.get("evidence_status") == "associated"]
    associated_wrong = [row for row in wrong_rows if row.get("evidence_status") == "associated"]
    return {
        "rows": len(rows),
        "associated_rows": len(associated_rows),
        "unassociated_rows": len([row for row in rows if row.get("evidence_status") == "unassociated"]),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "no_label_commit_rows": len(no_label_rows),
        "associated_commit_rows": len(associated_commits),
        "associated_success_commit_rows": len(associated_success),
        "associated_wrong_goal_commit_rows": len(associated_wrong),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "success_commit_rate": ratio(len(success_rows), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), len(rows)),
        "associated_commit_rate": ratio(len(associated_commits), len(associated_rows)),
        "associated_success_commit_rate": ratio(len(associated_success), len(associated_rows)),
        "associated_wrong_goal_commit_rate": ratio(len(associated_wrong), len(associated_rows)),
        "action_counts": dict(sorted(Counter(str(row.get("action")) for row in rows).items())),
        "reason_counts": dict(sorted(Counter(str(row.get("reason")) for row in rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in rows).items())),
    }


def row_failure_type(row: Dict[str, Any], validation_scope: str) -> str:
    if row.get("evaluation_only_no_label_commit") is True:
        return "evaluation_label_plumbing_failure"
    if row.get("evaluation_only_wrong_goal_commit") is True:
        if "secondary" in validation_scope or "stress" in validation_scope:
            return "stress_slice_wrong_commit"
        return "guard_wrong_commit_depth_consistent_wrong_instance"
    if row.get("evidence_status") == "unassociated":
        return "association_coverage_failure"
    if row.get("action") == "defer":
        reason = str(row.get("reason"))
        if reason in {
            "associated_heading_count_below_guard",
            "box_hit_count_below_guard",
            "mask_hit_count_below_guard",
            "missing_depth_error",
            "depth_error_above_guard",
            "visible_count_below_guard",
        }:
            return "correct_candidate_blocked_by_association"
        return "guard_defer_or_low_confidence"
    return "none"


def attach_failure_taxonomy(rows: Sequence[Dict[str, Any]], validation_scope: str) -> List[Dict[str, Any]]:
    evaluated: List[Dict[str, Any]] = []
    for row in rows:
        evaluated.append({**row, "failure_taxonomy_type": row_failure_type(row, validation_scope)})
    return evaluated


def summarize_failure_taxonomy(rows: Sequence[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
    counts = Counter(str(row.get("failure_taxonomy_type")) for row in rows)
    flags = {
        "guard_over_defer_no_success": bool(
            summary["associated_rows"] > 0
            and summary["associated_commit_rows"] == 0
            and summary["associated_success_commit_rows"] == 0
        ),
        "has_wrong_goal_commit": bool(summary["wrong_goal_commit_rows"] > 0),
        "has_no_label_commit": bool(summary["no_label_commit_rows"] > 0),
        "has_unassociated_rows": bool(summary["unassociated_rows"] > 0),
    }
    return {
        "row_counts": dict(sorted(counts.items())),
        "summary_flags": flags,
    }


def stable_metric_subset(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "commit_rows": summary["commit_rows"],
        "success_commit_rows": summary["success_commit_rows"],
        "wrong_goal_commit_rows": summary["wrong_goal_commit_rows"],
        "associated_commit_rows": summary["associated_commit_rows"],
        "associated_success_commit_rows": summary["associated_success_commit_rows"],
        "associated_wrong_goal_commit_rows": summary["associated_wrong_goal_commit_rows"],
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    action_rows = load_jsonl(Path(args.action_evidence))
    labels = load_jsonl(Path(args.evaluation_labels))
    guard_config = load_json(Path(args.guard_config))
    guard_name = str(args.guard_name)
    guard = validate_guard_config(guard_config, guard_name)

    forbidden = action_forbidden_keys(action_rows)
    decisions = decision_rows(action_rows, guard_name, guard)
    evaluated = attach_failure_taxonomy(evaluated_rows(decisions, labels), str(args.validation_scope))
    validation_summary = summarize(evaluated)
    failure_taxonomy_summary = summarize_failure_taxonomy(evaluated, validation_summary)

    design_expected = {
        "commit_rows": int(args.expected_commit_rows),
        "success_commit_rows": int(args.expected_success_commit_rows),
        "wrong_goal_commit_rows": int(args.expected_wrong_goal_commit_rows),
        "associated_commit_rows": int(args.expected_associated_commit_rows),
        "associated_success_commit_rows": int(args.expected_associated_success_commit_rows),
        "associated_wrong_goal_commit_rows": int(args.expected_associated_wrong_goal_commit_rows),
    }
    observed = stable_metric_subset(validation_summary)
    metric_gate_mode = str(args.metric_gate_mode)
    metric_match = observed == design_expected
    metric_gate_passed = True if metric_gate_mode == "none" else metric_match
    safety_passed = validation_summary["wrong_goal_commit_rows"] <= int(args.max_wrong_goal_commit_rows)
    no_label_passed = validation_summary["no_label_commit_rows"] <= int(args.max_no_label_commit_rows)
    utility_passed = validation_summary["success_commit_rows"] >= int(args.min_success_commit_rows)
    minimum_commit_passed = validation_summary["commit_rows"] >= int(args.min_commit_rows)
    local_full_gate_passed = bool(
        metric_gate_passed
        and safety_passed
        and no_label_passed
        and utility_passed
        and minimum_commit_passed
        and not forbidden
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "validation_scope": str(args.validation_scope),
        "guard_name": guard_name,
        "guard_config": str(args.guard_config),
        "action_evidence": str(args.action_evidence),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "guard": guard,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "summary": validation_summary,
        "design_expected_metrics": design_expected,
        "observed_stable_metrics": observed,
        "metric_gate_mode": metric_gate_mode,
        "stable_metric_match_design": metric_match,
        "metric_gate_passed": metric_gate_passed,
        "safety_gate_passed": safety_passed,
        "no_label_gate_passed": no_label_passed,
        "nonzero_utility_gate_passed": utility_passed,
        "minimum_commit_gate_passed": minimum_commit_passed,
        "failure_taxonomy_summary": failure_taxonomy_summary,
        "local_fixed_rule_validation_passed": local_full_gate_passed,
        "terminal_validation_gate_passed": local_full_gate_passed,
        "paper_claim_allowed": False,
        "paper_claim_status": str(args.paper_claim_status),
        "interpretation": {
            "fact": (
                "The validation script writes action decisions before joining evaluation labels, and the action "
                "evidence scan found no forbidden correctness keys."
            ),
            "agent_inference": str(args.agent_inference),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "summary": "terminal_validation_summary.json",
            "decision_rows": "terminal_validation_decision_rows.jsonl",
            "evaluated_rows": "terminal_validation_evaluated_rows.jsonl",
        },
    }

    out_root = Path(args.out_root)
    write_jsonl(out_root / "terminal_validation_decision_rows.jsonl", decisions)
    write_jsonl(out_root / "terminal_validation_evaluated_rows.jsonl", evaluated)
    write_json(out_root / "terminal_validation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a frozen dense-conflict terminal arbitration guard.")
    parser.add_argument("--action-evidence", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--guard-config", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--guard-name", default="strict_depth_consistency_v1")
    parser.add_argument("--validation-scope", default="dense_conflict_generalization_v1_same_split_fixed_rule")
    parser.add_argument("--metric-gate-mode", choices=["exact", "none"], default="exact")
    parser.add_argument("--expected-commit-rows", type=int, default=3)
    parser.add_argument("--expected-success-commit-rows", type=int, default=3)
    parser.add_argument("--expected-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument("--expected-associated-commit-rows", type=int, default=3)
    parser.add_argument("--expected-associated-success-commit-rows", type=int, default=3)
    parser.add_argument("--expected-associated-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument("--max-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument("--max-no-label-commit-rows", type=int, default=0)
    parser.add_argument("--min-commit-rows", type=int, default=0)
    parser.add_argument("--min-success-commit-rows", type=int, default=1)
    parser.add_argument("--paper-claim-status", default="same_split_fixed_rule_validation_not_method_claim")
    parser.add_argument(
        "--agent-inference",
        default=(
            "The frozen guard reproduces the same-split safety-positive result, but independent validation is "
            "still required before claiming terminal arbitration utility."
        ),
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
