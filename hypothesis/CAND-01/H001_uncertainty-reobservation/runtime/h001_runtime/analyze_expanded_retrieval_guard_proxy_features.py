import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_guard_proxy_features.v1"
FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "selected_for_goal",
    "wrong_goal_visit",
    "success",
    "evaluation_only_candidate_correct",
    "evaluation_only_goal_visit",
    "evaluation_only_wrong_goal_visit",
    "evaluation_only_wasted_path_from_candidate",
    "analysis_only_candidate_set_taxonomy",
    "analysis_only_correct_candidate_count",
    "analysis_only_wrong_goal_candidate_count",
    "analysis_only_full_pool_correct_candidate_count",
}


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


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) != 3:
        return None
    items = [safe_float(item) for item in value]
    if any(item is None for item in items):
        return None
    return [float(item) for item in items]


def horizontal_distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def candidate_position(candidate: Dict[str, Any]) -> Optional[List[float]]:
    return vector3(candidate.get("visit_position")) or vector3(candidate.get("position"))


def finite_scores(candidates: Sequence[Dict[str, Any]]) -> List[float]:
    scores: List[float] = []
    for candidate in candidates:
        score = safe_float(candidate.get("support_score"))
        if score is None:
            score = safe_float(candidate.get("semantic_score"))
        if score is not None:
            scores.append(score)
    return scores


def pairwise_distances(positions: Sequence[Sequence[float]]) -> List[float]:
    distances: List[float] = []
    for left_index, left in enumerate(positions):
        for right in positions[left_index + 1 :]:
            distances.append(horizontal_distance(left, right))
    return distances


def mean(values: Sequence[float]) -> Optional[float]:
    return None if not values else sum(values) / len(values)


def row_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(row.get("rival_identity_request_id")),
        str(row.get("episode_key")),
        str(row.get("query")),
    )


def index_guard(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    return {row_key(row): row for row in rows}


def forbidden_key_count(row: Dict[str, Any]) -> int:
    count = 0
    for key in FORBIDDEN_ACTION_KEYS:
        if key in row:
            count += 1
    for candidate in row.get("expanded_candidates") or []:
        for key in FORBIDDEN_ACTION_KEYS:
            if key in candidate:
                count += 1
    return count


def candidate_fingerprint(row: Dict[str, Any]) -> str:
    candidate_ids = [str(candidate.get("candidate_id")) for candidate in row.get("expanded_candidates") or []]
    payload = json.dumps(
        {
            "scene_key": row.get("scene_key"),
            "query": row.get("query"),
            "candidate_ids": candidate_ids,
        },
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]


def extract_features(row: Dict[str, Any], duplicate_fingerprint_count: int) -> Dict[str, Any]:
    candidates = sorted(
        list(row.get("expanded_candidates") or []),
        key=lambda candidate: (safe_int(candidate.get("selection_rank")), str(candidate.get("candidate_id"))),
    )
    scores = finite_scores(candidates)
    first4 = scores[:4]
    positions = [position for position in (candidate_position(candidate) for candidate in candidates) if position]
    distances = pairwise_distances(positions)
    positive_support_count = sum(1 for candidate in candidates if candidate.get("positive_support") is True)
    finite_position_count = len(positions)
    candidate_reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is True)
    known_reachability_count = sum(
        1 for candidate in candidates if candidate.get("candidate_reachable") is not None
    )
    path_costs = [
        cost
        for cost in (safe_float(candidate.get("path_to_candidate")) for candidate in candidates)
        if cost is not None
    ]
    source_count = safe_int(row.get("source_candidate_count"), default=0)
    source_positive = safe_int(row.get("source_positive_support_candidate_count"), default=0)
    top_score = scores[0] if scores else None
    second_score = scores[1] if len(scores) > 1 else None
    top2_margin = None if top_score is None or second_score is None else top_score - second_score
    top4_score_range = None if len(first4) < 2 else max(first4) - min(first4)
    score_spread = None if len(scores) < 2 else max(scores) - min(scores)

    return {
        "source_candidate_count": source_count,
        "source_positive_support_candidate_count": source_positive,
        "source_positive_support_rate": ratio(source_positive, source_count),
        "expanded_candidate_count": len(candidates),
        "expanded_positive_support_candidate_count": positive_support_count,
        "expanded_positive_support_rate": ratio(positive_support_count, len(candidates)),
        "finite_position_count": finite_position_count,
        "finite_position_rate": ratio(finite_position_count, len(candidates)),
        "candidate_reachable_count": candidate_reachable_count,
        "known_reachability_count": known_reachability_count,
        "known_reachability_rate": ratio(known_reachability_count, len(candidates)),
        "min_path_to_candidate": min(path_costs) if path_costs else None,
        "top_score": top_score,
        "second_score": second_score,
        "top2_score_margin": top2_margin,
        "top4_score_range": top4_score_range,
        "score_spread": score_spread,
        "score_zero_count": sum(1 for score in scores if score == 0.0),
        "score_ge_0_90_count": sum(1 for score in scores if score >= 0.90),
        "score_ge_0_95_count": sum(1 for score in scores if score >= 0.95),
        "positive_support_top4_count": sum(
            1 for candidate in candidates[:4] if candidate.get("positive_support") is True
        ),
        "min_semantic_rank": min((safe_int(candidate.get("semantic_rank")) for candidate in candidates), default=None),
        "max_semantic_rank": max((safe_int(candidate.get("semantic_rank"), 0) for candidate in candidates), default=None),
        "candidate_fingerprint": candidate_fingerprint(row),
        "duplicate_fingerprint_count": duplicate_fingerprint_count,
        "spatial_pair_min_distance": min(distances) if distances else None,
        "spatial_pair_mean_distance": mean(distances),
        "spatial_pair_max_distance": max(distances) if distances else None,
    }


