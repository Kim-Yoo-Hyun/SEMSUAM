import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.pairwise_goal_region_map_pose_arbitration_rule.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_pairwise_goal_region_map_pose_arbitration_rule_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_pairwise_goal_region_map_pose_arbitration_rule_v1"

OUTPUT_FILES = {
    "request_rows": "pairwise_goal_region_map_pose_arbitration_rule_request_rows.jsonl",
    "candidate_rows": "pairwise_goal_region_map_pose_arbitration_rule_candidate_rows.jsonl",
    "pair_rows": "pairwise_goal_region_map_pose_arbitration_rule_pair_rows.jsonl",
    "failure_rows": "pairwise_goal_region_map_pose_arbitration_rule_failure_rows.jsonl",
    "summary": "pairwise_goal_region_map_pose_arbitration_rule_summary.json",
}

JOIN_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_correctness_label_for_evaluation_only",
    "candidate_wrong_label",
    "candidate_wrong_label_for_evaluation_only",
    "no_valid_candidate_pool_label",
    "no_valid_candidate_pool_for_evaluation_only",
    "candidate_pair_label_pattern_for_evaluation_only",
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


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


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


def external_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("scene_key") or row.get("scene_key") or ""),
        str(source.get("query") or row.get("query") or ""),
        str(
            source.get("request_id")
            or row.get("request_id")
            or row.get("rival_identity_request_id")
            or row.get("expanded_retrieval_request_id")
            or ""
        ),
        str(source.get("episode_key") or row.get("episode_key") or ""),
    )


def external_candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    return (*external_request_key(row), str(row.get("candidate_id") or ""))


def goal_region_pair_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, Tuple[str, str]]:
    pair_ids = tuple(sorted((str(row.get("focus_candidate_id") or ""), str(row.get("rival_candidate_id") or ""))))
    return (*external_request_key(row), pair_ids)  # type: ignore[return-value]


def source_pair_external_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, Tuple[str, str]]:
    pair_ids = tuple(sorted((str(row.get("candidate_a_id") or ""), str(row.get("candidate_b_id") or ""))))
    return (*external_request_key(row), pair_ids)  # type: ignore[return-value]


def key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(JOIN_KEYS, key))


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
        scan(row.get("rule_inputs", {}))
        scan(row.get("action_evidence_inputs", {}))
        scan(row.get("action_route_inputs", {}))
    return sorted(found)


