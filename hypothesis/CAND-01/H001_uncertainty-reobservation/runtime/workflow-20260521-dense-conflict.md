# Dense Conflict Validation

## Purpose

### 사실

Current dense backend result is a local two-row `y9hTuugGdiq/chair` diagnostic. It recovered correct dense candidates and produced detector-backed commits under post-hoc GT analysis labels, but every positive-support candidate was also post-hoc correct.

### 에이전트 추론

This does not prove wrong-goal repair utility. The next validation must test rows where correct and wrong candidates both receive positive detector/depth support, because that is the actual failure mode a top-tier paper claim must survive.

## Validation Question

If a dense non-GT candidate backend provides both correct and wrong positively supported candidates, can the terminal active-observation objective choose a correct candidate without increasing wrong-goal commits, compared with defer-only, first-external, and detector-score-only alternatives?

## Current Broader Standoff Diagnostic

### 사실

The navmesh-only standoff substrate is now valid, but the current post-observation decision rule is unsafe:

```text
detector_output: local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1
post_observation_output: local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1
unsafe_diagnostic_output: local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1
detector_box_rate: 0.9808
sam2_mask_rate: 0.9808
candidate_association_rate: 0.7212
request/evidence/decision_rows: 28 / 110 / 28
commit/success/wrong/no_label: 7 / 0 / 7 / 0
unsafe_commit_queries: bed 4, chair 2, tv_monitor 1
post_observation_gate_passed: false
uses_gt_for_action: false
```

Unsafe-commit mechanisms:

```text
absence_of_cross_support_not_discriminative: 7
low_detector_score_still_strong_by_count: 5
wrong_candidate_has_stronger_own_view_support_than_correct: 4
rival_candidate_false_positive_commit: 4
candidate_set_no_valid_goal_candidate: 3
depth_consistent_wrong_candidate: 3
semantic_prior_favors_wrong_over_correct: 3
semantic_top_is_wrong: 3
```

Simple guards rejected by the diagnostic:

```text
existing_unique_strong_own_view_identity: wrong 7 / commit 7
semantic_rank_1_only: wrong 3 / commit 3
detector_box_ge_0_25: wrong 2 / commit 2
depth_error_le_0_33: wrong 3 / commit 3
own_count_ge_4_only: wrong 4 / commit 4
rank_le_3_box_ge_0_25_depth_le_0_50: safe but inert, commit 0
```

### 에이전트 추론

The post-observation blocker is no longer detector availability or viewpoint geometry. The current own-view evidence confirms that a category-like object is visible near a candidate, but it does not prove that the candidate is a valid `ObjectNav` goal. The next rule must add a candidate-set validity and local semantic/geometric consistency contract before any detector-backed commit.

### Rule-Change Contract

Contract file:

```text
manifests/h001_rival_identity_strict_arbitration_v1.json
```

Do not change the post-observation rule by tuning only these terms:

- own-view associated heading count
- identity margin
- detector box score
- depth error
- semantic rank

The next objective must report the same frozen evidence against:

- `defer_only`
- `semantic_rank_1_only`
- `detector_box_score_only`
- `depth_consistency_only`
- `own_count_only`
- a combined simple guard
- the proposed stricter arbitration objective

The proposed objective may only be promoted if it produces nonzero success commits while keeping wrong-goal and no-label commits at `0` on this broader standoff split.

### Implemented Diagnostic Objective

### 사실

`goal_validity_arbitration_v1` is implemented as an objective option in:

```text
runtime/h001_runtime/analyze_rival_identity_post_observation.py
```

Docker verification:

```text
default_regression_output: local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_default_regression_v1
strict_objective_output: local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1
default_commit/success/wrong/no_label: 7 / 0 / 7 / 0
strict_commit/success/wrong/no_label: 2 / 2 / 0 / 0
strict_request/evidence/decision_rows: 28 / 110 / 28
strict_post_observation_gate_passed: true
uses_gt_for_action: false
```

### 에이전트 추론

This is a diagnostic repair, not a paper-facing claim. The same broader split was used for unsafe-commit diagnosis and objective design, so a separate independent or predeclared validation source is required for `goal_validity_arbitration_v1`.

### Goal-Validity Independent Source Freeze

### 사실

```text
contract: rival_identity_goal_validity_independent_v1
design_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_design_v1
source_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_source_v1
manifest: manifests/h001_rival_identity_goal_validity_independent_v1.json
verify: manifests/h001_rival_identity_goal_validity_independent_v1.verify.json
source_candidate_decisions: local_dataset/runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/policy_revision/candidate_decisions.jsonl
preferred_source: v3_fresh_validation
design_parent_rows/scenes/queries: 72 / 11 / 6
design_top_wrong_goal_rows: 51
design_correct_and_wrong_candidate_rows: 59
request_rows/scenes/queries: 30 / 10 / 6
request_route_counts:
  rival_identity_arbitration: 26
  object_existence_validation: 4
excluded_scene_overlap: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
verify_ok: true
paper_claim_allowed: false
```

### 에이전트 추론

This source was suitable as the independent validation substrate because it was frozen before rerunning `goal_validity_arbitration_v1`, uses `v3_fresh_validation` rows after excluding prior diagnostic and broader objective-design scenes, and preserves all six ObjectNav query categories. The completed rerun below is a safe-but-inert negative result, not a paper claim.

### Goal-Validity Independent Runtime Substrate

### 사실

Plan, frame, and detector substrate:

```text
status: completed
plan_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1
frame_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1
filtered_frame_summary: local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
detector_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1
plan_rows: 92
planned_request_rows: 30
skipped_rows: 9
skip_reason: standoff_navmesh_required
planned_scene_count: 10
planned_query_count: 6
zero_standoff_plan_rows: 0
near_standoff_plan_rows: 0
viewpoint_source_counts:
  standoff_navmesh: 92
rows_exported: 92
rendered_heading_count: 810
nonblank_output_rows: 92
dropped_rows: 0
removed_blank_heading_count: 0
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: true
detector_rows: 92
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.6196
rows_with_candidate_association: 57
associated_candidate_heading_count: 239
passes_detector_substrate_gate: true
uses_gt_for_action: false
```

Detector/SAM2 substrate job contract:

```text
status: completed
tmux_session: h001-goal-validity-independent-detector-20260527-021807
working_directory: /home/yoohyun/research3
script: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
frames: local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
frame_root: local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1
candidate_artifact: local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl
output: local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/rival-identity-goal-validity-independent-detector-20260527-021807.log
status_file: local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1/job_status.json
expected_files:
  detector_v3c/summary.json
  detector_v3c/detector_candidate_associations.jsonl
  rival_identity_detector_associations.jsonl
  rival_identity_detector_substrate_summary.json
verification_command: cat local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1/job_status.json && cat local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1/rival_identity_detector_substrate_summary.json
initial_status: detector_mask_scoring
launch_command: TS=20260527-021807 ROOT=/home/yoohyun/research3 PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1 FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1 FRAME_EXPORT_SUMMARY=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_frames_standoff_navmesh_v1/summary.json CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1 EXPECTED_FRAME_ROWS=92 MAX_FRAMES=92 MAX_DEBUG_IMAGES=180 LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/rival-identity-goal-validity-independent-detector-20260527-021807.log STATUS=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1/job_status.json bash /home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
```

Independent goal-validity rerun:

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
objective: goal_validity_arbitration_v1
output: local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1
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
reason_counts:
  defer_low_goal_validity_cross_view_aliasing: 12
  post_observation_no_candidate_support: 8
  object_existence_requires_independent_confirmation: 6
  defer_visible_object_not_goal_validity: 2
  defer_comparable_goal_validity_candidates: 1
  defer_low_goal_validity_surrogate: 1
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The independent rerun rejects the current `goal_validity_arbitration_v1` as a paper-facing utility rule. It is safe on this source, but inert: no wrong-goal/no-label commits and no success commits. Row-level diagnosis and a same-evidence default counterfactual now show that this is a safety-utility tradeoff, not a simple threshold issue.

### Goal-Validity Independent Failure Diagnosis

### 사실

```text
default_counterfactual_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1
failure_diagnostic_script: runtime/h001_runtime/diagnose_goal_validity_independent_failure.py
failure_diagnostic_output: local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1
strict_goal_validity_commit/success/wrong/no_label: 0 / 0 / 0 / 0
default_counterfactual_commit/success/wrong/no_label: 7 / 4 / 3 / 0
default_wrong_goal_queries:
  chair: 1
  sofa: 1
  toilet: 1
diagnostic_has_tradeoff: true
loose_rule_nontrivial: true
loose_rule_safe: false
strict_rule_safe: true
strict_rule_nontrivial: false
mechanism_tag_counts:
  cross_view_aliasing_blocks_goal_validity: 14
  planned_candidate_set_has_no_valid_goal: 13
  no_own_candidate_support: 11
  strong_identity_not_goal_validity: 8
  object_existence_branch_blocks_commit: 6
  default_rule_success_lost_by_strict_rule: 4
  default_rule_wrong_goal: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The default objective recovers some successes, but wrong-goal commits appear on `chair`, `sofa`, and `toilet`. The strict objective blocks those wrong goals but also loses every success. A same-evidence terminal commit rule is therefore not justified unless it adds a new candidate-validity signal; tuning semantic rank, box score, depth, own-count, or margin from joined labels would not be a defensible paper-facing revision.

### Goal-Validity Revision V2 Router

### 사실

```text
revision_contract: manifests/h001_rival_identity_goal_validity_revision_v2.json
router_script: runtime/h001_runtime/route_goal_validity_revision_v2.py
router_output: local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1
request_rows: 30
request_action_rows: 30
commit_allowed_rows: 0
revision_action_counts:
  request_discriminative_rival_view: 14
  request_expanded_retrieval: 8
  request_object_existence_confirmation: 6
  request_goal_validity_confirmation: 2
revision_branch_counts:
  cross_view_aliasing: 14
  no_own_candidate_support: 8
  object_existence_validation: 6
  strong_identity_not_goal_validity: 2
routes_all_requests: true
terminal_commit_blocked: true
uses_gt_for_action: false
uses_gt_for_analysis: false
paper_claim_allowed: false
```

### 에이전트 추론

`goal_validity_revision_v2` should be treated as an active-evidence routing contract, not a terminal utility method. The next implementation should start from the largest branch, `request_discriminative_rival_view`, and define a planner/evaluation contract that can test whether an additional contrastive view reduces cross-view aliasing without introducing wrong-goal commits.

### Discriminative Rival View Planner Contract

### 사실

```text
contract: manifests/h001_discriminative_rival_view_planner_v1.json
source_router_output: local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1
source_filter: revision_action == request_discriminative_rival_view
target_request_rows: 14
planner_status: design_contract_only
planned_view_type:
  - common_pair_view
  - matched_dual_standoff_view
required_candidate_set: explicit focus-rival pair candidate ids
minimum_plan_gate:
  target_request_rows_minimum: 10
  zero_standoff_rows: 0
  near_standoff_rows: 0
  rotation_fallback_rows: 0
  planned_pair_rows_minimum: 10
  planned_query_count_minimum: 3
frame_detector_gate:
  row_level_nonblank_gate: true
  detector_box_rate_minimum: 0.80
  sam2_mask_rate_minimum: 0.80
  pair_candidate_association_rate_minimum: 0.40
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The previous standoff planner already observed each candidate individually, but cross-view aliasing remained. The next planner should not be a stronger confidence threshold or another single-candidate view. It should create contrastive pair evidence where focus and rival candidates are evaluated under matched geometry and explicit pair candidate association.

### Discriminative Rival View Plan Smoke

### 사실

```text
planner_script: runtime/h001_runtime/plan_discriminative_rival_view.py
planner_output: local_dataset/runs/h001_discriminative_rival_view_plan_v1
source_router_rows: 14
planned_request_rows: 14
plan_rows: 38
common_pair_view_rows: 10
matched_dual_standoff_rows: 28
skipped_rows: 4
skip_reason_counts:
  common_pair_view_unavailable: 4
viewpoint_pair_role_counts:
  common: 10
  focus: 14
  rival: 14
viewpoint_source_counts:
  common_pair_geometry: 4
  common_pair_navmesh: 6
  standoff_navmesh: 28
target_distance_min/mean/max_m: 1.6344 / 1.9781 / 3.1546
zero_standoff_rows: 0
near_standoff_rows: 0
rotation_fallback_rows: 0
plan_smoke_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The planner produces enough contrastive views for the largest revision branch. At this point the next gate was frame export and nonblank filtering, because the plan smoke only validated geometry and routing; it did not yet prove detector association or terminal utility.

### Discriminative Rival View Frame Smoke

### 사실

```text
v1_frame_output: local_dataset/runs/h001_discriminative_rival_view_frames_v1
v1_nonblank_output: local_dataset/runs/h001_discriminative_rival_view_frames_v1/nonblank_filter_v1
v1_rows/headings: 38 / 222
v1_dropped_rows: 1
v1_dropped_row: HY1NcmCgn3n / chair / common_pair_geometry
v1_row_level_nonblank_gate_passed: false

v2_planner_output: local_dataset/runs/h001_discriminative_rival_view_plan_v2
v2_frame_output: local_dataset/runs/h001_discriminative_rival_view_frames_v2
v2_nonblank_output: local_dataset/runs/h001_discriminative_rival_view_frames_v2/nonblank_filter_v1
v2_plan_rows: 38
v2_common_pair_navmesh_rows: 10
v2_matched_dual_standoff_rows: 28
v2_rows/headings: 38 / 222
v2_dropped_rows: 0
v2_removed_blank_headings: 0
v2_row_level_nonblank_gate_passed: true
v2_strict_no_blank_heading_gate_passed: true
v2_metadata_repair: export_postview_frames_v2.py passthrough now preserves viewpoint_pair_role, rival_*, revision_*, and standoff_* fields
v2_role_counts:
  common: 10
  focus: 14
  rival: 14
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

Geometry-only common pair views are not robust enough for detector substrate generation. The v2 repair keeps only navmesh-snapped common pair views and falls back to matched dual standoff views, which passes the frame/nonblank gate. Detector/SAM2 substrate has now run on the v2 nonblank frame summary; substrate availability is not the current blocker.

### Discriminative Rival View Detector Substrate Launch

### 사실

```text
session: h001-discriminative-rival-view-detector-20260527-032810
status: completed, superseded
stage: completed
working_directory: /home/yoohyun/research3
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
frames: local_dataset/runs/h001_discriminative_rival_view_frames_v2/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
frame_root: local_dataset/runs/h001_discriminative_rival_view_frames_v2
candidate_artifact: local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl
output: local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/discriminative-rival-view-detector-20260527-032810.log
expected_files:
  local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/detector_v3c/summary.json
  local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/detector_v3c/detector_candidate_associations.jsonl
  local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/rival_identity_detector_associations.jsonl
  local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/rival_identity_detector_substrate_summary.json
verification_command:
  cat local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/job_status.json
  cat local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/rival_identity_detector_substrate_summary.json
```

Exact launch command:

```bash
cd /home/yoohyun/research3 && TS=20260527-032810 ROOT=/home/yoohyun/research3 PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_plan_v2 FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_frames_v2/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_frames_v2 FRAME_EXPORT_SUMMARY=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_frames_v2/summary.json CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl OUT=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1 EXPECTED_FRAME_ROWS=38 MAX_FRAMES=38 MAX_DEBUG_IMAGES=180 LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/discriminative-rival-view-detector-20260527-032810.log STATUS=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/job_status.json bash /home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
```

```text
v1_detector_rows: 38
v1_detector_box_rate: 1.0
v1_sam2_mask_rate: 1.0
v1_candidate_association_rate: 0.8158
v1_rows_with_candidate_association: 31
v1_associated_candidate_heading_count: 128
v1_uses_gt_for_action: false
v1_superseded_reason: detector output did not preserve viewpoint_pair_role for pair-level evidence analysis

v2_session: h001-discriminative-rival-view-detector-v2-20260527-033307
v2_status: completed
v2_stage: completed
v2_output: local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2
v2_log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/discriminative-rival-view-detector-v2-20260527-033307.log
v2_verification_command:
  cat local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2/job_status.json
  cat local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2/rival_identity_detector_substrate_summary.json
```

Exact v2 launch command:

```bash
cd /home/yoohyun/research3 && TS=20260527-033307 ROOT=/home/yoohyun/research3 PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_plan_v2 FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_frames_v2/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_frames_v2 FRAME_EXPORT_SUMMARY=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_frames_v2/summary.json CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl OUT=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2 EXPECTED_FRAME_ROWS=38 MAX_FRAMES=38 MAX_DEBUG_IMAGES=180 LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/discriminative-rival-view-detector-v2-20260527-033307.log STATUS=/home/yoohyun/research3/local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2/job_status.json bash /home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
```

### 에이전트 추론

This job tests perception substrate availability only. It is not yet a post-observation decision rule or ObjectNav utility claim. v1 is useful as a substrate-positive result, but v2 is required for pair-role-aware evidence analysis.

### Discriminative Rival View Evidence Diagnostic

### 사실

```text
script: runtime/h001_runtime/analyze_discriminative_rival_view_evidence.py
output: local_dataset/runs/h001_discriminative_rival_view_evidence_v1
request_rows: 14
association_rows: 444
evidence_available_rate: 1.0
disambiguation_rate: 0.6429
actions:
  discriminative_support_focus: 8
  discriminative_support_rival: 1
  discriminative_ambiguous_defer: 5
label_cases:
  both_correct: 6
  neither_correct: 5
  rival_only_correct: 3
single_correct_preferred_rate: 0.0
single_correct_wrong_preference_rate: 0.3333
passes_discriminative_evidence_diagnostic_gate: false
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The active contrastive views produce measurable detector evidence, but the evidence is not yet a reliable identity-utility signal. In the only single-correct cases, the correct candidate is the rival, not the focus, and the current scoring either defers or prefers the wrong focus. The next step is failure taxonomy before any objective/rule revision.

### Discriminative Rival View Failure Diagnostic

### 사실

```text
script: runtime/h001_runtime/diagnose_discriminative_rival_view_failure.py
output: local_dataset/runs/h001_discriminative_rival_view_failure_diagnostic_v1
diagnostic_rows: 14
failure_tag_counts:
  symmetric_cross_view_leak: 7
  rival_visible_from_focus_view: 6
  identity_score_near_tie: 5
  common_view_supports_both_candidates: 5
  no_valid_goal_pair_but_disambiguated: 4
  both_correct_goal_region_or_duplicate_preferred: 4
  rival_correct_own_view_evidence_weak: 3
  rival_only_correct_deferred_by_margin: 2
  rival_only_correct_wrong_focus_preferred: 1
gate:
  threshold_tuning_allowed: false
  objective_revision_allowed: false
  planner_or_branch_revision_required: true
  fresh_validation_allowed: false
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The failure is not a detector-availability issue. It is a combination of cross-view leakage, common-view non-discrimination, invalid focus/rival pairs, and weak own-view evidence for the correct rival candidate. The next decision is whether to revise the discriminative view design or move to the next router branch, `request_expanded_retrieval`.

### Branch Priority Decision

### 에이전트 추론

Proceed to `request_expanded_retrieval` before another discriminative-view revision. The failure taxonomy shows that the current focus/rival pair is often not a reliable candidate set: some rows have no valid goal candidate in the pair, some have both candidates valid, and cross-view leakage makes viewpoint-only disambiguation weak. Expanded retrieval should first test whether action-time semantic memory can recover a better candidate set; discriminative views can then serve as a later identity-validation step.

### Expanded Retrieval Branch Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_branch_v1.json
status: frozen_before_implementation
source_filter: revision_action == request_expanded_retrieval
expected_request_rows: 8
candidate_budget: 6-10
terminal_commit_allowed: false
paper_claim_allowed: false
forbidden_action_inputs:
  candidate_correct
  selected_for_goal
  wrong_goal_visit
  success labels
  post-hoc GT object ids
  evaluation labels
  threshold tuning from joined labels
diagnostic_gates:
  request_rows_min: 6
  expanded_candidate_rows_min: 48
  duplicate_candidate_id_rate_max: 0.05
  nonfinite_position_rate_max: 0.05
  uses_gt_for_action: false
jq_validation: passed
```

### Expanded Retrieval Planner Smoke

### 사실

```text
planner: runtime/h001_runtime/plan_expanded_retrieval_branch.py
output: local_dataset/runs/h001_expanded_retrieval_plan_v1
expected_request_rows: 8
request_rows: 8
candidate_set_rows: 8
plan_rows: 80
expanded_candidates_per_request_min/max: 10 / 10
skipped_rows: 0
duplicate_candidate_id_rate: 0.0
nonfinite_position_rate: 0.0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
planner_gate_passed: true
```

### Expanded Retrieval Candidate-Set Validity

### 사실

```text
diagnostic: local_dataset/runs/h001_expanded_retrieval_candidate_set_validity_v1
analysis_only_labels: local_dataset/runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl
label_join_gate_passed: true
missing_label_rows: 0
missing_label_candidates: 0
request_rows: 8
candidate_rows: 80
candidate_set_contains_correct_rows/rate: 6 / 0.75
no_valid_candidate_rows/rate: 2 / 0.25
source_top_correct_rows: 1
source_top_wrong_rows: 7
source_top_wrong_goal_rows: 7
wrong_top_replacement_rows/rate: 5 / 0.7143
rows_with_wrong_goal_candidate: 7
full_pool_contains_correct_rows/rate: 6 / 0.75
full_pool_no_valid_rows: 2
selected_missed_full_pool_correct_rows: 0
candidate_set_taxonomy:
  source_pool_no_valid_candidate: 2
  valid_set_with_wrong_goal_distractor: 5
  valid_set_without_wrong_goal_distractor: 1
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

Candidate-set expansion is mechanically valid and often useful: it recovers a correct candidate in `6/8` rows and replaces a wrong source top in `5/7` wrong-top rows. The no-valid rows are not rank-band misses because the full action-time pool also lacks correct candidates. It is not yet a detector/objective gate because source-pool failures must route away from terminal commitment and `5/6` valid rows still include wrong-goal distractors. The next step is to define the guard target before detector/viewpoint evidence, then convert it into non-GT action-time proxies.

### Expanded Retrieval Candidate-Set Guard Design

### 사실

