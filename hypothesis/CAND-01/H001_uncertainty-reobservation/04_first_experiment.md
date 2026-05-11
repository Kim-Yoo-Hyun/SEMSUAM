# First Experiment

## Goal

Test the Step 1-3 portion of H001: whether semantic map object/node uncertainty can function as an active navigation utility that identifies goal candidates requiring re-observation before ObjectNav commitment.

## Minimal Probe

Use a small Habitat ObjectNav subset or one replayable indoor scene. Construct pre-explored semantic map candidates, assign uncertainty scores, and compare navigation decision quality with and without active re-observation.

This first experiment does not complete H001. It is the first falsification probe for the central claim that semantic uncertainty can drive useful robot mobility decisions before adding SLAM uncertainty and evaluating Step 4-5 metrics.

## Data

- Primary: Habitat ObjectNav with MP3D / HM3D subset
- Fallback: Replica / ScanNet one-scene replay
- Required annotations or proxies: object candidate correctness, candidate position, reachable viewpoints, path cost

## Metrics

- wrong-goal visit rate
- wasted path / extra path length
- `Success Rate`
- `SPL`
- object candidate precision / recall
- uncertainty calibration: confidence vs wrong-goal probability

## Extension Metrics After First Probe

- map error
- semantic accuracy
- ATE/RPE
- pose graph connectivity
- localization failure count

## Step 4-5 Extension Plan

### 사실

The extension is not a new hypothesis. It is the SLAM/map-side measurement gate for H001 after the Step 1-3 semantic re-observation probe.

### 에이전트 추론

Start with the lowest SLAM signal that can be measured reliably in the selected environment:

| Stage | Input proxy for viewpoint selection | Output metric |
| --- | --- | --- |
| Step 4a | tracking state, tracked feature count, inlier ratio, keyframe density | localization failure count, tracking loss count |
| Step 4b | pose graph connectivity, loop closure candidate count, graph `lambda2` / D-optimality proxy | pose graph connectivity before/after re-observation |
| Step 5 | pose covariance trace or full SLAM trajectory if available | `ATE`, `RPE`, map error, semantic accuracy |

The minimum acceptable Step 4-5 experiment compares `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` under the same navigation episodes and logs travel cost. Without travel cost, the result cannot distinguish useful re-observation from expensive over-exploration.

## Baselines

- `NoReobserve`: navigate to top semantic candidate directly
- `RandomReobserve`: re-observe from a random reachable nearby viewpoint
- `FrontierReobserve`: re-observe from geometry/frontier-driven reachable viewpoint
- `CARe-style`: use confidence to switch candidate or replan without explicit viewpoint optimization
- `GTTargetOracle`: shortest path to a valid target instance; upper-bound reference, not deployable baseline
- `GTCandidateOracle`: choose correct semantic candidate using GT if it exists in candidate set
- `GTViewOracle`: choose best re-observation viewpoint using ground-truth candidate correctness

## Extension Baselines After First Probe

- `SemanticOnly`: semantic uncertainty reduction only
- `SLAMOnly`: SLAM uncertainty reduction only
- geometry-only exploration
- `SemanticSLAM`: combined utility

## Success Criteria

- `NoReobserve`보다 wrong-goal visit rate가 감소한다.
- `NoReobserve`보다 wasted path가 감소한다.
- `SPL` drop이 re-observation cost 때문에 과도하지 않다.
- uncertainty score가 wrong-goal probability와 measurable correlation을 가진다.
- `RandomReobserve`보다 failure decomposition metric에서 개선된다.
- GT oracle과의 gap을 보고 candidate ranking error와 navigation policy error를 분리한다.

## Failure Interpretation

- If uncertainty does not predict wrong-goal visits: semantic confidence signal이 부적절하거나 map error type이 hypothesis와 다르다.
- If wrong-goal visits decrease but `SPL` drops: re-observation utility에 travel cost arbitration이 부족하다.
- If random re-observation matches the proposed method: viewpoint selection objective가 contribution이 아니다.
- If only synthetic perturbation works: real semantic map error model을 다시 조사해야 한다.

## Stage 1 Smoke Result

### 사실

- Date checked: 2026-05-07
- Docker command path: `sg docker`
- Docker image: `research3/vlmaps-smoke:20260507`
- Base image: `python:3.8-slim`
- `VLMaps` repo: `vlmaps/vlmaps`, `demo` branch, commit `bc79b26a577e5a9408f86e45e5c16530ca80f867`
- Demo scene: `5LpN3gDmAk7_1`
- Host data cache: `/tmp/research3-data/vlmaps`, about 12G
- Lightweight import checks passed: `utils.time_utils`, `utils.mp3dcat`, `examples.context`
- Full map-creation utility import is not covered by this minimal image: `utils.clip_mapping_utils` currently needs missing runtime dependency `cv2`

The smoke test inspected the following `VLMaps` demo scene files:

| Item | Result |
| --- | --- |
| `rgb` / `depth` / `pose` / `semantic` frames | 1159 each |
| `map_correct` files | 5 |
| `color_top_down_1.npy` | 1000 x 1000 x 3, `uint8` |
| `grid_lseg_1.npy` | 1000 x 1000 x 512, `float32` |
| `obstacles.npy` | 1000 x 1000, `uint8` |

### 에이전트 추론

The `VLMaps` demo scene is sufficient for the next local probe: extracting object/node uncertainty features from precomputed semantic map artifacts. It is not sufficient for full `VLMaps` map creation / object-goal evaluation or final ObjectNav metrics yet because the minimal image does not install all `VLMaps` runtime dependencies and MP3D/HM3D mount paths are still unresolved.

### 사용자 판단 필요

