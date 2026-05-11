# Literature

Last updated: 2026-05-07

## Field Map

### Scope

최근 조사 범위는 robot mobility를 통해 환경을 능동적으로 학습하고, 이전에 얻은 environment-specific perception을 SLAM과 robot navigation에 재사용하는 연구 흐름이다. 중심 키워드는 active perception, Active SLAM, semantic SLAM, neural mapping, 3D Gaussian Splatting, open-vocabulary semantic map, embodied memory, object-goal navigation, language-guided navigation이다.

이번 업데이트는 CVPR, ICCV, ICRA, CoRL, NeurIPS, RA-L, IJRR 등 top-tier conference/journal primary source를 우선 확인했다.

### Venue Coverage

- CVPR: `OpenScene`, `SplaTAM`, `SNI-SLAM`, `NARUTO`, `Neural Visibility Field`, `MemoNav`, `ActiveGAMER`, `UniGoal`
- ICCV: `Active Neural Mapping`, `LERF`, `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information`, `CogNav`
- ICRA: `VLMaps`, `ConceptGraphs`, `Scene Action Maps`
- IROS: `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`
- CoRL: `Context-Aware Replanning with Pre-explored Semantic Map for Object Navigation`
- NeurIPS: `Embodied-RAG`, `SG-Nav`, `Trajectory Diffusion for ObjectGoal Navigation`
- RSS: `Uni-NaVid`
- RA-L / robotics journal: `3D Active Metric-Semantic SLAM`, `DualMap`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `ActiveSplat`
- IJRR: `Open Scene Graphs for Open-World Object-Goal Navigation`

### Core Axes

- Mobility as sensing: robot motion을 단순 이동이 아니라 next-best-view, exploration, active reconstruction, active mapping을 위한 정보 획득 행동으로 다룬다.
- Environmental perception intelligence: geometry-only map보다 object, place, affordance, language query, scene relation을 담는 semantic map과 memory가 중요해지고 있다.
- SLAM-navigation coupling: exploration planner가 SLAM state uncertainty, pose graph connectivity, loop closure 가능성, dynamic object risk를 함께 고려하는 방향으로 이동하고 있다.
- Map representation: occupancy grid와 pose graph 위에 metric-semantic map, 3D scene graph, neural field, 3D Gaussian Splatting map, semantic forest, dual global-local map이 얹히고 있다.
- Prior experience reuse: 한 번 관찰한 환경 또는 여러 환경에서 얻은 place-object relation, semantic landmark, hierarchical memory를 localization, object-goal navigation, replanning에 재사용하려는 흐름이 있다.
- Evaluation surface: Habitat, MP3D, HM3D, Replica, Gibson, RoboTHOR, ScanNet, TUM-RGBD와 real robot 환경이 함께 쓰이며, metric은 map error, semantic classification accuracy, ATE/RPE, success rate, SPL, coverage, reconstruction completeness, PSNR, Depth L1, cost, latency로 분산되어 있다.

## Trend Synthesis

### 1. Active SLAM is becoming semantic and uncertainty-aware.

**사실**

최근 Active SLAM 연구는 frontier exploration이나 geometry-only information gain을 넘어 semantic information, pose uncertainty, pose graph connectivity, dynamic object handling을 함께 최적화한다.

**논문 근거**

