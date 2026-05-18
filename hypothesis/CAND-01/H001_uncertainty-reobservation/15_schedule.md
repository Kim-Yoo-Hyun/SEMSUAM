# Schedule

## Purpose

H001을 6개월-1년 범위에서 first probe, Step 4-5 SLAM extension, real-world validation으로 순차 확장하는 연구 일정을 정의한다.

이 문서는 논문 제목이나 최종 claim을 확정하지 않는다. 각 단계가 다음 단계로 넘어가기 위한 evidence gate를 정한다.

## Facts

- Date checked: 2026-05-08
- Active hypothesis: H001 `Semantic-SLAM Uncertainty Re-observation`
- Primary benchmark path: Habitat ObjectNav with HM3D, then HM3D-OVON extension.
- Available runtime gates: HM3D / HM3D-OVON Docker mount, `habitat-h001` smoke, logging schema, non-GT candidate adapter, `VLMaps` artifact exporter, synthetic alignment adapter.
- Current paper-facing blocker: real HM3D `VLMaps` map artifact must provide `alignment.json` generated from the same Habitat pre-exploration trajectory.
- First-probe gate: `07_evaluation_contract.md`.
- Real-world setup gate: `03_feasibility.md`.
- Long-running I/O-heavy jobs must follow `AGENTS.md` background-task policy.

## Paper Claims

- ObjectNav papers commonly report `Success Rate` and `SPL`.
- Semantic navigation and semantic memory papers motivate candidate confidence, re-observation, and wrong-goal failure analysis.
- Active SLAM papers motivate viewpoint utility terms that improve pose graph, localization, and map consistency.

## Inferences

The top-tier path should not start with real-world deployment. The strongest sequence is:

1. make the simulator evidence reproducible and non-GT,
2. show semantic uncertainty predicts and reduces wrong-goal commitment,
3. add SLAM-side utility only after Step 1-3 is positive,
4. use real-world validation as a later repeatability and deployment check.

## Top-Tier Alignment Check

### Facts

- Date checked: 2026-05-08
- The current H001 direction targets adaptive AI robotics through environmental perception intelligence, semantic memory, SLAM uncertainty, and navigation utility.
- Current planned benchmark path is `HM3D ObjectNav` first, `HM3D-OVON` second, and real-world validation only after simulator evidence is stable.
- Current primary metrics include `Success Rate`, `SPL`, `wrong_goal_visit`, `wasted_path`, candidate coverage, semantic uncertainty calibration, pose graph connectivity, map error, semantic accuracy, and `ATE/RPE` when trajectory GT is available.

### Paper Claims

- Recent open-vocabulary navigation and semantic memory papers motivate using environment-specific semantic memory, but they often leave semantic uncertainty, wrong-goal commitment, and map/pose-side utility weakly connected.
- Recent active semantic mapping and active SLAM papers motivate information-gain-driven viewpoint selection, but task-level navigation failure metrics are not always tied to semantic uncertainty.
- Recent `HM3D-OVON` and open-vocabulary embodied navigation work makes semantic ambiguity and unseen-object generalization more important than closed-class ObjectNav alone.

### Inferences

The current direction is aligned with recent AI, ML, CV, and Robotics top-tier trends if it is framed as semantic uncertainty becoming an active SLAM/navigation utility, not simply as adding `VLMaps` to ObjectNav.

The dataset path is appropriate:

| Dataset / benchmark | Role | Reason |
| --- | --- | --- |
| `HM3D ObjectNav` | primary first probe | stable Habitat benchmark with standard `Success Rate` and `SPL`; useful for controlled wrong-goal and wasted-path analysis |
| `HM3D-OVON` | top-tier robustness extension | tests open-vocabulary ambiguity, seen/unseen categories, and semantic generalization |
| `MP3D` | optional compatibility check | useful for comparison with older embodied navigation work, but weaker as the main novelty benchmark |
| `Replica` / `ScanNet` / `OpenLex3D` | optional semantic representation probes | useful for semantic map quality or retrieval sanity, not the main active navigation benchmark |
| real-world robot logs | late validation | strengthens robotics/journal credibility only if external GT or calibrated event-level proxy exists |

The baseline path must be stronger than simple ablation:

| Baseline | Required role |
| --- | --- |
| `NoReobserve` | shows the wrong-goal failure mode exists |
| `RandomReobserve` | separates active selection from extra observation budget |
| `FrontierReobserve` | separates semantic uncertainty from geometry-only exploration |
| `CARe`-style confidence replanning | anchors comparison to recent confidence-aware navigation |
| `VLMaps` direct / semantic memory direct | shows gain is not from semantic memory alone |
| GT oracle references | diagnose candidate coverage and upper-bound policy/action failure, not a deployable baseline |
| `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` | required for Step 4-5 to prove semantic and SLAM utility are complementary |

### Novelty Risk

The main risk is that H001 can look like a combination of `VLMaps`, confidence replanning, and active SLAM if the evidence only reports `Success Rate` and `SPL`.

