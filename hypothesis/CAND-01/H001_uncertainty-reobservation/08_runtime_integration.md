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

## Policy Objective Revision Implementation Contract

### 사실

Current recovered-substrate result:

```text
artifact_id: random256_k10_sr1_v1
manifest: manifests/h001_splits_sr1.json
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
coverage_gate: passed
NoReobserve_wrong_goal_visit_rate: 0.38
SemanticOnly_wrong_goal_visit_rate: 0.54
SemanticOnly_final_candidate_changed: 29 / 44 re-observation episodes
```

Implementation target:

```text
runtime_file: runtime/h001_runtime/run_smoke.py
new_policies: SemanticVerifyTop, EvidenceGatedSemanticOnly
first_output_root: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision
scope: calibration split only
held_out_eval_status: blocked until revised policy passes calibration gates
```

### 에이전트 추론

The next code change should separate two things that current `SemanticOnly` mixes:

- re-observation target selection;
- final goal candidate selection.

Do not change the candidate artifact, manifest, scene set, or candidate backend while implementing these policies. Otherwise the next result cannot isolate the policy objective revision.

### Policy Contracts

| Policy | Purpose | Final candidate switch allowed? | Evidence update required? |
| --- | --- | --- | --- |
| `SemanticOnly` | current diagnostic baseline | yes, by reachable tie candidate | no |
| `SemanticVerifyTop` | no-switch ablation | no | no |
| `EvidenceGatedSemanticOnly` | revised semantic utility | yes, only through switch gates | yes, non-GT only |

`SemanticVerifyTop` required behavior:

```text
top = candidates[0]
if U_sem(top) < semantic_uncertainty_trigger:
    commit top as `NoReobserve`
else:
    reobserve top.visit_position
    keep final candidate = top
    final_candidate_changed = false
    selected_for_reobserve = top
    selected_for_goal = top
```

`SemanticVerifyTop` is not expected to solve wrong-goal by itself. It is an ablation to test whether the previous failure came from premature candidate switching.

`EvidenceGatedSemanticOnly` required behavior:

```text
top_before = candidates[0]
trigger if U_sem(top_before) >= semantic_uncertainty_trigger
select a re-observation viewpoint using non-GT utility
compute post-reobservation non-GT evidence
candidate switch is allowed only if all switch gates pass
otherwise keep top_before
```

Switch gates:

```text
candidate_new is reachable
score_after(candidate_new) - score_after(top_before) >= delta_switch_score
U_sem_after(candidate_new) + delta_switch_uncertainty <= U_sem_after(top_before)
support_after(candidate_new) > support_before(candidate_new)
```

Default calibration constants:

```text
delta_switch_score: 0.03
delta_switch_uncertainty: 0.05
semantic_uncertainty_trigger: 0.60
semantic_tie_band: 0.01
max_reobservations: 1
evidence_update_mode: support_proxy first, image_feature later
```

### Required Runtime Refactor

Add small helpers rather than embedding all logic inside `run_policy`:

```text
candidate_paths(cache, scene, start, candidates)
should_reobserve(candidate, candidates)
select_verify_top(...)
select_evidence_gated_viewpoint(...)
apply_evidence_update(...)
passes_switch_gate(...)
policy_transition_log(...)
```

The first implementation can use `support_proxy` as a non-GT evidence update:

```text
score_after = score_before
view_count_after(observed_candidate) = view_count_before + semantic_reobs_view_bonus
U_sem_after = uncertainty_fields(candidate, candidates, extra_view_count=bonus_for_observed_candidate)
```

This proxy is calibration-only and must be marked as lower confidence. Paper-facing evidence should later use actual visual-language feature response or visibility-weighted support from the re-observation view.

### Required CLI Additions

```text
--semantic-delta-switch-score 0.03
--semantic-delta-switch-uncertainty 0.05
--semantic-evidence-mode support_proxy
--semantic-max-reobservations 1
```

Do not expose a held-out evaluation run until these remain fixed after calibration.

### Required Log Additions

Add these fields to `viewpoint_decisions.jsonl` when policy is `SemanticVerifyTop` or `EvidenceGatedSemanticOnly`:

```text
evidence_update_mode
final_candidate_id_before
final_candidate_id_after
switch_gate_pass
switch_gate_reason
score_delta_after_reobserve
U_sem_delta_after_reobserve
support_delta_after_reobserve
```

Add these aggregate metrics to `summary.json`:

```text
final_candidate_changed_rate
switch_gate_pass_rate
mean_score_delta_after_reobserve
mean_U_sem_delta_after_reobserve
mean_travel_cost_to_reobserve
```

Existing required fields must remain:

```text
candidate_backend_uses_gt_for_action == false
wrong_goal_visit is commit-based
wrong_goal_pass_through remains diagnostic only
GTTargetOracle remains reference only
```

### Implementation Smoke Command

After implementation, run:

```bash
mkdir -p /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision

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
    --policies GTTargetOracle NoReobserve RandomReobserve SemanticOnly SemanticVerifyTop EvidenceGatedSemanticOnly \
    --out /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision \
    --run-id h001_calibration_random256_k10_sr1_policy_revision_20260511 \
    --candidate-backend artifact_jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --semantic-uncertainty-trigger 0.60 \
    --semantic-tie-band 0.01 \
    --semantic-reobs-view-bonus 1 \
    --semantic-delta-switch-score 0.03 \
    --semantic-delta-switch-uncertainty 0.05 \
    --semantic-evidence-mode support_proxy \
    --semantic-max-reobservations 1"
```

### Acceptance Gates

Implementation acceptance:

```text
summary.json includes SemanticVerifyTop and EvidenceGatedSemanticOnly
candidate_backend_uses_gt_for_action == false
SemanticVerifyTop final_candidate_changed_rate == 0
EvidenceGatedSemanticOnly logs switch_gate_pass_rate
all compared policies have 50 episodes
GTTargetOracle success_rate == 1.0
```

Calibration interpretation gate:

```text
SemanticVerifyTop should not increase wrong_goal_visit_rate above current SemanticOnly.
EvidenceGatedSemanticOnly must reduce wrong_goal_visit_rate versus current SemanticOnly.
Promotion to held-out first_eval requires EvidenceGatedSemanticOnly to reduce wrong_goal_visit_rate versus NoReobserve or explain why support_proxy is insufficient.
```

If `support_proxy` cannot reduce wrong-goal, the next implementation should add actual post-view visual-language re-scoring before Step 4-5.

Implementation status:

```text
SemanticVerifyTop: implemented
SemanticVerifyTop_smoke: passed on 5 calibration episodes
smoke_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/semantic_verify_top_smoke
final_candidate_changed_rate: 0.0
required_switch_log_fields: present
EvidenceGatedSemanticOnly: implemented with support_proxy
EvidenceGatedSemanticOnly_smoke: passed on 5 calibration episodes
full_policy_revision_run: completed on calibration split
full_policy_revision_output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 0.38
NoReobserve_wrong_goal_visit_rate: 0.38
SemanticOnly_wrong_goal_visit_rate: 0.54
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.0
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.0
next_policy_step: post-view visual-language re-scoring contract
```

## Post-View Visual-Language Re-scoring Contract

### 사실

The `support_proxy` policy revision is complete and calibration-only:

```text
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 0.38
NoReobserve_wrong_goal_visit_rate: 0.38
SemanticOnly_wrong_goal_visit_rate: 0.54
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.0
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.0
```

Existing runtime pieces:

```text
Habitat renderer/exporter: runtime/h001_runtime/export_hm3d_vlmaps.py
VLMaps map scorer: runtime/h001_runtime/export_vlmaps_artifact.py
VLMaps map image: research3/vlmaps-hm3d:20260508-timmfix
Habitat image: research3/habitat-h001:20260508-calib-artifacts
Text embeddings: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings
Candidate artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
Policy decision log: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl
```

### 에이전트 추론

`support_proxy` can prevent unsupported candidate switching, but it does not create new semantic evidence. A contribution-level active re-observation mechanism needs image-conditioned score updates from the actual selected viewpoint.

The next implementation should not put LSeg / `VLMaps` inside `habitat-h001`. Keep the two-image pattern:

1. `habitat-h001` renders re-observation RGB-D/pose frames from selected viewpoints.
2. `vlmaps-hm3d` computes visual-language score updates from those frames.
3. `run_smoke.py` consumes a fixed score artifact and applies switch gates.

This keeps Habitat evaluation, map generation, and visual-language scoring separately reproducible.

### Artifact Contract

Output root:

```text
/tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1
```

Expected files:

```text
postview_frames.jsonl
postview_scores.jsonl
summary.json
frames/<decision_id>/rgb.png
frames/<decision_id>/depth.npy
frames/<decision_id>/pose.txt
frames/<decision_id>/metadata.json
```

`postview_frames.jsonl` row:

```json
{
  "schema_version": "h001.postview.v1",
  "decision_id": "string",
  "run_id": "string",
  "episode_key": "string",
  "policy": "EvidenceGatedSemanticOnly",
  "scene_id": "string",
  "query": "string",
  "viewpoint_position": [0.0, 0.0, 0.0],
  "viewpoint_rotation": [0.0, 0.0, 0.0, 1.0],
  "rgb": "frames/<decision_id>/rgb.png",
  "depth": "frames/<decision_id>/depth.npy",
  "pose": "frames/<decision_id>/pose.txt",
  "uses_gt_for_action": false
}
```

`postview_scores.jsonl` row:

```json
{
  "schema_version": "h001.postview_score.v1",
  "decision_id": "string",
  "episode_key": "string",
  "scene_id": "string",
  "query": "string",
  "evidence_update_mode": "image_feature",
  "uses_gt_for_action": false,
  "candidate_scores": [
    {
      "candidate_id": "string",
      "candidate_rank_before": 1,
      "score_before": 0.0,
      "score_after": 0.0,
      "score_delta": 0.0,
      "U_sem_before": 0.0,
      "U_sem_after": 0.0,
      "support_before": 0.0,
      "support_after": 0.0,
      "support_delta": 0.0,
      "projected_pixel": [0.0, 0.0],
      "projection_status": "visible | occluded | out_of_fov | behind_camera | depth_mismatch | missing_frame",
      "score_source": "openai_clip_local_crop"
    }
  ]
}
```

### Scoring Rule

For each `EvidenceGatedSemanticOnly` re-observation decision:

1. render RGB-D from the chosen `viewpoint_position` and `viewpoint_rotation`;
2. project top candidate and tied candidates into the rendered view using camera pose and intrinsics;
3. compute local image-text score for the query around each visible candidate projection;
4. update `score_after`, `support_after`, and `U_sem_after`;
5. run switch gates using only the score artifact.

First scoring defaults:

```text
candidate_set: top candidate + candidates within semantic_tie_band
crop_radius_px: 12
depth_tolerance_m: 0.75
score_source: OpenAI CLIP local crop cosine
score_calibration: raw_clip_cosine
support_after: support_before + 1 only if projection_status == visible
score_after: local image-text score if visible, else score_before
```

Scale note:

```text
The first implemented scorer writes raw OpenAI CLIP image-text cosine scores. These are not on the same calibrated scale as the existing VLMaps map candidate scores, so `run_smoke.py` image_feature loading must either gate on relative post-view evidence or introduce an explicit calibration rule before using `score_delta_after_reobserve` as a switch condition.
```

Not allowed:

```text
candidate_correct
GT target id
distance to GT target
choosing switch candidate by correctness label
tuning switch gates on held-out first_eval
```

### Required New Modules

Keep these as separate commands:

```text
runtime/h001_runtime/export_postview_frames.py
runtime/h001_runtime/score_postview_vlm.py
```

Required `run_smoke.py` additions:

```text
--semantic-evidence-mode image_feature
--semantic-postview-score-artifact /runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
```

When `image_feature` mode is selected, `EvidenceGatedSemanticOnly` must:

- load score updates by `episode_key` and decision/candidate id;
- use `score_after`, `U_sem_after`, and `support_after` from the artifact;
- when `score_calibration = raw_clip_cosine`, compare switch candidates by relative post-view image-text score rather than by map-score delta;
- log `evidence_update_mode = image_feature`;
- set `candidate_backend_uses_gt_for_action = false`.

### Docker Command Shape

Frame export:

```bash
mkdir -p /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1

sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-data:/data:ro \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames \
    --data-root /data \
    --viewpoint-decisions /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --out-root /runs/h001_postview_scores_random256_k10_sr1_v1 \
    --policy EvidenceGatedSemanticOnly"
```

Visual-language scoring:

```bash
sg docker -c "docker run --rm --gpus all --ipc=host \
  -e HOME=/models \
  -e XDG_CACHE_HOME=/models/.cache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-models:/models \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/vlmaps-hm3d:20260508-timmfix \
  python -m h001_runtime.score_postview_vlm \
    --frames /runs/h001_postview_scores_random256_k10_sr1_v1/postview_frames.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --query-embeddings /runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings \
    --out /runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl \
    --device cpu \
    --crop-radius-px 12 \
    --depth-tolerance-m 0.75"
```

Implementation status:

```text
score_postview_vlm.py: implemented
smoke_output: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1_smoke/postview_scores.jsonl
smoke_rows_requested: 2
smoke_rows_scored: 2
smoke_visible_row_rate: 1.0
smoke_projection_status_counts: visible 13, out_of_fov 4, behind_camera 3
smoke_score_sources: openai_clip_local_crop 11, openai_clip_center_crop_fallback 2, not_used 7
uses_gt_for_action: false
```

Policy run:

```bash
sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.run_smoke \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_sr1.json \
    --manifest-split calibration \
    --episodes 50 \
    --policies GTTargetOracle NoReobserve SemanticVerifyTop EvidenceGatedSemanticOnly \
    --out /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision_image_feature \
    --run-id h001_calibration_random256_k10_sr1_image_feature_20260511 \
    --candidate-backend artifact_jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --semantic-evidence-mode image_feature \
    --semantic-postview-score-artifact /runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl \
    --semantic-uncertainty-trigger 0.60 \
    --semantic-tie-band 0.01 \
    --semantic-delta-switch-score 0.03 \
    --semantic-delta-switch-uncertainty 0.05"
```

Policy loader implementation status:

```text
run_smoke.py image_feature score artifact loader: implemented
postview_index_keys: episode_key, fallback episode_id + scene_basename + query
required_cli: --semantic-evidence-mode image_feature, --semantic-postview-score-artifact
gate_score_delta_for_raw_clip_cosine: candidate_postview_score - top_postview_score
missing_artifact_reason: missing_postview_score
top_visibility_reason: top_not_visible
local_loader_check: passed on 2 smoke post-view rows
uses_gt_for_action: false
next_step: post-view image_feature Docker smoke run
```

Policy image_feature smoke status:

```text
smoke_output: /tmp/research3-runs/h001_postview_image_feature_policy_smoke
episodes: 2
policies: GTTargetOracle, NoReobserve, EvidenceGatedSemanticOnly
candidate_backend_uses_gt_for_action: false
semantic_evidence_mode: image_feature
semantic_postview_score_rows: 2
semantic_postview_uses_gt_for_action: false
viewpoint_decision_rows: 2
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.0
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.0
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 1.0
postview_gate_reasons: score_delta_failed for both smoke rows
postview_score_calibration: raw_clip_cosine
interpretation: integration works, but raw CLIP crop score is not yet sufficient evidence for switching under the current delta gate.
next_step: full calibration post-view artifact generation or score calibration diagnostic before policy-scale comparison
```

### Full Calibration Post-View Artifact Scope

### 사실

Existing full calibration policy revision log:

```text
source_viewpoint_log: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl
EvidenceGatedSemanticOnly_viewpoint_rows: 50
unique_episode_keys: 50
unique_scenes: 5
queries: bed 10, chair 8, plant 10, sofa 10, toilet 6, tv_monitor 6
support_proxy_switch_reasons: score_delta_failed 33, no_reobserve 17
```

### 에이전트 추론

The next artifact should cover all 50 `EvidenceGatedSemanticOnly` calibration re-observation rows, not a held-out split and not only the two smoke rows. This is still a calibration diagnostic artifact, not a paper result. Its purpose is to measure projection quality and post-view score distribution before running a larger `image_feature` policy comparison.

Do not move to `first_eval` until this calibration artifact passes the artifact acceptance gates and a score calibration diagnostic explains whether `raw_clip_cosine` can be used directly or needs calibration.

### Scope Decision

```text
artifact_scope: full calibration diagnostic
rows: all EvidenceGatedSemanticOnly rows from policy_revision/viewpoint_decisions.jsonl
expected_frame_rows: 50
expected_score_rows: 50
candidate_set: top candidate + candidates within semantic_tie_band, capped at 10
semantic_tie_band: 0.01
crop_radius_px: 12
depth_tolerance_m: 0.75
score_source: openai_clip_local_crop with selected-candidate center fallback
score_calibration: raw_clip_cosine
output_root: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1
held_out_eval_status: blocked
```

Long-running job record:

```text
working_directory: /home/yoohyun/research3
log_directory: logs/
frame_export_log: logs/postview-frames-fullcalib-<timestamp>.log
score_log: logs/postview-score-fullcalib-<timestamp>.log
expected_files:
  /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_frames.jsonl
  /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
  /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/summary.json
verification:
  rows in postview_frames.jsonl == 50
  rows in postview_scores.jsonl == 50
  uses_gt_for_action == false
  summary.json postview_scoring.visible_row_rate >= 0.70
```

Frame export job launch:

```text
status: completed
launched_at: 2026-05-12 08:24:07
tmux_session: h001-postview-frames-fullcalib-20260512-082407
log: logs/postview-frames-fullcalib-20260512-082407.log
working_directory: /home/yoohyun/research3
output_path: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1
expected_files:
  postview_frames.jsonl
  summary.json
  frames/<decision_id>/rgb.png
  frames/<decision_id>/depth.npy
  frames/<decision_id>/pose.txt
  frames/<decision_id>/metadata.json
verification_command:
  python - <<'PY'
  import json
  from pathlib import Path
  root = Path('/tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1')
  rows = [json.loads(line) for line in (root / 'postview_frames.jsonl').read_text().splitlines() if line.strip()]
  assert len(rows) == 50
  assert all(row.get('uses_gt_for_action') is False for row in rows)
  assert all((root / row['rgb']).exists() and (root / row['depth']).exists() and (root / row['pose']).exists() and (root / row['metadata']).exists() for row in rows)
  print({'rows': len(rows), 'ok': True})
  PY
```

Exact command:

```bash
sg docker -c 'docker run --rm --gpus all --ipc=host --user <uid>:<gid> -e HOME=/tmp -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime -v /tmp/research3-data:/data:ro -v /tmp/research3-runs:/runs -v /home/yoohyun/research3:/workspace:ro research3/habitat-h001:20260508-calib-artifacts micromamba run -n base python -m h001_runtime.export_postview_frames --data-root /data --viewpoint-decisions /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl --out-root /runs/h001_postview_scores_random256_k10_sr1_v1 --policy EvidenceGatedSemanticOnly'
```

Frame export completion verification:

```text
completed_at: 2026-05-12 08:24:36
exit_code: 0
output_size: 5.4M
postview_frames_exists: true
summary_exists: true
rows_requested_summary: 50
rows_exported_summary: 50
rows_verified: 50
unique_scenes: 5
uses_gt_for_action: false
missing_expected_files: 0
summary_ok: true
next_step: full calibration post-view VLM scoring Docker job launch
```

VLM scoring job launch:

```text
status: completed
launched_at: 2026-05-12 08:28:44
tmux_session: h001-postview-score-fullcalib-20260512-082844
log: logs/postview-score-fullcalib-20260512-082844.log
working_directory: /home/yoohyun/research3
input_frames: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_frames.jsonl
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
query_embeddings: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings
output_path: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
expected_files:
  postview_scores.jsonl
  summary.json with postview_scoring
verification_command:
  python - <<'PY'
  import json, math
  from pathlib import Path
  root = Path('/tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1')
  rows = [json.loads(line) for line in (root / 'postview_scores.jsonl').read_text().splitlines() if line.strip()]
  visible = [score for row in rows for score in row.get('candidate_scores', []) if score.get('projection_status') == 'visible']
  assert len(rows) == 50
  assert all(row.get('uses_gt_for_action') is False for row in rows)
  assert all(math.isfinite(float(score['score_after'])) for score in visible)
  print({'rows': len(rows), 'visible_scores': len(visible), 'ok': True})
  PY
```

Exact command:

```bash
sg docker -c 'docker run --rm --ipc=host --user <uid>:<gid> -e HOME=/models -e XDG_CACHE_HOME=/models/.cache -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime -v /tmp/research3-models:/models -v /tmp/research3-runs:/runs -v /home/yoohyun/research3:/workspace:ro research3/vlmaps-hm3d:20260508-timmfix python -m h001_runtime.score_postview_vlm --frames /runs/h001_postview_scores_random256_k10_sr1_v1/postview_frames.jsonl --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl --query-embeddings /runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings --out /runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl --device cpu --semantic-tie-band 0.01 --max-candidates-per-frame 10 --crop-radius-px 12 --depth-tolerance-m 0.75'
```

VLM scoring completion verification:

```text
completed_at: 2026-05-12 08:35:05
exit_code: 0
output_size: 5.5M
postview_scores_exists: true
summary_exists: true
rows_requested_summary: 50
rows_scored_summary: 50
rows_verified: 50
candidate_score_count: 263
visible_scores: 127
visible_row_count: 50
visible_row_rate: 1.0
finite_visible_scores: true
uses_gt_for_action: false
summary_scoring_ok: true
projection_status_counts:
  visible: 127
  out_of_fov: 57
  behind_camera: 79
score_source_counts:
  openai_clip_local_crop: 83
  openai_clip_center_crop_fallback: 44
  not_used: 136
raw_clip_cosine_visible_range: 0.1720 to 0.2455
raw_clip_cosine_visible_mean: 0.2083
next_step: image_feature score calibration diagnostic design
```

## Image Feature Score Calibration Diagnostic Design

### 사실

Current full calibration post-view score artifact:

```text
postview_scores: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
policy_candidate_labels: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/candidate_decisions.jsonl
policy_viewpoints: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl
score_rows: 50
visible_candidate_scores: 127
visible_candidate_scores_with_labels: 127
visible_correct_candidates: 41
visible_wrong_candidates: 86
rows_with_at_least_1_visible_candidate: 50
rows_with_at_least_2_visible_candidates: 27
rows_with_visible_correct_candidate: 29
raw_clip_cosine_visible_range: 0.1720 to 0.2455
raw_clip_cosine_correct_mean: 0.2135
raw_clip_cosine_wrong_mean: 0.2058
precheck_pairwise_auc_correct_vs_wrong: 0.638
precheck_raw_clip_visible_top_correct_rows: 23 / 50
precheck_top_before_visible_correct_rows: 18 / 50
```

GT-derived `candidate_correct` labels are available for all visible candidate scores, but they are diagnostic labels only. They must not be used by `EvidenceGatedSemanticOnly` during action selection.

### 에이전트 추론

The current `raw_clip_cosine` signal has a narrow dynamic range and only borderline correctness separation in the pre-check. The next diagnostic should decide whether:

- raw CLIP crop cosine can be used directly as post-view evidence;
- query-normalized or rank-based evidence is safer;
- projection/viewpoint quality is the main bottleneck;
- a stronger visual-language scorer is needed before policy-scale comparison.

### Diagnostic Inputs

```text
postview_scores_jsonl: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
candidate_decisions_jsonl: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/candidate_decisions.jsonl
viewpoint_decisions_jsonl: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl
policy: EvidenceGatedSemanticOnly
split_role: calibration only
uses_gt_for_action: false
uses_gt_for_analysis: true
```

### Diagnostic Outputs

Use a runtime output directory, not a repository folder:

```text
output_root: /tmp/research3-runs/h001_postview_score_calibration_random256_k10_sr1_v1
candidate_score_table: candidate_score_table.jsonl
row_summary: row_summary.jsonl
query_breakdown: query_breakdown.json
threshold_sweep: threshold_sweep.jsonl
summary: summary.json
```

### Required Measurements

Coverage and projection:

```text
visible_row_rate
visible_candidate_rate
rows_with_at_least_2_visible_candidates
projection_status_counts by query
score_source_counts by query
center_fallback_rate
depth_mismatch_rate if available
```

Score separation with diagnostic labels:

```text
correct_vs_wrong_auc
correct_mean_raw_clip_cosine
wrong_mean_raw_clip_cosine
per_query_correct_vs_wrong_auc
visible_top1_correct_rate
rank_improvement_over_top_before
rows_where_correct_candidate_visible_but_raw_score_not_top
```

Policy-facing calibration alternatives:

```text
raw_delta = raw_score(candidate) - raw_score(top_before)
query_zscore_delta = zscore_by_query(candidate) - zscore_by_query(top_before)
row_rank_delta = rank_score(candidate) - rank_score(top_before)
margin_to_best_visible_wrong
threshold_sweep over raw_delta, query_zscore_delta, row_rank_delta
```

### Decision Gates

```text
Direct raw score usable:
  correct_vs_wrong_auc >= 0.70
  visible_top1_correct_rate >= 0.60 on rows with a visible correct candidate
  per-query results do not collapse for more than one query

Needs calibrated/rank evidence:
  0.60 <= correct_vs_wrong_auc < 0.70
  raw score improves ranking over top-before but absolute deltas are small
  query-normalized or rank-based delta is more stable than raw_delta

Needs scorer/viewpoint revision:
  correct_vs_wrong_auc < 0.60
  rows_with_at_least_2_visible_candidates < 25
  center_fallback dominates selected candidate evidence
  visible correct candidates often exist but are not ranked near top
```

