import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.dense_conflict_generalization_manifest.v1"
SPLIT_SCHEMA_VERSION = "h001.split_manifest.v1"
DEFAULT_SELECTED_SPLIT = "dense_conflict_generalization_v1"
DEFAULT_SEED = 20260523
DEFAULT_EXCLUDED_SCENES = ["y9hTuugGdiq"]

CONTRACT = {
    "minimum_rows": 20,
    "minimum_scenes": 5,
    "minimum_queries": 3,
    "minimum_source_selected_wrong_rows": 6,
    "minimum_rows_with_correct_and_wrong_candidates": 12,
    "minimum_no_reobserve_wrong_goal_rows": 8,
    "maximum_rows_per_scene": 3,
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def stable_hash(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def scene_key_from_scene_id(value: str) -> str:
    if not value:
        return "unknown"
    parts = [part for part in value.split("/") if part]
    if not parts:
        return "unknown"
    stem = parts[-1]
    if stem.endswith(".basis.glb"):
        return stem[: -len(".basis.glb")]
    return stem


def index_manifest_rows(paths: Sequence[Path]) -> Dict[str, Dict[str, Any]]:
    rows: Dict[str, Dict[str, Any]] = {}
    for path in paths:
        manifest = load_json(path)
        for row in manifest.get("rows", []):
            key = str(row.get("episode_key"))
            if key:
                rows[key] = dict(row)
    return rows


def group_candidate_decisions(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(path):
        if row.get("policy") != "NoReobserve":
            continue
        if row.get("candidate_uses_gt_for_action") is True:
            continue
        key = str(row.get("episode_key") or "")
        if key:
            grouped[key].append(dict(row))
    for rows in grouped.values():
        rows.sort(key=lambda item: int(item.get("candidate_rank") or 10**9))
    return grouped


def first_correct_rank(candidates: Sequence[Dict[str, Any]]) -> Optional[int]:
    for candidate in candidates:
        if candidate.get("candidate_correct") is True:
            return int(candidate.get("candidate_rank") or 0)
    return None


def score_gap(candidates: Sequence[Dict[str, Any]]) -> Optional[float]:
    if len(candidates) < 2:
        return None
    top = candidates[0].get("candidate_score")
    second = candidates[1].get("candidate_score")
    if top is None or second is None:
        return None
    return float(top) - float(second)


def compact_candidate(candidate: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if candidate is None:
        return None
    return {
        "candidate_id": candidate.get("candidate_id"),
        "candidate_rank": candidate.get("candidate_rank"),
        "candidate_score": candidate.get("candidate_score"),
        "candidate_correct": candidate.get("candidate_correct"),
        "candidate_correct_source": candidate.get("candidate_correct_source"),
        "candidate_position": candidate.get("candidate_position"),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "wrong_goal_visit": candidate.get("wrong_goal_visit"),
        "uses_gt_for_action": candidate.get("candidate_uses_gt_for_action"),
    }


def summarize_episode(
    *,
    source_name: str,
    coverage_path: Path,
    manifest_row: Dict[str, Any],
    candidates: List[Dict[str, Any]],
) -> Dict[str, Any]:
    top = candidates[0] if candidates else None
    correct = [candidate for candidate in candidates if candidate.get("candidate_correct") is True]
    wrong = [candidate for candidate in candidates if candidate.get("candidate_correct") is False]
    correct_and_wrong = bool(correct and wrong)
    source_selected_wrong = bool(top and top.get("candidate_correct") is False and correct)
    no_reobserve_wrong_goal = bool(top and top.get("wrong_goal_visit") is True and correct)
    query = str(manifest_row.get("target_or_query") or (top or {}).get("query") or "unknown")
    scene_key = str(manifest_row.get("scene_key") or scene_key_from_scene_id(str(manifest_row.get("scene_id") or "")))
    return {
        "source_name": source_name,
        "coverage_path": str(coverage_path),
        "episode_key": str(manifest_row.get("episode_key")),
        "scene_key": scene_key,
        "scene_id": manifest_row.get("scene_id"),
        "query": query,
        "candidate_count": len(candidates),
        "correct_candidate_count": len(correct),
        "wrong_candidate_count": len(wrong),
        "rows_with_correct_and_wrong_candidates": correct_and_wrong,
        "source_selected_wrong_candidate": source_selected_wrong,
        "no_reobserve_wrong_goal_with_correct_present": no_reobserve_wrong_goal,
        "first_correct_rank": first_correct_rank(candidates),
        "top_candidate_correct": None if top is None else top.get("candidate_correct"),
        "top_candidate_id": None if top is None else top.get("candidate_id"),
        "top_candidate_score": None if top is None else top.get("candidate_score"),
        "top2_score_gap": score_gap(candidates),
        "correct_candidate_ids": [str(candidate.get("candidate_id")) for candidate in correct[:10]],
        "wrong_candidate_ids": [str(candidate.get("candidate_id")) for candidate in wrong[:10]],
        "top_candidates": [compact_candidate(candidate) for candidate in candidates[:5]],
        "uses_gt_for_action": any(candidate.get("candidate_uses_gt_for_action") is True for candidate in candidates),
        "uses_gt_for_analysis": True,
    }


def conflict_class(summary: Dict[str, Any]) -> str:
    if summary["source_selected_wrong_candidate"] and summary["no_reobserve_wrong_goal_with_correct_present"]:
        return "wrong_goal_baseline_selected_wrong_correct_present"
    if summary["source_selected_wrong_candidate"]:
        return "selected_wrong_positive_correct_present"
    if summary["rows_with_correct_and_wrong_candidates"] and summary["top_candidate_correct"] is True:
        return "correct_and_wrong_positive_selected_correct"
    if summary["correct_candidate_count"] > 0:
        return "correct_present_without_wrong_candidate"
    return "backend_recall_failure_negative_slice"


def priority(summary: Dict[str, Any], seed: int) -> Tuple[int, int, int, int, str]:
    return (
        0 if summary["source_selected_wrong_candidate"] else 1,
        0 if summary["no_reobserve_wrong_goal_with_correct_present"] else 1,
        0 if summary["rows_with_correct_and_wrong_candidates"] else 1,
        int(summary["first_correct_rank"] or 10**6),
        stable_hash(seed, summary["episode_key"]),
    )


def candidate_pool(
    *,
    source_name: str,
    manifest_rows: Dict[str, Dict[str, Any]],
    coverage_path: Path,
    excluded_scene_keys: Sequence[str],
) -> List[Dict[str, Any]]:
    grouped = group_candidate_decisions(coverage_path)
    excluded = set(excluded_scene_keys)
    rows: List[Dict[str, Any]] = []
    for key, candidates in grouped.items():
        manifest_row = manifest_rows.get(key)
        if manifest_row is None:
            continue
        summary = summarize_episode(
            source_name=source_name,
            coverage_path=coverage_path,
            manifest_row=manifest_row,
            candidates=candidates,
        )
        if summary["scene_key"] in excluded:
            continue
        rows.append({"manifest_row": manifest_row, "summary": summary})
    return rows


def select_rows(pool: Sequence[Dict[str, Any]], total_rows: int, max_rows_per_scene: int, seed: int) -> List[Dict[str, Any]]:
    by_scene: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for item in pool:
        summary = item["summary"]
        if summary["correct_candidate_count"] <= 0:
            continue
        if not summary["rows_with_correct_and_wrong_candidates"]:
            continue
        by_scene[summary["scene_key"]].append(item)

    for scene_items in by_scene.values():
        scene_items.sort(key=lambda item: priority(item["summary"], seed))

    selected: List[Dict[str, Any]] = []
    scene_order = sorted(
        by_scene,
        key=lambda scene: (
            -sum(item["summary"]["source_selected_wrong_candidate"] for item in by_scene[scene]),
            -sum(item["summary"]["no_reobserve_wrong_goal_with_correct_present"] for item in by_scene[scene]),
            scene,
        ),
    )
    scene_counts: Counter[str] = Counter()
    while len(selected) < total_rows:
        progressed = False
        for scene in scene_order:
            if len(selected) >= total_rows:
                break
            if scene_counts[scene] >= max_rows_per_scene:
                continue
            if not by_scene[scene]:
                continue
            selected.append(by_scene[scene].pop(0))
            scene_counts[scene] += 1
            progressed = True
        if not progressed:
            break
    selected.sort(key=lambda item: priority(item["summary"], seed))
    return selected


def build_manifest_row(item: Dict[str, Any], selected_split: str, seed: int, rank: int) -> Dict[str, Any]:
    source = dict(item["manifest_row"])
    summary = item["summary"]
    row = dict(source)
    row["source_selected_split"] = source.get("selected_split")
    row["selected_split"] = selected_split
    row["selection_rank"] = rank
    row["selection_seed"] = seed
    row["deterministic_hash"] = stable_hash(seed, f"{selected_split}:{row['episode_key']}")
    row["dense_conflict_generalization_schema_version"] = SCHEMA_VERSION
    row["dense_conflict_generalization_role"] = "primary_generalization"
    row["dense_conflict_role"] = "primary"
    row["dense_conflict_class"] = conflict_class(summary)
    row["dense_conflict_source_name"] = summary["source_name"]
    row["dense_conflict_source_coverage_path"] = summary["coverage_path"]
    row["dense_conflict_candidate_count"] = summary["candidate_count"]
    row["dense_conflict_correct_candidate_count"] = summary["correct_candidate_count"]
    row["dense_conflict_wrong_candidate_count"] = summary["wrong_candidate_count"]
    row["dense_conflict_positive_support_candidate_count"] = summary["candidate_count"]
    row["dense_conflict_correct_positive_support_candidate_count"] = summary["correct_candidate_count"]
    row["dense_conflict_wrong_positive_support_candidate_count"] = summary["wrong_candidate_count"]
    row["dense_conflict_selected_wrong_positive_support"] = summary["source_selected_wrong_candidate"]
    row["dense_conflict_rows_with_correct_and_wrong_candidates"] = summary["rows_with_correct_and_wrong_candidates"]
    row["dense_conflict_source_selected_wrong_candidate"] = summary["source_selected_wrong_candidate"]
    row["dense_conflict_no_reobserve_wrong_goal_with_correct_present"] = summary[
        "no_reobserve_wrong_goal_with_correct_present"
    ]
    row["dense_conflict_first_correct_rank"] = summary["first_correct_rank"]
    row["dense_conflict_top_candidate_correct"] = summary["top_candidate_correct"]
    row["dense_conflict_top_candidate_id"] = summary["top_candidate_id"]
    row["dense_conflict_top_candidate_score"] = summary["top_candidate_score"]
    row["dense_conflict_top2_score_gap"] = summary["top2_score_gap"]
    row["dense_conflict_correct_candidate_ids"] = summary["correct_candidate_ids"]
    row["dense_conflict_wrong_candidate_ids"] = summary["wrong_candidate_ids"]
    row["dense_conflict_top_candidates"] = summary["top_candidates"]
    row["dense_conflict_positive_support_proxy"] = "candidate_correctness_labels_from_coverage_sanity"
    row["uses_gt_for_action"] = False
    row["uses_gt_for_analysis"] = True
    return row


def count_rows(rows: Sequence[Dict[str, Any]], field: str) -> int:
    return sum(1 for row in rows if row.get(field) is True)


def contract_summary(rows: Sequence[Dict[str, Any]], contract: Dict[str, int]) -> Dict[str, Any]:
    scene_counts = Counter(str(row.get("scene_key")) for row in rows)
    query_counts = Counter(str(row.get("target_or_query")) for row in rows)
    selected_wrong = count_rows(rows, "dense_conflict_source_selected_wrong_candidate")
    correct_wrong = count_rows(rows, "dense_conflict_rows_with_correct_and_wrong_candidates")
    wrong_goal = count_rows(rows, "dense_conflict_no_reobserve_wrong_goal_with_correct_present")
    checks = {
        "minimum_rows": len(rows) >= contract["minimum_rows"],
        "minimum_scenes": len(scene_counts) >= contract["minimum_scenes"],
        "minimum_queries": len(query_counts) >= contract["minimum_queries"],
        "minimum_source_selected_wrong_rows": selected_wrong >= contract["minimum_source_selected_wrong_rows"],
        "minimum_rows_with_correct_and_wrong_candidates": correct_wrong
        >= contract["minimum_rows_with_correct_and_wrong_candidates"],
        "minimum_no_reobserve_wrong_goal_rows": wrong_goal >= contract["minimum_no_reobserve_wrong_goal_rows"],
        "maximum_rows_per_scene": all(count <= contract["maximum_rows_per_scene"] for count in scene_counts.values()),
    }
    return {
        "checks": checks,
        "passes_contract": all(checks.values()),
        "rows": len(rows),
        "scenes": len(scene_counts),
        "queries": len(query_counts),
        "source_selected_wrong_rows": selected_wrong,
        "rows_with_correct_and_wrong_candidates": correct_wrong,
        "no_reobserve_wrong_goal_rows": wrong_goal,
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "class_counts": dict(sorted(Counter(str(row.get("dense_conflict_class")) for row in rows).items())),
        "missing_to_contract": {
            "rows": max(0, contract["minimum_rows"] - len(rows)),
            "scenes": max(0, contract["minimum_scenes"] - len(scene_counts)),
            "queries": max(0, contract["minimum_queries"] - len(query_counts)),
            "source_selected_wrong_rows": max(0, contract["minimum_source_selected_wrong_rows"] - selected_wrong),
            "rows_with_correct_and_wrong_candidates": max(
                0,
                contract["minimum_rows_with_correct_and_wrong_candidates"] - correct_wrong,
            ),
            "no_reobserve_wrong_goal_rows": max(0, contract["minimum_no_reobserve_wrong_goal_rows"] - wrong_goal),
        },
    }


def pool_summary(pool: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    summaries = [item["summary"] for item in pool]
    return {
        "rows": len(summaries),
        "scenes": len(Counter(summary["scene_key"] for summary in summaries)),
        "queries": len(Counter(summary["query"] for summary in summaries)),
        "rows_with_correct_and_wrong_candidates": sum(
            1 for summary in summaries if summary["rows_with_correct_and_wrong_candidates"]
        ),
        "source_selected_wrong_rows": sum(1 for summary in summaries if summary["source_selected_wrong_candidate"]),
        "no_reobserve_wrong_goal_rows": sum(
            1 for summary in summaries if summary["no_reobserve_wrong_goal_with_correct_present"]
        ),
        "scene_counts": dict(sorted(Counter(summary["scene_key"] for summary in summaries).items())),
        "query_counts": dict(sorted(Counter(summary["query"] for summary in summaries).items())),
    }


def verify_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    rows = list(manifest.get("rows", []))
    keys = [str(row.get("episode_key")) for row in rows]
    duplicate_keys = sorted(key for key, count in Counter(keys).items() if count > 1)
    action_gt_rows = [row["episode_key"] for row in rows if row.get("uses_gt_for_action") is True]
    summary = contract_summary(rows, manifest["contract"])
    ok = not duplicate_keys and not action_gt_rows and summary["passes_contract"]
    return {
        "ok": ok,
        "manifest": manifest.get("selected_split"),
        "manifest_status": manifest.get("manifest_status"),
        "rows": len(rows),
        "unique_episode_keys": len(set(keys)),
        "duplicate_episode_keys": duplicate_keys,
        "action_gt_rows": action_gt_rows,
        "contract_summary": summary,
        "detector_job_allowed": bool(manifest.get("detector_job_allowed")),
        "next_gate": manifest.get("next_gate"),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    manifest_paths = [Path(path) for path in args.source_manifest]
    manifest_rows = index_manifest_rows(manifest_paths)
    pool = candidate_pool(
        source_name=str(args.source_name),
        manifest_rows=manifest_rows,
        coverage_path=Path(args.coverage_decisions),
        excluded_scene_keys=list(args.exclude_scene),
    )
    selected = select_rows(
        pool,
        total_rows=int(args.total_rows),
        max_rows_per_scene=int(args.max_rows_per_scene),
        seed=int(args.seed),
    )
    output_rows = [
        build_manifest_row(item, str(args.selected_split), int(args.seed), rank)
        for rank, item in enumerate(selected)
    ]
    summary = contract_summary(output_rows, CONTRACT)
    status = "frozen_pending_recall_gate" if summary["passes_contract"] else "draft_needs_more_rows"
    manifest = {
        "manifest_schema_version": SPLIT_SCHEMA_VERSION,
        "dense_conflict_generalization_schema_version": SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "creation_command": "python -m h001_runtime.build_dense_conflict_generalization_manifest",
        "selected_split": str(args.selected_split),
        "manifest_status": status,
        "selection_seed": int(args.seed),
        "source_manifests": [str(path) for path in manifest_paths],
        "source_coverage_decisions": str(args.coverage_decisions),
        "source_name": str(args.source_name),
        "source_candidate_artifact": str(args.source_candidate_artifact),
        "excluded_scene_keys": list(args.exclude_scene),
        "selection_strategy": {
            "name": "scene_disjoint_first_eval_style_round_robin",
            "source_policy": "NoReobserve",
            "requires_non_gt_candidates": True,
            "requires_correct_and_wrong_candidates": True,
            "priority": [
                "source_selected_wrong_candidate",
                "no_reobserve_wrong_goal_with_correct_present",
                "rows_with_correct_and_wrong_candidates",
                "first_correct_rank",
                "stable_hash",
            ],
            "maximum_rows_per_scene": int(args.max_rows_per_scene),
        },
        "contract": dict(CONTRACT),
        "pool_summary": pool_summary(pool),
        "contract_summary": summary,
        "split_counts": {str(args.selected_split): len(output_rows)},
        "scene_counts": summary["scene_counts"],
        "query_counts": summary["query_counts"],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "detector_job_allowed": False,
        "next_gate": (
            "run non-GT candidate recall gate on this frozen manifest; detector/association validation remains "
            "blocked until that gate passes"
        ),
        "rows": output_rows,
    }
    write_json(Path(args.out), manifest)
    verify = verify_manifest(manifest)
    write_json(Path(args.verify_out), verify)
    return {"manifest": str(args.out), "verify": str(args.verify_out), "summary": verify}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build H001 dense conflict generalization split manifest.")
    parser.add_argument(
        "--source-manifest",
        action="append",
        default=[],
        help="Source split manifest containing candidate episode rows. Can be repeated.",
    )
    parser.add_argument("--coverage-decisions", required=True)
    parser.add_argument("--source-name", default="first_eval_replacement_spatial_nms_p97_k20")
    parser.add_argument("--source-candidate-artifact", required=True)
    parser.add_argument("--selected-split", default=DEFAULT_SELECTED_SPLIT)
    parser.add_argument("--exclude-scene", action="append", default=list(DEFAULT_EXCLUDED_SCENES))
    parser.add_argument("--total-rows", type=int, default=CONTRACT["minimum_rows"])
    parser.add_argument("--max-rows-per-scene", type=int, default=CONTRACT["maximum_rows_per_scene"])
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--out", required=True)
    parser.add_argument("--verify-out", required=True)
    args = parser.parse_args()
    if not args.source_manifest:
        raise SystemExit("--source-manifest is required")
    return args


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
