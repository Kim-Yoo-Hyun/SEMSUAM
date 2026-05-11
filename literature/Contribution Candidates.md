# Contribution Candidates

Last updated: 2026-05-06

## Quality Gate Summary

### 사실

- `literature/PAPER.md`에는 34개 primary source 기반 paper registry가 있다.
- 각 paper는 `literature/<year>_<venue-or-arxiv>_<short-title>/` folder로 분리되어 있고, `paper.pdf`, `01_metadata.md`, `02_paper_card.md`, `03_evaluation.md`, `04_insights.md`가 있다.
- `literature/README.md`의 Trend Synthesis는 각 trend마다 최소 2개 이상의 논문 근거를 가진다.

### 에이전트 추론

- 현재 가장 강한 contribution surface는 `pre-explored semantic map`의 오류와 uncertainty를 ObjectNav / active re-observation / SLAM uncertainty / map consistency까지 연결하는 방향이다.
- 3DGS / neural active mapping은 top-tier 근거는 많지만 구현 비용과 compute risk가 커서 primary candidate로 바로 확정하지 않는다.
- graph + LLM navigation은 성능 근거는 강하지만, LLM reasoning과 graph representation contribution을 분리해야 해서 secondary candidate로 둔다.

### 사용자 판단 필요

- Step 1-3 first probe와 Step 4-5 SLAM/map-side extension의 일정과 실험 깊이를 조정해야 한다.
- real-world robot deploy proof-of-concept를 thesis main experiment로 둘지, appendix-level validation으로 둘지 결정해야 한다.

## Candidate Ranking

| ID | Candidate | Status | Why |
| --- | --- | --- | --- |
| CAND-01 | Semantic-SLAM uncertainty-aware active re-observation for adaptive navigation | Primary candidate | Step 1-5 최종 방향이며, semantic uncertainty와 SLAM uncertainty를 함께 평가할 수 있다. |
| CAND-02 | Semantic-memory-conditioned active semantic SLAM utility | Viable candidate | Active SLAM 근거는 충분하지만 prior memory와 직접 닫는 논문은 아직 약하다. |
| CAND-03 | Open-vocabulary semantic loop closure benchmark | Viable candidate | P01의 closed-set limitation과 OVO/OpenScene 계열의 open-vocabulary map을 연결할 수 있다. |
| CAND-04 | LLM-readable graph memory without LLM overdependence | Viable candidate | SG-Nav, CogNav, UniGoal 근거가 강하지만 contribution 분리 실험 설계가 필요하다. |
| CAND-05 | 3DGS active mapping for navigation-aware evaluation | 추가 조사 필요 | top-tier 근거는 충분하지만 6개월-1년 범위에서도 구현/compute risk가 크다. |

## CAND-01: Semantic-SLAM uncertainty-aware active re-observation for adaptive navigation

Status: Primary candidate. Detailed feasibility: `literature/CAND-01.md`.

### 기존 한계

`VLMaps`, `ConceptGraphs`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `DualMap`은 open-vocabulary semantic map을 만들거나 navigation에 사용하는 방향을 보인다. `CARe`는 pre-explored semantic map의 wrong decision을 confidence score와 multi-view consistency로 고치려 한다.

아직 남는 한계는 semantic map의 confidence가 낮을 때 robot이 어떤 행동을 해야 하는지, 그리고 그 행동이 SLAM/map consistency를 실제로 개선하는지 명확하지 않다는 점이다. 많은 방법이 "map을 믿고 goal로 간다" 또는 "실패하면 replanning한다"에 가깝고, uncertainty를 active re-observation viewpoint selection, pose uncertainty, pose graph connectivity와 직접 연결하지 않는다.

### 연구 질문

Pre-explored open-vocabulary semantic map에서 object/node uncertainty와 SLAM uncertainty를 함께 사용해 active re-observation viewpoint를 선택하면 ObjectNav `Success Rate`, `SPL`, wrong-goal visit, wasted path가 개선되고, 동시에 map error, semantic accuracy, ATE/RPE, pose graph connectivity가 개선되는가?

### 가능한 접근

