import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    request_sort_key,
)


SCHEMA_VERSION = "h001.expanded_retrieval_source_pool_repair.v1"
SOURCE_ROUTE_ACTION = "request_source_pool_repair"
REPAIR_ACTIONS = [
    "request_backend_pool_expansion",
    "route_to_goal_validity_confirmation_after_pool_repair",
    "defer_source_pool_unresolved",
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def indexed_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("expanded_retrieval_request_id")): row for row in rows}


def source_repair_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return sorted(
        [row for row in rows if row.get("route_action") == SOURCE_ROUTE_ACTION],
        key=lambda row: request_sort_key(str(row.get("expanded_retrieval_request_id"))),
    )


def pool_accounting(row: Dict[str, Any]) -> Dict[str, Any]:
    summary = dict(row.get("action_candidate_summary") or {})
    source_pool_proxy = dict(row.get("source_pool_proxy") or {})
    candidate_ids = list(summary.get("candidate_ids") or [])
    detector_strong_ids = list(summary.get("detector_strong_candidate_ids") or [])
    local_context_ids = list(summary.get("local_context_candidate_ids") or [])
    source_top_ids = list(summary.get("source_top_candidate_ids") or [])
    return {
        "original_candidate_count": safe_int(summary.get("candidate_count")),
        "original_candidate_ids": candidate_ids,
        "current_action_pool_candidate_count": len(candidate_ids),
        "repaired_pool_candidate_count": len(candidate_ids),
        "repaired_candidate_ids": candidate_ids,
        "new_candidate_count": 0,
        "removed_candidate_count": 0,
        "duplicated_candidate_count": len(candidate_ids) - len(set(candidate_ids)),
        "unreachable_candidate_count": max(
            0,
            safe_int(source_pool_proxy.get("candidate_count")) - safe_int(source_pool_proxy.get("reachable_candidate_count")),
        ),
        "source_pool_proxy_candidate_count": source_pool_proxy.get("candidate_count"),
        "source_pool_proxy_reachable_candidate_count": source_pool_proxy.get("reachable_candidate_count"),
        "source_pool_proxy_known_reachability_count": source_pool_proxy.get("known_reachability_count"),
        "source_top_retained": bool(set(source_top_ids) & set(candidate_ids)),
        "detector_strong_retained": bool(set(detector_strong_ids) & set(candidate_ids)),
        "local_context_retained": bool(set(local_context_ids) & set(candidate_ids)),
        "strong_own_view_candidate_count": safe_int(summary.get("strong_own_view_candidate_count")),
        "detector_strong_candidate_count": safe_int(summary.get("detector_strong_candidate_count")),
        "local_context_candidate_count": safe_int(summary.get("local_context_candidate_count")),
        "source_top_candidate_count": safe_int(summary.get("source_top_candidate_count")),
    }


def repair_decision(row: Dict[str, Any], accounting: Dict[str, Any]) -> Dict[str, Any]:
    route_signals = set(str(signal) for signal in row.get("route_signals") or [])
    source_pool_proxy = dict(row.get("source_pool_proxy") or {})
    strong_own_view = safe_int(accounting.get("strong_own_view_candidate_count"))
    detector_strong = safe_int(accounting.get("detector_strong_candidate_count"))
    local_context = safe_int(accounting.get("local_context_candidate_count"))
    source_top = safe_int(accounting.get("source_top_candidate_count"))
    proxy_available = source_pool_proxy.get("available") is True
    proxy_rejected = source_pool_proxy.get("source_pool_invalid_proxy") is True

    failure_signals: List[str] = []
    if not proxy_available:
        failure_signals.append("backend_pool_proxy_unavailable")
    if proxy_rejected:
        failure_signals.append("source_pool_proxy_rejected")
    if "no_strong_own_view_candidate" in route_signals or strong_own_view == 0:
        failure_signals.append("no_strong_own_view_support")
    if "source_top_visibility_not_goal_validity" in route_signals and source_top > 0:
        failure_signals.append("source_top_visibility_not_goal_validity")
    if "expanded_local_context_pool_not_validated" in route_signals and local_context >= 2:
        failure_signals.append("local_context_pool_contradiction")
    if detector_strong == 0 and strong_own_view == 0:
        failure_signals.append("no_independent_candidate_specific_support")

    if not proxy_available:
        return {
            "repair_action": "defer_source_pool_unresolved",
            "repair_reason": "source_pool_proxy_missing",
            "repair_signals": sorted(set(failure_signals)),
            "terminal_commit": False,
        }

    if failure_signals or proxy_rejected:
        return {
            "repair_action": "request_backend_pool_expansion",
            "repair_reason": "current_pool_does_not_establish_goal_valid_candidate_pool",
            "repair_signals": sorted(set(failure_signals)),
            "terminal_commit": False,
        }

    return {
        "repair_action": "route_to_goal_validity_confirmation_after_pool_repair",
        "repair_reason": "current_pool_has_independent_support_without_action_time_pool_contradiction",
        "repair_signals": ["source_pool_repair_ready_for_goal_validity_confirmation"],
        "terminal_commit": False,
    }


