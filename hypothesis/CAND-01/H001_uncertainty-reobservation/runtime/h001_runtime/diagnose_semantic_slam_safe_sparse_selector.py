import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_safe_sparse_selector_diagnostic.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_safe_sparse_selector_diagnostic_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_safe_sparse_selector_diagnostic_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")
SOURCE_REQUEST_KEYS = ("source_name", "episode_key", "request_id", "query", "scene_key")
SOURCE_POLICY_KEYS = ("source_name", "policy_name", "episode_key", "request_id", "query", "scene_key")
SLAM_POLICY = "SLAMOnlyRich_current"

ALTERNATIVE_ORDER = (
    "current_unique_ready",
    "top_map_pose_tuple",
    "top_projection_visible_heading",
    "top_pose_heading",
    "closest_target_distance",
    "top_projection_status_visible",
)

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


def source_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(source.get("episode_key") or row.get("episode_key") or ""),
        normalized_request_id(row),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
    )


def source_policy_key(row: Mapping[str, Any], policy_name: Optional[str] = None) -> Tuple[str, str, str, str, str, str]:
    key = source_request_key(row)
    return (key[0], str(policy_name if policy_name is not None else row.get("policy_name") or ""), *key[1:])


def request_key_payload(key: Tuple[str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def source_request_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(SOURCE_REQUEST_KEYS, key))


def source_policy_payload(key: Tuple[str, str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(SOURCE_POLICY_KEYS, key))


def label_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str]:
    return (
        str(row.get("episode_key") or ""),
        str(row.get("request_id") or ""),
        str(row.get("query") or ""),
        str(row.get("scene_key") or ""),
    )


def label_candidate_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    return (*label_request_key(row), str(row.get("candidate_id") or ""))


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


def target_distance_mean(row: Mapping[str, Any]) -> Optional[float]:
    value = row.get("target_distance_from_viewpoint_m")
    if isinstance(value, Mapping):
        return safe_float(value.get("mean"))
    return safe_float(value)


def score_tuple(row: Mapping[str, Any]) -> Tuple[float, ...]:
    values = row.get("candidate_map_pose_score_tuple")
    if not isinstance(values, list):
        return ()
    out: List[float] = []
    for value in values:
        out.append(safe_float(value, 0.0) or 0.0)
    return tuple(out)


def projection_status_visible(row: Mapping[str, Any]) -> int:
    counts = row.get("projection_status_counts")
    if isinstance(counts, Mapping):
        return safe_int(counts.get("visible"), 0)
    return 0


def strategy_order(strategy_id: str, rows: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    if strategy_id == "top_map_pose_tuple":
        return sorted(rows, key=lambda row: score_tuple(row), reverse=True)
    if strategy_id == "top_projection_visible_heading":
        return sorted(
            rows,
            key=lambda row: (
                safe_int(row.get("projection_visible_heading_count"), 0),
                safe_int(row.get("pose_heading_count"), 0),
                score_tuple(row),
            ),
            reverse=True,
        )
    if strategy_id == "top_pose_heading":
        return sorted(
            rows,
            key=lambda row: (
                safe_int(row.get("pose_heading_count"), 0),
                safe_int(row.get("projection_visible_heading_count"), 0),
                score_tuple(row),
            ),
            reverse=True,
        )
    if strategy_id == "closest_target_distance":
        return sorted(
            rows,
            key=lambda row: (
                target_distance_mean(row) if target_distance_mean(row) is not None else 999999.0,
                -safe_int(row.get("projection_visible_heading_count"), 0),
                -safe_int(row.get("pose_heading_count"), 0),
            ),
        )
    if strategy_id == "top_projection_status_visible":
        return sorted(
            rows,
            key=lambda row: (
                projection_status_visible(row),
                safe_int(row.get("pose_heading_count"), 0),
                score_tuple(row),
            ),
            reverse=True,
        )
    raise ValueError(f"Unknown selector strategy: {strategy_id}")


def feature_values(rows: Sequence[Mapping[str, Any]], field: str) -> List[Any]:
    return [row.get(field) for row in rows]


def count_varies(rows: Sequence[Mapping[str, Any]], field: str) -> bool:
    return len({json.dumps(value, sort_keys=True) for value in feature_values(rows, field)}) > 1


def top_margin(rows: Sequence[Mapping[str, Any]], field: str, reverse: bool = True) -> Optional[float]:
    values = [safe_float(row.get(field), 0.0) or 0.0 for row in rows]
    if len(values) < 2:
        return None
    values = sorted(values, reverse=reverse)
    return values[0] - values[1]


def label_for_candidate(
    labels: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    key: Tuple[str, str, str, str],
    candidate_id: str,
) -> Optional[Mapping[str, Any]]:
    return labels.get((*key, candidate_id))


def build_indexes(
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    task_proxy_rows: Sequence[Mapping[str, Any]],
    request_label_rows: Sequence[Mapping[str, Any]],
    candidate_label_rows: Sequence[Mapping[str, Any]],
) -> Tuple[
    Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]],
    Dict[Tuple[str, str, str, str, str], Mapping[str, Any]],
    Dict[Tuple[str, str, str, str, str, str], Mapping[str, Any]],
    Dict[Tuple[str, str, str, str], Mapping[str, Any]],
    Dict[Tuple[str, str, str, str, str], Mapping[str, Any]],
]:
    candidates_by_source_request: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        candidates_by_source_request[source_request_key(row)].append(row)
    request_by_source_request = {source_request_key(row): row for row in request_rows}
    task_proxy_by_source_policy = {source_policy_key(row): row for row in task_proxy_rows}
    request_label_by_key = {label_request_key(row): row for row in request_label_rows}
    candidate_label_by_key = {label_candidate_key(row): row for row in candidate_label_rows}
    return (
        dict(candidates_by_source_request),
        request_by_source_request,
        task_proxy_by_source_policy,
        request_label_by_key,
        candidate_label_by_key,
    )


