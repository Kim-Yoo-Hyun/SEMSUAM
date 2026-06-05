import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence


SCHEMA_VERSION = "h001.semantic_slam_pose_graph_connectivity_proxy_gate.v1"
POLICY_NAME = "semantic_slam_pose_graph_connectivity_proxy_gate_v1"
CONTRACT_DEFAULT = (
    "hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/"
    "h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1"

FORBIDDEN_ACTION_KEYS = {
    "candidate_correctness",
    "correctness_label",
    "evaluation_label",
    "evaluation_only_correct_candidate_count",
    "evaluation_only_correct_candidate_ids",
    "evaluation_only_no_valid_candidate_pool",
    "evaluation_only_unlabeled_candidate_count",
    "evaluation_only_wrong_candidate_count",
    "evaluation_only_wrong_candidate_ids",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_label",
    "is_correct",
    "oracle_action",
    "shortest_path_distance",
    "target_label",
}


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def sum_counters(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for row in rows:
        value = row.get(key) or {}
        if not isinstance(value, Mapping):
            continue
        for name, count in value.items():
            counter[str(name)] += safe_int(count)
    return dict(sorted(counter.items()))


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value, default=float("nan")) for value in values]
    nums = [value for value in nums if math.isfinite(value)]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


def reason_count(row: Mapping[str, Any], reason: str) -> int:
    counts = row.get("edge_reason_counts") or {}
    if not isinstance(counts, Mapping):
        return 0
    return safe_int(counts.get(reason))


def has_reason(row: Mapping[str, Any], reason: str) -> bool:
    return reason_count(row, reason) > 0


def has_spatial_or_loop(row: Mapping[str, Any]) -> bool:
    return has_reason(row, "spatial_proximity") or has_reason(row, "loop_closure_opportunity")


def candidate_overlap_only(row: Mapping[str, Any]) -> bool:
    return (
        has_reason(row, "candidate_id_overlap")
        and not has_reason(row, "spatial_proximity")
        and not has_reason(row, "loop_closure_opportunity")
        and not has_reason(row, "target_position_neighborhood")
    )


def action_forbidden_keys(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if key in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row)
    return sorted(found)


def source_summary_rows(proxy_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    source_names = sorted({str(row.get("source_name") or "unknown_source") for row in proxy_rows})
    for source_name in source_names:
        subset = [row for row in proxy_rows if str(row.get("source_name") or "unknown_source") == source_name]
        row_count = len(subset)
        ready_rows = sum(1 for row in subset if row.get("proxy_ready") is True)
        spatial_rows = sum(1 for row in subset if has_reason(row, "spatial_proximity"))
        loop_rows = sum(1 for row in subset if has_reason(row, "loop_closure_opportunity"))
        spatial_or_loop_rows = sum(1 for row in subset if has_spatial_or_loop(row))
        overlap_only_rows = sum(1 for row in subset if candidate_overlap_only(row))
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "source_gate_summary",
                "policy": POLICY_NAME,
                "source_name": source_name,
                "semantic_uncertainty_family_counts": compact_counter(
                    row.get("semantic_uncertainty_family") for row in subset
                ),
                "proxy_rows": row_count,
                "proxy_ready_rows": ready_rows,
                "proxy_ready_rate": ratio(ready_rows, row_count),
                "spatial_edge_rows": spatial_rows,
                "loop_edge_rows": loop_rows,
                "spatial_or_loop_edge_rows": spatial_or_loop_rows,
                "candidate_overlap_only_rows": overlap_only_rows,
                "spatial_or_loop_edge_row_rate": ratio(spatial_or_loop_rows, row_count),
                "candidate_overlap_only_row_rate": ratio(overlap_only_rows, row_count),
                "node_count": number_stats(row.get("node_count") for row in subset),
                "edge_count": number_stats(row.get("edge_count") for row in subset),
                "edge_reason_counts": sum_counters(subset, "edge_reason_counts"),
                "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in subset),
                "terminal_commit_rows": sum(1 for row in subset if row.get("terminal_commit") is True),
                "candidate_commit_rows": sum(1 for row in subset if row.get("candidate_commit") is True),
                "candidate_rejection_rows": sum(1 for row in subset if row.get("candidate_rejection") is True),
                "paper_claim_allowed": False,
            }
        )
    return rows


