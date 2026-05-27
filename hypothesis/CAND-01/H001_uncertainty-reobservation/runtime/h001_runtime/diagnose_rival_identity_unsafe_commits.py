import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.rival_identity_unsafe_commit_diagnostic.v1"


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
    return number


def safe_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {(str(row["episode_key"]), str(row["candidate_id"])): row for row in label_rows}


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["rival_identity_request_id"])].append(row)
    return grouped


def is_correct(label: Optional[Dict[str, Any]]) -> bool:
    return bool(label and label.get("evaluation_only_candidate_correct") is True)


def selected_unique_strong(rows: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    strong_rows = [row for row in rows if row.get("strong_identity_evidence") is True]
    if len(strong_rows) != 1:
        return None
    return strong_rows[0]


def evaluate_variant(
    *,
    name: str,
    description: str,
    evaluated_rows: Sequence[Dict[str, Any]],
    evidence_by_request: Dict[str, List[Dict[str, Any]]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    predicate: Callable[[Dict[str, Any]], bool],
) -> Dict[str, Any]:
    commit_rows = 0
    success_rows = 0
    wrong_rows = 0
    no_label_rows = 0
    committed_queries: Counter[str] = Counter()
    for decision in evaluated_rows:
        request_id = str(decision["rival_identity_request_id"])
        rows = evidence_by_request.get(request_id, [])
        exemplar = rows[0] if rows else decision
        if exemplar.get("request_taxonomy_route") != "rival_identity_arbitration":
            continue
        selected = selected_unique_strong(rows)
        if selected is None or not predicate(selected):
            continue
        commit_rows += 1
        committed_queries[str(selected.get("query"))] += 1
        label = labels.get((str(selected["episode_key"]), str(selected["candidate_id"])))
        if label is None:
            no_label_rows += 1
        elif is_correct(label):
            success_rows += 1
        else:
            wrong_rows += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "variant": name,
        "description": description,
        "commit_rows": commit_rows,
        "success_commit_rows": success_rows,
        "wrong_goal_commit_rows": wrong_rows,
        "no_label_commit_rows": no_label_rows,
        "committed_query_counts": dict(sorted(committed_queries.items())),
        "safe_and_nontrivial": wrong_rows == 0 and no_label_rows == 0 and success_rows > 0,
    }


def best_correct_row(
    rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    correct_rows = [row for row in rows if is_correct(labels.get((str(row["episode_key"]), str(row["candidate_id"]))))]
    if not correct_rows:
        return None
    return max(
        correct_rows,
        key=lambda row: (
            safe_int(row.get("post_own_associated_heading_count")) or 0,
            -(safe_int(row.get("semantic_rank")) or 999999),
            safe_float(row.get("post_best_box_score")) or 0.0,
        ),
    )


def mechanisms_for_wrong_commit(
    *,
    selected: Dict[str, Any],
    correct: Optional[Dict[str, Any]],
    correct_count: int,
) -> List[str]:
    mechanisms: List[str] = []
    selected_own = safe_int(selected.get("post_own_associated_heading_count")) or 0
    selected_cross = safe_int(selected.get("post_cross_associated_heading_count")) or 0
    selected_rank = safe_int(selected.get("semantic_rank"))
    selected_box = safe_float(selected.get("post_best_box_score"))
    selected_depth = safe_float(selected.get("post_min_depth_error_m"))
    if correct_count == 0:
        mechanisms.append("candidate_set_no_valid_goal_candidate")
    if correct is not None:
        correct_own = safe_int(correct.get("post_own_associated_heading_count")) or 0
        correct_rank = safe_int(correct.get("semantic_rank")) or 999999
        if selected_own > correct_own:
            mechanisms.append("wrong_candidate_has_stronger_own_view_support_than_correct")
        if selected_rank is not None and selected_rank <= correct_rank:
            mechanisms.append("semantic_prior_favors_wrong_over_correct")
    if selected_rank == 1:
        mechanisms.append("semantic_top_is_wrong")
    elif selected_rank is not None and selected_rank > 1:
        mechanisms.append("rival_candidate_false_positive_commit")
    if selected_cross == 0:
        mechanisms.append("absence_of_cross_support_not_discriminative")
    if selected_box is not None and selected_box < 0.25:
        mechanisms.append("low_detector_score_still_strong_by_count")
    if selected_depth is not None and selected_depth <= 0.33:
        mechanisms.append("depth_consistent_wrong_candidate")
    return mechanisms


def unsafe_commit_rows(
    *,
    evaluated_rows: Sequence[Dict[str, Any]],
    evidence_by_request: Dict[str, List[Dict[str, Any]]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for decision in evaluated_rows:
        if decision.get("evaluation_only_wrong_goal_commit") is not True:
            continue
        request_id = str(decision["rival_identity_request_id"])
        selected_id = str(decision.get("selected_candidate_id"))
        rows = evidence_by_request.get(request_id, [])
        selected = next((row for row in rows if str(row["candidate_id"]) == selected_id), None)
        if selected is None:
            continue
        correct_rows = [
            row for row in rows
            if is_correct(labels.get((str(row["episode_key"]), str(row["candidate_id"]))))
        ]
        correct = best_correct_row(rows, labels)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": request_id,
                "episode_key": decision.get("episode_key"),
                "scene_key": decision.get("scene_key"),
                "query": decision.get("query"),
                "selected_candidate_id": selected_id,
                "selected_semantic_rank": selected.get("semantic_rank"),
                "selected_semantic_score": selected.get("semantic_score"),
                "selected_post_own_associated_heading_count": selected.get("post_own_associated_heading_count"),
                "selected_post_cross_associated_heading_count": selected.get("post_cross_associated_heading_count"),
                "selected_post_identity_margin": selected.get("post_identity_margin"),
                "selected_post_best_box_score": selected.get("post_best_box_score"),
                "selected_post_min_depth_error_m": selected.get("post_min_depth_error_m"),
                "correct_candidate_count_in_planned_set": len(correct_rows),
                "best_correct_candidate_id": None if correct is None else correct.get("candidate_id"),
                "best_correct_semantic_rank": None if correct is None else correct.get("semantic_rank"),
                "best_correct_semantic_score": None if correct is None else correct.get("semantic_score"),
                "best_correct_post_own_associated_heading_count": None
                if correct is None
                else correct.get("post_own_associated_heading_count"),
                "best_correct_post_cross_associated_heading_count": None
                if correct is None
                else correct.get("post_cross_associated_heading_count"),
                "best_correct_post_identity_margin": None if correct is None else correct.get("post_identity_margin"),
                "best_correct_post_best_box_score": None if correct is None else correct.get("post_best_box_score"),
                "best_correct_post_min_depth_error_m": None
                if correct is None
                else correct.get("post_min_depth_error_m"),
                "mechanisms": mechanisms_for_wrong_commit(
                    selected=selected,
                    correct=correct,
                    correct_count=len(correct_rows),
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return output


def build_summary(
    *,
    evidence_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    unsafe_rows: Sequence[Dict[str, Any]],
    variants: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    mechanism_counts = Counter(mechanism for row in unsafe_rows for mechanism in row["mechanisms"])
    safe_nontrivial_variants = [
        row["variant"]
        for row in variants
        if row["safe_and_nontrivial"] and row["variant"] != "defer_all_rival_identity"
    ]
    wrong_variants = [
        row["variant"]
        for row in variants
        if row["wrong_goal_commit_rows"] > 0
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "inputs": {
            "post_observation_evidence": str(args.post_observation_evidence),
            "post_observation_evaluated": str(args.post_observation_evaluated),
            "evaluation_labels": [str(path) for path in args.evaluation_labels],
        },
        "evidence_rows": len(evidence_rows),
        "evaluated_request_rows": len(evaluated_rows),
        "unsafe_commit_rows": len(unsafe_rows),
        "unsafe_commit_query_counts": dict(sorted(Counter(str(row.get("query")) for row in unsafe_rows).items())),
        "unsafe_commit_mechanism_counts": dict(sorted(mechanism_counts.items())),
        "simple_guard_variant_count": len(variants),
        "simple_guard_variants_with_wrong_commit": wrong_variants,
        "safe_nontrivial_simple_guard_variants": safe_nontrivial_variants,
        "gates": {
            "unsafe_commit_diagnostic_gate_passed": len(unsafe_rows) > 0 and bool(mechanism_counts),
            "simple_threshold_fix_rejected": len(safe_nontrivial_variants) == 0,
            "post_observation_threshold_tuning_allowed": False,
            "paper_claim_allowed": False,
        },
        "safer_arbitration_contract": {
            "status": "required_before_post_observation_rule_change",
            "blocked_changes": [
                "increase only own-view count or identity-margin threshold",
                "commit from object/category existence evidence alone",
                "commit from detector box score, depth error, or semantic rank alone",
                "use evaluation-only correctness, GT goal ids, or GT target distance in action rows",
            ],
            "required_before_next_rule": [
                "separate candidate-set validity failure from rival-identity arbitration",
                "report defer-only, semantic-rank, detector-score, depth-consistency, and combined simple guards",
                "require an action-time surrogate that a candidate is a valid navigation goal, not merely a visible object",
                "route no-valid-candidate or low-validity-surrogate rows to expanded retrieval or object-existence validation",
                "keep label joins sidecar-only and evaluate wrong-goal, no-label, and success commits after action selection",
            ],
            "next_implementation_target": (
                "design a stricter rival-identity arbitration objective that tests candidate-set validity and "
                "local semantic/geometric consistency before any detector-backed commit"
            ),
        },
        "interpretation": {
            "fact": (
                "The current fixed rule can produce unique strong own-view identity evidence for candidates that "
                "are wrong under evaluation labels."
            ),
            "agent_inference": (
                "The blocker is no longer detector availability or standoff geometry. The remaining failure is "
                "that category-level own-view evidence proves object existence, not valid ObjectNav goal identity."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "summary": "rival_identity_unsafe_commit_diagnostic_summary.json",
            "unsafe_commit_rows": "rival_identity_unsafe_commit_rows.jsonl",
            "simple_guard_variants": "rival_identity_simple_guard_variants.jsonl",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    evidence_rows = load_jsonl(Path(args.post_observation_evidence))
    evaluated_rows = load_jsonl(Path(args.post_observation_evaluated))
    labels = label_lookup([row for path in args.evaluation_labels for row in load_jsonl(Path(path))])
    evidence_by_request = group_by_request(evidence_rows)
    unsafe_rows = unsafe_commit_rows(
        evaluated_rows=evaluated_rows,
        evidence_by_request=evidence_by_request,
        labels=labels,
    )
    variants = [
        evaluate_variant(
            name="existing_unique_strong_own_view_identity",
            description="Current fixed rule: commit if exactly one candidate has strong own-view support.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: True,
        ),
        evaluate_variant(
            name="defer_all_rival_identity",
            description="Safety lower bound with no rival-identity commits.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: False,
        ),
        evaluate_variant(
            name="semantic_rank_1_only",
            description="Commit current unique-strong candidate only when it is semantic rank 1.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: safe_int(row.get("semantic_rank")) == 1,
        ),
        evaluate_variant(
            name="detector_box_ge_0_25",
            description="Commit current unique-strong candidate only when post_best_box_score >= 0.25.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: (safe_float(row.get("post_best_box_score")) or 0.0) >= 0.25,
        ),
        evaluate_variant(
            name="depth_error_le_0_33",
            description="Commit current unique-strong candidate only when post_min_depth_error_m <= 0.33.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: (
                safe_float(row.get("post_min_depth_error_m")) is not None
                and safe_float(row.get("post_min_depth_error_m")) <= 0.33
            ),
        ),
        evaluate_variant(
            name="rank_le_3_box_ge_0_25_depth_le_0_50",
            description="Combined simple guard using rank, box score, and depth consistency only.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: (
                (safe_int(row.get("semantic_rank")) or 999999) <= 3
                and (safe_float(row.get("post_best_box_score")) or 0.0) >= 0.25
                and safe_float(row.get("post_min_depth_error_m")) is not None
                and safe_float(row.get("post_min_depth_error_m")) <= 0.50
            ),
        ),
        evaluate_variant(
            name="own_count_ge_4_only",
            description="Commit current unique-strong candidate only when own associated heading count >= 4.",
            evaluated_rows=evaluated_rows,
            evidence_by_request=evidence_by_request,
            labels=labels,
            predicate=lambda row: (safe_int(row.get("post_own_associated_heading_count")) or 0) >= 4,
        ),
    ]
    summary = build_summary(
        evidence_rows=evidence_rows,
        evaluated_rows=evaluated_rows,
        unsafe_rows=unsafe_rows,
        variants=variants,
        args=args,
    )
    out_root = Path(args.out_root)
    write_json(out_root / "rival_identity_unsafe_commit_diagnostic_summary.json", summary)
    write_jsonl(out_root / "rival_identity_unsafe_commit_rows.jsonl", unsafe_rows)
    write_jsonl(out_root / "rival_identity_simple_guard_variants.jsonl", variants)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose unsafe rival-identity post-observation commits.")
    parser.add_argument("--post-observation-evidence", required=True)
    parser.add_argument("--post-observation-evaluated", required=True)
    parser.add_argument("--evaluation-labels", nargs="+", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
