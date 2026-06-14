# AGENTS.md

이 파일은 agent entrypoint이자 연구 운영 규칙의 단일 source of truth다. Paper novelty 판단 기준은 `docs/paper.md`를 함께 따른다.

## Entry Order

에이전트는 이 파일을 먼저 읽은 뒤 아래 순서로 현재 작업 맥락을 확인한다.

1. `README.md`
2. `TODO.md`
3. `docs/index.md`
4. `docs/paper.md`
5. Current hypothesis or workflow document

## Document Responsibilities

- `AGENTS.md`는 repo-level project instruction이다. 세부 실험 기록을 담지 않고 작업 규칙, 파일 책임, novelty 기준, Docker/reproducibility 원칙만 정의한다.
- 루트 `README.md`는 repo 전체의 현재 상태와 핵심 파일 안내를 제공한다. 긴 실험 결과, dataset log, paper summary를 중복해서 쓰지 않는다.
- `TODO.md`는 `Now`, `Next`, `Running`, `Recently Completed`만 관리한다. 긴 설명은 가까운 workflow 문서나 local README에 둔다.
- `docs/index.md`는 전체 문서 지도다. 세부 연구 판단이나 실험 로그를 길게 보관하지 않는다.
- `docs/literature.md`는 문헌 조사 workflow와 작성 규칙을 관리한다. 문헌 조사 결과와 cross-paper synthesis는 `literature/README.md`에 둔다.
- `docs/hypothesis.md`는 hypothesis 검증 workflow와 promotion 기준을 관리한다. 실제 H001 hypothesis 상태는 `experiments/h001_uncertainty-reobservation/README.md`와 가까운 experiment workflow 문서에 둔다.
- `docs/paper.md`는 paper framing, novelty, reviewer-defense 기준을 관리한다. 논문 관련 판단은 이 문서를 우선 적용한다.
- `docs/reproducibility.md`는 데이터, checkpoint, Docker, artifact, 재현 명령, 백업/복구 기준을 관리한다. 실험 재현이나 artifact 관련 판단은 이 문서를 우선 적용한다.
- `src/`는 핵심 Python runtime package를 관리한다.
- `scripts/`는 Docker 실행 wrapper와 helper script를 관리한다.
- `configs/`는 Dockerfile, manifest, verify contract, 고정 설정을 관리한다.
- `experiments/`는 active hypothesis workspace, experiment workflow, ablation/analysis 기록을 관리한다.
- `results/`는 가벼운 결과 요약, table, log summary를 관리한다.
- `archive/`는 삭제가 애매하지만 shareable core path에서 제외한 legacy/raw material을 보존한다.
- 각 폴더의 `README.md`는 해당 폴더의 local entry point다.
- `literature/README.md`는 문헌 조사 결과의 field map, trend synthesis, cross-paper insight, open question을 관리한다.
- `experiments/README.md`는 active hypothesis/experiment index를 관리한다.
- `paper/README.md`는 paper workspace가 실제로 필요해질 때 만들고, 파일 역할, 읽는 순서, 업데이트 규칙을 관리한다.
- 세부 결과나 긴 실험 기록은 `AGENTS.md`나 루트 `README.md`에 쓰지 말고, 해당 workflow 문서 또는 가장 가까운 폴더의 `README`, report, artifact 문서에 기록한다.

## Startup And Update Protocol

- 작업 시작 시 `AGENTS.md`, `README.md`, `TODO.md`, `docs/index.md`를 읽어 현재 연구 상태와 우선순위를 재구성한다.
- `TODO.md`의 `Now`와 `Next`를 기준으로 현재 할 일을 선택한다.
- 작업 전에는 관련 `docs/` workflow와 local `README.md`를 읽어 문서 역할을 침범하지 않는지 확인한다.
- 작업 후에는 변경 내용이 어느 문서의 책임인지 판단해서 가장 가까운 책임 문서에만 업데이트한다.
- 필요한 경우 `TODO.md`의 `Now`, `Next`, `Recently Completed`를 함께 갱신한다.
- 논문 본문용 experiment는 Docker 기반 결과만 확정한다.
- hypothesis-stage smoke test와 paper experiment artifact를 명확히 구분한다.

