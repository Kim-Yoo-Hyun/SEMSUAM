import argparse
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.rival_identity_broader_manifest.v1"
CONTRACT_NAME = "rival_identity_broader_validation_v1"
POLICY_NAME = "semantic_uncertainty_request_split_v1"
DEFAULT_DATE_FROZEN = "2026-05-26"


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


def canonical_manifest_path(path_text: str) -> str:
    if path_text.startswith("/runs/"):
        return "local_dataset/runs/" + path_text[len("/runs/") :]
    if path_text.startswith("/workspace/"):
        return path_text[len("/workspace/") :]
    return path_text


def count_unique(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return len({str(row.get(key)) for row in rows if row.get(key) is not None})


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def contains_gt_action_flag(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) == "uses_gt_for_action" and child is True:
                return True
            if contains_gt_action_flag(child):
                return True
    if isinstance(value, list):
        return any(contains_gt_action_flag(item) for item in value)
    return False


def group_candidate_decisions(path: Path, episode_keys: Sequence[str]) -> Dict[str, List[Dict[str, Any]]]:
    wanted = set(str(key) for key in episode_keys)
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(path):
        if str(row.get("episode_key")) not in wanted:
            continue
        if row.get("policy") != "NoReobserve":
            continue
        if row.get("candidate_uses_gt_for_action") is True:
            continue
        grouped[str(row["episode_key"])].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: safe_int(item.get("candidate_rank")))
    return grouped


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def top2_gap(rows: Sequence[Dict[str, Any]]) -> Optional[float]:
    if len(rows) < 2:
        return None
    top = safe_float(rows[0].get("candidate_score"))
    second = safe_float(rows[1].get("candidate_score"))
    if top is None or second is None:
        return None
    return top - second


def candidate_position(row: Dict[str, Any]) -> Optional[List[float]]:
    value = row.get("candidate_position")
    if not isinstance(value, list) or len(value) < 3:
        return None
    output: List[float] = []
    for item in value[:3]:
        number = safe_float(item)
        if number is None:
            return None
        output.append(float(number))
    return output


def candidate_evidence_row(
    row: Dict[str, Any],
    *,
    top_score: float,
    positive_score_gap: float,
    max_positive_rank: int,
) -> Dict[str, Any]:
    score = safe_float(row.get("candidate_score")) or 0.0
    rank = safe_int(row.get("candidate_rank"))
    position = candidate_position(row)
    positive_support = bool(rank <= max_positive_rank and (top_score - score) <= positive_score_gap)
    return {
        "candidate_id": row.get("candidate_id"),
        "category": row.get("query"),
        "semantic_rank": rank,
        "semantic_score": score,
        "support_score": score,
        "detector_score_max": None,
        "associated_heading_count": 0,
        "box_hit_count": 0,
        "mask_hit_count": 0,
        "visible_count": 0,
        "min_depth_error_m": None,
        "positive_support": positive_support,
        "position": position,
        "visit_position": position,
        "candidate_backend": row.get("candidate_backend"),
        "path_to_candidate": row.get("path_to_candidate"),
        "candidate_reachable": row.get("candidate_reachable"),
        "uses_gt_for_action": False,
    }


