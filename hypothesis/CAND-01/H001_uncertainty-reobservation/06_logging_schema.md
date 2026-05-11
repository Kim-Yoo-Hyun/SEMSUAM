# Navigation Failure Logging Schema

## Purpose

Define logging fields for wrong-goal visit and wasted path in H001.

This schema is used to test whether semantic uncertainty as active SLAM/navigation utility reduces avoidable navigation failures, not only final `Success Rate` or `SPL`.

## Facts

- H001 evaluates ObjectNav behavior on HM3D ObjectNav and optionally HM3D-OVON.
- Standard ObjectNav metrics such as `Success Rate` and `SPL` do not directly explain why an episode failed or wasted travel.
- H001 needs per-candidate and per-decision logs because the intervention happens before committing to a semantic goal candidate.
- `05_uncertainty_features.md` defines candidate uncertainty fields that must be linked to this navigation log.

## Paper Claims

- ObjectNav and open-vocabulary ObjectNav benchmarks report task-level metrics such as `Success Rate` and `SPL`.
- Semantic-map navigation methods such as `CARe`, `VLMaps`, and `SG-Nav` motivate candidate confidence, re-perception, or semantic map quality as reasons for navigation behavior changes.

## Inferences

For H001, the key evidence is not just that an agent succeeds more often. The key evidence is that high semantic uncertainty predicts wrong semantic commitments, and active re-observation prevents or reduces those commitments without excessive extra travel.

## Log File Format

Use JSON Lines for implementation logs:

```text
runs/<run_id>/episodes.jsonl
runs/<run_id>/candidate_decisions.jsonl
runs/<run_id>/viewpoint_decisions.jsonl
runs/<run_id>/summary.json
```

Do not create these folders until an actual implementation run starts.

## Episode Log

One row per episode.

```json
{
  "schema_version": "h001.navlog.v1",
  "run_id": "string",
  "episode_id": "string",
  "dataset": "hm3d_objectnav_v2 | hm3d_ovon",
  "split": "train | val | minival | val_seen | val_unseen | val_seen_synonyms",
  "scene_id": "string",
  "query": "string",
  "query_type": "closed_class | open_vocabulary",
  "policy": "NoReobserve | RandomReobserve | FrontierReobserve | CAReStyle | SemanticOnly | SLAMOnly | SemanticSLAM | GTTargetOracle | GTCandidateOracle | GTViewOracle",
  "start_position": [0.0, 0.0, 0.0],
  "start_rotation": [0.0, 0.0, 0.0, 1.0],
  "success": false,
  "spl": 0.0,
  "soft_spl": null,
  "distance_to_success": null,
  "path_length_total": 0.0,
  "shortest_path_to_success": null,
  "num_reobservations": 0,
  "num_candidate_commits": 0,
  "num_wrong_goal_visits": 0,
  "wrong_goal_visit": false,
  "wrong_goal_pass_through": false,
  "wasted_path_total": 0.0,
  "wasted_path_wrong_goal": 0.0,
  "wasted_path_reobserve": 0.0,
  "wasted_path_other": 0.0,
  "final_goal_candidate_id": "string",
  "final_goal_correct": false,
  "gt_nearest_target_distance": null,
  "gt_shortest_path_to_target": null,
  "termination_reason": "success | timeout | collision_budget | unreachable | no_candidate | runtime_error"
}
```

## Candidate Decision Log

One row per semantic candidate considered.