### Promotion Rule

Do not run a full `image_feature` policy-scale comparison just because the artifact exists. Run it only after the diagnostic selects one action-facing evidence rule:

```text
evidence_rule: raw_delta | query_zscore_delta | row_rank_delta | defer
fixed_thresholds: selected on calibration only
held_out_eval_status: blocked until evidence_rule is fixed
```

If `evidence_rule = defer`, the next implementation should improve projection/viewpoint scoring or replace the crop-based CLIP scorer before rerunning policy comparison.

### Diagnostic Implementation And Run

```text
status: completed
date_checked: 2026-05-12
script: runtime/h001_runtime/analyze_postview_scores.py
docker_image: research3/habitat-h001:20260508-calib-artifacts
output_root: /tmp/research3-runs/h001_postview_score_calibration_random256_k10_sr1_v1
candidate_score_table_rows: 263
row_summary_rows: 50
threshold_sweep_rows: 35
query_breakdown_exists: true
summary_exists: true
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Summary metrics:

```text
decision_gate: needs_calibrated_or_rank_evidence
correct_vs_wrong_auc: 0.6383
correct_mean_raw_clip_cosine: 0.2135
wrong_mean_raw_clip_cosine: 0.2058
visible_top1_correct_rate_when_correct_visible: 0.7931
raw_visible_top_correct_rows: 23 / 50
top_before_visible_correct_rows: 18 / 50
rank_improvement_over_top_before: +5 rows
center_fallback_rate_visible: 0.3465
collapsed_query_count_auc_lt_0_55: 3
```

Best threshold sweep row:

```text
rule: raw_delta
threshold: 0.0
eligible_rows: 50
switch_count: 12
switch_rate: 0.24
beneficial_switch_count: 5
harmful_switch_count: 0
neutral_switch_count: 7
top_before_correct_rate: 0.36
selected_correct_rate: 0.46
correct_rate_delta_vs_top_before: +0.10
wrong_goal_proxy_rate: 0.54
```

Per-query diagnostic:

```text
bed_auc: 0.4649
chair_auc: 0.6667
plant_auc: 0.5000
sofa_auc: 0.6667
toilet_auc: 0.9375
tv_monitor_auc: 0.4107
```

### 에이전트 추론

The diagnostic does not support direct absolute raw-score use because overall AUC is below `0.70` and three query groups have weak AUC. However, the best threshold sweep shows that a conservative relative rule can improve calibration selected-candidate correctness without harmful switches on this calibration set. This should be treated as a candidate evidence rule, not a final result, because the rule was selected using calibration labels.

Next decision should choose whether to implement `raw_delta >= 0.0` as the first fixed `image_feature` rule for policy-scale calibration comparison, or to defer for a stronger scorer due to weak per-query stability.

## Image Feature Evidence Rule Decision

### 사실

The diagnostic selected the following best calibration sweep row:

```text
evidence_rule: raw_delta
threshold: 0.0
eligible_rows: 50
switch_count: 12
switch_rate: 0.24
beneficial_switch_count: 5
harmful_switch_count: 0
neutral_switch_count: 7
top_before_correct_rate: 0.36
selected_correct_rate: 0.46
correct_rate_delta_vs_top_before: +0.10
```

The diagnostic also found:

```text
correct_vs_wrong_auc: 0.6383
decision_gate: needs_calibrated_or_rank_evidence
collapsed_query_count_auc_lt_0_55: 3
center_fallback_rate_visible: 0.3465
```

### 에이전트 추론

This is not strong enough to claim that raw CLIP crop score is a calibrated confidence. It is strong enough to justify one calibration policy comparison with a conservative relative rule, because the selected rule improves candidate correctness on calibration without harmful switches in the offline diagnostic.

Do not defer immediately, because the current evidence is informative enough to test whether the re-observation loop can improve actual navigation logs. Do not promote to held-out evaluation, because the rule was chosen using calibration labels and per-query stability is weak.

### Decision

```text
selected_evidence_rule: raw_delta
selected_threshold: 0.0
selected_scope: calibration policy-scale comparison only
held_out_eval_status: blocked
policy_target: EvidenceGatedSemanticOnly image_feature
score_source: openai_clip_local_crop / openai_clip_center_crop_fallback
score_calibration: raw_clip_cosine
```

Action-facing switch rule:

```text
top_before must have a visible post-view score
candidate_new must have a visible post-view score
candidate_new must be reachable
candidate_new must be within the pre-view semantic_tie_band
raw_delta = raw_clip_cosine(candidate_new) - raw_clip_cosine(top_before)
raw_delta >= 0.0
support_delta(candidate_new) > 0
```

Do not use CLIP-derived `U_sem_after` as an action gate for this rule:

```text
postview_uncertainty_gate_used: false
reason: raw_clip_cosine is not on the same scale as the pre-view VLMaps score, so CLIP-derived U_sem_after is not calibrated enough to reject a raw_delta switch.
```

Still log these fields for analysis:

```text
U_sem_before
U_sem_after
U_sem_delta_after_reobserve
switch_candidate_U_sem_delta
postview_score_calibration
postview_evidence_rule
postview_uncertainty_gate_used
```

### Implementation Target

Update `run_smoke.py` so `image_feature` mode supports an explicit score rule:

```text
--semantic-image-score-rule raw_delta
--semantic-delta-switch-score 0.0
--semantic-use-postview-uncertainty-gate false
```

Expected calibration command will use:

```text
--semantic-evidence-mode image_feature
--semantic-postview-score-artifact /runs/h001_postview_scores_random256_k10_sr1_v1/postview_scores.jsonl
--semantic-image-score-rule raw_delta
--semantic-delta-switch-score 0.0
```

### Failure Interpretation

```text
If wrong_goal_visit_rate improves below NoReobserve: proceed to a fixed-rule held-out eval plan.
If selected candidate correctness improves but wrong_goal_visit does not: navigation/path-cost interaction is the blocker.
If wrong_goal_visit worsens: raw_delta is misleading despite calibration diagnostic; defer and improve scorer/viewpoint.
If switch_count remains near zero: implementation gates are too strict or visible candidate coverage is insufficient.
```

### Raw Delta Rule Implementation

```text
status: implemented
date_checked: 2026-05-12
runtime_file: runtime/h001_runtime/run_smoke.py
new_cli:
  --semantic-image-score-rule raw_delta
  --semantic-use-postview-uncertainty-gate false
summary_fields:
  semantic_image_score_rule
  semantic_use_postview_uncertainty_gate
viewpoint_log_fields:
  postview_evidence_rule
  postview_uncertainty_gate_used
```

Implementation smoke:

```text
smoke_output: /tmp/research3-runs/h001_postview_raw_delta_policy_smoke
episodes: 2
candidate_backend_uses_gt_for_action: false
semantic_evidence_mode: image_feature
semantic_image_score_rule: raw_delta
semantic_delta_switch_score: 0.0
semantic_use_postview_uncertainty_gate: false
semantic_postview_score_rows: 50
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.5
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.5
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 1.0
smoke_switch_gate_reasons: passed, score_delta_failed
uses_gt_for_action: false
```

### 에이전트 추론

The implementation now matches the selected calibration-only evidence rule. The two-episode smoke is not an outcome claim, but it confirms that the raw post-view score can actually change final candidate selection when the post-view uncertainty gate is disabled.

### Raw Delta Policy-Scale Calibration Run

```text
status: completed
date_checked: 2026-05-12
output: /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision_image_feature_raw_delta
episodes: 50
policies: GTTargetOracle, NoReobserve, SemanticOnly, SemanticVerifyTop, EvidenceGatedSemanticOnly
candidate_backend_uses_gt_for_action: false
semantic_evidence_mode: image_feature
semantic_image_score_rule: raw_delta
semantic_delta_switch_score: 0.0
semantic_use_postview_uncertainty_gate: false
semantic_postview_score_rows: 50
semantic_postview_uses_gt_for_action: false
episode_rows: 250
candidate_decision_rows: 2100
viewpoint_decision_rows: 144
EvidenceGatedSemanticOnly_viewpoint_rows: 50
EvidenceGatedSemanticOnly_gate_reasons:
  passed: 9
  score_delta_failed: 12
  no_reobserve: 29
```

Policy aggregate:

```text
GTTargetOracle_SR: 1.00
GTTargetOracle_SPL: 1.00
GTTargetOracle_wrong_goal_visit_rate: 0.00

NoReobserve_SR: 0.24
NoReobserve_SPL: 0.1531
NoReobserve_wrong_goal_visit_rate: 0.38

SemanticOnly_SR: 0.30
SemanticOnly_SPL: 0.2146
SemanticOnly_wrong_goal_visit_rate: 0.54
SemanticOnly_final_candidate_changed_rate: 0.6591

SemanticVerifyTop_SR: 0.24
SemanticVerifyTop_SPL: 0.1531
SemanticVerifyTop_wrong_goal_visit_rate: 0.38
SemanticVerifyTop_final_candidate_changed_rate: 0.0

EvidenceGatedSemanticOnly_raw_delta_SR: 0.26
EvidenceGatedSemanticOnly_raw_delta_SPL: 0.1690
EvidenceGatedSemanticOnly_raw_delta_wrong_goal_visit_rate: 0.38
EvidenceGatedSemanticOnly_raw_delta_switch_gate_pass_rate: 0.18
EvidenceGatedSemanticOnly_raw_delta_final_candidate_changed_rate: 0.18
```

### 에이전트 추론

`raw_delta` produced real candidate switching and slightly improved `Success Rate` / `SPL` over `NoReobserve`, but it did not reduce wrong-goal visit rate below `0.38`. This means the current evidence rule is better than unsupported `SemanticOnly` switching, but it is not yet sufficient for the core claim that semantic uncertainty-driven re-observation reduces wrong-goal navigation failures.

### Raw Delta Result Interpretation

#### 사실

Episode-level comparison against `NoReobserve`:

```text
wrong_goal_fixed: 0 / 50
wrong_goal_newly_introduced: 0 / 50
wrong_goal_unchanged_failure: 19 / 50
wrong_goal_unchanged_non_wrong_goal: 31 / 50
success_fixed: 1 / 50
success_newly_failed: 0 / 50
selected_candidate_correct_transitions:
  wrong_to_wrong: 29
  correct_to_correct: 18
  wrong_to_correct: 3
switch_gate_passed: 9 / 50
switch_gate_reasons: passed 9, score_delta_failed 12, no_reobserve 29
postview_projection_status: visible 50 / 50
postview_uncertainty_gate_used: false
```

#### 에이전트 추론

`raw_delta` is a conservative behavioral improvement over unsupported `SemanticOnly`: it avoids increasing wrong-goal visits while still allowing 9 candidate switches. It also fixes one `NoReobserve` failure into a success and introduces no new success failure.

The primary H001 gate is still not met. The run does not reduce `wrong_goal_visit_rate`, and none of the 19 `NoReobserve` wrong-goal failures are fixed. The current visual evidence therefore validates the mechanism only partially: post-view evidence can safely gate switching, but the evidence source is not yet discriminative enough for the main wrong-goal failure mode.

Likely bottlenecks:

- the CLIP crop score is too weak or query-collapsed for object disambiguation
- the selected viewpoint sees candidate regions but not sufficiently discriminative object evidence
- center-crop fallback is too frequent for a paper-facing evidence source
- the switch objective changes some candidates without targeting explicit wrong-goal rows
- travel cost and map-side uncertainty are not yet part of the utility

Do not promote this result to held-out evaluation. The next step is an evidence-source revision decision before another policy-scale comparison.

### Evidence Source Revision Decision

#### 사실

Additional diagnostic on `NoReobserve` wrong-goal rows:

```text
date_checked: 2026-05-12
scope: 19 NoReobserve wrong-goal episodes from calibration split
rows_with_visible_postview_candidate: 19 / 19
rows_with_at_least_2_visible_candidates: 10 / 19
rows_with_visible_correct_candidate: 6 / 19
raw_clip_top_correct_when_wrong_goal: 0 / 19
wrong_goal_rows_with_no_visible_correct_candidate: 13 / 19
query_breakdown:
  bed: correct visible 2 / 4, raw top correct 0 / 4
  chair: correct visible 2 / 4, raw top correct 0 / 4
  plant: correct visible 2 / 5, raw top correct 0 / 5
  sofa: correct visible 0 / 4, raw top correct 0 / 4
  toilet: correct visible 0 / 2, raw top correct 0 / 2
```

#### 에이전트 추론

The next revision should not be threshold tuning only. The failure has two parts:

- evidence coverage failure: in 13 / 19 wrong-goal rows, the post-view evidence did not expose a visible correct candidate;
- evidence ranking failure: in the 6 rows where a correct candidate was visible, the raw CLIP crop score did not rank it first.

Selected next direction:

```text
decision: build postview_evidence_v2 before another policy-scale run
primary change: candidate-directed multi-heading / multi-crop post-view evidence
secondary change: object-centered local crop aggregation with action-facing center-crop fallback disabled
deferred change: stronger open-vocabulary detector/segmenter scorer, unless crop-only v2 still fails the diagnostic gate
held_out_eval_status: blocked
raw_delta_crop_only_status: keep as ablation baseline
```

Rejected alternatives:

| Alternative | Decision | Reason |
| --- | --- | --- |
| query-specific threshold tuning only | reject | cannot fix rows where correct candidate is not visible in evidence |
| immediate held-out evaluation | reject | calibration primary wrong-goal gate failed |
| stronger single-frame scorer only | defer | may help visible-correct rows but does not address 13 / 19 coverage failures |
| travel-cost tuning first | defer | current bottleneck is semantic evidence quality, not re-observation cost arbitration |

Minimum gate for `postview_evidence_v2`:

```text
wrong-goal diagnostic rows with visible correct candidate should increase above 6 / 19
raw top or aggregated top should recover at least one NoReobserve wrong-goal row in calibration
center-crop fallback must be logged separately and must not drive action-facing switches
all action-facing evidence must remain non-GT
```

Next implementation plan should specify new artifact schema, rendering/scoring commands, Docker smoke checks, and the exact policy comparison gate.

### Evidence Source Revision Implementation Plan

#### 사실

Current evidence-source blocker:

```text
current_artifact: h001.postview_score.v1
current_frame_policy: one RGB-D frame per EvidenceGatedSemanticOnly viewpoint row
current_action_score: raw_clip_cosine from local crop, with center-crop fallback for selected observed candidate
current_wrong_goal_rows: 19
wrong_goal_rows_with_visible_correct_candidate: 6 / 19
raw_clip_top_correct_on_wrong_goal_rows: 0 / 19
held_out_eval_status: blocked
```

#### 에이전트 추론

`postview_evidence_v2` should improve visibility coverage without changing the physical travel-cost model first. The first implementation should therefore keep the same re-observation position from `EvidenceGatedSemanticOnly`, but render multiple camera headings at that position. This tests whether the failure is caused by heading/FOV/crop evidence before adding a more expensive multi-viewpoint travel policy.

#### Implementation Scope

Do not change:

- calibration manifest
- candidate artifact
- physical re-observation position
- baseline policies
- wrong-goal definition
- GT usage boundary

Add:

```text
new_frame_exporter: runtime/h001_runtime/export_postview_frames_v2.py
new_scorer: runtime/h001_runtime/score_postview_v2.py
runtime_policy_extension: EvidenceGatedSemanticOnly image_feature with agg_local_delta
new_artifact_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
raw_delta_crop_only_status: ablation baseline
```

#### Frame Export V2 Contract

Input:

```text
viewpoint_decisions: /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl
candidate_artifact: /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
policy: EvidenceGatedSemanticOnly
```

Output:

```text
postview_frames_v2.jsonl
frames/<decision_id>/<heading_id>/rgb.png
frames/<decision_id>/<heading_id>/depth.npy
frames/<decision_id>/<heading_id>/pose.txt
frames/<decision_id>/<heading_id>/metadata.json
summary.json
```

One `postview_frames_v2.jsonl` row should represent a decision and contain multiple rendered headings:

```json
{
  "schema_version": "h001.postview.v2",
  "decision_id": "string",
  "episode_key": "string",
  "scene_id": "string",
  "query": "string",
  "physical_viewpoint_position": [0.0, 0.0, 0.0],
  "physical_viewpoint_source": "EvidenceGatedSemanticOnly",
  "candidate_set_rule": "semantic_tie_band",
  "heading_policy": "candidate_bearing_offsets",
  "yaw_offsets_deg": [-30.0, 0.0, 30.0],
  "rendered_headings": [
    {
      "heading_id": "string",
      "target_candidate_id": "string",
      "rotation_source": "bearing_to_candidate | stored_viewpoint_rotation",
      "yaw_offset_deg": 0.0,
      "rgb": "string",
      "depth": "string",
      "pose": "string",
      "metadata": "string"
    }
  ],
  "uses_gt_for_action": false
}
```

Heading generation:

```text
candidate set: top candidate plus candidates within semantic_tie_band, capped by max_candidates_per_decision
heading per candidate: bearing from physical_viewpoint_position to candidate.position
offsets: -30, 0, +30 degrees by default
include stored_viewpoint_rotation as diagnostic heading
deduplicate headings whose yaw differs by less than 10 degrees
```

#### Scoring V2 Contract

Action-facing evidence should use local projected crops only:

```text
score_source: openai_clip_multiview_local_crop
score_calibration: aggregate_raw_clip_cosine
center_crop_fallback: diagnostic only, never action-facing
strict_depth_check: true by default for action-facing score
candidate_point_field: position
crop_radii_px: 12, 24, 36
aggregate_rule: max over valid local crops, with visible/depth-consistent support count logged
```

Output file should stay loadable by the policy runner:

```text
postview_scores.jsonl
schema_version: h001.postview_score.v2
evidence_update_mode: image_feature
candidate_scores[].raw_image_text_score: aggregate action score
candidate_scores[].score_after: aggregate action score
candidate_scores[].projection_status: visible only if at least one local crop is action-valid
candidate_scores[].score_source: openai_clip_multiview_local_crop
candidate_scores[].score_calibration: aggregate_raw_clip_cosine
candidate_scores[].frame_evidence: per-heading / per-crop diagnostic list
candidate_scores[].action_eligible: true | false
candidate_scores[].center_fallback_used_for_action: false
uses_gt_for_action: false
```

Candidate aggregate fields:

```text
heading_visible_count
depth_consistent_count
valid_crop_count
best_local_raw_clip_cosine
mean_top2_local_raw_clip_cosine
best_heading_id
best_crop_box_xyxy
best_crop_radius_px
center_fallback_score_diagnostic
center_fallback_used_for_action: false
```

#### Runtime Policy Extension

Add one action-facing rule:

```text
--semantic-image-score-rule agg_local_delta
```

Switch gate:

```text
top_before has action_eligible visible aggregate score
candidate_new has action_eligible visible aggregate score
candidate_new is reachable
candidate_new is within semantic_tie_band before re-observation
agg_local_delta = aggregate_score(candidate_new) - aggregate_score(top_before)
agg_local_delta >= 0.0
candidate_new.valid_crop_count > 0
center_fallback_used_for_action == false
```

Still log:

```text
raw_delta
agg_local_delta
heading_visible_count
valid_crop_count
best_heading_id
postview_evidence_rule: agg_local_delta
```

#### Docker Smoke Contract

Frame export smoke:

```bash
mkdir -p logs
LOG=logs/postview-evidence-v2-frames-smoke-$(date +%Y%m%d-%H%M%S).log
sg docker -c 'docker run --rm --gpus all --ipc=host \
  --user <uid>:<gid> \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-data:/data:ro \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --out-root /runs/h001_postview_scores_v2_random256_k10_sr1_v1_smoke \
    --policy EvidenceGatedSemanticOnly \
    --max-decisions 2 \
    --max-candidates-per-decision 5 \
    --yaw-offsets -30,0,30' > "$LOG" 2>&1
```

Scoring smoke:

```bash
LOG=logs/postview-evidence-v2-score-smoke-$(date +%Y%m%d-%H%M%S).log
sg docker -c 'docker run --rm --ipc=host \
  --user <uid>:<gid> \
  -e HOME=/models \
  -e XDG_CACHE_HOME=/models/.cache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-models:/models \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/vlmaps-hm3d:20260508-timmfix \
  python -m h001_runtime.score_postview_v2 \
    --frames /runs/h001_postview_scores_v2_random256_k10_sr1_v1_smoke/postview_frames_v2.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --query-embeddings /runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings \
    --out /runs/h001_postview_scores_v2_random256_k10_sr1_v1_smoke/postview_scores.jsonl \
    --device cpu \
    --semantic-tie-band 0.01 \
    --crop-radii-px 12,24,36 \
    --strict-depth-check \
    --no-center-fallback-for-action' > "$LOG" 2>&1
```

Smoke verification:

```text
postview_frames_v2 rows == 2
rendered_headings per row >= 2
postview_scores rows == 2
uses_gt_for_action == false
candidate_scores exist for top candidate
center_fallback_used_for_action == false for every candidate score
at least one candidate has action_eligible == true
summary.json records heading_count, valid_crop_count, action_eligible_count
```

#### Calibration Diagnostic Gate

Run full calibration v2 only after smoke passes. The diagnostic gate before policy-scale comparison is:

```text
wrong_goal_rows_with_visible_correct_candidate > 6 / 19
aggregated_top_correct_on_wrong_goal_rows >= 1 / 19
center_fallback_used_for_action == 0
action_eligible row rate >= 0.70
uses_gt_for_action == false
```

#### Policy Comparison Gate

Run policy-scale calibration only after the diagnostic gate passes:

```text
policies: GTTargetOracle, NoReobserve, SemanticOnly, SemanticVerifyTop, EvidenceGatedSemanticOnly
candidate_backend: artifact_jsonl
semantic_evidence_mode: image_feature
semantic_image_score_rule: agg_local_delta
semantic_postview_score_artifact: /runs/h001_postview_scores_v2_random256_k10_sr1_v1/postview_scores.jsonl
```

Promotion beyond calibration requires:

```text
EvidenceGatedSemanticOnly_v2_wrong_goal_visit_rate < NoReobserve_wrong_goal_visit_rate
wrong_goal_fixed_vs_NoReobserve >= 1
wrong_goal_newly_introduced_vs_NoReobserve == 0
center_fallback_used_for_action == 0
SR and SPL are not worse than NoReobserve after accounting for re-observation cost
```

If v2 improves candidate evidence but does not reduce wrong-goal visits, the next revision should move to viewpoint selection rather than scorer tuning.

### Postview Evidence V2 Docker Smoke

#### 사실

Implementation files:

```text
frame_exporter: runtime/h001_runtime/export_postview_frames_v2.py
scorer: runtime/h001_runtime/score_postview_v2.py
policy_loader_update: runtime/h001_runtime/run_smoke.py supports --semantic-image-score-rule agg_local_delta
```

Frame export smoke:

```text
date_checked: 2026-05-12
log: logs/postview-evidence-v2-frames-smoke-20260512-122544.log
output_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1_smoke
schema_version: h001.postview.v2
rows_requested: 2
rows_exported: 2
rendered_heading_count: 17
headings_per_row: 7, 10
yaw_offsets_deg: -30, 0, 30
uses_gt_for_action: false
status: passed
```

Scoring smoke:

```text
date_checked: 2026-05-12
log: logs/postview-evidence-v2-score-smoke-20260512-122611.log
output: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1_smoke/postview_scores.jsonl
schema_version: h001.postview_score.v2
rows_scored: 2
candidate_score_count: 6
action_eligible_candidate_count: 5
action_eligible_row_rate: 1.0
valid_crop_count: 26
score_source_counts:
  openai_clip_multiview_local_crop: 5
  not_used: 1
projection_status_counts:
  visible: 5
  behind_camera: 1
center_fallback_used_for_action: false
uses_gt_for_action: false
status: passed
```

Policy integration smoke:

```text
date_checked: 2026-05-12
log: logs/postview-evidence-v2-policy-smoke-20260512-122856.log
output: /tmp/research3-runs/h001_postview_evidence_v2_policy_smoke
episodes: 2
policies: NoReobserve, EvidenceGatedSemanticOnly
semantic_evidence_mode: image_feature
semantic_image_score_rule: agg_local_delta
semantic_postview_score_rows: 2
semantic_postview_uses_gt_for_action: false
EvidenceGatedSemanticOnly_switch_gate_pass_rate: 0.5
EvidenceGatedSemanticOnly_final_candidate_changed_rate: 0.5
EvidenceGatedSemanticOnly_wrong_goal_visit_rate: 0.5
NoReobserve_wrong_goal_visit_rate: 1.0
switch_gate_reasons:
  passed: 1
  top_not_visible: 1