def evaluation_label_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "episode_key": row.get("episode_key"),
        "candidate_id": row.get("candidate_id"),
        "evaluation_only_candidate_correct": row.get("candidate_correct"),
        "evaluation_only_correct_source": row.get("candidate_correct_source"),
        "evaluation_only_wrong_goal_visit": row.get("wrong_goal_visit"),
        "evaluation_only_goal_visit": row.get("goal_visit"),
        "evaluation_only_wasted_path_from_candidate": row.get("wasted_path_from_candidate"),
        "evaluation_only_candidate_score": row.get("candidate_score"),
        "evaluation_only_candidate_rank": row.get("candidate_rank"),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def build_action_record(
    parent: Dict[str, Any],
    rows: Sequence[Dict[str, Any]],
    *,
    max_candidates: int,
    positive_score_gap: float,
    max_positive_rank: int,
    contract_name: str,
    policy_name: str,
) -> Dict[str, Any]:
    top = rows[0]
    top_score = safe_float(top.get("candidate_score")) or 0.0
    candidates = [
        candidate_evidence_row(
            row,
            top_score=top_score,
            positive_score_gap=positive_score_gap,
            max_positive_rank=max_positive_rank,
        )
        for row in rows[:max_candidates]
    ]
    positive_count = sum(candidate.get("positive_support") is True for candidate in candidates)
    return {
        "schema_version": SCHEMA_VERSION,
        "action_path_fields_exclude_evaluation_labels": True,
        "contract_name": contract_name,
        "policy_name": policy_name,
        "episode_key": parent.get("episode_key"),
        "scene_key": parent.get("scene_key"),
        "scene_id": parent.get("scene_id"),
        "query": parent.get("query"),
        "source_name": parent.get("source_name"),
        "source_candidate_decisions": parent.get("source_candidate_decisions"),
        "source_manifest_split": top.get("manifest_selected_split"),
        "selection_rank": parent.get("selection_rank"),
        "parent_episode_class_for_analysis": parent.get("episode_class"),
        "evidence_status": "semantic_candidate_proxy",
        "candidate_count": len(candidates),
        "has_any_positive_support": positive_count > 0,
        "positive_support_candidate_count": positive_count,
        "semantic_top_candidate_id": top.get("candidate_id"),
        "semantic_top2_score_gap": top2_gap(rows),
        "top_candidate_score": top_score,
        "top_score_uncertainty": top.get("score_uncertainty"),
        "top_margin_uncertainty": top.get("margin_uncertainty"),
        "top_U_sem": top.get("U_sem"),
        "top_trigger_reobserve": top.get("trigger_reobserve"),
        "candidate_evidence": candidates,
        "uses_gt_for_action": False,
    }


def request_priority(row: Dict[str, Any]) -> Tuple[int, float, float, float, int, str]:
    route = str(row.get("request_taxonomy_route"))
    route_priority = 0 if route == "rival_identity_arbitration" else 1
    gap = safe_float(row.get("semantic_top2_score_gap"))
    score_uncertainty = safe_float(row.get("top_score_uncertainty")) or 0.0
    u_sem = safe_float(row.get("top_U_sem")) or 0.0
    rank = safe_int(row.get("selection_rank"))
    return (
        route_priority,
        float("inf") if gap is None else gap,
        -score_uncertainty,
        -u_sem,
        rank,
        str(row.get("episode_key")),
    )


def object_priority(row: Dict[str, Any]) -> Tuple[float, float, float, int, str]:
    score_uncertainty = safe_float(row.get("top_score_uncertainty")) or 0.0
    u_sem = safe_float(row.get("top_U_sem")) or 0.0
    gap = safe_float(row.get("semantic_top2_score_gap")) or 0.0
    rank = safe_int(row.get("selection_rank"))
    return (-score_uncertainty, -u_sem, -gap, rank, str(row.get("episode_key")))


def add_rows(
    *,
    selected: List[Dict[str, Any]],
    pool: Sequence[Dict[str, Any]],
    target_total: int,
    selected_keys: set[str],
    scene_counts: Counter[str],
    query_counts: Counter[str],
    max_rows_per_scene: int,
    max_rows_per_query: int,
    enforce_caps: bool,
) -> None:
    for row in pool:
        if len(selected) >= target_total:
            break
        key = str(row.get("episode_key"))
        scene = str(row.get("scene_key"))
        query = str(row.get("query"))
        if key in selected_keys:
            continue
        if enforce_caps and scene_counts[scene] >= max_rows_per_scene:
            continue
        if enforce_caps and query_counts[query] >= max_rows_per_query:
            continue
        selected.append(row)
        selected_keys.add(key)
        scene_counts[scene] += 1
        query_counts[query] += 1


