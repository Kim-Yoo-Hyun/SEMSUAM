# Paper Card

## Problem

OVMM robot은 unseen dynamic environment에서 semantic map을 만들고 natural language instruction을 이해하며 navigation/manipulation plan을 수정해야 한다.

## Core Idea

VLM zero-shot detection/grounding과 dense 3D entity reconstruction으로 3D semantic map을 만들고 LLM으로 spatial abstraction과 online planning/replanning을 수행한다.

## Input / Output

Input: robot observations, VLM detections, 3D reconstruction, human language instruction. Output: semantic map, plan, navigation/manipulation action.

## Method

- 3D semantic map을 dense entity reconstruction으로 구축한다.
- LLM이 spatial semantic context를 사용해 online planning한다.
- initial plan failure 시 candidate location으로 replanning한다.

## Main Claims

- real-world JSR-1 platform에서 navigation and task success를 높이고 dynamic setting에서 replanning이 가능하다고 주장한다.

## Strengths

- real robot, language instruction, dynamic environment를 함께 다룬다.
- semantic map을 action/replanning에 직접 사용한다.

## Limitations

- mobile manipulation까지 포함해 research scope가 크다.
- standard benchmark보다 custom real robot episodes 중심이다.

## Relevance to My Research

semantic map이 dynamic replanning에 쓰이는 실사용 예시로 참고 가치가 있다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
