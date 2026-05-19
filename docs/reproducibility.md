# Reproducibility

이 문서는 H001 실험을 다시 실행하기 위한 데이터, checkpoint, Docker, artifact, evaluation entrypoint를 모은다. 세부 실험 해석은 `hypothesis/CAND-01/H001_uncertainty-reobservation/04_first_experiment.md`와 `08_runtime_integration.md`를 따른다.

## Status

### 사실

- Date checked: 2026-05-19
- Primary hypothesis: `H001_uncertainty-reobservation`
- Runtime root: `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/`
- Data root: `/tmp/research3-data`
- Run artifact root: `/tmp/research3-runs`
- Model root: `/tmp/research3-models`
- Logs: `logs/`
- Host Python은 문서/사전 점검에만 사용한다. Smoke test와 논문 본문용 실험은 Docker 기반으로 실행한다.
- 개인 credential은 repo에 저장하지 않는다.

### 에이전트 추론

재현 정보는 기존 workflow와 job script에 흩어져 있었고, 데이터 다운로드, checkpoint, Docker image, 실험 명령, artifact/evaluation summary가 한 문서로 닫혀 있지는 않았다. 이 문서를 재현 entrypoint로 사용한다.

## Data

### 위치

```text
/tmp/research3-data/
  scene_datasets/hm3d/
  datasets/objectnav/hm3d/v2/
  datasets/ovon/hm3d/
```

Docker 내부 mount 기준:

```text
/data/scene_datasets/hm3d/
/data/datasets/objectnav/hm3d/v2/
/data/datasets/ovon/hm3d/
```

### HM3D / ObjectNav Download

`HM3D` scene assets와 `ObjectNav HM3D v2` episodes는 Matterport credential이 필요하다.

```bash
export MATTERPORT_TOKEN_ID='<token-id>'
export MATTERPORT_TOKEN_SECRET='<token-secret>'

ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-hm3d-restore-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   DATA_ROOT=/tmp/research3-data \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/hm3d_restore.sh"
```

검증:

```bash
python hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_hm3d.py /tmp/research3-data
docker run --rm \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/hm3d-download:20260507 \
  python /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_hm3d.py /data
```

### HM3D-OVON Download

```bash
docker run --rm \
  -v /tmp/research3-data:/data \
  research3/hm3d-download:20260507 \
  bash -lc 'mkdir -p /data/datasets/ovon; \
    curl --fail --location --continue-at - \
      https://huggingface.co/datasets/nyokoyama/hm3d_ovon/resolve/main/hm3d.tar.gz \
      -o /data/datasets/ovon/hm3d.tar.gz; \
    rm -rf /data/datasets/ovon/hm3d; \
    tar -xzf /data/datasets/ovon/hm3d.tar.gz -C /data/datasets/ovon; \
    find /data/datasets/ovon/hm3d -name "._*" -delete'
```

검증:

```bash
docker run --rm \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/hm3d-download:20260507 \
  python /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_ovon.py /data
```

## Checkpoints

### 위치

```text
/tmp/research3-models/
  openvocab/groundingdino/IDEA-Research_grounding-dino-tiny/
  openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
  openvocab/owlvit/google_owlvit-base-patch32/
  vlmaps/lseg/checkpoints/demo_e200.ckpt
```

### GroundingDINO + SAM2

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-openvocab-v3c-setup-${ts}" \
  "cd /home/yoohyun/research3 && \
   LOG_FILE=logs/openvocab-perception-v3c-groundingdino-sam2-${ts}.log \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh"
```

다운로드 대상:

```text
GroundingDINO model id: IDEA-Research/grounding-dino-tiny
GroundingDINO local dir: /tmp/research3-models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny
SAM2 checkpoint URL: https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt
SAM2 local path: /tmp/research3-models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
```

오프라인 검증은 setup script의 `verify_offline_load` 단계가 수행한다.

### OWL-ViT

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-openvocab-owlvit-setup-${ts}" \
  "cd /home/yoohyun/research3 && \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_owlvit_setup.sh"
```

다운로드 대상:

```text
model id: google/owlvit-base-patch32
local dir: /tmp/research3-models/openvocab/owlvit/google_owlvit-base-patch32
```

### VLMaps / LSeg

