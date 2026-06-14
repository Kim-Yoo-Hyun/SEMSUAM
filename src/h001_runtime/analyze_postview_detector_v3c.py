import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.postview_detector_calibration.v3c"


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


def safe_float(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def pairwise_auc(positives: List[float], negatives: List[float]) -> Optional[float]:
    if not positives or not negatives:
        return None
    wins = 0.0
    pairs = 0
    for pos in positives:
        for neg in negatives:
            pairs += 1
            if pos > neg:
                wins += 1.0
            elif pos == neg:
                wins += 0.5
    return wins / pairs if pairs else None


def ratio(numerator: int, denominator: int) -> Optional[float]:
    return None if denominator == 0 else numerator / denominator


def box_area_ratio(box: Any, image_area: float = 160.0 * 120.0) -> Optional[float]:
    if not isinstance(box, list) or len(box) != 4:
        return None
    left, top, right, bottom = [safe_float(value) for value in box]
    if left is None or top is None or right is None or bottom is None:
        return None
    width = max(0.0, right - left)
    height = max(0.0, bottom - top)
    if image_area <= 0.0:
        return None
    return min(1.0, (width * height) / image_area)


def box_diagonal(box: Any) -> Optional[float]:
    if not isinstance(box, list) or len(box) != 4:
        return None
    left, top, right, bottom = [safe_float(value) for value in box]
    if left is None or top is None or right is None or bottom is None:
        return None
    width = max(0.0, right - left)
    height = max(0.0, bottom - top)
    return math.hypot(width, height)


def compactness_from_area(area_ratio: Optional[float]) -> Optional[float]:
    if area_ratio is None:
        return None
    # Very large boxes often mean room-level or repeated-object clutter, not node-local support.
    if area_ratio <= 0.35:
        return 1.0
    return max(0.0, 1.0 - ((area_ratio - 0.35) / 0.65))


def projected_box_proximity(row: Dict[str, Any]) -> Optional[float]:
    if row.get("projection_status") != "visible":
        return None
    score = safe_float(row.get("best_box_score"))
    distance = safe_float(row.get("box_center_distance_px"))
    box = row.get("best_box_xyxy")
    if score is None or distance is None or box is None:
        return None
    diagonal = box_diagonal(box)
    scale = max(18.0, (diagonal or 0.0) * 0.35)
    proximity = math.exp(-distance / scale)
    if row.get("projected_pixel_inside_mask") is True:
        proximity = 1.0
    elif row.get("projected_pixel_inside_box") is True:
        proximity = max(proximity, 0.85)
    return float(max(0.0, min(1.0, proximity)))


def rank_score(rank: Optional[int], count: int) -> Optional[float]:
    if rank is None or count <= 0:
        return None
    if count == 1:
        return 1.0
    return 1.0 - (rank - 1) / (count - 1)


def sigmoid(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    clipped = max(-20.0, min(20.0, float(value)))
    return 1.0 / (1.0 + math.exp(-clipped))


def candidate_label_index(rows: List[Dict[str, Any]], policy: str) -> Dict[Tuple[str, str], Dict[str, Any]]:
    labels: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        labels[(str(episode_key), str(candidate_id))] = row
    return labels


def baseline_top_index(rows: List[Dict[str, Any]], policy: str) -> Dict[str, Dict[str, Any]]:
    index: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        if str(row.get("policy")) != policy:
            continue
        if row.get("selected_for_goal") is not True:
            continue
        episode_key = row.get("episode_key")
        if episode_key is not None:
            index[str(episode_key)] = row
    return index


def aggregate_candidate_rows(
    association_rows: List[Dict[str, Any]],
    labels: Dict[Tuple[str, str], Dict[str, Any]],
) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = defaultdict(list)
    for row in association_rows:
        episode_key = row.get("episode_key")
        candidate_id = row.get("candidate_id")
        if episode_key is None or candidate_id is None:
            continue
        grouped[(str(episode_key), str(candidate_id))].append(row)

    table: List[Dict[str, Any]] = []
    all_keys = set(labels) | set(grouped)
    for episode_key, candidate_id in sorted(all_keys):
        rows = grouped.get((episode_key, candidate_id), [])
        label = labels.get((episode_key, candidate_id), {})
        best_scores = [safe_float(row.get("best_box_score")) for row in rows]
        best_scores = [score for score in best_scores if score is not None]
        visible_rows = [row for row in rows if row.get("projection_status") == "visible"]
        center_distances = [safe_float(row.get("box_center_distance_px")) for row in visible_rows]
        center_distances = [dist for dist in center_distances if dist is not None]
        depth_errors = [safe_float(row.get("depth_error_m")) for row in rows]
        depth_errors = [err for err in depth_errors if err is not None]
        box_area_ratios = [box_area_ratio(row.get("best_box_xyxy")) for row in visible_rows]
        box_area_ratios = [value for value in box_area_ratios if value is not None]
        proximity_values = [projected_box_proximity(row) for row in visible_rows]
        proximity_values = [value for value in proximity_values if value is not None]
        extent_scores: List[float] = []
        compact_extent_scores: List[float] = []
        for row in visible_rows:
            score = safe_float(row.get("best_box_score"))
            proximity = projected_box_proximity(row)
            area = box_area_ratio(row.get("best_box_xyxy"))
            compactness = compactness_from_area(area)
            if score is None or proximity is None:
                continue
            extent_score = float(score * proximity)
            extent_scores.append(extent_score)
            if compactness is not None:
                compact_extent_scores.append(float(extent_score * compactness))
        table.append(
            {
                "schema_version": SCHEMA_VERSION,
                "episode_key": episode_key,
                "episode_id": label.get("episode_id") or (rows[0].get("episode_id") if rows else None),
                "scene_id": label.get("scene_id") or (rows[0].get("scene_id") if rows else None),
                "query": label.get("query") or (rows[0].get("query") if rows else None),
                "candidate_id": candidate_id,
                "candidate_rank_before": label.get("candidate_rank")
                if label.get("candidate_rank") is not None
                else (rows[0].get("candidate_rank_before") if rows else None),
                "candidate_score_before": safe_float(label.get("candidate_score")),
                "U_sem_before": safe_float(label.get("U_sem")),
                "score_uncertainty_before": safe_float(label.get("score_uncertainty")),
                "margin_uncertainty_before": safe_float(label.get("margin_uncertainty")),
                "view_count_uncertainty_before": safe_float(label.get("view_count_uncertainty")),
                "is_top_before": label.get("selected_for_goal") is True,
                "candidate_correct": label.get("candidate_correct"),
                "candidate_correct_source": label.get("candidate_correct_source"),
                "candidate_reachable": label.get("candidate_reachable"),
                "wrong_goal_visit_before": label.get("wrong_goal_visit"),
                "selected_for_goal_before": label.get("selected_for_goal"),
                "association_observation_count": len(rows),
                "visible_count": sum(row.get("projection_status") == "visible" for row in rows),
                "inside_box_count": sum(row.get("projected_pixel_inside_box") is True for row in rows),
                "inside_mask_count": sum(row.get("projected_pixel_inside_mask") is True for row in rows),
                "associated_count": sum(row.get("associated_to_candidate") is True for row in rows),
                "depth_consistent_count": sum(row.get("depth_check_status") == "consistent" for row in rows),
                "depth_mismatch_count": sum(row.get("depth_check_status") == "depth_mismatch" for row in rows),
                "best_box_score_max": max(best_scores) if best_scores else None,
                "best_box_score_mean": statistics.mean(best_scores) if best_scores else None,
                "min_box_center_distance_px": min(center_distances) if center_distances else None,
                "min_depth_error_m": min(depth_errors) if depth_errors else None,
                "node_box_proximity_max": max(proximity_values) if proximity_values else None,
                "node_box_proximity_mean": statistics.mean(proximity_values) if proximity_values else None,
                "node_extent_score_max": max(extent_scores) if extent_scores else None,
                "node_extent_score_mean": statistics.mean(extent_scores) if extent_scores else None,
                "compact_node_extent_score_max": max(compact_extent_scores) if compact_extent_scores else None,
                "compact_node_extent_score_mean": statistics.mean(compact_extent_scores)
                if compact_extent_scores
                else None,
                "near_box_support_count": sum(value >= 0.35 for value in proximity_values),
                "compact_box_support_count": sum(value >= 0.05 for value in compact_extent_scores),
                "large_box_hit_count": sum((value or 0.0) >= 0.50 for value in box_area_ratios),
                "mean_visible_box_area_ratio": statistics.mean(box_area_ratios) if box_area_ratios else None,
                "uses_gt_for_action": False,
                "uses_gt_for_analysis": label.get("candidate_correct") is not None,
            }
        )
    return table


def add_objective_fields(candidate_table: List[Dict[str, Any]]) -> None:
    scores_by_query: Dict[str, List[float]] = defaultdict(list)
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in candidate_table:
        by_episode[str(row.get("episode_key"))].append(row)
        score = safe_float(row.get("best_box_score_max"))
        if score is not None:
            scores_by_query[str(row.get("query"))].append(score)

    query_stats: Dict[str, Tuple[float, float]] = {}
    for query, values in scores_by_query.items():
        if len(values) < 2:
            query_stats[query] = (values[0] if values else 0.0, 1.0)
        else:
            std = statistics.pstdev(values)
            query_stats[query] = (statistics.mean(values), std if std > 1e-8 else 1.0)

    episode_counts = {episode_key: len(rows) for episode_key, rows in by_episode.items()}
    for row in candidate_table:
        detector = safe_float(row.get("best_box_score_max"))
        mean_std = query_stats.get(str(row.get("query")), (0.0, 1.0))
        detector_z = None if detector is None else (detector - mean_std[0]) / mean_std[1]
        detector_prob = sigmoid(detector_z)
        rank = row.get("candidate_rank_before")
        semantic_prior = rank_score(int(rank), episode_counts.get(str(row.get("episode_key")), 0)) if rank else None
        visible = int(row.get("visible_count") or 0)
        inside_mask = int(row.get("inside_mask_count") or 0)
        associated = int(row.get("associated_count") or 0)
        depth_mismatch = int(row.get("depth_mismatch_count") or 0)
        visibility_support = min(1.0, visible / 3.0)
        mask_support = min(1.0, inside_mask / 2.0)
        association_support = min(1.0, associated / 2.0)
        geometry_penalty = min(1.0, depth_mismatch / max(1, visible))
        semantic_value = semantic_prior if semantic_prior is not None else 0.0
        detector_value = detector_prob if detector_prob is not None else 0.0

        row["detector_query_zscore"] = detector_z
        row["detector_query_prob"] = detector_prob
        row["semantic_rank_prior"] = semantic_prior
        row["visibility_support"] = visibility_support
        row["mask_support"] = mask_support
        row["association_support"] = association_support
        row["geometry_penalty"] = geometry_penalty
        row["O1_detector_max"] = detector
        row["O2_detector_prior"] = 0.50 * semantic_value + 0.50 * detector_value
        row["O3_detector_geometry"] = (
            0.45 * semantic_value
            + 0.35 * detector_value
            + 0.10 * visibility_support
            + 0.10 * mask_support
            - 0.15 * geometry_penalty
        )
        row["O5_node_extent"] = safe_float(row.get("node_extent_score_max"))
        row["O6_compact_extent"] = safe_float(row.get("compact_node_extent_score_max"))
        compact_value = safe_float(row.get("compact_node_extent_score_max")) or 0.0
        proximity_value = safe_float(row.get("node_box_proximity_max")) or 0.0
        row["O7_extent_prior"] = 0.40 * semantic_value + 0.40 * compact_value + 0.20 * proximity_value

    query_detector_stats = per_query_auc(candidate_table, "O1_detector_max")
    reliable_queries = {
        query
        for query, stats in query_detector_stats.items()
        if (stats.get("auc") is not None)
        and float(stats["auc"]) >= 0.65
        and int(stats.get("positive_count") or 0) >= 3
        and int(stats.get("negative_count") or 0) >= 3
    }
    for row in candidate_table:
        semantic_value = safe_float(row.get("semantic_rank_prior")) or 0.0
        if str(row.get("query")) in reliable_queries:
            row["O8_category_gate"] = safe_float(row.get("O1_detector_max"))
            row["category_gate_mode"] = "detector"
        else:
            row["O8_category_gate"] = semantic_value
            row["category_gate_mode"] = "semantic_prior"

    candidate_fields = ["O1_detector_max", "O5_node_extent", "O6_compact_extent"]
    stats_by_field = {field: per_query_auc(candidate_table, field) for field in candidate_fields}
    best_field_by_query: Dict[str, str] = {}
    for query in sorted({str(row.get("query")) for row in candidate_table}):
        candidates: List[Tuple[float, str]] = []
        for field in candidate_fields:
            stats = stats_by_field[field].get(query, {})
            auc = stats.get("auc")
            if (
                auc is not None
                and float(auc) >= 0.65
                and int(stats.get("positive_count") or 0) >= 3
                and int(stats.get("negative_count") or 0) >= 3
            ):
                candidates.append((float(auc), field))
        if candidates:
            best_field_by_query[query] = max(candidates, key=lambda item: item[0])[1]

    for row in candidate_table:
        query = str(row.get("query"))
        semantic_value = safe_float(row.get("semantic_rank_prior")) or 0.0
        selected_field = best_field_by_query.get(query)
        if selected_field is None:
            row["O9_category_best_gate"] = semantic_value
            row["category_best_gate_mode"] = "semantic_prior"
        else:
            row["O9_category_best_gate"] = safe_float(row.get(selected_field))
            row["category_best_gate_mode"] = selected_field


def per_query_auc(candidate_table: List[Dict[str, Any]], field: str) -> Dict[str, Dict[str, Any]]:
    grouped: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: {"positive": [], "negative": []})
    for row in candidate_table:
        score = score_value(row, field)
        correct = row.get("candidate_correct")
        if score is None or correct is None:
            continue
        key = str(row.get("query"))
        if correct is True:
            grouped[key]["positive"].append(score)
        elif correct is False:
            grouped[key]["negative"].append(score)
    stats: Dict[str, Dict[str, Any]] = {}
    for query, values in sorted(grouped.items()):
        positives = values["positive"]
        negatives = values["negative"]
        stats[query] = {
            "field": field,
            "positive_count": len(positives),
            "negative_count": len(negatives),
            "auc": pairwise_auc(positives, negatives),
        }
    return stats


def score_value(row: Dict[str, Any], field: str) -> Optional[float]:
    value = row.get(field)
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int):
        return float(value)
    return safe_float(value)


