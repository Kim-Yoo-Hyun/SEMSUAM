import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.object_node_confirmation.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def scene_short_id(scene_id: Any) -> str:
    return Path(str(scene_id)).stem.replace(".basis", "")


def group_by_episode(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("episode_key"))].append(row)
    return grouped


def evaluate_config(
    grouped: Dict[str, List[Dict[str, Any]]],
    field: str,
    confirm_min: float,
    confirm_margin: float,
    disconfirm_margin: float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    decisions: List[Dict[str, Any]] = []
    counts: Dict[str, int] = defaultdict(int)
    scene_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    property_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for episode_key, candidates in sorted(grouped.items()):
        top = next((row for row in candidates if row.get("is_top_before") is True), None)
        if top is None:
            top = min(candidates, key=lambda row: int(row.get("candidate_rank_before") or 9999))
        alternatives = [row for row in candidates if row.get("candidate_id") != top.get("candidate_id")]
        best_alt = max(
            alternatives,
            key=lambda row: (safe_float(row.get(field)) or 0.0, -int(row.get("candidate_rank_before") or 9999)),
        ) if alternatives else top
        top_score = safe_float(top.get(field)) or 0.0
        alt_score = safe_float(best_alt.get(field)) or 0.0
        evidence_gap = top_score - alt_score

        if top_score >= confirm_min and evidence_gap >= confirm_margin:
            state = "confirmed"
        elif -evidence_gap >= disconfirm_margin:
            state = "disconfirmed"
        else:
            state = "uncertain"

        top_correct = top.get("candidate_correct") is True
        top_wrong_goal = top.get("wrong_goal_visit_before") is True
        counts["rows"] += 1
        counts["baseline_correct"] += int(top_correct)
        counts["baseline_wrong_goal"] += int(top_wrong_goal)
        counts[state] += 1
        counts[f"{state}_correct"] += int(top_correct)
        counts[f"{state}_wrong_goal"] += int(top_wrong_goal)
        scene = scene_short_id(top.get("scene_id"))
        prop = str(top.get("property_group"))
        for bucket in (scene_counts[scene], property_counts[prop]):
            bucket["rows"] += 1
            bucket[state] += 1
            bucket[f"{state}_wrong_goal"] += int(top_wrong_goal)
            bucket[f"{state}_correct"] += int(top_correct)

        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "field": field,
                "episode_key": episode_key,
                "episode_id": top.get("episode_id"),
                "scene_id": top.get("scene_id"),
                "query": top.get("query"),
                "property_group": prop,
                "top_candidate_id": top.get("candidate_id"),
                "top_candidate_correct": top.get("candidate_correct"),
                "top_wrong_goal_visit": top.get("wrong_goal_visit_before"),
                "top_score": top_score,
                "best_alt_candidate_id": best_alt.get("candidate_id"),
                "best_alt_score": alt_score,
                "evidence_gap_top_minus_alt": evidence_gap,
                "state": state,
                "would_commit": state == "confirmed",
                "would_request_reobserve": state != "confirmed",
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )

    rows = counts["rows"]
    baseline_correct_rate = ratio(counts["baseline_correct"], rows)
    baseline_wrong_rate = ratio(counts["baseline_wrong_goal"], rows)
    confirmed = counts["confirmed"]
    disconfirmed = counts["disconfirmed"]
    uncertain = counts["uncertain"]
    wrong_goal_routed = counts["disconfirmed_wrong_goal"] + counts["uncertain_wrong_goal"]
    confirmed_correct_rate = ratio(counts["confirmed_correct"], confirmed)
    confirmed_wrong_rate = ratio(counts["confirmed_wrong_goal"], confirmed)
    disconfirm_precision = ratio(counts["disconfirmed_wrong_goal"], disconfirmed)
    false_disconfirm = counts["disconfirmed_correct"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "field": field,
        "confirm_min": confirm_min,
        "confirm_margin": confirm_margin,
        "disconfirm_margin": disconfirm_margin,
        "rows": rows,
        "baseline_correct_rate": baseline_correct_rate,
        "baseline_wrong_goal_rate": baseline_wrong_rate,
        "confirmed_rows": confirmed,
        "confirmed_correct_rate": confirmed_correct_rate,
        "confirmed_wrong_goal_rate": confirmed_wrong_rate,
        "disconfirmed_rows": disconfirmed,
        "disconfirmed_wrong_goal_precision": disconfirm_precision,
        "false_disconfirm_correct_top_count": false_disconfirm,
        "uncertain_rows": uncertain,
        "wrong_goal_routed_to_reobserve_rate": ratio(wrong_goal_routed, counts["baseline_wrong_goal"]),
        "overall_reobserve_request_rate": ratio(disconfirmed + uncertain, rows),
        "confirmation_gate": (
            confirmed >= 20
            and confirmed_correct_rate is not None
            and baseline_correct_rate is not None
            and confirmed_correct_rate >= baseline_correct_rate + 0.05
            and confirmed_wrong_rate is not None
            and baseline_wrong_rate is not None
            and confirmed_wrong_rate <= baseline_wrong_rate - 0.05
        ),
        "disconfirmation_gate": (
            disconfirmed >= 3
            and disconfirm_precision is not None
            and disconfirm_precision >= 0.80
            and false_disconfirm <= 1
            and ratio(wrong_goal_routed, counts["baseline_wrong_goal"]) is not None
            and ratio(wrong_goal_routed, counts["baseline_wrong_goal"]) >= 0.45
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    summary["passes_confirm_disconfirm_gate"] = bool(summary["confirmation_gate"] and summary["disconfirmation_gate"])
    summary["scene_rows"] = [{"key": key, **dict(value)} for key, value in sorted(scene_counts.items())]
    summary["property_rows"] = [{"key": key, **dict(value)} for key, value in sorted(property_counts.items())]
    return decisions, summary


def support_values(row: Dict[str, Any]) -> Tuple[float, float, float, bool]:
    s_det = safe_float(row.get("S_det")) or 0.0
    aux = max(
        safe_float(row.get("S_proj")) or 0.0,
        safe_float(row.get("S_depth")) or 0.0,
        safe_float(row.get("S_prop")) or 0.0,
    )
    supported_score = s_det * aux
    positive_support = s_det > 0.0 and aux > 0.0 and supported_score > 0.0
    return s_det, aux, supported_score, positive_support


def evaluate_supported_config(
    grouped: Dict[str, List[Dict[str, Any]]],
    confirm_margin: float,
    disconfirm_margin: float,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    decisions: List[Dict[str, Any]] = []
    counts: Dict[str, int] = defaultdict(int)
    scene_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    property_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for episode_key, candidates in sorted(grouped.items()):
        top = next((row for row in candidates if row.get("is_top_before") is True), None)
        if top is None:
            top = min(candidates, key=lambda row: int(row.get("candidate_rank_before") or 9999))
        alternatives = [row for row in candidates if row.get("candidate_id") != top.get("candidate_id")]
        best_alt = max(
            alternatives,
            key=lambda row: (support_values(row)[2], -int(row.get("candidate_rank_before") or 9999)),
        ) if alternatives else top
        top_det, top_aux, top_score, top_supported = support_values(top)
        alt_det, alt_aux, alt_score, alt_supported = support_values(best_alt)
        evidence_gap = top_score - alt_score

        if top_supported and evidence_gap >= confirm_margin:
            state = "confirmed"
        elif alt_supported and -evidence_gap >= disconfirm_margin:
            state = "disconfirmed"
        else:
            state = "uncertain"

        top_correct = top.get("candidate_correct") is True
        top_wrong_goal = top.get("wrong_goal_visit_before") is True
        counts["rows"] += 1
        counts["baseline_correct"] += int(top_correct)
        counts["baseline_wrong_goal"] += int(top_wrong_goal)
        counts[state] += 1
        counts[f"{state}_correct"] += int(top_correct)
        counts[f"{state}_wrong_goal"] += int(top_wrong_goal)
        scene = scene_short_id(top.get("scene_id"))
        prop = str(top.get("property_group"))
        for bucket in (scene_counts[scene], property_counts[prop]):
            bucket["rows"] += 1
            bucket[state] += 1
            bucket[f"{state}_wrong_goal"] += int(top_wrong_goal)
            bucket[f"{state}_correct"] += int(top_correct)

        decisions.append(
            {
                "schema_version": SCHEMA_VERSION,
                "field": "supported_evidence",
                "episode_key": episode_key,
                "episode_id": top.get("episode_id"),
                "scene_id": top.get("scene_id"),
                "query": top.get("query"),
                "property_group": prop,
                "top_candidate_id": top.get("candidate_id"),
                "top_candidate_correct": top.get("candidate_correct"),
                "top_wrong_goal_visit": top.get("wrong_goal_visit_before"),
                "top_score": top_score,
                "top_detector_score": top_det,
                "top_aux_support": top_aux,
                "top_positive_support": top_supported,
                "best_alt_candidate_id": best_alt.get("candidate_id"),
                "best_alt_score": alt_score,
                "best_alt_detector_score": alt_det,
                "best_alt_aux_support": alt_aux,
                "best_alt_positive_support": alt_supported,
                "evidence_gap_top_minus_alt": evidence_gap,
                "state": state,
                "would_commit": state == "confirmed",
                "would_request_reobserve": state != "confirmed",
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )

    rows = counts["rows"]
    baseline_correct_rate = ratio(counts["baseline_correct"], rows)
    baseline_wrong_rate = ratio(counts["baseline_wrong_goal"], rows)
    confirmed = counts["confirmed"]
    disconfirmed = counts["disconfirmed"]
    uncertain = counts["uncertain"]
    wrong_goal_routed = counts["disconfirmed_wrong_goal"] + counts["uncertain_wrong_goal"]
    confirmed_correct_rate = ratio(counts["confirmed_correct"], confirmed)
    confirmed_wrong_rate = ratio(counts["confirmed_wrong_goal"], confirmed)
    disconfirm_precision = ratio(counts["disconfirmed_wrong_goal"], disconfirmed)
    false_disconfirm = counts["disconfirmed_correct"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "rule": "supported_contradiction",
        "field": "supported_evidence",
        "confirm_min": 0.0,
        "confirm_margin": confirm_margin,
        "disconfirm_margin": disconfirm_margin,
        "rows": rows,
        "baseline_correct_rate": baseline_correct_rate,
        "baseline_wrong_goal_rate": baseline_wrong_rate,
        "confirmed_rows": confirmed,
        "confirmed_correct_rate": confirmed_correct_rate,
        "confirmed_wrong_goal_rate": confirmed_wrong_rate,
        "disconfirmed_rows": disconfirmed,
        "disconfirmed_wrong_goal_precision": disconfirm_precision,
        "false_disconfirm_correct_top_count": false_disconfirm,
        "uncertain_rows": uncertain,
        "wrong_goal_routed_to_reobserve_rate": ratio(wrong_goal_routed, counts["baseline_wrong_goal"]),
        "overall_reobserve_request_rate": ratio(disconfirmed + uncertain, rows),
        "confirmation_gate": (
            confirmed >= 3
            and confirmed_correct_rate is not None
            and baseline_correct_rate is not None
            and confirmed_correct_rate >= baseline_correct_rate + 0.05
            and confirmed_wrong_rate is not None
            and baseline_wrong_rate is not None
            and confirmed_wrong_rate <= baseline_wrong_rate - 0.05
        ),
        "disconfirmation_gate": (
            disconfirmed >= 1
            and disconfirm_precision is not None
            and disconfirm_precision >= 0.80
            and false_disconfirm <= 1
            and ratio(wrong_goal_routed, counts["baseline_wrong_goal"]) is not None
            and ratio(wrong_goal_routed, counts["baseline_wrong_goal"]) >= 0.45
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    summary["passes_confirm_disconfirm_gate"] = bool(summary["confirmation_gate"] and summary["disconfirmation_gate"])
    summary["scene_rows"] = [{"key": key, **dict(value)} for key, value in sorted(scene_counts.items())]
    summary["property_rows"] = [{"key": key, **dict(value)} for key, value in sorted(property_counts.items())]
    return decisions, summary


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.candidate_features))
    grouped = group_by_episode(rows)
    fields = [field.strip() for field in str(args.fields).split(",") if field.strip()]
    confirm_mins = [float(value) for value in str(args.confirm_mins).split(",")]
    confirm_margins = [float(value) for value in str(args.confirm_margins).split(",")]
    disconfirm_margins = [float(value) for value in str(args.disconfirm_margins).split(",")]

    summaries: List[Dict[str, Any]] = []
    decision_sets: Dict[str, List[Dict[str, Any]]] = {}
    if args.rule == "supported_contradiction":
        for confirm_margin in confirm_margins:
            for disconfirm_margin in disconfirm_margins:
                decisions, summary = evaluate_supported_config(
                    grouped,
                    confirm_margin,
                    disconfirm_margin,
                )
                key = f"supported_evidence__cm_{confirm_margin:g}__dm_{disconfirm_margin:g}"
                summary["config_key"] = key
                summaries.append(summary)
                decision_sets[key] = decisions
    else:
        for field in fields:
            for confirm_min in confirm_mins:
                for confirm_margin in confirm_margins:
                    for disconfirm_margin in disconfirm_margins:
                        decisions, summary = evaluate_config(
                            grouped,
                            field,
                            confirm_min,
                            confirm_margin,
                            disconfirm_margin,
                        )
                        key = f"{field}__cmin_{confirm_min:g}__cm_{confirm_margin:g}__dm_{disconfirm_margin:g}"
                        summary["config_key"] = key
                        summaries.append(summary)
                        decision_sets[key] = decisions

    def rank_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
        return (
            row["passes_confirm_disconfirm_gate"] is True,
            row["disconfirmation_gate"] is True,
            row.get("disconfirmed_wrong_goal_precision") or 0.0,
            row.get("wrong_goal_routed_to_reobserve_rate") or 0.0,
            row["confirmation_gate"] is True,
            row.get("confirmed_correct_rate") or 0.0,
            -(row.get("false_disconfirm_correct_top_count") or 0),
        )

    best = max(summaries, key=rank_key)
    best_key = str(best["config_key"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fixed_gate = {
        "gate_name": args.fixed_gate_name,
        "field": best["field"],
        "confirm_min": best["confirm_min"],
        "confirm_margin": best["confirm_margin"],
        "disconfirm_margin": best["disconfirm_margin"],
        "is_single_config": len(summaries) == 1,
    }
    promotion_ready = bool(
        args.independent_validation
        and fixed_gate["is_single_config"]
        and best["passes_confirm_disconfirm_gate"] is True
        and best["rows"] >= int(args.min_rows)
    )
    if promotion_ready:
        reason = "independent_fixed_gate_passed"
    elif args.independent_validation and not fixed_gate["is_single_config"]:
        reason = "independent_validation_requires_single_fixed_config"
    elif args.independent_validation:
        reason = "independent_fixed_gate_failed"
    else:
        reason = "same_artifact_confirmation_diagnostic_only"

    write_json(out / "summary.json", {
        "schema_version": SCHEMA_VERSION,
        "candidate_features": str(args.candidate_features),
        "rule": args.rule,
        "best_config_key": best_key,
        "fixed_gate": fixed_gate,
        "independent_validation": bool(args.independent_validation),
        "min_rows": int(args.min_rows),
        "best_summary": {key: value for key, value in best.items() if key not in {"scene_rows", "property_rows"}},
        "config_summaries": [{key: value for key, value in row.items() if key not in {"scene_rows", "property_rows"}} for row in summaries],
        "promotion_ready": promotion_ready,
        "reason": reason,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    })
    write_jsonl(out / "config_summaries.jsonl", summaries)
    write_jsonl(out / "best_decisions.jsonl", decision_sets[best_key])
    write_jsonl(out / "best_scene_summary.jsonl", best["scene_rows"])
    write_jsonl(out / "best_property_summary.jsonl", best["property_rows"])
    return {key: value for key, value in best.items() if key not in {"scene_rows", "property_rows"}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze top-candidate confirmation/disconfirmation from object-node evidence.")
    parser.add_argument("--candidate-features", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--fields",
        default="N1_detector_score_only,N4_property_conditioned_depth_reliability,N5_object_node_evidence_full",
    )
    parser.add_argument("--rule", choices=["score_gap", "supported_contradiction"], default="score_gap")
    parser.add_argument("--confirm-mins", default="0,0.2,0.4,0.6")
    parser.add_argument("--confirm-margins", default="0,0.05,0.1,0.2")
    parser.add_argument("--disconfirm-margins", default="0.1,0.15,0.2,0.25,0.3")
    parser.add_argument("--fixed-gate-name", default="")
    parser.add_argument("--independent-validation", action="store_true")
    parser.add_argument("--min-rows", type=int, default=20)
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
