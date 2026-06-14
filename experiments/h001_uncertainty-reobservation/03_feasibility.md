# Feasibility

## Dataset / Benchmark

### Primary

- Habitat ObjectNav
- MP3D / HM3D subset if accessible

### Fallback Probe

- Replica or ScanNet replay with object candidates and precomputed viewpoints
- Synthetic perturbation on semantic map candidates: wrong label, missing object, duplicate object, stale object

## Metrics

### Task Behavior

- `Success Rate`
- `SPL`
- wrong-goal visit rate
- wasted path / extra path length
- re-observation count

### Map Quality

- object precision / recall
- semantic candidate accuracy
- uncertainty calibration: confidence vs failure probability

### SLAM / Pose Quality

- ATE/RPE
- pose graph connectivity
- localization failure count
- pose covariance or tracking confidence if available

## Baselines

- no-reobservation semantic map baseline
- random re-observation baseline
- `CARe`-style confidence replanning
- frontier / nearest-view re-observation baseline
- semantic-only re-observation baseline
- geometry-only exploration baseline

## Implementation Dependencies

- access to Habitat ObjectNav or replayable RGB-D scene
- semantic map candidate generation through `VLMaps`, `ConceptGraphs`, or a simplified precomputed map
- object/node uncertainty features
- shortest-path or navigation-cost computation
- SLAM uncertainty proxy or trajectory ground truth for Step 4-5

## Stage 1 Baseline Feasibility Check

Date checked: 2026-05-07

### 사실

| Item | Current source-level status | Local status |
| --- | --- | --- |
| `CARe` | Official repo exists: https://github.com/CARe-maps/CARe_experiments. README documents OpenMask3D setting, MP3D preprocessing, feature extraction, and `evaluate_mp3d_top_category.py` / `evaluate_mp3d_top_confidence.py`. | Repo not cloned. Dataset and OpenMask3D environment not installed. |
| `VLMaps` | Official repo exists: https://github.com/vlmaps/vlmaps. README documents demo branch, map creation, map indexing, object-goal navigation evaluation, and metric computation. | Docker smoke test passed on the `demo` branch scene `5LpN3gDmAk7_1`. |
| Habitat ObjectNav | Habitat-Lab exists: https://github.com/facebookresearch/habitat-lab. Dataset table lists ObjectNav MP3D and HM3D task datasets; scenes require MP3D/HM3D access. | Habitat-Lab not installed. Docker mount check found no local MP3D/HM3D scene assets. |
| Local compute | NVIDIA GeForce RTX 5090 32GB and about 911GB disk free were detected. Docker is installed. | Docker daemon and GPU checks pass through `sg docker`; Docker is the chosen smoke-test and implementation environment. |

### 논문 주장

- `CARe`는 pre-explored semantic map의 uncertainty / multi-view consistency signal로 wrong decision 이후 replanning을 개선한다고 주장한다.
- `VLMaps`는 pretrained visual-language features를 3D/top-down map에 fuse해 open-vocabulary goal localization and navigation이 가능하다고 주장한다.
- Habitat ObjectNav는 `Success Rate` and `SPL` 같은 standard navigation metrics를 제공하는 benchmark surface다.

### 에이전트 추론

Stage 1의 `VLMaps` demo map inspection path는 Docker에서 실행 가능성이 확인됐다. Direct full reproduction보다 staged probe가 여전히 필요하다.

1. `VLMaps`를 먼저 확인한다. 이유는 map creation, map indexing, object-goal navigation evaluation path가 README에 직접 있으며, CAND-01의 `NoReobserve` baseline과 uncertainty heatmap extraction에 가장 가깝기 때문이다.
2. `CARe`는 first implementation baseline보다 uncertainty-signal / replanning baseline으로 두는 편이 안전하다. Official repo가 OpenMask3D setting 중심이고 VLMaps/Habitat full ObjectNav reproduction path를 직접 문서화하지 않기 때문이다.
3. Habitat ObjectNav는 final Stage 1 metric surface로 필요하지만, MP3D/HM3D scene access가 gate다. Local smoke test는 Habitat test scenes로 simulator health만 확인할 수 있고, semantic ObjectNav 검증은 MP3D/HM3D가 필요하다.
4. Local setup은 host Python 3.12를 쓰지 않고 Docker로 진행한다. `VLMaps`는 Python 3.8 / older dependency stack, Habitat-Lab stable은 Python >=3.9 stack이므로 같은 image에 억지로 합치지 않고 smoke test image와 later SLAM image를 분리할 수 있게 둔다.

