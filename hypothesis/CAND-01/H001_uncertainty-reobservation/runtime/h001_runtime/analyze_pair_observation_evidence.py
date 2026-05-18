import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.analyze_object_node_evidence_objective import labels_for_policy, projection_proximity, safe_float
from h001_runtime.export_postview_frames_v2 import decision_id


SCHEMA_VERSION = "h001.pair_observation_evidence.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def pair_key(row: Dict[str, Any]) -> str:
    value = row.get("pair_observation_id")
    if value is not None:
        return str(value)
    return f"{row.get('episode_key')}|{row.get('pair_top_candidate_id')}|{row.get('pair_alt_candidate_id')}"


def plan_decision_index(plan_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {decision_id(row): row for row in plan_rows}


def candidate_support(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    detector_scores = [safe_float(row.get("best_box_score")) for row in rows]
    detector_scores = [value for value in detector_scores if value is not None]
    visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
    box_hits = [row for row in visible_rows if row.get("projected_pixel_inside_box") is True]
    mask_hits = [row for row in visible_rows if row.get("projected_pixel_inside_mask") is True]
    strict_hits = [row for row in rows if row.get("associated_to_candidate") is True]
    proximity = [projection_proximity(row) for row in rows]
    s_det = max(detector_scores) if detector_scores else 0.0
    s_proj = min(1.0, (len(mask_hits) + 0.5 * max(0, len(box_hits) - len(mask_hits))) / 3.0)
    s_depth = min(1.0, len(strict_hits) / 2.0)
    s_mask = min(1.0, len(mask_hits) / 2.0)
    s_prox = max(proximity, default=0.0)
    pair_score = max(
        0.0,
        min(1.0, 0.30 * s_det + 0.25 * s_proj + 0.25 * s_depth + 0.10 * s_mask + 0.10 * s_prox),
    )
    return {
        "detector_score_max": s_det,
        "visible_count": len(visible_rows),
        "box_hit_count": len(box_hits),
        "mask_hit_count": len(mask_hits),
        "strict_association_count": len(strict_hits),
        "S_pair_proj": s_proj,
        "S_pair_depth": s_depth,
        "S_pair_mask": s_mask,
        "S_pair_proximity": s_prox,
        "S_pair": pair_score,
    }


def pair_decision(top_score: float, alt_score: float, margin: float) -> Tuple[str, str]:
    if top_score <= 0.0 and alt_score <= 0.0:
        return "pair_unresolved_no_evidence", "no_pair_evidence"
    if (alt_score - top_score) >= margin:
        return "pair_reject_top", "alt_evidence_margin"
    if (top_score - alt_score) >= margin:
        return "pair_support_top", "top_evidence_margin"
    return "pair_ambiguous_defer", "insufficient_pair_margin"


def label_for(labels: Dict[Tuple[str, str], Dict[str, Any]], episode_key: Any, candidate_id: Any) -> Dict[str, Any]:
    return labels.get((str(episode_key), str(candidate_id)), {})


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.pair_observation_plan))
    detector_root = Path(args.detector_root)
    association_path = detector_root / "detector_candidate_associations.jsonl"
    association_rows = load_jsonl(association_path)
    decision_to_plan = plan_decision_index(plan_rows)

    labels: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if args.candidate_decisions:
        labels = labels_for_policy(load_jsonl(Path(args.candidate_decisions)), str(args.label_policy))

    grouped: Dict[str, Dict[str, Any]] = {}
    rows_by_pair_candidate: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for plan in plan_rows:
        key = pair_key(plan)
        if key not in grouped:
            grouped[key] = {
                "pair_observation_id": plan.get("pair_observation_id"),
                "episode_key": plan.get("episode_key"),
                "scene_id": plan.get("scene_id"),
                "query": plan.get("query"),
                "pair_observation_mode": plan.get("pair_observation_mode"),
                "pair_top_candidate_id": plan.get("pair_top_candidate_id"),
                "pair_alt_candidate_id": plan.get("pair_alt_candidate_id"),
                "arbitration_action": plan.get("arbitration_action"),
                "arbitration_reason": plan.get("arbitration_reason"),
                "plan_row_count": 0,
            }
        grouped[key]["plan_row_count"] += 1

    unmatched_association_rows = 0
    for row in association_rows:
        plan = decision_to_plan.get(str(row.get("decision_id")))
        if plan is None:
            unmatched_association_rows += 1
            continue
        key = pair_key(plan)
        candidate_id = str(row.get("candidate_id"))
        rows_by_pair_candidate[(key, candidate_id)].append(row)

    pair_rows: List[Dict[str, Any]] = []
    for key, meta in sorted(grouped.items()):
        top_id = str(meta.get("pair_top_candidate_id"))
        alt_id = str(meta.get("pair_alt_candidate_id"))
        top_support = candidate_support(rows_by_pair_candidate.get((key, top_id), []))
        alt_support = candidate_support(rows_by_pair_candidate.get((key, alt_id), []))
        top_score = float(top_support["S_pair"])
        alt_score = float(alt_support["S_pair"])
        action, reason = pair_decision(top_score, alt_score, float(args.pair_evidence_margin))
        episode_key = meta.get("episode_key")
        top_label = label_for(labels, episode_key, top_id)
        alt_label = label_for(labels, episode_key, alt_id)
        top_correct = top_label.get("candidate_correct")
        alt_correct = alt_label.get("candidate_correct")
        row = {
            "schema_version": SCHEMA_VERSION,
            **meta,
            "pair_top_score": top_score,
            "pair_alt_score": alt_score,
            "pair_evidence_margin_alt_minus_top": alt_score - top_score,
            "pair_evidence_action": action,
            "pair_evidence_reason": reason,
            "pair_has_any_evidence": bool(top_score > 0.0 or alt_score > 0.0),
            "pair_is_disambiguated": action in {"pair_reject_top", "pair_support_top"},
            "top_candidate_correct": top_correct,
            "alt_candidate_correct": alt_correct,
            "pair_rejects_wrong_top": bool(action == "pair_reject_top" and top_correct is False),
            "pair_false_rejects_correct_top": bool(action == "pair_reject_top" and top_correct is True),
            "pair_supports_correct_top": bool(action == "pair_support_top" and top_correct is True),
            "pair_supports_wrong_top": bool(action == "pair_support_top" and top_correct is False),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": bool(top_correct is not None or alt_correct is not None),
        }
        for prefix, support in [("top", top_support), ("alt", alt_support)]:
            for support_key, support_value in support.items():
                row[f"pair_{prefix}_{support_key}"] = support_value
        pair_rows.append(row)

    write_jsonl(out_root / "pair_observation_evidence_rows.jsonl", pair_rows)
    action_counts = Counter(row["pair_evidence_action"] for row in pair_rows)
    mode_counts = Counter(str(row.get("pair_observation_mode")) for row in pair_rows)
    rows_with_gt = [row for row in pair_rows if row.get("top_candidate_correct") is not None]
    wrong_top_rows = [row for row in rows_with_gt if row.get("top_candidate_correct") is False]
    correct_top_rows = [row for row in rows_with_gt if row.get("top_candidate_correct") is True]
    evidence_available_rate = ratio(sum(row["pair_has_any_evidence"] for row in pair_rows), len(pair_rows))
    disambiguation_rate = ratio(sum(row["pair_is_disambiguated"] for row in pair_rows), len(pair_rows))
    wrong_top_reject_rate = ratio(sum(row["pair_rejects_wrong_top"] for row in wrong_top_rows), len(wrong_top_rows))
    false_reject_correct_rate = ratio(
        sum(row["pair_false_rejects_correct_top"] for row in correct_top_rows),
        len(correct_top_rows),
    )
    support_wrong_top_rate = ratio(sum(row["pair_supports_wrong_top"] for row in wrong_top_rows), len(wrong_top_rows))
    gate = {
        "min_pair_evidence_available_rate": float(args.min_pair_evidence_available_rate),
        "min_pair_disambiguation_rate": float(args.min_pair_disambiguation_rate),
        "min_wrong_top_reject_rate": float(args.min_wrong_top_reject_rate),
        "max_false_reject_correct_top_rate": float(args.max_false_reject_correct_top_rate),
        "max_support_wrong_top_rate": float(args.max_support_wrong_top_rate),
        "pair_evidence_available_rate": evidence_available_rate,
        "pair_disambiguation_rate": disambiguation_rate,
        "wrong_top_reject_rate": wrong_top_reject_rate,
        "false_reject_correct_top_rate": false_reject_correct_rate,
        "support_wrong_top_rate": support_wrong_top_rate,
    }
    gate["passes_pair_evidence_diagnostic_gate"] = bool(
        (evidence_available_rate or 0.0) >= float(args.min_pair_evidence_available_rate)
        and (disambiguation_rate or 0.0) >= float(args.min_pair_disambiguation_rate)
        and (wrong_top_reject_rate or 0.0) >= float(args.min_wrong_top_reject_rate)
        and (false_reject_correct_rate or 0.0) <= float(args.max_false_reject_correct_top_rate)
        and (support_wrong_top_rate or 0.0) <= float(args.max_support_wrong_top_rate)
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "pair_observation_plan": str(args.pair_observation_plan),
        "detector_root": str(args.detector_root),
        "candidate_decisions": str(args.candidate_decisions) if args.candidate_decisions else None,
        "label_policy": str(args.label_policy),
        "pair_rows": len(pair_rows),
        "association_rows": len(association_rows),
        "unmatched_association_rows": unmatched_association_rows,
        "mode_counts": dict(sorted(mode_counts.items())),
        "pair_evidence_action_counts": dict(sorted(action_counts.items())),
        "pair_evidence_margin": float(args.pair_evidence_margin),
        "wrong_top_rows": len(wrong_top_rows),
        "correct_top_rows": len(correct_top_rows),
        "gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(labels),
        "output_files": {
            "rows": "pair_observation_evidence_rows.jsonl",
            "summary": "pair_observation_evidence_summary.json",
        },
    }
    write_json(out_root / "pair_observation_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze paired top-vs-alt detector evidence for H001.")
    parser.add_argument("--pair-observation-plan", required=True)
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--candidate-decisions", default=None)
    parser.add_argument("--label-policy", default="RiskResolutionReobserve")
    parser.add_argument("--pair-evidence-margin", type=float, default=0.05)
    parser.add_argument("--min-pair-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-pair-disambiguation-rate", type=float, default=0.30)
    parser.add_argument("--min-wrong-top-reject-rate", type=float, default=0.30)
    parser.add_argument("--max-false-reject-correct-top-rate", type=float, default=0.10)
    parser.add_argument("--max-support-wrong-top-rate", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
