# 연구 보고서: Semantic Uncertainty 기반 Active SLAM/Navigation Utility

## 0. 최신 상태

### 사실

- Date checked: 2026-05-23
- `risk_validation_v1` candidate substrate와 `v3_fresh_validation_v1` candidate substrate는 모두 coverage gate를 통과했다.
- `risk_validation_v1` coverage: reachable correct-and-wrong rate `0.54`, `NoReobserve` wrong-goal visit rate `0.47`, `Success Rate 0.19`, `SPL 0.1004`.
- `v3_fresh_validation_v1` coverage: reachable correct-and-wrong rate `0.69`, `NoReobserve` wrong-goal visit rate `0.61`, `Success Rate 0.26`, `SPL 0.1459`.
- Full follow-up detector/evidence validation exposed unsafe V1 commits, so the follow-up objective was revised through V2/V3 safety repairs.
- Explicit frame `candidate_ids` are now respected by `detect_postview_groundingdino_sam2.py`; held-out follow-up detector association recovered correct-candidate availability from `1/5` to `3/5`.
- Identity ambiguity diagnostic showed that threshold-only relaxation is unsafe: `best_strong_score` would commit wrong-goal `4/5`.
- `selected_local_cluster_margin` was implemented as fixed follow-up evidence V4 in `analyze_external_candidate_followup_evidence.py`.
- V4 on the explicit-candidate held-out diagnostic passed the local full gate: commit/success/wrong/no-valid `1/1/0/0`.
- V4 on separate `v3_fresh_validation_v1` passed safety but failed utility: commit/success/wrong/no-valid `0/0/0/0`, with `request_identity_confirmation 6/7`.
- V4 request-identity bottleneck diagnostic shows direct selected commit is unsafe: commit/success/wrong `6/3/3`.
- Existing second-stage identity objective V2 recovers nonzero safe utility on the same V4 separate split substrate: commit/success/wrong `2/2/0`.
- V4 + second-stage identity V2 terminal diagnostic passes the local integrated full gate with terminal commit/success/wrong/no-valid `2/2/0/0`, but remains blocked for `first_eval` because the scope is `v4_fixed_terminal_diagnostic`.
- Selected-wrong `plant` recovery design shows the current stage2 target rule misses the correct candidate: follow-up set contains correct `3/3`, current stage2 context contains correct `3/3`, current stage2 targets correct `0/3`, and semantic-neighbor target rule would target correct `3/3` with feasible standoff viewpoints.
- Second-stage identity planner now supports `--target-selection-mode semantic_neighbor`; schema/frame smoke produced `15` plan rows and `15` frame rows, with `semantic_neighbor_1_standoff` rows targeting `plant` candidate `spatial_nms:1` and all frame rows using `explicit_candidate_ids`.
- Detector-backed semantic-neighbor validation completed. The first GPU attempt failed at `second_stage_detector` due CUDA OOM while unrelated GPU processes occupied memory; the reduced CPU retry completed with detector rows `15`, candidate association `0.80`, and integrated commit/success/wrong/no-valid `2/2/0/0`.
- Full GPU rerun `v4_semantic_neighbor_stage2_gpu_rerun_v1` completed with detector rows `15`, candidate association `1.00`, stage2 request coverage `6/6`, integrated commit/success/wrong/no-valid `2/2/0/0`, and wrong-goal/no-valid/visit-position-only commit `0`.
- Full GPU rerun remains diagnostic only: `validation_scope v4_semantic_neighbor_diagnostic`, `local_integrated_gate_passed true`, `utility_proof_passed false`, `first_eval_rerun_blocked true`, `policy_scale_comparison_blocked true`.
- Remaining semantic-neighbor terminal reasons are `request_further_identity_confirmation_strong_rival_supported 3`, `request_further_identity_confirmation_selected_not_strong_in_own_view 1`, and `defer_identity_selected_local_cluster_too_small 1`.
- Row-level diagnosis of selected-wrong `plant` rows shows the correct semantic-neighbor candidate is present but weak: `spatial_nms:1` has `S_ext ~0.483` and strong depth `false`, while wrong selected/rival candidates have `S_ext ~0.783/0.784` and strong depth `true`.
- Semantic-neighbor multiview acquisition revision was implemented. Focused Docker plan smoke for selected-wrong `plant` branches `external_candidate:14,17,21` produced `24` plan rows with `18` semantic-neighbor standoff rows and `0` skipped rows; frame smoke exported `24/24` rows and `312` headings.
- Focused detector-backed multiview job `h001-v4-sem-neighbor-multiview-20260520-235618` completed. Detector rows `24`, candidate association `0.875`, detector box/SAM2 mask `1.0`.
- Multiview improved correct semantic-neighbor evidence: selected-wrong `plant` rows now have correct `spatial_nms:1` at `S_ext ~0.783`, strong depth `true`, own strict association `13`. However wrong selected/rival candidates remain strong at `S_ext ~0.786`, so objective V2 still returns `request_further_identity_confirmation 3/3`.
- Semantic-prior strong-tie arbitration objective V3 was implemented in `analyze_external_candidate_second_stage_identity_evidence.py`. On the focused selected-wrong multiview rows, it commits the semantic-neighbor candidate on `3/3` branches with success/wrong/no-valid `3/0/0`; source selected candidate is wrong `spatial_nms:0`, committed candidate is correct `spatial_nms:1`.
- Integrated focused V3 summary is safety-positive but not a utility proof: terminal commit/success/wrong/no-valid `3/3/0/0`, stage2 request coverage `3/6`, `passes_integrated_stage2_coverage false`, `utility_proof_passed false`.
- Full V4 semantic-neighbor multiview objective V3 coverage validation completed in tmux `h001-v4-sem-neighbor-v3-full-20260521-004207`. It covered all `6/6` V4 identity-request rows, exported `45` second-stage frames, detector association rate `0.80`, detector box/SAM2 mask rate `1.0`.
- Full V4 V3 integrated diagnostic passed the local integrated full gate: terminal commit/success/wrong/no-valid `5/5/0/0`, stage2 coverage `6/6`, terminal actions `commit_arbitrated_candidate 3`, `commit_selected_candidate 2`, `request_further_identity_confirmation 1`, `followup_defer 1`. `utility_proof_passed` remains false because `validation_scope` is diagnostic.
- Scene-disjoint held-out V3 validation contract was defined. Existing held-out V4 artifact has no `request_identity_confirmation` rows: `commit_selected_candidate 1`, `defer 4`. The proposed held-out route is to send only `defer_identity_selected_local_rival_stronger` sofa rows (`2`, correct candidate present) to second-stage V3, keep outside-cluster near-tie chair rows (`2`, no correct candidate) as broader retrieval/backend failures, and compare against current held-out V4 baseline commit/success/wrong/no-valid `1/1/0/0`.
- Held-out follow-up objective V5 was implemented. It routes only local-rival-stronger identity ambiguity to `request_identity_confirmation`; Docker output has action counts `commit_selected 1`, `request_identity 2`, `defer 2`, safety gate pass, and `uses_gt_for_action false`.
- Held-out V5 plus second-stage V3 validation completed after recovering the integrated summary with `validation_scope heldout_validation`. Result: stage2 request coverage `2/2`, stage2 actions `request_further_identity_confirmation 2`, terminal commit/success/wrong/no-valid `1/1/0/0`, integrated full gate `false`, utility proof `false`.
- Held-out sofa failure diagnosis: correct sofa candidates are present, but semantic-neighbor correct candidate remains weak (`S_ext ~0.501`, own strong `false`) while wrong selected/rival candidates stay strong (`S_ext ~0.799/0.805`). This does not improve over the held-out V4 baseline.
- Held-out sofa second-stage failure diagnostic was added. Output `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/heldout_sofa_stage2_failure_diagnostic_v1` shows both held-out sofa rows share the same failure modes: `correct_target_not_strong_in_own_view`, `viewpoint_geometry_correct_target_out_of_fov_or_behind`, `target_selection_left_stronger_correct_candidate_as_context`, and `wrong_selected_or_rival_remains_strong`.
- Held-out local-rival target expansion and grounded geometry were implemented. `local_rival_expanded` now targets selected, semantic-neighbor, rival, and local-context candidates; `grounded_position` normalizes candidate points when semantic-map `position.y` and navigable `visit_position.y` disagree by more than `2.0m`. Projection-only Docker smoke improved the held-out sofa second-stage target visible rate from `4/16 = 0.25` to `20/22 = 0.909`, and now actively targets the previously untargeted stronger correct context `vlmaps:export:sofa:spatial_nms:9`.
- Held-out local-rival expanded grounded detector validation completed. Detector box/SAM2/candidate association rates are all `1.0`, so the visibility/association substrate recovered. However stage2 still returns `request_further_identity_confirmation 2/2`, terminal commit/success/wrong/no-valid remains `1/1/0/0`, and utility proof remains false.
- Local-rival grounded diagnostic shows the remaining blocker is terminal arbitration under score saturation: `correct_evidence_recovered 2`, `correct_local_context_tied_but_not_arbitrated 2`, `score_saturation_multiple_strong_candidates 2`, `selected_wrong_remains_strong 2`, `wrong_rivals_remain_strong 2`.
- Local-context arbitration design was added and Docker-smoked. On the two detector-saturated held-out sofa rows, current V3 commits `0/2`, selected-direct would be unsafe with wrong-goal `2/2`, while the non-GT `local_context_unique_own_view_advantage` rule commits the local-context candidate on `2/2` rows with success/wrong/no-valid `2/0/0`.
- Local-context arbitration objective V4 was implemented and replayed on the held-out sofa route. Stage2 commits `2/2` with success/wrong/no-valid `2/0/0`; integrated terminal commit/success/wrong/no-valid is `3/3/0/0`, with integrated detector substrate, safety, and full gates passing on this local held-out contract.
- Broader retrieval/backend design for the two no-correct chair rows completed. Current follow-up set, V4 external set, and `artifact_semantic_top20` all miss the correct target on both rows. This is a backend recall failure, not a detector association or identity-confirmation failure.
- Available-artifact dense backend recall probe was implemented. Existing materialized non-GT artifacts `replacement_spatial_p97_k20`, `first_eval_spatial_p97_k20`, `first_eval_spatial_k20`, `first_eval_random256_k20`, and `first_eval_random256_k10` all recover `0/2` no-correct chair rows.
- Dense VLMaps source-map re-export recall job `h001-dense-backend-y9h-chair-20260521-030146` completed. Output `/tmp/research3-runs/h001_dense_backend_recall_y9h_chair_v1` recovered both no-correct chair rows with all four dense variants. `spatial_nms_p95_k100_d10` recovered `2/2` rows with recall@5 `1.0` using `100` candidates, while `spatial_nms_p90_k200_d5`, `components_p90_min1_k200`, and `components_p80_min1_k200` also recovered `2/2` but use `200` candidates.
- Fixed dense backend artifact was materialized at `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/all_scenes_aligned.jsonl`. Docker verification recovered `2/2` no-correct chair rows with recall@5 `1.0`, candidate count `100`, and `uses_gt_for_action false`.
- Fixed dense backend detector observation job `h001-dense-fixed-detector-y9h-chair-20260521-031417` completed. It triggered `2` held-out chair rows, produced `12` plan/frame rows and `36` rendered headings, and kept `uses_gt_for_action false`. `GroundingDINO + SAM2` produced detector box/SAM2 mask rates `1.0`, but candidate association rate was `0.0`; evidence action remained `external_evidence_v1_defer 2`, safety gate passed, and full gate failed.
- Detector association diagnostic was added and Docker-run at `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_v1/detector_association_diagnostic_v1`. It reports `36` association rows, `20` visible projections, `12` inside-mask projections, `12` visible-inside-mask-but-unassociated rows, `18` depth-mismatch rows, and median depth error `3.94m`; dominant failure is `visible_inside_mask_but_depth_or_association_rejects`.
- Dense association repair design was added and Docker-run at `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_v1/dense_association_repair_design_v1`. The first variant that recovers both held-out chair episodes, passes association-rate gate `0.20`, and supports no wrong candidate under GT analysis labels is `mask_depth_2_0`.
- Detector association repair job with `association_depth_tolerance_m=2.0` completed in tmux `h001-dense-fixed-detector-depth2-y9h-chair-20260521-034718`. Output `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1` has detector box/SAM2 mask rates `1.0`, candidate association rate `0.5`, and detector substrate gate pass. Existing evidence analyzer commits `2/2`, but its built-in safety/full gate fails because dense candidate correctness labels are not attached to branch rows.
- Depth2 dense repair commit evaluation was added at `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_repair_commit_evaluation_v1`. Post-hoc recall-label analysis shows action commits `2/2`, success commits `2/2`, wrong-goal commits `0/2`, with `uses_gt_for_action false` and `uses_gt_for_analysis true`.
- Fixed dense backend terminal diagnostic contract was added to `07_evaluation_contract.md`. The depth2 result is now explicitly limited to a local two-row chair diagnostic; `first_eval`, policy-scale, and cross-scene/category `association_depth_tolerance_m=2.0` claims remain blocked.
- `association_depth_tolerance_m=2.0` generalization decision was recorded: do not generalize it beyond the two chair rows yet. Broader 100-row association-variant evidence shows relaxed depth matching improves coverage but does not make association count reliable and introduces new wrong-goal risk.
- Dense terminal arbitration diagnostic was added at `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_terminal_arbitration_diagnostic_v1`. It shows commits `2/2`, selected post-hoc correct `1.0`, first external post-hoc correct `1.0`, selected-correct improvement over first `0.0`, wrong positive-support row rate `0.0`, and same-goal evidence selection rate `1.0`.
- Independent dense conflict validation was designed in `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md`. Primary target rows are six `v3_fresh_validation_v1` rows across `DYehNKdT76V`, `HY1NcmCgn3n`, and `7MXmsvcQjpJ`; all have correct and wrong positive-support candidates. The previous `y9hTuugGdiq/chair` dense rows are excluded from promotion and kept only as regression sanity checks.
- `h001_dense_conflict_v1` manifest and recall gate were implemented. Manifest verify passed with `8` rows and `8` unique episode keys. Final canonical recall on the existing selected `v3_fresh_spatial_p97_k20` primary substrate passed with `6/6` rows containing a correct candidate and recall@20 `1.0`.
- Frozen-row `spatial_nms_p95_k100_d10` dense artifact job wrapper was added at `runtime/jobs/dense_conflict_candidate_artifact.sh`, with scene spec `manifests/dense_conflict_v1_scenes.txt`. First launch `h001-dense-conflict-artifact-20260521-175656` failed immediately at Docker GPU init because host `nvidia-smi` reports driver/library mismatch: kernel module `580.126.09`, user-space library `580.159.03`. No final dense artifact was produced.
- Host/Docker NVIDIA runtime recovered on 2026-05-23: host `nvidia-smi`, kernel module, `nvidia-persistenced`, and Docker `--gpus all` smoke all passed.
- Default dense artifact resume `h001-dense-conflict-artifact-20260523-140640` failed because `/tmp/research3-data` was a stale empty directory rather than the expected compatibility symlink.
- Canonical `spatial_nms_p95_k100_d10` job completed but failed the final recall gate: primary rows with correct candidate `3/6`, recall@20 `0.5`, required rows with correct `4/6`; detector/association validation remains blocked for this re-export substrate.
- Revised `spatial_nms_p90_k200_d5` dense candidate job completed with `24` rows, `4800` candidates, and `4241` finite-position candidates, but also failed the final recall gate: primary rows with correct candidate `3/6`, recall@20 `0.5`, required rows with correct `4/6`. Lower threshold, larger candidate budget, and tighter NMS did not recover the missed `7MXmsvcQjpJ/plant` primary rows.
- Dense conflict detector/association validation was materialized from the existing `v3_fresh` second-stage evidence with `runtime/h001_runtime/analyze_dense_conflict_validation.py`. Output `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1` passes the primary diagnostic gate: detector box `1.0`, SAM2 mask `1.0`, candidate association `0.8`, rows with correct+wrong positive support `6/6`, commit/success/wrong/no-valid `5/5/0/0`, selected-correct improvement over source-selected `3`, and `uses_gt_for_action false`.
- Secondary-stress held-out `sofa` validation also passed. Recall output `local_dataset/runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1` has recall rows with correct `2/2` and recall@20 `1.0`; validation output `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1` has detector box/SAM2/candidate association `1.0/1.0/1.0`, commit/success/wrong/no-valid `2/2/0/0`, selected-correct improvement over source-selected `2`, and `uses_gt_for_action false`.
- Broader dense-conflict generalization design was added with `runtime/h001_runtime/design_dense_conflict_generalization.py`. Docker output `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json` summarizes current evidence as `10` rows, `5` scenes, `3` queries, `8` rows with correct+wrong positive support, `5` source-selected-wrong rows, and wrong-goal commits `0`. It selects `scene_disjoint_first_eval_style` as the next path and requires a frozen `dense_conflict_generalization_v1` manifest with at least `20` rows, `5` scenes, `3` queries, `6` selected-wrong rows, and `12` correct+wrong positive-support rows.
- `dense_conflict_generalization_v1` was frozen with `runtime/h001_runtime/build_dense_conflict_generalization_manifest.py`. Manifest `manifests/h001_dense_conflict_generalization_v1.json` has `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`, and `uses_gt_for_action false`.
- Generalization recall gate passed at `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1`: rows with correct `20/20`, recall@20 `1.0`, recall@5 `0.85`, first correct rank `1-9`, so detector substrate validation is allowed for this frozen split.
- Detector substrate job for `dense_conflict_generalization_v1` completed in tmux `h001-dense-conflict-generalization-detector-20260523-170533`. Output `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1/generalization_detector_substrate_summary.json` reports detector rows `20`, frame rows `20`, rendered headings `125`, detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`, associated rows `7`, substrate gate pass, and `uses_gt_for_action false`. The policy diagnostic on this hard split has success `0.2` and wrong-goal visit `0.8`.
- Terminal evidence extraction was implemented with `runtime/h001_runtime/extract_dense_conflict_generalization_evidence.py`. Output `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1` separates `action_evidence_rows.jsonl` from `evaluation_labels.jsonl`; action evidence rows `20`, label rows `55`, associated/unassociated rows `7/13`, forbidden action key count `0`, and `uses_gt_for_action false`.
- Terminal policy design diagnostic is a negative result for current v0 rules. `semantic_top_if_supported` and `first_associated` commit `7/20` but produce `6` wrong-goal commits. `support_score_best` and `proposed_conservative_v0` commit `7/20` with `3` success and `4` wrong-goal commits. Therefore terminal validation should not be promoted until a stricter arbitration guard is designed.
- Terminal guard design was implemented with `runtime/h001_runtime/design_dense_conflict_terminal_guard.py`. Docker output `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1` selects `strict_depth_consistency_v1`: `max_depth_error_m 0.33`, `min_associated_heading_count 2`, `min_mask_hit_count 2`, `max_semantic_rank 5`; same diagnostic split commit/success/wrong `3/3/0`, associated commit rate `3/7`, and `uses_gt_for_action false`. This is a fixed-rule validation candidate, not a paper claim.
- Frozen guard config and fixed-rule validation were added. `manifests/h001_dense_conflict_terminal_guard_v1.json` freezes `strict_depth_consistency_v1`; `runtime/h001_runtime/validate_dense_conflict_terminal_arbitration.py` writes action decisions before evaluation labels are joined. Docker output `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1` has forbidden action key count `0`, stable metric match design `true`, local fixed-rule validation pass `true`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`, and `uses_gt_for_action false`.
- Independent terminal validation contract was frozen at `manifests/h001_dense_conflict_terminal_independent_v1.json`. Primary source is `dense_conflict_v1_v3_fresh_primary`; profile output `local_dataset/runs/h001_dense_conflict_independent_terminal_evidence_profile_v1` has rows `6`, associated rows `6`, scenes `3`, queries `2`, forbidden action key count `0`, and naive `support_score_best` success/wrong `2/4`. Secondary stress source `local_dataset/runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1` has rows `2`, associated rows `2`, and naive success/wrong `0/2`.
- Independent terminal validation was run without changing guard thresholds. Primary output `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1` failed the gate with commit/success/wrong `6/2/4`, no-label commits `0`, forbidden action key count `0`, and `uses_gt_for_action false`. Secondary stress output `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1` also failed with commit/success/wrong `2/0/2`. The failure taxonomy is `guard_wrong_commit_depth_consistent_wrong_instance = 4` for primary and `stress_slice_wrong_commit = 2` for secondary.
- Failure diagnosis was added at `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1`. Wrong rows `6` are dominated by saturated same-category rival ambiguity: `repeated_wrong_instance_selected_by_saturated_support 5`, `guard_cannot_arbitrate_between_eligible_correct_and_wrong 1`; correct candidates are present in all wrong rows, wrong candidates pass the frozen guard in all wrong rows, and support scores are saturated in all wrong rows. The next design contract is `rival_identity_confirmation_v1`.
- `rival_identity_confirmation_v1` diagnostic policy was implemented with `runtime/h001_runtime/analyze_dense_conflict_rival_identity_policy.py`. Docker output `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1` passes the local diagnostic gate: commit/success/wrong `2/2/0`, request identity rows `6`, forbidden action key count `0`, and `uses_gt_for_action false`. Simpler alternatives fail in the expected ways: support/depth/semantic-top commit policies keep `6` wrong-goal commits, while `defer_all_ambiguous` is safe but inert with `0` success commits.
- Active observation/evaluation contract was frozen at `manifests/h001_rival_identity_observation_v1.json`. It fixes six `request_rival_identity_confirmation` rows, planner `rival_identity_pair_probe_v1`, non-GT focus/rival observation inputs, detector substrate gates `box/SAM2/association >= 0.80/0.80/0.50`, and post-observation gates requiring wrong-goal `0`, no-label `0`, newly resolved primary request `>=1`, and secondary stress wrong-goal `0`.
- `rival_identity_pair_probe_v1` observation planner was implemented with `runtime/h001_runtime/plan_rival_identity_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1` passes the plan smoke gate: request rows `6`, planned request rows `6`, plan rows `19`, skipped rows `0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- `rival_identity_pair_probe_v1` frame export smoke was run with `runtime/h001_runtime/export_postview_frames_v2.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1` passes renderability checks: rows requested/exported `19/19`, rendered headings `142`, RGB/depth files `142/142`, unique scenes `3`, nonblank RGB sanity passed, and `uses_gt_for_action false`. The first non-GPU attempt failed at Habitat EGL context creation; rerun with `--gpus all` passed.
- `rival_identity_pair_probe_v1` detector substrate job completed at `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1`. Summary `rival_identity_detector_substrate_summary.json` reports detector rows `19`, detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, rows with candidate association `12/19`, associated candidate heading count `57`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Post-observation evidence/validation contract was frozen in `07_evaluation_contract.md` and `runtime/workflow-20260521-dense-conflict.md`. It separates action-time evidence from evaluation labels, fixes label join to `(episode_key, candidate_id)`, computes own-view versus cross-view detector association, and allows `commit_candidate` only when exactly one candidate has strong own-view identity evidence. Otherwise the rule must `defer_unresolved_identity`; no semantic-top fallback or category-specific branch is allowed.
- `rival_identity_pair_probe_v1` post-observation analyzer was implemented with `runtime/h001_runtime/analyze_rival_identity_post_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1` passes the diagnostic gate: request rows `6`, evidence rows `19`, decision rows `6`, commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Failure taxonomy is `none 1`, `post_observation_no_candidate_support 3`, and `post_observation_cross_view_aliasing 2`.
- Fresh/predeclared validation source design selected `rival_identity_generalization_v1` from frozen `dense_conflict_generalization_v1` primary action evidence. Design probe output `local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1` shows parent rows `20`, parent scenes `9`, parent queries `6`, and selected request rows `6` across scenes `5cdEh9F2hJL`, `CrMo8WxCyVb`, `mL8ThkuaVTM` and queries `bed`, `toilet`. Previous diagnostic scenes `DYehNKdT76V`, `7MXmsvcQjpJ`, and `y9hTuugGdiq` are excluded.
- `rival_identity_generalization_v1` source miner was implemented with `runtime/h001_runtime/build_rival_identity_generalization_manifest.py`. Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1` freezes `manifests/h001_rival_identity_generalization_v1.json`; verify `manifests/h001_rival_identity_generalization_v1.verify.json` reports `ok true`, request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` planner smoke passed at `local_dataset/runs/h001_rival_identity_generalization_plan_v1`: request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_generalization_frames_v1`: rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity passed, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` detector/SAM2 substrate job completed at `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1`: detector rows `12`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `1.0`, associated candidate heading count `84`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Frozen post-observation analyzer on `rival_identity_generalization_v1` completed at `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1`: request/evidence/decision rows `6/12/6`, commit/success/wrong/no-label `4/2/2/0`, new primary success `2`, resolved rows `4`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. The fresh-source post-observation gate failed because two single-candidate `toilet` requests committed false-positive object candidates as wrong goals.
- Cross-machine reproducibility check was updated in `docs/reproducibility.md`. `git check-ignore -v` did not flag essential source-of-truth files such as `AGENTS.md`, `README.md`, `TODO.md`, `summary.md`, `docs/reproducibility.md`, H001 manifests, Dockerfiles, runtime scripts, or job scripts. Data, runs, models, checkpoints, paper PDFs, large archives, and secrets remain intentionally local-only.
- Ignored local assets were classified in `docs/reproducibility.md`: `local_dataset/data`, `local_dataset/models`, main Docker images, and key `local_dataset/runs` evidence snapshots are Drive preservation candidates; datasets, checkpoints, Docker images, candidate artifacts, detector artifacts, and logs are regenerable through documented commands; credentials, exact historical GPU detector outputs, manual local-only annotations, and paywalled/annotated PDFs are non-regenerable or risky unless managed separately.
- Google Drive backup paths were made explicit in `docs/reproducibility.md`: preserve `local_dataset/data/versioned_data/hm3d-0.2/hm3d`, `local_dataset/data/datasets/objectnav/hm3d/v2/objectnav_hm3d_v2`, `GroundingDINO + SAM2`, `VLMaps / LSeg`, `CLIP`, key H001 evidence snapshots, and optional Docker image archive.
- Drive restore and no-Drive rebuild procedures were added in `docs/reproducibility.md`; failed p95/p90 dense conflict re-export artifacts are excluded from high-priority backup, while the selected `v3_fresh` dense conflict recall/validation outputs are Drive preservation candidates.
- Local dataset migration completed. Canonical local paths are now `local_dataset/data`, `local_dataset/models`, and `local_dataset/runs`; `/tmp/research3-data`, `/tmp/research3-models`, and `/tmp/research3-runs` remain as compatibility symlinks.
- Migration verification passed: `du -sh` reports `42G`, `5.8G`, and `3.6G`; `.gitignore` excludes `local_dataset/`; Docker `check_hm3d.py`, `/runs` mount smoke, and `/models` mount smoke all passed through the `/tmp` symlink paths.
- Duplicate-goal/category-region handling is separated from the main ObjectNav GT contract. The `both_candidates_correct` chair row is not counted as a main utility recovery unless a separate goal-region metric is defined.
- Reproducibility entrypoint was added at `docs/reproducibility.md`.

### 에이전트 추론

현재 가장 유망한 novelty 방향은 detector/segmenter를 붙이는 것이 아니라, semantic uncertainty를 `commit/defer` threshold에서 `request_identity_confirmation`, `request_expanded_retrieval`, semantic-prior arbitration, local-context arbitration 같은 active SLAM/navigation utility로 변환하는 것이다. 아직 paper claim은 확정하지 않는다. V3 full V4 diagnostic은 selected-wrong `plant` failure를 복구했고, scene-disjoint held-out `sofa` local-rival ambiguity에서는 target expansion + grounded geometry가 projection substrate를 회복했다. V4 local-context objective는 score-saturated repeated-object case에서 selected-direct가 위험하고 own-view local-context evidence가 더 안전한 arbitration signal일 수 있음을 보였다. no-correct chair rows는 dense backend로 candidate recall이 회복되었고, depth2 association repair에서는 detector-backed commit도 post-hoc GT analysis 기준으로 `2/2` 성공했다. 다만 terminal arbitration은 same-goal correct cluster 안에서 evidence-rank가 더 강한 후보를 고른 것이므로 wrong-goal repair utility proof는 아니다. `association_depth_tolerance_m=2.0`는 전역 default로 일반화하지 않는다. p95/p90 dense re-export는 final dense recall gate를 통과하지 못했지만, selected `v3_fresh_spatial_p97_k20` primary diagnostic과 held-out `sofa` secondary stress diagnostic은 recall과 detector/association gate를 통과했다. 이제 `scene_disjoint_first_eval_style` broader split도 후보 recall과 detector substrate는 통과했고 action/evaluation evidence separation도 통과했다. v0 terminal arbitration은 wrong-goal commit을 만들었고, frozen `strict_depth_consistency_v1`은 same-split에서만 commit/success/wrong `3/3/0`을 재현했다. Independent validation은 이 guard를 reject했고, failure diagnosis는 dense same-category positive support를 identity ambiguity로 봐야 한다는 근거를 만들었다. `rival_identity_confirmation_v1`은 이 ambiguity를 active request로 바꾸는 diagnostic에서는 성공했다. Fresh-source frame과 detector/SAM2 substrate도 통과했지만, frozen post-observation analyzer는 single-candidate `toilet` false positive를 strong identity evidence로 오인해 wrong-goal commit `2`를 만들었다. 다음 판단 지점은 failure taxonomy를 `rival identity ambiguity`와 `object-existence false positive`로 분리할지 여부다. 다른 컴퓨터 재현은 GitHub repo plus `docs/reproducibility.md`의 Drive backup/restore 또는 no-Drive rebuild 절차를 따른다.

## 1. 연구 관심 배경

### 사실

본 연구는 AI robot이 새 환경에서 perception, mobility, SLAM, navigation을 결합해 적응하는 문제를 다룬다. 현재 primary direction은 `CAND-01: Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`이며, hypothesis 작업은 `hypothesis/CAND-01/H001_uncertainty-reobservation/`에 정리되어 있다.

### 에이전트 추론

연구의 핵심은 semantic map uncertainty를 단순 confidence score로만 쓰지 않고, robot이 어디로 이동해 다시 관찰할지 결정하는 active SLAM/navigation utility로 사용하는 것이다.

## 2. 문제 정의

### 사실

Pre-explored semantic map은 ObjectNav와 language-guided navigation에서 goal candidate를 찾는 데 사용할 수 있다. 그러나 map에는 false positive object, ambiguous query match, low-support observation, viewpoint bias, stale semantic evidence가 남는다.

### 에이전트 추론

현재 문제 정의는 다음과 같다.

> 불확실한 semantic memory를 robot이 언제, 어디서 다시 관찰해야 ObjectNav failure와 SLAM/map inconsistency를 함께 줄일 수 있는가?

## 3. 현재 핵심 가설

### 에이전트 추론

If an ObjectNav agent uses pre-explored semantic map object/node uncertainty and SLAM uncertainty to choose active re-observation viewpoints, then wrong-goal visits and wasted path decrease while map/pose consistency improves, compared with semantic-only replanning and geometry-only exploration baselines.

## 4. 제안 방향

### 에이전트 추론

연구는 Step 1-5를 하나의 umbrella hypothesis로 진행한다.

1. Pre-explored semantic map에서 object/node uncertainty를 계산한다.
2. Uncertain candidate에 대해 active re-observation viewpoint를 선택한다.
3. ObjectNav에서 `Success Rate`, `SPL`, wrong-goal visit, wasted path를 평가한다.
4. Semantic memory를 active SLAM utility로 확장한다.
5. Map error, semantic accuracy, `ATE`, `RPE`, pose graph connectivity까지 평가한다.

## 5. 문헌 및 workflow 상태

### 사실

- `AGENTS.md`, `TODO.md`, `docs/index.md`, `docs/literature.md`, `docs/hypothesis.md`를 작성했다.
- Top-tier venue 중심으로 literature survey를 진행했고, `literature/README.md`, `literature/PAPER.md`, paper folder, `literature/Contribution Candidates.md`, `literature/CAND-001.md`를 작성했다.
- Hypothesis workflow와 `H001` 문서를 만들었고, 6개월-1년 연구 범위로 기준을 수정했다.
- 연구 목표 rule에 AI, ML, CV, Robotics top-tier journal/conference 타겟을 반영했다.

### 논문 주장

`VLMaps`, `ConceptGraphs`, `CARe`, `DualMap`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `3D Active Metric-Semantic SLAM` 등은 semantic map, object-centric memory, active perception, SLAM uncertainty가 navigation 성능과 연결될 수 있음을 각각 주장한다.

`LAMP`는 implicit neural language field, sparse graph planning, gradient-based fine pose refinement, embedding uncertainty modeling을 통해 memory-efficient language-driven navigation이 가능하다고 주장한다. `3DSR`은 voxelized 3D Gaussian splatting을 통해 renderable visual spatial representation의 memory cost를 줄이면서 robotics용 reconstruction / localization / navigation applicability를 유지할 수 있다고 주장한다.

### 에이전트 추론

현재 방향은 최신 흐름과 잘 맞지만, top-tier 수준의 차별점은 "semantic uncertainty가 실제 mobility decision과 SLAM/map quality 개선으로 이어지는가"를 재현 가능한 metric으로 보여줄 때 생긴다.

`LAMP`는 H001과 직접 연결된다. 다만 H001은 implicit language map 자체보다 semantic uncertainty가 active re-observation, wrong-goal visit, wasted path, SLAM/map consistency를 개선하는지에 초점을 둔다. `3DSR`은 직접 baseline보다는 Step 4-5와 real-world deploy에서 renderable spatial memory backend 후보로 연결된다.

## 6. Dataset / runtime 확보 상태

### 사실

- Docker 기반 실험 원칙을 정했다.
- HM3D v0.2 scene assets, ObjectNav HM3D v2 episodes, HM3D-OVON episodes의 Docker mount smoke를 통과했다.
- `research3/habitat-h001:20260508` runtime image smoke를 통과했다.
- `wrong_goal_visit`, `wasted_path`, GT oracle reference, baseline log schema를 구현했다.
- GT는 action selection에는 사용하지 않고, correctness labeling과 oracle reference에만 사용하도록 boundary를 정했다.

### 에이전트 추론

Benchmark path는 `HM3D ObjectNav`를 primary로 두고, positive signal 이후 `HM3D-OVON`으로 open-vocabulary ambiguity를 확장하는 구성이 적합하다.

## 7. Candidate backend 및 calibration 진행

### 사실

- Non-GT semantic candidate backend adapter를 구현했다.
- `VLMaps` 기반 feature-grid artifact exporter와 OpenAI `CLIP` `ViT-B/32` query embedding exporter를 구현했다.
- Habitat pre-exploration RGB-D/pose export와 trajectory-derived `alignment.json` smoke를 통과했다.
- `random256_k10_sr1_v1` scene replacement recovery artifact는 candidate count `300`, reachable correct-and-wrong rate `0.66`으로 coverage gate를 통과했다.

### 에이전트 추론

초기 blocker는 policy가 아니라 candidate substrate coverage였다. 현재는 coverage가 어느 정도 회복되어 policy/evidence scorer 쪽 병목을 분리해서 보는 단계다.

## 8. Policy / evidence scorer 진행 결과

### 사실

- `NoReobserve`, `RandomReobserve`, `SemanticOnly`, `SemanticVerifyTop`, `EvidenceGatedSemanticOnly` 관련 smoke와 calibration run을 진행했다.
- Recovered substrate에서 current `SemanticOnly`는 wrong-goal visit rate를 줄이지 못했고, 오히려 `NoReobserve` 대비 악화되는 결과를 보였다.
- `EvidenceGatedSemanticOnly` support proxy는 wrong-goal `0.38`, switch gate pass rate `0.0`으로 action 변화가 거의 없었다.
- `image_feature raw_delta` calibration run은 `SR 0.26`, `SPL 0.1690`, wrong-goal `0.38`, switch pass `0.18`을 기록했지만 held-out promotion은 막혔다.
- `postview_evidence_v2`는 action eligible row rate `0.56`, AUC `0.4968`로 gate failed.
- `postview_evidence_v2.1 relaxed_position`은 action eligible row rate `0.80`, AUC `0.4939`로 gate failed.
- `postview_evidence_v3a depth_mask`는 action eligible row rate `0.80`, object mask row rate `0.80`, AUC `0.5598`, selected-correct delta `+0.12`를 보였지만 wrong-goal aggregated top correct는 `4/19`로 유지되어 policy-scale comparison은 blocked 상태다.

### 에이전트 추론

v3a는 object-level evidence가 local crop보다 낫다는 신호를 보였지만, depth-mask만으로는 cluttered category에서 충분하지 않다. 다음 병목은 detector/segmenter 기반 object evidence와 semantic candidate association이다.

## 9. Open-vocabulary detector / segmenter 진행

### 사실

- 별도 `openvocab-perception` image 원칙을 정했다. Habitat runtime image에는 detector/segmenter stack을 섞지 않는다.
- `OWL-ViT` setup job은 완료되었고, image `research3/openvocab-perception:20260513-owlvit`에서 offline `OwlViTProcessor` / `OwlViTForObjectDetection` load가 통과했다.
- `v3b_owlvit_box` 2-row Docker smoke를 구현했다.
- `v3b` 결과:
  - default query, threshold `0.05`: detector box rate `0.50`, candidate association rate `0.00`
  - `a photo of a {query}`, threshold `0.01`, `position`: detector box rate `1.00`, candidate association rate `0.50`
  - 같은 조건의 `visit_position`: detector box rate `1.00`, candidate association rate `0.00`
- `v3b_owlvit_box`는 full calibration으로 promote하지 않는다.
- `v3c_groundingdino_sam2` setup job을 `tmux` session `h001-openvocab-v3c-setup`으로 launch했고, 완료 verification을 통과했다.
- `v3c_groundingdino_sam2` detector+mask CPU smoke를 실행했다.

Current v3c setup:

```text
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
GroundingDINO model: IDEA-Research/grounding-dino-tiny
SAM2 checkpoint: sam2.1_hiera_tiny.pt
status_file: /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup/job_status.json
log: logs/openvocab-perception-v3c-groundingdino-sam2-20260513-204258.log
status: completed/verified
CPU verification log: logs/openvocab-perception-v3c-groundingdino-sam2-cpu-verify-20260514-000244.log
cuda_available: false
smoke output: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_cpu_smoke_top3
smoke log: logs/postview-evidence-v3c-groundingdino-sam2-cpu-smoke-top3-20260514-001410.log
smoke result: detector_box_rate 1.00, sam2_mask_rate 1.00, candidate_association_rate 1.00
```

### 에이전트 추론

`OWL-ViT` box-only evidence는 detector recall 자체는 확보할 수 있지만, semantic candidate와 안정적으로 연결되지는 않았다. `GroundingDINO + SAM2`는 box/mask generation 자체는 안정적이지만, 현재 association count와 mask count만으로는 candidate correctness를 충분히 구분하지 못한다.

## 9.1 V3C calibration status

### 사실

```text
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
uses_gt_for_action: false
```

Completed detector diagnostics:

```text
original_v3c_calib50:
  query_template: a photo of a {query}.
  max_headings_per_frame: 2
  association_rate: 0.30
  promotion: failed

