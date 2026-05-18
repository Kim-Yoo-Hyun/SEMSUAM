import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.association_recovery_arbitration.v1"


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


def arbitration_decision(row: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    top_supported = bool(row.get("top_positive_support_after_second"))
    top_score = safe_float(row.get("risk_top_supported_score_after_second")) or 0.0
    alt_score = safe_float(row.get("risk_best_alt_supported_score_after_second")) or 0.0
    support_gap = safe_float(row.get("risk_support_gap_alt_minus_top_after_second"))
    if support_gap is None:
        support_gap = alt_score - top_score
    r_total = safe_float(row.get("R_after2")) or 1.0
    r_no_evidence = safe_float(row.get("R_after2_no_evidence")) or 0.0
    r_contradiction = safe_float(row.get("R_after2_contradiction")) or 0.0
    r_ambiguity = safe_float(row.get("R_after2_ambiguity")) or 0.0
    r_property = safe_float(row.get("R_after2_property_weakness")) or 0.0

    if not top_supported:
        if alt_score > 0.0:
            action = "reject_top_or_defer"
            reason = "top_has_no_support_alt_has_support"
        else:
            action = "retry_association_or_defer"
            reason = "persistent_no_evidence"
    elif support_gap >= 0.0:
        action = "reject_top_or_request_pair_view"
        reason = "alt_not_weaker_than_top"
    elif r_contradiction >= float(args.contradiction_block):
        action = "reject_top_or_request_pair_view"
        reason = "contradiction_block"
    elif r_ambiguity >= float(args.ambiguity_block):
        action = "request_paired_top_alt_view"
        reason = "ambiguity_block"
    elif r_property >= float(args.property_block):
        action = "request_property_targeted_view"
        reason = "property_weakness_block"
    elif r_total < float(args.risk_total_commit) and (-support_gap) >= float(args.support_margin):
        action = "commit_top"
        reason = "top_supported_low_risk_margin"
    else:
        action = "defer_insufficient_margin"
        reason = "low_confidence_margin_or_residual_risk"

    return {
        "arbitration_action": action,
        "arbitration_reason": reason,
        "arbitration_top_supported": top_supported,
        "arbitration_top_score": top_score,
        "arbitration_alt_score": alt_score,
        "arbitration_support_gap_alt_minus_top": support_gap,
        "arbitration_R_after2": r_total,
        "arbitration_R_after2_no_evidence": r_no_evidence,
        "arbitration_R_after2_contradiction": r_contradiction,
        "arbitration_R_after2_ambiguity": r_ambiguity,
        "arbitration_R_after2_property_weakness": r_property,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    source_rows = load_jsonl(Path(args.rows))
    failure_rows = {}
    if args.failure_modes:
        failure_rows = {
            str(row.get("episode_key")): row
            for row in load_jsonl(Path(args.failure_modes))
            if row.get("episode_key") is not None
        }

    out_rows: List[Dict[str, Any]] = []
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    action_by_failure: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in source_rows:
        decision = arbitration_decision(row, args)
        episode_key = str(row.get("episode_key"))
        failure = failure_rows.get(episode_key, {})
        top_correct = row.get("top_candidate_correct")
        commit = decision["arbitration_action"] == "commit_top"
        out = {
            "schema_version": SCHEMA_VERSION,
            "episode_key": episode_key,
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "second_observation_reason": row.get("second_observation_reason"),
            "risk_top_candidate_id": row.get("risk_top_candidate_id"),
            "risk_best_alt_candidate_id_after_second": row.get("risk_best_alt_candidate_id_after_second"),
            "association_recovered_after_second": row.get("association_recovered_after_second"),
            "top_positive_support_after_second": row.get("top_positive_support_after_second"),
            "primary_failure_mode": failure.get("primary_failure_mode"),
            **decision,
            "arbitration_commit_top": commit,
            "top_candidate_correct": top_correct,
            "wrong_goal_commit_if_arbitration_applied": bool(commit and top_correct is False),
            "success_commit_if_arbitration_applied": bool(commit and top_correct is True),
            "success_lost_by_arbitration_defer": bool((not commit) and top_correct is True),
            "wrong_goal_avoided_by_arbitration_defer": bool((not commit) and top_correct is False),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": top_correct is not None,
        }
        out_rows.append(out)
        action_counts[out["arbitration_action"]] += 1
        reason_counts[out["arbitration_reason"]] += 1
        action_by_failure[str(out.get("primary_failure_mode"))][out["arbitration_action"]] += 1

    out_root = Path(args.out_root)
    write_jsonl(out_root / "association_recovery_arbitration_rows.jsonl", out_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "rows": len(out_rows),
        "source_rows": str(args.rows),
        "failure_modes": str(args.failure_modes) if args.failure_modes else None,
        "thresholds": {
            "risk_total_commit": float(args.risk_total_commit),
            "support_margin": float(args.support_margin),
            "contradiction_block": float(args.contradiction_block),
            "ambiguity_block": float(args.ambiguity_block),
            "property_block": float(args.property_block),
        },
        "arbitration_action_counts": dict(sorted(action_counts.items())),
        "arbitration_reason_counts": dict(sorted(reason_counts.items())),
        "arbitration_action_by_primary_failure_mode": {
            failure: dict(sorted(counts.items()))
            for failure, counts in sorted(action_by_failure.items())
        },
        "commit_top_rate": ratio(sum(row["arbitration_commit_top"] for row in out_rows), len(out_rows)),
        "wrong_goal_commit_rate_if_arbitration_applied": ratio(
            sum(row["wrong_goal_commit_if_arbitration_applied"] for row in out_rows),
            len(out_rows),
        ),
        "success_commit_rate_if_arbitration_applied": ratio(
            sum(row["success_commit_if_arbitration_applied"] for row in out_rows),
            len(out_rows),
        ),
        "success_lost_by_arbitration_defer_rate": ratio(
            sum(row["success_lost_by_arbitration_defer"] for row in out_rows),
            len(out_rows),
        ),
        "wrong_goal_avoided_by_arbitration_defer_rate": ratio(
            sum(row["wrong_goal_avoided_by_arbitration_defer"] for row in out_rows),
            len(out_rows),
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "association_recovery_arbitration_rows.jsonl",
            "summary": "association_recovery_arbitration_summary.json",
        },
    }
    write_json(out_root / "association_recovery_arbitration_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply a non-GT commit/defer arbitration design to H001 second-observation rows.")
    parser.add_argument("--rows", required=True)
    parser.add_argument("--failure-modes", default=None)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--risk-total-commit", type=float, default=0.6)
    parser.add_argument("--support-margin", type=float, default=0.05)
    parser.add_argument("--contradiction-block", type=float, default=0.25)
    parser.add_argument("--ambiguity-block", type=float, default=0.5)
    parser.add_argument("--property-block", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
