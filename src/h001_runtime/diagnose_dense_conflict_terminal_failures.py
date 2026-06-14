import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.design_dense_conflict_terminal_guard import candidate_passes, load_jsonl, write_json, write_jsonl


SCHEMA_VERSION = "h001.dense_conflict_terminal_failure_diagnostic.v1"


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: Any, default: int = 9999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row["episode_key"]), str(row["candidate_id"])): row
        for row in label_rows
    }


def row_lookup(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row["episode_key"]): row for row in rows}


def candidate_snapshot(candidate: Optional[Dict[str, Any]], labels: Dict[Tuple[str, str], Dict[str, Any]], episode_key: str, guard: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if candidate is None:
        return None
    candidate_id = str(candidate.get("candidate_id"))
    label = labels.get((str(episode_key), candidate_id), {})
    passes, reason = candidate_passes(candidate, guard)
    return {
        "candidate_id": candidate_id,
        "evaluation_only_candidate_correct": bool(label.get("evaluation_only_candidate_correct")),
        "evaluation_only_recall_rank": label.get("evaluation_only_recall_rank"),
        "semantic_rank": safe_int(candidate.get("semantic_rank")),
        "semantic_score": safe_float(candidate.get("semantic_score")),
        "support_score": safe_float(candidate.get("support_score")),
        "detector_score_max": safe_float(candidate.get("detector_score_max")),
        "min_depth_error_m": safe_float(candidate.get("min_depth_error_m")),
        "associated_heading_count": safe_int(candidate.get("associated_heading_count"), 0),
        "mask_hit_count": safe_int(candidate.get("mask_hit_count"), 0),
        "box_hit_count": safe_int(candidate.get("box_hit_count"), 0),
        "visible_count": safe_int(candidate.get("visible_count"), 0),
        "depth_match_count": safe_int(candidate.get("depth_match_count"), 0),
        "depth_mismatch_count": safe_int(candidate.get("depth_mismatch_count"), 0),
        "positive_support": bool(candidate.get("positive_support")),
        "guard_passes": bool(passes),
        "guard_reject_reason": reason,
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "uses_gt_for_action": False,
    }


def choose_best_correct(candidates: Sequence[Dict[str, Any]], labels: Dict[Tuple[str, str], Dict[str, Any]], episode_key: str) -> Optional[Dict[str, Any]]:
    correct = [
        candidate
        for candidate in candidates
        if labels.get((str(episode_key), str(candidate.get("candidate_id"))), {}).get("evaluation_only_candidate_correct")
    ]
    return max(
        correct,
        key=lambda item: (
            safe_float(item.get("support_score")) or 0.0,
            safe_float(item.get("detector_score_max")) or 0.0,
            safe_float(item.get("semantic_score")) or 0.0,
            -safe_int(item.get("semantic_rank")),
        ),
        default=None,
    )


def feature_delta(selected: Optional[Dict[str, Any]], correct: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if selected is None or correct is None:
        return {}

    def delta(name: str) -> Optional[float]:
        left = safe_float(selected.get(name))
        right = safe_float(correct.get(name))
        if left is None or right is None:
            return None
        return left - right

    return {
        "selected_minus_correct_support_score": delta("support_score"),
        "selected_minus_correct_detector_score_max": delta("detector_score_max"),
        "selected_minus_correct_semantic_score": delta("semantic_score"),
        "selected_minus_correct_min_depth_error_m": delta("min_depth_error_m"),
        "selected_minus_correct_associated_heading_count": safe_int(selected.get("associated_heading_count"), 0)
        - safe_int(correct.get("associated_heading_count"), 0),
        "selected_minus_correct_mask_hit_count": safe_int(selected.get("mask_hit_count"), 0)
        - safe_int(correct.get("mask_hit_count"), 0),
        "selected_minus_correct_box_hit_count": safe_int(selected.get("box_hit_count"), 0)
        - safe_int(correct.get("box_hit_count"), 0),
        "selected_minus_correct_semantic_rank": safe_int(selected.get("semantic_rank"))
        - safe_int(correct.get("semantic_rank")),
    }


def repeated_wrong_keys(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], int]:
    counts: Dict[Tuple[str, str, str], int] = defaultdict(int)
    for row in rows:
        if row.get("evaluation_only_wrong_goal_commit") is not True:
            continue
        key = (
            str(row.get("scene_key")),
            str(row.get("query")),
            str(row.get("selected_candidate_id")),
        )
        counts[key] += 1
    return counts


def mechanism_tags(
    selected: Optional[Dict[str, Any]],
    correct: Optional[Dict[str, Any]],
    evaluated: Dict[str, Any],
    repeat_count: int,
) -> List[str]:
    tags: List[str] = []
    is_wrong_commit = evaluated.get("evaluation_only_wrong_goal_commit") is True
    is_success_commit = evaluated.get("evaluation_only_success_commit") is True
    if is_wrong_commit:
        tags.append("wrong_commit")
    if is_success_commit:
        tags.append("successful_commit")
    if selected and selected.get("guard_passes"):
        tags.append("selected_candidate_passes_frozen_guard")
    if is_wrong_commit and selected and selected.get("guard_passes"):
        tags.append("wrong_candidate_passes_frozen_guard")
    if correct:
        tags.append("correct_candidate_present")
        if correct.get("positive_support"):
            tags.append("correct_candidate_positive_support_present")
        if correct.get("guard_passes"):
            tags.append("correct_candidate_also_guard_eligible")
        else:
            tags.append("correct_candidate_blocked_by_guard")

    if selected and correct and selected.get("candidate_id") == correct.get("candidate_id"):
        tags.append("selected_is_correct_candidate")
    elif selected and correct:
        support_delta = safe_float(selected.get("support_score")) - safe_float(correct.get("support_score"))  # type: ignore[operator]
        detector_delta = safe_float(selected.get("detector_score_max")) - safe_float(correct.get("detector_score_max"))  # type: ignore[operator]
        depth_delta = safe_float(selected.get("min_depth_error_m")) - safe_float(correct.get("min_depth_error_m"))  # type: ignore[operator]
        rank_delta = safe_int(selected.get("semantic_rank")) - safe_int(correct.get("semantic_rank"))
        if support_delta >= 0:
            tags.append("wrong_support_score_ge_correct")
        if abs(support_delta) <= 0.02:
            tags.append("support_score_saturated")
        if detector_delta >= -0.01:
            tags.append("detector_score_tie_or_wrong_advantage")
        if depth_delta <= 0:
            tags.append("wrong_depth_error_le_correct")
        if rank_delta <= 0:
            tags.append("wrong_semantic_rank_as_good_or_better")
        if selected.get("semantic_rank") == 1:
            tags.append("wrong_is_semantic_top")
    if repeat_count > 1:
        tags.append("same_wrong_candidate_repeated_across_episodes")
    return sorted(set(tags))


def primary_mechanism(tags: Sequence[str]) -> str:
    tagset = set(tags)
    if "successful_commit" in tagset:
        return "successful_commit_reference"
    if "same_wrong_candidate_repeated_across_episodes" in tagset:
        return "repeated_wrong_instance_selected_by_saturated_support"
    if "correct_candidate_also_guard_eligible" in tagset and "wrong_support_score_ge_correct" in tagset:
        return "guard_cannot_arbitrate_between_eligible_correct_and_wrong"
    if "correct_candidate_blocked_by_guard" in tagset:
        return "guard_blocks_correct_but_not_wrong"
    if "wrong_is_semantic_top" in tagset:
        return "semantic_prior_points_to_wrong_instance"
    return "wrong_instance_receives_non_discriminative_support"


def diagnose_source(
    *,
    source_name: str,
    role: str,
    action_evidence: Path,
    evaluation_labels: Path,
    evaluated_rows: Path,
    guard: Dict[str, Any],
) -> List[Dict[str, Any]]:
    action_rows = load_jsonl(action_evidence)
    labels = label_lookup(load_jsonl(evaluation_labels))
    evaluated = row_lookup(load_jsonl(evaluated_rows))
    repeat_counts = repeated_wrong_keys(list(evaluated.values()))
    outputs: List[Dict[str, Any]] = []

    for action_row in action_rows:
        episode_key = str(action_row["episode_key"])
        evaluated_row = evaluated.get(episode_key, {})
        selected_id = str(evaluated_row.get("selected_candidate_id"))
        candidates = list(action_row.get("candidate_evidence") or [])
        selected_candidate = next((item for item in candidates if str(item.get("candidate_id")) == selected_id), None)
        best_correct = choose_best_correct(candidates, labels, episode_key)
        selected = candidate_snapshot(selected_candidate, labels, episode_key, guard)
        correct = candidate_snapshot(best_correct, labels, episode_key, guard)
        repeat_key = (
            str(action_row.get("scene_key")),
            str(action_row.get("query")),
            selected_id,
        )
        tags = mechanism_tags(selected, correct, evaluated_row, repeat_counts.get(repeat_key, 0))
        outputs.append(
            {
                "schema_version": SCHEMA_VERSION,
                "source_name": source_name,
                "role": role,
                "episode_key": episode_key,
                "scene_key": action_row.get("scene_key"),
                "query": action_row.get("query"),
                "validation_action": evaluated_row.get("action"),
                "validation_reason": evaluated_row.get("reason"),
                "validation_wrong_goal_commit": bool(evaluated_row.get("evaluation_only_wrong_goal_commit")),
                "validation_success_commit": bool(evaluated_row.get("evaluation_only_success_commit")),
                "failure_taxonomy_type": evaluated_row.get("failure_taxonomy_type"),
                "selected_candidate": selected,
                "best_correct_candidate": correct,
                "feature_delta_selected_minus_correct": feature_delta(selected_candidate, best_correct),
                "positive_support_candidate_count": action_row.get("positive_support_candidate_count"),
                "candidate_count": action_row.get("candidate_count"),
                "semantic_top2_score_gap": action_row.get("semantic_top2_score_gap"),
                "mechanism_tags": tags,
                "primary_mechanism": primary_mechanism(tags),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return outputs


def revision_contract(summary: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": "h001.dense_conflict_terminal_revision_contract.v1",
        "revision_name": "rival_identity_confirmation_v1",
        "status": "design_contract_not_implemented",
        "rejected_rule": "strict_depth_consistency_v1",
        "failure_mechanism": (
            "Depth-consistent detector support is not instance-discriminative when multiple same-category "
            "candidates have saturated support; wrong instances can satisfy the same guard as correct candidates."
        ),
        "principle": (
            "Treat dense same-category positive support as an identity ambiguity signal. Commit only when one "
            "candidate is uniquely supported across semantic prior, detector/mask evidence, and local rival "
            "comparison; otherwise request additional observation instead of terminal commit."
        ),
        "action_time_inputs": [
            "candidate_evidence without evaluation labels",
            "semantic rank and semantic top-2 gap",
            "detector score and mask/box/association counts",
            "depth consistency and depth rival gap",
            "same-category eligible rival count",
            "candidate visit/position geometry for next observation planning",
        ],
        "forbidden_inputs": [
            "evaluation_only_candidate_correct",
            "evaluation_only_recall_rank",
            "GT object position",
            "GT geodesic distance to object",
        ],
        "proposed_actions": [
            "commit_candidate only for unique multi-axis support",
            "request_rival_identity_confirmation when multiple same-category candidates pass guard",
            "defer_or_expand_retrieval when correct evidence is blocked by association",
        ],
        "simpler_alternatives_to_ablate": [
            {
                "name": "support_margin_only",
                "expected_failure": "keeps failing when wrong and correct support scores are saturated or tied",
            },
            {
                "name": "depth_margin_only",
                "expected_failure": "keeps failing when wrong instance is also depth-consistent or depth-better",
            },
            {
                "name": "semantic_top_only",
                "expected_failure": "keeps failing when semantic rank points to a wrong instance",
            },
            {
                "name": "defer_all_ambiguous",
                "expected_failure": "safe but inert; loses successful terminal commits and does not show utility",
            },
        ],
        "next_ablation_expectations": {
            "wrong_goal_commit_rows": "must decrease versus strict_depth_consistency_v1 on primary and stress rows",
            "success_commit_rows": "must not collapse to zero on associated primary rows",
            "request_identity_confirmation_rows": "should explain most rows previously tagged as saturated rival ambiguity",
            "paper_claim_status": "design_only_until validated on a fresh or predeclared split",
        },
        "diagnostic_summary_dependency": summary,
    }


def summarize(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    wrong_rows = [row for row in rows if row["validation_wrong_goal_commit"]]
    success_rows = [row for row in rows if row["validation_success_commit"]]
    mechanism_counts = Counter(str(row["primary_mechanism"]) for row in rows)
    tag_counts = Counter(tag for row in rows for tag in row["mechanism_tags"])
    wrong_mechanism_counts = Counter(str(row["primary_mechanism"]) for row in wrong_rows)
    wrong_tag_counts = Counter(tag for row in wrong_rows for tag in row["mechanism_tags"])
    by_source = defaultdict(Counter)
    wrong_by_source = defaultdict(Counter)
    for row in rows:
        by_source[str(row["source_name"])][str(row["primary_mechanism"])] += 1
        if row["validation_wrong_goal_commit"]:
            wrong_by_source[str(row["source_name"])][str(row["primary_mechanism"])] += 1

    return {
        "schema_version": SCHEMA_VERSION,
        "rows": len(rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), len(rows)),
        "success_commit_rate": ratio(len(success_rows), len(rows)),
        "primary_mechanism_counts": dict(sorted(mechanism_counts.items())),
        "mechanism_tag_counts": dict(sorted(tag_counts.items())),
        "wrong_primary_mechanism_counts": dict(sorted(wrong_mechanism_counts.items())),
        "wrong_mechanism_tag_counts": dict(sorted(wrong_tag_counts.items())),
        "primary_mechanism_by_source": {
            source: dict(sorted(counts.items()))
            for source, counts in sorted(by_source.items())
        },
        "wrong_primary_mechanism_by_source": {
            source: dict(sorted(counts.items()))
            for source, counts in sorted(wrong_by_source.items())
        },
        "mechanism_interpretation": {
            "fact": "The diagnostic joins evaluation labels only after action-time decisions are fixed.",
            "agent_inference": (
                "The dominant failure is not missing detector evidence. It is non-discriminative positive support "
                "among same-category rivals, so the next method should model rival identity ambiguity rather than "
                "tighten a single depth/support threshold on this split."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    guard_config = load_json(Path(args.guard_config))
    guard = dict(guard_config.get("params") or {})
    rows: List[Dict[str, Any]] = []
    rows.extend(
        diagnose_source(
            source_name="primary_independent",
            role="primary",
            action_evidence=Path(args.primary_action_evidence),
            evaluation_labels=Path(args.primary_evaluation_labels),
            evaluated_rows=Path(args.primary_evaluated_rows),
            guard=guard,
        )
    )
    rows.extend(
        diagnose_source(
            source_name="secondary_stress",
            role="secondary_stress",
            action_evidence=Path(args.secondary_action_evidence),
            evaluation_labels=Path(args.secondary_evaluation_labels),
            evaluated_rows=Path(args.secondary_evaluated_rows),
            guard=guard,
        )
    )
    summary = summarize(rows)
    contract = revision_contract(summary)

    out_root = Path(args.out_root)
    write_jsonl(out_root / "terminal_failure_diagnostic_rows.jsonl", rows)
    write_json(out_root / "terminal_failure_diagnostic_summary.json", summary)
    write_json(out_root / "mechanism_revision_contract.json", contract)
    return {
        **summary,
        "out_root": str(out_root),
        "output_files": {
            "rows": "terminal_failure_diagnostic_rows.jsonl",
            "summary": "terminal_failure_diagnostic_summary.json",
            "mechanism_revision_contract": "mechanism_revision_contract.json",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose independent dense-conflict terminal validation failures.")
    parser.add_argument("--guard-config", required=True)
    parser.add_argument("--primary-action-evidence", required=True)
    parser.add_argument("--primary-evaluation-labels", required=True)
    parser.add_argument("--primary-evaluated-rows", required=True)
    parser.add_argument("--secondary-action-evidence", required=True)
    parser.add_argument("--secondary-evaluation-labels", required=True)
    parser.add_argument("--secondary-evaluated-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
