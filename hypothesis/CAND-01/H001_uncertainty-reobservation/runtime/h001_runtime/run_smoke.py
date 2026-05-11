import argparse
import gzip
import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


SCHEMA_VERSION = "h001.navlog.v1"
SUCCESS_DISTANCE = 1.0
SEMANTIC_UNCERTAINTY_TRIGGER = 0.60
SEMANTIC_TIE_BAND = 0.01
SEMANTIC_REOBS_VIEW_BONUS = 1


@dataclass
class LoadedEpisode:
    dataset: str
    split: str
    shard: Path
    shard_data: Dict[str, Any]
    episode: Dict[str, Any]
    index: int
    manifest_row: Optional[Dict[str, Any]] = None


@dataclass
class Candidate:
    candidate_id: str
    category: str
    object_id: Optional[int]
    object_name: Optional[str]
    position: List[float]
    visit_position: List[float]
    visit_rotation: List[float]
    score: float
    view_count: int
    correct: Optional[bool] = None
    correct_source: str = "unlabeled"
    backend_name: str = "unknown"
    uses_gt_for_action: bool = False


def load_json_gz(path: Path) -> Dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return json.load(handle)


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def append_jsonl(path: Path, row: Dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def norm_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    value = float(value)
    if math.isinf(value) or math.isnan(value):
        return None
    return value


def mean(values: Iterable[Optional[float]]) -> Optional[float]:
    valid = [float(v) for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def dataset_root(data_root: Path, dataset: str) -> Path:
    if dataset == "hm3d_objectnav_v2":
        return data_root / "datasets" / "objectnav" / "hm3d" / "v2" / "objectnav_hm3d_v2"
    if dataset == "hm3d_ovon":
        return data_root / "datasets" / "ovon" / "hm3d"
    raise ValueError(f"unsupported dataset: {dataset}")


def query_type(dataset: str) -> str:
    return "open_vocabulary" if dataset == "hm3d_ovon" else "closed_class"


def target_for_episode(episode: Dict[str, Any]) -> str:
    return str(
        episode.get("object_category")
        or episode.get("object_name")
        or episode.get("goal_name")
        or episode.get("query")
        or "unknown"
    )


def episode_shards(data_root: Path, dataset: str, split: str) -> List[Path]:
    root = dataset_root(data_root, dataset) / split
    content = root / "content"
    if content.exists():
        shards = sorted(content.glob("*.json.gz"))
    else:
        shards = sorted(root.glob("*.json.gz"))
    return [path for path in shards if path.is_file()]


def load_episodes(data_root: Path, dataset: str, split: str, limit: int) -> List[LoadedEpisode]:
    loaded: List[LoadedEpisode] = []
    for shard in episode_shards(data_root, dataset, split):
        shard_data = load_json_gz(shard)
        for episode in shard_data.get("episodes", []):
            loaded.append(
                LoadedEpisode(
                    dataset=dataset,
                    split=split,
                    shard=shard,
                    shard_data=shard_data,
                    episode=episode,
                    index=len(loaded),
                )
            )
            if len(loaded) >= limit:
                return loaded
    return loaded


def load_manifest_episodes(data_root: Path, manifest: Path, selected_split: str, limit: int) -> List[LoadedEpisode]:
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    rows = [
        row
        for row in manifest_data.get("rows", [])
        if str(row.get("selected_split")) == selected_split
    ]
    if limit > 0:
        rows = rows[:limit]
    if not rows:
        raise ValueError(f"manifest has no rows for selected split: {selected_split}")

    shard_cache: Dict[Path, Dict[str, Any]] = {}
    loaded: List[LoadedEpisode] = []
    for row in rows:
        source = data_root / str(row["source_file"])
        if source not in shard_cache:
            shard_cache[source] = load_json_gz(source)
        shard_data = shard_cache[source]
        row_index = int(row["row_index"])
        episodes = shard_data.get("episodes", [])
        if row_index < 0 or row_index >= len(episodes):
            raise IndexError(f"manifest row_index out of range: {source}:{row_index}")
        episode = episodes[row_index]
        if str(episode.get("episode_id")) != str(row.get("source_episode_id")):
            raise ValueError(f"episode_id mismatch for manifest key: {row.get('episode_key')}")
        if target_for_episode(episode) != str(row.get("target_or_query")):
            raise ValueError(f"target mismatch for manifest key: {row.get('episode_key')}")
        loaded.append(
            LoadedEpisode(
                dataset=str(row["dataset"]),
                split=str(row["source_split"]),
                shard=source,
                shard_data=shard_data,
                episode=episode,
                index=len(loaded),
                manifest_row=row,
            )
        )
    return loaded


def scene_path(data_root: Path, scene_id: str) -> Path:
    normalized = "/".join(part for part in scene_id.split("/") if part)
    parts = normalized.split("/")
    if parts and parts[0] in {"hm3d", "hm3d_v0.2"}:
        parts = parts[1:]
    return data_root / "scene_datasets" / "hm3d" / Path(*parts)


def navmesh_path(scene: Path) -> Path:
    if scene.name.endswith(".basis.glb"):
        return scene.with_name(scene.name.replace(".basis.glb", ".basis.navmesh"))
    return scene.with_suffix(".navmesh")


def scene_basename(scene_id: str) -> str:
    normalized = "/".join(part for part in scene_id.split("/") if part)
    return Path(normalized).name


def manifest_fields(loaded: LoadedEpisode) -> Dict[str, Any]:
    row = loaded.manifest_row
    if row is None:
        return {
            "episode_key": None,
            "manifest_selected_split": None,
            "manifest_source_file": None,
            "manifest_row_index": None,
            "manifest_selection_rank": None,
            "manifest_deterministic_hash": None,
        }
    return {
        "episode_key": row.get("episode_key"),
        "manifest_selected_split": row.get("selected_split"),
        "manifest_source_file": row.get("source_file"),
        "manifest_row_index": row.get("row_index"),
        "manifest_selection_rank": row.get("selection_rank"),
        "manifest_deterministic_hash": row.get("deterministic_hash"),
    }


def goal_key_for(episode: Dict[str, Any], category: str) -> str:
    return f"{scene_basename(episode['scene_id'])}_{category}"


def goals_for_category(shard_data: Dict[str, Any], episode: Dict[str, Any], category: str) -> List[Dict[str, Any]]:
    goals_by_category = shard_data.get("goals_by_category", {})
    exact_key = goal_key_for(episode, category)
    if exact_key in goals_by_category:
        return list(goals_by_category[exact_key])

    suffix = f"_{category}"
    base = scene_basename(episode["scene_id"])
    for key, goals in goals_by_category.items():
        if key.endswith(suffix) and key.startswith(base):
            return list(goals)
    return []


def all_scene_goals(shard_data: Dict[str, Any], episode: Dict[str, Any]) -> List[Dict[str, Any]]:
    base = scene_basename(episode["scene_id"])
    rows: List[Dict[str, Any]] = []
    for key, goals in shard_data.get("goals_by_category", {}).items():
        if key.startswith(base):
            rows.extend(goals)
    return rows


def best_viewpoint(goal: Dict[str, Any]) -> Tuple[List[float], List[float], int]:
    viewpoints = list(goal.get("view_points") or [])
    if not viewpoints:
        return list(goal["position"]), [0.0, 0.0, 0.0, 1.0], 0
    best = max(viewpoints, key=lambda vp: float(vp.get("iou") or 0.0))
    state = best.get("agent_state", {})
    return (
        [float(v) for v in state.get("position", goal["position"])],
        [float(v) for v in state.get("rotation", [0.0, 0.0, 0.0, 1.0])],
        len(viewpoints),
    )


def candidate_from_goal(goal: Dict[str, Any], score: float, correct: bool, backend_name: str) -> Candidate:
    visit_position, visit_rotation, view_count = best_viewpoint(goal)
    category = str(goal.get("object_category") or "unknown")
    object_id = goal.get("object_id")
    return Candidate(
        candidate_id=f"goal:{category}:{object_id if object_id is not None else goal.get('object_name', 'unknown')}",
        category=category,
        object_id=object_id,
        object_name=goal.get("object_name"),
        position=[float(v) for v in goal["position"]],
        visit_position=visit_position,
        visit_rotation=visit_rotation,
        score=float(score),
        view_count=view_count,
        correct=bool(correct),
        correct_source="gt_instance",
        backend_name=backend_name,
        uses_gt_for_action=True,
    )


class CandidateBackend:
    name = "base"
    uses_gt_for_action = False

    def candidates_for(self, loaded: LoadedEpisode) -> List[Candidate]:
        raise NotImplementedError


class DiagnosticGTBackend(CandidateBackend):
    name = "diagnostic_gt"
    uses_gt_for_action = True

    def __init__(self, name: str = "diagnostic_gt") -> None:
        self.name = name

    def candidates_for(self, loaded: LoadedEpisode) -> List[Candidate]:
        episode = loaded.episode
        query = str(episode.get("object_category") or "")
        correct_goals = goals_for_category(loaded.shard_data, episode, query)
        wrong_goals = [
            goal
            for goal in all_scene_goals(loaded.shard_data, episode)
            if goal.get("object_category") != query
        ]

        candidates: List[Candidate] = []
        wrong_first = bool(wrong_goals) and sum(ord(ch) for ch in str(episode.get("episode_id", ""))) % 2 == 1

        if correct_goals:
            closest_goal_object_id = episode.get("info", {}).get("closest_goal_object_id")
            if closest_goal_object_id is not None:
                correct_goal = next(
                    (
                        goal
                        for goal in correct_goals
                        if str(goal.get("object_id")) == str(closest_goal_object_id)
                    ),
                    correct_goals[0],
                )
            else:
                correct_goal = correct_goals[0]
            correct_score = 0.70 if wrong_first else 0.82
            candidates.append(candidate_from_goal(correct_goal, correct_score, True, self.name))
        if wrong_goals:
            wrong_score = 0.74 if wrong_first else 0.64
            candidates.append(candidate_from_goal(wrong_goals[0], wrong_score, False, self.name))

        candidates.sort(key=lambda cand: cand.score, reverse=True)
        return candidates[:4]


class ArtifactJSONLBackend(CandidateBackend):
    name = "artifact_jsonl"
    uses_gt_for_action = False

    def __init__(self, artifact: Path) -> None:
        self.artifact = artifact
        self.index: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self._load()

    def _load(self) -> None:
        if not self.artifact.exists():
            raise FileNotFoundError(f"candidate artifact not found: {self.artifact}")
        with self.artifact.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                scene = str(row.get("scene_id") or row.get("scene") or "")
                scene_key = scene_basename(scene) if scene else str(row.get("scene_key") or "")
                query = str(row.get("query") or row.get("object_category") or "")
                if not scene_key or not query:
                    continue
                if "candidates" in row:
                    candidates = list(row["candidates"])
                else:
                    candidates = [row]
                self.index.setdefault((scene_key, query), []).extend(candidates)

    def candidates_for(self, loaded: LoadedEpisode) -> List[Candidate]:
        episode = loaded.episode
        query = str(episode.get("object_category") or "")
        scene_key = scene_basename(episode["scene_id"])
        rows = self.index.get((scene_key, query), [])
        candidates = [self._candidate_from_row(row, scene_key, query, i) for i, row in enumerate(rows)]
        candidates.sort(key=lambda cand: cand.score, reverse=True)
        return candidates

    def _candidate_from_row(self, row: Dict[str, Any], scene_key: str, query: str, index: int) -> Candidate:
        position = (
            row.get("position")
            or row.get("map_position")
            or row.get("candidate_position")
            or row.get("centroid")
        )
        if position is None:
            raise ValueError(f"candidate row missing position for {scene_key}/{query}: {row}")
        visit_position = row.get("visit_position") or row.get("reachable_viewpoint") or position
        visit_rotation = row.get("visit_rotation") or row.get("viewpoint_rotation") or [0.0, 0.0, 0.0, 1.0]
        candidate_id = str(row.get("candidate_id") or f"{self.name}:{scene_key}:{query}:{index}")
        category = str(row.get("category") or row.get("class_or_text_label") or row.get("label") or query)
        score = float(row.get("score", row.get("semantic_score", row.get("confidence", 0.0))))
        view_count = int(row.get("view_count", row.get("observation_count", 0)) or 0)
        return Candidate(
            candidate_id=candidate_id,
            category=category,
            object_id=row.get("object_id"),
            object_name=row.get("object_name"),
            position=[float(v) for v in position],
            visit_position=[float(v) for v in visit_position],
            visit_rotation=[float(v) for v in visit_rotation],
            score=score,
            view_count=view_count,
            backend_name=self.name,
            uses_gt_for_action=False,
        )


def build_candidate_backend(name: str, artifact: Optional[str]) -> CandidateBackend:
    if name == "diagnostic_gt":
        return DiagnosticGTBackend()
    if name == "artifact_jsonl":
        if artifact is None:
            raise ValueError("--candidate-artifact is required for artifact_jsonl backend")
        return ArtifactJSONLBackend(Path(artifact))
    raise ValueError(f"unsupported candidate backend: {name}")


def euclidean(a: List[float], b: List[float]) -> float:
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def label_candidate_correctness(loaded: LoadedEpisode, candidates: List[Candidate]) -> None:
    query = str(loaded.episode.get("object_category") or "")
    valid_goals = goals_for_category(loaded.shard_data, loaded.episode, query)
    valid_object_ids = {str(goal.get("object_id")) for goal in valid_goals if goal.get("object_id") is not None}

    for candidate in candidates:
        if candidate.correct_source == "gt_instance":
            continue
        if candidate.object_id is not None and str(candidate.object_id) in valid_object_ids:
            candidate.correct = True
            candidate.correct_source = "gt_instance"
            continue
        if candidate.category != query:
            candidate.correct = False
            candidate.correct_source = "gt_category"
            continue
        candidate_points = [candidate.position]
        if candidate.visit_position != candidate.position:
            candidate_points.append(candidate.visit_position)
        candidate.correct = any(
            euclidean(point, [float(v) for v in goal["position"]]) <= SUCCESS_DISTANCE
            for point in candidate_points
            for goal in valid_goals
        )
        candidate.correct_source = "gt_position_radius"


class SceneCache:
    def __init__(self) -> None:
        self._scene: Optional[Path] = None
        self._sim: Any = None

    def close(self) -> None:
        if self._sim is not None:
            self._sim.close()
        self._scene = None
        self._sim = None

    def sim_for(self, scene: Path) -> Any:
        if self._sim is not None and self._scene == scene:
            return self._sim
        self.close()

        import habitat_sim

        sim_cfg = habitat_sim.SimulatorConfiguration()
        sim_cfg.scene_id = str(scene)
        sim_cfg.enable_physics = False

        agent_cfg = habitat_sim.agent.AgentConfiguration()
        agent_cfg.sensor_specifications = []

        self._sim = habitat_sim.Simulator(habitat_sim.Configuration(sim_cfg, [agent_cfg]))
        self._scene = scene
        navmesh = navmesh_path(scene)
        if navmesh.exists() and not self._sim.pathfinder.is_loaded:
            self._sim.pathfinder.load_nav_mesh(str(navmesh))
        return self._sim

    def distance(self, scene: Path, start: List[float], end: List[float]) -> Optional[float]:
        import habitat_sim
        import numpy as np

        sim = self.sim_for(scene)
        path = habitat_sim.ShortestPath()
        path.requested_start = np.array(start, dtype=np.float32)
        path.requested_end = np.array(end, dtype=np.float32)
        if not sim.pathfinder.find_path(path):
            return None
        return norm_float(path.geodesic_distance)

    def random_navigable_point(self, scene: Path, seed: int) -> List[float]:
        sim = self.sim_for(scene)
        sim.seed(seed)
        point = sim.pathfinder.get_random_navigable_point()
        return [float(v) for v in point]


def shortest_correct_path(cache: SceneCache, scene: Path, start: List[float], candidates: List[Candidate], episode: Dict[str, Any]) -> Optional[float]:
    metadata_distance = norm_float(episode.get("info", {}).get("geodesic_distance"))
    if metadata_distance is not None:
        return metadata_distance

    distances = [
        cache.distance(scene, start, cand.visit_position)
        for cand in candidates
        if cand.correct is True
    ]
    valid = [distance for distance in distances if distance is not None]
    if valid:
        return min(valid)
    return norm_float(episode.get("info", {}).get("geodesic_distance"))


def uncertainty_fields(candidate: Candidate, candidates: List[Candidate], extra_view_count: int = 0) -> Dict[str, float]:
    scores = sorted([cand.score for cand in candidates], reverse=True)
    top1 = scores[0] if scores else candidate.score
    top2 = scores[1] if len(scores) > 1 else 0.0
    score_uncertainty = max(0.0, min(1.0, 1.0 - candidate.score))
    margin_uncertainty = max(0.0, min(1.0, 1.0 - max(0.0, top1 - top2)))
    view_count = max(0, candidate.view_count + extra_view_count)
    support_uncertainty = max(0.0, min(1.0, 1.0 - min(view_count, 25) / 25.0))
    u_sem = (score_uncertainty + margin_uncertainty + support_uncertainty) / 3.0
    return {
        "top1_score": top1,
        "top2_score": top2,
        "score_uncertainty": score_uncertainty,
        "margin_uncertainty": margin_uncertainty,
        "view_count_uncertainty": support_uncertainty,
        "U_sem": u_sem,
    }


def candidate_log_row(
    run_id: str,
    loaded: LoadedEpisode,
    policy: str,
    candidate: Candidate,
    candidates: List[Candidate],
    decision_step: int,
    selected_for_goal: bool,
    selected_for_reobserve: bool,
    explicit_commit: bool,
    path_to_candidate: Optional[float],
    wrong_goal_visit: bool,
) -> Dict[str, Any]:
    episode = loaded.episode
    fields = uncertainty_fields(candidate, candidates)
    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "episode_id": str(episode.get("episode_id")),
        "policy": policy,
        "decision_step": decision_step,
        "scene_id": episode.get("scene_id"),
        "query": episode.get("object_category"),
        "candidate_id": candidate.candidate_id,
        "candidate_backend": candidate.backend_name,
        "candidate_uses_gt_for_action": candidate.uses_gt_for_action,
        "candidate_rank": candidates.index(candidate) + 1,
        "candidate_position": candidate.position,
        "candidate_score": candidate.score,
        "top1_score": fields["top1_score"],
        "top2_score": fields["top2_score"],
        "score_uncertainty": fields["score_uncertainty"],
        "margin_uncertainty": fields["margin_uncertainty"],
        "view_count_uncertainty": fields["view_count_uncertainty"],
        "view_diversity_uncertainty": None,
        "visibility_uncertainty": None,
        "size_support_uncertainty": None,
        "spatial_ambiguity_uncertainty": None,
        "U_sem": fields["U_sem"],
        "trigger_reobserve": fields["U_sem"] >= SEMANTIC_UNCERTAINTY_TRIGGER,
        "commit_without_reobserve": explicit_commit and not selected_for_reobserve,
        "selected_for_goal": selected_for_goal,
        "selected_for_reobserve": selected_for_reobserve,
        "candidate_correct": candidate.correct,
        "candidate_correct_source": candidate.correct_source,
        "candidate_reachable": path_to_candidate is not None if selected_for_goal else None,
        "goal_visit": explicit_commit and selected_for_goal,
        "wrong_goal_visit": wrong_goal_visit,
        "wrong_goal_pass_through": False,
        "explicit_commit": explicit_commit,
        "path_to_candidate": path_to_candidate,
        "path_after_candidate": None,
        "wasted_path_from_candidate": path_to_candidate if wrong_goal_visit else 0.0,
    }
    row.update(manifest_fields(loaded))
    return row


def rank_of(candidate: Candidate, candidates: List[Candidate]) -> int:
    return candidates.index(candidate) + 1


def select_semantic_reobserve_candidate(
    cache: SceneCache,
    scene: Path,
    start: List[float],
    candidates: List[Candidate],
) -> Tuple[Candidate, Optional[float], bool, List[Tuple[Candidate, Optional[float]]]]:
    top = candidates[0]
    top_fields = uncertainty_fields(top, candidates)
    paths = [(cand, cache.distance(scene, start, cand.visit_position)) for cand in candidates]
    if top_fields["U_sem"] < SEMANTIC_UNCERTAINTY_TRIGGER:
        top_path = next(path for cand, path in paths if cand == top)
        return top, top_path, False, paths

    min_score = top.score - SEMANTIC_TIE_BAND
    eligible = [(cand, path) for cand, path in paths if cand.score >= min_score and path is not None]
    if not eligible:
        top_path = next(path for cand, path in paths if cand == top)
        return top, top_path, False, paths

    selected, selected_path = min(
        eligible,
        key=lambda item: (float(item[1]), -item[0].score, rank_of(item[0], candidates)),
    )
    return selected, selected_path, True, paths


def episode_log_row(
    run_id: str,
    loaded: LoadedEpisode,
    policy: str,
    success: bool,
    spl: Optional[float],
    path_length_total: Optional[float],
    p_star: Optional[float],
    reobservations: int,
    commits: int,
    wrong_goal_visit: bool,
    wasted_wrong: Optional[float],
    wasted_reobserve: Optional[float],
    final_candidate: Optional[Candidate],
    termination_reason: str,
) -> Dict[str, Any]:
    episode = loaded.episode
    if path_length_total is None or p_star is None:
        wasted_total = None
        wasted_other = None
    elif not success:
        wasted_total = max(0.0, (wasted_wrong or 0.0) + (wasted_reobserve or 0.0))
        wasted_other = 0.0
    else:
        wasted_total = max(0.0, path_length_total - p_star)
        used = (wasted_wrong or 0.0) + (wasted_reobserve or 0.0)
        wasted_other = max(0.0, wasted_total - used)

    row = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "episode_id": str(episode.get("episode_id")),
        "dataset": loaded.dataset,
        "split": loaded.split,
        "scene_id": episode.get("scene_id"),
        "query": episode.get("object_category"),
        "query_type": query_type(loaded.dataset),
        "policy": policy,
        "start_position": episode.get("start_position"),
        "start_rotation": episode.get("start_rotation"),
        "success": success,
        "spl": spl,
        "soft_spl": None,
        "distance_to_success": 0.0 if success else None,
        "path_length_total": path_length_total,
        "shortest_path_to_success": p_star,
        "num_reobservations": reobservations,
        "num_candidate_commits": commits,
        "num_wrong_goal_visits": 1 if wrong_goal_visit else 0,
        "wrong_goal_visit": wrong_goal_visit,
        "wrong_goal_pass_through": False,
        "wasted_path_total": wasted_total,
        "wasted_path_wrong_goal": wasted_wrong,
        "wasted_path_reobserve": wasted_reobserve,
        "wasted_path_other": wasted_other,
        "final_goal_candidate_id": final_candidate.candidate_id if final_candidate else None,
        "final_goal_candidate_backend": final_candidate.backend_name if final_candidate else None,
        "final_goal_candidate_uses_gt_for_action": final_candidate.uses_gt_for_action if final_candidate else None,
        "final_goal_correct": final_candidate.correct if final_candidate else False,
        "gt_nearest_target_distance": p_star,
        "gt_shortest_path_to_target": p_star,
        "termination_reason": termination_reason,
    }
    row.update(manifest_fields(loaded))
    return row


