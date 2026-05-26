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

Promotion gate beyond this first fresh source:

```text
request_rows >= 20
request_scenes >= 5
request_queries >= 3
at least one non-furniture or small-object query
same frozen analyzer and thresholds
failure taxonomy reported for all unresolved rows
```

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
