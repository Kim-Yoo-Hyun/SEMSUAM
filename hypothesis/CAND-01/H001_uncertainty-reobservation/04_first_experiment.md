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

### Implementation Contract

The implementation contract is recorded in `08_runtime_integration.md`.

```text
new_policies: SemanticVerifyTop, EvidenceGatedSemanticOnly
first_mode: support_proxy
first_run_scope: calibration split only
next_code_target: runtime/h001_runtime/run_smoke.py
promotion_blocker: held-out `first_eval` remains blocked until revised policy passes calibration interpretation gate
```

SemanticVerifyTop implementation smoke:

```text
date_checked: 2026-05-11
runtime_file: runtime/h001_runtime/run_smoke.py
smoke_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/semantic_verify_top_smoke
episodes: 5
policies: GTTargetOracle, NoReobserve, SemanticVerifyTop
candidate_backend_uses_gt_for_action: false
SemanticVerifyTop_final_candidate_changed_rate: 0.0
SemanticVerifyTop_switch_gate_pass_rate: 0.0
viewpoint_rows: 5
required_switch_log_fields: present
interpretation: implementation smoke passed; full calibration policy revision waits for EvidenceGatedSemanticOnly
```

EvidenceGatedSemanticOnly support_proxy result:

```text
date_checked: 2026-05-11
policy_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision
episodes: 50
candidate_backend_uses_gt_for_action: false
GTTargetOracle_success_rate: 1.00
NoReobserve_wrong_goal_visit_rate: 0.38
SemanticOnly_wrong_goal_visit_rate: 0.54
SemanticVerifyTop_wrong_goal_visit_rate: 0.38
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 0.38
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.0
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.0
EvidenceGatedSemanticOnly_mean_U_sem_delta_after_reobserve: -0.0133
EvidenceGatedSemanticOnly_mean_travel_cost_to_reobserve: 5.625
switch_gate_reasons: no_reobserve, score_delta_failed
```

### 에이전트 추론

`EvidenceGatedSemanticOnly` with `support_proxy` fixed the harmful behavior of current `SemanticOnly`: it prevented unsupported candidate switching and brought wrong-goal behavior back to `NoReobserve`. However, it did not improve beyond `NoReobserve`, because support-only evidence does not change semantic scores or create a valid switch.

This is useful negative evidence. It suggests the next mechanism must add actual post-view visual-language re-scoring or visibility-conditioned semantic evidence. Without that, active re-observation is only a safety gate, not yet a contribution-level semantic utility.

Post-view visual-language re-scoring contract:

```text
date_written: 2026-05-11
contract: 08_runtime_integration.md
target_evidence_mode: image_feature
new_artifact_root: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1
new_required_modules: export_postview_frames.py, score_postview_vlm.py
policy_target: EvidenceGatedSemanticOnly with image_feature score artifact
promotion_blocker: support_proxy result only matches NoReobserve, so held-out first_eval remains blocked
```

Post-view frame export smoke:

```text
date_checked: 2026-05-11
module: runtime/h001_runtime/export_postview_frames.py
smoke_output: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1_smoke
rows_requested: 2
rows_exported: 2
expected_files: present
uses_gt_for_action: false
next_step: score_postview_vlm.py implementation
```

Post-view full calibration artifact scope decision:

```text
date_checked: 2026-05-12
decision: generate full calibration diagnostic artifact before any held-out evaluation
source_viewpoint_log: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl
rows: 50 EvidenceGatedSemanticOnly re-observation rows
scenes: 5 HM3D train scenes
queries: bed, chair, plant, sofa, toilet, tv_monitor
output_root: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1
expected_files: postview_frames.jsonl, postview_scores.jsonl, summary.json, frames/<decision_id>/*
score_source: openai_clip_local_crop
score_calibration: raw_clip_cosine
held_out_eval_status: blocked
next_step: launch full calibration frame export Docker job
```

### 에이전트 추론

The two-row `image_feature` policy smoke proves integration, not evidence quality. The full calibration artifact is needed to decide whether the current crop-based `raw_clip_cosine` signal has enough separation, whether projection quality is the blocker, or whether a different visual-language evidence source is required.

Post-view full calibration artifact completion:

```text
date_checked: 2026-05-12
frame_export: completed
vlm_scoring: completed
output_root: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1
postview_frames_rows: 50
postview_scores_rows: 50
candidate_score_count: 263
visible_scores: 127
visible_row_rate: 1.0
finite_visible_scores: true
projection_status_counts: visible 127, out_of_fov 57, behind_camera 79
score_source_counts: openai_clip_local_crop 83, openai_clip_center_crop_fallback 44, not_used 136
score_calibration: raw_clip_cosine
raw_clip_cosine_visible_range: 0.1720 to 0.2455
raw_clip_cosine_visible_mean: 0.2083
uses_gt_for_action: false
next_step: image_feature score calibration diagnostic 설계
```

Image feature score calibration diagnostic design:

```text
date_checked: 2026-05-12
design_location: 08_runtime_integration.md
diagnostic_scope: calibration only
postview_scores: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
candidate_labels: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/candidate_decisions.jsonl
output_root: /tmp/research3-runs/h001_postview_score_calibration_random256_k10_sr1_v1
visible_candidate_scores_with_labels: 127
visible_correct_candidates: 41
visible_wrong_candidates: 86
precheck_pairwise_auc_correct_vs_wrong: 0.638
precheck_raw_clip_visible_top_correct_rows: 23 / 50
precheck_top_before_visible_correct_rows: 18 / 50
diagnostic_goal: choose raw_delta, query_zscore_delta, row_rank_delta, or defer before policy-scale comparison
uses_gt_for_action: false
uses_gt_for_analysis: true
held_out_eval_status: blocked
next_step: implement and run diagnostic script in Docker
```

### 에이전트 추론

The pre-check suggests `raw_clip_cosine` is not clearly strong enough to use as an absolute switch score. It may still be useful as a relative or query-normalized signal. The diagnostic should therefore compare raw, query-normalized, and rank-based evidence rules before any larger `image_feature` policy run.

Image feature score calibration diagnostic result:

```text
date_checked: 2026-05-12
script: runtime/h001_runtime/analyze_postview_scores.py
output_root: /tmp/research3-runs/h001_postview_score_calibration_random256_k10_sr1_v1
candidate_score_table_rows: 263
row_summary_rows: 50
threshold_sweep_rows: 35
decision_gate: needs_calibrated_or_rank_evidence
correct_vs_wrong_auc: 0.638
visible_top1_correct_rate_when_correct_visible: 0.793
rank_improvement_over_top_before: +5 rows
collapsed_query_count_auc_lt_0_55: 3
best_rule: raw_delta
best_threshold: 0.0
best_switch_count: 12 / 50
best_beneficial_switch_count: 5
best_harmful_switch_count: 0
best_selected_correct_rate: 0.46
top_before_correct_rate: 0.36
uses_gt_for_action: false
uses_gt_for_analysis: true
next_step: image_feature evidence rule decision
```

### 에이전트 추론

This diagnostic is enough to avoid using raw CLIP score as an absolute confidence. A conservative relative rule, `raw_delta >= 0.0`, is the strongest current candidate for calibration policy comparison, but per-query instability means the next decision should explicitly choose between implementing this fixed rule and deferring for a stronger scorer.

Image feature evidence rule decision:

```text
date_checked: 2026-05-12
decision: implement `raw_delta >= 0.0` as the first fixed image_feature evidence rule
scope: calibration policy-scale comparison only
held_out_eval_status: blocked
selected_evidence_rule: raw_delta
selected_threshold: 0.0
postview_uncertainty_gate_used: false
reason: CLIP raw crop score is useful as relative evidence but not calibrated enough for U_sem_after action gating
required_visibility: top_before and candidate_new must both have visible post-view scores
required_support: support_delta(candidate_new) > 0
required_reachability: candidate_new reachable
diagnostic_best_switch_count: 12 / 50
diagnostic_beneficial_switch_count: 5
diagnostic_harmful_switch_count: 0
next_step: implement explicit raw_delta rule in `run_smoke.py`
```

### 에이전트 추론

This is a pragmatic calibration-only step. The evidence is not stable enough to claim a final semantic confidence model, but it is strong enough to test whether active re-observation can improve the navigation failure logs when the visual evidence rule is fixed before the next policy run.

Selected image_feature evidence rule implementation:

```text
date_checked: 2026-05-12
runtime_file: runtime/h001_runtime/run_smoke.py
implemented_rule: raw_delta
implemented_threshold_cli: --semantic-delta-switch-score 0.0
implemented_uncertainty_gate_cli: --semantic-use-postview-uncertainty-gate false
smoke_output: /tmp/research3-runs/h001_postview_raw_delta_policy_smoke
smoke_episodes: 2
candidate_backend_uses_gt_for_action: false
semantic_postview_score_rows: 50
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.5
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.5
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 1.0
smoke_gate_reasons: passed, score_delta_failed
next_step: image_feature raw_delta policy-scale calibration Docker run
```

### 에이전트 추론

The smoke verifies mechanism, not performance. One of two episodes switched under the fixed raw-delta rule, so the next useful evidence is a 50-episode calibration policy run against `NoReobserve`, `SemanticVerifyTop`, and the support-proxy result.

Image feature raw_delta policy-scale calibration run:

```text
date_checked: 2026-05-12
output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision_image_feature_raw_delta
episodes: 50
candidate_backend_uses_gt_for_action: false
semantic_evidence_mode: image_feature
semantic_image_score_rule: raw_delta
semantic_delta_switch_score: 0.0
semantic_use_postview_uncertainty_gate: false
semantic_postview_score_rows: 50

NoReobserve_SR: 0.24
NoReobserve_SPL: 0.1531
NoReobserve_wrong_goal_visit_rate: 0.38

SemanticOnly_SR: 0.30
SemanticOnly_SPL: 0.2146
SemanticOnly_wrong_goal_visit_rate: 0.54

SemanticVerifyTop_SR: 0.24
SemanticVerifyTop_SPL: 0.1531
SemanticVerifyTop_wrong_goal_visit_rate: 0.38

EvidenceGatedSemanticOnly_raw_delta_SR: 0.26
EvidenceGatedSemanticOnly_raw_delta_SPL: 0.1690
EvidenceGatedSemanticOnly_raw_delta_wrong_goal_visit_rate: 0.38
EvidenceGatedSemanticOnly_raw_delta_switch_gate_pass_rate: 0.18
EvidenceGatedSemanticOnly_raw_delta_final_candidate_changed_rate: 0.18
gate_reasons: passed 9, score_delta_failed 12, no_reobserve 29
next_step: image_feature raw_delta calibration result interpretation
```

### 에이전트 추론

The raw-delta rule is active and safer than `SemanticOnly`, but the first policy-scale calibration result does not yet improve the primary wrong-goal metric over `NoReobserve` or `SemanticVerifyTop`.

### Image Feature Raw Delta Calibration Interpretation

#### 사실

```text
date_checked: 2026-05-12
scope: calibration split only
wrong_goal_fixed_vs_NoReobserve: 0 / 50
wrong_goal_newly_introduced_vs_NoReobserve: 0 / 50
success_fixed_vs_NoReobserve: 1 / 50
success_newly_failed_vs_NoReobserve: 0 / 50
selected_candidate_wrong_to_correct: 3
switch_gate_passed: 9 / 50
decision: do not promote to held-out evaluation yet
next_step: next evidence-source revision decision
```

#### 에이전트 추론

This result is partial mechanism evidence, not a validated contribution claim. The active post-view evidence gate is conservative enough to avoid `SemanticOnly`'s wrong-goal regression, but it does not yet attack the wrong-goal failures that define the H001 first-probe success criterion.

The next revision should target evidence quality before adding more evaluation scale. Candidate directions are stronger object-centered crops, multi-view aggregation, query-specific calibration, or a stronger open-vocabulary detector/segmenter evidence source.

### Evidence Source Revision Decision

#### 사실

```text
date_checked: 2026-05-12
NoReobserve_wrong_goal_rows: 19
wrong_goal_rows_with_visible_correct_candidate: 6 / 19
wrong_goal_rows_without_visible_correct_candidate: 13 / 19
raw_clip_top_correct_on_wrong_goal_rows: 0 / 19
```

#### 에이전트 추론

The next revision should be `postview_evidence_v2`: candidate-directed multi-heading / multi-crop post-view evidence with object-centered local crop aggregation. Pure threshold tuning is not enough because most wrong-goal rows do not expose a visible correct candidate under the current evidence artifact.

Action-facing center-crop fallback should be disabled in `postview_evidence_v2`; it may remain diagnostic only. `raw_delta` crop-only stays as an ablation baseline, not the main evidence source.

Next step: write the `postview_evidence_v2` implementation plan and Docker smoke contract before changing runtime behavior.

### Evidence Source Revision Implementation Plan

#### 사실

Detailed implementation plan is recorded in `08_runtime_integration.md`.

```text
target: postview_evidence_v2
physical_viewpoint_policy: keep current EvidenceGatedSemanticOnly re-observation position
new_visual_coverage: candidate-bearing headings with yaw offsets
new_action_score: aggregate local CLIP crop score
center_fallback_for_action: disabled
held_out_eval_status: blocked
raw_delta_crop_only_status: ablation baseline
```

#### 에이전트 추론

The first v2 implementation should isolate heading/FOV/crop evidence quality before changing travel behavior. If v2 improves wrong-goal evidence coverage but still does not reduce `wrong_goal_visit_rate`, the next bottleneck is viewpoint selection rather than the scorer.

First gate before another policy comparison:

```text
wrong_goal_rows_with_visible_correct_candidate > 6 / 19
aggregated_top_correct_on_wrong_goal_rows >= 1 / 19
center_fallback_used_for_action == 0
```

### Postview Evidence V2 Docker Smoke

#### 사실

```text
date_checked: 2026-05-12
frame_exporter: export_postview_frames_v2.py
scorer: score_postview_v2.py
policy_rule: agg_local_delta
frame_smoke_rows: 2
rendered_heading_count: 17
score_smoke_rows: 2
candidate_score_count: 6
action_eligible_candidate_count: 5
valid_crop_count: 26
center_fallback_used_for_action: false
policy_smoke_episodes: 2
policy_smoke_switch_gate_pass_rate: 0.5
policy_smoke_gate_reasons: passed 1, top_not_visible 1
uses_gt_for_action: false
```

#### 에이전트 추론

The Docker smoke confirms that v2 evidence can be generated, scored, and loaded by the policy runner. It does not yet validate the research claim because the sample is only two episodes. The next useful step is a calibration diagnostic over all 50 calibration rows to test whether v2 increases visible-correct coverage and aggregated top correctness on wrong-goal rows.

### Postview Evidence V2 Diagnostic Implementation

#### 사실

```text
date_checked: 2026-05-13
script: analyze_postview_scores_v2.py
docker_smoke_output: /tmp/research3-runs/h001_postview_score_calibration_v2_smoke
score_rows: 2
candidate_score_rows: 6
threshold_sweep_rows: 35
action_eligible_row_rate: 1.0
center_fallback_used_for_action_count: 0
aggregated_top_correct_on_wrong_goal_rows: 1
decision_gate: needs_full_calibration_artifact
uses_gt_for_action: false
```

#### 에이전트 추론

The diagnostic script is implemented and smoke-tested. The result is not a calibration conclusion because it uses only two rows. The next step is full calibration `postview_evidence_v2` artifact generation, followed by the same diagnostic on all 50 rows.

### Postview Evidence V2 Full Calibration Artifact Job

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-postview-v2-fullcalib
job_script: runtime/jobs/postview_v2_fullcalib.sh
output_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
status_file: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1/job_status.json
log: logs/postview-evidence-v2-fullcalib-20260513-011329.log
status_at_launch_check: running, stage=scoring
```

#### 에이전트 추론

The full artifact job has been launched and should be verified before running the full v2 diagnostic. The diagnostic and policy-scale comparison remain blocked until the artifact reports `completed`.

### Postview Evidence V2 Full Artifact Verification

#### 사실

```text
date_checked: 2026-05-13
status: completed
output_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
frames_rows: 50
scores_rows: 50
rendered_heading_count: 388
candidate_score_count: 172
action_eligible_candidate_count: 64
action_eligible_row_rate: 0.56
valid_crop_count: 420
center_fallback_used_for_action: false
uses_gt_for_action: false
```

#### 에이전트 추론

The artifact is ready for full diagnostic analysis. The action-eligible row rate is below the planned `0.70` gate, so the diagnostic should focus on whether v2 still improves wrong-goal-row correct visibility enough to justify policy comparison.

### Postview Evidence V2 Full Diagnostic Result

#### 사실

```text
date_checked: 2026-05-13
output_root: /tmp/research3-runs/h001_postview_score_calibration_v2_random256_k10_sr1_v1
decision_gate: fails_v2_calibration_diagnostic_gate
score_rows: 50
candidate_score_rows: 172
action_eligible_row_rate: 0.56
correct_vs_wrong_auc: 0.4968
wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19
center_fallback_used_for_action_count: 0
best_agg_local_delta_selected_correct_rate: 0.36
best_agg_local_delta_top_before_correct_rate: 0.36
best_agg_local_delta_beneficial_switches: 2
best_agg_local_delta_harmful_switches: 2
```

#### 에이전트 추론

The full v2 diagnostic fails the calibration gate. This is useful negative evidence: removing center fallback makes the evidence more principled, but action-facing visibility becomes too sparse and the aggregate CLIP score is not discriminative enough.

Do not run policy-scale comparison for `postview_evidence_v2`. The next step should be a visibility/depth ablation plan before policy work: `position` vs `visit_position`, strict vs relaxed depth diagnostics, and depth mismatch distribution by query/correctness.

### Postview Evidence V2.1 First Ablation Plan

#### 사실

The v2 reference artifact is complete, but the diagnostic gate failed:

```text
reference_artifact: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
reference_diagnostic: /tmp/research3-runs/h001_postview_score_calibration_v2_random256_k10_sr1_v1
action_eligible_row_rate: 0.56
correct_vs_wrong_auc: 0.4968
wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19
baseline_wrong_goal_visible_correct: 6 / 19
depth_mismatch projections: 60
out_of_fov projections: 38
```

#### 에이전트 추론

The next experiment should not change the policy objective yet. It should first test whether the failed gate is caused by the visual anchor (`position` vs `visit_position`), the strict depth check, or the CLIP local-crop signal itself.

#### Plan

1. Analyze existing v2 scores for `depth_error_m` distribution by query and candidate correctness.
2. Run `relaxed_position`: same frames and `position`, but `--no-strict-depth-check`.
3. Run `strict_visit`: same frames and strict depth, but `--candidate-point-field visit_position`.
4. Run `relaxed_visit` only if the first two variants show plausible coverage recovery.
5. Re-export wider-heading frames only if `out_of_fov` remains the dominant failure after point/depth ablation.

#### Gate

Policy-scale comparison is still blocked until a variant reaches:

```text
center_fallback_used_for_action_count == 0
action_eligible_row_rate >= 0.70
wrong_goal_rows_with_action_eligible_correct_candidate >= 6 / 19
correct_vs_wrong_auc > 0.55
beneficial_switch_count > harmful_switch_count
```

Paper-facing promotion should require `correct_vs_wrong_auc >= 0.60` and a positive `selected_correct_rate` delta over `top_before_correct_rate`.

### Postview Evidence V2.1 Lightweight Diagnostic Result

#### 사실

```text
date_checked: 2026-05-13
script: runtime/h001_runtime/analyze_postview_visibility_v2.py
log: logs/postview-evidence-v2-1-visibility-diagnostic-20260513-081009.log
output_root: /tmp/research3-runs/h001_postview_visibility_v2_1_random256_k10_sr1_v1
score_rows: 50
candidate_visibility_rows: 344
heading_visibility_rows: 3198
```

Coverage summary:

```text
position + strict depth:
  action_eligible_row_rate: 0.56
  wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19

