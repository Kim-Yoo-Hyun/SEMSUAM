import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_multi_case_source.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_multi_case_scaling_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_source_v1"

OUTPUT_FILES = {
    "source_rows": "rival_contradiction_region_contamination_multi_case_source_rows.jsonl",
    "candidate_role_rows": "rival_contradiction_region_contamination_multi_case_candidate_role_rows.jsonl",
    "observation_plan_seed_rows": "rival_contradiction_region_contamination_multi_case_observation_seed_rows.jsonl",
    "audit_rows": "rival_contradiction_region_contamination_multi_case_audit_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_multi_case_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_a_correctness_label_for_evaluation_only",
    "candidate_b_correctness_label_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "candidate_a_wrong_label_for_evaluation_only",
    "candidate_b_wrong_label_for_evaluation_only",
    "candidate_pair_label_pattern_for_evaluation_only",
    "pair_label_is_action_forbidden",
    "terminal_selector_allowed_from_pair_label",
    "wrong_goal_visit_proxy",
    "success_commit_proxy",
    "terminal_commit_proxy",
    "wasted_path_proxy_m",
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "oracle_shortest_path",
    "ground_truth",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "post_hoc_label_tuned_threshold",
}

ROLE_EVIDENCE_AXIS = {
    "candidate_a_own_view": "candidate_a_own_region_evidence",
    "candidate_b_own_view": "candidate_b_own_region_evidence",
    "shared_region_or_relation_anchor_view": "shared_region_or_relation_context_overlap",
    "cross_candidate_challenge_view": "cross_candidate_contamination_or_relation_leakage",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def resolve_path(path: Any) -> Path:
    raw = Path(str(path))
    if raw.exists():
        return raw
    workspace_path = Path("/workspace") / raw
    if workspace_path.exists():
        return workspace_path
    raw_text = str(raw)
    if raw_text.startswith("local_dataset/runs/"):
        runs_path = Path("/runs") / raw_text.removeprefix("local_dataset/runs/")
        if runs_path.exists():
            return runs_path
    return raw


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result if math.isfinite(result) else default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def join_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return tuple(str(source.get(key) or row.get(key) or "") for key in JOIN_KEYS)  # type: ignore[return-value]


def candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("candidate_id") or row.get("candidate_id") or ""))


def pair_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        *join_key(row),
        str(source.get("candidate_a_id") or row.get("candidate_a_id") or ""),
        str(source.get("candidate_b_id") or row.get("candidate_b_id") or ""),
    )


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def row_matches_filter(row: Mapping[str, Any], frozen_filter: Mapping[str, Any]) -> bool:
    return (
        row.get("source_name") == frozen_filter.get("source_name")
        and row.get("target_role") == frozen_filter.get("target_role")
        and row.get("selected_branch") == frozen_filter.get("selected_branch")
        and row.get("selected_action") == frozen_filter.get("selected_action")
        and row.get("source_resolution_route") == frozen_filter.get("source_resolution_route")
        and row.get("terminal_commit") is frozen_filter.get("terminal_commit")
        and row.get("candidate_commit") is frozen_filter.get("candidate_commit")
        and row.get("candidate_rejection") is frozen_filter.get("candidate_rejection")
        and row.get("uses_gt_for_action") is frozen_filter.get("uses_gt_for_action")
    )


