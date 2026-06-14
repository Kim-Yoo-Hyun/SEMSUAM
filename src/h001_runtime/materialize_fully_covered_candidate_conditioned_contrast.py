import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence


SCHEMA_VERSION = "h001.fully_covered_candidate_conditioned_contrast.v1"
CONTRACT_DEFAULT = (
    "configs/h001/manifests/"
    "h001_fully_covered_candidate_conditioned_contrast_v1.json"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_fully_covered_candidate_conditioned_contrast_v1"

OUTPUT_FILES = {
    "pair_contrast_rows": "fully_covered_candidate_conditioned_contrast_pair_rows.jsonl",
    "candidate_contrast_rows": "fully_covered_candidate_conditioned_contrast_candidate_rows.jsonl",
    "candidate_role_contrast_rows": "fully_covered_candidate_conditioned_contrast_candidate_role_rows.jsonl",
    "alternative_audit_rows": "fully_covered_candidate_conditioned_contrast_alternative_audit_rows.jsonl",
    "summary": "fully_covered_candidate_conditioned_contrast_summary.json",
}

FORBIDDEN_ACTION_KEYS = {
    "candidate_correct",
    "candidate_correctness_label",
    "candidate_pair_label_pattern_for_evaluation_only",
    "candidate_wrong_label",
    "correct_candidate",
    "evaluation_only",
    "gt_action",
    "gt_candidate",
    "gt_goal",
    "gt_instance_id",
    "gt_label",
    "gt_object_id",
    "ground_truth",
    "map_pose_consistency_delta",
    "oracle_object_id",
    "oracle_shortest_path",
    "success_label",
    "valid_candidate",
    "wasted_path_m",
    "wrong_goal",
    "wrong_goal_visit",
}

ROLE_NAMES = [
    "candidate_a_goal_region_context_view",
    "candidate_b_goal_region_context_view",
    "candidate_pair_object_relation_context_view",
    "shared_goal_region_anchor_view",
]
GOAL_REGION_ROLES = {
    "candidate_a": "candidate_a_goal_region_context_view",
    "candidate_b": "candidate_b_goal_region_context_view",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def resolve_path(path_like: str) -> Path:
    path = Path(path_like)
    if path.exists():
        return path
    if path_like.startswith("local_dataset/runs/"):
        runs_path = Path("/runs") / path_like.removeprefix("local_dataset/runs/")
        if runs_path.exists():
            return runs_path
    workspace_path = Path("/workspace") / path
    if workspace_path.exists():
        return workspace_path
    return path


def path_from_contract(contract: Mapping[str, Any], key: str) -> Path:
    source = contract.get("source_artifacts") or contract.get("source") or {}
    if key not in source:
        raise KeyError(f"missing source path: {key}")
    return resolve_path(str(source[key]))


def compact_counter(values: Iterable[Any]) -> dict[str, int]:
    counter = Counter(str(value) for value in values if value is not None and str(value) != "")
    return dict(sorted(counter.items()))


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def scan_forbidden_action_inputs(rows: Sequence[Mapping[str, Any]]) -> list[str]:
    found: set[str] = set()

    def scan(value: Any) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                if str(key) in FORBIDDEN_ACTION_KEYS:
                    found.add(str(key))
                scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)

    for row in rows:
        scan(row.get("action_evidence_inputs", {}))
        scan(row.get("action_route_inputs", {}))
    return sorted(found)


def common_flags(uses_gt_for_analysis: bool = False) -> dict[str, Any]:
    return {
        "terminal_commit": False,
        "candidate_commit": False,
        "candidate_rejection": False,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": uses_gt_for_analysis,
        "paper_claim_allowed": False,
    }


def contrast_pair_ids(contract: Mapping[str, Any]) -> list[str]:
    source_gate = contract.get("source_gate") or {}
    wrong = (source_gate.get("wrong_contrast_row") or {}).get("coverage_completion_pair_id")
    correct = (source_gate.get("correct_contrast_row") or {}).get("coverage_completion_pair_id")
    pair_ids = [str(value) for value in [wrong, correct] if value]
    if len(pair_ids) != 2:
        raise ValueError(f"expected two contrast pair ids, got {pair_ids}")
    return pair_ids


def role_state(row: Mapping[str, Any], role: str) -> str:
    states = row.get("coverage_completion_candidate_view_states_by_role") or {}
    return str(states.get(role) or "")


def candidate_label(row: Mapping[str, Any]) -> str:
    if row.get("candidate_correctness_label_for_evaluation_only") is True:
        return "correct"
    if row.get("candidate_wrong_label_for_evaluation_only") is True:
        return "wrong"
    return "unknown"


def candidate_role(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_pair_role") or "")


def is_goal_region_role(role: str) -> bool:
    return role in set(GOAL_REGION_ROLES.values())


def build_candidate_role_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for candidate in sorted(
        candidate_rows,
        key=lambda row: (
            str(row.get("coverage_completion_pair_id")),
            str(row.get("candidate_pair_role")),
            str(row.get("candidate_id")),
        ),
    ):
        c_role = candidate_role(candidate)
        own_goal_role = GOAL_REGION_ROLES.get(c_role)
        peer_goal_role = next((value for key, value in GOAL_REGION_ROLES.items() if key != c_role), None)
        for role in ROLE_NAMES:
            state = role_state(candidate, role)
            visible_without_association = state == "visible_without_candidate_association"
            mixed_depth_support = state == "associated_depth_mixed"
            associated_depth_consistent = state == "associated_depth_consistent"
            rule_positive = visible_without_association and is_goal_region_role(role)
            role_blocker = (
                "visible_without_depth_association_in_goal_region_context"
                if rule_positive
                else "mixed_depth_support_not_blocker"
                if mixed_depth_support
                else "none"
            )
            output.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "row_type": "fully_covered_candidate_conditioned_contrast_candidate_role",
                    "validation_stage": "fully_covered_candidate_conditioned_contrast_after_contract_freeze",
                    "scene_key": candidate.get("scene_key"),
                    "query": candidate.get("query"),
                    "episode_key": candidate.get("episode_key"),
                    "source_name": candidate.get("source_name"),
                    "request_id": candidate.get("request_id"),
                    "coverage_completion_pair_id": candidate.get("coverage_completion_pair_id"),
                    "candidate_id": candidate.get("candidate_id"),
                    "candidate_pair_role": c_role,
                    "role": role,
                    "candidate_view_evidence_state": state,
                    "is_goal_region_context_role": is_goal_region_role(role),
                    "is_own_goal_region_context": role == own_goal_role,
                    "is_peer_goal_region_context": role == peer_goal_role,
                    "visible_without_candidate_association": visible_without_association,
                    "mixed_depth_support": mixed_depth_support,
                    "associated_depth_consistent": associated_depth_consistent,
                    "candidate_conditioned_role_blocker": role_blocker,
                    "rule_positive_role": rule_positive,
                    "candidate_label_for_audit_only": candidate_label(candidate),
                    "evaluation_only_label_is_action_forbidden": True,
                    "terminal_selector_allowed_from_this_contrast": False,
                    **common_flags(uses_gt_for_analysis=True),
                }
            )
    return output


