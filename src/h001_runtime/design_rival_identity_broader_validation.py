import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_identity_broader_validation_design.v1"
DEFAULT_SEED = 20260526
DEFAULT_EXCLUDED_SCENES = [
    "DYehNKdT76V",
    "7MXmsvcQjpJ",
    "y9hTuugGdiq",
    "5cdEh9F2hJL",
    "CrMo8WxCyVb",
    "mL8ThkuaVTM",
]


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


def parse_source(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.parent.parent.name, path
    name, path = value.split("=", 1)
    return name.strip(), Path(path)


def stable_hash(seed: int, value: str) -> str:
    return hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest()


def scene_key_from_scene_id(value: Any) -> str:
    text = str(value or "")
    if not text:
        return "unknown"
    parts = [part for part in text.split("/") if part]
    if not parts:
        return "unknown"
    stem = parts[-1]
    if stem.endswith(".basis.glb"):
        return stem[: -len(".basis.glb")]
    return stem


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def group_candidates(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(path):
        if row.get("policy") != "NoReobserve":
            continue
        if row.get("candidate_uses_gt_for_action") is True:
            continue
        grouped[str(row["episode_key"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: int(item.get("candidate_rank") or 10**9))
    return grouped


def first_correct_rank(rows: Sequence[Dict[str, Any]]) -> Optional[int]:
    for row in rows:
        if row.get("candidate_correct") is True:
            return int(row.get("candidate_rank") or 0)
    return None


def top2_gap(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    if len(rows) < 2:
        return None
    top = rows[0].get("candidate_score")
    second = rows[1].get("candidate_score")
    if top is None or second is None:
        return None
    return float(top) - float(second)


def classify_episode(rows: Sequence[Dict[str, Any]]) -> str:
    top = rows[0]
    correct_count = sum(row.get("candidate_correct") is True for row in rows)
    wrong_count = sum(row.get("candidate_correct") is False for row in rows)
    top_wrong = top.get("candidate_correct") is False
    wrong_goal_top = top.get("wrong_goal_visit") is True
    if top_wrong and correct_count > 0 and wrong_goal_top:
        return "rival_identity_likely_wrong_goal"
    if top_wrong and correct_count > 0:
        return "rival_identity_likely_selected_wrong"
    if top_wrong and correct_count == 0:
        return "object_existence_or_backend_recall_negative"
    if correct_count > 0 and wrong_count > 0:
        return "rival_identity_control_selected_correct"
    return "low_priority"


def summarize_episode(source_name: str, path: Path, episode_key: str, rows: Sequence[Dict[str, Any]], seed: int) -> Dict[str, Any]:
    top = rows[0]
    correct_count = sum(row.get("candidate_correct") is True for row in rows)
    wrong_count = sum(row.get("candidate_correct") is False for row in rows)
    scene_key = scene_key_from_scene_id(top.get("scene_id"))
    query = str(top.get("query") or "unknown")
    episode_class = classify_episode(rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "source_name": source_name,
        "source_candidate_decisions": str(path),
        "episode_key": episode_key,
        "scene_id": top.get("scene_id"),
        "scene_key": scene_key,
        "query": query,
        "candidate_count": len(rows),
        "correct_candidate_count": correct_count,
        "wrong_candidate_count": wrong_count,
        "top_candidate_id": top.get("candidate_id"),
        "top_candidate_rank": top.get("candidate_rank"),
        "top_candidate_score": top.get("candidate_score"),
        "top_candidate_correct": top.get("candidate_correct"),
        "top_wrong_goal_visit": top.get("wrong_goal_visit"),
        "top_candidate_reachable": top.get("candidate_reachable"),
        "first_correct_rank": first_correct_rank(rows),
        "top2_score_gap": top2_gap(rows),
        "episode_class": episode_class,
        "selection_hash": stable_hash(seed, episode_key),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def class_priority(row: Dict[str, Any]) -> int:
    order = {
        "rival_identity_likely_wrong_goal": 0,
        "rival_identity_likely_selected_wrong": 1,
        "object_existence_or_backend_recall_negative": 2,
        "rival_identity_control_selected_correct": 3,
        "low_priority": 4,
    }
    return order.get(str(row.get("episode_class")), 99)


def row_priority(row: Dict[str, Any]) -> Tuple[int, int, int, str]:
    return (
        class_priority(row),
        int(row.get("first_correct_rank") or 10**6),
        0 if row.get("top_wrong_goal_visit") is True else 1,
        str(row.get("selection_hash")),
    )


def select_balanced(rows: Sequence[Dict[str, Any]], target_rows: int, max_rows_per_scene: int) -> List[Dict[str, Any]]:
    by_scene: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_scene[str(row["scene_key"])].append(row)
    for scene_rows in by_scene.values():
        scene_rows.sort(key=row_priority)
    scene_order = sorted(
        by_scene,
        key=lambda scene: (
            -sum(item["episode_class"] == "rival_identity_likely_wrong_goal" for item in by_scene[scene]),
            -sum(item["episode_class"] == "rival_identity_likely_selected_wrong" for item in by_scene[scene]),
            scene,
        ),
    )
    selected: List[Dict[str, Any]] = []
    scene_counts: Counter[str] = Counter()
    while len(selected) < target_rows:
        progressed = False
        for scene in scene_order:
            if len(selected) >= target_rows:
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
    selected.sort(key=row_priority)
    for index, row in enumerate(selected):
        row["selection_rank"] = index
    return selected


def summarize_rows(rows: Sequence[Dict[str, Any]], expected_request_rate: float, min_request_rows: int) -> Dict[str, Any]:
    scene_counts = Counter(str(row.get("scene_key")) for row in rows)
    query_counts = Counter(str(row.get("query")) for row in rows)
    class_counts = Counter(str(row.get("episode_class")) for row in rows)
    top_wrong = sum(row.get("top_candidate_correct") is False for row in rows)
    wrong_goal_top = sum(row.get("top_wrong_goal_visit") is True for row in rows)
    correct_wrong = sum(
        bool((row.get("correct_candidate_count") or 0) > 0 and (row.get("wrong_candidate_count") or 0) > 0)
        for row in rows
    )
    estimated_request_rows = int(round(len(rows) * expected_request_rate))
    return {
        "rows": len(rows),
        "scenes": len(scene_counts),
        "queries": len(query_counts),
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "episode_class_counts": dict(sorted(class_counts.items())),
        "top_wrong_rows": top_wrong,
        "top_wrong_goal_rows": wrong_goal_top,
        "rows_with_correct_and_wrong_candidates": correct_wrong,
        "expected_request_rate": expected_request_rate,
        "estimated_request_rows": estimated_request_rows,
        "estimated_request_rows_pass_minimum": estimated_request_rows >= min_request_rows,
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in rows),
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") is True for row in rows),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    excluded = set(args.exclude_scene)
    sources: List[Dict[str, Any]] = []
    source_rows: List[Dict[str, Any]] = []
    for source_name, path in map(parse_source, args.source):
        grouped = group_candidates(path)
        rows = [
            summarize_episode(source_name, path, episode_key, candidates, args.seed)
            for episode_key, candidates in grouped.items()
            if candidates
        ]
        filtered = [row for row in rows if row["scene_key"] not in excluded]
        sources.append(
            {
                "source_name": source_name,
                "path": str(path),
                "episode_rows": len(rows),
                "eligible_after_exclusion": len(filtered),
                "scenes_after_exclusion": len({row["scene_key"] for row in filtered}),
                "queries_after_exclusion": len({row["query"] for row in filtered}),
                "excluded_scene_overlap_rows": len(rows) - len(filtered),
                "summary_after_exclusion": summarize_rows(filtered, args.expected_request_rate, args.min_request_rows),
            }
        )
        source_rows.extend(filtered)

    preferred = [row for row in source_rows if row["source_name"] == args.preferred_source]
    pool = preferred if preferred else source_rows
    selected = select_balanced(pool, args.target_parent_rows, args.max_rows_per_scene)
    selected_summary = summarize_rows(selected, args.expected_request_rate, args.min_request_rows)
    gates = {
        "parent_rows_gate": len(selected) >= args.target_parent_rows,
        "scene_gate": selected_summary["scenes"] >= args.min_scenes,
        "query_gate": selected_summary["queries"] >= args.min_queries,
        "estimated_request_gate": selected_summary["estimated_request_rows"] >= args.min_request_rows,
        "top_wrong_goal_gate": selected_summary["top_wrong_goal_rows"] >= args.min_top_wrong_goal_rows,
        "correct_wrong_candidate_gate": selected_summary["rows_with_correct_and_wrong_candidates"]
        >= args.min_correct_wrong_rows,
        "no_gt_for_action": selected_summary["uses_gt_for_action"] is False,
    }
    gates["design_gate_passed"] = all(gates.values())
    payload = {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "design_name": args.design_name,
        "seed": args.seed,
        "excluded_scenes": list(args.exclude_scene),
        "preferred_source": args.preferred_source,
        "sources": sources,
        "selected_parent_summary": selected_summary,
        "gates": gates,
        "contract": {
            "parent_source": (
                "Use action-time candidate_decisions rows from the preferred source first; fall back to additional "
                "sources only if the preferred source cannot meet the parent-row gate."
            ),
            "preferred_source": args.preferred_source,
            "target_parent_rows": args.target_parent_rows,
            "max_rows_per_scene": args.max_rows_per_scene,
            "minimum_actual_request_rows_after_miner": args.min_request_rows,
            "minimum_actual_request_scenes_after_miner": args.min_scenes,
            "minimum_actual_request_queries_after_miner": args.min_queries,
            "expected_request_rate_from_prior_source": args.expected_request_rate,
            "actual_source_freeze_gate": [
                "request_rows >= 20",
                "request_scenes >= 5",
                "request_queries >= 3",
                "excluded_scene_overlap == 0",
                "action_evidence_forbidden_key_count == 0",
                "uses_gt_for_action == false",
            ],
            "post_observation_gate": [
                "wrong_goal_commit_rows == 0",
                "no_label_commit_rows == 0",
                "rival_identity_arbitration_rows reported",
                "object_existence_validation_rows reported",
                "wrong_goal_avoided_by_defer and success_lost_by_defer reported for object-existence rows",
            ],
        },
        "facts": [
            "The previous fresh source produced 6 request rows from 20 parent action-evidence rows.",
            "The broader design uses a larger scene-disjoint parent pool before any detector rerun.",
        ],
        "agent_inferences": [
            "A 72-row parent source is the smallest practical next design because the prior request rate was about 0.30.",
            (
                f"The preferred source {args.preferred_source} is used only if it meets the post-exclusion "
                "coverage gates while keeping HM3D ObjectNav semantics."
            ),
        ],
        "paper_claim_allowed": False,
        "paper_claim_status": "design_only_until_broader_split_miner_and_detector_validation_pass",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "rival_identity_broader_parent_rows.jsonl",
            "summary": "rival_identity_broader_design_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "rival_identity_broader_parent_rows.jsonl", selected)
    write_json(out_root / "rival_identity_broader_design_summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design broader source for rival-identity/object-existence validation.")
    parser.add_argument("--source", action="append", required=True, help="Name/path pair, e.g. risk=path.jsonl")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--design-name", default="rival_identity_broader_validation_v1")
    parser.add_argument("--preferred-source", default="risk_validation")
    parser.add_argument("--exclude-scene", action="append", default=list(DEFAULT_EXCLUDED_SCENES))
    parser.add_argument("--target-parent-rows", type=int, default=72)
    parser.add_argument("--max-rows-per-scene", type=int, default=8)
    parser.add_argument("--min-request-rows", type=int, default=20)
    parser.add_argument("--min-scenes", type=int, default=5)
    parser.add_argument("--min-queries", type=int, default=3)
    parser.add_argument("--min-top-wrong-goal-rows", type=int, default=16)
    parser.add_argument("--min-correct-wrong-rows", type=int, default=40)
    parser.add_argument("--expected-request-rate", type=float, default=0.30)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