def action_source_inputs(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "source_name": row.get("source_name"),
        "scene_key": row.get("scene_key"),
        "query": row.get("query"),
        "request_id": row.get("request_id"),
        "episode_key": row.get("episode_key"),
        "candidate_a_id": row.get("candidate_a_id"),
        "candidate_b_id": row.get("candidate_b_id"),
        "candidate_pair_status_pattern": row.get("candidate_pair_status_pattern"),
        "candidate_a_evidence_status": row.get("candidate_a_evidence_status"),
        "candidate_b_evidence_status": row.get("candidate_b_evidence_status"),
        "candidate_a_support_evidence_count": safe_int(row.get("candidate_a_support_evidence_count"), 0),
        "candidate_b_support_evidence_count": safe_int(row.get("candidate_b_support_evidence_count"), 0),
        "candidate_a_contradiction_evidence_count": safe_int(
            row.get("candidate_a_contradiction_evidence_count"), 0
        ),
        "candidate_b_contradiction_evidence_count": safe_int(
            row.get("candidate_b_contradiction_evidence_count"), 0
        ),
        "support_count_abs_delta": safe_int(row.get("support_count_abs_delta"), 0),
        "contradiction_count_abs_delta": safe_int(row.get("contradiction_count_abs_delta"), 0),
        "viewpoint_coverage_abs_delta": safe_float(row.get("viewpoint_coverage_abs_delta")),
        "association_quality_abs_delta": safe_float(row.get("association_quality_abs_delta")),
        "map_pose_consistency_abs_delta": safe_float(row.get("map_pose_consistency_abs_delta")),
        "pose_graph_connectivity_abs_delta": safe_float(row.get("pose_graph_connectivity_abs_delta")),
        "selected_branch": row.get("selected_branch"),
        "selected_action": row.get("selected_action"),
    }


def materialize_source_rows(source_pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for index, source in enumerate(sorted(source_pair_rows, key=pair_key), start=1):
        key = join_key(source)
        payload = key_payload(key)
        candidate_a = str(source.get("candidate_a_id") or "")
        candidate_b = str(source.get("candidate_b_id") or "")
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "multi_case_source_materialization",
                "row_type": "rival_contradiction_region_contamination_multi_case_source",
                "multi_case_source_id": f"rival_contamination_pair:{index:03d}",
                "join_key": {**payload, "candidate_a_id": candidate_a, "candidate_b_id": candidate_b},
                **payload,
                "candidate_a_id": candidate_a,
                "candidate_b_id": candidate_b,
                "candidate_ordering_source": "action_frozen_pair_rows",
                "candidate_a_and_b_are_not_correctness_roles": True,
                "selected_evidence_family": "rival_contradiction_or_region_contamination_multi_case_source_v1",
                "selected_branch": source.get("selected_branch"),
                "selected_action": source.get("selected_action"),
                "source_resolution_route": source.get("source_resolution_route"),
                "request_evidence_status": source.get("request_evidence_status"),
                "candidate_pair_status_pattern": source.get("candidate_pair_status_pattern"),
                "candidate_a_evidence_status": source.get("candidate_a_evidence_status"),
                "candidate_b_evidence_status": source.get("candidate_b_evidence_status"),
                "candidate_a_support_evidence_count": safe_int(source.get("candidate_a_support_evidence_count"), 0),
                "candidate_b_support_evidence_count": safe_int(source.get("candidate_b_support_evidence_count"), 0),
                "candidate_a_contradiction_evidence_count": safe_int(
                    source.get("candidate_a_contradiction_evidence_count"), 0
                ),
                "candidate_b_contradiction_evidence_count": safe_int(
                    source.get("candidate_b_contradiction_evidence_count"), 0
                ),
                "support_count_abs_delta": safe_int(source.get("support_count_abs_delta"), 0),
                "contradiction_count_abs_delta": safe_int(source.get("contradiction_count_abs_delta"), 0),
                "viewpoint_coverage_abs_delta": safe_float(source.get("viewpoint_coverage_abs_delta")),
                "association_quality_abs_delta": safe_float(source.get("association_quality_abs_delta")),
                "map_pose_consistency_abs_delta": safe_float(source.get("map_pose_consistency_abs_delta")),
                "pose_graph_connectivity_abs_delta": safe_float(source.get("pose_graph_connectivity_abs_delta")),
                "map_pose_uncertainty_abs_delta": safe_float(source.get("map_pose_uncertainty_abs_delta")),
                "requires_candidate_pair_frame_projection": True,
                "requires_detector_sam2_substrate": True,
                "requires_post_detector_evidence": True,
                "evaluation_label_fields_dropped_for_action": True,
                "pair_labels_join_only_after_source_freeze": True,
                "terminal_utility_allowed": False,
                "action_evidence_inputs": action_source_inputs(source),
                **common_flags(),
            }
        )
    return out


