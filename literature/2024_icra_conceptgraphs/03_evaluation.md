# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| 3D scene graph construction | `Replica` `room0-2`, `office0-3` | node precision, valid objects, duplicates, edge precision | `ConceptGraphs`, `ConceptGraphs-Detector` |
| Open-vocabulary 3D semantic segmentation | `Replica`, `ConceptFusion` protocol | `mAcc`, `F-mIoU` | `CLIPSeg`, `LSeg`, `OpenSeg`, `MaskCLIP`, `ConceptFusion`, variants |
| Text-query object retrieval | `Replica`, `REAL Lab` scan | `R@1`, `R@2`, `R@3` by query type | `CLIP`, `LLM` over scene graph |
| Real-world demos | Jackal, Spot, REAL Lab / mapped indoor scenes | qualitative task success | no standardized benchmark baseline |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 1 semantic memory quality | node precision, edge precision, `R@k`, `mAcc`, `F-mIoU` | ObjectNav `SR` / `SPL`, wrong-goal visit, active re-observation utility, `ATE/RPE` |

## Dataset / Benchmark

### 사실

- Main quantitative dataset: `Replica`.
- Scene graph quality uses `Replica` scenes `room0`, `room1`, `room2`, `office0`, `office1`, `office2`, `office3`.
- Open-vocabulary 3D semantic segmentation uses `Replica`, following the `ConceptFusion` evaluation protocol.
- Object retrieval uses `Replica` and a real-world `REAL Lab` scan.
- Real-world navigation uses a `Clearpath Jackal UGV` with `VLP-16 LiDAR` and forward-facing `Realsense D435i`.
- Navigation setup builds an initial `REAL Lab` point cloud with onboard `VLP-16` and `Open3D SLAM`, then downprojects it to a 2D costmap.
- Object-search / traversability scenes are mapped with an `Azure Kinect` and `RTAB-Map` poses.
- Open-vocabulary mobile manipulation is demonstrated on a `Boston Dynamics Spot Arm`.
- Localization / map-update demonstration uses `AI2Thor` / `ProcThor`-style simulation, but the README notes no quantitative AI2Thor evaluation was performed.

## Splits

### 사실

- Scene graph construction: 7 `Replica` scenes: `room0`, `room1`, `room2`, `office0`, `office1`, `office2`, `office3`.
- Text-query retrieval on `Replica`: descriptive, affordance, and negation query types.
- Table III reports `Replica` query counts as 20 descriptive, 5 affordance, and 5 negation.
- Table III reports `REAL Lab` query counts as 10 descriptive, 10 affordance, and 10 negation.
- Appendix lists example query sets for `Replica` office/room scenes and `REAL Lab`.

### 사용자 판단 필요

- For `CAND-01`, decide whether the first probe should reuse `Replica` for graph quality, `AI2Thor` for controlled interaction, or Habitat ObjectNav for direct task behavior.

## Metrics

### Scene Graph Construction

- `node precision`: fraction of nodes for which at least 2 of 3 AMT evaluators judge the node caption correct.
- `valid objects`: number of human-recognizable objects found.
- `duplicates`: number of redundant detections.
- `edge precision`: AMT-evaluated accuracy of estimated spatial relationship labels.

### Semantic Segmentation

- `mAcc`: mean class accuracy.
- `F-mIoU`: frequency-weighted mean intersection-over-union.

### Text Query Object Retrieval

- `R@1`, `R@2`, `R@3`: top-k recall for object retrieval from language queries.
- Query types: descriptive, affordance, negation.

### Not Reported

- No ObjectNav `Success Rate`.
- No ObjectNav `SPL`.
- No wrong-goal visit.
- No wasted path.
- No `ATE` / `RPE`.
- No pose graph connectivity.
- No active re-observation cost / information gain metric.
- No standardized quantitative real-world navigation success metric.

## Baselines

### Scene Graph Construction

- `ConceptGraphs` (`CG`)
- `ConceptGraphs-Detector` (`CG-D`)

### Semantic Segmentation

- Privileged methods: `CLIPSeg (rd64-uni)`, `LSeg`, `OpenSeg`.
- Zero-shot methods: `MaskCLIP`, `Mask2former + Global CLIP feat`, `ConceptFusion`, `ConceptFusion + SAM`, `ConceptGraphs`, `ConceptGraphs-Detector`.

### Text Query Retrieval

- `CLIP`: cosine similarity between query embedding and object features.
- `LLM`: LLM parses scene graph nodes and returns relevant object.

### Qualitative / Concurrent Comparisons

- The paper discusses `OpenMask3D`, `OVIR-3D`, `OGSV`, and `SayPlan`, but these are not used as quantitative baselines in the main tables.

## Main Results

### Table I: Scene Graph Accuracy on Replica