- `3D Active Metric-Semantic SLAM`은 GPS-denied multi-floor indoor environment에서 exploration efficiency와 agent state uncertainty를 함께 균형화하고, Semantic Loop Closure로 pose/map uncertainty를 낮추는 방향을 제시한다.
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`은 semantic mutual information과 pose graph connectivity metric을 함께 utility로 사용해 active metric-semantic SLAM을 구성한다.
- `Mutual information-based hierarchical NBV decision for active semantic visual SLAM under dynamic environments`는 semantic segmentation, dynamic object tracking, global/local NBV를 결합해 dynamic environment에서 active visual SLAM의 tracking robustness를 다룬다.

**에이전트 추론**

석사 연구 후보로는 "semantic prior가 active SLAM의 viewpoint selection과 localization robustness를 얼마나 개선하는가"를 작게 검증할 수 있다. 단, dataset과 metric을 먼저 고정해야 한다.

### 2. Neural field and 3DGS representations are becoming active mapping backbones.

**사실**

NeRF, hybrid neural field, 3D Gaussian Splatting 기반 map은 고품질 reconstruction만이 아니라 uncertainty estimation, rendering-based information gain, path planning, active exploration의 내부 표현으로 쓰이기 시작했다.

**논문 근거**

- `Active Neural Mapping`은 continuously learned neural scene representation의 uncertainty를 이용해 traversable path와 target exploration space를 선택한다.
- `NARUTO`는 neural active reconstruction에서 learned uncertainty를 goal searching과 path planning에 사용한다.
- `Neural Visibility Field for Uncertainty-Driven Active Mapping`은 NeRF visibility uncertainty를 next-best-view 선택에 연결한다.
- `Active Neural Mapping at Scale`은 neural map에서 topology와 uncertainty를 결합해 large-scale indoor exploration을 다룬다.
- `SplaTAM`, `ActiveSplat`, `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information`, `ActiveGAMER`, `Splat-SLAM`은 3D Gaussian Splatting 또는 Gaussian map을 SLAM, active reconstruction, exploration의 map backbone으로 사용한다.

**에이전트 추론**

이 흐름은 "map representation이 planner에 어떤 uncertainty 또는 semantic signal을 제공할 수 있는가"를 연구 질문으로 만들기 좋다. 다만 3DGS 계열은 compute와 implementation 비용이 커서 6개월-1년 범위에서도 simulator와 기존 codebase 재사용 가능성을 먼저 확인해야 한다.

### 3. Environmental perception is shifting toward open-vocabulary semantic maps and retrievable embodied memory.

**사실**

robot navigation 쪽 환경 표현은 closed-set semantic segmentation에서 open-vocabulary object/scene grounding, 3D scene graph, semantic atlas, hierarchical memory로 확장되고 있다.

**논문 근거**

- `OpenScene`은 labeled 3D dataset 없이 CLIP-aligned dense 3D feature를 학습해 open-vocabulary 3D scene understanding을 가능하게 한다.
- `LERF`는 NeRF 내부에 multi-scale language field를 학습해 3D relevancy map과 long-tail query를 지원한다.
- `VLMaps`는 pretrained visual-language feature를 3D reconstruction에 fuse해 natural language indexing과 spatial command navigation을 지원한다.
- `ConceptGraphs`는 open-vocabulary 3D scene graph를 만들어 language prompt 기반 perception and planning에 사용한다.
- `Open-Vocabulary Online Semantic Mapping for SLAM`은 posed RGB-D sequence에서 3D segment를 detect/track하고 CLIP descriptor를 merge해 online open-vocabulary 3D semantic mapping을 SLAM backbone과 연결한다.
- `Semantic Environment Atlas for Object-Goal Navigation`은 여러 환경의 semantic graph map을 통합해 place-object relation memory를 만들고 visual localization과 object-goal navigation에 사용한다.
- `Embodied-RAG`는 robot experience를 hierarchical semantic forest로 저장해 navigation query와 explanation query에 검색 가능하게 만든다.

**에이전트 추론**

사용자가 제시한 "previous environment-specific perception 기반 SLAM/navigation 효율화"와 가장 직접적으로 맞닿는 축이다. 기여 후보는 foundation model 자체보다 memory representation, retrieval condition, navigation/SLAM metric 연결에서 찾는 편이 현실적이다.

### 4. Pre-explored semantic maps are becoming actionable but need uncertainty-aware correction.

**사실**

이전 exploration으로 만든 semantic map을 object navigation에 재사용하는 논문들이 늘고 있지만, map retrieval error와 perception bias를 그대로 믿지 않고 uncertainty나 re-perception으로 수정하려는 흐름이 함께 나타난다.

**논문 근거**

- `Context-Aware Replanning with Pre-explored Semantic Map for Object Navigation`은 pre-explored semantic map의 오류를 confidence score와 multi-view consistency로 추정해 replanning한다.
- `One Map to Find Them All`은 consecutive object queries에서 이전 search로 얻은 reusable open-vocabulary feature map을 재사용하고 semantic uncertainty를 multi-object exploration에 활용한다.
- `DualMap`은 dynamic changing scenes에서 global abstract map과 local concrete map을 나눠 online semantic mapping과 natural language navigation을 수행한다.
- `MemoNav`는 short-term, long-term, working memory를 topological map 위에 구성해 multi-goal visual navigation 효율을 높인다.

**에이전트 추론**

석사 연구에서 가장 현실적인 방향은 "pre-explored semantic map의 uncertainty를 어떻게 정의하고, 실패 후 replanning 또는 active re-observation에 어떻게 연결할 것인가"이다.

### 5. Navigation is becoming graph-structured and LLM-readable.

**사실**

zero-shot ObjectNav, language-guided navigation, generalist navigation은 raw map이나 raw observation을 그대로 쓰기보다 scene graph, landmark graph, cognitive map, goal graph처럼 LLM이 읽을 수 있는 구조로 변환한다.

**논문 근거**

- `SG-Nav`는 online 3D scene graph와 hierarchical chain-of-thought prompt를 사용해 LLM-based zero-shot ObjectNav를 수행한다.
- `CogNav`는 scene graph, landmark graph, occupancy map으로 구성된 heterogeneous cognitive map을 만들고 LLM으로 cognitive state transition을 결정한다.
- `UniGoal`은 scene graph와 goal graph를 통일된 graph representation으로 만들어 object category, instance image, text goal navigation을 한 framework로 다룬다.
- `Open Scene Graphs for Open-World Object-Goal Navigation`은 Open Scene Graph를 persistent scene memory로 사용해 open-world ObjectNav를 구성한다.

**에이전트 추론**

이 흐름은 "environmental perception intelligence"를 단순 semantic label이 아니라 planning interface로 보는 방향이다. SLAM 연구와 연결하려면 graph node/edge의 uncertainty, update cost, localization effect를 metric으로 넣어야 한다.

### 6. SLAM-free VLM/VLA navigation is a competing baseline, not a separate field.

**사실**

최근 embodied navigation은 SLAM을 유지하는 map-centric pipeline과 SLAM-free 또는 map-light video/VLM/VLA policy로 갈라진다. 그러나 두 방향 모두 current frame만으로는 부족해서 observation history, video context, semantic memory, topological abstraction을 사용한다.

**논문 근거**

- `NaVid`는 map, odometer, depth 없이 monocular RGB video stream과 instruction으로 next-step action을 예측한다.
- `Uni-NaVid`는 여러 embodied navigation task를 video-based VLA model 하나로 통합하려고 한다.
- `OctoNav`는 ObjNav, ImgNav, VLN 등 분리된 navigation task를 multi-modal, multi-capability instruction-trajectory benchmark와 method로 통합하려고 한다.
- `SLAM-Free Visual Navigation with Hierarchical Vision-Language Perception and Coarse-to-Fine Semantic Topological Planning`은 dense geometry 대신 vision-language perception과 semantic-probabilistic topological map을 사용한다.

**에이전트 추론**

SLAM-free 흐름은 SLAM을 대체한다기보다 "navigation success에 필요한 memory와 perception abstraction이 무엇인가"를 반대로 보여준다. 본 연구가 SLAM을 포함한다면, SLAM-free baseline이나 ablation을 비교 대상으로 둘 수 있다.

## Cross-Paper Insights

- Low confidence: semantic memory가 active SLAM의 next-best-view selection을 직접 개선한다는 연결은 아직 강한 trend로 보기 어렵다. SEA, Embodied-RAG, DualMap, CARe는 memory/navigation을 보이고 Active Semantic Mapping, Active Neural Mapping 계열은 active mapping을 보이지만, "prior environment-specific perception -> active SLAM efficiency"를 직접 닫는 논문은 더 찾아야 한다.
- Low confidence: multimodal LLM을 long-horizon exploration planner로 쓰는 방향은 나타나지만, mapping quality, localization robustness, cost를 함께 검증하는 표준 benchmark는 아직 분산되어 있다.
- Low confidence: dynamic environment에서 semantic active SLAM의 필요성은 분명하지만, real-world dynamic benchmark와 repeatable metric이 충분히 정리되어 있는지는 추가 확인이 필요하다.
- Low confidence: 3DGS active mapping은 reconstruction fidelity에 강하지만, mobile robot navigation에서 collision risk, localization failure, online memory update까지 포함한 end-to-end evidence는 아직 제한적으로 보인다.
- Low confidence: graph-structured LLM navigation의 성능 개선은 뚜렷하지만, LLM reasoning 자체와 map representation quality의 기여를 분리하는 ablation은 더 엄격히 볼 필요가 있다.

## Open Questions

- 이전 environment-specific perception을 어떤 representation으로 저장해야 SLAM과 navigation 양쪽에 도움이 되는가?
- semantic memory가 exploration cost, map error, ATE/RPE, object-goal success, SPL 중 무엇을 가장 직접적으로 개선하는가?
- prior semantic memory를 쓰면 unknown environment generalization이 좋아지는가, 아니면 특정 layout에 overfit되는가?
- active SLAM에서 semantic objective와 localization robustness objective가 충돌할 때 어떤 arbitration rule이 필요한가?
- Habitat, MP3D, HM3D, Replica, Gibson, RoboTHOR, ScanNet 중 어떤 dataset이 active mobility, semantic memory, SLAM/navigation metric을 동시에 검증하기에 가장 적합한가?
- 석사 6개월-1년 범위에서는 3DGS 기반 full system, semantic memory + active planner, lightweight SLAM/navigation metric 조합 중 어디까지 목표로 둘 수 있는가?
- pre-explored semantic map의 오류를 annotation 없이 추정할 때, confidence, entropy, multi-view consistency, geometric consistency 중 무엇이 가장 robust한가?

## Open Question to Candidate Links

### 사실

| Open question | Candidate link | Primary evidence |
| --- | --- | --- |
| 어떤 representation으로 저장해야 SLAM과 navigation 양쪽에 도움이 되는가? | `CAND-01`, `CAND-02`, `CAND-03`, `CAND-04` | `VLMaps`, `ConceptGraphs`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `SG-Nav`, `3D Active Metric-Semantic SLAM` |
| semantic memory가 어떤 metric을 가장 직접적으로 개선하는가? | `CAND-01` | `CARe`, `SG-Nav`, `Semantic Environment Atlas`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration` |
| prior semantic memory가 generalization을 돕는가, overfit을 만드는가? | `CAND-01`, `CAND-02` | `CARe`, `Semantic Environment Atlas`, `Embodied-RAG`, `DualMap` |
| semantic objective와 localization robustness objective가 충돌할 때 어떤 arbitration rule이 필요한가? | `CAND-01`, `CAND-02` | `3D Active Metric-Semantic SLAM`, `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`, `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information` |
| 어떤 dataset이 active mobility, semantic memory, SLAM/navigation metric을 동시에 검증하기에 적합한가? | `CAND-01`, `CAND-03` | `CARe`, `SG-Nav`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `VLMaps`, `ConceptGraphs` |
| 6개월-1년 범위에서 어디까지 목표로 둘 수 있는가? | `CAND-01`, `CAND-05` | `VLMaps`, `CARe`, `ConceptGraphs`, `Open-Vocabulary Online Semantic Mapping for SLAM`, `SplaTAM`, `ActiveGAMER` |
| annotation 없이 semantic map 오류를 어떻게 추정할 수 있는가? | `CAND-01`, `CAND-03` | `CARe`, `SG-Nav`, `ConceptGraphs`, `Open-Vocabulary Online Semantic Mapping for SLAM` |

