# Stage 1 Smoke Test

## Why This Stage Is Needed

### 사실

- `CAND-01`의 first probe는 `VLMaps` / Habitat-style pre-explored semantic map에서 object/node uncertainty를 얻고, re-observation policy를 평가하는 것이다.
- Host Python은 3.12이고, `VLMaps`는 older Python / dependency stack을 요구한다.
- 연구 운영 규칙상 smoke test와 논문 본문용 implementation experiment는 Docker 기반으로 진행한다.

### 에이전트 추론

Stage 1 smoke test의 목적은 full experiment가 아니라 최소 실행 가능성 확인이다. 먼저 `VLMaps` demo/custom scene에서 map output과 object-goal navigation logging path가 실제로 생성되는지 확인하고, MP3D/HM3D는 dataset access와 mount path가 준비된 뒤 연결한다.

## Linked Research Item

- Candidate: `literature/CAND-01.md`
- Hypothesis: `hypothesis/CAND-01/H001_uncertainty-reobservation/`
- First experiment: `hypothesis/CAND-01/H001_uncertainty-reobservation/04_first_experiment.md`

## Scope

### In Scope

- Docker 기반 `VLMaps` smoke test workflow 정의
- Dataset mount rule 정의
- GPU / Docker health check 정의
- 성공 / 실패 gate 정의

### Out of Scope

- Full Habitat ObjectNav benchmark 실행
- MP3D/HM3D 전체 다운로드
- `CARe` exact reproduction
- SLAM backend integration
- 논문 본문용 결과 생성

## Docker Rule

### 사실

- Smoke test는 Docker로 실행한다.
- Host Python은 사용하지 않는다.
- Docker GPU option, base image, dataset mount, command는 이 문서 또는 이후 experiment workflow에 기록한다.

### 에이전트 추론

First Docker image는 `VLMaps` demo/custom scene 확인 전용으로 둔다. SLAM tooling은 dependency 충돌 가능성이 크므로 별도 Docker image로 분리한다.

## Docker Image Layout Decision

### 사실

- `VLMaps` smoke test는 semantic map output과 logging path 확인이 목적이다.
- Step 4-5 SLAM tooling은 ORB-SLAM2, GTSAM, g2o, ROS, `evo` 같은 별도 dependency를 요구할 수 있다.

### 에이전트 추론

Use separate images:

- `research3/vlmaps-smoke:<date>`: `VLMaps` demo/custom scene, map creation/indexing, object-goal logging path.
- `research3/slam-eval:<date>`: later pose graph connectivity, `ATE/RPE`, tracking proxy, live SLAM / offline trajectory evaluation.

The first smoke test image should not include SLAM tooling. Shared artifacts should pass through mounted folders such as `/runs` or exported map / trajectory files.

## Dataset Mount Plan

| Host variable | Container path | Required now? | Role |
| --- | --- | --- | --- |
| `$RESEARCH_DATA_ROOT/vlmaps` | `/datasets/vlmaps` | Optional | `VLMaps` demo/custom scene input/output |
| `$RESEARCH_DATA_ROOT/mp3d` | `/datasets/mp3d` | No | later Matterport3D scene assets |
| `$RESEARCH_DATA_ROOT/hm3d` | `/datasets/hm3d` | No | later Habitat ObjectNav / HM3D scenes |
| `$RESEARCH_RUN_ROOT` | `/runs` | Optional | smoke test logs and generated map artifacts |

MP3D/HM3D path가 없으면 smoke test는 `VLMaps` demo/custom data만 확인하고, Habitat ObjectNav metric은 blocked 상태로 기록한다.

## Planned Commands

These commands define the smoke-test path. The exact executed commands and outputs are recorded in the Attempt Log.

### Docker Health Check

```bash
docker --version
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi
```

If the CUDA image tag is unavailable, choose a CUDA 12.x base image compatible with the installed NVIDIA driver and record the exact tag.

### Candidate Smoke Image

```bash
cd hypothesis/CAND-01/H001_uncertainty-reobservation/runtime
docker build -f Dockerfile.vlmaps-smoke -t research3/vlmaps-smoke:20260507 .
```

### Candidate Run Shape

```bash
sg docker -c 'docker run --rm --gpus all --ipc=host \
  -v "$RESEARCH_DATA_ROOT/vlmaps:/datasets/vlmaps" \
  -v "$RESEARCH_RUN_ROOT:/runs" \
  research3/vlmaps-smoke:20260507'
```

The exact command may change after inspecting the `VLMaps` repo layout inside the image.