def common_flags() -> Dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def index_candidates(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {candidate_key(row): row for row in rows}


def group_pairs_by_request(
    rows: Sequence[Mapping[str, Any]],
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[join_key(row)].append(row)
    return dict(grouped)


def index_goal_region_pairs(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, Tuple[str, str]], Mapping[str, Any]]:
    return {goal_region_pair_key(row): row for row in rows}


def index_object_relation_candidates(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {external_candidate_key(row): row for row in rows}


def role_support_from_goal_region(
    pair: Mapping[str, Any],
    candidate_id: str,
) -> Tuple[bool, bool, Optional[str]]:
    focus_id = str(pair.get("focus_candidate_id") or "")
    rival_id = str(pair.get("rival_candidate_id") or "")
    if candidate_id == focus_id:
        return (
            pair.get("focus_own_support") is True,
            pair.get("common_focus_support") is True,
            "focus",
        )
    if candidate_id == rival_id:
        return (pair.get("rival_own_support") is True, False, "rival")
    return (False, False, None)


def goal_region_state(
    pair: Mapping[str, Any],
    candidate_a_id: str,
    candidate_b_id: str,
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    if not pair:
        return (
            "goal_region_pair_evidence_missing",
            None,
            {
                "goal_region_pair_evidence_available": False,
                "candidate_a_goal_region_support": False,
                "candidate_b_goal_region_support": False,
            },
        )

    a_support, a_common, a_role = role_support_from_goal_region(pair, candidate_a_id)
    b_support, b_common, b_role = role_support_from_goal_region(pair, candidate_b_id)
    status = str(pair.get("goal_region_evidence_status") or "unknown_goal_region_state")
    if status == "contrastive_goal_region_pair" and a_support and not b_support:
        state = "candidate_a_contrastive_goal_region_support"
        supported = "candidate_a"
    elif status == "contrastive_goal_region_pair" and b_support and not a_support:
        state = "candidate_b_contrastive_goal_region_support"
        supported = "candidate_b"
    elif a_support and b_support:
        state = "both_candidates_have_goal_region_support"
        supported = None
    elif not a_support and not b_support:
        state = "neither_candidate_has_goal_region_support"
        supported = None
    else:
        state = "noncontrastive_goal_region_support"
        supported = None

    return (
        state,
        supported,
        {
            "goal_region_pair_evidence_available": True,
            "goal_region_evidence_status": status,
            "candidate_a_goal_region_role": a_role,
            "candidate_b_goal_region_role": b_role,
            "candidate_a_goal_region_support": a_support,
            "candidate_b_goal_region_support": b_support,
            "candidate_a_common_pair_support": a_common,
            "candidate_b_common_pair_support": b_common,
            "goal_region_recommended_nonterminal_action": pair.get("recommended_nonterminal_action"),
        },
    )


def relation_metrics(row: Mapping[str, Any]) -> Dict[str, Any]:
    routing = row.get("routing_inputs")
    routing = routing if isinstance(routing, Mapping) else {}
    return {
        "preferred_candidate_branch": row.get("preferred_candidate_branch"),
        "preferred_candidate_action": row.get("preferred_candidate_action"),
        "relation_depth_evidence_status": routing.get("relation_depth_evidence_status"),
        "relation_associated_heading_count": safe_int(routing.get("relation_associated_heading_count"), 0),
        "relation_depth_consistent_count": safe_int(routing.get("relation_depth_consistent_count"), 0),
        "relation_resolved_direction_source_count": safe_int(
            routing.get("relation_resolved_direction_source_count"),
            0,
        ),
        "base_candidate_specific_support": routing.get("base_candidate_specific_support") is True,
        "base_candidate_evidence_class": routing.get("base_candidate_evidence_class"),
        "arbitration_action": routing.get("arbitration_action"),
    }


def relation_consistent(metrics: Mapping[str, Any]) -> bool:
    return (
        metrics.get("relation_depth_evidence_status") == "relation_depth_recheck_resolved"
        and safe_int(metrics.get("relation_resolved_direction_source_count"), 0) >= 2
        and safe_int(metrics.get("relation_depth_consistent_count"), 0) >= 2
        and metrics.get("base_candidate_specific_support") is True
    )


def relation_contradicted(metrics: Mapping[str, Any]) -> bool:
    return str(metrics.get("arbitration_action") or "").startswith("reject_")


def object_relation_state(
    candidate_a: Mapping[str, Any],
    candidate_b: Mapping[str, Any],
) -> Tuple[str, Optional[str], Dict[str, Any]]:
    a = relation_metrics(candidate_a) if candidate_a else {}
    b = relation_metrics(candidate_b) if candidate_b else {}
    a_available = bool(candidate_a)
    b_available = bool(candidate_b)
    a_consistent = relation_consistent(a)
    b_consistent = relation_consistent(b)
    a_contradicted = relation_contradicted(a)
    b_contradicted = relation_contradicted(b)

    if not a_available or not b_available:
        state = "object_relation_evidence_missing"
        supported = None
    elif a_consistent and not b_consistent:
        state = "candidate_a_anchor_consistent"
        supported = "candidate_a"
    elif b_consistent and not a_consistent:
        state = "candidate_b_anchor_consistent"
        supported = "candidate_b"
    elif a_consistent and b_consistent:
        state = "both_candidates_anchor_consistent"
        supported = None
    elif a_contradicted and b_contradicted:
        state = "both_candidates_relation_contradicted"
        supported = None
    elif a_contradicted and not b_contradicted:
        state = "candidate_a_relation_contradicted"
        supported = None
    elif b_contradicted and not a_contradicted:
        state = "candidate_b_relation_contradicted"
        supported = None
    else:
        state = "object_relation_anchor_unstable_or_partial"
        supported = None

    return (
        state,
        supported,
        {
            "object_relation_candidate_a_available": a_available,
            "object_relation_candidate_b_available": b_available,
            "candidate_a_object_relation": a,
            "candidate_b_object_relation": b,
            "candidate_a_object_relation_anchor_consistent": a_consistent,
            "candidate_b_object_relation_anchor_consistent": b_consistent,
            "candidate_a_object_relation_contradicted": a_contradicted,
            "candidate_b_object_relation_contradicted": b_contradicted,
        },
    )


def map_pose_state(pair: Mapping[str, Any]) -> Tuple[str, bool, Dict[str, Any]]:
    map_pose_abs = safe_float(pair.get("map_pose_consistency_abs_delta"))
    pose_graph_abs = safe_float(pair.get("pose_graph_connectivity_abs_delta"))
    uncertainty_abs = safe_float(pair.get("map_pose_uncertainty_abs_delta"))
    if map_pose_abs is None or pose_graph_abs is None:
        return (
            "map_pose_non_contradiction_missing",
            False,
            {
                "map_pose_consistency_abs_delta": map_pose_abs,
                "pose_graph_connectivity_abs_delta": pose_graph_abs,
                "map_pose_uncertainty_abs_delta": uncertainty_abs,
            },
        )
    if map_pose_abs == 0.0 and pose_graph_abs == 0.0:
        state = "map_pose_non_contradictory_but_non_discriminative"
    else:
        state = "map_pose_non_contradictory_with_pair_delta"
    return (
        state,
        True,
        {
            "map_pose_consistency_abs_delta": map_pose_abs,
            "pose_graph_connectivity_abs_delta": pose_graph_abs,
            "map_pose_uncertainty_abs_delta": uncertainty_abs,
        },
    )


def provisional_state(
    *,
    selected_branch: str,
    goal_supported: Optional[str],
    relation_supported: Optional[str],
    relation_payload: Mapping[str, Any],
    map_pose_ok: bool,
    goal_state: str,
) -> Tuple[str, Optional[str]]:
    if selected_branch == "missing_evidence_second_view_followup_v1":
        return ("missing_evidence_second_view_followup_required", "missing_followup_pair_without_second_view_evidence")
    if selected_branch != "pairwise_goal_region_map_pose_arbitration_v1":
        return ("audit_control_preserved", "audit_control_preserved")
    if goal_supported is None:
        if goal_state == "goal_region_pair_evidence_missing":
            return ("pair_remains_unresolved", "any_required_non_gt_evidence_family_is_missing")
        return ("pair_remains_unresolved", goal_state)
    if relation_supported is None:
        if not relation_payload.get("object_relation_candidate_a_available") or not relation_payload.get(
            "object_relation_candidate_b_available"
        ):
            return ("pair_remains_unresolved", "any_required_non_gt_evidence_family_is_missing")
        return ("pair_remains_unresolved", "relation_anchor_assignment_is_unstable")
    if goal_supported != relation_supported:
        return ("pair_remains_unresolved", "goal_region_relation_support_disagree")
    if not map_pose_ok:
        return ("pair_remains_unresolved", "map_pose_non_contradiction_missing")
    if goal_supported == "candidate_a":
        return ("candidate_a_provisionally_supported_by_non_gt_pairwise_rule", None)
    return ("candidate_b_provisionally_supported_by_non_gt_pairwise_rule", None)


def materialize_pair_rows(
    *,
    source_pairs: Sequence[Mapping[str, Any]],
    goal_region_pairs_by_key: Mapping[Tuple[str, str, str, str, Tuple[str, str]], Mapping[str, Any]],
    object_relation_by_candidate: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_pairs, key=pair_key):
        key = join_key(source)
        payload = key_payload(key)
        candidate_a_id = str(source.get("candidate_a_id") or "")
        candidate_b_id = str(source.get("candidate_b_id") or "")
        external_key = external_request_key(source)
        goal_region = goal_region_pairs_by_key.get(source_pair_external_key(source)) or {}
        object_a = object_relation_by_candidate.get((*external_key, candidate_a_id)) or {}
        object_b = object_relation_by_candidate.get((*external_key, candidate_b_id)) or {}

        goal_state, goal_supported, goal_payload = goal_region_state(goal_region, candidate_a_id, candidate_b_id)
        relation_state, relation_supported, relation_payload = object_relation_state(object_a, object_b)
        map_state, map_ok, map_payload = map_pose_state(source)
        selected_branch = str(source.get("selected_branch") or "")
        state, defer_reason = provisional_state(
            selected_branch=selected_branch,
            goal_supported=goal_supported,
            relation_supported=relation_supported,
            relation_payload=relation_payload,
            map_pose_ok=map_ok,
            goal_state=goal_state,
        )
        rule_input_complete = bool(
            selected_branch == "pairwise_goal_region_map_pose_arbitration_v1"
            and goal_payload.get("goal_region_pair_evidence_available") is True
            and relation_payload.get("object_relation_candidate_a_available") is True
            and relation_payload.get("object_relation_candidate_b_available") is True
            and map_ok
        )
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "pairwise_goal_region_map_pose_arbitration_rule_materialization",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_pair",
                "join_key": {**payload, "candidate_a_id": candidate_a_id, "candidate_b_id": candidate_b_id},
                **payload,
                "candidate_a_id": candidate_a_id,
                "candidate_b_id": candidate_b_id,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("source_branch_action"),
                "source_resolution_route": source.get("source_resolution_route"),
                "selected_evidence_family": source.get("selected_evidence_family"),
                "selected_branch": selected_branch,
                "selected_action": source.get("selected_action"),
                "same_pair_order_as_source": True,
                "source_pair_label_removed_from_rule_input": True,
                "non_gt_pairwise_rule_state": state,
                "goal_region_contrast_state": goal_state,
                "object_relation_anchor_consistency_state": relation_state,
                "map_pose_non_contradiction_state": map_state,
                "rule_input_complete": rule_input_complete,
                "rule_defer_reason": defer_reason,
                "pairwise_goal_validity_arbitration_required": (
                    source.get("pairwise_goal_validity_arbitration_required") is True
                ),
                "missing_evidence_second_view_followup_required": (
                    source.get("missing_evidence_second_view_followup_required") is True
                ),
                "candidate_a_support_evidence_count": safe_int(source.get("candidate_a_support_evidence_count"), 0),
                "candidate_b_support_evidence_count": safe_int(source.get("candidate_b_support_evidence_count"), 0),
                "candidate_a_contradiction_evidence_count": safe_int(
                    source.get("candidate_a_contradiction_evidence_count"),
                    0,
                ),
                "candidate_b_contradiction_evidence_count": safe_int(
                    source.get("candidate_b_contradiction_evidence_count"),
                    0,
                ),
                "support_count_abs_delta": safe_int(source.get("support_count_abs_delta"), 0),
                "contradiction_count_abs_delta": safe_int(source.get("contradiction_count_abs_delta"), 0),
                "viewpoint_coverage_abs_delta": safe_float(source.get("viewpoint_coverage_abs_delta")),
                "association_quality_abs_delta": safe_float(source.get("association_quality_abs_delta")),
                **map_payload,
                **goal_payload,
                **relation_payload,
                "rule_inputs": {
                    "selected_branch": selected_branch,
                    "candidate_pair_status_pattern": source.get("candidate_pair_status_pattern"),
                    "candidate_a_evidence_status": source.get("candidate_a_evidence_status"),
                    "candidate_b_evidence_status": source.get("candidate_b_evidence_status"),
                    "support_count_abs_delta": safe_int(source.get("support_count_abs_delta"), 0),
                    "contradiction_count_abs_delta": safe_int(source.get("contradiction_count_abs_delta"), 0),
                    "viewpoint_coverage_abs_delta": safe_float(source.get("viewpoint_coverage_abs_delta")),
                    "association_quality_abs_delta": safe_float(source.get("association_quality_abs_delta")),
                    "goal_region_contrast_state": goal_state,
                    "object_relation_anchor_consistency_state": relation_state,
                    "map_pose_non_contradiction_state": map_state,
                },
                "evaluation_labels_forbidden_for_rule": True,
                "terminal_selector_allowed_from_this_rule": False,
                **common_flags(),
            }
        )
    return out


def pair_state_for_candidate(candidate: Mapping[str, Any], pairs_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]]) -> Dict[str, Any]:
    cid = candidate_key(candidate)[-1]
    pairs = [pair for pair in pairs_by_key.get(join_key(candidate), []) if cid in {pair.get("candidate_a_id"), pair.get("candidate_b_id")}]
    if not pairs:
        return {
            "candidate_in_pair_rule_rows": 0,
            "candidate_pair_rule_states": [],
            "candidate_has_provisional_pair_support": False,
        }
    provisional_states = {
        "candidate_a_provisionally_supported_by_non_gt_pairwise_rule",
        "candidate_b_provisionally_supported_by_non_gt_pairwise_rule",
    }
    has_support = False
    for pair in pairs:
        state = pair.get("non_gt_pairwise_rule_state")
        if state == "candidate_a_provisionally_supported_by_non_gt_pairwise_rule" and pair.get("candidate_a_id") == cid:
            has_support = True
        if state == "candidate_b_provisionally_supported_by_non_gt_pairwise_rule" and pair.get("candidate_b_id") == cid:
            has_support = True
    return {
        "candidate_in_pair_rule_rows": len(pairs),
        "candidate_pair_rule_states": sorted(str(pair.get("non_gt_pairwise_rule_state")) for pair in pairs),
        "candidate_has_provisional_pair_support": has_support,
        "candidate_pair_rule_has_any_provisional_support": any(
            pair.get("non_gt_pairwise_rule_state") in provisional_states for pair in pairs
        ),
    }