- Step 1: pre-explored semantic map을 `VLMaps` 또는 `ConceptGraphs` style로 만들고 object/node uncertainty를 계산한다.
- Step 2: uncertainty가 높은 object/node에 대해 active re-observation viewpoint를 선택한다.
- Step 3: ObjectNav에서 `Success Rate`, `SPL`, wrong-goal visit, wasted path를 평가한다.
- Step 4: semantic memory를 active SLAM utility로 확장해 pose uncertainty, visibility, loop closure opportunity를 함께 고려한다.
- Step 5: map error, semantic accuracy, ATE/RPE, pose graph connectivity까지 함께 평가한다.
- noisy semantic map을 만들기 위해 object false positive, false negative, viewpoint gap, wrong label, stale object를 controlled perturbation으로 넣는다.

### 필요한 dataset / benchmark

- Primary: Habitat ObjectNav with MP3D / HM3D
- Optional: RoboTHOR for robustness check
- Map construction / semantic evaluation: Replica, ScanNet, ScanNet++ subset
- Metrics: `Success Rate`, `SPL`, `DTS`, extra path length, replanning success, wrong-goal visit rate, map object precision/recall, semantic accuracy, uncertainty calibration, map error, ATE/RPE, pose graph connectivity, localization failure count, runtime

### baseline

- `VLMaps`
- `CARe`
- `ConceptGraphs`
- `DualMap`
- no-replanning semantic map baseline
- random re-observation / frontier re-observation baseline
- `SemanticOnly`: semantic uncertainty만 사용하는 re-observation baseline
- `SLAMOnly`: SLAM uncertainty 또는 geometry-only exploration baseline
- `SemanticSLAM`: semantic uncertainty와 SLAM uncertainty를 결합한 proposed baseline

### 실패 조건

- semantic confidence가 실제 navigation failure와 correlation이 낮으면 실패다.
- re-observation cost가 커서 `SPL`이 떨어지면 실패다.
- SLAM uncertainty proxy가 map error, ATE/RPE, pose graph connectivity 개선으로 이어지지 않으면 Step 4-5 contribution은 약해진다.
- map construction noise가 너무 synthetic해서 real error와 다르면 contribution이 약해진다.
- `CARe` baseline 재현이 어렵거나 code dependency가 과도하면 scope를 줄여야 한다.

### 6개월-1년 범위 판단

가능하다. 단, full open-vocabulary mapping system을 새로 만들지 않고 `VLMaps` / `CARe` / `ConceptGraphs` / Habitat pipeline 중 하나를 재사용해야 한다. 6개월-1년 범위의 staged target은 Step 1-3 first probe, Step 4-5 SLAM/map-side extension, 작은 real-world proof-of-concept 순서다.

### 근거 논문

- `CARe`
- `VLMaps`
- `ConceptGraphs`
- `DualMap`
- `Open-Vocabulary Online Semantic Mapping for SLAM`
- `Semantic Environment Atlas`
- `SG-Nav`
- `MemoNav`

## CAND-02: Semantic-memory-conditioned active semantic SLAM utility

Status: Viable candidate.

### 기존 한계

`3D Active Metric-Semantic SLAM`과 `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`은 semantic information과 SLAM uncertainty를 exploration utility로 넣는다. 그러나 이들은 mostly online observation 기반이고, previously acquired environment-specific perception을 prior로 재사용하는 문제를 직접 닫지는 않는다.

반대로 `CARe`, `Semantic Environment Atlas`, `Embodied-RAG`, `DualMap`은 memory / navigation reuse를 다루지만, active SLAM의 map error, pose graph connectivity, ATE/RPE까지 직접 연결하지 않는다.

### 연구 질문

Pre-explored semantic memory를 active SLAM utility에 넣으면 exploration cost를 줄이면서 map error, semantic classification accuracy, pose uncertainty를 개선할 수 있는가?

### 가능한 접근

- Habitat / Replica에서 lightweight active mapping simulator를 구성한다.
- utility를 frontier information gain, semantic prior uncertainty, pose graph connectivity로 분해한다.
- prior semantic memory가 맞는 경우와 틀린 경우를 나눠 overconfident prior failure를 측정한다.
- semantic prior가 exploration target selection과 loop closure candidate selection에 미치는 영향을 ablation한다.

### 필요한 dataset / benchmark

- Habitat, Replica, Gibson
- Optional: ScanNet RGB-D sequence for offline map construction
- Metrics: average map error, semantic classification accuracy, coverage, path length, ATE/RPE, pose graph connectivity, replanning count

### baseline