position + relaxed depth:
  action_eligible_row_rate: 0.80
  wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19

visit_position + strict depth:
  action_eligible_row_rate: 0.12
  wrong_goal_rows_with_action_eligible_correct_candidate: 2 / 19

visit_position + relaxed depth:
  action_eligible_row_rate: 0.60
  wrong_goal_rows_with_action_eligible_correct_candidate: 7 / 19
```

#### 에이전트 추론

The highest-probability next implementation is `relaxed_position` rescoring. It isolates the strict-depth bottleneck while preserving the same candidate anchor and viewpoint policy. `strict_visit` should not be prioritized because its action coverage collapses.

This result is not yet evidence that the policy will improve. It only says the candidate can be visually scored more often if strict depth is relaxed. The next gate is whether rescored CLIP evidence under `relaxed_position` has better correct-vs-wrong separation and beneficial switch behavior.

### Postview Evidence V2.1 Relaxed Position Rescoring Launch

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-postview-v2-1-relaxed-position
job_script: runtime/jobs/postview_v2_1_relaxed_position.sh
output_root: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1
status_file: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/job_status.json
log: logs/postview-evidence-v2-1-relaxed-position-20260513-082406.log
status_at_launch_check: running
stage_at_launch_check: scoring
```

#### 에이전트 추론

The job changes only the depth gate from strict to relaxed while keeping `candidate_point_field=position` and disabling action-facing center fallback. The next task is completion verification, followed by the existing v2 calibration diagnostic on the rescored artifact.

Completion verification:

```text
date_checked: 2026-05-13
status: completed
scores_rows: 50
action_eligible_row_rate: 0.80
candidate_score_count: 172
action_eligible_candidate_count: 124
center_fallback_used_for_action: false
uses_gt_for_action: false
```

### Postview Evidence V2.1 Relaxed Position Diagnostic Result

#### 사실

```text
date_checked: 2026-05-13
log: logs/postview-evidence-v2-1-relaxed-position-diagnostic-20260513-122828.log
output_root: /tmp/research3-runs/h001_postview_score_calibration_v2_1_relaxed_position_random256_k10_sr1_v1
decision_gate: fails_v2_calibration_diagnostic_gate
action_eligible_row_rate: 0.80
wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19
correct_vs_wrong_auc: 0.4939
best_sweep_rule: row_rank_delta
best_sweep_selected_correct_rate: 0.40
best_sweep_top_before_correct_rate: 0.36
best_sweep_beneficial_switches: 4
best_sweep_harmful_switches: 2
```

#### 에이전트 추론

`relaxed_position` fixes coverage but not score discriminativeness. The current local CLIP crop signal should not be promoted to policy-scale comparison because the correct-vs-wrong score separation is random and wrong candidates have slightly higher mean aggregate score than correct candidates.

`relaxed_visit` is deferred. It had lower lightweight coverage (`0.60`) than `relaxed_position`, and the current result says the next bottleneck is the visual evidence source. The next research step should be a `postview_evidence_v3` scorer revision, likely object-level / segmentation-aware evidence rather than another depth-only ablation.

### Postview Evidence V3 Scorer Revision Plan

#### 사실

The latest diagnostic shows a scorer bottleneck:

```text
v2.1 relaxed_position action_eligible_row_rate: 0.80
v2.1 relaxed_position correct_vs_wrong_auc: 0.4939
v2.1 relaxed_position wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
v2.1 relaxed_position aggregated_top_correct_on_wrong_goal_rows: 4 / 19
```

Local CLIP crops are not discriminating correct and wrong candidates.

#### 논문 주장

`CARe` uses object-mask visible-view CLIP features and multi-view consistency for pre-explored semantic map replanning. `OVO-SLAM` uses segment-level open-vocabulary descriptors in an online semantic SLAM pipeline. `ConceptGraphs` uses object-centric RGB-D mask nodes and visual descriptors for open-vocabulary planning.

#### 에이전트 추론

The next scorer should move from point-centered local crops to object-level evidence. The first implementation should be `v3a_depth_mask`: use existing RGB-D post-view frames to build a local depth-connected object mask around the projected candidate point, score the masked object crop, and compare it against the current v2/v2.1 crop score.

This keeps the diagnostic cheap and isolated:

```text
no new dataset
no new checkpoint
same 50-row calibration split
same candidate_point_field=position
same relaxed depth visibility
no center fallback for action
```

#### First V3A Gate

Do not run policy-scale comparison unless `v3a_depth_mask` satisfies:

```text
score_rows == 50
object_mask_valid_row_rate >= 0.60
action_eligible_row_rate >= 0.70
correct_vs_wrong_auc > 0.58
wrong_goal_rows_with_action_eligible_correct_candidate >= 6 / 19
aggregated_top_correct_on_wrong_goal_rows > 4 / 19
beneficial_switch_count > harmful_switch_count
selected_correct_rate - top_before_correct_rate >= 0.06
```

#### Next Implementation Shape

```text
script: runtime/h001_runtime/score_postview_v3_depth_mask.py
input_scores_reference: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1
diagnostic_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1
```

If `v3a_depth_mask` improves score separation, the paper-facing follow-up is detector + segmenter evidence such as `GroundingDINO` / `OWL-ViT` with `SAM` / `SAM2`, plus multi-view descriptor consistency.

### Postview Evidence V3A Docker Smoke Result

#### 사실

```text
date_checked: 2026-05-13
script: runtime/h001_runtime/score_postview_v3_depth_mask.py
log: logs/postview-evidence-v3a-depth-mask-smoke-20260513-130424.log
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_smoke
rows_scored: 2
candidate_score_count: 10
action_eligible_candidate_count: 9
action_eligible_row_rate: 1.0
object_mask_valid_row_rate: 1.0
valid_mask_count: 31
debug_images_written: 20
center_fallback_used_for_action: false
uses_gt_for_action: false
```

Diagnostic smoke:

```text
log: logs/postview-evidence-v3a-depth-mask-diagnostic-smoke-20260513-130605.log
output_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_smoke
score_rows: 2
candidate_score_rows: 10
correct_vs_wrong_auc: 0.5
decision_gate: passes_v2_calibration_diagnostic_gate
```

#### 에이전트 추론

The smoke verifies implementation and analyzer compatibility only. The `decision_gate` is not meaningful because it uses two rows and relaxed smoke thresholds. The next task is a full 50-row calibration artifact and diagnostic run, preferably as a background Docker job.

### Postview Evidence V3A Full Calibration Launch

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-postview-v3a-fullcalib
job_script: runtime/jobs/postview_v3a_depth_mask_fullcalib.sh
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1
diagnostic_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1
status_file: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/job_status.json
log: logs/postview-evidence-v3a-depth-mask-fullcalib-20260513-132125.log
status_at_launch_check: running
stage_at_launch_check: scoring
```

#### 에이전트 추론

The job will produce both the 50-row v3a score artifact and the calibration diagnostic. Do not run policy-scale comparison while this job is running. The next task is completion verification and result interpretation.

Completion verification:

```text
date_checked: 2026-05-13
status: completed
score_rows: 50
diagnostic_score_rows: 50
action_eligible_row_rate: 0.80
object_mask_valid_row_rate: 0.80
debug_images_written: 240
uses_gt_for_action: false
center_fallback_used_for_action: false
```

### Postview Evidence V3A Full Calibration Interpretation

#### 사실

```text
decision_gate: fails_v2_calibration_diagnostic_gate
correct_vs_wrong_auc: 0.5598
wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19
rank_improvement_over_top_before: 7
best_sweep_rule: agg_local_delta
best_sweep_threshold: 0.0
best_sweep_selected_correct_rate: 0.48
best_sweep_top_before_correct_rate: 0.36
best_sweep_beneficial_switches: 8
best_sweep_harmful_switches: 2
```

Compared with `v2.1 relaxed_position`:

```text
AUC: 0.4939 -> 0.5598
selected_correct_delta: +0.04 -> +0.12
beneficial_switches: 4 -> 8
harmful_switches: 2 -> 2
wrong-goal aggregated top correct: 4 / 19 -> 4 / 19
```

#### 에이전트 추론

`v3a_depth_mask` is promising but not enough. It improves the score signal and switch sweep, but it does not improve the wrong-goal recovery metric that matters for the first ObjectNav hypothesis. Policy-scale comparison and held-out evaluation remain blocked.

The next useful step is not another policy run. It is a `v3b/v3c` feasibility check for detector + segmentation evidence, because the depth-mask scorer suggests object-level evidence helps but depth connectivity alone is not reliable enough for cluttered categories such as `bed`, `sofa`, and `chair`.

### Postview Evidence V3B / V3C Feasibility Result

#### 사실

Date checked: 2026-05-13.

Current runtime cannot execute detector/SAM smoke without additional packages and checkpoints:

```text
transformers: missing
segment_anything: missing
sam2: missing
groundingdino: missing
local OWL-ViT checkpoint: not found
local GroundingDINO checkpoint: not found
local SAM/SAM2 checkpoint: not found
```

Available in the current image:

```text
torch, torchvision, clip, cv2, PIL, numpy
```

#### 논문 주장 / 공식 문서 주장

`GroundingDINO` supports image-text open-set detection. `SAM2` supports promptable object segmentation in images and videos. `OWL-ViT` is available through Hugging Face `transformers` for open-vocabulary object detection.

#### 에이전트 추론

The next executable step requires a separate detector/segmenter environment. Do not add these dependencies to the Habitat runtime image. Keep v3b/v3c as a separate `openvocab-perception` image so ObjectNav/Habitat reproducibility stays stable.

Recommended order:

```text
1. v3b_owlvit_box smoke
2. v3c_groundingdino_sam2 smoke if v3b is promising or box-only evidence remains too noisy
3. full calibration only after 2-row smoke passes box/mask association gates
```

Proceeding requires user approval for model/package downloads.

### OpenVocab Perception OWL-ViT Setup Launch

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-openvocab-owlvit-setup
dockerfile: runtime/Dockerfile.openvocab-perception
job_script: runtime/jobs/openvocab_perception_owlvit_setup.sh
image: research3/openvocab-perception:20260513-owlvit
model_id: google/owlvit-base-patch32
model_dir: /tmp/research3-models/openvocab/owlvit/google_owlvit-base-patch32
status_file: /tmp/research3-runs/openvocab_perception_owlvit_setup/job_status.json
log: logs/openvocab-perception-owlvit-setup-20260513-142201.log
status_at_launch_check: running
stage_at_launch_check: build_image
```

#### 에이전트 추론

This starts the separate perception image path. The Habitat runtime remains unchanged. After the setup verifies offline `OWL-ViT` loading, the next implementation target is a 2-row `v3b_owlvit_box` smoke.

### V3B OWL-ViT Box Smoke Result

#### 사실

The `openvocab-perception` setup job completed and offline `OWL-ViT` loading passed.

```text
image: research3/openvocab-perception:20260513-owlvit
model_dir: /tmp/research3-models/openvocab/owlvit/google_owlvit-base-patch32
offline_load: OwlViTProcessor / OwlViTForObjectDetection passed
```

Implemented script:

```text
runtime/h001_runtime/detect_postview_owlvit_box.py
schema_version: h001.postview_detector.v3b_owlvit_box
```

2-row smoke results:

```text
default query, threshold 0.05, position:
  detector_box_rate: 0.50
  candidate_association_rate: 0.00

query_template "a photo of a {query}", threshold 0.01, position:
  detector_box_rate: 1.00
  candidate_association_rate: 0.50
  associated_candidate_heading_count: 6

query_template "a photo of a {query}", threshold 0.01, visit_position:
  detector_box_rate: 1.00
  candidate_association_rate: 0.00
```

Output roots:

```text
/tmp/research3-runs/h001_postview_detector_v3b_owlvit_box_smoke
/tmp/research3-runs/h001_postview_detector_v3b_owlvit_box_template_smoke
/tmp/research3-runs/h001_postview_detector_v3b_owlvit_box_template_visit_smoke
```

#### 에이전트 추론

`OWL-ViT` box-only evidence is feasible but not yet experiment-ready. The prompt template fixes detector recall on the tiny smoke set, but candidate association remains below the minimum smoke gate and is sensitive to the candidate point field.

Do not promote `v3b_owlvit_box` to full calibration. The next technically stronger path is `v3c_groundingdino_sam2`, where detector boxes are converted into object masks before semantic candidate association and scoring.

#### 사용자 판단 필요

Proceeding to `v3c_groundingdino_sam2` requires another separate perception setup step with additional packages and checkpoints. This should stay outside the Habitat runtime image.

### V3C GroundingDINO + SAM2 Setup Launch

#### 사실

The next setup decision after `v3b_owlvit_box` gate failure is to proceed with detector+mask evidence.

```text
date_launched: 2026-05-13
tmux_session: h001-openvocab-v3c-setup
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
dockerfile: runtime/Dockerfile.openvocab-perception-v3c
job_script: runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh
GroundingDINO model: IDEA-Research/grounding-dino-tiny
SAM2 checkpoint: sam2.1_hiera_tiny.pt
status_file: /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup/job_status.json
log: logs/openvocab-perception-v3c-groundingdino-sam2-20260513-204258.log
status_at_launch_check: running
stage_at_launch_check: build_image
```

#### 에이전트 추론

This setup targets the next falsification path: if detector boxes plus SAM2 masks still cannot associate with semantic candidates on the same 2-row smoke, the bottleneck is likely candidate geometry / semantic artifact quality rather than visual object segmentation alone. If the mask association passes, the next step is a small calibration run before policy-scale comparison.

### V3C Setup Verification

#### 사실

```text
date_checked: 2026-05-14
status: completed
stage: verified
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
CPU verification log: logs/openvocab-perception-v3c-groundingdino-sam2-cpu-verify-20260514-000244.log
cuda_available: false
GroundingDINO: GroundingDinoProcessor / GroundingDinoForObjectDetection offline load passed
SAM2: SAM2ImagePredictor offline load passed
```

#### 에이전트 추론

The setup gate is cleared without GPU execution. The next smoke should remain CPU-only and limited to the same 2-row post-view subset used for v3b, so any difference is attributable to detector+mask evidence rather than a new dataset slice.

### V3C Detector+Mask CPU Smoke Result

#### 사실

Implemented:

```text
runtime/h001_runtime/detect_postview_groundingdino_sam2.py
```

CPU-only smoke results:

```text
lite top-1:
  output: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_cpu_smoke_lite
  log: logs/postview-evidence-v3c-groundingdino-sam2-cpu-smoke-lite-20260514-001222.log
  rows: 2
  detector_box_rate: 1.00
  sam2_mask_rate: 1.00
  candidate_association_rate: 0.00

top-3:
  output: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_cpu_smoke_top3
  log: logs/postview-evidence-v3c-groundingdino-sam2-cpu-smoke-top3-20260514-001410.log
  rows: 2
  max_headings_per_frame: 2
  max_detector_boxes_per_heading: 3
  max_masks_per_heading: 3
  detector_box_rate: 1.00
  sam2_mask_rate: 1.00
  candidate_association_rate: 1.00
  associated_candidate_heading_count: 4
  uses_gt_for_action: false
```

#### 에이전트 추론

`v3c_groundingdino_sam2` passes the tiny detector+mask smoke when top-3 boxes/masks are retained. This is stronger than the `v3b_owlvit_box` result because candidate association is based on projected candidate points inside SAM2 masks, plus depth agreement. However, it is still a tiny probe; the next step is not policy-scale comparison but a 50-row calibration run contract with compute budget limits.

### Related Representation Papers Checked

#### 사실

```text
LAMP: Implicit Language Map for Robot Navigation
venue/status: IEEE Robotics and Automation Letters, 2025 / arXiv 2026
link: https://lab-of-ai-and-robotics.github.io/LAMP/
arXiv: https://arxiv.org/abs/2602.11862

Memory-Efficient Voxelized Renderable Neural 3D Spatial Representation for Vision-Based Robotics
method shorthand: 3DSR
venue/status: IEEE Robotics and Automation Letters, 2026
DOI: https://doi.org/10.1109/LRA.2025.3632118
```

#### 논문 주장

`LAMP` proposes an implicit neural language field for memory-efficient language-driven navigation, with sparse graph planning, gradient-based fine goal pose refinement, and embedding uncertainty modeling.

`3DSR` proposes a voxelized 3D Gaussian splatting representation for memory-efficient renderable spatial memory and reports applicability to visual localization and navigation.

#### 에이전트 추론

`LAMP` is directly relevant as related work and a future semantic memory baseline because H001 also studies language/semantic map uncertainty for navigation. H001's distinction is active re-observation and wrong-goal / wasted-path reduction rather than only language-map memory efficiency and goal pose refinement.

`3DSR` is indirectly relevant to Step 4-5 and real-world deploy. It could become a renderable spatial memory backend for candidate verification and localization/map consistency, but it is not the immediate first-probe baseline.

### V3C Calibration Run Contract

#### 사실

```text
scope: 50 calibration rows
device: cuda
GPU use: approved on 2026-05-14
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
input_frames: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
query_template: a photo of a {query}.
max_headings_per_frame: 2
max_detector_boxes_per_heading: 3
max_masks_per_heading: 3
candidate_point_field: position
box_threshold: 0.10
text_threshold: 0.10
job_script: runtime/jobs/postview_v3c_groundingdino_sam2_calib50.sh
output_root: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu
```

Prerequisite status checked on 2026-05-14:

```text
/tmp/research3-runs: recreated
/tmp/research3-data: recreated, HM3D restore running
/tmp/research3-models: v3c GroundingDINO / SAM2 restored
HM3D restore tmux: h001-hm3d-restore
HM3D restore status: running/download_hm3d
HM3D restore log: logs/hm3d-restore-20260514-111758.log
launch_status: blocked until HM3D, candidate artifact, policy log, and post-view frames are restored
```

#### 에이전트 추론

The 50-row calibration should be an artifact/diagnostic run only. It should not trigger policy-scale comparison until detector boxes, SAM2 masks, candidate-mask association, and wrong-goal row coverage pass the diagnostic gate. GPU approval solves the compute issue, but launch should wait until the `/tmp` dataset/model/run artifacts are restored or regenerated.

### V3C Calibration Result

#### 사실

```text
date_checked: 2026-05-15
job_status: failed at verification gate
output_root: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu
log: logs/postview-evidence-v3c-groundingdino-sam2-calib50-20260514-223034.log
rows: 50
uses_gt_for_action: false
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.30
wrong_goal_rows_with_candidate_association: 7 / 26
```

