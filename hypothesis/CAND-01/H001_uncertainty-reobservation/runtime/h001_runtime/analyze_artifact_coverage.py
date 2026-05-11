import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from h001_runtime.run_smoke import (
    ArtifactJSONLBackend,
    SceneCache,
    label_candidate_correctness,
    load_manifest_episodes,
    scene_path,
)


def mean(values: Iterable[float]) -> Optional[float]:
    values = list(values)
    if not values:
        return None
    return sum(values) / len(values)


def rate(count: int, total: int) -> Optional[float]:
    if total <= 0:
        return None
    return count / total


def load_json(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    source = Path(path)
    if not source.exists():
        return None
    return json.loads(source.read_text(encoding="utf-8"))


def analyze(args: argparse.Namespace) -> Dict[str, Any]:
    data_root = Path(args.data_root)
    loaded = load_manifest_episodes(data_root, Path(args.manifest), args.manifest_split, args.episodes)
    backend = ArtifactJSONLBackend(Path(args.candidate_artifact))
    summary = load_json(args.summary)

    cache = SceneCache()
    episode_rows: List[Dict[str, Any]] = []
    candidate_rows: List[Dict[str, Any]] = []
    try:
        for item in loaded:
            episode = item.episode
            start = [float(v) for v in episode["start_position"]]
            scene = scene_path(data_root, episode["scene_id"])
            candidates = backend.candidates_for(item)
            label_candidate_correctness(item, candidates)
            rows = []
            for rank, candidate in enumerate(candidates, start=1):
                path = cache.distance(scene, start, candidate.visit_position)
                row = {
                    "episode_key": item.manifest_row.get("episode_key") if item.manifest_row else None,
                    "scene_id": episode.get("scene_id"),
                    "scene_key": Path(str(episode.get("scene_id"))).name.replace(".basis.glb", ""),
                    "query": episode.get("object_category"),
                    "candidate_id": candidate.candidate_id,
                    "rank": rank,
                    "score": candidate.score,
                    "correct": candidate.correct,
                    "correct_source": candidate.correct_source,
                    "reachable": path is not None,
                    "path_to_candidate": path,
                    "uses_gt_for_action": candidate.uses_gt_for_action,
                }
                rows.append(row)
                candidate_rows.append(row)

            reachable_correct = [row for row in rows if row["reachable"] and row["correct"] is True]
            reachable_wrong = [row for row in rows if row["reachable"] and row["correct"] is False]
            top = rows[0] if rows else None
            episode_rows.append(
                {
                    "episode_key": item.manifest_row.get("episode_key") if item.manifest_row else None,
                    "scene_id": episode.get("scene_id"),
                    "scene_key": Path(str(episode.get("scene_id"))).name.replace(".basis.glb", ""),
                    "query": episode.get("object_category"),
                    "candidate_count": len(rows),
                    "has_candidate": bool(rows),
                    "has_correct_candidate": any(row["correct"] is True for row in rows),
                    "has_wrong_candidate": any(row["correct"] is False for row in rows),
                    "has_reachable_candidate": any(row["reachable"] for row in rows),
                    "has_reachable_correct": bool(reachable_correct),
                    "has_reachable_wrong": bool(reachable_wrong),
                    "has_reachable_correct_and_wrong": bool(reachable_correct and reachable_wrong),
                    "top_candidate_reachable": bool(top and top["reachable"]),
                    "top_candidate_correct": top["correct"] if top else None,
                    "top_path_to_candidate": top["path_to_candidate"] if top else None,
                }
            )
    finally:
        cache.close()

    total_episodes = len(episode_rows)
    total_candidates = len(candidate_rows)
    labeled_candidates = sum(row["correct"] is not None for row in candidate_rows)
    reachable_candidates = sum(row["reachable"] for row in candidate_rows)

    by_scene: Dict[str, Dict[str, Any]] = {}
    for scene_key in sorted({row["scene_key"] for row in episode_rows}):
        rows = [row for row in episode_rows if row["scene_key"] == scene_key]
        by_scene[scene_key] = {
            "episodes": len(rows),
            "candidate_count_mean": mean(row["candidate_count"] for row in rows),
            "top_candidate_reachable_rate": rate(sum(row["top_candidate_reachable"] for row in rows), len(rows)),
            "reachable_correct_and_wrong_rate": rate(
                sum(row["has_reachable_correct_and_wrong"] for row in rows),
                len(rows),
            ),
        }

    query_counts = Counter(row["query"] for row in episode_rows)
    no_reobserve = None
    if summary is not None:
        no_reobserve = (summary.get("aggregate") or {}).get("NoReobserve")

    checks = {
        "all_episodes_have_candidates": all(row["has_candidate"] for row in episode_rows),
        "candidate_label_coverage_pass": rate(labeled_candidates, total_candidates) is not None
        and rate(labeled_candidates, total_candidates) >= args.min_label_coverage,
        "reachable_correct_and_wrong_pass": rate(
            sum(row["has_reachable_correct_and_wrong"] for row in episode_rows),
            total_episodes,
        )
        is not None
        and rate(sum(row["has_reachable_correct_and_wrong"] for row in episode_rows), total_episodes)
        >= args.min_reachable_ambiguity_rate,
        "no_reobserve_wrong_goal_pass": bool(
            no_reobserve
            and no_reobserve.get("wrong_goal_visit_rate") is not None
            and float(no_reobserve["wrong_goal_visit_rate"]) >= args.min_wrong_goal_rate
        ),
        "backend_uses_gt_for_action": backend.uses_gt_for_action,
    }
    checks["overall_pass"] = (
        checks["all_episodes_have_candidates"]
        and checks["candidate_label_coverage_pass"]
        and checks["reachable_correct_and_wrong_pass"]
        and checks["no_reobserve_wrong_goal_pass"]
        and checks["backend_uses_gt_for_action"] is False
    )

    return {
        "schema_version": "h001.artifact_coverage.v1",
        "manifest": args.manifest,
        "manifest_split": args.manifest_split,
        "candidate_artifact": args.candidate_artifact,
        "summary": args.summary,
        "episodes": total_episodes,
        "candidate_rows": total_candidates,
        "candidate_backend": backend.name,
        "candidate_backend_uses_gt_for_action": backend.uses_gt_for_action,
        "candidate_count_per_episode": {
            "min": min((row["candidate_count"] for row in episode_rows), default=0),
            "mean": mean(row["candidate_count"] for row in episode_rows),
            "max": max((row["candidate_count"] for row in episode_rows), default=0),
        },
        "candidate_label_coverage": rate(labeled_candidates, total_candidates),
        "candidate_reachable_rate": rate(reachable_candidates, total_candidates),
        "top_candidate_reachable_rate": rate(sum(row["top_candidate_reachable"] for row in episode_rows), total_episodes),
        "top_candidate_correct_rate": rate(sum(row["top_candidate_correct"] is True for row in episode_rows), total_episodes),
        "episodes_with_correct_candidate_rate": rate(sum(row["has_correct_candidate"] for row in episode_rows), total_episodes),
        "episodes_with_wrong_candidate_rate": rate(sum(row["has_wrong_candidate"] for row in episode_rows), total_episodes),
        "episodes_with_reachable_correct_rate": rate(sum(row["has_reachable_correct"] for row in episode_rows), total_episodes),
        "episodes_with_reachable_wrong_rate": rate(sum(row["has_reachable_wrong"] for row in episode_rows), total_episodes),
        "episodes_with_reachable_correct_and_wrong_rate": rate(
            sum(row["has_reachable_correct_and_wrong"] for row in episode_rows),
            total_episodes,
        ),
        "query_counts": dict(sorted(query_counts.items())),
        "by_scene": by_scene,
        "no_reobserve_summary": no_reobserve,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze artifact_jsonl candidate coverage on fixed H001 manifest rows.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-split", default="calibration")
    parser.add_argument("--episodes", type=int, default=50)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--summary", default=None)
    parser.add_argument("--out", required=True)
    parser.add_argument("--min-label-coverage", type=float, default=0.70)
    parser.add_argument("--min-reachable-ambiguity-rate", type=float, default=0.50)
    parser.add_argument("--min-wrong-goal-rate", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = analyze(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["checks"]["overall_pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
