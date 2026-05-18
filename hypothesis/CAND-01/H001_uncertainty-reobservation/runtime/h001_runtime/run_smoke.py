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
SEMANTIC_DELTA_SWITCH_SCORE = 0.03
SEMANTIC_DELTA_SWITCH_UNCERTAINTY = 0.05
SEMANTIC_EVIDENCE_MODE = "support_proxy"
SEMANTIC_MAX_REOBSERVATIONS = 1
SEMANTIC_POSTVIEW_SCORE_ARTIFACT: Optional[Path] = None
SEMANTIC_IMAGE_SCORE_RULE = "raw_delta"
SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE = True
RISK_OBJECT_NODE_FEATURE_ARTIFACT: Optional[Path] = None
RISK_TOTAL_TRIGGER = 0.60
RISK_CONTRADICTION_SCALE = 0.25
RISK_RESOLUTION_DELTA_TRIGGER = 0.05
RISK_RESOLUTION_MAX_RISK = 0.95
RISK_RESOLUTION_MAX_CONTRADICTION = 0.25
RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT = True
RISK_POLICIES = {"RiskOnlyReobserve", "RiskResolutionReobserve"}


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


def safe_float(value: Any) -> Optional[float]:
    try:
        return norm_float(value)
    except (TypeError, ValueError):
        return None


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "f", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected boolean value, got {value!r}")


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


class PostviewScoreIndex:
    def __init__(self, artifact: Path) -> None:
        self.artifact = artifact
        self.rows: List[Dict[str, Any]] = []
        self.by_episode_key: Dict[str, List[Dict[str, Any]]] = {}
        self.by_episode_scene_query: Dict[Tuple[str, str, str], List[Dict[str, Any]]] = {}
        self.uses_gt_for_action = False
        self._load()

    def _load(self) -> None:
        if not self.artifact.exists():
            raise FileNotFoundError(f"post-view score artifact not found: {self.artifact}")
        with self.artifact.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("uses_gt_for_action") is not False:
                    raise ValueError(f"post-view score row must have uses_gt_for_action=false: {row.get('decision_id')}")
                self.rows.append(row)
                episode_key = row.get("episode_key")
                if episode_key is not None:
                    self.by_episode_key.setdefault(str(episode_key), []).append(row)
                episode_id = str(row.get("episode_id"))
                scene_key = scene_basename(str(row.get("scene_id") or ""))
                query = str(row.get("query") or "")
                if episode_id and scene_key and query:
                    self.by_episode_scene_query.setdefault((episode_id, scene_key, query), []).append(row)

    def find(self, loaded: LoadedEpisode, query: str, candidate_id: str) -> Optional[Dict[str, Any]]:
        fields = manifest_fields(loaded)
        rows: List[Dict[str, Any]] = []
        episode_key = fields.get("episode_key")
        if episode_key is not None:
            rows.extend(self.by_episode_key.get(str(episode_key), []))
        if not rows:
            key = (
                str(loaded.episode.get("episode_id")),
                scene_basename(str(loaded.episode.get("scene_id") or "")),
                query,
            )
            rows.extend(self.by_episode_scene_query.get(key, []))
        if not rows:
            return None

        matching_query = [row for row in rows if str(row.get("query") or "") == query]
        rows = matching_query or rows
        for row in rows:
            if candidate_id in postview_candidate_scores(row):
                return row
        return rows[0]


class ObjectNodeFeatureIndex:
    def __init__(self, artifact: Path) -> None:
        self.artifact = artifact
        self.by_episode_candidate: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.by_scene_query_candidate: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        self.rows = 0
        self.uses_gt_for_action = False
        self._load()

    def _load(self) -> None:
        if not self.artifact.exists():
            raise FileNotFoundError(f"object-node feature artifact not found: {self.artifact}")
        with self.artifact.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("uses_gt_for_action") is not False:
                    raise ValueError(f"object-node feature row must have uses_gt_for_action=false: {row.get('episode_key')}")
                self.rows += 1
                episode_key = row.get("episode_key")
                candidate_id = row.get("candidate_id")
                if episode_key is not None and candidate_id is not None:
                    self.by_episode_candidate[(str(episode_key), str(candidate_id))] = row
                scene_key = scene_basename(str(row.get("scene_id") or ""))
                query = str(row.get("query") or "")
                if scene_key and query and candidate_id is not None:
                    self.by_scene_query_candidate[(scene_key, query, str(candidate_id))] = row

    def find(self, loaded: LoadedEpisode, query: str, candidate_id: str) -> Optional[Dict[str, Any]]:
        fields = manifest_fields(loaded)
        episode_key = fields.get("episode_key")
        if episode_key is not None:
            row = self.by_episode_candidate.get((str(episode_key), candidate_id))
            if row is not None:
                return row
        scene_key = scene_basename(str(loaded.episode.get("scene_id") or ""))
        return self.by_scene_query_candidate.get((scene_key, query, candidate_id))


def build_candidate_backend(name: str, artifact: Optional[str]) -> CandidateBackend:
    if name == "diagnostic_gt":
        return DiagnosticGTBackend()
    if name == "artifact_jsonl":
        if artifact is None:
            raise ValueError("--candidate-artifact is required for artifact_jsonl backend")
        return ArtifactJSONLBackend(Path(artifact))
    raise ValueError(f"unsupported candidate backend: {name}")


def postview_candidate_scores(row: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(score.get("candidate_id")): score
        for score in row.get("candidate_scores", [])
        if score.get("candidate_id") is not None
    }


def postview_score_value(score_row: Optional[Dict[str, Any]]) -> Optional[float]:
    if not score_row:
        return None
    raw = safe_float(score_row.get("raw_image_text_score"))
    if raw is not None:
        return raw
    return safe_float(score_row.get("score_after"))


def postview_support_delta(score_row: Optional[Dict[str, Any]]) -> float:
    value = safe_float(score_row.get("support_delta") if score_row else None)
    return float(value) if value is not None else 0.0


def postview_u_sem(score_row: Optional[Dict[str, Any]], fallback: float) -> float:
    value = safe_float(score_row.get("U_sem_after") if score_row else None)
    return float(value) if value is not None else float(fallback)