```text
script: runtime/h001_runtime/design_expanded_retrieval_candidate_set_guard.py
output: local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1
request_rows: 8
taxonomy_counts:
  source_pool_no_valid_candidate: 2
  valid_set_with_wrong_goal_distractor: 5
  valid_set_without_wrong_goal_distractor: 1
guard_route_counts:
  request_backend_retrieval_revision: 2
  request_detector_guarded_observation: 5
  request_lightweight_confirmation: 1
detector_evidence_allowed_rows/rate: 6 / 0.75
terminal_commit_allowed_rows: 0
missing_candidate_set_rows: 0
guard_design_gate_passed: true
guard_is_action_time_rule: false
requires_action_time_proxy: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The guard design fixes the intended route before detector/viewpoint evidence: source-pool failures should go to backend retrieval revision, valid-but-distractor sets may acquire detector evidence but cannot commit, and cleaner valid sets only get lightweight confirmation. This artifact uses analysis-only taxonomy to define the target behavior, so it is not a paper-facing action rule. The first non-GT proxy feature audit is recorded below; it shows candidate-set score/support features are insufficient for source-pool validity.

### Expanded Retrieval Guard Proxy Feature Audit

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_guard_proxy_features.py
output: local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1
request_rows: 8
feature_extraction_gate_passed: true
forbidden_action_feature_rows: 0
terminal_commit_allowed_rows: 0
proxy_route_counts:
  request_detector_guarded_observation_proxy: 8
analysis_only_target_route_counts:
  request_backend_retrieval_revision: 2
  request_detector_guarded_observation: 5
  request_lightweight_confirmation: 1
target_backend_rows: 2
target_backend_proxy_backend_rows: 0
target_backend_proxy_evidence_rows: 2
source_pool_validity_proxy_recall: 0.0
evidence_allowed_target_recall: 1.0
proxy_ready_for_detector_gate: false
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

Non-GT candidate-set features are available at action time, including source/expanded candidate counts, positive support counts, score margins, high-score saturation, spatial spread, reachability availability, and duplicate candidate fingerprints. They are enough to detect that the expanded sets are ambiguous, but not enough to tell whether the source pool actually contains a valid goal. The two no-valid `tv_monitor` rows still look like high-confidence ambiguous sets and are routed to detector evidence by the proxy. The source-pool proxy below addresses this diagnostic blocker; detector/viewpoint evidence remains paper-blocked until the revised branch passes fresh/predeclared validation.

### Expanded Retrieval Source-Pool Validity Proxy

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_source_pool_validity_proxy.py
output: local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1
request_rows: 8
proxy_route_counts:
  request_backend_retrieval_revision_proxy: 2
  request_detector_guarded_observation_proxy: 6
analysis_only_target_route_counts:
  request_backend_retrieval_revision: 2
  request_detector_guarded_observation: 5
  request_lightweight_confirmation: 1
target_backend_rows: 2
target_backend_proxy_backend_rows: 2
target_backend_proxy_evidence_rows: 0
target_evidence_rows: 6
target_evidence_proxy_evidence_rows: 6
target_evidence_proxy_backend_rows: 0
source_pool_validity_proxy_recall: 1.0
evidence_allowed_target_recall: 1.0
consumed_forbidden_rows: 0
proxy_ready_for_detector_gate: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The source-pool score-shape proxy uses non-GT action-time candidate evidence to separate the two backend/source-pool failure rows from the six detector-eligible rows on this diagnostic source. This permits the next detector/viewpoint evidence gate for proxy detector-eligible rows, but it is still not a paper-facing method claim because the thresholds were derived after inspecting current diagnostic evidence.

### Expanded Retrieval Detector Evidence Gate

### 사실

```text
contract: manifests/h001_expanded_retrieval_detector_evidence_v1.json
planner: runtime/h001_runtime/plan_expanded_retrieval_detector_observation.py
plan_output: local_dataset/runs/h001_expanded_retrieval_detector_plan_v1
detector_proxy_request_rows: 6
planned_request_rows: 6
plan_rows: 42
plan_rows_per_request_min/max: 5 / 8
skipped_rows: 18
skipped_reason_counts:
  standoff_navmesh_required: 18
zero_standoff_rows: 0
near_standoff_rows: 0
fallback_rows: 0
rotation_fallback_rows: 0
target_distance_from_viewpoint_m_min/mean/max: 1.7499 / 1.7500 / 1.7521
consumed_forbidden_action_field_count: 0
uses_gt_for_action: false
paper_claim_allowed: false

frame_output: local_dataset/runs/h001_expanded_retrieval_detector_frames_v1
frame_rows/headings: 42 / 168
nonblank_output: local_dataset/runs/h001_expanded_retrieval_detector_frames_v1/nonblank_filter_v1
dropped_rows: 0
removed_blank_heading_count: 0
strict_no_blank_heading_gate_passed: true

detector_job: h001-expanded-retrieval-detector-20260527-141012
detector_output: local_dataset/runs/h001_expanded_retrieval_detector_substrate_v1
detector_job_status: completed
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.0714
rows_with_candidate_association: 3 / 42
passes_detector_substrate_gate: false
projection_status_counts:
  out_of_fov: 134
  visible: 34
depth_check_counts:
  consistent: 6
  depth_mismatch: 28
  out_of_fov: 134

failure_diagnostic_output: local_dataset/runs/h001_expanded_retrieval_detector_failure_diagnostic_v1
failure_diagnostic_gate_passed: true
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

viewpoint_revision_design_output: local_dataset/runs/h001_expanded_retrieval_detector_viewpoint_revision_design_v1
viewpoint_revision_contract: manifests/h001_expanded_retrieval_detector_viewpoint_revision_v1.json
selected_revision: projection_anchor_height_sweep_v1
projection_anchor_height_offsets_m:
  - 0.0
  - 0.4
  - 0.8
  - 1.2
  - 1.6
out_of_fov_axis_counts:
  x_in_y_above: 134
projection_never_visible_recovery:
  offsets_0_0_to_0_8: 29 / 33
  offsets_0_0_to_1_6: 33 / 33

revised_projection_anchor_plan_output: local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1
revised_projection_anchor_plan_schema: h001.expanded_retrieval_detector_observation_plan.v2
revised_projection_anchor_planner: expanded_retrieval_detector_standoff_projection_anchor_v1
revised_projection_anchor_plan_rows: 42
revised_projection_anchor_planned_request_rows: 6
revised_projection_anchor_plan_gate: true
projection_anchor_smoke_output: local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_smoke_v1
projection_anchor_visible_rows: 42 / 42
projection_anchor_visible_rate: 1.0
projection_anchor_frame_passthrough_smoke: local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_frame_passthrough_smoke_v1
projection_anchor_frame_revision_metadata_rows: 2 / 2
projection_anchor_smoke_uses_gt_for_action: false

fixed_anchor_detector_rerun_job:
  status: completed
  tmux_session: h001-expanded-retrieval-detector-anchor-20260527-163608
  working_directory: /home/yoohyun/research3
  output: local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1
  log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/expanded-retrieval-detector-anchor-20260527-163608.log
  status_file: local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1/job_status.json
  expected_files:
    - detector_v3c/summary.json
    - detector_v3c/detector_candidate_associations.jsonl
    - expanded_retrieval_detector_associations.jsonl
    - expanded_retrieval_detector_substrate_summary.json
  launch_command: >-
    cd /home/yoohyun/research3 && TS=20260527-163608 ROOT=/home/yoohyun/research3
    PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1
    FRAME_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_frames_v1
    FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
    FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_frames_v1
    CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1/expanded_retrieval_detector_candidate_artifact.jsonl
    OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1
    EXPECTED_FRAME_ROWS=42 MAX_FRAMES=42 MAX_DEBUG_IMAGES=180 DEVICE=cuda
    PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=0.0,0.4,0.8,1.2,1.6
    LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/expanded-retrieval-detector-anchor-20260527-163608.log
    STATUS=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1/job_status.json
    bash /home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_detector_substrate.sh
  verification_command: >-
    cat local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1/job_status.json &&
    cat local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1/expanded_retrieval_detector_substrate_summary.json
  result:
    detector_rows: 42
    detector_box_rate: 1.0
    sam2_mask_rate: 1.0
    candidate_association_rate: 0.7381
    rows_with_candidate_association: 31 / 42
    associated_candidate_heading_count: 96
    passes_detector_substrate_gate: true
    uses_gt_for_action: false
    paper_claim_allowed: false
```

### 에이전트 추론

The detector evidence gate now has a geometry-safe frame substrate: only source-pool-valid rows are rendered, each candidate observation uses a navmesh standoff viewpoint, and frame export produces no blank rows or headings. The skipped candidates are navmesh-infeasible under the current standoff policy, not GT-filtered. The first detector/SAM2 substrate failed because candidate projection and depth association were weak despite detector boxes and masks being available. The failure taxonomy shows the dominant blocker is not detector availability but out-of-FOV candidate projection, with a smaller depth-mismatch association path. The design probe shows this is vertical anchor uncertainty rather than horizontal yaw: all out-of-FOV projections are `x_in_y_above`, and a category-agnostic projection-anchor height sweep recovers all `projection_never_visible` rows in replay. Revised plan/projection smoke passes and preserves the revision metadata through a 2-row renderer passthrough smoke. The fixed-anchor detector/SAM2 rerun also passes the substrate gate with candidate association rate `0.7381`, compared with the previous `0.0714`. Terminal commit and paper claims remain blocked. Fresh/predeclared source freeze, fresh detector/SAM2 substrate, fresh detector evidence diagnostic, ambiguity-aware objective contract, paper-scale source freeze, local-context branches, recovered-row goal-validity branches, and bounded object-relation branches later pass or are frozen. The current active gate is the fresh object-relation detector/SAM2 substrate documented near the end of this workflow.

### Expanded Retrieval Fresh Validation and Ambiguity Contract

### 사실

```text
fresh_source_manifest: manifests/h001_expanded_retrieval_fresh_validation_v1.json
fresh_source_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_v1
fresh_source_request_rows: 6
fresh_source_scenes: 2
fresh_source_queries: 4
paper_scale_gate_passed: false

fresh_detector_substrate_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_substrate_projection_anchor_v1
fresh_detector_rows: 51
fresh_detector_box_rate: 1.0
fresh_sam2_mask_rate: 1.0
fresh_candidate_association_rate: 0.6078
fresh_rows_with_candidate_association: 31 / 51

fresh_evidence_diagnostic_output: local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_evidence_diagnostic_v1
fresh_evidence_topology_counts:
  multi_strong_saturated_ambiguity: 5
  single_strong_lower_rank: 1
terminal_objective_allowed: false

ambiguity_contract: manifests/h001_expanded_retrieval_ambiguity_objective_v1.json
ambiguity_contract_output: local_dataset/runs/h001_expanded_retrieval_ambiguity_objective_contract_v1
request_rows: 6
route_coverage: 1.0
objective_action_counts:
  request_local_context_disambiguation: 5
  request_rank_challenge_confirmation: 1
terminal_commit_rows: 0
contract_gate_passed: true
larger_source_allowed_after_contract: true
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The fresh-source detector evidence is available but mostly ambiguous. The contract therefore treats detector support as active evidence topology, not as a terminal `ObjectNav` commit rule. This keeps the contribution aligned with semantic uncertainty as active SLAM/navigation utility and permits a larger source freeze without claiming utility yet.

### Expanded Retrieval Paper-Scale Source

### 사실

```text
paper_scale_manifest: manifests/h001_expanded_retrieval_paper_scale_v1.json
source_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_source_v1
source_rows: 23
source_scenes: 10
source_queries: 6
source_filter: defer_expanded_retrieval_needed
excluded_scene_overlap_with_fresh_source: 0
action_evidence_forbidden_key_count: 0
paper_scale_gate_passed: true

planner_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_plan_v1
candidate_set_rows: 23
plan_rows: 230
skipped_rows: 0
expanded_candidates_per_request: 10
planner_gate_passed: true

source_pool_proxy_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_source_pool_validity_proxy_v1
proxy_route_counts:
  request_backend_retrieval_revision_proxy: 2
  request_detector_guarded_observation_proxy: 21
proxy_ready_for_detector_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The paper-scale source is large enough for detector observation and remains nonterminal. Its `21` detector-eligible rows are now planned with the projection-anchor revision before any detector/SAM2 or terminal objective run.

### Expanded Retrieval Paper-Scale Detector Observation and Frame Gate

### 사실

```text
initial_detector_plan_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_v1
detector_proxy_request_rows: 21
planned_request_rows: 21
plan_rows: 162
skipped_rows: 48
skipped_reason_counts:
  standoff_navmesh_required: 48
plan_rows_per_request: 5-10
target_distance_from_viewpoint_m: 1.6335 / 1.7503 / 1.8053
viewpoint_source_counts:
  standoff_navmesh: 162
zero_standoff_rows: 0
near_standoff_rows: 0
fallback_rows: 0
rotation_fallback_rows: 0
initial_anchor_offsets_m: [0.0, 0.4, 0.8, 1.2, 1.6]

initial_frame_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_v1
initial_frame_rows: 162 / 162
initial_rendered_heading_count: 648
initial_nonblank_rows: 162 / 162
initial_removed_blank_heading_count: 0
initial_projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_projection_anchor_smoke_v1
initial_projection_visible_rows: 153 / 162
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

### 에이전트 추론

The initial paper-scale projection failure is a narrow anchor-range failure, not a source-pool or standoff geometry failure. Extending the fixed category-agnostic vertical sweep to `2.4m` repairs the frame substrate while preserving non-GT action inputs. Detector/SAM2 validation is now allowed on the upper-anchor artifact, but terminal utility and paper claims remain blocked.

### Expanded Retrieval Paper-Scale Detector Substrate Job

### 사실

```text
status: completed
tmux_session: h001-paper-expanded-detector-upper-20260527-194607
working_directory: /home/yoohyun/research3
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/paper-scale-expanded-retrieval-detector-substrate-upper-20260527-194607.log
status_file: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/job_status.json
expected_files:
  local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/detector_v3c/summary.json
  local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/detector_v3c/detector_candidate_associations.jsonl
  local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/expanded_retrieval_detector_associations.jsonl
  local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/expanded_retrieval_detector_substrate_summary.json
verification_command:
  cat local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/job_status.json &&
  cat local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/expanded_retrieval_detector_substrate_summary.json
detector_rows: 162
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.8272
rows_with_candidate_association: 134 / 162
associated_candidate_heading_count: 378
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

Exact launch command:

```bash
tmux new-session -d -s h001-paper-expanded-detector-upper-20260527-194607 'cd /home/yoohyun/research3 && TS=20260527-194607 ROOT=/home/yoohyun/research3 RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs MODEL_ROOT=/home/yoohyun/research3/local_dataset/models PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_upper_v1 FRAME_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_upper_v1 FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_upper_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_upper_v1 CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_upper_v1/expanded_retrieval_detector_candidate_artifact.jsonl OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1 DETECTOR_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/detector_v3c OPENVOCAB_IMG=research3/openvocab-perception:20260513-v3c-gdino-sam2 DEVICE=cuda MAX_FRAMES=162 EXPECTED_FRAME_ROWS=162 MAX_HEADINGS_PER_FRAME=0 MAX_DETECTOR_BOXES_PER_HEADING=3 MAX_MASKS_PER_HEADING=3 CANDIDATE_POINT_FIELD=grounded_position PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=0.0,0.4,0.8,1.2,1.6,2.0,2.4 BOX_THRESHOLD=0.10 TEXT_THRESHOLD=0.10 ASSOCIATION_DEPTH_TOLERANCE_M=1.0 MIN_DETECTOR_BOX_RATE=0.80 MIN_SAM2_MASK_RATE=0.80 MIN_CANDIDATE_ASSOCIATION_RATE=0.40 MAX_DEBUG_IMAGES=180 LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/paper-scale-expanded-retrieval-detector-substrate-upper-20260527-194607.log STATUS=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/job_status.json bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_detector_substrate.sh'
```

### 에이전트 추론

The upper-anchor detector/SAM2 substrate removes the detector availability and projection-anchor blocker at paper scale. It still does not justify terminal commitment because the follow-up detector evidence diagnostic shows all request rows are multi-strong saturated ambiguity.

### Expanded Retrieval Paper-Scale Detector Evidence and Local-Context Contract

### 사실

```text
detector_evidence_diagnostic_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_evidence_diagnostic_upper_v1
request_rows: 21
candidate_rows: 162
association_heading_rows: 648
associated_request_count: 21 / 21
associated_request_rate: 1.0
strong_request_rate: 1.0
multi_strong_request_rate: 1.0
lower_rank_only_association_rate: 0.2381
evidence_topology_counts:
  multi_strong_saturated_ambiguity: 21
terminal_objective_risk_counts:
  multi_candidate_detector_ambiguity: 21
diagnostic_gate_passed: true
paper_scale_gate_passed: true
terminal_objective_allowed: false
uses_gt_for_action: false
uses_gt_for_analysis: false
paper_claim_allowed: false

ambiguity_objective_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_ambiguity_objective_upper_v1
request_rows: 21
route_coverage: 1.0
objective_action_counts:
  request_local_context_disambiguation: 21
terminal_commit_rows: 0
contract_gate_passed: true
larger_source_allowed_after_contract: true
terminal_objective_allowed: false
uses_gt_for_action: false
uses_gt_for_analysis: false
paper_claim_allowed: false

local_context_contract: manifests/h001_expanded_retrieval_local_context_disambiguation_v1.json
contract_status: design_contract_only
planner_name: expanded_retrieval_local_context_disambiguation_v1
source_filter: objective_action == request_local_context_disambiguation
planned_request_rows_minimum: 18
planned_request_coverage_minimum: 0.85
projection_visible_row_rate_minimum: 0.95
detector_box_rate_minimum: 0.80
sam2_mask_rate_minimum: 0.80
candidate_association_rate_minimum: 0.40
local_context_evidence_available_rate_minimum: 0.50
terminal_rule: local_context_unique_own_view_advantage
wrong_goal_commit_rate_maximum: 0.0
success_commit_rows_minimum: 2
direct_detector_score_commit_allowed: false
source_top_if_associated_commit_allowed: false
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The current paper-scale evidence is positive substrate evidence but negative terminal evidence: detector support is available, yet every request remains multi-candidate ambiguous. The frozen local-context contract turns that negative result into the next active observation step. The next implementation must show whether local context can produce a unique own-view advantage; otherwise the method should stay in defer/request mode rather than becoming a detector-score commit rule.

### Expanded Retrieval Paper-Scale Local-Context Planner Smoke

### 사실

```text
planner: runtime/h001_runtime/plan_expanded_retrieval_local_context_disambiguation.py
contract: manifests/h001_expanded_retrieval_local_context_disambiguation_v1.json
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1
summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan_summary.json
plan: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan.jsonl
candidate_artifact: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl
request_rows: 21
planned_request_rows: 21
planned_request_coverage: 1.0
plan_rows: 113
skipped_rows: 3
skipped_reason:
  standoff_navmesh_required: 3
plan_rows_per_request_min/max: 2 / 6
viewpoint_source:
  standoff_navmesh: 113
candidate_roles:
  detector_strong_candidate: 19
  detector_strong_rival: 54
  local_context_candidate: 20
  source_top: 11
  source_top+detector_strong_candidate: 2
  source_top+detector_strong_rival: 7
zero_standoff_rows: 0
near_standoff_rows: 0
fallback_rows: 0
rotation_fallback_rows: 0
nonfinite_candidate_position_rows: 0
consumed_forbidden_action_field_count: 0
output_forbidden_action_field_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
planner_gate_passed: true
```

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.plan_expanded_retrieval_local_context_disambiguation \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_disambiguation_v1.json \
    --ambiguity-rows /runs/h001_expanded_retrieval_paper_scale_ambiguity_objective_upper_v1/expanded_retrieval_ambiguity_objective_rows.jsonl \
    --candidate-set /runs/h001_expanded_retrieval_paper_scale_plan_v1/expanded_retrieval_candidate_set.jsonl \
    --detector-candidate-rows /runs/h001_expanded_retrieval_paper_scale_detector_evidence_diagnostic_upper_v1/expanded_retrieval_detector_evidence_candidate_rows.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1 \
    --data-root /data \
    --run-id h001_expanded_retrieval_paper_scale_local_context_plan_v1
```

### 에이전트 추론

Planner smoke clears the local-context action substrate gate without using joined evaluation labels. This does not prove ObjectNav utility; it only allows the next frame/nonblank/projection smoke on the local-context plan.

### Expanded Retrieval Paper-Scale Local-Context Frame/Projection Smoke

### 사실

```text
frame_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1
frame_summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/summary.json
filtered_frame_summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
nonblank_summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json
projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_projection_smoke_v1
projection_smoke_summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_projection_smoke_v1/projection_anchor_smoke_summary.json
frame_rows: 113 / 113
rendered_heading_count: 1285
headings_per_row_min/max: 7 / 17
unique_scenes: 9
nonblank_rows: 113 / 113
removed_blank_heading_count: 0
strict_no_blank_heading_gate_passed: true
projection_visible_rows: 113 / 113
projection_visible_rate: 1.0
missing_candidate_rows: 0
frame_revision_metadata_rows: 113
candidate_selection_source:
  explicit_candidate_ids: 113
uses_gt_for_action: false
paper_claim_allowed: false
projection_smoke_gate_passed: true
```

Frame export command:

```bash
docker run --rm --gpus all --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan.jsonl \
    --candidate-artifact /runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1 \
    --policy ExpandedRetrievalLocalContextDisambiguation \
    --candidate-point-field grounded_position \
    --max-candidates-per-decision 6 \
    --yaw-offsets=-30,0,30 \
    --width 160 \
    --height 120 \
    --camera-height 1.5 \
    --hfov 90
```

Nonblank/projection smoke commands:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.filter_nonblank_frame_summary \
    --frame-summary /runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/rival_identity_frame_summary.jsonl \
    --frame-root /runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1 \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1 \
    --min-stddev 0.0

docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.smoke_expanded_retrieval_projection_anchor \
    --frames /runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl \
    --frame-root /runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1 \
    --candidate-artifact /runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_projection_smoke_v1 \
    --projection-anchor-height-offsets-m 0.0,0.4,0.8,1.2,1.6,2.0,2.4 \
    --candidate-point-field grounded_position \
    --max-candidates-per-frame 6 \
    --expected-rows 113 \
    --min-visible-row-rate 0.95
```

### 에이전트 추론

The local-context frame substrate is detector-ready: every planned local-context row rendered, every row kept nonblank, and every target candidate has at least one visible projection anchor. This is still a substrate result, not terminal utility.

### Expanded Retrieval Paper-Scale Local-Context Detector/SAM2 Substrate Job