def materialize_candidate_rows(
    *,
    source_candidates: Sequence[Mapping[str, Any]],
    pairs_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_candidates, key=candidate_key):
        key = join_key(source)
        payload = key_payload(key)
        cid = candidate_key(source)[-1]
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "pairwise_goal_region_map_pose_arbitration_rule_materialization",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_candidate",
                "join_key": {**payload, "candidate_id": cid},
                **payload,
                "candidate_id": cid,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("source_branch_action"),
                "source_resolution_route": source.get("source_resolution_route"),
                "selected_evidence_family": source.get("selected_evidence_family"),
                "selected_branch": source.get("selected_branch"),
                "selected_action": source.get("selected_action"),
                "request_evidence_status": source.get("request_evidence_status"),
                "candidate_evidence_status": source.get("candidate_evidence_status"),
                "candidate_evidence_reason": source.get("candidate_evidence_reason"),
                "candidate_support_evidence_count": safe_int(source.get("candidate_support_evidence_count"), 0),
                "candidate_contradiction_evidence_count": safe_int(
                    source.get("candidate_contradiction_evidence_count"),
                    0,
                ),
                "viewpoint_coverage_delta": safe_float(source.get("viewpoint_coverage_delta")),
                "association_quality_proxy": safe_float(source.get("association_quality_proxy")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_uncertainty_proxy": safe_float(
                    source.get("map_pose_consistency_uncertainty_proxy")
                ),
                "evaluation_label_fields_dropped_for_rule": True,
                **pair_state_for_candidate(source, pairs_by_key),
                **common_flags(),
            }
        )
    return out