def postview_projection_status(score_row: Optional[Dict[str, Any]]) -> str:
    if not score_row:
        return "missing_frame"
    return str(score_row.get("projection_status") or "missing_frame")


def postview_score_source(score_row: Optional[Dict[str, Any]]) -> str:
    if not score_row:
        return "not_used"
    return str(score_row.get("score_source") or "not_used")


def postview_score_calibration(score_row: Optional[Dict[str, Any]]) -> Optional[str]:
    if not score_row:
        return None
    value = score_row.get("score_calibration")
    return str(value) if value is not None else None


def postview_action_eligible(score_row: Optional[Dict[str, Any]]) -> bool:
    if not score_row:
        return False
    if SEMANTIC_IMAGE_SCORE_RULE == "agg_local_delta":
        return (
            score_row.get("action_eligible") is True
            and score_row.get("center_fallback_used_for_action") is not True
        )
    return True


def image_feature_score_value(candidate: Candidate, score_row: Optional[Dict[str, Any]]) -> Optional[float]:
    if SEMANTIC_IMAGE_SCORE_RULE == "raw_delta":
        return postview_score_value(score_row)
    if SEMANTIC_IMAGE_SCORE_RULE == "agg_local_delta":
        if not postview_action_eligible(score_row):
            return None
        return postview_score_value(score_row)
    raise ValueError(f"unsupported semantic image score rule: {SEMANTIC_IMAGE_SCORE_RULE}")


def object_node_support(feature_row: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    if not feature_row:
        return {
            "S_det": 0.0,
            "S_proj": 0.0,
            "S_depth": 0.0,
            "S_prop": 0.0,
            "R_amb": 0.0,
            "property_group": None,
            "object_node_aux_support": 0.0,
            "object_node_supported_score": 0.0,
            "object_node_positive_support": False,
        }
    s_det = safe_float(feature_row.get("S_det")) or safe_float(feature_row.get("N1_detector_score_only")) or 0.0
    s_proj = safe_float(feature_row.get("S_proj")) or 0.0
    s_depth = safe_float(feature_row.get("S_depth")) or 0.0
    s_prop = safe_float(feature_row.get("S_prop")) or 0.0
    r_amb = safe_float(feature_row.get("R_amb")) or 0.0
    aux_support = max(0.0, s_proj, s_depth, s_prop)
    supported_score = max(0.0, min(1.0, s_det * aux_support))
    return {
        "S_det": s_det,
        "S_proj": s_proj,
        "S_depth": s_depth,
        "S_prop": s_prop,
        "R_amb": r_amb,
        "property_group": feature_row.get("property_group"),
        "object_node_aux_support": aux_support,
        "object_node_supported_score": supported_score,
        "object_node_positive_support": bool(s_det > 0.0 and aux_support > 0.0 and supported_score > 0.0),
    }


def risk_dominant_term(terms: Dict[str, float]) -> str:
    order = [
        "R_before_no_evidence",
        "R_before_contradiction",
        "R_before_ambiguity",
        "R_before_property_weakness",
    ]
    return max(order, key=lambda key: (float(terms.get(key, 0.0)), -order.index(key)))


def compute_risk_context(
    loaded: LoadedEpisode,
    candidates: List[Candidate],
    risk_features: Optional[ObjectNodeFeatureIndex],
    policy: str = "RiskOnlyReobserve",
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]]]:
    top = candidates[0]
    query = str(loaded.episode.get("object_category") or "")
    feature_by_candidate: Dict[str, Dict[str, Any]] = {}
    for cand in candidates:
        feature = risk_features.find(loaded, query, cand.candidate_id) if risk_features is not None else None
        feature_by_candidate[cand.candidate_id] = object_node_support(feature)

    top_support = feature_by_candidate[top.candidate_id]
    alternatives = candidates[1:]
    best_alt = max(
        alternatives,
        key=lambda cand: (
            feature_by_candidate[cand.candidate_id]["object_node_supported_score"],
            -rank_of(cand, candidates),
        ),
    ) if alternatives else top
    best_alt_support = feature_by_candidate[best_alt.candidate_id]
    top_fields = uncertainty_fields(top, candidates)

    r_before_no_evidence = max(0.0, min(1.0, top_fields["view_count_uncertainty"]))
    r_before_contradiction = 0.0
    r_before_ambiguity = max(0.0, min(1.0, top_fields["margin_uncertainty"]))
    r_before_property = 0.0
    r_before = max(
        r_before_no_evidence,
        r_before_contradiction,
        r_before_ambiguity,
        r_before_property,
    )
    before_terms = {
        "R_before_no_evidence": r_before_no_evidence,
        "R_before_contradiction": r_before_contradiction,
        "R_before_ambiguity": r_before_ambiguity,
        "R_before_property_weakness": r_before_property,
    }

    support_gap = (
        best_alt_support["object_node_supported_score"]
        - top_support["object_node_supported_score"]
    )
    r_after_no_evidence = 0.0 if top_support["object_node_positive_support"] else 1.0
    r_after_contradiction = max(0.0, min(1.0, support_gap / max(RISK_CONTRADICTION_SCALE, 1e-6)))
    r_after_ambiguity = max(0.0, min(1.0, top_support["R_amb"]))
    group = str(top_support.get("property_group") or "unknown")
    property_weight = 0.5 if group == "standard_furniture_or_fixture" else 1.0
    r_after_property = max(0.0, min(1.0, property_weight * (1.0 - top_support["object_node_aux_support"])))
    r_after = max(r_after_no_evidence, r_after_contradiction, r_after_ambiguity, r_after_property)
    risk_triggered = bool(r_before >= RISK_TOTAL_TRIGGER)
    context = {
        "risk_feature_source": str(RISK_OBJECT_NODE_FEATURE_ARTIFACT) if risk_features is not None else None,
        "risk_feature_available": risk_features is not None,
        "risk_policy": policy,
        "risk_top_candidate_id": top.candidate_id,
        "risk_best_alt_candidate_id": best_alt.candidate_id if best_alt else None,
        "risk_top_supported_score": top_support["object_node_supported_score"],
        "risk_best_alt_supported_score": best_alt_support["object_node_supported_score"] if best_alt else 0.0,
        "risk_support_gap_alt_minus_top": support_gap,
        "R_no_evidence": r_after_no_evidence,
        "R_contradiction": r_after_contradiction,
        "R_ambiguity": r_after_ambiguity,
        "R_property_weakness": r_after_property,
        "R_total": r_after,
        "R_before": r_before,
        "R_before_no_evidence": r_before_no_evidence,
        "R_before_contradiction": r_before_contradiction,
        "R_before_ambiguity": r_before_ambiguity,
        "R_before_property_weakness": r_before_property,
        "R_after": r_after,
        "R_after_no_evidence": r_after_no_evidence,
        "R_after_contradiction": r_after_contradiction,
        "R_after_ambiguity": r_after_ambiguity,
        "R_after_property_weakness": r_after_property,
        "risk_delta_after_reobserve": None,
        "risk_resolved_after_reobserve": None,
        "risk_unresolved_no_commit": False,
        "dominant_risk_term": risk_dominant_term(before_terms),
        "wrong_goal_avoided_by_defer": False,
        "success_lost_by_defer": False,
        "risk_total_trigger": RISK_TOTAL_TRIGGER,
        "risk_contradiction_scale": RISK_CONTRADICTION_SCALE,
        "risk_resolution_delta_trigger": RISK_RESOLUTION_DELTA_TRIGGER,
        "risk_resolution_max_risk": RISK_RESOLUTION_MAX_RISK,
        "risk_resolution_max_contradiction": RISK_RESOLUTION_MAX_CONTRADICTION,
        "risk_resolution_require_positive_support": RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT,
        "risk_triggered_reobserve": risk_triggered,
        "risk_direct_goal_switch_allowed": False,
    }
    return context, feature_by_candidate


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
    extra_fields: Optional[Dict[str, Any]] = None,
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
    if extra_fields:
        row.update(extra_fields)
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