### 사실

```text
date_launched: 2026-05-27
job_status: completed
tmux_session: h001-paper-local-context-detector-20260527-205216
working_directory: /home/yoohyun/research3
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
frames: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
frame_root: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1
candidate_artifact: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1
detector_out: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/detector_v3c
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/paper-scale-local-context-detector-substrate-20260527-205216.log
status: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/job_status.json
expected_frame_rows: 113
expected_policy: ExpandedRetrievalLocalContextDisambiguation
projection_anchor_height_offsets_m: 0.0,0.4,0.8,1.2,1.6,2.0,2.4
candidate_point_field: grounded_position
detector_rows: 113
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.9203539823008849
rows_with_candidate_association: 104 / 113
associated_candidate_heading_count: 365
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

Expected files:

```text
local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/detector_v3c/summary.json
local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/detector_v3c/detector_candidate_associations.jsonl
local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_associations.jsonl
local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json
```

Verification command:

```bash
cat local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/job_status.json
cat local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json
```

Launch command:

```bash
TS=20260527-205216
tmux new-session -d -s h001-paper-local-context-detector-${TS} \
  'cd /home/yoohyun/research3 && \
  TS=20260527-205216 \
  ROOT=/home/yoohyun/research3 \
  HYP=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation \
  RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs \
  MODEL_ROOT=/home/yoohyun/research3/local_dataset/models \
  PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1 \
  FRAME_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1 \
  FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl \
  FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1 \
  FRAME_EXPORT_SUMMARY=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/summary.json \
  CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl \
  OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1 \
  DETECTOR_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/detector_v3c \
  OPENVOCAB_IMG=research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  DEVICE=cuda \
  MAX_FRAMES=113 \
  EXPECTED_FRAME_ROWS=113 \
  EXPECTED_POLICY=ExpandedRetrievalLocalContextDisambiguation \
  MAX_HEADINGS_PER_FRAME=0 \
  MAX_DETECTOR_BOXES_PER_HEADING=3 \
  MAX_MASKS_PER_HEADING=3 \
  CANDIDATE_POINT_FIELD=grounded_position \
  PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=0.0,0.4,0.8,1.2,1.6,2.0,2.4 \
  BOX_THRESHOLD=0.10 \
  TEXT_THRESHOLD=0.10 \
  ASSOCIATION_DEPTH_TOLERANCE_M=1.0 \
  MIN_DETECTOR_BOX_RATE=0.80 \
  MIN_SAM2_MASK_RATE=0.80 \
  MIN_CANDIDATE_ASSOCIATION_RATE=0.40 \
  MAX_DEBUG_IMAGES=180 \
  LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/paper-scale-local-context-detector-substrate-20260527-205216.log \
  STATUS=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/job_status.json \
  bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_detector_substrate.sh'
```

### 에이전트 추론

This job clears the detector substrate gate for the local-context branch. It should not be interpreted as terminal navigation utility until post-observation evidence and simpler-alternative comparison pass.

### Expanded Retrieval Paper-Scale Local-Context Post-Observation Evaluation

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_local_context_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1
summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1/expanded_retrieval_local_context_post_observation_summary.json
plan: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan.jsonl
detector_associations: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_associations.jsonl
evaluation_labels: local_dataset/runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl
request_rows: 21
evidence_rows: 113
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.9203539823008849
strong_own_view_request_rows: 19 / 21
local_context_candidate_rows: 20
local_context_candidate_strong_rows: 6
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Proposed variant:

```text
variant: proposed_local_context_unique_own_view_advantage
commit_rows: 10 / 21
success_commit_rows: 3
wrong_goal_commit_rows: 7
no_valid_commit_rows: 3
success_commit_rate: 0.14285714285714285
wrong_goal_commit_rate: 0.3333333333333333
failure_taxonomy:
  ambiguous_multiple_strong_own_view: 9
  no_strong_own_view_evidence: 2
  no_valid_candidate_commit: 3
  success: 3
  wrong_instance_selected_by_local_context_evidence: 4
post_observation_gate_passed: false
```

Simpler alternatives:

```text
defer_all: commit/success/wrong/no-valid = 0 / 0 / 0 / 0
semantic_top: commit/success/wrong/no-valid = 21 / 11 / 10 / 4
source_top_if_associated: commit/success/wrong/no-valid = 18 / 9 / 9 / 3
detector_score_best: commit/success/wrong/no-valid = 21 / 6 / 15 / 4
own_support_best: commit/success/wrong/no-valid = 21 / 9 / 12 / 4
local_context_only_best: commit/success/wrong/no-valid = 15 / 5 / 10 / 4
```

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_local_context_evidence \
    --plan /runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan.jsonl \
    --detector-associations /runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_associations.jsonl \
    --detector-summary /runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/detector_v3c/summary.json \
    --evaluation-labels /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1
```

### 에이전트 추론

The local-context detector substrate is strong, but terminal local-context commitment is unsafe on the paper-scale rows. This is a useful negative result: own-view detector/SAM2 support still does not equal ObjectNav goal validity in repeated-object scenes, and no-valid source-pool rows remain a separate failure. The next step is failure diagnosis, not threshold tuning or policy-scale promotion.

### Expanded Retrieval Paper-Scale Local-Context Failure Diagnosis

### 사실

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_local_context_failures.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_failure_diagnostic_v1
summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_failure_diagnostic_v1/expanded_retrieval_local_context_failure_summary.json
rows: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_failure_diagnostic_v1/expanded_retrieval_local_context_failure_rows.jsonl
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

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.diagnose_expanded_retrieval_local_context_failures \
    --evidence-rows /runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1/expanded_retrieval_local_context_evidence_rows.jsonl \
    --evaluated-rows /runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1/expanded_retrieval_local_context_evaluated_rows.jsonl \
    --evaluation-labels /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_failure_diagnostic_v1
```

### 에이전트 추론

There are two separate blockers. First, some source-pool rows have no correct planned candidate, so any terminal commit is invalid regardless of viewpoint evidence. Second, when a correct candidate exists, own-view detector/SAM2 support can be stronger for the wrong repeated instance than for the correct one. The next objective contract must separate no-valid pool repair from wrong-instance arbitration and must not promote detector-score, source-top, own-support, or local-context-only alternatives.

### Expanded Retrieval Paper-Scale Revised Local-Context Objective Contract

### 사실

```text
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_revision_v1.json
verify: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_revision_v1.verify.json
status: frozen_design_contract_before_implementation
objective_name: goal_validity_guarded_local_context_v1
guard_order:
  1. pool_validity_guard_v2
  2. wrong_instance_arbitration_guard_v1
blocked_shortcuts:
  semantic_top
  source_top_if_associated
  detector_score_best
  own_support_best
  local_context_only_best
  local_context_unique_own_view_advantage_without_pool_validity_guard
expected_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The revised contract turns the negative local-context result into two explicit routes. Rows whose action-time evidence cannot establish a valid candidate pool must request backend retrieval revision or defer. Rows with a valid-looking pool but unresolved repeated-instance identity must request goal-validity confirmation or defer. A terminal commit is allowed only after both guards pass, so own-view category evidence no longer acts as ObjectNav goal-validity evidence by itself.

### Expanded Retrieval Paper-Scale Revised Local-Context Analyzer

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_local_context_revision.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1
summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_summary.json
request/evidence/decision/evaluated_rows: 21 / 113 / 168 / 168
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.9203539823008849
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

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_local_context_revision \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_revision_v1.json \
    --plan /runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan.jsonl \
    --detector-associations /runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_associations.jsonl \
    --detector-summary /runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/detector_v3c/summary.json \
    --source-pool-proxy-rows /runs/h001_expanded_retrieval_paper_scale_source_pool_validity_proxy_v1/expanded_retrieval_source_pool_validity_proxy_rows.jsonl \
    --evaluation-labels /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1
```

### 에이전트 추론

The revised analyzer successfully blocks the previous unsafe terminal commits, but it is safe-but-inert. This is not a paper utility result. It shows that the current action-time evidence can route uncertainty to confirmation/defer, but cannot yet convert local-context evidence into safe nonzero `ObjectNav` goal commitment. The next step is route diagnosis, not threshold tuning.

### Expanded Retrieval Paper-Scale Revised Local-Context Route Diagnosis

### 사실

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_local_context_revision_routes.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1
summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1/expanded_retrieval_local_context_revision_route_summary.json
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
  no_valid_candidate_pool_after_label_join: 4
  unsafe_previous_commit_prevented: 7
  previous_rule_success_lost_by_guard: 3
  correct_and_wrong_both_strong_own_view: 7
  wrong_only_strong_own_view: 7
  correct_candidate_not_strong_own_view: 5
  detector_strong_visibility_not_goal_validity: 9
  multi_strong_own_view_ambiguity: 9
  simpler_alternatives_unsafe_analysis_only: 20
  some_simpler_alternative_succeeds_analysis_only: 15
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.diagnose_expanded_retrieval_local_context_revision_routes \
    --evidence-rows /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_evidence_rows.jsonl \
    --decision-rows /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_decision_rows.jsonl \
    --evaluated-rows /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_evaluated_rows.jsonl \
    --evaluation-labels /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1
```

### 에이전트 추론

There are two next design constraints. First, `pool_validity_guard_v2` is not sufficient: it passes four no-valid rows, so backend/source-pool repair must be a first-class branch. Second, valid-pool rows still cannot use own-view category evidence as a commit authority because correct and wrong repeated instances are often both strong, or only wrong instances are strong. The next contract should define source-pool repair and goal-validity confirmation separately.

### Expanded Retrieval Paper-Scale Route-Specific Local-Context Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_local_context_route_contract_v1.json
verify: manifests/h001_expanded_retrieval_local_context_route_contract_v1.verify.json
status: frozen_design_contract_before_implementation
source_revision_output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1
source_route_diagnostic: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1
branches:
  source_pool_repair_v1: request_source_pool_repair
  goal_validity_confirmation_v1: request_goal_validity_confirmation_evidence
  instance_arbitration_defer_v1: defer_instance_arbitration_unresolved
terminal_commit_allowed: false
routes_all_request_rows_required: 21
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_action_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

This contract fixes the next implementation target as branch routing, not a terminal utility rule. The source-pool branch must test whether the candidate pool itself is trustworthy before goal-validity evidence is considered. The goal-validity branch must add candidate-specific confirmation stronger than object/category visibility. The contract intentionally keeps terminal commits blocked because the current evidence only proves that unsafe shortcuts exist and that the strict guard is inert.

### Expanded Retrieval Paper-Scale Route-Specific Local-Context Analyzer

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_local_context_route_specific.py
output: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1
summary: local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1/expanded_retrieval_local_context_route_specific_summary.json
request_rows: 21
route_action_counts:
  request_source_pool_repair: 5
  request_goal_validity_confirmation_evidence: 7
  defer_instance_arbitration_unresolved: 9
route_counts_for_no_valid_rows:
  request_source_pool_repair: 4
route_counts_for_valid_rows:
  request_source_pool_repair: 1
  request_goal_validity_confirmation_evidence: 7
  defer_instance_arbitration_unresolved: 9
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
route_contract_gate_passed: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_local_context_route_specific \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_route_contract_v1.json \
    --evidence-rows /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_evidence_rows.jsonl \
    --decision-rows /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_decision_rows.jsonl \
    --evaluated-rows /runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_evaluated_rows.jsonl \
    --evaluation-labels /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1
```

### 에이전트 추론

The route-specific analyzer converts the safe-but-inert local-context result into a branch plan. It is useful because all four no-valid rows are kept out of the goal-validity branch and routed to source-pool repair, while seven rows remain available for future goal-validity confirmation evidence. It is still not a utility claim: one valid row is conservatively routed to source-pool repair, and no terminal commits are allowed. The next contract should therefore define source-pool repair evidence before goal-validity confirmation or policy-scale comparison.

### Expanded Retrieval Source-Pool Repair Evidence Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_source_pool_repair_v1.json
verify: manifests/h001_expanded_retrieval_source_pool_repair_v1.verify.json
status: frozen_design_contract_before_implementation
source_filter:
  route_action: request_source_pool_repair
source_rows: 5
post_action_no_valid_rows: 4
post_action_valid_but_conservative_repair_rows: 1
required_route_actions:
  request_backend_pool_expansion
  route_to_goal_validity_confirmation_after_pool_repair
  defer_source_pool_unresolved
terminal_commit_allowed: false
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_action_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Target rows:

| Request id | Scene | Query | Action-time route signal |
| --- | --- | --- | --- |
| `rival_identity:8` | `Dd4bFSTQ8gi` | `bed` | `source_top_visibility_not_goal_validity` |
| `rival_identity:10` | `qyAac8rV8Zk` | `tv_monitor` | `no_strong_own_view_candidate` |
| `rival_identity:12` | `QaLdnwvtxbs` | `bed` | `expanded_local_context_pool_not_validated` |
| `rival_identity:13` | `bxsVRursffK` | `bed` | `no_strong_own_view_candidate` |
| `rival_identity:14` | `QaLdnwvtxbs` | `bed` | `expanded_local_context_pool_not_validated` |

### 에이전트 추론

The repair contract should not try to prove a goal instance. Its role is narrower: decide whether the candidate pool needs backend expansion, can be handed to goal-validity confirmation after repair, or must remain unresolved. This keeps no-valid and weak-pool cases from contaminating goal-validity confirmation. Passing this contract only permits a source-pool repair analyzer; it does not permit terminal commits or policy-scale comparison.

### Expanded Retrieval Source-Pool Repair Analyzer Result

### 사실

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
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The current repair rows should not be handed directly to goal-validity confirmation. Four are no-valid after evaluation-only label join, and the one valid row lacks enough action-time source-pool evidence to distinguish it from the no-valid cases without backend expansion. The next contract should therefore define backend pool expansion evidence and its handoff criteria before goal-validity confirmation.

### Expanded Retrieval Backend Pool Expansion Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_backend_pool_expansion_v1.json
verify: manifests/h001_expanded_retrieval_backend_pool_expansion_v1.verify.json
status: frozen_design_contract_before_implementation
source_filter:
  repair_action: request_backend_pool_expansion
source_rows: 5
post_action_no_valid_rows: 4
post_action_valid_but_not_goal_validity_ready_rows: 1
required_route_actions:
  request_backend_candidate_generation
  route_to_goal_validity_confirmation_after_expansion
  defer_backend_pool_unresolved
terminal_commit_allowed: false
action_evidence_forbidden_key_count_maximum: 0
expanded_candidate_accounting_required: true
duplicate_and_reachability_accounting_required: true
label_join_only_after_expansion_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

This contract freezes backend expansion as the next branch, not a terminal rule. It allows fixed non-GT candidate generation, spatial diversity, reachability checks, and later detector/local-context evidence only after expansion. It rejects pass-through to goal-validity confirmation until an expanded pool is candidate-accountable and action-time safe enough to hand off. If dense re-export is needed, it must be launched as a background job with logged command and verification.

### Expanded Retrieval Backend Pool Expansion Analyzer

### 사실

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
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The available paper-scale candidate artifact is only a top-10 preview. It is useful for accounting and post-action diagnosis, but it does not meet the fixed backend expansion budget of at least `20` candidates. The next step is therefore not goal-validity confirmation; it is a fixed non-GT backend candidate generation contract that materializes a larger, spatially accountable pool.

### Expanded Retrieval Backend Candidate Generation Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_backend_candidate_generation_v1.json
verify: manifests/h001_expanded_retrieval_backend_candidate_generation_v1.verify.json
status: frozen_design_contract_before_implementation
source_filter:
  backend_route_action: request_backend_candidate_generation
source_rows: 5
fixed_generation_policy: fixed_action_evidence_top20_v1
candidate_backend_family: existing_vlmaps_action_evidence_jsonl
generated_candidate_count_per_row: 20
expected_generated_candidate_rows: 100
source_action_evidence_rows_available_for_targets: 5
required_outputs:
  backend_candidate_generation_rows.jsonl
  backend_candidate_generation_evaluated_rows.jsonl
  backend_candidate_generation_summary.json
terminal_commit_allowed: false
action_evidence_forbidden_key_count_maximum: 0
duplicate_candidate_id_count_maximum: 0
nonfinite_candidate_position_count_maximum: 0
label_join_only_after_generation_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

This contract deliberately tests the existing top-20 non-GT action evidence before launching a deeper dense backend job. If fixed top-20 generation still leaves no-valid pools after evaluation-only reporting, the next contract should be deeper backend generation, not goal-validity confirmation.

### Expanded Retrieval Backend Candidate Generation Analyzer

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_backend_candidate_generation.py
output: local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1
summary: local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1/backend_candidate_generation_summary.json
generation_rows: local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1/backend_candidate_generation_rows.jsonl
evaluated_rows: local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1/backend_candidate_generation_evaluated_rows.jsonl
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
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

Command:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_backend_candidate_generation \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_backend_candidate_generation_v1.json \
    --backend-expansion-rows /runs/h001_expanded_retrieval_backend_pool_expansion_v1/backend_pool_expansion_rows.jsonl \
    --source-action-evidence /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_action_evidence_rows.jsonl \
    --evaluation-labels /runs/h001_rival_identity_goal_validity_independent_source_v1/rival_identity_goal_validity_independent_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_backend_candidate_generation_v1
```

### 에이전트 추론

The fixed top-20 action evidence passes the structural candidate generation gate, so the immediate blocker is not candidate count or lineage. The remaining blocker is candidate-pool validity: post-generation evaluation-only labels still show `3/5` no-valid pools. The next contract should therefore test deeper backend generation or a non-GT pool-validity proxy before goal-validity confirmation.

### Expanded Retrieval Deeper Backend Generation Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_deeper_backend_generation_v1.json
verify: manifests/h001_expanded_retrieval_deeper_backend_generation_v1.verify.json
status: frozen_design_contract_before_implementation
source_rows: 5 fixed top-20 generation rows
diagnostic_target_request_rows: 3 no-valid rows after evaluation-only label join
target_scene_query_pairs: 2
target_scene_query_keys:
  QaLdnwvtxbs::bed
  bxsVRursffK::bed
first_variant: spatial_nms_p90_k100_d5_v1
expected_candidate_count_minimum_per_request: 50
expected_candidate_count_primary_target_per_request: 100
expected_new_beyond_top20_minimum_per_request: 30
generated_candidate_rows_minimum: 150
required_outputs:
  deeper_backend_generation_rows.jsonl
  deeper_backend_generation_evaluated_rows.jsonl
  deeper_backend_generation_summary.json
  deeper_backend_scene_query_artifacts.jsonl
terminal_commit_allowed: false
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_generation_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

This contract is a diagnostic backend recall repair contract. It freezes the first deeper generation variant before implementation, but it does not allow a paper method claim because the diagnostic target rows are selected after evaluation-only no-valid reporting. The next implementation should materialize target scene/query specs and deeper candidate rows first, then join labels only for recovery analysis.

### Expanded Retrieval Deeper Backend Generation Analyzer / Job

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_deeper_backend_generation.py
job: runtime/jobs/expanded_retrieval_deeper_backend_generation.sh
target_spec_output: local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1
existing_artifact_smoke_output: local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_existing_p97_k20_smoke_v1
full_job_session: h001-deeper-backend-20260529-003000
full_job_status: completed
full_job_log: runtime/logs/expanded-retrieval-deeper-backend-generation-20260529-003000.log
full_job_output: local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1
full_job_candidate_artifact: local_dataset/runs/h001_expanded_retrieval_deeper_backend_artifact_spatial_nms_p90_k100_d5_v1/all_scenes_aligned.jsonl
target_spec_source_rows: 5
target_spec_request_rows: 3
target_scene_query_pairs: 2
target_spec_terminal_commit_rows: 0
target_spec_action_forbidden_keys: 0
existing_artifact_candidate_rows: 60
existing_artifact_candidate_count_per_request: 20
existing_artifact_new_beyond_top20: 0
existing_artifact_valid_containing_rows: 0
existing_artifact_no_valid_rows: 3
existing_artifact_gate_passed: false
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
full_gate_passed: true
goal_validity_confirmation_unblocked: true
paper_claim_allowed: false
```

### 에이전트 추론

The analyzer/job implementation closes the target-spec and schema step. The existing `p97_k20` artifact smoke is useful because it exercises artifact loading, scene-key normalization, nonfinite-candidate handling, action/evaluation separation, and label join. It is expected to fail the deeper gate because it is not the fixed `spatial_nms_p90_k100_d5_v1` variant and adds no new candidates beyond top-20. The completed full job shows backend recall repair is partially effective: `QaLdnwvtxbs::bed` recovers valid candidates, while `bxsVRursffK::bed` remains no-valid. The next contract should split these paths instead of passing all three rows into one goal-validity confirmation rule.

### Expanded Retrieval Goal-Validity Confirmation Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.verify.json
status: frozen_design_contract_before_implementation
source_rows: 3 deeper backend generation rows
goal_validity_request_rows: 2
goal_validity_request_ids:
  rival_identity:12
  rival_identity:14
backend_pool_validity_branch_rows: 1
backend_pool_validity_request_ids:
  rival_identity:13
candidate_count_per_request: 100
new_beyond_top20_per_request: 80
terminal_commit_allowed: false
action_evidence_forbidden_key_count_maximum: 0
label_join_only_after_request_and_evidence_rows: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
```

### 에이전트 추론

The recovered-row contract is a branch-separation gate. It allows goal-validity evidence only where the deeper backend has recovered a valid pool under evaluation-only analysis, and it keeps the still-no-valid row on a backend/pool-validity branch. This avoids treating object/category observation evidence as an explanation for a row that still has no candidate capable of satisfying the ObjectNav goal.

### Expanded Retrieval Goal-Validity Confirmation Analyzer

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_confirmation.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1
request_rows: 2
branch_rows: 1
evidence_rows: 200
evaluated_rows: 3
handoff_action_counts:
  request_goal_validity_confirmation_evidence: 2
  request_non_gt_pool_validity_proxy_or_fallback_backend_variant: 1
request_ids:
  rival_identity:12
  rival_identity:14
branch_request_ids:
  rival_identity:13
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
goal_validity_confirmation_request_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

### 에이전트 추론

The analyzer materializes the split required by the contract. It does not prove a terminal policy; it keeps recovered-pool goal-validity evidence and still-no-valid backend/pool validity as separate branches. The still-no-valid branch is now specified by the pool-validity fallback contract below.

## Expanded Retrieval Pool-Validity Branch Fallback Contract

