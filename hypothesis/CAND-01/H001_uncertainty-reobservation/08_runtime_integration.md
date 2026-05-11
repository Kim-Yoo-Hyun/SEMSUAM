# Runtime Integration Plan

## Purpose

Define how the first implementation should connect HM3D / HM3D-OVON data, semantic candidates, GT references, baselines, and H001 logging.

This is an implementation plan, not an experiment result.

## Facts

- HM3D v0.2 scene assets are available under `/tmp/research3-data/scene_datasets/hm3d`.
- ObjectNav HM3D v2 episodes are available under `/tmp/research3-data/datasets/objectnav/hm3d/v2`.
- HM3D-OVON episodes are available under `/tmp/research3-data/datasets/ovon/hm3d`.
- Runtime scripts and Dockerfiles are stored under `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/`.
- Smoke tests and paper-body implementation experiments must run in Docker.
- The root repository is connected to Git remote `https://github.com/Kim-Yoo-Hyun/SSLAM.git`.

## Paper Claims

- Habitat ObjectNav reports task-level navigation metrics such as `Success Rate` and `SPL`.
- HM3D-OVON evaluates open-vocabulary ObjectNav and is useful for semantic ambiguity stress testing.
- Semantic-map navigation methods motivate candidate confidence, semantic memory, and re-perception as causes of navigation behavior changes.

## Inferences

The first runtime should start from Habitat ObjectNav integration rather than full `VLMaps` reproduction. The reason is evidence quality: H001 needs controlled episode loading, GT target labels, shortest-path references, and failure decomposition before a complex semantic-map backend is introduced.

`VLMaps` or another semantic map backend should enter through an adapter interface that produces candidate nodes and uncertainty features. This keeps baselines, GT oracle references, and logging comparable across closed-vocabulary ObjectNav and HM3D-OVON.

## Runtime Direction

Use two layers:

- evaluation harness: Habitat episode loading, simulator, GT labels, shortest paths, policy loop, logging
- semantic candidate backend: map/query-to-candidate extraction, semantic scores, uncertainty features, re-observation view proposals

The first implementation should make the evaluation harness work with a minimal candidate backend before adding full `VLMaps` map creation.

## Docker Images

| Image | Role | Status |
| --- | --- | --- |
| `research3/hm3d-download:20260507` | dataset download / dataset smoke checks | existing |
| `research3/vlmaps-smoke:20260507` | precomputed `VLMaps` demo artifact check | existing |
| `research3/habitat-h001:<date>` | first runtime integration for Habitat ObjectNav / HM3D-OVON | needed |
| `research3/slam-eval:<date>` | Step 4-5 SLAM/map-side metrics | later |

## Mount Contract

Container paths:

```text
/data/scene_datasets/hm3d
/data/datasets/objectnav/hm3d/v2
/data/datasets/ovon/hm3d
/workspace
/runs
```

Host paths:

```text
/tmp/research3-data -> /data
/home/yoohyun/research3 -> /workspace:ro for smoke checks
/tmp/research3-runs -> /runs
```

Implementation runs may mount `/workspace` read-write only when generating code is explicitly part of the task. Dataset mounts should be read-only for evaluation.

## Module Boundaries

The first runtime code should have these conceptual modules:

| Module | Responsibility |
| --- | --- |
| `EpisodeLoader` | load HM3D ObjectNav v2 and HM3D-OVON episode shards |
| `GTResolver` | resolve valid target instances, accepted synonyms, success radius, candidate correctness |
| `PathOracle` | compute shortest path to valid target and candidate locations |
| `CandidateBackend` | return semantic candidate nodes for a query |
| `UncertaintyScorer` | compute `U_sem` from `05_uncertainty_features.md` |
| `ViewpointSelector` | choose no/random/semantic/GT re-observation viewpoint |
| `PolicyRunner` | execute or simulate candidate commit and re-observation sequence |
| `NavLogger` | write logs defined in `06_logging_schema.md` |
| `Aggregator` | compute metrics defined in `07_evaluation_contract.md` |

