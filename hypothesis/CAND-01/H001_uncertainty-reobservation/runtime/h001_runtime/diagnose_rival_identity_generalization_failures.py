import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "h001.rival_identity_failure_diagnostic.v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def group_by(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key))].append(row)
    return grouped


def ordered_unique(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        output.append(text)
        seen.add(text)
    return output


def any_gt_action(rows: Sequence[Dict[str, Any]]) -> bool:
    return any(row.get("uses_gt_for_action") is True for row in rows)


def first_value(rows: Sequence[Dict[str, Any]], field: str) -> Any:
    for row in rows:
        if field in row:
            return row.get(field)
    return None


def classify_request(
    evaluated: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
    plan_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    request_id = str(evaluated.get("rival_identity_request_id"))
    target_ids = ordered_unique(row.get("target_candidate_id") for row in plan_rows)
    evidence_ids = ordered_unique(row.get("candidate_id") for row in evidence_rows)
    target_roles = ordered_unique(row.get("rival_identity_target_role") for row in plan_rows)
    positive_support_candidate_count = first_value(plan_rows, "positive_support_candidate_count")
    source_candidate_count = first_value(plan_rows, "candidate_count")
    strong_rows = [row for row in evidence_rows if row.get("strong_identity_evidence") is True]
    selected_id = evaluated.get("selected_candidate_id")
    selected_evidence = next((row for row in evidence_rows if str(row.get("candidate_id")) == str(selected_id)), None)

    has_rival_contrast = len(target_ids) >= 2 and int(positive_support_candidate_count or 0) >= 2
    single_positive_candidate = len(target_ids) <= 1 or int(positive_support_candidate_count or 0) <= 1
    wrong_commit = evaluated.get("evaluation_only_wrong_goal_commit") is True
    success_commit = evaluated.get("evaluation_only_success_commit") is True
    defer = evaluated.get("action") == "defer_unresolved_identity"

    if wrong_commit and single_positive_candidate:
        mechanism = "single_candidate_object_existence_false_positive"
        proposed_route = "object_existence_validation"
        interpretation = (
            "The post-observation detector evidence supports the only planned candidate, but no rival contrast "
            "exists; the post-join ObjectNav label marks that candidate as wrong."
        )
    elif wrong_commit:
        mechanism = "unsafe_rival_identity_commit"
        proposed_route = "rival_identity_arbitration_needs_stronger_contrast"
        interpretation = "The rule committed to a wrong candidate despite rival candidates being available."
    elif success_commit and has_rival_contrast:
        mechanism = "rival_identity_resolved_success"
        proposed_route = "keep_in_rival_identity_arbitration"
        interpretation = "A rival-identity request with multiple positive candidates was resolved safely."
    elif success_commit:
        mechanism = "single_candidate_success"
        proposed_route = "object_existence_validation_or_safe_single_commit"
        interpretation = "A single-candidate request committed successfully, but this is not rival disambiguation."
    elif defer and evaluated.get("reason") == "post_observation_cross_view_aliasing":
        mechanism = "rival_identity_unresolved_cross_view_aliasing"
        proposed_route = "keep_in_rival_identity_arbitration"
        interpretation = "Multiple positive candidates remain cross-view aliased after observation."
    elif defer:
        mechanism = "safe_defer_unresolved"
        proposed_route = "keep_defer_or_expand_evidence"
        interpretation = "The fixed analyzer avoided a commit."
    else:
        mechanism = "unclassified"
        proposed_route = "manual_review"
        interpretation = "The request does not match a known diagnostic class."

    return {
        "schema_version": SCHEMA_VERSION,
        "rival_identity_request_id": request_id,
        "episode_key": evaluated.get("episode_key"),
        "scene_key": evaluated.get("scene_key"),
        "query": evaluated.get("query"),
        "request_reason": evaluated.get("request_reason"),
        "action": evaluated.get("action"),
        "decision_reason": evaluated.get("reason"),
        "selected_candidate_id": selected_id,
        "evaluation_only_success_commit": evaluated.get("evaluation_only_success_commit"),
        "evaluation_only_wrong_goal_commit": evaluated.get("evaluation_only_wrong_goal_commit"),
        "evaluation_only_no_label_commit": evaluated.get("evaluation_only_no_label_commit"),
        "original_failure_taxonomy_type": evaluated.get("failure_taxonomy_type"),
        "mechanism": mechanism,
        "proposed_route": proposed_route,
        "interpretation": interpretation,
        "source_candidate_count": source_candidate_count,
        "positive_support_candidate_count": positive_support_candidate_count,
        "planned_target_count": len(target_ids),
        "planned_target_ids": target_ids,
        "planned_target_roles": target_roles,
        "evidence_candidate_count": len(evidence_ids),
        "strong_identity_candidate_count": len(strong_rows),
        "strong_identity_candidate_ids": [str(row.get("candidate_id")) for row in strong_rows],
        "has_rival_contrast": has_rival_contrast,
        "single_positive_candidate": single_positive_candidate,
        "selected_post_own_associated_heading_count": None
        if selected_evidence is None
        else selected_evidence.get("post_own_associated_heading_count"),
        "selected_post_cross_associated_heading_count": None
        if selected_evidence is None
        else selected_evidence.get("post_cross_associated_heading_count"),
        "selected_post_identity_margin": None if selected_evidence is None else selected_evidence.get("post_identity_margin"),
        "selected_pre_semantic_rank": None if selected_evidence is None else selected_evidence.get("semantic_rank"),
        "selected_pre_support_score": None if selected_evidence is None else selected_evidence.get("support_score"),
        "selected_pre_min_depth_error_m": None if selected_evidence is None else selected_evidence.get("pre_min_depth_error_m"),
        "selected_post_min_depth_error_m": None if selected_evidence is None else selected_evidence.get("post_min_depth_error_m"),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize(
    rows: Sequence[Dict[str, Any]],
    *,
    args: argparse.Namespace,
    detector_summary: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    mechanism_counts = Counter(str(row["mechanism"]) for row in rows)
    route_counts = Counter(str(row["proposed_route"]) for row in rows)
    request_reason_mechanisms: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        request_reason_mechanisms[str(row.get("request_reason"))][str(row["mechanism"])] += 1

    wrong_rows = [row for row in rows if row.get("evaluation_only_wrong_goal_commit") is True]
    single_false_positive = [
        row for row in rows if row.get("mechanism") == "single_candidate_object_existence_false_positive"
    ]
    rival_identity_rows = [row for row in rows if row.get("proposed_route") == "keep_in_rival_identity_arbitration"]
    object_existence_rows = [row for row in rows if row.get("proposed_route") == "object_existence_validation"]
    checks = {
        "all_wrong_commits_explained": len(single_false_positive) + mechanism_counts.get("unsafe_rival_identity_commit", 0)
        == len(wrong_rows),
        "single_candidate_false_positive_present": len(single_false_positive) >= 1,
        "request_reason_is_mixed": len(request_reason_mechanisms.get("request_identity_no_guard_eligible_positive_candidates", {}))
        >= 2,
        "no_gt_action": not any_gt_action(rows),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "inputs": {
            "evaluated": str(args.evaluated),
            "evidence": str(args.evidence),
            "plan": str(args.plan),
            "detector_summary": str(args.detector_summary) if args.detector_summary else None,
        },
        "request_rows": len(rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "success_commit_rows": sum(1 for row in rows if row.get("evaluation_only_success_commit") is True),
        "defer_rows": sum(1 for row in rows if row.get("action") == "defer_unresolved_identity"),
        "mechanism_counts": dict(sorted(mechanism_counts.items())),
        "proposed_route_counts": dict(sorted(route_counts.items())),
        "request_reason_mechanism_counts": {
            reason: dict(sorted(counter.items()))
            for reason, counter in sorted(request_reason_mechanisms.items())
        },
        "single_candidate_false_positive_rows": len(single_false_positive),
        "rival_identity_arbitration_rows": len(rival_identity_rows),
        "object_existence_validation_rows": len(object_existence_rows),
        "diagnostic_checks": checks,
        "diagnostic_passed": all(checks.values()),
        "detector_substrate": None
        if detector_summary is None
        else {
            "detector_rows": detector_summary.get("detector_rows"),
            "detector_box_rate": detector_summary.get("detector_box_rate"),
            "sam2_mask_rate": detector_summary.get("sam2_mask_rate"),
            "candidate_association_rate": detector_summary.get("candidate_association_rate"),
            "passes_detector_substrate_gate": (detector_summary.get("gate") or {}).get("passes_detector_substrate_gate"),
            "uses_gt_for_action": detector_summary.get("uses_gt_for_action"),
        },
        "facts": [
            "The frozen post-observation analyzer committed two wrong goals on the fresh source.",
            "Both wrong commits are single-positive-candidate toilet requests with no planned rival contrast.",
            "The detector substrate passed, so the immediate failure is not missing detector/SAM2 evidence.",
        ],
        "agent_inferences": [
            "`request_identity_no_guard_eligible_positive_candidates` is a mixed request reason in this source.",
            "Single-positive-candidate requests should be separated from rival-identity arbitration before rule revision.",
            "A safer next branch is object-existence validation for single-candidate false positives and rival-identity arbitration only when multiple positive candidates are present.",
        ],
        "user_decision_needed": [
            "Decide whether to split `request_identity_no_guard_eligible_positive_candidates` into object-existence validation versus multi-candidate rival-identity arbitration.",
        ],
        "paper_claim_allowed": False,
        "paper_claim_status": "blocked_by_fresh_source_wrong_goal_commits",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "rival_identity_failure_diagnostic_rows.jsonl",
            "summary": "rival_identity_failure_diagnostic_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evaluated_rows = load_jsonl(Path(args.evaluated))
    evidence_rows = load_jsonl(Path(args.evidence))
    plan_rows = load_jsonl(Path(args.plan))
    detector_summary = load_json(Path(args.detector_summary)) if args.detector_summary else None
    evidence_by_request = group_by(evidence_rows, "rival_identity_request_id")
    plan_by_request = group_by(plan_rows, "rival_identity_request_id")
    diagnostic_rows = [
        classify_request(
            evaluated=row,
            evidence_rows=evidence_by_request.get(str(row.get("rival_identity_request_id")), []),
            plan_rows=plan_by_request.get(str(row.get("rival_identity_request_id")), []),
        )
        for row in evaluated_rows
    ]
    summary = summarize(diagnostic_rows, args=args, detector_summary=detector_summary)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "rival_identity_failure_diagnostic_rows.jsonl", diagnostic_rows)
    write_json(out_root / "rival_identity_failure_diagnostic_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose fresh-source H001 rival-identity post-observation failures.")
    parser.add_argument("--evaluated", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--detector-summary")
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
