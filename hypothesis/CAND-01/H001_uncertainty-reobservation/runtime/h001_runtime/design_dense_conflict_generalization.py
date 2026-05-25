import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.dense_conflict_generalization_design.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def positive_support(candidate: Dict[str, Any]) -> bool:
    return (
        candidate.get("positive_support") is True
        or candidate.get("second_stage_strong_depth_evidence") is True
        or candidate.get("own_view_positive_support") is True
    )


def scene_key(row: Dict[str, Any]) -> str:
    value = str(row.get("scene_id") or "")
    if "/" in value:
        stem = value.split("/")[-2]
        return stem.split("-", 1)[-1]
    return str(row.get("scene_key") or value or "unknown")


def parse_source(value: str) -> Tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    name, path = value.split("=", 1)
    return name.strip(), Path(path)


def candidate_rows(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("second_stage_candidate_evidence") or row.get("candidate_evidence") or [])


def summarize_source(name: str, path: Path) -> Dict[str, Any]:
    rows = load_jsonl(path)
    scene_counts = Counter(scene_key(row) for row in rows)
    query_counts = Counter(str(row.get("query")) for row in rows)
    action_counts = Counter(str(row.get("second_stage_identity_v1_action") or row.get("external_evidence_v1_action")) for row in rows)
    conflict_rows = 0
    source_selected_wrong_rows = 0
    success_commit_rows = 0
    wrong_commit_rows = 0
    no_valid_commit_rows = 0
    visit_position_only_commit_rows = 0
    for row in rows:
        positives = [candidate for candidate in candidate_rows(row) if positive_support(candidate)]
        correct_positive = [candidate for candidate in positives if candidate.get("candidate_correct") is True]
        wrong_positive = [candidate for candidate in positives if candidate.get("candidate_correct") is False]
        conflict_rows += int(bool(correct_positive and wrong_positive))
        source_selected_wrong_rows += int(row.get("source_selected_candidate_correct") is False)
        success_commit_rows += int(
            bool(row.get("second_stage_identity_v1_success_commit") or row.get("external_evidence_v1_success_commit"))
        )
        wrong_commit_rows += int(
            bool(row.get("second_stage_identity_v1_wrong_goal_commit") or row.get("external_evidence_v1_wrong_goal_commit"))
        )
        no_valid_commit_rows += int(
            bool(row.get("second_stage_identity_v1_no_valid_commit") or row.get("external_evidence_v1_no_valid_external_commit"))
        )
        visit_position_only_commit_rows += int(bool(row.get("second_stage_identity_v1_visit_position_only_commit")))
    return {
        "name": name,
        "path": str(path),
        "rows": len(rows),
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "rows_with_correct_and_wrong_positive_support": conflict_rows,
        "source_selected_wrong_rows": source_selected_wrong_rows,
        "success_commit_rows": success_commit_rows,
        "wrong_goal_commit_rows": wrong_commit_rows,
        "no_valid_commit_rows": no_valid_commit_rows,
        "visit_position_only_commit_rows": visit_position_only_commit_rows,
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in rows),
        "uses_gt_for_analysis": any(row.get("uses_gt_for_analysis") is True for row in rows),
    }


