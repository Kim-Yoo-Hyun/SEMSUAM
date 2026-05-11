# Insights

## Facts

- `ActiveSplat: High-Fidelity Scene Reconstruction through Active Gaussian Splatting`는 RA-L 2025로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2410.21955 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- ActiveSplat이 high-fidelity scene reconstruction에서 strong performance를 낸다고 주장한다.

## Inferences

- 3DGS active mapping trend의 robotics-side evidence로 registry에 유지한다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic goal query를 3DGS active planner objective로 추가
- reconstruction fidelity 대신 semantic localization utility 평가
- 3DGS map update cost와 navigation gain trade-off 분석

## What Would Change This Assessment

public code와 scene benchmark가 확보되면 구현 우선순위가 올라간다.
