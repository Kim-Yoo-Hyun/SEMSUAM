# Insights

## Facts

- `NARUTO: Neural Active Reconstruction from Uncertain Target Observations`는 CVPR 2024로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/CVPR2024/html/Feng_NARUTO_Neural_Active_Reconstruction_from_Uncertain_Target_Observations_CVPR_2024_paper.html 이다.
- arXiv version은 v2이며, last revised date는 2024-04-16이다.
- Project page는 https://oppo-us-research.github.io/NARUTO-website/ 이다.
- Official code는 https://github.com/oppo-us-research/NARUTO 이다.
- Evaluation uses HabitatSim with 8 Replica scenes and 5 MP3D scenes.
- The paper assumes known localization and perfect action execution.
- Main metrics are `MAD`, `Accuracy`, `Completion`, and `Completion Ratio`.

## Paper Claims

- NARUTO is the first neural active reconstruction system operating with 6DoF movement in unrestricted spaces라고 주장한다.
- Learned uncertainty can guide goal search and efficient path planning for active reconstruction이라고 주장한다.
- Active Ray Sampling improves stability and consistency of neural SLAM / neural mapping optimization이라고 주장한다.
- MP3D `Completion Ratio`를 previous SOTA 73.15%에서 90.18%로 개선한다고 주장한다.
- Replica ablation에서 `Full` method가 `w/o ActiveRay`와 `Uncertainty Net`보다 better reconstruction mean metrics를 보인다고 주장한다.

## Inferences

- P05는 `CAND-01` Step 2 active re-observation viewpoint selection에 강한 method analogy를 제공한다.
- `Uncertainty Aggregation for Goal Search`는 object/node uncertainty에도 적용 가능하다. High-uncertainty object candidates를 reachable viewpoints에 aggregate하고, visibility / distance / path cost로 선택할 수 있다.
- P05의 full neural reconstruction stack은 `CAND-01` first probe에는 과하다. 필요한 것은 uncertainty aggregation, reachability filtering, active ray / active observation sampling idea다.
- P05는 Step 5의 SLAM uncertainty evidence로는 약하다. Known localization assumption 때문에 `ATE/RPE`나 pose graph connectivity 주장을 직접 뒷받침하지 않는다.

## 사용자 판단 필요

- NARUTO code를 직접 실행해 active reconstruction baseline으로 검토할지 결정해야 한다.
- `CAND-01` first probe에서는 NARUTO-style uncertainty aggregation만 차용하고 neural reconstruction은 제외할지 결정해야 한다.
- Semantic re-observation utility에서 `top-k uncertain targets`와 `candidate viewpoint visibility aggregation`을 핵심 설계로 둘지 결정해야 한다.

## Connection to Field Trends

- Active perception and uncertainty-driven mapping trend의 strong evidence다.
- Neural active reconstruction trend의 strong evidence다.
- SLAM-navigation coupling과는 간접 연결이다. It assumes localization rather than evaluating localization uncertainty.
- Environmental perception intelligence와 mobility coupling은 uncertainty-aware goal search / path planning 측면에서 연결된다.

## Possible Contribution Angles

- Semantic object/node uncertainty를 NARUTO-style uncertainty aggregation으로 candidate viewpoints에 project하기.
- Active re-observation에서 `Observe` action을 명시적으로 정의하기.
- Habitat ObjectNav에서 top-k uncertain object nodes, visibility range, path cost를 결합한 first probe 만들기.
- Active Ray Sampling idea를 semantic map update에 적용해 uncertain object observations를 preferentially sample하기.

## What Would Change This Assessment

- Official code가 local machine에서 Docker / Conda로 실행되면 implementation reference로 격상할 수 있다.
- NARUTO-style aggregation이 semantic wrong-goal probability와 상관이 없으면 Step 2 utility design reference로서 가치가 낮아진다.
- `CAND-01` Step 5에서 pose uncertainty가 핵심으로 드러나면 P05보다 P02/P03/P01 근거를 우선해야 한다.
- Real-world robot deploy를 중심으로 바꾸면 known localization and perfect action execution assumption이 큰 limitation이 된다.
