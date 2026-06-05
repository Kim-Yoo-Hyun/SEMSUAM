import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_task_policy_selector.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_task_policy_selector_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_task_policy_selector_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")
SOURCE_POLICY_KEYS = ("source_name", "policy_name", "episode_key", "request_id", "query", "scene_key")
POLICIES = ("NoReobserveReference", "SemanticOnly", "SLAMOnlyRich_current")

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness_label",
    "candidate_wrong_label",
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


def list_field(row: Mapping[str, Any], key: str) -> List[str]:
    value = row.get(key)
    if isinstance(value, list):
        return [str(item) for item in value if item is not None]
    return []


def action_candidate_summary(row: Mapping[str, Any]) -> Mapping[str, Any]:
    value = row.get("action_candidate_summary")
    return value if isinstance(value, Mapping) else {}


def action_ids(row: Mapping[str, Any], key: str) -> List[str]:
    return list_field(action_candidate_summary(row), key)


def exactly_one(values: Sequence[str]) -> Optional[str]:
    return values[0] if len(values) == 1 else None


def first_numeric(value: Any) -> Optional[float]:
    if isinstance(value, Mapping):
        for key in ("mean", "value", "delta", "max", "min"):
            if key in value:
                return first_numeric(value[key])
        return None
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def map_policy_metrics(
    source_row: Mapping[str, Any],
    policy_row: Optional[Mapping[str, Any]],
) -> Dict[str, Optional[float]]:
    return {
        "reobserve_travel_cost_m": first_numeric(
            (policy_row or {}).get("reobserve_travel_cost_m", source_row.get("travel_cost_proxy_m"))
        ),
        "pose_graph_connectivity_delta": first_numeric(
            (policy_row or {}).get("pose_graph_connectivity_delta", source_row.get("pose_graph_connectivity_delta"))
        ),
        "map_pose_consistency_delta": first_numeric(
            (policy_row or {}).get("map_pose_consistency_delta", source_row.get("map_pose_consistency_delta"))
        ),
        "map_side_delta": first_numeric((policy_row or {}).get("map_side_delta", source_row.get("map_side_delta"))),
    }


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


def build_indexes(
    action_rows: Sequence[Mapping[str, Any]],
    policy_rows: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[Tuple[str, str, str, str], Mapping[str, Any]], Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]]]:
    action_index: Dict[Tuple[str, str, str, str], Mapping[str, Any]] = {}
    for row in action_rows:
        action_index[request_key(row)] = row
    policy_index: Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]] = {}
    for row in policy_rows:
        policy_index[source_policy_key(row)] = row
    return action_index, policy_index


