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

#### Backend Pool Expansion Analyzer Result

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_backend_pool_expansion.py
output: local_dataset/runs/h001_expanded_retrieval_backend_pool_expansion_v1
request_rows: 5
evaluated_rows: 5
backend_route_action_counts:
  request_backend_candidate_generation: 5
  route_to_goal_validity_confirmation_after_expansion: 0
  defer_backend_pool_unresolved: 0
expanded_candidate_count_min/max: 10 / 10
fixed_candidate_budget_minimum: 20
new_candidate_count_min/max: 4 / 8
reachable_candidate_count_min/max: 1 / 1
no_valid_rows_by_backend_route:
  request_backend_candidate_generation: 3
valid_rows_by_backend_route:
  request_backend_candidate_generation: 2
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
backend_pool_expansion_gate_passed: true
goal_validity_confirmation_unblocked: false
paper_claim_allowed: false
```

사실: The analyzer writes expansion action rows before evaluation label join. The existing paper-scale artifact provides only `10` expanded candidates per row, while the contract requires a fixed minimum of `20`.

에이전트 추론: Goal-validity confirmation remains blocked. The next contract should materialize fixed backend candidate generation rather than pass the top-10 preview into goal-validity confirmation.

#### Backend Candidate Generation Contract

```text
contract: manifests/h001_expanded_retrieval_backend_candidate_generation_v1.json
verify: manifests/h001_expanded_retrieval_backend_candidate_generation_v1.verify.json
source_filter:
  backend_route_action: request_backend_candidate_generation
input_request_rows: 5
fixed_generation_policy: fixed_action_evidence_top20_v1
candidate_backend_family: existing_vlmaps_action_evidence_jsonl
generated_candidate_count_min/max: 20 / 20
generated_candidate_rows_minimum: 100
source_action_evidence_rows_found_minimum: 5
duplicate_candidate_id_count_maximum: 0
nonfinite_candidate_position_count_maximum: 0
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_generation_rows: true
paper_claim_allowed: false
```

사실: The contract freezes fixed top-20 candidate generation before implementation. It uses existing non-GT action evidence, not evaluation labels, as the candidate source.

에이전트 추론: This is the narrowest next step because it tests whether the already materialized non-GT top-20 evidence is enough before triggering expensive deeper backend generation. If the generated top-20 pool still has no-valid rows after evaluation-only reporting, goal-validity confirmation should remain blocked.

#### Backend Candidate Generation Analyzer Result

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_backend_candidate_generation.py
output: local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1
request_rows: 5
evaluated_rows: 5
generated_candidate_rows: 100
candidate_generation_status_counts:
  generated_fixed_top20_pool: 5
  request_deeper_backend_generation: 0
  defer_backend_candidate_generation_unresolved: 0
generated_candidate_count_min/max: 20 / 20
duplicate_candidate_id_count_min/max: 0 / 0
nonfinite_candidate_position_count_min/max: 0 / 0
reachable_or_standoff_candidate_count_min/max: 1 / 1
positive_support_candidate_count_min/max: 3 / 5
evaluation_only_contains_valid_rows: 2
evaluation_only_no_valid_rows: 3
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
backend_candidate_generation_gate_passed: true
goal_validity_confirmation_unblocked: false
deeper_backend_generation_required: true
paper_claim_allowed: false
```

사실: The analyzer writes generation rows before label join and materializes exactly `20` candidates per row from existing non-GT action evidence.

에이전트 추론: The fixed top-20 source is structurally valid, but it does not repair candidate-pool validity for all rows. Goal-validity confirmation remains blocked because `3/5` generated pools still have no valid candidate after evaluation-only reporting. The next contract should define deeper backend generation or a non-GT pool-validity proxy rather than terminal commitment.

#### Deeper Backend Generation Contract

```text
contract: manifests/h001_expanded_retrieval_deeper_backend_generation_v1.json
verify: manifests/h001_expanded_retrieval_deeper_backend_generation_v1.verify.json
status: frozen_design_contract_before_implementation
source_fixed_top20_rows: 5
diagnostic_target_request_rows: 3
target_scene_query_pairs: 2
target_scene_query_keys:
  QaLdnwvtxbs::bed
  bxsVRursffK::bed
first_variant: spatial_nms_p90_k100_d5_v1
expected_candidate_count_minimum_per_request: 50
expected_candidate_count_primary_target_per_request: 100
expected_new_beyond_top20_minimum_per_request: 30
generated_candidate_rows_minimum: 150
duplicate_candidate_id_count_maximum: 0
nonfinite_candidate_position_count_maximum: 0
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_generation_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

사실: The contract freezes a diagnostic deeper backend generation probe for the three fixed top-20 rows that still have no valid candidate after evaluation-only label join.

에이전트 추론: This is backend recall repair, not goal-validity confirmation. Because the target rows were selected by evaluation-only no-valid reporting, paper-facing policy claims remain blocked until either deeper generation is evaluated on a predeclared action-time source or a non-GT pool-validity proxy can isolate the same failure class.

#### Deeper Backend Generation Analyzer / Job

```text
analyzer: runtime/h001_runtime/analyze_expanded_retrieval_deeper_backend_generation.py
job: runtime/jobs/expanded_retrieval_deeper_backend_generation.sh
target_spec_smoke: local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1
existing_artifact_smoke: local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_existing_p97_k20_smoke_v1
full_job_session: h001-deeper-backend-20260529-003000
full_job_status: completed
full_job_log: runtime/logs/expanded-retrieval-deeper-backend-generation-20260529-003000.log
full_job_candidate_artifact: local_dataset/runs/h001_expanded_retrieval_deeper_backend_artifact_spatial_nms_p90_k100_d5_v1/all_scenes_aligned.jsonl
target_spec_source_rows: 5
target_spec_request_rows: 3
target_scene_query_pairs: 2
existing_artifact_generated_candidate_rows: 60
existing_artifact_candidate_count_per_request: 20
existing_artifact_new_beyond_top20: 0
existing_artifact_valid_containing_rows: 0
existing_artifact_no_valid_rows: 3
full_artifact_coverage_ok: true
full_artifact_scene_query_rows: 12
full_artifact_candidates: 1200
full_generated_candidate_rows: 300
full_candidate_count_per_request: 100
full_new_beyond_top20_per_request: 80
full_valid_containing_rows: 2
full_still_no_valid_rows: 1
full_recovered_rows:
  rival_identity:12 first_correct_rank=34 correct_count=3
  rival_identity:14 first_correct_rank=34 correct_count=3
full_still_no_valid_row:
  rival_identity:13
deeper_backend_generation_gate_passed: true
goal_validity_confirmation_unblocked: true
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
paper_claim_allowed: false
```

사실: The analyzer writes action-time deeper generation rows before any GT-analysis label join. It normalizes artifact scene keys, verifies that contract targets are no-valid rows in the previous evaluation-only join, and keeps nonfinite candidates as structural gate evidence rather than crashing the evaluation join.

에이전트 추론: The existing `p97_k20` smoke is a schema and label-join test, not a recovery result. It has only `20` candidates per request and no new candidates beyond top-20, so it is expected to fail the deeper generation gate. The completed `p90_k100_d5` job shows that deeper backend recall can recover valid candidates for `QaLdnwvtxbs::bed`, but not for `bxsVRursffK::bed`. The next contract should define goal-validity confirmation only for recovered rows and keep the still-no-valid row on a backend/pool-validity branch.

#### Goal-Validity Confirmation Contract For Recovered Rows

```text
contract: manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.verify.json
status: frozen_design_contract_before_implementation
source_deeper_generation_rows: 3
target_goal_validity_rows: 2
target_goal_validity_request_ids:
  rival_identity:12
  rival_identity:14
excluded_backend_pool_validity_rows: 1
excluded_request_ids:
  rival_identity:13
candidate_count_per_request: 100
new_beyond_top20_per_request: 80
goal_validity_target_scene_query_pairs: 1
excluded_target_scene_query_pairs: 1
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_request_and_evidence_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

사실: The contract consumes the completed deeper backend generation output and routes only the recovered `QaLdnwvtxbs::bed` rows to goal-validity confirmation evidence. `rival_identity:13` remains on a backend/pool-validity branch because the evaluation-only label join still finds no valid candidate.

에이전트 추론: This prevents a category/pool recall failure from being interpreted as goal-validity evidence. The next analyzer should produce label-free request/evidence rows for `rival_identity:12` and `rival_identity:14`, write a separate backend/pool-validity branch row for `rival_identity:13`, and keep terminal commits blocked.

#### Goal-Validity Confirmation Request / Branch Analyzer

```text
analyzer: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_confirmation.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1
request_rows: 2
branch_rows: 1
candidate_evidence_target_rows: 200
evaluated_rows: 3
handoff_actions:
  request_goal_validity_confirmation_evidence: 2
  request_non_gt_pool_validity_proxy_or_fallback_backend_variant: 1
request_ids:
  rival_identity:12
  rival_identity:14
branch_request_ids:
  rival_identity:13
goal_validity_target_scene_query_pairs:
  QaLdnwvtxbs::bed
excluded_target_scene_query_pairs:
  bxsVRursffK::bed
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
goal_validity_confirmation_request_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

사실: The analyzer writes request rows, candidate evidence target rows, and the backend/pool-validity branch row before attaching evaluation-only labels. Docker compile and the 3-row smoke run passed.

에이전트 추론: This closes the branch handoff step. The still-no-valid `rival_identity:13` branch is now handled by the pool-validity fallback contract below, while candidate-specific goal-validity evidence for `rival_identity:12` and `rival_identity:14` remains a later branch.

#### Pool-Validity Branch Fallback Contract

```text
contract: manifests/h001_expanded_retrieval_pool_validity_branch_v1.json
verify: manifests/h001_expanded_retrieval_pool_validity_branch_v1.verify.json
status: frozen_design_contract_before_implementation
source_branch_rows: 1
target_request_ids:
  rival_identity:13
target_scene_query_keys:
  bxsVRursffK::bed
source_variant: spatial_nms_p90_k100_d5_v1
source_candidate_count: 100
source_reachable_or_standoff_candidate_count: 100
source_positive_support_candidate_count: 5
source_duplicate_candidate_id_count: 0
source_nonfinite_candidate_position_count: 0
non_gt_proxy_ready: false
first_fallback_variant: spatial_nms_p80_k200_d3_v1
second_fallback_variant: components_p80_min1_k200_v1
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

사실: `rival_identity:13` remains no-valid after the completed `spatial_nms_p90_k100_d5_v1` deeper backend generation, but the action-time pool is structurally strong: `100` finite candidates, `100` reachable/standoff candidates, `5` positive-support candidates, no duplicate candidate ids, no nonfinite positions, and high semantic scores.

에이전트 추론: Count, reachability, positive-support, duplicate/nonfinite, and score-shape proxies are not safe pool-validity separators here because the still-no-valid row is not weaker than the recovered rows on those features. The contract therefore rejects a simple proxy and fixes a fallback backend variant before any goal-validity confirmation. This remains diagnostic because the branch row was selected by evaluation-only no-valid reporting.

#### Pool-Validity Branch Analyzer / Job

```text
analyzer: runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_branch.py
job: runtime/jobs/expanded_retrieval_pool_validity_branch.sh
target_spec_smoke: local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1
full_job_session: h001-pool-validity-fallback-20260529-093033
full_job_status: completed
full_job_stage: completed
full_job_log: runtime/logs/expanded-retrieval-pool-validity-branch-20260529-093033.log
full_job_candidate_artifact: local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_spatial_nms_p80_k200_d3_v1/all_scenes_aligned.jsonl
full_artifact_coverage_ok: true
full_artifact_scene_count: 1
full_artifact_query_rows: 6
full_artifact_candidates: 1200
target_spec_branch_rows: 1
target_spec_action_rows: 1
target_spec_evaluated_rows: 1
target_spec_status: defer_pool_validity_fallback_unresolved
target_spec_gate_passed: false
target_spec_expected_reason: fallback_candidate_artifact_row_missing
target_spec_terminal_commit_rows: 0
target_spec_action_forbidden_keys: 0
target_request_ids:
  rival_identity:13
target_scene_query_keys:
  bxsVRursffK::bed
full_fallback_candidate_rows: 200
full_new_beyond_previous_pool: 100
full_gate_passed: true
full_valid_containing_rows: 0
full_no_valid_rows: 1
goal_validity_confirmation_unblocked: false
second_fallback_backend_required: true
```

사실: Docker compile and target-spec smoke passed. The smoke intentionally has no candidate artifact, so it writes schema-valid branch/action/evaluated rows and a false fallback gate with reason `fallback_candidate_artifact_row_missing`. The full `spatial_nms_p80_k200_d3_v1` job completed. The artifact coverage gate passed, and the final analyzer wrote `200` fallback candidates with `100` candidates new beyond the previous pool, but evaluation-only label join still found no valid candidate.

에이전트 추론: This implementation closes the first fallback branch. Because the wider spatial NMS backend is structurally valid but still no-valid, `rival_identity:13` should not move to goal-validity confirmation. The next contract should use the already predeclared component-level fallback `components_p80_min1_k200_v1` or, if that also fails, record `bxsVRursffK::bed` as a backend/source-map recall blind spot.

#### Pool-Validity Second Fallback Contract

```text
contract: manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.json
verify: manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.verify.json
status: frozen_design_contract_before_implementation
source_branch_rows: 1
target_request_ids:
  rival_identity:13
target_scene_query_keys:
  bxsVRursffK::bed
previous_source_variant: spatial_nms_p90_k100_d5_v1
first_fallback_variant: spatial_nms_p80_k200_d3_v1
first_fallback_candidate_count: 200
first_fallback_new_beyond_source_pool_count: 100
first_fallback_valid_containing_rows: 0
first_fallback_no_valid_rows: 1
second_fallback_variant: components_p80_min1_k200_v1
second_fallback_selection_mode: components
second_fallback_top_percentile: 80.0
second_fallback_max_candidates: 200
second_fallback_min_component_cells: 1
terminal_commit_rows_maximum: 0
action_evidence_forbidden_key_count_maximum: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

사실: The second fallback contract is now frozen after the first fallback produced a structurally valid but still no-valid `200`-candidate spatial-NMS pool. The new fixed backend variant is component-level `VLMaps` export with `top_percentile 80.0`, `max_candidates 200`, and `min_component_cells 1`.

에이전트 추론: The second fallback changes backend granularity rather than tuning another spatial-NMS threshold. It must report component candidate count, `component_cells`, duplicate/nonfinite/reachability accounting, and overlap with both previous spatial-NMS pools before any evaluation-only label join. If this also remains no-valid, `bxsVRursffK::bed` should be recorded as a backend/source-map recall blind spot for this branch.

#### Pool-Validity Second Fallback Analyzer / Job

```text
analyzer: runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_second_fallback.py
job: runtime/jobs/expanded_retrieval_pool_validity_second_fallback.sh
target_spec_output: local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1
full_job_session: h001-pool-validity-second-fallback-20260529-151217
full_job_status: completed
full_job_stage: completed
full_job_log: runtime/logs/expanded-retrieval-pool-validity-second-fallback-20260529-151217.log
full_job_candidate_artifact: local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_components_p80_min1_k200_v1/all_scenes_aligned.jsonl
full_artifact_coverage_ok: true
full_artifact_scene_count: 1
full_artifact_query_rows: 6
full_artifact_candidates: 1163
target_spec_branch_rows: 1
target_spec_action_rows: 1
target_spec_evaluated_rows: 1
target_spec_status: defer_component_fallback_unresolved
target_spec_gate_passed: false
target_spec_expected_reason: component_candidate_artifact_row_missing
target_spec_terminal_commit_rows: 0
target_spec_action_forbidden_keys: 0
target_request_ids:
  rival_identity:13
target_scene_query_keys:
  bxsVRursffK::bed
full_component_candidate_rows: 200
full_component_cells_min_mean_max: 1 / 20.29 / 1254
full_new_positions_beyond_first_fallback: 200
full_gate_passed: true
full_valid_containing_rows: 0
full_no_valid_rows: 1
goal_validity_confirmation_unblocked: false
backend_source_map_blind_spot_after_second_fallback: true
```

사실: Docker compile, bash syntax check, and target-spec smoke passed. The full component fallback job completed and generated a structurally valid component pool, but evaluation-only label join still found no valid candidate.

에이전트 추론: This closes the fallback backend branch for `rival_identity:13` under the current diagnostic scope. The row should not be sent to goal-validity confirmation. Treat `bxsVRursffK::bed` as a backend/source-map recall blind spot for this branch unless a later all-row backend policy changes the source-map evidence.

#### Candidate-Specific Goal-Validity Evidence Contract / Planner

사실: The candidate-specific goal-validity evidence contract is frozen at `manifests/h001_expanded_retrieval_goal_validity_evidence_v1.json`. It consumes recovered request rows `rival_identity:12` and `rival_identity:14`, fixes `candidate_specific_goal_validity_evidence_v1`, and requires target-candidate standoff evidence with local rival context. Terminal commit remains blocked and `paper_claim_allowed false`.

Docker planner implementation:

```text
script: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1
request_rows: 2
candidate_evidence_target_rows: 200
plan_rows: 158
skipped_rows: 42
skipped_reason_counts: standoff_navmesh_required 42
plan_rows_by_request: rival_identity:12 79, rival_identity:14 79
candidate_artifact_rows: 1
candidate_artifact_candidate_count: 80
terminal_commit_rows: 0
output_forbidden_action_field_count: 0
uses_gt_for_action: false
goal_validity_evidence_plan_gate_passed: true
verification_command:
  jq -e '.gate.goal_validity_evidence_plan_gate_passed == true and .output_forbidden_action_field_count == 0 and .terminal_commit_rows == 0 and .uses_gt_for_action == false' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan_summary.json
```

에이전트 추론: This planner is stronger than a category-visible detector rule because every observation row is tied to one target candidate plus label-free rival context. The next gate is frame/projection sanity. Detector/SAM2 scoring and terminal utility validation remain blocked until the rendered evidence substrate is verified.

#### Candidate-Specific Goal-Validity Frame/Projection Smoke

사실: Bounded Docker frame/projection smoke passed for the first `20` rows of `goal_validity_evidence_plan_v1`.

```text
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_smoke_v1
rows_exported: 20 / 20
rendered_heading_count: 172
headings_per_row_min_max: 5 / 11
nonblank_rows: 20 / 20
removed_blank_heading_count: 0
projection_visible_rows: 20 / 20
projection_visible_rate: 1.0
missing_candidate_rows: 0
frame_revision_metadata_rows: 20
candidate_selection_source: explicit_candidate_ids 20
uses_gt_for_action: false
paper_claim_allowed: false
projection_anchor_smoke_passed: true
```

에이전트 추론: The rendered substrate is detector-ready for this bounded gate. This still does not authorize terminal commits; detector/SAM2 evidence and a post-detector candidate-specific objective must pass before any utility validation.

#### Candidate-Specific Goal-Validity Detector/SAM2 Substrate

사실: Bounded detector/SAM2 substrate passed for the frame/projection smoke rows.

```text
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1
tmux_session: h001-goal-validity-detector-20260529-171217
detector_rows: 20
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.95
rows_with_candidate_association: 19
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
verification_command:
  cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/job_status.json
  cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_substrate_summary.json
```

에이전트 추론: Perception substrate is not the immediate blocker for the bounded candidate-specific evidence branch. The next gate must be an objective analyzer, not a terminal commit rule, because the previous local-context failures show category visibility can still be wrong ObjectNav goal evidence.

#### Candidate-Specific Goal-Validity Objective Analyzer

사실: The post-detector candidate-specific goal-validity objective analyzer is frozen and Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_objective_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_objective_v1.verify.json
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1
planned_request_rows: 2
planned_candidate_rows: 158
observed_detector_candidate_rows: 20
observed_detector_request_rows: 1
unscored_candidate_rows: 138
candidate_evidence_class_counts:
  candidate_specific_support: 18
  weak_or_partial_candidate_specific_support: 2
  not_scored_in_bounded_substrate: 138
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.95
observed_candidate_evaluation_wrong: 20 / 20
first_correct_generated_rank: 34 for rival_identity:12 and rival_identity:14
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
objective_analyzer_gate_passed: true
terminal_utility_validation_allowed: false
full_detector_substrate_required: true
paper_claim_allowed: false
verification_command:
  jq '{gate:.gate.objective_analyzer_gate_passed, terminal:.terminal_utility_validation_allowed, full_required:.full_detector_substrate_required, forbidden:.action_evidence_forbidden_key_count, observed_wrong:.observed_candidate_evaluation.evaluation_only_observed_wrong_candidate_count, paper:.paper_claim_allowed}' local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1/goal_validity_objective_summary.json
```

에이전트 추론: This closes the bounded post-detector analyzer gate as a diagnostic, not as a utility claim. The result is important because it shows the top-20 bounded detector subset is structurally available but incomplete and wrong-only. Terminal commit, `first_eval`, and policy-scale comparison remain blocked. The full recovered-row candidate-specific detector/SAM2 scoring contract below now includes the recovered correct-rank region and should be executed before any terminal utility validation.

#### Full Candidate-Specific Detector/SAM2 Substrate Contract

사실: The full recovered-row candidate-specific substrate contract is frozen before launch.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.verify.json
source_plan: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan.jsonl
expected_request_rows: 2
expected_plan_rows: 158
expected_plan_rows_by_request: rival_identity:12 79, rival_identity:14 79
expected_correct_candidate_rows_in_plan: 6
expected_correct_candidate_rows_in_skipped: 0
expected_correct_generated_ranks: 34, 57, 60 for both recovered requests
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_full_v1
detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1
expected_frame_rows: 158
expected_detector_rows: 158
detector_box_rate_minimum: 0.80
sam2_mask_rate_minimum: 0.80
candidate_association_rate_minimum: 0.40
terminal_commit_allowed: false
paper_claim_allowed: false
```

에이전트 추론: This contract specifically fixes the bounded top-20 failure: it requires both recovered rows and the expected correct-rank region before detector evidence can be interpreted. Passing it permits a full post-detector objective analyzer run, not a terminal ObjectNav utility claim.

#### Full Candidate-Specific Objective Analyzer

사실: The full recovered-row candidate-specific substrate and objective analyzer are Docker-verified.

```text
substrate_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1
objective_contract: manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.json
objective_verify: manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.verify.json
objective_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_full_v1
detector_rows: 158
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.9746835443037974
observed_request_rows: 2
observed_candidate_rows: 158
unscored_candidate_rows: 0
candidate_evidence_class_counts:
  candidate_specific_support: 146
  weak_or_partial_candidate_specific_support: 12
evaluation_only_observed_correct_candidate_count: 6
evaluation_only_observed_wrong_candidate_count: 152
proposed_objective_action: defer_candidate_specific_support_ambiguous for both request rows
unsafe_simpler_alternatives:
  semantic_top_observed: wrong 2 / 2
  detector_score_best_observed: wrong 2 / 2
  positive_support_best_observed: wrong 2 / 2
  candidate_specific_support_best_observed: wrong 2 / 2
terminal_commit_rows: 0
objective_analyzer_gate_passed: true
terminal_utility_validation_allowed: false
paper_claim_allowed: false
```

에이전트 추론: Full substrate resolves the bounded coverage flaw but exposes a stronger failure mechanism: candidate-specific visual support is saturated across many same-category candidates. Detector score, semantic rank, positive support, and support-count variants are unsafe on the recovered rows. The next contract should target ambiguity resolution or discriminative goal evidence, not terminal commit thresholding.

#### Candidate-Specific Ambiguity-Resolution Diagnostic Contract

사실: The next diagnostic contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_full_v1/goal_validity_objective_summary.json
expected_request_rows: 2
expected_candidate_rows: 158
candidate_specific_support_count_minimum: 100
evaluation_only_correct_candidate_count_minimum: 6
blocked_actions:
  threshold_tune_detector_score
  threshold_tune_semantic_rank
  terminal_commit_from_support_count
  first_eval_rerun
required_diagnostics:
  support_saturation_profile
  unsafe_selector_taxonomy
  next_evidence_requirement
terminal_commit_allowed: false
paper_claim_allowed: false
```

에이전트 추론: This contract turns the negative result into the next research question: whether active semantic uncertainty needs discriminative instance, relation, or goal-region evidence after visual support becomes saturated. It keeps the work aligned with novelty-by-failure-mechanism rather than adding another score threshold.

#### Candidate-Specific Ambiguity-Resolution Analyzer

사실: The ambiguity-resolution diagnostic analyzer is implemented and Docker-verified.

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_ambiguity.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1
request_rows: 2
candidate_rows: 158
candidate_specific_support_count: 146
candidate_specific_support_rate: 0.9240506329113924
correct_support_count: 6
wrong_support_count: 140
correct_wrong_support_overlap: true
selector_rows: 8
wrong_selector_rows: 8
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
ambiguity_diagnostic_gate_passed: true
recommended_next_actions:
  request_discriminative_instance_or_goal_region_evidence
  request_relation_or_spatial_context_evidence
  defer_goal_validity_terminal_policy
paper_claim_allowed: false
```

에이전트 추론: The diagnostic supports a narrower next step: first test discriminative instance or goal-region evidence, then relation/spatial context evidence if the first probe remains ambiguous. This is stronger than threshold tuning because it follows the observed failure mechanism.

#### Discriminative Instance/Goal-Region Evidence Contract

사실: The discriminative evidence contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1/goal_validity_ambiguity_resolution_summary.json
request_ids:
  rival_identity:12
  rival_identity:14
expected_request_rows: 2
expected_candidate_rows: 158
candidate_specific_support_count: 146
wrong_selector_rows: 8
evaluation_only_correct_candidates:
  vlmaps:export:bed:spatial_nms:33
  vlmaps:export:bed:spatial_nms:56
  vlmaps:export:bed:spatial_nms:59
evaluation_only_unsafe_selector_candidates:
  vlmaps:export:bed:spatial_nms:0
  vlmaps:export:bed:spatial_nms:21
  vlmaps:export:bed:spatial_nms:23
required_outputs:
  goal_validity_discriminative_candidate_rows.jsonl
  goal_validity_discriminative_pair_rows.jsonl
  goal_validity_discriminative_request_rows.jsonl
  goal_validity_discriminative_evidence_summary.json
blocked_actions:
  threshold_tuning
  terminal_commit_from_support_count
  first_eval_rerun
  policy_scale_comparison
terminal_commit_allowed: false
paper_claim_allowed: false
```

