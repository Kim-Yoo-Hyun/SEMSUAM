# Insights

## Facts

- `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information` is an ICCV 2025 paper.
- Primary source is the CVF open access page: https://openaccess.thecvf.com/content/ICCV2025/html/Jiang_Multimodal_LLM_Guided_Exploration_and_Active_Mapping_using_Fisher_Information_ICCV_2025_paper.html
- arXiv source is https://arxiv.org/abs/2410.17422, with v3 last revised on 2025-09-05.
- Official code linked by the author is https://github.com/JiangWenPL/multimodal-active
- The method uses 3DGS, multimodal LLM long-horizon planning, Expected Information Gain, Fisher Information, and localization uncertainty.
- Evaluation uses Habitat Simulator with Gibson and HM3D.
- Metrics are `PSNR`, `SSIM`, `LPIPS`, `Depth MAE`, `RMSE ATE`, and `Completeness`.
- Baselines include `ANS`, `UPEN`, `active-INR`, `ExplORB`, and `FBE`.
- The paper does not report ObjectNav `Success Rate`, `SPL`, wrong-goal visit, wasted path, `RPE`, semantic accuracy, or pose graph connectivity.
- The paper's future work explicitly mentions higher-DOF motion, task-driven object search, and semantic feature grounding.

## Paper Claims

- The method is the first 3DGS active mapping system that does not depend on ground-truth camera pose readings.
- Multimodal LLM can be used as a zero-shot long-horizon exploration planner from a semantic scene-layout perspective.
- Fisher Information can quantify both scene information gain and localization uncertainty for path selection.
- Balancing EIG and localization cost improves mapping and tracking.
- The method achieves state-of-the-art active mapping results on Gibson and HM3D against reported baselines.
- Ablations support that localization uncertainty and `GPT-4o` long-horizon planning improve the reported metrics.

## Inferences

### 에이전트 추론

P09 is strong evidence for `CAND-01` Step 4-5: semantic / prior-based exploration should be coupled with localization-aware active SLAM utility. It is weaker evidence for Step 1-3 because the paper does not define object/node uncertainty and does not evaluate ObjectNav behavior.

For the current thesis direction, the most reusable pieces are:

- two-level planner: semantic coarse target followed by SLAM-aware short-term path
- metric bundle: map quality plus tracking accuracy plus completeness
- failure split: semantic target selection failure vs localization failure vs reconstruction failure
- ablation shape: no semantic planner, no localization uncertainty, full method

Full system reproduction is probably not the first milestone. A smaller `CAND-01` probe can test whether uncertain semantic memory should trigger re-observation viewpoints, then later add SLAM uncertainty and pose graph metrics.

## 사용자 판단 필요

- P09를 implementation baseline으로 둘지, Step 4-5 design / metric reference로 둘지 결정해야 한다.
- `CAND-01` first probe에서 `RMSE ATE`만 사용할지, planned final metric처럼 `ATE/RPE` and pose graph connectivity까지 포함할지 결정해야 한다.
- Full 3DGS SLAM을 직접 재현할지, existing SLAM/log replay에서 uncertainty proxy를 뽑는 lightweight route로 갈지 결정해야 한다.
- Real-world deploy를 고려한다면 P09 code의 3DOF ground robot assumption을 실험 장비 후보와 맞춰야 한다.

## Connection to Field Trends

- Strong evidence for active perception / active mapping moving from coverage-only exploration to information-theoretic utility.
- Strong evidence for SLAM-navigation coupling because path selection explicitly considers localization uncertainty.
- Moderate evidence for environmental perception intelligence because multimodal LLM uses scene-layout prior, but semantic map grounding is not evaluated.
- Indirect evidence for ObjectNav-oriented semantic memory because task-driven object search is listed as future work, not demonstrated.

## Possible Contribution Angles

- Replace multimodal LLM long-horizon planning with pre-explored semantic memory retrieval and evaluate whether ObjectNav behavior improves.
- Replace 3DGS Fisher Information with semantic object/node uncertainty plus SLAM uncertainty proxy.
- Add object-level failure metrics missing in P09: wrong-goal visit and wasted path.
- Add `RPE` and pose graph connectivity to complement `RMSE ATE`.
- Use the same ablation logic: `SemanticOnly`, `SLAMOnly`, `SemanticSLAM`, and `NoReobserve`.
- Evaluate if a lightweight semantic map can get part of P09's localization-aware planning benefit without full 3DGS.

## What Would Change This Assessment

- If the official code runs on one local Habitat scene with manageable GPU memory, P09 can become a stronger implementation baseline for Step 4-5.
- If code reproduction requires unavailable internal checkpoints or dataset paths, use P09 as design / metric evidence only.
- If `CAND-01` first experiments show no ObjectNav benefit from semantic re-observation, P09 relevance shifts toward SLAM utility rather than semantic memory.
- If real-world deploy becomes a near-term milestone, the paper's 3DOF ground robot setup and linked real-world demo become more important than the simulator benchmark.
- If semantic feature grounding is added to 3DGS in a follow-up work, this paper may become a direct baseline for the full thesis direction.
