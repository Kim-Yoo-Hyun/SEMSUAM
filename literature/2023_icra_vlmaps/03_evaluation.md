# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Multi-object navigation | Habitat + Matterport3D, 91 task sequences, 4 subgoals each | in-a-row `SR`, independent subgoal success | `LM-Nav`, `CoW`, `CLIP Map`, `GT Map` |
| Spatial goal navigation | Habitat + Matterport3D, 21 trajectories in 7 scenes | in-a-row `SR` | `LM-Nav`, `CoW`, `CLIP Map`, `GT Map` |
| Cross-embodiment navigation | `AI2THOR`, more than 100 subgoal sequences | `SR`, `SPL` | embodiment-specific obstacle map variants |
| Real-world HSR demo | semantically rich indoor scene, 374 mapping frames | successful goals / total goals | no standardized baseline |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 1-3 pre-explored open-vocabulary map baseline | `SR`, `SPL` in limited setting, semantic map `mIOU` appendix | wrong-goal visit, wasted path, uncertainty calibration, `ATE/RPE`, active re-observation |

## Dataset / Benchmark

- Multi-object and spatial goal navigation: `Habitat` simulator with `Matterport3D`.
- Cross-embodiment obstacle map evaluation: `AI2THOR`.
- Real-world evaluation: HSR mobile robot in a semantically rich indoor scene.
- Map creation in Habitat: 12,096 RGB-D frames across 10 scenes.
- Map creation in AI2THOR: 1,826 RGB-D frames across 10 rooms.
- Real-world map creation: 374 frames; `RTAB-Map` estimates camera poses and initializes global localization.

## Splits

- Multi-object navigation: 91 task sequences; each sequence has 4 subgoals sampled from 30 object categories.
- Spatial goal navigation: 21 trajectories in 7 scenes; each trajectory has 4 spatial subgoals.
- Cross-embodiment navigation: more than 100 sequences of subgoals in `AI2THOR`.
- The paper does not define a supervised train/validation/test split because the method uses pretrained models and zero-shot map indexing.

## Metrics

- Multi-object navigation: in-a-row Success Rate (`SR`) for 1, 2, 3, 4 consecutive subgoals and independent subgoal success.
- Spatial goal navigation: in-a-row Success Rate (`SR`) for 1, 2, 3, 4 consecutive spatial subgoals.
- Cross-embodiment navigation: `SR` and `SPL`.
- Success threshold: stop position within 1m of the correct object or spatial subgoal.
- Top-down map semantic segmentation appendix: pixel accuracy, mean accuracy, `mIOU`, frequency weighted `mIOU`, per-class `IOU`.

## Baselines

- `LM-Nav`: graph of image observations; uses `GPT-3` and `CLIP` to parse landmarks and plan on graph nodes.
- `CoW`: `CLIP` + `GradCAM` saliency map for language-based object navigation.
- `CLIP Map`: ablation that projects `CLIP` visual features into a map instead of `LSeg` features.
- `GT Map`: ground-truth semantic map upper bound.

## Main Results

- Multi-object navigation Table I, 1-subgoal SR: `VLMaps` 59 vs `LM-Nav` 26, `CoW` 42, `CLIP Map` 33, `GT Map` 91.
- Multi-object navigation Table I, 4-subgoal in-a-row SR: `VLMaps` 15 vs `LM-Nav` 1, `CoW` 3, `CLIP Map` 0, `GT Map` 67.
- Multi-object independent subgoal SR: `VLMaps` 59 vs `LM-Nav` 26, `CoW` 36, `CLIP Map` 30, `GT Map` 85.
- Spatial goal navigation Table II, 1-subgoal SR: `VLMaps` 62 vs `LM-Nav` 5, `CoW` 33, `CLIP Map` 19, `GT Map` 76.
- Spatial goal navigation Table II, 4-subgoal in-a-row SR: `VLMaps` 10 vs all three non-GT baselines 0, `GT Map` 29.
- Cross-embodiment Table III: drone with drone-specific obstacle map improves 4-subgoal SR to 7 and independent SR to 55.0, compared with drone using ground map 6 and 53.3.
- Top-down semantic segmentation Table V: `VLMaps` pixel accuracy 92.3, mean accuracy 27.7, `mIOU` 19.0, frequency weighted `mIOU` 85.9; `CoW Map` reports 66.1, 9.6, 5.7, 42.9.
- Real-world HSR experiment: 10 successful navigation goals out of 20.

## Reproducibility Notes

- Local PDF is arXiv v4.
- Official repository is public: https://github.com/vlmaps/vlmaps
- Repository supports dataset generation from Matterport3D/Habitat, VLMap creation, map indexing, object goal navigation, spatial goal navigation, and customized datasets.
- Repository requires Matterport3D data access for the original simulated setup.
- Navigation evaluation needs an OpenAI API key for the LLM planning/indexing path when using category matching through GPT.
- Repository has no GitHub releases as of 2026-05-07.

## Evaluation Weaknesses

- The paper does not report `ATE`, `RPE`, map error, pose graph connectivity, or loop closure quality.
- The method depends on external odometry / SLAM poses, so map/navigation success does not imply SLAM improvement.
- `SPL` is only reported in cross-embodiment experiments, not for the core multi-object or spatial-goal navigation tasks.
- Wrong-goal visit and wasted path are not separately measured.
- Dynamic object handling and active re-observation are not evaluated.
- The 1m success threshold may hide near-miss and wrong-instance behavior.