에이전트 추론: This contract fixes the next question as separability, not confidence. The analyzer should test whether non-GT visual/geometric evidence can distinguish unsafe early-rank selected candidates from late-rank valid candidates or whether the method must request relation/spatial-context evidence and keep terminal policy deferred.

#### Discriminative Instance/Goal-Region Analyzer

사실: The discriminative evidence analyzer is implemented and Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_discriminative_evidence.py
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1
request_rows: 2
candidate_rows: 158
pair_rows: 420
target_contrast_pair_rows_after_label_join: 18
candidate_specific_support_count: 146
simple_selector_candidate_count: 6
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
discriminative_evidence_gate_passed: true
target_pair_visual_delta_sign_counts:
  contrast_visual_higher: 8
  selector_visual_higher: 10
target_pair_region_proxy_counts:
  adjacent_region_proxy: 12
  distinct_region_proxy: 6
diagnostic_conclusion: discriminative_instance_or_goal_region_signal_ready false
recommended_next_action: request_relation_or_spatial_context_evidence
paper_claim_allowed: false
```

에이전트 추론: The diagnostic rejects instance/goal-region visual separability as a terminal selector for this recovered-row branch. The target contrast grid exists, but action-time features still favor unsafe selector candidates in more than half of the target pairs. The next contract should ask for relation or spatial-context evidence rather than relaxing detector/support thresholds.

#### Relation/Spatial Context Evidence Contract

사실: The relation/spatial context evidence contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1/goal_validity_discriminative_evidence_summary.json
request_rows: 2
candidate_rows: 158
pair_rows: 420
candidate_specific_support_count: 146
target_contrast_pair_rows_after_label_join: 18
target_pair_visual_delta_sign_counts_after_label_join:
  contrast_visual_higher: 8
  selector_visual_higher: 10
target_pair_region_proxy_counts_after_label_join:
  adjacent_region_proxy: 12
  distinct_region_proxy: 6
required_outputs:
  goal_validity_relation_spatial_candidate_context_rows.jsonl
  goal_validity_relation_spatial_pair_context_rows.jsonl
  goal_validity_relation_spatial_request_context_rows.jsonl
  goal_validity_relation_spatial_context_summary.json
blocked_actions:
  direct_candidate_commit
  threshold_tuning
  first_eval_rerun
  policy_scale_comparison
terminal_commit_allowed: false
paper_claim_allowed: false
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_relation_spatial_context.py
```

에이전트 추론: This contract turns the negative discriminative result into a more precise diagnostic: action-time context rows must test whether unsafe selectors and late-rank valid candidates differ by local spatial component, neighborhood density, relation-to-anchor, or co-visibility proxy. Correctness labels can only be joined after those context rows are written. If context features still cannot separate the pairs, the branch should remain deferred or request richer scene-graph/object-relation evidence.

#### Relation/Spatial Context Analyzer

사실: The relation/spatial context analyzer is implemented and Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_relation_spatial_context.py
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1
request_rows: 2
candidate_context_rows: 158
pair_context_rows: 420
spatial_context_group_count: 8
target_contrast_pair_rows_after_label_join: 18
target_pair_component_relation_counts:
  same_component: 12
  distinct_component: 6
target_pair_context_score_delta_sign_counts:
  contrast_context_higher: 18
target_pair_failure_taxonomy_counts:
  same_component_selector_visual_dominates: 10
  same_component_context_not_discriminative: 2
  context_candidate_for_followup: 6
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
relation_spatial_context_gate_passed: true
diagnostic_conclusion: relation_spatial_context_signal_ready false
recommended_next_action: request_scene_graph_or_object_relation_evidence
paper_claim_allowed: false
```

에이전트 추론: Static relation/spatial context is useful as a failure diagnostic because all target contrast pairs have higher context score for the contrast candidate. It is not sufficient as a terminal selector because most target pairs remain in the same spatial component and unsafe selector visual evidence still dominates in `10/18` target pairs. The next contract should define object-relation or scene-graph evidence and keep terminal policy blocked.

#### Scene-Graph/Object-Relation Evidence Contract

사실: The scene-graph/object-relation evidence contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1/goal_validity_relation_spatial_context_summary.json
request_rows: 2
candidate_context_rows: 158
pair_context_rows: 420
spatial_context_group_count: 8
target_contrast_pair_rows_after_label_join: 18
same_component_target_pair_rows_after_label_join: 12
same_component_selector_visual_dominates_after_label_join: 10
required_outputs:
  goal_validity_scene_graph_candidate_relation_rows.jsonl
  goal_validity_scene_graph_pair_relation_rows.jsonl
  goal_validity_scene_graph_request_relation_rows.jsonl
  goal_validity_scene_graph_context_object_rows.jsonl
  goal_validity_scene_graph_object_relation_summary.json
blocked_actions:
  direct_candidate_commit
  threshold_tuning
  first_eval_rerun
  policy_scale_comparison
terminal_commit_allowed: false
paper_claim_allowed: false
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_scene_graph_object_relation.py
```

에이전트 추론: This contract narrows the next diagnostic to same-component object-relation evidence. It does not allow importing GT scene graphs. The intended evidence is action-time relation rows computed from RGB-D, detector/SAM2 masks, candidate geometry, and non-GT context detections. If those relations cannot separate unsafe selectors from late-rank valid candidates, the branch should remain deferred or move to a new active observation design.

#### Scene-Graph/Object-Relation Evidence Analyzer

사실: The scene-graph/object-relation evidence analyzer is implemented and Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_scene_graph_object_relation.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
scene_graph_object_relation_gate_passed: true
request_rows: 2
candidate_relation_rows: 158
pair_relation_rows: 420
context_object_rows: 7788
target_contrast_pair_rows_after_label_join: 18
same_component_target_pair_rows_after_label_join: 12
same_component_selector_visual_dominates_after_label_join: 10
target_pair_relation_delta_sign_counts_after_label_join:
  contrast_relation_higher: 18
relation_separability_probe_supports_signal: true
relation_coverage_complete: true
detector_coverage_complete: false
rows_with_detector_association_by_request:
  rival_identity:12: 77 / 79
  rival_identity:14: 77 / 79
scene_graph_object_relation_signal_ready: false
recommended_next_action: request_object_relation_observation
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
paper_claim_allowed: false
```

에이전트 추론: The object-relation proxy is directionally useful because every evaluation-only target contrast pair has higher relation signature score for the contrast candidate, including the same-component selector-visual failures. It is still not a terminal selector because detector association coverage is incomplete and the signal is measured in a narrow recovered-row diagnostic. The next contract should repair or explicitly account for object-relation observation coverage before any `first_eval` rerun, threshold tuning, or policy-scale comparison.

#### Object-Relation Observation Coverage Repair Contract

사실: The object-relation observation coverage repair contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1/goal_validity_scene_graph_object_relation_summary.json
scene_graph_object_relation_gate_passed: true
scene_graph_object_relation_signal_ready: false
recommended_next_action: request_object_relation_observation
request_rows: 2
candidate_relation_rows: 158
pair_relation_rows: 420
context_object_rows: 7788
detector_coverage_complete: false
rows_with_detector_association_by_request:
  rival_identity:12: 77 / 79
  rival_identity:14: 77 / 79
detector_missing_candidate_rows: 4
detector_missing_unique_candidate_ids:
  - vlmaps:export:bed:spatial_nms:5
  - vlmaps:export:bed:spatial_nms:90
evaluation_only_missing_detector_correct_rows: 0
evaluation_only_missing_detector_target_pair_rows: 0
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
paper_claim_allowed: false
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_coverage_repair.py
```

에이전트 추론: The missing detector rows are not target-pair or correct-candidate rows under the current evaluation-only join, but that fact must not be used as an action-time shortcut. The next analyzer should materialize coverage-gap rows and either request bounded object-relation observations or define an action-time waiver before any terminal policy, threshold tuning, or `first_eval` rerun.

#### Object-Relation Observation Coverage Repair Analyzer

사실: The object-relation observation coverage repair analyzer is Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_coverage_repair.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1
coverage_gap_rows: 4
repair_action_rows: 4
repair_action_counts:
  request_object_relation_observation: 2
  waive_non_target_policy_promotion_only: 2
request_coverage_rows: 2
evaluated_coverage_gap_rows: 4
evaluation_only_missing_detector_candidate_valid_rows: 0
evaluation_only_missing_detector_target_pair_rows: 0
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
coverage_repair_gate_passed: true
paper_claim_allowed: false
recommended_next_action: freeze_object_relation_observation_plan_contract
```

에이전트 추론: The analyzer preserves the label separation rule: rank-6 dense relation gaps become bounded observation targets, while rank-91 medium relation gaps are waived only from terminal-policy promotion by an action-time rank/context rule. This resolves the coverage materialization step but still does not permit terminal relation utility or `first_eval` rerun.

#### Object-Relation Observation Plan Contract

사실: The object-relation observation plan contract is frozen before planner implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1/goal_validity_object_relation_coverage_repair_summary.json
planner_name: object_relation_depth_recheck_standoff_v1
observation_target_rows: 2
observation_targets:
  - rival_identity:12 / vlmaps:export:bed:spatial_nms:5 / rank 6 / relation_dense
  - rival_identity:14 / vlmaps:export:bed:spatial_nms:5 / rank 6 / relation_dense
waiver_rows_kept_out_of_terminal_policy_promotion: 2
minimum_plan_rows: 8
minimum_plan_rows_per_request: 4
relation_anchor_candidates_per_plan_minimum: 2
required_viewpoint_policy: relation_multiview_depth_recheck_v1
projection_anchor_policy: projection_anchor_height_sweep_v1
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
paper_claim_allowed: false
next_script_target: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py
```

에이전트 추론: This contract turns the coverage repair output into a planner-only task. The next implementation must create relation-aware multiview/depth-recheck observation rows from action-time relation anchors, not a relation-score terminal selector or an evaluation-label shortcut.

#### Object-Relation Observation Planner

사실: The object-relation observation planner is Docker-verified.

```text
script: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py
docker_image: research3/habitat-h001:20260508-calib-artifacts
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1
plan_rows: 8
skipped_rows: 0
plan_rows_by_request:
  rival_identity:12: 4
  rival_identity:14: 4
relation_anchor_candidates_per_plan_min_mean_max: 8 / 8 / 8
direction_sources: source_viewpoint_to_target, target_to_relation_anchor, relation_anchor_to_target, orthogonal_relation_axis
candidate_artifact_rows: 1
output_forbidden_action_field_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
paper_claim_allowed: false
object_relation_observation_plan_gate_passed: true
```

에이전트 추론: The planner now turns the dense relation coverage gap into a bounded action-time observation substrate. It still does not provide terminal utility; the next gate is frame/projection smoke and then detector substrate validation.

#### Object-Relation Observation Frame/Projection Smoke

사실: The object-relation observation frame/projection smoke is Docker-verified.

```text
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_frames_v1
filtered_frame_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_projection_v1
frame_rows: 8 / 8
rendered_heading_count: 72
headings_per_row_min_max: 9 / 9
candidate_point_field: grounded_position
candidate_ids_per_frame: 9
nonblank_rows: 8 / 8
removed_blank_heading_count: 0
strict_no_blank_heading_gate_passed: true
projection_visible_rows: 8 / 8
projection_visible_rate: 1.0
missing_candidate_rows: 0
frame_revision_metadata_rows: 8
candidate_selection_source: explicit_candidate_ids
uses_gt_for_action: false
paper_claim_allowed: false
projection_anchor_smoke_passed: true
```

에이전트 추론: The render/projection substrate is now detector-ready. This still only verifies viewpoint/render/projection feasibility, not whether detector/SAM2 association resolves the visible-but-depth-weak relation gap.

#### Object-Relation Observation Detector Substrate

사실: The object-relation observation detector substrate is Docker-verified.

```text
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1
detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1/detector_v3c
log: runtime/logs/object-relation-detector-substrate-20260530-092542.log
detector_rows: 8
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 1.0
rows_with_candidate_association: 8 / 8
associated_candidate_heading_count: 48
association_rows: 72
detector_box_rows: 110
detector_mask_rows: 110
projection_status_counts:
  visible: 58
  out_of_fov: 14
candidate_selection_source: explicit_candidate_ids
projection_anchor_policy: projection_anchor_height_sweep_v1
uses_gt_for_action: false
paper_claim_allowed: false
passes_detector_substrate_gate: true
```

에이전트 추론: Detector availability and candidate association are no longer the blocker for these two dense relation gaps. The post-detector evidence contract below defines nonterminal evidence rows and decides whether the new detector-depth evidence resolves the prior visible-but-depth-weak relation gap, while still separating this substrate result from terminal goal-validity utility.

#### Object-Relation Post-Detector Evidence Contract

사실: The object-relation post-detector evidence analyzer contract is frozen before analyzer implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1.verify.json
source_plan_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1/goal_validity_object_relation_observation_plan_summary.json
source_projection_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_projection_v1/projection_anchor_smoke_summary.json
source_detector_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json
source_association_rows: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1/detector_v3c/detector_candidate_associations.jsonl
analyzer_name: object_relation_detector_depth_evidence_v1
expected_request_rows: 2
expected_plan_rows: 8
expected_detector_rows: 8
expected_association_rows: 72
minimum_evidence_rows: 8
minimum_request_rows: 2
minimum_associated_candidate_heading_count: 40
minimum_depth_consistent_rows: 32
depth_check_status_counts:
  consistent: 44
  depth_mismatch: 14
  out_of_fov: 14
allowed_evidence_status:
  - relation_depth_recheck_resolved
  - relation_depth_recheck_partial
  - relation_depth_recheck_unresolved
required_outputs:
  - goal_validity_object_relation_evidence_rows.jsonl
  - goal_validity_object_relation_request_rows.jsonl
  - goal_validity_object_relation_evaluated_rows.jsonl
  - goal_validity_object_relation_evidence_summary.json
terminal_commit_rows: 0
uses_gt_for_action: false
paper_claim_allowed: false
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1
```

에이전트 추론: This contract moves the branch from detector availability to nonterminal evidence aggregation. A positive analyzer result may show that relation-aware re-observation resolves a detector-depth coverage gap, but it still cannot authorize direct commit, threshold tuning, `first_eval` rerun, or policy-scale comparison until a separate terminal utility gate is fixed and validated.

#### Object-Relation Post-Detector Evidence Analyzer

사실: The object-relation post-detector evidence analyzer is Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1
evidence_rows: 8
request_rows: 2
evaluation_only_rows: 2
association_rows: 72
detector_rows: 8
associated_candidate_heading_count: 48
depth_check_status_counts:
  consistent: 44
  depth_mismatch: 14
  out_of_fov: 14
request_evidence_status_counts:
  relation_depth_recheck_resolved: 2
evaluation_only_candidate_correct_counts:
  false: 2
evaluation_only_interpretation:
  resolved_detector_depth_gap_for_evaluation_negative_candidate: 2
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
object_relation_evidence_gate_passed: true
paper_claim_allowed: false
recommended_next_action: validate_object_relation_evidence_output_before_terminal_contract
```

에이전트 추론: The analyzer resolves the detector-depth coverage gap, but it resolves it for candidates that are negative under evaluation-only labels. This strengthens the terminal blocker: object-relation detector/depth evidence can repair observation coverage, but object visibility and depth consistency still do not imply valid `ObjectNav` goal identity. The next gate should freeze this interpretation before any terminal utility contract or `first_eval` rerun.

#### Object-Relation Evidence Interpretation Gate

사실: The object-relation evidence interpretation gate is frozen.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_interpretation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_interpretation_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1/goal_validity_object_relation_evidence_summary.json
source_evidence_gate_passed: true
evidence_rows: 8
request_rows: 2
evaluation_only_rows: 2
request_evidence_status_counts:
  relation_depth_recheck_resolved: 2
evaluation_only_candidate_correct_counts:
  false: 2
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
terminal_utility_validation_allowed: false
paper_claim_allowed: false
blocked_actions:
  - direct_candidate_commit
  - detector_association_best_commit
  - relation_depth_resolved_commit
  - threshold_tuning_from_evaluation_labels
  - first_eval_rerun
  - policy_scale_comparison
  - terminal_goal_validity_policy
next_contract_required: non-GT goal-validity arbitration before terminal utility
```

에이전트 추론: This freezes the negative interpretation instead of treating it as a failed implementation detail. The useful evidence is now a sharper failure mechanism: relation-aware active observation can repair detector/depth coverage, but repeated-object goal validity still requires a separate non-GT arbitration signal. Any next terminal contract must first reject relation-depth-resolved negative candidates; otherwise it will reproduce the same wrong-goal mechanism under a stronger detector substrate.

#### Object-Relation Goal-Validity Arbitration Rule

사실: The bounded non-GT object-relation arbitration rule is frozen and Docker-smoked.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1.verify.json
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_arbitration.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1
policy: relation_depth_guarded_non_gt_arbitration_v1
decision_rows: 2
evaluated_rows: 2
base_candidate_rows: 158
relation_depth_resolved_rows: 2
arbitration_action_counts:
  reject_relation_depth_resolved_without_independent_candidate_support: 2
evaluation_only_candidate_correct_counts:
  false: 2
evaluation_only_interpretation_counts:
  rejected_relation_depth_resolved_negative_candidate: 2
support_saturation_eligible_candidate_count_per_row: 73
support_saturation_rate_per_row: 0.9240506329113924
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
object_relation_arbitration_rule_gate_passed: true
terminal_utility_validation_allowed: false
paper_claim_allowed: false
```

에이전트 추론: The rule rejects the current relation-depth-resolved negative candidates without reading evaluation labels at action time. The rejection mechanism is not "the candidate is negative"; it is that relation-depth evidence cannot override missing independent candidate-specific support from the full substrate. This is a useful guard, but not a utility result: it produces zero terminal commits and must be validated on a fresh/predeclared source before a terminal contract can be written.

#### Fresh Object-Relation Arbitration Source

사실: The fresh/predeclared source precheck for object-relation arbitration validation is Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1.verify.json
script: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1
source_rows: 7
evaluated_rows: 7
request_ids: rival_identity:3, rival_identity:5, rival_identity:7, rival_identity:22, rival_identity:25, rival_identity:27, rival_identity:29
unique_scene_count: 5
unique_query_count: 3
candidate_count_sum: 36
detector_strong_candidate_count_sum: 28
bounded_arbitration_overlap_count: 0
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
fresh_source_precheck_gate_passed: true
object_relation_evidence_generation_required: true
object_relation_arbitration_validation_ready: false
terminal_utility_validation_allowed: false
paper_claim_allowed: false
```

에이전트 추론: This is a source freeze, not an arbitration validation result. The source is fresh relative to the bounded rule smoke because request-id overlap is `0`, and it keeps route-specific candidate evidence before label join. The next experiment must generate object-relation observation/evidence rows for these seven requests, then apply the fixed arbitration rule before any terminal contract.

#### Fresh Object-Relation Observation Plan

사실: The fresh object-relation observation inputs and Habitat standoff plan are Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1.verify.json
input_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs.py
planner: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py
input_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs_v1
plan_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1
target_rows: 36
repair_action_rows: 36
context_object_rows: 152
missing_plan_rows: 0
candidate_positions_missing: 0
plan_rows: 144
skipped_rows: 0
plan_rows_by_request: 16-24
candidate_artifact_rows: 5
candidate_artifact_candidate_count: 26
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
object_relation_observation_plan_gate_passed: true
paper_claim_allowed: false
```

에이전트 추론: This is still a planner substrate. It confirms the fresh route-specific source can be converted into relation-aware active observation viewpoints without label leakage. The frame/projection gate below is now passed, so the next gate is detector/SAM2 substrate, then fixed-rule arbitration validation.

#### Fresh Object-Relation Frame/Projection Smoke

사실: The fresh object-relation frame/projection substrate is Docker-verified.

```text
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_frame_projection_v1.verify.json
job_wrapper: runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_frame_projection.sh
log: runtime/logs/fresh-object-relation-frame-projection-20260531-000459.log
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1
expected_frame_rows: 144
rows_exported: 144
rendered_heading_count: 576
nonblank_output_rows: 144
kept_heading_count: 573
removed_blank_heading_count: 3
blank_heading_scene/query: bxsVRursffK / plant
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: false
projection_anchor_visible_rows: 141
projection_expected_rows: 144
projection_anchor_visible_rate: 0.9792
missing_candidate_rows: 0
gt_action_rows: 0
projection_anchor_smoke_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This passes the detector-substrate entry gate because no observation row is dropped and no candidate is missing from projection. The three blank headings are a rendering/viewpoint limitation in `bxsVRursffK/plant`, not a row-level blocker. This result is not terminal utility evidence.

#### Fresh Object-Relation Detector/SAM2 Substrate

사실: The fresh object-relation detector/SAM2 substrate is Docker-verified.

```text
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate_v1.verify.json
job_wrapper: runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate.sh
base_script: runtime/jobs/expanded_retrieval_detector_substrate.sh
log: runtime/logs/fresh-object-relation-detector-substrate-20260531-013027.log
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1
detector_rows: 144
detector_box_rate: 0.9583
sam2_mask_rate: 0.9583
candidate_association_rate: 0.8264
rows_with_candidate_association: 119 / 144
associated_candidate_heading_count: 338
association_rows: 573
detector_box_rows: 906
detector_mask_rows: 906
projected_pixel_inside_mask_count: 401
projection_status_counts: visible 561, out_of_fov 12
gt_action_rows: 0
passes_detector_substrate_gate: true
paper_claim_allowed: false
```

에이전트 추론: This removes the immediate detector availability and candidate-association blocker for the fresh object-relation source. It still does not prove goal validity or terminal navigation utility because the next step must aggregate detector-depth evidence, then apply the fixed non-GT arbitration rule before any evaluation-only label join.

#### Fresh Object-Relation Post-Detector Evidence

사실: The fresh object-relation post-detector evidence analyzer is Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1.verify.json
label_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_labels.py
evidence_analyzer: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1
label_rows: 36
evaluation_only_correct/wrong: 11 / 25
request_rows: 36
evidence_rows: 108
association_rows: 573
associated_candidate_heading_count: 338
depth_consistent_rows: 321
depth_mismatch_rows: 223
out_of_fov_rows: 12
evidence_status_counts:
  relation_depth_recheck_resolved: 24
  relation_depth_recheck_partial: 12
evaluation_only_interpretation_counts:
  resolved_detector_depth_gap_for_evaluation_positive_candidate: 3
  resolved_detector_depth_gap_for_evaluation_negative_candidate: 21
  partial_detector_depth_gap_after_relation_observation: 12
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
object_relation_evidence_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The fresh evidence is strong enough to run the fixed arbitration rule, but it is not safe as a direct terminal signal. Most resolved rows are evaluation-negative after label join (`21` negative vs `3` positive), so detector-depth resolution alone would be an unsafe commit authority.

#### Fresh Object-Relation Fixed-Rule Arbitration

사실: The fresh fixed-rule object-relation arbitration validation is Docker-verified and fails the promotion gate.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_v1.verify.json
base_support_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_base_support.py
arbitration_analyzer: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_arbitration.py
base_support_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_base_support_v1
arbitration_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_v1
base_support_candidate_rows: 36
base_support_candidate_specific_support_rows: 7
base_support_associated_candidate_rows: 33
base_support_missing_rows: 0
fresh_base_support_gate_passed: true
decision_rows: 36
relation_depth_resolved_rows: 24
decision_action_counts:
  reject_relation_depth_resolved_without_independent_candidate_support: 20
  defer_relation_depth_unresolved_or_partial: 12
  provisional_unique_goal_validity_candidate_requires_fresh_validation: 4
evaluation_only_interpretation_counts:
  rejected_relation_depth_resolved_negative_candidate: 17
  rejected_relation_depth_resolved_positive_candidate: 3
  provisional_relation_depth_resolved_negative_candidate: 4
  provisional_relation_depth_resolved_positive_candidate: 0
  deferred_relation_depth_resolved_positive_candidate: 8
  deferred_relation_depth_resolved_negative_candidate: 4
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
object_relation_arbitration_rule_gate_passed: false
paper_claim_allowed: false
```

에이전트 추론: The fixed rule remains useful as a failure diagnostic but is not promotable. It rejects many resolved negatives, which supports the guard intuition, but it also rejects positives and gives provisional status to wrong repeated-object candidates. This means independent own-view support and relation-depth consistency still describe object visibility, not `ObjectNav` goal validity. The next gate is failure diagnosis, not terminal utility, `first_eval` rerun, or threshold tuning.

#### Fresh Object-Relation Arbitration Failure Diagnosis

사실: The fresh object-relation arbitration failure diagnosis is Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure_v1.verify.json
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure_v1
candidate_failure_rows: 36
request_failure_rows: 7
primary_failure_class_counts:
  negative_rejected_missing_independent_support: 17
  positive_deferred_partial_relation_depth: 8
  wrong_provisional_unique_support: 4
  positive_rejected_missing_independent_support: 3
  negative_deferred_partial_relation_depth: 4
request_failure_tag_counts:
  negative_candidates_blocked_by_missing_support: 7
  correct_goal_relation_depth_partial: 5
  unique_independent_support_selects_wrong_goal: 4
  object_visibility_preferred_over_true_goal_validity: 4
  correct_goal_rejected_by_missing_strong_own_view: 3
  true_candidate_support_blocked_by_relation_depth_partial: 3
  semantic_top_can_be_wrong_visible_object: 3
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
fresh_arbitration_failure_diagnostic_gate_passed: true
terminal_utility_validation_allowed: false
paper_claim_allowed: false
```

에이전트 추론: The key failure mechanism is now concrete: object visibility and relation-depth consistency do not establish `ObjectNav` goal validity. Four requests have unique independent support on a wrong candidate, three requests reject a correct candidate for missing strong own-view support, and five requests have correct goals blocked by partial relation-depth evidence. The next contract must introduce branch-specific goal-validity evidence or keep those rows deferred; threshold tuning is not allowed.

#### Branch-Specific Goal-Validity Evidence Contract

사실: The branch-specific object-relation goal-validity evidence contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure_v1/object_relation_fresh_arbitration_failure_summary.json
expected_request_rows: 7
expected_candidate_rows: 36
branches:
  unique_support_visibility_not_goal_validity
  correct_candidate_missing_own_view_support
  partial_relation_depth_true_goal
  negative_missing_support_guard
terminal_commit_allowed: false
terminal_utility_validation_allowed: false
paper_claim_allowed: false
next_implementation_target: runtime/h001_runtime/route_expanded_retrieval_goal_validity_object_relation_branch_evidence.py
```

