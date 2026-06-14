import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


SCHEMA_VERSION = "h001.semantic_slam_active_observation_risk_analysis.v1"
INPUT_ROOT_DEFAULT = (
    "local_dataset/runs/"
    "h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1"
)
OUT_ROOT_DEFAULT = "local_dataset/runs/h001_semantic_slam_active_observation_risk_analysis_v1"
VERIFY_DEFAULT = (
    "configs/h001/manifests/"
    "h001_semantic_slam_active_observation_risk_analysis_v1.verify.json"
)

REQUEST_FILE = "semantic_slam_candidate_relative_active_observation_task_proxy_request_rows.jsonl"
PRIORITY_FILE = "semantic_slam_candidate_relative_active_observation_task_proxy_priority_rows.jsonl"
BASELINE_FILE = "semantic_slam_candidate_relative_active_observation_task_proxy_baseline_rows.jsonl"
JOIN_SUMMARY_FILE = "semantic_slam_candidate_relative_active_observation_task_proxy_summary.json"

OUTPUT_FILES = {
    "request_rows": "active_observation_risk_request_rows.jsonl",
    "candidate_rows": "active_observation_risk_candidate_rows.jsonl",
    "rule_audit_rows": "active_observation_terminal_shortcut_audit_rows.jsonl",
    "summary": "active_observation_risk_analysis_summary.json",
}

REQUEST_KEYS = ("source_name", "scene_key", "query", "request_id", "episode_key")


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
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


def safe_float(value: Any, default: Optional[float] = None) -> Optional[float]:
    try:
        if value is None:
            return default
        result = float(value)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(result):
        return default
    return result


def safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def ratio(numerator: float, denominator: float) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    rows = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not rows:
        return None
    return sum(rows) / len(rows)


def compact_counter(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values if value is not None and str(value) != "").items()))


def auroc(scores: Sequence[float], labels: Sequence[int]) -> Optional[float]:
    positives = [score for score, label in zip(scores, labels) if label == 1]
    negatives = [score for score, label in zip(scores, labels) if label == 0]
    if not positives or not negatives:
        return None
    wins = 0.0
    total = len(positives) * len(negatives)
    for pos in positives:
        for neg in negatives:
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / total


def request_key(row: Mapping[str, Any]) -> Tuple[str, str, str, str, str]:
    join_key = row.get("join_key")
    source = join_key if isinstance(join_key, Mapping) else row
    return (
        str(source.get("source_name") or row.get("source_name") or ""),
        str(source.get("scene_key") or row.get("scene_key") or ""),
        str(source.get("query") or row.get("query") or ""),
        str(source.get("request_id") or row.get("request_id") or ""),
        str(source.get("episode_key") or row.get("episode_key") or ""),
    )


def request_payload(key: Tuple[str, str, str, str, str]) -> Dict[str, str]:
    return dict(zip(REQUEST_KEYS, key))


def candidate_id(row: Mapping[str, Any]) -> str:
    return str(row.get("candidate_id") or "")


def candidate_result(row: Mapping[str, Any]) -> str:
    if row.get("no_valid_candidate_pool") is True:
        return "no_valid_pool"
    if row.get("candidate_correctness_label") is True:
        return "success_if_committed"
    if row.get("candidate_wrong_label") is True:
        return "wrong_goal_if_committed"
    return "unlabeled_if_committed"


def request_selected_status(row: Mapping[str, Any]) -> str:
    counts = row.get("selected_candidate_label_counts")
    counts = counts if isinstance(counts, Mapping) else {}
    selected = safe_int(counts.get("selected_candidate_rows"), 0)
    correct = safe_int(counts.get("correct_rows"), 0)
    wrong = safe_int(counts.get("wrong_rows"), 0)
    missing = safe_int(counts.get("label_missing_rows"), 0)
    no_valid = counts.get("no_valid_request_pool") is True
    if missing > 0:
        return "selected_label_missing"
    if no_valid:
        return "selected_in_no_valid_pool"
    if selected > 0 and correct == selected:
        return "selected_all_correct"
    if correct > 0 and wrong > 0:
        return "selected_mixed_correct_wrong"
    if selected > 0 and wrong == selected:
        return "selected_all_wrong"
    if selected > 0 and correct == 0 and wrong == 0:
        return "selected_unlabeled"
    return "selected_other"


