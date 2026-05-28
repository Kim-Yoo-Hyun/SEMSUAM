# Evaluation Contract

## Purpose

Define the top-tier evaluation contract for H001 before implementation.

The goal is to test whether semantic uncertainty can function as active SLAM/navigation utility, not only whether an ObjectNav agent obtains a higher final score.

## Facts

- HM3D ObjectNav v2 is available locally through Docker.
- HM3D-OVON is available locally through Docker.
- H001 already defines semantic candidate uncertainty features in `05_uncertainty_features.md`.
- H001 already defines navigation failure logging in `06_logging_schema.md`.
- Primary implementation and smoke tests must run in Docker.

## Paper Claims

- ObjectNav benchmarks commonly report `Success Rate`, `SPL`, and distance-style task metrics.
- Open-vocabulary ObjectNav benchmarks evaluate language-conditioned target search with broader query ambiguity.
- Semantic-map navigation papers motivate confidence, re-perception, and semantic memory quality as causes of navigation behavior changes.

## Inferences

A top-tier paper needs evidence at three levels:

- task outcome: `Success Rate`, `SPL`, distance to success
- failure mechanism: wrong-goal commit, wasted path, re-observation cost
- uncertainty validity: uncertainty score predicts semantic decision failure

If H001 improves only `SPL` without reducing semantic failure, the contribution may look like path planning. If H001 reduces wrong-goal commits but destroys `SPL`, the method may be semantically useful but not a good navigation policy.

## Primary Claim

Semantic uncertainty from a pre-explored semantic map can be converted into an active navigation utility that reduces wrong semantic goal commitment and wasted path in ObjectNav, and can later be extended with SLAM uncertainty to improve map/pose consistency.

## Primary Benchmarks

| Benchmark | Role | Why it matters |
| --- | --- | --- |
| HM3D ObjectNav v2 | first controlled benchmark | closed-class ObjectNav with accessible HM3D assets and episodes |
| HM3D-OVON | open-vocabulary extension | stronger semantic ambiguity and query uncertainty |

## Secondary Benchmarks

| Benchmark | Role | Use condition |
| --- | --- | --- |
| Replica one-scene replay | debugging / visual sanity | use if HM3D runtime integration is slow |
| ScanNet or ScanNet++ replay | map/pose-side probe | use for Step 4-5 SLAM/map quality extension |
| Real-world lab scene | robotics credibility | use after simulator evidence is stable |

## Split Discipline

Use calibration splits only for thresholds and fixed weights.

| Data | Calibration | Evaluation |
| --- | --- | --- |
| HM3D ObjectNav v2 | small train subset or minival | held-out val subset |
| HM3D-OVON | train subset | `val_seen`, `val_unseen`, `val_seen_synonyms` |

Do not tune `theta_uncertain`, feature weights, or travel-cost weights on final evaluation splits.

## Fixed Split Plan

### 사실

- Fixed manifest: `manifests/h001_splits_v1.json`
- Verification summary: `manifests/h001_splits_v1.verify.json`
- Runtime module: `runtime/h001_runtime/split_manifest.py`
- Calibration split: 50 rows across 5 scenes
- First evaluation target: at least 100 rows across 10 scenes

### 에이전트 추론

Episode identity should include dataset, split, source file, row index, source episode id, scene id, and target/query. Do not tune `semantic_uncertainty_trigger`, tie band, feature weights, scene replacement, or candidate backend after seeing held-out first-evaluation results.

## Primary Metrics

Report these for every non-oracle policy:

- `Success Rate`
- `SPL`
- `DTS` or distance to success if available
- `wrong_goal_visit_rate`
- `mean_wasted_path_total`
- `mean_wasted_path_wrong_goal`
- `mean_wasted_path_reobserve`
- `mean_num_reobservations`
- `mean_travel_cost_to_reobserve`

## Uncertainty Metrics

Report when candidate labels are available:

- uncertainty vs wrong-goal `AUROC`
- uncertainty vs wrong-goal `AUPRC`
- Spearman correlation between `U_sem` and candidate failure
- calibration bins: `U_sem` bucket vs wrong-goal probability

## SLAM / Map Extension Metrics

Use these after Step 1-3 is stable:

- semantic map accuracy or object precision / recall
- map consistency before/after re-observation
- pose graph connectivity
- ATE/RPE if trajectory ground truth is available
- localization failure count

## Primary Baselines

| Baseline | Uses semantic map? | Uses re-observation? | Uses GT? | Role |
| --- | --- | --- | --- | --- |
| `NoReobserve` | yes | no | no | direct commit baseline |
| `RandomReobserve` | yes | yes | no | tests whether any extra view helps |
| `FrontierReobserve` | partial | yes | no | geometry / exploration baseline |
| `CAReStyle` | yes | replan/confidence only | no | semantic confidence baseline |
| `SemanticOnly` | yes | yes | no | proposed semantic utility without SLAM |
| `SLAMOnly` | no or limited | yes | no | later Step 4-5 geometry/SLAM utility |
| `SemanticSLAM` | yes | yes | no | final H001 policy |

## Ground-truth References

GT policies are not deployable baselines. They are upper bounds and diagnostic controls.

| Reference | Role |
| --- | --- |
| `GTTargetOracle` | shortest path to valid target; path-efficiency upper bound |
| `GTCandidateOracle` | chooses correct semantic candidate if candidate set contains one |
| `GTViewOracle` | chooses best re-observation viewpoint using target/candidate correctness |

Use GT for candidate correctness labels, shortest-path reference, and oracle upper bounds. Do not tune proposed policy with GT on evaluation splits.

## Ablations

Feature ablations:

- `score_uncertainty` only
- `margin_uncertainty` only
- support feature only
- `score + margin`
- `score + margin + support`

Policy ablations:

- no travel-cost penalty
- fixed `theta_uncertain`
- percentile-based `theta_uncertain`
- re-observe top-1 only
- re-observe top-k ambiguous candidates

Step 4-5 ablations:

- semantic-only utility
- SLAM-only utility
- semantic + SLAM utility
- no pose graph connectivity term

## Wrong-goal Metric Decision

Primary wrong-goal metric is commit-based.

Count `wrong_goal_visit = true` only when:

- the policy explicitly commits to a semantic candidate as goal
- the candidate is not a valid target by GT label or accepted synonym group
- the agent reaches the candidate neighborhood or executes stop/commit
- traveled distance exceeds `wrong_goal_min_path`

Near-candidate pass-through is logged as `wrong_goal_pass_through` and reported only as diagnostic.

## Statistical Reporting

For each benchmark and split:

- report mean over episodes
- report 95 percent bootstrap confidence intervals
- report paired deltas against `NoReobserve` and strongest non-GT baseline on the same episodes
- report per-scene aggregate when enough scenes exist
- separate HM3D-OVON `val_seen`, `val_unseen`, and `val_seen_synonyms`

## Success Criteria

H001 first probe is promising if:

- `wrong_goal_visit_rate` decreases against `NoReobserve`
- `mean_wasted_path_wrong_goal` decreases against `NoReobserve`
- `SPL` does not drop beyond the accepted re-observation cost threshold
- `U_sem` has measurable relation with candidate failure
- `SemanticOnly` beats `RandomReobserve` on failure decomposition, not only path length

## First-Probe Hard Validity Gate

The first probe is invalid unless:

- all compared policies run on the exact same episode ids;
- non-GT policies do not use GT labels, target ids, or shortest paths for action selection;
- GT is used only for candidate correctness labels, shortest-path references, and oracle upper bounds;
- `wrong_goal_visit` is commit-based;
- `wrong_goal_pass_through` is diagnostic only;
- every episode has a logged termination reason;
- at least 70 percent of evaluated episodes have usable candidate correctness labels;
- at least 50 percent of evaluated episodes contain both a reachable correct candidate and a reachable distractor candidate;
- `NoReobserve` wrong-goal visit rate is at least 10 percent.

## Primary Numeric Gate

`SemanticOnly` is first-probe positive against `NoReobserve` if all primary thresholds pass:

| Metric | Required threshold |
| --- | --- |
| `wrong_goal_visit_rate` | at least 5 percentage-point absolute reduction and at least 20 percent relative reduction |
| `mean_wasted_path_wrong_goal` | at least 0.5 m absolute reduction and at least 15 percent relative reduction |
| `SPL` | drop no worse than 0.03 absolute and no worse than 10 percent relative |
| `Success Rate` | drop no worse than 3 percentage points |
| `mean_wasted_path_total` | no increase above 0.5 m absolute or 10 percent relative |
| `mean_num_reobservations` | no more than 1.5 per episode on average |

## Policy Objective Revision Gate

### 사실

The current diagnostic `SemanticOnly` objective can change the final candidate during re-observation. This must be measured explicitly before any revised policy is promoted.

### 에이전트 추론

A top-tier claim should not present reachability-biased candidate switching as semantic verification. Revised policies must separate:

- re-observation trigger;
- viewpoint selection;
- post-reobservation evidence update;
- final commit or candidate switch.

Additional required metrics for revised semantic policies:

- `final_candidate_changed_rate`
- `switch_gate_pass_rate`
- `mean_score_delta_after_reobserve`
- `mean_U_sem_delta_after_reobserve`
- `mean_wasted_path_reobserve`

Policy progression:

| Policy | Role | Promotion condition |
| --- | --- | --- |
| `SemanticOnly` | current diagnostic policy | run unchanged after substrate gate passes |
| `SemanticVerifyTop` | no-switch verification ablation | isolates premature switching and re-observation cost |
| `EvidenceGatedSemanticOnly` | revised semantic utility | may switch only after non-GT evidence delta passes predeclared gates |

Do not tune switch gates on held-out `first_eval`.

## Expanded Retrieval Guard Gate

### 사실

- Analysis-only guard design output: `local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1`
- Non-GT proxy feature audit output: `local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1`
- Route counts: `request_backend_retrieval_revision 2`, `request_detector_guarded_observation 5`, `request_lightweight_confirmation 1`
- Detector evidence allowed rows: `6/8`
- Terminal commit rows: `0`
- `guard_design_gate_passed`: `true`
- Proxy route counts: `request_detector_guarded_observation_proxy 8`
- Source-pool validity proxy recall: `0.0`
- Evidence-allowed target recall: `1.0`
- `proxy_ready_for_detector_gate`: `false`
- Source-pool validity proxy output: `local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1`
- Source-pool proxy route counts: `request_backend_retrieval_revision_proxy 2`, `request_detector_guarded_observation_proxy 6`
- Source-pool proxy recall: `1.0`
- Source-pool proxy evidence-allowed target recall: `1.0`
- Source-pool proxy backend targets escalated to evidence: `0`
- Source-pool proxy evidence targets blocked as backend: `0`
- Source-pool proxy consumed forbidden rows: `0`
- Source-pool `proxy_ready_for_detector_gate`: `true`
- Detector evidence contract: `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_detector_evidence_v1.json`
- Detector plan output: `local_dataset/runs/h001_expanded_retrieval_detector_plan_v1`
- Detector plan rows: `42`
- Detector planned request rows: `6`
- Detector plan rows per request min/max: `5/8`
- Detector zero/near-standoff rows: `0/0`
- Detector fallback rows: `0`
- Detector plan consumed forbidden action fields: `0`
- Detector frame output: `local_dataset/runs/h001_expanded_retrieval_detector_frames_v1`
- Detector frame rows/headings: `42/168`
- Detector nonblank dropped rows / removed blank headings: `0/0`
- Detector/SAM2 substrate output: `local_dataset/runs/h001_expanded_retrieval_detector_substrate_v1`
- Detector/SAM2 substrate job status: `completed`
- Detector box / SAM2 mask rates: `1.0 / 1.0`
- Candidate association rate: `0.0714`
- Rows with candidate association: `3/42`
- Detector substrate gate: `false`
- Projection status counts: `out_of_fov 134`, `visible 34`
- Depth check counts: `consistent 6`, `depth_mismatch 28`, `out_of_fov 134`
- `uses_gt_for_action`: `false`
- `uses_gt_for_analysis`: `true`
- `paper_claim_allowed`: `false`

### 에이전트 추론

This guard defines target behavior, not an action-time method. The first non-GT proxy feature audit extracts usable action-time features but fails the source-pool validity gate. The stronger source-pool proxy passes the current diagnostic gate without GT action inputs, but it was designed from this diagnostic evidence and is not a paper-facing claim. A detector/viewpoint evidence gate is now allowed only for proxy detector-eligible rows and must still estimate:

- source-pool validity risk;
- wrong-goal distractor risk;
- whether evidence acquisition is allowed;
- whether terminal commit remains blocked.

Current candidate-set score/support/margin/spatial/reachability features were insufficient because both `source_pool_no_valid_candidate` rows were routed to detector evidence rather than backend revision. The source-pool score-shape proxy fixes this diagnostic blocker, and the detector standoff frame gate shows detector frames can be collected without zero-standoff or blank-frame substrate failures. However, the first detector/SAM2 substrate failed candidate association. Failure diagnostic output `local_dataset/runs/h001_expanded_retrieval_detector_failure_diagnostic_v1` accounts for `42` candidate observation rows and `168` heading rows; mechanisms are `projection_never_visible 33`, `mask_overlap_depth_mismatch_only 4`, `associated_success 3`, `visible_projection_no_detector_overlap 1`, and `box_overlap_mask_reject 1`. Detector availability is not the primary blocker. Design output `local_dataset/runs/h001_expanded_retrieval_detector_viewpoint_revision_design_v1` shows all out-of-FOV projections are `x_in_y_above 134`; selected `projection_anchor_height_sweep_v1` recovers `33/33` `projection_never_visible` rows in projection replay. Revised observation/projection smoke passes: plan output `local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1` has plan rows `42`, planned request rows `6`, and fixed offsets `[0.0, 0.4, 0.8, 1.2, 1.6]`; detector-free projection smoke `local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_smoke_v1` has visible rows `42/42`. Fixed-anchor detector/SAM2 rerun `local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1` passes with candidate association rate `0.7381` and associated rows `31/42`. Fresh/predeclared validation source freeze, source-pool proxy, detector plan/frame, projection smoke, detector/SAM2 substrate, detector evidence diagnostic, and ambiguity-aware objective contract gates pass on the small frozen fresh source. Paper-scale source freeze, planner compatibility, source-pool proxy, projection-anchor detector observation plan, upper-anchor frame/projection smoke, detector/SAM2 substrate, detector evidence diagnostic, ambiguity objective application, local-context planner smoke, and local-context frame/projection smoke now pass. Paper-scale evidence is all `multi_strong_saturated_ambiguity`, so the next gate is local-context detector/SAM2 substrate before post-observation evaluation; paper-facing utility claims still require post-observation evaluation and simpler-alternative comparison.

