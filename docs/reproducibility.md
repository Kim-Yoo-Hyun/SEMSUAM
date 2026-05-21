# Reproducibility

이 문서는 H001 실험을 다시 실행하기 위한 데이터, checkpoint, Docker, artifact, evaluation entrypoint를 모은다. 세부 실험 해석은 `hypothesis/CAND-01/H001_uncertainty-reobservation/04_first_experiment.md`와 `08_runtime_integration.md`를 따른다.

## Status

### 사실

- Date checked: 2026-05-22
- Primary hypothesis: `H001_uncertainty-reobservation`
- Runtime root: `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/`
- Local dataset root: `local_dataset/`
- Data root: `local_dataset/data` (`/tmp/research3-data` compatibility symlink)
- Run artifact root: `local_dataset/runs` (`/tmp/research3-runs` compatibility symlink)
- Model root: `local_dataset/models` (`/tmp/research3-models` compatibility symlink)
- Logs: `logs/`
- Host Python은 문서/사전 점검에만 사용한다. Smoke test와 논문 본문용 실험은 Docker 기반으로 실행한다.
- 개인 credential은 repo에 저장하지 않는다.
- 다른 컴퓨터 재현을 위한 GitHub source-of-truth는 code, Dockerfile, job script, manifest, workflow 문서, reproducibility 문서다.
- 대용량 dataset, checkpoint, Docker image layer, `local_dataset/runs` artifact는 GitHub source-of-truth가 아니다. 이 문서의 다운로드/빌드/검증 명령으로 복구한다.
- `/tmp/research3-data`, `/tmp/research3-models`, `/tmp/research3-runs`는 기존 Docker command 호환을 위해 `local_dataset/` 아래 canonical path로 연결된 symlink다.

### 에이전트 추론

재현 정보는 기존 workflow와 job script에 흩어져 있었고, 데이터 다운로드, checkpoint, Docker image, 실험 명령, artifact/evaluation summary가 한 문서로 닫혀 있지는 않았다. 이 문서를 재현 entrypoint로 사용한다.

## GitHub Portability Check

### 사실

Date checked: 2026-05-22

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

Date checked: 2026-05-22

Current local footprint:

```text
local_dataset/data:   42G
local_dataset/models: 5.8G
local_dataset/runs:   3.6G
```

`.gitignore` intentionally excludes `local_dataset/`, data, runs, models, checkpoints, paper PDFs, large archives/arrays/model files, and credentials.

Compatibility symlinks:

```text
/tmp/research3-data   -> /home/yoohyun/research3/local_dataset/data
/tmp/research3-models -> /home/yoohyun/research3/local_dataset/models
/tmp/research3-runs   -> /home/yoohyun/research3/local_dataset/runs
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

Date checked: 2026-05-22

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
```

보존 이유:

- 재생성은 가능하지만 detector GPU run, `VLMaps` dense re-export, failure taxonomy 분석을 다시 거쳐야 한다.
- 논문 주장으로 아직 확정된 evidence는 아니지만, novelty 판단과 다음 gate 설계의 provenance로 중요하다.
- `local_dataset/runs/h001_dense_conflict_artifacts_spatial_nms_p95_k100_d10_v1/`는 현재 `status: failed`이고 크기도 작으므로 Drive 1순위가 아니다. NVIDIA runtime 복구 후 재생성한다.

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

6. Regenerate artifacts and evaluations using the job scripts in `Reproduction Commands` and the current `TODO.md`. Current blocker is the NVIDIA runtime recovery followed by:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-dense-conflict-artifact-${ts}" \
  "cd /home/yoohyun/research3 && TS=${ts} bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh"
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

### NVIDIA Runtime Recovery Checklist

Use this checklist when a GPU job fails before container startup. Do not treat this as experiment evidence.

Current known failure on 2026-05-21:

```text
nvidia-smi: Failed to initialize NVML: Driver/library version mismatch
kernel_module: 580.126.09
user_space_library: 580.159.03
docker_gpu_error: open /run/nvidia-persistenced/socket: no such file or directory
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

Dense conflict resume command:

```bash
ts=$(date +%Y%m%d-%H%M%S)
tmux new-session -d -s "h001-dense-conflict-artifact-${ts}" \
  "cd /home/yoohyun/research3 && TS=${ts} bash hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh"
