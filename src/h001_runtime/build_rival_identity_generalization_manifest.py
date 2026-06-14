import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from h001_runtime.analyze_dense_conflict_rival_identity_policy import (
    action_forbidden_keys,
    rival_identity_confirmation_policy,
)


SCHEMA_VERSION = "h001.rival_identity_generalization_contract.v1"
POLICY_NAME = "rival_identity_confirmation_v1"
CONTRACT_NAME = "rival_identity_generalization_v1"
DEFAULT_EXCLUDED_SCENES = ["DYehNKdT76V", "7MXmsvcQjpJ", "y9hTuugGdiq"]

SOURCE_FREEZE_GATE = {
    "minimum_request_rows": 6,
    "minimum_request_scenes": 3,
    "minimum_request_queries": 2,
    "excluded_scene_overlap": 0,
    "action_evidence_forbidden_key_count": 0,
}


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


def request_row_from_decision(action_row: Dict[str, Any], decision: Dict[str, Any], role: str) -> Dict[str, Any]:
    return {
        "role": role,
        "episode_key": str(action_row.get("episode_key")),
        "scene_key": str(action_row.get("scene_key")),
        "query": str(action_row.get("query")),
        "request_reason": str(decision.get("reason")),
        "focus_candidate_id": decision.get("selected_candidate_id"),
        "rival_candidate_ids": [str(candidate_id) for candidate_id in decision.get("rival_candidate_ids") or []],
    }


def source_row(action_row: Dict[str, Any], decision: Dict[str, Any], role: str) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_name": CONTRACT_NAME,
        "policy_name": POLICY_NAME,
        "role": role,
        "episode_key": action_row.get("episode_key"),
        "scene_key": action_row.get("scene_key"),
        "scene_id": action_row.get("scene_id"),
        "query": action_row.get("query"),
        "source_manifest_split": action_row.get("source_manifest_split"),
        "evidence_status": action_row.get("evidence_status"),
        "candidate_count": action_row.get("candidate_count"),
        "positive_support_candidate_count": action_row.get("positive_support_candidate_count"),
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "selected_candidate_id": decision.get("selected_candidate_id"),
        "rival_candidate_ids": list(decision.get("rival_candidate_ids") or []),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
    }


