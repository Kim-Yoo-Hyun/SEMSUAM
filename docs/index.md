# Research Docs

이 문서는 연구 문서의 첫 진입점이다. `docs/` 안의 workflow 문서와 주요 연구 산출물을 빠르게 찾기 위해 사용한다.

## How to Use

1. 현재 작업 상태는 먼저 [TODO.md](../TODO.md)에서 확인한다.
2. 연구 운영 규칙은 [AGENTS.md](../AGENTS.md)를 따른다.
3. 문헌 조사 작업은 [literature.md](literature.md)를 읽고 [literature/README.md](../literature/README.md)와 [literature/PAPER.md](../literature/PAPER.md)로 이동한다.
4. contribution candidate 검토는 [Contribution Candidates.md](../literature/Contribution%20Candidates.md)와 [CAND-01.md](../literature/CAND-01.md)를 본다.
5. hypothesis 작업은 [hypothesis.md](hypothesis.md)를 읽고 [hypothesis/README.md](../hypothesis/README.md)로 이동한다.
6. paper novelty와 top-tier framing은 [paper.md](paper.md)를 따른다.
7. 재현을 위한 데이터, checkpoint, Docker, artifact 위치는 [reproducibility.md](reproducibility.md)에서 확인한다.
8. 현재 연구 보고서 형태의 요약은 [summary.md](../summary.md)에서 확인한다.

## Workflow Docs

| Workflow | Rule Document | Output Location | Role |
| --- | --- | --- | --- |
| Literature | [literature.md](literature.md) | [literature/](../literature/README.md) | field map, paper registry, contribution candidate 관리 |
| Hypothesis | [hypothesis.md](hypothesis.md) | [hypothesis/](../hypothesis/README.md) | candidate를 검증 가능한 hypothesis와 first probe로 압축 |
| Paper | [paper.md](paper.md) | `summary.md`, H001 documents | novelty gate, top-tier framing, paper-ready claim 판단 |
| Reproducibility | [reproducibility.md](reproducibility.md) | `local_dataset/{data,models,runs}` with `/tmp/research3-*` compatibility symlinks | 데이터, checkpoint, Docker, Drive 백업 경로, 재현 명령, artifact/evaluation 요약 |
| Dense Conflict Validation | [workflow-20260521-dense-conflict.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md) | H001 runtime workflow | wrong/ambiguous positive-support dense validation 설계 |
| Stage 1 Smoke Test | [workflow-20260507-smoke.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-smoke.md) | H001 runtime workflow | `VLMaps` / Habitat smoke test |
| HM3D-OVON | [workflow-20260507-ovon.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-ovon.md) | H001 runtime workflow | HM3D-OVON episode 확보와 mount smoke test |

## Active Research Direction

### 사실

