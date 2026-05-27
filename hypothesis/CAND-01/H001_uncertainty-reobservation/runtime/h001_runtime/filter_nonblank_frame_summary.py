import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from PIL import Image, ImageStat


SCHEMA_VERSION = "h001.nonblank_frame_filter.v1"


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


def resolve_frame_path(frame_root: Path, path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return frame_root / path


def is_nonblank_rgb(path: Path, min_stddev: float) -> bool:
    image = Image.open(path).convert("RGB")
    stat = ImageStat.Stat(image)
    return max(float(value) for value in stat.stddev) > min_stddev


def filter_rows(rows: Sequence[Dict[str, Any]], frame_root: Path, min_stddev: float) -> Dict[str, Any]:
    filtered_rows: List[Dict[str, Any]] = []
    blank_records: List[Dict[str, Any]] = []
    rows_with_blank = 0
    dropped_rows: List[Dict[str, Any]] = []
    original_heading_count = 0
    kept_heading_count = 0

    for row in rows:
        original_headings = list(row.get("rendered_headings") or [])
        original_heading_count += len(original_headings)
        kept_headings: List[Dict[str, Any]] = []
        blank_count = 0
        for heading in original_headings:
            rgb_path = resolve_frame_path(frame_root, str(heading.get("rgb") or ""))
            if is_nonblank_rgb(rgb_path, min_stddev):
                kept_headings.append(dict(heading))
            else:
                blank_count += 1
                blank_records.append(
                    {
                        "decision_id": row.get("decision_id"),
                        "episode_key": row.get("episode_key"),
                        "scene_key": row.get("scene_key"),
                        "query": row.get("query"),
                        "candidate_id": row.get("candidate_id"),
                        "target_candidate_id": row.get("target_candidate_id"),
                        "rival_identity_target_role": row.get("rival_identity_target_role"),
                        "heading_id": heading.get("heading_id"),
                        "rgb": heading.get("rgb"),
                        "uses_gt_for_action": False,
                    }
                )
        if blank_count:
            rows_with_blank += 1
        if not kept_headings:
            dropped_rows.append(
                {
                    "decision_id": row.get("decision_id"),
                    "episode_key": row.get("episode_key"),
                    "scene_key": row.get("scene_key"),
                    "query": row.get("query"),
                    "candidate_id": row.get("candidate_id"),
                    "target_candidate_id": row.get("target_candidate_id"),
                    "rival_identity_target_role": row.get("rival_identity_target_role"),
                    "original_heading_count": len(original_headings),
                    "uses_gt_for_action": False,
                }
            )
            continue
        updated = dict(row)
        updated["rendered_headings"] = kept_headings
        updated["nonblank_filter_schema_version"] = SCHEMA_VERSION
        updated["nonblank_filter_removed_heading_count"] = blank_count
        updated["nonblank_filter_original_heading_count"] = len(original_headings)
        updated["nonblank_filter_kept_heading_count"] = len(kept_headings)
        filtered_rows.append(updated)
        kept_heading_count += len(kept_headings)

    query_blank_counts = Counter(str(row.get("query")) for row in blank_records)
    scene_blank_counts = Counter(str(row.get("scene_key")) for row in blank_records)
    summary = {
        "schema_version": SCHEMA_VERSION,
        "input_rows": len(rows),
        "output_rows": len(filtered_rows),
        "dropped_rows": len(dropped_rows),
        "rows_with_blank_headings": rows_with_blank,
        "original_heading_count": original_heading_count,
        "kept_heading_count": kept_heading_count,
        "removed_blank_heading_count": len(blank_records),
        "row_level_nonblank_gate_passed": len(dropped_rows) == 0 and len(filtered_rows) == len(rows),
        "strict_no_blank_heading_gate_passed": len(blank_records) == 0,
        "query_blank_heading_counts": dict(sorted(query_blank_counts.items())),
        "scene_blank_heading_counts": dict(sorted(scene_blank_counts.items())),
        "uses_gt_for_action": False,
        "paper_claim_allowed": False,
        "interpretation": {
            "fact": "Blank RGB headings are removed before detector/SAM2 scoring.",
            "agent_inference": (
                "Detector validation can proceed if row_level_nonblank_gate_passed is true, but the blank heading "
                "rate should be reported as a rendering/viewpoint limitation."
            ),
        },
    }
    return {
        "rows": filtered_rows,
        "blank_records": blank_records,
        "dropped_rows": dropped_rows,
        "summary": summary,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    frame_summary = Path(args.frame_summary)
    frame_root = Path(args.frame_root)
    out_root = Path(args.out_root)
    result = filter_rows(load_jsonl(frame_summary), frame_root, float(args.min_stddev))
    write_jsonl(out_root / "rival_identity_frame_summary_nonblank.jsonl", result["rows"])
    write_jsonl(out_root / "blank_heading_rows.jsonl", result["blank_records"])
    write_jsonl(out_root / "dropped_frame_rows.jsonl", result["dropped_rows"])
    write_json(out_root / "nonblank_frame_filter_summary.json", result["summary"])
    return result["summary"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Filter blank RGB headings from a frame summary JSONL.")
    parser.add_argument("--frame-summary", required=True)
    parser.add_argument("--frame-root", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-stddev", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
