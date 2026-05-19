import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from h001_runtime.plan_association_recovery_observation import (
    NavmeshSnapper,
    artifact_index,
    candidate_viewpoint,
    plan_standoff_viewpoint,
)


SCHEMA_VERSION = "h001.external_candidate_second_stage_identity_plan.v1"
POLICY_NAME = "ExternalCandidateSecondStageIdentityConfirmation"
REQUEST_ACTION = "followup_evidence_v1_request_identity_confirmation"


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def ordered_unique(values: Iterable[Any]) -> List[str]:
    result: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text == "None" or text in seen:
            continue
        result.append(text)
        seen.add(text)
    return result


def evidence_candidates(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    values = row.get("followup_candidate_evidence") or []
    return [value for value in values if isinstance(value, dict) and value.get("candidate_id") is not None]


def evidence_by_id(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(candidate.get("candidate_id")): candidate for candidate in evidence_candidates(row)}


def strongest_positive_rivals(row: Dict[str, Any], selected_id: str, max_rivals: int) -> List[str]:
    rivals = [
        candidate
        for candidate in evidence_candidates(row)
        if str(candidate.get("candidate_id")) != selected_id and candidate.get("positive_support") is True
    ]
    rivals.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
            safe_float(candidate.get("mask_hit_count")) or 0.0,
        ),
        reverse=True,
    )
    return [str(candidate.get("candidate_id")) for candidate in rivals[:max_rivals]]


def strongest_rivals(row: Dict[str, Any], selected_id: str, max_rivals: int) -> List[str]:
    positive = strongest_positive_rivals(row, selected_id, max_rivals)
    strong = [
        candidate
        for candidate in evidence_candidates(row)
        if str(candidate.get("candidate_id")) != selected_id
        and candidate.get("followup_strong_depth_evidence") is True
    ]
    strong.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
        ),
        reverse=True,
    )
    return ordered_unique([*positive, *(candidate.get("candidate_id") for candidate in strong)])[:max_rivals]


def candidate_ids_for_request(row: Dict[str, Any], selected_id: str, rivals: List[str], max_ids: int) -> List[str]:
    return ordered_unique([selected_id, *rivals, *(row.get("followup_candidate_ids") or [])])[:max_ids]


def viewpoint_for_candidate(
    source: Dict[str, Any],
    candidate: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    alt_id: Optional[str],
    snapper: NavmeshSnapper,
    args: argparse.Namespace,
) -> Optional[Tuple[List[float], List[float], str, Dict[str, Any]]]:
    standoff = plan_standoff_viewpoint(
        {"scene_id": source.get("scene_id"), "viewpoint_position": source.get("viewpoint_position")},
        candidate,
        candidates,
        alt_id,
        snapper,
        args,
    )
    if standoff is not None:
        return standoff["position"], standoff["rotation"], str(standoff.get("viewpoint_source")), standoff
    fallback = candidate_viewpoint(candidate)
    if fallback is None:
        return None
    position, rotation = fallback
    return position, rotation, "candidate_visit_position_fallback", {}


def make_plan_row(
    source: Dict[str, Any],
    args: argparse.Namespace,
    source_index: int,
    role: str,
    candidate_id: str,
    candidate_ids: List[str],
    position: List[float],
    rotation: List[float],
    viewpoint_source: str,
    extra: Dict[str, Any],
    selected_id: str,
    rival_ids: List[str],
) -> Dict[str, Any]:
    suffix = candidate_id.rsplit(":", 1)[-1]
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "source_index": source_index,
        "source_schema_version": source.get("schema_version"),
        "policy": POLICY_NAME,
        "viewpoint_policy": POLICY_NAME,
        "viewpoint_id": f"{source.get('external_branch_id')}:stage2_identity:{role}:{suffix}",
        "candidate_id": candidate_id,
        "candidate_ids": candidate_ids,
        "viewpoint_position": position,
        "viewpoint_rotation": rotation,
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "property_group": source.get("property_group"),
        "label_case": source.get("label_case"),
        "external_branch_id": source.get("external_branch_id"),
        "source_external_branch_id": source.get("external_branch_id"),
        "source_followup_action": source.get("followup_evidence_v1_action"),
        "source_followup_reason": source.get("followup_evidence_v1_reason"),
        "source_external_evidence_v4_action": source.get("source_external_evidence_v4_action"),
        "source_external_evidence_v4_reason": source.get("source_external_evidence_v4_reason"),
        "followup_evidence_v1_action": source.get("followup_evidence_v1_action"),
        "followup_evidence_v1_reason": source.get("followup_evidence_v1_reason"),
        "followup_set_contains_correct": source.get("followup_set_contains_correct"),
        "selected_candidate_id": selected_id,
        "selected_score": source.get("selected_score"),
        "score_margin": source.get("score_margin"),
        "second_stage_policy": POLICY_NAME,
        "second_stage_action": "identity_confirmation",
        "second_stage_reason": "confirm_v2_request_identity_candidate_against_rival",
        "second_stage_role": role,
        "second_stage_candidate_id": candidate_id,
        "second_stage_selected_candidate_id": selected_id,
        "second_stage_rival_candidate_ids": rival_ids,
        "second_stage_viewpoint_source": viewpoint_source,
        "second_stage_direct_commit_allowed": False,
        "second_stage_visit_position_only_commit_allowed": False,
    }
    for key, value in extra.items():
        row[f"second_stage_{key}"] = value
    return row