## Expected Outputs

Smoke test output should be small and disposable.

- Docker image tag and base image
- `VLMaps` repo commit hash
- command line
- whether demo/custom map creation runs
- whether map indexing or object-goal logging path is reachable
- generated artifact path, if any
- failure reason if blocked

No `experiments/`, `data/`, `results/`, or `paper/` folder is created at workflow-definition time.

## Attempt Log

### 2026-05-07

### 사실

Docker CLI exists:

```text
Docker version 29.4.0, build 9d7ad9f
```

The current shell did not initially include the `docker` group, so plain `docker ps` failed:

```text
permission denied while trying to connect to the docker API at unix:///var/run/docker.sock
```

System group membership and socket permissions:

```text
docker:x:979:user,yoohyun
yoohyun : yoohyun sudo docker
/var/run/docker.sock -> root:docker srw-rw----
```

`sg docker` gives the current command a `docker` group context:

```text
uid=1001(yoohyun) gid=979(docker) groups=979(docker),27(sudo),1001(yoohyun)
```

Docker daemon and GPU checks passed through `sg docker`:

```text
docker run --rm hello-world -> passed
docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi -> passed
GPU: NVIDIA GeForce RTX 5090, 32607 MiB
Driver: 580.126.09
```

`VLMaps` branch references checked:

```text
master: 58060f97239074338ab419a2090d43fa752d724d
demo: bc79b26a577e5a9408f86e45e5c16530ca80f867
```

Smoke image built:

```text
tag: research3/vlmaps-smoke:20260507
base image: python:3.8-slim
image id: sha256:9956fd7c97087b6bcb05c9beba3962a2e73af45cc7baf32f52cc58dac67bdd5e
```

Executed command:

```bash
sg docker -c 'docker run --rm --gpus all --ipc=host \
  -v /tmp/research3-data/vlmaps:/datasets/vlmaps \
  -v /tmp/research3-runs:/runs \
  research3/vlmaps-smoke:20260507'
```

Smoke result:

```text
status: ok
repo: vlmaps/vlmaps
branch: demo
commit: bc79b26a577e5a9408f86e45e5c16530ca80f867
scene: /datasets/vlmaps/5LpN3gDmAk7_1
host data cache: /tmp/research3-data/vlmaps
host data size: 12G
```

Lightweight import checks passed:

```text
utils.time_utils -> /opt/vlmaps/utils/time_utils.py
utils.mp3dcat -> /opt/vlmaps/utils/mp3dcat.py
examples.context -> /opt/vlmaps/examples/context.py
```

Full map-creation utility import was not covered by the minimal smoke image:

```text
import utils.clip_mapping_utils -> ModuleNotFoundError: No module named 'cv2'
```

Loaded scene counts:

| Directory | Count |
| --- | ---: |
| `rgb` | 1159 |
| `depth` | 1159 |
| `pose` | 1159 |
| `semantic` | 1159 |
| `map_correct` | 5 |

Map artifacts inspected:

| File | Shape | Dtype | Min | Max |
| --- | --- | --- | ---: | ---: |
| `color_top_down_1.npy` | 1000 x 1000 x 3 | `uint8` | 0.0 | 255.0 |
| `grid_lseg_1.npy` | 1000 x 1000 x 512 | `float32` | -3.9830 | 9.0398 |
| `obstacles.npy` | 1000 x 1000 | `uint8` | 0.0 | 1.0 |

### 에이전트 추론

Stage 1 Docker smoke test passed for the `VLMaps` demo scene at the map-artifact inspection level. The local blocker is no longer Docker daemon access for this session when commands are wrapped with `sg docker`; however, plain `docker` commands may still require a new login shell before the updated `docker` group is inherited.

This smoke test verifies that the `VLMaps` demo map artifacts are inspectable enough to start object/node uncertainty extraction. It does not yet verify full `VLMaps` map creation, map indexing, object-goal navigation logging, Habitat ObjectNav `SR`, `SPL`, wrong-goal visit, or wasted path logging.

### 사용자 판단 필요

- For ordinary `docker ...` commands without `sg docker`, start a new login shell or reboot once.

## HM3D Acquisition And Mount Smoke

### 사실

- Date checked: 2026-05-07
- Docker image: `research3/hm3d-download:20260507`
- Host data root: `/tmp/research3-data`
- Container data root: `/data`
- Habitat-Sim dataset downloader source: `datasets_download.py`
- Matterport token was passed through environment variables and is not stored in this workflow document.

Docker mount smoke command:

```bash
sg docker -c 'docker run --rm \
  -v /tmp/research3-data:/data:ro \
  research3/hm3d-download:20260507 \
  python /opt/check_hm3d.py /data'
```

Smoke result:

```text
status: ok
hm3d_path: /data/scene_datasets/hm3d
objectnav_hm3d_v2_path: /data/datasets/objectnav/hm3d/v2
objectnav json.gz files: 186
hm3d_basis.scene_dataset_config.json: exists
hm3d_annotated_basis.scene_dataset_config.json: exists
```

HM3D split files found through Docker mount:

| Split | basis `.glb` | basis `.navmesh` | semantic `.glb` | semantic `.txt` |
| --- | ---: | ---: | ---: | ---: |
| `train` | 800 | 800 | 145 | 145 |
| `val` | 100 | 100 | 36 | 36 |
| `minival` | 10 | 10 | 4 | 4 |

ObjectNav HM3D v2 sample paths were visible under:

```text
/data/datasets/objectnav/hm3d/v2/objectnav_hm3d_v2/train/content/*.json.gz
```

### 에이전트 추론

The HM3D/HM3DSem benchmark gate is no longer blocked for Docker-based first-probe setup. The next implementation gate is not dataset access, but whether the chosen runtime image can connect HM3D scene assets, ObjectNav episodes, semantic map candidates, and logging for wrong-goal visit / wasted path.

This does not automatically validate full Habitat ObjectNav evaluation, `VLMaps` map creation on HM3D, or Step 4-5 SLAM metrics.
- Provide or confirm MP3D/HM3D scene data access and host mount paths before Habitat ObjectNav metrics.
- Decide when to build a fuller `VLMaps` runtime image with `requirements.txt` for map creation / object-goal evaluation.

## Dataset Gate Log

### 2026-05-07

### 사실

Dataset mount checks were run through Docker using `sg docker`.

Checked host mounts:

```text
/home -> /host/home:ro
/home/yoohyun -> /host/home/yoohyun:ro
/tmp/research3-data -> /datasets:ro
```

Current `/tmp/research3-data` contents inside Docker:

```text
/datasets/vlmaps
```

Missing paths:

```text
/datasets/mp3d
/datasets/hm3d
/datasets/scene_datasets
/datasets/scene_datasets/mp3d
/datasets/scene_datasets/hm3d
```

Search results:

```text
MP3D/HM3D scene asset directories: not found
Habitat scene files such as .glb / .navmesh / .habitat: not found
Only literature folder match: /home/yoohyun/research2/literature/2024_arxiv_hm3d-ovon
```

### 에이전트 추론

This was the initial dataset gate before HM3D acquisition. HM3D scene assets and ObjectNav episodes were later acquired under `/tmp/research3-data` and checked through Docker. MP3D remains optional unless a specific baseline or cross-dataset comparison requires it.

### 사용자 판단 필요

- Decide whether MP3D is needed as a secondary benchmark or whether HM3D / HM3D-OVON is sufficient for the first implementation.

## Success Gate

The minimal map-artifact smoke test passes if all are true:

- Docker GPU check passes or CPU-only fallback is explicitly recorded.
- `VLMaps` repo is cloned at a pinned commit inside Docker.
- Lightweight `VLMaps` modules can be imported inside Docker.
- At least one demo/custom scene has inspectable RGB-D, pose, semantic, and map artifact files.
- The expected output path for map artifact or navigation log is known.
- Failure logs are captured if the command does not complete.

Full `VLMaps` runtime is a later gate if the first probe needs map creation, map indexing, or object-goal evaluation scripts.

## Failure Gate

The smoke test fails if one of these blocks the path:

- Docker cannot access GPU and CPU fallback is too slow or incompatible.
- `VLMaps` dependency stack cannot be built in a pinned Docker image.
- Demo/custom data path is unavailable.
- The map output is not inspectable enough to define object/node uncertainty.

Missing full `VLMaps` runtime dependencies such as `cv2` are not a minimal smoke failure unless the current task requires map creation or object-goal evaluation.

## Next Actions

1. [x] Decide whether SLAM tooling should be in the same Docker image or a separate image.
2. [x] Create the smoke-test Docker workflow files when execution begins.
3. [x] Run `VLMaps` demo/custom smoke test.
4. [x] Record the result back in `04_first_experiment.md`.
5. [x] Confirm MP3D/HM3D local scene access and Docker mount paths: local scene assets not found.
6. [ ] Select fallback Replica / ScanNet one-scene replay candidate.