def materialize_candidate_role_rows(
    source_rows: Sequence[Mapping[str, Any]],
    candidate_source_by_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in source_rows:
        key = join_key(source)
        payload = key_payload(key)
        candidate_a = str(source.get("candidate_a_id") or "")
        candidate_b = str(source.get("candidate_b_id") or "")
        for role, cid, paired in (
            ("candidate_a", candidate_a, candidate_b),
            ("candidate_b", candidate_b, candidate_a),
        ):
            candidate = candidate_source_by_key.get((*key, cid), {})
            out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "multi_case_source_materialization",
                    "row_type": "rival_contradiction_region_contamination_multi_case_candidate_role",
                    "multi_case_source_id": source.get("multi_case_source_id"),
                    "join_key": {**payload, "candidate_id": cid},
                    **payload,
                    "candidate_id": cid,
                    "candidate_pair_role": role,
                    "paired_candidate_id": paired,
                    "candidate_ordering_source": "action_frozen_pair_rows",
                    "candidate_role_is_not_correctness": True,
                    "candidate_evidence_status": candidate.get("candidate_evidence_status")
                    or source.get(f"{role}_evidence_status"),
                    "candidate_support_evidence_count": safe_int(
                        candidate.get("candidate_support_evidence_count")
                        or source.get(f"{role}_support_evidence_count"),
                        0,
                    ),
                    "candidate_contradiction_evidence_count": safe_int(
                        candidate.get("candidate_contradiction_evidence_count")
                        or source.get(f"{role}_contradiction_evidence_count"),
                        0,
                    ),
                    "viewpoint_coverage_delta": safe_float(candidate.get("viewpoint_coverage_delta")),
                    "association_quality_proxy": safe_float(candidate.get("association_quality_proxy")),
                    "map_pose_consistency_delta": safe_float(candidate.get("map_pose_consistency_delta")),
                    "pose_graph_connectivity_delta": safe_float(candidate.get("pose_graph_connectivity_delta")),
                    "map_pose_consistency_uncertainty_proxy": safe_float(
                        candidate.get("map_pose_consistency_uncertainty_proxy")
                    ),
                    "requires_own_view_seed": True,
                    "requires_cross_candidate_challenge_seed": True,
                    "label_fields_dropped_from_action": True,
                    "action_evidence_inputs": {
                        "candidate_id": cid,
                        "candidate_pair_role": role,
                        "paired_candidate_id": paired,
                        "candidate_evidence_status": candidate.get("candidate_evidence_status")
                        or source.get(f"{role}_evidence_status"),
                        "candidate_support_evidence_count": safe_int(
                            candidate.get("candidate_support_evidence_count")
                            or source.get(f"{role}_support_evidence_count"),
                            0,
                        ),
                        "candidate_contradiction_evidence_count": safe_int(
                            candidate.get("candidate_contradiction_evidence_count")
                            or source.get(f"{role}_contradiction_evidence_count"),
                            0,
                        ),
                        "viewpoint_coverage_delta": safe_float(candidate.get("viewpoint_coverage_delta")),
                        "association_quality_proxy": safe_float(candidate.get("association_quality_proxy")),
                        "map_pose_consistency_delta": safe_float(candidate.get("map_pose_consistency_delta")),
                        "pose_graph_connectivity_delta": safe_float(candidate.get("pose_graph_connectivity_delta")),
                    },
                    **common_flags(),
                }
            )
    return sorted(out, key=candidate_key)


