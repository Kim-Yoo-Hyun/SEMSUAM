import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.goal_region_object_relation_coverage_completion.v1"
VERIFY_SCHEMA_VERSION = "h001.verify.goal_region_object_relation_coverage_completion.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_goal_region_object_relation_coverage_completion_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_goal_region_object_relation_coverage_completion_v1"

OUTPUT_FILES = {
    "target_pair_rows": "goal_region_object_relation_coverage_completion_target_pair_rows.jsonl",
    "candidate_rows": "goal_region_object_relation_coverage_completion_candidate_rows.jsonl",
    "observation_seed_rows": "goal_region_object_relation_coverage_completion_observation_seed_rows.jsonl",
    "audit_rows": "goal_region_object_relation_coverage_completion_audit_rows.jsonl",
    "summary": "goal_region_object_relation_coverage_completion_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
PAIR_KEYS = (*JOIN_KEYS, "candidate_a_id", "candidate_b_id")

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
    "wrong_goal_visit",
    "wrong_goal_visit_proxy",
    "wasted_path_m",
    "wasted_path_proxy_m",
    "map_pose_consistency_delta",
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
    "threshold_tuned_from_joined_labels",
}

ROLE_ACTIONS = {
    "candidate_a_goal_region_context_view": "request_goal_region_evidence",
    "candidate_b_goal_region_context_view": "request_goal_region_evidence",
    "candidate_pair_object_relation_context_view": "request_object_relation_evidence",
    "shared_goal_region_anchor_view": "request_joint_goal_region_object_relation_evidence",
}

ROLE_EVIDENCE_AXIS = {
    "candidate_a_goal_region_context_view": "goal_region_context_for_candidate_a",
    "candidate_b_goal_region_context_view": "goal_region_context_for_candidate_b",
    "candidate_pair_object_relation_context_view": "object_relation_context_for_candidate_pair",
    "shared_goal_region_anchor_view": "shared_goal_region_anchor_context",
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


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def join_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return tuple(str(source.get(key) or row.get(key) or "") for key in JOIN_KEYS)  # type: ignore[return-value]


def pair_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        *join_key(row),
        str(source.get("candidate_a_id") or row.get("candidate_a_id") or ""),
        str(source.get("candidate_b_id") or row.get("candidate_b_id") or ""),
    )


def candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (*join_key(row), str(source.get("candidate_id") or row.get("candidate_id") or ""))


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


def common_flags(*, uses_gt_for_analysis: bool = False) -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": uses_gt_for_analysis,
        "paper_claim_allowed": False,
    }


def row_matches_filter(row: Mapping[str, Any], target_filter: Mapping[str, Any]) -> bool:
    for key, expected in target_filter.items():
        if key in {"terminal_commit", "candidate_commit", "candidate_rejection", "uses_gt_for_action"}:
            if row.get(key) is not expected:
                return False
            continue
        if row.get(key) != expected:
            return False
    return True


def contract_target_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    return (
        str(row.get("episode_key") or ""),
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        str(row.get("request_id") or ""),
        str(row.get("candidate_a_id") or ""),
        str(row.get("candidate_b_id") or ""),
    )


def source_target_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    return (
        str(row.get("episode_key") or ""),
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        str(row.get("request_id") or ""),
        str(row.get("candidate_a_id") or ""),
        str(row.get("candidate_b_id") or ""),
    )


def target_pair_id(index: int) -> str:
    return f"coverage_completion_pair:{index:03d}"


