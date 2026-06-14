# Semantic Candidate Uncertainty Features

## Purpose

Define the semantic uncertainty features used by H001 before implementing the first probe.

The target unit is a candidate object/node retrieved from a pre-explored semantic map for an ObjectNav query.

## Facts

- H001 uses semantic map object/node uncertainty as the primary signal for active re-observation.
- The first probe must work before full SLAM-side evaluation is available.
- Available first-probe sources may include precomputed `VLMaps` demo artifacts, Habitat ObjectNav episodes after HM3D is ready, or a one-scene Replica / ScanNet replay.
- Final evaluation must connect uncertainty to task behavior: wrong-goal visit, wasted path, `Success Rate`, and `SPL`.

## Paper Claims

- `CARe` treats low confidence and multi-view inconsistency in pre-explored semantic maps as signs that a navigation decision may be unreliable.
- `VLMaps` uses visual-language features fused into a 3D map for language-indexed navigation.
- `SG-Nav` and related online scene-graph navigation work imply that re-perception can reduce errors from stale or incomplete semantic memory.
- Active metric-semantic SLAM papers treat uncertainty reduction as a planning objective, but usually focus on pose/map uncertainty rather than ObjectNav candidate uncertainty.

## Inferences

Semantic uncertainty should not be a single detector confidence. For H001, useful uncertainty is the probability that committing to a semantic candidate will cause wrong-goal behavior or waste path. The first feature set should therefore mix semantic ambiguity, observation support, viewpoint diversity, and geometric visibility.

## Candidate Definition

For a query object class or text query `q`, a semantic map returns candidate nodes:

```text
c_i = {
  candidate_id,
  query,
  class_or_text_label,
  map_position,
  semantic_score,
  competing_scores,
  observation_views,
  geometry_support,
  reachable_viewpoints
}
```

The uncertainty score should answer:

```text
How risky is it to commit to candidate c_i without re-observation?
```

## First Probe Feature Set

| Feature | Meaning | Required input | First-probe status |
| --- | --- | --- | --- |
| `score_uncertainty` | top candidate has weak semantic evidence | top-1 semantic similarity or confidence | Required |
| `margin_uncertainty` | top candidate is hard to distinguish from runner-up | top-1 and top-2 candidate scores | Required |
| `view_count_uncertainty` | candidate was observed too few times | observation count per candidate/node | Required if view history exists |
| `view_diversity_uncertainty` | observations come from similar directions | camera poses for observations | Required if pose history exists |
| `visibility_uncertainty` | candidate should be observable but is weakly or inconsistently visible | map geometry, obstacle grid, candidate position, reachable views | Optional first probe |
| `size_support_uncertainty` | candidate is too small, fragmented, or sparse | object mask area, cluster size, point count, grid support | Optional first probe |
| `spatial_ambiguity_uncertainty` | multiple plausible candidates are close enough to confuse navigation | candidate positions and scores | Optional first probe |

## Minimal Required Features

The first implementation should use at least these three:

- `score_uncertainty`
- `margin_uncertainty`
- one support feature: `view_count_uncertainty` or `view_diversity_uncertainty`

If view history is unavailable in the first artifact, use `size_support_uncertainty` as the support feature and mark the result as lower confidence.

## Feature Formulas

### `score_uncertainty`

```text
u_score(c) = 1 - normalize(s_1)
```

`s_1` is the top semantic score for candidate `c`. The normalization method must be fixed per map backend.

First default:

```text
normalize(s_1) = clamp((s_1 - p05) / (p95 - p05), 0, 1)
```

where `p05` and `p95` are score percentiles from candidates in the same scene.

### `margin_uncertainty`

```text
u_margin(c) = 1 - clamp((s_1 - s_2) / tau_margin, 0, 1)
```

`s_2` is the second-best competing candidate score for the same query. Small margin means the map cannot clearly separate the top candidate from alternatives.

First default:

```text
tau_margin = percentile_75(s_1 - s_2)
```

computed over query-candidate pairs in the probe scene.

### `view_count_uncertainty`

```text
u_view_count(c) = 1 - clamp(n_obs / n_min, 0, 1)
```

`n_obs` is the number of observations that contributed to candidate `c`.

First default:

```text
n_min = 3
```

This should be tuned only after checking whether observation count is available in the chosen map representation.