Fresh expanded-retrieval detector substrate:

```text
job: h001-fresh-expanded-detector-20260527-173955
output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_substrate_projection_anchor_v1
status: completed
detector_rows: 51
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.6078
rows_with_candidate_association: 31 / 51
associated_candidate_heading_count: 68
projection_anchor_selected_offset_counts:
  0.0: 8
  1.2: 12
  1.6: 184
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

Ambiguity-aware expanded-retrieval objective contract:

```text
contract: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_ambiguity_objective_v1.json
output: local_dataset/runs/h001_expanded_retrieval_ambiguity_objective_contract_v1
status: completed
request_rows: 6
route_coverage: 1.0
objective_action_counts:
  request_local_context_disambiguation: 5
  request_rank_challenge_confirmation: 1
terminal_commit_rows: 0
contract_gate_passed: true
larger_source_allowed_after_contract: true
terminal_objective_allowed: false
paper_claim_allowed: false
```

사실: The contract consumes detector evidence topology only, routes all fresh diagnostic request rows, and produces no terminal commit.

에이전트 추론: This is the correct transition point from small fresh diagnostic to a larger source freeze. It is not a utility proof because no terminal task outcome is claimed.

Paper-scale expanded-retrieval source:

```text
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_paper_scale_v1.json
source_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_source_v1
source_rows: 23
source_scenes: 10
source_queries: 6
excluded_scene_overlap: 0
action_evidence_forbidden_key_count: 0
paper_scale_gate_passed: true
planner_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_plan_v1
candidate_set_rows: 23
planner_plan_rows: 230
planner_skipped_rows: 0
source_pool_proxy_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_source_pool_validity_proxy_v1
proxy_route_counts:
  request_backend_retrieval_revision_proxy: 2
  request_detector_guarded_observation_proxy: 21
proxy_ready_for_detector_gate: true
detector_plan_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_v1
detector_proxy_request_rows: 21
planned_request_rows: 21
detector_plan_rows: 162
detector_skipped_rows: 48
detector_skipped_reason: standoff_navmesh_required
plan_rows_per_request: 5-10
target_distance_from_viewpoint_m: 1.6335 / 1.7503 / 1.8053
viewpoint_source_counts:
  standoff_navmesh: 162
zero_standoff_rows: 0
near_standoff_rows: 0
fallback_rows: 0
rotation_fallback_rows: 0
detector_plan_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

사실: The larger source is frozen from nonterminal `defer_expanded_retrieval_needed` decisions and is scene-disjoint from the small fresh source used to define the ambiguity contract.

Paper-scale expanded-retrieval frame/projection gate:

```text
initial_frame_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_v1
initial_frame_rows: 162 / 162
initial_rendered_heading_count: 648
initial_nonblank_rows: 162 / 162
initial_removed_blank_heading_count: 0
initial_projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_projection_anchor_smoke_v1
initial_projection_anchor_visible_rows: 153 / 162
initial_projection_anchor_visible_rate: 0.9444
initial_projection_gate_passed: false
initial_failure_slice: bxsVRursffK / plant
initial_failure_axis: x_in_y_above

upper_anchor_plan_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_upper_v1
upper_anchor_offsets_m: [0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4]
upper_anchor_frame_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_upper_v1
upper_anchor_frame_rows: 162 / 162
upper_anchor_rendered_heading_count: 648
upper_anchor_nonblank_rows: 162 / 162
upper_anchor_removed_blank_heading_count: 0
upper_anchor_projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_projection_anchor_upper_smoke_v1
upper_anchor_projection_visible_rows: 162 / 162
upper_anchor_missing_candidate_rows: 0
upper_anchor_projection_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

사실: The upper-anchor repair changes only the fixed projection anchor offsets carried by the plan/frame metadata; it does not change request rows, standoff viewpoints, source-pool proxy routing, or GT separation.

에이전트 추론: This is now large enough for a detector/evidence falsification gate, but still not a terminal ObjectNav utility proof. The detector substrate and detector evidence diagnostic have since passed; the remaining question is whether local-context re-observation can resolve the multi-strong ambiguity safely.

Fresh detector evidence diagnostic:

```text
output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_evidence_diagnostic_v1
status: completed
request_rows: 6
candidate_rows: 51
associated_request_rate: 1.0
strong_request_rate: 1.0
multi_strong_request_rate: 0.8333
lower_rank_only_association_rate: 0.5
evidence_topology_counts:
  multi_strong_saturated_ambiguity: 5
  single_strong_lower_rank: 1
terminal_objective_risk_counts:
  multi_candidate_detector_ambiguity: 5
  source_top_challenged_by_lower_rank_evidence: 1
diagnostic_gate_passed: true
objective_design_allowed: true
terminal_objective_allowed: false
paper_scale_gate_passed: false
paper_claim_allowed: false
```

## Fixed Dense Backend Terminal Diagnostic Contract

### 사실

This contract applies only to the two held-out `y9hTuugGdiq` chair rows that were previously classified as no-correct-candidate backend recall failures.

```text
fixed_dense_backend_artifact: /tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/all_scenes_aligned.jsonl
fixed_dense_backend_verification: recovered 2 / 2, recall@5 1.0, candidate_count 100
strict_detector_observation: /tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_v1
strict_detector_association_rate: 0.0
association_diagnostic_failure: visible_inside_mask_but_depth_or_association_rejects
depth2_detector_observation: /tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1
association_depth_tolerance_m: 2.0
depth2_candidate_association_rate: 0.5
posthoc_commit_evaluation: /tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_repair_commit_evaluation_v1
posthoc_action_commits: 2 / 2
posthoc_success_commits: 2 / 2
posthoc_wrong_goal_commits: 0 / 2
uses_gt_for_action: false
uses_gt_for_analysis: true
```

### Evaluation Boundary

Action selection may use only non-GT semantic scores, detector boxes, SAM2 masks, depth association, branch rows, and evidence summaries.

GT candidate correctness or recall-probe labels may be used only after action selection for:

- post-hoc candidate correctness labeling;
- wrong-goal / success accounting;
- oracle-gap diagnosis;
- scope decisions about whether a diagnostic can be promoted.

Do not interpret built-in evidence gate fields that require `candidate_correct` when dense branch rows do not contain correctness labels. In this diagnostic, `no_valid_external_commit_rate=1.0` is a label-plumbing artifact, not evidence that the committed actions are truly no-valid.

### Allowed Interpretation

- `spatial_nms_p95_k100_d10` can recover correct chair candidates for these two held-out rows without GT action selection.
- `association_depth_tolerance_m=2.0` can recover detector association that strict `1.0m` depth matching rejects in this local chair diagnostic.
- The post-hoc result supports the failure taxonomy: candidate backend recall failure -> detector association depth gate failure -> evaluation-label plumbing failure.
- The result is useful for deciding the next non-GT backend and association validation path.

### Not Allowed

- Do not claim a policy-scale ObjectNav improvement from this diagnostic.
- Do not claim that `association_depth_tolerance_m=2.0` is generally valid across categories, scenes, or detectors.
- Do not report this as `Success Rate`, `SPL`, or `wrong_goal_visit_rate` improvement on `first_eval`.
- Do not merge post-hoc GT labels into action-time branch rows unless the field is explicitly marked evaluation-only.
- Do not use this result to unblock first_eval or policy-scale comparison by itself.

### Promotion Gate

Before using this repair beyond the two-row diagnostic, complete all gates below:

| Gate | Required evidence |
| --- | --- |
| evaluation-label plumbing | action rows and evaluation-only correctness labels are stored separately |
| scene/category expansion | validate on at least one independent scene/query set or all held-out no-correct rows |
| simpler alternatives | compare strict depth `1.0m`, depth `2.0m`, no-depth mask association, and grounded-position association |
| safety | wrong-goal commit does not increase under GT analysis labels |
| utility | commit/success improves over defer-only handling without action-time GT |
| reproducibility | command, image, artifact path, and validation summary are recorded |

### Scope Status

| Scope | Status |
| --- | --- |
| local two-row chair diagnostic | positive |
| general detector association repair | do not generalize yet |
| `first_eval` rerun | blocked |
| policy-scale comparison | blocked |

## Dense Conflict Primary Diagnostic Contract

### 사실

This contract applies to the six primary `h001_dense_conflict_v1` rows selected from `v3_fresh_validation_v1`.

```text
selected_candidate_substrate: v3_fresh_spatial_p97_k20
recall_gate: local_dataset/runs/h001_dense_conflict_recall_gate_v3_fresh_spatial_p97_k20_primary_final_v1
detector_association_validation: local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1
primary_rows: 6
recall_rows_with_correct: 6 / 6
recall_at_20: 1.0
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.8
rows_with_correct_and_wrong_positive_support: 6 / 6
commit / success / wrong / no_valid: 5 / 5 / 0 / 0
selected_correct_improvement_over_source_selected_rows: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Secondary-stress held-out `sofa` rows:

```text
secondary_validation: local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1
secondary_rows: 2
recall_rows_with_correct: 2 / 2
recall_at_20: 1.0
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 1.0
commit / success / wrong / no_valid: 2 / 2 / 0 / 0
selected_correct_improvement_over_source_selected_rows: 2
uses_gt_for_action: false
uses_gt_for_analysis: true
```

### Interpretation Boundary

- This unblocks detector/association validation only for the selected `v3_fresh_spatial_p97_k20` primary diagnostic substrate.
- It does not unblock the failed `spatial_nms_p95_k100_d10` or `spatial_nms_p90_k200_d5` dense re-export substrates.
- It is not yet a policy-scale ObjectNav claim.
- Secondary-stress evidence is positive but too small for generalization because it contains only two `sofa` rows from one scene.
- Promotion requires broader split validation with the same non-GT action path and the same failure taxonomy.

## Dense Conflict Generalization Contract

### 사실

Broader split design output:

```text
local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json
```

Recommended next split:

```text
name: dense_conflict_generalization_v1
type: scene_disjoint_first_eval_style
minimum_rows: 20
minimum_scenes: 5
minimum_queries: 3
minimum_selected_wrong_rows: 6
minimum_rows_with_correct_and_wrong_positive_support: 12
```

Materialized split:

```text
manifest: manifests/h001_dense_conflict_generalization_v1.json
verify: manifests/h001_dense_conflict_generalization_v1.verify.json
manifest_status: frozen_pending_recall_gate
rows: 20
scenes: 9
queries: 6
rows_with_correct_and_wrong_candidates: 20 / 20
source_selected_wrong_rows: 16
NoReobserve wrong-goal rows with correct present: 16
excluded_scene_keys: y9hTuugGdiq
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Non-GT recall gate:

```text
output: local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1
artifact: first_eval_replacement_spatial_nms_p97_k20
primary_rows: 20
rows_with_correct: 20 / 20
recall_at_20: 1.0
recall_at_5: 0.85
first_correct_rank: 1-9
detector_job_allowed: true
```

Detector substrate job:

```text
wrapper: runtime/jobs/dense_conflict_generalization_detector_substrate.sh
tmux_session: h001-dense-conflict-generalization-detector-20260523-170533
output: local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1
status: completed
detector_rows: 20
frame_rows: 20
rendered_heading_count: 125
detector_box_rate: 0.85
sam2_mask_rate: 0.85
candidate_association_rate: 0.35
passes_detector_substrate_gate: true
uses_gt_for_action: false
```

Required slices:

- `selected_wrong_positive_correct_present`
- `correct_and_wrong_positive_selected_correct`
- `repeated_object_local_context_positive_conflict`
- `backend_recall_failure_negative_slice`

### Gate Order

1. Freeze `dense_conflict_generalization_v1` manifest. Completed.
2. Verify manifest uniqueness, scene count, query count, and slice counts. Completed.
3. Run non-GT candidate recall gate before detector rerun. Completed.
4. Keep backend-recall failure rows as a negative slice; do not force them through detector arbitration.
5. Run detector/association only after recall gate passes on the positive slices. Detector substrate completed and passed.

Next required gate:

```text
terminal_arbitration_validation: blocked until evidence extraction keeps GT labels evaluation-only
minimum_terminal_rows: report all 20 rows, but separate associated rows from unassociated rows
minimum_associated_rows: 7 current rows, do not overclaim beyond associated subset
```

Terminal evidence extraction status:

```text
script: runtime/h001_runtime/extract_dense_conflict_generalization_evidence.py
output: local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1
action_evidence_rows: 20
evaluation_label_rows: 55
associated_rows: 7
unassociated_rows: 13
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
```

Current terminal policy diagnostic:

| Variant | Commit rows | Success commits | Wrong-goal commits | Status |
| --- | ---: | ---: | ---: | --- |
| `defer_only` | 0 | 0 | 0 | safe but inert |
| `semantic_top_if_supported` | 7 | 1 | 6 | reject |
| `first_associated` | 7 | 1 | 6 | reject |
| `support_score_best` | 7 | 3 | 4 | reject |
| `proposed_conservative_v0` | 7 | 3 | 4 | reject |

### Gate Update

Do not run a paper-facing terminal arbitration validation with `proposed_conservative_v0`.

The next fixed rule is:

```text
guard_name: strict_depth_consistency_v1
source: local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1/terminal_guard_design_summary.json
max_depth_error_m: 0.33
min_associated_heading_count: 2
min_mask_hit_count: 2
max_semantic_rank: 5
same_split_commit_success_wrong: 3 / 3 / 0
associated_commit_rate: 3 / 7
uses_gt_for_action: false
paper_claim_status: same_split_guard_design_not_method_claim
```

Run terminal arbitration validation only after freezing this guard unchanged. The validation script must consume `action_evidence_rows.jsonl` for decisions, join `evaluation_labels.jsonl` only after actions are frozen, and report associated/unassociated rows separately.

Fixed-rule validation status:

```text
config: manifests/h001_dense_conflict_terminal_guard_v1.json
script: runtime/h001_runtime/validate_dense_conflict_terminal_arbitration.py
output: local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1
action_evidence_forbidden_key_count: 0
stable_metric_match_design: true
local_fixed_rule_validation_passed: true
rows: 20
associated_rows: 7
commit_success_wrong: 3 / 3 / 0
associated_commit_success_wrong: 3 / 3 / 0
uses_gt_for_action: false
paper_claim_status: same_split_fixed_rule_validation_not_method_claim
```

Promotion remains blocked for paper-facing utility claims until the same frozen guard passes an independent validation split with enough associated rows and a predeclared failure taxonomy.

Independent terminal validation contract:

```text
contract: manifests/h001_dense_conflict_terminal_independent_v1.json
primary_source: dense_conflict_v1_v3_fresh_primary
primary_profile: local_dataset/runs/h001_dense_conflict_independent_terminal_evidence_profile_v1
primary_rows: 6
primary_associated_rows: 6
primary_scenes: 3
primary_queries: 2
secondary_stress_profile: local_dataset/runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1
secondary_stress_rows: 2
scene_overlap_with_design_split_allowed: false
```

Predeclared gate:

```text
primary_wrong_goal_commit_rows == 0
primary_no_label_commit_rows == 0
primary_success_commit_rows >= 1
primary_commit_rows >= 1
secondary_stress_wrong_goal_commit_rows == 0
paper_claim_allowed_after_pass: false
```

If this independent validation fails, classify the failure using the contract taxonomy before changing thresholds or detector inputs.

### 에이전트 추론

Independent validation result:

```text
primary_output: local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1
primary_commit_success_wrong: 6 / 2 / 4
primary_no_label_commit_rows: 0
primary_gate_passed: false
primary_failure_taxonomy: guard_wrong_commit_depth_consistent_wrong_instance = 4
secondary_output: local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1
secondary_commit_success_wrong: 2 / 0 / 2
secondary_gate_passed: false
secondary_failure_taxonomy: stress_slice_wrong_commit = 2
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
```

`strict_depth_consistency_v1` must be rejected as an independent terminal arbitration rule. `scene_disjoint_first_eval_style` remains the right top-tier-aligned path, but the next step is failure-row diagnosis and a mechanism-level arbitration revision, not policy-scale evaluation or threshold tuning on the failed validation split. HM3D-OVON is deferred as external validity, not the immediate next gate.

Failure diagnosis result:

```text
output: local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1
wrong_goal_commit_rows: 6
success_commit_rows: 2
wrong_primary_mechanism_counts:
  repeated_wrong_instance_selected_by_saturated_support: 5
  guard_cannot_arbitrate_between_eligible_correct_and_wrong: 1
