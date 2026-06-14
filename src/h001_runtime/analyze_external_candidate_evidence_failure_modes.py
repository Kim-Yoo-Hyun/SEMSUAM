import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "h001.external_candidate_evidence_failure_modes.v1"


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


def strong_candidate_count(row: Dict[str, Any]) -> int:
    return sum(candidate.get("v2_strong_depth_evidence") is True for candidate in row.get("candidate_evidence") or [])


def positive_candidate_count(row: Dict[str, Any]) -> int:
    return sum(candidate.get("positive_support") is True for candidate in row.get("candidate_evidence") or [])


def selected_candidate(row: Dict[str, Any]) -> Dict[str, Any]:
    selected_id = row.get("selected_candidate_id")
    for candidate in row.get("candidate_evidence") or []:
        if candidate.get("candidate_id") == selected_id:
            return candidate
    return {}


def classify(row: Dict[str, Any]) -> Dict[str, Any]:
    commits = row.get("external_evidence_v2_commits") is True
    selected_correct = row.get("selected_candidate_correct")
    contains_correct = row.get("external_set_contains_correct") is True
    first_correct = row.get("first_external_correct") is True
    no_valid_commit = row.get("external_evidence_v2_no_valid_external_commit") is True
    wrong_commit = row.get("external_evidence_v2_wrong_goal_commit") is True
    source_reason = str(row.get("source_objective_reason"))
    query = str(row.get("query"))
    selected = selected_candidate(row)
    selected_strong = selected.get("v2_strong_depth_evidence") is True
    tags: List[str] = []

    if commits and selected_correct is True:
        tags.append("successful_external_commit")
    if commits and no_valid_commit:
        tags.append("unsafe_no_valid_external_commit")
    if commits and wrong_commit and contains_correct:
        tags.append("wrong_instance_selected_despite_correct_in_set")
    if commits and wrong_commit and first_correct:
        tags.append("wrong_rerank_over_correct_first_candidate")
    if commits and wrong_commit and selected_strong:
        tags.append("strong_depth_evidence_not_instance_safe")
    if commits and wrong_commit and query in {"bed", "chair", "sofa"}:
        tags.append("large_repeated_furniture_instance_confusion")
    if commits and wrong_commit and source_reason == "alt_confirmation_without_pair_set_completeness":
        tags.append("alt_confirm_untrusted_external_commit_unsafe")
    if not commits and not contains_correct:
        tags.append("external_retrieval_miss_defer")
    if not commits and contains_correct and positive_candidate_count(row) == 0:
        tags.append("detector_missed_correct_external_candidate")
    if not commits and contains_correct and positive_candidate_count(row) > 0:
        tags.append("conservative_defer_with_correct_available")
    if not commits and row.get("external_evidence_v2_reason") == "defer_no_positive_external_evidence":
        tags.append("defer_no_positive_external_evidence")

    if not tags:
        tags.append("uncategorized")

    priority = [
        "unsafe_no_valid_external_commit",
        "wrong_rerank_over_correct_first_candidate",
        "wrong_instance_selected_despite_correct_in_set",
        "strong_depth_evidence_not_instance_safe",
        "successful_external_commit",
        "external_retrieval_miss_defer",
        "detector_missed_correct_external_candidate",
        "conservative_defer_with_correct_available",
    ]
    primary = next((tag for tag in priority if tag in tags), tags[0])
    return {
        "failure_tags": tags,
        "primary_failure_mode": primary,
        "strong_candidate_count": strong_candidate_count(row),
        "positive_candidate_count": positive_candidate_count(row),
        "selected_strong_depth_evidence": selected_strong,
        "selected_strict_association_count": selected.get("strict_association_count"),
        "selected_mask_hit_count": selected.get("mask_hit_count"),
        "selected_visible_count": selected.get("visible_count"),
        "selected_score": safe_float(row.get("selected_score")),
        "selected_margin": safe_float(row.get("score_margin")),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.rows))
    out_rows: List[Dict[str, Any]] = []
    primary_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    primary_by_query: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_source_reason: Dict[str, Counter[str]] = defaultdict(Counter)

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
            "source_objective_action": row.get("source_objective_action"),
            "source_objective_reason": row.get("source_objective_reason"),
            "external_branch_trigger_reason": row.get("external_branch_trigger_reason"),
            "external_evidence_v2_action": row.get("external_evidence_v2_action"),
            "external_evidence_v2_reason": row.get("external_evidence_v2_reason"),
            "external_set_contains_correct": row.get("external_set_contains_correct"),
            "first_external_correct": row.get("first_external_correct"),
            "selected_candidate_id": row.get("selected_candidate_id"),
            "selected_candidate_correct": row.get("selected_candidate_correct"),
            "external_evidence_v2_commits": row.get("external_evidence_v2_commits"),
            "external_evidence_v2_success_commit": row.get("external_evidence_v2_success_commit"),
            "external_evidence_v2_wrong_goal_commit": row.get("external_evidence_v2_wrong_goal_commit"),
            "external_evidence_v2_no_valid_external_commit": row.get("external_evidence_v2_no_valid_external_commit"),
            "uses_gt_for_action": row.get("uses_gt_for_action"),
            "uses_gt_for_analysis": row.get("uses_gt_for_analysis"),
            **labels,
        }
        out_rows.append(out)
        primary_counts[out["primary_failure_mode"]] += 1
        primary_by_query[str(out.get("query"))][out["primary_failure_mode"]] += 1
        primary_by_label[str(out.get("label_case"))][out["primary_failure_mode"]] += 1
        primary_by_source_reason[str(out.get("source_objective_reason"))][out["primary_failure_mode"]] += 1
        for tag in out["failure_tags"]:
            tag_counts[tag] += 1

    commit_rows = [row for row in out_rows if row.get("external_evidence_v2_commits") is True]
    wrong_commit_rows = [row for row in out_rows if row.get("external_evidence_v2_wrong_goal_commit") is True]
    no_valid_commit_rows = [row for row in out_rows if row.get("external_evidence_v2_no_valid_external_commit") is True]
    retrieval_miss_rows = [row for row in out_rows if "external_retrieval_miss_defer" in row["failure_tags"]]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "rows": len(out_rows),
        "source_rows": str(args.rows),
        "commit_rows": len(commit_rows),
        "wrong_commit_rows": len(wrong_commit_rows),
        "no_valid_commit_rows": len(no_valid_commit_rows),
        "retrieval_miss_rows": len(retrieval_miss_rows),
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
        "primary_failure_by_source_objective_reason": {
            key: dict(sorted(counts.items()))
            for key, counts in sorted(primary_by_source_reason.items())
        },
        "revision_implications": {
            "first_eval_rerun_blocked": bool(wrong_commit_rows or no_valid_commit_rows),
            "threshold_only_revision_rejected": bool(wrong_commit_rows),
            "needs_instance_safety_or_identity_consistency": bool(
                tag_counts["strong_depth_evidence_not_instance_safe"]
                or tag_counts["wrong_instance_selected_despite_correct_in_set"]
            ),
            "needs_external_retrieval_revision": bool(
                retrieval_miss_rows or tag_counts["unsafe_no_valid_external_commit"]
            ),
            "needs_alt_confirm_untrusted_scope_guard": bool(
                tag_counts["alt_confirm_untrusted_external_commit_unsafe"]
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "external_candidate_evidence_failure_modes.jsonl",
            "summary": "external_candidate_evidence_failure_mode_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "external_candidate_evidence_failure_modes.jsonl", out_rows)
    write_json(out_root / "external_candidate_evidence_failure_mode_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify H001 external-candidate evidence failure modes.")
    parser.add_argument("--rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
