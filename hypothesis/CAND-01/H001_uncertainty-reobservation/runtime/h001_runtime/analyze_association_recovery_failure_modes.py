import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.association_recovery_failure_modes.v1"


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


def dominant_term(row: Dict[str, Any]) -> str:
    terms = {
        "no_evidence": safe_float(row.get("R_after2_no_evidence")) or 0.0,
        "contradiction": safe_float(row.get("R_after2_contradiction")) or 0.0,
        "ambiguity": safe_float(row.get("R_after2_ambiguity")) or 0.0,
        "property_weakness": safe_float(row.get("R_after2_property_weakness")) or 0.0,
    }
    return max(terms, key=lambda key: terms[key])


def classify(row: Dict[str, Any], high_risk_threshold: float) -> Dict[str, Any]:
    top_supported = bool(row.get("top_positive_support_after_second"))
    top_correct = row.get("top_candidate_correct")
    commit = bool(row.get("commit_after_second_observation"))
    recovered = bool(row.get("association_recovered_after_second"))
    r_no_evidence = safe_float(row.get("R_after2_no_evidence")) or 0.0
    r_contradiction = safe_float(row.get("R_after2_contradiction")) or 0.0
    r_ambiguity = safe_float(row.get("R_after2_ambiguity")) or 0.0
    r_property = safe_float(row.get("R_after2_property_weakness")) or 0.0
    tags: List[str] = []

    if commit and top_correct is False:
        tags.append("unsafe_commit_wrong_top")
    if top_supported and top_correct is False:
        tags.append("recovered_or_supported_wrong_top")
    if top_supported and top_correct is True and not commit:
        tags.append("correct_top_supported_but_deferred")
    if recovered and r_no_evidence >= high_risk_threshold:
        tags.append("recovered_but_no_evidence_remains_high")
    if r_no_evidence >= high_risk_threshold and not top_supported:
        tags.append("persistent_no_evidence")
    if r_ambiguity >= high_risk_threshold:
        tags.append("persistent_ambiguity")
    if r_contradiction >= high_risk_threshold:
        tags.append("persistent_contradiction")
    if r_property >= high_risk_threshold:
        tags.append("persistent_property_weakness")
    if not tags:
        tags.append("low_risk_not_committed_or_uncategorized")

    if "unsafe_commit_wrong_top" in tags:
        primary = "unsafe_commit_wrong_top"
    elif "recovered_or_supported_wrong_top" in tags:
        primary = "recovered_or_supported_wrong_top"
    elif "correct_top_supported_but_deferred" in tags:
        primary = "correct_top_supported_but_deferred"
    elif "persistent_no_evidence" in tags:
        primary = "persistent_no_evidence"
    elif "persistent_ambiguity" in tags:
        primary = "persistent_ambiguity"
    elif "persistent_contradiction" in tags:
        primary = "persistent_contradiction"
    elif "persistent_property_weakness" in tags:
        primary = "persistent_property_weakness"
    else:
        primary = tags[0]

    return {
        "failure_tags": tags,
        "primary_failure_mode": primary,
        "dominant_R_after2_term": dominant_term(row),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    rows = load_jsonl(Path(args.rows))
    classified_rows = []
    primary_counts: Counter[str] = Counter()
    tag_counts: Counter[str] = Counter()
    reason_counts: Dict[str, Counter[str]] = defaultdict(Counter)

    for row in rows:
        labels = classify(row, float(args.high_risk_threshold))
        out = {
            "schema_version": SCHEMA_VERSION,
            "episode_key": row.get("episode_key"),
            "scene_id": row.get("scene_id"),
            "query": row.get("query"),
            "second_observation_reason": row.get("second_observation_reason"),
            "risk_top_candidate_id": row.get("risk_top_candidate_id"),
            "second_observation_candidate_id": row.get("second_observation_candidate_id"),
            "association_recovered_after_second": row.get("association_recovered_after_second"),
            "top_positive_support_after_second": row.get("top_positive_support_after_second"),
            "commit_after_second_observation": row.get("commit_after_second_observation"),
            "top_candidate_correct": row.get("top_candidate_correct"),
            "R_after2": row.get("R_after2"),
            "R_after2_no_evidence": row.get("R_after2_no_evidence"),
            "R_after2_contradiction": row.get("R_after2_contradiction"),
            "R_after2_ambiguity": row.get("R_after2_ambiguity"),
            "R_after2_property_weakness": row.get("R_after2_property_weakness"),
            "uses_gt_for_action": row.get("uses_gt_for_action"),
            "uses_gt_for_analysis": row.get("uses_gt_for_analysis"),
            **labels,
        }
        classified_rows.append(out)
        primary_counts[out["primary_failure_mode"]] += 1
        for tag in out["failure_tags"]:
            tag_counts[tag] += 1
        reason_counts[str(out.get("second_observation_reason"))][out["primary_failure_mode"]] += 1

    out_root = Path(args.out_root)
    write_jsonl(out_root / "association_recovery_failure_modes.jsonl", classified_rows)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "rows": len(classified_rows),
        "source_rows": str(args.rows),
        "high_risk_threshold": float(args.high_risk_threshold),
        "primary_failure_mode_counts": dict(sorted(primary_counts.items())),
        "failure_tag_counts": dict(sorted(tag_counts.items())),
        "primary_failure_by_second_observation_reason": {
            reason: dict(sorted(counts.items()))
            for reason, counts in sorted(reason_counts.items())
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "rows": "association_recovery_failure_modes.jsonl",
            "summary": "association_recovery_failure_mode_summary.json",
        },
    }
    write_json(out_root / "association_recovery_failure_mode_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify H001 association-recovery second-observation failure modes.")
    parser.add_argument("--rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--high-risk-threshold", type=float, default=0.5)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