`calibration_artifact_job.sh`가 `VLMaps` map 생성 시 아래 checkpoint를 사용한다.

```text
container path: /models/vlmaps/lseg/checkpoints/demo_e200.ckpt
host path: /tmp/research3-models/vlmaps/lseg/checkpoints/demo_e200.ckpt
```

기본 job은 `run_vlmaps_map.py --download-checkpoint`를 사용해 필요 시 checkpoint를 받는다.

## Docker

### Host Prerequisites

```text
Docker Engine
NVIDIA Container Toolkit for GPU jobs
tmux for long-running jobs
git checkout of this repo at /home/yoohyun/research3
```

Host Python package 설치는 재현 경로가 아니다. 필요한 Python dependency는 Docker image 안에서 관리한다.

### 사용 중인 Image

```text
research3/habitat-h001:20260508-calib-artifacts
research3/hm3d-download:20260507
research3/openvocab-perception:20260513-v3c-gdino-sam2
research3/openvocab-perception:20260513-owlvit
research3/vlmaps-hm3d:20260508-timmfix
research3/vlmaps-text:20260508
```

### Build / Setup

Habitat runtime image는 artifact job에서 없으면 자동 build한다.

```bash
docker build \
  -f hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/Dockerfile.habitat-h001 \
  -t research3/habitat-h001:20260508-calib-artifacts \
  hypothesis/CAND-01/H001_uncertainty-reobservation/runtime
```

Open-vocabulary detector image는 setup script를 사용한다.

```bash
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_owlvit_setup.sh
```

## Reproduction Commands

### Candidate Artifact / Coverage Gate

`risk_validation_v1`:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-risk-validation-p97-k20-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   MANIFEST=hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_risk_validation_v1.json \
   MANIFEST_SPLIT=risk_validation_v1 \
   SCENE_SPECS_FILE=hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/risk_validation_v1_scenes.txt \
   ARTIFACT_OUT=/tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1 \
   COVERAGE_OUT=/tmp/research3-runs/h001_risk_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity \
   EXPECTED_SCENE_COUNT=10 \
   EXPECTED_QUERY_ROWS=60 \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/v3_fresh_validation_candidate_artifact_coverage.sh"
```

`v3_fresh_validation_v1`:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-v3-fresh-validation-p97-k20-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/v3_fresh_validation_candidate_artifact_coverage.sh"
```

### V4b External Candidate Detector Validation

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-risk-v4b-ext-v2-holdout-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/risk_validation_pair_objective_v4b_external_candidate_v2_holdout.sh"
```

검증:

```bash
cat /tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/frozen_v2_holdout_job_status.json
cat /tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/frozen_v2_holdout_validation_summary.json
```

### Follow-up Planner / Detector Smoke / Evidence Smoke

Planner:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-data:/data:ro \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.plan_external_candidate_followup_observation \
    --data-root /data \
    --external-evidence-v4-rows /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_evidence_v4/external_candidate_evidence_v4_rows.jsonl \
    --candidate-artifact /runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --out-root /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_plan
```

Frame export smoke:

```bash
docker run --rm --gpus all --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-data:/data:ro \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_plan/external_candidate_followup_observation_plan.jsonl \
    --candidate-artifact /runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --out-root /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_frame_smoke \
    --policy ExternalCandidateFollowupObservation \
    --max-decisions 4 \
    --max-candidates-per-decision 6 \
    --yaw-offsets=-30,0,30 \
    --candidate-point-field position
```

Detector smoke:

```bash
docker run --rm --gpus all \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /tmp/research3-runs:/runs \
  -v /tmp/research3-models:/models:ro \
  -w /workspace \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  python -m h001_runtime.detect_postview_groundingdino_sam2 \
    --frames /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_frame_smoke/postview_frames_v2.jsonl \
    --candidate-artifact /runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --groundingdino-dir /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny \
    --sam2-checkpoint /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt \
    --out-root /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_detector_smoke \
    --debug-root /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_detector_smoke/debug_images \
    --device cuda \
    --max-frames 4 \
    --max-headings-per-frame 0 \
    --max-detector-boxes-per-heading 3 \
    --max-masks-per-heading 3 \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 6 \
    --candidate-point-field position \
    --box-threshold 0.10 \
    --text-threshold 0.10 \
    --query-template '{query}' \
    --box-padding-px 4 \
    --association-depth-tolerance-m 1.0 \
    --max-debug-images 40
```

