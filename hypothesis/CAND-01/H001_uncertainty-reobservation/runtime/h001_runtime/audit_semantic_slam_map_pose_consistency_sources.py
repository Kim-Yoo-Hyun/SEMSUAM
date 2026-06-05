import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_map_pose_consistency_source_audit.v1"
POLICY_NAME = "semantic_slam_map_pose_consistency_source_audit_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_map_pose_consistency_probe_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_map_pose_consistency_probe_v1"

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
    "shortest_path_distance",
    "target_label",
}

FILE_KEYS = ("rgb", "depth", "pose", "metadata")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_json_if_exists(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    return load_json(path)


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
    if not math.isfinite(result):
        return default
    return result


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [float(value) for value in (safe_float(item) for item in values) if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {
        "count": len(nums),
        "min": min(nums),
        "mean": sum(nums) / len(nums),
        "max": max(nums),
    }


def finite_position(value: Any) -> Optional[Tuple[float, float, float]]:
    if not isinstance(value, list) or len(value) < 3:
        return None
    coords: List[float] = []
    for item in value[:3]:
        coord = safe_float(item)
        if coord is None:
            return None
        coords.append(coord)
    return (coords[0], coords[1], coords[2])


def distance_xz(a: Tuple[float, float, float], b: Tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2)


def round_position_key(value: Optional[Tuple[float, float, float]]) -> Optional[str]:
    if value is None:
        return None
    return f"{value[0]:.3f},{value[1]:.3f},{value[2]:.3f}"


def action_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
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


def source_definitions(contract: Mapping[str, Any]) -> List[Dict[str, Any]]:
    source = contract.get("source") or {}
    definitions: List[Dict[str, Any]] = []
    primary = dict(source.get("primary_frame_source") or {})
    if primary:
        primary["source_role"] = "primary"
        definitions.append(primary)
    for support in source.get("support_frame_sources") or []:
        item = dict(support)
        item["source_role"] = "support"
        definitions.append(item)
    return definitions


def frame_output_path(source: Mapping[str, Any]) -> Path:
    return Path(str(source.get("frame_output") or ""))


def source_path(source: Mapping[str, Any], key: str) -> Path:
    return Path(str(source.get(key) or ""))


def heading_file_path(frame_output: Path, value: Any) -> Path:
    path = Path(str(value))
    if path.is_absolute():
        return path
    return frame_output / path


def count_actual_files(frame_output: Path) -> Dict[str, int]:
    frames = frame_output / "frames"
    if not frames.exists():
        return {key: 0 for key in FILE_KEYS}
    return {
        "rgb": sum(1 for _ in frames.rglob("rgb.png")),
        "depth": sum(1 for _ in frames.rglob("depth.npy")),
        "pose": sum(1 for _ in frames.rglob("pose.txt")),
        "metadata": sum(1 for _ in frames.rglob("metadata.json")),
    }


def heading_ref_stats(frame_output: Path, rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    total_headings = 0
    existing = {key: 0 for key in FILE_KEYS}
    missing = {key: 0 for key in FILE_KEYS}
    missing_preview: List[Dict[str, str]] = []
    for row in rows:
        for heading in row.get("rendered_headings") or []:
            total_headings += 1
            for key in FILE_KEYS:
                value = heading.get(key)
                if not value:
                    missing[key] += 1
                    if len(missing_preview) < 10:
                        missing_preview.append(
                            {
                                "missing_type": "missing_reference",
                                "file_key": key,
                                "decision_id": str(row.get("decision_id") or ""),
                                "heading_id": str(heading.get("heading_id") or ""),
                            }
                        )
                    continue
                path = heading_file_path(frame_output, value)
                if path.exists():
                    existing[key] += 1
                else:
                    missing[key] += 1
                    if len(missing_preview) < 10:
                        missing_preview.append(
                            {
                                "missing_type": "missing_file",
                                "file_key": key,
                                "relative_path": str(value),
                                "decision_id": str(row.get("decision_id") or ""),
                                "heading_id": str(heading.get("heading_id") or ""),
                            }
                        )
    return {
        "rendered_heading_ref_count": total_headings,
        "heading_existing_file_counts": existing,
        "heading_missing_file_counts": missing,
        "heading_missing_file_preview": missing_preview,
        "all_heading_refs_exist": all(missing[key] == 0 for key in FILE_KEYS),
    }


def row_request_id(row: Mapping[str, Any]) -> str:
    for key in (
        "expanded_retrieval_request_id",
        "rival_identity_request_id",
        "goal_validity_request_id",
        "request_id",
        "decision_id",
        "episode_key",
    ):
        value = row.get(key)
        if value:
            return str(value)
    return "unknown_request"


def row_candidate_ids(row: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for value in row.get("candidate_ids") or []:
        if value is not None:
            ids.append(str(value))
    for key in (
        "candidate_id",
        "target_candidate_id",
        "focus_candidate_id",
        "rival_candidate_id",
        "second_observation_candidate_id",
        "second_observation_alt_candidate_id",
        "standoff_relation_anchor_candidate_id",
    ):
        value = row.get(key)
        if value is not None and str(value) != "":
            ids.append(str(value))
    return sorted(set(ids))


def semantic_family_for_source(source_name: str) -> str:
    if "instance_arbitration" in source_name:
        return "instance_arbitration_defer_v1"
    if "missing_own_view" in source_name:
        return "missing_own_view_support_recheck"
    if "partial_relation_depth" in source_name:
        return "partial_relation_depth_true_goal"
    if "object_relation" in source_name:
        return "object_relation_goal_validity_confirmation"
    if "expanded_retrieval" in source_name or "local_context" in source_name:
        return "expanded_retrieval_source_pool"
    return "unknown_semantic_uncertainty_family"


def read_source(source: Mapping[str, Any]) -> Dict[str, Any]:
    frame_output = frame_output_path(source)
    frame_summary_path = source_path(source, "frame_summary")
    frame_rows_path = source_path(source, "frame_rows")
    nonblank_summary_path = source_path(source, "nonblank_summary")
    projection_summary_path = source_path(source, "projection_summary")
    rows = load_jsonl(frame_rows_path)
    frame_summary = load_json_if_exists(frame_summary_path)
    nonblank_summary = load_json_if_exists(nonblank_summary_path)
    projection_summary = load_json_if_exists(projection_summary_path)
    return {
        "source": source,
        "frame_output": frame_output,
        "frame_summary_path": frame_summary_path,
        "frame_rows_path": frame_rows_path,
        "nonblank_summary_path": nonblank_summary_path,
        "projection_summary_path": projection_summary_path,
        "frame_summary": frame_summary,
        "nonblank_summary": nonblank_summary,
        "projection_summary": projection_summary,
        "rows": rows,
    }


def source_uses_gt_for_action(
    rows: Sequence[Mapping[str, Any]],
    frame_summary: Mapping[str, Any],
    nonblank_summary: Mapping[str, Any],
    projection_summary: Mapping[str, Any],
) -> bool:
    if frame_summary.get("uses_gt_for_action") is True:
        return True
    if nonblank_summary.get("uses_gt_for_action") is True:
        return True
    if projection_summary.get("uses_gt_for_action") is True:
        return True
    return any(row.get("uses_gt_for_action") is True for row in rows)


def nonblank_gate_passed(summary: Mapping[str, Any]) -> bool:
    if not summary:
        return False
    if summary.get("row_level_nonblank_gate_passed") is True:
        return True
    if summary.get("nonblank_row_level_gate_passed") is True:
        return True
    if summary.get("gate") and (summary.get("gate") or {}).get("row_level_nonblank_gate_passed") is True:
        return True
    return False


def projection_gate_passed(summary: Mapping[str, Any]) -> bool:
    if not summary:
        return False
    if (summary.get("gate") or {}).get("projection_anchor_smoke_passed") is True:
        return True
    if summary.get("projection_anchor_smoke_passed") is True:
        return True
    return False


def output_row_count(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> int:
    for key in ("rows_exported", "output_rows", "rows", "expected_rows"):
        if summary.get(key) is not None:
            return safe_int(summary.get(key), len(rows))
    return len(rows)


def rendered_heading_count(summary: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> int:
    if summary.get("rendered_heading_count") is not None:
        return safe_int(summary.get("rendered_heading_count"), 0)
    if summary.get("kept_heading_count") is not None:
        return safe_int(summary.get("kept_heading_count"), 0)
    return sum(len(row.get("rendered_headings") or []) for row in rows)


def build_inventory_row(
    *,
    source_data: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> Dict[str, Any]:
    source = source_data["source"]
    source_name = str(source.get("name") or "unknown_source")
    source_role = str(source.get("source_role") or "support")
    frame_output = source_data["frame_output"]
    frame_summary = source_data["frame_summary"]
    nonblank_summary = source_data["nonblank_summary"]
    projection_summary = source_data["projection_summary"]
    rows = source_data["rows"]
    actual_counts = count_actual_files(frame_output)
    ref_stats = heading_ref_stats(frame_output, rows)
    row_count = output_row_count(frame_summary, rows)
    heading_count = rendered_heading_count(frame_summary, rows)
    uses_gt = source_uses_gt_for_action(rows, frame_summary, nonblank_summary, projection_summary)
    row_level_nonblank = nonblank_gate_passed(nonblank_summary)
    projection_ok = projection_gate_passed(projection_summary)
    pose_depth_metadata_ready = (
        ref_stats["all_heading_refs_exist"]
        and actual_counts["rgb"] >= ref_stats["rendered_heading_ref_count"]
        and actual_counts["depth"] >= ref_stats["rendered_heading_ref_count"]
        and actual_counts["pose"] >= ref_stats["rendered_heading_ref_count"]
        and actual_counts["metadata"] >= ref_stats["rendered_heading_ref_count"]
    )
    source_ready = (
        bool(frame_output.exists())
        and bool(source_data["frame_rows_path"].exists())
        and len(rows) > 0
        and heading_count > 0
        and pose_depth_metadata_ready
        and row_level_nonblank
        and projection_ok
        and not uses_gt
    )
    required = contract.get("probe_contract") or {}
    primary_min_rows = safe_int(required.get("primary_source_min_frame_rows"), 0)
    primary_min_headings = safe_int(required.get("primary_source_min_rendered_headings"), 0)
    primary_contract_ready: Optional[bool] = None
    if source_role == "primary":
        primary_contract_ready = (
            source_ready
            and row_count >= primary_min_rows
            and heading_count >= primary_min_headings
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_semantic_slam_source_inventory",
        "row_type": "source_inventory",
        "policy": POLICY_NAME,
        "source_name": source_name,
        "source_role": source_role,
        "semantic_uncertainty_family": semantic_family_for_source(source_name),
        "frame_output": str(frame_output),
        "frame_output_exists": frame_output.exists(),
        "frame_summary": str(source_data["frame_summary_path"]),
        "frame_summary_exists": source_data["frame_summary_path"].exists(),
        "frame_rows": str(source_data["frame_rows_path"]),
        "frame_rows_exists": source_data["frame_rows_path"].exists(),
        "nonblank_summary": str(source_data["nonblank_summary_path"]),
        "nonblank_summary_exists": source_data["nonblank_summary_path"].exists(),
        "projection_summary": str(source_data["projection_summary_path"]),
        "projection_summary_exists": source_data["projection_summary_path"].exists(),
        "frame_rows_loaded": len(rows),
        "frame_rows_reported": row_count,
        "rendered_heading_count": heading_count,
        "rendered_heading_ref_count": ref_stats["rendered_heading_ref_count"],
        "unique_scene_count": len(frame_summary.get("unique_scenes") or sorted({row.get("scene_key") for row in rows if row.get("scene_key")})),
        "unique_query_count": len(sorted({str(row.get("query")) for row in rows if row.get("query")})),
        "actual_file_counts": actual_counts,
        "heading_existing_file_counts": ref_stats["heading_existing_file_counts"],
        "heading_missing_file_counts": ref_stats["heading_missing_file_counts"],
        "heading_missing_file_preview": ref_stats["heading_missing_file_preview"],
        "pose_depth_metadata_ready": pose_depth_metadata_ready,
        "nonblank_row_level_gate_passed": row_level_nonblank,
        "strict_no_blank_heading_gate_passed": nonblank_summary.get("strict_no_blank_heading_gate_passed"),
        "removed_blank_heading_count": safe_int(nonblank_summary.get("removed_blank_heading_count"), 0),
        "dropped_rows": safe_int(nonblank_summary.get("dropped_rows"), 0),
        "projection_anchor_smoke_passed": projection_ok,
        "projection_anchor_visible_rows": safe_int(projection_summary.get("projection_anchor_visible_rows"), 0),
        "projection_anchor_visible_rate": projection_summary.get("projection_anchor_visible_rate"),
        "projection_missing_candidate_rows": safe_int(projection_summary.get("missing_candidate_rows"), 0),
        "projection_reported_action_label_rows": safe_int(projection_summary.get("gt_action_rows"), 0),
        "uses_gt_for_action": uses_gt,
        "source_ready_for_pose_graph_proxy": source_ready,
        "primary_contract_ready": primary_contract_ready,
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "paper_claim_allowed": False,
    }


def request_group_key(source_name: str, row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    return (
        source_name,
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        row_request_id(row),
        str(row.get("episode_key") or ""),
    )


def build_request_rows(
    *,
    source_payloads: Sequence[Mapping[str, Any]],
    inventory_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    ready_sources = {
        str(row.get("source_name"))
        for row in inventory_rows
        if row.get("source_ready_for_pose_graph_proxy") is True
    }
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    source_roles: Dict[str, str] = {}
    source_families: Dict[str, str] = {}
    for payload in source_payloads:
        source = payload["source"]
        source_name = str(source.get("name") or "unknown_source")
        if source_name not in ready_sources:
            continue
        source_roles[source_name] = str(source.get("source_role") or "support")
        source_families[source_name] = semantic_family_for_source(source_name)
        for row in payload["rows"]:
            grouped[request_group_key(source_name, row)].append(row)

    request_rows: List[Dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        source_name, scene_key, query, request_id, episode_key = key
        candidate_ids = sorted({candidate_id for row in rows for candidate_id in row_candidate_ids(row)})
        positions = [finite_position(row.get("physical_viewpoint_position")) for row in rows]
        target_positions = [finite_position(row.get("target_position")) for row in rows]
        rendered_headings = [heading for row in rows for heading in (row.get("rendered_headings") or [])]
        request_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_semantic_slam_probe_request",
                "row_type": "probe_request",
                "policy": POLICY_NAME,
                "source_name": source_name,
                "source_role": source_roles.get(source_name),
                "semantic_uncertainty_family": source_families.get(source_name),
                "scene_key": scene_key,
                "scene_id": next((row.get("scene_id") for row in rows if row.get("scene_id")), None),
                "query": query,
                "request_id": request_id,
                "episode_key": episode_key,
                "frame_row_count": len(rows),
                "rendered_heading_count": len(rendered_headings),
                "position_ready_row_count": sum(1 for position in positions if position is not None),
                "target_position_ready_row_count": sum(1 for position in target_positions if position is not None),
                "unique_viewpoint_count": len({round_position_key(position) for position in positions if position is not None}),
                "view_role_counts": compact_counter(row.get("view_role") for row in rows),
                "viewpoint_source_counts": compact_counter(row.get("viewpoint_source") for row in rows),
                "candidate_id_count": len(candidate_ids),
                "candidate_ids_preview": candidate_ids[:20],
                "candidate_set_rule_counts": compact_counter(row.get("candidate_set_rule") for row in rows),
                "target_distance_from_viewpoint_m": number_stats(row.get("target_distance_from_viewpoint_m") for row in rows),
                "standoff_distance_requested_m": number_stats(row.get("standoff_distance_requested") for row in rows),
                "travel_cost_proxy_m": number_stats(row.get("target_distance_from_viewpoint_m") for row in rows),
                "probe_request_ready": len(rows) > 0 and any(position is not None for position in positions),
                "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in rows),
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "paper_claim_allowed": False,
            }
        )
    return request_rows


def build_nodes(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    nodes: List[Dict[str, Any]] = []
    for index, row in enumerate(rows):
        viewpoint = finite_position(row.get("physical_viewpoint_position"))
        if viewpoint is None:
            continue
        target = finite_position(row.get("target_position"))
        nodes.append(
            {
                "node_index": len(nodes),
                "source_row_index": index,
                "viewpoint_id": row.get("viewpoint_id"),
                "decision_id": row.get("decision_id"),
                "view_role": row.get("view_role"),
                "viewpoint_source": row.get("viewpoint_source"),
                "viewpoint_position": viewpoint,
                "target_position": target,
                "candidate_ids": row_candidate_ids(row),
                "target_distance_from_viewpoint_m": safe_float(row.get("target_distance_from_viewpoint_m")),
            }
        )
    return nodes


def connected_component_sizes(node_count: int, edges: Sequence[Tuple[int, int]]) -> List[int]:
    adjacency: Dict[int, List[int]] = {index: [] for index in range(node_count)}
    for a, b in edges:
        adjacency[a].append(b)
        adjacency[b].append(a)
    seen: set[int] = set()
    sizes: List[int] = []
    for start in range(node_count):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            node = stack.pop()
            size += 1
            for neighbor in adjacency[node]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    return sorted(sizes, reverse=True)


def graph_proxy_for_group(
    *,
    source_name: str,
    source_role: str,
    semantic_family: str,
    key: Tuple[str, str, str, str, str],
    rows: Sequence[Mapping[str, Any]],
    spatial_threshold_m: float,
    target_neighborhood_threshold_m: float,
    loop_closure_threshold_m: float,
) -> Dict[str, Any]:
    _, scene_key, query, request_id, episode_key = key
    nodes = build_nodes(rows)
    edge_reasons: Dict[Tuple[int, int], set[str]] = defaultdict(set)
    loop_edges: set[Tuple[int, int]] = set()
    for i, left in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            right = nodes[j]
            viewpoint_distance = distance_xz(left["viewpoint_position"], right["viewpoint_position"])
            if viewpoint_distance <= spatial_threshold_m:
                edge_reasons[(i, j)].add("spatial_proximity")
            if viewpoint_distance <= loop_closure_threshold_m:
                loop_edges.add((i, j))
                edge_reasons[(i, j)].add("loop_closure_opportunity")
            left_candidates = set(left["candidate_ids"])
            right_candidates = set(right["candidate_ids"])
            if left_candidates and right_candidates and left_candidates & right_candidates:
                edge_reasons[(i, j)].add("candidate_id_overlap")
            left_target = left.get("target_position")
            right_target = right.get("target_position")
            if left_target is not None and right_target is not None:
                target_distance = distance_xz(left_target, right_target)
                if target_distance <= target_neighborhood_threshold_m:
                    edge_reasons[(i, j)].add("target_position_neighborhood")

    edges = sorted(edge_reasons.keys())
    component_sizes = connected_component_sizes(len(nodes), edges) if nodes else []
    largest = component_sizes[0] if component_sizes else 0
    edge_reason_counts = Counter()
    for reasons in edge_reasons.values():
        for reason in reasons:
            edge_reason_counts[reason] += 1
    travel_values = [node["target_distance_from_viewpoint_m"] for node in nodes if node["target_distance_from_viewpoint_m"] is not None]
    edge_count = len(edges)
    node_count = len(nodes)
    proxy_ready = node_count >= 2 and edge_count >= 1
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_semantic_slam_pose_graph_connectivity_proxy",
        "row_type": "pose_graph_proxy",
        "policy": POLICY_NAME,
        "proxy_name": "pose_graph_connectivity_proxy_v1",
        "source_name": source_name,
        "source_role": source_role,
        "semantic_uncertainty_family": semantic_family,
        "scene_key": scene_key,
        "scene_id": next((row.get("scene_id") for row in rows if row.get("scene_id")), None),
        "query": query,
        "request_id": request_id,
        "episode_key": episode_key,
        "node_definition": "row_level_camera_pose_from_label_free_reobservation_artifact",
        "edge_definition": [
            "same_request_same_scene_spatial_proximity",
            "candidate_id_overlap",
            "target_position_neighborhood",
            "loop_closure_opportunity_proxy",
        ],
        "spatial_proximity_threshold_m": spatial_threshold_m,
        "target_neighborhood_threshold_m": target_neighborhood_threshold_m,
        "loop_closure_threshold_m": loop_closure_threshold_m,
        "node_count": node_count,
        "edge_count": edge_count,
        "connected_component_count": len(component_sizes),
        "component_sizes": component_sizes,
        "largest_component_fraction": None if node_count == 0 else largest / node_count,
        "mean_degree": None if node_count == 0 else (2.0 * edge_count) / node_count,
        "loop_closure_opportunity_edge_count": len(loop_edges),
        "edge_reason_counts": dict(sorted(edge_reason_counts.items())),
        "candidate_id_count": len({candidate_id for row in rows for candidate_id in row_candidate_ids(row)}),
        "view_role_counts": compact_counter(row.get("view_role") for row in rows),
        "viewpoint_source_counts": compact_counter(row.get("viewpoint_source") for row in rows),
        "travel_cost_proxy_m": number_stats(travel_values),
        "optional_lambda2": None,
        "proxy_ready": proxy_ready,
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in rows),
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "paper_claim_allowed": False,
    }


def build_pose_graph_rows(
    *,
    source_payloads: Sequence[Mapping[str, Any]],
    inventory_rows: Sequence[Mapping[str, Any]],
    spatial_threshold_m: float,
    target_neighborhood_threshold_m: float,
    loop_closure_threshold_m: float,
) -> List[Dict[str, Any]]:
    inventory_by_source = {str(row.get("source_name")): row for row in inventory_rows}
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    source_roles: Dict[str, str] = {}
    source_families: Dict[str, str] = {}
    for payload in source_payloads:
        source = payload["source"]
        source_name = str(source.get("name") or "unknown_source")
        inventory = inventory_by_source.get(source_name) or {}
        if inventory.get("source_ready_for_pose_graph_proxy") is not True:
            continue
        source_roles[source_name] = str(source.get("source_role") or "support")
        source_families[source_name] = semantic_family_for_source(source_name)
        for row in payload["rows"]:
            grouped[request_group_key(source_name, row)].append(row)

    proxy_rows: List[Dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        source_name = key[0]
        proxy_rows.append(
            graph_proxy_for_group(
                source_name=source_name,
                source_role=source_roles.get(source_name, "support"),
                semantic_family=source_families.get(source_name, "unknown_semantic_uncertainty_family"),
                key=key,
                rows=rows,
                spatial_threshold_m=spatial_threshold_m,
                target_neighborhood_threshold_m=target_neighborhood_threshold_m,
                loop_closure_threshold_m=loop_closure_threshold_m,
            )
        )
    return proxy_rows


def summarize(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    inventory_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    pose_graph_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    primary_rows = [row for row in inventory_rows if row.get("source_role") == "primary"]
    primary_ready = any(row.get("primary_contract_ready") is True for row in primary_rows)
    pose_depth_metadata_ready = any(row.get("pose_depth_metadata_ready") is True for row in primary_rows)
    non_gt_action_gate = all(row.get("uses_gt_for_action") is False for row in inventory_rows)
    forbidden = action_forbidden_keys(list(inventory_rows) + list(request_rows) + list(pose_graph_rows))
    probe_contract = contract.get("probe_contract") or {}
    success_condition = probe_contract.get("success_condition_for_source_audit") or {}
    proxy_ready_rows = [row for row in pose_graph_rows if row.get("proxy_ready") is True]
    max_node_count = max([safe_int(row.get("node_count"), 0) for row in pose_graph_rows] or [0])
    max_edge_count = max([safe_int(row.get("edge_count"), 0) for row in pose_graph_rows] or [0])
    source_audit_gate = {
        "source_inventory_rows_minimum_passed": len(inventory_rows)
        >= safe_int(success_condition.get("source_inventory_rows_minimum"), 1),
        "primary_source_ready_passed": primary_ready is bool(success_condition.get("primary_source_ready", True)),
        "pose_depth_metadata_ready_passed": pose_depth_metadata_ready
        is bool(success_condition.get("pose_depth_metadata_ready", True)),
        "non_gt_action_gate_passed": non_gt_action_gate is bool(success_condition.get("non_gt_action_gate", True)),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int((contract.get("source_gate") or {}).get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": 0 <= safe_int((contract.get("source_gate") or {}).get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": 0 <= safe_int((contract.get("source_gate") or {}).get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": 0
        <= safe_int((contract.get("source_gate") or {}).get("max_candidate_rejection_rows"), 0),
        "paper_claim_allowed": False,
    }
    source_audit_gate["semantic_slam_map_pose_source_audit_gate_passed"] = all(
        value is True
        for key, value in source_audit_gate.items()
        if key != "paper_claim_allowed"
    )
    p4_proxy_gate = {
        "pose_graph_proxy_rows_present_passed": len(pose_graph_rows) > 0,
        "pose_graph_proxy_ready_rows_present_passed": len(proxy_ready_rows) > 0,
        "pose_graph_proxy_node_count_nonzero_passed": max_node_count > 0,
        "pose_graph_proxy_edge_count_nonzero_passed": max_edge_count > 0,
        "p4_proxy_readiness_gate_passed": len(proxy_ready_rows) > 0 and max_node_count > 0 and max_edge_count > 0,
        "step_4_5_promotion_satisfied": False,
        "paper_claim_allowed": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "date_checked": "2026-06-04",
        "status": "implemented_source_audit_and_pose_graph_proxy_rows",
        "stage": "P4-design",
        "step_4_5_promotion_satisfied": False,
        "source_inventory_rows": len(inventory_rows),
        "source_ready_rows": sum(1 for row in inventory_rows if row.get("source_ready_for_pose_graph_proxy") is True),
        "primary_source_ready": primary_ready,
        "pose_depth_metadata_ready": pose_depth_metadata_ready,
        "non_gt_action_gate": non_gt_action_gate,
        "probe_request_rows": len(request_rows),
        "probe_request_ready_rows": sum(1 for row in request_rows if row.get("probe_request_ready") is True),
        "pose_graph_proxy_rows": len(pose_graph_rows),
        "pose_graph_proxy_ready_rows": len(proxy_ready_rows),
        "pose_graph_proxy_max_node_count": max_node_count,
        "pose_graph_proxy_max_edge_count": max_edge_count,
        "pose_graph_proxy_source_counts": compact_counter(row.get("source_name") for row in pose_graph_rows),
        "pose_graph_proxy_semantic_family_counts": compact_counter(
            row.get("semantic_uncertainty_family") for row in pose_graph_rows
        ),
        "pose_graph_proxy_ready_source_counts": compact_counter(row.get("source_name") for row in proxy_ready_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden,
        "terminal_commit_rows": 0,
        "candidate_commit_rows": 0,
        "candidate_rejection_rows": 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "gate": {
            "source_audit": source_audit_gate,
            "p4_proxy_readiness": p4_proxy_gate,
        },
        "diagnostic_conclusion": {
            "recommended_next_task": "define_semantic_slam_pose_graph_connectivity_proxy_gate",
            "source_audit_gate_passed": source_audit_gate["semantic_slam_map_pose_source_audit_gate_passed"],
            "p4_proxy_readiness_gate_passed": p4_proxy_gate["p4_proxy_readiness_gate_passed"],
            "terminal_policy_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": {
            "fact": (
                "The source audit inventories existing label-free RGB/depth/pose/metadata frame artifacts "
                "and writes row-level pose graph connectivity proxy rows."
            ),
            "agent_inference": (
                "Existing artifacts are sufficient to define a first pose-graph connectivity proxy gate, "
                "but this remains P4-design plumbing rather than a SLAM utility or paper claim."
            ),
            "paper_claim": "No SLAM benefit or policy utility claim is allowed from this source audit alone.",
        },
        "output_files": {
            "source_inventory_rows": "semantic_slam_map_pose_source_inventory_rows.jsonl",
            "probe_request_rows": "semantic_slam_map_pose_probe_request_rows.jsonl",
            "pose_graph_proxy_rows": "semantic_slam_map_pose_graph_proxy_rows.jsonl",
            "summary": "semantic_slam_map_pose_consistency_probe_summary.json",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--spatial-proximity-threshold-m", type=float, default=2.0)
    parser.add_argument("--target-neighborhood-threshold-m", type=float, default=1.0)
    parser.add_argument("--loop-closure-threshold-m", type=float, default=0.75)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    args.contract = Path(args.contract)
    args.out_root = Path(args.out_root)
    contract = load_json(args.contract)
    source_payloads = [read_source(source) for source in source_definitions(contract)]
    inventory_rows = [
        build_inventory_row(source_data=source_payload, contract=contract)
        for source_payload in source_payloads
    ]
    request_rows = build_request_rows(source_payloads=source_payloads, inventory_rows=inventory_rows)
    pose_graph_rows = build_pose_graph_rows(
        source_payloads=source_payloads,
        inventory_rows=inventory_rows,
        spatial_threshold_m=float(args.spatial_proximity_threshold_m),
        target_neighborhood_threshold_m=float(args.target_neighborhood_threshold_m),
        loop_closure_threshold_m=float(args.loop_closure_threshold_m),
    )
    summary = summarize(
        args=args,
        contract=contract,
        inventory_rows=inventory_rows,
        request_rows=request_rows,
        pose_graph_rows=pose_graph_rows,
    )
    outputs = contract.get("required_future_outputs") or {}
    write_jsonl(
        args.out_root / str(outputs.get("source_inventory_rows", "semantic_slam_map_pose_source_inventory_rows.jsonl")),
        inventory_rows,
    )
    write_jsonl(
        args.out_root / str(outputs.get("probe_request_rows", "semantic_slam_map_pose_probe_request_rows.jsonl")),
        request_rows,
    )
    write_jsonl(
        args.out_root / str(outputs.get("pose_graph_proxy_rows", "semantic_slam_map_pose_graph_proxy_rows.jsonl")),
        pose_graph_rows,
    )
    write_json(
        args.out_root / str(outputs.get("summary", "semantic_slam_map_pose_consistency_probe_summary.json")),
        summary,
    )


if __name__ == "__main__":
    main()