### Baseline Decision

| Baseline | Stage 1 role | Feasibility | Risk |
| --- | --- | --- | --- |
| `NoReobserve` on `VLMaps` map | primary first baseline | High after `VLMaps` smoke test | MP3D data and old dependency stack for benchmark metrics |
| `RandomReobserve` | simple implemented baseline | High | requires reachable viewpoint sampler |
| `CARe-style` | uncertainty/replanning baseline | Medium | official code focuses OpenMask3D, not full ObjectNav `SR` / `SPL` |
| `OracleView` | diagnostic upper bound | Medium | requires ground-truth candidate correctness and reachable views |
| Habitat ObjectNav agent | benchmark/evaluation surface | Medium | scene access and simulator installation |

### Docker Smoke Test Decision

### 사실

- Smoke test와 논문 본문용 implementation experiment는 Docker 기반으로 진행한다.
- Host Python은 Docker 실행 전 사전 점검과 문서 작업에만 사용한다.

### 에이전트 추론

Stage 1 smoke test는 `VLMaps` demo scene에서 통과했다. MP3D/HM3D access는 별도 dataset gate로 두며, Habitat ObjectNav full metric은 scene data path가 확보된 뒤 진행한다. `CARe`는 exact reproduction보다 CARe-style uncertainty formula reimplementation을 first baseline으로 두는 편이 현실적이다.

### 사용자 판단 필요

- MP3D/HM3D scene data 접근 권한과 local mount path를 지정해야 한다.
- Docker smoke test workflow는 `runtime/workflow-20260507-smoke.md`에 작성했다.
- Plain `docker` command는 새 login shell에서 group membership을 다시 받으면 더 깔끔하다. 현재 shell에서는 `sg docker`로 실행 가능하다.

### Docker Smoke Test Result

### 사실

- Date checked: 2026-05-07
- Image: `research3/vlmaps-smoke:20260507`
- `VLMaps` commit: `bc79b26a577e5a9408f86e45e5c16530ca80f867`
- Command path: `sg docker`
- Demo scene: `5LpN3gDmAk7_1`
- Loaded frame counts: `rgb` 1159, `depth` 1159, `pose` 1159, `semantic` 1159
- Loaded map artifacts: `color_top_down_1.npy`, `grid_lseg_1.npy`, `obstacles.npy`
- Lightweight import checks passed: `utils.time_utils`, `utils.mp3dcat`, `examples.context`
- Full map-creation utility import is not covered by the minimal smoke image because `utils.clip_mapping_utils` needs missing dependency `cv2`

### 에이전트 추론

The first executable path should now move from environment smoke testing to uncertainty feature extraction on precomputed artifacts. `grid_lseg_1.npy`, `obstacles.npy`, RGB-D frames, semantic labels, and poses give enough local material for a small probe before full Habitat ObjectNav is mounted. If the first probe requires regenerating maps or running object-goal evaluation scripts, build a fuller `VLMaps` runtime image from `requirements.txt`.

### 사용자 판단 필요

- MP3D/HM3D scene access remains the next benchmark gate.

## MP3D/HM3D Dataset Gate

### 사실

- Date checked: 2026-05-07
- Check method: Docker read-only mount through `sg docker`
- Checked paths: `/home`, `/home/yoohyun`, `/tmp/research3-data`
- Found dataset path: `/tmp/research3-data/vlmaps`
- Not found: local MP3D/HM3D scene asset directories or Habitat scene files such as `.glb`, `.navmesh`, `.habitat`

### 에이전트 추론

This was the initial dataset gate. HM3D ObjectNav and HM3D-OVON are now available through Docker under `/tmp/research3-data`. The current blocker is runtime integration: episode loading, GT target labels, candidate extraction, shortest-path reference, and logging.

### 사용자 판단 필요

- Decide whether first runtime should extend `VLMaps` or start from Habitat ObjectNav directly.
- Keep Replica / ScanNet as fallback or Step 4-5 replay support rather than the primary unblock path.

## Step 4-5 SLAM Proxy and Metric Plan

Date checked: 2026-05-07

### 사실

