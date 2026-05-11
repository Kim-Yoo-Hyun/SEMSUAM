# Insights

## Facts

- `ActiveGAMER: Active GAussian Mapping through Efficient Rendering`는 CVPR 2025로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/CVPR2025/html/Chen_ActiveGAMER_Active_GAussian_Mapping_through_Efficient_Rendering_CVPR_2025_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- efficient rendering 기반 active Gaussian mapping이 mapping quality와 exploration efficiency를 개선한다고 주장한다.

## Inferences

- 3DGS backbone을 쓰는 경우 candidate viewpoint scoring baseline으로 유용하다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic-aware rendering utility 설계
- rendering uncertainty와 object query uncertainty 결합
- 3DGS active mapping을 semantic ObjectNav metric으로 재평가

## What Would Change This Assessment

implementation이 공개되면 ActiveSplat/P09와 함께 3DGS 후보군 비교가 가능하다.
