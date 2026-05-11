# Paper Card

## Problem

기존 mapping은 map을 만든 뒤 expensive planner가 path를 찾는 식이라 mapping과 motion planning이 분리되어 있다.

## Core Idea

arrival time field를 mapping feature로 학습하고 Eikonal equation을 physics-informed neural network로 풀어 mapping과 planning을 동시에 지원한다.

## Input / Output

Input: environment observations and robot state. Output: neural arrival time field and motion plan.

## Method

- Active Neural Time Fields를 online으로 학습한다.
- arrival time field가 planner guidance로 직접 쓰인다.
- expert data 없이 Eikonal equation을 neural network로 푼다.

## Main Claims

- simulated and real-world environments에서 mapping/planning baselines보다 좋은 performance를 보인다고 주장한다.

## Strengths

- map representation 자체를 planning-friendly하게 설계한다.
- real robot differential drive와 manipulator evaluation이 있다.

## Limitations

- semantic perception intelligence는 다루지 않는다.
- SLAM uncertainty와 object-goal navigation metric은 중심이 아니다.

## Relevance to My Research

planning-friendly map representation이라는 관점은 semantic map 설계에도 중요하다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
