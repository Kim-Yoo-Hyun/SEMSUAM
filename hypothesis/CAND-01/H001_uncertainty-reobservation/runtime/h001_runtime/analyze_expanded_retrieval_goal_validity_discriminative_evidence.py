import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_local_context_evidence import (
    action_forbidden_keys,
    request_sort_key,
)


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_discriminative.v1"


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


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def candidate_id(row: Dict[str, Any]) -> str:
    return str(row.get("candidate_id") or row.get("target_candidate_id"))


def row_request_id(row: Dict[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))


def index_plan_rows(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        request_id = row_request_id(row)
        cid = candidate_id(row)
        if request_id and cid and (request_id, cid) not in indexed:
            indexed[(request_id, cid)] = dict(row)
    return indexed


def group_by_request(rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row_request_id(row)].append(dict(row))
    for request_rows in grouped.values():
        request_rows.sort(
            key=lambda row: (
                safe_int(row.get("target_generated_rank"), 999999),
                safe_int(row.get("target_semantic_rank"), 999999),
                candidate_id(row),
            )
        )
    return grouped


def vector3(value: Any) -> Optional[Tuple[float, float, float]]:
    if not isinstance(value, list) or len(value) < 3:
        return None
    xyz = [safe_float(item) for item in value[:3]]
    if any(item is None for item in xyz):
        return None
    return (float(xyz[0]), float(xyz[1]), float(xyz[2]))


def horizontal_distance(a: Any, b: Any) -> Optional[float]:
    va = vector3(a)
    vb = vector3(b)
    if va is None or vb is None:
        return None
    return math.sqrt((va[0] - vb[0]) ** 2 + (va[2] - vb[2]) ** 2)


def distance_stats(values: Sequence[Optional[float]]) -> Dict[str, Optional[float]]:
    clean = [value for value in values if value is not None and math.isfinite(value)]
    if not clean:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(clean), "mean": sum(clean) / len(clean), "max": max(clean)}


def number_stats(values: Sequence[int]) -> Dict[str, Optional[float]]:
    clean = list(values)
    if not clean:
        return {"min": None, "mean": None, "max": None}
    return {"min": min(clean), "mean": sum(clean) / len(clean), "max": max(clean)}


def visual_support_score(row: Dict[str, Any]) -> float:
    return (
        safe_int(row.get("associated_heading_count"), 0)
        + safe_int(row.get("mask_hit_count"), 0)
        + safe_int(row.get("consistent_depth_count"), 0)
        + (safe_float(row.get("best_box_score"), 0.0) or 0.0)
    )


def visual_delta_sign(delta: float) -> str:
    if delta > 0:
        return "contrast_visual_higher"
    if delta < 0:
        return "selector_visual_higher"
    return "visual_tie"


def region_proxy(distance_m: Optional[float]) -> str:
    if distance_m is None:
        return "unknown_region_proxy"
    if distance_m <= 0.75:
        return "same_local_region_proxy"
    if distance_m <= 2.0:
        return "adjacent_region_proxy"
    return "distinct_region_proxy"


def selector_variants(selector_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[str]]:
    selected: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for row in selector_rows:
        request_id = str(row.get("expanded_retrieval_request_id"))
        cid = str(row.get("selected_candidate_id"))
        variant = str(row.get("objective_variant"))
        if request_id and cid and variant:
            selected[(request_id, cid)].append(variant)
    return selected