def best_by_field(rows: List[Dict[str, Any]], field: str) -> Optional[Dict[str, Any]]:
    scored: List[Tuple[float, int, Dict[str, Any]]] = []
    for row in rows:
        score = score_value(row, field)
        if score is None:
            continue
        rank = int(row.get("candidate_rank_before") or 9999)
        scored.append((score, -rank, row))
    if not scored:
        return None
    return max(scored, key=lambda item: (item[0], item[1]))[2]


def build_episode_table(
    candidate_table: List[Dict[str, Any]],
    baseline_top: Dict[str, Dict[str, Any]],
    selector_fields: List[str],
    switch_margin: float,
) -> List[Dict[str, Any]]:
    by_episode: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in candidate_table:
        by_episode[str(row.get("episode_key"))].append(row)

    rows_out: List[Dict[str, Any]] = []
    for episode_key, rows in sorted(by_episode.items()):
        top_label = baseline_top.get(episode_key) or next((row for row in rows if row.get("is_top_before")), {})
        baseline_correct = top_label.get("candidate_correct")
        baseline_wrong = top_label.get("wrong_goal_visit")
        top_candidate = str(top_label.get("candidate_id"))
        top_detector = next((row for row in rows if str(row.get("candidate_id")) == top_candidate), {})
        item = {
            "schema_version": SCHEMA_VERSION,
            "episode_key": episode_key,
            "episode_id": top_label.get("episode_id") or (rows[0].get("episode_id") if rows else None),
            "scene_id": top_label.get("scene_id") or (rows[0].get("scene_id") if rows else None),
            "query": top_label.get("query") or (rows[0].get("query") if rows else None),
            "baseline_candidate_id": top_candidate,
            "baseline_candidate_correct": baseline_correct,
            "baseline_wrong_goal_visit": baseline_wrong,
            "candidate_count": len(rows),
            "any_association": any(int(row.get("associated_count") or 0) > 0 for row in rows),
            "top_association": int(top_detector.get("associated_count") or 0) > 0,
            "top_inside_mask": int(top_detector.get("inside_mask_count") or 0) > 0,
            "top_visible": int(top_detector.get("visible_count") or 0) > 0,
            "uses_gt_for_action": False,
            "uses_gt_for_analysis": baseline_correct is not None,
        }
        for field in selector_fields:
            if field == "O4_conservative_switch":
                top_detector = next((row for row in rows if str(row.get("candidate_id")) == top_candidate), {})
                top_score = score_value(top_detector, "O3_detector_geometry")
                best_alternative = best_by_field(
                    [
                        row
                        for row in rows
                        if str(row.get("candidate_id")) != top_candidate
                        and int(row.get("visible_count") or 0) > 0
                    ],
                    "O3_detector_geometry",
                )
                alt_score = score_value(best_alternative or {}, "O3_detector_geometry")
                selected = (
                    best_alternative
                    if alt_score is not None
                    and top_score is not None
                    and (alt_score - top_score) >= switch_margin
                    else top_detector
                )
            elif field == "O10_category_best_switch":
                top_detector = next((row for row in rows if str(row.get("candidate_id")) == top_candidate), {})
                top_score = score_value(top_detector, "O9_category_best_gate")
                best_alternative = best_by_field(
                    [row for row in rows if str(row.get("candidate_id")) != top_candidate],
                    "O9_category_best_gate",
                )
                alt_score = score_value(best_alternative or {}, "O9_category_best_gate")
                selected = (
                    best_alternative
                    if alt_score is not None
                    and top_score is not None
                    and (alt_score - top_score) >= switch_margin
                    else top_detector
                )
            else:
                selected = best_by_field(rows, field)
            prefix = f"select_{field}"
            if selected is None:
                item[f"{prefix}_eligible"] = False
                item[f"{prefix}_candidate_id"] = None
                item[f"{prefix}_candidate_correct"] = None
                item[f"{prefix}_fixes_wrong_goal"] = False
                item[f"{prefix}_creates_wrong_goal"] = False
                continue
            selected_correct = selected.get("candidate_correct")
            item[f"{prefix}_eligible"] = score_value(selected, field) not in (None, 0.0)
            if field == "O4_conservative_switch":
                item[f"{prefix}_eligible"] = selected.get("candidate_id") is not None
            if field == "O10_category_best_switch":
                item[f"{prefix}_eligible"] = selected.get("candidate_id") is not None
            item[f"{prefix}_candidate_id"] = selected.get("candidate_id")
            item[f"{prefix}_candidate_correct"] = selected_correct
            item[f"{prefix}_score"] = score_value(selected, field)
            item[f"{prefix}_rank_before"] = selected.get("candidate_rank_before")
            item[f"{prefix}_fixes_wrong_goal"] = baseline_correct is False and selected_correct is True
            item[f"{prefix}_creates_wrong_goal"] = baseline_correct is True and selected_correct is False
        rows_out.append(item)
    return rows_out