### 사실

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
paper_claim_allowed: false
```

### 에이전트 추론

The still-no-valid `bxsVRursffK::bed` branch is not separable by simple non-GT structural proxy: it has more reachable/standoff candidates than the recovered rows and the same positive-support count. The next implementation should therefore materialize the fixed fallback backend variant rather than tune a proxy on the diagnostic label join. Goal-validity confirmation remains blocked for this branch until fallback generation rows are written label-free and recovery is checked only after generation.

## Expanded Retrieval Pool-Validity Branch Analyzer / Job

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_branch.py
job: runtime/jobs/expanded_retrieval_pool_validity_branch.sh
target_spec_output: local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1
target_spec_branch_rows: 1
target_spec_action_rows: 1
target_spec_evaluated_rows: 1
target_spec_status_counts:
  defer_pool_validity_fallback_unresolved: 1
target_spec_reason:
  fallback_candidate_artifact_row_missing: 1
target_spec_gate_passed: false
target_spec_terminal_commit_rows: 0
target_spec_action_forbidden_keys: 0
tmux_session: h001-pool-validity-fallback-20260529-093033
status_file: local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1/job_status.json
current_status: completed
current_stage: completed
log: runtime/logs/expanded-retrieval-pool-validity-branch-20260529-093033.log
artifact_out: local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_spatial_nms_p80_k200_d3_v1
artifact_coverage_ok: true
artifact_scene_count: 1
artifact_query_rows: 6
artifact_candidates: 1200
final_fallback_candidate_rows: 200
final_new_beyond_previous_pool: 100
final_gate_passed: true
final_valid_containing_rows: 0
final_no_valid_rows: 1
goal_validity_confirmation_unblocked: false
second_fallback_backend_required: true
verification_command:
  cat local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1/job_status.json
  cat local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_spatial_nms_p80_k200_d3_v1/coverage_check.json
  cat local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1/pool_validity_summary.json
```

### 에이전트 추론

The target-spec smoke confirms the branch analyzer preserves action/evaluation separation before the expensive artifact exists. The completed first fallback shows the wider spatial NMS backend is structurally adequate but still does not recover a valid goal candidate for `bxsVRursffK::bed`. The next branch should either materialize the predeclared component fallback or, after that fails, record a backend blind-spot note instead of sending this row to goal-validity confirmation.

## Expanded Retrieval Pool-Validity Second Fallback Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.json
verify: manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.verify.json
status: frozen_design_contract_before_implementation
source_branch_rows: 1
target_request_ids:
  rival_identity:13
target_scene_query_keys:
  bxsVRursffK::bed
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
paper_claim_allowed: false
```

### 에이전트 추론

The frozen second fallback keeps the branch diagnostic and label-separated. It tests whether component-level map export recovers a valid candidate where wider point-level spatial NMS did not. This is not a terminal utility rule; the branch either becomes eligible for later goal-validity evidence after evaluation-only recovery, or becomes a backend/source-map recall blind spot if the component fallback also remains no-valid.

## Expanded Retrieval Pool-Validity Second Fallback Analyzer / Job

### 사실

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_second_fallback.py
job: runtime/jobs/expanded_retrieval_pool_validity_second_fallback.sh
target_spec_output: local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1
target_spec_branch_rows: 1
target_spec_action_rows: 1
target_spec_evaluated_rows: 1
target_spec_status_counts:
  defer_component_fallback_unresolved: 1
target_spec_reason:
  component_candidate_artifact_row_missing: 1
target_spec_gate_passed: false
target_spec_terminal_commit_rows: 0
target_spec_action_forbidden_keys: 0
tmux_session: h001-pool-validity-second-fallback-20260529-151217
status_file: local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1/job_status.json
current_status: completed
current_stage: completed
log: runtime/logs/expanded-retrieval-pool-validity-second-fallback-20260529-151217.log
artifact_out: local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_components_p80_min1_k200_v1
artifact_coverage_ok: true
artifact_scene_count: 1
artifact_query_rows: 6
artifact_candidates: 1163
final_component_candidate_rows: 200
final_component_cells_min_mean_max: 1 / 20.29 / 1254
final_new_positions_beyond_first_fallback: 200
final_gate_passed: true
final_valid_containing_rows: 0
final_no_valid_rows: 1
goal_validity_confirmation_unblocked: false
backend_source_map_blind_spot_after_second_fallback: true
verification_command:
  cat local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1/job_status.json
  cat local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_components_p80_min1_k200_v1/coverage_check.json
  cat local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1/second_fallback_summary.json
```

### 에이전트 추론

The component fallback rules out the simplest backend-granularity explanation for `bxsVRursffK::bed` under this diagnostic branch. Since both wider spatial NMS and component export are structurally valid but no-valid, the branch should be treated as source-map/backend recall failure rather than goal-validity ambiguity. The next active branch is candidate-specific goal-validity evidence for recovered rows `rival_identity:12` and `rival_identity:14`.

## Expanded Retrieval Candidate-Specific Goal-Validity Evidence Contract / Planner

### 사실

The evidence contract is frozen at:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_evidence_v1.json
```

It consumes:

```text
local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1/goal_validity_confirmation_request_rows.jsonl
local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1/goal_validity_confirmation_evidence_rows.jsonl
```

The target request ids are `rival_identity:12` and `rival_identity:14`. The planner/objective separates `candidate_specific_support`, `category_only_support`, `cross_view_or_rival_ambiguous`, `no_visual_support`, and `unrenderable_or_unreachable`. Terminal commit is not allowed.

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
target_distance_min_mean_max_m: 1.5952 / 1.7506 / 1.8677
viewpoint_source_counts: standoff_navmesh 158
terminal_commit_rows: 0
output_forbidden_action_field_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
goal_validity_evidence_plan_gate_passed: true
```

Verification command:

```bash
jq -e '.gate.goal_validity_evidence_plan_gate_passed == true and .plan_rows == 158 and .skipped_rows == 42 and .output_forbidden_action_field_count == 0 and .terminal_commit_rows == 0 and .uses_gt_for_action == false and .paper_claim_allowed == false' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan_summary.json
```

### 에이전트 추론

This closes the planner/objective definition step for recovered rows. The result is not terminal utility evidence. It only says the recovered candidate pools can be converted into label-free, candidate-specific standoff observation rows with local rival context. The bounded frame/projection smoke now passes, so the next step is detector/SAM2 scoring.

### Expanded Retrieval Candidate-Specific Goal-Validity Frame/Projection Smoke

### 사실

```text
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1
filtered_frame_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
projection_smoke_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_smoke_v1
bounded_rows: 20
frame_rows: 20 / 20
rendered_heading_count: 172
headings_per_row_min/max: 5 / 11
unique_scenes: 1
nonblank_rows: 20 / 20
removed_blank_heading_count: 0
strict_no_blank_heading_gate_passed: true
projection_visible_rows: 20 / 20
projection_visible_rate: 1.0
missing_candidate_rows: 0
frame_revision_metadata_rows: 20
candidate_selection_source:
  explicit_candidate_ids: 20
uses_gt_for_action: false
paper_claim_allowed: false
projection_smoke_gate_passed: true
```

Verification command:

```bash
jq '{rows_requested,rows_exported,rendered_heading_count,min_headings_per_row,max_headings_per_row,unique_scenes,candidate_point_field,uses_gt_for_action}' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/summary.json
jq '{input_rows,output_rows,dropped_rows,removed_blank_heading_count,row_level_nonblank_gate_passed,strict_no_blank_heading_gate_passed,uses_gt_for_action}' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json
jq '{rows,projection_anchor_visible_rows,projection_anchor_visible_rate,missing_candidate_rows,frame_revision_metadata_rows,candidate_selection_source_counts,gate,uses_gt_for_action,paper_claim_allowed}' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_smoke_v1/projection_anchor_smoke_summary.json
```

### 에이전트 추론

The bounded smoke removes the immediate rendering/projection blocker for candidate-specific goal-validity evidence. It does not prove detector evidence quality or terminal utility. The next gate is detector/SAM2 substrate on the filtered frame summary, followed by a post-detector objective analyzer.

### Expanded Retrieval Candidate-Specific Goal-Validity Detector/SAM2 Substrate Job

### 사실

```text
status: completed
tmux_session: h001-goal-validity-detector-20260529-171217
script: runtime/jobs/expanded_retrieval_detector_substrate.sh
frames: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
frame_root: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1
candidate_artifact: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_candidate_artifact.jsonl
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1
detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/detector_v3c
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/goal-validity-evidence-detector-substrate-20260529-171217.log
expected_frame_rows: 20
expected_policy: ExpandedRetrievalGoalValidityEvidence
max_frames: 20
candidate_point_field: grounded_position
projection_anchor_height_offsets_m: 0.0,0.4,0.8,1.2,1.6,2.0,2.4
min_detector_box_rate: 0.80
min_sam2_mask_rate: 0.80
min_candidate_association_rate: 0.40
detector_rows: 20
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.95
rows_with_candidate_association: 19
passes_detector_substrate_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

Launch command:

```bash
tmux new-session -d -s h001-goal-validity-detector-20260529-171217 \
  'cd /home/yoohyun/research3 && TS=20260529-171217 ROOT=/home/yoohyun/research3 RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs MODEL_ROOT=/home/yoohyun/research3/local_dataset/models PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1 FRAME_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1 FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1 CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_candidate_artifact.jsonl OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1 DETECTOR_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/detector_v3c OPENVOCAB_IMG=research3/openvocab-perception:20260513-v3c-gdino-sam2 DEVICE=cuda MAX_FRAMES=20 EXPECTED_FRAME_ROWS=20 EXPECTED_POLICY=ExpandedRetrievalGoalValidityEvidence MAX_HEADINGS_PER_FRAME=0 MAX_DETECTOR_BOXES_PER_HEADING=3 MAX_MASKS_PER_HEADING=3 CANDIDATE_POINT_FIELD=grounded_position PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=0.0,0.4,0.8,1.2,1.6,2.0,2.4 BOX_THRESHOLD=0.10 TEXT_THRESHOLD=0.10 ASSOCIATION_DEPTH_TOLERANCE_M=1.0 MIN_DETECTOR_BOX_RATE=0.80 MIN_SAM2_MASK_RATE=0.80 MIN_CANDIDATE_ASSOCIATION_RATE=0.40 MAX_DEBUG_IMAGES=80 LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/goal-validity-evidence-detector-substrate-20260529-171217.log STATUS=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/job_status.json bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_detector_substrate.sh'
```

Verification command:

```bash
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/job_status.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_substrate_summary.json
```

### 에이전트 추론

The bounded detector/SAM2 substrate is strong enough to proceed to objective design: box/mask availability is not the blocker, and candidate association succeeds on `19/20` rows. The result still cannot be used as terminal utility evidence until a post-detector analyzer separates candidate-specific support from category-only visibility and rival ambiguity.

### Expanded Retrieval Candidate-Specific Goal-Validity Objective Analyzer

### 사실

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
candidate_specific_support_rows: 18
weak_or_partial_candidate_specific_support_rows: 2
not_scored_in_bounded_substrate_rows: 138
detector_box/sam2/candidate_association: 1.0 / 1.0 / 0.95
observed_candidate_evaluation_wrong: 20 / 20
first_correct_generated_rank: 34 for rival_identity:12 and rival_identity:14
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
objective_analyzer_gate_passed: true
terminal_utility_validation_allowed: false
full_detector_substrate_required: true
paper_claim_allowed: false
```

Verification command:

```bash
jq '{gate:.gate.objective_analyzer_gate_passed, terminal:.terminal_utility_validation_allowed, full_required:.full_detector_substrate_required, forbidden:.action_evidence_forbidden_key_count, observed_wrong:.observed_candidate_evaluation.evaluation_only_observed_wrong_candidate_count, paper:.paper_claim_allowed}' local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1/goal_validity_objective_summary.json
```

### 에이전트 추론

The analyzer validates the schema and confirms that candidate-specific detector evidence is being accounted for without GT action leakage. It also blocks terminal utility validation: the bounded detector subset observes only `20/158` candidates, covers only `1/2` recovered request rows, and all observed candidates are evaluation-only wrong. The full-substrate contract below is now the launch contract for the recovered-row frame/projection/detector run, not `first_eval` rerun or terminal commit validation.

### Expanded Retrieval Full Candidate-Specific Goal-Validity Substrate Contract

### 사실

```text
contract: manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.verify.json
status: frozen before full frame/projection/detector run
source_plan: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan.jsonl
candidate_artifact: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_candidate_artifact.jsonl
expected_request_rows: 2
expected_plan_rows: 158
expected_plan_rows_by_request: rival_identity:12 79, rival_identity:14 79
expected_skipped_rows: 42
skipped_rank_range_by_request: 63-100 for both requests
correct_candidate_rows_in_plan: 6
correct_candidate_rows_in_skipped: 0
expected_correct_generated_ranks: 34, 57, 60 for both recovered requests
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_full_v1
detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1
expected_frame_rows: 158
expected_detector_rows: 158
min_detector_box_rate: 0.80
min_sam2_mask_rate: 0.80
min_candidate_association_rate: 0.40
terminal_commit_allowed: false
paper_claim_allowed: false
```

Frame export command:

```bash
docker run --rm --gpus all --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan.jsonl \
    --candidate-artifact /runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_candidate_artifact.jsonl \
    --out-root /runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1 \
    --policy ExpandedRetrievalGoalValidityEvidence \
    --max-decisions 0 \
    --max-candidates-per-decision 1 \
    --candidate-point-field grounded_position \
    --yaw-offsets=-30,0,30 \
    --width 160 \
    --height 120 \
    --camera-height 1.5 \
    --hfov 90
```

Nonblank/projection commands:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.filter_nonblank_frame_summary \
    --frame-summary /runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1/rival_identity_frame_summary.jsonl \
    --frame-root /runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1 \
    --out-root /runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1/nonblank_filter_v1 \
    --min-stddev 0.0

docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.smoke_expanded_retrieval_projection_anchor \
    --frames /runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl \
    --frame-root /runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1 \
    --candidate-artifact /runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_candidate_artifact.jsonl \
    --out-root /runs/h001_expanded_retrieval_goal_validity_evidence_projection_full_v1 \
    --projection-anchor-height-offsets-m 0.0,0.4,0.8,1.2,1.6,2.0,2.4 \
    --candidate-point-field grounded_position \
    --max-candidates-per-frame 1 \
    --expected-rows 158 \
    --min-visible-row-rate 0.95
```

Detector launch template:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-goal-validity-full-detector-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   ROOT=/home/yoohyun/research3 \
   RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs \
   MODEL_ROOT=/home/yoohyun/research3/local_dataset/models \
   PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1 \
   FRAME_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1 \
   FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl \
   FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1 \
   CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_candidate_artifact.jsonl \
   OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1 \
   DETECTOR_OUT=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/detector_v3c \
   OPENVOCAB_IMG=research3/openvocab-perception:20260513-v3c-gdino-sam2 \
   DEVICE=cuda \
   MAX_FRAMES=158 \
   EXPECTED_FRAME_ROWS=158 \
   EXPECTED_POLICY=ExpandedRetrievalGoalValidityEvidence \
   MAX_HEADINGS_PER_FRAME=0 \
   MAX_DETECTOR_BOXES_PER_HEADING=3 \
   MAX_MASKS_PER_HEADING=3 \
   CANDIDATE_POINT_FIELD=grounded_position \
   PROJECTION_ANCHOR_HEIGHT_OFFSETS_M=0.0,0.4,0.8,1.2,1.6,2.0,2.4 \
   BOX_THRESHOLD=0.10 \
   TEXT_THRESHOLD=0.10 \
   ASSOCIATION_DEPTH_TOLERANCE_M=1.0 \
   MIN_DETECTOR_BOX_RATE=0.80 \
   MIN_SAM2_MASK_RATE=0.80 \
   MIN_CANDIDATE_ASSOCIATION_RATE=0.40 \
   MAX_DEBUG_IMAGES=180 \
   LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/goal-validity-full-detector-${ts}.log \
   STATUS=/home/yoohyun/research3/local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/job_status.json \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_detector_substrate.sh"
```

Verification command:

```bash
jq '{gate:.gate.passes_detector_substrate_gate, rows:.detector_rows, box:.detector_box_rate, sam2:.sam2_mask_rate, assoc:.candidate_association_rate, gt:.uses_gt_for_action, paper:.paper_claim_allowed}' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/expanded_retrieval_detector_substrate_summary.json
```

Full pipeline wrapper and launch:

```bash
ts=20260529-202640
tmux new-session -d -s "h001-goal-validity-full-substrate-${ts}" \
  "cd /home/yoohyun/research3 && TS=${ts} bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_full_substrate.sh"
```

Launch record:

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_full_substrate.sh
session: h001-goal-validity-full-substrate-20260529-202640
working_directory: /home/yoohyun/research3
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/goal-validity-full-substrate-20260529-202640.log
pipeline_status: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/full_substrate_job_status.json
detector_status: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/job_status.json
expected_files:
  local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1/summary.json
  local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_full_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json
  local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_full_v1/projection_anchor_smoke_summary.json
  local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/expanded_retrieval_detector_substrate_summary.json
initial_status: running at detector_substrate after frame/nonblank/projection passed
verification_command:
  jq '{gate:.gate.passes_detector_substrate_gate, rows:.detector_rows, box:.detector_box_rate, sam2:.sam2_mask_rate, assoc:.candidate_association_rate, gt:.uses_gt_for_action, paper:.paper_claim_allowed}' local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/expanded_retrieval_detector_substrate_summary.json
```

Known launch repair:

```text
failed_session: h001-goal-validity-full-substrate-20260529-202552
failed_stage: frame_export
failure: output root was host-created with insufficient Docker write permission
repair: wrapper now chmods full frame/projection/detector output roots to 0777 before Docker execution
```

Completion and full objective analyzer:

```text
completed_session: h001-goal-validity-full-substrate-20260529-202640
completed_at: 2026-05-29T20:29:04+09:00
substrate_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1
substrate_gate: true
detector_rows: 158
frame_rows: 158
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.9746835443037974
rows_with_candidate_association: 154
uses_gt_for_action: false
paper_claim_allowed: false

objective_contract: manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.json
objective_verify: manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.verify.json
objective_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_full_v1
objective_analyzer_gate_passed: true
observed_request_rows: 2
observed_candidate_rows: 158
unscored_candidate_rows: 0
candidate_specific_support: 146
weak_or_partial_candidate_specific_support: 12
evaluation_only_observed_correct_candidate_count: 6
evaluation_only_observed_wrong_candidate_count: 152
proposal_action: defer_candidate_specific_support_ambiguous on both request rows
unsafe_simpler_alternatives: semantic_top_observed, detector_score_best_observed, positive_support_best_observed, candidate_specific_support_best_observed
terminal_utility_validation_allowed: false
paper_claim_allowed: false
```

Bounded/full comparison:

```text
bounded_observed_candidate_rows: 20
bounded_observed_request_rows: 1
bounded_unscored_rows: 138
bounded_observed_correct_wrong: 0 / 20
full_observed_candidate_rows: 158
full_observed_request_rows: 2
full_unscored_rows: 0
full_observed_correct_wrong: 6 / 152
```

Next ambiguity-resolution contract:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.verify.json
status: frozen before implementation
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_full_v1/goal_validity_objective_summary.json
diagnostic_target: support saturation after full candidate-specific observation
required_diagnostics:
  support_saturation_profile
  unsafe_selector_taxonomy
  next_evidence_requirement
blocked_actions:
  threshold_tune_detector_score
  threshold_tune_semantic_rank
  terminal_commit_from_support_count
  first_eval_rerun
next_script_target: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_ambiguity.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1
```

Ambiguity-resolution diagnostic result:

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_ambiguity.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1
ambiguity_diagnostic_gate_passed: true
request_rows: 2
candidate_rows: 158
candidate_specific_support_count: 146
candidate_specific_support_rate: 0.9240506329113924
correct_support_count: 6
wrong_support_count: 140
correct_wrong_support_overlap: true
selector_rows: 8
wrong_selector_rows: 8
wrong_selector_rows_by_variant:
  semantic_top_observed: 2
  detector_score_best_observed: 2
  positive_support_best_observed: 2
  candidate_specific_support_best_observed: 2
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
recommended_next_actions:
  request_discriminative_instance_or_goal_region_evidence
  request_relation_or_spatial_context_evidence
  defer_goal_validity_terminal_policy
paper_claim_allowed: false
```

Discriminative instance/goal-region evidence contract:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1.verify.json
status: frozen before implementation
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1/goal_validity_ambiguity_resolution_summary.json
request_ids: rival_identity:12, rival_identity:14
expected_candidate_rows: 158
candidate_specific_support_count: 146
wrong_selector_rows: 8
evaluation_only_correct_candidates: spatial_nms:33, spatial_nms:56, spatial_nms:59
evaluation_only_unsafe_selector_candidates: spatial_nms:0, spatial_nms:21, spatial_nms:23
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
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_discriminative_evidence.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1
```

Discriminative analyzer result:

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_discriminative_evidence.py
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
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
recommended_next_action: request_relation_or_spatial_context_evidence
paper_claim_allowed: false
```

Relation/spatial context contract:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1/goal_validity_discriminative_evidence_summary.json
request_rows: 2
candidate_rows: 158
pair_rows: 420
target_contrast_pair_rows_after_label_join: 18
target_visual_split_after_label_join: contrast_visual_higher 8 / selector_visual_higher 10
target_region_split_after_label_join: adjacent_region_proxy 12 / distinct_region_proxy 6
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
blocked_actions: direct commit, threshold tuning, first_eval rerun, policy-scale comparison
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_relation_spatial_context.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1
```

Relation/spatial context analyzer result:

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_relation_spatial_context.py
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
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

Scene-graph/object-relation evidence contract:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1/goal_validity_relation_spatial_context_summary.json
request_rows: 2
candidate_context_rows: 158
pair_context_rows: 420
spatial_context_group_count: 8
target_contrast_pair_rows_after_label_join: 18
same_component_target_pair_rows_after_label_join: 12
same_component_selector_visual_dominates_after_label_join: 10
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
blocked_actions: direct commit, threshold tuning, first_eval rerun, policy-scale comparison
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_scene_graph_object_relation.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1
```

Scene-graph/object-relation analyzer result:

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_scene_graph_object_relation.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
scene_graph_object_relation_gate_passed: true
request/candidate/pair/context_object_rows: 2 / 158 / 420 / 7788
target_contrast_pair_rows_after_label_join: 18
same_component_target_pair_rows_after_label_join: 12
same_component_selector_visual_dominates_after_label_join: 10
target_pair_relation_delta_sign_counts_after_label_join:
  contrast_relation_higher: 18
relation_separability_probe_supports_signal: true
relation_coverage_complete: true
detector_coverage_complete: false
rows_with_detector_association_by_request: 77 / 79 for each recovered request
scene_graph_object_relation_signal_ready: false
recommended_next_action: request_object_relation_observation
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
paper_claim_allowed: false
```