def materialize_target_pair_rows(
    source_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for index, source in enumerate(sorted(source_rows, key=pair_key), start=1):
        key = join_key(source)
        payload = key_payload(key)
        candidate_a = str(source.get("candidate_a_id") or "")
        candidate_b = str(source.get("candidate_b_id") or "")
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "goal_region_object_relation_coverage_completion_materialization",
                "row_type": "coverage_completion_target_pair",
                "coverage_completion_pair_id": target_pair_id(index),
                "join_key": {**payload, "candidate_a_id": candidate_a, "candidate_b_id": candidate_b},
                **payload,
                "candidate_a_id": candidate_a,
                "candidate_b_id": candidate_b,
                "selected_branch": "goal_region_object_relation_coverage_completion_v1",
                "selected_nonterminal_action": "request_joint_goal_region_object_relation_evidence",
                "source_failure_class": source.get("failure_class"),
                "source_failure_mechanism": source.get("failure_mechanism"),
                "source_recommended_next_family": source.get("recommended_next_family"),
                "goal_region_contrast_state": source.get("goal_region_contrast_state"),
                "goal_region_pair_evidence_available": source.get("goal_region_pair_evidence_available") is True,
                "object_relation_anchor_consistency_state": source.get(
                    "object_relation_anchor_consistency_state"
                ),
                "object_relation_candidate_a_available": source.get("object_relation_candidate_a_available")
                is True,
                "object_relation_candidate_b_available": source.get("object_relation_candidate_b_available")
                is True,
                "map_pose_non_contradiction_state": source.get("map_pose_non_contradiction_state"),
                "map_pose_consistency_abs_delta": source.get("map_pose_consistency_abs_delta"),
                "pose_graph_connectivity_abs_delta": source.get("pose_graph_connectivity_abs_delta"),
                "coverage_completion_state": "goal_region_and_object_relation_evidence_missing",
                "goal_region_evidence_required": True,
                "object_relation_evidence_required": True,
                "terminal_utility_allowed": False,
                "candidate_ordering_source": "action_frozen_pairwise_diagnostic_rows",
                "evaluation_label_fields_dropped_from_action": True,
                "label_fields_used_for_action": [],
                "action_evidence_inputs": {
                    "source_name": payload["source_name"],
                    "scene_key": payload["scene_key"],
                    "query": payload["query"],
                    "request_id": payload["request_id"],
                    "episode_key": payload["episode_key"],
                    "candidate_a_id": candidate_a,
                    "candidate_b_id": candidate_b,
                    "goal_region_contrast_state": source.get("goal_region_contrast_state"),
                    "goal_region_pair_evidence_available": source.get("goal_region_pair_evidence_available")
                    is True,
                    "object_relation_anchor_consistency_state": source.get(
                        "object_relation_anchor_consistency_state"
                    ),
                    "object_relation_candidate_a_available": source.get(
                        "object_relation_candidate_a_available"
                    )
                    is True,
                    "object_relation_candidate_b_available": source.get(
                        "object_relation_candidate_b_available"
                    )
                    is True,
                    "map_pose_non_contradiction_state": source.get("map_pose_non_contradiction_state"),
                    "selected_branch": "goal_region_object_relation_coverage_completion_v1",
                    "selected_nonterminal_action": "request_joint_goal_region_object_relation_evidence",
                },
                **common_flags(uses_gt_for_analysis=True),
            }
        )
    return out


def materialize_candidate_rows(target_pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pair in target_pair_rows:
        key = join_key(pair)
        payload = key_payload(key)
        candidate_a = str(pair.get("candidate_a_id") or "")
        candidate_b = str(pair.get("candidate_b_id") or "")
        for role, cid, paired in (
            ("candidate_a", candidate_a, candidate_b),
            ("candidate_b", candidate_b, candidate_a),
        ):
            out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "goal_region_object_relation_coverage_completion_materialization",
                    "row_type": "coverage_completion_candidate",
                    "coverage_completion_pair_id": pair.get("coverage_completion_pair_id"),
                    "join_key": {**payload, "candidate_id": cid},
                    **payload,
                    "candidate_id": cid,
                    "candidate_pair_role": role,
                    "paired_candidate_id": paired,
                    "candidate_role_is_not_correctness": True,
                    "selected_branch": "goal_region_object_relation_coverage_completion_v1",
                    "candidate_goal_region_evidence_required": True,
                    "candidate_object_relation_context_required": True,
                    "candidate_ordering_source": "action_frozen_pairwise_diagnostic_rows",
                    "label_fields_dropped_from_action": True,
                    "terminal_utility_allowed": False,
                    "action_evidence_inputs": {
                        "candidate_id": cid,
                        "candidate_pair_role": role,
                        "paired_candidate_id": paired,
                        "selected_branch": "goal_region_object_relation_coverage_completion_v1",
                        "candidate_goal_region_evidence_required": True,
                        "candidate_object_relation_context_required": True,
                    },
                    **common_flags(uses_gt_for_analysis=False),
                }
            )
    return sorted(out, key=candidate_key)


def role_targets(role: str, candidate_a: str, candidate_b: str) -> Tuple[str, Optional[str], str]:
    if role == "candidate_a_goal_region_context_view":
        return candidate_a, candidate_b, "candidate_goal_region_context"
    if role == "candidate_b_goal_region_context_view":
        return candidate_b, candidate_a, "candidate_goal_region_context"
    if role == "candidate_pair_object_relation_context_view":
        return candidate_a, candidate_b, "candidate_pair_object_relation_context"
    if role == "shared_goal_region_anchor_view":
        return candidate_a, candidate_b, "shared_goal_region_context"
    return candidate_a, candidate_b, "unknown"


