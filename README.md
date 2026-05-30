# Research3

이 저장소는 석사 연구를 진행하고 최종 논문으로 발전시키기 위한 작업 공간이다.

## Start Here

처음 들어오면 `AGENTS.md`를 먼저 읽고, 이어서 이 README를 entrypoint로 사용한다. 이후 아래 순서로 현재 작업 맥락을 확인한다.

1. [TODO.md](TODO.md): 현재 `Now`, `Next`, `Running`, `Recently Completed`
2. [docs/index.md](docs/index.md): 전체 문서 지도
3. [docs/paper.md](docs/paper.md): novelty, paper framing, reviewer-defense 기준
4. [docs/reproducibility.md](docs/reproducibility.md): Docker, dataset, checkpoint, artifact 재현 기준
5. 현재 작업과 연결된 local `README.md` 또는 workflow 문서

## Active Direction

### 사실

- Date checked: 2026-05-30
- Primary candidate: `CAND-01`
- Active hypothesis: `H001_uncertainty-reobservation`
- Current gate: freeze object-relation post-detector evidence analyzer contract before terminal utility validation
- Current `Now`: [TODO.md](TODO.md)
- Active hypothesis entrypoint: [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)
- Current detailed workflow: [workflow-20260521-dense-conflict.md](hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md)

### 에이전트 추론

현재 연구 방향은 semantic uncertainty를 단순 confidence score가 아니라 active SLAM/navigation utility로 바꾸는 것이다. Paper-scale local-context detector/SAM2 substrate는 통과했지만 post-observation terminal rule은 wrong-goal/no-valid commit 때문에 실패했다. Route-specific analyzer는 source-pool repair, goal-validity confirmation, instance arbitration을 분리했고, backend expansion과 deeper generation은 `rival_identity:12`, `rival_identity:14`에서 valid candidates를 회복했다. `rival_identity:13`은 first/second fallback backend 모두에서 no-valid로 남아 `bxsVRursffK::bed` backend/source-map recall blind spot으로 기록한다. Candidate-specific goal-validity full substrate, ambiguity diagnostic, discriminative instance/goal-region analyzer, relation/spatial context analyzer, scene-graph/object-relation analyzer, object-relation coverage repair analyzer, object-relation observation planner, object-relation frame/projection smoke, and object-relation detector substrate are Docker-verified. The object-relation detector substrate has detector rows `8`, detector box/SAM2/candidate association `1.0/1.0/1.0`, associated heading count `48`, and `passes_detector_substrate_gate true`. The next gate is a post-detector evidence analyzer contract before terminal utility, `first_eval`, or policy-scale comparison.

## Key Documents

| Document | Role |
| --- | --- |
| [AGENTS.md](AGENTS.md) | repo 규칙, 작업 기대치, 파일 책임, novelty 기준 |
| [TODO.md](TODO.md) | 현재 작업 상태와 다음 행동 |
| [docs/index.md](docs/index.md) | 전체 문서 지도 |
| [docs/literature.md](docs/literature.md) | 문헌 조사 workflow |
| [docs/hypothesis.md](docs/hypothesis.md) | hypothesis 검증 workflow |
| [docs/paper.md](docs/paper.md) | paper framing, novelty, reviewer-defense 기준 |
| [docs/reproducibility.md](docs/reproducibility.md) | Docker, data, checkpoint, artifact 재현 기준 |
| [literature/README.md](literature/README.md) | cross-paper synthesis와 open questions |
| [hypothesis/README.md](hypothesis/README.md) | hypothesis index와 active gate |
| [summary.md](summary.md) | 연구 보고서형 요약 |

## Local Entry Points

- H001: [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)
- Runtime workflow: [workflow-20260521-dense-conflict.md](hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md)
- Reproducibility: [docs/reproducibility.md](docs/reproducibility.md)

## Repository Rule

루트는 entrypoint만 둔다. 세부 실험 결과, 긴 로그, dataset 기록, paper draft 내용은 가까운 workflow 문서나 local README에 둔다.

Root files should stay limited to:

- `AGENTS.md`
- `.gitignore`
- `README.md`
- `TODO.md`
- `summary.md`

## Docker And Artifacts

### 사실

- 논문 본문용 experiment와 implementation smoke는 Docker 기반으로 수행한다.
- Host Python은 문서 작업, 가벼운 파일 검증, Docker 실행 전 사전 점검에만 사용한다.
- Canonical local paths:

```text
local_dataset/data
local_dataset/models
local_dataset/runs
```

### 에이전트 추론

대용량 dataset, checkpoint, run artifact, Docker image archive는 GitHub source-of-truth가 아니다. 복구와 검증은 [docs/reproducibility.md](docs/reproducibility.md)를 따른다.
