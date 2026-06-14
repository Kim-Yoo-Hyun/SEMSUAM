# Research3

이 repository는 pre-explored semantic map의 uncertainty를 active SLAM/navigation utility로 바꾸는 석사 연구 workspace다. 현재 H001은 `ObjectNav`에서 semantic goal ambiguity가 wrong-goal visit, wasted path, map/pose consistency 문제로 드러나는 지점을 검증한다. 최신 gate는 `candidate_conditioned_blocker_multi_case_validation_contract` freeze이며, terminal utility, policy-scale comparison, paper claim은 아직 blocked 상태다. 실행 가능한 핵심 코드는 `src/`, command wrapper는 `scripts/`, 고정 contract와 Dockerfile은 `configs/`에 둔다.

## 핵심 문제의식

Semantic map이나 detector evidence가 있어도 그것이 곧바로 ObjectNav goal validity를 보장하지 않는다. 본 연구는 semantic uncertainty를 `goal_validity_risk`, `viewpoint_evidence_gap`, `map_pose_consistency_uncertainty`로 분해하고, 이를 terminal score가 아니라 active re-observation action을 고르는 utility로 검증한다.

## Repository Structure

```text
.
├── AGENTS.md                  # repo-level rules
├── README.md                  # repo entrypoint
├── TODO.md                    # Now / Next / Running / Recently Completed
├── summary.md                 # 연구 보고서형 요약
├── docs/                      # workflow, paper, reproducibility 기준
├── literature/                # literature survey와 paper folders
├── src/                       # 핵심 Python runtime package
├── scripts/                   # Docker 실행 wrapper와 helper scripts
├── configs/                   # Dockerfile, H001 manifests, verify contracts
├── experiments/               # H001 hypothesis 문서, workflow, ablation 기록
├── results/                   # 가벼운 결과 요약과 table/log summary
└── archive/                   # raw logs, legacy/ambiguous material
```

## 핵심 실행 방법

현재 gate의 핵심 entrypoint:

```bash
bash scripts/run_fully_covered_contrast.sh

jq '{status, contrast_materializer_gate_passed, primary_blocker, next_task}' \
  local_dataset/runs/h001_fully_covered_candidate_conditioned_contrast_v1/fully_covered_candidate_conditioned_contrast_summary.json
```

직접 Docker command를 실행할 때는 `PYTHONPATH=/workspace/src`를 사용하고, H001 manifest는 `configs/h001/manifests/`에서 읽는다. 세부 재현 명령은 [docs/reproducibility.md](docs/reproducibility.md)를 따른다.

## Artifact 원칙

- `local_dataset/data`: dataset mount와 local dataset copy
- `local_dataset/models`: checkpoint와 model cache
- `local_dataset/runs`: generated run/evaluation artifacts
- 대용량 dataset, checkpoint, raw data, cache, run artifact, Docker image layer는 GitHub source-of-truth가 아니다.
- 재현 가능한 artifact는 [docs/reproducibility.md](docs/reproducibility.md)의 다운로드, 빌드, 검증 명령으로 복구한다.
- 재생성 비용이 크거나 불가능한 artifact만 별도 backup 대상으로 분류한다.
- credential, access token, private dataset key는 repo에 저장하지 않는다.

## 읽는 순서

1. [AGENTS.md](AGENTS.md): repo rules, novelty 기준, Docker/reproducibility 원칙
2. [TODO.md](TODO.md): 현재 `Now`, `Next`, `Running`, `Recently Completed`
3. [docs/index.md](docs/index.md): 전체 문서 지도
4. [summary.md](summary.md): 연구 배경, 문제 정의, 핵심 가설, 실험 계획
5. [experiments/h001_uncertainty-reobservation/README.md](experiments/h001_uncertainty-reobservation/README.md): H001 local entrypoint
6. [docs/reproducibility.md](docs/reproducibility.md): data, checkpoint, Docker, result artifact 재현 방법
