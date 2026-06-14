import argparse
import json
import math
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from analyze_postview_detector_v3c import (
    add_objective_fields,
    aggregate_candidate_rows,
    baseline_top_index,
    build_episode_table,
    build_summary,
    candidate_label_index,
    candidate_auc,
    load_jsonl,
    selector_summary,
    write_json,
    write_jsonl,
)


SCHEMA_VERSION = "h001.detector_association_variants.v1"


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def association_hit(row: Dict[str, Any], inside_mode: str, depth_tolerance_m: Optional[float]) -> bool:
    if row.get("projection_status") != "visible":
        return False
    if inside_mode == "mask":
        inside = row.get("projected_pixel_inside_mask") is True
    elif inside_mode == "box_or_mask":
        inside = row.get("projected_pixel_inside_mask") is True or row.get("projected_pixel_inside_box") is True
    else:
        raise ValueError(f"unsupported inside_mode: {inside_mode}")
    if not inside:
        return False
    depth_agreement = safe_float(row.get("depth_agreement_m"))
    return depth_tolerance_m is None or depth_agreement is None or depth_agreement <= depth_tolerance_m


def variant_rows(
    rows: List[Dict[str, Any]],
    variant_name: str,
    inside_mode: str,
    depth_tolerance_m: Optional[float],
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for row in rows:
        item = deepcopy(row)
        item["association_variant"] = variant_name
        item["association_inside_mode"] = inside_mode
        item["association_depth_tolerance_m"] = depth_tolerance_m
        item["associated_to_candidate"] = association_hit(item, inside_mode, depth_tolerance_m)
        out.append(item)
    return out


def query_association_summary(episode_rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, int]] = {}
    for row in episode_rows:
        query = str(row.get("query"))
        grouped.setdefault(query, {"rows": 0, "any_association": 0})
        grouped[query]["rows"] += 1
        grouped[query]["any_association"] += int(row.get("any_association") is True)
    return {
        query: {
            "rows": values["rows"],
            "rows_with_any_association": values["any_association"],
            "rows_with_any_association_rate": ratio(values["any_association"], values["rows"]),
        }
        for query, values in sorted(grouped.items())
    }


def analyze_variant(
    name: str,
    inside_mode: str,
    depth_tolerance_m: Optional[float],
    association_rows: List[Dict[str, Any]],
    labels: Dict[Any, Dict[str, Any]],
    baseline_top: Dict[str, Dict[str, Any]],
    min_association_rate: float,
    min_candidate_auc: float,
    switch_margin: float,
) -> Dict[str, Any]:
    rows = variant_rows(association_rows, name, inside_mode, depth_tolerance_m)
    candidate_table = aggregate_candidate_rows(rows, labels)
    add_objective_fields(candidate_table)
    selector_fields = [
        "associated_count",
        "inside_mask_count",
        "best_box_score_max",
        "O7_extent_prior",
        "O10_category_best_switch",
    ]
    episode_table = build_episode_table(candidate_table, baseline_top, selector_fields, switch_margin)
    summary = build_summary(
        candidate_table,
        episode_table,
        selector_fields,
        min_association_rate,
        min_candidate_auc,
    )
    summary.update(
        {
            "schema_version": SCHEMA_VERSION,
            "variant": name,
            "inside_mode": inside_mode,
            "depth_tolerance_m": depth_tolerance_m,
            "associated_count_auc": candidate_auc(candidate_table, "associated_count"),
            "associated_count_selector": selector_summary(episode_table, "associated_count"),
            "query_association": query_association_summary(episode_table),
        }
    )
    return {
        "summary": summary,
        "candidate_table": candidate_table,
        "episode_table": episode_table,
    }


def default_variants() -> List[Dict[str, Any]]:
    specs: List[Dict[str, Any]] = []
    for inside_mode in ("mask", "box_or_mask"):
        for tolerance in (1.0, 1.5, 2.0, 3.0, 5.0, None):
            tolerance_label = "none" if tolerance is None else str(tolerance).replace(".", "p")
            specs.append(
                {
                    "name": f"{inside_mode}_depth_{tolerance_label}",
                    "inside_mode": inside_mode,
                    "depth_tolerance_m": tolerance,
                }
            )
    return specs


def write_variant_summaries(out: Path, rows: Iterable[Dict[str, Any]]) -> None:
    write_jsonl(out / "variant_summaries.jsonl", rows)


def run(args: argparse.Namespace) -> Dict[str, Any]:
    detector_root = Path(args.detector_root)
    out = Path(args.out)
    association_rows = load_jsonl(detector_root / "detector_candidate_associations.jsonl")
    decision_rows = load_jsonl(Path(args.candidate_decisions))
    labels = candidate_label_index(decision_rows, args.policy)
    baseline_top = baseline_top_index(decision_rows, args.policy)

    variant_results = []
    for spec in default_variants():
        result = analyze_variant(
            str(spec["name"]),
            str(spec["inside_mode"]),
            spec["depth_tolerance_m"],
            association_rows,
            labels,
            baseline_top,
            float(args.min_association_rate),
            float(args.min_candidate_auc),
            float(args.switch_margin),
        )
        variant_results.append(result)

    summaries = [result["summary"] for result in variant_results]
    ranked = sorted(
        summaries,
        key=lambda row: (
            row["gate"]["passes_detector_calibration_gate"] is True,
            row.get("associated_count_auc") or -1.0,
            row.get("rows_with_any_association_rate") or -1.0,
            row.get("best_selected_correct_delta_on_all_rows") or -1.0,
        ),
        reverse=True,
    )
    best = ranked[0] if ranked else {}
    out.mkdir(parents=True, exist_ok=True)
    write_variant_summaries(out, summaries)
    for result in variant_results:
        name = str(result["summary"]["variant"])
        write_jsonl(out / f"{name}_candidate_calibration.jsonl", result["candidate_table"])
        write_jsonl(out / f"{name}_episode_calibration.jsonl", result["episode_table"])
    report = {
        "schema_version": SCHEMA_VERSION,
        "detector_root": str(detector_root),
        "candidate_decisions": str(args.candidate_decisions),
        "policy": args.policy,
        "variant_count": len(summaries),
        "best_variant": best.get("variant"),
        "best_variant_summary": best,
        "variants": summaries,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }
    write_json(out / "summary.json", report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare detector-object association variants on an existing v3c artifact.")
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--policy", default="NoReobserve")
    parser.add_argument("--min-association-rate", type=float, default=0.60)
    parser.add_argument("--min-candidate-auc", type=float, default=0.65)
    parser.add_argument("--switch-margin", type=float, default=0.0)
    args = parser.parse_args()
    report = run(args)
    print(json.dumps(report["best_variant_summary"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
