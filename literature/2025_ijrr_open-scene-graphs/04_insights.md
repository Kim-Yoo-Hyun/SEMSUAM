# Insights

## Facts

- `Open Scene Graphs for Open-World Object-Goal Navigation`는 IJRR 2025로 registry에 기록했다.
- Primary source는 https://journals.sagepub.com/doi/10.1177/02783649251369549 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- OSG Navigator가 ObjectNav benchmarks에서 SOTA performance를 달성하고 diverse goals, environments, robot embodiments에 zero-shot generalize한다고 주장한다.

## Inferences

- persistent graph memory를 open-world ObjectNav에 쓰는 high-level target으로 중요하다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- OSG memory를 active SLAM loop closure candidate로 사용
- schema/node confidence를 replanning uncertainty로 사용
- OSG vs ConceptGraphs vs SG-Nav graph representation 비교

## What Would Change This Assessment

code/data가 공개되어 있으면 graph memory benchmark로 검토한다.