def select_risk_reobserve_candidate(
    cache: SceneCache,
    scene: Path,
    start: List[float],
    candidates: List[Candidate],
    dominant_term: str,
) -> Tuple[Candidate, Optional[float], List[Tuple[Candidate, Optional[float]]]]:
    top = candidates[0]
    paths = [(cand, cache.distance(scene, start, cand.visit_position)) for cand in candidates]
    top_path = next(path for cand, path in paths if cand == top)

    if dominant_term == "R_before_ambiguity":
        min_score = top.score - SEMANTIC_TIE_BAND
        eligible = [
            (cand, path)
            for cand, path in paths
            if cand.score >= min_score and path is not None
        ]
        if eligible:
            selected, selected_path = min(
                eligible,
                key=lambda item: (float(item[1]), -item[0].score, rank_of(item[0], candidates)),
            )
            return selected, selected_path, paths

    return top, top_path, paths


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
    extra_fields: Optional[Dict[str, Any]] = None,
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
    if extra_fields:
        row.update(extra_fields)
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
    postview_scores: Optional[PostviewScoreIndex] = None,
    risk_features: Optional[ObjectNodeFeatureIndex] = None,
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
    risk_context: Dict[str, Any] = {}
    risk_by_candidate: Dict[str, Dict[str, Any]] = {}
    if policy in RISK_POLICIES:
        risk_context, risk_by_candidate = compute_risk_context(loaded, candidates, risk_features, policy)

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
    reobserve_path: Optional[float] = 0.0
    path_after_reobserve = selected_path
    reobservations = 0
    commit_allowed = True
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

    if policy == "SemanticVerifyTop":
        top = candidates[0]
        before_fields = uncertainty_fields(top, candidates)
        triggered = before_fields["U_sem"] >= SEMANTIC_UNCERTAINTY_TRIGGER
        if triggered:
            reobservations = 1
            selected = top
            selected_for_reobserve = top
            selected_path = cache.distance(scene, start, top.visit_position)
            reobserve_path = selected_path or 0.0
            path_after_reobserve = 0.0 if selected_path is not None else None
            after_fields = uncertainty_fields(top, candidates, extra_view_count=SEMANTIC_REOBS_VIEW_BONUS)
            viewpoint_row = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "episode_id": str(episode.get("episode_id")),
                "policy": policy,
                "decision_step": 0,
                "scene_id": episode.get("scene_id"),
                "query": episode.get("object_category"),
                "candidate_id": top.candidate_id,
                "viewpoint_id": f"semantic_verify_top:{loaded.index}:1",
                "viewpoint_position": top.visit_position,
                "viewpoint_rotation": top.visit_rotation,
                "viewpoint_policy": "SemanticVerifyTop",
                "semantic_gain_pred": before_fields["U_sem"] - after_fields["U_sem"],
                "slam_gain_pred": None,
                "travel_cost_pred": selected_path,
                "travel_cost_actual": reobserve_path,
                "observation_success": selected_path is not None,
                "candidate_score_before": top.score,
                "candidate_score_after": top.score,
                "U_sem_before": before_fields["U_sem"],
                "U_sem_after": after_fields["U_sem"],
                "candidate_rank_before": 1,
                "candidate_rank_after": 1,
                "commit_after_reobserve": selected_path is not None,
                "final_candidate_changed": False,
                "semantic_uncertainty_trigger": SEMANTIC_UNCERTAINTY_TRIGGER,
                "semantic_tie_band": SEMANTIC_TIE_BAND,
                "evidence_update_mode": "support_proxy",
                "final_candidate_id_before": top.candidate_id,
                "final_candidate_id_after": top.candidate_id,
                "switch_gate_pass": False,
                "switch_gate_reason": "no_switch_allowed",
                "score_delta_after_reobserve": 0.0,
                "U_sem_delta_after_reobserve": after_fields["U_sem"] - before_fields["U_sem"],
                "support_delta_after_reobserve": float(SEMANTIC_REOBS_VIEW_BONUS),
            }
            viewpoint_row.update(manifest_fields(loaded))
            viewpoint_rows.append(viewpoint_row)
        else:
            path_after_reobserve = selected_path

    if policy == "EvidenceGatedSemanticOnly":
        top = candidates[0]
        before_fields = uncertainty_fields(top, candidates)
        triggered = (
            before_fields["U_sem"] >= SEMANTIC_UNCERTAINTY_TRIGGER
            and SEMANTIC_MAX_REOBSERVATIONS > 0
        )
        if triggered:
            reobservations = 1
            selected = top
            selected_for_reobserve = top
            selected_path = cache.distance(scene, start, top.visit_position)
            reobserve_path = selected_path or 0.0
            path_after_reobserve = 0.0 if selected_path is not None else None
            after_fields = uncertainty_fields(top, candidates, extra_view_count=SEMANTIC_REOBS_VIEW_BONUS)
            candidate_paths = [(cand, cache.distance(scene, start, cand.visit_position)) for cand in candidates]
            postview_row: Optional[Dict[str, Any]] = None
            postview_by_candidate: Dict[str, Dict[str, Any]] = {}
            top_postview_score = None
            top_score_row: Optional[Dict[str, Any]] = None
            top_score_after = top.score
            top_support_delta = float(SEMANTIC_REOBS_VIEW_BONUS)
            top_projection_status = "not_used"
            top_score_source = "support_proxy"
            top_score_calibration = None
            missing_image_feature_reason: Optional[str] = None

            if SEMANTIC_EVIDENCE_MODE == "image_feature":
                if postview_scores is None:
                    missing_image_feature_reason = "missing_postview_score"
                else:
                    postview_row = postview_scores.find(
                        loaded,
                        str(episode.get("object_category") or ""),
                        top.candidate_id,
                    )
                    if postview_row is None:
                        missing_image_feature_reason = "missing_postview_score"
                    else:
                        postview_by_candidate = postview_candidate_scores(postview_row)
                        top_score_row = postview_by_candidate.get(top.candidate_id)
                        if top_score_row is None:
                            missing_image_feature_reason = "missing_top_candidate_score"

                top_projection_status = postview_projection_status(top_score_row)
                top_score_source = postview_score_source(top_score_row)
                top_score_calibration = postview_score_calibration(top_score_row)
                top_postview_score = image_feature_score_value(top, top_score_row)
                if top_postview_score is not None:
                    top_score_after = top_postview_score
                top_support_delta = postview_support_delta(top_score_row)
                after_fields = dict(after_fields)
                after_fields["U_sem"] = postview_u_sem(top_score_row, before_fields["U_sem"])

            switch_candidates: List[Tuple[Candidate, float, Optional[Dict[str, Any]], Optional[float]]] = []
            if SEMANTIC_EVIDENCE_MODE == "image_feature":
                if top_postview_score is not None and top_projection_status == "visible":
                    for cand, path in candidate_paths[1:]:
                        if cand.score < top.score - SEMANTIC_TIE_BAND or path is None:
                            continue
                        score_row = postview_by_candidate.get(cand.candidate_id)
                        if postview_projection_status(score_row) != "visible":
                            continue
                        score_value = image_feature_score_value(cand, score_row)
                        if score_value is None:
                            continue
                        switch_candidates.append((cand, float(path), score_row, score_value))
            else:
                switch_candidates = [
                    (cand, float(path), None, None)
                    for cand, path in candidate_paths[1:]
                    if cand.score >= top.score - SEMANTIC_TIE_BAND and path is not None
                ]
            switch_candidate: Optional[Candidate] = None
            switch_candidate_path: Optional[float] = None
            switch_candidate_score_row: Optional[Dict[str, Any]] = None
            switch_candidate_score_after: Optional[float] = None
            if switch_candidates:
                switch_candidate, switch_candidate_path, switch_candidate_score_row, switch_candidate_score_after = max(
                    switch_candidates,
                    key=lambda item: (
                        item[3] if item[3] is not None else item[0].score,
                        -float(item[1]),
                        -rank_of(item[0], candidates),
                    ),
                )

            if SEMANTIC_EVIDENCE_MODE == "image_feature":
                score_delta = (
                    0.0
                    if switch_candidate_score_after is None or top_postview_score is None
                    else switch_candidate_score_after - top_postview_score
                )
                support_delta = postview_support_delta(switch_candidate_score_row)
            else:
                score_delta = 0.0 if switch_candidate is None else switch_candidate.score - top.score
                support_delta = float(SEMANTIC_REOBS_VIEW_BONUS) if switch_candidate == top else 0.0
            switch_fields = (
                uncertainty_fields(switch_candidate, candidates)
                if switch_candidate is not None
                else after_fields
            )
            if SEMANTIC_EVIDENCE_MODE == "image_feature" and switch_candidate is not None:
                switch_fields = dict(switch_fields)
                switch_fields["U_sem"] = postview_u_sem(switch_candidate_score_row, switch_fields["U_sem"])
            u_sem_delta = switch_fields["U_sem"] - after_fields["U_sem"]
            switch_gate_pass = False
            switch_gate_reason = "no_reobserve"
            if SEMANTIC_EVIDENCE_MODE == "image_feature" and missing_image_feature_reason is not None:
                switch_gate_reason = missing_image_feature_reason
            elif SEMANTIC_EVIDENCE_MODE == "image_feature" and top_projection_status != "visible":
                switch_gate_reason = "top_not_visible"
            elif switch_candidate is None or switch_candidate_path is None:
                switch_gate_reason = "no_reobserve"
            elif score_delta < SEMANTIC_DELTA_SWITCH_SCORE:
                switch_gate_reason = "score_delta_failed"
            elif (
                (SEMANTIC_EVIDENCE_MODE != "image_feature" or SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE)
                and switch_fields["U_sem"] + SEMANTIC_DELTA_SWITCH_UNCERTAINTY > after_fields["U_sem"]
            ):
                switch_gate_reason = "uncertainty_delta_failed"
            elif support_delta <= 0.0:
                switch_gate_reason = "support_delta_failed"
            else:
                switch_gate_pass = True
                switch_gate_reason = "passed"

            if switch_gate_pass and switch_candidate is not None:
                selected = switch_candidate
                path_after_reobserve = cache.distance(scene, top.visit_position, switch_candidate.visit_position)
            if selected == top:
                selected_after_fields = after_fields
                selected_score_after = top_score_after
                selected_support_delta = top_support_delta
                selected_score_row = top_score_row
            else:
                selected_after_fields = dict(uncertainty_fields(selected, candidates))
                selected_score_row = switch_candidate_score_row
                selected_after_fields["U_sem"] = postview_u_sem(selected_score_row, selected_after_fields["U_sem"])
                selected_score_after = (
                    switch_candidate_score_after
                    if switch_candidate_score_after is not None
                    else selected.score
                )
                selected_support_delta = support_delta

            if SEMANTIC_EVIDENCE_MODE == "image_feature" and top_postview_score is not None:
                score_delta_after_reobserve = selected_score_after - top_postview_score
            else:
                score_delta_after_reobserve = selected.score - top.score

            viewpoint_row = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "episode_id": str(episode.get("episode_id")),
                "policy": policy,
                "decision_step": 0,
                "scene_id": episode.get("scene_id"),
                "query": episode.get("object_category"),
                "candidate_id": top.candidate_id,
                "viewpoint_id": f"evidence_gated:{loaded.index}:1",
                "viewpoint_position": top.visit_position,
                "viewpoint_rotation": top.visit_rotation,
                "viewpoint_policy": "EvidenceGatedSemanticOnly",
                "semantic_gain_pred": before_fields["U_sem"] - selected_after_fields["U_sem"],
                "slam_gain_pred": None,
                "travel_cost_pred": selected_path,
                "travel_cost_actual": reobserve_path,
                "observation_success": selected_path is not None,
                "candidate_score_before": top.score,
                "candidate_score_after": selected_score_after,
                "U_sem_before": before_fields["U_sem"],
                "U_sem_after": selected_after_fields["U_sem"],
                "candidate_rank_before": 1,
                "candidate_rank_after": rank_of(selected, candidates),
                "commit_after_reobserve": path_after_reobserve is not None,
                "final_candidate_changed": selected != top,
                "semantic_uncertainty_trigger": SEMANTIC_UNCERTAINTY_TRIGGER,
                "semantic_tie_band": SEMANTIC_TIE_BAND,
                "evidence_update_mode": SEMANTIC_EVIDENCE_MODE,
                "final_candidate_id_before": top.candidate_id,
                "final_candidate_id_after": selected.candidate_id,
                "switch_gate_pass": switch_gate_pass,
                "switch_gate_reason": switch_gate_reason,
                "score_delta_after_reobserve": score_delta_after_reobserve,
                "U_sem_delta_after_reobserve": selected_after_fields["U_sem"] - before_fields["U_sem"],
                "support_delta_after_reobserve": selected_support_delta,
                "switch_candidate_id": switch_candidate.candidate_id if switch_candidate else None,
                "switch_candidate_score_delta": score_delta,
                "switch_candidate_U_sem_delta": u_sem_delta,
                "switch_candidate_support_delta": support_delta,
                "postview_score_artifact": str(SEMANTIC_POSTVIEW_SCORE_ARTIFACT) if SEMANTIC_EVIDENCE_MODE == "image_feature" else None,
                "postview_decision_id": postview_row.get("decision_id") if postview_row else None,
                "postview_projection_status": postview_projection_status(selected_score_row) if SEMANTIC_EVIDENCE_MODE == "image_feature" else "not_used",
                "postview_score_source": postview_score_source(selected_score_row) if SEMANTIC_EVIDENCE_MODE == "image_feature" else "support_proxy",
                "postview_score_calibration": postview_score_calibration(selected_score_row) if SEMANTIC_EVIDENCE_MODE == "image_feature" else None,
                "postview_evidence_rule": SEMANTIC_IMAGE_SCORE_RULE if SEMANTIC_EVIDENCE_MODE == "image_feature" else None,
                "postview_uncertainty_gate_used": SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE if SEMANTIC_EVIDENCE_MODE == "image_feature" else None,
                "postview_top_projection_status": top_projection_status,
                "postview_top_score_source": top_score_source,
                "postview_top_score_calibration": top_score_calibration,
                "postview_top_score_after": top_score_after if SEMANTIC_EVIDENCE_MODE == "image_feature" else None,
                "postview_switch_score_after": switch_candidate_score_after,
                "postview_candidate_score_count": len(postview_by_candidate) if postview_row else 0,
            }
            viewpoint_row.update(manifest_fields(loaded))
            viewpoint_rows.append(viewpoint_row)
        else:
            path_after_reobserve = selected_path

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

    if policy in RISK_POLICIES:
        top = candidates[0]
        before_fields = uncertainty_fields(top, candidates)
        selected = top
        top_direct_path = cache.distance(scene, start, top.visit_position)
        selected_path = top_direct_path
        risk_triggered = bool(risk_context.get("risk_triggered_reobserve"))
        if risk_triggered and SEMANTIC_MAX_REOBSERVATIONS > 0:
            reobservations = 1
            selected_for_reobserve, selected_path, _candidate_paths = select_risk_reobserve_candidate(
                cache,
                scene,
                start,
                candidates,
                str(risk_context.get("dominant_risk_term") or ""),
            )
            reobserve_path = selected_path
            r_before_value = safe_float(risk_context.get("R_before"))
            r_after_value = safe_float(risk_context.get("R_after"))
            risk_delta = (
                None
                if r_before_value is None or r_after_value is None
                else r_before_value - r_after_value
            )
            risk_resolved = bool(
                selected_path is not None
                and r_after_value is not None
                and r_after_value < RISK_TOTAL_TRIGGER
            )
            top_support = risk_by_candidate.get(top.candidate_id, {})
            top_positive_support = bool(top_support.get("object_node_positive_support"))
            r_after_contradiction = safe_float(risk_context.get("R_after_contradiction")) or 0.0
            risk_resolution_commit = bool(
                policy == "RiskResolutionReobserve"
                and selected_path is not None
                and not risk_resolved
                and risk_delta is not None
                and risk_delta >= RISK_RESOLUTION_DELTA_TRIGGER
                and r_after_value is not None
                and r_after_value <= RISK_RESOLUTION_MAX_RISK
                and r_after_contradiction <= RISK_RESOLUTION_MAX_CONTRADICTION
                and (
                    top_positive_support
                    or not RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT
                )
            )
            risk_unresolved = not (risk_resolved or risk_resolution_commit)
            path_after_reobserve = (
                cache.distance(scene, selected_for_reobserve.visit_position, top.visit_position)
                if (risk_resolved or risk_resolution_commit) and selected_for_reobserve != top
                else (0.0 if (risk_resolved or risk_resolution_commit) else None)
            )
            commit_allowed = bool((risk_resolved or risk_resolution_commit) and path_after_reobserve is not None)
            risk_resolution_commit_reason = "risk_unresolved_no_commit"
            if risk_resolved:
                risk_resolution_commit_reason = "risk_resolved_commit"
            elif risk_resolution_commit:
                risk_resolution_commit_reason = "risk_delta_positive_support_commit"
            would_wrong_goal_commit = bool(
                top.correct is False
                and top_direct_path is not None
                and top_direct_path >= wrong_min_path
            )
            would_success_commit = bool(top.correct is True and top_direct_path is not None)
            risk_context.update(
                {
                    "risk_delta_after_reobserve": risk_delta,
                    "risk_resolved_after_reobserve": risk_resolved,
                    "risk_resolution_commit": risk_resolution_commit,
                    "risk_resolution_commit_reason": risk_resolution_commit_reason,
                    "risk_resolution_top_positive_support": top_positive_support,
                    "risk_unresolved_no_commit": risk_unresolved,
                    "wrong_goal_avoided_by_defer": bool(risk_unresolved and would_wrong_goal_commit),
                    "success_lost_by_defer": bool(risk_unresolved and would_success_commit),
                }
            )
            viewpoint_row = {
                "schema_version": SCHEMA_VERSION,
                "run_id": run_id,
                "episode_id": str(episode.get("episode_id")),
                "policy": policy,
                "decision_step": 0,
                "scene_id": episode.get("scene_id"),
                "query": episode.get("object_category"),
                "candidate_id": top.candidate_id,
                "viewpoint_id": f"risk_only:{loaded.index}:1",
                "viewpoint_position": selected_for_reobserve.visit_position,
                "viewpoint_rotation": selected_for_reobserve.visit_rotation,
                "viewpoint_policy": policy,
                "semantic_gain_pred": None,
                "slam_gain_pred": None,
                "travel_cost_pred": selected_path,
                "travel_cost_actual": reobserve_path,
                "observation_success": selected_path is not None,
                "candidate_score_before": top.score,
                "candidate_score_after": top.score,
                "U_sem_before": before_fields["U_sem"],
                "U_sem_after": before_fields["U_sem"],
                "candidate_rank_before": 1,
                "candidate_rank_after": 1,
                "commit_after_reobserve": commit_allowed,
                "final_candidate_changed": False,
                "semantic_uncertainty_trigger": SEMANTIC_UNCERTAINTY_TRIGGER,
                "semantic_tie_band": SEMANTIC_TIE_BAND,
                "evidence_update_mode": "risk_only_object_node",
                "final_candidate_id_before": top.candidate_id,
                "final_candidate_id_after": top.candidate_id if commit_allowed else None,
                "reobserve_candidate_id": selected_for_reobserve.candidate_id,
                "reobserve_candidate_rank": rank_of(selected_for_reobserve, candidates),
                "reobserve_candidate_score": selected_for_reobserve.score,
                "reobserve_candidate_is_top": selected_for_reobserve == top,
                "switch_gate_pass": False,
                "switch_gate_reason": risk_resolution_commit_reason,
                "score_delta_after_reobserve": 0.0,
                "U_sem_delta_after_reobserve": 0.0,
                "support_delta_after_reobserve": 0.0,
            }
            viewpoint_row.update(risk_context)
            viewpoint_row.update(manifest_fields(loaded))
            viewpoint_rows.append(viewpoint_row)
        else:
            path_after_reobserve = selected_path

    commit_path = path_after_reobserve if commit_allowed else None
    if commit_path is None:
        path_length_total = reobserve_path if (reobservations and reobserve_path is not None) else None
    else:
        path_length_total = (reobserve_path or 0.0) + commit_path
    success = bool(commit_allowed and selected.correct is True and path_length_total is not None)
    spl = 0.0
    if success and p_star is not None and path_length_total is not None:
        spl = p_star / max(p_star, path_length_total)

    semantic_reobserve_policy = policy in {"SemanticOnly", "SemanticVerifyTop", "EvidenceGatedSemanticOnly"} or policy in RISK_POLICIES
    wrong_goal_commit_distance = (
        None
        if not commit_allowed
        else (path_length_total if semantic_reobserve_policy and reobservations else commit_path)
    )
    wrong_goal_visit = bool(
        selected.correct is False
        and wrong_goal_commit_distance is not None
        and wrong_goal_commit_distance >= wrong_min_path
    )
    wasted_wrong = wrong_goal_commit_distance if wrong_goal_visit else 0.0
    wasted_reobserve = (
        reobserve_path if policy in RISK_POLICIES and risk_context.get("risk_unresolved_no_commit") else
        (0.0 if semantic_reobserve_policy else (reobserve_path if reobservations else 0.0))
    )

    for cand in candidates:
        selected_for_goal = bool(commit_allowed and cand == selected)
        candidate_extra = {}
        if policy in RISK_POLICIES:
            candidate_support = risk_by_candidate.get(cand.candidate_id, {})
            candidate_extra.update(risk_context)
            candidate_extra.update(
                {
                    "candidate_object_node_S_det": candidate_support.get("S_det"),
                    "candidate_object_node_S_proj": candidate_support.get("S_proj"),
                    "candidate_object_node_S_depth": candidate_support.get("S_depth"),
                    "candidate_object_node_S_prop": candidate_support.get("S_prop"),
                    "candidate_object_node_R_amb": candidate_support.get("R_amb"),
                    "candidate_object_node_property_group": candidate_support.get("property_group"),
                    "candidate_object_node_aux_support": candidate_support.get("object_node_aux_support"),
                    "candidate_object_node_supported_score": candidate_support.get("object_node_supported_score"),
                    "candidate_object_node_positive_support": candidate_support.get("object_node_positive_support"),
                }
            )
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
                (wrong_goal_commit_distance if semantic_reobserve_policy else commit_path) if selected_for_goal else None,
                wrong_goal_visit if selected_for_goal else False,
                candidate_extra if candidate_extra else None,
            )
        )

    termination = "success" if success else ("risk_unresolved" if policy in RISK_POLICIES and risk_context.get("risk_unresolved_no_commit") else "timeout")
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
            1 if commit_allowed and commit_path is not None else 0,
            wrong_goal_visit,
            wasted_wrong,
            wasted_reobserve,
            selected if commit_allowed else None,
            termination,
            risk_context if policy in RISK_POLICIES else None,
        ),
        candidate_rows,
        viewpoint_rows,
    )


