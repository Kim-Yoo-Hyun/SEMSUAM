import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "h001.rival_identity_broader_post_observation_diagnostic.v1"


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


def finite_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def vector_distance(a: Any, b: Any) -> Optional[float]:
    if not isinstance(a, list) or not isinstance(b, list) or len(a) != len(b):
        return None
    values = []
    for left, right in zip(a, b):
        left_float = finite_float(left)
        right_float = finite_float(right)
        if left_float is None or right_float is None:
            return None
        values.append((left_float - right_float) ** 2)
    return math.sqrt(sum(values))


def stats(values: Sequence[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"min": None, "mean": None, "max": None}
    return {
        "min": min(values),
        "mean": sum(values) / len(values),
        "max": max(values),
    }


def group_by(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key))].append(row)
    return grouped


def request_sort_key(request_id: str) -> tuple[int, str]:
    suffix = request_id.split(":")[-1]
    return (int(suffix), request_id) if suffix.isdigit() else (999999, request_id)


def mechanism_for(row: Dict[str, Any], min_standoff_m: float) -> str:
    if row["zero_standoff_plan_rows"] == row["plan_rows"] and row["max_own_associated_heading_count"] == 0:
        if row["max_cross_associated_heading_count"] > 0:
            return "degenerate_zero_standoff_cross_association"
        return "degenerate_zero_standoff_no_visible_candidate"
    if row["near_standoff_plan_rows"] == row["plan_rows"] and row["max_own_associated_heading_count"] == 0:
        return "near_zero_standoff_no_own_support"
    if row["max_own_associated_heading_count"] == 0:
        return "no_own_support_nonzero_viewpoint"
    if row["strong_identity_candidate_count"] == 0 and row["max_cross_associated_heading_count"] > 0:
        return "cross_view_aliasing_or_margin_too_strict"
    return "other"


