# Research Direction

본 연구는 pre-explored semantic map에서 생기는 semantic uncertainty를 단순 confidence score가 아니라 robot mobility를 유도하는 active SLAM/navigation utility로 변환하는 방향을 따른다.

핵심 방향은 ObjectNav에서 나타나는 wrong-goal commitment와 wasted path를 semantic map failure의 task-level symptom으로 보고, 이를 goal-validity risk, viewpoint evidence gap, map/pose consistency uncertainty로 분해한 뒤, robot이 어떤 candidate를 더 관찰해야 하는지 결정하는 active re-observation framework를 설계하는 것이다.

# Research Background

Semantic map 기반 navigation은 robot이 이전에 탐색한 환경 정보를 재사용해 object search와 navigation을 수행할 수 있게 한다. 그러나 실제 robot이 새로운 환경에 들어가면 같은 category 이름을 가진 여러 object instance, partial observation, detector/segmenter uncertainty, pose/map uncertainty가 동시에 존재한다.

ObjectNav와 OVON 계열 task는 이러한 semantic ambiguity가 실제 navigation behavior로 어떻게 드러나는지 확인하기 좋은 benchmark다. 특히 `Success Rate`나 `SPL`만으로는 robot이 잘못된 object instance에 접근했는지, 불필요한 path를 썼는지, map/pose consistency가 navigation decision과 어떻게 연결되는지 충분히 설명하기 어렵다.

# Motivation

현재 연구의 motivation은 "semantic map을 더 잘 만드는 것"이 아니라, semantic map이 robot action에서 실패를 만드는 원인을 찾고 그 원인에서 method 형태를 자연스럽게 도출하는 것이다.

지금까지의 진단은 direct semantic ranking, detector-score confirmation, geometry-only selection, map-pose top-rule, evidence-availability-only defer가 모두 terminal goal selection으로 쓰일 때 wrong-goal risk 또는 over-deferral을 만든다는 방향을 보였다. 따라서 uncertainty는 candidate commit score가 아니라 active evidence acquisition utility로 쓰는 것이 더 타당하다.

# Limitation of Existing Work

기존 semantic navigation / semantic memory 접근은 semantic confidence나 map memory를 navigation decision에 직접 연결하는 경우가 많다. 이 경우 confidence가 높아도 같은 category의 wrong instance를 선택할 수 있고, detector evidence가 있어도 그 evidence가 ObjectNav goal validity를 보장하지 않는다.

Active perception과 active SLAM 연구는 information gain, uncertainty reduction, map quality를 다루지만, ObjectNav wrong-goal visit, wasted path, semantic goal-validity risk와 같은 task-side failure를 map/pose uncertainty와 함께 닫힌 evaluation contract로 연결하는 경우가 약하다.

현재 H001에서도 이 한계가 반복적으로 확인된다. `pairwise_goal_region_map_pose_arbitration_rule_evaluation_join_v1`은 label-free 조건에서 단 하나의 provisional support row만 만들었고, evaluation-only join에서 그 row는 wrong이었다. 이어서 `pairwise_goal_region_map_pose_rule_failure_diagnostic_v1`은 `dual_evidence_coverage_gap 12`, `relation_contradiction_without_goal_region_context 4`, `missing_second_view_evidence 3`, `provisional_positive_evidence_selects_wrong_instance 1`, `noncontrastive_goal_region_support 1`을 확인했다. 따라서 current rule은 utility가 아니라 failure mechanism diagnostic이며, bounded detector/evidence/evaluation/promotion ladder는 한 diagnostic row에서 mechanism probe만 통과했다. 최신 multi-case ladder는 이 single-case 결과를 terminal utility로 승격하지 않고, `18` action-frozen source rows에서 나온 `72` observation seed rows를 frame/projection, detector/SAM2, label-free evidence materializer, evaluation-only join, bounded promotion gate까지 Docker로 검증했다. 결과는 `bounded_multi_case_diagnostic_readiness_ready`까지만 허용하므로 `rival_contradiction_region_contamination_multi_case_diagnostic_report_v1`을 nonterminal report로 freeze했고, `rival_contradiction_region_contamination_multi_case_path_closure_v1`로 현재 path를 diagnostic-only로 닫았다. 이후 `next_label_free_branch_after_rival_contradiction_closure_v1`은 남은 가장 큰 failure family인 `dual_evidence_coverage_gap` 12 rows를 대상으로 `goal_region_object_relation_coverage_completion_v1`을 다음 observation branch로 선택했고, 현재는 이 branch materializer가 Docker-verified 상태로 target/candidate/observation-seed/audit rows `12/24/48/9`를 생성했다. 또한 frame/projection contract가 `48` symbolic observation rows와 `18/18` geometry candidate coverage를 고정했다. Terminal utility와 paper claim은 여전히 blocked다.