- Confirm MP3D/HM3D scene data access and Docker mount path for benchmark episodes.
- Decide whether the first uncertainty probe should start from `VLMaps` demo artifacts or wait for Habitat ObjectNav scene mount.

## Dataset Gate Result

### 사실

- Date checked: 2026-05-07
- Check method: Docker read-only mount through `sg docker`
- Checked mounts: `/home`, `/home/yoohyun`, `/tmp/research3-data`
- Existing Docker dataset path: `/datasets/vlmaps`
- Missing Docker dataset paths: `/datasets/mp3d`, `/datasets/hm3d`, `/datasets/scene_datasets/mp3d`, `/datasets/scene_datasets/hm3d`
- MP3D/HM3D scene files such as `.glb`, `.navmesh`, `.habitat` were not found under the checked local paths.

### 에이전트 추론

Habitat ObjectNav benchmark metrics are blocked until MP3D/HM3D scene assets are provided. This does not block a first uncertainty probe on precomputed `VLMaps` demo artifacts, but it does block claims about `SR`, `SPL`, wrong-goal visit, and wasted path on Habitat ObjectNav.

### 사용자 판단 필요

- Provide MP3D/HM3D host path, or continue with Replica / ScanNet one-scene replay fallback.

## HM3D Gate Update

### 사실

- Date checked: 2026-05-07
- Check method: Docker read-only mount through `sg docker`
- Host data root: `/tmp/research3-data`
- HM3D path in container: `/data/scene_datasets/hm3d`
- ObjectNav HM3D v2 path in container: `/data/datasets/objectnav/hm3d/v2`
- ObjectNav episode files: 186 `json.gz`
- HM3D split availability through Docker mount:

| Split | basis `.glb` | basis `.navmesh` | semantic `.glb` | semantic `.txt` |
| --- | ---: | ---: | ---: | ---: |
| `train` | 800 | 800 | 145 | 145 |
| `val` | 100 | 100 | 36 | 36 |
| `minival` | 10 | 10 | 4 | 4 |

### 에이전트 추론

Habitat ObjectNav on HM3D is now usable as the primary first-probe data path, subject to runtime integration. Replica / ScanNet fallback remains useful for one-scene replay and debugging, but it is no longer needed to unblock dataset access.

## HM3D-OVON Gate Update

### 사실

- Date checked: 2026-05-07
- Check method: Docker read-only mount through `sg docker`
- Source: HM3D-OVON episode archive from Hugging Face `nyokoyama/hm3d_ovon`
- Host path: `/tmp/research3-data/datasets/ovon/hm3d`
- Container path: `/data/datasets/ovon/hm3d`
- Total episode files: 257 `json.gz`

| Split | total `json.gz` | content `json.gz` | sample content episode count |
| --- | ---: | ---: | ---: |
| `train` | 146 | 145 | 50000 |
| `val_seen` | 37 | 36 | 95 |
| `val_unseen` | 37 | 36 | 121 |
| `val_seen_synonyms` | 37 | 36 | 98 |

### 에이전트 추론

HM3D-OVON is now available as the open-vocabulary extension path for H001. This is more directly aligned with semantic candidate uncertainty than MP3D because query ambiguity and candidate ranking uncertainty are central to the benchmark.

The first implementation can still start from closed-vocabulary ObjectNav HM3D v2 if runtime complexity is lower, then use HM3D-OVON to test whether the same uncertainty utility holds under open-vocabulary queries.

## Runtime Gate Summary

### 사실

- `habitat-h001` runtime image was built and smoke-tested.
- Fixed manifest rows were evaluated with an aligned non-GT `VLMaps` artifact.
- `GTTargetOracle` is separated from `artifact_jsonl`.
- `artifact_jsonl` records `candidate_backend_uses_gt_for_action = false`.

### 에이전트 추론

The evaluator interface is usable. Larger claims remain blocked by semantic candidate coverage and ambiguity coverage, not by basic runtime loading.

## Candidate Coverage Results

### 사실

- Early aligned artifact had candidates but they were not reachable from selected smoke starts.
- Anchor32 retry produced 32 frames from four low-floor smoke start anchors.
- Anchor32 `VLMaps` map verification passed.
- Anchor32 aligned artifact contained 20 candidates across `bed`, `chair`, `plant`, and `sofa`.
- Top non-GT candidates were reachable from all four smoke starts.
- `NoReobserve` produced `Success Rate = 0.25` and `wrong_goal_visit_rate = 0.75` on the Anchor32 smoke subset.

### 에이전트 추론

Anchor32 was enough to validate a reachable wrong-candidate substrate, but it was smoke evidence only because the subset was anchor-selected and too small for paper claims.

## Active Re-observation Smoke

### 사실

- Implemented policy: `SemanticOnly`
- Runtime module: `runtime/h001_runtime/run_smoke.py`
- Trigger: `U_sem >= 0.60`
- Tie band: `0.01`
- Action selection does not use GT candidate labels or GT target ids.
- Anchor32 output: `/tmp/research3-runs/h001_semanticpolicy_anchor_smoke`
- On Anchor32 smoke subset, `SemanticOnly` reduced wrong-goal visit rate from `0.75` to `0.50` versus `NoReobserve`.

### 에이전트 추론

The active re-observation mechanism is implemented and smoke-tested. It is not yet paper-facing evidence because calibration coverage and held-out evaluation are still required.

## Uncertainty Validity Smoke

### 사실

- Analysis script: `runtime/h001_runtime/analyze_uncertainty.py`
- Analysis output: `/tmp/research3-runs/h001_semanticpolicy_anchor_smoke/uncertainty_validity_noreobserve.json`

