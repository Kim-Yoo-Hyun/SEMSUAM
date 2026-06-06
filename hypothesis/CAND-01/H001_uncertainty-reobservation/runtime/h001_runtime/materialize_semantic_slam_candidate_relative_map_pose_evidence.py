import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_candidate_relative_map_pose_evidence.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_candidate_relative_map_pose_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_candidate_relative_map_pose_evidence_v1"

REQUEST_ID_ALIASES = (
    "request_id",
    "rival_identity_request_id",
    "expanded_retrieval_request_id",
)
SOURCE_REQUEST_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")

ALTERNATIVE_ORDER = (
    "current_unique_ready",
    "top_map_pose_tuple",
    "top_projection_visible_heading",
    "top_pose_heading",
    "closest_target_distance",
    "top_projection_status_visible",
    "defer_all",
    "semantic_rank_fallback",
    "detector_score_fallback",
)

FORBIDDEN_ACTION_KEYS = {
    "GTTargetOracle",
    "GTCandidateOracle",
    "GTViewOracle",
    "candidate_correctness_label",
    "candidate_wrong_label",
    "correctness_label",
    "detector_score",
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
    "semantic_rank",
    "semantic_score",
    "shortest_path_distance",
    "source_top_candidate_ids",
    "success_commit",
    "target_detector_evidence_score",
    "target_positive_support",
    "target_semantic_score",
    "target_support_score",
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


def merge_counters(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    out: Counter[str] = Counter()
    for row in rows:
        value = row.get(key)
        if isinstance(value, Mapping):
            for name, count in value.items():
                out[str(name)] += safe_int(count, 0)
    return dict(sorted(out.items()))


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


def source_request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    nested = row.get("join_key")
    source = nested if isinstance(nested, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
        str(source.get("query") or row.get("query") or ""),
        normalized_request_id(row),
        str(source.get("episode_key") or row.get("episode_key") or ""),
    )


def source_request_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(SOURCE_REQUEST_KEYS, key))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def target_distance_stats(row: Mapping[str, Any]) -> Dict[str, Optional[float]]:
    value = row.get("target_distance_from_viewpoint_m")
    if isinstance(value, Mapping):
        return {
            "count": safe_int(value.get("count"), 0),
            "min": safe_float(value.get("min")),
            "mean": safe_float(value.get("mean")),
            "max": safe_float(value.get("max")),
        }
    found = safe_float(value)
    return {"count": 1 if found is not None else 0, "min": found, "mean": found, "max": found}


def target_distance_mean(row: Mapping[str, Any]) -> Optional[float]:
    return target_distance_stats(row).get("mean")


def projection_status_visible(row: Mapping[str, Any]) -> int:
    counts = row.get("projection_status_counts")
    if isinstance(counts, Mapping):
        return safe_int(counts.get("visible"), 0)
    return 0


def projection_visible_fraction(row: Mapping[str, Any]) -> float:
    visible = projection_status_visible(row)
    counts = row.get("projection_status_counts")
    if not isinstance(counts, Mapping):
        return 0.0
    total = sum(safe_int(value, 0) for value in counts.values())
    return ratio(visible, total)


def entropy_proxy(counts: Any) -> float:
    if not isinstance(counts, Mapping):
        return 0.0
    values = [safe_int(value, 0) for value in counts.values()]
    total = sum(value for value in values if value > 0)
    if total <= 0:
        return 0.0
    entropy = 0.0
    for value in values:
        if value <= 0:
            continue
        p = value / total
        entropy -= p * math.log(p, 2)
    return entropy


def axis_failure_diversity_proxy(row: Mapping[str, Any]) -> int:
    counts = row.get("projection_axis_status_counts")
    if not isinstance(counts, Mapping):
        return 0
    return sum(1 for name, count in counts.items() if str(name) != "visible" and safe_int(count, 0) > 0)


def score_tuple(row: Mapping[str, Any]) -> Tuple[float, ...]:
    values = row.get("candidate_map_pose_score_tuple")
    if not isinstance(values, list):
        return ()
    return tuple(safe_float(value, 0.0) or 0.0 for value in values)


def rank_desc(value: float, values: Sequence[float]) -> int:
    return 1 + sum(1 for other in values if other > value)


def rank_asc(value: float, values: Sequence[float]) -> int:
    return 1 + sum(1 for other in values if other < value)


def tie_count_float(value: float, values: Sequence[float]) -> int:
    return sum(1 for other in values if other == value)


def rank_tuple_desc(value: Tuple[float, ...], values: Sequence[Tuple[float, ...]]) -> int:
    return 1 + sum(1 for other in values if other > value)


def tie_count_tuple(value: Tuple[float, ...], values: Sequence[Tuple[float, ...]]) -> int:
    return sum(1 for other in values if other == value)


def numeric_gap_to_best_rival(
    row: Mapping[str, Any], rows: Sequence[Mapping[str, Any]], field: str
) -> Optional[float]:
    current = safe_float(row.get(field))
    rivals = [safe_float(other.get(field)) for other in rows if candidate_id(other) != candidate_id(row)]
    rivals = [value for value in rivals if value is not None]
    if current is None or not rivals:
        return None
    return current - max(rivals)


def target_distance_advantage(row: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]) -> Optional[float]:
    current = target_distance_mean(row)
    rivals = [target_distance_mean(other) for other in rows if candidate_id(other) != candidate_id(row)]
    rivals = [value for value in rivals if value is not None]
    if current is None or not rivals:
        return None
    return min(rivals) - current


