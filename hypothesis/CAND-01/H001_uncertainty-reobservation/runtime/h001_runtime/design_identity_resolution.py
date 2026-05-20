import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.identity_resolution_design.v1"


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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def artifact_index(path: Path) -> Dict[Tuple[str, str], Dict[str, Dict[str, Any]]]:
    indexed: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = {}
    for row in load_jsonl(path):
        indexed[(str(row.get("scene_id")), str(row.get("query")))] = {
            str(candidate.get("candidate_id")): candidate
            for candidate in row.get("candidates") or []
            if candidate.get("candidate_id") is not None
        }
    return indexed


def position(candidate_id: str, artifact_candidates: Dict[str, Dict[str, Any]]) -> Optional[List[float]]:
    candidate = artifact_candidates.get(candidate_id)
    if not candidate:
        return None
    value = candidate.get("position")
    if not isinstance(value, list) or len(value) != 3:
        return None
    return [safe_float(item) for item in value]


def distance_xz(a: List[float], b: List[float]) -> float:
    return math.hypot(float(a[0]) - float(b[0]), float(a[2]) - float(b[2]))


def candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    return list(row.get("followup_candidate_evidence") or [])


def strong_positive(candidate: Dict[str, Any], min_score: float) -> bool:
    return (
        candidate.get("positive_support") is True
        and candidate.get("followup_strong_depth_evidence") is True
        and safe_float(candidate.get("S_ext")) >= min_score
    )


def score(candidate: Dict[str, Any]) -> float:
    return safe_float(candidate.get("S_ext"))


def best_strong(row: Dict[str, Any], args: argparse.Namespace) -> Optional[str]:
    eligible = [
        candidate
        for candidate in candidates(row)
        if strong_positive(candidate, float(args.min_score))
    ]
    if not eligible:
        return None
    best = max(
        eligible,
        key=lambda candidate: (
            score(candidate),
            safe_float(candidate.get("strict_association_count")),
            safe_float(candidate.get("mask_hit_count")),
        ),
    )
    return str(best.get("candidate_id"))


def selected_local_cluster_margin(
    row: Dict[str, Any],
    artifact_candidates: Dict[str, Dict[str, Any]],
    args: argparse.Namespace,
) -> Optional[str]:
    selected_id = row.get("selected_candidate_id")
    if selected_id is None:
        return None
    selected_id = str(selected_id)
    selected = next((candidate for candidate in candidates(row) if candidate.get("candidate_id") == selected_id), None)
    if selected is None or not strong_positive(selected, float(args.min_score)):
        return None
    selected_pos = position(selected_id, artifact_candidates)
    if selected_pos is None:
        return None

    radius = float(args.cluster_radius_m)
    local: List[Dict[str, Any]] = []
    outside: List[Dict[str, Any]] = []
    for candidate in candidates(row):
        candidate_id = str(candidate.get("candidate_id"))
        if not strong_positive(candidate, float(args.min_score)):
            continue
        candidate_pos = position(candidate_id, artifact_candidates)
        if candidate_pos is None:
            continue
        if distance_xz(selected_pos, candidate_pos) <= radius:
            local.append(candidate)
        else:
            outside.append(candidate)

    selected_score = score(selected)
    local_scores = [score(candidate) for candidate in local if candidate.get("candidate_id") != selected_id]
    outside_scores = [score(candidate) for candidate in outside]
    if len(local) < int(args.min_local_strong_count):
        return None
    if local_scores and max(local_scores) > selected_score + float(args.local_score_tolerance):
        return None
    if outside_scores and max(outside_scores) >= selected_score - float(args.outside_score_margin):
        return None
    return selected_id


def oracle_best_correct(row: Dict[str, Any]) -> Optional[str]:
    correct = [
        candidate
        for candidate in candidates(row)
        if candidate.get("candidate_correct") is True
        and candidate.get("followup_strong_depth_evidence") is True
    ]
    if not correct:
        return None
    return str(max(correct, key=score).get("candidate_id"))


