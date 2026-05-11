# Evaluation

## Dataset / Benchmark

### 사실

| Benchmark | Evaluation split / episodes | Goal categories | Notes |
| --- | --- | --- | --- |
| MP3D ObjectNav | 11 validation scenes, 2195 episodes | 21 | Habitat-style indoor ObjectNav evaluation |
| HM3D Habitat 2022 ObjectNav | 20 validation environments, 2000 validation episodes | 6 | Habitat 2022 ObjectNav setting |
| RoboTHOR ObjectNav | 15 validation environments, 1800 validation episodes | 12 | RoboTHOR 2020/2021 ObjectNav setting |

### 에이전트 추론

| CAND-01 step | Directly useful part | Missing part |
| --- | --- | --- |
| Step 1 object/node uncertainty | goal credibility, multi-view object confirmation | calibrated uncertainty metric over all graph nodes |
| Step 2 active re-observation viewpoint | graph-based re-perception loop | explicit NBV / information gain policy |
| Step 3 ObjectNav behavior evaluation | `SR`, `SPL`, `SoftSPL`, false-positive handling | `wrong-goal visit`, `wasted path` custom logging |
| Step 4-5 semantic memory to active SLAM | online scene graph memory | `ATE`, `RPE`, map error, pose graph connectivity |

## Splits

- MP3D: validation set, 11 scenes, 2195 episodes.
- HM3D: Habitat 2022 ObjectNav validation, 20 environments, 2000 episodes.
- RoboTHOR: validation, 15 environments, 1800 episodes.
- Common simulator setting: maximum 500 navigation steps, 0.25 m forward step, 30 degree turn, RGB-D 640 x 480, camera height 0.90 m.

## Metrics

- `SR`: success rate.
- `SPL`: Success weighted by Path Length.
- `SoftSPL`: soft success weighted by path length / navigation progress.
- Ablation metrics: `SR`, `SPL`, `SoftSPL` for components and graph variants.

## Baselines

- Supervised references: `SemEXP`, `PONI`, `ProcTHOR`.
- Unsupervised / zero-shot references: `ZSON`, `ProcTHOR-ZS`, `CoW`, `ESC`, `L3MVN`, `OpenFMNav`, `VLFM`.
- Internal ablations: `w/o SG&RP`, `w/o RP`, room/group node variants, edge variants, CoT prompt variants.

## Main Results

### 논문 주장

- Full `SG-Nav` improves over a frontier / prompt baseline without scene graph and re-perception.
- Scene graph contributes a larger gain than room/group refinements alone, and re-perception further improves `SR`.

### Key reported numbers

| Method | MP3D `SR` / `SPL` | HM3D `SR` / `SPL` | RoboTHOR `SR` / `SPL` |
| --- | --- | --- | --- |
| `VLFM` | 36.2 / 15.9 | 52.4 / 30.3 | 42.3 / 23.0 |
| `OpenFMNav` | 37.2 / 15.7 | 52.5 / 24.1 | 44.1 / 23.3 |
| `SG-Nav-LLaMA` | 40.1 / 16.0 | 53.9 / 24.8 | 47.3 / 23.7 |
| `SG-Nav-GPT` | 40.2 / 16.0 | 54.0 / 24.9 | 47.5 / 24.0 |

| Ablation | MP3D `SR` / `SPL` / `SoftSPL` | HM3D `SR` / `SPL` / `SoftSPL` | RoboTHOR `SR` / `SPL` |
| --- | --- | --- | --- |
| `w/o SG&RP` | 25.7 / 12.9 / 22.6 | 38.6 / 18.9 / 27.7 | 34.9 / 21.1 |
| `w/o RP` | 36.5 / 15.0 / 23.9 | 49.6 / 23.6 / 33.0 | 41.9 / 22.6 |
| `SG-Nav` | 40.1 / 16.0 / 24.9 | 53.9 / 24.8 / 33.8 | 47.3 / 23.7 |

| MP3D graph component | `SR` / `SPL` / `SoftSPL` |
| --- | --- |
| no room / no group | 38.3 / 15.3 / 23.9 |
| room only | 39.0 / 15.8 / 24.4 |
| group only | 39.4 / 15.8 / 24.6 |
| room + group | 40.1 / 16.0 / 24.9 |

## Reproducibility Notes

- Official NeurIPS PDF and project page are available.
- Code is available at https://github.com/bagh2178/SG-Nav.
- The full pipeline depends on simulator setup, object detection / segmentation, VLM, LLM, graph construction, and local navigation policy.
- For CAND-01, a smaller reproduction should first log graph node confidence, re-perception count, false goal approach, and path overhead on a subset of ObjectNav episodes.

## Evaluation Weaknesses

- `SR` / `SPL` do not reveal whether improvement comes from better semantic map quality, LLM reasoning, perception correction, or exploration bias.
- Re-perception can increase success while still increasing wasted path; the paper does not directly report `wrong-goal visit` or re-observation path cost as primary metrics.
- SLAM-side metrics such as `ATE`, `RPE`, map error, and pose graph connectivity are absent.
- Graph construction quality is evaluated indirectly through ObjectNav, not through standalone semantic map uncertainty / calibration.
