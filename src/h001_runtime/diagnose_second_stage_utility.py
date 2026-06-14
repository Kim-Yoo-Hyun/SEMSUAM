import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


SCHEMA_VERSION = "h001.second_stage_utility_diagnostic.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def ratio(num: int, den: int) -> Optional[float]:
    if den <= 0:
        return None
    return num / den


def candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("second_stage_candidate_evidence") or [])


def selected_candidate(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    selected_id = row.get("selected_candidate_id")
    return next((cand for cand in candidates(row) if cand.get("candidate_id") == selected_id), None)


def rival_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [cand for cand in candidates(row) if cand.get("identity_role") == "rival"]


def correct_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [cand for cand in candidates(row) if cand.get("candidate_correct") is True]


def is_positive(cand: Optional[Dict[str, Any]]) -> bool:
    return bool(cand and cand.get("positive_support") is True)


def is_strong(cand: Optional[Dict[str, Any]]) -> bool:
    return bool(cand and cand.get("second_stage_strong_depth_evidence") is True)


def is_own_strong(cand: Optional[Dict[str, Any]]) -> bool:
    return bool(cand and cand.get("own_view_strong_depth_evidence") is True)


def is_visit_only(cand: Optional[Dict[str, Any]]) -> bool:
    return bool(cand and cand.get("visit_position_only_evidence") is True)


def score(cand: Optional[Dict[str, Any]]) -> float:
    return safe_float(None if cand is None else cand.get("S_ext"))


def candidate_commit_metrics(rows: List[Dict[str, Any]], decisions: Dict[str, Optional[str]]) -> Dict[str, Any]:
    commit_rows = []
    success = []
    wrong = []
    no_valid = []
    visit_only = []
    for row in rows:
        branch_id = str(row.get("external_branch_id"))
        commit_id = decisions.get(branch_id)
        if commit_id is None:
            continue
        commit_rows.append(row)
        cand = next((item for item in candidates(row) if item.get("candidate_id") == commit_id), None)
        corrects = correct_candidates(row)
        if not corrects:
            no_valid.append(row)
        if cand and cand.get("candidate_correct") is True:
            success.append(row)
        else:
            wrong.append(row)
        if is_visit_only(cand):
            visit_only.append(row)
    return {
        "rows": len(rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success),
        "wrong_goal_commit_rows": len(wrong),
        "no_valid_commit_rows": len(no_valid),
        "visit_position_only_commit_rows": len(visit_only),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "success_commit_rate": ratio(len(success), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong), len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong), len(commit_rows)),
    }


