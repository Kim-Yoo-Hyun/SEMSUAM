# Dense Conflict Validation

## Purpose

### 사실

Current dense backend result is a local two-row `y9hTuugGdiq/chair` diagnostic. It recovered correct dense candidates and produced detector-backed commits under post-hoc GT analysis labels, but every positive-support candidate was also post-hoc correct.

### 에이전트 추론

This does not prove wrong-goal repair utility. The next validation must test rows where correct and wrong candidates both receive positive detector/depth support, because that is the actual failure mode a top-tier paper claim must survive.

## Validation Question

If a dense non-GT candidate backend provides both correct and wrong positively supported candidates, can the terminal active-observation objective choose a correct candidate without increasing wrong-goal commits, compared with defer-only, first-external, and detector-score-only alternatives?

## Target Row Contract

### Primary Independent Set

Use scene/category rows from `v3_fresh_validation_v1`, not the previous two `y9hTuugGdiq/chair` dense diagnostic.

Source evidence:

```text
/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_evidence/external_candidate_second_stage_identity_evidence_rows.jsonl
```

Frozen source rows:

| Episode key | Query | Scene | Conflict reason |
| --- | --- | --- | --- |
| `HM3D ObjectNav v2:val:DYehNKdT76V:22:4:chair` | `chair` | `DYehNKdT76V` | correct positive `1`, wrong positive `5`, unresolved |
| `HM3D ObjectNav v2:val:HY1NcmCgn3n:1:1:plant` | `plant` | `HY1NcmCgn3n` | correct positive `2`, wrong positive `4` |
| `HM3D ObjectNav v2:val:7MXmsvcQjpJ:26:0:plant` | `plant` | `7MXmsvcQjpJ` | selected wrong positive, correct positive present |
| `HM3D ObjectNav v2:val:HY1NcmCgn3n:8:8:plant` | `plant` | `HY1NcmCgn3n` | correct positive `2`, wrong positive `4` |
| `HM3D ObjectNav v2:val:7MXmsvcQjpJ:5:2:plant` | `plant` | `7MXmsvcQjpJ` | selected wrong positive, correct positive present |
| `HM3D ObjectNav v2:val:7MXmsvcQjpJ:23:3:plant` | `plant` | `7MXmsvcQjpJ` | selected wrong positive, correct positive present |

Selection facts:

```text
rows: 6
scenes: 3
queries: chair, plant
rows_with_correct_and_wrong_positive_support: 6 / 6
rows_with_wrong_positive_support: 6 / 6
rows_with_selected_wrong_positive_support: 3 / 6
uses_gt_for_action: false
uses_gt_for_analysis: true
```

### Secondary Repeated-Object Stress Set

Use only as stress evidence, not as the sole promotion evidence, because it is in `y9hTuugGdiq`.

Source evidence:

```text
/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_evidence_v4/external_candidate_second_stage_identity_evidence_rows.jsonl
```

Rows:

```text
HM3D ObjectNav v2:val:y9hTuugGdiq:11:1:sofa
HM3D ObjectNav v2:val:y9hTuugGdiq:5:4:sofa
```

Facts:

```text
rows: 2
query: sofa
rows_with_correct_and_wrong_positive_support: 2 / 2
current local-context V4 commits: 2 / 2 correct, 0 wrong
status: repeated-object stress/control, not independent dense promotion by itself
```

### Excluded From Promotion

The previous dense chair diagnostic rows are excluded from promotion:

```text
HM3D ObjectNav v2:val:y9hTuugGdiq:16:3:chair
HM3D ObjectNav v2:val:y9hTuugGdiq:17:4:chair
```

They may remain a regression sanity check only.

## Implementation Shape

### Implementation Status

### 사실

Implemented files:

```text
runtime/h001_runtime/build_dense_conflict_manifest.py
runtime/h001_runtime/probe_dense_conflict_recall.py
runtime/h001_runtime/analyze_dense_conflict_validation.py
runtime/h001_runtime/design_dense_conflict_generalization.py
runtime/jobs/dense_conflict_candidate_artifact.sh
runtime/jobs/dense_conflict_validation_from_source.sh
manifests/h001_dense_conflict_v1.json
manifests/h001_dense_conflict_v1.verify.json
manifests/dense_conflict_v1_scenes.txt
```

Docker validation completed on 2026-05-21:

