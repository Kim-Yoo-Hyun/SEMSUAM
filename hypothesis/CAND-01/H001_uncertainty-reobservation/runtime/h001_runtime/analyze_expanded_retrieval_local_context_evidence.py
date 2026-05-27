import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_local_context_post_observation.v1"
PROPOSED_VARIANT = "proposed_local_context_unique_own_view_advantage"
ALTERNATIVE_VARIANTS = [
    "defer_all",
    "semantic_top",
    "source_top_if_associated",
    "detector_score_best",
    "own_support_best",
    "local_context_only_best",
]
ALL_VARIANTS = [PROPOSED_VARIANT, *ALTERNATIVE_VARIANTS]


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


def safe_int(value: Any, default: int = 999999) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def label_index(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in label_rows:
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        key = (str(episode_key), str(candidate_id))
        existing = indexed.get(key)
        if existing is not None and bool(existing.get("evaluation_only_candidate_correct")) != bool(
            row.get("evaluation_only_candidate_correct")
        ):
            raise ValueError(f"conflicting label for {key}")
        indexed[key] = row
    return indexed


def request_sort_key(request_id: str) -> Tuple[int, str]:
    suffix = str(request_id).split(":")[-1]
    return (int(suffix), str(request_id)) if suffix.isdigit() else (999999, str(request_id))


def plan_groups(plan_rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        grouped[request_id].append(row)
    return grouped


def association_groups(association_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        candidate_id = str(row.get("candidate_id"))
        grouped[(request_id, candidate_id)].append(row)
    return grouped


def role_contains(row: Dict[str, Any], role: str) -> bool:
    return role in str(row.get("candidate_role") or "").split("+")


def candidate_score(row: Dict[str, Any]) -> float:
    return (
        safe_float(row.get("target_support_score"))
        or safe_float(row.get("target_semantic_score"))
        or 0.0
    )


def summarize_candidate(
    plan_row: Dict[str, Any],
    association_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    associated = [row for row in association_rows if row.get("associated_to_candidate") is True]
    mask_hits = [row for row in association_rows if row.get("projected_pixel_inside_mask") is True]
    box_hits = [row for row in association_rows if row.get("projected_pixel_inside_box") is True]
    visible = [row for row in association_rows if row.get("projection_status") == "visible"]
    detector_scores = [safe_float(row.get("best_box_score")) for row in association_rows]
    detector_scores = [score for score in detector_scores if score is not None]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in associated]
    depth_errors = [value for value in depth_errors if value is not None]
    strict_count = len(associated)
    mask_count = len(mask_hits)
    visible_count = len(visible)
    role = str(plan_row.get("candidate_role") or "")
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_evidence_only",
        "expanded_retrieval_request_id": plan_row.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": plan_row.get("rival_identity_request_id"),
        "episode_key": plan_row.get("episode_key"),
        "scene_key": plan_row.get("scene_key"),
        "scene_id": plan_row.get("scene_id"),
        "query": plan_row.get("query"),
        "candidate_id": plan_row.get("candidate_id"),
        "candidate_role": role,
        "is_source_top": role_contains(plan_row, "source_top"),
        "is_detector_strong_candidate": role_contains(plan_row, "detector_strong_candidate"),
        "is_detector_strong_rival": role_contains(plan_row, "detector_strong_rival"),
        "is_local_context_candidate": role_contains(plan_row, "local_context_candidate"),
        "semantic_rank": plan_row.get("target_semantic_rank"),
        "semantic_score": plan_row.get("target_semantic_score"),
        "support_score": plan_row.get("target_support_score"),
        "prior_detector_support_class": plan_row.get("target_detector_support_class"),
        "prior_detector_evidence_score": plan_row.get("target_detector_evidence_score"),
        "heading_rows": len(association_rows),
        "visible_count": visible_count,
        "box_hit_count": len(box_hits),
        "mask_hit_count": mask_count,
        "strict_association_count": strict_count,
        "best_box_score": max(detector_scores, default=None),
        "min_depth_error_m": min(depth_errors, default=None),
        "strong_own_view_evidence": bool(
            strict_count >= int(args.min_own_strict_count)
            and mask_count >= int(args.min_own_mask_count)
            and visible_count >= int(args.min_own_visible_count)
        ),
        "local_context_support_score": (
            strict_count * 1000
            + mask_count * 100
            + visible_count * 10
            + (safe_float(plan_row.get("target_detector_evidence_score")) or 0.0)
            + candidate_score(plan_row) * 0.001
        ),
        "uses_gt_for_action": False,
    }


def best_by(
    candidates: Sequence[Dict[str, Any]],
    key_fields: Sequence[str],
) -> Optional[Dict[str, Any]]:
    if not candidates:
        return None

    def sort_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
        values: List[Any] = []
        for field in key_fields:
            if field == "semantic_rank_ascending":
                values.append(-safe_int(row.get("semantic_rank")))
            elif field == "candidate_id":
                values.append(str(row.get("candidate_id")))
            else:
                values.append(safe_float(row.get(field)) or 0.0)
        return tuple(values)

    return max(candidates, key=sort_key)


def select_candidate(
    request_rows: Sequence[Dict[str, Any]],
    variant: str,
) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]:
    guard: Dict[str, Any] = {"variant": variant}
    if variant == "defer_all":
        return None, "defer_all_baseline", guard
    if variant == "semantic_top":
        selected = min(
            request_rows,
            key=lambda row: (
                safe_int(row.get("semantic_rank")),
                -(safe_float(row.get("semantic_score")) or 0.0),
                str(row.get("candidate_id")),
            ),
        )
        return selected, "commit_semantic_top", guard
    if variant == "source_top_if_associated":
        source_top = [row for row in request_rows if row.get("is_source_top") is True]
        selected = best_by(
            source_top,
            ["strict_association_count", "mask_hit_count", "visible_count", "semantic_score", "candidate_id"],
        )
        if selected is None or int(selected.get("strict_association_count") or 0) <= 0:
            return None, "defer_source_top_not_associated", guard
        return selected, "commit_source_top_if_associated", guard
    if variant == "detector_score_best":
        selected = best_by(
            request_rows,
            [
                "prior_detector_evidence_score",
                "strict_association_count",
                "mask_hit_count",
                "visible_count",
                "semantic_score",
                "candidate_id",
            ],
        )
        return selected, "commit_detector_score_best", guard
    if variant == "own_support_best":
        selected = best_by(
            request_rows,
            [
                "strict_association_count",
                "mask_hit_count",
                "visible_count",
                "prior_detector_evidence_score",
                "semantic_score",
                "candidate_id",
            ],
        )
        return selected, "commit_own_support_best", guard
    if variant == "local_context_only_best":
        local_rows = [row for row in request_rows if row.get("is_local_context_candidate") is True]
        selected = best_by(
            local_rows,
            [
                "strict_association_count",
                "mask_hit_count",
                "visible_count",
                "prior_detector_evidence_score",
                "semantic_score",
                "candidate_id",
            ],
        )
        if selected is None:
            return None, "defer_no_local_context_candidate", guard
        return selected, "commit_local_context_only_best", guard
    if variant == PROPOSED_VARIANT:
        strong_rows = [row for row in request_rows if row.get("strong_own_view_evidence") is True]
        guard.update(
            {
                "strong_own_view_candidate_count": len(strong_rows),
                "strong_own_view_candidate_ids": [row.get("candidate_id") for row in strong_rows],
            }
        )
        if len(strong_rows) == 1:
            return strong_rows[0], "commit_local_context_unique_own_view_advantage", guard
        if len(strong_rows) == 0:
            return None, "defer_no_strong_own_view_candidate", guard
        return None, "defer_multiple_strong_own_view_candidates", guard
    raise ValueError(f"unknown variant: {variant}")


def decision_rows(evidence_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[str(row.get("expanded_retrieval_request_id"))].append(row)
    decisions: List[Dict[str, Any]] = []
    for request_id in sorted(grouped, key=request_sort_key):
        rows = grouped[request_id]
        exemplar = rows[0]
        strong_count = sum(row.get("strong_own_view_evidence") is True for row in rows)
        for variant in ALL_VARIANTS:
            selected, reason, guard = select_candidate(rows, variant)
            action = "commit_candidate" if selected is not None else "defer"
            decisions.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_decision_only",
                    "variant": variant,
                    "expanded_retrieval_request_id": request_id,
                    "rival_identity_request_id": exemplar.get("rival_identity_request_id"),
                    "episode_key": exemplar.get("episode_key"),
                    "scene_key": exemplar.get("scene_key"),
                    "scene_id": exemplar.get("scene_id"),
                    "query": exemplar.get("query"),
                    "action": action,
                    "reason": reason,
                    "selected_candidate_id": None if selected is None else selected.get("candidate_id"),
                    "selected_candidate_role": None if selected is None else selected.get("candidate_role"),
                    "selected_semantic_rank": None if selected is None else selected.get("semantic_rank"),
                    "selected_semantic_score": None if selected is None else selected.get("semantic_score"),
                    "selected_prior_detector_evidence_score": None
                    if selected is None
                    else selected.get("prior_detector_evidence_score"),
                    "selected_strict_association_count": None
                    if selected is None
                    else selected.get("strict_association_count"),
                    "selected_mask_hit_count": None if selected is None else selected.get("mask_hit_count"),
                    "selected_visible_count": None if selected is None else selected.get("visible_count"),
                    "candidate_count": len(rows),
                    "strong_own_view_candidate_count": strong_count,
                    "candidate_ids": [row.get("candidate_id") for row in rows],
                    "strong_own_view_candidate_ids": [
                        row.get("candidate_id") for row in rows if row.get("strong_own_view_evidence") is True
                    ],
                    "decision_guard": guard,
                    "uses_gt_for_action": False,
                }
            )
    return decisions


