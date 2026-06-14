import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_candidate_set_guard_design.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def row_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(row.get("rival_identity_request_id")),
        str(row.get("episode_key")),
        str(row.get("query")),
    )


def index_candidate_set(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[row_key(row)] = row
    return indexed


def guard_design_for_taxonomy(taxonomy: str) -> Dict[str, Any]:
    if taxonomy == "source_pool_no_valid_candidate":
        return {
            "guard_design_route": "request_backend_retrieval_revision",
            "detector_evidence_allowed": False,
            "terminal_commit_allowed": False,
            "requires_action_time_proxy": True,
            "required_proxy": "non_gt_source_pool_validity_proxy",
            "design_reason": (
                "analysis shows neither the selected expanded set nor the full action-time source pool "
                "contains a valid candidate, so detector/viewpoint evidence on the current candidate set "
                "cannot recover the goal."
            ),
        }
    if taxonomy == "selection_missed_valid_candidate":
        return {
            "guard_design_route": "request_candidate_selection_revision",
            "detector_evidence_allowed": False,
            "terminal_commit_allowed": False,
            "requires_action_time_proxy": True,
            "required_proxy": "non_gt_selection_coverage_proxy",
            "design_reason": (
                "analysis shows the full source pool contains a valid candidate but the expanded selection "
                "missed it, so the retrieval selection policy must be revised before detector evidence."
            ),
        }
    if taxonomy == "valid_set_with_wrong_goal_distractor":
        return {
            "guard_design_route": "request_detector_guarded_observation",
            "detector_evidence_allowed": True,
            "terminal_commit_allowed": False,
            "requires_action_time_proxy": True,
            "required_proxy": "non_gt_wrong_goal_distractor_proxy",
            "design_reason": (
                "analysis shows the expanded set contains a valid candidate but also a wrong-goal distractor, "
                "so the next step may acquire detector/viewpoint evidence but must not terminally commit."
            ),
        }
    if taxonomy == "valid_set_without_wrong_goal_distractor":
        return {
            "guard_design_route": "request_lightweight_confirmation",
            "detector_evidence_allowed": True,
            "terminal_commit_allowed": False,
            "requires_action_time_proxy": True,
            "required_proxy": "non_gt_candidate_set_quality_proxy",
            "design_reason": (
                "analysis shows the expanded set contains a valid candidate without a labeled wrong-goal "
                "distractor, but confirmation evidence is still required before any terminal commit."
            ),
        }
    return {
        "guard_design_route": "defer_unknown_candidate_set_state",
        "detector_evidence_allowed": False,
        "terminal_commit_allowed": False,
        "requires_action_time_proxy": True,
        "required_proxy": "non_gt_candidate_set_state_proxy",
        "design_reason": f"unrecognized analysis taxonomy: {taxonomy}",
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    validity_rows = load_jsonl(Path(args.candidate_set_validity_rows))
    candidate_set_rows = load_jsonl(Path(args.candidate_set))
    candidate_index = index_candidate_set(candidate_set_rows)

    guard_rows: List[Dict[str, Any]] = []
    taxonomy_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    missing_candidate_set_rows = 0
    detector_allowed_rows = 0
    terminal_commit_allowed_rows = 0
    backend_revision_rows = 0
    selection_revision_rows = 0

    for row in validity_rows:
        taxonomy = str(row.get("analysis_only_candidate_set_taxonomy"))
        design = guard_design_for_taxonomy(taxonomy)
        candidate_set_row = candidate_index.get(row_key(row))
        if candidate_set_row is None:
            missing_candidate_set_rows += 1
        query = str(row.get("query"))
        taxonomy_counts[taxonomy] += 1
        route_counts[str(design["guard_design_route"])] += 1
        query_counts[query] += 1
        detector_allowed_rows += int(design["detector_evidence_allowed"] is True)
        terminal_commit_allowed_rows += int(design["terminal_commit_allowed"] is True)
        backend_revision_rows += int(design["guard_design_route"] == "request_backend_retrieval_revision")
        selection_revision_rows += int(design["guard_design_route"] == "request_candidate_selection_revision")

        guard_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": query,
                "expanded_candidate_count": row.get("expanded_candidate_count"),
                "analysis_only_candidate_set_taxonomy": taxonomy,
                "analysis_only_correct_candidate_count": row.get("analysis_only_correct_candidate_count"),
                "analysis_only_wrong_goal_candidate_count": row.get(
                    "analysis_only_wrong_goal_candidate_count"
                ),
                "analysis_only_full_pool_correct_candidate_count": row.get(
                    "analysis_only_full_pool_correct_candidate_count"
                ),
                "analysis_only_source_top_correct": row.get("analysis_only_source_top_correct"),
                "analysis_only_source_top_wrong_goal": row.get(
                    "analysis_only_source_top_wrong_goal"
                ),
                "guard_design_route": design["guard_design_route"],
                "detector_evidence_allowed": design["detector_evidence_allowed"],
                "terminal_commit_allowed": design["terminal_commit_allowed"],
                "requires_action_time_proxy": design["requires_action_time_proxy"],
                "required_proxy": design["required_proxy"],
                "design_reason": design["design_reason"],
                "guard_is_action_time_rule": False,
                "candidate_set_row_found": candidate_set_row is not None,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )

    row_count = len(validity_rows)
    source_pool_no_valid_rows = taxonomy_counts.get("source_pool_no_valid_candidate", 0)
    valid_with_distractor_rows = taxonomy_counts.get("valid_set_with_wrong_goal_distractor", 0)
    valid_without_distractor_rows = taxonomy_counts.get("valid_set_without_wrong_goal_distractor", 0)
    selected_missed_valid_rows = taxonomy_counts.get("selection_missed_valid_candidate", 0)
    guard_gate = {
        "all_validity_rows_have_candidate_set_row": missing_candidate_set_rows == 0,
        "no_terminal_commit_allowed": terminal_commit_allowed_rows == 0,
        "source_pool_no_valid_routed_to_backend_revision": backend_revision_rows
        == source_pool_no_valid_rows,
        "selection_missed_valid_routed_to_selection_revision": selection_revision_rows
        == selected_missed_valid_rows,
        "valid_rows_allow_evidence_only": detector_allowed_rows
        == valid_with_distractor_rows + valid_without_distractor_rows,
        "guard_is_action_time_rule": False,
        "requires_action_time_proxy": True,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }
    guard_gate["guard_design_gate_passed"] = (
        guard_gate["all_validity_rows_have_candidate_set_row"] is True
        and guard_gate["no_terminal_commit_allowed"] is True
        and guard_gate["source_pool_no_valid_routed_to_backend_revision"] is True
        and guard_gate["selection_missed_valid_routed_to_selection_revision"] is True
        and guard_gate["valid_rows_allow_evidence_only"] is True
        and guard_gate["guard_is_action_time_rule"] is False
        and guard_gate["requires_action_time_proxy"] is True
        and guard_gate["uses_gt_for_action"] is False
        and guard_gate["uses_gt_for_analysis"] is True
        and guard_gate["paper_claim_allowed"] is False
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_set": str(args.candidate_set),
        "candidate_set_validity_rows": str(args.candidate_set_validity_rows),
        "request_rows": row_count,
        "missing_candidate_set_rows": missing_candidate_set_rows,
        "taxonomy_counts": dict(sorted(taxonomy_counts.items())),
        "guard_route_counts": dict(sorted(route_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "detector_evidence_allowed_rows": detector_allowed_rows,
        "detector_evidence_allowed_rate": ratio(detector_allowed_rows, row_count),
        "terminal_commit_allowed_rows": terminal_commit_allowed_rows,
        "backend_revision_rows": backend_revision_rows,
        "selection_revision_rows": selection_revision_rows,
        "guard_scope": {
            "analysis_only_design": True,
            "guard_is_action_time_rule": False,
            "requires_action_time_proxy": True,
            "interpretation": (
                "This artifact converts analysis-only candidate-set taxonomy into a design target. "
                "It does not authorize paper-facing action claims until non-GT proxies implement the guard."
            ),
        },
        "guard_gate": guard_gate,
        "output_files": {
            "rows": "expanded_retrieval_candidate_set_guard_rows.jsonl",
            "summary": "expanded_retrieval_candidate_set_guard_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }
    write_jsonl(out_root / "expanded_retrieval_candidate_set_guard_rows.jsonl", guard_rows)
    write_json(out_root / "expanded_retrieval_candidate_set_guard_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Design the expanded-retrieval candidate-set guard from analysis-only taxonomy."
    )
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--candidate-set-validity-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