## First Candidate Backend

Start with a GT-assisted diagnostic candidate backend, not as the proposed method but as a harness validation tool.

Purpose:

- confirm target labels and candidate correctness
- test `GTTargetOracle`, `GTCandidateOracle`, and shortest path calculation
- produce controlled wrong candidates for logging validation

Then add a non-GT semantic backend:

- `VLMaps` precomputed artifact backend, if candidate extraction is available
- lightweight CLIP/open-vocabulary map backend, if `VLMaps` runtime becomes too expensive
- later `ConceptGraphs`-style object/node backend, if object-level candidates are needed

## Candidate Backend Contract

### 사실

- Runtime module: `runtime/h001_runtime/run_smoke.py`
- Supported backends include `diagnostic_gt` and `artifact_jsonl`.
- `GTTargetOracle` is a reference policy, not a deployable baseline.

### 에이전트 추론

H001 needs `artifact_jsonl` as the paper-facing non-GT candidate backend. GT labels are allowed only after candidate selection for evaluation and oracle references.

Required row or candidate fields:

- `scene_id` or `scene_key`
- `query` or `object_category`
- `candidate_id`
- `position`
- `visit_position`
- `visit_rotation`
- `score`
- `view_count` or `observation_count`

Runtime invariant:

```text
candidate_backend = artifact_jsonl
candidate_backend_uses_gt_for_action = false
```

## Semantic Artifact Generation

### 사실

- `VLMaps` artifact exporter: `runtime/h001_runtime/export_vlmaps_artifact.py`
- Text embedding exporter: `runtime/export_text_embeddings.py`
- HM3D trajectory exporter: `runtime/h001_runtime/export_hm3d_vlmaps.py`
- Alignment adapter: `runtime/h001_runtime/align_vlmaps_artifact.py`
- Habitat navigability smoke: `runtime/h001_runtime/smoke_vlmaps_alignment.py`
- Current map image: `research3/vlmaps-hm3d:20260508-timmfix`
- Current text image: `research3/vlmaps-text:20260508`

### 에이전트 추론

The selected artifact path is controlled Habitat pre-exploration export, trajectory-derived `alignment.json`, `VLMaps` map generation, candidate export, Habitat-world alignment, and navmesh verification.

Not allowed:

- GT object centroid based alignment
- target-id based candidate creation
- changing alignment or candidate extraction after seeing policy outcomes

## Calibration Artifact Job

Last completed recovery artifact:

```text
artifact_id: random256_v1
output_root: /tmp/research3-runs/h001_calibration_artifacts_random256_v1
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_v1/all_scenes_aligned.jsonl
policy_output_root: /tmp/research3-runs/h001_calibration_policy_random256_v1
```

Completed background job:

```text
session: h001-calib-artifacts-random256-20260509-233124
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/calibration-artifacts-random256-20260509-233124.log
status: /tmp/research3-runs/h001_calibration_artifacts_random256_v1/job_status.json
completion: completed, verified on 2026-05-10
coverage_check: rows=30, candidate_count=150, finite_position_candidates=150, scenes=5, queries=6
```

Completion verification:

```bash
cat /tmp/research3-runs/h001_calibration_artifacts_random256_v1/job_status.json
python - <<'PY'
import json
from pathlib import Path

root = Path('/tmp/research3-runs/h001_calibration_artifacts_random256_v1')
status = json.loads((root / 'job_status.json').read_text(encoding='utf-8'))
summary = json.loads((root / 'coverage_check.json').read_text(encoding='utf-8'))
print(json.dumps({'status': status, 'coverage_check': summary}, indent=2, sort_keys=True))
assert status['status'] == 'completed'
assert status['artifact_id'] == 'random256_v1'
assert status['frames'] == 256
assert summary['ok'] is True
PY
```

Coverage sanity command:

