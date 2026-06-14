# CAND-01

Working title: `Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`

Status: Primary candidate

Date created: 2026-05-06

Date updated: 2026-05-07

## Research Goal

### 사실

이 후보는 `CAND-01`의 semantic map uncertainty 기반 active re-observation과 `CAND-02`의 active semantic SLAM utility를 단계적으로 연결한다.

### 에이전트 추론

중심 주장은 semantic uncertainty가 단순 confidence score가 아니라 active SLAM/navigation utility로 작동할 수 있다는 것이다. 즉, pre-explored environment-specific semantic memory의 불확실성을 robot mobility decision에 재사용하면 ObjectNav 같은 navigation task의 wrong-goal visit과 wasted path를 줄이고, 확장 단계에서는 SLAM/map consistency도 함께 개선할 수 있는지 검증한다. 연구 기간은 6개월-1년을 기준으로 두고 Step 1-5 전체를 목표로 둔다.

## Step Plan

### Step 1: Pre-explored semantic map의 object/node uncertainty 계산

Pre-explored open-vocabulary semantic map에서 object/node별 uncertainty를 계산한다.

Candidate uncertainty signals:

- semantic similarity score
- top-1 / top-2 similarity margin
- multi-view observation count
- viewpoint diversity
- geometric visibility consistency
- object-size / distance prior
- map age or dynamic-change flag
- localization confidence if available

### Step 2: 불확실한 후보에 대해 active re-observation viewpoint 선택

Semantic uncertainty가 높은 object/node에 대해 바로 goal로 이동하지 않고, 추가 관찰을 위한 viewpoint를 선택한다.

Candidate utility:

```text
Utility(view) =
  semantic_uncertainty_reduction
- travel_cost
- observation_latency
```

### Step 3: ObjectNav에서 navigation outcome 평가

Active re-observation이 ObjectNav decision failure를 줄이는지 평가한다.

Primary metrics:

- `Success Rate`
- `SPL`
- `DTS`
- wrong-goal visit rate
- wasted path / extra path length
- re-observation count
- replanning count
- runtime / memory

### Step 4: semantic memory를 active SLAM utility로 확장

Semantic uncertainty만이 아니라 SLAM uncertainty를 active utility에 넣는다.

Extended utility:

```text
Utility(view) =
  semantic_uncertainty_reduction
+ lambda * SLAM_uncertainty_reduction
- beta * travel_cost
- gamma * observation_latency
```

SLAM-side signals:

- pose covariance if available
- visual tracking confidence
- feature count / inlier ratio
- loop closure likelihood
- pose graph connectivity proxy
- local map consistency
- relative drift proxy

### Step 5: SLAM/map-side metric까지 평가

ObjectNav metric뿐 아니라 map / pose / graph quality를 함께 본다.

SLAM and map metrics:

- map error
- semantic accuracy
- object precision / recall
- semantic map consistency before/after re-observation
- ATE/RPE
- pose graph connectivity
- localization failure count
- loop closure success / failure

## Problem Setting

### 사실

Pre-explored open-vocabulary semantic map은 ObjectNav와 language-guided navigation에서 많이 쓰인다. 관련 primary source는 `VLMaps`, `ConceptGraphs`, `DualMap`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `Semantic Environment Atlas`, `CARe`, `SG-Nav`, `3D Active Metric-Semantic SLAM`, `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`이다.

### 논문 주장

