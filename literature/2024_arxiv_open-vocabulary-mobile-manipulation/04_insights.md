# Insights

## Facts

- `Open-vocabulary Mobile Manipulation in Unseen Dynamic Environments with 3D Semantic Maps`는 arXiv 2024로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2406.18115 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- real-world JSR-1 platform에서 navigation and task success를 높이고 dynamic setting에서 replanning이 가능하다고 주장한다.

## Inferences

- semantic map이 dynamic replanning에 쓰이는 실사용 예시로 참고 가치가 있다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- manipulation 제외하고 ObjectNav replanning만 분리
- 3D semantic map candidate confidence를 active re-observation에 사용
- dynamic scene change detection을 map update benchmark로 사용

## What Would Change This Assessment

code와 episode data가 공개되면 dynamic semantic mapping baseline으로 검토한다.
