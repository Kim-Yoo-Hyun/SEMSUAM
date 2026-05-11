# Paper Card

## Problem

### 사실

이 논문은 unknown indoor environment에서 mobile robot이 RGB-D observation을 수집하며 3DGS map을 만들고, 동시에 localization을 유지하면서 exploration trajectory를 선택하는 active mapping 문제를 다룬다.

### 논문 주장

기존 active mapping / active reconstruction 방법은 either multimodal LLM의 scene-layout prior를 long-horizon exploration에 활용하지 않거나, pose/localization uncertainty를 충분히 고려하지 않는다고 주장한다. 특히 3DGS / neural rendering 기반 SLAM은 non-linear rendering loss로 pose와 map을 업데이트하므로 classical filter-based SLAM처럼 covariance를 쉽게 얻기 어렵다고 본다.

### 에이전트 추론

P09는 `CAND-01` Step 4-5에 가장 직접적인 reference 중 하나다. Semantic-level long-horizon goal selection과 Fisher Information 기반 localization-aware path utility를 하나의 loop에 넣었기 때문이다. 다만 object-level semantic memory나 ObjectNav success를 직접 평가하지 않으므로 Step 1-3의 direct baseline은 아니다.

## Core Idea

3DGS map에서 bird's-eye-view rendering, frontier candidates, current trajectory를 만들어 multimodal LLM에 long-horizon exploration region을 고르게 한다. 그 뒤 selected region 안에서 candidate poses / paths를 만들고, 3DGS scene parameters의 Expected Information Gain과 pose Fisher Information 기반 localization cost를 결합해 short-term path를 선택한다.

## Input / Output

Input:

- RGB-D observations in Habitat simulator
- current 3DGS map / occupancy grid
- bird's-eye-view rendering from 3DGS
- current trajectory, frontier candidates, current step / total budget text prompt
- multimodal LLM output for coarse region of interest
- candidate poses and A* paths

Output:

- selected long-horizon exploration target / region
- uncertainty-aware short-term path
- next discrete action among `MOVE_FORWARD`, `TURN_LEFT`, `TURN_RIGHT`
- updated 3DGS map and camera pose estimate
- final reconstruction and tracking evaluation

## Method

### 사실

- 3DGS is used as the scene representation.
- The system divides exploration into long-horizon planning and detailed motion planning.
- Long-horizon planning uses a multimodal LLM with text prompt plus annotated bird's-eye-view rendering.
- The paper uses `GPT-4o` for the main multimodal LLM experiment and `Llava-7b` in ablation.
- Frontiers are generated from an occupancy grid projected from the 3D Gaussian representation.
- Chain-of-Thought prompting is used to make the LLM analyze candidate frontiers before selecting one.
- If LLM output is not a valid candidate, the planner falls back to selecting the largest frontier.
- After the long-horizon target is selected, candidate poses are sampled in the region of interest.
- Expected Information Gain is computed using Fisher Information of 3DGS parameters.
- The current model Fisher Information is approximated with Monte-Carlo samples from free-space camera poses instead of only empirical Fisher from already visited training views.
- Candidate paths are generated with A* on the occupancy map.
- Localization cost is derived from pose Fisher Information and the Cramer-Rao bound.
- Final path objective combines localization cost and log Expected Information Gain with a hyperparameter.
- The system replans when close to a possible obstacle or when reaching the end of the selected path.

### 논문 주장

- EIG can be computed before visiting a candidate pose because Fisher Information does not require the future observation label.
- EIG correlates with rendering quality: high EIG tends to indicate poorly reconstructed or information-rich candidate views.
- Localization uncertainty is necessary because paths toward poorly reconstructed / textureless regions can increase camera tracking risk.
- Combining LLM long-horizon planning and Fisher Information path selection improves mapping, completeness, and tracking.

### 에이전트 추론

For `CAND-01`, the reusable design is the two-level utility structure:

- semantic / prior-driven coarse target selection
- SLAM-state-aware short-term utility for re-observation path choice