```bash
mkdir -p /tmp/research3-runs/h001_calibration_policy_random256_v1/coverage_sanity

sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_v1.json \
    --manifest-split calibration \
    --episodes 50 \
    --policies GTTargetOracle NoReobserve \
    --out /runs/h001_calibration_policy_random256_v1/coverage_sanity \
    --run-id h001_calibration_random256_coverage_sanity_20260509 \
    --candidate-backend artifact_jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_v1/all_scenes_aligned.jsonl"
```

Coverage sanity result:

```text
date_checked: 2026-05-10
summary: /tmp/research3-runs/h001_calibration_policy_random256_v1/coverage_sanity/summary.json
artifact_coverage: /tmp/research3-runs/h001_calibration_policy_random256_v1/coverage_sanity/artifact_coverage.json
coverage_sanity_log: runtime/logs/calibration-random256-coverage-sanity-20260510-143038.log
artifact_coverage_log: runtime/logs/calibration-random256-artifact-coverage-20260510-143058.log
overall_pass: false
failed_gate: reachable_correct_and_wrong_pass
reachable_correct_and_wrong_rate: 0.26
required_rate: 0.50
candidate_label_coverage: 1.0
no_reobserve_wrong_goal_visit_rate: 0.28
```

Do not run policy comparison for `random256_v1` unless a later recovery artifact passes the hard coverage gate.

Coverage failure decision:

```text
date_checked: 2026-05-10
decision: run candidate-budget recovery before scene replacement or backend revision
next_artifact_id: random256_k10_v1
FRAMES: 256
MAX_CANDIDATES: 10
TOP_PERCENTILE: 98.0
scenes: same calibration scenes
policy_comparison: blocked until hard coverage passes
decision_note: 04_first_experiment.md
```

## Candidate-Budget Recovery Run Contract

### 사실

The next recovery run changes only candidate budget:

```text
artifact_id: random256_k10_v1
output_root: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
policy_output_root: /tmp/research3-runs/h001_calibration_policy_random256_k10_v1
FRAMES: 256
MAX_CANDIDATES: 10
TOP_PERCENTILE: 98.0
scenes: same five calibration scenes
queries: bed, chair, plant, sofa, toilet, tv_monitor
trajectory_policy: same random navigable pre-exploration
policy_thresholds: unchanged
```

Expected files:

```text
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/job_status.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/coverage_check.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_raw.jsonl
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/scenes/<scene>/export/export_summary.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/scenes/<scene>/verify_map.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/scenes/<scene>/aligned.jsonl
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/scenes/<scene>/artifact_summary.json
```

### 에이전트 추론

This run isolates one factor: increasing the per-query candidate budget from `5` to `10`. If reachable correct-and-wrong ambiguity improves, the first-probe substrate was candidate-budget limited. If it still fails, the next decision should compare scene replacement with reachability-diverse candidate extraction.

Launch command:

```bash
cd /home/yoohyun/research3
TS=$(date +%Y%m%d-%H%M%S)
SESSION="h001-calib-artifacts-random256-k10-${TS}"
LOG="hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/calibration-artifacts-random256-k10-${TS}.log"
OUT="/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1"
mkdir -p hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs "$OUT"
printf '%s\n' "$SESSION" > "$OUT/tmux_session.txt"
printf '%s\n' "$LOG" > "$OUT/log_path.txt"
tmux new-session -d -s "$SESSION" \
  "bash -lc 'set -o pipefail; cd /home/yoohyun/research3 && ARTIFACT_ID=random256_k10_v1 TRAJECTORY_SUFFIX=calib_random256_k10_v1 FRAMES=256 MAX_CANDIDATES=10 TOP_PERCENTILE=98.0 OUT_ROOT=/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1 ./hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/calibration_artifact_job.sh 2>&1 | tee -a \"$LOG\"; rc=\$?; echo \"[\$(date -Is)] job exit status: \$rc\" | tee -a \"$LOG\"; exit \$rc'"
```

Progress check:

```bash
cat /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/job_status.json
tail -n 40 "$(cat /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/log_path.txt)"
```

