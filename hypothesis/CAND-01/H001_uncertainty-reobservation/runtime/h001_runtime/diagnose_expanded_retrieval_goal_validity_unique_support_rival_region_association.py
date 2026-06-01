import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence

from h001_runtime.extract_dense_conflict_generalization_evidence import scan_forbidden_keys


SCHEMA_VERSION = "h001.unique_support_rival_region_association_repair_diagnostic.v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1.json"
)
OUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1"
)


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def finite_stats(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"count": 0, "min": None, "mean": None, "median": None, "max": None}
    return {
        "count": len(clean),
        "min": min(clean),
        "mean": mean(clean),
        "median": median(clean),
        "max": max(clean),
    }


def counter_dict(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def group_by(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get(key) or "missing")].append(dict(row))
    return grouped


def source_path(args: argparse.Namespace, contract: Dict[str, Any], attr: str, key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if key not in source:
        raise KeyError(f"contract source is missing {key}")
    return Path(str(source[key]))


def decision_id(row: Dict[str, Any]) -> str:
    return str(row.get("decision_id") or "")


def index_by_decision(rows: Sequence[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {decision_id(row): dict(row) for row in rows if decision_id(row)}


def variant_specs(contract: Dict[str, Any]) -> List[Dict[str, Any]]:
    specs = [
        {
            "name": "source_current_strict_v1",
            "mode": "source_current",
            "depth_threshold_m": None,
            "promotable_repair_variant": False,
            "description": "Use associated_to_candidate from the failed detector substrate.",
        }
    ]
    for item in (contract.get("repair_decision") or {}).get("allowed_repair_candidates") or []:
        name = str(item.get("name"))
        if name == "mask_depth_1_25_v1":
            specs.append({**item, "mode": "mask_depth", "depth_threshold_m": 1.25, "promotable_repair_variant": True})
        elif name == "mask_depth_1_5_v1":
            specs.append({**item, "mode": "mask_depth", "depth_threshold_m": 1.5, "promotable_repair_variant": True})
        elif name == "mask_depth_2_0_v1":
            specs.append({**item, "mode": "mask_depth", "depth_threshold_m": 2.0, "promotable_repair_variant": True})
        elif name == "mask_only_upper_bound_v1":
            specs.append({**item, "mode": "mask_only", "depth_threshold_m": None, "promotable_repair_variant": False})
        elif name == "box_only_upper_bound_v1":
            specs.append({**item, "mode": "box_only", "depth_threshold_m": None, "promotable_repair_variant": False})
        else:
            raise ValueError(f"unsupported association repair variant: {name}")
    return specs


def association_hit(row: Dict[str, Any], spec: Dict[str, Any]) -> bool:
    mode = str(spec.get("mode"))
    if mode == "source_current":
        return row.get("associated_to_candidate") is True
    if row.get("projection_status") != "visible":
        return False
    if mode == "mask_only":
        return row.get("projected_pixel_inside_mask") is True
    if mode == "box_only":
        return row.get("projected_pixel_inside_box") is True
    if mode == "mask_depth":
        if row.get("projected_pixel_inside_mask") is not True:
            return False
        depth_error = safe_float(row.get("depth_error_m"))
        threshold = safe_float(spec.get("depth_threshold_m"))
        return depth_error is not None and threshold is not None and depth_error <= threshold
    raise ValueError(f"unsupported variant mode: {mode}")


def source_failure_class(rows: Sequence[Dict[str, Any]], frame_row: Dict[str, Any]) -> str:
    if frame_row.get("has_detector_box") is False:
        return "detector_box_missing"
    if frame_row.get("has_sam2_mask") is False:
        return "sam2_mask_missing"
    if any(row.get("associated_to_candidate") is True for row in rows):
        return "source_associated_success"
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    if not visible:
        return "projection_never_visible"
    inside_mask = [row for row in visible if row.get("projected_pixel_inside_mask") is True]
    inside_box = [row for row in visible if row.get("projected_pixel_inside_box") is True]
    if inside_mask:
        unavailable = [row for row in inside_mask if row.get("depth_check_status") in {None, "unavailable"}]
        if len(unavailable) == len(inside_mask):
            return "mask_overlap_depth_unavailable_only"
        return "mask_overlap_depth_mismatch_or_reject"
    if inside_box:
        return "box_overlap_mask_reject"
    return "visible_projection_no_detector_overlap"


def variant_row(
    decision: str,
    rows: Sequence[Dict[str, Any]],
    frame_row: Dict[str, Any],
    spec: Dict[str, Any],
) -> Dict[str, Any]:
    hits = [row for row in rows if association_hit(row, spec)]
    sample = frame_row or rows[0]
    return {
        "schema_version": SCHEMA_VERSION,
        "variant": spec.get("name"),
        "variant_mode": spec.get("mode"),
        "promotable_repair_variant": bool(spec.get("promotable_repair_variant")),
        "depth_threshold_m": spec.get("depth_threshold_m"),
        "decision_id": decision,
        "episode_key": sample.get("episode_key"),
        "scene_key": sample.get("scene_key"),
        "query": sample.get("query"),
        "expanded_retrieval_request_id": sample.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": sample.get("rival_identity_request_id"),
        "pair_id": sample.get("pair_id"),
        "pair_index": sample.get("pair_index"),
        "target_candidate_id": sample.get("target_candidate_id"),
        "focus_candidate_id": sample.get("focus_candidate_id"),
        "rival_candidate_id": sample.get("rival_candidate_id"),
        "target_candidate_role": sample.get("target_candidate_role"),
        "second_pass_view_role": sample.get("second_pass_view_role"),
        "source_view_role": sample.get("source_view_role"),
        "viewpoint_reused_from_first_pass": sample.get("viewpoint_reused_from_first_pass"),
        "heading_rows": len(rows),
        "variant_associated": bool(hits),
        "variant_associated_heading_count": len(hits),
        "source_has_candidate_association": frame_row.get("has_candidate_association"),
        "source_associated_heading_count": frame_row.get("associated_candidate_heading_count"),
        "source_failure_class": source_failure_class(rows, frame_row),
        "detector_box_count": frame_row.get("detector_box_count"),
        "sam2_mask_count": frame_row.get("sam2_mask_count"),
        "projection_status_counts": counter_dict(row.get("projection_status") for row in rows),
        "depth_check_status_counts": counter_dict(row.get("depth_check_status") for row in rows),
        "inside_mask_heading_count": sum(1 for row in rows if row.get("projected_pixel_inside_mask") is True),
        "inside_box_heading_count": sum(1 for row in rows if row.get("projected_pixel_inside_box") is True),
        "depth_error_m": finite_stats([safe_float(row.get("depth_error_m")) for row in rows]),
        "hit_depth_error_m": finite_stats([safe_float(row.get("depth_error_m")) for row in hits]),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def stratified_rate(rows: Sequence[Dict[str, Any]], key: str) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    for value, group in sorted(group_by(rows, key).items()):
        associated = [row for row in group if row.get("variant_associated") is True]
        output[value] = {
            "rows": len(group),
            "rows_with_candidate_association": len(associated),
            "candidate_association_rate": ratio(len(associated), len(group)),
            "associated_heading_count": sum(int(row.get("variant_associated_heading_count") or 0) for row in group),
        }
    return output


def min_rate(strata: Dict[str, Dict[str, Any]]) -> Optional[float]:
    rates = [
        safe_float(value.get("candidate_association_rate"))
        for value in strata.values()
        if safe_float(value.get("candidate_association_rate")) is not None
    ]
    return min(rates) if rates else None


def variant_summary(
    variant: str,
    rows: Sequence[Dict[str, Any]],
    detector_summary: Dict[str, Any],
    gate: Dict[str, Any],
) -> Dict[str, Any]:
    associated = [row for row in rows if row.get("variant_associated") is True]
    by_query = stratified_rate(rows, "query")
    by_role = stratified_rate(rows, "second_pass_view_role")
    by_scene = stratified_rate(rows, "scene_key")
    by_target_role = stratified_rate(rows, "target_candidate_role")
    action_forbidden = []
    for index, row in enumerate(rows):
        action_forbidden.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])
    global_rate = ratio(len(associated), len(rows))
    min_query_rate = min_rate(by_query)
    min_role_rate = min_rate(by_role)
    promotable = bool(rows and rows[0].get("promotable_repair_variant"))
    summary_gate = {
        "promotable_repair_variant": promotable,
        "detector_box_rate_pass": (safe_float(detector_summary.get("detector_box_rate")) or 0.0)
        >= float(gate.get("detector_box_rate_minimum")),
        "sam2_mask_rate_pass": (safe_float(detector_summary.get("sam2_mask_rate")) or 0.0)
        >= float(gate.get("sam2_mask_rate_minimum")),
        "global_candidate_association_rate_pass": (global_rate or 0.0)
        >= float(gate.get("global_candidate_association_rate_minimum")),
        "minimum_query_candidate_association_rate_pass": (min_query_rate or 0.0)
        >= float(gate.get("minimum_query_candidate_association_rate_minimum")),
        "minimum_second_pass_role_candidate_association_rate_pass": (min_role_rate or 0.0)
        >= float(gate.get("minimum_second_pass_role_candidate_association_rate_minimum")),
        "action_forbidden_key_count_pass": len(action_forbidden) == int(gate.get("action_forbidden_key_count")),
        "terminal_commit_rows_pass": int(gate.get("terminal_commit_rows")) == 0,
        "no_gt_action_pass": gate.get("uses_gt_for_action") is False,
        "paper_claim_allowed_pass": gate.get("paper_claim_allowed") is False,
    }
    summary_gate["repair_gate_passed"] = all(summary_gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "variant": variant,
        "rows": len(rows),
        "associated_rows": len(associated),
        "candidate_association_rate": global_rate,
        "associated_heading_count": sum(int(row.get("variant_associated_heading_count") or 0) for row in rows),
        "source_failure_class_counts": counter_dict(row.get("source_failure_class") for row in rows),
        "by_query": by_query,
        "by_second_pass_view_role": by_role,
        "by_scene_key": by_scene,
        "by_target_candidate_role": by_target_role,
        "minimum_query_candidate_association_rate": min_query_rate,
        "minimum_second_pass_role_candidate_association_rate": min_role_rate,
        "action_forbidden_key_count": len(action_forbidden),
        "action_forbidden_keys": action_forbidden[:20],
        "gate": summary_gate,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }


def build_diagnostic_rows(
    association_rows: Sequence[Dict[str, Any]],
    frame_rows: Sequence[Dict[str, Any]],
    specs: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        grouped[decision_id(row)].append(dict(row))
    frames = index_by_decision(frame_rows)
    diagnostic_rows: List[Dict[str, Any]] = []
    for decision in sorted(grouped):
        frame_row = frames.get(decision)
        if frame_row is None:
            raise KeyError(f"missing detector frame summary for decision_id={decision}")
        for spec in specs:
            diagnostic_rows.append(variant_row(decision, grouped[decision], frame_row, spec))
    return diagnostic_rows


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    out_root = Path(args.out_root)
    detector_summary_path = source_path(args, contract, "detector_summary", "detector_summary")
    detector_frame_summary_path = source_path(
        args, contract, "detector_frame_summary", "detector_frame_summary"
    )
    detector_associations_path = source_path(args, contract, "detector_associations", "detector_associations")

    detector_summary = load_json(detector_summary_path)
    detector_frame_rows = load_jsonl(detector_frame_summary_path)
    association_rows = load_jsonl(detector_associations_path)
    specs = variant_specs(contract)
    diagnostic_rows = build_diagnostic_rows(association_rows, detector_frame_rows, specs)

    gate = contract.get("minimum_repair_gate_for_rerun") or {}
    variant_rows_by_name = group_by(diagnostic_rows, "variant")
    summaries = [
        variant_summary(name, rows, detector_summary, gate)
        for name, rows in sorted(variant_rows_by_name.items())
    ]
    passing = [
        row
        for row in summaries
        if row.get("gate", {}).get("repair_gate_passed") is True
        and row.get("gate", {}).get("promotable_repair_variant") is True
    ]
    allowed_order = [str(spec.get("name")) for spec in specs]
    passing.sort(key=lambda row: allowed_order.index(str(row.get("variant"))))
    selected = passing[0] if passing else None

    diagnostic_gate = contract.get("minimum_diagnostic_gate") or {}
    source_frame_rows = len(detector_frame_rows)
    source_association_rows = len(association_rows)
    repair_summary = {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(out_root),
        "input_files": {
            "detector_summary": str(detector_summary_path),
            "detector_frame_summary": str(detector_frame_summary_path),
            "detector_associations": str(detector_associations_path),
        },
        "source_frame_rows": source_frame_rows,
        "source_association_rows": source_association_rows,
        "variant_count": len(summaries),
        "selected_repair_variant": None if selected is None else selected.get("variant"),
        "selected_repair_variant_summary": selected,
        "repair_gate_passed": selected is not None,
        "rerun_allowed": selected is not None,
        "post_detector_evidence_analyzer_allowed": False,
        "terminal_commit_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "diagnostic_gate": {
            "source_frame_rows_pass": source_frame_rows == int(diagnostic_gate.get("source_frame_rows")),
            "source_association_rows_pass": source_association_rows
            == int(diagnostic_gate.get("source_association_rows")),
            "reports_global_rate": True,
            "reports_by_second_pass_view_role": True,
            "reports_by_query": True,
            "reports_by_scene_key": True,
            "reports_depth_status_counts": True,
            "reports_upper_bound_controls": True,
            "no_gt_action_pass": True,
        },
        "variant_summaries": summaries,
        "output_files": {
            "diagnostic_rows": "unique_support_rival_region_association_diagnostic_rows.jsonl",
            "variant_summary": "unique_support_rival_region_association_variant_summary.json",
            "repair_summary": "unique_support_rival_region_association_repair_summary.json",
        },
        "notes": [
            "This analyzer reuses existing detector/SAM2 association rows and does not rerun perception.",
            "Upper-bound variants are reported for diagnosis only and cannot unlock rerun.",
            "Rerun is allowed only if a promotable fixed non-GT mask-depth variant clears global, query, and role gates.",
        ],
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
    }
    repair_summary["diagnostic_gate"]["diagnostic_gate_passed"] = all(
        bool(value) for value in repair_summary["diagnostic_gate"].values()
    )

    write_jsonl(out_root / "unique_support_rival_region_association_diagnostic_rows.jsonl", diagnostic_rows)
    write_json(out_root / "unique_support_rival_region_association_variant_summary.json", {"variants": summaries})
    write_json(out_root / "unique_support_rival_region_association_repair_summary.json", repair_summary)
    return repair_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose and pre-gate fixed association repair variants for second-pass rival-region evidence."
    )
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--detector-summary")
    parser.add_argument("--detector-frame-summary")
    parser.add_argument("--detector-associations")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
