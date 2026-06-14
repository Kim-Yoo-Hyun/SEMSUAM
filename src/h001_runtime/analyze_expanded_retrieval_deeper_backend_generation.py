import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    request_sort_key,
)
from h001_runtime.run_smoke import Candidate, label_candidate_correctness, load_manifest_episodes, scene_basename


SCHEMA_VERSION = "h001.expanded_retrieval_deeper_backend_generation.v1"
SOURCE_GENERATION_STATUS = "generated_fixed_top20_pool"
GENERATION_STATUSES = [
    "generated_deeper_backend_pool",
    "request_fallback_deeper_backend_variant",
    "defer_deeper_backend_generation_unresolved",
]


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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def finite_vector(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    try:
        numbers = [float(item) for item in value]
    except (TypeError, ValueError):
        return False
    return all(math.isfinite(number) for number in numbers)


def source_action_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("candidate_generation_status") == SOURCE_GENERATION_STATUS],
        key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))),
    )


def target_request_ids(contract: Dict[str, Any]) -> List[str]:
    return [
        str(row.get("expanded_retrieval_request_id"))
        for row in contract.get("target_rows_diagnostic_after_label_join") or []
        if row.get("expanded_retrieval_request_id") is not None
    ]


def target_rows_from_source(
    action_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    ids = set(target_request_ids(contract))
    rows = [row for row in source_action_rows(action_rows) if str(row.get("expanded_retrieval_request_id")) in ids]
    return sorted(rows, key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))))


def scene_query_key(scene_key: Any, query: Any) -> str:
    return f"{scene_key}::{query}"