Query-level association:

```text
bed: 8 / 10
chair: 0 / 8
plant: 0 / 10
sofa: 4 / 10
toilet: 2 / 6
tv_monitor: 1 / 6
```

#### 에이전트 추론

`v3c_groundingdino_sam2` confirms that open-vocabulary detector boxes and SAM2 masks can be generated at calibration scale, but it fails as an action-facing scorer because candidate-mask association is too sparse and query-dependent. The next bottleneck is not mask generation but association geometry / prompt filtering / candidate point choice.

Do not run policy-scale comparison from this artifact. The next implementation should be a small association ablation before another 50-row GPU job:

```text
candidate revisions:
  object-phrase box filtering
  query-only prompt vs "a photo of a {query}."
  more candidate-directed headings
  visible/depth-mismatch split
  candidate point field or object extent proxy for chair/plant
```

Small ablation order:

```text
A1_query_only_prompt:
  query_template: "{query}"
  max_headings_per_frame: 2
  candidate_point_field: position

A2_more_headings:
  query_template: "{query}"
  max_headings_per_frame: 6
  candidate_point_field: position

A3_visit_position:
  query_template: "{query}"
  max_headings_per_frame: 6
  candidate_point_field: visit_position
```

Only promote to another 50-row v3c run if the small smoke reaches at least `0.50` candidate association rate and recovers nonzero association for `chair` or `plant`.

### V3C Association Ablation Smoke Progress

#### 사실

`A1_query_only_prompt` result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a1_query_only_smoke
rows: 12
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.50
uses_gt_for_action: false
query-level association:
  bed: 3 / 3
  chair: 0 / 3
  plant: 0 / 2
  sofa: 2 / 2
  toilet: 0 / 1
  tv_monitor: 1 / 1
```

`A2_more_headings` launched:

```text
date_launched: 2026-05-15
session: h001-v3c-a2-more-headings-smoke-20260515-001233
log: logs/postview-evidence-v3c-a2-more-headings-smoke-20260515-001233.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a2_more_headings_smoke
query_template: "{query}"
max_headings_per_frame: 6
candidate_point_field: position
```

`A2_more_headings` result:

```text
date_checked: 2026-05-15
rows_with_candidate_association_rate: 0.667
rows_with_candidate_association: 8 / 12
associated_candidate_heading_count: 25
promotion_pass: true
query-level association:
  bed: 3 / 3
  chair: 1 / 3
  plant: 0 / 2
  sofa: 2 / 2
  toilet: 1 / 1
  tv_monitor: 1 / 1
```

`A3_visit_position` launched:

```text
date_launched: 2026-05-15
session: h001-v3c-a3-visit-position-smoke-20260515-001400
log: logs/postview-evidence-v3c-a3-visit-position-smoke-20260515-001400.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a3_visit_position_smoke
query_template: "{query}"
max_headings_per_frame: 6
candidate_point_field: visit_position
```

`A3_visit_position` result:

```text
date_checked: 2026-05-15
rows_with_candidate_association_rate: 0.00
rows_with_candidate_association: 0 / 12
promotion_pass: false
```

Selected 50-row diagnostic:

```text
date_launched: 2026-05-15
ablation: A2_query_heading6_calib50
session: h001-v3c-a2-calib50-20260515-001528
log: logs/postview-evidence-v3c-a2-calib50-20260515-001528.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a2_query_heading6_calib50
query_template: "{query}"
max_headings_per_frame: 6
candidate_point_field: position
promotion_association_rate: 0.60
```

`A2_query_heading6_calib50` result:

```text
date_checked: 2026-05-15
rows: 50
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.48
rows_with_candidate_association: 24 / 50
promotion_pass: false
query-level association:
  bed: 8 / 10
  chair: 2 / 8
  plant: 2 / 10
  sofa: 4 / 10
  toilet: 4 / 6
  tv_monitor: 4 / 6
```

Detector calibration analyzer:

```text
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a2_query_heading6_calibration_analysis
best_candidate_auc: 0.628
best_selected_correct_delta_on_all_rows: +0.08
association_count_auc: 0.502
inside_mask_count_auc: 0.511
passes_detector_calibration_gate: false
```

`A4_all_headings_calib50` launched:

```text
date_launched: 2026-05-15
session: h001-v3c-a4-all-headings-calib50-20260515-003255
log: logs/postview-evidence-v3c-a4-all-headings-calib50-20260515-003255.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_calib50
query_template: "{query}"
max_headings_per_frame: 0
candidate_point_field: position
```

#### 에이전트 추론

The query-only prompt fixes the generic `"a photo"` detector-label artifact, and `A2_more_headings` shows that view coverage is a causal bottleneck. `A3_visit_position` failed completely, so `position` remains the better association point. The next validation is whether the A2 setting holds at 50-row calibration scale.

The A2 setting does not hold strongly enough at 50-row scale. It improves detector association over the original prompt, but the evidence is not yet reliable enough for a policy-scale comparison because association count and mask count do not separate correct candidates from wrong candidates. The `A4_all_headings_calib50` run is a final low-confound view-coverage diagnostic before revising the detector evidence objective.

`A4_all_headings_calib50` result:

```text
date_checked: 2026-05-15
rows: 50
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.52
rows_with_candidate_association: 26 / 50
associated_candidate_heading_count: 121
promotion_pass: false
query-level association:
  bed: 8 / 10
  chair: 4 / 8
  plant: 2 / 10
  sofa: 4 / 10
  toilet: 4 / 6
  tv_monitor: 4 / 6
```

`A4_all_headings_calibration_analysis` result:

```text
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_calibration_analysis
rows_with_any_association_rate: 0.52
wrong_goal_rows_with_any_association_rate: 0.462
baseline_correct_rows_with_any_association_rate: 0.545
best_candidate_auc: 0.607
best_candidate_auc_field: best_box_score_max
best_selected_correct_delta_on_all_rows: +0.08
association_count_auc: 0.506
inside_mask_count_auc: 0.506
passes_detector_calibration_gate: false
```

### Detector Evidence Objective Revision

#### 사실

`GroundingDINO + SAM2` detects and segments objects in every 50-row calibration episode, but `associated_count`, `inside_box_count`, `inside_mask_count`, and `visible_count` are close to random for candidate correctness. `best_box_score_max` gives the only weak positive candidate-correctness signal, with AUC `0.607-0.628` across A2/A4.

#### 에이전트 추론

The next objective should not treat mask association count as a standalone correctness score. The better revision is a conservative confirmatory evidence objective:

```text
E_det(candidate) =
  calibrated_detector_confidence(candidate)
  + semantic_rank_prior(candidate)
  + visibility_support(candidate)
  - geometric_inconsistency_penalty(candidate)
```

Policy use should remain gated:

```text
Do not switch away from the top semantic candidate unless:
  E_det(best_alternative) - E_det(top_candidate) >= margin
  and best_alternative has at least one visible detector-supported observation
  and switching does not create excessive path cost.
```

Next implementation should be offline calibration first, not a policy run. The test is whether a detector-objective table improves candidate correctness and wrong-goal fix rate over `NoReobserve` without creating new wrong-goal cases.

`v3d_detector_objective` strict offline calibration:

```text
date_checked: 2026-05-15
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_objective_analysis_strict
detector_root: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_calib50
min_association_rate: 0.50
min_candidate_auc: 0.65
rows_with_any_association_rate: 0.52
best_candidate_auc: 0.607
passes_detector_calibration_gate: false
```

Objective comparison:

```text
O1_detector_max:
  candidate_auc: 0.607
  selected_correct_delta_on_all_rows: +0.08
  wrong_goal_fixes: 4
  new_wrong_goals: 0

O2_detector_prior:
  candidate_auc: 0.470
  selected_correct_delta_on_all_rows: +0.06
  wrong_goal_fixes: 3
  new_wrong_goals: 0

O3_detector_geometry:
  candidate_auc: 0.476
  selected_correct_delta_on_all_rows: +0.04
  wrong_goal_fixes: 3
  new_wrong_goals: 1

O4_conservative_switch:
  selected_correct_delta_on_all_rows: +0.06
  wrong_goal_fixes: 3
  new_wrong_goals: 0
```

#### 에이전트 추론

The detector confidence alone is the strongest current signal. Adding the current semantic-rank prior and geometry terms degrades candidate-level AUC, which means the present geometry/association features are not yet calibrated enough to be used as positive evidence. The next step should diagnose query/category-specific detector-objective failures before another policy run.

Query/category failure diagnosis:

```text
date_checked: 2026-05-15
source: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_objective_analysis_strict

per-query O1_detector_max candidate AUC:
  bed: 0.663
  chair: 0.288
  plant: 1.000, but only 2 positive candidate rows and no wrong-goal fixes
  sofa: 0.000
  toilet: 0.306
  tv_monitor: 0.700

per-query O1 selected-correct delta:
  bed: +2 / 10
  chair: 0 / 8
  plant: 0 / 10
  sofa: 0 / 10
  toilet: +2 / 6
  tv_monitor: 0 / 6
```

#### 에이전트 추론

The detector objective is not uniformly weak. It is category-dependent:

- `bed` and `tv_monitor` have useful detector confidence signals.
- `toilet` improves selected correctness despite low candidate-level AUC, likely because the selected subset is easier than the full candidate table.
- `chair` and `sofa` are the main failure categories for detector confidence.
- `plant` has too little correct-candidate support to support a robust claim.

The next revision should not be "more headings" or "more detector passes." It should revise object-node evidence representation for cluttered / repeated categories, especially `chair` and `sofa`.

Object-node evidence revision:

```text
date_checked: 2026-05-15
analysis_script: runtime/h001_runtime/analyze_postview_detector_v3c.py
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_gate_analysis_strict

new node features:
  node_box_proximity
  node_extent_score
  compact_node_extent_score
  category_best_gate
  category_best_switch

category_best_gate_modes:
  bed: O1_detector_max
  chair: semantic_prior
  plant: semantic_prior
  sofa: semantic_prior
  toilet: O6_compact_extent
  tv_monitor: O6_compact_extent
```

Objective result:

```text
O6_compact_extent:
  selected_correct_delta_on_all_rows: +0.08
  wrong_goal_fixes: 5
  new_wrong_goals: 1
  selected_correct_rate_on_eligible: 0.375

O9_category_best_gate:
  selected_correct_delta_on_all_rows: +0.12
  wrong_goal_fixes: 7
  new_wrong_goals: 1

O10_category_best_switch, switch_margin 0.10:
  selected_correct_delta_on_all_rows: +0.06
  wrong_goal_fixes: 3
  new_wrong_goals: 0
```

Switch-margin sweep over `O9_category_best_gate`:

```text
output: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_switch_sweep/switch_margin_sweep.json
margin 0.00: selected_correct_delta +5, fixes 5, new_wrong_goals 0
margin 0.02: selected_correct_delta +3, fixes 3, new_wrong_goals 0
margin 0.05-0.15: selected_correct_delta +3, fixes 3, new_wrong_goals 0
margin 0.20+: no switches
```

#### 에이전트 추론

The object-node revision produces a better episode-level signal than raw detector confidence, especially through category-specific feature selection. However, this is still calibration-split evidence and the aggregate candidate AUC remains below the paper-facing gate. Do not run policy-scale comparison yet. The next gate should be cross-validated or held-out validation of the category-best switch rule.

### Category-Best Detector Objective Cross-Validation

#### 사실

Leave-one-scene-out cross-validation was run on the 50-row calibration artifact:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/cross_validate_postview_detector_v3c.py
input: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_gate_analysis_strict/detector_candidate_calibration.jsonl
output: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_loso_cv
fold_strategy: leave_one_scene_out
fold_count: 5
feature_fields: O1_detector_max, O5_node_extent, O6_compact_extent
min_train_auc: 0.65
min_positive: 3
min_negative: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Best aggregate margin:

```text
switch_margin: 0.00
baseline_correct: 11 / 50
selected_correct: 14 / 50
selected_correct_delta: +3
wrong_goal_fixes: 3
new_wrong_goals: 0
switches: 10
folds_with_positive_delta: 2 / 5
folds_with_negative_delta: 0 / 5
passes_minimal_safety_gate: true
passes_robust_gate: false
```

Other margins:

```text
margin 0.02: selected_correct_delta +1, fixes 1, new_wrong_goals 0
margin 0.05-0.15: selected_correct_delta 0
margin 0.20: no switches
```

Fold-level result at margin `0.00`:

```text
00009-vLpv2VX547B: delta +1, fixes 1, new_wrong_goals 0
00017-oEPjPNSPmzL: delta +2, fixes 2, new_wrong_goals 0
00020-XYyR54sxe6b: delta 0, fixes 0, new_wrong_goals 0
00057-1UnKg1rAb8A: delta 0, fixes 0, new_wrong_goals 0
00744-1S7LAXRdDqK: delta 0, fixes 0, new_wrong_goals 0
```

#### 에이전트 추론

The category-best detector objective generalizes better than the same-split result but only weakly. It is safe in this small cross-validation because it does not create new wrong-goal cases, but it is not robust enough for a paper-facing policy claim because only 2 out of 5 held-out scenes improve.

Do not promote to policy-scale comparison yet. The next validation should use independent held-out episodes/scenes or regenerate a larger detector-objective calibration set before writing a paper-facing policy integration contract.

### Independent Held-Out Detector Objective Validation Contract

#### 사실

Prepared held-out validation inputs:

```text
date_prepared: 2026-05-15
target_split: first_eval
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_sr1.json
scene_specs: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/first_eval_scenes.txt
scene_count: 10
episode_count: 100
source_split: HM3D ObjectNav v2 val
candidate_artifact_target: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1
detector_artifact_target: /tmp/research3-runs/h001_first_eval_postview_detector_v3c_a4_all_headings
```

Runtime preparation:

```text
calibration_artifact_job.sh: generalized expected combined row/scene checks through EXPECTED_QUERY_ROWS and EXPECTED_SCENE_COUNT
postview_v3c_groundingdino_sam2_calib50.sh: parameterized FRAMES, CANDIDATE_ARTIFACT, and OUT paths for non-calibration splits
```

Validation rule:

```text
train_rule_source: calibration split only
heldout_action_tuning: disallowed
heldout_allowed_use_of_gt: analysis labels, oracle references, and gate reporting only
policy_scale_run: blocked until this gate passes
```

Promotion gate:

```text
candidate_substrate:
  GTTargetOracle success_rate == 1.0
  candidate_label_coverage >= 0.70
  episodes_with_reachable_correct_and_wrong_rate >= 0.50
  NoReobserve wrong_goal_visit_rate >= 0.10
detector_artifact:
  rows >= 100
  rows_with_detector_box_rate >= 0.80
  rows_with_sam2_mask_rate >= 0.80
  rows_with_candidate_association_rate >= 0.60
detector_objective:
  selected_correct_delta > 0
  new_wrong_goals == 0
  folds_or_scenes_with_positive_delta >= 5 / 10
  candidate_auc >= 0.65 if candidate-level labels are sufficiently balanced
```

#### 에이전트 추론

This is the right next gate because it tests whether the category-best detector objective survives scene shift, not whether the calibration set can be tuned harder. If it fails, the next change should revise the semantic memory / detector-object association representation rather than tune switch margins on `first_eval`.

#### Launch Status

```text
date_launched: 2026-05-15
status: completed
session: h001-first-eval-artifacts-random256-k10-20260515-014112
working_directory: /home/yoohyun/research3
log: logs/first-eval-artifacts-random256-k10-20260515-014112.log
output_root: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1
expected_status: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/job_status.json
expected_artifact: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
rows: 60
candidate_count: 600
finite_position_candidates: 579
scenes: 10
queries: 6
```

Candidate substrate coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_random256_k10_v1/coverage_sanity
log: logs/first-eval-coverage-sanity-20260515-080212.log
episodes: 100
GTTargetOracle_success_rate: 1.0
NoReobserve_success_rate: 0.18
NoReobserve_SPL: 0.0979
NoReobserve_wrong_goal_visit_rate: 0.49
candidate_label_coverage: 1.0
episodes_with_reachable_correct_and_wrong_rate: 0.40
required_reachable_correct_and_wrong_rate: 0.50
overall_pass: false
```

Recovery launch:

```text
date_launched: 2026-05-15
artifact_id: first_eval_random256_k20_v1
change: MAX_CANDIDATES 10 -> 20
session: h001-first-eval-artifacts-random256-k20-20260515-080343
log: logs/first-eval-artifacts-random256-k20-20260515-080343.log
output_root: /tmp/research3-runs/h001_first_eval_artifacts_random256_k20_v1
status: completed
rows: 60
candidate_count: 1200
finite_position_candidates: 1170
```

`k20` coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_random256_k20_v1/coverage_sanity
log: logs/first-eval-k20-coverage-sanity-20260515-085112.log
episodes: 100
GTTargetOracle_success_rate: 1.0
NoReobserve_success_rate: 0.14
NoReobserve_SPL: 0.0800
NoReobserve_wrong_goal_visit_rate: 0.49
candidate_label_coverage: 1.0
episodes_with_reachable_correct_and_wrong_rate: 0.46
required_reachable_correct_and_wrong_rate: 0.50
overall_pass: false
```

Reachability-diverse backend revision:

```text
date_implemented: 2026-05-15
runtime_file: runtime/h001_runtime/export_vlmaps_artifact.py
new_mode: --selection-mode spatial_nms
principle: greedily select high-scoring grid cells with a minimum spatial distance
uses_gt_for_action: false
smoke: TEEsavR23oF/chair, 20 candidates, selection_mode spatial_nms
```

Spatial-NMS recovery launch:

```text
date_launched: 2026-05-15
artifact_id: first_eval_spatial_nms_k20_v1
change: component candidates -> spatial NMS candidates
session: h001-first-eval-spatial-nms-k20-20260515-085336
log: logs/first-eval-spatial-nms-k20-20260515-085336.log
output_root: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1
status: failed
failure_reason: habitat-h001 image used stale export_vlmaps_artifact.py without --selection-mode support
fix: calibration_artifact_job.sh now mounts repo runtime and sets PYTHONPATH for export_vlmaps_artifact.py
retry_session: h001-first-eval-spatial-nms-k20-retry-20260515-095921
retry_log: logs/first-eval-spatial-nms-k20-retry-20260515-095921.log
retry_status: interrupted after 7 / 10 scenes, job_status.json was empty
status_write_fix: calibration_artifact_job.sh now writes job_status.json atomically
resume2_session: h001-first-eval-spatial-nms-k20-resume2-20260515-105554
resume2_log: logs/first-eval-spatial-nms-k20-resume2-20260515-105554.log
resume2_status: completed
rows: 60
candidate_count: 1200
finite_position_candidates: 1004
```

`spatial_nms_k20` coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_spatial_nms_k20_v1/coverage_sanity
log: logs/first-eval-spatial-nms-k20-coverage-sanity-20260515-110249.log
episodes: 100
GTTargetOracle_success_rate: 1.0
NoReobserve_success_rate: 0.20
NoReobserve_SPL: 0.1036
NoReobserve_wrong_goal_visit_rate: 0.47
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.5215
episodes_with_reachable_correct_and_wrong_rate: 0.49
required_reachable_correct_and_wrong_rate: 0.50
overall_pass: false
```

