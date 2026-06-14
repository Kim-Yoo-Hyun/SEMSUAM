import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List

import numpy as np

from h001_runtime.export_hm3d_vlmaps import vlmaps_camera_pose
from h001_runtime.export_postview_frames import quaternion_from_xyzw
from h001_runtime.score_postview_vlm import artifact_index, candidate_point, project_point


SCHEMA_VERSION = "h001.stage2_projection_geometry_check.v1"


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


def ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def run(args: argparse.Namespace) -> Dict[str, Any]:
    out_root = Path(args.out_root)
    plan_rows = load_jsonl(Path(args.stage2_plan))
    candidates_by_key = artifact_index(Path(args.candidate_artifact))
    rows: List[Dict[str, Any]] = []
    status_counts: Counter[str] = Counter()
    status_by_role: Dict[str, Counter[str]] = defaultdict(Counter)
    missing_candidate_rows = 0

    for row in plan_rows:
        scene_id = str(row.get("scene_id"))
        query = str(row.get("query"))
        candidate_id = str(row.get("candidate_id"))
        candidates = candidates_by_key.get((scene_id, query), [])
        candidate = next((item for item in candidates if str(item.get("candidate_id")) == candidate_id), None)
        role = str(row.get("second_stage_role"))
        if candidate is None:
            missing_candidate_rows += 1
            status = "missing_candidate"
            projection = {"projection_status": status, "projected_pixel": None, "camera_forward_m": None}
        else:
            point = candidate_point(
                candidate,
                str(args.candidate_point_field),
                float(args.grounded_point_height_m),
                float(args.grounded_point_max_vertical_gap_m),
            )
            if point is None:
                projection = {"projection_status": "missing_candidate_point", "projected_pixel": None, "camera_forward_m": None}
            else:
                base_position = np.asarray(row.get("viewpoint_position"), dtype=np.float64)
                rotation = quaternion_from_xyzw(row.get("viewpoint_rotation"))
                world_from_camera = vlmaps_camera_pose(base_position, rotation, float(args.camera_height))
                projection = project_point(
                    point,
                    world_from_camera,
                    int(args.width),
                    int(args.height),
                    float(args.hfov),
                    float(args.min_projection_depth_m),
                )
            status = str(projection.get("projection_status"))

        status_counts[status] += 1
        status_by_role[role][status] += 1
        rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "external_branch_id": row.get("external_branch_id"),
                "scene_id": scene_id,
                "query": query,
                "candidate_id": candidate_id,
                "second_stage_role": role,
                "viewpoint_id": row.get("viewpoint_id"),
                "second_stage_viewpoint_index": row.get("second_stage_viewpoint_index"),
                "candidate_point_field": str(args.candidate_point_field),
                "projection_status": status,
                "projected_pixel": projection.get("projected_pixel"),
                "camera_forward_m": projection.get("camera_forward_m"),
                "uses_gt_for_action": False,
            }
        )

    visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
    summary = {
        "schema_version": SCHEMA_VERSION,
        "stage2_plan": str(args.stage2_plan),
        "candidate_artifact": str(args.candidate_artifact),
        "out_root": str(out_root),
        "candidate_point_field": str(args.candidate_point_field),
        "grounded_point_height_m": float(args.grounded_point_height_m),
        "grounded_point_max_vertical_gap_m": float(args.grounded_point_max_vertical_gap_m),
        "rows": len(rows),
        "visible_rows": len(visible_rows),
        "visible_rate": ratio(len(visible_rows), len(rows)),
        "missing_candidate_rows": missing_candidate_rows,
        "projection_status_counts": dict(sorted(status_counts.items())),
        "projection_status_by_role": {
            key: dict(sorted(value.items()))
            for key, value in sorted(status_by_role.items())
        },
        "uses_gt_for_action": False,
        "output_files": {
            "rows": "stage2_projection_geometry_rows.jsonl",
            "summary": "stage2_projection_geometry_summary.json",
        },
    }
    write_jsonl(out_root / "stage2_projection_geometry_rows.jsonl", rows)
    write_json(out_root / "stage2_projection_geometry_summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check second-stage target projection geometry without detector inference.")
    parser.add_argument("--stage2-plan", required=True)
    parser.add_argument("--candidate-artifact", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument(
        "--candidate-point-field",
        default="position",
        choices=["position", "visit_position", "grounded_position"],
    )
    parser.add_argument("--grounded-point-height-m", type=float, default=0.8)
    parser.add_argument("--grounded-point-max-vertical-gap-m", type=float, default=2.0)
    parser.add_argument("--width", type=int, default=160)
    parser.add_argument("--height", type=int, default=120)
    parser.add_argument("--camera-height", type=float, default=1.5)
    parser.add_argument("--hfov", type=float, default=90.0)
    parser.add_argument("--min-projection-depth-m", type=float, default=0.05)
    return parser.parse_args()


def main() -> None:
    summary = run(parse_args())
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
