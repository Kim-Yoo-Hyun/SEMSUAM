import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.goal_validity_independent_failure_diagnostic.v1"


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["rival_identity_request_id"])].append(row)
    return grouped


def one_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        request_id = str(row["rival_identity_request_id"])
        if request_id in output:
            raise ValueError(f"duplicate request row: {request_id}")
        output[request_id] = row
    return output


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in label_rows:
        key = (str(row["episode_key"]), str(row["candidate_id"]))
        existing = lookup.get(key)
        if existing is not None and bool(existing.get("evaluation_only_candidate_correct")) != bool(
            row.get("evaluation_only_candidate_correct")
        ):
            raise ValueError(f"conflicting evaluation label for {key}")
        lookup[key] = row
    return lookup


def is_correct(row: Dict[str, Any], labels: Dict[Tuple[str, str], Dict[str, Any]]) -> Optional[bool]:
    label = labels.get((str(row["episode_key"]), str(row["candidate_id"])))
    if label is None:
        return None
    return bool(label.get("evaluation_only_candidate_correct"))


def goal_validity_surrogate(row: Dict[str, Any]) -> bool:
    own = safe_int(row.get("post_own_associated_heading_count"))
    cross = safe_int(row.get("post_cross_associated_heading_count"))
    rank = safe_int(row.get("semantic_rank"), default=999999)
    box = safe_float(row.get("post_best_box_score"))
    depth = safe_float(row.get("post_min_depth_error_m"))
    return bool(
        row.get("has_rival_contrast") is True
        and own >= 3
        and cross == 0
        and rank <= 5
        and box is not None
        and box >= 0.25
        and depth is not None
        and depth <= 0.50
    )


def stats(rows: Sequence[Dict[str, Any]], field: str, *, minimum: bool = False) -> Optional[float]:
    values = [safe_float(row.get(field)) for row in rows]
    finite = [value for value in values if value is not None]
    if not finite:
        return None
    return min(finite) if minimum else max(finite)


