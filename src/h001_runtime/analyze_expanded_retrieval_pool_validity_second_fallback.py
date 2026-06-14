import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_deeper_backend_generation import (
    artifact_candidates,
    artifact_index,
    candidate_position_key,
    compact_candidate,
    count_stats,
    finite_vector,
    load_json,
    load_jsonl,
    parse_scene_specs,
    safe_float,
    safe_int,
    scene_query_key,
    write_json,
    write_jsonl,
)
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    request_sort_key,
)
from h001_runtime.analyze_expanded_retrieval_pool_validity_branch import (
    derive_scene_rel,
    scene_spec_line,
    source_branch_rows,
    source_pool_summary,
)
from h001_runtime.run_smoke import Candidate, label_candidate_correctness, load_manifest_episodes


SCHEMA_VERSION = "h001.expanded_retrieval_pool_validity_second_fallback.v1"
SECOND_FALLBACK_STATUSES = [
    "generated_component_fallback_pool",
    "defer_component_fallback_unresolved",
]


def target_request_ids(contract: Dict[str, Any]) -> List[str]:
    return [str(value) for value in ((contract.get("source") or {}).get("expected_branch_request_ids") or [])]


def target_scene_query_keys(contract: Dict[str, Any]) -> List[str]:
    return [str(value) for value in ((contract.get("source") or {}).get("expected_target_scene_query_keys") or [])]


