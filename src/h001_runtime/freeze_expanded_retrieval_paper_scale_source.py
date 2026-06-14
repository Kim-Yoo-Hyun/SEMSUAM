import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_paper_scale_source.v1"
DEFAULT_CONTRACT_NAME = "expanded_retrieval_paper_scale_v1"
DEFAULT_DATE_FROZEN = "2026-05-27"


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


def canonical_manifest_path(path_text: str) -> str:
    if path_text.startswith("/workspace/"):
        return path_text[len("/workspace/") :]
    return path_text


def request_sort_key(row: Dict[str, Any]) -> Tuple[int, str]:
    request_id = str(row.get("rival_identity_request_id") or "")
    suffix = request_id.split(":")[-1]
    return (int(suffix), request_id) if suffix.isdigit() else (999999, request_id)


def action_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return (str(row.get("episode_key")), str(row.get("query")))


def action_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    output: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        episode_key = row.get("episode_key")
        query = row.get("query")
        if episode_key is None or query is None:
            continue
        output[(str(episode_key), str(query))] = row
    return output


def scene_keys_from_jsonl(path: Optional[Path]) -> List[str]:
    if path is None:
        return []
    return sorted({str(row.get("scene_key")) for row in load_jsonl(path) if row.get("scene_key") is not None})


def contains_gt_action(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            if str(key) == "uses_gt_for_action" and child is True:
                return True
            if contains_gt_action(child):
                return True
    if isinstance(value, list):
        return any(contains_gt_action(item) for item in value)
    return False


def action_forbidden_keys(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend(
            [
                f"row[{index}].{finding}"
                for finding in scan_forbidden_keys(row)
                if finding != "uses_gt_for_analysis"
            ]
        )
    return findings


def build_router_rows(decision_rows: Sequence[Dict[str, Any]], decision_action: str) -> List[Dict[str, Any]]:
    selected = [row for row in decision_rows if row.get("action") == decision_action]
    selected.sort(key=request_sort_key)
    output: List[Dict[str, Any]] = []
    for row in selected:
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "request_taxonomy_route": row.get("request_taxonomy_route"),
                "source_objective": row.get("objective"),
                "source_action": row.get("action"),
                "source_reason": row.get("reason"),
                "source_request_reason": row.get("request_reason"),
                "source_candidate_count": row.get("source_candidate_count"),
                "positive_support_candidate_count": row.get("positive_support_candidate_count"),
                "evidence_candidate_count": row.get("evidence_candidate_count"),
                "strong_identity_candidate_count": row.get("strong_identity_candidate_count"),
                "goal_validity_candidate_count": row.get("goal_validity_candidate_count"),
                "max_own_associated_heading_count": row.get("selected_post_own_associated_heading_count"),
                "max_cross_associated_heading_count": row.get("selected_post_cross_associated_heading_count"),
                "max_identity_margin": row.get("selected_post_identity_margin"),
                "revision_action": "request_expanded_retrieval",
                "revision_branch": "paper_scale_goal_validity_defer_expanded_retrieval",
                "revision_reason": row.get("reason") or "strict_goal_validity_requires_expanded_retrieval",
                "commit_allowed": False,
                "terminal_commit_allowed": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": False,
            }
        )
    return output