```text
manifest_rows: 8
manifest_unique_episode_keys: 8
manifest_split: dense_conflict_v1
primary_rows: 6
secondary_stress_rows: 2
manifest_verify_ok: true
scene_assets_checked: 4
sim_scene_limit: 0
```

Existing-artifact recall gate smoke:

```text
output: /tmp/research3-runs/h001_dense_conflict_recall_gate_existing_artifact_smoke_v1
artifact: v3_fresh_spatial_p97_k20
primary_rows: 6
primary_rows_with_correct: 6 / 6
primary_recall_at_20: 1.0
first_correct_rank_min: 1
first_correct_rank_max: 3
passes_dense_recall_gate: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_status: gate_only_not_policy_claim
```

### 에이전트 추론

The existing-artifact smoke verifies that the frozen manifest and recall-gate code are usable. It does not replace the planned dense backend validation with `spatial_nms_p95_k100_d10`. The next implementation step should generate the dense conflict candidate artifact for the frozen rows, then rerun the same recall gate before any detector job.

### Artifact Job Status

### 사실

First launch:

```text
tmux_session: h001-dense-conflict-artifact-20260521-175656
script: runtime/jobs/dense_conflict_candidate_artifact.sh
log: runtime/logs/dense-conflict-artifact-p95-k100-d10-20260521-175656.log
artifact_out: /tmp/research3-runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1
recall_out: /tmp/research3-runs/h001_dense_conflict_recall_gate_spatial_nms_p95_k100_d10_v1
status: failed
failed_stage: candidate_artifact_generation
```

Host GPU blocker:

```text
status: resolved_on_2026-05-23
nvidia-smi: Failed to initialize NVML: Driver/library version mismatch
kernel_module: 580.126.09
user_space_library: 580.159.03
docker_gpu_error: failed to fulfil mount request: open /run/nvidia-persistenced/socket: no such file or directory
recovered_driver: 580.159.03
docker_gpu_smoke: passed with research3/habitat-h001:20260508-calib-artifacts
```

Resume attempt after host NVIDIA runtime was fixed:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-dense-conflict-artifact-${ts}" \
  "cd /home/yoohyun/research3 && TS=${ts} bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh"
