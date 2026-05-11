# Paper Card

## Problem

### 사실

Active reconstruction은 agent가 어디로 움직이고 무엇을 관찰해야 3D reconstruction quality와 completeness가 좋아지는지 결정하는 문제다.

### 논문 주장

기존 neural active reconstruction은 NeRF 계열의 느린 최적화 속도, 제한된 action space, object-centric setup, 2D plane movement 같은 제약이 있어 large-scale indoor scene에서 6DoF movement를 수행하기 어렵다고 주장한다.

### 에이전트 추론

P05는 semantic ObjectNav 논문은 아니지만, uncertainty를 target observation과 path planning으로 바꾸는 구조가 `CAND-01` Step 2 active re-observation viewpoint selection과 직접적으로 닮아 있다.

## Core Idea

Hybrid neural representation, uncertainty learning, uncertainty-aware goal search, efficient RRT path planning을 결합한다. Learned reconstruction uncertainty가 높은 3D points를 찾고, 그 불확실한 target을 잘 관찰할 수 있는 goal location을 선택한 뒤, SDF map 기반 RRT로 feasible trajectory를 만든다.

## Input / Output

Input:

- posed RGB-D images from HabitatSim
- observation database from keyframes
- hybrid neural representation from Co-SLAM-style mapping
- SDF volume
- learned uncertainty volume
- goal space and traversable space

Output:

- selected goal state and camera direction
- RRT path toward uncertain target observations
- reconstructed mesh / SDF field
- uncertainty map and active ray sampling choices

## Method

### 사실

- Mapping backbone은 `Co-SLAM`의 hybrid representation을 사용한다.
- One-blob coordinate encoding과 multi-resolution hash-grid feature를 결합한다.
- Bundle adjustment uses color loss, depth loss, SDF loss, free-space loss, feature smoothness regularization.
- Reconstruction uncertainty는 uncertainty-aware depth rendering loss로 학습한다.
- Implicit uncertainty MLP와 explicit uncertainty grid를 비교하고, explicit `Uncertainty Grid`를 채택한다.
- Goal search는 top-k uncertain points를 goal space에 aggregate한다. Paper uses `k=300`.
- Candidate goal은 uncertainty가 높은 points를 sensing range `[0.5, 2]m` 안에서 볼 수 있는지 SDF visibility로 평가한다.
- Path planning은 SDF map 기반 efficient RRT를 사용한다.
- Agent actions are `Move`, `Observe`, and `Stay`.
- Active Ray Sampling은 random rays 일부를 high-uncertainty rays로 교체해 mapping optimization의 consistency를 높인다.

### 에이전트 추론

`CAND-01`에 직접 가져올 수 있는 부분은 neural reconstruction backbone 전체가 아니라 uncertainty aggregation and reachability filtering이다. Semantic object/node uncertainty도 top-k uncertain nodes를 candidate viewpoints에 aggregate하는 방식으로 바꿀 수 있다.

## Main Claims

### 논문 주장

- NARUTO는 unrestricted 6DoF space에서 동작하는 first neural active reconstruction system이라고 주장한다.
- Learned uncertainty가 active reconstruction의 goal search와 path planning에 효과적이라고 주장한다.
- Active Ray Sampling은 existing neural SLAM / neural mapping method의 stability와 reconstruction consistency를 높인다고 주장한다.
- MP3D에서 completion ratio를 previous SOTA 73.15%에서 90.18%로 올렸다고 주장한다.
- Replica에서 full method가 `w/o ActiveRay`와 `Uncertainty Net`보다 better accuracy, completion, completion ratio를 보인다고 주장한다.

## Strengths

- uncertainty learning과 path planning을 active reconstruction으로 연결한다.
- Replica와 MP3D를 모두 사용한다.
- reconstruction `Accuracy`, `Completion`, `Completion Ratio`, `MAD`를 명확하게 보고한다.
- 5 repeated trials 평균을 사용한다.
- Code가 공개되어 있다.
- `w/o ActiveRay`, `Uncertainty Net`, `Co-SLAM w/ ActRay` 같은 ablation이 있어 uncertainty representation과 sampling effect를 분리할 수 있다.
- Planning module이 goal search와 path feasibility를 함께 다룬다.

## Limitations

- Known localization and perfect action execution을 가정한다.
- Real-world deploy는 수행하지 않는다.
- Semantic perception intelligence, object/node uncertainty, ObjectNav는 다루지 않는다.
- `ATE/RPE`, pose graph connectivity, localization failure는 중심 metric이 아니다.
- Neural reconstruction stack과 HabitatSim / Co-SLAM dependency가 크다.
- Motion constraints는 practical robotics setting보다 단순하다.
- Single-resolution uncertainty grid는 future work로 multi-resolution extension 필요성을 언급한다.

## Relevance to My Research

### 사실

`CAND-01` Step 2는 uncertain candidate에 대해 active re-observation viewpoint를 선택한다.

### 에이전트 추론

P05는 Step 2의 algorithmic reference로 유용하다. Semantic object/node uncertainty를 NARUTO-style target uncertainty로 보고, reachable candidate viewpoints에 aggregate한 뒤, travel cost와 visibility로 최종 viewpoint를 선택하는 형태가 가능하다. 다만 Step 5의 SLAM/map consistency 근거로는 P02/P03보다 약하다.

## Follow-up Questions

- `CAND-01`에서 NARUTO-style uncertainty aggregation을 object/node graph에 적용할 수 있는가?
- Habitat ObjectNav에서 reachable viewpoint search를 RRT 대신 shortest path / navigability graph로 대체할 수 있는가?
- Code를 실행하지 않고도 top-k uncertain target aggregation만 small probe로 재현할 수 있는가?
- Neural reconstruction metric과 semantic map metric을 어떻게 분리할 것인가?