Completion verification:

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path('/tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1')
status = json.loads((root / 'job_status.json').read_text(encoding='utf-8'))
summary = json.loads((root / 'coverage_check.json').read_text(encoding='utf-8'))
expected_scenes = {'HkseAnWCgqk', 'XYyR54sxe6b', 'oEPjPNSPmzL', 'qk9eeNeR4vw', 'vLpv2VX547B'}
expected_queries = ['bed', 'chair', 'plant', 'sofa', 'toilet', 'tv_monitor']
print(json.dumps({'status': status, 'coverage_check': summary}, indent=2, sort_keys=True))
assert status['status'] == 'completed'
assert status['artifact_id'] == 'random256_k10_v1'
assert status['frames'] == 256
assert summary['ok'] is True
assert summary['rows'] == 30
assert set(summary['scenes']) == expected_scenes
assert summary['queries'] == expected_queries
assert summary['finite_position_candidates'] == summary['candidate_count']
assert summary['candidate_count'] >= 150
for scene in expected_scenes:
    scene_root = root / 'scenes' / scene
    for rel in ['export/export_summary.json', 'verify_map.json', 'aligned.jsonl', 'artifact_summary.json']:
        assert (scene_root / rel).exists(), f'missing {scene}/{rel}'
PY
```

Coverage sanity command:

```bash
mkdir -p /tmp/research3-runs/h001_calibration_policy_random256_k10_v1/coverage_sanity

sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_v1.json \
    --manifest-split calibration \
    --episodes 50 \
    --policies GTTargetOracle NoReobserve \
    --out /runs/h001_calibration_policy_random256_k10_v1/coverage_sanity \
    --run-id h001_calibration_random256_k10_coverage_sanity_20260510 \
    --candidate-backend artifact_jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_aligned.jsonl"
```

Artifact coverage gate:

```bash
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_artifact_coverage \
    --summary /runs/h001_calibration_policy_random256_k10_v1/coverage_sanity/summary.json \
    --out /runs/h001_calibration_policy_random256_k10_v1/coverage_sanity/artifact_coverage.json"
