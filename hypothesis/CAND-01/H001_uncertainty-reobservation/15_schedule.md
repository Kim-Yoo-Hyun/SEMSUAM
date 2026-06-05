# Schedule

## Purpose

H001을 6개월-1년 범위에서 first probe, Step 4-5 SLAM extension, real-world validation으로 순차 확장하는 연구 일정을 정의한다.

이 문서는 논문 제목이나 최종 claim을 확정하지 않는다. 각 단계가 다음 단계로 넘어가기 위한 evidence gate를 정한다.

## Facts

- Date checked: 2026-06-06
- Active hypothesis: H001 `Semantic-SLAM Uncertainty Re-observation`
- Primary benchmark path: Habitat ObjectNav with HM3D, then HM3D-OVON extension.
- Available runtime gates: HM3D / HM3D-OVON Docker mount, `habitat-h001` smoke, logging schema, non-GT candidate adapter, `VLMaps` artifact exporter, synthetic alignment adapter.
- Current paper-facing blocker: semantic object routes are branch-closed or terminal-blocked with promotable terminal outcome `0`, and the current `SemanticSLAM` proxy line is still `P4-design`. The safe-but-sparse selector diagnostic shows current geometry-only map/pose evidence is available but not candidate-discriminative.
- Latest schedule gate: safe-but-sparse selector diagnostic passed, but candidate separability gate failed with primary blocker `label_free_geometry_alternatives_reintroduce_wrong_goal_risk`. Terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, formula revision, and paper claims remain blocked.
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
- `h001_expanded_retrieval_detector_evidence_v1` is frozen as the detector evidence contract. Plan output `local_dataset/runs/h001_expanded_retrieval_detector_plan_v1` passes with detector proxy request rows `6`, planned request rows `6`, plan rows `42`, min/max plan rows per request `5/8`, zero/near-standoff `0/0`, fallback rows `0`, consumed forbidden action fields `0`, and `uses_gt_for_action false`.
- Frame output `local_dataset/runs/h001_expanded_retrieval_detector_frames_v1` passes with rows/headings `42/168`; nonblank filter passes with dropped rows `0`, removed blank headings `0`, and strict no-blank heading gate `true`.
- Detector/SAM2 substrate job `h001-expanded-retrieval-detector-20260527-141012` completed at `local_dataset/runs/h001_expanded_retrieval_detector_substrate_v1`. Detector rows match `42`, detector box/SAM2 mask rates pass at `1.0/1.0`, but candidate association rate is `0.0714` with rows with association `3/42`; `passes_detector_substrate_gate false`. Projection status counts are `out_of_fov 134` and `visible 34`; depth checks are `consistent 6`, `depth_mismatch 28`, and `out_of_fov 134`.
- Failure diagnostic `local_dataset/runs/h001_expanded_retrieval_detector_failure_diagnostic_v1` passes its accounting gate with `42` candidate observation rows and `168` heading rows. Failure mechanisms are `projection_never_visible 33`, `mask_overlap_depth_mismatch_only 4`, `associated_success 3`, `visible_projection_no_detector_overlap 1`, and `box_overlap_mask_reject 1`; all `42` rows have detector box/SAM2 availability. Gates set `threshold_tuning_allowed false`, `viewpoint_revision_required true`, `association_depth_revision_required true`, and `paper_claim_allowed false`.
- Viewpoint/projection revision design `local_dataset/runs/h001_expanded_retrieval_detector_viewpoint_revision_design_v1` passes. Current out-of-FOV axis count is `x_in_y_above 134`; `projection_anchor_height_sweep_v1` with offsets `[0.0, 0.4, 0.8, 1.2, 1.6]` recovers `33/33` `projection_never_visible` rows in projection replay. Contract `manifests/h001_expanded_retrieval_detector_viewpoint_revision_v1.json` freezes the design and blocks detector threshold, depth tolerance, and terminal objective changes before projection-anchor smoke.
- Revised observation/projection implementation smoke passes. `plan_expanded_retrieval_detector_observation.py` now emits `h001.expanded_retrieval_detector_observation_plan.v2`; `detect_postview_groundingdino_sam2.py` evaluates fixed projection anchors during candidate association; `smoke_expanded_retrieval_projection_anchor.py` provides detector-free projection smoke. Plan output `local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1` passes with plan rows `42`, planned request rows `6`, offsets `[0.0, 0.4, 0.8, 1.2, 1.6]`, and `uses_gt_for_action false`. Full projection smoke `local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_smoke_v1` passes with visible rows `42/42`; 2-row frame passthrough smoke `local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_frame_passthrough_smoke_v1` preserves revision metadata in `2/2` rows.
- Fixed-anchor detector/SAM2 rerun completed at `local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1`. Detector rows `42`, detector box/SAM2 rates `1.0/1.0`, candidate association rate `0.7381`, associated rows `31/42`, associated heading count `96`, selected projection anchor offsets counts `0.0:21`, `0.4:3`, `0.8:13`, `1.2:9`, `1.6:122`, and `passes_detector_substrate_gate true`; `uses_gt_for_action false`, `paper_claim_allowed false`.
- Fresh/predeclared expanded-retrieval source freeze passes at `local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_v1` with manifest `manifests/h001_expanded_retrieval_fresh_validation_v1.json`: `6` `request_expanded_retrieval` rows, `2` scenes, `4` queries, excluded-scene overlap `0`, action forbidden keys `0`, missing action evidence rows `0`, and `uses_gt_for_action false`. Planner compatibility output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_plan_v1` passes with candidate-set rows `6`, plan rows `60`, skipped rows `0`, and `paper_claim_allowed false`. Paper-scale gate remains false because rows/scenes are below `20/5`.
- Frozen fresh source proxy/plan/frame gates pass. Proxy output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_pool_validity_proxy_v1` routes `6/6` rows to detector-guarded observation and passes the action-only detector gate. Detector plan output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_plan_projection_anchor_v1` has planned requests `6`, plan rows `51`, skipped rows `9` all `standoff_navmesh_required`, plan rows per request `7-10`, target distance min/mean/max `1.7417/1.7506/1.7975m`, zero/near/fallback rows `0/0/0`, and `uses_gt_for_action false`. Frame output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_frames_projection_anchor_v1` exports `51` rows and `204` headings; nonblank filter removes `0` headings; projection smoke output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_projection_anchor_smoke_v1` has visible rows `51/51` and revision metadata rows `51/51`.
- Frozen fresh detector/SAM2 substrate passes at `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_substrate_projection_anchor_v1`. Detector rows `51`, detector box/SAM2 rates `1.0/1.0`, candidate association rate `0.6078`, associated rows `31/51`, associated heading count `68`, selected projection anchor offsets `0.0:8`, `1.2:12`, `1.6:184`, `uses_gt_for_action false`, and `paper_claim_allowed false`.
- Fresh detector evidence diagnostic output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_evidence_diagnostic_v1` passes the diagnostic gate. It has request rows `6`, candidate rows `51`, associated request rate `1.0`, strong request rate `1.0`, multi-strong request rate `0.8333`, lower-rank-only association rate `0.5`, topology counts `multi_strong_saturated_ambiguity 5` and `single_strong_lower_rank 1`; `terminal_objective_allowed false`, `paper_scale_gate_passed false`, and `paper_claim_allowed false`.
- Ambiguity-aware expanded-retrieval objective contract `manifests/h001_expanded_retrieval_ambiguity_objective_v1.json` is Docker-applied at `local_dataset/runs/h001_expanded_retrieval_ambiguity_objective_contract_v1`. It has request rows `6`, route coverage `1.0`, terminal commit rows `0`, action counts `request_local_context_disambiguation 5` and `request_rank_challenge_confirmation 1`; `contract_gate_passed true`, `larger_source_allowed_after_contract true`, `terminal_objective_allowed false`, and `paper_claim_allowed false`.
- Paper-scale expanded-retrieval source `manifests/h001_expanded_retrieval_paper_scale_v1.json` is Docker-frozen from nonterminal `defer_expanded_retrieval_needed` decisions. Source output `local_dataset/runs/h001_expanded_retrieval_paper_scale_source_v1` has request rows `23`, scenes `10`, queries `6`, excluded-scene overlap `0`, action forbidden keys `0`, `uses_gt_for_action false`, and paper-scale gate `true`. Planner compatibility output `local_dataset/runs/h001_expanded_retrieval_paper_scale_plan_v1` has candidate-set rows `23`, plan rows `230`, skipped rows `0`, and planner gate `true`. Source-pool proxy output `local_dataset/runs/h001_expanded_retrieval_paper_scale_source_pool_validity_proxy_v1` routes `21/23` rows to `request_detector_guarded_observation_proxy` and passes the action-only detector gate.
- Paper-scale projection-anchor detector observation plan `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_v1` passes. It has detector proxy request rows `21`, planned request rows `21`, plan rows `162`, skipped rows `48` all `standoff_navmesh_required`, plan rows per request `5-10`, candidate artifact rows `16`, target distance min/mean/max `1.6335/1.7503/1.8053m`, viewpoint source `standoff_navmesh 162`, zero/near/fallback/rotation fallback rows `0/0/0/0`, and `uses_gt_for_action false`.
- Paper-scale frame/projection smoke initially failed with fixed offsets `[0.0, 0.4, 0.8, 1.2, 1.6]`: frame export and nonblank passed with rows/headings `162/648` and blank rows/headings `0/0`, but projection visible rows were `153/162 = 0.9444`. All failed rows were `bxsVRursffK/plant` with `x_in_y_above`. The official upper-anchor repair `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_upper_v1` extends fixed category-agnostic offsets to `[0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4]`; frame output `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_upper_v1` and projection smoke `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_projection_anchor_upper_smoke_v1` pass with visible rows `162/162`, missing candidates `0`, and `uses_gt_for_action false`.
- Paper-scale detector/SAM2 substrate `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1` passes with detector rows `162`, detector box/SAM2 `1.0/1.0`, candidate association `0.8272`, associated rows `134/162`, and `uses_gt_for_action false`.
- Paper-scale detector evidence diagnostic `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_evidence_diagnostic_upper_v1` passes with request rows `21`, associated/strong/multi-strong request rates `1.0/1.0/1.0`, topology `multi_strong_saturated_ambiguity 21`, and `terminal_objective_allowed false`.
- Paper-scale ambiguity objective `local_dataset/runs/h001_expanded_retrieval_paper_scale_ambiguity_objective_upper_v1` passes with route coverage `1.0`, action `request_local_context_disambiguation 21`, and terminal commit rows `0`.
- Paper-scale local-context disambiguation contract `manifests/h001_expanded_retrieval_local_context_disambiguation_v1.json` is frozen with source filter `objective_action == request_local_context_disambiguation`, planner `expanded_retrieval_local_context_disambiguation_v1`, planned request minimum `18/21`, and terminal commit limited to `local_context_unique_own_view_advantage`; direct detector-score and source-top shortcut commits are blocked.
- Revised local-context objective contract `manifests/h001_expanded_retrieval_local_context_revision_v1.json` is frozen after post-observation failure diagnosis. It requires `pool_validity_guard_v2` before `wrong_instance_arbitration_guard_v1`, blocks detector-score/source-top/own-support/local-context-only shortcut commits, and keeps paper claims blocked until Docker evaluation produces zero wrong/no-valid commits with nonzero safe utility.
- Revised local-context analyzer output `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1` is safe but inert: `goal_validity_guarded_local_context_v1` commit/success/wrong/no-valid `0/0/0/0`, route counts `request_goal_validity_confirmation 12` and `defer_instance_arbitration_unresolved 9`, action forbidden keys `0`, substrate gate passed, utility gate failed.
- Revised local-context route diagnostic `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1` shows `pool_guard_false_positive_no_valid_pool 4`, `unsafe_previous_commit_prevented 7`, `previous_rule_success_lost_by_guard 3`, `correct_and_wrong_both_strong_own_view 7`, `wrong_only_strong_own_view 7`, and `simpler_alternatives_unsafe_analysis_only 20`. The next contract must separate source-pool validity repair from goal-validity confirmation.
- Route-specific local-context contract `manifests/h001_expanded_retrieval_local_context_route_contract_v1.json` is frozen. It separates `source_pool_repair_v1`, `goal_validity_confirmation_v1`, and `instance_arbitration_defer_v1`; keeps terminal commits blocked; requires all `21` rows to be routed with forbidden action keys `0`; and keeps `paper_claim_allowed false`.
- Route-specific local-context analyzer `runtime/h001_runtime/analyze_expanded_retrieval_local_context_route_specific.py` is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1`. It routes `21` rows into `request_source_pool_repair 5`, `request_goal_validity_confirmation_evidence 7`, and `defer_instance_arbitration_unresolved 9`; terminal commits are `0`; forbidden action keys are `0`; and post-action label join shows all no-valid rows route to source-pool repair `4/4`.
- Source-pool repair evidence contract `manifests/h001_expanded_retrieval_source_pool_repair_v1.json` is frozen. It consumes the five `request_source_pool_repair` rows, keeps terminal commits blocked, and requires route actions `request_backend_pool_expansion`, `route_to_goal_validity_confirmation_after_pool_repair`, or `defer_source_pool_unresolved`; label join remains evaluation-only.
- Source-pool repair analyzer `runtime/h001_runtime/analyze_expanded_retrieval_source_pool_repair.py` is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_source_pool_repair_v1`. It has request/evaluated rows `5/5`, route counts `request_backend_pool_expansion 5`, `route_to_goal_validity_confirmation_after_pool_repair 0`, `defer_source_pool_unresolved 0`, no-valid rows under backend expansion `4`, valid rows under backend expansion `1`, terminal commits `0`, forbidden action keys `0`, and `source_pool_repair_gate_passed true`.
- Backend pool expansion evidence contract `manifests/h001_expanded_retrieval_backend_pool_expansion_v1.json` is frozen. It consumes the five `request_backend_pool_expansion` rows, keeps terminal commits blocked, requires expanded candidate accounting, duplicate/reachability accounting, fixed backend config reporting, and routes to `request_backend_candidate_generation`, `route_to_goal_validity_confirmation_after_expansion`, or `defer_backend_pool_unresolved`; long-running dense backend jobs must follow the background-task policy.
- Backend pool expansion analyzer `runtime/h001_runtime/analyze_expanded_retrieval_backend_pool_expansion.py` is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_backend_pool_expansion_v1`. It has request/evaluated rows `5/5`, route counts `request_backend_candidate_generation 5`, `route_to_goal_validity_confirmation_after_expansion 0`, `defer_backend_pool_unresolved 0`, expanded candidate count `10` on all rows, fixed candidate budget minimum `20`, no-valid rows under the top-10 preview `3`, valid-containing rows `2`, terminal commits `0`, forbidden action keys `0`, and `backend_pool_expansion_gate_passed true`.
- Fixed backend candidate generation analyzer `runtime/h001_runtime/analyze_expanded_retrieval_backend_candidate_generation.py` is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1`. It consumes five `request_backend_candidate_generation` rows, uses existing non-GT action evidence through `fixed_action_evidence_top20_v1`, generates exactly `20` candidates per row and `100` candidate rows total, blocks terminal commits, reports lineage/duplicate/reachability accounting, and passes with action forbidden keys `0`. Post-generation label join shows valid-containing rows `2` and no-valid rows `3`, so deeper backend generation remains required before goal-validity confirmation.
- Deeper backend generation contract `manifests/h001_expanded_retrieval_deeper_backend_generation_v1.json` is frozen. It targets three diagnostic no-valid fixed top-20 rows across two scene/query pairs, fixes first variant `spatial_nms_p90_k100_d5_v1`, requires at least `50` candidates per target request and `150` generated candidate rows, blocks terminal commits, keeps action forbidden keys `0`, and allows only post-generation label join.
- Deeper backend generation analyzer/job is implemented. Docker target-spec smoke writes `3` action rows for `2` scene/query pairs with action forbidden keys `0`; existing `p97_k20` smoke writes `60` candidate labels but fails as expected because it has `20` candidates per request and `0` new-beyond-top20 candidates. Full job `h001-deeper-backend-20260529-003000` completed for `spatial_nms_p90_k100_d5_v1`: artifact coverage `ok true`, generated candidate rows `300`, `100` candidates per request, new-beyond-top20 `80` per request, recovered-valid rows `2`, still-no-valid rows `1`, `deeper_backend_generation_gate_passed true`, and `goal_validity_confirmation_unblocked true`.
- Recovered-row goal-validity confirmation contract `manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.json` is frozen. It consumes the three deeper-generation rows, sends `rival_identity:12` and `rival_identity:14` to goal-validity confirmation evidence, keeps `rival_identity:13` on a backend/pool-validity branch, blocks terminal commits, requires action forbidden keys `0`, and keeps `paper_claim_allowed false`.
- Pool-validity branch fallback contract `manifests/h001_expanded_retrieval_pool_validity_branch_v1.json` is frozen. It finds the `rival_identity:13` no-valid pool non-separable by candidate count, reachability/standoff, positive support, duplicate/nonfinite, or score-shape proxy, and fixes `spatial_nms_p80_k200_d3_v1` as the first fallback variant before any goal-validity confirmation.
- Pool-validity branch analyzer/job `runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_branch.py` and `runtime/jobs/expanded_retrieval_pool_validity_branch.sh` are implemented. Docker compile and target-spec smoke pass with branch/action/evaluated rows `1/1/1`, terminal commits `0`, action forbidden keys `0`, and expected missing-artifact gate false. Full job `h001-pool-validity-fallback-20260529-093033` completed: artifact coverage `ok true`, fallback candidate rows `200`, new-beyond-previous `100`, structural gate pass, valid-containing rows `0`, no-valid rows `1`, and `second_fallback_backend_required true`.
- Goal-validity confirmation request/branch analyzer `runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_confirmation.py` is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1`. It emits request rows `2`, branch rows `1`, candidate evidence target rows `200`, evaluated rows `3`, handoff actions `request_goal_validity_confirmation_evidence 2` and `request_non_gt_pool_validity_proxy_or_fallback_backend_variant 1`, terminal commits `0`, action forbidden keys `0`, and `goal_validity_confirmation_request_gate_passed true`.

### Paper Claims

- Recent open-vocabulary navigation and semantic memory papers motivate using environment-specific semantic memory, but they often leave semantic uncertainty, wrong-goal commitment, and map/pose-side utility weakly connected.
- Recent active semantic mapping and active SLAM papers motivate information-gain-driven viewpoint selection, but task-level navigation failure metrics are not always tied to semantic uncertainty.
- Recent `HM3D-OVON` and open-vocabulary embodied navigation work makes semantic ambiguity and unseen-object generalization more important than closed-class ObjectNav alone.

### Inferences

The current direction is aligned with recent AI, ML, CV, and Robotics top-tier trends if it is framed as semantic uncertainty becoming an active SLAM/navigation utility, not simply as adding `VLMaps` to ObjectNav. The latest result strengthens that framing: semantic uncertainty is no longer just a confidence threshold, but a router for additional evidence acquisition when terminal commitment is unsafe. The source-pool validity proxy removes the immediate detector-gate blocker on current diagnostic evidence, and the standoff frame gate avoids the earlier zero-standoff substrate failure. The detector run and failure taxonomy show box/mask availability is not enough because candidate projections are mostly out of FOV or depth-inconsistent. The revision design connects that failure to semantic-map anchor uncertainty: a category-agnostic height sweep recovers the vertical projection failures in replay. Paper-scale validation exposed that the first vertical range was still too narrow for one `plant` slice, and the upper-anchor repair fixes that frame substrate without changing source routing or GT separation. The fresh-source proxy/plan/frame, detector/SAM2 substrate, detector evidence diagnostic, ambiguity-aware objective contract, paper-scale source freeze, detector observation plan, upper-anchor frame/projection smoke, paper-scale detector/SAM2 substrate, paper-scale detector evidence diagnostic, ambiguity objective application, route-specific local-context analyzer, source-pool repair analyzer, backend pool expansion contract, backend pool expansion analyzer, fixed backend candidate generation contract, fixed backend candidate generation analyzer, deeper backend generation contract, deeper backend generation analyzer/job, recovered-row goal-validity confirmation contract, recovered-row request/branch analyzer, pool-validity branch fallback contract, pool-validity branch analyzer target-spec smoke, first fallback full job, second fallback contract, second fallback full job, candidate-specific goal-validity evidence planner, bounded/full detector substrate, full objective analyzer, ambiguity diagnostic, discriminative evidence contract, discriminative analyzer, relation/spatial context evidence contract, relation/spatial context analyzer, scene-graph/object-relation evidence contract, scene-graph/object-relation analyzer, object-relation observation coverage repair contract, bounded object-relation observation/evidence/arbitration gates, and fresh object-relation plan/frame/projection/detector/evidence gates now pass or are implemented/frozen. The latest deeper backend result shows backend recall can recover valid candidates on part of the no-valid pool, which supports the active backend-retrieval branch, but `bxsVRursffK::bed` is not recovered by either fallback. The current Semantic-SLAM blocker is now candidate separability: the safe-but-sparse diagnostic shows geometry-only map/pose alternatives can create commits, but they reintroduce `21` wrong-goal rows and `4` no-valid commits, so formula revision remains blocked.

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

Close geometry-only `SLAMOnlyRich_current` selector path as non-promotable and define candidate-relative map/pose evidence requirements.

사실: Safe-but-sparse `SLAMOnlyRich_current` selector diagnostic is implemented at `runtime/h001_runtime/diagnose_semantic_slam_safe_sparse_selector.py`, verified through `manifests/h001_semantic_slam_safe_sparse_selector_diagnostic_v1.verify.json`, and Docker-run at `local_dataset/runs/h001_semantic_slam_safe_sparse_selector_diagnostic_v1`. It writes request/alternative rows `50/300`; current unique-ready selector commit/success/wrong/defer rows `3/2/1/47`; `top_map_pose_tuple` and `top_projection_visible_heading` commit all `50` rows but produce success/wrong/no-valid rows `29/21/4`; action forbidden key count `0`; `uses_gt_for_action false`; diagnostic gate `true`; candidate separability gate `false`.

에이전트 추론: The geometry-only path should be closed as non-promotable under the current evidence. Any next `SLAMOnlyRich_current` revision must require candidate-relative map/pose evidence that separates same-category rivals without falling back to semantic rank, detector score, source-top, local-context, or evaluation labels.

The historical runtime notes below preserve why the active gate moved from semantic object branches to the `SemanticSLAM` task/map outcome probe.

The active observation/evaluation contract is frozen at `manifests/h001_rival_identity_observation_v1.json`. The observation planner is implemented at `runtime/h001_runtime/plan_rival_identity_observation.py`, and Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1` passes the diagnostic plan gate with six planned request rows, `19` plan rows, `0` skipped rows, and `uses_gt_for_action false`. Frame export smoke also passes at `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1` with `19/19` rows exported and `142` rendered headings. Detector substrate validation completed at `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1` with detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, and substrate gate `true`. The post-observation analyzer completed at `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1` with commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, and gate `true`.