def seed_role_targets(role: str, candidate_a: str, candidate_b: str) -> Tuple[str, str, str]:
    if role == "candidate_a_own_view":
        return candidate_a, candidate_b, "candidate_a"
    if role == "candidate_b_own_view":
        return candidate_b, candidate_a, "candidate_b"
    if role == "shared_region_or_relation_anchor_view":
        return candidate_a, candidate_b, "pair_context"
    if role == "cross_candidate_challenge_view":
        return candidate_a, candidate_b, "pair_challenge"
    return candidate_a, candidate_b, "unknown"


def materialize_observation_seed_rows(
    source_rows: Sequence[Mapping[str, Any]],
    required_roles: Sequence[str],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in source_rows:
        key = join_key(source)
        payload = key_payload(key)
        candidate_a = str(source.get("candidate_a_id") or "")
        candidate_b = str(source.get("candidate_b_id") or "")
        for index, role in enumerate(required_roles, start=1):
            target_candidate_id, context_candidate_id, role_scope = seed_role_targets(role, candidate_a, candidate_b)
            out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "multi_case_source_materialization",
                    "row_type": "rival_contradiction_region_contamination_multi_case_observation_seed",
                    "multi_case_source_id": source.get("multi_case_source_id"),
                    "join_key": {
                        **payload,
                        "candidate_a_id": candidate_a,
                        "candidate_b_id": candidate_b,
                        "observation_role": role,
                    },
                    **payload,
                    "candidate_a_id": candidate_a,
                    "candidate_b_id": candidate_b,
                    "observation_index": index,
                    "observation_role": role,
                    "role_scope": role_scope,
                    "target_candidate_id": target_candidate_id,
                    "context_candidate_id": context_candidate_id,
                    "candidate_ids": [candidate_a, candidate_b],
                    "evidence_axis": ROLE_EVIDENCE_AXIS.get(role, "unknown"),
                    "viewpoint_policy": "multi_case_pairwise_rival_region_contamination_probe_v1",
                    "frame_projection_contract_required_next": True,
                    "detector_substrate_required_after_projection": True,
                    "candidate_ordering_source": "action_frozen_pair_rows",
                    "label_fields_dropped_from_action": True,
                    "action_plan_inputs": {
                        "candidate_a_id": candidate_a,
                        "candidate_b_id": candidate_b,
                        "target_candidate_id": target_candidate_id,
                        "context_candidate_id": context_candidate_id,
                        "observation_role": role,
                        "role_scope": role_scope,
                        "viewpoint_policy": "multi_case_pairwise_rival_region_contamination_probe_v1",
                    },
                    **common_flags(),
                }
            )
    return out


def materialize_audit_rows(all_pair_rows: Sequence[Mapping[str, Any]], source_pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    selected_keys = {pair_key(row) for row in source_pair_rows}
    out: List[Dict[str, Any]] = []
    for source in sorted(all_pair_rows, key=pair_key):
        if pair_key(source) in selected_keys:
            continue
        key = join_key(source)
        payload = key_payload(key)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "multi_case_source_materialization",
                "row_type": "rival_contradiction_region_contamination_multi_case_audit",
                "join_key": {
                    **payload,
                    "candidate_a_id": source.get("candidate_a_id"),
                    "candidate_b_id": source.get("candidate_b_id"),
                },
                **payload,
                "candidate_a_id": source.get("candidate_a_id"),
                "candidate_b_id": source.get("candidate_b_id"),
                "selected_branch": source.get("selected_branch"),
                "selected_action": source.get("selected_action"),
                "source_resolution_route": source.get("source_resolution_route"),
                "candidate_pair_status_pattern": source.get("candidate_pair_status_pattern"),
                "audit_reason": "not_selected_by_multi_case_pairwise_conflict_filter",
                "terminal_utility_allowed": False,
                "action_route_inputs": {
                    "selected_branch": source.get("selected_branch"),
                    "selected_action": source.get("selected_action"),
                    "source_resolution_route": source.get("source_resolution_route"),
                    "candidate_pair_status_pattern": source.get("candidate_pair_status_pattern"),
                },
                **common_flags(),
            }
        )
    return out


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row.get("action_evidence_inputs", {}))
        scan(row.get("action_plan_inputs", {}))
        scan(row.get("action_route_inputs", {}))
    return sorted(found)


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