def materialize_request_rows(
    *,
    source_requests: Sequence[Mapping[str, Any]],
    pairs_by_key: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for source in sorted(source_requests, key=join_key):
        key = join_key(source)
        payload = key_payload(key)
        pairs = list(pairs_by_key.get(key, []))
        pair_states = [str(pair.get("non_gt_pairwise_rule_state")) for pair in pairs]
        has_provisional = any("provisionally_supported" in state for state in pair_states)
        state = "audit_control_preserved"
        if source.get("target_role") == "primary_target":
            if has_provisional:
                state = "non_gt_pairwise_rule_provisional_support_available"
            elif any(state == "missing_evidence_second_view_followup_required" for state in pair_states):
                state = "missing_evidence_second_view_followup_required"
            else:
                state = "pairwise_goal_region_map_pose_arbitration_unresolved"
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "pairwise_goal_region_map_pose_arbitration_rule_materialization",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_request",
                "join_key": payload,
                **payload,
                "target_role": source.get("target_role"),
                "source_branch_action": source.get("source_branch_action"),
                "source_resolution_route": source.get("source_resolution_route"),
                "source_resolution_reason": source.get("source_resolution_reason"),
                "selected_evidence_family": source.get("selected_evidence_family"),
                "selected_branch": source.get("selected_branch"),
                "selected_action": source.get("selected_action"),
                "request_evidence_status": source.get("request_evidence_status"),
                "post_action_goal_validity_evidence_available": (
                    source.get("post_action_goal_validity_evidence_available") is True
                ),
                "goal_validity_risk_state": source.get("goal_validity_risk_state"),
                "viewpoint_evidence_gap_state": source.get("viewpoint_evidence_gap_state"),
                "map_pose_consistency_uncertainty_state": source.get("map_pose_consistency_uncertainty_state"),
                "pose_graph_connectivity_delta": safe_float(source.get("pose_graph_connectivity_delta")),
                "map_pose_consistency_delta": safe_float(source.get("map_pose_consistency_delta")),
                "pair_rule_rows": len(pairs),
                "pair_rule_state_counts": compact_counter(pair_states),
                "request_rule_state": state,
                "rule_output_nonterminal": True,
                "evaluation_label_fields_dropped_for_rule": True,
                **common_flags(),
            }
        )
    return out