def select_request_rows(
    action_rows: Sequence[Dict[str, Any]],
    *,
    target_request_rows: int,
    min_object_existence_rows: int,
    min_rival_identity_rows: int,
    max_rows_per_scene: int,
    max_rows_per_query: int,
) -> List[Dict[str, Any]]:
    eligible = [row for row in action_rows if row.get("top_trigger_reobserve") is True]
    for row in eligible:
        route = "rival_identity_arbitration"
        if safe_int(row.get("positive_support_candidate_count"), 0) <= 1:
            route = "object_existence_validation"
        row["request_taxonomy_route"] = route

    rival_pool = sorted(
        [row for row in eligible if row.get("request_taxonomy_route") == "rival_identity_arbitration"],
        key=request_priority,
    )
    object_pool = sorted(
        [row for row in eligible if row.get("request_taxonomy_route") == "object_existence_validation"],
        key=object_priority,
    )
    all_pool = sorted(eligible, key=request_priority)

    selected: List[Dict[str, Any]] = []
    selected_keys: set[str] = set()
    scene_counts: Counter[str] = Counter()
    query_counts: Counter[str] = Counter()
    add_rows(
        selected=selected,
        pool=object_pool,
        target_total=min(min_object_existence_rows, target_request_rows),
        selected_keys=selected_keys,
        scene_counts=scene_counts,
        query_counts=query_counts,
        max_rows_per_scene=max_rows_per_scene,
        max_rows_per_query=max_rows_per_query,
        enforce_caps=True,
    )
    add_rows(
        selected=selected,
        pool=rival_pool,
        target_total=min(max(min_rival_identity_rows, len(selected)), target_request_rows),
        selected_keys=selected_keys,
        scene_counts=scene_counts,
        query_counts=query_counts,
        max_rows_per_scene=max_rows_per_scene,
        max_rows_per_query=max_rows_per_query,
        enforce_caps=True,
    )
    add_rows(
        selected=selected,
        pool=all_pool,
        target_total=target_request_rows,
        selected_keys=selected_keys,
        scene_counts=scene_counts,
        query_counts=query_counts,
        max_rows_per_scene=max_rows_per_scene,
        max_rows_per_query=max_rows_per_query,
        enforce_caps=True,
    )
    if len(selected) < target_request_rows:
        add_rows(
            selected=selected,
            pool=all_pool,
            target_total=target_request_rows,
            selected_keys=selected_keys,
            scene_counts=scene_counts,
            query_counts=query_counts,
            max_rows_per_scene=max_rows_per_scene,
            max_rows_per_query=max_rows_per_query,
            enforce_caps=False,
        )

    selected.sort(key=lambda row: safe_int(row.get("selection_rank")))
    for index, row in enumerate(selected):
        row["request_selection_rank"] = index
    return selected


def decision_from_action_row(row: Dict[str, Any]) -> Dict[str, Any]:
    candidates = list(row.get("candidate_evidence") or [])
    positives = [candidate for candidate in candidates if candidate.get("positive_support") is True]
    focus = candidates[0] if candidates else None
    if focus is None:
        return {
            "action": "defer_or_expand_retrieval",
            "reason": "no_actionable_candidate",
            "selected_candidate_id": None,
            "rival_candidate_ids": [],
            "uses_gt_for_action": False,
        }
    rivals = [candidate for candidate in positives if str(candidate.get("candidate_id")) != str(focus.get("candidate_id"))]
    route = str(row.get("request_taxonomy_route"))
    reason = "request_semantic_rival_identity_confirmation"
    if route == "object_existence_validation":
        reason = "request_object_existence_independent_confirmation"
    return {
        "action": "request_rival_identity_confirmation",
        "reason": reason,
        "selected_candidate_id": str(focus.get("candidate_id")),
        "rival_candidate_ids": [str(candidate.get("candidate_id")) for candidate in rivals[:5]],
        "request_taxonomy_route": route,
        "uses_gt_for_action": False,
    }


def request_row_from_decision(action_row: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "role": "primary",
        "episode_key": str(action_row.get("episode_key")),
        "scene_key": str(action_row.get("scene_key")),
        "query": str(action_row.get("query")),
        "request_reason": str(decision.get("reason")),
        "request_taxonomy_route": decision.get("request_taxonomy_route"),
        "focus_candidate_id": decision.get("selected_candidate_id"),
        "rival_candidate_ids": [str(candidate_id) for candidate_id in decision.get("rival_candidate_ids") or []],
    }