def evaluation_counts(eval_rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "evaluation_join_pair_rows": len(eval_rows),
        "evaluation_only_pair_label_pattern_counts": compact_counter(
            row.get("candidate_pair_label_pattern_for_evaluation_only") for row in eval_rows
        ),
        "evaluation_only_wrong_goal_candidate_pair_rows": sum(
            1
            for row in eval_rows
            if row.get("candidate_a_wrong_label_for_evaluation_only") is True
            or row.get("candidate_b_wrong_label_for_evaluation_only") is True
        ),
        "evaluation_only_correct_wrong_pair_rows": sum(
            1
            for row in eval_rows
            if (
                row.get("candidate_a_correctness_label_for_evaluation_only") is True
                and row.get("candidate_b_wrong_label_for_evaluation_only") is True
            )
            or (
                row.get("candidate_a_wrong_label_for_evaluation_only") is True
                and row.get("candidate_b_correctness_label_for_evaluation_only") is True
            )
        ),
        "pair_label_action_forbidden_rows": sum(
            1 for row in eval_rows if row.get("pair_label_is_action_forbidden") is True
        ),
        "terminal_selector_allowed_from_pair_label_rows": sum(
            1 for row in eval_rows if row.get("terminal_selector_allowed_from_pair_label") is True
        ),
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    all_pair_rows: Sequence[Mapping[str, Any]],
    source_rows: Sequence[Mapping[str, Any]],
    candidate_role_rows: Sequence[Mapping[str, Any]],
    observation_seed_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
    eval_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    frozen_filter = contract.get("frozen_source_filter") or {}
    source_gate = contract.get("source_gate") or {}
    all_action_rows = [*source_rows, *candidate_role_rows, *observation_seed_rows, *audit_rows]
    scenes = sorted({str(row.get("scene_key")) for row in source_rows})
    queries = sorted({str(row.get("query")) for row in source_rows})
    role_policy = ((contract.get("scaling_contract") or {}).get("role_policy") or {})
    required_roles = list(role_policy.get("default_pair_roles") or [])
    eval_count_payload = evaluation_counts(eval_rows)
    gate = {
        "source_rows_expected_passed": len(source_rows) == safe_int(frozen_filter.get("required_pair_rows"), -1),
        "minimum_scene_count_passed": len(scenes) >= safe_int(frozen_filter.get("minimum_scene_count"), -1),
        "minimum_query_count_passed": len(queries) >= safe_int(frozen_filter.get("minimum_query_count"), -1),
        "candidate_role_rows_expected_passed": len(candidate_role_rows) == len(source_rows) * 2,
        "observation_seed_rows_expected_passed": len(observation_seed_rows)
        == len(source_rows) * len(required_roles),
        "audit_rows_expected_passed": len(audit_rows)
        == safe_int(source_gate.get("multi_case_missing_followup_rows"), len(audit_rows)),
        "evaluation_join_pair_rows_expected_passed": eval_count_payload["evaluation_join_pair_rows"]
        == len(source_rows),
        "pair_label_action_forbidden_passed": eval_count_payload["pair_label_action_forbidden_rows"]
        == len(eval_rows),
        "terminal_selector_from_pair_label_blocked_passed": eval_count_payload[
            "terminal_selector_allowed_from_pair_label_rows"
        ]
        == 0,
        "action_evidence_forbidden_key_count_passed": len(forbidden_keys) == 0,
        "terminal_commit_rows_passed": count_true(all_action_rows, "terminal_commit") == 0,
        "candidate_commit_rows_passed": count_true(all_action_rows, "candidate_commit") == 0,
        "candidate_rejection_rows_passed": count_true(all_action_rows, "candidate_rejection") == 0,
        "uses_gt_for_action_true_rows_passed": count_true(all_action_rows, "uses_gt_for_action") == 0,
        "paper_claim_allowed_true_rows_passed": count_true(all_action_rows, "paper_claim_allowed") == 0,
    }
    materializer_gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-12",
        "status": "multi_case_source_materializer_gate_passed_terminal_blocked"
        if materializer_gate_passed
        else "multi_case_source_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_pair_rows_total": len(all_pair_rows),
        "source_rows": len(source_rows),
        "candidate_role_rows": len(candidate_role_rows),
        "observation_plan_seed_rows": len(observation_seed_rows),
        "audit_rows": len(audit_rows),
        "scene_count": len(scenes),
        "query_count": len(queries),
        "scene_keys": scenes,
        "queries": queries,
        "pair_status_pattern_counts": compact_counter(row.get("candidate_pair_status_pattern") for row in source_rows),
        "selected_branch_counts": compact_counter(row.get("selected_branch") for row in source_rows),
        "candidate_role_counts": compact_counter(row.get("candidate_pair_role") for row in candidate_role_rows),
        "observation_role_counts": compact_counter(row.get("observation_role") for row in observation_seed_rows),
        "audit_selected_branch_counts": compact_counter(row.get("selected_branch") for row in audit_rows),
        **eval_count_payload,
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
        "implementation_gate": gate,
        "materializer_gate_passed": materializer_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "terminal_utility_validation_allowed": False,
        "terminal_utility_contract_allowed_now": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "multi_case_frame_projection_contract_required"
        if materializer_gate_passed
        else "multi_case_source_materializer_gate_failed",
        "next_task": "freeze_multi_case_rival_contradiction_region_contamination_frame_projection_contract"
        if materializer_gate_passed
        else "debug_multi_case_source_materializer",
        "interpretation": {
            "fact": (
                "The materializer preserves the frozen 18-row pairwise conflict source and writes source, "
                "candidate-role, observation seed, audit, and summary rows without GT action fields."
            ),
            "agent_inference": (
                "This is the correct next step after the bounded single-case promotion gate: it expands the "
                "same failure mechanism across scenes and queries before any terminal utility is defined."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM utility, terminal utility, first_eval rerun, "
                "policy-scale comparison, formula revision, Step 4-5 promotion, or paper claim is allowed."
            ),
        },
    }