def compact_plan_fields(plan_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if plan_row is None:
        return {
            "target_position": None,
            "target_visit_position": None,
            "target_visit_position_navigable": None,
            "target_candidate_reachable": None,
            "target_score": None,
            "target_semantic_score": None,
            "target_support_score": None,
            "target_positive_support": None,
        }
    return {
        "target_position": plan_row.get("target_position"),
        "target_visit_position": plan_row.get("target_visit_position"),
        "target_visit_position_navigable": plan_row.get("target_visit_position_navigable"),
        "target_candidate_reachable": plan_row.get("target_candidate_reachable"),
        "target_score": plan_row.get("target_score"),
        "target_semantic_score": plan_row.get("target_semantic_score"),
        "target_support_score": plan_row.get("target_support_score"),
        "target_positive_support": plan_row.get("target_positive_support"),
    }


def candidate_rows(
    diagnostic_rows: Sequence[Dict[str, Any]],
    selector_map: Dict[Tuple[str, str], List[str]],
    plan_index: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in sorted(
        diagnostic_rows,
        key=lambda item: (
            request_sort_key(row_request_id(item)),
            safe_int(item.get("target_generated_rank"), 999999),
            candidate_id(item),
        ),
    ):
        request_id = row_request_id(row)
        cid = candidate_id(row)
        variants = sorted(set(selector_map.get((request_id, cid), [])))
        plan_row = plan_index.get((request_id, cid))
        output = {
            "schema_version": SCHEMA_VERSION,
            "validation_stage": "action_candidate_profile",
            "expanded_retrieval_request_id": request_id,
            "rival_identity_request_id": row.get("rival_identity_request_id"),
            "episode_key": row.get("episode_key"),
            "scene_key": row.get("scene_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "candidate_id": cid,
            "target_generated_rank": row.get("target_generated_rank"),
            "target_semantic_rank": row.get("target_semantic_rank"),
            "candidate_evidence_class": row.get("candidate_evidence_class"),
            "candidate_specific_support": row.get("candidate_evidence_class") == "candidate_specific_support",
            "associated_heading_count": row.get("associated_heading_count"),
            "mask_hit_count": row.get("mask_hit_count"),
            "consistent_depth_count": row.get("consistent_depth_count"),
            "best_box_score": row.get("best_box_score"),
            "visual_support_score": visual_support_score(row),
            "simple_selector_selected": bool(variants),
            "simple_selector_variants": variants,
            "terminal_commit": False,
            "uses_gt_for_action": False,
        }
        output.update(compact_plan_fields(plan_row))
        rows.append(output)
    return rows


def pair_rows(candidates: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for request_id, request_rows in sorted(group_by_request(candidates).items(), key=lambda item: request_sort_key(item[0])):
        selectors = [row for row in request_rows if row.get("simple_selector_selected") is True]
        contrasts = [
            row
            for row in request_rows
            if row.get("candidate_specific_support") is True
            and row.get("simple_selector_selected") is not True
        ]
        for selector in selectors:
            for contrast in contrasts:
                selector_score = visual_support_score(selector)
                contrast_score = visual_support_score(contrast)
                support_delta = contrast_score - selector_score
                target_distance = horizontal_distance(selector.get("target_position"), contrast.get("target_position"))
                visit_distance = horizontal_distance(
                    selector.get("target_visit_position"), contrast.get("target_visit_position")
                )
                rows.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "validation_stage": "action_pair_profile",
                        "expanded_retrieval_request_id": request_id,
                        "episode_key": selector.get("episode_key"),
                        "scene_key": selector.get("scene_key"),
                        "scene_id": selector.get("scene_id"),
                        "query": selector.get("query"),
                        "selector_candidate_id": selector.get("candidate_id"),
                        "contrast_candidate_id": contrast.get("candidate_id"),
                        "selector_candidate_variants": selector.get("simple_selector_variants") or [],
                        "selector_generated_rank": selector.get("target_generated_rank"),
                        "contrast_generated_rank": contrast.get("target_generated_rank"),
                        "selector_semantic_rank": selector.get("target_semantic_rank"),
                        "contrast_semantic_rank": contrast.get("target_semantic_rank"),
                        "rank_delta_contrast_minus_selector": safe_int(
                            contrast.get("target_generated_rank"), 999999
                        )
                        - safe_int(selector.get("target_generated_rank"), 999999),
                        "selector_visual_support_score": selector_score,
                        "contrast_visual_support_score": contrast_score,
                        "visual_support_delta_contrast_minus_selector": support_delta,
                        "visual_delta_sign": visual_delta_sign(support_delta),
                        "associated_heading_delta": safe_int(contrast.get("associated_heading_count"), 0)
                        - safe_int(selector.get("associated_heading_count"), 0),
                        "mask_hit_delta": safe_int(contrast.get("mask_hit_count"), 0)
                        - safe_int(selector.get("mask_hit_count"), 0),
                        "consistent_depth_delta": safe_int(contrast.get("consistent_depth_count"), 0)
                        - safe_int(selector.get("consistent_depth_count"), 0),
                        "box_score_delta": (safe_float(contrast.get("best_box_score"), 0.0) or 0.0)
                        - (safe_float(selector.get("best_box_score"), 0.0) or 0.0),
                        "target_horizontal_distance_m": target_distance,
                        "visit_horizontal_distance_m": visit_distance,
                        "goal_region_overlap_proxy": region_proxy(target_distance),
                        "terminal_commit": False,
                        "uses_gt_for_action": False,
                    }
                )
    rows.sort(
        key=lambda row: (
            request_sort_key(str(row.get("expanded_retrieval_request_id"))),
            safe_int(row.get("selector_generated_rank"), 999999),
            safe_int(row.get("contrast_generated_rank"), 999999),
            str(row.get("contrast_candidate_id")),
        )
    )
    return rows


def request_rows(candidates: Sequence[Dict[str, Any]], pairs: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    candidate_groups = group_by_request(candidates)
    pair_groups = group_by_request(pairs)
    for request_id, request_candidates in sorted(candidate_groups.items(), key=lambda item: request_sort_key(item[0])):
        request_pairs = pair_groups.get(request_id, [])
        support_rows = [row for row in request_candidates if row.get("candidate_specific_support") is True]
        selector_rows = [row for row in request_candidates if row.get("simple_selector_selected") is True]
        region_counts = Counter(str(row.get("goal_region_overlap_proxy")) for row in request_pairs)
        visual_counts = Counter(str(row.get("visual_delta_sign")) for row in request_pairs)
        high_saturation = ratio(len(support_rows), len(request_candidates)) is not None and (
            ratio(len(support_rows), len(request_candidates)) or 0.0
        ) >= 0.8
        mixed_visual = len([key for key, value in visual_counts.items() if value > 0]) > 1
        distinct_regions = region_counts.get("distinct_region_proxy", 0) > 0
        if high_saturation and (mixed_visual or distinct_regions):
            next_action = "request_relation_or_spatial_context_evidence"
            reason = "support_saturation_with_mixed_visual_and_region_proxies"
        else:
            next_action = "defer_goal_validity_terminal_policy"
            reason = "discriminative_signal_not_actionable"
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_request_profile",
                "expanded_retrieval_request_id": request_id,
                "episode_key": request_candidates[0].get("episode_key") if request_candidates else None,
                "scene_key": request_candidates[0].get("scene_key") if request_candidates else None,
                "scene_id": request_candidates[0].get("scene_id") if request_candidates else None,
                "query": request_candidates[0].get("query") if request_candidates else None,
                "candidate_rows": len(request_candidates),
                "candidate_specific_support_rows": len(support_rows),
                "candidate_specific_support_rate": ratio(len(support_rows), len(request_candidates)),
                "simple_selector_candidate_rows": len(selector_rows),
                "pair_rows": len(request_pairs),
                "pair_region_proxy_counts": dict(sorted(region_counts.items())),
                "pair_visual_delta_sign_counts": dict(sorted(visual_counts.items())),
                "rank_delta_stats": number_stats(
                    [safe_int(row.get("rank_delta_contrast_minus_selector"), 0) for row in request_pairs]
                ),
                "target_horizontal_distance_stats": distance_stats(
                    [safe_float(row.get("target_horizontal_distance_m")) for row in request_pairs]
                ),
                "next_observation_action": next_action,
                "next_observation_reason": reason,
                "terminal_commit": False,
                "uses_gt_for_action": False,
            }
        )
    return rows


def label_map_from_diagnostic(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        indexed[(row_request_id(row), candidate_id(row))] = {
            "evaluation_only_candidate_correct": row.get("evaluation_only_candidate_correct"),
            "evaluation_only_candidate_rank": row.get("evaluation_only_candidate_rank"),
        }
    return indexed


def evaluated_candidates(
    candidates: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in candidates:
        label = labels.get((row_request_id(row), candidate_id(row))) or {}
        rows.append(
            {
                **row,
                "validation_stage": "evaluated_candidate_profile_after_action_rows",
                "evaluation_only_candidate_correct": label.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def evaluated_pairs(
    pairs: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in pairs:
        request_id = str(row.get("expanded_retrieval_request_id"))
        selector_label = labels.get((request_id, str(row.get("selector_candidate_id")))) or {}
        contrast_label = labels.get((request_id, str(row.get("contrast_candidate_id")))) or {}
        selector_ok = selector_label.get("evaluation_only_candidate_correct")
        contrast_ok = contrast_label.get("evaluation_only_candidate_correct")
        rows.append(
            {
                **row,
                "validation_stage": "evaluated_pair_profile_after_action_rows",
                "evaluation_only_selector_candidate_correct": selector_ok,
                "evaluation_only_contrast_candidate_correct": contrast_ok,
                "evaluation_only_target_contrast_pair": selector_ok is False and contrast_ok is True,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def summarize(
    *,
    contract: Dict[str, Any],
    ambiguity_summary: Dict[str, Any],
    candidates: Sequence[Dict[str, Any]],
    pairs: Sequence[Dict[str, Any]],
    requests: Sequence[Dict[str, Any]],
    eval_candidates: Sequence[Dict[str, Any]],
    eval_pairs: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    action_rows = [*candidates, *pairs, *requests]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    request_ids = sorted({row_request_id(row) for row in candidates}, key=request_sort_key)
    support_rows = [row for row in candidates if row.get("candidate_specific_support") is True]
    selector_rows = [row for row in candidates if row.get("simple_selector_selected") is True]
    eval_correct = [
        row
        for row in eval_candidates
        if row.get("evaluation_only_candidate_correct") is True
    ]
    eval_target_pairs = [
        row
        for row in eval_pairs
        if row.get("evaluation_only_target_contrast_pair") is True
    ]
    target_visual_counts = Counter(str(row.get("visual_delta_sign")) for row in eval_target_pairs)
    target_region_counts = Counter(str(row.get("goal_region_overlap_proxy")) for row in eval_target_pairs)
    target_pairs_with_contrast_advantage = target_visual_counts.get("contrast_visual_higher", 0)
    target_pairs_with_selector_advantage = target_visual_counts.get("selector_visual_higher", 0)
    target_pairs_with_visual_tie = target_visual_counts.get("visual_tie", 0)
    separability_ready = (
        len(eval_target_pairs) >= safe_int(gates.get("candidate_pair_rows_minimum_after_label_join"), 0)
        and target_pairs_with_selector_advantage == 0
        and target_pairs_with_contrast_advantage > 0
    )
    recommended = (
        "request_relation_or_spatial_context_evidence"
        if not separability_ready
        else "defer_goal_validity_terminal_policy"
    )
    gate = {
        "input_ambiguity_diagnostic_gate_passed": ambiguity_summary.get("gate", {}).get(
            "ambiguity_diagnostic_gate_passed"
        )
        is bool(gates.get("input_ambiguity_diagnostic_gate_passed", True)),
        "expected_request_rows_passed": len(request_ids) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_rows_passed": len(candidates) == safe_int(gates.get("expected_candidate_rows")),
        "candidate_specific_support_count_minimum_passed": len(support_rows)
        >= safe_int(gates.get("candidate_specific_support_count_minimum"), 0),
        "wrong_selector_rows_minimum_passed": (
            ambiguity_summary.get("unsafe_selector_taxonomy", {}).get("wrong_selector_rows", 0)
            >= safe_int(gates.get("wrong_selector_rows_minimum"), 0)
        ),
        "correct_candidate_rows_minimum_after_label_join_passed": len(eval_correct)
        >= safe_int(gates.get("correct_candidate_rows_minimum_after_label_join"), 0),
        "candidate_pair_rows_minimum_after_label_join_passed": len(eval_target_pairs)
        >= safe_int(gates.get("candidate_pair_rows_minimum_after_label_join"), 0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), 0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), 0),
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in action_rows),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["discriminative_evidence_gate_passed"] = all(
        value is True
        for key, value in gate.items()
        if key
        not in {
            "uses_gt_for_action",
            "uses_gt_for_analysis",
            "terminal_utility_validation_allowed",
            "paper_claim_allowed",
        }
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "ambiguity_summary": str(args.ambiguity_summary),
        "diagnostic_rows": str(args.diagnostic_rows),
        "selector_rows": str(args.selector_rows),
        "plan": str(args.plan) if args.plan else None,
        "out_root": str(args.out_root),
        "request_rows": len(requests),
        "candidate_rows": len(candidates),
        "pair_rows": len(pairs),
        "candidate_specific_support_count": len(support_rows),
        "simple_selector_candidate_count": len(selector_rows),
        "candidate_evidence_class_counts": dict(
            sorted(Counter(str(row.get("candidate_evidence_class")) for row in candidates).items())
        ),
        "action_time_pair_profile": {
            "visual_delta_sign_counts": dict(sorted(Counter(str(row.get("visual_delta_sign")) for row in pairs).items())),
            "goal_region_overlap_proxy_counts": dict(
                sorted(Counter(str(row.get("goal_region_overlap_proxy")) for row in pairs).items())
            ),
            "target_horizontal_distance_stats": distance_stats(
                [safe_float(row.get("target_horizontal_distance_m")) for row in pairs]
            ),
        },
        "post_label_analysis": {
            "evaluation_only_candidate_rows": len(eval_candidates),
            "evaluation_only_correct_candidate_rows": len(eval_correct),
            "evaluation_only_target_contrast_pair_rows": len(eval_target_pairs),
            "evaluation_only_target_pair_visual_delta_sign_counts": dict(sorted(target_visual_counts.items())),
            "evaluation_only_target_pair_region_proxy_counts": dict(sorted(target_region_counts.items())),
            "evaluation_only_target_pairs_with_contrast_visual_advantage": target_pairs_with_contrast_advantage,
            "evaluation_only_target_pairs_with_selector_visual_advantage": target_pairs_with_selector_advantage,
            "evaluation_only_target_pairs_with_visual_tie": target_pairs_with_visual_tie,
        },
        "diagnostic_conclusion": {
            "discriminative_instance_or_goal_region_signal_ready": separability_ready,
            "recommended_next_action": recommended,
            "reason": (
                "target_contrast_pairs_not_consistently_preferred_by_action_time_visual_features"
                if not separability_ready
                else "target_contrast_pairs_have_nonzero_visual_advantage_without_selector_advantage"
            ),
            "terminal_policy_allowed": False,
        },
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": {
            "fact": "The analyzer materializes candidate, pair, and request profiles from frozen ambiguity evidence without terminal commits.",
            "agent_inference": (
                "If target contrast pairs are not separable by action-time features, the next branch should request relation or spatial-context evidence."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "candidate_rows": "goal_validity_discriminative_candidate_rows.jsonl",
            "pair_rows": "goal_validity_discriminative_pair_rows.jsonl",
            "request_rows": "goal_validity_discriminative_request_rows.jsonl",
            "evaluated_candidate_rows": "goal_validity_discriminative_evaluated_candidate_rows.jsonl",
            "evaluated_pair_rows": "goal_validity_discriminative_evaluated_pair_rows.jsonl",
            "summary": "goal_validity_discriminative_evidence_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    ambiguity_summary = load_json(Path(args.ambiguity_summary))
    diagnostic = load_jsonl(Path(args.diagnostic_rows))
    selectors = load_jsonl(Path(args.selector_rows))
    plan_index: Dict[Tuple[str, str], Dict[str, Any]] = {}
    if args.plan:
        plan_index = index_plan_rows(load_jsonl(Path(args.plan)))
    selector_map = selector_variants(selectors)
    candidates = candidate_rows(diagnostic, selector_map, plan_index)
    pairs = pair_rows(candidates)
    requests = request_rows(candidates, pairs)
    labels = label_map_from_diagnostic(diagnostic)
    eval_candidates = evaluated_candidates(candidates, labels)
    eval_pairs = evaluated_pairs(pairs, labels)
    summary = summarize(
        contract=contract,
        ambiguity_summary=ambiguity_summary,
        candidates=candidates,
        pairs=pairs,
        requests=requests,
        eval_candidates=eval_candidates,
        eval_pairs=eval_pairs,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "goal_validity_discriminative_candidate_rows.jsonl", candidates)
    write_jsonl(out_root / "goal_validity_discriminative_pair_rows.jsonl", pairs)
    write_jsonl(out_root / "goal_validity_discriminative_request_rows.jsonl", requests)
    write_jsonl(out_root / "goal_validity_discriminative_evaluated_candidate_rows.jsonl", eval_candidates)
    write_jsonl(out_root / "goal_validity_discriminative_evaluated_pair_rows.jsonl", eval_pairs)
    write_json(out_root / "goal_validity_discriminative_evidence_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze discriminative instance or goal-region evidence after support saturation."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--ambiguity-summary", required=True)
    parser.add_argument("--diagnostic-rows", required=True)
    parser.add_argument("--selector-rows", required=True)
    parser.add_argument("--plan", default="")
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
