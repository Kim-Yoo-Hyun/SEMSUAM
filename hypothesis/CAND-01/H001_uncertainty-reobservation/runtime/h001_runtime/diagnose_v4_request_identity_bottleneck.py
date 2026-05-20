import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.v4_request_identity_bottleneck_diagnostic.v1"


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


def ratio(num: int, den: int) -> Optional[float]:
    return None if den <= 0 else num / den


def followup_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("followup_candidate_evidence") or [])


def stage2_candidates(row: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not row:
        return []
    return list(row.get("second_stage_candidate_evidence") or [])


def score(candidate: Optional[Dict[str, Any]]) -> float:
    return safe_float(None if candidate is None else candidate.get("S_ext"))


def selected_followup(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    selected_id = row.get("selected_candidate_id")
    return next((cand for cand in followup_candidates(row) if cand.get("candidate_id") == selected_id), None)


def selected_stage2(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not row:
        return None
    selected_id = row.get("selected_candidate_id")
    return next((cand for cand in stage2_candidates(row) if cand.get("candidate_id") == selected_id), None)


def correct_followup(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [cand for cand in followup_candidates(row) if cand.get("candidate_correct") is True]


def correct_stage2(row: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [cand for cand in stage2_candidates(row) if cand.get("candidate_correct") is True]


def is_followup_strong(candidate: Optional[Dict[str, Any]]) -> bool:
    return bool(candidate and candidate.get("followup_strong_depth_evidence") is True)


def is_stage2_strong(candidate: Optional[Dict[str, Any]]) -> bool:
    return bool(candidate and candidate.get("second_stage_strong_depth_evidence") is True)


def is_stage2_own_strong(candidate: Optional[Dict[str, Any]]) -> bool:
    return bool(candidate and candidate.get("own_view_strong_depth_evidence") is True)


def is_positive(candidate: Optional[Dict[str, Any]]) -> bool:
    return bool(candidate and candidate.get("positive_support") is True)


def stage2_index(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in rows}


def commit_metrics(rows: List[Dict[str, Any]], decisions: Dict[str, Optional[str]]) -> Dict[str, Any]:
    committed = []
    success = []
    wrong = []
    no_valid = []
    for row in rows:
        branch_id = str(row.get("external_branch_id"))
        commit_id = decisions.get(branch_id)
        if commit_id is None:
            continue
        committed.append(row)
        candidate = next((cand for cand in followup_candidates(row) if cand.get("candidate_id") == commit_id), None)
        correct = correct_followup(row)
        if not correct:
            no_valid.append(row)
        if candidate and candidate.get("candidate_correct") is True:
            success.append(row)
        else:
            wrong.append(row)
    return {
        "rows": len(rows),
        "commit_rows": len(committed),
        "success_commit_rows": len(success),
        "wrong_goal_commit_rows": len(wrong),
        "no_valid_commit_rows": len(no_valid),
        "commit_rate": ratio(len(committed), len(rows)),
        "success_commit_rate": ratio(len(success), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong), len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong), len(committed)),
        "no_valid_commit_rate": ratio(len(no_valid), len(rows)),
    }


def decide_current_v4(row: Dict[str, Any]) -> Optional[str]:
    if row.get("followup_evidence_v1_commits") is True:
        return str(row.get("selected_candidate_id"))
    return None


def decide_selected_direct(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    selected = selected_followup(row)
    if (
        row.get("followup_evidence_v1_action") == "followup_evidence_v1_request_identity_confirmation"
        and selected
        and is_positive(selected)
        and is_followup_strong(selected)
        and score(selected) >= float(args.min_score)
    ):
        return str(selected.get("candidate_id"))
    return decide_current_v4(row)


def decide_stage2_existing(row: Dict[str, Any], stage2: Optional[Dict[str, Any]]) -> Optional[str]:
    if stage2 and stage2.get("second_stage_identity_v1_commits") is True:
        return str(stage2.get("selected_candidate_id"))
    return decide_current_v4(row)


def decide_category_region(row: Dict[str, Any]) -> Optional[str]:
    if row.get("followup_evidence_v1_action") in {
        "followup_evidence_v1_request_identity_confirmation",
        "followup_evidence_v1_defer",
    }:
        return str(row.get("selected_candidate_id"))
    return decide_current_v4(row)


def decide_oracle_followup(row: Dict[str, Any]) -> Optional[str]:
    correct = correct_followup(row)
    if not correct:
        return None
    return str(max(correct, key=score).get("candidate_id"))


def decide_oracle_stage2_strong(row: Dict[str, Any], stage2: Optional[Dict[str, Any]], args: argparse.Namespace) -> Optional[str]:
    del row
    eligible = [
        cand
        for cand in correct_stage2(stage2)
        if is_positive(cand) and is_stage2_strong(cand) and score(cand) >= float(args.min_score)
    ]
    if not eligible:
        return None
    return str(max(eligible, key=score).get("candidate_id"))


def row_mode(row: Dict[str, Any], stage2: Optional[Dict[str, Any]]) -> str:
    action = str(row.get("followup_evidence_v1_action"))
    source_action = str(row.get("source_external_evidence_v4_action"))
    selected = selected_followup(row)
    selected_stage = selected_stage2(stage2)
    correct = correct_followup(row)
    strong_correct = [cand for cand in correct if is_followup_strong(cand)]
    selected_correct = bool(selected and selected.get("candidate_correct") is True)
    strong_count = sum(1 for cand in followup_candidates(row) if is_followup_strong(cand))
    all_candidates_correct = bool(correct) and len(correct) == len(followup_candidates(row))

    if action == "followup_evidence_v1_defer" and source_action == "external_evidence_v4_request_identity_confirmation":
        if selected_correct and all_candidates_correct:
            return "identity_defer_all_candidates_correct_local_cluster_too_small"
        if selected_correct:
            return "identity_defer_selected_correct_cluster_guard"
        return "identity_defer_selected_wrong_or_unresolved"

    if action != "followup_evidence_v1_request_identity_confirmation":
        return "non_request_row"

    if stage2 and stage2.get("second_stage_identity_v1_commits") is True:
        return "request_identity_resolved_by_stage2_objective"
    if selected_correct:
        if selected_stage and is_stage2_strong(selected_stage) and not is_stage2_own_strong(selected_stage):
            return "selected_correct_needs_better_view_geometry"
        if strong_count > 1:
            return "selected_correct_multi_strong_ambiguous"
        return "selected_correct_overguarded"
    if correct and not strong_correct:
        return "selected_wrong_correct_candidate_without_strong_support"
    if correct:
        return "selected_wrong_correct_candidate_identity_ambiguous"
    return "no_correct_candidate_in_followup_set"


def recommended_route(mode: str) -> str:
    mapping = {
        "request_identity_resolved_by_stage2_objective": "second_stage_identity_objective",
        "selected_correct_needs_better_view_geometry": "viewpoint_geometry_revision",
        "selected_correct_multi_strong_ambiguous": "contrastive_identity_or_duplicate_goal_rule",
        "selected_correct_overguarded": "identity_threshold_revision_with_safety_gate",
        "selected_wrong_correct_candidate_without_strong_support": "broader_retrieval_or_candidate_viewpoint_revision",
        "selected_wrong_correct_candidate_identity_ambiguous": "contrastive_identity_or_retrieval_revision",
        "identity_defer_all_candidates_correct_local_cluster_too_small": "category_goal_region_or_duplicate_goal_contract",
        "identity_defer_selected_correct_cluster_guard": "local_cluster_guard_revision",
        "identity_defer_selected_wrong_or_unresolved": "identity_safety_revision",
    }
    return mapping.get(mode, "no_action")


def build_rows(
    followup_rows: List[Dict[str, Any]],
    stage2_by_branch: Dict[str, Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    diagnostic_rows = []
    for row in followup_rows:
        branch_id = str(row.get("external_branch_id"))
        stage2 = stage2_by_branch.get(branch_id)
        selected = selected_followup(row) or {}
        correct = correct_followup(row)
        stage_correct = correct_stage2(stage2)
        mode = row_mode(row, stage2)
        diagnostic_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "external_branch_id": branch_id,
                "episode_key": row.get("episode_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "property_group": row.get("property_group"),
                "label_case": row.get("label_case"),
                "source_external_evidence_v4_action": row.get("source_external_evidence_v4_action"),
                "followup_action": row.get("followup_evidence_v1_action"),
                "followup_reason": row.get("followup_evidence_v1_reason"),
                "selected_candidate_id": row.get("selected_candidate_id"),
                "selected_candidate_correct": selected.get("candidate_correct"),
                "selected_score": selected.get("S_ext"),
                "selected_positive": is_positive(selected),
                "selected_strong": is_followup_strong(selected),
                "followup_candidate_count": len(followup_candidates(row)),
                "followup_correct_candidate_count": len(correct),
                "followup_strong_candidate_count": sum(1 for cand in followup_candidates(row) if is_followup_strong(cand)),
                "followup_strong_correct_candidate_count": sum(1 for cand in correct if is_followup_strong(cand)),
                "followup_correct_candidate_ids": [cand.get("candidate_id") for cand in correct],
                "stage2_available": stage2 is not None,
                "stage2_action": None if not stage2 else stage2.get("second_stage_identity_v1_action"),
                "stage2_reason": None if not stage2 else stage2.get("second_stage_identity_v1_reason"),
                "stage2_commits": None if not stage2 else stage2.get("second_stage_identity_v1_commits"),
                "stage2_correct_candidate_count": len(stage_correct),
                "stage2_strong_correct_candidate_count": sum(1 for cand in stage_correct if is_stage2_strong(cand)),
                "stage2_own_strong_selected": is_stage2_own_strong(selected_stage2(stage2)),
                "bottleneck_mode": mode,
                "recommended_route": recommended_route(mode),
                "non_gt_decisions": {
                    "current_v4": decide_current_v4(row),
                    "selected_direct_first_stage": decide_selected_direct(row, args),
                    "stage2_objective_v2_existing": decide_stage2_existing(row, stage2),
                    "category_goal_region_commit_selected": decide_category_region(row),
                },
                "oracle_decisions": {
                    "oracle_followup_candidate_set": decide_oracle_followup(row),
                    "oracle_stage2_observed_strong_correct": decide_oracle_stage2_strong(row, stage2, args),
                },
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return diagnostic_rows


def run(args: argparse.Namespace) -> Dict[str, Any]:
    followup_rows = load_jsonl(Path(args.v4_followup_evidence_rows))
    stage2_rows = load_jsonl(Path(args.stage2_evidence_rows)) if args.stage2_evidence_rows else []
    stage2_by_branch = stage2_index(stage2_rows)
    diagnostic_rows = build_rows(followup_rows, stage2_by_branch, args)
    request_rows = [
        row for row in followup_rows
        if row.get("followup_evidence_v1_action") == "followup_evidence_v1_request_identity_confirmation"
    ]
    row_by_branch = {str(row.get("external_branch_id")): row for row in followup_rows}

    decisions = {
        "current_v4": {str(row.get("external_branch_id")): decide_current_v4(row) for row in followup_rows},
        "selected_direct_first_stage": {
            str(row.get("external_branch_id")): decide_selected_direct(row, args) for row in followup_rows
        },
        "stage2_objective_v2_existing": {
            str(row.get("external_branch_id")): decide_stage2_existing(row, stage2_by_branch.get(str(row.get("external_branch_id"))))
            for row in followup_rows
        },
        "category_goal_region_commit_selected": {
            str(row.get("external_branch_id")): decide_category_region(row) for row in followup_rows
        },
        "oracle_followup_candidate_set": {
            str(row.get("external_branch_id")): decide_oracle_followup(row) for row in followup_rows
        },
        "oracle_stage2_observed_strong_correct": {
            str(row.get("external_branch_id")): decide_oracle_stage2_strong(
                row,
                stage2_by_branch.get(str(row.get("external_branch_id"))),
                args,
            )
            for row in followup_rows
        },
    }
    variant_summary = {
        name: {
            **commit_metrics(followup_rows, variant_decisions),
            "uses_gt_for_decision": name.startswith("oracle_"),
        }
        for name, variant_decisions in decisions.items()
    }
    mode_counts = Counter(row["bottleneck_mode"] for row in diagnostic_rows)
    route_counts = Counter(row["recommended_route"] for row in diagnostic_rows)
    request_mode_counts = Counter(
        row["bottleneck_mode"]
        for row in diagnostic_rows
        if row["followup_action"] == "followup_evidence_v1_request_identity_confirmation"
    )
    selected_wrong_request_rows = [
        row for row in request_rows
        if (selected_followup(row) or {}).get("candidate_correct") is False
    ]
    selected_correct_request_rows = [
        row for row in request_rows
        if (selected_followup(row) or {}).get("candidate_correct") is True
    ]
    category_conflict_rows = [
        row_by_branch[branch_id]
        for branch_id, commit_id in decisions["category_goal_region_commit_selected"].items()
        if commit_id is not None
        and (
            next(
                (
                    cand for cand in followup_candidates(row_by_branch[branch_id])
                    if cand.get("candidate_id") == commit_id
                ),
                {},
            ).get("candidate_correct") is False
        )
    ]

    out_root = Path(args.out_root)
    write_jsonl(out_root / "v4_request_identity_bottleneck_rows.jsonl", diagnostic_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "v4_followup_evidence_rows": str(args.v4_followup_evidence_rows),
        "stage2_evidence_rows": args.stage2_evidence_rows,
        "out_root": str(out_root),
        "rows": len(followup_rows),
        "request_identity_rows": len(request_rows),
        "request_identity_selected_correct_rows": len(selected_correct_request_rows),
        "request_identity_selected_wrong_rows": len(selected_wrong_request_rows),
        "mode_counts": dict(sorted(mode_counts.items())),
        "request_identity_mode_counts": dict(sorted(request_mode_counts.items())),
        "recommended_route_counts": dict(sorted(route_counts.items())),
        "variant_summary": variant_summary,
        "category_goal_region_conflicts_with_current_gt_label_rows": len(category_conflict_rows),
        "interpretation": {
            "first_eval_rerun_blocked": True,
            "policy_scale_comparison_blocked": True,
            "stage2_identity_objective_recovers_nonzero_safe_utility": (
                variant_summary["stage2_objective_v2_existing"]["success_commit_rows"] > 0
                and variant_summary["stage2_objective_v2_existing"]["wrong_goal_commit_rows"] == 0
            ),
            "stage2_identity_objective_solves_all_requests": False,
            "direct_selected_commit_is_unsafe": variant_summary["selected_direct_first_stage"]["wrong_goal_commit_rows"] > 0,
            "category_goal_region_requires_evaluation_contract_change": len(category_conflict_rows) > 0,
            "broader_retrieval_or_viewpoint_revision_needed": any(
                row["recommended_route"] == "broader_retrieval_or_candidate_viewpoint_revision"
                for row in diagnostic_rows
            ),
        },
        "recommendation": {
            "next": "integrate_or_replay_v4_with_second_stage_identity_objective_v2_as_a_fixed_terminal_diagnostic",
            "why": (
                "existing second-stage evidence recovers safe utility for selected-correct request rows, "
                "while selected-wrong plant rows need broader retrieval/viewpoint revision before direct commits"
            ),
            "do_not_rerun_first_eval_yet": True,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "v4_request_identity_bottleneck_rows.jsonl",
            "summary": "v4_request_identity_bottleneck_summary.json",
        },
    }
    write_json(out_root / "v4_request_identity_bottleneck_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose V4 request-identity bottlenecks before first_eval rerun.")
    parser.add_argument("--v4-followup-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--stage2-evidence-rows", default=None)
    parser.add_argument("--min-score", type=float, default=0.35)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