def policy_row(
    action_row: Dict[str, Any],
    decision: Dict[str, Any],
    selected: bool,
    *,
    contract_name: str,
    policy_name: str,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_name": contract_name,
        "policy_name": policy_name,
        "role": "primary",
        "episode_key": action_row.get("episode_key"),
        "scene_key": action_row.get("scene_key"),
        "scene_id": action_row.get("scene_id"),
        "query": action_row.get("query"),
        "source_manifest_split": action_row.get("source_manifest_split"),
        "evidence_status": action_row.get("evidence_status"),
        "candidate_count": action_row.get("candidate_count"),
        "positive_support_candidate_count": action_row.get("positive_support_candidate_count"),
        "semantic_top2_score_gap": action_row.get("semantic_top2_score_gap"),
        "request_taxonomy_route": action_row.get("request_taxonomy_route"),
        "selected_by_broader_miner": selected,
        "action": decision.get("action") if selected else "not_selected_by_broader_budget",
        "reason": decision.get("reason") if selected else "outside_action_time_uncertainty_budget",
        "selected_candidate_id": decision.get("selected_candidate_id") if selected else None,
        "rival_candidate_ids": list(decision.get("rival_candidate_ids") or []) if selected else [],
        "uses_gt_for_action": False,
    }


def source_freeze_gate(
    *,
    request_rows: Sequence[Dict[str, Any]],
    action_rows: Sequence[Dict[str, Any]],
    forbidden: Sequence[str],
    excluded_scenes: Sequence[str],
    min_request_rows: int,
    min_scenes: int,
    min_queries: int,
    min_object_existence_rows: int,
    min_rival_identity_rows: int,
    parent_design_gate_passed: bool,
) -> Dict[str, Any]:
    scene_counts = Counter(str(row.get("scene_key")) for row in request_rows)
    query_counts = Counter(str(row.get("query")) for row in request_rows)
    route_counts = Counter(str(row.get("request_taxonomy_route")) for row in request_rows)
    overlap = sorted(scene for scene in scene_counts if scene in set(excluded_scenes))
    gt_action_rows = [str(row.get("episode_key")) for row in action_rows if contains_gt_action_flag(row)]
    checks = {
        "parent_design_gate_passed": bool(parent_design_gate_passed),
        "minimum_request_rows": len(request_rows) >= min_request_rows,
        "minimum_request_scenes": len(scene_counts) >= min_scenes,
        "minimum_request_queries": len(query_counts) >= min_queries,
        "minimum_object_existence_rows": route_counts.get("object_existence_validation", 0) >= min_object_existence_rows,
        "minimum_rival_identity_rows": route_counts.get("rival_identity_arbitration", 0) >= min_rival_identity_rows,
        "excluded_scene_overlap": len(overlap) == 0,
        "action_evidence_forbidden_key_count": len(forbidden) == 0,
        "no_gt_for_action": len(gt_action_rows) == 0,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "required": {
            "minimum_request_rows": min_request_rows,
            "minimum_request_scenes": min_scenes,
            "minimum_request_queries": min_queries,
            "minimum_object_existence_rows": min_object_existence_rows,
            "minimum_rival_identity_rows": min_rival_identity_rows,
            "excluded_scene_overlap": 0,
            "action_evidence_forbidden_key_count": 0,
            "uses_gt_for_action": False,
        },
        "request_rows": len(request_rows),
        "request_scenes": len(scene_counts),
        "request_queries": len(query_counts),
        "request_taxonomy_route_counts": dict(sorted(route_counts.items())),
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "excluded_scene_overlap": overlap,
        "action_evidence_forbidden_key_count": len(forbidden),
        "gt_action_rows": gt_action_rows[:20],
    }


def verify_contract(contract: Dict[str, Any]) -> Dict[str, Any]:
    request_rows = list(contract.get("request_rows") or [])
    episode_keys = [str(row.get("episode_key")) for row in request_rows]
    duplicate_episode_keys = sorted(key for key, count in Counter(episode_keys).items() if count > 1)
    gate = dict(contract.get("source_freeze_gate") or {})
    ok = (
        contract.get("manifest_status") == "frozen"
        and bool(gate.get("passed"))
        and not duplicate_episode_keys
        and contract.get("uses_gt_for_action") is False
    )
    return {
        "ok": ok,
        "contract_name": contract.get("contract_name"),
        "manifest_status": contract.get("manifest_status"),
        "request_rows": len(request_rows),
        "request_scenes": count_unique(request_rows, "scene_key"),
        "request_queries": count_unique(request_rows, "query"),
        "request_taxonomy_route_counts": dict(
            sorted(Counter(str(row.get("request_taxonomy_route")) for row in request_rows).items())
        ),
        "duplicate_episode_keys": duplicate_episode_keys,
        "source_freeze_gate": gate,
        "uses_gt_for_action": contract.get("uses_gt_for_action"),
        "paper_claim_allowed": False,
    }