status: passed
```

#### 에이전트 추론

The v2 smoke validates the implementation path: multi-heading rendering, aggregate local-crop scoring, and `agg_local_delta` policy loading work in Docker without GT action usage. The 2-episode policy numbers are not result evidence, but the gate behavior is informative: one row switched under v2 evidence and one row was blocked because the top candidate was not action-visible. The next step should be a calibration diagnostic over all 50 calibration rows before any policy-scale v2 comparison.

### Postview Evidence V2 Diagnostic Implementation

#### 사실

Implementation file:

```text
diagnostic_script: runtime/h001_runtime/analyze_postview_scores_v2.py
schema_version: h001.postview_score_calibration.v2
```

Diagnostic outputs:

```text
candidate_score_table.jsonl
row_summary.jsonl
query_breakdown.json
threshold_sweep.jsonl
summary.json
```

Docker smoke:

```text
date_checked: 2026-05-13
log: logs/postview-evidence-v2-diagnostic-smoke-20260513-005714.log
input_scores: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1_smoke/postview_scores.jsonl
output_root: /tmp/research3-runs/h001_postview_score_calibration_v2_smoke
score_rows: 2
candidate_score_rows: 6
threshold_sweep_rows: 35
action_eligible_row_rate: 1.0
center_fallback_used_for_action_count: 0
aggregated_top_correct_on_wrong_goal_rows: 1
decision_gate: needs_full_calibration_artifact
uses_gt_for_action: false
uses_gt_for_analysis: true
status: passed
```

The smoke intentionally returns `needs_full_calibration_artifact` because it only analyzes two rows while the calibration gate expects 50 rows.

#### 에이전트 추론

The diagnostic implementation is ready for the full calibration artifact. It now measures the v2-specific gates that decide whether a policy-scale v2 comparison is justified:

```text
wrong_goal_rows_with_action_eligible_correct_candidate
aggregated_top_correct_on_wrong_goal_rows
center_fallback_used_for_action_count
action_eligible_row_rate
agg_local_delta threshold sweep
```

Next step is to generate the full 50-row `postview_evidence_v2` artifact in Docker, then run this diagnostic on that artifact before any full policy comparison.

### Postview Evidence V2 Full Calibration Artifact Job

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-postview-v2-fullcalib
job_script: runtime/jobs/postview_v2_fullcalib.sh
working_directory: /home/yoohyun/research3
output_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
status_file: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1/job_status.json
log: logs/postview-evidence-v2-fullcalib-20260513-011329.log
current_status_at_launch_check: running, stage=scoring
```

Expected files:

```text
postview_frames_v2.jsonl
postview_scores.jsonl
summary.json
job_status.json
frames/<decision_id>/<heading_id>/rgb.png
frames/<decision_id>/<heading_id>/depth.npy
frames/<decision_id>/<heading_id>/pose.txt
frames/<decision_id>/<heading_id>/metadata.json
```

Exact command is recorded in:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/postview_v2_fullcalib.sh
```

Progress check:

```bash
cat /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1/job_status.json
tmux list-sessions | rg 'h001-postview-v2-fullcalib'
tail -n 40 logs/postview-evidence-v2-fullcalib-20260513-011329.log
```

Completion verification:

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path('/tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1')
status = json.loads((root / 'job_status.json').read_text())
frames = [json.loads(line) for line in (root / 'postview_frames_v2.jsonl').open() if line.strip()]
scores = [json.loads(line) for line in (root / 'postview_scores.jsonl').open() if line.strip()]
summary = json.loads((root / 'summary.json').read_text())
scoring = summary.get('postview_scoring_v2', {})
assert status['status'] == 'completed'
assert len(frames) == 50
assert len(scores) == 50
assert all(row.get('uses_gt_for_action') is False for row in frames)
assert all(row.get('uses_gt_for_action') is False for row in scores)
assert all(
    score.get('center_fallback_used_for_action') is False
    for row in scores
    for score in row.get('candidate_scores', [])
)
assert scoring.get('rows_scored') == 50
print({
    'status': status,
    'frames': len(frames),
    'scores': len(scores),
    'candidate_score_count': scoring.get('candidate_score_count'),
    'action_eligible_row_rate': scoring.get('action_eligible_row_rate'),
})
PY
```

#### 에이전트 추론

This is a long-running artifact generation job, not a completed result yet. Do not run the full v2 diagnostic until `job_status.json` reports `completed` and the verification command passes.

Status check:

```text
date_checked: 2026-05-13
status_file_status: running
status_file_stage: scoring
tmux_session: h001-postview-v2-fullcalib active
docker_container: research3/vlmaps-hm3d:20260508-timmfix running score_postview_v2
frame_export_verified: 50 rows, 388 headings
postview_scores_status: not written yet
next_action: wait for scoring completion, then run verification command
```

Completion verification:

```text
date_checked: 2026-05-13
status: completed
stage: verified
completed_at: 2026-05-13T01:44:35+09:00
output_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
frames_rows: 50
scores_rows: 50
rendered_heading_count: 388
candidate_score_count: 172
action_eligible_candidate_count: 64
rows_with_action_eligible_candidate: 28
action_eligible_row_rate: 0.56
valid_crop_count: 420
projection_status_counts:
  visible: 64
  depth_mismatch: 60
  out_of_fov: 38
  behind_camera: 10
score_source_counts:
  openai_clip_multiview_local_crop: 64
  not_used: 108
center_fallback_used_for_action: false
uses_gt_for_action: false
```

#### 에이전트 추론

The full v2 artifact is complete and valid for diagnostic analysis. The low `action_eligible_row_rate` of `0.56` is below the planned diagnostic gate of `0.70`, so the next full diagnostic is likely to expose a visibility/depth-consistency bottleneck. Do not run policy-scale comparison until the diagnostic confirms whether the wrong-goal rows improved despite this low row rate.

### Postview Evidence V2 Full Diagnostic Result

#### 사실

```text
date_checked: 2026-05-13
script: runtime/h001_runtime/analyze_postview_scores_v2.py
log: logs/postview-evidence-v2-diagnostic-full-20260513-075647.log
output_root: /tmp/research3-runs/h001_postview_score_calibration_v2_random256_k10_sr1_v1
schema_version: h001.postview_score_calibration.v2
score_rows: 50
candidate_score_rows: 172
threshold_sweep_rows: 35
decision_gate: fails_v2_calibration_diagnostic_gate
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Gate metrics:

```text
action_eligible_row_rate: 0.56
required_action_eligible_row_rate: 0.70
rows_with_action_eligible_candidate: 28 / 50
center_fallback_used_for_action_count: 0
correct_vs_wrong_auc: 0.4968
rows_with_action_eligible_correct_candidate: 12 / 50
no_reobserve_wrong_goal_rows: 19
wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19
baseline_wrong_goal_visible_correct: 6 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19
```

Best threshold sweep row:

```text
rule: agg_local_delta
threshold: 0.0
rows: 50
switch_eligible_rows: 15
top_not_action_eligible_rows: 35
switch_count: 11
beneficial_switch_count: 2
harmful_switch_count: 2
neutral_switch_count: 7
selected_correct_rate: 0.36
top_before_correct_rate: 0.36
correct_rate_delta_vs_top_before: 0.0
```

Projection / score source:

```text
projection_status_counts:
  visible: 64
  depth_mismatch: 60
  out_of_fov: 38
  behind_camera: 10
score_source_counts:
  openai_clip_multiview_local_crop: 64
  not_used: 108
```

Query-level weak spots:

```text
bed: wrong_goal_rows_with_action_eligible_correct 0 / 4, auc 0.3333
chair: wrong_goal_rows_with_action_eligible_correct 2 / 4, auc 0.4444
plant: wrong_goal_rows_with_action_eligible_correct 2 / 5, auc 1.0000
sofa: wrong_goal_rows_with_action_eligible_correct 0 / 4, auc 0.1429
toilet: wrong_goal_rows_with_action_eligible_correct 0 / 2, auc 0.7778
tv_monitor: no wrong-goal rows, auc 0.2222
```

#### 에이전트 추론

`postview_evidence_v2` should not proceed to policy-scale comparison. It removed action-facing center fallback, but that exposed a coverage problem: only 28 / 50 rows have any action-eligible candidate and 35 / 50 rows have a top candidate that is not action-eligible. The score itself is also not discriminative enough because `correct_vs_wrong_auc` is approximately random.

The main bottleneck is visibility/depth consistency, not only CLIP thresholding:

- 60 candidate projections are rejected by strict depth mismatch;
- 38 are out of FOV even after candidate-bearing headings;
- wrong-goal rows with action-eligible correct candidates drop from the v1 baseline of 6 / 19 to 4 / 19;
- the best `agg_local_delta` sweep has equal beneficial and harmful switches and no selected-correct improvement.

Policy-scale comparison is blocked. The next revision should be a `postview_evidence_v2.1` visibility/depth ablation before changing the high-level policy:

```text
1. compare candidate_point_field=position vs visit_position
2. compare strict_depth_check=true vs diagnostic relaxed depth
3. log depth mismatch distance distribution by query and candidate correctness
4. test larger heading offsets or candidate-surface/visit-position projection before rescoring policy
```

### Postview Evidence V2.1 Visibility / Depth Ablation Plan

#### 사실

The full `postview_evidence_v2` diagnostic failed before policy-scale comparison:

```text
reference_artifact: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
reference_diagnostic: /tmp/research3-runs/h001_postview_score_calibration_v2_random256_k10_sr1_v1
action_eligible_row_rate: 0.56
correct_vs_wrong_auc: 0.4968
wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19
baseline_wrong_goal_visible_correct: 6 / 19
projection_status_counts:
  visible: 64
  depth_mismatch: 60
  out_of_fov: 38
  behind_camera: 10
center_fallback_used_for_action_count: 0
```

`score_postview_v2.py` already exposes the two controls needed for the next diagnostic:

```text
--candidate-point-field position | visit_position
--strict-depth-check / --no-strict-depth-check
```

#### 에이전트 추론

The current failure can come from at least three different causes, and they should not be mixed:

1. `position` may represent a semantic map node that is not visually inspectable from the selected re-observation pose.
2. Strict depth consistency may reject candidates that are semantically plausible but geometrically noisy under the current map / RGB-D alignment.
3. Multi-heading local crop CLIP evidence may be insufficient even when the candidate is visible.

Therefore `postview_evidence_v2.1` should isolate `point field` and `depth gate` before changing the active policy objective.

#### Ablation Matrix

| Variant | Point field | Depth gate | Purpose | Expected output |
| --- | --- | --- | --- | --- |
| `strict_position` | `position` | strict | Existing v2 reference | already complete |
| `relaxed_position` | `position` | relaxed | Test whether strict depth rejects useful evidence | new score + diagnostic artifact |
| `strict_visit` | `visit_position` | strict | Test whether candidate map point is the wrong visual anchor | new score + diagnostic artifact |
| `relaxed_visit` | `visit_position` | relaxed | Combined diagnostic if either previous variant improves | optional, run after first two |
| `wider_heading_export` | selected after above | strict first | Test FOV limitation, not depth limitation | only if `out_of_fov` remains dominant |

#### Diagnostic Outputs

Each v2.1 variant should produce:

```text
postview_scores.jsonl
summary.json
candidate_score_table.jsonl
row_summary.jsonl
query_breakdown.json
threshold_sweep.jsonl
```

Additional visibility/depth analysis should report:

```text
depth_mismatch_count_by_query
depth_error_m distribution for correct vs wrong candidates
action_eligible_row_rate by query
wrong_goal_rows_with_action_eligible_correct_candidate
top_not_action_eligible_rows
beneficial_switch_count vs harmful_switch_count under agg_local_delta
```

#### Gate Before Policy-Scale Comparison

Policy-scale comparison remains blocked unless a v2.1 variant satisfies all minimum diagnostic gates:

```text
center_fallback_used_for_action_count == 0
action_eligible_row_rate >= 0.70
wrong_goal_rows_with_action_eligible_correct_candidate >= 6 / 19
correct_vs_wrong_auc > 0.55
beneficial_switch_count > harmful_switch_count for the selected rule
```

Promotion to a paper-facing policy run is stronger:

```text
correct_vs_wrong_auc >= 0.60
selected_correct_rate > top_before_correct_rate in threshold_sweep
failure mode is explainable by query / projection / depth logs
```

#### Execution Rule

The next implementation should begin with a lightweight visibility/depth diagnostic over the existing v2 artifact. If that diagnostic shows that `depth_mismatch` or `visit_position` can plausibly recover coverage, launch the first full CLIP rescoring variants as background Docker jobs with timestamped logs:

```text
relaxed_position:
  out: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1

strict_visit:
  out: /tmp/research3-runs/h001_postview_scores_v2_1_strict_visit_random256_k10_sr1_v1
```

Do not run `postview_evidence_v2` or v2.1 policy-scale comparison until the diagnostic gate passes.

### Postview Evidence V2.1 Lightweight Visibility / Depth Diagnostic Result

#### 사실

```text
date_checked: 2026-05-13
script: runtime/h001_runtime/analyze_postview_visibility_v2.py
log: logs/postview-evidence-v2-1-visibility-diagnostic-20260513-081009.log
output_root: /tmp/research3-runs/h001_postview_visibility_v2_1_random256_k10_sr1_v1
schema_version: h001.postview_visibility_diagnostic.v2.1
score_rows: 50
frame_rows: 50
candidate_visibility_rows: 344
heading_visibility_rows: 3198
missing_frame_count: 0
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Generated files:

```text
candidate_visibility_table.jsonl
heading_visibility_table.jsonl
row_visibility_summary.jsonl
query_visibility_breakdown.json
summary.json
```

Field summary:

```text
position + strict depth:
  action_eligible_row_rate: 0.56
  rows_with_action_eligible_candidate: 28 / 50
  rows_with_action_eligible_correct_candidate: 12 / 50
  wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19
  projection_status_counts: visible 64, depth_mismatch 60, out_of_fov 38, behind_camera 10
  current_v2_action_mismatch_count: 0

position + relaxed depth:
  action_eligible_row_rate: 0.80
  rows_with_action_eligible_candidate: 40 / 50
  rows_with_action_eligible_correct_candidate: 26 / 50
  wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
  projection_status_counts: visible 124, out_of_fov 38, behind_camera 10

visit_position + strict depth:
  action_eligible_row_rate: 0.12
  rows_with_action_eligible_candidate: 6 / 50
  rows_with_action_eligible_correct_candidate: 2 / 50
  wrong_goal_rows_with_action_eligible_correct_candidate: 2 / 19
  projection_status_counts: visible 7, depth_mismatch 50, out_of_fov 63, behind_camera 52

visit_position + relaxed depth:
  action_eligible_row_rate: 0.60
  rows_with_action_eligible_candidate: 30 / 50
  rows_with_action_eligible_correct_candidate: 16 / 50
  wrong_goal_rows_with_action_eligible_correct_candidate: 7 / 19
  projection_status_counts: visible 57, out_of_fov 63, behind_camera 52
```

Query-level visibility recovery under `position + relaxed depth`:

```text
bed: strict rows 6 / 10 -> relaxed rows 10 / 10, wrong-goal correct 0 / 4 -> 2 / 4
chair: strict rows 4 / 8 -> relaxed rows 6 / 8, wrong-goal correct 2 / 4 -> 2 / 4
plant: strict rows 4 / 10 -> relaxed rows 6 / 10, wrong-goal correct 2 / 5 -> 2 / 5
sofa: strict rows 4 / 10 -> relaxed rows 6 / 10, wrong-goal correct 0 / 4 -> 0 / 4
toilet: strict rows 5 / 6 -> relaxed rows 6 / 6, wrong-goal correct 0 / 2 -> 0 / 2
tv_monitor: strict rows 5 / 6 -> relaxed rows 6 / 6, no wrong-goal rows
```

Recommended next variants from the diagnostic:

```text
run_relaxed_position_rescoring
consider_relaxed_visit_rescoring_after_first_two
```

#### 에이전트 추론

The lightweight diagnostic confirms that the previous v2 gate failure is primarily a strict depth-consistency bottleneck for the existing `position` anchor. The cross-check is consistent with the original v2 artifact because `position + strict depth` has `current_v2_action_mismatch_count == 0`.

`position + relaxed depth` is the highest-probability next run:

- it raises action-eligible row rate from `0.56` to `0.80`;
- it reaches the previous baseline wrong-goal correct-candidate coverage of `6 / 19`;
- it does not change the viewpoint policy or candidate anchor, so the ablation remains isolated.

`visit_position + strict depth` should not be run first because it collapses coverage to `0.12`. `visit_position + relaxed depth` may be useful later because wrong-goal correct-candidate coverage is `7 / 19`, but its overall row rate is only `0.60` and it introduces a larger FOV / behind-camera problem.

Next step: launch `relaxed_position` CLIP rescoring in Docker, then run the existing v2 calibration diagnostic on that rescored artifact. Policy-scale comparison remains blocked until score discriminativeness is verified.

### Postview Evidence V2.1 Relaxed Position Rescoring Job

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-postview-v2-1-relaxed-position
job_script: runtime/jobs/postview_v2_1_relaxed_position.sh
working_directory: /home/yoohyun/research3
source_root: /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
output_root: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1
status_file: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/job_status.json
log: logs/postview-evidence-v2-1-relaxed-position-20260513-082406.log
status_at_launch_check: running
stage_at_launch_check: scoring
```

The job reuses the existing `postview_evidence_v2` frame export and changes only the scoring gate:

```text
candidate_point_field: position
strict_depth_check: false
center_fallback_for_action: false
device: cpu
crop_radii_px: 12,24,36
max_candidates_per_frame: 5
```

Exact command is recorded in:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/postview_v2_1_relaxed_position.sh
```

Expected files:

```text
postview_frames_v2.jsonl
frames -> ../h001_postview_scores_v2_random256_k10_sr1_v1/frames
postview_scores.jsonl
summary.json
job_status.json
```

Progress check:

```bash
cat /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/job_status.json
tmux list-sessions | rg 'h001-postview-v2-1-relaxed-position'
tail -n 40 logs/postview-evidence-v2-1-relaxed-position-20260513-082406.log
```

Completion verification:

```bash
python - <<'PY'
import json
from pathlib import Path

root = Path('/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1')
status = json.loads((root / 'job_status.json').read_text())
rows = [json.loads(line) for line in (root / 'postview_scores.jsonl').open() if line.strip()]
summary = json.loads((root / 'summary.json').read_text())
scoring = summary.get('postview_scoring_v2', {})
assert status['status'] == 'completed'
assert len(rows) == 50
assert all(row.get('uses_gt_for_action') is False for row in rows)
assert all(
    score.get('center_fallback_used_for_action') is False
    for row in rows
    for score in row.get('candidate_scores', [])
)
assert scoring.get('rows_scored') == 50
assert float(scoring.get('action_eligible_row_rate') or 0.0) >= 0.70
print({
    'status': status,
    'rows': len(rows),
    'candidate_score_count': scoring.get('candidate_score_count'),
    'action_eligible_row_rate': scoring.get('action_eligible_row_rate'),
    'projection_status_counts': scoring.get('projection_status_counts'),
})
PY
```

#### 에이전트 추론

This is the minimum isolated rescoring needed after the v2.1 lightweight diagnostic. It should not be interpreted as a policy result. If the job completes and the score calibration diagnostic still shows random or harmful correct-vs-wrong separation, the next issue is the visual-language scorer rather than strict depth gating alone.

Completion verification:

```text
date_checked: 2026-05-13
status: completed
stage: verified
output_root: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1
scores_rows: 50
candidate_score_count: 172
action_eligible_candidate_count: 124
rows_with_action_eligible_candidate: 40
action_eligible_row_rate: 0.80
valid_crop_count: 1620
projection_status_counts:
  visible: 124
  out_of_fov: 38
  behind_camera: 10
score_source_counts:
  openai_clip_multiview_local_crop: 124
  not_used: 48
center_fallback_used_for_action: false
uses_gt_for_action: false
```

### Postview Evidence V2.1 Relaxed Position Diagnostic Result

#### 사실

```text
date_checked: 2026-05-13
script: runtime/h001_runtime/analyze_postview_scores_v2.py
log: logs/postview-evidence-v2-1-relaxed-position-diagnostic-20260513-122828.log
output_root: /tmp/research3-runs/h001_postview_score_calibration_v2_1_relaxed_position_random256_k10_sr1_v1
schema_version: h001.postview_score_calibration.v2
score_rows: 50
candidate_score_rows: 172
threshold_sweep_rows: 35
decision_gate: fails_v2_calibration_diagnostic_gate
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Gate metrics:

```text
action_eligible_row_rate: 0.80
rows_with_action_eligible_candidate: 40 / 50
rows_with_action_eligible_correct_candidate: 26 / 50
wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19
correct_vs_wrong_auc: 0.4939
correct_mean_aggregate_raw_clip_cosine: 0.2386
wrong_mean_aggregate_raw_clip_cosine: 0.2396
center_fallback_used_for_action_count: 0
```

Best threshold sweep row:

```text
rule: row_rank_delta
threshold: 0.3
switch_eligible_rows: 27
top_not_action_eligible_rows: 23
switch_count: 13
beneficial_switch_count: 4
harmful_switch_count: 2
neutral_switch_count: 7
selected_correct_rate: 0.40
top_before_correct_rate: 0.36
correct_rate_delta_vs_top_before: 0.04
```

Query-level weak spots:

```text
bed: auc 0.4167, wrong-goal eligible correct 2 / 4, aggregated top correct on wrong-goal 0 / 4
chair: auc 0.4375, wrong-goal eligible correct 2 / 4, aggregated top correct on wrong-goal 2 / 4
plant: auc 1.0000, wrong-goal eligible correct 2 / 5, aggregated top correct on wrong-goal 2 / 5
sofa: auc 0.3750, wrong-goal eligible correct 0 / 4, aggregated top correct on wrong-goal 0 / 4
toilet: auc 0.3600, wrong-goal eligible correct 0 / 2, aggregated top correct on wrong-goal 0 / 2
tv_monitor: auc 0.4762, no wrong-goal rows
```

#### 에이전트 추론

`relaxed_position` confirms that strict depth was a coverage bottleneck, but it does not solve the score-quality bottleneck. Coverage improves from `0.56` to `0.80`, yet `correct_vs_wrong_auc` remains approximately random and wrong candidates have a slightly higher mean aggregate score than correct candidates.

The best threshold sweep is weak positive evidence, not enough for a policy-scale comparison:

- selected correctness improves by only `0.04`;
- the best row still has harmful switches (`2`);
- `aggregated_top_correct_on_wrong_goal_rows` remains `4 / 19`, unchanged from strict v2;
- the gate requires discriminative score behavior, not only more visible crops.

`relaxed_visit` should be deferred for now. The lightweight diagnostic showed `visit_position + relaxed depth` has `action_eligible_row_rate == 0.60`, below the `0.70` gate, and this `relaxed_position` result indicates that the main remaining failure is the local CLIP scoring signal rather than strict depth alone. The next revision should target object-level or segmentation-aware visual evidence instead of another policy-scale run.

### Postview Evidence V3 Object-Level / Segmentation-Aware Scorer Plan

#### 사실

Current failed scorer evidence:

```text
v2 strict position:
  action_eligible_row_rate: 0.56
  correct_vs_wrong_auc: 0.4968
  wrong_goal_rows_with_action_eligible_correct_candidate: 4 / 19

v2.1 relaxed position:
  action_eligible_row_rate: 0.80
  correct_vs_wrong_auc: 0.4939
  wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
  aggregated_top_correct_on_wrong_goal_rows: 4 / 19
  correct_mean_aggregate_raw_clip_cosine: 0.2386
  wrong_mean_aggregate_raw_clip_cosine: 0.2396
```

Relevant literature hooks from the current survey:

```text
CARe:
  OpenMask3D stores visible-view CLIP crop features per object mask and uses uncertainty / multi-view consistency.

OVO-SLAM:
  uses 2D segments, CLIP/SigLIP descriptors, and multi-view descriptor merging for online open-vocabulary semantic maps tied to SLAM.

ConceptGraphs:
  builds object-centric nodes from RGB-D masks, CLIP/DINO-style features, 3D point clouds, captions, and spatial relations.

OpenScene:
  supports CLIP-aligned open-vocabulary 3D features, but is dense scene understanding rather than active re-observation.
