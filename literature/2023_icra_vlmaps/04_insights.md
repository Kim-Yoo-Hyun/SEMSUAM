# Insights

## Facts

- `VLMaps: Visual Language Maps for Robot Navigation` is an `ICRA 2023` paper.
- arXiv records `arXiv:2210.05714v4`, last revised 2023-03-08.
- The official code repository is public and MIT licensed.
- The local PDF has 11 pages.
- The paper evaluates multi-object navigation, spatial goal navigation, cross-embodiment obstacle maps, top-down semantic segmentation, and real-world HSR navigation.
- The method uses `LSeg` visual embeddings, `CLIP` text embeddings, RGB-D back-projection, and top-down feature fusion.

## Paper Claims

- `VLMaps` brings spatial precision to pretrained visual-language features by grounding them in a 3D/top-down map.
- `VLMaps` can localize open-vocabulary object and spatial goals without additional labeled data or model finetuning.
- `VLMaps` outperforms `LM-Nav`, `CoW`, and `CLIP Map` on the paper's long-horizon multi-object and spatial-goal navigation tasks.
- The same `VLMap` can generate different obstacle maps for different robot embodiments.

## Inferences

- `VLMaps` is a necessary baseline for the thesis direction because many later semantic-memory navigation papers assume or extend this style of pre-explored open-vocabulary map.
- The strongest thesis gap is not "build a language-indexed map"; `VLMaps` already establishes that. The gap is uncertainty-aware repair: when the map is noisy or ambiguous, the agent should actively re-observe before committing to a wrong goal.
- `VLMaps` provides several uncertainty proxies: text-map similarity margin, feature variance from multi-view averaging, entropy over category similarity, disagreement with geometry/obstacle map, and repeated failure at the selected goal.
- For Step 4-5, `VLMaps` is only a representation baseline. It does not connect semantic uncertainty to SLAM pose uncertainty or pose graph quality.

## 사용자 판단 필요

- `VLMaps`를 `CAND-01` Stage 1 direct baseline으로 실행할지 결정해야 한다.
- Matterport3D access and OpenAI API dependency를 허용할지 확인해야 한다.
- First probe를 official object-goal navigation task로 할지, map indexing + synthetic perturbation으로 더 작게 시작할지 정해야 한다.

## Connection to Field Trends

- Strong connection: pre-explored open-vocabulary semantic map.
- Strong connection: language-indexed navigation memory.
- Strong connection: foundational baseline for `CARe`, `DualMap`, and related semantic-memory systems.
- Moderate connection: environmental perception intelligence through map reuse.
- Weak connection: active SLAM uncertainty, dynamic map update, and real-time adaptation.

## Possible Contribution Angles

- `VLMaps` text-query heatmap confidence를 object/node uncertainty로 정의한다.
- Low-confidence or high-ambiguity landmarks에 대해 active re-observation viewpoint를 선택한다.
- `VLMaps` baseline의 wrong-goal visit and wasted path를 `CARe` / active re-observation variant와 비교한다.
- `VLMaps` map-cell uncertainty와 SLAM pose/map uncertainty를 결합해 Step 4-5 active SLAM utility로 확장한다.

## What Would Change This Assessment

- Official code가 현재 환경에서 Matterport3D 없이도 demo/small scene으로 바로 작동하면 first implementation baseline으로 우선순위를 올린다.
- If `CARe` provides a cleaner `VLMaps`-based pre-explored map pipeline, `VLMaps`는 직접 실행 baseline보다 representation ancestor로 두는 편이 낫다.
- If map uncertainty from `VLMaps` heatmaps is poorly calibrated, semantic uncertainty should be estimated from multi-view consistency or object-level graph checks instead.
