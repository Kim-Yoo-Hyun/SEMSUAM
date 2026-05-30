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

- H001은 umbrella hypothesis draft이며 candidate-specific active re-observation evidence gate를 진행 중이다.
- 현재 branch는 `rival_identity:12`와 `rival_identity:14`의 recovered candidates에 대해 full candidate-specific detector/SAM2 substrate, objective analyzer, ambiguity diagnostic, and discriminative instance/goal-region analyzer를 통과했다.
- Full substrate observes `158/158` candidate rows and recovers `6` evaluation-only correct candidates, but `candidate_specific_support` saturates at `146/158`, so terminal commit remains blocked.
- Discriminative target pairs are not consistently separable by action-time visual evidence (`contrast_visual_higher 8`, `selector_visual_higher 10`). The relation/spatial context analyzer is Docker-verified but still not a terminal separator because `12/18` target pairs are same-component cases. The scene-graph/object-relation analyzer is Docker-verified and its target-pair relation separability probe is positive (`contrast_relation_higher 18/18`), but detector coverage is incomplete (`77/79` candidates per request). The object-relation coverage repair analyzer is Docker-verified: `4` coverage gaps, `2` object-relation observation requests, `2` terminal-policy-promotion waivers, action forbidden keys `0`, terminal commits `0`, and `coverage_repair_gate_passed true`. The object-relation observation planner, frame/projection smoke, and detector substrate are Docker-verified: plan rows `8`, frame rows/headings `8/72`, projection visible rows `8/8`, detector rows `8`, detector box/SAM2/candidate association `1.0/1.0/1.0`, associated heading count `48`, terminal commits `0`, and `paper_claim_allowed false`; the next gate is post-detector evidence analyzer contract.
- map quality metric과 task behavior metric을 동시에 만족해야 experiment-ready로 승격한다.
- Step 4-5 확장을 위해 SLAM uncertainty proxy와 ATE/RPE 또는 pose graph connectivity 측정 가능성을 확인해야 한다.