```

#### 논문 주장

`CARe` claims that uncertainty and multi-view consistency can correct erroneous decisions in pre-explored semantic maps without additional labels. `OVO-SLAM` claims segment-level open-vocabulary descriptors can be maintained online with SLAM backbones. `ConceptGraphs` claims object-centric open-vocabulary 3D scene graphs are more compact and useful for planning than dense feature maps alone.

#### 에이전트 추론

The v2.1 result says the current bottleneck is no longer only candidate visibility. It is the evidence unit: local CLIP crops around projected pixels still include background, neighboring objects, and arbitrary scale. A top-tier-facing revision should therefore score object evidence rather than point-centered crops.

V3 should separate two questions:

1. Does object isolation improve correct-vs-wrong score separation?
2. If yes, can the object-level score be used as active semantic memory update and later SLAM utility?

#### V3 Variants

| Variant | Purpose | Dependency | Role |
| --- | --- | --- | --- |
| `v3a_depth_mask` | Use RGB-D depth connectivity around candidate projection to isolate a local object region, then CLIP-score masked object crop | existing frames only | first diagnostic implementation |
| `v3b_detector_box` | Use an open-vocabulary detector box for the query, then associate boxes with candidate projections | new detector checkpoint | scorer feasibility extension |
| `v3c_detector_sam_mask` | Use detector box + SAM/SAM2 mask, then score masked object region and mask-view consistency | new detector + segmenter checkpoints | paper-facing scorer candidate |
| `v3d_object_node_memory` | Aggregate per-candidate segment descriptors across headings and update semantic node uncertainty | v3c or object-map backbone | bridge toward Step 4-5 semantic memory / active SLAM utility |

#### Selected First Implementation

Start with `v3a_depth_mask`.

Reasons:

```text
uses existing v2/v2.1 RGB-D frames
requires no new model checkpoint download
keeps candidate_point_field=position and relaxed depth coverage fixed
isolates whether segmentation/object isolation helps the CLIP evidence itself
can be run on the same 50-row calibration artifact before any policy-scale run
```

This is a diagnostic scorer, not the final paper-facing system. If it improves separation, move to `v3c_detector_sam_mask` for a stronger open-vocabulary object scorer. If it does not improve separation, the failure is likely not only background contamination; model/query calibration or semantic map candidate quality must be revised.

#### V3A Scoring Contract

Input:

```text
postview_frames_v2.jsonl from /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1
frames/ RGB-D assets reused from /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
query_embeddings: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings
```

Core method:

```text
1. project candidate `position` into each candidate-bearing heading.
2. allow relaxed projection visibility, but log depth consistency separately.
3. around the projected pixel, build a local depth-connected component mask.
4. reject masks that are too small, too large, or disconnected from the projected point.
5. create masked RGB crop and box crop variants.
6. compute CLIP cosine for masked object crop, box crop, and optional background-suppressed crop.
7. aggregate per candidate by max masked score and view-consistency features.
```

Required candidate score fields:

```text
score_source: openai_clip_depth_mask_object_crop
score_calibration: object_mask_aggregate_raw_clip_cosine
object_mask_valid: bool
object_mask_area_px
object_mask_area_ratio
object_mask_depth_median
object_mask_depth_mad
object_mask_component_radius_px
object_mask_projection_in_component
masked_raw_clip_cosine
box_raw_clip_cosine
background_suppressed_raw_clip_cosine
mask_view_count
mask_score_std
mask_score_margin_to_box
projection_status
depth_check_status
center_fallback_used_for_action: false
uses_gt_for_action: false
```

Action-facing score rule:

```text
primary: masked_raw_clip_cosine max over valid object masks
fallback for analysis only: box_raw_clip_cosine
no center fallback for action
candidate action_eligible only if object_mask_valid == true
```

#### V3A Outputs

```text
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1
postview_scores.jsonl
summary.json
mask_debug/<decision_id>/<candidate_id>/<heading_id>_mask.png
mask_debug/<decision_id>/<candidate_id>/<heading_id>_crop.png
```

Diagnostic output:

```text
output_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1
candidate_score_table.jsonl
row_summary.jsonl
query_breakdown.json
threshold_sweep.jsonl
summary.json
```

#### V3A Gates

Artifact gate:

```text
score_rows == 50
uses_gt_for_action == false
center_fallback_used_for_action_count == 0
object_mask_valid_row_rate >= 0.60
action_eligible_row_rate >= 0.70
mask_debug samples exist for failed and passed rows
```

Score diagnostic gate before any policy-scale comparison:

```text
correct_vs_wrong_auc > 0.58
preferred paper-facing target: correct_vs_wrong_auc >= 0.60
wrong_goal_rows_with_action_eligible_correct_candidate >= 6 / 19
aggregated_top_correct_on_wrong_goal_rows > 4 / 19
best_sweep_beneficial_switch_count > best_sweep_harmful_switch_count
selected_correct_rate - top_before_correct_rate >= 0.06
```

Policy-scale comparison remains blocked unless the score diagnostic gate passes.

#### V3B / V3C Feasibility Gate

Move from `v3a_depth_mask` to foundation segmentation only if at least one condition holds:

```text
v3a improves AUC but not enough for policy gate
v3a masks fail because depth connectivity is noisy or includes neighboring furniture
query-level failures concentrate on visually cluttered categories such as bed, sofa, chair
```

Candidate model direction:

```text
detector-first: GroundingDINO or OWL-ViT / OWLv2 for text-conditioned boxes
mask refinement: SAM / SAM2 from detector boxes
descriptor: CLIP / SigLIP masked region embedding
association: candidate projection inside mask or nearest mask in image plane plus depth agreement
uncertainty: mask score entropy, view-consistency std, query-vs-distractor margin, support count
```

#### 사용자 판단 필요

No user decision is needed before `v3a_depth_mask` implementation because it uses existing artifacts and no new heavy downloads. User decision is needed before installing or downloading detector/SAM/SAM2 checkpoints for `v3b` / `v3c`.

### Postview Evidence V3A Depth-Mask Docker Smoke

#### 사실

Implementation file:

```text
script: runtime/h001_runtime/score_postview_v3_depth_mask.py
schema_version: h001.postview_score.v3a_depth_mask
score_source: openai_clip_depth_mask_object_crop
score_calibration: object_mask_aggregate_raw_clip_cosine
```

Smoke scoring run:

```text
date_checked: 2026-05-13
log: logs/postview-evidence-v3a-depth-mask-smoke-20260513-130424.log
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_smoke
input_frames: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl
rows_scored: 2
candidate_score_count: 10
action_eligible_candidate_count: 9
rows_with_action_eligible_candidate: 2 / 2
action_eligible_row_rate: 1.0
rows_with_object_mask_valid_candidate: 2 / 2
object_mask_valid_row_rate: 1.0
valid_mask_count: 31
debug_images_written: 20
projection_status_counts:
  visible: 9
  behind_camera: 1
score_source_counts:
  openai_clip_depth_mask_object_crop: 9
  not_used: 1
center_fallback_used_for_action: false
uses_gt_for_action: false
status: passed
```

Generated smoke files:

```text
postview_scores.jsonl
summary.json
mask_debug/*/*_mask.png
mask_debug/*/*_masked_crop.png
```

Diagnostic smoke:

```text
date_checked: 2026-05-13
log: logs/postview-evidence-v3a-depth-mask-diagnostic-smoke-20260513-130605.log
output_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_smoke
score_rows: 2
candidate_score_rows: 10
threshold_sweep_rows: 35
action_eligible_row_rate: 1.0
center_fallback_used_for_action_count: 0
correct_vs_wrong_auc: 0.5
decision_gate: passes_v2_calibration_diagnostic_gate
uses_gt_for_action: false
uses_gt_for_analysis: true
```

The smoke gate uses only two rows and relaxed thresholds, so it verifies compatibility and artifact generation only. It is not result evidence.

#### 에이전트 추론

The v3a implementation path is valid: existing RGB-D post-view frames can produce depth-connected object masks, masked CLIP object scores, debug masks/crops, and analyzer-compatible score files in Docker. The next useful evidence is a 50-row calibration artifact with the same scorer, followed by the calibration diagnostic using the v3a gates.

Full calibration should be launched as a background job because the 2-row CPU smoke took about 84 seconds.

### Postview Evidence V3A Full Calibration Job

#### 사실

```text
date_launched: 2026-05-13
tmux_session: h001-postview-v3a-fullcalib
job_script: runtime/jobs/postview_v3a_depth_mask_fullcalib.sh
working_directory: /home/yoohyun/research3
source_root: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1
diagnostic_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1
status_file: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/job_status.json
log: logs/postview-evidence-v3a-depth-mask-fullcalib-20260513-132125.log
status_at_launch_check: running
stage_at_launch_check: scoring
```

The job performs:

```text
1. copy postview_frames_v2.jsonl from v2.1 relaxed_position artifact.
2. reuse the existing rendered RGB-D frames via frames symlink.
3. run score_postview_v3_depth_mask.py over all 50 rows.
4. verify score rows, no GT action use, and no center fallback.
5. run analyze_postview_scores_v2.py on the v3a score artifact.
6. verify diagnostic output files.
```

Exact command is recorded in:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/postview_v3a_depth_mask_fullcalib.sh
```

Expected score files:

```text
postview_frames_v2.jsonl
frames -> ../h001_postview_scores_v2_random256_k10_sr1_v1/frames
postview_scores.jsonl
summary.json
mask_debug/
job_status.json
```

Expected diagnostic files:

```text
candidate_score_table.jsonl
row_summary.jsonl
query_breakdown.json
threshold_sweep.jsonl
summary.json
```

Progress check:

```bash
cat /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/job_status.json
tmux list-sessions | rg 'h001-postview-v3a-fullcalib'
tail -n 40 logs/postview-evidence-v3a-depth-mask-fullcalib-20260513-132125.log
```

Completion verification:

```bash
python - <<'PY'
import json
from pathlib import Path

score_root = Path('/tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1')
diag_root = Path('/tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1')
status = json.loads((score_root / 'job_status.json').read_text())
score_rows = [json.loads(line) for line in (score_root / 'postview_scores.jsonl').open() if line.strip()]
score_summary = json.loads((score_root / 'summary.json').read_text())['postview_scoring_v3a_depth_mask']
diag_summary = json.loads((diag_root / 'summary.json').read_text())
assert status['status'] == 'completed'
assert len(score_rows) == 50
assert all(row.get('uses_gt_for_action') is False for row in score_rows)
assert all(
    score.get('center_fallback_used_for_action') is False
    for row in score_rows
    for score in row.get('candidate_scores', [])
)
assert diag_summary.get('score_rows') == 50
print({
    'status': status,
    'score_rows': len(score_rows),
    'action_eligible_row_rate': score_summary.get('action_eligible_row_rate'),
    'object_mask_valid_row_rate': score_summary.get('object_mask_valid_row_rate'),
    'diagnostic_gate': diag_summary.get('decision_gate'),
    'correct_vs_wrong_auc': diag_summary.get('correct_vs_wrong_auc'),
})
PY
```

#### 에이전트 추론

This is an artifact and diagnostic job, not a policy-scale comparison. The next decision should wait for the diagnostic summary. The main question is whether object-level depth masks improve `correct_vs_wrong_auc` and wrong-goal aggregated-top correction beyond v2.1 `relaxed_position`.

Completion verification:

```text
date_checked: 2026-05-13
status: completed
stage: verified
output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1
diagnostic_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1
score_rows: 50
diagnostic_score_rows: 50
candidate_score_count: 172
action_eligible_candidate_count: 122
action_eligible_row_rate: 0.80
object_mask_valid_row_rate: 0.80
valid_mask_count: 374
debug_images_written: 240
center_fallback_used_for_action: false
uses_gt_for_action: false
```

### Postview Evidence V3A Full Calibration Result Interpretation

#### 사실

```text
date_checked: 2026-05-13
score_output_root: /tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1
diagnostic_output_root: /tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1
log: logs/postview-evidence-v3a-depth-mask-fullcalib-20260513-132125.log
decision_gate: fails_v2_calibration_diagnostic_gate
score_rows: 50
candidate_score_rows: 172
action_eligible_row_rate: 0.80
rows_with_action_eligible_correct_candidate: 26 / 50
wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19
rank_improvement_over_top_before: 7
correct_vs_wrong_auc: 0.5598
correct_mean_aggregate_raw_clip_cosine: 0.2309
wrong_mean_aggregate_raw_clip_cosine: 0.2287
projection_status_counts: visible 122, mask_invalid 2, out_of_fov 38, behind_camera 10
```

Comparison against `v2.1 relaxed_position`:

```text
correct_vs_wrong_auc: 0.4939 -> 0.5598
rank_improvement_over_top_before: 1 -> 7
best selected_correct_rate: 0.40 -> 0.48
best selected_correct_delta: +0.04 -> +0.12
best beneficial_switch_count: 4 -> 8
best harmful_switch_count: 2 -> 2
wrong_goal_rows_with_action_eligible_correct_candidate: 6 / 19 -> 6 / 19
aggregated_top_correct_on_wrong_goal_rows: 4 / 19 -> 4 / 19
action_eligible_row_rate: 0.80 -> 0.80
```

Best threshold sweep row:

```text
rule: agg_local_delta
threshold: 0.0
switch_eligible_rows: 27
top_not_action_eligible_rows: 23
switch_count: 14
beneficial_switch_count: 8
harmful_switch_count: 2
neutral_switch_count: 4
selected_correct_rate: 0.48
top_before_correct_rate: 0.36
correct_rate_delta_vs_top_before: 0.12
```

Query-level result:

```text
bed: auc 0.4545, wrong-goal eligible correct 2 / 4, aggregated top correct on wrong-goal 0 / 4
chair: auc 0.4792, wrong-goal eligible correct 2 / 4, aggregated top correct on wrong-goal 2 / 4
plant: auc 1.0000, wrong-goal eligible correct 2 / 5, aggregated top correct on wrong-goal 2 / 5
sofa: auc 0.3571, wrong-goal eligible correct 0 / 4, aggregated top correct on wrong-goal 0 / 4
toilet: auc 0.7200, wrong-goal eligible correct 0 / 2, aggregated top correct on wrong-goal 0 / 2
tv_monitor: auc 0.2667, no wrong-goal rows
```

#### 에이전트 추론

`v3a_depth_mask` is a meaningful scorer improvement over point-centered local crops, but it is not yet strong enough for policy-scale comparison.

Evidence for improvement:

- AUC improves from near-random `0.4939` to `0.5598`.
- Best selected-correct delta improves from `+0.04` to `+0.12`.
- Beneficial switches double from `4` to `8` while harmful switches stay at `2`.
- Correct candidates now have a slightly higher mean score than wrong candidates.

Remaining blocker:

- The planned paper-facing AUC gate was `> 0.58` and the stronger target was `>= 0.60`; v3a is below both.
- `aggregated_top_correct_on_wrong_goal_rows` remains `4 / 19`, unchanged from v2.1.
- `bed` and `sofa` remain weak, and `tv_monitor` collapses under the depth-mask score despite no wrong-goal rows.
- `wrong_goal_rows_with_action_eligible_correct_candidate` remains `6 / 19`, so object masking did not create new wrong-goal recovery coverage.

Therefore:

```text
policy_scale_comparison: blocked
held_out_evaluation: blocked
relaxed_visit_rescoring: still deferred
next_direction: v3b/v3c detector + SAM/SAM2 feasibility check, no checkpoint download before user approval
```

The result is useful for the research argument because it supports the claim that object-level evidence is more appropriate than local crops. It does not yet support the stronger claim that the current object-level evidence is sufficient to improve ObjectNav behavior.

### Postview Evidence V3B / V3C Detector + Segmentation Feasibility Check

#### 사실

Date checked: 2026-05-13.

Current local model cache:

```text
/tmp/research3-models/.cache/clip/ViT-B-32.pt
/tmp/research3-models/clip/ViT-B-32.pt
/tmp/research3-models/vlmaps/lseg/checkpoints
```

No local checkpoint was found for:

```text
GroundingDINO
OWL-ViT / OWLv2
SAM
SAM2
```

Current Docker image import check for `research3/vlmaps-hm3d:20260508-timmfix`:

```text
torch: available
torchvision: available
clip: available
transformers: missing
segment_anything: missing
sam2: missing
groundingdino: missing
cv2: available
PIL: available
numpy: available
torch_version: 2.7.1+cu128
cuda_available: false
```

Primary sources checked:

```text
GroundingDINO official GitHub:
https://github.com/IDEA-Research/GroundingDINO

SAM2 official GitHub:
https://github.com/facebookresearch/sam2

Meta SAM2 page:
https://ai.meta.com/research/sam2/

Hugging Face OWL-ViT docs:
https://huggingface.co/docs/transformers/model_doc/owlvit
```

#### 논문 주장 / 공식 문서 주장

`GroundingDINO` is documented as an open-set / open-vocabulary detector that accepts an image-text pair. `SAM2` is documented by Meta as a promptable segmentation model for images and videos, with the official repository providing inference code and checkpoint links. `OWL-ViT` is supported in Hugging Face `transformers` for open-vocabulary object detection.

#### 에이전트 추론

`v3b/v3c` cannot be executed in the current runtime without adding packages and model weights. This is expected and does not invalidate v3a; it only means the next step is environment design and checkpoint approval, not another immediate Docker smoke.

Feasibility ranking:

| Option | Description | Current feasibility | Research value | Risk |
| --- | --- | --- | --- | --- |
| `v3b_owlvit_box` | text-conditioned detector boxes, no mask model | blocked by missing `transformers` and checkpoint | lowest-complexity detector baseline | box-only evidence may still include background |
| `v3c_groundingdino_sam2` | text-conditioned boxes + SAM2 masks | blocked by missing packages and checkpoints | strongest paper-facing object evidence | heavier image, checkpoint, and association complexity |
| `v3c_groundingdino_sam` | text-conditioned boxes + original SAM masks | blocked by missing packages and checkpoints | mature still-image segmenter path | less aligned with video/sequence memory than SAM2 |
| API-based GroundingDINO 1.5 | external detector API | not recommended | fast external check | weak reproducibility and possible cost/network dependency |

Recommended path:

```text
1. Keep Habitat/runtime image unchanged.
2. Build a separate open-vocabulary perception image.
3. First implement a 2-row detector-only smoke on existing post-view RGB frames.
4. Then add SAM/SAM2 mask refinement only if detector boxes associate with projected candidates.
5. Do not run policy-scale comparison until detector+mask diagnostic beats v3a gates.
```

Proposed separate image:

```text
image_name: research3/openvocab-perception:<date>
base: CUDA/PyTorch image compatible with current torch stack, or a separate pinned environment
mounts:
  /tmp/research3-models:/models
  /tmp/research3-runs:/runs
  /home/yoohyun/research3:/workspace:ro
```

Proposed local model paths if user approves downloads:

```text
/tmp/research3-models/openvocab/owlvit/
/tmp/research3-models/openvocab/groundingdino/
/tmp/research3-models/openvocab/sam2/
```

Minimum v3b/v3c smoke contract:

```text
input: 2-row postview_frames_v2.jsonl smoke subset
outputs:
  detector_boxes.jsonl
  detector_candidate_associations.jsonl
  optional_segment_masks.jsonl
  debug_images/
required fields:
  query
  candidate_id
  heading_id
  box_xyxy
  detector_score
  projected_pixel_inside_box
  depth_agreement_m
  associated_to_candidate
  uses_gt_for_action: false
```

Promotion gates before full calibration:

```text
detector finds at least one query box in >= 70 percent of smoke rows
candidate projection can be associated to a detector box in >= 60 percent of smoke rows
debug images show boxes/masks are object-level rather than background-level
runtime per 2 rows is acceptable for background full calibration
```

Full calibration gates remain stricter than v3a:

```text
correct_vs_wrong_auc > 0.58
preferred target: correct_vs_wrong_auc >= 0.60
aggregated_top_correct_on_wrong_goal_rows > 4 / 19
selected_correct_rate - top_before_correct_rate >= 0.06
beneficial_switch_count > harmful_switch_count
```

#### 사용자 판단 필요

Proceeding beyond this feasibility check requires user approval to download checkpoints and/or build a new Docker image. The recommended next approval target is:

```text
first approval: v3b_owlvit_box smoke, using a separate openvocab-perception Docker image
second approval: v3c_groundingdino_sam2 if v3b boxes are useful but box-only evidence is insufficient
```

### OpenVocab Perception OWL-ViT Setup Job

#### 사실

User approved proceeding with a separate `openvocab-perception` image and `v3b_owlvit_box` checkpoint setup.

```text
date_launched: 2026-05-13
tmux_session: h001-openvocab-owlvit-setup
dockerfile: runtime/Dockerfile.openvocab-perception
job_script: runtime/jobs/openvocab_perception_owlvit_setup.sh
image: research3/openvocab-perception:20260513-owlvit
model_id: google/owlvit-base-patch32
model_dir: /tmp/research3-models/openvocab/owlvit/google_owlvit-base-patch32
output_root: /tmp/research3-runs/openvocab_perception_owlvit_setup
status_file: /tmp/research3-runs/openvocab_perception_owlvit_setup/job_status.json
log: logs/openvocab-perception-owlvit-setup-20260513-142201.log
status_at_launch_check: running
stage_at_launch_check: build_image
```

The job performs:

```text
1. build separate Docker image `research3/openvocab-perception:20260513-owlvit`.
2. verify imports for torch, torchvision, transformers, cv2, PIL, numpy.
3. download `google/owlvit-base-patch32` into a fixed local directory.
4. verify offline loading with `OwlViTProcessor` and `OwlViTForObjectDetection`.
```

Exact command is recorded in:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_owlvit_setup.sh
```

Progress check:

```bash
cat /tmp/research3-runs/openvocab_perception_owlvit_setup/job_status.json
tmux list-sessions | rg 'h001-openvocab-owlvit-setup'
tail -n 40 logs/openvocab-perception-owlvit-setup-20260513-142201.log
```

Completion verification:

```bash
python - <<'PY'
import json
from pathlib import Path

status_path = Path('/tmp/research3-runs/openvocab_perception_owlvit_setup/job_status.json')
model_dir = Path('/tmp/research3-models/openvocab/owlvit/google_owlvit-base-patch32')
status = json.loads(status_path.read_text())
assert status['status'] == 'completed'
expected_any = ['config.json', 'preprocessor_config.json']
assert all((model_dir / name).exists() for name in expected_any), sorted(p.name for p in model_dir.iterdir())
print({
    'status': status,
    'model_dir': str(model_dir),
    'model_files': len(list(model_dir.rglob('*'))),
})
PY

sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/models \
  -e HF_HOME=/models/.cache/huggingface \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -v /tmp/research3-models:/models \
  research3/openvocab-perception:20260513-owlvit \
  python -c 'from transformers import OwlViTForObjectDetection, OwlViTProcessor; p=\"/models/openvocab/owlvit/google_owlvit-base-patch32\"; OwlViTProcessor.from_pretrained(p, local_files_only=True); OwlViTForObjectDetection.from_pretrained(p, local_files_only=True); print(\"owlvit_offline_load_ok\")'"
```

#### 에이전트 추론

This setup keeps detector dependencies out of the Habitat and VLMaps runtime images. The next executable research task after completion is a `v3b_owlvit_box` 2-row smoke over existing post-view RGB frames, with detector boxes associated to projected semantic candidates.

### V3B OWL-ViT Box Smoke

#### 사실

The `openvocab-perception` setup job completed and offline model loading passed.

```text
status_file: /tmp/research3-runs/openvocab_perception_owlvit_setup/job_status.json
status: completed
stage: verified
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
default query, box_threshold 0.05, point_field position:
  output: /tmp/research3-runs/h001_postview_detector_v3b_owlvit_box_smoke
  log: logs/postview-evidence-v3b-owlvit-box-smoke-20260513-202047.log
  rows: 2
  detector_box_rows: 2
  rows_with_detector_box_rate: 0.50
  rows_with_candidate_association_rate: 0.00

query_template "a photo of a {query}", box_threshold 0.01, point_field position:
  output: /tmp/research3-runs/h001_postview_detector_v3b_owlvit_box_template_smoke
  log: logs/postview-evidence-v3b-owlvit-box-template-smoke-20260513-202415.log
  rows: 2
  detector_box_rows: 89
  rows_with_detector_box_rate: 1.00
  rows_with_candidate_association_rate: 0.50
  associated_candidate_heading_count: 6

query_template "a photo of a {query}", box_threshold 0.01, point_field visit_position:
  output: /tmp/research3-runs/h001_postview_detector_v3b_owlvit_box_template_visit_smoke
  log: logs/postview-evidence-v3b-owlvit-box-template-visit-smoke-20260513-202558.log
  rows: 2
  detector_box_rows: 89
  rows_with_detector_box_rate: 1.00
  rows_with_candidate_association_rate: 0.00
```

The detector rows include `uses_gt_for_action: false`. Candidate association is based on projected non-GT semantic candidates, box containment, and depth agreement.

#### 에이전트 추론

`OWL-ViT` is usable as an offline Docker detector dependency, but the box-only association gate is not stable enough for full calibration. The query template improves box recall, while `visit_position` worsens association because fewer candidate points project visibly. The remaining failure is not just package availability; it is object evidence quality and candidate-to-box association reliability.

For top-tier paper direction, do not scale this v3b result directly into policy comparison. Treat it as evidence that a stronger object-level scorer should use detector boxes plus segmentation or mask consistency before policy-scale evaluation.

#### 사용자 판단 필요

The recommended next setup decision is whether to proceed to `v3c_groundingdino_sam2` in the separate `openvocab-perception` image path. This will require additional package and checkpoint setup. The Habitat runtime image should remain unchanged.

### V3C GroundingDINO + SAM2 Setup Job

#### 사실

After the `v3b_owlvit_box` association gate failed, the next setup decision is to proceed with a separate detector+mask environment.

Primary sources checked on 2026-05-13:

```text
Hugging Face Transformers GroundingDINO docs:
https://huggingface.co/docs/transformers/model_doc/grounding-dino

Meta SAM2 official repository:
https://github.com/facebookresearch/sam2

SAM2.1 Hiera-Tiny Hugging Face page:
https://huggingface.co/facebook/sam2.1-hiera-tiny
```

Setup artifacts:

```text
date_launched: 2026-05-13
tmux_session: h001-openvocab-v3c-setup
dockerfile: runtime/Dockerfile.openvocab-perception-v3c
job_script: runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
GroundingDINO model: IDEA-Research/grounding-dino-tiny
GroundingDINO local dir: /tmp/research3-models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny
SAM2 checkpoint: /tmp/research3-models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
output_root: /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup
status_file: /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup/job_status.json
log: logs/openvocab-perception-v3c-groundingdino-sam2-20260513-204258.log
status_at_launch_check: running
stage_at_launch_check: build_image
```

The setup job records the exact command, output paths, expected model files, and offline load verification. Long-running Docker build and checkpoint downloads run in tmux and should not block other research tasks.

Progress check:

```bash
cat /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup/job_status.json
tmux list-sessions | rg 'h001-openvocab-v3c-setup'
tail -n 40 logs/openvocab-perception-v3c-groundingdino-sam2-20260513-204258.log
```

Expected completion verification:

```bash
sg docker -c "docker run --rm \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e HF_HOME=/models/.cache/huggingface \
  -v /tmp/research3-models:/models \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  python - <<'PY'
from pathlib import Path
from transformers import AutoProcessor, GroundingDinoForObjectDetection
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor

