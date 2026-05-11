# Paper Card

## Problem

### 사실

Dynamic environment에서 moving object는 visual SLAM의 localization accuracy와 mapping quality를 떨어뜨릴 수 있다. Semantic SLAM은 dynamic features를 제거할 수 있지만, active SLAM에서 feature를 제거하기만 하면 visible static features가 부족해 tracking loss가 생길 수 있다.

### 논문 주장

기존 active visual SLAM은 complete mapping 또는 efficient exploration에 집중하고, dynamic object가 feature observability와 tracking stability에 미치는 영향을 path planning에 충분히 반영하지 않는다고 주장한다.

### 에이전트 추론

이 논문은 `CAND-01` Step 5에서 `localization failure count`, near collision, dynamic map contamination 같은 failure metric을 정당화하는 근거다.

## Core Idea

Global NBV와 local NBV를 hierarchical하게 결합한다. Global NBV는 occupancy grid entropy reduction으로 exploration target을 고르고, local NBV는 current feature distribution과 tracked dynamic object motion을 합친 `Feature Probability Map`으로 short-horizon viewpoint를 고른다.

## Input / Output

Input:

- RGB-D stream
- ORB-SLAM2 pose / sparse feature state
- 2D occupancy grid from OctoMap projection
- YOLOv8s semantic segmentation / object detection
- BoT-SORT object tracks
- dynamic object motion estimate

Output:

- global NBV target and yaw
- local NBV direction / short-horizon motion
- updated occupancy map and SLAM trajectory
- tracking loss, near collision, ATE/RPE, ERR evaluation traces

## Method

- Global NBV:
  - occupancy grid frontier를 추출한다.
  - DBSCAN으로 frontier candidates를 downsample한다.
  - eight yaw directions에서 ray casting으로 visible cells를 계산한다.
  - Shannon entropy reduction을 information gain으로 계산한다.
  - translational / rotational cost로 discount한 score를 greedy하게 최대화한다.
- Dynamic object perception:
  - YOLOv8s COCO pretrained model로 object segmentation / detection을 수행한다.
  - BoT-SORT로 object ID를 track한다.
  - epipolar constraint violation이 3 consecutive frames 이상이면 dynamic feature로 판단한다.
  - confirmed dynamic object features는 SLAM optimization에서 제거한다.
- Local NBV:
  - current frame의 static feature point distribution으로 feature probability map을 만든다.
  - tracked object motion을 anisotropic Gaussian distribution으로 모델링한다.
  - feature map과 dynamic influence map을 fuse해 `Feature Probability Map`을 만든다.
  - local candidate views의 predicted `Feature Probability Map` entropy reduction을 비교한다.
  - DWA constraints 안에서 10 Hz로 executable local viewpoint를 선택한다.

## Main Claims

### 논문 주장

- Full hierarchical NBV가 global-only variant보다 tracking loss와 near collision을 줄인다고 주장한다.
- Dynamic environment에서 ATE/RPE 기준 localization accuracy를 개선한다고 주장한다.
- Two simulated environments와 one real-world Meerkat robot scene에서 robustness와 real-time deploy 가능성을 보였다고 주장한다.

## Strengths

- dynamic environment와 active semantic visual SLAM을 직접 연결한다.
- `ATE`, `RPE`, `ERR`, tracking loss rate, near collision counts를 함께 본다.
- `Feature Probability Map`은 dynamic object가 feature observability를 줄이는 현상을 action selection으로 연결한다.
- Real-world Meerkat robot 실험과 module runtime을 보고한다.
- Global-only vs full hierarchical NBV 비교가 있어 local NBV / FPM contribution을 분리해 볼 수 있다.

## Limitations

- Top-tier robotics conference 논문은 아니다.
- Code가 공개되어 있지 않아 재현성이 제한된다.
- Simulation은 Gazebo 두 scene이며, dynamic object는 두 명의 person이 fixed trajectories로 움직이는 설정이다.
- 실제 dynamic class는 실험에서 `person`만 potential dynamic object로 사용한다.
- Open-vocabulary semantics, pre-explored semantic memory, ObjectNav task metric은 다루지 않는다.
- Real-world experiment는 usability demonstration에 가깝고, ATE/RPE table은 simulation 중심이다.
- Robot may still lose track when dynamic objects suddenly occupy most of the camera view.

## Relevance to My Research

### 사실

`CAND-01` Step 5는 map error, semantic accuracy, ATE/RPE, pose graph connectivity를 평가한다. Real-world deploy까지 고려하면 tracking loss와 near collision 같은 robustness metric도 필요하다.

### 에이전트 추론

P03는 `CAND-01`의 core method baseline보다는 dynamic failure metric reference로 강하다. 특히 `tracking loss rate`, near collision counts, moving-object residual map contamination은 semantic memory가 dynamic environment에서 어떻게 실패하는지 보기 좋은 보조 metric이다.

## Follow-up Questions

- `CAND-01`에서 dynamic objects를 main scope에 넣을지, real-world stress test로만 둘지 결정해야 한다.
- `Feature Probability Map`을 semantic uncertainty map과 결합할 수 있는가?
- `tracking loss rate`와 near collision을 Habitat / real robot harness에서 어떻게 정의할 것인가?
- Code가 없을 때 Table 5 스타일의 global-only vs local re-observation ablation만 재구성할 수 있는가?
