# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Uncertainty estimation | Hotdog, Hubble, Room with deliberately unobserved regions | qualitative entropy maps | `WD`, `ActiveRMAP`, `AIR`, `ActiveNeRF`, `NeurAR` |
| Active mapping / reconstruction | original NeRF synthetic assets, Hubble, custom Room scene | `PSNR`, `SSIM`, `LPIPS`, `RGB`, `Acc`, `Comp`, `CR`, `Vis` | `Random`, `WD`, `ActiveRMAP`, `AIR`, `ActiveNeRF`, `NeurAR` |
| Ablation / optimization | average over active mapping scenes, Hubble gradient optimization | same reconstruction / coverage metrics | `w/o Vis.`, `w/o Var.`, `Ind. Rays`, `Loose`, `AIR-OPT`, `NeurAR-OPT` |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4 active re-observation / coverage utility | `Vis`, `CR`, reconstruction `Acc` / `Comp`, entropy map behavior | semantic object/node uncertainty, ObjectNav `SR` / `SPL`, path cost, `ATE/RPE` |

## Dataset / Benchmark

- Original NeRF synthetic assets: Chair, Drums, Ficus, Hotdog, Lego, Materials, Mic, Ship.
- Hubble Space Telescope scene.
- Custom synthetic indoor Room scene. 두 공간이 wall로 나뉘며, 두 번째 room은 initial views에서 보이지 않도록 설정된다.
- Ground truth images는 Blender로 `512 x 512` resolution에서 render한다.
- Code README 기준 실행 scene: `hubble`, `room`, `lego`, `hotdog`.

## Splits

- Uncertainty estimation:
  - Hotdog: plate 위 90-degree sector에서 `20` training views.
  - Hubble: 한쪽 90-degree sector에서 `20` training views, 반대쪽은 out of view.
  - Room: 한 room의 back wall, common wall, floor를 향한 `30` training views, 다른 room은 unobserved.
- Active mapping:
  - Original NeRF assets / Hubble: scene 일부만 cover하는 `3-5` initial views.
  - Room: one room에서 `9` initial views, second room은 unknown.
  - Active mapping horizon: `20` steps.
  - Supplement 기준 candidate poses: `N = 512`.

## Metrics

- Novel view synthesis: `PSNR`, `SSIM`, `LPIPS`, `RGB loss`.
- Mesh reconstruction: `Accuracy (Acc)`, `Completion (Comp)`, `Completion Ratio (CR)`.
- Visual coverage: `Vis`, ground truth mesh faces 중 trajectory views에서 occlusion 없이 관찰된 face 비율.
- Uncertainty estimation: qualitative entropy map comparison. 논문 본문에는 explicit calibration metric은 없다.

## Baselines

- `Random`
- `WD`: weight distribution-based entropy approximation.
- `ActiveRMAP`: occlusion-based entropy approximation.
- `AIR` / `ActiveImplicitRecon`: weighted occlusion-based entropy approximation.
- `ActiveNeRF`: spatial RGB variance-based uncertainty.
- `NeurAR`: spatial RGB variance-based uncertainty.

## Main Results

- NeRF Assets average: NVF `PSNR 23.90`, `SSIM 0.890`, `LPIPS 0.106`, `CR 0.685`, `Vis 0.532`; strongest baseline PSNR은 `ActiveRMAP 20.03`, strongest baseline Vis는 `ActiveRMAP 0.471`.
- Hubble: NVF `PSNR 27.99`, `SSIM 0.919`, `LPIPS 0.100`, `CR 0.651`, `Vis 0.681`; strongest baseline PSNR은 `NeurAR 25.19`, strongest baseline Vis는 `AIR 0.586`.
- Room: NVF `PSNR 22.83`, `SSIM 0.943`, `LPIPS 0.156`, `CR 0.464`, `Vis 0.586`; strongest baseline PSNR은 `AIR 15.19`, strongest baseline Vis는 `AIR 0.498`.
- Ablation average: `w/o Vis.`는 `PSNR 21.11`, `Vis 0.382`, NVF는 `PSNR 24.42`, `Vis 0.546`. 논문은 이를 visibility factor의 중요 근거로 제시한다.
- Supplement gradient-based pose optimization: `NVF-OPT`는 Hubble setting에서 `PSNR 29.33`, `Vis 0.690`으로 `NVF`의 `PSNR 27.99`, `Vis 0.681`보다 높다.

## Reproducibility Notes

- Official code: https://github.com/GaTech-RL2/nvf_cvpr24
- Tested setup: Ubuntu 20.04, RTX 3090, CUDA >= 11.7, Python 3.10, PyTorch 2.0.1+cu117.
- Codebase builds on `nerfstudio`, `nerf_bridge`, and Instant-NGP.
- Training assets require `.blend` and `.ply` files from the project Google Drive and placement under `/data/assets/blend_files/`.
- Example command: `python eval.py --scene hubble --method nvf`.
- Reproduction risk: dependency stack is GPU/CUDA-specific and may require pinned `tiny-cuda-nn`, `nerfacc`, `viser`, `pytorch3d`, and Blender.

## Evaluation Weaknesses

- semantic goal-oriented navigation과 직접 연결되지 않는다.
- path length, collision, SPL, wrong-goal visit 같은 navigation behavior metric이 없다.
- trajectory constraints는 제한적으로만 처리된다. 논문 conclusion은 cost-aware path planning 통합을 future direction으로 둔다.
- uncertainty estimation은 qualitative entropy map 중심이며 calibration-style metric은 부족하다.
- synthetic rendering 중심이므로 sensor noise, pose drift, dynamic object, real-world map update latency는 별도 검증이 필요하다.
