# Experiment Workflow

이 문서는 hypothesis-stage probe가 논문 본문용 experiment로 승격될 때 적용할 workflow와 rule을 정의한다. 실제 experiment contract, script, artifact, result는 해당 hypothesis folder 아래에 둔다.

## Role

- `docs/experiments.md`는 full experiment 승격 기준과 운영 규칙만 관리한다.
- 실험별 세부 contract는 가까운 hypothesis runtime/workflow 문서에 둔다.
- 결과 요약은 가까운 hypothesis `README.md`, workflow 문서, 또는 `docs/reproducibility.md`에 둔다.
- 논문 claim 판단은 `docs/paper.md`를 우선 적용한다.
- Docker, dataset, checkpoint, artifact 복구 기준은 `docs/reproducibility.md`를 우선 적용한다.

## Entry Context

Experiment 작업을 시작하는 에이전트는 아래 순서로 읽는다.

1. `AGENTS.md`
2. `README.md`
3. `TODO.md`
4. `docs/index.md`
5. `docs/hypothesis.md`
6. `docs/experiments.md`
7. `docs/paper.md`
8. `docs/reproducibility.md`
9. 대상 hypothesis `README.md`
10. 대상 workflow 또는 experiment contract

## Promotion From Hypothesis

Hypothesis를 experiment로 승격하려면 아래 조건을 만족해야 한다.

- 검증할 hypothesis와 failure mechanism이 명확하다.
- intervention, baseline, metric, split, threshold가 사전에 정의되어 있다.
- 결과가 나쁘면 무엇을 배울 수 있는지 적혀 있다.
- paper claim이 아니라 experiment claim 단위로 승격한다.
- 최소 하나의 small probe 또는 smoke result가 implementation path를 지지한다.
- 논문 본문용 실험은 Docker 기반으로 재현 가능해야 한다.

## Natural Proof Rule

Experiment는 원하는 hypothesis를 증명하기 위해 evidence를 끼워 맞추는 과정이 아니다. 문제 원인에서 method 형태가 자연스럽게 도출되고, 실험은 그 원인이 실제 실패를 만든다는 점과 intervention이 그 원인을 줄인다는 점을 검증해야 한다.

- 실험 전 hypothesis, split, metric, baseline, threshold, failure interpretation을 기록한다.
- 결과를 본 뒤 metric 정의, threshold, baseline set을 바꾸어 positive claim을 만들지 않는다.
- 결과가 기대와 다르면 failure taxonomy, scope reduction, deferred claim, 또는 새 hypothesis로 기록한다.
- 단순 성능 개선보다 어떤 failure mode가 어떤 component 때문에 줄었는지 검증한다.
- `Success Rate` / `SPL` 개선만으로 contribution을 주장하지 않는다.
- map/pose degradation을 task metric 개선으로 숨기지 않는다.
- detector, segmenter, semantic memory, SLAM backend 조합 자체를 novelty로 쓰지 않는다.

## Experiment Contract

논문 본문용 experiment contract는 최소 아래 항목을 포함한다.

```md
# Experiment Contract

## Hypothesis

## Failure Mechanism

## Intervention

## Dataset / Benchmark

## Split

## Metrics

## Baselines

## Oracle References

## Ablations

## Predefined Thresholds

## Success Gate

## Failure Interpretation

## Docker Command

## Expected Artifacts

## Verification Command

## Blocked Claims
```

## Docker Rule

- 논문 본문용 experiment는 Docker 기반 결과만 확정한다.
- smoke test도 Docker 기반으로 수행한다.
- Host Python은 문서 작업, 가벼운 파일 검증, Docker 실행 전 사전 점검에만 사용한다.
- Docker image, dataset mount, model cache, command, output path, verification command를 contract에 기록한다.
- long-running job은 `AGENTS.md`의 background-task rule을 따른다.

## Result Interpretation

- "사실", "논문 주장", "에이전트 추론", "사용자 판단 필요"를 구분한다.
- 실패한 experiment도 failure mechanism을 설명하면 보존한다.
- positive result는 사전 gate를 통과했을 때만 claim으로 승격한다.
- gate를 통과하지 못한 결과는 diagnostic, negative result, blocker 중 하나로 기록한다.
- paper claim으로 승격하기 전 `docs/paper.md`의 novelty gate와 reviewer-defense 기준을 확인한다.
