import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1"
)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Sequence[Dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def sort_request_id(value: str) -> tuple:
    prefix, _, number = str(value).partition(":")
    return (prefix, safe_int(number, 999999), str(value))


def classify_residual(row: Dict[str, Any]) -> str:
    associated = safe_int(row.get("completion_associated_heading_count"))
    depth_consistent = safe_int(row.get("completion_depth_consistent_count"))
    prior_depth = safe_int(row.get("prior_depth_consistent_count"))
    if associated == 0 and depth_consistent == 0:
        return "mask_projection_without_association_or_depth"
    if associated == 0 and depth_consistent > 0:
        return "depth_signal_not_candidate_associated"
    if associated > 0 and depth_consistent <= prior_depth:
        return "association_present_without_depth_improvement"
    return "manual_review_unexpected_partial_relation_depth"


def residual_tags(row: Dict[str, Any], residual_class: str) -> List[str]:
    tags = [residual_class]
    associated = safe_int(row.get("completion_associated_heading_count"))
    depth_consistent = safe_int(row.get("completion_depth_consistent_count"))
    inside_mask = safe_int(row.get("completion_inside_mask_count"))
    prior_associated = safe_int(row.get("prior_candidate_association_count"))
    prior_depth = safe_int(row.get("prior_depth_consistent_count"))
    direction = str(row.get("prior_standoff_direction_source") or "")
    scene_query = f"{row.get('scene_key')}/{row.get('query')}"

    if inside_mask > 0:
        tags.append("mask_projection_available")
    else:
        tags.append("mask_projection_missing")
    if associated == 0:
        tags.append("association_missing_after_completion")
    else:
        tags.append("association_present_after_completion")
    if depth_consistent > 0:
        tags.append("depth_consistent_signal_present")
    else:
        tags.append("no_depth_consistent_completion_signal")
    if depth_consistent <= prior_depth:
        tags.append("no_depth_consistency_improvement")
    if prior_associated > 0 and associated == 0:
        tags.append("association_regressed_from_prior_partial_row")
    if direction:
        tags.append(f"direction_{direction}")
    if scene_query == "bxsVRursffK/plant":
        tags.append("dominant_bxsVRursffK_plant_repeated_object_slice")
    return sorted(set(tags))


def build_taxonomy_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in sorted(
        rows,
        key=lambda item: (
            sort_request_id(request_id(item)),
            safe_int(item.get("failed_evidence_index")),
            str(item.get("target_candidate_id") or item.get("candidate_id") or ""),
        ),
    ):
        residual_class = classify_residual(row)
        tags = residual_tags(row, residual_class)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_residual_taxonomy",
                "expanded_retrieval_request_id": request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "candidate_id": row.get("candidate_id"),
                "target_candidate_id": row.get("target_candidate_id"),
                "failed_evidence_index": row.get("failed_evidence_index"),
                "prior_relation_depth_evidence_status": row.get("prior_relation_depth_evidence_status"),
                "prior_standoff_direction_source": row.get("prior_standoff_direction_source"),
                "prior_candidate_association_count": row.get("prior_candidate_association_count"),
                "prior_depth_consistent_count": row.get("prior_depth_consistent_count"),
                "prior_depth_mismatch_count": row.get("prior_depth_mismatch_count"),
                "prior_inside_mask_count": row.get("prior_inside_mask_count"),
                "completion_status": row.get("completion_status"),
                "unresolved_reason": row.get("unresolved_reason"),
                "completion_evidence_rows": row.get("completion_evidence_rows"),
                "completion_direction_sources": list(row.get("completion_direction_sources") or []),
                "completion_associated_heading_count": row.get("completion_associated_heading_count"),
                "completion_associated_depth_consistent_count": row.get(
                    "completion_associated_depth_consistent_count"
                ),
                "completion_depth_consistent_count": row.get("completion_depth_consistent_count"),
                "completion_inside_mask_count": row.get("completion_inside_mask_count"),
                "residual_failure_class": residual_class,
                "residual_failure_tags": tags,
                "recommended_next_action": "freeze_residual_partial_relation_depth_failure_taxonomy",
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_request_rows(taxonomy_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in taxonomy_rows:
        grouped[request_id(row)].append(row)

    request_rows: List[Dict[str, Any]] = []
    for rid, rows in sorted(grouped.items(), key=lambda item: sort_request_id(item[0])):
        exemplar = rows[0]
        class_counts = compact_counter(row.get("residual_failure_class") for row in rows)
        tag_counts = compact_counter(tag for row in rows for tag in row.get("residual_failure_tags", []))
        if tag_counts.get("dominant_bxsVRursffK_plant_repeated_object_slice", 0):
            request_status = "repeated_object_relation_anchor_ambiguity"
            next_action = "freeze_repeated_object_relation_anchor_failure_branch"
        elif class_counts.get("association_present_without_depth_improvement", 0):
            request_status = "association_present_but_depth_not_improved"
            next_action = "freeze_depth_stagnation_failure_branch"
        else:
            request_status = "association_geometry_underlink"
            next_action = "freeze_association_geometry_failure_branch"
        request_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_partial_relation_depth_residual_request_taxonomy",
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                "episode_key": exemplar.get("episode_key"),
                "scene_key": exemplar.get("scene_key"),
                "scene_id": exemplar.get("scene_id"),
                "query": exemplar.get("query"),
                "residual_rows": len(rows),
                "residual_failure_class_counts": class_counts,
                "residual_failure_tag_counts": tag_counts,
                "rows_with_inside_mask": sum(safe_int(row.get("completion_inside_mask_count")) > 0 for row in rows),
                "rows_with_completion_association": sum(
                    safe_int(row.get("completion_associated_heading_count")) > 0 for row in rows
                ),
                "rows_with_zero_completion_association": sum(
                    safe_int(row.get("completion_associated_heading_count")) == 0 for row in rows
                ),
                "rows_with_completion_depth_consistent": sum(
                    safe_int(row.get("completion_depth_consistent_count")) > 0 for row in rows
                ),
                "request_residual_status": request_status,
                "recommended_next_action": next_action,
                "terminal_policy_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return request_rows


def summarize(
    *,
    contract: Dict[str, Any],
    evidence_summary: Dict[str, Any],
    taxonomy_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    minimum = contract.get("minimum_diagnostic_gate") or {}
    forbidden = action_forbidden_keys([*taxonomy_rows, *request_rows])
    terminal_rows = [
        row for row in [*taxonomy_rows, *request_rows]
        if row.get("terminal_commit") is True or row.get("terminal_policy_allowed") is True
    ]
    class_counts = compact_counter(row.get("residual_failure_class") for row in taxonomy_rows)
    tag_counts = compact_counter(tag for row in taxonomy_rows for tag in row.get("residual_failure_tags", []))
    reason_counts = compact_counter(row.get("unresolved_reason") for row in taxonomy_rows)
    query_counts = compact_counter(row.get("query") for row in taxonomy_rows)
    direction_counts = compact_counter(row.get("prior_standoff_direction_source") for row in taxonomy_rows)
    dominant_scene_query = str(minimum.get("dominant_scene_query") or "")
    dominant_scene, _, dominant_query = dominant_scene_query.partition("/")
    dominant_rows = [
        row
        for row in taxonomy_rows
        if str(row.get("scene_key")) == dominant_scene and str(row.get("query")) == dominant_query
    ]
    expected_class_counts = {
        str(key): safe_int(value)
        for key, value in (minimum.get("expected_taxonomy_class_counts") or {}).items()
    }
    source_gate = (evidence_summary.get("gate") or {}).get("partial_relation_depth_detector_evidence_gate_passed")
    gate = {
        "source_evidence_gate_passed": source_gate is bool(minimum.get("source_evidence_gate_passed", True)),
        "expected_unresolved_or_partial_rows_passed": len(taxonomy_rows)
        == safe_int(minimum.get("expected_unresolved_or_partial_rows")),
        "expected_unresolved_reason_passed": reason_counts
        == {str(minimum.get("expected_unresolved_reason")): len(taxonomy_rows)},
        "minimum_inside_mask_rows_passed": sum(
            safe_int(row.get("completion_inside_mask_count")) > 0 for row in taxonomy_rows
        ) >= safe_int(minimum.get("minimum_inside_mask_rows")),
        "expected_zero_completion_association_rows_passed": sum(
            safe_int(row.get("completion_associated_heading_count")) == 0 for row in taxonomy_rows
        ) == safe_int(minimum.get("expected_zero_completion_association_rows")),
        "expected_positive_completion_association_rows_passed": sum(
            safe_int(row.get("completion_associated_heading_count")) > 0 for row in taxonomy_rows
        ) == safe_int(minimum.get("expected_positive_completion_association_rows")),
        "expected_depth_consistent_completion_rows_passed": sum(
            safe_int(row.get("completion_depth_consistent_count")) > 0 for row in taxonomy_rows
        ) == safe_int(minimum.get("expected_depth_consistent_completion_rows")),
        "expected_taxonomy_class_counts_passed": class_counts == expected_class_counts,
        "minimum_dominant_scene_query_rows_passed": len(dominant_rows)
        >= safe_int(minimum.get("minimum_dominant_scene_query_rows")),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(minimum.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(minimum.get("terminal_commit_rows_maximum")),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in taxonomy_rows),
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["partial_relation_depth_residual_taxonomy_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "evidence_summary": str(args.evidence_summary),
            "unresolved_rows": str(args.unresolved_rows),
            "failed_evidence_summary_rows": str(args.failed_evidence_summary_rows),
            "request_summary_rows": str(args.request_summary_rows),
        },
        "taxonomy_rows": len(taxonomy_rows),
        "request_taxonomy_rows": len(request_rows),
        "unresolved_reason_counts": reason_counts,
        "residual_failure_class_counts": class_counts,
        "residual_failure_tag_counts": tag_counts,
        "query_counts": query_counts,
        "direction_counts": direction_counts,
        "rows_with_inside_mask": sum(safe_int(row.get("completion_inside_mask_count")) > 0 for row in taxonomy_rows),
        "rows_with_completion_association": sum(
            safe_int(row.get("completion_associated_heading_count")) > 0 for row in taxonomy_rows
        ),
        "rows_with_zero_completion_association": sum(
            safe_int(row.get("completion_associated_heading_count")) == 0 for row in taxonomy_rows
        ),
        "rows_with_completion_depth_consistent": sum(
            safe_int(row.get("completion_depth_consistent_count")) > 0 for row in taxonomy_rows
        ),
        "dominant_scene_query": dominant_scene_query,
        "dominant_scene_query_rows": len(dominant_rows),
        "request_residual_status_counts": compact_counter(row.get("request_residual_status") for row in request_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "terminal_policy_allowed": False,
            "terminal_utility_validation_allowed": False,
            "threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
            "main_residual_mechanism": "inside_mask_visible_but_candidate_associated_depth_not_improved",
            "recommended_next_action": "freeze_residual_partial_relation_depth_failure_taxonomy_before_terminal_contract",
        },
        "output_files": {
            "taxonomy_rows": "partial_relation_depth_residual_taxonomy_rows.jsonl",
            "request_taxonomy_rows": "partial_relation_depth_residual_request_taxonomy_rows.jsonl",
            "summary": "partial_relation_depth_residual_taxonomy_summary.json",
        },
        "interpretation": {
            "fact": "The taxonomy consumes nonterminal detector evidence rows and does not join evaluation labels.",
            "agent_inference": "The residual rows are not missing-render failures; they are association/depth-improvement and repeated-object relation-anchor blockers that must remain separate from terminal goal validity.",
        },
        "paper_claim_allowed": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=Path(CONTRACT_DEFAULT))
    parser.add_argument("--out-root", type=Path, default=Path(OUT_ROOT_DEFAULT))
    parser.add_argument("--evidence-summary", type=Path)
    parser.add_argument("--unresolved-rows", type=Path)
    parser.add_argument("--failed-evidence-summary-rows", type=Path)
    parser.add_argument("--request-summary-rows", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(args.contract)
    args.evidence_summary = source_path(args, contract, "evidence_summary", "partial_relation_depth_evidence_summary")
    args.unresolved_rows = source_path(args, contract, "unresolved_rows", "partial_relation_depth_unresolved_rows")
    args.failed_evidence_summary_rows = source_path(
        args,
        contract,
        "failed_evidence_summary_rows",
        "partial_relation_depth_failed_evidence_summary_rows",
    )
    args.request_summary_rows = source_path(
        args,
        contract,
        "request_summary_rows",
        "partial_relation_depth_request_summary_rows",
    )
    evidence_summary = load_json(args.evidence_summary)
    unresolved_rows = load_jsonl(args.unresolved_rows)
    # Loaded for path verification and future schema stability.
    load_jsonl(args.failed_evidence_summary_rows)
    load_jsonl(args.request_summary_rows)

    taxonomy_rows = build_taxonomy_rows(unresolved_rows)
    request_taxonomy_rows = build_request_rows(taxonomy_rows)
    summary = summarize(
        contract=contract,
        evidence_summary=evidence_summary,
        taxonomy_rows=taxonomy_rows,
        request_rows=request_taxonomy_rows,
        args=args,
    )

    args.out_root.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.out_root / "partial_relation_depth_residual_taxonomy_rows.jsonl", taxonomy_rows)
    write_jsonl(
        args.out_root / "partial_relation_depth_residual_request_taxonomy_rows.jsonl",
        request_taxonomy_rows,
    )
    write_json(args.out_root / "partial_relation_depth_residual_taxonomy_summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["partial_relation_depth_residual_taxonomy_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