```json
{
  "schema_version": "h001.navlog.v1",
  "run_id": "string",
  "episode_id": "string",
  "decision_step": 0,
  "scene_id": "string",
  "query": "string",
  "candidate_id": "string",
  "candidate_rank": 1,
  "candidate_position": [0.0, 0.0, 0.0],
  "candidate_score": 0.0,
  "top1_score": 0.0,
  "top2_score": 0.0,
  "score_uncertainty": 0.0,
  "margin_uncertainty": 0.0,
  "view_count_uncertainty": null,
  "view_diversity_uncertainty": null,
  "visibility_uncertainty": null,
  "size_support_uncertainty": null,
  "spatial_ambiguity_uncertainty": null,
  "U_sem": 0.0,
  "trigger_reobserve": false,
  "commit_without_reobserve": true,
  "selected_for_goal": true,
  "selected_for_reobserve": false,
  "candidate_correct": null,
  "candidate_correct_source": "gt_instance | gt_synonym_group | synthetic | unavailable",
  "candidate_reachable": null,
  "goal_visit": false,
  "wrong_goal_visit": false,
  "wrong_goal_pass_through": false,
  "explicit_commit": false,
  "path_to_candidate": null,
  "path_after_candidate": null,
  "wasted_path_from_candidate": 0.0
}
```

## Viewpoint Decision Log

One row per selected re-observation viewpoint.

```json
{
  "schema_version": "h001.navlog.v1",
  "run_id": "string",
  "episode_id": "string",
  "decision_step": 0,
  "scene_id": "string",
  "query": "string",
  "candidate_id": "string",
  "viewpoint_id": "string",
  "viewpoint_position": [0.0, 0.0, 0.0],
  "viewpoint_rotation": [0.0, 0.0, 0.0, 1.0],
  "viewpoint_policy": "RandomReobserve | SemanticOnly | SLAMOnly | SemanticSLAM | OracleView",
  "semantic_gain_pred": null,
  "slam_gain_pred": null,
  "travel_cost_pred": 0.0,
  "travel_cost_actual": 0.0,
  "observation_success": false,
  "candidate_score_before": 0.0,
  "candidate_score_after": 0.0,
  "U_sem_before": 0.0,
  "U_sem_after": 0.0,
  "candidate_rank_before": 1,
  "candidate_rank_after": 1,
  "commit_after_reobserve": false,
  "final_candidate_changed": false
}
```

## Wrong-goal Visit Definition

### Facts

Standard ObjectNav success is based on reaching a correct goal object category within a success distance. H001 additionally needs to detect whether the agent committed to an incorrect semantic candidate before success or failure.

### Inferences

The primary wrong-goal metric should require explicit policy commitment. A near-candidate pass-through can happen while following a shortest path or re-observation route, so counting it as a primary wrong-goal visit can over-penalize incidental geometry and weaken the evidence.

Pass-through events are still useful diagnostics, but they are not the primary metric for top-tier evaluation.

### Operational Definition

Set `wrong_goal_visit = true` for a candidate decision if all conditions hold:

- `selected_for_goal = true`
- `explicit_commit = true`
- the agent reaches the candidate neighborhood or executes a stop/commit decision for that candidate
- `candidate_correct = false`
- traveled distance toward that candidate exceeds `wrong_goal_min_path`

First default:

```text
wrong_goal_min_path = max(1.0 meter, 0.10 * shortest_path_to_success)
candidate_neighborhood_radius = success_distance if available, else 1.0 meter
```

Episode-level `wrong_goal_visit = true` if any candidate decision in the episode has `wrong_goal_visit = true`.

Set `wrong_goal_pass_through = true` only as a diagnostic if all conditions hold:

- the agent enters a wrong candidate neighborhood
- `candidate_correct = false`
- `explicit_commit = false`
- the event was not the final success target

Do not include `wrong_goal_pass_through` in the primary wrong-goal visit rate. Report it separately to detect policies that simply route through ambiguous object areas.

## Candidate Correctness

Use the strongest available label:

| Data condition | `candidate_correct` rule |
| --- | --- |
| ObjectNav HM3D v2 with target instances | candidate is within success radius of a valid target instance for the episode |
| HM3D-OVON with open-vocabulary target annotations | candidate matches target object instance or accepted synonym group |
| Synthetic perturbation / replay | candidate id is labeled by constructed ground truth |
| No instance-level label | mark `candidate_correct = null` and do not use wrong-goal rate as primary result |

## Ground Truth Usage

Use ground truth for three purposes:

- label candidate correctness
- compute shortest-path and wasted-path references
- define oracle upper bounds

Do not present ground-truth policies as deployable baselines. They are diagnostic upper bounds.

