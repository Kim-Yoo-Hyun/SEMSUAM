import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.repeated_object_relation_anchor_consistency_plan.v1"
POLICY_NAME = "RepeatedObjectRelationAnchorConsistencyEvidence"
PLANNER_NAME = "repeated_object_relation_anchor_consistency_v1"
VIEWPOINT_POLICY = "relation_anchor_consistency_standoff_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_repeated_object_relation_anchor_consistency_evidence_v1.json"
)
PRIOR_PLAN_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/"
    "partial_relation_depth_observation_plan.jsonl"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_repeated_object_relation_anchor_consistency_v1"

ROLE_TO_DIRECTION = {
    "candidate_own_view": "relation_anchor_to_target",
    "relation_anchor_context_view": "target_to_relation_anchor",
    "orthogonal_axis_challenge_view": "orthogonal_relation_axis",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, source_key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if source_key not in source:
        raise KeyError(f"contract source is missing {source_key}")
    return Path(str(source[source_key]))


def request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("target_candidate_id") or row.get("candidate_id") or "")


def safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return number


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) < 3:
        return None
    output: List[float] = []
    for item in value[:3]:
        number = safe_float(item)
        if number is None:
            return None
        output.append(number)
    return output


def horizontal_distance(a: Any, b: Any) -> Optional[float]:
    vec_a = vector3(a)
    vec_b = vector3(b)
    if vec_a is None or vec_b is None:
        return None
    return math.sqrt((vec_a[0] - vec_b[0]) ** 2 + (vec_a[2] - vec_b[2]) ** 2)


