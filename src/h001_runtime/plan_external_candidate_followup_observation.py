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


SCHEMA_VERSION = "h001.external_candidate_followup_observation_plan.v1"
POLICY_NAME = "ExternalCandidateFollowupObservation"


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


def finite_vector(value: Any, length: int = 3) -> bool:
    if not isinstance(value, list) or len(value) != length:
        return False
    return all(safe_float(item) is not None for item in value)


def candidate_rank(candidate_id: str) -> Optional[int]:
    try:
        return int(candidate_id.rsplit(":", 1)[-1]) + 1
    except (TypeError, ValueError):
        return None


def all_candidates_sorted(candidates: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows = list(candidates.values())
    rows.sort(
        key=lambda candidate: (
            safe_float(candidate.get("score")) or -math.inf,
            -(candidate_rank(str(candidate.get("candidate_id"))) or 9999),
        ),
        reverse=True,
    )
    return rows


def evidence_by_id(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(candidate.get("candidate_id")): candidate
        for candidate in row.get("candidate_evidence") or []
        if candidate.get("candidate_id") is not None
    }


def strong_candidate_ids(row: Dict[str, Any]) -> List[str]:
    rows = [
        candidate
        for candidate in row.get("candidate_evidence") or []
        if candidate.get("v4_strong_depth_evidence") is True
    ]
    rows.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
            -int(candidate.get("external_branch_rank") or 9999),
        ),
        reverse=True,
    )
    return [str(candidate.get("candidate_id")) for candidate in rows if candidate.get("candidate_id") is not None]


def positive_candidate_ids(row: Dict[str, Any]) -> List[str]:
    rows = [
        candidate
        for candidate in row.get("candidate_evidence") or []
        if candidate.get("positive_support") is True
    ]
    rows.sort(
        key=lambda candidate: (
            safe_float(candidate.get("S_ext")) or 0.0,
            safe_float(candidate.get("strict_association_count")) or 0.0,
            -int(candidate.get("external_branch_rank") or 9999),
        ),
        reverse=True,
    )
    return [str(candidate.get("candidate_id")) for candidate in rows if candidate.get("candidate_id") is not None]


def ordered_unique(values: Iterable[Optional[str]]) -> List[str]:
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


def followup_candidate_ids(row: Dict[str, Any], primary_id: str, max_ids: int) -> List[str]:
    ids = ordered_unique(
        [
            primary_id,
            *(strong_candidate_ids(row)),
            *(positive_candidate_ids(row)),
            *(row.get("external_candidate_ids") or []),
        ]
    )
    return ids[:max_ids]


def make_base_row(
    source: Dict[str, Any],
    args: argparse.Namespace,
    source_index: int,
    candidate_id: str,
    candidate_ids: List[str],
    viewpoint_position: List[float],
    viewpoint_rotation: List[float],
    followup_action: str,
    followup_reason: str,
    viewpoint_source: str,
    role: str,
) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": str(args.run_id),
        "source_index": source_index,
        "source_schema_version": source.get("schema_version"),
        "policy": POLICY_NAME,
        "viewpoint_policy": POLICY_NAME,
        "viewpoint_id": f"{source.get('external_branch_id')}:{followup_action}:{role}:{candidate_id.rsplit(':', 1)[-1]}",
        "candidate_id": candidate_id,
        "candidate_ids": candidate_ids,
        "viewpoint_position": viewpoint_position,
        "viewpoint_rotation": viewpoint_rotation,
        "commit_after_reobserve": False,
        "observation_success": True,
        "uses_gt_for_action": False,
        "episode_key": source.get("episode_key"),
        "scene_id": source.get("scene_id"),
        "query": source.get("query"),
        "followup_action": followup_action,
        "followup_reason": followup_reason,
        "followup_role": role,
        "followup_viewpoint_source": viewpoint_source,
        "external_branch_id": source.get("external_branch_id"),
        "external_branch_trigger_reason": source.get("external_branch_trigger_reason"),
        "external_candidate_ids": source.get("external_candidate_ids"),
        "external_evidence_v4_action": source.get("external_evidence_v4_action"),
        "external_evidence_v4_reason": source.get("external_evidence_v4_reason"),
        "selected_candidate_id": source.get("selected_candidate_id"),
        "selected_score": source.get("selected_score"),
        "score_margin": source.get("score_margin"),
        "property_group": source.get("property_group"),
        "label_case": source.get("label_case"),
        "source_objective_prefix": source.get("source_objective_prefix"),
        "source_objective_action": source.get("source_objective_action"),
        "source_objective_reason": source.get("source_objective_reason"),
        "pair_observation_id": source.get("pair_observation_id"),
        "pair_top_candidate_id": source.get("pair_top_candidate_id"),
        "pair_alt_candidate_id": source.get("pair_alt_candidate_id"),
    }


