# H001: Semantic-SLAM Uncertainty Re-observation

## Hypothesis

If an ObjectNav agent uses both pre-explored semantic map object/node uncertainty and SLAM uncertainty to choose active re-observation viewpoints, then wrong-goal visits and wasted path decrease while map/pose consistency improves, compared with semantic-only replanning and geometry-only exploration baselines.

## Why This Is Testable

- Intervention is explicit: semantic-SLAM uncertainty-aware active re-observation.
- Expected effects are measurable: wrong-goal visit, wasted path, map error, semantic accuracy, ATE/RPE, pose graph connectivity.
- Evaluation targets are staged: Habitat ObjectNav or replay subset first, SLAM/map-side metrics next.
- Baselines are available: no-reobservation, `CARe`-style replanning, semantic-only re-observation, geometry-only exploration.

## First Experiment

First probe는 small subset 또는 one-scene replay에서 semantic map uncertainty가 high인 object candidates를 만들고, re-observation 전후의 candidate decision과 navigation cost를 비교한다. 이 first probe는 H001 전체의 Step 1-3만 빠르게 falsify한다. Positive signal이 있으면 같은 H001 안에서 Step 4-5로 확장한다.

## Current Status

Active diagnostic. H001 remains a hypothesis, not a paper-ready claim.

## Current Gate

- Problem and hypothesis: `01_problem.md`, `02_hypothesis.md`
- Feasibility, fallback, real-world setup: `03_feasibility.md`
- First experiment, smoke results, sensitivity results, coverage status: `04_first_experiment.md`
- Uncertainty features: `05_uncertainty_features.md`
- Logging schema: `06_logging_schema.md`
- Evaluation contract, split discipline, numeric gates, Step 4-5 promotion gate: `07_evaluation_contract.md`
- Runtime integration, candidate backend, artifact generation, calibration commands: `08_runtime_integration.md`
- 6-12 month schedule: `15_schedule.md`
- Reproducibility entrypoint: `../../../docs/reproducibility.md`
- Dense conflict validation workflow: `runtime/workflow-20260521-dense-conflict.md`
- Cross-machine backup/restore: `../../../docs/reproducibility.md#google-drive-backup-manifest`
- Current next implementation target: design expanded-retrieval frame/detector evidence gate for source-pool-valid rows

## Latest Gate

### 사실