Evidence smoke after follow-up detector smoke:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_external_candidate_followup_evidence \
    --external-evidence-v4-rows /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_evidence_v4/external_candidate_evidence_v4_rows.jsonl \
    --followup-observation-plan /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_plan/external_candidate_followup_observation_plan.jsonl \
    --detector-root /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_detector_smoke \
    --object-node-features /runs/h001_risk_validation_pair_objective_v4b_revised_geometry_v1/association_recovery/candidate_object_node_features_after_second.jsonl \
    --out-root /runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_evidence_smoke
```

### Full Follow-up Detector / Evidence Validation

Full validation은 smoke와 같은 schema를 전체 `risk_validation_v1` follow-up plan에 적용한다. Long-running detector job이므로 tmux로 실행한다.

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-followup-full-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/risk_validation_external_candidate_followup_detector.sh"
```

검증:

```bash
cat /tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_job_status.json
cat /tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_validation_summary.json
```

Expected outputs:

```text
/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_plan/
/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_frames/
/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_detector/
/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_evidence/
/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_validation_summary.json
```

Current launch:

```text
tmux_session: h001-followup-full-20260519-001658
log: logs/risk-validation-external-candidate-followup-detector-20260519-001658.log
status_file: /tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_job_status.json
final_status: completed
completed_at: 2026-05-19 00:19:34 KST
result: detector substrate pass, follow-up evidence safety/full gate fail
```

## Artifact / Evaluation Summary

### 사실

