# Evaluation

## Dataset / Benchmark

### 사실

| Evaluation target | Dataset / benchmark | Metrics |
| --- | --- | --- |
| 2D open-vocabulary segmentation / descriptor learning | ScanNet++, ImageNet-S validation | `mIoU`, `mAcc`, `f-mIoU`, `f-mAcc`, `Top-1 mAcc`, `Top-5 mAcc` |
| 3D open-vocabulary semantic segmentation | ScanNetv2 validation, Replica 8-scene subset | `mIoU`, `mAcc`, `f-mIoU`, `f-mAcc`, head/common/tail split |
| SLAM-integrated mapping | Replica, ScanNetv2 | semantic segmentation metrics, `ATE RMSE [cm]` |
| Compute / online feasibility | Replica 2k frames per scene | vRAM, RAM, runtime, seconds/keyframe |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing metric |
| --- | --- | --- |
| Step 1 object/node uncertainty | multi-view descriptor consistency, segment confidence proxy | calibrated node uncertainty / entropy not directly reported |
| Step 4 semantic memory to active SLAM utility | loop closure semantic map fusion, online keyframe mapping | active viewpoint utility absent |
| Step 5 SLAM + semantic evaluation | `ATE RMSE`, `mIoU`, `mAcc`, runtime | ObjectNav `SR`, `SPL`, wrong-goal visit |

## Splits

- ScanNet++: main text reports 250 training / 50 validation indoor RGB-D scene sequences; appendix mentions 230 train scenes / 50 validation scenes, so exact count should be rechecked before citing in a thesis table.
- ImageNet-S: validation set, about 12k images and 919 semantic labels.
- ScanNetv2: 312 RGB-D validation sequences, evaluated with ScanNet20 and ScanNet200 label sets.
- HOV-SG subset: 5-scene subset from ScanNetv2 used for comparison.
- Replica: 8 scenes, `office0-4` and `room0-2`, 51 annotated classes.

## Metrics

- Semantic classification / segmentation: `mIoU`, `mAcc`, `f-mIoU`, `f-mAcc`, `Top-1 mAcc`, `Top-5 mAcc`.
- SLAM trajectory: `ATE RMSE [cm]`.
- Compute: average / max vRAM, max RAM, total runtime, average seconds per keyframe.
- Class frequency analysis on Replica: head / common / tail classes.

## Baselines

- Concept-Graphs
- Open-Fusion
- OpenScene
- OpenNeRF
- Open3DIS
- HOV-SG
- Concept-Fusion
- HOV-SG CLIP fusion
- SigLIP / Alpha-CLIP descriptor baselines
- OVO variants: OVO-mapping, OVO-Gaussian-SLAM, OVO-ORB-SLAM2, OVO-ORB-SLAM2 without loop closure

## Main Results

### 논문 주장

- OVO-mapping improves open-vocabulary 3D semantic segmentation on Replica over several offline baselines while using less memory than heavy offline pipelines.
- SLAM-integrated variants remain competitive and expose the tradeoff between trajectory accuracy and semantic segmentation quality.
- Loop closure improves both trajectory and semantic mapping in OVO-ORB-SLAM2 compared with no loop closure.

### Key reported numbers

| Replica 51 classes | `ATE RMSE [cm]` | `mIoU` | `mAcc` |
| --- | --- | --- | --- |
| OpenScene Distilled | - | 14.8 | 23.0 |
| HOV-SG | - | 22.5 | 34.2 |
| Open3DIS | - | 25.6 | 38.7 |
| Concept-Graphs | - | 16.7 | 33.7 |
| Open-Fusion | - | 20.5 | 34.8 |
| OVO-mapping | - | 27.0 | 39.1 |
| OVO-Gaussian-SLAM | 0.6 | 27.1 | 38.6 |
| OVO-ORB-SLAM2 | 1.9 | 25.6 | 39.0 |

| ScanNetv2 HOV-SG subset, ScanNet20 | `ATE RMSE [cm]` | `mIoU` | `mAcc` |
| --- | --- | --- | --- |
| OVO-mapping | - | 38.1 | 50.5 |
| OVO-Gaussian-SLAM | 23.7 | 29.3 | 41.1 |
| OVO-ORB-SLAM2 | 21.5 | 31.3 | 45.2 |
| OVO-ORB-SLAM2 w/o loop closure | 30.2 | 23.6 | 34.5 |

| Descriptor / classification setting | Main result |
| --- | --- |
| ImageNet-S | OVO CLIP merging reports `Top-1 mAcc` 84.8 and `Top-5 mAcc` 96.6 |
| ScanNet++ 2D open-vocabulary | OVO CLIP merging reports higher `f-mIoU` / `f-mAcc` than compared fusion variants |
| Runtime on Replica | OVO-mapping around minutes rather than hours; OVO-ORB-SLAM2 average around 0.67 s/keyframe |

## Reproducibility Notes

- Project page and code are available.
- Local PDF is arXiv:2411.15043v3 [cs.CV], 2025-09-29.
- The pipeline depends on SAM2.1-l, SigLIP ViT-SO400, RGB-D data, and a SLAM backend.
- For CAND-01, first feasibility should avoid full OVO reproduction and instead test a small RGB-D sequence: segment stability, descriptor consistency, semantic accuracy, and loop-closure-before/after map correction.

## Evaluation Weaknesses

- Navigation success로 이어지는지 직접 평가하지 않는다.
- Uncertainty is not exposed as an active planning signal.
- Dataset setup is broad but the exact ScanNet++ train count differs between main text and appendix, so citation should be careful.
- `ATE RMSE` and semantic segmentation are reported together, but causal relation between semantic correction and pose graph quality is not fully isolated.
- Object-level wrong-goal behavior, path waste, and active re-observation cost are outside the evaluation.
