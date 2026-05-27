# Research Docs

이 문서는 `docs/`와 주요 연구 산출물의 문서 지도다. 세부 실험 결과와 긴 판단 기록은 각 workflow 문서 또는 가까운 local `README.md`에 둔다.

## How To Use

1. repo-level 규칙은 [AGENTS.md](../AGENTS.md)를 따른다.
2. repo 상태와 핵심 파일 안내는 [README.md](../README.md)를 확인한다.
3. 현재 작업 상태는 [TODO.md](../TODO.md)의 `Now`와 `Next`를 확인한다.
4. 논문 novelty와 reviewer-defense 판단은 [paper.md](paper.md)를 우선 적용한다.
5. 재현, artifact, Docker 판단은 [reproducibility.md](reproducibility.md)를 우선 적용한다.
6. 현재 작업과 연결된 local `README.md` 또는 workflow 문서를 읽는다.

## Document Map

| Document | Responsibility | Output / Local Entry |
| --- | --- | --- |
| [literature.md](literature.md) | 문헌 조사 workflow와 paper folder convention | [literature/README.md](../literature/README.md), [literature/PAPER.md](../literature/PAPER.md) |
| [hypothesis.md](hypothesis.md) | hypothesis 검증 workflow와 promotion 기준 | [hypothesis/README.md](../hypothesis/README.md) |
| [paper.md](paper.md) | paper framing, novelty, reviewer-defense 기준 | `summary.md`, future `paper/README.md` |
| [reproducibility.md](reproducibility.md) | dataset, checkpoint, Docker, artifact, 백업/복구 기준 | `local_dataset/{data,models,runs}` |

## Active Workflows

| Workflow | Entry | Role |
| --- | --- | --- |
| H001 active hypothesis | [H001 README](../hypothesis/CAND-01/H001_uncertainty-reobservation/README.md) | active gate와 local 문서 안내 |
| H001 evaluation contract | [07_evaluation_contract.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md) | evaluation gate, metric, split discipline |
| H001 schedule | [15_schedule.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/15_schedule.md) | 6-12개월 단계 계획 |
| Dense conflict / expanded retrieval workflow | [workflow-20260521-dense-conflict.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md) | H001 runtime workflow와 세부 gate 기록 |
| Stage 1 smoke | [workflow-20260507-smoke.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-smoke.md) | `VLMaps` / Habitat smoke |
| HM3D-OVON | [workflow-20260507-ovon.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-ovon.md) | HM3D-OVON 확보와 mount smoke |

## Current State Pointer

### 사실

- Date checked: 2026-05-28
- Primary candidate: `CAND-01`
- Active hypothesis: `H001_uncertainty-reobservation`
- Current gate is tracked in [TODO.md](../TODO.md).
- Detailed current H001 state is tracked in [H001 README](../hypothesis/CAND-01/H001_uncertainty-reobservation/README.md).
- Reproduction and artifact paths are tracked in [reproducibility.md](reproducibility.md).

### 에이전트 추론

이 파일은 navigation map 역할만 한다. 실험 세부 결과, long-running job 기록, paper claim 판단, artifact 요약은 각각 H001 workflow, `docs/paper.md`, `docs/reproducibility.md`에 둔다.

## Update Rules

- 새 workflow 문서가 생기면 `Active Workflows`에 link만 추가한다.
- 새 top-level document가 생기면 `Document Map`에 책임을 짧게 추가한다.
- 긴 실험 설명은 이 파일에 쓰지 않는다.
- 아직 필요하지 않은 `experiments/`, `paper/`, `results/`, `decisions/` folder는 만들지 않는다.
