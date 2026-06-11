# Reproducibility

이 문서는 H001 실험을 다시 실행하기 위한 데이터, checkpoint, Docker, artifact, evaluation entrypoint를 모은다. 세부 실험 해석은 `hypothesis/CAND-01/H001_uncertainty-reobservation/04_first_experiment.md`와 `08_runtime_integration.md`를 따른다.

## Status

### 사실

- Date checked: 2026-06-12
- Primary hypothesis: `H001_uncertainty-reobservation`
- Runtime root: `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/`
- Local dataset root: `local_dataset/`
- Data root: `local_dataset/data`
- Run artifact root: `local_dataset/runs`
- Model root: `local_dataset/models`
- Logs: new jobs write under the relevant workflow/hypothesis `logs/` directory, usually `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/`. Root `logs/` is legacy local output and is not a source-of-truth artifact.
- Host Python은 문서/사전 점검에만 사용한다. Smoke test와 논문 본문용 실험은 Docker 기반으로 실행한다.
- 개인 credential은 repo에 저장하지 않는다.
- 다른 컴퓨터 재현을 위한 GitHub source-of-truth는 code, Dockerfile, job script, manifest, workflow 문서, reproducibility 문서다.
- 대용량 dataset, checkpoint, Docker image layer, `local_dataset/runs` artifact는 GitHub source-of-truth가 아니다. 이 문서의 다운로드/빌드/검증 명령으로 복구한다.
- `/tmp/research3-data`, `/tmp/research3-models`, `/tmp/research3-runs`는 기존 Docker command 호환용 path다. 2026-05-27 host symlink는 복구됐고 host `check_hm3d.py /tmp/research3-data`는 통과하지만, 현재 Docker daemon에서는 top-level `/tmp` symlink를 직접 bind source로 쓰면 `mkdir /tmp/research3-data: file exists`로 실패한다. Docker job은 canonical `local_dataset/` path 또는 `readlink -f`로 해석한 path를 사용한다.
- Current static contract gate: `rival_contradiction_region_contamination_multi_case_frame_projection_v1`.
- Current source artifact: `local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_source_v1`.
- Current frame/projection contract verify: `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_contradiction_region_contamination_multi_case_frame_projection_v1.verify.json`.

### 에이전트 추론

재현 정보는 기존 workflow와 job script에 흩어져 있었고, 데이터 다운로드, checkpoint, Docker image, 실험 명령, artifact/evaluation summary가 한 문서로 닫혀 있지는 않았다. 이 문서를 재현 entrypoint로 사용한다.

## Current Reproduction Gate

### 사실

Date checked: 2026-06-12

```bash
jq empty hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_contradiction_region_contamination_multi_case_frame_projection_v1.json
jq empty hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_contradiction_region_contamination_multi_case_frame_projection_v1.verify.json
jq '{status, source_rows, candidate_role_rows, observation_plan_seed_rows, audit_rows, scene_count, query_count, materializer_gate_passed, primary_blocker, next_task}' local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_source_v1/rival_contradiction_region_contamination_multi_case_summary.json
comm -23 <(jq -r '[.scene_key,.query,.candidate_id] | @tsv' local_dataset/runs/h001_rival_contradiction_region_contamination_multi_case_source_v1/rival_contradiction_region_contamination_multi_case_candidate_role_rows.jsonl | sort -u) <(jq -r '. as $r | .candidates[] | [$r.scene_key,$r.query,.candidate_id] | @tsv' local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_candidate_artifact.jsonl | sort -u) | wc -l
```

Expected summary:

```text
contract status: static_verified_multi_case_frame_projection_contract_frozen_terminal_blocked
source/observation-seed rows: 18/72
scene/query coverage: 9/5
geometry candidate coverage: 26/26, missing 0
minimum frame/projection rows: 72/72
minimum projection visible rate: 0.95
minimum projection visible rows: 69
max missing candidate rows: 0
next_task: implement_docker_rival_contradiction_region_contamination_multi_case_frame_projection_smoke
```

## GitHub Portability Check

### 사실

Date checked: 2026-05-23

`git check-ignore -v` 결과, 아래 필수 재현 파일들은 `.gitignore`에 의해 막히지 않는다.

```text
AGENTS.md
README.md
TODO.md
summary.md
docs/reproducibility.md
docs/index.md
hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md
hypothesis/CAND-01/H001_uncertainty-reobservation/08_runtime_integration.md
hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_splits_v1.json
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/Dockerfile.habitat-h001
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_dense_terminal_arbitration.py
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_backend_recall_y9h_chair.sh
```

`.gitignore`가 의도적으로 막는 항목:

```text
local_dataset/
data/
runs/
models/
checkpoints/
*.pdf
*.tar, *.zip, *.npy, *.pt, *.ckpt, *.glb, *.navmesh
*token*, *secret*, *credential*
```

### 에이전트 추론

현재 `.gitignore` 때문에 GitHub에 올라갈 수 없는 필수 재현 정보는 확인되지 않았다. 필수 정보는 문서, manifest, Dockerfile, runtime script, job script에 남아 있고, 대용량 또는 credential성 파일은 로컬 복구 대상으로 분리되어 있다.

주의할 점:

- `runtime/logs/*.log`는 로컬 실행 로그로 취급하고 `.gitignore`에서 제외한다. 재현 필수 정보는 log가 아니라 이 문서와 각 workflow 문서의 command/result summary에 기록한다.
- 새 컴퓨터로 옮길 때는 repo 파일만으로 data/checkpoint/Docker image가 자동 포함되지 않는다. 아래 Data, Checkpoints, Docker 섹션에 따라 별도로 복구한다.

## Ignored Local Asset Policy

### 사실

Date checked: 2026-06-07

Current local footprint:

```text
local_dataset/data:   42G
local_dataset/models: 5.8G
local_dataset/runs:   3.3G
```

`.gitignore` intentionally excludes `local_dataset/`, data, runs, models, checkpoints, paper PDFs, large archives/arrays/model files, and credentials.

Intended compatibility symlinks:

```text
/tmp/research3-data   -> /home/yoohyun/research3/local_dataset/data
/tmp/research3-models -> /home/yoohyun/research3/local_dataset/models
/tmp/research3-runs   -> /home/yoohyun/research3/local_dataset/runs
```

Current compatibility note:

```text
date_checked: 2026-05-27
/tmp/research3-data: host symlink to local_dataset/data; host check_hm3d.py passes
/tmp/research3-models: host symlink to local_dataset/models
/tmp/research3-runs: host symlink to local_dataset/runs
docker_direct_bind_source: false in current daemon for top-level /tmp symlinks
docker_path_rule: use canonical local_dataset paths or readlink -f resolved paths
next_cleanup: full /tmp Docker compatibility requires sudo/root bind-mount cleanup, not only symlink recreation
```

Docker path template:

```bash
DATA_ROOT=$(readlink -f /tmp/research3-data)
MODEL_ROOT=$(readlink -f /tmp/research3-models)
RUN_ROOT=$(readlink -f /tmp/research3-runs)
```

Local dataset migration:

```text
Date: 2026-05-21
Working directory: /home/yoohyun/research3
Command shape: Docker root container moved /tmp/research3-{data,models,runs} into local_dataset/{data,models,runs}, then recreated /tmp compatibility symlinks
Log: hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/local-dataset-migration-20260521-053204.log
Expected files: local_dataset/data, local_dataset/models, local_dataset/runs, /tmp/research3-data symlink, /tmp/research3-models symlink, /tmp/research3-runs symlink
Verification: ls -ld, readlink, du -sh, git check-ignore, Docker check_hm3d.py, Docker /runs mount smoke, Docker /models mount smoke
Status: completed
```

### Google Drive Backup Manifest

Date checked: 2026-06-07

아래 항목은 GitHub에 올리지 않는 local-only asset이다. 순수 재현성만 놓고 보면 대부분 다시 받을 수 있지만, 다른 컴퓨터에서 빠르게 같은 실험 상태를 복구하려면 Drive 보존 우선순위가 높다.

#### 1순위: 데이터셋

```text
local_dataset/data/versioned_data/hm3d-0.2/hm3d/
local_dataset/data/datasets/objectnav/hm3d/v2/objectnav_hm3d_v2/
```

보존 이유:

- `HM3D` scene assets는 현재 약 `42G`이며 Matterport credential, license 동의, 다운로드 시간이 필요하다.
- `ObjectNav HM3D v2` episodes는 현재 약 `250M`으로 작지만 scene assets와 함께 있어야 evaluation harness가 바로 동작한다.
- `local_dataset/data/scene_datasets/hm3d`는 위 `hm3d` 폴더로 향하는 symlink라서 별도 업로드 대상이 아니다. 새 컴퓨터에서는 아래 `Restore from Drive` 절차로 다시 만든다.

#### 2순위: checkpoint / model cache

```text
local_dataset/models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny/
local_dataset/models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
local_dataset/models/vlmaps/lseg/checkpoints/demo_e200.ckpt
local_dataset/models/.cache/clip/ViT-B-32.pt
```

보존 이유:

- `GroundingDINO + SAM2`는 현재 detector evidence path의 핵심이다.
- `VLMaps / LSeg` checkpoint와 `CLIP` cache는 dense backend와 semantic map artifact 재생성 비용을 줄인다.
- 현재 확인된 대용량 model files:

```text
local_dataset/models/vlmaps/lseg/checkpoints/demo_e200.ckpt
local_dataset/models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny/pytorch_model.bin
local_dataset/models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny/model.safetensors
local_dataset/models/.cache/clip/ViT-B-32.pt
local_dataset/models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
```

#### 3순위: 현재 evidence snapshot

```text
local_dataset/runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/
local_dataset/runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/
local_dataset/runs/h001_dense_backend_recall_y9h_chair_v1/
local_dataset/runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/
local_dataset/runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/
local_dataset/runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/
local_dataset/runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/
local_dataset/runs/h001_v3_fresh_validation_policy_spatial_nms_p97_k20_v1/
local_dataset/runs/h001_dense_conflict_recall_gate_v3_fresh_spatial_p97_k20_primary_final_v1/
local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1/
local_dataset/runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1/
local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1/
local_dataset/runs/h001_dense_conflict_generalization_design_v1/
```

보존 이유:

- 재생성은 가능하지만 detector GPU run, `VLMaps` dense re-export, failure taxonomy 분석을 다시 거쳐야 한다.
- 논문 주장으로 아직 확정된 evidence는 아니지만, novelty 판단과 다음 gate 설계의 provenance로 중요하다.
- `local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1/`와 `local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p90_k200_d5_v1/`는 final recall gate를 통과하지 못한 re-export substrate이므로 Drive 1순위가 아니다. 필요하면 기록된 command로 재생성한다.
- `local_dataset/runs/h001_dense_backend_recall_y9h_chair_v1/`는 `recall_probe/*`, `job_status.json`, `verify_map.json`, 및 `embeddings/*`만 현재 보존 대상이다. 대용량 `export/` cache는 2026-06-07에 삭제됐고 필요하면 dense backend recall job으로 재생성한다.

#### Deleted generated intermediate caches

Date checked: 2026-06-07

아래 경로는 과거 backend recall / pool-validity diagnostic의 generated intermediate cache다. 현재 active-observation post-update path에는 직접 필요하지 않고, parent folder의 summary / `jsonl` / `coverage_check` / `job_status` / `recall_probe` / `embeddings` 파일은 남겨 provenance를 유지했다.

```text
local_dataset/runs/h001_expanded_retrieval_deeper_backend_artifact_spatial_nms_p90_k100_d5_v1/scenes/
local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_spatial_nms_p80_k200_d3_v1/scenes/
local_dataset/runs/h001_expanded_retrieval_pool_validity_artifact_components_p80_min1_k200_v1/scenes/
local_dataset/runs/h001_dense_backend_recall_y9h_chair_v1/export/
```

검증 상태:

```text
local_dataset/runs: 3.3G
all four cache paths: deleted
```

복구 기준:

- `scenes/` cache는 해당 backend artifact generation job을 다시 실행해 재생성한다.
- `export/` cache는 `runtime/jobs/dense_backend_recall_y9h_chair.sh`를 다시 실행해 재생성한다.
- 과거 diagnostic summary 확인에는 parent folder에 남은 작은 파일을 우선 사용한다.

#### Deleted failed / superseded run outputs

Date checked: 2026-06-05

아래 경로는 과거 diagnostic 또는 substrate repair 과정에서 생성됐고, 현재 paper-facing path에서는 사용하지 않는 run output으로 분류해 삭제했다. Source-of-truth인 manifest, runtime script, verify file은 삭제하지 않았다.

```text
local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1/
local_dataset/runs/h001_dense_conflict_recall_gate_spatial_nms_p95_k100_d10_v1/
local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p90_k200_d5_v1/
local_dataset/runs/h001_dense_conflict_recall_gate_spatial_nms_p90_k200_d5_v1/
local_dataset/runs/h001_expanded_retrieval_detector_substrate_v1/
local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_smoke_v1/
local_dataset/runs/h001_expanded_retrieval_detector_frames_projection_anchor_smoke_v1/
local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/
local_dataset/runs/h001_semantic_slam_proxy_comparison_v1/
local_dataset/runs/h001_semantic_slam_proxy_comparison_output_evaluation_v1/
local_dataset/runs/h001_semantic_slam_non_dominated_proxy_redesign_v1/
local_dataset/runs/h001_semantic_slam_non_dominated_proxy_output_evaluation_v1/
```

분류 기준:

- `p95_k100_d10`와 `p90_k200_d5` dense re-export artifacts는 final recall gate를 통과하지 못했다.
- 초기 expanded-retrieval detector substrate/projection smoke는 projection-anchor upper/fixed variants로 superseded됐다.
- `discriminative_rival_view_detector_substrate_v1`은 pair role metadata를 보존하지 못해 v2로 superseded됐다.
- 초기 `SemanticSLAM` proxy artifacts는 midpoint dominance 또는 semantic-first shadowing을 드러낸 negative diagnostic이다. 현재 path는 reviewer-defense output evaluation과 `SLAMOnlyRich` underpowered diagnostic 이후 revision contract로 이동했다.

#### 4순위: Docker image export

아래 image들은 Dockerfile/setup script로 재빌드 가능하지만, dependency drift와 setup 시간을 줄이려면 Drive에 `docker save` archive를 보존한다.

```text
research3/habitat-h001:20260508-calib-artifacts
research3/openvocab-perception:20260513-v3c-gdino-sam2
research3/vlmaps-hm3d:20260508-timmfix
research3/vlmaps-text:20260508
```

Archive command:

```bash
docker save \
  research3/habitat-h001:20260508-calib-artifacts \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  research3/vlmaps-hm3d:20260508-timmfix \
  research3/vlmaps-text:20260508 \
  | gzip > local_dataset/research3-docker-images-20260522.tar.gz
```

Drive upload target:

```text
local_dataset/research3-docker-images-20260522.tar.gz
```

#### Optional

```text
literature/**/paper.pdf
*.pdf
```

보존 이유:

- metadata와 link는 repo에 남지만, annotation이 있거나 접근 제한이 있는 PDF는 Drive에 보존한다.

#### Do Not Upload

```text
*token*
*secret*
*credential*
*.pem
*.key
*.netrc
.env
.env.*
```

Credential은 GitHub와 Drive 연구 백업에 넣지 않는다. Matterport, Hugging Face, 기타 provider credential은 각 provider나 password manager에서 별도 관리한다.

### Restore from Drive

새 컴퓨터에서 Drive snapshot을 사용할 때는 repo clone 뒤 아래 형태로 복구한다.

```bash
cd /home/yoohyun/research3
mkdir -p local_dataset/data/versioned_data/hm3d-0.2
mkdir -p local_dataset/data/datasets/objectnav/hm3d/v2
mkdir -p local_dataset/models
mkdir -p local_dataset/runs

# Drive에서 받은 폴더를 위 Google Drive Backup Manifest의 동일한 상대 경로로 배치한다.

mkdir -p local_dataset/data/scene_datasets
ln -sfn ../versioned_data/hm3d-0.2/hm3d local_dataset/data/scene_datasets/hm3d
ln -sfn /home/yoohyun/research3/local_dataset/data /tmp/research3-data
ln -sfn /home/yoohyun/research3/local_dataset/models /tmp/research3-models
ln -sfn /home/yoohyun/research3/local_dataset/runs /tmp/research3-runs
```

Docker image archive를 보존한 경우:

```bash
gunzip -c local_dataset/research3-docker-images-20260522.tar.gz | docker load
```

복구 검증:

```bash
python hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_hm3d.py local_dataset/data

docker run --rm \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/hm3d-download:20260507 \
  python /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_hm3d.py /data

docker run --rm \
  -v /tmp/research3-models:/models:ro \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  bash -lc 'test -d /models/openvocab/groundingdino/IDEA-Research_grounding-dino-tiny && test -f /models/openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt'

find local_dataset/runs -maxdepth 2 -name '*summary.json' | wc -l
```

### Rebuild Without Drive

Drive snapshot 없이도 아래 순서로 재현 가능하다. 단, dataset credential과 GPU/NVIDIA runtime은 별도 준비가 필요하고, detector output은 bitwise 동일성을 보장하지 않는다.

1. Clone repo and create local paths:

```bash
cd /home/yoohyun
git clone git@github.com:Kim-Yoo-Hyun/SSLAM.git research3
cd /home/yoohyun/research3
mkdir -p local_dataset/data local_dataset/models local_dataset/runs
ln -sfn /home/yoohyun/research3/local_dataset/data /tmp/research3-data
ln -sfn /home/yoohyun/research3/local_dataset/models /tmp/research3-models
ln -sfn /home/yoohyun/research3/local_dataset/runs /tmp/research3-runs
```

2. Restore datasets:

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

3. Restore model checkpoints:

```bash
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh
```

4. Build required Docker image if it was not loaded from Drive:

```bash
docker build \
  -f hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/Dockerfile.habitat-h001 \
  -t research3/habitat-h001:20260508-calib-artifacts \
  hypothesis/CAND-01/H001_uncertainty-reobservation/runtime
```

5. Verify before running experiments:

```bash
python hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/check_hm3d.py /tmp/research3-data
nvidia-smi
docker run --rm --gpus all --entrypoint nvidia-smi research3/habitat-h001:20260508-calib-artifacts
```

6. Regenerate artifacts and evaluations using the job scripts in `Reproduction Commands` and the current `TODO.md`. Current blocker is candidate-specific support saturation after the full recovered-row substrate and objective analyzer passed:

```bash
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_deeper_backend_generation_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_evidence_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_objective_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.json
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_pool_validity_branch_v1.json
cat local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1/job_status.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1/goal_validity_confirmation_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_smoke_v1/projection_anchor_smoke_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/job_status.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_substrate_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1/goal_validity_objective_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/full_substrate_job_status.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_full_v1/expanded_retrieval_detector_substrate_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_full_v1/goal_validity_objective_summary.json
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1/goal_validity_ambiguity_resolution_summary.json
cat local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1/job_status.json
cat local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1/job_status.json
```

### 재생성 가능

| Asset | Regeneration path |
| --- | --- |
| HM3D / ObjectNav HM3D v2 | `HM3D / ObjectNav Download` 섹션의 `hm3d_restore.sh`와 `check_hm3d.py` 사용 |
| HM3D-OVON | `HM3D-OVON Download` 섹션의 `curl --continue-at -` 명령과 `check_ovon.py` 사용 |
| `GroundingDINO + SAM2` checkpoints | `GroundingDINO + SAM2` 섹션의 `openvocab_perception_v3c_groundingdino_sam2_setup.sh` 사용 |
| `OWL-ViT` checkpoint | `OWL-ViT` 섹션의 `openvocab_perception_owlvit_setup.sh` 사용. 현재 main path는 아니므로 낮은 우선순위 |
| `VLMaps / LSeg` checkpoint | `VLMaps / LSeg` 섹션의 `run_vlmaps_map.py --download-checkpoint` 경로 사용 |
| Docker images | `Docker` 섹션의 Dockerfile build 또는 setup scripts 사용. 빠른 이전은 `docker save` / `docker load` 사용 |
| Candidate artifacts / detector artifacts / evaluation outputs | `Reproduction Commands`와 `Artifact / Evaluation Summary`의 command, job script, output path를 사용해 재실행 |
| Logs | 재생성 가능. 논문 증거는 full log가 아니라 command, config, output path, summary JSON으로 추적한다 |
| Paper PDFs | 가능하면 `literature/PAPER.md`와 각 paper folder metadata link에서 재다운로드. annotation이 있으면 Drive 보존 |

### 재생성이 불가능하거나 위험한 것

| Asset | Policy |
| --- | --- |
| Credential / token / secret | GitHub와 Drive 연구 백업에 넣지 않는다. Matterport, Hugging Face, 기타 provider에서 별도 관리한다 |
| Exact historical GPU detector outputs | 재실행은 가능하지만 bitwise 동일성은 보장하지 않는다. 논문 evidence로 쓰는 핵심 output은 summary JSON과 함께 Drive snapshot 보존 권장 |
| Manual annotation or hand-edited local-only files | 발견되면 repo 문서 또는 작은 metadata file로 승격한다. 대용량 원본은 Drive에 보존한다 |
| Paywalled or annotated paper PDFs | metadata는 repo에 남기고 PDF/annotation은 개인 Drive에 보존한다 |

### 재생성 명령 요약

Dataset:

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

Models:

```bash
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_owlvit_setup.sh
```

Main Docker images:

```bash
docker build \
  -f hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/Dockerfile.habitat-h001 \
  -t research3/habitat-h001:20260508-calib-artifacts \
  hypothesis/CAND-01/H001_uncertainty-reobservation/runtime

bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/openvocab_perception_v3c_groundingdino_sam2_setup.sh
```

Key dense diagnostic reruns:

```bash
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_backend_recall_y9h_chair.sh

docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.diagnose_dense_terminal_arbitration \
    --evidence-rows /runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/external_candidate_evidence/external_candidate_evidence_rows.jsonl \
    --recall-rows /runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/verification/recall_probe/dense_backend_recall_probe_rows.jsonl \
    --out-root /runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_terminal_arbitration_diagnostic_v1
```

### 에이전트 추론

다른 컴퓨터 이전 시 최소 실전 백업은 다음 조합이다.

```text
1. GitHub repo
2. local_dataset/data
3. local_dataset/models
4. docker save로 만든 main image tar.gz
5. 핵심 local_dataset/runs evidence snapshot
```

시간이 부족하면 `1`, `2`, `3`, main Docker images만 먼저 보존한다. `local_dataset/runs` 전체는 재생성 가능하지만, 현재 novelty 판단의 근거가 되는 key snapshot은 Drive에 남기는 편이 안전하다.

## Data

### 위치

Canonical host path:

```text
local_dataset/data/
  scene_datasets/hm3d/
  datasets/objectnav/hm3d/v2/
  datasets/ovon/hm3d/
```

Compatibility host path:

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

Canonical host path:

```text
local_dataset/models/
  openvocab/groundingdino/IDEA-Research_grounding-dino-tiny/
  openvocab/sam2/sam2.1_hiera_tiny/sam2.1_hiera_tiny.pt
  openvocab/owlvit/google_owlvit-base-patch32/
  vlmaps/lseg/checkpoints/demo_e200.ckpt
```

Compatibility host path:

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
   mkdir -p hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs && \
   LOG_FILE=hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/openvocab-perception-v3c-groundingdino-sam2-${ts}.log \
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

### NVIDIA Runtime Recovery Checklist

Use this checklist when a GPU job fails before container startup. Do not treat this as experiment evidence.

Historical failure on 2026-05-21:

```text
nvidia-smi: Failed to initialize NVML: Driver/library version mismatch
kernel_module: 580.126.09
user_space_library: 580.159.03
docker_gpu_error: open /run/nvidia-persistenced/socket: no such file or directory
```

Recovered status on 2026-05-23:

```text
host_nvidia_smi: passed
driver: 580.159.03
kernel_module: 580.159.03
nvidia_persistenced: active
docker_gpu_smoke: passed with research3/habitat-h001:20260508-calib-artifacts
```

Check commands:

```bash
nvidia-smi
cat /proc/driver/nvidia/version
modinfo nvidia | sed -n '1,20p'
dpkg -l | rg 'nvidia-driver|libnvidia|nvidia-utils|libnvidia-container'
systemctl is-active nvidia-persistenced || true
docker run --rm --gpus all --entrypoint nvidia-smi research3/habitat-h001:20260508-calib-artifacts
```

