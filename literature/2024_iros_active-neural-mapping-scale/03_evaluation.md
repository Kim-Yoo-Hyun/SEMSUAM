# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Small / medium active mapping | Habitat with Gibson 9 scenes and MP3D 4 scenes | `Completion Ratio`, `Completion`, runtime/system rate | `Random`, `FBE`, `UPEN`, `ANM` |
| Large-scale active mapping | largest MP3D scenes with over 20 rooms | `Completion Ratio`, qualitative completeness curves | mainly method variants / reported large-scene runs |
| Topology/anchoring ablation | `Gibson-Cantwell`, 2000 steps | completeness | random Voronoi vertex, best anchored vertex, full method |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4 map coverage / scalability | `Completion Ratio`, `Completion`, runtime | ObjectNav `SR` / `SPL`, semantic accuracy, `ATE/RPE`, pose graph connectivity |

## Dataset / Benchmark

### 사실

- Simulator: Habitat.
- Datasets: Gibson and Matterport3D / MP3D.
- Hardware: Intel Core i9-10850K, 64 GB RAM, NVIDIA GeForce RTX 3090.
- Observation: posed RGB-D sequence.
- Resolution: 256 x 256.
- Action space: `MOVE_FORWARD` by 6.5 cm, `TURN_LEFT` / `TURN_RIGHT` by 10 degrees, `STOP`.
- Camera height: 1.25 m above the floor.
- Camera field of view: 90 degrees vertical and horizontal.
- System rate: 7-9 Hz average, according to paper.

## Splits

### Small / Medium Scene Evaluation

- 13 diverse scenes are used following `Active Neural Mapping`.
- Gibson scenes: `Cantwell`, `Denmark`, `Eastville`, `Elmira`, `Eudora`, `Greigsville`, `Pablo`, `Ribera`, `Swormville`.
- MP3D scenes: `GdvgF`, `gZ6f7`, `pLe4w`, `YmJkq`.

### Large-scale Scene Evaluation

- Largest three scenes in MP3D test/val splits.
- Each scene has over 20 rooms.
- The paper reports examples `MP3D-Z6MFQ`, `MP3D-q9vSo`, and `MP3D-zsNo4`.
- Large-scale scenes are reconstructed in at most 10,000 steps.

## Metrics

- `Completion Ratio` (%): percentage of points whose nearest distance is within 5 cm.
- `Completion` (cm): nearest-distance-based completion distance.
- Runtime / system rate: average Hz.
- Qualitative mesh reconstruction and completeness curves.

### Not Central in This Paper

- No ObjectNav `Success Rate` / `SPL`.
- No wrong-goal visit or wasted path.
- No `ATE/RPE`.
- No pose graph connectivity.
- No semantic accuracy / object precision / recall.

## Baselines

- `Random`
- `FBE`
- `UPEN`
- `ANM`

## Main Results

### Table I: Gibson Mean

| Method | Completion Ratio | Completion |
| --- | ---: | ---: |
| `Random` | 45.80 | 34.48 |
| `FBE` | 68.30 | 14.42 |
| `UPEN` | 63.30 | 21.09 |
| `ANM` | 80.45 | 7.44 |
| Ours | 92.10 | 2.83 |

### Table I: MP3D Mean

| Method | Completion Ratio | Completion |
| --- | ---: | ---: |
| `Random` | 45.36 | 28.39 |
| `FBE` | 74.30 | 9.29 |
| `UPEN` | 75.56 | 9.72 |
| `ANM` | 79.36 | 7.40 |
| Ours | 89.74 | 4.14 |

### Large-scale MP3D Results

- `MP3D-Z6MFQ`: 22 rooms, 90.97% completeness.
- `MP3D-q9vSo`: 22 rooms, 92.93% completeness.
- `MP3D-zsNo4`: 23 rooms shown in Fig. 1; exact numeric completeness is not in the text snippet.
- Paper states large scenes with over 20 rooms reach over 90% completeness in at most 10,000 steps.

### Ablations

- On `Gibson-Cantwell` in 2000 steps:
  - Random Voronoi vertex: 64.78% completeness.
  - Best anchored vertex: 73.93% completeness.
  - Full method: 91.46% completeness.
- Visibility guidance improves local geometric / appearance details compared with accessibility-only exploration.
- Bootstrap rotation uses 36 steps and improves early coverage in many scenes.

### 논문 주장

- The method consistently outperforms `FBE`, `UPEN`, and `ANM` on Gibson and MP3D mean completion.
- Topology plus uncertainty anchoring improves both exploration completeness and reconstruction quality.
- Hierarchical local/global granularity supports large-scale exploration efficiency.

## Reproducibility Notes

- arXiv PDF is accessible.
- DBLP confirms IROS 2024 publication metadata.
- No official code or project page was found on 2026-05-07.
- Reimplementation dependencies inferred from paper: Habitat, Gibson, MP3D, Co-SLAM-style hybrid neural map, GVG extraction, Dijkstra graph search.
- Exact scene split is partially inferable from Table I and figures, but full config files are not available in this repo.

## Evaluation Weaknesses

- No public code, so direct reproduction risk is high.
- Evaluation centers on reconstruction completion, not navigation task behavior.
- Semantic / language-guided navigation is not evaluated.
- Localization is not evaluated as `ATE/RPE`.
- Pose graph connectivity is not measured, although navigational topology is central.
- Real-world deployment is not shown.
