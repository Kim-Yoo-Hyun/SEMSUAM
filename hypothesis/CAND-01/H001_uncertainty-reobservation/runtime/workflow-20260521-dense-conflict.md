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
runtime/jobs/dense_conflict_candidate_artifact.sh
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
nvidia-smi: Failed to initialize NVML: Driver/library version mismatch
kernel_module: 580.126.09
user_space_library: 580.159.03
docker_gpu_error: failed to fulfil mount request: open /run/nvidia-persistenced/socket: no such file or directory
```

Resume command after host NVIDIA runtime is fixed:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-dense-conflict-artifact-${ts}" \
  "cd /home/yoohyun/research3 && TS=${ts} bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh"
```

Completion check:

```bash
cat /tmp/research3-runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1/pipeline_status.json
cat /tmp/research3-runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1/coverage_check.json
cat /tmp/research3-runs/h001_dense_conflict_recall_gate_spatial_nms_p95_k100_d10_v1/dense_conflict_recall_summary.json
```

### 에이전트 추론

The current blocker is host environment, not dense-conflict harness logic. Do not launch detector/association validation until the dense artifact job completes and `dense_conflict_recall_summary.json` passes the primary recall gate.

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

Planned output root:

```text
/tmp/research3-runs/h001_dense_conflict_validation_v1
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
