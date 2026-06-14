import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


def read_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                yield json.loads(line)


def mean(values: Iterable[float]) -> Optional[float]:
    rows = [float(value) for value in values if value is not None and math.isfinite(float(value))]
    if not rows:
        return None
    return sum(rows) / len(rows)


def percentile(values: List[float], q: float) -> Optional[float]:
    if not values:
        return None
    rows = sorted(float(value) for value in values)
    if len(rows) == 1:
        return rows[0]
    pos = (len(rows) - 1) * q
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return rows[lo]
    weight = pos - lo
    return rows[lo] * (1.0 - weight) + rows[hi] * weight


def average_ranks(values: List[float]) -> List[float]:
    indexed = sorted(enumerate(values), key=lambda item: item[1])
    ranks = [0.0] * len(values)
    idx = 0
    while idx < len(indexed):
        end = idx + 1
        while end < len(indexed) and indexed[end][1] == indexed[idx][1]:
            end += 1
        avg_rank = (idx + 1 + end) / 2.0
        for original_idx, _ in indexed[idx:end]:
            ranks[original_idx] = avg_rank
        idx = end
    return ranks


def pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    x_mean = sum(xs) / len(xs)
    y_mean = sum(ys) / len(ys)
    x_var = sum((x - x_mean) ** 2 for x in xs)
    y_var = sum((y - y_mean) ** 2 for y in ys)
    if x_var <= 1e-12 or y_var <= 1e-12:
        return None
    cov = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys))
    return cov / math.sqrt(x_var * y_var)


def spearman(xs: List[float], ys: List[float]) -> Optional[float]:
    return pearson(average_ranks(xs), average_ranks(ys))


def auroc(scores: List[float], labels: List[int]) -> Optional[float]:
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


def average_precision(scores: List[float], labels: List[int]) -> Optional[float]:
    positives = sum(labels)
    if positives == 0:
        return None
    ranked = sorted(zip(scores, labels), key=lambda item: item[0], reverse=True)
    hits = 0
    precision_sum = 0.0
    for idx, (_, label) in enumerate(ranked, start=1):
        if label == 1:
            hits += 1
            precision_sum += hits / idx
    return precision_sum / positives


def norm_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        return None
    return out


def candidate_rows(path: Path, policy: str) -> List[Dict[str, Any]]:
    rows = []
    for row in read_jsonl(path):
        if row.get("policy") != policy:
            continue
        if row.get("candidate_uses_gt_for_action") is not False:
            continue
        if not isinstance(row.get("candidate_correct"), bool):
            continue
        score = norm_float(row.get("U_sem"))
        if score is None:
            continue
        rows.append(row)
    return rows


def summarize_by_query(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("query"))].append(row)
    summary = []
    for query, query_rows in sorted(grouped.items()):
        labels = [0 if row["candidate_correct"] else 1 for row in query_rows]
        summary.append(
            {
                "query": query,
                "n": len(query_rows),
                "failure_rate": mean(labels),
                "mean_U_sem": mean(float(row["U_sem"]) for row in query_rows),
                "selected_rank_failure": [
                    {
                        "rank": int(row["candidate_rank"]),
                        "U_sem": float(row["U_sem"]),
                        "failure": not bool(row["candidate_correct"]),
                    }
                    for row in sorted(query_rows, key=lambda item: int(item["candidate_rank"]))
                ],
            }
        )
    return summary


def selected_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    selected = [row for row in rows if row.get("selected_for_goal") is True]
    labels = [0 if row["candidate_correct"] else 1 for row in selected]
    return {
        "n": len(selected),
        "failure_rate": mean(labels),
        "mean_U_sem": mean(float(row["U_sem"]) for row in selected),
        "rows": [
            {
                "episode_key": row.get("episode_key"),
                "query": row.get("query"),
                "rank": row.get("candidate_rank"),
                "U_sem": row.get("U_sem"),
                "failure": not bool(row.get("candidate_correct")),
            }
            for row in selected
        ],
    }


def analyze(args: argparse.Namespace) -> Dict[str, Any]:
    rows = candidate_rows(Path(args.candidate_log), args.policy)
    labels = [0 if row["candidate_correct"] else 1 for row in rows]
    scores = [float(row["U_sem"]) for row in rows]
    positive_rate = mean(labels)
    ap = average_precision(scores, labels)
    p30 = percentile(scores, 0.30)
    p70 = percentile(scores, 0.70)
    low_rows = [row for row in rows if p30 is not None and float(row["U_sem"]) <= p30]
    high_rows = [row for row in rows if p70 is not None and float(row["U_sem"]) >= p70]
    low_rate = mean(0 if row["candidate_correct"] else 1 for row in low_rows)
    high_rate = mean(0 if row["candidate_correct"] else 1 for row in high_rows)
    bucket_gap = None if low_rate is None or high_rate is None else high_rate - low_rate

    result = {
        "candidate_log": str(args.candidate_log),
        "policy": args.policy,
        "n": len(rows),
        "positives_failure": sum(labels),
        "negatives_correct": len(labels) - sum(labels),
        "positive_rate_baseline": positive_rate,
        "AUROC": auroc(scores, labels),
        "AUPRC": ap,
        "AUPRC_delta_vs_baseline": None if ap is None or positive_rate is None else ap - positive_rate,
        "spearman_U_sem_vs_failure": spearman(scores, [float(label) for label in labels]),
        "p30_U_sem": p30,
        "p70_U_sem": p70,
        "low_bucket_n": len(low_rows),
        "high_bucket_n": len(high_rows),
        "low_bucket_failure_rate": low_rate,
        "high_bucket_failure_rate": high_rate,
        "high_minus_low_failure_rate": bucket_gap,
        "gate_thresholds": {
            "AUROC": 0.60,
            "AUPRC_delta_vs_baseline": 0.05,
            "spearman_U_sem_vs_failure": 0.15,
            "high_minus_low_failure_rate": 0.10,
        },
        "gate_pass": {
            "AUROC": auroc(scores, labels) is not None and auroc(scores, labels) >= 0.60,
            "AUPRC_delta_vs_baseline": ap is not None and positive_rate is not None and ap - positive_rate >= 0.05,
            "spearman_U_sem_vs_failure": spearman(scores, [float(label) for label in labels]) is not None
            and spearman(scores, [float(label) for label in labels]) >= 0.15,
            "high_minus_low_failure_rate": bucket_gap is not None and bucket_gap >= 0.10,
        },
        "selected_candidates": selected_summary(rows),
        "by_query": summarize_by_query(rows),
    }
    result["all_gate_pass"] = all(result["gate_pass"].values())
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze U_sem validity against candidate failure labels.")
    parser.add_argument("--candidate-log", required=True)
    parser.add_argument("--policy", default="NoReobserve")
    parser.add_argument("--out", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = analyze(args)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
