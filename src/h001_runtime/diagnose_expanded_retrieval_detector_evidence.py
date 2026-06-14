import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_detector_evidence_diagnostic.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def numeric_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    numeric_values = [float(value) for value in values if isinstance(value, (int, float))]
    if not numeric_values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(numeric_values),
        "min": min(numeric_values),
        "max": max(numeric_values),
        "mean": mean(numeric_values),
        "median": median(numeric_values),
    }


def counter_dict(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def request_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(row.get("rival_identity_request_id") or row.get("expanded_retrieval_request_id")),
        str(row.get("episode_key")),
        str(row.get("query")),
    )


def candidate_key(row: Dict[str, Any]) -> Tuple[str, str, str, str]:
    base = request_key(row)
    return base + (str(row.get("candidate_id") or row.get("target_candidate_id")),)


def frame_candidate_key(row: Dict[str, Any]) -> Tuple[str, str, str, str]:
    base = request_key(row)
    return base + (str(row.get("target_candidate_id") or row.get("selected_candidate_ids", [""])[0]),)


def index_frame_rows(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[frame_candidate_key(row)] = row
    return indexed


def group_by_candidate(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[candidate_key(row)].append(row)
    return grouped


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_key(row)].append(row)
    return grouped


def evidence_score(rows: Sequence[Dict[str, Any]]) -> float:
    strict_hits = sum(1 for row in rows if row.get("associated_to_candidate") is True)
    mask_hits = sum(1 for row in rows if row.get("projected_pixel_inside_mask") is True)
    box_hits = sum(1 for row in rows if row.get("projected_pixel_inside_box") is True)
    best_scores = [safe_float(row.get("best_box_score")) for row in rows]
    best_scores = [value for value in best_scores if value is not None]
    s_depth = min(1.0, strict_hits / 2.0)
    s_mask = min(1.0, mask_hits / 2.0)
    s_box = min(1.0, box_hits / 2.0)
    s_det = max(best_scores, default=0.0)
    return max(0.0, min(1.0, 0.45 * s_depth + 0.25 * s_mask + 0.15 * s_box + 0.15 * s_det))


def candidate_row(
    key: Tuple[str, str, str, str],
    rows: Sequence[Dict[str, Any]],
    frame_row: Optional[Dict[str, Any]],
    min_strict_hits: int,
) -> Dict[str, Any]:
    sample = rows[0]
    associated_rows = [row for row in rows if row.get("associated_to_candidate") is True]
    visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
    mask_rows = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    box_rows = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    score = evidence_score(rows)
    strict_hits = len(associated_rows)
    if strict_hits >= min_strict_hits:
        support_class = "strong_detector_support"
    elif strict_hits > 0:
        support_class = "weak_detector_support"
    elif mask_rows:
        support_class = "mask_overlap_without_depth_support"
    elif box_rows:
        support_class = "box_overlap_without_mask_depth_support"
    elif visible_rows:
        support_class = "visible_without_detector_overlap"
    else:
        support_class = "not_visible_from_sampled_views"

    return {
        "schema_version": SCHEMA_VERSION,
        "rival_identity_request_id": key[0],
        "episode_key": key[1],
        "query": key[2],
        "candidate_id": key[3],
        "scene_key": sample.get("scene_key"),
        "expanded_candidate_rank": sample.get("expanded_candidate_rank"),
        "target_semantic_rank": sample.get("target_semantic_rank"),
        "target_semantic_score": sample.get("target_semantic_score"),
        "target_support_score": sample.get("target_support_score"),
        "target_positive_support": sample.get("target_positive_support"),
        "source_pool_proxy_route": sample.get("source_pool_proxy_route"),
        "source_pool_saturated": sample.get("source_pool_saturated"),
        "source_pool_positive_support_candidate_count": sample.get("source_pool_positive_support_candidate_count"),
        "source_pool_top4_score_range": sample.get("source_pool_top4_score_range"),
        "source_pool_semantic_top2_score_gap": sample.get("source_pool_semantic_top2_score_gap"),
        "heading_rows": len(rows),
        "visible_heading_rows": len(visible_rows),
        "box_hit_heading_rows": len(box_rows),
        "mask_hit_heading_rows": len(mask_rows),
        "strict_association_heading_rows": strict_hits,
        "has_detector_box": None if frame_row is None else frame_row.get("has_detector_box"),
        "has_sam2_mask": None if frame_row is None else frame_row.get("has_sam2_mask"),
        "has_candidate_association": strict_hits > 0,
        "evidence_score": score,
        "detector_support_class": support_class,
        "best_box_score": numeric_stats(row.get("best_box_score") for row in rows),
        "depth_error_m": numeric_stats(row.get("depth_error_m") for row in rows),
        "projection_status_counts": counter_dict(row.get("projection_status") for row in rows),
        "depth_check_status_counts": counter_dict(row.get("depth_check_status") for row in rows),
        "projection_anchor_selected_offset_counts": counter_dict(
            row.get("projection_anchor_height_offset_m") for row in associated_rows
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
    }


def request_topology(row: Dict[str, Any], args: argparse.Namespace) -> str:
    strong_count = int(row["strong_candidate_count"])
    associated_count = int(row["associated_candidate_count"])
    top_strong = bool(row["source_top_strong"])
    top_associated = bool(row["source_top_associated"])
    if associated_count == 0:
        return "no_detector_evidence"
    if strong_count == 0:
        return "weak_detector_evidence_only"
    if strong_count == 1 and top_strong:
        return "single_strong_source_top"
    if strong_count == 1:
        return "single_strong_lower_rank"
    if bool(row["source_pool_saturated"]) or strong_count > int(args.max_strong_candidates_for_simple_objective):
        return "multi_strong_saturated_ambiguity"
    if top_associated:
        return "multi_associated_with_source_top"
    return "multi_associated_lower_rank_only"


def request_risk(topology: str) -> str:
    if topology == "no_detector_evidence":
        return "cannot_score_without_more_observation"
    if topology == "weak_detector_evidence_only":
        return "weak_evidence_terminal_commit_unsafe"
    if topology == "single_strong_source_top":
        return "candidate_for_simple_rule_but_still_diagnostic"
    if topology == "single_strong_lower_rank":
        return "source_top_challenged_by_lower_rank_evidence"
    return "multi_candidate_detector_ambiguity"


def build_rows(
    associations: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    frame_index = index_frame_rows(frame_rows)
    candidate_rows = [
        candidate_row(key, rows, frame_index.get(key), int(args.min_strict_hits_for_strong))
        for key, rows in sorted(group_by_candidate(associations).items())
    ]

    request_rows: List[Dict[str, Any]] = []
    for key, rows in sorted(group_by_request(candidate_rows).items()):
        associated = [row for row in rows if row["has_candidate_association"]]
        strong = [row for row in rows if row["strict_association_heading_rows"] >= int(args.min_strict_hits_for_strong)]
        positive = [row for row in rows if row.get("target_positive_support") is True]
        strong_positive = [row for row in strong if row.get("target_positive_support") is True]
        strong_nonpositive = [row for row in strong if row.get("target_positive_support") is not True]
        source_top_rows = [
            row
            for row in rows
            if row.get("expanded_candidate_rank") == 1 or row.get("target_semantic_rank") == 1
        ]
        source_top_associated = any(row["has_candidate_association"] for row in source_top_rows)
        source_top_strong = any(
            row["strict_association_heading_rows"] >= int(args.min_strict_hits_for_strong)
            for row in source_top_rows
        )
        best = max(rows, key=lambda row: (row["evidence_score"], -int(row.get("expanded_candidate_rank") or 9999)))
        source_pool_saturated = any(row.get("source_pool_saturated") is True for row in rows)
        request = {
            "schema_version": SCHEMA_VERSION,
            "rival_identity_request_id": key[0],
            "episode_key": key[1],
            "query": key[2],
            "scene_key": rows[0].get("scene_key"),
            "candidate_count": len(rows),
            "associated_candidate_count": len(associated),
            "strong_candidate_count": len(strong),
            "semantic_positive_candidate_count": len(positive),
            "strong_semantic_positive_candidate_count": len(strong_positive),
            "strong_semantic_nonpositive_candidate_count": len(strong_nonpositive),
            "source_top_associated": source_top_associated,
            "source_top_strong": source_top_strong,
            "lower_rank_only_association": bool(associated and not source_top_associated),
            "best_evidence_candidate_id": best["candidate_id"],
            "best_evidence_score": best["evidence_score"],
            "best_evidence_rank": best.get("expanded_candidate_rank"),
            "best_evidence_positive_support": best.get("target_positive_support"),
            "source_pool_saturated": source_pool_saturated,
            "source_pool_proxy_route": rows[0].get("source_pool_proxy_route"),
            "source_pool_positive_support_candidate_count": rows[0].get(
                "source_pool_positive_support_candidate_count"
            ),
            "detector_support_class_counts": counter_dict(row["detector_support_class"] for row in rows),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": False,
        }
        topology = request_topology(request, args)
        request["evidence_topology"] = topology
        request["terminal_objective_risk"] = request_risk(topology)
        request_rows.append(request)
    return candidate_rows, request_rows


def summarize(
    candidate_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    associations: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    request_count = len(request_rows)
    associated_requests = [row for row in request_rows if row["associated_candidate_count"] > 0]
    strong_requests = [row for row in request_rows if row["strong_candidate_count"] > 0]
    multi_strong_requests = [row for row in request_rows if row["strong_candidate_count"] > 1]
    lower_rank_only = [row for row in request_rows if row["lower_rank_only_association"]]
    topology_counts = Counter(row["evidence_topology"] for row in request_rows)
    risk_counts = Counter(row["terminal_objective_risk"] for row in request_rows)
    no_gt_action = not any(row.get("uses_gt_for_action") is True for row in associations)
    no_gt_analysis = not any(
        any(str(key).startswith("analysis_only") for key in row.keys()) for row in associations
    )
    diagnostic_gate = bool(
        candidate_rows
        and request_count >= int(args.min_request_rows)
        and no_gt_action
        and no_gt_analysis
        and len(frame_rows) == len(candidate_rows)
    )
    objective_design_allowed = bool(
        diagnostic_gate
        and ratio(len(associated_requests), request_count or 1) >= float(args.min_associated_request_rate)
    )
    terminal_objective_allowed = False

    return {
        "schema_version": SCHEMA_VERSION,
        "associations": str(args.associations),
        "detector_frame_summary": str(args.detector_frame_summary),
        "candidate_rows": len(candidate_rows),
        "request_rows": request_count,
        "association_heading_rows": len(associations),
        "frame_rows": len(frame_rows),
        "associated_request_count": len(associated_requests),
        "associated_request_rate": ratio(len(associated_requests), request_count),
        "strong_request_count": len(strong_requests),
        "strong_request_rate": ratio(len(strong_requests), request_count),
        "multi_strong_request_count": len(multi_strong_requests),
        "multi_strong_request_rate": ratio(len(multi_strong_requests), request_count),
        "lower_rank_only_association_count": len(lower_rank_only),
        "lower_rank_only_association_rate": ratio(len(lower_rank_only), request_count),
        "evidence_topology_counts": dict(sorted(topology_counts.items())),
        "terminal_objective_risk_counts": dict(sorted(risk_counts.items())),
        "query_topology_counts": {
            query: counter_dict(row["evidence_topology"] for row in rows)
            for query, rows in sorted(group_by_request_field(request_rows, "query").items())
        },
        "scene_topology_counts": {
            scene: counter_dict(row["evidence_topology"] for row in rows)
            for scene, rows in sorted(group_by_request_field(request_rows, "scene_key").items())
        },
        "candidate_evidence_score": numeric_stats(row.get("evidence_score") for row in candidate_rows),
        "gate": {
            "diagnostic_gate_passed": diagnostic_gate,
            "candidate_frame_rows_match": len(frame_rows) == len(candidate_rows),
            "min_request_rows": int(args.min_request_rows),
            "min_associated_request_rate": float(args.min_associated_request_rate),
            "associated_request_rate_pass": ratio(len(associated_requests), request_count) is not None
            and (ratio(len(associated_requests), request_count) or 0.0) >= float(args.min_associated_request_rate),
            "no_gt_action_pass": no_gt_action,
            "no_gt_analysis_pass": no_gt_analysis,
            "objective_design_allowed": objective_design_allowed,
            "terminal_objective_allowed": terminal_objective_allowed,
            "paper_scale_gate_passed": request_count >= int(args.min_paper_request_rows),
        },
        "interpretation": {
            "facts": [
                "This diagnostic reads frozen detector/SAM2 substrate outputs and does not rerun detector, segmenter, navigation, or ObjectNav evaluation.",
                "It summarizes request-level detector evidence topology before defining any terminal objective.",
            ],
            "agent_inference": [
                "Multi-strong or lower-rank-only detector evidence should be treated as ambiguity evidence, not as an immediate commit signal.",
                "A terminal objective remains blocked until this diagnostic is converted into a predeclared rule and tested on a larger source.",
            ],
            "user_decision_needed": [],
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "candidate_rows": "expanded_retrieval_detector_evidence_candidate_rows.jsonl",
            "request_rows": "expanded_retrieval_detector_evidence_request_rows.jsonl",
            "summary": "expanded_retrieval_detector_evidence_diagnostic_summary.json",
        },
    }


def group_by_request_field(rows: Sequence[Dict[str, Any]], field: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(field))].append(row)
    return grouped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    associations = load_jsonl(Path(args.associations))
    frame_rows = load_jsonl(Path(args.detector_frame_summary))
    candidate_rows, request_rows = build_rows(associations, frame_rows, args)
    summary = summarize(candidate_rows, request_rows, associations, frame_rows, args)
    summary["out_root"] = str(out_root)
    write_jsonl(out_root / "expanded_retrieval_detector_evidence_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "expanded_retrieval_detector_evidence_request_rows.jsonl", request_rows)
    write_json(out_root / "expanded_retrieval_detector_evidence_diagnostic_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose request-level detector evidence topology for expanded retrieval before terminal objectives."
    )
    parser.add_argument("--associations", required=True)
    parser.add_argument("--detector-frame-summary", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-strict-hits-for-strong", type=int, default=2)
    parser.add_argument("--max-strong-candidates-for-simple-objective", type=int, default=1)
    parser.add_argument("--min-request-rows", type=int, default=1)
    parser.add_argument("--min-paper-request-rows", type=int, default=20)
    parser.add_argument("--min-associated-request-rate", type=float, default=0.8)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