```

Pass rule:

```text
candidate_backend_uses_gt_for_action == false
candidate_label_coverage >= 0.70
episodes_with_reachable_correct_and_wrong_rate >= 0.50
NoReobserve wrong_goal_visit_rate >= 0.10
GTTargetOracle success_rate == 1.0
```

If the pass rule fails, do not run policy comparison. Write a second decision note comparing scene replacement and reachability-diverse backend revision.

Launched background job:

```text
date_launched: 2026-05-10
status: completed
session: h001-calib-artifacts-random256-k10-20260510-165427
working_directory: /home/yoohyun/research3
launch_script: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/launch_command.sh
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/calibration-artifacts-random256-k10-20260510-165427.log
output_root: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1
expected_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
expected_status: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_v1/job_status.json
verification_command: completion verification block above
```

Completion verification:

```text
date_verified: 2026-05-11
job_exit_status: 0
job_completed_at: 2026-05-10T17:08:15+09:00
rows: 30
candidate_count: 300
finite_position_candidates: 300
scenes: HkseAnWCgqk, XYyR54sxe6b, oEPjPNSPmzL, qk9eeNeR4vw, vLpv2VX547B
queries: bed, chair, plant, sofa, toilet, tv_monitor
all_expected_scene_files: present
```

Coverage sanity and diagnostic policy result:

```text
date_checked: 2026-05-11
coverage_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_v1/coverage_sanity
diagnostic_policy_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_v1/policy_comparison_diagnostic
coverage_sanity_log: runtime/logs/calibration-random256-k10-coverage-sanity-20260511-010532.log
artifact_coverage_log: runtime/logs/calibration-random256-k10-artifact-coverage-20260511-010633.log
diagnostic_policy_log: runtime/logs/calibration-random256-k10-policy-comparison-diagnostic-20260511-010704.log
candidate_label_coverage: 1.0
episodes_with_reachable_correct_and_wrong_rate: 0.48
required_reachable_correct_and_wrong_rate: 0.50
overall_hard_coverage_pass: false
diagnostic_policy_status: completed, not paper-facing evidence
SemanticOnly_wrong_goal_visit_rate: 0.50
NoReobserve_wrong_goal_visit_rate: 0.36
next_step: second recovery decision note
```

Second recovery decision:

```text
date_checked: 2026-05-11
decision: scene replacement first
reason: hard coverage failure is concentrated in weak scenes; scene replacement is the least confounded recovery
keep_scenes: XYyR54sxe6b, oEPjPNSPmzL, vLpv2VX547B
replace_scenes: HkseAnWCgqk, qk9eeNeR4vw
candidate_backend_revision: defer unless scene replacement fails
policy_objective_revision: design in parallel, but do not evaluate as evidence until coverage passes
next_step: scene replacement recovery run contract
decision_note: 04_first_experiment.md
```

## Scene Replacement Recovery Run Contract

### 사실

This recovery changes only the calibration scenes. Candidate extraction, query set, pre-exploration length, candidate budget, and provisional policy parameters remain fixed.

```text
artifact_id: random256_k10_sr1_v1
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_sr1.json
scene_specs: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/sr1_scenes.txt
output_root: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
policy_output_root: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1
FRAMES: 256
MAX_CANDIDATES: 10
TOP_PERCENTILE: 98.0
queries: bed, chair, plant, sofa, toilet, tv_monitor
```

Scene policy:

| Role | Scene | Source |
| --- | --- | --- |
| replacement | `1S7LAXRdDqK` | HM3D train, not held-out `first_eval` |
| kept | `vLpv2VX547B` | previous calibration scene, high ambiguity in `random256_k10_v1` |
| replacement | `1UnKg1rAb8A` | HM3D train, not held-out `first_eval` |
| kept | `oEPjPNSPmzL` | previous calibration scene, high ambiguity in `random256_k10_v1` |
| kept | `XYyR54sxe6b` | previous calibration scene, nonzero ambiguity in `random256_k10_v1` |

Generated manifest check:

```text
calibration episodes: 50
calibration scene counts: 10 each
total manifest rows: 460
manifest verification: ok
```

Expected files:

```text
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/job_status.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/coverage_check.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_raw.jsonl
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/scenes/<scene>/export/export_summary.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/scenes/<scene>/verify_map.json
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/scenes/<scene>/aligned.jsonl
/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/scenes/<scene>/artifact_summary.json
```

### 에이전트 추론

This run tests whether the hard ambiguity coverage failure was caused mainly by weak scene selection. It should not be interpreted as a policy improvement run. If coverage passes, run calibration policy comparison with the same `SemanticOnly` parameters before changing the policy objective.

Launch command:

```bash
cd /home/yoohyun/research3
TS=$(date +%Y%m%d-%H%M%S)
SESSION="h001-calib-artifacts-random256-k10-sr1-${TS}"
LOG="hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/calibration-artifacts-random256-k10-sr1-${TS}.log"
OUT="/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1"
SCENES="/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/sr1_scenes.txt"
mkdir -p hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs "$OUT"
printf '%s\n' "$SESSION" > "$OUT/tmux_session.txt"
printf '%s\n' "$LOG" > "$OUT/log_path.txt"
tmux new-session -d -s "$SESSION" \
  "bash -lc 'set -o pipefail; cd /home/yoohyun/research3 && SCENE_SPECS_FILE=\"$SCENES\" ARTIFACT_ID=random256_k10_sr1_v1 TRAJECTORY_SUFFIX=calib_random256_k10_sr1_v1 FRAMES=256 MAX_CANDIDATES=10 TOP_PERCENTILE=98.0 OUT_ROOT=/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1 ./hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/calibration_artifact_job.sh 2>&1 | tee -a \"$LOG\"; rc=\$?; echo \"[\$(date -Is)] job exit status: \$rc\" | tee -a \"$LOG\"; exit \$rc'"