에이전트 추론: This contract converts the negative fixed-rule result into a method-design requirement. `unique_support_visibility_not_goal_validity` is the highest-value branch because it directly explains why a strong visible-object signal can still produce wrong `ObjectNav` goals. `partial_relation_depth_true_goal` and `correct_candidate_missing_own_view_support` prevent the rule from treating observation incompleteness as candidate invalidity. The implementation must first write branch router rows and an evaluation-only coverage audit; it must not create terminal commits or tune thresholds from joined labels.

#### Branch-Specific Goal-Validity Router

사실: The branch-specific object-relation goal-validity router is Docker-verified.

```text
script: runtime/h001_runtime/route_expanded_retrieval_goal_validity_object_relation_branch_evidence.py
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1
request_rows: 7
candidate_rows: 36
evaluated_branch_request_rows: 7
request_branch_counts:
  unique_support_visibility_not_goal_validity: 4
  partial_relation_depth_true_goal: 6
  correct_candidate_missing_own_view_support: 7
  negative_missing_support_guard: 7
failure_tag_branch_coverage: all known tags covered
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
selected_next_branch: unique_support_visibility_not_goal_validity
selected_next_action: request_contrastive_goal_region_evidence
branch_evidence_router_gate_passed: true
paper_claim_allowed: false
```

에이전트 추론: The router is a nonterminal harness component. It proves that the fresh failure taxonomy can be converted into branch-specific evidence requests without label leakage or terminal commits. It does not prove navigation utility. The next contract should focus on `unique_support_visibility_not_goal_validity`, because this branch most directly supports the paper mechanism: visible object support must be converted into contrastive goal-region evidence rather than terminal commitment.

#### Unique-Support Goal-Region Observation Contract

사실: The first branch-specific observation contract is frozen before planner implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1.verify.json
source_router_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1
target_branch: unique_support_visibility_not_goal_validity
target_action: request_contrastive_goal_region_evidence
target_request_rows: 4
focus_candidate_rows: 4
expected_pair_rows_if_all_rivals_materialized: 17
expected_candidate_target_rows_if_all_rivals_materialized: 21
target_requests:
  rival_identity:3 QaLdnwvtxbs sofa focus vlmaps:export:sofa:spatial_nms:1
  rival_identity:5 bCPU9suPUw9 bed focus vlmaps:export:bed:spatial_nms:2
  rival_identity:7 q3zU7Yy5E5s bed focus vlmaps:export:bed:spatial_nms:2
  rival_identity:22 4ok3usBNeis sofa focus vlmaps:export:sofa:spatial_nms:5
minimum_contrastive_rivals_per_request: 2
terminal_commit_allowed: false
terminal_utility_validation_allowed: false
paper_claim_allowed: false
next_implementation_target: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_unique_support_goal_region.py
```

에이전트 추론: This contract freezes the paper-relevant mechanism test for visible-object false positives. The planner must materialize focus-vs-rival goal-region rows before any correctness-label join, then use observation as a nonterminal evidence request. A later positive result would support "semantic uncertainty as active motion utility"; this contract alone is not a utility claim.

#### Unique-Support Goal-Region Planner

사실: The unique-support goal-region planner is implemented and Docker-smoked.

```text
script: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_unique_support_goal_region.py
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1
request_rows: 4
candidate_target_rows: 21
focus_candidate_rows: 4
pair_rows: 17
observation_target_rows: 51
view_role_counts:
  common_pair_view: 17
  focus_own_view: 17
  rival_own_view: 17
viewpoint_source_counts:
  common_pair_navmesh: 17
  standoff_navmesh: 34
candidate_artifact_rows: 4
candidate_artifact_candidate_count: 21
skipped_rows: 0
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
unique_support_goal_region_plan_gate_passed: true
paper_claim_allowed: false
```

에이전트 추론: The planner converts the visible-object failure branch into motion-ready nonterminal evidence rows. This is a harness gate, not a detector or utility result. The next gate should verify frame export and projection visibility for these `51` observation targets before any detector/SAM2 substrate or terminal arbitration work.

#### Unique-Support Goal-Region Frame/Projection Smoke

사실: The unique-support goal-region frame/projection smoke is Docker-verified.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_goal_region_frame_projection.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_frame_projection_v1.verify.json
source_plan_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_frames_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_projection_v1
frame_rows_requested: 51
frame_rows_exported: 51
rendered_heading_count: 204
nonblank_output_rows: 51
nonblank_kept_heading_count: 204
removed_blank_heading_count: 0
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: true
projection_rows: 51
projection_anchor_visible_rows: 51
projection_anchor_visible_rate: 1.0
missing_candidate_rows: 0
gt_action_rows: 0
candidate_selection_source_counts:
  explicit_candidate_ids: 51
frame_revision_metadata_rows: 51
projection_anchor_smoke_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This closes the detector-free rendering/projection substrate for the first branch-specific goal-region observation. It still does not prove goal validity or navigation utility. The next gate is detector/SAM2 substrate on the same non-GT frame set, followed by post-detector evidence analysis only if the substrate gate passes.

#### Unique-Support Goal-Region Detector/SAM2 Substrate

사실: The unique-support goal-region detector/SAM2 substrate is Docker-verified.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1.verify.json
source_plan_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_frames_v1
detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1
log: runtime/logs/unique-support-goal-region-detector-substrate-20260531-174311.log
detector_rows: 51
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.6470588235294118
rows_with_candidate_association: 33
associated_candidate_heading_count: 87
association_rows: 204
detector_box_rows: 467
detector_mask_rows: 467
projected_pixel_inside_mask_count: 140
projection_anchor_selected_offset_counts:
  "0.0": 58
  "0.4": 2
  "0.8": 4
  "1.2": 7
  "1.6": 3
  "2.0": 41
  "2.4": 89
gt_action_rows: 0
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This verifies that the first branch-specific goal-region evidence path has usable detector/SAM2 associations under the fixed substrate gate. It does not prove `ObjectNav` goal validity, because detector support can still favor a visible wrong object. The next gate should aggregate focus/rival/common-view detector evidence into a nonterminal goal-region evidence analyzer before any terminal arbitration.

#### Unique-Support Goal-Region Evidence Analyzer Contract

사실: The post-detector evidence analyzer contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.verify.json
implementation_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_unique_support_goal_region_evidence.py
source_detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1
expected_view_evidence_rows: 51
expected_pair_evidence_rows: 17
expected_request_evidence_rows: 4
required_roles_per_pair:
  focus_own_view
  rival_own_view
  common_pair_view
source_associated_rows_by_role:
  focus_own_view: 17
  rival_own_view: 10
  common_pair_view: 6
source_associated_heading_count_by_role:
  focus_own_view: 62
  rival_own_view: 13
  common_pair_view: 12
pairs_by_request:
  rival_identity:3: 3
  rival_identity:5: 4
  rival_identity:7: 5
  rival_identity:22: 5
blocked_actions:
  direct_commit_focus_candidate
  commit_by_detector_box_presence
  commit_by_sam2_mask_presence
  commit_by_candidate_association_count
  commit_by_focus_own_support_only
  threshold_tuning_on_evaluation_labels
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This contract makes the next analyzer a nonterminal evidence aggregator. The useful question is not whether detector support exists, because focus own-view support exists for all `17` pairs. The useful question is whether focus support, rival support, and common-view focus support expose goal-region ambiguity in a way that can force the next method component. The common view currently scores the focus candidate only, so the analyzer must report that limitation rather than treating common-view support as proof of goal validity.

#### Unique-Support Goal-Region Evidence Analyzer

사실: The unique-support goal-region post-detector evidence analyzer is Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_unique_support_goal_region_evidence.py
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1
view_evidence_rows: 51
pair_evidence_rows: 17
request_evidence_rows: 4
role_counts:
  focus_own_view: 17
  rival_own_view: 17
  common_pair_view: 17
associated_rows_by_role:
  focus_own_view: 17
  rival_own_view: 10
  common_pair_view: 6
goal_region_pair_status_counts:
  contrastive_goal_region_pair: 7
  ambiguous_goal_region_pair: 10
request_nonterminal_action_counts:
  request_additional_rival_region_evidence: 4
all_pairs_have_three_roles: true
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
unique_support_goal_region_evidence_gate_passed: true
```

에이전트 추론: This analyzer closes the nonterminal evidence aggregation gate, not the terminal utility gate. The result is useful because it shows that focus own-view support is saturated (`17/17`) while rival own-view support remains present in `10/17` pairs. Therefore "unique visible support" is still not enough for `ObjectNav` goal validity. The next step is to inspect the ambiguous pair rows and define what additional rival-region evidence would be needed before any terminal arbitration contract.

#### Unique-Support Goal-Region Evidence Inspection

사실: The unique-support goal-region evidence inspection is Docker-verified.

```text
script: runtime/h001_runtime/inspect_expanded_retrieval_goal_validity_unique_support_goal_region_evidence.py
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_inspection_v1.verify.json
source_evidence_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_inspection_v1
pair_inspection_rows: 17
request_inspection_rows: 4
pair_blocker_counts:
  rival_own_view_supported: 10
  contrastive_without_common_focus_support: 5
  contrastive_but_request_level_ambiguity_check_required: 2
request_recommendation_counts:
  freeze_second_pass_rival_region_evidence_contract: 4
terminal_contract_allowed: false
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
uses_gt_for_analysis: false
inspection_gate_passed: true
paper_claim_allowed: false
```

에이전트 추론: Terminal arbitration is not justified. Every request still has at least one rival-own-view-supported pair, so a direct "contrastive pair exists" rule would ignore unresolved repeated-object ambiguity. The next contract should target only the ambiguous rival candidates and collect second-pass rival-region evidence, preferably with a common-view or cross-region observation that can test whether rival support is independent object evidence or viewpoint leakage.

#### Second-Pass Rival-Region Evidence Contract

사실: The second-pass rival-region evidence contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1.verify.json
implementation_target: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_unique_support_rival_region.py
source_inspection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_inspection_v1
target_request_rows: 4
target_ambiguous_pair_rows: 10
target_request_candidate_rows: 14
target_observation_rows: 30
required_second_pass_roles_per_pair:
  rival_from_common_pair_view
  rival_from_focus_own_view
  focus_from_rival_own_view
target_query_counts:
  bed: 5
  sofa: 5
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This contract converts the inspection blocker into the next active evidence step. The method question is now whether rival support is independent evidence for a competing goal region or an artifact of viewpoint leakage / repeated-object visibility. The contract deliberately does not authorize terminal arbitration from existing contrastive rows.

#### Second-Pass Rival-Region Planner Smoke

사실: The second-pass rival-region planner is implemented and Docker-verified.

```text
script: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_unique_support_rival_region.py
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_v1
docker_image: research3/habitat-h001:20260508-calib-artifacts
request_rows: 4
pair_rows: 10
request_candidate_rows: 14
observation_plan_rows: 30
skipped_rows: 0
candidate_artifact_rows: 4
candidate_artifact_candidate_count: 14
second_pass_view_role_counts:
  rival_from_common_pair_view: 10
  rival_from_focus_own_view: 10
  focus_from_rival_own_view: 10
source_view_role_counts:
  common_pair_view: 10
  focus_own_view: 10
  rival_own_view: 10
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
unique_support_rival_region_plan_gate_passed: true
paper_claim_allowed: false
```

에이전트 추론: The planner gate confirms that the inspection blocker can be turned into a concrete active evidence plan without label leakage. It still only authorizes the next substrate step, which is frame/projection smoke for swapped candidate-view rows.

#### Second-Pass Rival-Region Frame/Projection Smoke

사실: The second-pass rival-region frame/projection smoke is Docker-verified.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_frame_projection.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_frame_projection_v1.verify.json
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_frames_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_projection_v1
docker_image: research3/habitat-h001:20260508-calib-artifacts
rows_requested: 30
rows_exported: 30
rendered_heading_count: 120
nonblank_rows: 30
kept_heading_count: 120
removed_blank_heading_count: 0
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: true
projection_anchor_visible_rows: 30
projection_anchor_visible_rate: 1.0
missing_candidate_rows: 0
gt_action_rows: 0
explicit_candidate_ids: 30
source_decision_id_rows: 30
source_viewpoint_id_rows: 30
second_pass_view_role_rows: 30
viewpoint_reused_from_first_pass_rows: 30
projection_anchor_smoke_passed: true
paper_claim_allowed: false
```

에이전트 추론: This closes the geometry/rendering substrate for swapped rival-region evidence. The next evidence step is detector/SAM2 substrate on these frames; terminal goal-validity utility remains blocked.

#### Second-Pass Rival-Region Detector/SAM2 Substrate

사실: The second-pass rival-region detector/SAM2 substrate job completed, but the fixed substrate gate failed on candidate association.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1
diagnostic: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1/rival_region_detector_substrate_diagnostic.json
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
frame_rows: 30
detector_rows: 30
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.2667
rows_with_candidate_association: 8
associated_candidate_heading_count: 18
projected_pixel_inside_mask_count: 82
association_depth_status_counts:
  consistent: 18
  depth_mismatch: 77
  out_of_fov: 15
  unavailable: 10
by_query:
  bed: 1 / 15 associated rows
  sofa: 7 / 15 associated rows
gt_action_rows: 0
passes_detector_substrate_gate: false
paper_claim_allowed: false
```

에이전트 추론: Detector and mask availability are not the blocker; swapped rival-region candidate association is the blocker. Post-detector evidence analysis, terminal arbitration, and threshold tuning remain blocked. The next step should freeze an association-failure or association-repair contract that explains whether this is viewpoint geometry, depth association, source-map candidate position, or category-specific substrate weakness before any rerun.

#### Second-Pass Rival-Region Association Repair Contract

사실: The association-failure/repair contract is frozen before rerun or post-detector evidence analysis.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1.verify.json
source_failed_detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1
implementation_target: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_unique_support_rival_region_association.py
selected_next_contract: association_failure_and_repair_diagnostic_v1
source_candidate_association_rate: 0.2667
required_global_candidate_association_rate_minimum: 0.4
required_minimum_query_candidate_association_rate_minimum: 0.25
required_minimum_second_pass_role_candidate_association_rate_minimum: 0.3
allowed_diagnostic_variants:
  mask_depth_1_25_v1
  mask_depth_1_5_v1
  mask_depth_2_0_v1
  mask_only_upper_bound_v1
  box_only_upper_bound_v1
blocked:
  query-specific thresholds
  role-specific thresholds
  label-tuned thresholds
  detector threshold tuning
  terminal commit
  post-detector evidence analyzer before repair gate
  first_eval rerun
  policy-scale comparison
paper_claim_allowed: false
```

에이전트 추론: This contract keeps the repair paper-defensible: it turns the negative substrate result into a fixed failure diagnostic with global/query/role gates. If the diagnostic cannot pass without category- or role-specific tuning, the result should remain a substrate limitation rather than a method claim.

#### Second-Pass Rival-Region Association Repair Diagnostic

사실: The fixed non-GT association repair diagnostic is implemented and Docker-verified.

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_unique_support_rival_region_association.py
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_diagnostic_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1
diagnostic_rows: 180
source_frame_rows: 30
source_association_rows: 120
selected_repair_variant: mask_depth_1_25_v1
selected_rule: projected pixel inside SAM2 mask and depth_error_m <= 1.25
candidate_association_rate: 15 / 30 = 0.5
minimum_query_candidate_association_rate: 0.2667
minimum_second_pass_role_candidate_association_rate: 0.3
associated_heading_count: 26
action_forbidden_key_count: 0
diagnostic_gate_passed: true
repair_gate_passed: true
rerun_allowed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The repair gate is now passed for the most conservative predeclared promotable variant. This unlocks only a repaired detector/SAM2 substrate rerun using `mask_depth_1_25_v1`; it does not unlock post-detector evidence analysis, terminal utility validation, `first_eval` rerun, policy-scale comparison, or paper claims.

#### Second-Pass Rival-Region Repaired Detector Substrate

사실: The repaired detector/SAM2 substrate rerun with `mask_depth_1_25_v1` completed, but the fixed substrate gate still fails.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_v1
tmux_session: h001-unique-support-rival-repair-20260531-234903
association_depth_tolerance_m: 1.25
detector_rows: 30
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 10 / 30 = 0.3333
associated_candidate_heading_count: 23
by_query:
  bed: 1 / 15 associated rows
  sofa: 9 / 15 associated rows
by_second_pass_view_role:
  focus_from_rival_own_view: 3 / 10 associated rows
  rival_from_common_pair_view: 4 / 10 associated rows
  rival_from_focus_own_view: 3 / 10 associated rows
gt_action_rows: 0
passes_detector_substrate_gate: false
paper_claim_allowed: false
```

에이전트 추론: This invalidates the previous offline diagnostic as a rerun gate for `mask_depth_1_25_v1`. The likely mismatch is association semantics: the offline diagnostic used `depth_error_m`, while the detector runtime uses `depth_agreement_m` between candidate projection depth and selected SAM2 mask depth. A same-output runtime-depth sweep suggests `mask_depth_2_0_v1` could clear the global/query/role association gate, but that must be frozen as a runtime-semantics repair before another rerun. Post-detector evidence analysis and terminal utility remain blocked.

#### Runtime Association-Semantics Diagnostic

사실: The runtime association-semantics diagnostic is frozen and Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association_semantics_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association_semantics_v1.verify.json
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association_semantics_v1
source_repair_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_v1
runtime_depth_field: depth_agreement_m
diagnostic_rows: 180
selected_runtime_repair_variant: mask_depth_2_0_v1
candidate_association_rate: 16 / 30 = 0.5333
minimum_query_candidate_association_rate: 0.3333
minimum_second_pass_role_candidate_association_rate: 0.5
associated_heading_count: 35
action_forbidden_key_count: 0
diagnostic_gate_passed: true
runtime_repair_gate_passed: true
rerun_allowed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This diagnostic makes the next rerun defensible because it uses the same association semantics as the detector runtime rather than the rejected `depth_error_m` proxy. It only unlocks a detector/SAM2 substrate rerun with `association_depth_tolerance_m=2.0`; it does not unlock post-detector evidence analysis, terminal utility validation, `first_eval` rerun, policy-scale comparison, or paper claims.

#### Runtime Depth2 Detector/SAM2 Rerun Result

사실: The depth2 detector/SAM2 substrate rerun completed and passed the fixed substrate gate.

```text
session: h001-unique-support-rival-repair-depth2-20260601-001356
working_directory: /home/yoohyun/research3
command: TS=20260601-001356 bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_depth2.sh
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_depth2.sh
association_repair_variant: mask_depth_2_0_v1
association_depth_tolerance_m: 2.0
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_depth2_v1
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_repair_depth2_v1.verify.json
log: runtime/logs/unique-support-rival-region-detector-substrate-repair-depth2-20260601-001356.log
detector_rows: 30
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 16 / 30 = 0.5333
associated_candidate_heading_count: 35
query_association: bed 5 / 15, sofa 11 / 15
role_association:
  rival_from_common_pair_view: 6 / 10
  rival_from_focus_own_view: 5 / 10
  focus_from_rival_own_view: 5 / 10
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The runtime-semantics repair survives the actual detector/SAM2 rerun. This only unlocks post-detector evidence analysis; it does not unlock terminal utility validation, `first_eval` rerun, policy-scale comparison, or paper claims.

#### Second-Pass Rival-Region Evidence Analyzer

사실: The post-detector evidence analyzer is frozen and Docker-run as nonterminal evidence aggregation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_evidence_v1.verify.json
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_unique_support_rival_region_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_evidence_v1
view_evidence_rows: 30
pair_evidence_rows: 10
request_evidence_rows: 4
pair_status:
  cross_region_overlap_pair: 7
  shared_common_view_rival_support_pair: 2
  second_pass_rival_region_contrastive_pair: 1
request_actions:
  defer_goal_region_unresolved_cross_region_overlap: 3
  request_goal_region_arbitration_after_shared_common_evidence: 1
terminal_commit_rows: 0
action_forbidden_key_count: 0
unique_support_rival_region_evidence_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The second-pass evidence mainly shows unresolved cross-region overlap rather than a safe terminal goal-validity signal. A terminal arbitration contract is still blocked. The next workflow step is to inspect the cross-region overlap cases and decide whether they imply an additional observation branch, a stricter evidence definition, or a negative finding for this branch.

#### Cross-Region Overlap Inspection

사실: The cross-region overlap inspection is Docker-run before any terminal arbitration contract.

```text
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_inspection_v1.verify.json
script: runtime/h001_runtime/inspect_expanded_retrieval_goal_validity_unique_support_rival_region_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_inspection_v1
pair_rows: 10
request_rows: 4
pair_blockers:
  bidirectional_cross_region_overlap: 3
  rival_visible_from_focus_region: 2
  focus_visible_from_rival_region: 2
  shared_common_view_rival_support: 2
  pure_contrastive_no_second_pass_support: 1
request_blockers:
  contains_cross_region_overlap_pairs: 3
  contains_shared_common_view_rival_support: 1
request_recommendations:
  freeze_cross_region_overlap_failure_branch: 3
  inspect_shared_common_view_support_before_terminal_arbitration: 1
terminal_contract_allowed: false
terminal_commit_rows: 0
action_forbidden_key_count: 0
inspection_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: No request is clean contrastive-only. The dominant failure is not detector coverage but repeated-object region overlap after active re-observation. This inspection led to the cross-region overlap failure branch freeze below; terminal arbitration remains blocked, and the one non-cross-overlap request still needs shared common-view support inspection.

#### Cross-Region Overlap Failure Branch Freeze

사실: The cross-region overlap failure branch is frozen and Docker-run.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1.verify.json
script: runtime/h001_runtime/route_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1
pair_branch_rows: 10
request_branch_rows: 4
pair_branches:
  cross_region_overlap_failure_branch: 7
  shared_common_view_support_pending_branch: 2
  clean_contrastive_pending_branch: 1
request_branches:
  cross_region_overlap_failure_branch: 3
  shared_common_view_support_pending_branch: 1
request_actions:
  route_to_cross_region_overlap_failure_branch: 3
  route_to_shared_common_view_support_inspection: 1
cross_region_request_ids:
  rival_identity:3
  rival_identity:5
  rival_identity:22
shared_common_pending_request_ids:
  rival_identity:7
clean_contrastive_pending_request_rows: 0
terminal_contract_allowed: false
terminal_commit_rows: 0
action_forbidden_key_count: 0
cross_region_overlap_branch_freeze_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: Cross-region overlap is now a frozen nonterminal failure branch, not a terminal utility rule. This narrows the next check to the single remaining non-cross-overlap request with shared common-view rival support. A terminal goal-region arbitration contract, `first_eval` rerun, policy-scale comparison, and paper claims remain blocked.

#### Shared Common-View Support Inspection

사실: The remaining shared common-view support case is inspected before any terminal arbitration contract.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1.verify.json
script: runtime/h001_runtime/inspect_expanded_retrieval_goal_validity_unique_support_shared_common_view.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1
request_inspection_rows: 1
pair_inspection_rows: 2
request_ids:
  rival_identity:7
pair_status:
  shared_common_view_rival_support_blocks_terminal: 1
  clean_contrastive_pair_contaminated_by_request_level_shared_common_support: 1
request_recommendations:
  freeze_shared_common_view_support_failure_branch: 1
terminal_contract_allowed: false
terminal_commit_rows: 0
action_forbidden_key_count: 0
shared_common_view_inspection_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The remaining non-cross-overlap request is still not a clean terminal arbitration case. The clean contrastive pair is request-level contaminated by shared common-view rival support, so `commit_if_any_clean_contrastive_pair` and `commit_if_no_cross_region_overlap` are rejected as terminal rules. This led to the shared-common-view support failure branch freeze below, not terminal utility.

#### Shared Common-View Support Failure Branch Freeze

사실: The shared common-view support failure branch is frozen and Docker-run.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_branch_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_branch_v1.verify.json
script: runtime/h001_runtime/route_expanded_retrieval_goal_validity_unique_support_shared_common_view_branch.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_branch_v1
request_branch_rows: 1
pair_branch_rows: 2
request_branch:
  shared_common_view_support_failure_branch: 1
pair_branches:
  shared_common_view_support_failure_branch: 1
  contaminated_clean_contrastive_pair_branch: 1
request_actions:
  route_to_shared_common_view_support_failure_branch: 1
terminal_contract_allowed: false
terminal_commit_rows: 0
action_forbidden_key_count: 0
shared_common_view_branch_freeze_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This closes the "clean contrastive pair can be used if there is no cross-region overlap" path. The request-level shared common-view support still blocks terminal arbitration.

#### Unique-Support Branch Closure

사실: The unique-support branch closure is frozen and Docker-run.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1.verify.json
script: runtime/h001_runtime/close_expanded_retrieval_goal_validity_unique_support_branch.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1
closed_branch: unique_support_visibility_not_goal_validity
closure_status: terminal_blocked
closure_request_rows: 4
closure_mechanisms:
  cross_region_overlap_failure_branch: 3
  shared_common_view_support_failure_branch: 1
unclosed_unique_support_request_rows: 0
selected_next_branch: partial_relation_depth_true_goal
selected_next_action: request_additional_relation_depth_evidence
selected_next_request_rows: 6
selected_next_candidate_rows: 12
terminal_commit_rows: 0
action_forbidden_key_count: 0
unique_support_branch_closure_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The unique-support visibility branch is closed as terminal-blocked, not promoted. The next branch-specific evidence route is `partial_relation_depth_true_goal`, because it tests whether additional relation-depth observation can recover true-goal candidates that the fixed arbitration rule blocked as partial.

#### Partial Relation-Depth True-Goal Observation Contract

사실: The partial relation-depth true-goal observation contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1.verify.json
target_branch: partial_relation_depth_true_goal
target_action: request_additional_relation_depth_evidence
request_rows: 6
target_candidate_rows: 12
failed_relation_depth_evidence_rows: 22
partial_relation_depth_rows: 19
unresolved_relation_depth_rows: 3
resolved_relation_depth_rows_for_same_targets: 14
context_anchor_rows: 48
failed_directions:
  orthogonal_relation_axis: 8
  relation_anchor_to_target: 11
  target_to_relation_anchor: 3
minimum_plan_rows: 48
terminal_commit_rows: 0
action_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This contract treats partial relation-depth as observation incompleteness, not candidate invalidity. The next implementation must materialize request, target-candidate, failed-evidence, and context-anchor rows before any label join, then run a Docker planner smoke. Terminal utility, `first_eval` rerun, and paper claims remain blocked.

