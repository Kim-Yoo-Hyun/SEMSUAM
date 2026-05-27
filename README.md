# Research3

이 저장소는 석사 연구를 진행하고 최종 논문으로 발전시키기 위한 작업 공간이다.

## Start Here

처음 들어오면 아래 순서로 읽는다.

1. [AGENTS.md](AGENTS.md): 연구 운영 규칙과 에이전트 작업 규칙
2. [TODO.md](TODO.md): 현재 작업 상태, 다음 행동, 완료 이력
3. [docs/index.md](docs/index.md): 문헌 조사, hypothesis, workflow 문서로 이동하는 index
4. [docs/reproducibility.md](docs/reproducibility.md): 데이터, checkpoint, Docker, 재현 명령, artifact/evaluation 요약

## Active Direction

현재 primary direction은 `CAND-01 / H001`이다.

중심 주장은 다음과 같다.

> semantic uncertainty가 active SLAM/navigation utility로 작동해서 ObjectNav 같은 navigation task에서 wrong-goal visit과 wasted path를 줄이고, 확장 단계에서는 map/pose consistency까지 개선할 수 있는지 검증한다.

## Current Status

### 사실

- Date checked: 2026-05-27
- Current gate: design expanded-retrieval frame/detector evidence gate for source-pool-valid rows.
- `h001_dense_conflict_v1` manifest and recall gate are implemented and Docker-verified.
- Host NVIDIA runtime was recovered on 2026-05-23.
- `spatial_nms_p95_k100_d10` and revised `spatial_nms_p90_k200_d5` dense re-export artifacts both failed the final recall gate with primary rows with correct candidate `3/6`; detector/association validation remains blocked for those re-export substrates.
- The existing selected substrate `v3_fresh_spatial_p97_k20` passed the final primary recall gate with `6/6` rows and recall@20 `1.0`.
- Dense conflict detector/association validation was materialized from the existing `v3_fresh` second-stage evidence at `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1`; primary gate passed with detector box `1.0`, SAM2 mask `1.0`, candidate association `0.8`, commit/success/wrong/no-valid `5/5/0/0`, and `uses_gt_for_action false`.
- Secondary-stress held-out `sofa` validation also passed at `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1`; recall rows with correct `2/2`, detector box/SAM2/candidate association `1.0/1.0/1.0`, commit/success/wrong/no-valid `2/2/0/0`, and `uses_gt_for_action false`.
- Broader split design output `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json` selects `scene_disjoint_first_eval_style` as the next paper-facing path.
- Frozen `dense_conflict_generalization_v1` manifest is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_generalization_v1.json`: `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`, and `uses_gt_for_action false`.
- Generalization recall gate passed at `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1`: rows with correct `20/20`, recall@20 `1.0`, recall@5 `0.85`.
- Generalization detector substrate passed at `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1`: detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`, associated rows `7/20`, and `uses_gt_for_action false`.
- Terminal evidence extraction passed GT separation at `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1`: action evidence rows `20`, evaluation label rows `55`, associated/unassociated rows `7/13`, forbidden action key count `0`, and `uses_gt_for_action false`.
- Terminal arbitration v0 is unsafe. `proposed_conservative_v0` commits `7/20` with `3` success and `4` wrong-goal commits.
- `strict_depth_consistency_v1` guard design was Docker-verified at `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1`: commit/success/wrong `3/3/0` on the same diagnostic split, associated commit rate `3/7`, and `uses_gt_for_action false`. This is a fixed-rule validation candidate, not a paper claim.
- Fixed-rule terminal validation was Docker-verified at `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1`: action evidence forbidden key count `0`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`, and `uses_gt_for_action false`. It remains same-split validation, so independent validation is still required before a paper-facing utility claim.
- Independent terminal validation contract is frozen at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_independent_v1.json`: primary `v3_fresh_validation_v1` source has `6/6` associated rows across `3` scenes and `2` queries; secondary `sofa` stress source has `2/2` associated rows.
- Independent validation rejects `strict_depth_consistency_v1`: primary output `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1` has commit/success/wrong `6/2/4`; secondary stress output `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1` has `2/0/2`. Both have forbidden action key count `0` and `uses_gt_for_action false`.
- Failure diagnosis output `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1` shows wrong rows `6`, with `repeated_wrong_instance_selected_by_saturated_support 5` and `guard_cannot_arbitrate_between_eligible_correct_and_wrong 1`. The next design contract is `rival_identity_confirmation_v1`.
- `rival_identity_confirmation_v1` diagnostic output `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1` passes the local diagnostic gate: commit/success/wrong `2/2/0`, request identity rows `6`, forbidden action keys `0`, and `uses_gt_for_action false`. This is not yet a paper-facing utility proof.
- Active observation/evaluation contract is frozen at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_observation_v1.json`: request rows `6`, planner `rival_identity_pair_probe_v1`, and post-observation gate requires zero wrong-goal commits plus at least one newly resolved primary request.
- `rival_identity_pair_probe_v1` observation planner is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/plan_rival_identity_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1` passes the plan smoke gate: request rows `6`, planned request rows `6`, plan rows `19`, skipped rows `0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- `rival_identity_pair_probe_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1`: rows requested/exported `19/19`, rendered headings `142`, RGB/depth files `142/142`, unique scenes `3`, nonblank RGB sanity pass, and `uses_gt_for_action false`.
- `rival_identity_pair_probe_v1` detector substrate job completed at `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1`: detector rows `19`, detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, rows with candidate association `12/19`, associated candidate heading count `57`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Post-observation evidence/validation contract is frozen in `hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md`: action-time evidence and evaluation labels are separated, label join key is `(episode_key, candidate_id)`, and the fixed rule commits only when exactly one candidate has strong own-view identity evidence.
- `rival_identity_pair_probe_v1` post-observation analyzer is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_rival_identity_post_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1` passes the diagnostic gate: request rows `6`, evidence rows `19`, commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- Fresh/predeclared validation source design selects `rival_identity_generalization_v1` from the frozen `dense_conflict_generalization_v1` primary action evidence. A design probe at `local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1` finds `6` request rows across `3` scenes and `2` queries, excluding the prior diagnostic scenes `DYehNKdT76V`, `7MXmsvcQjpJ`, and `y9hTuugGdiq`.
- `rival_identity_generalization_v1` source miner is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/build_rival_identity_generalization_manifest.py`. Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1` freezes `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_generalization_v1.json` with request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`; verify file reports `ok true`.
- `rival_identity_generalization_v1` observation planner smoke passed at `local_dataset/runs/h001_rival_identity_generalization_plan_v1`: request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_generalization_frames_v1`: rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity passed, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` detector/SAM2 substrate job completed at `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1`: detector rows `12`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `1.0`, associated candidate heading count `84`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Frozen post-observation analyzer on `rival_identity_generalization_v1` completed at `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1`: request/evidence/decision rows `6/12/6`, commit/success/wrong/no-label `4/2/2/0`, new primary success `2`, resolved rows `4`, and `uses_gt_for_action false`. The gate failed because two single-candidate `toilet` requests committed wrong goals.
- Failure diagnosis output `local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1` explains the fresh-source failure before any rule revision. Mechanism counts are `rival_identity_resolved_success 2`, `rival_identity_unresolved_cross_view_aliasing 2`, and `single_candidate_object_existence_false_positive 2`; all wrong commits are single-positive-candidate `toilet` false positives, while multi-positive `bed` requests stay in rival-identity arbitration.
- Taxonomy split output `local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1` is Docker-verified. The analyzer now writes `request_taxonomy_route`; route counts are `rival_identity_arbitration 4` and `object_existence_validation 2`. Failure taxonomy counts are `none 2`, `rival_identity_unresolved_cross_view_aliasing 2`, and `object_existence_false_positive_commit 2`; unsafe rival-identity commits are `0`.
- Object-existence no-commit branch output `local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1` is Docker-verified. Single-positive `object_existence_validation` rows now produce `defer_object_existence_validation` instead of commit. The fresh-source gate passes with commit/success/wrong `2/2/0`, defer-object-existence `2`, and `uses_gt_for_action false`.
- Regression output `local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1` preserves the prior diagnostic positive signal with commit/success/wrong `1/1/0`, route counts `rival_identity_arbitration 6`, and `uses_gt_for_action false`.
- Independent object-existence validation probe output `local_dataset/runs/h001_rival_identity_object_existence_probe_v1` is Docker-verified. Object-existence request rows `2` both have a naive unique-strong commit baseline that would be wrong; wrong-goal avoided by defer is `2`, success lost by defer is `0`, and action evidence forbidden key count is `0`.
- Broader fresh-source validation design output `local_dataset/runs/h001_rival_identity_broader_validation_design_v1` is Docker-verified. It freezes `risk_validation` as preferred source, selects `72` parent rows across `10` scenes and `6` queries, estimates `22` request rows from prior request rate `0.30`, and passes the design gate. Actual miner gate is `>=20` request rows, `>=5` scenes, `>=3` queries, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- `rival_identity_broader_validation_v1` source miner is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/build_rival_identity_broader_manifest.py`. Docker output `local_dataset/runs/h001_rival_identity_broader_source_v1` freezes `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_broader_validation_v1.json`; verify reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` and `object_existence_validation 4`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- `rival_identity_broader_validation_v1` observation planner smoke passed at `local_dataset/runs/h001_rival_identity_broader_plan_v1`: request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, missing action rows `0`, candidate artifact rows/candidates `21/80`, action evidence forbidden key count `0`, plan gate `true`, and `uses_gt_for_action false`.
- `rival_identity_broader_validation_v1` frame export passed at `local_dataset/runs/h001_rival_identity_broader_frames_v1`: rows requested/exported `112/112`, rendered headings `862`, RGB/depth/metadata files `862/862/862`, unique scenes `10`, and `uses_gt_for_action false`. Strict no-blank-heading sanity found `56/862` blank RGB headings across `20` rows, but no all-blank rows; `filter_nonblank_frame_summary.py` produced `nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl` with `112` rows and `806` headings, row-level nonblank gate `true`.
- Corrected broader detector substrate passed at `local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2`, but post-observation remained safe and inert. Failure diagnostic `local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1` shows this is a zero-standoff planner geometry failure: all `112` plan rows used target-distance `0.0m` viewpoints, own associations are `0`, and cross associations are `442`.
- Zero-standoff-safe planner contract is defined at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_broader_standoff_planner_v1.json`. It requires non-GT standoff viewpoints before rerunning frames, detector, and post-observation analysis.
- Zero-standoff-safe planner implementation is Docker-verified at `local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1`. It passes plan and geometry gates with request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, scenes `10`, queries `6`, zero/near-standoff rows `0/0`, rotation/candidate fallback rows `0/0`, target distance min/mean/max `1.6386/1.7506/1.9747m`, viewpoint sources `standoff_navmesh 104` / `standoff_geometry 8`, and `uses_gt_for_action false`.
- Mixed standoff frame export `local_dataset/runs/h001_rival_identity_broader_frames_standoff_v1` rendered `112/112` rows and `1079` headings, but row-level nonblank gate failed with `5` dropped rows. All dropped rows were `standoff_geometry` fallback with `standoff_navmesh_navigable false`.
- Navmesh-only standoff repair is Docker-verified at `local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1` and `local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1`: plan rows `104`, planned request rows `28`, skipped rows `8`, scenes `9`, queries `6`, frame rows `104/104`, headings `997`, dropped/blank rows `0/0`, row-level and strict no-blank gates `true`, `uses_gt_for_action false`.
- Navmesh-only standoff detector/SAM2 substrate passed at `local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1`: detector rows `104`, detector box rate `0.9808`, SAM2 mask rate `0.9808`, candidate association rate `0.7212`, rows with association `75`, associated heading count `277`, `uses_gt_for_action false`.
- Fixed post-observation analyzer on that substrate failed at `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1`: request/evidence/decision rows `28/110/28`, commit/success/wrong/no-label `7/0/7/0`, unsafe commit queries `bed 4`, `chair 2`, `tv_monitor 1`.
- Unsafe-commit diagnostic `local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1` rejects threshold-only repair: semantic-rank, detector-score, depth-consistency, and own-count simple guards still commit wrong goals, while the safe combined simple guard is inert with `0` commits.
- Stricter arbitration design contract is frozen at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_strict_arbitration_v1.json`.
- `goal_validity_arbitration_v1` is implemented in `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_rival_identity_post_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1` passes the diagnostic gate with commit/success/wrong/no-label `2/2/0/0`, but this is not a paper claim because the same broader split was used for diagnosis and objective design.
- Independent/predeclared source for `goal_validity_arbitration_v1` is frozen at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_goal_validity_independent_v1.json`; verify reports `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` and `object_existence_validation 4`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`. The source is mined from `v3_fresh_validation` after excluding prior diagnostic and broader diagnostic scenes.
- Independent substrate `local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1` passes detector gate with detector rows `92`, detector box `1.0`, SAM2 mask `1.0`, candidate association `0.6196`, rows with association `57`, and `uses_gt_for_action false`.
- Independent `goal_validity_arbitration_v1` rerun at `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1` is safe but inert: request/evidence/decision rows `30/101/30`, commit/success/wrong/no-label `0/0/0/0`, wrong-goal and no-label gates pass, but success and resolved-request gates fail.
- Default counterfactual on the same independent evidence at `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1` is nontrivial but unsafe: commit/success/wrong/no-label `7/4/3/0`, with wrong-goal queries `chair`, `sofa`, and `toilet`.
- Failure diagnostic `local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1` rejects same-evidence threshold repair: dominant tags include `cross_view_aliasing_blocks_goal_validity 14`, `planned_candidate_set_has_no_valid_goal 13`, `no_own_candidate_support 11`, and `strong_identity_not_goal_validity 8`.
- Revision contract `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_goal_validity_revision_v2.json` blocks threshold tuning from joined labels and requires branch-specific evidence revision.
- Router output `local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1` maps all `30` requests to next-evidence actions without GT action inputs: `request_discriminative_rival_view 14`, `request_expanded_retrieval 8`, `request_object_existence_confirmation 6`, and `request_goal_validity_confirmation 2`; terminal commit remains blocked.
- Branch-specific planner contract `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_discriminative_rival_view_planner_v1.json` is defined for the largest router branch. It requires contrastive focus-rival pair views, explicit pair candidate ids, no GT/post-join action inputs, and plan/frame/detector/evaluation gates before any paper claim.
- `discriminative_rival_view_planner_v1` plan smoke passed at `local_dataset/runs/h001_discriminative_rival_view_plan_v1`: source router rows `14`, planned request rows `14`, plan rows `38`, common pair view rows `10`, matched dual standoff rows `28`, zero/near-standoff `0/0`, rotation fallback `0`, and `uses_gt_for_action false`.
- v1 frame smoke exposed one blank `common_pair_geometry` row, so planner v2 now keeps only navmesh-snapped common pair views. v2 plan output `local_dataset/runs/h001_discriminative_rival_view_plan_v2` keeps plan rows `38`, common pair navmesh rows `10`, and matched dual standoff rows `28`.
- v2 frame/nonblank output `local_dataset/runs/h001_discriminative_rival_view_frames_v2` passes with rows/headings `38/222`, dropped rows `0`, removed blank headings `0`, row-level and strict no-blank gates `true`, role counts `common 10`, `focus 14`, `rival 14`, and `uses_gt_for_action false`.
- Initial detector/SAM2 substrate v1 passed the substrate gate but did not preserve pair-role metadata in detector associations. Detector/SAM2 substrate v2 completed at `local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2` with detector rows `38`, detector box/SAM2 `1.0/1.0`, candidate association `0.8158`, rows with association `31`, and role-preserved detector associations.
- `analyze_discriminative_rival_view_evidence.py` output `local_dataset/runs/h001_discriminative_rival_view_evidence_v1` fails the diagnostic gate: evidence availability `1.0`, disambiguation `0.6429`, actions `support_focus 8`, `support_rival 1`, `ambiguous_defer 5`, but single-correct pairs are all `rival_only_correct 3`, preferred-correct rate is `0.0`, and wrong-preference rate is `0.3333`.
- Failure diagnostic `local_dataset/runs/h001_discriminative_rival_view_failure_diagnostic_v1` blocks threshold tuning and fresh validation. Dominant tags are `symmetric_cross_view_leak 7`, `rival_visible_from_focus_view 6`, `identity_score_near_tie 5`, `common_view_supports_both_candidates 5`, `no_valid_goal_pair_but_disambiguated 4`, and `rival_correct_own_view_evidence_weak 3`.
- Branch priority decision: handle `request_expanded_retrieval` before further discriminative-view tuning, because the current failure includes invalid/no-valid candidate pairs; discriminative views remain useful later as identity validation after retrieval expands the candidate set.
- Contract `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_branch_v1.json` is frozen before implementation. It uses router rows with `revision_action == request_expanded_retrieval`, expects `8` request rows, sets candidate budget `6-10`, forbids GT/evaluation labels for action, blocks terminal commit, and requires candidate-set validity gates before detector/objective work.
- Expanded-retrieval planner smoke passed at `local_dataset/runs/h001_expanded_retrieval_plan_v1`: expected/request rows `8/8`, candidate-set rows `8`, plan rows `80`, candidates per request `10`, skipped rows `0`, duplicate candidate rate `0.0`, nonfinite position rate `0.0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- Expanded-retrieval analysis-only candidate-set diagnostic passed label join at `local_dataset/runs/h001_expanded_retrieval_candidate_set_validity_v1`: contains-correct `6/8`, no-valid `2/8`, source-top correct `1/8`, source-top wrong-goal `7/8`, wrong-top replacement `5/7`, and wrong-goal candidate present in `7/8`. Full-pool comparison shows `source_pool_no_valid_candidate 2`, `valid_set_with_wrong_goal_distractor 5`, and `valid_set_without_wrong_goal_distractor 1`.
- Expanded-retrieval candidate-set guard design passed at `local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1`: route counts are `request_backend_retrieval_revision 2`, `request_detector_guarded_observation 5`, and `request_lightweight_confirmation 1`; detector evidence is allowed for `6/8`, terminal commit rows are `0`, `guard_design_gate_passed true`, `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false`. This is analysis-only design, not an action-time rule.
- Expanded-retrieval non-GT proxy feature audit passed feature extraction at `local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1`, but the candidate-set score/support proxy is not ready: proxy route counts are `request_detector_guarded_observation_proxy 8`, source-pool validity proxy recall is `0.0`, both backend-revision target rows are escalated to evidence, and `proxy_ready_for_detector_gate false`.
- Expanded-retrieval source-pool validity proxy passed the current diagnostic gate at `local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1`: proxy route counts are `request_backend_retrieval_revision_proxy 2` and `request_detector_guarded_observation_proxy 6`, consumed forbidden rows are `0`, source-pool validity proxy recall is `1.0`, evidence-allowed target recall is `1.0`, backend targets escalated to evidence are `0`, `proxy_ready_for_detector_gate true`, `uses_gt_for_action false`, and `paper_claim_allowed false`.
- Cross-machine recovery and Drive backup paths are documented in [docs/reproducibility.md](docs/reproducibility.md).