Object-relation observation coverage repair contract:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1/goal_validity_scene_graph_object_relation_summary.json
source_gate: scene_graph_object_relation_gate_passed true
source_signal_ready: false
request/candidate/pair/context_object_rows: 2 / 158 / 420 / 7788
detector_coverage_complete: false
rows_with_detector_association_by_request: 77 / 79 for each recovered request
detector_missing_candidate_rows: 4
detector_missing_unique_candidate_ids:
  - vlmaps:export:bed:spatial_nms:5
  - vlmaps:export:bed:spatial_nms:90
evaluation_only_missing_detector_correct_rows: 0
evaluation_only_missing_detector_target_pair_rows: 0
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
blocked_actions: direct commit, threshold tuning, first_eval rerun, policy-scale comparison
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_coverage_repair.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1
```

Object-relation observation coverage repair analyzer:

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

Object-relation observation plan contract:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1/goal_validity_object_relation_coverage_repair_summary.json
planner_name: object_relation_depth_recheck_standoff_v1
observation_target_rows: 2
observation_targets:
  - rival_identity:12 / vlmaps:export:bed:spatial_nms:5 / rank 6 / relation_dense
  - rival_identity:14 / vlmaps:export:bed:spatial_nms:5 / rank 6 / relation_dense
waiver_rows_kept_out_of_terminal_policy_promotion: 2
minimum_plan_rows: 8
minimum_plan_rows_per_request: 4
relation_anchor_candidates_per_plan_minimum: 2
viewpoint_policy: relation_multiview_depth_recheck_v1
projection_anchor_policy: projection_anchor_height_sweep_v1
blocked_actions: direct commit, relation-signature best commit, threshold tuning, first_eval rerun, policy-scale comparison
next_script_target: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1
```

Object-relation observation planner:

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
next_gate: object-relation observation frame/projection smoke
```

Object-relation observation frame/projection smoke:

```text
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_frames_v1
filtered_frame_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_projection_v1
frame_rows: 8 / 8
rendered_heading_count: 72
headings_per_row_min_max: 9 / 9
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
next_gate: object-relation observation detector substrate
```

Object-relation observation detector substrate:

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
next_gate: object-relation post-detector evidence analyzer contract frozen below
```

Object-relation post-detector evidence analyzer contract:

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
depth_status_counts: consistent 44 / depth_mismatch 14 / out_of_fov 14
terminal_commit_rows: 0
uses_gt_for_action: false
paper_claim_allowed: false
blocked_actions: direct commit, detector-association best commit, relation-signature best commit, threshold tuning, first_eval rerun, policy-scale comparison
next_script_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py
next_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1
next_gate: implement nonterminal object-relation post-detector evidence analyzer
```

Object-relation post-detector evidence analyzer:

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
docker_compile: passed
docker_run: passed
evidence_rows: 8
request_rows: 2
evaluation_only_rows: 2
association_rows: 72
detector_rows: 8
associated_candidate_heading_count: 48
depth_status_counts: consistent 44 / depth_mismatch 14 / out_of_fov 14
request_evidence_status_counts: relation_depth_recheck_resolved 2
evaluation_only_candidate_correct_counts: false 2
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
object_relation_evidence_gate_passed: true
paper_claim_allowed: false
next_gate: freeze interpretation that detector-depth evidence repaired coverage but did not prove goal validity
```

Object-relation evidence interpretation gate:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_interpretation_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_interpretation_v1.verify.json
source_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1/goal_validity_object_relation_evidence_summary.json
source_evidence_gate_passed: true
evidence_rows: 8
request_rows: 2
evaluation_only_rows: 2
request_evidence_status_counts: relation_depth_recheck_resolved 2
evaluation_only_candidate_correct_counts: false 2
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
terminal_utility_validation_allowed: false
paper_claim_allowed: false
rejected_terminal_shortcuts: relation-depth-resolved commit, box/mask presence commit, high-association-count commit
next_gate: object-relation goal-validity arbitration rule frozen below
```

Object-relation goal-validity arbitration rule:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1.verify.json
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_arbitration.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
docker_compile: passed
docker_run: passed
policy: relation_depth_guarded_non_gt_arbitration_v1
decision_rows: 2
evaluated_rows: 2
relation_depth_resolved_rows: 2
arbitration_action_counts: reject_relation_depth_resolved_without_independent_candidate_support 2
evaluation_only_candidate_correct_counts: false 2
evaluation_only_interpretation_counts: rejected_relation_depth_resolved_negative_candidate 2
support_saturation_eligible_candidate_count_per_row: 73 / 79
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
object_relation_arbitration_rule_gate_passed: true
terminal_utility_validation_allowed: false
paper_claim_allowed: false
next_gate: freeze fresh/predeclared source before generating object-relation evidence
```

Fresh/predeclared object-relation arbitration source:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1.verify.json
script: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
docker_compile: passed
docker_run: passed
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
next_gate: plan and generate fresh object-relation evidence for these route-specific rows
```

Fresh object-relation observation plan:

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1.verify.json
input_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs.py
input_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs_v1
planner_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1
input_target_rows: 36
input_repair_action_rows: 36
input_context_object_rows: 152
input_missing_plan_rows: 0
candidate_positions_missing: 0
docker_image: research3/habitat-h001:20260508-calib-artifacts
planner_script: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py
planner_command_note: use /opt/conda/bin/python in this image
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
next_gate: Docker frame/projection smoke, completed below
```

Fresh object-relation frame/projection smoke:

```text
status: completed
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_frame_projection_v1.verify.json
job_wrapper: runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_frame_projection.sh
tmux_session: h001-fresh-object-relation-frame-projection-20260531-000459
working_directory: /home/yoohyun/research3
log: runtime/logs/fresh-object-relation-frame-projection-20260531-000459.log
status_file: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1/frame_projection_job_status.json
plan_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1
filtered_frame_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1
docker_image: research3/habitat-h001:20260508-calib-artifacts
docker_gpu_args: --gpus all
frame_export_command: /opt/conda/bin/python runtime/h001_runtime/export_postview_frames_v2.py
nonblank_filter_command: /opt/conda/bin/python runtime/h001_runtime/filter_nonblank_frame_summary.py
projection_smoke_command: /opt/conda/bin/python runtime/h001_runtime/smoke_expanded_retrieval_projection_anchor.py
expected_files:
  frame_output/summary.json
  frame_output/nonblank_filter_v1/nonblank_frame_filter_summary.json
  frame_output/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
  projection_output/projection_anchor_smoke_summary.json
  projection_output/projection_anchor_smoke_rows.jsonl
verification_command: jq '.status' local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1/frame_projection_job_status.json && jq '.ok' local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1/summary.json && jq '.gate.projection_anchor_smoke_passed' local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1/projection_anchor_smoke_summary.json
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
repair_notes:
  - first launch failed because Docker frame export lacked GPU args for headless rendering
  - second launch failed because output roots had host permission restrictions
  - wrapper now defaults to --gpus all and chmods frame/projection output roots before Docker execution
next_gate: detector/SAM2 substrate for fresh object-relation observation rows
```

Fresh object-relation detector/SAM2 substrate:

```text
status: completed
tmux_session: h001-fresh-object-relation-detector-20260531-013027
working_directory: /home/yoohyun/research3
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate_v1.verify.json
script: runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate.sh
base_script: runtime/jobs/expanded_retrieval_detector_substrate.sh
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
frames: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
frame_root: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1
candidate_artifact: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1/goal_validity_object_relation_observation_candidate_artifact.jsonl
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1
detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/detector_v3c
log: runtime/logs/fresh-object-relation-detector-substrate-20260531-013027.log
status_file: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/job_status.json
expected_policy: ExpandedRetrievalGoalValidityObjectRelationObservation
expected_frame_rows: 144
projection_anchor_height_offsets_m: 0.0,0.4,0.8,1.2,1.6,2.0,2.4
candidate_point_field: grounded_position
min_detector_box_rate: 0.80
min_sam2_mask_rate: 0.80
min_candidate_association_rate: 0.40
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
projection_status_counts:
  visible: 561
  out_of_fov: 12
projection_anchor_selected_offset_counts:
  0.0: 205
  0.4: 44
  0.8: 29
  1.2: 24
  1.6: 31
  2.0: 75
  2.4: 165
passes_detector_substrate_gate: true
expected_files:
  detector_v3c/summary.json
  detector_v3c/detector_candidate_associations.jsonl
  expanded_retrieval_detector_associations.jsonl
  expanded_retrieval_detector_frame_summary.jsonl
  expanded_retrieval_detector_substrate_summary.json
verification_command: cat local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/job_status.json && cat local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json
launch_command: TS=20260531-013027 bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate.sh
uses_gt_for_action: false
paper_claim_allowed: false
next_gate_after_completion: fresh object-relation post-detector evidence analyzer
```

Fresh object-relation post-detector evidence analyzer:

```text
status: completed
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1.verify.json
label_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_labels.py
evidence_analyzer: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1
source_evaluated_rows: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1/object_relation_arbitration_fresh_source_evaluated_rows.jsonl
fresh_target_rows: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs_v1/object_relation_fresh_observation_coverage_gap_rows.jsonl
detector_associations: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/detector_v3c/detector_candidate_associations.jsonl
label_rows: 36
label_correct/wrong: 11 / 25
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
evidence_status_counts_by_direction:
  relation_depth_recheck_resolved: 72
  relation_depth_recheck_partial: 33
  relation_depth_recheck_unresolved: 3
evaluation_only_interpretation_counts:
  resolved_detector_depth_gap_for_evaluation_positive_candidate: 3
  resolved_detector_depth_gap_for_evaluation_negative_candidate: 21
  partial_detector_depth_gap_after_relation_observation: 12
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
object_relation_evidence_gate_passed: true
uses_gt_for_action: false
uses_gt_for_analysis: true
paper_claim_allowed: false
next_gate_after_evidence: fixed-rule object-relation arbitration validation on fresh evidence (completed; see below)
```

### 에이전트 추론

This contract fixed the bounded-substrate flaw by requiring all `158` planned rows and preserving the recovered correct candidate ranks `34`, `57`, and `60` for both request rows. The full objective analyzer and ambiguity diagnostic show the remaining problem is not candidate coverage. It is support saturation: same-category visual evidence marks almost every candidate as candidate-specific support, and simple selection rules still choose wrong instances. The discriminative analyzer shows instance/goal-region evidence is insufficient as a terminal separator because target contrast pairs are split between contrast-favored and selector-favored visual evidence. The relation/spatial context analyzer adds a stronger failure diagnosis: static context favors the contrast candidates, but same-component selector failures remain. The scene-graph/object-relation analyzer now adds a positive target-pair separability probe, and the object-relation observation substrate resolves the detector association coverage gap for the two rank-6 dense targets. The bounded post-detector analyzer confirms the relation-depth gap is resolved, but only for evaluation-negative candidates. The bounded arbitration rule rejects these candidates without action-time labels by requiring independent candidate-specific support from the full substrate. The fresh/predeclared source precheck shows that route-specific goal-validity rows exist outside the bounded two-row smoke, and the fresh planner/frame/projection/detector/evidence gates show those rows can be converted into relation-aware standoff observations with candidate-local evidence and without action-time label leakage. The fresh evidence result is mixed: many resolved candidates are evaluation-negative, so detector-depth resolution is not terminal goal-validity evidence.

#### Fresh Fixed-Rule Arbitration Validation

사실: Fresh fixed-rule validation was run with a non-GT base-support conversion from `expanded_retrieval_local_context_revision_v1`.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_v1.verify.json
base_support_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_base_support_v1
arbitration_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_v1
base_support_candidate_rows: 36
base_support_candidate_specific_support_rows: 7
base_support_associated_candidate_rows: 33
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
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
object_relation_arbitration_rule_gate_passed: false
paper_claim_allowed: false
next_gate_after_arbitration: diagnose fresh arbitration failure before terminal contract (completed; see below)
```

에이전트 추론: The fixed rule is not promotable on fresh route-specific rows. It does reject many resolved negatives, but the positive-rejection and wrong-provisional rows show that own-view support plus relation-depth consistency still confounds repeated-object visibility with goal validity. This result should become a failure taxonomy and branch-design problem, not a threshold-tuning problem.

#### Fresh Arbitration Failure Diagnosis

사실: Fresh arbitration failure diagnosis was run after fixed decision rows were written.

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
next_gate: design branch-specific goal-validity evidence contract
```

에이전트 추론: This diagnosis makes the blocker actionable: relation-depth repair and own-view support are visibility signals, not goal-validity signals. A next method component must be forced by this taxonomy, for example by separating wrong unique-support cases, correct-but-partial relation-depth cases, and correct-without-strong-own-view cases. Direct threshold tuning remains blocked.

#### Branch-Specific Goal-Validity Evidence Contract

사실: The branch-specific contract is frozen as a nonterminal router design.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_arbitration_failure_v1
expected_request_rows: 7
expected_candidate_rows: 36
branches:
  unique_support_visibility_not_goal_validity
  correct_candidate_missing_own_view_support
  partial_relation_depth_true_goal
  negative_missing_support_guard
required_outputs:
  goal_validity_object_relation_branch_request_rows.jsonl
  goal_validity_object_relation_branch_candidate_rows.jsonl
  goal_validity_object_relation_evaluated_branch_request_rows.jsonl
  goal_validity_object_relation_branch_evidence_summary.json
next_implementation_target: runtime/h001_runtime/route_expanded_retrieval_goal_validity_object_relation_branch_evidence.py
terminal_commit_allowed: false
paper_claim_allowed: false
```

에이전트 추론: The first implementation should be a branch router and coverage audit, not another terminal policy. The preferred first branch is `unique_support_visibility_not_goal_validity` because it turns the strongest current contradiction into an active evidence request: independent support can identify a visible object, but that does not prove this object is the intended `ObjectNav` goal.

#### Branch-Specific Goal-Validity Router

사실: The branch router was implemented and Docker-run.

```text
script: runtime/h001_runtime/route_expanded_retrieval_goal_validity_object_relation_branch_evidence.py
contract: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_branch_evidence_v1
branch_request_rows: goal_validity_object_relation_branch_request_rows.jsonl
branch_candidate_rows: goal_validity_object_relation_branch_candidate_rows.jsonl
evaluated_branch_request_rows: goal_validity_object_relation_evaluated_branch_request_rows.jsonl
summary: goal_validity_object_relation_branch_evidence_summary.json
request_rows: 7
candidate_rows: 36
evaluated_branch_request_rows: 7
branch_evidence_router_gate_passed: true
request_branch_counts:
  unique_support_visibility_not_goal_validity: 4
  partial_relation_depth_true_goal: 6
  correct_candidate_missing_own_view_support: 7
  negative_missing_support_guard: 7
candidate_branch_counts:
  unique_support_visibility_not_goal_validity: 4
  partial_relation_depth_true_goal: 12
  correct_candidate_missing_own_view_support: 20
  negative_missing_support_guard: 20
uncovered_failure_tags: []
action_evidence_forbidden_key_count: 0
terminal_commit_rows: 0
uses_gt_for_action: false
selected_next_branch: unique_support_visibility_not_goal_validity
selected_next_action: request_contrastive_goal_region_evidence
paper_claim_allowed: false
```

에이전트 추론: The router covers the fresh taxonomy, but it intentionally over-routes `correct_candidate_missing_own_view_support` at action time because correctness is not available before the audit join. That is acceptable for this gate: the branch is a request for missing-own-view evidence, not a terminal label. The next contract should define the first branch observation, starting with contrastive goal-region evidence for `unique_support_visibility_not_goal_validity`.

#### Unique-Support Goal-Region Contract

사실: The first branch-specific observation contract is frozen before implementation.

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
target_focus_candidates:
  rival_identity:3 -> vlmaps:export:sofa:spatial_nms:1
  rival_identity:5 -> vlmaps:export:bed:spatial_nms:2
  rival_identity:7 -> vlmaps:export:bed:spatial_nms:2
  rival_identity:22 -> vlmaps:export:sofa:spatial_nms:5
minimum_contrastive_rivals_per_request: 2
terminal_commit_allowed: false
terminal_utility_validation_allowed: false
paper_claim_allowed: false
next_implementation_target: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_unique_support_goal_region.py
```

에이전트 추론: This contract turns the most direct negative mechanism into a planner target. It asks whether the robot should move to collect goal-region evidence when a uniquely visible candidate is plausible but not trustworthy. The next code change should produce nonterminal request, pair, and observation target rows; it must not create a terminal policy.

#### Unique-Support Goal-Region Planner

사실: The planner was implemented and Docker-smoked in the Habitat runtime image.

```text
script: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_unique_support_goal_region.py
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

에이전트 추론: This passes the nonterminal planner gate. The next workflow step is frame/projection smoke for the `51` observation targets, not detector evidence or terminal utility.

#### Unique-Support Goal-Region Frame/Projection Smoke

사실: The frame/projection smoke passed in the Habitat runtime image.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_goal_region_frame_projection.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_frame_projection_v1.verify.json
source_plan_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_frames_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_projection_v1
frame_rows_exported: 51
rendered_heading_count: 204
nonblank_output_rows: 51
nonblank_kept_heading_count: 204
removed_blank_heading_count: 0
projection_anchor_visible_rows: 51
projection_anchor_visible_rate: 1.0
missing_candidate_rows: 0
gt_action_rows: 0
candidate_selection_source_counts:
  explicit_candidate_ids: 51
projection_anchor_smoke_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This verifies that the branch-specific goal-region planner can be rendered into RGB-D evidence frames with visible projection anchors and no blank-heading repair need. The next workflow step is detector/SAM2 substrate for these frames, not terminal utility or threshold tuning.

#### Unique-Support Goal-Region Detector/SAM2 Substrate Job

사실: The detector/SAM2 substrate job completed and passed the fixed substrate gate.

```text
status: completed
tmux_session: h001-unique-support-detector-20260531-174311
working_directory: /home/yoohyun/research3
command: TS=20260531-174311 bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate.sh
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate.sh
base_wrapper: runtime/jobs/expanded_retrieval_detector_substrate.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1.verify.json
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
frames: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
candidate_artifact: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_v1/unique_support_goal_region_candidate_artifact.jsonl
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1
log: runtime/logs/unique-support-goal-region-detector-substrate-20260531-174311.log
expected_frame_rows: 51
expected_policy: ExpandedRetrievalGoalValidityUniqueSupportGoalRegion
expected_files:
  detector_v3c/summary.json
  detector_v3c/detector_candidate_associations.jsonl
  expanded_retrieval_detector_associations.jsonl
  expanded_retrieval_detector_substrate_summary.json
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
uses_gt_for_action: false
passes_detector_substrate_gate: true
paper_claim_allowed: false
```

에이전트 추론: This closes the detector/SAM2 substrate gate for the first branch-specific goal-region evidence path. Candidate association is sufficient for the fixed substrate gate, but it is still not terminal evidence. The next task is a post-detector evidence analyzer that converts focus/rival/common-view detector associations into nonterminal goal-region evidence without threshold tuning or evaluation-label action inputs.

#### Unique-Support Goal-Region Evidence Analyzer Contract

사실: The evidence analyzer contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.verify.json
implementation_target: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_unique_support_goal_region_evidence.py
source_frame_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1/expanded_retrieval_detector_frame_summary.jsonl
source_detector_associations: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1/expanded_retrieval_detector_associations.jsonl
source_detector_summary: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json
expected_outputs:
  unique_support_goal_region_view_evidence_rows.jsonl: 51
  unique_support_goal_region_pair_evidence_rows.jsonl: 17
  unique_support_goal_region_request_evidence_rows.jsonl: 4
  unique_support_goal_region_evidence_summary.json: 1
role_reconstruction:
  common_pair_view: viewpoint_source == common_pair_navmesh
  focus_own_view: viewpoint_source != common_pair_navmesh and target_candidate_id == focus_candidate_id
  rival_own_view: viewpoint_source != common_pair_navmesh and target_candidate_id == rival_candidate_id
all_pairs_have_three_roles: true
source_associated_rows_by_role:
  focus_own_view: 17
  rival_own_view: 10
  common_pair_view: 6
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The analyzer should report `contrastive_goal_region_pair`, `ambiguous_goal_region_pair`, and `insufficient_detector_pair` as evidence statuses. It should also report simpler alternatives such as focus-own support only, rival absence as goal validity, association-count best, and defer-all. No terminal policy is allowed at this stage.

#### Unique-Support Goal-Region Evidence Analyzer

사실: The analyzer is implemented and Docker-verified.

```text
script: runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_unique_support_goal_region_evidence.py
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_goal_region_evidence_v1
docker_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
view_evidence_rows: 51
pair_evidence_rows: 17
request_evidence_rows: 4
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

에이전트 추론: The gate passes as evidence aggregation, but it does not justify terminal arbitration. Focus own-view support is saturated across all `17` pairs, while `10` pairs also have rival own-view support. The next workflow step is evidence output inspection, especially ambiguous pair rows, before deciding whether an additional rival-region observation or a fixed arbitration contract is possible.

#### Unique-Support Goal-Region Evidence Inspection