Ground-truth references:

| Reference | Role |
| --- | --- |
| `GTTargetOracle` | shortest path to a valid target instance; upper bound for `SPL` / path cost |
| `GTCandidateOracle` | chooses the correct semantic candidate if present; separates candidate ranking error from navigation error |
| `GTViewOracle` | chooses the best re-observation viewpoint using target/candidate labels; upper bound for active re-observation |

## Wasted Path Definition

### Facts

`SPL` penalizes inefficient path length, but it does not separate useful re-observation from avoidable wrong semantic commitment.

### Inferences

H001 needs at least three path buckets:

- path spent on useful or intended re-observation
- path wasted by wrong semantic commitment
- path wasted by other causes such as collisions, local planner detours, or unreachable goals

### Path Buckets

```text
path_length_total =
  path_to_reobserve
+ path_to_goal_candidates
+ path_after_success_or_failure
```

Episode log fields:

- `wasted_path_wrong_goal`: distance traveled toward wrong candidates before returning, replanning, or timing out
- `wasted_path_reobserve`: extra distance spent on re-observation beyond direct path to final committed correct goal
- `wasted_path_other`: inefficient distance not attributable to wrong candidate or planned re-observation
- `wasted_path_total`: sum of the three buckets

## Wasted Path Formula

Let:

```text
P_total = executed path length
P_star = shortest path from start to nearest valid target
P_reobs = executed path assigned to re-observation viewpoints
P_wrong = executed path assigned to wrong-goal visits
```

First default:

```text
wasted_path_total = max(0, P_total - P_star)
wasted_path_wrong_goal = P_wrong
wasted_path_reobserve = min(P_reobs, wasted_path_total - wasted_path_wrong_goal)
wasted_path_other = max(0, wasted_path_total - wasted_path_wrong_goal - wasted_path_reobserve)
```

If the episode has no reachable valid target or no valid `P_star`, log:

```text
shortest_path_to_success = null
wasted_path_total = null
```

and exclude it from wasted-path aggregate metrics.

## Aggregate Metrics

Report per policy:

- `wrong_goal_visit_rate`
- `mean_wasted_path_total`
- `mean_wasted_path_wrong_goal`
- `mean_wasted_path_reobserve`
- `Success Rate`
- `SPL`
- `mean_num_reobservations`
- `mean_travel_cost_to_reobserve`
- `uncertainty_failure_auc` if enough labels exist
- `uncertainty_failure_spearman` if enough labels exist

## Closed-vocabulary And OVON Compatibility

Use the same schema for `hm3d_objectnav_v2` and `hm3d_ovon`.

Differences:

- `query_type = closed_class` for HM3D ObjectNav v2
- `query_type = open_vocabulary` for HM3D-OVON
- HM3D-OVON must preserve raw text query, synonym group, and accepted target ids if available
- Candidate correctness for HM3D-OVON must account for synonyms before counting wrong-goal visits

## Required Before Implementation

The first implementation must define:

- success distance used for candidate visit
- source of target instance ids
- source of candidate positions
- path segment assignment rule for re-observation vs goal commitment
- handling of unreachable target episodes
- whether aggregate metrics are computed over all episodes or only episodes with valid candidate labels
- explicit commit signal used by each policy
- diagnostic handling of `wrong_goal_pass_through`

## Failure Interpretation

| Observation | Interpretation |
| --- | --- |
| `wrong_goal_visit_rate` drops but `SPL` drops strongly | re-observation is semantically useful but too expensive |
| `SPL` improves but wrong-goal rate is unchanged | improvement may come from path planning, not semantic uncertainty |
| uncertainty does not correlate with wrong-goal labels | uncertainty features are not measuring semantic decision risk |
| `RandomReobserve` matches proposed policy | viewpoint utility is not the contribution yet |
| HM3D works but HM3D-OVON fails | open-vocabulary ambiguity needs better semantic scoring or synonym handling |

## User Decision Needed

- Whether `wrong_goal_min_path` should start as `1.0 meter` or a percentage-only threshold.
