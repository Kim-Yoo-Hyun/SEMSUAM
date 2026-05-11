# Literature Rules

## Literature Workflow

- `literature/README.md`: Field Map, Trend Synthesis, Cross-Paper Insights, Open Questions
- `literature/PAPER.md`: Paper Registry, Reading Queue
- `literature/Contribution Candidates.md`: 석사 연구 contribution candidate 목록과 Quality Gate 판정
- `literature/CAND-<number>.md`: primary candidate 수준으로 구체화된 후보의 feasibility 문서
- 문헌 조사는 가능한 한 primary source를 우선한다.
- 최신 흐름을 다룰 때는 반드시 최신 정보를 확인한다.
- top-tier conference/journal를 우선한다. 예: CVPR, ICCV, ECCV, NeurIPS, ICRA, CoRL, RSS, IROS, RA-L, TRO, IJRR.
- 각 trend는 최소 2개 이상의 논문 근거가 있을 때만 `Trend Synthesis`에 기록한다.
- 근거가 약하거나 연결이 간접적이면 `Cross-Paper Insights`에 Low confidence로 기록한다.
- "사실", "논문 주장", "에이전트 추론", "사용자 판단 필요"를 섞지 않는다.

## Contribution Candidate Workflow

- contribution candidate는 `literature/Contribution Candidates.md`에 먼저 기록한다.
- 후보 중 하나가 primary candidate 수준으로 구체화되면 `literature/CAND-<number>.md`를 만든다.
- 논문 근거가 부족한 candidate는 확정하지 않고 `추가 조사 필요`로 표시한다.
- 각 candidate는 최소한 아래 항목을 포함한다.
  - 기존 한계
  - 연구 질문
  - 가능한 접근
  - 필요한 dataset / benchmark
  - baseline
  - 실패 조건
  - 6개월-1년 안에 단계적으로 검증 가능한 범위인지

## Contribution Candidate Quality Gate

문헌 조사 결과가 아래 기준을 만족하지 않으면 contribution candidate를 확정하지 않는다.

- 최소 6개 이상의 primary source를 확인했다.
- 각 주요 trend는 2개 이상의 근거 논문을 가진다.
- dataset, benchmark, metric이 확인되어 있다.
- "이 분야에서 중요해 보인다"가 아니라 "왜 아직 풀리지 않았는지"가 설명되어 있다.
- 석사 연구 범위에서 구현/검증 가능한지 판단할 수 있다.

## Candidate Status Terms

- `Primary candidate`: 근거, dataset, metric, baseline, 구현 범위가 충분히 좁혀져 바로 feasibility 문서로 분리한 후보.
- `Viable candidate`: 근거와 평가면은 충분하지만 implementation risk 또는 exact protocol 확인이 남은 후보.
- `추가 조사 필요`: trend 근거는 있으나 dataset/metric/baseline 또는 재현 가능성이 부족해 확정하지 않는 후보.

## Paper Folder Convention

논문 하나는 하나의 폴더로 관리한다.

```text
literature/
  <year>_<venue-or-arxiv>_<short-title>/
    paper.pdf
    01_metadata.md
    02_paper_card.md
    03_evaluation.md
    04_insights.md
```

예시:

```text
literature/
  2024_cvpr_open3dsg/
    paper.pdf
    01_metadata.md
    02_paper_card.md
    03_evaluation.md
    04_insights.md
```

폴더명 규칙:

- 소문자 사용
- 공백 대신 `-` 사용
- 가능한 형식: `<year>_<venue>_<short-title>`
- venue가 불명확하면 `arxiv` 또는 `preprint` 사용
- 같은 논문을 중복 생성하지 않는다. 먼저 `literature/PAPER.md`의 Paper Registry를 확인한다.
- 가능한 경우 논문 PDF를 `paper.pdf`라는 이름으로 저장한다.
- arXiv 등에서 버전이 중요한 경우 `01_metadata.md`에 확인한 버전과 다운로드 날짜를 적는다.

## File Roles

### `01_metadata.md`

논문의 식별 정보와 출처를 저장한다.

```md
# <Paper Title>

- Date checked:
- Year:
- Venue / status:
- Authors:
- Link:
- PDF:
- Local PDF: `paper.pdf`
- PDF version:
- PDF downloaded:
- Code:
- Project page:
- Dataset:
- Tags:
- Reading status: Queued / Skimmed / Read / Revisit
```

### `02_paper_card.md`

논문의 핵심 문제와 방법을 정리한다.

```md
# Paper Card

## Problem

## Core Idea

## Input / Output

## Method

## Main Claims

## Strengths

## Limitations

## Relevance to My Research

## Follow-up Questions
```

### `03_evaluation.md`

실험과 평가 가능성을 따로 본다. 석사 연구로 이어질 수 있는지 판단하는 핵심 파일이다.

```md
# Evaluation

## Dataset / Benchmark

## Splits

## Metrics

## Baselines

## Main Results

## Reproducibility Notes

## Evaluation Weaknesses
```

### `04_insights.md`

에이전트의 해석, trend 연결, 기여 가능성을 기록한다. 논문 사실과 추론을 분리한다.

```md
# Insights

## Facts

## Paper Claims

## Inferences

## Connection to Field Trends

## Possible Contribution Angles

## What Would Change This Assessment
```
