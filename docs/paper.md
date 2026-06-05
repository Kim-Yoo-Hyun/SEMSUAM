# Paper Workflow

이 문서는 H001을 석사 논문과 AI, ML, CV, Robotics top-tier journal/conference submission 수준의 paper claim으로 발전시키기 위한 novelty workflow다. 실제 논문 초안, figure, result table은 충분한 evidence가 생기기 전까지 만들지 않는다.

## Source Note

### 사실

- Source checked: 2026-05-14
- Reference: [Motivation != Novelty](https://gisbi-kim.github.io/motivation-is-not-novelty/#dialogue-section)
- 이 문서는 연구 설계와 paper framing을 위한 guideline으로 사용한다.

### 에이전트 추론

이 source는 scientific primary source가 아니라 research coaching guide다. 따라서 실험 근거나 related work citation으로 쓰지 않고, contribution framing과 self-diagnosis checklist로만 사용한다.

## Entry Context

Paper 관련 작업을 시작하는 에이전트는 아래 순서로 읽는다.

1. `AGENTS.md`
2. `README.md`
3. `TODO.md`
4. `docs/index.md`
5. `docs/literature.md`
6. `docs/hypothesis.md`
7. `docs/paper.md`
8. `summary.md`
9. `hypothesis/CAND-01/H001_uncertainty-reobservation/README.md`
10. 대상 numbered hypothesis 문서

## Core Lesson

### 자료 주장

Top-tier paper는 "기존 방법이 어떤 상황에서 안 된다"에서 멈추지 않고, 왜 실패하는지 원리적으로 진단한 뒤, 그 진단에서 method 형태를 도출한다. 실험은 전체 성능 향상만 보이는 것이 아니라 각 design choice가 특정 failure mode를 줄이는지 검증해야 한다.

### 에이전트 추론

H001에서 위험한 framing은 "`VLMaps` semantic map에 detector/segmenter를 붙이고 active re-observation을 했다"이다. 이 표현은 module combination에 가깝다. 더 강한 framing은 "semantic map failure가 viewpoint-conditioned evidence uncertainty, object association uncertainty, geometry/pose uncertainty로 분해되며, 이 uncertainty를 motion utility로 바꾸면 wrong-goal commitment와 map/pose inconsistency를 줄일 수 있다"이다.

## Top-Tier Pattern Checklist

아래 항목 중 하나라도 약하면 paper claim을 확정하지 않는다.

| Gate | Required Question | H001 기준 |
| --- | --- | --- |
| Motivation | 기존 semantic navigation / semantic memory가 어디서 실패하는가? | wrong-goal visit, wasted path, map/pose inconsistency |
| Challenge | 왜 실패하는가? | semantic confidence miscalibration, viewpoint evidence gap, candidate association ambiguity, SLAM uncertainty |
| Problem formulation | 기존 benchmark 점수 외에 어떤 비교 축을 새로 잡는가? | semantic uncertainty calibration + active mobility utility + task/map-side failure decomposition |
| Method derivation | 왜 이 utility 형태여야 하는가? | failure taxonomy의 각 항이 utility term으로 대응되어야 함 |
| Naive baseline | 가장 단순한 구현은 무엇이고 왜 부족한가? | `NoReobserve`, threshold-only `SemanticOnly`, direct semantic memory, detector-only evidence |
| Simpler alternatives | 더 단순한 3개 방법이 왜 안 되는가? | confidence threshold, random re-observation, geometry/frontier-only exploration |
| Ablation | 각 component를 빼면 무엇이 깨지는가? | semantic gain, SLAM gain, travel cost, risk, evidence update, mask/box association |
| Generality | 단일 scene/task에 갇히지 않는가? | `HM3D ObjectNav` first, `HM3D-OVON` extension, optional real-world validation |
| Failure analysis | 언제 실패하는지 숨기지 않는가? | candidate coverage failure, wrong association, unreachable viewpoint, localization failure, excessive travel cost |
| Reviewer answer | "그래서 뭐가 새로운가?"에 30초 안에 답할 수 있는가? | 아래 one-liner가 실험으로 뒷받침되어야 함 |

## Contribution One-Liner Draft

### 에이전트 추론

Semantic map uncertainty becomes actionable when decomposed into semantic evidence uncertainty, viewpoint coverage uncertainty, and SLAM/geometric consistency uncertainty; using expected reduction of these terms as active re-observation utility reduces wrong-goal commitment and wasted path while preserving or improving map/pose consistency.

### 사용자 판단 필요

최종 one-liner는 `v3c_groundingdino_sam2` calibration, policy-scale comparison, Step 4-5 SLAM proxy 결과가 나온 뒤 더 좁혀야 한다. 현재는 draft claim이지 확정 claim이 아니다.

## H001 Novelty Gate

H001을 paper-ready claim으로 올리려면 아래 증거가 필요하다.

- `U_sem` 또는 revised uncertainty가 wrong-goal candidate failure를 calibration split에서 예측한다.
- Active re-observation이 `NoReobserve`보다 wrong-goal visit과 wasted path를 줄인다.
- Active re-observation이 `RandomReobserve`보다 낫다. 그렇지 않으면 "active selection" contribution이 아니다.
- Geometry/frontier-only baseline보다 semantic uncertainty term이 필요한 장면을 보여준다.
- Direct semantic memory / `VLMaps` direct baseline보다 mobility-based evidence update가 필요한 장면을 보여준다.
- Detector-only 또는 threshold-only evidence update보다 uncertainty utility가 필요한 장면을 보여준다.
- `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` 비교에서 semantic utility와 SLAM utility의 역할이 분리된다.
- `GTTargetOracle`, `GTCandidateOracle`, `GTViewOracle` gap analysis로 candidate coverage failure와 policy failure를 분리한다.
- 최소 하나의 held-out split에서 tuning 없이 같은 방향의 결과가 유지된다.

## Confirmation Gate Rule

### 사실

Current frozen candidate-only gate:

```text
gate_name: confirmation_v1_detector_contradiction
field: N1_detector_score_only
confirm: top detector score >= best alternative detector score
disconfirm: best alternative detector score - top detector score >= 0.25
```

### 에이전트 추론

This gate is paper-relevant only as a failure-mechanism probe unless it passes an independent split without tuning. The claim should not be "detector score selects the goal." The stronger and safer claim is:

```text
object-node evidence can disconfirm an overconfident semantic top candidate,
and disconfirmation should trigger active re-observation instead of direct goal switching.
```

Promotion requires an independent run with one fixed config, low false disconfirmation, and wrong-goal routing to re-observation. If this fails, the result should be written as evidence that current object-node evidence is insufficient, not as motivation to tune the threshold on the validation split.

### 사실

The first independent validation of this frozen gate failed on `confirmation_independent_v1`:

```text
rows: 20
promotion_ready: false
reason: independent_fixed_gate_failed
confirmed_wrong_goal: 9 / 12
disconfirmed_wrong_goal_precision: 1.0
false_disconfirm_correct_top_count: 0
wrong_goal_routed_to_reobserve_rate: 0.40
```

### 에이전트 추론

The negative result sharpens the novelty path: V1 disconfirmation is precise but sparse, while V1 confirmation is unsafe because score ties and zero-evidence cases are treated as confirmation. A paper-facing method must therefore distinguish "confirmed by positive evidence" from "not contradicted." This supports an active re-observation framing, but V1 is not promotable.

V2 `supported_contradiction` debugging fixed the no-evidence tie issue but still produced unsafe confirmation:

```text
confirmed_rows: 3 / 20
confirmed_wrong_goal_rate: 1.0
wrong_goal_routed_to_reobserve_rate: 0.80
```

Paper implication: object-node evidence is currently stronger as a risk / re-observation trigger than as a commit authority. A stronger claim should be about reducing premature commitment, not about proving the semantic top candidate correct.

## Risk-Only Claim Direction

### 에이전트 추론

The current strongest paper direction is not "object evidence confirms the correct goal." It is:

```text
semantic map failures can be detected as commitment risk,
and object-node evidence should convert that risk into active re-observation utility.
```

This aligns better with the novelty rule because the method shape follows from the observed failure mechanism:

```text
direct re-ranking creates new wrong-goals
confirmation gates are unsafe
disconfirmation / uncertainty is useful for routing wrong-goal rows to re-observation
```

The required ablation is therefore `RiskOnlyReobserve` against `NoReobserve`, `RandomReobserve`, direct re-ranking, and detector-score confirmation variants.

## Current Direction Assessment

### 사실

- Active hypothesis: `H001_uncertainty-reobservation`
- Current target claim: semantic uncertainty를 active SLAM/navigation utility로 사용해 `ObjectNav` wrong-goal visit, wasted path, map/pose consistency를 개선한다.
- Current benchmark path: `HM3D ObjectNav` first, `HM3D-OVON` extension.
- Current metrics: `Success Rate`, `SPL`, wrong-goal visit, wasted path, uncertainty calibration, candidate coverage, semantic accuracy, map error, pose graph connectivity, `ATE/RPE`.
- Current evidence 상태:
  - `risk_validation_v1` candidate substrate는 reachable correct-and-wrong rate `0.54`로 coverage gate를 통과했다.
  - `v3_fresh_validation_v1` candidate substrate는 reachable correct-and-wrong rate `0.69`로 coverage gate를 통과했다.
  - Direct semantic/object-node re-ranking, threshold-only revision, and positive confirmation gates produced wrong-goal or over-deferral failure modes.
  - V4 external evidence on `risk_validation_v1` passes the current safety/full gate with `commit_rate 0.20`, `success_commit_rate 0.20`, and wrong-goal commit `0.00`.
  - V4 still requests active mobility for unresolved rows: `request_identity_confirmation 0.40`, `request_expanded_retrieval 0.40`.
  - `ExternalCandidateFollowupObservation` planner and small detector smoke passed, but follow-up evidence smoke failed the full gate because strong depth-associated evidence rate was `0.00`.
  - Object-relation bounded arbitration rejects two relation-depth-resolved negative candidates without action-time labels, and fresh/predeclared source precheck freezes `7` route-specific goal-validity rows across `5` scenes and `3` queries with bounded overlap `0`; fresh observation planning passes with `36` targets and `144` standoff plan rows, fresh frame/projection smoke passes with frame rows/headings `144/576`, nonblank rows/headings `144/573`, projection visible rows `141/144`, missing candidates `0`, and GT action rows `0`, fresh detector/SAM2 substrate passes with detector rows `144`, detector box/SAM2/candidate association `0.9583/0.9583/0.8264`, associated candidate heading count `338`, and GT action rows `0`, and fresh post-detector evidence aggregation passes with request/evidence rows `36/108`, `resolved 24`, `partial 12`, evaluation-only `resolved positive 3`, `resolved negative 21`, and terminal commits `0`. Fresh fixed-rule arbitration validation is Docker-run and fails promotion: `reject 20`, `defer 12`, `provisional 4`, rejected negative/positive `17/3`, provisional negative/positive `4/0`, terminal commits `0`, and `object_relation_arbitration_rule_gate_passed false`. Failure diagnosis shows the main mechanism is `object_visibility_and_relation_depth_do_not_establish_objectnav_goal_validity`, with request tags `unique_independent_support_selects_wrong_goal 4`, `object_visibility_preferred_over_true_goal_validity 4`, `correct_goal_rejected_by_missing_strong_own_view 3`, and `correct_goal_relation_depth_partial 5`.
  - The first branch-specific unique-support goal-region path now passes planner, frame/projection, detector/SAM2, post-detector evidence analyzer, and inspection gates. Its second-pass rival-region planner and frame/projection smoke are Docker-verified. The strict detector/SAM2 substrate and `mask_depth_1_25_v1` repair both failed candidate association, but the predeclared runtime-semantics repair `mask_depth_2_0_v1` passes the actual substrate. Post-detector evidence aggregation passes its nonterminal gate with view/pair/request rows `30/10/4`, but cross-region inspection blocks terminal arbitration: pair blockers are `bidirectional_cross_region_overlap 3`, `rival_visible_from_focus_region 2`, `focus_visible_from_rival_region 2`, `shared_common_view_rival_support 2`, and `pure_contrastive_no_second_pass_support 1`; request blockers are `contains_cross_region_overlap_pairs 3` and `contains_shared_common_view_rival_support 1`. The cross-region overlap branch freeze routes `3/4` requests to `cross_region_overlap_failure_branch`; shared-common branch freeze routes the remaining `rival_identity:7` request to `shared_common_view_support_failure_branch`. Unique-support branch closure closes `4/4` unique-support requests as terminal-blocked and selects `partial_relation_depth_true_goal` as the next branch-specific route with request/candidate rows `6/12`. Terminal utility and paper claims remain blocked.
  - `first_eval` replacement rerun and policy-scale comparison remain blocked.

### 에이전트 추론

현재 방향은 링크에서 말한 top-tier pattern과 맞을 가능성이 있다. 이유는 단순히 semantic map을 쓰는 것이 아니라, semantic map이 navigation에서 어떤 failure를 일으키는지 wrong-goal visit과 wasted path로 정의하고, 그 failure를 active mobility decision으로 줄이려는 구조이기 때문이다.

하지만 아직 top-tier-ready는 아니다. V4는 semantic uncertainty를 active observation request로 바꾸는 더 좋은 method shape를 보였지만, follow-up observation이 실제로 over-deferral을 줄이고 wrong-goal commit을 다시 만들지 않는다는 full validation이 아직 없다. 특히 `GroundingDINO + SAM2`는 좋은 engineering component일 수 있지만, 그 자체가 novelty가 되면 안 된다. 이 component는 object evidence update와 active observation utility가 왜 필요한지 보여주는 diagnostic 도구로만 취급해야 한다.

## Risk of Weak Framing

아래 표현은 피한다.

- "`VLMaps`에 active re-observation을 추가했다."
- "Detector/segmenter를 붙여서 semantic map을 개선했다."
- "기존 ObjectNav보다 `Success Rate`가 올랐다."
- "Foundation model을 쓰면 semantic navigation이 좋아진다."
- "특정 category마다 다른 hand-tuned switch rule을 넣었다."

이 표현들은 motivation 또는 engineering description으로는 가능하지만 contribution으로는 약하다.

## Category Rule Gate

### 사실

`weak_category_rule_v1`은 same-artifact diagnostic에서 selected-correct를 `33/100`에서 `36/100`으로 올렸고 new wrong-goal을 만들지 않았다. Scene-wise minimal gate는 통과했지만, category-level robustness는 실패했다. `plant`는 `TEEsavR23oF` 한 scene에서만, `tv_monitor`는 `y9hTuugGdiq` 한 scene에서만 개선됐다.

### 에이전트 추론

이 rule은 paper-facing method로 freeze하지 않는다. Top-tier novelty를 강화하려면 category별 patch가 아니라 failure taxonomy에서 강제되는 일반 원리를 method로 만들어야 한다. Category-specific result는 다음 용도로만 사용한다.

- detector evidence가 strict depth association보다 나은 경우가 있음을 보여주는 diagnostic
- object property별 failure taxonomy를 만드는 근거
- ablation에서 "category-tuned rule"을 weak baseline 또는 upper diagnostic으로 비교하는 후보

### 사용자 판단 필요

사용자가 빠른 석사 실험 안정성을 더 중시하면 `weak_category_rule_v1`을 diagnostic baseline으로 유지할 수 있다. Top-tier submission을 우선하면 이 rule을 main method로 쓰지 않고 object-node evidence objective로 일반화한다.

## Stronger Paper Framing

### 에이전트 추론

H001은 다음 구조로 좁힐 때 가장 강하다.

1. Semantic memory 기반 ObjectNav에서 wrong-goal commitment가 반복적으로 발생한다.
2. 이 failure는 단순 confidence threshold 문제가 아니라 object evidence, viewpoint coverage, map/pose uncertainty가 섞인 decision uncertainty 문제다.
3. 이 uncertainty를 candidate re-ranking score가 아니라 robot motion utility로 바꾼다.
4. Re-observation viewpoint는 expected uncertainty reduction, travel cost, reachability/risk를 함께 고려해 선택한다.
5. 결과는 `SR`/`SPL`뿐 아니라 wrong-goal visit, wasted path, uncertainty calibration, map/pose metrics로 검증한다.

## Required Baselines and Ablations

| Type | Required Comparisons |
| --- | --- |
| Navigation baseline | `NoReobserve`, `RandomReobserve`, `FrontierReobserve`, `CARe`-style confidence replanning |
| Semantic memory baseline | `VLMaps` direct / semantic memory direct, direct candidate ranking |
| Oracle reference | `GTTargetOracle`, `GTCandidateOracle`, `GTViewOracle` |
| Utility ablation | semantic gain only, SLAM gain only, travel-cost removal, risk removal |
| Evidence ablation | score-only, margin-only, support-only, box-only, mask-only, detector+mask |
| Dataset generality | `HM3D ObjectNav`, `HM3D-OVON`; real-world only after simulator evidence is stable |

## Near-Term Paper Actions

1. Use the completed full candidate-specific objective analyzer as a diagnostic gate, not as terminal utility evidence.
2. Keep terminal commits blocked because full candidate-specific visual support is saturated: `146/158` candidates have `candidate_specific_support`, and simple observed-candidate selection rules still commit wrong on both recovered rows.
3. Treat the frozen object-relation interpretation gate as terminal-blocking evidence: detector-depth evidence resolves both bounded requests, but evaluation-only labels mark both target candidates negative, so detector-depth consistency is not terminal goal-validity utility.
4. Treat the bounded `relation_depth_guarded_non_gt_arbitration_v1` smoke as a guard result: it rejects `2/2` relation-depth-resolved negative candidates using independent candidate-specific support, but terminal utility remains blocked because it has not shown nonzero success over defer-all.
5. Record `bxsVRursffK::bed` / `rival_identity:13` as a backend/source-map recall blind spot for this diagnostic branch unless a later all-row backend policy changes the source-map evidence.
6. Preserve simpler alternatives as unsafe or inert baselines: direct re-ranking, detector-score best, source-top, own-support, local-context-only, observed semantic-top, observed detector-score-best, relation-depth-resolved commit, box/mask presence commit, high-association-count commit, and defer-all.
7. Write the failure taxonomy around source-pool validity, object visibility vs goal validity, repeated-instance arbitration, bounded-substrate candidate coverage, and support-saturation after full candidate-specific observation.
8. Do not promote the current fixed rule: fresh validation rejects many negatives but also rejects positives and gives provisional status to wrong candidates. The fresh failure taxonomy is now the paper-relevant signal.
9. Treat the frozen branch-specific contract as the next paper mechanism test: `unique_support_visibility_not_goal_validity`, `correct_candidate_missing_own_view_support`, `partial_relation_depth_true_goal`, and `negative_missing_support_guard` must be routed before any terminal utility or `first_eval` rerun.
10. Treat the Docker-verified branch router as a mechanism-routing result, not a utility result: it covers all known fresh failure tags with terminal commits `0` and selects `unique_support_visibility_not_goal_validity` for the next contrastive goal-region evidence contract.
11. Treat the frozen `unique_support_goal_region_v1` contract as the first branch-specific observation mechanism, not a claim: it fixes `4` target requests, `17` focus-vs-rival pairs, and `21` candidate target rows to test whether visible-object support must become contrastive goal-region evidence before terminal commitment.
12. Treat the Docker-smoked unique-support planner/frame/projection/detector substrate as substrate evidence only: it produces `51` nonterminal focus/rival/common-view observation targets with visible projection anchors, no blank headings, detector box/SAM2 rates `1.0/1.0`, candidate association `0.6471`, and no action-label leakage.
13. Treat the second-pass rival-region path as a mechanism diagnosis, not terminal-policy evidence. The `mask_depth_2_0_v1` runtime repair clears detector/SAM2 substrate, but inspection shows no request is clean contrastive-only: `3/4` requests contain cross-region overlap and `1/4` still has shared common-view rival support.
14. Treat the frozen cross-region overlap branch as failure-mechanism routing, not a method claim: `3` requests are terminal-blocked cross-region overlap failures and `rival_identity:7` remains a shared common-view support case. This led to the shared common-view inspection below rather than a terminal arbitration contract.
15. Treat shared common-view inspection and branch freeze as another terminal-blocking result: `rival_identity:7` has one clean contrastive pair, but the same request also has one shared-common-view rival support pair, so `commit_if_any_clean_contrastive_pair` and `commit_if_no_cross_region_overlap` are rejected as terminal rules.
16. Treat unique-support branch closure as route selection, not a method claim: `4/4` unique-support requests are terminal-blocked, and the next nonterminal branch is `partial_relation_depth_true_goal` with request/candidate rows `6/12`. The next paper-relevant mechanism test is whether additional relation-depth observation can separate true-goal incompleteness from candidate invalidity without terminal-label leakage.
17. Treat the frozen `partial_relation_depth_true_goal` contract as a nonterminal observation mechanism: it fixes failed relation-depth evidence rows `22` and context anchor rows `48`, and blocks both `reject_partial_relation_depth_as_invalid` and `commit_partial_relation_depth_candidate`. The next evidence must show whether relation-depth completion reduces false rejection risk without creating a new confidence-based commit shortcut.
18. Treat the Docker-verified partial relation-depth materializer/planner as substrate evidence only: input rows are `6/12/22/48`, planner rows are `48`, skipped rows are `0`, failed evidence mapped/unmapped is `22/0`, and action forbidden keys/terminal commits are `0/0`. The next reviewer-facing test is frame/projection and detector evidence, not terminal utility.
19. Treat the partial relation-depth frame/projection smoke as renderability evidence only: frame rows/headings are `48/192`, nonblank rows are `48`, projection rows/expected are `48/48`, visible rows/rate are `48/1.0`, and GT action rows are `0`. The next paper-relevant gate is whether detector/SAM2 evidence can actually complete relation-depth uncertainty without using labels.
20. Treat the partial relation-depth detector/SAM2 substrate as sufficient to write an evidence analyzer contract, not as utility evidence: detector rows are `48`, detector box/SAM2/candidate association rates are `1.0/1.0/0.8125`, associated candidate heading count is `97`, and GT action is `false`. The analyzer must separate relation-depth evidence completion from terminal commit.
21. Treat the frozen partial relation-depth post-detector contract as the next novelty-defense mechanism test: it requires expected plan/detector/association rows `48/48/192`, minimum candidate association rate `0.80`, minimum associated candidate heading count `90`, and terminal commits `0`. The reviewer-facing question is whether partial relation-depth uncertainty can be converted into evidence completion without using detector visibility as a goal-validity shortcut.
22. Treat the Docker-verified partial relation-depth post-detector analyzer as nonterminal mechanism evidence: it resolves `7/22` failed relation-depth rows, leaves `15/22` partial, writes terminal commits `0`, and keeps `uses_gt_for_action false`. The next paper action is residual partial-row taxonomy, not a terminal utility contract.
23. Treat the residual partial-row inspection as the next novelty-defense constraint: all `15` remaining rows have inside-mask evidence but still `no_candidate_associated_depth_improvement`; `bxsVRursffK/plant` accounts for `12/15`. A terminal rule would be weak unless it first explains association-zero rows, association-positive-but-not-improved rows, and repeated-object relation-anchor ambiguity as separate failure mechanisms.
24. Treat the frozen residual taxonomy as a terminal-blocking result: rows split into `association_present_without_depth_improvement 7`, `depth_signal_not_candidate_associated 3`, and `mask_projection_without_association_or_depth 5`; request statuses split into `repeated_object_relation_anchor_ambiguity 3`, `association_geometry_underlink 2`, and `association_present_but_depth_not_improved 1`. The next novelty-defense step is branch handling, not a terminal utility contract.
25. Treat the frozen residual branch-handling contract as reviewer-defense scaffolding, not a method claim: `association_geometry_underlink` routes to association-geometry repair, `association_present_but_depth_not_improved` routes to depth-stagnation handling, and `repeated_object_relation_anchor_ambiguity` routes to repeated-object relation-anchor ambiguity. The next evidence must show that the router preserves all request rows without labels, terminal commits, threshold tuning, `first_eval`, or policy-scale comparison.
26. Treat the Docker-verified residual branch-handling router as mechanism routing only: it routes request rows `6/6` with branch actions `route_to_repeated_object_relation_anchor_ambiguity_branch 3`, `route_to_association_geometry_repair_branch 2`, and `route_to_depth_stagnation_branch 1`, with unmapped request rows `0`, terminal commits `0`, and action forbidden keys `0`. The next reviewer-defense step is an association-geometry repair branch contract, because projection/mask evidence cannot be treated as goal-validity evidence when candidate association underlinks.
27. Treat the frozen association-geometry repair contract as a substrate diagnostic, not a goal-validity rule: the two target rows have inside-mask projection evidence but zero candidate association and zero depth-consistent completion. The next evidence should test projection-anchor replay, mask-depth agreement, and candidate geometry sanity without using labels, committing candidates, or rejecting partial relation-depth rows as invalid.
28. Treat the Docker-verified association-geometry repair diagnostic as a mechanism split, not a terminal utility result: exact failed completion views still have association/depth-consistent counts `0/0` with inside-mask count `5`, while alternative completion geometry recovers same-requested/other-requested associated heading counts `2/14`. The next paper-defense step is a nonterminal follow-up repair contract for relation-anchor selection and direction-specific re-observation, not a candidate commit/reject rule.
29. Treat the frozen association-geometry follow-up repair contract as branch scaffolding only: it routes `sofa` to relation-anchor selection repair and `bed` to direction-specific re-observation repair. This can support method derivation later, but it is not evidence that either candidate is a valid ObjectNav goal.
30. Treat the Docker-verified association-geometry follow-up router as mechanism routing only: it preserves follow-up/request rows `2/2`, maps both source actions, keeps action forbidden keys `0`, terminal commits `0`, and candidate commit/rejection rows `0/0`. The next novelty-defense step is a relation-anchor selection repair probe for `rival_identity:3` `sofa`, not terminal goal-validity evidence.
31. Treat the frozen relation-anchor selection repair contract as a replay/audit constraint: the failed explicit anchor row has association/depth/inside-mask `0/0/4`, while the same-direction anchorless recovery row has `2/1/4`. This can motivate a relation-anchor selection design choice only if implementation shows the contrast is reproducible without labels, candidate rejection, or terminal commit.
32. Treat the Docker-verified relation-anchor selection repair probe as reproducibility evidence for one mechanism only: it materializes the failed explicit anchor and anchorless recovery rows with no forbidden action keys, terminal commits, or candidate commit/rejection rows. The next novelty-defense step is the different `bed` mechanism, where recovery is direction-specific rather than same-direction anchor selection.
33. Treat the frozen direction-specific re-observation repair contract as a separate mechanism constraint: `rival_identity:5` `bed` fails under relation-anchor-to-target / `compass_315` rows but recovers under target-to-relation-anchor rows, with no action-label leakage or terminal commit. This can support a future direction-priority design choice only after the Docker probe materializes the four-row contrast and preserves candidate commit/rejection `0/0`.
34. Treat the Docker-verified direction-specific re-observation repair probe as mechanism evidence only: it materializes two failed same-requested-direction rows and two recovered target-to-relation-anchor rows, preserves forbidden action keys `0`, terminal commits `0`, and candidate commit/rejection `0/0`, and should not be reframed as a valid-goal proof. The next novelty-defense step is repeated-object relation-anchor ambiguity, not terminal utility.
35. Treat the frozen repeated-object relation-anchor ambiguity contract as a reviewer-defense constraint, not a method claim: the `bxsVRursffK/plant` slice has three requests and twelve branch rows with mixed association-positive, association-zero, depth-consistent, and mask-only evidence across repeated candidate ids. This supports an instance/anchor ambiguity branch only if implementation preserves label-free routing, terminal commits `0`, and candidate commit/rejection `0/0`.
36. Treat the Docker-verified repeated-object relation-anchor ambiguity branch as mechanism audit only: it materializes branch/request rows `12/3` with nonterminal action `request_repeated_object_relation_anchor_ambiguity_audit 12`, action forbidden keys `0`, terminal commits `0`, candidate commit/rejection `0/0`, and branch gate `true`. It should not be reframed as valid-goal evidence because mixed association/depth/mask signals still occur across repeated `plant` candidates. This led to the depth-stagnation branch contract below.
37. Treat the frozen depth-stagnation branch contract as a reviewer-defense constraint, not a terminal rule: the `4ok3usBNeis/sofa` row has candidate association and depth-consistent evidence, but prior and completion evidence remain partial (`3/1/7/7` prior association/depth-consistent/depth-mismatch/inside-mask; `3/1/4` completion association/depth-consistent/inside-mask). This supports a depth-stagnation audit only if implementation preserves label-free routing, terminal commits `0`, and candidate commit/rejection `0/0`.
38. Treat the Docker-verified depth-stagnation branch as the final residual partial relation-depth mechanism audit, not as a terminal utility result: it materializes branch/request rows `1/1`, nonterminal action `request_depth_stagnation_audit 1`, depth/association delta `0/0`, action forbidden keys `0`, terminal commits `0`, candidate commit/rejection `0/0`, and branch gate `true`. The next reviewer-defense step is residual branch synthesis, because all residual branches are still nonterminal audits rather than validated commit/reject rules.
39. Treat the Docker-verified residual partial relation-depth branch synthesis as terminal-blocking evidence, not as method utility: it accounts for all request/source-branch rows `6/15` across `association_geometry_underlink`, `repeated_object_relation_anchor_ambiguity`, and `depth_stagnation`, with family output rows `8/12/1`, synthesis status `nonterminal_audit_or_repair_only 3`, promotable terminal outcome rows `0`, action forbidden keys `0`, terminal commits `0`, and candidate commit/rejection `0/0`. The next paper-defense step is to define what extra label-free evidence would make a branch outcome promotable; `first_eval`, policy-scale comparison, and paper claims remain blocked.
40. Treat the Docker-verified residual branch promotion requirement as a design gate, not as utility evidence: it defines three unsatisfied branch requirements, finds promotable family rows `0`, preserves action forbidden keys `0`, terminal commits `0`, and candidate commit/rejection `0/0`, and prioritizes `repeated_object_relation_anchor_ambiguity` before `association_geometry_underlink` and `depth_stagnation`. This led to the repeated-object relation-anchor consistency evidence contract below; terminal utility and paper claims remain blocked.
41. Treat the frozen repeated-object relation-anchor consistency evidence contract as the first concrete residual-branch promotion probe, not as a terminal rule: it targets `bxsVRursffK/plant` request/branch rows `3/12`, uses prior context anchor rows `36`, requires at least `18` candidate-anchor pair rows and `27` observation target rows across `candidate_own_view`, `relation_anchor_context_view`, and `orthogonal_axis_challenge_view`, and preserves action forbidden keys `0`, terminal commits `0`, and candidate commit/rejection `0/0`. The next paper-defense step is a Docker materializer/planner; terminal utility and paper claims remain blocked.
42. Treat the Docker-verified repeated-object relation-anchor consistency materializer/planner as substrate evidence only: it writes request/candidate/pair/observation rows `3/9/27/27`, candidate artifact rows/candidates `1/5`, skipped rows `0`, minimum context candidates per request `4`, and all required view roles with action forbidden keys `0`, terminal commits `0`, candidate commit/rejection `0/0`, and `uses_gt_for_action false`. The next paper-defense step is frame/projection smoke and detector-backed consistency evidence, not terminal utility.
43. Treat the Docker-verified repeated-object relation-anchor consistency frame/projection smoke as renderability evidence only: it exports frame rows/headings `27/180`, keeps nonblank rows/headings `27/180`, passes projection with visible rows/rate `27/1.0`, missing candidate rows `0`, explicit candidate-id selection rows `27`, and `uses_gt_for_action false`. The next paper-defense step is detector/SAM2 evidence and a consistency analyzer that can test whether relation-anchor assignment is stable; terminal utility and paper claims remain blocked.
44. Treat the Docker-verified repeated-object relation-anchor consistency detector/SAM2 substrate as sufficient to write a consistency evidence analyzer contract, not as utility evidence: it has frame/detector rows `27/27`, detector box/SAM2/candidate association `1.0/1.0/0.8889`, association rows `360`, selected candidate count rows `2:27`, and GT action rows `0`. The analyzer must test relation-anchor assignment stability, conflict-free target/context support, candidate-associated depth consistency, and orthogonal-axis contradiction before any candidate commit/rejection can be reconsidered.
45. Treat the frozen repeated-object relation-anchor consistency detector-evidence contract as the next novelty-defense mechanism test: it requires view/candidate/request evidence rows `27/9/3`, candidate-context pair rows `27`, target/context support accounting across three view roles, terminal commits `0`, candidate commit/rejection `0/0`, and no label action inputs. The reviewer-facing question is whether relation-anchor consistency can reduce repeated-object semantic ambiguity without turning raw detector association into a goal-validity shortcut.
46. Treat the Docker-verified repeated-object relation-anchor consistency detector-evidence analyzer as terminal-blocking mechanism evidence: it passes the nonterminal gate with view/pair/candidate/request rows `27/27/9/3`, but candidate statuses are `ambiguous_repeated_object_candidate 6` and `insufficient_candidate_evidence 3`, with promotable branch outcome rows `0`. This strengthens the novelty-defense failure taxonomy: relation-anchor consistency evidence exposes own-view context leakage and missing own-view target support, so the next step is residual diagnosis rather than terminal utility.
47. Treat the Docker-verified repeated-object residual diagnostic as branch closure, not method utility: every request has `same_request_stable_tie_with_own_view_context_leakage`, with failure classes `own_view_context_leakage 3`, `same_request_stable_rule_tie 3`, and `missing_own_view_target_support 3`. The repeated-object priority branch produces `0` promotable outcomes, so the next reviewer-defense step is `association_geometry_underlink` repair-followup evidence, still without terminal commit, candidate rejection, `first_eval`, policy-scale comparison, or paper claim.
48. Treat the frozen `association_geometry_underlink` repair-followup evidence contract as a repairability audit, not a goal-validity result: it preserves source branch/request/materialized rows `2/2/8`, route counts `route_to_relation_anchor_selection_repair 1` and `route_to_direction_specific_reobservation_repair 1`, expected probe/request rows `6/2`, recovered association/depth minimums `10/9`, terminal commits `0`, candidate commit/rejection `0/0`, and `uses_gt_for_action false`. The reviewer-facing question is whether underlinked semantic-map geometry can be repaired by anchor/direction evidence without creating a new shortcut such as `commit_if_any_repair_recovers_association`.
49. Treat the Docker-verified `association_geometry_underlink` repair-followup analyzer as terminal-blocking mechanism evidence: it passes with evidence/request rows `6/2`, underlink rows `3`, repair-recovered association/depth rows `3`, recovered association/depth counts `10/9`, and zero forbidden action keys or terminal commits. This supports anchor/direction repair as active evidence acquisition, but no branch is promotable because repaired association and depth are still not ObjectNav goal validity.
50. Treat the frozen `residual_branch_closure_v1` contract as branch-family closure, not method utility: residual synthesis accounts for family/request/source-branch rows `3/6/15`, promotion requirements remain `defined_not_satisfied 3`, repeated-object and association-geometry extra probes both have promotable branch outcome rows `0`, and depth-stagnation is a one-row stagnant case with association/depth-consistency delta `0/0`. This closes the current residual partial relation-depth family as terminal-blocking failure taxonomy and defers a depth-stagnation independent-support probe until broader rows or map/pose-side evidence exist.
51. Treat the Docker-verified `residual_branch_closure_v1` analyzer as closure evidence, not a utility result: it writes `3` closure rows with closure gate `true`, zero terminal commits, zero candidate commit/rejection rows, and six failure mechanisms across repeated-object ambiguity, anchor/direction underlink repairability, and depth-stagnation. This strengthens reviewer defense by explaining why these branches are not terminal shortcuts; the next novelty step must identify a different label-free evidence family that can produce a promotable branch outcome.
52. Treat the Docker-verified `next_label_free_evidence_family_v1` selector as route selection, not paper evidence: it selects `missing_own_view_support_recheck` with branch/action `correct_candidate_missing_own_view_support` / `request_missing_own_view_recheck`, request/candidate rows `7/20`, and paired `negative_missing_support_guard` rows `7/20`. The reviewer-facing reason is that missing own-view evidence should trigger active observation before absence of support is used as candidate rejection. Terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked until the missing-own-view recheck branch produces a promotable label-free outcome.
53. Treat the frozen `missing_own_view_recheck_observation_v1` contract as an active-evidence acquisition constraint, not a rejection rule: all `20` selected candidates have `weak_or_partial_candidate_specific_support` and strong own-view evidence `false`, while existing source plan rows provide `4` standoff references per target candidate. The paper-facing design choice is that missing own-view support must be observed before `negative_missing_support_guard` can be tested as anything stronger than a safety counterfactual.
54. Treat the Docker-verified missing-own-view materializer/planner as substrate evidence only: it preserves request/candidate/base/source-plan rows `7/20/20/80`, writes `80` candidate-centered own-view recheck plan rows with skipped rows `0`, action forbidden keys `0`, terminal commits `0`, and candidate rejection rows `0`. The reviewer-facing next question is whether frame/projection and detector evidence can acquire independent own-view support without turning missing evidence into a rejection shortcut.
55. Treat the Docker-verified missing-own-view frame/projection smoke as renderability evidence only: it exports frame rows/headings `80/320`, keeps nonblank rows/headings `80/317`, projects target candidates for `80/80` rows, and has missing candidate rows `0` plus GT action rows `0`. The reviewer-facing next question is whether detector/SAM2 evidence actually provides independent own-view support; renderability alone is not a utility claim.
56. Treat the Docker-verified missing-own-view detector/SAM2 substrate as analyzer-enabling evidence only: detector box/SAM2/candidate association rates are `1.0/1.0/0.9625` over `80` rows, with `77` associated rows and `3` unassociated `sofa` rows. The reviewer-facing next question is not whether boxes/masks exist, but whether acquired own-view support changes the branch outcome without equating visibility or missing association with ObjectNav goal validity.
57. Treat the frozen missing-own-view post-detector contract as a mechanism test, not a claim: it requires view/candidate/request/unassociated-frame rows `80/20/7/3`, target candidates with any association `20`, full `4/4` association `17`, partial `3/4` association `3`, and zero target candidates with no association. The analyzer should show whether missing own-view uncertainty becomes explicit support state; it must not promote `negative_missing_support_guard`, candidate rejection, terminal utility, `first_eval`, policy-scale comparison, or paper claims.
58. Treat the Docker-verified missing-own-view analyzer as evidence-acquisition mechanism only: all `20` target candidates become `candidate_own_view_support_acquired`, with full `4/4` association `17`, partial `3/4` association `3`, unassociated-frame audit rows `3`, and terminal/candidate commit/rejection `0/0/0`. The next reviewer-defense question is how `negative_missing_support_guard` should be interpreted after recheck; acquired support is still not `ObjectNav` goal validity.
59. Treat the frozen missing-own-view guard arbitration contract as a safety-rule test, not a terminal rule: it expects `negative_missing_support_guard` to be deactivated for all `20` candidate rows after recheck, with request rows `7`, unassociated-frame audit rows `3`, terminal/candidate commit/rejection `0/0/0`, and promotable terminal outcome rows `0`. The reviewer-facing point is that missing support should cause active evidence acquisition before rejection; once support is acquired, the guard should not become a shortcut to goal commitment.
60. Treat the Docker-verified missing-own-view guard arbitration analyzer as nonterminal safety-rule closure: it deactivates `negative_missing_support_guard` for candidate/request rows `20/7`, preserves unassociated-frame audit rows `3`, keeps guard-deferred/candidate rejection/candidate commit/terminal commit/promotable terminal rows `0`, and keeps paper claims blocked. The reviewer-defense value is the causal rule ordering: missing support triggers active observation first, then the negative guard is removed rather than converted into either rejection or goal commitment.
61. Treat the Docker-verified missing-own-view guard branch closure as object-relation branch-family accounting, not terminal utility: it closes `correct_candidate_missing_own_view_support` and `negative_missing_support_guard` with branch/request/candidate rows `2/7/20`, closed request/candidate rows `7/20`, and promotable terminal outcome rows `0`. The paper-facing value is stronger failure taxonomy and causal rule ordering, while the next action is selecting a new label-free evidence family rather than rerunning `first_eval` or claiming utility.
62. Treat the Docker-verified post-object-relation selector as branch prioritization, not paper evidence: it closes the object-relation family for now and selects `instance_arbitration_defer_v1` as the next label-free evidence family with request rows `9`, scenes `5`, queries `3`, candidate count sum `51`, and route action `defer_instance_arbitration_unresolved 9`. The reviewer-facing reason is that multi-candidate instance ambiguity remains an unprocessed semantic uncertainty family, while source-pool repair and object-relation evidence have already produced terminal-blocking or backend-blind-spot outcomes.
63. Treat the frozen `instance_arbitration_evidence_v1` contract as novelty-defense scaffolding, not paper evidence: it fixes all selected instance-arbitration rows as request/candidate/pair evidence with request rows `9`, candidate refs `51`, unordered candidate pair rows `121`, and minimum observation rows `172`. The reviewer-facing design choice is that repeated-instance semantic uncertainty must be tested with pair-level active evidence, while source-top, detector-score, semantic-rank, own-support, local-context-only, category-only merge, threshold tuning, candidate commit/rejection, terminal utility, `first_eval`, policy-scale comparison, and paper claims remain blocked.
64. Treat the Docker-verified `instance_arbitration_evidence_v1` materializer/planner as substrate evidence only: it writes request/candidate/pair/artifact/observation rows `9/51/121/7/172`, pair probe counts `pair_common_view 57` and `pair_dual_standoff_fallback 64`, skipped rows `0`, action forbidden keys `0`, terminal commits `0`, and candidate commit/rejection rows `0/0`. The reviewer-facing next question is whether frame/projection and detector evidence can make repeated-instance arbitration observable without turning detector score, semantic rank, local-context support, or source-top position into a shortcut commit.
65. Treat the Docker-verified `instance_arbitration_evidence_v1` frame/projection smoke as renderability evidence only: it exports frame rows/headings `172/1012`, keeps nonblank rows/headings `172/1012`, has projection visible rows/rate `172/1.0`, missing candidates `0`, explicit candidate-id rows `172`, and GT action rows `0`. The reviewer-facing next question is whether detector/SAM2 evidence can provide pair-level instance evidence without collapsing into score/rank/local-context shortcut arbitration.
66. Treat the Docker-verified instance-arbitration detector/SAM2 substrate as analyzer-enabling evidence only: it has frame/detector rows `172/172`, detector box/SAM2/candidate association `1.0/1.0/0.8081`, rows with candidate association `139`, associated candidate heading count `483`, association rows `1820`, and GT action rows `0`. The reviewer-facing question is whether repeated-instance uncertainty can be decomposed into own-view support, source-top contrast, local-context contrast, pair support, and rival leakage, not whether `GroundingDINO + SAM2` can produce boxes and masks.
67. Treat the frozen `instance_arbitration_detector_evidence_v1` contract as the next novelty-defense mechanism test: it requires view/candidate/pair/request evidence rows `172/51/121/9`, blocks terminal commits and candidate commit/rejection, and rejects detector-score, SAM2-presence, any-association, source-top, own-view-only, local-context-only, and pair-support-only shortcut rules. A promotable branch outcome can only unlock a separate terminal utility contract; it cannot directly unlock `first_eval`, policy-scale comparison, or paper claims.
68. Treat the Docker-verified instance-arbitration post-detector analyzer as terminal-blocking failure taxonomy: it passes the nonterminal gate with rows `172/51/121/9/9`, but candidate statuses are `ambiguous_rival_leakage_candidate 32`, `contradicted_by_pair_or_contrast_evidence 18`, and `partial_instance_support 1`, while pair statuses include `ambiguous_both_candidates_supported 36` and `ambiguous_no_candidate_support 25`. Promotable branch outcome rows are `0`, so the reviewer-facing next step is residual mechanism diagnosis rather than terminal utility or policy-scale evaluation.
69. Treat the Docker-verified instance-arbitration residual diagnostic as method-derivation signal, not utility evidence: it classifies candidate/pair/request rows `51/121/9`, with candidate residual classes dominated by rival leakage and pair/contrast contradiction, and pair residual classes dominated by nonterminal one-sided support plus common-view overlap. It finds pair-graph follow-up signal in `9/9` requests, but `7/9` have multiple lossless graph candidates and `2/9` unique candidates are still blocked by common-view overlap. The next reviewer-defense step is a nonterminal pair-graph consistency contract that forbids `commit_graph_winner`, not a terminal rule.
70. Treat the frozen pair-graph consistency follow-up contract as shortcut rejection, not utility evidence: it fixes lossless/max-pair-winner candidate memberships `17/14`, unique/multiple lossless request rows `2/7`, expected promotable branch outcomes `0`, and blocks `commit_graph_winner`, `commit_lossless_candidate`, `commit_max_pair_win_candidate`, candidate rejection by pair loss, terminal utility, `first_eval`, policy-scale comparison, and paper claims. The reviewer-facing value is method derivation: pair graph signal exists, but graph winners are not goal-validity authority under common-view overlap and rival leakage.
71. Treat the Docker-verified pair-graph consistency follow-up analyzer as branch-closing shortcut audit: it writes candidate/pair/request graph rows `51/121/9` and shortcut audit rows `357`, with request statuses `multiple_lossless_pair_graph_candidates_unresolved 7` and `unique_lossless_candidate_blocked_by_common_view_overlap 2`. Graph-winner, lossless-candidate, max-pair-win, source-top-lossless, detector-strong-lossless, and pair-loss rejection shortcuts all remain blocked; promotable branch outcome rows are `0`. The next novelty-defense move is closing this instance-arbitration pair-graph branch or selecting a different label-free evidence family, not terminal utility.
72. Treat the Docker-verified pair-graph branch closure as reviewer-defense taxonomy, not a method utility result: it closes branch/request/candidate/pair/shortcut rows `1/9/51/121/357`, preserves terminal commits `0`, candidate commit/rejection `0/0`, and `uses_gt_for_action false`, and records that graph winners/lossless candidates remain blocked by multiple lossless candidates, common-view overlap, rival leakage, no-support pairs, and pair-loss shortcuts. The next paper action is selecting another label-free evidence family; terminal utility remains blocked until a new family produces a promotable branch outcome.
73. Treat the Docker-verified post-instance-arbitration selector as a Step 4-5 direction choice, not paper evidence: source-pool repair, object-relation/missing-own-view branches, and instance-arbitration pair-graph closure together produce semantic branch promotable rows `0`, so the selector chooses `semantic_slam_map_pose_consistency_probe_v1` with next action `freeze_semantic_slam_map_pose_consistency_probe_contract`. This strengthens the novelty direction only if the next contract measures map/pose-side uncertainty with `SemanticOnly`, `SLAMOnly`, and `SemanticSLAM` comparisons; it does not unlock terminal utility, `first_eval`, policy-scale comparison, or paper claims.
74. Treat the frozen `semantic_slam_map_pose_consistency_probe_v1` contract as `P4-design` only: it confirms a primary source with frame rows/headings `172/1012` and RGB/depth/pose/metadata files `1012/1012/1012/1012`, but it has not run a pose graph proxy, `SLAMOnly`, or `SemanticSLAM` comparison. The reviewer-facing value is that the next method axis is now map/pose-side uncertainty rather than another semantic object shortcut; no SLAM benefit, policy utility, or paper claim is allowed until the source audit and later proxy gate pass.
75. Treat the Docker-verified semantic-SLAM source audit as proxy-readiness evidence, not a SLAM result: it inventories `5` label-free frame sources and writes `50` probe request rows plus `50` pose graph proxy rows with source audit and P4 proxy readiness gates passing, while terminal/candidate commit/rejection rows remain `0/0/0`. This led to the stricter pose graph connectivity proxy gate in action 76; it still does not unlock Step 4-5 promotion, `SLAMOnly`, `SemanticSLAM`, policy-scale comparison, or paper claims.
76. Treat the Docker-verified pose graph connectivity proxy gate as a P4-design gate, not a Step 4-5 result: dependency, proxy plumbing, edge quality, and action safety gates pass on `50` proxy rows with spatial-or-loop edges on `46/50` rows and candidate-overlap-only rows `4/50`, but `candidate_id_overlap` still contributes `57.46%` of edge reasons. The next novelty-defense step is strict edge variant analysis; `SemanticOnly`, `SLAMOnly`, `SemanticSLAM`, terminal utility, policy-scale comparison, and paper claims remain blocked.
77. Treat the Docker-verified strict edge variant proxy as a shortcut-objection gate, not a method result: recomputing from label-free frame rows yields `350` variant rows across `50` request groups, and the canonical `pose_spatial_or_loop` variant stays ready on `46/50` groups after excluding `candidate_id_overlap`, with minimum source ready rate `0.8095`. This allows a `SemanticOnly` / `SLAMOnly` / `SemanticSLAM` proxy comparison contract to be defined, but the comparison run, Step 4-5 promotion, terminal utility, policy-scale comparison, and paper claims remain blocked.
78. Treat the frozen `semantic_slam_proxy_comparison_v1` contract as ablation setup, not result evidence: it fixes the same `50` request groups, four policies (`NoReobserveReference`, `SemanticOnly`, `SLAMOnly`, `SemanticSLAM`), separated input channels, fixed utility formulas, expected future rows `200`, and blocked task-behavior metrics. It allows Docker implementation of the proxy comparison, but does not unlock Step 4-5 promotion, terminal utility, policy-scale comparison, or paper claims.
79. Treat the Docker-verified `semantic_slam_proxy_comparison_v1` implementation as a negative complementarity diagnostic, not a Step 4-5 result: it writes `200` comparison rows and `4` policy summary rows on the same `50` request groups with no GT action leakage, no terminal commits, and no candidate commit/rejection rows; the proxy gate passes with canonical/loop ready rates `0.92/0.72`. However, `SemanticSLAM` has rank-1 rows/rate `0/0.0`, while `SemanticOnly` has `36/0.72` and `SLAMOnly` has `14/0.28`, so the current fixed combined utility cannot support a reviewer-facing complementarity claim. The next paper action is to evaluate whether the failure is weight design, SLAM proxy coarseness, task-behavior decoupling, or request-pool composition.
80. Treat the Docker-verified proxy output evaluation as a design rejection for midpoint utility: it confirms all `50/50` request groups are `semantic_slam_midpoint_strictly_dominated_by_best_component`, with `SemanticSLAM` equal to the midpoint of `SemanticOnly` and `SLAMOnly` up to floating-point error `1.11e-16`. This is a useful novelty-defense result because it prevents a weak paper claim based on module combination. The next reviewer-facing design must be non-dominated: it should introduce a real interaction, constraint, or outcome-linked SLAM term rather than linear interpolation between component utilities.
81. Treat the frozen `semantic_slam_non_dominated_proxy_redesign_v1` contract as a method-design guard, not evidence: it defines `SemanticSLAMInteraction`, forbids midpoint-only interpolation, component-max selection, constant bonus tricks, and label-tuned weight search, and requires non-dominated diagnostic rows before any further claim. The reviewer-facing value is that the method is now constrained by a failure mechanism: semantic and map/pose pressure must interact, rather than being a module list or a weighted average.
82. Treat the Docker-verified `SemanticSLAMInteraction` implementation as a proxy-design pass, not a Step 4-5 result: it writes comparison/policy/diagnostic rows `200/4/50`, has no midpoint identity rows or component-max shortcut rows, and produces non-dominated interaction rows/rate `42/0.84` with no GT action leakage. The next reviewer-defense question is whether `42/50` interaction rank-1 rows indicate real complementarity or a too-permissive semantic-first bonus; no paper claim is allowed until this proxy output is linked to task/map outcomes.
83. Treat the Docker-verified `SemanticSLAMInteraction` output evaluation as a reviewer-defense rejection of the current additive proxy: it writes `50` group evaluation rows and shows that `SemanticSLAMInteraction` strictly exceeds `SemanticOnly` on all `50/50` groups, while rank-1 rows/rates are `SemanticSLAMInteraction 42/0.84`, `SLAMOnly 8/0.16`, and `SemanticOnly 0/0.0`. This is not a midpoint failure, but it is a semantic-first shadowing failure: the current interaction bonus can make the combined policy look dominant without task/map outcome evidence. The next paper-facing method design must add a stricter cap, a richer SLAM proxy, or direct task/map outcome validation before any Step 4-5 or paper claim.
84. Use richer SLAM/outcome-linked proxy as the primary next path, not cap-only tuning: a non-shadowing cap is required as a reviewer-defense guard, but it is too weak to be a contribution by itself. Direct task/map validation of the current additive proxy is also premature because it would test a known semantic-first shadowing design. The next paper-facing contract should require that any `SemanticSLAMInteraction` gain over `SemanticOnly` is explained by independent map/pose evidence and later validated with at least one map-side metric and one task-side metric.
85. Treat the frozen `semantic_slam_reviewer_defense_v1` contract as method-derivation guard, not evidence: it replaces the current additive interaction with a four-policy comparison (`NoReobserveReference`, `SemanticOnly`, `SLAMOnlyRich`, `SemanticSLAMInteractionGuarded`) and requires map/pose-side explanation terms such as fragmentation, largest-component gap, loop gap, source coverage gap, and context gap. The reviewer-facing value is that it turns the shadowing failure into a falsifiable design rule: the next implementation must not be `SemanticOnly + nonnegative bonus` on every row, and it must fail if interaction rank-1 or semantic shadowing remains high without outcome evidence.
86. Treat the Docker-verified `semantic_slam_reviewer_defense_v1` implementation as a negative-but-useful reviewer-defense result, not a Step 4-5 promotion: it writes comparison/policy/diagnostic rows `200/4/50`, keeps action leakage and terminal commits at `0`, reduces the prior all-row `SemanticOnly` shadowing to `40/50`, and keeps guarded interaction rank-1 at `37/50 = 0.74`, but the reviewer-defense gate fails because `SLAMOnlyRich` rank-1 rows are only `3`, below the frozen minimum `5`. The paper-facing implication is that the current proxy is less shortcut-prone than the additive interaction, but independent map/pose utility is still underpowered; this led to the dedicated `SLAMOnlyRich` failure diagnostic, not a paper claim, weight tuning, `first_eval`, or policy-scale comparison.
87. Treat the Docker-verified reviewer-defense output evaluation as the blocker taxonomy for the next design step: action-safety and comparison gates pass, but `SLAMOnlyRich` has rank-1 rows `3/50` against required `5/50`, with blocker classes `semantic_wins_but_guarded_interaction_adds_small_map_pose_bonus 29`, `semantic_wins_with_weak_map_pose_proxy 17`, `slam_only_wins_but_insufficient_count 3`, and `interaction_overrides_slam_component 1`. This blocks Step 4-5 promotion because independent map/pose utility is not yet strong enough; the follow-up diagnostic now rejects scale-only tuning and makes outcome-linked map/pose evidence the next contract requirement.
88. Treat the Docker-verified `SLAMOnlyRich` underpowered diagnostic as a scale-tuning rejection, not a formula-change permission: it writes diagnostic/query/scene rows `50/6/9`, confirms `SLAMOnlyRich` rank-1 rows/rate `3/0.06`, and attributes the failure mainly to `map_pose_terms_saturated 19`, `weak_map_pose_proxy 17`, and `near_miss_scale 8`. The reviewer-facing implication is that a simple weight increase would be weak novelty and likely overfit the current source. The next paper action is to freeze a revision contract requiring outcome-linked map/pose evidence before any revised `SemanticSLAM` utility is implemented.
89. Treat the frozen `SLAMOnlyRich` revision contract as a method-derivation guard, not an implementation result: it explicitly forbids scale-only tuning, semantic score weakening, request-pool tuning, candidate-overlap pose evidence, and GT action labels. The next reviewer-facing work is a small task/map outcome probe that predeclares at least one map-side metric and one task-side metric before any revised `SLAMOnlyRich` formula is implemented.
90. Treat the frozen task/map outcome probe contract as the bridge from proxy design to evidence, not as evidence itself: it fixes the same `50` request groups, baselines `NoReobserveReference`, `SemanticOnly`, and `SLAMOnlyRich_current`, map-side metrics `pose_graph_connectivity_delta` and `map_pose_consistency_delta`, and task-side proxies `wrong_goal_visit_proxy_delta` and `wasted_path_proxy_delta`. The next reviewer-facing implementation must show whether strict map/pose evidence aligns with task behavior before any `SLAMOnlyRich` formula revision, Step 4-5 promotion, terminal utility, or paper claim.
91. Treat the Docker-verified task/map outcome probe implementation as a measurement-blocker result, not a `SemanticSLAM` benefit: it writes probe/policy/failure rows `150/3/50`, keeps action leakage and terminal/candidate commits at `0`, and shows `SLAMOnlyRich_current` map-positive rows `50/50`, but label-backed task proxy rows are `0/50` and map-task alignment rows are `0`. The paper-facing implication is that map-side deltas alone cannot be presented as navigation utility. The next reviewer-defense contract must define separated label-backed `wrong_goal_visit` and `wasted_path` joins before any formula revision or Step 4-5 claim.
92. Treat the Docker-verified task label join materializer as measurement plumbing, not contribution evidence: it writes request/candidate/policy/failure rows `21/113/150/150`, joins all `150` policy rows to the primary evaluation-only label backbone, and passes the label join gate with action leakage `0`. However, `task_proxy_evaluable_rows` remains `0` because `policy_selector_missing` is `150`. The next reviewer-defense step is a non-GT policy selector contract; do not claim ObjectNav utility, SLAM benefit, SemanticSLAM complementarity, or formula validity from label coverage alone.
93. Treat the frozen non-GT task policy selector contract as a shortcut-rejection gate, not utility evidence: it defines `NoReobserveReference` from source-top direct commit and `SemanticOnly` from unique local-context / own-view support, but explicitly marks `SLAMOnlyRich_current` as candidate-specific selector-missing on all `50` source rows. This is important for top-tier framing: a row-level map/pose score cannot be presented as a navigation decision by substituting source-top, semantic-top, detector-best, local-context, or `evaluation_only_variant_outcomes`. Formula revision requires a separate candidate-specific SLAM/map-pose selector contract.
94. Treat the Docker-verified task policy selector materializer as measurement plumbing, not contribution evidence: it writes selector/failure rows `150/60`, makes `NoReobserveReference` and `SemanticOnly` task proxies evaluable with terminal commit proxy rows `49/50` and `41/50`, and keeps action leakage `0`. It also keeps `SLAMOnlyRich_current` selector-missing on `50/50` rows, so it strengthens the reviewer defense against semantic shortcut substitution but still cannot support a `SemanticSLAM` utility claim. The next novelty-defense step is a candidate-specific SLAM/map-pose selector contract.
95. Treat the frozen candidate-specific SLAM/map-pose selector contract as a shortcut-defense and measurement gate, not a `SLAMOnlyRich` formula: it confirms all `50` source request rows have label-free candidate-targeted frame geometry and defines `232` expected candidate feature rows, but the selector may commit only when exactly one candidate is strict candidate-map-pose-ready. Multiple geometry-ready candidates must defer rather than falling back to semantic rank, detector score, source-top, local-context, or evaluation labels. Formula revision remains blocked until geometry-only selection shows nontrivial task/map alignment without increasing wrong-goal or wasted path.
96. Treat the Docker-verified candidate-specific SLAM/map-pose selector materializer as an ambiguity diagnosis, not utility evidence: it writes candidate/request/failure rows `232/50/50`, removes `SLAMOnlyRich_current` selector-missing rows (`0/50`), and keeps action leakage `0`, but all `232` candidates are strict map-pose-ready, so only `3` single-candidate requests commit and `47` multi-ready requests defer. This strengthens novelty framing: current map/pose evidence is mostly availability evidence, not discriminative goal-candidate evidence. The next reviewer-defense step is task-proxy join to test whether the `3` geometry-only commits have any useful wrong-goal / wasted-path / map-task alignment signal before any formula revision.
97. Treat the Docker-verified candidate-specific task proxy join as a measurement gate pass and formula gate failure: it writes policy/failure rows `150/100`, makes all `150` policy decisions decision-evaluable, removes selector-missing rows, and keeps action leakage `0`. `SLAMOnlyRich_current` has terminal/success/wrong/defer/map-task-alignment rows `3/2/1/47/2`, while `NoReobserveReference` and `SemanticOnly` have terminal/success/wrong rows `49/28/21` and `41/20/21`. The reviewer-facing implication is negative but useful: geometry-only candidate map/pose evidence reduces wrong-goal exposure by deferring, but it is too sparse to claim active SLAM/navigation utility. The next paper action is a safe-but-sparse diagnostic for label-free candidate separability, not a `SLAMOnlyRich` formula revision.

## Promotion Rule

Paper writing can start only when the following sentence can be backed by logs, metrics, and ablations:

> Because semantic map failures arise from measurable uncertainty in object evidence, viewpoint coverage, and map/pose consistency, H001 converts those uncertainty terms into active re-observation utility and reduces wrong-goal commitment without hiding the cost in longer paths.

Until then, H001 remains a hypothesis and harness-building effort, not a finished paper contribution.
