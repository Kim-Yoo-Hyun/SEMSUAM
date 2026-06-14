import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    load_json,
    load_jsonl,
    request_sort_key,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_goal_region_inspection.v1"
EVIDENCE_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_goal_region_inspection_v1"
)


def row_request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    return grouped


def counter_dict(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def sorted_pair_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [dict(row) for row in rows],
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("pair_index"), 999999),
            str(row.get("pair_id")),
        ),
    )


def pair_blocker(row: Dict[str, Any]) -> str:
    status = str(row.get("goal_region_evidence_status"))
    if status == "ambiguous_goal_region_pair":
        return "rival_own_view_supported"
    if status == "contrastive_goal_region_pair" and row.get("common_focus_support") is True:
        return "contrastive_but_request_level_ambiguity_check_required"
    if status == "contrastive_goal_region_pair":
        return "contrastive_without_common_focus_support"
    return "insufficient_detector_or_role_evidence"


def pair_inspection_rows(pair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted_pair_rows(pair_rows):
        status = str(row.get("goal_region_evidence_status"))
        ambiguous = status == "ambiguous_goal_region_pair"
        contrastive = status == "contrastive_goal_region_pair"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "analysis_unique_support_goal_region_pair_inspection",
                "expanded_retrieval_request_id": row_request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "pair_id": row.get("pair_id"),
                "pair_index": row.get("pair_index"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "rival_candidate_id": row.get("rival_candidate_id"),
                "goal_region_evidence_status": status,
                "focus_own_support": row.get("focus_own_support") is True,
                "rival_own_support": row.get("rival_own_support") is True,
                "common_focus_support": row.get("common_focus_support") is True,
                "focus_own_associated_heading_count": safe_int(
                    row.get("focus_own_associated_heading_count"), 0
                ),
                "rival_own_associated_heading_count": safe_int(
                    row.get("rival_own_associated_heading_count"), 0
                ),
                "common_focus_associated_heading_count": safe_int(
                    row.get("common_focus_associated_heading_count"), 0
                ),
                "focus_rival_span_m": row.get("focus_rival_span_m"),
                "inspection_blocker": pair_blocker(row),
                "is_request_level_blocker": ambiguous,
                "is_later_arbitration_candidate": contrastive,
                "terminal_arbitration_allowed": False,
                "recommended_next_evidence": (
                    "reobserve_rival_region_or_collect_rival_common_view"
                    if ambiguous
                    else "hold_as_contrastive_candidate_until_request_blockers_clear"
                ),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def request_inspection_rows(
    request_rows: Sequence[Dict[str, Any]],
    pair_inspections: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    pairs_by_request = group_by_request(pair_inspections)
    rows: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=lambda row: request_sort_key(row_request_id(row))):
        request_id = row_request_id(request)
        pair_rows = pairs_by_request.get(request_id, [])
        ambiguous_pairs = [
            row for row in pair_rows if row.get("goal_region_evidence_status") == "ambiguous_goal_region_pair"
        ]
        contrastive_pairs = [
            row for row in pair_rows if row.get("goal_region_evidence_status") == "contrastive_goal_region_pair"
        ]
        has_request_blocker = bool(ambiguous_pairs)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "analysis_unique_support_goal_region_request_inspection",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": request.get("rival_identity_request_id"),
                "episode_key": request.get("episode_key"),
                "scene_key": request.get("scene_key"),
                "scene_id": request.get("scene_id"),
                "query": request.get("query"),
                "focus_candidate_id": request.get("focus_candidate_id"),
                "pair_count": request.get("pair_count"),
                "contrastive_goal_region_pair_count": len(contrastive_pairs),
                "ambiguous_goal_region_pair_count": len(ambiguous_pairs),
                "insufficient_detector_pair_count": request.get("insufficient_detector_pair_count"),
                "ambiguous_pair_ids": [row.get("pair_id") for row in ambiguous_pairs],
                "ambiguous_rival_candidate_ids": [
                    row.get("rival_candidate_id") for row in ambiguous_pairs
                ],
                "contrastive_pair_ids": [row.get("pair_id") for row in contrastive_pairs],
                "request_level_blocker": (
                    "contains_rival_own_view_supported_pairs"
                    if has_request_blocker
                    else "no_request_level_rival_support_blocker"
                ),
                "terminal_arbitration_allowed": False,
                "recommended_next_evidence": (
                    "freeze_second_pass_rival_region_evidence_contract"
                    if has_request_blocker
                    else "eligible_for_fixed_non_gt_arbitration_design_review"
                ),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    evidence_summary: Dict[str, Any],
    pair_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    pair_inspections: Sequence[Dict[str, Any]],
    request_inspections: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    action_rows = list(pair_inspections) + list(request_inspections)
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    request_blockers = [
        row for row in request_inspections if row.get("request_level_blocker") == "contains_rival_own_view_supported_pairs"
    ]
    pair_status_counts = Counter(str(row.get("goal_region_evidence_status")) for row in pair_rows)
    pair_blocker_counts = Counter(str(row.get("inspection_blocker")) for row in pair_inspections)
    request_recommendation_counts = Counter(str(row.get("recommended_next_evidence")) for row in request_inspections)
    gate = {
        "source_evidence_gate_passed": (evidence_summary.get("gate") or {}).get(
            "unique_support_goal_region_evidence_gate_passed"
        )
        is True,
        "expected_pair_rows_passed": len(pair_rows) == safe_int(evidence_summary.get("pair_evidence_rows"), -1),
        "expected_request_rows_passed": len(request_rows) == safe_int(evidence_summary.get("request_evidence_rows"), -1),
        "all_requests_have_terminal_blocker_passed": len(request_blockers) == len(request_inspections),
        "terminal_arbitration_blocked_passed": all(
            row.get("terminal_arbitration_allowed") is False for row in request_inspections
        ),
        "terminal_commit_rows_passed": len(terminal_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "paper_claim_allowed": False,
    }
    gate["inspection_gate_passed"] = all(
        value is True for key, value in gate.items() if key != "paper_claim_allowed"
    )
    terminal_contract_allowed = False
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_root": str(args.evidence_root),
        "out_root": str(args.out_root),
        "source_summary": str(Path(args.evidence_root) / "unique_support_goal_region_evidence_summary.json"),
        "pair_rows": len(pair_rows),
        "request_rows": len(request_rows),
        "pair_status_counts": dict(sorted(pair_status_counts.items())),
        "pair_blocker_counts": dict(sorted(pair_blocker_counts.items())),
        "request_recommendation_counts": dict(sorted(request_recommendation_counts.items())),
        "query_counts": counter_dict(row.get("query") for row in request_inspections),
        "scene_counts": counter_dict(row.get("scene_key") for row in request_inspections),
        "request_profiles": {
            row_request_id(row): {
                "query": row.get("query"),
                "scene_key": row.get("scene_key"),
                "pair_count": row.get("pair_count"),
                "contrastive_goal_region_pair_count": row.get("contrastive_goal_region_pair_count"),
                "ambiguous_goal_region_pair_count": row.get("ambiguous_goal_region_pair_count"),
                "ambiguous_rival_candidate_ids": row.get("ambiguous_rival_candidate_ids"),
                "recommended_next_evidence": row.get("recommended_next_evidence"),
            }
            for row in request_inspections
        },
        "terminal_contract_allowed": terminal_contract_allowed,
        "recommended_next_task": "freeze_second_pass_rival_region_evidence_contract",
        "recommended_next_task_reason": (
            "All requests contain at least one rival own-view supported pair; terminal arbitration would treat "
            "visible repeated-object evidence as goal validity."
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": "The inspection uses only post-detector evidence rows and does not join correctness labels.",
            "agent_inference": "The current output supports another active evidence request, not a terminal arbitration contract.",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "pair_inspection_rows": "unique_support_goal_region_pair_inspection_rows.jsonl",
            "request_inspection_rows": "unique_support_goal_region_request_inspection_rows.jsonl",
            "summary": "unique_support_goal_region_inspection_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evidence_root = Path(args.evidence_root)
    evidence_summary = load_json(evidence_root / "unique_support_goal_region_evidence_summary.json")
    pair_rows = load_jsonl(evidence_root / "unique_support_goal_region_pair_evidence_rows.jsonl")
    request_rows = load_jsonl(evidence_root / "unique_support_goal_region_request_evidence_rows.jsonl")
    pair_inspections = pair_inspection_rows(pair_rows)
    request_inspections = request_inspection_rows(request_rows, pair_inspections)
    summary = summarize(
        evidence_summary=evidence_summary,
        pair_rows=pair_rows,
        request_rows=request_rows,
        pair_inspections=pair_inspections,
        request_inspections=request_inspections,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "unique_support_goal_region_pair_inspection_rows.jsonl", pair_inspections)
    write_jsonl(out_root / "unique_support_goal_region_request_inspection_rows.jsonl", request_inspections)
    write_json(out_root / "unique_support_goal_region_inspection_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect unique-support goal-region evidence before terminal arbitration."
    )
    parser.add_argument("--evidence-root", default=EVIDENCE_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
