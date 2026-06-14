import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from h001_runtime.audit_semantic_slam_map_pose_consistency_sources import (
    build_nodes,
    compact_counter,
    connected_component_sizes,
    distance_xz,
    read_source,
    request_group_key,
    safe_float,
    safe_int,
    semantic_family_for_source,
    source_definitions,
)


SCHEMA_VERSION = "h001.semantic_slam_strict_edge_variant_proxy.v1"
POLICY_NAME = "semantic_slam_strict_edge_variant_proxy_v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_strict_edge_variant_proxy_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_strict_edge_variant_proxy_v1"

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


def ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def number_stats(values: Iterable[Any]) -> Dict[str, Optional[float]]:
    nums = [safe_float(value) for value in values]
    nums = [value for value in nums if value is not None and math.isfinite(value)]
    if not nums:
        return {"count": 0, "min": None, "mean": None, "max": None}
    return {"count": len(nums), "min": min(nums), "mean": sum(nums) / len(nums), "max": max(nums)}


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


def edge_reasons_for_nodes(
    nodes: Sequence[Mapping[str, Any]],
    *,
    spatial_threshold_m: float,
    target_neighborhood_threshold_m: float,
    loop_closure_threshold_m: float,
) -> Dict[Tuple[int, int], set[str]]:
    edge_reasons: Dict[Tuple[int, int], set[str]] = defaultdict(set)
    for i, left in enumerate(nodes):
        for j in range(i + 1, len(nodes)):
            right = nodes[j]
            viewpoint_distance = distance_xz(left["viewpoint_position"], right["viewpoint_position"])
            if viewpoint_distance <= spatial_threshold_m:
                edge_reasons[(i, j)].add("spatial_proximity")
            if viewpoint_distance <= loop_closure_threshold_m:
                edge_reasons[(i, j)].add("loop_closure_opportunity")
            left_candidates = set(left["candidate_ids"])
            right_candidates = set(right["candidate_ids"])
            if left_candidates and right_candidates and left_candidates & right_candidates:
                edge_reasons[(i, j)].add("candidate_id_overlap")
            left_target = left.get("target_position")
            right_target = right.get("target_position")
            if left_target is not None and right_target is not None:
                target_distance = distance_xz(left_target, right_target)
                if target_distance <= target_neighborhood_threshold_m:
                    edge_reasons[(i, j)].add("target_position_neighborhood")
    return edge_reasons


def edge_reason_counts(edge_reasons: Mapping[Tuple[int, int], set[str]], allowed_reasons: set[str]) -> Dict[str, int]:
    counter: Counter[str] = Counter()
    for reasons in edge_reasons.values():
        for reason in sorted(reasons & allowed_reasons):
            counter[reason] += 1
    return dict(sorted(counter.items()))


def variant_edges(
    edge_reasons: Mapping[Tuple[int, int], set[str]],
    allowed_reasons: set[str],
) -> List[Tuple[int, int]]:
    return sorted(edge for edge, reasons in edge_reasons.items() if reasons & allowed_reasons)


def build_grouped_source_rows(
    *,
    source_audit_contract: Mapping[str, Any],
    inventory_rows: Sequence[Mapping[str, Any]],
) -> Tuple[Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]], Dict[str, str], Dict[str, str]]:
    inventory_by_source = {str(row.get("source_name")): row for row in inventory_rows}
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    source_roles: Dict[str, str] = {}
    source_families: Dict[str, str] = {}
    for source in source_definitions(source_audit_contract):
        source_name = str(source.get("name") or "unknown_source")
        inventory = inventory_by_source.get(source_name) or {}
        if inventory.get("source_ready_for_pose_graph_proxy") is not True:
            continue
        payload = read_source(source)
        source_roles[source_name] = str(source.get("source_role") or "support")
        source_families[source_name] = semantic_family_for_source(source_name)
        for row in payload["rows"]:
            grouped[request_group_key(source_name, row)].append(row)
    return grouped, source_roles, source_families