def aggregate(
    episode_rows: List[Dict[str, Any]],
    viewpoint_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    by_policy: Dict[str, List[Dict[str, Any]]] = {}
    for row in episode_rows:
        by_policy.setdefault(row["policy"], []).append(row)

    viewpoint_by_policy: Dict[str, List[Dict[str, Any]]] = {}
    for row in viewpoint_rows or []:
        viewpoint_by_policy.setdefault(row["policy"], []).append(row)

    result: Dict[str, Any] = {}
    for policy, rows in sorted(by_policy.items()):
        policy_viewpoints = viewpoint_by_policy.get(policy, [])
        result[policy] = {
            "episodes": len(rows),
            "success_rate": mean(1.0 if row["success"] else 0.0 for row in rows),
            "mean_spl": mean(row.get("spl") for row in rows),
            "wrong_goal_visit_rate": mean(1.0 if row["wrong_goal_visit"] else 0.0 for row in rows),
            "mean_wasted_path_total": mean(row.get("wasted_path_total") for row in rows),
            "mean_wasted_path_wrong_goal": mean(row.get("wasted_path_wrong_goal") for row in rows),
            "mean_wasted_path_reobserve": mean(row.get("wasted_path_reobserve") for row in rows),
            "mean_num_reobservations": mean(float(row.get("num_reobservations", 0)) for row in rows),
            "final_candidate_changed_rate": mean(
                1.0 if row.get("final_candidate_changed") else 0.0 for row in policy_viewpoints
            ),
            "switch_gate_pass_rate": mean(
                1.0 if row.get("switch_gate_pass") else 0.0
                for row in policy_viewpoints
                if row.get("switch_gate_pass") is not None
            ),
            "mean_score_delta_after_reobserve": mean(
                norm_float(row.get("score_delta_after_reobserve")) for row in policy_viewpoints
            ),
            "mean_U_sem_delta_after_reobserve": mean(
                norm_float(row.get("U_sem_delta_after_reobserve")) for row in policy_viewpoints
            ),
            "mean_travel_cost_to_reobserve": mean(
                norm_float(row.get("travel_cost_actual")) for row in policy_viewpoints
            ),
            "risk_triggered_reobserve_rate": mean(
                1.0 if row.get("risk_triggered_reobserve") else 0.0
                for row in rows
                if row.get("risk_triggered_reobserve") is not None
            ),
            "risk_resolved_after_reobserve_rate": mean(
                1.0 if row.get("risk_resolved_after_reobserve") else 0.0
                for row in rows
                if row.get("risk_resolved_after_reobserve") is not None
            ),
            "risk_unresolved_no_commit_rate": mean(
                1.0 if row.get("risk_unresolved_no_commit") else 0.0
                for row in rows
                if row.get("risk_unresolved_no_commit") is not None
            ),
            "wrong_goal_avoided_by_defer_rate": mean(
                1.0 if row.get("wrong_goal_avoided_by_defer") else 0.0
                for row in rows
                if row.get("wrong_goal_avoided_by_defer") is not None
            ),
            "success_lost_by_defer_rate": mean(
                1.0 if row.get("success_lost_by_defer") else 0.0
                for row in rows
                if row.get("success_lost_by_defer") is not None
            ),
            "risk_resolution_commit_rate": mean(
                1.0 if row.get("risk_resolution_commit") else 0.0
                for row in rows
                if row.get("risk_resolution_commit") is not None
            ),
            "mean_R_before": mean(norm_float(row.get("R_before")) for row in rows),
            "mean_R_after": mean(norm_float(row.get("R_after")) for row in rows),
            "mean_risk_delta_after_reobserve": mean(
                norm_float(row.get("risk_delta_after_reobserve")) for row in rows
            ),
            "mean_R_total": mean(norm_float(row.get("R_total")) for row in rows),
            "mean_R_no_evidence": mean(norm_float(row.get("R_no_evidence")) for row in rows),
            "mean_R_contradiction": mean(norm_float(row.get("R_contradiction")) for row in rows),
            "mean_R_ambiguity": mean(norm_float(row.get("R_ambiguity")) for row in rows),
            "mean_R_property_weakness": mean(norm_float(row.get("R_property_weakness")) for row in rows),
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
    parser.add_argument("--semantic-delta-switch-score", type=float, default=SEMANTIC_DELTA_SWITCH_SCORE)
    parser.add_argument("--semantic-delta-switch-uncertainty", type=float, default=SEMANTIC_DELTA_SWITCH_UNCERTAINTY)
    parser.add_argument("--semantic-evidence-mode", default=SEMANTIC_EVIDENCE_MODE, choices=["support_proxy", "image_feature"])
    parser.add_argument("--semantic-postview-score-artifact", default=None)
    parser.add_argument("--semantic-image-score-rule", default=SEMANTIC_IMAGE_SCORE_RULE, choices=["raw_delta", "agg_local_delta"])
    parser.add_argument("--semantic-use-postview-uncertainty-gate", type=parse_bool, default=SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE)
    parser.add_argument("--semantic-max-reobservations", type=int, default=SEMANTIC_MAX_REOBSERVATIONS)
    parser.add_argument("--risk-object-node-features", default=None)
    parser.add_argument("--risk-total-trigger", type=float, default=RISK_TOTAL_TRIGGER)
    parser.add_argument("--risk-contradiction-scale", type=float, default=RISK_CONTRADICTION_SCALE)
    parser.add_argument("--risk-resolution-delta-trigger", type=float, default=RISK_RESOLUTION_DELTA_TRIGGER)
    parser.add_argument("--risk-resolution-max-risk", type=float, default=RISK_RESOLUTION_MAX_RISK)
    parser.add_argument("--risk-resolution-max-contradiction", type=float, default=RISK_RESOLUTION_MAX_CONTRADICTION)
    parser.add_argument("--risk-resolution-require-positive-support", type=parse_bool, default=RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT)
    return parser.parse_args()


def main() -> None:
    global SEMANTIC_DELTA_SWITCH_SCORE, SEMANTIC_DELTA_SWITCH_UNCERTAINTY
    global SEMANTIC_EVIDENCE_MODE, SEMANTIC_MAX_REOBSERVATIONS
    global SEMANTIC_POSTVIEW_SCORE_ARTIFACT
    global SEMANTIC_IMAGE_SCORE_RULE, SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE
    global SEMANTIC_REOBS_VIEW_BONUS, SEMANTIC_TIE_BAND, SEMANTIC_UNCERTAINTY_TRIGGER
    global RISK_OBJECT_NODE_FEATURE_ARTIFACT, RISK_TOTAL_TRIGGER, RISK_CONTRADICTION_SCALE
    global RISK_RESOLUTION_DELTA_TRIGGER, RISK_RESOLUTION_MAX_RISK
    global RISK_RESOLUTION_MAX_CONTRADICTION, RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT

    args = parse_args()
    SEMANTIC_UNCERTAINTY_TRIGGER = float(args.semantic_uncertainty_trigger)
    SEMANTIC_TIE_BAND = float(args.semantic_tie_band)
    SEMANTIC_REOBS_VIEW_BONUS = int(args.semantic_reobs_view_bonus)
    SEMANTIC_DELTA_SWITCH_SCORE = float(args.semantic_delta_switch_score)
    SEMANTIC_DELTA_SWITCH_UNCERTAINTY = float(args.semantic_delta_switch_uncertainty)
    SEMANTIC_EVIDENCE_MODE = str(args.semantic_evidence_mode)
    SEMANTIC_MAX_REOBSERVATIONS = int(args.semantic_max_reobservations)
    SEMANTIC_IMAGE_SCORE_RULE = str(args.semantic_image_score_rule)
    SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE = bool(args.semantic_use_postview_uncertainty_gate)
    SEMANTIC_POSTVIEW_SCORE_ARTIFACT = Path(args.semantic_postview_score_artifact) if args.semantic_postview_score_artifact else None
    RISK_OBJECT_NODE_FEATURE_ARTIFACT = Path(args.risk_object_node_features) if args.risk_object_node_features else None
    RISK_TOTAL_TRIGGER = float(args.risk_total_trigger)
    RISK_CONTRADICTION_SCALE = float(args.risk_contradiction_scale)
    RISK_RESOLUTION_DELTA_TRIGGER = float(args.risk_resolution_delta_trigger)
    RISK_RESOLUTION_MAX_RISK = float(args.risk_resolution_max_risk)
    RISK_RESOLUTION_MAX_CONTRADICTION = float(args.risk_resolution_max_contradiction)
    RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT = bool(args.risk_resolution_require_positive_support)
    if SEMANTIC_EVIDENCE_MODE == "image_feature" and SEMANTIC_POSTVIEW_SCORE_ARTIFACT is None:
        raise ValueError("--semantic-postview-score-artifact is required when --semantic-evidence-mode image_feature")
    if any(policy in RISK_POLICIES for policy in args.policies) and RISK_OBJECT_NODE_FEATURE_ARTIFACT is None:
        raise ValueError("--risk-object-node-features is required when policy includes risk re-observation policies")

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
    postview_scores = (
        PostviewScoreIndex(SEMANTIC_POSTVIEW_SCORE_ARTIFACT)
        if SEMANTIC_POSTVIEW_SCORE_ARTIFACT is not None
        else None
    )
    risk_features = (
        ObjectNodeFeatureIndex(RISK_OBJECT_NODE_FEATURE_ARTIFACT)
        if RISK_OBJECT_NODE_FEATURE_ARTIFACT is not None
        else None
    )

    random.seed(args.seed)
    cache = SceneCache()
    episode_rows: List[Dict[str, Any]] = []
    all_viewpoint_rows: List[Dict[str, Any]] = []
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
                    postview_scores,
                    risk_features,
                )
                append_jsonl(episode_log, episode_row)
                for row in candidate_rows:
                    append_jsonl(candidate_log, row)
                for row in viewpoint_rows:
                    append_jsonl(viewpoint_log, row)
                episode_rows.append(episode_row)
                all_viewpoint_rows.extend(viewpoint_rows)
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
        "semantic_delta_switch_score": SEMANTIC_DELTA_SWITCH_SCORE,
        "semantic_delta_switch_uncertainty": SEMANTIC_DELTA_SWITCH_UNCERTAINTY,
        "semantic_evidence_mode": SEMANTIC_EVIDENCE_MODE,
        "semantic_postview_score_artifact": str(SEMANTIC_POSTVIEW_SCORE_ARTIFACT) if SEMANTIC_POSTVIEW_SCORE_ARTIFACT else None,
        "semantic_postview_score_rows": len(postview_scores.rows) if postview_scores else None,
        "semantic_postview_uses_gt_for_action": postview_scores.uses_gt_for_action if postview_scores else None,
        "semantic_image_score_rule": SEMANTIC_IMAGE_SCORE_RULE,
        "semantic_use_postview_uncertainty_gate": SEMANTIC_USE_POSTVIEW_UNCERTAINTY_GATE,
        "semantic_max_reobservations": SEMANTIC_MAX_REOBSERVATIONS,
        "risk_object_node_feature_artifact": str(RISK_OBJECT_NODE_FEATURE_ARTIFACT) if RISK_OBJECT_NODE_FEATURE_ARTIFACT else None,
        "risk_object_node_feature_rows": risk_features.rows if risk_features else None,
        "risk_object_node_uses_gt_for_action": risk_features.uses_gt_for_action if risk_features else None,
        "risk_total_trigger": RISK_TOTAL_TRIGGER,
        "risk_contradiction_scale": RISK_CONTRADICTION_SCALE,
        "risk_resolution_delta_trigger": RISK_RESOLUTION_DELTA_TRIGGER,
        "risk_resolution_max_risk": RISK_RESOLUTION_MAX_RISK,
        "risk_resolution_max_contradiction": RISK_RESOLUTION_MAX_CONTRADICTION,
        "risk_resolution_require_positive_support": RISK_RESOLUTION_REQUIRE_POSITIVE_SUPPORT,
        "episode_rows": len(episode_rows),
        "candidate_decision_rows": candidate_count,
        "viewpoint_decision_rows": viewpoint_count,
        "aggregate": aggregate(episode_rows, all_viewpoint_rows),
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
