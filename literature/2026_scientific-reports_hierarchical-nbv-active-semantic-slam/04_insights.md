# Insights

## Facts

- `Mutual information-based hierarchical NBV decision for active semantic visual SLAM under dynamic environments`는 Scientific Reports 2026로 registry에 기록했다.
- Primary source는 https://www.nature.com/articles/s41598-026-36259-x 이다.
- DOI는 `10.1038/s41598-026-36259-x`이다.
- Publication date는 2026-01-20이다.
- Authors are Zhenyuan Yang, Ash Wan Yaw Sang, M. A. Viraj J. Muthugala, and Mohan Rajesh Elara.
- Method stack includes ORB-SLAM2, YOLOv8s, BoT-SORT, OctoMap, ROS, Gazebo, DWA, RGB-D camera.
- Evaluation uses two Gazebo simulation environments and one real-world Meerkat robot scene.
- No public code link was found in the paper or web search on 2026-05-06.

## Paper Claims

- Full hierarchical NBV가 global-only variant보다 tracking loss와 near collision을 줄인다고 주장한다.
- Proposed method가 Nearest frontier, `TARE`, `RNE`/`RNEX`, global-only variant보다 `ATE`, `RPE Trans.`, `RPE Rot.`에서 좋은 결과를 낸다고 주장한다.
- Dynamic object를 semantic segmentation과 epipolar constraint로 제거하되, local NBV가 feature observability 높은 방향을 고르기 때문에 active SLAM tracking robustness를 유지한다고 주장한다.
- Real-world Meerkat robot에서 module runtime이 real-time deployment 가능성을 보인다고 주장한다.

## Inferences

- `CAND-01` Step 5의 SLAM uncertainty metric을 보강하는 secondary evidence다.
- P02가 pose graph / semantic mutual information 쪽 근거라면, P03는 dynamic object로 인한 feature observability failure와 tracking loss metric 근거다.
- Direct baseline으로 쓰기에는 code 부재가 크다. 대신 `tracking loss rate`, near collision, dynamic residual point 같은 robustness metric을 harness에 가져오는 것이 현실적이다.
- `Feature Probability Map`은 semantic map uncertainty와 다른 종류의 uncertainty다. It is image-domain feature observability under dynamic occlusion, not object/node semantic uncertainty.

## 사용자 판단 필요

- Dynamic objects를 `CAND-01` main scope에 넣을지, real-world stress test / limitation analysis로 둘지 결정해야 한다.
- Supplementary Information을 내려받아 실험 영상과 추가 data가 있는지 확인할지 결정해야 한다.
- Code가 없으므로 direct implementation baseline으로 둘지, metric reference로만 둘지 결정해야 한다.

## Connection to Field Trends

- Active semantic SLAM in dynamic environments trend의 evidence다.
- Environmental perception intelligence와 robot mobility coupling에 연결된다.
- SLAM-navigation coupling에서는 global exploration과 local motion planning을 hierarchical NBV로 연결한다.
- Open-vocabulary semantic mapping trend와는 약하다. COCO/YOLOv8s 기반 dynamic object detection에 가깝다.

## Possible Contribution Angles

- `CAND-01` Step 5 metric에 `tracking loss rate`와 `localization failure count`를 넣기.
- Real-world proof-of-concept에서 near collision 또는 dynamic occlusion stress case를 정의하기.
- Active re-observation viewpoint utility에 feature observability / dynamic object avoidance penalty를 추가하기.
- Semantic map memory가 moving objects를 stale object로 보존하는 failure를 residual contamination metric으로 측정하기.

## What Would Change This Assessment

- Supplementary Information이 scene parameters and replay assets를 충분히 제공하면 partial reproduction 후보가 된다.
- Public code가 발견되면 Step 4-5 `SLAMOnly` dynamic robustness baseline 후보가 된다.
- `CAND-01` first probe에서 dynamic object가 주요 wrong-goal failure 원인으로 드러나면 P03의 FPM-style local utility를 primary extension으로 올릴 수 있다.
- 반대로 static simulation에서 대부분 성능 차이가 설명되면 P03는 real-world stress-test reference로만 둔다.
