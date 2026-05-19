import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.followup_v2_stage2_feasibility.v1"
REQUEST_ACTIONS = {
    "external_evidence_v4_request_expanded_retrieval",
    "external_evidence_v4_request_identity_confirmation",
}


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


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if text == "" or text == "None" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def rows_by_branch(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("external_branch_id"))].append(row)
    return grouped


def source_candidate_labels(source: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    labels: Dict[str, Dict[str, Any]] = {}
    for row in source.get("candidate_evidence") or []:
        candidate_id = row.get("candidate_id")
        if candidate_id is None:
            continue
        labels[str(candidate_id)] = {
            "candidate_id": str(candidate_id),
            "candidate_correct": row.get("candidate_correct"),
            "candidate_reachable": row.get("candidate_reachable"),
            "semantic_rank": row.get("semantic_rank"),
            "semantic_score": row.get("semantic_score"),
            "label_source": "external_evidence_v4_candidate_evidence",
        }
    return labels


def object_node_label_index(rows: List[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    labels: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        labels[(str(episode_key), str(candidate_id))] = {
            "candidate_id": str(candidate_id),
            "candidate_correct": row.get("candidate_correct"),
            "candidate_reachable": row.get("candidate_reachable"),
            "semantic_rank": row.get("candidate_rank_before"),
            "semantic_score": row.get("S_sem"),
            "label_source": "object_node_features",
        }
    return labels


def candidate_label(
    source: Dict[str, Any],
    source_labels: Dict[str, Dict[str, Any]],
    object_node_labels: Dict[Tuple[str, str], Dict[str, Any]],
    candidate_id: str,
) -> Dict[str, Any]:
    source_label = source_labels.get(candidate_id)
    if source_label is not None:
        return source_label
    label = object_node_labels.get((str(source.get("episode_key")), candidate_id))
    if label is not None:
        return label
    return {
        "candidate_id": candidate_id,
        "candidate_correct": None,
        "candidate_reachable": None,
        "semantic_rank": None,
        "semantic_score": None,
        "label_source": "unknown",
    }


def plan_candidate_sets(plan_rows: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    viewpoint_target_ids = ordered_unique(row.get("candidate_id") for row in plan_rows)
    association_candidate_ids = ordered_unique(
        candidate_id
        for row in plan_rows
        for candidate_id in (row.get("candidate_ids") or [row.get("candidate_id")])
    )
    external_candidate_ids = ordered_unique(
        candidate_id
        for row in plan_rows
        for candidate_id in (row.get("external_candidate_ids") or [])
    )
    return {
        "viewpoint_target_candidate_ids": viewpoint_target_ids,
        "association_candidate_ids": association_candidate_ids,
        "external_candidate_ids": external_candidate_ids,
    }


def label_candidate_set(
    source: Dict[str, Any],
    source_labels: Dict[str, Dict[str, Any]],
    object_node_labels: Dict[Tuple[str, str], Dict[str, Any]],
    candidate_ids: List[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for candidate_id in candidate_ids:
        label = candidate_label(source, source_labels, object_node_labels, candidate_id)
        rows.append({"candidate_id": candidate_id, **label})
    return rows


def correct_candidate_ids(rows: List[Dict[str, Any]]) -> List[str]:
    return [str(row.get("candidate_id")) for row in rows if row.get("candidate_correct") is True]


def known_label_count(rows: List[Dict[str, Any]]) -> int:
    return sum(row.get("candidate_correct") is not None for row in rows)


def inspect_row(
    source: Dict[str, Any],
    plan_rows: List[Dict[str, Any]],
    object_node_labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    action = str(source.get("external_evidence_v4_action"))
    source_labels = source_candidate_labels(source)
    sets = plan_candidate_sets(plan_rows)
    viewpoint_rows = label_candidate_set(source, source_labels, object_node_labels, sets["viewpoint_target_candidate_ids"])
    association_rows = label_candidate_set(source, source_labels, object_node_labels, sets["association_candidate_ids"])
    external_rows = label_candidate_set(source, source_labels, object_node_labels, sets["external_candidate_ids"])
    viewpoint_correct = correct_candidate_ids(viewpoint_rows)
    association_correct = correct_candidate_ids(association_rows)
    external_correct = correct_candidate_ids(external_rows)
    source_candidate_correct = correct_candidate_ids(list(source_labels.values()))
    property_group = str(source.get("property_group") or "unknown")
    is_expanded = action == "external_evidence_v4_request_expanded_retrieval"
    is_identity = action == "external_evidence_v4_request_identity_confirmation"
    association_set_contains_correct = bool(association_correct)
    viewpoint_target_contains_correct = bool(viewpoint_correct)
    large_repeated_expanded = is_expanded and property_group == "large_repeated_furniture"
    small_or_cluttered_expanded = is_expanded and property_group == "small_or_cluttered"

    return {
        "schema_version": SCHEMA_VERSION,
        "external_branch_id": source.get("external_branch_id"),
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "property_group": property_group,
        "label_case": source.get("label_case"),
        "external_evidence_v4_action": action,
        "external_evidence_v4_reason": source.get("external_evidence_v4_reason"),
        "selected_candidate_id": source.get("selected_candidate_id"),
        "selected_candidate_correct": source.get("selected_candidate_correct"),
        "source_external_set_contains_correct": source.get("external_set_contains_correct"),
        "source_candidate_evidence_correct_candidate_ids": source_candidate_correct,
        "followup_plan_rows": len(plan_rows),
        "followup_viewpoint_target_candidate_count": len(viewpoint_rows),
        "followup_association_candidate_count": len(association_rows),
        "followup_external_candidate_count": len(external_rows),
        "followup_viewpoint_target_known_label_count": known_label_count(viewpoint_rows),
        "followup_association_known_label_count": known_label_count(association_rows),
        "followup_viewpoint_target_contains_correct": viewpoint_target_contains_correct,
        "followup_association_set_contains_correct": association_set_contains_correct,
        "followup_external_set_contains_correct": bool(external_correct),
        "followup_viewpoint_target_correct_candidate_ids": viewpoint_correct,
        "followup_association_correct_candidate_ids": association_correct,
        "followup_external_correct_candidate_ids": external_correct,
        "followup_viewpoint_target_candidate_ids": sets["viewpoint_target_candidate_ids"],
        "followup_association_candidate_ids": sets["association_candidate_ids"],
        "potential_followup_utility_case": bool(association_set_contains_correct or viewpoint_target_contains_correct),
        "potential_v2_second_stage_identity_utility_case": bool(
            large_repeated_expanded and (association_set_contains_correct or viewpoint_target_contains_correct)
        ),
        "potential_non_identity_followup_utility_case": bool(
            small_or_cluttered_expanded and (association_set_contains_correct or viewpoint_target_contains_correct)
        ),
        "direct_identity_recheck_contains_correct": bool(is_identity and association_set_contains_correct),
        "analysis_note": (
            "large_repeated_expanded_retrieval_with_valid_candidate"
            if large_repeated_expanded and (association_set_contains_correct or viewpoint_target_contains_correct)
            else "small_or_cluttered_expanded_retrieval_with_valid_candidate"
            if small_or_cluttered_expanded and (association_set_contains_correct or viewpoint_target_contains_correct)
            else "direct_identity_recheck_contains_valid_candidate"
            if is_identity and association_set_contains_correct
            else "request_branch_without_known_valid_followup_candidate"
        ),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize(rows: List[Dict[str, Any]], source_rows: List[Dict[str, Any]], plan_rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    action_counts = Counter(row["external_evidence_v4_action"] for row in rows)
    property_counts = Counter(row["property_group"] for row in rows)
    note_counts = Counter(row["analysis_note"] for row in rows)
    expanded_rows = [row for row in rows if row["external_evidence_v4_action"] == "external_evidence_v4_request_expanded_retrieval"]
    identity_rows = [row for row in rows if row["external_evidence_v4_action"] == "external_evidence_v4_request_identity_confirmation"]
    potential_followup = [row for row in rows if row["potential_followup_utility_case"]]
    potential_stage2 = [row for row in rows if row["potential_v2_second_stage_identity_utility_case"]]
    potential_non_identity = [row for row in rows if row["potential_non_identity_followup_utility_case"]]
    direct_identity = [row for row in rows if row["direct_identity_recheck_contains_correct"]]
    expanded_with_correct = [row for row in expanded_rows if row["followup_association_set_contains_correct"]]
    identity_with_correct = [row for row in identity_rows if row["followup_association_set_contains_correct"]]
    can_run_fresh_followup_detector = bool(potential_stage2 or potential_non_identity)
    recommendation = (
        "run_fresh_followup_detector_v2_stage2_before_first_eval"
        if potential_stage2
        else "run_fresh_followup_detector_for_non_identity_followup_only"
        if potential_non_identity
        else "broaden_or_replace_split_before_detector_rerun"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "split_name": str(args.split_name),
        "external_evidence_v4_rows": str(args.external_evidence_v4_rows),
        "followup_observation_plan": str(args.followup_observation_plan),
        "object_node_features": str(args.object_node_features),
        "out_root": str(args.out_root),
        "source_rows_total": len(source_rows),
        "source_request_rows": len(rows),
        "plan_rows": len(plan_rows),
        "action_counts": dict(sorted(action_counts.items())),
        "property_group_counts": dict(sorted(property_counts.items())),
        "analysis_note_counts": dict(sorted(note_counts.items())),
        "expanded_request_rows": len(expanded_rows),
        "expanded_request_rows_with_correct_followup_set": len(expanded_with_correct),
        "expanded_request_rows_with_correct_followup_set_rate": ratio(len(expanded_with_correct), len(expanded_rows)),
        "identity_request_rows": len(identity_rows),
        "identity_request_rows_with_correct_followup_set": len(identity_with_correct),
        "identity_request_rows_with_correct_followup_set_rate": ratio(len(identity_with_correct), len(identity_rows)),
        "potential_followup_utility_rows": len(potential_followup),
        "potential_followup_utility_rate": ratio(len(potential_followup), len(rows)),
        "potential_v2_second_stage_identity_utility_rows": len(potential_stage2),
        "potential_v2_second_stage_identity_utility_rate": ratio(len(potential_stage2), len(rows)),
        "potential_non_identity_followup_utility_rows": len(potential_non_identity),
        "direct_identity_recheck_rows_with_correct_followup_set": len(direct_identity),
        "potential_v2_second_stage_identity_branch_ids": [row["external_branch_id"] for row in potential_stage2],
        "potential_non_identity_followup_branch_ids": [row["external_branch_id"] for row in potential_non_identity],
        "direct_identity_recheck_branch_ids": [row["external_branch_id"] for row in direct_identity],
        "recommended_next": recommendation,
        "fresh_followup_detector_rerun_supported": can_run_fresh_followup_detector,
        "first_eval_rerun_blocked": True,
        "first_eval_rerun_block_reason": "label_only_feasibility_inspection_does_not_replace_detector_evidence_gate",
        "analysis_scope": {
            "role": "label-only feasibility inspection before expensive detector/follow-up rerun",
            "does_not_score_detector": True,
            "does_not_change_policy_action": True,
            "valid_second_stage_identity_case_definition": (
                "a V4 expanded-retrieval request in large_repeated_furniture whose planned follow-up "
                "candidate/association set contains at least one GT-correct candidate; detector evidence is still required"
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "followup_v2_stage2_feasibility_rows.jsonl",
            "summary": "followup_v2_stage2_feasibility_summary.json",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    source_rows = load_jsonl(Path(args.external_evidence_v4_rows))
    plan_rows = load_jsonl(Path(args.followup_observation_plan))
    object_node_labels = object_node_label_index(load_jsonl(Path(args.object_node_features)))
    plans_by_branch = rows_by_branch(plan_rows)
    request_rows = [row for row in source_rows if row.get("external_evidence_v4_action") in REQUEST_ACTIONS]
    inspected_rows = [
        inspect_row(source, plans_by_branch.get(str(source.get("external_branch_id")), []), object_node_labels)
        for source in request_rows
    ]
    out_root = Path(args.out_root)
    write_jsonl(out_root / "followup_v2_stage2_feasibility_rows.jsonl", inspected_rows)
    summary = summarize(inspected_rows, source_rows, plan_rows, args)
    write_json(out_root / "followup_v2_stage2_feasibility_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect whether V4 follow-up rows can yield V2 second-stage identity utility cases."
    )
    parser.add_argument("--external-evidence-v4-rows", required=True)
    parser.add_argument("--followup-observation-plan", required=True)
    parser.add_argument("--object-node-features", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--split-name", default="unknown")
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
