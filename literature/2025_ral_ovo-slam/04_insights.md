# Insights

## Facts

- `Open-Vocabulary Online Semantic Mapping for SLAM`는 RA-L 2025로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2411.15043 이다.
- Local PDF는 arXiv:2411.15043v3 [cs.CV], 2025-09-29 버전으로 저장했다.
- Project page는 https://tberriel.github.io/ovo/ 이고 code는 https://github.com/tberriel/OVO 에 공개되어 있다.
- 평가 dataset은 ScanNet++, ImageNet-S, ScanNetv2, Replica다.

## Paper Claims

- OVO-SLAM은 offline baselines보다 lower compute/memory footprint와 better segmentation metrics를 보이고, ground-truth poses 없이 end-to-end open-vocabulary online 3D reconstruction을 시연한다고 주장한다.
- Learned CLIP merging은 여러 viewpoint / crop descriptor를 효과적으로 통합해 open-vocabulary semantic labeling을 개선한다고 주장한다.
- Loop closure 이후 3D segment fusion은 SLAM-integrated semantic map quality를 개선한다고 주장한다.

## Inferences

- CAND-01 Step 4-5의 backbone 근거로 강하다. 이 논문은 open-vocabulary semantic map과 SLAM trajectory metric을 같은 evaluation table에 둔다.
- Step 1의 object/node uncertainty는 논문이 직접 제공하지 않지만, descriptor consistency, segment persistence, loop-closure fusion result를 uncertainty proxy로 만들 여지가 있다.
- Step 2-3의 ObjectNav behavior는 별도 harness가 필요하다. OVO 자체는 active re-observation 또는 navigation policy 논문이 아니다.

## 사용자 판단 필요

- `OVO`를 구현 backbone 후보로 둘지, metric/design evidence로만 둘지 결정해야 한다.
- `OVO-ORB-SLAM2` 쪽으로 가면 classical SLAM integration이 쉬울 수 있고, `OVO-Gaussian-SLAM` 쪽으로 가면 map quality는 좋지만 구현 비용이 커질 수 있다.

## Connection to Field Trends

- Trend 3 `Environmental perception is shifting toward open-vocabulary semantic maps and retrievable embodied memory`: open-vocabulary 3D semantic map의 online version으로 강한 evidence다.
- Trend 1 `Active SLAM is becoming semantic and uncertainty-aware`: direct active SLAM은 아니지만, SLAM backbone과 semantic map correction이 결합되어 Step 5 metric 설계에 유용하다.
- P01 `3D Active Metric-Semantic SLAM`이 closed-set active SLC라면, OVO는 open-vocabulary semantic SLAM backbone 쪽 근거다.

## Possible Contribution Angles

- OVO segment descriptor consistency를 active re-observation utility로 사용한다.
- Loop closure 전후 semantic map correction량과 `ATE` / `RPE` / `mIoU` 변화를 함께 측정한다.
- OVO semantic map을 `CARe`-style ObjectNav replanning과 결합해 map uncertainty가 behavior metric에 미치는 영향을 본다.
- ORB-SLAM2 vs Gaussian-SLAM backbone에서 semantic map correction과 navigation utility가 어떻게 달라지는지 비교한다.

## What Would Change This Assessment

- Code가 target machine에서 실행 가능하면 CAND-01 Step 4-5의 implementation baseline 후보가 된다.
- Runtime / memory가 과하면 first experiment에서는 OVO 전체가 아니라 saved RGB-D sequence 기반 semantic uncertainty proxy만 사용한다.
- ObjectNav harness와 연결이 어려우면 Step 5 논문 방향은 semantic SLAM evaluation 중심으로 남고, Step 3는 별도 simulator experiment로 분리해야 한다.