## Working Language

- 사용자에게는 한국어로 답한다.
- 논문 제목, 방법명, 데이터셋명, metric, benchmark 이름은 영어 원문을 유지한다.
- "사실", "논문 주장", "에이전트 추론", "사용자 판단 필요"를 섞지 말고 구분한다.

## Research Mission

- 이 저장소는 석사 연구를 진행하고 최종적으로 논문을 작성하기 위한 작업 공간이다.
- 연구 목표와 방향성은 AI, ML, CV, Robotics top-tier journal/conference 수준의 문제 정의, 실험 엄밀성, 재현성, novelty 기준을 타겟한다.
- 연구 질문, 기여 후보, 실험, 해석, 논문 주장을 서로 추적 가능하게 유지한다.
- 코드, 데이터, 결과, 문서는 재현 가능한 연구 증거를 만들기 위한 목적일 때만 추가한다.
- 아이디어는 가설로, 관찰은 증거로, 해석은 주장으로 구분한다.

## Naming Rules

- 파일명과 문서 제목은 직관적이고 핵심 단어 기반으로 짧게 작성한다.
- 부모 폴더나 workflow 이름을 파일명에 반복하지 않는다. 예: `visual_inspection/labels.jsonl`처럼 쓴다.
- 불필요한 긴 접두사, 중복된 candidate/hypothesis 이름, 설명문 형태의 파일명은 피한다.
- 번호가 필요한 workflow 문서는 기존 순서를 유지하되 제목은 짧게 둔다. 예: `01_overview.md`, `02_evidence_verifier.md`.

## Minimal Structure Policy

- `experiments/`, `paper/`, `decisions/`, `data/`, `figures/`, `results/` 같은 빈 디렉터리를 미리 만들지 않는다.
- 루트에는 `AGENTS.md`, `.gitignore`, `README.md`, `TODO.md`, `summary.md`만 둔다.
- 새 연구 단계가 실제로 필요해지면 관련 workflow 또는 experiment 폴더 안에 짧은 workflow 문서를 만든다. 예: `experiments/h001_uncertainty-reobservation/runtime/workflow-YYYYMMDD-eval.md`.
- 핵심 `.py` package는 `src/`, 실행 wrapper와 helper script는 `scripts/`, Dockerfile과 manifest/config는 `configs/`, runtime workflow 문서는 관련 `experiments/` 폴더에 둔다.
- workflow 문서는 다음을 포함한다.
  - 지금 이 단계가 필요한 이유
  - 연결되는 연구 질문, 기여 후보, 또는 논문 주장
  - 예상 입력과 출력
  - 실행 절차 또는 명령
  - 재현성 요구사항
  - 새 파일이나 디렉터리가 필요한 이유
- 디렉터리는 즉시 의미 있는 파일을 담을 때만 만든다.
- 구조는 연구가 커질 때 따라오게 하고, 구조를 먼저 만들어 연구 방향을 고정하지 않는다.

## Contribution Candidate Standard

기여 후보는 아래 조건을 만족해야 한다.

- 어떤 기존 한계에서 출발하는지 분명해야 한다.
- 어떤 데이터셋, benchmark, metric으로 확인할 수 있는지 가늠 가능해야 한다.
- 석사 과정에서 6개월-1년 단위로 단계적 검증이 가능한 범위여야 한다.
- 실패했을 때 무엇을 배울 수 있는지 적어야 한다.

## Harness Engineering Rules

