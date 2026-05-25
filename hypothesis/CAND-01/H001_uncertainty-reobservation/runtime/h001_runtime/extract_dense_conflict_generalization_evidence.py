import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.dense_conflict_generalization_evidence.v1"


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def scene_key_from_scene_id(value: str) -> str:
    parts = [part for part in value.split("/") if part]
    if not parts:
        return "unknown"
    name = parts[-1]
    if name.endswith(".basis.glb"):
        return name[: -len(".basis.glb")]
    return name


def candidate_artifact_index(path: Path) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(path):
        scene_id = str(row.get("scene_id") or row.get("scene") or "")
        scene_key = str(row.get("scene_key") or scene_key_from_scene_id(scene_id))
        query = str(row.get("query") or row.get("object_category") or "")
        if not scene_key or not query:
            continue
        candidates = list(row.get("candidates") or [row])
        candidates.sort(key=lambda item: safe_float(item.get("score")) or 0.0, reverse=True)
        index[(scene_key, query)].extend(candidates)
    return index


def frame_index(path: Path) -> Dict[str, Dict[str, Any]]:
    return {str(row.get("episode_key")): dict(row) for row in load_jsonl(path)}


def associations_index(path: Path) -> Dict[Tuple[str, str], List[Dict[str, Any]]]:
    index: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in load_jsonl(path):
        key = (str(row.get("episode_key")), str(row.get("candidate_id")))
        index[key].append(dict(row))
    return index


def recall_label_index(path: Path) -> Dict[str, Dict[str, Dict[str, Any]]]:
    labels: Dict[str, Dict[str, Dict[str, Any]]] = defaultdict(dict)
    for row in load_jsonl(path):
        episode_key = str(row.get("episode_key"))
        for candidate in row.get("correct_candidates") or []:
            candidate_id = str(candidate.get("candidate_id"))
            labels[episode_key][candidate_id] = {
                "evaluation_only_candidate_id": candidate_id,
                "evaluation_only_candidate_correct": True,
                "evaluation_only_correct_source": candidate.get("correct_source"),
                "evaluation_only_recall_rank": candidate.get("rank"),
                "evaluation_only_candidate_score": candidate.get("score"),
            }
    return labels


def compact_artifact_candidate(candidate: Dict[str, Any], rank: int) -> Dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id")),
        "semantic_rank": rank,
        "semantic_score": safe_float(candidate.get("score")),
        "category": candidate.get("category"),
        "position": candidate.get("position"),
        "visit_position": candidate.get("visit_position"),
        "view_count": candidate.get("view_count"),
        "component_cells": candidate.get("component_cells"),
    }


