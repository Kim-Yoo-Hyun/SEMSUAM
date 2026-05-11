# Insights

## Facts

- `LERF: Language Embedded Radiance Fields`는 ICCV 2023로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/ICCV2023/html/Kerr_LERF_Language_Embedded_Radiance_Fields_ICCV_2023_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- LERF는 open-ended language queries를 3D radiance field에서 localize할 수 있다고 주장한다.

## Inferences

- open-vocabulary memory가 neural field 안에 들어갈 수 있다는 representation reference다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- LERF-style language field를 lightweight topological node descriptor로 distill
- language relevancy uncertainty를 active view selection에 사용
- open-vocabulary query map과 ObjectNav metric 연결

## What Would Change This Assessment

real-time/online variant가 확보되면 mapping backbone 후보가 된다.
