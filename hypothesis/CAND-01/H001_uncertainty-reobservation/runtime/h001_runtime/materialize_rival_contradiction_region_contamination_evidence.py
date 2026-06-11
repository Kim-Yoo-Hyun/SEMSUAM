import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_rival_contradiction_region_contamination_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_rival_contradiction_region_contamination_evidence_v1"

OUTPUT_FILES = {
    "request_rows": "rival_contradiction_region_contamination_request_rows.jsonl",
    "pair_rows": "rival_contradiction_region_contamination_pair_rows.jsonl",
    "candidate_rows": "rival_contradiction_region_contamination_candidate_rows.jsonl",
    "observation_plan_rows": "rival_contradiction_region_contamination_observation_plan_rows.jsonl",
    "audit_rows": "rival_contradiction_region_contamination_audit_rows.jsonl",
    "failure_rows": "rival_contradiction_region_contamination_failure_rows.jsonl",
    "summary": "rival_contradiction_region_contamination_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")
PROVISIONAL_STATES = {
    "candidate_a_provisionally_supported_by_non_gt_pairwise_rule",
    "candidate_b_provisionally_supported_by_non_gt_pairwise_rule",
}

FORBIDDEN_ACTION_KEYS = {
    "candidate_a_correctness_label_for_evaluation_only",
    "candidate_b_correctness_label_for_evaluation_only",
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_pair_label_pattern_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "candidate_a_wrong_label_for_evaluation_only",
    "candidate_b_wrong_label_for_evaluation_only",
    "provisional_rule_candidate_correct_for_evaluation_only",
    "provisional_rule_candidate_wrong_for_evaluation_only",
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
    "query_specific_threshold_selected_after_evaluation_join",
}

OBSERVATION_ROLES = (
    "supported_candidate_own_view",
    "rival_candidate_own_view",
    "shared_region_or_relation_anchor_view",
    "cross_candidate_challenge_view",
)

