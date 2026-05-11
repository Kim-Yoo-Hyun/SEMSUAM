# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Active semantic exploration | Habitat + Matterport3D, two indoor environments, 10 repetitions each | `ATE`, map error, semantic `IoU`, explored volume over time | `SSMI`, `TARE` |
| Utility evidence | semantic octomap + pose graph spectral utility | final `ATE` / map error / semantic `IoU`; pose graph term is used inside utility | semantic-only mutual information and exploration baseline |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4-5 active SLAM utility | `ATE`, map error, semantic `IoU`, explored volume | ObjectNav `SR` / `SPL`, wrong-goal visit, open-vocabulary semantic map uncertainty |

## Dataset / Benchmark

### 사실

- Benchmark environment: Habitat simulator.
- Scene source: Matterport3D.
- Number of environments: two indoor environments.
- Repetitions: 10 exploration repetitions per environment.
- Robot sensor: RGB-D camera.
- Semantic segmentation source: Habitat simulator.
- Semantic segmentation resolution / rate: 640 x 360, 30 Hz.
- Mapping representation: semantic octomap.
- Map resolution: 0.25 m.
- Semantic mapping rate: 2 Hz.
- SLAM backend: graph-based visual SLAM using ORB-SLAM2-style frontend and g2o backend.
- Hardware reported: Intel Core i5-11400H CPU and NVIDIA GeForce RTX 3060 GPU laptop.

## Splits

- Standard train/test split은 보고되지 않는다.
- Experiment 1: smaller Matterport3D environment, 5 minute stopping criterion.
- Experiment 2: larger Matterport3D environment, 10 minute stopping criterion.
- Each environment is repeated 10 times.
- Semantic `IoU` evaluation uses top eight frequent categories in each experiment.

### 사용자 판단 필요

- Exact Matterport3D scene IDs가 paper text에 명시되어 있지 않아 재현 전 code/config 확인이 필요하다.

## Metrics

- `ATE`: localization evaluation, computed with `evo`.
- Map error: mean Euclidean distance between estimated map and ground truth map, evaluated with CloudCompare.
- Semantic `IoU`: top eight frequent semantic categories.
- Explored volume over time: exploration efficiency.
- Pose graph D-optimality / connectivity: used inside utility, but not separately reported as a final table metric.
- Localization failure: observed in baseline runs, but not reported as a primary metric.

## Baselines

- `SSMI`: Semantic Shannon Mutual Information, information-theoretic active semantic mapping baseline.
- `TARE`: hierarchical exploration baseline used in large-scale exploration.
- Baseline settings: default parameters, according to paper.

### Missing Baselines for My Research

- No `ObjectNav` baseline.
- No `CARe`-style pre-explored semantic map replanning baseline.
- No open-vocabulary semantic map baseline such as `VLMaps` or `ConceptGraphs`.
- No explicit `SemanticOnly` / `SLAMOnly` ablation table for the proposed utility.

## Main Results

### 논문 주장

- Average localization error reduction: maximum 38%.
- Average map error reduction: maximum 21%.
- Semantic classification accuracy improvement: about 9%.
- Proposed method has the lowest localization and map errors in 8 / 10 repetitions for experiment 1 and 9 / 10 repetitions for experiment 2.
- Exploration efficiency is close to `SSMI`, with slight time overhead.
- `TARE` can show better exploration speed in larger environments because its hierarchy is designed for large-scale exploration.

### Table Results

| Experiment | Metric | Ours | SSMI | TARE |
| --- | --- | ---: | ---: | ---: |
| Experiment 1 | Average semantic `IoU` | 42.15 | 40.72 | 32.82 |
| Experiment 2 | Average semantic `IoU` | 41.82 | 36.18 | 32.76 |

### 에이전트 추론

The result pattern supports using pose graph uncertainty as an active utility term, but it does not by itself prove ObjectNav improvement. For `CAND-01`, this paper is stronger as Step 4-5 evidence than as Step 1-3 evidence.

## Reproducibility Notes

- Code is public: https://github.com/BohemianRhapsodyz/semantic_exploration
- Repository dependencies include ROS Noetic, OctoMap, PCL, Eigen, OpenCV, Python3.
- Repository launch path indicates separate localization, mapping, and planning processes.
- The paper uses rosbag logging, `evo`, CloudCompare, Habitat, ORB-SLAM2/g2o, semantic octomap.
- Exact scene IDs and full parameter config need code inspection.
- Current repo has not executed the code.

## Evaluation Weaknesses

- Habitat-centered simulation; no field experiment in this paper.
- Semantic segmentation is simulator-provided, so detector error and open-vocabulary ambiguity are under-tested.
- Baseline localization loss is excluded from some fair comparisons instead of being elevated to a failure metric.
- Two environments may be too narrow for generalization claims.
- No direct ObjectNav task metric such as `Success Rate`, `SPL`, wrong-goal visit, or wasted path.
- No `RPE` report, although `ATE` is reported.
- Pose graph connectivity is central to the method but not exposed as a final user-facing evaluation table.