def sort_request_id(value: str) -> Tuple[str, int, str]:
    text = str(value)
    if ":" in text:
        prefix, suffix = text.rsplit(":", 1)
        return (prefix, safe_int(suffix, 999999), suffix)
    return (text, 999999, text)


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def unique_ordered(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        output.append(text)
        seen.add(text)
    return output


def source_suffix(value: str) -> Tuple[int, str]:
    text = str(value)
    try:
        return (int(text.rsplit(":", 1)[-1]), text)
    except ValueError:
        return (999999, text)


def expected_requests(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    target_scope = contract.get("target_scope") or {}
    requests = [dict(row) for row in target_scope.get("target_requests") or []]
    return sorted(requests, key=lambda row: sort_request_id(str(row.get("expanded_retrieval_request_id") or "")))


def expected_candidate_ids(contract: Dict[str, Any]) -> List[str]:
    source_gate = contract.get("source_gate") or {}
    return sorted([str(value) for value in source_gate.get("expected_candidate_ids") or []], key=source_suffix)


def expected_request_ids(contract: Dict[str, Any]) -> List[str]:
    source_gate = contract.get("source_gate") or {}
    return [str(value) for value in source_gate.get("expected_request_ids") or []]


def row_sort_key(row: Dict[str, Any]) -> Tuple[Tuple[str, int, str], Tuple[int, str], int, str]:
    return (
        sort_request_id(request_id(row)),
        source_suffix(candidate_id(row)),
        safe_int(row.get("failed_evidence_index"), 999999),
        str(row.get("requested_direction_source") or row.get("prior_standoff_direction_source") or ""),
    )


def target_branch_rows(rows: Sequence[Dict[str, Any]], contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    request_ids = set(expected_request_ids(contract))
    candidate_ids = set(expected_candidate_ids(contract))
    source_gate = contract.get("source_gate") or {}
    scene_query = set(str(value) for value in source_gate.get("expected_scene_query") or [])

    filtered = []
    for row in rows:
        if request_id(row) not in request_ids:
            continue
        if candidate_id(row) not in candidate_ids:
            continue
        if scene_query and f"{row.get('scene_key')}/{row.get('query')}" not in scene_query:
            continue
        filtered.append(dict(row))
    return sorted(filtered, key=row_sort_key)


def target_request_rows(rows: Sequence[Dict[str, Any]], contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    request_ids = set(expected_request_ids(contract))
    filtered = [dict(row) for row in rows if request_id(row) in request_ids]
    return sorted(filtered, key=lambda row: sort_request_id(request_id(row)))


def prior_plan_rows(rows: Sequence[Dict[str, Any]], contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    request_ids = set(expected_request_ids(contract))
    candidate_ids = set(expected_candidate_ids(contract))
    filtered = []
    for row in rows:
        if request_id(row) not in request_ids:
            continue
        if candidate_id(row) not in candidate_ids:
            continue
        filtered.append(dict(row))
    return sorted(filtered, key=row_sort_key)


def prior_context_rows(rows: Sequence[Dict[str, Any]], contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    request_ids = set(expected_request_ids(contract))
    candidate_ids = set(expected_candidate_ids(contract))
    source_gate = contract.get("source_gate") or {}
    expected_context_ids = set(str(value) for value in source_gate.get("expected_prior_context_candidate_ids") or [])
    filtered = []
    for row in rows:
        if request_id(row) not in request_ids:
            continue
        if candidate_id(row) not in candidate_ids:
            continue
        context_id = str(row.get("context_candidate_id") or "")
        if expected_context_ids and context_id not in expected_context_ids:
            continue
        filtered.append(dict(row))
    return sorted(
        filtered,
        key=lambda row: (
            sort_request_id(request_id(row)),
            source_suffix(candidate_id(row)),
            source_suffix(str(row.get("context_candidate_id") or "")),
            safe_int(row.get("context_anchor_index"), 999999),
        ),
    )


def group_by_key(rows: Sequence[Dict[str, Any]], key_fn: Any) -> Dict[Any, List[Dict[str, Any]]]:
    grouped: Dict[Any, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[key_fn(row)].append(dict(row))
    return grouped


def best_plan_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[
            (
                request_id(row),
                candidate_id(row),
                str(row.get("requested_direction_source") or row.get("standoff_direction_source") or ""),
            )
        ].append(dict(row))

    output: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for key, candidates in grouped.items():
        output[key] = sorted(
            candidates,
            key=lambda row: (
                0 if vector3(row.get("viewpoint_position")) is not None else 1,
                safe_float(row.get("standoff_score")) if safe_float(row.get("standoff_score")) is not None else 999999.0,
                safe_int(row.get("observation_index"), 999999),
            ),
        )[0]
    return output


def candidate_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    cid = candidate_id(row)
    position = vector3(row.get("target_position")) or vector3(row.get("position"))
    visit_position = vector3(row.get("target_visit_position")) or vector3(row.get("visit_position")) or position
    return {
        "candidate_id": cid,
        "category": row.get("query"),
        "candidate_role": row.get("target_candidate_role") or "target_candidate",
        "generated_rank": row.get("target_generated_rank"),
        "semantic_rank": row.get("target_semantic_rank"),
        "score": row.get("target_score"),
        "semantic_score": row.get("target_semantic_score"),
        "support_score": row.get("target_support_score"),
        "positive_support": row.get("target_positive_support"),
        "position": position,
        "visit_position": visit_position,
        "source": "prior_partial_relation_depth_plan_target_candidate",
        "uses_gt_for_action": False,
    }


def context_snapshot(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_id": str(row.get("context_candidate_id") or ""),
        "category": row.get("query"),
        "candidate_role": row.get("context_candidate_role"),
        "generated_rank": row.get("context_generated_rank"),
        "semantic_rank": row.get("context_generated_rank"),
        "score": None,
        "semantic_score": None,
        "support_score": None,
        "positive_support": None,
        "position": vector3(row.get("context_position")),
        "visit_position": vector3(row.get("context_visit_position")) or vector3(row.get("context_position")),
        "context_detector_visible_rows": safe_int(row.get("context_detector_visible_rows"), 0),
        "context_detector_associated_rows": safe_int(row.get("context_detector_associated_rows"), 0),
        "context_detector_inside_mask_rows": safe_int(row.get("context_detector_inside_mask_rows"), 0),
        "source": "prior_partial_relation_depth_context_anchor",
        "uses_gt_for_action": False,
    }


def context_rank(row: Dict[str, Any], target_id: str, primary_context_ids: Sequence[str]) -> Tuple[int, int, int, Tuple[int, str]]:
    context_id = str(row.get("context_candidate_id") or "")
    is_primary = context_id in set(primary_context_ids)
    is_rival = context_id != target_id
    return (
        0 if is_primary else (1 if is_rival else 2),
        -safe_int(row.get("context_detector_associated_rows"), 0),
        -safe_int(row.get("context_detector_visible_rows"), 0),
        source_suffix(context_id),
    )


def select_context_rows(
    rows: Sequence[Dict[str, Any]],
    target_id: str,
    primary_context_ids: Sequence[str],
    target_candidate_ids: Sequence[str],
    minimum: int = 3,
) -> List[Dict[str, Any]]:
    by_context: Dict[str, Dict[str, Any]] = {}
    for row in sorted(rows, key=lambda item: context_rank(item, target_id, primary_context_ids)):
        context_id = str(row.get("context_candidate_id") or "")
        if not context_id or context_id == target_id or context_id in by_context:
            continue
        by_context[context_id] = dict(row)

    selected: List[Dict[str, Any]] = []
    for context_id in primary_context_ids:
        if context_id in by_context:
            selected.append(by_context[context_id])

    rival = [cid for cid in target_candidate_ids if cid != target_id and cid in by_context]
    if rival:
        selected.append(by_context[rival[0]])

    for context_id in sorted(by_context.keys(), key=source_suffix):
        if len(selected) >= minimum:
            break
        if any(str(row.get("context_candidate_id")) == context_id for row in selected):
            continue
        selected.append(by_context[context_id])
    return selected[:minimum]


def build_request_output_rows(
    request_rows: Sequence[Dict[str, Any]],
    branch_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    by_request = group_by_key(branch_rows, request_id)
    output: List[Dict[str, Any]] = []
    for index, row in enumerate(request_rows):
        rid = request_id(row)
        rows = sorted(by_request.get(rid, []), key=row_sort_key)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_repeated_object_relation_anchor_consistency_request",
                "policy": POLICY_NAME,
                "planner_name": PLANNER_NAME,
                "contract_name": contract.get("contract_name"),
                "request_index": index,
                "expanded_retrieval_request_id": rid,
                "rival_identity_request_id": row.get("rival_identity_request_id") or rid,
                "episode_key": row.get("episode_key"),
                "scene_id": row.get("scene_id"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "source_branch_action": row.get("source_branch_action"),
                "source_request_residual_status": row.get("source_request_residual_status"),
                "branch_row_count": len(rows),
                "candidate_ids": unique_ordered(candidate_id(item) for item in rows),
                "prior_direction_counts": compact_counter(
                    row.get("prior_standoff_direction_source") for row in rows
                ),
                "source_residual_failure_class_counts": compact_counter(
                    row.get("source_residual_failure_class") for row in rows
                ),
                "relation_anchor_consistency_action": "request_relation_anchor_consistency_evidence",
                "request_status": "relation_anchor_consistency_materialized",
                "terminal_arbitration_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_candidate_rows(
    *,
    request_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
    branch_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    plan_by_pair = group_by_key(plan_rows, lambda row: (request_id(row), candidate_id(row)))
    branch_by_pair = group_by_key(branch_rows, lambda row: (request_id(row), candidate_id(row)))
    target_ids = expected_candidate_ids(contract)
    candidate_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []

    for request_index, request in enumerate(request_rows):
        rid = request_id(request)
        for candidate_index, cid in enumerate(target_ids):
            plans = sorted(plan_by_pair.get((rid, cid), []), key=row_sort_key)
            branches = sorted(branch_by_pair.get((rid, cid), []), key=row_sort_key)
            if not plans:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "validation_stage": "action_repeated_object_relation_anchor_consistency_skip",
                        "expanded_retrieval_request_id": rid,
                        "episode_key": request.get("episode_key"),
                        "scene_id": request.get("scene_id"),
                        "scene_key": request.get("scene_key"),
                        "query": request.get("query"),
                        "candidate_id": cid,
                        "skip_reason": "missing_prior_plan_rows_for_candidate",
                        "terminal_commit": False,
                        "uses_gt_for_action": False,
                    }
                )
                continue
            representative = dict(plans[0])
            branch_count = len(branches)
            snapshot = candidate_snapshot(representative)
            candidate_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_repeated_object_relation_anchor_consistency_candidate",
                    "policy": POLICY_NAME,
                    "planner_name": PLANNER_NAME,
                    "contract_name": contract.get("contract_name"),
                    "request_index": request_index,
                    "candidate_index": candidate_index,
                    "expanded_retrieval_request_id": rid,
                    "rival_identity_request_id": request.get("rival_identity_request_id") or rid,
                    "episode_key": request.get("episode_key"),
                    "scene_id": request.get("scene_id"),
                    "scene_key": request.get("scene_key"),
                    "query": request.get("query"),
                    "candidate_id": cid,
                    "target_candidate_id": cid,
                    "target_candidate_role": snapshot["candidate_role"],
                    "target_position": snapshot["position"],
                    "target_visit_position": snapshot["visit_position"],
                    "target_score": snapshot["score"],
                    "target_semantic_score": snapshot["semantic_score"],
                    "target_support_score": snapshot["support_score"],
                    "target_semantic_rank": snapshot["semantic_rank"],
                    "target_generated_rank": snapshot["generated_rank"],
                    "target_positive_support": snapshot["positive_support"],
                    "source_branch_row_count": branch_count,
                    "source_residual_failure_class_counts": compact_counter(
                        row.get("source_residual_failure_class") for row in branches
                    ),
                    "source_direction_counts": compact_counter(
                        row.get("prior_standoff_direction_source") for row in branches
                    ),
                    "relation_anchor_consistency_action": "materialize_candidate_anchor_consistency_pairs",
                    "terminal_arbitration_allowed": False,
                    "candidate_commit_allowed": False,
                    "candidate_rejection_allowed": False,
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )
    return candidate_rows, skipped_rows


def build_pair_rows(
    *,
    candidate_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    target_scope = contract.get("target_scope") or {}
    anchor_policy = target_scope.get("anchor_context_policy") or {}
    primary_context_ids = [str(value) for value in anchor_policy.get("primary_context_candidates") or []]
    target_ids = expected_candidate_ids(contract)
    gates = contract.get("evaluation_gates") or {}
    minimum_context_candidates_per_request = safe_int(gates.get("minimum_context_candidates_per_request"), 4)
    minimum_per_candidate = 3 if minimum_context_candidates_per_request >= 4 else 2
    context_by_pair = group_by_key(context_rows, lambda row: (request_id(row), candidate_id(row)))
    pair_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []

    for candidate in candidate_rows:
        rid = request_id(candidate)
        cid = candidate_id(candidate)
        selected = select_context_rows(
            context_by_pair.get((rid, cid), []),
            cid,
            primary_context_ids,
            target_ids,
            minimum=minimum_per_candidate,
        )
        if len(selected) < minimum_per_candidate:
            skipped_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_repeated_object_relation_anchor_consistency_skip",
                    "expanded_retrieval_request_id": rid,
                    "episode_key": candidate.get("episode_key"),
                    "scene_id": candidate.get("scene_id"),
                    "scene_key": candidate.get("scene_key"),
                    "query": candidate.get("query"),
                    "candidate_id": cid,
                    "skip_reason": "insufficient_prior_context_anchor_rows_for_candidate",
                    "available_context_rows": len(context_by_pair.get((rid, cid), [])),
                    "selected_context_rows": len(selected),
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                }
            )
            continue
        target_position = vector3(candidate.get("target_position"))
        for pair_index, context in enumerate(selected):
            context_id = str(context.get("context_candidate_id") or "")
            context_position = vector3(context.get("context_position"))
            pair_id = f"{rid}:{cid.rsplit(':', 1)[-1]}:{context_id.rsplit(':', 1)[-1]}"
            pair_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_repeated_object_relation_anchor_consistency_pair",
                    "policy": POLICY_NAME,
                    "planner_name": PLANNER_NAME,
                    "contract_name": contract.get("contract_name"),
                    "expanded_retrieval_request_id": rid,
                    "rival_identity_request_id": candidate.get("rival_identity_request_id") or rid,
                    "episode_key": candidate.get("episode_key"),
                    "scene_id": candidate.get("scene_id"),
                    "scene_key": candidate.get("scene_key"),
                    "query": candidate.get("query"),
                    "candidate_id": cid,
                    "target_candidate_id": cid,
                    "context_candidate_id": context_id,
                    "candidate_anchor_pair_id": pair_id,
                    "pair_index": pair_index,
                    "target_position": target_position,
                    "target_visit_position": vector3(candidate.get("target_visit_position")),
                    "context_position": context_position,
                    "context_visit_position": vector3(context.get("context_visit_position")),
                    "horizontal_distance_m": horizontal_distance(target_position, context_position),
                    "near_2m_proxy": bool(context.get("near_2m_proxy")),
                    "near_4m_proxy": bool(context.get("near_4m_proxy")),
                    "same_component_proxy": bool(context.get("same_component_proxy")),
                    "same_support_surface_proxy": bool(context.get("same_support_surface_proxy")),
                    "context_candidate_role": context.get("context_candidate_role"),
                    "context_detector_visible_rows": safe_int(context.get("context_detector_visible_rows"), 0),
                    "context_detector_associated_rows": safe_int(
                        context.get("context_detector_associated_rows"), 0
                    ),
                    "context_detector_inside_mask_rows": safe_int(
                        context.get("context_detector_inside_mask_rows"), 0
                    ),
                    "relation_anchor_pair_role": (
                        "primary_context_anchor"
                        if context_id in primary_context_ids
                        else "same_category_rival_anchor"
                    ),
                    "relation_anchor_consistency_action": "collect_relation_anchor_pair_evidence",
                    "terminal_arbitration_allowed": False,
                    "candidate_commit_allowed": False,
                    "candidate_rejection_allowed": False,
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )
    return sorted(pair_rows, key=row_sort_key), skipped_rows


def build_observation_rows(
    *,
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    plan_index: Dict[Tuple[str, str, str], Dict[str, Any]],
    contract: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    required_roles = list((contract.get("evidence_contract") or {}).get("observation_rule", {}).get("view_roles") or [])
    if not required_roles:
        required_roles = list(ROLE_TO_DIRECTION)
    pair_by_candidate = group_by_key(pair_rows, lambda row: (request_id(row), candidate_id(row)))
    observation_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []

    for candidate in candidate_rows:
        rid = request_id(candidate)
        cid = candidate_id(candidate)
        pairs = sorted(pair_by_candidate.get((rid, cid), []), key=lambda row: source_suffix(str(row.get("context_candidate_id") or "")))
        if not pairs:
            skipped_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_repeated_object_relation_anchor_consistency_skip",
                    "expanded_retrieval_request_id": rid,
                    "episode_key": candidate.get("episode_key"),
                    "scene_id": candidate.get("scene_id"),
                    "scene_key": candidate.get("scene_key"),
                    "query": candidate.get("query"),
                    "candidate_id": cid,
                    "skip_reason": "missing_candidate_anchor_pair_for_observation",
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                }
            )
            continue
        for role_index, role in enumerate(required_roles):
            requested_direction = ROLE_TO_DIRECTION.get(str(role), str(role))
            source_plan = plan_index.get((rid, cid, requested_direction))
            if source_plan is None:
                skipped_rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "validation_stage": "action_repeated_object_relation_anchor_consistency_skip",
                        "expanded_retrieval_request_id": rid,
                        "episode_key": candidate.get("episode_key"),
                        "scene_id": candidate.get("scene_id"),
                        "scene_key": candidate.get("scene_key"),
                        "query": candidate.get("query"),
                        "candidate_id": cid,
                        "observation_role": role,
                        "requested_direction_source": requested_direction,
                        "skip_reason": "missing_prior_plan_viewpoint_for_role",
                        "terminal_commit": False,
                        "uses_gt_for_action": False,
                    }
                )
                continue
            pair = pairs[role_index % len(pairs)]
            context_id = str(pair.get("context_candidate_id") or "")
            observation_index = len(observation_rows)
            observation_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_repeated_object_relation_anchor_consistency_observation_target",
                    "policy": POLICY_NAME,
                    "planner_name": PLANNER_NAME,
                    "contract_name": contract.get("contract_name"),
                    "expanded_retrieval_request_id": rid,
                    "rival_identity_request_id": candidate.get("rival_identity_request_id") or rid,
                    "episode_key": candidate.get("episode_key"),
                    "scene_id": candidate.get("scene_id"),
                    "scene_key": candidate.get("scene_key"),
                    "query": candidate.get("query"),
                    "candidate_id": cid,
                    "target_candidate_id": cid,
                    "context_candidate_id": context_id,
                    "candidate_anchor_pair_id": pair.get("candidate_anchor_pair_id"),
                    "candidate_ids": unique_ordered([cid, context_id]),
                    "relation_anchor_candidate_ids": unique_ordered([context_id]),
                    "observation_index": observation_index,
                    "observation_role": role,
                    "view_role": role,
                    "requested_direction_source": requested_direction,
                    "source_viewpoint_id": source_plan.get("viewpoint_id"),
                    "viewpoint_id": f"relation_anchor_consistency:{rid}:{cid.rsplit(':', 1)[-1]}:{role_index:02d}",
                    "viewpoint_policy": VIEWPOINT_POLICY,
                    "viewpoint_source": source_plan.get("viewpoint_source"),
                    "viewpoint_position": source_plan.get("viewpoint_position"),
                    "viewpoint_rotation": source_plan.get("viewpoint_rotation"),
                    "standoff_direction_source": source_plan.get("standoff_direction_source"),
                    "standoff_distance_requested": source_plan.get("standoff_distance_requested"),
                    "standoff_desired_position": source_plan.get("standoff_desired_position"),
                    "standoff_navmesh_navigable": source_plan.get("standoff_navmesh_navigable"),
                    "standoff_navmesh_snapped": source_plan.get("standoff_navmesh_snapped"),
                    "standoff_projection_sane": source_plan.get("standoff_projection_sane"),
                    "standoff_score": source_plan.get("standoff_score"),
                    "standoff_snap_distance": source_plan.get("standoff_snap_distance"),
                    "standoff_target_horizontal_distance": source_plan.get("standoff_target_horizontal_distance"),
                    "standoff_viewpoint_yaw_rad": source_plan.get("standoff_viewpoint_yaw_rad"),
                    "target_distance_from_viewpoint_m": source_plan.get("target_distance_from_viewpoint_m"),
                    "target_position": candidate.get("target_position"),
                    "target_visit_position": candidate.get("target_visit_position"),
                    "context_position": pair.get("context_position"),
                    "context_visit_position": pair.get("context_visit_position"),
                    "context_target_distance_m": pair.get("horizontal_distance_m"),
                    "revision_projection_anchor_policy": source_plan.get("revision_projection_anchor_policy"),
                    "revision_projection_anchor_height_offsets_m": source_plan.get(
                        "revision_projection_anchor_height_offsets_m"
                    ),
                    "revision_projection_anchor_source": source_plan.get("revision_projection_anchor_source"),
                    "revision_projection_anchor_label_free": source_plan.get(
                        "revision_projection_anchor_label_free"
                    ),
                    "relation_anchor_consistency_action": "collect_relation_anchor_consistency_evidence",
                    "commit_after_reobserve": False,
                    "terminal_arbitration_allowed": False,
                    "candidate_commit_allowed": False,
                    "candidate_rejection_allowed": False,
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )
    return sorted(observation_rows, key=row_sort_key), skipped_rows


