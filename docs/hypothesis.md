# Hypothesis Workflow

이 문서는 현재 연구 후보를 검증 가능한 hypothesis로 바꾸는 에이전트 workflow와 작성 규칙을 정의한다. 실제 hypothesis 내용은 루트의 `hypothesis/` 폴더에 저장한다.

## Storage Rule

Hypothesis 관련 산출물은 루트의 `hypothesis/` 폴더에 저장한다.

- workflow와 작성 규칙: `docs/hypothesis.md`
- hypothesis index: `hypothesis/README.md`
- candidate별 hypothesis 묶음: `hypothesis/CAND-<number>/`
- 개별 hypothesis: `hypothesis/CAND-<number>/H<number>_<short-title>/`
- 작업 계획과 진행 상태: `TODO.md`

`docs/hypothesis.md`는 절차와 기준만 관리한다. 문제 정의, hypothesis, feasibility gate, first experiment shape는 `hypothesis/` 아래에 기록한다.

이 repo는 기존 `literature/CAND-01.md` 표기와 맞춰 candidate folder를 `CAND-01`, `CAND-02`처럼 두 자리 번호로 쓴다.

## Entry Context

Hypothesis 작업을 시작하는 에이전트는 아래 순서로 읽는다. 없는 파일은 건너뛰고, 있는 파일의 최신 내용을 우선한다.

1. `AGENTS.md`
2. `README.md`
3. `TODO.md`
4. `docs/index.md`
5. `docs/literature.md`
6. `docs/hypothesis.md`
7. `literature/README.md`
8. `literature/PAPER.md`
9. `literature/Contribution Candidates.md`
10. `literature/CAND-01.md`
11. `hypothesis/README.md`
12. 대상 candidate folder의 `README.md`
13. 대상 hypothesis folder의 `README.md`

## Phase Gate

Hypothesis 단계로 넘어간다는 뜻은 thesis direction을 확정한다는 뜻이 아니다. 다음 조건을 만족하는지 검증 가능한 문장으로 압축하는 단계다.

- 기존 한계가 primary source로 뒷받침된다.
- 왜 semantic mapping 문제인지 설명된다.
- 왜 robot mobility / active re-observation 문제인지 설명된다.
- SLAM uncertainty 또는 navigation uncertainty와의 연결이 있다.
- dataset / benchmark / metric / baseline 후보가 있다.
- 실패했을 때 배울 수 있는 것이 명확하다.
- 첫 probe와 확장 실험이 6개월-1년 석사 연구 범위에서 실행 가능한 단계로 나뉜다.

## Scope Rule

Hypothesis 단계는 full reproduction이나 full dataset 검증 단계가 아니다. 이 단계의 목표는 논문으로 발전할 가능성이 있는지 빠르게 확인하는 것이다.

- full dataset 사용을 요구하지 않는다.
- 기존 논문 전체 재현을 요구하지 않는다.
- 작은 subset, one-scene replay, before/after probe, synthetic perturbation을 허용한다.
- 단, metric, baseline, failure interpretation은 반드시 있어야 한다.
- 논문으로서의 가치 검증이 충분히 완료되기 전에는 `docs/experiments.md`로 넘어가지 않는다.
- Hypothesis 단계의 probe 설계, dataset/replay 접근성 판단, baseline 후보, metric 정의는 모두 `hypothesis/` 아래에 기록한다.
- 좋은 결과가 나오고 논문 발전 가능성이 확인되면 그때 `docs/experiments.md`에서 full experiment contract로 승격한다.
- 나쁜 결과가 나오면 왜 안 되는지 기록하고 candidate를 수정하거나 보류한다.
- 현재 연구의 planning horizon은 6개월-1년이다. 단기 최소 실험만으로 연구 범위를 제한하지 않는다.

## Natural Proof Rule