| Metric | Value |
| --- | ---: |
| candidates analyzed | 20 |
| failure labels | 16 |
| `AUROC` | 0.828 |
| `AUPRC` | 0.953 |
| Spearman `U_sem` vs failure | 0.455 |
| high-vs-low failure-rate gap | 0.500 |

### 에이전트 추론

`U_sem` passed the Anchor32 smoke sanity gate. The same validity check must be repeated on calibration data before promotion.

## Sensitivity Smoke Result

### 사실

- Sweep output: `/tmp/research3-runs/h001_semanticpolicy_sensitivity`
- Aggregated summary: `/tmp/research3-runs/h001_semanticpolicy_sensitivity/sensitivity_summary.json`
- Sweep grid: 12 `SemanticOnly` parameter settings.
- Pass count: 6 / 12.
- Provisional parameters:
  - `semantic_uncertainty_trigger = 0.60`
  - `semantic_tie_band = 0.01`
  - `semantic_reobs_view_bonus = 1`

### 에이전트 추론

The sweep is sufficient to move from Anchor32 smoke to calibration split work, but not sufficient for a paper claim.

## Calibration Coverage Result

### 사실

- `random128_v1` artifact: `/tmp/research3-runs/h001_calibration_artifacts_v1/all_scenes_aligned.jsonl`
- Structural check passed: 30 rows, 150 candidates, 5 scenes, 6 queries, all map verifications `ok = true`.
- Coverage output: `/tmp/research3-runs/h001_calibration_policy_v1/coverage_sanity/artifact_coverage.json`
- Failed hard gate: too few episodes contained both a reachable correct candidate and a reachable wrong candidate.

### 에이전트 추론

`random128_v1` is structurally valid but fails the ambiguity coverage gate. `SemanticOnly` policy comparison remains blocked until recovery coverage passes.

## Coverage Recovery Status

### 사실

- Recovery artifact id: `random256_v1`
- Background process: `tmux`
- Session: `h001-calib-artifacts-random256-20260509-233124`
- Output root: `/tmp/research3-runs/h001_calibration_artifacts_random256_v1`
- Job status file: `/tmp/research3-runs/h001_calibration_artifacts_random256_v1/job_status.json`
- Log: `runtime/logs/calibration-artifacts-random256-20260509-233124.log`
- Completion status: `completed`
- Completion verification date: 2026-05-10
- Structural verification passed:
  - `rows = 30`
  - `candidate_count = 150`
  - `finite_position_candidates = 150`
  - scenes = `HkseAnWCgqk`, `XYyR54sxe6b`, `oEPjPNSPmzL`, `qk9eeNeR4vw`, `vLpv2VX547B`
  - queries = `bed`, `chair`, `plant`, `sofa`, `toilet`, `tv_monitor`
  - each scene has `export/export_summary.json`, `verify_map.json`, `aligned.jsonl`, and `artifact_summary.json`

### 에이전트 추론

The generation step is complete and structurally valid. The next gate is evaluator coverage sanity. Do not run `NoReobserve` / `RandomReobserve` / `SemanticOnly` calibration policy comparison until coverage passes.

## Random256 Coverage Sanity Result

### 사실

- Date checked: 2026-05-10
- Candidate artifact: `/tmp/research3-runs/h001_calibration_artifacts_random256_v1/all_scenes_aligned.jsonl`
- Coverage sanity output: `/tmp/research3-runs/h001_calibration_policy_random256_v1/coverage_sanity`
- Coverage sanity log: `runtime/logs/calibration-random256-coverage-sanity-20260510-143038.log`
- Artifact coverage log: `runtime/logs/calibration-random256-artifact-coverage-20260510-143058.log`
- Summary file: `/tmp/research3-runs/h001_calibration_policy_random256_v1/coverage_sanity/summary.json`
- Artifact coverage file: `/tmp/research3-runs/h001_calibration_policy_random256_v1/coverage_sanity/artifact_coverage.json`

Structural and baseline checks:

| Check | Result | Gate |
| --- | ---: | --- |
| episodes loaded | 50 | expected 50 |
| candidate backend uses GT for action | false | required false |
| candidates per episode | 5.0 mean | non-empty |
| candidate label coverage | 1.0 | pass, `>= 0.70` |
| `GTTargetOracle` success rate | 1.0 | reference OK |
| `NoReobserve` wrong-goal visit rate | 0.28 | pass, `>= 0.10` |
| reachable correct-and-wrong ambiguity rate | 0.26 | fail, required `>= 0.50` |

Scene-level reachable correct-and-wrong rates:

| Scene | Rate |
| --- | ---: |
| `HkseAnWCgqk` | 0.0 |
| `XYyR54sxe6b` | 0.5 |
| `oEPjPNSPmzL` | 0.6 |
| `qk9eeNeR4vw` | 0.0 |
| `vLpv2VX547B` | 0.2 |

### 에이전트 추론

`random256_v1` improves neither the hard ambiguity coverage enough nor the weakest scenes enough to unblock policy comparison. The artifact is structurally valid and creates a wrong-goal stress signal, but it still does not contain enough episodes where both a reachable correct target candidate and a reachable wrong semantic candidate are available. Running `SemanticOnly` now would overfit to incomplete candidate-set coverage rather than test active re-observation arbitration.

Do not tune `SemanticOnly` thresholds on this failed coverage result. The next step should be a recovery decision note comparing candidate budget increase, scene replacement, and candidate backend revision.

## Coverage Failure Decision Note

### 사실

