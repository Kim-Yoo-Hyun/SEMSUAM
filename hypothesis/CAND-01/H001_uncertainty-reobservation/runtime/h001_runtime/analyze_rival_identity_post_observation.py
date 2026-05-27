import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.rival_identity_post_observation.v1"
DEFAULT_OBJECTIVE = "unique_strong_own_view_identity"
GOAL_VALIDITY_OBJECTIVE = "goal_validity_arbitration_v1"


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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def label_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    lookup: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in label_rows:
        key = (str(row["episode_key"]), str(row["candidate_id"]))
        existing = lookup.get(key)
        if existing is not None and bool(existing.get("evaluation_only_candidate_correct")) != bool(
            row.get("evaluation_only_candidate_correct")
        ):
            raise ValueError(f"conflicting label for {key}")
        lookup[key] = row
    return lookup


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def plan_index(plan_rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    requests: Dict[str, Dict[str, Any]] = {}
    for row in plan_rows:
        request_id = str(row["rival_identity_request_id"])
        request = requests.setdefault(
            request_id,
            {
                "rival_identity_request_id": request_id,
                "episode_key": row["episode_key"],
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "role": row.get("role"),
                "request_index": row.get("request_index"),
                "request_reason": row.get("request_reason"),
                "focus_candidate_id": row.get("focus_candidate_id"),
                "rival_candidate_ids": list(row.get("rival_candidate_ids") or []),
                "source_candidate_count": row.get("candidate_count"),
                "positive_support_candidate_count": row.get("positive_support_candidate_count"),
                "candidate_ids": set(),
                "target_candidate_ids": set(),
                "target_roles_by_candidate": defaultdict(set),
                "candidate_meta": {},
                "plan_rows": 0,
            },
        )
        request["plan_rows"] += 1
        target_candidate_id = str(row.get("target_candidate_id"))
        request["candidate_ids"].add(target_candidate_id)
        request["target_candidate_ids"].add(target_candidate_id)
        for candidate_id in row.get("candidate_ids") or []:
            request["candidate_ids"].add(str(candidate_id))
        if request.get("source_candidate_count") is None and row.get("candidate_count") is not None:
            request["source_candidate_count"] = row.get("candidate_count")
        if request.get("positive_support_candidate_count") is None and row.get("positive_support_candidate_count") is not None:
            request["positive_support_candidate_count"] = row.get("positive_support_candidate_count")
        request["target_roles_by_candidate"][target_candidate_id].add(str(row.get("rival_identity_target_role")))
        request["candidate_meta"].setdefault(
            target_candidate_id,
            {
                "candidate_id": target_candidate_id,
                "target_role": row.get("rival_identity_target_role"),
                "semantic_rank": row.get("target_semantic_rank"),
                "semantic_score": row.get("target_semantic_score"),
                "support_score": row.get("target_support_score"),
                "positive_support": row.get("target_positive_support"),
                "pre_associated_heading_count": row.get("target_associated_heading_count"),
                "pre_box_hit_count": row.get("target_box_hit_count"),
                "pre_mask_hit_count": row.get("target_mask_hit_count"),
                "pre_detector_score_max": row.get("target_detector_score_max"),
                "pre_min_depth_error_m": row.get("target_min_depth_error_m"),
                "target_position": row.get("target_position"),
                "target_visit_position": row.get("target_visit_position"),
                "uses_gt_for_action": False,
            },
        )
    return requests


def association_index(association_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    indexed: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        indexed[(str(row["rival_identity_request_id"]), str(row["candidate_id"]))].append(row)
    return indexed


def request_sort_key(request_id: str) -> Tuple[int, str]:
    suffix = request_id.split(":")[-1]
    if suffix.isdigit():
        return int(suffix), request_id
    return 999999, request_id


def summarize_candidate(
    *,
    request: Dict[str, Any],
    candidate_id: str,
    rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    own = [row for row in associated if str(row.get("candidate_id")) == str(row.get("target_candidate_id"))]
    cross = [row for row in associated if str(row.get("candidate_id")) != str(row.get("target_candidate_id"))]
    box_scores = [safe_float(row.get("best_box_score")) for row in rows]
    box_scores = [score for score in box_scores if score is not None]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    depth_errors = [error for error in depth_errors if error is not None]
    own_roles = sorted({str(row.get("rival_identity_target_role")) for row in own})
    cross_roles = sorted({str(row.get("rival_identity_target_role")) for row in cross})
    meta = dict(request["candidate_meta"].get(candidate_id) or {"candidate_id": candidate_id, "uses_gt_for_action": False})
    planned_target_ids = sorted(str(value) for value in request["target_candidate_ids"])
    planned_target_count = len(planned_target_ids)
    positive_support_candidate_count = safe_int(request.get("positive_support_candidate_count"))
    has_rival_contrast = planned_target_count >= 2 and positive_support_candidate_count >= 2
    single_positive_candidate = planned_target_count <= 1 or positive_support_candidate_count <= 1
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_evidence_only",
        "rival_identity_request_id": request["rival_identity_request_id"],
        "episode_key": request["episode_key"],
        "scene_key": request.get("scene_key"),
        "scene_id": request.get("scene_id"),
        "query": request.get("query"),
        "role": request.get("role"),
        "request_index": request.get("request_index"),
        "request_reason": request.get("request_reason"),
        "focus_candidate_id": request.get("focus_candidate_id"),
        "rival_candidate_ids": request.get("rival_candidate_ids"),
        "source_candidate_count": request.get("source_candidate_count"),
        "positive_support_candidate_count": request.get("positive_support_candidate_count"),
        "planned_target_count": planned_target_count,
        "planned_target_ids": planned_target_ids,
        "has_rival_contrast": has_rival_contrast,
        "single_positive_candidate": single_positive_candidate,
        "request_taxonomy_route": "object_existence_validation"
        if single_positive_candidate
        else "rival_identity_arbitration"
        if has_rival_contrast
        else "insufficient_contrast_review",
        **meta,
        "detector_association_rows": len(rows),
        "post_associated_heading_count": len(associated),
        "post_own_associated_heading_count": len(own),
        "post_cross_associated_heading_count": len(cross),
        "post_best_box_score": max(box_scores, default=None),
        "post_min_depth_error_m": min(depth_errors, default=None),
        "post_own_target_role_count": len(own_roles),
        "post_cross_target_role_count": len(cross_roles),
        "post_own_target_roles": own_roles,
        "post_cross_target_roles": cross_roles,
        "uses_gt_for_action": False,
    }


def build_evidence_rows(
    plan_rows: Sequence[Dict[str, Any]],
    association_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    requests = plan_index(plan_rows)
    associations = association_index(association_rows)
    evidence_rows: List[Dict[str, Any]] = []
    for request_id in sorted(requests, key=request_sort_key):
        request = requests[request_id]
        candidates = sorted(str(candidate_id) for candidate_id in request["candidate_ids"])
        prelim = [
            summarize_candidate(
                request=request,
                candidate_id=candidate_id,
                rows=associations.get((request_id, candidate_id), []),
            )
            for candidate_id in candidates
        ]
        own_counts = {
            row["candidate_id"]: int(row["post_own_associated_heading_count"])
            for row in prelim
        }
        for row in prelim:
            other_best = max(
                (count for candidate_id, count in own_counts.items() if candidate_id != row["candidate_id"]),
                default=0,
            )
            row["post_identity_margin"] = int(row["post_own_associated_heading_count"]) - int(other_best)
            row["strong_identity_evidence"] = bool(
                int(row["post_own_associated_heading_count"]) >= 2
                and int(row["post_own_associated_heading_count"]) > int(row["post_cross_associated_heading_count"])
                and int(row["post_identity_margin"]) >= 2
            )
            evidence_rows.append(row)
    return evidence_rows


def request_reason(evidence_rows: Sequence[Dict[str, Any]], strong_rows: Sequence[Dict[str, Any]]) -> str:
    if len(strong_rows) > 1:
        return "post_observation_multiple_strong_candidates"
    if not any(int(row["post_own_associated_heading_count"]) > 0 for row in evidence_rows):
        return "post_observation_no_candidate_support"
    if any(
        int(row["post_cross_associated_heading_count"]) >= int(row["post_own_associated_heading_count"])
        and int(row["post_cross_associated_heading_count"]) > 0
        for row in evidence_rows
    ):
        return "post_observation_cross_view_aliasing"
    if any(int(row["post_own_associated_heading_count"]) >= 2 for row in evidence_rows):
        return "post_observation_margin_too_small"
    return "post_observation_safe_defer"


def goal_validity_surrogate(row: Dict[str, Any]) -> bool:
    own = int(row.get("post_own_associated_heading_count") or 0)
    cross = int(row.get("post_cross_associated_heading_count") or 0)
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


def low_goal_validity_reason(evidence_rows: Sequence[Dict[str, Any]], strong_rows: Sequence[Dict[str, Any]]) -> str:
    if not any(int(row["post_own_associated_heading_count"]) > 0 for row in evidence_rows):
        return "post_observation_no_candidate_support"
    if not any(safe_float(row.get("post_best_box_score")) is not None for row in evidence_rows):
        return "defer_low_goal_validity_no_detector_box"
    if any(int(row.get("post_cross_associated_heading_count") or 0) > 0 for row in evidence_rows):
        return "defer_low_goal_validity_cross_view_aliasing"
    if strong_rows:
        return "defer_visible_object_not_goal_validity"
    return "defer_low_goal_validity_surrogate"


def decision_rows(evidence_rows: Sequence[Dict[str, Any]], objective: str = DEFAULT_OBJECTIVE) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[str(row["rival_identity_request_id"])].append(row)

    decisions: List[Dict[str, Any]] = []
    for request_id in sorted(grouped, key=request_sort_key):
        rows = grouped[request_id]
        strong = [row for row in rows if row.get("strong_identity_evidence") is True]
        exemplar = rows[0]
        request_taxonomy_route = exemplar.get("request_taxonomy_route")
        requires_object_existence_validation = request_taxonomy_route == "object_existence_validation"
        validity_rows = [row for row in rows if goal_validity_surrogate(row)]
        if requires_object_existence_validation:
            selected = None
            action = "defer_object_existence_validation"
            reason = "object_existence_requires_independent_confirmation"
            selected_candidate_id = None
        elif objective == GOAL_VALIDITY_OBJECTIVE:
            if len(validity_rows) == 1:
                selected = validity_rows[0]
                action = "commit_candidate"
                reason = "commit_goal_validity_unique_semantic_geometric_consistency"
                selected_candidate_id = str(selected["candidate_id"])
            elif len(validity_rows) > 1:
                selected = None
                action = "defer_unresolved_identity"
                reason = "defer_comparable_goal_validity_candidates"
                selected_candidate_id = None
            else:
                selected = None
                action = "defer_expanded_retrieval_needed"
                reason = low_goal_validity_reason(rows, strong)
                selected_candidate_id = None
        elif len(strong) == 1:
            selected = strong[0]
            action = "commit_candidate"
            reason = "commit_unique_strong_own_view_identity"
            selected_candidate_id = str(selected["candidate_id"])
        else:
            selected = None
            action = "defer_unresolved_identity"
            reason = request_reason(rows, strong)
            selected_candidate_id = None
        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_decision_only",
                "rival_identity_request_id": request_id,
                "episode_key": exemplar["episode_key"],
                "scene_key": exemplar.get("scene_key"),
                "query": exemplar.get("query"),
                "role": exemplar.get("role"),
                "request_index": exemplar.get("request_index"),
                "request_reason": exemplar.get("request_reason"),
                "action": action,
                "reason": reason,
                "selected_candidate_id": selected_candidate_id,
                "objective": objective,
                "strong_identity_candidate_count": len(strong),
                "goal_validity_candidate_count": len(validity_rows),
                "candidate_count": len(rows),
                "selected_post_own_associated_heading_count": None
                if selected is None
                else selected.get("post_own_associated_heading_count"),
                "selected_post_cross_associated_heading_count": None
                if selected is None
                else selected.get("post_cross_associated_heading_count"),
                "selected_post_identity_margin": None if selected is None else selected.get("post_identity_margin"),
                "selected_post_best_box_score": None if selected is None else selected.get("post_best_box_score"),
                "selected_post_min_depth_error_m": None if selected is None else selected.get("post_min_depth_error_m"),
                "selected_semantic_rank": None if selected is None else selected.get("semantic_rank"),
                "source_candidate_count": exemplar.get("source_candidate_count"),
                "positive_support_candidate_count": exemplar.get("positive_support_candidate_count"),
                "planned_target_count": exemplar.get("planned_target_count"),
                "planned_target_ids": exemplar.get("planned_target_ids"),
                "evidence_candidate_count": len(rows),
                "requires_object_existence_validation": requires_object_existence_validation,
                "uses_gt_for_action": False,
            }
        )
        decisions[-1]["has_rival_contrast"] = bool(exemplar.get("has_rival_contrast"))
        decisions[-1]["single_positive_candidate"] = bool(exemplar.get("single_positive_candidate"))
        decisions[-1]["request_taxonomy_route"] = request_taxonomy_route
    return decisions


def failure_taxonomy(row: Dict[str, Any]) -> str:
    if row.get("evaluation_only_no_label_commit") is True:
        return "label_plumbing_failure"
    if row.get("evaluation_only_wrong_goal_commit") is True:
        if row.get("single_positive_candidate") is True:
            return "object_existence_false_positive_commit"
        if row.get("has_rival_contrast") is True:
            return "unsafe_rival_identity_commit"
        return "unsafe_post_observation_commit"
    if row.get("action") == "commit_candidate":
        return "none"
    if row.get("action") == "defer_object_existence_validation":
        return "object_existence_deferred_no_independent_confirmation"
    if (
        row.get("reason") == "post_observation_cross_view_aliasing"
        and row.get("has_rival_contrast") is True
    ):
        return "rival_identity_unresolved_cross_view_aliasing"
    return str(row.get("reason") or "post_observation_safe_defer")


def evaluated_rows(
    decisions: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for decision in decisions:
        selected_id = decision.get("selected_candidate_id")
        label = labels.get((str(decision["episode_key"]), str(selected_id))) if selected_id else None
        selected_correct = bool(label.get("evaluation_only_candidate_correct")) if label else None
        commit = decision["action"] == "commit_candidate"
        row = {
            **decision,
            "validation_stage": "evaluation_joined_after_action",
            "evaluation_only_selected_has_label": bool(label) if commit else None,
            "evaluation_only_selected_correct": selected_correct if commit else None,
            "evaluation_only_success_commit": bool(commit and selected_correct is True),
            "evaluation_only_wrong_goal_commit": bool(commit and selected_correct is False),
            "evaluation_only_no_label_commit": bool(commit and label is None),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
        }
        row["failure_taxonomy_type"] = failure_taxonomy(row)
        rows.append(row)
    return rows


def summarize(
    *,
    evidence_rows: Sequence[Dict[str, Any]],
    decisions: Sequence[Dict[str, Any]],
    evaluated: Sequence[Dict[str, Any]],
    forbidden: Sequence[str],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    request_rows = len(evaluated)
    commit_rows = [row for row in evaluated if row["action"] == "commit_candidate"]
    success_rows = [row for row in evaluated if row["evaluation_only_success_commit"]]
    wrong_rows = [row for row in evaluated if row["evaluation_only_wrong_goal_commit"]]
    no_label_rows = [row for row in evaluated if row["evaluation_only_no_label_commit"]]
    primary_rows = [row for row in evaluated if row.get("role") == "primary"]
    primary_success = [row for row in primary_rows if row["evaluation_only_success_commit"]]
    primary_wrong = [row for row in primary_rows if row["evaluation_only_wrong_goal_commit"]]
    secondary_rows = [row for row in evaluated if row.get("role") == "secondary_stress"]
    secondary_wrong = [row for row in secondary_rows if row["evaluation_only_wrong_goal_commit"]]
    defer_rows = [row for row in evaluated if str(row["action"]).startswith("defer_")]
    unresolved_identity_defer = [row for row in evaluated if row["action"] == "defer_unresolved_identity"]
    object_existence_defer = [row for row in evaluated if row["action"] == "defer_object_existence_validation"]
    object_existence_wrong = [
        row for row in evaluated if row["failure_taxonomy_type"] == "object_existence_false_positive_commit"
    ]
    unsafe_rival_identity = [row for row in evaluated if row["failure_taxonomy_type"] == "unsafe_rival_identity_commit"]
    rival_identity_cross_view = [
        row for row in evaluated
        if row["failure_taxonomy_type"] in {
            "rival_identity_unresolved_cross_view_aliasing",
            "post_observation_cross_view_aliasing",
        }
    ]

    gates = {
        "wrong_goal_gate_passed": len(wrong_rows) <= int(args.max_wrong_goal_commit_rows),
        "no_label_gate_passed": len(no_label_rows) <= int(args.max_no_label_commit_rows),
        "new_primary_success_gate_passed": len(primary_success) >= int(args.min_new_primary_success_commit_rows),
        "resolved_request_gate_passed": len(commit_rows) >= int(args.min_resolved_request_rows),
        "secondary_stress_safety_gate_passed": len(secondary_wrong)
        <= int(args.max_secondary_stress_wrong_goal_commit_rows),
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
    }
    gates["post_observation_gate_passed"] = all(gates.values())

    return {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "inputs": {
            "detector_associations": str(args.detector_associations),
            "plan": str(args.plan),
            "primary_evaluation_labels": str(args.primary_evaluation_labels),
            "secondary_evaluation_labels": str(args.secondary_evaluation_labels),
            "objective": str(args.objective),
        },
        "request_rows": request_rows,
        "evidence_rows": len(evidence_rows),
        "decision_rows": len(decisions),
        "resolved_request_rows": len(commit_rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "no_label_commit_rows": len(no_label_rows),
        "new_primary_success_commit_rows": len(primary_success),
        "primary_wrong_goal_commit_rows": len(primary_wrong),
        "secondary_stress_wrong_goal_commit_rows": len(secondary_wrong),
        "defer_rows": len(defer_rows),
        "defer_unresolved_identity_rows": len(unresolved_identity_defer),
        "defer_object_existence_validation_rows": len(object_existence_defer),
        "identity_evidence_non_discriminative_rows": len(
            [
                row
                for row in evaluated
                if row["action"] == "defer_unresolved_identity"
                and row["failure_taxonomy_type"]
                not in {"post_observation_no_candidate_support", "post_observation_safe_defer"}
            ]
        ),
        "post_observation_no_candidate_support_rows": len(
            [row for row in evaluated if row["failure_taxonomy_type"] == "post_observation_no_candidate_support"]
        ),
        "post_observation_cross_view_aliasing_rows": len(rival_identity_cross_view),
        "object_existence_false_positive_commit_rows": len(object_existence_wrong),
        "object_existence_deferred_no_independent_confirmation_rows": len(
            [
                row for row in evaluated
                if row["failure_taxonomy_type"] == "object_existence_deferred_no_independent_confirmation"
            ]
        ),
        "unsafe_rival_identity_commit_rows": len(unsafe_rival_identity),
        "rival_identity_unresolved_cross_view_aliasing_rows": len(
            [
                row for row in evaluated
                if row["failure_taxonomy_type"] == "rival_identity_unresolved_cross_view_aliasing"
            ]
        ),
        "commit_rate": ratio(len(commit_rows), request_rows),
        "success_commit_rate": ratio(len(success_rows), request_rows),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), request_rows),
        "action_counts": dict(sorted(Counter(str(row["action"]) for row in evaluated).items())),
        "reason_counts": dict(sorted(Counter(str(row["reason"]) for row in evaluated).items())),
        "objective_counts": dict(sorted(Counter(str(row.get("objective")) for row in evaluated).items())),
        "request_taxonomy_route_counts": dict(
            sorted(Counter(str(row.get("request_taxonomy_route")) for row in evaluated).items())
        ),
        "failure_taxonomy_counts": dict(
            sorted(Counter(str(row["failure_taxonomy_type"]) for row in evaluated).items())
        ),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in evaluated).items())),
        "role_counts": dict(sorted(Counter(str(row.get("role")) for row in evaluated).items())),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden)[:50],
        "gates": gates,
        "paper_claim_allowed": False,
        "paper_claim_status": "diagnostic_post_observation_contract_only_requires_fresh_or_predeclared_validation",
        "interpretation": {
            "fact": (
                "The analyzer writes action-time evidence and decisions before joining evaluation labels. "
                "The fixed decision rule is applied without category-specific branches. "
                "Failure taxonomy now separates single-positive-candidate object-existence failures from "
                "multi-candidate rival-identity arbitration failures. The object-existence branch is a no-commit "
                "safety branch until independent object-existence validation is defined."
            ),
            "agent_inference": (
                "A gate pass supports this diagnostic active-observation contract, but does not by itself "
                "establish a paper-facing ObjectNav utility claim."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "evidence_rows": "rival_identity_post_observation_evidence.jsonl",
            "decision_rows": "rival_identity_post_observation_decisions.jsonl",
            "evaluated_rows": "rival_identity_post_observation_evaluated.jsonl",
            "summary": "rival_identity_observation_validation_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    plan_rows = load_jsonl(Path(args.plan))
    association_rows = load_jsonl(Path(args.detector_associations))
    labels = label_lookup(
        load_jsonl(Path(args.primary_evaluation_labels)) + load_jsonl(Path(args.secondary_evaluation_labels))
    )
    forbidden = action_forbidden_keys(plan_rows + association_rows)
    evidence_rows = build_evidence_rows(plan_rows, association_rows)
    decisions = decision_rows(evidence_rows, objective=str(args.objective))
    evaluated = evaluated_rows(decisions, labels)
    summary = summarize(
        evidence_rows=evidence_rows,
        decisions=decisions,
        evaluated=evaluated,
        forbidden=forbidden,
        args=args,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "rival_identity_post_observation_evidence.jsonl", evidence_rows)
    write_jsonl(out_root / "rival_identity_post_observation_decisions.jsonl", decisions)
    write_jsonl(out_root / "rival_identity_post_observation_evaluated.jsonl", evaluated)
    write_json(out_root / "rival_identity_observation_validation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze rival identity post-observation evidence.")
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--primary-evaluation-labels", required=True)
    parser.add_argument("--secondary-evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--max-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument("--max-no-label-commit-rows", type=int, default=0)
    parser.add_argument("--min-new-primary-success-commit-rows", type=int, default=1)
    parser.add_argument("--min-resolved-request-rows", type=int, default=1)
    parser.add_argument("--max-secondary-stress-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument(
        "--objective",
        choices=[DEFAULT_OBJECTIVE, GOAL_VALIDITY_OBJECTIVE],
        default=DEFAULT_OBJECTIVE,
    )
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