#### Partial Relation-Depth Input and Planner Smoke

사실: The partial relation-depth true-goal input materializer and planner smoke are Docker-verified.

```text
input_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_partial_relation_depth_inputs.py
planner: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_partial_relation_depth.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1
input_request_rows: 6
input_target_candidate_rows: 12
input_failed_relation_depth_evidence_rows: 22
input_context_anchor_rows: 48
partial_relation_depth_rows: 19
unresolved_relation_depth_rows: 3
plan_rows: 48
plan_rows_per_target_candidate: 4
skipped_rows: 0
failed_evidence_rows_mapped: 22
failed_evidence_rows_unmapped: 0
candidate_artifact_rows: 4
candidate_artifact_candidate_count: 20
action_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
input_gate: true
plan_gate: true
paper_claim_allowed: false
```

에이전트 추론: The branch now has a label-free observation plan for partial relation-depth completion. This is still nonterminal substrate evidence; it supports moving to frame/projection and detector/SAM2 evidence, not terminal `ObjectNav` utility.

#### Partial Relation-Depth Frame/Projection Smoke

사실: The partial relation-depth frame/projection smoke is Docker-verified.

```text
job: runtime/jobs/expanded_retrieval_goal_validity_partial_relation_depth_frame_projection.sh
frames: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_frames_v1
projection: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_projection_v1
frame_rows: 48
rendered_heading_count: 192
nonblank_rows: 48
removed_blank_heading_count: 0
projection_rows: 48
projection_expected_rows: 48
projection_visible_rows: 48
projection_visible_rate: 1.0
missing_candidate_rows: 0
gt_action_rows: 0
projection_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The 48 relation-depth completion views are renderable and have visible projection anchors. The next evidence gate is detector/SAM2 substrate; terminal utility remains blocked.

#### Partial Relation-Depth Detector/SAM2 Substrate

사실: The partial relation-depth detector/SAM2 substrate is Docker/GPU-verified.

```text
job: runtime/jobs/expanded_retrieval_goal_validity_partial_relation_depth_detector_substrate.sh
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_detector_substrate_v1
detector_rows: 48
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.8125
rows_with_candidate_association: 39
associated_candidate_heading_count: 97
association_rows: 192
detector_box_rows: 230
detector_mask_rows: 230
projected_pixel_inside_mask_count: 133
selected_candidate_source: explicit_candidate_ids 48
projection_anchor_policy: projection_anchor_height_sweep_v1 48
uses_gt_for_action: false
detector_substrate_gate: true
paper_claim_allowed: false
```

에이전트 추론: Detector/SAM2 substrate coverage is strong enough to define a post-detector evidence analyzer. That analyzer must remain label-free until evidence rows are written and must not promote a terminal commit from detector visibility alone.

#### Partial Relation-Depth Post-Detector Evidence Contract

사실: The post-detector evidence analyzer contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1.verify.json
analyzer: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_partial_relation_depth_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1
source_gates: input true, plan true, projection true, detector true
expected_request_rows: 6
expected_target_candidate_rows: 12
expected_failed_relation_depth_evidence_rows: 22
expected_plan_rows: 48
expected_detector_rows: 48
expected_detector_association_rows: 192
minimum_candidate_association_rate: 0.80
minimum_associated_candidate_heading_count: 90
minimum_projected_pixel_inside_mask_count: 120
action_forbidden_key_count_maximum: 0
terminal_commit_rows_maximum: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The contract freezes a nonterminal analyzer: it can mark prior failed relation-depth evidence as resolved, partial, or unresolved, but cannot select a terminal goal. The next implementation should write evidence rows before any evaluation-only label join.

#### Partial Relation-Depth Post-Detector Evidence Analyzer

사실: The post-detector evidence analyzer is implemented and Docker-verified.

```text
analyzer: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_partial_relation_depth_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1
evidence_rows: 48
failed_relation_depth_evidence_rows: 22
failed_evidence_summary_rows: 22
request_summary_rows: 6
unresolved_or_partial_rows: 15
completion_status_counts:
  relation_depth_completion_resolved: 7
  relation_depth_completion_partial: 15
candidate_association_rate: 0.8125
associated_candidate_heading_count: 97
projected_pixel_inside_mask_count: 133
action_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
partial_relation_depth_detector_evidence_gate_passed: true
paper_claim_allowed: false
recommended_next_action: inspect_remaining_partial_relation_depth_rows
terminal_policy_allowed: false
terminal_utility_validation_allowed: false
```

에이전트 추론: Relation-depth completion is partly successful but not terminal. The analyzer resolves `7` prior failed rows and leaves `15` partial, which is exactly the reviewer-facing mechanism signal to inspect next: the method must explain why residual rows stay partial before defining any commit/reject rule.

#### Remaining Partial Relation-Depth Row Inspection

사실: The remaining partial rows were inspected from `partial_relation_depth_unresolved_rows.jsonl`.

```text
unresolved_or_partial_rows: 15
unresolved_reason_counts:
  no_candidate_associated_depth_improvement: 15
query_counts:
  plant: 12
  sofa: 2
  bed: 1
direction_counts:
  relation_anchor_to_target: 11
  orthogonal_relation_axis: 3
  target_to_relation_anchor: 1
rows_with_inside_mask: 15
rows_with_completion_association: 7
rows_with_zero_completion_association: 8
rows_with_completion_depth_consistent: 10
dominant_scene_query: bxsVRursffK/plant 12
dominant_requests:
  rival_identity:25: 4
  rival_identity:27: 4
  rival_identity:29: 4
```

에이전트 추론: The residual blocker is not blank rendering or missing projection. All rows reach the mask, but relation-depth evidence fails to improve candidate-associated depth. This led to the frozen residual taxonomy below, which separates association-zero rows, association-positive-but-not-improved rows, and repeated `bxsVRursffK/plant` relation-anchor ambiguity before any terminal utility rule.

#### Residual Partial Relation-Depth Taxonomy

사실: The residual taxonomy is frozen and Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1.verify.json
analyzer: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1
taxonomy_rows: 15
request_taxonomy_rows: 6
residual_failure_class_counts:
  association_present_without_depth_improvement: 7
  depth_signal_not_candidate_associated: 3
  mask_projection_without_association_or_depth: 5
request_residual_status_counts:
  repeated_object_relation_anchor_ambiguity: 3
  association_geometry_underlink: 2
  association_present_but_depth_not_improved: 1
rows_with_inside_mask: 15
rows_with_zero_completion_association: 8
rows_with_completion_association: 7
rows_with_completion_depth_consistent: 10
dominant_scene_query: bxsVRursffK/plant
dominant_scene_query_rows: 12
action_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
uses_gt_for_analysis: false
partial_relation_depth_residual_taxonomy_gate_passed: true
paper_claim_allowed: false
```

에이전트 추론: Residual partial relation-depth is now separated into branchable mechanisms rather than a single vague uncertainty bucket. The branch-handling contract below freezes how `association_geometry_underlink`, `association_present_but_depth_not_improved`, and `repeated_object_relation_anchor_ambiguity` must be routed; terminal utility remains blocked until those branches yield a validated non-GT arbitration rule.

#### Residual Partial Relation-Depth Branch Handling

사실: The branch-handling contract is frozen and Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1.verify.json
router: runtime/h001_runtime/route_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling.py
source_taxonomy_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1
source_taxonomy_rows: 15
source_request_taxonomy_rows: 6
branch_rows: 15
request_branch_rows: 6
branch_mapping:
  association_geometry_underlink: route_to_association_geometry_repair_branch
  association_present_but_depth_not_improved: route_to_depth_stagnation_branch
  repeated_object_relation_anchor_ambiguity: route_to_repeated_object_relation_anchor_ambiguity_branch
branch_action_counts:
  route_to_repeated_object_relation_anchor_ambiguity_branch: 3
  route_to_association_geometry_repair_branch: 2
  route_to_depth_stagnation_branch: 1
unmapped_request_rows: 0
action_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
partial_relation_depth_branch_handling_gate_passed: true
required_future_outputs:
  partial_relation_depth_branch_rows.jsonl
  partial_relation_depth_branch_request_rows.jsonl
  partial_relation_depth_branch_handling_summary.json
terminal_commits_allowed: false
threshold_tuning_allowed: false
first_eval_rerun_allowed: false
policy_scale_comparison_allowed: false
paper_claim_allowed: false
```

에이전트 추론: The router now verifies that every residual request maps to exactly one nonterminal branch and preserves the no-GT action boundary. The next branch-specific contract should start from `route_to_association_geometry_repair_branch` because those rows are substrate-level association underlinks; terminal utility remains blocked.

#### Association-Geometry Repair Branch Contract

사실: The association-geometry repair branch contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1
target_branch_action: route_to_association_geometry_repair_branch
target_request_rows: 2
target_branch_rows: 2
request_residual_status:
  association_geometry_underlink: 2
target_queries:
  sofa: 1
  bed: 1
target_candidate_ids:
  vlmaps:export:sofa:spatial_nms:2
  vlmaps:export:bed:spatial_nms:9
residual_failure_class_counts:
  mask_projection_without_association_or_depth: 2
rows_with_inside_mask: 2
rows_with_zero_completion_association: 2
rows_with_completion_association: 0
rows_with_completion_depth_consistent: 0
allowed_repair_checks:
  projection_anchor_replay
  mask_depth_agreement_recheck
  candidate_geometry_sanity_check
terminal_commit_rows: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This branch tests whether the underlink is a repairable geometry/association artifact, not whether the target is an `ObjectNav` goal. The future diagnostic may recover association evidence or request re-observation, but it must not commit or reject candidates.

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

### Current Proxy Comparison Result

사실:

- Date checked: 2026-06-04
- Implementation: `runtime/h001_runtime/compare_semantic_slam_proxy_policies.py`
- Contract / verify: `manifests/h001_semantic_slam_proxy_comparison_v1.json`, `manifests/h001_semantic_slam_proxy_comparison_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_proxy_comparison_v1`
- Rows: comparison/policy summary `200/4`
- Request groups: `50`
- Canonical/loop proxy ready rates: `0.92/0.72`
- Policy utility means: `NoReobserveReference 0.0`, `SemanticOnly 0.6092`, `SLAMOnly 0.3871`, `SemanticSLAM 0.4981`
- Rank-1 rows/rates: `SemanticOnly 36/0.72`, `SLAMOnly 14/0.28`, `SemanticSLAM 0/0.0`
- Action forbidden key count: `0`
- Terminal/candidate commit/rejection rows: `0/0/0`
- `uses_gt_for_action`: `false`
- Proxy comparison gate: `true`
- Step 4-5 promotion: `false`
- Paper claim allowed: `false`

에이전트 추론:

The current proxy comparison is a plumbing-positive but complementarity-negative diagnostic. It shows the same request groups can support separated semantic-only, SLAM-only, and combined proxy scoring without GT action leakage. It does not yet show that `SemanticSLAM` is better than either component policy. Before promotion, evaluate whether the failure comes from fixed utility weights, a too-coarse SLAM proxy, missing task-behavior coupling, or a request pool that lacks semantic-SLAM complementarity cases.

논문 주장:

No Step 4-5 paper claim is allowed from this result. A future positive signal must show map/pose improvement over `SemanticOnly` while preserving task behavior and not being fully explained by `SLAMOnly`.

### Current Proxy Output Evaluation

사실:

- Date checked: 2026-06-04
- Implementation / verify: `runtime/h001_runtime/evaluate_semantic_slam_proxy_comparison_output.py`, `manifests/h001_semantic_slam_proxy_comparison_output_evaluation_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_proxy_comparison_output_evaluation_v1`
- Group evaluation rows: `50`
- Component winners: `SemanticOnly 36/0.72`, `SLAMOnly 14/0.28`
- Dominance class: `semantic_slam_midpoint_strictly_dominated_by_best_component 50/1.0`
- `SemanticSLAM` midpoint identity max absolute error: `1.11e-16`
- Best-component margin over `SemanticSLAM`: min/mean/max `0.0159/0.1536/0.3995`
- Output evaluation gate: `true`
- Step 4-5 promotion: `false`
- Paper claim allowed: `false`

에이전트 추론:

The current `SemanticSLAM` proxy is structurally dominated because it is the midpoint of `SemanticOnly` and `SLAMOnly` under the score-only proxy ranking. This means simple fixed-weight averaging is not an acceptable Step 4-5 utility design. The next contract should require a non-dominated design and explicitly reject midpoint, linear interpolation without an interaction term, and post-hoc component-max selection as paper-facing `SemanticSLAM` evidence.

사용자 판단 필요:

No immediate user decision is required. The default next step is to freeze a non-dominated `SemanticSLAM` proxy redesign contract before any new implementation.

### Non-Dominated Proxy Redesign Contract

사실:

- Date checked: 2026-06-04
- Contract / verify: `manifests/h001_semantic_slam_non_dominated_proxy_redesign_v1.json`, `manifests/h001_semantic_slam_non_dominated_proxy_redesign_v1.verify.json`
- Policies: `NoReobserveReference`, `SemanticOnly`, `SLAMOnly`, `SemanticSLAMInteraction`
- Expected rows: `200`
- Prior failure recorded: midpoint dominance rows/rate `50/1.0`
- Forbidden patterns: midpoint or linear interpolation only, component-max shortcut, constant bonus scale trick, label-tuned weight search
- Primary interaction terms: `semantic_pressure`, `map_pose_pressure`, `interaction = semantic_pressure * map_pose_pressure`
- Required future diagnostics: `non_dominated_by_component`, `midpoint_identity_error`, `component_max_shortcut_used`, `component_dominance_margin`
- Minimum non-dominated interaction rows/rate: `10/0.2`
- Maximum midpoint identity rows: `0`
- Maximum component-max shortcut rows: `0`
- Step 4-5 promotion: `false`
- Paper claim allowed: `false`

에이전트 추론:

This contract is the right next step because it turns the failed midpoint result into a falsifiable design constraint. A valid redesigned proxy must show that the combined semantic-SLAM utility is not just selecting or averaging components. Passing this proxy redesign gate would only justify a later task/map validation; it would not prove navigation or SLAM benefit.

논문 주장:

No paper-facing `SemanticSLAM` contribution is allowed until a later implementation passes this non-dominated proxy gate and then links the signal to map/pose and task behavior metrics.

### Non-Dominated Proxy Implementation Result

사실:

- Date checked: 2026-06-04
- Implementation / verify: `runtime/h001_runtime/compare_semantic_slam_non_dominated_proxy.py`, `manifests/h001_semantic_slam_non_dominated_proxy_redesign_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_non_dominated_proxy_redesign_v1`
- Rows: comparison/policy summary/diagnostic `200/4/50`
- Policy rank-1 rows/rates: `SemanticSLAMInteraction 42/0.84`, `SLAMOnly 8/0.16`, `SemanticOnly 0/0.0`, `NoReobserveReference 0/0.0`
- Non-dominated interaction rows/rate: `42/0.84`
- Interaction-positive rows: `50`
- Midpoint identity rows: `0`
- Component-max shortcut rows: `0`
- Component reference rank-1 rows: `8`
- Action forbidden key count: `0`
- Terminal/candidate commit/rejection rows: `0/0/0`
- `uses_gt_for_action`: `false`
- Non-dominated proxy redesign gate: `true`
- Step 4-5 promotion: `false`
- Paper claim allowed: `false`

에이전트 추론:

This implementation passes the structural redesign gate, so the previous midpoint failure is repaired at the proxy-score level. The remaining risk is the opposite failure mode: `SemanticSLAMInteraction` may be too dominant because it wins `42/50` rows and `SemanticOnly` wins `0`. The next output evaluation must decide whether the high interaction rank-1 rate reflects meaningful semantic-map/pose complementarity or a too-permissive semantic-first bonus.

논문 주장:

Passing this proxy gate does not establish Step 4-5 benefit. A paper-facing claim still requires task/map outcome validation and failure analysis.

## Current Nonterminal Branch Gate

### 사실

- Date checked: 2026-06-01
- Association-geometry repair diagnostic output: `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1`
- Repair/request rows: `2/2`
- Exact failed completion association/depth-consistent counts: `0/0`
- Exact failed completion inside-mask count: `5`
- Same-requested / other-requested associated heading counts: `2/14`
- Diagnostic actions: `request_anchor_selection_repair_for_association_geometry 1`, `request_direction_specific_reobservation_repair 1`
- Terminal commits: `0`
- `uses_gt_for_action`: `false`
- Gate: `association_geometry_repair_diagnostic_gate_passed true`
- Follow-up contract: `manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_followup_repair_v1.json`
- Frozen follow-up routes: `route_to_relation_anchor_selection_repair 1`, `route_to_direction_specific_reobservation_repair 1`
- Follow-up router output: `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_followup_repair_v1`
- Follow-up router gate: `association_geometry_followup_repair_gate_passed true`
- Follow-up rows/request rows: `2/2`
- Mapped/routed rows: `2/2`
- Candidate commit/rejection rows: `0/0`
- Relation-anchor selection repair contract: `manifests/h001_relation_anchor_selection_repair_v1.json`
- Relation-anchor target: `rival_identity:3`, `QaLdnwvtxbs`, `sofa`, `vlmaps:export:sofa:spatial_nms:2`
- Failed explicit anchor row: anchor `vlmaps:export:sofa:spatial_nms:1`, association/depth/inside-mask `0/0/4`
- Same-direction anchorless recovery row: context `vlmaps:export:sofa:spatial_nms:0`, association/depth/inside-mask `2/1/4`
- Relation-anchor probe output: `local_dataset/runs/h001_relation_anchor_selection_repair_v1`
- Relation-anchor probe gate: `relation_anchor_selection_repair_probe_gate_passed true`
- Probe rows/request rows: `2/1`
- Nonterminal probe action: `request_relation_anchor_selection_replay 2`
- Probe terminal commits and candidate commit/rejection rows: `0`, `0/0`

### 에이전트 추론

This gate does not relax the terminal utility contract. The direction-specific re-observation repair contract and Docker probe are now complete for the `rival_identity:5` `bed` branch.

### 사실

- Contract: `manifests/h001_direction_specific_reobservation_repair_v1.json`
- Verify: `manifests/h001_direction_specific_reobservation_repair_v1.verify.json`
- Target request: `rival_identity:5`
- Scene/query: `bCPU9suPUw9` / `bed`
- Target candidate: `vlmaps:export:bed:spatial_nms:9`
- Failed requested direction: `relation_anchor_to_target` falling back to `compass_315`
- Failed explicit/anchorless association/depth/inside-mask: `0/0/1`, `0/0/1`
- Recovered direction: `target_to_relation_anchor`
- Recovered explicit/anchorless association/depth/inside-mask: `4/4/4`, `4/4/4`
- Same-requested direction associated heading count: `0`
- Other-requested direction associated/depth/inside-mask counts: `8/8/8`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0/0`
- `uses_gt_for_action`: `false`
- `paper_claim_allowed`: `false`
- Probe output: `local_dataset/runs/h001_direction_specific_reobservation_repair_v1`
- Probe rows/request rows: `4/1`
- Nonterminal probe action: `request_direction_specific_reobservation_replay 4`
- Probe gate: `direction_specific_reobservation_repair_probe_gate_passed true`

### 에이전트 추론

The direction-specific probe is still an evidence-acquisition repair gate, not terminal utility, candidate rejection, `first_eval`, or policy-scale comparison. The repeated-object relation-anchor ambiguity branch is now Docker-verified, so the next residual mechanism target is depth-stagnation handling.

### 사실

- Repeated-object contract: `manifests/h001_repeated_object_relation_anchor_ambiguity_v1.json`
- Verify: `manifests/h001_repeated_object_relation_anchor_ambiguity_v1.verify.json`
- Source output: `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1`
- Target branch action: `route_to_repeated_object_relation_anchor_ambiguity_branch`
- Target scene/query: `bxsVRursffK` / `plant`
- Target request ids: `rival_identity:25`, `rival_identity:27`, `rival_identity:29`
- Target request/branch rows: `3/12`
- Candidate ids: `vlmaps:export:plant:spatial_nms:0`, `vlmaps:export:plant:spatial_nms:2`, `vlmaps:export:plant:spatial_nms:4`
- Residual failure classes: `association_present_without_depth_improvement 6`, `depth_signal_not_candidate_associated 3`, `mask_projection_without_association_or_depth 3`
- Direction counts: `relation_anchor_to_target 9`, `orthogonal_relation_axis 3`
- Completion association-positive/zero rows: `6/6`
- Completion depth-consistent rows: `9`
- Inside-mask rows: `12`
- Completion association/depth/inside-mask sums: `18/12/42`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0/0`
- `uses_gt_for_action`: `false`
- `paper_claim_allowed`: `false`
- Implementation: `runtime/h001_runtime/route_repeated_object_relation_anchor_ambiguity.py`
- Output: `local_dataset/runs/h001_repeated_object_relation_anchor_ambiguity_v1`
- Output branch/request rows: `12/3`
- Nonterminal branch action: `request_repeated_object_relation_anchor_ambiguity_audit 12`
- Output action forbidden keys: `0`
- Output terminal commits: `0`
- Output candidate commit/rejection rows: `0/0`
- Output branch gate: `repeated_object_relation_anchor_ambiguity_branch_gate_passed true`

### 에이전트 추론

This branch is now a Docker-verified repeated-instance and relation-anchor ambiguity audit. Positive association, depth consistency, or inside-mask evidence must not become a candidate commit shortcut because the same request pattern contains association-positive, association-zero, depth-signal-not-associated, and mask-only rows across repeated `plant` candidates. The depth-stagnation contract below closes the last residual branch design gate; terminal utility, candidate rejection, `first_eval`, policy-scale comparison, and paper claims remain blocked.

### 사실

- Depth-stagnation contract: `manifests/h001_depth_stagnation_branch_v1.json`
- Verify: `manifests/h001_depth_stagnation_branch_v1.verify.json`
- Source output: `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1`
- Target branch action: `route_to_depth_stagnation_branch`
- Target scene/query: `4ok3usBNeis` / `sofa`
- Target request id: `rival_identity:22`
- Target candidate id: `vlmaps:export:sofa:spatial_nms:2`
- Target request/branch rows: `1/1`
- Request residual status: `association_present_but_depth_not_improved`
- Residual failure class: `association_present_without_depth_improvement`
- Direction: `target_to_relation_anchor`
- Prior association/depth-consistent/depth-mismatch/inside-mask counts: `3/1/7/7`
- Completion association/depth-consistent/inside-mask counts: `3/1/4`
- Completion status: `relation_depth_completion_partial`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0/0`
- `uses_gt_for_action`: `false`
- `paper_claim_allowed`: `false`
- Next implementation target: `runtime/h001_runtime/route_depth_stagnation_branch.py`
- Expected output: `local_dataset/runs/h001_depth_stagnation_branch_v1`
- Implementation: `runtime/h001_runtime/route_depth_stagnation_branch.py`
- Output: `local_dataset/runs/h001_depth_stagnation_branch_v1`
- Output branch/request rows: `1/1`
- Nonterminal branch action: `request_depth_stagnation_audit 1`
- Depth/association delta: `0/0`
- Output action forbidden keys: `0`
- Output terminal commits: `0`
- Output candidate commit/rejection rows: `0/0`
- Output branch gate: `depth_stagnation_branch_gate_passed true`

### 에이전트 추론

Depth-stagnation is a different residual mechanism from association-geometry underlink and repeated-object relation-anchor ambiguity. Here, association and depth-consistent signals exist, but they do not improve over prior partial relation-depth evidence. The Docker-verified output preserves a nonterminal audit/action request and blocks `commit_by_candidate_association`, `commit_by_depth_consistency`, `reject_candidate_because_depth_did_not_improve`, threshold tuning, `first_eval`, policy-scale comparison, and paper claims.

## Residual Branch Synthesis Gate

### 사실

- Contract: `manifests/h001_residual_partial_relation_depth_branch_synthesis_v1.json`
- Verify: `manifests/h001_residual_partial_relation_depth_branch_synthesis_v1.verify.json`
- Implementation: `runtime/h001_runtime/synthesize_residual_partial_relation_depth_branches.py`
- Output: `local_dataset/runs/h001_residual_partial_relation_depth_branch_synthesis_v1`
- Synthesis gate: `residual_branch_synthesis_gate_passed true`
- Family rows: `3`
- Request/source-branch rows: `6/15`
- Family output rows: `association_geometry_underlink 8`, `repeated_object_relation_anchor_ambiguity 12`, `depth_stagnation 1`
- Family synthesis status: `nonterminal_audit_or_repair_only 3`
- Promotable terminal outcome rows: `0`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0/0`
- `uses_gt_for_action`: `false`
- `paper_claim_allowed`: `false`

### 에이전트 추론

Residual branch accounting is complete, but terminal utility remains blocked. A future terminal utility contract needs an explicit extra-evidence requirement for at least one branch outcome. It cannot be opened from branch gate success, positive association, depth consistency, inside-mask projection, or nonterminal repair/audit readiness alone.

## Residual Branch Promotion Requirement Gate

### 사실

- Contract: `manifests/h001_residual_branch_promotion_requirement_v1.json`
- Verify: `manifests/h001_residual_branch_promotion_requirement_v1.verify.json`
- Implementation: `runtime/h001_runtime/define_residual_branch_promotion_requirements.py`
- Output: `local_dataset/runs/h001_residual_branch_promotion_requirement_v1`
- Source synthesis gate: `true`
- Promotion requirement gate: `true`
- Requirement rows: `3`
- Source family / request / branch rows: `3 / 6 / 15`
- Status: `defined_not_satisfied 3`
- Branch priority: `repeated_object_relation_anchor_ambiguity`, `association_geometry_underlink`, `depth_stagnation`
- Top priority family: `repeated_object_relation_anchor_ambiguity`
- Promotable family rows: `0`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The promotion requirement gate converts the completed residual branch synthesis into a stricter paper-defense requirement, not into terminal utility. The highest-priority unsatisfied branch is `repeated_object_relation_anchor_ambiguity`: it needs relation-anchor candidate assignment to stay stable across at least two independent observation roles, one conflict-free candidate-specific support pattern while same-category rivals do not satisfy it, candidate-associated depth-consistent evidence, and no orthogonal relation-axis contradiction. The repeated-object relation-anchor consistency evidence contract below freezes that next nonterminal evaluation step. Terminal utility, candidate commit/rejection, `first_eval`, policy-scale comparison, and paper claims remain blocked.

## Repeated-Object Relation-Anchor Consistency Evidence Contract

### 사실

- Contract: `manifests/h001_repeated_object_relation_anchor_consistency_evidence_v1.json`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_evidence_v1.verify.json`
- Source promotion requirement: `local_dataset/runs/h001_residual_branch_promotion_requirement_v1`
- Source repeated-object branch: `local_dataset/runs/h001_repeated_object_relation_anchor_ambiguity_v1`
- Prior context anchors: `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/partial_relation_depth_context_anchor_rows.jsonl`
- Source gates: promotion requirement gate `true`, repeated-object branch gate `true`
- Target scene/query: `bxsVRursffK/plant`
- Target request/branch rows: `3 / 12`
- Target candidates: `vlmaps:export:plant:spatial_nms:0`, `vlmaps:export:plant:spatial_nms:2`, `vlmaps:export:plant:spatial_nms:4`
- Prior context anchor rows for the scene/query: `36`
- Prior context candidate ids: `spatial_nms:0`, `spatial_nms:2`, `spatial_nms:4`, `spatial_nms:7`, `spatial_nms:8`
- Minimum candidate-anchor pair rows: `18`
- Minimum observation target rows: `27`
- Required observation roles: `candidate_own_view`, `relation_anchor_context_view`, `orthogonal_axis_challenge_view`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract turns the dominant repeated-object residual branch into a concrete active evidence acquisition target. It does not allow terminal utility. The next implementation should materialize request, candidate, candidate-anchor pair, and observation target rows that can test stable relation-anchor assignment, conflict-free candidate-specific support, candidate-associated depth consistency, and orthogonal-axis contradiction without using labels. If those rows still show mixed support or contradiction, the branch remains nonterminal and should not move to candidate commit/rejection or `first_eval`.

