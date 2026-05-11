# Insights

## Facts

- `Uni-NaVid: A Video-based Vision-Language-Action Model for Unifying Embodied Navigation Tasks`는 RSS 2025로 registry에 기록했다.
- Primary source는 https://roboticsconference.org/program/papers/13/ 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- unified model로 comprehensive navigation benchmarks에서 SOTA performance를 달성하고 real-world effectiveness를 보인다고 주장한다.

## Inferences

- explicit map 없이도 history가 얼마나 충분한지 보는 upper/competing baseline이다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- explicit semantic map을 추가했을 때 Uni-NaVid-style policy 개선 여부
- video memory vs semantic graph memory 비교
- generalist benchmark에서 SLAM-aware memory의 marginal value 측정

## What Would Change This Assessment

open weights가 있으면 lightweight evaluation baseline으로 고려한다.
