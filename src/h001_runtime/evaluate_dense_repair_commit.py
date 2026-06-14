import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


SCHEMA_VERSION = "h001.dense_repair_commit_evaluation.v1"


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


def correct_ids_by_episode(recall_rows: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    indexed: Dict[str, Set[str]] = {}
    for row in recall_rows:
        indexed[str(row.get("episode_key"))] = {
            str(candidate.get("candidate_id"))
            for candidate in row.get("correct_candidates") or []
            if candidate.get("candidate_id") is not None
        }
    return indexed


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evidence_rows = load_jsonl(Path(args.evidence_rows))
    recall_rows = load_jsonl(Path(args.recall_rows))
    correct_by_episode = correct_ids_by_episode(recall_rows)
    output_rows: List[Dict[str, Any]] = []
    for row in evidence_rows:
        episode_key = str(row.get("episode_key"))
        selected_id = str(row.get("selected_candidate_id")) if row.get("selected_candidate_id") is not None else None
        correct_ids = correct_by_episode.get(episode_key, set())
        commits = row.get("external_evidence_v1_action") == "external_evidence_v1_commit_candidate"
        selected_correct = selected_id in correct_ids if selected_id is not None else False
        output_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "query": row.get("query"),
                "external_branch_id": row.get("external_branch_id"),
                "action": row.get("external_evidence_v1_action"),
                "reason": row.get("external_evidence_v1_reason"),
                "selected_candidate_id": selected_id,
                "selected_candidate_correct": selected_correct,
                "correct_candidate_ids": sorted(correct_ids),
                "commits": commits,
                "success_commit": bool(commits and selected_correct),
                "wrong_goal_commit": bool(commits and not selected_correct),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )

    commit_rows = [row for row in output_rows if row["commits"]]
    success_rows = [row for row in output_rows if row["success_commit"]]
    wrong_rows = [row for row in output_rows if row["wrong_goal_commit"]]
    action_counts = Counter(str(row["action"]) for row in output_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "evidence_rows": str(args.evidence_rows),
        "recall_rows": str(args.recall_rows),
        "out_root": str(args.out_root),
        "rows": len(output_rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "commit_rate": ratio(len(commit_rows), len(output_rows)),
        "success_commit_rate": ratio(len(success_rows), len(output_rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), len(output_rows)),
        "action_counts": dict(sorted(action_counts.items())),
        "interpretation": {
            "fact": "This evaluation labels already-selected candidates against recall-probe GT analysis labels.",
            "agent_inference": (
                "If action selection did not use these labels, a positive result supports the detector-backed "
                "repair diagnostic but is still a narrow held-out analysis rather than a policy-scale claim."
            ),
            "paper_claim_status": "not_a_paper_claim",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "dense_repair_commit_evaluation_rows.jsonl",
            "summary": "dense_repair_commit_evaluation_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "dense_repair_commit_evaluation_rows.jsonl", output_rows)
    write_json(out_root / "dense_repair_commit_evaluation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate dense repair commits against recall-probe analysis labels.")
    parser.add_argument("--evidence-rows", required=True)
    parser.add_argument("--recall-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