- harness는 model, agent, benchmark, experiment 주변의 task, environment, tool, trace, grader, metric, aggregation을 설계하는 연구 인프라로 다룬다.
- harness를 만들기 전에 먼저 연구 질문이나 검증할 주장을 적는다.
- task는 입력, 허용 도구, 성공 기준, 실패 기준을 명확히 가진다.
- outcome은 가능하면 최종 상태, 산출물, test result, metric처럼 확인 가능한 대상으로 정의한다.
- 자연어 출력만으로 성공 여부를 판단하지 않는다.
- code-based grader를 우선 사용하고, model-based grader는 rubric이 명확하고 calibration이 가능할 때만 사용한다.
- human review가 필요한 평가는 자동 metric과 섞지 말고 별도 판단으로 기록한다.
- prompt, config, seed, model/version, dataset/version, command, timestamp, environment, cost, latency, error, output을 필요한 범위에서 기록한다.
- randomness, API drift, sampling, tool nondeterminism이 결론에 영향을 줄 수 있으면 반복 trial을 둔다.
- benchmark를 키우기 전에 error analysis를 먼저 수행한다.
- 최종 논문 주장에 사용할 evaluation set은 가능한 시점에 freeze하고 이후 변경 내역을 기록한다.

## Research Operating Rules

- 모든 실험은 연구 질문, 기여 후보, ablation, failure mode 중 하나와 연결한다.
- 수동 탐색 결과와 논문에 사용할 증거를 구분한다.
- 결과가 부족하면 주장 대신 hypothesis, note, observation으로 표기한다.
- negative result와 실패한 설계도 배운 점이 명확하면 연구 기록으로 남긴다.
- leaderboard 점수 최적화는 연구 질문이 benchmark ranking일 때만 목표로 삼는다.
- 새 dependency, framework, large dataset, external service는 workflow 문서에서 필요성을 먼저 설명한다.
- 중요한 결과는 code state, command, config, data source, metric definition으로 되돌아갈 수 있어야 한다.
- 논문 본문용 experiment 또는 실제 구현이 필요한 연구 단계는 Docker 기반 재현 환경에서 진행한다.
- smoke test도 Docker 기반으로 수행한다. Host Python 환경은 문서 작업, 가벼운 파일 검증, Docker 실행 전 사전 점검에만 사용한다.
- Docker image, base image, dataset mount, GPU option, 실행 command는 workflow 또는 hypothesis feasibility 문서에 기록한다.
- 루트 `README.md`는 entrypoint 역할만 한다. 세부 실험 로그, dataset log, paper summary는 해당 workflow/experiment/literature 문서에 둔다.

## Long-running and Background Tasks

- Dataset download, model checkpoint download, Docker pull/build, decompression, indexing, preprocessing 같은 long-running I/O-heavy job을 기다리며 Codex를 막아두지 않는다.
- 긴 작업은 별도 `tmux` session, `nohup`, 또는 background job으로 실행한다.
- 가능한 경우 `aria2c`, `wget -c`, `rsync --partial`, fixed cache/local-dir를 쓰는 `huggingface-cli download`처럼 재개 가능한 command를 사용한다.
- 로그는 해당 workflow/experiment 작업 디렉터리의 `logs/` 아래 timestamped filename으로 남긴다. 빈 `logs/` 폴더는 미리 만들지 않고 실제 job을 띄울 때 만든다.
- job을 시작할 때 exact command, working directory, output path, expected files, verification command를 `TODO.md` 또는 관련 experiment README/workflow 문서에 기록한다.
- job launch 후에는 계속 monitoring하지 말고 main research task로 돌아간다.
- progress 확인은 사용자가 명시적으로 요청했거나 dependent task가 결과를 필요로 할 때만 한다.
- 큰 log를 scan하거나 전체 출력하지 않는다. `tail`, `head`, 또는 relevant error `grep`만 사용한다.
- 완료 검증은 file count, expected directory layout, checksum if available, 또는 lightweight sanity script로 수행한다.
- job status는 `TODO.md` 또는 관련 experiment README에 `launched`, `running`, `completed`, `failed`, `needs verification` 중 하나로 갱신한다.

Template:

```bash
ts=$(date +%Y%m%d-%H%M%S)
mkdir -p logs
tmux new-session -d -s <job-name> 'cd <workdir> && <resumable-command> > logs/<job-name>-${ts}.log 2>&1'
```

## Agent Work Rules