def strict_variant_rows(
    *,
    grouped: Mapping[Tuple[str, str, str, str, str], Sequence[Mapping[str, Any]]],
    source_roles: Mapping[str, str],
    source_families: Mapping[str, str],
    variants: Sequence[Mapping[str, Any]],
    spatial_threshold_m: float,
    target_neighborhood_threshold_m: float,
    loop_closure_threshold_m: float,
) -> List[Dict[str, Any]]:
    output_rows: List[Dict[str, Any]] = []
    for key, rows in sorted(grouped.items()):
        source_name, scene_key, query, request_id, episode_key = key
        nodes = build_nodes(rows)
        edge_reasons = edge_reasons_for_nodes(
            nodes,
            spatial_threshold_m=spatial_threshold_m,
            target_neighborhood_threshold_m=target_neighborhood_threshold_m,
            loop_closure_threshold_m=loop_closure_threshold_m,
        )
        all_reason_counts = edge_reason_counts(
            edge_reasons,
            {
                "spatial_proximity",
                "loop_closure_opportunity",
                "target_position_neighborhood",
                "candidate_id_overlap",
            },
        )
        for variant in variants:
            variant_name = str(variant.get("name") or "unknown_variant")
            allowed_reasons = {str(reason) for reason in variant.get("allowed_reasons") or []}
            selected_edges = variant_edges(edge_reasons, allowed_reasons)
            component_sizes = connected_component_sizes(len(nodes), selected_edges) if nodes else []
            largest = component_sizes[0] if component_sizes else 0
            edge_count = len(selected_edges)
            node_count = len(nodes)
            proxy_ready = node_count >= 2 and edge_count >= 1
            output_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_semantic_slam_strict_edge_variant_proxy",
                    "row_type": "strict_edge_variant_proxy",
                    "policy": POLICY_NAME,
                    "source_name": source_name,
                    "source_role": source_roles.get(source_name, "support"),
                    "semantic_uncertainty_family": source_families.get(
                        source_name, "unknown_semantic_uncertainty_family"
                    ),
                    "scene_key": scene_key,
                    "scene_id": next((row.get("scene_id") for row in rows if row.get("scene_id")), None),
                    "query": query,
                    "request_id": request_id,
                    "episode_key": episode_key,
                    "edge_variant": variant_name,
                    "allowed_reasons": sorted(allowed_reasons),
                    "paper_role": variant.get("paper_role"),
                    "node_definition": "row_level_camera_pose_from_label_free_reobservation_artifact",
                    "node_count": node_count,
                    "edge_count": edge_count,
                    "connected_component_count": len(component_sizes),
                    "component_sizes": component_sizes,
                    "largest_component_fraction": None if node_count == 0 else largest / node_count,
                    "mean_degree": None if node_count == 0 else (2.0 * edge_count) / node_count,
                    "selected_edge_reason_counts": edge_reason_counts(edge_reasons, allowed_reasons),
                    "all_edge_reason_counts": all_reason_counts,
                    "candidate_overlap_removed": "candidate_id_overlap" not in allowed_reasons,
                    "strict_pose_proxy_candidate": variant_name in {"pose_spatial", "pose_loop", "pose_spatial_or_loop"},
                    "proxy_ready": proxy_ready,
                    "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in rows),
                    "terminal_commit": False,
                    "candidate_commit": False,
                    "candidate_rejection": False,
                    "paper_claim_allowed": False,
                }
            )
    return output_rows


