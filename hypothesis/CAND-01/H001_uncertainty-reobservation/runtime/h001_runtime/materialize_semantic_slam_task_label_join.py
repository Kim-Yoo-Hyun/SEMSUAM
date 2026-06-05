import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_task_label_join.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_task_label_join_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_task_label_join_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")
SOURCE_POLICY_KEYS = ("source_name", "policy_name", "episode_key", "request_id", "query", "scene_key")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
    "evaluation_only_correct_candidate_count",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_unlabeled_candidate_count",
    "evaluation_only_wrong_candidate_count",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "is_correct",
    "oracle_action",
    "posthoc_outcome_delta",
    "shortest_path_distance",
    "success_or_failure_label",
    "target_label",
    "wrong_goal_label",
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    return result


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


def request_key_payload(key: Tuple[str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def source_policy_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(row.get("policy_name") or ""),
        str(source.get("episode_key") or row.get("episode_key") or ""),
        normalized_request_id(row),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
    )


def candidate_ids(row: Mapping[str, Any]) -> List[str]:
    action_summary = row.get("action_candidate_summary")
    if isinstance(action_summary, Mapping):
        ids = action_summary.get("candidate_ids")
        if isinstance(ids, list):
            return [str(value) for value in ids if value is not None]
    ids = row.get("candidate_ids")
    if isinstance(ids, list):
        return [str(value) for value in ids if value is not None]
    ids = row.get("candidate_ids_preview")
    if isinstance(ids, list):
        return [str(value) for value in ids if value is not None]
    return []


def evaluation_summary(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("evaluation_candidate_summary")
    return value if isinstance(value, Mapping) else {}


def build_label_backbone(
    backbone_rows: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[Tuple[str, str, str, str], Dict[str, Any]], List[Dict[str, Any]]]:
    request_index: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    candidate_rows: List[Dict[str, Any]] = []
    for row in backbone_rows:
        key = request_key(row)
        key_data = request_key_payload(key)
        eval_summary = evaluation_summary(row)
        action_summary = row.get("action_candidate_summary")
        action_summary = action_summary if isinstance(action_summary, Mapping) else {}
        ids = candidate_ids(row)
        correct_ids = {str(value) for value in eval_summary.get("evaluation_only_correct_candidate_ids") or []}
        wrong_ids = {str(value) for value in eval_summary.get("evaluation_only_wrong_candidate_ids") or []}
        no_valid = bool(eval_summary.get("evaluation_only_no_valid_candidate_pool") is True)
        request_index[key] = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "evaluation_only_label_join_after_action_rows",
            "row_type": "semantic_slam_task_label_request",
            **key_data,
            "label_backbone_join_available": True,
            "label_source": "primary_expanded_retrieval_local_context_route_specific",
            "candidate_count": len(ids),
            "candidate_label_count": len(correct_ids) + len(wrong_ids),
            "correct_candidate_count": len(correct_ids),
            "wrong_candidate_count": len(wrong_ids),
            "unlabeled_candidate_count": max(0, len(ids) - len(correct_ids) - len(wrong_ids)),
            "no_valid_candidate_pool": no_valid,
            "route_action": row.get("route_action"),
            "route_branch": row.get("route_branch"),
            "semantic_top_variant_available": isinstance(row.get("evaluation_only_variant_outcomes"), Mapping)
            and "semantic_top" in row.get("evaluation_only_variant_outcomes", {}),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
            "paper_claim_allowed": False,
        }
        for candidate_id in ids:
            correct = candidate_id in correct_ids
            wrong = candidate_id in wrong_ids
            candidate_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "evaluation_only_label_join_after_action_rows",
                    "row_type": "semantic_slam_task_label_candidate",
                    **key_data,
                    "candidate_id": candidate_id,
                    "candidate_label_join_available": correct or wrong or no_valid,
                    "candidate_correctness_label": True if correct else False if wrong else None,
                    "candidate_wrong_label": True if wrong else False if correct else None,
                    "no_valid_candidate_pool": no_valid,
                    "label_source": "primary_expanded_retrieval_local_context_route_specific",
                    "candidate_in_action_candidate_summary": candidate_id in set(ids),
                    "source_top_candidate": candidate_id
                    in {str(value) for value in action_summary.get("source_top_candidate_ids") or []},
                    "detector_strong_candidate": candidate_id
                    in {str(value) for value in action_summary.get("detector_strong_candidate_ids") or []},
                    "strong_own_view_candidate": candidate_id
                    in {str(value) for value in action_summary.get("strong_own_view_candidate_ids") or []},
                    "local_context_candidate": candidate_id
                    in {str(value) for value in action_summary.get("local_context_candidate_ids") or []},
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                    "paper_claim_allowed": False,
                }
            )
    return request_index, candidate_rows


