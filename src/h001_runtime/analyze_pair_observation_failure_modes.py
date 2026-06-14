import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.pair_observation_failure_modes.v1"


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
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def label_case(top_correct: Any, alt_correct: Any) -> str:
    if top_correct is True and alt_correct is True:
        return "both_candidates_correct"
    if top_correct is True and alt_correct is False:
        return "top_only_correct"
    if top_correct is False and alt_correct is True:
        return "alt_only_correct"
    if top_correct is False and alt_correct is False:
        return "neither_candidate_correct"
    if top_correct is False:
        return "top_wrong_alt_unknown"
    if top_correct is True:
        return "top_correct_alt_unknown"
    return "unknown_labels"


def pair_key(row: Dict[str, Any]) -> str:
    value = row.get("pair_observation_id")
    if value is not None:
        return str(value)
    return f"{row.get('episode_key')}|{row.get('pair_top_candidate_id')}|{row.get('pair_alt_candidate_id')}"


def candidate_key(row: Dict[str, Any]) -> Tuple[str, str]:
    return pair_key(row), str(row.get("candidate_id"))


def association_stats(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    detector_scores = [safe_float(row.get("best_box_score")) for row in rows]
    detector_scores = [value for value in detector_scores if value is not None]
    visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
    associated_rows = [row for row in rows if row.get("associated_to_candidate") is True]
    mask_hits = [row for row in visible_rows if row.get("projected_pixel_inside_mask") is True]
    box_hits = [row for row in visible_rows if row.get("projected_pixel_inside_box") is True]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
    depth_errors = [value for value in depth_errors if value is not None]
    role_counts = Counter(str(row.get("pair_observation_role")) for row in rows)
    projection_counts = Counter(str(row.get("projection_status")) for row in rows)
    return {
        "association_row_count": len(rows),
        "visible_count": len(visible_rows),
        "associated_count": len(associated_rows),
        "mask_hit_count": len(mask_hits),
        "box_hit_count": len(box_hits),
        "detector_score_max": max(detector_scores, default=0.0),
        "detector_score_mean": sum(detector_scores) / len(detector_scores) if detector_scores else 0.0,
        "depth_error_mean": sum(depth_errors) / len(depth_errors) if depth_errors else None,
        "role_counts": dict(sorted(role_counts.items())),
        "projection_counts": dict(sorted(projection_counts.items())),
    }


def stats_index(association_rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        grouped[candidate_key(row)].append(row)
    return {key: association_stats(rows) for key, rows in grouped.items()}


def metric_margin(row: Dict[str, Any], name: str) -> float:
    top = safe_float(row.get(f"pair_top_{name}")) or 0.0
    alt = safe_float(row.get(f"pair_alt_{name}")) or 0.0
    return top - alt


def classify(row: Dict[str, Any], top_stats: Dict[str, Any], alt_stats: Dict[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    action = str(row.get("pair_evidence_action"))
    mode = str(row.get("pair_observation_mode"))
    top_correct = row.get("top_candidate_correct")
    alt_correct = row.get("alt_candidate_correct")
    case = label_case(top_correct, alt_correct)
    top_score = safe_float(row.get("pair_top_score")) or 0.0
    alt_score = safe_float(row.get("pair_alt_score")) or 0.0
    score_margin_top_minus_alt = top_score - alt_score
    detector_margin_top_minus_alt = metric_margin(row, "detector_score_max")
    assoc_margin_top_minus_alt = metric_margin(row, "strict_association_count")
    visible_margin_top_minus_alt = metric_margin(row, "visible_count")
    tags: List[str] = []

    if case == "both_candidates_correct":
        tags.append("both_candidates_correct_rank_ambiguity")
    if case == "neither_candidate_correct":
        tags.append("neither_candidate_correct_pair_forces_choice")
    if case == "alt_only_correct" and action == "pair_support_top":
        tags.append("wrong_top_supported_when_alt_correct")
    if case == "alt_only_correct" and action == "pair_ambiguous_defer":
        tags.append("alt_correct_but_pair_ambiguous")
    if case == "alt_only_correct" and action == "pair_reject_top":
        tags.append("paired_success_reject_wrong_top")
    if case == "top_only_correct" and action == "pair_reject_top":
        tags.append("false_reject_correct_top")
    if top_correct is False and action == "pair_support_top":
        tags.append("wrong_top_supported_by_pair_score")
    if top_correct is False and action == "pair_reject_top" and alt_correct is not True:
        tags.append("rejects_wrong_top_but_not_to_known_correct_alt")
    if top_correct is True and action == "pair_reject_top" and alt_correct is True:
        tags.append("false_reject_metric_confounded_by_both_correct")

    if top_correct is False and action == "pair_support_top" and detector_margin_top_minus_alt >= float(args.detector_margin_threshold):
        tags.append("wrong_top_supported_by_detector_confidence")
    if top_correct is False and action == "pair_support_top" and assoc_margin_top_minus_alt >= float(args.association_margin_threshold):
        tags.append("wrong_top_supported_by_association_count")

    if mode == "matched_dual_standoff" and action in {"pair_support_top", "pair_reject_top"}:
        tags.append("matched_dual_standoff_raw_scores_not_directly_comparable")
    if mode == "matched_dual_standoff" and abs(visible_margin_top_minus_alt) >= float(args.visible_imbalance_threshold):
        tags.append("matched_dual_standoff_view_opportunity_imbalance")
    if mode == "common_pair_view" and top_correct is False and action == "pair_support_top":
        tags.append("common_pair_view_clutter_or_repeated_category_confusion")
    if action == "pair_unresolved_no_evidence":
        tags.append("pair_unresolved_no_evidence")

    if not tags:
        tags.append("low_risk_or_uncategorized")

    if "paired_success_reject_wrong_top" in tags:
        primary = "paired_success_reject_wrong_top"
    elif "neither_candidate_correct_pair_forces_choice" in tags:
        primary = "neither_candidate_correct_pair_forces_choice"
    elif "both_candidates_correct_rank_ambiguity" in tags:
        primary = "both_candidates_correct_rank_ambiguity"
    elif "wrong_top_supported_by_detector_confidence" in tags:
        primary = "wrong_top_supported_by_detector_confidence"
    elif "wrong_top_supported_by_association_count" in tags:
        primary = "wrong_top_supported_by_association_count"
    elif "wrong_top_supported_when_alt_correct" in tags:
        primary = "wrong_top_supported_when_alt_correct"
    elif "alt_correct_but_pair_ambiguous" in tags:
        primary = "alt_correct_but_pair_ambiguous"
    elif "false_reject_correct_top" in tags:
        primary = "false_reject_correct_top"
    elif "matched_dual_standoff_raw_scores_not_directly_comparable" in tags:
        primary = "matched_dual_standoff_raw_scores_not_directly_comparable"
    else:
        primary = tags[0]

    return {
        "label_case": case,
        "failure_tags": tags,
        "primary_failure_mode": primary,
        "score_margin_top_minus_alt": score_margin_top_minus_alt,
        "detector_margin_top_minus_alt": detector_margin_top_minus_alt,
        "association_count_margin_top_minus_alt": assoc_margin_top_minus_alt,
        "visible_count_margin_top_minus_alt": visible_margin_top_minus_alt,
        "top_association_stats": top_stats,
        "alt_association_stats": alt_stats,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    pair_rows = load_jsonl(Path(args.pair_evidence_rows))
    association_rows = load_jsonl(Path(args.detector_associations))
    candidate_stats = stats_index(association_rows)
    out_rows: List[Dict[str, Any]] = []
    primary_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    label_case_counts: Counter[str] = Counter()
    action_by_label_case: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_mode: Dict[str, Counter[str]] = defaultdict(Counter)
    primary_by_query: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in pair_rows:
        key = pair_key(row)
        top_id = str(row.get("pair_top_candidate_id"))
        alt_id = str(row.get("pair_alt_candidate_id"))
        top_stats = candidate_stats.get((key, top_id), association_stats([]))
        alt_stats = candidate_stats.get((key, alt_id), association_stats([]))
        labels = classify(row, top_stats, alt_stats, args)
        out = {
            "schema_version": SCHEMA_VERSION,
            "pair_observation_id": row.get("pair_observation_id"),
            "episode_key": row.get("episode_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "pair_observation_mode": row.get("pair_observation_mode"),
            "pair_evidence_action": row.get("pair_evidence_action"),
            "pair_evidence_reason": row.get("pair_evidence_reason"),
            "pair_top_candidate_id": row.get("pair_top_candidate_id"),
            "pair_alt_candidate_id": row.get("pair_alt_candidate_id"),
            "top_candidate_correct": row.get("top_candidate_correct"),
            "alt_candidate_correct": row.get("alt_candidate_correct"),
            "pair_top_score": row.get("pair_top_score"),
            "pair_alt_score": row.get("pair_alt_score"),
            "pair_evidence_margin_alt_minus_top": row.get("pair_evidence_margin_alt_minus_top"),
            "pair_top_detector_score_max": row.get("pair_top_detector_score_max"),
            "pair_alt_detector_score_max": row.get("pair_alt_detector_score_max"),
            "pair_top_strict_association_count": row.get("pair_top_strict_association_count"),
            "pair_alt_strict_association_count": row.get("pair_alt_strict_association_count"),
            "pair_top_visible_count": row.get("pair_top_visible_count"),
            "pair_alt_visible_count": row.get("pair_alt_visible_count"),
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": row.get("uses_gt_for_analysis"),
            **labels,
        }
        out_rows.append(out)
        primary_counts[out["primary_failure_mode"]] += 1
        label_case_counts[out["label_case"]] += 1
        action_by_label_case[out["label_case"]][str(out["pair_evidence_action"])] += 1
        primary_by_mode[str(out["pair_observation_mode"])][out["primary_failure_mode"]] += 1
        primary_by_query[str(out["query"])][out["primary_failure_mode"]] += 1
        for tag in out["failure_tags"]:
            tag_counts[tag] += 1

    alt_only_rows = [row for row in out_rows if row["label_case"] == "alt_only_correct"]
    neither_rows = [row for row in out_rows if row["label_case"] == "neither_candidate_correct"]
    both_correct_rows = [row for row in out_rows if row["label_case"] == "both_candidates_correct"]
    top_only_rows = [row for row in out_rows if row["label_case"] == "top_only_correct"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "pair_rows": len(out_rows),
        "pair_evidence_rows": str(args.pair_evidence_rows),
        "detector_associations": str(args.detector_associations),
        "thresholds": {
            "detector_margin_threshold": float(args.detector_margin_threshold),
            "association_margin_threshold": float(args.association_margin_threshold),
            "visible_imbalance_threshold": float(args.visible_imbalance_threshold),
        },
        "primary_failure_mode_counts": dict(sorted(primary_counts.items())),
        "failure_tag_counts": dict(sorted(tag_counts.items())),
        "label_case_counts": dict(sorted(label_case_counts.items())),
        "action_by_label_case": {
            case: dict(sorted(counts.items()))
            for case, counts in sorted(action_by_label_case.items())
        },
        "primary_failure_by_mode": {
            mode: dict(sorted(counts.items()))
            for mode, counts in sorted(primary_by_mode.items())
        },
        "primary_failure_by_query": {
            query: dict(sorted(counts.items()))
            for query, counts in sorted(primary_by_query.items())
        },
        "reinterpreted_rates": {
            "alt_only_correct_rows": len(alt_only_rows),
            "alt_only_correct_reject_top_rate": ratio(
                sum(row["pair_evidence_action"] == "pair_reject_top" for row in alt_only_rows),
                len(alt_only_rows),
            ),
            "alt_only_correct_support_wrong_top_rate": ratio(
                sum(row["pair_evidence_action"] == "pair_support_top" for row in alt_only_rows),
                len(alt_only_rows),
            ),
            "neither_candidate_correct_rows": len(neither_rows),
            "neither_candidate_correct_forced_choice_rate": ratio(
                sum(row["pair_evidence_action"] in {"pair_reject_top", "pair_support_top"} for row in neither_rows),
                len(neither_rows),
            ),
            "both_candidates_correct_rows": len(both_correct_rows),
            "both_candidates_correct_reject_top_rate": ratio(
                sum(row["pair_evidence_action"] == "pair_reject_top" for row in both_correct_rows),
                len(both_correct_rows),
            ),
            "top_only_correct_rows": len(top_only_rows),
            "top_only_correct_false_reject_rate": ratio(
                sum(row["pair_evidence_action"] == "pair_reject_top" for row in top_only_rows),
                len(top_only_rows),
            ),
        },
        "diagnosis": {
            "detector_mask_availability": "not_primary_failure",
            "candidate_association_coverage": "sufficient_for_failure_diagnosis",
            "paired_evidence_objective": "failed",
            "policy_scale_integration": "blocked",
        },
        "revision_requirements": [
            "separate no-valid-candidate cases before forcing top-vs-alt choice",
            "treat both-candidates-correct rows as rank ambiguity rather than wrong-goal failure",
            "normalize matched_dual_standoff evidence before comparing raw top and alt scores",
            "require evidence that disconfirms top or confirms alt, not only detector support for top",
        ],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "pair_observation_failure_modes.jsonl",
            "summary": "pair_observation_failure_mode_summary.json",
        },
    }
    out_root = Path(args.out_root)
    write_jsonl(out_root / "pair_observation_failure_modes.jsonl", out_rows)
    write_json(out_root / "pair_observation_failure_mode_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify H001 paired top-vs-alt evidence failure modes.")
    parser.add_argument("--pair-evidence-rows", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--detector-margin-threshold", type=float, default=0.05)
    parser.add_argument("--association-margin-threshold", type=float, default=1.0)
    parser.add_argument("--visible-imbalance-threshold", type=float, default=2.0)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