def selected_evidence(
    decision: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    selected_id = decision.get("selected_candidate_id")
    if selected_id is None:
        return None
    return next((row for row in evidence_rows if str(row.get("candidate_id")) == str(selected_id)), None)


def best_correct_evidence(
    evidence_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    correct_rows = [row for row in evidence_rows if is_correct(row, labels) is True]
    if not correct_rows:
        return None
    return max(
        correct_rows,
        key=lambda row: (
            safe_int(row.get("post_own_associated_heading_count")),
            safe_float(row.get("post_best_box_score")) or 0.0,
            -safe_int(row.get("semantic_rank"), default=999999),
        ),
    )


def mechanism_tags(
    *,
    goal_decision: Dict[str, Any],
    default_decision: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[str]:
    tags: List[str] = []
    max_own = max((safe_int(row.get("post_own_associated_heading_count")) for row in evidence_rows), default=0)
    max_cross = max((safe_int(row.get("post_cross_associated_heading_count")) for row in evidence_rows), default=0)
    strong_rows = [row for row in evidence_rows if row.get("strong_identity_evidence") is True]
    valid_rows = [row for row in evidence_rows if goal_validity_surrogate(row)]
    correct_rows = [row for row in evidence_rows if is_correct(row, labels) is True]
    default_selected = selected_evidence(default_decision, evidence_rows)
    best_correct = best_correct_evidence(evidence_rows, labels)

    if goal_decision.get("request_taxonomy_route") == "object_existence_validation":
        tags.append("object_existence_branch_blocks_commit")
    if max_own == 0:
        tags.append("no_own_candidate_support")
    if max_cross > 0 and not valid_rows:
        tags.append("cross_view_aliasing_blocks_goal_validity")
    if strong_rows and not valid_rows:
        tags.append("strong_identity_not_goal_validity")
    if len(valid_rows) > 1:
        tags.append("multiple_goal_validity_candidates")
    if not correct_rows:
        tags.append("planned_candidate_set_has_no_valid_goal")
    if default_decision.get("evaluation_only_wrong_goal_commit") is True:
        tags.append("default_rule_wrong_goal")
        if default_selected is not None and best_correct is not None:
            if safe_int(default_selected.get("post_own_associated_heading_count")) >= safe_int(
                best_correct.get("post_own_associated_heading_count")
            ):
                tags.append("wrong_candidate_not_weaker_than_correct_by_own_support")
            if safe_int(default_selected.get("semantic_rank"), default=999999) <= safe_int(
                best_correct.get("semantic_rank"), default=999999
            ):
                tags.append("wrong_candidate_not_weaker_than_correct_by_semantic_rank")
    if default_decision.get("evaluation_only_success_commit") is True:
        tags.append("default_rule_success_lost_by_strict_rule")
    if goal_decision.get("reason") == "defer_low_goal_validity_surrogate":
        tags.append("surrogate_threshold_blocks_visible_candidate")
    if not tags:
        tags.append("manual_review")
    return sorted(set(tags))


def build_request_rows(
    *,
    goal_evidence: Sequence[Dict[str, Any]],
    goal_evaluated: Sequence[Dict[str, Any]],
    default_evaluated: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    evidence_by_request = group_by_request(goal_evidence)
    goal_by_request = one_by_request(goal_evaluated)
    default_by_request = one_by_request(default_evaluated)
    request_ids = sorted(goal_by_request, key=lambda value: int(value.split(":")[-1]) if value.split(":")[-1].isdigit() else 999999)
    rows: List[Dict[str, Any]] = []
    for request_id in request_ids:
        evidence_rows = evidence_by_request.get(request_id, [])
        goal_decision = goal_by_request[request_id]
        default_decision = default_by_request[request_id]
        strong_rows = [row for row in evidence_rows if row.get("strong_identity_evidence") is True]
        valid_rows = [row for row in evidence_rows if goal_validity_surrogate(row)]
        correct_rows = [row for row in evidence_rows if is_correct(row, labels) is True]
        selected_default = selected_evidence(default_decision, evidence_rows)
        best_correct = best_correct_evidence(evidence_rows, labels)
        tags = mechanism_tags(
            goal_decision=goal_decision,
            default_decision=default_decision,
            evidence_rows=evidence_rows,
            labels=labels,
        )
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": request_id,
                "episode_key": goal_decision.get("episode_key"),
                "scene_key": goal_decision.get("scene_key"),
                "query": goal_decision.get("query"),
                "request_taxonomy_route": goal_decision.get("request_taxonomy_route"),
                "has_rival_contrast": goal_decision.get("has_rival_contrast"),
                "single_positive_candidate": goal_decision.get("single_positive_candidate"),
                "planned_target_count": goal_decision.get("planned_target_count"),
                "positive_support_candidate_count": goal_decision.get("positive_support_candidate_count"),
                "evidence_candidate_count": len(evidence_rows),
                "strong_identity_candidate_count": len(strong_rows),
                "goal_validity_candidate_count": len(valid_rows),
                "correct_candidate_count_in_planned_set": len(correct_rows),
                "max_own_associated_heading_count": max(
                    (safe_int(row.get("post_own_associated_heading_count")) for row in evidence_rows),
                    default=0,
                ),
                "max_cross_associated_heading_count": max(
                    (safe_int(row.get("post_cross_associated_heading_count")) for row in evidence_rows),
                    default=0,
                ),
                "max_identity_margin": max(
                    (safe_int(row.get("post_identity_margin")) for row in evidence_rows),
                    default=0,
                ),
                "max_box_score": stats(evidence_rows, "post_best_box_score"),
                "min_depth_error_m": stats(evidence_rows, "post_min_depth_error_m", minimum=True),
                "goal_validity_action": goal_decision.get("action"),
                "goal_validity_reason": goal_decision.get("reason"),
                "goal_validity_success_commit": goal_decision.get("evaluation_only_success_commit"),
                "goal_validity_wrong_goal_commit": goal_decision.get("evaluation_only_wrong_goal_commit"),
                "default_action": default_decision.get("action"),
                "default_reason": default_decision.get("reason"),
                "default_success_commit": default_decision.get("evaluation_only_success_commit"),
                "default_wrong_goal_commit": default_decision.get("evaluation_only_wrong_goal_commit"),
                "default_selected_candidate_id": default_decision.get("selected_candidate_id"),
                "default_selected_semantic_rank": None
                if selected_default is None
                else selected_default.get("semantic_rank"),
                "default_selected_own_associated_heading_count": None
                if selected_default is None
                else selected_default.get("post_own_associated_heading_count"),
                "default_selected_cross_associated_heading_count": None
                if selected_default is None
                else selected_default.get("post_cross_associated_heading_count"),
                "best_correct_candidate_id": None if best_correct is None else best_correct.get("candidate_id"),
                "best_correct_semantic_rank": None if best_correct is None else best_correct.get("semantic_rank"),
                "best_correct_own_associated_heading_count": None
                if best_correct is None
                else best_correct.get("post_own_associated_heading_count"),
                "mechanism_tags": tags,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def summarize(
    *,
    request_rows: Sequence[Dict[str, Any]],
    goal_summary: Dict[str, Any],
    default_summary: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    tag_counts = Counter(tag for row in request_rows for tag in row["mechanism_tags"])
    goal_wrong = int(goal_summary.get("wrong_goal_commit_rows") or 0)
    goal_success = int(goal_summary.get("success_commit_rows") or 0)
    default_wrong = int(default_summary.get("wrong_goal_commit_rows") or 0)
    default_success = int(default_summary.get("success_commit_rows") or 0)
    default_commits = int(default_summary.get("commit_rows") or 0)
    request_count = len(request_rows)
    default_wrong_rows = [row for row in request_rows if row.get("default_wrong_goal_commit") is True]
    default_success_rows = [row for row in request_rows if row.get("default_success_commit") is True]
    checks = {
        "strict_rule_safe": goal_wrong == 0,
        "strict_rule_nontrivial": goal_success > 0,
        "loose_rule_nontrivial": default_success > 0,
        "loose_rule_safe": default_wrong == 0,
        "diagnostic_has_tradeoff": default_success > 0 and default_wrong > 0 and goal_wrong == 0 and goal_success == 0,
        "paper_claim_allowed": False,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "inputs": {
            "goal_validity_summary": str(args.goal_validity_summary),
            "goal_validity_evidence": str(args.goal_validity_evidence),
            "goal_validity_evaluated": str(args.goal_validity_evaluated),
            "default_summary": str(args.default_summary),
            "default_evaluated": str(args.default_evaluated),
            "evaluation_labels": [str(path) for path in args.evaluation_labels],
        },
        "request_rows": request_count,
        "goal_validity_commit_success_wrong": [
            int(goal_summary.get("commit_rows") or 0),
            goal_success,
            goal_wrong,
        ],
        "default_commit_success_wrong": [
            default_commits,
            default_success,
            default_wrong,
        ],
        "goal_validity_commit_rate": ratio(int(goal_summary.get("commit_rows") or 0), request_count),
        "default_commit_rate": ratio(default_commits, request_count),
        "default_wrong_goal_rate": ratio(default_wrong, request_count),
        "default_success_lost_by_strict_rule_rows": len(default_success_rows),
        "default_wrong_goal_blocked_by_strict_rule_rows": len(default_wrong_rows),
        "mechanism_tag_counts": dict(sorted(tag_counts.items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in request_rows).items())),
        "default_wrong_goal_query_counts": dict(
            sorted(Counter(str(row.get("query")) for row in default_wrong_rows).items())
        ),
        "default_success_query_counts": dict(
            sorted(Counter(str(row.get("query")) for row in default_success_rows).items())
        ),
        "goal_validity_reason_counts": dict(
            sorted(Counter(str(row.get("goal_validity_reason")) for row in request_rows).items())
        ),
        "default_reason_counts": dict(sorted(Counter(str(row.get("default_reason")) for row in request_rows).items())),
        "request_taxonomy_route_counts": dict(
            sorted(Counter(str(row.get("request_taxonomy_route")) for row in request_rows).items())
        ),
        "checks": checks,
        "facts": [
            "The strict goal-validity objective committed zero candidates on the independent source.",
            "The default unique-strong-identity objective committed candidates on the same evidence but produced wrong-goal commits.",
            "Both outputs were generated before joining evaluation labels for analysis.",
        ],
        "agent_inferences": [
            "The independent failure is not a simple strict-threshold problem.",
            "The current evidence creates a safety-utility tradeoff: loose identity evidence recovers successes but also commits wrong goals, while the strict rule is safe but inert.",
            "The next method revision should change the evidence design or candidate validity model, not tune thresholds from joined labels.",
        ],
        "user_decision_needed": None,
        "paper_claim_allowed": False,
        "paper_claim_status": "blocked_by_independent_safe_but_inert_strict_rule_and_unsafe_loose_counterfactual",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "goal_validity_independent_failure_rows.jsonl",
            "summary": "goal_validity_independent_failure_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    goal_summary = load_json(Path(args.goal_validity_summary))
    default_summary = load_json(Path(args.default_summary))
    labels = label_lookup([row for path in args.evaluation_labels for row in load_jsonl(Path(path))])
    request_rows = build_request_rows(
        goal_evidence=load_jsonl(Path(args.goal_validity_evidence)),
        goal_evaluated=load_jsonl(Path(args.goal_validity_evaluated)),
        default_evaluated=load_jsonl(Path(args.default_evaluated)),
        labels=labels,
    )
    summary = summarize(
        request_rows=request_rows,
        goal_summary=goal_summary,
        default_summary=default_summary,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "goal_validity_independent_failure_rows.jsonl", request_rows)
    write_json(out_root / "goal_validity_independent_failure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose independent goal-validity arbitration failure.")
    parser.add_argument("--goal-validity-summary", required=True)
    parser.add_argument("--goal-validity-evidence", required=True)
    parser.add_argument("--goal-validity-evaluated", required=True)
    parser.add_argument("--default-summary", required=True)
    parser.add_argument("--default-evaluated", required=True)
    parser.add_argument("--evaluation-labels", nargs="+", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