## Repeated-Object Relation-Anchor Consistency Planner Gate

### 사실

- Implementation: `runtime/h001_runtime/plan_repeated_object_relation_anchor_consistency.py`
- Contract: `manifests/h001_repeated_object_relation_anchor_consistency_evidence_v1.json`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_evidence_v1.verify.json`
- Output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Planner gate: `repeated_object_relation_anchor_consistency_plan_gate_passed true`
- Source rows: branch/request/context-anchor/prior-plan `12/3/36/36`
- Output rows: request/candidate/pair/observation `3/9/27/27`
- Candidate artifact rows/candidates: `1/5`
- Skipped rows: `0`
- Minimum context candidates per request: `4`
- Minimum observation roles per candidate: `3`
- View roles: `candidate_own_view 9`, `relation_anchor_context_view 9`, `orthogonal_axis_challenge_view 9`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The planner converts the frozen repeated-object residual branch into label-free observation targets. It is not a terminal utility result. It makes the next evidence step executable: frame/projection smoke, then detector/SAM2 evidence, then a consistency analyzer that can test stable relation-anchor assignment and conflict-free candidate-specific support. Candidate commit/rejection, `first_eval`, policy-scale comparison, and paper claims remain blocked until that post-observation evidence produces a promotable branch outcome.

## Repeated-Object Relation-Anchor Consistency Frame/Projection Gate

### 사실

- Wrapper: `runtime/jobs/repeated_object_relation_anchor_consistency_frame_projection.sh`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_frame_projection_v1.verify.json`
- Source plan output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_v1`
- Frame output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_frames_v1`
- Projection output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_projection_v1`
- Docker image: `research3/habitat-h001:20260508-calib-artifacts`
- Frame export rows/headings: `27 / 180`
- Nonblank rows/headings: `27 / 180`
- Removed blank headings: `0`
- Projection rows/expected rows: `27 / 27`
- Projection visible rows/rate: `27 / 1.0`
- Missing candidate rows: `0`
- Explicit candidate-id selection rows: `27`
- Frame revision metadata rows: `27`
- View roles: `candidate_own_view 9`, `relation_anchor_context_view 9`, `orthogonal_axis_challenge_view 9`
- GT action rows: `0`
- Projection gate: `projection_anchor_smoke_passed true`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The frame/projection gate confirms that the repeated-object relation-anchor consistency observation targets are renderable and projectable. It still does not test detector/SAM2 evidence, relation-anchor assignment stability, or terminal utility. The next gate should run detector/SAM2 substrate on these frames and preserve target/context candidate provenance for a later consistency analyzer.

## Repeated-Object Relation-Anchor Consistency Detector/SAM2 Gate

### 사실

- Wrapper: `runtime/jobs/repeated_object_relation_anchor_consistency_detector_substrate.sh`
- Base wrapper: `runtime/jobs/expanded_retrieval_detector_substrate.sh`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_detector_substrate_v1.verify.json`
- Source frame output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_frames_v1`
- Source projection output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_projection_v1`
- Detector output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_substrate_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Device: `cuda`
- Max candidates per frame: `2`
- Frame/detector rows: `27 / 27`
- Detector box/SAM2/candidate association rates: `1.0 / 1.0 / 0.8889`
- Rows with candidate association: `24`
- Associated candidate heading count: `69`
- Detector boxes/masks: `135 / 135`
- Association rows: `360`
- Selected candidate count rows: `2:27`
- Explicit candidate-id selection rows: `27`
- Candidate point field: `grounded_position`
- Association depth tolerance: `1.0m`
- GT action rows: `0`
- Detector substrate gate: `passes_detector_substrate_gate true`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The detector/SAM2 gate confirms that the repeated-object branch has enough action-time visual evidence to define a post-detector consistency analyzer. It still does not prove ObjectNav goal validity. The next contract must separate target/context candidate support, relation-anchor assignment stability, depth-consistent candidate association, and orthogonal-axis contradiction, while keeping terminal commits, candidate commit/rejection, label joins, `first_eval`, policy-scale comparison, and paper claims blocked.

## Repeated-Object Relation-Anchor Consistency Detector Evidence Contract

### 사실

- Contract: `manifests/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.json`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.verify.json`
- Source detector output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_substrate_v1`
- Implementation target: `runtime/h001_runtime/analyze_repeated_object_relation_anchor_consistency_evidence.py`
- Expected output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1`
- Source gates: planner `true`, projection `true`, detector substrate `true`
- Source rows: request/candidate/pair/observation `3 / 9 / 27 / 27`
- Detector rows: `27`
- Detector association rows: `360`
- Detector box/SAM2/candidate association: `1.0 / 1.0 / 0.8889`
- Rows with candidate association: `24`
- Associated candidate heading count: `69`
- Selected candidate count rows: `2:27`
- Required view evidence rows: `27`
- Required candidate-context pair rows: `27`
- Required candidate consistency rows: `9`
- Required request consistency rows: `3`
- Required view roles: `candidate_own_view`, `relation_anchor_context_view`, `orthogonal_axis_challenge_view`
- Target association by role: `candidate_own_view 6/9`, `relation_anchor_context_view 9/9`, `orthogonal_axis_challenge_view 9/9`
- Context association by role: `candidate_own_view 3/9`, `relation_anchor_context_view 0/9`, `orthogonal_axis_challenge_view 0/9`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The contract freezes a nonterminal evidence analyzer. It should aggregate target/context support per view role, then classify each candidate as stable, ambiguous, insufficient, or contradicted without using labels. A promotable branch outcome can only unlock a later terminal-utility contract design; this analyzer itself must not commit or reject any candidate.

## Repeated-Object Relation-Anchor Consistency Detector Evidence Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/analyze_repeated_object_relation_anchor_consistency_evidence.py`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.verify.json`
- Output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker `py_compile`: passed
- Docker run: passed
- Evidence gate: `true`
- View / pair / candidate / request rows: `27 / 27 / 9 / 3`
- Detector association rows: `360`
- Target association by role: `candidate_own_view 6/9`, `relation_anchor_context_view 9/9`, `orthogonal_axis_challenge_view 9/9`
- Context association by role: `candidate_own_view 3/9`, `relation_anchor_context_view 0/9`, `orthogonal_axis_challenge_view 0/9`
- Candidate consistency status: `ambiguous_repeated_object_candidate 6`, `insufficient_candidate_evidence 3`
- Candidate recommended actions: `request_repeated_object_ambiguity_followup 6`, `request_candidate_own_view_recovery 3`
- Request recommended action: `request_additional_repeated_object_disambiguation 3`
- Stable candidate rows: `0`
- Promotable branch outcome rows: `0`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The analyzer satisfies the frozen nonterminal evidence contract but does not unlock terminal utility. The repeated-object branch still needs residual diagnosis because own-view context leakage and missing own-view target support prevent a conflict-free promotable branch outcome.

## Repeated-Object Relation-Anchor Consistency Residual Diagnostic

### 사실

- Analyzer: `runtime/h001_runtime/diagnose_repeated_object_relation_anchor_consistency_residual.py`
- Verify: `manifests/h001_repeated_object_relation_anchor_consistency_residual_diagnostic_v1.verify.json`
- Output: `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_residual_diagnostic_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker `py_compile`: passed
- Docker run: passed
- Residual diagnostic gate: `true`
- Candidate / request rows: `9 / 3`
- Residual failure classes: `own_view_context_leakage 3`, `same_request_stable_rule_tie 3`, `missing_own_view_target_support 3`
- Request residual status: `same_request_stable_tie_with_own_view_context_leakage 3`
- Stable-rule candidate count: `2` per request
- Promotable branch outcome rows: `0`
- Recommended request action: `close_repeated_object_priority_branch_without_promotion 3`
- Next branch after closure: `association_geometry_underlink 3`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The repeated-object priority branch is closed as non-promotable. The next evaluation contract should move to `association_geometry_underlink` repair-followup evidence and keep terminal utility, candidate commit/rejection, `first_eval`, policy-scale comparison, and paper claims blocked.

## Association-Geometry Underlink Repair-Followup Evidence Contract

### 사실

- Contract: `manifests/h001_association_geometry_underlink_repair_followup_evidence_v1.json`
- Verify: `manifests/h001_association_geometry_underlink_repair_followup_evidence_v1.verify.json`
- Status: frozen design contract before implementation
- Source gates: repeated-object residual diagnostic `true`, repeated-object promotable rows `0`, promotion requirement `true`, branch synthesis `true`, association-geometry follow-up `true`, relation-anchor selection repair `true`, direction-specific re-observation repair `true`
- Target family: `association_geometry_underlink`
- Source branch/request/materialized rows: `2 / 2 / 8`
- Expected probe/request rows: `6 / 2`
- Follow-up routes: `route_to_relation_anchor_selection_repair 1`, `route_to_direction_specific_reobservation_repair 1`
- Required probe roles: `failed_explicit_relation_anchor_row`, `same_direction_anchorless_recovery_row`, `failed_requested_direction_explicit_anchor_row`, `failed_requested_direction_anchorless_row`, `recovered_target_to_relation_anchor_explicit_anchor_row`, `recovered_target_to_relation_anchor_anchorless_row`
- Minimum recovered associated/depth-consistent heading counts: `10 / 9`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract makes the next analyzer a repairability audit, not an ObjectNav goal-validity rule. It should show whether association-geometry underlink can be explained by anchor selection or direction-specific viewpoint failure, while rejecting shortcuts such as `commit_if_any_repair_recovers_association`, `commit_if_inside_mask_projection_exists`, and `choose_direction_with_highest_association`.

## Association-Geometry Underlink Repair-Followup Evidence Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/analyze_association_geometry_underlink_repair_followup_evidence.py`
- Verify: `manifests/h001_association_geometry_underlink_repair_followup_evidence_v1.verify.json`
- Output: `local_dataset/runs/h001_association_geometry_underlink_repair_followup_evidence_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker `py_compile`: passed
- Docker run: passed
- Evidence gate: `true`
- Evidence / request rows: `6 / 2`
- Evidence classes: `explicit_anchor_underlink 1`, `requested_direction_underlink 2`, `same_direction_anchorless_recovery 1`, `target_to_relation_anchor_recovery 2`
- Evidence status: `repair_recovered_association_and_depth 3`, `underlink_inside_mask_without_candidate_association 3`
- Request outcomes: `anchor_selection_repair_supported_but_nonterminal 1`, `direction_specific_reobservation_supported_but_nonterminal 1`
- Recovered associated/depth-consistent heading counts: `10 / 9`
- Promotable branch outcome rows: `0`
- Action forbidden keys: `0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The analyzer confirms association-geometry underlink is repairable as active evidence acquisition, but it still does not provide ObjectNav goal-validity authority. The next contract should either define depth-stagnation independent support or close the residual branch family set as terminal-blocking evidence.

## Residual Branch Closure Contract

### 사실

- Contract: `manifests/h001_residual_branch_closure_v1.json`
- Verify: `manifests/h001_residual_branch_closure_v1.verify.json`
- Status: frozen design contract before implementation
- Selected path: `residual_branch_closure_before_terminal_utility`
- Deferred path: `depth_stagnation_independent_support_probe`
- Source gates: residual branch synthesis `true`, promotion requirement `true`, repeated-object residual diagnostic `true`, association-geometry underlink repair-followup evidence `true`, depth-stagnation branch `true`
- Residual family / request / source-branch rows: `3 / 6 / 15`
- Family output rows: `association_geometry_underlink 8`, `repeated_object_relation_anchor_ambiguity 12`, `depth_stagnation 1`
- Promotion requirement status: `defined_not_satisfied 3`
- Repeated-object promotable branch outcome rows: `0`
- Association-geometry promotable branch outcome rows: `0`
- Depth-stagnation request rows: `1`
- Depth-stagnation association/depth-consistency delta: `0 / 0`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

Depth-stagnation independent-support is not the best immediate next probe because the current evidence is a single stagnant `sofa` row and would produce weak reviewer-defense if promoted now. Closing the residual branch family is stronger: repeated-object ambiguity, association-geometry underlink, and depth-stagnation are all recorded as terminal-blocking mechanism evidence before any terminal utility, `first_eval`, policy-scale comparison, or paper claim is reopened. The next implementation should write closure rows and a closure summary from the frozen contract.

## Residual Branch Closure Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/close_residual_partial_relation_depth_branches.py`
- Verify: `manifests/h001_residual_branch_closure_v1.verify.json`
- Output: `local_dataset/runs/h001_residual_branch_closure_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker `py_compile`: passed
- Docker run: passed
- Closure gate: `true`
- Closure rows: `3`
- Closure status counts: `closed_without_promotion_after_relation_anchor_consistency_residual_diagnostic 1`, `closed_as_repairable_but_nonpromotable_anchor_direction_underlink 1`, `closed_as_one_row_stagnant_evidence_audit_without_independent_support_probe 1`
- Closure failure mechanisms: `same_request_repeated_object_stable_tie_with_own_view_context_leakage 1`, `own_view_context_leakage 1`, `missing_own_view_target_support 1`, `anchor_selection_underlink_repairable_but_nonterminal 1`, `direction_specific_reobservation_repairable_but_nonterminal 1`, `association_present_depth_stagnant_without_evidence_delta 1`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The residual partial relation-depth branch family is now explicitly closed as terminal-blocking failure taxonomy. This is useful for paper novelty defense because it explains why repeated-object relation-anchor consistency, association-geometry repairability, and stagnant positive depth evidence are not valid terminal shortcuts. It still does not unlock terminal utility, `first_eval`, policy-scale comparison, or paper claims. This closure led to the next label-free selector below.

## Next Label-Free Evidence Family Selection

### 사실

- Contract: `manifests/h001_next_label_free_evidence_family_v1.json`
- Verify: `manifests/h001_next_label_free_evidence_family_v1.verify.json`
- Selector: `runtime/h001_runtime/select_next_label_free_evidence_family.py`
- Output: `local_dataset/runs/h001_next_label_free_evidence_family_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker `py_compile`: passed
- Docker run: passed
- Selection gate: `true`
- Selected family: `missing_own_view_support_recheck`
- Selected branch/action: `correct_candidate_missing_own_view_support` / `request_missing_own_view_recheck`
- Selected request/candidate rows: `7 / 20`
- Companion guard branch/action: `negative_missing_support_guard` / `guard_negative_missing_support`
- Companion request/candidate rows: `7 / 20`
- Closed/deferred branches: `unique_support_visibility_not_goal_validity`, `partial_relation_depth_true_goal`, `depth_stagnation_independent_support_probe`
- Terminal commits: `0`
- Candidate commit/rejection rows: `0 / 0`
- Uses GT for action: `false`
- Uses GT for analysis: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The next branch should test missing own-view support through active observation before any rejection shortcut is introduced. `negative_missing_support_guard` touches the same `7/20` request/candidate rows, but promoting it first would turn missing evidence into a candidate rejection rule. `missing_own_view_support_recheck` is more aligned with H001 because it asks whether mobility can acquire independent candidate evidence without using labels, terminal commits, or threshold tuning.

## Missing Own-View Recheck Observation Contract

### 사실

- Contract: `manifests/h001_missing_own_view_recheck_observation_v1.json`
- Verify: `manifests/h001_missing_own_view_recheck_observation_v1.verify.json`
- Status: Docker-verified materializer/planner smoke
- Input builder: `runtime/h001_runtime/build_missing_own_view_recheck_inputs.py`
- Planner: `runtime/h001_runtime/plan_missing_own_view_recheck.py`
- Output: `local_dataset/runs/h001_missing_own_view_recheck_observation_v1`
- Target branch/action: `correct_candidate_missing_own_view_support` / `request_missing_own_view_recheck`
- Target request/candidate rows: `7 / 20`
- Companion guard: `negative_missing_support_guard`
- Companion guard request/candidate rows: `7 / 20`
- Fresh base support rows: `20`
- Fresh base support class: `weak_or_partial_candidate_specific_support 20`
- Strong own-view evidence false rows: `20`
- Candidate-specific support false rows: `20`
- Base candidate association true/false rows: `18 / 2`
- Existing source plan rows for selected candidates: `80`
- Existing source plan rows per target candidate: `4`
- Materialized request/candidate/base/source-plan rows: `7 / 20 / 20 / 80`
- Observation plan rows: `80`
- Observation plan rows per target candidate: `4`
- Skipped rows: `0`
- Candidate artifact rows / unique candidates: `5 / 16`
- View role: `candidate_own_view_recheck 80`
- Query counts: `bed 8`, `plant 6`, `sofa 6`
- Scene counts: `4ok3usBNeis 4`, `QaLdnwvtxbs 2`, `bCPU9suPUw9 3`, `bxsVRursffK 6`, `q3zU7Yy5E5s 5`
- Terminal commits: `0`
- Candidate rejection rows: `0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This materializer/planner smoke turns missing own-view support into candidate-centered active observation rows while preserving `negative_missing_support_guard` only as a deferred safety counterfactual. It explicitly blocks `reject_missing_own_view_without_recheck`, `commit_after_relation_depth_resolved_without_own_view_support`, and promotion of the guard to candidate rejection. The next gate is frame/projection smoke; any detector evidence, correctness-label join, terminal utility, `first_eval`, policy-scale comparison, or paper claim must wait until render/projection rows exist.

## Missing Own-View Recheck Frame/Projection Smoke

### 사실

- Verify: `manifests/h001_missing_own_view_recheck_frame_projection_v1.verify.json`
- Job: `runtime/jobs/missing_own_view_recheck_frame_projection.sh`
- Frame output: `local_dataset/runs/h001_missing_own_view_recheck_observation_frames_v1`
- Projection output: `local_dataset/runs/h001_missing_own_view_recheck_observation_projection_v1`
- Docker image: `research3/habitat-h001:20260508-calib-artifacts`
- Frame rows / rendered headings: `80 / 320`
- Nonblank rows / kept headings: `80 / 317`
- Removed blank headings: `3`
- Dropped rows: `0`
- Projection rows / expected rows: `80 / 80`
- Projection visible rows / rate: `80 / 1.0`
- Missing candidate rows: `0`
- Candidate selection source: `explicit_candidate_ids 80`
- GT action rows: `0`
- Projection gate: `true`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This smoke confirms renderability and projection anchors for all missing-own-view recheck rows. The `3` blank headings are a viewpoint/rendering limitation isolated by the nonblank filter, not a row-level failure. The next gate is detector/SAM2 substrate; terminal utility, candidate rejection, `first_eval`, policy-scale comparison, and paper claims remain blocked.

## Missing Own-View Recheck Detector/SAM2 Substrate

### 사실

- Verify: `manifests/h001_missing_own_view_recheck_detector_substrate_v1.verify.json`
- Job: `runtime/jobs/missing_own_view_recheck_detector_substrate.sh`
- Output: `local_dataset/runs/h001_missing_own_view_recheck_observation_detector_substrate_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Device: `cuda`
- Detector rows: `80`
- Detector box / SAM2 / candidate association rates: `1.0 / 1.0 / 0.9625`
- Rows with candidate association: `77`
- Rows without candidate association: `3`
- Unassociated rows: `QaLdnwvtxbs sofa rival_identity:3 spatial_nms:0`, `4ok3usBNeis sofa rival_identity:22 spatial_nms:9`, `4ok3usBNeis sofa rival_identity:22 spatial_nms:3`
- Associated candidate heading count: `236`
- Detector boxes / masks: `562 / 562`
- Projected pixels inside mask: `263`
- Association rows: `317`
- Candidate selection source: `explicit_candidate_ids 80`
- GT action rows: `0`
- Detector substrate gate: `true`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The substrate now provides enough detector/SAM2 evidence to write a post-detector analyzer contract. That contract must aggregate acquired own-view support and separately report the `3` unassociated `sofa` rows. It must not convert detector visibility or missing association directly into candidate commit/rejection, terminal utility, `first_eval`, policy-scale comparison, or paper claims.

## Missing Own-View Recheck Post-Detector Evidence Contract

### 사실

- Contract: `manifests/h001_missing_own_view_recheck_evidence_v1.json`
- Verify: `manifests/h001_missing_own_view_recheck_evidence_v1.verify.json`
- Analyzer target: `runtime/h001_runtime/analyze_missing_own_view_recheck_evidence.py`
- Output target: `local_dataset/runs/h001_missing_own_view_recheck_evidence_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Source gates: input/materializer `true`, plan `true`, projection `true`, detector/SAM2 substrate `true`
- Expected view / target-candidate / request / unassociated-frame rows: `80 / 20 / 7 / 3`
- Target candidates with any association: `20`
- Target candidates with full `4/4` association: `17`
- Target candidates with partial `3/4` association: `3`
- Target candidates with zero association: `0`
- Minimum candidate association rate: `0.95`
- Minimum rows with candidate association: `77`
- Minimum associated candidate heading count: `236`
- Minimum projected pixels inside mask: `260`
- Required audit rows: `3` unassociated `sofa` frames
- Action forbidden key count maximum: `0`
- Terminal commits maximum: `0`
- Candidate commit / rejection rows maximum: `0 / 0`
- Uses GT for action: `false`
- Terminal utility validation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract converts the missing-own-view branch from substrate evidence into a nonterminal evidence aggregation problem. The analyzer may report `candidate_own_view_support_acquired`, `partial`, or `absent` states, but it must not turn acquired support into a goal commit or turn one unassociated view into candidate rejection. The reviewer-facing question is whether active mobility acquired the missing evidence state; `ObjectNav` goal validity remains a later arbitration problem.

## Missing Own-View Recheck Post-Detector Evidence Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/analyze_missing_own_view_recheck_evidence.py`
- Verify: `manifests/h001_missing_own_view_recheck_evidence_v1.verify.json`
- Output: `local_dataset/runs/h001_missing_own_view_recheck_evidence_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- View / target-candidate / request / unassociated-frame rows: `80 / 20 / 7 / 3`
- Candidate status: `candidate_own_view_support_acquired 20`
- Request action: `keep_nonterminal_own_view_support_for_guard_arbitration_contract 7`
- Rows with candidate association: `77`
- Candidate association rate: `0.9625`
- Target candidates with any association: `20`
- Target candidates with at least three associated views: `20`
- Target candidates with full `4/4` association: `17`
- Target candidates with partial `3/4` association: `3`
- Target candidates with zero association: `0`
- Associated candidate heading count: `236`
- Projected pixels inside mask: `263`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Evidence gate: `true`
- Paper claim allowed: `false`
- Recommended next action: `design_missing_own_view_guard_arbitration_contract`

### 에이전트 추론

The analyzer shows that active re-observation can acquire own-view support state for all selected candidates, including the three candidates with one unassociated frame. This is a mechanism result for evidence acquisition, not `ObjectNav` goal validity. The next contract should decide how to interpret `negative_missing_support_guard` after support acquisition without allowing direct candidate commit/rejection, `first_eval`, policy-scale comparison, terminal utility, or paper claims.

## Missing Own-View Guard Arbitration Contract

### 사실

- Contract: `manifests/h001_missing_own_view_guard_arbitration_v1.json`
- Verify: `manifests/h001_missing_own_view_guard_arbitration_v1.verify.json`
- Analyzer target: `runtime/h001_runtime/analyze_missing_own_view_guard_arbitration.py`
- Output target: `local_dataset/runs/h001_missing_own_view_guard_arbitration_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Source evidence gate: `true`
- Candidate / request guard rows: `20 / 7`
- Preserved unassociated-frame audit rows: `3`
- Expected guard-deactivated candidate / request rows: `20 / 7`
- Expected guard-deferred candidate rows: `0`
- Expected candidate commit / rejection rows: `0 / 0`
- Expected terminal commits: `0`
- Expected promotable terminal outcome rows: `0`
- Action forbidden key count maximum: `0`
- Uses GT for action: `false`
- Terminal utility validation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The contract turns acquired support into guard deactivation, not candidate selection. This preserves the paper-relevant mechanism: missing own-view support should trigger active observation before rejection. Since every selected request still has multiple acquired-support candidates or unresolved goal-validity context, terminal utility remains blocked.

## Missing Own-View Guard Arbitration Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/analyze_missing_own_view_guard_arbitration.py`
- Verify: `manifests/h001_missing_own_view_guard_arbitration_v1.verify.json`
- Output: `local_dataset/runs/h001_missing_own_view_guard_arbitration_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Source missing-own-view recheck evidence gate: `true`
- Candidate / request guard rows: `20 / 7`
- Preserved unassociated-frame audit rows: `3`
- Guard-deactivated candidate / request rows: `20 / 7`
- Guard-deferred candidate rows: `0`
- Guard arbitration decision: `deactivate_negative_missing_support_guard_after_recheck 20`
- Request guard status: `missing_own_view_guard_closed_as_nonterminal_evidence 7`
- Candidate nonterminal actions: `deactivate_negative_missing_support_guard_after_recheck 17`, `keep_guard_deactivated_but_report_unassociated_view_audit 3`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Promotable terminal outcome rows: `0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Gate: `true`
- Paper claim allowed: `false`
- Recommended next task: `freeze_missing_own_view_guard_branch_closure_or_select_next_label_free_family`