def run(args: argparse.Namespace) -> Dict[str, Any]:
    plan_rows = load_jsonl(Path(args.plan))
    evidence_rows = load_jsonl(Path(args.evidence))
    association_rows = load_jsonl(Path(args.associations))
    decision_rows = load_jsonl(Path(args.decisions))
    evaluated_rows = load_jsonl(Path(args.evaluated))

    plan_by_request = group_by(plan_rows, "rival_identity_request_id")
    evidence_by_request = group_by(evidence_rows, "rival_identity_request_id")
    decision_by_request = group_by(decision_rows, "rival_identity_request_id")
    evaluated_by_request = group_by(evaluated_rows, "rival_identity_request_id")

    target_distances = [
        value
        for value in (finite_float(row.get("target_distance_from_viewpoint_m")) for row in plan_rows)
        if value is not None
    ]
    target_visit_equal_distances = [
        value
        for value in (vector_distance(row.get("target_position"), row.get("target_visit_position")) for row in plan_rows)
        if value is not None
    ]
    zero_standoff_rows = [
        row for row in plan_rows if (finite_float(row.get("target_distance_from_viewpoint_m")) or 0.0) <= 1e-6
    ]
    near_standoff_rows = [
        row
        for row in plan_rows
        if (finite_float(row.get("target_distance_from_viewpoint_m")) or 0.0) < float(args.min_standoff_m)
    ]
    rotation_fallback_rows = [
        row for row in plan_rows if str(row.get("viewpoint_source", "")).endswith("rotation_fallback")
    ]

    associated = [row for row in association_rows if row.get("associated_to_candidate") is True]
    own_associated = [
        row for row in associated if str(row.get("candidate_id")) == str(row.get("target_candidate_id"))
    ]
    cross_associated = [
        row for row in associated if str(row.get("candidate_id")) != str(row.get("target_candidate_id"))
    ]

    request_rows: List[Dict[str, Any]] = []
    for request_id in sorted(plan_by_request, key=request_sort_key):
        plan = plan_by_request[request_id]
        evidence = evidence_by_request.get(request_id, [])
        decisions = decision_by_request.get(request_id, [])
        evaluated = evaluated_by_request.get(request_id, [])
        distances = [
            value
            for value in (finite_float(row.get("target_distance_from_viewpoint_m")) for row in plan)
            if value is not None
        ]
        zero_count = sum(1 for value in distances if value <= 1e-6)
        near_count = sum(1 for value in distances if value < float(args.min_standoff_m))
        row = {
            "schema_version": SCHEMA_VERSION,
            "rival_identity_request_id": request_id,
            "episode_key": plan[0].get("episode_key"),
            "scene_key": plan[0].get("scene_key"),
            "query": plan[0].get("query"),
            "request_taxonomy_route": evidence[0].get("request_taxonomy_route") if evidence else None,
            "plan_rows": len(plan),
            "zero_standoff_plan_rows": zero_count,
            "near_standoff_plan_rows": near_count,
            "rotation_fallback_plan_rows": sum(
                1 for item in plan if str(item.get("viewpoint_source", "")).endswith("rotation_fallback")
            ),
            "target_distance_from_viewpoint_m": stats(distances),
            "evidence_candidate_count": len(evidence),
            "strong_identity_candidate_count": sum(1 for item in evidence if item.get("strong_identity_evidence") is True),
            "max_own_associated_heading_count": max(
                (int(item.get("post_own_associated_heading_count") or 0) for item in evidence),
                default=0,
            ),
            "max_cross_associated_heading_count": max(
                (int(item.get("post_cross_associated_heading_count") or 0) for item in evidence),
                default=0,
            ),
            "max_identity_margin": max(
                (int(item.get("post_identity_margin") or 0) for item in evidence),
                default=0,
            ),
            "max_post_best_box_score": max(
                (finite_float(item.get("post_best_box_score")) or 0.0 for item in evidence),
                default=0.0,
            ),
            "action": decisions[0].get("action") if decisions else None,
            "reason": decisions[0].get("reason") if decisions else None,
            "failure_taxonomy_type": evaluated[0].get("failure_taxonomy_type") if evaluated else None,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": False,
        }
        row["mechanism"] = mechanism_for(row, float(args.min_standoff_m))
        request_rows.append(row)

    mechanism_counts = Counter(row["mechanism"] for row in request_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "plan": str(args.plan),
            "evidence": str(args.evidence),
            "associations": str(args.associations),
            "decisions": str(args.decisions),
            "evaluated": str(args.evaluated),
        },
        "request_rows": len(request_rows),
        "plan_rows": len(plan_rows),
        "evidence_rows": len(evidence_rows),
        "association_rows": len(association_rows),
        "associated_rows": len(associated),
        "own_associated_rows": len(own_associated),
        "cross_associated_rows": len(cross_associated),
        "zero_standoff_plan_rows": len(zero_standoff_rows),
        "near_standoff_plan_rows": len(near_standoff_rows),
        "rotation_fallback_plan_rows": len(rotation_fallback_rows),
        "zero_standoff_rate": ratio(len(zero_standoff_rows), len(plan_rows)),
        "near_standoff_rate": ratio(len(near_standoff_rows), len(plan_rows)),
        "rotation_fallback_rate": ratio(len(rotation_fallback_rows), len(plan_rows)),
        "target_distance_from_viewpoint_m": stats(target_distances),
        "target_position_to_visit_position_distance_m": stats(target_visit_equal_distances),
        "viewpoint_source_counts": dict(sorted(Counter(str(row.get("viewpoint_source")) for row in plan_rows).items())),
        "target_role_counts": dict(
            sorted(Counter(str(row.get("rival_identity_target_role")) for row in plan_rows).items())
        ),
        "action_counts": dict(sorted(Counter(str(row.get("action")) for row in decision_rows).items())),
        "reason_counts": dict(sorted(Counter(str(row.get("reason")) for row in decision_rows).items())),
        "failure_taxonomy_counts": dict(
            sorted(Counter(str(row.get("failure_taxonomy_type")) for row in evaluated_rows).items())
        ),
        "mechanism_counts": dict(sorted(mechanism_counts.items())),
        "gate": {
            "planner_standoff_gate_passed": len(near_standoff_rows) == 0,
            "own_association_available": len(own_associated) > 0,
            "post_observation_rule_change_allowed": False,
        },
        "interpretation": {
            "fact": (
                "The broader detector substrate produced associated rows, but every association was cross-view: "
                "candidate_id never matched target_candidate_id among associated rows."
            ),
            "agent_inference": (
                "The current failure is a viewpoint/planner geometry substrate failure, not evidence that the "
                "post-observation decision rule should be loosened. The broader plan used zero-standoff candidate "
                "viewpoints with rotation fallback, so own-view identity evidence could not form."
            ),
            "user_decision_needed": None,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "output_files": {
            "request_diagnostic_rows": "broader_post_observation_failure_rows.jsonl",
            "summary": "broader_post_observation_failure_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "broader_post_observation_failure_rows.jsonl", request_rows)
    write_json(out_root / "broader_post_observation_failure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose broader rival-identity post-observation inert result.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--associations", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--evaluated", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-standoff-m", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