def verification_path(contract_path: Path) -> Path:
    return contract_path.with_name(f"{contract_path.stem}.verify.json")


def build_verify_payload(
    *,
    contract_path: Path,
    out_root: Path,
    summary: Mapping[str, Any],
) -> Dict[str, Any]:
    script_path = (
        "hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/"
        "materialize_rival_contradiction_region_contamination_multi_case_source.py"
    )
    return {
        "schema_version": "h001.verify.rival_contradiction_region_contamination_multi_case_source.v1",
        "checked_at": "2026-06-12",
        "ok": summary.get("materializer_gate_passed") is True,
        "status": "docker_verified_multi_case_source_materializer_gate_passed_terminal_blocked"
        if summary.get("materializer_gate_passed") is True
        else "docker_verified_multi_case_source_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_files": {name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()},
        "verified_output_counts": {
            "source_rows": summary.get("source_rows"),
            "candidate_role_rows": summary.get("candidate_role_rows"),
            "observation_plan_seed_rows": summary.get("observation_plan_seed_rows"),
            "audit_rows": summary.get("audit_rows"),
            "scene_count": summary.get("scene_count"),
            "query_count": summary.get("query_count"),
            "evaluation_join_pair_rows": summary.get("evaluation_join_pair_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "pair_status_pattern_counts": summary.get("pair_status_pattern_counts"),
        "evaluation_only_pair_label_pattern_counts": summary.get("evaluation_only_pair_label_pattern_counts"),
        "observation_role_counts": summary.get("observation_role_counts"),
        "implementation_gate": summary.get("implementation_gate"),
        "materializer_gate_passed": summary.get("materializer_gate_passed"),
        "primary_blocker": summary.get("primary_blocker"),
        "next_task": summary.get("next_task"),
        "docker_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e HOME=/tmp "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                f"python -B -m py_compile {script_path}"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e HOME=/tmp "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -B -m h001_runtime.materialize_rival_contradiction_region_contamination_multi_case_source"
            ),
        ],
        "verification_commands": [
            f"jq empty {contract_path}",
            f"jq empty {verification_path(contract_path)}",
            (
                "jq '{status, source_rows, candidate_role_rows, observation_plan_seed_rows, "
                "audit_rows, scene_count, query_count, materializer_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "source_rows_preserved_before_label_join": True,
            "candidate_ordering_source_action_frozen": True,
            "candidate_roles_do_not_encode_correctness": True,
            "pair_labels_action_forbidden": True,
            "wrong_goal_and_wasted_path_action_forbidden": True,
            "terminal_utility_validation_allowed": False,
            "terminal_selector_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "formula_revision_allowed": False,
            "first_eval_rerun_allowed": False,
            "policy_scale_comparison_allowed": False,
            "step_4_5_promotion_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": summary.get("interpretation"),
        "paper_claim_allowed": False,
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(resolve_path(contract_path))
    source = contract.get("source") or {}
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")
    frozen_filter = contract.get("frozen_source_filter") or {}
    if not isinstance(frozen_filter, Mapping):
        raise ValueError("Contract frozen_source_filter section is missing.")

    action_pair_rows = load_jsonl(resolve_path(source["action_source_pair_rows"]))
    action_candidate_rows = load_jsonl(resolve_path(source["action_source_candidate_rows"]))
    eval_pair_rows = load_jsonl(resolve_path(source["evaluation_join_pair_rows"]))
    source_pair_rows = [row for row in action_pair_rows if row_matches_filter(row, frozen_filter)]
    source_pair_keys = {pair_key(row) for row in source_pair_rows}
    selected_eval_rows = [row for row in eval_pair_rows if pair_key(row) in source_pair_keys]
    candidate_source_by_key = {candidate_key(row): row for row in action_candidate_rows}

    source_rows = materialize_source_rows(source_pair_rows)
    candidate_role_rows = materialize_candidate_role_rows(source_rows, candidate_source_by_key)
    role_policy = ((contract.get("scaling_contract") or {}).get("role_policy") or {})
    required_roles = list(role_policy.get("default_pair_roles") or [])
    observation_seed_rows = materialize_observation_seed_rows(source_rows, required_roles)
    audit_rows = materialize_audit_rows(action_pair_rows, source_pair_rows)
    forbidden_keys = scan_forbidden_action_inputs([*source_rows, *candidate_role_rows, *observation_seed_rows, *audit_rows])
    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        all_pair_rows=action_pair_rows,
        source_rows=source_rows,
        candidate_role_rows=candidate_role_rows,
        observation_seed_rows=observation_seed_rows,
        audit_rows=audit_rows,
        eval_rows=selected_eval_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["source_rows"], source_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_role_rows"], candidate_role_rows)
    write_jsonl(out_root / OUTPUT_FILES["observation_plan_seed_rows"], observation_seed_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(verification_path(contract_path), build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary))

    if summary.get("materializer_gate_passed") is not True:
        raise SystemExit("multi-case source materializer gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize multi-case source rows for rival contradiction / region contamination evidence."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(
        json.dumps(
            {
                "status": summary.get("status"),
                "source_rows": summary.get("source_rows"),
                "candidate_role_rows": summary.get("candidate_role_rows"),
                "observation_plan_seed_rows": summary.get("observation_plan_seed_rows"),
                "audit_rows": summary.get("audit_rows"),
                "scene_count": summary.get("scene_count"),
                "query_count": summary.get("query_count"),
                "materializer_gate_passed": summary.get("materializer_gate_passed"),
                "primary_blocker": summary.get("primary_blocker"),
                "next_task": summary.get("next_task"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