def row_index(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {
        str(row.get("expanded_retrieval_request_id")): dict(row)
        for row in rows
        if row.get("expanded_retrieval_request_id") is not None
    }


def write_scene_specs(
    branch_rows: Sequence[Dict[str, Any]],
    scene_spec_source: Optional[Path],
    out_path: Path,
) -> Dict[str, str]:
    known_specs = parse_scene_specs(scene_spec_source)
    by_scene: Dict[str, Dict[str, Any]] = {}
    for row in branch_rows:
        by_scene.setdefault(str(row.get("scene_key")), row)
    lines = ["# scene_key|scene_id|scene_rel|seed"]
    scene_lines: Dict[str, str] = {}
    for offset, scene_key in enumerate(sorted(by_scene), start=1):
        row = by_scene[scene_key]
        line = scene_spec_line(row, known_specs, fallback_seed=202605292 + offset)
        if not line:
            scene_id = str(row.get("scene_id"))
            line = f"{scene_key}|{scene_id}|{derive_scene_rel(scene_id)}|{202605292 + offset}"
        lines.append(line)
        scene_lines[scene_key] = line
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not scene_lines:
        raise ValueError("no scene specs generated for pool-validity second fallback branch")
    return scene_lines


def generated_ids(row: Optional[Dict[str, Any]], accounting_key: str, ids_key: str) -> List[str]:
    if row is None:
        return []
    return [str(value) for value in (row.get(accounting_key) or {}).get(ids_key) or []]


def previous_component_inputs(
    branch_row: Dict[str, Any],
    deeper_row: Optional[Dict[str, Any]],
    first_fallback_row: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    source_summary = source_pool_summary(branch_row, deeper_row)
    first_accounting = dict((first_fallback_row or {}).get("fallback_pool_accounting") or {})
    first_ids = [str(value) for value in first_accounting.get("fallback_generated_candidate_ids") or []]
    return {
        "source_pool": {
            "variant": source_summary.get("source_variant"),
            "candidate_count": source_summary.get("candidate_count"),
            "reachable_or_standoff_candidate_count": source_summary.get("reachable_or_standoff_candidate_count"),
            "positive_support_candidate_count": source_summary.get("positive_support_candidate_count"),
            "duplicate_candidate_id_count": source_summary.get("duplicate_candidate_id_count"),
            "nonfinite_candidate_position_count": source_summary.get("nonfinite_candidate_position_count"),
            "candidate_ids": source_summary.get("candidate_ids") or [],
        },
        "first_fallback_pool": {
            "variant": ((first_fallback_row or {}).get("fallback_backend_config") or {}).get("variant_name"),
            "fallback_generation_status": (first_fallback_row or {}).get("fallback_generation_status"),
            "candidate_count": safe_int(first_accounting.get("fallback_generated_candidate_count")),
            "retained_from_source_pool_count": safe_int(first_accounting.get("retained_from_previous_pool_count")),
            "new_beyond_source_pool_count": safe_int(first_accounting.get("new_beyond_previous_pool_count")),
            "reachable_or_standoff_candidate_count": safe_int(
                first_accounting.get("reachable_or_standoff_candidate_count")
            ),
            "positive_support_candidate_count": safe_int(first_accounting.get("positive_support_candidate_count")),
            "duplicate_candidate_id_count": safe_int(first_accounting.get("duplicate_candidate_id_count")),
            "nonfinite_candidate_position_count": safe_int(first_accounting.get("nonfinite_candidate_position_count")),
            "candidate_ids": first_ids,
        },
    }


def position_set(candidates: Sequence[Dict[str, Any]]) -> set[str]:
    return {key for key in (candidate_position_key(candidate) for candidate in candidates) if key is not None}


def component_accounting(
    source_ids: Sequence[str],
    first_fallback_ids: Sequence[str],
    source_candidates: Sequence[Dict[str, Any]],
    first_fallback_candidates: Sequence[Dict[str, Any]],
    component_candidates: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    source_set = set(str(value) for value in source_ids)
    first_set = set(str(value) for value in first_fallback_ids)
    component_ids = [
        str(candidate.get("candidate_id"))
        for candidate in component_candidates
        if candidate.get("candidate_id") is not None
    ]
    component_set = set(component_ids)
    position_keys = [candidate_position_key(candidate) for candidate in component_candidates]
    finite_positions = [key for key in position_keys if key is not None]
    source_positions = position_set(source_candidates)
    first_positions = position_set(first_fallback_candidates)
    component_positions = set(finite_positions)
    component_cells = [safe_int(candidate.get("component_cells"), 0) for candidate in component_candidates]
    reachable_count = sum(1 for candidate in component_candidates if candidate.get("candidate_reachable") is True)
    unknown_reachability_count = sum(
        1 for candidate in component_candidates if candidate.get("candidate_reachable") is None
    )
    not_reachable_count = sum(1 for candidate in component_candidates if candidate.get("candidate_reachable") is False)
    positive_support_count = sum(1 for candidate in component_candidates if candidate.get("positive_support") is True)
    backend_counts = Counter(
        str(candidate.get("backend_source") or candidate.get("candidate_backend")) for candidate in component_candidates
    )
    return {
        "source_pool_candidate_count": len(source_ids),
        "first_fallback_pool_candidate_count": len(first_fallback_ids),
        "component_candidate_count": len(component_candidates),
        "component_candidate_ids": component_ids,
        "component_candidate_ids_preview": component_ids[:20],
        "component_candidate_id_overlap_with_source_pool_count": len(component_set & source_set),
        "component_candidate_id_overlap_with_first_fallback_count": len(component_set & first_set),
        "component_position_overlap_with_source_pool_count": len(component_positions & source_positions),
        "component_position_overlap_with_first_fallback_count": len(component_positions & first_positions),
        "component_new_position_beyond_source_pool_count": len(component_positions - source_positions),
        "component_new_position_beyond_first_fallback_count": len(component_positions - first_positions),
        "duplicate_candidate_id_count": len(component_ids) - len(component_set),
        "finite_position_count": len(finite_positions),
        "nonfinite_candidate_position_count": len(component_candidates) - len(finite_positions),
        "unique_position_count": len(component_positions),
        "duplicate_position_count": max(0, len(finite_positions) - len(component_positions)),
        "reachable_candidate_count": reachable_count,
        "unknown_reachability_count": unknown_reachability_count,
        "not_reachable_candidate_count": not_reachable_count,
        "reachable_or_standoff_candidate_count": reachable_count,
        "positive_support_candidate_count": positive_support_count,
        "component_cells_stats": count_stats(component_cells),
        "backend_candidate_family_counts": dict(sorted(backend_counts.items())),
    }


def second_fallback_decision(
    artifact_row: Optional[Dict[str, Any]],
    accounting: Dict[str, Any],
    gates: Dict[str, Any],
) -> Dict[str, Any]:
    if artifact_row is None:
        return {
            "second_fallback_status": "defer_component_fallback_unresolved",
            "second_fallback_reason": "component_candidate_artifact_row_missing",
            "second_fallback_signals": ["candidate_artifact_row_missing"],
            "terminal_commit": False,
        }
    signals: List[str] = []
    if safe_int(accounting.get("component_candidate_count")) < safe_int(
        gates.get("component_candidate_count_minimum_per_request")
    ):
        signals.append("component_pool_below_candidate_count_minimum")
    if safe_int(accounting.get("duplicate_candidate_id_count")) > safe_int(
        gates.get("duplicate_candidate_id_count_maximum")
    ):
        signals.append("component_pool_duplicate_candidate_ids")
    if safe_int(accounting.get("nonfinite_candidate_position_count")) > safe_int(
        gates.get("nonfinite_candidate_position_count_maximum")
    ):
        signals.append("component_pool_nonfinite_candidate_positions")
    if safe_int(accounting.get("reachable_or_standoff_candidate_count")) <= 0:
        signals.append("component_pool_no_reachable_or_standoff_candidate")
    if signals:
        return {
            "second_fallback_status": "defer_component_fallback_unresolved",
            "second_fallback_reason": "component_fallback_structural_gate_failed",
            "second_fallback_signals": sorted(set(signals)),
            "terminal_commit": False,
        }
    return {
        "second_fallback_status": "generated_component_fallback_pool",
        "second_fallback_reason": "component_fallback_structural_gate_passed",
        "second_fallback_signals": ["component_backend_pool_structurally_valid"],
        "terminal_commit": False,
    }


def scene_query_artifact_rows(
    branch_rows: Sequence[Dict[str, Any]],
    artifact_rows: Dict[Tuple[str, str], Dict[str, Any]],
    scene_lines: Dict[str, str],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in branch_rows:
        grouped[(str(row.get("scene_key")), str(row.get("query")))].append(row)
    output: List[Dict[str, Any]] = []
    for scene_key, query in sorted(grouped):
        artifact = artifact_rows.get((scene_key, query))
        candidates = list((artifact or {}).get("candidates") or [])
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "target_scene_query_key": scene_query_key(scene_key, query),
                "scene_key": scene_key,
                "query": query,
                "branch_rows": len(grouped[(scene_key, query)]),
                "expanded_retrieval_request_ids": [
                    row.get("expanded_retrieval_request_id") for row in grouped[(scene_key, query)]
                ],
                "scene_spec_line": scene_lines.get(scene_key),
                "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
                "artifact_row_found": artifact is not None,
                "artifact_candidate_count": len(candidates),
                "artifact_scene_id": (artifact or {}).get("scene_id"),
                "artifact_query": (artifact or {}).get("query"),
                "second_fallback_variant": args.variant_name,
                "uses_gt_for_action": False,
            }
        )
    return output


def build_action_rows(
    branch_rows: Sequence[Dict[str, Any]],
    deeper_rows: Dict[str, Dict[str, Any]],
    previous_generation_rows: Dict[str, Dict[str, Any]],
    artifact_rows: Dict[Tuple[str, str], Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    policy = dict(contract.get("second_fallback_backend_policy") or {})
    variant = dict(policy.get("second_fallback_variant") or {})
    gates = dict(contract.get("evaluation_gates") or {})
    output: List[Dict[str, Any]] = []
    for row in branch_rows:
        request_id = str(row.get("expanded_retrieval_request_id"))
        deeper_row = deeper_rows.get(request_id)
        first_row = previous_generation_rows.get(request_id)
        artifact_row = artifact_rows.get((str(row.get("scene_key")), str(row.get("query"))))
        raw_candidates = artifact_candidates(artifact_row, int(args.max_candidates))
        top_score = safe_float(raw_candidates[0].get("score", raw_candidates[0].get("semantic_score"))) if raw_candidates else -math.inf
        candidates = [
            compact_candidate(
                candidate,
                generated_rank=index + 1,
                top_score=float(top_score),
                positive_score_gap=float(args.positive_score_gap),
                max_positive_rank=int(args.max_positive_rank),
            )
            for index, candidate in enumerate(raw_candidates)
        ]
        first_fallback_candidates = list((first_row or {}).get("fallback_generated_candidates") or [])
        inputs = previous_component_inputs(row, deeper_row, first_row)
        source_ids = inputs["source_pool"]["candidate_ids"]
        first_ids = inputs["first_fallback_pool"]["candidate_ids"]
        source_candidates = [
            {"candidate_id": candidate_id}
            for candidate_id in source_ids
        ]
        if deeper_row is not None:
            source_candidates = list((deeper_row.get("deeper_generated_candidates") or []))
        accounting = component_accounting(
            source_ids,
            first_ids,
            source_candidates,
            first_fallback_candidates,
            candidates,
        )
        decision = second_fallback_decision(artifact_row, accounting, gates)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_only_before_label_join",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "target_scene_query_key": scene_query_key(row.get("scene_key"), row.get("query")),
                "source_schema_version": row.get("schema_version"),
                "source_handoff_action": row.get("handoff_action"),
                "source_handoff_reason": row.get("handoff_reason"),
                "source_deeper_generation_status": row.get("source_deeper_generation_status"),
                "source_deeper_generation_reason": row.get("source_deeper_generation_reason"),
                "source_deeper_backend_config": row.get("source_deeper_backend_config"),
                "previous_backend_inputs": inputs,
                "second_fallback_backend_config": {
                    "policy_name": policy.get("policy_name"),
                    "diagnostic_scope": policy.get("diagnostic_scope"),
                    "variant_name": variant.get("variant_name"),
                    "selection_mode": variant.get("selection_mode"),
                    "top_percentile": variant.get("top_percentile"),
                    "max_candidates": variant.get("max_candidates"),
                    "spatial_nms_min_distance_cells": variant.get("spatial_nms_min_distance_cells"),
                    "min_component_cells": variant.get("min_component_cells"),
                    "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
                    "deterministic_sort_key": [
                        "score descending",
                        "component_cells descending",
                        "candidate_id ascending",
                    ],
                },
                "second_fallback_pool_accounting": accounting,
                "second_fallback_generated_candidates": candidates,
                "uses_gt_for_action": False,
                **decision,
            }
        )
    return output


def candidate_from_row(row: Dict[str, Any]) -> Candidate:
    position = row.get("position")
    visit_position = row.get("visit_position") or position
    if not finite_vector(position) or not finite_vector(visit_position):
        raise ValueError(f"cannot label candidate without finite position: {row.get('candidate_id')}")
    return Candidate(
        candidate_id=str(row.get("candidate_id")),
        category=str(row.get("category") or ""),
        object_id=None,
        object_name=None,
        position=[float(value) for value in position],
        visit_position=[float(value) for value in visit_position],
        visit_rotation=[0.0, 0.0, 0.0, 1.0],
        score=safe_float(row.get("score", row.get("semantic_score"))),
        view_count=safe_int(row.get("view_count")),
        backend_name="artifact_jsonl",
        uses_gt_for_action=False,
    )


def build_evaluation_labels(
    action_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    if not args.data_root or not args.episode_manifest:
        return []
    loaded = load_manifest_episodes(
        Path(args.data_root),
        Path(args.episode_manifest),
        str(args.episode_manifest_split),
        0,
    )
    by_episode = {str(item.manifest_row.get("episode_key")): item for item in loaded if item.manifest_row}
    label_rows: List[Dict[str, Any]] = []
    for action_row in action_rows:
        item = by_episode.get(str(action_row.get("episode_key")))
        if item is None:
            continue
        candidates: List[Candidate] = []
        ranks_by_id: Dict[str, int] = {}
        for rank, row in enumerate(action_row.get("second_fallback_generated_candidates") or [], start=1):
            candidate_id = str(row.get("candidate_id"))
            ranks_by_id[candidate_id] = rank
            try:
                candidates.append(candidate_from_row(row))
            except ValueError:
                label_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "episode_key": action_row.get("episode_key"),
                        "expanded_retrieval_request_id": action_row.get("expanded_retrieval_request_id"),
                        "scene_key": action_row.get("scene_key"),
                        "query": action_row.get("query"),
                        "candidate_id": candidate_id,
                        "evaluation_only_candidate_correct": None,
                        "evaluation_only_correct_source": "unlabeled_nonfinite_position",
                        "evaluation_only_candidate_rank": rank,
                        "evaluation_only_candidate_score": safe_float(row.get("score", row.get("semantic_score"))),
                        "uses_gt_for_action": False,
                        "uses_gt_for_analysis": True,
                    }
                )
        label_candidate_correctness(item, candidates)
        for candidate in candidates:
            label_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "episode_key": action_row.get("episode_key"),
                    "expanded_retrieval_request_id": action_row.get("expanded_retrieval_request_id"),
                    "scene_key": action_row.get("scene_key"),
                    "query": action_row.get("query"),
                    "candidate_id": candidate.candidate_id,
                    "evaluation_only_candidate_correct": candidate.correct,
                    "evaluation_only_correct_source": candidate.correct_source,
                    "evaluation_only_candidate_rank": ranks_by_id.get(candidate.candidate_id),
                    "evaluation_only_candidate_score": candidate.score,
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                }
            )
    return label_rows