def failure_tags(row: Mapping[str, Any]) -> List[str]:
    tags = [
        "terminal_utility_blocked",
        "candidate_commit_blocked",
        "candidate_rejection_blocked",
        "paper_claim_blocked",
        "pairwise_rule_materialization_only",
    ]
    if row.get("target_role") != "primary_target":
        tags.append("audit_control_preserved")
    else:
        state = row.get("request_rule_state")
        if state == "non_gt_pairwise_rule_provisional_support_available":
            tags.append("pairwise_rule_evaluation_join_required")
        elif state == "missing_evidence_second_view_followup_required":
            tags.append("missing_evidence_second_view_followup_required")
        else:
            tags.append("pairwise_goal_region_map_pose_arbitration_unresolved")
    return sorted(set(tags))


def primary_failure(tags: Sequence[str]) -> str:
    for tag in (
        "pairwise_rule_evaluation_join_required",
        "pairwise_goal_region_map_pose_arbitration_unresolved",
        "missing_evidence_second_view_followup_required",
        "audit_control_preserved",
    ):
        if tag in tags:
            return tag
    return "pairwise_rule_materialization_only"


def materialize_failure_rows(request_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for request in sorted(request_rows, key=join_key):
        key = join_key(request)
        payload = key_payload(key)
        tags = failure_tags(request)
        out.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "pairwise_goal_region_map_pose_arbitration_rule_materialization",
                "row_type": "pairwise_goal_region_map_pose_arbitration_rule_failure",
                "join_key": payload,
                **payload,
                "target_role": request.get("target_role"),
                "selected_branch": request.get("selected_branch"),
                "selected_action": request.get("selected_action"),
                "request_rule_state": request.get("request_rule_state"),
                "failure_tags": tags,
                "primary_failure_or_blocker": primary_failure(tags),
                **common_flags(),
            }
        )
    return out


