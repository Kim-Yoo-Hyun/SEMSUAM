# Paper Card

## Problem

zero-shot navigation methods는 object category, instance image, text goal 등 goal type별 pipeline이 달라 universal goal-oriented navigation으로 generalize하기 어렵다.

## Core Idea

scene graph와 goal graph를 unified graph representation으로 만들고 graph matching state에 따라 exploration / coordinate projection / anchor alignment / verification 전략을 바꾼다.

## Input / Output

Input: online scene graph, goal graph from category/image/text. Output: long-term exploration goal and navigation decision.

## Method

- goal type을 graph representation으로 통일한다.
- scene graph와 goal graph matching을 수행한다.
- zero/partial/perfect matching state별 strategy와 blacklist mechanism을 사용한다.

## Main Claims

- single framework로 세 navigation tasks에서 SOTA zero-shot performance를 달성하고 task-specific zero-shot methods와 supervised universal methods를 능가한다고 주장한다.

## Strengths

- goal type generalization 문제를 graph interface로 푼다.
- CVPR 2025 latest top-tier paper다.

## Limitations

- scene graph construction quality에 강하게 의존한다.
- SLAM pose/map uncertainty는 직접 중심이 아니다.

## Relevance to My Research

semantic memory representation을 goal-conditioned graph matching으로 쓰는 방향을 보여준다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
