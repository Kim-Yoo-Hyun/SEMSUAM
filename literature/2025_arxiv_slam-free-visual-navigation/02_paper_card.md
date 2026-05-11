# Paper Card

## Problem

legged robot navigation에서 conventional SLAM은 rapid motion, calibration, sensor drift에 fragile하고 semantic reasoning이 약하다.

## Core Idea

dense geometry 대신 hierarchical vision-language perception과 semantic-probabilistic topological map으로 coarse-to-fine planning을 수행한다.

## Input / Output

Input: vision observations, language/semantic cues, topological state. Output: subgoal and local navigation action.

## Method

- scene-level context와 object-level cues를 hierarchical perception으로 fuse한다.
- LLM-based global reasoning으로 subgoal을 선택한다.
- vision-based local planning으로 obstacle avoidance를 처리한다.

## Main Claims

- simulation and real-world settings에서 semantic accuracy, planning quality, navigation success를 개선한다고 주장한다.

## Strengths

- SLAM-free baseline의 최신 방향을 보여준다.
- semantic topological map이 dense metric map의 대안으로 제시된다.

## Limitations

- arXiv 상태이며 full benchmark detail 확인 필요.
- SLAM 연구의 map/pose metric과 직접 비교하기 어렵다.

## Relevance to My Research

SLAM을 포함하는 연구라면 비교해야 할 map-light semantic navigation baseline이다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
