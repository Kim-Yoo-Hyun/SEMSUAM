# AGENT.md

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
- 루트에는 `AGENT.md`, `.gitignore`, `README.md`, `TODO.md`, `summary.md`만 둔다.
- 새 연구 단계가 실제로 필요해지면 관련 workflow 또는 hypothesis 폴더 안에 짧은 workflow 문서를 만든다. 예: `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-YYYYMMDD-eval.md`.
- Dockerfile, `.py`, `.sh`, runtime workflow 문서는 루트에 두지 않고 관련 hypothesis 내부에 둔다.
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
- 루트 `README.md`는 entrypoint 역할만 한다. 세부 실험 로그, dataset log, paper summary는 해당 workflow/hypothesis/literature 문서에 둔다.

## Long-running and Background Tasks

- Dataset download, model checkpoint download, Docker pull/build, decompression, indexing, preprocessing 같은 long-running I/O-heavy job을 기다리며 Codex를 막아두지 않는다.
- 긴 작업은 별도 `tmux` session, `nohup`, 또는 background job으로 실행한다.
- 가능한 경우 `aria2c`, `wget -c`, `rsync --partial`, fixed cache/local-dir를 쓰는 `huggingface-cli download`처럼 재개 가능한 command를 사용한다.
- 로그는 해당 workflow/hypothesis 작업 디렉터리의 `logs/` 아래 timestamped filename으로 남긴다. 빈 `logs/` 폴더는 미리 만들지 않고 실제 job을 띄울 때 만든다.
- job을 시작할 때 exact command, working directory, output path, expected files, verification command를 `TODO.md` 또는 관련 hypothesis README/workflow 문서에 기록한다.
- job launch 후에는 계속 monitoring하지 말고 main research task로 돌아간다.
- progress 확인은 사용자가 명시적으로 요청했거나 dependent task가 결과를 필요로 할 때만 한다.
- 큰 log를 scan하거나 전체 출력하지 않는다. `tail`, `head`, 또는 relevant error `grep`만 사용한다.
- 완료 검증은 file count, expected directory layout, checksum if available, 또는 lightweight sanity script로 수행한다.
- job status는 `TODO.md` 또는 관련 hypothesis README에 `launched`, `running`, `completed`, `failed`, `needs verification` 중 하나로 갱신한다.

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
