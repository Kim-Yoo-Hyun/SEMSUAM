# Evaluation Contract

## Purpose

Define the top-tier evaluation contract for H001 before implementation.

The goal is to test whether semantic uncertainty can function as active SLAM/navigation utility, not only whether an ObjectNav agent obtains a higher final score.

## Facts

- HM3D ObjectNav v2 is available locally through Docker.
- HM3D-OVON is available locally through Docker.
- H001 already defines semantic candidate uncertainty features in `05_uncertainty_features.md`.
- H001 already defines navigation failure logging in `06_logging_schema.md`.
- Primary implementation and smoke tests must run in Docker.

## Paper Claims

- ObjectNav benchmarks commonly report `Success Rate`, `SPL`, and distance-style task metrics.
- Open-vocabulary ObjectNav benchmarks evaluate language-conditioned target search with broader query ambiguity.
- Semantic-map navigation papers motivate confidence, re-perception, and semantic memory quality as causes of navigation behavior changes.

## Inferences

A top-tier paper needs evidence at three levels:

- task outcome: `Success Rate`, `SPL`, distance to success
- failure mechanism: wrong-goal commit, wasted path, re-observation cost
- uncertainty validity: uncertainty score predicts semantic decision failure

If H001 improves only `SPL` without reducing semantic failure, the contribution may look like path planning. If H001 reduces wrong-goal commits but destroys `SPL`, the method may be semantically useful but not a good navigation policy.

## Primary Claim

Semantic uncertainty from a pre-explored semantic map can be converted into an active navigation utility that reduces wrong semantic goal commitment and wasted path in ObjectNav, and can later be extended with SLAM uncertainty to improve map/pose consistency.

## Primary Benchmarks

| Benchmark | Role | Why it matters |
| --- | --- | --- |
| HM3D ObjectNav v2 | first controlled benchmark | closed-class ObjectNav with accessible HM3D assets and episodes |
| HM3D-OVON | open-vocabulary extension | stronger semantic ambiguity and query uncertainty |

## Secondary Benchmarks

| Benchmark | Role | Use condition |
| --- | --- | --- |
| Replica one-scene replay | debugging / visual sanity | use if HM3D runtime integration is slow |
| ScanNet or ScanNet++ replay | map/pose-side probe | use for Step 4-5 SLAM/map quality extension |
| Real-world lab scene | robotics credibility | use after simulator evidence is stable |

## Split Discipline

Use calibration splits only for thresholds and fixed weights.

| Data | Calibration | Evaluation |
| --- | --- | --- |
| HM3D ObjectNav v2 | small train subset or minival | held-out val subset |
| HM3D-OVON | train subset | `val_seen`, `val_unseen`, `val_seen_synonyms` |

Do not tune `theta_uncertain`, feature weights, or travel-cost weights on final evaluation splits.

## Fixed Split Plan

### 사실

- Fixed manifest: `manifests/h001_splits_v1.json`
- Verification summary: `manifests/h001_splits_v1.verify.json`
- Runtime module: `runtime/h001_runtime/split_manifest.py`
- Calibration split: 50 rows across 5 scenes
- First evaluation target: at least 100 rows across 10 scenes

### 에이전트 추론

Episode identity should include dataset, split, source file, row index, source episode id, scene id, and target/query. Do not tune `semantic_uncertainty_trigger`, tie band, feature weights, scene replacement, or candidate backend after seeing held-out first-evaluation results.

## Primary Metrics

Report these for every non-oracle policy:

- `Success Rate`
- `SPL`
- `DTS` or distance to success if available
- `wrong_goal_visit_rate`
- `mean_wasted_path_total`
- `mean_wasted_path_wrong_goal`
- `mean_wasted_path_reobserve`
- `mean_num_reobservations`
- `mean_travel_cost_to_reobserve`

## Uncertainty Metrics

Report when candidate labels are available:

- uncertainty vs wrong-goal `AUROC`
- uncertainty vs wrong-goal `AUPRC`
- Spearman correlation between `U_sem` and candidate failure
- calibration bins: `U_sem` bucket vs wrong-goal probability

## SLAM / Map Extension Metrics

Use these after Step 1-3 is stable:

- semantic map accuracy or object precision / recall
- map consistency before/after re-observation
- pose graph connectivity
- ATE/RPE if trajectory ground truth is available
- localization failure count

## Primary Baselines