wrong_mechanism_tags:
  correct_candidate_present: 6
  correct_candidate_positive_support_present: 6
  wrong_candidate_passes_frozen_guard: 6
  wrong_support_score_ge_correct: 6
  support_score_saturated: 6
  detector_score_tie_or_wrong_advantage: 6
  wrong_semantic_rank_as_good_or_better: 6
```

Mechanism-level revision contract:

```text
revision_name: rival_identity_confirmation_v1
status: design_contract_not_implemented
principle: dense same-category positive support is identity ambiguity, not terminal commit evidence
proposed primary action: request_rival_identity_confirmation
paper_claim_status: design_only_until_fresh_or_predeclared_validation
```

The next implementation may use this contract as a diagnostic policy, but must still avoid `evaluation_only_candidate_correct`, recall rank, GT position, or GT geodesic distance in action-time inputs.

Rival identity diagnostic policy result:

```text
output: local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1
diagnostic_passed: true
action_evidence_forbidden_key_count: 0
rival_identity_confirmation_v1:
  commit/success/wrong: 2 / 2 / 0
  request_rival_identity_confirmation_rows: 6
  primary_success_commit_rows: 2
  primary_wrong_goal_commit_rows: 0
  secondary_wrong_goal_commit_rows: 0
strict_depth_consistency_v1:
  commit/success/wrong: 8 / 2 / 6
defer_all_ambiguous:
  commit/success/wrong: 0 / 0 / 0
```

This passes the local diagnostic gate because it preserves nonzero primary success while removing wrong-goal commits. It does not pass a paper-facing utility gate. The later fresh-source validation completed the observation, detector, and analyzer path, but failed the post-observation gate because two single-candidate `toilet` false positives were committed as wrong goals.

Active observation contract:

```text
contract: manifests/h001_rival_identity_observation_v1.json
contract_name: rival_identity_observation_v1
request_rows: 6
primary_request_rows: 4
secondary_stress_request_rows: 2
planner_name: rival_identity_pair_probe_v1
```

Minimum implementation gates:

```text
planned_rows_minimum >= 6
action_evidence_forbidden_key_count == 0
detector_box_rate >= 0.80
sam2_mask_rate >= 0.80
candidate_association_rate >= 0.50
wrong_goal_commit_rows == 0
no_label_commit_rows == 0
new_primary_success_commit_rows >= 1
resolved_request_rows >= 1
secondary_stress_wrong_goal_commit_rows == 0
```

Plan smoke result:

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
output: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1
request_rows: 6
planned_request_rows: 6
plan_rows: 19
skipped_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
plan_smoke_passed: true
```

This satisfies only the minimum plan gate. Frame export, detector association, and post-observation validation remain required before any utility claim.

Frame export smoke result:

```text
renderer: runtime/h001_runtime/export_postview_frames_v2.py
output: local_dataset/runs/h001_rival_identity_pair_probe_frames_v1
rows_requested: 19
rows_exported: 19
rendered_heading_count: 142
rgb_files: 142
depth_files: 142
unique_scenes: 3
candidate_point_field: grounded_position
uses_gt_for_action: false
nonblank_rgb_sanity: pass
```

This satisfies only the renderability gate. Detector/SAM2 association and post-observation validation remain required before any utility claim.

Detector substrate job contract:

```text
script: runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
status: completed
frames: local_dataset/runs/h001_rival_identity_pair_probe_frames_v1/rival_identity_frame_summary.jsonl
candidate_artifact: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_candidate_artifact.jsonl
output: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1
expected_frame_rows: 19
candidate_point_field: grounded_position
query_template: "{query}"
box_threshold: 0.10
text_threshold: 0.10
association_depth_tolerance_m: 1.0
detector_box_rate_minimum: 0.80
sam2_mask_rate_minimum: 0.80
candidate_association_rate_minimum: 0.50
```

Pre-launch verification:

```text
bash -n: pass
frame_rows: 19
candidate_artifact_rows: 3
rival_identity_request_id_trace_rows: 19
```

Detector substrate result:

```text
output: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_substrate_summary.json
detector_rows: 19
detector_box_rate: 0.8421
sam2_mask_rate: 0.8421
candidate_association_rate: 0.6316
rows_with_candidate_association: 12
associated_candidate_heading_count: 57
uses_gt_for_action: false
passes_detector_substrate_gate: true
```

Passing this substrate gate is not a utility claim; it only allows post-observation evidence and validation to be evaluated.

Post-observation evidence/validation contract:

```text
status: analyzer_run_diagnostic_passed
evidence_input: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_associations.jsonl
plan_input: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_observation_plan.jsonl
primary_label_input: local_dataset/runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/evaluation_labels.jsonl
secondary_label_input: local_dataset/runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/evaluation_labels.jsonl
evidence_output: local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1/rival_identity_post_observation_evidence.jsonl
decision_output: local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1/rival_identity_post_observation_decisions.jsonl
summary_output: local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1/rival_identity_observation_validation_summary.json
```

Evidence/action separation:

- Action-time evidence may use `rival_identity_request_id`, `episode_key`, `query`, `role`, `request_reason`, `focus_candidate_id`, `rival_candidate_ids`, candidate geometry, semantic/support fields, target viewpoint metadata, detector box score, mask projection, depth agreement, and `associated_to_candidate`.
- Action-time evidence must not use `evaluation_only_candidate_correct`, `evaluation_only_selected_correct`, `evaluation_only_wrong_goal_commit`, `evaluation_only_success_commit`, recall rank, GT object position, GT geodesic distance, or any success/wrong label.
- Evaluation labels are joined only after `rival_identity_post_observation_decisions.jsonl` is written.
- Label join key is `(episode_key, candidate_id)`.
- Request join key is `rival_identity_request_id`; fallback validation should also require `(episode_key, query, role)` to match.

Frozen post-observation evidence fields per `(rival_identity_request_id, candidate_id)`:

```text
post_associated_heading_count: count(associated_to_candidate)
post_own_associated_heading_count: count(associated_to_candidate and candidate_id == target_candidate_id)
post_cross_associated_heading_count: count(associated_to_candidate and candidate_id != target_candidate_id)
post_best_box_score: max(best_box_score)
post_min_depth_error_m: min(depth_error_m)
post_own_target_role_count: count(unique target roles where candidate_id == target_candidate_id and associated_to_candidate)
post_cross_target_role_count: count(unique target roles where candidate_id != target_candidate_id and associated_to_candidate)
post_identity_margin: post_own_associated_heading_count - max(other candidates' post_own_associated_heading_count)
```

Frozen decision rule:

```text
strong_identity_evidence(candidate) =
  post_own_associated_heading_count >= 2
  and post_own_associated_heading_count > post_cross_associated_heading_count
  and post_identity_margin >= 2

if exactly one candidate has strong_identity_evidence:
  action = commit_candidate
  selected_candidate_id = that candidate
else:
  action = defer_unresolved_identity
  selected_candidate_id = null
```

Rule constraints:

- No category-specific branch for `chair`, `plant`, `sofa`, or other query names.
- No fallback commit to semantic top when post-observation evidence is absent or non-discriminative.
- No threshold sweep on the six request rows after evaluation labels are joined.
- If a committed candidate has no label, count it as `no_label_commit_rows` and classify as `label_plumbing_failure`, not as success.

Validation metrics:

```text
request_rows
resolved_request_rows
commit_rows
success_commit_rows
wrong_goal_commit_rows
no_label_commit_rows
new_primary_success_commit_rows
primary_wrong_goal_commit_rows
secondary_stress_wrong_goal_commit_rows
defer_unresolved_identity_rows
identity_evidence_non_discriminative_rows
post_observation_no_candidate_support_rows
post_observation_cross_view_aliasing_rows
```

Additional failure taxonomy:

| Failure code | Interpretation |
| --- | --- |
| `post_observation_no_candidate_support` | no candidate gets own-view detector association after active observation |
| `post_observation_cross_view_aliasing` | a candidate is associated mainly from another candidate's target view |
| `post_observation_multiple_strong_candidates` | more than one candidate satisfies the strong identity rule |
| `post_observation_margin_too_small` | own-view support exists but is not separated from the nearest rival |
| `post_observation_safe_defer` | no commit is made because the evidence is weak or ambiguous |

This contract is implemented by `runtime/h001_runtime/analyze_rival_identity_post_observation.py`. It must not be changed based on the post-join success/wrong labels from the six diagnostic request rows.

Post-observation analyzer Docker smoke result:

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
output: local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1
summary: rival_identity_observation_validation_summary.json
request_rows: 6
evidence_rows: 19
decision_rows: 6
commit_rows: 1
success_commit_rows: 1
wrong_goal_commit_rows: 0
no_label_commit_rows: 0
new_primary_success_commit_rows: 1
secondary_stress_wrong_goal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
post_observation_gate_passed: true
```

Failure taxonomy result:

```text
none: 1
post_observation_no_candidate_support: 3
post_observation_cross_view_aliasing: 2
```

The single commit is `DYehNKdT76V/chair` selecting `vlmaps:export:chair:spatial_nms:2`, which is a post-join success label. The three `7MXmsvcQjpJ/plant` primary rows defer because post-observation detector support does not associate to the candidates. The two `y9hTuugGdiq/sofa` stress rows defer because cross-view aliasing remains stronger than a safe identity margin.

Required baselines:

- `strict_depth_consistency_v1`
- `rival_identity_confirmation_v1_without_observation`
- `support_margin_only`
- `depth_margin_only`
- `semantic_top_only`
- `defer_all_ambiguous`

This result remains diagnostic-only. A paper-facing utility claim is blocked until the same frozen analyzer is evaluated on a fresh or predeclared validation source.

Fresh/predeclared validation source design:

```text
source_name: rival_identity_generalization_v1
parent_split: dense_conflict_generalization_v1
parent_manifest: manifests/h001_dense_conflict_generalization_v1.json
action_evidence: local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1/action_evidence_rows.jsonl
evaluation_labels: local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1/evaluation_labels.jsonl
design_probe: local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1
scope: primary rows only
exclude_previous_diagnostic_scenes: DYehNKdT76V, 7MXmsvcQjpJ, y9hTuugGdiq
selection_rule: run frozen rival_identity_confirmation_v1 on action-time evidence and keep rows with action == request_rival_identity_confirmation
label_use_for_selection: forbidden
```

Design probe facts:

```text
parent_rows: 20
parent_scenes: 9
parent_queries: bed, chair, plant, sofa, toilet, tv_monitor
selected_request_rows: 6
selected_request_scenes: 5cdEh9F2hJL, CrMo8WxCyVb, mL8ThkuaVTM
selected_request_queries: bed, toilet
request_reason_counts:
  request_identity_no_guard_eligible_positive_candidates: 4
  request_identity_unique_guard_eligible_not_semantic_top: 2
primary strict_depth_consistency_v1 on design probe:
  commit/success/wrong: 3 / 3 / 0
primary rival_identity_confirmation_v1 on design probe:
  commit/success/wrong/request: 1 / 1 / 0 / 6