def aggregate_candidate_evidence(
    artifact_candidate: Dict[str, Any],
    rank: int,
    association_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    associated = [row for row in association_rows if row.get("associated_to_candidate") is True]
    visible = [row for row in association_rows if row.get("projection_status") == "visible"]
    inside_box = [row for row in association_rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in association_rows if row.get("projected_pixel_inside_mask") is True]
    detector_scores = [safe_float(row.get("best_box_score")) for row in association_rows]
    detector_scores = [score for score in detector_scores if score is not None]
    depth_errors = [safe_float(row.get("depth_error_m")) for row in association_rows]
    depth_errors = [value for value in depth_errors if value is not None]
    associated_count = len(associated)
    visible_count = len(visible)
    max_detector_score = max(detector_scores, default=None)
    max_detector_term = max_detector_score if max_detector_score is not None else 0.0
    support_score = (
        min(1.0, associated_count / 3.0) * 0.45
        + min(1.0, len(inside_mask) / 3.0) * 0.20
        + min(1.0, len(inside_box) / 3.0) * 0.15
        + min(1.0, visible_count / 6.0) * 0.10
        + min(1.0, max_detector_term) * 0.10
    )
    row = compact_artifact_candidate(artifact_candidate, rank)
    row.update(
        {
            "associated_heading_count": associated_count,
            "box_hit_count": len(inside_box),
            "mask_hit_count": len(inside_mask),
            "visible_count": visible_count,
            "detector_score_max": max_detector_score,
            "min_depth_error_m": min(depth_errors, default=None),
            "depth_match_count": sum(1 for item in association_rows if item.get("depth_check_status") == "depth_match"),
            "depth_mismatch_count": sum(
                1 for item in association_rows if item.get("depth_check_status") == "depth_mismatch"
            ),
            "positive_support": associated_count > 0,
            "support_score": support_score,
            "uses_gt_for_action": False,
        }
    )
    return row


def selected_candidates(
    manifest_row: Dict[str, Any],
    artifact_rows: Sequence[Dict[str, Any]],
    frame_row: Optional[Dict[str, Any]],
    max_candidates: int,
) -> List[Dict[str, Any]]:
    by_id = {str(row.get("candidate_id")): row for row in artifact_rows}
    selected_ids = list((frame_row or {}).get("selected_candidate_ids") or [])
    if not selected_ids:
        selected_ids = [str(row.get("candidate_id")) for row in artifact_rows[:max_candidates]]
    selected: List[Dict[str, Any]] = []
    for candidate_id in selected_ids[:max_candidates]:
        candidate = by_id.get(str(candidate_id))
        if candidate is not None:
            selected.append(candidate)
    if selected:
        return selected
    return list(artifact_rows[:max_candidates])


def build_action_rows(args: argparse.Namespace) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
    manifest = load_json(Path(args.manifest))
    artifact = candidate_artifact_index(Path(args.candidate_artifact))
    frames = frame_index(Path(args.frame_summary))
    associations = associations_index(Path(args.detector_associations))
    labels = recall_label_index(Path(args.recall_rows))

    action_rows: List[Dict[str, Any]] = []
    label_rows: List[Dict[str, Any]] = []
    missing_artifact_rows: List[str] = []
    for manifest_row in manifest.get("rows", []):
        if manifest_row.get("selected_split") != args.manifest_split:
            continue
        episode_key = str(manifest_row.get("episode_key"))
        scene_key = str(manifest_row.get("scene_key"))
        query = str(manifest_row.get("target_or_query"))
        artifact_rows = artifact.get((scene_key, query), [])
        if not artifact_rows:
            missing_artifact_rows.append(episode_key)
            continue
        frame_row = frames.get(episode_key)
        selected = selected_candidates(manifest_row, artifact_rows, frame_row, int(args.max_candidates_per_row))
        candidate_rows: List[Dict[str, Any]] = []
        rank_by_id = {str(row.get("candidate_id")): rank for rank, row in enumerate(artifact_rows, start=1)}
        for candidate in selected:
            candidate_id = str(candidate.get("candidate_id"))
            candidate_rows.append(
                aggregate_candidate_evidence(
                    candidate,
                    rank_by_id.get(candidate_id, len(candidate_rows) + 1),
                    associations.get((episode_key, candidate_id), []),
                )
            )
            label = labels.get(episode_key, {}).get(candidate_id)
            label_rows.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "episode_key": episode_key,
                    "candidate_id": candidate_id,
                    "evaluation_only_candidate_correct": bool(label),
                    "evaluation_only_correct_source": None if label is None else label.get("evaluation_only_correct_source"),
                    "evaluation_only_recall_rank": None if label is None else label.get("evaluation_only_recall_rank"),
                    "evaluation_only_candidate_score": None if label is None else label.get("evaluation_only_candidate_score"),
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                }
            )
        positive_candidates = [candidate for candidate in candidate_rows if candidate["positive_support"]]
        action_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "scene_key": scene_key,
                "scene_id": manifest_row.get("scene_id"),
                "query": query,
                "source_manifest_split": manifest_row.get("source_selected_split"),
                "semantic_top_candidate_id": manifest_row.get("dense_conflict_top_candidate_id"),
                "semantic_top2_score_gap": manifest_row.get("dense_conflict_top2_score_gap"),
                "candidate_count": len(candidate_rows),
                "positive_support_candidate_count": len(positive_candidates),
                "has_any_positive_support": bool(positive_candidates),
                "evidence_status": "associated" if positive_candidates else "unassociated",
                "candidate_evidence": candidate_rows,
                "action_path_fields_exclude_evaluation_labels": True,
                "uses_gt_for_action": False,
            }
        )
    return action_rows, label_rows, {"missing_artifact_rows": missing_artifact_rows}