To make the contribution paper-facing, the schedule must preserve three evidence lines:

- semantic uncertainty predicts wrong-goal commitment before intervention;
- active re-observation reduces wrong-goal visit and wasted path against budget-aware baselines;
- adding SLAM uncertainty improves map/pose-side metrics over `SemanticOnly` without the effect being fully explained by `SLAMOnly`.

## Phase Plan

| Phase | Target time | Main question | Exit gate |
| --- | ---: | --- | --- |
| P0 | Week 0-2 | Can H001 produce aligned non-GT candidates in real HM3D scenes? | real HM3D `VLMaps` artifact has verified `alignment.json` and navigable candidates |
| P1 | Month 1-2 | Does `U_sem` predict wrong-goal candidate failure? | candidate coverage and `U_sem` validity pass on calibration split |
| P2 | Month 2-3 | Does active re-observation reduce wrong-goal visit and wasted path? | `SemanticOnly` passes first-probe gate against `NoReobserve` and `RandomReobserve` |
| P3 | Month 3-4 | Is the signal robust to stronger baselines and OVON ambiguity? | `CARe`-style / `FrontierReobserve` and HM3D-OVON checks do not remove the signal |
| P4 | Month 4-6 | Can semantic memory become active SLAM utility? | `SemanticSLAM` improves map/pose-side proxy over `SemanticOnly` and `SLAMOnly` |
| P5 | Month 6-9 | Is the result paper-facing? | fixed splits, ablations, error taxonomy, reproducible Docker commands, draft figure/table set |
| P6 | Month 9-12 | Does the idea survive small real-world validation? | ROS 2 bag / robot trial logs reproduce the failure decomposition with external GT or calibrated proxy |

## P0: Alignment and Split Freeze

### Goal

Turn the current synthetic alignment smoke into real HM3D scene-specific non-GT semantic artifacts.

### Required Work

- Decide HM3D scene subset and fixed episode ids for smoke, calibration, and first evaluation.
- Generate real HM3D `VLMaps` map artifacts from a controlled Habitat pre-exploration trajectory.
- Generate `alignment.json` from the same trajectory export metadata, not from GT object labels.
- Verify aligned candidate positions with Habitat navmesh.
- Record long-running map generation commands, logs, output paths, expected files, and verification commands.

### Exit Gate

- At least one HM3D scene has `artifact_jsonl` with `coordinate_frame = habitat_world`.
- Candidate visit positions are navigable or explicitly marked unreachable.
- `uses_gt_for_action = false` is preserved.
- Split file and episode ids are fixed before tuning `theta_uncertain` or utility weights.

### Failure Action

If real HM3D `VLMaps` alignment fails, do not run full ObjectNav metrics yet. Fix map construction metadata recovery first, or use a lightweight semantic proxy only for debugging.

## P1: Semantic Uncertainty Calibration

### Goal

Check whether object/node uncertainty is a valid failure predictor before implementing more policy complexity.

### Required Work

- Run 30-50 calibration episodes across at least 5 scenes.
- Compute `score_uncertainty`, `margin_uncertainty`, support features, and aggregate `U_sem`.
- Label candidate correctness only after non-GT candidate selection.
- Measure candidate coverage, reachable correct candidate rate, reachable distractor rate, wrong-goal prior rate, `AUROC`, `AUPRC`, Spearman, and high/low bucket gap.

### Exit Gate

- Candidate correctness labels are usable for at least 70 percent of evaluated episodes.
- At least 50 percent of episodes include both a reachable correct candidate and a reachable distractor candidate.
- `NoReobserve` wrong-goal visit rate is at least 10 percent on the selected subset.
- `U_sem` passes the validity gate in `07_evaluation_contract.md`.

### Failure Action

If `U_sem` fails, revise uncertainty features or candidate backend. Do not move to Step 4-5.

## P2: First Probe

### Goal

Test whether semantic uncertainty-driven active re-observation improves ObjectNav behavior without excessive travel cost.

### Required Work

- Implement `SemanticOnly` viewpoint selection.
- Compare the same episode ids under `NoReobserve`, `RandomReobserve`, `SemanticOnly`, and GT oracle references.
- Use commit-based `wrong_goal_visit`.
- Log `wrong_goal_visit_rate`, `mean_wasted_path_wrong_goal`, `mean_wasted_path_total`, `SPL`, `Success Rate`, and re-observation count.

### Exit Gate

- `SemanticOnly` passes the primary numeric gate against `NoReobserve`.
- `SemanticOnly` passes the random baseline sanity gate.
- GT oracle gap separates candidate-set coverage from policy failure.

### Failure Action

If wrong-goal improves but `SPL` drops too much, revise travel-cost arbitration. If `RandomReobserve` matches `SemanticOnly`, revise viewpoint objective before claiming contribution.

## P3: Robustness and Open-Vocabulary Extension

### Goal

Check whether the Step 1-3 signal survives stronger baselines and open-vocabulary ambiguity.

### Required Work

