import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.object_existence_validation_probe.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in label_rows:
        key = (str(row["episode_key"]), str(row["candidate_id"]))
        existing = lookup.get(key)
        if existing is not None and bool(existing.get("evaluation_only_candidate_correct")) != bool(
            row.get("evaluation_only_candidate_correct")
        ):
            raise ValueError(f"conflicting label for {key}")
        lookup[key] = row
    return lookup


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("rival_identity_request_id"))].append(row)
    return grouped


def request_sort_key(request_id: str) -> Tuple[int, str]:
    suffix = request_id.split(":")[-1]
    if suffix.isdigit():
        return int(suffix), request_id
    return 999999, request_id


def candidate_summary(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {
            "naive_candidate_id": None,
            "naive_post_own_associated_heading_count": None,
            "naive_post_cross_associated_heading_count": None,
            "naive_post_identity_margin": None,
            "naive_post_best_box_score": None,
            "naive_post_min_depth_error_m": None,
            "naive_semantic_rank": None,
            "naive_support_score": None,
        }
    return {
        "naive_candidate_id": row.get("candidate_id"),
        "naive_post_own_associated_heading_count": row.get("post_own_associated_heading_count"),
        "naive_post_cross_associated_heading_count": row.get("post_cross_associated_heading_count"),
        "naive_post_identity_margin": row.get("post_identity_margin"),
        "naive_post_best_box_score": row.get("post_best_box_score"),
        "naive_post_min_depth_error_m": row.get("post_min_depth_error_m"),
        "naive_semantic_rank": row.get("semantic_rank"),
        "naive_support_score": row.get("support_score"),
    }


def analyze_request(
    decision: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    strong_rows = [row for row in evidence_rows if row.get("strong_identity_evidence") is True]
    naive_selected = strong_rows[0] if len(strong_rows) == 1 else None
    naive_candidate_id = None if naive_selected is None else str(naive_selected.get("candidate_id"))
    label = labels.get((str(decision["episode_key"]), str(naive_candidate_id))) if naive_candidate_id else None
    naive_has_label = bool(label) if naive_candidate_id else None
    naive_correct = bool(label.get("evaluation_only_candidate_correct")) if label else None
    branch_deferred = decision.get("action") == "defer_object_existence_validation"
    naive_would_commit = naive_candidate_id is not None
    naive_wrong = bool(naive_would_commit and naive_correct is False)
    naive_success = bool(naive_would_commit and naive_correct is True)
    return {
        "schema_version": SCHEMA_VERSION,
        "rival_identity_request_id": decision.get("rival_identity_request_id"),
        "episode_key": decision.get("episode_key"),
        "scene_key": decision.get("scene_key"),
        "query": decision.get("query"),
        "role": decision.get("role"),
        "request_reason": decision.get("request_reason"),
        "request_taxonomy_route": decision.get("request_taxonomy_route"),
        "branch_action": decision.get("action"),
        "branch_reason": decision.get("reason"),
        "branch_deferred": branch_deferred,
        "strong_identity_candidate_count": len(strong_rows),
        "planned_target_count": decision.get("planned_target_count"),
        "positive_support_candidate_count": decision.get("positive_support_candidate_count"),
        "evidence_candidate_count": len(evidence_rows),
        **candidate_summary(naive_selected),
        "naive_unique_strong_commit_available": naive_would_commit,
        "evaluation_only_naive_candidate_has_label": naive_has_label,
        "evaluation_only_naive_candidate_correct": naive_correct,
        "evaluation_only_naive_success_commit": naive_success,
        "evaluation_only_naive_wrong_goal_commit": naive_wrong,
        "wrong_goal_avoided_by_defer": bool(branch_deferred and naive_wrong),
        "success_lost_by_defer": bool(branch_deferred and naive_success),
        "safe_confirm_allowed": False,
        "object_existence_probe_need": "independent_confirmation_evidence",
        "required_future_evidence": [
            "candidate-independent category confirmation",
            "multi-view object geometry consistency",
            "negative evidence around the candidate region",
            "comparison against nearby same-category or visually similar distractors when available",
        ],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize(
    rows: Sequence[Dict[str, Any]],
    *,
    forbidden: Sequence[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    request_rows = len(rows)
    naive_commit_rows = [row for row in rows if row["naive_unique_strong_commit_available"]]
    naive_wrong_rows = [row for row in rows if row["evaluation_only_naive_wrong_goal_commit"]]
    naive_success_rows = [row for row in rows if row["evaluation_only_naive_success_commit"]]
    wrong_avoided_rows = [row for row in rows if row["wrong_goal_avoided_by_defer"]]
    success_lost_rows = [row for row in rows if row["success_lost_by_defer"]]
    gates = {
        "has_object_existence_rows": request_rows > 0,
        "no_action_forbidden_keys": len(forbidden) == 0,
        "naive_baseline_available": len(naive_commit_rows) > 0,
        "defer_safety_measurable": len(wrong_avoided_rows) + len(success_lost_rows) == request_rows,
        "safe_confirm_not_allowed": all(row["safe_confirm_allowed"] is False for row in rows),
    }
    gates["probe_design_passed"] = all(gates.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "inputs": {
            "evaluated": str(args.evaluated),
            "evidence": str(args.evidence),
            "evaluation_labels": [str(path) for path in args.evaluation_labels],
        },
        "request_rows": request_rows,
        "naive_unique_strong_commit_rows": len(naive_commit_rows),
        "naive_success_commit_rows": len(naive_success_rows),
        "naive_wrong_goal_commit_rows": len(naive_wrong_rows),
        "wrong_goal_avoided_by_defer_rows": len(wrong_avoided_rows),
        "success_lost_by_defer_rows": len(success_lost_rows),
        "wrong_goal_avoided_by_defer_rate": ratio(len(wrong_avoided_rows), request_rows),
        "success_lost_by_defer_rate": ratio(len(success_lost_rows), request_rows),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in rows).items())),
        "branch_action_counts": dict(sorted(Counter(str(row.get("branch_action")) for row in rows).items())),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden)[:50],
        "gates": gates,
        "probe_contract": {
            "target_rows": "request_taxonomy_route == object_existence_validation",
            "naive_baseline": "unique strong object-like candidate would commit without the no-commit safety branch",
            "current_policy": "defer_object_existence_validation",
            "primary_metrics": [
                "wrong_goal_avoided_by_defer_rate",
                "success_lost_by_defer_rate",
                "naive_wrong_goal_commit_rows",
                "naive_success_commit_rows",
            ],
            "future_safe_confirm_gate": [
                "wrong_goal_commit_rows == 0",
                "success_lost_by_defer_rows decreases relative to defer-only",
                "uses_gt_for_action == false",
                "confirmation evidence is independent of ObjectNav evaluation labels",
            ],
        },
        "facts": [
            "The current no-commit branch can be evaluated as a defer-only object-existence safety policy.",
            "The naive unique-strong commit baseline is reconstructed only for analysis after action evidence is fixed.",
        ],
        "agent_inferences": [
            "Single-positive object-existence validation is a different problem from rival identity arbitration.",
            "A future commit rule should require evidence beyond the candidate-centric strong detector association that caused the unsafe toilet commits.",
        ],
        "paper_claim_allowed": False,
        "paper_claim_status": "blocked_until_independent_object_existence_confirmation_is_defined_and_validated",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "object_existence_validation_probe_rows.jsonl",
            "summary": "object_existence_validation_probe_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evaluated_rows = load_jsonl(Path(args.evaluated))
    evidence_rows = load_jsonl(Path(args.evidence))
    label_rows: List[Dict[str, Any]] = []
    for path in args.evaluation_labels:
        label_rows.extend(load_jsonl(Path(path)))
    labels = label_lookup(label_rows)
    evidence_by_request = group_by_request(evidence_rows)
    object_decisions = [
        row for row in evaluated_rows if row.get("request_taxonomy_route") == "object_existence_validation"
    ]
    out_rows = [
        analyze_request(
            decision=row,
            evidence_rows=evidence_by_request.get(str(row.get("rival_identity_request_id")), []),
            labels=labels,
        )
        for row in sorted(object_decisions, key=lambda item: request_sort_key(str(item.get("rival_identity_request_id"))))
    ]
    # Evaluated rows intentionally contain post-action labels. The action-evidence
    # purity check applies to detector/evidence rows only.
    forbidden = action_forbidden_keys(evidence_rows)
    summary = summarize(rows=out_rows, forbidden=forbidden, args=args)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "object_existence_validation_probe_rows.jsonl", out_rows)
    write_json(out_root / "object_existence_validation_probe_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze object-existence validation probe rows.")
    parser.add_argument("--evaluated", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--evaluation-labels", nargs="+", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
