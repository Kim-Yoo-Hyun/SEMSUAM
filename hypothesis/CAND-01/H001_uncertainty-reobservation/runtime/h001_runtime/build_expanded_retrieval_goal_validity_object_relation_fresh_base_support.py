import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_discriminative_evidence import (
    candidate_id,
    load_json,
    load_jsonl,
    ratio,
    request_sort_key,
    row_request_id,
    safe_float,
    safe_int,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_object_relation_fresh_base_support.v1"


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def revision_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (row_request_id(row), candidate_id(row))


def support_class(row: Dict[str, Any]) -> str:
    if row.get("strong_own_view_evidence") is True:
        return "candidate_specific_support"
    if (
        safe_int(row.get("strict_association_count"), 0) > 0
        or safe_int(row.get("mask_hit_count"), 0) > 0
        or safe_int(row.get("visible_count"), 0) > 0
    ):
        return "weak_or_partial_candidate_specific_support"
    return "no_independent_candidate_specific_support"


def build_candidate_rows(
    request_rows: Sequence[Dict[str, Any]],
    revision_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    revision_index = {revision_key(row): row for row in revision_rows}
    rows: List[Dict[str, Any]] = []
    for request_row in sorted(
        request_rows,
        key=lambda row: (
            request_sort_key(row_request_id(row)),
            safe_int(row.get("target_generated_rank"), 999999),
            candidate_id(row),
        ),
    ):
        key = (row_request_id(request_row), candidate_id(request_row))
        revision_row = revision_index.get(key)
        if revision_row is None:
            rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_fresh_base_support_before_relation_arbitration",
                    "base_support_source": "expanded_retrieval_local_context_revision_v1",
                    "expanded_retrieval_request_id": key[0],
                    "rival_identity_request_id": request_row.get("rival_identity_request_id"),
                    "episode_key": request_row.get("episode_key"),
                    "scene_key": request_row.get("scene_key"),
                    "scene_id": request_row.get("scene_id"),
                    "query": request_row.get("query"),
                    "candidate_id": key[1],
                    "target_candidate_id": key[1],
                    "target_generated_rank": request_row.get("target_generated_rank"),
                    "target_semantic_rank": request_row.get("target_semantic_rank"),
                    "candidate_evidence_class": "missing_from_independent_base_support",
                    "candidate_specific_support": False,
                    "has_candidate_association": False,
                    "consistent_depth_count": 0,
                    "depth_mismatch_count": None,
                    "mask_hit_count": 0,
                    "best_box_score": None,
                    "min_depth_error_m": None,
                    "heading_rows": None,
                    "visible_count": 0,
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )
            continue

        strict_count = safe_int(revision_row.get("strict_association_count"), 0)
        visible_count = safe_int(revision_row.get("visible_count"), 0)
        cls = support_class(revision_row)
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_fresh_base_support_before_relation_arbitration",
                "base_support_source": "expanded_retrieval_local_context_revision_v1",
                "expanded_retrieval_request_id": key[0],
                "rival_identity_request_id": request_row.get("rival_identity_request_id"),
                "episode_key": request_row.get("episode_key"),
                "scene_key": request_row.get("scene_key"),
                "scene_id": request_row.get("scene_id"),
                "query": request_row.get("query"),
                "candidate_id": key[1],
                "target_candidate_id": key[1],
                "target_generated_rank": request_row.get("target_generated_rank"),
                "target_semantic_rank": request_row.get("target_semantic_rank"),
                "candidate_evidence_class": cls,
                "candidate_specific_support": cls == "candidate_specific_support",
                "has_candidate_association": strict_count > 0,
                "consistent_depth_count": strict_count,
                "depth_mismatch_count": max(0, visible_count - strict_count),
                "mask_hit_count": safe_int(revision_row.get("mask_hit_count"), 0),
                "best_box_score": safe_float(revision_row.get("best_box_score")),
                "min_depth_error_m": safe_float(revision_row.get("min_depth_error_m")),
                "heading_rows": revision_row.get("heading_rows"),
                "visible_count": visible_count,
                "box_hit_count": revision_row.get("box_hit_count"),
                "prior_detector_evidence_score": revision_row.get("prior_detector_evidence_score"),
                "prior_detector_support_class": revision_row.get("prior_detector_support_class"),
                "local_context_support_score": revision_row.get("local_context_support_score"),
                "support_score": revision_row.get("support_score"),
                "semantic_rank": revision_row.get("semantic_rank"),
                "semantic_score": revision_row.get("semantic_score"),
                "candidate_role": revision_row.get("candidate_role"),
                "is_source_top": revision_row.get("is_source_top"),
                "is_detector_strong_candidate": revision_row.get("is_detector_strong_candidate"),
                "is_detector_strong_rival": revision_row.get("is_detector_strong_rival"),
                "is_local_context_candidate": revision_row.get("is_local_context_candidate"),
                "strong_own_view_evidence": revision_row.get("strong_own_view_evidence"),
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    *,
    contract: Dict[str, Any],
    request_rows: Sequence[Dict[str, Any]],
    revision_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_base_support_gate") or {}
    forbidden = action_forbidden_keys(candidate_rows)
    by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        by_request[row_request_id(row)].append(row)

    request_profiles = {}
    for request_id, rows in sorted(by_request.items(), key=lambda item: request_sort_key(item[0])):
        support_rows = [row for row in rows if row.get("candidate_specific_support") is True]
        assoc_rows = [row for row in rows if row.get("has_candidate_association") is True]
        request_profiles[request_id] = {
            "candidate_rows": len(rows),
            "candidate_specific_support_rows": len(support_rows),
            "candidate_specific_support_ids": [candidate_id(row) for row in support_rows],
            "associated_candidate_rows": len(assoc_rows),
        }

    support_rows = [row for row in candidate_rows if row.get("candidate_specific_support") is True]
    assoc_rows = [row for row in candidate_rows if row.get("has_candidate_association") is True]
    missing_rows = [
        row
        for row in candidate_rows
        if row.get("candidate_evidence_class") == "missing_from_independent_base_support"
    ]
    gate = {
        "expected_request_rows_passed": len(by_request) == safe_int(minimum.get("expected_request_rows"), 0),
        "expected_candidate_rows_passed": len(candidate_rows) == safe_int(minimum.get("expected_candidate_rows"), 0),
        "minimum_candidate_specific_support_rows_passed": len(support_rows)
        >= safe_int(minimum.get("minimum_candidate_specific_support_rows"), 0),
        "minimum_associated_candidate_rows_passed": len(assoc_rows)
        >= safe_int(minimum.get("minimum_associated_candidate_rows"), 0),
        "missing_base_support_rows_passed": len(missing_rows)
        <= safe_int(minimum.get("missing_base_support_rows_maximum"), 0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": all(row.get("terminal_commit") is not True for row in candidate_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in candidate_rows),
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }
    gate["fresh_base_support_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"uses_gt_for_action", "uses_gt_for_analysis", "paper_claim_allowed"}
    )
    gate["objective_analyzer_gate_passed"] = gate["fresh_base_support_gate_passed"]
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "object_relation_request_rows": str(args.object_relation_request_rows),
            "local_context_revision_evidence_rows": str(args.local_context_revision_evidence_rows),
        },
        "request_rows": len(request_rows),
        "source_revision_rows": len(revision_rows),
        "candidate_rows": len(candidate_rows),
        "request_count": len(by_request),
        "candidate_specific_support_rows": len(support_rows),
        "associated_candidate_rows": len(assoc_rows),
        "missing_base_support_rows": len(missing_rows),
        "candidate_evidence_class_counts": compact_counter(row.get("candidate_evidence_class") for row in candidate_rows),
        "candidate_role_counts": compact_counter(row.get("candidate_role") for row in candidate_rows),
        "request_profiles": request_profiles,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden,
        "gate": gate,
        "interpretation": {
            "fact": "This converter maps pre-existing local-context revision evidence into the fixed arbitration analyzer input schema before evaluation labels are joined.",
            "agent_inference": "The converted rows provide independent candidate-specific support for a fresh object-relation arbitration validation, but they do not authorize terminal ObjectNav commits.",
        },
        "output_files": {
            "candidate_rows": "object_relation_fresh_base_support_candidate_rows.jsonl",
            "summary": "object_relation_fresh_base_support_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, type=Path)
    parser.add_argument("--out-root", required=True, type=Path)
    parser.add_argument("--object-relation-request-rows", type=Path)
    parser.add_argument("--local-context-revision-evidence-rows", type=Path)
    return parser.parse_args()


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(explicit)
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.object_relation_request_rows = source_path(
        args,
        contract,
        "object_relation_request_rows",
        "object_relation_request_rows",
    )
    args.local_context_revision_evidence_rows = source_path(
        args,
        contract,
        "local_context_revision_evidence_rows",
        "local_context_revision_evidence_rows",
    )

    request_rows = load_jsonl(args.object_relation_request_rows)
    revision_rows = load_jsonl(args.local_context_revision_evidence_rows)
    candidate_rows = build_candidate_rows(request_rows, revision_rows)
    summary = summarize(
        contract=contract,
        request_rows=request_rows,
        revision_rows=revision_rows,
        candidate_rows=candidate_rows,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "object_relation_fresh_base_support_candidate_rows.jsonl", candidate_rows)
    write_json(args.out_root / "object_relation_fresh_base_support_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