- frontier exploration
- semantic-only exploration
- pose graph connectivity-only exploration
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`
- `3D Active Metric-Semantic SLAM` style active SLC ablation

### 실패 조건

- prior semantic memory가 exploration cost를 줄이지 못하거나 map error를 늘리면 실패다.
- active SLAM simulator가 실제 SLAM uncertainty를 너무 단순화하면 contribution이 약하다.
- P02 code/evaluation protocol 재현이 불가능하면 비교력이 떨어진다.

### 6개월-1년 범위 판단

조건부로 가능하다. full UAV / real robot stack을 main experiment로 두기보다는 Habitat 기반 simplified active semantic SLAM harness를 먼저 만들고, real-world robot deploy는 작은 proof-of-concept로 제한해야 한다.

### 근거 논문

- `3D Active Metric-Semantic SLAM`
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`
- `Mutual information-based hierarchical NBV decision`
- `Semantic Environment Atlas`
- `Embodied-RAG`
- `DualMap`
- `CARe`

## CAND-03: Open-vocabulary semantic loop closure benchmark

Status: Viable candidate.

### 기존 한계

`3D Active Metric-Semantic SLAM`은 sparse semantic landmarks로 `Semantic Loop Closure`를 수행하지만 실험 semantic object는 chair class 중심이다. `OpenScene`, `ConceptGraphs`, `Open-Vocabulary Online Semantic Mapping for SLAM`은 open-vocabulary 3D semantics를 제공하지만, loop closure / relocalization metric으로 직접 평가되는 경우는 제한적이다.

### 연구 질문

Open-vocabulary object landmarks는 closed-set object landmarks 또는 visual feature loop closure보다 drastic viewpoint change, repeated objects, wrong labels 조건에서 더 robust한 loop closure signal을 제공하는가?

### 가능한 접근

- RGB-D sequence에서 open-vocabulary object nodes를 추출한다.
- object embedding similarity, geometric arrangement, confidence score를 함께 사용해 loop closure candidate를 만든다.
- controlled perturbation으로 repeated objects, sparse objects, false positives, viewpoint gap을 만든다.
- offline factor graph 또는 pose graph correction으로 loop closure success가 ATE/RPE를 줄이는지 측정한다.

### 필요한 dataset / benchmark

- ScanNet, ScanNet++, Replica, TUM-RGBD
- Optional: author-collected loop closure sequences if available
- Metrics: loop detection precision/recall, relative pose error, ATE/RPE before/after loop closure, semantic landmark precision/recall, runtime

### baseline

- ORB-SLAM3 loop closure
- Kimera / visual feature loop closure
- closed-set object landmark loop closure
- `OVO-SLAM`
- `ConceptGraphs` object association

### 실패 조건

- open-vocabulary detector noise가 loop closure precision을 크게 낮추면 실패다.
- semantic object가 충분히 없는 scenes에서 loop recall이 낮으면 contribution을 환경 조건부로 제한해야 한다.
- factor graph integration이 과도하게 커지면 benchmark-only paper로 scope를 낮춰야 한다.

### 6개월-1년 범위 판단

가능하나 scope 관리가 중요하다. real-time SLAM system이 아니라 offline loop closure benchmark로 시작해야 6개월-1년 범위에서 검증 가능하다.

### 근거 논문

- `3D Active Metric-Semantic SLAM`
- `OpenScene`
- `ConceptGraphs`
- `Open-Vocabulary Online Semantic Mapping for SLAM`
- `SNI-SLAM`
- `VLMaps`

## CAND-04: LLM-readable graph memory without LLM overdependence

Status: Viable candidate.

### 기존 한계

`SG-Nav`, `CogNav`, `UniGoal`, `Open Scene Graphs`는 scene graph, cognitive map, goal graph 같은 LLM-readable structure를 사용해 ObjectNav 성능을 높인다. 하지만 graph representation의 품질, LLM reasoning, detector quality, re-perception mechanism이 각각 얼마나 기여하는지 분리하기 어렵다.

### 연구 질문

ObjectNav에서 LLM을 쓰지 않는 lightweight graph heuristic이 LLM-based scene graph planner와 어느 정도까지 경쟁할 수 있으며, graph uncertainty / re-perception이 성능 차이를 설명하는가?

### 가능한 접근

- scene graph를 object node, room node, relation edge, confidence로 구성한다.
- planner를 LLM prompt planner, heuristic graph search, learned scoring으로 나눠 비교한다.
- graph uncertainty가 높은 node는 re-perception 또는 local search를 유도한다.
- token cost, runtime, SR/SPL, failure mode를 함께 측정한다.

