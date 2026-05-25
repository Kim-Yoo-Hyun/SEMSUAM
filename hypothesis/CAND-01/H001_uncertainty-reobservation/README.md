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
- Current next implementation target: diagnose independent terminal validation failures and define a mechanism-level arbitration revision without threshold tuning on the failed split

## Latest Gate

### 사실

- Date checked: 2026-05-25
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
- Google Drive backup paths and no-Drive rebuild procedures are documented in `../../../docs/reproducibility.md`.
- Canonical local asset roots are `local_dataset/data`, `local_dataset/models`, and `local_dataset/runs`; `/tmp/research3-data`, `/tmp/research3-models`, and `/tmp/research3-runs` are compatibility symlinks.

### 에이전트 추론

The current method shape is more contribution-aligned than detector-based re-ranking because semantic uncertainty is being converted into an active observation request. It is still not paper-ready. The detector/association blocker is lifted for the selected primary and secondary diagnostic substrates, and the broader frozen split now passes candidate recall plus detector substrate. `strict_depth_consistency_v1` reproduced the same-split safety-positive result, but independent validation rejects it because wrong instances can still satisfy strict depth and support constraints. The next step is failure-row diagnosis and a mechanism-level arbitration revision, not threshold tuning on this failed split.

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