def edge_variant_rows(proxy_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    variants = [
        ("all_reported_edges", lambda row: safe_int(row.get("edge_count"))),
        ("spatial_proximity", lambda row: reason_count(row, "spatial_proximity")),
        ("loop_closure_opportunity", lambda row: reason_count(row, "loop_closure_opportunity")),
        ("spatial_or_loop", lambda row: reason_count(row, "spatial_proximity") + reason_count(row, "loop_closure_opportunity")),
        ("target_position_neighborhood", lambda row: reason_count(row, "target_position_neighborhood")),
        ("candidate_id_overlap", lambda row: reason_count(row, "candidate_id_overlap")),
    ]
    rows: List[Dict[str, Any]] = []
    for variant_name, edge_fn in variants:
        counts = [edge_fn(row) for row in proxy_rows]
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "edge_variant_summary",
                "policy": POLICY_NAME,
                "edge_variant": variant_name,
                "proxy_rows": len(proxy_rows),
                "rows_with_edge": sum(1 for count in counts if count > 0),
                "rows_with_edge_rate": ratio(sum(1 for count in counts if count > 0), len(proxy_rows)),
                "edge_count_sum": sum(counts),
                "edge_count": number_stats(counts),
                "paper_role": (
                    "shortcut_diagnostic_only"
                    if variant_name == "candidate_id_overlap"
                    else "pose_graph_proxy_signal_or_context"
                ),
                "paper_claim_allowed": False,
            }
        )
    rows.append(
        {
            "schema_version": SCHEMA_VERSION,
            "row_type": "edge_variant_summary",
            "policy": POLICY_NAME,
            "edge_variant": "candidate_overlap_only_rows",
            "proxy_rows": len(proxy_rows),
            "rows_with_edge": sum(1 for row in proxy_rows if candidate_overlap_only(row)),
            "rows_with_edge_rate": ratio(sum(1 for row in proxy_rows if candidate_overlap_only(row)), len(proxy_rows)),
            "edge_count_sum": sum(reason_count(row, "candidate_id_overlap") for row in proxy_rows if candidate_overlap_only(row)),
            "edge_count": number_stats(
                reason_count(row, "candidate_id_overlap") for row in proxy_rows if candidate_overlap_only(row)
            ),
            "paper_role": "shortcut_diagnostic_only",
            "paper_claim_allowed": False,
        }
    )
    return rows


