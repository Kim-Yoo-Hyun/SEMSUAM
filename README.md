# Research3

석사 연구를 진행하고 최종 논문으로 발전시키기 위한 연구 workspace다. 현재 중심 주제는 pre-explored semantic map의 uncertainty를 confidence score가 아니라 active SLAM/navigation utility로 바꾸는 것이다. H001은 `ObjectNav`에서 semantic goal ambiguity가 wrong-goal visit, wasted path, map/pose consistency 문제로 어떻게 드러나는지 검증한다. 현재 gate는 `candidate_conditioned_blocker_multi_case_validation_contract` freeze이며, terminal utility, policy-scale comparison, paper claim은 아직 blocked 상태다.

## 핵심 문제의식

Semantic map이나 detector evidence가 있어도 그것이 곧바로 ObjectNav goal validity를 보장하지 않는다. 따라서 본 연구는 semantic uncertainty를 `goal_validity_risk`, `viewpoint_evidence_gap`, `map_pose_consistency_uncertainty`로 분해하고, 이를 terminal score가 아니라 active re-observation action을 고르는 utility로 사용하는 방향을 검증한다.

## Repository Structure

```text
.
├── AGENTS.md                         # repo-level agent rules
├── README.md                         # repo entrypoint
├── TODO.md                           # Now / Next / Running / Recently Completed
├── summary.md                        # 연구 보고서형 요약
├── docs/                             # workflow, paper, reproducibility 기준
├── literature/                       # literature survey와 paper folders
├── hypothesis/                       # candidate/hypothesis별 실험 문서와 runtime code
│   └── CAND-01/H001_uncertainty-reobservation/
│       ├── README.md                 # H001 local entrypoint
│       ├── manifests/                # frozen contracts and verify files
│       └── runtime/                  # Docker-run scripts, runtime modules, workflows
├── local_dataset/                    # local data/model/run artifacts; GitHub source-of-truth 아님
└── logs/                             # legacy local logs; 새 job은 workflow-local logs 사용
```

## 실행 코드

핵심 runtime package는 `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/` 아래에 있다. 현재 재현 entrypoint는 [docs/reproducibility.md](docs/reproducibility.md)이며, 최신 Docker-verified materializer 예시는 아래와 같다.

```bash
export H001=hypothesis/CAND-01/H001_uncertainty-reobservation
export IMG=research3/openvocab-perception:20260513-v3c-gdino-sam2

docker run --rm --user "$(id -u):$(id -g)" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/$H001/runtime \
  -v "$PWD":/workspace:ro \
  -v "$PWD/local_dataset/runs":/runs \
  -w /workspace \
  "$IMG" \
  python -B -m h001_runtime.materialize_fully_covered_candidate_conditioned_contrast \
  --out-root /runs/h001_fully_covered_candidate_conditioned_contrast_v1

jq '{status, contrast_materializer_gate_passed, primary_blocker, next_task}' \
  local_dataset/runs/h001_fully_covered_candidate_conditioned_contrast_v1/fully_covered_candidate_conditioned_contrast_summary.json
```

논문 본문용 experiment와 smoke test는 Docker 기반 결과만 확정한다. Host Python은 문서 작업, 가벼운 파일 검증, Docker 실행 전 사전 점검에만 사용한다.

## Artifact 원칙

- `local_dataset/data`: dataset mount와 local dataset copy
- `local_dataset/models`: checkpoint와 model cache
- `local_dataset/runs`: generated run/evaluation artifacts
- 대용량 dataset, checkpoint, run artifact, Docker image layer는 GitHub source-of-truth가 아니다.
- 재현 가능한 artifact는 [docs/reproducibility.md](docs/reproducibility.md)의 다운로드, 빌드, 검증 명령으로 복구한다.
- 재생성 비용이 크거나 불가능한 artifact만 별도 backup 대상으로 분류한다.
- credential, access token, private dataset key는 repo에 저장하지 않는다.

## 읽는 순서

1. [AGENTS.md](AGENTS.md): repo rules, novelty 기준, Docker/reproducibility 원칙
2. [TODO.md](TODO.md): 현재 `Now`, `Next`, `Running`, `Recently Completed`
3. [docs/index.md](docs/index.md): 전체 문서 지도
4. [summary.md](summary.md): 연구 배경, 문제 정의, 핵심 가설, 실험 계획
5. [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md): H001 현재 상태와 local entrypoint
6. [docs/reproducibility.md](docs/reproducibility.md): data, checkpoint, Docker, result artifact 재현 방법
