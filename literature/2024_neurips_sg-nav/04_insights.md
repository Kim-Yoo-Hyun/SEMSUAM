# Insights

## Facts

- `SG-Nav: Online 3D Scene Graph Prompting for LLM-based Zero-shot Object Navigation`는 NeurIPS 2024로 registry에 기록했다.
- Primary source는 https://proceedings.neurips.cc/paper_files/paper/2024/hash/098491b37deebbe6c007e69815729e09-Abstract-Conference.html 이다.
- Local PDF는 official NeurIPS 2024 conference PDF로 저장했다.
- Code는 https://github.com/bagh2178/SG-Nav 에 공개되어 있다.
- 평가 benchmark는 MP3D, HM3D, RoboTHOR이며 주요 metric은 `SR`, `SPL`, `SoftSPL`이다.

## Paper Claims

- Online 3D scene graph와 H-CoT prompting은 zero-shot ObjectNav에서 nearby-object prompt보다 더 나은 goal localization reasoning을 제공한다고 주장한다.
- Graph-based re-perception은 false positive object detection을 줄이고 ObjectNav success를 높인다고 주장한다.
- MP3D, HM3D, RoboTHOR에서 prior zero-shot baselines보다 높은 `SR` / `SPL`을 달성한다고 주장한다.

## Inferences

- CAND-01 Step 1-3의 핵심 근거로 사용할 수 있다. 특히 object/node confidence, active re-observation, `SR` / `SPL` / wrong-goal behavior를 하나의 harness에서 묶는 방향과 잘 맞는다.
- 다만 `SG-Nav` 자체는 SLAM uncertainty를 줄이는 논문이 아니므로 Step 4-5 근거로 쓰려면 P01/P02/P30 계열과 결합해야 한다.
- 이 논문을 full baseline으로 재현하기보다, re-perception trigger와 graph/node uncertainty logging을 작게 떼어내는 것이 첫 실험에 더 적합하다.

## 사용자 판단 필요

- `SG-Nav`를 direct baseline으로 설치/실행할지, `CARe` 기반 harness에 re-perception idea만 이식할지 선택해야 한다.
- LLM prompting을 연구 핵심에 포함할지, semantic map uncertainty와 viewpoint selection 중심으로 제한할지 결정해야 한다.

## Connection to Field Trends

- Trend 3 `Environmental perception is shifting toward open-vocabulary semantic maps and retrievable embodied memory`: scene graph memory를 LLM-readable structure로 만드는 evidence다.
- Trend 4 `Pre-explored semantic maps are becoming actionable but need uncertainty-aware correction`: re-perception이 wrong semantic evidence를 action으로 수정하는 사례다.
- CAND-01에서는 P27 `CARe`와 함께 pre-explored / online semantic memory의 correction loop 근거로 묶을 수 있다.

## Possible Contribution Angles

- Scene graph node uncertainty를 active re-perception trigger로 사용한다.
- Goal credibility가 낮은 object에 대해 next-best re-observation viewpoint를 선택하고, `wrong-goal visit` / `wasted path`를 metric으로 둔다.
- SG-Nav-style semantic graph를 SLAM pose graph와 결합해 Step 4-5에서 map correction utility로 확장한다.
- LLM 없이 graph heuristic baseline을 만들어 contribution을 semantic memory / uncertainty / LLM reasoning으로 분리한다.

## What Would Change This Assessment

- Code 실행이 어렵거나 LLM/VLM dependency가 과하면 trend evidence로만 사용한다.
- Re-perception이 success는 높이지만 path overhead가 크면, CAND-01의 contribution은 "re-perception을 언제 할 것인가"로 좁아진다.
- Node uncertainty가 SLAM metric과 연결되지 않으면 Step 4-5는 P01/P02/P30 기반의 별도 active SLAM utility로 설계해야 한다.