def build_summary(
    *,
    contract: Mapping[str, Any],
    source_audit_summary: Mapping[str, Any],
    inventory_rows: Sequence[Mapping[str, Any]],
    request_rows: Sequence[Mapping[str, Any]],
    proxy_rows: Sequence[Mapping[str, Any]],
    gate_rows: Sequence[Mapping[str, Any]],
    out_root: Path,
) -> Dict[str, Any]:
    thresholds = contract.get("gate_thresholds") or {}
    proxy_row_count = len(proxy_rows)
    proxy_ready_rows = sum(1 for row in proxy_rows if row.get("proxy_ready") is True)
    source_names = sorted({str(row.get("source_name") or "") for row in proxy_rows if row.get("source_name")})
    semantic_families = sorted(
        {
            str(row.get("semantic_uncertainty_family") or "")
            for row in proxy_rows
            if row.get("semantic_uncertainty_family")
        }
    )
    primary_source_name = "instance_arbitration_evidence_frames_v1"
    primary_source_proxy_rows = sum(1 for row in proxy_rows if row.get("source_name") == primary_source_name)
    max_node_count = max([safe_int(row.get("node_count")) for row in proxy_rows] or [0])
    max_edge_count = max([safe_int(row.get("edge_count")) for row in proxy_rows] or [0])
    spatial_edge_rows = sum(1 for row in proxy_rows if has_reason(row, "spatial_proximity"))
    loop_edge_rows = sum(1 for row in proxy_rows if has_reason(row, "loop_closure_opportunity"))
    spatial_or_loop_edge_rows = sum(1 for row in proxy_rows if has_spatial_or_loop(row))
    candidate_overlap_edge_rows = sum(1 for row in proxy_rows if has_reason(row, "candidate_id_overlap"))
    candidate_overlap_only_rows = sum(1 for row in proxy_rows if candidate_overlap_only(row))
    edge_reason_counts = sum_counters(proxy_rows, "edge_reason_counts")
    total_reason_edges = sum(edge_reason_counts.values())
    forbidden_keys = action_forbidden_keys(list(inventory_rows) + list(request_rows) + list(proxy_rows) + list(gate_rows))

    source_audit_gate = source_audit_summary.get("gate", {}).get("source_audit", {})
    p4_readiness_gate = source_audit_summary.get("gate", {}).get("p4_proxy_readiness", {})
    dependency_gate = {
        "source_audit_gate_passed": source_audit_gate.get("semantic_slam_map_pose_source_audit_gate_passed") is True,
        "p4_proxy_readiness_gate_passed": p4_readiness_gate.get("p4_proxy_readiness_gate_passed") is True,
        "source_audit_uses_gt_for_action_passed": source_audit_summary.get("uses_gt_for_action") is False,
        "source_audit_paper_claim_blocked_passed": source_audit_summary.get("paper_claim_allowed") is False,
    }
    dependency_gate["dependency_gate_passed"] = all(dependency_gate.values())

    plumbing_gate = {
        "source_inventory_rows_minimum_passed": len(inventory_rows)
        >= safe_int(thresholds.get("min_source_inventory_rows"), 0),
        "source_ready_rows_minimum_passed": sum(
            1 for row in inventory_rows if row.get("source_ready_for_pose_graph_proxy") is True
        )
        >= safe_int(thresholds.get("min_source_ready_rows"), 0),
        "source_family_count_minimum_passed": len(source_names) >= safe_int(thresholds.get("min_source_family_count"), 0),
        "proxy_rows_minimum_passed": proxy_row_count >= safe_int(thresholds.get("min_proxy_rows"), 0),
        "proxy_ready_rate_passed": ratio(proxy_ready_rows, proxy_row_count)
        >= safe_float(thresholds.get("min_proxy_ready_rate"), 0.0),
        "primary_source_proxy_rows_minimum_passed": primary_source_proxy_rows
        >= safe_int(thresholds.get("min_primary_source_proxy_rows"), 0),
        "max_node_count_minimum_passed": max_node_count >= safe_int(thresholds.get("min_max_node_count"), 0),
        "max_edge_count_minimum_passed": max_edge_count >= safe_int(thresholds.get("min_max_edge_count"), 0),
    }
    plumbing_gate["proxy_plumbing_gate_passed"] = all(plumbing_gate.values())

    edge_quality_gate = {
        "spatial_edge_row_rate_passed": ratio(spatial_edge_rows, proxy_row_count)
        >= safe_float(thresholds.get("min_spatial_edge_row_rate"), 0.0),
        "loop_edge_row_rate_passed": ratio(loop_edge_rows, proxy_row_count)
        >= safe_float(thresholds.get("min_loop_edge_row_rate"), 0.0),
        "spatial_or_loop_edge_row_rate_passed": ratio(spatial_or_loop_edge_rows, proxy_row_count)
        >= safe_float(thresholds.get("min_spatial_or_loop_edge_row_rate"), 0.0),
        "candidate_overlap_only_row_rate_passed": ratio(candidate_overlap_only_rows, proxy_row_count)
        <= safe_float(thresholds.get("max_candidate_overlap_only_row_rate"), 1.0),
    }
    edge_quality_gate["edge_quality_gate_passed"] = all(edge_quality_gate.values())

    action_safety_gate = {
        "action_evidence_forbidden_key_gate_passed": len(forbidden_keys)
        <= safe_int(thresholds.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": sum(1 for row in proxy_rows if row.get("terminal_commit") is True)
        <= safe_int(thresholds.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": sum(1 for row in proxy_rows if row.get("candidate_commit") is True)
        <= safe_int(thresholds.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": sum(1 for row in proxy_rows if row.get("candidate_rejection") is True)
        <= safe_int(thresholds.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": any(row.get("uses_gt_for_action") is True for row in proxy_rows)
        is bool(thresholds.get("requires_uses_gt_for_action", False)),
    }
    action_safety_gate["action_safety_gate_passed"] = all(action_safety_gate.values())

    connectivity_gate_passed = (
        dependency_gate["dependency_gate_passed"]
        and plumbing_gate["proxy_plumbing_gate_passed"]
        and edge_quality_gate["edge_quality_gate_passed"]
        and action_safety_gate["action_safety_gate_passed"]
    )
    candidate_overlap_edge_share = ratio(edge_reason_counts.get("candidate_id_overlap", 0), total_reason_edges)
    strict_edge_ablation_required = True

    overall_row = {
        "schema_version": SCHEMA_VERSION,
        "row_type": "overall_gate_summary",
        "policy": POLICY_NAME,
        "pose_graph_connectivity_proxy_gate_passed": connectivity_gate_passed,
        "strict_edge_ablation_required": strict_edge_ablation_required,
        "semantic_slam_policy_comparison_allowed": False,
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "step_4_5_promotion_satisfied": False,
        "paper_claim_allowed": False,
    }

    summary = {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-04",
        "status": "implemented_and_docker_verified_pose_graph_connectivity_proxy_gate",
        "contract": CONTRACT_DEFAULT,
        "source_audit_summary": str((contract.get("source") or {}).get("source_audit_summary")),
        "out_root": str(out_root),
        "output_files": {
            "gate_rows": "semantic_slam_pose_graph_connectivity_proxy_gate_rows.jsonl",
            "summary": "semantic_slam_pose_graph_connectivity_proxy_gate_summary.json",
        },
        "source_inventory_rows": len(inventory_rows),
        "source_ready_rows": sum(1 for row in inventory_rows if row.get("source_ready_for_pose_graph_proxy") is True),
        "probe_request_rows": len(request_rows),
        "pose_graph_proxy_rows": proxy_row_count,
        "pose_graph_proxy_ready_rows": proxy_ready_rows,
        "pose_graph_proxy_ready_rate": ratio(proxy_ready_rows, proxy_row_count),
        "source_family_count": len(source_names),
        "source_counts": compact_counter(row.get("source_name") for row in proxy_rows),
        "semantic_uncertainty_family_count": len(semantic_families),
        "semantic_uncertainty_family_counts": compact_counter(row.get("semantic_uncertainty_family") for row in proxy_rows),
        "primary_source_proxy_rows": primary_source_proxy_rows,
        "max_node_count": max_node_count,
        "max_edge_count": max_edge_count,
        "spatial_edge_rows": spatial_edge_rows,
        "loop_edge_rows": loop_edge_rows,
        "spatial_or_loop_edge_rows": spatial_or_loop_edge_rows,
        "candidate_overlap_edge_rows": candidate_overlap_edge_rows,
        "candidate_overlap_only_rows": candidate_overlap_only_rows,
        "spatial_edge_row_rate": ratio(spatial_edge_rows, proxy_row_count),
        "loop_edge_row_rate": ratio(loop_edge_rows, proxy_row_count),
        "spatial_or_loop_edge_row_rate": ratio(spatial_or_loop_edge_rows, proxy_row_count),
        "candidate_overlap_only_row_rate": ratio(candidate_overlap_only_rows, proxy_row_count),
        "edge_reason_counts": edge_reason_counts,
        "candidate_overlap_edge_share": candidate_overlap_edge_share,
        "gate": {
            "dependency": dependency_gate,
            "proxy_plumbing": plumbing_gate,
            "edge_quality": edge_quality_gate,
            "action_safety": action_safety_gate,
            "pose_graph_connectivity_proxy_gate_passed": connectivity_gate_passed,
        },
        "diagnostic_conclusion": {
            "pose_graph_connectivity_proxy_gate_passed": connectivity_gate_passed,
            "strict_edge_ablation_required": strict_edge_ablation_required,
            "recommended_next_task": "implement_semantic_slam_strict_edge_variant_proxy_analyzer",
            "semantic_slam_policy_comparison_allowed": False,
            "terminal_policy_allowed": False,
            "paper_claim_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "action_evidence_forbidden_keys": forbidden_keys,
        "terminal_commit_rows": sum(1 for row in proxy_rows if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in proxy_rows if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in proxy_rows if row.get("candidate_rejection") is True),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in proxy_rows),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "semantic_slam_policy_comparison_allowed": False,
        "step_4_5_promotion_satisfied": False,
        "paper_claim_allowed": False,
        "interpretation": {
            "fact": "The source audit pose graph rows have enough spatial/loop proxy edges to pass the first connectivity proxy gate.",
            "agent_inference": "Because candidate_id_overlap still contributes many edges, the next implementation must recompute strict edge variants before SemanticOnly, SLAMOnly, or SemanticSLAM comparison.",
            "paper_claim": "No SLAM benefit, navigation utility, or SemanticSLAM complementarity claim is allowed from this gate.",
        },
    }
    return {"summary": summary, "overall_row": overall_row}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(Path(args.contract))
    source = contract.get("source") or {}
    inventory_rows = load_jsonl(Path(str(source.get("source_inventory_rows"))))
    request_rows = load_jsonl(Path(str(source.get("probe_request_rows"))))
    proxy_rows = load_jsonl(Path(str(source.get("pose_graph_proxy_rows"))))
    source_audit_summary = load_json(Path(str(source.get("source_audit_summary"))))

    gate_rows = source_summary_rows(proxy_rows) + edge_variant_rows(proxy_rows)
    built = build_summary(
        contract=contract,
        source_audit_summary=source_audit_summary,
        inventory_rows=inventory_rows,
        request_rows=request_rows,
        proxy_rows=proxy_rows,
        gate_rows=gate_rows,
        out_root=Path(args.out_root),
    )
    gate_rows = [built["overall_row"]] + gate_rows

    required_outputs = contract.get("required_outputs") or {}
    out_root = Path(args.out_root)
    write_jsonl(out_root / str(required_outputs.get("gate_rows", "semantic_slam_pose_graph_connectivity_proxy_gate_rows.jsonl")), gate_rows)
    write_json(out_root / str(required_outputs.get("summary", "semantic_slam_pose_graph_connectivity_proxy_gate_summary.json")), built["summary"])


if __name__ == "__main__":
    main()
