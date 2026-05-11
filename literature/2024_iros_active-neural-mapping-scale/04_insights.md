# Insights

## Facts

- `Active Neural Mapping at Scale`는 IROS 2024로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2409.20276 이다.
- arXiv version은 v1이며, submitted date는 2024-09-30이다.
- DBLP records the paper as IROS 2024, pages 7152-7159.
- Authors are Zijia Kuang, Zike Yan, Hao Zhao, Guyue Zhou, and Hongbin Zha.
- Evaluation uses Habitat simulator with Gibson and Matterport3D / MP3D.
- Baselines are `Random`, `FBE`, `UPEN`, and `ANM`.
- Main metrics are `Completion Ratio` and `Completion`.
- No official code or project page was found on 2026-05-07.

## Paper Claims

- The proposed method enables efficient and robust NeRF-based active mapping in large-scale indoor environments.
- `Generalized Voronoi Graph` extracted from the neural map integrates geometry, appearance, topology, and uncertainty.
- Anchoring uncertain areas to GVG vertices enables adaptive granularity along safe paths.
- The method outperforms `Random`, `FBE`, `UPEN`, and `ANM` on Gibson and MP3D mean completion metrics.
- It reconstructs MP3D scenes with more than 20 rooms at over 90% completeness in at most 10,000 steps.

## Inferences

- P06 gives a strong planning abstraction for scaling active re-observation beyond one object or one room.
- `CAND-01` can borrow the idea of anchoring uncertain semantic nodes to sparse navigational topology.
- P06 is weaker as a SLAM uncertainty metric source because it does not report `ATE/RPE` or pose graph connectivity.
- The paper's future work explicitly mentions semantics and object relations, which aligns with `CAND-01` but also shows that current method has not solved semantic memory reuse.

## 사용자 판단 필요

- P06를 implementation baseline으로 보지 않고 topology-aware planning reference로 둘지 결정해야 한다.
- `CAND-01` first probe에서 topology abstraction을 넣을지, semantic uncertainty signal부터 검증한 뒤 나중에 넣을지 결정해야 한다.
- GVG-style topology를 Habitat navigability graph, scene graph, room graph 중 무엇으로 대체할지 결정해야 한다.

## Connection to Field Trends

- Active perception / neural active mapping trend의 strong evidence다.
- Environmental perception intelligence와 robot mobility coupling에 연결된다.
- SLAM-navigation coupling보다는 reconstruction-oriented topology planning에 가깝다.
- Open-vocabulary semantic mapping과는 indirect connection이다.

## Possible Contribution Angles

- Semantic object/node uncertainty를 room/topology graph node에 anchor하기.
- `CAND-01` Step 2 re-observation candidates를 dense viewpoint search가 아니라 sparse topological node search로 줄이기.
- Wrong-goal visit and wasted path를 topology-aware re-observation과 semantic-only re-observation 사이에서 비교하기.
- Step 4에서 SLAM utility와 topology utility를 분리해 `SemanticOnly`, `TopologyOnly`, `SemanticSLAM` ablation 만들기.

## What Would Change This Assessment

- Official code가 공개되거나 authors' config가 확보되면 large-scale active mapping baseline으로 재검토한다.
- `CAND-01` first probe가 one-scene / one-object 수준이면 P06는 과하다.
- First probe에서 semantic uncertainty가 useful하다고 확인되면 P06-style topology anchoring은 scale-up stage에서 중요해진다.
- Real-world deploy에서 narrow passages or multi-room navigation이 핵심 failure mode로 나오면 P06의 topology planning relevance가 커진다.
