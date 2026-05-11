# Paper Card

## Problem

### 사실

Active neural mapping은 agent가 unknown environment를 탐색하면서 neural map을 계속 업데이트하고, map uncertainty를 줄이는 action sequence를 선택하는 문제다.

### 논문 주장

Neural map은 geometry와 appearance를 compact하게 표현하지만, explicit structural information이 부족해 large-scale indoor environment에서 granularity와 topology를 해석하기 어렵다고 주장한다. Greedy active neural mapping은 local minima와 inefficient traversal에 취약하다고 본다.

### 에이전트 추론

P06는 `CAND-01` Step 4-5의 SLAM/map metric보다 Step 2/4의 topology-aware viewpoint planning reference로 더 유용하다. Semantic memory를 room/graph topology와 연결할 때 필요한 "uncertain target을 safe path의 topological node에 anchor한다"는 구조를 제공한다.

## Core Idea

Continually updated neural map에서 `Generalized Voronoi Graph`를 추출하고, visible regions of interest와 accessible regions of interest를 Voronoi vertices에 anchor한다. Sparse topological graph에서 Dijkstra planning을 수행해 safe path를 만들고, local horizon에서는 fine-grained zero-crossing / uncertainty 정보를 사용해 adaptive-granularity exploration을 수행한다.

## Input / Output

Input:

- posed RGB-D observations from Habitat simulator
- continually updated hybrid NeRF / neural map
- zero-crossing surface samples queried from the neural map
- perturbation-based uncertainty over geometry and appearance
- extracted `Generalized Voronoi Graph`

Output:

- sparse topological roadmap of accessible free space
- anchored visible / accessible regions of interest
- Dijkstra path to selected Voronoi vertex
- updated neural map and reconstructed mesh
- completion / coverage traces during exploration

## Method

### 사실

- Neural map maps 3D coordinates to color and TSDF values.
- Surface points are queried from zero-crossings of the neural map.
- `Generalized Voronoi Graph` is extracted from top-down map / zero-crossing surfaces.
- Prediction variance is estimated by perturbing geometry and appearance decoder parameters with Gaussian noise.
- High-variance surface points are treated as visible regions of interest.
- Visible regions of interest are clustered and anchored to nearby Voronoi vertices, which become accessible regions of interest.
- Previously visited areas are depressed so the planner favors unvisited or uncertain Voronoi vertices.
- Path planning uses Dijkstra on the weighted Voronoi graph, with edge weights as Euclidean distance.
- Large-scale scenes use a hierarchical framework: fine local horizon near the camera and coarse global map elsewhere.
- Hybrid representation uses hash-encoded multi-resolution feature grid and one-blob encoding, similar to `Co-SLAM`.
- A bootstrap rotation of 36 steps is used at the beginning to improve initial confidence.

### 에이전트 추론

For `CAND-01`, the reusable method is not NeRF itself but the two-stage transformation: dense uncertainty -> sparse topological anchors -> safe path to target viewpoint. Semantic object/node uncertainty can follow the same pattern.

## Main Claims

### 논문 주장

- A NeRF-based active mapping system can explore large-scale indoor environments with over 20 rooms comprehensively.
- `Generalized Voronoi Graph` lets the system integrate scene geometry, appearance, topology, and uncertainty.
- Anchoring uncertain regions to GVG vertices enables adaptive granularity along safe paths.
- The method outperforms `Random`, `FBE`, `UPEN`, and `ANM` on Gibson and MP3D completion / completion distance.
- It achieves over 90% completeness in large MP3D scenes with 20+ rooms in at most 10,000 steps.

## Strengths

- large-scale에서 topology를 explicit하게 다룬다.
- uncertainty와 safe path planning을 연결한다.
- Gibson and MP3D를 모두 사용한다.
- `Random`, `FBE`, `UPEN`, `ANM`과 비교한다.
- GVG로 accessible region과 visible uncertain region을 분리한다.
- Ablation에서 random Voronoi vertex, best anchored vertex, hierarchical full method를 비교한다.
- Real-time-ish runtime claim을 제시한다. Paper reports 7-9 Hz average system rate.

## Limitations

- Official code가 공개되어 있지 않다.
- semantic memory나 ObjectNav metric은 중심이 아니다.
- posed RGB-D sequence와 Habitat simulator 기반이며, real-world robot deploy는 다루지 않는다.
- Completion 중심 평가라 `ATE/RPE`, pose graph connectivity, wrong-goal visit, wasted path는 없다.
- Semantic relations and object-level structure are future work, not current method.
- MP3D-YmJkq처럼 severe occlusion과 narrow navigable pathways가 있는 scene은 여전히 challenging하다고 보고한다.

## Relevance to My Research

### 사실

`CAND-01`은 semantic memory를 robot mobility decision에 재사용하고, Step 4에서 semantic memory를 active SLAM utility로 확장한다.

### 에이전트 추론

P06는 semantic map object/node uncertainty를 topological nodes에 anchor하는 방향의 근거다. `CAND-01`에서 object/node uncertainty가 dense하거나 candidate가 많아질 경우, GVG-style topology를 사용해 viewpoint candidates를 줄이고 safe path를 보장할 수 있다.

## Follow-up Questions

- Semantic map graph에서 GVG에 해당하는 sparse navigational topology를 어떻게 만들 것인가?
- Habitat ObjectNav에서 dense semantic candidate를 topological node로 anchor하면 wrong-goal visit과 wasted path가 줄어드는가?
- P06의 Dijkstra-on-GVG를 Habitat navigability graph / shortest path planner로 대체할 수 있는가?
- `CAND-01` Step 4-5에서 topology metric을 pose graph connectivity와 어떻게 구분할 것인가?
