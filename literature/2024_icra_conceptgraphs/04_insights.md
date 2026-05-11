# Insights

## Facts

- `ConceptGraphs: Open-Vocabulary 3D Scene Graphs for Perception and Planning` is an ICRA 2024 paper.
- Primary project page is https://concept-graphs.github.io/
- arXiv source is https://arxiv.org/abs/2309.16650
- Official code is https://github.com/concept-graphs/concept-graphs
- The method builds object-centric open-vocabulary 3D scene graphs from posed RGB-D sequences.
- Core components include `SAM`, `CLIP`, `LLaVA`, `GPT-4`, `RAM`, `Grounding DINO`, multi-view object association, and LLM-generated spatial relationships.
- Main quantitative datasets are `Replica` and a `REAL Lab` scan.
- Real-world demonstrations use `Clearpath Jackal UGV` and `Boston Dynamics Spot Arm`.
- AI2Thor / ProcThor support exists in code, but no quantitative AI2Thor evaluation is reported in the README.
- The paper does not report active SLAM uncertainty, `ATE/RPE`, pose graph connectivity, ObjectNav `SR/SPL`, wrong-goal visit, or wasted path.

## Paper Claims

- Dense per-point feature maps do not scale well and lack semantic spatial relationships useful for planning.
- ConceptGraphs provides compact, efficient, open-vocabulary, object-centric 3D representation for perception and planning.
- Open-vocabulary semantics can be obtained without collecting large 3D datasets or finetuning 3D models by leveraging 2D foundation models.
- LLM/LVLM-based node captions and edge relationships make the scene graph useful for abstract language queries and downstream task planning.
- The representation supports segmentation, object grounding, navigation, manipulation, localization, and remapping.
- LLM retrieval over scene graph captions is better than CLIP-only retrieval for complex affordance and negation queries.

## Inferences

### 에이전트 추론

P11 is one of the strongest papers for the semantic memory side of `CAND-01`. It gives a concrete object/node/edge representation that can be audited, assigned uncertainty, and used by a planner. It is not a direct active SLAM paper, so it should not be used as evidence that semantic memory already improves localization uncertainty.

For the current thesis direction, ConceptGraphs can support:

- Step 1: object/node uncertainty from caption agreement, view count, CLIP margin, duplicate conflict, and relation consistency.
- Step 2: active re-observation target selection over low-confidence graph nodes.
- Step 3: ObjectNav evaluation through graph-based goal selection and wrong-goal / wasted-path metrics.
- Step 4: semantic memory as an input to active SLAM utility.
- Step 5: semantic accuracy and graph consistency as map-side metrics, while `ATE/RPE` and pose graph connectivity must come from another SLAM source.

## 사용자 판단 필요

- Use ConceptGraphs as full implementation baseline or as semantic memory schema only.
- Decide whether first experiments should run on `Replica`, `AI2Thor`, or Habitat ObjectNav.
- Decide whether to use the stable `main` branch or the real-time `ali-dev` branch for any implementation trial.
- Decide whether the research should depend on proprietary `GPT-4` inference, local `LLaVA`, or a lighter captioning/retrieval alternative.

## Connection to Field Trends

- Strong evidence for open-vocabulary semantic memory / environmental perception intelligence.
- Strong evidence for scene graph as an interface between perception and planning.
- Moderate evidence for real-world robot deploy feasibility because Jackal and Spot demonstrations exist.
- Weak evidence for active SLAM uncertainty because input pose is assumed and localization metrics are not quantified.
- Indirect evidence for active re-observation because the paper exposes graph failure modes but does not actively correct them.

## Possible Contribution Angles

- Add uncertainty fields to ConceptGraphs nodes and edges.
- Turn missed/duplicate/low-confidence nodes into active re-observation candidates.
- Compare CLIP-only retrieval, LLM retrieval, and uncertainty-aware re-observation for ObjectNav wrong-goal visit and wasted path.
- Add a graph correction benchmark: before/after re-observation node precision, duplicate count, relation consistency, and semantic accuracy.
- Fuse ConceptGraphs-style semantic graph with SLAM utility from P02/P09-style pose graph / localization uncertainty.
- Replace proprietary LLM steps with local VLM/embedding confidence when deploy constraints matter.

## What Would Change This Assessment

- If ConceptGraphs can be built reliably on Habitat ObjectNav trajectories, it becomes a strong first-stage backbone for `CAND-01`.
- If graph construction is too brittle or expensive, use only its schema and evaluate with a synthetic/noisy semantic graph.
- If real-world deployment becomes near-term, the `ali-dev` branch and Jackal repository should be tested before committing to this backbone.
- If later papers provide online open-vocabulary scene graph construction with uncertainty and active correction, P11 may become background rather than primary implementation reference.
