import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_source_pool_validity_proxy.v1"
ACTION_FEATURE_SOURCE = "non_gt_source_pool_score_shape"
FORBIDDEN_CONSUMED_KEYS = {
    "candidate_correct",
    "selected_for_goal",
    "wrong_goal_visit",
    "success",
    "evaluation_only_candidate_correct",
    "evaluation_only_goal_visit",
    "evaluation_only_wrong_goal_visit",
    "evaluation_only_wasted_path_from_candidate",
    "parent_episode_class_for_analysis",
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


def row_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (
        str(row.get("rival_identity_request_id")),
        str(row.get("episode_key")),
        str(row.get("query")),
    )


def action_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (str(row.get("episode_key")), str(row.get("query")))


def index_by_action_key(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {action_key(row): row for row in rows}


def index_guard(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    return {row_key(row): row for row in rows}


def candidate_score(candidate: Dict[str, Any]) -> Optional[float]:
    score = safe_float(candidate.get("support_score"))
    return score if score is not None else safe_float(candidate.get("semantic_score"))


def rank_candidates(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        (dict(candidate) for candidate in candidates),
        key=lambda candidate: (
            safe_int(candidate.get("semantic_rank")),
            -(candidate_score(candidate) or -math.inf),
            str(candidate.get("candidate_id")),
        ),
    )


def score_range(scores: Sequence[float]) -> Optional[float]:
    return None if len(scores) < 2 else max(scores) - min(scores)


def count_consumed_forbidden_keys(feature_payload: Dict[str, Any]) -> int:
    return sum(1 for key in FORBIDDEN_CONSUMED_KEYS if key in feature_payload)


def source_pool_features(action_row: Dict[str, Any]) -> Dict[str, Any]:
    candidates = rank_candidates(action_row.get("candidate_evidence") or [])
    scores = [score for score in (candidate_score(candidate) for candidate in candidates) if score is not None]
    top4 = scores[:4]
    positive_support_count = sum(1 for candidate in candidates if candidate.get("positive_support") is True)
    reachable_count = sum(1 for candidate in candidates if candidate.get("candidate_reachable") is True)
    known_reachability_count = sum(
        1 for candidate in candidates if candidate.get("candidate_reachable") is not None
    )

    features = {
        "feature_source": ACTION_FEATURE_SOURCE,
        "candidate_count": len(candidates),
        "positive_support_candidate_count": positive_support_count,
        "positive_support_candidate_rate": ratio(positive_support_count, len(candidates)),
        "known_reachability_count": known_reachability_count,
        "known_reachability_rate": ratio(known_reachability_count, len(candidates)),
        "reachable_candidate_count": reachable_count,
        "top_candidate_score": scores[0] if scores else None,
        "semantic_top2_score_gap": safe_float(action_row.get("semantic_top2_score_gap")),
        "top_score_uncertainty": safe_float(action_row.get("top_score_uncertainty")),
        "top_margin_uncertainty": safe_float(action_row.get("top_margin_uncertainty")),
        "top_U_sem": safe_float(action_row.get("top_U_sem")),
        "top4_score_range": score_range(top4),
        "top20_score_range": score_range(scores[:20]),
        "score_ge_0_90_count": sum(1 for score in scores if score >= 0.90),
        "score_ge_0_91_count": sum(1 for score in scores if score >= 0.91),
        "score_ge_0_95_count": sum(1 for score in scores if score >= 0.95),
        "positive_support_top4_count": sum(
            1 for candidate in candidates[:4] if candidate.get("positive_support") is True
        ),
        "min_semantic_rank": min((safe_int(candidate.get("semantic_rank")) for candidate in candidates), default=None),
        "max_semantic_rank": max((safe_int(candidate.get("semantic_rank"), 0) for candidate in candidates), default=None),
        "consumed_action_fields": [
            "candidate_evidence.candidate_id",
            "candidate_evidence.semantic_rank",
            "candidate_evidence.semantic_score",
            "candidate_evidence.support_score",
            "candidate_evidence.positive_support",
            "candidate_evidence.candidate_reachable",
            "semantic_top2_score_gap",
            "top_score_uncertainty",
            "top_margin_uncertainty",
            "top_U_sem",
        ],
    }
    features["consumed_forbidden_key_count"] = count_consumed_forbidden_keys(features)
    return features


def source_pool_proxy_decision(features: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    top_score = safe_float(features.get("top_candidate_score"))
    top4_range = safe_float(features.get("top4_score_range"))
    score_ge_floor_count = safe_int(features.get("score_ge_0_91_count"), default=0)
    top_score_uncertainty = safe_float(features.get("top_score_uncertainty"))
    top2_gap = safe_float(features.get("semantic_top2_score_gap"))

    low_absolute_evidence = bool(top_score is not None and top_score < args.min_source_top_score)
    saturated_source_pool = bool(top4_range is not None and top4_range <= args.max_source_top4_range)
    no_high_confidence_candidate = score_ge_floor_count <= args.max_score_ge_091_count_for_invalid
    high_top_uncertainty = bool(
        top_score_uncertainty is not None and top_score_uncertainty >= args.min_top_score_uncertainty
    )
    near_tie_top = bool(top2_gap is not None and top2_gap <= args.max_top2_gap_for_invalid)
    source_pool_invalid_proxy = bool(
        low_absolute_evidence
        and saturated_source_pool
        and no_high_confidence_candidate
        and (high_top_uncertainty or near_tie_top)
    )

    if source_pool_invalid_proxy:
        route = "request_backend_retrieval_revision_proxy"
        reason = "source_pool_low_absolute_score_and_saturated_top_candidates"
        detector_allowed = False
    else:
        route = "request_detector_guarded_observation_proxy"
        reason = "source_pool_validity_not_rejected_by_score_shape"
        detector_allowed = True

    return {
        "proxy_route": route,
        "proxy_reason": reason,
        "source_pool_invalid_proxy": source_pool_invalid_proxy,
        "low_absolute_evidence": low_absolute_evidence,
        "saturated_source_pool": saturated_source_pool,
        "no_high_confidence_candidate": no_high_confidence_candidate,
        "high_top_uncertainty": high_top_uncertainty,
        "near_tie_top": near_tie_top,
        "detector_evidence_allowed_by_proxy": detector_allowed,
        "terminal_commit_allowed_by_proxy": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    candidate_rows = load_jsonl(Path(args.candidate_set))
    action_rows = index_by_action_key(load_jsonl(Path(args.action_evidence_rows)))
    guard_rows = load_jsonl(Path(args.guard_design_rows)) if args.guard_design_rows else []
    guard_index = index_guard(guard_rows)

    out_rows: List[Dict[str, Any]] = []
    missing_action_rows = 0
    consumed_forbidden_rows = 0
    proxy_route_counts: Counter[str] = Counter()
    target_route_counts: Counter[str] = Counter()
    target_backend_rows = 0
    target_backend_proxy_backend_rows = 0
    target_backend_proxy_evidence_rows = 0
    target_evidence_rows = 0
    target_evidence_proxy_evidence_rows = 0
    target_evidence_proxy_backend_rows = 0
    detector_proxy_request_rows = 0

    for row in candidate_rows:
        action = action_rows.get(action_key(row))
        if action is None:
            missing_action_rows += 1
            continue
        features = source_pool_features(action)
        consumed_forbidden_rows += int(features["consumed_forbidden_key_count"] > 0)
        decision = source_pool_proxy_decision(features, args)
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
        detector_proxy_request_rows += int(proxy_is_evidence)
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
                "source_pool_features": features,
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

    source_pool_validity_proxy_recall = ratio(target_backend_proxy_backend_rows, target_backend_rows)
    evidence_allowed_target_recall = ratio(target_evidence_proxy_evidence_rows, target_evidence_rows)
    has_analysis_targets = bool(guard_rows)
    analysis_target_gate_passed = (
        source_pool_validity_proxy_recall == 1.0
        and evidence_allowed_target_recall == 1.0
        and target_backend_proxy_evidence_rows == 0
        and target_evidence_proxy_backend_rows == 0
    )
    action_only_detector_gate_passed = (
        len(out_rows) == len(candidate_rows)
        and missing_action_rows == 0
        and consumed_forbidden_rows == 0
        and detector_proxy_request_rows >= int(args.min_detector_proxy_request_rows)
    )
    proxy_gate = {
        "all_candidate_rows_processed": len(out_rows) == len(candidate_rows),
        "missing_action_rows": missing_action_rows,
        "no_consumed_forbidden_keys": consumed_forbidden_rows == 0,
        "has_analysis_targets": has_analysis_targets,
        "source_pool_validity_proxy_gate_passed": (source_pool_validity_proxy_recall == 1.0)
        if has_analysis_targets
        else None,
        "evidence_allowed_target_recall_passed": (evidence_allowed_target_recall == 1.0)
        if has_analysis_targets
        else None,
        "no_backend_target_escalated_to_evidence": target_backend_proxy_evidence_rows == 0,
        "no_evidence_target_blocked_as_backend": target_evidence_proxy_backend_rows == 0,
        "detector_proxy_request_rows_min_pass": detector_proxy_request_rows >= int(args.min_detector_proxy_request_rows),
        "action_only_detector_gate_passed": action_only_detector_gate_passed,
        "analysis_target_gate_passed": analysis_target_gate_passed if has_analysis_targets else None,
        "no_terminal_commit_allowed": True,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    proxy_gate["proxy_ready_for_detector_gate"] = (
        action_only_detector_gate_passed
        and (analysis_target_gate_passed if has_analysis_targets else True)
        and proxy_gate["no_terminal_commit_allowed"] is True
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "candidate_set": str(args.candidate_set),
        "action_evidence_rows": str(args.action_evidence_rows),
        "guard_design_rows": str(args.guard_design_rows) if args.guard_design_rows else None,
        "request_rows": len(candidate_rows),
        "proxy_route_counts": dict(sorted(proxy_route_counts.items())),
        "analysis_only_target_route_counts": dict(sorted(target_route_counts.items())),
        "target_backend_rows": target_backend_rows,
        "target_backend_proxy_backend_rows": target_backend_proxy_backend_rows,
        "target_backend_proxy_evidence_rows": target_backend_proxy_evidence_rows,
        "target_evidence_rows": target_evidence_rows,
        "target_evidence_proxy_evidence_rows": target_evidence_proxy_evidence_rows,
        "target_evidence_proxy_backend_rows": target_evidence_proxy_backend_rows,
        "detector_proxy_request_rows": detector_proxy_request_rows,
        "source_pool_validity_proxy_recall": source_pool_validity_proxy_recall,
        "evidence_allowed_target_recall": evidence_allowed_target_recall,
        "consumed_forbidden_rows": consumed_forbidden_rows,
        "proxy_gate": proxy_gate,
        "proxy_thresholds": {
            "min_source_top_score": args.min_source_top_score,
            "max_source_top4_range": args.max_source_top4_range,
            "max_score_ge_091_count_for_invalid": args.max_score_ge_091_count_for_invalid,
            "min_top_score_uncertainty": args.min_top_score_uncertainty,
            "max_top2_gap_for_invalid": args.max_top2_gap_for_invalid,
            "min_detector_proxy_request_rows": args.min_detector_proxy_request_rows,
        },
        "interpretation": {
            "facts": (
                "The proxy consumes only non-GT source-pool score-shape fields and blocks terminal commit."
            ),
            "inference": (
                "On the current diagnostic rows, a low absolute top score plus saturated top candidates "
                "separates source-pool no-valid rows from evidence-eligible rows. This is a diagnostic "
                "gate, not a paper-facing claim. On fresh sources without analysis-only guard labels, "
                "the gate only checks action-time processing, forbidden-key separation, and detector-row "
                "availability."
            ),
        },
        "output_files": {
            "rows": "expanded_retrieval_source_pool_validity_proxy_rows.jsonl",
            "summary": "expanded_retrieval_source_pool_validity_proxy_summary.json",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(guard_rows),
        "paper_claim_allowed": False,
    }
    write_jsonl(out_root / "expanded_retrieval_source_pool_validity_proxy_rows.jsonl", out_rows)
    write_json(out_root / "expanded_retrieval_source_pool_validity_proxy_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit a stronger non-GT source-pool validity proxy for expanded retrieval."
    )
    parser.add_argument("--candidate-set", required=True)
    parser.add_argument("--action-evidence-rows", required=True)
    parser.add_argument("--guard-design-rows")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-source-top-score", type=float, default=0.91)
    parser.add_argument("--max-source-top4-range", type=float, default=0.002)
    parser.add_argument("--max-score-ge-091-count-for-invalid", type=int, default=0)
    parser.add_argument("--min-top-score-uncertainty", type=float, default=0.09)
    parser.add_argument("--max-top2-gap-for-invalid", type=float, default=0.001)
    parser.add_argument("--min-detector-proxy-request-rows", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