def evaluated_rows(
    decisions: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    request_correct_counts: Dict[str, int],
) -> List[Dict[str, Any]]:
    evaluated: List[Dict[str, Any]] = []
    for row in decisions:
        selected_id = row.get("selected_candidate_id")
        commit = row.get("action") == "commit_candidate"
        label = labels.get((str(row.get("episode_key")), str(selected_id))) if commit and selected_id else None
        selected_correct = None if label is None else bool(label.get("evaluation_only_candidate_correct"))
        wrong_goal_visit = None if label is None else bool(label.get("evaluation_only_wrong_goal_visit"))
        request_correct_count = request_correct_counts.get(str(row.get("expanded_retrieval_request_id")), 0)
        out = {
            **row,
            "validation_stage": "evaluation_joined_after_action",
            "evaluation_only_request_correct_candidate_count": request_correct_count,
            "evaluation_only_selected_has_label": bool(label) if commit else None,
            "evaluation_only_selected_correct": selected_correct if commit else None,
            "evaluation_only_selected_wrong_goal_visit": wrong_goal_visit if commit else None,
            "evaluation_only_success_commit": bool(commit and selected_correct is True),
            "evaluation_only_wrong_goal_commit": bool(commit and selected_correct is False),
            "evaluation_only_no_valid_commit": bool(commit and request_correct_count == 0),
            "evaluation_only_no_label_commit": bool(commit and label is None),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
        }
        if out["evaluation_only_no_label_commit"]:
            taxonomy = "label_plumbing_failure"
        elif out["evaluation_only_no_valid_commit"]:
            taxonomy = "no_valid_candidate_commit"
        elif out["evaluation_only_wrong_goal_commit"]:
            taxonomy = "wrong_instance_selected_by_local_context_evidence"
        elif out["evaluation_only_success_commit"]:
            taxonomy = "success"
        elif row.get("reason") == "defer_multiple_strong_own_view_candidates":
            taxonomy = "ambiguous_multiple_strong_own_view"
        elif row.get("reason") == "defer_no_strong_own_view_candidate":
            taxonomy = "no_strong_own_view_evidence"
        else:
            taxonomy = str(row.get("reason"))
        out["failure_taxonomy_type"] = taxonomy
        evaluated.append(out)
    return evaluated