def by_request(rows: Sequence[Mapping[str, Any]]) -> Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]]:
    grouped: Dict[Tuple[str, str, str, str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[request_key(row)].append(row)
    return dict(grouped)


def top_by_utility(rows: Sequence[Mapping[str, Any]]) -> Optional[Mapping[str, Any]]:
    if not rows:
        return None
    return max(rows, key=lambda row: safe_float(row.get("utility_score"), -1e9) or -1e9)


def build_candidate_rows(priority_rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    output: List[Dict[str, Any]] = []
    for row in priority_rows:
        key = request_key(row)
        result = candidate_result(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "active_observation_risk_candidate",
                "validation_stage": "evaluation_only_risk_analysis_after_active_observation_action_freeze",
                "join_key": {**request_payload(key), "candidate_id": candidate_id(row)},
                **request_payload(key),
                "candidate_id": candidate_id(row),
                "selected_for_request_action": bool(row.get("selected_for_request_action") is True),
                "selected_observation_action": row.get("selected_observation_action"),
                "observation_action": row.get("observation_action"),
                "utility_score": safe_float(row.get("utility_score")),
                "utility_terms": row.get("utility_terms"),
                "risk_tags": row.get("risk_tags"),
                "separability_status": row.get("separability_status"),
                "separability_tag": row.get("separability_tag"),
                "candidate_correctness_label": row.get("candidate_correctness_label"),
                "candidate_wrong_label": row.get("candidate_wrong_label"),
                "no_valid_candidate_pool": row.get("no_valid_candidate_pool"),
                "candidate_result_if_misused_as_terminal": result,
                "terminal_selector_training_allowed": False,
                "terminal_commit_allowed": False,
                "evaluation_only_task_proxy_analysis": True,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return output


def build_request_rows(
    request_rows: Sequence[Mapping[str, Any]],
    priority_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    priority_by_request = by_request(priority_rows)
    output: List[Dict[str, Any]] = []
    for row in request_rows:
        key = request_key(row)
        candidates = priority_by_request.get(key, [])
        selected_candidates = [candidate for candidate in candidates if candidate.get("selected_for_request_action") is True]
        top_candidate = top_by_utility(candidates)
        top_selected_candidate = top_by_utility(selected_candidates)
        counts = row.get("selected_candidate_label_counts")
        counts = counts if isinstance(counts, Mapping) else {}
        selected_wrong_or_no_valid = safe_int(counts.get("wrong_or_no_valid_risk_rows"), 0)
        selected_status = request_selected_status(row)
        output.append(
            {
                "schema_version": SCHEMA_VERSION,
                "row_type": "active_observation_risk_request",
                "validation_stage": "evaluation_only_risk_analysis_after_active_observation_action_freeze",
                "join_key": request_payload(key),
                **request_payload(key),
                "selected_observation_action": row.get("selected_observation_action"),
                "selected_candidate_count": safe_int(row.get("selected_candidate_count"), 0),
                "selected_candidate_ids": row.get("selected_candidate_ids"),
                "selected_candidate_label_counts": counts,
                "selected_candidate_status": selected_status,
                "selected_has_wrong_or_no_valid_risk": selected_wrong_or_no_valid > 0,
                "selected_all_correct": selected_status == "selected_all_correct",
                "selected_mixed_correct_wrong": selected_status == "selected_mixed_correct_wrong",
                "selected_no_valid_pool": selected_status == "selected_in_no_valid_pool",
                "request_risk_tags": row.get("request_risk_tags"),
                "separability_status": row.get("separability_status"),
                "top_observation_utility_candidate_id": candidate_id(top_candidate or {}),
                "top_observation_utility_score": safe_float((top_candidate or {}).get("utility_score")),
                "top_observation_utility_terminal_result": candidate_result(top_candidate or {}),
                "top_selected_candidate_id": candidate_id(top_selected_candidate or {}),
                "top_selected_utility_score": safe_float((top_selected_candidate or {}).get("utility_score")),
                "top_selected_utility_terminal_result": candidate_result(top_selected_candidate or {}),
                "terminal_shortcut_safe": False,
                "terminal_shortcut_status": "blocked_by_evaluation_only_risk_analysis",
                "terminal_commit_allowed": False,
                "evaluation_only_task_proxy_analysis": True,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": True,
                "paper_claim_allowed": False,
            }
        )
    return output


def summarize_terminal_rule(
    *,
    rule_name: str,
    rows: Sequence[Mapping[str, Any]],
    result_key: str,
    terminal_rows: Optional[int] = None,
    baseline: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    if baseline:
        rows_count = safe_int(baseline.get("rows"), 0)
        commits = safe_int(baseline.get("terminal_commit_proxy_rows"), 0)
        success = safe_int(baseline.get("success_commit_proxy_rows"), 0)
        wrong = safe_int(baseline.get("wrong_goal_visit_proxy_rows"), 0)
        no_valid = safe_int(baseline.get("no_valid_commit_proxy_rows"), 0)
        return {
            "schema_version": SCHEMA_VERSION,
            "row_type": "active_observation_terminal_shortcut_audit",
            "rule_name": rule_name,
            "rule_family": "baseline_context",
            "rows": rows_count,
            "terminal_rows": commits,
            "success_rows": success,
            "wrong_goal_rows": wrong,
            "no_valid_rows": no_valid,
            "defer_rows": rows_count - commits,
            "success_rate_over_rows": ratio(success, rows_count),
            "wrong_goal_rate_over_rows": ratio(wrong, rows_count),
            "terminal_utility_contract_allowed": False,
            "rule_status": "baseline_context_only",
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
            "paper_claim_allowed": False,
        }
    counts = compact_counter(row.get(result_key) for row in rows)
    total_rows = len(rows)
    terminal = terminal_rows if terminal_rows is not None else total_rows
    success = safe_int(counts.get("success_if_committed"), 0)
    wrong = safe_int(counts.get("wrong_goal_if_committed"), 0)
    no_valid = safe_int(counts.get("no_valid_pool"), 0)
    unlabeled = safe_int(counts.get("unlabeled_if_committed"), 0)
    safe = wrong == 0 and no_valid == 0 and unlabeled == 0 and success > 0
    inert = terminal == 0 or success == 0
    status = "unsafe_wrong_or_no_valid" if wrong or no_valid else "safe_but_inert" if inert else "safe_nontrivial"
    return {
        "schema_version": SCHEMA_VERSION,
        "row_type": "active_observation_terminal_shortcut_audit",
        "rule_name": rule_name,
        "rule_family": "active_observation_risk_analysis",
        "rows": total_rows,
        "terminal_rows": terminal,
        "success_rows": success,
        "wrong_goal_rows": wrong,
        "no_valid_rows": no_valid,
        "unlabeled_rows": unlabeled,
        "defer_rows": total_rows - terminal,
        "success_rate_over_rows": ratio(success, total_rows),
        "wrong_goal_rate_over_rows": ratio(wrong, total_rows),
        "terminal_utility_contract_allowed": False,
        "rule_status": status,
        "rule_safe": safe,
        "rule_nontrivial": success > 0,
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "paper_claim_allowed": False,
    }


def build_rule_audit_rows(
    request_analysis_rows: Sequence[Mapping[str, Any]],
    baseline_counts: Mapping[str, Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    rows = [
        summarize_terminal_rule(
            rule_name="top_observation_utility_if_misused_as_terminal",
            rows=request_analysis_rows,
            result_key="top_observation_utility_terminal_result",
        ),
        summarize_terminal_rule(
            rule_name="top_selected_observation_utility_if_misused_as_terminal",
            rows=request_analysis_rows,
            result_key="top_selected_utility_terminal_result",
        ),
        {
            "schema_version": SCHEMA_VERSION,
            "row_type": "active_observation_terminal_shortcut_audit",
            "rule_name": "defer_all_after_risk_detection",
            "rule_family": "safety_lower_bound",
            "rows": len(request_analysis_rows),
            "terminal_rows": 0,
            "success_rows": 0,
            "wrong_goal_rows": 0,
            "no_valid_rows": 0,
            "defer_rows": len(request_analysis_rows),
            "success_rate_over_rows": 0.0,
            "wrong_goal_rate_over_rows": 0.0,
            "terminal_utility_contract_allowed": False,
            "rule_status": "safe_but_inert",
            "rule_safe": True,
            "rule_nontrivial": False,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": True,
            "paper_claim_allowed": False,
        },
    ]
    for policy_name, policy_counts in sorted(baseline_counts.items()):
        rows.append(
            summarize_terminal_rule(
                rule_name=str(policy_name),
                rows=[],
                result_key="",
                baseline=policy_counts,
            )
        )
    return rows


def candidate_group_summary(rows: Sequence[Mapping[str, Any]], *, selected: Optional[bool] = None) -> Dict[str, Any]:
    subset = [
        row
        for row in rows
        if selected is None or row.get("selected_for_request_action") is selected
    ]
    risk_rows = [
        row
        for row in subset
        if row.get("candidate_wrong_label") is True or row.get("no_valid_candidate_pool") is True
    ]
    clean_correct = [
        row
        for row in subset
        if row.get("candidate_correctness_label") is True and row.get("no_valid_candidate_pool") is not True
    ]
    risk_scores = [safe_float(row.get("utility_score")) for row in risk_rows]
    clean_scores = [safe_float(row.get("utility_score")) for row in clean_correct]
    return {
        "rows": len(subset),
        "selected_rows": sum(1 for row in subset if row.get("selected_for_request_action") is True),
        "clean_correct_rows": len(clean_correct),
        "wrong_rows": sum(1 for row in subset if row.get("candidate_wrong_label") is True),
        "no_valid_pool_rows": sum(1 for row in subset if row.get("no_valid_candidate_pool") is True),
        "wrong_or_no_valid_rows": len(risk_rows),
        "clean_correct_rate": ratio(len(clean_correct), len(subset)),
        "wrong_or_no_valid_rate": ratio(len(risk_rows), len(subset)),
        "mean_utility_clean_correct": mean(clean_scores),
        "mean_utility_wrong_or_no_valid": mean(risk_scores),
    }


def request_profile_summary(rows: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "rows": len(rows),
        "selected_status_counts": compact_counter(row.get("selected_candidate_status") for row in rows),
        "selected_has_wrong_or_no_valid_rows": sum(
            1 for row in rows if row.get("selected_has_wrong_or_no_valid_risk") is True
        ),
        "selected_all_correct_rows": sum(1 for row in rows if row.get("selected_all_correct") is True),
        "selected_mixed_correct_wrong_rows": sum(1 for row in rows if row.get("selected_mixed_correct_wrong") is True),
        "selected_no_valid_pool_rows": sum(1 for row in rows if row.get("selected_no_valid_pool") is True),
        "selected_action_counts": compact_counter(row.get("selected_observation_action") for row in rows),
        "top_observation_terminal_result_counts": compact_counter(
            row.get("top_observation_utility_terminal_result") for row in rows
        ),
        "top_selected_terminal_result_counts": compact_counter(
            row.get("top_selected_utility_terminal_result") for row in rows
        ),
    }


def utility_risk_auc(candidate_rows: Sequence[Mapping[str, Any]]) -> Optional[float]:
    scored = [
        row
        for row in candidate_rows
        if safe_float(row.get("utility_score")) is not None
        and isinstance(row.get("candidate_wrong_label"), bool)
    ]
    if not scored:
        return None
    scores = [safe_float(row.get("utility_score"), 0.0) or 0.0 for row in scored]
    labels = [
        1 if row.get("candidate_wrong_label") is True or row.get("no_valid_candidate_pool") is True else 0
        for row in scored
    ]
    return auroc(scores, labels)


def build_summary(
    *,
    input_root: Path,
    out_root: Path,
    join_summary: Mapping[str, Any],
    request_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    rule_rows: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    top_rule = next(row for row in rule_rows if row.get("rule_name") == "top_observation_utility_if_misused_as_terminal")
    top_selected_rule = next(
        row for row in rule_rows if row.get("rule_name") == "top_selected_observation_utility_if_misused_as_terminal"
    )
    terminal_shortcut_unsafe = (
        safe_int(top_rule.get("wrong_goal_rows"), 0) > 0
        or safe_int(top_rule.get("no_valid_rows"), 0) > 0
        or safe_int(top_selected_rule.get("wrong_goal_rows"), 0) > 0
        or safe_int(top_selected_rule.get("no_valid_rows"), 0) > 0
    )
    selected_summary = candidate_group_summary(candidate_rows, selected=True)
    unselected_summary = candidate_group_summary(candidate_rows, selected=False)
    all_summary = candidate_group_summary(candidate_rows)
    gate = {
        "source_join_gate_passed": join_summary.get("active_observation_task_proxy_join_gate_passed") is True,
        "source_promotion_gate_blocked_passed": join_summary.get("promotion_gate_after_join_passed") is False,
        "label_coverage_complete_passed": safe_int(
            (join_summary.get("actual_counts") or {}).get("request_label_missing_rows"), -1
        )
        == 0
        and safe_int((join_summary.get("actual_counts") or {}).get("selected_candidate_label_missing_rows"), -1)
        == 0,
        "action_evidence_forbidden_keys_passed": safe_int(
            (join_summary.get("actual_counts") or {}).get("action_evidence_forbidden_key_count"), -1
        )
        == 0,
        "terminal_shortcut_rejected_passed": terminal_shortcut_unsafe,
        "terminal_commit_rows_passed": safe_int((join_summary.get("actual_counts") or {}).get("terminal_commit_rows"), -1)
        == 0,
        "uses_gt_for_action_passed": safe_int(
            (join_summary.get("actual_counts") or {}).get("uses_gt_for_action_true_rows"), -1
        )
        == 0,
        "paper_claim_blocked_passed": safe_int(
            (join_summary.get("actual_counts") or {}).get("paper_claim_allowed_true_rows"), -1
        )
        == 0,
    }
    gate["risk_analysis_gate_passed"] = all(gate.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "date_checked": "2026-06-06",
        "status": "risk_analysis_gate_passed_terminal_utility_blocked"
        if gate["risk_analysis_gate_passed"]
        else "risk_analysis_gate_failed",
        "input_root": str(input_root),
        "out_root": str(out_root),
        "output_files": OUTPUT_FILES,
        "source_summary": str(input_root / JOIN_SUMMARY_FILE),
        "actual_counts": {
            "request_analysis_rows": len(request_rows),
            "candidate_analysis_rows": len(candidate_rows),
            "rule_audit_rows": len(rule_rows),
            "terminal_commit_rows": 0,
            "candidate_commit_rows": 0,
            "candidate_rejection_rows": 0,
            "uses_gt_for_action_true_rows": 0,
            "paper_claim_allowed_true_rows": 0,
        },
        "request_risk_profile": request_profile_summary(request_rows),
        "candidate_risk_profile": {
            "all_priority_candidates": all_summary,
            "selected_candidates": selected_summary,
            "unselected_candidates": unselected_summary,
            "selected_minus_unselected_wrong_or_no_valid_rate": (
                selected_summary["wrong_or_no_valid_rate"] - unselected_summary["wrong_or_no_valid_rate"]
            ),
        },
        "utility_score_risk_auc": utility_risk_auc(candidate_rows),
        "terminal_shortcut_audit": {
            "top_observation_utility_if_misused_as_terminal": top_rule,
            "top_selected_observation_utility_if_misused_as_terminal": top_selected_rule,
        },
        "risk_analysis_gate": gate,
        "risk_analysis_gate_passed": gate["risk_analysis_gate_passed"],
        "terminal_utility_contract_allowed": False,
        "terminal_utility_validation_allowed": False,
        "formula_revision_allowed": False,
        "first_eval_rerun_allowed": False,
        "policy_scale_comparison_allowed": False,
        "step_4_5_promotion_allowed": False,
        "paper_claim_allowed": False,
        "primary_blocker": "top_observation_utility_terminal_shortcut_unsafe",
        "recommended_next_task": "freeze_active_observation_post_observation_evidence_update_contract",
        "next_task": "freeze_active_observation_post_observation_evidence_update_contract",
        "interpretation": {
            "fact": (
                "The selected active-observation candidates are joined to complete evaluation-only labels, "
                "and terminal shortcut audits over the frozen utility produce wrong-goal/no-valid outcomes."
            ),
            "agent_inference": (
                "The active-observation utility is useful as a risk acquisition signal, but it is not a valid "
                "terminal selector. The next method step should define a label-free post-observation evidence update "
                "contract before any terminal utility or formula revision."
            ),
            "paper_claim": (
                "No ObjectNav utility, Semantic-SLAM complementarity, terminal utility, Step 4-5 promotion, "
                "first_eval rerun, policy-scale comparison, or paper claim is allowed from this analysis."
            ),
        },
    }


def build_verify_payload(summary: Mapping[str, Any], verify_path: Path) -> Dict[str, Any]:
    return {
        "schema_version": f"{SCHEMA_VERSION}.verify",
        "date_checked": "2026-06-06",
        "status": summary.get("status"),
        "summary": str(Path(str(summary["out_root"])) / OUTPUT_FILES["summary"]),
        "verify_path": str(verify_path),
        "risk_analysis_gate_passed": summary.get("risk_analysis_gate_passed"),
        "terminal_utility_contract_allowed": summary.get("terminal_utility_contract_allowed"),
        "primary_blocker": summary.get("primary_blocker"),
        "actual_counts": summary.get("actual_counts"),
        "docker_compile_command": (
            "docker run --rm --ipc=host --user $(id -u):$(id -g) "
            "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
            "-e PYTHONPATH=/workspace/src "
            "-v /home/yoohyun/research3:/workspace -w /workspace "
            "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
            "python -m py_compile "
            "src/h001_runtime/"
            "analyze_semantic_slam_active_observation_risk.py"
        ),
        "docker_run_command": (
            "docker run --rm --ipc=host --user $(id -u):$(id -g) "
            "-e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPYCACHEPREFIX=/tmp/pycache "
            "-e PYTHONPATH=/workspace/src "
            "-v /home/yoohyun/research3:/workspace -w /workspace "
            "research3/openvocab-perception:20260513-v3c-gdino-sam2 "
            "python -m h001_runtime.analyze_semantic_slam_active_observation_risk"
        ),
        "verification_command": (
            "jq '.risk_analysis_gate_passed, .terminal_utility_contract_allowed, .primary_blocker, "
            ".terminal_shortcut_audit' "
            f"{Path(str(summary['out_root'])) / OUTPUT_FILES['summary']}"
        ),
    }


def run(input_root: Path, out_root: Path, verify_path: Path) -> Dict[str, Any]:
    join_summary = load_json(input_root / JOIN_SUMMARY_FILE)
    source_request_rows = load_jsonl(input_root / REQUEST_FILE)
    source_priority_rows = load_jsonl(input_root / PRIORITY_FILE)
    request_rows = build_request_rows(source_request_rows, source_priority_rows)
    candidate_rows = build_candidate_rows(source_priority_rows)
    baseline_counts = join_summary.get("baseline_policy_counts")
    baseline_counts = baseline_counts if isinstance(baseline_counts, Mapping) else {}
    rule_rows = build_rule_audit_rows(request_rows, baseline_counts)
    summary = build_summary(
        input_root=input_root,
        out_root=out_root,
        join_summary=join_summary,
        request_rows=request_rows,
        candidate_rows=candidate_rows,
        rule_rows=rule_rows,
    )
    write_jsonl(out_root / OUTPUT_FILES["request_rows"], request_rows)
    write_jsonl(out_root / OUTPUT_FILES["candidate_rows"], candidate_rows)
    write_jsonl(out_root / OUTPUT_FILES["rule_audit_rows"], rule_rows)
    write_json(out_root / OUTPUT_FILES["summary"], summary)
    write_json(verify_path, build_verify_payload(summary, verify_path))
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze frozen active-observation task-proxy join risk before terminal utility."
    )
    parser.add_argument("--input-root", default=INPUT_ROOT_DEFAULT)
    parser.add_argument("--out-root", default=OUT_ROOT_DEFAULT)
    parser.add_argument("--verify", default=VERIFY_DEFAULT)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(Path(args.input_root), Path(args.out_root), Path(args.verify))
    print(json.dumps(summary["actual_counts"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