def evaluate(
    rows: List[Dict[str, Any]],
    artifact: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]],
    variant: str,
    decisions: Dict[str, Optional[str]],
) -> Dict[str, Any]:
    commit_rows = []
    success_rows = []
    wrong_rows = []
    no_valid_rows = []
    row_details = []
    for row in rows:
        branch_id = str(row.get("external_branch_id"))
        commit_id = decisions.get(branch_id)
        candidate_rows = candidates(row)
        correct_ids = [str(candidate.get("candidate_id")) for candidate in candidate_rows if candidate.get("candidate_correct") is True]
        committed = commit_id is not None
        selected = next((candidate for candidate in candidate_rows if candidate.get("candidate_id") == commit_id), None)
        success = bool(selected and selected.get("candidate_correct") is True)
        wrong = bool(committed and not success)
        no_valid = bool(committed and not correct_ids)
        if committed:
            commit_rows.append(row)
        if success:
            success_rows.append(row)
        if wrong:
            wrong_rows.append(row)
        if no_valid:
            no_valid_rows.append(row)
        row_details.append(
            {
                "schema_version": SCHEMA_VERSION,
                "variant": variant,
                "external_branch_id": branch_id,
                "episode_key": row.get("episode_key"),
                "scene_id": row.get("scene_id"),
                "query": row.get("query"),
                "label_case": row.get("label_case"),
                "property_group": row.get("property_group"),
                "commit_candidate_id": commit_id,
                "commit_candidate_correct": None if selected is None else selected.get("candidate_correct"),
                "correct_candidate_ids": correct_ids,
                "commit": committed,
                "success_commit": success,
                "wrong_goal_commit": wrong,
                "no_valid_commit": no_valid,
                "uses_gt_for_action": variant.startswith("oracle_"),
                "uses_gt_for_analysis": True,
            }
        )
    return {
        "variant": variant,
        "rows": len(rows),
        "commit_rows": len(commit_rows),
        "success_commit_rows": len(success_rows),
        "wrong_goal_commit_rows": len(wrong_rows),
        "no_valid_commit_rows": len(no_valid_rows),
        "commit_rate": ratio(len(commit_rows), len(rows)),
        "success_commit_rate": ratio(len(success_rows), len(rows)),
        "wrong_goal_commit_rate": ratio(len(wrong_rows), len(rows)),
        "wrong_goal_commit_rate_on_commits": ratio(len(wrong_rows), len(commit_rows)),
        "no_valid_commit_rate": ratio(len(no_valid_rows), len(rows)),
        "uses_gt_for_action": variant.startswith("oracle_"),
        "uses_gt_for_analysis": True,
        "rows_detail": row_details,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.followup_evidence_rows))
    artifacts = artifact_index(Path(args.candidate_artifact))
    decisions_by_variant: Dict[str, Dict[str, Optional[str]]] = {
        "current_v3_defer": {str(row.get("external_branch_id")): None for row in rows},
        "best_strong_score": {str(row.get("external_branch_id")): best_strong(row, args) for row in rows},
        "selected_local_cluster_margin": {
            str(row.get("external_branch_id")): selected_local_cluster_margin(
                row,
                artifacts.get((str(row.get("scene_id")), str(row.get("query"))), {}),
                args,
            )
            for row in rows
        },
        "oracle_best_strong_correct": {str(row.get("external_branch_id")): oracle_best_correct(row) for row in rows},
    }
    evaluations = [
        evaluate(rows, artifacts, variant, decisions)
        for variant, decisions in decisions_by_variant.items()
    ]
    out_root = Path(args.out_root)
    detail_rows = [
        detail
        for evaluation in evaluations
        for detail in evaluation.pop("rows_detail")
    ]
    write_jsonl(out_root / "identity_resolution_variant_rows.jsonl", detail_rows)
    by_variant = {evaluation["variant"]: evaluation for evaluation in evaluations}
    recommended = "selected_local_cluster_margin"
    payload = {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "rows": len(rows),
        "parameters": {
            "min_score": float(args.min_score),
            "cluster_radius_m": float(args.cluster_radius_m),
            "min_local_strong_count": int(args.min_local_strong_count),
            "local_score_tolerance": float(args.local_score_tolerance),
            "outside_score_margin": float(args.outside_score_margin),
        },
        "variant_summary": by_variant,
        "recommended_design": recommended,
        "design_contract": {
            "selected_local_cluster_margin": [
                "commit only the source selected candidate",
                "require selected candidate to have positive support and strong depth evidence",
                "require at least one additional strong candidate within a local spatial cluster",
                "reject commit if a local strong candidate has materially higher evidence than selected",
                "reject commit if any outside-cluster strong candidate is near-tied with selected",
            ],
            "broader_retrieval_branch": [
                "rows with no correct candidate in the follow-up set are not identity-objective failures",
                "route these rows to candidate retrieval/backend expansion instead of threshold tuning",
            ],
        },
        "interpretation": {
            "same_split_design_only": True,
            "first_eval_rerun_blocked": True,
            "policy_scale_comparison_blocked": True,
            "next_required": "implement selected_local_cluster_margin as a fixed non-GT objective and validate on a separate split before first_eval or policy-scale",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "identity_resolution_variant_rows.jsonl",
            "summary": "identity_resolution_design_summary.json",
        },
    }
    write_json(out_root / "identity_resolution_design_summary.json", payload)
    return payload


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design H001 identity-resolution objective variants.")
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-score", type=float, default=0.35)
    parser.add_argument("--cluster-radius-m", type=float, default=2.0)
    parser.add_argument("--min-local-strong-count", type=int, default=2)
    parser.add_argument("--local-score-tolerance", type=float, default=0.002)
    parser.add_argument("--outside-score-margin", type=float, default=0.005)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
