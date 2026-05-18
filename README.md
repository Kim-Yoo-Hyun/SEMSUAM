# Research3

이 저장소는 석사 연구를 진행하고 최종 논문으로 발전시키기 위한 작업 공간이다.

## Start Here

처음 들어오면 아래 순서로 읽는다.

1. [AGENTS.md](AGENTS.md): 연구 운영 규칙과 에이전트 작업 규칙
2. [TODO.md](TODO.md): 현재 작업 상태, 다음 행동, 완료 이력
3. [docs/index.md](docs/index.md): 문헌 조사, hypothesis, workflow 문서로 이동하는 index

## Active Direction

현재 primary direction은 `CAND-01 / H001`이다.

중심 주장은 다음과 같다.

> semantic uncertainty가 active SLAM/navigation utility로 작동해서 ObjectNav 같은 navigation task에서 wrong-goal visit과 wasted path를 줄이고, 확장 단계에서는 map/pose consistency까지 개선할 수 있는지 검증한다.

## Key Documents

- Literature overview: [literature/README.md](literature/README.md)
- Paper registry: [literature/PAPER.md](literature/PAPER.md)
- Primary candidate: [literature/CAND-01.md](literature/CAND-01.md)
- Hypothesis index: [hypothesis/README.md](hypothesis/README.md)
- Active hypothesis: [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)
- Evaluation contract: [07_evaluation_contract.md](hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md)
- Research report summary: [summary.md](summary.md)

## Current Dataset Gates

The current Docker-based dataset gates are open for:

- HM3D v0.2 scene assets
- HM3D semantic annotations
- ObjectNav HM3D v2 episodes
- HM3D-OVON episodes

Runtime scripts, Dockerfiles, and smoke workflow notes live under:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/
```

## Repository Rule

The repository root is kept as an entrypoint only.

Root files should stay limited to:

- `AGENTS.md`
- `.gitignore`
- `README.md`
- `summary.md`
- `TODO.md`

Research details, workflow notes, runtime scripts, Dockerfiles, and experiment design documents should live under the relevant workflow or hypothesis folder.

## What Not To Do

- Do not create empty `experiments/`, `paper/`, `results/`, or `decisions/` folders in advance.
- Do not use host Python for smoke tests or implementation experiments.
- Do not treat GT oracle policies as deployable baselines.
- Do not mix facts, paper claims, agent inference, and user decisions in the same section.
