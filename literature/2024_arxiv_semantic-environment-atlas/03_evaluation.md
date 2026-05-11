# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Habitat ObjectNav | Matterport3D, 61 train scenes, 11 validation scenes, 2,195 validation episodes | Success, `SPL`, `DTS` | `BC`, `DD-PPO`, `Red-Rabbit`, `THDA`, `FBE`, `ANS`, `PONI`, `ANS + SI`, `SemExp + SI` |
| Visual localization | Matterport3D scenes used for SEA | `Acc@0.5m`, `Acc@1m` | `NRNS`, `VGM`, `TSGM` |
| Memory / place-info ablation | same ObjectNav setup | Success, `SPL`, `DTS` | `SEA w/o Update`, subgoal/stop variants |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 3 ObjectNav memory behavior | Success, `SPL`, `DTS`, visual localization accuracy | object/node uncertainty calibration, active re-observation, `ATE/RPE`, map error |

## Dataset / Benchmark

- Simulator: Habitat.
- Scene dataset: Matterport3D.
- Task: Habitat ObjectNav.
- Goal categories: 21 ObjectNav goal categories from Matterport3D.
- SEA construction data: 10 random exploration episodes per training scene, 610 episodes total, maximum 500 steps per episode.
- Visual data for encoder training: 5,000 panoramic RGB images per training environment, 305,000 images total.

## Splits

- Matterport3D standard split: 61 train scenes and 11 validation scenes.
- ObjectNav evaluation: 2,195 test episodes on validation scenes.
- Episode budget: 500 steps.
- Success threshold: 1.0m from goal object.

## Metrics

- ObjectNav: Success, SPL, DTS.
- Visual localization: Acc@0.5m, Acc@1m.
- Robustness: Success degradation under pose/action noise.
- Cost: training GPU hours, inference GPU memory, inference computational cost.

## Baselines

- Non-interactive / end-to-end: `BC`, `DD-PPO`, `Red-Rabbit`, `THDA`.
- Metric map: `FBE`, `ANS`, `PONI`.
- Graph / semantic prior: `ANS + SI`, `SemExp + SI`.
- Visual localization: `NRNS`, `VGM`, `TSGM`.
- Ablation: `SEA w/o Update`, subgoal/stop variants without place information.

## Main Results

- ObjectNav Table 1: `SEA` reports Success 39.0, SPL 13.7, DTS 5.0.
- `SEA w/o Update` reports Success 33.3, SPL 13.6, DTS 5.7.
- Best listed baseline Success is `SemExp + SI` at 34.7; its SPL is 15.1 and DTS is 5.8.
- `SEA` has lower SPL than `SemExp + SI`, but higher Success and lower DTS.
- Visual localization Table 2: `SEA` reports Acc@0.5m 40.4 and Acc@1m 73.1.
- Place-information ablation Table 3: adding place-based subgoal selection increases Success from 29.2 to 36.4; adding stop adjustment reports Success 39.0.

## Reproducibility Notes

- Local PDF is available as `paper.pdf`.
- No official code or project page was found from arXiv / ScienceDirect pages on 2026-05-07.
- Implementation depends on Matterport3D / Habitat access, MaskRCNN detector for Matterport3D object categories, trained ResNet18-based encoders, graph construction, and local depth-map navigation.
- Full reproduction is likely heavier than a first hypothesis probe. A smaller probe can reproduce the uncertainty/update logic on a precomputed semantic graph or replayed ObjectNav episodes.

## Evaluation Weaknesses

- The evaluation does not include `ATE`, `RPE`, map error, pose graph connectivity, or loop closure quality.
- Relation update is evaluated through ObjectNav behavior, not through calibrated semantic uncertainty metrics.
- Wrong-goal visit and wasted path are not reported directly.
- The paper evaluates prior semantic memory for navigation, but not active selection of re-observation viewpoints.
- Real-world robot deployment is not evaluated.
