import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.analyze_object_node_evidence_objective import labels_for_policy, projection_proximity, safe_float


SCHEMA_VERSION = "h001.discriminative_rival_view_evidence.v1"


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


def clip01(value: float) -> float:
    return max(0.0, min(1.0, value))


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
    score = clip01(0.30 * s_det + 0.25 * s_proj + 0.25 * s_depth + 0.10 * s_mask + 0.10 * s_prox)
    return {
        "row_count": len(rows),
        "detector_score_max": s_det,
        "visible_count": len(visible_rows),
        "box_hit_count": len(box_hits),
        "mask_hit_count": len(mask_hits),
        "strict_association_count": len(strict_hits),
        "S_proj": s_proj,
        "S_depth": s_depth,
        "S_mask": s_mask,
        "S_proximity": s_prox,
        "S": score,
    }


def label_for(labels: Dict[Tuple[str, str], Dict[str, Any]], episode_key: Any, candidate_id: Any) -> Dict[str, Any]:
    return labels.get((str(episode_key), str(candidate_id)), {})


def label_case(focus_correct: Any, rival_correct: Any) -> str:
    if focus_correct is True and rival_correct is False:
        return "focus_only_correct"
    if focus_correct is False and rival_correct is True:
        return "rival_only_correct"
    if focus_correct is True and rival_correct is True:
        return "both_correct"
    if focus_correct is False and rival_correct is False:
        return "neither_correct"
    return "unknown"