### 논문 주장

- `CARe`는 pre-explored semantic map의 confidence와 multi-view consistency를 사용해 wrong target decision을 줄인다고 주장한다.
- `SG-Nav`는 online 3D scene graph와 graph-based re-perception이 zero-shot ObjectNav success를 높인다고 주장한다.
- `Open-Vocabulary Online Semantic Mapping for SLAM`은 online open-vocabulary semantic mapping을 SLAM backbone과 결합해 semantic segmentation metric과 `ATE RMSE`를 함께 평가할 수 있다고 주장한다.
- `3D Active Metric-Semantic SLAM`과 `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`은 semantic signal과 SLAM uncertainty / pose graph quality를 active planning utility로 사용할 수 있다고 주장한다.

### 에이전트 추론

- `CAND-01`은 Open Questions 대부분을 하나의 staged thesis로 묶는 primary candidate다. Step 1-3은 semantic memory uncertainty가 ObjectNav behavior를 바꾸는지 보고, Step 4-5는 같은 uncertainty를 SLAM/map-side utility까지 확장한다.
- `CAND-02`는 `CAND-01`의 Step 4-5와 겹치므로 현재는 별도 primary로 밀기보다 `CAND-01`의 SLAM extension 근거로 쓰는 편이 낫다.
- `CAND-03`은 Step 5에서 open-vocabulary semantic loop closure가 핵심으로 부상할 때 분리할 수 있는 fallback / side candidate다.
- `CAND-04`는 LLM-readable graph memory의 contribution 분리 문제가 중요해질 때 보조 후보로 남긴다.
- `CAND-05`는 compute와 reproduction risk가 커서 지금은 thesis main path보다 추가 조사 후보가 맞다.

### 사용자 판단 필요

- 다음 단계에서는 `CAND-01` first probe를 `CARe` / `VLMaps` / `ConceptGraphs` 중 어디서 시작할지 결정해야 한다.
- Step 5의 SLAM-side metric을 처음부터 포함할지, Step 1-3 ObjectNav probe가 통과한 뒤 확장할지 결정해야 한다.
- Real-world deploy는 main experiment인지 proof-of-concept인지 정해야 한다.