Scene-level ambiguity:

```text
pass_or_borderline: p53SfW6mjZe 0.8, svBbv1Pavdk 0.8, CrMo8WxCyVb 0.6, h1zeeAwLh9Z 0.6, mL8ThkuaVTM 0.6, TEEsavR23oF 0.5
weak: eF36g7L6Z9M 0.4, wcojb4TFT35 0.3, y9hTuugGdiq 0.3, k1cupFYWXJ6 0.0
```

#### 에이전트 추론

`spatial_nms_k20` is a borderline failure, not a dead end. It improves the held-out candidate substrate relative to `k10` and component `k20`, but misses the hard ambiguity gate by one episode. The next lower-confound recovery is not scene replacement yet. It should first lower `TOP_PERCENTILE` for spatial NMS, because that changes only candidate extraction from the same map and same scenes. Scene/episode replacement should be used only if lower-percentile spatial NMS still fails.

Lower-percentile Spatial-NMS recovery launch:

```text
date_launched: 2026-05-15
artifact_id: first_eval_spatial_nms_p97_k20_v1
change: reuse `spatial_nms_k20` maps and lower candidate extraction TOP_PERCENTILE from 98.0 to 97.0
script: runtime/jobs/first_eval_spatial_nms_reexport.sh
session: h001-first-eval-spatial-nms-p97-k20-20260515-113345
log: logs/first-eval-spatial-nms-p97-k20-20260515-113345.log
source_root: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1
output_root: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_p97_k20_v1
expected_artifact: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
status: running
```

Lower-percentile Spatial-NMS coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_spatial_nms_p97_k20_v1/coverage_sanity
log: logs/first-eval-spatial-nms-p97-k20-coverage-sanity-20260515-113602.log
episodes: 100
GTTargetOracle_success_rate: 1.0
NoReobserve_success_rate: 0.20
NoReobserve_SPL: 0.1036
NoReobserve_wrong_goal_visit_rate: 0.47
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.59
episodes_with_reachable_correct_and_wrong_rate: 0.49
required_reachable_correct_and_wrong_rate: 0.50
overall_pass: false
```

#### 에이전트 추론

Lowering `TOP_PERCENTILE` made more candidate positions reachable, but it did not increase episodes with both reachable correct and reachable wrong candidates. The bottleneck is therefore not merely spatial-NMS thresholding. The next recovery should evaluate scene/episode replacement before detector validation.

Scene/episode replacement rule:

```text
do_not_use_for_paper_claim: true
purpose: detector-objective substrate construction only
selection_signal_allowed: candidate-substrate coverage, not detector/policy improvement
pool: HM3D ObjectNav val scenes not already in first_eval
requirements:
  - scene asset and navmesh available
  - all six ObjectNav categories available when possible
  - replacement list frozen before detector-objective validation
first_probe_scenes: 5cdEh9F2hJL, 6s7QHgap2fW, GLAQ4DNUx5U
scene_specs: manifests/replacement_probe_scenes.txt
```

Replacement-probe artifact launch:

```text
date_launched: 2026-05-15
artifact_id: replacement_probe_spatial_nms_p97_k20_v1
script: runtime/calibration_artifact_job.sh
session: h001-replacement-probe-p97-k20-20260515-113921
log: logs/replacement-probe-spatial-nms-p97-k20-20260515-113921.log
output_root: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1
scene_specs: manifests/replacement_probe_scenes.txt
selection_mode: spatial_nms
top_percentile: 97.0
max_candidates: 20
status: running
```

Replacement-probe coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_replacement_probe_policy_spatial_nms_p97_k20_v1/coverage_sanity
log: logs/replacement-probe-spatial-nms-p97-k20-coverage-sanity-20260515-115503.log
episodes: 30
GTTargetOracle_success_rate: 1.0
NoReobserve_success_rate: 0.30
NoReobserve_wrong_goal_visit_rate: 0.6333
candidate_reachable_rate: 0.8783
episodes_with_reachable_correct_and_wrong_rate: 0.6667
overall_pass: true
scene_rates: 5cdEh9F2hJL 1.0, 6s7QHgap2fW 0.6, GLAQ4DNUx5U 0.4
```

First_eval replacement v1:

```text
replacement_policy: minimal scene replacement
replaced_scene: k1cupFYWXJ6
replacement_scene: 5cdEh9F2hJL
manifest: manifests/h001_first_eval_replacement_v1.json
scene_specs: manifests/first_eval_replacement_v1_scenes.txt
combined_artifact: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
rows: 60
candidates: 1200
finite_position_candidates: 1118
selection_uses_detector_or_policy_result: false
```

First_eval replacement v1 coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/coverage_sanity
log: logs/first-eval-replacement-v1-spatial-nms-p97-k20-coverage-sanity-20260515-115704.log
episodes: 100
GTTargetOracle_success_rate: 1.0
NoReobserve_success_rate: 0.26
NoReobserve_SPL: 0.1290
NoReobserve_wrong_goal_visit_rate: 0.51
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.688
episodes_with_reachable_correct_and_wrong_rate: 0.59
overall_pass: true
```

First_eval replacement v1 detector artifact launch:

```text
date_launched: 2026-05-15
script: runtime/jobs/first_eval_replacement_v3c_detector_artifact.sh
session: h001-first-eval-repl-v3c-detector-20260515-115938
log: logs/first-eval-replacement-v3c-detector-artifact-20260515-115938.log
policy_out: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision
frames_out: /tmp/research3-runs/h001_first_eval_replacement_postview_frames_v2_spatial_nms_p97_k20_v1
detector_out: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
query_template: {query}
max_headings_per_frame: 0
max_frames: 100
status: running
```

First launch note:

```text
first_launch_status: failed at frame_export verification
policy_viewpoint_rows: 100
renderable_frame_rows: 98
invalid_rows: 2 p53SfW6mjZe/sofa rows with NaN viewpoint_position
fix: detector job now accepts MIN_FRAME_ROWS=95 and uses actual frame row count for detector MAX_FRAMES
retry_session: h001-first-eval-repl-v3c-detector-retry-20260515-120319
retry_log: logs/first-eval-replacement-v3c-detector-artifact-retry-20260515-120319.log
retry_status: failed at verification
```

Detector artifact verification result:

```text
date_checked: 2026-05-15
detector_out: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
job_status: failed
failed_stage: verification
rows: 98
rows_with_detector_box_rate: 0.9388
rows_with_sam2_mask_rate: 0.9388
rows_with_candidate_association_rate: 0.4082
required_candidate_association_rate: 0.60
promotion_pass: false
```

Query-level association:

```text
bed: 14 / 20
chair: 12 / 20
plant: 2 / 18
sofa: 4 / 18
toilet: 8 / 13
tv_monitor: 0 / 9
```

Held-out detector-objective diagnostic on the failed artifact:

```text
analysis_output: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_category_best_objective_diagnostic
rows: 100
rows_with_any_association_rate: 0.40
baseline_selected_correct: 33 / 100
baseline_wrong_goal_rows: 51
best_candidate_auc: 0.6916
best_candidate_auc_field: O7_extent_prior
best_selected_correct_delta_on_all_rows: +0.02
passes_detector_calibration_gate: false

O2_detector_prior:
  selected_correct_delta_on_all_rows: +0.02
  wrong_goal_fixes: 5
  new_wrong_goals: 3

O10_category_best_switch:
  selected_correct_delta_on_all_rows: 0.00
  wrong_goal_fixes: 0
  new_wrong_goals: 0
```

Association failure decomposition:

```text
box_mask_availability: high
  detector_box_rate: 0.9388
  sam2_mask_rate: 0.9388

main weak categories:
  tv_monitor: no associated rows despite detector boxes/masks
  plant: low detector row coverage and low association
  sofa: boxes/masks available but association sparse

existing-row depth sweep:
  mask + depth_tolerance_1m: association 0.408
  mask + depth_tolerance_3m: association 0.571
  mask + depth_tolerance_5m: association 0.663
  mask + no_depth_gate: association 0.724
  box_or_mask + depth_tolerance_3m: association 0.663
  box_or_mask + no_depth_gate: association 0.776
```

Association variant diagnostic:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/analyze_detector_association_variants.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_association_variants_v1
input_detector_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
input_candidate_decisions: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision/candidate_decisions.jsonl
docker_image: research3/habitat-h001:20260508-calib-artifacts
policy_for_labels: NoReobserve
```

Variant summary:

```text
variant                  assoc  associated_count_auc  selected_delta  fixes  new_wrong
box_or_mask_depth_none   0.760  0.586                 -0.11           5      10
box_or_mask_depth_5p0    0.710  0.574                 -0.11           4      9
mask_depth_none          0.710  0.563                 -0.14           4      10
box_or_mask_depth_3p0    0.650  0.566                 -0.10           5      7
mask_depth_5p0           0.650  0.554                 -0.15           4      11
mask_depth_1p0           0.400  0.512                 -0.24           2      6
```

#### 에이전트 추론

The replacement candidate substrate is now valid, but the detector artifact is not policy-ready. The failure is not detector or mask availability; it is detector-object association, especially for wall-mounted or depth-ambiguous objects such as `tv_monitor` and cluttered/repeated categories such as `plant` and `sofa`.

Relaxing depth or accepting box containment can pass the association-rate gate, but it does not make the association signal useful. The diagnostic shows that `associated_count` remains weak for GT candidate correctness and creates more new wrong-goals than it fixes. The next revision should not be another threshold-only association change; it should change the object evidence representation, likely with category-aware detector confidence, projection quality, depth disagreement handling, and object-node geometry for `tv_monitor`, `plant`, and `sofa`.

Fixed category-best detector objective validation remains blocked until a defensible evidence rule improves GT candidate correctness and wrong-goal behavior, not merely association coverage.

Weak-category detector evidence revision:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/analyze_detector_evidence_revision.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1
input_detector_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
input_candidate_decisions: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision/candidate_decisions.jsonl
docker_image: research3/habitat-h001:20260508-calib-artifacts
policy_for_labels: NoReobserve
```

Rule:

```text
plant:
  field: soft_box_no_depth_count
  margin: 0.1

tv_monitor:
  field: score_box_no_depth_sum
  margin: 1.0

sofa:
  field: none
  action: keep semantic prior
```

Result:

```text
baseline_selected_correct: 33 / 100
weak_category_rule_selected_correct: 36 / 100
selected_correct_delta_on_all_rows: +0.03
wrong_goal_fixes: 3
new_wrong_goals: 0
switches: 3
switch_rate: 0.03
passes_evidence_revision_gate: true
```

Per-category switches:

```text
plant:
  switches: 2
  wrong_goal_fixes: 2
  new_wrong_goals: 0

tv_monitor:
  switches: 1
  wrong_goal_fixes: 1
  new_wrong_goals: 0

sofa:
  switches: 0
  reason: no reliable detector-object evidence; keep semantic prior
```

#### 에이전트 추론

This is the first held-out replacement diagnostic where detector-derived object evidence improves selected-candidate correctness without creating new wrong-goals. The rule is also mechanistically cleaner than association-count tolerance:

- `plant` benefits from no-depth box/mask support count because the previous strict depth gate was too brittle for small or cluttered objects.
- `tv_monitor` benefits from detector-score-weighted box/mask support because depth agreement is often unreliable for wall-mounted objects.
- `sofa` remains unsafe for switching because current detector evidence does not separate correct vs wrong sofa candidates well enough.

However, this is not yet promotion evidence. The rule and margins were selected after inspecting the same first_eval replacement artifact, so the next gate must be scene-wise or independent-split robustness before fixed-rule detector-objective validation or policy-scale integration.

Weak-category evidence scene-wise robustness check:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/validate_detector_evidence_robustness.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_robustness_v1
input_decisions: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1/weak_category_decisions.jsonl
docker_image: research3/habitat-h001:20260508-calib-artifacts
```

Result:

```text
overall:
  baseline_selected_correct: 33 / 100
  selected_correct: 36 / 100
  selected_delta: +3
  wrong_goal_fixes: 3
  new_wrong_goals: 0
  switches: 3

scene_distribution:
  positive_scene_count: 2
  negative_scene_count: 0
  switch_scene_count: 2
  positive_scenes: TEEsavR23oF +2, y9hTuugGdiq +1

query_scene_distribution:
  plant_positive_scene_count: 1
  tv_monitor_positive_scene_count: 1
  sofa_positive_scene_count: 0

gate:
  scenewise_minimal_gate: true
  category_robust_gate: false
  independent_split_evaluated: false
  promotion_ready: false
  reason: category_signal_too_sparse
```

#### 에이전트 추론

`weak_category_rule_v1` is safer than previous association-count variants because it creates no new wrong-goals and does not degrade any scene. But its positive signal is sparse: `plant` improves only on `TEEsavR23oF`, and `tv_monitor` improves only on `y9hTuugGdiq`. This is enough to keep the rule as a candidate diagnostic rule, but not enough to promote it as a fixed detector-objective rule.

For the top-tier paper direction, the decision is to reject `weak_category_rule_v1` as a paper-facing method and keep it only as diagnostic evidence. The reason is not that the result is useless; it is that the method shape is not defensible enough. A category-specific rule selected after looking at the same artifact reads as a hand-tuned patch, not as a contribution derived from a failure mechanism.

### Novelty Decision on Weak-Category Rule V1

#### 사실

`weak_category_rule_v1` has positive same-artifact behavior:

```text
selected_correct: 33 / 100 -> 36 / 100
wrong_goal_fixes: 3
new_wrong_goals: 0
positive_scene_count: 2
negative_scene_count: 0
scenewise_minimal_gate: true
category_robust_gate: false
promotion_ready: false
```

The positive category signals are sparse:

```text
plant: improves only on TEEsavR23oF
tv_monitor: improves only on y9hTuugGdiq
sofa: no reliable switch evidence
```

#### 에이전트 추론

The stronger direction is to convert the diagnostics into a general object-node evidence objective:

```text
E_node(candidate, view) =
  detector_evidence(candidate, view)
  + projection_quality(candidate, view)
  + object_property_conditioned_depth_reliability(candidate, view)
  + semantic_rank_prior(candidate)
  - ambiguity_risk(candidate, view)
```

The design principle should be property-conditioned, not category-name-conditioned:

```text
small_or_cluttered_object:
  strict depth agreement may be too brittle
  use multi-view support and compact object evidence

wall_mounted_or_planar_object:
  depth disagreement can be unreliable
  use detector-score-weighted support and projection consistency

large_repeated_furniture:
  detector boxes/masks are often ambiguous
  require stronger disambiguation before switching
```

#### 사용자 판단 필요

No immediate user decision is needed for the top-tier direction. The default decision is: do not promote `weak_category_rule_v1`; use it as a diagnostic baseline and derive a general object-node evidence objective with explicit ablations.

#### Next Contract

Before another detector validation run, write and implement an ablation-ready objective with these variants:

```text
N0_semantic_prior_only
N1_detector_score_only
N2_projection_support_no_depth
N3_strict_depth_association
N4_property_conditioned_depth_reliability
N5_object_node_evidence_full
```

Promotion gate:

```text
same_rule_for_all_categories_or_property_groups: true
selected_correct_delta_on_all_rows > 0
new_wrong_goals == 0
positive_scene_count >= 2
category_or_property_robust_gate == true
independent_split_required_before_policy_scale: true
```

### General Object-Node Evidence Objective Contract

#### 에이전트 추론

The object-node objective should answer a stronger novelty question than "which category switch rule works?":

```text
When semantic map candidates are ambiguous, can robot-acquired object-node evidence reduce wrong-goal commitment without relying on category-specific tuning?
```

Define each candidate object node with evidence terms:

```text
S_sem:
  semantic rank / semantic memory prior

S_det:
  detector confidence aggregated over re-observation headings

S_proj:
  projection support without strict depth, using candidate projection inside detector box or mask

S_depth:
  strict depth agreement between projected candidate and detector/SAM2 mask depth

S_prop:
  property-conditioned depth reliability
  small_or_cluttered: prefer compact multi-view support over strict depth
  wall_mounted_or_planar: down-weight depth mismatch and require detector-score support
  large_repeated_furniture: require stronger projection/multi-view support before switch
  standard_furniture: use balanced projection + depth support

R_amb:
  ambiguity risk from large masks, repeated boxes, low scene support, and weak margin
```

Candidate objective:

```text
E_node = w_sem*S_sem + w_det*S_det + w_proj*S_proj + w_depth*S_depth + w_prop*S_prop - w_amb*R_amb
```

Switch rule:

```text
Only switch from the semantic top candidate if:
  E_node(best_alt) - E_node(top) >= fixed_margin
  and best_alt has nonzero object-node evidence
  and top candidate is not already strongly confirmed
```

#### Ablation Contract

```text
N0_semantic_prior_only:
  use S_sem only
  purpose: direct semantic memory baseline

N1_detector_score_only:
  use S_det only
  purpose: detector confidence baseline

N2_projection_support_no_depth:
  use S_proj without depth gating
  purpose: test whether strict depth is the bottleneck

N3_strict_depth_association:
  use S_proj + S_depth
  purpose: test current association logic

N4_property_conditioned_depth_reliability:
  use S_proj + S_depth + S_prop
  purpose: test whether property-conditioned reliability beats category tuning

N5_object_node_evidence_full:
  use S_sem + S_det + S_proj + S_depth + S_prop - R_amb
  purpose: paper-facing candidate objective
```

#### Fixed Object Property Groups

These groups are allowed only if fixed before validation and described as object-property assumptions, not tuned category performance:

```text
small_or_cluttered:
  plant

wall_mounted_or_planar:
  tv_monitor

large_repeated_furniture:
  bed
  chair
  sofa

standard_furniture_or_fixture:
  toilet
```

#### Promotion Gate

```text
same weights across property groups except predefined depth-reliability mapping
no category-specific margin tuning
selected_correct_delta_on_all_rows > 0
new_wrong_goals == 0
wrong_goal_fixes > 0
positive_scene_count >= 2
negative_scene_count == 0
property_robust_gate == true
independent_split_required_before policy-scale integration
```

#### 사용자 판단 필요

If the user prioritizes a faster thesis prototype, `weak_category_rule_v1` can remain as a diagnostic baseline. For a top-tier submission target, the next implementation should be `N0-N5` object-node objective evaluation, not independent validation of `weak_category_rule_v1`.

### Object-Node Evidence Objective V1 Result

#### 사실

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/analyze_object_node_evidence_objective.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1
input_detector_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
input_candidate_decisions: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision/candidate_decisions.jsonl
switch_margin: 0.05
```

Variant result:

```text
N0_semantic_prior_only:
  selected_correct_delta: 0.00
  new_wrong_goals: 0

N1_detector_score_only:
  selected_correct_delta: +0.01
  wrong_goal_fixes: 2
  new_wrong_goals: 1

N2_projection_support_no_depth:
  selected_correct_delta: -0.03
  wrong_goal_fixes: 4
  new_wrong_goals: 7

N3_strict_depth_association:
  selected_correct_delta: -0.05
  wrong_goal_fixes: 6
  new_wrong_goals: 11

N4_property_conditioned_depth_reliability:
  selected_correct_delta: -0.05
  wrong_goal_fixes: 6
  new_wrong_goals: 11