ROLE_EVIDENCE_AXIS = {
    "supported_candidate_own_view": "supported_candidate_own_region_evidence",
    "rival_candidate_own_view": "rival_candidate_own_region_evidence",
    "shared_region_or_relation_anchor_view": "region_context_overlap_or_contamination",
    "cross_candidate_challenge_view": "relation_anchor_contradiction_or_leakage",
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


def group_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[join_key(row)].append(row)
    return dict(grouped)


def index_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def target_role_from_pair(row: Mapping[str, Any]) -> str:
    state = str(row.get("non_gt_pairwise_rule_state") or "")
    goal_state = str(row.get("goal_region_contrast_state") or "")
    relation_state = str(row.get("object_relation_anchor_consistency_state") or "")
    map_pose_state = str(row.get("map_pose_non_contradiction_state") or "")
    if (
        state in PROVISIONAL_STATES
        and row.get("rule_input_complete") is True
        and goal_state in {
            "candidate_a_contrastive_goal_region_support",
            "candidate_b_contrastive_goal_region_support",
        }
        and relation_state in {"candidate_a_anchor_consistent", "candidate_b_anchor_consistent"}
        and map_pose_state == "map_pose_non_contradictory_but_non_discriminative"
        and row.get("terminal_commit") is False
        and row.get("candidate_commit") is False
        and row.get("candidate_rejection") is False
        and row.get("uses_gt_for_action") is False
    ):
        return "target_rival_contradiction_region_contamination"
    return "audit_or_coverage_family"


def supported_candidate_id(row: Mapping[str, Any]) -> Optional[str]:
    state = str(row.get("non_gt_pairwise_rule_state") or "")
    if state == "candidate_a_provisionally_supported_by_non_gt_pairwise_rule":
        return str(row.get("candidate_a_id") or "")
    if state == "candidate_b_provisionally_supported_by_non_gt_pairwise_rule":
        return str(row.get("candidate_b_id") or "")
    value = row.get("provisionally_supported_candidate_id")
    return str(value) if value else None


def rival_candidate_id(row: Mapping[str, Any], supported_id: Optional[str]) -> Optional[str]:
    candidate_a = str(row.get("candidate_a_id") or "")
    candidate_b = str(row.get("candidate_b_id") or "")
    if supported_id == candidate_a:
        return candidate_b
    if supported_id == candidate_b:
        return candidate_a
    return None


def next_state(row: Mapping[str, Any], role: str) -> str:
    if role == "target_rival_contradiction_region_contamination":
        return "rival_contradiction_or_region_contamination_evidence_required"
    family = str(row.get("recommended_next_family") or "")
    if family == "goal_region_object_relation_coverage_completion_v1":
        return "coverage_completion_family_required"
    if family == "missing_evidence_second_view_followup_v1":
        return "missing_evidence_second_view_followup_required"
    if family == "goal_region_conditioned_relation_recheck_v1":
        return "goal_region_conditioned_relation_recheck_required"
    if family == "contrastive_goal_region_rival_support_audit_v1":
        return "contrastive_goal_region_rival_support_audit_required"
    return "diagnostic_audit_preserved"


def materialize_pair_rows(pair_diag_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(pair_diag_rows, key=pair_key):
        key = join_key(source)
        payload = key_payload(key)
        role = target_role_from_pair(source)
        supported_id = supported_candidate_id(source) if role.startswith("target_") else None
        rival_id = rival_candidate_id(source, supported_id)
        action_state = next_state(source, role)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "rival_contradiction_region_contamination_materialization",
                "row_type": "rival_contradiction_region_contamination_pair",
                "join_key": {
                    **payload,
                    "candidate_a_id": source.get("candidate_a_id"),
                    "candidate_b_id": source.get("candidate_b_id"),
                },
                **payload,
                "candidate_a_id": source.get("candidate_a_id"),
                "candidate_b_id": source.get("candidate_b_id"),
                "target_role": role,
                "selected_evidence_family": "rival_contradiction_or_region_contamination_evidence_v1",
                "source_recommended_next_family": source.get("recommended_next_family"),
                "source_failure_class_for_audit": source.get("failure_class"),
                "source_failure_mechanism_for_audit": source.get("failure_mechanism"),
                "source_non_gt_pairwise_rule_state": source.get("non_gt_pairwise_rule_state"),
                "source_goal_region_contrast_state": source.get("goal_region_contrast_state"),
                "source_object_relation_anchor_consistency_state": source.get(
                    "object_relation_anchor_consistency_state"
                ),
                "map_pose_non_contradiction_state": source.get("map_pose_non_contradiction_state"),
                "source_rule_input_complete": source.get("rule_input_complete") is True,
                "provisionally_supported_candidate_id": supported_id,
                "rival_candidate_id": rival_id,
                "rival_contradiction_region_contamination_state": action_state,
                "contamination_or_contradiction_evidence_required": role.startswith("target_"),
                "same_pair_order_as_source": True,
                "pair_label_dropped_from_action": True,
                "label_free_target_filter_used": True,
                "action_evidence_inputs": {
                    "source_name": payload["source_name"],
                    "scene_key": payload["scene_key"],
                    "query": payload["query"],
                    "request_id": payload["request_id"],
                    "episode_key": payload["episode_key"],
                    "candidate_a_id": source.get("candidate_a_id"),
                    "candidate_b_id": source.get("candidate_b_id"),
                    "provisionally_supported_candidate_id": supported_id,
                    "rival_candidate_id": rival_id,
                    "non_gt_pairwise_rule_state": source.get("non_gt_pairwise_rule_state"),
                    "goal_region_contrast_state": source.get("goal_region_contrast_state"),
                    "object_relation_anchor_consistency_state": source.get(
                        "object_relation_anchor_consistency_state"
                    ),
                    "map_pose_non_contradiction_state": source.get("map_pose_non_contradiction_state"),
                    "rule_input_complete": source.get("rule_input_complete") is True,
                    "fixed_evidence_family": "rival_contradiction_or_region_contamination_evidence_v1",
                },
                **common_flags(),
            }
        )
    return out


def materialize_request_rows(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for key, rows in sorted(group_by_request(pair_rows).items()):
        payload = key_payload(key)
        target_rows = [
            row for row in rows if row.get("target_role") == "target_rival_contradiction_region_contamination"
        ]
        request_state = (
            "request_rival_contradiction_region_contamination_evidence"
            if target_rows
            else "audit_or_coverage_family_preserved"
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "rival_contradiction_region_contamination_materialization",
                "row_type": "rival_contradiction_region_contamination_request",
                "join_key": payload,
                **payload,
                "request_state": request_state,
                "target_pair_rows": len(target_rows),
                "audit_pair_rows": len(rows) - len(target_rows),
                "pair_rows": len(rows),
                "pair_state_counts": compact_counter(
                    row.get("rival_contradiction_region_contamination_state") for row in rows
                ),
                "selected_evidence_family": "rival_contradiction_or_region_contamination_evidence_v1",
                "terminal_utility_allowed": False,
                "label_free_target_filter_used": True,
                **common_flags(),
            }
        )
    return out


