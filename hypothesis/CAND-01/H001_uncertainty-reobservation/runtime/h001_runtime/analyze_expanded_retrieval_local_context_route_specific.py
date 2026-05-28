import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    ratio,
    request_sort_key,
)


SCHEMA_VERSION = "h001.expanded_retrieval_local_context_route_specific.v1"
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


def role_contains(row: Dict[str, Any], role: str) -> bool:
    return role in str(row.get("candidate_role") or "").split("+")


def action_candidate_summary(evidence_rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    strong = [row for row in evidence_rows if row.get("strong_own_view_evidence") is True]
    detector_strong = [
        row
        for row in evidence_rows
        if role_contains(row, "detector_strong_candidate") or role_contains(row, "detector_strong_rival")
    ]
    local_context = [row for row in evidence_rows if role_contains(row, "local_context_candidate")]
    source_top = [row for row in evidence_rows if role_contains(row, "source_top")]
    return {
        "candidate_count": len(evidence_rows),
        "strong_own_view_candidate_count": len(strong),
        "detector_strong_candidate_count": len(detector_strong),
        "local_context_candidate_count": len(local_context),
        "source_top_candidate_count": len(source_top),
        "candidate_ids": [row.get("candidate_id") for row in evidence_rows],
        "strong_own_view_candidate_ids": [row.get("candidate_id") for row in strong],
        "detector_strong_candidate_ids": [row.get("candidate_id") for row in detector_strong],
        "local_context_candidate_ids": [row.get("candidate_id") for row in local_context],
        "source_top_candidate_ids": [row.get("candidate_id") for row in source_top],
    }


def evaluation_candidate_summary(
    evidence_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    correct: List[Dict[str, Any]] = []
    wrong: List[Dict[str, Any]] = []
    unlabeled: List[Dict[str, Any]] = []
    for row in evidence_rows:
        label = labels.get((str(row.get("episode_key")), str(row.get("candidate_id"))))
        if label is None:
            unlabeled.append(row)
        elif label.get("evaluation_only_candidate_correct") is True:
            correct.append(row)
        else:
            wrong.append(row)
    return {
        "evaluation_only_correct_candidate_count": len(correct),
        "evaluation_only_wrong_candidate_count": len(wrong),
        "evaluation_only_unlabeled_candidate_count": len(unlabeled),
        "evaluation_only_no_valid_candidate_pool": len(correct) == 0,
        "evaluation_only_correct_candidate_ids": [row.get("candidate_id") for row in correct],
        "evaluation_only_wrong_candidate_ids": [row.get("candidate_id") for row in wrong],
    }


def outcome_payload(row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if row is None:
        return {
            "available": False,
            "action": None,
            "terminal_commit": None,
            "success_commit": None,
            "wrong_goal_commit": None,
            "no_valid_commit": None,
            "selected_candidate_id": None,
        }
    return {
        "available": True,
        "action": row.get("action"),
        "terminal_commit": row.get("terminal_commit"),
        "success_commit": row.get("evaluation_only_success_commit"),
        "wrong_goal_commit": row.get("evaluation_only_wrong_goal_commit"),
        "no_valid_commit": row.get("evaluation_only_no_valid_commit"),
        "selected_candidate_id": row.get("selected_candidate_id"),
    }


def route_action(
    revision: Dict[str, Any],
    candidate_summary: Dict[str, Any],
) -> Dict[str, Any]:
    guard = revision.get("decision_guard") or {}
    pool_guard = guard.get("pool_validity_guard") or {}
    instance_guard = guard.get("instance_arbitration_guard") or {}
    pool_status = str(pool_guard.get("status"))
    instance_reason = str(instance_guard.get("reason"))
    revision_action = str(revision.get("action"))

    pool_repair_signals: List[str] = []
    if pool_status != "passed":
        pool_repair_signals.append(f"pool_guard_{pool_status}")
    if revision_action == "request_goal_validity_confirmation" and instance_reason in {
        "no_strong_own_view_candidate",
        "source_top_visibility_not_goal_validity",
    }:
        pool_repair_signals.append(instance_reason)
    if (
        revision_action == "request_goal_validity_confirmation"
        and safe_int(candidate_summary.get("local_context_candidate_count")) >= 2
    ):
        pool_repair_signals.append("expanded_local_context_pool_not_validated")

    if pool_repair_signals:
        return {
            "route_branch": "source_pool_repair_v1",
            "route_action": "request_source_pool_repair",
            "route_reason": "source_pool_validity_requires_repair_before_goal_validity",
            "route_signals": sorted(set(pool_repair_signals)),
            "terminal_commit": False,
        }
    if revision_action == "request_goal_validity_confirmation":
        return {
            "route_branch": "goal_validity_confirmation_v1",
            "route_action": "request_goal_validity_confirmation_evidence",
            "route_reason": "visible_category_instance_requires_goal_validity_confirmation",
            "route_signals": [instance_reason],
            "terminal_commit": False,
        }
    return {
        "route_branch": "instance_arbitration_defer_v1",
        "route_action": "defer_instance_arbitration_unresolved",
        "route_reason": "multi_candidate_instance_arbitration_unresolved",
        "route_signals": [instance_reason],
        "terminal_commit": False,
    }


def build_action_rows(
    evidence_by_request: Dict[str, List[Dict[str, Any]]],
    revision_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for revision in sorted(revision_rows, key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id")))):
        request_id = str(revision.get("expanded_retrieval_request_id"))
        evidence = evidence_by_request.get(request_id, [])
        candidate_summary = action_candidate_summary(evidence)
        route = route_action(revision, candidate_summary)
        guard = revision.get("decision_guard") or {}
        pool_guard = guard.get("pool_validity_guard") or {}
        instance_guard = guard.get("instance_arbitration_guard") or {}
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_routing_only",
                "expanded_retrieval_request_id": request_id,
                "rival_identity_request_id": revision.get("rival_identity_request_id"),
                "episode_key": revision.get("episode_key"),
                "scene_key": revision.get("scene_key"),
                "scene_id": revision.get("scene_id"),
                "query": revision.get("query"),
                "source_variant": REVISION_VARIANT,
                "source_action": revision.get("action"),
                "source_reason": revision.get("reason"),
                "pool_guard_status": pool_guard.get("status"),
                "pool_guard_reason": pool_guard.get("reason"),
                "instance_guard_status": instance_guard.get("status"),
                "instance_guard_reason": instance_guard.get("reason"),
                "source_pool_proxy": pool_guard.get("source_pool_proxy"),
                "action_candidate_summary": candidate_summary,
                "uses_gt_for_action": False,
                **route,
            }
        )
    return rows


def build_evaluated_rows(
    action_rows: Sequence[Dict[str, Any]],
    evidence_by_request: Dict[str, List[Dict[str, Any]]],
    evaluated_by_key: Dict[Tuple[str, str], Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in action_rows:
        request_id = str(row.get("expanded_retrieval_request_id"))
        evidence = evidence_by_request.get(request_id, [])
        eval_summary = evaluation_candidate_summary(evidence, labels)
        variant_outcomes = {
            variant: outcome_payload(evaluated_by_key.get((request_id, variant)))
            for variant in ALTERNATIVE_VARIANTS
        }
        output.append(
            {
                **row,
                "validation_stage": "evaluation_joined_after_action",
                "evaluation_candidate_summary": eval_summary,
                "evaluation_only_route_has_valid_candidate": not eval_summary[
                    "evaluation_only_no_valid_candidate_pool"
                ],
                "evaluation_only_previous_success_lost_by_route": variant_outcomes[PREVIOUS_VARIANT][
                    "success_commit"
                ]
                is True,
                "evaluation_only_unsafe_previous_commit_prevented": (
                    variant_outcomes[PREVIOUS_VARIANT]["wrong_goal_commit"] is True
                    or variant_outcomes[PREVIOUS_VARIANT]["no_valid_commit"] is True
                ),
                "evaluation_only_any_simpler_alternative_unsafe": any(
                    outcome["wrong_goal_commit"] is True or outcome["no_valid_commit"] is True
                    for variant, outcome in variant_outcomes.items()
                    if variant != "defer_all"
                ),
                "evaluation_only_variant_outcomes": variant_outcomes,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return output


def summarize(action_rows: Sequence[Dict[str, Any]], evaluated_rows: Sequence[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    route_counts = Counter(str(row.get("route_action")) for row in action_rows)
    branch_counts = Counter(str(row.get("route_branch")) for row in action_rows)
    route_reason_counts = Counter(str(row.get("route_reason")) for row in action_rows)
    source_action_counts = Counter(str(row.get("source_action")) for row in action_rows)
    no_valid_by_route = Counter(
        str(row.get("route_action"))
        for row in evaluated_rows
        if row.get("evaluation_only_route_has_valid_candidate") is False
    )
    valid_by_route = Counter(
        str(row.get("route_action"))
        for row in evaluated_rows
        if row.get("evaluation_only_route_has_valid_candidate") is True
    )
    forbidden = action_forbidden_keys(action_rows)
    terminal_commit_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    expected_rows = int(args.expected_request_rows)
    gate = {
        "routes_all_request_rows": len(action_rows) == expected_rows,
        "terminal_commit_rows_pass": len(terminal_commit_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) == 0,
        "reports_source_pool_repair_rows": "request_source_pool_repair" in route_counts,
        "reports_goal_validity_confirmation_rows": "request_goal_validity_confirmation_evidence" in route_counts,
        "reports_instance_defer_rows": "defer_instance_arbitration_unresolved" in route_counts,
        "uses_gt_for_action_passed": True,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }
    gate["route_contract_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"paper_claim_allowed", "uses_gt_for_action"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "evidence_rows": str(args.evidence_rows),
        "decision_rows": str(args.decision_rows),
        "evaluated_rows": str(args.evaluated_rows),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "request_rows": len(action_rows),
        "terminal_commit_rows": len(terminal_commit_rows),
        "route_action_counts": dict(sorted(route_counts.items())),
        "route_branch_counts": dict(sorted(branch_counts.items())),
        "route_reason_counts": dict(sorted(route_reason_counts.items())),
        "source_revision_action_counts": dict(sorted(source_action_counts.items())),
        "route_counts_for_no_valid_rows": dict(sorted(no_valid_by_route.items())),
        "route_counts_for_valid_rows": dict(sorted(valid_by_route.items())),
        "source_pool_repair_rows": route_counts.get("request_source_pool_repair", 0),
        "goal_validity_confirmation_rows": route_counts.get("request_goal_validity_confirmation_evidence", 0),
        "instance_defer_rows": route_counts.get("defer_instance_arbitration_unresolved", 0),
        "lost_previous_success_rows": sum(
            row.get("evaluation_only_previous_success_lost_by_route") is True for row in evaluated_rows
        ),
        "unsafe_previous_commit_prevented_rows": sum(
            row.get("evaluation_only_unsafe_previous_commit_prevented") is True for row in evaluated_rows
        ),
        "simpler_alternatives_unsafe_rows": sum(
            row.get("evaluation_only_any_simpler_alternative_unsafe") is True for row in evaluated_rows
        ),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "interpretation": {
            "fact": (
                "This analyzer writes route actions without terminal commits and joins labels only after "
                "action rows are materialized."
            ),
            "agent_inference": (
                "The output is a branch-routing artifact. It can unblock source-pool repair and "
                "goal-validity confirmation implementation, but cannot support a paper utility claim."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "route_rows": "expanded_retrieval_local_context_route_specific_rows.jsonl",
            "evaluated_rows": "expanded_retrieval_local_context_route_specific_evaluated_rows.jsonl",
            "summary": "expanded_retrieval_local_context_route_specific_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    expected = contract.get("evaluation_gates", {}).get("routes_all_request_rows")
    if expected is not None and int(expected) != int(args.expected_request_rows):
        raise ValueError(f"expected rows mismatch: contract={expected} args={args.expected_request_rows}")

    evidence_rows = load_jsonl(Path(args.evidence_rows))
    decision_rows = load_jsonl(Path(args.decision_rows))
    source_evaluated_rows = load_jsonl(Path(args.evaluated_rows))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))
    evidence_by_request = group_by_request(evidence_rows)
    evaluated_by_key = decision_index(source_evaluated_rows)
    revision_rows = [row for row in decision_rows if row.get("variant") == REVISION_VARIANT]

    action_rows = build_action_rows(evidence_by_request, revision_rows)
    evaluated_rows = build_evaluated_rows(action_rows, evidence_by_request, evaluated_by_key, labels)
    summary = summarize(action_rows, evaluated_rows, args)

    write_jsonl(out_root / "expanded_retrieval_local_context_route_specific_rows.jsonl", action_rows)
    write_jsonl(out_root / "expanded_retrieval_local_context_route_specific_evaluated_rows.jsonl", evaluated_rows)
    write_json(out_root / "expanded_retrieval_local_context_route_specific_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route paper-scale local-context rows by branch-specific contract.")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--evidence-rows", required=True)
    parser.add_argument("--decision-rows", required=True)
    parser.add_argument("--evaluated-rows", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--expected-request-rows", type=int, default=21)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
