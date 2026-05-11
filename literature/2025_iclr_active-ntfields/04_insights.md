# Insights

## Facts

- `Physics-informed Neural Mapping and Motion Planning in Unknown Environments`는 ICLR 2025로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2410.09883 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- simulated and real-world environments에서 mapping/planning baselines보다 좋은 performance를 보인다고 주장한다.

## Inferences

- planning-friendly map representation이라는 관점은 semantic map 설계에도 중요하다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic object cost를 arrival time field에 condition
- semantic uncertainty가 path field를 바꾸는지 평가
- Active SLAM map을 planner-native field로 변환

## What Would Change This Assessment

code가 잘 실행되면 planning layer baseline으로 참고한다.
