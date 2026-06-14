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


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_unique_support_rival_region_inspection.v1"
EVIDENCE_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_evidence_v1"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_inspection_v1"
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


def support_pattern(row: Dict[str, Any]) -> Dict[str, bool]:
    return {
        "rival_from_common_pair_view": row.get("rival_from_common_pair_view_support") is True,
        "rival_from_focus_own_view": row.get("rival_from_focus_own_view_support") is True,
        "focus_from_rival_own_view": row.get("focus_from_rival_own_view_support") is True,
    }


def pair_blocker(row: Dict[str, Any]) -> str:
    pattern = support_pattern(row)
    status = str(row.get("rival_region_evidence_status"))
    rival_from_focus = pattern["rival_from_focus_own_view"]
    focus_from_rival = pattern["focus_from_rival_own_view"]
    rival_from_common = pattern["rival_from_common_pair_view"]
    if status == "insufficient_second_pass_detector_pair":
        return "insufficient_second_pass_detector_or_role_evidence"
    if rival_from_focus and focus_from_rival:
        return "bidirectional_cross_region_overlap"
    if rival_from_focus:
        return "rival_visible_from_focus_region"
    if focus_from_rival:
        return "focus_visible_from_rival_region"
    if rival_from_common:
        return "shared_common_view_rival_support"
    return "pure_contrastive_no_second_pass_support"


def pair_recommendation(blocker: str) -> str:
    if blocker in {
        "bidirectional_cross_region_overlap",
        "rival_visible_from_focus_region",
        "focus_visible_from_rival_region",
    }:
        return "treat_as_cross_region_overlap_blocker"
    if blocker == "shared_common_view_rival_support":
        return "inspect_shared_common_view_support_before_arbitration"
    if blocker == "pure_contrastive_no_second_pass_support":
        return "hold_as_contrastive_candidate_until_request_clean"
    return "diagnose_second_pass_evidence_coverage"


