# Insights

## Facts

- `UniGoal: Towards Universal Zero-shot Goal-oriented Navigation`는 CVPR 2025로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/CVPR2025/html/Yin_UniGoal_Towards_Universal_Zero-shot_Goal-oriented_Navigation_CVPR_2025_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- single framework로 세 navigation tasks에서 SOTA zero-shot performance를 달성하고 task-specific zero-shot methods와 supervised universal methods를 능가한다고 주장한다.

## Inferences

- semantic memory representation을 goal-conditioned graph matching으로 쓰는 방향을 보여준다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- pre-explored scene graph를 goal graph matching prior로 사용
- active re-observation을 matching state transition에 넣기
- SLAM uncertainty가 coordinate projection/anchor alignment에 미치는 영향 평가

## What Would Change This Assessment

code release가 있으면 graph-based universal navigation baseline으로 검토한다.
