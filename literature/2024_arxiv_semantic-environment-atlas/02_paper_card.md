# Paper Card

## Problem

ObjectNav agent는 unseen environment에서 goal object를 찾기 위해 현재 관측, 과거 환경에서 학습한 place-object relation, noisy pose/action 조건을 함께 다뤄야 한다. 기존 learning-based navigation은 계산 비용이 크고, noiseless pose sensor에 강하게 의존하거나, 환경 변화가 있을 때 map memory를 충분히 갱신하지 못하는 문제가 있다.

## Core Idea

`Semantic Environment Atlas`는 여러 환경에서 만든 `Semantic Graph Map`을 통합해 place-place reachability와 place-object relation을 저장한다. navigation 중에는 single query image로 현재 place를 localization하고, goal object가 있을 가능성이 높은 place를 subgoal로 선택하며, 실패 관측이 나오면 place-object probability를 update한다.

## Input / Output

- Input: 512x128 panoramic RGB observation for global semantic localization and mapping, 640x480 directional RGB-D observation for local policy, goal object category name.
- Output: current place estimate, target place / subgoal place, local navigation action, updated place-object relation.
- Action space: move forward 0.4m, turn left 30 degrees, turn right 30 degrees, stop.

## Method

- `Semantic Graph Map` node: place node, image node, object node.
- `Semantic Graph Map` edge: image-image affinity, image-object affinity, place-image assignment.
- Place encoder: image features, object features, object categories를 이용해 place representation을 만들고 contrastive loss로 학습한다.
- `Semantic Environment Atlas`: 여러 training environment의 `Semantic Graph Map`을 place reachability matrix와 place-object connection matrix로 통합한다.
- Global policy: current place와 goal object의 place-object relation을 바탕으로 target place와 subgoal place를 고른다.
- Local policy: depth 기반 local top-down map과 Fast Marching Method를 사용한다. 논문 설정에서 global pose sensor reading은 쓰지 않고 local policy에만 local pose를 사용한다.
- Adaptive update: 목표 object를 예상 place에서 찾지 못하면 Bayesian-style update로 해당 place-object relation을 낮추고 다른 후보 place를 탐색한다.

## Main Claims

- `SEA`는 `ObjectNav`에서 Success 39.0%, SPL 13.7, DTS 5.0을 달성해 비교 방법보다 높은 Success와 낮은 DTS를 보인다고 주장한다.
- `SEA w/o Update` 대비 adaptive update가 Success를 33.3에서 39.0으로 높인다고 주장한다.
- Noisy odometry / actuation 조건에서 metric map 기반 방법보다 성능 저하가 작다고 주장한다.
- Single query image localization에서 `SEA`가 Acc@0.5m 40.4, Acc@1m 73.1을 기록해 graph-based visual localization baselines보다 높다고 주장한다.

## Strengths

- Previous environment-specific perception을 reusable semantic memory로 구성한다.
- Navigation 성능을 `Success`, `SPL`, `DTS`로 평가하고, localization 성능을 `Acc@0.5m`, `Acc@1m`으로 별도 측정한다.
- ObjectNav 실패 후 relation update를 통해 environment change에 적응하는 요소가 있다.
- Global metric map 없이 semantic reachability와 place-object memory를 쓰기 때문에 noisy pose 조건에 대한 contrast가 명확하다.

## Limitations

- Active re-observation viewpoint selection이나 explicit SLAM uncertainty는 다루지 않는다.
- `ATE`, `RPE`, pose graph connectivity, map error 같은 SLAM metric은 평가하지 않는다.
- `SEA` construction은 training environments의 random exploration episodes와 learned detector/encoder에 의존한다.
- Object detector 성능 저하, unseen object category, real-world sensor noise가 semantic relation update에 주는 영향은 제한적으로만 확인된다.
- Local policy에는 depth 기반 local map과 local pose가 필요하므로 완전히 SLAM-free navigation이라고 보기 어렵다.

## Relevance to My Research

`CAND-01` Step 1-3에는 강하게 연결된다. Pre-explored semantic memory에서 object/place uncertainty를 계산하고, ObjectNav에서 `Success`, `SPL`, wrong-goal visit, wasted path를 보는 방향의 직접 근거가 된다. Step 4-5의 active SLAM utility 확장에는 간접 근거다. 이 논문은 semantic memory가 navigation behavior를 바꿀 수 있음을 보이지만, SLAM uncertainty와 pose graph quality를 함께 최적화하지는 않는다.

## Follow-up Questions

- `SEA`의 place-object relation update를 object/node uncertainty로 바꿀 때 entropy, disagreement, failed-observation count 중 어떤 proxy가 가장 안정적인가?
- `SEA`처럼 previous environment memory를 쓰되, active re-observation viewpoint가 SLAM map quality에도 이득을 주는지 어떻게 분리해서 측정할 수 있는가?
- Habitat ObjectNav에서 `SEA` 수준의 full reproduction 없이도 one-scene replay 또는 semantic map perturbation probe로 같은 failure mode를 재현할 수 있는가?
