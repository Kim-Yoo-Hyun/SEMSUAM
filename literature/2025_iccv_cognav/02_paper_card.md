# Paper Card

## Problem

ObjectNav는 perception뿐 아니라 search state, decision-making, target identification 같은 cognitive process가 필요하지만 기존 methods는 simulator rollout learning이나 heuristic rule에 의존한다.

## Core Idea

LLM이 heterogeneous cognitive map을 보고 finite state machine의 cognitive state transitions를 결정한다.

## Input / Output

Input: online scene graph/landmark graph/occupancy map, ObjectNav goal, current observation. Output: cognitive state and navigation decision.

## Method

- fine-grained cognitive states를 finite state machine으로 모델링한다.
- heterogeneous cognitive map에 spatial and semantic information을 저장한다.
- LLM이 state transition과 map update/correction을 reasoning한다.

## Main Claims

- HM3D, MP3D, RoboTHOR에서 ObjectNav success rate를 SOTA 대비 relative 14% 이상 개선한다고 주장한다. arXiv abstract는 HM3D SOTA를 69.3%에서 87.2%로 높였다고 주장한다.

## Strengths

- cognitive map이 semantic planning interface로 쓰인다.
- ICCV 2025 최신 ObjectNav top-tier paper다.

## Limitations

- LLM dependency와 prompt cost/reproducibility 리스크가 있다.
- SLAM map accuracy metric과 직접 연결되지는 않는다.

## Relevance to My Research

environmental perception intelligence가 navigation state machine으로 변환되는 최신 예시다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
