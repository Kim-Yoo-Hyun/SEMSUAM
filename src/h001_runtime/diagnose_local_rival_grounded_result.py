import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.local_rival_grounded_result_diagnostic.v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    return number


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


def candidate_brief(candidate: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "candidate_correct": candidate.get("candidate_correct"),
        "role_family": role_family(candidate),
        "identity_role": candidate.get("identity_role"),
        "second_stage_roles": candidate.get("second_stage_roles"),
        "S_ext": candidate.get("S_ext"),
        "S_sem": candidate.get("S_sem"),
        "own_view_S_ext": candidate.get("own_view_S_ext"),
        "own_view_strict_association_count": candidate.get("own_view_strict_association_count"),
        "own_view_mask_hit_count": candidate.get("own_view_mask_hit_count"),
        "own_view_visible_count": candidate.get("own_view_visible_count"),
        "own_view_strong_depth_evidence": candidate.get("own_view_strong_depth_evidence"),
        "second_stage_strong_depth_evidence": candidate.get("second_stage_strong_depth_evidence"),
        "strict_association_count": candidate.get("strict_association_count"),
        "mask_hit_count": candidate.get("mask_hit_count"),
        "detector_score_max": candidate.get("detector_score_max"),
    }


def best_by_score(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda row: (
            safe_float(row.get("S_ext")) or 0.0,
            safe_float(row.get("own_view_strict_association_count")) or 0.0,
            safe_float(row.get("strict_association_count")) or 0.0,
        ),
    )


def diagnose_row(row: Dict[str, Any], score_tie_gap: float) -> Dict[str, Any]:
    candidates = list(row.get("second_stage_candidate_evidence") or [])
    selected_id = str(row.get("source_selected_candidate_id") or row.get("selected_candidate_id"))
    selected = next((candidate for candidate in candidates if str(candidate.get("candidate_id")) == selected_id), None)
    correct_candidates = [candidate for candidate in candidates if candidate.get("candidate_correct") is True]
    wrong_candidates = [candidate for candidate in candidates if candidate.get("candidate_correct") is False]
    strong_correct = [
        candidate
        for candidate in correct_candidates
        if candidate.get("second_stage_strong_depth_evidence") is True
        or candidate.get("own_view_strong_depth_evidence") is True
    ]
    strong_wrong = [
        candidate
        for candidate in wrong_candidates
        if candidate.get("second_stage_strong_depth_evidence") is True
        or candidate.get("own_view_strong_depth_evidence") is True
    ]
    best_candidate = best_by_score(candidates)
    best_correct = best_by_score(correct_candidates)
    best_wrong = best_by_score(wrong_candidates)
    best_score = safe_float(best_candidate.get("S_ext")) if best_candidate else None
    tied = [
        candidate
        for candidate in candidates
        if best_score is not None and best_score - (safe_float(candidate.get("S_ext")) or 0.0) <= score_tie_gap
    ]
    correct_local_context = [
        candidate
        for candidate in correct_candidates
        if role_family(candidate) == "local_context"
    ]
    correct_semantic_neighbor = [
        candidate
        for candidate in correct_candidates
        if role_family(candidate) == "semantic_neighbor"
    ]
    guard = row.get("second_stage_identity_guard") or {}
    arbitration = guard.get("semantic_prior_strong_tie_arbitration") or {}

    failure_modes: List[str] = []
    if strong_correct:
        failure_modes.append("correct_evidence_recovered")
    if selected is not None and selected.get("candidate_correct") is False and selected.get("second_stage_strong_depth_evidence") is True:
        failure_modes.append("selected_wrong_remains_strong")
    if strong_wrong:
        failure_modes.append("wrong_rivals_remain_strong")
    if len(tied) >= 3:
        failure_modes.append("score_saturation_multiple_strong_candidates")
    if correct_local_context and any(candidate in tied for candidate in correct_local_context):
        failure_modes.append("correct_local_context_tied_but_not_arbitrated")
    if arbitration.get("reason"):
        failure_modes.append(f"semantic_arbitration_{arbitration.get('reason')}")
    if row.get("second_stage_identity_v1_action") == "second_stage_identity_v1_request_further_identity_confirmation":
        failure_modes.append("terminal_objective_remains_defer")

    return {
        "external_branch_id": row.get("external_branch_id"),
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "source_selected_candidate_id": selected_id,
        "source_selected_candidate_correct": row.get("source_selected_candidate_correct"),
        "second_stage_action": row.get("second_stage_identity_v1_action"),
        "second_stage_reason": row.get("second_stage_identity_v1_reason"),
        "best_candidate": None if best_candidate is None else candidate_brief(best_candidate),
        "best_correct_candidate": None if best_correct is None else candidate_brief(best_correct),
        "best_wrong_candidate": None if best_wrong is None else candidate_brief(best_wrong),
        "correct_candidates": [candidate_brief(candidate) for candidate in correct_candidates],
        "strong_correct_candidates": [candidate_brief(candidate) for candidate in strong_correct],
        "strong_wrong_candidates": [candidate_brief(candidate) for candidate in strong_wrong],
        "tied_candidates": [candidate_brief(candidate) for candidate in tied],
        "correct_local_context_candidates": [candidate_brief(candidate) for candidate in correct_local_context],
        "correct_semantic_neighbor_candidates": [candidate_brief(candidate) for candidate in correct_semantic_neighbor],
        "semantic_arbitration_guard": arbitration,
        "failure_modes": failure_modes,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(any(candidate.get("candidate_correct") is not None for candidate in candidates)),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    evidence_rows = load_jsonl(Path(args.second_stage_evidence_rows))
    integrated_summary = load_json(Path(args.integrated_summary))
    diagnostic_rows = [diagnose_row(row, float(args.score_tie_gap)) for row in evidence_rows]
    failure_counts = Counter(mode for row in diagnostic_rows for mode in row["failure_modes"])
    action_counts = Counter(str(row.get("second_stage_action")) for row in diagnostic_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "second_stage_evidence_rows": str(args.second_stage_evidence_rows),
        "integrated_summary": str(args.integrated_summary),
        "out_root": str(out_root),
        "rows": len(diagnostic_rows),
        "action_counts": dict(sorted(action_counts.items())),
        "failure_mode_counts": dict(sorted(failure_counts.items())),
        "integrated_gate": integrated_summary.get("integrated", {}).get("gate"),
        "integrated_interpretation": integrated_summary.get("interpretation"),
        "diagnosis": {
            "detector_substrate_recovered": bool(
                integrated_summary.get("second_stage", {})
                .get("evidence", {})
                .get("gate", {})
                .get("passes_second_stage_identity_detector_substrate_gate_v1")
            ),
            "utility_recovered": bool(integrated_summary.get("interpretation", {}).get("utility_proof_passed")),
            "summary": (
                "Grounded local-rival expansion recovers detector association for correct sofa candidates, "
                "but the terminal objective remains blocked by score saturation and strong wrong rivals."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") for row in diagnostic_rows),
        "output_files": {
            "rows": "local_rival_grounded_diagnostic_rows.jsonl",
            "summary": "local_rival_grounded_diagnostic_summary.json",
        },
    }
    write_jsonl(out_root / "local_rival_grounded_diagnostic_rows.jsonl", diagnostic_rows)
    write_json(out_root / "local_rival_grounded_diagnostic_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose held-out local-rival grounded second-stage result.")
    parser.add_argument("--second-stage-evidence-rows", required=True)
    parser.add_argument("--integrated-summary", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--score-tie-gap", type=float, default=0.02)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