def rate(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def merged_counts(sources: Iterable[Dict[str, Any]], field: str) -> Counter:
    counts: Counter[str] = Counter()
    for source in sources:
        counts.update(source.get(field) or {})
    return counts


def split_options(summaries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    first_eval = [source for source in summaries if "first_eval" in source["name"] or "heldout" in source["name"]]
    v3_fresh = [source for source in summaries if "v3_fresh" in source["name"]]
    risk = [source for source in summaries if "risk" in source["name"]]
    repeated = [
        source
        for source in summaries
        if source.get("query_counts", {}).get("sofa", 0) > 0
        or source.get("query_counts", {}).get("chair", 0) > 0
    ]

    first_eval_rows = sum(source["rows"] for source in first_eval)
    first_eval_conflict = sum(source["rows_with_correct_and_wrong_positive_support"] for source in first_eval)
    first_eval_scenes = len(merged_counts(first_eval, "scene_counts"))
    first_eval_queries = len(merged_counts(first_eval, "query_counts"))
    repeated_rows = sum(source["rows"] for source in repeated)
    repeated_scenes = len(merged_counts(repeated, "scene_counts"))

    return [
        {
            "option": "scene_disjoint_first_eval_style",
            "priority": 1,
            "status": "recommended_next_design",
            "reason": (
                "Closest to paper-facing generalization because it preserves HM3D ObjectNav task semantics, "
                "scene-disjoint heldout logic, and existing detector/association tooling."
            ),
            "current_available_evidence": {
                "rows": first_eval_rows,
                "scenes": first_eval_scenes,
                "queries": first_eval_queries,
                "rows_with_correct_and_wrong_positive_support": first_eval_conflict,
            },
            "minimum_new_split_contract": {
                "rows": 20,
                "scenes": 5,
                "queries": 3,
                "selected_wrong_rows": 6,
                "rows_with_correct_and_wrong_positive_support": 12,
                "wrong_goal_baseline_rows": 8,
            },
            "next_action": "implement a split miner that samples scene-disjoint first_eval-style rows before any detector rerun",
            "blocked_until": "a frozen manifest and non-GT candidate recall gate pass on the mined rows",
        },
        {
            "option": "additional_repeated_object_stress",
            "priority": 2,
            "status": "use_as_stress_not_main_generalization",
            "reason": (
                "Directly targets the repeated-object identity failure mechanism, but it is too narrow if used "
                "as the only next validation axis."
            ),
            "current_available_evidence": {
                "rows": repeated_rows,
                "scenes": repeated_scenes,
                "queries": dict(sorted(merged_counts(repeated, "query_counts").items())),
            },
            "minimum_new_split_contract": {
                "rows": 12,
                "scenes": 3,
                "repeated_categories": 2,
                "wrong_selected_rows": 6,
            },
            "next_action": "keep as a stress slice inside the broader split rather than a standalone promotion gate",
            "blocked_until": "scene diversity and category diversity are added",
        },
        {
            "option": "hm3d_ovon_extension",
            "priority": 3,
            "status": "defer_until_objectnav_generalization_passes",
            "reason": (
                "Open-vocabulary goals are valuable for top-tier framing, but they add new dataset, language "
                "query, and evaluation confounds before the core mechanism is stable."
            ),
            "current_available_evidence": {
                "rows": 0,
                "scenes": 0,
                "queries": 0,
            },
            "minimum_new_split_contract": {
                "ovon_episodes": 50,
                "open_vocab_queries": 10,
                "seen_unseen_query_groups": True,
                "separate_language_grounding_errors": True,
            },
            "next_action": "defer to a later external-validity experiment after first_eval-style split passes",
            "blocked_until": "ObjectNav dense-conflict generalization is stable",
        },
    ]


def run(args: argparse.Namespace) -> Dict[str, Any]:
    summaries = [summarize_source(name, path) for name, path in map(parse_source, args.source)]
    total_rows = sum(source["rows"] for source in summaries)
    total_conflict = sum(source["rows_with_correct_and_wrong_positive_support"] for source in summaries)
    source_selected_wrong = sum(source["source_selected_wrong_rows"] for source in summaries)
    success_commits = sum(source["success_commit_rows"] for source in summaries)
    wrong_commits = sum(source["wrong_goal_commit_rows"] for source in summaries)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "sources": summaries,
        "aggregate": {
            "rows": total_rows,
            "scenes": len(merged_counts(summaries, "scene_counts")),
            "queries": len(merged_counts(summaries, "query_counts")),
            "rows_with_correct_and_wrong_positive_support": total_conflict,
            "source_selected_wrong_rows": source_selected_wrong,
            "success_commit_rows": success_commits,
            "wrong_goal_commit_rows": wrong_commits,
            "success_commit_rate": rate(success_commits, total_rows),
            "wrong_goal_commit_rate": rate(wrong_commits, total_rows),
            "uses_gt_for_action": any(source["uses_gt_for_action"] for source in summaries),
            "uses_gt_for_analysis": any(source["uses_gt_for_analysis"] for source in summaries),
        },
        "split_options": split_options(summaries),
        "recommendation": {
            "selected_next": "scene_disjoint_first_eval_style",
            "why": (
                "It has the best top-tier trajectory: same ObjectNav task family, scene-disjoint validation, "
                "existing artifacts, and direct connection to wrong-goal visit / wasted-path metrics. "
                "HM3D-OVON should be an external-validity extension, and repeated-object rows should be a stress slice."
            ),
            "do_not_do_next": [
                "do not tune thresholds on the 6+2 diagnostic rows",
                "do not run policy-scale detector scoring before a broader manifest and recall gate are frozen",
                "do not switch to HM3D-OVON before the ObjectNav mechanism generalizes",
            ],
        },
        "next_manifest_contract": {
            "candidate_name": "dense_conflict_generalization_v1",
            "minimum_rows": 20,
            "minimum_scenes": 5,
            "minimum_queries": 3,
            "minimum_selected_wrong_rows": 6,
            "minimum_rows_with_correct_and_wrong_positive_support": 12,
            "include_slices": [
                "selected_wrong_positive_correct_present",
                "correct_and_wrong_positive_selected_correct",
                "repeated_object_local_context_positive_conflict",
                "backend_recall_failure_negative_slice",
            ],
            "gates_before_detector": [
                "manifest uniqueness and scene/query counts pass",
                "non-GT candidate artifact contains correct candidates on at least 70% of positive slices",
                "backend_recall_failure_negative_slice is reported separately, not forced through detector arbitration",
            ],
            "gates_after_detector": [
                "detector_box_rate >= 0.80",
                "sam2_mask_rate >= 0.80",
                "candidate_association_rate >= 0.30",
                "wrong_goal_commit_rate == 0.0",
                "success_commit_rows >= 25% of positive-slice rows",
                "selected_correct_improvement_over_source_selected_rows >= 20% of positive-slice rows",
            ],
        },
        "interpretation": {
            "fact": "This is a split design artifact. It does not create a new benchmark result.",
            "agent_inference": "The immediate next implementation should mine a scene-disjoint first_eval-style manifest, not run another detector job.",
            "paper_claim_status": "design_only_not_evidence",
        },
    }
    out_root = Path(args.out_root)
    write_json(out_root / "dense_conflict_generalization_design_summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design the next H001 dense-conflict generalization split.")
    parser.add_argument("--source", action="append", required=True, help="Name and JSONL path as name=path.")
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
