# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Active mapping with localization-aware utility | Habitat Simulator, Gibson validation scenes, 2000 steps | `PSNR`, `SSIM`, `LPIPS`, `Depth MAE`, `RMSE ATE`, `Completeness` | `ANS`, `UPEN`, `ExplORB`, `FBE` |
| Active mapping on larger indoor scenes | Habitat Simulator, 5 `HM3D` train scenes | same rendering / depth / localization / completeness metrics | `UPEN`, `ExplORB`, `FBE` |
| LLM and localization uncertainty ablation | `HM3D` setting | same metrics | no-LLM, no-localization-uncertainty, `Llava-7b`, regularizer variants |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4-5 localization-aware active mapping | `RMSE ATE`, `Completeness`, rendering/depth quality | semantic object/node accuracy, ObjectNav `SR` / `SPL`, `RPE`, pose graph connectivity |

## Dataset / Benchmark

### 사실

- Simulator: Habitat Simulator.
- Datasets in paper: Gibson and Habitat-Matterport 3D (`HM3D`).
- Environment type: indoor scenes reconstructed from scans of real houses.
- Sensor input: RGB-D.
- Image resolution: 800 x 800.
- Action space: `MOVE_FORWARD` by 5 cm, `TURN_LEFT` by 5 degrees, `TURN_RIGHT` by 5 degrees.
- Field of view: 90 degrees vertical and horizontal.
- Episode budget: 2000 steps.
- Starting point: default Habitat Simulator start point for each scene.
- Main model uses `GPT-4o`; ablation includes `Llava-7b`.

### 에이전트 추론

This benchmark is closer to active mapping / active SLAM than to ObjectNav. For `CAND-01`, it provides Step 4-5 map/localization metrics, not Step 3 ObjectNav metrics.

## Splits

### 사실

- Gibson: all scenes in the validation split according to the paper.
- HM3D: 5 scenes from the train split according to the paper.
- The PDF says the supplement contains more split / hyperparameter details.
- The local repository README primarily describes `Matterport3D (MP3D)` Habitat subset setup and the example scene `2azQ1b91cZZ`, which does not exactly match the paper's HM3D wording.

### 사용자 판단 필요

- If P09 becomes an implementation baseline, verify whether the released code reproduces the ICCV paper's `HM3D` setup or an earlier `MP3D` setup.

## Metrics

### 사실

- `PSNR`: RGB rendering reconstruction quality; higher is better.
- `SSIM`: RGB rendering structural similarity; higher is better.
- `LPIPS`: perceptual RGB rendering distance; lower is better.
- `Depth MAE`: depth rendering error; lower is better.
- `RMSE ATE`: root mean squared average tracking error; lower is better.
- `Completeness (%)`: completion / coverage-style map completeness; higher is better.
- Evaluation samples 2000 points uniformly from the agent movement plane and discards non-navigable points.

### Not Reported

- No ObjectNav `Success Rate`.
- No ObjectNav `SPL`.
- No wrong-goal visit.
- No wasted path.
- No `RPE`.
- No semantic object/node accuracy.
- No pose graph connectivity metric.

## Baselines

### 사실

- `ANS` / Active Neural SLAM.
- `UPEN`.
- `Active Neural Mapping` / `active-INR`.
- `ExplORB`.
- `FBE` / Frontier Based Exploration.
- On HM3D, `ANS` is not run because it is not trained on the dataset.
- For fair rendering-quality comparison, the paper runs all baselines using `MonoGS` backend for reconstruction.
- `UPEN` and `FBE` are run online.
- `ANS`, `active-INR`, and `ExplORB` trajectories are recorded / replayed from their source code.
- `UPEN` and `active-INR` do not produce pose estimates in the evaluation setting, so the paper evaluates them with ground-truth pose.
- `ANS` pose estimates are used to set the `MonoGS` backend pose estimate.

### 에이전트 추론

Baseline comparison is carefully normalized around the reconstruction backend, but it is not a clean policy-only comparison because some methods use ground-truth pose while P09 estimates pose. This matters when translating the metric contract into `CAND-01`.

## Main Results

### Gibson

