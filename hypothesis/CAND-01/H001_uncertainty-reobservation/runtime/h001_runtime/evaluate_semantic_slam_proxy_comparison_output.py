import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_proxy_comparison_output_evaluation.v1"
INPUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_proxy_comparison_v1"
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_proxy_comparison_output_evaluation_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def join_key(row: Mapping[str, Any]) -> Tuple[str, ...]:
    key = row.get("join_key")
    if isinstance(key, Mapping):
        return (
            str(key.get("source_name") or ""),
            str(key.get("scene_key") or ""),
            str(key.get("query") or ""),
            str(key.get("request_id") or ""),
            str(key.get("episode_key") or ""),
        )
    return (
        str(row.get("source_name") or ""),
        str(row.get("scene_key") or ""),
        str(row.get("query") or ""),
        str(row.get("request_id") or ""),
        str(row.get("episode_key") or ""),
    )


def group_by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]]:
    groups: Dict[Tuple[str, ...], Dict[str, Mapping[str, Any]]] = {}
    for row in rows:
        groups.setdefault(join_key(row), {})[str(row.get("policy_name") or "")] = row
    return groups


def row_float(row: Mapping[str, Any], key: str) -> float:
    return safe_float(row.get(key), 0.0) or 0.0


def evaluate_groups(groups: Mapping[Tuple[str, ...], Mapping[str, Mapping[str, Any]]]) -> List[Dict[str, Any]]:
    eval_rows: List[Dict[str, Any]] = []
    for key, policies in sorted(groups.items()):
        semantic = policies.get("SemanticOnly") or {}
        slam = policies.get("SLAMOnly") or {}
        combined = policies.get("SemanticSLAM") or {}
        reference = policies.get("NoReobserveReference") or {}
        semantic_utility = row_float(semantic, "policy_proxy_utility")
        slam_utility = row_float(slam, "policy_proxy_utility")
        combined_utility = row_float(combined, "policy_proxy_utility")
        component_max = max(semantic_utility, slam_utility)
        component_min = min(semantic_utility, slam_utility)
        component_gap = abs(semantic_utility - slam_utility)
        midpoint = 0.5 * semantic_utility + 0.5 * slam_utility
        midpoint_error = combined_utility - midpoint
        if semantic_utility > slam_utility:
            component_winner = "SemanticOnly"
        elif slam_utility > semantic_utility:
            component_winner = "SLAMOnly"
        else:
            component_winner = "tie"
        if component_gap <= 1e-9:
            dominance_class = "component_tie_midpoint_equal"
        elif combined_utility < component_max:
            dominance_class = "semantic_slam_midpoint_strictly_dominated_by_best_component"
        else:
            dominance_class = "unexpected_non_dominated_combination"
        eval_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "semantic_slam_proxy_comparison_group_evaluation",
                "join_key": combined.get("join_key") or semantic.get("join_key") or slam.get("join_key"),
                "source_name": combined.get("source_name") or semantic.get("source_name") or slam.get("source_name"),
                "scene_key": combined.get("scene_key") or semantic.get("scene_key") or slam.get("scene_key"),
                "query": combined.get("query") or semantic.get("query") or slam.get("query"),
                "request_id": combined.get("request_id") or semantic.get("request_id") or slam.get("request_id"),
                "episode_key": combined.get("episode_key") or semantic.get("episode_key") or slam.get("episode_key"),
                "semantic_uncertainty_family": combined.get("semantic_uncertainty_family")
                or semantic.get("semantic_uncertainty_family")
                or slam.get("semantic_uncertainty_family"),
                "component_winner": component_winner,
                "dominance_class": dominance_class,
                "semantic_only_utility": semantic_utility,
                "slam_only_utility": slam_utility,
                "semantic_slam_utility": combined_utility,
                "no_reobserve_utility": row_float(reference, "policy_proxy_utility"),
                "component_max_utility": component_max,
                "component_min_utility": component_min,
                "component_gap": component_gap,
                "best_component_margin_over_semantic_slam": component_max - combined_utility,
                "semantic_slam_midpoint_identity_error": midpoint_error,
                "semantic_score": row_float(combined, "semantic_score"),
                "slam_gap_score": row_float(combined, "slam_gap_score"),
                "semantic_minus_slam_score": row_float(combined, "semantic_score") - row_float(combined, "slam_gap_score"),
                "travel_penalty": row_float(combined, "travel_penalty"),
                "canonical_proxy_ready": combined.get("canonical_proxy_ready") is True,
                "loop_edge_available": safe_int(combined.get("loop_edge_count"), 0) > 0,
                "canonical_edge_count": safe_int(combined.get("canonical_edge_count"), 0),
                "loop_edge_count": safe_int(combined.get("loop_edge_count"), 0),
                "canonical_largest_component_fraction": row_float(combined, "canonical_largest_component_fraction"),
                "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in policies.values()),
                "paper_claim_allowed": False,
                "step_4_5_promotion_satisfied": False,
            }
        )
    return eval_rows


