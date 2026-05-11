# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Dynamic active semantic SLAM simulation | Gazebo `Env_1`, `Env_2` with two moving persons | travel distance/time, `ATE`, `RPE Trans.`, `RPE Rot.`, `ERR` | nearest frontier, `TARE`, `RNE`, proposed global-only |
| Robustness under dynamic objects | same Gazebo environments | tracking loss rate, near collision counts | proposed global-only |
| Real-world feasibility | Meerkat robot + Realsense D435i + Jetson AGX Orin | module runtime, qualitative map/trajectory | no quantitative baseline |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4-5 local NBV under uncertainty | `ATE`, `RPE`, tracking loss, near collision, `ERR` | ObjectNav `SR` / `SPL`, semantic object accuracy, open-vocabulary memory update |

## Dataset / Benchmark

### 사실

- Simulation platform: Gazebo with ROS.
- SLAM base: ORB-SLAM2.
- Robot sensor: RGB-D camera.
- Camera resolution: 640 x 480.
- Camera intrinsics: `fx=573.4`, `fy=574.8`, `cx=320.1`, `cy=322.6`.
- Maximum reliable depth range: 5.0 m.
- Semantic model: YOLOv8s pretrained on COCO.
- Object tracker: BoT-SORT.
- Dynamic class used in experiments: `person`.
- Dynamic verification: epipolar constraint violation for more than 3 consecutive frames.
- Real-world platform: Meerkat robot with Jetson AGX Orin and Realsense D435i.

## Splits

### Simulation Environments

| Environment | Size | Dynamic objects | Stop criterion | Robot velocity | Grid resolution |
| --- | --- | --- | --- | --- | --- |
| Env_1 | 10 m x 10 m open space | two persons walking on fixed trajectories | next global NBV information gain < 50 bits | 0.2 m/s, 0.2 rad/s | 0.05 m/cell |
| Env_2 | 19 m x 22 m larger complex layout | two persons walking on fixed trajectories | next global NBV information gain < 260 bits | 0.2 m/s, 0.2 rad/s | 0.05 m/cell |

### Real-world Scene

- Meerkat robot.
- Jetson AGX Orin.
- Realsense D435i.
- Person walking back and forth in the environment.
- Result reported mainly as created map / trajectory visualization and runtime table.

## Metrics

- Travel Distance (m): total path length.
- Travel Time (min): total exploration duration.
- `ATE` (m): global localization accuracy.
- `RPE Trans.` (m): local translational motion error.
- `RPE Rot.` (rad): local rotational motion error.
- `ERR` (bits/s): entropy reduction rate, `H(G0)-H(GT)` divided by travel time.
- Tracking loss rate (%): SLAM backend failure frequency.
- Near collision counts: number of cases where robot stays within 2 m of moving obstacles for more than 3 seconds.
- Dynamic object residual points: qualitative visual evidence in maps, not a numeric table metric.

## Baselines

- Nearest frontier-based exploration.
- `TARE`.
- `RNE` / `RNEX`: paper text uses `RNEX`, tables use `RNE`.
- Proposed (global): global NBV only.
- Proposed: full hierarchical global + local NBV.

## Main Results

### Table 3: Env_1

| Method | Travel distance | Travel time | `ATE` | `RPE Trans.` | `RPE Rot.` | `ERR` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Nearest frontier | 31.25 | 5.24 | 0.30 | 0.27 | 0.15 | 77.35 |
| `TARE` | 25.31 | 4.89 | 0.32 | 0.28 | 0.18 | 85.90 |
| `RNE` | 34.34 | 4.93 | 0.31 | 0.29 | 0.17 | 85.27 |
| Proposed (global) | 29.88 | 4.91 | 0.27 | 0.25 | 0.19 | 84.43 |
| Proposed | 24.21 | 4.31 | 0.25 | 0.21 | 0.13 | 97.47 |

### Table 4: Env_2

| Method | Travel distance | Travel time | `ATE` | `RPE Trans.` | `RPE Rot.` | `ERR` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Nearest frontier | 71.79 | 11.44 | 0.42 | 0.32 | 0.21 | 152.97 |
| `TARE` | 69.07 | 11.32 | 0.56 | 0.44 | 0.22 | 153.88 |
| `RNE` | 71.06 | 11.79 | 0.46 | 0.39 | 0.21 | 148.71 |
| Proposed (global) | 68.04 | 10.54 | 0.38 | 0.31 | 0.23 | 166.94 |
| Proposed | 68.86 | 10.60 | 0.30 | 0.26 | 0.18 | 165.36 |

### Table 5: Local NBV / FPM Robustness

| Environment | Metric | Proposed (global) | Proposed |
| --- | --- | ---: | ---: |
| Env_1 | Tracking loss rate (%) | 30 | 10 |
| Env_1 | Near collision counts | 5 | 1 |
| Env_2 | Tracking loss rate (%) | 20 | 10 |
| Env_2 | Near collision counts | 7 | 2 |

### Table 6: Real-time Runtime on Meerkat Robot

| Module | Time (s) | Hardware |
| --- | ---: | --- |
| SLAM pipeline | 0.132 | CPU |
| Semantic segmentation (`YOLOv8`) | 0.032 | GPU |
| Object tracking (`BoT-SORT`) | 0.024 | GPU |
| Global NBV planning | 0.087 | CPU |
| Local NBV planning | 0.064 | CPU |
| Motion planning | 0.056 | CPU |

### 논문 주장

- Proposed method has lowest `ATE`, `RPE Trans.`, `RPE Rot.` in Env_1 and Env_2.
- In Env_1, full hierarchical NBV reduces tracking loss rate from 30% to 10% and near collision counts from 5 to 1 versus global-only NBV.
- In Env_2, full hierarchical NBV reduces tracking loss rate from 20% to 10% and near collision counts from 7 to 2 versus global-only NBV.
- Real-world runtime table supports real-time feasibility on Meerkat robot.

### 에이전트 추론

The local NBV module is the strongest evidence in this paper. It does not mainly improve semantic map quality as a final metric; it improves dynamic-scene robustness through feature observability and moving-object avoidance.

## Reproducibility Notes

- Nature / PMC full text is accessible.
- Code was not found from primary source or web search on 2026-05-06.
- Data availability statement says data are within the paper and Supplementary Information.
- Supplementary Information is available from the publisher, but local repo has not downloaded or inspected it.
- Implementation dependencies inferred from paper: ROS, Gazebo, ORB-SLAM2, OctoMap, YOLOv8s, BoT-SORT, DWA, RGB-D camera.
- The paper includes many implementation parameters, making partial reimplementation possible even without code.

## Evaluation Weaknesses

- Code is not available, so direct reproduction risk is high.
- Simulation dynamic scenario is narrow: two persons walking on fixed trajectories.
- Real-world experiment has limited quantitative accuracy reporting.
- No ObjectNav metrics: no `Success Rate`, `SPL`, wrong-goal visit, wasted path.
- No open-vocabulary semantic map or pre-explored semantic memory.
- No semantic map precision/recall or semantic accuracy table.
- `RNE` / `RNEX` naming is inconsistent between text and tables.
