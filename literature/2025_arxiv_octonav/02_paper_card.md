# Paper Card

## Problem

Embodied navigation research가 ObjNav, ImgNav, VLN 등 task별로 갈라져 있어 compound multimodal/capability instruction을 평가하기 어렵다.

## Core Idea

OctoNav-Bench와 OctoNav-R1을 제안해 free-form multimodal/multicapability instruction-trajectory pairs로 generalist navigation을 평가한다.

## Input / Output

Input: free-form multimodal navigation instruction. Output: trajectory/action satisfying mixed capabilities.

## Method

- continuous environments 기반 benchmark를 구성한다.
- annotation pipeline으로 diverse instruction-trajectory pairs를 만든다.
- corresponding method OctoNav-R1을 제안한다.

## Main Claims

- generalist navigation agent 평가를 위한 large-scale benchmark와 method를 제공한다고 주장한다.

## Strengths

- 연구 harness 설계에 직접 참고할 수 있다.
- task 통합 평가 기준을 제시한다.

## Limitations

- arXiv 상태이며 benchmark adoption은 아직 확인 필요하다.
- SLAM/map uncertainty는 중심이 아닐 수 있다.

## Relevance to My Research

master research harness를 만들 때 task taxonomy와 evaluation surface를 참고할 수 있다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
