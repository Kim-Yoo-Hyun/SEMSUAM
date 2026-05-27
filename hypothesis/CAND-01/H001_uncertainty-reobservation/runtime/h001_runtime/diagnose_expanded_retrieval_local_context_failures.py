import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_local_context_failure_diagnostic.v1"
PROPOSED_VARIANT = "proposed_local_context_unique_own_view_advantage"


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


def label_index(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row.get("episode_key")), str(row.get("candidate_id"))): row
        for row in label_rows
        if row.get("episode_key") is not None and row.get("candidate_id") is not None
    }


def evidence_groups(evidence_rows: Sequence[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in evidence_rows:
        grouped[str(row.get("expanded_retrieval_request_id"))].append(row)
    return grouped


def support_key(row: Dict[str, Any]) -> Tuple[int, int, int, float, float, str]:
    return (
        int(row.get("strict_association_count") or 0),
        int(row.get("mask_hit_count") or 0),
        int(row.get("visible_count") or 0),
        float(row.get("prior_detector_evidence_score") or 0.0),
        float(row.get("semantic_score") or 0.0),
        str(row.get("candidate_id")),
    )


def role_tags(role: Optional[str]) -> List[str]:
    text = str(role or "")
    tags: List[str] = []
    if "source_top" in text:
        tags.append("selected_source_top_role")
    if "detector_strong" in text:
        tags.append("selected_detector_strong_role")
    if "local_context_candidate" in text:
        tags.append("selected_local_context_role")
    return tags


def candidate_label(labels: Dict[Tuple[str, str], Dict[str, Any]], row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return labels.get((str(row.get("episode_key")), str(row.get("candidate_id"))))


def diagnose_row(
    decision: Dict[str, Any],
    request_evidence: Sequence[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> Dict[str, Any]:
    selected_id = str(decision.get("selected_candidate_id"))
    selected = next((row for row in request_evidence if str(row.get("candidate_id")) == selected_id), None)
    labeled_candidates = [
        (row, candidate_label(labels, row))
        for row in request_evidence
    ]
    correct_candidates = [
        row for row, label in labeled_candidates
        if label is not None and label.get("evaluation_only_candidate_correct") is True
    ]
    wrong_candidates = [
        row for row, label in labeled_candidates
        if label is not None and label.get("evaluation_only_candidate_correct") is False
    ]
    best_correct = max(correct_candidates, key=support_key, default=None)
    best_wrong = max(wrong_candidates, key=support_key, default=None)
    tags: List[str] = []
    if decision.get("action") != "commit_candidate":
        tags.append(str(decision.get("reason") or "defer"))
    if decision.get("evaluation_only_no_valid_commit") is True:
        tags.extend(["source_pool_no_valid_candidate", "no_correct_candidate_in_planned_set"])
    if decision.get("evaluation_only_wrong_goal_commit") is True:
        tags.append("wrong_commit")
        if best_correct is None:
            tags.append("wrong_commit_without_correct_planned_candidate")
        elif selected is not None:
            if int(selected.get("strict_association_count") or 0) > int(best_correct.get("strict_association_count") or 0):
                tags.append("wrong_candidate_stronger_own_view_than_best_correct")
            elif int(selected.get("strict_association_count") or 0) == int(best_correct.get("strict_association_count") or 0):
                tags.append("wrong_candidate_tied_own_view_with_best_correct")
            else:
                tags.append("wrong_selected_despite_stronger_correct")
            if best_correct.get("strong_own_view_evidence") is not True:
                tags.append("best_correct_not_strong_own_view")
    if decision.get("evaluation_only_success_commit") is True:
        tags.append("success_commit")
    tags.extend(role_tags(decision.get("selected_candidate_role")))
    if (
        selected is not None
        and best_correct is not None
        and selected.get("candidate_id") != best_correct.get("candidate_id")
        and selected.get("strong_own_view_evidence") is True
        and best_correct.get("strong_own_view_evidence") is not True
    ):
        tags.append("own_view_support_prefers_wrong_over_weak_correct")
    return {
        "schema_version": SCHEMA_VERSION,
        "expanded_retrieval_request_id": decision.get("expanded_retrieval_request_id"),
        "rival_identity_request_id": decision.get("rival_identity_request_id"),
        "episode_key": decision.get("episode_key"),
        "scene_key": decision.get("scene_key"),
        "query": decision.get("query"),
        "action": decision.get("action"),
        "reason": decision.get("reason"),
        "selected_candidate_id": selected_id if selected is not None else None,
        "selected_candidate_role": decision.get("selected_candidate_role"),
        "selected_correct": decision.get("evaluation_only_selected_correct"),
        "request_correct_candidate_count": decision.get("evaluation_only_request_correct_candidate_count"),
        "candidate_count": len(request_evidence),
        "strong_own_view_candidate_count": decision.get("strong_own_view_candidate_count"),
        "selected_strict_association_count": None if selected is None else selected.get("strict_association_count"),
        "selected_mask_hit_count": None if selected is None else selected.get("mask_hit_count"),
        "selected_visible_count": None if selected is None else selected.get("visible_count"),
        "best_correct_candidate_id": None if best_correct is None else best_correct.get("candidate_id"),
        "best_correct_role": None if best_correct is None else best_correct.get("candidate_role"),
        "best_correct_strict_association_count": None if best_correct is None else best_correct.get("strict_association_count"),
        "best_correct_mask_hit_count": None if best_correct is None else best_correct.get("mask_hit_count"),
        "best_correct_visible_count": None if best_correct is None else best_correct.get("visible_count"),
        "best_correct_strong_own_view_evidence": None if best_correct is None else best_correct.get("strong_own_view_evidence"),
        "best_wrong_candidate_id": None if best_wrong is None else best_wrong.get("candidate_id"),
        "best_wrong_role": None if best_wrong is None else best_wrong.get("candidate_role"),
        "best_wrong_strict_association_count": None if best_wrong is None else best_wrong.get("strict_association_count"),
        "diagnostic_tags": sorted(set(tags)),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    evidence_rows = load_jsonl(Path(args.evidence_rows))
    evaluated_rows = load_jsonl(Path(args.evaluated_rows))
    labels = label_index(load_jsonl(Path(args.evaluation_labels)))
    evidence_by_request = evidence_groups(evidence_rows)
    proposed_rows = [row for row in evaluated_rows if row.get("variant") == PROPOSED_VARIANT]
    diagnostic_rows = [
        diagnose_row(row, evidence_by_request.get(str(row.get("expanded_retrieval_request_id")), []), labels)
        for row in proposed_rows
    ]
    tag_counts: Counter[str] = Counter()
    for row in diagnostic_rows:
        tag_counts.update(row.get("diagnostic_tags") or [])
    commit_rows = [row for row in diagnostic_rows if row.get("action") == "commit_candidate"]
    wrong_rows = [row for row in diagnostic_rows if row.get("selected_correct") is False and row.get("action") == "commit_candidate"]
    success_rows = [row for row in diagnostic_rows if row.get("selected_correct") is True and row.get("action") == "commit_candidate"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "evidence_rows": str(args.evidence_rows),
        "evaluated_rows": str(args.evaluated_rows),
        "evaluation_labels": str(args.evaluation_labels),
        "out_root": str(out_root),
        "proposed_request_rows": len(proposed_rows),
        "proposed_commit_rows": len(commit_rows),
        "proposed_success_commit_rows": len(success_rows),
        "proposed_wrong_goal_commit_rows": len(wrong_rows),
        "diagnostic_tag_counts": dict(sorted(tag_counts.items())),
        "selected_role_counts": dict(sorted(Counter(str(row.get("selected_candidate_role")) for row in commit_rows).items())),
        "query_counts": dict(sorted(Counter(str(row.get("query")) for row in diagnostic_rows).items())),
        "dominant_failure_mechanisms": [
            "source_pool_no_valid_candidate",
            "wrong_candidate_stronger_own_view_than_best_correct",
            "best_correct_not_strong_own_view",
            "selected_detector_strong_role",
        ],
        "revision_constraints": [
            "do not threshold-tune from joined labels",
            "do not promote source-top, detector-score-best, own-support-best, or local-context-only-best because all are unsafe",
            "separate no-valid candidate-pool failures from wrong-instance arbitration failures",
            "treat own-view category evidence as object visibility, not ObjectNav goal validity",
        ],
        "next_gate": "design local-context revision only after this failure taxonomy is reflected in the objective contract",
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "expanded_retrieval_local_context_failure_rows.jsonl",
            "summary": "expanded_retrieval_local_context_failure_summary.json",
        },
    }
    write_jsonl(out_root / "expanded_retrieval_local_context_failure_rows.jsonl", diagnostic_rows)
    write_json(out_root / "expanded_retrieval_local_context_failure_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose expanded-retrieval local-context post-observation failures.")
    parser.add_argument("--evidence-rows", required=True)
    parser.add_argument("--evaluated-rows", required=True)
    parser.add_argument("--evaluation-labels", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
