# Paper Card

## Problem

Image-goal navigation에서 모든 historical observation을 decision에 쓰면 goal-relevant fraction을 구분하지 못해 exploration이 비효율적이다.

## Core Idea

short-term memory, long-term memory, working memory를 topological map 위에 구성해 goal-relevant scene features를 policy에 전달한다.

## Input / Output

Input: visual observations, image goal, topological map node features. Output: action policy using working memory.

## Method

- STM은 dynamically updated local node features를 저장한다.
- forgetting module이 informative STM fraction을 남긴다.
- LTM은 scene-level representation을 aggregate하고 WM은 STM/LTM을 goal-relevant하게 encoding한다.

## Main Claims

- Gibson과 Matterport3D multi-goal tasks에서 previous methods를 outperform하고 더 efficient routes를 계획한다고 주장한다.

## Strengths

- memory selection과 navigation efficiency를 직접 다룬다.
- topological map memory가 explicit하다.

## Limitations

- SLAM map quality나 pose uncertainty는 직접 중심이 아니다.
- learned policy 기반이라 환경/task transfer 확인이 필요하다.

## Relevance to My Research

prior observation을 모두 쓰지 않고 goal-relevant memory만 쓰는 설계가 user research에 중요하다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