def gate_from_counts(contract: Mapping[str, Any], counts: Mapping[str, int]) -> Dict[str, bool]:
    gate = contract.get("implementation_gate")
    gate = gate if isinstance(gate, Mapping) else {}
    return {
        "request_rows_expected_passed": counts["request_rows"] == safe_int(gate.get("request_rows_expected"), 50),
        "selected_target_request_rows_expected_passed": counts["selected_target_request_rows"]
        == safe_int(gate.get("selected_target_request_rows_expected"), 21),
        "audit_request_rows_expected_passed": counts["audit_request_rows"]
        == safe_int(gate.get("audit_request_rows_expected"), 29),
        "candidate_rows_expected_passed": counts["candidate_rows"] == safe_int(gate.get("candidate_rows_expected"), 97),
        "pair_rows_expected_passed": counts["pair_rows"] == safe_int(gate.get("pair_rows_expected"), 21),
        "pairwise_arbitration_pair_rows_expected_passed": counts["pairwise_arbitration_pair_rows"]
        == safe_int(gate.get("pairwise_arbitration_pair_rows_expected"), 18),
        "missing_followup_pair_rows_expected_passed": counts["missing_followup_pair_rows"]
        == safe_int(gate.get("missing_followup_pair_rows_expected"), 3),
        "baseline_rows_preserved_for_later_evaluation_passed": counts["baseline_rows"]
        == safe_int(gate.get("baseline_rows_preserved_for_later_evaluation"), 150),
        "action_evidence_forbidden_key_count_passed": counts["action_evidence_forbidden_key_count"]
        == safe_int(gate.get("action_evidence_forbidden_key_count_expected"), 0),
        "terminal_commit_rows_passed": counts["terminal_commit_rows"]
        == safe_int(gate.get("terminal_commit_rows_expected"), 0),
        "candidate_commit_rows_passed": counts["candidate_commit_rows"]
        == safe_int(gate.get("candidate_commit_rows_expected"), 0),
        "candidate_rejection_rows_passed": counts["candidate_rejection_rows"]
        == safe_int(gate.get("candidate_rejection_rows_expected"), 0),
        "uses_gt_for_action_true_rows_passed": counts["uses_gt_for_action_true_rows"]
        == safe_int(gate.get("uses_gt_for_action_true_rows_expected"), 0),
        "paper_claim_allowed_true_rows_passed": counts["paper_claim_allowed_true_rows"]
        == safe_int(gate.get("paper_claim_allowed_true_rows_expected"), 0),
    }