def label_index(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row.get("episode_key")), str(row.get("candidate_id"))): row
        for row in label_rows
        if row.get("episode_key") is not None and row.get("candidate_id") is not None
    }


def candidate_label_summary(
    action_row: Dict[str, Any],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    episode_key = str(action_row.get("episode_key"))
    candidate_ids = list(
        (action_row.get("second_fallback_pool_accounting") or {}).get("component_candidate_ids") or []
    )
    label_rows = [labels.get((episode_key, str(candidate_id))) for candidate_id in candidate_ids]
    labeled_rows = [row for row in label_rows if row is not None]
    correct_ids = [
        str(candidate_id)
        for candidate_id, label in zip(candidate_ids, label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is True
    ]
    wrong_ids = [
        str(candidate_id)
        for candidate_id, label in zip(candidate_ids, label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is False
    ]
    correct_ranks = [
        index + 1
        for index, label in enumerate(label_rows)
        if label is not None and label.get("evaluation_only_candidate_correct") is True
    ]
    return {
        "evaluation_only_candidate_count": len(candidate_ids),
        "evaluation_only_labeled_candidate_count": len(labeled_rows),
        "evaluation_only_unlabeled_candidate_count": len(candidate_ids) - len(labeled_rows),
        "evaluation_only_correct_candidate_count": len(correct_ids),
        "evaluation_only_wrong_candidate_count": len(wrong_ids),
        "evaluation_only_correct_candidate_ids": correct_ids,
        "evaluation_only_wrong_candidate_ids_preview": wrong_ids[:10],
        "evaluation_only_first_correct_generated_rank": min(correct_ranks) if correct_ranks else None,
        "evaluation_only_no_valid_candidate_pool": len(correct_ids) == 0,
        "evaluation_only_contains_valid_candidate": len(correct_ids) > 0,
    }


def build_evaluated_rows(
    action_rows: Sequence[Dict[str, Any]],
    evaluation_labels: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    labels = label_index(evaluation_labels)
    output: List[Dict[str, Any]] = []
    for row in action_rows:
        summary = candidate_label_summary(row, labels)
        output.append(
            {
                **row,
                "validation_stage": "evaluation_joined_after_component_generation_rows",
                "evaluation_candidate_summary": summary,
                "evaluation_only_contains_valid_candidate": summary.get("evaluation_only_contains_valid_candidate"),
                "evaluation_only_no_valid_candidate_pool": summary.get("evaluation_only_no_valid_candidate_pool"),
                "evaluation_only_correct_candidate_count": summary.get("evaluation_only_correct_candidate_count"),
                "evaluation_only_wrong_candidate_count": summary.get("evaluation_only_wrong_candidate_count"),
                "evaluation_only_correct_candidate_ids": summary.get("evaluation_only_correct_candidate_ids"),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return output


def count_by_status(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(str(row.get("second_fallback_status")) for row in rows)
    return {status: counts.get(status, 0) for status in SECOND_FALLBACK_STATUSES}


def summarize(
    *,
    branch_rows: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    label_rows: Sequence[Dict[str, Any]],
    scene_query_rows: Sequence[Dict[str, Any]],
    previous_evaluated_rows: Dict[str, Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    expected_ids = target_request_ids(contract)
    expected_scene_queries = target_scene_query_keys(contract)
    observed_ids = [str(row.get("expanded_retrieval_request_id")) for row in branch_rows]
    observed_scene_queries = [scene_query_key(row.get("scene_key"), row.get("query")) for row in branch_rows]
    status_counts = count_by_status(action_rows)
    reason_counts = Counter(str(row.get("second_fallback_reason")) for row in action_rows)
    signal_counts = Counter(str(signal) for row in action_rows for signal in row.get("second_fallback_signals") or [])
    component_counts = [
        safe_int((row.get("second_fallback_pool_accounting") or {}).get("component_candidate_count"))
        for row in action_rows
    ]
    duplicate_counts = [
        safe_int((row.get("second_fallback_pool_accounting") or {}).get("duplicate_candidate_id_count"))
        for row in action_rows
    ]
    nonfinite_counts = [
        safe_int((row.get("second_fallback_pool_accounting") or {}).get("nonfinite_candidate_position_count"))
        for row in action_rows
    ]
    reachable_counts = [
        safe_int((row.get("second_fallback_pool_accounting") or {}).get("reachable_or_standoff_candidate_count"))
        for row in action_rows
    ]
    positive_counts = [
        safe_int((row.get("second_fallback_pool_accounting") or {}).get("positive_support_candidate_count"))
        for row in action_rows
    ]
    new_beyond_first_position_counts = [
        safe_int((row.get("second_fallback_pool_accounting") or {}).get("component_new_position_beyond_first_fallback_count"))
        for row in action_rows
    ]
    component_cells = [
        safe_int(candidate.get("component_cells"), 0)
        for row in action_rows
        for candidate in row.get("second_fallback_generated_candidates") or []
    ]
    no_valid_rows = sum(1 for row in evaluated_rows if row.get("evaluation_only_no_valid_candidate_pool") is True)
    valid_rows = sum(1 for row in evaluated_rows if row.get("evaluation_only_contains_valid_candidate") is True)
    recovered_rows = sum(
        1
        for row in evaluated_rows
        if row.get("evaluation_only_contains_valid_candidate") is True
        and safe_int((row.get("second_fallback_pool_accounting") or {}).get("component_candidate_count")) > 0
    )
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    forbidden = action_forbidden_keys(action_rows)
    variant = ((contract.get("second_fallback_backend_policy") or {}).get("second_fallback_variant") or {})
    first_evaluated = [previous_evaluated_rows.get(request_id) for request_id in observed_ids]
    first_structural = all(
        ((row.get("previous_backend_inputs") or {}).get("first_fallback_pool") or {}).get(
            "fallback_generation_status"
        )
        == "generated_pool_validity_fallback_pool"
        for row in action_rows
    )
    first_no_valid = all(
        row is not None and row.get("evaluation_only_no_valid_candidate_pool") is True
        for row in first_evaluated
    )
    gate = {
        "input_branch_rows_passed": len(branch_rows) == safe_int(gates.get("input_branch_rows")),
        "target_request_ids_passed": observed_ids == expected_ids,
        "target_scene_query_keys_passed": observed_scene_queries == expected_scene_queries,
        "first_fallback_structural_gate_passed": first_structural
        == bool(gates.get("first_fallback_must_be_structurally_valid")),
        "first_fallback_no_valid_after_label_join_passed": first_no_valid
        == bool(gates.get("first_fallback_must_be_no_valid_after_label_join")),
        "second_fallback_backend_variant_required": bool(gates.get("second_fallback_backend_variant_required")),
        "second_fallback_variant_fixed": str(variant.get("variant_name")) == str(gates.get("second_fallback_variant")),
        "second_fallback_selection_mode_fixed": str(variant.get("selection_mode"))
        == str(gates.get("second_fallback_selection_mode")),
        "component_candidate_count_minimum_passed": min(component_counts or [0])
        >= safe_int(gates.get("component_candidate_count_minimum_per_request")),
        "component_candidate_count_primary_target_passed": min(component_counts or [0])
        >= safe_int(gates.get("component_candidate_count_primary_target_per_request")),
        "duplicate_candidate_id_count_passed": max(duplicate_counts or [999999])
        <= safe_int(gates.get("duplicate_candidate_id_count_maximum")),
        "nonfinite_candidate_position_count_passed": max(nonfinite_counts or [999999])
        <= safe_int(gates.get("nonfinite_candidate_position_count_maximum")),
        "rows_with_reachable_or_standoff_candidate_passed": sum(1 for value in reachable_counts if value > 0)
        >= safe_int(gates.get("rows_with_reachable_or_standoff_candidate_minimum")),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "reports_component_settings": all(bool((row.get("second_fallback_backend_config") or {}).get("selection_mode")) for row in action_rows),
        "reports_overlap_with_source_and_first_fallback": all(
            "component_position_overlap_with_first_fallback_count" in (row.get("second_fallback_pool_accounting") or {})
            for row in action_rows
        ),
        "reports_scene_query_artifact_rows": len(scene_query_rows) == len(set(observed_scene_queries)),
        "reports_recovery_after_label_join": bool(evaluated_rows),
        "joins_labels_only_after_generation_rows": True,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(label_rows),
        "goal_validity_confirmation_unblocked": recovered_rows > 0,
        "backend_source_map_blind_spot_after_second_fallback": no_valid_rows > 0,
        "paper_claim_allowed": False,
    }
    gate["second_fallback_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "paper_claim_allowed",
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "goal_validity_confirmation_unblocked",
            "backend_source_map_blind_spot_after_second_fallback",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "branch_rows_path": str(args.branch_rows),
        "previous_generation_rows": str(args.previous_generation_rows),
        "previous_evaluated_rows": str(args.previous_evaluated_rows),
        "deeper_generation_rows": str(args.deeper_generation_rows),
        "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
        "episode_manifest": str(args.episode_manifest) if args.episode_manifest else None,
        "episode_manifest_split": args.episode_manifest_split,
        "data_root": str(args.data_root) if args.data_root else None,
        "out_root": str(args.out_root),
        "scene_spec_output": str(args.scene_spec_output),
        "branch_rows": len(branch_rows),
        "action_rows": len(action_rows),
        "evaluated_rows": len(evaluated_rows),
        "evaluation_label_rows": len(label_rows),
        "scene_query_artifact_rows": len(scene_query_rows),
        "terminal_commit_rows": len(terminal_rows),
        "second_fallback_status_counts": status_counts,
        "second_fallback_reason_counts": dict(sorted(reason_counts.items())),
        "second_fallback_signal_counts": dict(sorted(signal_counts.items())),
        "component_generated_candidate_rows": sum(component_counts),
        "component_candidate_count_stats": count_stats(component_counts),
        "component_cells_stats": count_stats(component_cells),
        "component_new_position_beyond_first_fallback_stats": count_stats(new_beyond_first_position_counts),
        "duplicate_candidate_id_count_stats": count_stats(duplicate_counts),
        "nonfinite_candidate_position_count_stats": count_stats(nonfinite_counts),
        "reachable_or_standoff_candidate_count_stats": count_stats(reachable_counts),
        "positive_support_candidate_count_stats": count_stats(positive_counts),
        "evaluation_only_contains_valid_rows": valid_rows,
        "evaluation_only_no_valid_rows": no_valid_rows,
        "recovered_valid_rows_after_second_fallback": recovered_rows,
        "target_request_ids": observed_ids,
        "target_scene_query_keys": observed_scene_queries,
        "scene_query_artifacts": list(scene_query_rows),
        "simpler_alternative_accounting": {
            "treat_first_fallback_spatial_nms_pool_as_valid": {
                "blocked_by": "first fallback is structurally valid but evaluation-only no-valid",
                "terminal_commit_allowed": False,
            },
            "pass_first_fallback_no_valid_row_to_goal_validity_confirmation": {
                "blocked_by": "would mix backend recall failure with goal-validity confirmation",
                "terminal_commit_allowed": False,
            },
            "lower_spatial_nms_percentile_again": {
                "blocked_by": "second contract changes backend granularity instead of repeated threshold tuning",
                "second_fallback_variant": variant.get("variant_name"),
            },
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "interpretation": {
            "fact": (
                "The analyzer consumes one first-fallback no-valid branch row and writes component "
                "fallback generation rows before any GT-analysis label join."
            ),
            "agent_inference": (
                "This tests whether connected-component export repairs a source-map candidate recall "
                "failure that wider spatial NMS did not repair. It is not a terminal commitment rule."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(label_rows),
        "paper_claim_allowed": False,
        "output_files": {
            "branch_rows": "second_fallback_branch_rows.jsonl",
            "generation_rows": "second_fallback_generation_rows.jsonl",
            "evaluation_labels": "second_fallback_evaluation_labels.jsonl",
            "evaluated_rows": "second_fallback_evaluated_rows.jsonl",
            "scene_query_artifacts": "second_fallback_scene_query_artifacts.jsonl",
            "summary": "second_fallback_summary.json",
            "scene_specs": Path(str(args.scene_spec_output)).name,
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    branch_rows_all = load_jsonl(Path(args.branch_rows))
    deeper_rows = row_index(load_jsonl(Path(args.deeper_generation_rows)))
    previous_generation_rows = row_index(load_jsonl(Path(args.previous_generation_rows)))
    previous_evaluated_rows = row_index(load_jsonl(Path(args.previous_evaluated_rows)))
    branch_rows = source_branch_rows(branch_rows_all, contract)
    expected_ids = target_request_ids(contract)
    observed_ids = [str(row.get("expanded_retrieval_request_id")) for row in branch_rows]
    if observed_ids != expected_ids:
        raise ValueError(f"branch rows {observed_ids} do not match contract {expected_ids}")
    scene_spec_output = Path(args.scene_spec_output) if args.scene_spec_output else out_root / "second_fallback_scene_specs.txt"
    scene_lines = write_scene_specs(
        branch_rows,
        Path(args.scene_spec_source) if args.scene_spec_source else None,
        scene_spec_output,
    )
    artifacts = artifact_index(Path(args.candidate_artifact) if args.candidate_artifact else None)
    scene_query_rows = scene_query_artifact_rows(branch_rows, artifacts, scene_lines, args)
    action_rows = build_action_rows(
        branch_rows,
        deeper_rows,
        previous_generation_rows,
        artifacts,
        contract,
        args,
    )
    label_rows = build_evaluation_labels(action_rows, args)
    evaluated_rows = build_evaluated_rows(action_rows, label_rows)
    summary = summarize(
        branch_rows=branch_rows,
        action_rows=action_rows,
        evaluated_rows=evaluated_rows,
        label_rows=label_rows,
        scene_query_rows=scene_query_rows,
        previous_evaluated_rows=previous_evaluated_rows,
        contract=contract,
        args=args,
    )
    write_jsonl(out_root / "second_fallback_branch_rows.jsonl", branch_rows)
    write_jsonl(out_root / "second_fallback_generation_rows.jsonl", action_rows)
    write_jsonl(out_root / "second_fallback_evaluation_labels.jsonl", label_rows)
    write_jsonl(out_root / "second_fallback_evaluated_rows.jsonl", evaluated_rows)
    write_jsonl(out_root / "second_fallback_scene_query_artifacts.jsonl", scene_query_rows)
    write_json(out_root / "second_fallback_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Implement the component backend second fallback for expanded retrieval pool validity."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--branch-rows", required=True)
    parser.add_argument("--previous-generation-rows", required=True)
    parser.add_argument("--previous-evaluated-rows", required=True)
    parser.add_argument("--deeper-generation-rows", required=True)
    parser.add_argument("--candidate-artifact", default=None)
    parser.add_argument("--episode-manifest", default=None)
    parser.add_argument("--episode-manifest-split", default="v3_fresh_validation_v1")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--scene-spec-source", default=None)
    parser.add_argument("--scene-spec-output", default=None)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--variant-name", default="components_p80_min1_k200_v1")
    parser.add_argument("--max-candidates", type=int, default=200)
    parser.add_argument("--positive-score-gap", type=float, default=0.01)
    parser.add_argument("--max-positive-rank", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