def index_candidate_rows(
    candidate_rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str], Dict[str, Mapping[str, Any]]] = {}
    for row in candidate_rows:
        key = (
            str(row.get("episode_key") or ""),
            str(row.get("request_id") or ""),
            str(row.get("query") or ""),
            str(row.get("scene_key") or ""),
        )
        index.setdefault(key, {})[str(row.get("candidate_id") or "")] = row
    return index


def has_action_leakage(rows: Sequence[Mapping[str, Any]]) -> List[str]:
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


def travel_cost(row: Mapping[str, Any]) -> Optional[float]:
    value = row.get("reobserve_travel_cost_m")
    if value is not None:
        return safe_float(value)
    proxy = row.get("travel_cost_proxy_m")
    if isinstance(proxy, Mapping):
        return safe_float(proxy.get("mean"))
    return safe_float(proxy)


def materialize_policy_rows(
    *,
    probe_rows: Sequence[Mapping[str, Any]],
    request_labels: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    candidate_label_index: Mapping[Tuple[str, str, str, str], Mapping[str, Mapping[str, Any]]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    policy_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    for row in probe_rows:
        req_key = request_key(row)
        key_data = request_key_payload(req_key)
        request_label = request_labels.get(req_key)
        candidate_labels = candidate_label_index.get(req_key) or {}
        label_backbone_join_available = request_label is not None
        candidate_label_join_available = bool(candidate_labels)
        selected_candidate_id = row.get("policy_selected_candidate_id")
        terminal_commit_proxy = row.get("terminal_commit_proxy")
        task_proxy_evaluable = (
            bool(label_backbone_join_available)
            and bool(candidate_label_join_available)
            and bool(selected_candidate_id)
            and terminal_commit_proxy is not None
        )

        wrong_goal_visit_proxy = None
        wasted_path_proxy_m = None
        failure_tag = None
        failure_detail = None
        if not label_backbone_join_available:
            failure_tag = "request_label_missing"
        elif not candidate_label_join_available:
            failure_tag = "candidate_label_missing"
        elif not task_proxy_evaluable:
            failure_tag = "policy_selector_missing"
            failure_detail = "labels_joined_but_no_frozen_selected_candidate_or_terminal_commit_proxy"
        else:
            selected_label = candidate_labels.get(str(selected_candidate_id))
            selected_wrong = selected_label and selected_label.get("candidate_wrong_label") is True
            wrong_goal_visit_proxy = bool(selected_wrong and terminal_commit_proxy is True)
            if wrong_goal_visit_proxy:
                wasted_path_proxy_m = travel_cost(row)
                if wasted_path_proxy_m is None:
                    failure_tag = "travel_cost_missing"

        out = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "evaluation_only_label_join_after_action_rows",
            "row_type": "semantic_slam_task_label_policy_join",
            "join_key": dict(zip(SOURCE_POLICY_KEYS, source_policy_key(row))),
            "source_name": str(row.get("source_name") or ""),
            "policy_name": str(row.get("policy_name") or ""),
            **key_data,
            "label_backbone_join_available": label_backbone_join_available,
            "candidate_label_join_available": candidate_label_join_available,
            "candidate_label_count": safe_int(request_label.get("candidate_label_count"), 0)
            if request_label
            else 0,
            "correct_candidate_count": safe_int(request_label.get("correct_candidate_count"), 0)
            if request_label
            else 0,
            "wrong_candidate_count": safe_int(request_label.get("wrong_candidate_count"), 0)
            if request_label
            else 0,
            "no_valid_candidate_pool": bool(request_label.get("no_valid_candidate_pool") is True)
            if request_label
            else None,
            "policy_selected_candidate_id": selected_candidate_id,
            "terminal_commit_proxy": terminal_commit_proxy,
            "wrong_goal_visit_proxy": wrong_goal_visit_proxy,
            "wasted_path_proxy_m": wasted_path_proxy_m,
            "task_proxy_evaluable": task_proxy_evaluable,
            "map_side_delta": row.get("map_side_delta"),
            "pose_graph_connectivity_delta": row.get("pose_graph_connectivity_delta"),
            "map_pose_consistency_delta": row.get("map_pose_consistency_delta"),
            "reobserve_travel_cost_m": row.get("reobserve_travel_cost_m"),
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
                    "validation_stage": "evaluation_only_label_join_after_action_rows",
                    "row_type": "semantic_slam_task_label_failure",
                    **key_data,
                    "source_name": out["source_name"],
                    "policy_name": out["policy_name"],
                    "failure_tag": failure_tag,
                    "failure_detail": failure_detail,
                    "label_backbone_join_available": label_backbone_join_available,
                    "candidate_label_join_available": candidate_label_join_available,
                    "policy_selected_candidate_id": selected_candidate_id,
                    "terminal_commit_proxy": terminal_commit_proxy,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )
    return policy_rows, failure_rows


def build_summary(
    *,
    contract: Mapping[str, Any],
    probe_rows: Sequence[Mapping[str, Any]],
    request_label_rows: Sequence[Mapping[str, Any]],
    candidate_label_rows: Sequence[Mapping[str, Any]],
    policy_label_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    out_root: Path,
    action_forbidden_keys: Sequence[str],
) -> Dict[str, Any]:
    unique_request_keys = {request_key(row) for row in probe_rows}
    source_policy_keys = {source_policy_key(row) for row in probe_rows}
    label_backbone_join_rows = sum(1 for row in policy_label_rows if row.get("label_backbone_join_available") is True)
    candidate_label_join_rows = sum(1 for row in policy_label_rows if row.get("candidate_label_join_available") is True)
    task_proxy_evaluable_rows = sum(1 for row in policy_label_rows if row.get("task_proxy_evaluable") is True)
    wrong_goal_nonnull_rows = sum(1 for row in policy_label_rows if row.get("wrong_goal_visit_proxy") is not None)
    wasted_path_nonnull_rows = sum(1 for row in policy_label_rows if row.get("wasted_path_proxy_m") is not None)
    policy_selector_missing_rows = sum(1 for row in policy_label_rows if row.get("failure_tag") == "policy_selector_missing")
    uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in policy_label_rows)
    paper_claim_allowed = any(row.get("paper_claim_allowed") is True for row in policy_label_rows)
    label_gate = contract.get("success_gates", {}).get("label_join_gate", {})
    outcome_gate = contract.get("success_gates", {}).get("outcome_proxy_gate", {})
    task_label_join_gate = {
        "unique_request_keys_passed": len(unique_request_keys)
        == safe_int(label_gate.get("unique_request_keys_required"), len(unique_request_keys)),
        "source_policy_rows_passed": len(source_policy_keys)
        == safe_int(label_gate.get("source_policy_rows_required"), len(source_policy_keys)),
        "request_label_rows_passed": len(request_label_rows) >= safe_int(label_gate.get("request_label_rows_min"), 0),
        "candidate_label_rows_passed": len(candidate_label_rows)
        >= safe_int(label_gate.get("candidate_label_rows_min"), 0),
        "policy_label_join_rows_passed": len(policy_label_rows)
        >= safe_int(label_gate.get("policy_label_join_rows_min"), 0),
        "label_backbone_join_rows_passed": label_backbone_join_rows
        >= safe_int(label_gate.get("label_backbone_join_rows_min"), 0),
        "action_evidence_forbidden_keys_passed": len(action_forbidden_keys)
        == safe_int(label_gate.get("action_evidence_forbidden_key_count"), 0),
        "uses_gt_for_action_passed": uses_gt_for_action is bool(label_gate.get("uses_gt_for_action", False)),
        "paper_claim_allowed_passed": paper_claim_allowed is bool(label_gate.get("paper_claim_allowed", False)),
    }
    outcome_proxy_gate = {
        "task_proxy_evaluable_rows_passed": task_proxy_evaluable_rows
        >= safe_int(outcome_gate.get("task_proxy_evaluable_rows_min"), 0),
        "wrong_goal_visit_proxy_nonnull_rows_passed": wrong_goal_nonnull_rows
        >= safe_int(outcome_gate.get("wrong_goal_visit_proxy_nonnull_rows_min"), 0),
        "wasted_path_proxy_nonnull_rows_passed": wasted_path_nonnull_rows
        >= safe_int(outcome_gate.get("wasted_path_proxy_nonnull_rows_min"), 0),
        "policy_selector_missing_rows_passed": policy_selector_missing_rows
        <= safe_int(outcome_gate.get("policy_selector_missing_rows_max"), 0),
    }
    task_label_join_gate_passed = all(task_label_join_gate.values())
    outcome_proxy_gate_passed = all(outcome_proxy_gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-05",
        "status": "completed_label_join_gate_passed_outcome_proxy_blocked"
        if task_label_join_gate_passed and not outcome_proxy_gate_passed
        else "completed",
        "contract": str(CONTRACT_DEFAULT),
        "out_root": str(out_root),
        "output_files": {
            "request_label_rows": "semantic_slam_task_label_request_rows.jsonl",
            "candidate_label_rows": "semantic_slam_task_label_candidate_rows.jsonl",
            "policy_label_join_rows": "semantic_slam_task_label_policy_rows.jsonl",
            "failure_rows": "semantic_slam_task_label_failure_rows.jsonl",
            "summary": "semantic_slam_task_label_join_summary.json",
        },
        "source_files": contract.get("source", {}),
        "unique_request_keys": len(unique_request_keys),
        "source_policy_rows": len(source_policy_keys),
        "input_probe_rows": len(probe_rows),
        "request_label_rows": len(request_label_rows),
        "candidate_label_rows": len(candidate_label_rows),
        "candidate_correct_label_rows": sum(
            1 for row in candidate_label_rows if row.get("candidate_correctness_label") is True
        ),
        "candidate_wrong_label_rows": sum(1 for row in candidate_label_rows if row.get("candidate_wrong_label") is True),
        "candidate_unlabeled_rows": sum(
            1
            for row in candidate_label_rows
            if row.get("candidate_correctness_label") is None and row.get("no_valid_candidate_pool") is not True
        ),
        "request_no_valid_pool_rows": sum(1 for row in request_label_rows if row.get("no_valid_candidate_pool") is True),
        "policy_label_join_rows": len(policy_label_rows),
        "label_backbone_join_rows": label_backbone_join_rows,
        "candidate_label_join_rows": candidate_label_join_rows,
        "task_proxy_evaluable_rows": task_proxy_evaluable_rows,
        "task_proxy_evaluable_rate": ratio(task_proxy_evaluable_rows, len(policy_label_rows)),
        "wrong_goal_visit_proxy_nonnull_rows": wrong_goal_nonnull_rows,
        "wasted_path_proxy_nonnull_rows": wasted_path_nonnull_rows,
        "policy_selector_missing_rows": policy_selector_missing_rows,
        "policy_selector_missing_rate": ratio(policy_selector_missing_rows, len(policy_label_rows)),
        "failure_tag_counts": compact_counter(row.get("failure_tag") for row in failure_rows),
        "policy_failure_tag_counts": compact_counter(row.get("failure_tag") for row in policy_label_rows),
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "uses_gt_for_action": uses_gt_for_action,
        "paper_claim_allowed": paper_claim_allowed,
        "task_label_join_gate": task_label_join_gate,
        "outcome_proxy_gate": outcome_proxy_gate,
        "task_label_join_gate_passed": task_label_join_gate_passed,
        "outcome_proxy_gate_passed": outcome_proxy_gate_passed,
        "revised_slam_formula_allowed": outcome_proxy_gate_passed,
        "step_4_5_promotion_satisfied": False,
        "primary_blocker": None if outcome_proxy_gate_passed else "policy_selector_missing",
        "recommended_next_task": "freeze_non_gt_policy_selector_contract_for_task_proxy"
        if task_label_join_gate_passed and not outcome_proxy_gate_passed
        else "inspect_label_join_failures",
        "interpretation": {
            "fact": "The primary label backbone is materialized and joined to Semantic-SLAM policy rows without action-time label use.",
            "agent_inference": "The remaining blocker is not label coverage but missing frozen policy selected-candidate and terminal-commit proxies.",
            "paper_claim": "No navigation utility, SLAM benefit, SemanticSLAM complementarity, or formula revision claim is allowed from this label materializer alone.",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize the frozen SemanticSLAM task label join.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(Path(args.contract))
    source = contract.get("source") or {}
    probe_rows = load_jsonl(Path(source["task_map_outcome_probe_rows"]))
    request_rows = load_jsonl(Path(source["task_map_probe_request_rows"]))
    backbone_rows = load_jsonl(Path(source["primary_label_backbone"]))
    request_index, candidate_label_rows = build_label_backbone(backbone_rows)
    candidate_label_index = index_candidate_rows(candidate_label_rows)
    policy_label_rows, failure_rows = materialize_policy_rows(
        probe_rows=probe_rows,
        request_labels=request_index,
        candidate_label_index=candidate_label_index,
    )
    action_forbidden_keys = has_action_leakage(request_rows)
    out_root = Path(args.out_root)
    request_label_rows = sorted(request_index.values(), key=lambda row: tuple(str(row.get(key) or "") for key in REQUEST_KEYS))
    candidate_label_rows = sorted(
        candidate_label_rows,
        key=lambda row: (
            str(row.get("episode_key") or ""),
            str(row.get("request_id") or ""),
            str(row.get("query") or ""),
            str(row.get("scene_key") or ""),
            str(row.get("candidate_id") or ""),
        ),
    )
    summary = build_summary(
        contract=contract,
        probe_rows=probe_rows,
        request_label_rows=request_label_rows,
        candidate_label_rows=candidate_label_rows,
        policy_label_rows=policy_label_rows,
        failure_rows=failure_rows,
        out_root=out_root,
        action_forbidden_keys=action_forbidden_keys,
    )
    write_jsonl(out_root / "semantic_slam_task_label_request_rows.jsonl", request_label_rows)
    write_jsonl(out_root / "semantic_slam_task_label_candidate_rows.jsonl", candidate_label_rows)
    write_jsonl(out_root / "semantic_slam_task_label_policy_rows.jsonl", policy_label_rows)
    write_jsonl(out_root / "semantic_slam_task_label_failure_rows.jsonl", failure_rows)
    write_json(out_root / "semantic_slam_task_label_join_summary.json", summary)


if __name__ == "__main__":
    main()