### 에이전트 추론

The detector/association blocker is lifted for the selected primary and secondary diagnostic substrates, and the broader frozen split now passes corrected detector substrate. The independent result is a useful negative result: strict depth-consistent support is not sufficient because wrong instances can also be detector-associated and depth-consistent. `rival_identity_confirmation_v1` remains useful as a mechanism-level direction for multi-positive rival ambiguity. The no-commit object-existence branch repairs the immediate fresh-source safety failure, and the probe shows why: the current single-positive rows are both avoided wrong-goals, not lost successes. The broader zero-standoff geometry blocker is repaired, and navmesh-only detector evidence is available. The newer negative result is that own-view category evidence alone proves visible object existence, not valid `ObjectNav` goal identity. `goal_validity_arbitration_v1` repaired the diagnostic split but fails as an independent paper-facing utility rule because it makes no commits on the frozen validation source. The default counterfactual shows the opposite failure: nonzero success comes with wrong-goal commits. Therefore the next useful path is branch-specific active evidence acquisition. Expanded retrieval is partially positive because it recovers valid candidates in `6/8` rows and replaces wrong source tops in `5/7` wrong-top rows. The guard design fixes the intended routing target, and the new source-pool proxy separates backend-revision rows from detector-eligible rows on the current diagnostic source without GT action inputs. The next blocker is a frame/detector evidence gate for the detector-eligible rows; paper-facing utility still requires fresh/predeclared validation.

