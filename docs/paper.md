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

## Promotion Rule

Paper writing can start only when the following sentence can be backed by logs, metrics, and ablations:

> Because semantic map failures arise from measurable uncertainty in object evidence, viewpoint coverage, and map/pose consistency, H001 converts those uncertainty terms into active re-observation utility and reduces wrong-goal commitment without hiding the cost in longer paths.

Until then, H001 remains a hypothesis and harness-building effort, not a finished paper contribution.