```

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
| Independent dense conflict validation manifest / recall gate | `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_v1.json` | implemented, Docker verified | added `build_dense_conflict_manifest.py` and `probe_dense_conflict_recall.py`; manifest verify output `manifests/h001_dense_conflict_v1.verify.json` has `ok true`, `rows 8`, `unique_episode_keys 8`; existing-artifact recall gate smoke `/tmp/research3-runs/h001_dense_conflict_recall_gate_existing_artifact_smoke_v1` passes on primary rows with `6/6` correct candidates and recall@20 `1.0`; this is gate-code validation, not final dense backend evidence |
| Dense conflict `spatial_nms_p95_k100_d10` artifact job | `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/jobs/dense_conflict_candidate_artifact.sh` | blocked by host GPU runtime | scene spec `manifests/dense_conflict_v1_scenes.txt`; first launch `h001-dense-conflict-artifact-20260521-175656`; log `runtime/logs/dense-conflict-artifact-p95-k100-d10-20260521-175656.log`; failed before scene export because Docker `--gpus all` cannot initialize NVIDIA runtime; `nvidia-smi` reports driver/library mismatch: kernel module `580.126.09`, user-space library `580.159.03`; resume after host driver/runtime is fixed |

### 에이전트 추론

현재 positive signal은 semantic uncertainty를 `commit/defer` threshold가 아니라 `request_identity_confirmation`과 `request_expanded_retrieval` 같은 active observation contract로 바꾸는 방향에서 나온다. 아직 paper claim은 확정하지 않는다. Fresh detector rerun은 V2가 compact object distractor에 취약하다는 새 failure mechanism을 확인했고, V3/V4는 이 failure를 safety repair로 막지만 separate split utility proof는 아직 없다. `first_eval` replacement rerun과 policy-scale comparison은 V4 separate-split request-identity bottleneck을 해결하기 전까지 계속 blocked다.

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
- Independent dense conflict validation design은 `runtime/workflow-20260521-dense-conflict.md`에 고정했다. `manifests/h001_dense_conflict_v1.json`과 dense recall gate는 Docker 검증을 통과했다. `spatial_nms_p95_k100_d10` artifact job wrapper도 준비했지만, host NVIDIA driver/library mismatch로 첫 launch가 실패했다. 다음 blocker는 host NVIDIA runtime 복구 후 artifact job resume과 final recall gate이며, detector scoring은 그 이후에만 진행한다.

### 에이전트 추론

Full follow-up job은 detector/rendering substrate가 충분한지 확인했지만, V1 `commit_expanded_candidate_after_followup`가 no-valid/wrong-goal commit을 만들었다. V2는 large repeated furniture direct commit을 막아 risk split safety를 복구했지만, fresh split에서는 `plant` small_or_cluttered visible distractor를 wrong-goal로 commit했다. V3는 compact-object expanded retrieval도 identity confirmation으로 넘겨 safety를 복구한다. V3 second-stage는 detector substrate와 safety를 통과했지만 모든 request를 further confirmation으로 남겼다. Objective V2는 same-artifact diagnostic에서 nonzero utility를 만들었지만 scene-disjoint held-out에서는 utility proof에 실패했다. Detector association이 plan의 explicit candidate set을 쓰지 않았던 harness mismatch는 수정됐다. 그 결과 correct candidate 보존은 `3/5`까지 회복됐지만, supported rival들이 동시에 강하게 관측되어 current objective는 안전하게 defer한다. Semantic-neighbor target rule은 candidate-viewpoint substrate를 고쳤고 full GPU detector-backed run에서도 substrate gate를 통과했다. Multiview focused job은 selected-wrong `plant` rows에서 correct semantic-neighbor strong-depth evidence를 회복했으므로, 남은 문제는 evidence acquisition이 아니라 semantic prior와 detector/depth strong tie를 결합한 arbitration objective다. 단순 threshold 완화는 supported wrong rival를 같이 통과시킬 위험이 있어 현재 근거로는 부적합하다. `selected_local_cluster_margin`은 spatially local duplicate-goal case 하나를 안전하게 회복하는 fixed objective 후보이지만, duplicate-goal/category-region은 main ObjectNav GT contract와 분리한다. Policy-scale comparison은 여전히 blocked다.

Follow-up evidence V4는 이 후보를 실제 analyzer objective로 고정했고 held-out diagnostic에서는 성공했지만, separate split에서는 대부분 expanded retrieval row가 `request_identity_confirmation`으로 남았다. 따라서 다음 단계는 first_eval rerun이 아니라 V4 separate-split request-identity bottleneck을 진단하고, second-stage identity evidence, category-level goal-region commit, broader retrieval/backend expansion 중 어느 축이 utility를 만들 수 있는지 분리하는 것이다.

V4 request-identity bottleneck diagnostic 결과, 바로 가능한 안전한 utility 회복 경로는 second-stage identity objective V2를 V4 terminal decision에 통합하는 것이다. 다만 이것은 `2/7` 회복에 그치며, selected-wrong `plant` rows는 correct candidate가 follow-up set에는 있어도 strong detector/depth support를 받지 못하므로 broader retrieval 또는 candidate-viewpoint revision이 별도 필요하다. Category-level goal-region commit은 현재 GT wrong-goal label과 충돌하는 row가 있어 paper metric contract를 바꾸지 않는 한 main path로 쓰지 않는다.

V4 terminal diagnostic과 semantic-neighbor detector-backed run은 이 통합 경로가 local method contract로는 안전하다는 것을 확인했다. Multiview semantic-neighbor acquisition은 correct candidate evidence를 strong으로 만들었지만, wrong selected/rival candidates도 strong이라 objective V2는 여전히 defer한다. 다음 작업은 broader retrieval보다 먼저 semantic-prior strong-tie arbitration objective를 설계하는 것이다.

최신 dense path 기준으로는, 같은-goal correct cluster에서 성공한 local chair diagnostic을 확장 주장으로 쓰지 않는다. 다음 검증은 correct/wrong candidates가 동시에 positive support를 받는 independent conflict rows에서 dense backend recall, detector association, terminal arbitration을 순서대로 분리해 확인하는 것이다.