def run_policy(
    cache: SceneCache,
    data_root: Path,
    loaded: LoadedEpisode,
    policy: str,
    run_id: str,
    seed: int,
    candidate_backend: CandidateBackend,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    episode = loaded.episode
    start = [float(v) for v in episode["start_position"]]
    scene = scene_path(data_root, episode["scene_id"])
    policy_candidate_backend = DiagnosticGTBackend(name="gt_target_oracle") if policy == "GTTargetOracle" else candidate_backend
    candidates = policy_candidate_backend.candidates_for(loaded)
    label_candidate_correctness(loaded, candidates)
    if not scene.exists() or not candidates:
        row = episode_log_row(run_id, loaded, policy, False, 0.0, None, None, 0, 0, False, None, None, None, "no_candidate")
        return row, [], []

    p_star = shortest_correct_path(cache, scene, start, candidates, episode)
    wrong_min_path = max(1.0, 0.10 * p_star) if p_star is not None else 1.0

    candidate_rows: List[Dict[str, Any]] = []
    viewpoint_rows: List[Dict[str, Any]] = []

    if policy == "GTTargetOracle":
        correct = [cand for cand in candidates if cand.correct is True]
        selected = correct[0] if correct else None
        path = p_star
        success = selected is not None and path is not None
        spl = 1.0 if success else 0.0
        for cand in candidates:
            selected_for_goal = cand == selected
            candidate_rows.append(
                candidate_log_row(
                    run_id,
                    loaded,
                    policy,
                    cand,
                    candidates,
                    0,
                    selected_for_goal,
                    False,
                    selected_for_goal,
                    path if selected_for_goal else None,
                    False,
                )
            )
        return (
            episode_log_row(run_id, loaded, policy, success, spl, path, p_star, 0, 1 if success else 0, False, 0.0, 0.0, selected, "success" if success else "unreachable"),
            candidate_rows,
            viewpoint_rows,
        )

    selected = candidates[0]
    selected_path = cache.distance(scene, start, selected.visit_position)
    reobserve_path = 0.0
    path_after_reobserve = selected_path
    reobservations = 0
    selected_for_reobserve: Optional[Candidate] = None

    if policy == "RandomReobserve":
        reobservations = 1
        viewpoint = cache.random_navigable_point(scene, seed + loaded.index)
        reobserve_path = cache.distance(scene, start, viewpoint) or 0.0
        path_after_reobserve = cache.distance(scene, viewpoint, selected.visit_position)
        viewpoint_row = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "episode_id": str(episode.get("episode_id")),
            "policy": policy,
            "decision_step": 0,
            "scene_id": episode.get("scene_id"),
            "query": episode.get("object_category"),
            "candidate_id": selected.candidate_id,
            "viewpoint_id": f"random:{loaded.index}",
            "viewpoint_position": viewpoint,
            "viewpoint_rotation": [0.0, 0.0, 0.0, 1.0],
            "viewpoint_policy": "RandomReobserve",
            "semantic_gain_pred": None,
            "slam_gain_pred": None,
            "travel_cost_pred": None,
            "travel_cost_actual": reobserve_path,
            "observation_success": path_after_reobserve is not None,
            "candidate_score_before": selected.score,
            "candidate_score_after": selected.score,
            "U_sem_before": uncertainty_fields(selected, candidates)["U_sem"],
            "U_sem_after": uncertainty_fields(selected, candidates)["U_sem"],
            "candidate_rank_before": 1,
            "candidate_rank_after": 1,
            "commit_after_reobserve": True,
            "final_candidate_changed": False,
        }
        viewpoint_row.update(manifest_fields(loaded))
        viewpoint_rows.append(viewpoint_row)
        selected_for_reobserve = selected

    if policy == "SemanticOnly":
        top = candidates[0]
        selected, selected_path, triggered, candidate_paths = select_semantic_reobserve_candidate(
            cache,
            scene,
            start,
            candidates,
        )
        if triggered:
            reobservations = 1
            selected_for_reobserve = selected
            reobserve_path = selected_path or 0.0
            path_after_reobserve = 0.0 if selected_path is not None else None
            before_fields = uncertainty_fields(top, candidates)
            after_fields = uncertainty_fields(selected, candidates, extra_view_count=SEMANTIC_REOBS_VIEW_BONUS)
            viewpoint_row = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "episode_id": str(episode.get("episode_id")),
                "policy": policy,
                "decision_step": 0,
                "scene_id": episode.get("scene_id"),
                "query": episode.get("object_category"),
                "candidate_id": selected.candidate_id,
                "viewpoint_id": f"semantic_uncertainty:{loaded.index}:{rank_of(selected, candidates)}",
                "viewpoint_position": selected.visit_position,
                "viewpoint_rotation": selected.visit_rotation,
                "viewpoint_policy": "SemanticUncertainty",
                "semantic_gain_pred": before_fields["U_sem"] - after_fields["U_sem"],
                "slam_gain_pred": None,
                "travel_cost_pred": selected_path,
                "travel_cost_actual": reobserve_path,
                "observation_success": selected_path is not None,
                "candidate_score_before": top.score,
                "candidate_score_after": selected.score,
                "U_sem_before": before_fields["U_sem"],
                "U_sem_after": after_fields["U_sem"],
                "candidate_rank_before": 1,
                "candidate_rank_after": rank_of(selected, candidates),
                "commit_after_reobserve": selected_path is not None,
                "final_candidate_changed": selected != top,
                "semantic_uncertainty_trigger": SEMANTIC_UNCERTAINTY_TRIGGER,
                "semantic_tie_band": SEMANTIC_TIE_BAND,
                "reachable_tie_candidates": sum(
                    1
                    for cand, path in candidate_paths
                    if cand.score >= top.score - SEMANTIC_TIE_BAND and path is not None
                ),
            }
            viewpoint_row.update(manifest_fields(loaded))
            viewpoint_rows.append(viewpoint_row)
        else:
            path_after_reobserve = selected_path

    commit_path = path_after_reobserve
    path_length_total = None if commit_path is None else reobserve_path + commit_path
    success = bool(selected.correct is True and path_length_total is not None)
    spl = 0.0
    if success and p_star is not None and path_length_total is not None:
        spl = p_star / max(p_star, path_length_total)

    wrong_goal_commit_distance = path_length_total if policy == "SemanticOnly" and reobservations else commit_path
    wrong_goal_visit = bool(
        selected.correct is False
        and wrong_goal_commit_distance is not None
        and wrong_goal_commit_distance >= wrong_min_path
    )
    wasted_wrong = wrong_goal_commit_distance if wrong_goal_visit else 0.0
    wasted_reobserve = 0.0 if policy == "SemanticOnly" else (reobserve_path if reobservations else 0.0)

    for cand in candidates:
        selected_for_goal = cand == selected
        candidate_rows.append(
            candidate_log_row(
                run_id,
                loaded,
                policy,
                cand,
                candidates,
                0,
                selected_for_goal,
                selected_for_reobserve is not None and cand == selected_for_reobserve,
                selected_for_goal,
                (wrong_goal_commit_distance if policy == "SemanticOnly" else commit_path) if selected_for_goal else None,
                wrong_goal_visit if selected_for_goal else False,
            )
        )

    termination = "success" if success else "timeout"
    return (
        episode_log_row(
            run_id,
            loaded,
            policy,
            success,
            spl,
            path_length_total,
            p_star,
            reobservations,
            1 if path_length_total is not None else 0,
            wrong_goal_visit,
            wasted_wrong,
            wasted_reobserve,
            selected,
            termination,
        ),
        candidate_rows,
        viewpoint_rows,
    )


