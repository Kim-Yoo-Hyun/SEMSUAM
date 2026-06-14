import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.discriminative_rival_view_failure_diagnostic.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def classify(row: Dict[str, Any], cross_leak_threshold: float, near_tie_margin: float) -> List[str]:
    tags: List[str] = []
    label_case = str(row.get("label_case"))
    action = str(row.get("discriminative_action"))
    focus_score = float(row.get("focus_identity_score") or 0.0)
    rival_score = float(row.get("rival_identity_score") or 0.0)
    focus_cross = float(row.get("focus_cross_leak_score") or 0.0)
    rival_cross = float(row.get("rival_cross_leak_score") or 0.0)
    focus_own_assoc = int(row.get("focus_own_strict_association_count") or 0)
    rival_own_assoc = int(row.get("rival_own_strict_association_count") or 0)
    focus_common_assoc = int(row.get("focus_common_strict_association_count") or 0)
    rival_common_assoc = int(row.get("rival_common_strict_association_count") or 0)

    if label_case == "rival_only_correct" and action == "discriminative_support_focus":
        tags.append("rival_only_correct_wrong_focus_preferred")
    if label_case == "rival_only_correct" and action == "discriminative_ambiguous_defer":
        tags.append("rival_only_correct_deferred_by_margin")
    if label_case == "rival_only_correct" and rival_own_assoc <= 2:
        tags.append("rival_correct_own_view_evidence_weak")
    if label_case == "rival_only_correct" and focus_score >= rival_score:
        tags.append("focus_prior_survives_rival_correct_evidence")

    if label_case == "neither_correct" and action in {"discriminative_support_focus", "discriminative_support_rival"}:
        tags.append("no_valid_goal_pair_but_disambiguated")
    if label_case == "both_correct" and action in {"discriminative_support_focus", "discriminative_support_rival"}:
        tags.append("both_correct_goal_region_or_duplicate_preferred")

    if focus_cross >= cross_leak_threshold and rival_cross >= cross_leak_threshold:
        tags.append("symmetric_cross_view_leak")
    elif focus_cross >= cross_leak_threshold:
        tags.append("focus_visible_from_rival_view")
    elif rival_cross >= cross_leak_threshold:
        tags.append("rival_visible_from_focus_view")

    if focus_common_assoc > 0 and rival_common_assoc > 0:
        tags.append("common_view_supports_both_candidates")
    if abs(focus_score - rival_score) < near_tie_margin and (focus_score > 0.0 or rival_score > 0.0):
        tags.append("identity_score_near_tie")

    if not tags:
        tags.append("other")
    return tags


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    rows = load_jsonl(Path(args.evidence_rows))
    diagnostic_rows: List[Dict[str, Any]] = []
    tag_counts: Counter[str] = Counter()
    for row in rows:
        tags = classify(row, float(args.cross_leak_threshold), float(args.near_tie_margin))
        tag_counts.update(tags)
        diagnostic_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "rival_candidate_id": row.get("rival_candidate_id"),
                "label_case": row.get("label_case"),
                "discriminative_action": row.get("discriminative_action"),
                "preferred_role": row.get("preferred_role"),
                "preferred_candidate_correct": row.get("preferred_candidate_correct"),
                "focus_identity_score": row.get("focus_identity_score"),
                "rival_identity_score": row.get("rival_identity_score"),
                "focus_cross_leak_score": row.get("focus_cross_leak_score"),
                "rival_cross_leak_score": row.get("rival_cross_leak_score"),
                "focus_own_strict_association_count": row.get("focus_own_strict_association_count"),
                "rival_own_strict_association_count": row.get("rival_own_strict_association_count"),
                "focus_common_strict_association_count": row.get("focus_common_strict_association_count"),
                "rival_common_strict_association_count": row.get("rival_common_strict_association_count"),
                "failure_tags": tags,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )

    label_counts = Counter(str(row.get("label_case")) for row in rows)
    action_counts = Counter(str(row.get("discriminative_action")) for row in rows)
    single_correct = [row for row in rows if row.get("label_case") in {"focus_only_correct", "rival_only_correct"}]
    wrong_preferred = [
        row
        for row in single_correct
        if row.get("preferred_candidate_correct") is False
    ]
    correct_preferred = [
        row
        for row in single_correct
        if row.get("preferred_candidate_correct") is True
    ]
    no_valid_disambiguated = [
        row
        for row in rows
        if row.get("label_case") == "neither_correct"
        and row.get("discriminative_action") in {"discriminative_support_focus", "discriminative_support_rival"}
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "evidence_rows": str(args.evidence_rows),
        "diagnostic_rows": len(diagnostic_rows),
        "label_case_counts": dict(sorted(label_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "failure_tag_counts": dict(sorted(tag_counts.items())),
        "single_correct_rows": len(single_correct),
        "single_correct_preferred_rate": ratio(len(correct_preferred), len(single_correct)),
        "single_correct_wrong_preference_rate": ratio(len(wrong_preferred), len(single_correct)),
        "no_valid_goal_pair_disambiguated_rows": len(no_valid_disambiguated),
        "gate": {
            "threshold_tuning_allowed": False,
            "objective_revision_allowed": False,
            "planner_or_branch_revision_required": True,
            "fresh_validation_allowed": False,
        },
        "interpretation": {
            "facts": [
                "The detector/SAM2 substrate is available for the discriminative rival view branch.",
                "The first pair-role evidence analyzer fails its diagnostic gate.",
                "All single-correct cases are rival_only_correct, and the current evidence rule never prefers the correct rival.",
            ],
            "agent_inference": [
                "The current contrastive views are not enough to turn same-category semantic uncertainty into a safe terminal utility.",
                "The dominant issue is not missing detector evidence alone; it is candidate-pair validity and cross-view leakage.",
                "A rule threshold change would risk committing invalid focus candidates, so failure taxonomy should guide either a planner revision or switching to expanded retrieval.",
            ],
            "user_decision_needed": [
                "Choose whether to revise discriminative view design first or move to the next router branch, request_expanded_retrieval.",
            ],
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "discriminative_rival_view_failure_rows.jsonl",
            "summary": "discriminative_rival_view_failure_summary.json",
        },
    }
    write_jsonl(out_root / "discriminative_rival_view_failure_rows.jsonl", diagnostic_rows)
    write_json(out_root / "discriminative_rival_view_failure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose failed discriminative rival view evidence rows.")
    parser.add_argument("--evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--cross-leak-threshold", type=float, default=0.45)
    parser.add_argument("--near-tie-margin", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