## Key Documents

- Literature overview: [literature/README.md](literature/README.md)
- Paper registry: [literature/PAPER.md](literature/PAPER.md)
- Primary candidate: [literature/CAND-01.md](literature/CAND-01.md)
- Hypothesis index: [hypothesis/README.md](hypothesis/README.md)
- Active hypothesis: [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)
- Evaluation contract: [07_evaluation_contract.md](hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md)
- Reproducibility: [docs/reproducibility.md](docs/reproducibility.md)
- Research report summary: [summary.md](summary.md)

## Current Dataset Gates

The current Docker-based dataset gates are open for:

- HM3D v0.2 scene assets
- HM3D semantic annotations
- ObjectNav HM3D v2 episodes
- HM3D-OVON episodes

Runtime scripts, Dockerfiles, and smoke workflow notes live under:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/
```

Current data paths, checkpoint paths, Docker images, and reproduction commands are summarized in [docs/reproducibility.md](docs/reproducibility.md).

## Local Assets

Canonical local paths:

```text
local_dataset/data
local_dataset/models
local_dataset/runs
```

Compatibility paths:

```text
/tmp/research3-data
/tmp/research3-models
/tmp/research3-runs
```

Large datasets, model checkpoints, run artifacts, Docker image archives, paper PDFs, and credentials are intentionally not GitHub source-of-truth.

2026-05-23 note: `/tmp/research3-data` was observed as a stale empty directory after reboot, so active jobs should use canonical `local_dataset/` paths until `/tmp` compatibility paths are normalized.

## Repository Rule

The repository root is kept as an entrypoint only.

Root files should stay limited to:

- `AGENTS.md`
- `.gitignore`
- `README.md`
- `summary.md`
- `TODO.md`

Research details, workflow notes, runtime scripts, Dockerfiles, and experiment design documents should live under the relevant workflow or hypothesis folder.

## What Not To Do

- Do not create empty `experiments/`, `paper/`, `results/`, or `decisions/` folders in advance.
- Do not use host Python for smoke tests or implementation experiments.
- Do not treat GT oracle policies as deployable baselines.
- Do not mix facts, paper claims, agent inference, and user decisions in the same section.