def plan_rows_for_source(
    source: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    source_index: int,
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selected_id = str(source.get("selected_candidate_id") or "")
    if selected_id not in candidates:
        return [], [{"source_index": source_index, "skip_reason": "missing_selected_candidate", **source}]
    rivals = strongest_rivals(source, selected_id, int(args.max_rivals))
    if not rivals:
        return [], [{"source_index": source_index, "skip_reason": "missing_positive_or_strong_rival", **source}]

    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    targets = [("selected_standoff", selected_id), *[(f"rival_{idx}_standoff", rival_id) for idx, rival_id in enumerate(rivals, start=1)]]
    candidate_ids = candidate_ids_for_request(source, selected_id, rivals, int(args.max_candidate_ids))
    for role, candidate_id in targets[: int(args.max_targets_per_request)]:
        candidate = candidates.get(candidate_id)
        if candidate is None:
            skipped.append({"source_index": source_index, "candidate_id": candidate_id, "skip_reason": "missing_candidate"})
            continue
        alt_ids = [value for value in candidate_ids if value != candidate_id]
        viewpoint = viewpoint_for_candidate(source, candidate, candidates, alt_ids[0] if alt_ids else None, snapper, args)
        if viewpoint is None:
            skipped.append({"source_index": source_index, "candidate_id": candidate_id, "skip_reason": "no_viewpoint"})
            continue
        position, rotation, viewpoint_source, extra = viewpoint
        rows.append(
            make_plan_row(
                source,
                args,
                source_index,
                role,
                candidate_id,
                candidate_ids,
                position,
                rotation,
                viewpoint_source,
                extra,
                selected_id,
                rivals,
            )
        )
    return rows, skipped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    rows = load_jsonl(Path(args.followup_evidence_rows))
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    request_rows = [row for row in rows if row.get("followup_evidence_v1_action") == REQUEST_ACTION]
    if int(args.max_requests) > 0:
        request_rows = request_rows[: int(args.max_requests)]

    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    role_counts: Counter[str] = Counter()
    viewpoint_source_counts: Counter[str] = Counter()
    rows_by_branch: Dict[str, int] = defaultdict(int)
    request_query_counts: Counter[str] = Counter()

    try:
        for source_index, source in enumerate(request_rows):
            key = (str(source.get("scene_id")), str(source.get("query")))
            candidates = candidates_by_key.get(key, {})
            request_query_counts[str(source.get("query"))] += 1
            if not candidates:
                skipped_rows.append({"source_index": source_index, "skip_reason": "missing_scene_query_candidates", **source})
                continue
            rows_for_source, skipped = plan_rows_for_source(source, candidates, snapper, source_index, args)
            plan_rows.extend(rows_for_source)
            skipped_rows.extend(skipped)
            for row in rows_for_source:
                role_counts[str(row.get("second_stage_role"))] += 1
                viewpoint_source_counts[str(row.get("second_stage_viewpoint_source"))] += 1
                rows_by_branch[str(row.get("external_branch_id"))] += 1
    finally:
        snapper.close()

    write_jsonl(out_root / "external_candidate_second_stage_identity_plan.jsonl", plan_rows)
    write_jsonl(out_root / "external_candidate_second_stage_identity_skipped.jsonl", skipped_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "followup_evidence_rows": str(args.followup_evidence_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "policy": POLICY_NAME,
        "source_rows": len(rows),
        "request_rows": len(request_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "request_query_counts": dict(sorted(request_query_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "viewpoint_source_counts": dict(sorted(viewpoint_source_counts.items())),
        "rows_by_external_branch_id": dict(sorted(rows_by_branch.items())),
        "max_rivals": int(args.max_rivals),
        "max_candidate_ids": int(args.max_candidate_ids),
        "max_targets_per_request": int(args.max_targets_per_request),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "plan_rows": "external_candidate_second_stage_identity_plan.jsonl",
            "skipped_rows": "external_candidate_second_stage_identity_skipped.jsonl",
            "summary": "external_candidate_second_stage_identity_summary.json",
        },
    }
    write_json(out_root / "external_candidate_second_stage_identity_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan H001 second-stage identity confirmation for V2 follow-up requests.")
    parser.add_argument("--followup-evidence-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--run-id", default="h001_external_candidate_second_stage_identity_v1")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--max-requests", type=int, default=0)
    parser.add_argument("--max-rivals", type=int, default=1)
    parser.add_argument("--max-candidate-ids", type=int, default=6)
    parser.add_argument("--max-targets-per-request", type=int, default=2)
    parser.add_argument("--standoff-distances", type=lambda text: [float(x) for x in text.split(",") if x], default=[1.25, 1.75, 2.25])
    parser.add_argument("--preferred-standoff-distance-m", type=float, default=1.75)
    parser.add_argument("--min-standoff-distance-m", type=float, default=0.75)
    parser.add_argument("--max-standoff-distance-m", type=float, default=3.25)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
