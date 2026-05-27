# Schedule

## Purpose

H001을 6개월-1년 범위에서 first probe, Step 4-5 SLAM extension, real-world validation으로 순차 확장하는 연구 일정을 정의한다.

이 문서는 논문 제목이나 최종 claim을 확정하지 않는다. 각 단계가 다음 단계로 넘어가기 위한 evidence gate를 정한다.

## Facts

- Date checked: 2026-05-27
- Active hypothesis: H001 `Semantic-SLAM Uncertainty Re-observation`
- Primary benchmark path: Habitat ObjectNav with HM3D, then HM3D-OVON extension.
- Available runtime gates: HM3D / HM3D-OVON Docker mount, `habitat-h001` smoke, logging schema, non-GT candidate adapter, `VLMaps` artifact exporter, synthetic alignment adapter.
- Current paper-facing blocker: independent `goal_validity_arbitration_v1` validation produced a strict-safe/inert result, while the default counterfactual produced nontrivial but unsafe commits; `discriminative_rival_view_planner_v1` v2 frame/nonblank and detector/SAM2 substrate gates pass, but `discriminative_rival_view_evidence_v1` and its failure diagnostic block threshold tuning and fresh validation. Expanded retrieval now has an analysis-only guard design, non-GT proxy feature extraction, and a diagnostic source-pool validity proxy; the next implementation gate is frame/detector evidence for proxy detector-eligible rows.
- First-probe gate: `07_evaluation_contract.md`.
- Real-world setup gate: `03_feasibility.md`.
- Long-running I/O-heavy jobs must follow `AGENTS.md` background-task policy.

## Paper Claims

- ObjectNav papers commonly report `Success Rate` and `SPL`.
- Semantic navigation and semantic memory papers motivate candidate confidence, re-observation, and wrong-goal failure analysis.
- Active SLAM papers motivate viewpoint utility terms that improve pose graph, localization, and map consistency.

## Inferences

The top-tier path should not start with real-world deployment. The strongest sequence is:

1. make the simulator evidence reproducible and non-GT,
2. show semantic uncertainty predicts and reduces wrong-goal commitment,
3. add SLAM-side utility only after Step 1-3 is positive,
4. use real-world validation as a later repeatability and deployment check.

## Top-Tier Alignment Check

### Facts