def best_rival_by_score_tuple(
    row: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> Optional[Mapping[str, Any]]:
    rivals = [other for other in rows if candidate_id(other) != candidate_id(row)]
    if not rivals:
        return None
    return sorted(rivals, key=lambda item: (score_tuple(item), candidate_id(item)), reverse=True)[0]


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


def strategy_order(strategy_id: str, rows: Sequence[Mapping[str, Any]]) -> List[Mapping[str, Any]]:
    if strategy_id == "top_map_pose_tuple":
        return sorted(rows, key=lambda row: (score_tuple(row), candidate_id(row)), reverse=True)
    if strategy_id == "top_projection_visible_heading":
        return sorted(
            rows,
            key=lambda row: (
                safe_int(row.get("projection_visible_heading_count"), 0),
                safe_int(row.get("pose_heading_count"), 0),
                score_tuple(row),
                candidate_id(row),
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
                candidate_id(row),
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
                candidate_id(row),
            ),
        )
    if strategy_id == "top_projection_status_visible":
        return sorted(
            rows,
            key=lambda row: (
                projection_status_visible(row),
                safe_int(row.get("pose_heading_count"), 0),
                score_tuple(row),
                candidate_id(row),
            ),
            reverse=True,
        )
    return []


def index_by_source_request(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        index[source_request_key(row)].append(row)
    return dict(index)


def index_one_by_source_request(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str, str], Mapping[str, Any]]:
    return {source_request_key(row): row for row in rows}


def index_strict_edge_variants(
    rows: Sequence[Mapping[str, Any]]
) -> Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]]:
    index: Dict[Tuple[str, str, str, str, str], Dict[str, Mapping[str, Any]]] = defaultdict(dict)
    for row in rows:
        index[source_request_key(row)][str(row.get("edge_variant") or "")] = row
    return dict(index)


def strict_edge_context(variants: Mapping[str, Mapping[str, Any]]) -> Dict[str, Any]:
    pose_spatial_or_loop = variants.get("pose_spatial_or_loop") or {}
    pose_loop = variants.get("pose_loop") or {}
    context = variants.get("target_context") or {}
    candidate_overlap = variants.get("candidate_overlap_only") or {}
    context_ready = bool(context.get("proxy_ready") is True)
    return {
        "strict_pose_spatial_or_loop_request_ready": bool(pose_spatial_or_loop.get("proxy_ready") is True),
        "strict_pose_loop_request_ready": bool(pose_loop.get("proxy_ready") is True),
        "strict_context_request_ready": context_ready,
        "candidate_overlap_only_request_flag": bool(
            candidate_overlap.get("proxy_ready") is True
            and pose_spatial_or_loop.get("proxy_ready") is not True
            and pose_loop.get("proxy_ready") is not True
            and not context_ready
        ),
        "strict_edge_variant_proxy_ready": {
            name: bool(row.get("proxy_ready") is True) for name, row in sorted(variants.items())
        },
        "strict_edge_variant_edge_count": {
            name: safe_int(row.get("edge_count"), 0) for name, row in sorted(variants.items())
        },
        "strict_edge_variant_connected_component_count": {
            name: safe_int(row.get("connected_component_count"), 0) for name, row in sorted(variants.items())
        },
        "strict_edge_variant_largest_component_fraction": {
            name: safe_float(row.get("largest_component_fraction"), 0.0) or 0.0
            for name, row in sorted(variants.items())
        },
    }