N5_object_node_evidence_full:
  candidate_auc: 0.6892
  selected_correct_delta: -0.04
  wrong_goal_fixes: 3
  new_wrong_goals: 7
```

Global margin sweep for `N5_object_node_evidence_full`:

```text
margin 0.10:
  selected_correct_delta: -0.03
  wrong_goal_fixes: 1
  new_wrong_goals: 4

margin 0.20:
  selected_correct_delta: -0.02
  wrong_goal_fixes: 0
  new_wrong_goals: 2

margin 0.30:
  selected_correct_delta: 0.00
  wrong_goal_fixes: 0
  new_wrong_goals: 0

margin 0.40:
  selected_correct_delta: 0.00
  wrong_goal_fixes: 0
  new_wrong_goals: 0
```

#### 에이전트 추론

The property-conditioned object-node objective is better framed than `weak_category_rule_v1`, but the current scoring form is not policy-ready. It has a useful ranking signal at candidate AUC level, but direct re-ranking converts that signal into too many new wrong-goals. Increasing a global margin makes it safe only by making it inactive.

This suggests the next method shape should not be "object-node score directly replaces semantic ranking." For top-tier novelty, the better direction is:

```text
Use object-node evidence as a confirmation / disconfirmation signal for semantic uncertainty,
then trigger active re-observation or delay commitment when evidence is insufficient,
instead of directly switching to the highest object-node score.
```

This keeps the core contribution aligned with semantic uncertainty as mobility utility rather than a detector-based re-ranker.

### Object-Node Confirmation / Disconfirmation V1 Result

#### 사실

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/analyze_object_node_confirmation.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_object_node_confirmation_v1
input_candidate_features: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
promotion_ready: false
reason: same_artifact_confirmation_diagnostic_only
```

Best same-artifact diagnostic config:

```text
field: N1_detector_score_only
confirm rule:
  top detector score >= best alternative detector score

disconfirm rule:
  best alternative detector score - top detector score >= 0.25
```

Result:

```text
baseline_correct_rate: 0.33
baseline_wrong_goal_rate: 0.51

confirmed_rows: 58 / 100
confirmed_correct_rate: 0.397
confirmed_wrong_goal_rate: 0.448

disconfirmed_rows: 3 / 100
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0

uncertain_rows: 39 / 100
wrong_goal_routed_to_reobserve_rate: 0.490
overall_reobserve_request_rate: 0.420
passes_confirm_disconfirm_gate: true
```

Disconfirmed top candidates:

```text
CrMo8WxCyVb / chair: top wrong-goal, alternative detector score exceeds top by 0.276
CrMo8WxCyVb / chair: top wrong-goal, alternative detector score exceeds top by 0.276
eF36g7L6Z9M / tv_monitor: top wrong-goal, alternative detector score exceeds top by 0.266
```

#### 에이전트 추론

This is a stronger signal than direct re-ranking. Detector/object-node evidence is weak when used to select the final candidate directly, but it can identify a small set of high-risk semantic top candidates without creating false disconfirmation on this artifact.

The useful method direction is asymmetric:

```text
Do not let detector evidence directly choose the goal.
Use it to reduce confidence in the semantic top candidate when another object node strongly contradicts it.
Then request another observation or delay commitment.
```

The confirmation signal is only moderate: confirmed rows still contain many wrong-goal cases. The disconfirmation signal is precise but sparse. Therefore this is not policy-ready, but it is a better top-tier novelty direction than category tuning or direct re-ranking because it supports the claim that object-node evidence should update semantic uncertainty before affecting mobility decisions.

### Confirmation / Disconfirmation Gate Freeze

#### 사실

```text
date_checked: 2026-05-15
fixed_gate_name: confirmation_v1_detector_contradiction
field: N1_detector_score_only
confirm_min: 0.0
confirm_margin: 0.0
disconfirm_margin: 0.25
script_updated: runtime/h001_runtime/analyze_object_node_confirmation.py
new_manifest: manifests/h001_confirmation_independent_v1.json
new_manifest_verify: manifests/h001_confirmation_independent_v1.verify.json
docker_manifest_verify: passed
docker_script_smoke: /tmp/research3-runs/h001_confirmation_script_smoke_v1
```

Independent validation split:

```text
split: confirmation_independent_v1
source: replacement_probe rows excluding all scenes used by first_eval_replacement_v1
episodes: 20
scenes: 6s7QHgap2fW, GLAQ4DNUx5U
scene_counts: 10, 10
query_counts:
  bed: 4
  chair: 4
  plant: 4
  sofa: 4
  toilet: 2
  tv_monitor: 2
candidate_artifact: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
```

Independent detector artifact wrapper:

```text
script: runtime/jobs/confirmation_independent_v3c_detector_artifact.sh
policy_out: /tmp/research3-runs/h001_confirmation_independent_policy_spatial_nms_p97_k20_v1/policy_revision
frames_out: /tmp/research3-runs/h001_confirmation_independent_postview_frames_v2_spatial_nms_p97_k20_v1
detector_out: /tmp/research3-runs/h001_confirmation_independent_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
episodes: 20
max_frames: 20
promotion_association_rate_for_job_completion: 0.0
```

Independent detector artifact launch:

```text
date_launched: 2026-05-15
session: h001-confirmation-independent-v3c-20260515-160651
log: logs/confirmation-independent-v3c-detector-artifact-20260515-160651.log
status_file: /tmp/research3-runs/h001_confirmation_independent_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1/job_status.json
current_status: running
current_stage: detector_mask_scoring
```

Independent detector artifact completion:

```text
date_checked: 2026-05-15
status: completed
rows: 20
rows_with_detector_box_rate: 1.0
rows_with_sam2_mask_rate: 1.0
rows_with_candidate_association_rate: 0.45
uses_gt_for_action: false
```

Fixed gate validation result:

```text
object_node_features: /tmp/research3-runs/h001_confirmation_independent_object_node_evidence_objective_v1
confirmation_output: /tmp/research3-runs/h001_confirmation_independent_object_node_confirmation_v1
promotion_ready: false
reason: independent_fixed_gate_failed

baseline_correct_rate: 0.25
baseline_wrong_goal_rate: 0.75
confirmed_rows: 12 / 20
confirmed_correct_rate: 0.25
confirmed_wrong_goal_rate: 0.75
disconfirmed_rows: 2 / 20
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0
wrong_goal_routed_to_reobserve_rate: 0.40
overall_reobserve_request_rate: 0.40
passes_confirm_disconfirm_gate: false
```

Failure decomposition:

```text
confirmed_wrong_goal: 9 / 12
confirmed_zero_zero_evidence: 4 rows, all wrong-goal
confirmed_top_positive_alt_zero: 3 rows, all wrong-goal
scene_distribution:
  6s7QHgap2fW: confirmed_wrong 2, disconfirmed_wrong 2, uncertain_correct 2, uncertain_wrong 4
  GLAQ4DNUx5U: confirmed_correct 3, confirmed_wrong 7
```

#### 에이전트 추론

This gate is now frozen as a candidate-only diagnostic, not a paper claim. The fixed rule may be used only as a top-candidate risk update:

```text
commit only when semantic top candidate is confirmed
request active re-observation when semantic top candidate is disconfirmed or uncertain
do not switch directly to the best detector/object-node candidate
```

The independent validation path deliberately excludes `5cdEh9F2hJL` because that scene was imported into `first_eval_replacement_v1`. This leaves only two scenes and 20 episodes, so a pass would be a stronger sanity check than same-artifact tuning but still not final paper evidence. It is enough to decide whether to write a policy-scale integration contract; it is not enough to claim generality.

The independent validation failed. The most important failure is not false disconfirmation; it is unsafe confirmation. `N1_detector_score_only` confirms too many wrong semantic top candidates, including zero-evidence ties where both top and alternative detector scores are `0`. Therefore the current V1 rule is useful as a negative result: disconfirmation can be precise, but confirmation cannot mean "top score is at least alternative score" without an evidence-support requirement.

Promotion to policy integration remains blocked. Any V2 rule should be derived from this failure mechanism and then tested on a fresh split or larger validation set, not tuned on `confirmation_independent_v1`.

V1 promotion requirements were:

```text
single fixed config only
independent_validation: true
rows >= 20
passes_confirm_disconfirm_gate: true
false_disconfirm_correct_top_count <= 1
disconfirmed_wrong_goal_precision >= 0.80
wrong_goal_routed_to_reobserve_rate >= 0.45
no threshold or field tuning on confirmation_independent_v1 after seeing results
```

### Confirmation V2 Design Contract

#### 에이전트 추론

V1 failed because it treated "not contradicted" as "confirmed." For the paper-facing direction, these must be separate states:

```text
confirmed:
  semantic top candidate has positive object-node evidence support
  and the support is not weaker than alternatives

disconfirmed:
  another candidate has positive object-node evidence support
  and it contradicts the semantic top candidate by a fixed margin

uncertain:
  no positive evidence
  score tie
  weak single-term evidence
  conflict that does not meet the contradiction margin
```

V2 fixed rule candidate:

```text
gate_name: confirmation_v2_supported_contradiction

positive_evidence_support:
  S_det > 0
  and at least one of S_proj, S_depth, S_prop is > 0

confirm:
  top has positive_evidence_support
  and top supported evidence >= best alternative supported evidence

disconfirm:
  best alternative has positive_evidence_support
  and best alternative supported evidence - top supported evidence >= fixed contradiction margin

uncertain:
  otherwise
```

The important design choice is not the exact detector model. It is the state machine:

```text
no evidence does not confirm
single detector score does not confirm
confirmation and disconfirmation are asymmetric
uncertain routes to active re-observation instead of direct switch
```

#### 사용자 판단 필요

V2 should not be promoted using `confirmation_independent_v1`, because that split already exposed the V1 failure. It can be used for debugging implementation only. Promotion needs a fresh split or a larger validation split frozen before running V2.

V2 debug result on `confirmation_independent_v1`:

```text
date_checked: 2026-05-15
output: /tmp/research3-runs/h001_confirmation_independent_object_node_confirmation_v2_debug
rule: supported_contradiction
promotion_ready: false
reason: debugging_only_on_used_validation_split

confirmed_rows: 3 / 20
confirmed_correct_rate: 0.0
confirmed_wrong_goal_rate: 1.0
disconfirmed_rows: 2 / 20
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0
uncertain_rows: 15 / 20
wrong_goal_routed_to_reobserve_rate: 0.80
overall_reobserve_request_rate: 0.85
```

#### 에이전트 추론

V2 fixes the zero-evidence confirmation problem by routing many more rows to `uncertain`, but it still cannot safely use positive object-node support as commit evidence. The useful signal remains asymmetric: contradiction / uncertainty is useful for deciding to re-observe, while confirmation is not reliable enough to justify commitment. The next method shape should therefore be risk-only:

```text
semantic top remains the default candidate
object-node evidence only increases re-observation utility
commit is allowed by semantic/task policy, not by detector confirmation alone
```

### Risk-Only Re-Observation Utility Contract

#### 에이전트 추론

The method should no longer ask whether object-node evidence can approve a goal. The better hypothesis is:

```text
object-node evidence can identify when the semantic top candidate is unsafe to commit,
and that risk should increase active re-observation utility.
```

Risk terms:

```text
R_no_evidence:
  top candidate lacks positive support

R_contradiction:
  supported alternative evidence exceeds supported top evidence

R_ambiguity:
  multiple candidates have similar semantic or object-node support

R_weak_category_or_property:
  current evidence is weak for small/cluttered, wall-mounted, or repeated large objects
```

Policy shape:

```text
baseline candidate:
  semantic top candidate remains the default

commit:
  allowed only when semantic/task policy would commit and risk is low

reobserve:
  triggered when R_no_evidence, R_contradiction, or R_ambiguity is high

not allowed:
  detector/object-node evidence directly switches the final goal candidate
```

Evaluation target:

```text
NoReobserve vs RandomReobserve vs RiskOnlyReobserve
metrics: wrong_goal_visit, wasted_path, Success Rate, SPL, reobserve_request_rate
diagnostics: risk term activation, wrong-goal routed rate, false reobserve on correct top
oracle references: GTTargetOracle, GTCandidateOracle, GTViewOracle
```

#### 사용자 판단 필요

Risk-only validation should use a fresh or larger split before promotion. `confirmation_independent_v1` can remain a debugging split because it has already influenced V2/risk-only design.

Implementation smoke:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/run_smoke.py
output: /tmp/research3-runs/h001_risk_only_reobserve_smoke_v1
episodes: 4
policies: NoReobserve, RiskOnlyReobserve
schema_check: passed
```

RiskOnlyReobserve smoke result:

```text
success_rate: 0.25
wrong_goal_visit_rate: 0.75
risk_triggered_reobserve_rate: 1.0
mean_R_total: 0.9990
final_candidate_changed_rate: 0.0
switch_gate_pass_rate: 0.0
```

#### 에이전트 추론

This smoke validates logging and behavior, not effectiveness. `RiskOnlyReobserve` currently requests re-observation when risk is high but keeps the semantic top candidate fixed, so it is expected not to improve `wrong_goal_visit` yet. The next implementation question is how the active viewpoint or second observation changes risk before commit without allowing detector evidence to directly switch the goal.

### Risk-Only Validation Split Decision

#### 에이전트 추론

`confirmation_independent_v1` must stay debugging-only because it already shaped V2 and risk-only design. For any promotion check, use a fresh and larger split.

Decision:

```text
promotion_split_strategy: fresh larger independent split
reuse_confirmation_independent_v1_for_promotion: false
minimum_target_size: 5 scenes / 50 episodes
preferred_target_size: 10 scenes / 100 episodes if candidate substrate coverage passes
```

Exclusion rule:

```text
exclude scenes used by:
  calibration
  first_eval
  first_eval_replacement_v1
  replacement_probe
  confirmation_independent_v1
```

Gate order:

```text
1. select candidate risk_validation_v1 scene pool before detector/risk results
2. generate non-GT candidate artifact
3. run coverage gate with GTTargetOracle and NoReobserve
4. require reachable correct-and-wrong ambiguity before detector/risk validation
5. run detector/object-node feature artifact
6. run RiskOnlyReobserve without threshold tuning
```

Promotion criteria should compare:

```text
NoReobserve
RandomReobserve
RiskOnlyReobserve
GTTargetOracle
GTCandidateOracle
GTViewOracle
```

#### 사용자 판단 필요

The default is `5 scenes / 50 episodes` for the next validation because it is large enough to avoid the 2-scene bias of `confirmation_independent_v1` while still feasible. A `10 scenes / 100 episodes` split is stronger but should be used only if candidate artifact generation time is acceptable.

Prepared `risk_validation_v1` split:

```text
date_checked: 2026-05-15
scene_file: manifests/risk_validation_v1_scenes.txt
manifest: manifests/h001_risk_validation_v1.json
verify: manifests/h001_risk_validation_v1.verify.json
docker_verify: passed
rows: 100
scenes: 10
episodes_per_scene: 10
selection_uses_detector_or_policy_result: false
```

Scene pool:

```text
LT9Jq6dN3Ea
MHPLjHsuG27
VBzV5z6i1WS
XB4GS9ShBRE
a8BtkwhxdRV
cvZr5TUy5C5
mv2HUxq3B53
q5QZSEeHe5g
ziup5kvtCCR
zt1RVoi7PcG
```

Query distribution:

```text
bed: 20
chair: 20
plant: 20
sofa: 20
toilet: 10
tv_monitor: 10
```

Candidate artifact launch:

```text
date_launched: 2026-05-15
session: h001-risk-validation-p97-k20-20260515-173425
log: logs/risk-validation-spatial-nms-p97-k20-20260515-173425.log
output_root: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1
artifact_id: risk_validation_spatial_nms_p97_k20_v1
scene_specs: manifests/risk_validation_v1_scenes.txt
frames: 256
selection_mode: spatial_nms
top_percentile: 97.0
max_candidates: 20
status: completed
completed_at: 2026-05-15 17:58 KST
rows: 60
candidate_count: 1200
finite_position_candidates: 1062
coverage_check_ok: true
```

Coverage gate:

```text
date_checked: 2026-05-15
output: /tmp/research3-runs/h001_risk_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity
GTTargetOracle success_rate: 1.0
NoReobserve success_rate: 0.19
NoReobserve wrong_goal_visit_rate: 0.47
NoReobserve mean_spl: 0.1004
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.625
reachable_correct_and_wrong_rate: 0.54
overall_pass: true
```

Detector artifact launch:

```text
date_launched: 2026-05-15
session: h001-risk-validation-v3c-20260515-181935
log: logs/risk-validation-v3c-detector-artifact-20260515-181935.log
policy_output: /tmp/research3-runs/h001_risk_validation_policy_spatial_nms_p97_k20_v1/policy_revision
frames_output: /tmp/research3-runs/h001_risk_validation_postview_frames_v2_spatial_nms_p97_k20_v1
detector_output: /tmp/research3-runs/h001_risk_validation_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
status: running/frame_export
episodes: 100
max_frames: 100
promotion_association_rate: 0.0
```

Detector artifact result:

```text
date_checked: 2026-05-15
status: completed
detector_output: /tmp/research3-runs/h001_risk_validation_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
frame_rows: 98
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.3673
uses_gt_for_action: false
```

Object-node evidence objective:

```text
output: /tmp/research3-runs/h001_risk_validation_object_node_evidence_objective_v1
promotion_ready: false
best_variant: N2_projection_support_no_depth
baseline_selected_correct: 31 / 100
best_selected_correct: 37 / 100
wrong_goal_fixes: 8
new_wrong_goals: 2
```

RiskOnlyReobserve validation:

```text
output: /tmp/research3-runs/h001_risk_validation_risk_only_twostage_v1

NoReobserve:
  success_rate: 0.19
  mean_spl: 0.1004
  wrong_goal_visit_rate: 0.47
  mean_wasted_path_wrong_goal: 6.5983

RiskOnlyReobserve:
  success_rate: 0.01
  mean_spl: 0.0010
  wrong_goal_visit_rate: 0.04
  risk_triggered_reobserve_rate: 1.0
  risk_resolved_after_reobserve_rate: 0.05
  risk_unresolved_no_commit_rate: 0.95
  wrong_goal_avoided_by_defer_rate: 0.43
  success_lost_by_defer_rate: 0.18
```

#### 에이전트 추론

This is a useful negative result. `RiskOnlyReobserve` shows that object-node risk can identify many unsafe commitments: wrong-goal visit drops from `0.47` to `0.04`. However, the policy is too conservative because `risk_unresolved_no_commit_rate` is `0.95` and success drops from `0.19` to `0.01`.

The paper-facing conclusion is not that H001 works yet. The result supports a narrower claim: semantic/object-node uncertainty can function as a commitment-risk signal, but defer-only handling is insufficient for navigation utility. The next method step must reduce unresolved risk through additional observation or commit arbitration, not simply tune a threshold on this split.

Next policy revision contract:

```text
Do not promote direct object-node re-ranking:
  reason: new wrong-goals remain under the best direct objective.

Do not promote defer-only RiskOnlyReobserve:
  reason: wrong-goal safety improves, but success/SPL collapse.

