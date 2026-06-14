import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    artifact_index,
    candidate_viewpoint,
    plan_standoff_viewpoint,
)


SCHEMA_VERSION = "h001.selected_wrong_recovery_design.v1"
SELECTED_WRONG_MODE = "selected_wrong_correct_candidate_without_strong_support"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def candidate_rank(candidate_id: str) -> Optional[int]:
    try:
        return int(candidate_id.rsplit(":", 1)[-1]) + 1
    except (TypeError, ValueError):
        return None


def sort_artifact_candidates(candidates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        candidates.values(),
        key=lambda candidate: (
            safe_float(candidate.get("score")) or -math.inf,
            -(candidate_rank(str(candidate.get("candidate_id"))) or 9999),
        ),
        reverse=True,
    )


def rows_by_branch(rows: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("external_branch_id")): row
        for row in rows
        if row.get("external_branch_id") is not None
    }


def grouped_rows_by_branch(rows: Iterable[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        branch_id = row.get("external_branch_id")
        if branch_id is None:
            continue
        grouped.setdefault(str(branch_id), []).append(row)
    return grouped


def followup_evidence_by_id(row: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    if not row:
        return {}
    return {
        str(candidate.get("candidate_id")): candidate
        for candidate in row.get("followup_candidate_evidence") or []
        if candidate.get("candidate_id") is not None
    }


def followup_candidate_ids(row: Optional[Dict[str, Any]]) -> List[str]:
    if not row:
        return []
    ids = list(row.get("followup_candidate_ids") or [])
    if ids:
        return ordered_unique(ids)
    return ordered_unique(candidate.get("candidate_id") for candidate in row.get("followup_candidate_evidence") or [])


def stage2_target_ids(rows: List[Dict[str, Any]]) -> List[str]:
    return ordered_unique(row.get("candidate_id") for row in rows)


def stage2_context_ids(rows: List[Dict[str, Any]]) -> List[str]:
    return ordered_unique(
        candidate_id
        for row in rows
        for candidate_id in [row.get("candidate_id"), *(row.get("candidate_ids") or [])]
    )


def top_semantic_ids(
    artifact_candidates: List[Dict[str, Any]],
    allowed_ids: Optional[List[str]],
    limit: int,
) -> List[str]:
    allowed = None if allowed_ids is None else set(allowed_ids)
    return ordered_unique(
        candidate.get("candidate_id")
        for candidate in artifact_candidates
        if candidate.get("candidate_id") is not None and (allowed is None or str(candidate.get("candidate_id")) in allowed)
    )[:limit]


def strongest_positive_rival_ids(row: Optional[Dict[str, Any]], selected_id: str, limit: int) -> List[str]:
    candidates = [
        candidate
        for candidate in followup_evidence_by_id(row).values()
        if str(candidate.get("candidate_id")) != selected_id and candidate.get("positive_support") is True
    ]
    candidates.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
            safe_float(candidate.get("mask_hit_count")) or 0.0,
        ),
        reverse=True,
    )
    return ordered_unique(candidate.get("candidate_id") for candidate in candidates[:limit])


def target_set_variants(
    selected_id: str,
    current_targets: List[str],
    followup_ids: List[str],
    artifact_ids: List[str],
    row: Optional[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, List[str]]:
    semantic_followup = top_semantic_ids_from_ids(artifact_ids, followup_ids, int(args.semantic_neighbor_budget) + 1)
    semantic_neighbors = [candidate_id for candidate_id in semantic_followup if candidate_id != selected_id]
    strongest_positive = strongest_positive_rival_ids(row, selected_id, int(args.max_positive_rivals))
    return {
        "current_stage2_targets": current_targets,
        "selected_plus_strongest_positive_rival": ordered_unique([selected_id, *strongest_positive]),
        "selected_plus_semantic_neighbor_1": ordered_unique([selected_id, *semantic_neighbors[:1]]),
        "selected_plus_semantic_neighbors": ordered_unique([selected_id, *semantic_neighbors[: int(args.semantic_neighbor_budget)]]),
        "current_stage2_plus_semantic_neighbor_1": ordered_unique([*current_targets, *semantic_neighbors[:1]]),
        "semantic_followup_top3": semantic_followup[:3],
        "artifact_semantic_top3": artifact_ids[:3],
    }


def top_semantic_ids_from_ids(semantic_order: List[str], allowed_ids: List[str], limit: int) -> List[str]:
    allowed = set(allowed_ids)
    return ordered_unique(candidate_id for candidate_id in semantic_order if candidate_id in allowed)[:limit]


def contains_any(ids: List[str], targets: List[str]) -> bool:
    target_set = set(targets)
    return any(candidate_id in target_set for candidate_id in ids)


def viewpoint_for_target(
    source: Dict[str, Any],
    target_id: str,
    candidates: Dict[str, Dict[str, Any]],
    alt_ids: List[str],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    candidate = candidates.get(target_id)
    if candidate is None:
        return {"candidate_id": target_id, "viewpoint_feasible": False, "skip_reason": "missing_candidate"}

    standoff = plan_standoff_viewpoint(
        {"scene_id": source.get("scene_id"), "viewpoint_position": source.get("viewpoint_position")},
        candidate,
        candidates,
        alt_ids[0] if alt_ids else None,
        snapper,
        args,
    )
    if standoff is not None:
        return {
            "candidate_id": target_id,
            "viewpoint_feasible": True,
            "viewpoint_source": standoff.get("viewpoint_source"),
            "target_horizontal_distance": standoff.get("target_horizontal_distance"),
            "navmesh_navigable": standoff.get("navmesh_navigable"),
            "projection_sane": standoff.get("projection_sane"),
        }

    fallback = candidate_viewpoint(candidate)
    if fallback is None:
        return {"candidate_id": target_id, "viewpoint_feasible": False, "skip_reason": "no_viewpoint"}
    return {
        "candidate_id": target_id,
        "viewpoint_feasible": True,
        "viewpoint_source": "candidate_visit_position_fallback",
        "target_horizontal_distance": None,
        "navmesh_navigable": candidate.get("visit_position_navigable"),
        "projection_sane": True,
    }


def inspect_row(
    bottleneck: Dict[str, Any],
    followup: Optional[Dict[str, Any]],
    stage2_rows: List[Dict[str, Any]],
    candidates: Dict[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    branch_id = str(bottleneck.get("external_branch_id"))
    selected_id = str(bottleneck.get("selected_candidate_id"))
    correct_ids = ordered_unique(bottleneck.get("followup_correct_candidate_ids") or [])
    followup_ids = followup_candidate_ids(followup)
    current_targets = stage2_target_ids(stage2_rows)
    current_context = stage2_context_ids(stage2_rows)
    artifact_candidates = sort_artifact_candidates(candidates)
    semantic_order = ordered_unique(candidate.get("candidate_id") for candidate in artifact_candidates)
    semantic_top_followup = top_semantic_ids_from_ids(semantic_order, followup_ids, 6)
    variants = target_set_variants(selected_id, current_targets, followup_ids, semantic_order, followup, args)
    selected_neighbor_targets = variants["selected_plus_semantic_neighbor_1"]
    alt_ids = [candidate_id for candidate_id in selected_neighbor_targets if candidate_id != selected_id]
    feasibility = [
        viewpoint_for_target(
            {**(followup or {}), **bottleneck},
            candidate_id,
            candidates,
            [value for value in selected_neighbor_targets if value != candidate_id],
            snapper,
            args,
        )
        for candidate_id in selected_neighbor_targets
    ]
    positive_rivals = strongest_positive_rival_ids(followup, selected_id, int(args.max_positive_rivals))
    variant_rows = [
        {
            "variant": name,
            "target_ids": ids,
            "target_count": len(ids),
            "targets_correct_candidate": contains_any(ids, correct_ids),
        }
        for name, ids in variants.items()
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "external_branch_id": branch_id,
        "episode_key": bottleneck.get("episode_key"),
        "scene_id": bottleneck.get("scene_id"),
        "query": bottleneck.get("query"),
        "property_group": bottleneck.get("property_group"),
        "label_case": bottleneck.get("label_case"),
        "bottleneck_mode": bottleneck.get("bottleneck_mode"),
        "selected_candidate_id": selected_id,
        "selected_candidate_correct": bottleneck.get("selected_candidate_correct"),
        "correct_candidate_ids": correct_ids,
        "followup_candidate_ids": followup_ids,
        "followup_set_contains_correct": contains_any(followup_ids, correct_ids),
        "current_stage2_target_ids": current_targets,
        "current_stage2_context_ids": current_context,
        "current_stage2_targets_correct": contains_any(current_targets, correct_ids),
        "current_stage2_context_contains_correct": contains_any(current_context, correct_ids),
        "semantic_order_top6": semantic_order[:6],
        "semantic_followup_top6": semantic_top_followup,
        "semantic_neighbor_ids": [candidate_id for candidate_id in semantic_top_followup if candidate_id != selected_id][
            : int(args.semantic_neighbor_budget)
        ],
        "strongest_positive_rival_ids": positive_rivals,
        "proposed_variant_rows": variant_rows,
        "selected_plus_semantic_neighbor_viewpoint_feasibility": feasibility,
        "correct_target_would_be_added_by_semantic_neighbor_rule": contains_any(
            variants["selected_plus_semantic_neighbor_1"], correct_ids
        ),
        "broader_retrieval_needed_for_this_row": not contains_any(followup_ids, correct_ids),
        "candidate_viewpoint_revision_supported_for_this_row": (
            contains_any(followup_ids, correct_ids)
            and not contains_any(current_targets, correct_ids)
            and contains_any(variants["selected_plus_semantic_neighbor_1"], correct_ids)
        ),
        "analysis_only_correct_ids": correct_ids,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize(rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    variant_totals: Dict[str, Dict[str, int]] = {}
    for row in rows:
        for variant in row["proposed_variant_rows"]:
            name = str(variant["variant"])
            totals = variant_totals.setdefault(name, {"rows": 0, "targets_correct_rows": 0})
            totals["rows"] += 1
            totals["targets_correct_rows"] += int(variant["targets_correct_candidate"])

    variant_summary = {
        name: {
            **totals,
            "targets_correct_rate": ratio(totals["targets_correct_rows"], totals["rows"]),
        }
        for name, totals in sorted(variant_totals.items())
    }
    current_hits = sum(row["current_stage2_targets_correct"] for row in rows)
    followup_hits = sum(row["followup_set_contains_correct"] for row in rows)
    context_hits = sum(row["current_stage2_context_contains_correct"] for row in rows)
    semantic_hits = sum(row["correct_target_would_be_added_by_semantic_neighbor_rule"] for row in rows)
    semantic_feasible = sum(
        all(item.get("viewpoint_feasible") is True for item in row["selected_plus_semantic_neighbor_viewpoint_feasibility"])
        for row in rows
    )
    mode_counts = Counter(str(row.get("bottleneck_mode")) for row in rows)
    if rows and followup_hits == len(rows) and semantic_hits == len(rows) and current_hits < len(rows):
        recommendation = "candidate_viewpoint_revision_first"
    elif rows and followup_hits < len(rows):
        recommendation = "broader_retrieval_or_backend_expansion_first"
    else:
        recommendation = "inspect_mixed_failure_modes"
    return {
        "schema_version": SCHEMA_VERSION,
        "bottleneck_rows": str(args.bottleneck_rows),
        "v4_followup_evidence_rows": str(args.v4_followup_evidence_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "stage2_plan": str(args.stage2_plan) if args.stage2_plan else None,
        "out_root": str(args.out_root),
        "rows": len(rows),
        "mode_counts": dict(sorted(mode_counts.items())),
        "followup_set_contains_correct_rows": followup_hits,
        "current_stage2_targets_correct_rows": current_hits,
        "current_stage2_context_contains_correct_rows": context_hits,
        "semantic_neighbor_rule_targets_correct_rows": semantic_hits,
        "semantic_neighbor_viewpoint_feasible_rows": semantic_feasible,
        "variant_summary": variant_summary,
        "recommendation": recommendation,
        "interpretation": {
            "primary_bottleneck": (
                "the correct candidate is already in the follow-up/context set, but the current second-stage target rule "
                "observes selected plus strongest positive/strong rival instead of the high-semantic neighbor"
            ),
            "recommended_revision": (
                "for selected-wrong small_or_cluttered identity requests, add a non-GT semantic-neighbor target "
                "from the current follow-up candidate set before expanding retrieval"
            ),
            "broader_retrieval_needed_for_current_selected_wrong_rows": followup_hits < len(rows),
            "first_eval_rerun_blocked": True,
            "policy_scale_comparison_blocked": True,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "selected_wrong_recovery_rows.jsonl",
            "summary": "selected_wrong_recovery_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    bottleneck_rows = [
        row
        for row in load_jsonl(Path(args.bottleneck_rows))
        if row.get("bottleneck_mode") == SELECTED_WRONG_MODE
    ]
    if int(args.max_rows) > 0:
        bottleneck_rows = bottleneck_rows[: int(args.max_rows)]
    followups = rows_by_branch(load_jsonl(Path(args.v4_followup_evidence_rows)))
    stage2_plan = grouped_rows_by_branch(load_jsonl(Path(args.stage2_plan))) if args.stage2_plan else {}
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    snapper = NavmeshSnapper(args.data_root)
    rows: List[Dict[str, Any]] = []
    try:
        for bottleneck in bottleneck_rows:
            key = (str(bottleneck.get("scene_id")), str(bottleneck.get("query")))
            rows.append(
                inspect_row(
                    bottleneck,
                    followups.get(str(bottleneck.get("external_branch_id"))),
                    stage2_plan.get(str(bottleneck.get("external_branch_id")), []),
                    candidates_by_key.get(key, {}),
                    snapper,
                    args,
                )
            )
    finally:
        snapper.close()

    out_root = Path(args.out_root)
    write_jsonl(out_root / "selected_wrong_recovery_rows.jsonl", rows)
    summary = summarize(rows, args)
    write_json(out_root / "selected_wrong_recovery_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design recovery for selected-wrong V4 request-identity rows.")
    parser.add_argument("--bottleneck-rows", required=True)
    parser.add_argument("--v4-followup-evidence-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--stage2-plan", default=None)
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--max-rows", type=int, default=0)
    parser.add_argument("--semantic-neighbor-budget", type=int, default=2)
    parser.add_argument("--max-positive-rivals", type=int, default=1)
    parser.add_argument("--standoff-distances", type=lambda text: [float(x) for x in text.split(",") if x], default=[1.25, 1.75, 2.25])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
