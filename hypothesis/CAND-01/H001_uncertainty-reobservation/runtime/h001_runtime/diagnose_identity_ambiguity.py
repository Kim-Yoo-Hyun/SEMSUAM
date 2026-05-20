import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.identity_ambiguity_diagnostic.v1"


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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("followup_candidate_evidence") or [])


def correct_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [candidate for candidate in candidates(row) if candidate.get("candidate_correct") is True]


def wrong_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [candidate for candidate in candidates(row) if candidate.get("candidate_correct") is False]


def strong_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [candidate for candidate in candidates(row) if candidate.get("followup_strong_depth_evidence") is True]


def score(candidate: Dict[str, Any]) -> float:
    return safe_float(candidate.get("S_ext"))


def best_by_score(rows: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not rows:
        return None
    return max(
        rows,
        key=lambda candidate: (
            score(candidate),
            safe_float(candidate.get("strict_association_count")),
            safe_float(candidate.get("mask_hit_count")),
        ),
    )


def candidate_ids(rows: List[Dict[str, Any]]) -> List[str]:
    return [str(row.get("candidate_id")) for row in rows if row.get("candidate_id") is not None]


def diagnose_row(row: Dict[str, Any], min_margin: float) -> Dict[str, Any]:
    all_candidates = candidates(row)
    correct = correct_candidates(row)
    wrong = wrong_candidates(row)
    strong = strong_candidates(row)
    strong_correct = [candidate for candidate in correct if candidate.get("followup_strong_depth_evidence") is True]
    strong_wrong = [candidate for candidate in wrong if candidate.get("followup_strong_depth_evidence") is True]
    selected_id = row.get("selected_candidate_id")
    selected = next((candidate for candidate in all_candidates if candidate.get("candidate_id") == selected_id), None)
    best = best_by_score(all_candidates)
    best_correct = best.get("candidate_correct") is True if best else None
    best_correct_candidate = best_by_score(correct)
    best_wrong_candidate = best_by_score(wrong)
    score_gap_correct_minus_wrong = (
        safe_float(best_correct_candidate.get("S_ext")) - safe_float(best_wrong_candidate.get("S_ext"))
        if best_correct_candidate and best_wrong_candidate
        else None
    )

    if not correct:
        failure_mode = "no_correct_candidate_in_followup_set"
    elif selected and selected.get("candidate_correct") is True and strong_wrong:
        failure_mode = "selected_correct_but_supported_wrong_rival"
    elif strong_correct and strong_wrong and (score_gap_correct_minus_wrong is None or score_gap_correct_minus_wrong < min_margin):
        failure_mode = "correct_present_but_not_contrastive_against_wrong_rival"
    elif strong_correct and not strong_wrong:
        failure_mode = "potential_threshold_overconservative"
    else:
        failure_mode = "correct_present_but_evidence_too_weak"

    return {
        "schema_version": SCHEMA_VERSION,
        "external_branch_id": row.get("external_branch_id"),
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "property_group": row.get("property_group"),
        "label_case": row.get("label_case"),
        "followup_action": row.get("followup_evidence_v1_action"),
        "followup_reason": row.get("followup_evidence_v1_reason"),
        "selected_candidate_id": selected_id,
        "selected_candidate_correct": None if selected is None else selected.get("candidate_correct"),
        "candidate_count": len(all_candidates),
        "correct_candidate_count": len(correct),
        "strong_correct_candidate_count": len(strong_correct),
        "strong_wrong_candidate_count": len(strong_wrong),
        "correct_candidate_ids": candidate_ids(correct),
        "strong_correct_candidate_ids": candidate_ids(strong_correct),
        "strong_wrong_candidate_ids": candidate_ids(strong_wrong),
        "best_candidate_id": None if best is None else best.get("candidate_id"),
        "best_candidate_correct": best_correct,
        "best_correct_candidate_id": None if best_correct_candidate is None else best_correct_candidate.get("candidate_id"),
        "best_wrong_candidate_id": None if best_wrong_candidate is None else best_wrong_candidate.get("candidate_id"),
        "score_gap_correct_minus_wrong": score_gap_correct_minus_wrong,
        "failure_mode": failure_mode,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize(rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    failure_counts = Counter(row["failure_mode"] for row in rows)
    action_counts = Counter(str(row.get("followup_action")) for row in rows)
    correct_rows = [row for row in rows if row["correct_candidate_count"] > 0]
    strong_correct_rows = [row for row in rows if row["strong_correct_candidate_count"] > 0]
    best_correct_rows = [row for row in rows if row["best_candidate_correct"] is True]
    recommendation = (
        "broader_retrieval_backend_required_first"
        if failure_counts.get("no_correct_candidate_in_followup_set", 0) == len(rows)
        else "contrastive_identity_objective_or_viewpoint_required_before_first_eval"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "out_root": str(args.out_root),
        "rows": len(rows),
        "action_counts": dict(sorted(action_counts.items())),
        "failure_mode_counts": dict(sorted(failure_counts.items())),
        "rows_with_correct_candidate": len(correct_rows),
        "rows_with_correct_candidate_rate": ratio(len(correct_rows), len(rows)),
        "rows_with_strong_correct_candidate": len(strong_correct_rows),
        "rows_with_strong_correct_candidate_rate": ratio(len(strong_correct_rows), len(rows)),
        "rows_where_best_score_candidate_is_correct": len(best_correct_rows),
        "rows_where_best_score_candidate_is_correct_rate": ratio(len(best_correct_rows), len(rows)),
        "recommendation": recommendation,
        "interpretation": {
            "threshold_only_revision_is_supported": False,
            "first_eval_rerun_blocked": True,
            "policy_scale_comparison_blocked": True,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "identity_ambiguity_rows.jsonl",
            "summary": "identity_ambiguity_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    source_rows = load_jsonl(Path(args.followup_evidence_rows))
    rows = [diagnose_row(row, float(args.min_contrastive_margin)) for row in source_rows]
    out_root = Path(args.out_root)
    write_jsonl(out_root / "identity_ambiguity_rows.jsonl", rows)
    summary = summarize(rows, args)
    write_json(out_root / "identity_ambiguity_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose H001 follow-up identity ambiguity after detector repair.")
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-contrastive-margin", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
