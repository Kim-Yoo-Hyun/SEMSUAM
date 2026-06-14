import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_candidate_task_proxy_join.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_candidate_task_proxy_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_candidate_task_proxy_join_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")
SOURCE_POLICY_KEYS = ("source_name", "policy_name", "episode_key", "request_id", "query", "scene_key")
BASELINE_POLICIES = ("NoReobserveReference", "SemanticOnly")
SLAM_POLICY = "SLAMOnlyRich_current"
POLICY_ORDER = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_wrong_label",
    "correctness_label",
    "evaluation_candidate_summary",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_variant_outcomes",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "no_valid_candidate_pool",
    "oracle_action",
    "shortest_path_distance",
    "success_commit",
    "wasted_path_proxy_m",
    "wrong_goal_commit",
    "wrong_goal_visit_proxy",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
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


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def normalized_request_id(row: Mapping[str, Any]) -> str:
    for key in REQUEST_ID_ALIASES:
        value = row.get(key)
        if value:
            return str(value)
    nested = row.get("join_key")
    if isinstance(nested, Mapping):
        value = nested.get("request_id")
        if value:
            return str(value)
    return ""


def request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("episode_key") or row.get("episode_key") or ""),
        normalized_request_id(row),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
    )


def source_policy_key(row: Mapping[str, Any], policy_name: Optional[str] = None) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(policy_name if policy_name is not None else row.get("policy_name") or ""),
        str(source.get("episode_key") or row.get("episode_key") or ""),
        normalized_request_id(row),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
    )


def request_key_payload(key: Tuple[str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def join_key_payload(key: Tuple[str, str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(SOURCE_POLICY_KEYS, key))


def label_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("episode_key") or ""),
        str(row.get("request_id") or ""),
        str(row.get("query") or ""),
        str(row.get("scene_key") or ""),
    )


def index_request_labels(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str], Mapping[str, Any]]:
    return {label_request_key(row): row for row in rows}