def materialize_candidate_rows(
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_source_by_key: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    target_pairs = [
        row for row in pair_rows if row.get("target_role") == "target_rival_contradiction_region_contamination"
    ]
    for pair in target_pairs:
        key = join_key(pair)
        payload = key_payload(key)
        supported_id = str(pair.get("provisionally_supported_candidate_id") or "")
        rival_id = str(pair.get("rival_candidate_id") or "")
        for cid, role in ((supported_id, "provisionally_supported_candidate"), (rival_id, "rival_candidate")):
            source = candidate_source_by_key.get((*key, cid), {})
            out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "rival_contradiction_region_contamination_materialization",
                    "row_type": "rival_contradiction_region_contamination_candidate",
                    "join_key": {**payload, "candidate_id": cid},
                    **payload,
                    "candidate_id": cid,
                    "candidate_pair_role": role,
                    "paired_candidate_id": rival_id if role == "provisionally_supported_candidate" else supported_id,
                    "source_candidate_evidence_status": source.get("candidate_evidence_status"),
                    "source_candidate_support_evidence_count": source.get("candidate_support_evidence_count"),
                    "source_candidate_contradiction_evidence_count": source.get(
                        "candidate_contradiction_evidence_count"
                    ),
                    "source_candidate_has_provisional_pair_support": source.get(
                        "candidate_has_provisional_pair_support"
                    )
                    is True,
                    "viewpoint_coverage_delta": source.get("viewpoint_coverage_delta"),
                    "association_quality_proxy": source.get("association_quality_proxy"),
                    "map_pose_consistency_delta": source.get("map_pose_consistency_delta"),
                    "pose_graph_connectivity_delta": source.get("pose_graph_connectivity_delta"),
                    "map_pose_consistency_uncertainty_proxy": source.get(
                        "map_pose_consistency_uncertainty_proxy"
                    ),
                    "rival_contradiction_or_contamination_evidence_required": True,
                    "candidate_label_dropped_from_action": True,
                    "action_evidence_inputs": {
                        "candidate_id": cid,
                        "candidate_pair_role": role,
                        "paired_candidate_id": rival_id
                        if role == "provisionally_supported_candidate"
                        else supported_id,
                        "source_candidate_evidence_status": source.get("candidate_evidence_status"),
                        "source_candidate_support_evidence_count": source.get(
                            "candidate_support_evidence_count"
                        ),
                        "source_candidate_contradiction_evidence_count": source.get(
                            "candidate_contradiction_evidence_count"
                        ),
                        "source_candidate_has_provisional_pair_support": source.get(
                            "candidate_has_provisional_pair_support"
                        )
                        is True,
                        "viewpoint_coverage_delta": source.get("viewpoint_coverage_delta"),
                        "association_quality_proxy": source.get("association_quality_proxy"),
                        "map_pose_consistency_delta": source.get("map_pose_consistency_delta"),
                        "pose_graph_connectivity_delta": source.get("pose_graph_connectivity_delta"),
                        "map_pose_consistency_uncertainty_proxy": source.get(
                            "map_pose_consistency_uncertainty_proxy"
                        ),
                    },
                    **common_flags(),
                }
            )
    return sorted(out, key=candidate_key)