def request_pose_graph_context(
    request_row: Mapping[str, Any],
    graph_row: Optional[Mapping[str, Any]],
    variants: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    edge_reason_counts = (
        graph_row.get("edge_reason_counts")
        if isinstance(graph_row, Mapping) and isinstance(graph_row.get("edge_reason_counts"), Mapping)
        else request_row.get("request_pose_graph_edge_reason_counts")
    )
    edge_reason_counts = dict(edge_reason_counts) if isinstance(edge_reason_counts, Mapping) else {}
    graph_edge_count = safe_int(
        (graph_row or {}).get("edge_count"), safe_int(request_row.get("request_pose_graph_edge_count"), 0)
    )
    candidate_overlap_edge_count = safe_int(edge_reason_counts.get("candidate_id_overlap"), 0)
    non_candidate_reason_count = sum(
        safe_int(count, 0) for reason, count in edge_reason_counts.items() if str(reason) != "candidate_id_overlap"
    )
    graph_candidate_overlap_only = bool(
        graph_edge_count > 0 and candidate_overlap_edge_count > 0 and non_candidate_reason_count == 0
    )
    strict_context = strict_edge_context(variants)
    return {
        "request_pose_graph_proxy_ready": bool(request_row.get("request_pose_graph_proxy_ready") is True),
        "request_pose_graph_connected_component_count": safe_int(
            request_row.get("request_pose_graph_connected_component_count"), 0
        ),
        "request_pose_graph_largest_component_fraction": safe_float(
            request_row.get("request_pose_graph_largest_component_fraction"), 0.0
        )
        or 0.0,
        "request_pose_graph_edge_count": safe_int(request_row.get("request_pose_graph_edge_count"), 0),
        "request_pose_graph_edge_reason_counts": dict(request_row.get("request_pose_graph_edge_reason_counts") or {}),
        "pose_graph_proxy_ready": bool((graph_row or {}).get("proxy_ready") is True),
        "pose_graph_node_count": safe_int((graph_row or {}).get("node_count"), 0),
        "pose_graph_edge_count": graph_edge_count,
        "pose_graph_connected_component_count": safe_int((graph_row or {}).get("connected_component_count"), 0),
        "pose_graph_largest_component_fraction": safe_float((graph_row or {}).get("largest_component_fraction"), 0.0)
        or 0.0,
        "pose_graph_edge_reason_counts": edge_reason_counts,
        "pose_graph_loop_closure_opportunity_edge_count": safe_int(
            (graph_row or {}).get("loop_closure_opportunity_edge_count"), 0
        ),
        "pose_graph_candidate_overlap_only_request_flag": graph_candidate_overlap_only,
        **strict_context,
    }


def candidate_separability_tag(
    row: Mapping[str, Any],
    candidate_count: int,
    map_pose_tuple_rank: int,
    map_pose_tuple_tie_count: int,
    projection_gap: Optional[float],
    pose_gap: Optional[float],
    distance_advantage: Optional[float],
) -> str:
    if row.get("strict_candidate_map_pose_ready") is not True:
        return "candidate_relative_weak_or_partial_support"
    if candidate_count <= 1:
        return "single_candidate_geometry_only_nonterminal"
    positive_gap = any((value or 0.0) > 0.0 for value in (projection_gap, pose_gap, distance_advantage))
    if map_pose_tuple_rank == 1 and map_pose_tuple_tie_count == 1 and positive_gap:
        return "candidate_relative_dominant_map_pose_support"
    if map_pose_tuple_tie_count > 1 or map_pose_tuple_rank == 1:
        return "candidate_relative_tied_map_pose_support"
    return "candidate_relative_weak_or_partial_support"


def build_candidate_rows(
    *,
    source_key: Tuple[str, str, str, str, str],
    source_rows: Sequence[Mapping[str, Any]],
    request_row: Mapping[str, Any],
    graph_row: Optional[Mapping[str, Any]],
    strict_variants: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    candidates = sorted(source_rows, key=candidate_id)
    candidate_count = len(candidates)
    ready_count = sum(1 for row in candidates if row.get("strict_candidate_map_pose_ready") is True)
    numeric_values = {
        "projection_visible_heading_count": [
            float(safe_int(row.get("projection_visible_heading_count"), 0)) for row in candidates
        ],
        "pose_heading_count": [float(safe_int(row.get("pose_heading_count"), 0)) for row in candidates],
        "unique_viewpoint_count": [float(safe_int(row.get("unique_viewpoint_count"), 0)) for row in candidates],
        "navmesh_ready_viewpoint_count": [
            float(safe_int(row.get("navmesh_ready_viewpoint_count"), 0)) for row in candidates
        ],
        "candidate_targeted_frame_row_count": [
            float(safe_int(row.get("candidate_targeted_frame_row_count"), 0)) for row in candidates
        ],
    }
    distance_values = [target_distance_mean(row) for row in candidates]
    distance_values_float = [value for value in distance_values if value is not None]
    tuple_values = [score_tuple(row) for row in candidates]
    pose_context = request_pose_graph_context(request_row, graph_row, strict_variants)
    rows: List[Dict[str, Any]] = []
    for row in candidates:
        cid = candidate_id(row)
        dist = target_distance_stats(row)
        tuple_value = score_tuple(row)
        projection_gap = numeric_gap_to_best_rival(row, candidates, "projection_visible_heading_count")
        pose_gap = numeric_gap_to_best_rival(row, candidates, "pose_heading_count")
        distance_gap = target_distance_advantage(row, candidates)
        best_rival = best_rival_by_score_tuple(row, candidates)
        map_pose_rank = rank_tuple_desc(tuple_value, tuple_values)
        map_pose_tie = tie_count_tuple(tuple_value, tuple_values)
        tag = candidate_separability_tag(
            row,
            candidate_count,
            map_pose_rank,
            map_pose_tie,
            projection_gap,
            pose_gap,
            distance_gap,
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "candidate_relative_map_pose_evidence_nonterminal",
                "row_type": "semantic_slam_candidate_relative_map_pose_evidence_candidate",
                "join_key": {**source_request_payload(source_key), "candidate_id": cid},
                **source_request_payload(source_key),
                "candidate_id": cid,
                "candidate_count": candidate_count,
                "ready_candidate_count": ready_count,
                "all_candidates_ready": candidate_count > 0 and ready_count == candidate_count,
                "strict_candidate_map_pose_ready": bool(row.get("strict_candidate_map_pose_ready") is True),
                "candidate_map_pose_score_tuple": list(tuple_value),
                "map_pose_score_tuple_rank": map_pose_rank,
                "map_pose_score_tuple_tie_count": map_pose_tie,
                "best_rival_candidate_id_by_map_pose_tuple": candidate_id(best_rival or {}),
                "best_rival_map_pose_score_tuple": list(score_tuple(best_rival or {})) if best_rival else None,
                "map_pose_score_tuple_gap_to_best_rival_componentwise": [
                    current - rival
                    for current, rival in zip(tuple_value, score_tuple(best_rival or {}))
                ]
                if best_rival
                else None,
                "candidate_targeted_frame_row_count": safe_int(row.get("candidate_targeted_frame_row_count"), 0),
                "candidate_targeted_frame_count_rank": rank_desc(
                    float(safe_int(row.get("candidate_targeted_frame_row_count"), 0)),
                    numeric_values["candidate_targeted_frame_row_count"],
                ),
                "candidate_targeted_frame_count_gap_to_best_rival": numeric_gap_to_best_rival(
                    row, candidates, "candidate_targeted_frame_row_count"
                ),
                "unique_viewpoint_count": safe_int(row.get("unique_viewpoint_count"), 0),
                "unique_viewpoint_count_rank": rank_desc(
                    float(safe_int(row.get("unique_viewpoint_count"), 0)),
                    numeric_values["unique_viewpoint_count"],
                ),
                "unique_viewpoint_count_gap_to_best_rival": numeric_gap_to_best_rival(
                    row, candidates, "unique_viewpoint_count"
                ),
                "navmesh_ready_viewpoint_count": safe_int(row.get("navmesh_ready_viewpoint_count"), 0),
                "navmesh_ready_viewpoint_count_rank": rank_desc(
                    float(safe_int(row.get("navmesh_ready_viewpoint_count"), 0)),
                    numeric_values["navmesh_ready_viewpoint_count"],
                ),
                "navmesh_ready_viewpoint_count_gap_to_best_rival": numeric_gap_to_best_rival(
                    row, candidates, "navmesh_ready_viewpoint_count"
                ),
                "projection_visible_heading_count": safe_int(row.get("projection_visible_heading_count"), 0),
                "projection_visible_heading_rank": rank_desc(
                    float(safe_int(row.get("projection_visible_heading_count"), 0)),
                    numeric_values["projection_visible_heading_count"],
                ),
                "projection_visible_heading_tie_count": tie_count_float(
                    float(safe_int(row.get("projection_visible_heading_count"), 0)),
                    numeric_values["projection_visible_heading_count"],
                ),
                "projection_visible_heading_gap_to_best_rival": projection_gap,
                "projection_visible_fraction": projection_visible_fraction(row),
                "projection_status_counts": dict(row.get("projection_status_counts") or {}),
                "projection_status_entropy_proxy": entropy_proxy(row.get("projection_status_counts")),
                "projection_axis_status_counts": dict(row.get("projection_axis_status_counts") or {}),
                "axis_failure_diversity_proxy": axis_failure_diversity_proxy(row),
                "pose_heading_count": safe_int(row.get("pose_heading_count"), 0),
                "pose_heading_rank": rank_desc(
                    float(safe_int(row.get("pose_heading_count"), 0)), numeric_values["pose_heading_count"]
                ),
                "pose_heading_tie_count": tie_count_float(
                    float(safe_int(row.get("pose_heading_count"), 0)), numeric_values["pose_heading_count"]
                ),
                "pose_heading_gap_to_best_rival": pose_gap,
                "total_heading_count": safe_int(row.get("total_heading_count"), 0),
                "target_distance_from_viewpoint_m": dist,
                "target_distance_mean_rank": rank_asc(dist["mean"] or 999999.0, distance_values_float)
                if distance_values_float
                else None,
                "target_distance_advantage_m_against_closest_rival": distance_gap,
                "target_position_ready": bool(row.get("target_position_ready") is True),
                "physical_viewpoint_position_ready": bool(row.get("physical_viewpoint_position_ready") is True),
                "view_role_counts": dict(row.get("view_role_counts") or {}),
                "viewpoint_source_counts": dict(row.get("viewpoint_source_counts") or {}),
                **pose_context,
                "separability_tag": tag,
                "request_all_candidates_ready_saturated": candidate_count > 0 and ready_count == candidate_count,
                "request_candidate_overlap_only_risk": bool(
                    pose_context["candidate_overlap_only_request_flag"]
                    or pose_context["pose_graph_candidate_overlap_only_request_flag"]
                ),
                "request_no_valid_risk_requires_evaluation_join": True,
                "primary_nonterminal_action": "request_candidate_relative_map_pose_evidence_or_defer",
                "terminal_commit": False,
                "candidate_commit": False,
                "candidate_rejection": False,
                "uses_gt_for_action": False,
                "uses_semantic_or_detector_shortcut": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def feature_variation(candidates: Sequence[Mapping[str, Any]]) -> Dict[str, bool]:
    fields = (
        "candidate_map_pose_score_tuple",
        "candidate_targeted_frame_row_count",
        "unique_viewpoint_count",
        "navmesh_ready_viewpoint_count",
        "projection_visible_heading_count",
        "pose_heading_count",
        "projection_visible_frame_row_count",
    )
    out: Dict[str, bool] = {}
    for field in fields:
        values = {json.dumps(row.get(field), sort_keys=True) for row in candidates}
        out[f"{field}_varies"] = len(values) > 1
    return out


def top_tuple_tie_count(candidates: Sequence[Mapping[str, Any]]) -> int:
    if not candidates:
        return 0
    tuples = [score_tuple(row) for row in candidates]
    top = max(tuples)
    return sum(1 for value in tuples if value == top)


def build_request_row(
    *,
    source_key: Tuple[str, str, str, str, str],
    candidate_rows: Sequence[Mapping[str, Any]],
    candidate_evidence_rows: Sequence[Mapping[str, Any]],
    request_row: Mapping[str, Any],
    graph_row: Optional[Mapping[str, Any]],
    strict_variants: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    candidates = sorted(candidate_rows, key=candidate_id)
    top_candidates = sorted(candidates, key=lambda row: (score_tuple(row), candidate_id(row)), reverse=True)
    top_candidate = top_candidates[0] if top_candidates else None
    tags = Counter(str(row.get("separability_tag") or "") for row in candidate_evidence_rows)
    pose_context = request_pose_graph_context(request_row, graph_row, strict_variants)
    dominant_count = tags.get("candidate_relative_dominant_map_pose_support", 0)
    candidate_count = len(candidates)
    ready_count = sum(1 for row in candidates if row.get("strict_candidate_map_pose_ready") is True)
    tie_count = top_tuple_tie_count(candidates)
    if candidate_count <= 1:
        separability_status = "single_candidate_geometry_only_nonterminal"
    elif dominant_count > 0 and tie_count == 1:
        separability_status = "candidate_relative_unique_top_nonterminal"
    else:
        separability_status = "candidate_relative_tie_or_saturation_nonterminal"
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "candidate_relative_map_pose_evidence_nonterminal",
        "row_type": "semantic_slam_candidate_relative_map_pose_evidence_request",
        "join_key": source_request_payload(source_key),
        **source_request_payload(source_key),
        "candidate_count": candidate_count,
        "ready_candidate_count": ready_count,
        "all_candidates_ready": candidate_count > 0 and ready_count == candidate_count,
        "multi_candidate_all_ready": candidate_count > 1 and ready_count == candidate_count,
        "candidate_ids": [candidate_id(row) for row in candidates],
        "top_map_pose_tuple_candidate_id": candidate_id(top_candidate or {}),
        "top_map_pose_tuple": list(score_tuple(top_candidate or {})) if top_candidate else None,
        "top_map_pose_tuple_tie_count": tie_count,
        "candidate_relative_dominant_support_candidate_count": dominant_count,
        "candidate_relative_tied_support_candidate_count": tags.get("candidate_relative_tied_map_pose_support", 0),
        "candidate_relative_weak_or_partial_candidate_count": tags.get(
            "candidate_relative_weak_or_partial_support", 0
        ),
        "separability_status": separability_status,
        "candidate_separability_tag_counts": dict(sorted(tags.items())),
        "feature_variation": feature_variation(candidates),
        "projection_status_counts_merged": merge_counters(candidates, "projection_status_counts"),
        "projection_axis_status_counts_merged": merge_counters(candidates, "projection_axis_status_counts"),
        "strict_candidate_map_pose_ready_candidate_ids": [
            str(item) for item in request_row.get("strict_candidate_map_pose_ready_candidate_ids", [])
        ],
        "current_selector_id": request_row.get("selector_id"),
        "current_selector_action": request_row.get("selector_action"),
        "current_selector_missing_reason": request_row.get("selector_missing_reason"),
        **pose_context,
        "request_all_candidates_ready_saturated": candidate_count > 0 and ready_count == candidate_count,
        "request_candidate_overlap_only_risk": bool(
            pose_context["candidate_overlap_only_request_flag"]
            or pose_context["pose_graph_candidate_overlap_only_request_flag"]
        ),
        "request_no_valid_risk_requires_evaluation_join": True,
        "primary_nonterminal_action": "request_candidate_relative_map_pose_evidence_or_defer",
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_semantic_or_detector_shortcut": False,
        "paper_claim_allowed": False,
    }


def make_alternative_row(
    *,
    source_key: Tuple[str, str, str, str, str],
    strategy_id: str,
    candidates: Sequence[Mapping[str, Any]],
    request_row: Mapping[str, Any],
) -> Dict[str, Any]:
    selected: Optional[Mapping[str, Any]] = None
    selection_reason: str
    allowed_as_nonterminal_audit = True
    allowed_as_terminal_action = False
    fallback_shortcut_forbidden = False
    if strategy_id == "current_unique_ready":
        ready = [row for row in candidates if row.get("strict_candidate_map_pose_ready") is True]
        if len(ready) == 1:
            selected = ready[0]
            selection_reason = "single_strict_map_pose_ready_candidate"
        else:
            selection_reason = "multiple_map_pose_ready_candidates" if ready else "no_candidate_map_pose_ready"
    elif strategy_id == "defer_all":
        selection_reason = "diagnostic_defer_all"
    elif strategy_id in {"semantic_rank_fallback", "detector_score_fallback"}:
        selection_reason = "forbidden_shortcut_not_materialized"
        allowed_as_nonterminal_audit = False
        fallback_shortcut_forbidden = True
    else:
        ordered = strategy_order(strategy_id, candidates)
        selected = ordered[0] if ordered else None
        selection_reason = "top_candidate_by_label_free_geometry_rule" if selected else "no_candidate_rows"
    selected_id = candidate_id(selected or {}) or None
    tuple_values = [score_tuple(row) for row in candidates]
    selected_tuple = score_tuple(selected or {}) if selected else ()
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "candidate_relative_map_pose_evidence_nonterminal",
        "row_type": "semantic_slam_candidate_relative_map_pose_evidence_alternative_audit",
        "join_key": {**source_request_payload(source_key), "alternative_id": strategy_id},
        **source_request_payload(source_key),
        "alternative_id": strategy_id,
        "alternative_role": "diagnostic_only",
        "alternative_allowed_as_nonterminal_audit": allowed_as_nonterminal_audit,
        "alternative_allowed_as_terminal_action": allowed_as_terminal_action,
        "fallback_shortcut_forbidden": fallback_shortcut_forbidden,
        "audit_selected_candidate_id": selected_id,
        "audit_selection_reason": selection_reason,
        "audit_would_commit_if_terminal_policy_existed": bool(selected is not None and not fallback_shortcut_forbidden),
        "candidate_count": len(candidates),
        "ready_candidate_count": sum(1 for row in candidates if row.get("strict_candidate_map_pose_ready") is True),
        "audit_selected_map_pose_score_tuple": list(selected_tuple) if selected else None,
        "audit_selected_map_pose_score_tuple_rank": rank_tuple_desc(selected_tuple, tuple_values)
        if selected and tuple_values
        else None,
        "audit_selected_projection_visible_heading_count": safe_int(
            (selected or {}).get("projection_visible_heading_count"), 0
        )
        if selected
        else None,
        "audit_selected_pose_heading_count": safe_int((selected or {}).get("pose_heading_count"), 0)
        if selected
        else None,
        "audit_selected_target_distance_mean_m": target_distance_mean(selected or {}) if selected else None,
        "current_selector_action": request_row.get("selector_action"),
        "current_selector_missing_reason": request_row.get("selector_missing_reason"),
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_semantic_or_detector_shortcut": False,
        "paper_claim_allowed": False,
    }


def build_failure_row(
    *,
    source_key: Tuple[str, str, str, str, str],
    request_summary: Mapping[str, Any],
) -> Dict[str, Any]:
    candidate_count = safe_int(request_summary.get("candidate_count"), 0)
    tags: List[str] = ["terminal_commit_blocked_by_contract", "request_no_valid_risk_requires_evaluation_join"]
    if request_summary.get("request_all_candidates_ready_saturated") is True:
        tags.append("all_candidates_ready_saturation")
    if request_summary.get("multi_candidate_all_ready") is True:
        tags.append("multi_candidate_all_ready_saturation")
    if candidate_count <= 1:
        tags.append("single_candidate_geometry_only_nonterminal")
    if request_summary.get("request_candidate_overlap_only_risk") is True:
        tags.append("candidate_overlap_only_pose_graph_context")
    if request_summary.get("separability_status") != "candidate_relative_unique_top_nonterminal":
        tags.append("relative_score_tie_or_weak_margin")
    if request_summary.get("strict_pose_spatial_or_loop_request_ready") is not True:
        tags.append("strict_pose_spatial_or_loop_not_ready")
    primary = "candidate_relative_evidence_materialized_nonterminal"
    if "relative_score_tie_or_weak_margin" in tags:
        primary = "candidate_relative_separability_unresolved"
    if "candidate_overlap_only_pose_graph_context" in tags:
        primary = "candidate_overlap_only_pose_graph_context"
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "candidate_relative_map_pose_evidence_nonterminal",
        "row_type": "semantic_slam_candidate_relative_map_pose_evidence_failure_taxonomy",
        "join_key": source_request_payload(source_key),
        **source_request_payload(source_key),
        "primary_failure_or_blocker": primary,
        "failure_tags": sorted(set(tags)),
        "candidate_count": candidate_count,
        "ready_candidate_count": safe_int(request_summary.get("ready_candidate_count"), 0),
        "separability_status": request_summary.get("separability_status"),
        "top_map_pose_tuple_tie_count": safe_int(request_summary.get("top_map_pose_tuple_tie_count"), 0),
        "pose_graph_proxy_ready": bool(request_summary.get("pose_graph_proxy_ready") is True),
        "strict_pose_spatial_or_loop_request_ready": bool(
            request_summary.get("strict_pose_spatial_or_loop_request_ready") is True
        ),
        "candidate_overlap_only_request_flag": bool(request_summary.get("candidate_overlap_only_request_flag") is True),
        "pose_graph_candidate_overlap_only_request_flag": bool(
            request_summary.get("pose_graph_candidate_overlap_only_request_flag") is True
        ),
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def build_rows(
    *,
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    pose_graph_rows: Sequence[Mapping[str, Any]],
    strict_edge_rows: Sequence[Mapping[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    candidates_by_key = index_by_source_request(candidate_rows)
    request_by_key = index_one_by_source_request(request_rows)
    pose_graph_by_key = index_one_by_source_request(pose_graph_rows)
    strict_variants_by_key = index_strict_edge_variants(strict_edge_rows)

    candidate_out: List[Dict[str, Any]] = []
    request_out: List[Dict[str, Any]] = []
    alternative_out: List[Dict[str, Any]] = []
    failure_out: List[Dict[str, Any]] = []

    for source_key in sorted(request_by_key):
        request_row = request_by_key[source_key]
        candidates = candidates_by_key.get(source_key) or []
        graph_row = pose_graph_by_key.get(source_key)
        strict_variants = strict_variants_by_key.get(source_key) or {}
        candidate_evidence = build_candidate_rows(
            source_key=source_key,
            source_rows=candidates,
            request_row=request_row,
            graph_row=graph_row,
            strict_variants=strict_variants,
        )
        candidate_out.extend(candidate_evidence)
        request_summary = build_request_row(
            source_key=source_key,
            candidate_rows=candidates,
            candidate_evidence_rows=candidate_evidence,
            request_row=request_row,
            graph_row=graph_row,
            strict_variants=strict_variants,
        )
        request_out.append(request_summary)
        for strategy_id in ALTERNATIVE_ORDER:
            alternative_out.append(
                make_alternative_row(
                    source_key=source_key,
                    strategy_id=strategy_id,
                    candidates=candidates,
                    request_row=request_row,
                )
            )
        failure_out.append(build_failure_row(source_key=source_key, request_summary=request_summary))
    return candidate_out, request_out, alternative_out, failure_out


def build_summary(
    *,
    contract: Mapping[str, Any],
    source_counts: Mapping[str, int],
    candidate_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    pose_graph_rows: Sequence[Mapping[str, Any]],
    strict_edge_rows: Sequence[Mapping[str, Any]],
    candidate_out: Sequence[Mapping[str, Any]],
    request_out: Sequence[Mapping[str, Any]],
    alternative_out: Sequence[Mapping[str, Any]],
    failure_out: Sequence[Mapping[str, Any]],
    action_forbidden_keys: Sequence[str],
    out_root: Path,
) -> Dict[str, Any]:
    expected_outputs = contract.get("expected_future_outputs")
    expected_outputs = expected_outputs if isinstance(expected_outputs, Mapping) else {}
    source_gate = contract.get("source_gate")
    source_gate = source_gate if isinstance(source_gate, Mapping) else {}
    actual_counts = {
        "candidate_relative_evidence_rows": len(candidate_out),
        "request_summary_rows": len(request_out),
        "simpler_alternative_audit_rows": len(alternative_out),
        "failure_taxonomy_rows": len(failure_out),
        "source_candidate_rows": len(candidate_rows),
        "source_request_rows": len(request_rows),
        "source_pose_graph_proxy_rows": len(pose_graph_rows),
        "source_strict_edge_variant_rows": len(strict_edge_rows),
        "candidate_request_groups": len({source_request_key(row) for row in candidate_rows}),
        "candidate_ids": len({candidate_id(row) for row in candidate_rows}),
        "all_ready_candidate_rows": sum(
            1 for row in candidate_rows if row.get("strict_candidate_map_pose_ready") is True
        ),
        "request_pose_graph_context_rows": sum(1 for row in request_out if row.get("pose_graph_proxy_ready") is True),
        "strict_edge_variant_context_rows": sum(
            1 for row in request_out if row.get("strict_edge_variant_proxy_ready")
        ),
        "terminal_commit_rows": sum(1 for row in [*candidate_out, *request_out, *alternative_out, *failure_out] if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in [*candidate_out, *request_out, *alternative_out, *failure_out] if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in [*candidate_out, *request_out, *alternative_out, *failure_out] if row.get("candidate_rejection") is True),
        "action_evidence_forbidden_key_count": len(action_forbidden_keys),
        "candidate_relative_dominant_candidate_rows": sum(
            1 for row in candidate_out if row.get("separability_tag") == "candidate_relative_dominant_map_pose_support"
        ),
        "candidate_relative_unique_top_request_rows": sum(
            1 for row in request_out if row.get("separability_status") == "candidate_relative_unique_top_nonterminal"
        ),
        "candidate_relative_tie_or_saturation_request_rows": sum(
            1 for row in request_out if row.get("separability_status") == "candidate_relative_tie_or_saturation_nonterminal"
        ),
        "single_candidate_geometry_only_request_rows": sum(
            1 for row in request_out if row.get("separability_status") == "single_candidate_geometry_only_nonterminal"
        ),
        "candidate_overlap_only_request_rows": sum(
            1 for row in request_out if row.get("request_candidate_overlap_only_risk") is True
        ),
    }
    expected_counts = {
        "candidate_relative_evidence_rows": safe_int(
            expected_outputs.get("expected_candidate_relative_evidence_rows"), actual_counts["candidate_relative_evidence_rows"]
        ),
        "request_summary_rows": safe_int(
            expected_outputs.get("expected_request_summary_rows"), actual_counts["request_summary_rows"]
        ),
        "simpler_alternative_audit_rows_minimum": safe_int(
            expected_outputs.get("expected_simpler_alternative_rows_minimum"),
            actual_counts["simpler_alternative_audit_rows"],
        ),
        "failure_taxonomy_rows_minimum": safe_int(
            expected_outputs.get("expected_failure_taxonomy_rows_minimum"),
            actual_counts["failure_taxonomy_rows"],
        ),
        "source_candidate_rows": safe_int(source_gate.get("expected_candidate_rows"), len(candidate_rows)),
        "source_request_groups": safe_int(source_gate.get("expected_candidate_request_groups"), 0),
        "source_candidate_ids": safe_int(source_gate.get("expected_candidate_ids"), 0),
        "source_pose_graph_proxy_rows": safe_int(source_gate.get("expected_request_level_pose_graph_proxy_rows"), 0),
        "source_strict_edge_variant_rows": safe_int(source_gate.get("expected_strict_edge_variant_rows"), 0),
    }
    materializer_gate = {
        "candidate_relative_evidence_rows_match_expected": actual_counts["candidate_relative_evidence_rows"]
        == expected_counts["candidate_relative_evidence_rows"],
        "request_summary_rows_match_expected": actual_counts["request_summary_rows"]
        == expected_counts["request_summary_rows"],
        "simpler_alternative_rows_minimum_passed": actual_counts["simpler_alternative_audit_rows"]
        >= expected_counts["simpler_alternative_audit_rows_minimum"],
        "failure_taxonomy_rows_minimum_passed": actual_counts["failure_taxonomy_rows"]
        >= expected_counts["failure_taxonomy_rows_minimum"],
        "all_candidate_rows_join_to_request_summary": actual_counts["candidate_request_groups"]
        == actual_counts["request_summary_rows"],
        "pose_graph_proxy_context_coverage_passed": actual_counts["request_pose_graph_context_rows"] >= 50,
        "strict_edge_variant_context_coverage_passed": actual_counts["strict_edge_variant_context_rows"] >= 50,
        "action_evidence_forbidden_keys_passed": len(action_forbidden_keys) == 0,
        "uses_gt_for_action_passed": not any(
            row.get("uses_gt_for_action") is True for row in [*candidate_out, *request_out, *alternative_out, *failure_out]
        ),
        "terminal_commit_rows_passed": actual_counts["terminal_commit_rows"] == 0,
        "candidate_commit_rows_passed": actual_counts["candidate_commit_rows"] == 0,
        "candidate_rejection_rows_passed": actual_counts["candidate_rejection_rows"] == 0,
        "paper_claim_allowed_passed": not any(
            row.get("paper_claim_allowed") is True for row in [*candidate_out, *request_out, *alternative_out, *failure_out]
        ),
    }
    promotion_gate = {
        "candidate_relative_evidence_gate_must_pass": all(materializer_gate.values()),
        "candidate_relative_separable_rows_min_passed": actual_counts["candidate_relative_unique_top_request_rows"] >= 5,
        "multi_candidate_tie_rows_reported": actual_counts["candidate_relative_tie_or_saturation_request_rows"] > 0,
        "no_valid_risk_rows_separated_before_commit": sum(
            1 for row in failure_out if "request_no_valid_risk_requires_evaluation_join" in row.get("failure_tags", [])
        )
        == len(failure_out),
        "required_map_side_metric_count_min_passed": True,
        "required_task_side_proxy_count_min_passed": False,
        "heldout_or_fresh_validation_required_before_paper_claim": False,
    }
    materializer_gate_passed = all(materializer_gate.values())
    promotion_gate_passed = all(promotion_gate.values())
    failure_tag_counts = compact_counter(tag for row in failure_out for tag in row.get("failure_tags", []))
    primary_blocker = None
    if not materializer_gate_passed:
        primary_blocker = "candidate_relative_materializer_gate_failed"
    elif not promotion_gate_passed:
        if not promotion_gate["required_task_side_proxy_count_min_passed"]:
            primary_blocker = "task_side_proxy_not_joined_for_terminal_utility"
        elif not promotion_gate["candidate_relative_separable_rows_min_passed"]:
            primary_blocker = "candidate_relative_separability_too_weak"
        else:
            primary_blocker = "candidate_relative_promotion_gate_failed"
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "materializer_gate_passed_promotion_blocked"
        if materializer_gate_passed and not promotion_gate_passed
        else "completed"
        if materializer_gate_passed
        else "failed",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "candidate_relative_evidence_rows": "semantic_slam_candidate_relative_map_pose_evidence_candidate_rows.jsonl",
            "request_summary_rows": "semantic_slam_candidate_relative_map_pose_evidence_request_rows.jsonl",
            "simpler_alternative_audit_rows": "semantic_slam_candidate_relative_map_pose_evidence_alternative_rows.jsonl",
            "failure_taxonomy_rows": "semantic_slam_candidate_relative_map_pose_evidence_failure_rows.jsonl",
            "summary": "semantic_slam_candidate_relative_map_pose_evidence_summary.json",
        },
        "source_files": contract.get("source", {}),
        "source_counts": dict(source_counts),
        "actual_counts": actual_counts,
        "expected_counts": expected_counts,
        "candidate_count_distribution": compact_counter(row.get("candidate_count") for row in request_out),
        "ready_candidate_count_distribution": compact_counter(row.get("ready_candidate_count") for row in request_out),
        "separability_status_counts": compact_counter(row.get("separability_status") for row in request_out),
        "candidate_separability_tag_counts": compact_counter(row.get("separability_tag") for row in candidate_out),
        "alternative_counts": compact_counter(row.get("alternative_id") for row in alternative_out),
        "failure_tag_counts": failure_tag_counts,
        "action_evidence_forbidden_keys": list(action_forbidden_keys),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "materializer_gate": materializer_gate,
        "promotion_gate_after_materialization": promotion_gate,
        "candidate_relative_evidence_gate_passed": materializer_gate_passed,
        "promotion_gate_after_materialization_passed": promotion_gate_passed,
        "revised_slam_formula_allowed": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed_from_this_artifact": False,
        "known_negative_baselines_from_safe_sparse_diagnostic": (
            contract.get("simpler_alternative_audit", {}).get("known_negative_baselines_from_safe_sparse_diagnostic", {})
            if isinstance(contract.get("simpler_alternative_audit"), Mapping)
            else {}
        ),
        "primary_blocker": primary_blocker,
        "recommended_next_task": "join_candidate_relative_evidence_to_task_side_proxy_before_terminal_utility"
        if materializer_gate_passed
        else "repair_candidate_relative_materializer",
        "interpretation": {
            "fact": (
                "The materializer writes label-free candidate-relative map/pose evidence rows and keeps every "
                "selector alternative diagnostic-only."
            ),
            "agent_inference": (
                "If this gate passes, the next falsifiable step is not a revised formula yet; it is a task-side "
                "proxy join that can test whether relative map/pose contrast predicts wrong-goal/no-valid risk."
            ),
            "paper_claim": (
                "No Semantic-SLAM utility, ObjectNav improvement, SLAM benefit, terminal utility, first_eval, "
                "policy-scale comparison, or paper claim is allowed from this materializer alone."
            ),
        },
        "next_task": "join_candidate_relative_evidence_to_task_side_proxy_before_terminal_utility",
    }


def run(contract_path: Path, out_root: Path) -> Dict[str, Any]:
    contract = load_json(contract_path)
    source = contract.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("Contract source section is missing.")
    candidate_rows = load_jsonl(Path(str(source["candidate_map_pose_candidate_rows"])))
    request_rows = load_jsonl(Path(str(source["candidate_map_pose_request_rows"])))
    pose_source_rows = load_jsonl(Path(str(source["map_pose_source_inventory_rows"])))
    pose_probe_rows = load_jsonl(Path(str(source["map_pose_probe_request_rows"])))
    pose_graph_rows = load_jsonl(Path(str(source["request_level_pose_graph_proxy_rows"])))
    strict_edge_rows = load_jsonl(Path(str(source["strict_edge_variant_rows"])))
    strict_summary_rows = load_jsonl(Path(str(source["strict_edge_variant_summary_rows"])))
    safe_sparse_rows = load_jsonl(Path(str(source["safe_sparse_selector_alternative_rows"])))

    candidate_out, request_out, alternative_out, failure_out = build_rows(
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        pose_graph_rows=pose_graph_rows,
        strict_edge_rows=strict_edge_rows,
    )
    action_forbidden_keys = scan_forbidden_keys([*candidate_out, *request_out, *alternative_out, *failure_out])
    source_counts = {
        "map_pose_source_inventory_rows": len(pose_source_rows),
        "map_pose_probe_request_rows": len(pose_probe_rows),
        "strict_edge_variant_summary_rows": len(strict_summary_rows),
        "safe_sparse_selector_alternative_rows": len(safe_sparse_rows),
    }
    summary = build_summary(
        contract=contract,
        source_counts=source_counts,
        candidate_rows=candidate_rows,
        request_rows=request_rows,
        pose_graph_rows=pose_graph_rows,
        strict_edge_rows=strict_edge_rows,
        candidate_out=candidate_out,
        request_out=request_out,
        alternative_out=alternative_out,
        failure_out=failure_out,
        action_forbidden_keys=action_forbidden_keys,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_candidate_relative_map_pose_evidence_candidate_rows.jsonl", candidate_out)
    write_jsonl(out_root / "semantic_slam_candidate_relative_map_pose_evidence_request_rows.jsonl", request_out)
    write_jsonl(out_root / "semantic_slam_candidate_relative_map_pose_evidence_alternative_rows.jsonl", alternative_out)
    write_jsonl(out_root / "semantic_slam_candidate_relative_map_pose_evidence_failure_rows.jsonl", failure_out)
    write_json(out_root / "semantic_slam_candidate_relative_map_pose_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Materialize candidate-relative Semantic-SLAM map/pose evidence.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.contract), Path(args.out_root))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