- `CARe`는 inaccurate pre-explored semantic map으로 인한 wrong decision을 confidence score와 multi-view consistency로 줄일 수 있다고 주장한다.
- `VLMaps`는 pretrained visual-language feature를 3D map에 fuse하면 language-indexed navigation이 가능하다고 주장한다.
- `DualMap`은 dynamic changing scenes에서 global abstract map과 local concrete map을 나누면 online language navigation에 유리하다고 주장한다.
- `SG-Nav`는 online 3D scene graph와 re-perception을 쓰면 zero-shot ObjectNav success가 개선된다고 주장한다.
- `3D Active Metric-Semantic SLAM`은 `Semantic Loop Closure`와 active uncertainty reduction planning으로 pose/map uncertainty를 줄일 수 있다고 주장한다.
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`은 semantic mutual information과 pose graph connectivity를 함께 쓰면 active metric-semantic SLAM에 유리하다고 주장한다.

### 에이전트 추론

현재 빈틈은 semantic map uncertainty와 SLAM uncertainty가 따로 다뤄진다는 점이다. Semantic map 기반 navigation 논문은 wrong semantic decision을 줄이는 데 집중하고, Active SLAM 논문은 online map/pose uncertainty를 줄이는 데 집중한다. 그러나 adaptive robot 관점에서는 "불확실한 semantic memory를 어디서 다시 관찰해야 navigation과 SLAM이 함께 좋아지는가"가 핵심이다.

## Research Question

Pre-explored semantic memory의 object/node uncertainty를 active SLAM/navigation utility로 사용하면, semantic-only replanning이나 geometry-only exploration보다 ObjectNav outcome과 map/pose consistency를 동시에 개선하는가?

## Hypothesis

### 에이전트 추론

Object candidate confidence가 낮거나 semantic candidates가 서로 ambiguous할 때 바로 goal로 이동하면 wrong-goal visit과 wasted path가 늘어난다. 이때 semantic uncertainty를 utility로 바꿔 informative viewpoint에서 re-observation을 수행하면 semantic decision과 navigation behavior가 개선될 수 있다. 추가로, 같은 utility를 SLAM uncertainty와 결합하면 re-observation이 navigation뿐 아니라 map/pose consistency에도 기여할 수 있다.

## Approach

### Phase 1: Semantic uncertainty only

1. Habitat ObjectNav environment에서 pre-explored semantic map을 준비한다.
2. object query마다 candidate object/node를 retrieval한다.
3. candidate uncertainty를 계산한다.
4. low-confidence case에서 active re-observation viewpoint를 선택한다.
5. new observation으로 semantic map confidence를 update한다.
6. final goal decision 후 ObjectNav metric을 측정한다.

### Phase 2: Semantic + SLAM uncertainty

1. active re-observation candidate view마다 SLAM uncertainty proxy를 계산한다.
2. semantic gain과 SLAM gain을 함께 쓰는 utility를 만든다.
3. semantic-only utility, SLAM-only utility, combined utility를 비교한다.
4. ObjectNav metric과 SLAM/map metric을 함께 측정한다.

### Phase 3: Real-world proof-of-concept

1. small indoor environment에서 pre-explored semantic map을 만든다.
2. mobile robot 또는 RGB-D sensor platform으로 active re-observation을 수행한다.
3. semantic correction, localization failure, wrong-goal visit을 기록한다.
4. simulation 결과가 real-world에서도 같은 failure mode를 줄이는지 본다.

## Re-observation Policy Variants

- `NoReplan`: top candidate로 바로 이동한다.
- `CARe-style`: confidence가 낮으면 next candidate로 replanning한다.
- `RandomReobserve`: confidence가 낮으면 random nearby viewpoint를 본다.
- `FrontierReobserve`: candidate 주변 unobserved frontier를 본다.
- `SemanticOnly`: semantic uncertainty reduction만 보고 viewpoint를 고른다.
- `SLAMOnly`: SLAM uncertainty reduction만 보고 viewpoint를 고른다.
- `SemanticSLAM`: semantic uncertainty reduction과 SLAM uncertainty reduction을 함께 본다.
- `Oracle`: ground-truth map update / shortest path 기준 best view를 고른다.

## Dataset / Benchmark

### Simulation

- Habitat ObjectNav
- MP3D / HM3D
- Replica
- Gibson
- RoboTHOR for robustness check

### Offline RGB-D / SLAM evaluation

- ScanNet
- ScanNet++
- TUM-RGBD
- Replica trajectories

### Real-world proof-of-concept

- indoor lab / corridor / room-scale environment
- RGB-D camera
- mobile base or handheld replay platform
- ROS / ROS2 logging
- optional ground truth: AprilTag, floor markers, motion capture, manual map

## Metrics

### Navigation metrics

- `Success Rate`
- `SPL`
- `DTS`
- wrong-goal visit rate
- wasted path / extra path length
- re-observation count
- replanning count
- task time

### Semantic map metrics

- object precision / recall
- semantic accuracy
- mIoU if dense labels are available
- false positive removal rate
- missing object recovery rate
- uncertainty calibration: confidence vs failure probability

### SLAM / localization metrics

- ATE/RPE
- pose covariance if available
- pose graph connectivity
- localization failure count
- loop closure success / failure
- local map consistency
- drift before/after re-observation

### System metrics

- runtime
- memory
- semantic perception latency
- re-observation travel cost
- robot safety interventions in real-world deploy

## Baselines

- `VLMaps`
- `CARe`
- `ConceptGraphs`
- `DualMap`
- `Open-Vocabulary Online Semantic Mapping for SLAM`
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`
- `3D Active Metric-Semantic SLAM` style active SLC ablation
- frontier exploration
- geometry uncertainty-only exploration
- semantic-only re-observation
- no-replanning semantic map baseline
- random re-observation baseline

