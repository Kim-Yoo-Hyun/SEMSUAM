# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Active neural reconstruction | HabitatSim + Replica 8 scenes, MP3D 5 scenes | `MAD`, `Accuracy`, `Completion`, `Completion Ratio` | `FBE`, `UPEN`, `OccAnt`, `ANM` |
| Neural SLAM / mapping ablation | Replica, 5 repeats | `Accuracy`, `Completion`, `Completion Ratio` mean/variance | `iMAP`, `NICE-SLAM`, `Co-SLAM`, `Co-SLAM w/ ActRay`, ablations |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4 map quality probe | reconstruction `Accuracy`, `Completion`, `Completion Ratio` | semantic map accuracy, ObjectNav behavior, `ATE/RPE`, wrong-goal visit |

## Dataset / Benchmark

### 사실

- Simulator: HabitatSim.
- Datasets: Replica and Matterport3D / MP3D.
- Replica scenes: 8 scenes.
- MP3D scenes: 5 scenes.
- Input: posed RGB-D images.
- Image resolution: 680 x 1200.
- Field of view: 60 degrees vertical, 90 degrees horizontal.
- Voxel size for 3D volume generation: 10 cm.
- Mapping backbone: `Co-SLAM`.

## Splits

- Replica runs for 2000 steps.
- MP3D runs for 5000 steps.
- Each active planning experiment is repeated 5 times and average results are reported.
- Agent starting position is randomly initialized within traversable space for each trial.
- Individual scene results are delegated to supplementary material.

## Metrics

- `MAD` (cm): mean absolute distance between estimated SDF distance and ground-truth mesh vertices.
- `Accuracy` (cm): mean nearest distance with respect to prediction.
- `Completion` (cm): reconstruction completeness distance.
- `Completion Ratio` (%): completion ratio with a 5 cm threshold.
- Replica table reports mean and variance for `Accuracy`, `Completion`, and `Completion Ratio`.

### Not Central in This Paper

- No ObjectNav `Success Rate` / `SPL`.
- No wrong-goal visit or wasted path.
- No `ATE/RPE`.
- No semantic accuracy / object precision / recall.

## Baselines

### MP3D Baselines

- `FBE`
- `UPEN`
- `OccAnt`
- `ANM`

### Replica / Ablation Baselines

- `iMAP`
- `NICE-SLAM`
- `Co-SLAM`
- `Co-SLAM w/ ActRay`
- `w/o ActiveRay`
- `Uncertainty Net`
- `Full`

## Main Results

### MP3D Results

| Method | `MAD` | `Accuracy` | `Completion` | `Completion Ratio` |
| --- | ---: | ---: | ---: | ---: |
| `FBE` | / | / | 9.78 | 71.18 |
| `UPEN` | / | / | 10.60 | 69.06 |
| `OccAnt` | / | / | 9.40 | 71.72 |
| `ANM` | 4.29 | 7.80 | 9.11 | 73.15 |
| NARUTO | 1.44 | 6.31 | 3.00 | 90.18 |

### Replica Results and Ablations

| Task | Method | `Accuracy` mean | `Completion` mean | `Completion Ratio` mean |
| --- | --- | ---: | ---: | ---: |
| Neural SLAM | `iMAP` | 3.62 | 4.93 | 80.50 |
| Neural SLAM | `NICE-SLAM` | 2.37 | 2.63 | 91.13 |
| Neural SLAM | `Co-SLAM` | 2.30 | 2.35 | 92.74 |
| Neural SLAM | `Co-SLAM w/ ActRay` | 2.30 | 2.35 | 92.70 |
| Neural Mapping | `Co-SLAM` | 1.96 | 2.00 | 93.79 |
| Neural Mapping | `Co-SLAM w/ ActRay` | 1.96 | 1.98 | 93.90 |
| Neural Active Mapping | `w/o ActiveRay` | 1.67 | 1.76 | 96.89 |
| Neural Active Mapping | `Uncertainty Net` | 1.69 | 2.05 | 94.62 |
| Neural Active Mapping | `Full` | 1.61 | 1.66 | 97.20 |

### 논문 주장

- MP3D에서 NARUTO는 `ANM` 대비 `Completion Ratio`를 73.15에서 90.18로 개선한다고 주장한다.
- Replica에서 `Full` method는 `w/o ActiveRay`와 `Uncertainty Net`보다 best mean `Accuracy`, `Completion`, `Completion Ratio`를 보인다고 주장한다.
- Active Ray Sampling은 Neural SLAM / Neural Mapping에서 variance를 줄이고 result consistency를 개선한다고 주장한다.

## Reproducibility Notes

- CVF paper and arXiv v2 are accessible.
- Project page: https://oppo-us-research.github.io/NARUTO-website/
- Official code: https://github.com/oppo-us-research/NARUTO
- GitHub provides Docker and Anaconda environment paths.
- GitHub lists HabitatSim and Co-SLAM as key dependencies.
- GitHub provides `scripts/naruto/run_replica.sh` and `scripts/naruto/run_mp3d.sh`.
- Matterport3D download is not included due to terms of use; users must download task data separately.
- Current repo has not run the code.

## Evaluation Weaknesses

- Known localization and perfect action execution are assumed.
- Reconstruction metrics dominate; no navigation task behavior metrics.
- No semantic map / object-level evaluation.
- MP3D `Accuracy` can be penalized by incomplete ground-truth scans and neural extrapolation, as the paper itself notes.
- Full system dependency is heavy for a quick `CAND-01` first probe.