def support_by_role(
    association_rows: List[Dict[str, Any]],
) -> Dict[Tuple[str, str, str], List[Dict[str, Any]]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        request_id = row.get("rival_identity_request_id")
        candidate_id = row.get("candidate_id")
        role = row.get("viewpoint_pair_role")
        if request_id is None or candidate_id is None or role is None:
            continue
        grouped[(str(request_id), str(candidate_id), str(role))].append(row)
    return grouped


def decision(focus_score: float, rival_score: float, margin: float) -> Tuple[str, str, Optional[str]]:
    if focus_score <= 0.0 and rival_score <= 0.0:
        return "discriminative_unresolved_no_evidence", "no_discriminative_evidence", None
    if (focus_score - rival_score) >= margin:
        return "discriminative_support_focus", "focus_identity_margin", "focus"
    if (rival_score - focus_score) >= margin:
        return "discriminative_support_rival", "rival_identity_margin", "rival"
    return "discriminative_ambiguous_defer", "insufficient_identity_margin", None


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.plan_rows))
    association_rows = load_jsonl(Path(args.detector_associations))
    role_rows = support_by_role(association_rows)

    labels: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if args.candidate_decisions:
        labels = labels_for_policy(load_jsonl(Path(args.candidate_decisions)), str(args.label_policy))

    grouped_plan: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in plan_rows:
        request_id = row.get("rival_identity_request_id")
        if request_id is not None:
            grouped_plan[str(request_id)].append(row)

    evidence_rows: List[Dict[str, Any]] = []
    for request_id, rows in sorted(grouped_plan.items()):
        first = rows[0]
        focus_id = str(first.get("focus_candidate_id"))
        rival_id = str(first.get("rival_candidate_id"))
        episode_key = first.get("episode_key")

        focus_focus = candidate_support(role_rows.get((request_id, focus_id, "focus"), []))
        focus_common = candidate_support(role_rows.get((request_id, focus_id, "common"), []))
        focus_rival = candidate_support(role_rows.get((request_id, focus_id, "rival"), []))
        rival_rival = candidate_support(role_rows.get((request_id, rival_id, "rival"), []))
        rival_common = candidate_support(role_rows.get((request_id, rival_id, "common"), []))
        rival_focus = candidate_support(role_rows.get((request_id, rival_id, "focus"), []))

        focus_target_score = 0.65 * float(focus_focus["S"]) + 0.35 * float(focus_common["S"])
        rival_target_score = 0.65 * float(rival_rival["S"]) + 0.35 * float(rival_common["S"])
        focus_leak_score = float(focus_rival["S"])
        rival_leak_score = float(rival_focus["S"])
        focus_identity_score = clip01(focus_target_score - float(args.cross_view_leak_penalty) * focus_leak_score)
        rival_identity_score = clip01(rival_target_score - float(args.cross_view_leak_penalty) * rival_leak_score)
        action, reason, preferred_role = decision(focus_identity_score, rival_identity_score, float(args.identity_margin))

        focus_label = label_for(labels, episode_key, focus_id)
        rival_label = label_for(labels, episode_key, rival_id)
        focus_correct = focus_label.get("candidate_correct")
        rival_correct = rival_label.get("candidate_correct")
        preferred_candidate_id = None
        preferred_correct = None
        if preferred_role == "focus":
            preferred_candidate_id = focus_id
            preferred_correct = focus_correct
        elif preferred_role == "rival":
            preferred_candidate_id = rival_id
            preferred_correct = rival_correct

        row = {
            "schema_version": SCHEMA_VERSION,
            "rival_identity_request_id": request_id,
            "episode_key": episode_key,
            "scene_id": first.get("scene_id"),
            "scene_key": first.get("scene_key"),
            "query": first.get("query"),
            "focus_candidate_id": focus_id,
            "rival_candidate_id": rival_id,
            "plan_row_count": len(rows),
            "focus_identity_score": focus_identity_score,
            "rival_identity_score": rival_identity_score,
            "identity_margin_focus_minus_rival": focus_identity_score - rival_identity_score,
            "focus_target_score": focus_target_score,
            "rival_target_score": rival_target_score,
            "focus_cross_leak_score": focus_leak_score,
            "rival_cross_leak_score": rival_leak_score,
            "discriminative_action": action,
            "discriminative_reason": reason,
            "preferred_role": preferred_role,
            "preferred_candidate_id": preferred_candidate_id,
            "focus_candidate_correct": focus_correct,
            "rival_candidate_correct": rival_correct,
            "label_case": label_case(focus_correct, rival_correct),
            "preferred_candidate_correct": preferred_correct,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": bool(focus_correct is not None or rival_correct is not None),
        }
        for prefix, support in [
            ("focus_own", focus_focus),
            ("focus_common", focus_common),
            ("focus_cross", focus_rival),
            ("rival_own", rival_rival),
            ("rival_common", rival_common),
            ("rival_cross", rival_focus),
        ]:
            for key, value in support.items():
                row[f"{prefix}_{key}"] = value
        evidence_rows.append(row)

    write_jsonl(out_root / "discriminative_rival_view_evidence_rows.jsonl", evidence_rows)

    action_counts = Counter(row["discriminative_action"] for row in evidence_rows)
    label_counts = Counter(row["label_case"] for row in evidence_rows)
    query_counts = Counter(str(row.get("query")) for row in evidence_rows)
    rows_with_evidence = [
        row for row in evidence_rows if row["focus_identity_score"] > 0.0 or row["rival_identity_score"] > 0.0
    ]
    disambiguated = [
        row
        for row in evidence_rows
        if row["discriminative_action"] in {"discriminative_support_focus", "discriminative_support_rival"}
    ]
    single_correct = [row for row in evidence_rows if row["label_case"] in {"focus_only_correct", "rival_only_correct"}]
    single_correct_preferred = [
        row for row in single_correct if row.get("preferred_candidate_correct") is True
    ]
    single_correct_wrong_preferred = [
        row for row in single_correct if row.get("preferred_candidate_correct") is False
    ]
    gate = {
        "min_evidence_available_rate": float(args.min_evidence_available_rate),
        "min_disambiguation_rate": float(args.min_disambiguation_rate),
        "max_wrong_preference_rate": float(args.max_wrong_preference_rate),
        "evidence_available_rate": ratio(len(rows_with_evidence), len(evidence_rows)),
        "disambiguation_rate": ratio(len(disambiguated), len(evidence_rows)),
        "single_correct_preferred_rate": ratio(len(single_correct_preferred), len(single_correct)),
        "single_correct_wrong_preference_rate": ratio(len(single_correct_wrong_preferred), len(single_correct)),
        "no_gt_action_pass": True,
    }
    gate["passes_discriminative_evidence_diagnostic_gate"] = bool(
        (gate["evidence_available_rate"] or 0.0) >= float(args.min_evidence_available_rate)
        and (gate["disambiguation_rate"] or 0.0) >= float(args.min_disambiguation_rate)
        and (gate["single_correct_wrong_preference_rate"] or 0.0) <= float(args.max_wrong_preference_rate)
        and gate["no_gt_action_pass"]
    )
    summary = {
        "schema_version": SCHEMA_VERSION,
        "plan_rows": str(args.plan_rows),
        "detector_associations": str(args.detector_associations),
        "candidate_decisions": str(args.candidate_decisions) if args.candidate_decisions else None,
        "label_policy": str(args.label_policy),
        "request_rows": len(evidence_rows),
        "association_rows": len(association_rows),
        "action_counts": dict(sorted(action_counts.items())),
        "label_case_counts": dict(sorted(label_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "identity_margin": float(args.identity_margin),
        "cross_view_leak_penalty": float(args.cross_view_leak_penalty),
        "gate": gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": bool(labels),
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "discriminative_rival_view_evidence_rows.jsonl",
            "summary": "discriminative_rival_view_evidence_summary.json",
        },
    }
    write_json(out_root / "discriminative_rival_view_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze focus-rival discriminative view evidence for H001.")
    parser.add_argument("--plan-rows", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--candidate-decisions", default=None)
    parser.add_argument("--label-policy", default="NoReobserve")
    parser.add_argument("--identity-margin", type=float, default=0.05)
    parser.add_argument("--cross-view-leak-penalty", type=float, default=0.35)
    parser.add_argument("--min-evidence-available-rate", type=float, default=0.50)
    parser.add_argument("--min-disambiguation-rate", type=float, default=0.20)
    parser.add_argument("--max-wrong-preference-rate", type=float, default=0.25)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
