# Insights

## Facts

- `MemoNav: Working Memory Model for Visual Navigation`는 CVPR 2024로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/CVPR2024/html/Li_MemoNav_Working_Memory_Model_for_Visual_Navigation_CVPR_2024_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- Gibson과 Matterport3D multi-goal tasks에서 previous methods를 outperform하고 더 efficient routes를 계획한다고 주장한다.

## Inferences

- prior observation을 모두 쓰지 않고 goal-relevant memory만 쓰는 설계가 user research에 중요하다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic map node forgetting/retrieval policy 설계
- working memory selection을 active SLAM viewpoint 후보 pruning에 사용
- memory size vs ObjectNav SR/SPL trade-off 평가

## What Would Change This Assessment

code가 공개되면 memory baseline으로 빠르게 비교 가능하다.
