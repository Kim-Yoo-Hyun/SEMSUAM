import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    request_sort_key,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_fresh_labels.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def row_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (request_id(row), candidate_id(row))


def source_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    indexed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        rid = request_id(row)
        if rid and rid not in indexed:
            indexed[rid] = dict(row)
    return indexed


def unique_target_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = row_key(row)
        if all(key) and key not in indexed:
            indexed[key] = dict(row)
    return [
        indexed[key]
        for key in sorted(
            indexed,
            key=lambda item: (request_sort_key(item[0]), item[1]),
        )
    ]


def build_labels(source_rows: Sequence[Dict[str, Any]], target_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    sources = source_index(source_rows)
    labels: List[Dict[str, Any]] = []
    for target in unique_target_rows(target_rows):
        rid = request_id(target)
        cid = candidate_id(target)
        source = sources.get(rid) or {}
        summary = source.get("evaluation_candidate_summary") or {}
        correct_ids = {str(value) for value in summary.get("evaluation_only_correct_candidate_ids") or []}
        wrong_ids = {str(value) for value in summary.get("evaluation_only_wrong_candidate_ids") or []}
        if cid in correct_ids:
            correct = True
            label_source = "evaluation_only_correct_candidate_ids"
        elif cid in wrong_ids:
            correct = False
            label_source = "evaluation_only_wrong_candidate_ids"
        else:
            correct = None
            label_source = "evaluation_only_unlabeled_candidate"
        labels.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "evaluation_only_fresh_object_relation_candidate_label",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": target.get("rival_identity_request_id") or source.get("rival_identity_request_id"),
                "episode_key": target.get("episode_key") or source.get("episode_key"),
                "scene_key": target.get("scene_key") or source.get("scene_key"),
                "scene_id": target.get("scene_id") or source.get("scene_id"),
                "query": target.get("query") or source.get("query"),
                "candidate_id": cid,
                "target_candidate_id": cid,
                "evaluation_only_candidate_correct": correct,
                "evaluation_only_candidate_rank": target.get("target_generated_rank"),
                "evaluation_only_label_source": label_source,
                "evaluation_only_correct_candidate_count": summary.get("evaluation_only_correct_candidate_count"),
                "evaluation_only_wrong_candidate_count": summary.get("evaluation_only_wrong_candidate_count"),
                "evaluation_only_no_valid_candidate_pool": summary.get("evaluation_only_no_valid_candidate_pool"),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return labels


def count_values(rows: Iterable[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for row in rows:
        value = str(row.get(key))
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expand fresh object-relation source evaluation summaries into candidate-level labels."
    )
    parser.add_argument("--source-evaluated-rows", required=True)
    parser.add_argument("--target-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_rows = load_jsonl(Path(args.source_evaluated_rows))
    target_rows = load_jsonl(Path(args.target_rows))
    labels = build_labels(source_rows, target_rows)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "object_relation_fresh_candidate_labels.jsonl", labels)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "source_evaluated_rows": str(args.source_evaluated_rows),
        "target_rows": str(args.target_rows),
        "label_rows": len(labels),
        "request_rows": len({request_id(row) for row in labels}),
        "candidate_correct_counts": count_values(labels, "evaluation_only_candidate_correct"),
        "label_source_counts": count_values(labels, "evaluation_only_label_source"),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "labels": "object_relation_fresh_candidate_labels.jsonl",
            "summary": "object_relation_fresh_candidate_labels_summary.json",
        },
    }
    write_json(out_root / "object_relation_fresh_candidate_labels_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