Hypothesis는 원하는 결론을 증명하기 위해 뒤에서 맞추는 문장이 아니라, 문제 원인에서 자연스럽게 나오는 검증 가능한 주장이어야 한다.

- hypothesis는 기존 failure mechanism에서 도출한다.
- method 형태는 "이렇게 하면 좋아질 것"이 아니라 "이 원인 때문에 이 intervention이 필요하다"로 설명한다.
- metric, baseline, split, threshold는 가능한 한 probe 실행 전에 적는다.
- 결과가 기대와 다르면 metric, threshold, baseline을 바꾸어 hypothesis를 살리지 않는다.
- 기대와 다른 결과는 failure mechanism, scope reduction, deferred claim, 또는 새 hypothesis로 기록한다.
- 증거가 아직 약하면 paper claim이 아니라 diagnostic hypothesis로 유지한다.
- first falsification path가 없는 hypothesis는 아직 experiment-ready가 아니다.

## Current Research Scope

현재 primary candidate는 `literature/CAND-01.md`의 `Semantic-SLAM Uncertainty-aware Active Re-observation for Adaptive Navigation`이다.

Hypothesis는 아래 Step 1-5 중 어디까지 검증하는지 명시해야 한다.

- Step 1: pre-explored semantic map의 object/node uncertainty 계산
- Step 2: uncertain candidate에 대한 active re-observation viewpoint 선택
- Step 3: ObjectNav에서 `Success Rate`, `SPL`, wrong-goal visit, wasted path 평가
- Step 4: semantic memory를 SLAM uncertainty-aware active utility로 확장
- Step 5: map error, semantic accuracy, ATE/RPE, pose graph connectivity 평가

현재 최종 연구 방향은 Step 5까지 포함한다. H001 같은 umbrella hypothesis는 Step 1-5 전체를 hypothesis로 포함해야 한다. Step 1-3은 first probe로 사용할 수 있지만, Step 4-5를 별도 hypothesis로 분리하지 않는다. Step 4-5는 H001의 extension gate와 full experiment contract에서 확장한다.

## Hypothesis Folder Convention

```text
hypothesis/
  README.md
  CAND-01/
    README.md
    H001_<short-title>/
      README.md
      01_problem.md
      02_hypothesis.md
      03_feasibility.md
      04_first_experiment.md
      05_uncertainty_features.md
      06_logging_schema.md
      07_evaluation_contract.md
      08_runtime_integration.md
      15_schedule.md
```

폴더명 규칙:

- candidate folder는 `CAND-<number>`를 사용한다.
- 현재 repo에서는 `CAND-01`처럼 두 자리 번호를 사용한다.
- hypothesis folder는 `H<number>_<short-title>`을 사용한다.
- short title은 짧고 핵심 단어 중심으로 쓴다.
- 아직 hypothesis가 확정되지 않았으면 빈 `H<number>_...` 폴더를 만들지 않는다.

## File Roles

### `hypothesis/README.md`

전체 hypothesis index를 관리한다.

```md
# Hypotheses

## Active Candidate

## Hypothesis Registry

## Promotion Criteria

## Deferred Candidates
```

### `hypothesis/CAND-<number>/README.md`

candidate별 hypothesis 후보 묶음을 관리한다.

```md
# CAND-<number>

## Candidate Summary

## Source Literature

## Hypothesis Queue

## Current Gate
```

### `H<number>_<short-title>/README.md`

개별 hypothesis의 첫 진입점이다.

```md
# H<number>: <Short Title>

## Hypothesis

## Why This Is Testable

## First Experiment

## Current Status
```

### `01_problem.md`

문제 정의와 기존 한계를 기록한다.

```md
# Problem

## Facts

## Paper Claims

## Inferences

## Why This Is Not Solved Yet

## User Decision Needed
```

### `02_hypothesis.md`

한 문장 hypothesis와 falsification path를 기록한다.

