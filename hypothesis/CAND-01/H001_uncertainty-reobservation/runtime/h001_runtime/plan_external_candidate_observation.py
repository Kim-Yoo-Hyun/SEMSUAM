import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.external_candidate_observation_plan.v1"
POLICY_NAME = "ExternalCandidateObservation"


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


def finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def finite_vector(value: Any, length: int = 3) -> bool:
    if not isinstance(value, list) or len(value) != length:
        return False
    return all(finite_float(item) is not None for item in value)


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def artifact_index(path: Path) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    indexed: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        scene_id = str(row.get("scene_id"))
        query = str(row.get("query"))
        candidates = [dict(candidate) for candidate in row.get("candidates") or []]
        candidates.sort(
            key=lambda candidate: finite_float(candidate.get("score")) or -math.inf,
            reverse=True,
        )
        indexed[(scene_id, query)] = candidates
    return indexed


def feature_index(path: Optional[Path]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_jsonl(path):
        indexed[(str(row.get("episode_key")), str(row.get("candidate_id")))] = row
    return indexed


def candidate_rank(candidate_id: str) -> Optional[int]:
    try:
        return int(candidate_id.rsplit(":", 1)[-1]) + 1
    except (TypeError, ValueError):
        return None


def top_confirm(row: Dict[str, Any]) -> float:
    return float((row.get("pair_v3_top_features") or {}).get("confirm_score") or 0.0)


def alt_confirm(row: Dict[str, Any]) -> float:
    return float((row.get("pair_v3_alt_features") or {}).get("confirm_score") or 0.0)


def external_trigger(row: Dict[str, Any], args: argparse.Namespace) -> Tuple[bool, str]:
    if row.get("pair_v3_defer") is not True:
        return False, "pair_v3_already_committed_or_not_deferred"

    action = str(row.get("pair_v3_action"))
    max_confirm = max(top_confirm(row), alt_confirm(row))
    confirm_gap = abs(float(row.get("pair_v3_confirm_gap_alt_minus_top") or 0.0))
    top_rejected = bool(row.get("pair_v3_top_rejection_evidence"))

    if action == "pair_v3_defer_no_valid_candidate_or_external_search":
        return True, "pair_v3_no_valid_pair_state"
    if action != "pair_v3_defer_rank_ambiguous" and max_confirm < float(args.max_pair_confirm_for_weak_external):
        return True, "weak_pair_evidence_after_pair_observation"
    if (
        action == "pair_v3_defer_rank_ambiguous"
        and top_rejected
        and confirm_gap <= float(args.max_rank_ambiguous_confirm_gap_for_external)
    ):
        return True, "rank_ambiguous_and_top_rejected"
    return False, "pair_defer_but_external_gate_not_met"


def selectable_external_candidates(
    candidates: List[Dict[str, Any]],
    excluded_ids: set[str],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    selected = []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id in excluded_ids:
            continue
        if args.require_navigable_visit and candidate.get("visit_position_navigable") is not True:
            continue
        if not finite_vector(candidate.get("visit_position")):
            continue
        selected.append(candidate)
    return selected


def rank_band_order(candidates: List[Dict[str, Any]], rank_pattern: List[int]) -> List[Dict[str, Any]]:
    ordered: List[Dict[str, Any]] = []
    seen: set[str] = set()

    for rank in rank_pattern:
        if rank < 1 or rank > len(candidates):
            continue
        candidate = candidates[rank - 1]
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id in seen:
            continue
        ordered.append(candidate)
        seen.add(candidate_id)

    for candidate in candidates:
        candidate_id = str(candidate.get("candidate_id"))
        if candidate_id in seen:
            continue
        ordered.append(candidate)
        seen.add(candidate_id)
    return ordered


def rank_external_candidates(
    candidates: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    if args.external_selection_mode == "semantic_rank":
        return list(candidates)
    if args.external_selection_mode == "rank_bands":
        return rank_band_order(candidates, args.rank_band_pattern)
    raise ValueError(f"unknown external selection mode: {args.external_selection_mode}")


def candidate_snapshot(
    candidate: Dict[str, Any],
    feature: Optional[Dict[str, Any]],
    selection_rank: int,
    external_pool_rank: Optional[int],
) -> Dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "source_rank": selection_rank,
        "selection_rank": selection_rank,
        "external_pool_rank": external_pool_rank,
        "semantic_rank": candidate_rank(str(candidate.get("candidate_id"))),
        "score": candidate.get("score"),
        "mean_score": candidate.get("mean_score"),
        "view_count": candidate.get("view_count"),
        "visit_position_navigable": candidate.get("visit_position_navigable"),
        "candidate_correct": None if feature is None else feature.get("candidate_correct"),
        "candidate_reachable": None if feature is None else feature.get("candidate_reachable"),
        "S_sem": None if feature is None else feature.get("S_sem"),
        "N2_projection_support_no_depth": None if feature is None else feature.get("N2_projection_support_no_depth"),
        "N5_object_node_evidence_full": None if feature is None else feature.get("N5_object_node_evidence_full"),
    }


def make_plan_row(
    row: Dict[str, Any],
    candidate: Dict[str, Any],
    source_index: int,
    branch_id: str,
    branch_rank: int,
    trigger_reason: str,
    selected_ids: List[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "source_index": source_index,
        "source_schema_version": row.get("schema_version"),
        "policy": POLICY_NAME,
        "viewpoint_policy": POLICY_NAME,
        "viewpoint_id": f"{branch_id}:external:{branch_rank}",
        "candidate_id": str(candidate.get("candidate_id")),
        "candidate_ids": [str(candidate.get("candidate_id"))],
        "external_candidate_ids": selected_ids,
        "external_branch_id": branch_id,
        "external_branch_rank": branch_rank,
        "external_branch_trigger_reason": trigger_reason,
        "external_selection_mode": str(args.external_selection_mode),
        "external_rank_band_pattern": list(args.rank_band_pattern),
        "viewpoint_position": candidate.get("visit_position"),
        "viewpoint_rotation": [0.0, 0.0, 0.0, 1.0],
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
        "episode_key": row.get("episode_key"),
        "scene_id": row.get("scene_id"),
        "query": row.get("query"),
        "pair_observation_id": row.get("pair_observation_id"),
        "pair_top_candidate_id": row.get("pair_top_candidate_id"),
        "pair_alt_candidate_id": row.get("pair_alt_candidate_id"),
        "pair_v3_action": row.get("pair_v3_action"),
        "pair_v3_reason": row.get("pair_v3_reason"),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    pair_rows = load_jsonl(Path(args.pair_objective_rows))
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    features = feature_index(Path(args.object_node_features) if args.object_node_features else None)

    branch_rows: List[Dict[str, Any]] = []
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    trigger_counts: Counter[str] = Counter()
    trigger_by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    action_by_label: Dict[str, Counter[str]] = defaultdict(Counter)
    budget_hit_counts: Counter[int] = Counter()
    budget_denominators: Counter[int] = Counter()
    full_pool_hit_rows = 0
    full_pool_denominator = 0
    neither_full_pool_hit_rows = 0
    neither_full_pool_denominator = 0

    for source_index, row in enumerate(pair_rows):
        should_trigger, trigger_reason = external_trigger(row, args)
        label = str(row.get("label_case"))
        action_by_label[label][str(row.get("pair_v3_action"))] += 1
        if not should_trigger:
            continue

        trigger_counts[trigger_reason] += 1
        trigger_by_label[label][trigger_reason] += 1
        scene_id = str(row.get("scene_id"))
        query = str(row.get("query"))
        episode_key = str(row.get("episode_key"))
        candidates = candidates_by_key.get((scene_id, query), [])
        excluded = {str(row.get("pair_top_candidate_id")), str(row.get("pair_alt_candidate_id"))}
        external_pool = selectable_external_candidates(candidates, excluded, args)
        external_pool_rank = {
            str(candidate.get("candidate_id")): rank
            for rank, candidate in enumerate(external_pool, start=1)
        }
        ranked_pool = rank_external_candidates(external_pool, args)
        selected = ranked_pool[: int(args.external_budget)]
        selected_ids = [str(candidate.get("candidate_id")) for candidate in selected]
        selected_features = [features.get((episode_key, candidate_id)) for candidate_id in selected_ids]
        selected_snapshots = [
            candidate_snapshot(
                candidate,
                feature,
                rank + 1,
                external_pool_rank.get(str(candidate.get("candidate_id"))),
            )
            for rank, (candidate, feature) in enumerate(zip(selected, selected_features))
        ]
        selected_correct_flags = [
            (feature or {}).get("candidate_correct") is True
            for feature in selected_features
        ]
        selected_contains_correct = any(selected_correct_flags)
        first_selected_correct = bool(selected_correct_flags[0]) if selected_correct_flags else False
        full_pool_contains_correct = any(
            (features.get((episode_key, str(candidate.get("candidate_id")))) or {}).get("candidate_correct") is True
            for candidate in external_pool
        )
        full_pool_denominator += 1
        full_pool_hit_rows += int(full_pool_contains_correct)
        if label == "neither_candidate_correct":
            neither_full_pool_denominator += 1
            neither_full_pool_hit_rows += int(full_pool_contains_correct)

        for budget in args.recall_budgets:
            pool_k = ranked_pool[: int(budget)]
            flags = [
                (features.get((episode_key, str(candidate.get("candidate_id")))) or {}).get("candidate_correct") is True
                for candidate in pool_k
            ]
            budget_denominators[int(budget)] += 1
            if any(flags):
                budget_hit_counts[int(budget)] += 1

        branch_id = f"external_candidate:{source_index}"
        branch_row = {
            "schema_version": SCHEMA_VERSION,
            "run_id": str(args.run_id),
            "source_index": source_index,
            "external_branch_id": branch_id,
            "external_branch_action": "request_external_candidate_observation" if selected else "defer_no_external_candidate",
            "external_branch_trigger_reason": trigger_reason,
            "external_selection_mode": str(args.external_selection_mode),
            "external_rank_band_pattern": list(args.rank_band_pattern),
            "episode_key": row.get("episode_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "pair_observation_id": row.get("pair_observation_id"),
            "pair_top_candidate_id": row.get("pair_top_candidate_id"),
            "pair_alt_candidate_id": row.get("pair_alt_candidate_id"),
            "pair_v3_action": row.get("pair_v3_action"),
            "pair_v3_reason": row.get("pair_v3_reason"),
            "label_case": label,
            "external_budget": int(args.external_budget),
            "external_pool_size": len(external_pool),
            "external_candidate_ids": selected_ids,
            "external_candidates": selected_snapshots,
            "selected_contains_correct": selected_contains_correct,
            "first_selected_correct": first_selected_correct,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": bool(features),
        }
        branch_rows.append(branch_row)

        if not selected:
            skipped_rows.append({**branch_row, "skip_reason": "no_selectable_external_candidate"})
            continue
        for rank, candidate in enumerate(selected, start=1):
            plan_rows.append(
                make_plan_row(row, candidate, source_index, branch_id, rank, trigger_reason, selected_ids, args)
            )

    triggered_rows = len(branch_rows)
    neither_triggered = [row for row in branch_rows if row["label_case"] == "neither_candidate_correct"]
    pair_correct_triggered = [
        row for row in branch_rows
        if row["label_case"] in {"top_only_correct", "alt_only_correct", "both_candidates_correct"}
    ]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "pair_objective_rows": str(args.pair_objective_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "object_node_features": args.object_node_features,
        "rows": len(pair_rows),
        "triggered_rows": triggered_rows,
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "external_budget": int(args.external_budget),
        "external_selection_mode": str(args.external_selection_mode),
        "rank_band_pattern": list(args.rank_band_pattern),
        "trigger_counts": dict(sorted(trigger_counts.items())),
        "trigger_by_label_case": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(trigger_by_label.items())
        },
        "pair_v3_action_by_label_case": {
            label: dict(sorted(counts.items()))
            for label, counts in sorted(action_by_label.items())
        },
        "neither_candidate_triggered_rows": len(neither_triggered),
        "neither_candidate_external_set_contains_correct_rate": ratio(
            sum(row["selected_contains_correct"] for row in neither_triggered),
            len(neither_triggered),
        ),
        "neither_candidate_first_external_correct_rate": ratio(
            sum(row["first_selected_correct"] for row in neither_triggered),
            len(neither_triggered),
        ),
        "full_external_pool_contains_correct_rate": ratio(
            full_pool_hit_rows,
            full_pool_denominator,
        ),
        "neither_candidate_full_external_pool_contains_correct_rate": ratio(
            neither_full_pool_hit_rows,
            neither_full_pool_denominator,
        ),
        "pair_correct_candidate_unnecessary_external_rows": len(pair_correct_triggered),
        "pair_correct_candidate_unnecessary_external_rate": ratio(
            len(pair_correct_triggered),
            triggered_rows,
        ),
        "external_recall_by_budget": {
            str(budget): {
                "rows": int(budget_denominators[int(budget)]),
                "contains_correct_rows": int(budget_hit_counts[int(budget)]),
                "contains_correct_rate": ratio(
                    int(budget_hit_counts[int(budget)]),
                    int(budget_denominators[int(budget)]),
                ),
            }
            for budget in args.recall_budgets
        },
        "diagnosis": {
            "branch_role": "request_observation_not_commit",
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": bool(features),
            "paper_claim_status": "blocked_until_external_observation_is_scored_on_fresh_split",
        },
        "output_files": {
            "branch_rows": "external_candidate_branch_rows.jsonl",
            "plan_rows": "external_candidate_observation_plan.jsonl",
            "skipped_rows": "external_candidate_observation_skipped.jsonl",
            "summary": "external_candidate_branch_summary.json",
        },
    }

    write_jsonl(out_root / "external_candidate_branch_rows.jsonl", branch_rows)
    write_jsonl(out_root / "external_candidate_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "external_candidate_observation_skipped.jsonl", skipped_rows)
    write_json(out_root / "external_candidate_branch_summary.json", summary)
    return summary


def parse_int_list(text: str) -> List[int]:
    values = [int(item.strip()) for item in text.split(",") if item.strip()]
    if not values:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return values


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan external-candidate observation after H001 pair objective v3 defer.")
    parser.add_argument("--pair-objective-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--object-node-features")
    parser.add_argument("--run-id", default="h001_external_candidate_observation_v1")
    parser.add_argument("--external-budget", type=int, default=6)
    parser.add_argument("--recall-budgets", type=parse_int_list, default=[1, 2, 3, 5, 6, 10])
    parser.add_argument(
        "--external-selection-mode",
        default="semantic_rank",
        choices=["semantic_rank", "rank_bands"],
    )
    parser.add_argument("--rank-band-pattern", type=parse_int_list, default=[1, 2, 3, 4, 6, 10])
    parser.add_argument("--max-pair-confirm-for-weak-external", type=float, default=0.60)
    parser.add_argument("--max-rank-ambiguous-confirm-gap-for-external", type=float, default=0.05)
    parser.add_argument("--require-navigable-visit", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