def build_candidate_artifact_rows(
    *,
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    context_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
) -> List[Dict[str, Any]]:
    if not candidate_rows:
        return []
    snapshots: Dict[str, Dict[str, Any]] = {}
    for row in candidate_rows:
        cid = candidate_id(row)
        snapshots[cid] = {
            "candidate_id": cid,
            "category": row.get("query"),
            "candidate_role": row.get("target_candidate_role") or "target_candidate",
            "generated_rank": row.get("target_generated_rank"),
            "semantic_rank": row.get("target_semantic_rank"),
            "score": row.get("target_score"),
            "semantic_score": row.get("target_semantic_score"),
            "support_score": row.get("target_support_score"),
            "positive_support": row.get("target_positive_support"),
            "position": row.get("target_position"),
            "visit_position": row.get("target_visit_position"),
            "source": "relation_anchor_consistency_target_candidate",
            "uses_gt_for_action": False,
        }

    context_by_id: Dict[str, Dict[str, Any]] = {}
    for row in context_rows:
        context_id = str(row.get("context_candidate_id") or "")
        if context_id and context_id not in context_by_id:
            context_by_id[context_id] = context_snapshot(row)

    for row in pair_rows:
        context_id = str(row.get("context_candidate_id") or "")
        if context_id and context_id not in snapshots and context_id in context_by_id:
            snapshots[context_id] = context_by_id[context_id]

    first = dict(candidate_rows[0])
    return [
        {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "action_repeated_object_relation_anchor_consistency_candidate_artifact",
            "policy": POLICY_NAME,
            "planner_name": PLANNER_NAME,
            "contract_name": contract.get("contract_name"),
            "scene_id": first.get("scene_id"),
            "scene_key": first.get("scene_key"),
            "query": first.get("query"),
            "candidate_ids": sorted(snapshots.keys(), key=source_suffix),
            "candidates": [snapshots[cid] for cid in sorted(snapshots.keys(), key=source_suffix)],
            "terminal_commit": False,
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        }
    ]


