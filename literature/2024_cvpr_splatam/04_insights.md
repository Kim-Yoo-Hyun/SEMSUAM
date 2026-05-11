# Insights

## Facts

- `SplaTAM: Splat, Track & Map 3D Gaussians for Dense RGB-D SLAM`는 CVPR 2024로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2312.02126 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- dense RGB-D SLAM tracking, mapping, rendering accuracy에서 prior dense baselines보다 strong result를 보인다고 주장한다.

## Inferences

- 3DGS active mapping 계열의 map backbone baseline으로 중요하지만, user research에서는 semantic/action layer를 별도로 얹어야 한다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- 3DGS map 위에 semantic confidence layer 추가
- 3DGS rendering uncertainty와 semantic NBV 결합
- SplaTAM pose/map output을 active semantic planner 입력으로 사용

## What Would Change This Assessment

local machine에서 SplaTAM이 안정적으로 돌아가면 3DGS baseline 후보가 된다.