def candidate_auc(candidate_table: List[Dict[str, Any]], field: str) -> Optional[float]:
    positives: List[float] = []
    negatives: List[float] = []
    for row in candidate_table:
        score = score_value(row, field)
        correct = row.get("candidate_correct")
        if score is None or correct is None:
            continue
        if correct is True:
            positives.append(score)
        elif correct is False:
            negatives.append(score)
    return pairwise_auc(positives, negatives)


def selector_summary(episode_table: List[Dict[str, Any]], field: str) -> Dict[str, Any]:
    prefix = f"select_{field}"
    eligible = [row for row in episode_table if row.get(f"{prefix}_eligible") is True]
    baseline_labeled = [row for row in episode_table if row.get("baseline_candidate_correct") is not None]
    baseline_correct = sum(row.get("baseline_candidate_correct") is True for row in baseline_labeled)
    selected_labeled = [row for row in eligible if row.get(f"{prefix}_candidate_correct") is not None]
    selected_correct = sum(row.get(f"{prefix}_candidate_correct") is True for row in selected_labeled)
    fixes = sum(row.get(f"{prefix}_fixes_wrong_goal") is True for row in eligible)
    creates = sum(row.get(f"{prefix}_creates_wrong_goal") is True for row in eligible)
    return {
        "field": field,
        "eligible_rows": len(eligible),
        "eligible_rate": ratio(len(eligible), len(episode_table)),
        "baseline_labeled_rows": len(baseline_labeled),
        "baseline_selected_correct": baseline_correct,
        "baseline_selected_correct_rate": ratio(baseline_correct, len(baseline_labeled)),
        "selected_labeled_rows": len(selected_labeled),
        "selected_correct": selected_correct,
        "selected_correct_rate_on_eligible": ratio(selected_correct, len(selected_labeled)),
        "selected_correct_delta_on_all_rows": ratio(selected_correct - baseline_correct, len(baseline_labeled)),
        "wrong_goal_fixes": fixes,
        "new_wrong_goals": creates,
    }