- Date checked: 2026-05-10
- Failed artifacts: `random128_v1`, `random256_v1`
- `random256_v1` structural artifact generation passed.
- `random256_v1` candidate label coverage passed: `1.0`.
- `random256_v1` `NoReobserve` wrong-goal stress passed: `wrong_goal_visit_rate = 0.28`.
- Failed hard gate: reachable correct-and-wrong ambiguity rate = `0.26`, required `>= 0.50`.
- Current candidate budget: `MAX_CANDIDATES = 5` per scene/query.
- Current candidate count per episode: min `5`, mean `5.0`, max `5`.
- Weak scenes:
  - `HkseAnWCgqk`: reachable correct-and-wrong rate `0.0`
  - `qk9eeNeR4vw`: reachable correct-and-wrong rate `0.0`
  - `vLpv2VX547B`: reachable correct-and-wrong rate `0.2`
- Passing or near-passing scenes:
  - `XYyR54sxe6b`: reachable correct-and-wrong rate `0.5`
  - `oEPjPNSPmzL`: reachable correct-and-wrong rate `0.6`

### 논문 주장

- ObjectNav behavior metrics are meaningful only when the candidate set contains plausible correct and wrong choices.
- Active re-observation should be evaluated on the same episode ids and same non-GT candidate artifacts across policies.

### 에이전트 추론

The failure is not a basic runtime failure. The evaluator loads 50 episodes, labels candidates, and produces a strong enough `NoReobserve` wrong-goal prior. The failure is narrower: the candidate artifact does not expose enough reachable correct candidates together with reachable distractors.

Candidate budget increase is the least confounded next recovery because it keeps:

- the same calibration scenes;
- the same fixed episode ids;
- the same pre-exploration trajectories;
- the same non-GT generation policy;
- the same `TOP_PERCENTILE = 98.0`;
- the same policy parameters.

Scene replacement can improve coverage, but it changes the calibration distribution after seeing coverage results. That is acceptable only as a later predeclared recovery if a budget-only retry fails.

Candidate backend revision is likely needed eventually for robustness, especially if weak scenes remain weak after increasing budget. However, changing extraction logic now would mix two changes at once: candidate count and candidate scoring / selection.

### Decision

Next recovery path: create a candidate-budget retry.

Recommended run:

```text
artifact_id: random256_k10_v1
FRAMES: 256
MAX_CANDIDATES: 10
TOP_PERCENTILE: 98.0
scenes: same calibration scenes
queries: same six closed-class queries
trajectory policy: same random navigable pre-exploration
policy thresholds: unchanged
```

### Rejected For Now

| Option | Decision | Reason |
| --- | --- | --- |
| Scene replacement | defer | changes calibration scene distribution after seeing coverage; use only if budget retry fails |
| Candidate backend revision | defer | higher implementation risk and changes scoring / extraction logic; use after isolating budget effect |
| `SemanticOnly` threshold tuning | reject | would tune policy on a failed coverage substrate |
| Policy comparison on `random256_v1` | reject | hard validity gate failed |

### Next Gate

Launch the `random256_k10_v1` candidate-budget recovery job using the run contract in `08_runtime_integration.md`. If it fails:

1. write a second decision note;
2. compare reachability-diverse backend revision against scene replacement;
3. keep `SemanticOnly` policy comparison blocked until hard coverage passes.

### 사용자 판단 필요

No user decision is required before launching the `random256_k10_v1` recovery job. User decision is needed if the budget retry also fails and the study must choose between scene replacement and candidate backend revision.

## Random256 K10 Coverage Decision Tree

### 사실

- Date written: 2026-05-10
- Applicable artifact: `random256_k10_v1`
- This decision tree must be applied after artifact generation, structural verification, coverage sanity, and artifact coverage analysis.
- The policy comparison remains blocked until the hard validity gate in `07_evaluation_contract.md` passes.
- `random256_k10_v1` changes only `MAX_CANDIDATES` from `5` to `10`; it does not change scenes, queries, trajectory policy, `FRAMES`, `TOP_PERCENTILE`, alignment, or policy thresholds.

Required inputs:

```text
job_status.json
coverage_check.json
all_scenes_aligned.jsonl
coverage_sanity/summary.json
coverage_sanity/artifact_coverage.json
per-scene export_summary.json
per-scene verify_map.json
per-scene aligned.jsonl
per-scene artifact_summary.json
```

### 논문 주장

- Active re-observation should be compared only when the candidate set exposes plausible correct and wrong options.
- Calibration runs can diagnose substrate validity and tune provisional gates, but they should not be treated as held-out paper evidence.

### 에이전트 추론

The next decision should separate four possible failure causes:

| Cause | Observable signal | Interpretation |
| --- | --- | --- |
| generation failure | missing files, failed `job_status`, invalid `coverage_check` | runtime/artifact generation issue |
| budget ineffective | candidate count does not increase beyond `random256_v1` or many queries still have fewer than 6 candidates | candidate extraction is saturated or too sparse |
| reachability failure | candidates exist but reachable correct / wrong candidates are missing | scene/trajectory/navmesh alignment or candidate placement issue |
| ambiguity failure | reachable candidates exist but few episodes contain both correct and wrong candidates | selected scene/query/episode substrate is weak for wrong-goal evaluation |

### Decision Tree

