import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.run_smoke import (
    ArtifactJSONLBackend,
    Candidate,
    label_candidate_correctness,
    load_manifest_episodes,
)


SCHEMA_VERSION = "h001.dense_conflict_recall_gate.v1"


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


def first_correct_rank(candidates: List[Candidate]) -> Optional[int]:
    for rank, candidate in enumerate(candidates, start=1):
        if candidate.correct is True:
            return rank
    return None


def role_allowed(role: str, allowed: List[str]) -> bool:
    return "all" in allowed or role in allowed


def inspect_artifact(
    artifact_name: str,
    artifact_path: Path,
    loaded_items: List[Any],
    recall_ks: List[int],
    roles: List[str],
) -> List[Dict[str, Any]]:
    backend = ArtifactJSONLBackend(artifact_path)
    rows: List[Dict[str, Any]] = []
    for item in loaded_items:
        manifest_row = item.manifest_row or {}
        role = str(manifest_row.get("dense_conflict_role") or "unknown")
        if not role_allowed(role, roles):
            continue
        candidates = backend.candidates_for(item)
        label_candidate_correctness(item, candidates)
        correct = [
            candidate_brief(candidate, rank)
            for rank, candidate in enumerate(candidates, start=1)
            if candidate.correct is True
        ]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_name": artifact_name,
                "artifact_path": str(artifact_path),
                "episode_key": manifest_row.get("episode_key"),
                "scene_id": item.episode.get("scene_id"),
                "scene_key": manifest_row.get("scene_key"),
                "query": item.episode.get("object_category"),
                "dense_conflict_role": role,
                "dense_conflict_class": manifest_row.get("dense_conflict_class"),
                "source_external_branch_id": manifest_row.get("dense_conflict_source_external_branch_id"),
                "source_positive_support_candidate_count": manifest_row.get(
                    "dense_conflict_positive_support_candidate_count"
                ),
                "source_correct_positive_support_candidate_count": manifest_row.get(
                    "dense_conflict_correct_positive_support_candidate_count"
                ),
                "source_wrong_positive_support_candidate_count": manifest_row.get(
                    "dense_conflict_wrong_positive_support_candidate_count"
                ),
                "source_selected_wrong_positive_support": manifest_row.get(
                    "dense_conflict_selected_wrong_positive_support"
                ),
                "candidate_count": len(candidates),
                "first_correct_rank": first_correct_rank(candidates),
                "top_candidate": candidate_brief(candidates[0], 1) if candidates else None,
                "correct_candidate_count": len(correct),
                "correct_candidates": correct[:10],
                "contains_correct": bool(correct),
                "recall_at_k": {str(k): recall_at_k(candidates, k) for k in recall_ks},
                "uses_gt_for_action": backend.uses_gt_for_action,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def aggregate(rows: List[Dict[str, Any]], recall_ks: List[int]) -> Dict[str, Any]:
    if not rows:
        return {
            "rows": 0,
            "rows_with_correct": 0,
            "rows_with_correct_rate": None,
            "candidate_count_min": 0,
            "candidate_count_max": 0,
            "recall_at_k": {str(k): None for k in recall_ks},
        }
    return {
        "rows": len(rows),
        "rows_with_correct": sum(row["contains_correct"] for row in rows),
        "rows_with_correct_rate": sum(row["contains_correct"] for row in rows) / len(rows),
        "candidate_count_min": min(row["candidate_count"] for row in rows),
        "candidate_count_max": max(row["candidate_count"] for row in rows),
        "recall_at_k": {
            str(k): sum(row["recall_at_k"][str(k)] for row in rows) / len(rows)
            for k in recall_ks
        },
        "first_correct_rank_min": min(
            (row["first_correct_rank"] for row in rows if row["first_correct_rank"] is not None),
            default=None,
        ),
        "first_correct_rank_max": max(
            (row["first_correct_rank"] for row in rows if row["first_correct_rank"] is not None),
            default=None,
        ),
    }


