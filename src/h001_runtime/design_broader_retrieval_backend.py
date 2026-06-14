import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


SCHEMA_VERSION = "h001.broader_retrieval_backend_design.v1"
NO_CORRECT_REASON = "defer_identity_selected_outside_rival_near_tie"


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


def rows_by_branch(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in rows if row.get("external_branch_id") is not None}


def variant_contains(row: Dict[str, Any], name: str) -> bool:
    for variant in row.get("candidate_set_variants") or []:
        if variant.get("candidate_set") == name:
            return bool(variant.get("contains_correct"))
    return False


def variant_count(row: Dict[str, Any], name: str) -> int:
    for variant in row.get("candidate_set_variants") or []:
        if variant.get("candidate_set") == name:
            return int(variant.get("candidate_count") or 0)
    return 0


def inspect_branch(source: Dict[str, Any], expansion: Dict[str, Any]) -> Dict[str, Any]:
    artifact_top20_contains_correct = variant_contains(expansion, "artifact_semantic_top20")
    v4_external_contains_correct = variant_contains(expansion, "v4_external_set")
    current_contains_correct = bool(source.get("followup_set_contains_correct"))
    failure_modes: List[str] = []
    if not current_contains_correct:
        failure_modes.append("current_followup_set_missing_correct")
    if not v4_external_contains_correct:
        failure_modes.append("v4_external_set_missing_correct")
    if not artifact_top20_contains_correct:
        failure_modes.append("current_artifact_top20_missing_correct")
    if not artifact_top20_contains_correct and not v4_external_contains_correct:
        failure_modes.append("backend_recall_failure_not_detector_association")

    if "backend_recall_failure_not_detector_association" in failure_modes:
        recommendation = "new_backend_or_dense_export_recall_probe"
    elif not current_contains_correct and v4_external_contains_correct:
        recommendation = "preserve_explicit_candidate_ids_and_detector_association"
    else:
        recommendation = "identity_arbitration_or_goal_region_contract"

    return {
        "external_branch_id": source.get("external_branch_id"),
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "selected_candidate_id": source.get("selected_candidate_id"),
        "selected_candidate_correct": source.get("selected_candidate_correct"),
        "followup_set_contains_correct": current_contains_correct,
        "followup_candidate_count": len(source.get("followup_candidate_ids") or []),
        "v4_external_contains_correct": v4_external_contains_correct,
        "artifact_top20_contains_correct": artifact_top20_contains_correct,
        "artifact_top20_count": variant_count(expansion, "artifact_semantic_top20"),
        "failure_modes": failure_modes,
        "recommendation": recommendation,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    followup_rows = [
        row
        for row in load_jsonl(Path(args.followup_evidence_rows))
        if row.get("followup_evidence_v1_reason") == NO_CORRECT_REASON
    ]
    expansion_rows = rows_by_branch(load_jsonl(Path(args.candidate_set_expansion_rows)))
    rows = [
        inspect_branch(row, expansion_rows.get(str(row.get("external_branch_id")), {}))
        for row in followup_rows
    ]
    mode_counts = Counter(mode for row in rows for mode in row["failure_modes"])
    recommendation_counts = Counter(str(row.get("recommendation")) for row in rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "candidate_set_expansion_rows": str(args.candidate_set_expansion_rows),
        "out_root": str(out_root),
        "rows": len(rows),
        "failure_mode_counts": dict(sorted(mode_counts.items())),
        "recommendation_counts": dict(sorted(recommendation_counts.items())),
        "decision": {
            "do_not_do": [
                "Do not force identity confirmation when the follow-up set contains no correct candidate.",
                "Do not claim broader retrieval utility from the current spatial_nms_p97_k20 artifact when artifact_top20 also misses the correct target.",
            ],
            "next_probe": "dense_backend_recall_probe_for_no_correct_rows",
            "probe_contract": [
                "Generate a denser non-GT candidate pool for the same scene/query without using target labels for action.",
                "Measure recall@K against GT only after candidate generation.",
                "Proceed to detector observation only if the expanded pool contains at least one correct candidate.",
            ],
            "candidate_generation_options": [
                "lower VLMaps score percentile and raise max_candidates beyond 20 for the target scene/query",
                "raw grid-cell or connected-component export before spatial NMS",
                "object-node backend with less aggressive suppression",
                "active frontier/search expansion when semantic map recall is exhausted",
            ],
            "promotion_gate": {
                "min_no_correct_rows_with_recovered_candidate_rate": 0.5,
                "max_wrong_goal_commit_rate": 0.0,
                "requires_no_gt_for_action": True,
            },
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "broader_retrieval_backend_design_rows.jsonl",
            "summary": "broader_retrieval_backend_design_summary.json",
        },
    }
    write_jsonl(out_root / "broader_retrieval_backend_design_rows.jsonl", rows)
    write_json(out_root / "broader_retrieval_backend_design_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design broader retrieval/backend expansion for no-correct follow-up rows.")
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--candidate-set-expansion-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