def build_candidate_rows(
    source_candidates: Sequence[Mapping[str, Any]],
    role_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for candidate in sorted(
        source_candidates,
        key=lambda row: (
            str(row.get("coverage_completion_pair_id")),
            str(row.get("candidate_pair_role")),
            str(row.get("candidate_id")),
        ),
    ):
        cid = str(candidate.get("candidate_id"))
        pair_id = str(candidate.get("coverage_completion_pair_id"))
        roles = [
            row
            for row in role_rows
            if str(row.get("candidate_id")) == cid
            and str(row.get("coverage_completion_pair_id")) == pair_id
        ]
        visible_roles = [
            str(row.get("role"))
            for row in roles
            if row.get("candidate_conditioned_role_blocker")
            == "visible_without_depth_association_in_goal_region_context"
        ]
        mixed_roles = [str(row.get("role")) for row in roles if row.get("mixed_depth_support") is True]
        consistent_roles = [
            str(row.get("role")) for row in roles if row.get("associated_depth_consistent") is True
        ]
        label = candidate_label(candidate)
        rule_blocker_triggered = len(visible_roles) > 0
        mixed_depth_without_visible_gap = bool(mixed_roles) and not rule_blocker_triggered
        if rule_blocker_triggered and label == "wrong":
            contrast_state = "blocked_wrong_candidate_for_audit_only"
        elif rule_blocker_triggered and label == "correct":
            contrast_state = "false_positive_blocker_on_correct_candidate_for_audit_only"
        elif len(consistent_roles) == len(ROLE_NAMES):
            contrast_state = "clean_all_role_support_candidate"
        elif mixed_depth_without_visible_gap:
            contrast_state = "mixed_depth_support_but_no_visible_gap"
        else:
            contrast_state = "unblocked_candidate"
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "fully_covered_candidate_conditioned_contrast_candidate",
                "validation_stage": "fully_covered_candidate_conditioned_contrast_after_contract_freeze",
                "scene_key": candidate.get("scene_key"),
                "query": candidate.get("query"),
                "episode_key": candidate.get("episode_key"),
                "source_name": candidate.get("source_name"),
                "request_id": candidate.get("request_id"),
                "coverage_completion_pair_id": pair_id,
                "candidate_id": cid,
                "candidate_pair_role": candidate.get("candidate_pair_role"),
                "coverage_completion_pair_evidence_state": candidate.get(
                    "coverage_completion_pair_evidence_state"
                ),
                "candidate_view_rows": int(candidate.get("coverage_completion_candidate_view_rows") or 0),
                "associated_rows": int(candidate.get("coverage_completion_associated_rows") or 0),
                "depth_consistent_rows": int(candidate.get("coverage_completion_depth_consistent_rows") or 0),
                "consistent_role_count": len(consistent_roles),
                "consistent_roles": consistent_roles,
                "mixed_depth_role_count": len(mixed_roles),
                "mixed_depth_roles": mixed_roles,
                "visible_without_association_goal_region_role_count": len(visible_roles),
                "visible_without_association_goal_region_roles": visible_roles,
                "candidate_conditioned_blocker": (
                    "visible_without_depth_association_in_goal_region_context"
                    if rule_blocker_triggered
                    else "none"
                ),
                "rule_blocker_triggered": rule_blocker_triggered,
                "mixed_depth_support_without_visible_gap": mixed_depth_without_visible_gap,
                "all_role_strict_associated": len(consistent_roles) == len(ROLE_NAMES),
                "all_role_nonmissing_support": all(
                    role_state(candidate, role) in {"associated_depth_consistent", "associated_depth_mixed"}
                    for role in ROLE_NAMES
                ),
                "candidate_contrast_state": contrast_state,
                "candidate_label_for_audit_only": label,
                "true_positive_blocker_for_audit_only": rule_blocker_triggered and label == "wrong",
                "false_positive_blocker_for_audit_only": rule_blocker_triggered and label == "correct",
                "evaluation_only_label_is_action_forbidden": True,
                "terminal_selector_allowed_from_this_contrast": False,
                **common_flags(uses_gt_for_analysis=True),
            }
        )
    return output


