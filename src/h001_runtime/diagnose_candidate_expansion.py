import argparse
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.candidate_set_expansion_diagnostic.v1"


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def candidate_rank(candidate_id: str) -> Optional[int]:
    try:
        return int(candidate_id.rsplit(":", 1)[-1]) + 1
    except (TypeError, ValueError):
        return None


def artifact_index(path: Path) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        candidates = list(row.get("candidates") or [])
        candidates.sort(
            key=lambda candidate: (
                safe_float(candidate.get("score")) or -math.inf,
                -(candidate_rank(str(candidate.get("candidate_id"))) or 9999),
            ),
            reverse=True,
        )
        index[(str(row.get("scene_id")), str(row.get("query")))] = candidates
    return index


def feature_index(path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    labels: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in load_jsonl(path):
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        labels[(str(episode_key), str(candidate_id))] = row
    return labels


def rows_by_branch(rows: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("external_branch_id")): row for row in rows if row.get("external_branch_id") is not None}


def grouped_rows_by_branch(rows: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        branch_id = row.get("external_branch_id")
        if branch_id is None:
            continue
        grouped.setdefault(str(branch_id), []).append(row)
    return grouped


def plan_candidate_ids(plan_rows: List[Dict[str, Any]]) -> List[str]:
    return ordered_unique(
        candidate_id
        for row in plan_rows
        for candidate_id in [row.get("candidate_id"), *(row.get("candidate_ids") or [])]
    )


def evidence_label_index(source: Dict[str, Any], followup: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    labels: Dict[str, Dict[str, Any]] = {}
    for candidate in source.get("candidate_evidence") or []:
        candidate_id = candidate.get("candidate_id")
        if candidate_id is not None:
            labels[str(candidate_id)] = candidate
    if followup:
        for candidate in followup.get("followup_candidate_evidence") or []:
            candidate_id = candidate.get("candidate_id")
            if candidate_id is not None:
                labels.setdefault(str(candidate_id), candidate)
    return labels


def label_for(
    source: Dict[str, Any],
    evidence_labels: Dict[str, Dict[str, Any]],
    object_labels: Dict[Tuple[str, str], Dict[str, Any]],
    candidate_id: str,
) -> Optional[bool]:
    if candidate_id in evidence_labels and evidence_labels[candidate_id].get("candidate_correct") is not None:
        return evidence_labels[candidate_id].get("candidate_correct") is True
    row = object_labels.get((str(source.get("episode_key")), candidate_id))
    if row is not None and row.get("candidate_correct") is not None:
        return row.get("candidate_correct") is True
    return None


def correct_ids(
    source: Dict[str, Any],
    evidence_labels: Dict[str, Dict[str, Any]],
    object_labels: Dict[Tuple[str, str], Dict[str, Any]],
    candidate_ids: List[str],
) -> List[str]:
    return [candidate_id for candidate_id in candidate_ids if label_for(source, evidence_labels, object_labels, candidate_id) is True]


def known_count(
    source: Dict[str, Any],
    evidence_labels: Dict[str, Dict[str, Any]],
    object_labels: Dict[Tuple[str, str], Dict[str, Any]],
    candidate_ids: List[str],
) -> int:
    return sum(label_for(source, evidence_labels, object_labels, candidate_id) is not None for candidate_id in candidate_ids)


def top_artifact_ids(candidates: List[Dict[str, Any]], limit: int) -> List[str]:
    return ordered_unique(candidate.get("candidate_id") for candidate in candidates[:limit])


def variant_row(
    name: str,
    ids: List[str],
    source: Dict[str, Any],
    evidence_labels: Dict[str, Dict[str, Any]],
    object_labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    ids = ordered_unique(ids)
    hits = correct_ids(source, evidence_labels, object_labels, ids)
    return {
        "candidate_set": name,
        "candidate_count": len(ids),
        "known_label_count": known_count(source, evidence_labels, object_labels, ids),
        "contains_correct": bool(hits),
        "correct_candidate_ids": hits,
        "candidate_ids": ids,
    }


def inspect_row(
    source: Dict[str, Any],
    followup: Optional[Dict[str, Any]],
    plan_rows: List[Dict[str, Any]],
    artifact_candidates: List[Dict[str, Any]],
    object_labels: Dict[Tuple[str, str], Dict[str, Any]],
    budgets: List[int],
) -> Dict[str, Any]:
    evidence_labels = evidence_label_index(source, followup)
    current_ids = ordered_unique((followup or {}).get("followup_candidate_ids") or [])
    planned_ids = plan_candidate_ids(plan_rows)
    external_ids = ordered_unique(source.get("external_candidate_ids") or [])
    selected_id = str(source.get("selected_candidate_id"))
    current_plus_external = ordered_unique([*current_ids, *external_ids])
    external_correct = correct_ids(source, evidence_labels, object_labels, external_ids)
    planned_correct = correct_ids(source, evidence_labels, object_labels, planned_ids)
    current_correct = correct_ids(source, evidence_labels, object_labels, current_ids)
    variants = [
        variant_row("current_followup_set", current_ids, source, evidence_labels, object_labels),
        variant_row("followup_plan_explicit_set", planned_ids, source, evidence_labels, object_labels),
        variant_row("v4_external_set", external_ids, source, evidence_labels, object_labels),
        variant_row("current_plus_v4_external", current_plus_external, source, evidence_labels, object_labels),
    ]
    for budget in budgets:
        top_ids = top_artifact_ids(artifact_candidates, budget)
        variants.append(
            variant_row(f"artifact_semantic_top{budget}", top_ids, source, evidence_labels, object_labels)
        )
        variants.append(
            variant_row(
                f"current_plus_artifact_top{budget}",
                ordered_unique([*current_ids, *top_ids]),
                source,
                evidence_labels,
                object_labels,
            )
        )

    if planned_correct and not current_correct:
        failure_mode = "detector_association_dropped_planned_correct_candidate"
    elif external_correct and not planned_correct:
        failure_mode = "planner_dropped_v4_correct_candidate"
    elif not external_correct:
        failure_mode = "v4_external_set_missing_correct_candidate"
    elif source.get("selected_candidate_correct") is True and current_correct:
        failure_mode = "selected_correct_but_identity_ambiguous"
    elif current_correct:
        failure_mode = "current_set_contains_correct_but_no_commit"
    else:
        failure_mode = "unclassified_candidate_set_failure"

    return {
        "schema_version": SCHEMA_VERSION,
        "external_branch_id": source.get("external_branch_id"),
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "property_group": source.get("property_group"),
        "label_case": source.get("label_case"),
        "selected_candidate_id": selected_id,
        "selected_candidate_correct": source.get("selected_candidate_correct"),
        "external_evidence_v4_action": source.get("external_evidence_v4_action"),
        "external_evidence_v4_reason": source.get("external_evidence_v4_reason"),
        "followup_action": None if followup is None else followup.get("followup_evidence_v1_action"),
        "followup_reason": None if followup is None else followup.get("followup_evidence_v1_reason"),
        "current_followup_count": len(current_ids),
        "followup_plan_count": len(planned_ids),
        "v4_external_count": len(external_ids),
        "current_plus_v4_external_count": len(current_plus_external),
        "current_followup_correct_candidate_ids": current_correct,
        "followup_plan_correct_candidate_ids": planned_correct,
        "v4_external_correct_candidate_ids": external_correct,
        "failure_mode": failure_mode,
        "candidate_set_variants": variants,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def summarize(rows: List[Dict[str, Any]], args: argparse.Namespace) -> Dict[str, Any]:
    variant_totals: Dict[str, Dict[str, int]] = {}
    for row in rows:
        for variant in row["candidate_set_variants"]:
            name = str(variant["candidate_set"])
            totals = variant_totals.setdefault(name, {"rows": 0, "contains_correct_rows": 0})
            totals["rows"] += 1
            totals["contains_correct_rows"] += int(variant["contains_correct"])

    variant_summary = {
        name: {
            **totals,
            "contains_correct_rate": ratio(totals["contains_correct_rows"], totals["rows"]),
        }
        for name, totals in sorted(variant_totals.items())
    }
    failure_counts = Counter(row["failure_mode"] for row in rows)
    current_hits = variant_totals.get("current_followup_set", {}).get("contains_correct_rows", 0)
    planned_hits = variant_totals.get("followup_plan_explicit_set", {}).get("contains_correct_rows", 0)
    external_hits = variant_totals.get("v4_external_set", {}).get("contains_correct_rows", 0)
    union_hits = variant_totals.get("current_plus_v4_external", {}).get("contains_correct_rows", 0)
    recommendation = (
        "make_detector_association_respect_explicit_frame_candidate_ids_first"
        if planned_hits > current_hits
        else "preserve_v4_external_candidates_in_identity_confirmation_first"
        if union_hits > current_hits
        else "expand_external_candidate_retrieval_budget_or_backend_first"
        if external_hits == current_hits
        else "inspect_unclassified_candidate_set_behavior"
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "external_evidence_v4_rows": str(args.external_evidence_v4_rows),
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "followup_observation_plan": str(args.followup_observation_plan) if args.followup_observation_plan else None,
        "candidate_artifact": str(args.candidate_artifact),
        "object_node_features": str(args.object_node_features),
        "out_root": str(args.out_root),
        "rows": len(rows),
        "failure_mode_counts": dict(sorted(failure_counts.items())),
        "candidate_set_summary": variant_summary,
        "recommendation": recommendation,
        "interpretation": {
            "first_repair": "detector association should use explicit candidate_ids from the follow-up frame before another threshold change",
            "remaining_issue": "rows where V4 external set also misses the correct candidate need a broader retrieval or backend expansion",
            "first_eval_rerun_blocked": True,
            "policy_scale_comparison_blocked": True,
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "candidate_set_expansion_rows.jsonl",
            "summary": "candidate_set_expansion_summary.json",
        },
    }


def parse_budgets(text: str) -> List[int]:
    budgets = [int(item.strip()) for item in text.split(",") if item.strip()]
    if not budgets:
        raise argparse.ArgumentTypeError("expected at least one comma-separated budget")
    return sorted(set(budget for budget in budgets if budget > 0))


def run(args: argparse.Namespace) -> Dict[str, Any]:
    sources = load_jsonl(Path(args.external_evidence_v4_rows))
    followups = rows_by_branch(load_jsonl(Path(args.followup_evidence_rows)))
    plan_groups = (
        grouped_rows_by_branch(load_jsonl(Path(args.followup_observation_plan)))
        if args.followup_observation_plan
        else {}
    )
    artifacts = artifact_index(Path(args.candidate_artifact))
    object_labels = feature_index(Path(args.object_node_features))
    budgets = parse_budgets(str(args.recall_budgets))
    rows = [
        inspect_row(
            source,
            followups.get(str(source.get("external_branch_id"))),
            plan_groups.get(str(source.get("external_branch_id")), []),
            artifacts.get((str(source.get("scene_id")), str(source.get("query"))), []),
            object_labels,
            budgets,
        )
        for source in sources
    ]
    out_root = Path(args.out_root)
    write_jsonl(out_root / "candidate_set_expansion_rows.jsonl", rows)
    summary = summarize(rows, args)
    write_json(out_root / "candidate_set_expansion_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose candidate-set expansion needs after H001 held-out V4 follow-up.")
    parser.add_argument("--external-evidence-v4-rows", required=True)
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--followup-observation-plan", default=None)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--object-node-features", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--recall-budgets", default="6,10,20")
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