def normalize_scene_key(value: Any) -> str:
    text = str(value or "")
    if "/" in text:
        text = scene_basename(text)
    for suffix in (".basis.glb", ".basis.navmesh", ".glb", ".navmesh"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    return text


def parse_scene_specs(path: Optional[Path]) -> Dict[str, str]:
    if path is None or not path.exists():
        return {}
    output: Dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#"):
            continue
        scene_key = text.split("|", 1)[0]
        output[scene_key] = text
    return output


def derive_scene_rel(scene_id: str) -> str:
    if scene_id.startswith("hm3d_v0.2/"):
        return scene_id.split("hm3d_v0.2/", 1)[1]
    if scene_id.startswith("hm3d/"):
        return scene_id.split("hm3d/", 1)[1]
    return scene_id


def scene_spec_line(row: Dict[str, Any], known_specs: Dict[str, str], fallback_seed: int) -> str:
    scene_key = str(row.get("scene_key"))
    if scene_key in known_specs:
        return known_specs[scene_key]
    scene_id = str(row.get("scene_id"))
    return f"{scene_key}|{scene_id}|{derive_scene_rel(scene_id)}|{fallback_seed}"


def write_scene_specs(
    target_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    scene_spec_source: Optional[Path],
    out_path: Path,
) -> Dict[str, str]:
    known_specs = parse_scene_specs(scene_spec_source)
    by_scene: Dict[str, Dict[str, Any]] = {}
    for index, row in enumerate(target_rows, start=1):
        scene_key = str(row.get("scene_key"))
        by_scene.setdefault(scene_key, row)
    lines = ["# scene_key|scene_id|scene_rel|seed"]
    scene_lines: Dict[str, str] = {}
    for offset, scene_key in enumerate(sorted(by_scene), start=1):
        line = scene_spec_line(by_scene[scene_key], known_specs, fallback_seed=202605290 + offset)
        lines.append(line)
        scene_lines[scene_key] = line
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    expected_pairs = safe_int((contract.get("source") or {}).get("expected_target_scene_query_pairs"))
    if expected_pairs and not scene_lines:
        raise ValueError("no scene specs generated for deeper backend target rows")
    return scene_lines


def candidate_sort_key(candidate: Dict[str, Any]) -> Tuple[float, float, str]:
    return (
        -safe_float(candidate.get("score", candidate.get("semantic_score"))),
        -safe_float(candidate.get("mean_score", candidate.get("support_score"))),
        str(candidate.get("candidate_id")),
    )


def artifact_index(path: Optional[Path]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_jsonl(path):
        scene = str(row.get("scene_id") or row.get("scene") or "")
        scene_key = normalize_scene_key(scene if scene else row.get("scene_key"))
        query = str(row.get("query") or row.get("object_category") or "")
        if scene_key and query:
            indexed[(scene_key, query)] = row
    return indexed


def artifact_candidates(row: Optional[Dict[str, Any]], max_candidates: int) -> List[Dict[str, Any]]:
    if row is None:
        return []
    candidates = list(row.get("candidates") or [row])
    return sorted(candidates, key=candidate_sort_key)[:max_candidates]


def fixed_top20_ids(row: Dict[str, Any]) -> List[str]:
    return [
        str(candidate_id)
        for candidate_id in (row.get("generated_pool_accounting") or {}).get("generated_candidate_ids") or []
    ]


def candidate_position_key(candidate: Dict[str, Any]) -> Optional[str]:
    position = candidate.get("position") if finite_vector(candidate.get("position")) else candidate.get("visit_position")
    if not finite_vector(position):
        return None
    rounded = [round(float(value), 4) for value in position]
    return json.dumps(rounded, sort_keys=True)


def compact_candidate(
    candidate: Dict[str, Any],
    *,
    generated_rank: int,
    top_score: float,
    positive_score_gap: float,
    max_positive_rank: int,
) -> Dict[str, Any]:
    score = safe_float(candidate.get("score", candidate.get("semantic_score")))
    positive_support = bool(
        generated_rank <= max_positive_rank and math.isfinite(top_score) and (top_score - score) <= positive_score_gap
    )
    visit_position_navigable = candidate.get("visit_position_navigable")
    return {
        "generated_rank": generated_rank,
        "candidate_id": candidate.get("candidate_id"),
        "candidate_backend": "artifact_jsonl",
        "backend_source": candidate.get("backend_source"),
        "category": candidate.get("category"),
        "semantic_rank": generated_rank,
        "semantic_score": score,
        "support_score": score,
        "score": score,
        "mean_score": candidate.get("mean_score"),
        "positive_support": positive_support,
        "candidate_reachable": visit_position_navigable if isinstance(visit_position_navigable, bool) else None,
        "path_to_candidate": None,
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "visit_position_navigable": visit_position_navigable,
        "visit_position_snapped": candidate.get("visit_position_snapped"),
        "component_cells": candidate.get("component_cells"),
        "view_count": candidate.get("view_count"),
        "coordinate_frame": candidate.get("coordinate_frame"),
        "alignment_id": candidate.get("alignment_id"),
        "uses_gt_for_action": False,
    }


def generation_accounting(source_row: Dict[str, Any], candidates: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    fixed_ids = fixed_top20_ids(source_row)
    fixed_set = set(fixed_ids)
    generated_ids = [str(candidate.get("candidate_id")) for candidate in candidates if candidate.get("candidate_id") is not None]
    generated_set = set(generated_ids)
    position_keys = [candidate_position_key(candidate) for candidate in candidates]
    finite_positions = [key for key in position_keys if key is not None]
    reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is True)
    unknown_reachability_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is None)
    not_reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is False)
    positive_support_count = sum(1 for candidate in candidates if candidate.get("positive_support") is True)
    backend_counts = Counter(str(candidate.get("backend_source") or candidate.get("candidate_backend")) for candidate in candidates)
    return {
        "fixed_top20_candidate_count": len(fixed_ids),
        "fixed_top20_candidate_ids": fixed_ids,
        "deeper_generated_candidate_count": len(candidates),
        "deeper_generated_candidate_ids": generated_ids,
        "retained_from_top20_count": len(fixed_set & generated_set),
        "retained_from_top20_ids": sorted(fixed_set & generated_set),
        "new_beyond_top20_count": len(generated_set - fixed_set),
        "new_beyond_top20_ids_preview": sorted(generated_set - fixed_set)[:20],
        "duplicate_candidate_id_count": len(generated_ids) - len(generated_set),
        "finite_position_count": len(finite_positions),
        "nonfinite_candidate_position_count": len(candidates) - len(finite_positions),
        "unique_position_count": len(set(finite_positions)),
        "duplicate_position_count": max(0, len(finite_positions) - len(set(finite_positions))),
        "reachable_candidate_count": reachable_count,
        "unknown_reachability_count": unknown_reachability_count,
        "not_reachable_candidate_count": not_reachable_count,
        "reachable_or_standoff_candidate_count": reachable_count,
        "positive_support_candidate_count": positive_support_count,
        "backend_candidate_family_counts": dict(sorted(backend_counts.items())),
    }