def summarize_variant(rows: Sequence[Mapping[str, Any]], variant_name: str) -> Dict[str, Any]:
    subset = [row for row in rows if row.get("edge_variant") == variant_name]
    ready = [row for row in subset if row.get("proxy_ready") is True]
    source_counts = compact_counter(row.get("source_name") for row in subset)
    source_ready_rates: Dict[str, float] = {}
    for source_name in source_counts:
        source_subset = [row for row in subset if row.get("source_name") == source_name]
        source_ready_rates[source_name] = ratio(sum(1 for row in source_subset if row.get("proxy_ready") is True), len(source_subset))
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "strict_edge_variant_summary",
        "policy": POLICY_NAME,
        "edge_variant": variant_name,
        "proxy_rows": len(subset),
        "proxy_ready_rows": len(ready),
        "proxy_ready_rate": ratio(len(ready), len(subset)),
        "source_counts": source_counts,
        "source_ready_rates": dict(sorted(source_ready_rates.items())),
        "min_source_ready_rate": min(source_ready_rates.values()) if source_ready_rates else 0.0,
        "edge_count": number_stats(row.get("edge_count") for row in subset),
        "node_count": number_stats(row.get("node_count") for row in subset),
        "largest_component_fraction": number_stats(row.get("largest_component_fraction") for row in subset),
        "connected_component_count": number_stats(row.get("connected_component_count") for row in subset),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in subset),
        "terminal_commit_rows": sum(1 for row in subset if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in subset if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in subset if row.get("candidate_rejection") is True),
        "paper_claim_allowed": False,
    }


def find_variant_summary(summary_rows: Sequence[Mapping[str, Any]], variant_name: str) -> Mapping[str, Any]:
    for row in summary_rows:
        if row.get("edge_variant") == variant_name:
            return row
    return {}