| Result after `random256_k10_v1` | Decision | Next action |
| --- | --- | --- |
| structural verification fails | reject artifact | fix runtime/export/alignment issue before any policy run |
| `candidate_backend_uses_gt_for_action != false` | reject artifact | fix backend provenance before any policy run |
| `candidate_label_coverage < 0.70` | reject artifact | inspect label mapping and query/category normalization |
| `NoReobserve` wrong-goal visit rate `< 0.10` | reject as weak stress test | select stronger ambiguity scenes/queries before policy comparison |
| reachable correct-and-wrong rate `>= 0.50` | pass substrate gate | run calibration policy comparison with `GTTargetOracle`, `NoReobserve`, `RandomReobserve`, `SemanticOnly` |
| reachable correct-and-wrong rate `0.40-0.50` and at least 4 / 5 scenes have nonzero ambiguity | borderline pass for diagnostic only | run policy comparison as diagnostic, but do not promote to paper-facing evidence without evaluation split confirmation |
| reachable correct-and-wrong rate `0.40-0.50` with 2 or more zero-ambiguity scenes | fail | prefer scene replacement over threshold tuning |
| reachable correct-and-wrong rate `< 0.40` and candidate count increased | fail | compare scene replacement against reachability-diverse candidate backend |
| reachable correct-and-wrong rate `< 0.40` and candidate count did not increase | fail | revise candidate extraction before replacing scenes |

### Next Action If Pass

Run the predeclared policy comparison command in `08_runtime_integration.md`.

Keep these constants fixed:

```text
semantic_uncertainty_trigger: 0.60
semantic_tie_band: 0.01
semantic_reobs_view_bonus: 1
manifest_split: calibration
episodes: 50
candidate_artifact: random256_k10_v1/all_scenes_aligned.jsonl
```

After the policy comparison, interpret only:

- direction and magnitude of `wrong_goal_visit_rate`;
- `mean_wasted_path_wrong_goal`;
- `mean_wasted_path_total`;
- `Success Rate`;
- `SPL`;
- oracle gap between `GTTargetOracle`, `NoReobserve`, and `SemanticOnly`.

Use the policy comparison interpretation template in `07_evaluation_contract.md`. Do not use calibration results as final paper evidence.

### Next Action If Fail

Write a second decision note before changing implementation.

The second decision note must choose one primary recovery:

| Recovery | Choose when | Not allowed when |
| --- | --- | --- |
| scene replacement | candidate budget works but ambiguity is scene/episode sparse | candidate count did not increase or alignment is broken |
| reachability-diverse backend revision | candidates exist but are poorly distributed or unreachable | structural generation is broken |
| query/category revision | wrong-goal stress is weak because selected categories are too easy or rare | candidate labels are unreliable |
| trajectory revision | candidates are concentrated around poor pre-exploration coverage | `VLMaps` map generation or alignment is unstable |

Rejected after failure:

- tuning `SemanticOnly` threshold on a failed substrate;
- reporting policy comparison as evidence;
- switching to evaluation split before calibration substrate passes;
- changing multiple factors at once without a decision note.

### 사용자 판단 필요

No user decision is required if `random256_k10_v1` clearly passes or clearly fails by the table above. User decision is required only for borderline diagnostic runs or if the next recovery changes the study scope, such as replacing scenes versus revising the candidate backend.

## Random256 K10 Coverage and Diagnostic Result

### 사실

- Date checked: 2026-05-11
- Candidate artifact: `/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_aligned.jsonl`
- Coverage sanity output: `/tmp/research3-runs/h001_calibration_policy_random256_k10_v1/coverage_sanity`
- Diagnostic policy output: `/tmp/research3-runs/h001_calibration_policy_random256_k10_v1/policy_comparison_diagnostic`
- Coverage sanity log: `runtime/logs/calibration-random256-k10-coverage-sanity-20260511-010532.log`
- Artifact coverage log: `runtime/logs/calibration-random256-k10-artifact-coverage-20260511-010633.log`
- Diagnostic policy log: `runtime/logs/calibration-random256-k10-policy-comparison-diagnostic-20260511-010704.log`

Coverage checks:

| Check | Result | Gate |
| --- | ---: | --- |
| candidate backend uses GT for action | false | required false |
| candidates per episode | 10.0 mean | non-empty |
| candidate label coverage | 1.0 | pass, `>= 0.70` |
| `NoReobserve` wrong-goal visit rate | 0.36 | pass, `>= 0.10` |
| reachable correct-and-wrong ambiguity rate | 0.48 | fail, required `>= 0.50` |
| overall hard coverage pass | false | required true |

Scene-level reachable correct-and-wrong rates:

| Scene | Rate |
| --- | ---: |
| `HkseAnWCgqk` | 0.0 |
| `XYyR54sxe6b` | 0.6 |
| `oEPjPNSPmzL` | 0.8 |
| `qk9eeNeR4vw` | 0.2 |
| `vLpv2VX547B` | 0.8 |

Diagnostic policy comparison:

| Policy | `Success Rate` | `SPL` | `wrong_goal_visit_rate` | `mean_wasted_path_wrong_goal` | `mean_wasted_path_total` |
| --- | ---: | ---: | ---: | ---: | ---: |
| `GTTargetOracle` | 1.00 | 1.000 | 0.00 | 0.000 | 0.000 |
| `NoReobserve` | 0.28 | 0.165 | 0.36 | 3.834 | 7.530 |
| `RandomReobserve` | 0.26 | 0.080 | 0.36 | 3.260 | 15.280 |
| `SemanticOnly` | 0.30 | 0.182 | 0.50 | 4.445 | 6.688 |

### 논문 주장

- This diagnostic run is not paper-facing evidence because the hard coverage gate failed.
- Active re-observation should reduce wrong-goal commitment and wasted path, not only improve `Success Rate` or `SPL`.

### 에이전트 추론

The budget increase worked mechanically: candidate count rose from 5 to 10 per episode and `NoReobserve` wrong-goal stress increased to `0.36`. However, the hard ambiguity gate still failed narrowly at `0.48`. The failure is now concentrated in scene-level reachability and ambiguity, especially `HkseAnWCgqk` and `qk9eeNeR4vw`.

