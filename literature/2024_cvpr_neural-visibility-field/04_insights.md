# Insights

## Facts

- `Neural Visibility Field for Uncertainty-Driven Active Mapping`는 CVPR 2024 paper이며 CVF Open Access proceedings page는 pp. 18122-18132로 기록한다.
- arXiv page는 `arXiv:2406.06948`, submitted 2024-06-11, v2 2024-06-15, `cs.CV`와 `cs.RO`로 기록한다.
- Official project page와 GitHub code가 있다.
- Local folder에는 CVPR Open Access PDF `paper.pdf`가 저장되어 있다.
- 실험은 original NeRF synthetic assets, Hubble Space Telescope, custom synthetic Room scene에서 진행한다.

## Paper Claims

- 기존 NeRF uncertainty methods는 density, occupancy, RGB variance proxy에 집중하고 visibility coverage를 놓친다고 주장한다.
- NVF는 Bayesian Network로 position-based field uncertainty를 ray-based observation uncertainty로 합성해 unobserved regions에 higher entropy를 부여한다고 주장한다.
- NVF는 active mapping에서 reconstruction quality와 visual coverage를 기존 baselines보다 높인다고 주장한다.
- visibility factor ablation 결과가 NVF 성능의 핵심 원인이 visibility modeling임을 뒷받침한다고 주장한다.

## Inferences

- CAND-01 Step 4-5의 핵심 연결점은 `unobserved area uncertainty`를 active SLAM/NBV utility로 바꾸는 구조다.
- 이 논문은 semantic memory 자체를 다루지 않으므로 Step 1-3 ObjectNav evidence로 쓰기보다는 Step 4-5의 geometric active mapping evidence로 쓰는 것이 더 정확하다.
- 내 연구의 semantic memory uncertainty는 NVF의 visibility 개념을 object/node/relation 단위로 옮겨 `semantic coverage`, `multi-view support`, `occlusion risk`로 확장할 수 있다.
- NVF가 인정한 path planning constraint 부재는 CAND-01에서 navigation-aware active re-observation 또는 cost-aware active SLAM utility를 주장할 때 좋은 gap이 된다.

## 사용자 판단 필요

- NVF를 직접 reproduction baseline으로 둘지, 아니면 uncertainty utility 설계 근거와 metric reference로만 둘지 결정해야 한다.
- real-world robot deploy까지 고려한다면 NeRF/NVF를 그대로 쓸지, 3DGS 또는 semantic scene graph 위에 visibility-style uncertainty만 이식할지 선택해야 한다.
- CAND-01 first experiment에서 `Vis`와 유사한 semantic coverage metric을 새로 정의할지 판단해야 한다.

## Connection to Field Trends

- Active perception trend: uncertainty를 information gain으로 바꿔 NBV를 선택한다.
- Environmental perception intelligence trend: map representation이 단순 reconstruction이 아니라 uncertainty-aware perception state를 포함한다.
- SLAM-navigation coupling trend에는 부분적으로만 연결된다. mapping quality와 visual coverage는 강하지만, pose graph, ATE/RPE, navigation success는 평가하지 않는다.

## Possible Contribution Angles

- Semantic Visibility Field: object/node/relation이 training trajectory에서 얼마나 reliable하게 관찰됐는지 추정한다.
- Semantic NBV utility: geometric visibility entropy와 semantic uncertainty를 결합해 active re-observation viewpoint를 선택한다.
- Cost-aware extension: NVF가 future direction으로 둔 trajectory constraint를 navigation path cost, collision, localization risk와 결합한다.
- Evaluation bridge: `Vis`를 semantic coverage와 연결하고, 추가로 ObjectNav `SR`, `SPL`, `wrong-goal visit`, `wasted path`를 같이 본다.

## What Would Change This Assessment

- Code가 현재 GPU 환경에서 재현 가능하면 NVF를 Step 4-5 baseline으로 강하게 채택할 수 있다.
- real-world RGB-D/SLAM input에서 visibility head 학습이 불안정하면, full NVF reproduction보다 visibility-inspired proxy로 범위를 줄여야 한다.
- semantic ObjectNav에서 `Vis`류 metric과 task metric 간 상관이 약하면, 이 논문은 contribution 중심 근거가 아니라 background trend evidence로 내려야 한다.
