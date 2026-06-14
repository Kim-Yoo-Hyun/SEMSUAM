import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set


SCHEMA_VERSION = "h001.dense_association_repair_design.v1"


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


def correct_ids_by_episode(recall_rows: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    result: Dict[str, Set[str]] = {}
    for row in recall_rows:
        result[str(row.get("episode_key"))] = {
            str(candidate.get("candidate_id"))
            for candidate in row.get("correct_candidates") or []
            if candidate.get("candidate_id") is not None
        }
    return result


def candidate_is_correct(row: Dict[str, Any], correct_by_episode: Dict[str, Set[str]]) -> bool:
    return str(row.get("candidate_id")) in correct_by_episode.get(str(row.get("episode_key")), set())


def passes_variant(row: Dict[str, Any], variant: Dict[str, Any]) -> bool:
    if row.get("projection_status") != "visible":
        return False
    if variant["pixel_gate"] == "mask" and row.get("projected_pixel_inside_mask") is not True:
        return False
    if variant["pixel_gate"] == "box" and row.get("projected_pixel_inside_box") is not True:
        return False
    tolerance = variant.get("association_depth_tolerance_m")
    if tolerance is not None:
        depth_agreement = row.get("depth_agreement_m")
        if depth_agreement is not None and float(depth_agreement) > float(tolerance):
            return False
    return True


def summarize_variant(
    name: str,
    variant: Dict[str, Any],
    rows: List[Dict[str, Any]],
    correct_by_episode: Dict[str, Set[str]],
) -> Dict[str, Any]:
    passed = [row for row in rows if passes_variant(row, variant)]
    episodes = sorted({str(row.get("episode_key")) for row in rows})
    by_episode: List[Dict[str, Any]] = []
    recovered_episodes = 0
    wrong_supported_episodes = 0
    for episode_key in episodes:
        episode_rows = [row for row in passed if str(row.get("episode_key")) == episode_key]
        correct_rows = [row for row in episode_rows if candidate_is_correct(row, correct_by_episode)]
        wrong_rows = [row for row in episode_rows if not candidate_is_correct(row, correct_by_episode)]
        recovered_episodes += int(bool(correct_rows))
        wrong_supported_episodes += int(bool(wrong_rows))
        by_episode.append(
            {
                "episode_key": episode_key,
                "associated_rows": len(episode_rows),
                "correct_associated_rows": len(correct_rows),
                "wrong_associated_rows": len(wrong_rows),
                "associated_candidate_ids": sorted({str(row.get("candidate_id")) for row in episode_rows}),
                "correct_candidate_ids": sorted({str(row.get("candidate_id")) for row in correct_rows}),
                "wrong_candidate_ids": sorted({str(row.get("candidate_id")) for row in wrong_rows}),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "variant": name,
        "pixel_gate": variant["pixel_gate"],
        "association_depth_tolerance_m": variant.get("association_depth_tolerance_m"),
        "rows": len(rows),
        "associated_rows": len(passed),
        "association_rate": ratio(len(passed), len(rows)),
        "episodes": len(episodes),
        "episodes_with_correct_association": recovered_episodes,
        "episode_correct_association_rate": ratio(recovered_episodes, len(episodes)),
        "episodes_with_wrong_association": wrong_supported_episodes,
        "episode_wrong_association_rate": ratio(wrong_supported_episodes, len(episodes)),
        "associated_candidate_ids": sorted({str(row.get("candidate_id")) for row in passed}),
        "correct_associated_rows": sum(candidate_is_correct(row, correct_by_episode) for row in passed),
        "wrong_associated_rows": sum(not candidate_is_correct(row, correct_by_episode) for row in passed),
        "by_episode": by_episode,
    }


def choose_recommendation(variant_rows: List[Dict[str, Any]], min_association_rate: float) -> Dict[str, Any]:
    feasible = [
        row
        for row in variant_rows
        if row["episodes_with_correct_association"] == row["episodes"]
        and row["episodes_with_wrong_association"] == 0
        and row["associated_rows"] > 0
        and float(row["association_rate"] or 0.0) >= float(min_association_rate)
    ]
    if not feasible:
        return {
            "recommended_next_revision": "rerun_grounded_position_or_viewpoint_geometry",
            "min_association_rate": float(min_association_rate),
            "reason": "No offline depth/mask rule recovered all episodes without wrong associations while passing the association-rate gate.",
        }
    feasible.sort(
        key=lambda row: (
            float("inf")
            if row["association_depth_tolerance_m"] is None
            else float(row["association_depth_tolerance_m"]),
            row["associated_rows"],
        )
    )
    best = feasible[0]
    return {
        "recommended_next_revision": "rerun_same_geometry_with_relaxed_association_depth_tolerance",
        "recommended_variant": best["variant"],
        "association_depth_tolerance_m": best["association_depth_tolerance_m"],
        "min_association_rate": float(min_association_rate),
        "reason": (
            "This is the smallest tested depth tolerance that recovers both held-out chair episodes, "
            "passes the association-rate gate, and does not support a wrong candidate under GT analysis labels."
        ),
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    association_rows = load_jsonl(Path(args.association_rows))
    recall_rows = load_jsonl(Path(args.recall_rows))
    correct_by_episode = correct_ids_by_episode(recall_rows)
    variants = {
        "current_mask_depth_1_0": {"pixel_gate": "mask", "association_depth_tolerance_m": 1.0},
        "mask_depth_1_5": {"pixel_gate": "mask", "association_depth_tolerance_m": 1.5},
        "mask_depth_2_0": {"pixel_gate": "mask", "association_depth_tolerance_m": 2.0},
        "mask_depth_2_5": {"pixel_gate": "mask", "association_depth_tolerance_m": 2.5},
        "mask_depth_3_0": {"pixel_gate": "mask", "association_depth_tolerance_m": 3.0},
        "mask_no_depth": {"pixel_gate": "mask", "association_depth_tolerance_m": None},
        "box_no_depth": {"pixel_gate": "box", "association_depth_tolerance_m": None},
    }
    variant_rows = [
        summarize_variant(name, variant, association_rows, correct_by_episode)
        for name, variant in variants.items()
    ]
    recommendation = choose_recommendation(variant_rows, float(args.min_association_rate))
    by_status = Counter()
    for row in association_rows:
        if row.get("projection_status") == "visible" and row.get("projected_pixel_inside_mask") is True:
            by_status["visible_inside_mask"] += 1
        elif row.get("projection_status") == "visible" and row.get("projected_pixel_inside_box") is True:
            by_status["visible_inside_box_only"] += 1
        else:
            by_status[str(row.get("projection_status"))] += 1

    summary = {
        "schema_version": SCHEMA_VERSION,
        "association_rows": str(args.association_rows),
        "recall_rows": str(args.recall_rows),
        "out_root": str(args.out_root),
        "rows": len(association_rows),
        "status_counts": dict(sorted(by_status.items())),
        "variant_count": len(variant_rows),
        "min_association_rate": float(args.min_association_rate),
        "variants": variant_rows,
        "recommendation": recommendation,
        "point_height_assessment": {
            "status": "requires_detector_rerun",
            "agent_inference": (
                "The current detector output is sufficient to test depth tolerance offline, but not to measure "
                "a changed candidate point projection from grounded_position or visit_position."
            ),
        },
        "viewpoint_geometry_assessment": {
            "status": "not_first_revision",
            "agent_inference": (
                "The current frames already contain visible inside-mask projections for correct candidates; "
                "therefore viewpoint geometry is not the first repair unless relaxed depth association fails."
            ),
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
        "output_files": {
            "summary": "dense_association_repair_design_summary.json",
            "variants": "dense_association_repair_variant_rows.jsonl",
        },
    }
    out_root = Path(args.out_root)
    write_json(out_root / "dense_association_repair_design_summary.json", summary)
    write_jsonl(out_root / "dense_association_repair_variant_rows.jsonl", variant_rows)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Design association repair for fixed dense backend detector output.")
    parser.add_argument("--association-rows", required=True)
    parser.add_argument("--recall-rows", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--min-association-rate", type=float, default=0.20)
    return parser.parse_args()


def main() -> None:
    print(json.dumps(run(parse_args()), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