# Problem Definition

입력은 pre-explored semantic map, object/node candidates, candidate-relative geometric/map-pose evidence, detector/segmenter evidence, active observation candidates, 그리고 Habitat 기반 ObjectNav episode context다.

문제는 robot이 target category query를 받았을 때 곧바로 semantic top candidate로 commit하지 않고, 다음 중 하나를 label-free evidence로 결정하는 것이다.

- commit 가능한 goal-validity evidence가 충분한가
- wrong-goal risk가 높아 추가 observation이 필요한가
- 어떤 candidate pair, viewpoint, relation/context evidence를 더 관찰해야 하는가
- map/pose consistency uncertainty가 semantic decision을 보완하거나 반박하는가
- evidence가 부족하면 terminal claim을 미루고 어떤 failure family로 분기해야 하는가

출력은 terminal commit 자체가 아니라, 우선적으로 active re-observation action, post-observation evidence state, failure taxonomy, 그리고 later promotion gate를 통과할 수 있는 task/map evaluation row다.

# Core Hypothesis

If semantic map uncertainty is decomposed into goal-validity risk, viewpoint evidence gap, and map/pose consistency uncertainty, then using the expected reduction of those uncertainties as active re-observation utility can reduce wrong-goal commitment and wasted path in ObjectNav while preserving or improving map/pose consistency, compared with direct semantic memory commitment, semantic-only confidence replanning, random re-observation, and geometry-only exploration baselines.

# Proposed Framework

1. Semantic candidate extraction

   Build object/node candidates from a pre-explored semantic map. Each candidate stores category/query match, semantic score or rank, estimated position, reachable/standoff status, source evidence, and candidate-relative map/pose fields. Candidate generation is treated as a substrate, not the contribution.

2. Uncertainty decomposition

   For each request and candidate set, compute three uncertainty families.

   - `goal_validity_risk`: risk that the semantic top or selected candidate is not a valid target instance.
   - `viewpoint_evidence_gap`: missing or conflicting evidence that could be reduced by moving to a better viewpoint.
   - `map_pose_consistency_uncertainty`: uncertainty in whether candidate geometry, pose graph connectivity, and map consistency support the same decision.

3. Nonterminal routing before commit

   The policy first routes each request into one of several nonterminal branches rather than directly committing:

   - keep audit/control row
   - request independent goal-validity evidence
   - request pairwise goal-region/map-pose arbitration
   - request missing-evidence second-view follow-up
   - request object-relation or relation-depth evidence
   - request source-pool/backend repair when no valid candidate exists
   - defer terminal utility when evidence remains ambiguous

4. Active re-observation utility

   A candidate viewpoint is scored by expected uncertainty reduction under travel and reachability constraints:

   ```text
   U(v) =
     w_g * ExpectedGoalValidityRiskReduction(v)
   + w_e * ExpectedViewpointEvidenceGapReduction(v)
   + w_m * ExpectedMapPoseConsistencyGain(v)
   - w_t * TravelCost(v)
   - w_r * ReachabilityRisk(v)
   ```

   The utility cannot be used as a terminal correctness score. It selects what to observe next. A separate post-observation rule must decide whether the new evidence resolves, contradicts, or preserves ambiguity.

