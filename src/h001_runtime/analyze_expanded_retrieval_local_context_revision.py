import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    ALTERNATIVE_VARIANTS,
    PROPOSED_VARIANT as PREVIOUS_PROPOSED_VARIANT,
    action_forbidden_keys,
    association_groups,
    label_index,
    load_json,
    load_jsonl,
    plan_groups,
    ratio,
    request_sort_key,
    safe_float,
    safe_int,
    select_candidate as select_previous_candidate,
    summarize_candidate,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.expanded_retrieval_local_context_revision.v1"
REVISION_VARIANT = "goal_validity_guarded_local_context_v1"
PREVIOUS_VARIANT = "previous_local_context_unique_own_view_advantage"
ALL_VARIANTS = [REVISION_VARIANT, *ALTERNATIVE_VARIANTS, PREVIOUS_VARIANT]


def source_pool_proxy_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for row in rows:
        key = (
            str(row.get("rival_identity_request_id")),
            str(row.get("episode_key")),
            str(row.get("query")),
        )
        indexed[key] = row
    return indexed


def proxy_for_request(
    proxy_rows: Dict[Tuple[str, str, str], Dict[str, Any]],
    exemplar: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    key = (
        str(exemplar.get("rival_identity_request_id")),
        str(exemplar.get("episode_key")),
        str(exemplar.get("query")),
    )
    return proxy_rows.get(key)


def source_proxy_action_payload(proxy: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if proxy is None:
        return {
            "available": False,
            "proxy_route": None,
            "proxy_reason": "missing_source_pool_proxy",
            "detector_evidence_allowed_by_proxy": False,
            "source_pool_invalid_proxy": None,
            "feature_source": None,
            "candidate_count": None,
            "positive_support_candidate_count": None,
            "positive_support_top4_count": None,
            "reachable_candidate_count": None,
            "known_reachability_count": None,
            "top_candidate_score": None,
            "top4_score_range": None,
            "score_ge_0_91_count": None,
            "semantic_top2_score_gap": None,
            "top_score_uncertainty": None,
            "consumed_forbidden_key_count": None,
        }
    decision = proxy.get("proxy_decision") or {}
    features = proxy.get("source_pool_features") or {}
    return {
        "available": True,
        "proxy_route": decision.get("proxy_route"),
        "proxy_reason": decision.get("proxy_reason"),
        "detector_evidence_allowed_by_proxy": decision.get("detector_evidence_allowed_by_proxy"),
        "source_pool_invalid_proxy": decision.get("source_pool_invalid_proxy"),
        "feature_source": features.get("feature_source"),
        "candidate_count": features.get("candidate_count"),
        "positive_support_candidate_count": features.get("positive_support_candidate_count"),
        "positive_support_top4_count": features.get("positive_support_top4_count"),
        "reachable_candidate_count": features.get("reachable_candidate_count"),
        "known_reachability_count": features.get("known_reachability_count"),
        "top_candidate_score": features.get("top_candidate_score"),
        "top4_score_range": features.get("top4_score_range"),
        "score_ge_0_91_count": features.get("score_ge_0_91_count"),
        "semantic_top2_score_gap": features.get("semantic_top2_score_gap"),
        "top_score_uncertainty": features.get("top_score_uncertainty"),
        "consumed_forbidden_key_count": features.get("consumed_forbidden_key_count"),
    }


def pool_validity_guard(proxy_payload: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    route = proxy_payload.get("proxy_route")
    positive_count = safe_int(proxy_payload.get("positive_support_candidate_count"), default=0)
    reachable_count = safe_int(proxy_payload.get("reachable_candidate_count"), default=0)
    consumed_forbidden = safe_int(proxy_payload.get("consumed_forbidden_key_count"), default=999999)
    detector_allowed = proxy_payload.get("detector_evidence_allowed_by_proxy") is True
    if not proxy_payload.get("available"):
        status = "unresolved"
        reason = "missing_source_pool_proxy"
    elif consumed_forbidden > 0:
        status = "unresolved"
        reason = "source_pool_proxy_consumed_forbidden_key"
    elif route == "request_backend_retrieval_revision_proxy":
        status = "failed"
        reason = "source_pool_proxy_requests_backend_revision"
    elif not detector_allowed:
        status = "unresolved"
        reason = "source_pool_proxy_blocks_detector_evidence"
    elif positive_count < int(args.min_source_positive_support_count):
        status = "unresolved"
        reason = "source_pool_positive_support_below_guard"
    elif reachable_count < int(args.min_source_reachable_count):
        status = "unresolved"
        reason = "source_pool_reachability_below_guard"
    else:
        status = "passed"
        reason = "source_pool_proxy_and_support_shape_passed"
    return {
        "guard_name": "pool_validity_guard_v2",
        "status": status,
        "reason": reason,
        "source_pool_proxy": proxy_payload,
    }


def support_key(row: Dict[str, Any]) -> Tuple[int, int, int, float, float, str]:
    return (
        int(row.get("strict_association_count") or 0),
        int(row.get("mask_hit_count") or 0),
        int(row.get("visible_count") or 0),
        safe_float(row.get("prior_detector_evidence_score")) or 0.0,
        safe_float(row.get("semantic_score")) or 0.0,
        str(row.get("candidate_id")),
    )


def strong_rows(request_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [row for row in request_rows if row.get("strong_own_view_evidence") is True]


def weakly_supported_rows(request_rows: Sequence[Dict[str, Any]], args: argparse.Namespace) -> List[Dict[str, Any]]:
    return [
        row
        for row in request_rows
        if int(row.get("strict_association_count") or 0) >= int(args.min_rival_strict_count)
        or int(row.get("mask_hit_count") or 0) >= int(args.min_rival_mask_count)
        or int(row.get("visible_count") or 0) >= int(args.min_rival_visible_count)
    ]


def local_only_candidate(row: Dict[str, Any]) -> bool:
    return (
        row.get("is_local_context_candidate") is True
        and row.get("is_source_top") is not True
        and row.get("is_detector_strong_candidate") is not True
        and row.get("is_detector_strong_rival") is not True
    )


def instance_arbitration_guard(request_rows: Sequence[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    strong = strong_rows(request_rows)
    weak_supported = weakly_supported_rows(request_rows, args)
    detector_strong_supported = [
        row
        for row in strong
        if row.get("is_detector_strong_candidate") is True or row.get("is_detector_strong_rival") is True
    ]
    local_only_strong = [row for row in strong if local_only_candidate(row)]
    source_top_strong = [row for row in strong if row.get("is_source_top") is True]
    selected: Optional[Dict[str, Any]] = None
    status = "unresolved"
    reason = "local_context_does_not_establish_goal_validity"

    if len(strong) == 0:
        reason = "no_strong_own_view_candidate"
    elif len(strong) > 1:
        reason = "multiple_strong_own_view_candidates"
    elif len(local_only_strong) == 1 and len(detector_strong_supported) == 0 and len(source_top_strong) == 0:
        selected = local_only_strong[0]
        status = "passed"
        reason = "unique_local_context_only_strong_candidate"
    elif len(detector_strong_supported) > 0:
        reason = "detector_strong_object_visibility_not_goal_validity"
    elif len(source_top_strong) > 0:
        reason = "source_top_visibility_not_goal_validity"

    if selected is not None:
        rival_rows = [
            row for row in weak_supported if str(row.get("candidate_id")) != str(selected.get("candidate_id"))
        ]
        if rival_rows:
            status = "unresolved"
            reason = "rival_candidate_still_supported"
            selected = None

    return {
        "guard_name": "instance_arbitration_guard_v1",
        "status": status,
        "reason": reason,
        "selected_candidate_id": None if selected is None else selected.get("candidate_id"),
        "strong_candidate_count": len(strong),
        "strong_candidate_ids": [row.get("candidate_id") for row in strong],
        "weak_supported_candidate_count": len(weak_supported),
        "detector_strong_supported_count": len(detector_strong_supported),
        "local_only_strong_count": len(local_only_strong),
        "source_top_strong_count": len(source_top_strong),
    }


def select_revision_candidate(
    request_rows: Sequence[Dict[str, Any]],
    source_proxy: Optional[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]:
    proxy_payload = source_proxy_action_payload(source_proxy)
    pool_guard = pool_validity_guard(proxy_payload, args)
    if pool_guard["status"] == "failed":
        return None, "request_backend_retrieval_revision", {
            "variant": REVISION_VARIANT,
            "pool_validity_guard": pool_guard,
            "instance_arbitration_guard": None,
        }
    if pool_guard["status"] != "passed":
        return None, "defer_pool_validity_unresolved", {
            "variant": REVISION_VARIANT,
            "pool_validity_guard": pool_guard,
            "instance_arbitration_guard": None,
        }

    instance_guard = instance_arbitration_guard(request_rows, args)
    selected = None
    if instance_guard["status"] == "passed":
        selected_id = str(instance_guard.get("selected_candidate_id"))
        selected = next((row for row in request_rows if str(row.get("candidate_id")) == selected_id), None)
        if selected is not None:
            return selected, "commit_goal_validity_confirmed_candidate", {
                "variant": REVISION_VARIANT,
                "pool_validity_guard": pool_guard,
                "instance_arbitration_guard": instance_guard,
            }
    if instance_guard["reason"] in {
        "detector_strong_object_visibility_not_goal_validity",
        "source_top_visibility_not_goal_validity",
        "no_strong_own_view_candidate",
    }:
        action = "request_goal_validity_confirmation"
    else:
        action = "defer_instance_arbitration_unresolved"
    return None, action, {
        "variant": REVISION_VARIANT,
        "pool_validity_guard": pool_guard,
        "instance_arbitration_guard": instance_guard,
    }


def select_variant_candidate(
    request_rows: Sequence[Dict[str, Any]],
    variant: str,
    source_proxy: Optional[Dict[str, Any]],
    args: argparse.Namespace,
) -> Tuple[Optional[Dict[str, Any]], str, Dict[str, Any]]:
    if variant == REVISION_VARIANT:
        return select_revision_candidate(request_rows, source_proxy, args)
    base_variant = PREVIOUS_PROPOSED_VARIANT if variant == PREVIOUS_VARIANT else variant
    selected, reason, guard = select_previous_candidate(request_rows, base_variant)
    guard = dict(guard)
    guard["variant"] = variant
    if variant == PREVIOUS_VARIANT:
        guard["previous_variant"] = PREVIOUS_PROPOSED_VARIANT
    return selected, reason, guard


def decision_rows(
    evidence_rows: Sequence[Dict[str, Any]],
    proxy_rows: Dict[Tuple[str, str, str], Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[str(row.get("expanded_retrieval_request_id"))].append(row)
    decisions: List[Dict[str, Any]] = []
    for request_id in sorted(grouped, key=request_sort_key):
        rows = grouped[request_id]
        exemplar = rows[0]
        source_proxy = proxy_for_request(proxy_rows, exemplar)
        strong_count = sum(row.get("strong_own_view_evidence") is True for row in rows)
        for variant in ALL_VARIANTS:
            selected, reason, guard = select_variant_candidate(rows, variant, source_proxy, args)
            terminal_commit = selected is not None and (
                variant != REVISION_VARIANT or reason == "commit_goal_validity_confirmed_candidate"
            )
            action = reason if variant == REVISION_VARIANT else ("commit_candidate" if terminal_commit else "defer")
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
                    "terminal_commit": terminal_commit,
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
        commit = row.get("terminal_commit") is True
        label = labels.get((str(row.get("episode_key")), str(selected_id))) if commit and selected_id else None
        selected_correct = None if label is None else bool(label.get("evaluation_only_candidate_correct"))
        request_correct_count = request_correct_counts.get(str(row.get("expanded_retrieval_request_id")), 0)
        out = {
            **row,
            "validation_stage": "evaluation_joined_after_action",
            "evaluation_only_request_correct_candidate_count": request_correct_count,
            "evaluation_only_selected_has_label": bool(label) if commit else None,
            "evaluation_only_selected_correct": selected_correct if commit else None,
            "evaluation_only_selected_wrong_goal_visit": None
            if label is None
            else bool(label.get("evaluation_only_wrong_goal_visit")),
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
            taxonomy = "wrong_instance_commit"
        elif out["evaluation_only_success_commit"]:
            taxonomy = "success"
        else:
            taxonomy = str(row.get("reason"))
        out["failure_taxonomy_type"] = taxonomy
        evaluated.append(out)
    return evaluated


def summarize_variant(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    request_rows = len(rows)
    commit_rows = [row for row in rows if row.get("terminal_commit") is True]
    success_rows = [row for row in commit_rows if row.get("evaluation_only_success_commit") is True]
    unsafe_rows = [row for row in commit_rows if row.get("evaluation_only_wrong_goal_commit") is True]
    no_valid_rows = [row for row in commit_rows if row.get("evaluation_only_no_valid_commit") is True]
    no_label_rows = [row for row in commit_rows if row.get("evaluation_only_no_label_commit") is True]
    return {
        "request_rows": request_rows,
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(unsafe_rows),
        "no_valid_commit_rows": len(no_valid_rows),
        "no_label_commit_rows": len(no_label_rows),
        "commit_rate": ratio(len(commit_rows), request_rows),
        "success_commit_rate": ratio(len(success_rows), request_rows),
        "wrong_goal_commit_rate": ratio(len(unsafe_rows), request_rows),
        "action_counts": dict(sorted(Counter(str(row.get("action")) for row in rows).items())),
        "reason_counts": dict(sorted(Counter(str(row.get("reason")) for row in rows).items())),
        "failure_taxonomy_counts": dict(
            sorted(Counter(str(row.get("failure_taxonomy_type")) for row in rows).items())
        ),
    }


def revision_route_counts(decisions: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    revision = [row for row in decisions if row.get("variant") == REVISION_VARIANT]
    pool_status = Counter()
    pool_reasons = Counter()
    instance_status = Counter()
    instance_reasons = Counter()
    for row in revision:
        guard = row.get("decision_guard") or {}
        pool = guard.get("pool_validity_guard") or {}
        instance = guard.get("instance_arbitration_guard") or {}
        pool_status.update([str(pool.get("status"))])
        pool_reasons.update([str(pool.get("reason"))])
        if instance:
            instance_status.update([str(instance.get("status"))])
            instance_reasons.update([str(instance.get("reason"))])
    return {
        "pool_validity_status_counts": dict(sorted(pool_status.items())),
        "pool_validity_reason_counts": dict(sorted(pool_reasons.items())),
        "instance_arbitration_status_counts": dict(sorted(instance_status.items())),
        "instance_arbitration_reason_counts": dict(sorted(instance_reasons.items())),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.plan))
    association_rows = load_jsonl(Path(args.detector_associations))
    detector_summary = load_json(Path(args.detector_summary))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))
    proxy_rows = source_pool_proxy_index(load_jsonl(Path(args.source_pool_proxy_rows)))
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
            row = summarize_candidate(
                plan_row,
                associations_by_candidate.get((request_id, str(plan_row.get("candidate_id"))), []),
                args,
            )
            row["schema_version"] = SCHEMA_VERSION
            evidence_rows.append(row)
        request_correct_counts[request_id] = correct_count

    decisions = decision_rows(evidence_rows, proxy_rows, args)
    evaluated = evaluated_rows(decisions, labels, request_correct_counts)
    variant_summaries = {
        variant: summarize_variant([row for row in evaluated if row.get("variant") == variant])
        for variant in ALL_VARIANTS
    }
    revision_rows = [row for row in evaluated if row.get("variant") == REVISION_VARIANT]
    revision_summary = variant_summaries[REVISION_VARIANT]
    request_rows = len(plan_by_request)
    strong_request_rows = len(
        {
            str(row.get("expanded_retrieval_request_id"))
            for row in evidence_rows
            if row.get("strong_own_view_evidence") is True
        }
    )
    forbidden = action_forbidden_keys(evidence_rows + decisions)
    detector_box_rate = safe_float(detector_summary.get("rows_with_detector_box_rate"))
    sam2_mask_rate = safe_float(detector_summary.get("rows_with_sam2_mask_rate"))
    candidate_association_rate = safe_float(detector_summary.get("rows_with_candidate_association_rate"))
    route_counts = revision_route_counts(decisions)
    safe_nonzero = (
        int(revision_summary["wrong_goal_commit_rows"]) <= int(args.max_wrong_goal_commit_rows)
        and int(revision_summary["no_valid_commit_rows"]) <= int(args.max_no_valid_commit_rows)
        and int(revision_summary["no_label_commit_rows"]) <= int(args.max_no_label_commit_rows)
        and int(revision_summary["success_commit_rows"]) >= int(args.min_success_commit_rows)
    )
    gate = {
        "detector_box_rate_pass": (detector_box_rate or 0.0) >= float(args.min_detector_box_rate),
        "sam2_mask_rate_pass": (sam2_mask_rate or 0.0) >= float(args.min_sam2_mask_rate),
        "candidate_association_rate_pass": (candidate_association_rate or 0.0)
        >= float(args.min_candidate_association_rate),
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "wrong_goal_commit_rows_pass": int(revision_summary["wrong_goal_commit_rows"])
        <= int(args.max_wrong_goal_commit_rows),
        "no_valid_commit_rows_pass": int(revision_summary["no_valid_commit_rows"])
        <= int(args.max_no_valid_commit_rows),
        "no_label_commit_rows_pass": int(revision_summary["no_label_commit_rows"])
        <= int(args.max_no_label_commit_rows),
        "success_commit_rows_pass": int(revision_summary["success_commit_rows"])
        >= int(args.min_success_commit_rows),
        "safe_nonzero_utility_passed": safe_nonzero,
    }
    gate["revision_substrate_gate_passed"] = (
        gate["detector_box_rate_pass"]
        and gate["sam2_mask_rate_pass"]
        and gate["candidate_association_rate_pass"]
        and gate["action_evidence_forbidden_key_gate_passed"]
    )
    gate["revision_utility_gate_passed"] = all(gate.values())
    gate["paper_claim_allowed"] = False
    summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "plan": str(args.plan),
        "detector_associations": str(args.detector_associations),
        "detector_summary": str(args.detector_summary),
        "source_pool_proxy_rows": str(args.source_pool_proxy_rows),
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
        "strong_own_view_request_rows": strong_request_rows,
        "request_correct_candidate_count_distribution": dict(
            sorted(Counter(str(value) for value in request_correct_counts.values()).items())
        ),
        "thresholds": {
            "min_own_strict_count": int(args.min_own_strict_count),
            "min_own_mask_count": int(args.min_own_mask_count),
            "min_own_visible_count": int(args.min_own_visible_count),
            "min_rival_strict_count": int(args.min_rival_strict_count),
            "min_rival_mask_count": int(args.min_rival_mask_count),
            "min_rival_visible_count": int(args.min_rival_visible_count),
            "min_source_positive_support_count": int(args.min_source_positive_support_count),
            "min_source_reachable_count": int(args.min_source_reachable_count),
            "min_success_commit_rows": int(args.min_success_commit_rows),
            "max_wrong_goal_commit_rows": int(args.max_wrong_goal_commit_rows),
            "max_no_valid_commit_rows": int(args.max_no_valid_commit_rows),
            "max_no_label_commit_rows": int(args.max_no_label_commit_rows),
        },
        "variant_summaries": variant_summaries,
        "simpler_alternative_table": [
            {"variant": variant, **variant_summaries[variant]} for variant in ALL_VARIANTS
        ],
        "revision_route_counts": route_counts,
        "gate": gate,
        "failure_taxonomy_counts": dict(
            sorted(Counter(str(row.get("failure_taxonomy_type")) for row in revision_rows).items())
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "interpretation": {
            "fact": (
                "The revised analyzer writes action-time decisions before joining labels, and separates "
                "pool-validity routing from instance arbitration."
            ),
            "agent_inference": (
                "A safe-but-inert result should block paper utility claims but still supports the failure "
                "mechanism that own-view category evidence is not ObjectNav goal validity evidence."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "evidence_rows": "expanded_retrieval_local_context_revision_evidence_rows.jsonl",
            "decision_rows": "expanded_retrieval_local_context_revision_decision_rows.jsonl",
            "evaluated_rows": "expanded_retrieval_local_context_revision_evaluated_rows.jsonl",
            "alternative_rows": "expanded_retrieval_local_context_revision_alternative_rows.jsonl",
            "summary": "expanded_retrieval_local_context_revision_summary.json",
        },
    }
    write_jsonl(out_root / "expanded_retrieval_local_context_revision_evidence_rows.jsonl", evidence_rows)
    write_jsonl(out_root / "expanded_retrieval_local_context_revision_decision_rows.jsonl", decisions)
    write_jsonl(out_root / "expanded_retrieval_local_context_revision_evaluated_rows.jsonl", evaluated)
    write_jsonl(
        out_root / "expanded_retrieval_local_context_revision_alternative_rows.jsonl",
        [row for row in evaluated if row.get("variant") != REVISION_VARIANT],
    )
    write_json(out_root / "expanded_retrieval_local_context_revision_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze revised expanded-retrieval local-context objective.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--detector-summary", required=True)
    parser.add_argument("--source-pool-proxy-rows", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-own-strict-count", type=int, default=3)
    parser.add_argument("--min-own-mask-count", type=int, default=4)
    parser.add_argument("--min-own-visible-count", type=int, default=5)
    parser.add_argument("--min-rival-strict-count", type=int, default=1)
    parser.add_argument("--min-rival-mask-count", type=int, default=2)
    parser.add_argument("--min-rival-visible-count", type=int, default=3)
    parser.add_argument("--min-source-positive-support-count", type=int, default=1)
    parser.add_argument("--min-source-reachable-count", type=int, default=1)
    parser.add_argument("--min-detector-box-rate", type=float, default=0.80)
    parser.add_argument("--min-sam2-mask-rate", type=float, default=0.80)
    parser.add_argument("--min-candidate-association-rate", type=float, default=0.40)
    parser.add_argument("--min-success-commit-rows", type=int, default=2)
    parser.add_argument("--max-wrong-goal-commit-rows", type=int, default=0)
    parser.add_argument("--max-no-valid-commit-rows", type=int, default=0)
    parser.add_argument("--max-no-label-commit-rows", type=int, default=0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["revision_substrate_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
