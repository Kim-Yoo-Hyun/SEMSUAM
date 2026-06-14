import argparse
import json
import math
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.instance_arbitration_inputs.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_instance_arbitration_evidence_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_instance_arbitration_evidence_v1"
TARGET_BRANCH = "instance_arbitration_defer_v1"
TARGET_ACTION = "defer_instance_arbitration_unresolved"
POLICY_NAME = "InstanceArbitrationPairEvidence"
BUILDER_NAME = "instance_arbitration_inputs_v1"


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def source_path(args: argparse.Namespace, contract: Mapping[str, Any], attr: str, source_key: str) -> Path:
    explicit = getattr(args, attr)
    if explicit:
        return Path(str(explicit))
    source = contract.get("source") or {}
    if source_key not in source:
        raise KeyError(f"contract source is missing {source_key}")
    return Path(str(source[source_key]))


def safe_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        text = str(value).rsplit(":", 1)[-1]
        try:
            return int(text)
        except (TypeError, ValueError):
            return default


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def vector3(value: Any) -> Optional[List[float]]:
    if not isinstance(value, list) or len(value) != 3:
        return None
    values = [safe_float(item) for item in value]
    if any(item is None for item in values):
        return None
    return [float(item) for item in values]


def horizontal_distance(a: Any, b: Any) -> Optional[float]:
    avec = vector3(a)
    bvec = vector3(b)
    if avec is None or bvec is None:
        return None
    return math.hypot(avec[0] - bvec[0], avec[2] - bvec[2])


def request_id(row: Mapping[str, Any]) -> str:
    return str(row.get("expanded_retrieval_request_id") or row.get("rival_identity_request_id") or "")


def candidate_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    return text.rsplit(":", 1)[0], safe_int(text.rsplit(":", 1)[-1], 999999), text


def request_sort_key(value: Any) -> Tuple[str, int, str]:
    text = str(value or "")
    if ":" in text:
        prefix, suffix = text.rsplit(":", 1)
        return prefix, safe_int(suffix, 999999), text
    return text, 999999, text