### 필요한 dataset / benchmark

- MP3D, HM3D, RoboTHOR ObjectNav
- Optional: text-goal / image-goal tasks for `UniGoal` style extension
- Metrics: `Success Rate`, `SPL`, `DTS`, category-wise SR, token cost, runtime, graph error rate

### baseline

- `SG-Nav`
- `CogNav`
- `UniGoal`
- `ConceptGraphs`
- no-LLM graph search baseline
- no-reperception baseline

### 실패 조건

- LLM planner와 graph heuristic의 difference가 graph quality가 아니라 hidden prompt / model artifact로만 설명되면 contribution이 약하다.
- code release가 없어서 fair reproduction이 어렵다면 additional investigation이 필요하다.
- graph construction 자체가 너무 noisy하면 planner 비교가 무의미해진다.

### 6개월-1년 범위 판단

가능하지만 baseline reproduction risk가 있다. 최소 범위는 `ConceptGraphs` style graph + ObjectNav simulator + LLM-free heuristic / LLM planner ablation이며, full LLM navigation system reproduction은 후순위로 둔다.

### 근거 논문

- `SG-Nav`
- `CogNav`
- `UniGoal`
- `Open Scene Graphs`
- `ConceptGraphs`
- `MemoNav`

## CAND-05: 3DGS active mapping for navigation-aware evaluation

Status: 추가 조사 필요.

### 기존 한계

`SplaTAM`, `ActiveSplat`, `ActiveGAMER`, `Neural Visibility Field`, `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information`은 neural field / 3DGS map을 active mapping backbone으로 사용한다. 그러나 많은 평가가 reconstruction fidelity, rendering quality, coverage 중심이고, mobile robot navigation의 collision risk, localization failure, semantic memory update까지 닫는 evidence는 아직 제한적이다.

### 연구 질문

3DGS / neural uncertainty 기반 active mapping이 ObjectNav success, localization robustness, semantic map update까지 개선하는가, 아니면 reconstruction metric만 개선하는가?

### 가능한 접근

- `SplaTAM` 또는 `ActiveGAMER` code를 사용해 Replica / MP3D scenes에서 map을 만든다.
- next-best-view objective를 rendering uncertainty, semantic goal uncertainty, navigation cost로 분해한다.
- reconstruction metric과 navigation metric 사이의 correlation을 측정한다.

### 필요한 dataset / benchmark

- Replica, MP3D, Gibson
- Metrics: PSNR, SSIM, LPIPS, depth error, coverage, path length, runtime, `Success Rate`, `SPL`, ATE/RPE

### baseline

- `SplaTAM`
- `ActiveGAMER`
- `ActiveSplat`
- `Neural Visibility Field`
- frontier / random NBV

### 실패 조건

- compute cost가 커서 반복 실험이 어렵다면 실패다.
- reconstruction metric improvement가 navigation metric과 무관하면 contribution 방향을 바꿔야 한다.
- code integration이 초기 재현 단계에서 길어지면 6개월-1년 전체 일정에서 핵심 실험을 압박한다.

### 6개월-1년 범위 판단

현재는 확정하지 않는다. code 재현성과 compute budget을 먼저 확인해야 한다.

### 근거 논문

- `SplaTAM`
- `ActiveSplat`
- `ActiveGAMER`
- `Neural Visibility Field`
- `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information`
- `Active Neural Mapping`

## Primary Candidate Decision

### 사실

`CAND-01`은 최소 6개 이상의 primary source 근거가 있고, dataset / benchmark / metric / baseline이 가장 명확하다. 현재 최종 연구 방향은 Step 5까지 포함한다.

### 에이전트 추론

`CAND-01`은 석사 연구의 contribution statement를 "pre-explored semantic map uncertainty와 SLAM uncertainty를 active re-observation utility로 변환해 navigation outcome과 map/pose consistency를 함께 개선한다"로 잡을 수 있다. 이는 논문 주장과 에이전트 추론을 구분하기 쉽고, 실패하더라도 semantic confidence calibration, map error taxonomy, re-observation cost, SLAM uncertainty proxy validity라는 학습 결과를 남길 수 있다.

### 사용자 판단 필요

이 후보를 primary candidate로 유지하려면 다음 단계에서 `CARe`, `VLMaps`, Habitat ObjectNav pipeline의 실행 가능성과 Step 4-5 SLAM metric 측정 가능성을 먼저 확인해야 한다.
