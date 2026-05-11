# Insights

## Facts

- `SLAM-Free Visual Navigation with Hierarchical Vision-Language Perception and Coarse-to-Fine Semantic Topological Planning`는 arXiv 2025로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2509.20739 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- simulation and real-world settings에서 semantic accuracy, planning quality, navigation success를 개선한다고 주장한다.

## Inferences

- SLAM을 포함하는 연구라면 비교해야 할 map-light semantic navigation baseline이다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- SLAM-based semantic memory와 SLAM-free semantic topological map 비교
- sensor drift 조건에서 explicit SLAM의 benefit/failure 측정
- legged robot 대신 simulator에서 semantic topological planning만 재현

## What Would Change This Assessment

benchmark와 code가 공개되면 contrast baseline으로 사용 가능하다.