- Add or approximate `CARe`-style confidence replanning.
- Add `FrontierReobserve` or geometry-only reachable viewpoint baseline if implementation cost is acceptable.
- Run HM3D-OVON validation splits with fixed synonym handling.
- Run feature ablations for `score_uncertainty`, `margin_uncertainty`, support, travel cost, and visibility.

### Exit Gate

- Main signal keeps the same sign against stronger non-GT baselines.
- HM3D-OVON `val_seen` and `val_unseen` do not reverse the result direction.
- Failure taxonomy identifies whether errors are candidate coverage, uncertainty calibration, viewpoint selection, or navigation execution.

### Failure Action

If OVON fails while closed-class ObjectNav passes, keep the first claim closed-class and mark open-vocabulary robustness as future work or separate extension.

## P4: Step 4-5 SLAM Extension

### Goal

Extend semantic re-observation into active SLAM/navigation utility and evaluate map/pose consistency.

### Entry Gate

Do not enter P4 until the Step 4-5 promotion gate in `07_evaluation_contract.md` is satisfied. The default first entry is `P4-proxy`, using pose graph connectivity before adding a live SLAM backend.

### Required Work

- Build or use a separate SLAM evaluation image.
- Start with pose graph connectivity proxy as the first SLAM-side metric.
- Implement `SLAMOnly` and `SemanticSLAM` utility:

```text
U(v) = alpha * SemanticGain(v)
     + beta  * SLAMGain(v)
     - gamma * TravelCost(v)
     - eta   * Risk(v)
```

- Evaluate `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` on the same episodes.
- Add map error, semantic accuracy, localization failure count, pose graph connectivity, and `ATE/RPE` when trajectory GT is available.

### Exit Gate

- `SemanticSLAM` improves at least one map/pose-side metric over `SemanticOnly`.
- `SemanticSLAM` improves task behavior or keeps task behavior within the P2 acceptable cost bounds.
- `SLAMOnly` does not fully explain the improvement.
- Failure cases are logged separately: semantic candidate failure, unreachable viewpoint, localization failure, map update failure, and excessive travel cost.

### Failure Action

If `SemanticSLAM` only improves map/pose metrics by taking much longer paths, revise travel-cost normalization. If it does not improve over `SemanticOnly`, keep the paper centered on semantic re-observation and report SLAM extension as negative result.

## P5: Paper-Facing Consolidation

### Goal

Convert validated experiments into stable evidence for a thesis and possible AI, ML, CV, or Robotics top-tier submission.

### Required Work

- Freeze evaluation split and code state.
- Run final repeated evaluation with saved configs and Docker commands.
- Prepare ablation tables, failure taxonomy, qualitative route examples, and oracle gap analysis.
- Verify all claims trace back to logs, configs, datasets, and commands.
- Decide target venue style and paper outline only after result quality is visible.

### Exit Gate

- Main tables are reproducible from logged commands.
- Limitations are separated from claims.
- Negative results are recorded instead of hidden.
- Thesis-level narrative is stable even if top-tier submission needs more experiments.

## P6: Real-World Validation

### Goal

Test whether the same failure decomposition appears outside simulation.

### Required Work

- Confirm available robot base, RGB-D / stereo sensor, LiDAR, and GT setup.
- Use ROS 2 with `Nav2` if a mobile base is available.
- Use motion capture if available; otherwise use a calibrated `AprilTag` map for small-area event-level validation.
- Record ROS bag topics for `/tf`, `/odom`, `/cmd_vel`, `/scan`, RGB-D streams, semantic candidates, selected viewpoints, stop/commit events, and GT pose.
- Compare at least `NoReobserve`, `SemanticOnly`, and one SLAM/map-side variant if the hardware supports it.

### Exit Gate

- Logs reproduce the same event definitions as Habitat.
- Stop/commit-based `wrong_goal_visit` and wasted path are measurable.
- External GT or calibrated proxy supports `ATE/RPE` or event-level pose correctness.

### Failure Action

If GT is weak, present real-world results as qualitative or diagnostic only. Do not use wheel odometry alone as paper-facing `ATE/RPE` evidence.

## Decision Points

| Decision | Latest point | Default |
| --- | --- | --- |
| First paper includes real-world POC? | after P4 | simulation-first, real-world if GT is available |
| HM3D-OVON is core or extension? | after P2 | extension unless closed-class result is weak |
| Full `VLMaps` runtime needed? | during P0 | only if real HM3D map generation requires it |
| Live SLAM backend needed? | during P4 | start with pose graph proxy, add live backend only if necessary |
| Target venue paper or thesis-first? | after P5 | thesis-first evidence, top-tier submission if P2-P4 signal is strong |

## Immediate Next Task

Complete `random256_k10_v1` candidate-budget recovery verification and apply the coverage decision tree in `04_first_experiment.md`.

If the coverage gate passes, run the predeclared calibration policy comparison and interpret it with `07_evaluation_contract.md`. If it fails, write a second recovery decision note before changing scenes, candidate extraction, queries, or trajectories.
