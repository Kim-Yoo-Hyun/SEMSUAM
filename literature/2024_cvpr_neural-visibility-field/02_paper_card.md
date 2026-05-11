# Paper Card

## Problem

NeRF 기반 active mapping에서 아직 보지 못한 region은 reconstruction에 중요하지만, 기존 uncertainty proxy가 이 region의 visibility gap을 충분히 반영하지 못한다. 따라서 next-best-view를 고를 때 이미 본 영역을 다시 방문하거나, scene coverage가 낮은 trajectory가 선택될 수 있다.

## Core Idea

Neural Visibility Field (NVF)는 training views에서 point가 보였는지 여부를 visibility factor로 모델링하고, Bayesian Network로 position-based uncertainty를 ray-based camera observation uncertainty로 합성한다.

## Input / Output

- Input: initial training views, current NeRF/NVF map state, sampled candidate camera poses.
- Output: candidate view별 ray/image entropy score, selected next-best-view, updated active mapping trajectory.

## Method

- Instant-NGP backbone 위에 RGB variance head와 visibility head를 추가한다.
- volume rendering을 hybrid Bayesian Network로 해석한다. `C_i`는 position-based emitted color, `Z_i`는 ray-based observed color, `D_i`는 ray segment occlusion variable이다.
- visible point는 NeRF가 예측한 color distribution을 사용하고, invisible point는 prior color distribution을 사용해 high uncertainty를 부여한다.
- ray color distribution을 Gaussian Mixture Model로 보고 entropy upper bound를 사용해 view uncertainty를 계산한다.
- active mapping pipeline은 small initial views에서 시작해 candidate poses를 샘플링하고, entropy가 가장 높은 view를 선택한 뒤 새 observation을 추가하고 NVF를 재학습한다.
- supplement 기준으로 active mapping은 `N = 512` candidate views, `20` horizon steps로 평가한다.

## Main Claims

- NVF는 unobserved regions에 더 높은 entropy를 부여해 기존 NeRF uncertainty baselines보다 uncertainty map이 active exploration에 더 적합하다고 주장한다.
- NVF는 active mapping에서 reconstruction quality와 visual coverage를 동시에 향상한다고 주장한다.
- visibility factor 제거 ablation에서 성능이 크게 떨어지므로 visibility가 uncertainty estimation의 핵심 요인이라고 주장한다.

## Strengths

- position uncertainty와 observation uncertainty 사이의 연결을 Bayesian Network로 정식화한다.
- visibility를 active mapping utility에 직접 넣어 `unseen-but-important` region을 탐색하도록 만든다.
- baselines, ablation, supplement, official code가 있어 active uncertainty baseline으로 재검토하기 좋다.
- `PSNR`, `SSIM`, `LPIPS`, `RGB`, mesh `Acc`, `Comp`, `CR`, `Vis`를 함께 보고 map quality와 coverage를 분리한다.

## Limitations

- active mapping pipeline이 planned trajectory constraints를 고려하지 않는다고 논문이 직접 한계로 적었다.
- semantic map, object/node uncertainty, ObjectNav success는 다루지 않는다.
- experiments는 Blender-rendered synthetic assets 중심이며 real-world robot deployment는 검증하지 않는다.
- 매 step 새 view를 추가한 뒤 model을 다시 train하는 구조라 real-time mobile robot loop로 옮기려면 계산 비용과 latency를 따로 검증해야 한다.

## Relevance to My Research

- CAND-01 Step 4-5에서 semantic memory를 active SLAM utility로 확장할 때, `visibility-aware uncertainty -> NBV -> map quality / coverage`라는 가장 가까운 geometric baseline이다.
- Step 1-3의 ObjectNav metric과 직접 연결되지는 않지만, Step 4-5의 SLAM uncertainty proxy, visual coverage, map error 평가 설계에 강하게 연결된다.
- semantic object/node uncertainty를 만들 때 `unobserved semantic node`, `low multi-view support`, `occluded relation`을 high uncertainty로 처리하는 설계 근거가 된다.

## Follow-up Questions

- NVF의 `Vis`를 semantic map의 object/node coverage 또는 relation coverage로 치환할 수 있는가?
- CAND-01에서 path cost-aware NBV를 추가하면 NVF의 stated limitation을 직접 겨냥하는 contribution으로 만들 수 있는가?
- real-world robot deploy에서는 NVF-style visibility uncertainty를 3DGS, semantic scene graph, occupancy map 중 어느 representation에 얹는 것이 가장 현실적인가?