def build_summary(
    *,
    contract: Mapping[str, Any],
    connectivity_summary: Mapping[str, Any],
    source_audit_summary: Mapping[str, Any],
    variant_rows_payload: Sequence[Mapping[str, Any]],
    variant_summary_rows: Sequence[Mapping[str, Any]],
    out_root: Path,
) -> Dict[str, Any]:
    thresholds = contract.get("gate_thresholds") or {}
    canonical_name = str(thresholds.get("canonical_variant") or "pose_spatial_or_loop")
    context_name = str(thresholds.get("context_variant") or "map_pose_context_no_candidate")
    loop_name = str(thresholds.get("loop_variant") or "pose_loop")
    shortcut_name = str(thresholds.get("shortcut_variant") or "candidate_overlap_only")
    canonical = find_variant_summary(variant_summary_rows, canonical_name)
    context = find_variant_summary(variant_summary_rows, context_name)
    loop = find_variant_summary(variant_summary_rows, loop_name)
    shortcut = find_variant_summary(variant_summary_rows, shortcut_name)
    source_names = sorted({str(row.get("source_name") or "") for row in variant_rows_payload if row.get("source_name")})
    group_keys = {
        (
            row.get("source_name"),
            row.get("scene_key"),
            row.get("query"),
            row.get("request_id"),
            row.get("episode_key"),
        )
        for row in variant_rows_payload
        if row.get("edge_variant") == canonical_name
    }
    forbidden_keys = action_forbidden_keys(list(variant_rows_payload) + list(variant_summary_rows))

    dependency_gate = {
        "source_audit_gate_passed": (
            source_audit_summary.get("gate", {}).get("source_audit", {}).get(
                "semantic_slam_map_pose_source_audit_gate_passed"
            )
            is True
        ),
        "connectivity_proxy_gate_passed": (
            connectivity_summary.get("gate", {}).get("pose_graph_connectivity_proxy_gate_passed") is True
        ),
        "connectivity_gate_paper_claim_blocked_passed": connectivity_summary.get("paper_claim_allowed") is False,
    }
    dependency_gate["dependency_gate_passed"] = all(dependency_gate.values())

    strict_gate = {
        "request_groups_minimum_passed": len(group_keys) >= safe_int(thresholds.get("min_request_groups"), 0),
        "source_family_count_minimum_passed": len(source_names) >= safe_int(thresholds.get("min_source_family_count"), 0),
        "canonical_ready_rate_passed": safe_float(canonical.get("proxy_ready_rate"), 0.0)
        >= safe_float(thresholds.get("min_canonical_ready_rate"), 0.0),
        "canonical_min_source_ready_rate_passed": safe_float(canonical.get("min_source_ready_rate"), 0.0)
        >= safe_float(thresholds.get("min_canonical_min_source_ready_rate"), 0.0),
        "context_ready_rate_passed": safe_float(context.get("proxy_ready_rate"), 0.0)
        >= safe_float(thresholds.get("min_context_ready_rate"), 0.0),
        "loop_ready_rate_passed": safe_float(loop.get("proxy_ready_rate"), 0.0)
        >= safe_float(thresholds.get("min_loop_ready_rate"), 0.0),
        "shortcut_variant_present_passed": safe_int(shortcut.get("proxy_rows"), 0) == len(group_keys),
    }
    strict_gate["strict_edge_variant_gate_passed"] = all(strict_gate.values())

    action_safety_gate = {
        "action_evidence_forbidden_key_gate_passed": len(forbidden_keys)
        <= safe_int(thresholds.get("max_action_evidence_forbidden_key_count"), 0),
        "terminal_commit_rows_passed": sum(1 for row in variant_rows_payload if row.get("terminal_commit") is True)
        <= safe_int(thresholds.get("max_terminal_commit_rows"), 0),
        "candidate_commit_rows_passed": sum(1 for row in variant_rows_payload if row.get("candidate_commit") is True)
        <= safe_int(thresholds.get("max_candidate_commit_rows"), 0),
        "candidate_rejection_rows_passed": sum(1 for row in variant_rows_payload if row.get("candidate_rejection") is True)
        <= safe_int(thresholds.get("max_candidate_rejection_rows"), 0),
        "uses_gt_for_action_passed": any(row.get("uses_gt_for_action") is True for row in variant_rows_payload)
        is bool(thresholds.get("requires_uses_gt_for_action", False)),
    }
    action_safety_gate["action_safety_gate_passed"] = all(action_safety_gate.values())

    strict_edge_variant_gate_passed = (
        dependency_gate["dependency_gate_passed"]
        and strict_gate["strict_edge_variant_gate_passed"]
        and action_safety_gate["action_safety_gate_passed"]
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-04",
        "status": "implemented_and_docker_verified_strict_edge_variant_proxy",
        "contract": CONTRACT_DEFAULT,
        "out_root": str(out_root),
        "output_files": {
            "variant_rows": "semantic_slam_strict_edge_variant_proxy_rows.jsonl",
            "variant_summary_rows": "semantic_slam_strict_edge_variant_proxy_summary_rows.jsonl",
            "summary": "semantic_slam_strict_edge_variant_proxy_summary.json",
        },
        "request_groups": len(group_keys),
        "source_family_count": len(source_names),
        "variant_row_count": len(variant_rows_payload),
        "variant_summary_row_count": len(variant_summary_rows),
        "canonical_variant": canonical_name,
        "canonical_proxy_ready_rows": safe_int(canonical.get("proxy_ready_rows"), 0),
        "canonical_proxy_ready_rate": safe_float(canonical.get("proxy_ready_rate"), 0.0),
        "canonical_min_source_ready_rate": safe_float(canonical.get("min_source_ready_rate"), 0.0),
        "context_variant": context_name,
        "context_proxy_ready_rows": safe_int(context.get("proxy_ready_rows"), 0),
        "context_proxy_ready_rate": safe_float(context.get("proxy_ready_rate"), 0.0),
        "loop_variant": loop_name,
        "loop_proxy_ready_rows": safe_int(loop.get("proxy_ready_rows"), 0),
        "loop_proxy_ready_rate": safe_float(loop.get("proxy_ready_rate"), 0.0),
        "shortcut_variant": shortcut_name,
        "shortcut_proxy_ready_rows": safe_int(shortcut.get("proxy_ready_rows"), 0),
        "shortcut_proxy_ready_rate": safe_float(shortcut.get("proxy_ready_rate"), 0.0),
        "variant_ready_rates": {
            str(row.get("edge_variant")): row.get("proxy_ready_rate") for row in variant_summary_rows
        },
        "gate": {
            "dependency": dependency_gate,
            "strict_edge_variant": strict_gate,
            "action_safety": action_safety_gate,
            "strict_edge_variant_proxy_gate_passed": strict_edge_variant_gate_passed,
        },
        "diagnostic_conclusion": {
            "strict_edge_variant_proxy_gate_passed": strict_edge_variant_gate_passed,
            "semantic_slam_proxy_comparison_contract_allowed": strict_edge_variant_gate_passed,
            "semantic_slam_policy_comparison_run_allowed": False,
            "recommended_next_task": (
                "define_semantic_slam_proxy_comparison_contract"
                if strict_edge_variant_gate_passed
                else "repair_semantic_slam_strict_edge_variant_proxy"
            ),
            "terminal_policy_allowed": False,
            "paper_claim_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden_keys),
        "action_evidence_forbidden_keys": forbidden_keys,
        "terminal_commit_rows": sum(1 for row in variant_rows_payload if row.get("terminal_commit") is True),
        "candidate_commit_rows": sum(1 for row in variant_rows_payload if row.get("candidate_commit") is True),
        "candidate_rejection_rows": sum(1 for row in variant_rows_payload if row.get("candidate_rejection") is True),
        "uses_gt_for_action": any(row.get("uses_gt_for_action") is True for row in variant_rows_payload),
        "terminal_utility_validation_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "semantic_slam_policy_comparison_run_allowed": False,
        "step_4_5_promotion_satisfied": False,
        "paper_claim_allowed": False,
        "interpretation": {
            "fact": "Strict variants recompute graph connectivity after excluding candidate-id overlap from pose/map context variants.",
            "agent_inference": "If the canonical strict variant passes, H001 can define a SemanticOnly / SLAMOnly / SemanticSLAM proxy comparison contract, but not run or claim it yet.",
            "paper_claim": "No SLAM benefit or navigation utility claim is allowed from this strict variant gate.",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    contract = load_json(Path(args.contract))
    source = contract.get("source") or {}
    connectivity_summary = load_json(Path(str(source.get("connectivity_gate_summary"))))
    source_audit_summary = load_json(Path(str(source.get("source_audit_summary"))))
    source_audit_contract = load_json(Path(str(source.get("source_audit_contract"))))
    inventory_rows = load_jsonl(Path(str(source.get("source_inventory_rows"))))
    grouped, source_roles, source_families = build_grouped_source_rows(
        source_audit_contract=source_audit_contract,
        inventory_rows=inventory_rows,
    )

    probe_contract = source_audit_contract.get("probe_contract") or {}
    first_proxy = probe_contract.get("first_proxy_definition") or {}
    spatial_threshold_m = safe_float(first_proxy.get("spatial_proximity_threshold_m"), 2.0)
    target_threshold_m = safe_float(first_proxy.get("target_neighborhood_threshold_m"), 1.0)
    loop_threshold_m = safe_float(first_proxy.get("loop_closure_threshold_m"), 0.75)

    variant_rows_payload = strict_variant_rows(
        grouped=grouped,
        source_roles=source_roles,
        source_families=source_families,
        variants=contract.get("edge_variants") or [],
        spatial_threshold_m=spatial_threshold_m,
        target_neighborhood_threshold_m=target_threshold_m,
        loop_closure_threshold_m=loop_threshold_m,
    )
    variant_names = [str(variant.get("name")) for variant in contract.get("edge_variants") or []]
    variant_summary_rows = [summarize_variant(variant_rows_payload, name) for name in variant_names]
    summary = build_summary(
        contract=contract,
        connectivity_summary=connectivity_summary,
        source_audit_summary=source_audit_summary,
        variant_rows_payload=variant_rows_payload,
        variant_summary_rows=variant_summary_rows,
        out_root=Path(args.out_root),
    )

    out_root = Path(args.out_root)
    outputs = contract.get("required_outputs") or {}
    write_jsonl(out_root / str(outputs.get("variant_rows", "semantic_slam_strict_edge_variant_proxy_rows.jsonl")), variant_rows_payload)
    write_jsonl(
        out_root / str(outputs.get("variant_summary_rows", "semantic_slam_strict_edge_variant_proxy_summary_rows.jsonl")),
        variant_summary_rows,
    )
    write_json(out_root / str(outputs.get("summary", "semantic_slam_strict_edge_variant_proxy_summary.json")), summary)


if __name__ == "__main__":
    main()