- 작업 전에 기존 파일을 읽고 현재 구조를 따른다.
- 에이전트는 작업 전후로 `TODO.md`도 갱신한다.
- 시작할 작업은 `Now`에 둔다.
- 바로 다음 작업은 `Next`에 둔다.
- 완료한 작업은 체크한다.
- 사용자 작업이나 관련 없는 변경을 되돌리지 않는다.
- 검색은 우선 `rg` 또는 `rg --files`를 사용한다.
- 수동 파일 편집은 `apply_patch`를 사용한다.
- 변경은 작고 검토 가능한 단위로 유지한다.
- 실험 명령을 추가하면 smoke test, dry run, tiny fixture 중 하나로 최소 검증 경로를 둔다.
- 사용자의 판단이 필요한 선택지는 "사용자 판단 필요"로 분리해서 제시한다.

## Paper Rules

- 논문 작성은 충분한 evidence와 outline이 생긴 뒤 시작한다.
- 논문 workflow가 필요해지면 먼저 target venue 또는 thesis format, citation style, figure/table 계획, source-of-truth 규칙을 문서화한다.
- 논문 주장은 실험 증거, 문헌 근거, 또는 명시적 reasoning note로 추적 가능해야 한다.
- limitation은 결과 해석과 분리해서 기록한다.
- paper용 문서와 실험용 문서는 역할을 섞지 않는다.

## Paper Novelty Rules

- Motivation과 novelty를 구분한다. "기존 방법이 안 된다" 또는 "새 모듈을 붙였다"는 motivation일 수 있지만, 그 자체를 contribution으로 쓰지 않는다.
- 논문화 과정은 원하는 hypothesis를 증명하기 위해 evidence, metric, baseline, threshold를 사후적으로 끼워 맞추는 방식으로 진행하지 않는다. 문제 원인 진단에서 method 형태가 자연스럽게 도출되어야 하며, claim은 그 원인을 해결한다는 사전 정의된 gate를 통과할 때만 승격한다.
- 결과가 기대와 다르면 threshold, metric, baseline을 바꾸어 hypothesis를 살리지 말고 failure mechanism, scope reduction, deferred claim, or new hypothesis로 기록한다.
- Contribution은 원인 진단과 해법의 원리가 함께 있어야 한다. 실패 원인을 설명하는 한 문장과 그 원인에서 method 형태가 왜 도출되는지 연결한다.
- Challenge는 단순히 "기존 방식이 안 된다"가 아니라 naive baseline을 실제로 돌린 뒤 case-level failure taxonomy로 정의한다.
- Naive baseline을 먼저 정의하고, 어디서 왜 실패하는지 case-level failure taxonomy를 만든다.
- Method component는 swap 가능한 module list가 아니라 failure taxonomy에서 강제된 design choice여야 한다.
- 각 design choice는 ablation으로 검증 가능해야 한다. Ablation은 "전체 시스템 vs baseline"에서 멈추지 않고 component removal, simpler alternative, threshold/utility variant를 포함한다.
- "왜 더 단순한 방법으로는 안 되는가?"에 답할 수 있어야 한다. 최소 3개 simpler alternative를 정의하고 실패 조건을 적는다.
- 논문 contribution one-liner는 "원인 진단 + 해법의 원리 + 검증 대상"을 포함한다.
- 실험은 motivation을 반복하지 않고 novelty를 검증해야 한다. 단순 성능 향상보다 어떤 failure mode가 어떤 component 때문에 줄었는지 보여준다.
- Top-tier pattern을 목표로 할 때, 같은 데이터셋에서 점수가 좋아졌다는 주장보다 새로운 비교 축, failure mechanism, method derivation, ablation, generality, limitation analysis를 먼저 갖춘다.
- H001의 novelty 후보는 "semantic uncertainty를 confidence score가 아니라 active SLAM/navigation utility로 변환한다"는 방향이지만, `VLMaps`, detector, segmenter, confidence replanning을 조합했다는 식으로 쓰면 novelty가 약하다.
- Top-tier target 판단은 `docs/paper.md`의 novelty gate를 따른다.
