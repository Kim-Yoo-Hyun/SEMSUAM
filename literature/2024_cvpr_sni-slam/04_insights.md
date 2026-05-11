# Insights

## Facts

- `SNI-SLAM: Semantic Neural Implicit SLAM`는 CVPR 2024로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/CVPR2024/papers/Zhu_SNI-SLAM_Semantic_Neural_Implicit_SLAM_CVPR_2024_paper.pdf 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- recent NeRF-based SLAM methods보다 mapping/tracking accuracy가 좋고 semantic segmentation도 우수하다고 주장한다.

## Inferences

- semantic SLAM backbone 후보지만 active decision layer는 별도 설계해야 한다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- SNI-SLAM map을 active viewpoint planner input으로 사용
- closed-set semantic SLAM vs open-vocabulary semantic map 비교
- semantic mIoU와 ObjectNav SR/SPL 상관 측정

## What Would Change This Assessment

code가 공개되어 안정적이면 semantic SLAM baseline으로 검토한다.
