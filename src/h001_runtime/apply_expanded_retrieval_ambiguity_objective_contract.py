import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


SCHEMA_VERSION = "h001.expanded_retrieval_ambiguity_objective_application.v1"


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


def ratio(numerator: int, denominator: int) -> float:
    return 0.0 if denominator == 0 else numerator / denominator


def route_index(contract: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {str(rule["evidence_topology"]): rule for rule in contract.get("route_rules", [])}


def request_key(row: Dict[str, Any]) -> Tuple[str, str, str]:
    return (str(row.get("rival_identity_request_id")), str(row.get("episode_key")), str(row.get("query")))


def apply_contract(
    contract: Dict[str, Any],
    diagnostic_summary: Dict[str, Any],
    request_rows: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    routes = route_index(contract)
    output_rows: List[Dict[str, Any]] = []
    for row in request_rows:
        topology = str(row.get("evidence_topology"))
        rule = routes.get(topology)
        if rule is None:
            action = "contract_route_missing"
            reason = "evidence_topology_not_covered_by_contract"
            required_next_evidence: List[str] = []
            terminal_commit_allowed = False
        else:
            action = str(rule.get("objective_action"))
            reason = str(rule.get("objective_reason"))
            required_next_evidence = list(rule.get("required_next_evidence") or [])
            terminal_commit_allowed = bool(rule.get("terminal_commit_allowed"))

        output_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "contract_name": contract.get("contract_name"),
                "source_diagnostic_schema": diagnostic_summary.get("schema_version"),
                "rival_identity_request_id": row.get("rival_identity_request_id"),
                "episode_key": row.get("episode_key"),
                "scene_key": row.get("scene_key"),
                "query": row.get("query"),
                "candidate_count": row.get("candidate_count"),
                "associated_candidate_count": row.get("associated_candidate_count"),
                "strong_candidate_count": row.get("strong_candidate_count"),
                "source_top_strong": row.get("source_top_strong"),
                "source_top_associated": row.get("source_top_associated"),
                "lower_rank_only_association": row.get("lower_rank_only_association"),
                "best_evidence_candidate_id": row.get("best_evidence_candidate_id"),
                "best_evidence_rank": row.get("best_evidence_rank"),
                "best_evidence_score": row.get("best_evidence_score"),
                "best_evidence_positive_support": row.get("best_evidence_positive_support"),
                "evidence_topology": topology,
                "terminal_objective_risk": row.get("terminal_objective_risk"),
                "objective_action": action,
                "objective_reason": reason,
                "required_next_evidence": required_next_evidence,
                "terminal_commit_allowed": terminal_commit_allowed,
                "paper_claim_allowed": False,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": False,
            }
        )
    return output_rows


def summarize(
    contract: Dict[str, Any],
    diagnostic_summary: Dict[str, Any],
    output_rows: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    covered_rows = [row for row in output_rows if row["objective_action"] != "contract_route_missing"]
    terminal_commit_rows = [row for row in output_rows if row.get("terminal_commit_allowed") is True]
    action_counts = Counter(str(row.get("objective_action")) for row in output_rows)
    topology_counts = Counter(str(row.get("evidence_topology")) for row in output_rows)
    risk_counts = Counter(str(row.get("terminal_objective_risk")) for row in output_rows)
    missing_routes = sorted({row["evidence_topology"] for row in output_rows if row["objective_action"] == "contract_route_missing"})
    route_coverage = ratio(len(covered_rows), len(output_rows))
    diagnostic_gate = contract.get("diagnostic_gate", {})
    min_rows = int(diagnostic_gate.get("min_request_rows", 1))
    required_coverage = float(diagnostic_gate.get("required_route_coverage", 1.0))
    no_gt_action = not any(row.get("uses_gt_for_action") is True for row in output_rows)
    no_gt_analysis = not any(row.get("uses_gt_for_analysis") is True for row in output_rows)
    contract_gate_passed = bool(
        len(output_rows) >= min_rows
        and route_coverage >= required_coverage
        and len(terminal_commit_rows) == int(diagnostic_gate.get("terminal_commit_rows", 0))
        and no_gt_action
        and no_gt_analysis
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "contract": str(args.contract),
        "diagnostic_summary": str(args.diagnostic_summary),
        "diagnostic_request_rows": str(args.diagnostic_request_rows),
        "contract_name": contract.get("contract_name"),
        "source_diagnostic_request_rows": diagnostic_summary.get("request_rows"),
        "source_diagnostic_topology_counts": diagnostic_summary.get("evidence_topology_counts"),
        "request_rows": len(output_rows),
        "route_coverage": route_coverage,
        "missing_route_topologies": missing_routes,
        "objective_action_counts": dict(sorted(action_counts.items())),
        "evidence_topology_counts": dict(sorted(topology_counts.items())),
        "terminal_objective_risk_counts": dict(sorted(risk_counts.items())),
        "terminal_commit_rows": len(terminal_commit_rows),
        "gate": {
            "contract_gate_passed": contract_gate_passed,
            "min_request_rows": min_rows,
            "required_route_coverage": required_coverage,
            "route_coverage_pass": route_coverage >= required_coverage,
            "terminal_commit_rows_pass": len(terminal_commit_rows) == int(diagnostic_gate.get("terminal_commit_rows", 0)),
            "no_gt_action_pass": no_gt_action,
            "no_gt_analysis_pass": no_gt_analysis,
            "larger_source_allowed_after_contract": contract_gate_passed,
            "terminal_objective_allowed": False,
            "paper_claim_allowed": False,
        },
        "interpretation": {
            "facts": [
                "This application reads diagnostic request rows and a frozen JSON contract.",
                "It produces only nonterminal objective actions.",
                "It does not consume correctness labels or ObjectNav evaluation labels."
            ],
            "agent_inference": [
                "The contract can be used to freeze a larger source, but it is not a terminal utility proof.",
                "Multi-strong and lower-rank detector evidence must be treated as ambiguity needing more evidence."
            ],
            "user_decision_needed": []
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
        "paper_claim_allowed": False,
        "output_files": {
            "rows": "expanded_retrieval_ambiguity_objective_rows.jsonl",
            "summary": "expanded_retrieval_ambiguity_objective_summary.json"
        }
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    contract = load_json(Path(args.contract))
    diagnostic_summary = load_json(Path(args.diagnostic_summary))
    request_rows = load_jsonl(Path(args.diagnostic_request_rows))
    output_rows = apply_contract(contract, diagnostic_summary, request_rows)
    summary = summarize(contract, diagnostic_summary, output_rows, args)
    summary["out_root"] = str(out_root)
    write_jsonl(out_root / "expanded_retrieval_ambiguity_objective_rows.jsonl", output_rows)
    write_json(out_root / "expanded_retrieval_ambiguity_objective_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply the H001 expanded-retrieval ambiguity-aware objective contract to detector evidence diagnostics."
    )
    parser.add_argument("--contract", required=True)
    parser.add_argument("--diagnostic-summary", required=True)
    parser.add_argument("--diagnostic-request-rows", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