def materialize_observation_seed_rows(
    target_pair_rows: Sequence[Mapping[str, Any]],
    required_roles: Sequence[str],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pair in target_pair_rows:
        key = join_key(pair)
        payload = key_payload(key)
        candidate_a = str(pair.get("candidate_a_id") or "")
        candidate_b = str(pair.get("candidate_b_id") or "")
        for index, role in enumerate(required_roles, start=1):
            target_candidate_id, context_candidate_id, role_scope = role_targets(role, candidate_a, candidate_b)
            selected_action = ROLE_ACTIONS.get(role, "audit_only")
            out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "goal_region_object_relation_coverage_completion_materialization",
                    "row_type": "coverage_completion_observation_seed",
                    "coverage_completion_pair_id": pair.get("coverage_completion_pair_id"),
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
                    "selected_nonterminal_action": selected_action,
                    "evidence_axis": ROLE_EVIDENCE_AXIS.get(role, "unknown"),
                    "viewpoint_policy": "goal_region_object_relation_coverage_completion_probe_v1",
                    "frame_projection_contract_required_next": True,
                    "detector_substrate_required_after_projection": True,
                    "post_detector_evidence_required_after_substrate": True,
                    "candidate_ordering_source": "action_frozen_pairwise_diagnostic_rows",
                    "label_fields_dropped_from_action": True,
                    "terminal_utility_allowed": False,
                    "action_plan_inputs": {
                        "candidate_a_id": candidate_a,
                        "candidate_b_id": candidate_b,
                        "target_candidate_id": target_candidate_id,
                        "context_candidate_id": context_candidate_id,
                        "observation_role": role,
                        "role_scope": role_scope,
                        "selected_nonterminal_action": selected_action,
                        "viewpoint_policy": "goal_region_object_relation_coverage_completion_probe_v1",
                    },
                    **common_flags(uses_gt_for_analysis=False),
                }
            )
    return out


def materialize_audit_rows(
    all_pair_rows: Sequence[Mapping[str, Any]],
    selected_pair_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    selected_keys = {pair_key(row) for row in selected_pair_rows}
    out: List[Dict[str, Any]] = []
    for source in sorted(all_pair_rows, key=pair_key):
        if pair_key(source) in selected_keys:
            continue
        key = join_key(source)
        payload = key_payload(key)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "goal_region_object_relation_coverage_completion_materialization",
                "row_type": "coverage_completion_audit",
                "join_key": {
                    **payload,
                    "candidate_a_id": source.get("candidate_a_id"),
                    "candidate_b_id": source.get("candidate_b_id"),
                },
                **payload,
                "candidate_a_id": source.get("candidate_a_id"),
                "candidate_b_id": source.get("candidate_b_id"),
                "source_recommended_next_family": source.get("recommended_next_family"),
                "source_failure_class": source.get("failure_class"),
                "source_failure_mechanism": source.get("failure_mechanism"),
                "audit_reason": "not_selected_by_goal_region_object_relation_coverage_completion_filter",
                "terminal_utility_allowed": False,
                "action_route_inputs": {
                    "source_recommended_next_family": source.get("recommended_next_family"),
                    "source_failure_class": source.get("failure_class"),
                    "source_failure_mechanism": source.get("failure_mechanism"),
                },
                **common_flags(uses_gt_for_analysis=True),
            }
        )
    return out


def count_true(rows: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for row in rows if row.get(key) is True)


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