def pair_label(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_pair_label_pattern_for_evaluation_only") or "unknown")


def build_pair_rows(
    detector_pair_rows: Sequence[Mapping[str, Any]],
    eval_pair_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    eval_by_pair = {str(row.get("coverage_completion_pair_id")): row for row in eval_pair_rows}
    for detector_pair in sorted(detector_pair_rows, key=lambda row: str(row.get("coverage_completion_pair_id"))):
        pair_id = str(detector_pair.get("coverage_completion_pair_id"))
        eval_pair = eval_by_pair[pair_id]
        candidates = [row for row in candidate_rows if str(row.get("coverage_completion_pair_id")) == pair_id]
        blocker_candidates = [row for row in candidates if row.get("rule_blocker_triggered") is True]
        false_positive_candidates = [
            row for row in blocker_candidates if row.get("false_positive_blocker_for_audit_only") is True
        ]
        true_positive_candidates = [
            row for row in blocker_candidates if row.get("true_positive_blocker_for_audit_only") is True
        ]
        label = pair_label(eval_pair)
        if label == "a_wrong_b_correct" and true_positive_candidates and not false_positive_candidates:
            contrast_state = "wrong_pair_blocker_matches_audit_only"
        elif label == "both_correct" and not false_positive_candidates and not blocker_candidates:
            contrast_state = "correct_pair_no_false_positive"
        else:
            contrast_state = "contrast_rule_requires_revision"
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "fully_covered_candidate_conditioned_contrast_pair",
                "validation_stage": "fully_covered_candidate_conditioned_contrast_after_contract_freeze",
                "scene_key": detector_pair.get("scene_key"),
                "query": detector_pair.get("query"),
                "episode_key": detector_pair.get("episode_key"),
                "source_name": detector_pair.get("source_name"),
                "request_id": detector_pair.get("request_id"),
                "coverage_completion_pair_id": pair_id,
                "candidate_a_id": detector_pair.get("candidate_a_id"),
                "candidate_b_id": detector_pair.get("candidate_b_id"),
                "pair_evidence_state": detector_pair.get("pair_evidence_state"),
                "role_evidence_states": detector_pair.get("role_evidence_states"),
                "candidate_pair_label_for_audit_only": label,
                "evaluation_only_label_is_action_forbidden": True,
                "blocker_candidate_ids": [row.get("candidate_id") for row in blocker_candidates],
                "true_positive_blocker_candidate_ids_for_audit_only": [
                    row.get("candidate_id") for row in true_positive_candidates
                ],
                "false_positive_blocker_candidate_ids_for_audit_only": [
                    row.get("candidate_id") for row in false_positive_candidates
                ],
                "candidate_conditioned_contrast_state": contrast_state,
                "binary_coverage_completion_too_coarse": True,
                "terminal_arbitration_rule_ready": False,
                "terminal_selector_allowed_from_this_contrast": False,
                **common_flags(uses_gt_for_analysis=True),
            }
        )
    return output