| Artifact | Path | Status | Key Result |
| --- | --- | --- | --- |
| `risk_validation_v1` candidate artifact | `/tmp/research3-runs/h001_risk_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl` | valid | `60` query rows, `1200` candidates, `1062` finite positions |
| `risk_validation_v1` coverage | `/tmp/research3-runs/h001_risk_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json` | pass | `episodes=100`, reachable correct-and-wrong `0.54`, `NoReobserve` wrong-goal `0.47`, `Success Rate 0.19`, `SPL 0.1004` |
| `v3_fresh_validation_v1` candidate artifact | `/tmp/research3-runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl` | valid | `78` query rows, `1560` candidates, `1411` finite positions |
| `v3_fresh_validation_v1` coverage | `/tmp/research3-runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/coverage_sanity/artifact_coverage.json` | pass | `episodes=100`, reachable correct-and-wrong `0.69`, `NoReobserve` wrong-goal `0.61`, `Success Rate 0.26`, `SPL 0.1459` |
| V4 external evidence on `risk_validation_v1` | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_evidence_v4/external_candidate_evidence_v4_summary.json` | pass on current gate | `commit_rate 0.20`, `success_commit_rate 0.20`, wrong-goal commit `0.00`, request identity `0.40`, request expanded retrieval `0.40` |
| Follow-up planner | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_plan` | pass | `28` plan rows, `0` skipped, `18` expanded retrieval, `10` identity confirmation |
| Follow-up detector smoke | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_detector_smoke` | pass as smoke | `4` rows, detector box rate `1.00`, SAM2 mask rate `1.00`, candidate association `0.75` |
| Follow-up evidence smoke | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_evidence_smoke` | safety pass, full gate fail | analyzed `2` observed request branches, safety wrong-goal/no-valid commit `0.00`, strong depth evidence `0.00`, full gate false |
| Full follow-up detector/evidence validation | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_validation_summary.json` | substrate pass, evidence fail | `28` rows, detector box `1.00`, SAM2 mask `1.00`, candidate association `0.714`, commit rate `0.25`, success commit `0.0`, wrong-goal commit `0.25`, no-valid commit `0.25` |
| Full follow-up failure taxonomy | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_failure_modes/external_candidate_followup_failure_mode_summary.json` | complete | `unsafe_no_valid_expanded_retrieval_commit 2`, `safe_identity_defer_rival_supported 4`, `safe_expanded_retrieval_defer_no_valid_target 2`; threshold-only revision rejected |
| Follow-up evidence V2 | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_evidence_v2/external_candidate_followup_evidence_summary.json` | safety pass, utility unresolved | property-conditioned large repeated furniture guard; `wrong_goal_commit_rate 0.0`, no-valid commit `0.0`, request identity `0.25`, success commit `0.0`, full gate false |
| Second-stage identity planner/frame smoke | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_identity_stage2_frame_smoke/summary.json` | pass | V2 request rows `2`, plan rows `4`, skipped `0`, frame rows `4`, rendered headings `46`, selected/rival standoff metadata preserved, `uses_gt_for_action false` |
| Second-stage identity evidence schema smoke | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_identity_stage2_evidence_schema_smoke/external_candidate_second_stage_identity_evidence_summary.json` | schema/safety pass, detector gate fail | analyzed `2` V2 identity request rows, `4` frame rows, `0` association rows; action `defer 2`, wrong-goal/no-valid/visit-position-only commit `0.0`, detector/full gate false as expected without detector evidence |
| Second-stage identity detector/evidence smoke | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_identity_stage2_evidence_smoke/external_candidate_second_stage_identity_evidence_summary.json` | detector substrate/safety pass, full gate fail | detector rows `4`, detector box `1.00`, SAM2 mask `1.00`, candidate association `1.00`, association rows `92`; analyzed `2` V2 request rows, action `defer 2`, wrong-goal/no-valid/visit-position-only commit `0.0`, full gate false because commit/success `0.0` on current no-valid `sofa` diagnostic |
| V2 + second-stage integrated validation | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_v2_stage2_validation/external_candidate_followup_v2_stage2_validation_summary.json` | integrated safety pass, full gate fail | terminal rows `8`, stage2 required/resolved `2/2`, terminal actions `followup_v2 defer 6` + `stage2 defer 2`, integrated detector substrate/safety pass, commit/success `0.0`, wrong-goal/no-valid/visit-position-only commit `0.0`, `first_eval_rerun_blocked true` |
| V2 + second-stage regression rerun | `/tmp/research3-runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_v2_stage2_validation_rerun_v1/external_candidate_followup_v2_stage2_validation_summary.json` | matches previous integrated gate | terminal rows `8`, stage2 required/resolved `2/2`, terminal actions unchanged, integrated safety pass, full gate fail, commit/success `0.0`, `first_eval_rerun_blocked true`, `uses_gt_for_action false` |
| Broader/fresh second-stage feasibility inspection | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/followup_v2_stage2_feasibility/followup_v2_stage2_feasibility_summary.json` | detector rerun supported, first_eval still blocked | label-only inspection; `v3_fresh_validation_v1` has `7` potential follow-up utility rows, `6/6` expanded retrieval rows with correct follow-up set, `1` potential V2 second-stage identity utility branch `external_candidate:12`; `risk_validation_v1` has `0` expanded rows with correct follow-up set; `uses_gt_for_action false`, `uses_gt_for_analysis true` |
| Fresh follow-up V2 + second-stage validation job | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v2_stage2_validation/external_candidate_followup_v2_stage2_validation_summary.json` | completed, safety fail | V2 detector substrate pass; V2 action counts `commit_expanded_candidate 3`, `request_identity 3`, `defer 1`; integrated wrong-goal commit `3/7`, success commit `0/7`; stage2 detector substrate pass on `3` request rows but no commit; `uses_gt_for_action false`; `first_eval` remains blocked |
| Fresh V2 failure taxonomy | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v2_failure_modes/external_candidate_followup_failure_mode_summary.json` | complete | `unsafe_wrong_goal_followup_commit 3`, `strong_depth_evidence_not_instance_safe 3`, `positive_detector_support_not_instance_safe 3`; failures are `plant` small_or_cluttered expanded retrieval rows, so threshold-only revision rejected |
| Follow-up evidence V3 safety repair | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_evidence_v3/external_candidate_followup_evidence_summary.json` | safety pass, utility unresolved | property-conditioned small_or_cluttered guard routes expanded retrieval to identity confirmation; action counts `request_identity 6`, `defer 1`; wrong-goal/no-valid commit `0.0`, commit/success `0.0`; full gate false |
| Fresh V3 second-stage identity validation | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v3_stage2_validation/external_candidate_followup_v2_stage2_validation_summary.json` | completed, safety pass, utility unresolved | request coverage `6/6`; detector box/SAM2 mask/candidate association `1.0`; terminal actions `second_stage_identity_v1_request_further_identity_confirmation 6` and `followup_defer 1`; integrated safety pass, full gate fail, commit/success `0.0`; `first_eval` remains blocked |
| Fresh V3 second-stage utility diagnostic | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/second_stage_utility_diagnostic_v1/second_stage_utility_diagnostic_summary.json` | complete | failure modes: `selected_correct_but_weak_rival_overguarded 2`, `selected_correct_but_view_geometry_insufficient 1`, `correct_candidate_requires_candidate_set_expansion 3`; same-artifact non-GT decision variant `selected_margin_ignore_weak_rival` gives success `2/6`, wrong `0/6`; naive `selected_strong_ignore_rival` gives wrong `3/6`; candidate-set expansion is needed for the remaining `3/6` |
| Second-stage objective V2 same-artifact probe | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v3_stage2_objective_v2_validation/external_candidate_followup_v2_stage2_validation_summary.json` | local gate pass, held-out required | objective `selected_margin_ignore_weak_rival`; second-stage commits `2/6`, success `2/6`, wrong `0/6`; integrated terminal rows `7`, commit/success `2/7`, wrong `0/7`; `validation_scope same_artifact_diagnostic`, so `local_integrated_gate_passed true` but `utility_proof_passed false` and `first_eval_rerun_blocked true` |

