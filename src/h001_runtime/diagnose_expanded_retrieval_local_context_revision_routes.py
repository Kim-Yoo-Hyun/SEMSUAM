import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_local_context_revision_route_diagnostic.v1"
REVISION_VARIANT = "goal_validity_guarded_local_context_v1"
PREVIOUS_VARIANT = "previous_local_context_unique_own_view_advantage"
ALTERNATIVE_VARIANTS = [
    "defer_all",
    "semantic_top",
    "source_top_if_associated",
    "detector_score_best",
    "own_support_best",
    "local_context_only_best",
    PREVIOUS_VARIANT,
]


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


def label_index(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row.get("episode_key")), str(row.get("candidate_id"))): row
        for row in label_rows
        if row.get("episode_key") is not None and row.get("candidate_id") is not None
    }


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("expanded_retrieval_request_id"))].append(row)
    return grouped


def decision_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row.get("expanded_retrieval_request_id")), str(row.get("variant"))): row
        for row in rows
    }


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def candidate_label(labels: Dict[Tuple[str, str], Dict[str, Any]], row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return labels.get((str(row.get("episode_key")), str(row.get("candidate_id"))))


def role_contains(row: Dict[str, Any], role: str) -> bool:
    return role in str(row.get("candidate_role") or "").split("+")


def summarize_candidates(
    evidence_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    correct_rows: List[Dict[str, Any]] = []
    wrong_rows: List[Dict[str, Any]] = []
    unlabeled_rows: List[Dict[str, Any]] = []
    strong_rows: List[Dict[str, Any]] = []
    correct_strong: List[Dict[str, Any]] = []
    wrong_strong: List[Dict[str, Any]] = []
    detector_strong: List[Dict[str, Any]] = []
    local_context: List[Dict[str, Any]] = []
    source_top: List[Dict[str, Any]] = []

    for row in evidence_rows:
        label = candidate_label(labels, row)
        if label is None:
            unlabeled_rows.append(row)
        elif label.get("evaluation_only_candidate_correct") is True:
            correct_rows.append(row)
        else:
            wrong_rows.append(row)
        if row.get("strong_own_view_evidence") is True:
            strong_rows.append(row)
            if label is not None and label.get("evaluation_only_candidate_correct") is True:
                correct_strong.append(row)
            elif label is not None and label.get("evaluation_only_candidate_correct") is False:
                wrong_strong.append(row)
        if role_contains(row, "detector_strong_candidate") or role_contains(row, "detector_strong_rival"):
            detector_strong.append(row)
        if role_contains(row, "local_context_candidate"):
            local_context.append(row)
        if role_contains(row, "source_top"):
            source_top.append(row)

    return {
        "candidate_count": len(evidence_rows),
        "correct_candidate_count": len(correct_rows),
        "wrong_candidate_count": len(wrong_rows),
        "unlabeled_candidate_count": len(unlabeled_rows),
        "strong_own_view_candidate_count": len(strong_rows),
        "correct_strong_own_view_count": len(correct_strong),
        "wrong_strong_own_view_count": len(wrong_strong),
        "detector_strong_candidate_count": len(detector_strong),
        "local_context_candidate_count": len(local_context),
        "source_top_candidate_count": len(source_top),
        "correct_candidate_ids": [row.get("candidate_id") for row in correct_rows],
        "wrong_candidate_ids": [row.get("candidate_id") for row in wrong_rows],
        "strong_own_view_candidate_ids": [row.get("candidate_id") for row in strong_rows],
        "correct_strong_own_view_candidate_ids": [row.get("candidate_id") for row in correct_strong],
        "wrong_strong_own_view_candidate_ids": [row.get("candidate_id") for row in wrong_strong],
    }


def outcome_payload(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {
            "available": False,
            "action": None,
            "terminal_commit": None,
            "selected_candidate_id": None,
            "selected_candidate_role": None,
            "success_commit": None,
            "wrong_goal_commit": None,
            "no_valid_commit": None,
            "reason": None,
        }
    return {
        "available": True,
        "action": row.get("action"),
        "terminal_commit": row.get("terminal_commit"),
        "selected_candidate_id": row.get("selected_candidate_id"),
        "selected_candidate_role": row.get("selected_candidate_role"),
        "success_commit": row.get("evaluation_only_success_commit"),
        "wrong_goal_commit": row.get("evaluation_only_wrong_goal_commit"),
        "no_valid_commit": row.get("evaluation_only_no_valid_commit"),
        "reason": row.get("reason"),
    }


def diagnose_tags(
    revision: Dict[str, Any],
    candidate_summary: Dict[str, Any],
    variant_outcomes: Dict[str, Dict[str, Any]],
) -> List[str]:
    tags: List[str] = []
    correct_count = safe_int(candidate_summary.get("correct_candidate_count"))
    correct_strong = safe_int(candidate_summary.get("correct_strong_own_view_count"))
    wrong_strong = safe_int(candidate_summary.get("wrong_strong_own_view_count"))
    strong_count = safe_int(candidate_summary.get("strong_own_view_candidate_count"))
    guard = revision.get("decision_guard") or {}
    pool_guard = guard.get("pool_validity_guard") or {}
    instance_guard = guard.get("instance_arbitration_guard") or {}
    pool_status = str(pool_guard.get("status"))
    instance_reason = str(instance_guard.get("reason"))

    if pool_status == "passed" and correct_count == 0:
        tags.append("pool_guard_false_positive_no_valid_pool")
    elif pool_status == "passed":
        tags.append("pool_guard_passed_valid_pool")
    if correct_count == 0:
        tags.append("no_valid_candidate_pool_after_label_join")
    if strong_count == 0:
        tags.append("no_strong_own_view_candidate")
    if correct_count > 0 and correct_strong == 0:
        tags.append("correct_candidate_not_strong_own_view")
    if correct_strong > 0 and wrong_strong > 0:
        tags.append("correct_and_wrong_both_strong_own_view")
    if correct_strong == 0 and wrong_strong > 0:
        tags.append("wrong_only_strong_own_view")
    if instance_reason == "multiple_strong_own_view_candidates":
        tags.append("multi_strong_own_view_ambiguity")
    if instance_reason == "detector_strong_object_visibility_not_goal_validity":
        tags.append("detector_strong_visibility_not_goal_validity")
    if instance_reason == "source_top_visibility_not_goal_validity":
        tags.append("source_top_visibility_not_goal_validity")

    previous = variant_outcomes.get(PREVIOUS_VARIANT) or {}
    if previous.get("success_commit") is True:
        tags.append("previous_rule_success_lost_by_guard")
    if previous.get("wrong_goal_commit") is True or previous.get("no_valid_commit") is True:
        tags.append("unsafe_previous_commit_prevented")
    if any(
        (variant_outcomes.get(variant) or {}).get("success_commit") is True
        for variant in ALTERNATIVE_VARIANTS
        if variant != "defer_all"
    ):
        tags.append("some_simpler_alternative_succeeds_analysis_only")
    if any(
        (variant_outcomes.get(variant) or {}).get("wrong_goal_commit") is True
        or (variant_outcomes.get(variant) or {}).get("no_valid_commit") is True
        for variant in ALTERNATIVE_VARIANTS
        if variant != "defer_all"
    ):
        tags.append("simpler_alternatives_unsafe_analysis_only")
    return sorted(set(tags))


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    evidence_rows = load_jsonl(Path(args.evidence_rows))
    decision_rows = load_jsonl(Path(args.decision_rows))
    evaluated_rows = load_jsonl(Path(args.evaluated_rows))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))

    evidence_by_request = group_by_request(evidence_rows)
    evaluated_by_key = decision_index(evaluated_rows)
    revision_rows = [
        row for row in evaluated_rows
        if row.get("variant") == REVISION_VARIANT
    ]

    diagnostic_rows: List[Dict[str, Any]] = []
    tag_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    pool_reason_counts: Counter[str] = Counter()
    instance_reason_counts: Counter[str] = Counter()
    route_no_valid_counts: Counter[str] = Counter()
    route_valid_counts: Counter[str] = Counter()
    lost_previous_success_rows = 0
    unsafe_previous_prevented_rows = 0
    pool_false_positive_rows = 0

    for revision in revision_rows:
        request_id = str(revision.get("expanded_retrieval_request_id"))
        request_evidence = evidence_by_request.get(request_id, [])
        candidate_summary = summarize_candidates(request_evidence, labels)
        variant_outcomes = {
            variant: outcome_payload(evaluated_by_key.get((request_id, variant)))
            for variant in ALTERNATIVE_VARIANTS
        }
        guard = revision.get("decision_guard") or {}
        pool_guard = guard.get("pool_validity_guard") or {}
        instance_guard = guard.get("instance_arbitration_guard") or {}
        tags = diagnose_tags(revision, candidate_summary, variant_outcomes)
        tag_counts.update(tags)
        route = str(revision.get("action"))
        route_counts.update([route])
        pool_reason_counts.update([str(pool_guard.get("reason"))])
        instance_reason_counts.update([str(instance_guard.get("reason"))])
        if safe_int(candidate_summary.get("correct_candidate_count")) == 0:
            route_no_valid_counts.update([route])
        else:
            route_valid_counts.update([route])
        lost_previous_success_rows += int("previous_rule_success_lost_by_guard" in tags)
        unsafe_previous_prevented_rows += int("unsafe_previous_commit_prevented" in tags)
        pool_false_positive_rows += int("pool_guard_false_positive_no_valid_pool" in tags)
        diagnostic_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": revision.get("rival_identity_request_id"),
                "episode_key": revision.get("episode_key"),
                "scene_key": revision.get("scene_key"),
                "query": revision.get("query"),
                "revision_action": route,
                "revision_reason": revision.get("reason"),
                "pool_guard_status": pool_guard.get("status"),
                "pool_guard_reason": pool_guard.get("reason"),
                "instance_guard_status": instance_guard.get("status"),
                "instance_guard_reason": instance_guard.get("reason"),
                "candidate_summary": candidate_summary,
                "variant_outcomes": variant_outcomes,
                "diagnostic_tags": tags,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "evidence_rows": str(args.evidence_rows),
        "decision_rows": str(args.decision_rows),
        "evaluated_rows": str(args.evaluated_rows),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(out_root),
        "request_rows": len(revision_rows),
        "route_counts": dict(sorted(route_counts.items())),
        "pool_guard_reason_counts": dict(sorted(pool_reason_counts.items())),
        "instance_guard_reason_counts": dict(sorted(instance_reason_counts.items())),
        "route_counts_for_no_valid_rows": dict(sorted(route_no_valid_counts.items())),
        "route_counts_for_valid_rows": dict(sorted(route_valid_counts.items())),
        "diagnostic_tag_counts": dict(sorted(tag_counts.items())),
        "pool_false_positive_no_valid_rows": pool_false_positive_rows,
        "lost_previous_success_rows": lost_previous_success_rows,
        "unsafe_previous_commit_prevented_rows": unsafe_previous_prevented_rows,
        "primary_blockers": [
            "pool_validity_proxy_passes_rows_that_are_no_valid_after_label_join",
            "own_view_detector_category_evidence_does_not_establish_goal_validity",
            "multiple_or_detector_strong_own_view_evidence_requires_confirmation_instead_of_commit",
        ],
        "next_design_constraints": [
            "do not threshold-tune from joined labels",
            "repair source-pool validity proxy before treating every detector-eligible row as valid",
            "design goal-validity confirmation evidence for request_goal_validity_confirmation rows",
            "treat defer_instance_arbitration_unresolved rows as contrastive instance ambiguity, not missed threshold",
            "keep detector-score/source-top/own-support/local-context-only alternatives as unsafe baselines",
        ],
        "interpretation": {
            "fact": (
                "The revised rule made no terminal commits, so all row-level correctness analysis is post-action "
                "diagnostic only."
            ),
            "agent_inference": (
                "The safety repair over-defers because the current local-context evidence can expose object "
                "visibility but not goal validity. The next method should add route-specific confirmation evidence, "
                "not relax the current commit guard."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "expanded_retrieval_local_context_revision_route_rows.jsonl",
            "summary": "expanded_retrieval_local_context_revision_route_summary.json",
        },
    }
    write_jsonl(out_root / "expanded_retrieval_local_context_revision_route_rows.jsonl", diagnostic_rows)
    write_json(out_root / "expanded_retrieval_local_context_revision_route_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose safe-but-inert local-context revision routes.")
    parser.add_argument("--evidence-rows", required=True)
    parser.add_argument("--decision-rows", required=True)
    parser.add_argument("--evaluated-rows", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