def materialize_observation_plan_rows(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    target_pairs = [
        row for row in pair_rows if row.get("target_role") == "target_rival_contradiction_region_contamination"
    ]
    for pair in target_pairs:
        key = join_key(pair)
        payload = key_payload(key)
        supported_id = str(pair.get("provisionally_supported_candidate_id") or "")
        rival_id = str(pair.get("rival_candidate_id") or "")
        for index, role in enumerate(OBSERVATION_ROLES, start=1):
            if role == "supported_candidate_own_view":
                target_candidate_id = supported_id
                context_candidate_id = rival_id
            elif role == "rival_candidate_own_view":
                target_candidate_id = rival_id
                context_candidate_id = supported_id
            else:
                target_candidate_id = supported_id
                context_candidate_id = rival_id
            out.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "rival_contradiction_region_contamination_materialization",
                    "row_type": "rival_contradiction_region_contamination_observation_plan",
                    "join_key": {
                        **payload,
                        "candidate_a_id": pair.get("candidate_a_id"),
                        "candidate_b_id": pair.get("candidate_b_id"),
                        "observation_role": role,
                    },
                    **payload,
                    "candidate_a_id": pair.get("candidate_a_id"),
                    "candidate_b_id": pair.get("candidate_b_id"),
                    "observation_index": index,
                    "observation_role": role,
                    "viewpoint_policy": "paired_supported_vs_rival_region_contamination_probe_v1",
                    "target_candidate_id": target_candidate_id,
                    "context_candidate_id": context_candidate_id,
                    "provisionally_supported_candidate_id": supported_id,
                    "rival_candidate_id": rival_id,
                    "evidence_axis": ROLE_EVIDENCE_AXIS[role],
                    "observation_goal": "acquire_label_free_rival_contradiction_or_region_contamination_evidence",
                    "frame_projection_contract_required_next": True,
                    "map_pose_fields_preserved": True,
                    "candidate_pair_preserved": True,
                    "action_plan_inputs": {
                        "candidate_a_id": pair.get("candidate_a_id"),
                        "candidate_b_id": pair.get("candidate_b_id"),
                        "target_candidate_id": target_candidate_id,
                        "context_candidate_id": context_candidate_id,
                        "observation_role": role,
                        "viewpoint_policy": "paired_supported_vs_rival_region_contamination_probe_v1",
                    },
                    **common_flags(),
                }
            )
    return out


def materialize_audit_rows(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pair in pair_rows:
        if pair.get("target_role") == "target_rival_contradiction_region_contamination":
            continue
        key = join_key(pair)
        payload = key_payload(key)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "rival_contradiction_region_contamination_materialization",
                "row_type": "rival_contradiction_region_contamination_audit",
                "join_key": {
                    **payload,
                    "candidate_a_id": pair.get("candidate_a_id"),
                    "candidate_b_id": pair.get("candidate_b_id"),
                },
                **payload,
                "candidate_a_id": pair.get("candidate_a_id"),
                "candidate_b_id": pair.get("candidate_b_id"),
                "audit_family_state": pair.get("rival_contradiction_region_contamination_state"),
                "source_recommended_next_family": pair.get("source_recommended_next_family"),
                "source_failure_class_for_audit": pair.get("source_failure_class_for_audit"),
                "audit_reason": "preserve_non_target_diagnostic_pair_for_coverage_or_followup_family",
                "terminal_utility_allowed": False,
                **common_flags(),
            }
        )
    return out


