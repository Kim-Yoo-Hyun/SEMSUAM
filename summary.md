# 연구 보고서: Semantic Uncertainty 기반 Active SLAM/Navigation Utility

## 1. 연구 개요

### 사실

본 연구는 환경마다 달라지는 robot deployment 조건에서 AI robot이 perception, mobility, SLAM, navigation을 함께 사용해 새 환경에 적응하는 문제를 다룬다.

현재 primary candidate는 `CAND-01: Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`이다.

### 에이전트 추론

핵심 방향은 pre-explored semantic map의 object/node uncertainty를 단순 confidence score로 쓰지 않고, robot이 어디로 이동해 다시 관찰할지 결정하는 active SLAM/navigation utility로 바꾸는 것이다.

## 2. 연구 배경

### 사실

최근 문헌 흐름은 open-vocabulary semantic map, object-centric memory, active re-observation, SLAM uncertainty, ObjectNav evaluation이 서로 가까워지는 방향이다. 확인한 주요 primary source에는 `VLMaps`, `ConceptGraphs`, `CARe`, `DualMap`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `3D Active Metric-Semantic SLAM`, `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`이 포함된다.

### 논문 주장

`VLMaps`는 visual-language feature를 spatial map에 fuse하면 language-conditioned navigation에 사용할 수 있다고 주장한다. `CARe`는 pre-explored semantic map의 confidence와 multi-view consistency를 활용해 wrong semantic decision을 줄일 수 있다고 주장한다. Active SLAM 계열 논문들은 viewpoint selection이 map quality, pose graph, localization uncertainty를 개선할 수 있다고 주장한다.

### 에이전트 추론

기존 semantic navigation 연구는 semantic candidate selection failure를 줄이는 데 강하고, active SLAM 연구는 map/pose uncertainty reduction에 강하다. 하지만 adaptive robot 관점에서는 semantic uncertainty와 SLAM uncertainty를 같은 mobility decision 안에서 다루는 것이 더 자연스럽다.

## 3. 문제 정의

### 사실

Pre-explored semantic map은 ObjectNav와 language-guided navigation에서 goal candidate를 찾는 데 쓰일 수 있다. 그러나 semantic map에는 false positive object, ambiguous query match, low-support observation, viewpoint bias, stale map 같은 uncertainty가 남는다.

### 에이전트 추론

문제는 "불확실한 semantic memory를 robot이 언제, 어디서 다시 관찰해야 ObjectNav failure와 SLAM/map inconsistency를 함께 줄일 수 있는가"이다.

## 4. 핵심 가설

### 에이전트 추론

If an ObjectNav agent uses pre-explored semantic map object/node uncertainty and SLAM uncertainty to choose active re-observation viewpoints, then wrong-goal visits and wasted path decrease while map/pose consistency improves, compared with semantic-only replanning and geometry-only exploration baselines.

## 5. 제안 방향

### 에이전트 추론

연구는 Step 1-5로 진행한다.

1. Pre-explored semantic map에서 object/node uncertainty를 계산한다.
2. Uncertain candidate에 대해 active re-observation viewpoint를 선택한다.
3. ObjectNav에서 `Success Rate`, `SPL`, wrong-goal visit, wasted path를 측정한다.
4. Semantic memory를 active SLAM utility로 확장한다.
5. Map error, semantic accuracy, `ATE`, `RPE`, pose graph connectivity까지 평가한다.

## 6. 실험 설계

### 사실

Primary benchmark path는 Habitat ObjectNav with HM3D와 HM3D-OVON이다. Docker 기반으로 HM3D v0.2 scene assets, ObjectNav HM3D v2 episodes, HM3D-OVON episodes 접근은 확인했다.

### 에이전트 추론

첫 실험은 full system reproduction보다 작은, 검증 가능한 probe로 시작한다. 먼저 non-GT semantic candidate artifact를 만들고, GT는 candidate commitment 이후 correctness labeling과 oracle reference에만 사용한다.

Primary metrics:

- `Success Rate`
- `SPL`
- wrong-goal visit rate
- wasted path / extra path length
- object candidate precision / recall
- uncertainty calibration

Extension metrics:

- map error
- semantic accuracy
- `ATE`
- `RPE`
- pose graph connectivity
- localization failure count

