import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_candidate_set_diagnostic.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def label_index(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in label_rows:
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is not None and candidate_id is not None:
            indexed[(str(episode_key), str(candidate_id))] = row
    return indexed


def action_evidence_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        episode_key = row.get("episode_key")
        query = row.get("query")
        if episode_key is not None and query is not None:
            indexed[(str(episode_key), str(query))] = row
    return indexed


def source_top(candidates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda candidate: (
            safe_int(candidate.get("semantic_rank")),
            safe_int(candidate.get("selection_rank")),
            str(candidate.get("candidate_id")),
        ),
    )


def candidate_snapshot(candidate: Dict[str, Any], label: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "selection_rank": candidate.get("selection_rank"),
        "semantic_rank": candidate.get("semantic_rank"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": candidate.get("positive_support"),
        "analysis_only_candidate_correct": None
        if label is None
        else label.get("evaluation_only_candidate_correct"),
        "analysis_only_wrong_goal_visit": None
        if label is None
        else label.get("evaluation_only_wrong_goal_visit"),
        "analysis_only_goal_visit": None
        if label is None
        else label.get("evaluation_only_goal_visit"),
        "analysis_only_wasted_path_from_candidate": None
        if label is None
        else label.get("evaluation_only_wasted_path_from_candidate"),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    candidate_rows = load_jsonl(Path(args.candidate_set))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))
    action_rows = (
        action_evidence_index(load_jsonl(Path(args.action_evidence_rows)))
        if args.action_evidence_rows
        else {}
    )

    diagnostic_rows: List[Dict[str, Any]] = []
    missing_label_rows = 0
    missing_label_candidates = 0
    rows_with_correct = 0
    rows_without_correct = 0
    rows_with_wrong_goal_candidate = 0
    source_top_correct_rows = 0
    source_top_wrong_rows = 0
    source_top_wrong_goal_rows = 0
    wrong_top_replacement_rows = 0
    correct_count_dist: Counter[int] = Counter()
    wrong_goal_count_dist: Counter[int] = Counter()
    taxonomy_counts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    full_pool_contains_correct_rows = 0
    full_pool_no_valid_rows = 0
    selected_missed_full_pool_correct_rows = 0

    for row in candidate_rows:
        episode_key = str(row.get("episode_key"))
        query = str(row.get("query"))
        query_counts[query] += 1
        expanded = list(row.get("expanded_candidates") or [])
        snapshots = []
        correct_count = 0
        wrong_goal_count = 0
        labeled_count = 0
        for candidate in expanded:
            key = (episode_key, str(candidate.get("candidate_id")))
            label = labels.get(key)
            if label is None:
                missing_label_candidates += 1
            else:
                labeled_count += 1
                correct_count += int(label.get("evaluation_only_candidate_correct") is True)
                wrong_goal_count += int(label.get("evaluation_only_wrong_goal_visit") is True)
            snapshots.append(candidate_snapshot(candidate, label))

        top = source_top(expanded)
        top_label = labels.get((episode_key, str(top.get("candidate_id")))) if top else None
        top_correct = None if top_label is None else top_label.get("evaluation_only_candidate_correct") is True
        top_wrong_goal = None if top_label is None else top_label.get("evaluation_only_wrong_goal_visit") is True
        if top_label is None:
            missing_label_rows += 1
        elif top_correct:
            source_top_correct_rows += 1
        else:
            source_top_wrong_rows += 1
            wrong_top_replacement_rows += int(correct_count > 0)
        if top_wrong_goal:
            source_top_wrong_goal_rows += 1

        full_pool = list((action_rows.get((episode_key, query)) or {}).get("candidate_evidence") or [])
        full_pool_correct_count = 0
        full_pool_labeled_count = 0
        for candidate in full_pool:
            label = labels.get((episode_key, str(candidate.get("candidate_id"))))
            if label is None:
                continue
            full_pool_labeled_count += 1
            full_pool_correct_count += int(label.get("evaluation_only_candidate_correct") is True)
        if full_pool:
            full_pool_contains_correct_rows += int(full_pool_correct_count > 0)
            full_pool_no_valid_rows += int(full_pool_correct_count == 0)

        contains_correct = correct_count > 0
        contains_wrong_goal = wrong_goal_count > 0
        selected_missed_full_pool_correct = bool(not contains_correct and full_pool_correct_count > 0)
        selected_missed_full_pool_correct_rows += int(selected_missed_full_pool_correct)
        if not contains_correct and full_pool_correct_count == 0:
            taxonomy = "source_pool_no_valid_candidate"
        elif selected_missed_full_pool_correct:
            taxonomy = "selection_missed_valid_candidate"
        elif contains_wrong_goal:
            taxonomy = "valid_set_with_wrong_goal_distractor"
        else:
            taxonomy = "valid_set_without_wrong_goal_distractor"
        taxonomy_counts[taxonomy] += 1
        rows_with_correct += int(contains_correct)
        rows_without_correct += int(not contains_correct)
        rows_with_wrong_goal_candidate += int(contains_wrong_goal)
        correct_count_dist[correct_count] += 1
        wrong_goal_count_dist[wrong_goal_count] += 1

        diagnostic_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "expanded_candidate_count": row.get("expanded_candidate_count"),
                "labeled_candidate_count": labeled_count,
                "analysis_only_correct_candidate_count": correct_count,
                "analysis_only_wrong_goal_candidate_count": wrong_goal_count,
                "analysis_only_contains_correct": contains_correct,
                "analysis_only_no_valid_candidate": not contains_correct,
                "analysis_only_contains_wrong_goal_candidate": contains_wrong_goal,
                "source_top_candidate_id": None if top is None else top.get("candidate_id"),
                "analysis_only_source_top_correct": top_correct,
                "analysis_only_source_top_wrong_goal": top_wrong_goal,
                "analysis_only_wrong_top_replaced_by_expanded_set": bool(top_correct is False and contains_correct),
                "analysis_only_full_pool_candidate_count": len(full_pool),
                "analysis_only_full_pool_labeled_count": full_pool_labeled_count,
                "analysis_only_full_pool_correct_candidate_count": full_pool_correct_count,
                "analysis_only_selected_missed_full_pool_correct": selected_missed_full_pool_correct,
                "analysis_only_candidate_set_taxonomy": taxonomy,
                "analysis_only_candidates": snapshots,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )

    row_count = len(candidate_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_set": str(args.candidate_set),
        "evaluation_labels": str(args.evaluation_labels),
        "request_rows": row_count,
        "candidate_rows": sum(len(row.get("expanded_candidates") or []) for row in candidate_rows),
        "missing_label_rows": missing_label_rows,
        "missing_label_candidates": missing_label_candidates,
        "candidate_set_contains_correct_rows": rows_with_correct,
        "candidate_set_contains_correct_rate": ratio(rows_with_correct, row_count),
        "no_valid_candidate_rows": rows_without_correct,
        "no_valid_candidate_rate": ratio(rows_without_correct, row_count),
        "rows_with_wrong_goal_candidate": rows_with_wrong_goal_candidate,
        "rows_with_wrong_goal_candidate_rate": ratio(rows_with_wrong_goal_candidate, row_count),
        "source_top_correct_rows": source_top_correct_rows,
        "source_top_correct_rate": ratio(source_top_correct_rows, row_count),
        "source_top_wrong_rows": source_top_wrong_rows,
        "source_top_wrong_goal_rows": source_top_wrong_goal_rows,
        "wrong_top_replacement_rows": wrong_top_replacement_rows,
        "wrong_top_replacement_rate": ratio(wrong_top_replacement_rows, source_top_wrong_rows),
        "full_pool_contains_correct_rows": full_pool_contains_correct_rows,
        "full_pool_contains_correct_rate": ratio(full_pool_contains_correct_rows, row_count),
        "full_pool_no_valid_rows": full_pool_no_valid_rows,
        "selected_missed_full_pool_correct_rows": selected_missed_full_pool_correct_rows,
        "correct_candidate_count_distribution": {str(key): value for key, value in sorted(correct_count_dist.items())},
        "wrong_goal_candidate_count_distribution": {str(key): value for key, value in sorted(wrong_goal_count_dist.items())},
        "candidate_set_taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "diagnostic_gate": {
            "all_request_rows_labeled": missing_label_rows == 0,
            "no_missing_candidate_labels": missing_label_candidates == 0,
            "analysis_only_report": True,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
            "paper_claim_allowed": False,
        },
        "output_files": {
            "rows": "expanded_retrieval_candidate_set_validity_rows.jsonl",
            "summary": "expanded_retrieval_candidate_set_validity_summary.json",
        },
    }
    summary["diagnostic_gate"]["passes_label_join_gate"] = (
        summary["diagnostic_gate"]["all_request_rows_labeled"]
        and summary["diagnostic_gate"]["no_missing_candidate_labels"]
    )

    write_jsonl(out_root / "expanded_retrieval_candidate_set_validity_rows.jsonl", diagnostic_rows)
    write_json(out_root / "expanded_retrieval_candidate_set_validity_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose expanded retrieval candidate-set validity using analysis-only labels.")
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--action-evidence-rows")
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["diagnostic_gate"]["passes_label_join_gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