def build_source_gate(
    *,
    request_rows: Sequence[Dict[str, Any]],
    matched_action_rows: Sequence[Dict[str, Any]],
    missing_action_rows: Sequence[Dict[str, Any]],
    selected_decision_rows: Sequence[Dict[str, Any]],
    excluded_scenes: Sequence[str],
    ambiguity_summary: Dict[str, Any],
    min_request_rows: int,
    min_scenes: int,
    min_queries: int,
) -> Dict[str, Any]:
    scene_counts = Counter(str(row.get("scene_key")) for row in request_rows)
    query_counts = Counter(str(row.get("query")) for row in request_rows)
    reason_counts = Counter(str(row.get("source_reason")) for row in request_rows)
    overlap = sorted(scene for scene in scene_counts if scene in set(excluded_scenes))
    forbidden = action_forbidden_keys(list(request_rows) + list(selected_decision_rows) + list(matched_action_rows))
    gt_action_rows = [
        str(row.get("episode_key") or f"row[{index}]")
        for index, row in enumerate(list(request_rows) + list(selected_decision_rows) + list(matched_action_rows))
        if contains_gt_action(row)
    ]
    ambiguity_gate = ambiguity_summary.get("gate") or {}
    checks = {
        "ambiguity_contract_gate_passed": bool(ambiguity_gate.get("contract_gate_passed")),
        "ambiguity_contract_allows_larger_source": bool(ambiguity_gate.get("larger_source_allowed_after_contract")),
        "minimum_request_rows": len(request_rows) >= min_request_rows,
        "minimum_request_scenes": len(scene_counts) >= min_scenes,
        "minimum_request_queries": len(query_counts) >= min_queries,
        "missing_action_evidence_rows": len(missing_action_rows) == 0,
        "excluded_scene_overlap": len(overlap) == 0,
        "action_evidence_forbidden_key_count": len(forbidden) == 0,
        "no_gt_for_action": len(gt_action_rows) == 0,
    }
    paper_scale_checks = {
        "minimum_request_rows": len(request_rows) >= 20,
        "minimum_request_scenes": len(scene_counts) >= 5,
        "minimum_request_queries": len(query_counts) >= 3,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "required": {
            "minimum_request_rows": min_request_rows,
            "minimum_request_scenes": min_scenes,
            "minimum_request_queries": min_queries,
            "excluded_scene_overlap": 0,
            "action_evidence_forbidden_key_count": 0,
            "uses_gt_for_action": False,
        },
        "request_rows": len(request_rows),
        "request_scenes": len(scene_counts),
        "request_queries": len(query_counts),
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "source_reason_counts": dict(sorted(reason_counts.items())),
        "excluded_scene_overlap": overlap,
        "missing_action_evidence_rows": [
            {
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "query": row.get("query"),
            }
            for row in missing_action_rows
        ],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "gt_action_rows": gt_action_rows[:50],
        "paper_scale_gate": {
            "passed": all(paper_scale_checks.values()),
            "checks": paper_scale_checks,
            "required": {
                "minimum_request_rows": 20,
                "minimum_request_scenes": 5,
                "minimum_request_queries": 3,
            },
        },
    }