```

Source-freeze result:

```text
source_miner: runtime/h001_runtime/build_rival_identity_generalization_manifest.py
source_output: local_dataset/runs/h001_rival_identity_generalization_source_v1
manifest: manifests/h001_rival_identity_generalization_v1.json
verify: manifests/h001_rival_identity_generalization_v1.verify.json
manifest_status: frozen
verify_ok: true
request_rows: 6
request_scenes: 3
request_queries: 2
overlap_with_previous_diagnostic_scenes: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
```

Planner smoke result:

```text
planner_output: local_dataset/runs/h001_rival_identity_generalization_plan_v1
request_rows: 6
planned_request_rows: 6
plan_rows: 12
skipped_rows: 0
candidate_artifact_rows: 4
candidate_artifact_candidates: 7
plan_gate: true
uses_gt_for_action: false
```

Frame export smoke result:

```text
frame_output: local_dataset/runs/h001_rival_identity_generalization_frames_v1
frames: rival_identity_frame_summary.jsonl
rows_requested: 12
rows_exported: 12
rendered_heading_count: 72
rgb_files: 72
depth_files: 72
unique_scenes: 3
candidate_point_field: grounded_position
nonblank_rgb_sanity: pass
uses_gt_for_action: false
```

Detector/SAM2 substrate job status:

```text
tmux_session: h001-rival-identity-generalization-detector-20260526-102744
status: completed
frames: local_dataset/runs/h001_rival_identity_generalization_frames_v1/rival_identity_frame_summary.jsonl
candidate_artifact: local_dataset/runs/h001_rival_identity_generalization_plan_v1/rival_identity_candidate_artifact.jsonl
output: local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1
log: runtime/logs/rival-identity-generalization-detector-substrate-20260526-102744.log
expected_frame_rows: 12
detector_rows: 12
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 1.0
associated_candidate_heading_count: 84
detector_substrate_gate: true
uses_gt_for_action: false
```

Fresh-source post-observation analyzer result:

```text
output: local_dataset/runs/h001_rival_identity_generalization_post_observation_v1
request_rows: 6
evidence_rows: 12
decision_rows: 6
commit/success/wrong/no-label: 4 / 2 / 2 / 0
new_primary_success_commit_rows: 2
resolved_request_rows: 4
failure_taxonomy_counts:
  none: 2
  post_observation_cross_view_aliasing: 2
  unsafe_post_observation_commit: 2
post_observation_gate_passed: false
uses_gt_for_action: false
```

Fresh validation gates after observation:

```text
wrong_goal_commit_rows == 0
no_label_commit_rows == 0
new_primary_success_commit_rows >= 1
resolved_request_rows >= 1
action_evidence_forbidden_key_count == 0
uses_gt_for_action == false
```

Gate interpretation:

- 사실: The frozen analyzer resolves two `bed` requests successfully and defers two ambiguous `bed` requests, but commits wrong goals on two `toilet` requests.
- 에이전트 추론: These failures are not dense same-category rival ambiguity. Both failed `toilet` rows have only one focus candidate in the observation plan, strong own-view detector association, and post-join labels mark that candidate as wrong. The failure mechanism is closer to object-existence false positive than rival-identity arbitration.
- 사용자 판단 필요: Decide whether `request_identity_no_guard_eligible_positive_candidates` should remain in the rival-identity branch or be routed to a separate object-existence validation branch.

Fresh-source failure diagnostic:

```text
diagnostic_script: runtime/h001_runtime/diagnose_rival_identity_generalization_failures.py
output: local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1
diagnostic_passed: true
mechanism_counts:
  rival_identity_resolved_success: 2
  rival_identity_unresolved_cross_view_aliasing: 2
  single_candidate_object_existence_false_positive: 2
proposed_route_counts:
  keep_in_rival_identity_arbitration: 4
  object_existence_validation: 2
request_identity_no_guard_eligible_positive_candidates:
  rival_identity_unresolved_cross_view_aliasing: 2
  single_candidate_object_existence_false_positive: 2
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Facts:

- The detector substrate passed with detector box / SAM2 / candidate association rates `1.0 / 1.0 / 1.0`.
- All wrong commits are explained by single-positive-candidate `toilet` false positives.
- `request_identity_no_guard_eligible_positive_candidates` is a mixed request reason, not a stable mechanism label.

Agent inference:

- Single-positive-candidate requests need an object-existence validation branch before any commit rule is promoted.
- Multi-positive requests can remain in rival-identity arbitration.
- Candidate/rival count split is required before changing thresholds; this split is implemented in the taxonomy run below.

Fresh-source taxonomy split:

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
output: local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1
status: Docker py_compile and analyzer rerun passed
request_taxonomy_route_counts:
  rival_identity_arbitration: 4
  object_existence_validation: 2
failure_taxonomy_counts:
  none: 2
  rival_identity_unresolved_cross_view_aliasing: 2
  object_existence_false_positive_commit: 2
unsafe_rival_identity_commit_rows: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
post_observation_gate_passed: false
```

Decision:

- The split is accepted.
- `request_reason` remains a planner/action reason, not a mechanism label.
- `request_taxonomy_route == rival_identity_arbitration` covers multi-positive candidate requests with planned rival contrast.
- `request_taxonomy_route == object_existence_validation` covers single-positive candidate requests and must not use the same unique-strong-identity commit rule.
- The no-commit object-existence validation branch for single-positive requests is implemented below.

Object-existence no-commit branch:

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
rule: if request_taxonomy_route == object_existence_validation, action = defer_object_existence_validation
reason: object_existence_requires_independent_confirmation
fresh_output: local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1
regression_output: local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1
```

Fresh-source result:

```text
action_counts:
  commit_candidate: 2
  defer_object_existence_validation: 2
  defer_unresolved_identity: 2
failure_taxonomy_counts:
  none: 2
  object_existence_deferred_no_independent_confirmation: 2
  rival_identity_unresolved_cross_view_aliasing: 2
commit / success / wrong: 2 / 2 / 0
request_taxonomy_route_counts:
  rival_identity_arbitration: 4
  object_existence_validation: 2
post_observation_gate_passed: true
uses_gt_for_action: false
```

Regression result on the earlier diagnostic source:

```text
output: local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1
commit / success / wrong: 1 / 1 / 0
request_taxonomy_route_counts:
  rival_identity_arbitration: 6
post_observation_gate_passed: true
uses_gt_for_action: false
```

Interpretation:

- 사실: The no-commit branch removes the two fresh-source `toilet` wrong-goal commits without changing the earlier multi-candidate diagnostic success.
- 에이전트 추론: This is a safety repair, not an object-existence utility proof. A paper-facing method still needs independent evidence that can distinguish true single-object goals from false-positive object candidates.
- 사용자 판단 필요: None for the safety branch; future object-existence confirmation should be evaluated separately before allowing any single-positive commit.

Independent object-existence validation probe:

```text
script: runtime/h001_runtime/analyze_object_existence_validation_probe.py
output: local_dataset/runs/h001_rival_identity_object_existence_probe_v1
target_rows: request_taxonomy_route == object_existence_validation
current_policy: defer_object_existence_validation
naive_baseline: unique strong object-like candidate would commit without the no-commit safety branch
```

Probe result:

```text
request_rows: 2
query_counts:
  toilet: 2
naive_unique_strong_commit_rows: 2
naive_wrong_goal_commit_rows: 2
naive_success_commit_rows: 0
wrong_goal_avoided_by_defer_rows: 2
success_lost_by_defer_rows: 0
wrong_goal_avoided_by_defer_rate: 1.0
success_lost_by_defer_rate: 0.0
action_evidence_forbidden_key_count: 0
probe_design_passed: true
paper_claim_allowed: false
```

Interpretation:

- 사실: On this source, the no-commit branch is not hiding a success; it avoids two wrong-goal commits.
- 에이전트 추론: The current object-existence probe supports keeping single-positive rows in defer until independent confirmation evidence exists.
- 사용자 판단 필요: No paper-facing object-existence commit rule should be promoted from two `toilet` rows only.

Broader fresh-source validation design:

```text
script: runtime/h001_runtime/design_rival_identity_broader_validation.py
output: local_dataset/runs/h001_rival_identity_broader_validation_design_v1
design_name: rival_identity_broader_validation_v1
preferred_source: risk_validation
source_candidate_decisions: local_dataset/runs/h001_risk_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/candidate_decisions.jsonl
excluded_scenes:
  DYehNKdT76V
  7MXmsvcQjpJ
  y9hTuugGdiq
  5cdEh9F2hJL
  CrMo8WxCyVb
  mL8ThkuaVTM
```

Design result:

```text
selected_parent_rows: 72
selected_parent_scenes: 10
selected_parent_queries: 6
estimated_request_rows: 22
expected_request_rate_from_prior_source: 0.30
top_wrong_goal_rows: 41
top_wrong_rows: 61
rows_with_correct_and_wrong_candidates: 49
episode_class_counts:
  rival_identity_likely_wrong_goal: 24
  rival_identity_likely_selected_wrong: 14
  object_existence_or_backend_recall_negative: 23
  rival_identity_control_selected_correct: 11
design_gate_passed: true
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Actual miner result:

```text
script: runtime/h001_runtime/build_rival_identity_broader_manifest.py
output: local_dataset/runs/h001_rival_identity_broader_source_v1
manifest: manifests/h001_rival_identity_broader_validation_v1.json
verify: manifests/h001_rival_identity_broader_validation_v1.verify.json
request_rows: 30
request_scenes: 10
request_queries: 6
request_taxonomy_route_counts:
  rival_identity_arbitration: 26
  object_existence_validation: 4
excluded_scene_overlap: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
source_freeze_gate_passed: true
```

Planner smoke result:

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
output: local_dataset/runs/h001_rival_identity_broader_plan_v1
request_rows: 30
planned_request_rows: 30
plan_rows: 112
skipped_rows: 0
missing_action_rows: 0
candidate_artifact_rows: 21
candidate_artifact_candidates: 80
action_evidence_forbidden_key_count: 0
plan_gate: true
uses_gt_for_action: false
```

Frame export and nonblank filter result:

```text
renderer: runtime/h001_runtime/export_postview_frames_v2.py
filter: runtime/h001_runtime/filter_nonblank_frame_summary.py
frame_output: local_dataset/runs/h001_rival_identity_broader_frames_v1
filtered_frame_summary: local_dataset/runs/h001_rival_identity_broader_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
rows_requested: 112
rows_exported: 112
rendered_heading_count: 862
rgb_files: 862
depth_files: 862
metadata_files: 862
unique_scenes: 10
removed_blank_heading_count: 56
rows_with_blank_headings: 20
dropped_rows: 0
kept_heading_count: 806
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: false
uses_gt_for_action: false
```

Interpretation:

- 사실: `risk_validation` is scene-disjoint from the previous diagnostic and current fresh-source scenes under the explicit exclusion list.
- 에이전트 추론: The broader miner, row-level frame substrate, and corrected detector substrate pass, but the broader post-observation failure diagnosis shows the current planner used zero-standoff viewpoints for every target. The next gate is `rival_identity_broader_standoff_planner_v1`, not threshold tuning.
- 사용자 판단 필요: None before detector/SAM2 substrate job.

Zero-standoff-safe planner revision:

```text
contract: manifests/h001_rival_identity_broader_standoff_planner_v1.json
trigger_diagnostic: local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1
current_failure:
  zero_standoff_plan_rows: 112
  rotation_fallback_plan_rows: 112
  own_associated_rows: 0
  cross_associated_rows: 442
revision: replace candidate_visit_position/position fallback with non-GT standoff viewpoints
reuse:
  runtime/h001_runtime/plan_association_recovery_observation.py::NavmeshSnapper
  runtime/h001_runtime/plan_association_recovery_observation.py::plan_standoff_viewpoint
minimum_geometry_gate:
  zero_standoff_plan_rows: 0
  near_standoff_plan_rows: 0
  rotation_fallback_plan_rows: 0
  target_distance_from_viewpoint_min_m: 0.75
  planned_request_rows_minimum: 20
  planned_scene_count_minimum: 5
  planned_query_count_minimum: 3
post_observation_rule_change_allowed_before_standoff_gate: false
```

Zero-standoff-safe planner implementation result:

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
mode: --viewpoint-mode standoff
output: local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1
docker_syntax_smoke: passed
plan_gate: true
geometry_gate: true
request_rows: 30
planned_request_rows: 30
plan_rows: 112
skipped_rows: 0
planned_scene_count: 10
planned_query_count: 6
zero_standoff_plan_rows: 0
near_standoff_plan_rows: 0
rotation_fallback_plan_rows: 0
candidate_fallback_plan_rows: 0
target_distance_from_viewpoint_min_mean_max_m: 1.6386 / 1.7506 / 1.9747
viewpoint_source_counts:
  standoff_navmesh: 104
  standoff_geometry: 8
uses_gt_for_action: false
next_gate: broader standoff frame export and row-level nonblank sanity
```

Mixed standoff frame export result:

```text
frame_output: local_dataset/runs/h001_rival_identity_broader_frames_standoff_v1
rows_requested: 112
rows_exported: 112
rendered_heading_count: 1079
nonblank_output_rows: 107
nonblank_kept_heading_count: 1028
dropped_rows: 5
removed_blank_heading_count: 51
row_level_nonblank_gate_passed: false
failure_rows: all dropped rows use standoff_geometry fallback with standoff_navmesh_navigable false
detector_rerun_allowed: false
```

Navmesh-only standoff repair result:

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
mode: --viewpoint-mode standoff --require-navmesh-standoff
plan_output: local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1
frame_output: local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1
filtered_frame_summary: local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
plan_gate: true
geometry_gate: true
request_rows: 30
planned_request_rows: 28
plan_rows: 104
skipped_rows: 8
skip_reason: standoff_navmesh_required
planned_scene_count: 9
planned_query_count: 6
viewpoint_source_counts:
  standoff_navmesh: 104
rows_exported: 104
rendered_heading_count: 997
nonblank_output_rows: 104
nonblank_kept_heading_count: 997
dropped_rows: 0
removed_blank_heading_count: 0
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: true
uses_gt_for_action: false
next_gate: completed below; detector/SAM2 and post-observation objective validation are recorded in the following sections
```

Navmesh-only detector and post-observation result:

```text
detector_output: local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1
post_observation_output: local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1
detector_rows: 104
frame_rows: 104
detector_box_rate: 0.9808
sam2_mask_rate: 0.9808
candidate_association_rate: 0.7212
rows_with_candidate_association: 75
associated_candidate_heading_count: 277
request/evidence/decision_rows: 28 / 110 / 28
commit/success/wrong/no_label: 7 / 0 / 7 / 0
defer_unresolved_identity: 19
defer_object_existence_validation: 2
failure_taxonomy:
  unsafe_rival_identity_commit: 7
  rival_identity_unresolved_cross_view_aliasing: 8
  post_observation_no_candidate_support: 6
  post_observation_margin_too_small: 5
  object_existence_deferred_no_independent_confirmation: 2
post_observation_gate_passed: false
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Unsafe-commit diagnostic:

```text
script: runtime/h001_runtime/diagnose_rival_identity_unsafe_commits.py
output: local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1
unsafe_commit_rows: 7
unsafe_commit_query_counts:
  bed: 4
  chair: 2
  tv_monitor: 1