def materialize_failure_rows(pair_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for pair in pair_rows:
        key = join_key(pair)
        payload = key_payload(key)
        target = pair.get("target_role") == "target_rival_contradiction_region_contamination"
        blocker = (
            "rival_contradiction_region_contamination_evidence_required_before_terminal_utility"
            if target
            else "preserved_as_audit_or_coverage_family_before_terminal_utility"
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "rival_contradiction_region_contamination_materialization",
                "row_type": "rival_contradiction_region_contamination_failure",
                "join_key": {
                    **payload,
                    "candidate_a_id": pair.get("candidate_a_id"),
                    "candidate_b_id": pair.get("candidate_b_id"),
                },
                **payload,
                "candidate_a_id": pair.get("candidate_a_id"),
                "candidate_b_id": pair.get("candidate_b_id"),
                "primary_blocker": blocker,
                "failure_tags": [
                    "terminal_utility_blocked",
                    "candidate_rejection_blocked",
                    "evaluation_join_required_after_evidence_rows_are_frozen",
                ],
                "paper_claim_allowed_from_this_row": False,
                **common_flags(),
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


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    observation_plan_rows: Sequence[Mapping[str, Any]],
    audit_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    target_pairs = [
        row for row in pair_rows if row.get("target_role") == "target_rival_contradiction_region_contamination"
    ]
    target_requests = [
        row for row in request_rows if row.get("request_state") == "request_rival_contradiction_region_contamination_evidence"
    ]
    audit_pairs = [row for row in pair_rows if row.get("target_role") != "target_rival_contradiction_region_contamination"]
    gate = {
        "source_diagnostic_pair_rows_expected_passed": len(pair_rows)
        == contract["implementation_gate"]["source_diagnostic_pair_rows_expected"],
        "source_diagnostic_request_rows_expected_passed": len(request_rows)
        == contract["implementation_gate"]["source_diagnostic_request_rows_expected"],
        "target_pair_rows_expected_passed": len(target_pairs)
        == contract["implementation_gate"]["target_pair_rows_expected"],
        "target_request_rows_expected_passed": len(target_requests)
        == contract["implementation_gate"]["target_request_rows_expected"],
        "audit_pair_rows_minimum_passed": len(audit_pairs)
        >= contract["implementation_gate"]["audit_pair_rows_minimum"],
        "candidate_rows_minimum_passed": len(candidate_rows)
        >= contract["implementation_gate"]["candidate_rows_minimum"],
        "minimum_observation_plan_rows_passed": len(observation_plan_rows)
        >= contract["implementation_gate"]["minimum_observation_plan_rows"],
        "action_evidence_forbidden_key_count_passed": len(forbidden_keys)
        == contract["implementation_gate"]["action_evidence_forbidden_key_count_expected"],
        "terminal_commit_rows_passed": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "terminal_commit",
        )
        == contract["implementation_gate"]["terminal_commit_rows_expected"],
        "candidate_commit_rows_passed": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "candidate_commit",
        )
        == contract["implementation_gate"]["candidate_commit_rows_expected"],
        "candidate_rejection_rows_passed": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "candidate_rejection",
        )
        == contract["implementation_gate"]["candidate_rejection_rows_expected"],
        "uses_gt_for_action_true_rows_passed": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "uses_gt_for_action",
        )
        == contract["implementation_gate"]["uses_gt_for_action_true_rows_expected"],
        "paper_claim_allowed_true_rows_passed": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "paper_claim_allowed",
        )
        == contract["implementation_gate"]["paper_claim_allowed_true_rows_expected"],
    }
    materializer_gate_passed = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "materializer_gate_passed_terminal_blocked"
        if materializer_gate_passed
        else "materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "selected_family": contract.get("selected_family_from_diagnostic"),
        "request_rows": len(request_rows),
        "pair_rows": len(pair_rows),
        "target_request_rows": len(target_requests),
        "target_pair_rows": len(target_pairs),
        "audit_pair_rows": len(audit_pairs),
        "candidate_rows": len(candidate_rows),
        "observation_plan_rows": len(observation_plan_rows),
        "audit_rows": len(audit_rows),
        "failure_rows": len(failure_rows),
        "target_pair_row_keys": [
            {
                "source_name": row.get("source_name"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "request_id": row.get("request_id"),
                "episode_key": row.get("episode_key"),
                "candidate_a_id": row.get("candidate_a_id"),
                "candidate_b_id": row.get("candidate_b_id"),
            }
            for row in target_pairs
        ],
        "pair_target_role_counts": compact_counter(row.get("target_role") for row in pair_rows),
        "pair_state_counts": compact_counter(
            row.get("rival_contradiction_region_contamination_state") for row in pair_rows
        ),
        "request_state_counts": compact_counter(row.get("request_state") for row in request_rows),
        "candidate_pair_role_counts": compact_counter(row.get("candidate_pair_role") for row in candidate_rows),
        "observation_role_counts": compact_counter(row.get("observation_role") for row in observation_plan_rows),
        "audit_family_counts": compact_counter(row.get("source_recommended_next_family") for row in audit_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "terminal_commit",
        ),
        "candidate_commit_rows": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "candidate_commit",
        ),
        "candidate_rejection_rows": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "candidate_rejection",
        ),
        "uses_gt_for_action_true_rows": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "uses_gt_for_action",
        ),
        "paper_claim_allowed_true_rows": count_true(
            [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows],
            "paper_claim_allowed",
        ),
        "implementation_gate": gate,
        "materializer_gate_passed": materializer_gate_passed,
        "active_reobservation_promotion_gate_passed": False,
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": "frame_projection_or_post_observation_evidence_required"
        if materializer_gate_passed
        else "rival_contradiction_region_contamination_materializer_gate_failed",
        "next_task": "freeze_rival_contradiction_region_contamination_frame_projection_contract"
        if materializer_gate_passed
        else "fix_rival_contradiction_region_contamination_materializer",
        "interpretation": {
            "fact": (
                "The materializer writes request, pair, candidate, observation-plan, audit, failure, and summary "
                "rows for the frozen rival contradiction / region contamination evidence family."
            ),
            "agent_inference": (
                "The target is selected by label-free provisional support and evidence-state fields. The row still "
                "requires frame/projection or post-observation evidence before any terminal utility can be tested."
            ),
            "paper_claim": (
                "No ObjectNav improvement, Semantic-SLAM complementarity, terminal utility, formula revision, "
                "first_eval rerun, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed."
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
        "materialize_rival_contradiction_region_contamination_evidence.py"
    )
    return {
        "schema_version": f"{SCHEMA_VERSION}.verify",
        "date_checked": "2026-06-11",
        "ok": summary.get("materializer_gate_passed") is True,
        "status": summary.get("status"),
        "verified_artifact": str(contract_path),
        "out_root": str(out_root),
        "summary": str(out_root / OUTPUT_FILES["summary"]),
        "verified_output_counts": {
            "request_rows": summary.get("request_rows"),
            "pair_rows": summary.get("pair_rows"),
            "target_request_rows": summary.get("target_request_rows"),
            "target_pair_rows": summary.get("target_pair_rows"),
            "audit_pair_rows": summary.get("audit_pair_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "observation_plan_rows": summary.get("observation_plan_rows"),
            "audit_rows": summary.get("audit_rows"),
            "failure_rows": summary.get("failure_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "pair_target_role_counts": summary.get("pair_target_role_counts"),
        "pair_state_counts": summary.get("pair_state_counts"),
        "observation_role_counts": summary.get("observation_role_counts"),
        "implementation_gate": summary.get("implementation_gate"),
        "materializer_gate_passed": summary.get("materializer_gate_passed"),
        "active_reobservation_promotion_gate_passed": summary.get(
            "active_reobservation_promotion_gate_passed"
        ),
        "primary_blocker": summary.get("primary_blocker"),
        "next_task": summary.get("next_task"),
        "paper_claim_allowed": False,
        "verified_output_files": {name: str(out_root / filename) for name, filename in OUTPUT_FILES.items()},
        "verification_commands": [
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                f"python -m py_compile {script_path}"
            ),
            (
                "docker run --rm --ipc=host --user $(id -u):$(id -g) "
                "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
                "-e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime "
                "-v /home/yoohyun/research3:/workspace -w /workspace "
                "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
                "python -m h001_runtime.materialize_rival_contradiction_region_contamination_evidence"
            ),
            (
                "jq '{status, request_rows, pair_rows, target_pair_rows, candidate_rows, "
                "observation_plan_rows, materializer_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "failure_diagnostic_consumed": True,
            "target_filter_label_free": True,
            "same_pair_order_required": True,
            "same_candidate_pool_required": True,
            "pair_labels_dropped_from_action": True,
            "terminal_commit_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "terminal_utility_validation_allowed": False,
            "formula_revision_allowed": False,
            "first_eval_rerun_allowed": False,
            "policy_scale_comparison_allowed": False,
            "step_4_5_promotion_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": summary.get("interpretation"),
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")

    pair_diag_rows = load_jsonl(Path(str(source["failure_diagnostic_pair_rows"])))
    candidate_source_rows = load_jsonl(Path(str(source["pairwise_rule_evaluation_join_candidate_rows"])))

    candidate_source_by_key = index_candidates(candidate_source_rows)
    pair_rows = materialize_pair_rows(pair_diag_rows)
    request_rows = materialize_request_rows(pair_rows)
    candidate_rows = materialize_candidate_rows(pair_rows, candidate_source_by_key)
    observation_plan_rows = materialize_observation_plan_rows(pair_rows)
    audit_rows = materialize_audit_rows(pair_rows)
    failure_rows = materialize_failure_rows(pair_rows)
    forbidden_keys = scan_forbidden_action_inputs(
        [*request_rows, *pair_rows, *candidate_rows, *observation_plan_rows, *audit_rows, *failure_rows]
    )
    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        pair_rows=pair_rows,
        candidate_rows=candidate_rows,
        observation_plan_rows=observation_plan_rows,
        audit_rows=audit_rows,
        failure_rows=failure_rows,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["observation_plan_rows"], observation_plan_rows)
    write_jsonl(out_root / OUTPUT_FILES["audit_rows"], audit_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("materializer_gate_passed") is not True:
        raise SystemExit("rival contradiction / region contamination materializer gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize rival contradiction / region contamination evidence rows for H001."
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
                "request_rows": summary.get("request_rows"),
                "pair_rows": summary.get("pair_rows"),
                "target_pair_rows": summary.get("target_pair_rows"),
                "candidate_rows": summary.get("candidate_rows"),
                "observation_plan_rows": summary.get("observation_plan_rows"),
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
