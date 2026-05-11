# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Open-vocabulary semantic mapping | `ScanNet` / `ScanNet200`, `Replica` | `mIoU`, `F-mIoU`, `mAcc`, `ODR`, memory, `TPF` | `ConceptGraphs`, `HOV-SG` |
| Static ObjectNav-style query navigation | `HM3DSem` scenes `00829`, `00848`, `00880` with `YCB` objects | `SR` within 1m | `ConceptGraphs`, `HOV-SG` |
| Dynamic object relocation navigation | custom Habitat scenes with moved `YCB` objects | `SR`, failure breakdown, candidate-selection ablation | random pick, original abstract map `Ma`, updated abstract map `M'a` |
| Real-world navigation | Meeting Room, Apartment, Indoor Hallway, Outdoor scenes | static/dynamic `SR` | no direct standardized baseline table |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 1-3 online semantic map and ObjectNav | `mIoU`, `F-mIoU`, `mAcc`, `ODR`, `SR`, failure breakdown | `SPL`, wrong-goal visit, wasted path, `ATE/RPE`, active re-observation policy |

## Dataset / Benchmark

- Semantic segmentation and efficiency: `ScanNet` / `ScanNet200`, `Replica`.
- `ScanNet` scenes: `scene0011_00`, `scene0050_00`, `scene0231_00`, `scene0378_00`, `scene0518_00`.
- `Replica` scenes: `office0`-`office4`, `room0`-`room2`.
- Static object navigation: `HM3DSem` scenes `00829`, `00848`, `00880`, augmented with `YCB` objects.
- Dynamic navigation: custom `Habitat Simulator` environments with moved `YCB` objects.
- Dynamic change types: in-anchor relocation and cross-anchor relocation.
- Real-world: Meeting Room, Apartment, Indoor Hallway, Outdoor scenes on wheeled and quadruped platforms.
- Additional dynamic-human qualitative test: `TUM RGB-D` Dynamic Objects split, `freiburg3_walking_static`.

## Splits

- The paper uses scene selections following `ConceptGraphs` and `HOV-SG` for mapping evaluation.
- Static `HM3D` navigation uses three scenes and 78 total trials.
- Dynamic in-anchor navigation uses 54 total trials.
- Dynamic cross-anchor navigation uses 53 total trials.
- Real-world static navigation uses 91 trials; real-world dynamic navigation uses 105 trials.
- The paper does not report a learning train/val/test split because the system is mostly training-free / online mapping with pretrained perception models.

## Metrics

- Semantic segmentation: `mIoU`, `F-mIoU`, `mAcc`.
- Object count realism: `ODR` or Object Density Ratio; closer to 1 is better.
- Efficiency: average memory, peak memory, time per frame (`TPF`).
- Navigation: Success Rate (`SR`), successful if the agent stops within 1m of queried object.
- Dynamic navigation success additionally requires finding the target within three attempts.
- Ablation: mapping ablations on `FmIoU`, `mAcc`, `mIoU`; efficiency ablations on `ODR` and `TPF`; relocated-object candidate-selection ablation on `SR`.

## Baselines

- Semantic mapping and navigation: `ConceptGraphs`, `HOV-SG`.
- System comparison table also contrasts `Hydra`, `Khronos`, `CLIO`, and `OpenIN` along open-vocabulary / online mapping / dynamic handling axes.
- For Habitat navigation, the paper extends `ConceptGraphs` and `HOV-SG` to navigate using their query results and the same planning algorithm.

## Main Results

- `Replica` semantic segmentation: `DualMap` mIoU 0.2538, F-mIoU 0.5207, mAcc 0.4024, ODR 0.97, peak memory 4564.0 MB, TPF 0.276s.
- `Replica` baselines: `ConceptGraphs` mIoU 0.1501 / TPF 4.188s; `HOV-SG` mIoU 0.2050 / TPF 42.005s.
- `ScanNet` semantic segmentation: `DualMap` mIoU 0.1604, F-mIoU 0.3288, mAcc 0.3794, ODR 2.56, peak memory 2820.2 MB, TPF 0.163s.
- `ScanNet` baselines: `ConceptGraphs` mIoU 0.0882 / TPF 6.301s; `HOV-SG` mIoU 0.1333 / TPF 8.039s.
- Static `HM3D` navigation average SR: `DualMap` 70.5%, `ConceptGraphs` 61.5%, `HOV-SG` 52.6%.
- Dynamic `HM3D` navigation SR: in-anchor 64.8%, cross-anchor 60.3%.
- Cross-anchor failure breakdown: 28.3% false matches, 9.4% exceeding navigation attempt limits, 1.9% planning errors.
- Candidate selection ablation for relocated objects: random pick 13.2%, original abstract map `Ma` 47.2%, updated abstract map `M'a` 60.3%.
- Real-world SR: Meeting Room 85.7% static / 70.3% dynamic; Apartment 69.6% / 51.5%; Indoor Hallway 78.9% / 55.6%; Outdoor 75.0% / 50.0%.

## Reproducibility Notes

- Local PDF is `arXiv v4`.
- Public code is available at https://github.com/Eku127/DualMap.
- GitHub supports offline datasets, ROS1/ROS2, online simulation with Habitat Data Collector, iPhone streaming, and offline map query.
- Supported datasets in the repository include `Replica`, `ScanNet`, `TUM RGB-D`, and self-collected data using `Habitat Data Collector`.
- Main experiments use NVIDIA RTX 4090 GPU and Intel i7-12700KF CPU.
- Real-world pose estimation is supplied by `FastLIO2` using LiDAR; this is important because the method itself does not estimate camera pose.

## Evaluation Weaknesses

- The navigation metric is `SR` only; the paper does not report `SPL`, wrong-goal visit, wasted path, or path-length-normalized ObjectNav performance.
- `ATE`, `RPE`, map error, pose graph connectivity, and loop closure quality are not evaluated.
- The method uses external localization, so mapping/navigation improvements cannot be interpreted as SLAM accuracy improvements.
- Dynamic evaluation focuses on manually relocated `YCB` objects and may not cover natural human-object interaction patterns.
- Real-world mapping is manually driven before task queries, so active exploration/re-observation policy is not evaluated.