mechanism_counts:
  absence_of_cross_support_not_discriminative: 7
  low_detector_score_still_strong_by_count: 5
  wrong_candidate_has_stronger_own_view_support_than_correct: 4
  rival_candidate_false_positive_commit: 4
  candidate_set_no_valid_goal_candidate: 3
  depth_consistent_wrong_candidate: 3
  semantic_prior_favors_wrong_over_correct: 3
  semantic_top_is_wrong: 3
simple_guard_variants_with_wrong_commit:
  existing_unique_strong_own_view_identity
  semantic_rank_1_only
  detector_box_ge_0_25
  depth_error_le_0_33
  own_count_ge_4_only
safe_nontrivial_simple_guard_variants: []
post_observation_threshold_tuning_allowed: false
paper_claim_allowed: false
```

Promotion gate beyond this first fresh source:

```text
request_rows >= 20
request_scenes >= 5
request_queries >= 3
at least one non-furniture or small-object query
same frozen analyzer and thresholds
failure taxonomy reported for all unresolved rows
```

Safer rival-identity arbitration contract before the next rule:

```text
contract: manifests/h001_rival_identity_strict_arbitration_v1.json
contract_name: rival_identity_goal_validity_arbitration_v1
status: design_contract_before_implementation
blocked_changes:
  - increase only own-view count or identity-margin threshold
  - commit from object/category existence evidence alone
  - commit from detector box score, depth error, or semantic rank alone
  - use evaluation-only correctness, GT goal ids, or GT target distance in action rows
required_before_next_rule:
  - separate candidate-set validity failure from rival-identity arbitration
  - report defer-only, semantic-rank, detector-score, depth-consistency, and combined simple guards
  - require an action-time surrogate that a candidate is a valid navigation goal, not merely a visible object
  - route no-valid-candidate or low-validity-surrogate rows to expanded retrieval or object-existence validation
  - keep label joins sidecar-only and evaluate wrong-goal, no-label, and success commits after action selection
next_implementation_target:
  design a stricter rival-identity arbitration objective that tests candidate-set validity and local semantic/geometric consistency before any detector-backed commit
```

Implementation result:

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
objective: goal_validity_arbitration_v1
default_regression_output: local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_default_regression_v1
strict_objective_output: local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1
default_commit/success/wrong/no_label: 7 / 0 / 7 / 0
strict_commit/success/wrong/no_label: 2 / 2 / 0 / 0
strict_request/evidence/decision_rows: 28 / 110 / 28
strict_action_counts:
  commit_candidate: 2
  defer_expanded_retrieval_needed: 23
  defer_object_existence_validation: 2
  defer_unresolved_identity: 1
strict_reason_counts:
  commit_goal_validity_unique_semantic_geometric_consistency: 2
  defer_low_goal_validity_cross_view_aliasing: 12
  post_observation_no_candidate_support: 6
  defer_low_goal_validity_surrogate: 4
  object_existence_requires_independent_confirmation: 2
  defer_comparable_goal_validity_candidates: 1
  defer_visible_object_not_goal_validity: 1
strict_post_observation_gate_passed: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Independent/predeclared source freeze:

```text
contract: rival_identity_goal_validity_independent_v1
design_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_design_v1
source_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_source_v1
manifest: manifests/h001_rival_identity_goal_validity_independent_v1.json
verify: manifests/h001_rival_identity_goal_validity_independent_v1.verify.json
preferred_source: v3_fresh_validation
excluded_scene_policy:
  - exclude prior diagnostic scenes
  - exclude broader unsafe-diagnostic/objective-design scenes
design_parent_rows/scenes/queries: 72 / 11 / 6
design_top_wrong_goal_rows: 51
design_correct_and_wrong_candidate_rows: 59
source_request_rows/scenes/queries: 30 / 10 / 6
source_route_counts:
  rival_identity_arbitration: 26
  object_existence_validation: 4
source_excluded_scene_overlap: 0
source_action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The zero-standoff and detector-substrate blockers are resolved. The stricter objective is a useful diagnostic repair because it turns seven unsafe commits into two successful commits and zero wrong-goal commits without GT action inputs. It is not paper-ready because this same broader split was used to diagnose the unsafe failure and define the objective. The independent/predeclared source, runtime substrate, and objective rerun are now complete; the independent result below rejects the current rule as a utility claim.

Independent runtime and rerun result:

```text
plan_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1
frame_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1
detector_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1
post_observation_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1
plan_request/planned/rows: 30 / 30 / 92
frame_rows/headings: 92 / 810
detector_box/sam2/candidate_association: 1.0 / 1.0 / 0.6196
objective: goal_validity_arbitration_v1
request/evidence/decision_rows: 30 / 101 / 30
action_counts:
  defer_expanded_retrieval_needed: 23
  defer_object_existence_validation: 6
  defer_unresolved_identity: 1
commit/success/wrong/no_label: 0 / 0 / 0 / 0
post_observation_gate_passed: false
wrong_goal_gate_passed: true
no_label_gate_passed: true
new_primary_success_gate_passed: false
resolved_request_gate_passed: false
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: Independent validation rejects the current `goal_validity_arbitration_v1` as a utility rule. The result is a safe negative result, not a success: the objective avoids wrong commits by deferring every request. The failure diagnosis below shows that any next change must revise the evidence acquisition or candidate-validity model, not tune thresholds from joined labels.

Independent failure diagnosis and revision contract:

```text
default_counterfactual_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1
failure_diagnostic_script: runtime/h001_runtime/diagnose_goal_validity_independent_failure.py
failure_diagnostic_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1
revision_contract: manifests/h001_rival_identity_goal_validity_revision_v2.json
revision_router_script: runtime/h001_runtime/route_goal_validity_revision_v2.py
revision_router_output: local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1
discriminative_rival_view_contract: manifests/h001_discriminative_rival_view_planner_v1.json
strict_goal_validity_commit/success/wrong/no_label: 0 / 0 / 0 / 0
default_counterfactual_commit/success/wrong/no_label: 7 / 4 / 3 / 0
default_wrong_goal_queries:
  chair: 1
  sofa: 1
  toilet: 1
diagnostic_tradeoff_check: true
dominant_mechanism_tags:
  cross_view_aliasing_blocks_goal_validity: 14
  planned_candidate_set_has_no_valid_goal: 13
  no_own_candidate_support: 11
  strong_identity_not_goal_validity: 8
  object_existence_branch_blocks_commit: 6
revision_router_actions:
  request_discriminative_rival_view: 14
  request_expanded_retrieval: 8
  request_object_existence_confirmation: 6
  request_goal_validity_confirmation: 2
router_commit_allowed_rows: 0
router_uses_gt_for_action: false
discriminative_rival_view_target_rows: 14
discriminative_rival_view_contract_status: detector_substrate_running
discriminative_rival_view_plan_output: local_dataset/runs/h001_discriminative_rival_view_plan_v1
discriminative_rival_view_plan_rows: 38
discriminative_rival_view_planned_request_rows: 14
discriminative_rival_view_common_pair_rows: 10
discriminative_rival_view_matched_dual_standoff_rows: 28
discriminative_rival_view_zero/near_standoff_rows: 0 / 0
discriminative_rival_view_rotation_fallback_rows: 0
discriminative_rival_view_plan_smoke_passed: true
discriminative_rival_view_v1_frame_rows/headings: 38 / 222
discriminative_rival_view_v1_nonblank_dropped_rows: 1
discriminative_rival_view_v1_nonblank_gate_passed: false
discriminative_rival_view_v2_plan_output: local_dataset/runs/h001_discriminative_rival_view_plan_v2
discriminative_rival_view_v2_frame_output: local_dataset/runs/h001_discriminative_rival_view_frames_v2
discriminative_rival_view_v2_frame_rows/headings: 38 / 222
discriminative_rival_view_v2_nonblank_dropped_rows: 0
discriminative_rival_view_v2_removed_blank_headings: 0
discriminative_rival_view_v2_row_level_nonblank_gate_passed: true
discriminative_rival_view_v2_strict_no_blank_heading_gate_passed: true
discriminative_rival_view_v2_metadata_repair: viewpoint_pair_role/rival_*/revision_*/standoff_* passthrough preserved for pair-level evidence analysis
discriminative_rival_view_v2_role_counts: common 10 / focus 14 / rival 14
discriminative_rival_view_detector_v1_output: local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1
discriminative_rival_view_detector_v1_status: completed, substrate gate pass, superseded for pair analysis
discriminative_rival_view_detector_v1_box/sam2/association: 1.0 / 1.0 / 0.8158
discriminative_rival_view_detector_v1_superseded_reason: detector output did not preserve viewpoint_pair_role
discriminative_rival_view_detector_v2_job: h001-discriminative-rival-view-detector-v2-20260527-033307
discriminative_rival_view_detector_v2_job_status: completed, substrate gate pass
discriminative_rival_view_detector_v2_output: local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2
discriminative_rival_view_detector_v2_box/sam2/association: 1.0 / 1.0 / 0.8158
discriminative_rival_view_evidence_script: runtime/h001_runtime/analyze_discriminative_rival_view_evidence.py
discriminative_rival_view_evidence_output: local_dataset/runs/h001_discriminative_rival_view_evidence_v1
discriminative_rival_view_evidence_availability/disambiguation: 1.0 / 0.6429
discriminative_rival_view_evidence_actions: support_focus 8 / support_rival 1 / ambiguous_defer 5
discriminative_rival_view_evidence_single_correct_preferred/wrong: 0.0 / 0.3333
discriminative_rival_view_evidence_gate_passed: false
discriminative_rival_view_failure_diagnostic: local_dataset/runs/h001_discriminative_rival_view_failure_diagnostic_v1
discriminative_rival_view_failure_tags:
  symmetric_cross_view_leak: 7
  rival_visible_from_focus_view: 6
  identity_score_near_tie: 5
  common_view_supports_both_candidates: 5
  no_valid_goal_pair_but_disambiguated: 4
  both_correct_goal_region_or_duplicate_preferred: 4
  rival_correct_own_view_evidence_weak: 3
failure_diagnostic_decision: threshold_tuning false, objective_revision false, fresh_validation false, planner_or_branch_revision required
branch_priority_decision: request_expanded_retrieval before discriminative view revision
expanded_retrieval_contract: manifests/h001_expanded_retrieval_branch_v1.json
expanded_retrieval_expected_request_rows: 8
expanded_retrieval_candidate_budget: 6-10
expanded_retrieval_terminal_commit_allowed: false
expanded_retrieval_jq_validation: passed
expanded_retrieval_planner_output: local_dataset/runs/h001_expanded_retrieval_plan_v1
expanded_retrieval_request_rows: 8
expanded_retrieval_candidate_set_rows: 8
expanded_retrieval_plan_rows: 80
expanded_retrieval_candidates_per_request: 10
expanded_retrieval_duplicate_candidate_id_rate: 0.0
expanded_retrieval_nonfinite_position_rate: 0.0
expanded_retrieval_forbidden_action_keys: 0
expanded_retrieval_planner_gate_passed: true
expanded_retrieval_candidate_set_validity: local_dataset/runs/h001_expanded_retrieval_candidate_set_validity_v1
expanded_retrieval_label_join_gate_passed: true
expanded_retrieval_contains_correct_rows: 6/8
expanded_retrieval_no_valid_candidate_rows: 2/8
expanded_retrieval_source_top_correct_rows: 1/8
expanded_retrieval_source_top_wrong_goal_rows: 7/8
expanded_retrieval_wrong_top_replacement_rows: 5/7
expanded_retrieval_rows_with_wrong_goal_candidate: 7/8
expanded_retrieval_full_pool_contains_correct_rows: 6/8
expanded_retrieval_selected_missed_full_pool_correct_rows: 0
expanded_retrieval_taxonomy:
  source_pool_no_valid_candidate: 2
  valid_set_with_wrong_goal_distractor: 5
  valid_set_without_wrong_goal_distractor: 1
expanded_retrieval_candidate_set_guard: local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1
expanded_retrieval_guard_routes:
  request_backend_retrieval_revision: 2
  request_detector_guarded_observation: 5
  request_lightweight_confirmation: 1
expanded_retrieval_guard_detector_evidence_allowed_rows: 6/8
expanded_retrieval_guard_terminal_commit_rows: 0
expanded_retrieval_guard_design_gate_passed: true
expanded_retrieval_guard_is_action_time_rule: false
expanded_retrieval_guard_requires_action_time_proxy: true
expanded_retrieval_guard_proxy_features: local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1
expanded_retrieval_proxy_route_counts:
  request_detector_guarded_observation_proxy: 8
expanded_retrieval_proxy_source_pool_validity_recall: 0.0
expanded_retrieval_proxy_evidence_allowed_target_recall: 1.0
expanded_retrieval_proxy_ready_for_detector_gate: false
expanded_retrieval_source_pool_validity_proxy: local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1
expanded_retrieval_source_pool_proxy_route_counts:
  request_backend_retrieval_revision_proxy: 2
  request_detector_guarded_observation_proxy: 6
expanded_retrieval_source_pool_proxy_validity_recall: 1.0
expanded_retrieval_source_pool_proxy_evidence_allowed_recall: 1.0
expanded_retrieval_source_pool_proxy_backend_escalated_to_evidence: 0
expanded_retrieval_source_pool_proxy_evidence_blocked_as_backend: 0
expanded_retrieval_source_pool_proxy_consumed_forbidden_rows: 0
expanded_retrieval_source_pool_proxy_ready_for_detector_gate: true
expanded_retrieval_detector_contract: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_detector_evidence_v1.json
expanded_retrieval_detector_plan: local_dataset/runs/h001_expanded_retrieval_detector_plan_v1
expanded_retrieval_detector_plan_rows: 42
expanded_retrieval_detector_planned_request_rows: 6
expanded_retrieval_detector_plan_rows_per_request_min_max: 5 / 8
expanded_retrieval_detector_zero_near_standoff_rows: 0 / 0
expanded_retrieval_detector_fallback_rows: 0
expanded_retrieval_detector_consumed_forbidden_action_fields: 0
expanded_retrieval_detector_frame_output: local_dataset/runs/h001_expanded_retrieval_detector_frames_v1
expanded_retrieval_detector_frame_rows_headings: 42 / 168
expanded_retrieval_detector_nonblank_dropped_removed: 0 / 0
expanded_retrieval_detector_substrate: local_dataset/runs/h001_expanded_retrieval_detector_substrate_v1
expanded_retrieval_detector_job_status: completed
expanded_retrieval_detector_box_sam2_rates: 1.0 / 1.0
expanded_retrieval_detector_candidate_association_rate: 0.0714
expanded_retrieval_detector_rows_with_candidate_association: 3 / 42
expanded_retrieval_detector_substrate_gate: false
expanded_retrieval_detector_projection_status_counts:
  out_of_fov: 134
  visible: 34