## Evidence Base

### 사실

확인한 primary source는 6개 이상이다.

- `VLMaps`
- `ConceptGraphs`
- `CARe`
- `DualMap`
- `Open-Vocabulary Online Semantic Mapping for SLAM`
- `Semantic Environment Atlas`
- `SG-Nav`
- `MemoNav`
- `OpenScene`
- `3D Active Metric-Semantic SLAM`
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`
- `Mutual information-based hierarchical NBV decision`

### 왜 아직 풀리지 않았는가

- open-vocabulary semantic map은 false positive, false negative, ambiguous category, viewpoint-dependent detection에 취약하다.
- ObjectNav metric은 final success를 보지만, semantic map error가 어떤 decision failure로 이어지는지 분리하지 않는 경우가 많다.
- `CARe`는 confidence와 replanning을 다루지만, active re-observation viewpoint selection과 SLAM uncertainty를 함께 최적화하지 않는다.
- Active SLAM 논문은 state uncertainty와 pose graph utility를 다루지만, previous environment-specific semantic memory를 prior로 쓰는 문제를 직접 닫지는 않는다.
- graph/LLM navigation은 strong result를 내지만, map confidence, SLAM uncertainty, action cost arbitration을 독립 contribution으로 분리하기 어렵다.

## Implementation Roadmap

### Stage 1: Baseline and semantic uncertainty

- `CARe` / `VLMaps` / Habitat ObjectNav 실행 가능성 확인
- pre-explored map 생성 또는 제공 map loading
- baseline metric reproduction: `Success Rate`, `SPL`
- object/node uncertainty feature extraction
- controlled map perturbation: wrong label, missing object, duplicate object, stale object

### Stage 2: Semantic active re-observation

- active re-observation policy 구현
- `NoReplan`, `CARe-style`, `RandomReobserve`, `SemanticOnly` 비교
- wrong-goal visit, wasted path, re-observation cost 분석
- semantic uncertainty calibration 분석

### Stage 3: SLAM uncertainty extension

- SLAM uncertainty proxy 정의
- pose covariance, tracking confidence, inlier ratio, pose graph connectivity 중 사용 가능한 signal 선택
- `SLAMOnly`와 `SemanticSLAM` policy 구현
- map error, semantic accuracy, ATE/RPE, pose graph connectivity 평가

### Stage 4: Robustness and ablation

- confidence signal별 ablation
- `lambda`, `beta`, `gamma` sensitivity 분석
- MP3D / HM3D / Replica cross-scene validation
- detector noise and map perturbation robustness check

### Stage 5: Real-world proof-of-concept

- indoor environment setup
- RGB-D / robot pose logging
- pre-explored semantic map construction
- active re-observation execution
- simulation failure mode가 real-world에서도 줄어드는지 확인

## Stage 1 Baseline Feasibility Result

Date checked: 2026-05-07

### 사실

| Component | Source checked | Result |
| --- | --- | --- |
| `CARe` | https://github.com/CARe-maps/CARe_experiments | Official repo is available. It documents OpenMask3D setup, MP3D preprocessing, feature extraction, and top-k replanning evaluation scripts. |
| `VLMaps` | https://github.com/vlmaps/vlmaps | Official repo is available. It documents demo branch, Habitat/Matterport3D dataset generation, map creation, map indexing, object-goal navigation evaluation, and metric computation. Docker smoke test passed on the demo scene. |
| Habitat ObjectNav | https://github.com/facebookresearch/habitat-lab and `DATASETS.md` | Habitat-Lab supports ObjectNav task datasets for MP3D and HM3D; scene assets are separate dataset gates. Docker mount check found no local MP3D/HM3D scene assets. |
| Local environment | local command check | RTX 5090 32GB and disk space are sufficient for first experiments. Docker daemon and GPU checks pass through `sg docker`; Docker is chosen for smoke tests and implementation experiments. |

### 에이전트 추론

Stage 1 is conditionally feasible and the `VLMaps` demo map inspection path has passed in Docker. The first implementation path should not start from full CARe reproduction. A more robust order is:

1. Extract object/node uncertainty features from the inspected `VLMaps` demo map artifacts.
2. Add `NoReobserve`, `RandomReobserve`, and `OracleView` logging around map candidates.
3. Reimplement `CARe-style` uncertainty / replanning as a controlled baseline instead of depending on exact CARe repo behavior.
4. Move to Habitat MP3D/HM3D ObjectNav after scene access and simulator installation are resolved.

### Docker Smoke Result

### 사실

- Date checked: 2026-05-07
- Docker image: `research3/vlmaps-smoke:20260507`
- `VLMaps` branch / commit: `demo`, `bc79b26a577e5a9408f86e45e5c16530ca80f867`
- Demo scene: `5LpN3gDmAk7_1`
- Map artifacts inspected: `color_top_down_1.npy`, `grid_lseg_1.npy`, `obstacles.npy`
- Loaded frame counts: `rgb` 1159, `depth` 1159, `pose` 1159, `semantic` 1159
- Lightweight import checks passed: `utils.time_utils`, `utils.mp3dcat`, `examples.context`
- Full map-creation utility import is not covered by the minimal smoke image because `utils.clip_mapping_utils` needs missing dependency `cv2`

### 에이전트 추론

The next CAND-01 work should not spend more time on general environment setup for precomputed artifacts. It should define the first object/node uncertainty features on `VLMaps` map artifacts, while MP3D/HM3D access is handled as the benchmark gate. A fuller `VLMaps` runtime image is only needed when the probe must regenerate maps or run object-goal evaluation scripts.

### 사용자 판단 필요

- MP3D/HM3D scene data access and Docker mount path.

### Dataset Gate Result

### 사실

- Date checked: 2026-05-07
- Check method: Docker read-only mount through `sg docker`
- Checked local roots: `/home`, `/home/yoohyun`, `/tmp/research3-data`
- Found: `/tmp/research3-data/vlmaps`
- Not found: local MP3D/HM3D scene asset directories or Habitat scene files such as `.glb`, `.navmesh`, `.habitat`

### 에이전트 추론

Habitat ObjectNav benchmark execution is blocked by missing local scene assets. The next feasible path is to choose a fallback one-scene replay candidate or continue a small probe with the existing `VLMaps` demo artifacts.

### Docker Decision

### 사실

- Smoke test and paper-body implementation experiments will use Docker-based isolated environments.
- Host Python is not the target environment for `VLMaps`, Habitat, or SLAM tooling.

### 에이전트 추론

The first smoke test used a `VLMaps` demo scene inside Docker and passed. HM3D ObjectNav and HM3D-OVON are now available through Docker, so the next gate is runtime integration rather than dataset access. `CARe-style` uncertainty should be reimplemented as a controlled baseline before attempting exact CARe reproduction.

### 사용자 판단 필요

- Whether MP3D is needed later as a secondary benchmark.
- Docker smoke test workflow is written at `experiments/h001_uncertainty-reobservation/runtime/workflow-20260507-smoke.md`.

## Step 4-5 SLAM Proxy and Metric Plan

Date checked: 2026-05-07

### 사실

| Evidence | Useful signal |
| --- | --- |
| `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration` | pose graph spectral utility, `ATE`, map error, semantic `IoU` |
| `3D Active Metric-Semantic SLAM` | pose covariance trace, landmark covariance trace, semantic loop closure, drift |
| `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information` | localization-aware active mapping utility, `RMSE ATE`, completeness |
| `Open-Vocabulary Online Semantic Mapping for SLAM` | SLAM-integrated semantic mapping, `ATE RMSE`, `mIoU`, `mAcc`, runtime |
| `Mutual information-based hierarchical NBV decision` | `ATE`, `RPE`, tracking loss rate, near collision count |

### 에이전트 추론

Step 4-5 should be measured as a staged extension, not as a separate hypothesis.

1. Keep Step 1-3 focused on semantic uncertainty and ObjectNav behavior.
2. Add `SLAMGain(v)` only after the semantic re-observation probe produces a usable signal.
3. Separate policy proxy from final metric:
   - policy proxy: tracking confidence, inlier ratio, keyframe graph connectivity, loop closure opportunity, covariance trace if exposed;
   - final metric: `ATE`, `RPE`, map error, semantic accuracy, pose graph connectivity, localization failure count.
4. Compare `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` with the same candidate viewpoints and travel-cost accounting.

### Utility Shape

```text
U(v) = alpha * SemanticGain(v)
     + beta  * SLAMGain(v)
     - gamma * TravelCost(v)
     - eta   * Risk(v)