The diagnostic policy result is negative for the current `SemanticOnly` policy: it improves `Success Rate`, `SPL`, and total wasted path slightly versus `NoReobserve`, but increases `wrong_goal_visit_rate` from `0.36` to `0.50` and increases wrong-goal wasted path. This does not support the H001 mechanism.

### Decision

Do not promote `random256_k10_v1` to paper-facing first-probe evidence.

Next required step: write a second recovery decision note. The decision note should compare:

- scene replacement, because 4 / 5 scenes now have nonzero ambiguity but weak scenes dominate the hard gate;
- reachability-diverse candidate backend revision, because the current top candidate reachability remains weak in some scenes;
- policy objective revision, because `SemanticOnly` re-observation did not reduce wrong-goal visits even under a borderline diagnostic substrate.

Rejected now:

- held-out evaluation run;
- Step 4-5 promotion;
- `SemanticOnly` threshold tuning without a recovery decision note;
- reporting the diagnostic policy comparison as evidence.

## Second Recovery Decision Note

### 사실

- Date checked: 2026-05-11
- Failed hard gate: `random256_k10_v1` reachable correct-and-wrong ambiguity rate = `0.48`, required `>= 0.50`.
- `random256_k10_v1` candidate budget worked mechanically:
  - candidates per episode: `10.0`
  - candidate label coverage: `1.0`
  - `NoReobserve` wrong-goal visit rate: `0.36`
- Weak scene-level ambiguity:
  - `HkseAnWCgqk`: `0.0`
  - `qk9eeNeR4vw`: `0.2`
- Passing scene-level ambiguity:
  - `XYyR54sxe6b`: `0.6`
  - `oEPjPNSPmzL`: `0.8`
  - `vLpv2VX547B`: `0.8`
- Diagnostic policy result:
  - `NoReobserve` wrong-goal visit rate: `0.36`
  - `SemanticOnly` wrong-goal visit rate: `0.50`
  - `SemanticOnly` selected a re-observation candidate in 40 / 50 episodes.
  - `SemanticOnly` changed the final candidate in 28 / 40 re-observation episodes.
  - `SemanticOnly` fixed 2 `NoReobserve` wrong-goal cases but introduced 9 new wrong-goal cases.

### 논문 주장

- A valid first-probe policy comparison requires a candidate set with reachable correct and reachable wrong candidates.
- Active semantic re-observation should reduce wrong-goal commitment, not merely increase reachability or `Success Rate`.

### 에이전트 추론

The current blocker has two layers:

1. Substrate blocker: the coverage gate failed narrowly, with failure concentrated in two weak scenes.
2. Policy blocker: the current `SemanticOnly` objective often changes the committed candidate to a reachable tied candidate, which increases wrong-goal visits.

These should not be fixed in the same run. Changing scenes, candidate extraction, and policy objective together would make the next result hard to interpret.

### Ranked Recovery Options

| Rank | Option | Likelihood | Why | Risk |
| ---: | --- | --- | --- | --- |
| 1 | scene replacement | high for coverage gate | failure is concentrated in `HkseAnWCgqk` and `qk9eeNeR4vw`; the other three scenes already pass or exceed the ambiguity gate | does not fix the negative `SemanticOnly` policy behavior |
| 2 | policy objective revision | high for wrong-goal behavior, medium for overall progress | diagnostic logs show current `SemanticOnly` changes final candidate too often and introduces wrong-goal visits | cannot be validated as evidence until the substrate gate passes |
| 3 | reachability-diverse backend revision | medium-high for robustness, lower as immediate next step | would address weak top-candidate reachability and candidate spatial distribution | changes the semantic candidate backend and may confound the contribution with extraction engineering |

### Decision

First recovery to run: scene replacement.

Rationale:

- It is the least invasive way to resolve the current hard gate.
- It keeps the candidate backend, policy code, query set, candidate budget, `FRAMES`, `TOP_PERCENTILE`, and thresholds fixed.
- It directly targets the observed failure mode: weak scene-level reachable correct-and-wrong ambiguity.
- It can determine whether the negative diagnostic policy result persists on a valid substrate.

Default scene replacement rule for the next run:

```text
keep: XYyR54sxe6b, oEPjPNSPmzL, vLpv2VX547B
replace: HkseAnWCgqk, qk9eeNeR4vw
replacement source: HM3D train scenes not used in held-out evaluation
selection rule: predeclare replacement scenes before policy comparison; do not use policy outcomes
artifact goal: same 5 scenes, same 6 queries, FRAMES=256, MAX_CANDIDATES=10
```

Second recovery to prepare in parallel as design only: policy objective revision.

Policy issue to fix after coverage substrate is valid:

```text
current behavior: if top candidate is uncertain, choose nearest reachable candidate within score tie-band and commit to it
observed failure: final candidate changes often and wrong-goal visits increase
required revision: re-observation should gather evidence about uncertainty, not simply replace the goal with the nearest tied candidate
```

Possible policy revision directions:

- re-observe the uncertain top candidate but keep final commitment unchanged unless a new evidence update changes ranking;
- separate viewpoint selection from goal candidate selection;
- add a commit gate after re-observation instead of always committing to the re-observed candidate;
- include predicted semantic-gain and wrong-goal risk, not only reachability and score tie-band.

Reachability-diverse backend revision is deferred until after scene replacement unless the replacement run still fails coverage. It is the right next step if replacement scenes also show weak top-candidate reachability or reachable correct candidates remain sparse.

### Next Gate

Launch the scene replacement recovery artifact generation job using the run contract in `08_runtime_integration.md`.

The contract must specify:

- replacement scene ids and seeds: done;
- artifact id: done;
- output path: done;
- exact Docker/background command: done;
- expected files: done;
- structural verification command: done;
- coverage sanity command: done;
- decision rule before policy comparison: done.