### 에이전트 추론

This analyzer closes the deferred `negative_missing_support_guard` as nonterminal evidence after recheck support acquisition. The result supports the method principle that missing own-view support should trigger active observation before rejection. It does not establish `ObjectNav` goal validity, terminal utility, `first_eval`, policy-scale comparison, or paper claims.

## Missing Own-View Guard Branch Closure

### 사실

- Contract: `manifests/h001_missing_own_view_guard_branch_closure_v1.json`
- Analyzer: `runtime/h001_runtime/close_missing_own_view_guard_branch.py`
- Verify: `manifests/h001_missing_own_view_guard_branch_closure_v1.verify.json`
- Output: `local_dataset/runs/h001_missing_own_view_guard_branch_closure_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Selected branch: `correct_candidate_missing_own_view_support`
- Paired guard branch: `negative_missing_support_guard`
- Branch / request / candidate closure rows: `2 / 7 / 20`
- Closed request / candidate rows: `7 / 20`
- Branch status counts: `closed_as_evidence_acquired_but_nonpromotable_goal_validity 1`, `closed_as_deactivated_after_recheck_support_acquisition 1`
- Request closure status: `missing_own_view_and_negative_guard_branches_closed_nonterminal 7`
- Guard-deactivated candidate / request rows: `20 / 7`
- Guard-deferred candidate rows: `0`
- Unassociated-frame audit rows preserved: `3`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Promotable terminal outcome rows: `0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Closure gate: `true`
- Paper claim allowed: `false`
- Recommended next task: `select_next_label_free_evidence_family_after_object_relation_branch_family_closure`

### 에이전트 추론

This closes the missing-own-view route as mechanism evidence: active re-observation acquired the missing support state and then removed the negative guard. It does not produce a promotable terminal outcome because own-view support acquisition still does not establish `ObjectNav` goal validity. The next step should select a new label-free evidence family or close the broader object-relation branch family, not unlock `first_eval`, policy-scale comparison, terminal utility, or paper claims.

## Next Label-Free Evidence Family After Object-Relation Closure

### 사실

- Contract: `manifests/h001_next_label_free_evidence_family_after_object_relation_v1.json`
- Selector: `runtime/h001_runtime/select_next_evidence_family_after_object_relation.py`
- Verify: `manifests/h001_next_label_free_evidence_family_after_object_relation_v1.verify.json`
- Output: `local_dataset/runs/h001_next_label_free_evidence_family_after_object_relation_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Selection gate: `true`
- Selected family: `instance_arbitration_defer_v1`
- Selected action: `freeze_instance_arbitration_label_free_evidence_contract`
- Route branch counts: `source_pool_repair_v1 5`, `goal_validity_confirmation_v1 7`, `instance_arbitration_defer_v1 9`
- Selected family stats: request rows `9`, scenes `5`, queries `3`, candidate count sum `51`, strong own-view candidate count sum `28`, detector-strong candidate count sum `36`
- Object-relation closure check: unique-support closed/unclosed request rows `4/0`, residual closure/promotable rows `3/0`, missing-own-view closed/promotable rows `7/0`
- Source-pool status: route branch rows `5`, second fallback gate `true`, backend/source-map blind spot after second fallback `true`, goal-validity confirmation unblocked `false`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This selector is not a utility result. It is a branch-priority gate after object-relation closure. It selects `instance_arbitration_defer_v1` because source-pool repair and object-relation evidence are already followed to terminal-blocking or backend-blind-spot outcomes, while multi-candidate instance arbitration remains the largest unprocessed label-free branch. The next contract must define what evidence could reduce this ambiguity without using evaluation labels, threshold tuning, candidate commit/rejection, `first_eval`, policy-scale comparison, or paper claims.

## Instance-Arbitration Evidence Contract

### 사실

- Contract: `manifests/h001_instance_arbitration_evidence_v1.json`
- Static verify: `manifests/h001_instance_arbitration_evidence_v1.verify.json`
- Status: frozen design contract before implementation
- Target branch/action: `instance_arbitration_defer_v1` / `defer_instance_arbitration_unresolved`
- Source route rows: `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1/expanded_retrieval_local_context_route_specific_rows.jsonl`
- Source candidate artifact: `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl`
- Request rows / scenes / queries: `9 / 5 / 3`
- Unique target scene/query artifact rows: `7`
- Candidate reference rows: `51`
- Unordered candidate pair rows: `121`
- Source-top / strong own-view / detector-strong / local-context refs: `9 / 28 / 36 / 11`
- Candidate count distribution: `4:1`, `5:1`, `6:7`
- Required candidate observation rows minimum: `51`
- Required pair observation rows minimum: `121`
- Required total observation rows minimum: `172`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract freezes instance arbitration as pair-level evidence acquisition rather than candidate reranking. The next implementation must write request, candidate, pair, and observation-plan rows for all selected rows. It must preserve duplicate request rows that share a scene/query, and it must not drop candidates because a simpler non-GT signal is weak or strong. This keeps the novelty path focused on converting repeated-instance semantic uncertainty into active evidence, not on source-top, detector-score, own-support, local-context-only, or threshold-tuned shortcut commits.

## Instance-Arbitration Evidence Materializer And Planner

### 사실

- Input materializer: `runtime/h001_runtime/build_instance_arbitration_inputs.py`
- Observation planner: `runtime/h001_runtime/plan_instance_arbitration_evidence.py`
- Verify: `manifests/h001_instance_arbitration_evidence_v1.verify.json`
- Output: `local_dataset/runs/h001_instance_arbitration_evidence_v1`
- Docker images: `research3/openvocab-perception:20260513-v3c-gdino-sam2` for materialization, `research3/habitat-h001:20260508-calib-artifacts` for Habitat observation planning
- Request / candidate / pair / candidate-artifact / observation rows: `9 / 51 / 121 / 7 / 172`
- Candidate / pair observation rows: `51 / 121`
- Skipped rows: `0`
- Pair probe types: `pair_common_view 57`, `pair_dual_standoff_fallback 64`
- Viewpoint sources: `common_pair_navmesh 57`, `standoff_navmesh 115`
- Target distance min / mean / max: `1.5926m / 1.9894m / 3.2408m`
- Action forbidden key count: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Uses GT for action: `false`
- Input materializer gate: `true`
- Observation plan gate: `true`
- Paper claim allowed: `false`
- Planning warning: Habitat printed `.basis.scn` semantic scene descriptor load warnings, but the observation plan gate passed.

### 에이전트 추론

The materializer/planner turns the frozen instance-arbitration branch into a complete nonterminal observation substrate. This is still substrate evidence only: it does not choose a candidate, reject a candidate, validate terminal utility, rerun `first_eval`, unlock policy-scale comparison, or support a paper claim. The next gate is frame/projection smoke for the `172` planned observations.

## Instance-Arbitration Frame / Projection Smoke

### 사실

- Job: `runtime/jobs/instance_arbitration_frame_projection.sh`
- Verify: `manifests/h001_instance_arbitration_frame_projection_v1.verify.json`
- Plan output: `local_dataset/runs/h001_instance_arbitration_evidence_v1`
- Frame output: `local_dataset/runs/h001_instance_arbitration_evidence_frames_v1`
- Projection output: `local_dataset/runs/h001_instance_arbitration_evidence_projection_v1`
- Docker image: `research3/habitat-h001:20260508-calib-artifacts`
- Policy: `InstanceArbitrationPairEvidence`
- Frame rows requested / exported: `172 / 172`
- Rendered heading count: `1012`
- Min / max headings per row: `4 / 7`
- RGB / depth / pose / metadata files: `1012 / 1012 / 1012 / 1012`
- Nonblank input / output rows: `172 / 172`
- Dropped rows: `0`
- Removed blank heading count: `0`
- Row-level nonblank gate: `true`
- Strict no-blank-heading gate: `true`
- Projection rows / expected rows: `172 / 172`
- Projection visible rows / rate: `172 / 1.0`
- Candidate selection source: `explicit_candidate_ids 172`
- Missing candidate rows: `0`
- GT action rows: `0`
- Uses GT for action: `false`
- Projection gate: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The frame/projection smoke shows the pair-level instance-arbitration observation plan is renderable and every target candidate has at least one visible projection anchor. This enables detector/SAM2 substrate on the same fixed observation rows. It still does not establish detector evidence quality, terminal utility, candidate commitment, candidate rejection, `first_eval`, policy-scale comparison, or a paper claim.

## Instance-Arbitration Detector / SAM2 Substrate

### 사실

- Job: `runtime/jobs/instance_arbitration_detector_substrate.sh`
- Verify: `manifests/h001_instance_arbitration_detector_substrate_v1.verify.json`
- Output: `local_dataset/runs/h001_instance_arbitration_evidence_detector_substrate_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Policy: `InstanceArbitrationPairEvidence`
- Frame / detector rows: `172 / 172`
- Detector box / SAM2 / candidate association rates: `1.0 / 1.0 / 0.8081`
- Rows with candidate association: `139`
- Associated candidate heading count: `483`
- Association rows: `1820`
- Detector boxes / masks: `2562 / 2562`
- Projected pixels inside mask: `963`
- View-role rows: `candidate_own_view_refresh 51`, `source_top_contrast_view 42`, `pair_common_view_or_dual_standoff 39`, `local_context_contrast_view 40`
- Frame association by role: `43/51`, `32/42`, `30/39`, `34/40`
- Selected candidate count rows: `1:51`, `2:121`
- Candidate selection source: `explicit_candidate_ids 172`
- GT action rows: `0`
- Uses GT for action: `false`
- Detector substrate gate: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The detector/SAM2 substrate is sufficient to implement a post-detector evidence analyzer because every planned frame row produced detector boxes and masks, and candidate association clears the fixed `0.80` gate. This still does not prove candidate identity or ObjectNav goal validity. The analyzer must aggregate evidence across own-view refresh, source-top contrast, local-context contrast, and pair/common-or-standoff roles without allowing detector-score, SAM2 presence, any-association, own-view-only, or source-top shortcut commits.

## Instance-Arbitration Post-Detector Evidence Contract

### 사실

- Contract: `manifests/h001_instance_arbitration_detector_evidence_v1.json`
- Status: `frozen_before_implementation`
- Target analyzer: `runtime/h001_runtime/analyze_instance_arbitration_detector_evidence.py`
- Target output: `local_dataset/runs/h001_instance_arbitration_detector_evidence_v1`
- Required view / candidate / pair / request rows: `172 / 51 / 121 / 9`
- Minimum detector association rows: `1820`
- Minimum candidate association rate: `0.80`
- Minimum associated candidate heading count: `483`
- Required view roles: `candidate_own_view_refresh`, `source_top_contrast_view`, `local_context_contrast_view`, `pair_common_view_or_dual_standoff`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Uses GT for action: `false`
- Terminal utility validation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract turns repeated-instance ambiguity into a nonterminal evidence aggregation problem. The analyzer should report view, candidate, pair, request, and unresolved-case evidence. A promotable branch outcome, if it appears, only permits a later terminal utility contract. It does not permit immediate commit/rejection, `first_eval` rerun, policy-scale comparison, or paper claim.

## Instance-Arbitration Post-Detector Evidence Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/analyze_instance_arbitration_detector_evidence.py`
- Verify: `manifests/h001_instance_arbitration_detector_evidence_v1.verify.json`
- Output: `local_dataset/runs/h001_instance_arbitration_detector_evidence_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- View / candidate / pair / request / unresolved rows: `172 / 51 / 121 / 9 / 9`
- Candidate evidence statuses: `ambiguous_rival_leakage_candidate 32`, `contradicted_by_pair_or_contrast_evidence 18`, `partial_instance_support 1`
- Pair evidence statuses: `ambiguous_both_candidates_supported 36`, `ambiguous_no_candidate_support 25`, `resolved_in_favor_of_candidate_a_nonterminal 49`, `resolved_in_favor_of_candidate_b_nonterminal 11`
- Request action: `diagnose_instance_arbitration_residual_evidence 9`
- Promotable branch outcome rows: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Analyzer gate: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The analyzer verifies the aggregation harness, but it does not produce a promotable instance-arbitration branch. All nine requests remain unresolved because no request has a unique candidate-specific instance-support outcome with all pair contexts resolved. The next gate is residual diagnosis: separate rival leakage, pair ambiguity, contradiction-by-pair/contrast, missing support, and backend/source-pool limitations before designing any further observation or terminal utility contract.

## Instance-Arbitration Residual Diagnostic

### 사실

- Diagnostic: `runtime/h001_runtime/diagnose_instance_arbitration_residual.py`
- Verify: `manifests/h001_instance_arbitration_residual_diagnostic_v1.verify.json`
- Output: `local_dataset/runs/h001_instance_arbitration_residual_diagnostic_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Candidate / pair / request rows: `51 / 121 / 9`
- Candidate residual classes: `own_view_support_with_rival_leakage 20`, `pair_or_contrast_contradiction 18`, `source_top_shortcut_rival_leakage 8`, `contrast_support_with_rival_leakage 4`, `partial_support_without_pair_resolution 1`
- Pair residual classes: `one_sided_pair_support_nonterminal 53`, `common_view_both_candidates_supported 36`, `dual_standoff_no_candidate_support 14`, `common_view_no_candidate_support 11`, `one_sided_pair_support_with_leakage 7`
- Request residual statuses: `multiple_lossless_pair_graph_candidates 7`, `unique_lossless_pair_graph_candidate_blocked_by_common_view_overlap 2`
- Pair-graph follow-up request rows: `9`
- Unique / multiple lossless pair-graph request rows: `2 / 7`
- Promotable branch outcome rows: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Diagnostic gate: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The residual diagnostic identifies a label-free graph signal but no terminal outcome. Pair evidence can produce lossless graph candidates, yet `7/9` requests have multiple lossless candidates and `2/9` unique candidates are still blocked by common-view overlap. The next contract should test pair-graph consistency as a nonterminal follow-up and must explicitly block `commit_graph_winner`, `commit_lossless_candidate`, and `commit_max_pair_win_candidate`.

## Instance-Arbitration Pair-Graph Consistency Follow-Up Contract

### 사실

- Contract: `manifests/h001_instance_arbitration_pair_graph_consistency_followup_v1.json`
- Static verify: `manifests/h001_instance_arbitration_pair_graph_consistency_followup_v1.verify.json`
- Status: `frozen_design_contract_before_implementation`
- Target analyzer: `runtime/h001_runtime/analyze_instance_arbitration_pair_graph_consistency_followup.py`
- Target output: `local_dataset/runs/h001_instance_arbitration_pair_graph_consistency_followup_v1`
- Source residual candidate / pair / request rows: `51 / 121 / 9`
- Pair-graph follow-up request rows: `9`
- Lossless / max-pair-winner candidate memberships: `17 / 14`
- Unique / multiple lossless request rows: `2 / 7`
- Pair graph winner / no-winner pair rows: `60 / 61`
- Expected candidate / pair / request graph rows: `51 / 121 / 9`
- Expected shortcut audit rows minimum: `17`
- Expected promotable branch outcome rows: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Terminal utility validation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract turns pair-graph signal into a nonterminal consistency audit. It intentionally blocks `commit_graph_winner`, `commit_lossless_candidate`, `commit_max_pair_win_candidate`, source-top or detector-strong shortcut commits, candidate rejection by pair loss, threshold tuning, `first_eval`, policy-scale comparison, terminal utility, and paper claims. The next implementation should write candidate graph, pair graph, request graph, shortcut-audit, and summary rows; if it still produces zero promotable outcomes, the instance-arbitration pair-graph branch should be closed or routed to the next label-free evidence family.

## Instance-Arbitration Pair-Graph Consistency Follow-Up Analyzer

### 사실

- Analyzer: `runtime/h001_runtime/analyze_instance_arbitration_pair_graph_consistency_followup.py`
- Verify: `manifests/h001_instance_arbitration_pair_graph_consistency_followup_v1.verify.json`
- Output: `local_dataset/runs/h001_instance_arbitration_pair_graph_consistency_followup_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Candidate / pair / request graph rows: `51 / 121 / 9`
- Shortcut audit rows: `357`
- Candidate graph statuses: `lossless_blocked_by_common_view_overlap 2`, `lossless_but_multiple_graph_candidates 15`, `max_pair_win_nonterminal_due_pair_losses 4`, `pair_or_contrast_contradiction_nonterminal 18`, `rival_leakage_nonterminal 12`
- Pair graph statuses: `common_view_overlap_blocks_pair_resolution 36`, `no_candidate_support_blocks_pair_resolution 25`, `one_sided_support_nonterminal_graph_edge 53`, `one_sided_support_with_leakage_nonterminal 7`
- Request graph statuses: `multiple_lossless_pair_graph_candidates_unresolved 7`, `unique_lossless_candidate_blocked_by_common_view_overlap 2`
- Shortcut would-select counts: `graph_winner_commit 14`, `lossless_candidate_commit 17`, `max_pair_win_count_commit 14`, `reject_candidate_with_pair_loss 33`, `source_top_lossless_commit 7`, `detector_strong_lossless_commit 4`
- Promotable branch outcome rows: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Follow-up gate: `true`
- Paper claim allowed: `false`
- Recommended next task: `close_instance_arbitration_pair_graph_branch_or_select_next_label_free_evidence_family`

### 에이전트 추론

Graph winners and lossless candidates remain useful as failure-taxonomy evidence, but they are not goal-validity authority. Multiple lossless candidates, common-view overlap, rival leakage, and pair losses block shortcut commitment or rejection. The next step should close this pair-graph branch or select another label-free evidence family; terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked.

## Instance-Arbitration Pair-Graph Branch Closure

### 사실

- Contract: `manifests/h001_instance_arbitration_pair_graph_branch_closure_v1.json`
- Analyzer: `runtime/h001_runtime/close_instance_arbitration_pair_graph_branch.py`
- Verify: `manifests/h001_instance_arbitration_pair_graph_branch_closure_v1.verify.json`
- Output: `local_dataset/runs/h001_instance_arbitration_pair_graph_branch_closure_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Branch / request / candidate / pair / shortcut closure rows: `1 / 9 / 51 / 121 / 357`
- Request closure statuses: `closed_as_multiple_lossless_pair_graph_candidates_unresolved 7`, `closed_as_unique_lossless_candidate_blocked_by_common_view_overlap 2`
- Candidate closure statuses: `closed_as_lossless_blocked_by_common_view_overlap 2`, `closed_as_lossless_but_multiple_graph_candidates 15`, `closed_as_max_pair_win_nonterminal_due_pair_losses 4`, `closed_as_pair_or_contrast_contradiction_nonterminal 18`, `closed_as_rival_leakage_nonterminal 12`
- Pair closure statuses: `closed_as_common_view_overlap_blocks_pair_resolution 36`, `closed_as_no_candidate_support_blocks_pair_resolution 25`, `closed_as_one_sided_support_nonterminal_graph_edge 53`, `closed_as_one_sided_support_with_leakage_nonterminal 7`
- Shortcut blocked reason counts: `candidate_rejection_by_pair_loss_forbidden_without_goal_validity_evidence 33`, `common_view_overlap_blocks_shortcut_commit 10`, `defer_all_is_control_baseline_not_utility_evidence 51`, `multiple_lossless_pair_graph_candidates_block_shortcut_commit 46`, `shortcut_rule_not_applicable_to_candidate 217`
- Promotable branch outcome rows: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Closure gate: `true`
- Paper claim allowed: `false`
- Recommended next task: `select_next_label_free_evidence_family_after_instance_arbitration_pair_graph_closure`

### 에이전트 추론

This closes the instance-arbitration pair-graph branch as terminal-blocking shortcut taxonomy. The branch is useful for reviewer-defense because it explains why graph winners, lossless candidates, max-pair wins, and pair-loss rejection are not valid goal-commit rules. It does not unlock terminal utility, `first_eval`, policy-scale comparison, or paper claims.

## Next Label-Free Evidence Family After Instance-Arbitration Closure

### 사실

- Contract: `manifests/h001_next_label_free_evidence_family_after_instance_arbitration_v1.json`
- Selector: `runtime/h001_runtime/select_next_evidence_family_after_instance_arbitration.py`
- Verify: `manifests/h001_next_label_free_evidence_family_after_instance_arbitration_v1.verify.json`
- Output: `local_dataset/runs/h001_next_label_free_evidence_family_after_instance_arbitration_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Selected family: `semantic_slam_map_pose_consistency_probe_v1`
- Selected action: `freeze_semantic_slam_map_pose_consistency_probe_contract`
- Route branch counts: `source_pool_repair_v1 5`, `goal_validity_confirmation_v1 7`, `instance_arbitration_defer_v1 9`
- Semantic branch promotable rows: `0`
- Semantic object branches exhausted: `true`
- Selection rows: `5`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Action forbidden key count: `0`
- Uses GT for action: `false`
- Selection gate: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The current semantic object evidence route is exhausted as terminal utility. Source-pool repair ends in a backend/source-map blind spot, object-relation and missing-own-view branches close without promotable terminal outcomes, and instance-arbitration pair-graph evidence closes as shortcut taxonomy. The next evaluation contract should therefore freeze a Step 4-5 semantic-SLAM map/pose consistency probe rather than reopening semantic object commit/reject shortcuts or rerunning `first_eval`.

The probe contract must keep the same separation rules:

- no terminal commit or candidate rejection from this selection result;
- no `first_eval` rerun or policy-scale comparison until a new probe has measurable evidence;
- action-time inputs must be label-free;
- map/pose metrics may use GT only as evaluation/reference, not as action input;
- `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` must be compared on the same rows or replay episodes.

## Semantic-SLAM Map/Pose Consistency Probe Contract

### 사실

- Contract: `manifests/h001_semantic_slam_map_pose_consistency_probe_v1.json`
- Verify: `manifests/h001_semantic_slam_map_pose_consistency_probe_v1.verify.json`
- Status: implemented and Docker-verified source audit
- Stage: `P4-design`
- Step 4-5 promotion satisfied: `false`
- First proxy metric: `pose_graph_connectivity`
- Primary source: `local_dataset/runs/h001_instance_arbitration_evidence_frames_v1`
- Primary source rows / headings: `172 / 1012`
- Primary source unique scenes: `5`
- RGB / depth / pose / metadata files: `1012 / 1012 / 1012 / 1012`
- Required first output: source audit completed
- Implementation: `runtime/h001_runtime/audit_semantic_slam_map_pose_consistency_sources.py`
- Target output: `local_dataset/runs/h001_semantic_slam_map_pose_consistency_probe_v1`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Uses GT for action: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract does not mean H001 has passed the Step 4-5 promotion gate. It only freezes the minimum source-audit and proxy-metric requirements for moving from exhausted semantic object shortcut branches toward map/pose-side uncertainty. The implemented source audit proves that existing RGB/depth/pose/metadata artifacts can support a label-free pose graph connectivity proxy. The next gate must define how this proxy is judged before any `SemanticOnly`, `SLAMOnly`, or `SemanticSLAM` comparison is implemented.

The first source audit should report:

- source inventory rows for primary and support frame families;
- RGB/depth/pose/metadata file counts;
- request/scene/query grouping;
- candidate or viewpoint node counts;
- candidate pose graph proxy readiness;
- forbidden action-label key count;
- whether a later `P4-proxy` implementation is justified.

## Semantic-SLAM Source Audit Result

### 사실

- Date checked: `2026-06-04`
- Implementation: `runtime/h001_runtime/audit_semantic_slam_map_pose_consistency_sources.py`
- Verify: `manifests/h001_semantic_slam_map_pose_consistency_probe_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_map_pose_consistency_probe_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Source inventory / probe request / pose graph proxy rows: `5 / 50 / 50`
- Source-ready rows: `5`
- Primary source ready: `true`
- Pose/depth/metadata ready: `true`
- Non-GT action gate: `true`
- Pose graph proxy ready rows: `50`
- Max node / edge count: `24 / 236`
- Pose graph proxy source counts:
  - `expanded_retrieval_local_context_frames_v1`: `21`
  - `instance_arbitration_evidence_frames_v1`: `9`
  - `missing_own_view_recheck_observation_frames_v1`: `7`
  - `object_relation_fresh_observation_frames_v1`: `7`
  - `partial_relation_depth_observation_frames_v1`: `6`
- Action forbidden key count: `0`
- Terminal commit rows: `0`
- Candidate commit / rejection rows: `0 / 0`
- Uses GT for action: `false`
- Source audit gate: `true`
- P4 proxy readiness gate: `true`
- Step 4-5 promotion satisfied: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The source audit unblocked the formal pose graph connectivity proxy gate below because the existing label-free frame artifacts have synchronized RGB/depth/pose/metadata and enough request-level nodes/edges. It does not prove SLAM utility, task improvement, or semantic-SLAM complementarity. The next evaluation step is strict edge variant analysis before any `SemanticOnly` / `SLAMOnly` / `SemanticSLAM` comparison.

## Semantic-SLAM Pose Graph Connectivity Proxy Gate

### 사실