Fresh-source design selects `rival_identity_generalization_v1`: `6` request rows from frozen `dense_conflict_generalization_v1` primary action evidence, across `3` scenes and `2` queries, excluding the previous diagnostic scenes. The source miner is implemented at `runtime/h001_runtime/build_rival_identity_generalization_manifest.py`; Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1` freezes `manifests/h001_rival_identity_generalization_v1.json`, and verify reports `ok true`, request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Planner smoke output `local_dataset/runs/h001_rival_identity_generalization_plan_v1` passes with request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, and `uses_gt_for_action false`. Frame export smoke output `local_dataset/runs/h001_rival_identity_generalization_frames_v1` passes with rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, nonblank RGB sanity pass, and `uses_gt_for_action false`. Detector/SAM2 substrate output `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1` passes with detector box/SAM2/candidate association `1.0/1.0/1.0`. Frozen post-observation analyzer output `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1` fails the gate with commit/success/wrong/no-label `4/2/2/0`. Failure diagnostic output `local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1` explains all wrong commits as single-positive-candidate `toilet` object-existence false positives and keeps the other four rows in rival-identity arbitration. Taxonomy split output `local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1` accepts this split with route counts `rival_identity_arbitration 4`, `object_existence_validation 2`, and failure taxonomy `none 2`, `rival_identity_unresolved_cross_view_aliasing 2`, `object_existence_false_positive_commit 2`. Object-existence no-commit branch output `local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1` passes the gate with commit/success/wrong `2/2/0` and defer-object-existence `2`; regression output `local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1` keeps diagnostic commit/success/wrong `1/1/0`. Independent object-existence probe output `local_dataset/runs/h001_rival_identity_object_existence_probe_v1` shows request rows `2`, naive wrong-goal rows `2`, wrong-goal avoided by defer `2`, success lost by defer `0`, and action evidence forbidden key count `0`. Broader validation design output `local_dataset/runs/h001_rival_identity_broader_validation_design_v1` freezes `risk_validation` as preferred source and selects `72` parent rows across `10` scenes and `6` queries, with estimated request rows `22`, top wrong-goal rows `41`, correct-and-wrong candidate rows `49`, and design gate pass. Broader source miner output `local_dataset/runs/h001_rival_identity_broader_source_v1` freezes `manifests/h001_rival_identity_broader_validation_v1.json`; verify reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` and `object_existence_validation 4`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Broader planner smoke output `local_dataset/runs/h001_rival_identity_broader_plan_v1` passes with request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, missing action rows `0`, candidate artifact rows/candidates `21/80`, plan gate `true`, and `uses_gt_for_action false`. Broader frame export output `local_dataset/runs/h001_rival_identity_broader_frames_v1` passes export with rows requested/exported `112/112`, rendered headings `862`, RGB/depth/metadata files `862/862/862`, and unique scenes `10`; nonblank filter output `nonblank_filter_v1` removes `56` blank headings, drops `0` rows, keeps `112` rows and `806` headings, and passes row-level nonblank gate. Corrected broader detector substrate later passed, but post-observation stayed safe and inert. Failure diagnostic `local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1` shows all `112` plan rows used zero-standoff target-distance `0.0m` viewpoints, yielding own associations `0` and cross associations `442`. Zero-standoff-safe standoff planner output `local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1` passes plan and geometry gates, but mixed-standoff frame export drops `5` geometry fallback rows. Navmesh-only standoff repair output `local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1` keeps plan rows `104`, planned request rows `28`, scenes `9`, queries `6`, and `uses_gt_for_action false`; frame output `local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1` passes row-level and strict no-blank gates with `104/104` rows and `997/997` headings. Navmesh-only detector/SAM2 substrate output `local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1` passes with detector rows `104`, detector box `0.9808`, SAM2 mask `0.9808`, candidate association `0.7212`, and `uses_gt_for_action false`. Fixed post-observation output `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1` fails with commit/success/wrong/no-label `7/0/7/0`. Unsafe diagnostic output `local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1` rejects threshold-only repair because simple guards still commit wrong goals or become inert. Contract `manifests/h001_rival_identity_strict_arbitration_v1.json` and implementation `analyze_rival_identity_post_observation.py --objective goal_validity_arbitration_v1` are now Docker-verified. Output `local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1` passes this diagnostic gate with commit/success/wrong/no-label `2/2/0/0`, but paper claim remains blocked. Independent/predeclared source `rival_identity_goal_validity_independent_v1` is now frozen from `v3_fresh_validation`; verify reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. Independent substrate passes with plan rows `92`, frame headings `810`, detector box/SAM2/candidate association `1.0/1.0/0.6196`. Independent rerun output `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1` is safe but inert with commit/success/wrong/no-label `0/0/0/0`. Default counterfactual output `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1` is nontrivial but unsafe with commit/success/wrong/no-label `7/4/3/0`. Failure diagnostic output `local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1` rejects same-evidence threshold repair, and router output `local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1` routes all `30` rows into branch-specific next observation actions. Paper claim remains blocked until a fixed branch-specific observation method passes fresh/predeclared validation.