def generation_decision(
    artifact_row: Optional[Dict[str, Any]],
    accounting: Dict[str, Any],
    gates: Dict[str, Any],
) -> Dict[str, Any]:
    if artifact_row is None:
        return {
            "deeper_generation_status": "defer_deeper_backend_generation_unresolved",
            "deeper_generation_reason": "deeper_candidate_artifact_row_missing",
            "deeper_generation_signals": ["candidate_artifact_row_missing"],
            "terminal_commit": False,
        }
    signals: List[str] = []
    if safe_int(accounting.get("deeper_generated_candidate_count")) < safe_int(
        gates.get("generated_candidate_count_minimum_per_target_request")
    ):
        signals.append("deeper_pool_below_candidate_count_minimum")
    if safe_int(accounting.get("new_beyond_top20_count")) < safe_int(
        gates.get("new_beyond_top20_count_minimum_per_target_request")
    ):
        signals.append("deeper_pool_has_insufficient_new_candidates_beyond_top20")
    if safe_int(accounting.get("duplicate_candidate_id_count")) > safe_int(
        gates.get("duplicate_candidate_id_count_maximum")
    ):
        signals.append("deeper_pool_duplicate_candidate_ids")
    if safe_int(accounting.get("nonfinite_candidate_position_count")) > safe_int(
        gates.get("nonfinite_candidate_position_count_maximum")
    ):
        signals.append("deeper_pool_nonfinite_candidate_positions")
    if safe_int(accounting.get("reachable_or_standoff_candidate_count")) <= 0:
        signals.append("deeper_pool_no_reachable_or_standoff_candidate")
    if signals:
        return {
            "deeper_generation_status": "request_fallback_deeper_backend_variant",
            "deeper_generation_reason": "first_variant_structural_gate_failed",
            "deeper_generation_signals": sorted(set(signals)),
            "terminal_commit": False,
        }
    return {
        "deeper_generation_status": "generated_deeper_backend_pool",
        "deeper_generation_reason": "first_variant_structural_gate_passed",
        "deeper_generation_signals": ["deeper_backend_pool_structurally_valid"],
        "terminal_commit": False,
    }


def scene_query_artifact_rows(
    target_rows: Sequence[Dict[str, Any]],
    artifact_rows: Dict[Tuple[str, str], Dict[str, Any]],
    scene_lines: Dict[str, str],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in target_rows:
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
                "request_rows": len(grouped[(scene_key, query)]),
                "expanded_retrieval_request_ids": [
                    row.get("expanded_retrieval_request_id") for row in grouped[(scene_key, query)]
                ],
                "scene_spec_line": scene_lines.get(scene_key),
                "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
                "artifact_row_found": artifact is not None,
                "artifact_candidate_count": len(candidates),
                "artifact_scene_id": (artifact or {}).get("scene_id"),
                "artifact_query": (artifact or {}).get("query"),
                "first_variant": args.variant_name,
                "uses_gt_for_action": False,
            }
        )
    return output


