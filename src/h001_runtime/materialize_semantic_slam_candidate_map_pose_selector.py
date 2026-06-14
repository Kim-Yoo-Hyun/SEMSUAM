import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_candidate_map_pose_selector.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_candidate_map_pose_selector_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_candidate_map_pose_selector_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
REQUEST_KEYS = ("episode_key", "request_id", "query", "scene_key")
SOURCE_REQUEST_KEYS = ("source_name", "episode_key", "request_id", "query", "scene_key")
POLICY_NAME = "SLAMOnlyRich_current"
SELECTOR_ID = "candidate_map_pose_unique_ready_v1"

FORBIDDEN_ACTION_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "correctness_label",
    "evaluation_candidate_summary",
    "evaluation_label",
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
    "target_detector_evidence_score",
    "target_positive_support",
    "target_semantic_score",
    "target_support_score",
    "wasted_path_proxy_m",
    "wrong_goal_commit",
    "wrong_goal_visit_proxy",
}

SOURCE_SEMANTIC_DETECTOR_FIELDS = (
    "target_detector_evidence_score",
    "target_positive_support",
    "target_semantic_score",
    "target_support_score",
)


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


def finite_vec3(value: Any) -> bool:
    if not isinstance(value, list) or len(value) < 3:
        return False
    return all(safe_float(item) is not None for item in value[:3])


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


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


def source_request_key(row: Mapping[str, Any], source_name: Optional[str] = None) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source_name if source_name is not None else source.get("source_name") or row.get("source_name") or ""),
        str(source.get("episode_key") or row.get("episode_key") or ""),
        normalized_request_id(row),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
    )


def request_key_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(SOURCE_REQUEST_KEYS, key))


def candidate_id_for_frame(row: Mapping[str, Any]) -> str:
    for key in ("candidate_id", "target_candidate_id"):
        value = row.get(key)
        if value:
            return str(value)
    ids = row.get("candidate_ids")
    if isinstance(ids, list) and len(ids) == 1 and ids[0]:
        return str(ids[0])
    return ""


def heading_pose_depth_metadata_count(row: Mapping[str, Any]) -> int:
    headings = row.get("rendered_headings")
    if not isinstance(headings, list):
        return 0
    count = 0
    for heading in headings:
        if not isinstance(heading, Mapping):
            continue
        if heading.get("pose") and heading.get("depth") and heading.get("metadata"):
            count += 1
    return count


def projection_visible_heading_count(row: Mapping[str, Any]) -> int:
    direct = safe_int(row.get("projection_anchor_visible_heading_rows"), -1)
    if direct >= 0:
        return direct
    heading_ids = set()
    anchors = row.get("projection_anchor_rows")
    if not isinstance(anchors, list):
        return 0
    for anchor in anchors:
        if not isinstance(anchor, Mapping):
            continue
        if anchor.get("projection_status") == "visible":
            heading_id = anchor.get("heading_id")
            if heading_id:
                heading_ids.add(str(heading_id))
    return len(heading_ids)


def projection_status_counts(row: Mapping[str, Any], field: str) -> Dict[str, int]:
    anchors = row.get("projection_anchor_rows")
    if not isinstance(anchors, list):
        return {}
    return compact_counter(anchor.get(field) for anchor in anchors if isinstance(anchor, Mapping))


def load_projection_rows(source_inventory: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str], Mapping[str, Any]]:
    index: Dict[Tuple[str, str, str], Mapping[str, Any]] = {}
    for source in source_inventory:
        source_name = str(source.get("source_name") or "")
        summary_path = Path(str(source.get("projection_summary") or ""))
        projection_path = summary_path.parent / "projection_anchor_smoke_rows.jsonl"
        for row in load_jsonl(projection_path):
            decision_id = str(row.get("decision_id") or "")
            candidate_id = str(row.get("candidate_id") or "")
            if source_name and decision_id and candidate_id:
                index[(source_name, decision_id, candidate_id)] = row
    return index


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


