import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.design_dense_conflict_terminal_guard import (
    candidate_passes,
    choose_candidate,
    load_jsonl,
    write_json,
    write_jsonl,
)
from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.dense_conflict_rival_identity_policy.v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: Any, default: int = 9999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row["episode_key"]), str(row["candidate_id"])): row
        for row in label_rows
    }


def positive_candidates(action_row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        candidate
        for candidate in list(action_row.get("candidate_evidence") or [])
        if candidate.get("positive_support") is True
    ]


def eligible_candidates(action_row: Dict[str, Any], guard: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        candidate
        for candidate in positive_candidates(action_row)
        if candidate_passes(candidate, guard)[0]
    ]


def candidate_key(candidate: Dict[str, Any]) -> Tuple[float, float, float, int]:
    return (
        safe_float(candidate.get("support_score")) or 0.0,
        safe_float(candidate.get("detector_score_max")) or 0.0,
        safe_float(candidate.get("semantic_score")) or 0.0,
        -safe_int(candidate.get("semantic_rank")),
    )


def support_best(candidates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return max(candidates, key=candidate_key, default=None)


def depth_best(candidates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    finite = [candidate for candidate in candidates if safe_float(candidate.get("min_depth_error_m")) is not None]
    return min(
        finite,
        key=lambda item: (
            safe_float(item.get("min_depth_error_m")) or float("inf"),
            -((safe_float(item.get("support_score")) or 0.0)),
            -((safe_float(item.get("detector_score_max")) or 0.0)),
            safe_int(item.get("semantic_rank")),
        ),
        default=None,
    )


def semantic_top(candidates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return min(
        candidates,
        key=lambda item: (
            safe_int(item.get("semantic_rank")),
            -((safe_float(item.get("semantic_score")) or 0.0)),
            -((safe_float(item.get("support_score")) or 0.0)),
        ),
        default=None,
    )


def request_decision(action_row: Dict[str, Any], reason: str, focus: Optional[Dict[str, Any]], rivals: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "action": "request_rival_identity_confirmation",
        "reason": reason,
        "selected_candidate_id": str(focus.get("candidate_id")) if focus else None,
        "rival_candidate_ids": [str(candidate.get("candidate_id")) for candidate in rivals[:5]],
        "uses_gt_for_action": False,
    }


def commit_decision(candidate: Optional[Dict[str, Any]], reason: str) -> Dict[str, Any]:
    if candidate is None:
        return {
            "action": "defer_or_expand_retrieval",
            "reason": "no_actionable_candidate",
            "selected_candidate_id": None,
            "rival_candidate_ids": [],
            "uses_gt_for_action": False,
        }
    return {
        "action": "commit_candidate",
        "reason": reason,
        "selected_candidate_id": str(candidate.get("candidate_id")),
        "rival_candidate_ids": [],
        "uses_gt_for_action": False,
    }


def strict_depth_policy(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    decision = choose_candidate(action_row, guard)
    return {
        "action": decision["action"],
        "reason": decision["reason"],
        "selected_candidate_id": decision.get("selected_candidate_id"),
        "rival_candidate_ids": [],
        "uses_gt_for_action": False,
    }


def support_margin_only_policy(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    del guard
    return commit_decision(support_best(positive_candidates(action_row)), "support_margin_only_best_positive_support")


def depth_margin_only_policy(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    del guard
    return commit_decision(depth_best(positive_candidates(action_row)), "depth_margin_only_best_depth_consistency")


def semantic_top_only_policy(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    del guard
    return commit_decision(semantic_top(positive_candidates(action_row)), "semantic_top_only_best_rank")


def defer_all_ambiguous_policy(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    del guard
    positives = positive_candidates(action_row)
    if len(positives) >= 2:
        return request_decision(action_row, "defer_all_ambiguous_multiple_positive_candidates", support_best(positives), positives)
    return commit_decision(positives[0] if positives else None, "defer_all_ambiguous_single_positive_candidate")


def rival_identity_confirmation_policy(action_row: Dict[str, Any], guard: Dict[str, Any]) -> Dict[str, Any]:
    positives = positive_candidates(action_row)
    eligible = eligible_candidates(action_row, guard)
    if not positives:
        return {
            "action": "defer_or_expand_retrieval",
            "reason": "no_positive_support",
            "selected_candidate_id": None,
            "rival_candidate_ids": [],
            "uses_gt_for_action": False,
        }
    if not eligible:
        return request_decision(action_row, "request_identity_no_guard_eligible_positive_candidates", support_best(positives), positives)
    if len(eligible) > 1:
        return request_decision(action_row, "request_identity_multiple_guard_eligible_rivals", support_best(eligible), eligible)

    only = eligible[0]
    if safe_int(only.get("semantic_rank")) == 1:
        return commit_decision(only, "commit_unique_guard_eligible_semantic_top")
    return request_decision(action_row, "request_identity_unique_guard_eligible_not_semantic_top", only, positives)


POLICIES = {
    "strict_depth_consistency_v1": strict_depth_policy,
    "support_margin_only": support_margin_only_policy,
    "depth_margin_only": depth_margin_only_policy,
    "semantic_top_only": semantic_top_only_policy,
    "defer_all_ambiguous": defer_all_ambiguous_policy,
    "rival_identity_confirmation_v1": rival_identity_confirmation_policy,
}


def load_sources(args: argparse.Namespace) -> List[Dict[str, Any]]:
    return [
        {
            "source_name": "primary_independent",
            "role": "primary",
            "action_rows": load_jsonl(Path(args.primary_action_evidence)),
            "labels": label_lookup(load_jsonl(Path(args.primary_evaluation_labels))),
        },
        {
            "source_name": "secondary_stress",
            "role": "secondary_stress",
            "action_rows": load_jsonl(Path(args.secondary_action_evidence)),
            "labels": label_lookup(load_jsonl(Path(args.secondary_evaluation_labels))),
        },
    ]


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def evaluate_decision(
    *,
    source_name: str,
    role: str,
    policy_name: str,
    action_row: Dict[str, Any],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    decision: Dict[str, Any],
) -> Dict[str, Any]:
    selected_id = decision.get("selected_candidate_id")
    label = labels.get((str(action_row["episode_key"]), str(selected_id))) if selected_id else None
    selected_correct = bool(label.get("evaluation_only_candidate_correct")) if label else None
    commit = decision["action"] == "commit_candidate"
    request = decision["action"] == "request_rival_identity_confirmation"
    return {
        "schema_version": SCHEMA_VERSION,
        "source_name": source_name,
        "role": role,
        "policy_name": policy_name,
        "episode_key": action_row["episode_key"],
        "scene_key": action_row.get("scene_key"),
        "query": action_row.get("query"),
        "evidence_status": action_row.get("evidence_status"),
        "positive_support_candidate_count": action_row.get("positive_support_candidate_count"),
        "candidate_count": action_row.get("candidate_count"),
        **decision,
        "evaluation_only_selected_has_label": bool(label) if commit else None,
        "evaluation_only_selected_correct": selected_correct if commit else None,
        "evaluation_only_success_commit": bool(commit and selected_correct is True),
        "evaluation_only_wrong_goal_commit": bool(commit and selected_correct is False),
        "evaluation_only_no_label_commit": bool(commit and label is None),
        "evaluation_only_request_identity": bool(request),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize_policy(rows: Sequence[Dict[str, Any]], policy_name: str) -> Dict[str, Any]:
    policy_rows = [row for row in rows if row["policy_name"] == policy_name]
    commit_rows = [row for row in policy_rows if row["action"] == "commit_candidate"]
    success_rows = [row for row in policy_rows if row["evaluation_only_success_commit"]]
    wrong_rows = [row for row in policy_rows if row["evaluation_only_wrong_goal_commit"]]
    no_label_rows = [row for row in policy_rows if row["evaluation_only_no_label_commit"]]
    request_rows = [row for row in policy_rows if row["action"] == "request_rival_identity_confirmation"]
    primary_rows = [row for row in policy_rows if row["role"] == "primary"]
    primary_success = [row for row in primary_rows if row["evaluation_only_success_commit"]]
    primary_wrong = [row for row in primary_rows if row["evaluation_only_wrong_goal_commit"]]
    secondary_rows = [row for row in policy_rows if row["role"] == "secondary_stress"]
    secondary_wrong = [row for row in secondary_rows if row["evaluation_only_wrong_goal_commit"]]

    return {
        "policy_name": policy_name,
        "rows": len(policy_rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "no_label_commit_rows": len(no_label_rows),
        "request_identity_confirmation_rows": len(request_rows),
        "defer_or_expand_rows": len([row for row in policy_rows if row["action"] == "defer_or_expand_retrieval"]),
        "commit_rate": ratio(len(commit_rows), len(policy_rows)),
        "success_commit_rate": ratio(len(success_rows), len(policy_rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), len(policy_rows)),
        "request_identity_confirmation_rate": ratio(len(request_rows), len(policy_rows)),
        "primary_success_commit_rows": len(primary_success),
        "primary_wrong_goal_commit_rows": len(primary_wrong),
        "secondary_wrong_goal_commit_rows": len(secondary_wrong),
        "action_counts": dict(sorted(Counter(str(row["action"]) for row in policy_rows).items())),
        "reason_counts": dict(sorted(Counter(str(row["reason"]) for row in policy_rows).items())),
        "diagnostic_gate": {
            "safety_gate_passed": len(wrong_rows) == 0,
            "no_label_gate_passed": len(no_label_rows) == 0,
            "primary_nonzero_success_gate_passed": len(primary_success) >= 1,
            "identity_request_gate_passed": len(request_rows) >= 1,
            "secondary_stress_safety_gate_passed": len(secondary_wrong) == 0,
        },
    }


def summarize(rows: Sequence[Dict[str, Any]], forbidden: Sequence[str], args: argparse.Namespace) -> Dict[str, Any]:
    policy_summaries = {name: summarize_policy(rows, name) for name in POLICIES}
    strict = policy_summaries["strict_depth_consistency_v1"]
    rival = policy_summaries["rival_identity_confirmation_v1"]
    simpler = {
        name: policy_summaries[name]
        for name in ["support_margin_only", "depth_margin_only", "semantic_top_only", "defer_all_ambiguous"]
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden)[:50],
        "policy_summaries": policy_summaries,
        "rival_identity_vs_strict_depth": {
            "wrong_goal_commit_delta": rival["wrong_goal_commit_rows"] - strict["wrong_goal_commit_rows"],
            "success_commit_delta": rival["success_commit_rows"] - strict["success_commit_rows"],
            "request_identity_confirmation_delta": rival["request_identity_confirmation_rows"]
            - strict["request_identity_confirmation_rows"],
        },
        "simpler_alternative_summary": simpler,
        "diagnostic_passed": bool(
            rival["diagnostic_gate"]["safety_gate_passed"]
            and rival["diagnostic_gate"]["no_label_gate_passed"]
            and rival["diagnostic_gate"]["primary_nonzero_success_gate_passed"]
            and rival["diagnostic_gate"]["identity_request_gate_passed"]
            and rival["diagnostic_gate"]["secondary_stress_safety_gate_passed"]
            and len(forbidden) == 0
        ),
        "paper_claim_allowed": False,
        "paper_claim_status": "diagnostic_policy_only_requires_fresh_or_predeclared_validation",
        "interpretation": {
            "fact": (
                "All compared policies consume action-time candidate evidence only; evaluation labels are joined "
                "after decisions are fixed."
            ),
            "agent_inference": (
                "rival_identity_confirmation_v1 turns same-category rival ambiguity into an active confirmation "
                "request while preserving nonzero primary commits on this diagnostic evidence. This is a design "
                "diagnostic, not a paper-facing utility proof."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "rival_identity_policy_rows.jsonl",
            "summary": "rival_identity_policy_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    guard = dict(load_json(Path(args.guard_config)).get("params") or {})
    sources = load_sources(args)
    action_rows_all = [row for source in sources for row in source["action_rows"]]
    forbidden = action_forbidden_keys(action_rows_all)
    out_rows: List[Dict[str, Any]] = []

    for source in sources:
        for action_row in source["action_rows"]:
            for policy_name, policy in POLICIES.items():
                decision = policy(action_row, guard)
                out_rows.append(
                    evaluate_decision(
                        source_name=source["source_name"],
                        role=source["role"],
                        policy_name=policy_name,
                        action_row=action_row,
                        labels=source["labels"],
                        decision=decision,
                    )
                )

    summary = summarize(out_rows, forbidden, args)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "rival_identity_policy_rows.jsonl", out_rows)
    write_json(out_root / "rival_identity_policy_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare rival identity confirmation against dense-conflict terminal alternatives.")
    parser.add_argument("--guard-config", required=True)
    parser.add_argument("--primary-action-evidence", required=True)
    parser.add_argument("--primary-evaluation-labels", required=True)
    parser.add_argument("--secondary-action-evidence", required=True)
    parser.add_argument("--secondary-evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
