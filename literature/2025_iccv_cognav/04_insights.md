# Insights

## Facts

- `CogNav: Cognitive Process Modeling for Object Goal Navigation with LLMs`는 ICCV 2025로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/ICCV2025/html/Cao_CogNav_Cognitive_Process_Modeling_for_Object_Goal_Navigation_with_LLMs_ICCV_2025_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- HM3D, MP3D, RoboTHOR에서 ObjectNav success rate를 SOTA 대비 relative 14% 이상 개선한다고 주장한다. arXiv abstract는 HM3D SOTA를 69.3%에서 87.2%로 높였다고 주장한다.

## Inferences

- environmental perception intelligence가 navigation state machine으로 변환되는 최신 예시다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- LLM 없이 cognitive state machine rule baseline 구성
- cognitive map node uncertainty와 active re-observation 결합
- SLAM pose confidence를 cognitive state transition input으로 추가

## What Would Change This Assessment

code가 공개되면 SG-Nav/UniGoal과 함께 graph-LLM baseline으로 묶는다.