```md
# Hypothesis

## Status

## Hypothesis Sentence

## Intervention

## Expected Measurable Effect

## Evaluation Target

## First Falsification Path
```

### `03_feasibility.md`

dataset, metric, baseline, implementation risk를 기록한다.

```md
# Feasibility

## Dataset / Benchmark

## Metrics

## Baselines

## Implementation Dependencies

## Risks

## Gate
```

### `04_first_experiment.md`

first probe contract, TODO, smoke result, sensitivity result, calibration coverage status를 기록한다.

```md
# First Experiment

## Goal

## Minimal Probe

## Data

## Metrics

## Baselines

## Success Criteria

## Failure Interpretation

## TODO
```

### `05_uncertainty_features.md`

semantic candidate uncertainty feature와 `U_sem` formula를 기록한다.

### `06_logging_schema.md`

`episodes.jsonl`, `candidate_decisions.jsonl`, `viewpoint_decisions.jsonl`, `summary.json` schema와 wrong-goal / wasted path 정의를 기록한다.

### `07_evaluation_contract.md`

benchmark, split discipline, metric, baseline, numeric gate, calibration interpretation rule을 기록한다.

### `08_runtime_integration.md`

Docker runtime, candidate backend, artifact generation, alignment, calibration execution command를 기록한다.

### `15_schedule.md`

6개월-1년 phase plan과 top-tier alignment check를 기록한다. Schedule은 별도 파일로 유지한다.

## Writing Rules

- "사실", "논문 주장", "에이전트 추론", "사용자 판단 필요"를 구분한다.
- hypothesis는 한 문장으로 쓴다.
- hypothesis에는 intervention, expected effect, evaluation target이 들어가야 한다.
- "좋아질 것이다"처럼 막연하게 쓰지 않는다.
- metric이 없는 hypothesis는 아직 hypothesis가 아니다.
- baseline이 없는 hypothesis는 아직 experiment-ready가 아니다.
- 구현 아이디어보다 first falsification path를 먼저 쓴다.
- Step 1-5 전체를 목표로 하되 first experiment는 작은 falsifiable probe로 쓴다.
- real-world deploy는 first probe가 아니라 system validation으로 둔다.
- 기간 기준은 6개월-1년으로 둔다. 단기 가능성만을 hypothesis gate로 쓰지 않는다.
- hypothesis를 살리기 위해 결과 해석을 사후적으로 바꾸지 않는다. 문제 원인에서 method와 metric이 자연스럽게 연결되지 않으면 candidate를 줄이거나 보류한다.

## Hypothesis Template

```md
# H<number>: <Short Title>

## Status

Draft / Candidate / Experiment-ready / Deferred

## Facts

## Paper Claims

## Inferences

## Hypothesis

If <intervention>, then <expected measurable effect> on <task/benchmark>, compared with <baseline>.

## Why This Is Semantic Mapping

## Why This Is Active Robotics

## Dataset / Benchmark

## Metrics

## Baselines

## First Experiment Shape

## What Failure Teaches

## User Decision Needed
```

## Promotion Criteria

Draft hypothesis를 experiment-ready로 올리려면 다음을 만족해야 한다.

- 최소 6개 primary source와 연결된다.
- benchmark 또는 small probe 후보가 1개 이상 있고 접근 가능성을 판단했다.
- metric 2개 이상이 있다. 하나는 map quality, 하나는 task behavior와 연결한다.
- baseline 2개 이상이 있다.
- 실패 시 해석이 최소 2갈래 이상으로 나뉜다.
- hypothesis folder 안에서 first probe contract와 가치 판단 기준이 작성되어 있다.
- failure mechanism에서 method 형태가 자연스럽게 도출되는지 설명되어 있다.
- metric, baseline, threshold가 사전에 정리되어 있고 사후 fitting 금지가 명시되어 있다.
- 논문으로서의 가치 검증이 끝난 뒤 `docs/experiments.md`로 옮길 수 있다.