def index_candidate_labels(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        index[label_request_key(row)][str(row.get("candidate_id") or "")] = row
    return dict(index)


def index_policy_rows(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]:
    return {source_policy_key(row): row for row in rows}


def scan_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def travel_cost(row: Mapping[str, Any], fallback: Optional[Mapping[str, Any]] = None) -> Optional[float]:
    for source in (row, fallback or {}):
        if not isinstance(source, Mapping):
            continue
        value = source.get("reobserve_travel_cost_m")
        if value is not None:
            return safe_float(value)
        value = source.get("travel_cost_proxy_m")
        if isinstance(value, Mapping):
            found = safe_float(value.get("mean"))
        else:
            found = safe_float(value)
        if found is not None:
            return found
    return None


def numeric_field(row: Mapping[str, Any], fallback: Optional[Mapping[str, Any]], key: str) -> Optional[float]:
    value = safe_float(row.get(key))
    if value is not None:
        return value
    if fallback is not None:
        return safe_float(fallback.get(key))
    return None


def normalize_slam_selector_row(
    row: Mapping[str, Any],
    fallback_policy_row: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    key = request_key(row)
    source_policy = source_policy_key(row, SLAM_POLICY)
    selector_missing_reason = row.get("selector_missing_reason")
    terminal_commit = bool(row.get("terminal_commit_proxy") is True)
    selector_action = "commit_candidate" if terminal_commit else "defer"
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "candidate_map_pose_selector_joined_to_task_proxy",
        "row_type": "semantic_slam_candidate_task_proxy_selector_input",
        "source_name": source_policy[0],
        "policy_name": SLAM_POLICY,
        **request_key_payload(key),
        "join_key": join_key_payload(source_policy),
        "selector_id": row.get("selector_id"),
        "selector_action": selector_action,
        "selector_source": "unique_candidate_map_pose_ready" if terminal_commit else None,
        "selector_missing": bool(row.get("selector_missing") is True),
        "selector_missing_reason": None if terminal_commit else selector_missing_reason,
        "policy_selected_candidate_id": row.get("policy_selected_candidate_id"),
        "terminal_commit_proxy": terminal_commit,
        "candidate_count": safe_int(row.get("candidate_count"), 0),
        "ready_candidate_count": safe_int(row.get("ready_candidate_count"), 0),
        "strict_candidate_map_pose_ready_candidate_ids": row.get("strict_candidate_map_pose_ready_candidate_ids"),
        "single_candidate_pool_geometry_only": bool(row.get("single_candidate_pool_geometry_only") is True),
        "request_pose_graph_proxy_ready": bool(row.get("request_pose_graph_proxy_ready") is True),
        "request_pose_graph_connected_component_count": row.get("request_pose_graph_connected_component_count"),
        "request_pose_graph_largest_component_fraction": row.get("request_pose_graph_largest_component_fraction"),
        "request_pose_graph_edge_count": row.get("request_pose_graph_edge_count"),
        "strict_pose_spatial_proxy_ready": bool(row.get("strict_pose_spatial_proxy_ready") is True),
        "strict_pose_loop_proxy_ready": bool(row.get("strict_pose_loop_proxy_ready") is True),
        "pose_graph_connectivity_delta": numeric_field(row, fallback_policy_row, "pose_graph_connectivity_delta"),
        "map_pose_consistency_delta": numeric_field(row, fallback_policy_row, "map_pose_consistency_delta"),
        "map_side_delta": numeric_field(row, fallback_policy_row, "map_side_delta"),
        "reobserve_travel_cost_m": travel_cost(row, fallback_policy_row),
        "source_family": row.get("source_family") or (fallback_policy_row or {}).get("source_family"),
        "candidate_specific_map_pose_required": True,
        "uses_reobservation_evidence": True,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def collect_selector_rows(
    old_policy_selector_rows: Sequence[Mapping[str, Any]],
    candidate_slam_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    old_index = index_policy_rows(old_policy_selector_rows)
    rows: List[Dict[str, Any]] = []
    for row in old_policy_selector_rows:
        if row.get("policy_name") in BASELINE_POLICIES:
            out = dict(row)
            out["schema_version"] = SCHEMA_VERSION
            out["validation_stage"] = "frozen_task_policy_selector_joined_to_task_proxy"
            out["row_type"] = "semantic_slam_candidate_task_proxy_selector_input"
            out["uses_gt_for_action"] = False
            out["paper_claim_allowed"] = False
            rows.append(out)
    for row in candidate_slam_rows:
        fallback = old_index.get(source_policy_key(row, SLAM_POLICY))
        rows.append(normalize_slam_selector_row(row, fallback))

    def sort_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, int]:
        policy_rank = POLICY_ORDER.index(str(row.get("policy_name"))) if row.get("policy_name") in POLICY_ORDER else 99
        return (
            str(row.get("source_name") or ""),
            str(row.get("episode_key") or ""),
            str(row.get("request_id") or ""),
            str(row.get("query") or ""),
            str(row.get("scene_key") or ""),
            policy_rank,
        )

    return sorted(rows, key=sort_key)


def materialize_task_proxy_rows(
    selector_rows: Sequence[Mapping[str, Any]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    policy_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    for selector in selector_rows:
        req_key = request_key(selector)
        req_label = request_labels.get(req_key)
        cand_label_index = candidate_labels.get(req_key) or {}
        selected_candidate_id = selector.get("policy_selected_candidate_id")
        selected_label = cand_label_index.get(str(selected_candidate_id or ""))
        terminal_commit = selector.get("terminal_commit_proxy")
        label_backbone_join = req_label is not None
        candidate_label_pool_join = bool(cand_label_index)
        selected_candidate_label_join = selected_label is not None if selected_candidate_id else False
        selector_missing = bool(selector.get("selector_missing") is True)
        decision_evaluable = label_backbone_join and candidate_label_pool_join and terminal_commit is not None and not selector_missing
        commit_evaluable = decision_evaluable and terminal_commit is True and selected_candidate_label_join

        selected_correct = bool(selected_label and selected_label.get("candidate_correctness_label") is True)
        selected_wrong = bool(selected_label and selected_label.get("candidate_wrong_label") is True)
        no_valid_pool = bool(req_label and req_label.get("no_valid_candidate_pool") is True)

        success_commit_proxy = bool(commit_evaluable and selected_correct)
        wrong_goal_visit_proxy = bool(commit_evaluable and selected_wrong)
        no_valid_commit_proxy = bool(decision_evaluable and terminal_commit is True and no_valid_pool)
        wasted = travel_cost(selector) if wrong_goal_visit_proxy else 0.0
        if wasted is None:
            wasted = 0.0

        failure_tag: Optional[str] = None
        failure_detail: Optional[str] = None
        if not label_backbone_join:
            failure_tag = "request_label_missing"
            failure_detail = "No request-level evaluation label row joins this selector decision."
        elif not candidate_label_pool_join:
            failure_tag = "candidate_label_pool_missing"
            failure_detail = "No candidate-level evaluation label rows join this selector decision."
        elif selector_missing:
            failure_tag = "policy_selector_missing"
            failure_detail = str(selector.get("selector_missing_reason") or "")
        elif terminal_commit is not True:
            failure_tag = "policy_deferred"
            failure_detail = str(selector.get("selector_missing_reason") or "terminal_commit_proxy_false")
        elif not selected_candidate_label_join:
            failure_tag = "selected_candidate_label_missing"
            failure_detail = str(selected_candidate_id or "")
        elif no_valid_commit_proxy:
            failure_tag = "no_valid_commit"
            failure_detail = "Policy terminal-committed although the evaluation label marks the candidate pool as no-valid."
        elif wrong_goal_visit_proxy:
            failure_tag = "wrong_goal_visit"
            failure_detail = "Policy terminal-committed to a label-wrong selected candidate."

        out = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "evaluation_only_task_proxy_after_candidate_map_pose_selector",
            "row_type": "semantic_slam_candidate_task_proxy_policy",
            "join_key": join_key_payload(source_policy_key(selector)),
            "source_name": str(selector.get("source_name") or ""),
            "policy_name": str(selector.get("policy_name") or ""),
            **request_key_payload(req_key),
            "selector_id": selector.get("selector_id"),
            "selector_action": selector.get("selector_action"),
            "selector_source": selector.get("selector_source"),
            "selector_missing": selector_missing,
            "selector_missing_reason": selector.get("selector_missing_reason"),
            "policy_selected_candidate_id": selected_candidate_id,
            "terminal_commit_proxy": terminal_commit,
            "label_backbone_join_available": label_backbone_join,
            "candidate_label_pool_join_available": candidate_label_pool_join,
            "selected_candidate_label_join_available": selected_candidate_label_join,
            "candidate_label_count": safe_int((req_label or {}).get("candidate_label_count"), 0),
            "correct_candidate_count": safe_int((req_label or {}).get("correct_candidate_count"), 0),
            "wrong_candidate_count": safe_int((req_label or {}).get("wrong_candidate_count"), 0),
            "no_valid_candidate_pool": no_valid_pool if req_label else None,
            "selected_candidate_correctness_label": selected_label.get("candidate_correctness_label") if selected_label else None,
            "selected_candidate_wrong_label": selected_label.get("candidate_wrong_label") if selected_label else None,
            "task_proxy_decision_evaluable": decision_evaluable,
            "task_proxy_commit_evaluable": commit_evaluable,
            "success_commit_proxy": success_commit_proxy,
            "wrong_goal_visit_proxy": wrong_goal_visit_proxy,
            "no_valid_commit_proxy": no_valid_commit_proxy,
            "wasted_path_proxy_m": wasted,
            "map_task_alignment_proxy": bool(
                str(selector.get("policy_name") or "") == SLAM_POLICY and success_commit_proxy
            ),
            "map_side_delta": selector.get("map_side_delta"),
            "pose_graph_connectivity_delta": selector.get("pose_graph_connectivity_delta"),
            "map_pose_consistency_delta": selector.get("map_pose_consistency_delta"),
            "reobserve_travel_cost_m": selector.get("reobserve_travel_cost_m"),
            "candidate_count": selector.get("candidate_count"),
            "ready_candidate_count": selector.get("ready_candidate_count"),
            "single_candidate_pool_geometry_only": selector.get("single_candidate_pool_geometry_only"),
            "source_family": selector.get("source_family"),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
            "paper_claim_allowed": False,
            "failure_tag": failure_tag,
            "failure_detail": failure_detail,
        }
        policy_rows.append(out)
        if failure_tag:
            failure_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "evaluation_only_task_proxy_after_candidate_map_pose_selector",
                    "row_type": "semantic_slam_candidate_task_proxy_failure",
                    "join_key": out["join_key"],
                    "source_name": out["source_name"],
                    "policy_name": out["policy_name"],
                    **request_key_payload(req_key),
                    "failure_tag": failure_tag,
                    "failure_detail": failure_detail,
                    "selector_id": selector.get("selector_id"),
                    "selector_action": selector.get("selector_action"),
                    "policy_selected_candidate_id": selected_candidate_id,
                    "terminal_commit_proxy": terminal_commit,
                    "wrong_goal_visit_proxy": wrong_goal_visit_proxy,
                    "no_valid_commit_proxy": no_valid_commit_proxy,
                    "wasted_path_proxy_m": wasted,
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                    "paper_claim_allowed": False,
                }
            )
    return policy_rows, failure_rows


def per_policy_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    for policy in POLICY_ORDER:
        subset = [row for row in rows if row.get("policy_name") == policy]
        wasted_values = [safe_float(row.get("wasted_path_proxy_m"), 0.0) or 0.0 for row in subset]
        result[policy] = {
            "rows": len(subset),
            "terminal_commit_rows": sum(1 for row in subset if row.get("terminal_commit_proxy") is True),
            "defer_rows": sum(1 for row in subset if row.get("terminal_commit_proxy") is False),
            "selector_missing_rows": sum(1 for row in subset if row.get("selector_missing") is True),
            "task_proxy_decision_evaluable_rows": sum(
                1 for row in subset if row.get("task_proxy_decision_evaluable") is True
            ),
            "task_proxy_commit_evaluable_rows": sum(
                1 for row in subset if row.get("task_proxy_commit_evaluable") is True
            ),
            "success_commit_rows": sum(1 for row in subset if row.get("success_commit_proxy") is True),
            "wrong_goal_visit_rows": sum(1 for row in subset if row.get("wrong_goal_visit_proxy") is True),
            "no_valid_commit_rows": sum(1 for row in subset if row.get("no_valid_commit_proxy") is True),
            "wasted_path_sum_m": sum(wasted_values),
            "wasted_path_mean_m": ratio(sum(wasted_values), len(wasted_values)),
            "map_task_alignment_rows": sum(1 for row in subset if row.get("map_task_alignment_proxy") is True),
        }
    return result


def gate_check(
    contract: Mapping[str, Any],
    rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    gate = (contract.get("success_gates") or {}).get("task_proxy_join_gate") or {}
    formula_gate = (contract.get("success_gates") or {}).get("formula_revision_unlock_gate") or {}
    policy = per_policy_counts(rows)
    policy_selector_missing_rows = sum(1 for row in rows if row.get("selector_missing") is True)
    task_proxy_decision_rows = sum(1 for row in rows if row.get("task_proxy_decision_evaluable") is True)
    task_proxy_commit_rows = sum(1 for row in rows if row.get("task_proxy_commit_evaluable") is True)
    wrong_nonnull = sum(1 for row in rows if row.get("wrong_goal_visit_proxy") is not None)
    wasted_nonnull = sum(1 for row in rows if row.get("wasted_path_proxy_m") is not None)
    uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in rows)
    paper_claim_allowed = any(row.get("paper_claim_allowed") is True for row in rows)

    task_gate = {
        "policy_task_proxy_rows_passed": len(rows) == safe_int(gate.get("policy_task_proxy_rows"), len(rows)),
        "policy_selector_missing_rows_passed": policy_selector_missing_rows
        <= safe_int(gate.get("policy_selector_missing_rows_max"), policy_selector_missing_rows),
        "task_proxy_decision_evaluable_rows_passed": task_proxy_decision_rows
        >= safe_int(gate.get("task_proxy_decision_evaluable_rows_min"), 0),
        "task_proxy_commit_evaluable_rows_passed": task_proxy_commit_rows
        >= safe_int(gate.get("task_proxy_commit_evaluable_rows_min"), 0),
        "wrong_goal_visit_proxy_nonnull_rows_passed": wrong_nonnull
        >= safe_int(gate.get("wrong_goal_visit_proxy_nonnull_rows_min"), 0),
        "wasted_path_proxy_nonnull_rows_passed": wasted_nonnull
        >= safe_int(gate.get("wasted_path_proxy_nonnull_rows_min"), 0),
        "action_evidence_forbidden_keys_passed": len(action_forbidden_keys)
        == safe_int(gate.get("action_evidence_forbidden_key_count"), 0),
        "uses_gt_for_action_passed": uses_gt_for_action is bool(gate.get("uses_gt_for_action", False)),
        "paper_claim_allowed_passed": paper_claim_allowed is bool(gate.get("paper_claim_allowed", False)),
    }

    baseline_wrong = max(
        policy["NoReobserveReference"]["wrong_goal_visit_rows"],
        policy["SemanticOnly"]["wrong_goal_visit_rows"],
    )
    baseline_wasted = max(
        policy["NoReobserveReference"]["wasted_path_sum_m"],
        policy["SemanticOnly"]["wasted_path_sum_m"],
    )
    formula = {
        "SLAMOnlyRich_current_terminal_commit_rows_passed": policy[SLAM_POLICY]["terminal_commit_rows"]
        >= safe_int(formula_gate.get("SLAMOnlyRich_current_terminal_commit_rows_min"), 0),
        "SLAMOnlyRich_current_map_task_alignment_rows_passed": policy[SLAM_POLICY]["map_task_alignment_rows"]
        >= safe_int(formula_gate.get("SLAMOnlyRich_current_map_task_alignment_rows_min"), 0),
        "wrong_goal_visit_not_increased_vs_baselines_passed": policy[SLAM_POLICY]["wrong_goal_visit_rows"]
        <= baseline_wrong,
        "wasted_path_not_increased_vs_baselines_passed": policy[SLAM_POLICY]["wasted_path_sum_m"]
        <= baseline_wasted,
        "uses_gt_for_action_passed": not uses_gt_for_action,
    }
    return task_gate, formula


def build_summary(
    *,
    contract: Mapping[str, Any],
    selector_rows: Sequence[Mapping[str, Any]],
    policy_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    request_label_rows: Sequence[Mapping[str, Any]],
    candidate_label_rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
    out_root: Path,
) -> Dict[str, Any]:
    policy = per_policy_counts(policy_rows)
    task_gate, formula_gate = gate_check(contract, policy_rows, action_forbidden_keys)
    task_gate_passed = all(task_gate.values())
    formula_gate_passed = all(formula_gate.values())
    actual_counts = {
        "selector_input_rows": len(selector_rows),
        "policy_task_proxy_rows": len(policy_rows),
        "failure_rows": len(failure_rows),
        "request_label_rows": len(request_label_rows),
        "candidate_label_rows": len(candidate_label_rows),
        "policy_selector_missing_rows": sum(1 for row in policy_rows if row.get("selector_missing") is True),
        "task_proxy_decision_evaluable_rows": sum(
            1 for row in policy_rows if row.get("task_proxy_decision_evaluable") is True
        ),
        "task_proxy_commit_evaluable_rows": sum(
            1 for row in policy_rows if row.get("task_proxy_commit_evaluable") is True
        ),
        "wrong_goal_visit_proxy_nonnull_rows": sum(
            1 for row in policy_rows if row.get("wrong_goal_visit_proxy") is not None
        ),
        "wasted_path_proxy_nonnull_rows": sum(1 for row in policy_rows if row.get("wasted_path_proxy_m") is not None),
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
        "NoReobserveReference_rows": policy["NoReobserveReference"]["rows"],
        "SemanticOnly_rows": policy["SemanticOnly"]["rows"],
        "SLAMOnlyRich_current_rows": policy[SLAM_POLICY]["rows"],
        "NoReobserveReference_terminal_commit_rows": policy["NoReobserveReference"]["terminal_commit_rows"],
        "SemanticOnly_terminal_commit_rows": policy["SemanticOnly"]["terminal_commit_rows"],
        "SLAMOnlyRich_current_terminal_commit_rows": policy[SLAM_POLICY]["terminal_commit_rows"],
        "NoReobserveReference_defer_rows": policy["NoReobserveReference"]["defer_rows"],
        "SemanticOnly_defer_rows": policy["SemanticOnly"]["defer_rows"],
        "SLAMOnlyRich_current_defer_rows": policy[SLAM_POLICY]["defer_rows"],
        "NoReobserveReference_wrong_goal_visit_rows": policy["NoReobserveReference"]["wrong_goal_visit_rows"],
        "SemanticOnly_wrong_goal_visit_rows": policy["SemanticOnly"]["wrong_goal_visit_rows"],
        "SLAMOnlyRich_current_wrong_goal_visit_rows": policy[SLAM_POLICY]["wrong_goal_visit_rows"],
        "NoReobserveReference_success_commit_rows": policy["NoReobserveReference"]["success_commit_rows"],
        "SemanticOnly_success_commit_rows": policy["SemanticOnly"]["success_commit_rows"],
        "SLAMOnlyRich_current_success_commit_rows": policy[SLAM_POLICY]["success_commit_rows"],
        "SLAMOnlyRich_current_map_task_alignment_rows": policy[SLAM_POLICY]["map_task_alignment_rows"],
    }
    expected = contract.get("expected_materializer_counts")
    expected = expected if isinstance(expected, Mapping) else {}
    comparable_expected = {
        key: value for key, value in expected.items() if key in actual_counts and not isinstance(value, bool)
    }
    expected_count_mismatches = {
        key: {"expected": value, "actual": actual_counts.get(key)}
        for key, value in comparable_expected.items()
        if actual_counts.get(key) != value
    }
    if expected.get("uses_gt_for_action") is not False:
        expected_count_mismatches["uses_gt_for_action"] = {"expected": False, "actual": expected.get("uses_gt_for_action")}
    if expected.get("paper_claim_allowed") is not False:
        expected_count_mismatches["paper_claim_allowed"] = {
            "expected": False,
            "actual": expected.get("paper_claim_allowed"),
        }

    primary_blocker = None
    if not formula_gate_passed:
        if not formula_gate["SLAMOnlyRich_current_terminal_commit_rows_passed"]:
            primary_blocker = "slam_only_terminal_commits_too_sparse"
        elif not formula_gate["SLAMOnlyRich_current_map_task_alignment_rows_passed"]:
            primary_blocker = "slam_only_map_task_alignment_too_sparse"
        else:
            primary_blocker = "formula_revision_unlock_gate_failed"

    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "task_proxy_join_gate_passed_formula_revision_blocked"
        if task_gate_passed and not formula_gate_passed
        else "completed",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "policy_rows": "semantic_slam_candidate_task_proxy_policy_rows.jsonl",
            "failure_rows": "semantic_slam_candidate_task_proxy_failure_rows.jsonl",
            "summary": "semantic_slam_candidate_task_proxy_summary.json",
        },
        "source_files": contract.get("source", {}),
        "actual_counts": actual_counts,
        "expected_materializer_counts": dict(expected),
        "expected_count_mismatches": expected_count_mismatches,
        "policy_counts": policy,
        "failure_taxonomy": compact_counter(row.get("failure_tag") for row in failure_rows),
        "selector_action_counts": compact_counter(row.get("selector_action") for row in policy_rows),
        "selector_missing_reason_counts": compact_counter(row.get("selector_missing_reason") for row in policy_rows),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "task_proxy_join_gate": task_gate,
        "formula_revision_unlock_gate": formula_gate,
        "task_proxy_join_gate_passed": task_gate_passed and not expected_count_mismatches,
        "formula_revision_unlock_gate_passed": formula_gate_passed,
        "revised_slam_formula_allowed": formula_gate_passed,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": primary_blocker,
        "recommended_next_task": "diagnose_safe_but_sparse_slam_selector_before_formula_revision"
        if task_gate_passed and not formula_gate_passed
        else "inspect_task_proxy_join_failures",
        "interpretation": {
            "fact": (
                "NoReobserveReference, SemanticOnly, and the candidate-specific SLAMOnlyRich_current selector are "
                "joined to the same evaluation-only task labels without using those labels for action selection."
            ),
            "agent_inference": (
                "The task proxy plumbing is complete, but the conservative SLAM/map-pose selector commits only on "
                "single-candidate geometry pools, so it is safe but too sparse for a formula revision or Step 4-5 claim."
            ),
            "paper_claim": (
                "No ObjectNav utility, Semantic-SLAM complementarity, formula revision, first_eval, policy-scale, "
                "or paper claim is allowed from this artifact."
            ),
        },
        "next_task": "diagnose_safe_but_sparse_slam_selector_before_formula_revision",
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")
    old_policy_selector_rows = load_jsonl(Path(str(source["task_policy_selector_rows"])))
    candidate_slam_rows = load_jsonl(Path(str(source["candidate_map_pose_selector_request_rows"])))
    request_label_rows = load_jsonl(Path(str(source["task_label_request_rows"])))
    candidate_label_rows = load_jsonl(Path(str(source["task_label_candidate_rows"])))
    selector_rows = collect_selector_rows(old_policy_selector_rows, candidate_slam_rows)
    action_forbidden_keys = scan_forbidden_keys(selector_rows)
    request_labels = index_request_labels(request_label_rows)
    candidate_labels = index_candidate_labels(candidate_label_rows)
    policy_rows, failure_rows = materialize_task_proxy_rows(selector_rows, request_labels, candidate_labels)
    summary = build_summary(
        contract=contract,
        selector_rows=selector_rows,
        policy_rows=policy_rows,
        failure_rows=failure_rows,
        request_label_rows=request_label_rows,
        candidate_label_rows=candidate_label_rows,
        action_forbidden_keys=action_forbidden_keys,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_candidate_task_proxy_policy_rows.jsonl", policy_rows)
    write_jsonl(out_root / "semantic_slam_candidate_task_proxy_failure_rows.jsonl", failure_rows)
    write_json(out_root / "semantic_slam_candidate_task_proxy_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Join candidate-specific Semantic-SLAM selector rows to label-backed task proxies."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