def pair_inspection_rows(pair_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted_pair_rows(pair_rows):
        blocker = pair_blocker(row)
        pattern = support_pattern(row)
        cross_region = blocker in {
            "bidirectional_cross_region_overlap",
            "rival_visible_from_focus_region",
            "focus_visible_from_rival_region",
        }
        shared_common = blocker == "shared_common_view_rival_support"
        contrastive = blocker == "pure_contrastive_no_second_pass_support"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "analysis_unique_support_rival_region_pair_inspection",
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
                "rival_region_evidence_status": row.get("rival_region_evidence_status"),
                "support_pattern": pattern,
                "rival_from_common_pair_view_support": pattern["rival_from_common_pair_view"],
                "rival_from_focus_own_view_support": pattern["rival_from_focus_own_view"],
                "focus_from_rival_own_view_support": pattern["focus_from_rival_own_view"],
                "role_associated_heading_counts": row.get("role_associated_heading_counts"),
                "role_detector_box_counts": row.get("role_detector_box_counts"),
                "role_sam2_mask_counts": row.get("role_sam2_mask_counts"),
                "second_pass_support_role_count": row.get("second_pass_support_role_count"),
                "inspection_blocker": blocker,
                "is_cross_region_overlap_blocker": cross_region,
                "is_shared_common_view_blocker": shared_common,
                "is_later_arbitration_candidate": contrastive,
                "terminal_arbitration_allowed": False,
                "recommended_next_evidence": pair_recommendation(blocker),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def request_recommendation(
    cross_region_count: int,
    shared_common_count: int,
    contrastive_count: int,
    insufficient_count: int,
) -> str:
    if cross_region_count > 0:
        return "freeze_cross_region_overlap_failure_branch"
    if shared_common_count > 0:
        return "inspect_shared_common_view_support_before_terminal_arbitration"
    if contrastive_count > 0 and insufficient_count == 0:
        return "eligible_for_fixed_non_gt_arbitration_design_review"
    return "diagnose_second_pass_evidence_coverage"


def request_blocker(
    cross_region_count: int,
    shared_common_count: int,
    contrastive_count: int,
    insufficient_count: int,
) -> str:
    if cross_region_count > 0:
        return "contains_cross_region_overlap_pairs"
    if shared_common_count > 0:
        return "contains_shared_common_view_rival_support"
    if contrastive_count > 0 and insufficient_count == 0:
        return "clean_contrastive_candidate_only"
    return "insufficient_second_pass_evidence"


def request_inspection_rows(
    request_rows: Sequence[Dict[str, Any]],
    pair_inspections: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    pairs_by_request = group_by_request(pair_inspections)
    rows: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=lambda row: request_sort_key(row_request_id(row))):
        request_id = row_request_id(request)
        pair_rows = pairs_by_request.get(request_id, [])
        cross_region_pairs = [row for row in pair_rows if row.get("is_cross_region_overlap_blocker") is True]
        shared_common_pairs = [row for row in pair_rows if row.get("is_shared_common_view_blocker") is True]
        contrastive_pairs = [row for row in pair_rows if row.get("is_later_arbitration_candidate") is True]
        insufficient_pairs = [
            row
            for row in pair_rows
            if row.get("inspection_blocker") == "insufficient_second_pass_detector_or_role_evidence"
        ]
        recommendation = request_recommendation(
            len(cross_region_pairs),
            len(shared_common_pairs),
            len(contrastive_pairs),
            len(insufficient_pairs),
        )
        blocker = request_blocker(
            len(cross_region_pairs),
            len(shared_common_pairs),
            len(contrastive_pairs),
            len(insufficient_pairs),
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "analysis_unique_support_rival_region_request_inspection",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": request.get("rival_identity_request_id"),
                "episode_key": request.get("episode_key"),
                "scene_key": request.get("scene_key"),
                "scene_id": request.get("scene_id"),
                "query": request.get("query"),
                "focus_candidate_id": request.get("focus_candidate_id"),
                "pair_count": request.get("pair_count"),
                "cross_region_overlap_pair_count": len(cross_region_pairs),
                "shared_common_view_rival_support_pair_count": len(shared_common_pairs),
                "second_pass_rival_region_contrastive_pair_count": len(contrastive_pairs),
                "insufficient_second_pass_detector_pair_count": len(insufficient_pairs),
                "cross_region_pair_ids": [row.get("pair_id") for row in cross_region_pairs],
                "shared_common_pair_ids": [row.get("pair_id") for row in shared_common_pairs],
                "contrastive_pair_ids": [row.get("pair_id") for row in contrastive_pairs],
                "request_level_blocker": blocker,
                "terminal_arbitration_allowed": False,
                "recommended_next_evidence": recommendation,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def simpler_alternative_report(
    pair_inspections: Sequence[Dict[str, Any]],
    request_inspections: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    any_contrastive_requests = [
        row for row in request_inspections if row.get("second_pass_rival_region_contrastive_pair_count", 0) > 0
    ]
    no_cross_requests = [
        row for row in request_inspections if row.get("cross_region_overlap_pair_count", 0) == 0
    ]
    return {
        "commit_if_any_contrastive_pair": {
            "decision": "rejected_as_terminal_rule",
            "eligible_request_rows": len(any_contrastive_requests),
            "reason": "the only contrastive-containing request still has shared common-view rival support",
        },
        "commit_if_no_cross_region_overlap": {
            "decision": "diagnostic_only_not_terminal",
            "eligible_request_rows": len(no_cross_requests),
            "reason": "absence of cross-region overlap does not remove shared common-view rival support",
        },
        "association_count_best": {
            "decision": "diagnostic_only_not_terminal",
            "supported_pair_rows": sum(1 for row in pair_inspections if row.get("second_pass_support_role_count", 0) > 0),
            "reason": "support count is a visibility signal, not ObjectNav goal validity",
        },
        "defer_all_cross_region": {
            "decision": "safe_but_inert",
            "deferred_request_rows": sum(
                1
                for row in request_inspections
                if row.get("request_level_blocker") == "contains_cross_region_overlap_pairs"
            ),
            "reason": "avoids unsafe terminal commits but does not resolve over-deferral",
        },
    }


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
    pair_status_counts = Counter(str(row.get("rival_region_evidence_status")) for row in pair_rows)
    pair_blocker_counts = Counter(str(row.get("inspection_blocker")) for row in pair_inspections)
    request_blocker_counts = Counter(str(row.get("request_level_blocker")) for row in request_inspections)
    request_recommendation_counts = Counter(str(row.get("recommended_next_evidence")) for row in request_inspections)
    clean_contrastive_requests = [
        row for row in request_inspections if row.get("request_level_blocker") == "clean_contrastive_candidate_only"
    ]
    gate = {
        "source_evidence_gate_passed": (evidence_summary.get("gate") or {}).get(
            "unique_support_rival_region_evidence_gate_passed"
        )
        is True,
        "expected_pair_rows_passed": len(pair_rows) == safe_int(evidence_summary.get("pair_evidence_rows"), -1),
        "expected_request_rows_passed": len(request_rows) == safe_int(evidence_summary.get("request_evidence_rows"), -1),
        "cross_region_or_shared_common_blocker_accounted_passed": len(clean_contrastive_requests) == 0,
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
    if request_blocker_counts.get("contains_cross_region_overlap_pairs", 0) > 0:
        recommended_next_task = "freeze_cross_region_overlap_failure_branch"
        reason = "Most requests still contain cross-region overlap after second-pass evidence."
    elif request_blocker_counts.get("contains_shared_common_view_rival_support", 0) > 0:
        recommended_next_task = "inspect_shared_common_view_support_before_terminal_arbitration"
        reason = "The remaining blocker is shared common-view rival support."
    else:
        recommended_next_task = "design_fixed_non_gt_goal_region_arbitration_contract"
        reason = "Only clean contrastive requests remain."
    return {
        "schema_version": SCHEMA_VERSION,
        "evidence_root": str(args.evidence_root),
        "out_root": str(args.out_root),
        "source_summary": str(Path(args.evidence_root) / "unique_support_rival_region_evidence_summary.json"),
        "pair_rows": len(pair_rows),
        "request_rows": len(request_rows),
        "pair_status_counts": dict(sorted(pair_status_counts.items())),
        "pair_blocker_counts": dict(sorted(pair_blocker_counts.items())),
        "request_blocker_counts": dict(sorted(request_blocker_counts.items())),
        "request_recommendation_counts": dict(sorted(request_recommendation_counts.items())),
        "query_counts": counter_dict(row.get("query") for row in request_inspections),
        "scene_counts": counter_dict(row.get("scene_key") for row in request_inspections),
        "request_profiles": {
            row_request_id(row): {
                "query": row.get("query"),
                "scene_key": row.get("scene_key"),
                "pair_count": row.get("pair_count"),
                "cross_region_overlap_pair_count": row.get("cross_region_overlap_pair_count"),
                "shared_common_view_rival_support_pair_count": row.get(
                    "shared_common_view_rival_support_pair_count"
                ),
                "second_pass_rival_region_contrastive_pair_count": row.get(
                    "second_pass_rival_region_contrastive_pair_count"
                ),
                "request_level_blocker": row.get("request_level_blocker"),
                "recommended_next_evidence": row.get("recommended_next_evidence"),
            }
            for row in request_inspections
        },
        "simpler_alternatives": simpler_alternative_report(pair_inspections, request_inspections),
        "terminal_contract_allowed": False,
        "recommended_next_task": recommended_next_task,
        "recommended_next_task_reason": reason,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": "The inspection uses only second-pass post-detector evidence rows and does not join correctness labels.",
            "agent_inference": "The second-pass branch is not terminal-ready because request-level blockers remain after contrastive evidence is collected.",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "pair_inspection_rows": "unique_support_rival_region_pair_inspection_rows.jsonl",
            "request_inspection_rows": "unique_support_rival_region_request_inspection_rows.jsonl",
            "summary": "unique_support_rival_region_inspection_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evidence_root = Path(args.evidence_root)
    evidence_summary = load_json(evidence_root / "unique_support_rival_region_evidence_summary.json")
    pair_rows = load_jsonl(evidence_root / "unique_support_rival_region_pair_evidence_rows.jsonl")
    request_rows = load_jsonl(evidence_root / "unique_support_rival_region_request_evidence_rows.jsonl")
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
    write_jsonl(out_root / "unique_support_rival_region_pair_inspection_rows.jsonl", pair_inspections)
    write_jsonl(out_root / "unique_support_rival_region_request_inspection_rows.jsonl", request_inspections)
    write_json(out_root / "unique_support_rival_region_inspection_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect second-pass rival-region evidence before terminal arbitration."
    )
    parser.add_argument("--evidence-root", default=EVIDENCE_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