| Variant | Scene | Node precision | Valid objects | Duplicates | Edge precision |
| --- | --- | ---: | ---: | ---: | ---: |
| `CG` | `room0` | 0.78 | 54 | 3 | 0.91 |
| `CG` | `room1` | 0.77 | 43 | 4 | 0.93 |
| `CG` | `room2` | 0.66 | 47 | 4 | 1.00 |
| `CG` | `office0` | 0.65 | 44 | 2 | 0.88 |
| `CG` | `office1` | 0.65 | 23 | 0 | 0.90 |
| `CG` | `office2` | 0.75 | 44 | 3 | 0.82 |
| `CG` | `office3` | 0.68 | 60 | 5 | 0.79 |
| `CG` | Average | 0.71 | - | - | 0.88 |
| `CG-D` | `room0` | 0.56 | 60 | 4 | 0.87 |
| `CG-D` | `room1` | 0.70 | 40 | 3 | 0.93 |
| `CG-D` | `room2` | 0.54 | 49 | 2 | 0.93 |
| `CG-D` | `office0` | 0.59 | 35 | 0 | 1.00 |
| `CG-D` | `office1` | 0.49 | 24 | 2 | 0.90 |
| `CG-D` | `office2` | 0.67 | 47 | 3 | 0.88 |
| `CG-D` | `office3` | 0.71 | 59 | 1 | 0.83 |
| `CG-D` | Average | 0.61 | - | - | 0.91 |

### Table II: Open-Vocabulary Semantic Segmentation on Replica

| Group | Method | mAcc | F-mIoU |
| --- | --- | ---: | ---: |
| Privileged | `CLIPSeg (rd64-uni)` | 28.21 | 39.84 |
| Privileged | `LSeg` | 33.39 | 51.54 |
| Privileged | `OpenSeg` | 41.19 | 53.74 |
| Zero-shot | `MaskCLIP` | 4.53 | 0.94 |
| Zero-shot | `Mask2former + Global CLIP feat` | 10.42 | 13.11 |
| Zero-shot | `ConceptFusion` | 24.16 | 31.31 |
| Zero-shot | `ConceptFusion + SAM` | 31.53 | 38.70 |
| Zero-shot | `ConceptGraphs` | 40.63 | 35.95 |
| Zero-shot | `ConceptGraphs-Detector` | 38.72 | 35.82 |

### Table III: Object Retrieval from Text Queries

| Dataset | Query type | Model | R@1 | R@2 | R@3 | # Queries |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `Replica` | Descriptive | `CLIP` | 0.59 | 0.82 | 0.86 | 20 |
| `Replica` | Descriptive | `LLM` | 0.61 | 0.64 | 0.64 | 20 |
| `Replica` | Affordance | `CLIP` | 0.43 | 0.57 | 0.63 | 5 |
| `Replica` | Affordance | `LLM` | 0.57 | 0.63 | 0.66 | 5 |
| `Replica` | Negation | `CLIP` | 0.26 | 0.60 | 0.71 | 5 |
| `Replica` | Negation | `LLM` | 0.80 | 0.89 | 0.97 | 5 |
| `REAL Lab` | Descriptive | `CLIP` | 1.00 | - | - | 10 |
| `REAL Lab` | Descriptive | `LLM` | 1.00 | - | - | 10 |
| `REAL Lab` | Affordance | `CLIP` | 0.40 | 0.60 | 0.60 | 10 |
| `REAL Lab` | Affordance | `LLM` | 1.00 | - | - | 10 |
| `REAL Lab` | Negation | `CLIP` | 0.00 | - | - | 10 |
| `REAL Lab` | Negation | `LLM` | 1.00 | - | - | 10 |

### 논문 주장

- `CG` has higher average node precision than `CG-D`; `CG-D` has slightly higher average edge precision.
- ConceptGraphs semantic segmentation is comparable with or better than `ConceptFusion` while using a smaller memory footprint.
- `CLIP` retrieval is strong for descriptive queries but weak for affordance and negation queries.
- LLM retrieval over scene graph captions performs better on complex affordance and negation queries.

## Reproducibility Notes

### 사실

- Official code and project page are available.
- README says ConceptGraphs takes posed RGB-D images as input.
- README uses `Replica` / Nice-SLAM RGB-D trajectories as the example dataset setup.
- README states the code was tested with Python 3.10.12 and PyTorch 2.0.1 / CUDA 11.8 in one example setup.
- Setup includes `Pytorch3D`, `GradSLAM`, `Grounded-SAM`, `SAM`, `RAM`, `Grounding DINO`, `LLaVA`, and `OpenAI` API key for `GPT-4`.
- README states `Grounded-SAM` and `LLaVA` were tested at specific commits.
- README reports semantic segmentation evaluation outputs `mrecall` as `mAcc` and `fmiou` as `F-mIoU`.
- README states `ali-dev` is a real-time, streamlined reimplementation with iPhone RGB-D video support.
- Separate Jackal code is linked from the README.

### 에이전트 추론

For `CAND-01`, direct full reproduction is possible but dependency-heavy. A practical path is to start from saved object graph outputs or a small `Replica`/AI2Thor scene, then define uncertainty fields and active re-observation probes before adopting the full real-world stack.

## Evaluation Weaknesses

- Graph quality evaluation relies on AMT judgments, not fully automatic ground truth.
- Real-world Jackal and Spot tasks are mainly demonstrations, not standardized benchmarks.
- Input poses are assumed, so localization uncertainty is outside the main evaluation.
- `AI2Thor` support exists in code, but README states no quantitative AI2Thor evaluation was performed.
- LLM/LVLM model quality directly affects captions, relations, and planning.
- Small/thin object misses and duplicate detections can cause downstream planning failures.
- The paper does not evaluate active viewpoint selection for fixing graph errors.
- There is no direct ObjectNav behavior metric, despite strong relevance to ObjectNav memory.