| Baseline | Uses semantic map? | Uses re-observation? | Uses GT? | Role |
| --- | --- | --- | --- | --- |
| `NoReobserve` | yes | no | no | direct commit baseline |
| `RandomReobserve` | yes | yes | no | tests whether any extra view helps |
| `FrontierReobserve` | partial | yes | no | geometry / exploration baseline |
| `CAReStyle` | yes | replan/confidence only | no | semantic confidence baseline |
| `SemanticOnly` | yes | yes | no | proposed semantic utility without SLAM |
| `SLAMOnly` | no or limited | yes | no | later Step 4-5 geometry/SLAM utility |
| `SemanticSLAM` | yes | yes | no | final H001 policy |

## Ground-truth References

GT policies are not deployable baselines. They are upper bounds and diagnostic controls.

| Reference | Role |
| --- | --- |
| `GTTargetOracle` | shortest path to valid target; path-efficiency upper bound |
| `GTCandidateOracle` | chooses correct semantic candidate if candidate set contains one |
| `GTViewOracle` | chooses best re-observation viewpoint using target/candidate correctness |

Use GT for candidate correctness labels, shortest-path reference, and oracle upper bounds. Do not tune proposed policy with GT on evaluation splits.

## Ablations

Feature ablations:

- `score_uncertainty` only
- `margin_uncertainty` only
- support feature only
- `score + margin`
- `score + margin + support`

Policy ablations:

- no travel-cost penalty
- fixed `theta_uncertain`
- percentile-based `theta_uncertain`
- re-observe top-1 only
- re-observe top-k ambiguous candidates

Step 4-5 ablations:

- semantic-only utility
- SLAM-only utility
- semantic + SLAM utility
- no pose graph connectivity term

## Wrong-goal Metric Decision

Primary wrong-goal metric is commit-based.

Count `wrong_goal_visit = true` only when:

- the policy explicitly commits to a semantic candidate as goal
- the candidate is not a valid target by GT label or accepted synonym group
- the agent reaches the candidate neighborhood or executes stop/commit
- traveled distance exceeds `wrong_goal_min_path`

Near-candidate pass-through is logged as `wrong_goal_pass_through` and reported only as diagnostic.

## Statistical Reporting

For each benchmark and split:

- report mean over episodes
- report 95 percent bootstrap confidence intervals
- report paired deltas against `NoReobserve` and strongest non-GT baseline on the same episodes
- report per-scene aggregate when enough scenes exist
- separate HM3D-OVON `val_seen`, `val_unseen`, and `val_seen_synonyms`

## Success Criteria

H001 first probe is promising if:

- `wrong_goal_visit_rate` decreases against `NoReobserve`
- `mean_wasted_path_wrong_goal` decreases against `NoReobserve`
- `SPL` does not drop beyond the accepted re-observation cost threshold
- `U_sem` has measurable relation with candidate failure
- `SemanticOnly` beats `RandomReobserve` on failure decomposition, not only path length

## First-Probe Hard Validity Gate

The first probe is invalid unless:

- all compared policies run on the exact same episode ids;
- non-GT policies do not use GT labels, target ids, or shortest paths for action selection;
- GT is used only for candidate correctness labels, shortest-path references, and oracle upper bounds;
- `wrong_goal_visit` is commit-based;
- `wrong_goal_pass_through` is diagnostic only;
- every episode has a logged termination reason;
- at least 70 percent of evaluated episodes have usable candidate correctness labels;
- at least 50 percent of evaluated episodes contain both a reachable correct candidate and a reachable distractor candidate;
- `NoReobserve` wrong-goal visit rate is at least 10 percent.

## Primary Numeric Gate

`SemanticOnly` is first-probe positive against `NoReobserve` if all primary thresholds pass:

| Metric | Required threshold |
| --- | --- |
| `wrong_goal_visit_rate` | at least 5 percentage-point absolute reduction and at least 20 percent relative reduction |
| `mean_wasted_path_wrong_goal` | at least 0.5 m absolute reduction and at least 15 percent relative reduction |
| `SPL` | drop no worse than 0.03 absolute and no worse than 10 percent relative |
| `Success Rate` | drop no worse than 3 percentage points |
| `mean_wasted_path_total` | no increase above 0.5 m absolute or 10 percent relative |
| `mean_num_reobservations` | no more than 1.5 per episode on average |

## Policy Objective Revision Gate

### 사실

The current diagnostic `SemanticOnly` objective can change the final candidate during re-observation. This must be measured explicitly before any revised policy is promoted.

### 에이전트 추론

A top-tier claim should not present reachability-biased candidate switching as semantic verification. Revised policies must separate:

- re-observation trigger;
- viewpoint selection;
- post-reobservation evidence update;
- final commit or candidate switch.

Additional required metrics for revised semantic policies:

- `final_candidate_changed_rate`
- `switch_gate_pass_rate`
- `mean_score_delta_after_reobserve`
- `mean_U_sem_delta_after_reobserve`
- `mean_wasted_path_reobserve`

Policy progression:

| Policy | Role | Promotion condition |
| --- | --- | --- |
| `SemanticOnly` | current diagnostic policy | run unchanged after substrate gate passes |
| `SemanticVerifyTop` | no-switch verification ablation | isolates premature switching and re-observation cost |
| `EvidenceGatedSemanticOnly` | revised semantic utility | may switch only after non-GT evidence delta passes predeclared gates |

Do not tune switch gates on held-out `first_eval`.

## Random Baseline Gate

`SemanticOnly` must pass at least two of:

- lower `wrong_goal_visit_rate` than `RandomReobserve`;
- lower `mean_wasted_path_wrong_goal` than `RandomReobserve`;
- `SPL` no worse than `RandomReobserve` by more than 0.02 absolute.

If `RandomReobserve` matches `SemanticOnly`, viewpoint selection is not yet the contribution.

## Uncertainty Validity Gate

| Metric | Required threshold |
| --- | --- |
| wrong-goal `AUROC` | at least 0.60 |
| wrong-goal `AUPRC` | above positive-rate baseline by at least 0.05 |
| Spearman `U_sem` vs candidate failure | at least 0.15 |
| high-vs-low `U_sem` bucket gap | high bucket wrong-goal rate exceeds low bucket by at least 10 percentage points |

If `U_sem` fails this gate, revise uncertainty features or candidate backend before Step 4-5.

## What Does Not Count As Strong Evidence

- improvement only over `RandomReobserve`
- improvement only on `Success Rate` without wrong-goal or wasted-path improvement
- tuning thresholds on final evaluation splits
- using GT oracle as the main comparison
- reporting only successful episodes
- excluding episodes without a predeclared filtering rule
- showing HM3D only without any open-vocabulary or ambiguity stress test

## Implementation Order

1. Build log-only candidate evaluator for HM3D ObjectNav v2.
2. Verify GT target labels, candidate correctness, and shortest-path references.
3. Run `NoReobserve`, `RandomReobserve`, and `GTTargetOracle` on a tiny Docker smoke subset.
4. Add `score_uncertainty`, `margin_uncertainty`, and support feature.
5. Run `SemanticOnly` against `NoReobserve` and `RandomReobserve`.
6. Add HM3D-OVON loading and evaluate `val_seen`, `val_unseen`, `val_seen_synonyms`.
7. Add `FrontierReobserve` and `CAReStyle`.
8. Add Step 4-5 SLAM/map-side metrics only after Step 1-3 evidence is stable.

## Calibration Interpretation Gate

Calibration runs are allowed to choose or reject provisional thresholds and diagnose candidate coverage. They should not be used as held-out paper evidence.

Do not interpret calibration policy metrics unless:

- structural artifact checks pass;
- candidate coverage and ambiguity coverage pass;
- `candidate_backend_uses_gt_for_action = false`;
- policy comparison uses the same manifest rows and candidate artifact for all non-GT policies.

If a coverage recovery artifact is borderline, use the decision tree in `04_first_experiment.md` before launching any policy comparison. Borderline diagnostic policy runs must be labeled diagnostic and cannot be promoted to paper-facing evidence without held-out evaluation confirmation.

## Policy Comparison Interpretation Template

Use this template after a calibration or evaluation policy comparison finishes. Do not interpret policy numbers until the hard validity gate and calibration interpretation gate pass.

### 사실

Required inputs:

```text
summary.json
episodes.jsonl
candidate_decisions.jsonl
viewpoint_decisions.jsonl
artifact_coverage.json
candidate artifact used for all non-GT policies
manifest split and episode ids
```

Required metadata:

| Field | Required value |
| --- | --- |
| `candidate_backend_uses_gt_for_action` | `false` for non-GT policies |
| compared episode ids | identical across policies |
| candidate artifact | identical across non-GT policies |
| `wrong_goal_visit` | commit-based |
| `wrong_goal_pass_through` | diagnostic only |
| GT use | labels, shortest-path references, and oracle upper bounds only |

### Result Tables

Substrate validity table:

| Metric | Value | Gate | Interpretation |
| --- | ---: | --- | --- |
| evaluated episodes |  | expected run size | incomplete run if lower |
| candidate label coverage |  | `>= 0.70` | whether GT labels can evaluate candidates |
| reachable correct-and-wrong rate |  | `>= 0.50` | whether active re-observation is testable |
| `NoReobserve` wrong-goal visit rate |  | `>= 0.10` | whether a wrong-goal stress signal exists |
| `GTTargetOracle` `Success Rate` |  | `1.0` on diagnostic subset | shortest-path / success semantics sanity |

