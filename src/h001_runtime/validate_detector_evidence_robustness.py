import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.detector_evidence_robustness.v1"


def load_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def scene_short_id(scene_id: Any) -> str:
    stem = Path(str(scene_id)).stem
    return stem.replace(".basis", "")


def init_bucket() -> Dict[str, int]:
    return {
        "rows": 0,
        "baseline_correct": 0,
        "selected_correct": 0,
        "selected_delta_count": 0,
        "wrong_goal_fixes": 0,
        "new_wrong_goals": 0,
        "switches": 0,
    }


def add_decision(bucket: Dict[str, int], row: Dict[str, Any]) -> None:
    baseline_correct = row.get("baseline_candidate_correct") is True
    selected_correct = row.get("selected_candidate_correct") is True
    bucket["rows"] += 1
    bucket["baseline_correct"] += int(baseline_correct)
    bucket["selected_correct"] += int(selected_correct)
    bucket["selected_delta_count"] += int(selected_correct) - int(baseline_correct)
    bucket["wrong_goal_fixes"] += int(row.get("fixes_wrong_goal") is True)
    bucket["new_wrong_goals"] += int(row.get("creates_wrong_goal") is True)
    bucket["switches"] += int(row.get("switched") is True)


def finalize_bucket(key: str, bucket: Dict[str, int]) -> Dict[str, Any]:
    rows = bucket["rows"]
    return {
        "key": key,
        **bucket,
        "baseline_correct_rate": ratio(bucket["baseline_correct"], rows),
        "selected_correct_rate": ratio(bucket["selected_correct"], rows),
        "selected_delta_rate": ratio(bucket["selected_delta_count"], rows),
        "switch_rate": ratio(bucket["switches"], rows),
    }


def summarize(decisions: List[Dict[str, Any]], independent_split: bool) -> Dict[str, Any]:
    overall = init_bucket()
    by_scene: Dict[str, Dict[str, int]] = defaultdict(init_bucket)
    by_query: Dict[str, Dict[str, int]] = defaultdict(init_bucket)
    by_query_scene: Dict[str, Dict[str, int]] = defaultdict(init_bucket)

    for row in decisions:
        scene = scene_short_id(row.get("scene_id"))
        query = str(row.get("query"))
        add_decision(overall, row)
        add_decision(by_scene[scene], row)
        add_decision(by_query[query], row)
        add_decision(by_query_scene[f"{query}/{scene}"], row)

    scene_rows = [finalize_bucket(key, value) for key, value in sorted(by_scene.items())]
    query_rows = [finalize_bucket(key, value) for key, value in sorted(by_query.items())]
    query_scene_rows = [finalize_bucket(key, value) for key, value in sorted(by_query_scene.items())]

    positive_scene_count = sum(row["selected_delta_count"] > 0 for row in scene_rows)
    negative_scene_count = sum(row["selected_delta_count"] < 0 for row in scene_rows)
    switch_scene_count = sum(row["switches"] > 0 for row in scene_rows)
    positive_query_scene_count = {
        row["key"].split("/", 1)[0]: 0 for row in query_scene_rows
    }
    switched_query_scene_count = {
        row["key"].split("/", 1)[0]: 0 for row in query_scene_rows
    }
    for row in query_scene_rows:
        query = row["key"].split("/", 1)[0]
        positive_query_scene_count[query] += int(row["selected_delta_count"] > 0)
        switched_query_scene_count[query] += int(row["switches"] > 0)

    overall_row = finalize_bucket("overall", overall)
    scenewise_minimal_gate = (
        overall_row["selected_delta_count"] >= 2
        and overall["new_wrong_goals"] == 0
        and positive_scene_count >= 2
        and negative_scene_count == 0
        and switch_scene_count >= 2
    )
    active_queries = [row["key"] for row in query_rows if row["switches"] > 0]
    category_robust_gate = all(positive_query_scene_count.get(query, 0) >= 2 for query in active_queries)
    promotion_ready = bool(scenewise_minimal_gate and category_robust_gate and independent_split)

    return {
        "schema_version": SCHEMA_VERSION,
        "overall": overall_row,
        "scene_count": len(scene_rows),
        "positive_scene_count": positive_scene_count,
        "negative_scene_count": negative_scene_count,
        "switch_scene_count": switch_scene_count,
        "positive_query_scene_count": dict(sorted(positive_query_scene_count.items())),
        "switched_query_scene_count": dict(sorted(switched_query_scene_count.items())),
        "active_queries": active_queries,
        "gate": {
            "scenewise_minimal_gate": scenewise_minimal_gate,
            "category_robust_gate": category_robust_gate,
            "independent_split_evaluated": independent_split,
            "promotion_ready": promotion_ready,
            "reason": (
                "promotion_ready"
                if promotion_ready
                else (
                    "category_signal_too_sparse"
                    if scenewise_minimal_gate and not category_robust_gate
                    else "scenewise_minimal_gate_failed"
                    if not scenewise_minimal_gate
                    else "independent_split_not_evaluated"
                )
            ),
        },
        "scene_rows": scene_rows,
        "query_rows": query_rows,
        "query_scene_rows": query_scene_rows,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    decisions = load_jsonl(Path(args.decisions))
    summary = summarize(decisions, bool(args.independent_split))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_json(out / "summary.json", summary)
    write_jsonl(out / "scene_summary.jsonl", summary["scene_rows"])
    write_jsonl(out / "query_summary.jsonl", summary["query_rows"])
    write_jsonl(out / "query_scene_summary.jsonl", summary["query_scene_rows"])
    write_jsonl(out / "switched_decisions.jsonl", [row for row in decisions if row.get("switched") is True])
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate weak-category detector evidence with scene-wise robustness checks.")
    parser.add_argument("--decisions", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--independent-split", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