| Source | SLAM-side signal used in the paper | Evaluation metrics useful for H001 |
| --- | --- | --- |
| `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration` | pose graph spectral utility / weighted Laplacian D-optimality, loop-closure-aware edge weighting | `ATE`, map error, semantic `IoU`, explored volume |
| `3D Active Metric-Semantic SLAM` | pose covariance trace, semantic landmark covariance trace, semantic loop closure opportunity | position error, yaw error, covariance reduction, odometry drift |
| `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information` | localization-aware Fisher Information-style utility in active mapping | `RMSE ATE`, `PSNR`, `SSIM`, `LPIPS`, `Depth MAE`, completeness |
| `Open-Vocabulary Online Semantic Mapping for SLAM` | SLAM backbone variants and loop-closure-aware semantic map fusion | `ATE RMSE`, `mIoU`, `mAcc`, runtime |
| `Mutual information-based hierarchical NBV decision for active semantic visual SLAM under dynamic environments` | tracking robustness / local NBV under dynamic objects | `ATE`, `RPE Trans.`, `RPE Rot.`, tracking loss rate, near collision counts, entropy reduction rate |

### Proxy vs Metric Separation

| Role | Use inside policy? | Report as result? | Candidate signals |
| --- | --- | --- | --- |
| SLAM uncertainty proxy | Yes | Secondary diagnostic | tracking state, number of tracked features, inlier ratio, keyframe density, loop closure candidate score, pose graph connectivity, covariance trace |
| Pose / map quality metric | No | Yes | `ATE`, `RPE`, drift, map error, semantic `IoU` / `mIoU`, object precision / recall |
| Safety / robustness metric | No, except optional risk penalty | Yes | localization failure count, tracking loss rate, near collision count, recovery count |

### Measurement Tiers

| Tier | When to use | Minimum implementation | What it proves |
| --- | --- | --- | --- |
| Tier 0: no live SLAM | Stage 1-2 only | GT pose replay, path cost, semantic map update, wrong-goal logging | semantic re-observation value only; not enough for Step 4-5 claim |
| Tier 1: tracking proxy | first Step 4 extension | run a SLAM/tracking backend or expose simulator pose-noise proxy; log tracking state, feature count, inlier ratio, keyframe frequency | re-observation viewpoint can avoid low-localization-confidence motion |
| Tier 2: pose graph proxy | stronger Step 4 | maintain keyframe graph; compute degree, loop-closure candidate count, algebraic connectivity `lambda2`, or log-det / D-optimality proxy | selected viewpoint improves graph connectivity / loop closure opportunity |
| Tier 3: covariance proxy | strongest simulator/real extension | use GTSAM/g2o/SLAM covariance if available; log pose covariance trace and landmark covariance trace | selected viewpoint reduces pose / map uncertainty directly |
| Tier 4: full evaluation | Step 5 | compute `ATE/RPE`, map error, semantic accuracy, connectivity, failure counts for each policy | `SemanticSLAM` improves map/pose consistency over `SemanticOnly` and `SLAMOnly` |

### Proposed Utility

`SemanticSLAM` should use a small explicit utility, not an opaque learned score:

```text
U(v) = alpha * SemanticGain(v)
     + beta  * SLAMGain(v)
     - gamma * TravelCost(v)
     - eta   * Risk(v)
```

- `SemanticGain(v)`: expected reduction of object/node uncertainty visible from viewpoint `v`.
- `SLAMGain(v)`: tracking confidence improvement, loop closure opportunity, graph connectivity gain, or covariance trace reduction proxy.
- `TravelCost(v)`: shortest path length or estimated navigation time from current pose to `v`.
- `Risk(v)`: optional penalty for low visibility, collision risk, dynamic object proximity, or expected tracking loss.

### Required Comparisons

| Policy | Purpose |
| --- | --- |
| `SemanticOnly` | tests whether semantic uncertainty alone is enough |
| `SLAMOnly` | tests whether localization-aware motion alone explains the improvement |
| `SemanticSLAM` | proposed combined utility |
| `RandomReobserve` | checks whether any extra view is enough |
| `NoReobserve` | base semantic map commitment |
| `OracleView` | upper bound for candidate correctness / best re-observation viewpoint |

### Step 4-5 Gate

Step 4-5 is valid only if all conditions below are met:

- At least one SLAM uncertainty proxy is available before action selection.
- At least one pose/map quality metric is measured after action execution.
- `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` are compared on the same scenes / episodes.
- Travel cost is included, otherwise `SemanticSLAM` may win by spending too much path budget.
- Failure cases are counted instead of excluded: localization failure, tracking loss, unreachable viewpoint, and semantic map update failure.

### 에이전트 추론

The first practical Step 4 path should use Tier 1 or Tier 2, not Tier 3. Direct covariance is ideal but likely expensive unless a factor-graph backend is already exposed. A reasonable first extension is:

1. run Stage 1 with `VLMaps` / Habitat or replayed RGB-D scenes;
2. add a simple keyframe graph over the executed trajectory;
3. define `SLAMGain(v)` as visibility-weighted loop-closure opportunity plus graph connectivity improvement;
4. evaluate with `ATE/RPE` if a SLAM trajectory is available, otherwise use localization failure / tracking proxy and defer `ATE/RPE` to the next gate.

### 사용자 판단 필요

- Step 4 first proxy should be chosen: tracking proxy first or pose graph connectivity first.
- If Docker is used for Stage 1, decide whether the same Docker image should include SLAM tooling, or whether SLAM evaluation should be isolated in a second image.
- `ATE/RPE` requires ground truth trajectory. For simulation this can come from Habitat / Replica trajectory; for real-world it needs AprilTag, motion capture, wheel-odometry plus manual alignment, or another ground-truth approximation.

### Step 4 First Proxy Decision

### 사실

- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration` uses pose graph spectral utility as the SLAM-side planning signal.
- Tracking proxy such as inlier ratio or feature count requires a live SLAM / visual odometry backend.
- Docker image layout decision: `VLMaps` smoke test and SLAM evaluation use separate Docker images.

### 에이전트 추론

Choose `pose graph connectivity` as the first Step 4 proxy.

This is the lowest-dependency proxy that still represents the SLAM/map-side goal. It can be computed from keyframes and candidate re-observation viewpoints before a full ORB-SLAM2 / GTSAM / g2o backend is running. Tracking confidence remains a later proxy once a live SLAM backend is available.

Initial proxy definition:

- graph node: keyframe, current pose, candidate re-observation viewpoint, or confirmed semantic landmark anchor;
- odometry edge: consecutive movement between keyframes / viewpoints;
- candidate loop edge: spatially close or high-overlap viewpoint pair that may improve map consistency;
- connectivity metric: algebraic connectivity `lambda2`, graph degree / component count, loop-closure candidate count, or D-optimality-style log-det proxy;
- `SLAMGain(v)`: expected graph connectivity improvement after adding viewpoint `v` and its candidate edges.

### 사용자 판단 필요

- When a live SLAM backend is introduced, tracking confidence / inlier ratio can be added as a second proxy.
- The first Docker smoke test does not include SLAM tooling.

## Risks

- `CARe` / `VLMaps` reproduction may be slow.
- Habitat dataset access may be blocked.
- Synthetic perturbation may not represent real detector errors.
- Re-observation cost may dominate any semantic benefit.
- ATE/RPE or pose graph connectivity may be hard to measure consistently across simulator and real-world setup.

## Fallback Replay Plan

### 사실

- Primary path is still `HM3D ObjectNav` and `HM3D-OVON`.
- Fallback replay is only for debugging or a blocked simulator path.
- Candidate fallback datasets: `Replica`, `ScanNet`, ScanNet-style RGB-D replay, or a small real-world ROS 2 bag.

### 에이전트 추론

Fallback replay is useful when HM3D artifact coverage fails because it can isolate semantic candidate uncertainty, viewpoint selection, and logging without depending on full ObjectNav benchmark structure. It should not replace HM3D as the main benchmark if HM3D remains available.

Recommended fallback order:

1. `Replica` one-scene RGB-D replay for controlled indoor object layout.
2. `ScanNet` / ScanNet-style replay for real captured trajectories.
3. Real-world ROS 2 bag only after simulator metrics and logging are stable.

## Real-World Feasibility

### 사실

- Real-world validation is a later system validation stage, not the current first probe.
- Hardware-specific planning requires robot platform, RGB-D / LiDAR sensor, compute device, ROS availability, and ground-truth source.
- Possible GT sources: motion capture, AprilTag map, LiDAR SLAM reference, calibrated object-position map, or manually verified event labels.
- Date checked for representative hardware references: 2026-05-22.

Representative source facts:

| Component | Official reference fact | Link |
| --- | --- | --- |
| `TurtleBot 4` | ROS 2 learning/research platform with `OAK-D`, 2D LiDAR, IMU, wheel odometry, and ROS topics | https://clearpathrobotics.com/turtlebot-4/ |
| `Jackal UGV` | mobile base with payload and user power for custom sensor stacks | https://docs.clearpathrobotics.com/docs_robots/outdoor_robots/jackal/user_manual_jackal/ |
| `NVIDIA Jetson AGX Orin` | edge AI/robotics compute; AGX Orin series lists up to 275 TOPS | https://www.nvidia.com/en-us/autonomous-machines/embedded-systems/jetson-orin/ |
| `OAK-D Pro` | stereo depth, IMU, IR/dot projector, on-device CV/AI pipeline | https://docs.luxonis.com/hardware/products/OAK-D%20Pro |
| `Intel RealSense D455` | stereo depth camera; official spec lists 0.6m-6m range and 1280x720 up to 90 FPS | https://www.intel.de/content/www/de/de/products/sku/205847/intel-realsense-depth-camera-d455/specifications.html |
| `Hokuyo UST-10LX` | 2D LiDAR with 270 degree field of view, 10m range, ROS1/ROS2 compatibility | https://www.hokuyo-usa.com/products/lidar-sensors/ust-10lx |
| `Ouster OS0` | short-range 3D LiDAR; official page lists 90 degree vertical FoV and high point-rate options | https://ouster.com/products/os0-lidar-sensor |
| `OptiTrack PrimeX 13` | motion-capture camera with 240 FPS capture for external GT setups | https://optitrack.com/cameras/primex-13 |

### 에이전트 추론

Real-world validation should test whether the same failure decomposition appears outside simulation: candidate uncertainty, explicit commit, wrong-goal visit, wasted path, and pose/map-side consistency. It should not replace simulator evidence unless simulator data becomes unusable.

### Representative Hardware Configurations

These are research setup templates, not purchase decisions.

| Tier | Purpose | Representative setup | What it can validate | Main limitation |
| --- | --- | --- | --- | --- |
| `RW0_ros2_minimal` | small indoor proof-of-concept | `TurtleBot 4` Standard, built-in `OAK-D Pro`, built-in 2D LiDAR, Raspberry Pi 4, optional external workstation | wrong-goal visit, wasted path, active re-observation logging in a controlled room | onboard compute is weak for full detector/segmenter stack |
| `RW1_semantic_nav` | paper-style indoor semantic navigation | `Jackal UGV` or similar differential mobile base, `OAK-D Pro` or `Intel RealSense D455`, `Hokuyo UST-10LX`, `NVIDIA Jetson AGX Orin` or onboard x86+GPU, ROS 2 | semantic uncertainty trigger, re-observation viewpoint choice, wrong-goal commit reduction | object GT and repeatability require careful scene setup |
| `RW2_semantic_slam` | Step 4-5 SLAM/map consistency | `Jackal UGV`, RGB-D/stereo camera, `Ouster OS0` or comparable 3D LiDAR, wheel odometry/IMU, Jetson/onboard PC, external GT | semantic map update, pose graph connectivity, map consistency, localization failure | expensive and heavier calibration burden |
| `RW3_gt_lab` | high-confidence evaluation | any above platform plus `OptiTrack` or calibrated `AprilTag` map and surveyed object positions | `ATE/RPE`, object-position error, event-level wrong-goal labels | lab infrastructure and calibration time |

### Recommended First Real-World POC

### 에이전트 추론

Use `RW1_semantic_nav` if hardware can be chosen freely:

- mobile base: `Jackal UGV`-class platform or equivalent ROS 2 differential-drive base with enough payload for sensors and compute;
- perception: one forward RGB-D/stereo sensor, preferably `OAK-D Pro` or `Intel RealSense D455`;
- localization / safety: 2D LiDAR such as `Hokuyo UST-10LX` for navigation and obstacle safety;
- compute: `NVIDIA Jetson AGX Orin` or a tethered workstation if foundation-model perception is too heavy onboard;
- GT: `AprilTag` map for low-cost first validation, `OptiTrack` for stronger `ATE/RPE`;
- environment: one indoor lab room with 5-10 movable object instances and repeated distractors, e.g. chairs, plants, sofas, monitors, boxes.

Minimum publishable real-world role:

- confirm that the same failure taxonomy appears outside simulator;
- report event-level metrics: wrong-goal commit, wasted path, re-observation count, unresolved-risk rate;
- report pose/map-side metric only if GT or a stable SLAM reference exists;
- keep real-world result as proof-of-concept unless it has enough repeated trials and calibrated GT.

### 사용자 판단 필요

- Confirm actual robot, camera / RGB-D / LiDAR, compute, ROS / ROS 2 availability, and GT setup.
- Decide whether real-world validation is required for the first submission or reserved for thesis/journal extension.

## Gate

Move to experiment-ready only if:

- at least one dataset/replay path is executable,
- at least two baselines are implementable,
- wrong-goal visit and wasted path can be logged,
- map candidate correctness can be measured or approximated.
- Step 4-5 extension requires at least one SLAM-side metric: ATE/RPE, pose graph connectivity, localization failure count, or pose covariance proxy.