Revise toward uncertainty-resolution utility:
  choose next observation to reduce the dominant risk term;
  allow commit only when R_after is reduced enough or when travel/success loss dominates defer cost;
  log avoided wrong-goal and lost success as paired safety/utility metrics.
```

### RiskResolutionReobserve Diagnostic

#### 사실

- Date checked: 2026-05-15
- Runtime file: `runtime/h001_runtime/run_smoke.py`
- New policy: `RiskResolutionReobserve`
- Output: `/tmp/research3-runs/h001_risk_validation_risk_resolution_v1`
- Split: `risk_validation_v1`
- Episodes: `100`
- Candidate artifact: `/tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl`
- Object-node feature artifact: `/tmp/research3-runs/h001_risk_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl`

Commit arbitration rule:

```text
Keep direct goal switching disabled.
Commit semantic top if:
  R_after < risk_total_trigger
or:
  risk_delta_after_reobserve >= 0.05
  R_after <= 0.95
  R_after_contradiction <= 0.25
  top candidate has positive object-node support
Otherwise:
  risk_unresolved
```

Result:

```text
NoReobserve:
  success_rate: 0.19
  mean_spl: 0.1004
  wrong_goal_visit_rate: 0.47

RiskOnlyReobserve:
  success_rate: 0.01
  mean_spl: 0.0010
  wrong_goal_visit_rate: 0.04
  risk_unresolved_no_commit_rate: 0.95

RiskResolutionReobserve:
  success_rate: 0.06
  mean_spl: 0.0310
  wrong_goal_visit_rate: 0.07
  risk_unresolved_no_commit_rate: 0.87
  risk_resolution_commit_rate: 0.08
  wrong_goal_avoided_by_defer_rate: 0.40
  success_lost_by_defer_rate: 0.13
```

#### 에이전트 추론

`RiskResolutionReobserve` partially recovers success compared with strict defer-only behavior, but it is still not a policy-scale success. It increases wrong-goal visit from `0.04` to `0.07` while success remains far below `NoReobserve`.

The important evidence is the failure shape:

```text
commitment risk detection works
one-step resolution evidence is too sparse
commit arbitration alone cannot close the navigation gap
```

The next method step should not tune these thresholds on `risk_validation_v1`. It should improve the evidence/action mechanism: either add another targeted observation for unresolved risk, or improve detector/candidate association so `R_after` becomes meaningfully resolvable.

### Risk Evidence-Resolution Design Decision

#### 사실

- `RiskOnlyReobserve` reduced wrong-goal visit from `0.47` to `0.04`, but left `0.95` of episodes unresolved.
- `RiskResolutionReobserve` recovered success from `0.01` to `0.06`, but still left `0.87` of episodes unresolved and remained below `NoReobserve` success `0.19`.
- The `v3c_groundingdino_sam2` artifact produced detector boxes and `SAM2` masks reliably, but candidate association remained sparse: `candidate_association_rate = 0.3673`.
- The direct object-node objective is not promotion-ready: best selected-correct improved from `31/100` to `37/100`, but direct re-ranking still created `2` new wrong-goals.

#### 논문 주장

Active re-observation is only a contribution if the movement resolves a defined failure mechanism. Adding more observation steps without showing why they reduce uncertainty is not sufficient for a top-tier claim.

#### 에이전트 추론

Pure `second targeted observation` is too weak as the next design because the first observation already shows that observation alone does not guarantee lower `R_after`. If the detector/candidate association remains weak, a second view can add travel cost without resolving the risk.

Pure offline `association recovery` is also weak as a paper-facing direction because it looks like detector/geometry engineering and loses the active mobility part of H001.

The better next design is therefore:

```text
AssociationRecoveryObservation:
  use a second targeted observation only when the goal is to recover missing or weak candidate-object association for the dominant risk term.
```

This keeps the novelty path aligned with H001: semantic uncertainty is converted into a mobility utility, but the utility is explicitly grounded in evidence resolution rather than threshold tuning or direct goal switching.

#### Decision

Select `AssociationRecoveryObservation` as the next evidence-resolution step.

Design principle:

```text
unresolved semantic risk -> choose an observation that should improve candidate-object association -> recompute R_after2 -> commit only if risk is actually resolved
```

Behavior:

```text
if R_after is already below risk_total_trigger:
  commit semantic top

if R_after remains high and dominant risk is R_no_evidence or R_property_weakness:
  request a second view optimized for semantic top association recovery

if R_after remains high and dominant risk is R_ambiguity:
  request a second view that can cover top-2 ambiguous candidates when feasible

if R_after_contradiction remains high:
  do not commit; request a paired top-vs-alt view only if a non-GT feasible viewpoint exists, otherwise terminate as unresolved contradiction
```

Not allowed:

```text
direct candidate switching from detector/object-node evidence
threshold tuning on risk_validation_v1
relaxing association gates only to raise coverage
reporting the diagnostic as paper evidence before a held-out gate
```

#### First Diagnostic Contract

Run this before modifying the full policy loop:

```text
name: association_recovery_observation_v1
input_policy_output: /tmp/research3-runs/h001_risk_validation_risk_resolution_v1
input_candidate_artifact: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
input_object_node_features: /tmp/research3-runs/h001_risk_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
target_rows: unresolved rows from RiskResolutionReobserve
max_rows_first_debug: 20
action: export a second observation plan and frames for association recovery
detector_stack: v3c_groundingdino_sam2, same checkpoint/image as previous artifact
output_root: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1
```

Required outputs:

```text
second_observation_plan.jsonl
second_observation_frames.jsonl
detector_candidate_associations.jsonl
candidate_object_node_features_after_second.jsonl
risk_resolution_after_second_summary.json
```

Primary diagnostic metrics:

```text
second_observation_trigger_rate
association_recovered_rate
top_positive_support_after_second_rate
risk_resolved_after_second_observation_rate
risk_unresolved_after_second_observation_rate
mean_second_observation_travel_cost
wrong_goal_commit_rate_if_fixed_commit_gate_applied
success_lost_by_remaining_defer_rate
```

Minimum gate before policy integration:

```text
risk_resolved_after_second_observation_rate improves by at least 10 percentage points over first observation
association_recovered_rate >= 0.20 on rows that lacked top-candidate positive support
wrong_goal_commit_rate_if_fixed_commit_gate_applied does not exceed RiskResolutionReobserve by more than 0.03 absolute
all action-selection fields use non-GT candidate geometry and semantic/object-node features only
```

#### 사용자 판단 필요

No user decision is needed for the next diagnostic. User decision is needed only if the diagnostic shows that association recovery works but the extra travel cost is too high for the accepted `SPL` budget.

#### Implementation Status

```text
date_checked: 2026-05-15
planner: runtime/h001_runtime/plan_association_recovery_observation.py
after_second_analyzer: runtime/h001_runtime/analyze_association_recovery_observation.py
job_wrapper: runtime/jobs/risk_validation_association_recovery_observation_v1.sh
frame_export_update: export_postview_frames_v2.py now accepts explicit candidate_ids from the second-observation plan
schema_smoke_output: /tmp/research3-runs/h001_association_recovery_observation_schema_smoke
schema_smoke_status: passed
plan_rows: 20
unresolved_input_rows: 87
uses_gt_for_action: false
```

The schema smoke used the existing first-observation detector artifact only to validate analyzer compatibility. It is not an evidence result for second observation.

#### Docker Diagnostic Result

##### 사실

```text
date_checked: 2026-05-16
session: h001-assoc-recovery-v1-20260516-093917
output: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1
status: completed
plan_rows: 20
second_observation_trigger_rate: 1.0
detector_box_rate: 1.0
SAM2_mask_rate: 1.0
rows_with_candidate_association_rate: 0.10
associated_candidate_heading_count: 2
association_recovered_rate: 0.0
risk_resolved_after_second_observation_rate: 0.0
risk_unresolved_after_second_observation_rate: 1.0
top_positive_support_after_second_rate: 0.30
wrong_goal_commit_rate_if_fixed_commit_gate_applied: 0.0
gate_pass: false
uses_gt_for_action: false
```

Reason-level result:

```text
no_evidence rows: 14, association recovered: 0, risk resolved: 0
ambiguity rows: 6, association recovered: 0, risk resolved: 0
```

Projection status:

```text
visible: 119
behind_camera: 136
out_of_fov: 146
```

##### 에이전트 추론

`AssociationRecoveryObservation` v1 should not be promoted to policy integration. The failure is not detector or mask availability, because detector boxes and `SAM2` masks were generated on all rows. The failure is that the selected second view does not recover candidate-object association.

The most likely implementation-level failure is viewpoint geometry: the v1 planner often uses the candidate `visit_position` as the camera base, which can put the camera too close to or vertically aligned with the candidate point. In that setup, the target candidate can be behind the camera, out of field of view, or poorly projected even when the detector finds object boxes.

Next revision should fix the second-view planner, not thresholds:

```text
choose a standoff viewpoint around the target candidate
face the target candidate explicitly
verify projection sanity before running detector
only then rerun the second-observation diagnostic
```

#### Standoff Docker Diagnostic Result

##### 사실

```text
date_checked: 2026-05-16
session: h001-assoc-recovery-standoff-v1-20260516-100438
output: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1
status: completed
plan_rows: 20
second_observation_trigger_rate: 1.0
planner_projection_sane_rate: 1.0
planner_navmesh_snapped_rate: 1.0
viewpoint_source: standoff_navmesh
frame_rows: 20
rendered_heading_count: 136
detector_box_rate: 1.0
SAM2_mask_rate: 1.0
rows_with_candidate_association_rate: 0.40
associated_candidate_heading_count: 19
association_recovered_rate: 0.3571
top_positive_support_after_second_rate: 0.55
risk_resolved_after_second_observation_rate: 0.0
risk_unresolved_after_second_observation_rate: 0.90
commit_after_second_observation_rate: 0.10
wrong_goal_commit_rate_if_fixed_commit_gate_applied: 0.10
success_lost_by_remaining_defer_rate: 0.15
gate_pass: false
uses_gt_for_action: false
```

Reason-level result:

```text
no_evidence rows: 14, association recovered: 5, risk resolved: 0, fixed-gate commits: 2, wrong commits: 2
ambiguity rows: 6, association recovered: 0, risk resolved: 0, fixed-gate commits: 0, wrong commits: 0
```

Projection status:

```text
visible: 130
behind_camera: 192
out_of_fov: 152
```

Dominant `R_after2` terms:

```text
R_after2_no_evidence: 9
R_after2_property_weakness: 2
R_after2_ambiguity: 8
R_after2_contradiction: 1
```

##### 에이전트 추론

The standoff planner fixed the first v1 geometry bottleneck enough to recover association on previously unsupported top candidates. This is useful evidence for the H001 mechanism because motion changed the semantic evidence state without using GT for action.

However, the result is not policy-promotable. Association recovery alone is not equivalent to safe risk resolution. In this diagnostic, the fixed commit gate commits only `2/20` rows and both would be wrong-goal commits. The remaining failures are now risk-model and target-selection failures rather than pure detector availability failures:

```text
association recovery works on some no_evidence rows
but recovered evidence can support an incorrect semantic top candidate
ambiguity rows remain unresolved even when top support becomes positive
R_after2 is still dominated by no_evidence, ambiguity, and property weakness
```

Next revision should derive a failure taxonomy from the standoff result before changing the policy loop:

```text
1. recovered association for wrong semantic top
2. recovered support but persistent ambiguity
3. no recovered association despite standoff view
4. top support recovered but contradiction/property risk remains high
```

The next design should not simply lower risk thresholds. It should define when second-view evidence is used to reject, defer, or request a paired top-vs-alt observation.

##### Failure Taxonomy

```text
date_checked: 2026-05-16
script: runtime/h001_runtime/analyze_association_recovery_failure_modes.py
summary: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_failure_mode_summary.json
rows: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_failure_modes.jsonl
docker_smoke: passed
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Primary failure-mode counts:

```text
persistent_no_evidence: 9
recovered_or_supported_wrong_top: 7
unsafe_commit_wrong_top: 2
correct_top_supported_but_deferred: 2
```

Failure tags:

```text
persistent_property_weakness: 11
recovered_or_supported_wrong_top: 9
persistent_no_evidence: 9
persistent_ambiguity: 8
persistent_contradiction: 7
unsafe_commit_wrong_top: 2
correct_top_supported_but_deferred: 2
```

##### 에이전트 추론

The next risk-update revision should separate three uses of second-view evidence:

```text
positive support for semantic top: reduces no_evidence only
positive support for wrong semantic top: evidence for reject/defer, not commit
persistent ambiguity or contradiction: requires paired top-vs-alt observation or no-commit
```

This points to a commit/defer arbitration design rather than another viewpoint-only revision.

##### Commit/Defer Arbitration Design

###### 사실

```text
date_checked: 2026-05-16
script: runtime/h001_runtime/analyze_association_recovery_arbitration.py
summary: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_arbitration_summary.json
rows: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_arbitration_rows.jsonl
docker_smoke: passed
uses_gt_for_action: false
uses_gt_for_analysis: true
```

The proposed arbitration uses only action-eligible risk and support fields:

```text
top_positive_support_after_second
risk_top_supported_score_after_second
risk_best_alt_supported_score_after_second
risk_support_gap_alt_minus_top_after_second
R_after2
R_after2_no_evidence
R_after2_contradiction
R_after2_ambiguity
R_after2_property_weakness
```

Explicit gates:

```text
if top has no positive support and alt has support:
  reject_top_or_defer

if top has no positive support and no candidate has support:
  retry_association_or_defer

if alt support is not weaker than top support:
  reject_top_or_request_pair_view

if contradiction risk is high:
  reject_top_or_request_pair_view

if ambiguity risk is high:
  request_paired_top_alt_view

if property weakness risk is high:
  request_property_targeted_view

commit_top is allowed only if:
  top has positive support
  R_after2 < risk_total_commit
  top support exceeds alt support by support_margin
  contradiction, ambiguity, and property weakness are below their block thresholds
```

Default thresholds for the design diagnostic:

```text
risk_total_commit: 0.6
support_margin: 0.05
contradiction_block: 0.25
ambiguity_block: 0.5
property_block: 0.5
```

Diagnostic result on the standoff second-observation rows:

```text
commit_top_rate: 0.0
wrong_goal_commit_rate_if_arbitration_applied: 0.0
success_commit_rate_if_arbitration_applied: 0.0
success_lost_by_arbitration_defer_rate: 0.15
wrong_goal_avoided_by_arbitration_defer_rate: 0.85
```

Action counts:

```text
reject_top_or_defer: 6
reject_top_or_request_pair_view: 8
request_paired_top_alt_view: 3
retry_association_or_defer: 3
```

###### 에이전트 추론

This arbitration design fixes the unsafe part of the standoff diagnostic: recovered association is no longer treated as automatic commit evidence. The two wrong commits from the previous fixed gate are blocked because their alternative support is not weaker than top support.

The design is intentionally conservative and does not yet recover success. That is acceptable for this step because the current TODO is a safe arbitration contract, not final policy performance. The next implementation should connect non-commit states to additional action:

```text
reject_top_or_request_pair_view -> paired top-vs-alt observation
request_paired_top_alt_view -> paired top-vs-alt observation
request_property_targeted_view -> property/object-part focused observation if available, otherwise defer
retry_association_or_defer -> alternate standoff direction or defer after one retry budget
reject_top_or_defer -> do not switch directly; mark semantic top unsafe and require additional evidence
```

###### 논문 주장

This is not yet a paper claim. It is a diagnostic design that supports the mechanism-level claim only if the next paired-view or retry action reduces wrong-goal commitment without collapsing success.

###### Integration Status

```text
date_checked: 2026-05-18
integrated_analyzer: runtime/h001_runtime/analyze_association_recovery_observation.py
job_wrapper: runtime/jobs/risk_validation_association_recovery_observation_v1.sh
docker_verification_output: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1
main_summary_field: risk_resolution_after_second_summary.json/arbitration
separate_summary: association_recovery_arbitration_summary.json
separate_rows: association_recovery_arbitration_rows.jsonl
row_count: 20
uses_gt_for_action: false
```

The job wrapper now lists `association_recovery_arbitration_summary.json` as an expected file, so the arbitration output is part of the normal `AssociationRecoveryObservation` diagnostic path rather than a detached post-hoc analysis.

##### Paired Top-vs-Alt Observation Design

###### 사실

```text
date_checked: 2026-05-18
design_diagnostic: runtime/h001_runtime/analyze_pair_observation_design.py
host_smoke: /tmp/research3-runs/h001_pair_observation_design_host_smoke
docker_smoke: /tmp/research3-runs/h001_pair_observation_design_docker_smoke
input_arbitration_rows: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_arbitration_rows.jsonl
input_candidate_artifact: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
pair_trigger_rows: 11
reject_top_or_request_pair_view: 8
request_paired_top_alt_view: 3
common_pair_view_feasible_rate: 0.3636
dual_standoff_feasible_rate: 1.0
mode_counts: common_pair_view 4, matched_dual_standoff 7
skipped_rows: 0
uses_gt_for_action: false
uses_gt_for_analysis: false
```

Feasibility gates used by the diagnostic:

```text
common-pair candidate source:
  arbitration_action in {reject_top_or_request_pair_view, request_paired_top_alt_view}
  risk_top_candidate_id and risk_best_alt_candidate_id_after_second exist in the non-GT candidate artifact

common_pair_view:
  top and alt positions are finite
  a navmesh-snapped common viewpoint exists
  both top and alt are within [0.75m, 6.0m]
  top-vs-alt bearing separation from the viewpoint is <= 70 degrees
  common viewpoint is selected without GT labels

matched_dual_standoff:
  used when common_pair_view is not feasible
  top and alt positions are finite
  plan two matched standoff observations with the same detector/mask settings and the same candidate budget
```

###### 에이전트 추론

The phrase `paired top-vs-alt observation` should not mean "force both candidates into one camera frame" in every case. In the current diagnostic rows, candidate pairs often span `4.45m` to `9.60m`, so a single common viewpoint is not always a realistic or fair action.

The implementation should therefore use a two-mode design:

```text
Mode A: common_pair_view
  use one navmesh-snapped viewpoint when both candidates can be seen under the bearing/distance gates

Mode B: matched_dual_standoff
  use two normalized standoff views when candidates are too far apart for a common view
  compare top and alt evidence under matched observation budget
```

This keeps the active SLAM/navigation utility claim cleaner than direct object-node re-ranking. The robot spends additional motion budget only when arbitration identifies a specific top-vs-alt failure mode.

###### Non-GT Action Contract

Allowed action inputs:

```text
arbitration_action
arbitration_reason
risk_top_candidate_id
risk_best_alt_candidate_id_after_second
candidate position / visit_position / visit_rotation from the artifact
navmesh snap and geometric visibility proxy
R_after2_* fields and support scores
```

Not allowed for action:

```text
top_candidate_correct
GT target object id
oracle shortest path to target object
post-hoc category-specific thresholds from this diagnostic split
```

###### Next Implementation Contract

