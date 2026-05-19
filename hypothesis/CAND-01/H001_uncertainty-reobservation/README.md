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
- Current next implementation target: prepare full follow-up detector/evidence validation job for `ExternalCandidateFollowupObservation`

## Latest Gate

### 사실

- Date checked: 2026-05-18
- `risk_validation_v1` and `v3_fresh_validation_v1` candidate coverage gates pass with non-GT `artifact_jsonl` candidates.
- V4 external evidence on `risk_validation_v1` passes the current external evidence gate with `commit_rate 0.20`, `success_commit_rate 0.20`, and wrong-goal commit `0.00`.
- V4 routes unresolved semantic uncertainty into `request_identity_confirmation` and `request_expanded_retrieval`.
- `ExternalCandidateFollowupObservation` planner produced `28` `risk_validation_v1` follow-up rows with `0` skipped rows.
- Follow-up detector smoke passed on `4` rows with detector box rate `1.00`, SAM2 mask rate `1.00`, and candidate association rate `0.75`.
- Follow-up evidence analyzer smoke passed safety with wrong-goal/no-valid commit rates `0.00`, but full gate failed because strong depth-associated follow-up evidence rate was `0.00`.

### 에이전트 추론

The current method shape is more contribution-aligned than detector-based re-ranking because semantic uncertainty is being converted into an active observation request. It is still not paper-ready; the next gate is a full follow-up detector/evidence validation job before any `first_eval` replacement rerun or policy-scale comparison.

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