def decide_selected_strong_ignore_rival(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    selected = selected_candidate(row)
    if (
        selected
        and is_positive(selected)
        and is_strong(selected)
        and not is_visit_only(selected)
        and score(selected) >= args.min_identity_score
    ):
        return str(selected.get("candidate_id"))
    return None


def decide_selected_margin_ignore_weak_rival(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    selected = selected_candidate(row)
    rivals = rival_candidates(row)
    rival_strong = any(is_strong(cand) for cand in rivals)
    margin = safe_float(row.get("score_margin"))
    if (
        selected
        and is_positive(selected)
        and is_strong(selected)
        and is_own_strong(selected)
        and not is_visit_only(selected)
        and score(selected) >= args.min_identity_score
        and margin >= args.min_identity_margin
        and not rival_strong
    ):
        return str(selected.get("candidate_id"))
    return None


def decide_selected_no_rival_positive(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    selected = selected_candidate(row)
    rivals = rival_candidates(row)
    rival_positive = any(is_positive(cand) or is_strong(cand) for cand in rivals)
    margin = safe_float(row.get("score_margin"))
    if (
        selected
        and is_positive(selected)
        and is_strong(selected)
        and is_own_strong(selected)
        and not is_visit_only(selected)
        and score(selected) >= args.min_identity_score
        and margin >= args.min_identity_margin
        and not rival_positive
    ):
        return str(selected.get("candidate_id"))
    return None


def decide_best_strong_score(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    eligible = [
        cand
        for cand in candidates(row)
        if is_positive(cand)
        and is_strong(cand)
        and not is_visit_only(cand)
        and score(cand) >= args.min_identity_score
    ]
    if not eligible:
        return None
    best = max(
        eligible,
        key=lambda cand: (
            score(cand),
            safe_float(cand.get("strict_association_count")),
            safe_float(cand.get("mask_hit_count")),
        ),
    )
    return str(best.get("candidate_id"))


def decide_oracle_observed_correct(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    eligible = [
        cand
        for cand in correct_candidates(row)
        if is_positive(cand) and is_strong(cand) and score(cand) >= args.min_identity_score
    ]
    if not eligible:
        return None
    return str(max(eligible, key=score).get("candidate_id"))


def decide_oracle_candidate_set_correct(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    del args
    correct = correct_candidates(row)
    if not correct:
        return None
    return str(max(correct, key=score).get("candidate_id"))


def failure_mode(row: Dict[str, Any], args: argparse.Namespace) -> str:
    selected = selected_candidate(row)
    correct = correct_candidates(row)
    correct_positive = [cand for cand in correct if is_positive(cand) or is_strong(cand)]
    correct_selected_or_rival = [
        cand for cand in correct if cand.get("identity_role") in {"selected", "rival"}
    ]
    weak_rivals = [cand for cand in rival_candidates(row) if is_positive(cand) and not is_strong(cand)]
    strong_rivals = [cand for cand in rival_candidates(row) if is_strong(cand)]
    margin = safe_float(row.get("score_margin"))

    if not correct:
        return "no_valid_candidate_in_second_stage_set"
    if selected and selected.get("candidate_correct") is True:
        if not is_own_strong(selected):
            return "selected_correct_but_view_geometry_insufficient"
        if weak_rivals and not strong_rivals and margin >= args.min_identity_margin:
            return "selected_correct_but_weak_rival_overguarded"
        return "selected_correct_but_identity_guard_unresolved"
    if not correct_selected_or_rival and not correct_positive:
        return "correct_candidate_requires_candidate_set_expansion"
    if not correct_positive:
        return "correct_candidate_observed_without_detector_support"
    return "selected_wrong_identity_ambiguous"


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.stage2_evidence_rows))
    out_root = Path(args.out_root)
    variants: Dict[str, Tuple[bool, Dict[str, Optional[str]]]] = {
        "current_v3_second_stage": (
            False,
            {
                str(row.get("external_branch_id")): row.get("selected_candidate_id")
                if row.get("second_stage_identity_v1_commits") is True
                else None
                for row in rows
            },
        ),
        "selected_strong_ignore_rival": (
            False,
            {str(row.get("external_branch_id")): decide_selected_strong_ignore_rival(row, args) for row in rows},
        ),
        "selected_margin_ignore_weak_rival": (
            False,
            {str(row.get("external_branch_id")): decide_selected_margin_ignore_weak_rival(row, args) for row in rows},
        ),
        "selected_no_rival_positive": (
            False,
            {str(row.get("external_branch_id")): decide_selected_no_rival_positive(row, args) for row in rows},
        ),
        "best_strong_score": (
            False,
            {str(row.get("external_branch_id")): decide_best_strong_score(row, args) for row in rows},
        ),
        "oracle_observed_correct_upper_bound": (
            True,
            {str(row.get("external_branch_id")): decide_oracle_observed_correct(row, args) for row in rows},
        ),
        "oracle_candidate_set_upper_bound": (
            True,
            {str(row.get("external_branch_id")): decide_oracle_candidate_set_correct(row, args) for row in rows},
        ),
    }
    variant_summary = {
        name: {
            **candidate_commit_metrics(rows, decisions),
            "uses_gt_for_decision": uses_gt,
        }
        for name, (uses_gt, decisions) in variants.items()
    }
    diagnostic_rows = []
    for row in rows:
        branch_id = str(row.get("external_branch_id"))
        selected = selected_candidate(row) or {}
        correct = correct_candidates(row)
        diagnostic_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "external_branch_id": branch_id,
                "episode_key": row.get("episode_key"),
                "query": row.get("query"),
                "property_group": row.get("property_group"),
                "label_case": row.get("label_case"),
                "selected_candidate_id": row.get("selected_candidate_id"),
                "selected_candidate_correct": row.get("selected_candidate_correct"),
                "score_margin": row.get("score_margin"),
                "current_reason": row.get("second_stage_identity_v1_reason"),
                "failure_mode": failure_mode(row, args),
                "correct_candidate_ids": [cand.get("candidate_id") for cand in correct],
                "correct_selected_or_rival_count": sum(
                    1 for cand in correct if cand.get("identity_role") in {"selected", "rival"}
                ),
                "correct_positive_or_strong_count": sum(1 for cand in correct if is_positive(cand) or is_strong(cand)),
                "selected_positive": is_positive(selected),
                "selected_strong": is_strong(selected),
                "selected_own_strong": is_own_strong(selected),
                "rival_positive_count": sum(1 for cand in rival_candidates(row) if is_positive(cand)),
                "rival_strong_count": sum(1 for cand in rival_candidates(row) if is_strong(cand)),
                "variant_commits": {
                    name: decisions.get(branch_id)
                    for name, (_, decisions) in variants.items()
                    if decisions.get(branch_id) is not None
                },
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    mode_counts = Counter(row["failure_mode"] for row in diagnostic_rows)
    recommendation = {
        "do_not_rerun_first_eval_yet": True,
        "next_probe": "selected_margin_ignore_weak_rival",
        "why": (
            "It recovers the high-margin selected-correct rows while still blocking "
            "the tie/strong-rival rows on this artifact."
        ),
        "required_followup": [
            "validate selected_margin_ignore_weak_rival on held-out fresh rows before policy-scale use",
            "add candidate-set expansion for rows where the correct object is outside selected/rival evidence",
            "keep oracle upper bounds analysis-only because it uses labels",
        ],
    }
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage2_evidence_rows": str(args.stage2_evidence_rows),
        "out_root": str(out_root),
        "rows": len(rows),
        "failure_mode_counts": dict(sorted(mode_counts.items())),
        "variant_summary": variant_summary,
        "recommendation": recommendation,
        "thresholds": {
            "min_identity_score": args.min_identity_score,
            "min_identity_margin": args.min_identity_margin,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "summary": "second_stage_utility_diagnostic_summary.json",
            "rows": "second_stage_utility_diagnostic_rows.jsonl",
        },
    }
    write_json(out_root / "second_stage_utility_diagnostic_summary.json", summary)
    write_jsonl(out_root / "second_stage_utility_diagnostic_rows.jsonl", diagnostic_rows)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose H001 second-stage identity utility recovery options.")
    parser.add_argument("--stage2-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-identity-score", type=float, default=0.35)
    parser.add_argument("--min-identity-margin", type=float, default=0.20)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
