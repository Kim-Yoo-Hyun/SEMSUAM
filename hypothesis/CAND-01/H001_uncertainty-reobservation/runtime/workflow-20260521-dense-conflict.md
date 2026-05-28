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

The detector evidence gate now has a geometry-safe frame substrate: only source-pool-valid rows are rendered, each candidate observation uses a navmesh standoff viewpoint, and frame export produces no blank rows or headings. The skipped candidates are navmesh-infeasible under the current standoff policy, not GT-filtered. The first detector/SAM2 substrate failed because candidate projection and depth association were weak despite detector boxes and masks being available. The failure taxonomy shows the dominant blocker is not detector availability but out-of-FOV candidate projection, with a smaller depth-mismatch association path. The design probe shows this is vertical anchor uncertainty rather than horizontal yaw: all out-of-FOV projections are `x_in_y_above`, and a category-agnostic projection-anchor height sweep recovers all `projection_never_visible` rows in replay. Revised plan/projection smoke passes and preserves the revision metadata through a 2-row renderer passthrough smoke. The fixed-anchor detector/SAM2 rerun also passes the substrate gate with candidate association rate `0.7381`, compared with the previous `0.0714`. Terminal commit and paper claims remain blocked. Fresh/predeclared source freeze, fresh detector/SAM2 substrate, fresh detector evidence diagnostic, and ambiguity-aware objective contract pass on a small source. Paper-scale source freeze, planner compatibility, source-pool proxy, detector observation planning, upper-anchor frame/projection smoke, detector/SAM2 substrate, detector evidence diagnostic, ambiguity objective application, local-context contract, local-context planner smoke, and local-context frame/projection smoke now pass; the next step is local-context detector/SAM2 substrate.

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