def build_summary(
    candidate_table: List[Dict[str, Any]],
    episode_table: List[Dict[str, Any]],
    selector_fields: List[str],
    min_association_rate: float,
    min_candidate_auc: float,
) -> Dict[str, Any]:
    rows = len(episode_table)
    rows_with_any = sum(row.get("any_association") is True for row in episode_table)
    baseline_wrong = [row for row in episode_table if row.get("baseline_wrong_goal_visit") is True]
    baseline_correct = [row for row in episode_table if row.get("baseline_candidate_correct") is True]
    wrong_any = sum(row.get("any_association") is True for row in baseline_wrong)
    correct_any = sum(row.get("any_association") is True for row in baseline_correct)
    auc_by_field = {field: candidate_auc(candidate_table, field) for field in selector_fields}
    selector_summaries = {field: selector_summary(episode_table, field) for field in selector_fields}
    best_auc = max((value for value in auc_by_field.values() if value is not None), default=None)
    best_delta = max(
        (
            value["selected_correct_delta_on_all_rows"]
            for value in selector_summaries.values()
            if value["selected_correct_delta_on_all_rows"] is not None
        ),
        default=None,
    )
    association_rate = ratio(rows_with_any, rows)
    gate_pass = (
        association_rate is not None
        and association_rate >= min_association_rate
        and best_auc is not None
        and best_auc >= min_candidate_auc
        and best_delta is not None
        and best_delta > 0.0
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "rows": rows,
        "candidate_rows": len(candidate_table),
        "rows_with_any_association": rows_with_any,
        "rows_with_any_association_rate": association_rate,
        "baseline_wrong_goal_rows": len(baseline_wrong),
        "baseline_correct_rows": len(baseline_correct),
        "wrong_goal_rows_with_any_association": wrong_any,
        "wrong_goal_rows_with_any_association_rate": ratio(wrong_any, len(baseline_wrong)),
        "baseline_correct_rows_with_any_association": correct_any,
        "baseline_correct_rows_with_any_association_rate": ratio(correct_any, len(baseline_correct)),
        "candidate_auc_by_field": auc_by_field,
        "selector_summary": selector_summaries,
        "best_candidate_auc": best_auc,
        "best_selected_correct_delta_on_all_rows": best_delta,
        "gate": {
            "min_association_rate": min_association_rate,
            "min_candidate_auc": min_candidate_auc,
            "passes_detector_calibration_gate": gate_pass,
            "reason": "pass" if gate_pass else "detector_mask_evidence_not_yet_policy_ready",
        },
        "uses_gt_for_action": False,
        "uses_gt_for_analysis": True,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    detector_root = Path(args.detector_root)
    candidate_decisions = load_jsonl(Path(args.candidate_decisions))
    association_rows = load_jsonl(detector_root / "detector_candidate_associations.jsonl")
    labels = candidate_label_index(candidate_decisions, str(args.policy))
    baseline_top = baseline_top_index(candidate_decisions, str(args.policy))
    selector_fields = [
        "associated_count",
        "inside_mask_count",
        "inside_box_count",
        "visible_count",
        "best_box_score_max",
        "O1_detector_max",
        "O2_detector_prior",
        "O3_detector_geometry",
        "O4_conservative_switch",
        "O5_node_extent",
        "O6_compact_extent",
        "O7_extent_prior",
        "O8_category_gate",
        "O9_category_best_gate",
        "O10_category_best_switch",
    ]
    candidate_table = aggregate_candidate_rows(association_rows, labels)
    add_objective_fields(candidate_table)
    episode_table = build_episode_table(candidate_table, baseline_top, selector_fields, float(args.switch_margin))
    summary = build_summary(
        candidate_table,
        episode_table,
        selector_fields,
        float(args.min_association_rate),
        float(args.min_candidate_auc),
    )
    summary["per_query_auc"] = {
        field: per_query_auc(candidate_table, field)
        for field in [
            "O1_detector_max",
            "O5_node_extent",
            "O6_compact_extent",
            "O8_category_gate",
            "O9_category_best_gate",
        ]
    }
    summary["category_gate_reliable_queries"] = sorted(
        {
            str(row.get("query"))
            for row in candidate_table
            if row.get("category_gate_mode") == "detector"
        }
    )
    summary["category_best_gate_modes"] = {
        query: sorted({str(row.get("category_best_gate_mode")) for row in candidate_table if str(row.get("query")) == query})
        for query in sorted({str(row.get("query")) for row in candidate_table})
    }
    out = Path(args.out_root)
    write_jsonl(out / "detector_candidate_calibration.jsonl", candidate_table)
    write_jsonl(out / "detector_episode_calibration.jsonl", episode_table)
    write_json(out / "summary.json", summary)
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze v3c detector/mask association as a policy-facing signal.")
    parser.add_argument("--detector-root", required=True)
    parser.add_argument("--candidate-decisions", required=True)
    parser.add_argument("--out-root", required=True)
    parser.add_argument("--policy", default="NoReobserve")
    parser.add_argument("--min-association-rate", type=float, default=0.60)
    parser.add_argument("--min-candidate-auc", type=float, default=0.60)
    parser.add_argument("--switch-margin", type=float, default=0.10)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = run(args)
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