expanded_retrieval_detector_depth_check_counts:
  consistent: 6
  depth_mismatch: 28
  out_of_fov: 134
paper_claim_allowed: false
```

에이전트 추론: The independent evidence shows a strict-safe/inert versus loose-nontrivial/unsafe tradeoff. Therefore, `goal_validity_arbitration_v1` is rejected as a paper-facing utility rule, and the next implementation should be branch-specific active evidence acquisition rather than threshold tuning. `goal_validity_revision_v2` is a routing contract only: it does not claim terminal ObjectNav utility. The first branch-specific planner is `discriminative_rival_view_planner_v1`, because cross-view aliasing is the largest route. v2 passes the frame/nonblank and detector substrate gates after rejecting geometry-only common pair views, but the first pair-role evidence analyzer fails. Failure taxonomy suggests candidate-set expansion before another discriminative-view revision. The `request_expanded_retrieval` planner gate, label-join diagnostic, candidate-set guard design, proxy feature extraction, source-pool validity proxy, and standoff frame gate pass on current diagnostic evidence. The detector/SAM2 run shows category detections and masks are available, but candidate projection/association fails. The next gate is association failure taxonomy, not threshold or terminal objective tuning.
Expanded-retrieval detector association diagnostic:

```text
output: local_dataset/runs/h001_expanded_retrieval_detector_failure_diagnostic_v1
candidate_observation_rows: 42
association_heading_rows: 168
candidate_association_rate: 0.0714
failure_mechanism_counts:
  projection_never_visible: 33
  mask_overlap_depth_mismatch_only: 4
  associated_success: 3
  visible_projection_no_detector_overlap: 1
  box_overlap_mask_reject: 1
detector_available_rows: 42
threshold_tuning_allowed: false
viewpoint_revision_required: true
association_depth_revision_required: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The independent evidence shows a strict-safe/inert versus loose-nontrivial/unsafe tradeoff. Therefore, `goal_validity_arbitration_v1` is rejected as a paper-facing utility rule, and the next implementation should be branch-specific active evidence acquisition rather than threshold tuning. `goal_validity_revision_v2` is a routing contract only: it does not claim terminal ObjectNav utility. The first branch-specific planner is `discriminative_rival_view_planner_v1`, because cross-view aliasing is the largest route. v2 passes the frame/nonblank and detector substrate gates after rejecting geometry-only common pair views, but the first pair-role evidence analyzer fails. Failure taxonomy suggests candidate-set expansion before another discriminative-view revision. The `request_expanded_retrieval` planner gate, label-join diagnostic, candidate-set guard design, proxy feature extraction, source-pool validity proxy, and standoff frame gate pass on current diagnostic evidence. The detector/SAM2 run shows category detections and masks are available, but candidate projection/association fails primarily through out-of-FOV candidate projections. Viewpoint/projection revision is now implemented and smoked, so the next gate is detector/SAM2 association rerun with fixed anchors, not threshold or terminal objective tuning.

Expanded-retrieval viewpoint/projection revision design:

```text
contract: manifests/h001_expanded_retrieval_detector_viewpoint_revision_v1.json
design_output: local_dataset/runs/h001_expanded_retrieval_detector_viewpoint_revision_design_v1
selected_revision: projection_anchor_height_sweep_v1
projection_anchor_height_offsets_m: [0.0, 0.4, 0.8, 1.2, 1.6]
out_of_fov_axis_counts:
  x_in_y_above: 134
projection_never_visible_recovery:
  offsets_0_0_to_0_8: 29 / 33
  offsets_0_0_to_1_6: 33 / 33
rejected_next_step:
  detector_threshold_tuning
  yaw_widen_only
  terminal_objective_tuning
deferred:
  depth_tolerance_relaxation
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The selected revision treats the semantic-map object anchor as uncertain in vertical image projection while keeping the mobility/viewpoint substrate fixed. This is closer to the research thesis than threshold tuning because it converts a semantic-map uncertainty failure into an active evidence/acquisition contract. The projection-anchor revised plan/evidence path has now passed smoke, so detector/SAM2 can be rerun under the fixed-anchor rule.

Expanded-retrieval revised projection-anchor implementation smoke:

```text
plan_output: local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1
plan_schema: h001.expanded_retrieval_detector_observation_plan.v2
planner: expanded_retrieval_detector_standoff_projection_anchor_v1
plan_rows: 42
planned_request_rows: 6
projection_anchor_height_offsets_m: [0.0, 0.4, 0.8, 1.2, 1.6]
plan_gate: true
full_projection_smoke: local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_smoke_v1
projection_anchor_visible_rows: 42 / 42
projection_anchor_visible_rate: 1.0
frame_passthrough_smoke: local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_frame_passthrough_smoke_v1
frame_revision_metadata_rows: 2 / 2
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This smoke proves the fixed projection anchors are available to the observation/evidence path and recover frame-level visibility before detector/SAM2 scoring. By itself, it does not prove detector association or ObjectNav utility.

Expanded-retrieval fixed-anchor detector/SAM2 substrate rerun:

```text
job: h001-expanded-retrieval-detector-anchor-20260527-163608
output: local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1
status: completed
detector_rows: 42
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.7381
rows_with_candidate_association: 31 / 42
associated_candidate_heading_count: 96
projection_anchor_selected_offset_counts:
  0.0: 21
  0.4: 3
  0.8: 13
  1.2: 9
  1.6: 122
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: Fixed projection anchors repair the detector substrate association gate on diagnostic evidence without detector threshold, depth-tolerance, or terminal-objective tuning. This is still not a paper-facing utility claim; the next required gate is a fresh/predeclared validation source.

Expanded-retrieval fresh/predeclared source freeze:

```text
router_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_router_v1
source_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_v1
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_fresh_validation_v1.json
verify_ok: true
request_expanded_retrieval_rows: 6
request_scenes: 2
request_queries: 4
excluded_scene_overlap: 0
action_evidence_forbidden_key_count: 0
missing_action_evidence_rows: 0
uses_gt_for_action: false
paper_scale_gate: false
planner_compatibility_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_plan_v1
planner_candidate_set_rows: 6
planner_plan_rows: 60
planner_skipped_rows: 0
paper_claim_allowed: false
```

사실: The frozen fresh source is scene-disjoint from the projection-anchor diagnostic detector plan and passes branch-source gates, but it is below the paper-scale gate of `20` rows and `5` scenes.

에이전트 추론: This source is useful for falsifying whether the fixed-anchor branch generalizes beyond the repair diagnostic. It is not large enough to support a paper-facing utility claim by itself; a positive result should trigger a larger source freeze.

Expanded-retrieval fresh-source proxy, plan, and frame gates:

```text
source_pool_proxy_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_pool_validity_proxy_v1
proxy_route_counts:
  request_detector_guarded_observation_proxy: 6
detector_proxy_request_rows: 6
proxy_ready_for_detector_gate: true
detector_plan_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_plan_projection_anchor_v1
planned_request_rows: 6
plan_rows: 51
plan_rows_per_request: 7-10
skipped_rows: 9
skipped_reason: standoff_navmesh_required
zero_standoff_rows: 0
near_standoff_rows: 0
fallback_rows: 0
target_distance_from_viewpoint_m: 1.7417 / 1.7506 / 1.7975
frame_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_frames_projection_anchor_v1
frame_rows: 51
rendered_heading_count: 204
nonblank_rows: 51 / 51
removed_blank_heading_count: 0
projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_projection_anchor_smoke_v1
projection_anchor_visible_rows: 51 / 51
frame_revision_metadata_rows: 51 / 51
uses_gt_for_action: false
paper_claim_allowed: false
```

사실: The frozen fresh source now has detector-eligible proxy rows, navmesh standoff plan rows, rendered nonblank frames, visible projection anchors, a completed detector/SAM2 substrate pass, a completed detector evidence diagnostic, and a completed ambiguity-aware objective contract. Detector rows are `51`; detector box/SAM2 rates are `1.0/1.0`; candidate association rate is `0.6078`; evidence diagnostic topology is `multi_strong_saturated_ambiguity 5` and `single_strong_lower_rank 1`; objective contract route coverage is `1.0`; terminal commit rows are `0`; action counts are `request_local_context_disambiguation 5` and `request_rank_challenge_confirmation 1`; `uses_gt_for_action false`; `paper_claim_allowed false`. The paper-scale source has request rows `23`, scenes `10`, queries `6`, planner rows `230`, `21` detector-eligible proxy rows, and detector observation plan rows `162`.

에이전트 추론: The paper-scale substrate and evidence gates now pass, but the result is not a terminal utility proof because every detector-supported request is still multi-strong saturated. Local-context planner, frame/projection smoke, and detector/SAM2 substrate now pass under the frozen no-GT-action contract. The post-observation evaluation failed safety, so the next falsification step is failure diagnosis before any threshold or objective revision.

Paper-scale detector/evidence and local-context disambiguation contract:

```text
detector_substrate_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1
detector_rows: 162
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.8272
rows_with_candidate_association: 134 / 162
associated_candidate_heading_count: 378
detector_substrate_gate_passed: true

detector_evidence_diagnostic_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_evidence_diagnostic_upper_v1
request_rows: 21
candidate_rows: 162
association_heading_rows: 648
associated_request_rate: 1.0
strong_request_rate: 1.0
multi_strong_request_rate: 1.0
evidence_topology:
  multi_strong_saturated_ambiguity: 21
terminal_objective_risk:
  multi_candidate_detector_ambiguity: 21
diagnostic_gate_passed: true
paper_scale_gate_passed: true

ambiguity_objective_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_ambiguity_objective_upper_v1
objective_action:
  request_local_context_disambiguation: 21
terminal_commit_rows: 0
contract_gate_passed: true

local_context_contract: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_disambiguation_v1.json
planner_name: expanded_retrieval_local_context_disambiguation_v1
planned_request_rows_minimum: 18 / 21
terminal_objective: local_context_unique_own_view_advantage only
direct_detector_score_commit_allowed: false
source_top_if_associated_commit_allowed: false
wrong_goal_commit_rate_maximum: 0.0
success_commit_rows_minimum: 2
uses_gt_for_action: false
paper_claim_allowed: false
```

사실: The local-context contract freezes candidate selection, forbidden action inputs, nonzero utility gates, and simpler alternatives before implementation.

에이전트 추론: The contract keeps the novelty centered on semantic uncertainty as active evidence routing. A positive result must show that local context resolves repeated-object ambiguity better than score-only or source-top shortcuts, not merely that detector evidence exists.

Local-context planner smoke:

```text
planner: runtime/h001_runtime/plan_expanded_retrieval_local_context_disambiguation.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1
request/planned_request_rows: 21 / 21
planned_request_coverage: 1.0
plan_rows: 113
skipped_rows: 3
plan_rows_per_request_min/max: 2 / 6
viewpoint_source:
  standoff_navmesh: 113
zero/near/fallback/rotation_fallback_rows: 0 / 0 / 0 / 0
consumed/output_forbidden_action_fields: 0 / 0
uses_gt_for_action: false
planner_gate_passed: true
paper_claim_allowed: false
```

사실: Planner smoke is a substrate gate only. It allows the next frame/projection smoke but does not allow terminal utility or paper claims.

Local-context frame/projection smoke:

```text
frame_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1
projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_projection_smoke_v1
frame_rows: 113 / 113
rendered_heading_count: 1285
nonblank_rows: 113 / 113
removed_blank_heading_count: 0
projection_visible_rows: 113 / 113
projection_visible_rate: 1.0
missing_candidate_rows: 0
frame_revision_metadata_rows: 113
uses_gt_for_action: false
projection_smoke_gate_passed: true
paper_claim_allowed: false
```

사실: Frame/projection smoke is a detector-substrate prerequisite only. It allows the next detector/SAM2 substrate job but does not allow terminal utility or paper claims.

Local-context detector/SAM2 and post-observation evaluation:

```text
detector_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1
detector_rows: 113
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.9204
rows_with_candidate_association: 104 / 113
detector_substrate_gate_passed: true

post_observation_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1
request/evidence_rows: 21 / 113
strong_own_view_request_rows: 19 / 21
proposed_variant: proposed_local_context_unique_own_view_advantage
proposed_commit/success/wrong/no_valid: 10 / 3 / 7 / 3
post_observation_gate_passed: false
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Simpler alternatives on the same frozen rows:

```text
defer_all: commit/success/wrong/no_valid = 0 / 0 / 0 / 0
semantic_top: commit/success/wrong/no_valid = 21 / 11 / 10 / 4
source_top_if_associated: commit/success/wrong/no_valid = 18 / 9 / 9 / 3
detector_score_best: commit/success/wrong/no_valid = 21 / 6 / 15 / 4
own_support_best: commit/success/wrong/no_valid = 21 / 9 / 12 / 4
local_context_only_best: commit/success/wrong/no_valid = 15 / 5 / 10 / 4
```

사실: The detector substrate gate passes, but the terminal post-observation gate fails because wrong-goal and no-valid commit rows exceed the frozen maximum of `0`.

에이전트 추론: Local own-view detector/SAM2 evidence is not sufficient as ObjectNav goal validity evidence in this split. The result strengthens the novelty argument only if the next revision can explain why own-view evidence fails and derive a safer mechanism from that failure taxonomy. Threshold tuning from joined labels remains blocked.

Local-context failure diagnosis:

```text
diagnostic_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_failure_diagnostic_v1
proposed_request_rows: 21
proposed_commit_rows: 10
proposed_success_commit_rows: 3
proposed_wrong_goal_commit_rows: 7
selected_role_counts:
  detector_strong_candidate: 2
  detector_strong_rival: 7
  source_top: 1
diagnostic_tag_counts:
  selected_detector_strong_role: 9
  wrong_commit: 7
  wrong_candidate_stronger_own_view_than_best_correct: 4
  best_correct_not_strong_own_view: 4
  own_view_support_prefers_wrong_over_weak_correct: 4
  source_pool_no_valid_candidate: 3
  wrong_commit_without_correct_planned_candidate: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

사실: The failure diagnosis separates no-valid source-pool rows from wrong-instance arbitration rows. Most committed candidates selected by the proposed rule are detector-strong roles, not local-context-added candidates.

에이전트 추론: A revised contract must not be "raise the own-view threshold." It must first route no-valid pool failures away from terminal commitment and then require evidence that distinguishes goal validity from category/object visibility when detector-strong wrong instances outscore weak correct candidates.

Revised local-context objective contract:

```text
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_revision_v1.json
verify: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_revision_v1.verify.json
status: frozen_design_contract_before_implementation
objective_name: goal_validity_guarded_local_context_v1
guard_order:
  1. pool_validity_guard_v2
  2. wrong_instance_arbitration_guard_v1
blocked_shortcuts: semantic_top, source_top_if_associated, detector_score_best, own_support_best, local_context_only_best
wrong_goal_commit_rows_maximum_after_label_join: 0
no_valid_commit_rows_maximum_after_label_join: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

사실: The revised contract is a design contract, not a positive utility result. It freezes the next analyzer target and label-separation gates before implementation.

에이전트 추론: The next analyzer should first prove that the candidate pool is action-time valid enough to arbitrate. If that is unresolved, the method should request backend retrieval repair or defer instead of committing a detector-strong repeated object.

Revised local-context analyzer result:

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_local_context_revision.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1
request/evidence/decision/evaluated_rows: 21 / 113 / 168 / 168
action_evidence_forbidden_key_count: 0
goal_validity_guarded_local_context_v1 commit/success/wrong/no_valid: 0 / 0 / 0 / 0
revision action counts:
  request_goal_validity_confirmation: 12
  defer_instance_arbitration_unresolved: 9
pool_validity_status:
  passed: 21
instance_arbitration_status:
  unresolved: 21
revision_substrate_gate_passed: true
revision_utility_gate_passed: false
paper_claim_allowed: false
```

사실: The revised analyzer is Docker-run and safe against wrong/no-valid commits on the frozen paper-scale local-context rows.

에이전트 추론: The result is safe but inert. It supports the failure mechanism that own-view category evidence is not enough for ObjectNav goal validity, but it does not yet support a utility claim over `defer_all`.

Revised local-context route diagnosis:

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_local_context_revision_routes.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1
request_rows: 21
route_counts:
  request_goal_validity_confirmation: 12
  defer_instance_arbitration_unresolved: 9
route_counts_for_no_valid_rows:
  request_goal_validity_confirmation: 4
route_counts_for_valid_rows:
  request_goal_validity_confirmation: 8
  defer_instance_arbitration_unresolved: 9
diagnostic_tag_counts:
  pool_guard_false_positive_no_valid_pool: 4
  unsafe_previous_commit_prevented: 7
  previous_rule_success_lost_by_guard: 3
  correct_and_wrong_both_strong_own_view: 7
  wrong_only_strong_own_view: 7
  correct_candidate_not_strong_own_view: 5
  simpler_alternatives_unsafe_analysis_only: 20
paper_claim_allowed: false
```

사실: The route diagnostic is post-action analysis only. It shows the current source-pool proxy passes all 21 rows, including four no-valid rows after label join.

에이전트 추론: The next evaluation contract should not just add a looser commit rule. It should define a source-pool repair branch for no-valid risk and a separate goal-validity confirmation branch for valid but unresolved repeated-instance rows.

#### Route-Specific Contract

```text
contract: manifests/h001_expanded_retrieval_local_context_route_contract_v1.json
verify: manifests/h001_expanded_retrieval_local_context_route_contract_v1.verify.json
status: frozen_design_contract_before_implementation
branches:
  source_pool_repair_v1
  goal_validity_confirmation_v1
  instance_arbitration_defer_v1
terminal_commit_rows_maximum: 0
routes_all_request_rows: 21
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_action_rows: true
paper_claim_allowed: false
```

사실: The contract is a branch-routing contract. It does not promote a terminal local-context commit rule.

에이전트 추론: The next analyzer should report how many rows require source-pool repair versus goal-validity confirmation before any fresh validation. A paper claim remains blocked until branch-specific evidence is fixed and validated on a predeclared source.

#### Route-Specific Analyzer Result

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_local_context_route_specific.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1
request_rows: 21
route_action_counts:
  request_source_pool_repair: 5
  request_goal_validity_confirmation_evidence: 7
  defer_instance_arbitration_unresolved: 9
route_counts_for_no_valid_rows:
  request_source_pool_repair: 4
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
route_contract_gate_passed: true
paper_claim_allowed: false
```

사실: All no-valid rows are routed to source-pool repair after label join, but the route actions themselves are written before label join.

에이전트 추론: The next evaluation contract should start with source-pool repair evidence because no-valid rows must be resolved before goal-validity confirmation can be interpreted as an ObjectNav utility signal.

#### Source-Pool Repair Evidence Contract

```text
contract: manifests/h001_expanded_retrieval_source_pool_repair_v1.json
verify: manifests/h001_expanded_retrieval_source_pool_repair_v1.verify.json
source_filter:
  route_action: request_source_pool_repair
input_request_rows: 5
required_route_actions:
  request_backend_pool_expansion
  route_to_goal_validity_confirmation_after_pool_repair
  defer_source_pool_unresolved
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_action_rows: true
paper_claim_allowed: false
```

사실: The contract freezes the source-pool repair branch before implementation.

에이전트 추론: A row can move from source-pool repair to goal-validity confirmation only after action-time repair evidence says the candidate pool is repaired or sufficiently valid. The contract keeps `ObjectNav` terminal utility blocked.

#### Source-Pool Repair Analyzer Result

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_source_pool_repair.py
output: local_dataset/runs/h001_expanded_retrieval_source_pool_repair_v1
request_rows: 5
evaluated_rows: 5
repair_action_counts:
  request_backend_pool_expansion: 5
  route_to_goal_validity_confirmation_after_pool_repair: 0
  defer_source_pool_unresolved: 0
no_valid_rows_by_repair_action:
  request_backend_pool_expansion: 4
valid_rows_by_repair_action:
  request_backend_pool_expansion: 1
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
source_pool_repair_gate_passed: true
paper_claim_allowed: false
```

사실: The analyzer writes action rows before label join and keeps all five repair rows out of terminal reasoning.

에이전트 추론: Goal-validity confirmation is still blocked for this branch because no row is routed to `route_to_goal_validity_confirmation_after_pool_repair`. The next evaluation contract should define backend pool expansion evidence and a fixed criterion for when an expanded pool can be handed to goal-validity confirmation.

#### Backend Pool Expansion Evidence Contract

```text
contract: manifests/h001_expanded_retrieval_backend_pool_expansion_v1.json
verify: manifests/h001_expanded_retrieval_backend_pool_expansion_v1.verify.json
source_filter:
  repair_action: request_backend_pool_expansion
input_request_rows: 5
required_route_actions:
  request_backend_candidate_generation
  route_to_goal_validity_confirmation_after_expansion
  defer_backend_pool_unresolved
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
expanded_candidate_accounting_required: true
duplicate_and_reachability_accounting_required: true
backend_config_reporting_required: true
label_join_only_after_expansion_rows: true
paper_claim_allowed: false
```

사실: The contract freezes the backend expansion branch before implementation.

에이전트 추론: This branch should answer whether a fixed non-GT backend expansion can repair candidate-pool validity before any goal-validity confirmation. If the expanded pool still lacks reachable, non-duplicate, independently supported candidates, the correct action is unresolved defer or backend candidate generation, not terminal commitment.

### Generalization Decision

#### 사실

The two-row dense chair diagnostic supports `association_depth_tolerance_m=2.0` locally:

```text
variant: mask_depth_2_0
local_rows: 36 detector/candidate association rows
local_episodes: 2 held-out y9hTuugGdiq chair episodes
local_episode_correct_association_rate: 1.0
local_episode_wrong_association_rate: 0.0
local_association_rate: 0.2222
posthoc_success_commits: 2 / 2
posthoc_wrong_goal_commits: 0 / 2
```

A broader existing 100-row `first_eval` replacement association-variant diagnostic does not support threshold-only generalization:

```text
diagnostic: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_association_variants_v1/summary.json
mask_depth_2p0:
  rows_with_any_association_rate: 0.49
  associated_count_auc: 0.520
  selected_correct_delta_on_all_rows: -0.21
  wrong_goal_fixes: 2
  new_wrong_goals: 6
  detector_calibration_gate: false
box_or_mask_depth_2p0:
  rows_with_any_association_rate: 0.56
  associated_count_auc: 0.549
  selected_correct_delta_on_all_rows: -0.14
  wrong_goal_fixes: 5
  new_wrong_goals: 4
  detector_calibration_gate: false
```

#### 에이전트 추론

Do not generalize `association_depth_tolerance_m=2.0` as a global detector association default. It is allowed only as a local diagnostic treatment for the fixed dense backend chair path.

The reason is that the local chair rows diagnose a specific point-height/depth mismatch, while the broader association-variant diagnostic shows that relaxed depth matching increases association coverage without making association count a reliable correctness signal. A global depth relaxation risks adding supported wrong candidates, especially in repeated or cluttered object cases.

Broader use requires a new validation contract where depth tolerance is an ablation or property-conditioned association term, not a fixed default.

Required evidence before promotion:

- independent scene/category validation;
- action/evaluation label separation;
- strict `1.0m` vs `2.0m` vs no-depth mask vs grounded-position comparison;
- wrong-goal commit non-increase;
- utility improvement over defer-only handling;
- per-category failure accounting.

### Terminal Arbitration Decision

#### 사실

Dense terminal arbitration diagnostic:

```text
script: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_dense_terminal_arbitration.py
output: /tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_terminal_arbitration_diagnostic_v1
rows: 2
commit_rows: 2
action_recompute_match_rate: 1.0
selected_posthoc_correct_rate: 1.0
first_external_posthoc_correct_rate: 1.0
selected_correct_improvement_over_first: 0.0
wrong_positive_support_row_rate: 0.0
same_goal_evidence_selection_rate: 1.0
terminal_arbitration_class: same_goal_evidence_selection_not_wrong_repair 2
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Both rows commit `vlmaps:export:chair:spatial_nms:7`, while the first external candidate `vlmaps:export:chair:spatial_nms:2` is also post-hoc correct. Positive-support candidates are `spatial_nms:2`, `spatial_nms:5`, and `spatial_nms:7`; all are post-hoc correct.

#### 에이전트 추론

Terminal arbitration is locally safe under post-hoc labels, but it does not prove wrong-goal repair utility. The result shows detector evidence can rank a correct dense candidate inside a same-goal correct cluster. It does not show that the terminal objective can choose a correct candidate when wrong candidates also receive positive detector support.

Therefore, the next validation should target independent rows with one of these conditions:

- first external candidate is post-hoc wrong but a correct candidate is present;
- both correct and wrong candidates receive positive support;
- multiple repeated-object candidates receive strong detector/depth support;
- current strict association fails but `2.0m` depth association creates a candidate conflict.

## Independent Dense Conflict Validation Contract

### 사실

Design workflow:

```text
workflow: runtime/workflow-20260521-dense-conflict.md
planned_output: /tmp/research3-runs/h001_dense_conflict_validation_v1
manifest: manifests/h001_dense_conflict_v1.json
manifest_verify: manifests/h001_dense_conflict_v1.verify.json
manifest_status: implemented and Docker-verified
recall_gate_script: runtime/h001_runtime/probe_dense_conflict_recall.py
existing_artifact_recall_smoke: /tmp/research3-runs/h001_dense_conflict_recall_gate_existing_artifact_smoke_v1
primary_source_rows: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_evidence/external_candidate_second_stage_identity_evidence_rows.jsonl
secondary_stress_rows: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_evidence_v4/external_candidate_second_stage_identity_evidence_rows.jsonl
excluded_from_promotion: the previous two y9hTuugGdiq/chair dense diagnostic rows
```

Manifest / gate implementation status:

```text
date_checked: 2026-05-22
manifest_rows: 8
verify_ok: true
duplicate_episode_keys: 0
primary_recall_smoke_artifact: v3_fresh_spatial_p97_k20
primary_recall_smoke_rows_with_correct: 6 / 6
primary_recall_smoke_recall_at_20: 1.0
primary_recall_smoke_passes_gate: true
paper_claim_status: gate_only_not_policy_claim
dense_artifact_job: runtime/jobs/dense_conflict_candidate_artifact.sh
dense_artifact_status: p95_k100_d10_failed_recall_gate
dense_artifact_failed_launch: h001-dense-conflict-artifact-20260521-175656
dense_artifact_completed_launch: h001-dense-conflict-artifact-canonical-20260523-140845
p95_primary_rows_with_correct: 3 / 6
p95_primary_recall_at_20: 0.5
p95_detector_job_allowed: false
revision_running_launch: h001-dense-conflict-artifact-p90-k200-d5-20260523-150036
```

Primary independent set:

```text
rows: 6
scenes: DYehNKdT76V, HY1NcmCgn3n, 7MXmsvcQjpJ
queries: chair, plant
rows_with_correct_and_wrong_positive_support: 6 / 6
rows_with_wrong_positive_support: 6 / 6
rows_with_selected_wrong_positive_support: 3 / 6
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Secondary repeated-object stress set:

```text
rows: 2
scene: y9hTuugGdiq
query: sofa
rows_with_correct_and_wrong_positive_support: 2 / 2
role: stress/control only, not promotion by itself
```

### Evaluation Boundary

The validation may use existing GT-labeled evidence only to select conflict cases and to compute post-hoc evaluation labels. The implementation must still generate dense candidates, detector evidence, association variants, and terminal actions without action-time GT labels.

Evaluation-only labels must be stored separately from action rows, preferably as:

```text
evaluation_labels.jsonl
```

### Required Comparisons

| Comparison | Purpose |
| --- | --- |
| `defer_only` | confirms utility over safe non-commit |
| `first_external` | tests dense retrieval order |
| `score_only_best` | rejects detector-score-only novelty |
| `strict_mask_depth_1_0` | current association baseline |
| `mask_depth_2_0` | local chair repair ablation, not default |
| `mask_no_depth` | tests whether depth is necessary |
| `grounded_position_*` | tests point-height / geometry repair alternative |
| `proposed_conflict_arbitration` | final conflict-aware terminal policy |

### Promotion Gate

