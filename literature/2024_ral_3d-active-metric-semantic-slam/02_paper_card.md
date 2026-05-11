# Paper Card

## Problem

GPS-denied multi-floor indoor environment에서 SWaP-constrained UAV가 exploration, localization, metric-semantic mapping을 동시에 수행해야 한다. 기존 exploration / active mapping 연구는 robot localization을 별도 문제로 두는 경우가 많아, VIO drift가 누적되면 map error와 unsafe behavior로 이어진다.

## Core Idea

Sparse semantic object landmark를 metric-semantic SLAM factor graph에 넣고, COP-based exploration path에 active Semantic Loop Closure viewpoint를 삽입한다. 목적은 new area exploration의 information gain과 pose/map uncertainty reduction을 함께 균형화하는 것이다.

## Input / Output

- Input: RGB-D observation, VIO pose, IMU, instance segmentation result
- Output: optimized robot poses, semantic landmark map, hierarchical voxel map, refined exploration path with possible SLC viewpoints

## Method

- Hierarchical volumetric mapping: low-resolution global voxel map은 frontier detection, viewpoint sampling, COP planning에 쓰고, high-resolution ego-centric local map은 local trajectory planning에 쓴다.
- Semantic SLAM: GTSAM factor graph에서 robot pose node와 object landmark node를 유지하고, odometry factor와 range/bearing factor를 사용한다.
- Semantic Loop Closure: 현재 local semantic object centroid set과 과거 semantic submap을 align해 loop closure를 검출한다.
- COP-based exploration planning: sampled frontier viewpoint를 graph vertex로 두고, information gain과 travel cost를 고려해 long-horizon exploration tour를 선택한다.
- Active uncertainty reduction planning: candidate SLC viewpoint-submap pair에 virtual factor를 추가해 covariance trace reduction을 information gain으로 계산하고, exploration path에 SLC를 삽입할지 판단한다.

## Main Claims

- Semantic Loop Closure를 포함하면 robot pose estimation error와 pose/map uncertainty가 크게 줄어든다.
- Sparse semantic representation은 dense point cloud alignment보다 viewpoint change에 더 robust하고 onboard real-time planning에 적합하다.
- 제안 시스템은 cluttered multi-floor indoor environment에서 autonomous UAV exploration과 metric-semantic mapping을 실제로 수행한다.

## Strengths

- Active SLAM 문제를 exploration utility만이 아니라 localization uncertainty까지 포함해 정식화한다.
- real UAV, onboard compute, multi-floor indoor setting에서 검증했다.
- semantic landmark를 loop closure candidate generation과 information gain estimation에 직접 연결한다.
- Kimera, ORB-SLAM3처럼 feature matching 기반 loop closure가 어려운 drastic viewpoint change 조건을 명확히 겨냥한다.

## Limitations

- 실험 semantic object는 사실상 chair class 중심이다.
- public standardized benchmark로 재현한 결과가 아니라 authors' real-world missions 중심이다.
- semantic detector 품질과 object landmark 분포에 의존한다.
- UAV stack, depth sensor, VIO, onboard compute 조건이 강하게 전제된다.
- open-vocabulary semantic map이나 dynamic object setting까지 확장된 평가는 없다.

## Relevance to My Research

이 논문은 "previous environment-specific perception을 어떻게 SLAM/navigation 행동으로 되돌려 쓸 것인가"의 직접적인 출발점이다. 특히 semantic landmark memory를 단순 map annotation이 아니라 active re-observation / loop closure / uncertainty reduction action으로 바꾸는 구조가 중요하다.

석사 연구에서는 full UAV stack보다 작게 줄여서, pre-explored semantic map 또는 online semantic memory가 active viewpoint selection, ATE/RPE, map error, ObjectNav SR/SPL에 미치는 영향을 비교하는 방향이 현실적이다.

## Follow-up Questions

- chair 같은 closed-set object landmark 대신 open-vocabulary object landmark를 쓰면 SLC reliability가 어떻게 변하는가?
- semantic landmark가 부족하거나 false positive가 많은 환경에서 active SLC candidate scoring은 어떻게 실패하는가?
- pre-explored semantic map을 prior로 넣으면 exploration cost와 loop closure success가 개선되는가?
- Habitat, HM3D, Replica, ScanNet 중 어떤 benchmark에서 active SLAM + semantic memory metric을 가장 작게 구현할 수 있는가?