A2_query_heading6_calib50:
  query_template: {query}
  max_headings_per_frame: 6
  candidate_point_field: position
  detector_box_rate: 1.00
  sam2_mask_rate: 1.00
  association_rate: 0.48
  best_candidate_auc: 0.628
  promotion: failed

A4_all_headings_calib50:
  query_template: {query}
  max_headings_per_frame: all exported headings
  candidate_point_field: position
  detector_box_rate: 1.00
  sam2_mask_rate: 1.00
  association_rate: 0.52
  best_candidate_auc: 0.607
  promotion: failed
```

### 에이전트 추론

50-row calibration은 policy result가 아니라 detector+mask evidence diagnostic이다. 현재 결과는 detector/mask availability가 아니라 evidence objective가 병목임을 보여준다. `associated_count`, `inside_mask_count`, `visible_count`는 candidate correctness에 대해 거의 random이고, `best_box_score_max`만 약한 positive signal을 가진다.

다음 단계는 추가 policy run이 아니라 `v3d_detector_objective` offline calibration이다. 목표는 semantic prior, detector confidence, visibility support, geometry/depth penalty를 결합해 wrong-goal fix를 늘리면서 new wrong-goal을 만들지 않는 conservative switching objective를 찾는 것이다.

`v3d_detector_objective` strict offline calibration 결과, 현재 objective는 아직 paper-facing gate를 통과하지 못했다. `O1_detector_max`가 가장 강한 신호였지만 candidate AUC는 `0.607`로 기준 `0.65`에 못 미쳤다. `O2_detector_prior`, `O3_detector_geometry`, `O4_conservative_switch`는 selected-correct delta는 작게 양수였지만 candidate-level AUC는 더 낮아졌다. 다음 단계는 policy-scale run이 아니라 query/category별 detector-objective failure diagnosis와 object-node evidence representation revision이다.

Object-node evidence revision에서는 point-in-mask hit만 보지 않고 `node_box_proximity`, `node_extent_score`, `compact_node_extent_score`를 추가했다. Category-best gate는 `bed`에는 `O1_detector_max`, `toilet`과 `tv_monitor`에는 `O6_compact_extent`, 실패 category인 `chair`, `sofa`, `plant`에는 semantic prior를 유지하도록 설계했다. Calibration split에서 `O9_category_best_gate`는 selected-correct를 `11/50`에서 `17/50`으로 올렸고 wrong-goal fixes `7`, new wrong-goals `1`을 보였다. Conservative `O10_category_best_switch`는 switch margin `0.10`에서 selected-correct `14/50`, wrong-goal fixes `3`, new wrong-goals `0`을 보였다.

이 결과는 policy-facing shape는 생겼지만 아직 같은 calibration split에서 설계한 gate이므로 paper claim으로 쓰기에는 이르다.

Category-best detector objective의 leave-one-scene-out cross-validation은 output `/tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_loso_cv`에 기록했다. Best margin `0.00`에서 selected-correct는 baseline `11/50` 대비 `14/50`으로 증가했고, wrong-goal fixes `3`, new wrong-goals `0`, switches `10`이었다. 하지만 positive delta가 나온 held-out scene은 `2/5`개뿐이었다. 따라서 `minimal safety gate`는 통과했지만 `robust gate`는 실패했다.

다음 검증은 policy-scale run이 아니라 더 큰 independent held-out detector-objective validation이다. Policy-scale integration contract는 category-best rule이 더 넓은 held-out scene/episode에서 robust improvement를 보인 뒤에만 작성한다.

Held-out validation 준비로 `first_eval` scene spec을 `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/first_eval_scenes.txt`에 분리했다. 대상은 HM3D ObjectNav v2 `val`의 10개 scene, 100개 episode다. `calibration_artifact_job.sh`는 5 scene / 30 query-row 고정을 풀어 `EXPECTED_SCENE_COUNT`, `EXPECTED_QUERY_ROWS`를 받도록 바꿨고, `postview_v3c_groundingdino_sam2_calib50.sh`는 `FRAMES`, `CANDIDATE_ARTIFACT`, `OUT` override를 Docker 내부 경로까지 반영하도록 수정했다.

First_eval `k10` candidate artifact generation은 완료됐다. Output은 `/tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1`이고, rows `60`, candidates `600`, finite positions `579`, scenes `10`, queries `6`이다. 이어서 100 episode candidate substrate coverage gate를 실행했지만 실패했다. `GTTargetOracle` success는 `1.0`, `NoReobserve` wrong-goal은 `0.49`, candidate label coverage는 `1.0`으로 충분했지만, reachable correct-and-wrong ambiguity rate가 `0.40`으로 기준 `0.50`에 못 미쳤다.

따라서 first_eval detector validation은 아직 blocked다. 가장 낮은 confound recovery로 같은 first_eval scenes와 같은 trajectory budget을 유지하고 `MAX_CANDIDATES`만 `10 -> 20`으로 올린 `first_eval_random256_k20_v1`을 완료했다. Output은 `/tmp/research3-runs/h001_first_eval_artifacts_random256_k20_v1`이고, rows `60`, candidates `1200`, finite positions `1170`이다. Coverage는 `0.40 -> 0.46`으로 개선됐지만 기준 `0.50`에는 못 미쳤다. `GTTargetOracle` success는 `1.0`, `NoReobserve` wrong-goal은 `0.49`, candidate label coverage는 `1.0`이었다.

이 결과에 따라 reachability-diverse candidate backend revision을 시작했다. `export_vlmaps_artifact.py`에 `--selection-mode spatial_nms`를 추가했고, semantic score grid에서 고득점 cell을 최소 거리 제약으로 분산 선택한다. 1-query smoke는 통과했다. 첫 `first_eval_spatial_nms_k20_v1` launch는 `habitat-h001` image 내부의 오래된 exporter가 실행되어 실패했다. 이후 `calibration_artifact_job.sh`가 repo runtime을 mount하고 `PYTHONPATH`를 설정하도록 수정했다. 첫 retry는 `7/10` scene 이후 중단되면서 `job_status.json`이 0바이트로 남았다. 이를 막기 위해 status write를 atomic replace로 바꿨고, resume2 job을 완료했다.

`first_eval_spatial_nms_k20_v1` artifact는 rows `60`, candidates `1200`, finite positions `1004`로 구조 검증을 통과했다. Coverage gate 결과는 `GTTargetOracle` success `1.0`, `NoReobserve` wrong-goal `0.47`, candidate label coverage `1.0`, reachable correct-and-wrong rate `0.49`였다. 기준 `0.50`에 1 episode 부족해 detector validation은 여전히 blocked다. 다음 recovery는 scene replacement가 아니라 `TOP_PERCENTILE=97.0` 같은 lower-percentile spatial NMS가 적합하다. 같은 maps/scenes에서 후보 추출만 바꾸기 때문에 confound가 더 작다.

`first_eval_spatial_nms_p97_k20_v1`은 기존 `spatial_nms_k20` maps를 재사용해 후보 추출만 `TOP_PERCENTILE=97.0`으로 낮춘 artifact다. Rows `60`, candidates `1200`, finite positions `1087`로 구조 검증은 통과했다. Coverage gate에서는 candidate reachable rate가 `0.59`까지 올랐지만, reachable correct-and-wrong rate는 `0.49`로 그대로여서 hard gate는 실패했다. 따라서 detector validation은 계속 blocked이며, 다음 recovery는 scene/episode replacement substrate probe다.

Replacement pool은 first_eval에 아직 쓰지 않은 HM3D ObjectNav `val` scene 중 scene asset이 있고 여섯 ObjectNav category가 모두 있는 scene으로 제한했다. Deterministic top-3 probe scene은 `5cdEh9F2hJL`, `6s7QHgap2fW`, `GLAQ4DNUx5U`이며, `manifests/replacement_probe_scenes.txt`에 기록했다. Replacement-probe artifact generation은 `tmux` session `h001-replacement-probe-p97-k20-20260515-113921`에서 완료됐다.

Replacement-probe coverage는 통과했다. 30 episode probe에서 reachable correct-and-wrong rate는 `0.6667`, `NoReobserve` wrong-goal은 `0.6333`이었다. Scene별로는 `5cdEh9F2hJL 1.0`, `6s7QHgap2fW 0.6`, `GLAQ4DNUx5U 0.4`였다. 따라서 first_eval replacement v1은 최악 scene `k1cupFYWXJ6`만 `5cdEh9F2hJL`로 바꾸는 최소 교체안으로 구성했다.

First_eval replacement v1은 coverage gate를 통과했다. 100 episode 기준 `GTTargetOracle` success `1.0`, `NoReobserve` wrong-goal `0.51`, candidate reachable rate `0.688`, reachable correct-and-wrong rate `0.59`였다. 이에 따라 `first_eval_replacement_v3c_detector_artifact.sh`를 추가하고, `tmux` session `h001-first-eval-repl-v3c-detector-20260515-115938`에서 policy revision, post-view frame export, `GroundingDINO + SAM2` detector artifact 생성을 시작했다.

## 9.2 ObjectNav에서 Spatial Navigation으로의 확장 위치

### 에이전트 추론

현재 실험은 ObjectNav 쪽에서 시작한다. 이유는 ObjectNav가 GT correctness label, wrong-goal visit, wasted path, `Success Rate`, `SPL`을 제공해 semantic uncertainty가 실제 mobility decision에 도움이 되는지 먼저 검증할 수 있기 때문이다.

하지만 최종 연구 방향은 ObjectNav에 갇히지 않는다. ObjectNav는 first evaluation gate이고, positive signal 이후 spatial navigation / active SLAM 쪽으로 확장한다. 이때 같은 semantic uncertainty utility를 pose graph connectivity, tracking failure, map error, semantic accuracy, `ATE`, `RPE`, travel cost로 평가한다.

## 10. 아직 하지 않은 내용 / 검증 필요

### 사실

- Detector+mask 50-row calibration은 실행했지만 promotion gate를 통과하지 못했다.
- Detector evidence objective를 아직 policy-facing scorer로 확정하지 않았다.
- Category-best detector objective는 leave-one-scene-out cross-validation에서 minimal safety gate만 통과했고 robust gate는 통과하지 못했다.
- `first_eval` 원본 `k10`, `k20`, `spatial_nms_k20`, `spatial_nms_p97_k20` candidate artifact는 생성됐지만 coverage gate가 실패했다.
- `first_eval_replacement_v1` candidate substrate는 coverage gate를 통과했다.
- First_eval replacement v1 detector artifact retry는 완료됐지만 verification gate를 통과하지 못했다.
- Failed detector artifact의 detector box rate와 SAM2 mask rate는 각각 `0.9388`로 높았지만, candidate association rate는 `0.4082 < 0.60`이었다.
- 약한 category는 `tv_monitor 0/9`, `plant 2/18`, `sofa 4/18`이며, box/mask availability보다 detector-object association이 병목이다.
- Failed detector artifact에서 objective diagnostic을 실행했지만, gate는 `false`이고 best selected-correct delta는 `+0.02`뿐이었다. 이 결과는 diagnostic일 뿐 promotion evidence가 아니다.
- Association variant diagnostic을 Docker로 실행했다. `box_or_mask_depth_none`은 association rate를 `0.76`까지 올렸지만 `associated_count` AUC는 `0.586`, selected-correct delta는 `-0.11`, new wrong-goals는 `10`이었다.
- 따라서 단순 depth tolerance 완화나 box containment 허용은 coverage fix일 뿐, policy-facing evidence fix가 아니다.
- Weak-category evidence revision v1을 Docker로 실행했다. `plant`는 `soft_box_no_depth_count`, `tv_monitor`는 `score_box_no_depth_sum`, `sofa`는 semantic prior 유지로 처리했다.
- Same-artifact diagnostic에서는 selected-correct가 `33/100 -> 36/100`으로 증가했고, wrong-goal fixes는 `3`, new wrong-goals는 `0`이었다.
- 이 결과는 같은 artifact에서 rule/margin을 고른 candidate evidence이므로 아직 promotion evidence가 아니다.
- Weak-category rule v1의 scene-wise robustness check를 실행했다. 전체적으로는 positive scenes `2`, negative scenes `0`, new wrong-goals `0`으로 scene-wise minimal gate는 통과했다.
- 하지만 category-level로는 `plant`가 `TEEsavR23oF` 한 scene에서만, `tv_monitor`가 `y9hTuugGdiq` 한 scene에서만 개선되어 category robust gate는 실패했다.
- Top-tier novelty 관점에서는 `weak_category_rule_v1`을 paper-facing method로 reject하고 diagnostic evidence로만 유지하기로 했다. Category별 hand-tuned rule은 contribution으로 약하고, failure taxonomy에서 나온 일반 object-node evidence objective가 더 적합하다.
- General object-node evidence objective contract를 작성했다. 핵심 항은 `S_sem`, `S_det`, `S_proj`, `S_depth`, `S_prop`, `R_amb`이고, ablation은 `N0_semantic_prior_only`부터 `N5_object_node_evidence_full`까지다.
- Offline `N0-N5` object-node evidence analyzer를 구현하고 실행했다. `N5_object_node_evidence_full`은 candidate AUC `0.6892`를 보였지만 direct re-ranking에서는 selected-correct delta `-0.04`, new wrong-goals `7`로 실패했다.
- Global margin sweep에서 `N5`는 margin `0.30` 이상에서 new wrong-goal을 없앴지만 wrong-goal fix도 `0`이 되어 inactive해졌다. 따라서 direct object-node re-ranking은 현재 promotion-ready가 아니다.
- Conservative top-candidate confirmation/disconfirmation diagnostic을 구현하고 실행했다. Best same-artifact config는 `N1_detector_score_only`로, top detector score가 best alternative 이상이면 confirm, best alternative가 top보다 `0.25` 이상 높으면 disconfirm한다.
- Confirmation/disconfirmation diagnostic에서는 confirmed rows `58`, confirmed correct rate `0.397` vs baseline `0.33`, confirmed wrong-goal rate `0.448` vs baseline `0.51`, disconfirmed rows `3`, disconfirmed wrong-goal precision `1.0`, false disconfirm `0`이었다.
- 이 결과는 같은 artifact diagnostic이므로 promotion evidence는 아니지만, object-node evidence를 direct re-ranking이 아니라 semantic top candidate risk update로 쓰는 방향을 지지한다.
- Confirmation/disconfirmation gate는 `confirmation_v1_detector_contradiction`으로 freeze했다. Fixed config는 `N1_detector_score_only`, `confirm_margin 0.0`, `disconfirm_margin 0.25`다.
- 독립 검증용 `confirmation_independent_v1` manifest를 만들었다. `replacement_probe`에서 `first_eval_replacement_v1`에 들어간 `5cdEh9F2hJL`을 제외하고 `6s7QHgap2fW`, `GLAQ4DNUx5U`의 20 episode만 남겼으며, host와 Docker verify를 통과했다.
- `confirmation_independent_v3c_detector_artifact.sh` wrapper를 추가했다. 다음 검증은 이 split에서 detector artifact를 만들고, fixed confirmation gate를 search 없이 실행하는 것이다.
- `confirmation_independent_v1` detector artifact job을 `tmux` session `h001-confirmation-independent-v3c-20260515-160651`로 시작했고 완료했다. Detector box rate와 SAM2 mask rate는 `1.0`, candidate association rate는 `0.45`였다.
- 독립 split에서 fixed confirmation gate를 search 없이 실행했지만 실패했다. `promotion_ready false`, `confirmed_wrong_goal 9/12`, `wrong_goal_routed_to_reobserve_rate 0.40`, `disconfirmed_wrong_goal_precision 1.0`, `false_disconfirm 0`이다.
- 실패 원인은 false disconfirm이 아니라 unsafe confirmation이다. `top_score == alt_score == 0` 같은 no-evidence tie가 confirmation으로 처리되었고, 이 4개 row가 모두 wrong-goal이었다.
- V2 rule 방향을 `confirmation_v2_supported_contradiction`으로 정리했다. 핵심은 no-evidence tie와 detector-score-only evidence를 confirmation으로 보지 않고, `S_det`와 `S_proj/S_depth/S_prop` 중 하나 이상의 positive support가 있을 때만 confirmed 상태를 허용하는 것이다.
- V2 debugging run도 실행했다. `confirmed_rows 3/20`, `confirmed_wrong_goal_rate 1.0`, `disconfirmed_wrong_goal_precision 1.0`, `wrong_goal_routed_to_reobserve_rate 0.80`이었다. 따라서 object-node evidence는 commit authority가 아니라 risk/re-observation trigger로 쓰는 방향이 더 적합하다.
- Risk-only re-observation utility contract를 작성했다. `RiskOnlyReobserve`는 semantic top candidate를 default로 유지하고, object-node evidence는 `R_no_evidence`, `R_contradiction`, `R_ambiguity`, `R_property_weakness`를 통해 active re-observation utility만 높인다.
- `RiskOnlyReobserve`를 `run_smoke.py`에 구현했고 Docker smoke를 통과했다. Output은 `/tmp/research3-runs/h001_risk_only_reobserve_smoke_v1`이며, 4 episode에서 `risk_triggered_reobserve_rate 1.0`, `final_candidate_changed_rate 0.0`, `switch_gate_pass_rate 0.0`으로 direct goal switch가 비활성화되어 있음을 확인했다.
- Risk-only promotion 검증은 fresh larger split으로 진행하기로 했다. `confirmation_independent_v1`은 이미 V2/risk-only 설계에 영향을 줬으므로 debugging-only로 유지하고, 다음 validation은 최소 `5 scenes / 50 episodes`, 가능하면 `10 scenes / 100 episodes`의 `risk_validation_v1`로 만든다.
- Active observation 이후 risk update contract를 정했다. `R_before`는 semantic ambiguity와 missing object-node evidence 기반이고, `R_after`는 active observation 뒤 object-node evidence로 재계산한다. `R_after < risk_total_trigger`일 때만 semantic top candidate commit을 허용하고, unresolved risk는 `risk_unresolved`로 commit을 보류한다.
- `risk_validation_v1` split을 준비했다. Manifest는 `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_risk_validation_v1.json`이고, 10 scene / 100 episodes이며 host와 Docker verify를 통과했다.
- `risk_validation_v1` candidate artifact generation을 `tmux` session `h001-risk-validation-p97-k20-20260515-173425`로 시작했다. Output은 `/tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1`, log는 `logs/risk-validation-spatial-nms-p97-k20-20260515-173425.log`다.
- Policy-scale comparison은 independent confirmation validation이 통과하기 전까지 blocked 상태다.
- `SLAMOnly`, `SemanticSLAM`의 Step 4-5 paper-facing 비교는 아직 구현하지 않았다.
- Real-world robot deploy용 구체 장비, sensor, LiDAR, GT setup은 아직 확정되지 않았다.

### 사용자 판단 필요

- Simulation-only first paper로 갈지, small real-world proof-of-concept까지 포함할지 결정해야 한다.
- Real-world validation에 사용할 robot base, RGB-D/stereo sensor, LiDAR, external GT 또는 `AprilTag` setup을 확정해야 한다.

## 11. 향후 실험 계획

### 에이전트 추론

1. Full `ExternalCandidateFollowupObservation` detector/evidence validation job을 작성한다.
2. Full follow-up job에서 `request_identity_confirmation`과 `request_expanded_retrieval`이 safe commit 또는 safe defer로 바뀌는지 확인한다.
3. Follow-up evidence full gate가 통과할 때만 `first_eval` replacement rerun을 검토한다.
4. `NoReobserve`, `RandomReobserve`, geometry-only, semantic-only, direct re-ranking, threshold-only alternative를 ablation으로 고정한다.
5. Policy shape은 direct goal switch가 아니라 "semantic default + uncertainty-triggered active observation + evidence-based commit/defer"로 둔다.
6. Robust held-out detector-objective / follow-up evidence gate 통과 후에만 policy-scale integration contract를 작성한다.
7. Positive signal이 나오면 Step 4-5로 확장해 pose graph connectivity, semantic accuracy, map error, `ATE`, `RPE`를 평가한다.
8. Simulation 결과가 충분할 때 real-world proof-of-concept를 설계한다.

## 12. 현재 결론

### 사실

현재까지는 dataset/runtime/logging/candidate substrate를 구축했고, semantic uncertainty policy가 단순 score threshold나 direct re-ranking으로는 충분하지 않다는 negative evidence를 얻었다. V4 external evidence는 uncertainty를 active observation request로 바꾸는 방향에서 가장 좋은 신호를 보였지만, follow-up evidence full validation은 아직 통과하지 못했다.

### 에이전트 추론

현재 가장 중요한 연구 판단은 `semantic uncertainty` 자체를 포기하는 것이 아니라, uncertainty update를 active observation utility로 바꾸는 것이다. `GroundingDINO + SAM2`는 box/mask 생성에는 충분하지만, 그 자체가 novelty가 아니다. 단순히 더 많이 associate하거나 direct re-ranking하면 wrong-goal을 늘릴 수 있다. 다음 핵심은 object-node evidence를 "맞다는 확신"이 아니라 "어떤 추가 관찰이 필요한가"와 "관찰 뒤에도 commit이 안전한가"를 판단하는 utility로 쓰는 것이다.