### `view_diversity_uncertainty`

```text
u_view_diversity(c) = 1 - H(view_bins) / log(K)
```

`view_bins` are discretized approach angles around the candidate. Low entropy means the candidate was seen from one narrow direction.

First default:

```text
K = 8
```

If camera poses are available but object-specific association is weak, approximate this using viewpoints within visibility range of the candidate.

### `visibility_uncertainty`

```text
u_visibility(c) = 1 - visible_support(c)
```

`visible_support(c)` estimates how often candidate `c` is visible from reachable viewpoints without obstacle occlusion. This feature is useful for choosing re-observation viewpoints, but it should be optional until the map geometry and ray/visibility test are reliable.

### `size_support_uncertainty`

```text
u_size(c) = 1 - clamp(size_support(c) / size_min, 0, 1)
```

`size_support(c)` can be object mask area, point count, or occupied grid cell count. This feature catches tiny false positives, but it can penalize real small objects, so it should not dominate the utility.

### `spatial_ambiguity_uncertainty`

```text
u_spatial(c) = max_j exp(-dist(c, c_j) / sigma_d) * score_similarity(c, c_j)
```

This is high when another plausible candidate for the same query is spatially close enough to cause wrong-goal behavior.

## Composite Semantic Uncertainty

First-probe default:

```text
U_sem(c) =
  w_score * u_score(c)
+ w_margin * u_margin(c)
+ w_support * u_support(c)
```

where:

```text
u_support(c) = max(u_view_count, u_view_diversity)
```

Initial weights:

```text
w_score = 0.35
w_margin = 0.35
w_support = 0.30
```

Do not tune weights on final evaluation episodes. Use a small calibration split or a fixed heuristic.

## Re-observation Trigger

Candidate `c` should trigger active re-observation when:

```text
U_sem(c) >= theta_uncertain
```

First default:

```text
theta_uncertain = percentile_70(U_sem)
```

computed within the probe scene or calibration split.

Alternative threshold for ablation:

```text
theta_uncertain in {0.5, 0.6, 0.7, 0.8}
```

## Expected Relation to Failures

| Failure type | Expected high feature |
| --- | --- |
| semantic false positive | `score_uncertainty`, `size_support_uncertainty` |
| multiple similar objects | `margin_uncertainty`, `spatial_ambiguity_uncertainty` |
| poor view coverage | `view_count_uncertainty`, `view_diversity_uncertainty` |
| occluded or weakly visible candidate | `visibility_uncertainty` |
| map/viewpoint mismatch | `visibility_uncertainty`, later SLAM uncertainty |
| changed environment | deferred dynamic-change feature |

## Deferred Features

These are useful but should not block the first probe:

- dynamic-change or map-age uncertainty
- full SLAM pose covariance
- loop closure likelihood
- learned uncertainty model trained from failure labels
- LLM-based semantic plausibility score
- real-world safety risk score

## Logging Requirements

Each candidate evaluation should log:

- `episode_id`
- `scene_id`
- `query`
- `candidate_id`
- `candidate_position`
- `top1_score`
- `top2_score`
- `score_uncertainty`
- `margin_uncertainty`
- `view_count_uncertainty`
- `view_diversity_uncertainty`
- `visibility_uncertainty`
- `size_support_uncertainty`
- `spatial_ambiguity_uncertainty`
- `U_sem`
- `trigger_reobserve`
- `chosen_viewpoint_id`
- `travel_cost_to_viewpoint`
- `final_goal_id`
- `wrong_goal_visit`
- `wasted_path`
- `Success Rate`
- `SPL`

Missing feature values must be logged as `null`, not silently dropped.

## First Probe Decision

### Facts

The current first probe is blocked from full Habitat ObjectNav metrics until HM3D/ObjectNav assets are fully mounted and smoke-tested.

### Inferences

Once HM3D/ObjectNav is ready, the first probe should start with `score_uncertainty`, `margin_uncertainty`, and one support feature. If the available map artifact does not contain view history, use `size_support_uncertainty` as a temporary support proxy and avoid claiming multi-view uncertainty.

### User Decision Needed

- Whether to allow `size_support_uncertainty` as the fallback support feature if view history is unavailable.
- Whether first thresholding should use percentile-based `theta_uncertain` or a fixed grid search.