def standoff_or_visit_viewpoint(
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


def identity_confirmation_rows(
    source: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    snapper: NavmeshSnapper,
    source_index: int,
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    selected_id = str(source.get("selected_candidate_id"))
    selected = candidates.get(selected_id)
    if selected is None:
        return [], [{"source_index": source_index, "skip_reason": "missing_selected_candidate", **source}]
    strong_ids = strong_candidate_ids(source)
    positive_ids = positive_candidate_ids(source)
    targets = ordered_unique([selected_id, *strong_ids, *positive_ids])[: int(args.max_identity_targets)]
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for target_index, target_id in enumerate(targets):
        candidate = candidates.get(target_id)
        if candidate is None:
            skipped.append({"source_index": source_index, "candidate_id": target_id, "skip_reason": "missing_candidate"})
            continue
        alt_ids = [value for value in targets if value != target_id]
        alt_id = alt_ids[0] if alt_ids else selected_id
        viewpoint = standoff_or_visit_viewpoint(source, candidate, candidates, alt_id, snapper, args)
        if viewpoint is None:
            skipped.append({"source_index": source_index, "candidate_id": target_id, "skip_reason": "no_viewpoint"})
            continue
        position, rotation, viewpoint_source, extra = viewpoint
        candidate_ids = followup_candidate_ids(source, target_id, int(args.max_identity_candidate_ids))
        row = make_base_row(
            source,
            args,
            source_index,
            target_id,
            candidate_ids,
            position,
            rotation,
            "identity_confirmation",
            str(source.get("external_evidence_v4_reason")),
            viewpoint_source,
            "selected" if target_id == selected_id else f"rival_{target_index}",
        )
        row.update({f"followup_{key}": value for key, value in extra.items()})
        rows.append(row)
    return rows, skipped


def expanded_retrieval_rows(
    source: Dict[str, Any],
    candidates: Dict[str, Dict[str, Any]],
    source_index: int,
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    excluded = set(str(value) for value in (source.get("external_candidate_ids") or []))
    excluded.add(str(source.get("pair_top_candidate_id")))
    excluded.add(str(source.get("pair_alt_candidate_id")))
    pool = [
        candidate
        for candidate in all_candidates_sorted(candidates)
        if str(candidate.get("candidate_id")) not in excluded
        and finite_vector(candidate.get("visit_position"), 3)
    ]
    selected = pool[: int(args.max_expanded_candidates)]
    rows: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    if not selected:
        skipped.append({"source_index": source_index, "skip_reason": "no_expanded_candidates", **source})
        return rows, skipped
    selected_ids = [str(candidate.get("candidate_id")) for candidate in selected]
    for rank, candidate in enumerate(selected, start=1):
        candidate_id = str(candidate.get("candidate_id"))
        viewpoint = candidate_viewpoint(candidate)
        if viewpoint is None:
            skipped.append({"source_index": source_index, "candidate_id": candidate_id, "skip_reason": "no_visit_viewpoint"})
            continue
        position, rotation = viewpoint
        rows.append(
            make_base_row(
                source,
                args,
                source_index,
                candidate_id,
                selected_ids,
                position,
                rotation,
                "expanded_retrieval",
                str(source.get("external_evidence_v4_reason")),
                "expanded_candidate_visit_position",
                f"expanded_{rank}",
            )
        )
    return rows, skipped


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    source_rows = load_jsonl(Path(args.external_evidence_v4_rows))
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    snapper = NavmeshSnapper(args.data_root)
    plan_rows: List[Dict[str, Any]] = []
    skipped_rows: List[Dict[str, Any]] = []
    source_action_counts: Counter[str] = Counter()
    followup_action_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    viewpoint_source_counts: Counter[str] = Counter()
    rows_by_source: Dict[str, int] = defaultdict(int)

    try:
        for source_index, source in enumerate(source_rows):
            source_action = str(source.get("external_evidence_v4_action"))
            source_action_counts[source_action] += 1
            if source_action not in {
                "external_evidence_v4_request_identity_confirmation",
                "external_evidence_v4_request_expanded_retrieval",
            }:
                continue
            key = (str(source.get("scene_id")), str(source.get("query")))
            candidates = candidates_by_key.get(key, {})
            if not candidates:
                skipped_rows.append({"source_index": source_index, "skip_reason": "missing_scene_query_candidates", **source})
                continue
            if source_action == "external_evidence_v4_request_identity_confirmation":
                rows, skipped = identity_confirmation_rows(source, candidates, snapper, source_index, args)
            else:
                rows, skipped = expanded_retrieval_rows(source, candidates, source_index, args)
            plan_rows.extend(rows)
            skipped_rows.extend(skipped)
            for row in rows:
                followup_action_counts[str(row.get("followup_action"))] += 1
                reason_counts[str(row.get("followup_reason"))] += 1
                role_counts[str(row.get("followup_role"))] += 1
                viewpoint_source_counts[str(row.get("followup_viewpoint_source"))] += 1
                rows_by_source[str(row.get("external_branch_id"))] += 1
    finally:
        snapper.close()

    write_jsonl(out_root / "external_candidate_followup_observation_plan.jsonl", plan_rows)
    write_jsonl(out_root / "external_candidate_followup_observation_skipped.jsonl", skipped_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "external_evidence_v4_rows": str(args.external_evidence_v4_rows),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "policy": POLICY_NAME,
        "source_rows": len(source_rows),
        "plan_rows": len(plan_rows),
        "skipped_rows": len(skipped_rows),
        "source_action_counts": dict(sorted(source_action_counts.items())),
        "followup_action_counts": dict(sorted(followup_action_counts.items())),
        "followup_reason_counts": dict(sorted(reason_counts.items())),
        "followup_role_counts": dict(sorted(role_counts.items())),
        "viewpoint_source_counts": dict(sorted(viewpoint_source_counts.items())),
        "rows_by_external_branch_id": dict(sorted(rows_by_source.items())),
        "max_identity_targets": int(args.max_identity_targets),
        "max_identity_candidate_ids": int(args.max_identity_candidate_ids),
        "max_expanded_candidates": int(args.max_expanded_candidates),
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "plan_rows": "external_candidate_followup_observation_plan.jsonl",
            "skipped_rows": "external_candidate_followup_observation_skipped.jsonl",
            "summary": "external_candidate_followup_observation_summary.json",
        },
    }
    write_json(out_root / "external_candidate_followup_observation_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan H001 external-candidate follow-up observations after V4 routing.")
    parser.add_argument("--external-evidence-v4-rows", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--run-id", default="h001_external_candidate_followup_observation_v1")
    parser.add_argument("--data-root", default=None)
    parser.add_argument("--max-identity-targets", type=int, default=3)
    parser.add_argument("--max-identity-candidate-ids", type=int, default=6)
    parser.add_argument("--max-expanded-candidates", type=int, default=6)
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
