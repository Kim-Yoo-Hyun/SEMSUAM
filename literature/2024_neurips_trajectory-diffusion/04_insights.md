# Insights

## Facts

- `Trajectory Diffusion for ObjectGoal Navigation`는 NeurIPS 2024로 registry에 기록했다.
- Primary source는 https://papers.neurips.cc/paper_files/paper/2024/hash/c72861451d6fa9dfa64831102b9bb71a-Abstract-Conference.html 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- Gibson and MP3D에서 generated trajectories가 더 accurate and efficient navigation을 유도한다고 주장한다.

## Inferences

- semantic map을 사용한 planner output을 sequence로 바꾸는 대안 baseline이다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- active SLAM planner도 single NBV가 아니라 trajectory diffusion으로 생성
- semantic memory uncertainty를 diffusion condition에 추가
- pre-explored map error가 trajectory generation에 미치는 영향 평가

## What Would Change This Assessment

code가 local에서 실행되면 ObjectNav planning baseline으로 유용하다.
