# Insights

## Facts

- `OctoNav: Towards Generalist Embodied Navigation`는 arXiv 2025로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2506.09839 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- generalist navigation agent 평가를 위한 large-scale benchmark와 method를 제공한다고 주장한다.

## Inferences

- master research harness를 만들 때 task taxonomy와 evaluation surface를 참고할 수 있다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- SLAM-aware semantic memory task를 OctoNav-style mixed instruction으로 정의
- active mapping + ObjectNav compound benchmark 설계
- memory reuse 능력을 benchmark task로 분리

## What Would Change This Assessment

OctoNav-Bench가 공개되어 있으면 evaluation scaffold 후보이다.
