# Insights

## Facts

- `Active Neural Mapping`는 ICCV 2023로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/ICCV2023/html/Yan_Active_Neural_Mapping_ICCV_2023_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- online active mapping system으로 neural representation의 uncertainty를 줄이며 효율적으로 환경을 학습한다고 주장한다.
- Gibson과 Matterport3D에서 efficacy를 보인다고 주장한다.

## Inferences

- active SLAM에서 map representation uncertainty를 어떻게 planner objective로 넘길지 보는 핵심 참고문헌이다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic memory uncertainty와 neural uncertainty 비교
- lightweight map uncertainty estimator만 분리해 harness에 사용
- active semantic SLAM에서 uncertainty objective ablation

## What Would Change This Assessment

public code가 안정적이면 neural-map baseline으로 재사용 가능하다.