- Date checked: `2026-06-04`
- Contract: `manifests/h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1.json`
- Verify: `manifests/h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1.verify.json`
- Implementation: `runtime/h001_runtime/evaluate_semantic_slam_pose_graph_connectivity_proxy_gate.py`
- Output: `local_dataset/runs/h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Gate rows: `13`
- Pose graph proxy rows / ready rows: `50 / 50`
- Source family count: `5`
- Primary source proxy rows: `9`
- Spatial edge rows: `46`
- Loop-closure proxy edge rows: `36`
- Spatial-or-loop edge rows: `46`
- Candidate-overlap-only rows / rate: `4 / 0.08`
- Candidate-overlap edge share: `0.5746`
- Dependency gate: `true`
- Proxy plumbing gate: `true`
- Edge quality gate: `true`
- Action safety gate: `true`
- Pose graph connectivity proxy gate: `true`
- Action forbidden key count: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Uses GT for action: `false`
- Step 4-5 promotion satisfied: `false`
- `SemanticOnly` / `SLAMOnly` / `SemanticSLAM` comparison allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This gate is a proxy-definition gate, not a SLAM result. The first proxy gate passes because most rows contain spatial or loop-closure proxy edges and candidate-overlap-only rows are rare. However, `candidate_id_overlap` still accounts for `57.46%` of edge reasons, so a reviewer-facing Step 4-5 path must recompute strict edge variants before any `SemanticOnly`, `SLAMOnly`, or `SemanticSLAM` comparison.

Edge roles:

- `spatial_proximity`: pose graph proxy signal
- `loop_closure_opportunity`: pose graph proxy signal
- `target_position_neighborhood`: semantic-map geometric context signal
- `candidate_id_overlap`: shortcut diagnostic only

### 논문 주장

No SLAM benefit, navigation utility, or semantic-SLAM complementarity claim is allowed from this gate alone.

### Next Gate

Implement a strict edge variant proxy analyzer that reports connectivity under at least:

- all reported edges;
- spatial-only edges;
- loop-closure-only edges;
- spatial-or-loop edges;
- target-neighborhood context edges;
- candidate-overlap-only diagnostic edges.

The analyzer must keep action-label leakage, terminal commits, candidate commit/rejection, `first_eval`, policy-scale comparison, and paper claims blocked.

## Semantic-SLAM Strict Edge Variant Proxy Gate

### 사실

- Date checked: `2026-06-04`
- Contract: `manifests/h001_semantic_slam_strict_edge_variant_proxy_v1.json`
- Verify: `manifests/h001_semantic_slam_strict_edge_variant_proxy_v1.verify.json`
- Implementation: `runtime/h001_runtime/analyze_semantic_slam_strict_edge_variants.py`
- Output: `local_dataset/runs/h001_semantic_slam_strict_edge_variant_proxy_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Request groups: `50`
- Variant rows / summary rows: `350 / 7`
- Source family count: `5`
- Canonical variant: `pose_spatial_or_loop`
- Canonical ready rows / rate: `46 / 0.92`
- Canonical minimum source ready rate: `0.8095`
- Context variant `map_pose_context_no_candidate` ready rows / rate: `46 / 0.92`
- Loop variant `pose_loop` ready rows / rate: `36 / 0.72`
- Shortcut variant `candidate_overlap_only` ready rows / rate: `50 / 1.0`
- Variant ready rates:
  - `all_edges`: `1.0`
  - `candidate_overlap_only`: `1.0`
  - `map_pose_context_no_candidate`: `0.92`
  - `pose_loop`: `0.72`
  - `pose_spatial`: `0.92`
  - `pose_spatial_or_loop`: `0.92`
  - `target_context`: `0.58`
- Dependency gate: `true`
- Strict edge variant gate: `true`
- Action safety gate: `true`
- Strict edge variant proxy gate: `true`
- Action forbidden key count: `0`
- Terminal commits: `0`
- Candidate commit / rejection rows: `0 / 0`
- Uses GT for action: `false`
- `SemanticOnly` / `SLAMOnly` / `SemanticSLAM` proxy comparison contract allowed: `true`
- `SemanticOnly` / `SLAMOnly` / `SemanticSLAM` comparison run allowed: `false`
- Step 4-5 promotion satisfied: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The strict edge variant gate passes because the canonical pose-only proxy remains available on `46/50` groups after excluding `candidate_id_overlap`. This removes the most obvious shortcut objection to defining a proxy comparison contract. It does not mean `SemanticSLAM` improves map/pose consistency; it only means the comparison can now be specified without relying on candidate-id overlap as pose evidence.

### Next Contract Requirements

The next `SemanticOnly` / `SLAMOnly` / `SemanticSLAM` proxy comparison contract must define:

- same request groups and source split for all compared policies;
- `NoReobserve` or source artifact reference as a non-active baseline;
- `SemanticOnly` utility based on semantic uncertainty terms only;
- `SLAMOnly` utility based on strict pose/map proxy terms only;
- `SemanticSLAM` utility combining semantic and strict pose/map proxy terms;
- fixed metric outputs: canonical strict proxy ready rate, edge count, largest component fraction, loop edge availability, travel-cost proxy, and blocked task-behavior metrics;
- no candidate commit/rejection, terminal utility, `first_eval`, policy-scale comparison, or paper claim until the comparison run is separately implemented and verified.

## Semantic-SLAM Proxy Comparison Contract

### 사실

- Date checked: `2026-06-04`
- Contract: `manifests/h001_semantic_slam_proxy_comparison_v1.json`
- Verify: `manifests/h001_semantic_slam_proxy_comparison_v1.verify.json`
- Status: frozen proxy comparison contract before implementation
- Stage: `P4-design`
- Request groups: `50`
- Join key: `(source_name, scene_key, query, request_id, episode_key)`
- Policies:
  - `NoReobserveReference`
  - `SemanticOnly`
  - `SLAMOnly`
  - `SemanticSLAM`
- Expected future comparison rows: `200`
- Canonical pose variant: `pose_spatial_or_loop`
- Semantic family weights: fixed in the manifest
- `SemanticOnly` formula: semantic uncertainty proxy plus travel penalty
- `SLAMOnly` formula: strict pose/map proxy gap plus travel penalty
- `SemanticSLAM` formula: fixed `0.5 * U_sem + 0.5 * U_slam - travel_penalty`
- Future implementation target: `runtime/h001_runtime/compare_semantic_slam_proxy_policies.py`
- Future output: `local_dataset/runs/h001_semantic_slam_proxy_comparison_v1`
- Implementation allowed: `true`
- Step 4-5 promotion satisfied: `false`
- Terminal utility allowed: `false`
- Candidate commit / rejection allowed: `false / false`
- `first_eval` rerun allowed: `false`
- Policy-scale comparison allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract turns the strict edge variant gate into an implementable proxy comparison. It fixes which policy sees which information channel, preventing the comparison from becoming a tuned module combination:

- `SemanticOnly` cannot use strict pose graph connectivity metrics.
- `SLAMOnly` cannot use semantic uncertainty family as a utility term and cannot use `candidate_id_overlap` as pose evidence.
- `SemanticSLAM` combines the two fixed proxy terms but cannot tune weights on evaluation labels.

### 논문 주장

No SLAM benefit, ObjectNav utility, or `SemanticSLAM` complementarity claim is allowed from the contract alone. The next step is Docker implementation and a separate result gate.

## SemanticSLAMInteraction Output Evaluation

### 사실

- Date checked: `2026-06-04`
- Implementation: `runtime/h001_runtime/evaluate_semantic_slam_non_dominated_proxy_output.py`
- Verify: `manifests/h001_semantic_slam_non_dominated_proxy_output_evaluation_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_non_dominated_proxy_output_evaluation_v1`
- Group evaluation rows: `50`
- `SemanticSLAMInteraction` rank-1 rows/rate: `42/0.84`
- `SemanticOnly` rank-1 rows/rate: `0/0.0`
- `SLAMOnly` rank-1 rows/rate: `8/0.16`
- `SemanticSLAMInteraction` strictly exceeds `SemanticOnly` on `50/50` groups.
- Diagnostic classes: `semantic_first_bonus_shadows_semantic_only 36`, `interaction_overrides_slam_component 6`, `interaction_loses_to_component 8`
- Output evaluation integrity gate: `true`
- Reviewer-defense gate: `false`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The non-dominated proxy repair is structurally useful but not yet paper-defensible. The current formula creates semantic-first additive shadowing because `SemanticSLAMInteraction` is always `SemanticOnly` plus a nonnegative interaction bonus. This makes the high rank-1 rate a design-risk signal, not a complementarity result.

### Next Contract Requirements

The next reviewer-defense contract should choose one primary path before Step 4-5 promotion:

- Stricter cap: prevent `SemanticSLAMInteraction` from strictly shadowing `SemanticOnly` on all rows unless task/map outcome evidence is available.
- Richer SLAM proxy: replace the current scalar `slam_gap_score` with a map/pose outcome proxy that can independently explain benefit.
- Task/map outcome validation: link the proxy to `wrong-goal visit`, `wasted path`, map error, semantic accuracy, ATE/RPE, or pose graph connectivity before any paper claim.

## SemanticSLAMInteraction Reviewer-Defense Path Decision

### 사실

- Date checked: `2026-06-04`
- Current additive `SemanticSLAMInteraction` output evaluation has request groups `50`.
- `SemanticSLAMInteraction` rank-1 rows/rate: `42/0.84`
- `SemanticOnly` rank-1 rows/rate: `0/0.0`
- `SLAMOnly` rank-1 rows/rate: `8/0.16`
- `SemanticSLAMInteraction` strictly exceeds `SemanticOnly` on `50/50` groups.
- Diagnostic classes: `semantic_first_bonus_shadows_semantic_only 36`, `interaction_overrides_slam_component 6`, `interaction_loses_to_component 8`
- Output evaluation integrity gate: `true`
- Reviewer-defense gate: `false`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The best next path is not a cap-only patch. A stricter cap can stop the current all-row shadowing failure, but it does not by itself create a paper-facing mechanism. A task/map outcome validation is ultimately required, but running it directly on the current additive utility would validate a known shadowing-prone design. Therefore the next contract should use a richer SLAM/outcome-linked proxy as the primary design, with a non-shadowing cap as a guard and task/map outcome validation as the promotion gate.

### Decision

Primary path: richer SLAM/outcome-linked proxy.

Guard path: stricter non-shadowing cap.

Promotion path: task/map outcome validation.

Rejected as primary path:

- Cap-only redesign: too easy to tune and weak as novelty.
- Direct task/map validation of the current additive proxy: risks validating semantic-first bonus rather than semantic-SLAM complementarity.

### Next Contract Requirements

The next frozen contract should require:

- `SemanticSLAMInteraction` must not be expressible as `SemanticOnly + nonnegative bonus` on every row.
- Any interaction gain over `SemanticOnly` must be justified by an independent map/pose-side signal, not by semantic family weight alone.
- The SLAM term should use richer map/pose proxies such as pose graph connectivity change, loop-edge availability, connected-component fragmentation, source-view coverage, or pre/post map consistency.
- A stricter cap should be diagnostic, not the main method: if `SemanticOnly` is shadowed on all rows again, the contract fails unless task/map outcome evidence is already attached.
- Promotion to Step 4-5 requires at least one map-side metric and one task-side metric, for example pose graph connectivity plus wrong-goal visit or wasted path.
- `first_eval`, policy-scale comparison, terminal utility, and paper claims remain blocked until this reviewer-defense contract and its Docker output pass.

## SemanticSLAM Reviewer-Defense Contract Freeze

### 사실

- Date checked: `2026-06-05`
- Contract: `manifests/h001_semantic_slam_reviewer_defense_contract_v1.json`
- Verify: `manifests/h001_semantic_slam_reviewer_defense_contract_v1.verify.json`
- Status: frozen contract before implementation
- Stage: `P4-design`
- Request groups: `50`
- Expected future comparison rows: `200`
- Policies: `NoReobserveReference`, `SemanticOnly`, `SLAMOnlyRich`, `SemanticSLAMInteractionGuarded`
- Primary path: richer SLAM/outcome-linked proxy
- Guard path: stricter non-shadowing cap
- Promotion path: task/map outcome validation
- Previous failure captured: `SemanticSLAMInteraction` rank-1 `42/50`, `SemanticOnly` shadowed `50/50`, reviewer-defense gate `false`
- Main forbidden pattern: `SemanticOnly + nonnegative bonus` on every row
- Additional forbidden patterns: cap-only contribution, component-max shortcut, candidate-overlap pose evidence, label-tuned weight search
- Required map/pose terms: fragmentation, largest-component gap, loop gap, source coverage gap, context gap
- Required gates: max semantic shadowing rate without outcome `0.85`, max interaction rank-1 rate without outcome `0.75`, max unexplained positive bonus rows `0`, min map-pose explained interaction rows `10`
- Future implementation target: `runtime/h001_runtime/compare_semantic_slam_reviewer_defense_proxy.py`
- Future output: `local_dataset/runs/h001_semantic_slam_reviewer_defense_v1`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract converts the previous semantic-first shadowing failure into an implementable reviewer-defense gate. The next implementation must show that interaction gain is explained by map/pose-side evidence and must fail if it reproduces the all-row `SemanticOnly` shadowing pattern.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, or SLAM benefit claim is allowed from this contract alone.

## SemanticSLAM Reviewer-Defense Implementation

### 사실

- Date checked: `2026-06-05`
- Implementation: `runtime/h001_runtime/compare_semantic_slam_reviewer_defense_proxy.py`
- Contract / verify: `manifests/h001_semantic_slam_reviewer_defense_contract_v1.json`, `manifests/h001_semantic_slam_reviewer_defense_contract_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_reviewer_defense_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker compile/run: passed
- Comparison / policy summary / diagnostic rows: `200 / 4 / 50`
- Request groups: `50`
- Policy rank-1 rows / rates:
  - `SemanticSLAMInteractionGuarded`: `37 / 0.74`
  - `SemanticOnly`: `10 / 0.20`
  - `SLAMOnlyRich`: `3 / 0.06`
  - `NoReobserveReference`: `0 / 0.0`
- `SemanticOnly` shadowed by interaction rows / rate: `40 / 0.80`
- Map-pose explained interaction rows / rate: `40 / 0.80`
- Interaction rank-1 rows / rate: `37 / 0.74`
- Unexplained positive bonus rows: `0`
- Map-pose outcome proxy positive rows: `47`
- Canonical / loop proxy ready rates: `0.92 / 0.72`
- Action forbidden keys: `0`
- Terminal / candidate commit / candidate rejection rows: `0 / 0 / 0`
- `uses_gt_for_action`: `false`
- Reviewer-defense gate: `false`
- Failed gate: `SLAMOnlyRich` rank-1 rows are `3`, below frozen minimum `5`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The guarded interaction no longer reproduces the prior all-row `SemanticOnly` shadowing failure: shadowing is `40/50`, below the frozen maximum `0.85`, and interaction rank-1 is `37/50`, below the frozen maximum `0.75`. However, the independent SLAM-side component is still weak because `SLAMOnlyRich` wins only `3/50` groups. This means the current richer proxy is better behaved than the additive proxy, but not yet strong enough to support Step 4-5 promotion or a semantic-SLAM complementarity claim.

The next evaluation should inspect whether the failed `SLAMOnlyRich` gate is caused by proxy scaling, request-pool composition, missing map-side outcome terms, or real absence of independent SLAM utility. The next step should be diagnostic evaluation, not weight tuning or paper-scale rerun.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, or policy-scale comparison claim is allowed from this implementation output.

## SemanticSLAM Reviewer-Defense Output Evaluation

### 사실

- Date checked: `2026-06-05`
- Implementation: `runtime/h001_runtime/evaluate_semantic_slam_reviewer_defense_output.py`
- Verify: `manifests/h001_semantic_slam_reviewer_defense_output_evaluation_v1.verify.json`
- Input: `local_dataset/runs/h001_semantic_slam_reviewer_defense_v1`
- Output: `local_dataset/runs/h001_semantic_slam_reviewer_defense_output_evaluation_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker compile/run: passed
- Evaluation rows: `50`
- Action-safety gate: `true`
- Comparison gate: `true`
- Reviewer-defense output gate: `false`
- Primary blocker: `slam_only_rich_underpowered`
- `SLAMOnlyRich` rank-1 rows / required / deficit: `3 / 5 / 2`
- `SemanticSLAMInteractionGuarded` rank-1 rows / rate: `37 / 0.74`
- `SemanticOnly` shadowed rows / rate: `40 / 0.80`
- Map-pose explained interaction rows: `40`
- Unexplained positive bonus rows: `0`
- Blocker classes:
  - `semantic_wins_but_guarded_interaction_adds_small_map_pose_bonus`: `29`
  - `semantic_wins_with_weak_map_pose_proxy`: `17`
  - `slam_only_wins_but_insufficient_count`: `3`
  - `interaction_overrides_slam_component`: `1`
- `slam_minus_semantic_utility` min / mean / max: `-0.84 / -0.3230 / 0.1483`
- `map_pose_outcome_proxy` min / mean / max: `0.0 / 0.3646 / 0.8083`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The evaluation confirms that the guarded proxy fixed the most obvious reviewer objection from the additive proxy: it no longer shadows `SemanticOnly` on every row, interaction rank-1 stays under the frozen cap, and unexplained positive bonus rows remain `0`. The remaining blocker is not action leakage or row mismatch. It is that the independent map/pose component is too weak relative to semantic utility on most rows: `SemanticOnly` is the component winner for `46/50` rows, and `SLAMOnlyRich` is rank-1 on only `3/50`.

The next step should diagnose whether this is caused by utility scaling, request-pool composition, saturated source coverage/context terms, missing map-side outcome terms, or genuine absence of independent SLAM utility in the current proxy source. Formula changes, threshold tuning, `first_eval`, and policy-scale comparison remain premature.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, or policy-scale comparison claim is allowed from this output evaluation.

## SemanticSLAM SLAMOnlyRich Underpowered Diagnostic

### 사실

- Date checked: `2026-06-05`
- Implementation: `runtime/h001_runtime/diagnose_semantic_slam_slam_only_rich_underpowered.py`
- Verify: `manifests/h001_semantic_slam_slam_only_rich_underpowered_diagnostic_v1.verify.json`
- Input: `local_dataset/runs/h001_semantic_slam_reviewer_defense_v1` and `local_dataset/runs/h001_semantic_slam_reviewer_defense_output_evaluation_v1`
- Output: `local_dataset/runs/h001_semantic_slam_slam_only_rich_underpowered_diagnostic_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker compile/run: passed
- Diagnostic/query/scene rows: `50 / 6 / 9`
- Diagnostic gate: `true`
- Rank-1 rows/rates:
  - `SLAMOnlyRich`: `3 / 0.06`
  - `SemanticOnly`: `10 / 0.20`
  - `SemanticSLAMInteractionGuarded`: `37 / 0.74`
- Dominant causes:
  - `map_pose_terms_saturated`: `19`
  - `weak_map_pose_proxy`: `17`
  - `near_miss_scale`: `8`
  - `positive_slam_cases_too_sparse`: `3`
  - `mixed_or_request_pool_effect`: `3`
- Saturated map-pose term rows/rate: `46 / 0.92`
- Weak map-pose proxy rows/rate: `17 / 0.34`
- Scale near-miss rows/rate: `12 / 0.24`
- `slam_scale_needed_to_match_semantic_score` min/mean/max: `0.8140 / 2.4315 / 16.5333`
- `map_pose_outcome_proxy` min/mean/max: `0.0 / 0.3646 / 0.8083`
- Primary conclusion: `semantic_score_dominates_current_map_pose_proxy`
- Secondary conclusion: `map_pose_terms_often_saturated_or_weak_without_task_map_outcome`
- Formula change allowed: `false`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This diagnostic rejects immediate scale tuning. The `SLAMOnlyRich` deficit is not just a two-row threshold issue: most rows either have saturated map/pose terms, weak map/pose outcome proxy, or semantic scores that dominate the current map/pose proxy. The next gate should freeze a `SLAMOnlyRich` revision contract that separates scale-only tuning from outcome-linked map/pose evidence.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, or paper claim is allowed from this diagnostic.

## SemanticSLAM SLAMOnlyRich Revision Contract

### 사실

- Date checked: `2026-06-05`
- Contract: `manifests/h001_semantic_slam_slam_only_rich_revision_contract_v1.json`
- Verify: `manifests/h001_semantic_slam_slam_only_rich_revision_contract_v1.verify.json`
- Status: frozen contract before any revised utility formula
- Source diagnostic: `semantic_slam_slam_only_rich_underpowered_diagnostic_v1`
- Source `SLAMOnlyRich` rank-1 rows/rate: `3 / 0.06`
- Saturated map-pose term rows/rate: `46 / 0.92`
- Weak map-pose proxy rows/rate: `17 / 0.34`
- Primary cause: `semantic_score_dominates_current_map_pose_proxy`
- Secondary cause: `map_pose_terms_often_saturated_or_weak_without_task_map_outcome`
- Scale-only tuning allowed: `false`
- Revised formula implementation allowed now: `false`
- Next allowed work: `define_small_task_map_outcome_probe_contract`
- Required next probe minimum:
  - one map-side metric
  - one task-side metric
  - baselines: `SemanticOnly`, `SLAMOnlyRich_current`, `NoReobserveReference`
  - failure taxonomy
  - allowed/forbidden input contract
- Forbidden patterns:
  - multiply `SLAMOnlyRich` score by a constant
  - weaken semantic score to help `SLAMOnlyRich`
  - tune request pool so `SLAMOnlyRich` wins
  - use candidate correctness or wrong-goal labels for action
  - use candidate-overlap as pose evidence
  - make terminal or policy-scale claim from proxy-only evidence
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The revision contract turns the underpowered diagnostic into a reviewer-defense rule: the next method step cannot be a scale patch. The required task/map outcome probe, task proxy join, and safe-but-sparse selector diagnostic are Docker-implemented; formula revision remains blocked because simple label-free geometry alternatives reintroduce wrong-goal and no-valid commits.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, or paper claim is allowed from this contract.

## SemanticSLAM Task/Map Outcome Probe Contract

### 사실

- Date checked: `2026-06-05`
- Contract: `manifests/h001_semantic_slam_task_map_outcome_probe_v1.json`
- Verify: `manifests/h001_semantic_slam_task_map_outcome_probe_v1.verify.json`
- Status: frozen contract
- Source contract: `semantic_slam_slam_only_rich_revision_contract_v1`
- Request group rule: same `50` request groups
- Required baselines: `NoReobserveReference`, `SemanticOnly`, `SLAMOnlyRich_current`
- Map-side metrics:
  - `pose_graph_connectivity_delta`
  - `map_pose_consistency_delta`
- Task-side metrics:
  - `wrong_goal_visit_proxy_delta`
  - `wasted_path_proxy_delta`
- Bridge metrics:
  - `map_task_alignment_rate`
  - `slam_independent_value_rows`
- Required future output root: `local_dataset/runs/h001_semantic_slam_task_map_outcome_probe_v1`
- Action/evaluation input separation: frozen
- Failure taxonomy count: `7`
- Task/map outcome probe implementation allowed: `true`
- Revised `SLAMOnlyRich` formula implementation allowed now: `false`
- Step 4-5 promotion allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract closed the previous contract-definition TODO and led to the Docker implementation below. The probe must check whether strict map/pose evidence aligns with wrong-goal and wasted-path proxies before any `SLAMOnlyRich` formula is revised. If map metrics improve but task-side proxies do not, pose graph connectivity should not be presented as navigation utility.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, or paper claim is allowed from this contract.

## SemanticSLAM Task/Map Outcome Probe Implementation

### 사실

- Date checked: `2026-06-05`
- Script: `runtime/h001_runtime/evaluate_semantic_slam_task_map_outcome_probe.py`
- Verify: `manifests/h001_semantic_slam_task_map_outcome_probe_v1.verify.json`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Output root: `local_dataset/runs/h001_semantic_slam_task_map_outcome_probe_v1`
- Probe / policy summary / failure rows: `150 / 3 / 50`
- Request groups: `50`
- Required policies present: `NoReobserveReference`, `SemanticOnly`, `SLAMOnlyRich_current`
- `SLAMOnlyRich_current` map-positive rows: `50 / 50`
- Label-backed task proxy rows: `0 / 50`
- Label-free risk proxy rows: `50 / 50`
- Map-task alignment rows: `0`
- Failure taxonomy: `map_delta_not_task_aligned 50`
- Secondary failure: `task_proxy_label_join_missing 50`
- Action forbidden keys: `0`
- Terminal / candidate commit / candidate rejection rows: `0 / 0 / 0`
- `uses_gt_for_action`: `false`
- `outcome_probe_gate_passed`: `false`
- `revised_slam_formula_allowed`: `false`
- `paper_claim_allowed`: `false`

### 에이전트 추론

The implementation confirms that strict map/pose evidence can be joined to the same `50` request groups and produces nonzero map-side deltas. However, the current artifacts do not include separated label-backed `wrong_goal_visit` or `wasted_path` task proxies. Therefore the failure is not evidence against semantic-SLAM utility yet; it is a measurement blocker. The next defensible step is a task-label join contract that defines evaluation-only labels and deltas without allowing those labels into action-time policy.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed from this failed gate.

## SemanticSLAM Task Label Join Materializer

### 사실

- Date checked: `2026-06-05`
- Contract: `manifests/h001_semantic_slam_task_label_join_v1.json`
- Verify: `manifests/h001_semantic_slam_task_label_join_v1.verify.json`
- Script: `runtime/h001_runtime/materialize_semantic_slam_task_label_join.py`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Output root: `local_dataset/runs/h001_semantic_slam_task_label_join_v1`
- Request / candidate / policy / failure rows: `21 / 113 / 150 / 150`
- Candidate labels: correct `37`, wrong `76`, unlabeled `0`
- No-valid request pools: `4`
- Label backbone join rows: `150`
- Candidate label join rows: `150`
- Task proxy evaluable rows: `0`
- Policy selector missing rows: `150`
- Action forbidden keys: `0`
- `uses_gt_for_action`: `false`
- `task_label_join_gate_passed`: `true`
- `outcome_proxy_gate_passed`: `false`
- `revised_slam_formula_allowed`: `false`
- `paper_claim_allowed`: `false`

### 에이전트 추론

The label coverage blocker is resolved, but this stage still lacked a frozen non-GT policy selector with `policy_selected_candidate_id` and `terminal_commit_proxy`. Later selector, task-proxy-join, safe-but-sparse diagnostic, and geometry-only closure sections below resolve that measurement blocker and close the current geometry-only `SLAMOnlyRich_current` path as non-promotable. It is still not valid to revise the `SLAMOnlyRich` formula or claim task/map benefit.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, or paper claim is allowed from this materializer.

## SemanticSLAM Task Policy Selector Contract

### 사실

- Date checked: `2026-06-05`
- Contract: `manifests/h001_semantic_slam_task_policy_selector_v1.json`
- Verify: `manifests/h001_semantic_slam_task_policy_selector_v1.verify.json`
- Status: frozen contract
- Source action feature backbone: `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1/expanded_retrieval_local_context_route_specific_evaluated_rows.jsonl`
- Unique request keys: `21`
- Source request rows: `50`
- Source policy rows: `150`
- `NoReobserveReference` selector: `source_top_direct_commit_v1`
- Expected `NoReobserveReference` terminal commits on expanded source rows: `49 / 50`
- `SemanticOnly` selector: `local_context_then_unique_own_view_v1`
- Expected `SemanticOnly` terminal commits on expanded source rows: `41 / 50`
- `SLAMOnlyRich_current` selector: `candidate_specific_slam_selector_missing_v1`
- Expected `SLAMOnlyRich_current` selector-missing rows: `50 / 50`
- Forbidden action inputs include `evaluation_candidate_summary`, `evaluation_only_variant_outcomes`, correctness labels, wrong-goal labels, no-valid labels, oracle fields, and shortest-path labels.
- Forbidden shortcut: source-top, semantic-top, detector-best, local-context, or any other semantic selector cannot be substituted for `SLAMOnlyRich_current`.
- Policy selector materializer allowed: `true`
- Candidate-specific SLAM selector contract allowed: `true`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The selector contract can make `NoReobserveReference` and `SemanticOnly` task proxies evaluable in the next materializer, but it intentionally leaves `SLAMOnlyRich_current` unevaluable as a candidate selector. This is the conservative top-tier path: row-level map/pose utility is not the same as a candidate-specific navigation decision. A later candidate-specific SLAM/map-pose selector contract is required before formula revision can be considered.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this selector contract.

## SemanticSLAM Task Policy Selector Materializer

### 사실

- Date checked: `2026-06-05`
- Contract: `manifests/h001_semantic_slam_task_policy_selector_v1.json`
- Verify: `manifests/h001_semantic_slam_task_policy_selector_v1.verify.json`
- Script: `runtime/h001_runtime/materialize_semantic_slam_task_policy_selector.py`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Output root: `local_dataset/runs/h001_semantic_slam_task_policy_selector_v1`
- Selector / failure rows: `150 / 60`
- `NoReobserveReference` terminal commit proxy rows: `49 / 50`
- `SemanticOnly` terminal commit proxy rows: `41 / 50`
- `SemanticOnly` local-context / own-view commit sources: `23 / 18`
- `SLAMOnlyRich_current` selector-missing rows: `50 / 50`
- Total terminal commit / defer / selector-missing rows: `90 / 10 / 50`
- Action forbidden keys: `0`
- `uses_gt_for_action`: `false`
- `selector_contract_gate_passed`: `true`
- `partial_task_proxy_join_after_selector_allowed`: `true`
- Candidate-specific SLAM selector contract allowed: `true`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The materializer resolves selected-candidate / terminal-commit plumbing for `NoReobserveReference` and `SemanticOnly`, but intentionally preserves the real `SLAMOnlyRich_current` blocker. The next defensible gate is a candidate-specific SLAM/map-pose selector contract, because row-level map/pose utility still cannot choose an ObjectNav goal candidate.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this materializer.

## SemanticSLAM Candidate Map-Pose Selector Contract

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_candidate_map_pose_selector_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_map_pose_selector_v1.verify.json`
- Status: frozen contract verified
- Source inventory rows: `5`
- Source request rows: `50`
- Frame request keys: `50`
- Request keys without frame rows: `0`
- Frame rows total: `557`
- Candidate feature rows expected: `232`
- Candidate request groups: `50`
- Missing required candidate geometry fields: `0`
- Current `SLAMOnlyRich_current` selector-missing rows from upstream selector materializer: `50 / 50`
- Frozen selector id: `candidate_map_pose_unique_ready_v1`
- Selector rule: select only when exactly one candidate in the request is strict candidate-map-pose-ready; defer when zero or multiple candidates are ready.
- Forbidden selector evidence: semantic rank/score, detector score, source-top, local-context, `evaluation_only_variant_outcomes`, correctness labels, wrong-goal labels, no-valid labels, oracle fields, and task outcome fields.
- Candidate map-pose selector materializer allowed: `true`
- Task proxy join after candidate selector allowed: `true`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract converts the `SLAMOnlyRich_current` blocker from "no candidate-specific selector exists" into an implementable geometry-only measurement gate. It is intentionally conservative: geometry availability may expose candidate-specific map/pose evidence, but it cannot establish ObjectNav goal validity by itself. Ambiguous geometry must defer rather than fall back to semantic or detector shortcuts.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this contract.