Recovery rules:

- If host `nvidia-smi` fails, do not launch Docker GPU jobs.
- If kernel module and user-space library versions differ, reboot is the safest recovery path after driver updates.
- Do not unload NVIDIA kernel modules while other containers or desktop processes may be using `/dev/nvidia*`.
- Restarting `nvidia-persistenced` is only meaningful after driver/library versions match.
- Resume the exact recorded tmux command after both host `nvidia-smi` and Docker `--gpus all` succeed.

Dense conflict canonical resume command:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-dense-conflict-artifact-canonical-${ts}" \
  "cd /home/yoohyun/research3 && TS=${ts} DATA_ROOT=/home/yoohyun/research3/local_dataset/data RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs MODEL_ROOT=/home/yoohyun/research3/local_dataset/models bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh"
```

Dense conflict selected-artifact validation command:

```bash
TS=$(date +%Y%m%d-%H%M%S) \
RUNS_ROOT=/home/yoohyun/research3/local_dataset/runs \
bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_validation_from_source.sh
```

Dense conflict secondary-stress validation can be regenerated with the same analyzer after producing secondary recall rows:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.probe_dense_conflict_recall \
    --data-root /data \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_v1.json \
    --manifest-split dense_conflict_v1 \
    --roles secondary_stress \
    --candidate-artifact first_eval_replacement_spatial_p97_k20=/runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --out-root /runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1

docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_dense_conflict_validation \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_v1.json \
    --source-evidence-rows /runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_evidence_v4/external_candidate_second_stage_identity_evidence_rows.jsonl \
    --recall-rows /runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1/dense_conflict_recall_rows.jsonl \
    --recall-summary /runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1/dense_conflict_recall_summary.json \
    --detector-summary /runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_detector/summary.json \
    --out-root /runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1 \
    --source-name first_eval_heldout_local_context_v4 \
    --roles secondary_stress \
    --min-primary-rows 2 \
    --min-rows-with-correct-wrong-positive-support 2 \
    --min-success-commit-rows 2 \
    --min-selected-correct-improvement-rows 2 \
    --min-correct-commit-with-wrong-positive-rows 2
```

Dense conflict broader split design:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.design_dense_conflict_generalization \
    --source v3_fresh_primary=/runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_evidence/external_candidate_second_stage_identity_evidence_rows.jsonl \
    --source first_eval_heldout_secondary=/runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_evidence_v4/external_candidate_second_stage_identity_evidence_rows.jsonl \
    --source risk_validation_identity_smoke=/runs/h001_risk_validation_pair_objective_v4b_external_candidate_detector_v2_holdout_v1/external_candidate_followup_identity_stage2_evidence_smoke/external_candidate_second_stage_identity_evidence_rows.jsonl \
    --out-root /runs/h001_dense_conflict_generalization_design_v1
```

Dense conflict terminal guard design:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.design_dense_conflict_terminal_guard \
    --action-evidence /runs/h001_dense_conflict_generalization_terminal_evidence_v1/action_evidence_rows.jsonl \
    --evaluation-labels /runs/h001_dense_conflict_generalization_terminal_evidence_v1/evaluation_labels.jsonl \
    --out-root /runs/h001_dense_conflict_generalization_terminal_guard_design_v1
```

Dense conflict fixed terminal validation:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.validate_dense_conflict_terminal_arbitration \
    --action-evidence /runs/h001_dense_conflict_generalization_terminal_evidence_v1/action_evidence_rows.jsonl \
    --evaluation-labels /runs/h001_dense_conflict_generalization_terminal_evidence_v1/evaluation_labels.jsonl \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --out-root /runs/h001_dense_conflict_generalization_terminal_validation_v1
```

Dense conflict independent terminal evidence profiles:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.extract_dense_conflict_generalization_evidence \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_v1.json \
    --manifest-split dense_conflict_v1 \
    --candidate-artifact /runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --frame-summary /runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_detector/frame_summary.jsonl \
    --detector-associations /runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_multiview_v3_full_detector/detector_candidate_associations.jsonl \
    --recall-rows /runs/h001_dense_conflict_recall_gate_v3_fresh_spatial_p97_k20_primary_final_v1/dense_conflict_recall_rows.jsonl \
    --out-root /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1 \
    --max-candidates-per-row 6

docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.extract_dense_conflict_generalization_evidence \
    --manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_v1.json \
    --manifest-split dense_conflict_v1 \
    --candidate-artifact /runs/h001_first_eval_replacement_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --frame-summary /runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_detector/frame_summary.jsonl \
    --detector-associations /runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_detector/detector_candidate_associations.jsonl \
    --recall-rows /runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1/dense_conflict_recall_rows.jsonl \
    --out-root /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1 \
    --max-candidates-per-row 6
```

Independent terminal contract:

```bash
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_independent_v1.json >/dev/null
```

Current independent profile summary:

| Artifact | Status | Rows | Associated rows | Notes |
| --- | --- | ---: | ---: | --- |
| `local_dataset/runs/h001_dense_conflict_independent_terminal_evidence_profile_v1` | contract source | 6 | 6 | primary independent source, scenes `7MXmsvcQjpJ`, `DYehNKdT76V`, `HY1NcmCgn3n`, queries `chair`, `plant`; naive `support_score_best` success/wrong `2/4` |
| `local_dataset/runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1` | stress source | 2 | 2 | repeated-object `sofa` stress slice in `y9hTuugGdiq`; naive success/wrong `0/2` |

Dense conflict independent terminal validation:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.validate_dense_conflict_terminal_arbitration \
    --action-evidence /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --evaluation-labels /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --out-root /runs/h001_dense_conflict_independent_terminal_validation_v1 \
    --validation-scope dense_conflict_independent_v1_primary \
    --metric-gate-mode none \
    --min-commit-rows 1 \
    --min-success-commit-rows 1 \
    --max-wrong-goal-commit-rows 0 \
    --max-no-label-commit-rows 0 \
    --paper-claim-status independent_terminal_validation_not_method_claim

docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.validate_dense_conflict_terminal_arbitration \
    --action-evidence /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --evaluation-labels /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --out-root /runs/h001_dense_conflict_secondary_terminal_validation_v1 \
    --validation-scope dense_conflict_independent_v1_secondary_stress \
    --metric-gate-mode none \
    --min-commit-rows 0 \
    --min-success-commit-rows 0 \
    --max-wrong-goal-commit-rows 0 \
    --max-no-label-commit-rows 0 \
    --paper-claim-status secondary_stress_validation_not_method_claim
```

Independent validation result:

| Artifact | Gate | Commit / Success / Wrong | Failure taxonomy |
| --- | --- | --- | --- |
| `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1` | failed | `6 / 2 / 4` | `guard_wrong_commit_depth_consistent_wrong_instance = 4` |
| `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1` | failed | `2 / 0 / 2` | `stress_slice_wrong_commit = 2` |

Both validation outputs have `action_evidence_forbidden_key_count = 0`, `no_label_commit_rows = 0`, and `uses_gt_for_action = false`. The result rejects `strict_depth_consistency_v1` as an independent terminal arbitration rule.

Dense conflict terminal failure diagnosis:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.diagnose_dense_conflict_terminal_failures \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --primary-action-evidence /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --primary-evaluation-labels /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --primary-evaluated-rows /runs/h001_dense_conflict_independent_terminal_validation_v1/terminal_validation_evaluated_rows.jsonl \
    --secondary-action-evidence /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --secondary-evaluation-labels /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --secondary-evaluated-rows /runs/h001_dense_conflict_secondary_terminal_validation_v1/terminal_validation_evaluated_rows.jsonl \
    --out-root /runs/h001_dense_conflict_terminal_failure_diagnostic_v1
```

Failure diagnosis result:

| Artifact | Status | Key result |
| --- | --- | --- |
| `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1/terminal_failure_diagnostic_summary.json` | completed | wrong rows `6`; `repeated_wrong_instance_selected_by_saturated_support 5`; `guard_cannot_arbitrate_between_eligible_correct_and_wrong 1`; support-score saturation on all wrong rows |
| `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1/mechanism_revision_contract.json` | design contract | `rival_identity_confirmation_v1`; treat dense same-category positive support as identity ambiguity; request rival identity confirmation rather than terminal commit |

Dense conflict rival identity diagnostic policy:

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_dense_conflict_rival_identity_policy \
    --guard-config /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_guard_v1.json \
    --primary-action-evidence /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --primary-evaluation-labels /runs/h001_dense_conflict_independent_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --secondary-action-evidence /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/action_evidence_rows.jsonl \
    --secondary-evaluation-labels /runs/h001_dense_conflict_secondary_terminal_evidence_profile_v1/evaluation_labels.jsonl \
    --out-root /runs/h001_dense_conflict_rival_identity_policy_v1
```

Policy diagnostic result:

| Policy | Commit / Success / Wrong | Request rows | Status |
| --- | --- | ---: | --- |
| `rival_identity_confirmation_v1` | `2 / 2 / 0` | 6 | local diagnostic pass |
| `strict_depth_consistency_v1` | `8 / 2 / 6` | 0 | fail |
| `support_margin_only` | `8 / 2 / 6` | 0 | fail |
| `depth_margin_only` | `8 / 2 / 6` | 0 | fail |
| `semantic_top_only` | `8 / 2 / 6` | 0 | fail |
| `defer_all_ambiguous` | `0 / 0 / 0` | 8 | safe but inert |

Artifact: `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1/rival_identity_policy_summary.json`.

Active observation contract:

```bash
jq . hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_observation_v1.json >/dev/null
```

Contract summary:

| Field | Value |
| --- | --- |
| Contract | `rival_identity_observation_v1` |
| Manifest | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_observation_v1.json` |
| Request rows | `6` |
| Planner | `rival_identity_pair_probe_v1` |
| Detector gate | box/SAM2/association `>= 0.80 / 0.80 / 0.50` |
| Post-observation gate | wrong-goal `0`, no-label `0`, newly resolved primary request `>= 1` |

### 사용 중인 Image

```text
research3/habitat-h001:20260508-calib-artifacts
research3/hm3d-download:20260507
research3/openvocab-perception:20260513-v3c-gdino-sam2
research3/openvocab-perception:20260513-owlvit
research3/vlmaps-hm3d:20260508-timmfix
research3/vlmaps-text:20260508
```

### 다른 컴퓨터로 옮길 때 우선순위

필수 또는 권장 image:

| Image | Priority | Reason |
| --- | --- | --- |
| `research3/habitat-h001:20260508-calib-artifacts` | keep / export first | Habitat ObjectNav evaluation harness와 H001 runtime 기본 image |
| `research3/openvocab-perception:20260513-v3c-gdino-sam2` | keep / export first | 현재 `GroundingDINO + SAM2` detector evidence path 핵심 image |
| `research3/vlmaps-hm3d:20260508-timmfix` | keep if regenerating semantic artifacts | `VLMaps` HM3D map/artifact 재생성에 필요 |
| `research3/vlmaps-text:20260508` | keep if regenerating text embeddings | `VLMaps` text embedding 재현에 필요 |

삭제 가능성이 높은 image:

| Image | Reason |
| --- | --- |
| `research3/openvocab-perception:20260513-owlvit` | `OWL-ViT` diagnostic path는 현재 main path에서 제외됨 |
| `research3/hm3d-download:20260507` | dataset download/check용이며 재빌드 가능 |

Docker image를 직접 옮길 때:

```bash
docker save \
  research3/habitat-h001:20260508-calib-artifacts \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  research3/vlmaps-hm3d:20260508-timmfix \
  research3/vlmaps-text:20260508 \
  | gzip > research3-docker-images-20260521.tar.gz
```

새 컴퓨터에서:

```bash
gunzip -c research3-docker-images-20260521.tar.gz | docker load
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

### Expanded Retrieval Deeper Backend Generation

Target-spec and existing-artifact smoke:

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -v /home/yoohyun/research3/local_dataset/data:/data:ro \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_deeper_backend_generation \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_deeper_backend_generation_v1.json \
    --backend-generation-rows /runs/h001_expanded_retrieval_backend_candidate_generation_v1/backend_candidate_generation_rows.jsonl \
    --backend-generation-evaluated-rows /runs/h001_expanded_retrieval_backend_candidate_generation_v1/backend_candidate_generation_evaluated_rows.jsonl \
    --candidate-artifact /runs/h001_v3_fresh_validation_artifacts_spatial_nms_p97_k20_v1/all_scenes_aligned.jsonl \
    --episode-manifest /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_v3_fresh_validation_v1.json \
    --episode-manifest-split v3_fresh_validation_v1 \
    --data-root /data \
    --scene-spec-source /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/v3_fresh_validation_v1_scenes.txt \
    --scene-spec-output /runs/h001_expanded_retrieval_deeper_backend_generation_existing_p97_k20_smoke_v1/deeper_backend_scene_specs.txt \
    --out-root /runs/h001_expanded_retrieval_deeper_backend_generation_existing_p97_k20_smoke_v1
```

Full long-running job:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-deeper-backend-${ts}" \
  "cd /home/yoohyun/research3 && \
   TS=${ts} \
   bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_deeper_backend_generation.sh"
```

Verification:

```bash
cat local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1/job_status.json
cat local_dataset/runs/h001_expanded_retrieval_deeper_backend_artifact_spatial_nms_p90_k100_d5_v1/coverage_check.json
cat local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_summary.json
```

### Expanded Retrieval Goal-Validity Confirmation Handoff

```bash
docker run --rm --ipc=host \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_goal_validity_confirmation \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.json \
    --deeper-generation-rows /runs/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_rows.jsonl \
    --deeper-generation-evaluated-rows /runs/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_evaluated_rows.jsonl \
    --out-root /runs/h001_expanded_retrieval_goal_validity_confirmation_v1