The full 3DGS + multimodal LLM stack is probably too heavy as a first implementation target. A smaller version can replace 3DGS Fisher Information with object/node uncertainty, pose graph connectivity, ATE/RPE proxy, or semantic map confidence while preserving the same evaluation logic.

## Main Claims

### 논문 주장

- The method is the first active mapping system with 3D Gaussian representation that does not depend on ground-truth camera poses.
- It provides a way to use zero-shot multimodal LLM long-horizon planning inside active mapping.
- It introduces localization uncertainty into active mapping and balances information gain against localization error cost.
- It outperforms `ANS`, `UPEN`, `ExplORB`, and `FBE` on Gibson in reconstruction quality, tracking accuracy, and completeness.
- It outperforms `UPEN`, `ExplORB`, and `FBE` on HM3D in the reported metrics.
- Ablations show that adding localization uncertainty improves tracking / reconstruction and adding LLM improves all reported metrics.

## Strengths

- Directly couples environmental perception, active exploration, mapping, and localization uncertainty.
- Uses top-tier primary source: ICCV 2025.
- Evaluation includes map quality, tracking accuracy, and coverage/completeness-style metric.
- Baselines include both learned exploration (`ANS`, `UPEN`, `active-INR`) and classical / SLAM-oriented exploration (`ExplORB`, `FBE`).
- Ablation separates no LLM / no localization uncertainty / `Llava-7b` / `GPT-4o`.
- Official code is publicly linked.
- Code README includes a real-world demo link, which is relevant to later deploy planning.

## Limitations

### 사실

- The paper evaluates in Habitat simulator on Gibson and HM3D.
- The supported robot motion is 3DOF ground-plane movement.
- The paper does not report ObjectNav `Success Rate`, `SPL`, wrong-goal visit, or wasted path.
- The paper does not report `RPE`.
- The method is not object-goal-navigation-specific.
- Future work mentions extending to higher DOF, task-driven exploration such as object search, and semantic feature grounding.

### 에이전트 추론

- Full reproduction has high engineering cost: 3DGS SLAM, Habitat setup, CUDA extensions, LLM API/local VLM, and dataset preparation are all required.
- Evaluation conflates improved reconstruction with improved pose accuracy to some extent; the paper reports `RMSE ATE`, but rendering quality is also treated as reflecting both reconstruction and pose quality.
- The LLM contribution may depend on prompt design, candidate annotation, and model choice.
- Semantic grounding is not yet part of the map representation, so this is not sufficient alone for environmental perception intelligence with object/node memory.
- The code README still exposes internal cluster paths and inconsistent data notes, so reproduction should start with a small scene probe rather than full benchmark.

## Relevance to My Research

### 사실

`CAND-01` aims to progress from semantic map object/node uncertainty, active re-observation viewpoint selection, ObjectNav behavior metrics, and then semantic memory as active SLAM utility with map error, semantic accuracy, `ATE/RPE`, and pose graph connectivity.

### 에이전트 추론

P09 directly supports the Step 4-5 thesis direction: active mobility should choose views not only for semantic/mapping gain but also for localization stability. For Step 1-3, it is better used as a design reference rather than direct baseline because it does not evaluate object-level uncertainty or ObjectNav success. For real-world deploy, the paper/code is relevant because it includes a real-world demo and 3DOF ground robot assumption, but it still lacks semantic object-level evaluation.

## Follow-up Questions

- Can `CAND-01` replace 3DGS Fisher Information with object/node uncertainty plus pose graph uncertainty while keeping the same two-level planning structure?
- What is the minimal probe: one Habitat scene, one object category, and a pre-explored semantic map with noisy object confidence?
- Should P09 be treated as an implementation baseline, or as a metric/design reference for Step 4-5?
- Can `RMSE ATE` be extended to `ATE/RPE` and pose graph connectivity in the `CAND-01` evaluation harness?
- If semantic re-observation improves ObjectNav but worsens ATE/RPE, is that a failure or a tradeoff worth modeling?