def gate_for_artifact(
    artifact_rows: List[Dict[str, Any]],
    args: argparse.Namespace,
    recall_ks: List[int],
) -> Dict[str, Any]:
    primary_rows = [row for row in artifact_rows if row.get("dense_conflict_role") == "primary"]
    primary_summary = aggregate(primary_rows, recall_ks)
    recall_key = str(args.gate_recall_k)
    recall_value = primary_summary["recall_at_k"].get(recall_key)
    rows_with_correct = int(primary_summary["rows_with_correct"] or 0)
    passes = (
        int(primary_summary["rows"]) >= int(args.min_primary_rows)
        and rows_with_correct >= int(args.min_primary_rows_with_correct)
        and recall_value is not None
        and recall_value >= float(args.min_primary_recall_at_k)
        and all(row.get("uses_gt_for_action") is False for row in primary_rows)
    )
    return {
        "passes_dense_recall_gate": passes,
        "primary_summary": primary_summary,
        "thresholds": {
            "min_primary_rows": int(args.min_primary_rows),
            "min_primary_rows_with_correct": int(args.min_primary_rows_with_correct),
            "gate_recall_k": int(args.gate_recall_k),
            "min_primary_recall_at_k": float(args.min_primary_recall_at_k),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    recall_ks = [int(value) for value in str(args.recall_ks).split(",") if value.strip()]
    if int(args.gate_recall_k) not in recall_ks:
        recall_ks.append(int(args.gate_recall_k))
        recall_ks = sorted(set(recall_ks))
    roles = [role.strip() for role in str(args.roles).split(",") if role.strip()]
    loaded_items = load_manifest_episodes(
        Path(args.data_root),
        Path(args.manifest),
        str(args.manifest_split),
        int(args.episodes),
    )

    all_rows: List[Dict[str, Any]] = []
    missing_artifacts: List[str] = []
    for artifact_arg in args.candidate_artifact:
        name, path = parse_named_path(artifact_arg)
        if not path.exists():
            missing_artifacts.append(f"{name}={path}")
            continue
        all_rows.extend(inspect_artifact(name, path, loaded_items, recall_ks, roles))

    artifact_names = sorted({row["artifact_name"] for row in all_rows})
    by_artifact: Dict[str, Dict[str, Any]] = {}
    gate_by_artifact: Dict[str, Dict[str, Any]] = {}
    for artifact_name in artifact_names:
        rows = [row for row in all_rows if row["artifact_name"] == artifact_name]
        by_artifact[artifact_name] = aggregate(rows, recall_ks)
        by_artifact[artifact_name]["by_role"] = {
            role: aggregate([row for row in rows if row.get("dense_conflict_role") == role], recall_ks)
            for role in sorted({str(row.get("dense_conflict_role")) for row in rows})
        }
        gate_by_artifact[artifact_name] = gate_for_artifact(rows, args, recall_ks)

    passing = [
        name
        for name, gate in gate_by_artifact.items()
        if gate.get("passes_dense_recall_gate") is True
    ]
    selected_artifact = None
    if passing:
        selected_artifact = max(
            passing,
            key=lambda name: (
                gate_by_artifact[name]["primary_summary"]["rows_with_correct"],
                gate_by_artifact[name]["primary_summary"]["recall_at_k"][str(args.gate_recall_k)] or 0.0,
                by_artifact[name]["candidate_count_max"],
            ),
        )

    role_counts = Counter(str(row.get("dense_conflict_role")) for row in all_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "manifest": str(args.manifest),
        "manifest_split": str(args.manifest_split),
        "candidate_artifacts_requested": args.candidate_artifact,
        "missing_artifacts": missing_artifacts,
        "out_root": str(args.out_root),
        "roles": roles,
        "rows": len(all_rows),
        "role_counts": dict(sorted(role_counts.items())),
        "by_artifact": by_artifact,
        "gate_by_artifact": gate_by_artifact,
        "passes_any_dense_recall_gate": bool(passing),
        "passing_artifacts": passing,
        "selected_artifact_for_next_detector_step": selected_artifact,
        "decision": {
            "detector_job_allowed": bool(passing),
            "next_step": (
                "run dense conflict detector/association validation for the selected artifact"
                if passing
                else "stop before detector scoring and revise dense candidate generation"
            ),
        },
        "interpretation": {
            "fact": "This gate measures candidate recall before detector scoring.",
            "agent_inference": (
                "Detector validation is meaningful only if the non-GT candidate pool contains correct "
                "candidates on enough frozen conflict rows."
            ),
            "paper_claim_status": "gate_only_not_policy_claim",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "dense_conflict_recall_rows.jsonl",
            "summary": "dense_conflict_recall_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "dense_conflict_recall_rows.jsonl", all_rows)
    write_json(out_root / "dense_conflict_recall_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gate dense conflict candidate recall before detector scoring.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-split", default="dense_conflict_v1")
    parser.add_argument("--episodes", type=int, default=0)
    parser.add_argument("--roles", default="primary")
    parser.add_argument("--candidate-artifact", action="append", default=[], required=True)
    parser.add_argument("--recall-ks", default="1,5,10,20,50,100,200")
    parser.add_argument("--gate-recall-k", type=int, default=20)
    parser.add_argument("--min-primary-rows", type=int, default=6)
    parser.add_argument("--min-primary-rows-with-correct", type=int, default=4)
    parser.add_argument("--min-primary-recall-at-k", type=float, default=0.50)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
