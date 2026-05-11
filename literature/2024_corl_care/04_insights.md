# Insights

## Facts

- `Context-Aware Replanning with Pre-explored Semantic Map for Object Navigation`는 CoRL 2024 paper이며 PMLR volume 270 proceedings에는 2025년에 pp. 4253-4267로 등재되어 있다.
- OpenReview page는 Published `2024-09-05`, Last Modified `2024-11-08`로 기록되어 있다.
- arXiv는 `arXiv:2409.04837`, submitted `2024-09-07`, last revised `2024-11-02`, v2, `cs.RO`로 기록되어 있다.
- Local `paper.pdf`는 PMLR PDF와 OpenReview PDF hash가 동일하다.
- Official code repository는 public, MIT License이며 README는 OpenMask3D setting experiments를 설명한다.
- 실험은 OpenMask3D object retrieval과 VLMaps / HabitatSim replanning subgoal setting을 사용한다.

## Paper Claims

- 기존 pre-explored semantic map 기반 navigation은 map accuracy를 가정하고, incorrect map decision을 수정하는 mechanism이 부족하다고 주장한다.
- CARe는 confidence score, entropy, standard error, pairwise KL divergence 같은 uncertainty / multi-view consistency signal로 wrong map retrieval 이후 replanning을 개선한다고 주장한다.
- CARe는 additional labels 없이 OpenMask3D와 VLMaps 두 backbone에서 max-confidence replanning보다 성능을 높인다고 주장한다.
- 논문은 first failure 이후 confidence만 다시 따르는 방식이 visual model bias를 반복할 수 있고, uncertainty-based selection이 이를 완화한다고 주장한다.

## Inferences

- CAND-01 Step 1-3의 가장 직접적인 baseline/evidence다. object/node uncertainty 계산, failed ObjectNav target 재선택, wrong-goal visit 분석에 바로 연결된다.
- CARe는 Step 2의 active re-observation viewpoint selection까지는 가지 않는다. 선택하는 것은 viewpoint가 아니라 second target/subgoal이다.
- CARe는 Step 4-5의 semantic memory를 active SLAM utility로 확장하는 부분도 직접 다루지 않는다. 대신 fixed map limitation이 내 연구의 확장 지점이다.
- 석사 연구 first probe는 CARe-style uncertainty signal을 재사용하되, `wrong-goal visit`, `wasted path`, `SPL`, semantic coverage를 추가 metric으로 붙이는 것이 현실적이다.

## 사용자 판단 필요

- CARe를 full reproduction baseline으로 둘지, OpenMask3D retrieval script만 먼저 재현할지 결정해야 한다.
- CAND-01에서 second-target replanning을 그대로 따를지, uncertainty가 높은 object/node에 대한 active re-observation viewpoint selection으로 바꿀지 결정해야 한다.
- `Min stderr`를 primary uncertainty signal로 둘지, `entropy`와 `KL divergence`까지 ablation으로 둘지 결정해야 한다.

## Connection to Field Trends

- Environmental perception intelligence: pre-explored map이 task execution 중 틀릴 수 있음을 인정하고, map uncertainty를 행동 선택에 사용한다.
- Semantic memory navigation: VLMaps / OpenMask3D 같은 pre-explored semantic map backbone을 ObjectNav decision에 재사용한다.
- Active perception에는 부분 연결만 있다. CARe는 uncertainty로 replan하지만 uncertainty를 줄이기 위한 active observation action은 선택하지 않는다.
- SLAM-navigation coupling에는 약하게 연결된다. map-based navigation을 다루지만 pose graph, map update, localization uncertainty는 없다.

## Possible Contribution Angles

- CARe-style object/node uncertainty를 active re-observation viewpoint selection으로 확장한다.
- Fixed map replanning을 online semantic map update로 바꾸고, before/after semantic accuracy와 ObjectNav behavior를 함께 평가한다.
- `Min stderr`, `entropy`, `KL divergence`를 semantic map uncertainty ablation으로 쓰고, `SR`, `SPL`, `wrong-goal visit`, `wasted path`와의 상관을 본다.
- CARe의 map uncertainty를 SLAM uncertainty proxy, pose graph connectivity, loop closure candidate score와 결합한다.
- Failure taxonomy를 만든다: model bias, low multi-view support, occlusion, wrong object category, map localization error, planner failure를 분리한다.

## What Would Change This Assessment

- OpenMask3D setting이 현재 환경에서 재현 가능하면 CARe는 CAND-01 Stage 1 baseline으로 거의 필수다.
- VLMaps/Habitat path가 코드에서 충분히 재현되지 않으면, CARe는 exact baseline보다 uncertainty-signal reference로 둬야 한다.
- CARe-style uncertainty와 `wrong-goal visit` / `wasted path`의 상관이 낮으면, active re-observation의 utility를 semantic uncertainty만으로 설계하기 어렵다.
- Online map update를 넣었을 때 CARe의 consistent-bias assumption이 깨지면, CAND-01은 uncertainty recalibration 또는 memory update policy를 더 중심에 둬야 한다.
