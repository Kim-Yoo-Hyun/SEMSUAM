# Paper Card

## Problem

floor-plan이나 sketch처럼 inaccurate abstract map은 metric geometry가 부족하지만 인간은 이를 behavior-level navigation에 활용한다.

## Core Idea

Scene Action Map이라는 behavioural topological graph를 만들고 learnable map-reading method로 2D abstract maps를 navigation behaviours로 변환한다.

## Input / Output

Input: abstract 2D map / floor-plan / sketch. Output: behavioural topological graph and route/behavior plan.

## Method

- abstract map에서 salient navigational behaviours를 추출한다.
- places를 nodes, behaviours를 edges로 표현한다.
- quadrupedal robot behavioural navigation stack에 배치한다.

## Main Claims

- metric information 없이도 abstract inaccurate map에서 navigation-relevant behaviour graph를 추출해 real robot navigation에 사용할 수 있다고 주장한다.

## Strengths

- environment prior를 metric map이 아니라 behavior graph로 쓰는 관점이 독특하다.
- ICRA 2024 + project page available.

## Limitations

- object-goal semantic search나 SLAM map building은 중심이 아니다.
- dataset release 상태는 project page 기준 coming/확인 필요.

## Relevance to My Research

pre-existing map/prior를 navigation action으로 변환하는 다른 방식의 reference다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