def build_summary(
    *,
    source_summary: Mapping[str, Any],
    group_rows: Sequence[Mapping[str, Any]],
    input_root: Path,
    out_root: Path,
) -> Dict[str, Any]:
    total = len(group_rows)
    strict_dominated = sum(
        1
        for row in group_rows
        if row.get("dominance_class") == "semantic_slam_midpoint_strictly_dominated_by_best_component"
    )
    unexpected = sum(1 for row in group_rows if row.get("dominance_class") == "unexpected_non_dominated_combination")
    midpoint_error_abs_max = max([abs(row_float(row, "semantic_slam_midpoint_identity_error")) for row in group_rows] or [0.0])
    component_winner_counts = compact_counter(row.get("component_winner") for row in group_rows)
    family_winner_counts = compact_counter(
        f"{row.get('semantic_uncertainty_family')}::{row.get('component_winner')}" for row in group_rows
    )
    semantic_score_dominant_rows = sum(1 for row in group_rows if row_float(row, "semantic_minus_slam_score") > 0)
    slam_score_dominant_rows = sum(1 for row in group_rows if row_float(row, "semantic_minus_slam_score") < 0)
    equal_score_rows = total - semantic_score_dominant_rows - slam_score_dominant_rows
    gate = {
        "source_proxy_comparison_gate_passed": bool(
            ((source_summary.get("gate") or {}).get("semantic_slam_proxy_comparison_gate_passed"))
        ),
        "no_gt_action_leakage_passed": not bool(source_summary.get("uses_gt_for_action")),
        "no_paper_claim_passed": source_summary.get("paper_claim_allowed") is False,
        "midpoint_identity_passed": midpoint_error_abs_max <= 1e-9,
        "dominance_diagnostic_passed": strict_dominated == total and unexpected == 0,
    }
    gate["output_evaluation_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-04",
        "status": "completed_semantic_slam_proxy_output_evaluation",
        "input_root": str(input_root),
        "out_root": str(out_root),
        "source_summary": str(input_root / "semantic_slam_proxy_comparison_summary.json"),
        "output_files": {
            "group_evaluation_rows": "semantic_slam_proxy_comparison_group_evaluation_rows.jsonl",
            "summary": "semantic_slam_proxy_comparison_output_evaluation_summary.json",
        },
        "request_groups": total,
        "component_winner_counts": component_winner_counts,
        "component_winner_rates": {key: ratio(value, total) for key, value in component_winner_counts.items()},
        "family_winner_counts": family_winner_counts,
        "dominance_class_counts": compact_counter(row.get("dominance_class") for row in group_rows),
        "semantic_score_dominant_rows": semantic_score_dominant_rows,
        "slam_score_dominant_rows": slam_score_dominant_rows,
        "equal_score_rows": equal_score_rows,
        "strict_dominated_rows": strict_dominated,
        "strict_dominated_rate": ratio(strict_dominated, total),
        "unexpected_non_dominated_rows": unexpected,
        "midpoint_identity_abs_error_max": midpoint_error_abs_max,
        "best_component_margin_over_semantic_slam_stats": stats(
            row.get("best_component_margin_over_semantic_slam") for row in group_rows
        ),
        "component_gap_stats": stats(row.get("component_gap") for row in group_rows),
        "semantic_minus_slam_score_stats": stats(row.get("semantic_minus_slam_score") for row in group_rows),
        "canonical_proxy_ready_rate": ratio(sum(1 for row in group_rows if row.get("canonical_proxy_ready") is True), total),
        "loop_edge_availability_rate": ratio(sum(1 for row in group_rows if row.get("loop_edge_available") is True), total),
        "source_policy_rank1_rows": source_summary.get("policy_rank1_rows"),
        "source_policy_rank1_rates": source_summary.get("policy_rank1_rates"),
        "gate": gate,
        "step_4_5_promotion_satisfied": False,
        "terminal_utility_validation_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "paper_claim_allowed": False,
        "decision": {
            "promotion_decision": "do_not_promote",
            "utility_redesign_required": True,
            "richer_slam_proxy_recommended": True,
            "recommended_next_task": "freeze_non_dominated_semantic_slam_proxy_redesign_contract",
        },
        "interpretation": {
            "fact": "SemanticSLAM is exactly the midpoint of SemanticOnly and SLAMOnly utilities in the current proxy output.",
            "agent_inference": "A midpoint scalar utility is structurally dominated by the better component under score-only ranking, so zero SemanticSLAM rank-1 rows is expected and not a dataset-specific failure alone.",
            "paper_claim": "No SemanticSLAM complementarity, navigation utility, or Step 4-5 SLAM benefit claim is allowed from this output.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()
    input_root = Path(args.input_root)
    out_root = Path(args.out_root)
    comparison_rows = load_jsonl(input_root / "semantic_slam_proxy_comparison_rows.jsonl")
    source_summary = load_json(input_root / "semantic_slam_proxy_comparison_summary.json")
    group_rows = evaluate_groups(group_by_request(comparison_rows))
    summary = build_summary(
        source_summary=source_summary,
        group_rows=group_rows,
        input_root=input_root,
        out_root=out_root,
    )
    write_jsonl(out_root / "semantic_slam_proxy_comparison_group_evaluation_rows.jsonl", group_rows)
    write_json(out_root / "semantic_slam_proxy_comparison_output_evaluation_summary.json", summary)


if __name__ == "__main__":
    main()
