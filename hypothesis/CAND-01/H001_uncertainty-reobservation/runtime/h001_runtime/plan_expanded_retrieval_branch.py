import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_plan.v1"
POLICY_NAME = "ExpandedRetrievalCandidateSet"
FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "selected_for_goal",
    "wrong_goal_visit",
    "success",
    "evaluation_only_candidate_correct",
    "evaluation_only_goal_visit",
    "evaluation_only_wrong_goal_visit",
    "evaluation_only_wasted_path_from_candidate",
    "parent_episode_class_for_analysis",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) != 3:
        return None
    values = [safe_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return [float(item) for item in values]


def horizontal_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def request_id_sort_key(row: Dict[str, Any]) -> Tuple[int, str]:
    request_id = str(row.get("rival_identity_request_id") or "")
    suffix = request_id.split(":")[-1]
    return (int(suffix), request_id) if suffix.isdigit() else (999999, request_id)


def action_evidence_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        episode_key = row.get("episode_key")
        query = row.get("query")
        if episode_key is not None and query is not None:
            indexed[(str(episode_key), str(query))] = row
    return indexed


def rank_candidates(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (dict(candidate) for candidate in candidates),
        key=lambda candidate: (
            safe_int(candidate.get("semantic_rank")),
            -(safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score")) or -math.inf),
            str(candidate.get("candidate_id")),
        ),
    )


def candidate_position(candidate: Dict[str, Any]) -> Optional[List[float]]:
    return vector3(candidate.get("visit_position")) or vector3(candidate.get("position"))


def select_rank_band(candidates: Sequence[Dict[str, Any]], rank_pattern: Sequence[int]) -> List[Dict[str, Any]]:
    selected: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for rank in rank_pattern:
        if rank < 1 or rank > len(candidates):
            continue
        candidate = dict(candidates[rank - 1])
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id not in seen:
            selected.append(candidate)
            seen.add(candidate_id)
    return selected


def select_spatial_fill(
    candidates: Sequence[Dict[str, Any]],
    selected: List[Dict[str, Any]],
    budget: int,
) -> List[Dict[str, Any]]:
    seen = {str(candidate.get("candidate_id")) for candidate in selected}
    while len(selected) < budget:
        best: Optional[Tuple[Tuple[float, int, float], Dict[str, Any]]] = None
        selected_positions = [
            position for position in (candidate_position(candidate) for candidate in selected) if position is not None
        ]
        for candidate in candidates:
            candidate_id = str(candidate.get("candidate_id"))
            if candidate_id in seen:
                continue
            position = candidate_position(candidate)
            if position is None:
                continue
            min_distance = min(
                (horizontal_distance(position, selected_position) for selected_position in selected_positions),
                default=0.0,
            )
            key = (
                min_distance,
                -safe_int(candidate.get("semantic_rank")),
                safe_float(candidate.get("support_score")) or safe_float(candidate.get("semantic_score")) or 0.0,
            )
            if best is None or key > best[0]:
                best = (key, dict(candidate))
        if best is None:
            break
        selected.append(best[1])
        seen.add(str(best[1].get("candidate_id")))
    return selected


def select_candidates(
    candidates: Sequence[Dict[str, Any]],
    *,
    min_budget: int,
    max_budget: int,
    rank_pattern: Sequence[int],
) -> Tuple[List[Dict[str, Any]], str]:
    ranked = rank_candidates(candidates)
    finite_ranked = [candidate for candidate in ranked if candidate_position(candidate) is not None]
    selected = select_rank_band(finite_ranked, rank_pattern)
    selected = select_spatial_fill(finite_ranked, selected, max_budget)
    if len(selected) < min_budget:
        selected = select_spatial_fill(finite_ranked, selected, min_budget)
    return selected[:max_budget], "semantic_rank_band_then_spatial_diversity"


def candidate_snapshot(candidate: Dict[str, Any], selection_rank: int) -> Dict[str, Any]:
    position = vector3(candidate.get("position"))
    visit_position = vector3(candidate.get("visit_position"))
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "candidate_backend": candidate.get("candidate_backend"),
        "category": candidate.get("category"),
        "selection_rank": selection_rank,
        "semantic_rank": candidate.get("semantic_rank"),
        "score": candidate.get("score"),
        "semantic_score": candidate.get("semantic_score"),
        "support_score": candidate.get("support_score"),
        "positive_support": bool(candidate.get("positive_support")),
        "candidate_reachable": candidate.get("candidate_reachable"),
        "path_to_candidate": candidate.get("path_to_candidate"),
        "position": position,
        "visit_position": visit_position,
        "uses_gt_for_action": False,
    }


def forbidden_key_count(rows: Sequence[Dict[str, Any]]) -> int:
    count = 0
    for row in rows:
        for key in FORBIDDEN_ACTION_KEYS:
            if key in row:
                count += 1
    return count


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    routes_all = load_jsonl(Path(args.router_rows))
    action_rows = load_jsonl(Path(args.action_evidence_rows))
    action_by_key = action_evidence_index(action_rows)
    request_rows = [
        row
        for row in routes_all
        if row.get("revision_action") == "request_expanded_retrieval"
    ]
    request_rows.sort(key=request_id_sort_key)

    candidate_set_rows: List[Dict[str, Any]] = []
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    candidate_counts: List[int] = []
    duplicate_rows = 0
    nonfinite_candidate_rows = 0
    selection_mode_counts: Counter[str] = Counter()

    for request_index, router in enumerate(request_rows):
        key = (str(router.get("episode_key")), str(router.get("query")))
        action = action_by_key.get(key)
        if action is None:
            skipped_rows.append(
                {
                    "rival_identity_request_id": router.get("rival_identity_request_id"),
                    "episode_key": router.get("episode_key"),
                    "query": router.get("query"),
                    "skip_reason": "missing_action_evidence",
                    "uses_gt_for_action": False,
                }
            )
            continue
        candidates = list(action.get("candidate_evidence") or [])
        selected, selection_mode = select_candidates(
            candidates,
            min_budget=int(args.min_candidates_per_request),
            max_budget=int(args.max_candidates_per_request),
            rank_pattern=list(args.rank_band_pattern),
        )
        selection_mode_counts[selection_mode] += 1
        selected_ids = [str(candidate.get("candidate_id")) for candidate in selected]
        duplicate_rows += max(0, len(selected_ids) - len(set(selected_ids)))
        nonfinite_candidate_rows += sum(1 for candidate in selected if candidate_position(candidate) is None)
        candidate_counts.append(len(selected))

        candidate_snapshots = [
            candidate_snapshot(candidate, selection_rank=rank)
            for rank, candidate in enumerate(selected, start=1)
        ]
        candidate_set_row = {
            "schema_version": SCHEMA_VERSION,
            "run_id": str(args.run_id),
            "contract_name": str(contract.get("contract_name")),
            "policy": POLICY_NAME,
            "rival_identity_request_id": router.get("rival_identity_request_id"),
            "episode_key": router.get("episode_key"),
            "scene_id": action.get("scene_id"),
            "scene_key": router.get("scene_key") or action.get("scene_key"),
            "query": router.get("query"),
            "revision_action": router.get("revision_action"),
            "revision_branch": router.get("revision_branch"),
            "revision_reason": router.get("revision_reason"),
            "source_reason": router.get("source_reason"),
            "source_candidate_count": action.get("candidate_count"),
            "source_positive_support_candidate_count": action.get("positive_support_candidate_count"),
            "expanded_candidate_count": len(selected),
            "expanded_candidate_ids": selected_ids,
            "selection_mode": selection_mode,
            "candidate_budget_min": int(args.min_candidates_per_request),
            "candidate_budget_max": int(args.max_candidates_per_request),
            "rank_band_pattern": list(args.rank_band_pattern),
            "expanded_candidates": candidate_snapshots,
            "commit_after_retrieve": False,
            "terminal_commit_allowed": False,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": False,
        }
        candidate_set_rows.append(candidate_set_row)

        for rank, candidate in enumerate(candidate_snapshots, start=1):
            plan_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "run_id": str(args.run_id),
                    "contract_name": str(contract.get("contract_name")),
                    "policy": POLICY_NAME,
                    "viewpoint_policy": POLICY_NAME,
                    "viewpoint_id": f"expanded_retrieval:{router.get('rival_identity_request_id')}:{rank}",
                    "rival_identity_request_id": router.get("rival_identity_request_id"),
                    "episode_key": router.get("episode_key"),
                    "scene_id": action.get("scene_id"),
                    "scene_key": router.get("scene_key") or action.get("scene_key"),
                    "query": router.get("query"),
                    "candidate_id": candidate["candidate_id"],
                    "candidate_ids": selected_ids,
                    "expanded_candidate_rank": rank,
                    "expanded_candidate_count": len(selected),
                    "expanded_selection_mode": selection_mode,
                    "target_position": candidate.get("position"),
                    "target_visit_position": candidate.get("visit_position"),
                    "viewpoint_position": candidate.get("visit_position"),
                    "viewpoint_rotation": [0.0, 0.0, 0.0, 1.0],
                    "commit_after_retrieve": False,
                    "terminal_commit_allowed": False,
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": False,
                }
            )

    expanded_candidate_rows = len(plan_rows)
    expected_request_rows = int(contract["source"]["expected_request_rows"])
    request_rows_min = int(contract["diagnostic_gates"]["source_gate"]["request_rows_min"])
    expanded_rows_min = int(contract["diagnostic_gates"]["candidate_set_gate"]["expanded_candidate_rows_min"])
    expanded_per_request_min = int(
        contract["diagnostic_gates"]["candidate_set_gate"]["expanded_candidates_per_request_min"]
    )
    duplicate_rate_max = float(contract["diagnostic_gates"]["candidate_set_gate"]["duplicate_candidate_id_rate_max"])
    nonfinite_rate_max = float(contract["diagnostic_gates"]["candidate_set_gate"]["nonfinite_position_rate_max"])
    duplicate_rate = ratio(duplicate_rows, expanded_candidate_rows) or 0.0
    nonfinite_rate = ratio(nonfinite_candidate_rows, expanded_candidate_rows) or 0.0
    forbidden_count = forbidden_key_count(plan_rows) + forbidden_key_count(candidate_set_rows)
    gate = {
        "expected_request_rows_pass": len(request_rows) == expected_request_rows,
        "request_rows_min_pass": len(request_rows) >= request_rows_min,
        "no_skipped_rows_pass": len(skipped_rows) == 0,
        "expanded_candidate_rows_min_pass": expanded_candidate_rows >= expanded_rows_min,
        "expanded_candidates_per_request_min_pass": bool(candidate_counts)
        and min(candidate_counts) >= expanded_per_request_min,
        "duplicate_candidate_id_rate_pass": duplicate_rate <= duplicate_rate_max,
        "nonfinite_position_rate_pass": nonfinite_rate <= nonfinite_rate_max,
        "action_evidence_forbidden_key_count_pass": forbidden_count == 0,
        "no_gt_action_pass": not any(row.get("uses_gt_for_action") is True for row in plan_rows + candidate_set_rows),
    }
    gate["passes_expanded_retrieval_planner_gate"] = all(gate.values())
    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "router_rows": str(args.router_rows),
        "action_evidence_rows": str(args.action_evidence_rows),
        "expected_request_rows": expected_request_rows,
        "request_rows": len(request_rows),
        "candidate_set_rows": len(candidate_set_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "expanded_candidate_count_min": min(candidate_counts) if candidate_counts else None,
        "expanded_candidate_count_max": max(candidate_counts) if candidate_counts else None,
        "expanded_candidate_count_mean": (sum(candidate_counts) / len(candidate_counts)) if candidate_counts else None,
        "duplicate_candidate_id_rows": duplicate_rows,
        "duplicate_candidate_id_rate": duplicate_rate,
        "nonfinite_candidate_rows": nonfinite_candidate_rows,
        "nonfinite_position_rate": nonfinite_rate,
        "action_evidence_forbidden_key_count": forbidden_count,
        "selection_mode_counts": dict(sorted(selection_mode_counts.items())),
        "gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "candidate_set": "expanded_retrieval_candidate_set.jsonl",
            "plan_rows": "expanded_retrieval_plan.jsonl",
            "skipped_rows": "expanded_retrieval_skipped.jsonl",
            "summary": "expanded_retrieval_summary.json",
        },
    }

    write_jsonl(out_root / "expanded_retrieval_candidate_set.jsonl", candidate_set_rows)
    write_jsonl(out_root / "expanded_retrieval_plan.jsonl", plan_rows)
    write_jsonl(out_root / "expanded_retrieval_skipped.jsonl", skipped_rows)
    write_json(out_root / "expanded_retrieval_summary.json", summary)
    return summary


def parse_int_list(text: str) -> List[int]:
    values = [int(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan expanded retrieval candidate sets for H001.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--router-rows", required=True)
    parser.add_argument("--action-evidence-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--run-id", default="h001_expanded_retrieval_branch_v1")
    parser.add_argument("--min-candidates-per-request", type=int, default=6)
    parser.add_argument("--max-candidates-per-request", type=int, default=10)
    parser.add_argument("--rank-band-pattern", type=parse_int_list, default=[1, 2, 3, 4, 6, 10])
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["passes_expanded_retrieval_planner_gate"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
