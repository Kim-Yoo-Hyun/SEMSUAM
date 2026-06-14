import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.expanded_retrieval_validation_source.v1"
DEFAULT_CONTRACT_NAME = "expanded_retrieval_fresh_validation_v1"
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
    if path_text.startswith("/runs/"):
        return "local_dataset/runs/" + path_text[len("/runs/") :]
    if path_text.startswith("/workspace/"):
        return path_text[len("/workspace/") :]
    return path_text


def count_unique(rows: Sequence[Dict[str, Any]], key: str) -> int:
    return len({str(row.get(key)) for row in rows if row.get(key) is not None})


def request_id_sort_key(row: Dict[str, Any]) -> Tuple[int, str]:
    request_id = str(row.get("rival_identity_request_id") or "")
    suffix = request_id.split(":")[-1]
    return (int(suffix), request_id) if suffix.isdigit() else (999999, request_id)


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


def nested_gt_action_rows(rows: Sequence[Dict[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        if contains_gt_action(row):
            findings.append(str(row.get("episode_key") or f"row[{index}]"))
    return findings


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
        findings.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    return findings


def gate_pass(summary: Dict[str, Any], *path: str) -> bool:
    value: Any = summary
    for item in path:
        if not isinstance(value, dict):
            return False
        value = value.get(item)
    return bool(value)


def build_source_gate(
    *,
    request_rows: Sequence[Dict[str, Any]],
    matched_action_rows: Sequence[Dict[str, Any]],
    missing_action_rows: Sequence[Dict[str, Any]],
    excluded_scenes: Sequence[str],
    fixed_anchor_summary: Dict[str, Any],
    source_detector_summary: Dict[str, Any],
    post_observation_summary: Dict[str, Any],
    min_request_rows: int,
    min_scenes: int,
    min_queries: int,
) -> Dict[str, Any]:
    scene_counts = Counter(str(row.get("scene_key")) for row in request_rows)
    query_counts = Counter(str(row.get("query")) for row in request_rows)
    action_counts = Counter(str(row.get("revision_action")) for row in request_rows)
    overlap = sorted(scene for scene in scene_counts if scene in set(excluded_scenes))
    forbidden = action_forbidden_keys(matched_action_rows)
    gt_action_rows = nested_gt_action_rows(list(request_rows) + list(matched_action_rows))
    checks = {
        "fixed_anchor_detector_substrate_gate_passed": gate_pass(
            fixed_anchor_summary, "gate", "passes_detector_substrate_gate"
        ),
        "source_detector_substrate_gate_passed": gate_pass(
            source_detector_summary, "gate", "passes_detector_substrate_gate"
        ),
        "source_post_observation_gate_passed": gate_pass(
            post_observation_summary, "gates", "post_observation_gate_passed"
        ),
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
        "revision_action_counts": dict(sorted(action_counts.items())),
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
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


def build_manifest(
    *,
    args: argparse.Namespace,
    source_summary: Dict[str, Any],
) -> Dict[str, Any]:
    expected_rows = int(source_summary["request_rows"])
    min_candidates = int(args.min_candidates_per_request)
    max_candidates = int(args.max_candidates_per_request)
    return {
        "schema_version": "h001.expanded_retrieval_branch_contract.v1",
        "contract_name": str(args.contract_name),
        "date_frozen": str(args.date_frozen),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "frozen_after_fixed_anchor_detector_gate"
        if source_summary["source_freeze_gate"]["passed"]
        else "draft_failed_source_freeze_gate",
        "source": {
            "router_output": canonical_manifest_path(str(args.router_rows)),
            "source_filter": {"revision_action": "request_expanded_retrieval"},
            "expected_request_rows": expected_rows,
            "source_evidence": canonical_manifest_path(str(args.source_post_observation_evidence)),
            "source_action_evidence": canonical_manifest_path(str(args.action_evidence_rows)),
            "source_candidate_artifact": canonical_manifest_path(str(args.source_candidate_artifact)),
            "source_rows": canonical_manifest_path(
                str(Path(args.out_root) / "expanded_retrieval_fresh_validation_source_rows.jsonl")
            ),
            "source_summary": canonical_manifest_path(str(Path(args.out_root) / "source_summary.json")),
        },
        "motivation": {
            "facts": [
                "The projection-anchor expanded-retrieval detector substrate passes on the earlier diagnostic branch.",
                "This manifest freezes a scene-disjoint fresh/predeclared branch source before running detector evidence on it.",
                "Terminal commitment remains disallowed in this source contract.",
            ],
            "agent_inference": [
                "The branch should next be validated on a source not used to repair the projection-anchor detector substrate.",
                "This source is sufficient for a branch-level detector substrate validation, but not a paper-scale utility claim by itself.",
            ],
        },
        "action_inputs_allowed": [
            "router rows with revision_action == request_expanded_retrieval",
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
            "paper_scale_gate": source_summary["source_freeze_gate"]["paper_scale_gate"],
        },
        "next_steps": [
            "run expanded retrieval planner on this frozen source",
            "run source-pool validity proxy on the frozen candidate set",
            "build projection-anchor detector observation plan only for detector-eligible rows",
            "run fixed-anchor detector/SAM2 substrate without using evaluation labels for action",
        ],
        "interpretation": {
            "fact": "This contract freezes branch rows after the diagnostic projection-anchor detector gate passed.",
            "agent_inference": (
                "A branch-level substrate result on this source can validate whether the fixed-anchor detector repair "
                "generalizes beyond the original diagnostic rows, but paper-facing ObjectNav utility remains blocked."
            ),
            "paper_claim_status": "not_allowed_until_fresh_branch_detector_and_objective_validation_pass",
        },
        "source_freeze_gate": source_summary["source_freeze_gate"],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def verify_manifest(manifest: Dict[str, Any]) -> Dict[str, Any]:
    gate = dict(manifest.get("source_freeze_gate") or {})
    status = manifest.get("status")
    return {
        "ok": status == "frozen_after_fixed_anchor_detector_gate" and bool(gate.get("passed")),
        "contract_name": manifest.get("contract_name"),
        "status": status,
        "request_rows": gate.get("request_rows"),
        "request_scenes": gate.get("request_scenes"),
        "request_queries": gate.get("request_queries"),
        "source_freeze_gate_passed": gate.get("passed"),
        "paper_scale_gate_passed": (gate.get("paper_scale_gate") or {}).get("passed"),
        "uses_gt_for_action": manifest.get("uses_gt_for_action"),
        "paper_claim_allowed": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    router_rows_all = load_jsonl(Path(args.router_rows))
    request_rows = [
        row for row in router_rows_all if row.get("revision_action") == "request_expanded_retrieval"
    ]
    request_rows.sort(key=request_id_sort_key)
    action_rows = load_jsonl(Path(args.action_evidence_rows))
    actions_by_key = action_index(action_rows)
    matched_action_rows: List[Dict[str, Any]] = []
    missing_action_rows: List[Dict[str, Any]] = []
    for row in request_rows:
        key = (str(row.get("episode_key")), str(row.get("query")))
        action = actions_by_key.get(key)
        if action is None:
            missing_action_rows.append(row)
        else:
            matched_action_rows.append(action)

    fixed_anchor_summary = load_json(Path(args.fixed_anchor_detector_summary))
    source_detector_summary = load_json(Path(args.source_detector_summary))
    post_observation_summary = load_json(Path(args.source_post_observation_summary))
    excluded_scenes = scene_keys_from_jsonl(Path(args.exclude_scenes_from_jsonl)) if args.exclude_scenes_from_jsonl else []
    source_gate = build_source_gate(
        request_rows=request_rows,
        matched_action_rows=matched_action_rows,
        missing_action_rows=missing_action_rows,
        excluded_scenes=excluded_scenes,
        fixed_anchor_summary=fixed_anchor_summary,
        source_detector_summary=source_detector_summary,
        post_observation_summary=post_observation_summary,
        min_request_rows=args.min_request_rows,
        min_scenes=args.min_scenes,
        min_queries=args.min_queries,
    )
    source_summary = {
        "schema_version": SCHEMA_VERSION,
        "contract_name": str(args.contract_name),
        "out_root": str(args.out_root),
        "router_rows": canonical_manifest_path(str(args.router_rows)),
        "router_summary": canonical_manifest_path(str(args.router_summary)),
        "source_post_observation_evidence": canonical_manifest_path(str(args.source_post_observation_evidence)),
        "source_post_observation_summary": canonical_manifest_path(str(args.source_post_observation_summary)),
        "action_evidence_rows": canonical_manifest_path(str(args.action_evidence_rows)),
        "source_candidate_artifact": canonical_manifest_path(str(args.source_candidate_artifact)),
        "fixed_anchor_detector_summary": canonical_manifest_path(str(args.fixed_anchor_detector_summary)),
        "source_detector_summary": canonical_manifest_path(str(args.source_detector_summary)),
        "excluded_scene_source": canonical_manifest_path(str(args.exclude_scenes_from_jsonl))
        if args.exclude_scenes_from_jsonl
        else None,
        "request_rows": len(request_rows),
        "request_scenes": count_unique(request_rows, "scene_key"),
        "request_queries": count_unique(request_rows, "query"),
        "scene_counts": dict(sorted(Counter(str(row.get("scene_key")) for row in request_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in request_rows).items())),
        "source_freeze_gate": source_gate,
        "source_freeze_gate_passed": source_gate["passed"],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "source_rows": "expanded_retrieval_fresh_validation_source_rows.jsonl",
            "source_summary": "source_summary.json",
        },
    }
    manifest = build_manifest(args=args, source_summary=source_summary)
    verify = verify_manifest(manifest)

    out_root = Path(args.out_root)
    write_jsonl(out_root / "expanded_retrieval_fresh_validation_source_rows.jsonl", request_rows)
    write_json(out_root / "source_summary.json", source_summary)
    write_json(Path(args.out_manifest), manifest)
    write_json(Path(args.verify_out), verify)
    return {
        "source_summary": source_summary,
        "manifest": canonical_manifest_path(str(args.out_manifest)),
        "verify": verify,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze an H001 expanded-retrieval fresh validation source.")
    parser.add_argument("--contract-name", default=DEFAULT_CONTRACT_NAME)
    parser.add_argument("--date-frozen", default=DEFAULT_DATE_FROZEN)
    parser.add_argument("--router-rows", required=True)
    parser.add_argument("--router-summary", required=True)
    parser.add_argument("--source-post-observation-evidence", required=True)
    parser.add_argument("--source-post-observation-summary", required=True)
    parser.add_argument("--action-evidence-rows", required=True)
    parser.add_argument("--source-candidate-artifact", required=True)
    parser.add_argument("--fixed-anchor-detector-summary", required=True)
    parser.add_argument("--source-detector-summary", required=True)
    parser.add_argument("--exclude-scenes-from-jsonl")
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--verify-out", required=True)
    parser.add_argument("--min-request-rows", type=int, default=6)
    parser.add_argument("--min-scenes", type=int, default=2)
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