## SemanticSLAM Candidate Map-Pose Selector Materializer Result

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/materialize_semantic_slam_candidate_map_pose_selector.py`
- Verify: `manifests/h001_semantic_slam_candidate_map_pose_selector_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_candidate_map_pose_selector_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker compile/run/artifact validation: passed
- Candidate / request / failure rows: `232 / 50 / 50`
- `SLAMOnlyRich_current` request rows: `50`
- Selector-missing rows: `0`
- Candidate geometry missing rows: `0`
- Strict candidate-map-pose-ready rows: `232`
- Geometry-only single-candidate commit rows: `3`
- Multi-ready defer rows: `47`
- Action forbidden key count: `0`
- `uses_gt_for_action`: `false`
- `candidate_map_pose_feature_gate_passed`: `true`
- `task_proxy_join_after_candidate_selector_allowed`: `true`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The materializer resolves the selector-missing blocker, but it also shows that candidate-specific map/pose evidence is mostly availability evidence: every candidate is strict-ready, so `47/50` requests remain ambiguous and must defer. The follow-up task proxy join and safe-but-sparse diagnostic confirm that this geometry-only signal is not yet candidate-discriminative enough for formula revision.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this materializer.

## SemanticSLAM Candidate Task Proxy Join Result

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/materialize_semantic_slam_candidate_task_proxy_join.py`
- Contract: `manifests/h001_semantic_slam_candidate_task_proxy_join_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_task_proxy_join_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_candidate_task_proxy_join_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker compile/run/artifact validation: passed
- Policy / failure rows: `150 / 100`
- Decision-evaluable task proxy rows: `150`
- Commit-evaluable task proxy rows: `93`
- Selector-missing rows: `0`
- `NoReobserveReference` terminal / success / wrong-goal rows: `49 / 28 / 21`
- `SemanticOnly` terminal / success / wrong-goal rows: `41 / 20 / 21`
- `SLAMOnlyRich_current` terminal / success / wrong-goal / defer / map-task alignment rows: `3 / 2 / 1 / 47 / 2`
- Action forbidden key count: `0`
- `uses_gt_for_action`: `false`
- `uses_gt_for_analysis`: `true`
- Task proxy join gate passed: `true`
- Formula revision unlock gate passed: `false`
- Primary blocker: `slam_only_terminal_commits_too_sparse`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The task proxy join resolves the measurement plumbing blocker: every policy decision now has label-backed evaluation proxies without using labels as action evidence. However, the conservative `SLAMOnlyRich_current` selector is safe-but-sparse. It reduces wrong-goal exposure mainly by deferring `47/50` rows, not by producing a nontrivial candidate-level map/pose utility. The next gate should diagnose whether label-free candidate map/pose evidence can become discriminative; formula revision remains premature.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this task proxy join.

## SemanticSLAM Safe-But-Sparse Selector Diagnostic Result

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/diagnose_semantic_slam_safe_sparse_selector.py`
- Contract: `manifests/h001_semantic_slam_safe_sparse_selector_diagnostic_v1.json`
- Verify: `manifests/h001_semantic_slam_safe_sparse_selector_diagnostic_v1.verify.json`
- Output: `local_dataset/runs/h001_semantic_slam_safe_sparse_selector_diagnostic_v1`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Docker compile/run/artifact validation: passed
- Request / alternative rows: `50 / 300`
- Candidate / source request rows: `232 / 50`
- Current unique-ready selector commit / success / wrong-goal / defer rows: `3 / 2 / 1 / 47`
- `top_map_pose_tuple` commit / success / wrong-goal / no-valid rows: `50 / 29 / 21 / 4`
- `top_projection_visible_heading` commit / success / wrong-goal / no-valid rows: `50 / 29 / 21 / 4`
- All-candidates-ready rows: `50`
- Multi-candidate all-ready rows: `47`
- Action forbidden key count: `0`
- `uses_gt_for_action`: `false`
- `uses_gt_for_analysis`: `true`
- Diagnostic gate passed: `true`
- Candidate separability gate passed: `false`
- Primary blocker: `label_free_geometry_alternatives_reintroduce_wrong_goal_risk`
- Discriminative candidate map/pose revision allowed: `false`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The current geometry-only candidate map/pose evidence is non-promotable under the frozen gates. It can make every candidate observable and can force all requests to commit with simple ranking rules, but those rules recreate wrong-goal and no-valid failures. A future `SLAMOnlyRich_current` revision must add candidate-relative evidence that separates same-category rivals, not just a larger weight on existing geometry availability features.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this diagnostic.

## SemanticSLAM Geometry-Only Closure Gate

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_geometry_only_closure_v1.json`
- Verify: `manifests/h001_semantic_slam_geometry_only_closure_v1.verify.json`
- Source diagnostic: `manifests/h001_semantic_slam_safe_sparse_selector_diagnostic_v1.verify.json`
- Closed path: `geometry_only_SLAMOnlyRich_current_selector`
- Closed status: `closed_as_non_promotable_under_current_evidence`
- Source request / candidate rows: `50 / 232`
- All-candidates-ready / multi-candidate all-ready rows: `50 / 47`
- Current unique-ready selector commit / success / wrong-goal / defer rows: `3 / 2 / 1 / 47`
- `top_map_pose_tuple` commit / success / wrong-goal / no-valid rows: `50 / 29 / 21 / 4`
- `top_projection_visible_heading` commit / success / wrong-goal / no-valid rows: `50 / 29 / 21 / 4`
- Action forbidden key count: `0`
- `uses_gt_for_action`: `false`
- Candidate-relative requirements defined: `true`
- Revised `SLAMOnlyRich` formula implementation allowed: `false`
- Terminal utility validation allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The geometry-only `SLAMOnlyRich_current` path is no longer an active method candidate under the current evidence. It is useful as a negative result: candidate map/pose availability can be measured without label leakage, but availability saturates across rivals and simple geometry tie-breakers recreate wrong-goal and no-valid commits.

The next `SemanticSLAM` step must freeze a candidate-relative map/pose evidence contract before any implementation. That contract must compare candidates within the same request group, use at least one map/pose-native relative term, preserve no-valid guarding, audit simpler alternatives, and join map-side and task-side proxies only after action rows are frozen.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this closure. A later claim requires a fresh candidate-relative evidence family that passes the frozen gates without semantic, detector, source-top, local-context, oracle, or label fallback shortcuts.

## SemanticSLAM Candidate-Relative Map/Pose Evidence Contract And Materializer

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_candidate_relative_map_pose_evidence_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_relative_map_pose_evidence_v1.verify.json`
- Status: `docker_materializer_verified_promotion_blocked`
- Source candidate / request group / candidate id counts: `232 / 50 / 43`
- All-ready candidate rows: `232`
- Map-pose source inventory / probe request / request-level pose graph rows: `5 / 50 / 50`
- Pose graph proxy ready / spatial-or-loop / candidate-overlap-only rows: `50 / 46 / 4`
- Strict edge variant / summary rows: `350 / 7`
- Strict canonical / loop / context ready rows: `46 / 36 / 46`
- Safe-sparse alternative rows: `300`
- Materializer script: `runtime/h001_runtime/materialize_semantic_slam_candidate_relative_map_pose_evidence.py`
- Docker output: `local_dataset/runs/h001_semantic_slam_candidate_relative_map_pose_evidence_v1`
- Materialized candidate / request / alternative / failure rows: `232 / 50 / 450 / 50`
- Candidate-relative unique-top / tie-or-saturation / single-candidate request rows: `42 / 5 / 3`
- Candidate-overlap-only request rows: `4`
- Action forbidden key count: `0`
- Terminal / candidate commit / candidate rejection rows: `0 / 0 / 0`
- Materializer gate passed: `true`
- Promotion gate after materialization passed: `false`
- Primary blocker: `task_side_proxy_not_joined_for_terminal_utility`
- Terminal commit allowed: `false`
- Candidate rejection allowed: `false`
- Formula revision allowed: `false`
- `uses_gt_for_action`: `false`
- Paper claim allowed: `false`
- Next contract target: task-side proxy join for candidate-relative map/pose evidence before terminal utility

### 에이전트 추론

The materializer is now implemented and passes the nonterminal evidence gate without action leakage. The result shows candidate-relative contrast exists in the current map/pose rows, but this is still not terminal utility because no task-side proxy has been joined to the relative evidence. The next contract should join frozen evidence rows to evaluation-only task proxies without allowing labels, semantic rank, detector score, source-top, or local-context fallback as action evidence.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this materializer. A later promotion requires a task-side proxy join that tests the materialized candidate-relative evidence against wrong-goal/no-valid risk after action rows are frozen.

## SemanticSLAM Candidate-Relative Task Proxy Join

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_candidate_relative_task_proxy_join_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_relative_task_proxy_join_v1.verify.json`
- Script: `runtime/h001_runtime/materialize_semantic_slam_candidate_relative_task_proxy_join.py`
- Output: `local_dataset/runs/h001_semantic_slam_candidate_relative_task_proxy_join_v1`
- Status: `docker_materializer_verified_promotion_blocked`
- Source candidate-relative candidate / request / alternative / failure rows: `232 / 50 / 450 / 50`
- Output candidate / request / alternative / baseline / failure rows: `232 / 50 / 450 / 150 / 50`
- Task label request / candidate rows: `21 / 113`
- Source-row request / candidate label missing rows: `0 / 0`
- Source candidate label correct / wrong / no-valid rows: `84 / 148 / 24`
- Top map-pose candidate correct / wrong / no-valid request rows: `29 / 21 / 4`
- Candidate-relative unique-top correct / wrong / no-valid request rows: `23 / 19 / 4`
- Candidate task-proxy policy rows: `150`
- Task proxy join gate passed: `true`
- Promotion gate after join passed: `false`
- Primary blocker: `candidate_relative_top_rule_wrong_goal_risk`
- Terminal commit allowed: `false`
- Candidate rejection allowed: `false`
- Formula revision allowed: `false`
- `uses_gt_for_action`: `false`
- `uses_gt_for_analysis`: `true`
- Paper claim allowed: `false`

### 에이전트 추론

The Docker materializer verifies full evaluation-only label coverage and materializes the risk as row-level failure taxonomy. A direct top-map-pose or unique-top candidate-relative rule would still include wrong-goal and no-valid cases. The current path should be closed or revised before any `SLAMOnlyRich_current` formula change.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this artifact.

## SemanticSLAM Candidate-Relative Path Closure

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_candidate_relative_path_closure_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_relative_path_closure_v1.verify.json`
- Status: `static_closure_verified`
- Closed path: `candidate_relative_map_pose_top_rule_as_terminal_selector`
- Closed status: `closed_as_non_promotable_under_task_proxy_join`
- Source candidate / request / alternative / baseline / failure rows: `232 / 50 / 450 / 150 / 50`
- Source-row request / candidate label missing rows: `0 / 0`
- Top map-pose candidate correct / wrong / no-valid rows: `29 / 21 / 4`
- Candidate-relative unique-top correct / wrong / no-valid rows: `23 / 19 / 4`
- Candidate-relative tie-or-saturation rows: `5`
- Single-candidate geometry-only rows: `3`
- Candidate-overlap-only request rows: `4`
- Primary blocker: `candidate_relative_top_rule_wrong_goal_risk`
- Active-observation revision requirements defined: `true`
- Formula revision allowed: `false`
- Terminal utility validation allowed: `false`
- `first_eval` rerun allowed: `false`
- Policy-scale comparison allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

The candidate-relative path should not be revised into a terminal selector. The useful signal is that map/pose contrast exposes uncertainty and rival ambiguity. The follow-up active-observation utility contract below freezes observe/defer priority as the next method step and keeps task proxies after action rows are frozen.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this closure.

## SemanticSLAM Candidate-Relative Active-Observation Utility Contract

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_candidate_relative_active_observation_utility_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_relative_active_observation_utility_v1.verify.json`
- Status: `static_contract_verified`
- Source closure: `manifests/h001_semantic_slam_candidate_relative_path_closure_v1.json`
- Source request / candidate / alternative / baseline / failure rows: `50 / 232 / 450 / 150 / 50`
- Top map-pose correct / wrong / no-valid rows: `29 / 21 / 4`
- Candidate-relative unique-top correct / wrong / no-valid rows: `23 / 19 / 4`
- Allowed action outputs: `observe_candidate`, `observe_candidate_pair`, `observe_request_context`, `defer_observation`, `audit_only`
- Required next output root: `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_utility_v1`
- Required next script: `runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_utility.py`
- Terminal commit allowed: `false`
- Candidate commit / rejection allowed: `false / false`
- Formula revision allowed: `false`
- `first_eval` rerun allowed: `false`
- Policy-scale comparison allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract freezes the method-direction shift forced by the task proxy join. Candidate-relative map/pose contrast can rank what to observe next, but cannot act as ObjectNav goal-validity authority. The Docker materializer below consumes this contract and preserves action/evaluation separation.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this contract. A later claim requires Docker materialization, post-action task proxy join, and held-out or fresh validation.

## SemanticSLAM Candidate-Relative Active-Observation Utility Materializer

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_utility.py`
- Verify: `manifests/h001_semantic_slam_candidate_relative_active_observation_utility_v1.verify.json`
- Docker output: `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_utility_v1`
- Status: `docker_materializer_verified_promotion_blocked`
- Output priority / request / alternative / failure rows: `232 / 50 / 300 / 50`
- Request action counts: `observe_request_context 21`, `observe_candidate_pair 26`, `observe_candidate 3`
- Candidate action counts: `observe_request_context 113`, `observe_candidate_pair 52`, `observe_candidate 19`, `audit_only 48`
- Terminal commit / candidate commit / candidate rejection rows: `0 / 0 / 0`
- `uses_gt_for_action` true rows: `0`
- Action forbidden key count: `0`
- Active-observation materializer gate passed: `true`
- Promotion gate after materialization passed: `false`
- Primary blocker: `task_proxy_join_after_active_observation_action_freeze_required`
- Next contract target: active-observation task-proxy join after action rows are frozen

### 에이전트 추론

The materializer converts the closed top-rule failure into nonterminal observation pressure. It does not solve goal validity. The next falsifiable step is to join these frozen observation actions to task proxies and test whether the proposed active-observation priorities explain wrong-goal/no-valid risk without using labels to choose the action.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this materializer.

## SemanticSLAM Candidate-Relative Active-Observation Task-Proxy Join Contract

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.json`
- Verify: `manifests/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.verify.json`
- Status: `static_contract_verified`
- Source active-observation priority / request / alternative / failure rows: `232 / 50 / 300 / 50`
- Selected candidate eval rows: `97`
- Alternative rows with audit-selected candidate: `100`
- Selected request action counts: `observe_request_context 21`, `observe_candidate_pair 26`, `observe_candidate 3`
- Task label request / candidate rows: `21 / 113`
- Candidate task-proxy policy rows: `150`
- Required next script: `runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_task_proxy_join.py`
- Required next output root: `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1`
- Terminal commit allowed: `false`
- Candidate commit / rejection allowed: `false / false`
- Label-tuned action revision allowed: `false`
- Formula revision allowed: `false`
- `first_eval` rerun allowed: `false`
- Policy-scale comparison allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract makes the next join a measurement step only. The selected observation actions and candidate sets are frozen before labels are joined. The implementation should measure request-level and selected-candidate risk, but it must not change observation actions, create terminal utility, reject candidates, or tune thresholds from the joined labels.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this contract.

## SemanticSLAM Candidate-Relative Active-Observation Task-Proxy Join Materializer

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_task_proxy_join.py`
- Verify: `manifests/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.verify.json`
- Docker output: `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1`
- Status: `active_observation_task_proxy_join_gate_passed_promotion_blocked`
- Output priority / selected candidate / request / alternative / baseline / failure rows: `232 / 97 / 50 / 300 / 150 / 50`
- Request label missing rows: `0`
- Priority candidate label missing rows: `0`
- Selected candidate label missing rows: `0`
- Alternative audit-selected candidate rows / missing labels: `100 / 0`
- Selected candidate labels: correct `43`, wrong `54`, no-valid pool `8`
- Request action risk counts: `observe_candidate` selected correct/wrong `2/1`; `observe_candidate_pair` selected correct/wrong `22/30`; `observe_request_context` selected correct/wrong/no-valid request pools `19/23/4`
- Baseline context rows: `NoReobserveReference 50`, `SemanticOnly 50`, `SLAMOnlyRich_current 50`
- Baseline wrong-goal proxy rows: `NoReobserveReference 21`, `SemanticOnly 21`, `SLAMOnlyRich_current 1`
- Terminal commit / candidate commit / candidate rejection rows: `0 / 0 / 0`
- `uses_gt_for_action` true rows: `0`
- Action forbidden key count on frozen active-observation input rows: `0`
- Active-observation task-proxy join gate passed: `true`
- Promotion gate after join passed: `false`
- Primary blocker: `active_observation_task_proxy_join_is_evaluation_only`
- Next target: analyze active-observation task-proxy join result before terminal utility

### 에이전트 추론

The join validates measurement coverage after action freeze and shows that selected observation targets are strongly enriched for wrong/no-valid risk. However, this is still an evaluation-only diagnosis. A terminal utility contract should not be defined until a label-free decision rule is shown to convert this risk profile into a promotable action without using joined labels.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this materializer.

## SemanticSLAM Active-Observation Risk Analysis

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/analyze_semantic_slam_active_observation_risk.py`
- Verify: `manifests/h001_semantic_slam_active_observation_risk_analysis_v1.verify.json`
- Docker output: `local_dataset/runs/h001_semantic_slam_active_observation_risk_analysis_v1`
- Status: `risk_analysis_gate_passed_terminal_utility_blocked`
- Output request / candidate / rule audit rows: `50 / 232 / 6`
- Selected request status counts: all-correct `11`, mixed-correct-wrong `23`, all-wrong `12`, no-valid pool `4`
- Selected candidate clean-correct / wrong-or-no-valid rows: `43 / 54`
- Utility score `AUROC` for wrong/no-valid risk over priority candidates: `0.5117`
- `top_observation_utility_if_misused_as_terminal`: success / wrong / no-valid `16 / 30 / 4`
- `top_selected_observation_utility_if_misused_as_terminal`: success / wrong / no-valid `19 / 27 / 4`
- `defer_all_after_risk_detection`: success / wrong / no-valid `0 / 0 / 0`
- Risk analysis gate passed: `true`
- Terminal utility contract allowed: `false`
- Primary blocker: `top_observation_utility_terminal_shortcut_unsafe`
- Next target: active-observation post-update evaluation join contract

### 에이전트 추론

The active-observation utility is a risk-acquisition signal, not a terminal goal selector. The selected candidates are enriched for ambiguous/wrong risk, and the top utility shortcut is unsafe if interpreted as a commit policy. The post-observation update contract below now defines how label-free evidence may change candidate state before any terminal utility is reconsidered.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this analysis.

## SemanticSLAM Active-Observation Post-Observation Evidence Update Contract

### 사실

- Date checked: `2026-06-06`
- Contract: `manifests/h001_semantic_slam_active_observation_post_update_v1.json`
- Verify: `manifests/h001_semantic_slam_active_observation_post_update_v1.verify.json`
- Status: `static_contract_verified_implementation_pending`
- Source risk request / candidate / rule audit rows: `50 / 232 / 6`
- Frozen selected candidate rows: `97`
- Selected request status counts: all-correct `11`, mixed-correct-wrong `23`, all-wrong `12`, no-valid pool `4`
- Selected candidate clean-correct / wrong-or-no-valid rows: `43 / 54`
- Required post-update request / selected-candidate / candidate-state rows: `50 / 97 / 232`
- Required rule audit rows: at least `6`
- Terminal commit / candidate commit / candidate rejection allowed: `0 / 0 / 0`
- Label join allowed only after post-update row freeze: `true`
- Required next script: `runtime/h001_runtime/materialize_semantic_slam_active_observation_post_update.py`
- Required next output: `local_dataset/runs/h001_semantic_slam_active_observation_post_update_v1`
- Formula revision allowed: `false`
- `first_eval` rerun allowed: `false`
- Policy-scale comparison allowed: `false`
- Paper claim allowed: `false`

### 에이전트 추론

This contract converts the risk-analysis result into a method step: `observe_candidate`, `observe_candidate_pair`, and `observe_request_context` may update label-free evidence state, but cannot decide goal validity. A valid implementation must produce `pre_observation_state`, `observation_evidence`, `post_observation_state`, and `evidence_delta` without using correctness labels, wrong-goal proxies, or oracle fields as action/update inputs.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this contract. A later claim requires Docker materialization, post-update evaluation join, and held-out or fresh validation.

## SemanticSLAM Active-Observation Post-Observation Evidence Update Materializer

### 사실

- Date checked: `2026-06-06`
- Script: `runtime/h001_runtime/materialize_semantic_slam_active_observation_post_update.py`
- Verify: `manifests/h001_semantic_slam_active_observation_post_update_v1.verify.json`
- Docker output: `local_dataset/runs/h001_semantic_slam_active_observation_post_update_v1`
- Status: `post_update_materializer_gate_passed_promotion_blocked`
- Output request / selected candidate / candidate state / rule audit / failure rows: `50 / 97 / 232 / 6 / 50`
- Selected candidate evidence delta rows: `97`
- Candidate-state evidence delta rows: `97`
- Request post-update states: `ambiguity_reduced 26`, `needs_goal_validity_confirmation 21`, `support_acquired 3`
- Selected candidate post states: `ambiguity_reduced 52`, `needs_goal_validity_confirmation 42`, `support_acquired 3`
- Terminal commit / candidate commit / candidate rejection rows: `0 / 0 / 0`
- `uses_gt_for_action` true rows: `0`
- Action forbidden key count: `0`
- Post-update materializer gate passed: `true`
- Promotion gate after post-update passed: `false`
- Primary blocker: `post_update_label_join_and_goal_validity_arbitration_required`
- Next target: post-update evaluation join contract

### 에이전트 추론

The materializer makes the method state transition explicit: active observation updates evidence state but still does not decide ObjectNav goal validity. The next measurement step should join evaluation labels only after these update rows are frozen, then test whether post-update states can support any non-GT arbitration rule without converting support acquisition or missing support into a shortcut.

### 논문 주장

No `SemanticSLAM` complementarity, ObjectNav benefit, SLAM benefit, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, or paper claim is allowed from this materializer.

## User Decision Needed

- Choose the accepted `SPL` drop threshold for first probe success.
- Choose whether first Docker runtime should extend `VLMaps` or start from Habitat ObjectNav runtime directly.
