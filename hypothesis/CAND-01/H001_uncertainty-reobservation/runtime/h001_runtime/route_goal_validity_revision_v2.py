import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


SCHEMA_VERSION = "h001.goal_validity_revision_v2_router.v1"


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


def request_sort_key(request_id: str) -> tuple[int, str]:
    suffix = request_id.split(":")[-1]
    return (int(suffix), request_id) if suffix.isdigit() else (999999, request_id)


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


def choose_revision_action(
    *,
    decision: Dict[str, Any],
    evidence_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    strong_rows = [row for row in evidence_rows if row.get("strong_identity_evidence") is True]
    validity_rows = [row for row in evidence_rows if goal_validity_surrogate(row)]
    max_own = max((safe_int(row.get("post_own_associated_heading_count")) for row in evidence_rows), default=0)
    max_cross = max((safe_int(row.get("post_cross_associated_heading_count")) for row in evidence_rows), default=0)
    max_margin = max((safe_int(row.get("post_identity_margin")) for row in evidence_rows), default=0)
    route = decision.get("request_taxonomy_route")

    if route == "object_existence_validation":
        return {
            "revision_action": "request_object_existence_confirmation",
            "revision_reason": "object_existence_requires_independent_confirmation",
            "revision_branch": "object_existence_validation",
            "commit_allowed": False,
        }
    if max_own == 0:
        return {
            "revision_action": "request_expanded_retrieval",
            "revision_reason": "no_own_candidate_support_after_observation",
            "revision_branch": "no_own_candidate_support",
            "commit_allowed": False,
        }
    if len(validity_rows) > 1:
        return {
            "revision_action": "request_discriminative_rival_view",
            "revision_reason": "multiple_goal_validity_candidates",
            "revision_branch": "cross_view_aliasing",
            "commit_allowed": False,
        }
    if max_cross > 0:
        return {
            "revision_action": "request_discriminative_rival_view",
            "revision_reason": "cross_view_aliasing_requires_contrastive_evidence",
            "revision_branch": "cross_view_aliasing",
            "commit_allowed": False,
        }
    if strong_rows:
        return {
            "revision_action": "request_goal_validity_confirmation",
            "revision_reason": "strong_identity_evidence_is_not_goal_validity",
            "revision_branch": "strong_identity_not_goal_validity",
            "commit_allowed": False,
        }
    if max_margin <= 1:
        return {
            "revision_action": "request_discriminative_rival_view",
            "revision_reason": "identity_margin_not_discriminative",
            "revision_branch": "cross_view_aliasing",
            "commit_allowed": False,
        }
    return {
        "revision_action": "request_expanded_retrieval",
        "revision_reason": "no_non_gt_terminal_commit_path",
        "revision_branch": "planned_candidate_set_needs_retrieval",
        "commit_allowed": False,
    }


def build_rows(evidence_rows: Sequence[Dict[str, Any]], decision_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    evidence_by_request = group_by_request(evidence_rows)
    decisions = one_by_request(decision_rows)
    output: List[Dict[str, Any]] = []
    for request_id in sorted(decisions, key=request_sort_key):
        decision = decisions[request_id]
        evidence = evidence_by_request.get(request_id, [])
        route = choose_revision_action(decision=decision, evidence_rows=evidence)
        strong_ids = [str(row.get("candidate_id")) for row in evidence if row.get("strong_identity_evidence") is True]
        validity_ids = [str(row.get("candidate_id")) for row in evidence if goal_validity_surrogate(row)]
        row = {
            "schema_version": SCHEMA_VERSION,
            "rival_identity_request_id": request_id,
            "episode_key": decision.get("episode_key"),
            "scene_key": decision.get("scene_key"),
            "query": decision.get("query"),
            "request_taxonomy_route": decision.get("request_taxonomy_route"),
            "source_objective": decision.get("objective"),
            "source_action": decision.get("action"),
            "source_reason": decision.get("reason"),
            "planned_target_count": decision.get("planned_target_count"),
            "positive_support_candidate_count": decision.get("positive_support_candidate_count"),
            "evidence_candidate_count": len(evidence),
            "strong_identity_candidate_count": len(strong_ids),
            "strong_identity_candidate_ids": strong_ids,
            "goal_validity_candidate_count": len(validity_ids),
            "goal_validity_candidate_ids": validity_ids,
            "max_own_associated_heading_count": max(
                (safe_int(item.get("post_own_associated_heading_count")) for item in evidence),
                default=0,
            ),
            "max_cross_associated_heading_count": max(
                (safe_int(item.get("post_cross_associated_heading_count")) for item in evidence),
                default=0,
            ),
            "max_identity_margin": max(
                (safe_int(item.get("post_identity_margin")) for item in evidence),
                default=0,
            ),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": False,
            **route,
        }
        output.append(row)
    return output


def summarize(rows: Sequence[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    action_counts = Counter(str(row["revision_action"]) for row in rows)
    branch_counts = Counter(str(row["revision_branch"]) for row in rows)
    request_count = len(rows)
    request_actions = [row for row in rows if str(row["revision_action"]).startswith("request_")]
    commit_allowed = [row for row in rows if row.get("commit_allowed") is True]
    return {
        "schema_version": SCHEMA_VERSION,
        "out_root": str(args.out_root),
        "inputs": {
            "evidence": str(args.evidence),
            "decisions": str(args.decisions),
            "revision_contract": str(args.revision_contract),
        },
        "request_rows": request_count,
        "request_action_rows": len(request_actions),
        "commit_allowed_rows": len(commit_allowed),
        "request_action_rate": ratio(len(request_actions), request_count),
        "revision_action_counts": dict(sorted(action_counts.items())),
        "revision_branch_counts": dict(sorted(branch_counts.items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in rows).items())),
        "source_reason_counts": dict(sorted(Counter(str(row.get("source_reason")) for row in rows).items())),
        "gate": {
            "routes_all_requests": len(rows) == request_count and request_count > 0,
            "terminal_commit_blocked": len(commit_allowed) == 0,
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        },
        "facts": [
            "This router consumes action-time post-observation evidence and strict goal-validity decisions only.",
            "It does not join evaluation labels and does not issue terminal commits.",
            "It maps each unresolved request to the next evidence-acquisition branch required by the revision contract.",
        ],
        "agent_inferences": [
            "A terminal rule cannot be promoted from the current evidence without trading utility for wrong-goal risk.",
            "The next implementation should create branch-specific observations for expanded retrieval, discriminative rival views, and goal-validity confirmation.",
        ],
        "user_decision_needed": None,
        "paper_claim_allowed": False,
        "paper_claim_status": "routing_contract_only_no_terminal_utility_claim",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "output_files": {
            "rows": "goal_validity_revision_v2_routes.jsonl",
            "summary": "goal_validity_revision_v2_router_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = build_rows(load_jsonl(Path(args.evidence)), load_jsonl(Path(args.decisions)))
    summary = summarize(rows, args)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "goal_validity_revision_v2_routes.jsonl", rows)
    write_json(out_root / "goal_validity_revision_v2_router_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Route goal-validity failures to branch-specific next evidence.")
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--revision-contract", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