```text
planner_module: extend or add a planner that consumes association_recovery_arbitration_rows.jsonl
output_rows:
  common_pair_view -> one row with candidate_ids [top, alt]
  matched_dual_standoff -> two rows with shared pair_observation_id and role in {top, alt}
required fields:
  pair_observation_id
  pair_observation_mode
  pair_observation_role
  pair_top_candidate_id
  pair_alt_candidate_id
  pair_common_view_feasible
  pair_dual_standoff_feasible
  pair_span_m
  pair_budget_views
  uses_gt_for_action: false
promotion blocker:
  do not run policy-scale comparison until paired observation shows lower unsafe commit without losing all success recovery on the diagnostic rows
```

###### Implementation Status

```text
date_checked: 2026-05-18
planner_module: runtime/h001_runtime/plan_pair_observation.py
policy_name: PairTopAltObservation
docker_smoke_output: /tmp/research3-runs/h001_pair_observation_plan_docker_smoke
pair_count: 11
plan_rows: 18
common_pair_row_count: 4
matched_dual_row_count: 14
role_counts: common 4, top 7, alt 7
navmesh_snapped_row_rate: 1.0
frame_export_rows: 18
rendered_heading_count: 112
candidate_set_rule: explicit_candidate_ids
uses_gt_for_action: false
```

Planner output files:

```text
pair_observation_plan.jsonl
pair_observation_skipped.jsonl
pair_observation_plan_summary.json
pair_observation_frames.jsonl
```

The planner/frame smoke verifies schema compatibility only. It does not yet show that paired evidence improves risk resolution.

###### Detector / Analysis Diagnostic Gate

###### 사실

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_evidence.py
frame_metadata_passthrough:
  export_postview_frames_v2.py preserves pair_* and arbitration_* fields
  detect_postview_groundingdino_sam2.py preserves pair_* and arbitration_* fields in detector rows, mask rows, association rows, and frame summaries
schema_smoke_output: /tmp/research3-runs/h001_pair_observation_gate_schema_smoke
empty_evidence_smoke_output: /tmp/research3-runs/h001_pair_observation_evidence_empty_smoke
schema_smoke_frame_rows: 18
schema_smoke_rendered_heading_count: 112
empty_evidence_pair_rows: 11
empty_evidence_action_counts: pair_unresolved_no_evidence 11
empty_evidence_gate_pass: false
uses_gt_for_action: false
```

Expected files after the real paired detector/mask diagnostic:

```text
detector_candidate_associations.jsonl
pair_observation_evidence_rows.jsonl
pair_observation_evidence_summary.json
```

The paired evidence diagnostic gate is fixed before running the GPU detector job:

```text
pair_evidence_margin: 0.05
min_pair_evidence_available_rate: 0.50
min_pair_disambiguation_rate: 0.30
min_wrong_top_reject_rate: 0.30
max_false_reject_correct_top_rate: 0.10
max_support_wrong_top_rate: 0.10
```

The analyzer records labels only for post-hoc analysis. The pair evidence action is computed from detector/mask association evidence:

```text
pair_reject_top: alt evidence exceeds top evidence by margin
pair_support_top: top evidence exceeds alt evidence by margin
pair_ambiguous_defer: both candidates have evidence but margin is insufficient
pair_unresolved_no_evidence: neither candidate has detector/mask evidence
```

###### 에이전트 추론

This diagnostic is the first direct test of whether active re-observation can do more than collect more images. A positive result requires the paired view to reduce the specific failure mode found in the standoff run: recovered or supported evidence for a wrong semantic top candidate.

The empty-evidence smoke intentionally fails the gate. Its purpose is only to verify that the analyzer does not accidentally turn missing detector evidence into a positive result.

###### 사용자 판단 필요

No user decision is needed before the next diagnostic. The next job should run detector/mask scoring on the paired observation frames in a background session with logs under `logs/`.

###### Diagnostic Result

###### 사실

```text
date_checked: 2026-05-18
output_root: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1
detector_rows: 18
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.6667
association_rows: 217
paired_rows: 11
pair_evidence_available_rate: 1.0
pair_disambiguation_rate: 0.9091
wrong_top_rows: 9
correct_top_rows: 2
pair_action_counts:
  pair_support_top: 7
  pair_reject_top: 3
  pair_ambiguous_defer: 1
wrong_top_reject_rate: 0.1111
support_wrong_top_rate: 0.7778
false_reject_correct_top_rate: 1.0
passes_pair_evidence_diagnostic_gate: false
uses_gt_for_action: false
```

Action breakdown with labels used only for analysis:

```text
wrong top + pair_support_top: 7
wrong top + pair_reject_top: 1
wrong top + pair_ambiguous_defer: 1
correct top + pair_reject_top: 2
```

###### 에이전트 추론

The current paired observation run rules out a simple detector/mask availability explanation. `GroundingDINO + SAM2` produced boxes and masks on every paired frame, and candidate association reached `0.6667`, but the paired score still supported the wrong semantic top in most wrong-top rows.

The failure is therefore closer to an evidence objective problem: the current `S_pair` measures whether a candidate has detector/mask support in its observation, but it does not yet measure whether that support should overturn the semantic top commitment. In `matched_dual_standoff`, top and alt are observed from different views, so raw support scores are not automatically comparable. In rows where both top and alt are correct, a forced reject action is also not meaningful.

The next revision should start from a failure taxonomy, not from threshold tuning:

```text
1. wrong_top_supported_by_detector_confidence
2. both_candidates_correct_but_ranked_as_reject
3. neither_candidate_correct_but_pair_forces_a_choice
4. matched_dual_standoff_score_not_view-normalized
5. common_pair_view_still_confuses repeated/cluttered categories
```

###### Failure Taxonomy Result

###### 사실

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_failure_modes.py
output_root: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1
rows: 11
summary: pair_observation_failure_mode_summary.json
rows_file: pair_observation_failure_modes.jsonl
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Primary failure mode counts:

```text
neither_candidate_correct_pair_forces_choice: 5
both_candidates_correct_rank_ambiguity: 2
wrong_top_supported_when_alt_correct: 2
wrong_top_supported_by_association_count: 1
alt_correct_but_pair_ambiguous: 1
```

Label-case/action breakdown:

```text
alt_only_correct:
  pair_support_top: 3
  pair_ambiguous_defer: 1
  pair_reject_top: 0
both_candidates_correct:
  pair_reject_top: 2
neither_candidate_correct:
  pair_support_top: 4
  pair_reject_top: 1
```

Reinterpreted diagnostic rates:

```text
alt_only_correct_reject_top_rate: 0.0
alt_only_correct_support_wrong_top_rate: 0.75
neither_candidate_correct_forced_choice_rate: 1.0
both_candidates_correct_reject_top_rate: 1.0
top_only_correct_rows: 0
```

Important secondary tags:

```text
wrong_top_supported_by_pair_score: 7
wrong_top_supported_by_association_count: 5
matched_dual_standoff_raw_scores_not_directly_comparable: 6
matched_dual_standoff_view_opportunity_imbalance: 3
common_pair_view_clutter_or_repeated_category_confusion: 2
false_reject_metric_confounded_by_both_correct: 2
```

###### 에이전트 추론

The previous `false_reject_correct_top_rate = 1.0` should not be read as two clear safety failures. Both rows have `top_candidate_correct = true` and `alt_candidate_correct = true`, so they are better treated as `both_candidates_correct_rank_ambiguity`.

The more serious failure is that the pair action forces a top-vs-alt choice even when neither candidate is correct. This affects `5/11` rows and creates a method requirement: the next objective needs a `no valid candidate / no commit` state, not only a top-vs-alt ranking.

For the rows where the alternative is actually correct, the current pair evidence never rejects top: `alt_only_correct_reject_top_rate = 0.0`. Therefore, the next score revision should not be a threshold change. It must add evidence that can disconfirm the semantic top or confirm the alternative under view-normalized conditions.

###### Revision Requirements

```text
1. separate no-valid-candidate cases before forcing top-vs-alt choice
2. treat both-candidates-correct rows as rank ambiguity rather than wrong-goal failure
3. normalize matched_dual_standoff evidence before comparing raw top and alt scores
4. require evidence that disconfirms top or confirms alt, not only detector support for top
```

###### Paired Objective V2

###### 사실

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_objective_v2.py
output_root: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1
summary: pair_observation_objective_v2_summary.json
rows_file: pair_observation_objective_v2_rows.jsonl
rows: 11
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Objective design:

```text
paired_branch_role: reject_top_or_defer_after_top_was_marked_unsafe
allow_support_top: false
not_threshold_only:
  uses prior arbitration alt gap
  uses view-normalized strict association advantage
  requires top disconfirmation or weak top association
  defers instead of forcing a top-vs-alt choice
```

Action counts:

```text
pair_v2_reject_top_confirm_alt: 3
pair_v2_defer_insufficient_disconfirmation: 3
pair_v2_defer_no_valid_candidate_or_external_search: 3
pair_v2_defer_view_not_comparable: 2
```

Gate result on the current paired diagnostic:

```text
passes_pair_objective_v2_gate: true
wrong_goal_commit_rate: 0.0
wrong_goal_commit_rate_on_commits: 0.0
support_wrong_top_rate: 0.0
neither_candidate_commit_rate: 0.0
alt_only_reject_or_defer_rate: 1.0
alt_only_reject_top_rate: 0.75
commit_rate: 0.2727
success_commit_rate: 0.2727
```

Label-case action breakdown:

```text
alt_only_correct:
  pair_v2_reject_top_confirm_alt: 3
  pair_v2_defer_no_valid_candidate_or_external_search: 1
both_candidates_correct:
  pair_v2_defer_insufficient_disconfirmation: 2
neither_candidate_correct:
  pair_v2_defer_no_valid_candidate_or_external_search: 2
  pair_v2_defer_view_not_comparable: 2
  pair_v2_defer_insufficient_disconfirmation: 1
```

###### 에이전트 추론

This revision directly addresses the observed failure mechanism. The previous objective allowed `pair_support_top` even though the pair branch is entered only after the semantic top has already been marked unsafe. V2 changes the branch semantics: paired evidence can reject the top only when prior arbitration and view-normalized association both support the alternative; otherwise it defers or asks for external candidate search.

This is promising but not a paper claim. The objective was designed after seeing this diagnostic split, so the next step must be held-out paired validation. The key risk is that `commit_rate = 0.2727` may be too conservative for navigation utility even though it fixes wrong-goal commitment on this split.

###### 사용자 판단 필요

No user decision is needed before a held-out validation contract. User judgment is needed later for the acceptable tradeoff between lower wrong-goal commitment and possible success loss by defer.

###### Held-Out Pair Objective V2 Validation Contract

###### 사실

```text
date_checked: 2026-05-18
contract_name: heldout_pair_objective_v2_validation_v1
objective_under_test: h001_runtime.analyze_pair_observation_objective_v2
train_or_design_split: risk_validation_v1
heldout_split: first_eval_replacement_v1
heldout_manifest: manifests/h001_first_eval_replacement_v1.json
heldout_manifest_verify: manifests/h001_first_eval_replacement_v1.verify.json
heldout_scenes: 10
heldout_episodes: 100
scene_overlap_with_risk_validation_v1: 0
debugging_only_split: confirmation_independent_v1
policy_scale_integration_status: blocked
```

Existing held-out prerequisites:

```text
candidate_artifact: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
object_node_features: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
baseline_policy_root: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision
baseline_detector_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
```

Required new held-out pipeline:

```text
1. run RiskResolutionReobserve on first_eval_replacement_v1 with fixed risk/object-node features
2. run AssociationRecoveryObservation standoff diagnostic on unresolved risk rows
3. run arbitration and produce association_recovery_arbitration_rows.jsonl
4. plan PairTopAltObservation from arbitration rows
5. render pair_observation_frames.jsonl
6. run GroundingDINO + SAM2 detector/mask scoring on paired frames
7. run pair_observation_evidence
8. run pair_observation_objective_v2 without modifying thresholds
```

Allowed fixed inputs:

```text
candidate artifact
object-node features
arbitration outputs
pair geometry
detector/mask association evidence
fixed v2 thresholds from risk_validation_v1
```

Not allowed before held-out scoring:

```text
changing v2 thresholds on first_eval_replacement_v1
changing pair_evidence_margin on first_eval_replacement_v1
selecting categories or scenes after seeing held-out objective result
using GT candidate correctness for action
reporting this as policy-scale result
```

Minimum substrate validity gate:

```text
risk_resolution_rows >= 80
association_recovery_rows >= 20
pair_trigger_rows >= 10
pair_observation_rows >= 10
detector_box_rate >= 0.80
sam2_mask_rate >= 0.80
pair_evidence_available_rate >= 0.50
uses_gt_for_action == false
```

Objective v2 held-out gate:

```text
wrong_goal_commit_rate <= 0.10
wrong_goal_commit_rate_on_commits <= 0.20
support_wrong_top_rate == 0.0
neither_candidate_commit_rate <= 0.10
alt_only_reject_or_defer_rate >= 0.80
commit_rate >= 0.15
alt_only_reject_top_rate >= 0.30 when alt_only_correct_rows >= 3
```

Required output root:

```text
/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1
```

Expected files:

```text
risk_resolution_summary.json
association_recovery_arbitration_summary.json
pair_observation_plan_summary.json
summary.json
pair_observation_evidence_summary.json
pair_observation_failure_mode_summary.json
pair_observation_objective_v2_summary.json
job_status.json
```

###### 에이전트 추론

`first_eval_replacement_v1` is the right next validation target because it is scene-disjoint from `risk_validation_v1` and large enough to avoid the 2-scene bias of `confirmation_independent_v1`. It is not final paper evidence because earlier detector-objective work already used this split. A pass here justifies writing a policy integration contract; a final paper claim still needs a fresh or broader evaluation split.

If this gate fails, do not tune v2 on `first_eval_replacement_v1`. The next research move should be one of:

```text
1. revise pair observation geometry if pair evidence is unavailable
2. revise object-node evidence if detector/mask support still confirms wrong top
3. add external candidate search if neither-candidate-correct dominates
```

###### Held-Out Substrate Generation Launch

###### 사실

```text
date_launched: 2026-05-18
job_wrapper: runtime/jobs/first_eval_replacement_pair_objective_v2_substrate.sh
tmux_session: h001-first-eval-pair-substrate-v1-20260518-020840
log: logs/first-eval-replacement-pair-objective-v2-substrate-20260518-020840.log
output_root: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1
status_file: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/job_status.json
status_at_launch_check: running, stage=association_recovery_frame_export
max_association_recovery_rows: 40
uses_gt_for_action: false
```

This job generates the held-out paired diagnostic substrate only. It intentionally does not run `pair_observation_objective_v2`; that remains the next task after `heldout_pair_substrate_summary.json` verifies the substrate validity gate.

###### Held-Out Substrate Verification

###### 사실

```text
date_checked: 2026-05-18
output_root: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1
job_status: completed
status_stage: verified
risk_resolution_rows: 100
association_recovery_rows: 40
pair_trigger_rows: 24
pair_observation_rows: 24
detector_box_rate: 1.0
sam2_mask_rate: 1.0
pair_evidence_available_rate: 1.0
passes_substrate_validity_gate: true
uses_gt_for_action: false
```

The held-out v1 pair evidence still fails:

```text
pair_evidence_action_counts:
  pair_support_top: 12
  pair_reject_top: 8
  pair_ambiguous_defer: 4
support_wrong_top_rate: 0.5714
wrong_top_reject_rate: 0.2857
false_reject_correct_top_rate: 0.4
passes_pair_evidence_diagnostic_gate: false
```

Failure taxonomy on held-out substrate:

```text
neither_candidate_correct_pair_forces_choice: 13
both_candidates_correct_rank_ambiguity: 5
low_risk_or_uncategorized: 3
false_reject_correct_top: 2
wrong_top_supported_by_association_count: 1
```

###### Held-Out Objective V2 Result

###### 사실

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_objective_v2.py
summary: pair_observation_objective_v2_summary.json
rows: 24
uses_gt_for_action: false
uses_gt_for_analysis: true
passes_pair_objective_v2_gate: false
```

Gate values:

```text
wrong_goal_commit_rate: 0.0
wrong_goal_commit_rate_on_commits: 0.0
support_wrong_top_rate: 0.0
neither_candidate_commit_rate: 0.0
alt_only_reject_or_defer_rate: 1.0
alt_only_reject_top_rate: 0.0
alt_only_reject_top_gate_applies: false
commit_rate: 0.0417
min_commit_rate: 0.15
success_commit_rate: 0.0417
```

Action counts:

```text
pair_v2_defer_insufficient_disconfirmation: 7
pair_v2_defer_rank_ambiguous: 7
pair_v2_defer_view_not_comparable: 7
pair_v2_defer_no_valid_candidate_or_external_search: 2
pair_v2_reject_top_confirm_alt: 1
```

###### 에이전트 추론

Held-out validation confirms the safety side of V2 but rejects it as a useful navigation objective. The method avoids wrong-goal commitment, but it almost always defers; `commit_rate = 0.0417` is below the fixed `0.15` gate. This means V2 is a safe arbitration filter, not yet an active navigation utility.

The next revision should not relax the commit threshold on `first_eval_replacement_v1`. The failure modes point to three mechanism-level changes:

```text
1. reduce view-not-comparable cases by improving paired viewpoint geometry
2. add an explicit external-candidate search branch for neither-candidate-correct cases
3. distinguish both-correct rank ambiguity from true unsafe alternatives without forcing no-commit
```

Policy-scale integration remains blocked.

###### Held-Out V2 Over-Deferral Diagnosis

###### 사실

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_v2_overdeferral.py
summary: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_v2_overdeferral_summary.json
rows: 24
commit_rows: 1
deferred_rows: 23
commit_rate: 0.0417
min_commit_rate: 0.15
min_commit_rows: 4
commit_gate_gap_rows: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Deferred label cases:

```text
neither_candidate_correct: 13
top_only_correct: 5
both_candidates_correct: 4
alt_only_correct: 1
```

Revision need counts:

```text
external_candidate_branch_needed: 13
rank_ambiguity_resolution_needed: 10
success_preserving_pair_commit_rule_needed: 9
paired_view_geometry_revision_needed: 9
top_disconfirmation_or_alt_confirmation_needed: 7
no_valid_pair_external_search_needed: 2
alt_confirmation_reject_top_rule_needed: 1
```

Pair-local safe commit ceiling:

```text
pair_correct_candidate_deferred_rows: 10
pair_correct_commit_ceiling_rows: 11
pair_correct_commit_ceiling_rate: 0.4583
```

###### 에이전트 추론

The immediate held-out gate failure is not detector/mask availability and not wrong-goal safety. The failure is utility over-deferral: V2 needs 3 more commits to reach the fixed `commit_rate >= 0.15` gate, while 10 deferred rows already contain a correct top/alt candidate under GT diagnosis.

Therefore, the next highest-probability revision is not threshold lowering and not policy-scale integration. It should be a fixed, non-GT success-preserving pair objective revision that can accept some top-only or both-correct pair cases without reintroducing `support_wrong_top`. The external-candidate branch remains important because `neither_candidate_correct` is the largest label context, but it is a broader recovery mechanism and does not by itself close the pair-objective commit-rate gate unless it searches beyond the top/alt pair.

Next design priority:

```text
1. success-preserving pair objective revision with fixed safety gate
2. external-candidate branch for neither-candidate-correct cases
3. paired-view geometry revision for view-not-comparable cases
```

