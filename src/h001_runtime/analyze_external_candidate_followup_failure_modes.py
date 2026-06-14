import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "h001.external_candidate_followup_failure_modes.v1"


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


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def candidate_evidence(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = row.get("followup_candidate_evidence") or []
    return [value for value in values if isinstance(value, dict)]


def selected_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    selected_id = row.get("selected_candidate_id")
    for candidate in candidate_evidence(row):
        if candidate.get("candidate_id") == selected_id:
            return candidate
    return {}


def count_candidates(candidates: List[Dict[str, Any]], field: str, value: Any = True) -> int:
    return sum(candidate.get(field) is value for candidate in candidates)


def max_field(candidates: List[Dict[str, Any]], field: str) -> float:
    values = [safe_float(candidate.get(field)) for candidate in candidates]
    return max(values) if values else 0.0


def classify(row: Dict[str, Any]) -> Dict[str, Any]:
    candidates = candidate_evidence(row)
    selected = selected_candidate(row)
    action = str(row.get("followup_evidence_v1_action"))
    reason = str(row.get("followup_evidence_v1_reason"))
    source_action = str(row.get("source_external_evidence_v4_action"))
    commits = row.get("followup_evidence_v1_commits") is True
    wrong_commit = row.get("followup_evidence_v1_wrong_goal_commit") is True
    no_valid_commit = row.get("followup_evidence_v1_no_valid_commit") is True
    success_commit = row.get("followup_evidence_v1_success_commit") is True
    contains_correct = row.get("followup_set_contains_correct") is True
    selected_correct = row.get("selected_candidate_correct")
    selected_strong = selected.get("followup_strong_depth_evidence") is True
    selected_positive = selected.get("positive_support") is True
    strong_count = count_candidates(candidates, "followup_strong_depth_evidence")
    positive_count = count_candidates(candidates, "positive_support")
    correct_count = count_candidates(candidates, "candidate_correct")
    tags: List[str] = []

    if commits and success_commit:
        tags.append("successful_followup_commit")
    if commits and no_valid_commit:
        tags.append("unsafe_no_valid_expanded_retrieval_commit")
    if commits and wrong_commit:
        tags.append("unsafe_wrong_goal_followup_commit")
    if commits and wrong_commit and selected_strong:
        tags.append("strong_depth_evidence_not_instance_safe")
    if commits and wrong_commit and selected_positive:
        tags.append("positive_detector_support_not_instance_safe")
    if commits and wrong_commit and not contains_correct:
        tags.append("expanded_retrieval_set_missing_valid_target")
    if commits and wrong_commit and row.get("property_group") == "large_repeated_furniture":
        tags.append("large_repeated_furniture_instance_confusion")
    if not commits and source_action == "external_evidence_v4_request_identity_confirmation":
        if reason == "defer_identity_ambiguous_rival_supported":
            tags.append("safe_identity_defer_rival_supported")
        elif contains_correct and selected_correct is not True:
            tags.append("identity_defer_correct_exists_but_not_selected")
        else:
            tags.append("identity_confirmation_defer")
    if not commits and source_action == "external_evidence_v4_request_expanded_retrieval":
        if not contains_correct:
            tags.append("safe_expanded_retrieval_defer_no_valid_target")
        elif reason == "defer_expanded_retrieval_without_strong_depth_association":
            tags.append("expanded_retrieval_correct_available_but_weak_depth")
        else:
            tags.append("expanded_retrieval_defer")
    if action == "followup_evidence_v1_request_identity_confirmation":
        tags.append("expanded_retrieval_requests_identity_confirmation")

    if not tags:
        tags.append("uncategorized")

    priority = [
        "unsafe_no_valid_expanded_retrieval_commit",
        "unsafe_wrong_goal_followup_commit",
        "strong_depth_evidence_not_instance_safe",
        "expanded_retrieval_set_missing_valid_target",
        "safe_identity_defer_rival_supported",
        "safe_expanded_retrieval_defer_no_valid_target",
        "expanded_retrieval_correct_available_but_weak_depth",
        "successful_followup_commit",
    ]
    primary = next((tag for tag in priority if tag in tags), tags[0])
    return {
        "failure_tags": tags,
        "primary_failure_mode": primary,
        "selected_positive_support": selected_positive,
        "selected_strong_depth_evidence": selected_strong,
        "selected_strict_association_count": selected.get("strict_association_count"),
        "selected_mask_hit_count": selected.get("mask_hit_count"),
        "selected_visible_count": selected.get("visible_count"),
        "selected_score": safe_float(row.get("selected_score")),
        "selected_margin": safe_float(row.get("score_margin")),
        "positive_candidate_count": positive_count,
        "strong_candidate_count": strong_count,
        "correct_candidate_count": correct_count,
        "max_candidate_score": max_field(candidates, "S_ext"),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.rows))
    out_rows: List[Dict[str, Any]] = []
    primary_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    primary_by_query: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_source_action: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_reason: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_scene: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        labels = classify(row)
        out = {
            "schema_version": SCHEMA_VERSION,
            "external_branch_id": row.get("external_branch_id"),
            "episode_key": row.get("episode_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "property_group": row.get("property_group"),
            "label_case": row.get("label_case"),
            "source_external_evidence_v4_action": row.get("source_external_evidence_v4_action"),
            "source_external_evidence_v4_reason": row.get("source_external_evidence_v4_reason"),
            "followup_evidence_v1_action": row.get("followup_evidence_v1_action"),
            "followup_evidence_v1_reason": row.get("followup_evidence_v1_reason"),
            "followup_set_contains_correct": row.get("followup_set_contains_correct"),
            "selected_candidate_id": row.get("selected_candidate_id"),
            "selected_candidate_correct": row.get("selected_candidate_correct"),
            "followup_evidence_v1_commits": row.get("followup_evidence_v1_commits"),
            "followup_evidence_v1_success_commit": row.get("followup_evidence_v1_success_commit"),
            "followup_evidence_v1_wrong_goal_commit": row.get("followup_evidence_v1_wrong_goal_commit"),
            "followup_evidence_v1_no_valid_commit": row.get("followup_evidence_v1_no_valid_commit"),
            "followup_guard": row.get("followup_guard"),
            "uses_gt_for_action": row.get("uses_gt_for_action"),
            "uses_gt_for_analysis": row.get("uses_gt_for_analysis"),
            **labels,
        }
        out_rows.append(out)
        primary_counts[out["primary_failure_mode"]] += 1
        primary_by_query[str(out.get("query"))][out["primary_failure_mode"]] += 1
        primary_by_label[str(out.get("label_case"))][out["primary_failure_mode"]] += 1
        primary_by_source_action[str(out.get("source_external_evidence_v4_action"))][out["primary_failure_mode"]] += 1
        primary_by_reason[str(out.get("followup_evidence_v1_reason"))][out["primary_failure_mode"]] += 1
        primary_by_scene[str(out.get("scene_id"))][out["primary_failure_mode"]] += 1
        for tag in out["failure_tags"]:
            tag_counts[tag] += 1

    commit_rows = [row for row in out_rows if row.get("followup_evidence_v1_commits") is True]
    wrong_commit_rows = [row for row in out_rows if row.get("followup_evidence_v1_wrong_goal_commit") is True]
    no_valid_commit_rows = [row for row in out_rows if row.get("followup_evidence_v1_no_valid_commit") is True]
    success_commit_rows = [row for row in out_rows if row.get("followup_evidence_v1_success_commit") is True]
    safe_identity_defer_rows = [
        row for row in out_rows
        if "safe_identity_defer_rival_supported" in row["failure_tags"]
    ]

    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_rows": str(args.rows),
        "rows": len(out_rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_commit_rows),
        "wrong_commit_rows": len(wrong_commit_rows),
        "no_valid_commit_rows": len(no_valid_commit_rows),
        "safe_identity_defer_rows": len(safe_identity_defer_rows),
        "primary_failure_mode_counts": dict(sorted(primary_counts.items())),
        "failure_tag_counts": dict(sorted(tag_counts.items())),
        "primary_failure_by_query": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(primary_by_query.items())
        },
        "primary_failure_by_label_case": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(primary_by_label.items())
        },
        "primary_failure_by_source_external_evidence_v4_action": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(primary_by_source_action.items())
        },
        "primary_failure_by_followup_reason": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(primary_by_reason.items())
        },
        "primary_failure_by_scene": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(primary_by_scene.items())
        },
        "unsafe_commit_examples": [
            {
                "episode_key": row.get("episode_key"),
                "query": row.get("query"),
                "scene_id": row.get("scene_id"),
                "label_case": row.get("label_case"),
                "selected_candidate_id": row.get("selected_candidate_id"),
                "selected_score": row.get("selected_score"),
                "selected_margin": row.get("selected_margin"),
                "selected_strong_depth_evidence": row.get("selected_strong_depth_evidence"),
                "selected_strict_association_count": row.get("selected_strict_association_count"),
                "selected_mask_hit_count": row.get("selected_mask_hit_count"),
                "followup_set_contains_correct": row.get("followup_set_contains_correct"),
                "primary_failure_mode": row.get("primary_failure_mode"),
                "failure_tags": row.get("failure_tags"),
            }
            for row in wrong_commit_rows
        ],
        "revision_implications": {
            "first_eval_rerun_blocked": bool(wrong_commit_rows or no_valid_commit_rows),
            "threshold_only_revision_rejected": bool(
                tag_counts["strong_depth_evidence_not_instance_safe"]
                or tag_counts["positive_detector_support_not_instance_safe"]
            ),
            "needs_expanded_retrieval_validity_guard": bool(
                tag_counts["unsafe_no_valid_expanded_retrieval_commit"]
                or tag_counts["expanded_retrieval_set_missing_valid_target"]
            ),
            "needs_instance_safety_beyond_depth_association": bool(
                tag_counts["strong_depth_evidence_not_instance_safe"]
                or tag_counts["large_repeated_furniture_instance_confusion"]
            ),
            "preserve_identity_confirmation_defer": bool(safe_identity_defer_rows),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") is True for row in out_rows),
        "output_files": {
            "rows": "external_candidate_followup_failure_modes.jsonl",
            "summary": "external_candidate_followup_failure_mode_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "external_candidate_followup_failure_modes.jsonl", out_rows)
    write_json(out_root / "external_candidate_followup_failure_mode_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify H001 external-candidate follow-up evidence failures.")
    parser.add_argument("--rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