def build_action_rows(
    target_rows: Sequence[Dict[str, Any]],
    artifact_rows: Dict[Tuple[str, str], Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    policy = dict(contract.get("deeper_generation_policy") or {})
    variant = dict(policy.get("first_variant") or {})
    gates = dict(contract.get("evaluation_gates") or {})
    output: List[Dict[str, Any]] = []
    for row in target_rows:
        artifact_row = artifact_rows.get((str(row.get("scene_key")), str(row.get("query"))))
        raw_candidates = artifact_candidates(artifact_row, int(args.max_candidates))
        top_score = safe_float(raw_candidates[0].get("score", raw_candidates[0].get("semantic_score"))) if raw_candidates else 0.0
        candidates = [
            compact_candidate(
                candidate,
                generated_rank=index + 1,
                top_score=top_score,
                positive_score_gap=float(args.positive_score_gap),
                max_positive_rank=int(args.max_positive_rank),
            )
            for index, candidate in enumerate(raw_candidates)
        ]
        accounting = generation_accounting(row, candidates)
        decision = generation_decision(artifact_row, accounting, gates)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_only_before_label_join",
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "target_scene_query_key": scene_query_key(row.get("scene_key"), row.get("query")),
                "source_schema_version": row.get("schema_version"),
                "source_candidate_generation_status": row.get("candidate_generation_status"),
                "source_candidate_generation_reason": row.get("candidate_generation_reason"),
                "source_backend_config": row.get("backend_candidate_config"),
                "source_pool_proxy": row.get("source_pool_proxy"),
                "source_generated_pool_accounting": {
                    "generated_candidate_count": (row.get("generated_pool_accounting") or {}).get(
                        "generated_candidate_count"
                    ),
                    "generated_candidate_ids": fixed_top20_ids(row),
                    "positive_support_candidate_count": (row.get("generated_pool_accounting") or {}).get(
                        "positive_support_candidate_count"
                    ),
                    "reachable_or_standoff_candidate_count": (row.get("generated_pool_accounting") or {}).get(
                        "reachable_or_standoff_candidate_count"
                    ),
                },
                "deeper_backend_config": {
                    "policy_name": policy.get("policy_name"),
                    "diagnostic_scope": policy.get("diagnostic_scope"),
                    "candidate_backend_family": policy.get("candidate_backend_family"),
                    "variant_name": variant.get("variant_name"),
                    "selection_mode": variant.get("selection_mode"),
                    "top_percentile": variant.get("top_percentile"),
                    "max_candidates": variant.get("max_candidates"),
                    "spatial_nms_min_distance_cells": variant.get("spatial_nms_min_distance_cells"),
                    "min_component_cells": variant.get("min_component_cells"),
                    "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
                    "deterministic_sort_key": [
                        "score descending",
                        "mean_score descending",
                        "candidate_id ascending",
                    ],
                },
                "deeper_pool_accounting": accounting,
                "deeper_generated_candidates": candidates,
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
        for rank, row in enumerate(action_row.get("deeper_generated_candidates") or [], start=1):
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
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in label_rows:
        key = (str(row.get("episode_key")), str(row.get("candidate_id")))
        indexed[key] = row
    return indexed


def candidate_label_summary(
    action_row: Dict[str, Any],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    episode_key = str(action_row.get("episode_key"))
    candidate_ids = list((action_row.get("deeper_pool_accounting") or {}).get("deeper_generated_candidate_ids") or [])
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
                "validation_stage": "evaluation_joined_after_deeper_generation_rows",
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


def count_stats(values: Sequence[int]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "max": None, "mean": None}
    return {"min": min(values), "max": max(values), "mean": sum(values) / len(values)}


def count_by_status(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    counts = Counter(str(row.get("deeper_generation_status")) for row in rows)
    return {status: counts.get(status, 0) for status in GENERATION_STATUSES}


def summarize(
    *,
    source_rows: Sequence[Dict[str, Any]],
    target_rows: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    label_rows: Sequence[Dict[str, Any]],
    scene_query_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    status_counts = count_by_status(action_rows)
    reason_counts = Counter(str(row.get("deeper_generation_reason")) for row in action_rows)
    signal_counts = Counter(
        str(signal) for row in action_rows for signal in row.get("deeper_generation_signals") or []
    )
    generated_counts = [
        safe_int((row.get("deeper_pool_accounting") or {}).get("deeper_generated_candidate_count"))
        for row in action_rows
    ]
    new_counts = [
        safe_int((row.get("deeper_pool_accounting") or {}).get("new_beyond_top20_count"))
        for row in action_rows
    ]
    duplicate_counts = [
        safe_int((row.get("deeper_pool_accounting") or {}).get("duplicate_candidate_id_count"))
        for row in action_rows
    ]
    nonfinite_counts = [
        safe_int((row.get("deeper_pool_accounting") or {}).get("nonfinite_candidate_position_count"))
        for row in action_rows
    ]
    reachable_counts = [
        safe_int((row.get("deeper_pool_accounting") or {}).get("reachable_or_standoff_candidate_count"))
        for row in action_rows
    ]
    positive_counts = [
        safe_int((row.get("deeper_pool_accounting") or {}).get("positive_support_candidate_count"))
        for row in action_rows
    ]
    total_generated = sum(generated_counts)
    target_pairs = {
        scene_query_key(row.get("scene_key"), row.get("query"))
        for row in target_rows
    }
    no_valid_rows = sum(1 for row in evaluated_rows if row.get("evaluation_only_no_valid_candidate_pool") is True)
    valid_rows = sum(1 for row in evaluated_rows if row.get("evaluation_only_contains_valid_candidate") is True)
    recovered_rows = sum(
        1
        for row in evaluated_rows
        if row.get("evaluation_only_contains_valid_candidate") is True
        and safe_int((row.get("deeper_pool_accounting") or {}).get("new_beyond_top20_count")) > 0
    )
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    forbidden = action_forbidden_keys(action_rows)
    gate = {
        "input_source_rows_passed": len(source_rows) == safe_int(gates.get("input_source_rows")),
        "diagnostic_target_request_rows_passed": len(target_rows)
        == safe_int(gates.get("diagnostic_target_request_rows")),
        "target_scene_query_pairs_passed": len(target_pairs) == safe_int(gates.get("target_scene_query_pairs")),
        "generated_candidate_count_minimum_per_target_request_passed": min(generated_counts or [0])
        >= safe_int(gates.get("generated_candidate_count_minimum_per_target_request")),
        "generated_candidate_rows_minimum_passed": total_generated
        >= safe_int(gates.get("generated_candidate_rows_minimum")),
        "new_beyond_top20_count_minimum_per_target_request_passed": min(new_counts or [0])
        >= safe_int(gates.get("new_beyond_top20_count_minimum_per_target_request")),
        "duplicate_candidate_id_count_passed": max(duplicate_counts or [999999])
        <= safe_int(gates.get("duplicate_candidate_id_count_maximum")),
        "nonfinite_candidate_position_count_passed": max(nonfinite_counts or [999999])
        <= safe_int(gates.get("nonfinite_candidate_position_count_maximum")),
        "rows_with_reachable_or_standoff_candidate_passed": sum(1 for value in reachable_counts if value > 0)
        >= safe_int(gates.get("rows_with_reachable_or_standoff_candidate_minimum")),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "reports_backend_variant_counts": bool(status_counts),
        "reports_scene_query_artifact_rows": len(scene_query_rows) == len(target_pairs),
        "reports_recovery_after_label_join": bool(evaluated_rows),
        "joins_labels_only_after_generation_rows": True,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(label_rows),
        "goal_validity_confirmation_unblocked": recovered_rows > 0,
        "deeper_backend_generation_required": no_valid_rows > 0,
        "paper_claim_allowed": False,
    }
    gate["deeper_backend_generation_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "paper_claim_allowed",
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "goal_validity_confirmation_unblocked",
            "deeper_backend_generation_required",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "backend_generation_rows": str(args.backend_generation_rows),
        "backend_generation_evaluated_rows": str(args.backend_generation_evaluated_rows),
        "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
        "episode_manifest": str(args.episode_manifest) if args.episode_manifest else None,
        "episode_manifest_split": args.episode_manifest_split,
        "data_root": str(args.data_root) if args.data_root else None,
        "out_root": str(args.out_root),
        "scene_spec_output": str(args.scene_spec_output),
        "source_rows": len(source_rows),
        "target_request_rows": len(target_rows),
        "target_scene_query_pairs": len(target_pairs),
        "scene_query_artifact_rows": len(scene_query_rows),
        "action_rows": len(action_rows),
        "evaluated_rows": len(evaluated_rows),
        "evaluation_label_rows": len(label_rows),
        "terminal_commit_rows": len(terminal_rows),
        "deeper_generation_status_counts": status_counts,
        "deeper_generation_reason_counts": dict(sorted(reason_counts.items())),
        "deeper_generation_signal_counts": dict(sorted(signal_counts.items())),
        "generated_candidate_rows": total_generated,
        "generated_candidate_count_stats": count_stats(generated_counts),
        "new_beyond_top20_count_stats": count_stats(new_counts),
        "duplicate_candidate_id_count_stats": count_stats(duplicate_counts),
        "nonfinite_candidate_position_count_stats": count_stats(nonfinite_counts),
        "reachable_or_standoff_candidate_count_stats": count_stats(reachable_counts),
        "positive_support_candidate_count_stats": count_stats(positive_counts),
        "evaluation_only_contains_valid_rows": valid_rows,
        "evaluation_only_no_valid_rows": no_valid_rows,
        "recovered_valid_rows_after_deeper_generation": recovered_rows,
        "target_rows": [
            {
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
            }
            for row in target_rows
        ],
        "scene_query_artifacts": list(scene_query_rows),
        "simpler_alternative_accounting": {
            "reuse_fixed_top20_without_deeper_generation": {
                "blocked_by": "fixed_top20_post_generation_label_join_has_no_valid_rows",
                "fixed_top20_no_valid_rows": safe_int(
                    (contract.get("observed_facts") or {}).get("fixed_top20_no_valid_rows_after_label_join")
                ),
            },
            "pass_fixed_top20_directly_to_goal_validity_confirmation": {
                "blocked_by": "would_mix_no_valid_pool_failure_with_goal_validity_confirmation",
                "goal_validity_confirmation_unblocked": False,
            },
            "semantic_rank_only_deeper_topk_without_spatial_accounting": {
                "blocked_by": "contract_requires_spatial_nms_or_component_lineage_and_duplicate_reachability_accounting",
            },
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "interpretation": {
            "fact": (
                "The analyzer builds deeper backend target scene/query specs and, when a deeper "
                "candidate artifact is available, writes generation rows before GT-analysis label joins."
            ),
            "agent_inference": (
                "This tests backend recall repair for no-valid fixed top-20 pools. It is not a "
                "goal-validity confirmation rule and does not permit terminal ObjectNav commits."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(label_rows),
        "paper_claim_allowed": False,
        "output_files": {
            "generation_rows": "deeper_backend_generation_rows.jsonl",
            "evaluated_rows": "deeper_backend_generation_evaluated_rows.jsonl",
            "scene_query_artifacts": "deeper_backend_scene_query_artifacts.jsonl",
            "evaluation_labels": "deeper_backend_generation_evaluation_labels.jsonl",
            "summary": "deeper_backend_generation_summary.json",
            "scene_specs": Path(str(args.scene_spec_output)).name,
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    backend_generation_rows = load_jsonl(Path(args.backend_generation_rows))
    backend_generation_evaluated_rows = load_jsonl(Path(args.backend_generation_evaluated_rows))

    source_rows = source_action_rows(backend_generation_rows)
    target_rows = target_rows_from_source(backend_generation_rows, contract)
    expected_targets = set(target_request_ids(contract))
    observed_targets = {str(row.get("expanded_retrieval_request_id")) for row in target_rows}
    if expected_targets != observed_targets:
        raise ValueError(f"target request mismatch: expected={sorted(expected_targets)} observed={sorted(observed_targets)}")
    diagnostic_targets = {
        str(row.get("expanded_retrieval_request_id"))
        for row in backend_generation_evaluated_rows
        if row.get("evaluation_only_no_valid_candidate_pool") is True
    }
    missing_diagnostic_targets = expected_targets - diagnostic_targets
    if missing_diagnostic_targets:
        raise ValueError(
            "contract targets must be no-valid rows after evaluation-only label join: "
            f"missing={sorted(missing_diagnostic_targets)}"
        )

    scene_spec_output = Path(args.scene_spec_output) if args.scene_spec_output else out_root / "deeper_backend_scene_specs.txt"
    scene_lines = write_scene_specs(target_rows, contract, Path(args.scene_spec_source) if args.scene_spec_source else None, scene_spec_output)
    artifact_rows = artifact_index(Path(args.candidate_artifact) if args.candidate_artifact else None)
    scene_query_rows = scene_query_artifact_rows(target_rows, artifact_rows, scene_lines, args)
    action_rows = build_action_rows(target_rows, artifact_rows, contract, args)
    label_rows = build_evaluation_labels(action_rows, args)
    evaluated_rows = build_evaluated_rows(action_rows, label_rows)
    summary = summarize(
        source_rows=source_rows,
        target_rows=target_rows,
        action_rows=action_rows,
        evaluated_rows=evaluated_rows,
        label_rows=label_rows,
        scene_query_rows=scene_query_rows,
        contract=contract,
        args=args,
    )

    write_jsonl(out_root / "deeper_backend_generation_rows.jsonl", action_rows)
    write_jsonl(out_root / "deeper_backend_generation_evaluation_labels.jsonl", label_rows)
    write_jsonl(out_root / "deeper_backend_generation_evaluated_rows.jsonl", evaluated_rows)
    write_jsonl(out_root / "deeper_backend_scene_query_artifacts.jsonl", scene_query_rows)
    write_json(out_root / "deeper_backend_generation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Implement deeper backend generation target specs and candidate-pool analysis."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--backend-generation-rows", required=True)
    parser.add_argument("--backend-generation-evaluated-rows", required=True)
    parser.add_argument("--candidate-artifact", default=None)
    parser.add_argument("--episode-manifest", default=None)
    parser.add_argument("--episode-manifest-split", default="v3_fresh_validation_v1")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--scene-spec-source", default=None)
    parser.add_argument("--scene-spec-output", default=None)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--variant-name", default="spatial_nms_p90_k100_d5_v1")
    parser.add_argument("--max-candidates", type=int, default=100)
    parser.add_argument("--positive-score-gap", type=float, default=0.01)
    parser.add_argument("--max-positive-rank", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