def build_manifest(args: argparse.Namespace, source_summary: Dict[str, Any]) -> Dict[str, Any]:
    gate = source_summary["source_freeze_gate"]
    expected_rows = int(source_summary["request_rows"])
    min_candidates = int(args.min_candidates_per_request)
    max_candidates = int(args.max_candidates_per_request)
    return {
        "schema_version": "h001.expanded_retrieval_branch_contract.v1",
        "contract_name": str(args.contract_name),
        "date_frozen": str(args.date_frozen),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "frozen_paper_scale_source" if gate["passed"] else "draft_failed_source_freeze_gate",
        "source": {
            "router_output": canonical_manifest_path(str(Path(args.out_root) / "expanded_retrieval_paper_scale_source_rows.jsonl")),
            "source_filter": {"source_action": str(args.decision_action)},
            "expected_request_rows": expected_rows,
            "source_decisions": canonical_manifest_path(str(args.decisions)),
            "source_evidence": canonical_manifest_path(str(args.evidence)),
            "source_action_evidence": canonical_manifest_path(str(args.action_evidence_rows)),
            "source_candidate_artifact": canonical_manifest_path(str(args.source_candidate_artifact)),
            "source_rows": canonical_manifest_path(str(Path(args.out_root) / "expanded_retrieval_paper_scale_source_rows.jsonl")),
            "source_summary": canonical_manifest_path(str(Path(args.out_root) / "source_summary.json")),
        },
        "motivation": {
            "facts": [
                "The ambiguity-aware expanded-retrieval objective contract passed on the smaller fresh diagnostic source.",
                "This manifest freezes nonterminal strict goal-validity decisions whose next action is expanded retrieval.",
                "Terminal commitment remains disabled in this paper-scale source contract.",
            ],
            "agent_inference": [
                "The larger source tests whether ambiguity routing scales beyond the small fresh diagnostic source.",
                "This is a source-freeze and planner-compatibility gate, not a terminal ObjectNav utility claim.",
            ],
        },
        "action_inputs_allowed": [
            "strict goal-validity nonterminal decision fields",
            "action-time candidate evidence fields",
            "semantic score/rank fields",
            "candidate position and visit_position fields",
            "non-GT reachability or navmesh-derived feasibility fields available before evaluation labels",
        ],
        "action_inputs_forbidden": [
            "candidate_correct",
            "selected_for_goal",
            "wrong_goal_visit",
            "success labels",
            "post-hoc GT object ids",
            "evaluation labels",
            "threshold tuning from joined labels",
        ],
        "branch_contract": {
            "planner_name": "expanded_retrieval_branch_v1",
            "candidate_budget": {
                "min_candidates_per_request": min_candidates,
                "max_candidates_per_request": max_candidates,
                "selection_modes": [
                    "semantic_rank_band",
                    "spatial_diversity",
                    "reachability_available_before_labels",
                ],
            },
            "required_outputs": [
                "expanded_retrieval_plan.jsonl",
                "expanded_retrieval_candidate_set.jsonl",
                "expanded_retrieval_summary.json",
            ],
            "terminal_commit_allowed": False,
            "paper_claim_allowed": False,
        },
        "diagnostic_gates": {
            "source_gate": {
                "request_rows_min": int(args.min_request_rows),
                "action_evidence_forbidden_key_count": 0,
                "uses_gt_for_action": False,
            },
            "candidate_set_gate": {
                "expanded_candidate_rows_min": expected_rows * min_candidates,
                "expanded_candidates_per_request_min": min_candidates,
                "duplicate_candidate_id_rate_max": 0.05,
                "nonfinite_position_rate_max": 0.05,
                "uses_gt_for_action": False,
            },
            "paper_scale_gate": gate["paper_scale_gate"],
        },
        "next_steps": [
            "run expanded retrieval planner on this frozen source",
            "run source-pool validity proxy on the frozen candidate set",
            "build projection-anchor detector observation plan only for detector-eligible rows",
            "run fixed-anchor detector/SAM2 substrate without using evaluation labels for action",
        ],
        "interpretation": {
            "fact": "This contract freezes paper-scale branch rows after the ambiguity-aware objective contract passed.",
            "agent_inference": (
                "A planner-compatible result can validate whether expanded retrieval has enough scene-diverse "
                "nonterminal evidence for detector observation planning, but paper-facing ObjectNav utility "
                "remains blocked."
            ),
            "paper_claim_status": "not_allowed_until_larger_source_detector_and_objective_validation_pass",
        },
        "source_freeze_gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def verify_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    gate = dict(manifest.get("source_freeze_gate") or {})
    return {
        "ok": manifest.get("status") == "frozen_paper_scale_source" and bool(gate.get("passed")),
        "contract_name": manifest.get("contract_name"),
        "status": manifest.get("status"),
        "request_rows": gate.get("request_rows"),
        "request_scenes": gate.get("request_scenes"),
        "request_queries": gate.get("request_queries"),
        "source_freeze_gate_passed": gate.get("passed"),
        "paper_scale_gate_passed": (gate.get("paper_scale_gate") or {}).get("passed"),
        "uses_gt_for_action": manifest.get("uses_gt_for_action"),
        "paper_claim_allowed": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    decisions = load_jsonl(Path(args.decisions))
    router_rows = build_router_rows(decisions, str(args.decision_action))
    action_rows = load_jsonl(Path(args.action_evidence_rows))
    actions_by_key = action_index(action_rows)
    selected_decisions_by_key = {action_key(row): row for row in decisions if row.get("action") == args.decision_action}
    matched_action_rows: List[Dict[str, Any]] = []
    missing_action_rows: List[Dict[str, Any]] = []
    for row in router_rows:
        action = actions_by_key.get(action_key(row))
        if action is None:
            missing_action_rows.append(row)
        else:
            matched_action_rows.append(action)
    selected_decisions = [selected_decisions_by_key[action_key(row)] for row in router_rows if action_key(row) in selected_decisions_by_key]
    excluded_scenes = scene_keys_from_jsonl(Path(args.exclude_scenes_from_jsonl)) if args.exclude_scenes_from_jsonl else []
    ambiguity_summary = load_json(Path(args.ambiguity_contract_summary))
    source_gate = build_source_gate(
        request_rows=router_rows,
        matched_action_rows=matched_action_rows,
        missing_action_rows=missing_action_rows,
        selected_decision_rows=selected_decisions,
        excluded_scenes=excluded_scenes,
        ambiguity_summary=ambiguity_summary,
        min_request_rows=int(args.min_request_rows),
        min_scenes=int(args.min_scenes),
        min_queries=int(args.min_queries),
    )
    source_summary = {
        "schema_version": SCHEMA_VERSION,
        "contract_name": str(args.contract_name),
        "out_root": str(args.out_root),
        "decisions": canonical_manifest_path(str(args.decisions)),
        "evidence": canonical_manifest_path(str(args.evidence)),
        "action_evidence_rows": canonical_manifest_path(str(args.action_evidence_rows)),
        "source_candidate_artifact": canonical_manifest_path(str(args.source_candidate_artifact)),
        "ambiguity_contract_summary": canonical_manifest_path(str(args.ambiguity_contract_summary)),
        "excluded_scene_source": canonical_manifest_path(str(args.exclude_scenes_from_jsonl))
        if args.exclude_scenes_from_jsonl
        else None,
        "decision_action_filter": str(args.decision_action),
        "request_rows": len(router_rows),
        "request_scenes": len({row.get("scene_key") for row in router_rows}),
        "request_queries": len({row.get("query") for row in router_rows}),
        "scene_counts": dict(sorted(Counter(str(row.get("scene_key")) for row in router_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in router_rows).items())),
        "source_freeze_gate": source_gate,
        "source_freeze_gate_passed": source_gate["passed"],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "source_rows": "expanded_retrieval_paper_scale_source_rows.jsonl",
            "source_summary": "source_summary.json",
        },
    }
    manifest = build_manifest(args, source_summary)
    verify = verify_manifest(manifest)
    out_root = Path(args.out_root)
    write_jsonl(out_root / "expanded_retrieval_paper_scale_source_rows.jsonl", router_rows)
    write_json(out_root / "source_summary.json", source_summary)
    write_json(Path(args.out_manifest), manifest)
    write_json(Path(args.verify_out), verify)
    return {
        "source_summary": source_summary,
        "manifest": canonical_manifest_path(str(args.out_manifest)),
        "verify": verify,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze an H001 expanded-retrieval paper-scale source.")
    parser.add_argument("--contract-name", default=DEFAULT_CONTRACT_NAME)
    parser.add_argument("--date-frozen", default=DEFAULT_DATE_FROZEN)
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--action-evidence-rows", required=True)
    parser.add_argument("--source-candidate-artifact", required=True)
    parser.add_argument("--ambiguity-contract-summary", required=True)
    parser.add_argument("--exclude-scenes-from-jsonl")
    parser.add_argument("--decision-action", default="defer_expanded_retrieval_needed")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--verify-out", required=True)
    parser.add_argument("--min-request-rows", type=int, default=20)
    parser.add_argument("--min-scenes", type=int, default=5)
    parser.add_argument("--min-queries", type=int, default=3)
    parser.add_argument("--min-candidates-per-request", type=int, default=6)
    parser.add_argument("--max-candidates-per-request", type=int, default=10)
    return parser.parse_args()


def main() -> None:
    result = run(parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["verify"]["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
