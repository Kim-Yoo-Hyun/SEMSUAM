# Insights

## Facts

- `Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration`는 IROS 2024로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2408.14726 이다.
- arXiv version은 v2이며, last revised date는 2024-09-02이다.
- DOI는 `10.1109/IROS58592.2024.10802821`이다.
- Code는 `BohemianRhapsodyz/semantic_exploration`에 공개되어 있다.
- Evaluation은 Habitat simulator와 Matterport3D environments를 사용한다.
- Baselines는 `SSMI`와 `TARE`다.
- Reported metrics include `ATE`, map error, semantic `IoU`, and explored volume over time.

## Paper Claims

- Habitat / Matterport3D simulation에서 exploration efficiency를 크게 잃지 않으면서 metric-semantic SLAM quality를 높인다고 주장한다.
- Average map error는 최대 21%, average localization error는 최대 38% 줄었다고 주장한다.
- Semantic classification accuracy는 약 9% 개선된다고 주장한다.
- Semantic mutual information과 pose graph spectral optimality를 함께 쓰면 `SSMI`, `TARE`보다 semantic map `IoU`와 SLAM error에서 유리하다고 주장한다.

## Inferences

- `CAND-01` Step 4-5에서 `SLAMOnly` 또는 active SLAM utility baseline으로 가장 직접적인 후보 중 하나다.
- Full ROS stack reproduction이 부담되면, first implementation은 weighted Laplacian D-optimality와 loop closure opportunity를 lightweight proxy로 재구성하는 쪽이 현실적이다.
- 이 논문은 "semantic uncertainty + pose uncertainty를 action utility로 결합할 수 있다"는 evidence를 제공하지만, "pre-explored semantic memory가 ObjectNav를 개선한다"는 evidence는 아니다.
- Baseline localization failure를 제외한 점은 `CAND-01`에서 오히려 contribution metric으로 살릴 수 있다. `localization failure count`를 primary failure metric으로 기록하면 deployment 관점이 강해진다.

## 사용자 판단 필요

- `semantic_exploration`을 직접 build하는 implementation baseline으로 둘지, utility design reference로만 둘지 결정해야 한다.
- Step 4-5에서 `ATE/RPE`를 full SLAM stack으로 측정할지, replay/pose-graph proxy로 먼저 측정할지 결정해야 한다.
- Real-world deploy를 고려한다면 ROS Noetic 기반 stack을 유지할지 ROS2 stack으로 포팅할지 판단해야 한다.

## Connection to Field Trends

- Active semantic SLAM trend의 strong evidence다.
- Environmental perception intelligence와 robot mobility를 utility function 안에서 연결한다.
- Semantic mapping metric과 SLAM pose/map metric을 함께 평가한다는 점에서 `CAND-01` Step 5와 직접 연결된다.
- Open-vocabulary semantic memory trend와는 간접 연결이다. 이 논문은 open-vocabulary retrieval보다 closed simulator semantics와 semantic octomap에 가깝다.

## Possible Contribution Angles

- Pre-explored semantic map confidence를 semantic mutual information term으로 변환하기.
- Pose graph D-optimality를 re-observation viewpoint utility에 넣기.
- `ObjectNav` metric과 `ATE` / map error / semantic `IoU`를 함께 logging하는 harness 만들기.
- Baseline localization failure를 제외하지 않고 wrong-goal visit, wasted path, localization failure count로 통합 평가하기.
- `SemanticOnly`, `SLAMOnly`, `SemanticSLAM` ablation으로 semantic gain과 SLAM gain을 분리하기.

## What Would Change This Assessment

- Code가 현재 environment에서 build되고 Habitat scene replay가 가능하면 implementation baseline 후보가 된다.
- Code dependency가 과도하거나 scene config가 불명확하면 trend evidence와 metric design reference로만 둔다.
- Real-world RGB-D / mobile base setup에서 pose graph uncertainty proxy를 안정적으로 얻을 수 있으면 `CAND-01` Step 5의 중심 근거가 된다.
- Open-vocabulary map과 결합했을 때 semantic uncertainty가 noisy해지면 utility design을 calibration-first로 바꿔야 한다.