gdino_dir = Path('/models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny')
sam2_ckpt = Path('/models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt')
AutoProcessor.from_pretrained(str(gdino_dir), local_files_only=True)
GroundingDinoForObjectDetection.from_pretrained(str(gdino_dir), local_files_only=True)
SAM2ImagePredictor(build_sam2('configs/sam2.1/sam2.1_hiera_t.yaml', str(sam2_ckpt), device='cpu', mode='eval'))
print('v3c_offline_load_ok')
PY"
```

#### 에이전트 추론

`GroundingDINO + SAM2` is the right next diagnostic path because v3b showed that open-vocabulary boxes can be produced, but box-only evidence does not associate reliably with semantic map candidates. Masks should let the scorer use object-region depth, mask overlap, and candidate projection consistency instead of relying on loose box containment.

### V3C Setup Verification

#### 사실

The setup job completed and CPU-only offline load verification passed.

```text
date_checked: 2026-05-14
status_file: /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup/job_status.json
status: completed
stage: verified
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
GroundingDINO local dir: /tmp/research3-models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny
SAM2 checkpoint: /tmp/research3-models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
SAM2 checkpoint size: 156008466 bytes
CPU verification log: logs/openvocab-perception-v3c-groundingdino-sam2-cpu-verify-20260514-000244.log
cuda_available: false
```

Verified offline components:

```text
GroundingDinoProcessor
GroundingDinoForObjectDetection
SAM2ImagePredictor
```

#### 에이전트 추론

The next executable task can be a CPU-only `v3c_groundingdino_sam2` 2-row smoke. It should avoid GPU flags and use a tiny subset only; full calibration should wait until the detector+mask association gate passes.

### V3C Detector+Mask CPU Smoke

#### 사실

Implemented script:

```text
runtime/h001_runtime/detect_postview_groundingdino_sam2.py
schema_version: h001.postview_detector.v3c_groundingdino_sam2
```

The smoke was run without GPU flags and with `--device cpu`.

Initial all-heading CPU run was stopped because it was too slow for a no-GPU smoke. The script was revised to support `--max-headings-per-frame` and `--max-detector-boxes-per-heading`.

Lite top-1 result:

```text
output: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_cpu_smoke_lite
log: logs/postview-evidence-v3c-groundingdino-sam2-cpu-smoke-lite-20260514-001222.log
device: cpu
rows: 2
max_headings_per_frame: 2
max_detector_boxes_per_heading: 1
detector_box_rate: 1.00
sam2_mask_rate: 1.00
candidate_association_rate: 0.00
```

Top-3 result:

```text
output: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_cpu_smoke_top3
log: logs/postview-evidence-v3c-groundingdino-sam2-cpu-smoke-top3-20260514-001410.log
device: cpu
rows: 2
max_headings_per_frame: 2
max_detector_boxes_per_heading: 3
max_masks_per_heading: 3
query_template: a photo of a {query}.
detector_box_rows: 12
detector_mask_rows: 12
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 1.00
associated_candidate_heading_count: 4
projected_pixel_inside_mask_count: 8
uses_gt_for_action: false
```

#### 에이전트 추론

The detector+mask path is now feasible on a tiny CPU-only smoke. Top-1 boxes were too brittle, while top-3 detector boxes plus SAM2 masks recovered candidate association on both rows. This supports moving to a calibrated run contract, but the calibration should explicitly control compute budget and avoid full-heading CPU expansion unless a GPU run is approved later.

### Relation to LAMP and 3DSR

#### 사실

Papers checked on 2026-05-14:

```text
LAMP: Implicit Language Map for Robot Navigation
venue/status: IEEE Robotics and Automation Letters, 2025 / arXiv 2026
project: https://lab-of-ai-and-robotics.github.io/LAMP/
arXiv: https://arxiv.org/abs/2602.11862
DOI: https://doi.org/10.1109/LRA.2025.3619820

Memory-Efficient Voxelized Renderable Neural 3D Spatial Representation for Vision-Based Robotics
method shorthand: 3DSR
venue/status: IEEE Robotics and Automation Letters, 2026
DOI: https://doi.org/10.1109/LRA.2025.3632118
```

#### 논문 주장

`LAMP` claims that explicit grid or node language maps have a memory-resolution tradeoff, and proposes an implicit neural language field with sparse-graph coarse planning and gradient-based fine pose refinement. It also models embedding uncertainty using a von Mises-Fisher distribution and samples graph nodes using view coverage, uncertainty scores, and semantic sensitivity.

`3DSR` claims that voxelized 3D Gaussian splatting can reduce memory requirements for renderable visual spatial representations while preserving image reconstruction quality needed for robotics. It reports more than 90% of the best method's reconstruction quality while using 54.54% of its memory, plus localization and navigation applicability experiments.

#### 에이전트 추론

`LAMP` is directly connected to H001. It validates three ideas that are central to this research: language-map memory efficiency, semantic embedding uncertainty, and navigation decisions over a learned semantic field. The gap for H001 is that `LAMP` optimizes goal-reaching in an implicit language field, while H001 asks whether semantic uncertainty should actively trigger re-observation and improve wrong-goal visit / wasted path / SLAM-map consistency.

`3DSR` is indirectly but strategically connected. It is not primarily a semantic uncertainty paper, but it supports the Step 4-5 direction: a memory-efficient renderable spatial memory could provide re-rendered evidence for candidate verification, localization checks, and real-world deploy. For the current first probe, `3DSR` should be treated as a future representation backend candidate, not a baseline.

Practical connection to the current runtime:

```text
LAMP connection:
  compare against explicit VLMaps-style feature grid and implicit language map as future semantic memory backend
  borrow uncertainty modeling vocabulary for object/node semantic confidence
  possible baseline / related work for language-map navigation

3DSR connection:
  possible renderable memory backend for post-view evidence without re-running Habitat rendering
  possible Step 4-5 bridge from semantic memory to visual localization / map consistency
  possible real-world deploy representation if memory budget becomes a bottleneck
```

### V3C Calibration Run Contract

#### 사실

User approved GPU use on 2026-05-14. GPU availability check:

```text
host_gpu: NVIDIA GeForce RTX 5090
gpu_memory_total: 32607 MiB
docker_cuda_available: true
docker_device_count: 1
```

Implemented run script:

```text
runtime/jobs/postview_v3c_groundingdino_sam2_calib50.sh
syntax_check: passed with zsh -n
```

Planned 50-row calibration artifact contract:

```text
scope: 50 calibration rows from existing post-view frame artifact
input_frames: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
query_template: a photo of a {query}.
max_headings_per_frame: 2
max_detector_boxes_per_heading: 3
max_masks_per_heading: 3
candidate_point_field: position
box_threshold: 0.10
text_threshold: 0.10
output_root: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu
```

Updated output root after GPU approval:

```text
output_root: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu
status_file: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu/job_status.json
log: logs/postview-evidence-v3c-groundingdino-sam2-calib50-<timestamp>.log
```

Calibration artifact outputs:

```text
detector_boxes.jsonl
detector_masks.jsonl
detector_candidate_associations.jsonl
frame_summary.jsonl
summary.json
debug_images/
```

Minimum gate before policy comparison:

```text
rows == 50
uses_gt_for_action == false
rows_with_detector_box_rate >= 0.80
rows_with_sam2_mask_rate >= 0.80
rows_with_candidate_association_rate >= 0.60
projected_pixel_inside_mask_count > 0
wrong-goal rows with candidate association >= 0.50
runtime is acceptable as background GPU job
```

Prerequisite check on 2026-05-14:

```text
/tmp/research3-runs: empty
/tmp/research3-data: missing
/tmp/research3-models: empty
v3c calib50 launch status: blocked
missing prerequisites:
  HM3D data mount /tmp/research3-data
  v3c model checkpoints under /tmp/research3-models/openvocab/
  candidate artifact /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
  post-view frames /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl
```

The launch command after prerequisites are restored:

```bash
tmux new-session -d -s h001-v3c-calib50-gpu \
  "cd /home/yoohyun/research3 && DEVICE=cuda hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/postview_v3c_groundingdino_sam2_calib50.sh"
```

### V3C Calibration Result

#### 사실

```text
date_checked: 2026-05-15
job_status: failed at verification gate
log: logs/postview-evidence-v3c-groundingdino-sam2-calib50-20260514-223034.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_groundingdino_sam2_calib50_gpu
rows: 50
uses_gt_for_action: false
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.30
rows_with_candidate_association: 15 / 50
wrong_goal_rows_with_candidate_association: 7 / 26
associated_candidate_heading_count: 25
projected_pixel_inside_mask_count: 71
detector_box_rows: 297
detector_mask_rows: 297
```

Query-level association:

```text
bed: 8 / 10 rows
chair: 0 / 8 rows
plant: 0 / 10 rows
sofa: 4 / 10 rows
toilet: 2 / 6 rows
tv_monitor: 1 / 6 rows
```

Projection and association diagnostics:

```text
projection_status_counts: behind_camera 145, out_of_fov 108, visible 91
visible_candidates: 91
projected_pixel_inside_box: 89
projected_pixel_inside_mask: 71
associated_to_candidate: 25
visible_depth_check: depth_mismatch 70, consistent 21
```

Detector phrase diagnostics:

```text
top_label_text: "a photo" 222 / 297 boxes
object_label_rows:
  bed 10 / 10
  chair 6 / 8
  plant 10 / 10
  sofa 8 / 10
  toilet 6 / 6
  tv_monitor 2 / 6
```

#### 에이전트 추론

`GroundingDINO + SAM2` produces boxes and masks reliably on all 50 rows, so the failure is not detector/mask availability. The failed gate is candidate association. The main bottlenecks are candidate projection coverage and depth consistency, with prompt phrase noise also visible because many boxes are labeled `"a photo"` instead of the object phrase.

This should not proceed to policy-scale comparison. The next useful revision is an association diagnostic, not a policy run:

```text
1. filter or re-rank detector boxes by object phrase rather than accepting generic "a photo" boxes;
2. compare query-only prompt against "a photo of a {query}.";
3. test more candidate-directed headings before increasing policy scale;
4. separate visible-but-depth-mismatched candidates from behind-camera / out-of-FOV candidates;
5. evaluate whether candidate `position` is the wrong association point for chair/plant.
```

### V3C Association Ablation Smoke Contract

#### 에이전트 추론

The next run should be a small ablation, not another full calibration artifact. It should isolate association mechanics before spending another 50-row GPU pass.

Use the same restored artifact inputs and keep `uses_gt_for_action == false`.

```text
input_frames: /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl
candidate_artifact: /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
base_image: research3/openvocab-perception:20260513-v3c-gdino-sam2
device: cuda
scope: small diagnostic only
rows: 12 or fewer, balanced across failed queries if possible
primary failed queries: chair, plant, tv_monitor
secondary queries: sofa, toilet, bed
```

Recommended ablation order:

```text
A1_query_only_prompt:
  query_template: "{query}"
  max_headings_per_frame: 2
  candidate_point_field: position
  purpose: test whether "a photo" phrase boxes caused prompt noise

A2_more_headings:
  query_template: "{query}"
  max_headings_per_frame: 6
  candidate_point_field: position
  purpose: test whether projection coverage is the main bottleneck

A3_visit_position:
  query_template: "{query}"
  max_headings_per_frame: 6
  candidate_point_field: visit_position
  purpose: test whether candidate `position` is the wrong association point
```

Promotion rule for another 50-row v3c run:

```text
rows_with_candidate_association_rate >= 0.50 on the small smoke
chair_or_plant_has_nonzero_association == true
generic "a photo" boxes are reduced or ignored
uses_gt_for_action == false
```

### V3C Association Ablation Smoke Progress

#### 사실

`A1_query_only_prompt` completed on 2026-05-15:

```text
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a1_query_only_smoke
log: logs/postview-evidence-v3c-a1-query-only-smoke-20260515-000920.log
rows: 12
query_template: "{query}"
max_headings_per_frame: 2
candidate_point_field: position
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.50
rows_with_candidate_association: 6 / 12
associated_candidate_heading_count: 6
uses_gt_for_action: false
```

Query-level association:

```text
bed: 3 / 3
chair: 0 / 3
plant: 0 / 2
sofa: 2 / 2
toilet: 0 / 1
tv_monitor: 1 / 1
```

Detector label text became object-specific under the query-only prompt:

```text
chair 18, bed 10, sofa 10, plant 6, toilet 6, tv monitor 6
```

`A2_more_headings` launched on 2026-05-15:

```text
session: h001-v3c-a2-more-headings-smoke-20260515-001233
log: logs/postview-evidence-v3c-a2-more-headings-smoke-20260515-001233.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a2_more_headings_smoke
query_template: "{query}"
max_headings_per_frame: 6
candidate_point_field: position
verification: /tmp/research3-runs/h001_postview_detector_v3c_a2_more_headings_smoke/job_status.json
diagnostic: /tmp/research3-runs/h001_postview_detector_v3c_a2_more_headings_smoke/ablation_diagnostic.json
```

`A2_more_headings` completed on 2026-05-15:

```text
rows: 12
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.667
rows_with_candidate_association: 8 / 12
associated_candidate_heading_count: 25
promotion_pass: true
uses_gt_for_action: false
query-level association:
  bed: 3 / 3
  chair: 1 / 3
  plant: 0 / 2
  sofa: 2 / 2
  toilet: 1 / 1
  tv_monitor: 1 / 1
```

`A3_visit_position` launched on 2026-05-15:

```text
session: h001-v3c-a3-visit-position-smoke-20260515-001400
log: logs/postview-evidence-v3c-a3-visit-position-smoke-20260515-001400.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a3_visit_position_smoke
query_template: "{query}"
max_headings_per_frame: 6
candidate_point_field: visit_position
verification: /tmp/research3-runs/h001_postview_detector_v3c_a3_visit_position_smoke/job_status.json
diagnostic: /tmp/research3-runs/h001_postview_detector_v3c_a3_visit_position_smoke/ablation_diagnostic.json
```

`A3_visit_position` completed on 2026-05-15:

```text
rows: 12
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.00
rows_with_candidate_association: 0 / 12
promotion_pass: false
uses_gt_for_action: false
```

Selected next 50-row calibration setting:

```text
ablation: A2_query_heading6_calib50
session: h001-v3c-a2-calib50-20260515-001528
log: logs/postview-evidence-v3c-a2-calib50-20260515-001528.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a2_query_heading6_calib50
query_template: "{query}"
max_headings_per_frame: 6
candidate_point_field: position
promotion_association_rate: 0.60
verification: /tmp/research3-runs/h001_postview_detector_v3c_a2_query_heading6_calib50/job_status.json
diagnostic: /tmp/research3-runs/h001_postview_detector_v3c_a2_query_heading6_calib50/ablation_diagnostic.json
```

`A2_query_heading6_calib50` completed on 2026-05-15:

```text
rows: 50
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.48
rows_with_candidate_association: 24 / 50
associated_candidate_heading_count: 90
promotion_pass: false
uses_gt_for_action: false
query-level association:
  bed: 8 / 10
  chair: 2 / 8
  plant: 2 / 10
  sofa: 4 / 10
  toilet: 4 / 6
  tv_monitor: 4 / 6
```

Detector calibration analyzer result:

```text
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a2_query_heading6_calibration_analysis
candidate_rows: 500
rows_with_any_association_rate: 0.48
wrong_goal_rows_with_any_association_rate: 0.462
baseline_correct_rows_with_any_association_rate: 0.364
best_candidate_auc: 0.628
best_candidate_auc_field: best_box_score_max
best_selected_correct_delta_on_all_rows: +0.08
association_count_auc: 0.502
inside_mask_count_auc: 0.511
passes_detector_calibration_gate: false
```

Next detector diagnostic:

```text
ablation: A4_all_headings_calib50
session: h001-v3c-a4-all-headings-calib50-20260515-003255
log: logs/postview-evidence-v3c-a4-all-headings-calib50-20260515-003255.log
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_calib50
query_template: "{query}"
max_headings_per_frame: 0
candidate_point_field: position
promotion_association_rate: 0.60
```

#### 에이전트 추론

`A1_query_only_prompt` reduced prompt phrase noise but did not recover `chair` or `plant` association. This means the next bottleneck is more likely candidate visibility / projection coverage or candidate point placement than text prompt phrasing alone.

`A2_more_headings` shows that heading coverage is a real bottleneck and is sufficient to recover nonzero `chair` association. `A3_visit_position` collapsed to zero association, so the current candidate artifact's `visit_position` should not be used as the detector-mask association point.

At 50-row scale, `A2_query_heading6_calib50` improves over the original `v3c` run but still fails the detector/mask association gate. The detector output contains a weak candidate-correctness signal in `best_box_score_max`, but mask/association count is nearly random with respect to candidate correctness. This is not policy-ready evidence yet. `A4_all_headings_calib50` is the next low-confound diagnostic because it uses already exported headings and tests whether the remaining failure is simply view coverage.

`A4_all_headings_calib50` completed on 2026-05-15:

```text
rows: 50
rows_with_detector_box_rate: 1.00
rows_with_sam2_mask_rate: 1.00
rows_with_candidate_association_rate: 0.52
rows_with_candidate_association: 26 / 50
associated_candidate_heading_count: 121
promotion_pass: false
uses_gt_for_action: false
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

### Detector Evidence Objective Revision Contract

#### 사실

`GroundingDINO + SAM2` box and mask generation is not the bottleneck:

```text
A2_query_heading6_calib50: detector box rate 1.00, SAM2 mask rate 1.00, association rate 0.48
A4_all_headings_calib50: detector box rate 1.00, SAM2 mask rate 1.00, association rate 0.52
```

The remaining bottleneck is the policy-facing evidence objective:

```text
associated_count_auc: 0.502-0.506
inside_mask_count_auc: 0.506-0.511
visible_count_auc: about 0.503
best_box_score_max_auc: 0.607-0.628
```

#### 에이전트 추론

Do not run a policy-scale comparison from A2 or A4. A detector/mask evidence source that detects objects in every frame but cannot reliably separate correct candidates from wrong candidates will produce a weak or misleading policy result.

The next scorer should be an offline `v3d_detector_objective` calibration, not another GPU detector pass. It should reuse existing A2/A4 detector artifacts and compare objective variants:

```text
O1_detector_max:
  score: per-candidate max detector score
  purpose: confirm the only positive A2/A4 signal

O2_detector_prior:
  score: semantic prior + calibrated detector max score
  purpose: avoid switching to detector false positives

O3_detector_geometry:
  score: semantic prior + calibrated detector max score + visible/inside-mask support - depth inconsistency penalty
  purpose: test whether geometry improves over detector confidence alone

O4_conservative_switch:
  score: O2 or O3 with switch margin and path-cost guard
  purpose: reduce wrong-goal fixes without creating new wrong-goal visits
```

Promotion gate before policy-scale run:

```text
uses_gt_for_action == false
candidate_correctness_AUC >= 0.65 on calibration
selected_correct_delta_on_all_rows > 0
wrong_goal_fixes > new_wrong_goals
rows_with_actionable_detector_evidence_rate >= 0.50
```

`v3d_detector_objective` strict offline calibration result:

```text
date_checked: 2026-05-15
analysis_script: runtime/h001_runtime/analyze_postview_detector_v3c.py
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_objective_analysis_strict
detector_root: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_calib50
min_association_rate: 0.50
min_candidate_auc: 0.65
rows_with_any_association_rate: 0.52
best_candidate_auc: 0.607
passes_detector_calibration_gate: false
```

Objective variants:

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

The current detector objective revision does not pass the stricter paper-facing gate. The only useful signal is detector confidence, while the current semantic prior and geometry terms degrade candidate-level AUC. This suggests the current spatial association features are too noisy to serve as positive evidence. Before another policy run, inspect query/category-specific failure modes and revise the object-node evidence representation rather than adding more headings or running another detector pass.

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

The next revision should focus on object-node evidence for repeated/cluttered categories, not on global detector recall. `chair` and `sofa` are the key failure categories; `bed` and `tv_monitor` already show usable detector-confidence signal; `plant` is under-supported by correct candidate rows. A plausible next implementation is a category-aware object-node support diagnostic:

```text
N1_extent_support:
  aggregate detections by candidate over nearby headings and use box/mask extent consistency, not only point-in-mask hits

N2_instance_separation:
  penalize candidates whose support overlaps multiple repeated instances or large room-level boxes

N3_category_gate:
  use detector confidence only for categories whose calibration AUC is above threshold; keep semantic prior for failed categories
```

Do not enter policy-scale comparison until this node-level diagnostic passes a stricter calibration gate.

Object-node evidence revision result:

```text
date_checked: 2026-05-15
analysis_script: runtime/h001_runtime/analyze_postview_detector_v3c.py
analysis_output: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_gate_analysis_strict
source_detector_root: /tmp/research3-runs/h001_postview_detector_v3c_a4_all_headings_calib50

new node features:
  node_box_proximity
  node_extent_score
  compact_node_extent_score
  O5_node_extent
  O6_compact_extent
  O7_extent_prior
  O8_category_gate
  O9_category_best_gate
  O10_category_best_switch
```

Category-best mode selection:

```text
bed: O1_detector_max
chair: semantic_prior
plant: semantic_prior
sofa: semantic_prior
toilet: O6_compact_extent
tv_monitor: O6_compact_extent
```

Episode-level results:

```text
baseline selected_correct: 11 / 50

O1_detector_max:
  selected_correct: 15 / 50
  selected_correct_delta: +0.08
  wrong_goal_fixes: 4
  new_wrong_goals: 0

O6_compact_extent:
  selected_correct: 15 / 50
  selected_correct_delta: +0.08
  wrong_goal_fixes: 5
  new_wrong_goals: 1

O9_category_best_gate:
  selected_correct: 17 / 50
  selected_correct_delta: +0.12
  wrong_goal_fixes: 7
  new_wrong_goals: 1

O10_category_best_switch, switch_margin 0.10:
  selected_correct: 14 / 50
  selected_correct_delta: +0.06
  wrong_goal_fixes: 3
  new_wrong_goals: 0
```

Switch margin sweep:

```text
output: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_switch_sweep/switch_margin_sweep.json
margin 0.00: switches 14, selected_correct_delta +5, fixes 5, new_wrong_goals 0
margin 0.02: switches 6, selected_correct_delta +3, fixes 3, new_wrong_goals 0
margin 0.05-0.15: switches 4, selected_correct_delta +3, fixes 3, new_wrong_goals 0
margin 0.20+: no switches
```

#### 에이전트 추론

This is the first detector-objective result that has a plausible policy-facing shape: it improves selected correctness, fixes more wrong-goal cases than it creates, and can be made conservative with a margin. It is not enough for a paper claim because category-best selection was derived on the same calibration split. The next step is cross-validated or held-out validation of the category-best switch rule before any policy-scale run.

### Category-Best Detector Objective Cross-Validation

#### 사실

Scene-wise cross-validation artifact:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/cross_validate_postview_detector_v3c.py
input: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_gate_analysis_strict/detector_candidate_calibration.jsonl
output_root: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_loso_cv
summary: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_loso_cv/summary.json
folds: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_loso_cv/folds.jsonl
decisions: /tmp/research3-runs/h001_postview_detector_v3c_a4_category_best_loso_cv/decisions.jsonl
fold_strategy: leave_one_scene_out
fold_count: 5
feature_fields: O1_detector_max, O5_node_extent, O6_compact_extent
min_train_auc: 0.65
min_positive: 3
min_negative: 3
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Best cross-validation setting:

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

Margin sensitivity:

```text
margin 0.00: selected_correct_delta +3, fixes 3, new_wrong_goals 0
margin 0.02: selected_correct_delta +1, fixes 1, new_wrong_goals 0
margin 0.05-0.15: selected_correct_delta 0
margin 0.20: no switches
```

Held-out scene deltas at margin `0.00`:

```text
00009-vLpv2VX547B: +1
00017-oEPjPNSPmzL: +2
00020-XYyR54sxe6b: 0
00057-1UnKg1rAb8A: 0
00744-1S7LAXRdDqK: 0
```

#### 에이전트 추론

This result passes a minimal safety gate but fails a robust policy-promotion gate. The useful signal is not an artifact of exact same-split category selection, but it is still too scene-sparse to justify a policy-scale claim.

Current promotion decision:

```text
policy_scale_run: blocked
reason: cross-validation improvement appears in only 2 / 5 held-out scenes
next_required_gate: larger independent held-out detector-objective validation or regenerated validation scenes
```

The integration contract can be drafted later, but the actual policy comparison should not run until the category-best rule shows robust held-out improvement.

### Independent Held-Out Detector Objective Validation Contract

#### 사실

Held-out validation target:

```text
date_prepared: 2026-05-15
split: first_eval
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_sr1.json
scene_specs: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/first_eval_scenes.txt
source: HM3D ObjectNav v2 val
scenes: 10
episodes: 100
queries: bed, chair, plant, sofa, toilet, tv_monitor
```

Prepared runtime changes:

```text
runtime/calibration_artifact_job.sh:
  supports EXPECTED_SCENE_COUNT and EXPECTED_QUERY_ROWS
  can generate a 10-scene / 60-query-row first_eval candidate artifact

runtime/jobs/postview_v3c_groundingdino_sam2_calib50.sh:
  FRAMES, CANDIDATE_ARTIFACT, and OUT are now honored in the Docker command
  the script can be reused for first_eval detector artifact generation
```

Expected artifact roots:

```text
candidate_artifact_root: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1
candidate_artifact: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
policy_root: /tmp/research3-runs/h001_first_eval_policy_random256_k10_v1
postview_root: /tmp/research3-runs/h001_first_eval_postview_scores_v2_1_relaxed_position_random256_k10_v1
detector_root: /tmp/research3-runs/h001_first_eval_postview_detector_v3c_a4_all_headings
objective_root: /tmp/research3-runs/h001_first_eval_postview_detector_v3c_a4_category_best_validation
```

Candidate artifact launch shape:

```bash
cd /home/yoohyun/research3
TS=$(date +%Y%m%d-%H%M%S)
SESSION="h001-first-eval-artifacts-random256-k10-${TS}"
LOG="logs/first-eval-artifacts-random256-k10-${TS}.log"
OUT="/tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1"
SCENES="/home/yoohyun/research3/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/first_eval_scenes.txt"
mkdir -p logs "$OUT"
tmux new-session -d -s "$SESSION" \
  "bash -lc 'set -o pipefail; cd /home/yoohyun/research3 && SCENE_SPECS_FILE=\"$SCENES\" ARTIFACT_ID=first_eval_random256_k10_v1 TRAJECTORY_SUFFIX=first_eval_random256_k10_v1 FRAMES=256 MAX_CANDIDATES=10 TOP_PERCENTILE=98.0 EXPECTED_SCENE_COUNT=10 EXPECTED_QUERY_ROWS=60 OUT_ROOT=\"$OUT\" ./hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/calibration_artifact_job.sh 2>&1 | tee -a \"$LOG\"; rc=\$?; echo \"[\$(date -Is)] job exit status: \$rc\" | tee -a \"$LOG\"; exit \$rc'"
```

Detector validation gate:

```text
train_rule_source: calibration split only
heldout_rule_change: disallowed
uses_gt_for_action: false
uses_gt_for_analysis: true

candidate_substrate_gate:
  GTTargetOracle success_rate == 1.0
  candidate_label_coverage >= 0.70
  episodes_with_reachable_correct_and_wrong_rate >= 0.50
  NoReobserve wrong_goal_visit_rate >= 0.10

detector_artifact_gate:
  rows >= 100
  rows_with_detector_box_rate >= 0.80
  rows_with_sam2_mask_rate >= 0.80
  rows_with_candidate_association_rate >= 0.60

objective_gate:
  selected_correct_delta > 0
  new_wrong_goals == 0
  scenes_with_positive_delta >= 5 / 10
  candidate_auc >= 0.65 when candidate labels are balanced enough
```

#### 에이전트 추론

This validation should be treated as an independent detector-objective gate, not as a policy result. It asks whether the fixed category-best rule learned from calibration reduces wrong-goal candidate selection on unseen `first_eval` scenes. If this gate fails, the next research move should be object-node semantic memory revision, not margin tuning on `first_eval`.

Launch status:

```text
date_launched: 2026-05-15
status: completed
session: h001-first-eval-artifacts-random256-k10-20260515-014112
working_directory: /home/yoohyun/research3
log: logs/first-eval-artifacts-random256-k10-20260515-014112.log
output_root: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1
command_record: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/launch_command.txt
expected_status: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/job_status.json
expected_artifact: /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
rows: 60
candidate_count: 600
finite_position_candidates: 579
scenes: 10
queries: 6
```

Completion verification:

```bash
cat /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/job_status.json
cat /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/coverage_check.json
wc -l /tmp/research3-runs/h001_first_eval_artifacts_random256_k10_v1/all_scenes_aligned.jsonl
```

Candidate substrate coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_random256_k10_v1/coverage_sanity
log: logs/first-eval-coverage-sanity-20260515-080212.log
artifact_coverage: /tmp/research3-runs/h001_first_eval_policy_random256_k10_v1/coverage_sanity/artifact_coverage.json
episodes: 100
candidate_backend_uses_gt_for_action: false
GTTargetOracle_success_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 0.49
NoReobserve_success_rate: 0.18
NoReobserve_SPL: 0.0979
candidate_label_coverage: 1.0
episodes_with_reachable_correct_and_wrong_rate: 0.40
gate: failed
failed_check: reachable_correct_and_wrong_pass
```

Recovery job:

```text
artifact_id: first_eval_random256_k20_v1
change: MAX_CANDIDATES 10 -> 20
session: h001-first-eval-artifacts-random256-k20-20260515-080343
log: logs/first-eval-artifacts-random256-k20-20260515-080343.log
output_root: /tmp/research3-runs/h001_first_eval_artifacts_random256_k20_v1
command_record: /tmp/research3-runs/h001_first_eval_artifacts_random256_k20_v1/launch_command.txt
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
artifact_coverage: /tmp/research3-runs/h001_first_eval_policy_random256_k20_v1/coverage_sanity/artifact_coverage.json
episodes: 100
candidate_backend_uses_gt_for_action: false
GTTargetOracle_success_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 0.49
NoReobserve_success_rate: 0.14
NoReobserve_SPL: 0.0800
candidate_label_coverage: 1.0
episodes_with_reachable_correct_and_wrong_rate: 0.46
gate: failed
failed_check: reachable_correct_and_wrong_pass
```

Reachability-diverse candidate revision:

```text
runtime_file: runtime/h001_runtime/export_vlmaps_artifact.py
job_file: runtime/calibration_artifact_job.sh
new_export_mode: --selection-mode spatial_nms
new_job_env:
  CANDIDATE_SELECTION_MODE=spatial_nms
  SPATIAL_NMS_MIN_DISTANCE_CELLS=20.0
uses_gt_for_action: false
smoke_output: /tmp/research3-runs/h001_spatial_nms_export_smoke/chair.jsonl
smoke_result: 20 candidates, metadata selection_mode spatial_nms
```

Spatial-NMS recovery launch:

```text
artifact_id: first_eval_spatial_nms_k20_v1
change: component extraction -> spatial NMS high-score cell extraction
session: h001-first-eval-spatial-nms-k20-20260515-085336
log: logs/first-eval-spatial-nms-k20-20260515-085336.log
output_root: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1
command_record: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1/launch_command.txt
status: failed
failure_reason: Docker image contained stale `export_vlmaps_artifact.py` without `--selection-mode`
fix: `calibration_artifact_job.sh` now mounts `/home/yoohyun/research3` and sets `PYTHONPATH` for candidate export
retry_session: h001-first-eval-spatial-nms-k20-retry-20260515-095921
retry_log: logs/first-eval-spatial-nms-k20-retry-20260515-095921.log
retry_status: interrupted after 7 / 10 scenes, job_status.json was empty
status_write_fix: `calibration_artifact_job.sh` now writes `job_status.json` through a temporary file and atomic replace
resume2_session: h001-first-eval-spatial-nms-k20-resume2-20260515-105554
resume2_log: logs/first-eval-spatial-nms-k20-resume2-20260515-105554.log
resume2_status: completed
rows: 60
candidate_count: 1200
finite_position_candidates: 1004
```

Completion check:

```bash
cat /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1/job_status.json
cat /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1/coverage_check.json
```

`spatial_nms_k20` coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_spatial_nms_k20_v1/coverage_sanity
log: logs/first-eval-spatial-nms-k20-coverage-sanity-20260515-110249.log
artifact_coverage: /tmp/research3-runs/h001_first_eval_policy_spatial_nms_k20_v1/coverage_sanity/artifact_coverage.json
episodes: 100
candidate_backend_uses_gt_for_action: false
GTTargetOracle_success_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 0.47
NoReobserve_success_rate: 0.20
NoReobserve_SPL: 0.1036
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.5215
episodes_with_reachable_correct_and_wrong_rate: 0.49
gate: failed
failed_check: reachable_correct_and_wrong_pass
```

Decision:

```text
detector_validation: blocked
reason: candidate substrate still misses hard ambiguity gate by 1 / 100 episodes
next_recovery: lower-percentile spatial NMS, e.g. TOP_PERCENTILE=97.0
why_not_scene_replacement_yet: lower-percentile spatial NMS changes only candidate extraction from the same maps/scenes, so it is lower confound
```

Lower-percentile Spatial-NMS recovery job:

```text
date_launched: 2026-05-15
artifact_id: first_eval_spatial_nms_p97_k20_v1
script: runtime/jobs/first_eval_spatial_nms_reexport.sh
coverage_script: runtime/jobs/first_eval_coverage_sanity.sh
session: h001-first-eval-spatial-nms-p97-k20-20260515-113345
log: logs/first-eval-spatial-nms-p97-k20-20260515-113345.log
source_root: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1
output_root: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_p97_k20_v1
command_record: /tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_p97_k20_v1/launch_command.txt
selection_mode: spatial_nms
top_percentile: 97.0
max_candidates: 20
spatial_nms_min_distance_cells: 20.0
status: running
```

Lower-percentile Spatial-NMS coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_policy_spatial_nms_p97_k20_v1/coverage_sanity
artifact_coverage: /tmp/research3-runs/h001_first_eval_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
GTTargetOracle_success_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 0.47
NoReobserve_success_rate: 0.20
NoReobserve_SPL: 0.1036
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.59
episodes_with_reachable_correct_and_wrong_rate: 0.49
gate: failed
failed_check: reachable_correct_and_wrong_pass
```

Replacement-probe substrate construction:

```text
reason: p97 improved candidate reachability but not correct-and-wrong ambiguity
selection_rule: choose from HM3D ObjectNav val scenes not already in first_eval, with available scene assets and all six ObjectNav categories where possible
scene_specs: manifests/replacement_probe_scenes.txt
probe_scenes: 5cdEh9F2hJL, 6s7QHgap2fW, GLAQ4DNUx5U
detector_validation: still blocked
```

Replacement-probe artifact launch:

```text
date_launched: 2026-05-15
session: h001-replacement-probe-p97-k20-20260515-113921
log: logs/replacement-probe-spatial-nms-p97-k20-20260515-113921.log
output_root: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1
command_record: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1/launch_command.txt
expected_status: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1/job_status.json
expected_artifact: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
status: running
```

Replacement-probe coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_replacement_probe_policy_spatial_nms_p97_k20_v1/coverage_sanity
artifact_coverage: /tmp/research3-runs/h001_replacement_probe_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
GTTargetOracle_success_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 0.6333
candidate_reachable_rate: 0.8783
episodes_with_reachable_correct_and_wrong_rate: 0.6667
gate: passed
scene_rates: 5cdEh9F2hJL 1.0, 6s7QHgap2fW 0.6, GLAQ4DNUx5U 0.4
```

First_eval replacement v1:

```text
replacement_policy: minimal scene replacement
replaced_scene: k1cupFYWXJ6
replacement_scene: 5cdEh9F2hJL
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_first_eval_replacement_v1.json
scene_specs: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/first_eval_replacement_v1_scenes.txt
combined_artifact: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
composition: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/composition.json
rows: 60
candidates: 1200
finite_position_candidates: 1118
```

First_eval replacement v1 coverage result:

```text
date_checked: 2026-05-15
output_root: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/coverage_sanity
artifact_coverage: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
GTTargetOracle_success_rate: 1.0
NoReobserve_wrong_goal_visit_rate: 0.51
NoReobserve_success_rate: 0.26
NoReobserve_SPL: 0.1290
candidate_label_coverage: 1.0
candidate_reachable_rate: 0.688
episodes_with_reachable_correct_and_wrong_rate: 0.59
gate: passed
```

First_eval replacement v1 detector artifact launch:

```text
script: runtime/jobs/first_eval_replacement_v3c_detector_artifact.sh
session: h001-first-eval-repl-v3c-detector-20260515-115938
log: logs/first-eval-replacement-v3c-detector-artifact-20260515-115938.log
policy_out: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision
frames_out: /tmp/research3-runs/h001_first_eval_replacement_postview_frames_v2_spatial_nms_p97_k20_v1
detector_out: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
status: completed with verification failure
```

Detector artifact retry:

```text
first_launch_status: failed at frame_export verification
reason: `export_postview_frames_v2` filtered out 2 non-finite viewpoint rows and exported 98 renderable rows
invalid_rows: p53SfW6mjZe/sofa, viewpoint_position NaN, observation_success false
script_fix: use `MIN_FRAME_ROWS=95` and pass actual `FRAME_ROWS` to detector `--max-frames`
retry_session: h001-first-eval-repl-v3c-detector-retry-20260515-120319
retry_log: logs/first-eval-replacement-v3c-detector-artifact-retry-20260515-120319.log
retry_status: failed at verification
```

Detector artifact verification:

```text
date_checked: 2026-05-15
job_status_file: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1/job_status.json
summary: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1/summary.json
diagnostic: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1/heldout_detector_diagnostic.json
rows: 98
rows_with_detector_box_rate: 0.9388
rows_with_sam2_mask_rate: 0.9388
rows_with_candidate_association_rate: 0.4082
required_candidate_association_rate: 0.60
promotion_pass: false
```

Weak association categories:

```text
bed: 14 / 20
chair: 12 / 20
plant: 2 / 18
sofa: 4 / 18
toilet: 8 / 13
tv_monitor: 0 / 9
```

Held-out objective diagnostic on failed detector artifact:

```text
analysis_output: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_category_best_objective_diagnostic
rows_with_any_association_rate: 0.40
best_candidate_auc: 0.6916
best_selected_correct_delta_on_all_rows: +0.02
passes_detector_calibration_gate: false
status: diagnostic_only_not_promotion
```

Association tolerance probe on existing rows:

```text
mask + depth_tolerance_1m: association 0.408
mask + depth_tolerance_3m: association 0.571
mask + depth_tolerance_5m: association 0.663
mask + no_depth_gate: association 0.724
box_or_mask + depth_tolerance_3m: association 0.663
box_or_mask + no_depth_gate: association 0.776
```

Association variant diagnostic:

```text
script: runtime/h001_runtime/analyze_detector_association_variants.py
docker_image: research3/habitat-h001:20260508-calib-artifacts
output_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_association_variants_v1
summary: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_association_variants_v1/summary.json
variant_summaries: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_association_variants_v1/variant_summaries.jsonl
```

Result:

```text
all_variants_passed_gate: false
best_coverage_variant: box_or_mask_depth_none
best_coverage_variant_association_rate: 0.76
best_coverage_variant_associated_count_auc: 0.586
best_coverage_variant_selected_delta: -0.11
best_coverage_variant_wrong_goal_fixes: 5
best_coverage_variant_new_wrong_goals: 10
box_or_mask_depth_3p0_association_rate: 0.65
box_or_mask_depth_3p0_associated_count_auc: 0.566
box_or_mask_depth_3p0_selected_delta: -0.10
box_or_mask_depth_3p0_wrong_goal_fixes: 5
box_or_mask_depth_3p0_new_wrong_goals: 7
```

#### 에이전트 추론

The first_eval replacement substrate is valid, but the detector artifact is not valid for objective validation because the candidate association gate failed. The bottleneck is detector-object association rather than detector/mask generation.

The association variant diagnostic rules out a simple threshold-only fix: relaxed depth / box containment can recover association coverage, but `associated_count` remains a weak correctness signal and creates too many new wrong-goals. The next implementation should revise object evidence representation rather than rerun the same detector validation.

### Weak-Category Evidence Revision V1

#### 사실

```text
script: runtime/h001_runtime/analyze_detector_evidence_revision.py
docker_image: research3/habitat-h001:20260508-calib-artifacts
input_detector_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
input_candidate_decisions: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision/candidate_decisions.jsonl
output_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1
summary: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1/summary.json
candidate_features: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1/candidate_features.jsonl
decisions: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1/weak_category_decisions.jsonl
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
  action: keep semantic prior
```

Result:

```text
baseline_selected_correct: 33 / 100
selected_correct: 36 / 100
selected_correct_delta_on_all_rows: +0.03
wrong_goal_fixes: 3
new_wrong_goals: 0
switches: 3
passes_evidence_revision_gate: true
```

#### 에이전트 추론

This revision is better than association-count tolerance because it improves selected-candidate correctness while preserving a zero-new-wrong-goal gate on the same artifact. It also gives category-specific behavior:

- `plant`: use support count without strict depth agreement.
- `tv_monitor`: use detector-score-weighted box/mask support without strict depth agreement.
- `sofa`: do not switch until evidence improves.

This remains a candidate rule, not a paper-facing result, because the rule was selected after inspecting the same first_eval replacement artifact. The next runtime task should be a scene-wise or independent-split robustness check before freezing the rule.

### Weak-Category Evidence Robustness V1

#### 사실

```text
script: runtime/h001_runtime/validate_detector_evidence_robustness.py
docker_image: research3/habitat-h001:20260508-calib-artifacts
input_decisions: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_revision_v1/weak_category_decisions.jsonl
output_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_robustness_v1
summary: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_robustness_v1/summary.json
scene_summary: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_robustness_v1/scene_summary.jsonl
query_scene_summary: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_evidence_robustness_v1/query_scene_summary.jsonl
```

Result:

```text
overall_selected_delta: +3 / 100
wrong_goal_fixes: 3
new_wrong_goals: 0
positive_scene_count: 2
negative_scene_count: 0
switch_scene_count: 2
positive_scenes: TEEsavR23oF +2, y9hTuugGdiq +1
plant_positive_scene_count: 1
tv_monitor_positive_scene_count: 1
scenewise_minimal_gate: true
category_robust_gate: false
promotion_ready: false
reason: category_signal_too_sparse
```

#### 에이전트 추론

The robustness check supports keeping `weak_category_rule_v1` as a diagnostic candidate, but it does not support promotion. The rule is safe on this artifact because it has no negative scenes and no new wrong-goals. The signal is not category-robust because each active category improves in only one scene.

For the top-tier paper direction, reject `weak_category_rule_v1` as a paper-facing method and keep it only as diagnostic evidence. The next runtime work should not build an independent split just to validate a category-tuned rule. Instead, it should derive an ablation-ready object-node evidence objective from the failure taxonomy.

Next objective family:

```text
N0_semantic_prior_only
N1_detector_score_only
N2_projection_support_no_depth
N3_strict_depth_association
N4_property_conditioned_depth_reliability
N5_object_node_evidence_full
```

Runtime requirements before rerunning detector/objective validation:

```text
same rule across categories or explicit property groups
property group assignment fixed before validation
no category-name-specific margin tuning on evaluation artifact
new_wrong_goals == 0
positive_scene_count >= 2
property/category robustness gate passes
independent split required before policy-scale integration
```

Implementation contract for the next offline analyzer:

```text
script_name: analyze_object_node_evidence_objective.py
input_detector_root: detector_candidate_associations.jsonl from v3c artifact
input_candidate_decisions: NoReobserve candidate_decisions.jsonl
output_files:
  - summary.json
  - candidate_object_node_features.jsonl
  - objective_variant_decisions.jsonl
  - property_group_summary.jsonl
  - scene_summary.jsonl

variants:
  N0_semantic_prior_only
  N1_detector_score_only
  N2_projection_support_no_depth
  N3_strict_depth_association
  N4_property_conditioned_depth_reliability
  N5_object_node_evidence_full

fixed_property_groups:
  small_or_cluttered: plant
  wall_mounted_or_planar: tv_monitor
  large_repeated_furniture: bed, chair, sofa
  standard_furniture_or_fixture: toilet

promotion_blocker:
  do not run policy-scale integration from this analyzer unless N5 beats N0-N4 under the robustness gate
```

Object-node objective V1 run:

```text
script: runtime/h001_runtime/analyze_object_node_evidence_objective.py
output_root: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1
switch_margin: 0.05
best_variant: N1_detector_score_only
promotion_ready: false
```

Key result:

```text
N1_detector_score_only:
  selected_correct_delta: +0.01
  wrong_goal_fixes: 2
  new_wrong_goals: 1

N5_object_node_evidence_full:
  candidate_auc: 0.6892
  selected_correct_delta: -0.04
  wrong_goal_fixes: 3
  new_wrong_goals: 7
```

N5 margin sweep:

```text
0.10: delta -0.03, fixes 1, new_wrong_goals 4
0.20: delta -0.02, fixes 0, new_wrong_goals 2
0.30: delta  0.00, fixes 0, new_wrong_goals 0
0.40: delta  0.00, fixes 0, new_wrong_goals 0
```

Runtime conclusion:

```text
direct_object_node_reranking: blocked
next_runtime_shape: confirmation/disconfirmation uncertainty update
do_not_promote_policy_scale: true
```

Object-node confirmation / disconfirmation V1:

```text
script: runtime/h001_runtime/analyze_object_node_confirmation.py
input_candidate_features: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
output_root: /tmp/research3-runs/h001_first_eval_replacement_object_node_confirmation_v1
best_config: N1_detector_score_only__cmin_0__cm_0__dm_0.25
promotion_ready: false
reason: same_artifact_confirmation_diagnostic_only
```

Best config behavior:

```text
confirm:
  top detector score >= best alternative detector score

disconfirm:
  best alternative detector score - top detector score >= 0.25
```

Diagnostic result:

```text
confirmed_rows: 58
confirmed_correct_rate: 0.397
confirmed_wrong_goal_rate: 0.448
disconfirmed_rows: 3
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0
wrong_goal_routed_to_reobserve_rate: 0.490
overall_reobserve_request_rate: 0.420
passes_confirm_disconfirm_gate: true
```

Runtime interpretation:

```text
direct_goal_switching: still blocked
safe_use: semantic top-candidate risk update
next_policy_shape: commit only when confirmed, reobserve when disconfirmed/uncertain
needs_independent_validation: true
```

### Confirmation Independent Validation Path

#### 사실

Frozen gate:

```text
gate_name: confirmation_v1_detector_contradiction
field: N1_detector_score_only
confirm: top detector score >= best alternative detector score
disconfirm: best alternative detector score - top detector score >= 0.25
direct_goal_switching: false
```

Independent manifest:

```text
manifest: manifests/h001_confirmation_independent_v1.json
verify: manifests/h001_confirmation_independent_v1.verify.json
split: confirmation_independent_v1
rows: 20
scenes: 6s7QHgap2fW, GLAQ4DNUx5U
source_rule: replacement_probe rows excluding any scene used by first_eval_replacement_v1
docker_verify: passed with /workspace read-only and /tmp verify output
```

Runtime wrapper:

```text
script: runtime/jobs/confirmation_independent_v3c_detector_artifact.sh
candidate_artifact: /tmp/research3-runs/h001_replacement_probe_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
policy_out: /tmp/research3-runs/h001_confirmation_independent_policy_spatial_nms_p97_k20_v1/policy_revision
frames_out: /tmp/research3-runs/h001_confirmation_independent_postview_frames_v2_spatial_nms_p97_k20_v1
detector_out: /tmp/research3-runs/h001_confirmation_independent_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
episodes: 20
max_frames: 20
min_frame_rows: 18
association_rate_gate_for_job_completion: 0.0
```

Launch record:

```text
date_launched: 2026-05-15
session: h001-confirmation-independent-v3c-20260515-160651
log: logs/confirmation-independent-v3c-detector-artifact-20260515-160651.log
status_file: /tmp/research3-runs/h001_confirmation_independent_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1/job_status.json
status: running
stage: detector_mask_scoring
```

Completion and fixed-gate result:

```text
date_checked: 2026-05-15
detector_status: completed
detector_rows: 20
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.45
object_node_output: /tmp/research3-runs/h001_confirmation_independent_object_node_evidence_objective_v1
confirmation_output: /tmp/research3-runs/h001_confirmation_independent_object_node_confirmation_v1
promotion_ready: false
reason: independent_fixed_gate_failed
```

Fixed gate metrics:

```text
baseline_correct_rate: 0.25
baseline_wrong_goal_rate: 0.75
confirmed_rows: 12
confirmed_correct_rate: 0.25
confirmed_wrong_goal_rate: 0.75
disconfirmed_rows: 2
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0
wrong_goal_routed_to_reobserve_rate: 0.40
passes_confirm_disconfirm_gate: false
```

Failure mechanism:

```text
unsafe_confirmation: true
confirmed_wrong_goal: 9 / 12
zero_evidence_ties_confirmed_wrong: 4 / 4
top_positive_alt_zero_confirmed_wrong: 3 / 3
main_scene_failure: GLAQ4DNUx5U has 7 confirmed wrong-goals and no disconfirmations
```

Runtime decision:

```text
policy_integration: blocked
do_not_tune_margin_on_confirmation_independent_v1: true
next_runtime_task: design V2 confirmation rule with explicit evidence-support requirement, then validate on a fresh or larger split
```

V2 rule contract:

```text
gate_name: confirmation_v2_supported_contradiction
input_terms: S_det, S_proj, S_depth, S_prop

positive_evidence_support:
  S_det > 0
  and max(S_proj, S_depth, S_prop) > 0

confirm:
  top candidate has positive_evidence_support
  and top supported evidence >= best alternative supported evidence

disconfirm:
  best alternative has positive_evidence_support
  and best alternative supported evidence - top supported evidence >= fixed contradiction margin

uncertain:
  no evidence, score tie, weak single-term evidence, or sub-margin conflict
```

Implementation requirement:

```text
V2 must expose confirmed / disconfirmed / uncertain counts
no-evidence ties must be uncertain
single detector-score-only support must be uncertain unless projection/depth/property support is also present
direct candidate switching remains disallowed
validation on confirmation_independent_v1 is debugging-only, not promotion evidence
```

V2 debugging result:

```text
output: /tmp/research3-runs/h001_confirmation_independent_object_node_confirmation_v2_debug
rule: supported_contradiction
confirmed_rows: 3
confirmed_wrong_goal_rate: 1.0
disconfirmed_rows: 2
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0
uncertain_rows: 15
wrong_goal_routed_to_reobserve_rate: 0.80
overall_reobserve_request_rate: 0.85
promotion_ready: false
```

Runtime decision after V2 debug:

