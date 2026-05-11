# Paper Card

## Problem

ObjectNav methods가 single-step action planning에 의존하면 temporal consistency가 약하고 myopic planning이 생긴다.

## Core Idea

current observation and goal에 conditioned된 future trajectory sequence distribution을 DDPM으로 학습해 temporally coherent waypoint/trajectory를 생성한다.

## Input / Output

Input: current observation, semantic map/state, object goal. Output: future trajectory sequence / waypoint.

## Method

- automatically collected optimal trajectory segments로 diffusion model을 학습한다.
- semantic map embedding과 target object embedding을 condition으로 사용한다.
- generated trajectory의 waypoint를 navigation goal로 사용한다.

## Main Claims

- Gibson and MP3D에서 generated trajectories가 더 accurate and efficient navigation을 유도한다고 주장한다.

## Strengths

- single-step policy가 아닌 sequence planning을 ObjectNav에 넣는다.
- NeurIPS 2024 + code available.

## Limitations

- optimal trajectory segment training data가 필요하다.
- semantic map 품질/uncertainty를 직접 수정하지 않는다.

## Relevance to My Research

semantic map을 사용한 planner output을 sequence로 바꾸는 대안 baseline이다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