사실: The evidence inspection is implemented and Docker-verified.

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
inspection_gate_passed: true
```

에이전트 추론: The inspection rejects an immediate terminal arbitration contract. All four requests remain request-level blocked because each contains at least one rival candidate with own-view support. The next workflow step is to freeze a second-pass rival-region evidence contract for the ambiguous rivals, not to tune thresholds or rerun `first_eval`.

#### Second-Pass Rival-Region Evidence Contract

사실: The contract is frozen before implementation.

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
blocked_actions:
  terminal_arbitration_contract
  direct_commit_focus_candidate
  commit_if_any_contrastive_pair_exists
  ignore_rival_own_view_support
  threshold_tuning_on_evaluation_labels
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The next implementation should write a planner that materializes a swapped candidate-view matrix for only the `10` ambiguous pairs. Existing frames may be reused if source camera pose and provenance are preserved, but the output must still be a Docker-verified action-time artifact with explicit candidate ids and no label join.

#### Second-Pass Rival-Region Planner Smoke

사실: The second-pass planner is implemented and Docker-run.

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
unique_support_rival_region_plan_gate_passed: true
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The planner turns the ambiguous-pair blocker into a runnable swapped-view evidence substrate. The next workflow step is frame/projection smoke; terminal utility remains blocked.

#### Second-Pass Rival-Region Frame/Projection Smoke

사실: The frame/projection substrate is Docker-verified.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_frame_projection.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_frame_projection_v1.verify.json
frame_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_frames_v1
projection_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_projection_v1
rows_requested: 30
rows_exported: 30
rendered_heading_count: 120
nonblank_rows: 30
kept_heading_count: 120
removed_blank_heading_count: 0
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

에이전트 추론: The swapped candidate-view matrix has a valid rendering/projection substrate. The next workflow step is detector/SAM2 substrate, still without terminal arbitration.

#### Second-Pass Rival-Region Detector/SAM2 Substrate

사실: The detector/SAM2 substrate job completed, but the frozen substrate gate failed because candidate association is below threshold.

```text
wrapper: runtime/jobs/expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate.sh
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1
diagnostic: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1/rival_region_detector_substrate_diagnostic.json
tmux_session: h001-unique-support-rival-region-detector-20260531-225208
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
by_second_pass_view_role:
  focus_from_rival_own_view: 3 / 10 associated rows
  rival_from_common_pair_view: 3 / 10 associated rows
  rival_from_focus_own_view: 2 / 10 associated rows
by_query:
  bed: 1 / 15 associated rows
  sofa: 7 / 15 associated rows
gt_action_rows: 0
passes_detector_substrate_gate: false
paper_claim_allowed: false
```

에이전트 추론: This is a negative substrate result. Detector boxes and masks are available on all rows, so the blocker is not open-vocabulary detection availability. The likely blocker is candidate association under swapped rival-region viewpoints, especially `bed` rows. The next workflow step is to freeze an association-failure or association-repair contract before any rerun or post-detector evidence analyzer; terminal utility remains blocked.

#### Second-Pass Rival-Region Association Repair Contract

사실: The association repair contract is frozen.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1.verify.json
source_failed_detector_output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1
source_failure_diagnostic: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_detector_substrate_v1/rival_region_detector_substrate_diagnostic.json
implementation_target: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_unique_support_rival_region_association.py
selected_next_contract: association_failure_and_repair_diagnostic_v1
minimum_repair_gate:
  global_candidate_association_rate_minimum: 0.4
  minimum_query_candidate_association_rate_minimum: 0.25
  minimum_second_pass_role_candidate_association_rate_minimum: 0.3
  terminal_commit_rows: 0
  uses_gt_for_action: false
allowed_diagnostic_variants:
  mask_depth_1_25_v1
  mask_depth_1_5_v1
  mask_depth_2_0_v1
  mask_only_upper_bound_v1
  box_only_upper_bound_v1
forbidden:
  query-specific threshold rescue
  role-specific threshold rescue
  label-tuned threshold rescue
  terminal utility validation
  first_eval rerun
  policy-scale comparison
paper_claim_allowed: false
```

에이전트 추론: The next implementation should be a diagnostic analyzer over the existing detector rows, not a detector rerun. It must show whether a fixed non-GT association variant clears the global/query/role gates. If it does not, the next design should revisit viewpoint/candidate geometry instead of relaxing the terminal evidence contract.

#### Second-Pass Rival-Region Association Repair Diagnostic

사실: The association repair diagnostic is implemented and Docker-run.

```text
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_unique_support_rival_region_association.py
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_diagnostic_v1.verify.json
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_association_repair_v1
diagnostic_rows: 180
source_frame_rows: 30
source_association_rows: 120
selected_repair_variant: mask_depth_1_25_v1
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

에이전트 추론: The source failure was mainly strict depth/mask candidate association under swapped rival-region views, not detector or SAM2 availability. The next workflow step is a repaired detector/SAM2 substrate rerun with the fixed `mask_depth_1_25_v1` association rule. Post-detector evidence analysis and terminal utility remain blocked until that rerun passes.

#### Second-Pass Rival-Region Repaired Detector Substrate

사실: The repaired detector/SAM2 rerun with `mask_depth_1_25_v1` completed and failed the fixed substrate gate.

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
bed_association: 1 / 15
sofa_association: 9 / 15
gt_action_rows: 0
passes_detector_substrate_gate: false
paper_claim_allowed: false
```

에이전트 추론: The rerun remains a negative substrate result. The offline repair diagnostic does not exactly match runtime detector association semantics because runtime uses `depth_agreement_m` between projected candidate depth and selected SAM2 mask depth. Before trying the predeclared `mask_depth_2_0_v1` fallback, the workflow should freeze a runtime association-semantics diagnostic and explicitly record the generalization risk.

#### Runtime Association-Semantics Diagnostic

사실: The runtime association-semantics diagnostic is implemented and Docker-run.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association_semantics_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association_semantics_v1.verify.json
script: runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_rival_region_runtime_association_semantics_v1
diagnostic_rows: 180
runtime_depth_field: depth_agreement_m
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

에이전트 추론: This diagnostic justified one actual depth2 detector/SAM2 substrate rerun. The rerun result is recorded below; the diagnostic itself remains nonterminal and not paper-claim evidence.

#### Runtime Depth2 Detector/SAM2 Rerun Result

사실: The predeclared `mask_depth_2_0_v1` detector/SAM2 substrate rerun completed and passed the fixed substrate gate.

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

에이전트 추론: This is still a substrate test. It unlocks only nonterminal post-detector evidence aggregation.

#### Second-Pass Rival-Region Evidence Analyzer

사실: The post-detector evidence analyzer is frozen and Docker-run.

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

에이전트 추론: The evidence pass sharpened the blocker: detector/SAM2 substrate is no longer the immediate issue, but the dominant evidence pattern is cross-region overlap. The inspection result below records why terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked.

#### Cross-Region Overlap Inspection

사실: The cross-region overlap inspection is implemented and Docker-run.

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

에이전트 추론: The second-pass branch is not terminal-ready. Three requests should be routed into a cross-region overlap failure branch, and the remaining request still has shared common-view rival support. This led to the branch freeze below rather than a terminal utility contract.

#### Cross-Region Overlap Failure Branch Freeze

사실: The branch freeze is implemented and Docker-run.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1.verify.json
script: runtime/h001_runtime/route_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_cross_region_overlap_branch_v1
pair_branch_rows: 10
request_branch_rows: 4
pair_branch_counts:
  cross_region_overlap_failure_branch: 7
  shared_common_view_support_pending_branch: 2
  clean_contrastive_pending_branch: 1
request_branch_counts:
  cross_region_overlap_failure_branch: 3
  shared_common_view_support_pending_branch: 1
request_action_counts:
  route_to_cross_region_overlap_failure_branch: 3
  route_to_shared_common_view_support_inspection: 1
cross_region_request_ids:
  rival_identity:3
  rival_identity:5
  rival_identity:22
shared_common_pending_request_ids:
  rival_identity:7
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
cross_region_overlap_branch_freeze_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The failure mechanism is now explicitly routed: three requests are cross-region overlap failures and one request remains a shared-common-view support case. Terminal arbitration is still blocked because no branch has yet established non-GT `ObjectNav` goal validity.

#### Shared Common-View Support Inspection

사실: The remaining non-cross-overlap request is inspected for shared common-view rival support.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1.verify.json
script: runtime/h001_runtime/inspect_expanded_retrieval_goal_validity_unique_support_shared_common_view.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_shared_common_view_inspection_v1
request_inspection_rows: 1
pair_inspection_rows: 2
request_ids:
  rival_identity:7
pair_status_counts:
  shared_common_view_rival_support_blocks_terminal: 1
  clean_contrastive_pair_contaminated_by_request_level_shared_common_support: 1
request_recommendation_counts:
  freeze_shared_common_view_support_failure_branch: 1
terminal_commit_rows: 0
action_evidence_forbidden_key_count: 0
shared_common_view_inspection_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This closes the "maybe the no-cross-overlap row is terminal-ready" possibility. The row still has shared common-view rival support, so the next workflow step is branch freeze rather than a terminal arbitration contract.

#### Shared Common-View Support Failure Branch Freeze

사실: The branch freeze is implemented and Docker-run.

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
terminal_contract_allowed: false
terminal_commit_rows: 0
action_forbidden_key_count: 0
shared_common_view_branch_freeze_gate_passed: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: Shared common-view rival support is a frozen nonterminal failure branch. Terminal utility remains blocked.

#### Unique-Support Branch Closure

사실: The branch closure is implemented and Docker-run.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1.verify.json
script: runtime/h001_runtime/close_expanded_retrieval_goal_validity_unique_support_branch.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_unique_support_branch_closure_v1
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

에이전트 추론: The unique-support visibility branch is closed as terminal-blocked. This led to the frozen `partial_relation_depth_true_goal` observation contract below before any implementation or terminal utility test.

#### Partial Relation-Depth True-Goal Observation Contract

사실: The branch-specific contract is frozen before implementation.

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

에이전트 추론: The contract treats partial relation-depth as observation incompleteness, not candidate invalidity. The runtime implementation below keeps this as nonterminal evidence acquisition, not a method claim.

#### Partial Relation-Depth Input and Planner Smoke

사실: The input materializer and planner smoke are Docker-verified.

```text
input_builder: runtime/h001_runtime/build_expanded_retrieval_goal_validity_partial_relation_depth_inputs.py
planner: runtime/h001_runtime/plan_expanded_retrieval_goal_validity_partial_relation_depth.py
output: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1
input_request_rows: 6
input_target_candidate_rows: 12
input_failed_relation_depth_evidence_rows: 22
input_context_anchor_rows: 48
input_action_forbidden_key_count: 0
input_terminal_commit_rows: 0
input_gate: true
plan_rows: 48
plan_rows_per_target_candidate: 4
skipped_rows: 0
failed_evidence_rows_mapped: 22
failed_evidence_rows_unmapped: 0
candidate_artifact_rows: 4
candidate_artifact_candidate_count: 20
planner_action_forbidden_key_count: 0
planner_terminal_commit_rows: 0
plan_gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The next runtime step is frame/projection smoke for the 48 planned relation-depth completion views. Terminal utility, `first_eval`, and policy-scale comparison stay blocked.

#### Partial Relation-Depth Frame/Projection Smoke

사실: The frame/projection smoke is Docker-verified.

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

에이전트 추론: The next runtime step is detector/SAM2 substrate on these frames. This remains a nonterminal evidence route and cannot support terminal utility or paper claims yet.

#### Partial Relation-Depth Detector/SAM2 Substrate

사실: The detector/SAM2 substrate is Docker/GPU-verified.

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
candidate_selection_source: explicit_candidate_ids 48
projection_anchor_policy: projection_anchor_height_sweep_v1 48
uses_gt_for_action: false
detector_substrate_gate: true
paper_claim_allowed: false
```

에이전트 추론: The next runtime step is to freeze a post-detector evidence analyzer contract for relation-depth completion. It should score whether detector-depth evidence resolves prior partial/unresolved relation-depth rows without creating a confidence-based terminal commit.

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

에이전트 추론: The contract is now implemented and Docker-verified as nonterminal evidence. Terminal utility, `first_eval`, and policy-scale comparison remain blocked.

#### Partial Relation-Depth Post-Detector Evidence Analyzer

사실: The analyzer is Docker-verified.

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

에이전트 추론: This result keeps relation-depth completion as evidence acquisition, not terminal goal selection. The immediate runtime follow-up is row-level inspection of the `15` unresolved/partial rows to separate viewpoint geometry, detector association, relation-anchor ambiguity, and remaining goal-validity blockers.

#### Remaining Partial Relation-Depth Row Inspection

사실: The unresolved/partial rows were inspected from the analyzer output.

```text
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_evidence_v1/partial_relation_depth_unresolved_rows.jsonl
rows: 15
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
inside_mask_no_association_rows: 8
depth_positive_association_zero_rows: 3
dominant_scene_query: bxsVRursffK/plant 12
dominant_request_rows:
  rival_identity:25: 4
  rival_identity:27: 4
  rival_identity:29: 4
```

에이전트 추론: Residual partial relation-depth is a structured blocker. It is not a missing-render or detector-absent case because all `15` rows have inside-mask evidence. This led to the frozen residual taxonomy below before any terminal utility rule.

#### Residual Partial Relation-Depth Taxonomy

사실: The residual taxonomy is Docker-verified.

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

에이전트 추론: The runtime branch is now frozen into three next mechanisms: association geometry underlink, depth stagnation despite association, and repeated-object relation-anchor ambiguity. The branch-handling contract below fixes how each mechanism is handled without tuning thresholds from labels.

#### Residual Partial Relation-Depth Branch Handling

사실: The branch-handling contract is frozen and Docker-verified.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1.verify.json
router: runtime/h001_runtime/route_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling.py
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_residual_taxonomy_v1
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

에이전트 추론: The branch router preserves the nonterminal split and keeps terminal utility/paper claims blocked. The next workflow step is to design the association-geometry repair branch contract for the two underlink requests before depth-stagnation or repeated-anchor ambiguity work.

#### Association-Geometry Repair Branch Contract

사실: The association-geometry repair branch contract is frozen before implementation.

```text
contract: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1.json
verify: manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1.verify.json
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1
target_branch_action: route_to_association_geometry_repair_branch
target_request_rows: 2
target_branch_rows: 2
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

에이전트 추론: The next workflow step is `runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair.py`. It should account for both underlink requests and emit nonterminal repair/re-observation/defer rows without label joins.

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

### Rival Identity Diagnostic Policy

Diagnostic output:

```text
script: runtime/h001_runtime/analyze_dense_conflict_rival_identity_policy.py
output: local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1
rows: rival_identity_policy_rows.jsonl
summary: rival_identity_policy_summary.json
```

Policy rule:

```text
commit_candidate:
  exactly one positive-support candidate passes strict_depth_consistency_v1
  and that candidate is semantic rank 1
request_rival_identity_confirmation:
  multiple guard-eligible same-category candidates exist
  or the only guard-eligible candidate is not semantic rank 1
defer_or_expand_retrieval:
  no positive-support candidate exists
```

Comparison result:

| Policy | Commit | Success | Wrong | Request | Diagnostic gate |
| --- | ---: | ---: | ---: | ---: | --- |
| `strict_depth_consistency_v1` | 8 | 2 | 6 | 0 | fail |
| `support_margin_only` | 8 | 2 | 6 | 0 | fail |
| `depth_margin_only` | 8 | 2 | 6 | 0 | fail |
| `semantic_top_only` | 8 | 2 | 6 | 0 | fail |
| `defer_all_ambiguous` | 0 | 0 | 0 | 8 | fail: inert |
| `rival_identity_confirmation_v1` | 2 | 2 | 0 | 6 | pass diagnostic |

Against `strict_depth_consistency_v1`, `rival_identity_confirmation_v1` keeps the same number of successful commits (`2`), removes all wrong-goal commits (`-6`), and converts six ambiguous rows into identity-confirmation requests. The result is still diagnostic-only. The later fresh-source observation/detector/analyzer path was executed, but the fixed post-observation rule failed because two single-candidate `toilet` false positives were committed as wrong goals.

### 에이전트 추론

This result supports the mechanism-level direction: semantic uncertainty should produce an active identity-confirmation request when same-category rivals are not separable by existing detector/depth support. It also now has a clear boundary: single-candidate object-existence false positives should not be treated as solved by the same rival-identity commit rule. The next step is not policy-scale evaluation. It is a separate object-existence validation branch after the accepted taxonomy split.

### Rival Identity Observation Contract

Contract:

```text
manifest: manifests/h001_rival_identity_observation_v1.json
contract_name: rival_identity_observation_v1
request_rows: 6
primary_request_rows: 4
secondary_stress_request_rows: 2
planner_name: rival_identity_pair_probe_v1
paper_claim_status: not_allowed_until_actual_observation_and_fresh_or_predeclared_validation
```

Observation contract:

- Always include the focus candidate from `rival_identity_confirmation_v1`.
- Include guard-eligible rivals first.
- For unique guard-eligible but non-semantic-top cases, include semantic/support rivals.
- Use non-GT `visit_position`, `position`, semantic score/rank, detector score, support, mask/box/association counts, and depth consistency only.
- Do not use `evaluation_only_candidate_correct`, recall rank, GT object position, GT geodesic distance, success label, or wrong-goal label.

Expected outputs:

```text
rival_identity_observation_plan.jsonl
rival_identity_frame_summary.jsonl
rival_identity_detector_associations.jsonl
rival_identity_post_observation_evidence.jsonl
rival_identity_observation_validation_summary.json
```

Predeclared gates:

```text
minimum_plan_gate:
  request_rows: 6
  primary_request_rows: 4
  secondary_stress_request_rows: 2
  planned_rows_minimum: 6
  action_evidence_forbidden_key_count: 0
detector_substrate_gate:
  detector_box_rate_minimum: 0.80
  sam2_mask_rate_minimum: 0.80
  candidate_association_rate_minimum: 0.50
post_observation_gate:
  wrong_goal_commit_rows: 0
  no_label_commit_rows: 0
  new_primary_success_commit_rows_minimum: 1
  resolved_request_rows_minimum: 1
  secondary_stress_wrong_goal_commit_rows: 0
```

Failure taxonomy:

| Failure code | Interpretation |
| --- | --- |
| `observation_plan_missing_target` | planner fails to create focus/rival observations from non-GT geometry |
| `detector_substrate_failure` | rendered observations exist but detector/mask/association evidence is insufficient |
| `identity_evidence_non_discriminative` | same-category rival evidence remains saturated after observation |
| `unsafe_post_observation_commit` | post-observation rule commits to a wrong candidate |
| `safe_but_inert` | no wrong commits, but no request rows are resolved |
| `label_plumbing_failure` | committed candidate has no evaluation label |
| `source_independence_violation` | contract is changed or tuned using evaluation labels from this failed split |

### Rival Identity Observation Plan Smoke

#### 사실

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
contract: manifests/h001_rival_identity_observation_v1.json
output: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1
plan: rival_identity_observation_plan.jsonl
summary: rival_identity_observation_plan_summary.json
request_rows: 6
planned_request_rows: 6
plan_rows: 19
skipped_rows: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
plan_smoke_passed: true
```

Docker verification:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.plan_rival_identity_observation \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_observation_v1.json \
    --runs-root /runs \
    --workspace-root /workspace \
    --out-root /runs/h001_rival_identity_pair_probe_plan_v1 \
    --run-id h001_rival_identity_pair_probe_v1
```

The planner consumes only the frozen request rows and action-time candidate evidence. It uses non-GT candidate `visit_position` / `position` to create focus and rival observation rows; evaluation labels are not loaded.

#### 에이전트 추론

The minimum plan gate is passed and produced a detector-ready candidate artifact. Detector/SAM2 association should not be launched until the detector substrate job contract records the exact command, logs, expected files, and verification gate.

### Rival Identity Frame Export Smoke

#### 사실

```text
renderer: runtime/h001_runtime/export_postview_frames_v2.py
plan_output: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1
candidate_artifact: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_candidate_artifact.jsonl
frame_output: local_dataset/runs/h001_rival_identity_pair_probe_frames_v1
frames: postview_frames_v2.jsonl
contract_alias: rival_identity_frame_summary.jsonl
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

Docker command:

```bash
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_observation_plan.jsonl \
    --candidate-artifact /runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_candidate_artifact.jsonl \
    --out-root /runs/h001_rival_identity_pair_probe_frames_v1 \
    --policy RivalIdentityPairProbe \
    --max-decisions 0 \
    --semantic-tie-band 0.0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30 \
    --dedupe-degrees 10 \
    --candidate-point-field grounded_position \
    --width 160 \
    --height 120 \
    --camera-height 1.5 \
    --hfov 90.0
```

The first attempt without `--gpus all` failed at Habitat EGL context creation. This is an environment/runtime requirement for rendering, not a detector result.

#### 에이전트 추론

The active observation plan is now renderable across the three request scenes. The next step is to write the detector substrate job contract with exact command, log path, expected files, and substrate gates before launching `GroundingDINO + SAM2`.

### Rival Identity Detector Substrate Job Contract

#### 사실

```text
script: runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
status: completed
frames: local_dataset/runs/h001_rival_identity_pair_probe_frames_v1/rival_identity_frame_summary.jsonl
candidate_artifact: local_dataset/runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_candidate_artifact.jsonl
output: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1
detector_output: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/detector_v3c
log_template: runtime/logs/rival-identity-detector-substrate-<timestamp>.log
status_file: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/job_status.json
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
candidate_point_field: grounded_position
query_template: "{query}"
box_threshold: 0.10
text_threshold: 0.10
association_depth_tolerance_m: 1.0
expected_frame_rows: 19
```

Expected files:

```text
local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/detector_v3c/summary.json
local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/detector_v3c/detector_candidate_associations.jsonl
local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_associations.jsonl
local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_frame_summary.jsonl
local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_substrate_summary.json
```

Launch command:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s h001-rival-identity-detector-${ts} \
  "cd /home/yoohyun/research3 && TS=${ts} bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh"
```

Verification command:

```bash
cat local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/job_status.json
cat local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_substrate_summary.json
```

Pre-launch checks already passed:

```text
bash -n: pass
frame_rows: 19
candidate_artifact_rows: 3
rival_identity_request_id_trace_rows: 19
```

Detector substrate gate:

```text
detector_rows == 19
detector_box_rate >= 0.80
sam2_mask_rate >= 0.80
candidate_association_rate >= 0.50
uses_gt_for_action == false
```

The wrapper copies detector associations to the contract-level alias `rival_identity_detector_associations.jsonl` and writes a gate summary to `rival_identity_detector_substrate_summary.json`.

#### 에이전트 추론

This contract keeps the next GPU-heavy detector job reproducible and inspectable. The job should be launched as a background `tmux` task; while it runs, do not continuously monitor unless a dependent task needs the result.

#### Launch Status

```text
launched_at: 2026-05-26 01:20:36 KST
tmux_session: h001-rival-identity-detector-20260526-012036
command: TS=20260526-012036 bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
status_file: local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/job_status.json
status_at_launch_check: running
stage_at_launch_check: detector_mask_scoring
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/rival-identity-detector-substrate-20260526-012036.log
completion_status: completed
completed_stage: completed
```

#### Detector Substrate Result

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
paper_claim_allowed: false
```

