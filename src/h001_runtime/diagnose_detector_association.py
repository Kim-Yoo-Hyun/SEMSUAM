import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional


SCHEMA_VERSION = "h001.detector_association_diagnostic.v1"


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


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def numeric_stats(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": mean(values),
        "median": median(values),
    }


def counter_dict(values: Iterable[Any]) -> Dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def branch_key(row: Dict[str, Any]) -> str:
    return str(row.get("external_branch_id") or row.get("episode_key") or "unknown")


def diagnose(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    visible = [row for row in rows if row.get("projection_status") == "visible"]
    associated = [row for row in rows if row.get("associated_to_candidate") is True]
    inside_box = [row for row in rows if row.get("projected_pixel_inside_box") is True]
    inside_mask = [row for row in rows if row.get("projected_pixel_inside_mask") is True]
    depth_mismatch = [row for row in rows if row.get("depth_check_status") == "depth_mismatch"]
    visible_inside_mask = [
        row
        for row in rows
        if row.get("projection_status") == "visible" and row.get("projected_pixel_inside_mask") is True
    ]
    visible_inside_mask_unassociated = [
        row
        for row in visible_inside_mask
        if row.get("associated_to_candidate") is not True
    ]
    depth_errors = [
        float(row["depth_error_m"])
        for row in rows
        if isinstance(row.get("depth_error_m"), (int, float))
    ]

    if rows and not associated and visible_inside_mask:
        dominant_failure = "visible_inside_mask_but_depth_or_association_rejects"
    elif rows and not associated and visible:
        dominant_failure = "visible_projection_without_candidate_association"
    elif rows and not visible:
        dominant_failure = "viewpoint_projection_failure"
    else:
        dominant_failure = "mixed_or_association_present"

    by_branch: List[Dict[str, Any]] = []
    grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[branch_key(row)].append(row)
    for key, branch_rows in sorted(grouped.items()):
        branch_visible = [row for row in branch_rows if row.get("projection_status") == "visible"]
        branch_inside_mask = [row for row in branch_rows if row.get("projected_pixel_inside_mask") is True]
        branch_associated = [row for row in branch_rows if row.get("associated_to_candidate") is True]
        branch_depth_errors = [
            float(row["depth_error_m"])
            for row in branch_rows
            if isinstance(row.get("depth_error_m"), (int, float))
        ]
        by_branch.append(
            {
                "schema_version": SCHEMA_VERSION,
                "external_branch_id": key,
                "episode_keys": sorted({str(row.get("episode_key")) for row in branch_rows}),
                "candidate_ids": sorted({str(row.get("candidate_id")) for row in branch_rows}),
                "rows": len(branch_rows),
                "visible_rows": len(branch_visible),
                "inside_mask_rows": len(branch_inside_mask),
                "associated_rows": len(branch_associated),
                "association_rate": ratio(len(branch_associated), len(branch_rows)),
                "projection_status_counts": counter_dict(row.get("projection_status") for row in branch_rows),
                "depth_check_status_counts": counter_dict(row.get("depth_check_status") for row in branch_rows),
                "depth_error_m": numeric_stats(branch_depth_errors),
                "uses_gt_for_action": False,
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "rows": len(rows),
        "associated_rows": len(associated),
        "association_rate": ratio(len(associated), len(rows)),
        "visible_rows": len(visible),
        "visible_rate": ratio(len(visible), len(rows)),
        "inside_box_rows": len(inside_box),
        "inside_box_rate": ratio(len(inside_box), len(rows)),
        "inside_mask_rows": len(inside_mask),
        "inside_mask_rate": ratio(len(inside_mask), len(rows)),
        "depth_mismatch_rows": len(depth_mismatch),
        "depth_mismatch_rate": ratio(len(depth_mismatch), len(rows)),
        "visible_inside_mask_rows": len(visible_inside_mask),
        "visible_inside_mask_unassociated_rows": len(visible_inside_mask_unassociated),
        "projection_status_counts": counter_dict(row.get("projection_status") for row in rows),
        "depth_check_status_counts": counter_dict(row.get("depth_check_status") for row in rows),
        "candidate_selection_counts": counter_dict(row.get("candidate_selection_source") for row in rows),
        "depth_error_m": numeric_stats(depth_errors),
        "dominant_failure": dominant_failure,
        "by_branch_rows": by_branch,
        "interpretation": {
            "fact": "This diagnostic reads detector candidate-association rows only.",
            "agent_inference": (
                "If detector boxes and masks exist but visible mask-overlapping candidate projections remain "
                "unassociated, the next revision should inspect point height, depth tolerance, and viewpoint geometry "
                "before changing terminal arbitration."
            ),
            "paper_claim_status": "not_a_paper_claim",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": False,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    detector_root = Path(args.detector_root)
    out_root = Path(args.out_root)
    rows = load_jsonl(detector_root / "detector_candidate_associations.jsonl")
    summary = diagnose(rows)
    summary.update(
        {
            "detector_root": str(detector_root),
            "out_root": str(out_root),
            "output_files": {
                "summary": "detector_association_diagnostic_summary.json",
                "by_branch": "detector_association_diagnostic_by_branch.jsonl",
            },
        }
    )
    write_json(out_root / "detector_association_diagnostic_summary.json", summary)
    write_jsonl(out_root / "detector_association_diagnostic_by_branch.jsonl", summary["by_branch_rows"])
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose detector candidate-association failures.")
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--out-root", required=True)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