def build_contract(
    *,
    args: argparse.Namespace,
    request_rows: Sequence[Dict[str, Any]],
    source_summary: Dict[str, Any],
) -> Dict[str, Any]:
    action_path = canonical_manifest_path(str(Path(args.out_root) / f"{args.output_prefix}_action_evidence_rows.jsonl"))
    labels_path = canonical_manifest_path(str(Path(args.out_root) / f"{args.output_prefix}_evaluation_labels.jsonl"))
    return {
        "schema_version": SCHEMA_VERSION,
        "date_frozen": str(args.date_frozen),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_name": args.contract_name,
        "manifest_status": "frozen" if source_summary["source_freeze_gate"]["passed"] else "draft_failed_source_freeze_gate",
        "policy_source": {
            "policy_name": args.policy_name,
            "policy_description": (
                "Mine a larger predeclared rival-identity/object-existence validation source from frozen "
                "semantic candidate decisions. Request selection uses action-time score uncertainty, semantic "
                "top-gap, trigger flags, and deterministic scene/query caps. Evaluation labels are written "
                "only after request rows are frozen."
            ),
            "design_source": canonical_manifest_path(str(args.design_summary)),
            "parent_rows": canonical_manifest_path(str(args.parent_rows)),
            "source_candidate_decisions": canonical_manifest_path(str(args.candidate_decisions)),
            "selection_rule": (
                "Use the frozen parent rows, convert candidate decisions to action-time candidate evidence, "
                "select request rows by semantic uncertainty budget, and never use candidate_correct or "
                "wrong_goal labels for the request action."
            ),
            "diagnostic_result": {
                "source_freeze_gate_passed": source_summary["source_freeze_gate"]["passed"],
                "request_rows": source_summary["request_rows"],
                "request_scenes": source_summary["request_scenes"],
                "request_queries": source_summary["request_queries"],
                "request_taxonomy_route_counts": source_summary["request_taxonomy_route_counts"],
                "action_evidence_forbidden_key_count": source_summary["action_evidence_forbidden_key_count"],
                "uses_gt_for_action": False,
            },
        },
        "request_rows": list(request_rows),
        "source_evidence": {
            "primary_action_evidence": action_path,
            "primary_evaluation_labels": labels_path,
            "secondary_action_evidence": action_path,
            "secondary_evaluation_labels": labels_path,
        },
        "observation_contract": {
            "planner_name": "rival_identity_pair_probe_v1",
            "purpose": (
                "Validate whether semantic uncertainty can be converted into active observation utility on a "
                "larger scene-disjoint ObjectNav source."
            ),
            "allowed_action_time_inputs": [
                "candidate_id",
                "query",
                "scene_key",
                "episode_key",
                "candidate position",
                "semantic_rank",
                "semantic_score",
                "candidate_score",
                "top2 score gap",
                "uncertainty scores",
                "trigger_reobserve",
            ],
            "forbidden_action_time_inputs": [
                "evaluation_only_candidate_correct",
                "evaluation_only_recall_rank",
                "GT object position",
                "GT geodesic distance",
                "success label",
                "wrong-goal label",
            ],
            "target_selection": {
                "always_include_focus_candidate": True,
                "include_guard_eligible_rivals_first": True,
                "include_semantic_or_support_rivals_for_unique_guard_candidate": False,
                "max_rivals_per_request": 4,
                "max_target_candidates_per_request": 5,
                "deduplicate_candidate_ids": True,
            },
            "viewpoint_policy": {
                "minimum": "Use non-GT candidate positions as the initial pair-probe view target source.",
                "fallback": "If later frame smoke shows navigation invalidity, add a separate viewpoint repair workflow.",
                "gt_usage_allowed": False,
            },
            "expected_outputs": [
                "rival_identity_observation_plan.jsonl",
                "rival_identity_frame_summary.jsonl",
                "rival_identity_detector_associations.jsonl",
                "rival_identity_post_observation_evidence.jsonl",
                "rival_identity_observation_validation_summary.json",
            ],
        },
        "evaluation_contract": {
            "scope": args.evaluation_scope,
            "minimum_plan_gate": {
                "request_rows": len(request_rows),
                "primary_request_rows": len(request_rows),
                "secondary_stress_request_rows": 0,
                "planned_rows_minimum": len(request_rows),
                "action_evidence_forbidden_key_count": 0,
            },
            "source_freeze_gate": source_summary["source_freeze_gate"],
            "post_observation_gate": {
                "wrong_goal_commit_rows": 0,
                "no_label_commit_rows": 0,
                "rival_identity_arbitration_rows_reported": True,
                "object_existence_validation_rows_reported": True,
            },
            "metrics": [
                "wrong_goal_commit_rows",
                "success_commit_rows",
                "request_identity_confirmation_rows",
                "defer_object_existence_validation_rows",
                "wrong_goal_avoided_by_defer",
                "success_lost_by_defer",
            ],
        },
        "source_freeze_gate": source_summary["source_freeze_gate"],
        "interpretation": {
            "fact": "This contract freezes request rows before frame rendering, detector association, and evaluation joins.",
            "agent_inference": (
                "Passing the source-freeze gate only establishes a broader validation substrate. A paper-facing "
                "utility claim remains blocked until detector-backed post-observation validation passes."
            ),
            "paper_claim_status": "not_allowed_until_broader_detector_backed_validation_passes",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    design_summary = load_json(Path(args.design_summary))
    parent_rows = load_jsonl(Path(args.parent_rows))
    episode_keys = [str(row.get("episode_key")) for row in parent_rows]
    grouped = group_candidate_decisions(Path(args.candidate_decisions), episode_keys)

    missing_episode_keys = sorted(key for key in episode_keys if key not in grouped)
    action_rows: List[Dict[str, Any]] = []
    label_rows: List[Dict[str, Any]] = []
    for parent in parent_rows:
        rows = grouped.get(str(parent.get("episode_key"))) or []
        if not rows:
            continue
        action_rows.append(
            build_action_record(
                parent,
                rows,
                max_candidates=args.max_candidates_per_episode,
                positive_score_gap=args.positive_score_gap,
                max_positive_rank=args.max_positive_rank,
                contract_name=args.contract_name,
                policy_name=args.policy_name,
            )
        )
        label_rows.extend(evaluation_label_row(row) for row in rows[: args.max_candidates_per_episode])

    selected_actions = select_request_rows(
        action_rows,
        target_request_rows=args.target_request_rows,
        min_object_existence_rows=args.min_object_existence_rows,
        min_rival_identity_rows=args.min_rival_identity_rows,
        max_rows_per_scene=args.max_rows_per_scene,
        max_rows_per_query=args.max_rows_per_query,
    )
    selected_keys = {str(row.get("episode_key")) for row in selected_actions}
    decisions = {str(row.get("episode_key")): decision_from_action_row(row) for row in selected_actions}
    request_rows = [
        request_row_from_decision(row, decisions[str(row.get("episode_key"))])
        for row in selected_actions
    ]
    all_policy_rows = [
        policy_row(
            row,
            decisions.get(str(row.get("episode_key"))) or decision_from_action_row(row),
            str(row.get("episode_key")) in selected_keys,
            contract_name=args.contract_name,
            policy_name=args.policy_name,
        )
        for row in action_rows
    ]
    selected_source_rows = [row for row in all_policy_rows if row.get("selected_by_broader_miner") is True]

    forbidden = action_forbidden_keys(action_rows)
    parent_design_gate_passed = bool((design_summary.get("gates") or {}).get("design_gate_passed"))
    gate = source_freeze_gate(
        request_rows=request_rows,
        action_rows=action_rows,
        forbidden=forbidden,
        excluded_scenes=list(design_summary.get("excluded_scenes") or []),
        min_request_rows=args.min_request_rows,
        min_scenes=args.min_scenes,
        min_queries=args.min_queries,
        min_object_existence_rows=args.min_object_existence_rows,
        min_rival_identity_rows=args.min_rival_identity_rows,
        parent_design_gate_passed=parent_design_gate_passed,
    )

    route_counts = Counter(str(row.get("request_taxonomy_route")) for row in request_rows)
    source_summary = {
        "schema_version": SCHEMA_VERSION,
        "contract_name": args.contract_name,
        "out_root": str(args.out_root),
        "design_summary": canonical_manifest_path(str(args.design_summary)),
        "parent_rows": canonical_manifest_path(str(args.parent_rows)),
        "source_candidate_decisions": canonical_manifest_path(str(args.candidate_decisions)),
        "parent_design_gate_passed": parent_design_gate_passed,
        "parent_rows_count": len(parent_rows),
        "action_rows": len(action_rows),
        "missing_episode_keys": missing_episode_keys[:50],
        "request_rows": len(request_rows),
        "request_scenes": count_unique(request_rows, "scene_key"),
        "request_queries": count_unique(request_rows, "query"),
        "request_taxonomy_route_counts": dict(sorted(route_counts.items())),
        "request_reason_counts": dict(sorted(Counter(str(row.get("request_reason")) for row in request_rows).items())),
        "scene_counts": dict(sorted(Counter(str(row.get("scene_key")) for row in request_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in request_rows).items())),
        "positive_support_candidate_count_distribution": dict(
            sorted(Counter(str(row.get("positive_support_candidate_count")) for row in selected_actions).items())
        ),
        "mean_candidates_per_action_row": ratio(
            sum(int(row.get("candidate_count") or 0) for row in action_rows),
            len(action_rows),
        ),
        "selection_params": {
            "target_request_rows": args.target_request_rows,
            "min_request_rows": args.min_request_rows,
            "min_scenes": args.min_scenes,
            "min_queries": args.min_queries,
            "min_object_existence_rows": args.min_object_existence_rows,
            "min_rival_identity_rows": args.min_rival_identity_rows,
            "max_rows_per_scene": args.max_rows_per_scene,
            "max_rows_per_query": args.max_rows_per_query,
            "positive_score_gap": args.positive_score_gap,
            "max_positive_rank": args.max_positive_rank,
            "max_candidates_per_episode": args.max_candidates_per_episode,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden)[:50],
        "source_freeze_gate": gate,
        "source_freeze_gate_passed": gate["passed"],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "action_evidence_rows": f"{args.output_prefix}_action_evidence_rows.jsonl",
            "evaluation_labels": f"{args.output_prefix}_evaluation_labels.jsonl",
            "selected_source_rows": f"{args.output_prefix}_source_rows.jsonl",
            "all_policy_rows": f"{args.output_prefix}_policy_rows.jsonl",
            "summary": "source_summary.json",
        },
    }

    contract = build_contract(args=args, request_rows=request_rows, source_summary=source_summary)
    verify = verify_contract(contract)

    out_root = Path(args.out_root)
    write_jsonl(out_root / f"{args.output_prefix}_action_evidence_rows.jsonl", action_rows)
    write_jsonl(out_root / f"{args.output_prefix}_evaluation_labels.jsonl", label_rows)
    write_jsonl(out_root / f"{args.output_prefix}_source_rows.jsonl", selected_source_rows)
    write_jsonl(out_root / f"{args.output_prefix}_policy_rows.jsonl", all_policy_rows)
    write_json(out_root / "source_summary.json", source_summary)
    write_json(Path(args.out_manifest), contract)
    write_json(Path(args.verify_out), verify)
    return {
        "manifest": str(args.out_manifest),
        "verify": str(args.verify_out),
        "source_summary": source_summary,
        "verify_summary": verify,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the H001 broader rival-identity validation manifest.")
    parser.add_argument("--contract-name", default=CONTRACT_NAME)
    parser.add_argument("--policy-name", default=POLICY_NAME)
    parser.add_argument("--evaluation-scope", default="broader_fresh_predeclared_validation_source")
    parser.add_argument("--output-prefix", default="rival_identity_broader")
    parser.add_argument("--design-summary", required=True)
    parser.add_argument("--parent-rows", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--verify-out", required=True)
    parser.add_argument("--target-request-rows", type=int, default=30)
    parser.add_argument("--min-request-rows", type=int, default=20)
    parser.add_argument("--min-scenes", type=int, default=5)
    parser.add_argument("--min-queries", type=int, default=3)
    parser.add_argument("--min-object-existence-rows", type=int, default=4)
    parser.add_argument("--min-rival-identity-rows", type=int, default=20)
    parser.add_argument("--max-rows-per-scene", type=int, default=4)
    parser.add_argument("--max-rows-per-query", type=int, default=12)
    parser.add_argument("--positive-score-gap", type=float, default=0.005)
    parser.add_argument("--max-positive-rank", type=int, default=5)
    parser.add_argument("--max-candidates-per-episode", type=int, default=20)
    parser.add_argument("--date-frozen", default=DEFAULT_DATE_FROZEN)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