```

Launched background job:

```text
date_launched: 2026-05-11
status: completed
session: h001-calib-artifacts-random256-k10-sr1-20260511-115330
working_directory: /home/yoohyun/research3
log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/calibration-artifacts-random256-k10-sr1-20260511-115330.log
output_root: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1
scene_specs: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/sr1_scenes.txt
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_sr1.json
expected_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
expected_status: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/job_status.json
verification_command: completion verification block above
initial_status_check: job_status.json reports running
completion_status_check: job_status.json reports completed
completion_verified: 2026-05-11
rows: 30
candidate_count: 300
finite_position_candidates: 300
scenes: 1S7LAXRdDqK, 1UnKg1rAb8A, XYyR54sxe6b, oEPjPNSPmzL, vLpv2VX547B
coverage_gate: passed
episodes_with_reachable_correct_and_wrong_rate: 0.66
candidate_label_coverage: 1.0
NoReobserve_wrong_goal_visit_rate: 0.38
policy_comparison_status: completed
SemanticOnly_wrong_goal_visit_rate: 0.54
SemanticOnly_success_rate: 0.30
SemanticOnly_SPL: 0.215
next_policy_step: implementation contract for `SemanticVerifyTop` and `EvidenceGatedSemanticOnly`
```

Progress check:

```bash
cat /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/job_status.json
tail -n 40 "$(cat /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/log_path.txt)"
```

Completion verification:

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path('/tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1')
status = json.loads((root / 'job_status.json').read_text(encoding='utf-8'))
summary = json.loads((root / 'coverage_check.json').read_text(encoding='utf-8'))
expected_scenes = {'1S7LAXRdDqK', '1UnKg1rAb8A', 'XYyR54sxe6b', 'oEPjPNSPmzL', 'vLpv2VX547B'}
expected_queries = ['bed', 'chair', 'plant', 'sofa', 'toilet', 'tv_monitor']
print(json.dumps({'status': status, 'coverage_check': summary}, indent=2, sort_keys=True))
assert status['status'] == 'completed'
assert status['artifact_id'] == 'random256_k10_sr1_v1'
assert status['frames'] == 256
assert summary['ok'] is True
assert summary['rows'] == 30
assert set(summary['scenes']) == expected_scenes
assert summary['queries'] == expected_queries
assert summary['finite_position_candidates'] == summary['candidate_count']
assert summary['candidate_count'] >= 300
for scene in expected_scenes:
    scene_root = root / 'scenes' / scene
    for rel in ['export/export_summary.json', 'verify_map.json', 'aligned.jsonl', 'artifact_summary.json']:
        assert (scene_root / rel).exists(), f'missing {scene}/{rel}'
PY
```

Coverage sanity command:

```bash
mkdir -p /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/coverage_sanity

sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_sr1.json \
    --manifest-split calibration \
    --episodes 50 \
    --policies GTTargetOracle NoReobserve \
    --out /runs/h001_calibration_policy_random256_k10_sr1_v1/coverage_sanity \
    --run-id h001_calibration_random256_k10_sr1_coverage_sanity_20260511 \
    --candidate-backend artifact_jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl"
```

Artifact coverage gate:

```bash
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_artifact_coverage \
    --summary /runs/h001_calibration_policy_random256_k10_sr1_v1/coverage_sanity/summary.json \
    --out /runs/h001_calibration_policy_random256_k10_sr1_v1/coverage_sanity/artifact_coverage.json"
```

Pass rule before policy comparison:

```text
candidate_backend_uses_gt_for_action == false
candidate_label_coverage >= 0.70
episodes_with_reachable_correct_and_wrong_rate >= 0.50
NoReobserve wrong_goal_visit_rate >= 0.10
GTTargetOracle success_rate == 1.0
```

If this pass rule fails, do not tune `SemanticOnly`. Compare reachability-diverse backend revision against query/category revision before launching another recovery job.

Policy comparison command, after a recovery artifact passes coverage:

```bash
mkdir -p /tmp/research3-runs/h001_calibration_policy_random256_k10_v1/policy_comparison

sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_v1.json \
    --manifest-split calibration \
    --episodes 50 \
    --policies GTTargetOracle NoReobserve RandomReobserve SemanticOnly \
    --out /runs/h001_calibration_policy_random256_k10_v1/policy_comparison \
    --run-id h001_calibration_random256_k10_policy_comparison_20260510 \
    --candidate-backend artifact_jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_v1/all_scenes_aligned.jsonl \
    --semantic-uncertainty-trigger 0.60 \
    --semantic-tie-band 0.01 \
    --semantic-reobs-view-bonus 1"
```

## Ground Truth Policy

Use GT only for:

- correctness labels
- shortest-path reference
- oracle upper bounds
- tiny harness validation

Do not use GT to tune `SemanticOnly` or `SemanticSLAM` on evaluation splits.

## Baseline Implementation Order

1. `GTTargetOracle`: verify shortest path and success-distance semantics.
2. `NoReobserve`: commit to top candidate.
3. `RandomReobserve`: choose random reachable nearby viewpoint before commit.
4. `GTCandidateOracle`: separate candidate-set coverage from policy failure.
5. `GTViewOracle`: upper bound for active re-observation.
6. `SemanticOnly`: first proposed non-GT policy.
7. `FrontierReobserve` / `CAReStyle`: stronger non-GT baselines.
8. `SemanticSLAM`: Step 4-5 extension.

## Tiny Smoke Subset

Before any full run, use:

- 1-2 HM3D scenes
- 5-10 ObjectNav episodes
- 5-10 HM3D-OVON `val_seen` or `val_unseen` episodes after loader works
- no result claims from smoke subset

Smoke must verify:

- scene loads
- episode loads
- target object references are resolvable
- shortest path can be computed
- candidate correctness can be logged
- `episodes.jsonl`, `candidate_decisions.jsonl`, `viewpoint_decisions.jsonl`, `summary.json` are produced

## Runtime Smoke Command Shape

Expected future command:

```bash
sg docker -c 'docker run --rm --gpus all --ipc=host \
  -v /tmp/research3-data:/data:ro \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:YYYYMMDD \
  python -m h001_runtime.run_smoke \
    --dataset hm3d_objectnav_v2 \
    --episodes 10 \
    --policies GTTargetOracle NoReobserve RandomReobserve \
    --out /runs/h001_smoke'
```

Do not create `/runs/h001_smoke` in the repository. Runtime outputs should go under `/tmp/research3-runs` until an experiment workflow promotes them.

## Minimal Success Gate

The runtime integration is ready for first probe when:

- Docker image builds from a pinned base image.
- HM3D ObjectNav v2 scene and episode load inside Docker.
- HM3D-OVON shard load is confirmed inside Docker.
- `GTTargetOracle`, `NoReobserve`, and `RandomReobserve` produce logs on the same tiny episode subset.
- `wrong_goal_visit` is commit-based, and `wrong_goal_pass_through` is diagnostic only.
- `wasted_path_total`, `wasted_path_wrong_goal`, and `wasted_path_reobserve` are either valid numbers or explicitly `null` with reason.
- GT oracle references are reported separately from deployable baselines.

## Implementation Risks

| Risk | Mitigation |
| --- | --- |
| Habitat dependency stack conflicts with `VLMaps` | keep `habitat-h001` separate from `vlmaps-smoke` |
| candidate extraction is slower than episode harness | start with GT-assisted diagnostic backend |
| ObjectNav and OVON episode schemas differ | implement `EpisodeLoader` adapters with common output fields |
| synonym handling changes wrong-goal labels | keep raw query, synonym group, and accepted target ids in logs |
| re-observation cost hurts `SPL` | report `wasted_path_reobserve` separately from `wasted_path_wrong_goal` |

## User Decision Needed

- Whether `habitat-h001` should use a minimal Habitat runtime first or reuse an existing baseline repository.
- Accepted `SPL` drop threshold for first-probe success.
- Whether to prioritize HM3D ObjectNav v2 or HM3D-OVON for the first non-GT semantic candidate backend.