### 에이전트 추론

현재 positive signal은 semantic uncertainty를 `commit/defer` threshold가 아니라 `request_identity_confirmation`과 `request_expanded_retrieval` 같은 active observation contract로 바꾸는 방향에서 나온다. 아직 paper claim은 확정하지 않는다. Fresh detector rerun은 V2가 compact object distractor에 취약하다는 새 failure mechanism을 확인했다. V3는 이 failure를 safety repair로 막지만 utility proof는 아니다. `first_eval` replacement rerun과 policy-scale comparison은 V3 second-stage integrated gate 전까지 계속 blocked다.

## Current Blocker

### 사실

- `first_eval` rerun은 아직 blocked다.
- Full follow-up detector/evidence validation job은 완료됐지만 evidence safety/full gate를 통과하지 못했다.
- Label-only broader/fresh feasibility inspection은 `v3_fresh_validation_v1` detector follow-up rerun을 지지하지만, detector evidence gate를 대체하지 않는다.
- `v3_fresh_validation_v1` fresh follow-up V2 + second-stage detector job은 완료됐지만 safety gate를 통과하지 못했다.
- V3 safety repair는 wrong commit을 제거했지만 아직 success utility를 만들지 못했다.
- V3 second-stage identity validation job은 2026-05-19에 완료됐고 detector substrate와 safety는 통과했지만 utility는 만들지 못했다.
- Utility diagnostic 기준으로 다음 구현 후보는 `selected_margin_ignore_weak_rival` objective probe다. 다만 same-artifact 결과이므로 held-out fresh validation 전에는 paper claim으로 쓰지 않는다.
- `selected_margin_ignore_weak_rival` objective probe는 same-artifact local gate를 통과했지만, `validation_scope`가 `same_artifact_diagnostic`이므로 `first_eval`와 policy-scale은 여전히 blocked다.
- HM3D ObjectNav v2 `val`의 36개 scene은 기존 manifest들에 모두 배정되어 있다. 다음 objective-heldout 경로는 `v3_fresh_validation_v1`와 scene-disjoint인 `h001_first_eval_replacement_v1`을 사용한다.

### 에이전트 추론

Full follow-up job은 detector/rendering substrate가 충분한지 확인했지만, V1 `commit_expanded_candidate_after_followup`가 no-valid/wrong-goal commit을 만들었다. V2는 large repeated furniture direct commit을 막아 risk split safety를 복구했지만, fresh split에서는 `plant` small_or_cluttered visible distractor를 wrong-goal로 commit했다. V3는 compact-object expanded retrieval도 identity confirmation으로 넘겨 safety를 복구한다. V3 second-stage는 detector substrate와 safety를 통과했지만 모든 request를 further confirmation으로 남겼다. Objective V2는 high-margin selected-correct / weak-rival case에서 nonzero utility를 만들었지만 same-artifact diagnostic이다. 다음 작업은 fixed Objective V2를 `h001_first_eval_replacement_v1`에 적용하는 scene-disjoint objective-heldout validation이다. Policy-scale comparison은 여전히 blocked다.