```

Verification:

```bash
cat local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1/goal_validity_confirmation_summary.json
wc -l local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1/*.jsonl
```

### Expanded Retrieval Goal-Validity Objective Analyzer

```bash
docker run --rm --ipc=host \
  --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /home/yoohyun/research3:/workspace:ro \
  -v /home/yoohyun/research3/local_dataset/runs:/runs \
  -w /workspace \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.analyze_expanded_retrieval_goal_validity_evidence \
    --contract /workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_objective_v1.json \
    --plan /runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan.jsonl \
    --detector-associations /runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_associations.jsonl \
    --detector-frame-summary /runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_frame_summary.jsonl \
    --detector-summary /runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_substrate_summary.json \
    --evaluation-labels /runs/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_evaluation_labels.jsonl \
    --out-root /runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1
```

Verification:

```bash
jq '{gate:.gate.objective_analyzer_gate_passed, terminal:.terminal_utility_validation_allowed, full_required:.full_detector_substrate_required, forbidden:.action_evidence_forbidden_key_count, observed_wrong:.observed_candidate_evaluation.evaluation_only_observed_wrong_candidate_count, paper:.paper_claim_allowed}' local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1/goal_validity_objective_summary.json
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
| Held-out Objective V2 validation job | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/objective_v2_heldout_validation_summary.json` | completed, safety pass, utility fail | tmux `h001-first-eval-replacement-objective-v2-heldout-20260519-143805`; `validation_scope heldout_validation`; scene overlap with `v3_fresh_validation_v1` is `0`; integrated terminal rows `5`, commit/success/wrong-goal `0/0/0`; safety gate true, full gate false, `utility_proof_passed false`, `first_eval_rerun_blocked true`, `policy_scale_comparison_blocked true` |
| Candidate-set expansion diagnostic | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/candidate_set_expansion_diagnostic_v1/candidate_set_expansion_summary.json` | completed | `current_followup_set` contains correct `1/5`, while `followup_plan_explicit_set`, `v4_external_set`, `current_plus_v4_external`, and `artifact_semantic_top6/10/20` contain correct `3/5`; failure modes are `detector_association_dropped_planned_correct_candidate 2`, `selected_correct_but_identity_ambiguous 1`, `v4_external_set_missing_correct_candidate 2`; recommendation is to make detector association respect explicit frame `candidate_ids` before broader retrieval/backend expansion |
| Detector explicit-candidate repair | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/detect_postview_groundingdino_sam2.py` | implemented, smoke pass | detector association now uses explicit frame `candidate_ids` / `second_observation_candidate_ids` before semantic tie-band fallback; smoke on branch `external_candidate:13` selects `[2,7,6,5,9,14]` from frame `candidate_ids`, including the two correct sofa candidates that the previous detector association dropped |
| Explicit-candidate held-out validation job | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_v3_stage2_objective_v2_explicit_candidate_validation/external_candidate_followup_v2_stage2_validation_summary.json` | completed, safety pass, utility fail | tmux `h001-followup-explicit-heldout-20260519-150430`; status file `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/followup_v3_stage2_objective_v2_explicit_candidate_job_status.json`; detector used `explicit_candidate_ids` on `15/15` frames, association rows `1008`, association rate `0.8667`; follow-up evidence action `defer 5/5`, correct candidate present `3/5`, integrated safety true, full false, commit/success/wrong `0/0/0`; integrated summary was recovered after adding `heldout_explicit_candidate_diagnostic` validation scope |
| Identity ambiguity diagnostic | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/identity_ambiguity_diagnostic_v1/identity_ambiguity_summary.json` | completed | failure modes: `correct_present_but_not_contrastive_against_wrong_rival 2`, `no_correct_candidate_in_followup_set 2`, `selected_correct_but_supported_wrong_rival 1`; correct candidate present `3/5`, strong correct present `3/5`, best-score candidate correct only `1/5`; threshold-only revision is not supported, next direction is contrastive identity objective/viewpoint or goal-region handling |
| Identity resolution design | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/identity_resolution_design_v1/identity_resolution_design_summary.json` | completed, design only | `best_strong_score` is unsafe with wrong-goal `4/5`; `selected_local_cluster_margin` gives commit/success/wrong `1/1/0` on the same diagnostic split; `oracle_best_strong_correct` ceiling is `3/5`; recommendation is to implement `selected_local_cluster_margin` as a fixed non-GT objective and validate on a separate split before first_eval or policy-scale |
| Follow-up evidence V4 selected local cluster margin | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_evidence_v4_selected_local_cluster_margin/external_candidate_followup_evidence_summary.json` | fixed objective implemented, held-out diagnostic pass | `objective_version v4`; action counts `commit_selected_candidate 1`, `defer 4`; commit/success/wrong/no-valid `1/1/0/0`; detector box `1.0`, SAM2 mask `1.0`, association diagnostic `0.8667`; safety and full follow-up gates pass on this explicit-candidate held-out diagnostic |
| Follow-up evidence V4 separate split validation | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_evidence_v4_selected_local_cluster_margin/external_candidate_followup_evidence_summary.json` | safety pass, utility fail | `v3_fresh_validation_v1`; action counts `request_identity 6`, `defer 1`; commit/success/wrong/no-valid `0/0/0/0`; detector box `1.0`, SAM2 mask `1.0`, association diagnostic `0.359`; safety gate passes but full gate fails; first_eval and policy-scale remain blocked |
| V4 request-identity bottleneck diagnostic | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/v4_request_identity_bottleneck_diagnostic_v1/v4_request_identity_bottleneck_summary.json` | completed | request rows `6/7`; `selected_direct_first_stage` is unsafe with commit/success/wrong `6/3/3`; existing `stage2_objective_v2` gives commit/success/wrong `2/2/0`; failure split is `2` resolved by second-stage identity, `1` needs better viewpoint geometry, `3` selected-wrong `plant` rows need broader retrieval/candidate-viewpoint revision, and `1` all-correct `chair` defer row needs duplicate-goal/category-region contract consideration |
| V4 + second-stage identity V2 terminal diagnostic | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v4_stage2_objective_v2_terminal_diagnostic/external_candidate_followup_v4_stage2_terminal_summary.json` | local integrated gate pass, rerun blocked | terminal rows `7`, stage2 required/resolved `6/6`, terminal source counts `followup_v4 1`, `second_stage_identity 6`; commit/success/wrong/no-valid `2/2/0/0`, visit-position-only commits `0`; integrated stage2 coverage, detector substrate, safety, and full gates pass; `validation_scope v4_fixed_terminal_diagnostic` keeps `utility_proof_passed false`, `first_eval_rerun_blocked true`, `policy_scale_comparison_blocked true` |
| Selected-wrong `plant` recovery design | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/selected_wrong_plant_recovery_design_v1/selected_wrong_recovery_summary.json` | completed, design supports planner revision | selected-wrong rows `3`; follow-up set contains correct `3/3`; current stage2 context contains correct `3/3`; current stage2 targets correct `0/3`; `selected_plus_semantic_neighbor_1` targets correct `3/3` with feasible `standoff_navmesh` viewpoints; recommendation is `candidate_viewpoint_revision_first`, not broader retrieval for these rows |
| Semantic-neighbor second-stage planner/frame smoke | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_identity_stage2_semantic_neighbor_frame_smoke/summary.json` | pass | planner mode `semantic_neighbor`; plan rows `15`, skipped `0`, role counts `selected_standoff 6`, `semantic_neighbor_1_standoff 6`, `rival_1_standoff 3`; frame rows `15/15`, rendered headings `182`, all frame candidate sets use `explicit_candidate_ids`; selected-wrong `plant` semantic-neighbor target is `vlmaps:export:plant:spatial_nms:1` |
| Semantic-neighbor detector-backed validation | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v4_stage2_semantic_neighbor_gpu_rerun_v1/external_candidate_followup_v4_stage2_semantic_neighbor_summary.json` | completed, diagnostic local gate pass, utility proof blocked | first GPU attempt `h001-v4-sem-neighbor-stage2-20260519-232655` failed at `second_stage_detector` with CUDA OOM; reduced CPU retry completed with detector rows `15`, candidate association `0.80`, commit/success/wrong/no-valid `2/2/0/0`; full GPU rerun `h001-v4-sem-neighbor-stage2-gpu-20260520-190626` completed with detector rows `15`, candidate association `1.00`, stage2 request coverage `6/6`, integrated commit/success/wrong/no-valid `2/2/0/0`, local integrated gate passed; `validation_scope v4_semantic_neighbor_diagnostic` keeps `utility_proof_passed false`, `first_eval_rerun_blocked true`, and policy-scale blocked |
| Semantic-neighbor multiview focused validation | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v4_stage2_semantic_neighbor_multiview_selected_wrong_v1/external_candidate_followup_v4_stage2_semantic_neighbor_summary.json` | completed, evidence acquisition improved, objective unresolved | planner now supports `--semantic-neighbor-viewpoints-per-target`; focused plan smoke for selected-wrong `plant` branches `external_candidate:14,17,21` produced `24` rows with `18` semantic-neighbor standoff rows and `0` skipped; frame smoke exported `24/24` rows and `312` headings; detector rows `24`, candidate association `0.875`, detector box/SAM2 mask `1.0`; correct semantic-neighbor `spatial_nms:1` improved to `S_ext ~0.783`, strong depth `true`, own strict association `13`, but wrong selected/rival candidates remain strong at `S_ext ~0.786`, so objective V2 still requests further confirmation `3/3` |
| Semantic-prior strong-tie arbitration V3 focused diagnostic | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v4_stage2_semantic_neighbor_multiview_selected_wrong_v1_objective_v3/external_candidate_followup_v4_stage2_semantic_neighbor_summary.json` | focused diagnostic pass, utility proof blocked | `analyze_external_candidate_second_stage_identity_evidence.py --objective-version v3`; focused selected-wrong multiview rows commit the semantic-neighbor candidate on `3/3` branches with success/wrong/no-valid `3/0/0`; source selected is wrong `spatial_nms:0`, committed candidate is correct `spatial_nms:1`; integrated terminal commit/success/wrong/no-valid `3/3/0/0`, but stage2 coverage is only `3/6`, so integrated full gate and utility proof remain false |
| Full V4 semantic-neighbor multiview V3 coverage validation | `/tmp/research3-runs/h001_v3_fresh_validation_pair_objective_v4b_external_candidate_detector_v1/external_candidate_followup_v4_stage2_semantic_neighbor_multiview_v3_full/external_candidate_followup_v4_stage2_semantic_neighbor_summary.json` | local integrated gate pass, utility proof blocked | tmux `h001-v4-sem-neighbor-v3-full-20260521-004207`; uses `SECOND_STAGE_OBJECTIVE_VERSION=v3`, `SEMANTIC_NEIGHBOR_VIEWPOINTS_PER_TARGET=6`, `MAX_VIEWPOINTS_PER_TARGET=1`; request rows `6`, plan/frame rows `45`, rendered headings `523`, detector association `0.80`, detector box/SAM2 mask `1.0`; integrated terminal commit/success/wrong/no-valid `5/5/0/0`, stage2 coverage `6/6`, local integrated full gate true; `validation_scope v4_semantic_neighbor_diagnostic` keeps `utility_proof_passed false` and first_eval/policy-scale blocked |
| Scene-disjoint V3 held-out validation contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/08_runtime_integration.md` | implemented, held-out utility fail | Current held-out V4 artifact had no `request_identity_confirmation` rows: `commit_selected_candidate 1`, `defer 4`; V5 routes only `defer_identity_selected_local_rival_stronger` sofa rows (`2`, correct candidate present) to second-stage V3 and keeps no-correct outside-near-tie chair rows deferred |
| Held-out follow-up V5 local-rival route | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_evidence_v5_local_rival_route/external_candidate_followup_evidence_summary.json` | safety pass, route implemented | action counts `commit_selected 1`, `request_identity 2`, `defer 2`; reason counts `request_identity_confirmation_after_local_rival_stronger 2`, `defer_identity_selected_outside_rival_near_tie 2`, `commit_selected_identity_confirmed_local_cluster_margin_after_followup 1`; detector box/SAM2 mask `1.0`, association `0.8667`, `uses_gt_for_action false` |
| Held-out V5 + second-stage V3 validation | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_v5_stage2_semantic_neighbor_v3_heldout/external_candidate_followup_v5_stage2_semantic_neighbor_summary.json` | safety pass, utility fail | tmux `h001-heldout-v5-v3-20260521-010455` reached detector/evidence but failed integrated summary once due invalid scope label; recovered with `validation_scope heldout_validation`; stage2 request coverage `2/2`, detector rows `16`, detector box/SAM2 mask `1.0`, candidate association `0.25`; stage2 actions `request_further_identity_confirmation 2`, terminal commit/success/wrong/no-valid `1/1/0/0`; stricter integrated gate requires stage2 full, so full gate and utility proof are false |
| Held-out sofa second-stage failure diagnostic | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/heldout_sofa_stage2_failure_diagnostic_v1/heldout_sofa_stage2_failure_summary.json` | completed | both held-out sofa rows share failure modes `correct_target_not_strong_in_own_view`, `viewpoint_geometry_correct_target_out_of_fov_or_behind`, `target_selection_left_stronger_correct_candidate_as_context`, and `wrong_selected_or_rival_remains_strong`; targeted correct `sofa:spatial_nms:5` has own association `0`, own visible `0`, projection counts `out_of_fov 47`, `behind_camera 18`; stronger correct context `sofa:spatial_nms:9` remains untargeted |
| Held-out local-rival expanded grounded geometry smoke | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/stage2_projection_geometry_v5_local_rival_expanded_grounded_check/stage2_projection_geometry_summary.json` | projection substrate pass, detector validation pending | added `local_rival_expanded` target selection, `grounded_position` candidate point mode, and `check_stage2_projection_geometry.py`; baseline V5/V3 position projection visible rate `4/16 = 0.25` with semantic-neighbor target out-of-FOV `12/12`; expanded grounded plan has visible rate `20/22 = 0.909`, role counts `selected 2`, `semantic_neighbor 6`, `rival 2`, `local_context_1 6`, `local_context_2 6`, and targets previously untargeted stronger correct sofa context `spatial_nms:9`; detector-backed utility remains unverified |
| Held-out local-rival expanded grounded detector validation | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_v5_stage2_local_rival_expanded_grounded_v1/external_candidate_followup_v5_stage2_local_rival_expanded_grounded_summary.json` | detector substrate pass, utility fail | tmux `h001-heldout-local-rival-grounded-retry-20260521-015542`; plan/frame rows `22`, rendered headings `238`, detector box/SAM2/candidate association rates `1.0`, stage2 request coverage `2/2`; stage2 action `request_further_identity_confirmation 2`, terminal commit/success/wrong/no-valid `1/1/0/0`; integrated safety true, full gate false, utility proof false |
| Held-out local-rival grounded result diagnostic | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/local_rival_grounded_result_diagnostic_v1/local_rival_grounded_diagnostic_summary.json` | completed | detector substrate recovered but terminal arbitration remains blocked; failure modes `correct_evidence_recovered 2`, `correct_local_context_tied_but_not_arbitrated 2`, `score_saturation_multiple_strong_candidates 2`, `selected_wrong_remains_strong 2`, `wrong_rivals_remain_strong 2`, `semantic_arbitration_semantic_neighbor_strict_advantage_too_small 2`, `terminal_objective_remains_defer 2` |
| Local-context arbitration design | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/local_context_arbitration_design_v1/local_context_arbitration_design_summary.json` | completed, design only | added `design_local_context_arbitration.py`; current V3 commits `0/2`; selected-direct strong own-view would commit wrong-goal `2/2`; non-GT `local_context_unique_own_view_advantage` commits `2/2` with success/wrong/no-valid `2/0/0`; uses GT only for analysis, so next step is fixed objective diagnostic replay before first_eval or policy-scale |
| Local-context arbitration objective V4 held-out replay | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_v5_stage2_local_context_v4_heldout/external_candidate_followup_v5_stage2_local_context_v4_summary.json` | local held-out gate pass, broader validation still needed | added `analyze_external_candidate_second_stage_identity_evidence.py --objective-version v4`; stage2 evidence output `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_identity_stage2_v5_local_rival_expanded_grounded_evidence_v4`; stage2 commits `2/2` with success/wrong/no-valid `2/0/0`, integrated terminal commit/success/wrong/no-valid `3/3/0/0`, detector substrate and integrated safety/full gates pass; scope is only local held-out repeated-object rows, so no-correct chair backend recall remains unresolved |
| Broader retrieval/backend design for no-correct rows | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/broader_retrieval_backend_design_v1/broader_retrieval_backend_design_summary.json` | completed | two held-out chair rows have no correct candidate in current follow-up set, V4 external set, or `artifact_semantic_top20`; failure modes `backend_recall_failure_not_detector_association 2`, `current_artifact_top20_missing_correct 2`; recommendation is a dense non-GT backend recall probe before detector observation, not forced identity confirmation |
| Available-artifact dense backend recall probe | `/tmp/research3-runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/dense_backend_recall_probe_available_artifacts_v1/dense_backend_recall_probe_summary.json` | completed, recall fail | added `probe_dense_backend_recall.py`; tested materialized non-GT artifacts `replacement_spatial_p97_k20`, `first_eval_spatial_p97_k20`, `first_eval_spatial_k20`, `first_eval_random256_k20`, and `first_eval_random256_k10`; all have recall@K `0.0` on the two no-correct chair rows, so existing artifacts cannot close the backend recall failure |
| Dense VLMaps source-map re-export recall job | `/tmp/research3-runs/h001_dense_backend_recall_y9h_chair_v1/recall_probe/dense_backend_recall_probe_summary.json` | completed, recall recovered | tmux `h001-dense-backend-y9h-chair-20260521-030146`; log `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/dense-backend-recall-y9h-chair-20260521-030146.log`; `job_status.json` is `completed`; all four dense variants recover `2/2` no-correct chair rows with recall@5 `1.0`; selected first fixed backend revision is `spatial_nms_p95_k100_d10` because it matches recovery with `100` candidates instead of `200`, reducing detector observation cost |
| Fixed dense backend candidate artifact | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/all_scenes_aligned.jsonl` | completed, Docker verified | metadata `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/artifact_metadata.json`; source variant `spatial_nms_p95_k100_d10`; rows `1`, candidates `100`; Docker verification summary `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/verification/recall_probe/dense_backend_recall_probe_summary.json` recovers `2/2` no-correct chair rows with recall@5 `1.0` and `uses_gt_for_action false`; next step is detector observation |
| Fixed dense backend detector observation | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_v1/external_candidate_detector_validation_summary.json` | completed, association fail | plan smoke `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_v1/plan_smoke` triggered `2/2` held-out chair rows, plan rows `12`, skipped `0`, `uses_gt_for_action false`; tmux `h001-dense-fixed-detector-y9h-chair-20260521-031417`; detector rows `12`, rendered headings `36`, detector box/SAM2 mask rates `1.0`, candidate association rate `0.0`; evidence actions `external_evidence_v1_defer 2`; safety gate passed, full gate failed; next step is association/depth geometry diagnosis before terminal arbitration |
| Fixed dense backend detector association diagnostic | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_v1/detector_association_diagnostic_v1/detector_association_diagnostic_summary.json` | completed | added `diagnose_detector_association.py`; Docker `py_compile` passed; diagnostic rows `36`, association rate `0.0`, visible rows `20`, inside-mask rows `12`, visible-inside-mask-unassociated rows `12`, depth mismatch rows `18`, median depth error `3.94m`; dominant failure `visible_inside_mask_but_depth_or_association_rejects`; next revision should inspect point height, depth tolerance, and viewpoint geometry before terminal arbitration |
| Fixed dense backend association repair design | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_v1/dense_association_repair_design_v1/dense_association_repair_design_summary.json` | completed, repair selected | added `design_dense_association_repair.py`; Docker `py_compile` passed; compared `current_mask_depth_1_0`, `mask_depth_1_5`, `mask_depth_2_0`, `mask_depth_2_5`, `mask_depth_3_0`, `mask_no_depth`, and `box_no_depth`; selected `mask_depth_2_0` because it is the smallest tested depth tolerance that recovers both held-out chair episodes, passes association-rate gate `0.20`, and supports no wrong candidate under GT analysis labels; `uses_gt_for_action false`, `uses_gt_for_analysis true` |
| Fixed dense backend depth2 association repair job | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/external_candidate_detector_validation_summary.json` | completed, substrate pass | tmux `h001-dense-fixed-detector-depth2-y9h-chair-20260521-034718`; uses `ASSOCIATION_DEPTH_TOLERANCE_M=2.0`; detector box/SAM2 mask rates `1.0`, candidate association rate `0.5`, detector substrate gate pass; evidence commits `2/2`, but built-in safety/full gates fail because dense candidate correctness labels are not attached to branch rows |
| Fixed dense backend depth2 commit evaluation | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_repair_commit_evaluation_v1/dense_repair_commit_evaluation_summary.json` | completed, local diagnostic positive | added `evaluate_dense_repair_commit.py`; labels selected candidates against recall-probe GT analysis labels only after action selection; action commits `2/2`, success commits `2/2`, wrong-goal commits `0/2`; `uses_gt_for_action false`, `uses_gt_for_analysis true`; not a policy-scale claim |
| Fixed dense backend terminal diagnostic contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md` | scope fixed | section `Fixed Dense Backend Terminal Diagnostic Contract`; allows only local two-row chair diagnostic interpretation; blocks `first_eval`, policy-scale, and cross-scene/category `association_depth_tolerance_m=2.0` claims until evaluation-label plumbing, independent validation, simpler-alternative comparison, and safety/utility gates pass |
| Depth2 generalization decision | `hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md` | do not generalize yet | local chair diagnostic supports `mask_depth_2_0`, but broader `/tmp/research3-runs/h001_first_eval_replacement_detector_v3c_association_variants_v1/summary.json` does not: `mask_depth_2p0` association `0.49`, associated-count AUC `0.520`, selected-correct delta `-0.21`, new wrong-goals `6`; `box_or_mask_depth_2p0` association `0.56`, AUC `0.549`, delta `-0.14`, new wrong-goals `4`; both detector calibration gates fail |
| Dense terminal arbitration diagnostic | `/tmp/research3-runs/h001_dense_backend_fixed_spatial_nms_p95_k100_d10_y9h_chair_detector_depth2_v1/dense_terminal_arbitration_diagnostic_v1/dense_terminal_arbitration_summary.json` | completed, local promising but not utility proof | added `diagnose_dense_terminal_arbitration.py`; Docker `py_compile` and diagnostic run passed; commits `2/2`, action recompute match `1.0`, selected post-hoc correct `1.0`, first external post-hoc correct `1.0`, selected-correct improvement over first `0.0`, wrong positive-support row rate `0.0`, same-goal evidence selection rate `1.0`; next validation should target wrong/ambiguous positive-support candidates |
| Independent dense conflict validation manifest / recall gate | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_v1.json` | implemented, Docker verified | added `build_dense_conflict_manifest.py` and `probe_dense_conflict_recall.py`; manifest verify output `manifests/h001_dense_conflict_v1.verify.json` has `ok true`, `rows 8`, `unique_episode_keys 8`; final selected-artifact primary recall output `local_dataset/runs/h001_dense_conflict_recall_gate_v3_fresh_spatial_p97_k20_primary_final_v1` passes with `6/6` correct candidates and recall@20 `1.0` |
| Dense conflict `spatial_nms_p95_k100_d10` artifact job | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh` | completed, recall gate fail | canonical relaunch `h001-dense-conflict-artifact-canonical-20260523-140845`; artifact generation completed with `24` rows, `2400` candidates, and `1451` finite-position candidates; final recall gate failed with primary rows with correct `3/6`, recall@20 `0.5`, required rows with correct `4/6`; detector job remains blocked for this substrate |
| Dense conflict `spatial_nms_p90_k200_d5` artifact job | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh` | completed, recall gate fail | tmux `h001-dense-conflict-artifact-p90-k200-d5-20260523-150036`; artifact generation completed with `24` rows, `4800` candidates, and `4241` finite-position candidates; final recall gate failed with primary rows with correct `3/6`, recall@20 `0.5`, required rows with correct `4/6`; detector job remains blocked for this substrate |
| Dense conflict selected-artifact detector/association validation | `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1/dense_terminal_arbitration_summary.json` | primary diagnostic pass | added `analyze_dense_conflict_validation.py` and `runtime/jobs/dense_conflict_validation_from_source.sh`; materializes existing `v3_fresh` second-stage detector/association evidence; primary rows `6`, detector box `1.0`, SAM2 mask `1.0`, candidate association `0.8`, correct+wrong positive support `6/6`, commit/success/wrong/no-valid `5/5/0/0`, selected-correct improvement over source-selected `3`, `uses_gt_for_action false`; detector/association blocked is lifted only for selected `v3_fresh_spatial_p97_k20` diagnostic substrate |
| Dense conflict secondary-stress validation | `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1/dense_terminal_arbitration_summary.json` | secondary diagnostic pass | held-out `sofa` local-context stress rows; recall output `local_dataset/runs/h001_dense_conflict_recall_gate_first_eval_replacement_spatial_p97_k20_secondary_v1` has rows with correct `2/2` and recall@20 `1.0`; detector box/SAM2/candidate association `1.0/1.0/1.0`, correct+wrong positive support `2/2`, commit/success/wrong/no-valid `2/2/0/0`, selected-correct improvement over source-selected `2`, `uses_gt_for_action false`; too small for paper-ready generalization |
| Dense conflict broader split design | `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json` | design complete | added `design_dense_conflict_generalization.py`; current evidence summary has `10` rows, `5` scenes, `3` queries, `8` correct+wrong positive-support rows, `5` source-selected-wrong rows, success commits `7`, wrong-goal commits `0`; recommends `scene_disjoint_first_eval_style`; next manifest contract is `dense_conflict_generalization_v1` with at least `20` rows, `5` scenes, `3` queries, `6` selected-wrong rows, and `12` correct+wrong positive-support rows |
| Dense conflict generalization manifest / recall gate | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_generalization_v1.json` and `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1/dense_conflict_recall_summary.json` | frozen, recall pass | added `build_dense_conflict_generalization_manifest.py`; manifest has `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`, `uses_gt_for_action false`; recall gate on `first_eval_replacement_spatial_nms_p97_k20` has rows with correct `20/20`, recall@20 `1.0`, recall@5 `0.85`, first correct rank `1-9`, detector job allowed |
| Dense conflict generalization detector substrate job | `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1/generalization_detector_substrate_summary.json` | completed, substrate pass | added `runtime/jobs/dense_conflict_generalization_detector_substrate.sh`; tmux `h001-dense-conflict-generalization-detector-20260523-170533`; log `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/dense-conflict-generalization-detector-substrate-20260523-170533.log`; detector rows `20`, frame rows `20`, rendered headings `125`, detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`, associated rows `7`, substrate gate passed, `uses_gt_for_action false`; policy diagnostic on this hard split has success `0.2` and wrong-goal visit `0.8` |
| Dense conflict generalization terminal evidence extraction | `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1/terminal_arbitration_design_summary.json` | design gate pass, terminal v0 fail | added `extract_dense_conflict_generalization_evidence.py`; outputs `action_evidence_rows.jsonl`, `evaluation_labels.jsonl`, and `terminal_policy_diagnostic_rows.jsonl`; action evidence rows `20`, evaluation label rows `55`, associated/unassociated rows `7/13`, forbidden action key count `0`, `uses_gt_for_action false`; `proposed_conservative_v0` commits `7/20` with `3` success and `4` wrong-goal commits, so terminal arbitration validation remains blocked pending safer guard design |
| Dense conflict generalization terminal guard design | `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1/terminal_guard_design_summary.json` | design gate pass, validation candidate | added `design_dense_conflict_terminal_guard.py`; selected `strict_depth_consistency_v1` with `max_depth_error_m 0.33`, `min_associated_heading_count 2`, `min_mask_hit_count 2`, `max_semantic_rank 5`; same diagnostic split commit/success/wrong `3/3/0`, associated commit rate `3/7`, `uses_gt_for_action false`; this is same-split guard design and not a paper-facing method claim |
| Dense conflict generalization fixed terminal validation | `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1/terminal_validation_summary.json` | same-split validation pass | added `manifests/h001_dense_conflict_terminal_guard_v1.json` and `validate_dense_conflict_terminal_arbitration.py`; action evidence forbidden key count `0`, stable metric match design `true`, local fixed-rule validation pass `true`, rows `20`, associated rows `7`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`, `uses_gt_for_action false`; paper claim status remains `same_split_fixed_rule_validation_not_method_claim` |
| Dense conflict independent terminal validation | `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1/terminal_validation_summary.json` and `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1/terminal_validation_summary.json` | independent validation fail | primary commit/success/wrong `6/2/4`, secondary stress `2/0/2`, forbidden action key count `0`, no-label commits `0`, `uses_gt_for_action false`; rejects `strict_depth_consistency_v1` as independent terminal arbitration rule |
| Dense conflict terminal failure diagnosis | `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1/terminal_failure_diagnostic_summary.json` | mechanism fixed, revision contract defined | added `diagnose_dense_conflict_terminal_failures.py`; wrong rows `6`, `repeated_wrong_instance_selected_by_saturated_support 5`, `guard_cannot_arbitrate_between_eligible_correct_and_wrong 1`; `mechanism_revision_contract.json` defines `rival_identity_confirmation_v1` as design-only next diagnostic policy |
| Dense conflict rival identity policy diagnostic | `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1/rival_identity_policy_summary.json` | local diagnostic pass | added `analyze_dense_conflict_rival_identity_policy.py`; `rival_identity_confirmation_v1` commit/success/wrong `2/2/0`, request rows `6`, diagnostic pass `true`; support/depth/semantic-top simpler alternatives keep `6` wrong-goal commits, while `defer_all_ambiguous` has `0` success commits; paper claim remains blocked until actual requested observations are evaluated |
| Dense conflict rival identity observation contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_observation_v1.json` | frozen, plan gate passed | freezes six `request_rival_identity_confirmation` rows; planner `rival_identity_pair_probe_v1`; detector substrate gate box/SAM2/association `0.80/0.80/0.50`; post-observation gate requires wrong-goal `0`, no-label `0`, newly resolved primary request `>=1`, secondary stress wrong-goal `0`; paper claim remains blocked |
| Dense conflict rival identity observation plan smoke | `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1/rival_identity_observation_plan_summary.json` | Docker plan smoke pass | added `plan_rival_identity_observation.py`; output plan rows `19`, request rows `6`, planned request rows `6`, skipped rows `0`, action evidence forbidden key count `0`, `uses_gt_for_action false`; also writes `rival_identity_candidate_artifact.jsonl` with `3` artifact rows and `10` candidates |
| Dense conflict rival identity frame export smoke | `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1/summary.json` | Docker frame smoke pass | renderer `export_postview_frames_v2.py`; rows requested/exported `19/19`, rendered headings `142`, RGB/depth files `142/142`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity pass, `uses_gt_for_action false`; output alias `rival_identity_frame_summary.jsonl`; Habitat EGL render required Docker `--gpus all` |
| Dense conflict rival identity detector substrate job | `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1/rival_identity_detector_substrate_summary.json` | completed, substrate gate pass | tmux `h001-rival-identity-detector-20260526-012036`; log `runtime/logs/rival-identity-detector-substrate-20260526-012036.log`; detector rows `19`, detector box `0.8421`, SAM2 mask `0.8421`, candidate association `0.6316`, rows with association `12/19`, associated candidate heading count `57`, `uses_gt_for_action false`; diagnostic analyzer result recorded below |
| Dense conflict rival identity post-observation contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md` and `runtime/workflow-20260521-dense-conflict.md` | frozen, analyzer run | freezes action/evaluation separation, label join key `(episode_key, candidate_id)`, own-view versus cross-view detector evidence fields, and fixed commit/defer rule; analyzer result is recorded below |
| Dense conflict rival identity post-observation analyzer | `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1/rival_identity_observation_validation_summary.json` | Docker diagnostic gate pass | added `analyze_rival_identity_post_observation.py`; evidence rows `19`, decision rows `6`, commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, action evidence forbidden key count `0`, `uses_gt_for_action false`; failure taxonomy `none 1`, `post_observation_no_candidate_support 3`, `post_observation_cross_view_aliasing 2`; paper claim remains blocked because fresh-source validation later failed |
| Dense conflict rival identity fresh source design | `local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1/rival_identity_policy_summary.json` | source criteria fixed | selects `rival_identity_generalization_v1` from frozen `dense_conflict_generalization_v1` primary action evidence; parent rows `20`, request rows `6`, request scenes `3`, request queries `2`; excludes prior diagnostic scenes `DYehNKdT76V`, `7MXmsvcQjpJ`, `y9hTuugGdiq`; label-based selection is forbidden |
| Dense conflict rival identity fresh source manifest | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_generalization_v1.json` and `local_dataset/runs/h001_rival_identity_generalization_source_v1/source_summary.json` | frozen, source gate pass | added `build_rival_identity_generalization_manifest.py`; Docker `py_compile` and source freeze run passed; verify `manifests/h001_rival_identity_generalization_v1.verify.json` reports `ok true`; request rows `6`, request scenes `3`, request queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, `uses_gt_for_action false` |
| Dense conflict rival identity fresh plan smoke | `local_dataset/runs/h001_rival_identity_generalization_plan_v1/rival_identity_observation_plan_summary.json` | Docker plan smoke pass | reused `plan_rival_identity_observation.py` on frozen fresh manifest; request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, `uses_gt_for_action false`; downstream frame, detector, and analyzer results are recorded below |
| Dense conflict rival identity fresh frame smoke | `local_dataset/runs/h001_rival_identity_generalization_frames_v1/summary.json` | Docker frame smoke pass | patched `export_postview_frames_v2.py` to write `rival_identity_frame_summary.jsonl` alias for rival-identity rows; rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity pass, `uses_gt_for_action false`; downstream detector substrate passed |
| Dense conflict rival identity fresh detector substrate job | `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1/rival_identity_detector_substrate_summary.json` | completed, substrate gate pass | tmux `h001-rival-identity-generalization-detector-20260526-102744`; detector rows `12`, detector box `1.0`, SAM2 mask `1.0`, candidate association `1.0`, rows with association `12`, associated candidate heading count `84`, `uses_gt_for_action false`; detector substrate gate passed |
| Dense conflict rival identity fresh post-observation analyzer | `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1/rival_identity_observation_validation_summary.json` | completed, gate fail | same frozen analyzer and thresholds as diagnostic; request/evidence/decision rows `6/12/6`; commit/success/wrong/no-label `4/2/2/0`; new primary success `2`, resolved rows `4`, action evidence forbidden key count `0`, `uses_gt_for_action false`; gate failed on wrong-goal commits from two single-candidate `toilet` false positives |
| Dense conflict rival identity fresh failure diagnostic | `local_dataset/runs/h001_rival_identity_generalization_failure_diagnostic_v1/rival_identity_failure_diagnostic_summary.json` | completed, superseded by taxonomy split | added `diagnose_rival_identity_generalization_failures.py`; mechanism counts `rival_identity_resolved_success 2`, `rival_identity_unresolved_cross_view_aliasing 2`, `single_candidate_object_existence_false_positive 2`; all wrong commits are explained by single-positive-candidate `toilet` false positives; mixed request reason led to the taxonomy split row below |
| Dense conflict rival identity fresh taxonomy split | `local_dataset/runs/h001_rival_identity_generalization_taxonomy_split_v1/rival_identity_observation_validation_summary.json` | completed, superseded by object-existence branch | patched `analyze_rival_identity_post_observation.py` to write `request_taxonomy_route`; Docker `py_compile` and analyzer rerun passed; route counts `rival_identity_arbitration 4`, `object_existence_validation 2`; failure taxonomy `none 2`, `rival_identity_unresolved_cross_view_aliasing 2`, `object_existence_false_positive_commit 2`; unsafe rival-identity commits `0`; object-existence rows are handled by the no-commit branch row below |
| Dense conflict rival identity object-existence branch | `local_dataset/runs/h001_rival_identity_generalization_object_existence_branch_v1/rival_identity_observation_validation_summary.json` | completed, gate pass | patched `analyze_rival_identity_post_observation.py` so `request_taxonomy_route == object_existence_validation` emits `defer_object_existence_validation`; Docker `py_compile` and analyzer rerun passed; commit/success/wrong `2/2/0`; defer-object-existence `2`; route counts `rival_identity_arbitration 4`, `object_existence_validation 2`; `uses_gt_for_action false`; regression `local_dataset/runs/h001_rival_identity_pair_probe_object_existence_branch_regression_v1` keeps commit/success/wrong `1/1/0` |
| Dense conflict rival identity object-existence probe | `local_dataset/runs/h001_rival_identity_object_existence_probe_v1/object_existence_validation_probe_summary.json` | completed, superseded by broader source design | added `analyze_object_existence_validation_probe.py`; Docker `py_compile` and probe run passed; request rows `2`, query `toilet`, naive unique-strong commit rows `2`, naive wrong-goal rows `2`, naive success rows `0`, wrong-goal avoided by defer `2`, success lost by defer `0`, action evidence forbidden key count `0`, probe design gate `true`; paper claim remains blocked, and the broader source design row below records the next validation path |
| Dense conflict rival identity broader source design | `local_dataset/runs/h001_rival_identity_broader_validation_design_v1/rival_identity_broader_design_summary.json` | completed, source miner passed | added `design_rival_identity_broader_validation.py`; Docker `py_compile` and design run passed; preferred source `risk_validation`; selected parent rows `72`, scenes `10`, queries `6`, estimated request rows `22`, top wrong-goal rows `41`, correct-and-wrong candidate rows `49`, design gate passed; actual miner result is recorded below |
| Dense conflict rival identity broader source manifest | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_broader_validation_v1.json` and `local_dataset/runs/h001_rival_identity_broader_source_v1/source_summary.json` | frozen, source gate pass | added `build_rival_identity_broader_manifest.py`; Docker `py_compile` and source freeze run passed; verify `manifests/h001_rival_identity_broader_validation_v1.verify.json` reports `ok true`; request rows `30`, request scenes `10`, request queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, excluded-scene overlap `0`, action evidence forbidden key count `0`, `uses_gt_for_action false` |
| Dense conflict rival identity broader plan smoke | `local_dataset/runs/h001_rival_identity_broader_plan_v1/rival_identity_observation_plan_summary.json` | Docker plan smoke pass | reused `plan_rival_identity_observation.py` on frozen broader manifest; request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, missing action rows `0`, candidate artifact rows/candidates `21/80`, action evidence forbidden key count `0`, plan gate `true`, `uses_gt_for_action false` |
| Dense conflict rival identity broader frame smoke | `local_dataset/runs/h001_rival_identity_broader_frames_v1/summary.json` and `local_dataset/runs/h001_rival_identity_broader_frames_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json` | Docker frame smoke pass with filtered heading caveat | added `filter_nonblank_frame_summary.py`; frame export rows requested/exported `112/112`, rendered headings `862`, RGB/depth/metadata files `862/862/862`, unique scenes `10`, `uses_gt_for_action false`; strict no-blank-heading gate failed with blank RGB `56/862` across `20` rows, but dropped rows `0`; nonblank-filtered summary keeps `112` rows and `806` headings with row-level nonblank gate `true` |
| Dense conflict rival identity broader detector substrate | `local_dataset/runs/h001_rival_identity_broader_detector_substrate_v2/rival_identity_detector_substrate_summary.json` | completed, substrate gate pass | added explicit detector `--frame-root` support because the filtered summary is under `nonblank_filter_v1` while frame assets remain under the original frame export root; first attempt `h001_rival_identity_broader_detector_substrate_v1` completed but gate failed with detector/SAM2/association `0.0`; corrected tmux `h001-rival-identity-broader-detector-v2-20260526-235709`, log `runtime/logs/rival-identity-broader-detector-substrate-v2-20260526-235709.log`; detector rows `112`, detector box `1.0`, SAM2 mask `1.0`, candidate association `0.6339`, rows with association `71/112`, associated heading count `442`, `uses_gt_for_action false` |
| Dense conflict rival identity broader post-observation analyzer | `local_dataset/runs/h001_rival_identity_broader_post_observation_v1/rival_identity_observation_validation_summary.json` | completed, safe but inert | Docker command used corrected detector associations, broader plan, and `rival_identity_broader_evaluation_labels.jsonl`; request/evidence/decision rows `30/112/30`, commit/success/wrong/no-label `0/0/0/0`, defer unresolved identity `26`, defer object-existence `4`, failure taxonomy `post_observation_no_candidate_support 26` and `object_existence_deferred_no_independent_confirmation 4`, post-observation gate `false`, `uses_gt_for_action false` |
| Dense conflict rival identity broader failure diagnostic | `local_dataset/runs/h001_rival_identity_broader_post_observation_diagnostic_v1/broader_post_observation_failure_summary.json` | completed, planner geometry blocker | added `diagnose_broader_post_observation_failure.py`; Docker `py_compile` and diagnostic run passed; mechanism counts `degenerate_zero_standoff_cross_association 22` and `degenerate_zero_standoff_no_visible_candidate 8`; plan rows `112`, zero/near-standoff rows `112/112`, rotation fallback rows `112`, target distance min/mean/max `0.0/0.0/0.0`, own associated rows `0`, cross associated rows `442`; `post_observation_rule_change_allowed false` |
| Dense conflict rival identity broader standoff planner contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_broader_standoff_planner_v1.json` | defined, implemented below | freezes the zero-standoff-safe planner revision; reuses `NavmeshSnapper` and `plan_standoff_viewpoint`; forbids candidate `visit_position` fallback when target distance is below `0.75m`; requires zero/near-standoff rows `0`, rotation fallback rows `0`, planned request rows `>=20`, scenes `>=5`, queries `>=3`, and no GT action input before rerunning frames/detector/analyzer |
| Dense conflict rival identity broader standoff planner smoke | `local_dataset/runs/h001_rival_identity_broader_plan_standoff_v1/rival_identity_observation_plan_summary.json` | Docker plan and geometry gate pass | patched `plan_rival_identity_observation.py` with `--viewpoint-mode standoff`; Docker `py_compile` passed; request rows `30`, planned request rows `30`, plan rows `112`, skipped rows `0`, scenes `10`, queries `6`, zero/near-standoff rows `0/0`, rotation/candidate fallback rows `0/0`, target distance min/mean/max `1.6386/1.7506/1.9747m`, viewpoint sources `standoff_navmesh 104` / `standoff_geometry 8`, plan gate `true`, geometry gate `true`, `uses_gt_for_action false`; next gate is standoff frame export and nonblank sanity |
| Dense conflict rival identity broader mixed-standoff frame smoke | `local_dataset/runs/h001_rival_identity_broader_frames_standoff_v1/summary.json` and `nonblank_filter_v1/nonblank_frame_filter_summary.json` | completed, row-level nonblank fail | frame export rows requested/exported `112/112`, rendered headings `1079`, unique scenes `10`, `uses_gt_for_action false`; nonblank kept `107/112` rows and `1028/1079` headings, removed blank headings `51`, dropped rows `5`; all dropped rows were `standoff_geometry` fallback with `standoff_navmesh_navigable false`, so detector rerun stayed blocked |
| Dense conflict rival identity broader navmesh-only standoff frame smoke | `local_dataset/runs/h001_rival_identity_broader_plan_standoff_navmesh_v1/rival_identity_observation_plan_summary.json`, `local_dataset/runs/h001_rival_identity_broader_frames_standoff_navmesh_v1/summary.json`, and `nonblank_filter_v1/nonblank_frame_filter_summary.json` | Docker plan/frame/nonblank gate pass | added `--require-navmesh-standoff`; plan keeps planned request rows `28/30`, plan rows `104`, skipped rows `8` all `standoff_navmesh_required`, scenes `9`, queries `6`, viewpoint sources `standoff_navmesh 104`, `uses_gt_for_action false`; frame export rows requested/exported `104/104`, rendered headings `997`; nonblank kept `104/104` rows and `997/997` headings with dropped/blank rows `0/0`, row-level and strict no-blank gates `true`; detector/SAM2 substrate is now unblocked for this filtered frame summary |
| Dense conflict rival identity broader navmesh-only detector substrate | `local_dataset/runs/h001_rival_identity_broader_detector_substrate_standoff_navmesh_v1/rival_identity_detector_substrate_summary.json` | completed, substrate gate pass | tmux `h001-rival-identity-broader-standoff-navmesh-detector-20260527-011137`; detector rows `104`, frame rows `104`, detector box `0.9808`, SAM2 mask `0.9808`, candidate association `0.7212`, rows with association `75`, associated heading count `277`, `uses_gt_for_action false` |
| Dense conflict rival identity broader navmesh-only post-observation analyzer | `local_dataset/runs/h001_rival_identity_broader_post_observation_standoff_navmesh_v1/rival_identity_observation_validation_summary.json` | completed, unsafe negative result | request/evidence/decision rows `28/110/28`, commit/success/wrong/no-label `7/0/7/0`, defer unresolved identity `19`, defer object-existence `2`, failure taxonomy `unsafe_rival_identity_commit 7`, `rival_identity_unresolved_cross_view_aliasing 8`, `post_observation_no_candidate_support 6`, `post_observation_margin_too_small 5`, `object_existence_deferred_no_independent_confirmation 2`, post-observation gate `false` |
| Dense conflict rival identity unsafe commit diagnostic | `local_dataset/runs/h001_rival_identity_unsafe_commit_diagnostic_standoff_navmesh_v1/rival_identity_unsafe_commit_diagnostic_summary.json` | completed, threshold-only repair rejected | added `diagnose_rival_identity_unsafe_commits.py`; unsafe commits `7` with query counts `bed 4`, `chair 2`, `tv_monitor 1`; mechanisms include `absence_of_cross_support_not_discriminative 7`, `low_detector_score_still_strong_by_count 5`, `wrong_candidate_has_stronger_own_view_support_than_correct 4`, `candidate_set_no_valid_goal_candidate 3`, `depth_consistent_wrong_candidate 3`; simple rank/box/depth/own-count guards still produce wrong commits, safe combined simple guard is inert |
| Dense conflict rival identity strict arbitration contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_strict_arbitration_v1.json` | frozen, design contract | contract name `rival_identity_goal_validity_arbitration_v1`; requires candidate-set validity, local semantic/geometric consistency, rival contrast, and commit/defer routing; blocks single-feature threshold repairs and keeps `paper_claim_allowed false` |
| Dense conflict rival identity goal-validity objective | `local_dataset/runs/h001_rival_identity_broader_post_observation_goal_validity_v1/rival_identity_observation_validation_summary.json` | completed, diagnostic gate pass | implemented `analyze_rival_identity_post_observation.py --objective goal_validity_arbitration_v1`; default regression output preserves prior unsafe result `7/0/7/0`; goal-validity output has request/evidence/decision rows `28/110/28`, commit/success/wrong/no-label `2/2/0/0`, post-observation gate `true`, `uses_gt_for_action false`; paper claim remains blocked pending independent/predeclared validation |
| Dense conflict rival identity goal-validity independent source | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_goal_validity_independent_v1.json` and `local_dataset/runs/h001_rival_identity_goal_validity_independent_source_v1/source_summary.json` | frozen, source gate pass | patched `build_rival_identity_broader_manifest.py` to accept explicit contract/policy/output names; source mined from `v3_fresh_validation` after excluding prior diagnostic and broader diagnostic scenes; design output has parent rows `72`, scenes `11`, queries `6`, top wrong-goal rows `51`, correct+wrong candidate rows `59`; verify reports `ok true`, request rows `30`, request scenes `10`, request queries `6`, route counts `rival_identity_arbitration 26` / `object_existence_validation 4`, excluded-scene overlap `0`, action evidence forbidden key count `0`, `uses_gt_for_action false`; downstream substrate and objective rerun are recorded below |
| Dense conflict rival identity goal-validity independent substrate | `local_dataset/runs/h001_rival_identity_goal_validity_independent_detector_substrate_standoff_navmesh_v1/rival_identity_detector_substrate_summary.json` | completed, substrate gate pass | plan output `local_dataset/runs/h001_rival_identity_goal_validity_independent_plan_standoff_navmesh_v1` has request/planned/plan rows `30/30/92`, skipped rows `9` all `standoff_navmesh_required`, scenes/queries `10/6`, zero/near-standoff `0/0`; frame output exports rows/headings `92/810`; nonblank filter keeps `92/810`, dropped rows `0`, strict no-blank gate `true`; detector rows `92`, detector box `1.0`, SAM2 mask `1.0`, candidate association `0.6196`, rows with association `57`, associated heading count `239`, `uses_gt_for_action false` |
| Dense conflict rival identity goal-validity independent rerun | `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_goal_validity_v1/rival_identity_observation_validation_summary.json` | completed, safe but inert negative result | reran frozen `goal_validity_arbitration_v1` without threshold changes; request/evidence/decision rows `30/101/30`; action counts `defer_expanded_retrieval_needed 23`, `defer_object_existence_validation 6`, `defer_unresolved_identity 1`; commit/success/wrong/no-label `0/0/0/0`; wrong-goal and no-label gates pass, but new-primary-success and resolved-request gates fail; dominant reasons are `defer_low_goal_validity_cross_view_aliasing 12`, `post_observation_no_candidate_support 8`, `object_existence_requires_independent_confirmation 6`; `uses_gt_for_action false`; paper claim remains blocked |
| Dense conflict rival identity goal-validity default counterfactual | `local_dataset/runs/h001_rival_identity_goal_validity_independent_post_observation_default_v1/rival_identity_observation_validation_summary.json` | completed, unsafe counterfactual | same independent evidence with default `unique_strong_own_view_identity`; commit/success/wrong/no-label `7/4/3/0`; wrong-goal queries `chair 1`, `sofa 1`, `toilet 1`; `uses_gt_for_action false`; demonstrates loose identity evidence is nontrivial but unsafe |
| Dense conflict rival identity goal-validity failure diagnostic | `local_dataset/runs/h001_rival_identity_goal_validity_independent_failure_diagnostic_v1/goal_validity_independent_failure_summary.json` | completed, threshold repair rejected | added `diagnose_goal_validity_independent_failure.py`; strict rule `0/0/0`, default rule `7/4/3`, diagnostic tradeoff check `true`; dominant mechanism tags `cross_view_aliasing_blocks_goal_validity 14`, `planned_candidate_set_has_no_valid_goal 13`, `no_own_candidate_support 11`, `strong_identity_not_goal_validity 8`, `object_existence_branch_blocks_commit 6`; `uses_gt_for_action false`, `uses_gt_for_analysis true` |
| Dense conflict rival identity goal-validity revision V2 router | `local_dataset/runs/h001_rival_identity_goal_validity_revision_v2_router_v1/goal_validity_revision_v2_router_summary.json` | completed, routing contract only | contract `manifests/h001_rival_identity_goal_validity_revision_v2.json`; added `route_goal_validity_revision_v2.py`; routes all `30` independent requests without evaluation labels into `request_discriminative_rival_view 14`, `request_expanded_retrieval 8`, `request_object_existence_confirmation 6`, `request_goal_validity_confirmation 2`; terminal commit rows `0`, `uses_gt_for_action false`; paper claim remains blocked |
| Dense conflict discriminative rival view planner contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_discriminative_rival_view_planner_v1.json` | frozen, design contract | starts from router rows with `revision_action == request_discriminative_rival_view` (`14` rows); requires contrastive focus-rival pair views, explicit pair candidate ids, no GT/post-join action inputs, zero/near-standoff and rotation fallback `0`, detector box/SAM2 `>=0.80`, pair association `>=0.40`, and fresh/predeclared validation before paper claim |
| Dense conflict discriminative rival view plan smoke | `local_dataset/runs/h001_discriminative_rival_view_plan_v1/discriminative_rival_view_plan_summary.json` | completed, plan gate pass | added `plan_discriminative_rival_view.py`; source router rows `14`, planned request rows `14`, plan rows `38`, common pair view rows `10`, matched dual standoff rows `28`, skipped rows `4` all `common_pair_view_unavailable`, zero/near-standoff `0/0`, rotation fallback `0`, target distance min/mean/max `1.6344/1.9781/3.1546m`, query counts `bed 15`, `chair 11`, `plant 9`, `sofa 3`, `uses_gt_for_action false`; v1 frame smoke exposed one blank geometry-only common pair row |
| Dense conflict discriminative rival view v2 frame/nonblank smoke | `local_dataset/runs/h001_discriminative_rival_view_frames_v2/summary.json` and `local_dataset/runs/h001_discriminative_rival_view_frames_v2/nonblank_filter_v1/nonblank_frame_filter_summary.json` | completed, frame gate pass | repaired planner to keep only navmesh-snapped common pair views; patched `export_postview_frames_v2.py` to preserve `viewpoint_pair_role`, `rival_*`, `revision_*`, and `standoff_*`; v2 plan rows `38`, common pair navmesh rows `10`, matched dual standoff rows `28`; frame rows/headings `38/222`, dropped rows `0`, removed blank headings `0`, role counts `common 10`, `focus 14`, `rival 14`, row-level and strict no-blank gates `true`, `uses_gt_for_action false` |
| Dense conflict discriminative rival view detector/SAM2 substrate v1 | `local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v1/rival_identity_detector_substrate_summary.json` | completed, superseded | detector rows `38`, detector box/SAM2 `1.0/1.0`, candidate association `0.8158`, rows with association `31`, associated heading count `128`, `uses_gt_for_action false`; substrate gate passed, but detector output did not preserve `viewpoint_pair_role`, so pair-level analysis uses v2 |
| Dense conflict discriminative rival view detector/SAM2 substrate v2 | `local_dataset/runs/h001_discriminative_rival_view_detector_substrate_v2/rival_identity_detector_substrate_summary.json` | completed, substrate gate pass | patched `detect_postview_groundingdino_sam2.py` to preserve `viewpoint_pair_role`, `rival_*`, `revision_*`, and `standoff_*`; tmux `h001-discriminative-rival-view-detector-v2-20260527-033307`; detector rows `38`, detector box/SAM2 `1.0/1.0`, candidate association `0.8158`, rows with association `31`, associated heading count `128`, association-role rows `common 118`, `focus 162`, `rival 164`, `uses_gt_for_action false`; paper claim remains blocked |
| Dense conflict discriminative rival view evidence analyzer | `local_dataset/runs/h001_discriminative_rival_view_evidence_v1/discriminative_rival_view_evidence_summary.json` | completed, diagnostic gate fail | added `analyze_discriminative_rival_view_evidence.py`; request rows `14`, association rows `444`, evidence availability `1.0`, disambiguation `0.6429`, actions `discriminative_support_focus 8`, `discriminative_support_rival 1`, `discriminative_ambiguous_defer 5`; label cases `both_correct 6`, `neither_correct 5`, `rival_only_correct 3`; diagnostic gate fails because single-correct preferred rate `0.0` and wrong-preference rate `0.3333`; next task is failure taxonomy, not threshold tuning |
| Dense conflict discriminative rival view failure diagnostic | `local_dataset/runs/h001_discriminative_rival_view_failure_diagnostic_v1/discriminative_rival_view_failure_summary.json` | completed, revision required | added `diagnose_discriminative_rival_view_failure.py`; dominant tags `symmetric_cross_view_leak 7`, `rival_visible_from_focus_view 6`, `identity_score_near_tie 5`, `common_view_supports_both_candidates 5`, `no_valid_goal_pair_but_disambiguated 4`, `both_correct_goal_region_or_duplicate_preferred 4`, `rival_correct_own_view_evidence_weak 3`; gates block threshold tuning, objective revision, and fresh validation; branch priority decision is to define `request_expanded_retrieval` next and reuse discriminative views only after retrieval expands the candidate set |
| Dense conflict expanded retrieval branch contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_branch_v1.json` | frozen, contract gate pass | uses router rows with `revision_action == request_expanded_retrieval`, expected request rows `8`, candidate budget `6-10`, forbidden action inputs include GT/evaluation labels and threshold tuning from joined labels, terminal commit is disabled, and candidate-set validity gates must pass before detector/objective work; `jq` validation passed |
| Dense conflict expanded retrieval planner smoke | `local_dataset/runs/h001_expanded_retrieval_plan_v1/expanded_retrieval_summary.json` | Docker plan gate pass | added `plan_expanded_retrieval_branch.py`; Docker `py_compile` and planner run passed; expected/request rows `8/8`, candidate-set rows `8`, plan rows `80`, expanded candidates per request `10`, skipped rows `0`, duplicate candidate rate `0.0`, nonfinite position rate `0.0`, forbidden action keys `0`, `uses_gt_for_action false`, `paper_claim_allowed false`; next gate is analysis-only candidate-set validity before detector/objective work |
| Dense conflict expanded retrieval candidate-set validity | `local_dataset/runs/h001_expanded_retrieval_candidate_set_validity_v1/expanded_retrieval_candidate_set_validity_summary.json` | Docker label-join diagnostic pass, guard source | added `diagnose_expanded_retrieval_candidate_set.py`; label join gate passes with missing labels `0`; request rows `8`, candidate rows `80`, contains-correct `6/8`, no-valid `2/8`, source-top correct `1/8`, source-top wrong-goal `7/8`, wrong-top replacement `5/7`, rows with wrong-goal candidate `7/8`; full-pool comparison has `source_pool_no_valid_candidate 2`, `valid_set_with_wrong_goal_distractor 5`, `valid_set_without_wrong_goal_distractor 1`, and `selected_missed_full_pool_correct_rows 0`; this is analysis-only evidence and not a paper claim |
| Dense conflict expanded retrieval candidate-set guard design | `local_dataset/runs/h001_expanded_retrieval_candidate_set_guard_v1/expanded_retrieval_candidate_set_guard_summary.json` | Docker guard design gate pass, action-time proxy needed | added `design_expanded_retrieval_candidate_set_guard.py`; route counts are `request_backend_retrieval_revision 2`, `request_detector_guarded_observation 5`, and `request_lightweight_confirmation 1`; detector evidence allowed rows `6/8`, terminal commit rows `0`, missing candidate-set rows `0`, `guard_design_gate_passed true`, `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false`; this artifact is analysis-only design and requires non-GT action-time proxies before detector/objective escalation |
| Dense conflict expanded retrieval guard proxy feature audit | `local_dataset/runs/h001_expanded_retrieval_guard_proxy_features_v1/expanded_retrieval_guard_proxy_feature_summary.json` | Docker feature gate pass, source-pool proxy fail | added `analyze_expanded_retrieval_guard_proxy_features.py`; feature extraction gate passes with request rows `8`, forbidden action feature rows `0`, terminal commit rows `0`, and `uses_gt_for_action false`; current candidate-set score/support proxy routes all rows to `request_detector_guarded_observation_proxy`; target backend rows `2`, target backend routed to backend `0`, target backend escalated to evidence `2`, source-pool validity proxy recall `0.0`, evidence-allowed target recall `1.0`, `proxy_ready_for_detector_gate false`; superseded by the stronger source-pool validity proxy below |
| Dense conflict expanded retrieval source-pool validity proxy | `local_dataset/runs/h001_expanded_retrieval_source_pool_validity_proxy_v1/expanded_retrieval_source_pool_validity_proxy_summary.json` | Docker diagnostic gate pass, fresh validation needed | added `analyze_expanded_retrieval_source_pool_validity_proxy.py`; proxy route counts are `request_backend_retrieval_revision_proxy 2` and `request_detector_guarded_observation_proxy 6`; consumed forbidden rows `0`; source-pool validity proxy recall `1.0`; evidence-allowed target recall `1.0`; backend targets escalated to evidence `0`; evidence targets blocked as backend `0`; `proxy_ready_for_detector_gate true`; `uses_gt_for_action false`; `paper_claim_allowed false`; superseded by the detector frame gate below |
| Dense conflict expanded retrieval detector evidence plan/frame | `local_dataset/runs/h001_expanded_retrieval_detector_plan_v1/expanded_retrieval_detector_plan_summary.json` and `local_dataset/runs/h001_expanded_retrieval_detector_frames_v1/summary.json` | Docker plan/frame gate pass, detector association gate fail | added `manifests/h001_expanded_retrieval_detector_evidence_v1.json`, `plan_expanded_retrieval_detector_observation.py`, and `runtime/jobs/expanded_retrieval_detector_substrate.sh`; plan gate passes with detector proxy request rows `6`, planned request rows `6`, plan rows `42`, min/max plan rows per request `5/8`, zero/near-standoff `0/0`, fallback rows `0`, consumed forbidden action fields `0`, and `uses_gt_for_action false`; frame export has rows/headings `42/168`; nonblank filter has dropped rows `0`, removed blank headings `0`, and strict no-blank heading gate `true`; detector/SAM2 substrate output `local_dataset/runs/h001_expanded_retrieval_detector_substrate_v1` has detector box/SAM2 mask rates `1.0/1.0` but candidate association rate `0.0714` with associated rows `3/42`, so detector substrate gate fails; projection status counts are `out_of_fov 134` and `visible 34` |
| Dense conflict expanded retrieval detector association failure diagnostic | `local_dataset/runs/h001_expanded_retrieval_detector_failure_diagnostic_v1/expanded_retrieval_detector_failure_summary.json` | Docker diagnostic gate pass, viewpoint revision required | added `diagnose_expanded_retrieval_detector_association_failure.py`; accounts for `42` candidate observation rows and `168` heading rows; failure mechanisms are `projection_never_visible 33`, `mask_overlap_depth_mismatch_only 4`, `associated_success 3`, `visible_projection_no_detector_overlap 1`, and `box_overlap_mask_reject 1`; detector box/SAM2 availability is `42/42`; gates set `threshold_tuning_allowed false`, `viewpoint_revision_required true`, `association_depth_revision_required true`, `fresh_validation_allowed false`, `uses_gt_for_action false`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval viewpoint/projection revision design | `local_dataset/runs/h001_expanded_retrieval_detector_viewpoint_revision_design_v1/expanded_retrieval_detector_viewpoint_revision_design_summary.json` and `manifests/h001_expanded_retrieval_detector_viewpoint_revision_v1.json` | Docker design gate pass, implemented | added `design_expanded_retrieval_detector_viewpoint_revision.py`; out-of-FOV axis count is `x_in_y_above 134`, so yaw-widen-only is rejected; selected `projection_anchor_height_sweep_v1` with offsets `[0.0, 0.4, 0.8, 1.2, 1.6]`; height sweep recovers `33/33` `projection_never_visible` rows in projection replay; detector threshold tuning, terminal objective tuning, and depth tolerance relaxation remain blocked before detector/SAM2 rerun; `uses_gt_for_action false`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval projection-anchor implementation smoke and detector rerun | `local_dataset/runs/h001_expanded_retrieval_detector_plan_projection_anchor_v1/expanded_retrieval_detector_plan_summary.json`, `local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_smoke_v1/projection_anchor_smoke_summary.json`, `local_dataset/runs/h001_expanded_retrieval_detector_projection_anchor_frame_passthrough_smoke_v1/projection_anchor_smoke_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_detector_substrate_projection_anchor_v1/expanded_retrieval_detector_substrate_summary.json` | Docker plan/projection smoke pass, detector substrate gate pass | patched `plan_expanded_retrieval_detector_observation.py` to emit `h001.expanded_retrieval_detector_observation_plan.v2`, patched `detect_postview_groundingdino_sam2.py` to evaluate fixed projection anchors, and added `smoke_expanded_retrieval_projection_anchor.py`; revised plan has plan rows `42`, planned request rows `6`, fixed offsets `[0.0, 0.4, 0.8, 1.2, 1.6]`, and `uses_gt_for_action false`; full projection smoke has visible rows `42/42`; 2-row frame passthrough smoke preserves revision metadata `2/2`; fixed-anchor detector/SAM2 rerun `h001-expanded-retrieval-detector-anchor-20260527-163608` completed with detector box/SAM2 `1.0/1.0`, candidate association rate `0.7381`, associated rows `31/42`, substrate gate pass, `uses_gt_for_action false`; no paper claim yet |
| Dense conflict expanded retrieval fresh/predeclared source freeze | `local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_v1/source_summary.json`, `manifests/h001_expanded_retrieval_fresh_validation_v1.json`, and `local_dataset/runs/h001_expanded_retrieval_fresh_validation_plan_v1/expanded_retrieval_summary.json` | Docker source freeze and planner compatibility gate pass, paper-scale gate fail | added `freeze_expanded_retrieval_validation_source.py`; router output `local_dataset/runs/h001_expanded_retrieval_fresh_validation_router_v1` has `6` `request_expanded_retrieval` rows from `2` scenes and `4` queries; source freeze has excluded-scene overlap `0`, action forbidden keys `0`, missing action evidence rows `0`, `uses_gt_for_action false`; planner compatibility has candidate-set rows `6`, plan rows `60`, skipped rows `0`; paper-scale gate is false because rows/scenes are below `20/5`; superseded by the paper-scale source freeze below |
| Dense conflict expanded retrieval fresh-source proxy/plan/frame gates | `local_dataset/runs/h001_expanded_retrieval_fresh_validation_source_pool_validity_proxy_v1/expanded_retrieval_source_pool_validity_proxy_summary.json`, `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_plan_projection_anchor_v1/expanded_retrieval_detector_plan_summary.json`, `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_frames_projection_anchor_v1/summary.json`, and `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_projection_anchor_smoke_v1/projection_anchor_smoke_summary.json` | Docker proxy, plan, frame, nonblank, and projection smoke gate pass | patched `analyze_expanded_retrieval_source_pool_validity_proxy.py` for fresh sources without analysis-only guard labels; proxy routes `6/6` rows to `request_detector_guarded_observation_proxy` and has `proxy_ready_for_detector_gate true`; detector plan has planned requests `6`, plan rows `51`, skipped rows `9` all `standoff_navmesh_required`, plan rows per request `7-10`, zero/near/fallback rows `0/0/0`, and `uses_gt_for_action false`; frame export has rows/headings `51/204`; nonblank filter keeps rows/headings `51/204`; projection smoke has visible rows `51/51` and revision metadata rows `51/51`; no paper claim yet |
| Dense conflict expanded retrieval fresh-source detector/SAM2 substrate | `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_substrate_projection_anchor_v1/expanded_retrieval_detector_substrate_summary.json` | Docker detector substrate gate pass, paper-scale gate blocked | tmux `h001-fresh-expanded-detector-20260527-173955` completed; detector rows `51`, detector box/SAM2 rates `1.0/1.0`, candidate association rate `0.6078`, associated rows `31/51`, associated candidate heading count `68`, selected projection anchor offsets `0.0:8`, `1.2:12`, `1.6:184`, `uses_gt_for_action false`; `paper_claim_allowed false`; superseded by the detector evidence diagnostic below |
| Dense conflict expanded retrieval fresh-source detector evidence diagnostic | `local_dataset/runs/h001_expanded_retrieval_fresh_validation_detector_evidence_diagnostic_v1/expanded_retrieval_detector_evidence_diagnostic_summary.json` | Docker diagnostic gate pass, terminal objective blocked | added `diagnose_expanded_retrieval_detector_evidence.py`; request rows `6`, candidate rows `51`, associated request rate `1.0`, strong request rate `1.0`, multi-strong request rate `0.8333`, lower-rank-only association rate `0.5`; topology counts `multi_strong_saturated_ambiguity 5`, `single_strong_lower_rank 1`; terminal risk counts `multi_candidate_detector_ambiguity 5`, `source_top_challenged_by_lower_rank_evidence 1`; `terminal_objective_allowed false`, `paper_scale_gate_passed false`, `paper_claim_allowed false`; superseded by the ambiguity-aware objective contract below |
| Dense conflict expanded retrieval ambiguity-aware objective contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_ambiguity_objective_v1.json` and `local_dataset/runs/h001_expanded_retrieval_ambiguity_objective_contract_v1/expanded_retrieval_ambiguity_objective_summary.json` | Docker contract gate pass, larger source allowed | added `apply_expanded_retrieval_ambiguity_objective_contract.py`; request rows `6`, route coverage `1.0`, terminal commit rows `0`, action counts `request_local_context_disambiguation 5` and `request_rank_challenge_confirmation 1`; topology counts `multi_strong_saturated_ambiguity 5`, `single_strong_lower_rank 1`; `larger_source_allowed_after_contract true`, `terminal_objective_allowed false`, `paper_claim_allowed false`; superseded by the paper-scale source freeze below |
| Dense conflict expanded retrieval paper-scale source freeze | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_paper_scale_v1.json`, `local_dataset/runs/h001_expanded_retrieval_paper_scale_source_v1/source_summary.json`, `local_dataset/runs/h001_expanded_retrieval_paper_scale_plan_v1/expanded_retrieval_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_paper_scale_source_pool_validity_proxy_v1/expanded_retrieval_source_pool_validity_proxy_summary.json` | Docker source, planner, and source-pool proxy gate pass | added `freeze_expanded_retrieval_paper_scale_source.py`; source freezes nonterminal `defer_expanded_retrieval_needed` decisions into `23` `request_expanded_retrieval` rows across `10` scenes and `6` queries, with excluded-scene overlap `0`, action forbidden keys `0`, `uses_gt_for_action false`, and paper-scale gate `true`; planner compatibility has candidate-set rows `23`, plan rows `230`, skipped rows `0`; source-pool proxy routes `2` rows to backend revision and `21` rows to detector-guarded observation, with action-only detector gate pass; superseded by the upper-anchor frame/projection gate below |
| Dense conflict expanded retrieval paper-scale upper-anchor frame/projection gate | `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_plan_projection_anchor_upper_v1/expanded_retrieval_detector_plan_summary.json`, `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_frames_projection_anchor_upper_v1/summary.json`, and `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_projection_anchor_upper_smoke_v1/projection_anchor_smoke_summary.json` | Docker plan, frame, nonblank, and projection smoke gate pass | initial `1.6m` anchor frame export passed with rows/headings `162/648` and blank rows/headings `0/0`, but projection smoke failed at `153/162 = 0.9444`; failed rows were all `bxsVRursffK/plant` with `x_in_y_above`; official upper-anchor plan extends offsets to `[0.0, 0.4, 0.8, 1.2, 1.6, 2.0, 2.4]`, preserves detector proxy request rows `21`, planned requests `21`, plan rows `162`, skipped rows `48`, and `uses_gt_for_action false`; upper frame/nonblank keeps rows/headings `162/648`, projection smoke passes with visible rows `162/162`, missing candidates `0`, and `paper_claim_allowed false`; superseded by detector substrate and evidence diagnostic below |
| Dense conflict expanded retrieval paper-scale detector/SAM2 substrate | `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_substrate_projection_anchor_upper_v1/expanded_retrieval_detector_substrate_summary.json` | Docker detector substrate gate pass | tmux job `h001-paper-expanded-detector-upper-20260527-194607` completed; detector rows `162`, detector box/SAM2 `1.0/1.0`, candidate association `0.8272`, associated rows `134/162`, associated candidate heading count `378`, selected projection anchor offsets `0.0:247`, `0.4:107`, `0.8:52`, `1.2:32`, `1.6:23`, `2.0:117`, `2.4:70`, `uses_gt_for_action false`, and `paper_claim_allowed false`; superseded by detector evidence diagnostic below |
| Dense conflict expanded retrieval paper-scale detector evidence diagnostic | `local_dataset/runs/h001_expanded_retrieval_paper_scale_detector_evidence_diagnostic_upper_v1/expanded_retrieval_detector_evidence_diagnostic_summary.json` | Docker diagnostic gate pass, terminal objective blocked | request rows `21`, candidate rows `162`, association heading rows `648`, associated request rate `1.0`, strong request rate `1.0`, multi-strong request rate `1.0`, lower-rank-only association rate `0.2381`, topology `multi_strong_saturated_ambiguity 21`, terminal risk `multi_candidate_detector_ambiguity 21`, diagnostic and paper-scale gates pass, `terminal_objective_allowed false`, `uses_gt_for_action false`, and `paper_claim_allowed false`; superseded by ambiguity objective and local-context contract |
| Dense conflict expanded retrieval paper-scale ambiguity objective and local-context contract | `local_dataset/runs/h001_expanded_retrieval_paper_scale_ambiguity_objective_upper_v1/expanded_retrieval_ambiguity_objective_summary.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_disambiguation_v1.json` | objective contract gate pass, planner contract frozen | ambiguity objective route coverage `1.0`, action `request_local_context_disambiguation 21`, terminal commit rows `0`; local-context contract defines planner `expanded_retrieval_local_context_disambiguation_v1`, source filter `objective_action == request_local_context_disambiguation`, planned request minimum `18/21`, direct detector-score/source-top commits blocked, terminal rule `local_context_unique_own_view_advantage`, `uses_gt_for_action false`, and `paper_claim_allowed false`; superseded by local-context planner smoke |
| Dense conflict expanded retrieval paper-scale local-context planner smoke | `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_plan_v1/expanded_retrieval_local_context_plan_summary.json` | Docker planner gate pass | added `plan_expanded_retrieval_local_context_disambiguation.py`; request/planned request rows `21/21`, planned coverage `1.0`, plan rows `113`, skipped rows `3` all `standoff_navmesh_required`, plan rows per request min/max `2/6`, viewpoint source `standoff_navmesh 113`, zero/near/fallback/rotation fallback rows `0/0/0/0`, consumed/output forbidden action fields `0/0`, `uses_gt_for_action false`, and `paper_claim_allowed false`; next gate is local-context frame/projection smoke |
| Dense conflict expanded retrieval paper-scale local-context frame/projection smoke | `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/summary.json`, `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_frames_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_projection_smoke_v1/projection_anchor_smoke_summary.json` | Docker frame/nonblank/projection gate pass | frame rows `113/113`, rendered headings `1285`, headings per row `7-17`, nonblank rows `113/113`, removed blank headings `0`, strict no-blank gate `true`, projection visible rows `113/113`, missing candidate rows `0`, revision metadata rows `113`, candidate selection source `explicit_candidate_ids 113`, `uses_gt_for_action false`, and `paper_claim_allowed false`; superseded by local-context detector/post-observation results below |
| Dense conflict expanded retrieval paper-scale local-context detector/SAM2 substrate | `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json` | Docker detector substrate gate pass | tmux `h001-paper-local-context-detector-20260527-205216` completed; detector rows `113`, detector box/SAM2 `1.0/1.0`, candidate association `0.9204`, associated rows `104/113`, associated candidate heading count `365`, selected projection anchor offsets `0.0:790`, `0.4:138`, `0.8:56`, `1.2:34`, `1.6:23`, `2.0:157`, `2.4:87`, `uses_gt_for_action false`, and `paper_claim_allowed false`; superseded by local-context post-observation evaluation below |
| Dense conflict expanded retrieval paper-scale local-context post-observation evaluation | `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_post_observation_v1/expanded_retrieval_local_context_post_observation_summary.json` | Docker evaluation complete, terminal gate fail | added `analyze_expanded_retrieval_local_context_evidence.py`; request/evidence rows `21/113`, detector box/SAM2/candidate association `1.0/1.0/0.9204`, strong own-view request rows `19/21`, proposed `local_context_unique_own_view_advantage` commits/success/wrong/no-valid `10/3/7/3`, post-observation gate `false`; simpler alternatives are unsafe except `defer_all`, which is safe but inert; `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false`; superseded by failure diagnosis below |
| Dense conflict expanded retrieval paper-scale local-context failure diagnosis | `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_failure_diagnostic_v1/expanded_retrieval_local_context_failure_summary.json` | Docker diagnostic complete, revision contract needed | added `diagnose_expanded_retrieval_local_context_failures.py`; proposed request/commit/success/wrong rows `21/10/3/7`; dominant tags include `selected_detector_strong_role 9`, `wrong_commit 7`, `wrong_candidate_stronger_own_view_than_best_correct 4`, `best_correct_not_strong_own_view 4`, `own_view_support_prefers_wrong_over_weak_correct 4`, `source_pool_no_valid_candidate 3`, and `wrong_commit_without_correct_planned_candidate 3`; revision must separate no-valid pool failure from wrong-instance arbitration and must not threshold-tune from joined labels |
| Dense conflict expanded retrieval revised local-context objective and analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_revision_v1.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_local_context_revision.py`, and `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_v1/expanded_retrieval_local_context_revision_summary.json` | Docker evaluation complete, safe but inert | freezes and implements `goal_validity_guarded_local_context_v1`; Docker compile and run passed; request/evidence/decision/evaluated rows `21/113/168/168`; detector box/SAM2/candidate association `1.0/1.0/0.9204`; action forbidden keys `0`; revised rule commit/success/wrong/no-valid `0/0/0/0`; route counts `request_goal_validity_confirmation 12` and `defer_instance_arbitration_unresolved 9`; substrate gate passed but utility gate failed, so `paper_claim_allowed false` |
| Dense conflict expanded retrieval revised local-context route diagnostic | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_expanded_retrieval_local_context_revision_routes.py` and `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_revision_route_diagnostic_v1/expanded_retrieval_local_context_revision_route_summary.json` | Docker diagnostic complete, route-specific contract needed | request rows `21`; route counts `request_goal_validity_confirmation 12` and `defer_instance_arbitration_unresolved 9`; no-valid rows all route to goal-validity confirmation `4`; diagnostic tags include `pool_guard_false_positive_no_valid_pool 4`, `unsafe_previous_commit_prevented 7`, `previous_rule_success_lost_by_guard 3`, `correct_and_wrong_both_strong_own_view 7`, `wrong_only_strong_own_view 7`, and `simpler_alternatives_unsafe_analysis_only 20`; next contract must separate source-pool repair from goal-validity confirmation; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval route-specific local-context contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_route_contract_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_local_context_route_contract_v1.verify.json` | Contract frozen before implementation | separates `source_pool_repair_v1`, `goal_validity_confirmation_v1`, and `instance_arbitration_defer_v1`; keeps terminal commits blocked with `terminal_commit_rows_maximum 0`; requires all `21` request rows to be routed, action forbidden keys `0`, and labels joined only after action rows; next analyzer output root is `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1`; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval route-specific local-context analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_local_context_route_specific.py` and `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1/expanded_retrieval_local_context_route_specific_summary.json` | Docker route contract gate pass | Docker compile and run passed; request rows `21`; route counts `request_source_pool_repair 5`, `request_goal_validity_confirmation_evidence 7`, and `defer_instance_arbitration_unresolved 9`; terminal commit rows `0`; action forbidden keys `0`; route contract gate passed; post-action label join shows no-valid rows route to source-pool repair `4/4`, with one valid row conservatively routed to source-pool repair; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval source-pool repair evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_source_pool_repair_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_source_pool_repair_v1.verify.json` | Contract frozen before implementation | consumes five `request_source_pool_repair` rows from `local_dataset/runs/h001_expanded_retrieval_paper_scale_local_context_route_specific_v1`; required route actions are `request_backend_pool_expansion`, `route_to_goal_validity_confirmation_after_pool_repair`, and `defer_source_pool_unresolved`; terminal commits remain blocked; action forbidden keys must remain `0`; label join is evaluation-only; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval source-pool repair analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_source_pool_repair.py` and `local_dataset/runs/h001_expanded_retrieval_source_pool_repair_v1/source_pool_repair_summary.json` | Docker repair gate pass | Docker compile and run passed; request/evaluated rows `5/5`; repair action counts `request_backend_pool_expansion 5`, `route_to_goal_validity_confirmation_after_pool_repair 0`, `defer_source_pool_unresolved 0`; no-valid rows under backend expansion `4`; valid rows under backend expansion `1`; terminal commit rows `0`; action forbidden keys `0`; `source_pool_repair_gate_passed true`; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval backend pool expansion contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_backend_pool_expansion_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_backend_pool_expansion_v1.verify.json` | Contract frozen before implementation | consumes five `request_backend_pool_expansion` rows from `local_dataset/runs/h001_expanded_retrieval_source_pool_repair_v1`; required route actions are `request_backend_candidate_generation`, `route_to_goal_validity_confirmation_after_expansion`, and `defer_backend_pool_unresolved`; expanded candidate counts, new candidate counts, duplicate/reachability counts, and backend config reporting are required; terminal commits remain blocked; label join is evaluation-only; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval backend pool expansion analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_backend_pool_expansion.py` and `local_dataset/runs/h001_expanded_retrieval_backend_pool_expansion_v1/backend_pool_expansion_summary.json` | Docker expansion gate pass, candidate generation required | Docker compile and run passed; request/evaluated rows `5/5`; backend route counts `request_backend_candidate_generation 5`, `route_to_goal_validity_confirmation_after_expansion 0`, `defer_backend_pool_unresolved 0`; existing top-10 paper-scale candidate artifact has expanded candidate count `10` on all rows, below fixed budget minimum `20`; post-expansion label join shows `2` valid-containing rows and `3` no-valid rows under the top-10 preview; terminal commit rows `0`; action forbidden keys `0`; `backend_pool_expansion_gate_passed true`; `goal_validity_confirmation_unblocked false`; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval backend candidate generation contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_backend_candidate_generation_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_backend_candidate_generation_v1.verify.json` | Contract frozen before implementation | consumes five `request_backend_candidate_generation` rows from `local_dataset/runs/h001_expanded_retrieval_backend_pool_expansion_v1`; fixed policy `fixed_action_evidence_top20_v1` uses existing non-GT action evidence and requires exactly `20` generated candidates per row, at least `100` generated candidate rows, candidate lineage, duplicate/reachability/finite-position accounting, terminal commits `0`, action forbidden keys `0`, label join only after generation rows, `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval backend candidate generation analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_backend_candidate_generation.py` and `local_dataset/runs/h001_expanded_retrieval_backend_candidate_generation_v1/backend_candidate_generation_summary.json` | Docker generation gate pass, deeper generation required | Docker compile and run passed; request/evaluated rows `5/5`; generated candidate rows `100`; status counts `generated_fixed_top20_pool 5`, `request_deeper_backend_generation 0`, `defer_backend_candidate_generation_unresolved 0`; generated candidate count `20` on every row; duplicate and nonfinite position counts `0`; reachable/standoff candidate count min `1`; positive support count min/max `3/5`; post-generation label join shows valid-containing rows `2` and no-valid rows `3`; terminal commits `0`; action forbidden keys `0`; `backend_candidate_generation_gate_passed true`; `goal_validity_confirmation_unblocked false`; `deeper_backend_generation_required true`; `uses_gt_for_action false`, `uses_gt_for_analysis true`, `paper_claim_allowed false` |
| Dense conflict expanded retrieval deeper backend generation contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_deeper_backend_generation_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_deeper_backend_generation_v1.verify.json` | Contract frozen before implementation | consumes fixed top-20 generation output as source evidence; diagnostic target rows are the three evaluation-only no-valid rows across two scene/query pairs `QaLdnwvtxbs::bed` and `bxsVRursffK::bed`; first variant `spatial_nms_p90_k100_d5_v1`; requires at least `50` candidates per target request, `100` as the primary target, at least `30` new candidates beyond top-20 per request, and at least `150` generated candidate rows; terminal commits `0`; action forbidden keys `0`; labels must join only after generation rows; `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval deeper backend generation analyzer / existing-artifact smoke | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_deeper_backend_generation.py`, `local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_existing_p97_k20_smoke_v1/deeper_backend_generation_summary.json` | Docker compile and schema smoke pass, superseded by full job | target-spec smoke has source rows `5`, target request rows `3`, scene/query pairs `2`, terminal commits `0`, action forbidden keys `0`, and expected false gate without candidate artifact; existing `p97_k20` smoke has action/evaluated rows `3/3`, generated candidate rows `60`, evaluation labels `60`, candidate count `20` per request, new-beyond-top20 `0`, valid-containing rows `0`, no-valid rows `3`, terminal commits `0`, action forbidden keys `0`, and expected false gate; this smoke validates schema/label separation but not deeper backend recovery |
| Dense conflict expanded retrieval deeper backend generation full job | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_deeper_backend_generation.sh` and `local_dataset/runs/h001_expanded_retrieval_deeper_backend_generation_v1/deeper_backend_generation_summary.json` | completed, gate pass, partial recovery | tmux `h001-deeper-backend-20260529-003000`; artifact coverage `ok true` with `12` scene/query rows, `1200` candidates, `1154` finite-position candidates, scenes `QaLdnwvtxbs` and `bxsVRursffK`; final analyzer has action/evaluated rows `3/3`, generated candidate rows `300`, evaluation labels `300`, candidate count `100` per request, new-beyond-top20 `80` per request, valid-containing rows `2`, still-no-valid rows `1`, terminal commits `0`, action forbidden keys `0`, `deeper_backend_generation_gate_passed true`, and `goal_validity_confirmation_unblocked true`; recovered rows are `rival_identity:12` and `rival_identity:14`, still-no-valid row is `rival_identity:13`; paper claim remains blocked |
| Dense conflict expanded retrieval recovered-row goal-validity confirmation contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_confirmation_v1.verify.json` | Contract frozen before implementation | consumes the three deeper-generation rows; routes only `rival_identity:12` and `rival_identity:14` to goal-validity confirmation evidence; keeps `rival_identity:13` on a backend/pool-validity branch; candidate count `100` per request; terminal commits `0`; action forbidden keys `0`; request/evidence rows must be label-free; `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval recovered-row goal-validity confirmation analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_confirmation.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_confirmation_v1/goal_validity_confirmation_summary.json` | Docker compile and handoff gate pass | request rows `2`, branch rows `1`, candidate evidence target rows `200`, evaluated rows `3`; handoff actions are `request_goal_validity_confirmation_evidence 2` and `request_non_gt_pool_validity_proxy_or_fallback_backend_variant 1`; request ids `rival_identity:12`, `rival_identity:14`; branch id `rival_identity:13`; terminal commits `0`; action forbidden keys `0`; `goal_validity_confirmation_request_gate_passed true`; `uses_gt_for_action false`; `paper_claim_allowed false` |
| Dense conflict expanded retrieval candidate-specific goal-validity evidence planner | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_evidence_v1.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/plan_expanded_retrieval_goal_validity_evidence.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_plan_v1/goal_validity_evidence_plan_summary.json` | Docker compile and plan gate pass | consumes recovered request ids `rival_identity:12` and `rival_identity:14`; objective `candidate_specific_goal_validity_evidence_v1` separates candidate-specific support from category-only visibility and rival ambiguity; Docker plan has request rows `2`, candidate evidence target rows `200`, plan rows `158`, skipped rows `42` all `standoff_navmesh_required`, plan rows by request `79/79`, candidate artifact rows `1`, candidate artifact candidates `80`, terminal commits `0`, output forbidden action fields `0`, `uses_gt_for_action false`, `goal_validity_evidence_plan_gate_passed true`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval candidate-specific goal-validity frame/projection smoke | `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/summary.json`, `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_frames_smoke_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_projection_smoke_v1/projection_anchor_smoke_summary.json` | Docker bounded frame/projection gate pass | first `20` rows exported `20/20` frames with `172` headings, min/max headings `5/11`, one scene, `grounded_position`, and `uses_gt_for_action false`; nonblank filter kept `20/20` rows, removed `0` blank headings, and passed row-level/strict gates; projection smoke has visible rows `20/20`, visible rate `1.0`, missing candidates `0`, revision metadata rows `20`, explicit candidate ids `20`, `projection_anchor_smoke_passed true`, `uses_gt_for_action false`, and `paper_claim_allowed false`; next step is detector/SAM2 substrate |
| Dense conflict expanded retrieval candidate-specific goal-validity detector/SAM2 substrate | `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/job_status.json` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_detector_substrate_smoke_v1/expanded_retrieval_detector_substrate_summary.json` | completed, substrate gate pass | tmux `h001-goal-validity-detector-20260529-171217`; detector rows `20`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `0.95`, rows with candidate association `19`, detector substrate gate `true`, `uses_gt_for_action false`, and `paper_claim_allowed false`; superseded by bounded objective analyzer result below |
| Dense conflict expanded retrieval candidate-specific goal-validity objective analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_objective_v1.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_evidence.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_smoke_v1/goal_validity_objective_summary.json` | Docker diagnostic gate pass, terminal utility blocked | planned request/candidate rows `2/158`; observed detector candidate rows `20`; observed request rows `1/2`; unscored candidate rows `138`; candidate evidence classes `candidate_specific_support 18`, `weak_or_partial_candidate_specific_support 2`, `not_scored_in_bounded_substrate 138`; detector box/SAM2/candidate association `1.0/1.0/0.95`; observed candidate evaluation-only wrong `20/20`; first correct generated rank `34` for recovered requests; action forbidden keys `0`; terminal commits `0`; `objective_analyzer_gate_passed true`; `terminal_utility_validation_allowed false`; `full_detector_substrate_required true`; `paper_claim_allowed false`; superseded by the full-substrate contract below |
| Dense conflict expanded retrieval full candidate-specific detector/SAM2 substrate contract/job | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_full_substrate_v1.verify.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_full_substrate.sh`, and `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md` | completed, substrate gate pass | request rows `2`; plan rows `158`; plan rows by request `79/79`; skipped rows `42`; correct candidates in plan `6`; skipped correct candidates `0`; expected correct ranks `34`, `57`, and `60` for both recovered requests; full frame/projection/detector outputs fixed under `local_dataset/runs/h001_expanded_retrieval_goal_validity_evidence_*_full_v1`; detector image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; tmux `h001-goal-validity-full-substrate-20260529-202640` completed; detector rows `158`; detector box/SAM2/candidate association `1.0/1.0/0.9747`; associated rows `154`; `uses_gt_for_action false`; detector-substrate gate passed; terminal commits and paper claims remain blocked |
| Dense conflict expanded retrieval full candidate-specific goal-validity objective analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_objective_full_v1.verify.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_evidence.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_objective_full_v1/goal_validity_objective_summary.json` | Docker diagnostic gate pass, support saturation blocker | observed request/candidate rows `2/158`; unscored rows `0`; candidate evidence classes `candidate_specific_support 146`, `weak_or_partial_candidate_specific_support 12`; observed evaluation-only correct/wrong `6/152`; bounded comparison improves from `20` observed candidates, `1` request, `138` unscored, and `0` correct to full `158` observed, `2` requests, `0` unscored, and `6` correct; proposed objective defers both rows as `defer_candidate_specific_support_ambiguous`; `semantic_top_observed`, `detector_score_best_observed`, `positive_support_best_observed`, and `candidate_specific_support_best_observed` all commit wrong on both rows; terminal utility and paper claims remain blocked |
| Dense conflict expanded retrieval candidate-specific ambiguity-resolution contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1.verify.json` | Contract frozen before implementation | consumes the full objective analyzer output; treats `146/158` candidate-specific support rows and unsafe simple selectors as the active failure mechanism; requires `support_saturation_profile`, `unsafe_selector_taxonomy`, and `next_evidence_requirement`; blocks detector-score/semantic-rank threshold tuning, terminal commit from support count, and `first_eval` rerun; next script target is `runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_ambiguity.py`; terminal utility and paper claims remain blocked |
| Dense conflict expanded retrieval candidate-specific ambiguity-resolution analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_expanded_retrieval_goal_validity_ambiguity.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_ambiguity_resolution_v1/goal_validity_ambiguity_resolution_summary.json` | Docker diagnostic gate pass, next evidence selected | request/candidate rows `2/158`; candidate-specific support `146/158 = 0.9241`; correct/wrong support `6/140`; correct/wrong support overlap `true`; selector rows `8`, wrong selector rows `8`; wrong selector variants are `semantic_top_observed`, `detector_score_best_observed`, `positive_support_best_observed`, and `candidate_specific_support_best_observed`; action forbidden keys `0`; terminal commits `0`; `ambiguity_diagnostic_gate_passed true`; recommended next actions are `request_discriminative_instance_or_goal_region_evidence`, `request_relation_or_spatial_context_evidence`, then `defer_goal_validity_terminal_policy`; terminal utility and paper claims remain blocked |
| Dense conflict expanded retrieval discriminative instance/goal-region evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1.verify.json` | Contract frozen before implementation | consumes the ambiguity diagnostic output; fixes recovered request rows `rival_identity:12` and `rival_identity:14`; records evaluation-only correct candidates `spatial_nms:33/56/59` and unsafe selector candidates `spatial_nms:0/21/23` only for post-action label join; requires `goal_validity_discriminative_candidate_rows.jsonl`, `goal_validity_discriminative_pair_rows.jsonl`, `goal_validity_discriminative_request_rows.jsonl`, and a summary; blocks threshold tuning, terminal commit, `first_eval` rerun, and policy-scale comparison; next script target is `runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_discriminative_evidence.py`; terminal utility and paper claims remain blocked |
| Dense conflict expanded retrieval discriminative instance/goal-region analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_discriminative_evidence.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_discriminative_evidence_v1/goal_validity_discriminative_evidence_summary.json` | Docker diagnostic gate pass, separability negative | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; request/candidate/pair rows `2/158/420`; candidate-specific support `146`; simple selector candidates `6`; target contrast pair rows after label join `18`; target pairs have contrast visual advantage `8`, selector visual advantage `10`, visual tie `0`; region proxy counts on target pairs are adjacent `12` and distinct `6`; action forbidden keys `0`; terminal commits `0`; `discriminative_evidence_gate_passed true`; conclusion `discriminative_instance_or_goal_region_signal_ready false`; recommended next action `request_relation_or_spatial_context_evidence`; terminal utility and paper claims remain blocked |
| Dense conflict expanded retrieval relation/spatial context evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1.verify.json` | Contract frozen before implementation | consumes the discriminative analyzer output; fixes recovered request rows `rival_identity:12` and `rival_identity:14`; requires action-time candidate, pair, and request context rows before evaluation label join; target contrast pairs are `18`, with visual split `contrast 8` vs `selector 10` and region split `adjacent 12` / `distinct 6`; required diagnostics are spatial component profile, relation-to-anchor profile, evaluation-only context separability probe, and next evidence requirement; blocks direct commit, threshold tuning, `first_eval` rerun, policy-scale comparison, terminal utility validation, and paper claims; next script target is `runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_relation_spatial_context.py` |
| Dense conflict expanded retrieval relation/spatial context analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_relation_spatial_context.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_relation_spatial_context_v1/goal_validity_relation_spatial_context_summary.json` | Docker diagnostic gate pass, static context negative | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; request/candidate/pair rows `2/158/420`; spatial context groups `8`; target contrast pair rows `18`; target pair component relation counts are `same_component 12`, `distinct_component 6`; target context score delta is `contrast_context_higher 18`; failure taxonomy counts are `same_component_selector_visual_dominates 10`, `same_component_context_not_discriminative 2`, and `context_candidate_for_followup 6`; action forbidden keys `0`; terminal commits `0`; `relation_spatial_context_gate_passed true`; `relation_spatial_context_signal_ready false`; recommended next action `request_scene_graph_or_object_relation_evidence`; paper claims remain blocked |
| Dense conflict expanded retrieval scene-graph/object-relation evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1.verify.json` | Contract frozen before implementation | consumes the relation/spatial context analyzer output; fixes recovered request rows `rival_identity:12` and `rival_identity:14`; focuses on same-component selector failures with target contrast pairs `18`, same-component target pairs `12`, and same-component selector-visual-dominates rows `10`; requires action-time candidate, pair, request, and context-object relation rows before evaluation label join; forbids GT scene graph, GT room, correctness, success, and wrong-goal labels for action rows; blocks direct commit, threshold tuning, `first_eval` rerun, policy-scale comparison, terminal utility validation, and paper claims; next script target is `runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_scene_graph_object_relation.py` |
| Dense conflict expanded retrieval scene-graph/object-relation analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_scene_graph_object_relation.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_scene_graph_object_relation_v1/goal_validity_scene_graph_object_relation_summary.json` | Docker diagnostic gate pass, coverage repair required | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; request/candidate/pair/context-object rows `2/158/420/7788`; target contrast pair rows `18`; same-component target pairs `12`; same-component selector-visual rows `10`; target relation delta `contrast_relation_higher 18`; relation separability probe supports signal `true`; relation coverage complete `true`; detector coverage complete `false`; rows with detector association are `77/79` for each recovered request; action forbidden keys `0`; terminal commits `0`; `scene_graph_object_relation_gate_passed true`; `scene_graph_object_relation_signal_ready false`; recommended next action `request_object_relation_observation`; paper claims remain blocked |
| Dense conflict expanded retrieval object-relation coverage repair contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1.verify.json` | Contract frozen before implementation | consumes the scene-graph/object-relation analyzer output; source gate is true but signal ready is false; fixes the action-time coverage gap to four rows, candidate ids `vlmaps:export:bed:spatial_nms:5` and `vlmaps:export:bed:spatial_nms:90` for both recovered requests; rows with detector association are `77/79` per request; evaluation-only check reports missing-detector correct rows `0` and missing-detector target-pair rows `0`, but these are analysis-only; requires coverage-gap rows, repair/waiver action rows, request coverage rows, and evaluated coverage-gap rows after label join; blocks direct commit, threshold tuning, `first_eval` rerun, policy-scale comparison, terminal utility validation, and paper claims; next script target is `runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_coverage_repair.py` |
| Dense conflict expanded retrieval object-relation coverage repair analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_coverage_repair.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_coverage_repair_v1/goal_validity_object_relation_coverage_repair_summary.json` | Docker diagnostic gate pass, observation plan required | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; coverage gap rows `4`; repair action rows `4`; request-object-relation-observation rows `2`; waiver rows `2`; request coverage rows `2`; evaluated coverage gap rows `4`; evaluation-only missing-detector candidate-valid rows `0`; evaluation-only missing-detector target-pair rows `0`; action forbidden keys `0`; terminal commits `0`; `coverage_repair_gate_passed true`; next action `freeze_object_relation_observation_plan_contract`; terminal utility and paper claims remain blocked |
| Dense conflict expanded retrieval object-relation observation plan contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1.verify.json` | Contract frozen before implementation | consumes the coverage repair analyzer output; fixes `object_relation_depth_recheck_standoff_v1`; observation targets are `spatial_nms:5` for `rival_identity:12` and `rival_identity:14`; `spatial_nms:90` rows stay as terminal-policy-promotion waivers; minimum plan rows `8`; minimum plan rows per request `4`; relation-anchor candidates per plan minimum `2`; next script target is `runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py`; Docker required; terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Dense conflict expanded retrieval object-relation observation planner | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_plan_v1/goal_validity_object_relation_observation_plan_summary.json` | Docker plan gate pass, frame/projection smoke required | Docker image `research3/habitat-h001:20260508-calib-artifacts`; output has plan rows `8`, skipped rows `0`, request rows `rival_identity:12 = 4` and `rival_identity:14 = 4`, relation-anchor candidates per plan min/mean/max `8/8/8`, direction sources `source_viewpoint_to_target`, `target_to_relation_anchor`, `relation_anchor_to_target`, and `orthogonal_relation_axis`, candidate artifact rows `1`, forbidden action fields `0`, terminal commits `0`, `uses_gt_for_action false`, `paper_claim_allowed false`, and `object_relation_observation_plan_gate_passed true`; next artifact gate is frame/projection smoke |
| Dense conflict expanded retrieval object-relation observation frame/projection smoke | `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_frames_v1/summary.json`, `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_frames_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_projection_v1/projection_anchor_smoke_summary.json` | Docker frame/nonblank/projection gate pass | Docker image `research3/habitat-h001:20260508-calib-artifacts`; frame export rows `8/8`, rendered headings `72`, headings per row `9/9`, one scene, `grounded_position`, explicit candidate ids with `9` candidates per row, and preserved `goal_validity_*` / `object_relation_*` metadata; nonblank filter keeps `8/8` rows and removes `0` blank headings; projection smoke has visible rows `8/8`, visible rate `1.0`, missing candidates `0`, revision metadata rows `8`, explicit candidate ids `8`, `projection_anchor_smoke_passed true`, `uses_gt_for_action false`, and `paper_claim_allowed false`; next artifact gate is detector/SAM2 substrate |
| Dense conflict expanded retrieval object-relation observation detector substrate | `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1/job_status.json`, `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1/detector_v3c/summary.json`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_observation_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json` | Docker detector substrate gate pass, post-detector analyzer contract frozen below | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; log `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/object-relation-detector-substrate-20260530-092542.log`; frame rows `8`; detector rows `8`; detector box rate `1.0`; SAM2 mask rate `1.0`; candidate association rate `1.0`; rows with candidate association `8/8`; associated candidate heading count `48`; association rows `72`; detector boxes/masks `110/110`; projection status counts `visible 58`, `out_of_fov 14`; selected candidate source `explicit_candidate_ids 8`; projection anchor policy `projection_anchor_height_sweep_v1 8`; `uses_gt_for_action false`; `paper_claim_allowed false`; `passes_detector_substrate_gate true`; next gate is analyzer implementation, not terminal utility |
| Dense conflict expanded retrieval object-relation post-detector evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1.verify.json` | Contract frozen before analyzer implementation | consumes the object-relation observation plan, projection, detector substrate, and detector association rows; fixes `object_relation_detector_depth_evidence_v1`; requires nonterminal evidence rows, request rows, evaluation-only rows after label join, and summary; expected request/plan/detector/association rows are `2/8/8/72`; minimum associated heading count `40`, minimum depth-consistent rows `32`; source status has depth counts `consistent 44`, `depth_mismatch 14`, `out_of_fov 14`; blocks direct commit, detector-association best commit, relation-signature best commit, threshold tuning, `first_eval` rerun, policy-scale comparison, terminal utility, and paper claims; next script target is `runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py` |
| Dense conflict expanded retrieval object-relation post-detector evidence analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py` and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_evidence_v1/goal_validity_object_relation_evidence_summary.json` | Docker diagnostic gate pass, terminal utility still blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; output has evidence/request/evaluation rows `8/2/2`, association rows `72`, detector rows `8`, associated heading count `48`, depth status `consistent 44`, `depth_mismatch 14`, `out_of_fov 14`; request evidence status `relation_depth_recheck_resolved 2`; evaluation-only candidate correctness is `false 2`; action forbidden keys `0`; terminal commits `0`; `object_relation_evidence_gate_passed true`; `paper_claim_allowed false`; next gate is interpretation/terminal-blocking, not `first_eval` rerun |
| Dense conflict expanded retrieval object-relation interpretation gate | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_interpretation_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_interpretation_v1.verify.json` | Interpretation frozen, terminal utility still blocked | consumes the Docker-verified post-detector evidence analyzer output; freezes the result as nonterminal coverage/depth repair because `relation_depth_recheck_resolved 2` are both evaluation-negative after label join; rejects `relation_depth_resolved_commit`, box/mask presence commit, and high-association-count commit; action forbidden keys `0`; terminal commits `0`; `uses_gt_for_action false`; `paper_claim_allowed false`; next contract requires a non-GT goal-validity arbitration rule that can reject resolved-but-negative repeated-object candidates before terminal utility |
| Dense conflict expanded retrieval object-relation arbitration rule | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1.json`, verify file, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_arbitration.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_v1/object_relation_arbitration_summary.json` | Docker bounded smoke pass, terminal utility still blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; decision/evaluated rows `2/2`; action `reject_relation_depth_resolved_without_independent_candidate_support 2`; evaluation-only rejected negative rows `2`; support saturation eligible candidates `73/79` per row; action forbidden keys `0`; terminal commits `0`; `object_relation_arbitration_rule_gate_passed true`; `terminal_utility_validation_allowed false`; `paper_claim_allowed false`; next gate is fresh/predeclared validation before any terminal contract |
| Dense conflict expanded retrieval object-relation arbitration fresh source | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1.json`, verify file, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_arbitration_fresh_source_v1/object_relation_arbitration_fresh_source_summary.json` | Docker source precheck pass, evidence generation required | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; source/evaluated rows `7/7`; request ids `rival_identity:3/5/7/22/25/27/29`; scenes/queries `5/3`; candidate rows `36`; detector-strong candidates `28`; bounded arbitration overlap `0`; action forbidden keys `0`; terminal commits `0`; `fresh_source_precheck_gate_passed true`; `object_relation_arbitration_validation_ready false`; next gate is fresh object-relation observation/evidence generation for these route-specific rows |
| Dense conflict expanded retrieval object-relation fresh observation plan | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1.json`, verify file, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_observation_inputs.py`, reused planner `runtime/h001_runtime/plan_expanded_retrieval_goal_validity_object_relation_observation.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1/goal_validity_object_relation_observation_plan_summary.json` | Docker planner gate pass, frame/projection smoke passed below | Input builder on `research3/openvocab-perception:20260513-v3c-gdino-sam2` passes with target/repair/context rows `36/36/152`, missing plan rows `0`, candidate positions missing `0`, action forbidden keys `0`; Habitat planner on `research3/habitat-h001:20260508-calib-artifacts` passes with plan rows `144`, skipped rows `0`, plan rows by request `16-24`, candidate artifact rows/candidates `5/26`, action forbidden keys `0`, terminal commits `0`, `uses_gt_for_action false`, and `object_relation_observation_plan_gate_passed true`; run `/opt/conda/bin/python` in this image |
| Dense conflict expanded retrieval object-relation fresh frame/projection smoke | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_frame_projection_v1.verify.json`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_frame_projection.sh`, `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1/summary.json`, `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1/nonblank_filter_v1/nonblank_frame_filter_summary.json`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1/projection_anchor_smoke_summary.json` | Docker frame/nonblank/projection gate pass, detector/SAM2 substrate next | Docker image `research3/habitat-h001:20260508-calib-artifacts`; wrapper uses `/opt/conda/bin/python`, defaults to `--gpus all`, and chmods output roots; final log `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/fresh-object-relation-frame-projection-20260531-000459.log`; status file `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_projection_v1/frame_projection_job_status.json`; frame rows/headings `144/576`; nonblank rows/headings `144/573`; removed blank headings `3` from `bxsVRursffK/plant`; row-level nonblank gate `true`; strict no-blank gate `false`; projection visible rows `141/144`; visible rate `0.9792`; missing candidates `0`; GT action rows `0`; `projection_anchor_smoke_passed true`; `uses_gt_for_action false`; `paper_claim_allowed false`; next gate is detector/SAM2 substrate, not terminal utility |
| Dense conflict expanded retrieval object-relation fresh detector/SAM2 substrate | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate.sh`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_detector_substrate.sh`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_detector_substrate_v1.verify.json`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json` | Docker/GPU detector substrate gate pass | tmux `h001-fresh-object-relation-detector-20260531-013027`; image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; log `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/logs/fresh-object-relation-detector-substrate-20260531-013027.log`; frames `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_frames_v1/nonblank_filter_v1/rival_identity_frame_summary_nonblank.jsonl`; candidate artifact `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_plan_v1/goal_validity_object_relation_observation_candidate_artifact.jsonl`; expected rows `144`; expected policy `ExpandedRetrievalGoalValidityObjectRelationObservation`; output `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1`; detector rows `144`; detector box/SAM2/candidate association `0.9583/0.9583/0.8264`; rows with candidate association `119/144`; associated candidate heading count `338`; association rows `573`; detector boxes/masks `906/906`; GT action rows `0`; `passes_detector_substrate_gate true`; verification command `cat local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/job_status.json && cat local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_observation_detector_substrate_v1/expanded_retrieval_detector_substrate_summary.json` |
| Dense conflict expanded retrieval object-relation fresh post-detector evidence | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1.json`, verify file, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/build_expanded_retrieval_goal_validity_object_relation_fresh_labels.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_goal_validity_object_relation_evidence.py`, and `local_dataset/runs/h001_expanded_retrieval_goal_validity_object_relation_fresh_evidence_v1/goal_validity_object_relation_evidence_summary.json` | Docker evidence gate pass, fixed-rule arbitration next | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; label rows `36` from fresh source evaluation summaries, correct/wrong `11/25`; evidence output request/evidence/association rows `36/108/573`; associated candidate heading count `338`; depth consistent/mismatch/out-of-FOV `321/223/12`; evidence status `relation_depth_recheck_resolved 24`, `relation_depth_recheck_partial 12`; evaluation-only interpretation `resolved positive 3`, `resolved negative 21`, `partial 12`; action forbidden keys `0`; terminal commits `0`; `object_relation_evidence_gate_passed true`; `uses_gt_for_action false`; `paper_claim_allowed false`; next gate is fixed-rule arbitration validation, not terminal utility |
| Dense conflict expanded retrieval pool-validity branch fallback contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_pool_validity_branch_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_pool_validity_branch_v1.verify.json` | Contract frozen before implementation | consumes the single backend/pool-validity branch row `rival_identity:13`; rejects simple candidate count/reachability/support/score-shape proxy readiness because the still-no-valid pool has `100` candidates, `100` reachable/standoff candidates, `5` positive-support candidates, zero duplicate/nonfinite candidates, and high scores; first fallback variant fixed to `spatial_nms_p80_k200_d3_v1`, second fallback `components_p80_min1_k200_v1`; terminal commits `0`; action forbidden keys `0`; labels must join only after fallback generation rows; `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval pool-validity branch analyzer/job | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_branch.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_pool_validity_branch.sh`, and `local_dataset/runs/h001_expanded_retrieval_pool_validity_branch_v1/pool_validity_summary.json` | completed, structural gate pass, still no-valid | Docker target-spec smoke has branch/action/evaluated rows `1/1/1`, target `rival_identity:13`, scene/query `bxsVRursffK::bed`, expected status `defer_pool_validity_fallback_unresolved` because artifact is missing, terminal commits `0`, action forbidden keys `0`, proxy rejection reported `true`, and `pool_validity_fallback_gate_passed false`; tmux `h001-pool-validity-fallback-20260529-093033` completed command `TS=20260529-093033 bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_pool_validity_branch.sh`; artifact coverage `ok true` with `1` scene, `6` query rows, `1200` candidates, and `1200` finite-position candidates; final output has fallback candidate rows `200`, new-beyond-previous `100`, terminal commits `0`, action forbidden keys `0`, `pool_validity_fallback_gate_passed true`, but `evaluation_only_contains_valid_rows 0`, `evaluation_only_no_valid_rows 1`, `goal_validity_confirmation_unblocked false`, and `second_fallback_backend_required true`; next branch is `components_p80_min1_k200_v1` |
| Dense conflict expanded retrieval pool-validity second fallback contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_expanded_retrieval_pool_validity_second_fallback_v1.verify.json` | Contract frozen before implementation | consumes the same single `rival_identity:13` no-valid branch after the structurally valid `spatial_nms_p80_k200_d3_v1` fallback; fixes `components_p80_min1_k200_v1` as the component-level backend; requires component candidate count, `component_cells`, backend-source counts, duplicate/nonfinite/reachability accounting, and overlap reporting against both previous spatial-NMS pools; terminal commits remain `0`; action forbidden keys must remain `0`; labels may join only after component generation rows; `uses_gt_for_action false`, `uses_gt_for_analysis true`, and `paper_claim_allowed false` |
| Dense conflict expanded retrieval pool-validity second fallback analyzer/job | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_expanded_retrieval_pool_validity_second_fallback.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_pool_validity_second_fallback.sh`, and `local_dataset/runs/h001_expanded_retrieval_pool_validity_second_fallback_v1/second_fallback_summary.json` | completed, structural gate pass, still no-valid | Docker target-spec smoke has branch/action/evaluated rows `1/1/1`, target `rival_identity:13`, scene/query `bxsVRursffK::bed`, expected status `defer_component_fallback_unresolved` because artifact is missing, terminal commits `0`, action forbidden keys `0`, first fallback structural/no-valid gates true, and `second_fallback_gate_passed false`; tmux `h001-pool-validity-second-fallback-20260529-151217` completed command `TS=20260529-151217 bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/expanded_retrieval_pool_validity_second_fallback.sh`; artifact coverage `ok true` with `1` scene, `6` query rows, `1163` candidates, and `1163` finite-position candidates; final output has component candidate rows `200`, component cell stats min/mean/max `1/20.29/1254`, new positions beyond first fallback `200`, terminal commits `0`, action forbidden keys `0`, `second_fallback_gate_passed true`, but `evaluation_only_contains_valid_rows 0`, `evaluation_only_no_valid_rows 1`, `goal_validity_confirmation_unblocked false`, and `backend_source_map_blind_spot_after_second_fallback true` |
| Dense conflict repeated-object relation-anchor consistency detector evidence analyzer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_repeated_object_relation_anchor_consistency_evidence.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1.verify.json`, and `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_detector_evidence_v1/relation_anchor_consistency_detector_evidence_summary.json` | Docker evidence gate pass, no promotable branch outcome | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; output has view/pair/candidate/request rows `27/27/9/3`, detector association rows `360`, target association by role `candidate_own_view 6/9`, `relation_anchor_context_view 9/9`, `orthogonal_axis_challenge_view 9/9`, context association by role `candidate_own_view 3/9`, `relation_anchor_context_view 0/9`, `orthogonal_axis_challenge_view 0/9`; candidate statuses `ambiguous_repeated_object_candidate 6` and `insufficient_candidate_evidence 3`; promotable branch outcome rows `0`; action forbidden keys `0`; terminal commits `0`; candidate commit/rejection `0/0`; `uses_gt_for_action false`; `paper_claim_allowed false`; next gate is residual diagnosis, not terminal utility |
| Dense conflict repeated-object relation-anchor consistency residual diagnostic | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_repeated_object_relation_anchor_consistency_residual.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_repeated_object_relation_anchor_consistency_residual_diagnostic_v1.verify.json`, and `local_dataset/runs/h001_repeated_object_relation_anchor_consistency_residual_diagnostic_v1/relation_anchor_consistency_residual_summary.json` | Docker residual gate pass, branch closed without promotion | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; output has candidate/request rows `9/3`; residual classes `own_view_context_leakage 3`, `same_request_stable_rule_tie 3`, and `missing_own_view_target_support 3`; request status `same_request_stable_tie_with_own_view_context_leakage 3`; stable-rule candidate count `2` per request; promotable branch outcome rows `0`; action forbidden keys `0`; terminal commits `0`; candidate commit/rejection `0/0`; `uses_gt_for_action false`; `paper_claim_allowed false`; next gate is `association_geometry_underlink` repair-followup evidence contract |
| Semantic-SLAM map/pose consistency source audit | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/audit_semantic_slam_map_pose_consistency_sources.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_map_pose_consistency_probe_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_map_pose_consistency_probe_v1/semantic_slam_map_pose_consistency_probe_summary.json` | Docker source audit and P4 proxy readiness gates pass | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; source inventory/probe request/pose graph proxy rows `5/50/50`; source-ready rows `5`; primary source ready `true`; pose/depth/metadata ready `true`; pose graph proxy ready rows `50`; max nodes/edges `24/236`; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; Step 4-5 promotion and paper claims remain blocked |
| Semantic-SLAM pose graph connectivity proxy gate | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/evaluate_semantic_slam_pose_graph_connectivity_proxy_gate.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_pose_graph_connectivity_proxy_gate_v1/semantic_slam_pose_graph_connectivity_proxy_gate_summary.json` | Docker proxy gate pass, strict edge ablation required | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; gate rows `13`; pose graph proxy rows/ready rows `50/50`; source family count `5`; primary source proxy rows `9`; spatial/loop/spatial-or-loop edge rows `46/36/46`; candidate-overlap-only rows/rate `4/0.08`; candidate-overlap edge share `0.5746`; dependency/proxy plumbing/edge quality/action safety gates pass; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; Step 4-5 promotion, policy comparison, terminal utility, and paper claims remain blocked |
| Semantic-SLAM strict edge variant proxy | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_semantic_slam_strict_edge_variants.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_strict_edge_variant_proxy_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_strict_edge_variant_proxy_v1/semantic_slam_strict_edge_variant_proxy_summary.json` | Docker strict variant gate pass, comparison contract allowed | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; variant rows/summary rows `350/7`; request groups `50`; source family count `5`; canonical `pose_spatial_or_loop` ready rows/rate `46/0.92`; canonical min source ready rate `0.8095`; `map_pose_context_no_candidate` ready rows/rate `46/0.92`; `pose_loop` ready rows/rate `36/0.72`; `candidate_overlap_only` ready rows/rate `50/1.0`; dependency/strict-edge/action-safety gates pass; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; comparison contract is allowed, but comparison run, Step 4-5 promotion, terminal utility, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM proxy comparison contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_proxy_comparison_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_proxy_comparison_v1.verify.json` | Frozen contract, implementation verified separately | fixes same `50` request groups, policies `NoReobserveReference`, `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM`, join key `(source_name, scene_key, query, request_id, episode_key)`, canonical pose variant `pose_spatial_or_loop`, expected rows `200`, fixed semantic weights, utility formulas, metric/output schema, and blocked task-behavior metrics; Docker implementation is recorded in the next row; Step 4-5 promotion, terminal utility, candidate commit/rejection, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM proxy comparison implementation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/compare_semantic_slam_proxy_policies.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_proxy_comparison_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_proxy_comparison_v1/semantic_slam_proxy_comparison_summary.json` | Docker proxy comparison gate pass, Step 4-5 promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; comparison/policy summary rows `200/4`; request groups `50`; same request groups gate `true`; canonical/loop proxy ready rates `0.92/0.72`; policy utility means `NoReobserveReference 0.0`, `SemanticOnly 0.6092`, `SLAMOnly 0.3871`, `SemanticSLAM 0.4981`; rank-1 rows/rates `SemanticOnly 36/0.72`, `SLAMOnly 14/0.28`, `SemanticSLAM 0/0.0`; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM proxy comparison output evaluation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/evaluate_semantic_slam_proxy_comparison_output.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_proxy_comparison_output_evaluation_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_proxy_comparison_output_evaluation_v1/semantic_slam_proxy_comparison_output_evaluation_summary.json` | Docker output evaluation gate pass, superseded by non-dominated redesign | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; group evaluation rows `50`; component winners `SemanticOnly 36/0.72` and `SLAMOnly 14/0.28`; all `50/50` request groups are `semantic_slam_midpoint_strictly_dominated_by_best_component`; midpoint identity max abs error `1.11e-16`; best-component margin over `SemanticSLAM` min/mean/max `0.0159/0.1536/0.3995`; output evaluation gate `true`; Step 4-5 promotion and paper claims remain blocked; superseded by the non-dominated and reviewer-defense proxy sequence |
| Semantic-SLAM non-dominated proxy redesign contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_non_dominated_proxy_redesign_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_non_dominated_proxy_redesign_v1.verify.json` | Frozen contract, implementation completed | Contract defines `SemanticSLAMInteraction` after prior midpoint dominance `50/50`; policies `NoReobserveReference`, `SemanticOnly`, `SLAMOnly`, `SemanticSLAMInteraction`; forbids midpoint/linear-only interpolation, component-max shortcut, constant bonus scale trick, and label-tuned weight search; requires semantic pressure and map/pose pressure interaction; expected future rows `200`; requires non-dominated diagnostic rows; minimum non-dominated interaction rows/rate `10/0.2`; action forbidden keys, terminal commit, candidate commit, and candidate rejection must remain `0`; implementation is recorded in the next row; Step 4-5 promotion and paper claims remain blocked |
| Semantic-SLAM non-dominated proxy implementation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/compare_semantic_slam_non_dominated_proxy.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_non_dominated_proxy_redesign_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_non_dominated_proxy_redesign_v1/semantic_slam_non_dominated_proxy_redesign_summary.json` | Docker redesign proxy gate pass, output evaluation completed | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; comparison/policy summary/diagnostic rows `200/4/50`; policy rank-1 rows/rates `SemanticSLAMInteraction 42/0.84`, `SLAMOnly 8/0.16`, `SemanticOnly 0/0.0`, `NoReobserveReference 0/0.0`; non-dominated interaction rows/rate `42/0.84`; interaction-positive rows `50`; midpoint identity rows `0`; component-max shortcut rows `0`; component reference rank-1 rows `8`; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; Step 4-5 promotion and paper claims remain blocked |
| Semantic-SLAM non-dominated proxy output evaluation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/evaluate_semantic_slam_non_dominated_proxy_output.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_non_dominated_proxy_output_evaluation_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_non_dominated_proxy_output_evaluation_v1/semantic_slam_non_dominated_proxy_output_evaluation_summary.json` | Docker integrity gate pass, reviewer-defense gate fail | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; group evaluation rows `50`; rank-1 rows/rates `SemanticSLAMInteraction 42/0.84`, `SLAMOnly 8/0.16`, `SemanticOnly 0/0.0`; `SemanticSLAMInteraction` strictly exceeds `SemanticOnly` on `50/50` groups; diagnostic classes `semantic_first_bonus_shadows_semantic_only 36`, `interaction_overrides_slam_component 6`, `interaction_loses_to_component 8`; output integrity gate `true`; reviewer-defense gate `false`; Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM reviewer-defense contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_reviewer_defense_contract_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_reviewer_defense_contract_v1.verify.json` | Frozen contract, implementation recorded separately | Contract freezes `NoReobserveReference`, `SemanticOnly`, `SLAMOnlyRich`, and `SemanticSLAMInteractionGuarded` on the same `50` request groups; primary path is richer SLAM/outcome-linked proxy, guard path is stricter non-shadowing cap, promotion path is task/map outcome validation; forbids `SemanticOnly + nonnegative bonus` on every row, cap-only contribution, component-max shortcut, candidate-overlap pose evidence, and label-tuned weight search; requires map/pose terms `fragmentation_score`, `largest_component_gap`, `loop_gap`, `source_coverage_gap`, and `context_gap`; Docker implementation is recorded in the next row; Step 4-5 promotion and paper claims remain blocked |
| Semantic-SLAM reviewer-defense implementation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/compare_semantic_slam_reviewer_defense_proxy.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_reviewer_defense_contract_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_reviewer_defense_v1/semantic_slam_reviewer_defense_summary.json` | Docker implementation pass, reviewer-defense gate fail | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; comparison/policy summary/diagnostic rows `200/4/50`; request groups `50`; rank-1 rows/rates `SemanticSLAMInteractionGuarded 37/0.74`, `SemanticOnly 10/0.20`, `SLAMOnlyRich 3/0.06`, `NoReobserveReference 0/0.0`; `SemanticOnly` shadowed rows/rate `40/0.80`; map-pose explained interaction rows/rate `40/0.80`; unexplained positive bonus rows `0`; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; reviewer-defense gate fails because `SLAMOnlyRich` rank-1 rows `3 < 5`; Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM reviewer-defense output evaluation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/evaluate_semantic_slam_reviewer_defense_output.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_reviewer_defense_output_evaluation_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_reviewer_defense_output_evaluation_v1/semantic_slam_reviewer_defense_output_evaluation_summary.json` | Docker output evaluation complete, primary blocker identified | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; evaluation rows `50`; action-safety and comparison gates pass; reviewer-defense output gate fails with primary blocker `slam_only_rich_underpowered`; `SLAMOnlyRich` rank-1 rows/required/deficit `3/5/2`; blocker classes `semantic_wins_but_guarded_interaction_adds_small_map_pose_bonus 29`, `semantic_wins_with_weak_map_pose_proxy 17`, `slam_only_wins_but_insufficient_count 3`, `interaction_overrides_slam_component 1`; `slam_minus_semantic_utility` min/mean/max `-0.84/-0.3230/0.1483`; Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM `SLAMOnlyRich` underpowered diagnostic | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_semantic_slam_slam_only_rich_underpowered.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_slam_only_rich_underpowered_diagnostic_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_slam_only_rich_underpowered_diagnostic_v1/semantic_slam_slam_only_rich_underpowered_diagnostic_summary.json` | Docker diagnostic complete, formula change blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile and run passed; diagnostic/query/scene rows `50/6/9`; diagnostic gate passes; rank-1 rows/rates `SLAMOnlyRich 3/0.06`, `SemanticOnly 10/0.20`, `SemanticSLAMInteractionGuarded 37/0.74`; dominant causes `map_pose_terms_saturated 19`, `weak_map_pose_proxy 17`, `near_miss_scale 8`, `positive_slam_cases_too_sparse 3`, `mixed_or_request_pool_effect 3`; saturated map-pose term rows/rate `46/0.92`; weak map-pose proxy rows/rate `17/0.34`; primary conclusion `semantic_score_dominates_current_map_pose_proxy`; secondary conclusion `map_pose_terms_often_saturated_or_weak_without_task_map_outcome`; formula change, Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM `SLAMOnlyRich` revision contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_slam_only_rich_revision_contract_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_slam_only_rich_revision_contract_v1.verify.json` | Frozen contract, outcome probe and task proxy join completed but formula still blocked | Static manifest/verify JSON; captures source `SLAMOnlyRich` rank-1 `3/50`, saturated map-pose term rows `46/50`, weak map-pose proxy rows `17/50`, and primary cause `semantic_score_dominates_current_map_pose_proxy`; forbids scale-only tuning, semantic score weakening, request-pool tuning, candidate-overlap pose evidence, GT action labels, and proxy-only terminal claims; revised formula implementation remains blocked because the candidate-specific task proxy join is safe-but-sparse with `SLAMOnlyRich_current` terminal/map-task-alignment rows `3/2` |
| Semantic-SLAM task/map outcome probe implementation | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/evaluate_semantic_slam_task_map_outcome_probe.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_task_map_outcome_probe_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_task_map_outcome_probe_v1/semantic_slam_task_map_outcome_probe_summary.json` | Docker implementation pass, outcome gate fail | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run/artifact validation passed; output has probe/policy/failure rows `150/3/50` on the same `50` request groups; required baselines `NoReobserveReference`, `SemanticOnly`, and `SLAMOnlyRich_current`; `SLAMOnlyRich_current` map-positive rows `50/50`; label-backed task proxy rows `0/50`; label-free risk proxy rows `50/50`; map-task alignment rows `0`; failure taxonomy `map_delta_not_task_aligned 50` and secondary `task_proxy_label_join_missing 50`; action forbidden keys `0`; terminal/candidate commit/rejection `0/0/0`; `uses_gt_for_action false`; `outcome_probe_gate_passed false`; `revised_slam_formula_allowed false`; Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM task label join materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_task_label_join.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_task_label_join_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_task_label_join_v1/semantic_slam_task_label_join_summary.json` | Docker materializer pass, outcome proxy gate fail | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output request/candidate/policy/failure rows `21/113/150/150`; candidate labels correct/wrong/unlabeled `37/76/0`; no-valid request pools `4`; label backbone join rows `150`; candidate label join rows `150`; action forbidden keys `0`; `uses_gt_for_action false`; `task_label_join_gate_passed true`; `outcome_proxy_gate_passed false` because `policy_selector_missing_rows 150` and `task_proxy_evaluable_rows 0`; revised `SLAMOnlyRich` formula, Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM task policy selector materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_task_policy_selector.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_task_policy_selector_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_task_policy_selector_v1/semantic_slam_task_policy_selector_summary.json` | Docker materializer pass, candidate-specific SLAM selector contract required next | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run/artifact validation passed; selector/failure rows `150/60`; `NoReobserveReference` terminal commit proxy rows `49/50`; `SemanticOnly` terminal commit proxy rows `41/50`; `SemanticOnly` local-context/own-view commit sources `23/18`; `SLAMOnlyRich_current` selector-missing rows `50/50`; total terminal/defer/selector-missing rows `90/10/50`; action forbidden keys `0`; `uses_gt_for_action false`; `selector_contract_gate_passed true`; `partial_task_proxy_join_after_selector_allowed true`; revised `SLAMOnlyRich` formula, Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked until a candidate-specific SLAM/map-pose selector contract exists |
| Semantic-SLAM candidate map-pose selector materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_map_pose_selector.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_map_pose_selector_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_candidate_map_pose_selector_v1/semantic_slam_candidate_map_pose_selector_summary.json` | Docker materializer pass, followed by task proxy join | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run/artifact validation passed; candidate/request/failure rows `232/50/50`; `SLAMOnlyRich_current` request rows `50`; selector-missing rows `0`; candidate geometry missing rows `0`; strict candidate-map-pose-ready rows `232`; geometry-only single-candidate commit rows `3`; multi-ready defer rows `47`; action forbidden keys `0`; `uses_gt_for_action false`; `candidate_map_pose_feature_gate_passed true`; follow-up task proxy join passed but formula revision remains blocked because `SLAMOnlyRich_current` is sparse |
| Semantic-SLAM candidate task proxy join materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_task_proxy_join.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_task_proxy_join_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_candidate_task_proxy_join_v1/semantic_slam_candidate_task_proxy_summary.json` | Docker materializer pass, formula revision unlock fail | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run/artifact validation passed; policy/failure rows `150/100`; decision-evaluable rows `150`; commit-evaluable rows `93`; selector-missing rows `0`; `NoReobserveReference` terminal/success/wrong rows `49/28/21`; `SemanticOnly` terminal/success/wrong rows `41/20/21`; `SLAMOnlyRich_current` terminal/success/wrong/defer/map-task-alignment rows `3/2/1/47/2`; action forbidden keys `0`; `uses_gt_for_action false`; `uses_gt_for_analysis true`; task proxy join gate passed; formula revision unlock gate failed with primary blocker `slam_only_terminal_commits_too_sparse`; revised `SLAMOnlyRich` formula, Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM safe-but-sparse selector diagnostic | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/diagnose_semantic_slam_safe_sparse_selector.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_safe_sparse_selector_diagnostic_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_safe_sparse_selector_diagnostic_v1/semantic_slam_safe_sparse_selector_summary.json` | Docker diagnostic pass, candidate separability gate fail | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run/artifact validation passed; request/alternative rows `50/300`; candidate/source rows `232/50`; current unique-ready selector commit/success/wrong/defer rows `3/2/1/47`; `top_map_pose_tuple` and `top_projection_visible_heading` both commit all `50` rows but produce success/wrong/no-valid rows `29/21/4`; all source requests have all candidates strict map-pose-ready; multi-candidate all-ready rows `47`; action forbidden keys `0`; `uses_gt_for_action false`; diagnostic gate passed; candidate separability gate failed with primary blocker `label_free_geometry_alternatives_reintroduce_wrong_goal_risk`; discriminative candidate map/pose revision, revised `SLAMOnlyRich` formula, Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked |
| Semantic-SLAM geometry-only closure and candidate-relative requirements | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_geometry_only_closure_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_geometry_only_closure_v1.verify.json` | Static contract pass, superseded by candidate-relative chain | Static `jq` verification; consumes safe-but-sparse diagnostic counts; closes `geometry_only_SLAMOnlyRich_current_selector` as non-promotable; source request/candidate rows `50/232`; all-candidates-ready rows `50`; multi-candidate all-ready rows `47`; current unique-ready selector commit/success/wrong/defer `3/2/1/47`; `top_map_pose_tuple` and `top_projection_visible_heading` success/wrong/no-valid `29/21/4`; action forbidden keys `0`; `uses_gt_for_action false`; follow-up candidate-relative evidence, task proxy join, path closure, and active-observation contract are now recorded below |
| Semantic-SLAM candidate-relative map/pose evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_map_pose_evidence_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_map_pose_evidence_v1.verify.json` | Contract plus Docker materializer verified | Static source verification freezes `232` candidate rows, `50` request groups, `43` candidate ids, `50` request-level pose graph rows, `350` strict edge variant rows, and `300` safe-sparse alternative rows; allowed fields are candidate geometry, request-level map/pose context, pose graph proxy, and strict edge variants; semantic/detector/source-top/local-context fallbacks, evaluation labels, terminal commits, candidate rejection, formula revision, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims remain blocked |
| Semantic-SLAM candidate-relative map/pose evidence materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_relative_map_pose_evidence.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_map_pose_evidence_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_candidate_relative_map_pose_evidence_v1/semantic_slam_candidate_relative_map_pose_evidence_summary.json` | Docker materializer gate pass, promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output candidate/request/alternative/failure rows `232/50/450/50`; candidate ids/request groups `43/50`; all-ready candidate rows `232`; pose graph and strict edge context rows `50/50`; candidate-overlap-only request rows `4`; candidate-relative unique-top/tie/single request rows `42/5/3`; action forbidden keys, terminal commits, candidate commits, and candidate rejections `0`; materializer gate passed; promotion blocked with `task_side_proxy_not_joined_for_terminal_utility`; its follow-up gate is now frozen as the candidate-relative task proxy join contract |
| Semantic-SLAM candidate-relative task proxy join materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_relative_task_proxy_join.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_task_proxy_join_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_candidate_relative_task_proxy_join_v1/semantic_slam_candidate_relative_task_proxy_summary.json` | Docker materializer pass, promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run/artifact validation passed; output candidate/request/alternative/baseline/failure rows `232/50/450/150/50`; source-row request/candidate label missing rows `0/0`; source candidate correct/wrong/no-valid rows `84/148/24`; top map-pose candidate correct/wrong/no-valid rows `29/21/4`; candidate-relative unique-top correct/wrong/no-valid rows `23/19/4`; task proxy join gate passed; promotion gate failed with `candidate_relative_top_rule_wrong_goal_risk`; terminal utility, formula revision, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims remain blocked |
| Semantic-SLAM candidate-relative path closure | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_path_closure_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_path_closure_v1.verify.json` | Static closure pass, active-observation contract required next | Static `jq` verification; consumes Docker task proxy join summary; closes `candidate_relative_map_pose_top_rule_as_terminal_selector` as non-promotable; candidate/request/alternative/baseline/failure rows `232/50/450/150/50`; label missing rows `0/0`; top map-pose correct/wrong/no-valid rows `29/21/4`; candidate-relative unique-top correct/wrong/no-valid rows `23/19/4`; primary blocker `candidate_relative_top_rule_wrong_goal_risk`; surviving role is active-observation or uncertainty diagnosis; formula revision, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims remain blocked |
| Semantic-SLAM candidate-relative active-observation utility contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_active_observation_utility_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_active_observation_utility_v1.verify.json` | Static contract pass, Docker materializer completed below | Static `jq` verification; consumes the candidate-relative path closure and task proxy join counts; allowed actions are `observe_candidate`, `observe_candidate_pair`, `observe_request_context`, `defer_observation`, and `audit_only`; implementation script is `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_utility.py`; output root is `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_utility_v1`; terminal commits, candidate commits/rejections, formula revision, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims remain blocked |
| Semantic-SLAM candidate-relative active-observation utility materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_utility.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_active_observation_utility_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_utility_v1/semantic_slam_candidate_relative_active_observation_utility_summary.json` | Docker materializer gate pass, promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output priority/request/alternative/failure rows `232/50/300/50`; request action counts `observe_request_context 21`, `observe_candidate_pair 26`, `observe_candidate 3`; candidate action counts `observe_request_context 113`, `observe_candidate_pair 52`, `observe_candidate 19`, `audit_only 48`; terminal commits, candidate commits/rejections, GT-action rows, paper-claim rows, and forbidden action keys `0`; materializer gate passed; promotion blocked with `task_proxy_join_after_active_observation_action_freeze_required`; follow-up active-observation task-proxy join contract is frozen below |
| Semantic-SLAM candidate-relative active-observation task-proxy join contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.verify.json` | Static contract pass, Docker materializer required next | Static `jq` verification; consumes active-observation priority/request/alternative/failure rows `232/50/300/50`; fixes selected candidate eval rows `97`, alternative audit-selected rows `100`, task label request/candidate rows `21/113`, and candidate task-proxy policy rows `150`; allows only evaluation-only labels/proxies after action freeze; blocks terminal commits, candidate commits/rejections, label-tuned action changes, formula revision, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims |
| Semantic-SLAM candidate-relative active-observation task-proxy join materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_candidate_relative_active_observation_task_proxy_join.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_candidate_relative_active_observation_task_proxy_join_v1/semantic_slam_candidate_relative_active_observation_task_proxy_summary.json` | Docker materializer gate pass, promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output priority/selected/request/alternative/baseline/failure rows `232/97/50/300/150/50`; request, priority candidate, selected candidate, and alternative audit-candidate label missing rows `0/0/0/0`; selected candidate labels correct/wrong/no-valid `43/54/8`; baseline wrong-goal proxy rows `NoReobserveReference 21`, `SemanticOnly 21`, `SLAMOnlyRich_current 1`; terminal commits, candidate commits/rejections, GT-action rows, paper-claim rows, and action forbidden keys `0`; join gate passed; promotion blocked with `active_observation_task_proxy_join_is_evaluation_only`; next step is risk-profile analysis before any terminal-utility contract |
| Semantic-SLAM active-observation risk analysis | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_semantic_slam_active_observation_risk.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_active_observation_risk_analysis_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_active_observation_risk_analysis_v1/active_observation_risk_analysis_summary.json` | Docker analysis gate pass, terminal utility blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output request/candidate/rule audit rows `50/232/6`; selected request status all-correct/mixed/all-wrong/no-valid `11/23/12/4`; selected candidate clean-correct/wrong-or-no-valid `43/54`; direct top-observation terminal shortcut success/wrong/no-valid `16/30/4`; top-selected terminal shortcut `19/27/4`; risk analysis gate passed; primary blocker `top_observation_utility_terminal_shortcut_unsafe`; terminal utility, formula revision, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims remain blocked |
| Semantic-SLAM active-observation post-observation evidence update contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_active_observation_post_update_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_active_observation_post_update_v1.verify.json` | Static contract pass, Docker materializer completed | Static `jq` verification; consumes risk request/candidate/rule audit rows `50/232/6`, selected candidate rows `97`, selected request statuses `11/23/12/4`, selected candidate clean-correct/wrong-or-no-valid rows `43/54`, and terminal shortcut audits `16/30/4` and `19/27/4`; requires post-update request/selected-candidate/candidate-state rows `50/97/232`; allows only label-free evidence state update before evaluation label join; blocks terminal commits, candidate commits/rejections, formula revision, terminal utility, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims |
| Semantic-SLAM active-observation post-observation evidence update materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_active_observation_post_update.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_active_observation_post_update_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_active_observation_post_update_v1/active_observation_post_update_summary.json` | Docker materializer gate pass, promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output request/selected-candidate/candidate-state/rule-audit/failure rows `50/97/232/6/50`; selected candidate and candidate-state evidence delta rows `97/97`; request post-update states `ambiguity_reduced 26`, `needs_goal_validity_confirmation 21`, `support_acquired 3`; selected candidate post states `ambiguity_reduced 52`, `needs_goal_validity_confirmation 42`, `support_acquired 3`; terminal commits, candidate commits/rejections, GT-action rows, paper-claim rows, and action forbidden keys `0`; materializer gate passed; promotion blocked with `post_update_label_join_and_goal_validity_arbitration_required`; follow-up post-update evaluation join materializer is completed below |
| Semantic-SLAM active-observation post-update evaluation join materializer | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/materialize_semantic_slam_active_observation_post_update_evaluation_join.py`, `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_active_observation_post_update_evaluation_join_v1.verify.json`, and `local_dataset/runs/h001_semantic_slam_active_observation_post_update_evaluation_join_v1/active_observation_post_update_evaluation_join_summary.json` | Docker join gate pass, promotion blocked | Docker image `research3/openvocab-perception:20260513-v3c-gdino-sam2`; Docker compile/run passed; output request/selected-candidate/candidate-state/baseline/failure rows `50/97/232/150/50`; goal-validity/viewpoint/map-pose join rows `50/50/50`; wrong-goal/wasted-path proxy evaluable rows `150/150`; map-pose delta evaluable rows `50`; request goal-validity states clean-correct/mixed/no-valid/wrong-risk `11/23/4/12`; baseline wrong-goal rows `NoReobserveReference 21`, `SemanticOnly 21`, `SLAMOnlyRich_current 1`; terminal commits, candidate commits/rejections, GT-action rows, paper-claim rows, and action forbidden keys `0`; join gate passed; promotion blocked with `evaluation_join_only_nonterminal_goal_validity_arbitration_required`; follow-up task/map evidence contract is frozen below |
| Semantic-SLAM task/map evidence contract | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_task_map_evidence_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_semantic_slam_task_map_evidence_v1.verify.json` | Static contract pass, promotion blocked | Static `jq` verification; consumes the Docker-verified post-update evaluation join rows `50/97/232/150/50`; fixes `ObjectNav` wrong-goal and wasted path as task-level failure surfaces of `Semantic-SLAM` uncertainty; keeps map/pose consistency as a separate evidence axis; requires same-row `goal_validity_risk`, `viewpoint_evidence_gap`, `map_pose_consistency_uncertainty`, wrong-goal, wasted-path, and map/pose delta fields; blocks terminal utility, formula revision, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims; follow-up reviewer-defense baseline matrix is frozen below |
| Reviewer-defense baseline matrix | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_reviewer_defense_baseline_matrix_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_reviewer_defense_baseline_matrix_v1.verify.json` | Static contract pass, promotion blocked | Static `jq` verification; consumes the task/map evidence contract; defines core task controls, active-observation controls, `Semantic-SLAM` component controls, related-work style references, oracle references, and simpler alternatives; requires `NoReobserveReference`, `SemanticOnly`, `SLAMOnly`, `SemanticSLAMInteraction`, `RandomReobserve`, `FrontierReobserve`, `CARe`-style confidence replanning, `VLFM`-style semantic frontier, and `OneMap`-style semantic memory before paper claim; separates `GTTargetOracle`, `GTCandidateOracle`, and `GTViewOracle` from deployable baselines; follow-up active re-observation promotion gate is frozen below |
| Active re-observation promotion gate | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_active_reobservation_promotion_gate_v1.json` and `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_active_reobservation_promotion_gate_v1.verify.json` | Static contract pass, promotion not satisfied | Static `jq` verification; consumes the task/map evidence contract and reviewer-defense baseline matrix; requires wrong-goal and wasted-path reduction against fixed baselines without map/pose degradation; preserves same-row, same-budget, no-GT-action comparison; keeps oracle references diagnostic; forbids post-hoc metric, threshold, baseline, or label fitting; blocks terminal utility, formula revision, `first_eval`, policy-scale comparison, Step 4-5 promotion, and paper claims until a future label-free branch satisfies the gate |

### 에이전트 추론

현재 positive signal은 semantic uncertainty를 `commit/defer` threshold가 아니라 active observation / active SLAM utility contract로 바꾸는 방향에서 나온다. Semantic object evidence route는 source-pool repair, object-relation, missing-own-view, instance-arbitration, pair-graph, residual branches까지 따라갔지만 promotable terminal outcome은 `0`이다. Semantic-SLAM proxy route는 midpoint utility, semantic-first additive utility, and guarded reviewer-defense utility를 차례로 reject하거나 block했고, frozen `SLAMOnlyRich` revision contract는 scale-only tuning을 금지한다. Candidate-specific task proxy join removes the selector-missing measurement blocker, and the safe-but-sparse diagnostic shows why formula revision remains blocked: simple geometry-only map/pose alternatives reintroduce `21` wrong-goal rows and `4` no-valid commits. `semantic_slam_geometry_only_closure_v1` closes that path as non-promotable, and the candidate-relative materializer shows relative map/pose contrast exists without action leakage. The candidate-relative task-side proxy join passes coverage but blocks promotion with `candidate_relative_top_rule_wrong_goal_risk`, and the closure now blocks the direct top-rule terminal-selector path. The candidate-relative active-observation utility materializer writes frozen nonterminal observation actions, the post-action task-proxy join materializer validates full evaluation-only risk coverage after action freeze, the risk analysis rejects the direct terminal shortcut, the post-update materializer writes explicit label-free evidence state deltas, the post-update evaluation join connects those rows to `goal_validity_risk`, `viewpoint_evidence_gap`, `map_pose_consistency_uncertainty`, wrong-goal, wasted path, and map/pose deltas, the task/map evidence contract freezes this interpretation, the reviewer-defense baseline matrix fixes the required comparison families, and the active re-observation promotion gate fixes the natural-proof and numeric promotion requirements. The reproducible next step is terminal utility definition only after a future label-free branch satisfies this gate. Step 4-5 promotion, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked.

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
- Selected-wrong `plant` rows는 correct candidate가 이미 follow-up/context 안에 있으므로 현재 blocker는 retrieval pool 크기보다 second-stage target selection이다. Semantic-neighbor target rule 구현 및 detector-backed smoke 전까지 `first_eval`와 policy-scale은 blocked다.
- Semantic-neighbor target rule은 planner/frame substrate와 detector-backed full GPU rerun까지 통과했다.
- Detector-backed semantic-neighbor validation은 local integrated gate를 통과했지만, `validation_scope v4_semantic_neighbor_diagnostic`이므로 utility proof가 아니다. `first_eval`와 policy-scale은 계속 blocked다.
- Full GPU rerun 기준 remaining blocker는 detector substrate가 아니라 `request_further_identity_confirmation_strong_rival_supported 3`, `request_further_identity_confirmation_selected_not_strong_in_own_view 1`, `defer_identity_selected_local_cluster_too_small 1`로 남은 evidence/action decision path다.
- Row-level diagnosis에서 selected-wrong `plant` 3개 row의 correct semantic-neighbor candidate는 present이지만 weak하다. Correct `spatial_nms:1`은 `S_ext ~0.483`, strong depth `false`이고, wrong selected/rival candidates는 `S_ext ~0.783/0.784`, strong depth `true`다.
- Semantic-neighbor multiview planner/frame smoke와 focused detector-backed validation은 완료됐다. Multiview는 correct semantic-neighbor evidence acquisition을 회복했지만 terminal utility는 아직 만들지 못했다.
- Semantic-prior strong-tie arbitration V3는 full V4 diagnostic에서 terminal utility를 만들었다. 다만 diagnostic scope이므로 utility proof가 아니며, scene-disjoint held-out validation 전까지 `first_eval`와 policy-scale은 계속 blocked다.
- Duplicate-goal/category-region row는 main ObjectNav GT success rule과 분리한다. 별도 goal-region metric이 정의되기 전에는 main utility proof에 포함하지 않는다.
- Held-out Objective V2 validation job은 2026-05-19에 완료됐고 scene-disjoint check를 통과했다. Safety gate는 통과했지만 commit/success가 `0/5`라 full gate와 utility proof는 실패했다.
- Candidate-set expansion diagnostic 기준으로 current detector/evidence follow-up set은 정답 후보를 `1/5`만 보존하지만, follow-up plan explicit set과 V4 external set은 `3/5`를 보존한다.
- `detect_postview_groundingdino_sam2.py`는 2026-05-19에 explicit frame `candidate_ids`를 우선 쓰도록 수정됐다.
- Explicit-candidate held-out validation job은 2026-05-19에 완료됐다. Detector candidate-set mismatch는 해결됐지만 모든 row가 `defer_identity_ambiguous_rival_supported`로 남았다.
- Identity ambiguity diagnostic은 threshold-only revision을 지지하지 않는다. `3/5` rows에는 correct candidate가 있지만 supported wrong rival와 contrastive하게 분리되지 않는다.
- Identity resolution design diagnostic에서 `selected_local_cluster_margin`은 same-split design 기준으로 success `1/5`, wrong-goal `0/5`를 만들지만, 아직 paper claim이나 first_eval rerun 근거는 아니다.
- Follow-up evidence V4로 `selected_local_cluster_margin`을 fixed non-GT objective로 구현했다. Explicit-candidate held-out diagnostic은 full gate를 통과했지만, separate `v3_fresh_validation_v1`은 safety만 통과하고 utility는 만들지 못했다.
- V4 request-identity bottleneck diagnostic 기준으로 first-stage selected direct commit은 wrong-goal `3/7`이라 안전하지 않다. Existing second-stage identity objective V2는 success `2/7`, wrong-goal `0/7`의 nonzero safe utility를 만든다.
- V4 + second-stage identity V2 terminal diagnostic은 same V4 separate-split substrate에서 local integrated full gate를 통과했다. 그러나 `validation_scope v4_fixed_terminal_diagnostic`이라 `utility_proof_passed false`로 기록한다.
- Dense terminal arbitration diagnostic은 two-row `y9hTuugGdiq/chair` local diagnostic에서 positive였지만 all positive-support candidates가 post-hoc correct라 wrong-goal repair proof가 아니다.
- Independent dense conflict validation design은 `runtime/workflow-20260521-dense-conflict.md`에 고정했다. `manifests/h001_dense_conflict_v1.json`과 dense recall gate는 Docker 검증을 통과했다. Host/Docker NVIDIA runtime은 2026-05-23에 복구됐다. `spatial_nms_p95_k100_d10`과 `spatial_nms_p90_k200_d5` final recall gate는 모두 실패했다. Selected `v3_fresh_spatial_p97_k20` primary diagnostic과 held-out `sofa` secondary-stress diagnostic은 recall과 detector/association gate를 통과했다. Broader `dense_conflict_generalization_v1`도 candidate recall과 detector substrate gate를 통과했다. Frozen `strict_depth_consistency_v1` validation은 same-split 기준 v0 wrong commits를 막았지만 independent validation에서 reject됐다. Failure diagnosis는 saturated same-category rival ambiguity를 dominant mechanism으로 고정했다. `rival_identity_confirmation_v1` diagnostic policy는 local gate를 통과했고, active observation/evaluation contract, plan smoke, frame export smoke, detector substrate gate, post-observation evidence/validation contract, analyzer smoke, fresh-source design, fresh-source freeze, fresh-source planner smoke, fresh-source frame smoke, and fresh-source detector substrate도 통과했다. Fresh-source post-observation gate initially failed with wrong-goal commit `2`. Failure diagnostic과 taxonomy split은 두 wrong commit이 single-positive-candidate `toilet` object-existence false positive임을 확인했고, multi-positive rows는 rival-identity arbitration에 남겼다. Object-existence no-commit branch는 fresh-source gate를 통과시켰고, independent object-existence probe는 current source에서 wrong-goal avoided by defer `2`, success lost `0`을 확인했다. Broader source design, source miner, row-level frame substrate, and corrected detector substrate는 `risk_validation` 기반으로 통과했다. Broader post-observation fixed rule은 safe but inert result를 냈고, failure diagnostic은 원인이 zero-standoff planner geometry임을 확인했다. Zero-standoff-safe planner smoke는 geometry gate를 통과했고, mixed-standoff frame gate 실패 후 navmesh-only standoff frame/nonblank gate와 detector substrate도 통과했다. Own-view category evidence가 valid `ObjectNav` goal identity를 보장하지 못한다는 unsafe commit failure가 진단됐고, `goal_validity_arbitration_v1`은 diagnostic split에서 이를 repair했다. Independent source에서는 `goal_validity_arbitration_v1`이 safe-but-inert로 실패했고 default counterfactual은 unsafe였다. `discriminative_rival_view_planner_v1` v2 frame/nonblank와 detector/SAM2 substrate는 통과했지만 `discriminative_rival_view_evidence_v1` diagnostic gate와 failure diagnostic이 threshold tuning과 fresh validation을 막았다. `request_expanded_retrieval` branch를 우선하는 결정은 내려졌고 planner smoke, analysis-only label join, full-pool taxonomy, analysis-only candidate-set guard design, non-GT proxy feature extraction, source-pool validity proxy, detector standoff frame gate, projection-anchor smoke, fixed-anchor detector substrate, fresh expanded-retrieval source freeze, fresh proxy/plan/frame gates, fresh detector/SAM2 substrate, fresh detector evidence diagnostic, ambiguity-aware objective contract, paper-scale source freeze, paper-scale detector plan, paper-scale upper-anchor frame/projection smoke, paper-scale detector/SAM2 substrate, detector evidence diagnostic, ambiguity objective application, local-context branch routing, source-pool repair, backend expansion analyzer, backend candidate generation contract, backend candidate generation analyzer, deeper backend generation contract, deeper backend generation full job, and recovered-row request/branch analyzer까지 통과하거나 구현/frozen 상태다. 이후 semantic object terminal branches는 promotable outcome `0`으로 닫혔고, semantic-SLAM source audit, pose graph connectivity proxy gate, strict edge variant proxy gate, proxy comparison contract, proxy comparison implementation, proxy output evaluation, non-dominated proxy redesign contract, `SemanticSLAMInteraction` implementation, redesigned output evaluation, reviewer-defense contract freeze, reviewer-defense implementation, reviewer-defense output evaluation, `SLAMOnlyRich` underpowered diagnostic, `SLAMOnlyRich` revision contract, task/map outcome probe implementation, task label join materializer, task policy selector contract/materializer, candidate-specific SLAM selector, candidate task proxy join, safe-but-sparse diagnostic, geometry-only closure, candidate-relative map/pose evidence materializer, candidate-relative task proxy join, candidate-relative path closure, active-observation contract, active-observation materializer, active-observation task-proxy join contract/materializer, active-observation risk analysis, active-observation post-update contract/materializer, active-observation post-update evaluation join materializer, Semantic-SLAM-centered task/map evidence contract, reviewer-defense baseline matrix, and active re-observation promotion gate까지 Docker 검증 또는 freeze를 통과했다. 현재 reproducible next step은 이 gate를 만족하는 label-free branch가 생긴 뒤 terminal utility contract를 정의하는 것이다.

### 에이전트 추론

Full follow-up job은 detector/rendering substrate가 충분한지 확인했지만, V1 `commit_expanded_candidate_after_followup`가 no-valid/wrong-goal commit을 만들었다. V2는 large repeated furniture direct commit을 막아 risk split safety를 복구했지만, fresh split에서는 `plant` small_or_cluttered visible distractor를 wrong-goal로 commit했다. V3는 compact-object expanded retrieval도 identity confirmation으로 넘겨 safety를 복구한다. V3 second-stage는 detector substrate와 safety를 통과했지만 모든 request를 further confirmation으로 남겼다. Objective V2는 same-artifact diagnostic에서 nonzero utility를 만들었지만 scene-disjoint held-out에서는 utility proof에 실패했다. Detector association이 plan의 explicit candidate set을 쓰지 않았던 harness mismatch는 수정됐다. 그 결과 correct candidate 보존은 `3/5`까지 회복됐지만, supported rival들이 동시에 강하게 관측되어 current objective는 안전하게 defer한다. Semantic-neighbor target rule은 candidate-viewpoint substrate를 고쳤고 full GPU detector-backed run에서도 substrate gate를 통과했다. Multiview focused job은 selected-wrong `plant` rows에서 correct semantic-neighbor strong-depth evidence를 회복했으므로, 남은 문제는 evidence acquisition이 아니라 semantic prior와 detector/depth strong tie를 결합한 arbitration objective다. 단순 threshold 완화는 supported wrong rival를 같이 통과시킬 위험이 있어 현재 근거로는 부적합하다. `selected_local_cluster_margin`은 spatially local duplicate-goal case 하나를 안전하게 회복하는 fixed objective 후보이지만, duplicate-goal/category-region은 main ObjectNav GT contract와 분리한다. Policy-scale comparison은 여전히 blocked다.

Follow-up evidence V4는 이 후보를 실제 analyzer objective로 고정했고 held-out diagnostic에서는 성공했지만, separate split에서는 대부분 expanded retrieval row가 `request_identity_confirmation`으로 남았다. 따라서 다음 단계는 first_eval rerun이 아니라 V4 separate-split request-identity bottleneck을 진단하고, second-stage identity evidence, category-level goal-region commit, broader retrieval/backend expansion 중 어느 축이 utility를 만들 수 있는지 분리하는 것이다.

V4 request-identity bottleneck diagnostic 결과, 바로 가능한 안전한 utility 회복 경로는 second-stage identity objective V2를 V4 terminal decision에 통합하는 것이다. 다만 이것은 `2/7` 회복에 그치며, selected-wrong `plant` rows는 correct candidate가 follow-up set에는 있어도 strong detector/depth support를 받지 못하므로 broader retrieval 또는 candidate-viewpoint revision이 별도 필요하다. Category-level goal-region commit은 현재 GT wrong-goal label과 충돌하는 row가 있어 paper metric contract를 바꾸지 않는 한 main path로 쓰지 않는다.

V4 terminal diagnostic과 semantic-neighbor detector-backed run은 이 통합 경로가 local method contract로는 안전하다는 것을 확인했다. Multiview semantic-neighbor acquisition은 correct candidate evidence를 strong으로 만들었지만, wrong selected/rival candidates도 strong이라 objective V2는 여전히 defer한다. 다음 작업은 broader retrieval보다 먼저 semantic-prior strong-tie arbitration objective를 설계하는 것이다.

최신 dense path 기준으로는, 같은-goal correct cluster에서 성공한 local chair diagnostic을 확장 주장으로 쓰지 않는다. 현재 reproducible next step은 `active_reobservation_promotion_gate_v1`을 만족하는 label-free branch가 생긴 뒤 terminal utility contract를 정의하는 것이다.