```

This attempt failed on 2026-05-23 because `/tmp/research3-data` had become a stale empty directory rather than the expected compatibility symlink.

Canonical relaunch:

```text
tmux_session: h001-dense-conflict-artifact-canonical-20260523-140845
status: completed_but_recall_gate_failed
working_directory: /home/yoohyun/research3
command: TS=20260523-140845 DATA_ROOT=/home/yoohyun/research3/local_dataset/data RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs MODEL_ROOT=/home/yoohyun/research3/local_dataset/models bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh
log: runtime/logs/dense-conflict-artifact-p95-k100-d10-20260523-140845.log
artifact_out: local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1
recall_out: local_dataset/runs/h001_dense_conflict_recall_gate_spatial_nms_p95_k100_d10_v1
```

Final recall result:

```text
status: completed_but_recall_gate_failed
artifact: spatial_nms_p95_k100_d10
rows: 8
primary_rows: 6
primary_rows_with_correct: 3 / 6
primary_recall_at_20: 0.5
required_primary_rows_with_correct: 4 / 6
detector_job_allowed: false
next_step: revise dense candidate generation before detector scoring
```

Revised dense candidate generation:

```text
tmux_session: h001-dense-conflict-artifact-p90-k200-d5-20260523-150036
status: completed_but_recall_gate_failed
artifact: spatial_nms_p90_k200_d5
command: TOP_PERCENTILE=90.0 MAX_CANDIDATES=200 SPATIAL_NMS_MIN_DISTANCE_CELLS=5.0 with canonical DATA_ROOT/RUNS_ROOT/MODEL_ROOT
artifact_out: local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p90_k200_d5_v1
recall_out: local_dataset/runs/h001_dense_conflict_recall_gate_spatial_nms_p90_k200_d5_v1
reason: p95_k100_d10 missed all three primary 7MXmsvcQjpJ/plant selected-wrong rows
```

Final recall result:

```text
artifact_generation_status: completed
rows: 24
candidate_count: 4800
finite_position_candidates: 4241
primary_rows: 6
primary_rows_with_correct: 3 / 6
primary_recall_at_20: 0.5
required_primary_rows_with_correct: 4 / 6
detector_job_allowed: false
```

### 에이전트 추론

The host GPU blocker is resolved. The p95 and p90 dense re-export substrates both miss the same three `7MXmsvcQjpJ/plant` selected-wrong primary rows, so detector/association validation remains blocked for those re-export substrates. The existing selected `v3_fresh_spatial_p97_k20` substrate is a separate path: it passed the final primary recall gate and can be used for detector/association validation if the scope is explicitly limited to that selected artifact.

### Selected Artifact Detector/Association Validation

```text
recall_output: local_dataset/runs/h001_dense_conflict_recall_gate_v3_fresh_spatial_p97_k20_primary_final_v1
validation_output: local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1
source_detector_evidence: local_dataset/runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_evidence
script: runtime/h001_runtime/analyze_dense_conflict_validation.py
wrapper: runtime/jobs/dense_conflict_validation_from_source.sh
```

Result:

```text
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
passes_dense_conflict_validation_gate: true
```

This unblocks detector/association validation for the selected `v3_fresh_spatial_p97_k20` primary diagnostic only. It does not unblock the failed p95/p90 dense re-export substrates and it is not yet a full policy-scale claim.

### Secondary Stress Validation

```text
recall_output: local_dataset/runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1
validation_output: local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1
source_detector_evidence: local_dataset/runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_evidence_v4
source_detector_summary: local_dataset/runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_detector/summary.json
```

Result:

```text
secondary_rows: 2
recall_rows_with_correct: 2 / 2
recall_at_20: 1.0
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 1.0
rows_with_correct_and_wrong_positive_support: 2 / 2
commit / success / wrong / no_valid: 2 / 2 / 0 / 0
selected_correct_improvement_over_source_selected_rows: 2
uses_gt_for_action: false
uses_gt_for_analysis: true
passes_dense_conflict_validation_gate: true
```

The secondary result is still stress-test evidence, not generalization evidence, because it contains only two repeated-object `sofa` rows from one scene. The next step should design a broader split rather than tune thresholds on these rows.

### Broader Generalization Split Design

Design output:

```text
local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json
```

Current evidence summary:

```text
sources: v3_fresh_primary, first_eval_heldout_secondary, risk_validation_identity_smoke
rows: 10
scenes: 5
queries: 3
rows_with_correct_and_wrong_positive_support: 8
source_selected_wrong_rows: 5
success_commit_rows: 7
wrong_goal_commit_rows: 0
uses_gt_for_action: false
```

Selected next path:

```text
selected_next: scene_disjoint_first_eval_style
minimum_rows: 20
minimum_scenes: 5
minimum_queries: 3
minimum_selected_wrong_rows: 6
minimum_rows_with_correct_and_wrong_positive_support: 12
```

Rationale:

- `scene_disjoint_first_eval_style` keeps the same HM3D ObjectNav task family and existing wrong-goal / wasted-path evaluation connection.
- Additional repeated-object rows should be included as a stress slice, not used as the main promotion gate.
- HM3D-OVON should be deferred until ObjectNav dense-conflict generalization is stable because it adds language/open-vocabulary confounds.

### Frozen Generalization Manifest And Recall Gate

Generalization manifest:

```text
script: runtime/h001_runtime/build_dense_conflict_generalization_manifest.py
manifest: manifests/h001_dense_conflict_generalization_v1.json
verify: manifests/h001_dense_conflict_generalization_v1.verify.json
source_manifest: manifests/h001_first_eval_replacement_v1.json
source_coverage_decisions: local_dataset/runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/coverage_sanity/candidate_decisions.jsonl
source_candidate_artifact: local_dataset/runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
excluded_scene_keys: y9hTuugGdiq
status: frozen_pending_recall_gate
```

Manifest facts:

```text
rows: 20
scenes: 9
queries: 6
rows_with_correct_and_wrong_candidates: 20 / 20
source_selected_wrong_rows: 16
NoReobserve wrong-goal rows with correct present: 16
max_rows_per_scene: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Recall gate:

```text
output: local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1
artifact: first_eval_replacement_spatial_nms_p97_k20
primary_rows: 20
primary_rows_with_correct: 20 / 20
recall_at_20: 1.0
recall_at_5: 0.85
first_correct_rank_min: 1
first_correct_rank_max: 9
passes_dense_recall_gate: true
detector_job_allowed: true
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Detector substrate job:

```text
wrapper: runtime/jobs/dense_conflict_generalization_detector_substrate.sh
tmux_session: h001-dense-conflict-generalization-detector-20260523-170533
output: local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1
log: runtime/logs/dense-conflict-generalization-detector-substrate-20260523-170533.log
status: completed
summary: local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1/generalization_detector_substrate_summary.json
frame_rows: 20
rendered_heading_count: 125
detector_rows: 20
detector_box_rate: 0.85
sam2_mask_rate: 0.85
candidate_association_rate: 0.35
associated_rows: 7
passes_detector_substrate_gate: true
uses_gt_for_action: false
```

### 에이전트 추론

The generalization split is now frozen, its non-GT candidate recall substrate passes, and detector substrate passes under the fixed detector/mask/association thresholds. This still does not prove terminal arbitration utility because only `7/20` rows have candidate association and the next step must keep GT correctness labels evaluation-only.

### Terminal Evidence Extraction Design

Evidence extraction output:

```text
script: runtime/h001_runtime/extract_dense_conflict_generalization_evidence.py
output: local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1
action_evidence: action_evidence_rows.jsonl
evaluation_labels: evaluation_labels.jsonl
policy_diagnostics: terminal_policy_diagnostic_rows.jsonl
summary: terminal_arbitration_design_summary.json
```

Facts:

```text
action_evidence_rows: 20
evaluation_label_rows: 55
associated_rows: 7
unassociated_rows: 13
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
terminal_validation_ready: true
terminal_utility_claim_allowed: false
```

Policy diagnostic:

| Variant | Commits | Success commits | Wrong-goal commits | Interpretation |
| --- | ---: | ---: | ---: | --- |
| `defer_only` | 0 / 20 | 0 | 0 | safe lower bound, no utility |
| `semantic_top_if_supported` | 7 / 20 | 1 | 6 | unsafe semantic-top baseline |
| `first_associated` | 7 / 20 | 1 | 6 | unsafe association-order baseline |
| `support_score_best` | 7 / 20 | 3 | 4 | detector support helps but remains unsafe |
| `proposed_conservative_v0` | 7 / 20 | 3 | 4 | not promotable |

V0 wrong commit rows:

```text
HM3D ObjectNav v2:val:5cdEh9F2hJL:14:2:toilet
HM3D ObjectNav v2:val:mL8ThkuaVTM:2:4:bed
HM3D ObjectNav v2:val:mL8ThkuaVTM:18:0:bed
HM3D ObjectNav v2:val:CrMo8WxCyVb:1:2:toilet
```

### 에이전트 추론

The extraction path is now clean enough for a validation script because action-time evidence and evaluation labels are separated. The current terminal rule is not clean enough for a method claim: support-score selection still commits wrong candidates on `4/7` associated rows. The next implementation should design a stricter arbitration guard from these failure rows before running a validation gate.

### Terminal Guard Design

Guard design output:

```text
script: runtime/h001_runtime/design_dense_conflict_terminal_guard.py
output: local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1
summary: terminal_guard_design_summary.json
fixed_guard_rows: terminal_guard_diagnostic_rows.jsonl
sweep_rows: terminal_guard_sweep_rows.jsonl
```

Selected guard:

```text
guard_name: strict_depth_consistency_v1
max_depth_error_m: 0.33
min_associated_heading_count: 2
min_mask_hit_count: 2
max_semantic_rank: 5
uses_gt_for_action: false
```

Diagnostic result:

| Variant | Commits | Success commits | Wrong-goal commits | Status |
| --- | ---: | ---: | ---: | --- |
| `strict_depth_consistency_v1` | 3 / 20 | 3 | 0 | fixed-rule validation candidate |
| `rank1_depth_consistency_v1` | 1 / 20 | 1 | 0 | too conservative |
| `support_only_conservative_depth_v1` | 4 / 20 | 3 | 1 | unsafe |

### 사실

`strict_depth_consistency_v1` blocks the four v0 wrong-commit rows and keeps nonzero success commits on the same diagnostic split. The selected commits are two `CrMo8WxCyVb/bed` rows and one `svBbv1Pavdk/plant` row.

### 에이전트 추론

Support score and support margin are insufficient because high-support candidates can still be wrong. Depth-consistent detector association is the safer next action guard, but this is same-split design evidence. It must be frozen before any validation run and cannot be described as a paper-facing method result yet.

### Fixed Rule Terminal Validation

Frozen guard config:

```text
config: manifests/h001_dense_conflict_terminal_guard_v1.json
guard_name: strict_depth_consistency_v1
date_frozen: 2026-05-24
```

Validation output:

```text
script: runtime/h001_runtime/validate_dense_conflict_terminal_arbitration.py
output: local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1
summary: terminal_validation_summary.json
decision_rows: terminal_validation_decision_rows.jsonl
evaluated_rows: terminal_validation_evaluated_rows.jsonl
```

Validation result:

```text
action_evidence_forbidden_key_count: 0
stable_metric_match_design: true
local_fixed_rule_validation_passed: true
rows: 20
associated_rows: 7
commit/success/wrong: 3 / 3 / 0
associated_commit/success/wrong: 3 / 3 / 0
uses_gt_for_action: false
paper_claim_status: same_split_fixed_rule_validation_not_method_claim
```

### 에이전트 추론

The frozen guard reproduced the design metrics with decision rows written before evaluation labels were joined. This is a useful harness milestone, but it remains same-split validation. The next research step should define an independent terminal validation split or source artifact before any policy-scale claim.

### Independent Terminal Validation Contract

Contract:

```text
contract: manifests/h001_dense_conflict_terminal_independent_v1.json
guard_config: manifests/h001_dense_conflict_terminal_guard_v1.json
primary_source: dense_conflict_v1_v3_fresh_primary
secondary_stress_source: dense_conflict_v1_first_eval_replacement_sofa_stress
paper_claim_status: validation_contract_only_not_method_claim
```

Primary evidence profile:

```text
output: local_dataset/runs/h001_dense_conflict_independent_terminal_evidence_profile_v1
rows: 6
associated_rows: 6
unassociated_rows: 0
scenes: 7MXmsvcQjpJ, DYehNKdT76V, HY1NcmCgn3n
queries: chair, plant
action_evidence_forbidden_key_count: 0
naive_support_score_best_success_wrong: 2 / 4
```

Secondary stress profile:

```text
output: local_dataset/runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1
rows: 2
associated_rows: 2
unassociated_rows: 0
scene: y9hTuugGdiq
query: sofa
action_evidence_forbidden_key_count: 0
naive_support_score_best_success_wrong: 0 / 2
```

Predeclared validation gate:

```text
primary_wrong_goal_commit_rows: 0
primary_no_label_commit_rows: 0
primary_success_commit_rows_minimum: 1
primary_commit_rows_minimum: 1
secondary_stress_wrong_goal_commit_rows: 0
report_associated_and_unassociated_rows_separately: true
paper_claim_allowed_after_pass: false
```

Failure taxonomy:

| Failure code | Interpretation |
| --- | --- |
| `guard_wrong_commit_depth_consistent_wrong_instance` | wrong candidate satisfies strict depth, association-count, and mask-count constraints |
| `guard_over_defer_no_success` | guard is safe but inert on fully associated primary rows |
| `correct_candidate_blocked_by_association` | correct candidate is present but blocked by association, mask, or depth constraints |
| `association_coverage_failure` | detector/association substrate fails before terminal arbitration |
| `evaluation_label_plumbing_failure` | committed candidate has no evaluation label |
| `source_independence_violation` | validation rows overlap with design scenes or source split |
| `stress_slice_wrong_commit` | repeated-object stress rows produce wrong commits |

### 에이전트 추론

The `v3_fresh_validation_v1` primary source is the smallest currently available independent source because it is scene-disjoint from `dense_conflict_generalization_v1`, uses a different source split, and already has `6/6` associated action-evidence rows. The two `sofa` rows should be reported as a repeated-object stress slice, not as the primary promotion gate.

### Independent Terminal Validation Result

Runner update:

```text
script: runtime/h001_runtime/validate_dense_conflict_terminal_arbitration.py
change: add metric_gate_mode=none and contract-style gates for independent validation
guard threshold change: none
```

Primary validation:

```text
output: local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1
validation_scope: dense_conflict_independent_v1_primary
rows: 6
associated_rows: 6
commit/success/wrong: 6 / 2 / 4
no_label_commit_rows: 0
action_evidence_forbidden_key_count: 0
terminal_validation_gate_passed: false
failure_taxonomy: guard_wrong_commit_depth_consistent_wrong_instance = 4
uses_gt_for_action: false
```

Secondary stress validation:

```text
output: local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1
validation_scope: dense_conflict_independent_v1_secondary_stress
rows: 2
associated_rows: 2
commit/success/wrong: 2 / 0 / 2
no_label_commit_rows: 0
action_evidence_forbidden_key_count: 0
terminal_validation_gate_passed: false
failure_taxonomy: stress_slice_wrong_commit = 2
uses_gt_for_action: false
```

Wrong-commit pattern:

```text
DYehNKdT76V / chair: selected rank 2, depth error 0.006m, support 0.932
7MXmsvcQjpJ / plant: selected rank 1, depth error 0.102m, support 0.915, repeated across 3 rows
y9hTuugGdiq / sofa: selected rank 3, depth error 0.119m, support 0.922, repeated across 2 stress rows
```

### 에이전트 추론

`strict_depth_consistency_v1` is rejected as an independent terminal arbitration rule. The negative result is useful because the action/evaluation separation held (`forbidden_key_count = 0`), so the failure is not label leakage; it is a mechanism failure where wrong instances can be depth-consistent, detector-associated, and high-support. The next revision should not be a threshold tweak on this validation split. It should diagnose why wrong object instances receive stronger action-time evidence and derive a more general arbitration principle, such as instance identity separation, local rival comparison, or observation utility that requests additional views instead of committing.

### Failure Diagnosis and Revision Contract

Diagnostic output:

```text
script: runtime/h001_runtime/diagnose_dense_conflict_terminal_failures.py
output: local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1
rows: terminal_failure_diagnostic_rows.jsonl
summary: terminal_failure_diagnostic_summary.json
revision_contract: mechanism_revision_contract.json
```

Failure mechanism summary:

```text
rows: 8
wrong_goal_commit_rows: 6
success_commit_rows: 2
wrong_primary_mechanism_counts:
  repeated_wrong_instance_selected_by_saturated_support: 5
  guard_cannot_arbitrate_between_eligible_correct_and_wrong: 1