def unique_ordered(values: Iterable[Any]) -> List[str]:
    output: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        output.append(text)
        seen.add(text)
    return output


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def scan_forbidden_keys(value: Any, prefix: str = "") -> List[str]:
    findings: List[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{prefix}.{key}" if prefix else str(key)
            lowered = str(key).lower()
            if lowered != "uses_gt_for_action" and any(
                term in lowered for term in ("candidate_correct", "correct_candidate", "valid_candidate", "wrong_goal", "evaluation_only", "gt_")
            ):
                findings.append(child_path)
            findings.extend(scan_forbidden_keys(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(scan_forbidden_keys(child, f"{prefix}[{index}]"))
    return findings


def forbidden_findings(rows: Sequence[Mapping[str, Any]]) -> List[str]:
    findings: List[str] = []
    for index, row in enumerate(rows):
        findings.extend([f"row[{index}].{item}" for item in scan_forbidden_keys(dict(row))])
    return findings


def target_route_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    filtered = [
        dict(row)
        for row in rows
        if str(row.get("route_branch")) == TARGET_BRANCH and str(row.get("route_action")) == TARGET_ACTION
    ]
    return sorted(filtered, key=lambda row: request_sort_key(request_id(row)))


def artifact_index(rows: Sequence[Dict[str, Any]]) -> Dict[Tuple[str, str], Dict[str, Any]]:
    indexed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        key = (str(row.get("scene_key") or ""), str(row.get("query") or ""))
        indexed[key] = dict(row)
    return indexed


def candidate_by_id(artifact: Optional[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    output: Dict[str, Dict[str, Any]] = {}
    if not artifact:
        return output
    for candidate in artifact.get("candidates") or []:
        candidate_id = candidate.get("candidate_id")
        if candidate_id is not None:
            output[str(candidate_id)] = dict(candidate)
    return output


def role_tags(summary: Mapping[str, Any], candidate_id: str) -> List[str]:
    tags: List[str] = []
    role_fields = [
        ("source_top", "source_top_candidate_ids"),
        ("strong_own_view", "strong_own_view_candidate_ids"),
        ("detector_strong", "detector_strong_candidate_ids"),
        ("local_context", "local_context_candidate_ids"),
    ]
    for tag, field in role_fields:
        if candidate_id in set(str(value) for value in summary.get(field) or []):
            tags.append(tag)
    return tags or ["unmatched_candidate"]


def make_request_rows(route_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for index, row in enumerate(route_rows):
        summary = row.get("action_candidate_summary") or {}
        candidate_ids = unique_ordered(summary.get("candidate_ids") or [])
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "validation_stage": "action_instance_arbitration_request",
                "policy": POLICY_NAME,
                "builder_name": BUILDER_NAME,
                "request_index": index,
                "episode_key": row.get("episode_key"),
                "scene_id": row.get("scene_id"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "expanded_retrieval_request_id": request_id(row),
                "rival_identity_request_id": row.get("rival_identity_request_id") or request_id(row),
                "source_variant": row.get("source_variant"),
                "source_action": row.get("source_action"),
                "source_reason": row.get("source_reason"),
                "route_branch": row.get("route_branch"),
                "route_action": row.get("route_action"),
                "route_reason": row.get("route_reason"),
                "route_signals": list(row.get("route_signals") or []),
                "candidate_ids": candidate_ids,
                "candidate_count": len(candidate_ids),
                "source_top_candidate_ids": unique_ordered(summary.get("source_top_candidate_ids") or []),
                "strong_own_view_candidate_ids": unique_ordered(summary.get("strong_own_view_candidate_ids") or []),
                "detector_strong_candidate_ids": unique_ordered(summary.get("detector_strong_candidate_ids") or []),
                "local_context_candidate_ids": unique_ordered(summary.get("local_context_candidate_ids") or []),
                "instance_arbitration_action": "materialize_candidate_and_pair_evidence",
                "terminal_commit_allowed": False,
                "candidate_commit_allowed": False,
                "candidate_rejection_allowed": False,
                "terminal_commit": False,
                "uses_gt_for_action": False,
                "paper_claim_allowed": False,
            }
        )
    return output


def make_candidate_row(
    *,
    route: Mapping[str, Any],
    artifact_candidate: Optional[Mapping[str, Any]],
    candidate_id: str,
    request_index: int,
    candidate_index: int,
) -> Dict[str, Any]:
    artifact_candidate = artifact_candidate or {}
    summary = route.get("action_candidate_summary") or {}
    roles = role_tags(summary, candidate_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_stage": "action_instance_arbitration_candidate",
        "policy": POLICY_NAME,
        "builder_name": BUILDER_NAME,
        "request_index": request_index,
        "candidate_index": candidate_index,
        "episode_key": route.get("episode_key"),
        "scene_id": route.get("scene_id"),
        "scene_key": route.get("scene_key"),
        "query": route.get("query"),
        "expanded_retrieval_request_id": request_id(route),
        "rival_identity_request_id": route.get("rival_identity_request_id") or request_id(route),
        "candidate_id": candidate_id,
        "target_candidate_id": candidate_id,
        "candidate_action_roles": roles,
        "source_top_candidate": "source_top" in roles,
        "strong_own_view_candidate": "strong_own_view" in roles,
        "detector_strong_candidate": "detector_strong" in roles,
        "local_context_candidate": "local_context" in roles,
        "artifact_candidate_role": artifact_candidate.get("candidate_role"),
        "candidate_backend": artifact_candidate.get("candidate_backend"),
        "category": artifact_candidate.get("category") or route.get("query"),
        "semantic_rank": artifact_candidate.get("semantic_rank"),
        "semantic_score": artifact_candidate.get("semantic_score"),
        "score": artifact_candidate.get("score"),
        "support_score": artifact_candidate.get("support_score"),
        "detector_evidence_score": artifact_candidate.get("detector_evidence_score"),
        "detector_support_class": artifact_candidate.get("detector_support_class"),
        "local_context_distance_m": artifact_candidate.get("local_context_distance_m"),
        "path_to_candidate": artifact_candidate.get("path_to_candidate"),
        "candidate_reachable": artifact_candidate.get("candidate_reachable"),
        "positive_support": artifact_candidate.get("positive_support"),
        "position": vector3(artifact_candidate.get("position")),
        "visit_position": vector3(artifact_candidate.get("visit_position")) or vector3(artifact_candidate.get("position")),
        "artifact_joined": bool(artifact_candidate),
        "terminal_commit_allowed": False,
        "candidate_commit_allowed": False,
        "candidate_rejection_allowed": False,
        "terminal_commit": False,
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
    }


def make_candidate_rows(
    route_rows: Sequence[Dict[str, Any]],
    artifacts: Mapping[Tuple[str, str], Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    output: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    for request_index, route in enumerate(route_rows):
        key = (str(route.get("scene_key") or ""), str(route.get("query") or ""))
        artifact = artifacts.get(key)
        candidates = candidate_by_id(artifact)
        candidate_ids = unique_ordered((route.get("action_candidate_summary") or {}).get("candidate_ids") or [])
        if artifact is None:
            skipped.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_instance_arbitration_input_skipped",
                    "expanded_retrieval_request_id": request_id(route),
                    "scene_key": route.get("scene_key"),
                    "query": route.get("query"),
                    "skip_reason": "missing_scene_query_candidate_artifact",
                    "uses_gt_for_action": False,
                }
            )
        for candidate_index, cid in enumerate(sorted(candidate_ids, key=candidate_sort_key)):
            artifact_candidate = candidates.get(cid)
            if artifact_candidate is None:
                skipped.append(
                    {
                        "schema_version": SCHEMA_VERSION,
                        "validation_stage": "action_instance_arbitration_input_skipped",
                        "expanded_retrieval_request_id": request_id(route),
                        "scene_key": route.get("scene_key"),
                        "query": route.get("query"),
                        "candidate_id": cid,
                        "skip_reason": "missing_candidate_in_artifact",
                        "uses_gt_for_action": False,
                    }
                )
            output.append(
                make_candidate_row(
                    route=route,
                    artifact_candidate=artifact_candidate,
                    candidate_id=cid,
                    request_index=request_index,
                    candidate_index=candidate_index,
                )
            )
    return output, skipped


def pair_view_role(a: Mapping[str, Any], b: Mapping[str, Any]) -> str:
    roles = set(a.get("candidate_action_roles") or []) | set(b.get("candidate_action_roles") or [])
    if "source_top" in roles:
        return "source_top_contrast_view"
    if "local_context" in roles:
        return "local_context_contrast_view"
    return "pair_common_view_or_dual_standoff"


def make_pair_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_request: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in candidate_rows:
        by_request[request_id(row)].append(row)

    output: List[Dict[str, Any]] = []
    pair_index = 0
    for rid in sorted(by_request.keys(), key=request_sort_key):
        rows = sorted(by_request[rid], key=lambda row: candidate_sort_key(row.get("candidate_id")))
        for request_pair_index, (a, b) in enumerate(combinations(rows, 2)):
            distance = horizontal_distance(a.get("position"), b.get("position"))
            roles_a = list(a.get("candidate_action_roles") or [])
            roles_b = list(b.get("candidate_action_roles") or [])
            output.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "validation_stage": "action_instance_arbitration_pair",
                    "policy": POLICY_NAME,
                    "builder_name": BUILDER_NAME,
                    "pair_index": pair_index,
                    "request_pair_index": request_pair_index,
                    "request_index": a.get("request_index"),
                    "episode_key": a.get("episode_key"),
                    "scene_id": a.get("scene_id"),
                    "scene_key": a.get("scene_key"),
                    "query": a.get("query"),
                    "expanded_retrieval_request_id": rid,
                    "rival_identity_request_id": a.get("rival_identity_request_id") or rid,
                    "candidate_id_a": a.get("candidate_id"),
                    "candidate_id_b": b.get("candidate_id"),
                    "candidate_ids": [a.get("candidate_id"), b.get("candidate_id")],
                    "candidate_a_roles": roles_a,
                    "candidate_b_roles": roles_b,
                    "view_role": pair_view_role(a, b),
                    "pair_distance_m": distance,
                    "candidate_a_position": a.get("position"),
                    "candidate_b_position": b.get("position"),
                    "candidate_a_visit_position": a.get("visit_position"),
                    "candidate_b_visit_position": b.get("visit_position"),
                    "candidate_a_semantic_rank": a.get("semantic_rank"),
                    "candidate_b_semantic_rank": b.get("semantic_rank"),
                    "candidate_a_detector_evidence_score": a.get("detector_evidence_score"),
                    "candidate_b_detector_evidence_score": b.get("detector_evidence_score"),
                    "pair_materialization_rule": "all_unordered_candidates_within_request",
                    "terminal_commit_allowed": False,
                    "candidate_commit_allowed": False,
                    "candidate_rejection_allowed": False,
                    "terminal_commit": False,
                    "uses_gt_for_action": False,
                    "paper_claim_allowed": False,
                }
            )
            pair_index += 1
    return output


def make_candidate_artifact_rows(candidate_rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], Dict[str, Dict[str, Any]]] = defaultdict(dict)
    request_ids: Dict[Tuple[str, str], set[str]] = defaultdict(set)
    scene_ids: Dict[Tuple[str, str], str] = {}
    for row in candidate_rows:
        key = (str(row.get("scene_key") or ""), str(row.get("query") or ""))
        scene_ids[key] = str(row.get("scene_id") or "")
        request_ids[key].add(request_id(row))
        grouped[key][str(row.get("candidate_id"))] = {
            "candidate_id": row.get("candidate_id"),
            "category": row.get("category") or row.get("query"),
            "candidate_role": "+".join(row.get("candidate_action_roles") or []),
            "artifact_candidate_role": row.get("artifact_candidate_role"),
            "position": row.get("position"),
            "visit_position": row.get("visit_position"),
            "score": row.get("score"),
            "semantic_rank": row.get("semantic_rank"),
            "semantic_score": row.get("semantic_score"),
            "support_score": row.get("support_score"),
            "detector_evidence_score": row.get("detector_evidence_score"),
            "detector_support_class": row.get("detector_support_class"),
            "local_context_distance_m": row.get("local_context_distance_m"),
            "path_to_candidate": row.get("path_to_candidate"),
            "candidate_reachable": row.get("candidate_reachable"),
            "positive_support": row.get("positive_support"),
            "source": "instance_arbitration_input_materializer",
            "uses_gt_for_action": False,
        }
    output: List[Dict[str, Any]] = []
    for key in sorted(grouped.keys()):
        scene_key, query = key
        candidates = sorted(grouped[key].values(), key=lambda row: candidate_sort_key(row.get("candidate_id")))
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "artifact_type": "instance_arbitration_candidate_artifact",
                "scene_id": scene_ids[key],
                "scene_key": scene_key,
                "query": query,
                "expanded_retrieval_request_ids": sorted(request_ids[key], key=request_sort_key),
                "candidate_count": len(candidates),
                "candidates": candidates,
                "uses_gt_for_action": False,
            }
        )
    return output