def aggregate(episode_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    by_policy: Dict[str, List[Dict[str, Any]]] = {}
    for row in episode_rows:
        by_policy.setdefault(row["policy"], []).append(row)

    result: Dict[str, Any] = {}
    for policy, rows in sorted(by_policy.items()):
        result[policy] = {
            "episodes": len(rows),
            "success_rate": mean(1.0 if row["success"] else 0.0 for row in rows),
            "mean_spl": mean(row.get("spl") for row in rows),
            "wrong_goal_visit_rate": mean(1.0 if row["wrong_goal_visit"] else 0.0 for row in rows),
            "mean_wasted_path_total": mean(row.get("wasted_path_total") for row in rows),
            "mean_wasted_path_wrong_goal": mean(row.get("wasted_path_wrong_goal") for row in rows),
            "mean_wasted_path_reobserve": mean(row.get("wasted_path_reobserve") for row in rows),
            "mean_num_reobservations": mean(float(row.get("num_reobservations", 0)) for row in rows),
        }
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run H001 log-schema smoke harness.")
    parser.add_argument("--data-root", default="/data")
    parser.add_argument("--dataset", default="hm3d_objectnav_v2", choices=["hm3d_objectnav_v2", "hm3d_ovon"])
    parser.add_argument("--split", default="val")
    parser.add_argument("--episodes", type=int, default=3)
    parser.add_argument("--manifest", default=None, help="Optional fixed split manifest JSON.")
    parser.add_argument("--manifest-split", default="smoke", help="Selected split name inside --manifest.")
    parser.add_argument("--policies", nargs="+", default=["GTTargetOracle", "NoReobserve", "RandomReobserve"])
    parser.add_argument("--out", default="/runs/h001_smoke")
    parser.add_argument("--run-id", default="h001_smoke")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--candidate-backend", default="diagnostic_gt", choices=["diagnostic_gt", "artifact_jsonl"])
    parser.add_argument("--candidate-artifact", default=None)
    parser.add_argument("--semantic-uncertainty-trigger", type=float, default=SEMANTIC_UNCERTAINTY_TRIGGER)
    parser.add_argument("--semantic-tie-band", type=float, default=SEMANTIC_TIE_BAND)
    parser.add_argument("--semantic-reobs-view-bonus", type=int, default=SEMANTIC_REOBS_VIEW_BONUS)
    return parser.parse_args()


def main() -> None:
    global SEMANTIC_REOBS_VIEW_BONUS, SEMANTIC_TIE_BAND, SEMANTIC_UNCERTAINTY_TRIGGER

    args = parse_args()
    SEMANTIC_UNCERTAINTY_TRIGGER = float(args.semantic_uncertainty_trigger)
    SEMANTIC_TIE_BAND = float(args.semantic_tie_band)
    SEMANTIC_REOBS_VIEW_BONUS = int(args.semantic_reobs_view_bonus)

    data_root = Path(args.data_root).resolve()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    episode_log = out / "episodes.jsonl"
    candidate_log = out / "candidate_decisions.jsonl"
    viewpoint_log = out / "viewpoint_decisions.jsonl"
    for path in [episode_log, candidate_log, viewpoint_log]:
        path.write_text("", encoding="utf-8")

    if args.manifest:
        loaded_episodes = load_manifest_episodes(data_root, Path(args.manifest), args.manifest_split, args.episodes)
    else:
        loaded_episodes = load_episodes(data_root, args.dataset, args.split, args.episodes)
    if not loaded_episodes:
        source = f"manifest {args.manifest}/{args.manifest_split}" if args.manifest else f"{args.dataset}/{args.split}"
        raise SystemExit(f"no episodes found for {source}")

    candidate_backend = build_candidate_backend(args.candidate_backend, args.candidate_artifact)

    random.seed(args.seed)
    cache = SceneCache()
    episode_rows: List[Dict[str, Any]] = []
    candidate_count = 0
    viewpoint_count = 0
    try:
        for loaded in loaded_episodes:
            for policy in args.policies:
                episode_row, candidate_rows, viewpoint_rows = run_policy(
                    cache,
                    data_root,
                    loaded,
                    policy,
                    args.run_id,
                    args.seed,
                    candidate_backend,
                )
                append_jsonl(episode_log, episode_row)
                for row in candidate_rows:
                    append_jsonl(candidate_log, row)
                for row in viewpoint_rows:
                    append_jsonl(viewpoint_log, row)
                episode_rows.append(episode_row)
                candidate_count += len(candidate_rows)
                viewpoint_count += len(viewpoint_rows)
    finally:
        cache.close()

    loaded_datasets = sorted({episode.dataset for episode in loaded_episodes})
    loaded_source_splits = sorted({episode.split for episode in loaded_episodes})
    loaded_manifest_splits = sorted(
        {
            str(episode.manifest_row.get("selected_split"))
            for episode in loaded_episodes
            if episode.manifest_row is not None
        }
    )

    summary = {
        "schema_version": SCHEMA_VERSION,
        "run_id": args.run_id,
        "dataset": loaded_datasets[0] if len(loaded_datasets) == 1 else loaded_datasets,
        "split": loaded_source_splits[0] if len(loaded_source_splits) == 1 else loaded_source_splits,
        "requested_dataset": args.dataset,
        "requested_split": args.split,
        "manifest": str(args.manifest) if args.manifest else None,
        "manifest_split": args.manifest_split if args.manifest else None,
        "loaded_datasets": loaded_datasets,
        "loaded_source_splits": loaded_source_splits,
        "loaded_manifest_splits": loaded_manifest_splits,
        "episodes_requested": args.episodes,
        "episodes_loaded": len(loaded_episodes),
        "policies": args.policies,
        "candidate_backend": candidate_backend.name,
        "candidate_backend_uses_gt_for_action": candidate_backend.uses_gt_for_action,
        "candidate_artifact": str(args.candidate_artifact) if args.candidate_artifact else None,
        "semantic_uncertainty_trigger": SEMANTIC_UNCERTAINTY_TRIGGER,
        "semantic_tie_band": SEMANTIC_TIE_BAND,
        "semantic_reobs_view_bonus": SEMANTIC_REOBS_VIEW_BONUS,
        "episode_rows": len(episode_rows),
        "candidate_decision_rows": candidate_count,
        "viewpoint_decision_rows": viewpoint_count,
        "aggregate": aggregate(episode_rows),
        "notes": [
            "diagnostic GT-assisted backend is for smoke only; artifact_jsonl is the non-GT adapter boundary",
            "not a paper result",
            "used to validate log schema, GT references, and baseline comparability",
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