def build_candidate_rows(
    source_inventory: Sequence[Mapping[str, Any]],
    projection_index: Mapping[Tuple[str, str, str], Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]], Dict[str, int]]:
    grouped: Dict[Tuple[str, str, str, str, str, str], List[Tuple[Mapping[str, Any], Optional[Mapping[str, Any]]]]] = defaultdict(list)
    source_forbidden_counts: Counter[str] = Counter()
    for source in source_inventory:
        source_name = str(source.get("source_name") or "")
        for frame in load_jsonl(Path(str(source.get("frame_rows") or ""))):
            for forbidden_key in SOURCE_SEMANTIC_DETECTOR_FIELDS:
                if forbidden_key in frame:
                    source_forbidden_counts[forbidden_key] += 1
            candidate_id = candidate_id_for_frame(frame)
            key = (*source_request_key(frame, source_name), candidate_id)
            projection = projection_index.get((source_name, str(frame.get("decision_id") or ""), candidate_id))
            grouped[key].append((frame, projection))

    candidate_rows: List[Dict[str, Any]] = []
    by_request: Dict[Tuple[str, str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for key in sorted(grouped):
        source_name, episode_key, request_id, query, scene_key, candidate_id = key
        rows = grouped[key]
        frame_rows = [frame for frame, _ in rows]
        projection_rows = [projection for _, projection in rows if projection is not None]
        pose_heading_count = sum(heading_pose_depth_metadata_count(frame) for frame in frame_rows)
        total_heading_count = sum(len(frame.get("rendered_headings") or []) for frame in frame_rows)
        projection_visible_count = sum(projection_visible_heading_count(projection) for projection in projection_rows)
        projection_visible_row_count = sum(
            1
            for projection in projection_rows
            if projection.get("projection_anchor_visible") is True or projection_visible_heading_count(projection) > 0
        )
        viewpoint_ids = {
            str(frame.get("viewpoint_id") or frame.get("decision_id") or "")
            for frame in frame_rows
            if frame.get("viewpoint_id") or frame.get("decision_id")
        }
        navmesh_ready_viewpoint_ids = {
            str(frame.get("viewpoint_id") or frame.get("decision_id") or "")
            for frame in frame_rows
            if (frame.get("standoff_navmesh_snapped") is True or frame.get("standoff_navmesh_navigable") is True)
            and (frame.get("viewpoint_id") or frame.get("decision_id"))
        }
        target_position_ready = any(finite_vec3(frame.get("target_position")) for frame in frame_rows)
        physical_viewpoint_position_ready = any(finite_vec3(frame.get("physical_viewpoint_position")) for frame in frame_rows)
        distance = number_stats(frame.get("target_distance_from_viewpoint_m") for frame in frame_rows)
        mean_distance = distance["mean"]
        score_tuple = [
            projection_visible_count,
            pose_heading_count,
            len(viewpoint_ids),
            len(navmesh_ready_viewpoint_ids),
            -(mean_distance if mean_distance is not None else 999999.0),
        ]
        strict_ready = (
            bool(candidate_id)
            and len(frame_rows) >= 1
            and pose_heading_count >= 3
            and projection_visible_count >= 1
            and len(navmesh_ready_viewpoint_ids) >= 1
            and target_position_ready
            and physical_viewpoint_position_ready
        )
        missing_required_fields = not (
            bool(candidate_id)
            and target_position_ready
            and physical_viewpoint_position_ready
            and pose_heading_count > 0
            and len(projection_rows) == len(frame_rows)
        )
        projection_status = Counter()
        projection_axis_status = Counter()
        for projection in projection_rows:
            projection_status.update(projection_status_counts(projection, "projection_status"))
            projection_axis_status.update(projection_status_counts(projection, "projection_axis_status"))
        request_key = key[:5]
        row = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "candidate_specific_map_pose_selector_materializer",
            "row_type": "semantic_slam_candidate_map_pose_selector_candidate",
            "source_name": source_name,
            "episode_key": episode_key,
            "request_id": request_id,
            "query": query,
            "scene_key": scene_key,
            "candidate_id": candidate_id,
            "join_key": {
                "source_name": source_name,
                "episode_key": episode_key,
                "request_id": request_id,
                "query": query,
                "scene_key": scene_key,
                "candidate_id": candidate_id,
            },
            "candidate_targeted_frame_row_count": len(frame_rows),
            "projection_row_count": len(projection_rows),
            "projection_rows_missing_count": max(0, len(frame_rows) - len(projection_rows)),
            "pose_heading_count": pose_heading_count,
            "total_heading_count": total_heading_count,
            "projection_visible_heading_count": projection_visible_count,
            "projection_visible_frame_row_count": projection_visible_row_count,
            "unique_viewpoint_count": len(viewpoint_ids),
            "navmesh_ready_viewpoint_count": len(navmesh_ready_viewpoint_ids),
            "target_position_ready": target_position_ready,
            "physical_viewpoint_position_ready": physical_viewpoint_position_ready,
            "target_distance_from_viewpoint_m": distance,
            "viewpoint_source_counts": compact_counter(frame.get("viewpoint_source") for frame in frame_rows),
            "view_role_counts": compact_counter(frame.get("view_role") for frame in frame_rows),
            "projection_status_counts": dict(sorted(projection_status.items())),
            "projection_axis_status_counts": dict(sorted(projection_axis_status.items())),
            "strict_candidate_map_pose_ready": strict_ready,
            "candidate_geometry_missing": missing_required_fields,
            "candidate_map_pose_score_tuple": score_tuple,
            "selector_evidence": "candidate_frame_pose_projection_navmesh_geometry_only",
            "uses_semantic_or_detector_shortcut": False,
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        }
        candidate_rows.append(row)
        by_request[request_key].append(row)
    return candidate_rows, by_request, dict(sorted(source_forbidden_counts.items()))


def make_failure(request_row: Mapping[str, Any], failure_tag: str, failure_detail: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "candidate_specific_map_pose_selector_materializer",
        "row_type": "semantic_slam_candidate_map_pose_selector_failure",
        "source_name": request_row.get("source_name"),
        "policy_name": request_row.get("policy_name"),
        "episode_key": request_row.get("episode_key"),
        "request_id": request_row.get("request_id"),
        "query": request_row.get("query"),
        "scene_key": request_row.get("scene_key"),
        "selector_id": request_row.get("selector_id"),
        "selector_action": request_row.get("selector_action"),
        "selector_missing": request_row.get("selector_missing"),
        "selector_missing_reason": request_row.get("selector_missing_reason"),
        "failure_tag": failure_tag,
        "failure_detail": failure_detail,
        "candidate_count": request_row.get("candidate_count"),
        "ready_candidate_count": request_row.get("ready_candidate_count"),
        "policy_selected_candidate_id": request_row.get("policy_selected_candidate_id"),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def request_context_index(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {source_request_key(row): row for row in rows}


def strict_variant_index(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        grouped[source_request_key(row)][str(row.get("edge_variant") or "")] = row
    return grouped


def materialize_request_rows(
    source_request_rows: Sequence[Mapping[str, Any]],
    candidate_by_request: Mapping[Tuple[str, str, str, str, str], List[Dict[str, Any]]],
    pose_graph_rows: Sequence[Mapping[str, Any]],
    strict_edge_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    pose_graph_index = request_context_index(pose_graph_rows)
    strict_index = strict_variant_index(strict_edge_rows)
    request_rows: List[Dict[str, Any]] = []
    failure_rows: List[Dict[str, Any]] = []
    for source_request in source_request_rows:
        key = source_request_key(source_request)
        candidates = sorted(
            candidate_by_request.get(key, []),
            key=lambda row: (
                row.get("candidate_map_pose_score_tuple") or [0, 0, 0, 0, -999999.0],
                row.get("candidate_id") or "",
            ),
            reverse=True,
        )
        ready_candidates = [row for row in candidates if row.get("strict_candidate_map_pose_ready") is True]
        geometry_missing_candidates = [row for row in candidates if row.get("candidate_geometry_missing") is True]
        key_data = request_key_payload(key)
        pose_graph = pose_graph_index.get(key) or {}
        strict_variants = strict_index.get(key) or {}
        pose_spatial = strict_variants.get("pose_spatial") or {}
        pose_loop = strict_variants.get("pose_loop") or {}
        source_role = source_request.get("source_role")
        source_family = source_request.get("semantic_uncertainty_family")
        row = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "candidate_specific_map_pose_selector_materializer",
            "row_type": "semantic_slam_candidate_map_pose_selector_request",
            **key_data,
            "policy_name": POLICY_NAME,
            "join_key": {
                "source_name": key[0],
                "policy_name": POLICY_NAME,
                "episode_key": key[1],
                "request_id": key[2],
                "query": key[3],
                "scene_key": key[4],
            },
            "selector_id": SELECTOR_ID,
            "candidate_count": len(candidates),
            "ready_candidate_count": len(ready_candidates),
            "geometry_missing_candidate_count": len(geometry_missing_candidates),
            "strict_candidate_map_pose_ready_candidate_ids": [
                str(candidate.get("candidate_id") or "") for candidate in ready_candidates
            ],
            "diagnostic_ranked_candidate_ids_by_map_pose_tuple": [
                str(candidate.get("candidate_id") or "") for candidate in candidates
            ],
            "candidate_map_pose_score_tuple_by_rank": [
                candidate.get("candidate_map_pose_score_tuple") for candidate in candidates
            ],
            "single_candidate_pool_geometry_only": len(candidates) == 1 and len(ready_candidates) == 1,
            "source_family": source_family,
            "source_role": source_role,
            "source_probe_request_ready": source_request.get("probe_request_ready"),
            "source_candidate_id_count": source_request.get("candidate_id_count"),
            "source_frame_row_count": source_request.get("frame_row_count"),
            "request_pose_graph_proxy_ready": pose_graph.get("proxy_ready"),
            "request_pose_graph_connected_component_count": pose_graph.get("connected_component_count"),
            "request_pose_graph_largest_component_fraction": pose_graph.get("largest_component_fraction"),
            "request_pose_graph_edge_count": pose_graph.get("edge_count"),
            "request_pose_graph_edge_reason_counts": pose_graph.get("edge_reason_counts"),
            "strict_pose_spatial_proxy_ready": pose_spatial.get("proxy_ready"),
            "strict_pose_spatial_connected_component_count": pose_spatial.get("connected_component_count"),
            "strict_pose_loop_proxy_ready": pose_loop.get("proxy_ready"),
            "selector_evidence": "candidate_frame_pose_projection_navmesh_geometry_only",
            "uses_semantic_or_detector_shortcut": False,
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        }
        if not candidates:
            row.update(
                {
                    "selector_action": "selector_missing",
                    "policy_selected_candidate_id": None,
                    "terminal_commit_proxy": None,
                    "selector_missing": True,
                    "selector_missing_reason": "candidate_feature_rows_not_materialized",
                }
            )
            failure_rows.append(
                make_failure(
                    row,
                    "candidate_geometry_missing",
                    "No candidate feature row could be materialized for this source request.",
                )
            )
        elif len(ready_candidates) == 1:
            selected = str(ready_candidates[0].get("candidate_id") or "")
            row.update(
                {
                    "selector_action": "commit_candidate",
                    "policy_selected_candidate_id": selected,
                    "terminal_commit_proxy": True,
                    "selector_missing": False,
                    "selector_missing_reason": None,
                }
            )
            if row["single_candidate_pool_geometry_only"]:
                failure_rows.append(
                    make_failure(
                        row,
                        "single_candidate_pool_geometry_only",
                        "Single-candidate pool selected because geometry is ready; this is diagnostic only.",
                    )
                )
        elif len(ready_candidates) == 0:
            row.update(
                {
                    "selector_action": "defer",
                    "policy_selected_candidate_id": None,
                    "terminal_commit_proxy": False,
                    "selector_missing": False,
                    "selector_missing_reason": "no_candidate_map_pose_ready",
                }
            )
            failure_rows.append(
                make_failure(
                    row,
                    "no_candidate_map_pose_ready",
                    "No candidate has enough candidate-specific frame, pose, projection, and navmesh evidence.",
                )
            )
        else:
            row.update(
                {
                    "selector_action": "defer",
                    "policy_selected_candidate_id": None,
                    "terminal_commit_proxy": False,
                    "selector_missing": False,
                    "selector_missing_reason": "multiple_map_pose_ready_candidates",
                }
            )
            failure_rows.append(
                make_failure(
                    row,
                    "multiple_map_pose_ready_candidates",
                    "Candidate-specific map/pose evidence is available but not discriminative across candidates.",
                )
            )
        request_rows.append(row)
    return request_rows, failure_rows


def build_summary(
    contract: Mapping[str, Any],
    source_inventory_rows: Sequence[Mapping[str, Any]],
    source_request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    failure_rows: Sequence[Mapping[str, Any]],
    source_forbidden_counts: Mapping[str, int],
    out_root: Path,
) -> Dict[str, Any]:
    expected = contract.get("expected_materializer_counts")
    expected = expected if isinstance(expected, Mapping) else {}
    all_output_rows = [*candidate_rows, *request_rows, *failure_rows]
    forbidden_keys = scan_forbidden_keys(all_output_rows)
    selector_missing_rows = sum(1 for row in request_rows if row.get("selector_missing") is True)
    actual_counts = {
        "source_inventory_rows": len(source_inventory_rows),
        "source_request_rows": len(source_request_rows),
        "candidate_feature_rows": len(candidate_rows),
        "request_selector_rows": len(request_rows),
        "SLAMOnlyRich_current_request_rows": sum(1 for row in request_rows if row.get("policy_name") == POLICY_NAME),
        "selector_missing_rows": selector_missing_rows,
        "commit_candidate_rows": sum(1 for row in request_rows if row.get("selector_action") == "commit_candidate"),
        "defer_rows": sum(1 for row in request_rows if row.get("selector_action") == "defer"),
        "no_candidate_map_pose_ready_rows": sum(
            1 for row in request_rows if row.get("selector_missing_reason") == "no_candidate_map_pose_ready"
        ),
        "multiple_map_pose_ready_candidates_rows": sum(
            1 for row in request_rows if row.get("selector_missing_reason") == "multiple_map_pose_ready_candidates"
        ),
        "single_candidate_pool_geometry_only_rows": sum(
            1 for row in request_rows if row.get("single_candidate_pool_geometry_only") is True
        ),
        "candidate_geometry_missing_rows": sum(1 for row in candidate_rows if row.get("candidate_geometry_missing") is True),
        "strict_candidate_map_pose_ready_rows": sum(
            1 for row in candidate_rows if row.get("strict_candidate_map_pose_ready") is True
        ),
        "failure_rows": len(failure_rows),
        "action_evidence_forbidden_key_count": len(forbidden_keys),
    }
    expected_count_mismatches: Dict[str, Dict[str, Any]] = {}
    for key, expected_value in expected.items():
        if key == "selector_missing_rows_max":
            if selector_missing_rows > safe_int(expected_value):
                expected_count_mismatches[key] = {"expected_max": expected_value, "actual": selector_missing_rows}
            continue
        if key in {"uses_gt_for_action", "paper_claim_allowed"}:
            continue
        if actual_counts.get(key) != expected_value:
            expected_count_mismatches[key] = {"expected": expected_value, "actual": actual_counts.get(key)}
    uses_gt_for_action = any(row.get("uses_gt_for_action") is True for row in all_output_rows)
    paper_claim_allowed = any(row.get("paper_claim_allowed") is True for row in all_output_rows)
    if uses_gt_for_action != bool(expected.get("uses_gt_for_action", False)):
        expected_count_mismatches["uses_gt_for_action"] = {
            "expected": expected.get("uses_gt_for_action", False),
            "actual": uses_gt_for_action,
        }
    if paper_claim_allowed != bool(expected.get("paper_claim_allowed", False)):
        expected_count_mismatches["paper_claim_allowed"] = {
            "expected": expected.get("paper_claim_allowed", False),
            "actual": paper_claim_allowed,
        }
    candidate_map_pose_feature_gate_passed = not expected_count_mismatches and not forbidden_keys
    ready_dist = Counter(row.get("ready_candidate_count") for row in request_rows)
    candidate_dist = Counter(row.get("candidate_count") for row in request_rows)
    failure_counter = Counter(row.get("failure_tag") for row in failure_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "contract": CONTRACT_DEFAULT,
        "output_root": str(out_root),
        "row_files": {
            "candidate_rows": "semantic_slam_candidate_map_pose_selector_candidate_rows.jsonl",
            "request_rows": "semantic_slam_candidate_map_pose_selector_request_rows.jsonl",
            "failure_rows": "semantic_slam_candidate_map_pose_selector_failure_rows.jsonl",
            "summary": "semantic_slam_candidate_map_pose_selector_summary.json",
        },
        "status": "materialized",
        "actual_counts": actual_counts,
        "expected_materializer_counts": dict(expected),
        "expected_count_mismatches": expected_count_mismatches,
        "candidate_count_distribution": dict(sorted((str(k), v) for k, v in candidate_dist.items())),
        "ready_candidate_count_distribution": dict(sorted((str(k), v) for k, v in ready_dist.items())),
        "selector_action_counts": compact_counter(row.get("selector_action") for row in request_rows),
        "selector_missing_reason_counts": compact_counter(row.get("selector_missing_reason") for row in request_rows),
        "failure_taxonomy": dict(sorted(failure_counter.items())),
        "source_family_rows": compact_counter(row.get("source_family") for row in request_rows),
        "source_semantic_detector_like_fields_present_but_not_consumed": dict(source_forbidden_counts),
        "action_evidence_forbidden_keys": forbidden_keys,
        "candidate_map_pose_feature_gate_passed": candidate_map_pose_feature_gate_passed,
        "task_proxy_join_after_candidate_selector_allowed": candidate_map_pose_feature_gate_passed,
        "revised_slam_formula_allowed": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "uses_gt_for_action": False,
        "primary_blocker": "multiple_map_pose_ready_candidates"
        if actual_counts["multiple_map_pose_ready_candidates_rows"]
        else None,
        "interpretation": {
            "fact": (
                "The materializer writes candidate-level map/pose feature rows and one conservative "
                "SLAMOnlyRich_current selector row for each source request."
            ),
            "agent_inference": (
                "Candidate-specific map/pose evidence is available, but most requests remain ambiguous; "
                "the next safe step is a task-proxy join, not a SLAMOnlyRich formula revision."
            ),
            "paper_claim": (
                "No ObjectNav, SLAM, SemanticSLAM complementarity, Step 4-5, formula revision, terminal "
                "utility, first_eval, policy-scale, or paper claim is allowed from this materializer."
            ),
        },
        "next_task": "join_task_proxies_after_candidate_specific_slam_map_pose_selector",
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")
    source_inventory_rows = load_jsonl(Path(str(source["source_inventory_rows"])))
    source_request_rows = load_jsonl(Path(str(source["source_request_rows"])))
    pose_graph_rows = load_jsonl(Path(str(source["request_level_pose_graph_rows"])))
    strict_edge_rows = load_jsonl(Path(str(source["strict_edge_variant_rows"])))
    projection_index = load_projection_rows(source_inventory_rows)
    candidate_rows, candidate_by_request, source_forbidden_counts = build_candidate_rows(source_inventory_rows, projection_index)
    request_rows, failure_rows = materialize_request_rows(
        source_request_rows,
        candidate_by_request,
        pose_graph_rows,
        strict_edge_rows,
    )
    summary = build_summary(
        contract,
        source_inventory_rows,
        source_request_rows,
        candidate_rows,
        request_rows,
        failure_rows,
        source_forbidden_counts,
        out_root,
    )
    write_jsonl(out_root / "semantic_slam_candidate_map_pose_selector_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "semantic_slam_candidate_map_pose_selector_request_rows.jsonl", request_rows)
    write_jsonl(out_root / "semantic_slam_candidate_map_pose_selector_failure_rows.jsonl", failure_rows)
    write_json(out_root / "semantic_slam_candidate_map_pose_selector_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize candidate-specific Semantic-SLAM map/pose selector rows.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