def build_summary(
    *,
    contract: Mapping[str, Any],
    contract_path: Path,
    out_root: Path,
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    pair_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    baseline_rows: Sequence[Mapping[str, Any]],
    forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    all_rule_rows = [*request_rows, *candidate_rows, *pair_rows, *failure_rows]
    primary_requests = [row for row in request_rows if row.get("target_role") == "primary_target"]
    audit_requests = [row for row in request_rows if row.get("target_role") != "primary_target"]
    counts = {
        "request_rows": len(request_rows),
        "selected_target_request_rows": len(primary_requests),
        "audit_request_rows": len(audit_requests),
        "candidate_rows": len(candidate_rows),
        "selected_target_candidate_rows": sum(1 for row in candidate_rows if row.get("target_role") == "primary_target"),
        "pair_rows": len(pair_rows),
        "pairwise_arbitration_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "pairwise_goal_region_map_pose_arbitration_v1"
        ),
        "missing_followup_pair_rows": sum(
            1 for row in pair_rows if row.get("selected_branch") == "missing_evidence_second_view_followup_v1"
        ),
        "baseline_rows": len(baseline_rows),
        "failure_rows": len(failure_rows),
        "provisional_candidate_a_rows": sum(
            1
            for row in pair_rows
            if row.get("non_gt_pairwise_rule_state")
            == "candidate_a_provisionally_supported_by_non_gt_pairwise_rule"
        ),
        "provisional_candidate_b_rows": sum(
            1
            for row in pair_rows
            if row.get("non_gt_pairwise_rule_state")
            == "candidate_b_provisionally_supported_by_non_gt_pairwise_rule"
        ),
        "pair_unresolved_rows": sum(
            1 for row in pair_rows if row.get("non_gt_pairwise_rule_state") == "pair_remains_unresolved"
        ),
        "missing_followup_required_rows": sum(
            1
            for row in pair_rows
            if row.get("non_gt_pairwise_rule_state") == "missing_evidence_second_view_followup_required"
        ),
        "rule_input_complete_rows": sum(1 for row in pair_rows if row.get("rule_input_complete") is True),
        "goal_region_pair_evidence_available_rows": sum(
            1 for row in pair_rows if row.get("goal_region_pair_evidence_available") is True
        ),
        "object_relation_pair_evidence_available_rows": sum(
            1
            for row in pair_rows
            if row.get("object_relation_candidate_a_available") is True
            and row.get("object_relation_candidate_b_available") is True
        ),
        "map_pose_non_contradiction_rows": sum(
            1
            for row in pair_rows
            if str(row.get("map_pose_non_contradiction_state") or "").startswith("map_pose_non_contradictory")
        ),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "terminal_commit_rows": count_true(all_rule_rows, "terminal_commit"),
        "candidate_commit_rows": count_true(all_rule_rows, "candidate_commit"),
        "candidate_rejection_rows": count_true(all_rule_rows, "candidate_rejection"),
        "uses_gt_for_action_true_rows": count_true(all_rule_rows, "uses_gt_for_action"),
        "paper_claim_allowed_true_rows": count_true(all_rule_rows, "paper_claim_allowed"),
    }
    gate = gate_from_counts(contract, counts)
    materializer_gate_passed = all(gate.values())
    provisional_rows = counts["provisional_candidate_a_rows"] + counts["provisional_candidate_b_rows"]
    if provisional_rows > 0:
        primary_blocker = "pairwise_rule_evaluation_join_required"
        next_task = "freeze_pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_contract"
    else:
        primary_blocker = "pairwise_goal_region_map_pose_arbitration_unresolved"
        next_task = "diagnose_goal_region_object_relation_evidence_gap_before_terminal_utility"
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-11",
        "status": "pairwise_rule_materializer_gate_passed_terminal_blocked"
        if materializer_gate_passed
        else "pairwise_rule_materializer_gate_failed",
        "contract": str(contract_path),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_files": contract.get("source", {}),
        **counts,
        "non_gt_pairwise_rule_state_counts": compact_counter(row.get("non_gt_pairwise_rule_state") for row in pair_rows),
        "goal_region_contrast_state_counts": compact_counter(row.get("goal_region_contrast_state") for row in pair_rows),
        "object_relation_anchor_consistency_state_counts": compact_counter(
            row.get("object_relation_anchor_consistency_state") for row in pair_rows
        ),
        "map_pose_non_contradiction_state_counts": compact_counter(
            row.get("map_pose_non_contradiction_state") for row in pair_rows
        ),
        "rule_defer_reason_counts": compact_counter(row.get("rule_defer_reason") for row in pair_rows),
        "request_rule_state_counts": compact_counter(row.get("request_rule_state") for row in request_rows),
        "failure_tag_counts": compact_counter(tag for row in failure_rows for tag in row.get("failure_tags", [])),
        "primary_failure_counts": compact_counter(row.get("primary_failure_or_blocker") for row in failure_rows),
        "action_evidence_forbidden_keys": list(forbidden_keys),
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
        "primary_blocker": primary_blocker,
        "next_task": next_task,
        "interpretation": {
            "fact": (
                "The materializer applies the frozen non-GT pairwise rule to preserved request, candidate, and pair "
                "rows while keeping correctness labels, wrong-goal outcomes, and oracle fields out of rule inputs."
            ),
            "agent_inference": (
                "This artifact tests whether goal-region/object-relation contrast plus map/pose non-contradiction "
                "can produce provisional support without terminal commits. Any provisional support still requires "
                "a separate action-frozen evaluation join."
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
        "materialize_pairwise_goal_region_map_pose_arbitration_rule.py"
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
            "selected_target_request_rows": summary.get("selected_target_request_rows"),
            "audit_request_rows": summary.get("audit_request_rows"),
            "candidate_rows": summary.get("candidate_rows"),
            "selected_target_candidate_rows": summary.get("selected_target_candidate_rows"),
            "pair_rows": summary.get("pair_rows"),
            "pairwise_arbitration_pair_rows": summary.get("pairwise_arbitration_pair_rows"),
            "missing_followup_pair_rows": summary.get("missing_followup_pair_rows"),
            "baseline_rows": summary.get("baseline_rows"),
            "failure_rows": summary.get("failure_rows"),
            "provisional_candidate_a_rows": summary.get("provisional_candidate_a_rows"),
            "provisional_candidate_b_rows": summary.get("provisional_candidate_b_rows"),
            "pair_unresolved_rows": summary.get("pair_unresolved_rows"),
            "missing_followup_required_rows": summary.get("missing_followup_required_rows"),
            "rule_input_complete_rows": summary.get("rule_input_complete_rows"),
            "goal_region_pair_evidence_available_rows": summary.get("goal_region_pair_evidence_available_rows"),
            "object_relation_pair_evidence_available_rows": summary.get("object_relation_pair_evidence_available_rows"),
            "map_pose_non_contradiction_rows": summary.get("map_pose_non_contradiction_rows"),
            "action_evidence_forbidden_key_count": summary.get("action_evidence_forbidden_key_count"),
            "terminal_commit_rows": summary.get("terminal_commit_rows"),
            "candidate_commit_rows": summary.get("candidate_commit_rows"),
            "candidate_rejection_rows": summary.get("candidate_rejection_rows"),
            "uses_gt_for_action_true_rows": summary.get("uses_gt_for_action_true_rows"),
            "paper_claim_allowed_true_rows": summary.get("paper_claim_allowed_true_rows"),
        },
        "non_gt_pairwise_rule_state_counts": summary.get("non_gt_pairwise_rule_state_counts"),
        "goal_region_contrast_state_counts": summary.get("goal_region_contrast_state_counts"),
        "object_relation_anchor_consistency_state_counts": summary.get(
            "object_relation_anchor_consistency_state_counts"
        ),
        "map_pose_non_contradiction_state_counts": summary.get("map_pose_non_contradiction_state_counts"),
        "rule_defer_reason_counts": summary.get("rule_defer_reason_counts"),
        "implementation_gate": summary.get("implementation_gate"),
        "materializer_gate_passed": summary.get("materializer_gate_passed"),
        "active_reobservation_promotion_gate_passed": summary.get("active_reobservation_promotion_gate_passed"),
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
                "python -m h001_runtime.materialize_pairwise_goal_region_map_pose_arbitration_rule"
            ),
            (
                "jq '{status, request_rows, candidate_rows, pair_rows, provisional_candidate_a_rows, "
                "provisional_candidate_b_rows, pair_unresolved_rows, missing_followup_required_rows, "
                "materializer_gate_passed, active_reobservation_promotion_gate_passed, primary_blocker, next_task}' "
                f"{out_root / OUTPUT_FILES['summary']}"
            ),
        ],
        "contract_checks": {
            "source_evaluation_join_preserved": True,
            "same_pair_order_required": True,
            "same_candidate_pool_required": True,
            "labels_for_rule_input_forbidden": True,
            "wrong_goal_for_rule_input_forbidden": True,
            "goal_region_or_object_relation_evidence_required": True,
            "map_pose_only_terminal_shortcut_forbidden": True,
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

    request_rows_source = load_jsonl(
        Path(str(source["post_action_arbitration_followup_evaluation_join_request_rows"]))
    )
    candidate_rows_source = load_jsonl(
        Path(str(source["post_action_arbitration_followup_evaluation_join_candidate_rows"]))
    )
    pair_rows_source = load_jsonl(Path(str(source["post_action_arbitration_followup_evaluation_join_pair_rows"])))
    baseline_rows_source = load_jsonl(
        Path(str(source["post_action_arbitration_followup_evaluation_join_baseline_rows"]))
    )
    goal_region_pair_rows = load_jsonl(
        Path(
            "local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1/"
            "unique_support_goal_region_pair_evidence_rows.jsonl"
        )
    )
    object_relation_candidate_rows = load_jsonl(
        Path(
            "local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1/"
            "goal_validity_object_relation_branch_candidate_rows.jsonl"
        )
    )

    goal_region_pairs_by_key = index_goal_region_pairs(goal_region_pair_rows)
    object_relation_by_candidate = index_object_relation_candidates(object_relation_candidate_rows)

    pair_rows = materialize_pair_rows(
        source_pairs=pair_rows_source,
        goal_region_pairs_by_key=goal_region_pairs_by_key,
        object_relation_by_candidate=object_relation_by_candidate,
    )
    pairs_by_key = group_pairs_by_request(pair_rows)
    request_rows = materialize_request_rows(source_requests=request_rows_source, pairs_by_key=pairs_by_key)
    candidate_rows = materialize_candidate_rows(source_candidates=candidate_rows_source, pairs_by_key=pairs_by_key)
    failure_rows = materialize_failure_rows(request_rows)
    forbidden_keys = scan_forbidden_action_inputs([*request_rows, *candidate_rows, *pair_rows, *failure_rows])

    summary = build_summary(
        contract=contract,
        contract_path=contract_path,
        out_root=out_root,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        failure_rows=failure_rows,
        baseline_rows=baseline_rows_source,
        forbidden_keys=forbidden_keys,
    )

    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["pair_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["failure_rows"], failure_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(
        verification_path(contract_path),
        build_verify_payload(contract_path=contract_path, out_root=out_root, summary=summary),
    )

    if summary.get("materializer_gate_passed") is not True:
        raise SystemExit("pairwise goal-region/map-pose arbitration rule materializer gate failed")
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Materialize the frozen non-GT pairwise goal-region/map-pose arbitration rule."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