## 7. 현재 진행한 내용

### 사실

- 연구 workflow: `AGENT.md`, `TODO.md`, `docs/literature.md`, `docs/hypothesis.md`, `docs/index.md` 작성.
- Literature survey: top-tier venue 중심 paper registry와 paper folder 작성.
- Candidate 정리: `literature/CAND-01.md`, `hypothesis/CAND-01/H001_uncertainty-reobservation/` 작성.
- Dataset gate: HM3D v0.2, ObjectNav HM3D v2, HM3D-OVON Docker mount 확인.
- Runtime gate: `research3/habitat-h001:20260508` Docker smoke 통과.
- Evaluation harness: `wrong_goal_visit`, `wasted_path`, GT oracle reference, baseline log smoke 통과.
- Candidate backend: non-GT `artifact_jsonl` boundary 구현.
- Semantic artifact path: `VLMaps` feature-grid artifact exporter 구현.
- Query embedding path: OpenAI `CLIP` `ViT-B/32` text embedding exporter 구현.
- Coordinate gate: `VLMaps` grid-to-Habitat alignment contract 작성.
- End-to-end artifact smoke: `chair` query로 실제 `VLMaps` demo map에서 candidate 5개 생성.
- Alignment adapter: `vlmaps_grid` candidate를 `habitat_world`로 변환하고 Habitat navmesh에서 navigability smoke 통과.
- Real-world deploy gate: ROS 2 mobile base, RGB-D / stereo depth, LiDAR, external GT 기반 sensor / robot / ground truth setup 후보 정리.
- Schedule gate: 6-12개월 범위에서 first probe, Step 4-5 SLAM extension, real-world validation 순서 작성.
- HM3D `VLMaps` path gate: controlled Habitat pre-exploration export와 동일 trajectory metadata 기반 `alignment.json` 생성 경로 선택.
- HM3D exporter smoke: one-scene RGB-D/pose export와 trajectory-derived `alignment.json` adapter smoke 통과.

## 8. 아직 하지 않은 내용

### 사실

- Real HM3D `VLMaps` map artifact는 아직 생성하지 않았다.
- Non-GT semantic candidates로 Habitat ObjectNav full metric은 아직 실행하지 않았다.
- `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` 비교는 아직 구현하지 않았다.
- Real-world deploy용 구체 장비 보유 여부와 사용 가능 GT는 아직 사용자 확인이 필요하다.

### 사용자 판단 필요

- First paper scope를 simulation-only로 둘지, small real-world proof-of-concept까지 포함할지 결정해야 한다.
- Step 4-5에서 live SLAM backend를 언제 도입할지 결정해야 한다.
- Real-world validation에 사용할 robot base, sensor, LiDAR, motion capture 또는 `AprilTag` setup을 결정해야 한다.

## 9. 향후 실험 계획

### 에이전트 추론

1. Separate `vlmaps-hm3d` image에서 one-scene full `VLMaps` map generation을 검증한다.
2. HM3D ObjectNav tiny subset에서 non-GT candidate backend로 `NoReobserve`, `RandomReobserve`, `GTTargetOracle`를 비교한다.
3. Semantic uncertainty 기반 `SemanticOnly` re-observation policy를 추가한다.
4. wrong-goal visit, wasted path, `SR`, `SPL` 기준으로 first probe gate를 평가한다.
5. Pose graph connectivity proxy를 추가해 `SLAMOnly`와 `SemanticSLAM`을 비교한다.
6. Positive signal이 있으면 HM3D-OVON으로 open-vocabulary query ambiguity를 확장 평가한다.
7. Simulation signal이 충분하면 small indoor real-world proof-of-concept를 설계한다.

## 10. 현재 결론

### 사실

현재까지는 논문 주장 검증이 아니라 workflow, dataset, Docker runtime, logging, non-GT candidate artifact path를 준비한 단계다.

### 에이전트 추론

다음 핵심 blocker는 separate `vlmaps-hm3d` image에서 방금 export한 HM3D RGB-D/pose scene을 full `VLMaps` map artifact로 변환하는 것이다. 이 gate가 통과되어야 ObjectNav `SR`, `SPL`, wrong-goal visit, wasted path를 paper-facing evidence로 사용할 수 있다.