###### Paired Objective V3 Design and Diagnostic

###### 사실

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_objective_v3.py
design_smoke_output: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1/pair_observation_objective_v3_summary.json
heldout_diagnostic_output: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_objective_v3_summary.json
uses_gt_for_action: false
uses_gt_for_analysis: true
```

V3 branch semantics:

```text
paired_branch_role: reject_top_commit_top_survival_or_defer_after_top_was_marked_unsafe
kept from V2: reject_top_confirm_alt with prior alt gap, view-normalized alt confirmation, and top disconfirmation
new action: pair_v3_commit_top_common_view_survival
new action condition: common_pair_view, alt has no comparable observation, top has direct confirmation, top disconfirmation is low, top has strict-association advantage, and prior arbitration does not favor alt
```

Held-out diagnostic result:

```text
rows: 24
passes_pair_objective_v3_gate: true
commit_rate: 0.1667
min_commit_rate: 0.15
wrong_goal_commit_rate: 0.0
wrong_goal_commit_rate_on_commits: 0.0
support_wrong_top_rate: 0.0
top_survival_wrong_commit_rate: 0.0
neither_candidate_commit_rate: 0.0
alt_only_reject_or_defer_rate: 1.0
```

Action counts:

```text
pair_v3_commit_top_common_view_survival: 3
pair_v3_reject_top_confirm_alt: 1
pair_v3_defer_insufficient_disconfirmation: 7
pair_v3_defer_rank_ambiguous: 7
pair_v3_defer_view_not_comparable: 4
pair_v3_defer_no_valid_candidate_or_external_search: 2
```

###### 에이전트 추론

V3 closes the pair-local commit-rate failure without reintroducing wrong-goal commits on this diagnostic. The improvement comes from reclassifying a specific `view_not_comparable` case: when a `common_pair_view` directly confirms top and the alternative has no comparable observation, V3 treats this as top survival rather than generic incomparability.

This is a better top-tier shape than a threshold-only change because the new action is forced by the failure taxonomy: V2 had no way to distinguish unsafe top support from a correct top candidate that survived a common-pair observation. However, this is still not paper evidence because the same held-out split was used to diagnose V2 over-deferral before V3 was implemented.

Next method work should address the remaining largest deferred context:

```text
neither_candidate_correct: 13 rows
```

That requires an external-candidate branch or no-valid-pair recovery, not another top/alt pair threshold change.

###### External-Candidate Branch After Pair V3

###### 사실

```text
date_checked: 2026-05-18
planner: runtime/h001_runtime/plan_external_candidate_observation.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1
summary: external_candidate_branch_summary.json
plan_rows: external_candidate_observation_plan.jsonl
frame_smoke: external_candidate_frame_smoke/summary.json
policy: ExternalCandidateObservation
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Branch rule:

```text
trigger after pair_v3_defer only
trigger if pair_v3_no_valid_pair_state
trigger if non-rank-ambiguous pair evidence is weak after observation
trigger if rank-ambiguous pair has top rejection evidence and very small confirm gap
action: request_external_candidate_observation
not action: external candidate commit
```

Held-out diagnostic:

```text
rows: 24
triggered_rows: 15
plan_rows: 90
skipped_rows: 0
neither_candidate_triggered_rows: 13
pair_correct_candidate_unnecessary_external_rows: 2
external_budget: 6
neither_candidate_external_set_contains_correct_rate: 0.3846
neither_candidate_first_external_correct_rate: 0.0
```

Recall by external budget on triggered rows:

```text
K=1: 0.0000
K=2: 0.2667
K=3: 0.2667
K=5: 0.4000
K=6: 0.4667
K=10: 0.6000
```

Frame export smoke:

```text
ok: true
rows_requested: 2
rows_exported: 2
rendered_heading_count: 5
policy: ExternalCandidateObservation
uses_gt_for_action: false
```

###### 에이전트 추론

The branch now exists as an active observation path, not as a goal-commit shortcut. This preserves the safety contract: when pair-local evidence is unsafe or insufficient, the method requests more perception over candidates outside the top/alt pair.

The diagnostic also exposes a deeper limitation. The external branch can route all 13 `neither_candidate_correct` rows into external search, but the current semantic memory ranking is weak: the first external candidate is never correct, and even a budget of 6 contains a correct external candidate in only `38.46%` of the neither-candidate rows. This means detector scoring of external observations should not be treated as the next paper-facing result until candidate retrieval/ranking or memory coverage improves.

Method implication:

```text
pair-local V3: solves safe commit over-deferral for top/alt pair cases
external branch: converts no-valid-pair failure into active search
remaining bottleneck: semantic memory coverage/ranking outside top/alt pair
```

###### External-Candidate Rank-Band Retrieval Revision

###### 사실

```text
date_checked: 2026-05-18
planner: runtime/h001_runtime/plan_external_candidate_observation.py
selection_mode: rank_bands
rank_band_pattern: 1,2,3,4,6,10
output_root: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/external_candidate_rank_bands_v1
summary: external_candidate_branch_summary.json
plan_rows: external_candidate_observation_plan.jsonl
frame_smoke: frame_smoke/summary.json
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Rank-band diagnostic against previous `semantic_rank` selection:

```text
triggered_rows: 15
external_budget: 6
semantic_rank K=6 recall on triggered rows: 0.4667
rank_bands K=6 recall on triggered rows: 0.6000
semantic_rank K=6 recall on neither-candidate rows: 0.3846
rank_bands K=6 recall on neither-candidate rows: 0.5385
rank_bands full external pool recall on neither-candidate rows: 0.5385
rank_bands first external correct rate on neither-candidate rows: 0.0000
```

Frame export smoke:

```text
ok: true
rows_requested: 2
rows_exported: 2
rendered_heading_count: 5
policy: ExternalCandidateObservation
uses_gt_for_action: false
```

###### 에이전트 추론

The revision improves candidate-set recall without changing the safety contract: external candidates are observed, not committed. The `rank_bands` pattern is a failure-driven retrieval rule because the diagnostic showed correct external candidates often appear at moderate semantic ranks rather than at the first few post-top/alt ranks.

The result also exposes a remaining ceiling. On the current artifact, `rank_bands` reaches the full external-pool recall for `neither_candidate_correct` rows, so the remaining miss cases are memory coverage failures rather than ranking-only failures. This should feed into candidate artifact coverage and fresh validation before any detector-scored external observation is used as paper-facing evidence.

###### Fresh V3 Validation Split

###### 사실

```text
date_checked: 2026-05-18
manifest: manifests/h001_v3_fresh_validation_v1.json
verify: manifests/h001_v3_fresh_validation_v1.verify.json
scene_list: manifests/v3_fresh_validation_v1_scenes.txt
selected_split: v3_fresh_validation_v1
benchmark: HM3D ObjectNav v2
source_split: val
rows: 100
scenes: 13
source_files_loaded: 13
scene_assets_checked: 13
docker_verify_ok: true
sim_scene_limit: 2
```

The split excludes all scenes already used for:

```text
first_eval
first_eval_replacement_v1
replacement_probe
confirmation_independent
risk_validation_v1
```

Query counts:

```text
bed: 17
chair: 17
sofa: 17
toilet: 17
plant: 16
tv_monitor: 16
```

Scene count range:

```text
min episodes per scene: 6
max episodes per scene: 9
scene count: 13
```

###### 에이전트 추론

This split is the correct next validation target for pair-local V3 because it was created after V3 was implemented and excludes all scenes used to diagnose V2/V3 behavior. It should be treated as locked before any V3 scoring:

```text
do not change pair_v3 thresholds after scoring this split
do not select categories or scenes after scoring this split
do not use external-candidate diagnostic labels for action
do not make paper claims until candidate artifact, pair observation substrate, detector evidence, and V3 objective all pass on this split
```

The split preparation does not mean the validation is complete. It only removes the immediate leakage risk from using `first_eval_replacement_v1` as both diagnostic and evidence.

###### Fresh V3 Candidate Artifact Coverage Gate

###### 사실

```text
date_checked: 2026-05-18
job_status: completed
artifact: /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
coverage: /tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
coverage_gate: pass
overall_pass: true
uses_gt_for_action: false
```

Artifact verification:

```text
scenes: 13
query_rows: 78
candidates: 1560
finite_candidate_positions: 1560
navigable_visit_positions: 1411
queries: bed, chair, plant, sofa, toilet, tv_monitor
```

Coverage metrics:

```text
episodes: 100
candidate_label_coverage: 1.0
episodes_with_correct_candidate_rate: 0.79
episodes_with_reachable_correct_rate: 0.69
episodes_with_reachable_wrong_rate: 0.97
episodes_with_reachable_correct_and_wrong_rate: 0.69
top_candidate_correct_rate: 0.31
top_candidate_reachable_rate: 0.88
NoReobserve success_rate: 0.26
NoReobserve SPL: 0.1459
NoReobserve wrong_goal_visit_rate: 0.61
GTTargetOracle success_rate: 1.0
```

###### 에이전트 추론

The fresh validation substrate is now strong enough for fixed-rule pair-local V3 validation. The high `NoReobserve` wrong-goal rate and `0.69` reachable correct-and-wrong rate indicate that this split contains meaningful semantic commitment risk rather than only easy successes. The next step can score V3 on this split, but thresholds and category choices should remain frozen after this gate.

###### Fixed-Rule Pair-Local V3 Validation Result

###### 사실

```text
date_checked: 2026-05-18
output_root: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1
pipeline_status: completed
substrate_gate: pass
pair_objective_v3_gate: fail
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Substrate:

```text
risk_resolution_rows: 100
association_recovery_rows: 40
pair_trigger_rows: 31
pair_observation_rows: 31
detector_box_rate: 1.0
sam2_mask_rate: 1.0
pair_evidence_available_rate: 1.0
passes_substrate_validity_gate: true
```

Objective gate:

```text
commit_rate: 0.0323
min_commit_rate: 0.15
wrong_goal_commit_rate: 0.0323
support_wrong_top_rate: 0.0323
top_survival_wrong_commit_rate: 1.0
neither_candidate_commit_rate: 0.0909
alt_only_reject_top_rate: 0.0
passes_pair_objective_v3_gate: false
```

Primary failure modes:

```text
neither_candidate_correct_pair_forces_choice: 11
both_candidates_correct_rank_ambiguity: 10
wrong_top_supported_by_detector_confidence: 5
alt_correct_but_pair_ambiguous: 2
false_reject_correct_top: 1
low_risk_or_uncategorized: 2
```

###### 에이전트 추론

The fixed fresh validation rejects V3 as a paper-facing objective. This is useful negative evidence: the substrate is valid, but the objective still over-defers and has an unsafe top-survival branch. The main failure is not detector/mask availability; detector box and mask rates are high. The next revision should be derived from the failure taxonomy, not from threshold tuning on `v3_fresh_validation_v1`.

Next method requirements:

```text
1. represent no-valid-candidate cases before any top-vs-alt commit
2. treat both-candidates-correct as rank ambiguity, not as a forced failure
3. reduce view-not-comparable cases through paired geometry revision
4. remove or harden top-survival commit because the only fresh top-survival commit was wrong
```

###### Pair Geometry V2 Revision

###### 사실

```text
date_checked: 2026-05-18
code: runtime/h001_runtime/plan_pair_observation.py
new option: --include-dual-fallback-for-common
wrapper default: PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON=1
plan_smoke_out: /tmp/research3-runs/h001_v3_fresh_validation_pair_geometry_v2_plan_smoke
frame_smoke_out: /tmp/research3-runs/h001_v3_fresh_validation_pair_geometry_v2_frame_smoke
uses_gt_for_action: false
```

Docker plan smoke on the fresh validation pair substrate:

```text
pair_count: 31
plan_rows: 86
common_with_dual_fallback pairs: 24
matched_dual_standoff pairs: 7
common_dual_fallback_unavailable_pairs: 0
skipped_rows: 0
role_counts: common 24, top 31, alt 31
navmesh_snapped_row_rate: 1.0
```

Docker frame export smoke:

```text
rows_exported: 6
rendered_heading_count: 32
errors: 0
uses_gt_for_action: false
```

###### 에이전트 추론

The previous `common_pair_view` design caused one-sided evidence: the common viewpoint often saw the top candidate while the alternative had `visible_count = 0`, producing `view-not-comparable` and one unsafe top-survival commit. The revised geometry keeps the common view but adds matched top/alt standoff views under one pair id. This makes the next objective depend on comparable evidence rather than on a single common-view visibility accident.

The `no-valid-candidate` cases are not solved by geometry alone. They should be handled in pair objective v4 as a separate action class: either rank ambiguity, external candidate search, or safe defer depending on pair labels and evidence, without using GT for action.

This is a design revision, not a paper claim. Detector/mask scoring and pair objective v4 must still pass a fresh fixed-rule gate before policy-scale integration.

###### Pair Objective V4 Design Smoke

###### 사실

```text
date_checked: 2026-05-18
code: runtime/h001_runtime/analyze_pair_observation_objective_v4.py
design_smoke_out: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4_design_smoke
input_evidence: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pair_observation_evidence_rows.jsonl
input_plan: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pair_observation_plan.jsonl
uses_gt_for_action: false
```

V4 action taxonomy:

```text
pair_v4_reject_top_confirm_alt
pair_v4_commit_top_verified_pair_evidence
pair_v4_defer_top_survival_untrusted
pair_v4_request_external_candidate_search
pair_v4_defer_rank_ambiguous_or_duplicate_goal
pair_v4_defer_view_not_comparable
pair_v4_defer_insufficient_disconfirmation
pair_v4_defer_no_pair_evidence
```

Design smoke on the previous fresh evidence:

```text
rows: 31
passes_pair_objective_v4_safety_gate: true
passes_pair_objective_v4_full_gate: false
wrong_goal_commit_rate: 0.0
commit_rate: 0.0
top_survival_signal_rate: 0.0323
top_survival_commit_rate: 0.0
top_survival_blocked_rate: 1.0
```

Action counts:

```text
pair_v4_defer_view_not_comparable: 15
pair_v4_defer_rank_ambiguous_or_duplicate_goal: 7
pair_v4_defer_insufficient_disconfirmation: 5
pair_v4_request_external_candidate_search: 3
pair_v4_defer_top_survival_untrusted: 1
```

###### 에이전트 추론

V4 fixes the unsafe part of V3 by removing `pair_v3_commit_top_common_view_survival` as a commit path. A top-survival signal is now a safety block unless the alternative candidate has comparable evidence. This makes the method less useful on the old common-view evidence, but that is expected: the full utility gate should be tested only after the revised `common_with_dual_fallback` geometry is scored by the detector/segmenter.

The key V4 design change is action-space separation, not threshold tuning:

```text
1. incomplete pair set -> request external candidate search
2. both confirmed -> rank/duplicate-goal ambiguity
3. one-sided top survival -> safe defer
4. commit alt -> only with alt confirmation plus top disconfirmation
5. commit top -> only with comparable top evidence plus alt disconfirmation
```

###### 논문 주장

This is not yet a paper claim. It is a fixed objective contract for the next revised-geometry validation run.

###### 논문 주장

This is still not a paper claim. It is a design bridge from the observed failure mechanism to the next action. It becomes claim-relevant only if pair evidence separates wrong semantic top from correct ambiguous top better than single-candidate standoff observation.

### Risk Update After Active Observation

#### 에이전트 추론

The current smoke only verifies that risk triggers re-observation. It does not yet test the actual intervention, because it commits to the semantic top candidate after re-observation regardless of whether risk was reduced. The next policy behavior must separate these states:

```text
R_before:
  risk estimated from semantic candidate ambiguity and missing object-node evidence

active observation:
  choose a viewpoint expected to reduce the dominant risk term

R_after:
  risk recomputed from object-node evidence after the new observation

commit:
  allowed only if R_after < risk_total_trigger

defer / continue:
  if R_after remains high, do not make an explicit wrong-goal commit
```

Dominant-risk viewpoint rule:

```text
if R_no_evidence dominates:
  observe semantic top candidate

if R_contradiction dominates:
  observe both semantic top and best contradictory alternative if one physical viewpoint can cover both;
  otherwise observe the semantic top first and log unresolved contradiction

if R_ambiguity dominates:
  choose the reachable candidate viewpoint with highest expected ambiguity reduction under travel cost

if R_property_weakness dominates:
  use property-specific observation preference:
    small_or_cluttered: closer compact-object view
    wall_mounted_or_planar: front-facing high-projection view
    large_repeated_furniture: view that separates repeated instances
```

One-step harness behavior:

```text
RiskOnlyReobserveV1:
  if R_before < trigger:
    commit semantic top
  else:
    take one active observation
    compute R_after
    if R_after < trigger:
      commit semantic top
    else:
      terminate as risk_unresolved / no explicit goal commit
```

Metrics to add:

```text
R_before
R_after
risk_delta_after_reobserve
risk_resolved_after_reobserve
risk_unresolved_no_commit
dominant_risk_term
wrong_goal_avoided_by_defer
success_lost_by_defer
```

This is still risk-only: object-node evidence does not choose a new final goal. It can only allow, delay, or request more observation before a semantic default commit.

### Two-Stage Risk Policy Smoke

#### 사실

- Date checked: 2026-05-15
- Runtime file: `runtime/h001_runtime/run_smoke.py`
- Smoke output: `/tmp/research3-runs/h001_risk_only_reobserve_twostage_smoke_v1`
- Manifest: `manifests/h001_first_eval_replacement_v1.json`
- Split: `first_eval_replacement_v1`
- Episodes: `4`
- Policies: `NoReobserve`, `RiskOnlyReobserve`
- Candidate artifact: `/tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl`
- Object-node feature artifact: `/tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl`

Smoke result:

```text
RiskOnlyReobserve:
  risk_triggered_reobserve_rate: 1.0
  risk_resolved_after_reobserve_rate: 0.0
  risk_unresolved_no_commit_rate: 1.0
  wrong_goal_visit_rate: 0.0
  wrong_goal_avoided_by_defer_rate: 0.5
  success_lost_by_defer_rate: 0.25
  mean_R_before: 0.9967
  mean_R_after: 1.0
```

#### 에이전트 추론

The smoke validates the new control-flow invariant, not effectiveness: when `R_after` remains high, the harness terminates as `risk_unresolved` without an explicit goal commit. This prevents wrong-goal commitment in the smoke rows, but it can also defer a correct semantic top candidate. Promotion therefore requires the larger `risk_validation_v1` split to show that avoided wrong-goal commits outweigh success lost by defer under fixed thresholds.

### ObjectNav to Spatial Navigation Scope

#### 에이전트 추론

The current probe is still ObjectNav-facing because it provides controlled target labels, wrong-goal visit, wasted path, `Success Rate`, and `SPL`. The research direction is broader: ObjectNav is the first measurable substrate for semantic uncertainty, and the positive signal should later be extended to spatial navigation / active SLAM by adding pose graph connectivity, map consistency, `ATE`, `RPE`, and semantic accuracy.

The claim should therefore be framed as:

```text
ObjectNav is the first evaluation gate.
Spatial navigation / active SLAM is the target extension.
Semantic uncertainty is the bridge variable that should become a mobility utility.
```

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