```text
positive_object_evidence_as_commit_gate: rejected_for_now
object_evidence_as_risk_update: keep
next_method_shape: risk-only re-observation utility
```

Risk-only runtime contract:

```text
policy_name: RiskOnlyReobserve
default_candidate: semantic top candidate
object_evidence_role: risk update only
direct_goal_switch: disallowed
```

Risk terms to log per episode:

```text
R_no_evidence
R_contradiction
R_ambiguity
R_property_weakness
R_total
risk_triggered_reobserve
```

Runtime behavior:

```text
if R_total is high:
  request active re-observation viewpoint
else:
  follow semantic default commit policy
```

Required comparisons:

```text
NoReobserve
RandomReobserve
RiskOnlyReobserve
GTTargetOracle
GTCandidateOracle
GTViewOracle
```

Promotion metrics:

```text
wrong_goal_visit decreases versus NoReobserve
wasted_path does not increase enough to erase SPL/SR utility
risk_triggered_reobserve captures a meaningful fraction of wrong-goal rows
false reobserve on correct top is reported separately
```

Implementation status:

```text
date_checked: 2026-05-15
script: runtime/h001_runtime/run_smoke.py
policy_added: RiskOnlyReobserve
object_node_feature_index: implemented
logging_fields: implemented in episodes, candidate_decisions, viewpoint_decisions
direct_goal_switch: disallowed
```

Docker smoke:

```text
output: /tmp/research3-runs/h001_risk_only_reobserve_smoke_v1
manifest: manifests/h001_confirmation_independent_v1.json
episodes: 4
policies: NoReobserve, RiskOnlyReobserve
candidate_backend: artifact_jsonl
risk_object_node_features: /tmp/research3-runs/h001_confirmation_independent_object_node_evidence_objective_v1/candidate_object_node_features.jsonl

RiskOnlyReobserve:
  success_rate: 0.25
  wrong_goal_visit_rate: 0.75
  risk_triggered_reobserve_rate: 1.0
  mean_R_total: 0.9990
  final_candidate_changed_rate: 0.0
  switch_gate_pass_rate: 0.0
```

Smoke interpretation:

```text
schema_and_policy_behavior: passed
paper_result: false
known_limitation: current risk trigger requests re-observation but does not yet update final candidate or viewpoint utility beyond semantic top viewpoint
```

Risk-only validation split decision:

```text
confirmation_independent_v1: debugging-only
promotion_split: new risk_validation_v1
minimum_size: 5 scenes / 50 episodes
preferred_size: 10 scenes / 100 episodes if substrate coverage passes
exclude_seen_diagnostic_scenes: true
```

Reason:

```text
confirmation_independent_v1 has already influenced V2/risk-only design
2 scenes is too small for top-tier style robustness evidence
fresh split prevents threshold/design leakage
larger split is needed to measure false reobserve and wasted path
```

Prepared split:

```text
manifest: manifests/h001_risk_validation_v1.json
scene_file: manifests/risk_validation_v1_scenes.txt
verify: manifests/h001_risk_validation_v1.verify.json
docker_verify: passed
rows: 100
scene_count: 10
query_counts: bed 20, chair 20, plant 20, sofa 20, toilet 10, tv_monitor 10
```

Candidate artifact job:

```text
date_launched: 2026-05-15
session: h001-risk-validation-p97-k20-20260515-173425
log: logs/risk-validation-spatial-nms-p97-k20-20260515-173425.log
status_file: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/job_status.json
output_root: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1
artifact_id: risk_validation_spatial_nms_p97_k20_v1
status: running
```

Required gate before detector/risk validation:

```text
GTTargetOracle success is high
NoReobserve wrong_goal_visit is nontrivial
candidate label coverage is high
reachable correct-and-wrong ambiguity rate passes the substrate threshold
```

Risk update after active observation:

```text
R_before: semantic ambiguity + missing object-node evidence before the new observation
R_after: object-node risk after active observation evidence is attached
risk_delta_after_reobserve: R_before - R_after
risk_resolved_after_reobserve: R_after < risk_total_trigger
```

Dominant-risk viewpoint selection:

```text
R_no_evidence -> observe semantic top candidate
R_contradiction -> try to observe semantic top and contradictory alternative; otherwise top first
R_ambiguity -> choose reachable candidate viewpoint with highest expected ambiguity reduction under travel cost
R_property_weakness -> use object-property observation preference
```

Commit rule:

```text
if R_before < trigger:
  commit semantic top
elif one active observation resolves risk:
  commit semantic top
else:
  do not make explicit wrong-goal commit in one-step harness
  log termination_reason = risk_unresolved
```

Additional fields:

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

Launch template:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s h001-confirmation-independent-v3c-${ts} \
  "cd /home/yoohyun/research3 && TS=${ts} hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/confirmation_independent_v3c_detector_artifact.sh"
```

After detector artifact completion, build object-node features:

```bash
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_object_node_evidence_objective \
    --detector-root /runs/h001_confirmation_independent_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1 \
    --candidate-decisions /runs/h001_confirmation_independent_policy_spatial_nms_p97_k20_v1/policy_revision/candidate_decisions.jsonl \
    --out /runs/h001_confirmation_independent_object_node_evidence_objective_v1 \
    --policy NoReobserve"
```

Then run the fixed confirmation gate without search:

```bash
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_object_node_confirmation \
    --candidate-features /runs/h001_confirmation_independent_object_node_evidence_objective_v1/candidate_object_node_features.jsonl \
    --out /runs/h001_confirmation_independent_object_node_confirmation_v1 \
    --fields N1_detector_score_only \
    --confirm-mins 0 \
    --confirm-margins 0 \
    --disconfirm-margins 0.25 \
    --fixed-gate-name confirmation_v1_detector_contradiction \
    --independent-validation \
    --min-rows 20"
```

#### 에이전트 추론

This path validates the method shape, not detector association coverage. Therefore the detector wrapper lowers the association-rate completion threshold to `0.0`; the confirmation gate itself decides whether the evidence is useful. If this split fails, do not tune `disconfirm_margin` on it. The next research action should revise the evidence representation or collect a larger validation split.

Policy integration remains blocked until the fixed gate passes independent validation with low false disconfirmation and meaningful wrong-goal routing.

### ObjectNav to Spatial Navigation Scope

#### 에이전트 추론

The current implementation is intentionally ObjectNav-first. ObjectNav gives controlled object targets, GT correctness labels for analysis, wrong-goal visit, wasted path, `Success Rate`, and `SPL`. These are the first falsification metrics for whether semantic uncertainty can guide useful robot motion.

The research direction is not limited to ObjectNav. ObjectNav is the first benchmark gate; the intended extension is spatial navigation / active SLAM. After the semantic uncertainty signal is validated, the same active re-observation utility should be evaluated on map-side and pose-side metrics:

```text
pose graph connectivity
localization failure / tracking loss
map error
semantic accuracy
ATE
RPE
travel cost
```

This keeps the contribution aligned with adaptive AI robots: semantic memory uncertainty should decide where the robot moves next, first to reduce ObjectNav failure and later to improve spatial map / SLAM consistency.

### V3C Prerequisite Restoration

#### 사실

Restoration status on 2026-05-14:

```text
/tmp workspace:
  /tmp/research3-data: recreated
  /tmp/research3-runs: recreated
  /tmp/research3-models: recreated
  permission: writable for Docker jobs

v3c model checkpoints:
  status: restored
  status_file: /tmp/research3-runs/openvocab_perception_v3c_groundingdino_sam2_setup/job_status.json
  status: completed
  stage: verified
  GroundingDINO: /tmp/research3-models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny
  SAM2: /tmp/research3-models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt

HM3D / ObjectNav:
  job_script: runtime/jobs/hm3d_restore.sh
  tmux_session: h001-hm3d-restore
  status_file: /tmp/research3-runs/hm3d_restore/job_status.json
  status: running
  stage: download_hm3d
  log: logs/hm3d-restore-20260514-111758.log
```

The HM3D restore job downloads HM3D assets and `ObjectNav HM3D v2`, then runs:

```bash
python hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_hm3d.py /tmp/research3-data
```

Next restoration steps after HM3D completes:

```text
1. regenerate /tmp/research3-runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl
2. regenerate /tmp/research3-runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/
3. regenerate /tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1/postview_frames_v2.jsonl
4. regenerate /tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl
5. launch v3c calib50 GPU artifact job
```

#### 에이전트 추론

Do not launch a policy-scale comparison from the 2-row smoke. The next run should be a calibration artifact only. GPU approval removes the compute blocker, but the current `/tmp` artifact loss creates a data prerequisite blocker. Regenerate or restore the prerequisites before launching `h001-v3c-calib50-gpu`.

### Acceptance Gates

Artifact acceptance:

```text
postview_frames rows == EvidenceGatedSemanticOnly re-observation rows
postview_scores rows == postview_frames rows
uses_gt_for_action == false for all rows
>= 70 percent of rows have at least one visible candidate score
all score_after values are finite when projection_status == visible
summary.json records projection_status counts
```

Policy acceptance:

```text
candidate_backend_uses_gt_for_action == false
EvidenceGatedSemanticOnly evidence_update_mode == image_feature
switch_gate_pass_rate is logged
final_candidate_changed_rate is logged
wrong_goal_visit_rate does not exceed support_proxy result 0.38
```

Promotion criterion:

```text
image_feature EvidenceGatedSemanticOnly must reduce wrong_goal_visit_rate below NoReobserve on calibration,
or the result is treated as evidence that the current visual-language signal is insufficient.
```

### Failure Interpretation

| Failure | Interpretation | Next action |
| --- | --- | --- |
| many `out_of_fov` / `behind_camera` projections | viewpoint orientation or candidate projection contract is wrong | fix renderer / camera geometry before policy work |
| many `depth_mismatch` / `occluded` projections | candidate positions are not visually inspectable from selected viewpoints | improve viewpoint selector |
| finite scores but no switch gate passes | post-view image-text score does not separate candidates under current thresholds or uses incompatible score scale | inspect score distribution and calibration before tuning |
| switch gates pass but wrong-goal increases | post-view score is misleading | add stronger evidence source or conservative commit gate |
| wrong-goal decreases but `SPL` drops heavily | semantic verification works but travel cost arbitration is weak | add travel-cost term before held-out evaluation |

Implementation status:

```text
export_postview_frames.py: implemented
smoke_output: /tmp/research3-runs/h001_postview_scores_random256_k10_sr1_v1_smoke
smoke_rows_requested: 2
smoke_rows_exported: 2
smoke_expected_files: present
uses_gt_for_action: false
next_step: post-view image_feature Docker smoke run
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

## Risk-Only Two-Stage Update

### Facts

- Implemented policy: `RiskOnlyReobserve`
- Runtime file: `runtime/h001_runtime/run_smoke.py`
- Smoke output: `/tmp/research3-runs/h001_risk_only_reobserve_twostage_smoke_v1`
- Docker image: `research3/habitat-h001:20260508-calib-artifacts`
- The policy now logs `R_before`, `R_after`, `risk_delta_after_reobserve`, `risk_resolved_after_reobserve`, `risk_unresolved_no_commit`, `dominant_risk_term`, `wrong_goal_avoided_by_defer`, and `success_lost_by_defer`.
- Direct goal switching remains disabled: `risk_direct_goal_switch_allowed = false`.

### Inferences

`RiskOnlyReobserve` is now a defer/commit policy rather than a candidate re-ranking policy. Object-node evidence can make the semantic top safe enough to commit, or keep the episode unresolved, but it cannot choose a new final goal. This preserves the paper-facing distinction between risk utility and detector-based goal switching.

## Risk Validation Runtime Status

### Facts

- `risk_validation_v1` candidate artifact completed on 2026-05-15.
- Candidate artifact: `/tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl`
- Coverage output: `/tmp/research3-runs/h001_risk_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity`
- Coverage gate result: `overall_pass = true`
- `GTTargetOracle` success rate: `1.0`
- `NoReobserve` wrong-goal visit rate: `0.47`
- Reachable correct-and-wrong rate: `0.54`
- v3c detector artifact job launched:
  - session: `h001-risk-validation-v3c-20260515-181935`
  - log: `logs/risk-validation-v3c-detector-artifact-20260515-181935.log`
  - detector output: `/tmp/research3-runs/h001_risk_validation_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1`
- v3c detector artifact completed:
  - frame rows: `98`
  - detector box rate: `1.0`
  - SAM2 mask rate: `1.0`
  - candidate association rate: `0.3673`
  - `uses_gt_for_action = false`
- Object-node evidence objective output: `/tmp/research3-runs/h001_risk_validation_object_node_evidence_objective_v1`
- Object-node direct objective status: `promotion_ready = false`
- Risk policy output: `/tmp/research3-runs/h001_risk_validation_risk_only_twostage_v1`
- `RiskOnlyReobserve` result:
  - wrong-goal visit rate: `0.04`
  - success rate: `0.01`
  - risk unresolved no-commit rate: `0.95`
  - wrong-goal avoided by defer rate: `0.43`
  - success lost by defer rate: `0.18`
- `RiskResolutionReobserve` output: `/tmp/research3-runs/h001_risk_validation_risk_resolution_v1`
- `RiskResolutionReobserve` result:
  - wrong-goal visit rate: `0.07`
  - success rate: `0.06`
  - mean SPL: `0.0310`
  - risk unresolved no-commit rate: `0.87`
  - risk resolution commit rate: `0.08`

### Inferences

The substrate is strong enough, but the current risk policy is not. Detector/object-node evidence is usable as a diagnostic risk signal, not as a direct goal-selector. `RiskResolutionReobserve` shows that simple commit arbitration recovers some success but still leaves most episodes unresolved and remains below `NoReobserve`.

The main runtime gap is now evidence resolution: the system needs a way to turn unresolved semantic risk into additional targeted observation or stronger candidate association so that `R_after` can actually decrease. One-step commit arbitration alone is not enough.

## Risk Evidence-Resolution Runtime Decision

### Facts

- Current unresolved bottleneck: `RiskResolutionReobserve` has `risk_unresolved_no_commit_rate = 0.87`.
- Current detector/mask availability is high: detector box rate `1.0`, `SAM2` mask rate `1.0`.
- Current candidate association remains weak: `candidate_association_rate = 0.3673`.
- Direct object-node re-ranking is blocked because it creates new wrong-goals.

### Inferences

The next runtime step should not be a full policy-scale run. It should be a small diagnostic that tests whether a targeted second observation can recover candidate-object association on rows where the first risk update remained unresolved.

The selected design is `AssociationRecoveryObservation`:

```text
second targeted observation + candidate-association recovery
```

This is stronger than choosing either option alone:

- a second observation without association recovery may only add travel cost;
- offline association recovery without motion weakens the active SLAM/navigation utility claim.

### Runtime Contract

First implementation target:

```text
script purpose: generate and evaluate a second-observation association-recovery diagnostic
input run: /tmp/research3-runs/h001_risk_validation_risk_resolution_v1
input candidate artifact: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
input object-node features: /tmp/research3-runs/h001_risk_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
output root: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1
max debug rows: 20 unresolved rows
docker image: research3/habitat-h001:20260508-calib-artifacts for planning/frame export
detector image: research3/openvocab-perception:20260513-v3c-gdino-sam2 for detector/mask scoring
```

Expected files:

```text
second_observation_plan.jsonl
second_observation_frames.jsonl
detector_candidate_associations.jsonl
candidate_object_node_features_after_second.jsonl
risk_resolution_after_second_summary.json
association_recovery_arbitration_summary.json
```

Promotion condition for policy integration:

```text
risk_resolved_after_second_observation_rate improves by at least 10 percentage points
association_recovered_rate >= 0.20 on previously unsupported top candidates
no GT field is used for action selection
commit simulation does not raise wrong-goal rate by more than 0.03 absolute versus RiskResolutionReobserve
```

### Implementation Status

```text
date_checked: 2026-05-15
planner_module: h001_runtime.plan_association_recovery_observation
analyzer_module: h001_runtime.analyze_association_recovery_observation
job_wrapper: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/risk_validation_association_recovery_observation_v1.sh
schema_smoke_output: /tmp/research3-runs/h001_association_recovery_observation_schema_smoke
schema_smoke_plan_rows: 20
schema_smoke_unresolved_input_rows: 87
schema_smoke_uses_gt_for_action: false
```

The next executable step is the Docker job wrapper. It should write:

```text
/tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/second_observation_plan.jsonl
/tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/second_observation_frames.jsonl
/tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/detector_candidate_associations.jsonl
/tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/candidate_object_node_features_after_second.jsonl
/tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/risk_resolution_after_second_summary.json
```

Launch status:

```text
date_launched: 2026-05-16
session: h001-assoc-recovery-v1-20260516-093917
working_directory: /home/yoohyun/research3
command: TS=20260516-093917 LOG=/home/yoohyun/research3/logs/risk-validation-association-recovery-observation-v1-20260516-093917.log OUT=/tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1 MAX_ROWS=20 hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/risk_validation_association_recovery_observation_v1.sh
log: logs/risk-validation-association-recovery-observation-v1-20260516-093917.log
output_root: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1
status_file: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/job_status.json
initial_status: running/detector_mask_scoring
expected_files: second_observation_plan.jsonl, second_observation_frames.jsonl, detector_candidate_associations.jsonl, candidate_object_node_features_after_second.jsonl, risk_resolution_after_second_summary.json
verification_command: cat /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/job_status.json && cat /tmp/research3-runs/h001_risk_validation_association_recovery_observation_v1/risk_resolution_after_second_summary.json
```

Completion result:

```text
date_checked: 2026-05-16
status: completed
stage: verified
detector_box_rate: 1.0
SAM2_mask_rate: 1.0
rows_with_candidate_association_rate: 0.10
association_recovered_rate: 0.0
risk_resolved_after_second_observation_rate: 0.0
risk_unresolved_after_second_observation_rate: 1.0
gate_pass: false
decision: do not promote AssociationRecoveryObservation v1
```

Runtime inference:

```text
current failure: second observation is renderable but not association-recovering
likely cause: candidate visit_position is not a reliable inspection viewpoint
next runtime change: standoff / visibility-aware second-view planner with projection sanity before detector scoring
```

Standoff-view planner revision:

```text
date_checked: 2026-05-16
planner_change: choose a standoff camera base around candidate position, orient yaw toward the target candidate, and snap the camera base to HM3D navmesh when --data-root is available
host_schema_smoke: /tmp/research3-runs/h001_association_recovery_observation_standoff_schema_smoke
docker_plan_smoke: /tmp/research3-runs/h001_association_recovery_observation_standoff_docker_plan_smoke
docker_plan_rows: 20
docker_projection_sane_rate: 1.0
docker_navmesh_snapped_rate: 1.0
docker_viewpoint_source: standoff_navmesh
uses_gt_for_action: false
```

Standoff diagnostic launch:

```text
date_launched: 2026-05-16
session: h001-assoc-recovery-standoff-v1-20260516-100438
working_directory: /home/yoohyun/research3
command: TS=20260516-100438 OUT=/tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1 RUN_ID=h001_risk_validation_association_recovery_observation_standoff_v1_20260516-100438 LOG=/home/yoohyun/research3/logs/risk-validation-association-recovery-observation-standoff-v1-20260516-100438.log MAX_ROWS=20 DEVICE=cuda bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/risk_validation_association_recovery_observation_v1.sh
log: logs/risk-validation-association-recovery-observation-standoff-v1-20260516-100438.log
output_root: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1
status_file: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/job_status.json
initial_status: running/detector_mask_scoring
expected_files: second_observation_plan.jsonl, second_observation_frames.jsonl, detector_candidate_associations.jsonl, candidate_object_node_features_after_second.jsonl, risk_resolution_after_second_summary.json
verification_command: cat /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/job_status.json && cat /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/risk_resolution_after_second_summary.json
```

Standoff diagnostic completion:

```text
date_checked: 2026-05-16
status: completed
stage: verified
rows_with_candidate_association_rate: 0.40
association_recovered_rate: 0.3571
top_positive_support_after_second_rate: 0.55
risk_resolved_after_second_observation_rate: 0.0
commit_after_second_observation_rate: 0.10
wrong_goal_commit_rate_if_fixed_commit_gate_applied: 0.10
gate_pass: false
decision: do not promote to policy integration yet
```

Runtime inference:

```text
fixed: standoff viewpoints improved candidate-object association recovery
not fixed: recovered association is not yet safe commitment evidence
next runtime change: classify standoff failure modes and revise risk update / commit-defer arbitration before any policy-scale comparison
```

Failure taxonomy artifact:

```text
script: h001_runtime.analyze_association_recovery_failure_modes
rows: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_failure_modes.jsonl
summary: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_failure_mode_summary.json
primary failures: persistent_no_evidence 9, recovered_or_supported_wrong_top 7, unsafe_commit_wrong_top 2, correct_top_supported_but_deferred 2
next implementation target: commit/defer arbitration revision
```

Commit/defer arbitration design:

```text
script: h001_runtime.analyze_association_recovery_arbitration
rows: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_arbitration_rows.jsonl
summary: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_arbitration_summary.json
docker_smoke: passed
uses_gt_for_action: false
```

Decision states:

```text
commit_top
reject_top_or_defer
reject_top_or_request_pair_view
request_paired_top_alt_view
request_property_targeted_view
retry_association_or_defer
defer_insufficient_margin
```

Diagnostic result:

```text
commit_top_rate: 0.0
wrong_goal_commit_rate_if_arbitration_applied: 0.0
success_lost_by_arbitration_defer_rate: 0.15
wrong_goal_avoided_by_arbitration_defer_rate: 0.85
action_counts: reject_top_or_defer 6, reject_top_or_request_pair_view 8, request_paired_top_alt_view 3, retry_association_or_defer 3
```

Runtime inference:

```text
arbitration blocks unsafe commits but is over-conservative by itself
next runtime implementation should turn reject/request states into paired top-vs-alt or retry observations instead of broadening the commit threshold
```

Analyzer/job integration:

```text
date_checked: 2026-05-18
integrated_module: h001_runtime.analyze_association_recovery_observation
job_wrapper_expected_file: association_recovery_arbitration_summary.json
verified_output_root: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1
verified_rows: 20
verified_commit_top_rate: 0.0
verified_wrong_goal_commit_rate_if_arbitration_applied: 0.0
verified_action_counts: reject_top_or_defer 6, reject_top_or_request_pair_view 8, request_paired_top_alt_view 3, retry_association_or_defer 3
uses_gt_for_action: false
```

Paired top-vs-alt observation design:

```text
date_checked: 2026-05-18
design_diagnostic_module: h001_runtime.analyze_pair_observation_design
docker_smoke_output: /tmp/research3-runs/h001_pair_observation_design_docker_smoke
input_rows: /tmp/research3-runs/h001_risk_validation_association_recovery_observation_standoff_v1/association_recovery_arbitration_rows.jsonl
candidate_artifact: /tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
pair_trigger_rows: 11
common_pair_view_feasible_rate: 0.3636
dual_standoff_feasible_rate: 1.0
mode_counts: common_pair_view 4, matched_dual_standoff 7
uses_gt_for_action: false
```

Runtime design:

```text
trigger actions:
  reject_top_or_request_pair_view
  request_paired_top_alt_view

Mode A: common_pair_view
  one navmesh-snapped viewpoint
  candidate_ids include top and alt
  allowed only when both candidates fit distance and bearing gates

Mode B: matched_dual_standoff
  two matched standoff observations with shared pair_observation_id
  one role=top, one role=alt
  same detector/mask settings and candidate budget
  selected when common_pair_view is not feasible
```

Next implementation target:

```text
extend planner/analyzer path so paired observation rows can be rendered through export_postview_frames_v2
do not use GT fields for action
do not broaden commit thresholds before pair evidence is measured
```

Planner implementation:

```text
date_checked: 2026-05-18
planner_module: h001_runtime.plan_pair_observation
policy_name: PairTopAltObservation
verified_output_root: /tmp/research3-runs/h001_pair_observation_plan_docker_smoke
pair_count: 11
plan_rows: 18
mode_counts: common_pair_view 4, matched_dual_standoff 7
role_counts: common 4, top 7, alt 7
navmesh_snapped_row_rate: 1.0
frame_export_ok: true
frame_rows: 18
rendered_heading_count: 112
uses_gt_for_action: false
```

Expected planner files:

```text
pair_observation_plan.jsonl
pair_observation_skipped.jsonl
pair_observation_plan_summary.json
pair_observation_frames.jsonl
```

Paired detector/analysis diagnostic gate:

```text
date_checked: 2026-05-18
analyzer_module: h001_runtime.analyze_pair_observation_evidence
schema_smoke_output: /tmp/research3-runs/h001_pair_observation_gate_schema_smoke
empty_evidence_smoke_output: /tmp/research3-runs/h001_pair_observation_evidence_empty_smoke
schema_smoke_frame_rows: 18
schema_smoke_rendered_heading_count: 112
empty_evidence_pair_rows: 11
empty_evidence_action_counts: pair_unresolved_no_evidence 11
empty_evidence_gate_pass: false
uses_gt_for_action: false
```

Metadata contract:

```text
export_postview_frames_v2.py:
  preserve pair_* and arbitration_* fields in postview frame rows

detect_postview_groundingdino_sam2.py:
  preserve pair_* and arbitration_* fields in detector_boxes.jsonl
  preserve pair_* and arbitration_* fields in sam2_masks.jsonl
  preserve pair_* and arbitration_* fields in detector_candidate_associations.jsonl
  preserve pair_* and arbitration_* fields in detector_frame_summary.jsonl
```

Gate:

```text
pair_evidence_margin: 0.05
min_pair_evidence_available_rate: 0.50
min_pair_disambiguation_rate: 0.30
min_wrong_top_reject_rate: 0.30
max_false_reject_correct_top_rate: 0.10
max_support_wrong_top_rate: 0.10
```

Expected paired diagnostic files:

```text
detector_candidate_associations.jsonl
pair_observation_evidence_rows.jsonl
pair_observation_evidence_summary.json
```

Paired detector/analysis diagnostic launch:

```text
date_launched: 2026-05-18
tmux_session: h001-pair-observation-detector-evidence-v1-20260518-014114
working_directory: /home/yoohyun/research3
job_wrapper: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/pair_observation_detector_evidence_v1.sh
command: TS=20260518-014114 OUT=/tmp/research3-runs/h001_pair_observation_detector_evidence_v1 LOG=/home/yoohyun/research3/logs/pair-observation-detector-evidence-v1-20260518-014114.log DEVICE=cuda hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/pair_observation_detector_evidence_v1.sh
log: logs/pair-observation-detector-evidence-v1-20260518-014114.log
output_root: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1
status_file: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1/job_status.json
status_at_launch_check: running, stage=detector_mask_scoring
expected_files:
  pair_observation_plan.jsonl
  pair_observation_frames.jsonl
  detector_candidate_associations.jsonl
  pair_observation_evidence_rows.jsonl
  pair_observation_evidence_summary.json
verification_command: cat /tmp/research3-runs/h001_pair_observation_detector_evidence_v1/job_status.json && cat /tmp/research3-runs/h001_pair_observation_detector_evidence_v1/summary.json && cat /tmp/research3-runs/h001_pair_observation_detector_evidence_v1/pair_observation_evidence_summary.json
```

Completion result:

```text
date_checked: 2026-05-18
status: completed
status_stage: verified
detector_rows: 18
detector_box_rate: 1.0
sam2_mask_rate: 1.0
candidate_association_rate: 0.6667
association_rows: 217
pair_rows: 11
pair_evidence_available_rate: 1.0
pair_disambiguation_rate: 0.9091
pair_action_counts: pair_support_top 7, pair_reject_top 3, pair_ambiguous_defer 1
wrong_top_rows: 9
correct_top_rows: 2
wrong_top_reject_rate: 0.1111
support_wrong_top_rate: 0.7778
false_reject_correct_top_rate: 1.0
gate_pass: false
uses_gt_for_action: false
```

Interpretation:

```text
detector/mask availability: passed
candidate association coverage: improved enough for diagnosis
paired evidence objective: failed
policy-scale integration: blocked
next_runtime_problem: paired evidence failure taxonomy and score/objective revision
```

Paired evidence failure taxonomy:

```text
date_checked: 2026-05-18
analyzer_module: h001_runtime.analyze_pair_observation_failure_modes
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

Reinterpreted rates:

```text
alt_only_correct_rows: 4
alt_only_correct_reject_top_rate: 0.0
alt_only_correct_support_wrong_top_rate: 0.75
neither_candidate_correct_rows: 5
neither_candidate_correct_forced_choice_rate: 1.0
both_candidates_correct_rows: 2
both_candidates_correct_reject_top_rate: 1.0
top_only_correct_rows: 0
```

Runtime implication:

```text
detector/mask availability is not the bottleneck
raw paired support is not a valid commit/reject objective
the next objective needs no-valid-candidate handling, both-correct ambiguity handling, and matched-view normalization
policy-scale integration remains blocked
```

Paired objective v2:

```text
date_checked: 2026-05-18
analyzer_module: h001_runtime.analyze_pair_observation_objective_v2
output_root: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1
summary: pair_observation_objective_v2_summary.json
rows_file: pair_observation_objective_v2_rows.jsonl
rows: 11
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Design contract:

```text
paired branch is reject-or-defer, not top recommit
support_top is disabled by default
reject_top requires:
  prior arbitration alt gap
  view-normalized alt strict-association advantage
  top disconfirmation or weak top association
otherwise:
  defer_view_not_comparable
  defer_no_valid_candidate_or_external_search
  defer_insufficient_disconfirmation
```

Current diagnostic result:

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

Important limitation:

```text
same_split_revision: true
paper_claim_status: blocked
next_gate: held-out paired objective v2 validation
```

Held-out paired objective v2 validation contract:

```text
date_checked: 2026-05-18
contract_name: heldout_pair_objective_v2_validation_v1
objective_under_test: h001_runtime.analyze_pair_observation_objective_v2
design_split: risk_validation_v1
heldout_split: first_eval_replacement_v1
heldout_manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_first_eval_replacement_v1.json
heldout_manifest_verify: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_first_eval_replacement_v1.verify.json
heldout_scenes: 10
heldout_episodes: 100
scene_overlap_with_risk_validation_v1: 0
debugging_only_split: confirmation_independent_v1
policy_scale_integration_status: blocked
```

Existing prerequisites:

```text
candidate_artifact: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
object_node_features: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
baseline_policy_root: /tmp/research3-runs/h001_first_eval_replacement_policy_spatial_nms_p97_k20_v1/policy_revision
baseline_detector_root: /tmp/research3-runs/h001_first_eval_replacement_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1
```

Required pipeline:

```text
1. RiskResolutionReobserve on first_eval_replacement_v1
2. AssociationRecoveryObservation standoff diagnostic
3. association recovery arbitration
4. PairTopAltObservation planning
5. pair frame export
6. GroundingDINO + SAM2 detector/mask scoring
7. pair_observation_evidence
8. pair_observation_failure_modes
9. pair_observation_objective_v2 with fixed thresholds
```

Output root:

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

Long-running job policy:

```text
run in tmux
write log under logs/
write status to job_status.json
record exact command and verification command before launch
do not continuously monitor
```

Substrate validity gate:

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

Disallowed during validation:

```text
changing v2 thresholds on first_eval_replacement_v1
changing pair_evidence_margin on first_eval_replacement_v1
selecting categories or scenes after seeing held-out objective result
using GT candidate correctness for action
reporting this as policy-scale result
```

Interpretation rule:

```text
pass: write policy integration contract, still not final paper evidence
fail_due_to_pair_evidence_unavailable: revise pair observation geometry
fail_due_to_wrong_top_support: revise object-node / detector evidence
fail_due_to_neither_candidate_correct: add external candidate search or no-valid-candidate branch
```

Held-out paired substrate generation launch:

```text
date_launched: 2026-05-18
tmux_session: h001-first-eval-pair-substrate-v1-20260518-020840
working_directory: /home/yoohyun/research3
job_wrapper: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/first_eval_replacement_pair_objective_v2_substrate.sh
command: TS=20260518-020840 OUT=/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1 LOG=/home/yoohyun/research3/logs/first-eval-replacement-pair-objective-v2-substrate-20260518-020840.log DEVICE=cuda MAX_ASSOC_ROWS=40 hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/first_eval_replacement_pair_objective_v2_substrate.sh
log: logs/first-eval-replacement-pair-objective-v2-substrate-20260518-020840.log
output_root: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1
status_file: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/job_status.json
status_at_launch_check: running, stage=association_recovery_frame_export
```

Launched pipeline:

```text
RiskResolutionReobserve on first_eval_replacement_v1
AssociationRecoveryObservation standoff diagnostic with MAX_ASSOC_ROWS=40
association recovery arbitration
PairTopAltObservation planning
pair frame export
GroundingDINO + SAM2 pair detector/mask scoring
pair_observation_evidence
pair_observation_failure_modes
```

Expected substrate files:

```text
risk_resolution_summary.json
association_recovery_arbitration_summary.json
association_recovery_arbitration_rows.jsonl
pair_observation_plan.jsonl
pair_observation_plan_summary.json
pair_observation_frames.jsonl
detector_candidate_associations.jsonl
summary.json
pair_observation_evidence_rows.jsonl
pair_observation_evidence_summary.json
pair_observation_failure_modes.jsonl
pair_observation_failure_mode_summary.json
heldout_pair_substrate_summary.json
job_status.json
```

Verification command:

```bash
cat /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/job_status.json
cat /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/heldout_pair_substrate_summary.json
cat /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_evidence_summary.json
```

Held-out substrate verification result:

```text
date_checked: 2026-05-18
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

Held-out pair evidence and taxonomy:

```text
pair_evidence_action_counts: pair_support_top 12, pair_reject_top 8, pair_ambiguous_defer 4
support_wrong_top_rate: 0.5714
wrong_top_reject_rate: 0.2857
false_reject_correct_top_rate: 0.4
passes_pair_evidence_diagnostic_gate: false
primary_failure_modes: neither_candidate_correct_pair_forces_choice 13, both_candidates_correct_rank_ambiguity 5, low_risk_or_uncategorized 3, false_reject_correct_top 2, wrong_top_supported_by_association_count 1
```

Held-out objective v2 result:

```text
date_checked: 2026-05-18
analyzer_module: h001_runtime.analyze_pair_observation_objective_v2
summary: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_objective_v2_summary.json
rows: 24
passes_pair_objective_v2_gate: false
wrong_goal_commit_rate: 0.0
wrong_goal_commit_rate_on_commits: 0.0
support_wrong_top_rate: 0.0
neither_candidate_commit_rate: 0.0
alt_only_reject_or_defer_rate: 1.0
commit_rate: 0.0417
min_commit_rate: 0.15
success_commit_rate: 0.0417
uses_gt_for_action: false
```

Action counts:

```text
pair_v2_defer_insufficient_disconfirmation: 7
pair_v2_defer_rank_ambiguous: 7
pair_v2_defer_view_not_comparable: 7
pair_v2_defer_no_valid_candidate_or_external_search: 2
pair_v2_reject_top_confirm_alt: 1
```

Interpretation:

```text
safety_gate: passed
utility_gate: failed
primary_failure: over-deferral / insufficient commit utility
policy_scale_integration: blocked
next_runtime_target: diagnose held-out V2 over-deferral before any threshold change
```

Next runtime target:

```text
diagnose held-out objective v2 over-deferral
do not lower commit thresholds on first_eval_replacement_v1
keep policy-scale integration blocked until the paired diagnostic has a positive evidence gate
```

Held-out objective v2 over-deferral diagnosis:

```text
date_checked: 2026-05-18
analyzer_module: h001_runtime.analyze_pair_observation_v2_overdeferral
summary: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_v2_overdeferral_summary.json
rows: 24
commit_rows: 1
deferred_rows: 23
commit_gate_gap_rows: 3
pair_correct_candidate_deferred_rows: 10
pair_correct_commit_ceiling_rate: 0.4583
neither_candidate_deferred_rows: 13
view_not_comparable_deferred_rows: 7
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Revision diagnosis:

```text
safety_status: passed
utility_status: failed_overdeferral
recommended_next_action: success_preserving_pair_objective_revision
reason: deferred rows with a correct top/alt candidate are enough to close the fixed commit gate
secondary_priority: external_candidate_branch, paired_view_geometry_revision, rank_ambiguity_handling
```

Updated next runtime target:

```text
design fixed success-preserving pair objective v3
preserve zero support-wrong-top and zero neither-candidate commit behavior
do not enable top support without a non-GT safety gate
do not run policy-scale integration yet
```

Paired objective v3 implementation and diagnostic:

```text
date_checked: 2026-05-18
analyzer_module: h001_runtime.analyze_pair_observation_objective_v3
design_smoke_summary: /tmp/research3-runs/h001_pair_observation_detector_evidence_v1/pair_observation_objective_v3_summary.json
heldout_diagnostic_summary: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_objective_v3_summary.json
new_action: pair_v3_commit_top_common_view_survival
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Held-out diagnostic gate:

```text
passes_pair_objective_v3_gate: true
commit_rate: 0.1667
wrong_goal_commit_rate: 0.0
wrong_goal_commit_rate_on_commits: 0.0
support_wrong_top_rate: 0.0
top_survival_wrong_commit_rate: 0.0
neither_candidate_commit_rate: 0.0
```

Diagnostic caveat:

```text
status: mechanism diagnostic only
reason: first_eval_replacement_v1 was already used to diagnose V2 over-deferral before V3 was implemented
paper_claim_status: blocked until fresh validation or broader split confirms the same behavior
policy_scale_integration_status: blocked until remaining neither-candidate deferrals have an external-candidate/no-valid-pair recovery path
```

Next runtime target:

```text
add external-candidate branch for neither-candidate-correct cases
preserve V3 pair-local safety gate
do not tune V3 on first_eval_replacement_v1
```

External-candidate branch implementation:

```text
date_checked: 2026-05-18
planner_module: h001_runtime.plan_external_candidate_observation
input_pair_rows: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_objective_v3_rows.jsonl
candidate_artifact: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
object_node_features: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
summary: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/external_candidate_branch_summary.json
plan_rows: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/external_candidate_observation_plan.jsonl
policy: ExternalCandidateObservation
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Branch output:

```text
rows: 24
triggered_rows: 15
plan_rows: 90
skipped_rows: 0
neither_candidate_triggered_rows: 13
neither_candidate_external_set_contains_correct_rate: 0.3846
neither_candidate_first_external_correct_rate: 0.0
pair_correct_candidate_unnecessary_external_rows: 2
```

Export smoke:

```text
summary: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/external_candidate_frame_smoke/summary.json
ok: true
rows_requested: 2
rows_exported: 2
rendered_heading_count: 5
uses_gt_for_action: false
```

Runtime interpretation:

```text
branch_status: implemented and renderable
commit_status: no external candidate commit yet
blocking_issue: first external candidate correctness is 0.0 and K=6 candidate-set recall is only 0.4667 on triggered rows
next_action: validate pair-local V3 on a fresh split before paper claim, and treat external branch as a recovery path that still needs retrieval/ranking improvement
```

External-candidate rank-band retrieval revision:

```text
date_checked: 2026-05-18
planner_module: h001_runtime.plan_external_candidate_observation
selection_mode: rank_bands
rank_band_pattern: 1,2,3,4,6,10
input_pair_rows: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/pair_observation_objective_v3_rows.jsonl
candidate_artifact: /tmp/research3-runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
object_node_features: /tmp/research3-runs/h001_first_eval_replacement_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
output_root: /tmp/research3-runs/h001_first_eval_replacement_pair_objective_v2_validation_v1/external_candidate_rank_bands_v1
summary: external_candidate_branch_summary.json
plan_rows: external_candidate_observation_plan.jsonl
frame_smoke: frame_smoke/summary.json
```

Diagnostic result:

```text
triggered_rows: 15
plan_rows: 90
skipped_rows: 0
external_budget: 6
external_selection_mode: rank_bands
rank_bands K=6 recall on triggered rows: 0.6000
rank_bands K=6 recall on neither-candidate rows: 0.5385
rank_bands full external pool recall on neither-candidate rows: 0.5385
first external correct rate on neither-candidate rows: 0.0000
frame_smoke_ok: true
frame_smoke_rows_exported: 2
uses_gt_for_action: false
uses_gt_for_analysis: true
```

Runtime interpretation:

```text
rank_band_status: implemented and renderable
improvement_over_semantic_rank: K=6 triggered recall 0.4667 -> 0.6000; neither-candidate K=6 recall 0.3846 -> 0.5385
remaining_bottleneck: artifact memory coverage, because rank_bands already reaches full external-pool recall on neither-candidate rows
paper_claim_status: still blocked until fresh split validation and scored observation evidence
```

Fresh V3 validation split:

```text
date_checked: 2026-05-18
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_v3_fresh_validation_v1.json
verify: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_v3_fresh_validation_v1.verify.json
scene_list: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/v3_fresh_validation_v1_scenes.txt
selected_split: v3_fresh_validation_v1
rows: 100
scenes: 13
query_counts: bed 17, chair 17, plant 16, sofa 17, toilet 17, tv_monitor 16
source_split: HM3D ObjectNav v2 val
docker_verify_ok: true
sim_scene_limit: 2
```

Excluded scene groups:

```text
first_eval
first_eval_replacement_v1
replacement_probe
confirmation_independent
risk_validation_v1
```

Validation lock:

```text
do not tune pair_v3 on v3_fresh_validation_v1 after scoring starts
do not change selected scenes or category quota after scoring starts
do not report first_eval_replacement_v1 V3 diagnostic as paper evidence
paper claim remains blocked until v3_fresh_validation_v1 candidate artifact, object-node features, pair substrate, detector evidence, and pair objective pass fixed gates
```

Next runtime target:

```text
build v3_fresh_validation_v1 candidate artifact and coverage gate as a background Docker job
```

V3 fresh artifact and coverage job launch:

```text
date_launched: 2026-05-18
job_wrapper: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/v3_fresh_validation_candidate_artifact_coverage.sh
tmux_session: h001-v3-fresh-artifact-coverage-20260518-092319
log: logs/v3-fresh-validation-artifact-coverage-20260518-092319.log
pipeline_status: /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/pipeline_status.json
artifact_out: /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1
coverage_out: /tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity
candidate_artifact: /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
coverage_summary: /tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
initial_status: running
initial_stage: candidate_artifact_generation
```

Fixed job parameters:

```text
manifest: manifests/h001_v3_fresh_validation_v1.json
manifest_split: v3_fresh_validation_v1
scene_specs_file: manifests/v3_fresh_validation_v1_scenes.txt
frames: 256
selection_mode: spatial_nms
top_percentile: 97.0
max_candidates: 20
spatial_nms_min_distance_cells: 20.0
expected_scene_count: 13
expected_query_rows: 78
episodes_for_coverage: 100
```

Verification command:

```bash
cat /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/pipeline_status.json
cat /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/job_status.json
cat /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/coverage_check.json
cat /tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
```

Do not monitor continuously. Check this job only when requested or before `run fixed-rule pair-local V3 validation on v3_fresh_validation_v1`.

V3 fresh artifact and coverage completion:

```text
date_checked: 2026-05-18
pipeline_status: completed
job_status: completed
tmux_session: completed and closed
candidate_artifact: /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
coverage_summary: /tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
coverage_gate: pass
overall_pass: true
```

Artifact verification:

```text
scenes: 13
query_rows: 78
candidates: 1560
finite_candidate_positions: 1560
navigable_visit_positions: 1411
```

Coverage verification:

```text
episodes: 100
candidate_label_coverage: 1.0
episodes_with_correct_candidate_rate: 0.79
episodes_with_reachable_correct_rate: 0.69
episodes_with_reachable_wrong_rate: 0.97
episodes_with_reachable_correct_and_wrong_rate: 0.69
candidate_reachable_rate: 0.732
top_candidate_correct_rate: 0.31
top_candidate_reachable_rate: 0.88
GTTargetOracle success_rate: 1.0
NoReobserve success_rate: 0.26
NoReobserve SPL: 0.1459
NoReobserve wrong_goal_visit_rate: 0.61
```

Runtime interpretation:

```text
fixed_rule_pair_v3_validation: unblocked
do_not_tune_after_this_gate: true
paper_claim_status: still blocked until fixed-rule V3 substrate, detector evidence, and objective gates pass on this split
```

Fixed-rule pair-local V3 validation launch:

```text
date_launched: 2026-05-18
job_wrapper: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/v3_fresh_validation_pair_objective_v3.sh
tmux_session: h001-v3-fresh-pair-v3-20260518-100545
log: logs/v3-fresh-validation-pair-objective-v3-20260518-100545.log
status: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pipeline_status.json
output_root: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1
```

Inputs:

```text
manifest: hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_v3_fresh_validation_v1.json
manifest_split: v3_fresh_validation_v1
candidate_artifact: /tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl
coverage_summary: /tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json
coverage_required: overall_pass true
```

Pipeline:

```text
1. generate fresh v3c detector artifact and policy/frame outputs
2. derive object-node evidence features for NoReobserve candidate decisions
3. run RiskResolutionReobserve, AssociationRecoveryObservation, and PairTopAltObservation substrate
4. score pair detector/mask evidence
5. run fixed-threshold analyze_pair_observation_objective_v3
```

Expected outputs:

```text
detector_summary: /tmp/research3-runs/h001_v3_fresh_validation_detector_v3c_a4_all_headings_spatial_nms_p97_k20_v1/summary.json
object_node_features: /tmp/research3-runs/h001_v3_fresh_validation_object_node_evidence_objective_v1/candidate_object_node_features.jsonl
substrate_summary: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/heldout_pair_substrate_summary.json
pair_v3_summary: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pair_observation_objective_v3_summary.json
fixed_validation_summary: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/fixed_rule_pair_v3_validation_summary.json
```

Verification command:

```bash
cat /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pipeline_status.json
cat /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/heldout_pair_substrate_summary.json
cat /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pair_observation_objective_v3_summary.json
```

Do not monitor continuously. Check this job only when requested or before deciding whether to revise pair observation geometry.

Fixed-rule pair-local V3 validation result:

```text
date_checked: 2026-05-18
pipeline_status: completed
tmux_session: completed and closed
substrate_gate: pass
pair_objective_v3_gate: fail
uses_gt_for_action: false
```

Substrate gate:

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

Detector diagnostic:

```text
detector_rows: 100
rows_with_detector_box_rate: 0.97
rows_with_sam2_mask_rate: 0.97
rows_with_candidate_association_rate: 0.53
associated_candidate_heading_count: 182
uses_gt_for_action: false
```

Fixed V3 objective gate:

```text
rows: 31
passes_pair_objective_v3_gate: false
commit_rate: 0.0323
min_commit_rate: 0.15
wrong_goal_commit_rate: 0.0323
support_wrong_top_rate: 0.0323
top_survival_wrong_commit_rate: 1.0
neither_candidate_commit_rate: 0.0909
alt_only_reject_top_rate: 0.0
```

Action counts:

```text
pair_v3_commit_top_common_view_survival: 1
pair_v3_defer_view_not_comparable: 15
pair_v3_defer_rank_ambiguous: 8
pair_v3_defer_insufficient_disconfirmation: 5
pair_v3_defer_no_valid_candidate_or_external_search: 2
```

Fresh failure taxonomy:

```text
neither_candidate_correct_pair_forces_choice: 11
both_candidates_correct_rank_ambiguity: 10
wrong_top_supported_by_detector_confidence: 5
alt_correct_but_pair_ambiguous: 2
false_reject_correct_top: 1
low_risk_or_uncategorized: 2
```

Runtime interpretation:

```text
policy_scale_integration: blocked
threshold_tuning_on_v3_fresh_validation_v1: disallowed
primary_next_step: revise pair observation geometry/objective from failure taxonomy
specific_next_targets: no-valid-candidate handling, both-candidates-correct ambiguity, view-not-comparable geometry, and top-survival safety
```

Revised pair observation geometry smoke:

```text
date_checked: 2026-05-18
planner: runtime/h001_runtime/plan_pair_observation.py
new planner option: --include-dual-fallback-for-common
substrate wrapper default: PAIR_INCLUDE_DUAL_FALLBACK_FOR_COMMON=1
plan_smoke_out: /tmp/research3-runs/h001_v3_fresh_validation_pair_geometry_v2_plan_smoke
frame_smoke_out: /tmp/research3-runs/h001_v3_fresh_validation_pair_geometry_v2_frame_smoke
```

Plan smoke result:

```text
pair_count: 31
plan_rows: 86
mode_counts: common_with_dual_fallback 24, matched_dual_standoff 7
role_counts: common 24, top 31, alt 31
common_dual_fallback_unavailable_pairs: 0
skipped_rows: 0
navmesh_snapped_row_rate: 1.0
uses_gt_for_action: false
```

Frame export smoke result:

```text
rows_exported: 6
rendered_heading_count: 32
errors: 0
uses_gt_for_action: false
```

Runtime interpretation:

```text
view_not_comparable_geometry: addressed at planner level by adding top/alt standoff fallback to common-view pairs
top_survival_branch: should not be trusted until pair objective v4 removes or hardens it
no_valid_candidate_cases: remain objective/external-search cases, not geometry-complete cases
next_step: design pair objective v4 before launching full revised-geometry detector/evidence validation
```

Pair objective v4 design smoke:

```text
date_checked: 2026-05-18
analyzer: runtime/h001_runtime/analyze_pair_observation_objective_v4.py
design_smoke_out: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4_design_smoke
input_evidence: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pair_observation_evidence_rows.jsonl
input_plan: /tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v3_fixed_v1/pair_observation_plan.jsonl
```

Design rules:

```text
top_survival_commit: removed
top_survival_signal: defer as pair_v4_defer_top_survival_untrusted
incomplete_pair_set: request external candidate search
both_confirmed_candidates: defer as rank/duplicate-goal ambiguity unless one side is disconfirmed
top_commit: allowed only with comparable top evidence and explicit alt disconfirmation
alt_commit: allowed only with alt confirmation and top disconfirmation
```

Design smoke result:

```text
rows: 31
passes_pair_objective_v4_safety_gate: true
passes_pair_objective_v4_full_gate: false
wrong_goal_commit_rate: 0.0
commit_rate: 0.0
top_survival_commit_rate: 0.0
top_survival_blocked_rate: 1.0
uses_gt_for_action: false
```

Runtime interpretation:

```text
v4_rules_fixed_for_next_validation: true
full_gate_failure_reason: old common-view evidence remains too one-sided and no revised-geometry detector evidence has been scored yet
next_step: launch revised geometry detector/evidence validation with fixed objective v4
```

## User Decision Needed

- Whether `habitat-h001` should use a minimal Habitat runtime first or reuse an existing baseline repository.
- Accepted `SPL` drop threshold for first-probe success.
- Whether to prioritize HM3D ObjectNav v2 or HM3D-OVON for the first non-GT semantic candidate backend.