def build_summary(
    *,
    args: argparse.Namespace,
    contract: Mapping[str, Any],
    selection_summary: Mapping[str, Any],
    route_rows: Sequence[Dict[str, Any]],
    request_rows: Sequence[Dict[str, Any]],
    candidate_rows: Sequence[Dict[str, Any]],
    pair_rows: Sequence[Dict[str, Any]],
    artifact_rows: Sequence[Dict[str, Any]],
    skipped_rows: Sequence[Dict[str, Any]],
) -> Dict[str, Any]:
    all_action_rows: List[Mapping[str, Any]] = [*request_rows, *candidate_rows, *pair_rows, *artifact_rows, *skipped_rows]
    forbidden = forbidden_findings(all_action_rows)
    gates = contract.get("evaluation_gates") or {}
    scope = contract.get("target_scope") or {}
    expected_scene_queries = set(str(value) for value in scope.get("target_scene_queries") or [])
    artifact_scene_queries = {f"{row.get('scene_key')}:{row.get('query')}" for row in artifact_rows}
    role_counts = Counter(role for row in candidate_rows for role in row.get("candidate_action_roles") or [])
    terminal_rows = [
        row
        for row in all_action_rows
        if row.get("terminal_commit") is True
        or row.get("terminal_commit_allowed") is True
        or row.get("candidate_commit_allowed") is True
        or row.get("candidate_rejection_allowed") is True
    ]
    gate = {
        "source_selection_gate_passed": bool((selection_summary.get("gate") or {}).get("next_label_free_evidence_family_after_object_relation_gate_passed")),
        "selected_family_passed": selection_summary.get("selected_family") == TARGET_BRANCH,
        "selected_action_passed": selection_summary.get("selected_action") == "freeze_instance_arbitration_label_free_evidence_contract",
        "route_contract_gate_passed": bool((selection_summary.get("gate") or {}).get("route_contract_gate_passed")),
        "expected_request_rows_passed": len(request_rows) == safe_int(gates.get("expected_request_rows")),
        "expected_candidate_rows_passed": len(candidate_rows) == safe_int(gates.get("expected_candidate_rows")),
        "expected_pair_rows_passed": len(pair_rows) == safe_int(gates.get("expected_pair_rows")),
        "expected_artifact_scene_query_rows_passed": len(artifact_rows) == safe_int(gates.get("expected_artifact_scene_query_rows")),
        "candidate_artifact_covers_all_target_scene_queries": expected_scene_queries.issubset(artifact_scene_queries),
        "source_top_candidate_refs_passed": role_counts.get("source_top", 0) == safe_int(scope.get("expected_source_top_candidate_refs")),
        "strong_own_view_candidate_refs_passed": role_counts.get("strong_own_view", 0) == safe_int(scope.get("expected_strong_own_view_candidate_refs")),
        "detector_strong_candidate_refs_passed": role_counts.get("detector_strong", 0) == safe_int(scope.get("expected_detector_strong_candidate_refs")),
        "local_context_candidate_refs_passed": role_counts.get("local_context", 0) == safe_int(scope.get("expected_local_context_candidate_refs")),
        "candidate_positions_available_passed": all(row.get("position") and row.get("visit_position") for row in candidate_rows),
        "skipped_rows_passed": len(skipped_rows) == 0,
        "action_evidence_forbidden_key_gate_passed": len(forbidden) <= safe_int(gates.get("action_evidence_forbidden_key_count_maximum")),
        "terminal_commit_rows_passed": len(terminal_rows) <= safe_int(gates.get("terminal_commit_rows_maximum")),
        "candidate_commit_rows_passed": 0 <= safe_int(gates.get("candidate_commit_rows_maximum")),
        "candidate_rejection_rows_passed": 0 <= safe_int(gates.get("candidate_rejection_rows_maximum")),
        "uses_gt_for_action": False,
        "uses_gt_for_action_passed": all(row.get("uses_gt_for_action") is False for row in all_action_rows),
        "paper_claim_allowed": False,
    }
    gate["instance_arbitration_input_gate_passed"] = all(
        value is True for key, value in gate.items() if key not in {"uses_gt_for_action", "paper_claim_allowed"}
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "out_root": str(args.out_root),
        "input_files": {
            "selection_summary": str(args.selection_summary),
            "route_specific_rows": str(args.route_specific_rows),
            "candidate_artifact": str(args.candidate_artifact),
        },
        "source_route_rows": len(route_rows),
        "request_rows": len(request_rows),
        "candidate_rows": len(candidate_rows),
        "pair_rows": len(pair_rows),
        "artifact_rows": len(artifact_rows),
        "skipped_rows": len(skipped_rows),
        "scene_count": len({str(row.get("scene_key")) for row in request_rows}),
        "query_count": len({str(row.get("query")) for row in request_rows}),
        "request_candidate_counts": dict(sorted(Counter(request_id(row) for row in candidate_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "request_pair_counts": dict(sorted(Counter(request_id(row) for row in pair_rows).items(), key=lambda item: request_sort_key(item[0]))),
        "candidate_role_counts": dict(sorted(role_counts.items())),
        "pair_view_role_counts": compact_counter(row.get("view_role") for row in pair_rows),
        "query_counts": compact_counter(row.get("query") for row in request_rows),
        "scene_counts": compact_counter(row.get("scene_key") for row in request_rows),
        "artifact_scene_queries": sorted(artifact_scene_queries),
        "action_evidence_forbidden_key_count": len(forbidden),
        "action_evidence_forbidden_keys": forbidden[:50],
        "terminal_commit_rows": len(terminal_rows),
        "candidate_commit_rows": 0,
        "candidate_rejection_rows": 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "terminal_utility_validation_allowed": False,
        "paper_claim_allowed": False,
        "gate": gate,
        "output_files": {
            "request_rows": "instance_arbitration_request_rows.jsonl",
            "candidate_rows": "instance_arbitration_candidate_rows.jsonl",
            "pair_rows": "instance_arbitration_pair_rows.jsonl",
            "candidate_artifact_rows": "instance_arbitration_candidate_artifact_rows.jsonl",
            "skipped_rows": "instance_arbitration_skipped_rows.jsonl",
            "input_summary": "instance_arbitration_input_summary.json",
        },
        "interpretation": {
            "fact": "The materializer writes request, candidate, pair, and target candidate-artifact rows before any evaluation-label join.",
            "agent_inference": "Passing this gate means instance-arbitration evidence is ready for nonterminal observation planning, not terminal ObjectNav utility.",
            "paper_claim": "No paper claim is allowed from this input materialization result.",
        },
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    contract = load_json(Path(args.contract))
    args.selection_summary = source_path(args, contract, "selection_summary", "selection_summary")
    args.route_specific_rows = source_path(args, contract, "route_specific_rows", "route_specific_rows")
    args.candidate_artifact = source_path(args, contract, "candidate_artifact", "candidate_artifact")

    selection_summary = load_json(args.selection_summary)
    route_rows_all = load_jsonl(args.route_specific_rows)
    artifact_rows_all = load_jsonl(args.candidate_artifact)
    route_rows = target_route_rows(route_rows_all)
    artifacts = artifact_index(artifact_rows_all)

    request_rows = make_request_rows(route_rows)
    candidate_rows, skipped_rows = make_candidate_rows(route_rows, artifacts)
    pair_rows = make_pair_rows(candidate_rows)
    candidate_artifact_rows = make_candidate_artifact_rows(candidate_rows)
    summary = build_summary(
        args=args,
        contract=contract,
        selection_summary=selection_summary,
        route_rows=route_rows,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        pair_rows=pair_rows,
        artifact_rows=candidate_artifact_rows,
        skipped_rows=skipped_rows,
    )

    out_root = Path(args.out_root)
    write_jsonl(out_root / "instance_arbitration_request_rows.jsonl", request_rows)
    write_jsonl(out_root / "instance_arbitration_candidate_rows.jsonl", candidate_rows)
    write_jsonl(out_root / "instance_arbitration_pair_rows.jsonl", pair_rows)
    write_jsonl(out_root / "instance_arbitration_candidate_artifact_rows.jsonl", candidate_artifact_rows)
    write_jsonl(out_root / "instance_arbitration_skipped_rows.jsonl", skipped_rows)
    write_json(out_root / "instance_arbitration_input_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build label-free instance-arbitration request/candidate/pair rows.")
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--selection-summary")
    parser.add_argument("--route-specific-rows")
    parser.add_argument("--candidate-artifact")
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not summary["gate"]["instance_arbitration_input_gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
