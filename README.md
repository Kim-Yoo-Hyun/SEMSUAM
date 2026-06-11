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

- Date checked: 2026-06-12
- Primary candidate: `CAND-01`
- Active hypothesis: `H001_uncertainty-reobservation`
- Current gate: terminal utility remains blocked; `rival_contradiction_region_contamination_multi_case_frame_projection_v1` is statically frozen as the next 72-row frame/projection smoke contract
- Current `Now`: [TODO.md](TODO.md)
- Active hypothesis entrypoint: [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)
- Current detailed workflow: [workflow-20260521-dense-conflict.md](hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md)

### 에이전트 추론

현재 연구 방향은 semantic uncertainty를 단순 confidence score가 아니라 active SLAM/navigation utility로 바꾸는 것이다. 최신 bounded detector/evidence/evaluation/promotion ladder는 `QaLdnwvtxbs/sofa/rival_identity:3` 한 행에서 mechanism probe를 통과했지만, 그 자체로 terminal utility나 paper claim은 허용하지 않는다. 새 multi-case frame/projection contract는 action-frozen source pool의 `18` pairwise conflict rows에서 나온 `72` observation seed rows를 Docker smoke 대상으로 고정했다. 다음 단계는 이 contract를 실제 Habitat frame/projection smoke로 구현한 뒤 detector/SAM2, post-detector evidence, evaluation-only join, promotion gate로 같은 no-GT-action discipline 아래 확장하는 것이다.

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
