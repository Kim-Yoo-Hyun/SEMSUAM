import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


SCHEMA_VERSION = "h001.dense_terminal_arbitration_diagnostic.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def correct_ids_by_episode(recall_rows: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    indexed: Dict[str, Set[str]] = {}
    for row in recall_rows:
        indexed[str(row.get("episode_key"))] = {
            str(candidate.get("candidate_id"))
            for candidate in row.get("correct_candidates") or []
            if candidate.get("candidate_id") is not None
        }
    return indexed


def ranked_candidates(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        candidates,
        key=lambda row: (
            safe_float(row.get("S_ext")) or 0.0,
            safe_float(row.get("detector_score_max")) or 0.0,
            -int(row.get("external_branch_rank") or 9999),
        ),
        reverse=True,
    )


def first_external(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    return min(candidates, key=lambda row: int(row.get("external_branch_rank") or 9999))


def recompute_reason(best: Optional[Dict[str, Any]], second_score: Optional[float], args: argparse.Namespace) -> str:
    if best is None:
        return "no_external_candidates"
    best_score = safe_float(best.get("S_ext")) or 0.0
    margin = best_score - (second_score if second_score is not None else 0.0)
    if best.get("positive_support") is not True:
        return "defer_no_positive_external_evidence"
    if best_score < float(args.min_commit_score):
        return "defer_weak_external_evidence"
    if margin < float(args.min_commit_margin):
        return "defer_ambiguous_external_evidence"
    if float(best.get("strict_association_count") or 0.0) < float(args.min_strict_association_count):
        return "defer_insufficient_strict_association"
    return "commit_external_candidate"


def classify_row(
    commits: bool,
    selected_correct: bool,
    first_correct: bool,
    wrong_positive_count: int,
    selected_id: Optional[str],
    first_id: Optional[str],
) -> str:
    if not commits:
        return "not_committed"
    if not selected_correct:
        return "unsafe_wrong_commit"
    if wrong_positive_count > 0:
        return "correct_commit_with_wrong_supported_rivals"
    if first_correct and selected_id != first_id:
        return "same_goal_evidence_selection_not_wrong_repair"
    if first_correct:
        return "first_candidate_correct_confirmed"
    return "correct_commit_after_first_candidate_not_correct"


def diagnose_row(row: Dict[str, Any], correct_by_episode: Dict[str, Set[str]], args: argparse.Namespace) -> Dict[str, Any]:
    episode_key = str(row.get("episode_key"))
    correct_ids = correct_by_episode.get(episode_key, set())
    candidates = [dict(candidate) for candidate in row.get("candidate_evidence") or []]
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        candidate["posthoc_candidate_correct"] = candidate_id in correct_ids

    ranked = ranked_candidates(candidates)
    best = ranked[0] if ranked else None
    second = ranked[1] if len(ranked) > 1 else None
    second_score = safe_float(second.get("S_ext")) if second else None
    recomputed_reason = recompute_reason(best, second_score, args)
    recomputed_action = (
        "external_evidence_v1_commit_candidate"
        if recomputed_reason == "commit_external_candidate"
        else "external_evidence_v1_defer"
    )
    first = first_external(candidates)
    selected_id = str(row.get("selected_candidate_id")) if row.get("selected_candidate_id") is not None else None
    first_id = None if first is None else str(first.get("candidate_id"))
    selected = next((candidate for candidate in candidates if str(candidate.get("candidate_id")) == selected_id), None)
    selected_correct = selected_id in correct_ids if selected_id is not None else False
    first_correct = first_id in correct_ids if first_id is not None else False
    positive = [candidate for candidate in candidates if candidate.get("positive_support") is True]
    correct_positive = [candidate for candidate in positive if candidate.get("posthoc_candidate_correct") is True]
    wrong_positive = [candidate for candidate in positive if candidate.get("posthoc_candidate_correct") is not True]
    commits = row.get("external_evidence_v1_action") == "external_evidence_v1_commit_candidate"
    selected_score = safe_float(row.get("selected_score"))
    first_score = safe_float(first.get("S_ext")) if first else None
    selected_first_score_delta = None
    if selected_score is not None and first_score is not None:
        selected_first_score_delta = selected_score - first_score

    classification = classify_row(
        commits=commits,
        selected_correct=selected_correct,
        first_correct=first_correct,
        wrong_positive_count=len(wrong_positive),
        selected_id=selected_id,
        first_id=first_id,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "episode_key": episode_key,
        "external_branch_id": row.get("external_branch_id"),
        "query": row.get("query"),
        "action": row.get("external_evidence_v1_action"),
        "reason": row.get("external_evidence_v1_reason"),
        "recomputed_action": recomputed_action,
        "recomputed_reason": recomputed_reason,
        "action_recompute_matches": row.get("external_evidence_v1_action") == recomputed_action,
        "selected_candidate_id": selected_id,
        "selected_score": selected_score,
        "selected_strict_association_count": None if selected is None else selected.get("strict_association_count"),
        "selected_mask_hit_count": None if selected is None else selected.get("mask_hit_count"),
        "selected_visible_count": None if selected is None else selected.get("visible_count"),
        "selected_positive_support": None if selected is None else selected.get("positive_support"),
        "selected_posthoc_correct": selected_correct,
        "first_external_candidate_id": first_id,
        "first_external_score": first_score,
        "first_external_posthoc_correct": first_correct,
        "selected_differs_from_first": selected_id != first_id,
        "selected_first_score_delta": selected_first_score_delta,
        "score_margin": row.get("score_margin"),
        "second_score": row.get("second_score"),
        "external_candidate_count": len(candidates),
        "posthoc_correct_candidate_ids_in_external_set": sorted(
            str(candidate.get("candidate_id"))
            for candidate in candidates
            if candidate.get("posthoc_candidate_correct") is True
        ),
        "posthoc_correct_candidate_count_in_external_set": sum(
            candidate.get("posthoc_candidate_correct") is True for candidate in candidates
        ),
        "positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in positive),
        "correct_positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in correct_positive),
        "wrong_positive_support_candidate_ids": sorted(str(candidate.get("candidate_id")) for candidate in wrong_positive),
        "positive_support_candidate_count": len(positive),
        "correct_positive_support_candidate_count": len(correct_positive),
        "wrong_positive_support_candidate_count": len(wrong_positive),
        "all_positive_support_candidates_correct": bool(positive and not wrong_positive),
        "terminal_arbitration_class": classification,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evidence_rows = load_jsonl(Path(args.evidence_rows))
    recall_rows = load_jsonl(Path(args.recall_rows))
    correct_by_episode = correct_ids_by_episode(recall_rows)
    diagnostic_rows = [diagnose_row(row, correct_by_episode, args) for row in evidence_rows]

    rows = len(diagnostic_rows)
    commit_rows = [row for row in diagnostic_rows if row["action"] == "external_evidence_v1_commit_candidate"]
    selected_correct_rows = [row for row in diagnostic_rows if row["selected_posthoc_correct"] is True]
    first_correct_rows = [row for row in diagnostic_rows if row["first_external_posthoc_correct"] is True]
    wrong_positive_rows = [row for row in diagnostic_rows if row["wrong_positive_support_candidate_count"] > 0]
    same_goal_rows = [
        row
        for row in diagnostic_rows
        if row["terminal_arbitration_class"] == "same_goal_evidence_selection_not_wrong_repair"
    ]
    action_counts = Counter(str(row["action"]) for row in diagnostic_rows)
    reason_counts = Counter(str(row["reason"]) for row in diagnostic_rows)
    classification_counts = Counter(str(row["terminal_arbitration_class"]) for row in diagnostic_rows)

    selected_correct_rate = ratio(len(selected_correct_rows), rows)
    first_correct_rate = ratio(len(first_correct_rows), rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "evidence_rows": str(args.evidence_rows),
        "recall_rows": str(args.recall_rows),
        "out_root": str(args.out_root),
        "rows": rows,
        "commit_rows": len(commit_rows),
        "action_counts": dict(sorted(action_counts.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
        "terminal_arbitration_class_counts": dict(sorted(classification_counts.items())),
        "selected_posthoc_correct_rate": selected_correct_rate,
        "first_external_posthoc_correct_rate": first_correct_rate,
        "selected_correct_improvement_over_first": None
        if selected_correct_rate is None or first_correct_rate is None
        else selected_correct_rate - first_correct_rate,
        "wrong_positive_support_row_rate": ratio(len(wrong_positive_rows), rows),
        "same_goal_evidence_selection_rate": ratio(len(same_goal_rows), rows),
        "action_recompute_match_rate": ratio(
            sum(row["action_recompute_matches"] is True for row in diagnostic_rows),
            rows,
        ),
        "interpretation": {
            "fact": (
                "This diagnostic joins already-selected dense terminal evidence rows with recall-probe GT "
                "analysis labels after action selection."
            ),
            "agent_inference": (
                "A positive local result means detector evidence can rank a correct dense candidate, but it is "
                "not a wrong-goal repair proof if the first external candidate and all supported candidates are "
                "also correct under post-hoc labels."
            ),
            "paper_claim_status": "local_diagnostic_only",
        },
        "decision": {
            "local_terminal_arbitration_promising": bool(
                rows > 0
                and len(commit_rows) == rows
                and len(selected_correct_rows) == rows
                and not wrong_positive_rows
            ),
            "wrong_repair_utility_proven": bool(
                first_correct_rate is not None
                and selected_correct_rate is not None
                and selected_correct_rate > first_correct_rate
            ),
            "generalization_ready": False,
            "next_validation_need": (
                "independent dense validation with rows that contain wrong or ambiguous positive-support "
                "candidates; do not use same-goal correct-cluster rows as policy utility proof"
            ),
        },
        "thresholds": {
            "min_commit_score": float(args.min_commit_score),
            "min_commit_margin": float(args.min_commit_margin),
            "min_strict_association_count": float(args.min_strict_association_count),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "dense_terminal_arbitration_rows.jsonl",
            "summary": "dense_terminal_arbitration_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "dense_terminal_arbitration_rows.jsonl", diagnostic_rows)
    write_json(out_root / "dense_terminal_arbitration_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose terminal arbitration for fixed dense backend evidence.")
    parser.add_argument("--evidence-rows", required=True)
    parser.add_argument("--recall-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-commit-score", type=float, default=0.35)
    parser.add_argument("--min-commit-margin", type=float, default=0.10)
    parser.add_argument("--min-strict-association-count", type=float, default=1.0)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
