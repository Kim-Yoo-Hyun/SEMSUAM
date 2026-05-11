# Paper Card

## Problem

pre-explored semantic map 기반 ObjectNav는 map-query score가 높은 candidate를 목표로 고르는 방식에 의존한다. 하지만 semantic map은 VLM/vision backbone의 bias, view-dependent noise, 주변 물체 간섭 때문에 틀릴 수 있고, 기존 방식은 wrong map retrieval 후 계획을 어떻게 수정할지 약하다.

## Core Idea

Context-Aware Replanning (CARe)는 initial plan이 실패했을 때 top-k candidate set 안에서 map uncertainty와 multi-view consistency를 계산해 다음 target을 고른다. 핵심은 높은 confidence만 따라가지 않고, confidence score의 bias를 uncertainty signal로 보정하는 것이다.

## Input / Output

- Input: pre-explored semantic map, target object query, map-query scores, per-candidate view features or class probabilities, first-attempt failure signal.
- Output: revised candidate target / subgoal for the second retrieval or replanning attempt.

## Method

- CARe는 first attempt가 실패하면 high-confidence candidate set을 만든다.
- Candidate set 생성은 `Top-k Confidence`와 `Top-k Category`를 사용한다.
- Single-view uncertainty는 classification distribution entropy를 계산하고, high-confidence candidates 중 entropy가 가장 큰 candidate를 선택한다.
- Multi-view consistency는 `Channel-average Feature Standard Error`와 `Mean Pairwise KL Divergence`를 사용한다. Standard error와 KL divergence가 낮을수록 multi-view prediction이 consistent하다고 본다.
- OpenMask3D에서는 object mask별 visible views의 CLIP-ViT-L/14 crop features를 평균하지 않고 저장해 uncertainty를 계산한다.
- VLMaps에서는 LSeg feature projection으로 만든 map grid에 entropy, standard error, KL divergence를 추가 저장한다.

## Main Claims

- CARe는 additional labels 없이 inaccurate pre-explored semantic map 때문에 생긴 erroneous decision을 수정할 수 있다고 주장한다.
- CARe는 VLMaps와 OpenMask3D 두 backbone에서 max-confidence replanning보다 높은 ObjectNav / retrieval performance를 보인다고 주장한다.
- 논문은 high-confidence만 계속 고르는 방식이 첫 실패 이후 같은 model bias를 반복할 수 있으며, uncertainty와 multi-view consistency가 이 bias를 줄인다고 주장한다.

## Strengths

- 사용자의 연구 방향인 pre-explored semantic map uncertainty와 ObjectNav replanning에 직접 대응한다.
- `entropy`, `standard error`, `pairwise KL divergence`처럼 구현 가능한 uncertainty signal이 명확하다.
- VLMaps와 OpenMask3D 두 map backbone에 얹어 backbone-independent replanning idea로 제시한다.
- Project page, PMLR/OpenReview PDF, arXiv, official code가 있다.

## Limitations

- CARe는 fixed semantic map에서 re-planning만 수행하고, 실패 후 새 observation으로 map을 update하지 않는다.
- consistent decision bias가 있다는 가정에 의존한다. 모델이 online update되거나 bias가 바뀌면 효과가 줄 수 있다고 논문이 직접 적었다.
- SLAM pose graph uncertainty, localization uncertainty, ATE/RPE, map error는 평가하지 않는다.
- `SR`, `SPL` full navigation metric보다는 object retrieval success와 subgoal success 중심이다.
- Pairwise KL divergence는 `O(n^2)`이고 VLMaps 실험에서 일부 larger scenes를 memory limit 때문에 skip했다.

## Relevance to My Research

- CAND-01 Step 1의 object/node uncertainty 계산과 Step 3의 ObjectNav failure/replanning 평가에 가장 직접적인 paper다.
- Step 2 active re-observation viewpoint selection에는 간접적으로 연결된다. CARe는 candidate target을 다시 고르지만, uncertainty를 줄이기 위한 view selection은 하지 않는다.
- Step 4-5의 semantic memory -> active SLAM utility 확장은 CARe의 한계를 확장하는 방향이다. 특히 fixed map을 update하지 않는다는 한계가 내 연구의 map update / re-observation contribution surface가 된다.

## Follow-up Questions

- CARe의 `entropy`, `standard error`, `KL divergence` 중 어느 signal이 CAND-01의 semantic object/node uncertainty로 가장 안정적인가?
- CARe-style replanning을 active re-observation으로 바꾸면 second target을 고르는 대신 어떤 viewpoint를 선택해야 하는가?
- ObjectNav `wrong-goal visit`, `wasted path`, `SPL`을 추가하면 CARe의 subgoal success보다 더 thesis-relevant한 metric이 되는가?
- CARe의 fixed map limitation을 online semantic map update 또는 SLAM uncertainty와 연결할 때 최소 구현 단위는 무엇인가?