- Date checked: 2026-05-27
- The current H001 direction targets adaptive AI robotics through environmental perception intelligence, semantic memory, SLAM uncertainty, and navigation utility.
- Current planned benchmark path is `HM3D ObjectNav` first, `HM3D-OVON` second, and real-world validation only after simulator evidence is stable.
- Current primary metrics include `Success Rate`, `SPL`, `wrong_goal_visit`, `wasted_path`, candidate coverage, semantic uncertainty calibration, pose graph connectivity, map error, semantic accuracy, and `ATE/RPE` when trajectory GT is available.
- Latest H001 diagnostic rejects same-evidence threshold tuning: strict `goal_validity_arbitration_v1` has commit/success/wrong `0/0/0`, while default unique-strong identity has `7/4/3` on the frozen independent source.
- `goal_validity_revision_v2` currently routes unresolved requests into branch-specific active evidence: `request_discriminative_rival_view 14`, `request_expanded_retrieval 8`, `request_object_existence_confirmation 6`, and `request_goal_validity_confirmation 2`.
- `discriminative_rival_view_planner_v1` is the first branch-specific planner contract; it targets contrastive focus-rival pair views with explicit pair candidate ids.
- `discriminative_rival_view_planner_v1` v2 plan/frame smoke passes with `14` planned request rows, `38` plan rows, `10` navmesh-snapped common pair views, `28` matched dual standoff rows, zero/near-standoff `0/0`, frame rows/headings `38/222`, dropped rows `0`, and preserved role counts `common 10`, `focus 14`, `rival 14`.
- `discriminative_rival_view_planner_v1` detector/SAM2 substrate v2 passes with detector box/SAM2/candidate association `1.0/1.0/0.8158`.
- `discriminative_rival_view_evidence_v1` fails its diagnostic gate: evidence availability `1.0`, disambiguation `0.6429`, but single-correct preferred rate `0.0` and wrong-preference rate `0.3333`.
- `discriminative_rival_view_failure_diagnostic_v1` blocks threshold tuning and objective revision; dominant tags are `symmetric_cross_view_leak 7`, `rival_visible_from_focus_view 6`, `identity_score_near_tie 5`, `common_view_supports_both_candidates 5`, `no_valid_goal_pair_but_disambiguated 4`, and `rival_correct_own_view_evidence_weak 3`.
- Branch priority decision: define `request_expanded_retrieval` next; use discriminative views later as identity validation after retrieval expands the candidate set.
- `h001_expanded_retrieval_branch_v1` is frozen before implementation: expected request rows `8`, candidate budget `6-10`, GT/evaluation action inputs forbidden, terminal commit disabled, candidate-set validity gates first.
- `h001_expanded_retrieval_plan_v1` planner smoke passes: expected/request rows `8/8`, candidate-set rows `8`, plan rows `80`, candidates per request `10`, skipped rows `0`, duplicate candidate rate `0.0`, nonfinite position rate `0.0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- `h001_expanded_retrieval_candidate_set_validity_v1` analysis-only diagnostic passes label join with missing labels `0`; it has contains-correct `6/8`, no-valid `2/8`, source-top correct `1/8`, source-top wrong-goal `7/8`, wrong-top replacement `5/7`, and wrong-goal candidate present in `7/8`. Full-pool comparison shows `source_pool_no_valid_candidate 2`, `valid_set_with_wrong_goal_distractor 5`, `valid_set_without_wrong_goal_distractor 1`, and `selected_missed_full_pool_correct_rows 0`.
- `h001_expanded_retrieval_candidate_set_guard_v1` analysis-only guard design passes: `request_backend_retrieval_revision 2`, `request_detector_guarded_observation 5`, `request_lightweight_confirmation 1`, detector evidence allowed `6/8`, terminal commit rows `0`, `guard_design_gate_passed true`, `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false`.
- `h001_expanded_retrieval_guard_proxy_features_v1` non-GT proxy feature audit passes feature extraction but fails source-pool validity: proxy route counts `request_detector_guarded_observation_proxy 8`, target backend rows `2`, target backend routed to backend `0`, source-pool validity proxy recall `0.0`, evidence-allowed target recall `1.0`, and `proxy_ready_for_detector_gate false`.
- `h001_expanded_retrieval_source_pool_validity_proxy_v1` passes the current diagnostic source-pool gate: proxy route counts `request_backend_retrieval_revision_proxy 2` and `request_detector_guarded_observation_proxy 6`, consumed forbidden rows `0`, source-pool validity proxy recall `1.0`, evidence-allowed target recall `1.0`, backend targets escalated to evidence `0`, evidence targets blocked as backend `0`, `proxy_ready_for_detector_gate true`, `uses_gt_for_action false`, and `paper_claim_allowed false`.

### Paper Claims

- Recent open-vocabulary navigation and semantic memory papers motivate using environment-specific semantic memory, but they often leave semantic uncertainty, wrong-goal commitment, and map/pose-side utility weakly connected.
- Recent active semantic mapping and active SLAM papers motivate information-gain-driven viewpoint selection, but task-level navigation failure metrics are not always tied to semantic uncertainty.
- Recent `HM3D-OVON` and open-vocabulary embodied navigation work makes semantic ambiguity and unseen-object generalization more important than closed-class ObjectNav alone.

### Inferences

The current direction is aligned with recent AI, ML, CV, and Robotics top-tier trends if it is framed as semantic uncertainty becoming an active SLAM/navigation utility, not simply as adding `VLMaps` to ObjectNav. The latest result strengthens that framing: semantic uncertainty is no longer just a confidence threshold, but a router for additional evidence acquisition when terminal commitment is unsafe. The source-pool validity proxy removes the immediate detector-gate blocker on current diagnostic evidence. The remaining top-tier blockers are detector/viewpoint evidence quality on proxy detector-eligible rows and fresh/predeclared validation of the revised branch.

The dataset path is appropriate:

| Dataset / benchmark | Role | Reason |
| --- | --- | --- |
| `HM3D ObjectNav` | primary first probe | stable Habitat benchmark with standard `Success Rate` and `SPL`; useful for controlled wrong-goal and wasted-path analysis |
| `HM3D-OVON` | top-tier robustness extension | tests open-vocabulary ambiguity, seen/unseen categories, and semantic generalization |
| `MP3D` | optional compatibility check | useful for comparison with older embodied navigation work, but weaker as the main novelty benchmark |
| `Replica` / `ScanNet` / `OpenLex3D` | optional semantic representation probes | useful for semantic map quality or retrieval sanity, not the main active navigation benchmark |
| real-world robot logs | late validation | strengthens robotics/journal credibility only if external GT or calibrated event-level proxy exists |

The baseline path must be stronger than simple ablation:

| Baseline | Required role |
| --- | --- |
| `NoReobserve` | shows the wrong-goal failure mode exists |
| `RandomReobserve` | separates active selection from extra observation budget |
| `FrontierReobserve` | separates semantic uncertainty from geometry-only exploration |
| `CARe`-style confidence replanning | anchors comparison to recent confidence-aware navigation |
| `VLMaps` direct / semantic memory direct | shows gain is not from semantic memory alone |
| GT oracle references | diagnose candidate coverage and upper-bound policy/action failure, not a deployable baseline |
| `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` | required for Step 4-5 to prove semantic and SLAM utility are complementary |

### Novelty Risk

The main risk is that H001 can look like a combination of `VLMaps`, confidence replanning, and active SLAM if the evidence only reports `Success Rate` and `SPL`.

To make the contribution paper-facing, the schedule must preserve three evidence lines:

- semantic uncertainty predicts wrong-goal commitment before intervention;
- active re-observation reduces wrong-goal visit and wasted path against budget-aware baselines;
- adding SLAM uncertainty improves map/pose-side metrics over `SemanticOnly` without the effect being fully explained by `SLAMOnly`.

## Phase Plan

| Phase | Target time | Main question | Exit gate |
| --- | ---: | --- | --- |
| P0 | Week 0-2 | Can H001 produce aligned non-GT candidates in real HM3D scenes? | real HM3D `VLMaps` artifact has verified `alignment.json` and navigable candidates |
| P1 | Month 1-2 | Does `U_sem` predict wrong-goal candidate failure? | candidate coverage and `U_sem` validity pass on calibration split |
| P2 | Month 2-3 | Does active re-observation reduce wrong-goal visit and wasted path? | `SemanticOnly` passes first-probe gate against `NoReobserve` and `RandomReobserve` |
| P3 | Month 3-4 | Is the signal robust to stronger baselines and OVON ambiguity? | `CARe`-style / `FrontierReobserve` and HM3D-OVON checks do not remove the signal |
| P4 | Month 4-6 | Can semantic memory become active SLAM utility? | `SemanticSLAM` improves map/pose-side proxy over `SemanticOnly` and `SLAMOnly` |
| P5 | Month 6-9 | Is the result paper-facing? | fixed splits, ablations, error taxonomy, reproducible Docker commands, draft figure/table set |
| P6 | Month 9-12 | Does the idea survive small real-world validation? | ROS 2 bag / robot trial logs reproduce the failure decomposition with external GT or calibrated proxy |

## P0: Alignment and Split Freeze

### Goal

Turn the current synthetic alignment smoke into real HM3D scene-specific non-GT semantic artifacts.

### Required Work

- Decide HM3D scene subset and fixed episode ids for smoke, calibration, and first evaluation.
- Generate real HM3D `VLMaps` map artifacts from a controlled Habitat pre-exploration trajectory.
- Generate `alignment.json` from the same trajectory export metadata, not from GT object labels.
- Verify aligned candidate positions with Habitat navmesh.
- Record long-running map generation commands, logs, output paths, expected files, and verification commands.

### Exit Gate

- At least one HM3D scene has `artifact_jsonl` with `coordinate_frame = habitat_world`.
- Candidate visit positions are navigable or explicitly marked unreachable.
- `uses_gt_for_action = false` is preserved.
- Split file and episode ids are fixed before tuning `theta_uncertain` or utility weights.

### Failure Action

If real HM3D `VLMaps` alignment fails, do not run full ObjectNav metrics yet. Fix map construction metadata recovery first, or use a lightweight semantic proxy only for debugging.

## P1: Semantic Uncertainty Calibration

### Goal

Check whether object/node uncertainty is a valid failure predictor before implementing more policy complexity.

### Required Work

- Run 30-50 calibration episodes across at least 5 scenes.
- Compute `score_uncertainty`, `margin_uncertainty`, support features, and aggregate `U_sem`.
- Label candidate correctness only after non-GT candidate selection.
- Measure candidate coverage, reachable correct candidate rate, reachable distractor rate, wrong-goal prior rate, `AUROC`, `AUPRC`, Spearman, and high/low bucket gap.

### Exit Gate

- Candidate correctness labels are usable for at least 70 percent of evaluated episodes.
- At least 50 percent of episodes include both a reachable correct candidate and a reachable distractor candidate.
- `NoReobserve` wrong-goal visit rate is at least 10 percent on the selected subset.
- `U_sem` passes the validity gate in `07_evaluation_contract.md`.

### Failure Action

If `U_sem` fails, revise uncertainty features or candidate backend. Do not move to Step 4-5.

## P2: First Probe

### Goal

Test whether semantic uncertainty-driven active re-observation improves ObjectNav behavior without excessive travel cost.

### Required Work

- Implement `SemanticOnly` viewpoint selection.
- Compare the same episode ids under `NoReobserve`, `RandomReobserve`, `SemanticOnly`, and GT oracle references.
- Use commit-based `wrong_goal_visit`.
- Log `wrong_goal_visit_rate`, `mean_wasted_path_wrong_goal`, `mean_wasted_path_total`, `SPL`, `Success Rate`, and re-observation count.

### Exit Gate

- `SemanticOnly` passes the primary numeric gate against `NoReobserve`.
- `SemanticOnly` passes the random baseline sanity gate.
- GT oracle gap separates candidate-set coverage from policy failure.

### Failure Action

If wrong-goal improves but `SPL` drops too much, revise travel-cost arbitration. If `RandomReobserve` matches `SemanticOnly`, revise viewpoint objective before claiming contribution.

## P3: Robustness and Open-Vocabulary Extension

### Goal

Check whether the Step 1-3 signal survives stronger baselines and open-vocabulary ambiguity.

### Required Work

- Add or approximate `CARe`-style confidence replanning.
- Add `FrontierReobserve` or geometry-only reachable viewpoint baseline if implementation cost is acceptable.
- Run HM3D-OVON validation splits with fixed synonym handling.
- Run feature ablations for `score_uncertainty`, `margin_uncertainty`, support, travel cost, and visibility.

### Exit Gate

- Main signal keeps the same sign against stronger non-GT baselines.
- HM3D-OVON `val_seen` and `val_unseen` do not reverse the result direction.
- Failure taxonomy identifies whether errors are candidate coverage, uncertainty calibration, viewpoint selection, or navigation execution.

### Failure Action

If OVON fails while closed-class ObjectNav passes, keep the first claim closed-class and mark open-vocabulary robustness as future work or separate extension.

## P4: Step 4-5 SLAM Extension

### Goal

Extend semantic re-observation into active SLAM/navigation utility and evaluate map/pose consistency.

### Entry Gate

Do not enter P4 until the Step 4-5 promotion gate in `07_evaluation_contract.md` is satisfied. The default first entry is `P4-proxy`, using pose graph connectivity before adding a live SLAM backend.

### Required Work

- Build or use a separate SLAM evaluation image.
- Start with pose graph connectivity proxy as the first SLAM-side metric.
- Implement `SLAMOnly` and `SemanticSLAM` utility:

```text
U(v) = alpha * SemanticGain(v)
     + beta  * SLAMGain(v)
     - gamma * TravelCost(v)
     - eta   * Risk(v)