Run contract summary:

```text
artifact_id: random256_k10_sr1_v1
manifest: manifests/h001_splits_sr1.json
scene_specs: manifests/sr1_scenes.txt
replacement_scenes: 1S7LAXRdDqK, 1UnKg1rAb8A
kept_scenes: XYyR54sxe6b, oEPjPNSPmzL, vLpv2VX547B
launch_status: running
session: h001-calib-artifacts-random256-k10-sr1-20260511-115330
completion_status: completed and structurally verified
rows: 30
candidate_count: 300
finite_position_candidates: 300
next_step: coverage sanity and artifact coverage gate
```

Coverage sanity result:

```text
date_checked: 2026-05-11
coverage_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/coverage_sanity
candidate_label_coverage: 1.0
episodes_with_reachable_correct_and_wrong_rate: 0.66
required_reachable_correct_and_wrong_rate: 0.50
NoReobserve_wrong_goal_visit_rate: 0.38
GTTargetOracle_success_rate: 1.0
overall_pass: true
next_step: run current `SemanticOnly` unchanged before implementing revised policy objective
```

Policy comparison result on recovered substrate:

```text
date_checked: 2026-05-11
policy_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_comparison
policies: GTTargetOracle, NoReobserve, RandomReobserve, SemanticOnly
candidate_backend_uses_gt_for_action: false
GTTargetOracle_success_rate: 1.00
NoReobserve_success_rate: 0.24
NoReobserve_SPL: 0.153
NoReobserve_wrong_goal_visit_rate: 0.38
NoReobserve_mean_wasted_path_wrong_goal: 3.061
RandomReobserve_success_rate: 0.20
RandomReobserve_SPL: 0.074
RandomReobserve_wrong_goal_visit_rate: 0.44
SemanticOnly_success_rate: 0.30
SemanticOnly_SPL: 0.215
SemanticOnly_wrong_goal_visit_rate: 0.54
SemanticOnly_mean_wasted_path_wrong_goal: 3.853
SemanticOnly_reobservations: 44 / 50
SemanticOnly_final_candidate_changed: 29 / 44 re-observation episodes
SemanticOnly_fixed_NoReobserve_wrong_goal: 5
SemanticOnly_introduced_wrong_goal: 13
```

### 에이전트 추론

Scene replacement fixed the substrate, but it did not fix the policy mechanism. The current `SemanticOnly` still improves `Success Rate` and `SPL` while worsening wrong-goal behavior. This confirms the design note: the next policy work should not tune thresholds. It should change the objective so re-observation collects evidence and final candidate switching is gated by post-view non-GT evidence.

### 사용자 판단 필요

No user decision is required to choose the first recovery direction. User decision is needed only if the user wants to prioritize policy objective research over reaching a valid first-probe substrate.

## Policy Objective Revision Design Note

### 사실

- Date written: 2026-05-11
- Triggering evidence: `random256_k10_v1` diagnostic policy comparison.
- Current policy: `SemanticOnly`
- Current behavior:
  - compute `U_sem` for the top semantic candidate;
  - if `U_sem >= 0.60`, find reachable candidates within score tie-band `0.01`;
  - choose the closest reachable tied candidate as the re-observation target;
  - commit to that selected candidate.
- Observed diagnostic failure:
  - `SemanticOnly` changed the final candidate in 28 / 40 re-observation episodes;
  - `SemanticOnly` fixed 2 `NoReobserve` wrong-goal cases but introduced 9 new wrong-goal cases;
  - `wrong_goal_visit_rate` increased from `0.36` to `0.50` versus `NoReobserve`.

### 논문 주장

- Active re-observation should collect additional evidence before final commitment.
- A navigation utility must trade off semantic risk reduction against travel cost.
- Policy comparison is meaningful only after the candidate substrate passes the reachable correct-and-wrong coverage gate.

### 에이전트 추론

The current policy confounds two decisions:

1. where to move for re-observation;
2. which semantic candidate to commit to.

This is likely the direct cause of the negative diagnostic result. The policy is not verifying uncertainty; it is often replacing the goal with a nearby tied candidate before any new evidence is measured. That makes `SemanticOnly` closer to reachability-biased reranking than active semantic verification.

The revised objective should therefore be evidence-gated:

```text
select re-observation viewpoint != select final goal candidate
final candidate switch requires post-reobservation evidence change
```

### Revised Policy Target

Working name: `EvidenceGatedSemanticOnly`.

The policy should execute three separate stages:

| Stage | Decision | Allowed signals | Not allowed |
| --- | --- | --- | --- |
| 1 | trigger re-observation | `U_sem(top1)`, margin, support, reachability | GT candidate correctness |
| 2 | choose viewpoint | predicted semantic gain, visibility, travel cost | final goal switch by distance alone |
| 3 | commit or switch | post-reobservation score / uncertainty update | switching without evidence delta |

Core objective:

```text
J(v, c) =
  alpha * predicted_semantic_risk_reduction(c, v)
+ beta  * predicted_margin_gain(q, v)
- lambda * travel_cost(start, v)
- mu     * unsupported_switch_penalty
```

First default interpretation:

```text
predicted_semantic_risk_reduction = U_sem_before(c) - U_sem_after_pred(c, v)
predicted_margin_gain = margin_after_pred(q, v) - margin_before(q)
travel_cost = geodesic_distance(start, v)
unsupported_switch_penalty = 1 if the action changes final candidate without post-view evidence
```

### First Implementable Revision

Use a two-step policy before full online visual re-scoring is available:

1. `SemanticVerifyTop`
   - re-observe the current top candidate if it is uncertain;
   - do not switch final candidate only because another candidate is closer;
   - purpose: isolate re-observation cost and show whether the previous failure came from premature switching;
   - expected result: wrong-goal may match `NoReobserve`, but `final_candidate_changed` should drop to zero.

2. `EvidenceGatedSemanticOnly`
   - re-observe top candidate or top ambiguous pair;
   - update non-GT evidence after the view using available map/re-observation features;
   - switch final candidate only if all switch gates pass.

Switch gates:

```text
candidate_new is reachable
score_after(candidate_new) - score_after(candidate_old) >= delta_switch_score
U_sem_after(candidate_new) + delta_switch_uncertainty <= U_sem_after(candidate_old)
observed_support_after(candidate_new) > observed_support_before(candidate_new)
```

First calibration defaults:

```text
delta_switch_score: 0.03
delta_switch_uncertainty: 0.05
max_reobservations: 1 per episode
travel_cost_weight: choose on calibration split only
```

### Required Evidence Update

The policy is not paper-facing until the post-reobservation evidence update uses non-GT information. Acceptable first-probe evidence sources:

- local `VLMaps` / visual-language feature response from the selected viewpoint;
- visibility-weighted support change around candidate position;
- observation count / view diversity update tied to the selected viewpoint;
- semantic margin change computed from candidate scores after re-observation.

Not acceptable:

- using `candidate_correct`;
- using distance to GT target;
- switching candidates only because a tied candidate is closer;
- tuning `delta_switch_score` or `travel_cost_weight` on held-out `first_eval`.

### Evaluation Rule

Do not implement or evaluate the revised policy as evidence until `random256_k10_sr1_v1` passes the coverage gate.

After coverage passes, run in this order:

1. current `SemanticOnly` unchanged, to confirm whether the previous failure persists on the recovered substrate;
2. `SemanticVerifyTop`, to isolate premature switching;
3. `EvidenceGatedSemanticOnly`, to test the revised active semantic utility.

Minimum reporting:

| Metric | Required interpretation |
| --- | --- |
| `wrong_goal_visit_rate` | primary mechanism metric |
| `mean_wasted_path_wrong_goal` | wrong semantic commitment cost |
| `mean_wasted_path_reobserve` | cost of verification |
| `final_candidate_changed_rate` | detects premature switching |
| `switch_gate_pass_rate` | shows how often evidence supports candidate switch |
| `semantic_gain_pred` vs actual failure | validates utility signal |

### Failure Interpretation

| Result | Interpretation | Next action |
| --- | --- | --- |
| `SemanticVerifyTop` matches `NoReobserve` and adds cost | re-observation without evidence update is not enough | implement stronger post-view scoring |
| `SemanticVerifyTop` lowers wrong-goal | current failure was mostly premature switching | keep commit-stability gate |
| `EvidenceGatedSemanticOnly` lowers wrong-goal but hurts `SPL` | travel-cost arbitration is too weak | tune cost weight on calibration only |
| `EvidenceGatedSemanticOnly` matches `RandomReobserve` | viewpoint objective is not contributing | add visibility / semantic-gain model |
| all revised policies fail | current semantic artifact does not expose useful evidence for active verification | revise candidate backend before Step 4-5 |

### 사용자 판단 필요

No user decision is required before writing the implementation contract. User decision is needed only if the study should prioritize full online visual re-scoring before completing the scene replacement coverage gate.

## TODO

- [x] `CARe` code와 dataset requirement 확인
- [x] `VLMaps` code와 dataset requirement 확인
- [x] Docker daemon 접근 권한 해결: current shell은 `sg docker`로 실행 가능
- [x] `VLMaps` map output을 Docker smoke test로 생성하거나 demo data로 확인
- [x] Habitat ObjectNav MP3D / HM3D 접근 가능성 확인
- [x] MP3D / HM3D scene data 실제 접근 권한과 local path 확인: local scene asset 없음, benchmark gate blocked
- [x] HM3D scene assets와 ObjectNav HM3DSem-v0.2 episode Docker mount smoke test 통과
- [x] HM3D-OVON episode tarball Docker 확보 및 mount smoke test 통과
- [x] fallback용 Replica / ScanNet one-scene replay 후보 선정: see `03_feasibility.md`
- [x] semantic candidate uncertainty feature 정의: see `05_uncertainty_features.md`
- [x] wrong-goal visit과 wasted path logging format 정의: see `06_logging_schema.md`
- [x] top-tier evaluation contract 작성: see `07_evaluation_contract.md`
- [x] HM3D/HM3D-OVON runtime integration plan 작성: see `08_runtime_integration.md`
- [x] `NoReobserve`, `RandomReobserve`, `CARe-style`, `OracleView` baseline 구현 가능성 판단
- [x] Stage 1 smoke test 환경 결정: Docker 기반
- [x] Stage 1 Docker smoke test workflow 작성
- [x] Stage 1 Docker smoke test 실행: passed on `VLMaps` demo scene, 2026-05-07
- [ ] first probe success/failure threshold 수치화
- [ ] Full `VLMaps` runtime image 필요 여부 결정: map creation / object-goal evaluation을 first probe에 포함할지 판단
- [x] H001 first probe가 positive일 때 Step 4-5 SLAM uncertainty extension으로 확장할 조건 작성
- [x] Step 4-5에서 사용할 SLAM uncertainty proxy 후보 정의
- [x] ATE/RPE 또는 pose graph connectivity 측정 가능성 확인
- [x] Step 4 first proxy 선택: pose graph connectivity
- [x] Docker 환경에 SLAM tooling을 같은 image로 넣을지 별도 image로 둘지 결정: 별도 image
- [ ] 6개월-1년 연구 일정에서 first probe, SLAM extension, real-world validation 순서 작성
