# Paper Card

## Problem

Robot experience stream은 text document와 다르다. Observation, pose, timestamp, sensor data가 강하게 spatially correlated되어 있고, 같은 장면이 반복 관측되며, 사용자는 object-level query뿐 아니라 implicit query와 global environment description도 요청한다. 기존 `RAG`, `GraphRAG`, `LightRAG`를 그대로 적용하면 embodied data를 flat text chunk처럼 다뤄 spatial structure와 multi-scale semantics를 잃기 쉽다.

## Core Idea

`Embodied-RAG`는 robot experience를 topological graph로 저장하고, 그 위에 hierarchical `semantic forest`를 만든다. Leaf node에는 pose, observation, timestamp, caption이 있고, non-leaf node에는 LLM summary가 저장된다. Retrieval은 semantic forest를 top-down으로 traverse하고, generation 단계에서는 retrieved chain을 사용해 waypoint 또는 text answer를 생성한다.

## Input / Output

- Input: query, robot pose/location, topological graph node, ego-centric image, timestamp, VLM caption, optional sensor data such as NDVI.
- Output for Find query: selected waypoint / image path and language reasoning.
- Output for Explain query: environment-level or region-level text answer.
- Query types: explicit, implicit, global.

## Method

- Topological map: node stores pose `(x, y, z)`, yaw, timestamp, image, VLM caption; edges come from path history or spatial threshold.
- Semantic forest: complete-linkage hierarchical clustering over hybrid spatial-semantic similarity.
- Spatial similarity: distance-based exponential decay.
- Semantic similarity: cosine similarity between language embeddings of node descriptions.
- Non-leaf summaries: LLM summarizes child descriptions into higher-level area descriptions.
- Retrieval phase 1: LLM-guided top-down traversal chooses relevant child nodes for query.
- Retrieval phase 2: collected base nodes are re-ranked by semantic score, spatial proximity if location is given, and optional sensor-conditioned score.
- Generation: LLM uses retrieved chains as context. For Find queries it emits a waypoint; for Explain queries it emits text.
- Navigation integration: Dijkstra path planning over topological graph plus local planner. The paper uses Unitree-Go2 `go-to-waypoint` API as local planner.

## Main Claims

- `Embodied-RAG` handles explicit, implicit, and global queries over 19 diverse real/simulated environments.
- `semantic forest` builds graph memory 7.38x faster than `GraphRAG` and 9.76x faster than `LightRAG` on the same dataset size.
- On E-image and E-multimodal settings, `Embodied-RAG` outperforms `Naive-RAG`, `GraphRAG`, and `LightRAG` on explicit/implicit Find queries.
- Sensor-conditioned retrieval improves E-multimodal performance, while text RAG baselines do not benefit in the same way.

## Strengths

- Environment-specific perception을 open-world, queryable, hierarchical memory로 바꾼다.
- Object-level retrieval, implicit navigation intent, global environment description을 같은 memory structure로 다룬다.
- Topological graph와 language abstraction을 결합하므로 indoor/outdoor, robot embodiment 차이에 상대적으로 유연하다.
- 공개 GitHub repository가 있어 semantic forest construction과 retrieval logic을 코드 수준으로 확인할 수 있다.

## Limitations

- Low-level SLAM, obstacle avoidance, dynamic object robustness를 직접 해결하지 않는다.
- Navigation task에서 perfect local planner 접근을 가정한다.
- `ATE`, `RPE`, pose graph connectivity, map error, semantic map calibration은 평가하지 않는다.
- Small-scale precise visual reasoning, object counting, multi-view consistency에 약하다고 논문이 밝힌다.
- `(V)LM` API dependency가 있어 offline real-world robot deploy에는 별도 경량화 또는 local model 검증이 필요하다.

## Relevance to My Research

`CAND-01`에는 semantic memory representation 관점에서 중요하다. 특히 Step 1의 object/node uncertainty를 만들 때 `semantic forest`의 retrieval score, hierarchy level, caption ambiguity, spatial-semantic disagreement를 uncertainty source로 볼 수 있다. Step 2의 active re-observation viewpoint selection에는 retrieval failure 또는 low-confidence chain을 re-observation trigger로 연결할 수 있다. 다만 Step 4-5의 active SLAM utility와 SLAM metric은 이 논문이 직접 다루지 않으므로 보조 근거로만 쓰는 것이 맞다.

## Follow-up Questions

- `semantic forest` node의 retrieval uncertainty를 object/node uncertainty로 정의할 수 있는가?
- Multi-view consistency가 없는 점을 active re-observation으로 보완하면 wrong-goal visit과 wasted path가 줄어드는가?
- `Embodied_RAG` repository의 AirSim / topological graph pipeline을 Habitat ObjectNav 또는 real-world replay로 축소 이식할 수 있는가?
