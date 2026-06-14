import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from h001_runtime.analyze_expanded_retrieval_goal_validity_evidence import candidate_id, safe_int
from h001_runtime.analyze_expanded_retrieval_local_context_evidence import action_forbidden_keys, request_sort_key


SCHEMA_VERSION = "h001.expanded_retrieval_goal_validity_ambiguity.v1"
UNSAFE_SELECTOR_VARIANTS = {
    "semantic_top_observed",
    "detector_score_best_observed",
    "positive_support_best_observed",
    "candidate_specific_support_best_observed",
}


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


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def label_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        request_id = str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id"))
        cid = candidate_id(row)
        indexed[(request_id, cid)] = dict(row)
    return indexed


def selected_variants(evaluated_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    selected: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in evaluated_rows:
        variant = str(row.get("objective_variant"))
        cid = row.get("selected_candidate_id")
        request_id = str(row.get("expanded_retrieval_request_id"))
        if variant in UNSAFE_SELECTOR_VARIANTS and cid:
            selected[(request_id, str(cid))].append(dict(row))
    return selected


def diagnostic_rows(
    candidate_rows: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
    selected: Dict[Tuple[str, str], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in candidate_rows:
        request_id = str(row.get("expanded_retrieval_request_id"))
        cid = candidate_id(row)
        label = labels.get((request_id, cid)) or {}
        selected_by = selected.get((request_id, cid), [])
        is_correct = label.get("evaluation_only_candidate_correct") is True
        is_wrong = label.get("evaluation_only_candidate_correct") is False
        has_support = row.get("candidate_evidence_class") == "candidate_specific_support"
        tags: List[str] = []
        if has_support:
            tags.append("candidate_specific_support")
        if is_correct and has_support:
            tags.append("correct_candidate_supported")
        if is_wrong and has_support:
            tags.append("wrong_candidate_supported")
        if selected_by:
            tags.append("selected_by_simple_observed_selector")
        if selected_by and is_wrong:
            tags.append("unsafe_wrong_selector_target")
        if selected_by and is_correct:
            tags.append("selector_found_correct_candidate")
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "diagnostic_joined_after_action_evidence",
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
                "associated_heading_count": row.get("associated_heading_count"),
                "mask_hit_count": row.get("mask_hit_count"),
                "consistent_depth_count": row.get("consistent_depth_count"),
                "best_box_score": row.get("best_box_score"),
                "evaluation_only_candidate_correct": label.get("evaluation_only_candidate_correct"),
                "evaluation_only_candidate_rank": label.get("evaluation_only_candidate_rank"),
                "selected_by_variants": [item.get("objective_variant") for item in selected_by],
                "diagnostic_tags": tags,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def selector_rows(evaluated_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for row in evaluated_rows:
        variant = str(row.get("objective_variant"))
        if variant not in UNSAFE_SELECTOR_VARIANTS:
            continue
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "selector_failure_taxonomy",
                "objective_variant": variant,
                "expanded_retrieval_request_id": row.get("expanded_retrieval_request_id"),
                "selected_candidate_id": row.get("selected_candidate_id"),
                "selected_target_generated_rank": row.get("selected_target_generated_rank"),
                "selected_target_semantic_rank": row.get("selected_target_semantic_rank"),
                "selected_candidate_evidence_class": row.get("selected_candidate_evidence_class"),
                "evaluation_only_selected_correct": row.get("evaluation_only_selected_correct"),
                "evaluation_only_wrong_goal_commit": row.get("evaluation_only_wrong_goal_commit"),
                "failure_tags": [
                    tag
                    for tag, enabled in {
                        "simple_selector_wrong_goal": row.get("evaluation_only_wrong_goal_commit") is True,
                        "support_not_discriminative": row.get("selected_candidate_evidence_class")
                        == "candidate_specific_support",
                    }.items()
                    if enabled
                ],
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
            }
        )
    return rows


def action_view(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value
        for key, value in row.items()
        if not key.startswith("evaluation_only_") and key != "uses_gt_for_analysis"
    }


def summarize(
    *,
    contract: Dict[str, Any],
    objective_summary: Dict[str, Any],
    diag_rows: Sequence[Dict[str, Any]],
    sel_rows: Sequence[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    gates = dict(contract.get("evaluation_gates") or {})
    request_ids = sorted({str(row.get("expanded_retrieval_request_id")) for row in diag_rows}, key=request_sort_key)
    support_rows = [row for row in diag_rows if row.get("candidate_evidence_class") == "candidate_specific_support"]
    correct_rows = [row for row in diag_rows if row.get("evaluation_only_candidate_correct") is True]
    wrong_rows = [row for row in diag_rows if row.get("evaluation_only_candidate_correct") is False]
    correct_support_rows = [
        row
        for row in support_rows
        if row.get("evaluation_only_candidate_correct") is True
    ]
    wrong_support_rows = [
        row
        for row in support_rows
        if row.get("evaluation_only_candidate_correct") is False
    ]
    unsafe_wrong = [row for row in sel_rows if row.get("evaluation_only_wrong_goal_commit") is True]
    action_rows: List[Dict[str, Any]] = [action_view(row) for row in [*diag_rows, *sel_rows]]
    forbidden = action_forbidden_keys(action_rows)
    terminal_rows = [row for row in action_rows if row.get("terminal_commit") is True]
    class_counts = Counter(str(row.get("candidate_evidence_class")) for row in diag_rows)
    support_by_request = {
        request_id: sum(
            1
            for row in diag_rows
            if row.get("expanded_retrieval_request_id") == request_id
            and row.get("candidate_evidence_class") == "candidate_specific_support"
        )
        for request_id in request_ids
    }
    gate = {
        "input_objective_gate_passed": objective_summary.get("gate", {}).get("objective_analyzer_gate_passed")
        is bool(gates.get("input_objective_gate_passed", True)),
        "expected_request_rows_passed": len(request_ids) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_rows_passed": len(diag_rows) == safe_int(gates.get("expected_candidate_rows")),
        "candidate_specific_support_count_minimum_passed": len(support_rows)
        >= safe_int(gates.get("candidate_specific_support_count_minimum"), default=0),
        "evaluation_only_correct_candidate_count_minimum_passed": len(correct_rows)
        >= safe_int(gates.get("evaluation_only_correct_candidate_count_minimum"), default=0),
        "unsafe_simpler_alternative_wrong_rows_minimum_passed": len(unsafe_wrong)
        >= safe_int(gates.get("unsafe_simpler_alternative_wrong_rows_minimum"), default=0),
        "action_evidence_forbidden_key_gate_passed": len(forbidden)
        <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum"), default=0),
        "terminal_commit_rows_passed": len(terminal_rows)
        <= safe_int(gates.get("terminal_commit_rows_maximum"), default=0),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
    }
    gate["ambiguity_diagnostic_gate_passed"] = all(
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
    recommended_next_actions = [
        "request_discriminative_instance_or_goal_region_evidence",
        "request_relation_or_spatial_context_evidence",
        "defer_goal_validity_terminal_policy",
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "objective_summary": str(args.objective_summary),
        "candidate_rows": str(args.candidate_rows),
        "evaluated_rows": str(args.evaluated_rows),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(args.out_root),
        "request_rows": len(request_ids),
        "candidate_rows_count": len(diag_rows),
        "candidate_evidence_class_counts": dict(sorted(class_counts.items())),
        "support_saturation": {
            "candidate_specific_support_count": len(support_rows),
            "candidate_specific_support_rate": ratio(len(support_rows), len(diag_rows)),
            "support_count_by_request": support_by_request,
            "correct_support_count": len(correct_support_rows),
            "wrong_support_count": len(wrong_support_rows),
            "correct_wrong_support_overlap": bool(correct_support_rows and wrong_support_rows),
        },
        "evaluation_only_counts": {
            "correct_candidates": len(correct_rows),
            "wrong_candidates": len(wrong_rows),
        },
        "unsafe_selector_taxonomy": {
            "selector_rows": len(sel_rows),
            "wrong_selector_rows": len(unsafe_wrong),
            "wrong_selector_rows_by_variant": dict(
                sorted(
                    Counter(
                        str(row.get("objective_variant"))
                        for row in unsafe_wrong
                    ).items()
                )
            ),
            "selected_wrong_candidate_ids": [
                row.get("selected_candidate_id") for row in unsafe_wrong
            ],
        },
        "recommended_next_actions": recommended_next_actions,
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "gate": gate,
        "interpretation": contract.get("interpretation_rule") or {},
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "diagnostic_rows": "goal_validity_ambiguity_diagnostic_rows.jsonl",
            "selector_rows": "goal_validity_ambiguity_selector_rows.jsonl",
            "summary": "goal_validity_ambiguity_resolution_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    objective_summary = load_json(Path(args.objective_summary))
    candidates = load_jsonl(Path(args.candidate_rows))
    evaluated = load_jsonl(Path(args.evaluated_rows))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))
    selected = selected_variants(evaluated)
    diag = diagnostic_rows(candidates, labels, selected)
    selectors = selector_rows(evaluated)
    summary = summarize(
        contract=contract,
        objective_summary=objective_summary,
        diag_rows=diag,
        sel_rows=selectors,
        args=args,
    )
    out_root = Path(args.out_root)
    write_jsonl(out_root / "goal_validity_ambiguity_diagnostic_rows.jsonl", diag)
    write_jsonl(out_root / "goal_validity_ambiguity_selector_rows.jsonl", selectors)
    write_json(out_root / "goal_validity_ambiguity_resolution_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Diagnose support saturation after full candidate-specific goal-validity evidence."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--objective-summary", required=True)
    parser.add_argument("--candidate-rows", required=True)
    parser.add_argument("--evaluated-rows", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
