import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.local_context_arbitration_design.v1"


Decision = Tuple[Optional[str], str, Dict[str, Any], bool]


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
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def role_family(candidate: Dict[str, Any]) -> str:
    roles = [str(role) for role in candidate.get("second_stage_roles") or []]
    if any(role.startswith("semantic_neighbor_") for role in roles):
        return "semantic_neighbor"
    if any(role.startswith("local_context_") for role in roles):
        return "local_context"
    if any(role.startswith("selected_") for role in roles):
        return "selected"
    if any(role.startswith("rival_") for role in roles):
        return "rival"
    return "context"


def candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("second_stage_candidate_evidence") or [])


def candidate_id(candidate: Dict[str, Any]) -> str:
    return str(candidate.get("candidate_id"))


def selected_candidate(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    selected_id = str(row.get("source_selected_candidate_id") or row.get("selected_candidate_id"))
    return next((candidate for candidate in candidates(row) if candidate_id(candidate) == selected_id), None)


def strong_candidate(candidate: Dict[str, Any], min_score: float) -> bool:
    return (
        candidate.get("positive_support") is True
        and candidate.get("second_stage_strong_depth_evidence") is True
        and candidate.get("own_view_strong_depth_evidence") is True
        and candidate.get("visit_position_only_evidence") is not True
        and safe_float(candidate.get("S_ext")) >= min_score
    )


def score(candidate: Dict[str, Any]) -> float:
    return safe_float(candidate.get("S_ext"))


def own_strict(candidate: Optional[Dict[str, Any]]) -> float:
    if candidate is None:
        return 0.0
    return safe_float(candidate.get("own_view_strict_association_count"))


def own_mask(candidate: Optional[Dict[str, Any]]) -> float:
    if candidate is None:
        return 0.0
    return safe_float(candidate.get("own_view_mask_hit_count"))


def own_visible(candidate: Optional[Dict[str, Any]]) -> float:
    if candidate is None:
        return 0.0
    return safe_float(candidate.get("own_view_visible_count"))


def tied_strong_candidates(row: Dict[str, Any], args: argparse.Namespace) -> List[Dict[str, Any]]:
    strong = [
        candidate
        for candidate in candidates(row)
        if strong_candidate(candidate, float(args.min_identity_score))
    ]
    if not strong:
        return []
    best_score = max(score(candidate) for candidate in strong)
    return [
        candidate
        for candidate in strong
        if best_score - score(candidate) <= float(args.max_strong_tie_score_gap)
    ]


def candidate_brief(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "role_family": role_family(candidate),
        "identity_role": candidate.get("identity_role"),
        "second_stage_roles": candidate.get("second_stage_roles"),
        "S_ext": candidate.get("S_ext"),
        "S_sem": candidate.get("S_sem"),
        "own_view_strict_association_count": candidate.get("own_view_strict_association_count"),
        "own_view_mask_hit_count": candidate.get("own_view_mask_hit_count"),
        "own_view_visible_count": candidate.get("own_view_visible_count"),
        "own_view_strong_depth_evidence": candidate.get("own_view_strong_depth_evidence"),
        "second_stage_strong_depth_evidence": candidate.get("second_stage_strong_depth_evidence"),
        "strict_association_count": candidate.get("strict_association_count"),
        "mask_hit_count": candidate.get("mask_hit_count"),
        "detector_score_max": candidate.get("detector_score_max"),
    }


def current_v3_decision(row: Dict[str, Any], args: argparse.Namespace) -> Decision:
    del args
    if row.get("second_stage_identity_v1_commits") is True:
        return (
            row.get("committed_candidate_id"),
            str(row.get("second_stage_identity_v1_reason")),
            {"source_action": row.get("second_stage_identity_v1_action")},
            False,
        )
    return None, str(row.get("second_stage_identity_v1_reason")), {"source_action": row.get("second_stage_identity_v1_action")}, False


def oracle_best_correct_decision(row: Dict[str, Any], args: argparse.Namespace) -> Decision:
    correct = [
        candidate
        for candidate in candidates(row)
        if candidate.get("candidate_correct") is True
        and strong_candidate(candidate, float(args.min_identity_score))
    ]
    if not correct:
        return None, "oracle_no_strong_correct_candidate", {"eligible_correct_count": 0}, True
    winner = max(
        correct,
        key=lambda candidate: (
            own_strict(candidate),
            own_mask(candidate),
            own_visible(candidate),
            score(candidate),
        ),
    )
    return (
        candidate_id(winner),
        "oracle_best_correct_strong_own_view",
        {"eligible_correct_count": len(correct), "winner": candidate_brief(winner)},
        True,
    )


def selected_direct_decision(row: Dict[str, Any], args: argparse.Namespace) -> Decision:
    selected = selected_candidate(row)
    if selected is None:
        return None, "selected_missing", {}, False
    guard = {"selected": candidate_brief(selected)}
    if not strong_candidate(selected, float(args.min_identity_score)):
        return None, "selected_not_strong", guard, False
    return candidate_id(selected), "selected_direct_strong_own_view", guard, False


def local_context_unique_own_view_advantage(row: Dict[str, Any], args: argparse.Namespace) -> Decision:
    selected = selected_candidate(row)
    tied = tied_strong_candidates(row, args)
    local_contexts = [candidate for candidate in tied if role_family(candidate) == "local_context"]
    if not local_contexts:
        return None, "no_local_context_in_strong_tie", {"tied_candidates": [candidate_brief(candidate) for candidate in tied]}, False

    ranked = sorted(
        local_contexts,
        key=lambda candidate: (
            own_strict(candidate),
            own_mask(candidate),
            own_visible(candidate),
            score(candidate),
        ),
        reverse=True,
    )
    winner = ranked[0]
    other_local = ranked[1:]
    nonlocal_tied = [candidate for candidate in tied if role_family(candidate) != "local_context"]
    best_other_local = max(other_local, key=lambda candidate: (own_strict(candidate), own_mask(candidate)), default=None)
    best_nonlocal = max(nonlocal_tied, key=lambda candidate: (own_strict(candidate), own_mask(candidate)), default=None)
    strict_advantage_vs_selected = own_strict(winner) - own_strict(selected)
    mask_advantage_vs_selected = own_mask(winner) - own_mask(selected)
    visible_advantage_vs_selected = own_visible(winner) - own_visible(selected)
    strict_advantage_vs_other_local = own_strict(winner) - own_strict(best_other_local)
    mask_advantage_vs_other_local = own_mask(winner) - own_mask(best_other_local)
    strict_advantage_vs_nonlocal = own_strict(winner) - own_strict(best_nonlocal)
    mask_advantage_vs_nonlocal = own_mask(winner) - own_mask(best_nonlocal)
    guard = {
        "winner": candidate_brief(winner),
        "selected": None if selected is None else candidate_brief(selected),
        "best_other_local": None if best_other_local is None else candidate_brief(best_other_local),
        "best_nonlocal_tied": None if best_nonlocal is None else candidate_brief(best_nonlocal),
        "tied_candidate_count": len(tied),
        "local_context_candidate_count": len(local_contexts),
        "strict_advantage_vs_selected": strict_advantage_vs_selected,
        "mask_advantage_vs_selected": mask_advantage_vs_selected,
        "visible_advantage_vs_selected": visible_advantage_vs_selected,
        "strict_advantage_vs_other_local": strict_advantage_vs_other_local,
        "mask_advantage_vs_other_local": mask_advantage_vs_other_local,
        "strict_advantage_vs_nonlocal": strict_advantage_vs_nonlocal,
        "mask_advantage_vs_nonlocal": mask_advantage_vs_nonlocal,
        "thresholds": {
            "min_local_own_strict_count": float(args.min_local_own_strict_count),
            "min_local_own_mask_count": float(args.min_local_own_mask_count),
            "min_local_own_visible_count": float(args.min_local_own_visible_count),
            "min_local_strict_advantage_vs_selected": float(args.min_local_strict_advantage_vs_selected),
            "min_local_mask_advantage_vs_selected": float(args.min_local_mask_advantage_vs_selected),
            "min_local_visible_advantage_vs_selected": float(args.min_local_visible_advantage_vs_selected),
            "min_local_strict_advantage_vs_other_local": float(args.min_local_strict_advantage_vs_other_local),
            "min_local_mask_advantage_vs_other_local": float(args.min_local_mask_advantage_vs_other_local),
            "min_local_strict_advantage_vs_nonlocal": float(args.min_local_strict_advantage_vs_nonlocal),
            "min_local_mask_advantage_vs_nonlocal": float(args.min_local_mask_advantage_vs_nonlocal),
        },
        "uses_gt_for_action": False,
    }
    checks = {
        "local_own_strict_count": own_strict(winner) >= float(args.min_local_own_strict_count),
        "local_own_mask_count": own_mask(winner) >= float(args.min_local_own_mask_count),
        "local_own_visible_count": own_visible(winner) >= float(args.min_local_own_visible_count),
        "strict_advantage_vs_selected": (
            selected is not None
            and strict_advantage_vs_selected >= float(args.min_local_strict_advantage_vs_selected)
        ),
        "mask_advantage_vs_selected": (
            selected is not None
            and mask_advantage_vs_selected >= float(args.min_local_mask_advantage_vs_selected)
        ),
        "visible_advantage_vs_selected": (
            selected is not None
            and visible_advantage_vs_selected >= float(args.min_local_visible_advantage_vs_selected)
        ),
        "strict_advantage_vs_other_local": (
            best_other_local is None
            or strict_advantage_vs_other_local >= float(args.min_local_strict_advantage_vs_other_local)
        ),
        "mask_advantage_vs_other_local": (
            best_other_local is None
            or mask_advantage_vs_other_local >= float(args.min_local_mask_advantage_vs_other_local)
        ),
        "strict_advantage_vs_nonlocal": (
            best_nonlocal is None
            or strict_advantage_vs_nonlocal >= float(args.min_local_strict_advantage_vs_nonlocal)
        ),
        "mask_advantage_vs_nonlocal": (
            best_nonlocal is None
            or mask_advantage_vs_nonlocal >= float(args.min_local_mask_advantage_vs_nonlocal)
        ),
    }
    guard["checks"] = checks
    if not all(checks.values()):
        failed = [name for name, passed in checks.items() if not passed]
        guard["failed_checks"] = failed
        return None, "local_context_advantage_gate_failed", guard, False
    return candidate_id(winner), "commit_local_context_unique_own_view_advantage", guard, False


def evaluate_variant(
    rows: List[Dict[str, Any]],
    variant: str,
    decide: Callable[[Dict[str, Any], argparse.Namespace], Decision],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    details: List[Dict[str, Any]] = []
    commit_count = 0
    success_count = 0
    wrong_count = 0
    no_valid_count = 0
    action_reasons: Counter[str] = Counter()
    for row in rows:
        commit_id, reason, guard, uses_gt_for_action = decide(row, args)
        candidate_rows = candidates(row)
        committed = commit_id is not None
        committed_candidate = next((candidate for candidate in candidate_rows if candidate_id(candidate) == str(commit_id)), None)
        contains_correct = any(candidate.get("candidate_correct") is True for candidate in candidate_rows)
        success = bool(committed_candidate and committed_candidate.get("candidate_correct") is True)
        wrong = bool(committed and not success)
        no_valid = bool(committed and not contains_correct)
        commit_count += int(committed)
        success_count += int(success)
        wrong_count += int(wrong)
        no_valid_count += int(no_valid)
        action_reasons[reason] += 1
        details.append(
            {
                "schema_version": SCHEMA_VERSION,
                "variant": variant,
                "external_branch_id": row.get("external_branch_id"),
                "episode_key": row.get("episode_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "source_selected_candidate_id": row.get("source_selected_candidate_id"),
                "source_selected_candidate_correct": row.get("source_selected_candidate_correct"),
                "commit_candidate_id": commit_id,
                "commit_candidate_correct": None if committed_candidate is None else committed_candidate.get("candidate_correct"),
                "commit": committed,
                "success_commit": success,
                "wrong_goal_commit": wrong,
                "no_valid_commit": no_valid,
                "reason": reason,
                "guard": guard,
                "uses_gt_for_action": uses_gt_for_action,
                "uses_gt_for_analysis": True,
            }
        )
    return {
        "variant": variant,
        "rows": len(rows),
        "commit_rows": commit_count,
        "success_commit_rows": success_count,
        "wrong_goal_commit_rows": wrong_count,
        "no_valid_commit_rows": no_valid_count,
        "commit_rate": ratio(commit_count, len(rows)),
        "success_commit_rate": ratio(success_count, len(rows)),
        "wrong_goal_commit_rate": ratio(wrong_count, len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(wrong_count, commit_count),
        "no_valid_commit_rate": ratio(no_valid_count, len(rows)),
        "reason_counts": dict(sorted(action_reasons.items())),
        "uses_gt_for_action": variant.startswith("oracle_"),
        "uses_gt_for_analysis": True,
        "row_details": details,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    rows = load_jsonl(Path(args.second_stage_evidence_rows))
    variants = [
        ("current_v3", current_v3_decision),
        ("selected_direct_strong_own_view", selected_direct_decision),
        ("local_context_unique_own_view_advantage", local_context_unique_own_view_advantage),
        ("oracle_best_correct", oracle_best_correct_decision),
    ]
    evaluations = {
        name: evaluate_variant(rows, name, decision_fn, args)
        for name, decision_fn in variants
    }
    all_details = [
        detail
        for evaluation in evaluations.values()
        for detail in evaluation["row_details"]
    ]
    for evaluation in evaluations.values():
        evaluation.pop("row_details", None)

    proposed = evaluations["local_context_unique_own_view_advantage"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "second_stage_evidence_rows": str(args.second_stage_evidence_rows),
        "out_root": str(out_root),
        "rows": len(rows),
        "evaluations": evaluations,
        "proposed_rule": {
            "name": "local_context_unique_own_view_advantage",
            "action_reason": "commit_local_context_unique_own_view_advantage",
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
            "recommendation": (
                "Promote to a diagnostic objective only after broader category/scene validation; "
                "current design evidence is limited to detector-saturated held-out sofa local-rival rows."
            ),
            "supported_on_current_rows": bool(
                proposed["commit_rows"] == len(rows)
                and proposed["success_commit_rows"] == len(rows)
                and proposed["wrong_goal_commit_rows"] == 0
                and proposed["no_valid_commit_rows"] == 0
            ),
        },
        "design_interpretation": {
            "fact": (
                "On these rows, detector scores saturate across selected, rival, and local-context candidates."
            ),
            "paper_claim_status": "not_a_paper_claim",
            "agent_inference": (
                "A local-context candidate can be considered only when its own-view evidence is uniquely "
                "stronger than the selected candidate, other local contexts, and non-local tied candidates."
            ),
            "next_step": (
                "Implement as an objective-version diagnostic replay only if the rule remains non-GT and "
                "is checked on at least this held-out split before first_eval or policy-scale reruns."
            ),
        },
        "thresholds": {
            "min_identity_score": float(args.min_identity_score),
            "max_strong_tie_score_gap": float(args.max_strong_tie_score_gap),
            "min_local_own_strict_count": float(args.min_local_own_strict_count),
            "min_local_own_mask_count": float(args.min_local_own_mask_count),
            "min_local_own_visible_count": float(args.min_local_own_visible_count),
            "min_local_strict_advantage_vs_selected": float(args.min_local_strict_advantage_vs_selected),
            "min_local_mask_advantage_vs_selected": float(args.min_local_mask_advantage_vs_selected),
            "min_local_visible_advantage_vs_selected": float(args.min_local_visible_advantage_vs_selected),
            "min_local_strict_advantage_vs_other_local": float(args.min_local_strict_advantage_vs_other_local),
            "min_local_mask_advantage_vs_other_local": float(args.min_local_mask_advantage_vs_other_local),
            "min_local_strict_advantage_vs_nonlocal": float(args.min_local_strict_advantage_vs_nonlocal),
            "min_local_mask_advantage_vs_nonlocal": float(args.min_local_mask_advantage_vs_nonlocal),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "local_context_arbitration_design_rows.jsonl",
            "summary": "local_context_arbitration_design_summary.json",
        },
    }
    write_jsonl(out_root / "local_context_arbitration_design_rows.jsonl", all_details)
    write_json(out_root / "local_context_arbitration_design_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design local-context arbitration for detector-saturated identity rows.")
    parser.add_argument("--second-stage-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-identity-score", type=float, default=0.35)
    parser.add_argument("--max-strong-tie-score-gap", type=float, default=0.02)
    parser.add_argument("--min-local-own-strict-count", type=float, default=5.0)
    parser.add_argument("--min-local-own-mask-count", type=float, default=8.0)
    parser.add_argument("--min-local-own-visible-count", type=float, default=10.0)
    parser.add_argument("--min-local-strict-advantage-vs-selected", type=float, default=3.0)
    parser.add_argument("--min-local-mask-advantage-vs-selected", type=float, default=6.0)
    parser.add_argument("--min-local-visible-advantage-vs-selected", type=float, default=8.0)
    parser.add_argument("--min-local-strict-advantage-vs-other-local", type=float, default=3.0)
    parser.add_argument("--min-local-mask-advantage-vs-other-local", type=float, default=6.0)
    parser.add_argument("--min-local-strict-advantage-vs-nonlocal", type=float, default=2.0)
    parser.add_argument("--min-local-mask-advantage-vs-nonlocal", type=float, default=4.0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
