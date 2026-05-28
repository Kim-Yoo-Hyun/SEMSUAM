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

1. Implement backend pool expansion evidence from `h001_expanded_retrieval_backend_pool_expansion_v1` for the five `request_backend_pool_expansion` rows.
2. Define goal-validity confirmation evidence only after backend expansion yields repaired or sufficiently valid candidate pools.
3. Keep terminal commits, `first_eval` rerun, and policy-scale comparison blocked until branch-specific evidence passes a fixed validation gate.
4. Preserve simpler alternatives as unsafe or inert baselines: direct re-ranking, detector-score best, source-top, own-support, local-context-only, and defer-all.
5. Write the failure taxonomy around source-pool validity, object visibility vs goal validity, and repeated-instance arbitration.
6. Promote only after a fresh or predeclared source shows nonzero safe utility over defer-all with wrong/no-valid commits still zero.

## Promotion Rule

Paper writing can start only when the following sentence can be backed by logs, metrics, and ablations:

> Because semantic map failures arise from measurable uncertainty in object evidence, viewpoint coverage, and map/pose consistency, H001 converts those uncertainty terms into active re-observation utility and reduces wrong-goal commitment without hiding the cost in longer paths.

Until then, H001 remains a hypothesis and harness-building effort, not a finished paper contribution.
