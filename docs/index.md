# Research Docs

이 문서는 연구 문서의 첫 진입점이다. `docs/` 안의 workflow 문서와 주요 연구 산출물을 빠르게 찾기 위해 사용한다.

## How to Use

1. 현재 작업 상태는 먼저 [TODO.md](../TODO.md)에서 확인한다.
2. 연구 운영 규칙은 [AGENTS.md](../AGENTS.md)를 따른다.
3. 문헌 조사 작업은 [literature.md](literature.md)를 읽고 [literature/README.md](../literature/README.md)와 [literature/PAPER.md](../literature/PAPER.md)로 이동한다.
4. contribution candidate 검토는 [Contribution Candidates.md](../literature/Contribution%20Candidates.md)와 [CAND-01.md](../literature/CAND-01.md)를 본다.
5. hypothesis 작업은 [hypothesis.md](hypothesis.md)를 읽고 [hypothesis/README.md](../hypothesis/README.md)로 이동한다.
6. paper novelty와 top-tier framing은 [paper.md](paper.md)를 따른다.
7. 재현을 위한 데이터, checkpoint, Docker, artifact 위치는 [reproducibility.md](reproducibility.md)에서 확인한다.
8. 현재 연구 보고서 형태의 요약은 [summary.md](../summary.md)에서 확인한다.

## Workflow Docs

| Workflow | Rule Document | Output Location | Role |
| --- | --- | --- | --- |
| Literature | [literature.md](literature.md) | [literature/](../literature/README.md) | field map, paper registry, contribution candidate 관리 |
| Hypothesis | [hypothesis.md](hypothesis.md) | [hypothesis/](../hypothesis/README.md) | candidate를 검증 가능한 hypothesis와 first probe로 압축 |
| Paper | [paper.md](paper.md) | `summary.md`, H001 documents | novelty gate, top-tier framing, paper-ready claim 판단 |
| Reproducibility | [reproducibility.md](reproducibility.md) | `local_dataset/{data,models,runs}` with `/tmp/research3-*` compatibility symlinks | 데이터, checkpoint, Docker, Drive 백업 경로, 재현 명령, artifact/evaluation 요약 |
| Dense Conflict Validation | [workflow-20260521-dense-conflict.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md) | H001 runtime workflow | wrong/ambiguous positive-support dense validation 설계 |
| Stage 1 Smoke Test | [workflow-20260507-smoke.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-smoke.md) | H001 runtime workflow | `VLMaps` / Habitat smoke test |
| HM3D-OVON | [workflow-20260507-ovon.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-ovon.md) | H001 runtime workflow | HM3D-OVON episode 확보와 mount smoke test |

## Active Research Direction

### 사실

- 현재 primary candidate는 [CAND-01.md](../literature/CAND-01.md)의 `Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`이다.
- 현재 active hypothesis는 [H001_uncertainty-reobservation](../hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)에 있다.
- 최종 연구 방향은 Step 5까지 포함한다.
- 현재 implementation gate는 independent dense conflict validation이며, host NVIDIA runtime 복구 전까지 final dense artifact generation은 blocked다.
- Google Drive 백업 후보와 Drive 없이 재생성하는 절차는 [reproducibility.md](reproducibility.md)의 `Google Drive Backup Manifest`, `Restore from Drive`, `Rebuild Without Drive`를 따른다.

### 에이전트 추론

Step 1-3은 ObjectNav first probe이고, Step 4-5는 같은 H001 안에서 SLAM uncertainty와 map/pose consistency 평가로 확장한다. 별도 hypothesis를 미리 만들지 않고, positive signal이 확인되면 full experiment contract로 승격한다.

## Entry Order

새 작업을 시작하는 에이전트는 아래 순서로 읽는다.

1. `../AGENTS.md`
2. `../TODO.md`
3. `index.md`
4. `literature.md`
5. `hypothesis.md`
6. `paper.md`
7. `reproducibility.md`
8. `../literature/README.md`
9. `../literature/PAPER.md`
10. `../literature/Contribution Candidates.md`
11. `../literature/CAND-01.md`
12. `../hypothesis/README.md`

## Update Rules

- 새 workflow 문서가 생기면 이 파일의 `Workflow Docs`에 추가한다.
- 새 연구 산출물 folder가 생기면 관련 workflow 문서와 이 index에서 함께 연결한다.
- 긴 설명, paper summary, experiment detail은 이 파일에 넣지 않는다.
- 아직 필요하지 않은 `experiments/`, `paper/`, `decisions/` folder는 만들지 않는다.
- 루트에는 `AGENTS.md`, `.gitignore`, `README.md`, `TODO.md`, `summary.md`만 둔다.

## Index Page Convention

### 사실

- Markdown documentation site에서는 `docs/index.md`를 documentation home page로 두는 관례가 있다.
- contents page는 포함하는 문서의 overview와 link를 제공하는 역할을 한다.
- navigation page는 관련 문서로 이동하기 위한 link 중심 문서다.

### 에이전트 추론

이 repo의 `docs/index.md`는 documentation site home, workflow router, current research direction pointer 역할만 한다. 실제 연구 내용은 `literature/`와 `hypothesis/` 아래에 둔다.