- 현재 primary candidate는 [CAND-01.md](../literature/CAND-01.md)의 `Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`이다.
- 현재 active hypothesis는 [H001_uncertainty-reobservation](../hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)에 있다.
- 최종 연구 방향은 Step 5까지 포함한다.
- 현재 implementation gate는 expanded-retrieval source-pool validity proxy를 통과한 detector-eligible rows에 대해 frame/detector evidence gate를 설계하는 것이다.
- `spatial_nms_p95_k100_d10`과 `spatial_nms_p90_k200_d5` dense re-export recall gate는 모두 primary `3/6`으로 실패했다.
- 기존 selected substrate인 `v3_fresh_spatial_p97_k20`은 final primary recall gate `6/6`, recall@20 `1.0`으로 통과했고, detector/association validation도 `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1`에서 통과했다.
- Secondary-stress held-out `sofa` validation도 `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1`에서 통과했다.
- Broader split design은 `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json`에 기록됐고, `scene_disjoint_first_eval_style`로 `manifests/h001_dense_conflict_generalization_v1.json`을 freeze했다.
- Frozen `dense_conflict_generalization_v1`은 `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`이며, recall gate `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1`에서 rows with correct `20/20`, recall@20 `1.0`으로 통과했다.
- Generalization detector substrate job은 `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1`에서 완료됐고 detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`로 substrate gate를 통과했다.
- Terminal evidence extraction output `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1`은 action evidence와 evaluation labels를 분리했고 forbidden action key count `0`으로 통과했다. 다만 `proposed_conservative_v0`는 `7/20` commit 중 `4` wrong-goal commit을 만들어 reject 상태다.
- Terminal guard design output `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1`은 `strict_depth_consistency_v1`을 다음 fixed-rule 후보로 제안한다. 같은 diagnostic split 기준 commit/success/wrong은 `3/3/0`, associated commit rate는 `3/7`, `uses_gt_for_action false`다.
- Fixed-rule terminal validation output `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1`은 action/evaluation 분리 흐름을 재검증했고, forbidden action key count `0`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`을 기록했다. Paper claim status는 `same_split_fixed_rule_validation_not_method_claim`이다.
- Independent terminal validation contract `manifests/h001_dense_conflict_terminal_independent_v1.json`은 primary `v3_fresh_validation_v1` source를 선택한다. Primary profile은 `6/6` associated rows, `3` scenes, `2` queries이고, secondary repeated-object stress profile은 `2/2` associated rows다.
- Independent validation은 `strict_depth_consistency_v1`을 reject했다. Primary output `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1`은 commit/success/wrong `6/2/4`, secondary stress output `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1`은 `2/0/2`다. 두 결과 모두 forbidden action key count `0`이고 `uses_gt_for_action false`다.
- Failure diagnosis output `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1`은 wrong rows `6`개 중 `5`개를 `repeated_wrong_instance_selected_by_saturated_support`, `1`개를 `guard_cannot_arbitrate_between_eligible_correct_and_wrong`로 분류했다. 다음 design contract는 `rival_identity_confirmation_v1`이다.
- `rival_identity_confirmation_v1` diagnostic output `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1`은 commit/success/wrong `2/2/0`, request identity rows `6`, diagnostic pass `true`를 기록했다. 단, fresh-source observation/detector/analyzer 검증에서 wrong-goal commit `2`가 발생했으므로 paper-facing utility proof는 현재 허용하지 않는다.
- Active observation/evaluation contract는 `manifests/h001_rival_identity_observation_v1.json`에 freeze했다. Request rows는 `6`, planner는 `rival_identity_pair_probe_v1`, post-observation gate는 wrong-goal `0`과 newly resolved primary request `>=1`을 요구한다.
- `rival_identity_pair_probe_v1` observation planner는 `runtime/h001_runtime/plan_rival_identity_observation.py`에 구현했다. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1`은 request rows `6`, planned request rows `6`, plan rows `19`, skipped rows `0`, forbidden action keys `0`, `uses_gt_for_action false`, plan smoke `true`를 기록했다.
- `rival_identity_pair_probe_v1` frame export smoke는 `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1`에서 통과했다. Rows requested/exported `19/19`, rendered headings `142`, RGB/depth files `142/142`, unique scenes `3`, nonblank RGB sanity pass, `uses_gt_for_action false`다.
- `rival_identity_pair_probe_v1` detector substrate job은 `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1`에서 완료됐다. Detector rows `19`, detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, rows with candidate association `12/19`, `uses_gt_for_action false`, detector substrate gate `true`다.
- `rival_identity_pair_probe_v1` post-observation evidence/validation contract는 `07_evaluation_contract.md`와 `runtime/workflow-20260521-dense-conflict.md`에 freeze했다. Label join key는 `(episode_key, candidate_id)`이고, rule은 own-view detector association이 cross-view association과 nearest rival보다 충분히 강한 단일 후보에만 commit한다.
- `rival_identity_pair_probe_v1` post-observation analyzer는 `runtime/h001_runtime/analyze_rival_identity_post_observation.py`에 구현했다. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1`은 request rows `6`, evidence rows `19`, commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, action evidence forbidden key count `0`, `uses_gt_for_action false`, gate `true`를 기록했다.
- Fresh/predeclared validation source는 `rival_identity_generalization_v1`로 설계했다. Parent는 frozen `dense_conflict_generalization_v1` primary action evidence이고, design probe `local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1`은 prior diagnostic scenes를 제외한 request rows `6`, scenes `3`, queries `2`를 만든다.
- `rival_identity_generalization_v1` source miner는 `runtime/h001_runtime/build_rival_identity_generalization_manifest.py`에 구현했다. Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1`은 manifest `manifests/h001_rival_identity_generalization_v1.json`과 verify `manifests/h001_rival_identity_generalization_v1.verify.json`을 만들었고, verify는 `ok true`, request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, `uses_gt_for_action false`를 기록했다.
- `rival_identity_generalization_v1` planner smoke는 `local_dataset/runs/h001_rival_identity_generalization_plan_v1`에서 통과했다. Request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, `uses_gt_for_action false`다.
- `rival_identity_generalization_v1` frame export smoke는 `local_dataset/runs/h001_rival_identity_generalization_frames_v1`에서 통과했다. Rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, nonblank RGB sanity pass, `uses_gt_for_action false`다.
- `rival_identity_generalization_v1` detector/SAM2 substrate job은 `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1`에서 완료됐다. Detector rows `12`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `1.0`, associated candidate heading count `84`, `uses_gt_for_action false`, detector substrate gate `true`다.
- `rival_identity_generalization_v1` frozen post-observation analyzer는 `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1`에서 완료됐지만 gate를 통과하지 못했다. Request/evidence/decision rows `6/12/6`, commit/success/wrong/no-label `4/2/2/0`, new primary success `2`, resolved rows `4`, `uses_gt_for_action false`이며, wrong-goal commits `2`는 single-candidate `toilet` false positive에서 발생했다.
- Failure diagnosis는 `local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1`에 기록했다. Mechanism counts는 `rival_identity_resolved_success 2`, `rival_identity_unresolved_cross_view_aliasing 2`, `single_candidate_object_existence_false_positive 2`이며, `request_identity_no_guard_eligible_positive_candidates`가 single-candidate object-existence false positive와 multi-candidate rival-identity unresolved를 섞는다는 결론이다.
- Taxonomy split은 `local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1`에 기록했다. Analyzer는 `request_taxonomy_route`를 쓰며, route counts는 `rival_identity_arbitration 4`, `object_existence_validation 2`; failure taxonomy는 `none 2`, `rival_identity_unresolved_cross_view_aliasing 2`, `object_existence_false_positive_commit 2`다.
- Object-existence no-commit branch는 `local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1`에 기록했다. Single-positive `object_existence_validation` rows는 `defer_object_existence_validation`으로 처리되고, fresh-source gate는 commit/success/wrong `2/2/0`으로 통과한다. Regression run `local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1`도 commit/success/wrong `1/1/0`으로 기존 positive signal을 유지한다.
- Independent object-existence probe는 `local_dataset/runs/h001_rival_identity_object_existence_probe_v1`에 기록했다. Request rows `2`, naive wrong-goal rows `2`, wrong-goal avoided by defer `2`, success lost by defer `0`, action evidence forbidden key count `0`, probe design gate `true`다.
- Broader fresh-source validation design은 `local_dataset/runs/h001_rival_identity_broader_validation_design_v1`에 기록했다. Preferred source는 `risk_validation`, selected parent rows는 `72`, scenes `10`, queries `6`, estimated request rows `22`, top wrong-goal rows `41`, correct-and-wrong candidate rows `49`이며 design gate가 통과했다.
- `rival_identity_broader_validation_v1` source miner는 `runtime/h001_runtime/build_rival_identity_broader_manifest.py`에 구현했다. Docker output `local_dataset/runs/h001_rival_identity_broader_source_v1`은 manifest `manifests/h001_rival_identity_broader_validation_v1.json`과 verify `manifests/h001_rival_identity_broader_validation_v1.verify.json`을 만들었고, verify는 `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, excluded-scene overlap `0`, action evidence forbidden key count `0`, `uses_gt_for_action false`를 기록했다.
- `rival_identity_broader_validation_v1` planner smoke는 `local_dataset/runs/h001_rival_identity_broader_plan_v1`에서 통과했다. Request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, missing action rows `0`, candidate artifact rows/candidates `21/80`, plan gate `true`, `uses_gt_for_action false`다.
- `rival_identity_broader_validation_v1` frame export는 `local_dataset/runs/h001_rival_identity_broader_frames_v1`에서 통과했다. Rows requested/exported `112/112`, rendered headings `862`, RGB/depth/metadata files `862/862/862`, unique scenes `10`, `uses_gt_for_action false`다. Strict no-blank-heading gate는 blank RGB `56/862`로 실패했지만, dropped rows는 `0`이고 `nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl`은 `112` rows / `806` headings로 row-level nonblank gate를 통과했다.
- Broader detector first launch `local_dataset/runs/h001_rival_identity_broader_detector_substrate_v1`은 filtered summary path-root mismatch 때문에 detector/SAM2/association rate `0.0`으로 gate 실패했다. Corrected job `local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2`는 detector box `1.0`, SAM2 mask `1.0`, candidate association `0.6339`, rows with association `71/112`, `uses_gt_for_action false`로 substrate gate를 통과했다.
- Broader post-observation analyzer `local_dataset/runs/h001_rival_identity_broader_post_observation_v1`은 safe but inert negative result다. Request/evidence/decision rows `30/112/30`, commit/success/wrong/no-label `0/0/0/0`, defer unresolved identity `26`, defer object-existence `4`, post-observation gate `false`다.
- Broader failure diagnostic `local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1`은 `post_observation_no_candidate_support`가 rule threshold 문제가 아니라 planner geometry 문제임을 확인했다. Plan rows `112` 모두 zero-standoff이고 rotation fallback이며, own associated rows `0`, cross associated rows `442`다.
- Zero-standoff-safe planner revision contract는 `manifests/h001_rival_identity_broader_standoff_planner_v1.json`에 정의됐다. It reuses `NavmeshSnapper` and `plan_standoff_viewpoint`, forbids zero-standoff fallback, and requires the geometry gate before rerunning frames/detector/analyzer.
- Zero-standoff-safe planner는 `runtime/h001_runtime/plan_rival_identity_observation.py`의 `--viewpoint-mode standoff`로 구현했고 Docker-smoke를 통과했다. Output `local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1`은 request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, scenes `10`, queries `6`, zero/near-standoff rows `0/0`, rotation/candidate fallback rows `0/0`, target distance min/mean/max `1.6386/1.7506/1.9747m`, viewpoint sources `standoff_navmesh 104` / `standoff_geometry 8`, `uses_gt_for_action false`, plan gate `true`, geometry gate `true`를 기록했다.
- Mixed standoff frame export `local_dataset/runs/h001_rival_identity_broader_frames_standoff_v1`은 `112/112` rows와 `1079` headings를 렌더링했지만 nonblank filter에서 `5` dropped rows가 발생해 row-level gate가 실패했다. Drop row는 모두 `standoff_geometry` fallback이고 `standoff_navmesh_navigable false`였다.
- Navmesh-only standoff repair는 `plan_rival_identity_observation.py --require-navmesh-standoff`로 구현했고 Docker-smoke를 통과했다. Plan output `local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1`은 planned request rows `28/30`, plan rows `104`, skipped rows `8` all `standoff_navmesh_required`, scenes `9`, queries `6`, viewpoint sources `standoff_navmesh 104`, `uses_gt_for_action false`다. Frame output `local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1`은 `104/104` rows, `997` headings, nonblank kept `104/104`, blank/dropped rows `0/0`, row-level and strict no-blank gates `true`다.
- Navmesh-only standoff detector/SAM2 substrate는 `local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1`에서 통과했다. Detector rows `104`, detector box rate `0.9808`, SAM2 mask rate `0.9808`, candidate association rate `0.7212`, rows with association `75`, associated heading count `277`, `uses_gt_for_action false`다.
- Fixed post-observation analyzer는 `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1`에서 실패했다. Request/evidence/decision rows `28/110/28`, commit/success/wrong/no-label `7/0/7/0`, unsafe commit queries `bed 4`, `chair 2`, `tv_monitor 1`이다.
- Unsafe-commit diagnostic은 `runtime/h001_runtime/diagnose_rival_identity_unsafe_commits.py`와 `local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1`에 기록했다. Semantic-rank, detector-score, depth-consistency, own-count simple guards는 wrong-goal commit을 만들고, safe combined simple guard는 commit `0`으로 inert라서 threshold-only repair는 reject한다.
- Stricter arbitration design contract는 `manifests/h001_rival_identity_strict_arbitration_v1.json`에 freeze했다. Contract name은 `rival_identity_goal_validity_arbitration_v1`이고, candidate-set validity, local semantic/geometric consistency, rival-contrast stage를 요구한다.
- `goal_validity_arbitration_v1`은 `analyze_rival_identity_post_observation.py --objective goal_validity_arbitration_v1`로 구현했다. Output `local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1`은 commit/success/wrong/no-label `2/2/0/0`, post-observation gate `true`, `uses_gt_for_action false`다. 단, 같은 broader split에서 진단과 설계를 했으므로 paper claim은 아직 허용하지 않는다.
- `rival_identity_goal_validity_independent_v1` source는 `v3_fresh_validation`에서 prior diagnostic 및 broader diagnostic scene을 제외해 freeze했다. Manifest `manifests/h001_rival_identity_goal_validity_independent_v1.json`과 verify `manifests/h001_rival_identity_goal_validity_independent_v1.verify.json`이 생성됐고, verify는 `ok true`, request rows `30`, scenes `10`, queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, action evidence forbidden key count `0`, `uses_gt_for_action false`를 기록했다.
- `rival_identity_goal_validity_independent_v1` substrate는 plan/frame/detector gate를 통과했다. Plan rows `92`, frame headings `810`, detector box/SAM2/candidate association `1.0/1.0/0.6196`, `uses_gt_for_action false`다.
- Independent `goal_validity_arbitration_v1` rerun은 safe but inert negative result다. Output `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1`은 request/evidence/decision rows `30/101/30`, commit/success/wrong/no-label `0/0/0/0`, safety gate pass, utility gate fail을 기록했다.
- Default counterfactual on the same independent evidence is nontrivial but unsafe: `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1` has commit/success/wrong/no-label `7/4/3/0`.
- Independent failure diagnostic `local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1` rejects threshold-only repair. Dominant tags are `cross_view_aliasing_blocks_goal_validity 14`, `planned_candidate_set_has_no_valid_goal 13`, `no_own_candidate_support 11`, and `strong_identity_not_goal_validity 8`.
- Revision contract `manifests/h001_rival_identity_goal_validity_revision_v2.json` and router output `local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1` route unresolved requests into `request_discriminative_rival_view 14`, `request_expanded_retrieval 8`, `request_object_existence_confirmation 6`, and `request_goal_validity_confirmation 2`; terminal commit remains blocked.
- Branch-specific contract `manifests/h001_discriminative_rival_view_planner_v1.json` is defined for the largest branch. It requires contrastive focus-rival pair views, explicit pair candidate ids, no GT/post-join action inputs, and plan/frame/detector/evaluation gates.
- Plan smoke `local_dataset/runs/h001_discriminative_rival_view_plan_v1` passes with source router rows `14`, planned request rows `14`, plan rows `38`, common pair view rows `10`, matched dual standoff rows `28`, zero/near-standoff `0/0`, rotation fallback `0`, and `uses_gt_for_action false`.
- v1 frame smoke exposed one blank geometry-only common pair row. v2 plan/frame outputs `local_dataset/runs/h001_discriminative_rival_view_plan_v2` and `local_dataset/runs/h001_discriminative_rival_view_frames_v2` pass with frame rows/headings `38/222`, dropped rows `0`, removed blank headings `0`, role counts `common 10`, `focus 14`, `rival 14`, and row-level plus strict no-blank gates `true`; detector/SAM2 substrate v2 completed at `local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2` with detector box/SAM2/candidate association `1.0/1.0/0.8158`.
- Evidence analyzer `runtime/h001_runtime/analyze_discriminative_rival_view_evidence.py` output `local_dataset/runs/h001_discriminative_rival_view_evidence_v1` fails: request rows `14`, evidence availability `1.0`, disambiguation `0.6429`, but single-correct pairs are all `rival_only_correct 3`, preferred-correct rate `0.0`, wrong-preference rate `0.3333`.
- Failure diagnostic `runtime/h001_runtime/diagnose_discriminative_rival_view_failure.py` output `local_dataset/runs/h001_discriminative_rival_view_failure_diagnostic_v1` blocks threshold tuning and fresh validation; dominant tags are `symmetric_cross_view_leak 7`, `rival_visible_from_focus_view 6`, `identity_score_near_tie 5`, `common_view_supports_both_candidates 5`, `no_valid_goal_pair_but_disambiguated 4`, and `rival_correct_own_view_evidence_weak 3`.
- Branch priority decision: do `request_expanded_retrieval` before another discriminative-view revision, because the failed branch often compares invalid/no-valid or non-discriminative candidate pairs.
- Contract `manifests/h001_expanded_retrieval_branch_v1.json` is frozen. It uses `request_expanded_retrieval` router rows, expected request rows `8`, candidate budget `6-10`, no GT/evaluation action inputs, no terminal commit, and candidate-set validity gates before detector/objective work.
- Expanded-retrieval planner smoke is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_plan_v1`: expected/request rows `8/8`, candidate-set rows `8`, plan rows `80`, candidates per request `10`, skipped rows `0`, duplicate candidate rate `0.0`, nonfinite position rate `0.0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- Expanded-retrieval candidate-set validity diagnostic is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_candidate_set_validity_v1`: label join gate passes with missing labels `0`; contains-correct `6/8`, no-valid `2/8`, source-top correct `1/8`, source-top wrong-goal `7/8`, wrong-top replacement `5/7`, and wrong-goal candidate present in `7/8`. Full-pool comparison gives taxonomy `source_pool_no_valid_candidate 2`, `valid_set_with_wrong_goal_distractor 5`, `valid_set_without_wrong_goal_distractor 1`.
- Expanded-retrieval candidate-set guard design is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1`: `request_backend_retrieval_revision 2`, `request_detector_guarded_observation 5`, `request_lightweight_confirmation 1`, detector evidence allowed `6/8`, terminal commit rows `0`, and `guard_design_gate_passed true`. It is analysis-only design and requires non-GT action-time proxies before paper-facing action claims.
- Expanded-retrieval proxy feature audit is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1`: feature extraction gate passes with forbidden action rows `0`, terminal commit rows `0`, and `uses_gt_for_action false`; current candidate-set score/support proxy routes all `8` rows to `request_detector_guarded_observation_proxy`, so source-pool validity proxy recall is `0.0` and `proxy_ready_for_detector_gate false`.
- Expanded-retrieval source-pool validity proxy is Docker-verified at `local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1`: proxy routes are `request_backend_retrieval_revision_proxy 2` and `request_detector_guarded_observation_proxy 6`, consumed forbidden rows `0`, source-pool validity proxy recall `1.0`, evidence-allowed target recall `1.0`, backend targets escalated to evidence `0`, evidence targets blocked as backend `0`, and `proxy_ready_for_detector_gate true`. This is diagnostic-only; paper claim remains blocked until fresh/predeclared validation.
- Google Drive 백업 후보와 Drive 없이 재생성하는 절차는 [reproducibility.md](reproducibility.md)의 `Google Drive Backup Manifest`, `Restore from Drive`, `Rebuild Without Drive`를 따른다.

### 에이전트 추론

Step 1-3은 ObjectNav first probe이고, Step 4-5는 같은 H001 안에서 SLAM uncertainty와 map/pose consistency 평가로 확장한다. Primary와 secondary-stress dense-conflict diagnostic은 positive signal이고, frozen generalization split의 recall 및 detector substrate도 통과했다. 하지만 independent terminal validation은 `strict_depth_consistency_v1`이 wrong instance를 막지 못한다는 negative result를 만들었다. `rival_identity_confirmation_v1`은 이 ambiguity를 active request로 바꾸는 local diagnostic이다. Fresh-source frame과 detector/SAM2 substrate도 통과했고, no-commit object-existence branch로 wrong-goal commit은 제거됐다. Independent object-existence probe는 현재 single-positive rows가 lost success가 아니라 avoided wrong-goal임을 확인했다. Broader source miner, corrected detector/SAM2 substrate, zero-standoff-safe planner, navmesh-only standoff frame/nonblank gate, and navmesh-only detector substrate까지 통과했다. 최신 diagnostic은 own-view category evidence가 valid `ObjectNav` goal identity로 충분하지 않다고 판정했고, `goal_validity_arbitration_v1`은 같은 broader split에서 diagnostic repair를 만들었다. 하지만 frozen independent source에서는 `0` commit으로 utility gate를 통과하지 못했다. Default counterfactual은 반대로 `7/4/3`이라 안전하지 않다. `discriminative_rival_view_planner_v1` v2는 frame/nonblank와 detector/SAM2 substrate를 통과했지만 evidence gate가 실패했다. Failure taxonomy도 threshold tuning을 막는다. `request_expanded_retrieval` planner, label-join diagnostic, guard design, proxy feature audit, and source-pool validity proxy는 통과했다. 이제 detector-eligible rows에 대한 frame/detector evidence gate를 설계하되, paper claim은 fresh/predeclared validation 전까지 허용하지 않는다.

## Entry Order

새 작업을 시작하는 에이전트는 아래 순서로 읽는다.

1. `../AGENTS.md`
2. `../TODO.md`
3. `index.md`
4. `literature.md`
5. `hypothesis.md`
6. `paper.md`
7. `reproducibility.md`
8. `../literature/README.md`
9. `../literature/PAPER.md`
10. `../literature/Contribution Candidates.md`
11. `../literature/CAND-01.md`
12. `../hypothesis/README.md`

## Update Rules

- 새 workflow 문서가 생기면 이 파일의 `Workflow Docs`에 추가한다.
- 새 연구 산출물 folder가 생기면 관련 workflow 문서와 이 index에서 함께 연결한다.
- 긴 설명, paper summary, experiment detail은 이 파일에 넣지 않는다.
- 아직 필요하지 않은 `experiments/`, `paper/`, `decisions/` folder는 만들지 않는다.
- 루트에는 `AGENTS.md`, `.gitignore`, `README.md`, `TODO.md`, `summary.md`만 둔다.

## Index Page Convention

### 사실

- Markdown documentation site에서는 `docs/index.md`를 documentation home page로 두는 관례가 있다.
- contents page는 포함하는 문서의 overview와 link를 제공하는 역할을 한다.
- navigation page는 관련 문서로 이동하기 위한 link 중심 문서다.

### 에이전트 추론

이 repo의 `docs/index.md`는 documentation site home, workflow router, current research direction pointer 역할만 한다. 실제 연구 내용은 `literature/`와 `hypothesis/` 아래에 둔다.
