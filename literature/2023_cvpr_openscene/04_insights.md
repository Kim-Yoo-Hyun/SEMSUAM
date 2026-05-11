# Insights

## Facts

- `OpenScene: 3D Scene Understanding with Open Vocabularies`는 CVPR 2023로 registry에 기록했다.
- Primary source는 https://openaccess.thecvf.com/content/CVPR2023/html/Peng_OpenScene_3D_Scene_Understanding_With_Open_Vocabularies_CVPR_2023_paper.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- zero-shot 3D semantic segmentation and open-vocabulary scene understanding이 가능하다고 주장한다.

## Inferences

- open-vocabulary semantic landmark/memory representation 후보이다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- OpenScene feature confidence를 map uncertainty로 사용
- OpenScene + active viewpoint selection
- OpenScene offline prior vs online semantic SLAM 비교

## What Would Change This Assessment

local dataset에서 feature extraction cost가 manageable하면 semantic backbone 후보이다.