```

- Evaluate `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` on the same episodes.
- Add map error, semantic accuracy, localization failure count, pose graph connectivity, and `ATE/RPE` when trajectory GT is available.

### Exit Gate

- `SemanticSLAM` improves at least one map/pose-side metric over `SemanticOnly`.
- `SemanticSLAM` improves task behavior or keeps task behavior within the P2 acceptable cost bounds.
- `SLAMOnly` does not fully explain the improvement.
- Failure cases are logged separately: semantic candidate failure, unreachable viewpoint, localization failure, map update failure, and excessive travel cost.

### Failure Action

If `SemanticSLAM` only improves map/pose metrics by taking much longer paths, revise travel-cost normalization. If it does not improve over `SemanticOnly`, keep the paper centered on semantic re-observation and report SLAM extension as negative result.

## P5: Paper-Facing Consolidation

### Goal

Convert validated experiments into stable evidence for a thesis and possible AI, ML, CV, or Robotics top-tier submission.

### Required Work

- Freeze evaluation split and code state.
- Run final repeated evaluation with saved configs and Docker commands.
- Prepare ablation tables, failure taxonomy, qualitative route examples, and oracle gap analysis.
- Verify all claims trace back to logs, configs, datasets, and commands.
- Decide target venue style and paper outline only after result quality is visible.

### Exit Gate

- Main tables are reproducible from logged commands.
- Limitations are separated from claims.
- Negative results are recorded instead of hidden.
- Thesis-level narrative is stable even if top-tier submission needs more experiments.

## P6: Real-World Validation

### Goal

Test whether the same failure decomposition appears outside simulation.

### Required Work

- Confirm available robot base, RGB-D / stereo sensor, LiDAR, and GT setup.
- Use ROS 2 with `Nav2` if a mobile base is available.
- Use motion capture if available; otherwise use a calibrated `AprilTag` map for small-area event-level validation.
- Record ROS bag topics for `/tf`, `/odom`, `/cmd_vel`, `/scan`, RGB-D streams, semantic candidates, selected viewpoints, stop/commit events, and GT pose.
- Compare at least `NoReobserve`, `SemanticOnly`, and one SLAM/map-side variant if the hardware supports it.

### Exit Gate

- Logs reproduce the same event definitions as Habitat.
- Stop/commit-based `wrong_goal_visit` and wasted path are measurable.
- External GT or calibrated proxy supports `ATE/RPE` or event-level pose correctness.

### Failure Action

If GT is weak, present real-world results as qualitative or diagnostic only. Do not use wheel odometry alone as paper-facing `ATE/RPE` evidence.

## Decision Points

| Decision | Latest point | Default |
| --- | --- | --- |
| First paper includes real-world POC? | after P4 | simulation-first, real-world if GT is available |
| HM3D-OVON is core or extension? | after P2 | extension unless closed-class result is weak |
| Full `VLMaps` runtime needed? | during P0 | only if real HM3D map generation requires it |
| Live SLAM backend needed? | during P4 | start with pose graph proxy, add live backend only if necessary |
| Target venue paper or thesis-first? | after P5 | thesis-first evidence, top-tier submission if P2-P4 signal is strong |

## Immediate Next Task

Design expanded-retrieval frame/detector evidence gate for source-pool-valid rows.

The active observation/evaluation contract is frozen at `manifests/h001_rival_identity_observation_v1.json`. The observation planner is implemented at `runtime/h001_runtime/plan_rival_identity_observation.py`, and Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1` passes the diagnostic plan gate with six planned request rows, `19` plan rows, `0` skipped rows, and `uses_gt_for_action false`. Frame export smoke also passes at `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1` with `19/19` rows exported and `142` rendered headings. Detector substrate validation completed at `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1` with detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, and substrate gate `true`. The post-observation analyzer completed at `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1` with commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, and gate `true`.