wrong_mechanism_tag_counts:
  correct_candidate_present: 6
  correct_candidate_positive_support_present: 6
  wrong_candidate_passes_frozen_guard: 6
  wrong_support_score_ge_correct: 6
  support_score_saturated: 6
  detector_score_tie_or_wrong_advantage: 6
  wrong_semantic_rank_as_good_or_better: 6
  same_wrong_candidate_repeated_across_episodes: 5
```

Revision contract:

```text
revision_name: rival_identity_confirmation_v1
status: design_contract_not_implemented
rejected_rule: strict_depth_consistency_v1
failure_mechanism: depth-consistent detector support is not instance-discriminative
principle: treat dense same-category positive support as identity ambiguity
```

Proposed actions:

- `commit_candidate` only for unique multi-axis support.
- `request_rival_identity_confirmation` when multiple same-category candidates pass guard.
- `defer_or_expand_retrieval` when correct evidence is blocked by association.

Simpler alternatives to ablate:

| Alternative | Expected failure |
| --- | --- |
| `support_margin_only` | fails when wrong and correct support scores are saturated or tied |
| `depth_margin_only` | fails when wrong instance is also depth-consistent or depth-better |
| `semantic_top_only` | fails when semantic rank points to a wrong instance |
| `defer_all_ambiguous` | safe but inert, loses successful terminal commits |

### 에이전트 추론

The next method should be derived from rival identity ambiguity, not from another threshold sweep on this failed split. The implementation target is a diagnostic `rival_identity_confirmation_v1` policy that converts saturated same-category evidence into an active observation request, then tests whether the request is explanatory and whether any commit remains safe. Any paper-facing claim still requires a fresh or predeclared validation split.

### Step 1: Freeze Row Manifest

Create a manifest only when implementation starts:

```text
manifests/h001_dense_conflict_v1.json
```

The manifest must store:

- `episode_key`
- `scene_id`
- `query`
- source artifact path
- source branch id
- source conflict class
- whether it belongs to primary independent or secondary stress set

### Step 2: Dense Candidate Recall Gate

Generate dense non-GT candidate pools for the frozen scene/query pairs. Start with the current first dense backend revision:

```text
selection_mode: spatial_nms
top_percentile: 95.0
max_candidates: 100
distance_nms_m: 10.0
```

Do not run detector observation until recall is checked after generation.

Recall gate:

```text
primary_rows_with_correct_candidate >= 4 / 6
primary_recall_at_20 >= 0.50
uses_gt_for_action = false
uses_gt_for_analysis = true
```

If recall fails, classify the result as dense backend recall failure and stop before detector scoring.

### Step 3: Detector / Association Variants

Run `GroundingDINO + SAM2` on the frozen rows after the recall gate passes.

Association variants are ablations, not defaults:

```text
strict_mask_depth_1_0
mask_depth_2_0
mask_no_depth
grounded_position_mask_depth_1_0
grounded_position_mask_depth_2_0
```

`association_depth_tolerance_m=2.0` must remain an ablation or property-conditioned treatment. It is not a global default.

### Step 4: Terminal Arbitration

Attach evaluation-only labels in a sidecar file after action selection:

```text
evaluation_labels.jsonl
```

Action rows must not contain GT correctness fields unless field names explicitly include `evaluation_only`.

Terminal comparison policies:

| Policy | Role |
| --- | --- |
| `defer_only` | safety lower bound |
| `first_external` | dense retrieval order baseline |
| `score_only_best` | detector evidence naive baseline |
| `strict_depth_terminal` | current association baseline |
| `depth2_terminal` | local chair repair ablation |
| `grounded_position_terminal` | geometry repair alternative |
| `proposed_conflict_arbitration` | final candidate only if conflict gates pass |

## Expected Failure Taxonomy

### 사실

This taxonomy is fixed before running the dense conflict detector/association job. It is used for post-run diagnosis and does not change the action-time policy.

| Code | Failure mode | Observable evidence | Interpretation | Next action |
| --- | --- | --- | --- | --- |
| `F0_runtime_blocked` | host or Docker runtime cannot launch GPU/IO job | `nvidia-smi` fails, Docker `--gpus all` fails, missing scene mount, missing checkpoint | environment failure, not method evidence | fix runtime and rerun same command |
| `F1_dense_recall_fail` | dense backend misses correct candidates | primary rows with correct candidate `< 4/6` or recall@20 `< 0.50` | semantic map candidate generation is still the bottleneck | stop before detector; revise candidate generation |
| `F2_candidate_nav_fail` | candidates exist but are not usable navigation goals | many `NaN`, non-finite, unsnapped, or non-navigable `visit_position` entries | map-to-Habitat alignment / navmesh snapping failure | fix alignment or viewpoint generation |
| `F3_detector_substrate_fail` | detector/mask evidence is unavailable | detector box rate `< 0.80` or SAM2 mask rate `< 0.80` | perception substrate failure | do not evaluate arbitration; fix detector/query/frames |
| `F4_association_underlink` | visible candidate is not associated | inside-mask projection exists but strict depth rejects; low association rate | geometry/depth association too strict | compare `strict`, `depth2`, `grounded_position` |
| `F5_association_overlink` | relaxed association supports distractors | wrong candidates gain support after `depth2` or no-depth association | geometry/depth association too permissive | keep as ablation only; add property-conditioned guard |
| `F6_conflict_not_present` | validation no longer contains real conflicts | fewer than `3` primary rows have both correct and wrong positive-support candidates | test does not stress the novelty claim | revise frozen rows or artifact generation |
| `F7_unsafe_commit` | terminal policy commits wrong/no-valid target | wrong-goal, no-valid, or visit-position-only commit rate `> 0` | arbitration is unsafe | reject policy variant; inspect simpler alternatives |
| `F8_inert_policy` | policy avoids errors only by deferring | commit rate equals `defer_only` or success commits `< 2/6` | no active utility evidence | revise utility or observation target selection |
| `F9_simpler_alt_wins` | simpler policy matches or beats proposal | `first_external`, `score_only_best`, or single association variant has equal utility and safety | proposed design is not necessary | remove component or re-derive from failure cases |
| `F10_scope_fragile` | result depends on secondary or single category | primary fails but secondary passes; only one scene/category contributes | weak generality | report as stress/control only |
| `F11_label_leakage` | action rows contain GT correctness labels | non-evaluation-only `candidate_correct`, target id, or oracle field appears before action | invalid experiment | discard run and fix logging |

### 에이전트 추론

The most informative negative results are `F1`, `F5`, `F7`, and `F9`. They say whether the bottleneck is candidate generation, association geometry, terminal safety, or novelty over simpler alternatives. The method should not be promoted if the only positive evidence is avoiding `F7` by becoming `F8`.

## Simpler Alternatives And Ablation Table

### 사실

All alternatives below use the same frozen rows and the same detector/association evidence. GT labels are used only after action selection for evaluation.

| Variant | Action-time inputs | What it tests | Required report |
| --- | --- | --- | --- |
| `defer_only` | none beyond trigger | safety lower bound | commit/success/wrong/no-valid all explicit |
| `first_external` | dense retrieval order | whether denser retrieval alone solves the issue | selected-correct improvement over first |
| `semantic_score_best` | original semantic map score | whether semantic prior alone is enough | wrong-goal fixes and new wrong-goals |
| `detector_score_best` | detector box/mask score only | whether detector confidence alone is enough | candidate-level AUC and commit safety |
| `strict_mask_depth_1_0` | mask + strict depth association | current geometry baseline | association rate and safety |
| `mask_depth_2_0` | mask + relaxed depth association | local chair repair generalization risk | new wrong-goal support count |
| `mask_no_depth` | mask without depth gate | whether depth is needed to suppress distractors | overlink / wrong support rate |
| `grounded_position_mask_depth_1_0` | grounded candidate point + strict depth | point-height mismatch repair | association recovery by row |
| `grounded_position_mask_depth_2_0` | grounded candidate point + relaxed depth | geometry repair plus tolerance | safety vs `mask_depth_2_0` |
| `local_context_only` | own-view/local candidate support | repeated-object local-context signal | sofa stress rows separately |
| `semantic_prior_arbitration` | semantic prior plus conflict guard | whether semantic prior resolves strong ties | selected-wrong primary rows |
| `proposed_minus_semantic_prior` | proposal without semantic-prior tie break | necessity of semantic prior | loss in correct commits |
| `proposed_minus_depth` | proposal without depth consistency | necessity of depth evidence | new wrong-goal support |
| `proposed_minus_local_context` | proposal without local-context term | necessity of local repeated-object handling | secondary stress degradation |
| `proposed_minus_conflict_guard` | proposal without wrong-support guard | whether guard prevents unsafe direct commits | wrong-goal commit increase |
| `oracle_best_correct` | GT correctness | diagnostic upper bound only | oracle gap, not baseline |

### 에이전트 추론

`proposed_conflict_arbitration` is only contribution-relevant if it beats `first_external`, `detector_score_best`, and the best single association variant under the same safety gate. If `mask_depth_2_0` or `detector_score_best` matches it, the contribution should be rewritten as a simpler association or detector calibration result, not as semantic uncertainty utility.

## Promotion Gates

### Substrate Gate

```text
primary_rows >= 6
detector_box_rate >= 0.80
sam2_mask_rate >= 0.80
candidate_association_rate >= 0.30
rows_with_correct_and_wrong_positive_support >= 3
```

### Safety Gate

```text
wrong_goal_commit_rate == 0.0
no_valid_commit_rate == 0.0
visit_position_only_commit_rate == 0.0
```

### Utility Gate

```text
success_commit_rows >= 2 / 6 on primary rows
selected_correct_improvement_over_first >= 2 rows
correct_commit_with_wrong_positive_support_rows >= 2
commit_rate > defer_only commit_rate
wrong_goal_commit_rate <= all simpler alternatives
```

### Generalization Gate

```text
primary scenes >= 3
primary query categories >= 2
secondary repeated-object stress set reported separately
per-category failure table recorded
```

## Output Contract

Current selected-artifact output root:

```text
local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1
```

Expected files:

```text
dense_conflict_manifest.json
dense_recall_summary.json
dense_detector_summary.json
dense_association_variant_summary.json
dense_terminal_arbitration_rows.jsonl
dense_terminal_arbitration_summary.json
evaluation_labels.jsonl
failure_taxonomy.json
```

## Stop Conditions

Stop and record a negative result if any of these happen:

- dense candidate generation does not recover correct candidates on at least `4 / 6` primary rows;
- detector/mask substrate fails;
- wrong candidates receive positive support but the objective cannot commit safely;
- `depth2` improves association coverage but increases wrong-goal commits;
- only the secondary `sofa` stress rows pass while primary independent rows fail.

## Interpretation Boundary

### 사실

The design uses existing evidence rows only to select conflict cases and define evaluation gates.

### 에이전트 추론

Passing this validation would support the narrower claim that active re-observation evidence can arbitrate semantic-memory conflicts when both correct and wrong candidates receive positive support. It would still not prove full ObjectNav policy-scale improvement until integrated with `wrong_goal_visit`, wasted path, `Success Rate`, and `SPL` on a larger frozen split.

### 사용자 판단 필요

No user decision is required before implementing the manifest and recall gate. Real-world deployment and Step 4-5 SLAM metrics remain separate later decisions.