| Method | PSNR | SSIM | LPIPS | Depth MAE | RMSE ATE | Completeness (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `ANS` | 16.34 | 0.6818 | 0.3923 | 0.3886 | 0.1105 | 35.33 |
| `UPEN` | 16.44 | 0.6678 | 0.4134 | 0.4841 | 0.5158 | 22.66 |
| `ExplORB` | 18.99 | 0.7175 | 0.3994 | 0.2664 | 0.2296 | 30.23 |
| `FBE` | 21.45 | 0.7618 | 0.2126 | 0.1028 | 0.1680 | 55.87 |
| Ours | 23.28 | 0.8067 | 0.2507 | 0.0696 | 0.0226 | 84.38 |

### HM3D

| Method | PSNR | SSIM | LPIPS | Depth MAE | RMSE ATE | Completeness (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `UPEN` | 12.23 | 0.4795 | 0.5157 | 0.7356 | 0.4393 | 17.48 |
| `ExplORB (gt)` | 17.81 | 0.3694 | 0.6810 | 0.5071 | - | 31.92 |
| `FBE` | 15.80 | 0.5952 | 0.4392 | 0.4085 | 1.2004 | 22.42 |
| Ours | 19.86 | 0.7127 | 0.4122 | 0.1666 | 0.0336 | 49.76 |

### Ablation on HM3D

| Method | PSNR | SSIM | LPIPS | Depth MAE | RMSE ATE | Completeness (%) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| w.o. LLM & Localization Uncertainty | 16.15 | 0.6550 | 0.6193 | 0.3409 | 0.2478 | 35.40 |
| w.o. LLM | 16.94 | 0.6799 | 0.5847 | 0.2887 | 0.1694 | 37.26 |
| Ours (`Llava-7b`) | 18.46 | 0.6805 | 0.4623 | 0.2033 | 0.0159 | 17.41 |
| regularizer 2e-6 with `GPT-4o` | 18.90 | 0.6976 | 0.4408 | 0.1966 | 0.0479 | 18.12 |
| regularizer 5e-6 with `GPT-4o` | 18.90 | 0.6946 | 0.4602 | 0.2145 | 0.0551 | 18.05 |
| Ours with `GPT-4o` | 19.86 | 0.7127 | 0.4122 | 0.1666 | 0.0336 | 49.76 |

### 논문 주장

- The paper states that the method outperforms baselines on all metrics.
- Localization uncertainty reduces `RMSE ATE` and improves reconstruction metrics compared with no-localization-uncertainty ablation.
- Adding `GPT-4o` long-horizon planning improves all reported metrics over no-LLM and no-localization-uncertainty variants.

### 에이전트 추론

- In the Gibson table, `FBE` has better `LPIPS` than Ours, so the broad "all metrics" statement should be read carefully.
- On HM3D, the method has best reported `PSNR`, `SSIM`, `LPIPS`, `Depth MAE`, `RMSE ATE`, and `Completeness` among compared methods with available values.

## Reproducibility Notes

### 사실

- CVF PDF and arXiv page are accessible.
- Official code is linked from the author's website and GitHub.
- Code README recommends Docker.
- Code setup requires custom CUDA extensions under `thirdparty/`, Habitat, `OPENAI_API_KEY`, and dataset paths.
- GitHub README includes a real-world demo link.
- Repository has low commit count and no releases at check time.
- Code README still contains internal cluster paths and notes about a future major refactor.
- GitHub README's data section says it uses `Matterport3D (MP3D)` Habitat subset, while the paper reports `HM3D`; this needs verification before reproduction.

### 에이전트 추론

The code is useful for inspecting planner structure, configs, and metric implementation, but a direct full benchmark reproduction is risky. A practical `CAND-01` first-use path is to borrow the metric contract and uncertainty utility concept, not to reproduce the full 3DGS active mapping stack immediately.

## Evaluation Weaknesses

- Evaluation is simulator-only in the paper; real-world evidence is in linked demo, not benchmark table.
- Object-level semantic mapping is not evaluated.
- The semantic contribution is long-horizon exploration through LLM prior, not open-vocabulary semantic map correctness.
- `RMSE ATE` is reported, but `RPE` and pose graph connectivity are missing.
- Rendering quality is used as a proxy that reflects both reconstruction and pose accuracy, which may blur failure attribution.
- `Llava-7b` ablation has very low `RMSE ATE` but low `Completeness`, showing that better tracking alone does not imply better exploration.
- Baselines differ in pose availability and training assumptions.
- The paper does not evaluate whether the selected views improve downstream ObjectNav behavior.