The detector substrate gate passed. This does not establish ObjectNav utility; it only unblocks post-observation evidence construction and validation against the frozen request rows.

### Rival Identity Post-observation Evidence Contract

#### 사실

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

Action-time evidence may use detector association, target viewpoint, candidate geometry, semantic/support, and request metadata. It must not use evaluation labels, recall rank, GT object position, GT geodesic distance, or success/wrong labels. Evaluation labels are joined only after decisions are written. The label join key is `(episode_key, candidate_id)`, and the request join key is `rival_identity_request_id`.

Frozen per-candidate evidence fields:

```text
post_associated_heading_count
post_own_associated_heading_count
post_cross_associated_heading_count
post_best_box_score
post_min_depth_error_m
post_own_target_role_count
post_cross_target_role_count
post_identity_margin
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
- If a committed candidate has no label, count it as `no_label_commit_rows` and classify as `label_plumbing_failure`.

Post-observation validation metrics:

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

Failure taxonomy additions:

| Failure code | Interpretation |
| --- | --- |
| `post_observation_no_candidate_support` | no candidate gets own-view detector association after active observation |
| `post_observation_cross_view_aliasing` | a candidate is associated mainly from another candidate's target view |
| `post_observation_multiple_strong_candidates` | more than one candidate satisfies the strong identity rule |
| `post_observation_margin_too_small` | own-view support exists but is not separated from the nearest rival |
| `post_observation_safe_defer` | no commit is made because the evidence is weak or ambiguous |

#### 에이전트 추론

This contract turns the detector substrate into a falsifiable active-observation test. A positive result requires at least one newly resolved primary request without wrong-goal or no-label commits. A negative result is still useful if it separates detector substrate failure, cross-view aliasing, insufficient margin, and safe-but-inert deferral.

### Rival Identity Post-observation Analyzer Smoke

#### 사실

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
output: local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1
summary: rival_identity_observation_validation_summary.json
evidence_rows: rival_identity_post_observation_evidence.jsonl
decision_rows: rival_identity_post_observation_decisions.jsonl
evaluated_rows: rival_identity_post_observation_evaluated.jsonl
request_rows: 6
evidence_rows_count: 19
decision_rows_count: 6
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

Docker command:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_rival_identity_post_observation \
    --detector-associations /runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_associations.jsonl \
    --plan /runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_observation_plan.jsonl \
    --primary-evaluation-labels /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --secondary-evaluation-labels /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --out-root /runs/h001_rival_identity_pair_probe_post_observation_v1
```

Per-request outcome:

| Request | Query | Role | Action | Result |
| --- | --- | --- | --- | --- |
| `rival_identity:0` | `chair` | primary | commit `vlmaps:export:chair:spatial_nms:2` | success |
| `rival_identity:1` | `plant` | primary | defer | `post_observation_no_candidate_support` |
| `rival_identity:2` | `plant` | primary | defer | `post_observation_no_candidate_support` |
| `rival_identity:3` | `plant` | primary | defer | `post_observation_no_candidate_support` |
| `rival_identity:4` | `sofa` | secondary_stress | defer | `post_observation_cross_view_aliasing` |
| `rival_identity:5` | `sofa` | secondary_stress | defer | `post_observation_cross_view_aliasing` |

#### 에이전트 추론

This is the first positive end-to-end diagnostic for the active identity-confirmation path: the frozen rule resolves one primary wrong-goal request without introducing wrong-goal or no-label commits. It is still not a paper-facing utility claim because the request rows are a small diagnostic set derived from the failed independent validation. The next step should be a fresh or predeclared validation split for the same frozen analyzer, not policy-scale integration.

### Rival Identity Fresh Validation Source Design

#### 사실

Selected source:

```text
source_name: rival_identity_generalization_v1
parent_split: dense_conflict_generalization_v1
parent_manifest: manifests/h001_dense_conflict_generalization_v1.json
action_evidence: local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1/action_evidence_rows.jsonl
evaluation_labels: local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1/evaluation_labels.jsonl
design_probe: local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1
scope: primary rows only
selection_rule: apply frozen rival_identity_confirmation_v1 to action-time evidence and keep request_rival_identity_confirmation rows
label_use_for_selection: forbidden
```

Freshness rule:

- Exclude local diagnostic scenes already used by `rival_identity_pair_probe_v1`: `DYehNKdT76V`, `7MXmsvcQjpJ`, `y9hTuugGdiq`.
- Do not include the secondary `y9hTuugGdiq/sofa` stress rows in the fresh source; those rows were already used in the diagnostic analyzer smoke.
- Do not filter rows by `evaluation_only_candidate_correct`, success, or wrong-goal label.

Design probe command:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_dense_conflict_rival_identity_policy \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --primary-action-evidence /runs/h001_dense_conflict_generalization_terminal_evidence_v1/action_evidence_rows.jsonl \
    --primary-evaluation-labels /runs/h001_dense_conflict_generalization_terminal_evidence_v1/evaluation_labels.jsonl \
    --secondary-action-evidence /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --secondary-evaluation-labels /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --out-root /runs/h001_rival_identity_generalization_policy_design_probe_v1
```

Primary-only design probe result:

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
strict_depth_consistency_v1 primary commit/success/wrong: 3 / 3 / 0
rival_identity_confirmation_v1 primary commit/success/wrong/request: 1 / 1 / 0 / 6
```

Predeclared request rows for the next miner:

| Episode | Scene | Query | Reason |
| --- | --- | --- | --- |
| `HM3D ObjectNav v2:val:CrMo8WxCyVb:24:2:bed` | `CrMo8WxCyVb` | `bed` | `request_identity_unique_guard_eligible_not_semantic_top` |
| `HM3D ObjectNav v2:val:5cdEh9F2hJL:14:2:toilet` | `5cdEh9F2hJL` | `toilet` | `request_identity_no_guard_eligible_positive_candidates` |
| `HM3D ObjectNav v2:val:CrMo8WxCyVb:22:5:bed` | `CrMo8WxCyVb` | `bed` | `request_identity_unique_guard_eligible_not_semantic_top` |
| `HM3D ObjectNav v2:val:mL8ThkuaVTM:2:4:bed` | `mL8ThkuaVTM` | `bed` | `request_identity_no_guard_eligible_positive_candidates` |
| `HM3D ObjectNav v2:val:mL8ThkuaVTM:18:0:bed` | `mL8ThkuaVTM` | `bed` | `request_identity_no_guard_eligible_positive_candidates` |
| `HM3D ObjectNav v2:val:CrMo8WxCyVb:1:2:toilet` | `CrMo8WxCyVb` | `toilet` | `request_identity_no_guard_eligible_positive_candidates` |

Source-freeze gate:

```text
request_rows >= 6
request_scenes >= 3
request_queries >= 2
overlap_with_previous_diagnostic_scenes == 0
action_evidence_forbidden_key_count == 0
uses_gt_for_action == false
manifest_status == frozen_before_observation_planning
```

Source-freeze implementation result:

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
excluded_scene_overlap: 0
action_evidence_forbidden_key_count: 0
uses_gt_for_action: false
```

Source miner command:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.build_rival_identity_generalization_manifest \
    --action-evidence /runs/h001_dense_conflict_generalization_terminal_evidence_v1/action_evidence_rows.jsonl \
    --evaluation-labels /runs/h001_dense_conflict_generalization_terminal_evidence_v1/evaluation_labels.jsonl \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --out-manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_generalization_v1.json \
    --verify-out /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_generalization_v1.verify.json \
    --out-root /runs/h001_rival_identity_generalization_source_v1
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

Planner smoke command:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.plan_rival_identity_observation \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_generalization_v1.json \
    --runs-root /runs \
    --workspace-root /workspace \
    --out-root /runs/h001_rival_identity_generalization_plan_v1 \
    --run-id h001_rival_identity_generalization_v1
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

Frame export command:

```bash
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_rival_identity_generalization_plan_v1/rival_identity_observation_plan.jsonl \
    --candidate-artifact /runs/h001_rival_identity_generalization_plan_v1/rival_identity_candidate_artifact.jsonl \
    --out-root /runs/h001_rival_identity_generalization_frames_v1 \
    --policy RivalIdentityPairProbe \
    --max-decisions 0 \
    --semantic-tie-band 0.0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30 \
    --dedupe-degrees 10 \
    --candidate-point-field grounded_position \
    --width 160 \
    --height 120 \
    --camera-height 1.5 \
    --hfov 90.0
```

Detector/SAM2 substrate launch:

```text
tmux_session: h001-rival-identity-generalization-detector-20260526-102744
status: completed
output: local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1
log: runtime/logs/rival-identity-generalization-detector-substrate-20260526-102744.log
expected_files:
  detector_v3c/summary.json
  detector_v3c/detector_candidate_associations.jsonl
  rival_identity_detector_associations.jsonl
  rival_identity_detector_substrate_summary.json
detector_rows: 12
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 1.0
associated_candidate_heading_count: 84
detector_substrate_gate: true
uses_gt_for_action: false
verification_command:
  cat local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1/job_status.json
  cat local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1/rival_identity_detector_substrate_summary.json
```

Launch command:

```bash
TS=20260526-102744
tmux new-session -d -s h001-rival-identity-generalization-detector-${TS} \
  "cd /home/yoohyun/research3 && \
  TS=${TS} \
  PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_plan_v1 \
  FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_frames_v1/rival_identity_frame_summary.jsonl \
  FRAME_EXPORT_SUMMARY=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_frames_v1/summary.json \
  CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_plan_v1/rival_identity_candidate_artifact.jsonl \
  OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1 \
  DETECTOR_OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1/detector_v3c \
  EXPECTED_FRAME_ROWS=12 \
  MAX_FRAMES=12 \
  LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/rival-identity-generalization-detector-substrate-${TS}.log \
  STATUS=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1/job_status.json \
  bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh"
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
wrong_goal_commit_rows: 2
failure_taxonomy_counts:
  none: 2
  post_observation_cross_view_aliasing: 2
  unsafe_post_observation_commit: 2
post_observation_gate_passed: false
uses_gt_for_action: false
```

Wrong commits:

| Request | Episode | Query | Selected candidate | Failure |
| --- | --- | --- | --- | --- |
| `rival_identity:1` | `HM3D ObjectNav v2:val:5cdEh9F2hJL:14:2:toilet` | `toilet` | `vlmaps:export:toilet:spatial_nms:0` | single false-positive focus candidate |
| `rival_identity:5` | `HM3D ObjectNav v2:val:CrMo8WxCyVb:1:2:toilet` | `toilet` | `vlmaps:export:toilet:spatial_nms:0` | single false-positive focus candidate |

#### 에이전트 추론

The failed `toilet` rows are not rival-identity ambiguity: each plan contains only the focus candidate, and strong own-view detector association confirms the candidate as a visible object-like detection while the post-join ObjectNav label marks it wrong. This suggests that `request_identity_no_guard_eligible_positive_candidates` mixes two mechanisms: rival identity ambiguity and object-existence false positive. The next revision should first split these mechanisms in the failure taxonomy before changing thresholds.

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
request_reason_mechanism_counts:
  request_identity_unique_guard_eligible_not_semantic_top:
    rival_identity_resolved_success: 2
  request_identity_no_guard_eligible_positive_candidates:
    rival_identity_unresolved_cross_view_aliasing: 2
    single_candidate_object_existence_false_positive: 2
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Diagnostic command:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.diagnose_rival_identity_generalization_failures \
    --evaluated /runs/h001_rival_identity_generalization_post_observation_v1/rival_identity_post_observation_evaluated.jsonl \
    --evidence /runs/h001_rival_identity_generalization_post_observation_v1/rival_identity_post_observation_evidence.jsonl \
    --plan /runs/h001_rival_identity_generalization_plan_v1/rival_identity_observation_plan.jsonl \
    --detector-summary /runs/h001_rival_identity_generalization_detector_substrate_v1/rival_identity_detector_substrate_summary.json \
    --out-root /runs/h001_rival_identity_generalization_failure_diagnostic_v1
```

#### 에이전트 추론

The request reason should not be used as the mechanism label. A conservative split is:

- `positive_support_candidate_count <= 1` or one planned target: object-existence validation.
- `positive_support_candidate_count >= 2` and multiple planned targets: rival-identity arbitration.

This split is evidence-derived and should be documented before any threshold or commit-rule change.

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

#### Decision

The split is accepted. `request_reason` remains a planner/action reason, not a mechanism label. Multi-positive requests stay in `rival_identity_arbitration`; single-positive requests route to `object_existence_validation`. The next implementation must define a separate no-commit safety branch for object-existence validation before any policy-scale evaluation.

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

Regression result:

```text
output: local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1
commit / success / wrong: 1 / 1 / 0
request_taxonomy_route_counts:
  rival_identity_arbitration: 6
post_observation_gate_passed: true
uses_gt_for_action: false
```

#### 에이전트 추론

The no-commit branch repairs the immediate safety failure but leaves object-existence as a conservative defer path. This should not be claimed as active navigation utility yet. The next useful step is an independent object-existence validation probe that can measure wrong-goal avoided by defer, success lost by defer, and any future safe-confirm rule.

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

#### 에이전트 추론

This probe supports the no-commit branch as safety evidence on the current source. It does not define a safe object-existence commit rule. The next split must include enough single-positive rows to measure both avoided wrong-goals and lost successes, otherwise pure defer may look better than it is.

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

#### 에이전트 추론

The design freezes `risk_validation` as the preferred broader source because it avoids all previous diagnostic and current fresh-source scenes while preserving the HM3D ObjectNav setup. The source miner and planner now pass; the frame export substrate is row-level usable after removing blank headings, so the next blocker is detector/SAM2 substrate validation on the nonblank-filtered frame summary.

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

Detector substrate launch/status:

```text
wrapper: runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
code_update: runtime/h001_runtime/detect_postview_groundingdino_sam2.py now accepts --frame-root
working_directory: /home/yoohyun/research3
failed_path_root_attempt:
  output: local_dataset/runs/h001_rival_identity_broader_detector_substrate_v1
  status: completed_but_gate_failed
  reason: filtered summary was under nonblank_filter_v1 while rendered_headings paths are relative to the original frame export root
  detector_box_rate: 0.0
  sam2_mask_rate: 0.0
  candidate_association_rate: 0.0
corrected_tmux_session: h001-rival-identity-broader-detector-v2-20260526-235709
corrected_status: completed
corrected_input: local_dataset/runs/h001_rival_identity_broader_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
corrected_frame_root: local_dataset/runs/h001_rival_identity_broader_frames_v1
corrected_output: local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2
log: runtime/logs/rival-identity-broader-detector-substrate-v2-20260526-235709.log
detector_rows: 112
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.6339285714285714
rows_with_candidate_association: 71
associated_candidate_heading_count: 442
passes_detector_substrate_gate: true
uses_gt_for_action: false
expected_files:
  local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/detector_v3c/summary.json
  local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/detector_v3c/detector_candidate_associations.jsonl
  local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/rival_identity_detector_associations.jsonl
  local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/rival_identity_detector_substrate_summary.json
verification_command: cat local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/job_status.json && cat local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/rival_identity_detector_substrate_summary.json
```

Broader post-observation analyzer result:

```text
script: runtime/h001_runtime/analyze_rival_identity_post_observation.py
output: local_dataset/runs/h001_rival_identity_broader_post_observation_v1
detector_associations: local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/rival_identity_detector_associations.jsonl
plan: local_dataset/runs/h001_rival_identity_broader_plan_v1/rival_identity_observation_plan.jsonl
evaluation_labels: local_dataset/runs/h001_rival_identity_broader_source_v1/rival_identity_broader_evaluation_labels.jsonl
request_rows: 30
evidence_rows: 112
decision_rows: 30
commit/success/wrong/no-label: 0 / 0 / 0 / 0
defer_unresolved_identity_rows: 26
defer_object_existence_validation_rows: 4
failure_taxonomy_counts:
  post_observation_no_candidate_support: 26
  object_existence_deferred_no_independent_confirmation: 4
wrong_goal_commit_rows: 0
new_primary_success_commit_rows: 0
resolved_request_rows: 0
action_evidence_forbidden_key_count: 0
post_observation_gate_passed: false
uses_gt_for_action: false
```

Broader failure diagnostic:

```text
script: runtime/h001_runtime/diagnose_broader_post_observation_failure.py
output: local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1
plan_rows: 112
request_rows: 30
zero_standoff_plan_rows: 112
near_standoff_plan_rows: 112
rotation_fallback_plan_rows: 112
target_distance_from_viewpoint_m:
  min: 0.0
  mean: 0.0
  max: 0.0
target_position_to_visit_position_distance_m:
  min: 0.0
  mean: 0.0
  max: 0.0
associated_rows: 442
own_associated_rows: 0
cross_associated_rows: 442
mechanism_counts:
  degenerate_zero_standoff_cross_association: 22
  degenerate_zero_standoff_no_visible_candidate: 8
planner_standoff_gate_passed: false
own_association_available: false
post_observation_rule_change_allowed: false
uses_gt_for_action: false
uses_gt_for_analysis: false
```

Zero-standoff-safe planner revision contract:

```text
contract: manifests/h001_rival_identity_broader_standoff_planner_v1.json
planner_name: rival_identity_pair_probe_standoff_v1
reuse:
  runtime/h001_runtime/plan_association_recovery_observation.py::NavmeshSnapper
  runtime/h001_runtime/plan_association_recovery_observation.py::plan_standoff_viewpoint
allowed_action_time_inputs:
  candidate position
  candidate visit_position
  same-request rival candidate positions
  semantic/support metadata
  Habitat navmesh for navigability/snap only
forbidden_action_time_inputs:
  GT object position
  GT geodesic distance
  evaluation_only_candidate_correct
  success/wrong labels
standoff_distances_m: 1.25, 1.75, 2.25
preferred_standoff_distance_m: 1.75
min_standoff_distance_m: 0.75
max_standoff_distance_m: 3.25
zero_standoff_policy: forbidden
rotation_fallback_policy: forbidden_for_planned_rows
candidate_visit_position_fallback_policy: forbidden_when_target_distance_from_viewpoint_m_is_below_min_standoff_distance_m
minimum_geometry_gate:
  planned_request_rows_minimum: 20
  planned_scene_count_minimum: 5
  planned_query_count_minimum: 3
  zero_standoff_plan_rows: 0
  near_standoff_plan_rows: 0
  rotation_fallback_plan_rows: 0
  target_distance_from_viewpoint_min_m: 0.75
  target_distance_from_viewpoint_max_m: 3.25
  navmesh_snapped_or_geometry_valid_row_rate_minimum: 0.8
planned_outputs:
  plan_output: local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1
  frame_output: local_dataset/runs/h001_rival_identity_broader_frames_standoff_v1
  detector_output: local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_v1
  post_observation_output: local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_v1
```

Standoff planner implementation smoke:

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
mode: --viewpoint-mode standoff
output: local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1
docker_py_compile: passed
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
next_gate: frame export and row-level nonblank sanity on standoff plan
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
failure_diagnosis: dropped rows were all standoff_geometry fallback with standoff_navmesh_navigable false
detector_rerun_allowed: false
```

Navmesh-only standoff repair:

```text
script: runtime/h001_runtime/plan_rival_identity_observation.py
mode: --viewpoint-mode standoff --require-navmesh-standoff
plan_output: local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1
frame_output: local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1
filtered_frame_summary: local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
plan_rows: 104
planned_request_rows: 28
skipped_rows: 8
skip_reason: standoff_navmesh_required
planned_scene_count: 9
planned_query_count: 6
viewpoint_source_counts:
  standoff_navmesh: 104
rows_exported: 104
rendered_heading_count: 997
nonblank_output_rows: 104
dropped_rows: 0
removed_blank_heading_count: 0
row_level_nonblank_gate_passed: true
strict_no_blank_heading_gate_passed: true
v2_detector_rows: 38
v2_detector_box_rate: 1.0
v2_sam2_mask_rate: 1.0
v2_candidate_association_rate: 0.8158
uses_gt_for_action: false
next_gate: evidence diagnostic
```

Navmesh-only standoff detector/SAM2 substrate job launch:

```text
status: completed
launched_at: 2026-05-27T01:11:37+09:00
tmux_session: h001-rival-identity-broader-standoff-navmesh-detector-20260527-011137
working_directory: /home/yoohyun/research3
script: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
frames: local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl
frame_root: local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1
candidate_artifact: local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl
output: local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/rival-identity-broader-standoff-navmesh-detector-20260527-011137.log
status_file: local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1/job_status.json
expected_files:
  detector_v3c/summary.json
  detector_v3c/detector_candidate_associations.jsonl
  rival_identity_detector_associations.jsonl
  rival_identity_detector_substrate_summary.json
verification_command: cat local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1/job_status.json && cat local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1/rival_identity_detector_substrate_summary.json
launch_command: TS=20260527-011137 ROOT=/home/yoohyun/research3 PLAN_OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1 FRAMES=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl FRAME_ROOT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1 FRAME_EXPORT_SUMMARY=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1/summary.json CANDIDATE_ARTIFACT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1/rival_identity_candidate_artifact.jsonl OUT=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1 EXPECTED_FRAME_ROWS=104 MAX_FRAMES=104 MAX_DEBUG_IMAGES=180 LOG=/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/rival-identity-broader-standoff-navmesh-detector-20260527-011137.log STATUS=/home/yoohyun/research3/local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1/job_status.json bash /home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/rival_identity_pair_probe_detector_substrate.sh
initial_status: detector_mask_scoring
```

Fresh validation gate after observation:

```text
wrong_goal_commit_rows == 0
no_label_commit_rows == 0
new_primary_success_commit_rows >= 1
resolved_request_rows >= 1
action_evidence_forbidden_key_count == 0
uses_gt_for_action == false
```

Promotion beyond this source requires a larger source:

```text
request_rows >= 20
request_scenes >= 5
request_queries >= 3
at least one non-furniture or small-object query
same frozen analyzer and thresholds
failure taxonomy reported for all unresolved rows
```

#### 에이전트 추론

`rival_identity_generalization_v1` was the right next source because it is a frozen scene-disjoint ObjectNav dense-conflict split and did not reuse the local diagnostic scenes. The result is a useful negative fresh validation: the substrate is strong, but the post-observation commit rule is unsafe when a request has no real rival and the only focus candidate is a false positive.

### 에이전트 추론

The contract keeps this step tied to active perception rather than another terminal arbitration threshold. The broader validation failed in an informative way, and the taxonomy split now separates object-existence false positives from same-category rival disambiguation. `object_existence_validation` is currently handled as a no-commit safety branch, not as rival-identity arbitration. The independent object-existence probe confirms the two current single-positive rows are avoided wrong-goals. Broader source design, source miner, row-level frame substrate, corrected detector/SAM2 substrate, zero-standoff-safe planner, and navmesh-only frame/nonblank gate now pass. The current blocker is not perception availability and not a reason to loosen the post-observation rule. The next evidence must show that detector-backed observation recovers own-view identity support.

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

## Partial Relation-Depth Association-Geometry Repair Diagnostic

### 사실

- Date checked: 2026-06-01
- Contract: `manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1.json`
- Script: `runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair.py`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`
- Output: `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair_v1`
- Repair/request rows: `2/2`
- Target rows: `rival_identity:3` `sofa` `vlmaps:export:sofa:spatial_nms:2`; `rival_identity:5` `bed` `vlmaps:export:bed:spatial_nms:9`
- Exact failed completion association/depth-consistent counts: `0/0`
- Exact failed completion inside-mask count: `5`
- Same-requested / other-requested associated heading counts: `2/14`
- Repair diagnostic actions: `request_anchor_selection_repair_for_association_geometry 1`, `request_direction_specific_reobservation_repair 1`
- Action forbidden keys: `0`
- Terminal commits: `0`
- `uses_gt_for_action`: `false`
- Gate: `association_geometry_repair_diagnostic_gate_passed true`