- Date checked: 2026-05-27
- `risk_validation_v1` and `v3_fresh_validation_v1` candidate coverage gates pass with non-GT `artifact_jsonl` candidates.
- V4 external evidence on `risk_validation_v1` passes the current external evidence gate with `commit_rate 0.20`, `success_commit_rate 0.20`, and wrong-goal commit `0.00`.
- V4 routes unresolved semantic uncertainty into `request_identity_confirmation` and `request_expanded_retrieval`.
- `ExternalCandidateFollowupObservation` planner produced `28` `risk_validation_v1` follow-up rows with `0` skipped rows.
- Follow-up detector smoke passed on `4` rows with detector box rate `1.00`, SAM2 mask rate `1.00`, and candidate association rate `0.75`.
- Follow-up evidence analyzer smoke passed safety with wrong-goal/no-valid commit rates `0.00`, but full gate failed because strong depth-associated follow-up evidence rate was `0.00`.
- Fixed dense backend terminal diagnostic is locally positive on two `y9hTuugGdiq/chair` rows, but it is not wrong-goal repair proof because all positive-support dense candidates are post-hoc correct.
- Independent dense conflict validation is designed in `runtime/workflow-20260521-dense-conflict.md`.
- Primary target rows are six scene/category rows from `v3_fresh_validation_v1` with correct and wrong positive-support candidates on all rows; secondary repeated-object stress rows are two `y9hTuugGdiq/sofa` rows.
- `h001_dense_conflict_v1` manifest verify passed with `8` rows and no duplicate episode keys.
- Final canonical recall gate for the existing `v3_fresh_spatial_p97_k20` primary substrate passed with `6/6` rows containing a correct candidate and recall@20 `1.0`.
- Frozen-row dense artifact job wrapper exists, but first launch failed before scene export because host NVIDIA runtime reports driver/library mismatch.
- Host/Docker NVIDIA runtime recovered on 2026-05-23. A default `/tmp` resume attempt failed because `/tmp/research3-data` was a stale empty directory.
- Canonical-path relaunch `h001-dense-conflict-artifact-canonical-20260523-140845` completed, but final recall gate failed: primary rows with correct candidate `3/6`, recall@20 `0.5`, required rows with correct `4/6`.
- Revised dense candidate generation `h001-dense-conflict-artifact-p90-k200-d5-20260523-150036` completed with `24` rows and `4800` candidates, but final recall gate also failed: primary rows with correct candidate `3/6`, recall@20 `0.5`, required rows with correct `4/6`.
- Dense conflict detector/association validation was materialized from the existing `v3_fresh` second-stage evidence at `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1`. The primary diagnostic passes with detector box `1.0`, SAM2 mask `1.0`, candidate association `0.8`, rows with correct+wrong positive support `6/6`, commit/success/wrong/no-valid `5/5/0/0`, selected-correct improvement over source-selected `3`, and `uses_gt_for_action false`.
- Secondary-stress held-out `sofa` validation was materialized at `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1`. It passes with recall rows with correct `2/2`, recall@20 `1.0`, detector box/SAM2/candidate association `1.0/1.0/1.0`, commit/success/wrong/no-valid `2/2/0/0`, selected-correct improvement over source-selected `2`, and `uses_gt_for_action false`.
- Broader split design was materialized at `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json`. It selects `scene_disjoint_first_eval_style` as the next path, keeps repeated-object rows as a stress slice, and defers HM3D-OVON until ObjectNav generalization is stable.
- `dense_conflict_generalization_v1` was frozen at `manifests/h001_dense_conflict_generalization_v1.json` with `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`, and `uses_gt_for_action false`.
- Generalization recall gate passed at `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1`: rows with correct `20/20`, recall@20 `1.0`, recall@5 `0.85`, first correct rank `1-9`, detector job allowed by recall gate.
- Detector substrate job for the frozen split completed in tmux `h001-dense-conflict-generalization-detector-20260523-170533`; output root is `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1`. Detector rows `20`, frame rows `20`, rendered headings `125`, detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`, associated rows `7`, substrate gate passed, and `uses_gt_for_action false`.
- Terminal evidence extraction was implemented with `runtime/h001_runtime/extract_dense_conflict_generalization_evidence.py`. Output `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1` has action evidence rows `20`, evaluation label rows `55`, associated/unassociated rows `7/13`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- Terminal policy design diagnostic rejects the current v0 rules: `semantic_top_if_supported` and `first_associated` commit `7/20` with `6` wrong-goal commits, while `support_score_best` and `proposed_conservative_v0` commit `7/20` with `3` success and `4` wrong-goal commits.
- Terminal guard design was implemented with `runtime/h001_runtime/design_dense_conflict_terminal_guard.py`. Docker output `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1` selects `strict_depth_consistency_v1`: `max_depth_error_m 0.33`, `min_associated_heading_count 2`, `min_mask_hit_count 2`, `max_semantic_rank 5`; same diagnostic split commit/success/wrong is `3/3/0`, associated commit rate is `3/7`, and `uses_gt_for_action false`.
- Frozen guard config was added at `manifests/h001_dense_conflict_terminal_guard_v1.json`, and fixed-rule validation was implemented with `runtime/h001_runtime/validate_dense_conflict_terminal_arbitration.py`. Docker output `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1` has action evidence forbidden key count `0`, stable metric match to design `true`, local fixed-rule validation pass `true`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`, and `uses_gt_for_action false`.
- Independent terminal validation contract was frozen at `manifests/h001_dense_conflict_terminal_independent_v1.json`. The primary independent profile `local_dataset/runs/h001_dense_conflict_independent_terminal_evidence_profile_v1` has rows `6`, associated rows `6`, scenes `3`, queries `2`, action evidence forbidden key count `0`, and naive `support_score_best` success/wrong `2/4`. The secondary stress profile `local_dataset/runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1` has rows `2`, associated rows `2`, and naive success/wrong `0/2`.
- Independent terminal validation failed without threshold changes. Primary output `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1` has commit/success/wrong `6/2/4`, no-label commits `0`, forbidden action keys `0`, and `terminal_validation_gate_passed false`. Secondary stress output `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1` has commit/success/wrong `2/0/2` and `terminal_validation_gate_passed false`.
- Failure diagnosis output `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1` identifies the dominant mechanism as saturated same-category rival ambiguity: wrong rows `6`, `repeated_wrong_instance_selected_by_saturated_support 5`, `guard_cannot_arbitrate_between_eligible_correct_and_wrong 1`. The revision path is `rival_identity_confirmation_v1` plus active observation, still diagnostic-only until detector/post-observation validation.
- `rival_identity_confirmation_v1` diagnostic policy was implemented at `runtime/h001_runtime/analyze_dense_conflict_rival_identity_policy.py`. Docker output `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1` has diagnostic pass `true`: commit/success/wrong `2/2/0`, request identity rows `6`, forbidden action keys `0`, and `uses_gt_for_action false`. Simpler alternatives fail: support/depth/semantic top commit `8/8` with `6` wrong-goal commits, while `defer_all_ambiguous` is safe but inert with `0` success commits.
- Active observation/evaluation contract was frozen at `manifests/h001_rival_identity_observation_v1.json`: request rows `6`, primary request rows `4`, secondary stress request rows `2`, planner `rival_identity_pair_probe_v1`, detector substrate gate `box/SAM2/association >= 0.80/0.80/0.50`, and post-observation gate `wrong_goal_commit_rows 0`, `new_primary_success_commit_rows >= 1`, `resolved_request_rows >= 1`.
- `rival_identity_pair_probe_v1` observation planner was implemented at `runtime/h001_runtime/plan_rival_identity_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1` passes the minimum plan gate: request rows `6`, planned request rows `6`, plan rows `19`, skipped rows `0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- `rival_identity_pair_probe_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1`: rows requested/exported `19/19`, rendered headings `142`, RGB/depth files `142/142`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity passed, and `uses_gt_for_action false`. Habitat rendering required Docker `--gpus all` for EGL context creation.
- `rival_identity_pair_probe_v1` detector substrate job completed at `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1`. Detector rows `19`, detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, rows with candidate association `12/19`, associated candidate heading count `57`, `uses_gt_for_action false`, and detector substrate gate `true`.
- `rival_identity_pair_probe_v1` post-observation evidence/validation contract is frozen in `07_evaluation_contract.md` and `runtime/workflow-20260521-dense-conflict.md`: action-time evidence and evaluation labels are separated, label join key is `(episode_key, candidate_id)`, and the fixed rule commits only when exactly one candidate has strong own-view identity evidence over cross-view and rival support.
- `rival_identity_pair_probe_v1` post-observation analyzer was implemented at `runtime/h001_runtime/analyze_rival_identity_post_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1` passes the diagnostic post-observation gate: request rows `6`, evidence rows `19`, commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- Fresh/predeclared validation source design selects `rival_identity_generalization_v1` from the frozen `dense_conflict_generalization_v1` primary action evidence. Design probe output `local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1` yields request rows `6`, request scenes `3`, request queries `2`, and no overlap with the previous diagnostic scenes.
- `rival_identity_generalization_v1` source miner was implemented with `runtime/h001_runtime/build_rival_identity_generalization_manifest.py`. Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1` freezes `manifests/h001_rival_identity_generalization_v1.json`; verify `manifests/h001_rival_identity_generalization_v1.verify.json` reports `ok true`, request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` planner smoke passed at `local_dataset/runs/h001_rival_identity_generalization_plan_v1`: request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_generalization_frames_v1`: rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity passed, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` detector/SAM2 substrate job completed at `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1`: detector rows `12`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `1.0`, associated candidate heading count `84`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Frozen post-observation analyzer on `rival_identity_generalization_v1` completed at `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1`: request/evidence/decision rows `6/12/6`, commit/success/wrong/no-label `4/2/2/0`, new primary success `2`, resolved rows `4`, and `uses_gt_for_action false`. The gate failed because two single-candidate `toilet` requests committed wrong goals.
- Failure diagnosis output `local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1` explains the failed fresh-source gate before any rule revision. Mechanism counts are `rival_identity_resolved_success 2`, `rival_identity_unresolved_cross_view_aliasing 2`, and `single_candidate_object_existence_false_positive 2`; `request_identity_no_guard_eligible_positive_candidates` mixes single-candidate object-existence false positives with multi-candidate rival-identity unresolved rows.
- Taxonomy split output `local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1` is Docker-verified. `request_taxonomy_route` separates `rival_identity_arbitration 4` from `object_existence_validation 2`; failure taxonomy counts are `none 2`, `rival_identity_unresolved_cross_view_aliasing 2`, and `object_existence_false_positive_commit 2`.
- Object-existence no-commit branch output `local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1` is Docker-verified. `request_taxonomy_route == object_existence_validation` now produces `defer_object_existence_validation`; fresh-source commit/success/wrong is `2/2/0`, defer-object-existence is `2`, and all gates pass. Regression output `local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1` preserves the prior diagnostic signal with commit/success/wrong `1/1/0`.
- Independent object-existence validation probe output `local_dataset/runs/h001_rival_identity_object_existence_probe_v1` is Docker-verified. Request rows `2`, naive unique-strong commit rows `2`, naive wrong-goal rows `2`, naive success rows `0`, wrong-goal avoided by defer `2`, success lost by defer `0`, action evidence forbidden key count `0`, and probe design gate `true`.
- Broader fresh-source validation design output `local_dataset/runs/h001_rival_identity_broader_validation_design_v1` is Docker-verified. Preferred source is `risk_validation`; selected parent rows are `72` across `10` scenes and `6` queries; estimated request rows are `22`; top wrong-goal rows are `41`; rows with correct and wrong candidates are `49`; design gate passed.
- `rival_identity_broader_validation_v1` source miner is implemented at `runtime/h001_runtime/build_rival_identity_broader_manifest.py`. Docker output `local_dataset/runs/h001_rival_identity_broader_source_v1` freezes `manifests/h001_rival_identity_broader_validation_v1.json`; verify `manifests/h001_rival_identity_broader_validation_v1.verify.json` reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` and `object_existence_validation 4`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- `rival_identity_broader_validation_v1` planner smoke passed at `local_dataset/runs/h001_rival_identity_broader_plan_v1`: request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, missing action rows `0`, candidate artifact rows/candidates `21/80`, plan gate `true`, and `uses_gt_for_action false`.
- `rival_identity_broader_validation_v1` frame export passed at `local_dataset/runs/h001_rival_identity_broader_frames_v1`: rows requested/exported `112/112`, rendered headings `862`, RGB/depth/metadata files `862/862/862`, unique scenes `10`, and `uses_gt_for_action false`. Strict no-blank-heading sanity found `56/862` blank RGB headings across `20` rows, but no all-blank rows; `nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl` keeps `112` rows and `806` headings with row-level nonblank gate `true`.
- The first broader detector launch at `local_dataset/runs/h001_rival_identity_broader_detector_substrate_v1` completed but is a path-root negative run: detector box, SAM2 mask, and candidate association rates are all `0.0` because the filtered summary under `nonblank_filter_v1` resolved `rendered_headings` paths relative to the filter directory instead of the original frame export root.
- Explicit detector `--frame-root` support was added to `runtime/h001_runtime/detect_postview_groundingdino_sam2.py` and `runtime/jobs/rival_identity_pair_probe_detector_substrate.sh`. Corrected output `local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2` passes the substrate gate: detector rows `112`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `0.6339`, rows with candidate association `71/112`, associated candidate heading count `442`, and `uses_gt_for_action false`.
- Broader post-observation analyzer output `local_dataset/runs/h001_rival_identity_broader_post_observation_v1` is safe but inert. It has request/evidence/decision rows `30/112/30`, commit/success/wrong/no-label `0/0/0/0`, object-existence defer `4`, unresolved identity defer `26`, failure taxonomy `post_observation_no_candidate_support 26` and `object_existence_deferred_no_independent_confirmation 4`, and post-observation gate `false`.
- Broader failure diagnostic output `local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1` is Docker-verified. It shows plan rows `112`, zero/near-standoff rows `112/112`, rotation fallback rows `112`, target distance min/mean/max `0.0/0.0/0.0`, own associated rows `0`, cross associated rows `442`, and mechanism counts `degenerate_zero_standoff_cross_association 22` / `degenerate_zero_standoff_no_visible_candidate 8`. The diagnostic gate sets `post_observation_rule_change_allowed false`.
- Zero-standoff-safe planner implementation is Docker-verified at `local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1`. The planner uses `--viewpoint-mode standoff`, reuses `NavmeshSnapper` and `plan_standoff_viewpoint`, and passes both plan and geometry gates: request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, scenes `10`, queries `6`, zero/near-standoff rows `0/0`, rotation/candidate fallback rows `0/0`, target distance min/mean/max `1.6386/1.7506/1.9747m`, viewpoint sources `standoff_navmesh 104` / `standoff_geometry 8`, and `uses_gt_for_action false`.
- Mixed standoff frame export `local_dataset/runs/h001_rival_identity_broader_frames_standoff_v1` exported `112/112` rows and `1079` headings, but row-level nonblank gate failed with `5` dropped rows. All dropped rows were `standoff_geometry` fallback with `standoff_navmesh_navigable false`.
- Navmesh-only standoff repair is Docker-verified at `local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1` and `local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1`. The planner uses `--require-navmesh-standoff`, keeps planned request rows `28/30`, plan rows `104`, scenes `9`, queries `6`, and skips `8` geometry fallback rows. Frame export keeps `104/104` rows and `997/997` headings after nonblank filtering with dropped/blank rows `0/0`; row-level and strict no-blank gates both pass.
- Broader navmesh-standoff detector/SAM2 substrate completed at `local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1`: detector rows `104`, detector box rate `0.9808`, SAM2 mask rate `0.9808`, candidate association rate `0.7212`, rows with association `75`, associated heading count `277`, and `uses_gt_for_action false`.
- Broader navmesh-standoff post-observation analyzer output `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1` fails the gate with request/evidence/decision rows `28/110/28`, commit/success/wrong/no-label `7/0/7/0`, defer unresolved identity `19`, defer object-existence `2`, and unsafe commit queries `bed 4`, `chair 2`, `tv_monitor 1`.
- Unsafe-commit diagnostic output `local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1` rejects threshold-only repair: simple guards based on semantic rank, detector box score, depth error, or own-view count alone still produce wrong commits, and the only safe combined simple guard is inert with `0` commits. The next rule must add candidate-set validity and local semantic/geometric consistency before detector-backed commit.
- Stricter arbitration design contract is frozen at `manifests/h001_rival_identity_strict_arbitration_v1.json`. It defines `rival_identity_goal_validity_arbitration_v1`, blocks single-feature threshold repairs, requires candidate-set validity / local semantic-geometric consistency / rival-contrast stages, and keeps `paper_claim_allowed false`.
- `goal_validity_arbitration_v1` is implemented in `runtime/h001_runtime/analyze_rival_identity_post_observation.py`. Default regression output `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_default_regression_v1` preserves the prior unsafe result `7/0/7/0`; strict objective output `local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1` passes the diagnostic gate with commit/success/wrong/no-label `2/2/0/0`, resolved rows `2`, and `uses_gt_for_action false`.
- Independent/predeclared source `rival_identity_goal_validity_independent_v1` is frozen from `v3_fresh_validation` after excluding prior diagnostic and broader diagnostic scenes. Design output `local_dataset/runs/h001_rival_identity_goal_validity_independent_design_v1` selects parent rows `72`, scenes `11`, queries `6`, top wrong-goal rows `51`, and correct+wrong candidate rows `59`. Source output `local_dataset/runs/h001_rival_identity_goal_validity_independent_source_v1` freezes manifest `manifests/h001_rival_identity_goal_validity_independent_v1.json`; verify `manifests/h001_rival_identity_goal_validity_independent_v1.verify.json` reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- Independent plan/frame/detector substrate is complete. Plan output `local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1` has request/planned/plan rows `30/30/92`; frame output has rows/headings `92/810`; nonblank gate has dropped rows `0`; detector output `local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1` passes with detector box/SAM2/candidate association `1.0/1.0/0.6196`.
- Independent `goal_validity_arbitration_v1` rerun output `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1` fails utility gate with commit/success/wrong/no-label `0/0/0/0`. Safety gates pass; success and resolved-request gates fail. Dominant reasons are `defer_low_goal_validity_cross_view_aliasing 12`, `post_observation_no_candidate_support 8`, and `object_existence_requires_independent_confirmation 6`.
- Default objective counterfactual on the same independent evidence is recorded at `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1`. It is nontrivial but unsafe with commit/success/wrong/no-label `7/4/3/0`; wrong-goal queries are `chair`, `sofa`, and `toilet`.
- Failure diagnostic `local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1` shows the strict-safe/inert vs default-nontrivial/unsafe tradeoff. Dominant tags are `cross_view_aliasing_blocks_goal_validity 14`, `planned_candidate_set_has_no_valid_goal 13`, `no_own_candidate_support 11`, `strong_identity_not_goal_validity 8`, and `object_existence_branch_blocks_commit 6`.
- Revision contract `manifests/h001_rival_identity_goal_validity_revision_v2.json` rejects `goal_validity_arbitration_v1` as a paper-facing utility rule and blocks threshold tuning from joined labels.
- Router `runtime/h001_runtime/route_goal_validity_revision_v2.py` is Docker-smoked. Output `local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1` routes all `30` requests without GT action inputs: `request_discriminative_rival_view 14`, `request_expanded_retrieval 8`, `request_object_existence_confirmation 6`, `request_goal_validity_confirmation 2`; terminal commits are blocked.
- Branch-specific planner contract `manifests/h001_discriminative_rival_view_planner_v1.json` is defined for the largest branch. It requires focus-rival pair selection, common pair or matched dual standoff views, explicit pair candidate ids, no GT/post-join action inputs, and separate plan/frame/detector/evaluation gates.
- Planner `runtime/h001_runtime/plan_discriminative_rival_view.py` is Docker-smoked. Output `local_dataset/runs/h001_discriminative_rival_view_plan_v1` passes with source router rows `14`, planned request rows `14`, plan rows `38`, common pair view rows `10`, matched dual standoff rows `28`, zero/near-standoff `0/0`, rotation fallback `0`, target distance min/mean/max `1.6344/1.9781/3.1546m`, and `uses_gt_for_action false`.
- Frame smoke on v1 exposed one blank `common_pair_geometry` row, so planner v2 requires navmesh-snapped common pair views. v2 plan output `local_dataset/runs/h001_discriminative_rival_view_plan_v2` has common pair navmesh rows `10` and matched dual standoff rows `28`.
- v2 frame/nonblank output `local_dataset/runs/h001_discriminative_rival_view_frames_v2` passes with rows/headings `38/222`, dropped rows `0`, removed blank headings `0`, row-level and strict no-blank gates `true`, role counts `common 10`, `focus 14`, `rival 14`, and `uses_gt_for_action false`.
- Initial detector/SAM2 substrate v1 passed the substrate gate but did not preserve pair-role metadata in detector associations. Detector/SAM2 substrate v2 completed at `local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2` with detector rows `38`, detector box/SAM2 `1.0/1.0`, candidate association `0.8158`, rows with association `31`, and role-preserved detector associations.
- `analyze_discriminative_rival_view_evidence.py` output `local_dataset/runs/h001_discriminative_rival_view_evidence_v1` fails the diagnostic gate: evidence availability `1.0`, disambiguation `0.6429`, actions `support_focus 8`, `support_rival 1`, `ambiguous_defer 5`, but single-correct pairs are all `rival_only_correct 3`, preferred-correct rate is `0.0`, and wrong-preference rate is `0.3333`.
- Failure diagnostic `local_dataset/runs/h001_discriminative_rival_view_failure_diagnostic_v1` blocks threshold tuning and fresh validation. Dominant tags are `symmetric_cross_view_leak 7`, `rival_visible_from_focus_view 6`, `identity_score_near_tie 5`, `common_view_supports_both_candidates 5`, `no_valid_goal_pair_but_disambiguated 4`, `both_correct_goal_region_or_duplicate_preferred 4`, and `rival_correct_own_view_evidence_weak 3`.
- Branch priority decision: handle `request_expanded_retrieval` before further discriminative-view tuning, because the current failure includes invalid/no-valid candidate pairs; discriminative views remain useful later as identity validation after retrieval expands the candidate set.
- Contract `manifests/h001_expanded_retrieval_branch_v1.json` is frozen before implementation. It uses router rows with `revision_action == request_expanded_retrieval`, expects `8` request rows, sets candidate budget `6-10`, forbids GT/evaluation labels for action, blocks terminal commit, and requires candidate-set validity gates before detector/objective work.
- Expanded-retrieval planner `runtime/h001_runtime/plan_expanded_retrieval_branch.py` is Docker-smoked. Output `local_dataset/runs/h001_expanded_retrieval_plan_v1` passes the planner gate with expected/request rows `8/8`, candidate-set rows `8`, plan rows `80`, expanded candidates per request `10`, skipped rows `0`, duplicate candidate rate `0.0`, nonfinite position rate `0.0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- Analysis-only candidate-set validity diagnostic `local_dataset/runs/h001_expanded_retrieval_candidate_set_validity_v1` passes the label join gate with missing labels `0`. It reports contains-correct rows/rate `6/8 = 0.75`, no-valid rows/rate `2/8 = 0.25`, source-top correct rows `1/8`, source-top wrong-goal rows `7/8`, wrong-top replacement rows/rate `5/7 = 0.7143`, and rows with wrong-goal candidate `7/8`. Full-pool comparison shows the two no-valid rows are `source_pool_no_valid_candidate`, not rank-band selection misses; taxonomy counts are `source_pool_no_valid_candidate 2`, `valid_set_with_wrong_goal_distractor 5`, and `valid_set_without_wrong_goal_distractor 1`.
- Analysis-only candidate-set guard design `local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1` passes the guard design gate. It routes `source_pool_no_valid_candidate 2` to `request_backend_retrieval_revision`, `valid_set_with_wrong_goal_distractor 5` to `request_detector_guarded_observation`, and `valid_set_without_wrong_goal_distractor 1` to `request_lightweight_confirmation`; detector evidence is allowed for `6/8`, terminal commit rows are `0`, `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false`.
- Non-GT proxy feature audit `local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1` passes feature extraction with forbidden action rows `0`, terminal commit rows `0`, and `uses_gt_for_action false`. Current candidate-set score/support features route all `8` rows to `request_detector_guarded_observation_proxy`; source-pool validity proxy recall is `0.0`, both backend target rows are escalated to evidence, and `proxy_ready_for_detector_gate false`.
- Non-GT source-pool validity proxy `local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1` passes the current diagnostic gate. It routes `2` rows to `request_backend_retrieval_revision_proxy` and `6` rows to `request_detector_guarded_observation_proxy`, with consumed forbidden rows `0`, source-pool validity proxy recall `1.0`, evidence-allowed target recall `1.0`, backend targets escalated to evidence `0`, evidence targets blocked as backend `0`, `proxy_ready_for_detector_gate true`, `uses_gt_for_action false`, and `paper_claim_allowed false`.
- Google Drive backup paths and no-Drive rebuild procedures are documented in `../../../docs/reproducibility.md`.
- Canonical local asset roots are `local_dataset/data`, `local_dataset/models`, and `local_dataset/runs`; `/tmp/research3-data`, `/tmp/research3-models`, and `/tmp/research3-runs` are compatibility symlinks.

### 에이전트 추론

The current method shape is more contribution-aligned than detector-based re-ranking because semantic uncertainty is being converted into active observation requests. It is still not paper-ready. The detector/association blocker is lifted for the selected primary and secondary diagnostic substrates and now also for the broader split. `rival_identity_confirmation_v1` supports the mechanism-level direction by turning saturated same-category evidence into identity-confirmation requests while preserving nonzero safe commits on diagnostic evidence. The accepted taxonomy split shows single-candidate false-positive object existence must be handled separately. The no-commit branch and object-existence probe are positive safety evidence. The zero-standoff geometry blocker is resolved at the planner substrate level, and the navmesh-only detector substrate now passes. The latest negative result is a safety-utility tradeoff: loose own-view identity evidence recovers successes but commits wrong goals, while `goal_validity_arbitration_v1` is safe but inert. `discriminative_rival_view_planner_v1` now passes plan, frame/nonblank, and detector/SAM2 substrate gates, but `discriminative_rival_view_evidence_v1` fails because the active view often still prefers the focus candidate when the rival is the only correct candidate. Failure taxonomy says the issue is cross-view leakage, common-view non-discrimination, weak rival own-view evidence, and invalid candidate pairs. The `request_expanded_retrieval` planner, label-join gate, guard design, proxy feature extraction, and source-pool validity proxy now pass. The next useful step is detector/viewpoint evidence acquisition for detector-eligible expanded-retrieval rows, while keeping terminal commit and paper claim blocked until a fresh/predeclared validation source is frozen.

## Pre-Schedule Verification Check

### 사실

- Date checked: 2026-05-08
- H001 hypothesis, first-probe metric thresholds, logging schema, non-GT candidate adapter, `VLMaps` artifact path, coordinate alignment policy, and real-world setup gate are documented.
- Non-GT semantic candidates have not yet been evaluated on Habitat ObjectNav full metrics.
- `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` comparisons have not yet been implemented as paper-facing evidence.
- Real-world robot / sensor / LiDAR / GT availability still needs user confirmation.

### 에이전트 추론

No additional literature review gate is required before continuing the 6-month to 1-year schedule. The active blocker is no longer basic dataset or candidate coverage; it is full follow-up detector/evidence validation for active observation requests.

### 사용자 판단 필요

- Decide whether real-world POC is part of the first paper or a follow-up result after simulation.
- Confirm available real-world robot, sensor, LiDAR, and GT setup before any hardware-specific workflow is created.

## Schedule Gate

### 사실

- Date checked: 2026-05-08
- Schedule document: `15_schedule.md`
- The 6-12 month plan is staged as P0 alignment, P1 semantic uncertainty calibration, P2 first probe, P3 robustness / HM3D-OVON extension, P4 Step 4-5 SLAM extension, P5 paper-facing consolidation, P6 real-world validation.

### 에이전트 추론

The schedule is still valid. The current execution point has moved past candidate-budget coverage recovery into active observation evidence validation.

## HM3D VLMaps Gate

### 사실

- Date checked: 2026-05-08
- Decision document: `08_runtime_integration.md`
- The selected path is controlled Habitat pre-exploration export, `alignment.json` emission from the same trajectory metadata, separate full `VLMaps` map-generation image, artifact export, alignment adapter, and Habitat navmesh verification.

## Non-GT Evaluator Smoke Gate

### 사실

- Date checked: 2026-05-08
- Fixed manifest rows were evaluated with an aligned non-GT `VLMaps` artifact.
- `GTTargetOracle` is now separated from `artifact_jsonl`.
- `artifact_jsonl` records `candidate_backend_uses_gt_for_action = false`.

### 에이전트 추론

The interface gate passed, but sparse smoke artifacts are not paper-facing ObjectNav evidence.

## Candidate Coverage Gate

### 사실

- Date checked: 2026-05-08
- Coverage document: `04_first_experiment.md`
- Early non-GT artifacts exposed reachability and distractor coverage as the main blocker.

### 에이전트 추론

This is now a historical gate. Later `risk_validation_v1` and `v3_fresh_validation_v1` coverage gates pass; current work should not return to policy threshold tuning.

## Active Re-observation Gate

### 사실

- Date checked: 2026-05-08
- Policy document: `04_first_experiment.md`
- `SemanticOnly` was implemented in `run_smoke.py`.
- `SemanticOnly` uses `U_sem >= 0.60` and a semantic tie band of `0.01`.
- Action selection does not use GT candidate labels or GT target ids.

### 에이전트 추론

The active re-observation mechanism is implemented and smoke-tested. Larger interpretation waits for calibration coverage.

## Calibration Coverage Gate

### 사실

- Date checked: 2026-05-09
- Coverage document: `04_first_experiment.md`
- `random128_v1` artifact is structurally valid but failed the reachable correct-and-wrong ambiguity gate.
- `random256_v1` artifact is structurally valid but also failed the reachable correct-and-wrong ambiguity gate on 2026-05-10.
- `random256_v1` reachable correct-and-wrong ambiguity rate: `0.26`, required `>= 0.50`.
- Decision note in `04_first_experiment.md` selects candidate-budget recovery before scene replacement or backend revision.

### 에이전트 추론

The failure is coverage-side rather than basic evaluator-side. `SemanticOnly` policy comparison remains blocked.

## Coverage Recovery Gate

### 사실

- Last completed recovery artifact: `random256_v1`
- `random256_v1` status: completed, structurally valid, hard ambiguity coverage failed.
- Historical recovery contract: `random256_k10_v1` in `08_runtime_integration.md`
- Historical output root: `/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1`
- Historical job status file: `/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/job_status.json`
- `random256_k10_v1` launch status: completed
- `random256_k10_v1` session: `h001-calib-artifacts-random256-k10-20260510-165427`
- `random256_k10_v1` log: `runtime/logs/calibration-artifacts-random256-k10-20260510-165427.log`
- `random256_k10_v1` candidate count: `300`
- `random256_k10_v1` hard coverage status: failed, reachable correct-and-wrong rate `0.48`
- `random256_k10_v1` diagnostic policy status: completed, `SemanticOnly` did not reduce wrong-goal visits
- second recovery decision: scene replacement first; policy objective revision as parallel design; reachability-diverse backend deferred
- scene replacement contract: `random256_k10_sr1_v1`, manifest `manifests/h001_splits_sr1.json`, scene specs `manifests/sr1_scenes.txt`
- scene replacement launch status: completed and structurally verified, session `h001-calib-artifacts-random256-k10-sr1-20260511-115330`
- scene replacement coverage gate: passed, reachable correct-and-wrong rate `0.66`
- recovered-substrate policy comparison: completed, current `SemanticOnly` still worsens wrong-goal visit rate `0.54` vs `NoReobserve` `0.38`
- policy objective revision design: `SemanticVerifyTop` and `EvidenceGatedSemanticOnly` in `04_first_experiment.md`
- policy objective revision implementation contract: `08_runtime_integration.md`
- `SemanticVerifyTop` implementation smoke: passed, final candidate switch rate `0.0`
- `EvidenceGatedSemanticOnly` support_proxy run: completed, wrong-goal `0.38`, switch gate pass rate `0.0`
- post-view visual-language re-scoring contract: `08_runtime_integration.md`, target mode `image_feature`
- `export_postview_frames.py` smoke: passed, 2 post-view frames exported
- Coverage recovery decision tree: `04_first_experiment.md`

### 에이전트 추론

After completion, run structural verification and coverage sanity. Do not run calibration policy comparison until coverage passes.

## OpenVocab Detector Gate

### 사실

- Date checked: 2026-05-13
- Separate perception image: `research3/openvocab-perception:20260513-owlvit`
- `google/owlvit-base-patch32` offline load passed with `OwlViTProcessor` and `OwlViTForObjectDetection`.
- `v3b_owlvit_box` 2-row Docker smoke was implemented in `runtime/h001_runtime/detect_postview_owlvit_box.py`.
- Best tiny-smoke setting: query template `a photo of a {query}`, threshold `0.01`, point field `position`.
- Best tiny-smoke result: detector box row rate `1.00`, candidate association row rate `0.50`.
- `visit_position` setting reduced candidate association to `0.00`.

### 에이전트 추론

`OWL-ViT` box-only evidence remains useful as a feasibility check but should not be promoted to full calibration. The active detector substrate is `GroundingDINO + SAM2`; the current bottleneck is whether follow-up observations produce strong enough object-node evidence for safe commit/defer decisions.