def base_row(
    source_row: Mapping[str, Any],
    action_row: Mapping[str, Any],
    policy_row: Optional[Mapping[str, Any]],
    policy_name: str,
    selector_id: str,
) -> Dict[str, Any]:
    key = request_key(source_row)
    summary = action_candidate_summary(action_row)
    candidate_ids = action_ids(action_row, "candidate_ids")
    source_top_ids = action_ids(action_row, "source_top_candidate_ids")
    local_context_ids = action_ids(action_row, "local_context_candidate_ids")
    strong_own_view_ids = action_ids(action_row, "strong_own_view_candidate_ids")
    detector_strong_ids = action_ids(action_row, "detector_strong_candidate_ids")
    source_policy = source_policy_key(source_row, policy_name)
    row = {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_non_gt_policy_selector_materializer",
        "row_type": "semantic_slam_task_policy_selector",
        "source_name": source_policy[0],
        "policy_name": policy_name,
        **request_key_payload(key),
        "join_key": {
            "source_name": source_policy[0],
            "policy_name": policy_name,
            **request_key_payload(key),
        },
        "selector_id": selector_id,
        "candidate_count": len(candidate_ids),
        "source_top_candidate_count": len(source_top_ids),
        "local_context_candidate_count": len(local_context_ids),
        "strong_own_view_candidate_count": len(strong_own_view_ids),
        "detector_strong_candidate_count": len(detector_strong_ids),
        "source_pool_proxy_available": bool((action_row.get("source_pool_proxy") or {}).get("available"))
        if isinstance(action_row.get("source_pool_proxy"), Mapping)
        else False,
        "route_action": action_row.get("route_action"),
        "route_branch": action_row.get("route_branch"),
        "source_row_type": source_row.get("row_type"),
        "source_family": source_row.get("semantic_uncertainty_family"),
        "candidate_specific_map_pose_required": policy_name == "SLAMOnlyRich_current",
        "uses_reobservation_evidence": policy_name in {"SemanticOnly", "SLAMOnlyRich_current"},
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    row.update(map_policy_metrics(source_row, policy_row))
    row["action_candidate_summary_counts"] = {
        "candidate_count": len(candidate_ids),
        "source_top_candidate_count": len(source_top_ids),
        "local_context_candidate_count": len(local_context_ids),
        "strong_own_view_candidate_count": len(strong_own_view_ids),
        "detector_strong_candidate_count": len(detector_strong_ids),
        "declared_candidate_count": summary.get("candidate_count"),
    }
    return row


def make_failure(selector_row: Mapping[str, Any], failure_tag: str, failure_detail: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_non_gt_policy_selector_materializer",
        "row_type": "semantic_slam_task_policy_selector_failure",
        "source_name": selector_row.get("source_name"),
        "policy_name": selector_row.get("policy_name"),
        "episode_key": selector_row.get("episode_key"),
        "request_id": selector_row.get("request_id"),
        "query": selector_row.get("query"),
        "scene_key": selector_row.get("scene_key"),
        "selector_id": selector_row.get("selector_id"),
        "selector_action": selector_row.get("selector_action"),
        "selector_missing": selector_row.get("selector_missing"),
        "selector_missing_reason": selector_row.get("selector_missing_reason"),
        "failure_tag": failure_tag,
        "failure_detail": failure_detail,
        "candidate_count": selector_row.get("candidate_count"),
        "source_top_candidate_count": selector_row.get("source_top_candidate_count"),
        "local_context_candidate_count": selector_row.get("local_context_candidate_count"),
        "strong_own_view_candidate_count": selector_row.get("strong_own_view_candidate_count"),
        "detector_strong_candidate_count": selector_row.get("detector_strong_candidate_count"),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def materialize_selectors(
    source_rows: Sequence[Mapping[str, Any]],
    action_index: Mapping[Tuple[str, str, str, str], Mapping[str, Any]],
    policy_index: Mapping[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selector_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    for source_row in source_rows:
        key = request_key(source_row)
        action_row = action_index.get(key)
        if action_row is None:
            for policy_name in POLICIES:
                missing = {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_non_gt_policy_selector_materializer",
                    "row_type": "semantic_slam_task_policy_selector",
                    "source_name": source_row.get("source_name"),
                    "policy_name": policy_name,
                    **request_key_payload(key),
                    "selector_id": "action_feature_backbone_missing_v1",
                    "selector_action": "selector_missing",
                    "policy_selected_candidate_id": None,
                    "terminal_commit_proxy": None,
                    "selector_missing": True,
                    "selector_missing_reason": "action_feature_backbone_missing",
                    "candidate_specific_map_pose_required": policy_name == "SLAMOnlyRich_current",
                    "uses_reobservation_evidence": policy_name in {"SemanticOnly", "SLAMOnlyRich_current"},
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
                selector_rows.append(missing)
                failure_rows.append(
                    make_failure(missing, "action_feature_backbone_missing", "No action-time candidate groups join this source request.")
                )
            continue

        policy_row = policy_index.get(source_policy_key(source_row, "NoReobserveReference"))
        row = base_row(
            source_row,
            action_row,
            policy_row,
            "NoReobserveReference",
            "source_top_direct_commit_v1",
        )
        source_top_id = exactly_one(action_ids(action_row, "source_top_candidate_ids"))
        if source_top_id is not None:
            row.update(
                {
                    "selector_action": "commit_candidate",
                    "policy_selected_candidate_id": source_top_id,
                    "terminal_commit_proxy": True,
                    "selector_missing": False,
                    "selector_missing_reason": None,
                    "selector_source": "unique_source_top",
                }
            )
        else:
            row.update(
                {
                    "selector_action": "defer",
                    "policy_selected_candidate_id": None,
                    "terminal_commit_proxy": False,
                    "selector_missing": False,
                    "selector_missing_reason": "source_top_missing_or_ambiguous",
                    "selector_source": None,
                }
            )
            failure_rows.append(
                make_failure(row, "source_top_missing_or_ambiguous", "NoReobserveReference requires exactly one source-top candidate.")
            )
        selector_rows.append(row)

        policy_row = policy_index.get(source_policy_key(source_row, "SemanticOnly"))
        row = base_row(
            source_row,
            action_row,
            policy_row,
            "SemanticOnly",
            "local_context_then_unique_own_view_v1",
        )
        local_context_id = exactly_one(action_ids(action_row, "local_context_candidate_ids"))
        own_view_id = exactly_one(action_ids(action_row, "strong_own_view_candidate_ids"))
        if local_context_id is not None:
            row.update(
                {
                    "selector_action": "commit_candidate",
                    "policy_selected_candidate_id": local_context_id,
                    "terminal_commit_proxy": True,
                    "selector_missing": False,
                    "selector_missing_reason": None,
                    "selector_source": "unique_local_context",
                }
            )
        elif own_view_id is not None:
            row.update(
                {
                    "selector_action": "commit_candidate",
                    "policy_selected_candidate_id": own_view_id,
                    "terminal_commit_proxy": True,
                    "selector_missing": False,
                    "selector_missing_reason": None,
                    "selector_source": "unique_own_view",
                }
            )
        else:
            row.update(
                {
                    "selector_action": "defer",
                    "policy_selected_candidate_id": None,
                    "terminal_commit_proxy": False,
                    "selector_missing": False,
                    "selector_missing_reason": "semantic_support_ambiguous_or_missing",
                    "selector_source": None,
                }
            )
            failure_rows.append(
                make_failure(
                    row,
                    "semantic_support_ambiguous_or_missing",
                    "SemanticOnly requires exactly one local-context candidate or exactly one strong own-view candidate.",
                )
            )
        selector_rows.append(row)

        policy_row = policy_index.get(source_policy_key(source_row, "SLAMOnlyRich_current"))
        row = base_row(
            source_row,
            action_row,
            policy_row,
            "SLAMOnlyRich_current",
            "candidate_specific_slam_selector_missing_v1",
        )
        row.update(
            {
                "selector_action": "selector_missing",
                "policy_selected_candidate_id": None,
                "terminal_commit_proxy": None,
                "selector_missing": True,
                "selector_missing_reason": "candidate_specific_map_pose_selector_missing",
                "selector_source": None,
            }
        )
        selector_rows.append(row)
        failure_rows.append(
            make_failure(
                row,
                "candidate_specific_map_pose_selector_missing",
                "Current artifacts provide row-level map/pose utility but no candidate-specific map/pose selector.",
            )
        )
    return selector_rows, failure_rows


def build_summary(
    contract: Mapping[str, Any],
    source_rows: Sequence[Mapping[str, Any]],
    action_rows: Sequence[Mapping[str, Any]],
    policy_rows: Sequence[Mapping[str, Any]],
    selector_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    output_root: Path,
) -> Dict[str, Any]:
    expected = contract.get("expected_materializer_counts")
    expected = expected if isinstance(expected, Mapping) else {}
    policy_counter = Counter(row.get("policy_name") for row in selector_rows)
    commit_counter = Counter(row.get("policy_name") for row in selector_rows if row.get("terminal_commit_proxy") is True)
    defer_counter = Counter(row.get("policy_name") for row in selector_rows if row.get("selector_action") == "defer")
    missing_counter = Counter(row.get("policy_name") for row in selector_rows if row.get("selector_missing") is True)
    selector_source_counter = Counter(row.get("selector_source") for row in selector_rows)
    failure_counter = Counter(row.get("failure_tag") for row in failure_rows)
    forbidden_keys = scan_forbidden_keys(selector_rows)

    actual_counts = {
        "source_request_rows": len(source_rows),
        "primary_action_feature_backbone_rows": len(action_rows),
        "task_label_policy_rows": len(policy_rows),
        "policy_selector_rows": len(selector_rows),
        "failure_rows": len(failure_rows),
        "NoReobserveReference_rows": policy_counter.get("NoReobserveReference", 0),
        "NoReobserveReference_terminal_commit_rows": commit_counter.get("NoReobserveReference", 0),
        "NoReobserveReference_defer_rows": defer_counter.get("NoReobserveReference", 0),
        "SemanticOnly_rows": policy_counter.get("SemanticOnly", 0),
        "SemanticOnly_terminal_commit_rows": commit_counter.get("SemanticOnly", 0),
        "SemanticOnly_local_context_commit_rows": selector_source_counter.get("unique_local_context", 0),
        "SemanticOnly_unique_own_view_commit_rows": selector_source_counter.get("unique_own_view", 0),
        "SemanticOnly_defer_rows": defer_counter.get("SemanticOnly", 0),
        "SLAMOnlyRich_current_rows": policy_counter.get("SLAMOnlyRich_current", 0),
        "SLAMOnlyRich_current_selector_missing_rows": missing_counter.get("SLAMOnlyRich_current", 0),
        "total_terminal_commit_rows": sum(1 for row in selector_rows if row.get("terminal_commit_proxy") is True),
        "total_defer_rows": sum(1 for row in selector_rows if row.get("selector_action") == "defer"),
        "total_selector_missing_rows": sum(1 for row in selector_rows if row.get("selector_missing") is True),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
    }
    expected_count_mismatches = {
        key: {"expected": value, "actual": actual_counts.get(key)}
        for key, value in expected.items()
        if actual_counts.get(key) != value
    }
    selector_contract_gate_passed = not expected_count_mismatches and not forbidden_keys
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-05",
        "contract": CONTRACT_DEFAULT,
        "output_root": str(output_root),
        "row_files": {
            "selector_rows": "semantic_slam_task_policy_selector_rows.jsonl",
            "failure_rows": "semantic_slam_task_policy_selector_failure_rows.jsonl",
            "summary": "semantic_slam_task_policy_selector_summary.json",
        },
        "status": "materialized",
        "actual_counts": actual_counts,
        "expected_materializer_counts": dict(expected),
        "expected_count_mismatches": expected_count_mismatches,
        "policy_rows": dict(sorted(policy_counter.items())),
        "terminal_commit_rows_by_policy": dict(sorted(commit_counter.items())),
        "defer_rows_by_policy": dict(sorted(defer_counter.items())),
        "selector_missing_rows_by_policy": dict(sorted(missing_counter.items())),
        "selector_source_rows": compact_counter(row.get("selector_source") for row in selector_rows),
        "failure_taxonomy": dict(sorted(failure_counter.items())),
        "action_evidence_forbidden_keys": forbidden_keys,
        "selector_contract_gate_passed": selector_contract_gate_passed,
        "partial_task_proxy_join_after_selector_allowed": selector_contract_gate_passed,
        "candidate_specific_slam_selector_contract_allowed": selector_contract_gate_passed,
        "revised_slam_formula_allowed": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "uses_gt_for_action": False,
        "primary_blocker": "candidate_specific_map_pose_selector_missing",
        "interpretation": {
            "fact": (
                "NoReobserveReference and SemanticOnly now have non-GT selected-candidate and terminal-commit "
                "proxies; SLAMOnlyRich_current remains selector-missing for every source request."
            ),
            "agent_inference": (
                "The next safe step is a candidate-specific SLAM/map-pose selector contract, not a "
                "SLAMOnlyRich formula revision."
            ),
            "paper_claim": (
                "No ObjectNav, SLAM, SemanticSLAM complementarity, Step 4-5, terminal utility, first_eval, "
                "policy-scale, or paper claim is allowed from this materializer alone."
            ),
        },
        "next_task": "freeze_candidate_specific_slam_map_pose_selector_contract",
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")
    source_rows = load_jsonl(Path(str(source["task_map_probe_request_rows"])))
    action_rows = load_jsonl(Path(str(source["primary_action_feature_backbone"])))
    policy_rows = load_jsonl(Path(str(source["task_label_policy_rows"])))
    action_index, policy_index = build_indexes(action_rows, policy_rows)
    selector_rows, failure_rows = materialize_selectors(source_rows, action_index, policy_index)
    summary = build_summary(contract, source_rows, action_rows, policy_rows, selector_rows, failure_rows, out_root)
    write_jsonl(out_root / "semantic_slam_task_policy_selector_rows.jsonl", selector_rows)
    write_jsonl(out_root / "semantic_slam_task_policy_selector_failure_rows.jsonl", failure_rows)
    write_json(out_root / "semantic_slam_task_policy_selector_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize frozen non-GT Semantic-SLAM task policy selectors.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