Docker verification:

```bash
docker run --rm --ipc=host --user $(id -u):$(id -g) \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace -w /workspace \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  python -m h001_runtime.diagnose_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_repair
```

### 에이전트 추론

This diagnostic separates two nonterminal repair mechanisms. `sofa` can recover association under the same requested direction through another relation-anchor/completion row, while `bed` recovers association only under another requested direction. This supports a follow-up repair contract, not terminal goal-validity utility.

### Follow-up Router Gate

The follow-up repair contract is frozen at `manifests/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_followup_repair_v1.json`.

It keeps both mechanisms separate:

- `rival_identity:3` `sofa`: `route_to_relation_anchor_selection_repair`
- `rival_identity:5` `bed`: `route_to_direction_specific_reobservation_repair`

The router is now implemented at `runtime/h001_runtime/route_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_followup_repair.py` and Docker-run at `local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_association_geometry_followup_repair_v1`.

```text
followup/request rows: 2 / 2
followup routes:
  route_to_relation_anchor_selection_repair: 1
  route_to_direction_specific_reobservation_repair: 1
route_mapping_status_counts: mapped 2
request_route_status_counts: routed 2
exact failed completion association/depth/inside-mask: 0 / 0 / 5
same-requested / other-requested associated heading counts: 2 / 14
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
uses_gt_for_analysis: false
gate: association_geometry_followup_repair_gate_passed true
paper_claim_allowed: false
```

### Relation-Anchor Selection Repair Contract

The relation-anchor selection repair probe contract is frozen at `manifests/h001_relation_anchor_selection_repair_v1.json`.

```text
target request: rival_identity:3
scene/query: QaLdnwvtxbs / sofa
target candidate: vlmaps:export:sofa:spatial_nms:2
target route: route_to_relation_anchor_selection_repair
failed explicit anchor:
  decision_id: QaLdnwvtxbs_sofa_58449f72249b14b7
  relation_anchor_candidate_id: vlmaps:export:sofa:spatial_nms:1
  requested/standoff direction: relation_anchor_to_target / relation_anchor_to_target
  association/depth/inside-mask: 0 / 0 / 4
same-direction anchorless recovery:
  decision_id: QaLdnwvtxbs_sofa_766fbb91687fb944
  context_candidate_id: vlmaps:export:sofa:spatial_nms:0
  requested/standoff direction: relation_anchor_to_target / relation_anchor_to_target
  association/depth/inside-mask: 2 / 1 / 4
gate: relation_anchor_selection_repair_contract_gate_passed true
paper_claim_allowed: false
```

The probe is now implemented at `runtime/h001_runtime/probe_relation_anchor_selection_repair.py` and Docker-run at `local_dataset/runs/h001_relation_anchor_selection_repair_v1`.

```text
probe/request rows: 2 / 1
probe roles:
  failed_explicit_relation_anchor_row: 1
  same_direction_anchorless_recovery_row: 1
nonterminal action: request_relation_anchor_selection_replay 2
failed explicit anchor association/depth/inside-mask: 0 / 0 / 4
same-direction anchorless recovery association/depth/inside-mask: 2 / 1 / 4
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
uses_gt_for_analysis: false
gate: relation_anchor_selection_repair_probe_gate_passed true
paper_claim_allowed: false
```

에이전트 추론: This narrows the `sofa` branch to a reproducible relation-anchor selection replay/audit, not to a goal-validity rule. The direction-specific re-observation repair for `rival_identity:5` `bed` is a separate branch contract and is frozen below.

### Direction-Specific Re-observation Repair Contract

The direction-specific re-observation repair probe contract is frozen at `manifests/h001_direction_specific_reobservation_repair_v1.json`.

```text
target request: rival_identity:5
scene/query: bCPU9suPUw9 / bed
target candidate: vlmaps:export:bed:spatial_nms:9
target route: route_to_direction_specific_reobservation_repair
failed requested direction:
  requested/standoff direction: relation_anchor_to_target / compass_315
  explicit anchor decision: bCPU9suPUw9_bed_48b07c346eb4683f
  explicit anchor/context: vlmaps:export:bed:spatial_nms:2 / vlmaps:export:bed:spatial_nms:2
  association/depth/inside-mask: 0 / 0 / 1
  anchorless decision: bCPU9suPUw9_bed_54cf4778171bf856
  anchorless context: vlmaps:export:bed:spatial_nms:0
  association/depth/inside-mask: 0 / 0 / 1
recovered target-to-relation-anchor direction:
  explicit anchor decision: bCPU9suPUw9_bed_4ccded6b70ddf90a
  explicit anchor/context: vlmaps:export:bed:spatial_nms:2 / vlmaps:export:bed:spatial_nms:2
  association/depth/inside-mask: 4 / 4 / 4
  anchorless decision: bCPU9suPUw9_bed_a6358d7274ab68e6
  anchorless context: vlmaps:export:bed:spatial_nms:1
  association/depth/inside-mask: 4 / 4 / 4
gate: direction_specific_reobservation_repair_contract_gate_passed true
paper_claim_allowed: false
```

사실: The source follow-up router gate remains `true`. Target follow-up/request rows are `1/1`; same-requested direction association is `0`, while other-requested direction association/depth/inside-mask counts are at least `8/8/8`. Action forbidden keys, terminal commits, and candidate commit/rejection rows remain `0`.

에이전트 추론: This contract isolates direction choice from relation-anchor choice. Both relation-anchor-to-target rows fail under the `compass_315` fallback, while both target-to-relation-anchor rows recover association and depth consistency. The next implementation should materialize four nonterminal probe rows and keep terminal utility, candidate rejection, `first_eval`, policy-scale comparison, and paper claims blocked.

The direction-specific re-observation repair probe is now implemented at `runtime/h001_runtime/probe_direction_specific_reobservation_repair.py` and Docker-run at `local_dataset/runs/h001_direction_specific_reobservation_repair_v1`.

```text
probe/request rows: 4 / 1
probe roles:
  failed_requested_direction_explicit_anchor_row: 1
  failed_requested_direction_anchorless_row: 1
  recovered_target_to_relation_anchor_explicit_anchor_row: 1
  recovered_target_to_relation_anchor_anchorless_row: 1
nonterminal action: request_direction_specific_reobservation_replay 4
failed explicit anchor association/depth/inside-mask: 0 / 0 / 1
failed anchorless association/depth/inside-mask: 0 / 0 / 1
recovered explicit anchor association/depth/inside-mask: 4 / 4 / 4
recovered anchorless association/depth/inside-mask: 4 / 4 / 4
same-requested / other-requested associated heading counts: 0 / 8
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
uses_gt_for_analysis: false
gate: direction_specific_reobservation_repair_probe_gate_passed true
paper_claim_allowed: false
```

에이전트 추론: This closes the association-geometry underlink branch split for the two target rows without turning either branch into a goal-validity rule. The remaining nonterminal residual branches are repeated-object relation-anchor ambiguity and depth stagnation; since repeated-object ambiguity covers more request rows, the next branch contract should start there.

### Repeated-Object Relation-Anchor Ambiguity Contract

The repeated-object relation-anchor ambiguity branch contract is frozen at `manifests/h001_repeated_object_relation_anchor_ambiguity_v1.json`; static source verification is recorded in `manifests/h001_repeated_object_relation_anchor_ambiguity_v1.verify.json`.

사실:

```text
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1
target branch action: route_to_repeated_object_relation_anchor_ambiguity_branch
scene/query: bxsVRursffK / plant
request ids: rival_identity:25, rival_identity:27, rival_identity:29
target request/branch rows: 3 / 12
candidate ids: vlmaps:export:plant:spatial_nms:0, spatial_nms:2, spatial_nms:4
residual classes:
  association_present_without_depth_improvement: 6
  depth_signal_not_candidate_associated: 3
  mask_projection_without_association_or_depth: 3
directions:
  relation_anchor_to_target: 9
  orthogonal_relation_axis: 3
completion association-positive / zero rows: 6 / 6
completion depth-consistent rows: 9
inside-mask rows: 12
completion association/depth/inside-mask sums: 18 / 12 / 42
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

Per-request pattern is identical for all three target requests: four residual rows, three candidate ids, two association-positive rows, two association-zero rows, three depth-consistent rows, and one orthogonal relation-axis row.

에이전트 추론: This branch should materialize a label-free repeated-object audit before any terminal utility. The required implementation must preserve the mixed evidence pattern instead of collapsing it into a positive association/depth shortcut.

The repeated-object relation-anchor ambiguity branch is now implemented at `runtime/h001_runtime/route_repeated_object_relation_anchor_ambiguity.py` and Docker-run at `local_dataset/runs/h001_repeated_object_relation_anchor_ambiguity_v1`.

```text
branch/request rows: 12 / 3
request ids: rival_identity:25, rival_identity:27, rival_identity:29
scene/query: bxsVRursffK / plant
candidate ids: spatial_nms:0, spatial_nms:2, spatial_nms:4
residual classes:
  association_present_without_depth_improvement: 6
  depth_signal_not_candidate_associated: 3
  mask_projection_without_association_or_depth: 3
directions:
  relation_anchor_to_target: 9
  orthogonal_relation_axis: 3
completion association-positive / zero rows: 6 / 6
completion depth-consistent rows: 9
inside-mask rows: 12
nonterminal action: request_repeated_object_relation_anchor_ambiguity_audit 12
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
uses_gt_for_analysis: false
gate: repeated_object_relation_anchor_ambiguity_branch_gate_passed true
paper_claim_allowed: false
```

에이전트 추론: This closes the repeated-object relation-anchor ambiguity branch as a nonterminal mechanism audit. It is useful reviewer-defense scaffolding because it preserves the mixed evidence pattern without labels or terminal actions. The remaining residual branch is depth stagnation: `route_to_depth_stagnation_branch` should get the next contract before terminal utility, candidate rejection, `first_eval`, policy-scale comparison, or paper claims are reconsidered.

### Depth-Stagnation Branch Contract

The depth-stagnation branch contract is frozen at `manifests/h001_depth_stagnation_branch_v1.json`; static source verification is recorded in `manifests/h001_depth_stagnation_branch_v1.verify.json`.

사실:

```text
source: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_branch_handling_v1
target branch action: route_to_depth_stagnation_branch
scene/query: 4ok3usBNeis / sofa
request id: rival_identity:22
candidate id: vlmaps:export:sofa:spatial_nms:2
target request/branch rows: 1 / 1
request residual status: association_present_but_depth_not_improved
residual class: association_present_without_depth_improvement
direction: target_to_relation_anchor
prior association/depth-consistent/depth-mismatch/inside-mask: 3 / 1 / 7 / 7
completion association/depth-consistent/inside-mask: 3 / 1 / 4
completion status: relation_depth_completion_partial
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This branch is a depth-stagnation audit, not a goal-validity rule. Candidate association and depth consistency are present, but the evidence remains partial and does not improve enough to support ObjectNav commitment.

The depth-stagnation branch is now implemented at `runtime/h001_runtime/route_depth_stagnation_branch.py` and Docker-run at `local_dataset/runs/h001_depth_stagnation_branch_v1`.

```text
branch/request rows: 1 / 1
request id: rival_identity:22
scene/query: 4ok3usBNeis / sofa
candidate id: vlmaps:export:sofa:spatial_nms:2
residual class: association_present_without_depth_improvement
direction: target_to_relation_anchor
prior association/depth-consistent/depth-mismatch/inside-mask: 3 / 1 / 7 / 7
completion association/depth-consistent/inside-mask: 3 / 1 / 4
depth/association delta: 0 / 0
nonterminal action: request_depth_stagnation_audit 1
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
uses_gt_for_analysis: false
gate: depth_stagnation_branch_gate_passed true
paper_claim_allowed: false
```

에이전트 추론: This closes the last residual partial relation-depth branch as a nonterminal audit. It should be synthesized with association-geometry repair, relation-anchor selection repair, direction-specific repair, and repeated-object ambiguity before any terminal utility, candidate commit/rejection, `first_eval`, policy-scale comparison, or paper claims are reconsidered.

### Residual Partial Relation-Depth Branch Synthesis

The residual branch synthesis contract is frozen at `manifests/h001_residual_partial_relation_depth_branch_synthesis_v1.json`; Docker verification is recorded in `manifests/h001_residual_partial_relation_depth_branch_synthesis_v1.verify.json`.

사실:

```text
implementation: runtime/h001_runtime/synthesize_residual_partial_relation_depth_branches.py
output: local_dataset/runs/h001_residual_partial_relation_depth_branch_synthesis_v1
synthesis gate: true
family rows: 3
request/source-branch rows: 6 / 15
family output rows:
  association_geometry_underlink: 8
  repeated_object_relation_anchor_ambiguity: 12
  depth_stagnation: 1
family synthesis status:
  nonterminal_audit_or_repair_only: 3
nonterminal actions:
  request_depth_stagnation_audit: 1
  request_direction_specific_reobservation_replay: 4
  request_relation_anchor_selection_replay: 2
  request_repeated_object_relation_anchor_ambiguity_audit: 12
  route_to_direction_specific_reobservation_repair: 1
  route_to_relation_anchor_selection_repair: 1
promotable terminal outcome rows: 0
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The residual accounting gate is now closed, but the outcome is terminal-blocking. All three branch families are useful mechanism evidence, yet none creates a label-free commit or rejection authority. The promotion requirement gate below defines what extra evidence would make a branch outcome promotable; terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked.

### Residual Branch Promotion Requirement

The residual branch promotion requirement contract is frozen at `manifests/h001_residual_branch_promotion_requirement_v1.json`; Docker verification is recorded in `manifests/h001_residual_branch_promotion_requirement_v1.verify.json`.

사실:

```text
implementation: runtime/h001_runtime/define_residual_branch_promotion_requirements.py
output: local_dataset/runs/h001_residual_branch_promotion_requirement_v1
promotion requirement gate: true
source family/request/branch rows: 3 / 6 / 15
requirement rows: 3
status:
  defined_not_satisfied: 3
branch priority:
  1. repeated_object_relation_anchor_ambiguity
  2. association_geometry_underlink
  3. depth_stagnation
top priority family: repeated_object_relation_anchor_ambiguity
promotable family rows: 0
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This gate defines what would be required before a residual branch can become paper-facing terminal utility, and it confirms that none of the current branch outcomes satisfies those requirements. The next workflow step is not terminal utility; it is the repeated-object relation-anchor consistency evidence contract frozen below for the `bxsVRursffK/plant` branch family. That contract must test stable relation-anchor candidate assignment, conflict-free candidate-specific support, candidate-associated depth consistency, and orthogonal-axis contradiction before any candidate commit/rejection can be reconsidered.

### Repeated-Object Relation-Anchor Consistency Evidence Contract

The repeated-object relation-anchor consistency evidence contract is frozen at `manifests/h001_repeated_object_relation_anchor_consistency_evidence_v1.json`; static source verification is recorded in `manifests/h001_repeated_object_relation_anchor_consistency_evidence_v1.verify.json`.

사실:

```text
source promotion output: local_dataset/runs/h001_residual_branch_promotion_requirement_v1
source repeated-object branch output: local_dataset/runs/h001_repeated_object_relation_anchor_ambiguity_v1
source prior context anchors: local_dataset/runs/h001_expanded_retrieval_goal_validity_partial_relation_depth_observation_v1/partial_relation_depth_context_anchor_rows.jsonl
promotion requirement gate: true
repeated-object branch gate: true
target scene/query: bxsVRursffK / plant
target request/branch rows: 3 / 12
target request ids: rival_identity:25, rival_identity:27, rival_identity:29
target candidate ids: spatial_nms:0, spatial_nms:2, spatial_nms:4
prior context anchor rows: 36
prior context candidate ids: spatial_nms:0, spatial_nms:2, spatial_nms:4, spatial_nms:7, spatial_nms:8
minimum candidate-anchor pair rows: 18
minimum observation target rows: 27
required observation roles:
  candidate_own_view
  relation_anchor_context_view
  orthogonal_axis_challenge_view
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: This contract is the first concrete promotion probe for a residual branch. It requires independent relation-anchor consistency evidence before any terminal utility. The Docker-based materializer/planner below now writes request, candidate, pair, observation target, skipped, candidate artifact, and summary files under `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_v1`.

### Repeated-Object Relation-Anchor Consistency Planner

사실:

```text
implementation: runtime/h001_runtime/plan_repeated_object_relation_anchor_consistency.py
output: local_dataset/runs/h001_repeated_object_relation_anchor_consistency_v1
planner gate: true
source branch/request/context-anchor/prior-plan rows: 12 / 3 / 36 / 36
output request/candidate/pair/observation rows: 3 / 9 / 27 / 27
candidate artifact rows/candidates: 1 / 5
skipped rows: 0
minimum context candidates per request: 4
minimum observation roles per candidate: 3
view roles:
  candidate_own_view: 9
  relation_anchor_context_view: 9
  orthogonal_axis_challenge_view: 9
action forbidden keys: 0
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The planner is nonterminal evidence materialization. It preserves the repeated-object branch as an active evidence acquisition problem rather than a confidence-based commit/reject rule. The next runnable workflow step is a frame/projection smoke over the materialized observation targets. Terminal utility, `first_eval`, policy-scale comparison, candidate commit/rejection, and paper claims remain blocked.

### Repeated-Object Relation-Anchor Consistency Frame/Projection Smoke

사실:

```text
wrapper: runtime/jobs/repeated_object_relation_anchor_consistency_frame_projection.sh
verify: manifests/h001_repeated_object_relation_anchor_consistency_frame_projection_v1.verify.json
frame output: local_dataset/runs/h001_repeated_object_relation_anchor_consistency_frames_v1
projection output: local_dataset/runs/h001_repeated_object_relation_anchor_consistency_projection_v1
frame rows/headings: 27 / 180
nonblank rows/headings: 27 / 180
removed blank headings: 0
projection rows/expected: 27 / 27
projection visible rows/rate: 27 / 1.0
missing candidate rows: 0
explicit candidate-id selection rows: 27
frame revision metadata rows: 27
view roles:
  candidate_own_view: 9
  relation_anchor_context_view: 9
  orthogonal_axis_challenge_view: 9
GT action rows: 0
projection gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The frame/projection substrate is ready for detector/SAM2 scoring. This result is still not a relation-anchor consistency proof; it only confirms that the planned viewpoints can be rendered and that target candidate projection anchors are visible without action-label leakage. Terminal utility, candidate commit/rejection, `first_eval`, policy-scale comparison, and paper claims remain blocked.

### Repeated-Object Relation-Anchor Consistency Detector/SAM2 Substrate

사실:

```text
wrapper: runtime/jobs/repeated_object_relation_anchor_consistency_detector_substrate.sh
base wrapper: runtime/jobs/expanded_retrieval_detector_substrate.sh
verify: manifests/h001_repeated_object_relation_anchor_consistency_detector_substrate_v1.verify.json
detector output: local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_substrate_v1
docker image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
max candidates per frame: 2
frame/detector rows: 27 / 27
detector box/SAM2/candidate association rates: 1.0 / 1.0 / 0.8889
rows with candidate association: 24
associated candidate heading count: 69
detector boxes/masks: 135 / 135
association rows: 360
selected candidate count rows: 2:27
explicit candidate-id selection rows: 27
candidate point field: grounded_position
association depth tolerance: 1.0m
GT action rows: 0
detector substrate gate: true
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The detector/SAM2 substrate is now strong enough to freeze a post-detector consistency analyzer contract. It is still substrate evidence only. The analyzer must decide whether target/context support is stable and conflict-free across `candidate_own_view`, `relation_anchor_context_view`, and `orthogonal_axis_challenge_view`; it must not convert visibility or association alone into terminal ObjectNav utility.

### Repeated-Object Relation-Anchor Consistency Detector Evidence Contract

사실:

```text
contract: manifests/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.json
verify: manifests/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.verify.json
implementation target: runtime/h001_runtime/analyze_repeated_object_relation_anchor_consistency_evidence.py
expected output: local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1
source gates:
  planner: true
  projection: true
  detector substrate: true
source request/candidate/pair/observation rows: 3 / 9 / 27 / 27
detector rows: 27
detector association rows: 360
detector box/SAM2/candidate association: 1.0 / 1.0 / 0.8889
rows with candidate association: 24
associated candidate heading count: 69
selected candidate count rows: 2:27
required view/candidate/request evidence rows: 27 / 9 / 3
required candidate-context pair rows: 27
target association by role:
  candidate_own_view: 6/9
  relation_anchor_context_view: 9/9
  orthogonal_axis_challenge_view: 9/9
context association by role:
  candidate_own_view: 3/9
  relation_anchor_context_view: 0/9
  orthogonal_axis_challenge_view: 0/9
terminal commits: 0
candidate commit/rejection rows: 0 / 0
uses_gt_for_action: false
paper_claim_allowed: false
```

에이전트 추론: The frozen contract turns the detector substrate into a concrete analyzer implementation target. The required analyzer output must distinguish stable target support from repeated-object ambiguity and context leakage. A later terminal-utility contract remains blocked unless this analyzer reports a promotable branch outcome without label leakage.