def unique_best(rows: Sequence[Mapping[str, Any]], metric: str) -> tuple[Optional[str], str]:
    values: list[tuple[str, float]] = []
    for row in rows:
        value = safe_float(row.get(metric))
        if value is not None:
            values.append((str(row.get("candidate_id")), value))
    if not values:
        return None, "no_value"
    best = max(value for _, value in values)
    winners = [cid for cid, value in values if value == best]
    if len(winners) != 1:
        return None, "tie"
    return winners[0], "unique"


def candidate_by_id(rows: Sequence[Mapping[str, Any]], candidate_id: Optional[str]) -> Optional[Mapping[str, Any]]:
    if candidate_id is None:
        return None
    for row in rows:
        if str(row.get("candidate_id")) == candidate_id:
            return row
    return None


def audit_label_for_candidate(rows: Sequence[Mapping[str, Any]], candidate_id: Optional[str]) -> str:
    row = candidate_by_id(rows, candidate_id)
    if row is None:
        return "none"
    return str(row.get("candidate_label_for_audit_only") or "unknown")


def alternative_row(
    *,
    name: str,
    decision: str,
    reason: str,
    selected_candidate_ids: Sequence[str] | None = None,
    selected_candidate_labels: Sequence[str] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "row_type": "fully_covered_candidate_conditioned_contrast_alternative_audit",
        "validation_stage": "fully_covered_candidate_conditioned_contrast_after_contract_freeze",
        "alternative_name": name,
        "decision": decision,
        "reason": reason,
        "selected_candidate_ids_for_audit_only": list(selected_candidate_ids or []),
        "selected_candidate_labels_for_audit_only": list(selected_candidate_labels or []),
        "evaluation_only_label_is_action_forbidden": True,
        "terminal_selector_allowed_from_this_contrast": False,
        **common_flags(uses_gt_for_analysis=True),
    }
    if extra:
        payload.update(dict(extra))
    return payload