def forbidden_findings(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def count_boolean_rows(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return sum(1 for row in rows if bool(row.get(key)))


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    out_root = Path(args.out_root)

    promotion_summary = load_json(source_path(args, contract, "promotion_requirement_summary", "promotion_requirement_summary"))
    branch_summary = load_json(source_path(args, contract, "branch_summary", "branch_summary"))
    branch_rows = target_branch_rows(load_jsonl(source_path(args, contract, "branch_rows", "branch_rows")), contract)
    request_rows = target_request_rows(
        load_jsonl(source_path(args, contract, "branch_request_rows", "branch_request_rows")),
        contract,
    )
    context_rows = prior_context_rows(
        load_jsonl(source_path(args, contract, "prior_context_anchor_rows", "prior_context_anchor_rows")),
        contract,
    )
    plan_rows = prior_plan_rows(load_jsonl(Path(args.prior_plan)), contract)

    request_output_rows = build_request_output_rows(request_rows, branch_rows, contract)
    candidate_rows, candidate_skips = build_candidate_rows(
        request_rows=request_rows,
        plan_rows=plan_rows,
        branch_rows=branch_rows,
        contract=contract,
    )
    pair_rows, pair_skips = build_pair_rows(
        candidate_rows=candidate_rows,
        context_rows=context_rows,
        contract=contract,
    )
    observation_rows, observation_skips = build_observation_rows(
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        plan_index=best_plan_index(plan_rows),
        contract=contract,
    )
    candidate_artifact_rows = build_candidate_artifact_rows(
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        context_rows=context_rows,
        contract=contract,
    )
    skipped_rows = sorted(candidate_skips + pair_skips + observation_skips, key=row_sort_key)

    required_outputs = contract.get("required_outputs") or {}
    output_paths = {
        "request_rows": out_root / str(required_outputs.get("request_rows")),
        "candidate_rows": out_root / str(required_outputs.get("candidate_rows")),
        "pair_rows": out_root / str(required_outputs.get("pair_rows")),
        "observation_targets": out_root / str(required_outputs.get("observation_targets")),
        "candidate_artifact": out_root / str(required_outputs.get("candidate_artifact")),
        "skipped_rows": out_root / str(required_outputs.get("skipped_rows")),
        "summary": out_root / str(required_outputs.get("summary")),
    }

    action_rows = request_output_rows + candidate_rows + pair_rows + observation_rows + candidate_artifact_rows + skipped_rows
    forbidden = forbidden_findings(action_rows)
    view_role_counts = compact_counter(row.get("observation_role") for row in observation_rows)
    observation_roles_by_candidate = group_by_key(
        observation_rows, lambda row: (request_id(row), candidate_id(row))
    )
    context_candidates_by_request = {
        rid: sorted({str(row.get("context_candidate_id") or "") for row in rows if row.get("context_candidate_id")}, key=source_suffix)
        for rid, rows in group_by_key(pair_rows, request_id).items()
    }
    minimum_context_candidates_per_request = min(
        (len(values) for values in context_candidates_by_request.values()),
        default=0,
    )
    minimum_observation_roles_per_candidate = min(
        (len({str(row.get("observation_role") or "") for row in rows}) for rows in observation_roles_by_candidate.values()),
        default=0,
    )
    candidate_rows_per_request = compact_counter(request_id(row) for row in candidate_rows)
    terminal_commit_rows = count_boolean_rows(action_rows, "terminal_commit")
    candidate_commit_rows = count_boolean_rows(action_rows, "candidate_commit_allowed")
    candidate_rejection_rows = count_boolean_rows(action_rows, "candidate_rejection_allowed")
    uses_gt_for_action = any(bool(row.get("uses_gt_for_action")) for row in action_rows)

    gates = contract.get("evaluation_gates") or {}
    gate = {
        "promotion_requirement_gate_passed": bool(
            (promotion_summary.get("gate") or {}).get("promotion_requirement_gate_passed")
            or (promotion_summary.get("gate") or {}).get("residual_branch_promotion_requirement_gate_passed")
        ),
        "source_branch_gate_passed": bool(
            (branch_summary.get("gate") or {}).get("repeated_object_relation_anchor_ambiguity_branch_gate_passed")
        ),
        "expected_request_rows_passed": len(request_output_rows) == safe_int(gates.get("expected_request_rows"), 3),
        "expected_candidate_rows_passed": len(candidate_rows) == safe_int(gates.get("expected_candidate_rows"), 9),
        "minimum_candidate_anchor_pair_rows_passed": len(pair_rows)
        >= safe_int(gates.get("minimum_candidate_anchor_pair_rows"), 18),
        "minimum_observation_target_rows_passed": len(observation_rows)
        >= safe_int(gates.get("minimum_observation_target_rows"), 27),
        "minimum_observation_roles_per_candidate_passed": minimum_observation_roles_per_candidate
        >= safe_int(gates.get("minimum_observation_roles_per_candidate"), 3),
        "minimum_context_candidates_per_request_passed": minimum_context_candidates_per_request
        >= safe_int(gates.get("minimum_context_candidates_per_request"), 4),
        "skipped_request_rows_passed": len(skipped_rows) <= safe_int(gates.get("skipped_request_rows_maximum"), 0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": terminal_commit_rows
        <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "candidate_commit_rows_passed": candidate_commit_rows
        <= safe_int(gates.get("candidate_commit_rows_maximum"), 0),
        "candidate_rejection_rows_passed": candidate_rejection_rows
        <= safe_int(gates.get("candidate_rejection_rows_maximum"), 0),
        "uses_gt_for_action_passed": uses_gt_for_action == bool(gates.get("uses_gt_for_action", False)),
    }
    gate["repeated_object_relation_anchor_consistency_plan_gate_passed"] = all(gate.values())

    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "prior_plan": str(args.prior_plan),
        "out_root": str(out_root),
        "output_files": {name: str(path) for name, path in output_paths.items()},
        "source_rows": {
            "branch_rows": len(branch_rows),
            "request_rows": len(request_rows),
            "prior_context_anchor_rows": len(context_rows),
            "prior_plan_rows": len(plan_rows),
        },
        "request_rows": len(request_output_rows),
        "candidate_rows": len(candidate_rows),
        "candidate_anchor_pair_rows": len(pair_rows),
        "observation_target_rows": len(observation_rows),
        "candidate_artifact_rows": len(candidate_artifact_rows),
        "candidate_artifact_candidate_count": sum(
            len(row.get("candidate_ids") or []) for row in candidate_artifact_rows
        ),
        "skipped_rows": len(skipped_rows),
        "request_ids": unique_ordered(request_id(row) for row in request_output_rows),
        "candidate_ids": unique_ordered(candidate_id(row) for row in candidate_rows),
        "context_candidate_ids": unique_ordered(row.get("context_candidate_id") for row in pair_rows),
        "context_candidate_ids_per_request": context_candidates_by_request,
        "view_role_counts": view_role_counts,
        "candidate_rows_per_request": candidate_rows_per_request,
        "minimum_observation_roles_per_candidate": minimum_observation_roles_per_candidate,
        "minimum_context_candidates_per_request": minimum_context_candidates_per_request,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": uses_gt_for_action,
        "paper_claim_allowed": False,
        "terminal_utility_validation_allowed": False,
        "candidate_commit_or_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "next_allowed_task": "run_repeated_object_relation_anchor_consistency_frame_projection_smoke",
        "gate": gate,
    }

    write_jsonl(output_paths["request_rows"], request_output_rows)
    write_jsonl(output_paths["candidate_rows"], candidate_rows)
    write_jsonl(output_paths["pair_rows"], pair_rows)
    write_jsonl(output_paths["observation_targets"], observation_rows)
    write_jsonl(output_paths["candidate_artifact"], candidate_artifact_rows)
    write_jsonl(output_paths["skipped_rows"], skipped_rows)
    write_json(output_paths["summary"], summary)
    return summary


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Materialize repeated-object relation-anchor consistency evidence targets."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--prior-plan", default=PRIOR_PLAN_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--promotion-requirement-summary", default=None)
    parser.add_argument("--branch-summary", default=None)
    parser.add_argument("--branch-rows", default=None)
    parser.add_argument("--branch-request-rows", default=None)
    parser.add_argument("--prior-context-anchor-rows", default=None)
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if (summary.get("gate") or {}).get("repeated_object_relation_anchor_consistency_plan_gate_passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