def best_by_support(candidates: Sequence[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    positives = [candidate for candidate in candidates if candidate["positive_support"]]
    if not positives:
        return None
    return max(
        positives,
        key=lambda item: (
            safe_float(item.get("support_score")) or 0.0,
            safe_float(item.get("semantic_score")) or 0.0,
            -int(item.get("semantic_rank") or 9999),
        ),
    )


def support_margin(best: Optional[Dict[str, Any]], candidates: Sequence[Dict[str, Any]]) -> Optional[float]:
    if best is None:
        return None
    scores = sorted(
        [safe_float(candidate.get("support_score")) or 0.0 for candidate in candidates if candidate is not best],
        reverse=True,
    )
    second = scores[0] if scores else 0.0
    return (safe_float(best.get("support_score")) or 0.0) - second


def policy_decision(row: Dict[str, Any], policy: str, min_support_margin: float) -> Dict[str, Any]:
    candidates = list(row.get("candidate_evidence") or [])
    semantic_top = min(candidates, key=lambda item: int(item.get("semantic_rank") or 9999), default=None)
    positives = [candidate for candidate in candidates if candidate["positive_support"]]
    first_associated = min(positives, key=lambda item: int(item.get("semantic_rank") or 9999), default=None)
    best = best_by_support(candidates)
    margin = support_margin(best, candidates)

    selected: Optional[Dict[str, Any]] = None
    reason = "defer_only"
    if policy == "defer_only":
        selected = None
    elif policy == "semantic_top_if_supported":
        if semantic_top and semantic_top["positive_support"]:
            selected = semantic_top
            reason = "semantic_top_has_positive_support"
        else:
            reason = "semantic_top_without_positive_support"
    elif policy == "first_associated":
        selected = first_associated
        reason = "first_semantic_rank_with_positive_support" if selected else "no_positive_support"
    elif policy == "support_score_best":
        selected = best
        reason = "best_support_score" if selected else "no_positive_support"
    elif policy == "proposed_conservative_v0":
        if best is None:
            reason = "no_positive_support"
        elif (margin or 0.0) < min_support_margin:
            reason = "defer_low_support_margin"
        else:
            selected = best
            reason = "commit_unique_support_advantage"
    else:
        raise ValueError(f"unknown policy: {policy}")

    return {
        "policy": policy,
        "episode_key": row["episode_key"],
        "action": "commit_candidate" if selected else "defer",
        "reason": reason,
        "selected_candidate_id": None if selected is None else selected.get("candidate_id"),
        "selected_support_score": None if selected is None else selected.get("support_score"),
        "support_margin": margin,
        "uses_gt_for_action": False,
    }


def evaluation_lookup(label_rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    return {
        (str(row["episode_key"]), str(row["candidate_id"])): dict(row)
        for row in label_rows
    }


def diagnostic_rows(
    action_rows: Sequence[Dict[str, Any]],
    label_rows: Sequence[Dict[str, Any]],
    policies: Sequence[str],
    min_support_margin: float,
) -> List[Dict[str, Any]]:
    labels = evaluation_lookup(label_rows)
    rows: List[Dict[str, Any]] = []
    for action_row in action_rows:
        for policy in policies:
            decision = policy_decision(action_row, policy, min_support_margin)
            selected_id = decision.get("selected_candidate_id")
            label = labels.get((str(action_row["episode_key"]), str(selected_id))) if selected_id else None
            rows.append(
                {
                    **decision,
                    "query": action_row["query"],
                    "evidence_status": action_row["evidence_status"],
                    "evaluation_only_selected_correct": None
                    if not selected_id
                    else bool(label and label.get("evaluation_only_candidate_correct")),
                    "evaluation_only_success_commit": bool(
                        selected_id and label and label.get("evaluation_only_candidate_correct")
                    ),
                    "evaluation_only_wrong_goal_commit": bool(
                        selected_id and not (label and label.get("evaluation_only_candidate_correct"))
                    ),
                    "uses_gt_for_action": False,
                    "uses_gt_for_analysis": True,
                }
            )
    return rows


def summarize_policy_diagnostics(rows: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    by_policy: Dict[str, Dict[str, Any]] = {}
    for policy in sorted({str(row["policy"]) for row in rows}):
        policy_rows = [row for row in rows if row["policy"] == policy]
        commit_rows = [row for row in policy_rows if row["action"] == "commit_candidate"]
        success_rows = [row for row in policy_rows if row["evaluation_only_success_commit"]]
        wrong_rows = [row for row in policy_rows if row["evaluation_only_wrong_goal_commit"]]
        associated_rows = [row for row in policy_rows if row["evidence_status"] == "associated"]
        by_policy[policy] = {
            "rows": len(policy_rows),
            "associated_rows": len(associated_rows),
            "commit_rows": len(commit_rows),
            "success_commit_rows": len(success_rows),
            "wrong_goal_commit_rows": len(wrong_rows),
            "commit_rate": ratio(len(commit_rows), len(policy_rows)),
            "success_commit_rate": ratio(len(success_rows), len(policy_rows)),
            "wrong_goal_commit_rate": ratio(len(wrong_rows), len(policy_rows)),
            "action_counts": dict(sorted(Counter(str(row["action"]) for row in policy_rows).items())),
            "reason_counts": dict(sorted(Counter(str(row["reason"]) for row in policy_rows).items())),
        }
    return by_policy


def forbidden_action_key(path: str, key: str) -> bool:
    lowered = key.lower()
    if lowered == "uses_gt_for_action":
        return False
    if lowered.startswith("action_path_fields_exclude"):
        return False
    forbidden = ["correct", "wrong_goal", "evaluation_only", "gt_"]
    return any(term in lowered for term in forbidden)


def scan_forbidden_keys(value: Any, prefix: str = "") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            if forbidden_action_key(prefix, str(key)):
                findings.append(child_path)
            findings.extend(scan_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_forbidden_keys(child, f"{prefix}[{index}]"))
    return findings


def run(args: argparse.Namespace) -> Dict[str, Any]:
    action_rows, label_rows, extra = build_action_rows(args)
    policies = [
        "defer_only",
        "semantic_top_if_supported",
        "first_associated",
        "support_score_best",
        "proposed_conservative_v0",
    ]
    diagnostics = diagnostic_rows(action_rows, label_rows, policies, float(args.min_support_margin))
    forbidden = []
    for index, row in enumerate(action_rows):
        forbidden.extend([f"row[{index}].{finding}" for finding in scan_forbidden_keys(row)])

    evidence_status_counts = Counter(str(row["evidence_status"]) for row in action_rows)
    query_counts = Counter(str(row["query"]) for row in action_rows)
    scene_counts = Counter(str(row["scene_key"]) for row in action_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "manifest": str(args.manifest),
        "manifest_split": str(args.manifest_split),
        "candidate_artifact": str(args.candidate_artifact),
        "frame_summary": str(args.frame_summary),
        "detector_associations": str(args.detector_associations),
        "recall_rows": str(args.recall_rows),
        "out_root": str(args.out_root),
        "rows": len(action_rows),
        "label_rows": len(label_rows),
        "evidence_status_counts": dict(sorted(evidence_status_counts.items())),
        "query_counts": dict(sorted(query_counts.items())),
        "scene_counts": dict(sorted(scene_counts.items())),
        "associated_rows": int(evidence_status_counts.get("associated", 0)),
        "unassociated_rows": int(evidence_status_counts.get("unassociated", 0)),
        "missing_artifact_rows": extra["missing_artifact_rows"],
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "policy_diagnostic_summary": summarize_policy_diagnostics(diagnostics),
        "design_decision": {
            "terminal_validation_ready": bool(action_rows and not forbidden),
            "terminal_utility_claim_allowed": False,
            "reason": (
                "evidence extraction is ready for a validation run, but utility claims require a separate "
                "terminal arbitration validation with evaluation-only labels and associated/unassociated rows separated"
            ),
            "next_script_contract": [
                "consume action_evidence_rows.jsonl only for action selection",
                "join evaluation_labels.jsonl only after decisions are frozen",
                "report associated rows and unassociated rows separately",
                "compare defer_only, semantic_top_if_supported, first_associated, support_score_best, and proposed_conservative_v0",
            ],
        },
        "interpretation": {
            "fact": "This step separates action-time detector/semantic evidence from evaluation-only correctness labels.",
            "agent_inference": (
                "Because only the associated subset has detector support, terminal arbitration should not count "
                "unassociated rows as arbitration failures; they remain detector/association coverage limits."
            ),
            "paper_claim_status": "design_gate_only_not_policy_claim",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "action_evidence": "action_evidence_rows.jsonl",
            "evaluation_labels": "evaluation_labels.jsonl",
            "policy_diagnostics": "terminal_policy_diagnostic_rows.jsonl",
            "summary": "terminal_arbitration_design_summary.json",
        },
    }

    out_root = Path(args.out_root)
    write_jsonl(out_root / "action_evidence_rows.jsonl", action_rows)
    write_jsonl(out_root / "evaluation_labels.jsonl", label_rows)
    write_jsonl(out_root / "terminal_policy_diagnostic_rows.jsonl", diagnostics)
    write_json(out_root / "terminal_arbitration_design_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract GT-separated terminal evidence for dense conflict generalization.")
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-split", default="dense_conflict_generalization_v1")
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--frame-summary", required=True)
    parser.add_argument("--detector-associations", required=True)
    parser.add_argument("--recall-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--max-candidates-per-row", type=int, default=5)
    parser.add_argument("--min-support-margin", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