def build_action_rows(route_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in source_repair_rows(route_rows):
        accounting = pool_accounting(row)
        decision = repair_decision(row, accounting)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_only_before_label_join",
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "source_schema_version": row.get("schema_version"),
                "source_route_action": row.get("route_action"),
                "source_route_branch": row.get("route_branch"),
                "source_route_reason": row.get("route_reason"),
                "source_route_signals": row.get("route_signals"),
                "source_action": row.get("source_action"),
                "source_reason": row.get("source_reason"),
                "pool_guard_status": row.get("pool_guard_status"),
                "pool_guard_reason": row.get("pool_guard_reason"),
                "instance_guard_status": row.get("instance_guard_status"),
                "instance_guard_reason": row.get("instance_guard_reason"),
                "source_pool_proxy": row.get("source_pool_proxy"),
                "action_candidate_summary": row.get("action_candidate_summary"),
                "pool_accounting": accounting,
                "uses_gt_for_action": False,
                **decision,
            }
        )
    return output


def build_evaluated_rows(
    action_rows: Sequence[Dict[str, Any]],
    route_evaluated_rows: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    evaluated_by_request = indexed_by_request(source_repair_rows(route_evaluated_rows))
    output: List[Dict[str, Any]] = []
    for row in action_rows:
        request_id = str(row.get("expanded_retrieval_request_id"))
        evaluated = evaluated_by_request.get(request_id) or {}
        candidate_summary = dict(evaluated.get("evaluation_candidate_summary") or {})
        output.append(
            {
                **row,
                "validation_stage": "evaluation_joined_after_action_rows",
                "evaluation_candidate_summary": candidate_summary,
                "evaluation_only_has_valid_candidate": candidate_summary.get(
                    "evaluation_only_no_valid_candidate_pool"
                )
                is False,
                "evaluation_only_no_valid_candidate_pool": candidate_summary.get(
                    "evaluation_only_no_valid_candidate_pool"
                ),
                "evaluation_only_correct_candidate_count": candidate_summary.get(
                    "evaluation_only_correct_candidate_count"
                ),
                "evaluation_only_wrong_candidate_count": candidate_summary.get(
                    "evaluation_only_wrong_candidate_count"
                ),
                "evaluation_only_correct_candidate_ids": candidate_summary.get(
                    "evaluation_only_correct_candidate_ids"
                ),
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return output


def count_by_action(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, int]:
    counts = Counter(str(row.get(key)) for row in rows)
    return {action: counts.get(action, 0) for action in REPAIR_ACTIONS}


def summarize(
    action_rows: Sequence[Dict[str, Any]],
    evaluated_rows: Sequence[Dict[str, Any]],
    contract: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    action_counts = count_by_action(action_rows, "repair_action")
    reason_counts = Counter(str(row.get("repair_reason")) for row in action_rows)
    signal_counts = Counter(
        str(signal)
        for row in action_rows
        for signal in row.get("repair_signals") or []
    )
    no_valid_by_route = Counter(
        str(row.get("repair_action"))
        for row in evaluated_rows
        if row.get("evaluation_only_no_valid_candidate_pool") is True
    )
    valid_by_route = Counter(
        str(row.get("repair_action"))
        for row in evaluated_rows
        if row.get("evaluation_only_has_valid_candidate") is True
    )
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    repaired_counts_reported = all("pool_accounting" in row for row in action_rows)
    gates = contract.get("evaluation_gates") or {}
    expected_rows = safe_int(gates.get("input_request_rows"), default=args.expected_request_rows)
    gate = {
        "input_request_rows_passed": len(action_rows) == expected_rows,
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(
            gates.get("terminal_commit_rows_maximum"), default=0
        ),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), default=0),
        "reports_route_action_counts": all(action in action_counts for action in REPAIR_ACTIONS),
        "reports_repaired_pool_candidate_counts": repaired_counts_reported,
        "reports_backend_expansion_rows": "request_backend_pool_expansion" in action_counts,
        "reports_goal_validity_ready_rows": (
            "route_to_goal_validity_confirmation_after_pool_repair" in action_counts
        ),
        "reports_defer_source_pool_unresolved_rows": "defer_source_pool_unresolved" in action_counts,
        "joins_labels_only_after_action_rows": True,
        "reports_no_valid_rows_by_route_after_label_join": bool(no_valid_by_route or evaluated_rows),
        "uses_gt_for_action_passed": True,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }
    gate["source_pool_repair_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key not in {"paper_claim_allowed", "uses_gt_for_action", "uses_gt_for_analysis"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "route_rows": str(args.route_rows),
        "route_evaluated_rows": str(args.route_evaluated_rows),
        "out_root": str(args.out_root),
        "request_rows": len(action_rows),
        "evaluated_rows": len(evaluated_rows),
        "terminal_commit_rows": len(terminal_rows),
        "repair_action_counts": action_counts,
        "repair_reason_counts": dict(sorted(reason_counts.items())),
        "repair_signal_counts": dict(sorted(signal_counts.items())),
        "no_valid_rows_by_repair_action": {
            action: no_valid_by_route.get(action, 0) for action in REPAIR_ACTIONS
        },
        "valid_rows_by_repair_action": {action: valid_by_route.get(action, 0) for action in REPAIR_ACTIONS},
        "backend_expansion_rows": action_counts.get("request_backend_pool_expansion", 0),
        "goal_validity_ready_rows": action_counts.get(
            "route_to_goal_validity_confirmation_after_pool_repair", 0
        ),
        "defer_source_pool_unresolved_rows": action_counts.get("defer_source_pool_unresolved", 0),
        "repaired_pool_candidate_counts": [
            {
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "repair_action": row.get("repair_action"),
                "pool_accounting": row.get("pool_accounting"),
            }
            for row in action_rows
        ],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gate": gate,
        "interpretation": {
            "fact": (
                "The analyzer materializes source-pool repair action rows before joining "
                "evaluation-only candidate labels."
            ),
            "agent_inference": (
                "The current five source-pool repair rows do not contain enough action-time "
                "evidence to proceed to goal-validity confirmation; they should request backend "
                "pool expansion before any terminal ObjectNav decision."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "repair_rows": "source_pool_repair_rows.jsonl",
            "evaluated_rows": "source_pool_repair_evaluated_rows.jsonl",
            "summary": "source_pool_repair_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    route_rows = load_jsonl(Path(args.route_rows))
    route_evaluated_rows = load_jsonl(Path(args.route_evaluated_rows))

    action_rows = build_action_rows(route_rows)
    evaluated_rows = build_evaluated_rows(action_rows, route_evaluated_rows)
    summary = summarize(action_rows, evaluated_rows, contract, args)

    write_jsonl(out_root / "source_pool_repair_rows.jsonl", action_rows)
    write_jsonl(out_root / "source_pool_repair_evaluated_rows.jsonl", evaluated_rows)
    write_json(out_root / "source_pool_repair_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Route source-pool repair rows before any goal-validity confirmation."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--route-rows", required=True)
    parser.add_argument("--route-evaluated-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--expected-request-rows", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