Main behavior table:

| Policy | `Success Rate` | `SPL` | `wrong_goal_visit_rate` | `mean_wasted_path_wrong_goal` | `mean_wasted_path_total` | `mean_num_reobservations` |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `GTTargetOracle` |  |  |  |  |  |  |
| `NoReobserve` |  |  |  |  |  |  |
| `RandomReobserve` |  |  |  |  |  |  |
| `SemanticOnly` |  |  |  |  |  |  |

Primary deltas:

| Comparison | Required interpretation |
| --- | --- |
| `SemanticOnly - NoReobserve` | primary H001 Step 1-3 effect |
| `SemanticOnly - RandomReobserve` | whether viewpoint selection is better than extra observation budget |
| `GTTargetOracle - SemanticOnly` | remaining gap from candidate coverage, policy, or execution |
| `GTTargetOracle - NoReobserve` | upper-bound room for improvement |

Uncertainty validity table:

| Metric | Value | Gate |
| --- | ---: | --- |
| wrong-goal `AUROC` |  | `>= 0.60` |
| wrong-goal `AUPRC` gap over positive-rate baseline |  | `>= 0.05` |
| Spearman `U_sem` vs candidate failure |  | `>= 0.15` |
| high-vs-low `U_sem` bucket gap |  | `>= 0.10` |

Qualitative audit table:

| Episode id | Scene | Query | Top candidate correct? | Reobserve? | Final committed candidate correct? | `wrong_goal_visit` | Wasted path reason |
| --- | --- | --- | --- | --- | --- | --- | --- |

Include at least:

- two cases where `SemanticOnly` fixes a `NoReobserve` wrong-goal visit;
- two cases where `SemanticOnly` fails;
- one case where `RandomReobserve` matches or beats `SemanticOnly`, if present;
- one oracle-gap case where `GTTargetOracle` succeeds but all non-GT policies fail.

### Interpretation Rules

| Observed result | Interpretation |
| --- | --- |
| `SemanticOnly` lowers wrong-goal and wasted-path metrics without unacceptable `SPL` / `Success Rate` drop | positive Step 1-3 signal |
| `SemanticOnly` lowers wrong-goal but increases `mean_wasted_path_total` or drops `SPL` beyond gate | travel-cost arbitration failure |
| `SemanticOnly` improves `Success Rate` / `SPL` but not wrong-goal or wasted-path metrics | not evidence for H001 mechanism |
| `SemanticOnly` matches `RandomReobserve` | active viewpoint selection is not yet the contribution |
| `U_sem` validity fails but policy improves | do not claim uncertainty is the causal mechanism; inspect confounds |
| GT oracle gap remains large because correct candidates are missing | candidate backend coverage limitation |
| GT oracle gap remains large despite candidate coverage | policy/viewpoint selection or navigation execution limitation |

### Do Not Claim

- Do not claim paper-facing improvement from calibration split alone.
- Do not claim semantic uncertainty is useful if only `Success Rate` improves.
- Do not hide re-observation travel cost behind `SPL`; report wasted-path components separately.
- Do not compare policies that used different episode ids or different candidate artifacts.
- Do not use `GTTargetOracle` as a deployable baseline.

## Step 4-5 Promotion Gate

This gate decides when H001 can move from Step 1-3 semantic re-observation to Step 4-5 active SLAM/map-side utility. Passing this gate does not mean the thesis direction is finished; it means a SLAM extension is justified enough to implement and evaluate.

### 사실

Required prior evidence:

| Requirement | Minimum condition |
| --- | --- |
| substrate validity | first-probe hard validity gate passes |
| semantic policy signal | `SemanticOnly` passes the primary numeric gate against `NoReobserve` |
| random baseline sanity | `SemanticOnly` passes the `RandomReobserve` gate |
| uncertainty validity | `U_sem` passes the uncertainty validity gate |
| policy provenance | non-GT policies keep `candidate_backend_uses_gt_for_action = false` |
| replayability | same episode ids can be replayed with added map/pose logging |
| cost accounting | `mean_wasted_path_total`, `mean_wasted_path_reobserve`, and `SPL` are available |

Required SLAM-side observability:

| Signal | Timing | Minimum acceptable proxy |
| --- | --- | --- |
| `SLAMGain(v)` input | before viewpoint choice | pose graph connectivity proxy, loop-closure opportunity, tracked-feature/inlier proxy, or pose covariance proxy |
| map/pose outcome | after execution | pose graph connectivity, localization failure count, map consistency, semantic accuracy, or `ATE/RPE` |
| travel cost | before and after execution | path length to re-observation viewpoint and final goal |