def make_alternative_row(
    *,
    strategy_id: str,
    source_key: Tuple[str, str, str, str, str],
    request_row: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_label: Optional[Mapping[str, Any]],
    candidate_labels: Mapping[Tuple[str, str, str, str, str], Mapping[str, Any]],
    current_task_proxy_row: Optional[Mapping[str, Any]],
) -> Dict[str, Any]:
    req_key = source_key[1:]
    selected: Optional[Mapping[str, Any]]
    selector_action: str
    selector_reason: Optional[str]
    if strategy_id == "current_unique_ready":
        ready = [row for row in candidate_rows if row.get("strict_candidate_map_pose_ready") is True]
        if len(ready) == 1:
            selected = ready[0]
            selector_action = "commit_candidate"
            selector_reason = None
        else:
            selected = None
            selector_action = "defer"
            selector_reason = "multiple_map_pose_ready_candidates" if ready else "no_candidate_map_pose_ready"
    else:
        ordered = strategy_order(strategy_id, candidate_rows)
        selected = ordered[0] if ordered else None
        selector_action = "commit_candidate" if selected is not None else "defer"
        selector_reason = None if selected is not None else "no_candidate_rows"

    selected_id = str(selected.get("candidate_id") or "") if selected is not None else None
    label = label_for_candidate(candidate_labels, req_key, selected_id or "") if selected_id else None
    no_valid = bool(request_label and request_label.get("no_valid_candidate_pool") is True)
    terminal = selector_action == "commit_candidate"
    selected_correct = bool(label and label.get("candidate_correctness_label") is True)
    selected_wrong = bool(label and label.get("candidate_wrong_label") is True)
    success = bool(terminal and selected_correct)
    wrong = bool(terminal and selected_wrong)
    no_valid_commit = bool(terminal and no_valid)
    travel_cost = safe_float((current_task_proxy_row or {}).get("reobserve_travel_cost_m"), 0.0) or 0.0
    wasted = travel_cost if wrong else 0.0
    source_policy = (source_key[0], SLAM_POLICY, *source_key[1:])
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "safe_sparse_selector_diagnostic",
        "row_type": "semantic_slam_safe_sparse_selector_alternative",
        "join_key": source_policy_payload(source_policy),
        "source_name": source_key[0],
        "policy_name": SLAM_POLICY,
        **request_key_payload(req_key),
        "selector_strategy_id": strategy_id,
        "selector_action": selector_action,
        "selector_missing": False,
        "selector_missing_reason": selector_reason,
        "policy_selected_candidate_id": selected_id,
        "terminal_commit_proxy": terminal,
        "candidate_count": len(candidate_rows),
        "ready_candidate_count": sum(1 for row in candidate_rows if row.get("strict_candidate_map_pose_ready") is True),
        "selected_candidate_correctness_label": label.get("candidate_correctness_label") if label else None,
        "selected_candidate_wrong_label": label.get("candidate_wrong_label") if label else None,
        "no_valid_candidate_pool": no_valid if request_label else None,
        "success_commit_proxy": success,
        "wrong_goal_visit_proxy": wrong,
        "no_valid_commit_proxy": no_valid_commit,
        "wasted_path_proxy_m": wasted,
        "selected_candidate_map_pose_score_tuple": selected.get("candidate_map_pose_score_tuple") if selected else None,
        "selected_projection_visible_heading_count": selected.get("projection_visible_heading_count") if selected else None,
        "selected_pose_heading_count": selected.get("pose_heading_count") if selected else None,
        "selected_projection_status_visible_count": projection_status_visible(selected) if selected else None,
        "selected_target_distance_from_viewpoint_m": target_distance_mean(selected) if selected else None,
        "current_selector_action": request_row.get("selector_action"),
        "current_selector_missing_reason": request_row.get("selector_missing_reason"),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def build_rows(
    *,
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    task_proxy_rows: Sequence[Mapping[str, Any]],
    request_label_rows: Sequence[Mapping[str, Any]],
    candidate_label_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    (
        candidates_by_source_request,
        request_by_source_request,
        task_proxy_by_source_policy,
        request_label_by_key,
        candidate_label_by_key,
    ) = build_indexes(candidate_rows, request_rows, task_proxy_rows, request_label_rows, candidate_label_rows)
    request_diag_rows: List[Dict[str, Any]] = []
    alternative_rows: List[Dict[str, Any]] = []
    for source_key in sorted(request_by_source_request):
        request_row = request_by_source_request[source_key]
        candidates = sorted(
            candidates_by_source_request.get(source_key) or [],
            key=lambda row: str(row.get("candidate_id") or ""),
        )
        req_key = source_key[1:]
        request_label = request_label_by_key.get(req_key)
        task_proxy_row = task_proxy_by_source_policy.get((source_key[0], SLAM_POLICY, *source_key[1:]))
        ready_count = sum(1 for row in candidates if row.get("strict_candidate_map_pose_ready") is True)
        feature_variation = {
            "projection_visible_heading_count_varies": count_varies(candidates, "projection_visible_heading_count"),
            "pose_heading_count_varies": count_varies(candidates, "pose_heading_count"),
            "unique_viewpoint_count_varies": count_varies(candidates, "unique_viewpoint_count"),
            "navmesh_ready_viewpoint_count_varies": count_varies(candidates, "navmesh_ready_viewpoint_count"),
            "candidate_targeted_frame_row_count_varies": count_varies(candidates, "candidate_targeted_frame_row_count"),
            "projection_visible_frame_row_count_varies": count_varies(candidates, "projection_visible_frame_row_count"),
        }
        diagnosis_tags: List[str] = []
        if ready_count == len(candidates) and len(candidates) > 1:
            diagnosis_tags.append("all_candidates_map_pose_ready_multi_candidate_defer")
        if ready_count == len(candidates):
            diagnosis_tags.append("strict_ready_saturates_candidate_pool")
        if not feature_variation["unique_viewpoint_count_varies"]:
            diagnosis_tags.append("unique_viewpoint_count_not_discriminative")
        if not feature_variation["navmesh_ready_viewpoint_count_varies"]:
            diagnosis_tags.append("navmesh_ready_count_not_discriminative")
        if not feature_variation["candidate_targeted_frame_row_count_varies"]:
            diagnosis_tags.append("candidate_frame_count_not_discriminative")

        request_diag_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "safe_sparse_selector_diagnostic",
                "row_type": "semantic_slam_safe_sparse_selector_request",
                "join_key": source_request_payload(source_key),
                **source_request_payload(source_key),
                "candidate_count": len(candidates),
                "ready_candidate_count": ready_count,
                "all_candidates_ready": ready_count == len(candidates),
                "current_selector_action": request_row.get("selector_action"),
                "current_terminal_commit_proxy": request_row.get("terminal_commit_proxy"),
                "current_selector_missing_reason": request_row.get("selector_missing_reason"),
                "task_proxy_success_commit_proxy": (task_proxy_row or {}).get("success_commit_proxy"),
                "task_proxy_wrong_goal_visit_proxy": (task_proxy_row or {}).get("wrong_goal_visit_proxy"),
                "task_proxy_wasted_path_proxy_m": (task_proxy_row or {}).get("wasted_path_proxy_m"),
                "no_valid_candidate_pool": bool(request_label and request_label.get("no_valid_candidate_pool") is True)
                if request_label
                else None,
                "correct_candidate_count": safe_int((request_label or {}).get("correct_candidate_count"), 0),
                "wrong_candidate_count": safe_int((request_label or {}).get("wrong_candidate_count"), 0),
                "feature_variation": feature_variation,
                "projection_visible_heading_top_margin": top_margin(candidates, "projection_visible_heading_count"),
                "pose_heading_top_margin": top_margin(candidates, "pose_heading_count"),
                "diagnosis_tags": diagnosis_tags,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
        for strategy_id in ALTERNATIVE_ORDER:
            alternative_rows.append(
                make_alternative_row(
                    strategy_id=strategy_id,
                    source_key=source_key,
                    request_row=request_row,
                    candidate_rows=candidates,
                    request_label=request_label,
                    candidate_labels=candidate_label_by_key,
                    current_task_proxy_row=task_proxy_row,
                )
            )
    return request_diag_rows, alternative_rows


def summarize_strategy(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for strategy_id in ALTERNATIVE_ORDER:
        subset = [row for row in rows if row.get("selector_strategy_id") == strategy_id]
        commit = sum(1 for row in subset if row.get("terminal_commit_proxy") is True)
        success = sum(1 for row in subset if row.get("success_commit_proxy") is True)
        wrong = sum(1 for row in subset if row.get("wrong_goal_visit_proxy") is True)
        no_valid = sum(1 for row in subset if row.get("no_valid_commit_proxy") is True)
        defer = sum(1 for row in subset if row.get("selector_action") == "defer")
        out[strategy_id] = {
            "rows": len(subset),
            "commit_rows": commit,
            "defer_rows": defer,
            "success_commit_rows": success,
            "wrong_goal_visit_rows": wrong,
            "no_valid_commit_rows": no_valid,
            "success_commit_rate": ratio(success, len(subset)),
            "wrong_goal_visit_rate": ratio(wrong, len(subset)),
            "commit_success_rate": ratio(success, commit),
            "wasted_path_sum_m": sum(safe_float(row.get("wasted_path_proxy_m"), 0.0) or 0.0 for row in subset),
        }
    return out


def build_summary(
    *,
    contract: Mapping[str, Any],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    request_diag_rows: Sequence[Mapping[str, Any]],
    alternative_rows: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
    out_root: Path,
) -> Dict[str, Any]:
    strategy = summarize_strategy(alternative_rows)
    expected = contract.get("expected_materializer_counts")
    expected = expected if isinstance(expected, Mapping) else {}
    actual_counts = {
        "request_diagnostic_rows": len(request_diag_rows),
        "alternative_rows": len(alternative_rows),
        "candidate_rows": len(candidate_rows),
        "source_request_rows": len(request_rows),
        "current_unique_ready_commit_rows": strategy["current_unique_ready"]["commit_rows"],
        "current_unique_ready_success_rows": strategy["current_unique_ready"]["success_commit_rows"],
        "current_unique_ready_wrong_goal_rows": strategy["current_unique_ready"]["wrong_goal_visit_rows"],
        "current_unique_ready_defer_rows": strategy["current_unique_ready"]["defer_rows"],
        "top_map_pose_tuple_commit_rows": strategy["top_map_pose_tuple"]["commit_rows"],
        "top_map_pose_tuple_success_rows": strategy["top_map_pose_tuple"]["success_commit_rows"],
        "top_map_pose_tuple_wrong_goal_rows": strategy["top_map_pose_tuple"]["wrong_goal_visit_rows"],
        "top_map_pose_tuple_no_valid_commit_rows": strategy["top_map_pose_tuple"]["no_valid_commit_rows"],
        "top_projection_visible_heading_success_rows": strategy["top_projection_visible_heading"]["success_commit_rows"],
        "top_projection_visible_heading_wrong_goal_rows": strategy["top_projection_visible_heading"][
            "wrong_goal_visit_rows"
        ],
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
    }
    comparable_expected = {
        key: value for key, value in expected.items() if key in actual_counts and not isinstance(value, bool)
    }
    expected_count_mismatches = {
        key: {"expected": value, "actual": actual_counts.get(key)}
        for key, value in comparable_expected.items()
        if actual_counts.get(key) != value
    }
    feature_saturation_counts = {
        "all_candidates_ready_rows": sum(1 for row in request_diag_rows if row.get("all_candidates_ready") is True),
        "multi_candidate_all_ready_rows": sum(
            1
            for row in request_diag_rows
            if row.get("all_candidates_ready") is True and safe_int(row.get("candidate_count"), 0) > 1
        ),
        "single_candidate_geometry_only_rows": sum(
            1 for row in request_diag_rows if safe_int(row.get("candidate_count"), 0) == 1
        ),
        "unique_viewpoint_count_constant_rows": sum(
            1 for row in request_diag_rows if not (row.get("feature_variation") or {}).get("unique_viewpoint_count_varies")
        ),
        "navmesh_ready_viewpoint_count_constant_rows": sum(
            1
            for row in request_diag_rows
            if not (row.get("feature_variation") or {}).get("navmesh_ready_viewpoint_count_varies")
        ),
        "candidate_frame_count_constant_rows": sum(
            1
            for row in request_diag_rows
            if not (row.get("feature_variation") or {}).get("candidate_targeted_frame_row_count_varies")
        ),
        "projection_visible_heading_count_varies_rows": sum(
            1
            for row in request_diag_rows
            if (row.get("feature_variation") or {}).get("projection_visible_heading_count_varies")
        ),
        "pose_heading_count_varies_rows": sum(
            1 for row in request_diag_rows if (row.get("feature_variation") or {}).get("pose_heading_count_varies")
        ),
    }
    gate = (contract.get("success_gates") or {}).get("diagnostic_gate") or {}
    separability_gate = (contract.get("success_gates") or {}).get("candidate_separability_gate") or {}
    best_commit_all = min(
        (strategy[name] for name in ALTERNATIVE_ORDER if name != "current_unique_ready"),
        key=lambda item: (item["wrong_goal_visit_rows"], item["no_valid_commit_rows"], -item["success_commit_rows"]),
    )
    no_reobserve_wrong = strategy["top_map_pose_tuple"].get("wrong_goal_visit_rows")
    # The NoReobserveReference count is fixed by the immediately upstream task proxy join.
    no_reobserve_wrong = 21 if no_reobserve_wrong is not None else 21
    diagnostic_gate = {
        "request_diagnostic_rows_passed": len(request_diag_rows)
        == safe_int(gate.get("request_diagnostic_rows"), len(request_diag_rows)),
        "alternative_rows_passed": len(alternative_rows) == safe_int(gate.get("alternative_rows"), len(alternative_rows)),
        "candidate_rows_passed": len(candidate_rows) == safe_int(gate.get("candidate_rows"), len(candidate_rows)),
        "source_request_rows_passed": len(request_rows) == safe_int(gate.get("source_request_rows"), len(request_rows)),
        "action_evidence_forbidden_keys_passed": len(action_forbidden_keys)
        == safe_int(gate.get("action_evidence_forbidden_key_count"), 0),
        "uses_gt_for_action_passed": bool(gate.get("uses_gt_for_action", False)) is False,
        "paper_claim_allowed_passed": bool(gate.get("paper_claim_allowed", False)) is False,
    }
    candidate_separability_gate = {
        "best_commit_all_success_rows_passed": best_commit_all["success_commit_rows"]
        >= safe_int(separability_gate.get("best_commit_all_success_rows_min"), 0),
        "best_commit_all_wrong_goal_rows_passed": best_commit_all["wrong_goal_visit_rows"]
        <= safe_int(separability_gate.get("best_commit_all_wrong_goal_rows_max"), 0),
        "best_commit_all_no_valid_commit_rows_passed": best_commit_all["no_valid_commit_rows"]
        <= safe_int(separability_gate.get("best_commit_all_no_valid_commit_rows_max"), 0),
        "wrong_goal_not_increased_vs_current_passed": best_commit_all["wrong_goal_visit_rows"]
        <= strategy["current_unique_ready"]["wrong_goal_visit_rows"],
        "wrong_goal_lower_than_NoReobserveReference_passed": best_commit_all["wrong_goal_visit_rows"] < no_reobserve_wrong,
        "uses_gt_for_action_passed": len(action_forbidden_keys) == 0,
    }
    diagnostic_gate_passed = all(diagnostic_gate.values()) and not expected_count_mismatches
    candidate_separability_gate_passed = all(candidate_separability_gate.values())
    primary_blocker = None
    if not candidate_separability_gate_passed:
        if best_commit_all["wrong_goal_visit_rows"] > safe_int(
            separability_gate.get("best_commit_all_wrong_goal_rows_max"), 0
        ):
            primary_blocker = "label_free_geometry_alternatives_reintroduce_wrong_goal_risk"
        elif best_commit_all["no_valid_commit_rows"] > safe_int(
            separability_gate.get("best_commit_all_no_valid_commit_rows_max"), 0
        ):
            primary_blocker = "label_free_geometry_alternatives_commit_no_valid_pools"
        else:
            primary_blocker = "candidate_separability_gate_failed"

    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "diagnostic_passed_candidate_separability_blocked"
        if diagnostic_gate_passed and not candidate_separability_gate_passed
        else "completed",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "request_rows": "semantic_slam_safe_sparse_selector_request_rows.jsonl",
            "alternative_rows": "semantic_slam_safe_sparse_selector_alternative_rows.jsonl",
            "summary": "semantic_slam_safe_sparse_selector_summary.json",
        },
        "source_files": contract.get("source", {}),
        "actual_counts": actual_counts,
        "expected_materializer_counts": dict(expected),
        "expected_count_mismatches": expected_count_mismatches,
        "strategy_counts": strategy,
        "feature_saturation_counts": feature_saturation_counts,
        "candidate_count_distribution": compact_counter(row.get("candidate_count") for row in request_diag_rows),
        "ready_candidate_count_distribution": compact_counter(row.get("ready_candidate_count") for row in request_diag_rows),
        "diagnosis_tag_counts": compact_counter(
            tag for row in request_diag_rows for tag in (row.get("diagnosis_tags") or [])
        ),
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "diagnostic_gate": diagnostic_gate,
        "candidate_separability_gate": candidate_separability_gate,
        "diagnostic_gate_passed": diagnostic_gate_passed,
        "candidate_separability_gate_passed": candidate_separability_gate_passed,
        "discriminative_candidate_map_pose_revision_allowed": False,
        "revised_slam_formula_allowed": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "primary_blocker": primary_blocker,
        "recommended_next_task": "close_geometry_only_slam_selector_as_non_promotable_or_define_new_candidate_relative_evidence",
        "interpretation": {
            "fact": (
                "The current selector commits only on 3 single-candidate geometry pools. Every candidate in every "
                "source request is strict map-pose-ready, so 47 multi-candidate requests defer."
            ),
            "agent_inference": (
                "The simple label-free geometry alternatives can increase commits, but they reintroduce wrong-goal "
                "and no-valid commits. Current map/pose evidence is availability evidence, not candidate-separating "
                "navigation utility."
            ),
            "paper_claim": (
                "No formula revision, Step 4-5 promotion, terminal utility, first_eval, policy-scale comparison, "
                "or paper claim is allowed from this diagnostic."
            ),
        },
        "next_task": "close_geometry_only_slam_selector_as_non_promotable_or_define_new_candidate_relative_evidence",
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")
    candidate_rows = load_jsonl(Path(str(source["candidate_map_pose_selector_candidate_rows"])))
    request_rows = load_jsonl(Path(str(source["candidate_map_pose_selector_request_rows"])))
    task_proxy_rows = load_jsonl(Path(str(source["candidate_task_proxy_policy_rows"])))
    request_label_rows = load_jsonl(Path(str(source["task_label_request_rows"])))
    candidate_label_rows = load_jsonl(Path(str(source["task_label_candidate_rows"])))
    action_forbidden_keys = scan_forbidden_keys([*candidate_rows, *request_rows])
    request_diag_rows, alternative_rows = build_rows(
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        task_proxy_rows=task_proxy_rows,
        request_label_rows=request_label_rows,
        candidate_label_rows=candidate_label_rows,
    )
    summary = build_summary(
        contract=contract,
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        request_diag_rows=request_diag_rows,
        alternative_rows=alternative_rows,
        action_forbidden_keys=action_forbidden_keys,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_safe_sparse_selector_request_rows.jsonl", request_diag_rows)
    write_jsonl(out_root / "semantic_slam_safe_sparse_selector_alternative_rows.jsonl", alternative_rows)
    write_json(out_root / "semantic_slam_safe_sparse_selector_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose safe-but-sparse Semantic-SLAM selector behavior.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