Fresh-source design selects `rival_identity_generalization_v1`: `6` request rows from frozen `dense_conflict_generalization_v1` primary action evidence, across `3` scenes and `2` queries, excluding the previous diagnostic scenes. The source miner is implemented at `runtime/h001_runtime/build_rival_identity_generalization_manifest.py`; Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1` freezes `manifests/h001_rival_identity_generalization_v1.json`, and verify reports `ok true`, request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Planner smoke output `local_dataset/runs/h001_rival_identity_generalization_plan_v1` passes with request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, and `uses_gt_for_action false`. Frame export smoke output `local_dataset/runs/h001_rival_identity_generalization_frames_v1` passes with rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, nonblank RGB sanity pass, and `uses_gt_for_action false`. Detector/SAM2 substrate output `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1` passes with detector box/SAM2/candidate association `1.0/1.0/1.0`. Frozen post-observation analyzer output `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1` fails the gate with commit/success/wrong/no-label `4/2/2/0`. Failure diagnostic output `local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1` explains all wrong commits as single-positive-candidate `toilet` object-existence false positives and keeps the other four rows in rival-identity arbitration. Taxonomy split output `local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1` accepts this split with route counts `rival_identity_arbitration 4`, `object_existence_validation 2`, and failure taxonomy `none 2`, `rival_identity_unresolved_cross_view_aliasing 2`, `object_existence_false_positive_commit 2`. Object-existence no-commit branch output `local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1` passes the gate with commit/success/wrong `2/2/0` and defer-object-existence `2`; regression output `local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1` keeps diagnostic commit/success/wrong `1/1/0`. Independent object-existence probe output `local_dataset/runs/h001_rival_identity_object_existence_probe_v1` shows request rows `2`, naive wrong-goal rows `2`, wrong-goal avoided by defer `2`, success lost by defer `0`, and action evidence forbidden key count `0`. Broader validation design output `local_dataset/runs/h001_rival_identity_broader_validation_design_v1` freezes `risk_validation` as preferred source and selects `72` parent rows across `10` scenes and `6` queries, with estimated request rows `22`, top wrong-goal rows `41`, correct-and-wrong candidate rows `49`, and design gate pass. Broader source miner output `local_dataset/runs/h001_rival_identity_broader_source_v1` freezes `manifests/h001_rival_identity_broader_validation_v1.json`; verify reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` and `object_existence_validation 4`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Broader planner smoke output `local_dataset/runs/h001_rival_identity_broader_plan_v1` passes with request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, missing action rows `0`, candidate artifact rows/candidates `21/80`, plan gate `true`, and `uses_gt_for_action false`. Broader frame export output `local_dataset/runs/h001_rival_identity_broader_frames_v1` passes export with rows requested/exported `112/112`, rendered headings `862`, RGB/depth/metadata files `862/862/862`, and unique scenes `10`; nonblank filter output `nonblank_filter_v1` removes `56` blank headings, drops `0` rows, keeps `112` rows and `806` headings, and passes row-level nonblank gate. Corrected broader detector substrate later passed, but post-observation stayed safe and inert. Failure diagnostic `local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1` shows all `112` plan rows used zero-standoff target-distance `0.0m` viewpoints, yielding own associations `0` and cross associations `442`. Zero-standoff-safe standoff planner output `local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1` passes plan and geometry gates, but mixed-standoff frame export drops `5` geometry fallback rows. Navmesh-only standoff repair output `local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1` keeps plan rows `104`, planned request rows `28`, scenes `9`, queries `6`, and `uses_gt_for_action false`; frame output `local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1` passes row-level and strict no-blank gates with `104/104` rows and `997/997` headings. Navmesh-only detector/SAM2 substrate output `local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1` passes with detector rows `104`, detector box `0.9808`, SAM2 mask `0.9808`, candidate association `0.7212`, and `uses_gt_for_action false`. Fixed post-observation output `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1` fails with commit/success/wrong/no-label `7/0/7/0`. Unsafe diagnostic output `local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1` rejects threshold-only repair because simple guards still commit wrong goals or become inert. Contract `manifests/h001_rival_identity_strict_arbitration_v1.json` and implementation `analyze_rival_identity_post_observation.py --objective goal_validity_arbitration_v1` are now Docker-verified. Output `local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1` passes this diagnostic gate with commit/success/wrong/no-label `2/2/0/0`, but paper claim remains blocked. Independent/predeclared source `rival_identity_goal_validity_independent_v1` is now frozen from `v3_fresh_validation`; verify reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Independent substrate passes with plan rows `92`, frame headings `810`, detector box/SAM2/candidate association `1.0/1.0/0.6196`. Independent rerun output `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1` is safe but inert with commit/success/wrong/no-label `0/0/0/0`. Default counterfactual output `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1` is nontrivial but unsafe with commit/success/wrong/no-label `7/4/3/0`. Failure diagnostic output `local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1` rejects same-evidence threshold repair, and router output `local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1` routes all `30` rows into branch-specific next observation actions. Paper claim remains blocked until a fixed branch-specific observation method passes fresh/predeclared validation.
