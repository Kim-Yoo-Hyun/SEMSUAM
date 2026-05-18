import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.analyze_association_recovery_arbitration import arbitration_decision
from h001_runtime.analyze_object_node_evidence_objective import (
    build_candidate_table,
    labels_for_policy,
    load_jsonl,
    safe_float,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.association_recovery_observation.v1"


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def support(feature_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not feature_row:
        return {
            "S_det": 0.0,
            "S_proj": 0.0,
            "S_depth": 0.0,
            "S_prop": 0.0,
            "R_amb": 0.0,
            "property_group": None,
            "aux_support": 0.0,
            "supported_score": 0.0,
            "positive_support": False,
        }
    s_det = safe_float(feature_row.get("S_det")) or safe_float(feature_row.get("N1_detector_score_only")) or 0.0
    s_proj = safe_float(feature_row.get("S_proj")) or 0.0
    s_depth = safe_float(feature_row.get("S_depth")) or 0.0
    s_prop = safe_float(feature_row.get("S_prop")) or 0.0
    r_amb = safe_float(feature_row.get("R_amb")) or 0.0
    aux = max(0.0, s_proj, s_depth, s_prop)
    supported_score = max(0.0, min(1.0, s_det * aux))
    return {
        "S_det": s_det,
        "S_proj": s_proj,
        "S_depth": s_depth,
        "S_prop": s_prop,
        "R_amb": r_amb,
        "property_group": feature_row.get("property_group"),
        "aux_support": aux,
        "supported_score": supported_score,
        "positive_support": bool(s_det > 0.0 and aux > 0.0 and supported_score > 0.0),
    }


def combined_feature(original: Optional[Dict[str, Any]], second: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    before = support(original)
    after = support(second)
    merged = {
        "S_det": max(before["S_det"], after["S_det"]),
        "S_proj": max(before["S_proj"], after["S_proj"]),
        "S_depth": max(before["S_depth"], after["S_depth"]),
        "S_prop": max(before["S_prop"], after["S_prop"]),
        "R_amb": max(before["R_amb"], after["R_amb"]),
        "property_group": after.get("property_group") or before.get("property_group"),
    }
    aux = max(0.0, merged["S_proj"], merged["S_depth"], merged["S_prop"])
    supported_score = max(0.0, min(1.0, merged["S_det"] * aux))
    out = {
        **(second or original or {}),
        "schema_version": SCHEMA_VERSION,
        "S_det_before": before["S_det"],
        "S_proj_before": before["S_proj"],
        "S_depth_before": before["S_depth"],
        "S_prop_before": before["S_prop"],
        "R_amb_before": before["R_amb"],
        "S_det_second": after["S_det"],
        "S_proj_second": after["S_proj"],
        "S_depth_second": after["S_depth"],
        "S_prop_second": after["S_prop"],
        "R_amb_second": after["R_amb"],
        **merged,
        "object_node_aux_support": aux,
        "object_node_supported_score": supported_score,
        "object_node_positive_support": bool(merged["S_det"] > 0.0 and aux > 0.0 and supported_score > 0.0),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": (second or original or {}).get("candidate_correct") is not None,
    }
    return out


def feature_index(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row.get("episode_key")), str(row.get("candidate_id"))): row
        for row in rows
        if row.get("episode_key") is not None and row.get("candidate_id") is not None
    }


def labels_by_episode(rows: List[Dict[str, Any]], policy: str) -> Dict[str, Dict[str, Dict[str, Any]]]:
    labels = labels_for_policy(rows, policy)
    out: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for (episode_key, candidate_id), row in labels.items():
        out[episode_key][candidate_id] = row
    return out


def compute_risk(
    plan: Dict[str, Any],
    combined: Dict[Tuple[str, str], Dict[str, Any]],
    labels: Dict[str, Dict[str, Dict[str, Any]]],
    risk_contradiction_scale: float,
) -> Dict[str, Any]:
    episode_key = str(plan.get("episode_key"))
    top_id = str(plan.get("risk_top_candidate_id") or plan.get("final_candidate_id_before") or "")
    alt_id = str(plan.get("risk_best_alt_candidate_id") or plan.get("second_observation_alt_candidate_id") or "")
    top = support(combined.get((episode_key, top_id)))
    candidate_rows = labels.get(episode_key, {})
    alt_candidates = [
        candidate_id
        for candidate_id in candidate_rows
        if candidate_id != top_id
    ]
    if alt_id not in candidate_rows and alt_candidates:
        alt_id = max(
            alt_candidates,
            key=lambda candidate_id: support(combined.get((episode_key, candidate_id)))["supported_score"],
        )
    alt = support(combined.get((episode_key, alt_id)))
    support_gap = alt["supported_score"] - top["supported_score"]
    property_group = str(top.get("property_group") or "unknown")
    property_weight = 0.5 if property_group == "standard_furniture_or_fixture" else 1.0
    r_no_evidence = 0.0 if top["positive_support"] else 1.0
    r_contradiction = max(0.0, min(1.0, support_gap / max(risk_contradiction_scale, 1e-6)))
    r_ambiguity = max(0.0, min(1.0, top["R_amb"]))
    r_property = max(0.0, min(1.0, property_weight * (1.0 - top["aux_support"])))
    r_total = max(r_no_evidence, r_contradiction, r_ambiguity, r_property)
    return {
        "risk_top_candidate_id": top_id,
        "risk_best_alt_candidate_id_after_second": alt_id,
        "risk_top_supported_score_after_second": top["supported_score"],
        "risk_best_alt_supported_score_after_second": alt["supported_score"],
        "risk_support_gap_alt_minus_top_after_second": support_gap,
        "R_after2": r_total,
        "R_after2_no_evidence": r_no_evidence,
        "R_after2_contradiction": r_contradiction,
        "R_after2_ambiguity": r_ambiguity,
        "R_after2_property_weakness": r_property,
        "top_positive_support_after_second": top["positive_support"],
        "top_aux_support_after_second": top["aux_support"],
    }


def arbitration_args(args: argparse.Namespace) -> argparse.Namespace:
    return argparse.Namespace(
        risk_total_commit=float(args.arbitration_risk_total_commit),
        support_margin=float(args.arbitration_support_margin),
        contradiction_block=float(args.arbitration_contradiction_block),
        ambiguity_block=float(args.arbitration_ambiguity_block),
        property_block=float(args.arbitration_property_block),
    )


def apply_arbitration(row: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    decision = arbitration_decision(row, arbitration_args(args))
    commit = decision["arbitration_action"] == "commit_top"
    top_correct = row.get("top_candidate_correct")
    return {
        **decision,
        "arbitration_commit_top": commit,
        "wrong_goal_commit_if_arbitration_applied": bool(commit and top_correct is False),
        "success_commit_if_arbitration_applied": bool(commit and top_correct is True),
        "success_lost_by_arbitration_defer": bool((not commit) and top_correct is True),
        "wrong_goal_avoided_by_arbitration_defer": bool((not commit) and top_correct is False),
    }


def arbitration_summary(rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    by_second_reason: Dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        action = str(row.get("arbitration_action"))
        reason = str(row.get("arbitration_reason"))
        second_reason = str(row.get("second_observation_reason"))
        action_counts[action] += 1
        reason_counts[reason] += 1
        by_second_reason[second_reason][action] += 1
    return {
        "schema_version": "h001.association_recovery_arbitration.v1",
        "rows": len(rows),
        "thresholds": {
            "risk_total_commit": float(args.arbitration_risk_total_commit),
            "support_margin": float(args.arbitration_support_margin),
            "contradiction_block": float(args.arbitration_contradiction_block),
            "ambiguity_block": float(args.arbitration_ambiguity_block),
            "property_block": float(args.arbitration_property_block),
        },
        "arbitration_action_counts": dict(sorted(action_counts.items())),
        "arbitration_reason_counts": dict(sorted(reason_counts.items())),
        "arbitration_action_by_second_observation_reason": {
            reason: dict(sorted(counts.items()))
            for reason, counts in sorted(by_second_reason.items())
        },
        "commit_top_rate": ratio(sum(row["arbitration_commit_top"] for row in rows), len(rows)),
        "wrong_goal_commit_rate_if_arbitration_applied": ratio(
            sum(row["wrong_goal_commit_if_arbitration_applied"] for row in rows),
            len(rows),
        ),
        "success_commit_rate_if_arbitration_applied": ratio(
            sum(row["success_commit_if_arbitration_applied"] for row in rows),
            len(rows),
        ),
        "success_lost_by_arbitration_defer_rate": ratio(
            sum(row["success_lost_by_arbitration_defer"] for row in rows),
            len(rows),
        ),
        "wrong_goal_avoided_by_arbitration_defer_rate": ratio(
            sum(row["wrong_goal_avoided_by_arbitration_defer"] for row in rows),
            len(rows),
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "association_recovery_arbitration_rows.jsonl",
            "summary": "association_recovery_arbitration_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.second_observation_plan))
    candidate_decisions = load_jsonl(Path(args.candidate_decisions))
    original_features = load_jsonl(Path(args.original_object_node_features))
    association_rows = load_jsonl(Path(args.detector_root) / "detector_candidate_associations.jsonl")
    labels = labels_for_policy(candidate_decisions, str(args.policy))
    second_features = build_candidate_table(association_rows, labels)

    original_idx = feature_index(original_features)
    second_idx = feature_index(second_features)
    all_keys = set(original_idx) | set(second_idx)
    combined_rows = [
        combined_feature(original_idx.get(key), second_idx.get(key))
        for key in sorted(all_keys)
    ]
    combined_idx = feature_index(combined_rows)
    label_episode = labels_by_episode(candidate_decisions, str(args.policy))

    rows_out: List[Dict[str, Any]] = []
    for plan in plan_rows:
        episode_key = str(plan.get("episode_key"))
        top_id = str(plan.get("risk_top_candidate_id") or plan.get("final_candidate_id_before") or "")
        original_top = support(original_idx.get((episode_key, top_id)))
        risk = compute_risk(plan, combined_idx, label_episode, float(args.risk_contradiction_scale))
        r_after = safe_float(plan.get("R_after"))
        r_after2 = safe_float(risk.get("R_after2"))
        risk_delta2 = None if r_after is None or r_after2 is None else r_after - r_after2
        risk_resolved = bool(r_after2 is not None and r_after2 < float(args.risk_total_trigger))
        risk_resolution_commit = bool(
            not risk_resolved
            and risk_delta2 is not None
            and risk_delta2 >= float(args.risk_resolution_delta_trigger)
            and r_after2 is not None
            and r_after2 <= float(args.risk_resolution_max_risk)
            and (safe_float(risk.get("R_after2_contradiction")) or 0.0) <= float(args.risk_resolution_max_contradiction)
            and (
                bool(risk.get("top_positive_support_after_second"))
                or not bool(args.risk_resolution_require_positive_support)
            )
        )
        commit = bool(risk_resolved or risk_resolution_commit)
        label = label_episode.get(episode_key, {}).get(top_id, {})
        top_correct = label.get("candidate_correct")
        association_gain = risk["top_aux_support_after_second"] - original_top["aux_support"]
        row = {
            "schema_version": SCHEMA_VERSION,
            "episode_key": episode_key,
            "episode_id": plan.get("episode_id"),
            "scene_id": plan.get("scene_id"),
            "query": plan.get("query"),
            "second_observation_reason": plan.get("second_observation_reason"),
            "second_observation_candidate_id": plan.get("second_observation_candidate_id"),
            "risk_top_candidate_id": top_id,
            "risk_feature_source_before": str(args.original_object_node_features),
            "risk_feature_source_after_second": str(args.detector_root),
            "R_after": r_after,
            **risk,
            "risk_delta_after_second_observation": risk_delta2,
            "risk_resolved_after_second_observation": risk_resolved,
            "risk_unresolved_after_second_observation": not commit,
            "association_recovered_after_second": bool(
                not original_top["positive_support"] and risk.get("top_positive_support_after_second")
            ),
            "second_observation_observed_association_gain": association_gain,
            "commit_after_second_observation": commit,
            "commit_after_second_reason": (
                "risk_resolved"
                if risk_resolved
                else ("risk_resolution_commit" if risk_resolution_commit else "risk_unresolved_no_commit")
            ),
            "top_candidate_correct": top_correct,
            "wrong_goal_commit_if_fixed_gate_applied": bool(commit and top_correct is False),
            "success_lost_by_remaining_defer": bool((not commit) and top_correct is True),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": top_correct is not None,
        }
        row.update(apply_arbitration(row, args))
        rows_out.append(row)

    plan_count = len(plan_rows)
    trigger_count = sum(row.get("second_observation_triggered") is True for row in plan_rows)
    unsupported_before = [
        row
        for row in rows_out
        if not support(original_idx.get((str(row.get("episode_key")), str(row.get("risk_top_candidate_id")))))["positive_support"]
    ]
    arbitration = arbitration_summary(rows_out, args)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "second_observation_plan": str(args.second_observation_plan),
        "detector_root": str(args.detector_root),
        "candidate_decisions": str(args.candidate_decisions),
        "original_object_node_features": str(args.original_object_node_features),
        "policy": str(args.policy),
        "plan_rows": plan_count,
        "second_observation_trigger_rate": ratio(trigger_count, plan_count),
        "association_recovered_count": sum(row["association_recovered_after_second"] for row in rows_out),
        "association_recovered_rate": ratio(
            sum(row["association_recovered_after_second"] for row in rows_out),
            len(unsupported_before),
        ),
        "unsupported_top_before_count": len(unsupported_before),
        "top_positive_support_after_second_rate": ratio(
            sum(row["top_positive_support_after_second"] for row in rows_out),
            len(rows_out),
        ),
        "risk_resolved_after_second_observation_rate": ratio(
            sum(row["risk_resolved_after_second_observation"] for row in rows_out),
            len(rows_out),
        ),
        "risk_unresolved_after_second_observation_rate": ratio(
            sum(row["risk_unresolved_after_second_observation"] for row in rows_out),
            len(rows_out),
        ),
        "commit_after_second_observation_rate": ratio(
            sum(row["commit_after_second_observation"] for row in rows_out),
            len(rows_out),
        ),
        "wrong_goal_commit_rate_if_fixed_commit_gate_applied": ratio(
            sum(row["wrong_goal_commit_if_fixed_gate_applied"] for row in rows_out),
            len(rows_out),
        ),
        "success_lost_by_remaining_defer_rate": ratio(
            sum(row["success_lost_by_remaining_defer"] for row in rows_out),
            len(rows_out),
        ),
        "mean_observed_association_gain": (
            sum(float(row["second_observation_observed_association_gain"]) for row in rows_out) / len(rows_out)
            if rows_out
            else None
        ),
        "gate": {
            "min_risk_resolution_gain_abs": float(args.min_risk_resolution_gain_abs),
            "min_association_recovered_rate": float(args.min_association_recovered_rate),
            "max_wrong_goal_increase_abs": float(args.max_wrong_goal_increase_abs),
            "baseline_risk_resolved_after_reobserve_rate": float(args.baseline_risk_resolved_after_reobserve_rate),
            "baseline_wrong_goal_rate": float(args.baseline_wrong_goal_rate),
        },
        "arbitration": arbitration,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    resolved_rate = summary["risk_resolved_after_second_observation_rate"] or 0.0
    recovered_rate = summary["association_recovered_rate"] or 0.0
    wrong_rate = summary["wrong_goal_commit_rate_if_fixed_commit_gate_applied"] or 0.0
    summary["gate"]["passes_policy_integration_diagnostic_gate"] = bool(
        resolved_rate
        >= float(args.baseline_risk_resolved_after_reobserve_rate) + float(args.min_risk_resolution_gain_abs)
        and recovered_rate >= float(args.min_association_recovered_rate)
        and wrong_rate
        <= float(args.baseline_wrong_goal_rate) + float(args.max_wrong_goal_increase_abs)
    )

    write_jsonl(out / "candidate_object_node_features_after_second.jsonl", combined_rows)
    write_jsonl(out / "risk_resolution_after_second_rows.jsonl", rows_out)
    write_jsonl(out / "association_recovery_arbitration_rows.jsonl", rows_out)
    write_json(out / "association_recovery_arbitration_summary.json", arbitration)
    write_json(out / "risk_resolution_after_second_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze AssociationRecoveryObservation diagnostic output.")
    parser.add_argument("--second-observation-plan", required=True)
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--original-object-node-features", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="RiskResolutionReobserve")
    parser.add_argument("--risk-total-trigger", type=float, default=0.6)
    parser.add_argument("--risk-contradiction-scale", type=float, default=0.25)
    parser.add_argument("--risk-resolution-delta-trigger", type=float, default=0.05)
    parser.add_argument("--risk-resolution-max-risk", type=float, default=0.95)
    parser.add_argument("--risk-resolution-max-contradiction", type=float, default=0.25)
    parser.add_argument("--risk-resolution-require-positive-support", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--baseline-risk-resolved-after-reobserve-rate", type=float, default=0.05)
    parser.add_argument("--baseline-wrong-goal-rate", type=float, default=0.07)
    parser.add_argument("--min-risk-resolution-gain-abs", type=float, default=0.10)
    parser.add_argument("--min-association-recovered-rate", type=float, default=0.20)
    parser.add_argument("--max-wrong-goal-increase-abs", type=float, default=0.03)
    parser.add_argument("--arbitration-risk-total-commit", type=float, default=0.6)
    parser.add_argument("--arbitration-support-margin", type=float, default=0.05)
    parser.add_argument("--arbitration-contradiction-block", type=float, default=0.25)
    parser.add_argument("--arbitration-ambiguity-block", type=float, default=0.5)
    parser.add_argument("--arbitration-property-block", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