### 논문 주장

- Step 4-5 is not justified by better ObjectNav task score alone.
- The extension must show that semantic memory and SLAM/map uncertainty complement each other, rather than one replacing the other.

### 에이전트 추론

Promotion should be staged:

| Level | Meaning | Allowed work |
| --- | --- | --- |
| `P4-design` | Step 1-3 signal exists, but SLAM metric plumbing is not ready | design utility, logging, Docker image, and proxy scripts |
| `P4-proxy` | pose graph or localization proxy is available | run `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` on same episodes |
| `P4-full` | trajectory GT or stable SLAM backend is available | add `ATE/RPE`, map error, semantic accuracy, and repeated evaluation |

Default path: promote to `P4-proxy` first with pose graph connectivity. Promote to `P4-full` only after the proxy run shows nontrivial map/pose benefit without breaking navigation behavior.

### Do Not Promote If

- candidate coverage or ambiguity coverage fails;
- `U_sem` does not predict candidate failure;
- `SemanticOnly` is matched by `RandomReobserve`;
- improvement is only on `Success Rate` / `SPL` without wrong-goal or wasted-path improvement;
- oracle gap analysis says missing correct candidates dominate the failure;
- there is no SLAM-side signal available before action selection;
- travel cost cannot be measured.

### Step 4-5 Experiment Contract

Compare these policies on the same scene / episode / candidate artifact set:

| Policy | Role |
| --- | --- |
| `SemanticOnly` | Step 1-3 reference |
| `SLAMOnly` | tests whether geometry/map utility alone explains the result |
| `SemanticSLAM` | proposed combined utility |
| `NoReobserve` | base semantic-map commitment |
| `RandomReobserve` | observation-budget control |
| `GTTargetOracle` | path upper bound and success semantics sanity |

Use a predeclared utility form:

```text
U(v) = alpha * SemanticGain(v)
     + beta  * SLAMGain(v)
     - gamma * TravelCost(v)
     - eta   * Risk(v)
```

Weights can be selected only on calibration splits. Do not tune `alpha`, `beta`, `gamma`, or `eta` on held-out evaluation splits.

### Step 4-5 Success Gate

`SemanticSLAM` is a positive Step 4-5 signal only if all conditions below hold:

| Condition | Required result |
| --- | --- |
| map/pose improvement over `SemanticOnly` | at least one SLAM/map metric improves by a predeclared nonzero margin |
| task behavior preservation | `Success Rate` drop no worse than 3 percentage points and `SPL` drop no worse than 0.03 absolute or 10 percent relative against `SemanticOnly` |
| travel-cost control | `mean_wasted_path_total` does not increase by more than 0.5 m absolute or 10 percent relative against `SemanticOnly` |
| complementarity | `SLAMOnly` does not fully explain both task behavior and map/pose improvement |
| failure accounting | localization failure, unreachable viewpoint, map update failure, and semantic candidate failure are logged separately |

Suggested first proxy margins:

| Metric | Positive signal |
| --- | --- |
| pose graph connectivity | `lambda2`, loop-closure count, or connected-component proxy improves over `SemanticOnly` |
| localization failure count | lower than `SemanticOnly` without higher wrong-goal rate |
| semantic accuracy / object precision | no worse than `SemanticOnly` by more than 2 percentage points |
| `ATE/RPE` if available | lower than `SemanticOnly` on the same replay / trajectory |

### Failure Interpretation

| Failure | Interpretation | Next action |
| --- | --- | --- |
| `SemanticSLAM` improves map/pose but hurts `SPL` or wasted path | utility overvalues SLAM gain | revise travel-cost normalization |
| `SLAMOnly` matches `SemanticSLAM` | semantic uncertainty is not contributing to Step 4-5 | keep paper centered on SLAM utility or return to semantic gain design |
| `SemanticOnly` beats `SemanticSLAM` on task and map/pose metrics | combined objective is harmful | report negative extension and keep Step 1-3 scope |
| map/pose metrics are noisy or unavailable | instrumentation failure | keep Step 4-5 at `P4-design`, do not claim SLAM benefit |
| real-world `ATE/RPE` lacks external GT | weak deployment evidence | report qualitative or event-level diagnostics only |

## User Decision Needed

- Choose the accepted `SPL` drop threshold for first probe success.
- Choose whether first Docker runtime should extend `VLMaps` or start from Habitat ObjectNav runtime directly.
