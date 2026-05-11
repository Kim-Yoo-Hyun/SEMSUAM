# Insights

## Facts

- `Scene Action Maps: Behavioural Maps for Navigation without Metric Information`는 ICRA 2024로 registry에 기록했다.
- Primary source는 https://scene-action-maps.github.io/ 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- metric information 없이도 abstract inaccurate map에서 navigation-relevant behaviour graph를 추출해 real robot navigation에 사용할 수 있다고 주장한다.

## Inferences

- pre-existing map/prior를 navigation action으로 변환하는 다른 방식의 reference다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic map을 behaviour graph로 abstract하기
- metric-SLAM이 불안정한 환경에서 non-metric semantic prior 사용
- pre-explored map의 inaccurate geometry를 behaviour-level로 보정

## What Would Change This Assessment

dataset/code가 공개되면 non-metric prior baseline으로 검토한다.
