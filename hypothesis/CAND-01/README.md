# CAND-01

## Candidate Summary

### 사실

Source candidate는 `literature/CAND-01.md`의 `Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`이다.

### 에이전트 추론

현재 H001은 Step 1-5 전체를 포함하는 umbrella hypothesis다. 중심 주장은 semantic uncertainty가 active SLAM/navigation utility로 작동한다는 것이며, Step 1-3은 ObjectNav first probe, Step 4-5는 같은 H001 안에서 SLAM/map-side extension으로 진행한다.

## Source Literature

- `CARe`
- `VLMaps`
- `ConceptGraphs`
- `DualMap`
- `Open-Vocabulary Online Semantic Mapping for SLAM`
- `Semantic Environment Atlas`
- `SG-Nav`
- `3D Active Metric-Semantic SLAM`
- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`

## Hypothesis Queue

| ID | Short title | Status | Scope |
| --- | --- | --- | --- |
| H001 | uncertainty-reobservation | Draft | Step 1-5: semantic uncertainty as utility, active re-observation, ObjectNav behavior, SLAM/map consistency |

## Current Gate

- H001은 umbrella hypothesis draft이며 first probe 설계 단계다.
- `CARe`, `VLMaps`, Habitat ObjectNav 접근 가능성을 먼저 확인해야 한다.
- map quality metric과 task behavior metric을 동시에 만족해야 experiment-ready로 승격한다.
- Step 4-5 확장을 위해 SLAM uncertainty proxy와 ATE/RPE 또는 pose graph connectivity 측정 가능성을 확인해야 한다.