def summarize_variant(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    request_rows = len(rows)
    commit_rows = [row for row in rows if row.get("action") == "commit_candidate"]
    success_rows = [row for row in commit_rows if row.get("evaluation_only_success_commit") is True]
    wrong_rows = [row for row in commit_rows if row.get("evaluation_only_wrong_goal_commit") is True]
    no_valid_rows = [row for row in commit_rows if row.get("evaluation_only_no_valid_commit") is True]
    no_label_rows = [row for row in commit_rows if row.get("evaluation_only_no_label_commit") is True]
    return {
        "request_rows": request_rows,
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "no_valid_commit_rows": len(no_valid_rows),
        "no_label_commit_rows": len(no_label_rows),
        "commit_rate": ratio(len(commit_rows), request_rows),
        "success_commit_rate": ratio(len(success_rows), request_rows),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), request_rows),
        "action_counts": dict(sorted(Counter(str(row.get("action")) for row in rows).items())),
        "reason_counts": dict(sorted(Counter(str(row.get("reason")) for row in rows).items())),
        "failure_taxonomy_counts": dict(
            sorted(Counter(str(row.get("failure_taxonomy_type")) for row in rows).items())
        ),
    }


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.plan))
    association_rows = load_jsonl(Path(args.detector_associations))
    detector_summary = load_json(Path(args.detector_summary))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))
    plan_by_request = plan_groups(plan_rows)
    associations_by_candidate = association_groups(association_rows)

    evidence_rows: List[Dict[str, Any]] = []
    request_correct_counts: Dict[str, int] = {}
    for request_id in sorted(plan_by_request, key=request_sort_key):
        request_plan_rows = sorted(
            plan_by_request[request_id],
            key=lambda row: (
                safe_int(row.get("target_index")),
                safe_int(row.get("target_semantic_rank")),
                str(row.get("candidate_id")),
            ),
        )
        correct_count = 0
        for plan_row in request_plan_rows:
            label = labels.get((str(plan_row.get("episode_key")), str(plan_row.get("candidate_id"))))
            correct_count += int(label is not None and label.get("evaluation_only_candidate_correct") is True)
            evidence_rows.append(
                summarize_candidate(
                    plan_row,
                    associations_by_candidate.get((request_id, str(plan_row.get("candidate_id"))), []),
                    args,
                )
            )
        request_correct_counts[request_id] = correct_count

    decisions = decision_rows(evidence_rows)
    evaluated = evaluated_rows(decisions, labels, request_correct_counts)
    proposed_rows = [row for row in evaluated if row.get("variant") == PROPOSED_VARIANT]
    variant_summaries = {
        variant: summarize_variant([row for row in evaluated if row.get("variant") == variant])
        for variant in ALL_VARIANTS
    }
    request_rows = len(plan_by_request)
    strong_request_rows = len(
        {
            str(row.get("expanded_retrieval_request_id"))
            for row in evidence_rows
            if row.get("strong_own_view_evidence") is True
        }
    )
    local_context_candidate_rows = [
        row for row in evidence_rows if row.get("is_local_context_candidate") is True
    ]
    forbidden = action_forbidden_keys(evidence_rows + decisions)
    detector_box_rate = safe_float(detector_summary.get("rows_with_detector_box_rate"))
    sam2_mask_rate = safe_float(detector_summary.get("rows_with_sam2_mask_rate"))
    candidate_association_rate = safe_float(detector_summary.get("rows_with_candidate_association_rate"))
    proposed_summary = variant_summaries[PROPOSED_VARIANT]
    gate = {
        "detector_box_rate_pass": (detector_box_rate or 0.0) >= float(args.min_detector_box_rate),
        "sam2_mask_rate_pass": (sam2_mask_rate or 0.0) >= float(args.min_sam2_mask_rate),
        "candidate_association_rate_pass": (candidate_association_rate or 0.0)
        >= float(args.min_candidate_association_rate),
        "local_context_evidence_available_rate": ratio(strong_request_rows, request_rows),
        "local_context_evidence_available_rate_pass": (ratio(strong_request_rows, request_rows) or 0.0)
        >= float(args.min_local_context_evidence_available_rate),
        "wrong_goal_commit_rows_pass": int(proposed_summary["wrong_goal_commit_rows"])
        <= int(args.max_wrong_goal_commit_rows),
        "no_valid_commit_rows_pass": int(proposed_summary["no_valid_commit_rows"])
        <= int(args.max_no_valid_commit_rows),
        "no_label_commit_rows_pass": int(proposed_summary["no_label_commit_rows"])
        <= int(args.max_no_label_commit_rows),
        "success_commit_rows_pass": int(proposed_summary["success_commit_rows"])
        >= int(args.min_success_commit_rows),
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
    }
    gate["post_observation_gate_passed"] = all(gate.values())
    gate["paper_claim_allowed"] = False
    summary = {
        "schema_version": SCHEMA_VERSION,
        "plan": str(args.plan),
        "detector_associations": str(args.detector_associations),
        "detector_summary": str(args.detector_summary),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(out_root),
        "request_rows": request_rows,
        "plan_rows": len(plan_rows),
        "association_rows": len(association_rows),
        "evidence_rows": len(evidence_rows),
        "decision_rows": len(decisions),
        "evaluated_rows": len(evaluated),
        "detector_box_rate": detector_box_rate,
        "sam2_mask_rate": sam2_mask_rate,
        "candidate_association_rate": candidate_association_rate,
        "rows_with_candidate_association": detector_summary.get("rows_with_candidate_association"),
        "strong_own_view_request_rows": strong_request_rows,
        "local_context_candidate_rows": len(local_context_candidate_rows),
        "local_context_candidate_strong_rows": sum(
            row.get("strong_own_view_evidence") is True for row in local_context_candidate_rows
        ),
        "request_correct_candidate_count_distribution": dict(
            sorted(Counter(str(value) for value in request_correct_counts.values()).items())
        ),
        "thresholds": {
            "min_own_strict_count": int(args.min_own_strict_count),
            "min_own_mask_count": int(args.min_own_mask_count),
            "min_own_visible_count": int(args.min_own_visible_count),
            "min_detector_box_rate": float(args.min_detector_box_rate),
            "min_sam2_mask_rate": float(args.min_sam2_mask_rate),
            "min_candidate_association_rate": float(args.min_candidate_association_rate),
            "min_local_context_evidence_available_rate": float(args.min_local_context_evidence_available_rate),
            "min_success_commit_rows": int(args.min_success_commit_rows),
            "max_wrong_goal_commit_rows": int(args.max_wrong_goal_commit_rows),
        },
        "variant_summaries": variant_summaries,
        "simpler_alternative_table": [
            {"variant": variant, **variant_summaries[variant]} for variant in ALL_VARIANTS
        ],
        "gate": gate,
        "failure_taxonomy_counts": dict(
            sorted(Counter(str(row.get("failure_taxonomy_type")) for row in proposed_rows).items())
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "interpretation": {
            "fact": (
                "Action-time local-context evidence and decisions are written before evaluation labels are joined. "
                "All variants use the same frozen rows and detector/SAM2 associations."
            ),
            "agent_inference": (
                "If the proposed variant fails safety or does not beat simpler alternatives under the same labels, "
                "the local-context branch needs failure diagnosis before policy-scale promotion."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "evidence_rows": "expanded_retrieval_local_context_evidence_rows.jsonl",
            "decision_rows": "expanded_retrieval_local_context_decision_rows.jsonl",
            "evaluated_rows": "expanded_retrieval_local_context_evaluated_rows.jsonl",
            "alternative_rows": "expanded_retrieval_local_context_alternative_rows.jsonl",
            "summary": "expanded_retrieval_local_context_post_observation_summary.json",
        },
    }
    write_jsonl(out_root / "expanded_retrieval_local_context_evidence_rows.jsonl", evidence_rows)
    write_jsonl(out_root / "expanded_retrieval_local_context_decision_rows.jsonl", decisions)
    write_jsonl(out_root / "expanded_retrieval_local_context_evaluated_rows.jsonl", evaluated)
    write_jsonl(
        out_root / "expanded_retrieval_local_context_alternative_rows.jsonl",
        [row for row in evaluated if row.get("variant") != PROPOSED_VARIANT],
    )
    write_json(out_root / "expanded_retrieval_local_context_post_observation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze expanded-retrieval local-context post-observation evidence.")
    parser.add_argument("--plan", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--detector-summary", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-own-strict-count", type=int, default=3)
    parser.add_argument("--min-own-mask-count", type=int, default=4)
    parser.add_argument("--min-own-visible-count", type=int, default=5)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-candidate-association-rate", type=float, default=0.40)
    parser.add_argument("--min-local-context-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-success-commit-rows", type=int, default=2)
    parser.add_argument("--max-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument("--max-no-valid-commit-rows", type=int, default=0)
    parser.add_argument("--max-no-label-commit-rows", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["detector_box_rate_pass"]:
        raise SystemExit(1)
    if not summary["gate"]["sam2_mask_rate_pass"]:
        raise SystemExit(1)
    if not summary["gate"]["candidate_association_rate_pass"]:
        raise SystemExit(1)
    if not summary["gate"]["action_evidence_forbidden_key_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