```

### Minimum Valid Step 4-5 Claim

`SemanticSLAM` is only stronger than `SemanticOnly` if it improves at least one map/pose metric without unacceptable loss in `SPL` or excessive travel cost.

Acceptable minimum metric pair:

- task behavior: wrong-goal visit rate or wasted path;
- map/pose consistency: pose graph connectivity or localization failure count.

Stronger metric pair:

- task behavior: `SR`, `SPL`, wrong-goal visit, wasted path;
- map/pose consistency: `ATE`, `RPE`, map error, semantic accuracy, pose graph connectivity.

### 사용자 판단 필요

- First SLAM proxy: tracking confidence / inlier ratio first, or pose graph connectivity first.
- Docker layout decision: separate `VLMaps` smoke-test image and later `SLAM eval` image.
- Ground truth path: simulation ground truth first, real-world AprilTag / motion capture / manual alignment later.

### Step 4 First Proxy Decision

### 사실

- P02 `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration` provides the strongest direct support for pose graph connectivity as an active planning utility.
- Tracking confidence / inlier ratio requires live SLAM or visual odometry output.

### 에이전트 추론

Use pose graph connectivity as the first Step 4 proxy. This keeps Step 4 connected to the SLAM literature while avoiding an immediate dependency on ORB-SLAM2 / GTSAM / g2o. The first version can maintain a lightweight keyframe-viewpoint graph and estimate whether a re-observation viewpoint improves graph connectivity or loop-closure opportunity.

Tracking confidence should be added later when a live SLAM backend is available, especially for real-world deploy.

## Failure Conditions

- semantic confidence signal이 wrong navigation decision을 예측하지 못하면 실패다.
- active re-observation이 `Success Rate`를 올려도 `SPL`을 크게 낮추면 contribution이 약하다.
- SLAM uncertainty proxy가 map/pose metric improvement와 연결되지 않으면 Step 4-5 contribution이 약하다.
- combined utility가 semantic-only 또는 SLAM-only baseline보다 좋지 않으면 핵심 hypothesis가 약해진다.
- baseline reproduction이 불가능하면 candidate scope를 benchmark paper 또는 failure taxonomy paper로 낮춰야 한다.
- semantic map perturbation이 현실적이지 않으면 reviewer가 contribution을 약하게 볼 수 있다.
- real-world deploy에서 logging / calibration / safety 문제가 크면 proof-of-concept는 appendix 수준으로 낮춰야 한다.

## Scope Notes

### 에이전트 추론

6개월-1년 범위에서는 Step 1-5 전체를 목표로 잡는다. 다만 논문 작성에서는 staged contribution으로 제시해야 한다. Phase 1은 semantic uncertainty 기반 re-observation, Phase 2는 SLAM uncertainty-aware utility, Phase 3은 real-world proof-of-concept다.

## Minimum Publishable Claim

Pre-explored open-vocabulary semantic map의 uncertainty를 active re-observation action으로 변환하면 wrong-goal visit과 wasted path를 줄일 수 있다.

## Stronger Claim

Semantic uncertainty와 SLAM uncertainty를 결합한 active re-observation utility는 ObjectNav outcome과 map/pose consistency를 동시에 개선한다.

## Real-world Claim

Small-scale indoor robot deployment에서도 uncertain semantic memory를 다시 관찰하는 행동이 semantic map correction과 localization/navigation failure reduction에 도움이 된다.

## What to Verify Next

- Stage 1 Docker smoke test result는 `experiments/h001_uncertainty-reobservation/runtime/workflow-20260507-smoke.md`에 있다.
- Habitat MP3D/HM3D scene data 접근 권한과 local storage path를 확보했는가? Current status: not found in checked Docker mounts.
- Full `VLMaps` runtime image가 first probe에 필요한가, 아니면 precomputed artifacts로 충분한가?
- `CARe-style` uncertainty formula를 exact reproduction 없이 재구현해도 baseline으로 충분한가?
- re-observation viewpoint를 simulator에서 action으로 자연스럽게 정의할 수 있는가?
- pose graph connectivity proxy를 실제 candidate viewpoint graph에서 계산할 수 있는가?
- ATE/RPE ground truth를 simulation과 real-world에서 어떻게 확보할 것인가?
- real-world robot deploy에서 가능한 sensor, compute, safety constraint는 무엇인가?