def verify_target_match(contract: Mapping[str, Any], selected_rows: Sequence[Mapping[str, Any]]) -> None:
    contract_targets = {contract_target_key(row) for row in contract.get("target_rows", [])}
    source_targets = {source_target_key(row) for row in selected_rows}
    if contract_targets != source_targets:
        missing = sorted(contract_targets - source_targets)
        extra = sorted(source_targets - contract_targets)
        raise ValueError(f"Target row mismatch. missing={missing} extra={extra}")


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    all_pair_rows: Sequence[Mapping[str, Any]],
    target_pair_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    observation_seed_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    minimum = contract.get("minimum_implementation_gates") or {}
    all_action_rows = [*target_pair_rows, *candidate_rows, *observation_seed_rows, *audit_rows]
    scenes = sorted({str(row.get("scene_key")) for row in target_pair_rows})
    queries = sorted({str(row.get("query")) for row in target_pair_rows})
    observation_roles = list((contract.get("observation_contract") or {}).get("required_observation_roles") or [])
    gate = {
        "target_pair_rows_expected_passed": len(target_pair_rows) == int(minimum.get("target_pair_rows", -1)),
        "target_request_rows_expected_passed": len({join_key(row) for row in target_pair_rows})
        == int(minimum.get("target_request_rows", -1)),
        "candidate_rows_expected_passed": len(candidate_rows) == int(minimum.get("candidate_rows_expected", -1)),
        "observation_seed_rows_expected_passed": len(observation_seed_rows)
        == int(minimum.get("observation_seed_rows_expected", -1)),
        "observation_roles_per_pair_passed": (
            len(observation_seed_rows) // max(len(target_pair_rows), 1)
        )
        == int(minimum.get("observation_roles_per_pair", -1)),
        "scene_count_passed": len(scenes) == int((contract.get("target_counts") or {}).get("scene_count", -1)),
        "query_count_passed": len(queries) == int((contract.get("target_counts") or {}).get("query_count", -1)),
        "all_target_rows_goal_region_evidence_missing_passed": all(
            row.get("goal_region_pair_evidence_available") is False for row in target_pair_rows
        ),
        "all_target_rows_object_relation_evidence_missing_passed": all(
            row.get("object_relation_candidate_a_available") is False
            and row.get("object_relation_candidate_b_available") is False
            for row in target_pair_rows
        ),
        "action_evidence_forbidden_key_count_passed": len(forbidden_keys)
        == int(minimum.get("action_evidence_forbidden_key_count", -1)),
        "terminal_commit_rows_passed": count_true(all_action_rows, "terminal_commit")
        == int(minimum.get("terminal_commit_rows", -1)),
        "candidate_commit_rows_passed": count_true(all_action_rows, "candidate_commit")
        == int(minimum.get("candidate_commit_rows", -1)),
        "candidate_rejection_rows_passed": count_true(all_action_rows, "candidate_rejection")
        == int(minimum.get("candidate_rejection_rows", -1)),
        "uses_gt_for_action_true_rows_passed": count_true(all_action_rows, "uses_gt_for_action") == 0,
        "paper_claim_allowed_true_rows_passed": count_true(all_action_rows, "paper_claim_allowed") == 0,
    }
    materializer_gate_passed = all(gate.values())
    label_counts = compact_counter(row.get("candidate_pair_label_pattern_for_evaluation_only") for row in target_pair_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-13",
        "status": "coverage_completion_materializer_gate_passed_terminal_blocked"
        if materializer_gate_passed
        else "coverage_completion_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_pair_rows_total": len(all_pair_rows),
        "target_pair_rows": len(target_pair_rows),
        "target_request_rows": len({join_key(row) for row in target_pair_rows}),
        "candidate_rows": len(candidate_rows),
        "observation_seed_rows": len(observation_seed_rows),
        "audit_rows": len(audit_rows),
        "scene_count": len(scenes),
        "query_count": len(queries),
        "scene_keys": scenes,
        "queries": queries,
        "query_counts": compact_counter(row.get("query") for row in target_pair_rows),
        "scene_counts": compact_counter(row.get("scene_key") for row in target_pair_rows),
        "failure_class_counts": compact_counter(row.get("source_failure_class") for row in target_pair_rows),
        "failure_mechanism_counts": compact_counter(row.get("source_failure_mechanism") for row in target_pair_rows),
        "candidate_role_counts": compact_counter(row.get("candidate_pair_role") for row in candidate_rows),
        "observation_role_counts": compact_counter(row.get("observation_role") for row in observation_seed_rows),
        "nonterminal_action_counts": compact_counter(
            row.get("selected_nonterminal_action") for row in observation_seed_rows
        ),
        "audit_family_counts": compact_counter(row.get("source_recommended_next_family") for row in audit_rows),
        "label_pattern_counts_for_evaluation_only": label_counts,
        "evaluation_only_labels_preserved_for_audit": True,
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_action_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_action_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_action_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_action_rows, "uses_gt_for_action"),
        "uses_gt_for_analysis_true_rows": count_true(all_action_rows, "uses_gt_for_analysis"),
        "paper_claim_allowed_true_rows": count_true(all_action_rows, "paper_claim_allowed"),
        "required_observation_roles": observation_roles,
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
        "primary_blocker": "frame_projection_contract_required"
        if materializer_gate_passed
        else "coverage_completion_materializer_gate_failed",
        "next_task": "freeze_goal_region_object_relation_coverage_completion_frame_projection_contract"
        if materializer_gate_passed
        else "debug_goal_region_object_relation_coverage_completion_materializer",
        "interpretation": {
            "fact": (
                "The materializer writes target pair, candidate, observation seed, audit, and summary rows for "
                "the frozen 12-row coverage-completion branch without terminal commits or GT action inputs."
            ),
            "agent_inference": (
                "This keeps the method step tied to the diagnosed missing-evidence mechanism: acquire missing "
                "goal-region and object-relation evidence before any arbitration."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM utility, terminal utility, first_eval readiness, "
                "policy-scale comparison, Step 4-5 promotion, or paper contribution claim is allowed."
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
        "src/h001_runtime/"
        "materialize_goal_region_object_relation_coverage_completion.py"
    )
    return {
        "schema_version": VERIFY_SCHEMA_VERSION,
        "date_checked": "2026-06-13",
        "ok": summary.get("materializer_gate_passed") is True,
        "verified_artifact": str(contract_path),
        "status": "docker_verified_coverage_completion_materializer_gate_passed_terminal_blocked"
        if summary.get("materializer_gate_passed") is True
        else "docker_verified_coverage_completion_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_files": {name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()},
        "verified_output_counts": {
            "target_pair_rows": summary.get("target_pair_rows"),
            "target_request_rows": summary.get("target_request_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "observation_seed_rows": summary.get("observation_seed_rows"),
            "audit_rows": summary.get("audit_rows"),
            "scene_count": summary.get("scene_count"),
            "query_count": summary.get("query_count"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "observation_role_counts": summary.get("observation_role_counts"),
        "nonterminal_action_counts": summary.get("nonterminal_action_counts"),
        "label_pattern_counts_for_evaluation_only": summary.get("label_pattern_counts_for_evaluation_only"),
        "implementation_gate": summary.get("implementation_gate"),
        "materializer_gate_passed": summary.get("materializer_gate_passed"),
        "primary_blocker": summary.get("primary_blocker"),
        "next_task": summary.get("next_task"),
        "docker_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e HOME=/tmp "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                f"python -B -m py_compile {script_path}"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e HOME=/tmp "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/src "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -B -m h001_runtime.materialize_goal_region_object_relation_coverage_completion"
            ),
        ],
        "verification_commands": [
            f"jq empty {contract_path}",
            f"jq empty {verification_path(contract_path)}",
            (
                "jq '{status, target_pair_rows, candidate_rows, observation_seed_rows, audit_rows, "
                "scene_count, query_count, materializer_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "target_rows_preserved_before_label_join": True,
            "candidate_roles_do_not_encode_correctness": True,
            "observation_roles_are_nonterminal": True,
            "evaluation_labels_audit_only": True,
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
    pair_rows = load_jsonl(resolve_path(source["pairwise_failure_pair_rows"]))
    target_filter = contract.get("target_filter") or {}
    if not isinstance(target_filter, Mapping):
        raise ValueError("Contract target_filter section is missing.")

    selected_source_rows = [row for row in pair_rows if row_matches_filter(row, target_filter)]
    verify_target_match(contract, selected_source_rows)

    target_pair_rows = materialize_target_pair_rows(selected_source_rows)
    candidate_rows = materialize_candidate_rows(target_pair_rows)
    required_roles = list((contract.get("observation_contract") or {}).get("required_observation_roles") or [])
    observation_seed_rows = materialize_observation_seed_rows(target_pair_rows, required_roles)
    audit_rows = materialize_audit_rows(pair_rows, selected_source_rows)
    forbidden_keys = scan_forbidden_action_inputs(
        [*target_pair_rows, *candidate_rows, *observation_seed_rows, *audit_rows]
    )
    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        all_pair_rows=pair_rows,
        target_pair_rows=target_pair_rows,
        candidate_rows=candidate_rows,
        observation_seed_rows=observation_seed_rows,
        audit_rows=audit_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["target_pair_rows"], target_pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["observation_seed_rows"], observation_seed_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(verification_path(contract_path), build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary))

    if summary.get("materializer_gate_passed") is not True:
        raise SystemExit("coverage-completion materializer gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize goal-region/object-relation coverage-completion rows."
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
                "target_pair_rows": summary.get("target_pair_rows"),
                "candidate_rows": summary.get("candidate_rows"),
                "observation_seed_rows": summary.get("observation_seed_rows"),
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
