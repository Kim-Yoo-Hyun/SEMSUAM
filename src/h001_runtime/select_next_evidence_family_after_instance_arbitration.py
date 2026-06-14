import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Sequence


SCHEMA_VERSION = "h001.next_label_free_evidence_family_after_instance_arbitration.v1"
POLICY_NAME = "next_evidence_family_after_instance_arbitration_selector_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_next_label_free_evidence_family_after_instance_arbitration_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_next_label_free_evidence_family_after_instance_arbitration_v1"


FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
    "evaluation_only_correct_candidate_count",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_unlabeled_candidate_count",
    "evaluation_only_wrong_candidate_count",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "is_correct",
    "oracle_action",
    "target_label",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def source_path(args: argparse.Namespace, contract: Mapping[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def gate_value(summary: Mapping[str, Any], key: str) -> Any:
    return (summary.get("gate") or {}).get(key)


def count_by(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    return dict(sorted(Counter(str(row.get(key) or "") for row in rows if row.get(key)).items()))


def action_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def route_rows_for(rows: Sequence[Mapping[str, Any]], route_branch: str) -> List[Mapping[str, Any]]:
    return [row for row in rows if row.get("route_branch") == route_branch]


def route_stats(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    scenes = sorted({str(row.get("scene_key")) for row in rows if row.get("scene_key")})
    queries = sorted({str(row.get("query")) for row in rows if row.get("query")})
    candidate_count_sum = sum(safe_int((row.get("action_candidate_summary") or {}).get("candidate_count")) for row in rows)
    strong_own_view_sum = sum(
        safe_int((row.get("action_candidate_summary") or {}).get("strong_own_view_candidate_count"))
        for row in rows
    )
    detector_strong_sum = sum(
        safe_int((row.get("action_candidate_summary") or {}).get("detector_strong_candidate_count"))
        for row in rows
    )
    return {
        "request_rows": len(rows),
        "unique_scene_count": len(scenes),
        "unique_query_count": len(queries),
        "scenes": scenes,
        "queries": queries,
        "route_action_counts": count_by(rows, "route_action"),
        "route_reason_counts": count_by(rows, "route_reason"),
        "candidate_count_sum": candidate_count_sum,
        "strong_own_view_candidate_count_sum": strong_own_view_sum,
        "detector_strong_candidate_count_sum": detector_strong_sum,
    }


def semantic_branch_promotable_rows(
    *,
    residual_summary: Mapping[str, Any],
    missing_summary: Mapping[str, Any],
    instance_summary: Mapping[str, Any],
) -> int:
    return (
        safe_int(residual_summary.get("closure_promotable_rows"), 0)
        + safe_int(missing_summary.get("promotable_terminal_outcome_rows"), 0)
        + safe_int(instance_summary.get("promotable_branch_outcome_rows"), 0)
    )


def build_selection_rows(
    *,
    contract: Mapping[str, Any],
    route_rows: Sequence[Mapping[str, Any]],
    route_summary: Mapping[str, Any],
    post_object_relation_summary: Mapping[str, Any],
    source_pool_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    missing_summary: Mapping[str, Any],
    instance_summary: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    del route_summary
    decision = contract.get("selection_decision") or {}
    selected = str(decision.get("selected_family"))
    closed = decision.get("closed_or_not_selected_families") or {}
    families = [
        "source_pool_repair_v1",
        "object_relation_branch_family",
        "instance_arbitration_defer_v1",
        "semantic_slam_map_pose_consistency_probe_v1",
        "depth_stagnation_independent_support_probe",
    ]
    rows: List[Dict[str, Any]] = []
    for family in families:
        if family == selected:
            status = decision.get("selected_output_status")
            next_action = decision.get("selected_action")
            route_branch = None
            reason = "semantic_object_evidence_branches_closed_without_promotable_outcome"
        elif family == "object_relation_branch_family":
            status = closed.get(family)
            next_action = "none_family_closed"
            route_branch = "goal_validity_confirmation_v1"
            reason = "goal_validity_confirmation_followed_to_object_relation_missing_own_view_and_residual_closures"
        elif family == "depth_stagnation_independent_support_probe":
            status = closed.get(family)
            next_action = "none_deferred"
            route_branch = None
            reason = "single_row_stagnant_case_deferred_until_broader_rows_or_map_pose_side_support"
        else:
            status = closed.get(family)
            next_action = "none_family_closed"
            route_branch = family
            reason = "already_followed_and_closed_or_recorded_as_blind_spot"
        family_route_rows = route_rows_for(route_rows, route_branch) if route_branch else []
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_next_label_free_evidence_family_after_instance_arbitration_closure",
                "policy": POLICY_NAME,
                "family_name": family,
                "selection_status": status,
                "next_action": next_action,
                "selection_reason": reason,
                "route_branch_name": route_branch,
                "route_branch_stats": route_stats(family_route_rows),
                "source_pool_status": {
                    "second_fallback_gate_passed": gate_value(source_pool_summary, "second_fallback_gate_passed"),
                    "backend_source_map_blind_spot_after_second_fallback": gate_value(
                        source_pool_summary, "backend_source_map_blind_spot_after_second_fallback"
                    ),
                    "goal_validity_confirmation_unblocked": gate_value(
                        source_pool_summary, "goal_validity_confirmation_unblocked"
                    ),
                },
                "object_relation_selector_status": {
                    "gate_passed": gate_value(
                        post_object_relation_summary,
                        "next_label_free_evidence_family_after_object_relation_gate_passed",
                    ),
                    "selected_family": post_object_relation_summary.get("selected_family"),
                    "selected_action": post_object_relation_summary.get("selected_action"),
                    "object_relation_family_closure": post_object_relation_summary.get("object_relation_family_closure")
                    or {},
                },
                "residual_closure_promotable_rows": safe_int(
                    residual_summary.get("closure_promotable_rows"), 0
                ),
                "missing_own_view_promotable_terminal_outcome_rows": safe_int(
                    missing_summary.get("promotable_terminal_outcome_rows"), 0
                ),
                "instance_arbitration_promotable_branch_outcome_rows": safe_int(
                    instance_summary.get("promotable_branch_outcome_rows"), 0
                ),
                "terminal_commit": False,
                "terminal_utility_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return rows


def summarize(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    route_summary: Mapping[str, Any],
    route_rows: Sequence[Mapping[str, Any]],
    post_object_relation_summary: Mapping[str, Any],
    source_pool_summary: Mapping[str, Any],
    residual_summary: Mapping[str, Any],
    missing_summary: Mapping[str, Any],
    instance_summary: Mapping[str, Any],
    selection_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    decision = contract.get("selection_decision") or {}
    source_gate = contract.get("source_gate") or {}
    route_branch_counts = route_summary.get("route_branch_counts") or count_by(route_rows, "route_branch")
    expected_counts = decision.get("expected_route_branch_counts") or {}
    semantic_promotable_rows = semantic_branch_promotable_rows(
        residual_summary=residual_summary,
        missing_summary=missing_summary,
        instance_summary=instance_summary,
    )
    terminal_commit_rows = sum(1 for row in selection_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in selection_rows if row.get("candidate_commit_allowed") is True)
    candidate_rejection_rows = sum(1 for row in selection_rows if row.get("candidate_rejection_allowed") is True)
    forbidden = action_forbidden_keys(selection_rows)
    semantic_object_branches_exhausted = (
        gate_value(source_pool_summary, "backend_source_map_blind_spot_after_second_fallback") is True
        and safe_int(residual_summary.get("closure_promotable_rows"), -1) == 0
        and safe_int(missing_summary.get("promotable_terminal_outcome_rows"), -1) == 0
        and safe_int(instance_summary.get("promotable_branch_outcome_rows"), -1) == 0
    )
    gate = {
        "route_contract_gate_passed": gate_value(route_summary, "route_contract_gate_passed")
        is source_gate.get("route_contract_gate_passed"),
        "expected_route_branch_counts_passed": {
            branch: safe_int(route_branch_counts.get(branch), 0) == safe_int(expected, 0)
            for branch, expected in expected_counts.items()
        },
        "post_object_relation_selector_gate_passed": gate_value(
            post_object_relation_summary, "next_label_free_evidence_family_after_object_relation_gate_passed"
        )
        is source_gate.get("post_object_relation_selector_gate_passed"),
        "source_pool_second_fallback_gate_passed": gate_value(source_pool_summary, "second_fallback_gate_passed")
        is source_gate.get("source_pool_second_fallback_gate_passed"),
        "source_pool_blind_spot_recorded_passed": gate_value(
            source_pool_summary, "backend_source_map_blind_spot_after_second_fallback"
        )
        is source_gate.get("source_pool_blind_spot_recorded"),
        "residual_branch_closure_gate_passed": gate_value(
            residual_summary, "residual_branch_closure_gate_passed"
        )
        is source_gate.get("residual_branch_closure_gate_passed"),
        "missing_own_view_guard_branch_closure_gate_passed": gate_value(
            missing_summary, "missing_own_view_guard_branch_closure_gate_passed"
        )
        is source_gate.get("missing_own_view_guard_branch_closure_gate_passed"),
        "instance_arbitration_pair_graph_branch_closure_gate_passed": gate_value(
            instance_summary, "instance_arbitration_pair_graph_branch_closure_gate_passed"
        )
        is source_gate.get("instance_arbitration_pair_graph_branch_closure_gate_passed"),
        "semantic_branch_promotable_rows_passed": semantic_promotable_rows
        <= safe_int(source_gate.get("max_semantic_branch_promotable_rows"), 0),
        "semantic_object_branches_exhausted_passed": semantic_object_branches_exhausted,
        "selected_family_is_step_4_5_probe_passed": decision.get("selected_family")
        == "semantic_slam_map_pose_consistency_probe_v1",
        "selected_action_is_contract_freeze_passed": decision.get("selected_action")
        == "freeze_semantic_slam_map_pose_consistency_probe_contract",
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(source_gate.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": terminal_commit_rows
        <= safe_int(source_gate.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": candidate_commit_rows
        <= safe_int(source_gate.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": candidate_rejection_rows
        <= safe_int(source_gate.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in selection_rows),
        "paper_claim_allowed": False,
    }
    nested_gate_values: List[Any] = []
    for key, value in gate.items():
        if key == "paper_claim_allowed":
            continue
        if isinstance(value, dict):
            nested_gate_values.extend(value.values())
        else:
            nested_gate_values.append(value)
    gate["next_label_free_evidence_family_after_instance_arbitration_gate_passed"] = all(
        item is True for item in nested_gate_values if isinstance(item, bool)
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "source_files": {
            "route_specific_summary": str(args.route_summary),
            "route_specific_rows": str(args.route_rows),
            "post_object_relation_selector_summary": str(args.post_object_relation_summary),
            "source_pool_second_fallback_summary": str(args.source_pool_summary),
            "residual_branch_closure_summary": str(args.residual_summary),
            "missing_own_view_guard_branch_closure_summary": str(args.missing_summary),
            "instance_arbitration_pair_graph_branch_closure_summary": str(args.instance_summary),
        },
        "selected_family": decision.get("selected_family"),
        "selected_action": decision.get("selected_action"),
        "route_branch_counts": route_branch_counts,
        "route_action_counts": route_summary.get("route_action_counts") or count_by(route_rows, "route_action"),
        "route_reason_counts": route_summary.get("route_reason_counts") or count_by(route_rows, "route_reason"),
        "semantic_object_branch_closure": {
            "source_pool_route_rows": safe_int(route_branch_counts.get("source_pool_repair_v1"), 0),
            "source_pool_second_fallback_gate_passed": gate_value(source_pool_summary, "second_fallback_gate_passed"),
            "backend_source_map_blind_spot_after_second_fallback": gate_value(
                source_pool_summary, "backend_source_map_blind_spot_after_second_fallback"
            ),
            "object_relation_prior_selected_family": post_object_relation_summary.get("selected_family"),
            "object_relation_prior_selected_action": post_object_relation_summary.get("selected_action"),
            "object_relation_family_closure": post_object_relation_summary.get("object_relation_family_closure")
            or {},
            "residual_closure_promotable_rows": safe_int(residual_summary.get("closure_promotable_rows"), 0),
            "missing_own_view_promotable_terminal_outcome_rows": safe_int(
                missing_summary.get("promotable_terminal_outcome_rows"), 0
            ),
            "instance_arbitration_promotable_branch_outcome_rows": safe_int(
                instance_summary.get("promotable_branch_outcome_rows"), 0
            ),
            "semantic_branch_promotable_rows": semantic_promotable_rows,
            "semantic_object_branches_exhausted": semantic_object_branches_exhausted,
        },
        "instance_arbitration_closure": {
            "request_closure_rows": safe_int(instance_summary.get("request_closure_rows"), 0),
            "candidate_closure_rows": safe_int(instance_summary.get("candidate_closure_rows"), 0),
            "pair_closure_rows": safe_int(instance_summary.get("pair_closure_rows"), 0),
            "shortcut_closure_rows": safe_int(instance_summary.get("shortcut_closure_rows"), 0),
            "request_closure_status_counts": instance_summary.get("request_closure_status_counts") or {},
            "candidate_closure_status_counts": instance_summary.get("candidate_closure_status_counts") or {},
            "pair_closure_status_counts": instance_summary.get("pair_closure_status_counts") or {},
            "shortcut_blocked_reason_counts": instance_summary.get("shortcut_blocked_reason_counts") or {},
        },
        "selection_rows": len(selection_rows),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "analysis_label_fields_allowed": True,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "diagnostic_conclusion": {
            "recommended_next_task": contract.get("next_research_task_after_selection"),
            "selected_family": decision.get("selected_family"),
            "selected_action": decision.get("selected_action"),
            "terminal_policy_allowed": False,
            "candidate_commit_allowed": False,
            "candidate_rejection_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": {
            "fact": (
                "The selector reads existing action-time route rows and closure summaries. It writes no "
                "terminal commit, candidate commit, or candidate rejection rows."
            ),
            "agent_inference": (
                "The current semantic object evidence route is exhausted as terminal utility. The next "
                "label-free evidence family should test semantic-SLAM map/pose consistency because that "
                "is the remaining H001 Step 4-5 novelty axis."
            ),
            "paper_claim": "No paper claim is allowed from this selection output alone.",
        },
        "output_files": {
            "selection_rows": "next_label_free_evidence_family_after_instance_arbitration_rows.jsonl",
            "summary": "next_label_free_evidence_family_after_instance_arbitration_summary.json",
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--route-summary")
    parser.add_argument("--route-rows")
    parser.add_argument("--post-object-relation-summary")
    parser.add_argument("--source-pool-summary")
    parser.add_argument("--residual-summary")
    parser.add_argument("--missing-summary")
    parser.add_argument("--instance-summary")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    contract = load_json(Path(args.contract))
    args.out_root = Path(args.out_root)
    args.route_summary = source_path(args, contract, "route_summary", "route_specific_summary")
    args.route_rows = source_path(args, contract, "route_rows", "route_specific_rows")
    args.post_object_relation_summary = source_path(
        args,
        contract,
        "post_object_relation_summary",
        "post_object_relation_selector_summary",
    )
    args.source_pool_summary = source_path(
        args, contract, "source_pool_summary", "source_pool_second_fallback_summary"
    )
    args.residual_summary = source_path(args, contract, "residual_summary", "residual_branch_closure_summary")
    args.missing_summary = source_path(
        args, contract, "missing_summary", "missing_own_view_guard_branch_closure_summary"
    )
    args.instance_summary = source_path(
        args,
        contract,
        "instance_summary",
        "instance_arbitration_pair_graph_branch_closure_summary",
    )

    route_summary = load_json(args.route_summary)
    route_rows = load_jsonl(args.route_rows)
    post_object_relation_summary = load_json(args.post_object_relation_summary)
    source_pool_summary = load_json(args.source_pool_summary)
    residual_summary = load_json(args.residual_summary)
    missing_summary = load_json(args.missing_summary)
    instance_summary = load_json(args.instance_summary)
    selection_rows = build_selection_rows(
        contract=contract,
        route_rows=route_rows,
        route_summary=route_summary,
        post_object_relation_summary=post_object_relation_summary,
        source_pool_summary=source_pool_summary,
        residual_summary=residual_summary,
        missing_summary=missing_summary,
        instance_summary=instance_summary,
    )
    summary = summarize(
        args=args,
        contract=contract,
        route_summary=route_summary,
        route_rows=route_rows,
        post_object_relation_summary=post_object_relation_summary,
        source_pool_summary=source_pool_summary,
        residual_summary=residual_summary,
        missing_summary=missing_summary,
        instance_summary=instance_summary,
        selection_rows=selection_rows,
    )
    write_jsonl(args.out_root / "next_label_free_evidence_family_after_instance_arbitration_rows.jsonl", selection_rows)
    write_json(args.out_root / "next_label_free_evidence_family_after_instance_arbitration_summary.json", summary)


if __name__ == "__main__":
    main()