def build_alternative_rows(candidate_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[str, list[Mapping[str, Any]]] = {}
    for row in candidate_rows:
        by_pair.setdefault(str(row.get("coverage_completion_pair_id")), []).append(row)

    assoc_selected: list[str] = []
    assoc_statuses: dict[str, str] = {}
    depth_selected: list[str] = []
    depth_statuses: dict[str, str] = {}
    strict_all_role_selected: list[str] = []
    for pair_id, rows in sorted(by_pair.items()):
        assoc_best, assoc_status = unique_best(rows, "associated_rows")
        depth_best, depth_status = unique_best(rows, "depth_consistent_rows")
        assoc_statuses[pair_id] = assoc_status
        depth_statuses[pair_id] = depth_status
        if assoc_best:
            assoc_selected.append(assoc_best)
        if depth_best:
            depth_selected.append(depth_best)
        strict_all_role_selected.extend(
            str(row.get("candidate_id")) for row in rows if row.get("all_role_strict_associated") is True
        )

    visible_blocker_rows = [row for row in candidate_rows if row.get("rule_blocker_triggered") is True]
    mixed_depth_rows = [row for row in candidate_rows if row.get("mixed_depth_role_count", 0) > 0]
    false_positive_visible_rows = [
        row for row in visible_blocker_rows if row.get("false_positive_blocker_for_audit_only") is True
    ]
    true_positive_visible_rows = [
        row for row in visible_blocker_rows if row.get("true_positive_blocker_for_audit_only") is True
    ]
    mixed_depth_false_positives = [
        row for row in mixed_depth_rows if row.get("candidate_label_for_audit_only") == "correct"
    ]

    assoc_labels = [audit_label_for_candidate(candidate_rows, cid) for cid in assoc_selected]
    depth_labels = [audit_label_for_candidate(candidate_rows, cid) for cid in depth_selected]
    strict_labels = [audit_label_for_candidate(candidate_rows, cid) for cid in strict_all_role_selected]
    visible_labels = [str(row.get("candidate_label_for_audit_only")) for row in visible_blocker_rows]
    mixed_labels = [str(row.get("candidate_label_for_audit_only")) for row in mixed_depth_rows]

    return [
        alternative_row(
            name="binary_coverage_completion_as_terminal_support",
            decision="rejected_as_terminal_rule",
            reason="two fully covered pairs have different audit-only labels, so binary coverage is not goal validity",
            extra={"pair_label_patterns_for_audit_only": {"a_wrong_b_correct": 1, "both_correct": 1}},
        ),
        alternative_row(
            name="association_count_best",
            decision="rejected_as_terminal_rule",
            selected_candidate_ids=assoc_selected,
            selected_candidate_labels=assoc_labels,
            reason="association count is tied on the wrong fully covered pair and cannot define a fixed terminal selector",
            extra={"selector_status_by_pair": assoc_statuses},
        ),
        alternative_row(
            name="depth_consistency_count_best",
            decision="rejected_as_terminal_rule",
            selected_candidate_ids=depth_selected,
            selected_candidate_labels=depth_labels,
            reason="depth-consistency count selects the wrong candidate on the wrong fully covered pair",
            extra={"selector_status_by_pair": depth_statuses},
        ),
        alternative_row(
            name="candidate_conditioned_visible_without_depth_association_blocker",
            decision="diagnostic_only_contrast_pass_not_terminal_rule",
            selected_candidate_ids=[str(row.get("candidate_id")) for row in visible_blocker_rows],
            selected_candidate_labels=visible_labels,
            reason="the blocker flags the wrong fully covered candidate and has no false positive on the fully covered correct row, but scope is still two pairs",
            extra={
                "true_positive_blocker_rows_for_audit_only": len(true_positive_visible_rows),
                "false_positive_blocker_rows_for_audit_only": len(false_positive_visible_rows),
            },
        ),
        alternative_row(
            name="mixed_depth_support_as_blocker",
            decision="rejected_as_terminal_rule",
            selected_candidate_ids=[str(row.get("candidate_id")) for row in mixed_depth_rows],
            selected_candidate_labels=mixed_labels,
            reason="mixed depth support appears on correct fully covered candidates and must not be treated as the same blocker",
            extra={"false_positive_correct_candidate_rows_for_audit_only": len(mixed_depth_false_positives)},
        ),
        alternative_row(
            name="strict_all_role_association_required",
            decision="safe_but_inert",
            selected_candidate_ids=strict_all_role_selected,
            selected_candidate_labels=strict_labels,
            reason="strict all-role support avoids this wrong row but over-defers the fully covered correct contrast row with mixed depth support",
        ),
        alternative_row(
            name="defer_all_fully_covered_pairs",
            decision="safe_but_inert",
            reason="defer-all avoids wrong commits but does not explain which evidence term should drive active utility",
        ),
    ]


def materialize(contract_path: Path, out_root: Path) -> dict[str, Any]:
    contract = load_json(contract_path)
    pair_ids = set(contrast_pair_ids(contract))
    expected = contract.get("expected_outputs") or {}

    detector_pair_rows = [
        row
        for row in load_jsonl(path_from_contract(contract, "detector_pair_rows"))
        if str(row.get("coverage_completion_pair_id")) in pair_ids
    ]
    eval_pair_rows = [
        row
        for row in load_jsonl(path_from_contract(contract, "evaluation_pair_rows"))
        if str(row.get("coverage_completion_pair_id")) in pair_ids
    ]
    eval_candidate_rows = [
        row
        for row in load_jsonl(path_from_contract(contract, "evaluation_candidate_rows"))
        if str(row.get("coverage_completion_pair_id")) in pair_ids
    ]
    asymmetry_summary = load_json(path_from_contract(contract, "asymmetry_inspection_summary"))

    candidate_role_rows = build_candidate_role_rows(eval_candidate_rows)
    candidate_rows = build_candidate_rows(eval_candidate_rows, candidate_role_rows)
    pair_rows = build_pair_rows(detector_pair_rows, eval_pair_rows, candidate_rows)
    alternative_rows = build_alternative_rows(candidate_rows)

    action_rows = pair_rows + candidate_rows + candidate_role_rows + alternative_rows
    forbidden_keys = scan_forbidden_action_inputs(action_rows)
    terminal_commit_rows = sum(1 for row in action_rows if row.get("terminal_commit") is True)
    candidate_commit_rows = sum(1 for row in action_rows if row.get("candidate_commit") is True)
    candidate_rejection_rows = sum(1 for row in action_rows if row.get("candidate_rejection") is True)
    uses_gt_for_action_true_rows = sum(1 for row in action_rows if row.get("uses_gt_for_action") is True)
    paper_claim_allowed_true_rows = sum(1 for row in action_rows if row.get("paper_claim_allowed") is True)

    wrong_pair_states = [
        row.get("candidate_conditioned_contrast_state")
        for row in pair_rows
        if row.get("candidate_pair_label_for_audit_only") == "a_wrong_b_correct"
    ]
    correct_pair_states = [
        row.get("candidate_conditioned_contrast_state")
        for row in pair_rows
        if row.get("candidate_pair_label_for_audit_only") == "both_correct"
    ]
    visible_blocker_rows = [row for row in candidate_rows if row.get("rule_blocker_triggered") is True]
    visible_false_positive_rows = [
        row for row in visible_blocker_rows if row.get("false_positive_blocker_for_audit_only") is True
    ]
    mixed_correct_rows = [
        row
        for row in candidate_rows
        if row.get("mixed_depth_role_count", 0) > 0 and row.get("candidate_label_for_audit_only") == "correct"
    ]
    mixed_positive_rows = [
        row
        for row in candidate_rows
        if row.get("mixed_depth_role_count", 0) > 0 and row.get("rule_blocker_triggered") is True
    ]

    gate = {
        "pair_contrast_rows_match": len(pair_rows) == int(expected.get("pair_contrast_rows", -1)),
        "candidate_contrast_rows_match": len(candidate_rows) == int(expected.get("candidate_contrast_rows", -1)),
        "candidate_role_contrast_rows_match": len(candidate_role_rows)
        == int(expected.get("candidate_role_contrast_rows", -1)),
        "alternative_audit_rows_min_pass": len(alternative_rows)
        >= int(expected.get("alternative_audit_rows_min", 0)),
        "wrong_contrast_blocker_present": "wrong_pair_blocker_matches_audit_only" in wrong_pair_states,
        "correct_contrast_false_positive_absent": "correct_pair_no_false_positive" in correct_pair_states
        and len(visible_false_positive_rows) == 0,
        "mixed_depth_support_not_equated_with_blocker": len(mixed_correct_rows) > 0
        and len(mixed_positive_rows) == 0,
        "terminal_rule_not_promoted": True,
        "forbidden_action_keys_absent": forbidden_keys == [],
        "no_terminal_commit_pass": terminal_commit_rows == int(expected.get("terminal_commit_rows", -1)),
        "no_candidate_commit_pass": candidate_commit_rows == int(expected.get("candidate_commit_rows", -1)),
        "no_candidate_rejection_pass": candidate_rejection_rows == int(expected.get("candidate_rejection_rows", -1)),
        "no_gt_action_pass": uses_gt_for_action_true_rows
        == int(expected.get("uses_gt_for_action_true_rows", -1)),
        "paper_claim_blocked_pass": paper_claim_allowed_true_rows
        == int(expected.get("paper_claim_allowed_true_rows", -1)),
        "prior_asymmetry_gate_consumed": asymmetry_summary.get("asymmetry_inspection_gate_passed") is True,
    }
    gate["contrast_materializer_gate_passed"] = all(gate.values())

    write_jsonl(out_root / OUTPUT_FILES["pair_contrast_rows"], pair_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_contrast_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_role_contrast_rows"], candidate_role_rows)
    write_jsonl(out_root / OUTPUT_FILES["alternative_audit_rows"], alternative_rows)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "status": "completed",
        "contract": str(contract_path),
        "source_detector_pair_rows": len(detector_pair_rows),
        "source_evaluation_pair_rows": len(eval_pair_rows),
        "source_evaluation_candidate_rows": len(eval_candidate_rows),
        "source_prior_asymmetry_gate_passed": asymmetry_summary.get("asymmetry_inspection_gate_passed"),
        "pair_contrast_rows": len(pair_rows),
        "candidate_contrast_rows": len(candidate_rows),
        "candidate_role_contrast_rows": len(candidate_role_rows),
        "alternative_audit_rows": len(alternative_rows),
        "pair_label_counts_for_audit_only": compact_counter(
            row.get("candidate_pair_label_for_audit_only") for row in pair_rows
        ),
        "candidate_label_counts_for_audit_only": compact_counter(
            row.get("candidate_label_for_audit_only") for row in candidate_rows
        ),
        "candidate_contrast_state_counts": compact_counter(
            row.get("candidate_contrast_state") for row in candidate_rows
        ),
        "pair_contrast_state_counts": compact_counter(
            row.get("candidate_conditioned_contrast_state") for row in pair_rows
        ),
        "candidate_conditioned_blocker_counts": compact_counter(
            row.get("candidate_conditioned_blocker") for row in candidate_rows
        ),
        "rule_blocker_candidate_ids": [row.get("candidate_id") for row in visible_blocker_rows],
        "true_positive_blocker_rows_for_audit_only": sum(
            1 for row in visible_blocker_rows if row.get("true_positive_blocker_for_audit_only") is True
        ),
        "false_positive_blocker_rows_for_audit_only": len(visible_false_positive_rows),
        "mixed_depth_correct_candidate_rows_for_audit_only": len(mixed_correct_rows),
        "mixed_depth_positive_blocker_rows": len(mixed_positive_rows),
        "alternative_decision_counts": compact_counter(row.get("decision") for row in alternative_rows),
        "action_evidence_forbidden_keys_found": forbidden_keys,
        "terminal_commit_rows": terminal_commit_rows,
        "candidate_commit_rows": candidate_commit_rows,
        "candidate_rejection_rows": candidate_rejection_rows,
        "uses_gt_for_action_true_rows": uses_gt_for_action_true_rows,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed_true_rows": paper_claim_allowed_true_rows,
        "gate": gate,
        "contrast_materializer_gate_passed": gate["contrast_materializer_gate_passed"],
        "fixed_blocker_survives_fully_covered_contrast": gate["wrong_contrast_blocker_present"]
        and gate["correct_contrast_false_positive_absent"]
        and gate["mixed_depth_support_not_equated_with_blocker"],
        "terminal_arbitration_rule_ready": False,
        "promotion_gate_after_contrast_passed": False,
        "paper_claim_allowed_after_contrast": False,
        "primary_blocker": "multi_case_candidate_conditioned_blocker_validation_required",
        "next_task": "freeze_candidate_conditioned_blocker_multi_case_validation_contract",
    }
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", default=CONTRACT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    args = parser.parse_args()

    summary = materialize(resolve_path(args.contract), Path(args.out_root))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