def proxy_decision(features: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    pool_quality_insufficient = bool(
        features["source_candidate_count"] < args.min_source_candidates
        or features["expanded_candidate_count"] < args.min_expanded_candidates
        or features["finite_position_count"] < args.min_finite_positions
        or features["expanded_positive_support_candidate_count"] == 0
        or (
            features["top_score"] is not None
            and features["top_score"] < args.min_top_score
        )
    )
    low_margin = bool(
        features["top2_score_margin"] is not None
        and features["top2_score_margin"] <= args.low_top2_margin
    )
    saturated_top4 = bool(
        features["top4_score_range"] is not None
        and features["top4_score_range"] <= args.low_top4_range
    )
    many_positive_support = features["expanded_positive_support_candidate_count"] >= args.ambiguous_positive_support_count
    many_high_score = features["score_ge_0_90_count"] >= args.high_score_count
    duplicate_fingerprint = features["duplicate_fingerprint_count"] > 1
    ambiguity_proxy = bool(low_margin or saturated_top4 or many_positive_support or many_high_score or duplicate_fingerprint)

    if pool_quality_insufficient:
        route = "request_backend_retrieval_revision_proxy"
        detector_allowed = False
        reason = "non_gt_pool_quality_insufficient"
    elif ambiguity_proxy:
        route = "request_detector_guarded_observation_proxy"
        detector_allowed = True
        reason = "non_gt_candidate_set_ambiguous"
    else:
        route = "request_lightweight_confirmation_proxy"
        detector_allowed = True
        reason = "non_gt_candidate_set_low_ambiguity"

    return {
        "proxy_route": route,
        "proxy_reason": reason,
        "pool_quality_insufficient_proxy": pool_quality_insufficient,
        "ambiguity_proxy": ambiguity_proxy,
        "low_margin_proxy": low_margin,
        "saturated_top4_proxy": saturated_top4,
        "many_positive_support_proxy": many_positive_support,
        "many_high_score_proxy": many_high_score,
        "duplicate_fingerprint_proxy": duplicate_fingerprint,
        "detector_evidence_allowed_by_proxy": detector_allowed,
        "terminal_commit_allowed_by_proxy": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    candidate_rows = load_jsonl(Path(args.candidate_set))
    guard_rows = load_jsonl(Path(args.guard_design_rows)) if args.guard_design_rows else []
    guard_index = index_guard(guard_rows)
    fingerprint_counts = Counter(candidate_fingerprint(row) for row in candidate_rows)

    out_rows: List[Dict[str, Any]] = []
    proxy_route_counts: Counter[str] = Counter()
    target_route_counts: Counter[str] = Counter()
    forbidden_rows = 0
    target_backend_rows = 0
    target_backend_proxy_backend_rows = 0
    target_backend_proxy_evidence_rows = 0
    target_evidence_rows = 0
    target_evidence_proxy_evidence_rows = 0
    target_evidence_proxy_backend_rows = 0

    for row in candidate_rows:
        forbidden_rows += int(forbidden_key_count(row) > 0)
        features = extract_features(row, fingerprint_counts[candidate_fingerprint(row)])
        decision = proxy_decision(features, args)
        guard = guard_index.get(row_key(row))
        target_route = None if guard is None else guard.get("guard_design_route")
        if target_route:
            target_route_counts[str(target_route)] += 1
        proxy_route_counts[str(decision["proxy_route"])] += 1

        target_is_backend = target_route == "request_backend_retrieval_revision"
        target_is_evidence = target_route in {
            "request_detector_guarded_observation",
            "request_lightweight_confirmation",
        }
        proxy_is_backend = decision["proxy_route"] == "request_backend_retrieval_revision_proxy"
        proxy_is_evidence = decision["detector_evidence_allowed_by_proxy"] is True
        target_backend_rows += int(target_is_backend)
        target_backend_proxy_backend_rows += int(target_is_backend and proxy_is_backend)
        target_backend_proxy_evidence_rows += int(target_is_backend and proxy_is_evidence)
        target_evidence_rows += int(target_is_evidence)
        target_evidence_proxy_evidence_rows += int(target_is_evidence and proxy_is_evidence)
        target_evidence_proxy_backend_rows += int(target_is_evidence and proxy_is_backend)

        out_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "revision_branch": row.get("revision_branch"),
                "revision_reason": row.get("revision_reason"),
                "source_reason": row.get("source_reason"),
                "non_gt_features": features,
                "proxy_decision": decision,
                "analysis_only_target_route": target_route,
                "analysis_only_target_taxonomy": None
                if guard is None
                else guard.get("analysis_only_candidate_set_taxonomy"),
                "analysis_only_proxy_matches_target_route": None
                if target_route is None
                else (
                    (target_route == "request_backend_retrieval_revision" and proxy_is_backend)
                    or (
                        target_route
                        in {"request_detector_guarded_observation", "request_lightweight_confirmation"}
                        and proxy_is_evidence
                    )
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": bool(guard_rows),
                "paper_claim_allowed": False,
            }
        )

    row_count = len(candidate_rows)
    source_pool_validity_proxy_recall = ratio(target_backend_proxy_backend_rows, target_backend_rows)
    evidence_allowed_target_recall = ratio(target_evidence_proxy_evidence_rows, target_evidence_rows)
    feature_gate = {
        "all_candidate_rows_processed": len(out_rows) == row_count,
        "no_forbidden_action_keys": forbidden_rows == 0,
        "uses_gt_for_action": False,
        "terminal_commit_allowed_rows": 0,
        "feature_extraction_gate_passed": len(out_rows) == row_count and forbidden_rows == 0,
    }
    proxy_gate = {
        "source_pool_validity_proxy_gate_passed": source_pool_validity_proxy_recall == 1.0,
        "evidence_allowed_target_recall_passed": evidence_allowed_target_recall == 1.0,
        "no_backend_target_escalated_to_evidence": target_backend_proxy_evidence_rows == 0,
        "no_terminal_commit_allowed": True,
        "proxy_ready_for_detector_gate": False,
    }
    proxy_gate["proxy_ready_for_detector_gate"] = (
        feature_gate["feature_extraction_gate_passed"] is True
        and proxy_gate["source_pool_validity_proxy_gate_passed"] is True
        and proxy_gate["evidence_allowed_target_recall_passed"] is True
        and proxy_gate["no_backend_target_escalated_to_evidence"] is True
        and proxy_gate["no_terminal_commit_allowed"] is True
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_set": str(args.candidate_set),
        "guard_design_rows": str(args.guard_design_rows) if args.guard_design_rows else None,
        "request_rows": row_count,
        "forbidden_action_feature_rows": forbidden_rows,
        "proxy_route_counts": dict(sorted(proxy_route_counts.items())),
        "analysis_only_target_route_counts": dict(sorted(target_route_counts.items())),
        "target_backend_rows": target_backend_rows,
        "target_backend_proxy_backend_rows": target_backend_proxy_backend_rows,
        "target_backend_proxy_evidence_rows": target_backend_proxy_evidence_rows,
        "target_evidence_rows": target_evidence_rows,
        "target_evidence_proxy_evidence_rows": target_evidence_proxy_evidence_rows,
        "target_evidence_proxy_backend_rows": target_evidence_proxy_backend_rows,
        "source_pool_validity_proxy_recall": source_pool_validity_proxy_recall,
        "evidence_allowed_target_recall": evidence_allowed_target_recall,
        "feature_gate": feature_gate,
        "proxy_gate": proxy_gate,
        "proxy_thresholds": {
            "min_source_candidates": args.min_source_candidates,
            "min_expanded_candidates": args.min_expanded_candidates,
            "min_finite_positions": args.min_finite_positions,
            "min_top_score": args.min_top_score,
            "low_top2_margin": args.low_top2_margin,
            "low_top4_range": args.low_top4_range,
            "ambiguous_positive_support_count": args.ambiguous_positive_support_count,
            "high_score_count": args.high_score_count,
        },
        "interpretation": {
            "facts": (
                "The extracted non-GT features are available at action time and the proxy never allows "
                "terminal commit."
            ),
            "inference": (
                "Current candidate-set features do not reliably identify source-pool no-valid rows if "
                "source_pool_validity_proxy_gate_passed is false. Detector evidence design should remain "
                "blocked until a stronger non-GT source-pool validity proxy is added."
            ),
        },
        "output_files": {
            "rows": "expanded_retrieval_guard_proxy_feature_rows.jsonl",
            "summary": "expanded_retrieval_guard_proxy_feature_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(guard_rows),
        "paper_claim_allowed": False,
    }
    write_jsonl(out_root / "expanded_retrieval_guard_proxy_feature_rows.jsonl", out_rows)
    write_json(out_root / "expanded_retrieval_guard_proxy_feature_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract non-GT expanded-retrieval guard proxy features and audit them against guard design targets."
    )
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--guard-design-rows")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-source-candidates", type=int, default=6)
    parser.add_argument("--min-expanded-candidates", type=int, default=6)
    parser.add_argument("--min-finite-positions", type=int, default=6)
    parser.add_argument("--min-top-score", type=float, default=0.50)
    parser.add_argument("--low-top2-margin", type=float, default=0.005)
    parser.add_argument("--low-top4-range", type=float, default=0.020)
    parser.add_argument("--ambiguous-positive-support-count", type=int, default=2)
    parser.add_argument("--high-score-count", type=int, default=4)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
