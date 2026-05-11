# Paper Card

## Problem

open-world semantic navigation에서 foundation models는 semantic knowledge가 풍부하지만 spatial information을 scalable하게 organize/maintain하기 어렵다.

## Core Idea

Open Scene Graph를 spatial memory로 사용하고 environment type schema를 자동 생성해 OSG Navigator가 diverse goals/environments/embodiments에 zero-shot adapt하게 한다.

## Input / Output

Input: robot observations, semantic labels/environment type, object goal. Output: Open Scene Graph memory and navigation action.

## Method

- OSG schemas로 environment class의 common structure를 표현한다.
- foundation models와 modular navigator를 결합한다.
- Fetch and Spot embodiments에서 simulation/real experiments를 수행한다.

## Main Claims

- OSG Navigator가 ObjectNav benchmarks에서 SOTA performance를 달성하고 diverse goals, environments, robot embodiments에 zero-shot generalize한다고 주장한다.

## Strengths

- persistent scene memory와 open-world ObjectNav를 IJRR 수준으로 다룬다.
- simulation + real robot + multiple embodiments가 강점이다.

## Limitations

- schema generation assumption과 graph maintenance failure mode 확인 필요.
- active SLAM localization uncertainty는 중심이 아닐 수 있다.

## Relevance to My Research

persistent graph memory를 open-world ObjectNav에 쓰는 high-level target으로 중요하다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
