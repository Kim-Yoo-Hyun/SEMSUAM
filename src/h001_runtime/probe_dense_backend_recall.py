import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from h001_runtime.run_smoke import (
    ArtifactJSONLBackend,
    Candidate,
    label_candidate_correctness,
    load_manifest_episodes,
)


SCHEMA_VERSION = "h001.dense_backend_recall_probe.v1"
NO_CORRECT_REASON = "defer_identity_selected_outside_rival_near_tie"


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


def parse_named_path(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    name, path = value.split("=", 1)
    return name.strip(), Path(path)


def candidate_brief(candidate: Candidate, rank: int) -> Dict[str, Any]:
    return {
        "rank": rank,
        "candidate_id": candidate.candidate_id,
        "score": candidate.score,
        "position": candidate.position,
        "visit_position": candidate.visit_position,
        "correct": candidate.correct,
        "correct_source": candidate.correct_source,
        "backend_name": candidate.backend_name,
        "uses_gt_for_action": candidate.uses_gt_for_action,
    }


def recall_at_k(candidates: List[Candidate], k: int) -> bool:
    return any(candidate.correct is True for candidate in candidates[:k])


def inspect_artifact(
    artifact_name: str,
    artifact_path: Path,
    loaded_items: List[Any],
    episode_keys: List[str],
    recall_ks: List[int],
) -> List[Dict[str, Any]]:
    backend = ArtifactJSONLBackend(artifact_path)
    rows: List[Dict[str, Any]] = []
    for item in loaded_items:
        episode_key = str((item.manifest_row or {}).get("episode_key"))
        if episode_key not in episode_keys:
            continue
        candidates = backend.candidates_for(item)
        label_candidate_correctness(item, candidates)
        correct = [
            candidate_brief(candidate, rank)
            for rank, candidate in enumerate(candidates, start=1)
            if candidate.correct is True
        ]
        top = candidate_brief(candidates[0], 1) if candidates else None
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_name": artifact_name,
                "artifact_path": str(artifact_path),
                "episode_key": episode_key,
                "scene_id": item.episode.get("scene_id"),
                "query": item.episode.get("object_category"),
                "candidate_count": len(candidates),
                "top_candidate": top,
                "correct_candidate_count": len(correct),
                "correct_candidates": correct[:10],
                "contains_correct": bool(correct),
                "recall_at_k": {str(k): recall_at_k(candidates, k) for k in recall_ks},
                "uses_gt_for_action": backend.uses_gt_for_action,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    followup_rows = [
        row
        for row in load_jsonl(Path(args.followup_evidence_rows))
        if row.get("followup_evidence_v1_reason") == NO_CORRECT_REASON
    ]
    episode_keys = [str(row.get("episode_key")) for row in followup_rows]
    loaded_items = load_manifest_episodes(
        Path(args.data_root),
        Path(args.manifest),
        str(args.manifest_split),
        int(args.episodes),
    )
    recall_ks = [int(value) for value in str(args.recall_ks).split(",") if str(value).strip()]

    artifact_rows: List[Dict[str, Any]] = []
    missing_artifacts: List[str] = []
    for artifact_arg in args.candidate_artifact:
        name, path = parse_named_path(artifact_arg)
        if not path.exists():
            missing_artifacts.append(f"{name}={path}")
            continue
        artifact_rows.extend(inspect_artifact(name, path, loaded_items, episode_keys, recall_ks))

    by_artifact: Dict[str, Dict[str, Any]] = {}
    for name in sorted({row["artifact_name"] for row in artifact_rows}):
        rows = [row for row in artifact_rows if row["artifact_name"] == name]
        by_artifact[name] = {
            "rows": len(rows),
            "candidate_count_min": min((row["candidate_count"] for row in rows), default=0),
            "candidate_count_max": max((row["candidate_count"] for row in rows), default=0),
            "rows_with_correct": sum(row["contains_correct"] for row in rows),
            "rows_with_correct_rate": None if not rows else sum(row["contains_correct"] for row in rows) / len(rows),
            "recall_at_k": {
                str(k): None if not rows else sum(row["recall_at_k"][str(k)] for row in rows) / len(rows)
                for k in recall_ks
            },
        }

    recovered_rows = [
        row
        for row in artifact_rows
        if row["contains_correct"]
    ]
    episode_recovered = {
        episode_key: any(row["episode_key"] == episode_key and row["contains_correct"] for row in artifact_rows)
        for episode_key in episode_keys
    }
    recommendation_counts = Counter()
    if all(episode_recovered.values()) if episode_recovered else False:
        recommendation_counts["promote_dense_backend_candidate_generation"] += 1
        next_step = "materialize the best non-GT dense backend as a fixed artifact and run detector observation"
    else:
        recommendation_counts["regenerate_raw_vlmaps_map_or_new_backend"] += 1
        next_step = "regenerate the source VLMaps map or test a less suppressed object-node backend"

    summary = {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "manifest": str(args.manifest),
        "manifest_split": str(args.manifest_split),
        "episode_keys": episode_keys,
        "candidate_artifacts_requested": args.candidate_artifact,
        "missing_artifacts": missing_artifacts,
        "out_root": str(out_root),
        "rows": len(artifact_rows),
        "episodes": len(episode_keys),
        "by_artifact": by_artifact,
        "episode_recovered_by_any_artifact": episode_recovered,
        "episode_recovered_by_any_artifact_rate": (
            None if not episode_recovered else sum(episode_recovered.values()) / len(episode_recovered)
        ),
        "recovered_rows": len(recovered_rows),
        "recommendation_counts": dict(sorted(recommendation_counts.items())),
        "next_step": next_step,
        "interpretation": {
            "paper_claim_status": "not_a_paper_claim",
            "fact": "This probe measures recall of already materialized non-GT candidate pools.",
            "agent_inference": (
                "If no available artifact recovers a correct candidate, the blocker is candidate generation "
                "rather than detector observation or identity arbitration."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "dense_backend_recall_probe_rows.jsonl",
            "summary": "dense_backend_recall_probe_summary.json",
        },
    }
    write_jsonl(out_root / "dense_backend_recall_probe_rows.jsonl", artifact_rows)
    write_json(out_root / "dense_backend_recall_probe_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe dense/backend recall for no-correct external-candidate rows.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-split", default="first_eval_replacement_v1")
    parser.add_argument("--episodes", type=int, default=0)
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--candidate-artifact", action="append", default=[], required=True)
    parser.add_argument("--recall-ks", default="1,5,10,20,50,100,200")
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