| Gate | Required threshold |
| --- | --- |
| primary rows | at least `6` |
| dense recall | correct candidate recovered on at least `4 / 6` primary rows and recall@20 at least `0.50` |
| detector substrate | detector box rate at least `0.80`, SAM2 mask rate at least `0.80` |
| association substrate | candidate association rate at least `0.30` |
| conflict substrate | at least `3` primary rows have both correct and wrong positive-support candidates after dense observation |
| safety | wrong-goal commit, no-valid commit, and visit-position-only commit rates all `0.0` |
| utility | at least `2 / 6` successful primary commits and at least `2` row selected-correct improvement over `first_external` |
| simpler alternatives | wrong-goal rate is no worse than all simpler alternatives |
| generality | at least `3` primary scenes and `2` primary query categories are reported |

### Stop Conditions

Stop before detector scoring if dense candidate generation does not pass the recall gate. Stop before policy-scale integration if wrong-positive support exists but terminal arbitration cannot commit safely. Stop before any `first_eval` claim if only the secondary `sofa` stress rows pass.

Current execution blocker:

```text
host_nvidia_runtime: recovered_on_2026-05-23
reason: host nvidia-smi and Docker --gpus all passed
failed_artifact: spatial_nms_p95_k100_d10
current_job: h001-dense-conflict-artifact-p90-k200-d5-20260523-150036
next_action: verify revised dense artifact job completion and final recall gate
detector_launch: blocked until dense recall gate passes
```

### 에이전트 추론

This validation is the correct next top-tier gate because it tests the actual novelty risk: detector/segmenter support is not enough when wrong objects are also supported. A positive result would support conflict-aware active-observation utility, not merely denser candidate generation or relaxed depth association.

## Random Baseline Gate

`SemanticOnly` must pass at least two of:

- lower `wrong_goal_visit_rate` than `RandomReobserve`;
- lower `mean_wasted_path_wrong_goal` than `RandomReobserve`;
- `SPL` no worse than `RandomReobserve` by more than 0.02 absolute.

If `RandomReobserve` matches `SemanticOnly`, viewpoint selection is not yet the contribution.

## Uncertainty Validity Gate

| Metric | Required threshold |
| --- | --- |
| wrong-goal `AUROC` | at least 0.60 |
| wrong-goal `AUPRC` | above positive-rate baseline by at least 0.05 |
| Spearman `U_sem` vs candidate failure | at least 0.15 |
| high-vs-low `U_sem` bucket gap | high bucket wrong-goal rate exceeds low bucket by at least 10 percentage points |

If `U_sem` fails this gate, revise uncertainty features or candidate backend before Step 4-5.

## What Does Not Count As Strong Evidence

- improvement only over `RandomReobserve`
- improvement only on `Success Rate` without wrong-goal or wasted-path improvement
- tuning thresholds on final evaluation splits
- using GT oracle as the main comparison
- reporting only successful episodes
- excluding episodes without a predeclared filtering rule
- showing HM3D only without any open-vocabulary or ambiguity stress test

## Implementation Order

1. Build log-only candidate evaluator for HM3D ObjectNav v2.
2. Verify GT target labels, candidate correctness, and shortest-path references.
3. Run `NoReobserve`, `RandomReobserve`, and `GTTargetOracle` on a tiny Docker smoke subset.
4. Add `score_uncertainty`, `margin_uncertainty`, and support feature.
5. Run `SemanticOnly` against `NoReobserve` and `RandomReobserve`.
6. Add HM3D-OVON loading and evaluate `val_seen`, `val_unseen`, `val_seen_synonyms`.
7. Add `FrontierReobserve` and `CAReStyle`.
8. Add Step 4-5 SLAM/map-side metrics only after Step 1-3 evidence is stable.

## Calibration Interpretation Gate

Calibration runs are allowed to choose or reject provisional thresholds and diagnose candidate coverage. They should not be used as held-out paper evidence.

Do not interpret calibration policy metrics unless:

- structural artifact checks pass;
- candidate coverage and ambiguity coverage pass;
- `candidate_backend_uses_gt_for_action = false`;
- policy comparison uses the same manifest rows and candidate artifact for all non-GT policies.

If a coverage recovery artifact is borderline, use the decision tree in `04_first_experiment.md` before launching any policy comparison. Borderline diagnostic policy runs must be labeled diagnostic and cannot be promoted to paper-facing evidence without held-out evaluation confirmation.

## Policy Comparison Interpretation Template

Use this template after a calibration or evaluation policy comparison finishes. Do not interpret policy numbers until the hard validity gate and calibration interpretation gate pass.

### 사실

Required inputs:

```text
summary.json
episodes.jsonl
candidate_decisions.jsonl
viewpoint_decisions.jsonl
artifact_coverage.json
candidate artifact used for all non-GT policies
manifest split and episode ids
```

Required metadata:

| Field | Required value |
| --- | --- |
| `candidate_backend_uses_gt_for_action` | `false` for non-GT policies |
| compared episode ids | identical across policies |
| candidate artifact | identical across non-GT policies |
| `wrong_goal_visit` | commit-based |
| `wrong_goal_pass_through` | diagnostic only |
| GT use | labels, shortest-path references, and oracle upper bounds only |

### Result Tables

Substrate validity table:

| Metric | Value | Gate | Interpretation |
| --- | ---: | --- | --- |
| evaluated episodes |  | expected run size | incomplete run if lower |
| candidate label coverage |  | `>= 0.70` | whether GT labels can evaluate candidates |
| reachable correct-and-wrong rate |  | `>= 0.50` | whether active re-observation is testable |
| `NoReobserve` wrong-goal visit rate |  | `>= 0.10` | whether a wrong-goal stress signal exists |
| `GTTargetOracle` `Success Rate` |  | `1.0` on diagnostic subset | shortest-path / success semantics sanity |

Main behavior table:

| Policy | `Success Rate` | `SPL` | `wrong_goal_visit_rate` | `mean_wasted_path_wrong_goal` | `mean_wasted_path_total` | `mean_num_reobservations` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `GTTargetOracle` |  |  |  |  |  |  |
| `NoReobserve` |  |  |  |  |  |  |
| `RandomReobserve` |  |  |  |  |  |  |
| `SemanticOnly` |  |  |  |  |  |  |

Primary deltas:

| Comparison | Required interpretation |
| --- | --- |
| `SemanticOnly - NoReobserve` | primary H001 Step 1-3 effect |
| `SemanticOnly - RandomReobserve` | whether viewpoint selection is better than extra observation budget |
| `GTTargetOracle - SemanticOnly` | remaining gap from candidate coverage, policy, or execution |
| `GTTargetOracle - NoReobserve` | upper-bound room for improvement |

Uncertainty validity table:

| Metric | Value | Gate |
| --- | ---: | --- |
| wrong-goal `AUROC` |  | `>= 0.60` |
| wrong-goal `AUPRC` gap over positive-rate baseline |  | `>= 0.05` |
| Spearman `U_sem` vs candidate failure |  | `>= 0.15` |
| high-vs-low `U_sem` bucket gap |  | `>= 0.10` |

Qualitative audit table:

| Episode id | Scene | Query | Top candidate correct? | Reobserve? | Final committed candidate correct? | `wrong_goal_visit` | Wasted path reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

Include at least:

- two cases where `SemanticOnly` fixes a `NoReobserve` wrong-goal visit;
- two cases where `SemanticOnly` fails;
- one case where `RandomReobserve` matches or beats `SemanticOnly`, if present;
- one oracle-gap case where `GTTargetOracle` succeeds but all non-GT policies fail.

### Interpretation Rules

| Observed result | Interpretation |
| --- | --- |
| `SemanticOnly` lowers wrong-goal and wasted-path metrics without unacceptable `SPL` / `Success Rate` drop | positive Step 1-3 signal |
| `SemanticOnly` lowers wrong-goal but increases `mean_wasted_path_total` or drops `SPL` beyond gate | travel-cost arbitration failure |
| `SemanticOnly` improves `Success Rate` / `SPL` but not wrong-goal or wasted-path metrics | not evidence for H001 mechanism |
| `SemanticOnly` matches `RandomReobserve` | active viewpoint selection is not yet the contribution |
| `U_sem` validity fails but policy improves | do not claim uncertainty is the causal mechanism; inspect confounds |
| GT oracle gap remains large because correct candidates are missing | candidate backend coverage limitation |
| GT oracle gap remains large despite candidate coverage | policy/viewpoint selection or navigation execution limitation |

### Do Not Claim

- Do not claim paper-facing improvement from calibration split alone.
- Do not claim semantic uncertainty is useful if only `Success Rate` improves.
- Do not hide re-observation travel cost behind `SPL`; report wasted-path components separately.
- Do not compare policies that used different episode ids or different candidate artifacts.
- Do not use `GTTargetOracle` as a deployable baseline.

## Step 4-5 Promotion Gate

This gate decides when H001 can move from Step 1-3 semantic re-observation to Step 4-5 active SLAM/map-side utility. Passing this gate does not mean the thesis direction is finished; it means a SLAM extension is justified enough to implement and evaluate.

### 사실

Required prior evidence:

| Requirement | Minimum condition |
| --- | --- |
| substrate validity | first-probe hard validity gate passes |
| semantic policy signal | `SemanticOnly` passes the primary numeric gate against `NoReobserve` |
| random baseline sanity | `SemanticOnly` passes the `RandomReobserve` gate |
| uncertainty validity | `U_sem` passes the uncertainty validity gate |
| policy provenance | non-GT policies keep `candidate_backend_uses_gt_for_action = false` |
| replayability | same episode ids can be replayed with added map/pose logging |
| cost accounting | `mean_wasted_path_total`, `mean_wasted_path_reobserve`, and `SPL` are available |

Required SLAM-side observability:

| Signal | Timing | Minimum acceptable proxy |
| --- | --- | --- |
| `SLAMGain(v)` input | before viewpoint choice | pose graph connectivity proxy, loop-closure opportunity, tracked-feature/inlier proxy, or pose covariance proxy |
| map/pose outcome | after execution | pose graph connectivity, localization failure count, map consistency, semantic accuracy, or `ATE/RPE` |
| travel cost | before and after execution | path length to re-observation viewpoint and final goal |

### 논문 주장

- Step 4-5 is not justified by better ObjectNav task score alone.
- The extension must show that semantic memory and SLAM/map uncertainty complement each other, rather than one replacing the other.

### 에이전트 추론

Promotion should be staged:

| Level | Meaning | Allowed work |
| --- | --- | --- |
| `P4-design` | Step 1-3 signal exists, but SLAM metric plumbing is not ready | design utility, logging, Docker image, and proxy scripts |
| `P4-proxy` | pose graph or localization proxy is available | run `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` on same episodes |
| `P4-full` | trajectory GT or stable SLAM backend is available | add `ATE/RPE`, map error, semantic accuracy, and repeated evaluation |

Default path: promote to `P4-proxy` first with pose graph connectivity. Promote to `P4-full` only after the proxy run shows nontrivial map/pose benefit without breaking navigation behavior.

### Do Not Promote If

- candidate coverage or ambiguity coverage fails;
- `U_sem` does not predict candidate failure;
- `SemanticOnly` is matched by `RandomReobserve`;
- improvement is only on `Success Rate` / `SPL` without wrong-goal or wasted-path improvement;
- oracle gap analysis says missing correct candidates dominate the failure;
- there is no SLAM-side signal available before action selection;
- travel cost cannot be measured.

### Step 4-5 Experiment Contract

Compare these policies on the same scene / episode / candidate artifact set:

| Policy | Role |
| --- | --- |
| `SemanticOnly` | Step 1-3 reference |
| `SLAMOnly` | tests whether geometry/map utility alone explains the result |
| `SemanticSLAM` | proposed combined utility |
| `NoReobserve` | base semantic-map commitment |
| `RandomReobserve` | observation-budget control |
| `GTTargetOracle` | path upper bound and success semantics sanity |

Use a predeclared utility form:

```text
U(v) = alpha * SemanticGain(v)
     + beta  * SLAMGain(v)
     - gamma * TravelCost(v)
     - eta   * Risk(v)
```

Weights can be selected only on calibration splits. Do not tune `alpha`, `beta`, `gamma`, or `eta` on held-out evaluation splits.

### Step 4-5 Success Gate

`SemanticSLAM` is a positive Step 4-5 signal only if all conditions below hold:

| Condition | Required result |
| --- | --- |
| map/pose improvement over `SemanticOnly` | at least one SLAM/map metric improves by a predeclared nonzero margin |
| task behavior preservation | `Success Rate` drop no worse than 3 percentage points and `SPL` drop no worse than 0.03 absolute or 10 percent relative against `SemanticOnly` |
| travel-cost control | `mean_wasted_path_total` does not increase by more than 0.5 m absolute or 10 percent relative against `SemanticOnly` |
| complementarity | `SLAMOnly` does not fully explain both task behavior and map/pose improvement |
| failure accounting | localization failure, unreachable viewpoint, map update failure, and semantic candidate failure are logged separately |

Suggested first proxy margins:

| Metric | Positive signal |
| --- | --- |
| pose graph connectivity | `lambda2`, loop-closure count, or connected-component proxy improves over `SemanticOnly` |
| localization failure count | lower than `SemanticOnly` without higher wrong-goal rate |
| semantic accuracy / object precision | no worse than `SemanticOnly` by more than 2 percentage points |
| `ATE/RPE` if available | lower than `SemanticOnly` on the same replay / trajectory |

### Failure Interpretation

| Failure | Interpretation | Next action |
| --- | --- | --- |
| `SemanticSLAM` improves map/pose but hurts `SPL` or wasted path | utility overvalues SLAM gain | revise travel-cost normalization |
| `SLAMOnly` matches `SemanticSLAM` | semantic uncertainty is not contributing to Step 4-5 | keep paper centered on SLAM utility or return to semantic gain design |
| `SemanticOnly` beats `SemanticSLAM` on task and map/pose metrics | combined objective is harmful | report negative extension and keep Step 1-3 scope |
| map/pose metrics are noisy or unavailable | instrumentation failure | keep Step 4-5 at `P4-design`, do not claim SLAM benefit |
| real-world `ATE/RPE` lacks external GT | weak deployment evidence | report qualitative or event-level diagnostics only |

## User Decision Needed

- Choose the accepted `SPL` drop threshold for first probe success.
- Choose whether first Docker runtime should extend `VLMaps` or start from Habitat ObjectNav runtime directly.
