import argparse
import json
from pathlib import Path
from typing import Any, Dict, Mapping


SCHEMA_VERSION = "h001.rival_contradiction_region_contamination_multi_case_diagnostic_report.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_rival_contradiction_region_contamination_multi_case_diagnostic_report_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_rival_contradiction_region_contamination_multi_case_diagnostic_report_v1"
)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def bool_field(payload: Mapping[str, Any], key: str) -> bool:
    return bool(payload.get(key))


def count_blocker(summary: Mapping[str, Any], key: str, expected: Any) -> str:
    actual = summary.get(key)
    return "" if actual == expected else f"{key}: expected {expected}, got {actual}"


def min_blocker(summary: Mapping[str, Any], key: str, expected_min: int) -> str:
    actual = summary.get(key)
    if isinstance(actual, (int, float)) and actual >= expected_min:
        return ""
    return f"{key}: expected >= {expected_min}, got {actual}"


def report_gate(
    contract: Mapping[str, Any],
    source: Mapping[str, Any],
    frame_plan: Mapping[str, Any],
    frame_export: Mapping[str, Any],
    projection: Mapping[str, Any],
    detector: Mapping[str, Any],
    evidence: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    promotion: Mapping[str, Any],
) -> Dict[str, Any]:
    expected = contract["expected_report_counts"]
    blockers = [
        count_blocker(source, "source_rows", expected["source_pair_rows"]),
        count_blocker(source, "scene_count", expected["scene_count"]),
        count_blocker(source, "query_count", expected["query_count"]),
        count_blocker(source, "observation_plan_seed_rows", expected["observation_seed_rows"]),
        count_blocker(frame_plan, "frame_plan_rows", expected["frame_plan_rows"]),
        count_blocker(frame_export, "rows_exported", expected["rendered_frame_rows"]),
        count_blocker(projection, "projection_anchor_visible_rows", expected["projection_visible_rows"]),
        count_blocker(detector, "frame_rows", expected["detector_frame_rows"]),
        min_blocker(detector, "associated_decision_rows", expected["detector_associated_decision_rows_min"]),
        min_blocker(detector, "association_rows", expected["detector_association_rows_min"]),
        count_blocker(evidence, "pair_rows", expected["detector_evidence_pair_rows"]),
        count_blocker(evaluation, "pair_rows", expected["evaluation_pair_rows"]),
        count_blocker(promotion, "contamination_or_contradiction_pair_rows", expected["contamination_or_contradiction_pair_rows"]),
        count_blocker(promotion, "wrong_labeled_pair_rows", expected["wrong_labeled_pair_rows"]),
        count_blocker(
            promotion,
            "wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence",
            expected["wrong_labeled_contamination_or_contradiction_pair_rows"],
        ),
        count_blocker(promotion, "total_wrong_goal_baseline_rows", expected["total_wrong_goal_baseline_rows"]),
        count_blocker(promotion, "slam_map_pose_delta_rows", expected["slam_map_pose_delta_rows"]),
        count_blocker(promotion, "promotion_ready_rows", expected["promotion_ready_rows"]),
        count_blocker(source, "terminal_commit_rows", expected["terminal_commit_rows"]),
        count_blocker(evidence, "terminal_commit_rows", expected["terminal_commit_rows"]),
        count_blocker(evaluation, "terminal_commit_rows", expected["terminal_commit_rows"]),
        count_blocker(source, "candidate_commit_rows", expected["candidate_commit_rows"]),
        count_blocker(evidence, "candidate_commit_rows", expected["candidate_commit_rows"]),
        count_blocker(evaluation, "candidate_commit_rows", expected["candidate_commit_rows"]),
        count_blocker(source, "candidate_rejection_rows", expected["candidate_rejection_rows"]),
        count_blocker(evidence, "candidate_rejection_rows", expected["candidate_rejection_rows"]),
        count_blocker(evaluation, "candidate_rejection_rows", expected["candidate_rejection_rows"]),
        count_blocker(source, "uses_gt_for_action_true_rows", 0),
        "" if bool_field(promotion, "promotion_gate_passed") else "promotion_gate_passed: expected true",
        "" if not bool_field(promotion, "terminal_selector_allowed_after_pass") else "terminal_selector_allowed_after_pass: expected false",
        "" if not bool_field(promotion, "paper_claim_allowed_after_pass") else "paper_claim_allowed_after_pass: expected false",
        "" if not bool_field(evaluation, "paper_claim_allowed") else "evaluation paper_claim_allowed: expected false",
        "" if not bool_field(evidence, "paper_claim_allowed") else "evidence paper_claim_allowed: expected false",
    ]
    active_blockers = [blocker for blocker in blockers if blocker]
    return {
        "report_gate_passed": not active_blockers,
        "blockers": active_blockers,
        "terminal_utility_contract_allowed": False,
        "paper_claim_allowed": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def render_report(summary: Mapping[str, Any]) -> str:
    facts = summary["facts"]
    diagnostic = summary["diagnostic_evidence"]
    evaluation = summary["evaluation_only_diagnostics"]
    gate = summary["gate"]
    return "\n".join(
        [
            "# Rival Contradiction Multi-Case Diagnostic Report",
            "",
            "## Facts",
            "",
            f"- Source pair rows: `{facts['source_pair_rows']}` across `{facts['scene_count']}` scenes and `{facts['query_count']}` queries.",
            f"- Observation seed / frame plan / rendered frame / projection-visible rows: `{facts['observation_seed_rows']}` / `{facts['frame_plan_rows']}` / `{facts['rendered_frame_rows']}` / `{facts['projection_visible_rows']}`.",
            f"- Detector frame rows: `{facts['detector_frame_rows']}`, association rows: `{facts['detector_association_rows']}`, rows with candidate association: `{facts['detector_associated_decision_rows']}`.",
            f"- Label-free detector evidence pair rows: `{diagnostic['detector_evidence_pair_rows']}`.",
            f"- Pair evidence states: `{diagnostic['pair_evidence_state_counts']}`.",
            f"- Request evidence states: `{diagnostic['request_evidence_state_counts']}`.",
            f"- Terminal commits / candidate commits / candidate rejections remain `{facts['terminal_commit_rows']}` / `{facts['candidate_commit_rows']}` / `{facts['candidate_rejection_rows']}`.",
            "",
            "## Paper Claims",
            "",
            "- No ObjectNav improvement, Semantic-SLAM performance improvement, terminal utility, `first_eval` readiness, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed from this report.",
            "",
            "## Agent Inferences",
            "",
            "- The multi-case ladder shows that rival contradiction / region contamination is observable across multiple scenes and queries.",
            "- The diagnostic is stronger than the single-case mechanism probe, but it is still not an action rule because wrong-goal, wasted-path, and map/pose deltas are joined only after evidence rows are frozen.",
            "- A terminal utility contract would be premature unless a separate label-free action rule is specified without evaluation-only labels or baseline outcomes.",
            "",
            "## Evaluation-Only Diagnostics",
            "",
            f"- Pair label counts: `{evaluation['pair_label_counts']}`.",
            f"- Baseline wrong-goal counts: `{evaluation['baseline_wrong_goal_counts']}`.",
            f"- Total wrong-goal baseline rows: `{evaluation['total_wrong_goal_baseline_rows']}`.",
            f"- Max wasted path exposure: `{evaluation['max_wasted_path_exposure_m']}`.",
            f"- SLAM map-pose delta rows / max: `{evaluation['slam_map_pose_delta_rows']}` / `{evaluation['slam_map_pose_delta_maximum']}`.",
            f"- Promotion gate passed: `{gate['report_gate_passed']}` for diagnostic readiness only.",
            "",
            "## Blocked Claims",
            "",
            "- Terminal selector: blocked.",
            "- Candidate rejection or candidate commit: blocked.",
            "- Formula revision from joined labels: blocked.",
            "- `first_eval` rerun and policy-scale comparison: blocked.",
            "- Paper contribution claim: blocked.",
            "",
            "## Next Valid Step",
            "",
            "- Define a separate terminal utility contract only after a future label-free branch produces an action rule that does not use pair labels, wrong-goal outcomes, wasted path, map/pose deltas, or baseline proxies as action inputs.",
            "",
        ]
    )


def build_summary(contract: Mapping[str, Any], root: Path) -> Dict[str, Any]:
    sources = contract["source"]
    source = load_json(root / sources["source_summary"])
    frame_plan = load_json(root / sources["frame_plan_summary"])
    frame_export = load_json(root / sources["frame_export_summary"])
    projection = load_json(root / sources["projection_summary"])
    detector = load_json(root / sources["detector_substrate_diagnostic"])
    evidence = load_json(root / sources["detector_evidence_summary"])
    evaluation = load_json(root / sources["evaluation_join_summary"])
    promotion = load_json(root / sources["promotion_gate_summary"])
    gate = report_gate(contract, source, frame_plan, frame_export, projection, detector, evidence, evaluation, promotion)
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": CONTRACT_DEFAULT,
        "decision": contract["decision"],
        "facts": {
            "source_pair_rows": source["source_rows"],
            "scene_count": source["scene_count"],
            "query_count": source["query_count"],
            "observation_seed_rows": source["observation_plan_seed_rows"],
            "frame_plan_rows": frame_plan["frame_plan_rows"],
            "rendered_frame_rows": frame_export["rows_exported"],
            "rendered_heading_count": frame_export["rendered_heading_count"],
            "projection_visible_rows": projection["projection_anchor_visible_rows"],
            "detector_frame_rows": detector["frame_rows"],
            "detector_association_rows": detector["association_rows"],
            "detector_associated_decision_rows": detector["associated_decision_rows"],
            "associated_scene_count": detector["associated_scene_count"],
            "associated_query_count": detector["associated_query_count"],
            "source_substrate_failure_taxonomy": detector["failure_taxonomy"],
            "terminal_commit_rows": max(
                int(source.get("terminal_commit_rows", 0)),
                int(evidence.get("terminal_commit_rows", 0)),
                int(evaluation.get("terminal_commit_rows", 0)),
            ),
            "candidate_commit_rows": max(
                int(source.get("candidate_commit_rows", 0)),
                int(evidence.get("candidate_commit_rows", 0)),
                int(evaluation.get("candidate_commit_rows", 0)),
            ),
            "candidate_rejection_rows": max(
                int(source.get("candidate_rejection_rows", 0)),
                int(evidence.get("candidate_rejection_rows", 0)),
                int(evaluation.get("candidate_rejection_rows", 0)),
            ),
            "uses_gt_for_action": False,
            "paper_claim_allowed": False,
        },
        "diagnostic_evidence": {
            "detector_evidence_pair_rows": evidence["pair_rows"],
            "candidate_view_evidence_state_counts": evidence["candidate_view_evidence_state_counts"],
            "role_evidence_state_counts": evidence["role_evidence_state_counts"],
            "pair_evidence_state_counts": evidence["pair_evidence_state_counts"],
            "request_evidence_state_counts": evidence["request_evidence_state_counts"],
            "role_rows_with_any_candidate_association": evidence["role_rows_with_any_candidate_association"],
            "pair_rows_with_any_candidate_association": evidence["pair_rows_with_any_candidate_association"],
        },
        "evaluation_only_diagnostics": {
            "evaluation_pair_rows": evaluation["pair_rows"],
            "pair_label_counts": evaluation["pair_label_counts"],
            "candidate_label_counts": evaluation["candidate_label_counts"],
            "baseline_wrong_goal_counts": evaluation["baseline_wrong_goal_counts"],
            "total_wrong_goal_baseline_rows": evaluation["total_wrong_goal_baseline_rows"],
            "max_wasted_path_exposure_m": evaluation["max_wasted_path_exposure_m"],
            "slam_map_pose_delta_rows": evaluation["slam_map_pose_delta_rows"],
            "slam_map_pose_delta_maximum": evaluation["slam_map_pose_delta_maximum"],
            "contamination_or_contradiction_pair_rows": promotion["contamination_or_contradiction_pair_rows"],
            "wrong_labeled_pair_rows": promotion["wrong_labeled_pair_rows"],
            "wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence": promotion[
                "wrong_labeled_pair_rows_with_contamination_or_contradiction_evidence"
            ],
            "uses_gt_for_analysis": True,
        },
        "gate": gate,
        "allowed_next_steps_after_report": contract["allowed_next_steps_after_report"],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    root = Path.cwd()
    contract = load_json(root / args.contract)
    out_root = Path(args.out_root)
    if not out_root.is_absolute():
        out_root = root / out_root

    summary = build_summary(contract, root)
    write_json(out_root / "rival_contradiction_region_contamination_multi_case_diagnostic_report_summary.json", summary)
    write_text(out_root / "rival_contradiction_region_contamination_multi_case_diagnostic_report.md", render_report(summary))

    if not summary["gate"]["report_gate_passed"]:
        raise SystemExit("Diagnostic report gate failed: " + "; ".join(summary["gate"]["blockers"]))


if __name__ == "__main__":
    main()