5. Evidence update

   After re-observation, the framework updates candidate evidence states such as `support_acquired`, `contradiction_acquired`, `support_and_contradiction_conflict`, `evidence_missing`, `ambiguity_reduced`, and `needs_goal_validity_confirmation`. Evaluation labels are joined only after these action rows are frozen.

6. Goal-validity arbitration

   A terminal rule is allowed only after a fixed non-GT arbitration rule passes held-out evaluation. Current evidence says the latest pairwise rule does not pass: it produces one provisional support row, and that row is evaluation-only wrong. The follow-up diagnostic selected `rival_contradiction_or_region_contamination_evidence_v1`; the bounded detector/evidence/evaluation/promotion ladder passes on one diagnostic row but allows only `bounded_single_case_mechanism_probe_ready`.

   The latest multi-case ladder now verifies the same failure family at larger diagnostic scale:

   - frame/projection source: `18` source pair rows, `72` observation rows, `9` scenes, `5` queries
   - detector/SAM2 substrate: detector/frame rows `72/72`, candidate association rate `0.8889`, associated candidate heading count `262`
   - label-free evidence: candidate-view/role/pair/request/audit rows `144/72/18/18/18`
   - evaluation-only join: pair labels `a_wrong_b_correct 8`, `both_correct 4`, `both_wrong 6`, baseline wrong-goal rows `17`, max wasted path exposure `1.7589m`, SLAM map-pose delta rows/max `18/1.0`
   - bounded promotion gate: contamination/contradiction pair rows `6`, wrong-labeled contamination/contradiction rows `5`, blockers `[]`, allowed outcome `bounded_multi_case_diagnostic_readiness_ready`

   This still does not define a terminal selector. The nonterminal diagnostic report is frozen, and the current rival contradiction / region contamination path is now closed as diagnostic-only. The next observation branch is `goal_region_object_relation_coverage_completion_v1`; its materializer fixes the missing goal-region/object-relation observation source, and its frame/projection contract is now frozen before Habitat rendering.

7. Semantic-SLAM extension

   After semantic re-observation is stable, map/pose evidence becomes a complementary utility term rather than a direct goal selector. `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` must be compared on the same rows to show whether map/pose consistency improves task behavior or only adds a weak proxy.

# Experiment Plan (Metric, Baseline)

Primary benchmark path:

- `HM3D ObjectNav v2` for controlled first probe.
- `HM3D-OVON` for open-vocabulary ambiguity extension.
- Optional real-world robot replay only after simulator evidence is stable and external GT or calibrated proxy is available.

Primary metrics:

- `Success Rate`
- `SPL`
- `wrong_goal_visit_rate`
- `mean_wasted_path_total`
- `mean_wasted_path_wrong_goal`
- `mean_wasted_path_reobserve`
- `mean_num_reobservations`
- candidate label coverage
- uncertainty vs wrong-goal `AUROC` / `AUPRC`
- map/pose consistency delta
- pose graph connectivity
- `ATE` / `RPE` only when trajectory GT is available

Baselines:

- `NoReobserve`: direct semantic map commit.
- `RandomReobserve`: same observation budget without active selection.
- `FrontierReobserve`: geometry/frontier-only exploration baseline.
- `CARe`-style confidence replanning: semantic confidence baseline.
- `VLFM`-style semantic frontier: semantic frontier navigation reference.
- `OneMap`-style semantic memory: semantic memory reference.
- `SemanticOnly`: semantic uncertainty utility without SLAM/map-pose term.
- `SLAMOnly`: map/pose utility without semantic goal-validity term.
- `SemanticSLAM`: combined semantic and map/pose active utility.
- `GTTargetOracle`, `GTCandidateOracle`, `GTViewOracle`: diagnostic upper bounds only, never deployable baselines.

Promotion gate:

The method can move toward paper-facing claims only if a fixed label-free branch reduces wrong-goal and wasted path against `NoReobserve` and `RandomReobserve`, does not hide cost through excessive re-observation, preserves map/pose consistency, and passes held-out evaluation without post-hoc threshold, metric, or baseline changes.