def source_freeze_gate(
    request_rows: Sequence[Dict[str, Any]],
    forbidden: Sequence[str],
    excluded_scenes: Sequence[str],
    action_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    scene_counts = Counter(str(row.get("scene_key")) for row in request_rows)
    query_counts = Counter(str(row.get("query")) for row in request_rows)
    overlap = sorted(scene for scene in scene_counts if scene in set(excluded_scenes))
    gt_action_rows = [str(row.get("episode_key")) for row in action_rows if contains_gt_action_flag(row)]
    checks = {
        "minimum_request_rows": len(request_rows) >= SOURCE_FREEZE_GATE["minimum_request_rows"],
        "minimum_request_scenes": len(scene_counts) >= SOURCE_FREEZE_GATE["minimum_request_scenes"],
        "minimum_request_queries": len(query_counts) >= SOURCE_FREEZE_GATE["minimum_request_queries"],
        "excluded_scene_overlap": len(overlap) == SOURCE_FREEZE_GATE["excluded_scene_overlap"],
        "action_evidence_forbidden_key_count": len(forbidden)
        == SOURCE_FREEZE_GATE["action_evidence_forbidden_key_count"],
        "no_gt_for_action": len(gt_action_rows) == 0,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "required": dict(SOURCE_FREEZE_GATE),
        "request_rows": len(request_rows),
        "request_scenes": len(scene_counts),
        "request_queries": len(query_counts),
        "excluded_scene_overlap": overlap,
        "gt_action_rows": gt_action_rows[:20],
        "scene_counts": dict(sorted(scene_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "action_evidence_forbidden_key_count": len(forbidden),
    }


def build_contract(
    *,
    args: argparse.Namespace,
    request_rows: Sequence[Dict[str, Any]],
    source_summary: Dict[str, Any],
) -> Dict[str, Any]:
    action_path = canonical_manifest_path(str(args.action_evidence))
    labels_path = canonical_manifest_path(str(args.evaluation_labels))
    guard_path = canonical_manifest_path(str(args.guard_config))
    return {
        "schema_version": SCHEMA_VERSION,
        "date_frozen": str(args.date_frozen),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "contract_name": CONTRACT_NAME,
        "manifest_status": "frozen" if source_summary["source_freeze_gate"]["passed"] else "draft_failed_source_freeze_gate",
        "policy_source": {
            "policy_name": POLICY_NAME,
            "policy_description": (
                "Apply the frozen rival-identity action rule to the frozen dense_conflict_generalization_v1 "
                "primary action evidence and select only action-time request rows."
            ),
            "source_action_evidence": action_path,
            "guard_config": guard_path,
            "design_source": "local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1",
            "excluded_scenes": list(args.exclude_scene),
            "selection_rule": (
                "Run the fixed action policy, exclude prior diagnostic scenes, keep rows whose action is "
                "request_rival_identity_confirmation, and never join evaluation labels during selection."
            ),
            "diagnostic_result": {
                "source_freeze_gate_passed": source_summary["source_freeze_gate"]["passed"],
                "request_rows": source_summary["request_rows"],
                "request_scenes": source_summary["request_scenes"],
                "request_queries": source_summary["request_queries"],
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
            "guard_config": guard_path,
        },
        "observation_contract": {
            "planner_name": "rival_identity_pair_probe_v1",
            "purpose": "Convert dense same-category rival ambiguity into active re-observation evidence on a fresh source.",
            "allowed_action_time_inputs": [
                "candidate_id",
                "query",
                "scene_key",
                "episode_key",
                "candidate position",
                "candidate visit_position",
                "semantic_rank",
                "semantic_score",
                "support_score",
                "detector_score_max",
                "associated_heading_count",
                "mask_hit_count",
                "box_hit_count",
                "visible_count",
                "min_depth_error_m",
                "positive_support",
                "request_reason",
                "rival_candidate_ids",
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
                "include_semantic_or_support_rivals_for_unique_guard_candidate": True,
                "max_rivals_per_request": 4,
                "max_target_candidates_per_request": 5,
                "deduplicate_candidate_ids": True,
            },
            "viewpoint_policy": {
                "minimum": (
                    "Use each target candidate's non-GT visit_position if available and render a heading toward "
                    "the target candidate position."
                ),
                "preferred": (
                    "Choose pair-probe viewpoints that can observe both focus and rival candidates when their "
                    "visit_position/position geometry supports it."
                ),
                "fallback": "Render candidate-centric observations for focus and each rival separately.",
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
            "scope": "fresh_predeclared_validation_source",
            "minimum_plan_gate": {
                "request_rows": len(request_rows),
                "primary_request_rows": len(request_rows),
                "secondary_stress_request_rows": 0,
                "planned_rows_minimum": len(request_rows),
                "action_evidence_forbidden_key_count": 0,
            },
            "detector_substrate_gate": {
                "detector_box_rate_minimum": 0.80,
                "sam2_mask_rate_minimum": 0.80,
                "candidate_association_rate_minimum": 0.50,
                "if_failed": "classify as observation/detector substrate failure, not arbitration failure",
            },
            "post_observation_gate": {
                "wrong_goal_commit_rows": 0,
                "no_label_commit_rows": 0,
                "new_primary_success_commit_rows_minimum": 1,
                "resolved_request_rows_minimum": 1,
                "secondary_stress_wrong_goal_commit_rows": 0,
            },
            "required_baselines": [
                "strict_depth_consistency_v1",
                "rival_identity_confirmation_v1_without_observation",
                "support_margin_only",
                "depth_margin_only",
                "semantic_top_only",
                "defer_all_ambiguous",
            ],
            "metrics": [
                "wrong_goal_commit_rows",
                "success_commit_rows",
                "request_identity_confirmation_rows",
                "resolved_request_rows",
                "new_success_commit_rows_from_request",
                "detector_box_rate",
                "sam2_mask_rate",
                "candidate_association_rate",
                "no_label_commit_rows",
            ],
        },
        "source_freeze_gate": source_summary["source_freeze_gate"],
        "failure_taxonomy": {
            "observation_plan_missing_target": "The planner fails to create observations for focus or rival candidates using non-GT candidate geometry.",
            "detector_substrate_failure": "Rendered observations exist but detector/mask/association evidence is insufficient.",
            "identity_evidence_non_discriminative": "Post-observation evidence remains saturated across same-category rivals.",
            "unsafe_post_observation_commit": "The post-observation rule commits to a wrong candidate.",
            "safe_but_inert": "The rule avoids wrong commits but resolves no request rows.",
            "label_plumbing_failure": "A committed candidate has no evaluation label; fix evaluation join before interpreting results.",
            "source_independence_violation": "The contract is changed or tuned using evaluation labels from this source.",
        },
        "interpretation": {
            "fact": (
                "This contract freezes request rows from primary action evidence before observation planning, frame "
                "rendering, detector association, or label evaluation."
            ),
            "agent_inference": (
                "Passing this source-freeze gate makes the next useful step a Docker plan smoke on a fresh "
                "predeclared source, followed by frame export and detector/SAM2 association."
            ),
            "paper_claim_status": "not_allowed_until_actual_observation_and_detector_validated_post_observation_result",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
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
        "duplicate_episode_keys": duplicate_episode_keys,
        "source_freeze_gate": gate,
        "uses_gt_for_action": contract.get("uses_gt_for_action"),
        "paper_claim_allowed": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    action_rows = load_jsonl(Path(args.action_evidence))
    guard = dict(load_json(Path(args.guard_config)).get("params") or {})
    forbidden = action_forbidden_keys(action_rows)
    excluded = set(str(scene) for scene in args.exclude_scene)
    request_rows: List[Dict[str, Any]] = []
    selected_source_rows: List[Dict[str, Any]] = []
    all_policy_rows: List[Dict[str, Any]] = []

    for action_row in action_rows:
        decision = rival_identity_confirmation_policy(action_row, guard)
        row = source_row(action_row, decision, "primary")
        all_policy_rows.append(row)
        if str(action_row.get("scene_key")) in excluded:
            continue
        if decision.get("action") != "request_rival_identity_confirmation":
            continue
        request_rows.append(request_row_from_decision(action_row, decision, "primary"))
        selected_source_rows.append(row)

    gate = source_freeze_gate(request_rows, forbidden, args.exclude_scene, action_rows)
    source_summary = {
        "schema_version": SCHEMA_VERSION,
        "contract_name": CONTRACT_NAME,
        "source_action_evidence": canonical_manifest_path(str(args.action_evidence)),
        "guard_config": canonical_manifest_path(str(args.guard_config)),
        "out_root": str(args.out_root),
        "source_rows": len(action_rows),
        "policy_rows": len(all_policy_rows),
        "request_rows": len(request_rows),
        "request_scenes": count_unique(request_rows, "scene_key"),
        "request_queries": count_unique(request_rows, "query"),
        "excluded_scenes": list(args.exclude_scene),
        "action_counts": dict(sorted(Counter(str(row.get("action")) for row in all_policy_rows).items())),
        "reason_counts": dict(sorted(Counter(str(row.get("reason")) for row in all_policy_rows).items())),
        "request_reason_counts": dict(sorted(Counter(str(row.get("request_reason")) for row in request_rows).items())),
        "scene_counts": dict(sorted(Counter(str(row.get("scene_key")) for row in request_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in request_rows).items())),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": list(forbidden)[:50],
        "source_freeze_gate": gate,
        "source_freeze_gate_passed": gate["passed"],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "selected_source_rows": "rival_identity_generalization_source_rows.jsonl",
            "all_policy_rows": "rival_identity_generalization_policy_rows.jsonl",
            "summary": "source_summary.json",
        },
    }
    contract = build_contract(args=args, request_rows=request_rows, source_summary=source_summary)
    verify = verify_contract(contract)

    out_root = Path(args.out_root)
    write_jsonl(out_root / "rival_identity_generalization_source_rows.jsonl", selected_source_rows)
    write_jsonl(out_root / "rival_identity_generalization_policy_rows.jsonl", all_policy_rows)
    write_json(out_root / "source_summary.json", source_summary)
    write_json(Path(args.out_manifest), contract)
    write_json(Path(args.verify_out), verify)
    return {"manifest": str(args.out_manifest), "verify": str(args.verify_out), "source_summary": source_summary, "verify_summary": verify}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Freeze H001 rival-identity fresh generalization source manifest.")
    parser.add_argument("--action-evidence", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--guard-config", required=True)
    parser.add_argument("--out-manifest", required=True)
    parser.add_argument("--verify-out", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--exclude-scene", action="append", default=list(DEFAULT_EXCLUDED_SCENES))
    parser.add_argument("--date-frozen", default="2026-05-26")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
