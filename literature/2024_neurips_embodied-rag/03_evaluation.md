# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Embodied memory retrieval / generation | `Embodied-Experiences Dataset`, 19 environments | `P(Q|A)`, `P(Q|A,L)`, `SS(A,Ae)` | `Naive-RAG`, `GraphRAG`, `LightRAG` |
| Multimodal memory retrieval | `E-multimodal` with image plus extra sensor data | sensor-conditioned retrieval score, `SS(A,Ae)` | same RAG baselines |
| Memory building scalability | one-kilometer CMU graph, 3,353 nodes | graph construction time, relative speedup | `GraphRAG`, `LightRAG` |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| semantic memory retrieval baseline | query satisfaction, path-weighted retrieval score, memory build time | standard ObjectNav `SR` / `SPL`, map uncertainty, active observation, SLAM metrics |

## Dataset / Benchmark

- Dataset: `Embodied-Experiences Dataset`.
- Environments in arXiv v5: 14 photorealistic simulated AirSim environments, 3 real indoor graphs, 1 real mixed outdoor-indoor graph, and 1 Google Street View graph.
- Total environments: 19.
- Average topological graph size: about 50 nodes.
- Large street-view graph: 3,525 nodes.
- Example large-scale CMU graph for memory-building time: 3,353 nodes in one-kilometer radius.
- Modalities: `E-image` with image-only node observations; `E-multimodal` with image plus additional sensor data such as NDVI.

## Splits

- The paper does not report a standard train/val/test split.
- Queries were created by four human annotators familiar with the dataset images and environmental context.
- The arXiv abstract reports over 250 explanation/navigation queries; OpenReview reports over 200 queries. The local arXiv v5 PDF should be treated as the current source.

## Metrics

- Find query score: `P(Q|A)`, estimated by cross-voting among five VLMs for whether the answer/image path satisfies the query.
- Location-aware Find score: `P(Q|A,L)`, path-length weighted variant inspired by `SPL`.
- Sensor-conditioned setting: `P(Q|A,L,S)` is used conceptually when extra sensor data is available; Table III labels the sensor rows under the location-aware metric.
- Explain query score: `SS(A,Ae)`, semantic similarity between generated answer and expert-provided answer.
- Efficiency: relative graph memory building time against `GraphRAG` and `LightRAG`.
- Ablation metric: top-1/top-5 `P(Q|A)`, normalized inverse path length, and path-weighted score on semantic forest memory.

## Baselines

- `Naive-RAG`: graph files converted into flat text chunks, GPT-4o context retrieval.
- `GraphRAG`: entity/relation extraction and community reports over text chunks.
- `LightRAG`: dual-level key retrieval over a graph RAG structure.
- Ablation: same semantic forest memory queried by modified baseline retrieval methods.

## Main Results

- E-image explicit `P(Q|A)`: `Embodied-RAG` 0.55 vs `Naive-RAG` 0.08, `GraphRAG` 0.06, `LightRAG` 0.08.
- E-image implicit `P(Q|A)`: `Embodied-RAG` 0.62 vs 0.10, 0.12, 0.13.
- E-image global `SS(A,Ae)`: `Embodied-RAG` 0.67, close to `GraphRAG` 0.68 and above `Naive-RAG` 0.31 / `LightRAG` 0.65.
- E-multimodal explicit sensor-conditioned score: `Embodied-RAG` 0.36 vs baselines 0.04, 0.04, 0.03.
- E-multimodal implicit sensor-conditioned score: `Embodied-RAG` 0.41 vs baselines 0.04, 0.04, 0.08.
- E-multimodal global `SS(A,Ae)` with sensor input: `Embodied-RAG` 0.95 vs baselines 0.46, 0.68, 0.78.
- Graph memory building: `Embodied-RAG` is reported as 7.38x faster than `GraphRAG` and 9.76x faster than `LightRAG`.
- One-kilometer CMU graph: semantic forest construction takes about 4 minutes 35 seconds for 3,353 nodes.

## Reproducibility Notes

- Local PDF is available as `paper.pdf` and is arXiv v5.
- Code repository is public: https://github.com/quanting-xie/Embodied_RAG
- Repository requirements include Python >= 3.9, AirSim, and OpenAI API key.
- Repository includes offline tele-operation collection, offline all-object collection, online semantic forest collection, semantic forest building, visualization, and retrieval scripts.
- The project is implementable as a memory/retrieval harness, but reproducing all environments and annotations may require additional data access and manual query labels.

## Evaluation Weaknesses

- No standard `ObjectNav` `Success` / `SPL` benchmark is used; `P(Q|A,L)` is only inspired by path efficiency.
- No SLAM quality metric such as `ATE`, `RPE`, map error, or pose graph connectivity is reported.
- Query labels and expert answers depend on human annotation, and cross-VLM scoring may introduce evaluator-model bias.
- The benchmark tests memory retrieval and generation more than active perception or active SLAM.
- Dynamic objects, stale observations, obstacle avoidance, and local planner failure are left as future work.
