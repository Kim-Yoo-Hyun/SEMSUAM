# Paper Card

## Problem

VLN에서 out-of-distribution scene과 Sim2Real generalization이 어렵고, map/depth/odometer 입력은 noise와 sim2real gap을 만든다.

## Core Idea

monocular RGB video stream과 instruction만으로 video-based VLM이 next-step action을 예측한다.

## Input / Output

Input: online monocular RGB video stream and language instruction. Output: next-step navigation action.

## Method

- historical observations를 video spatio-temporal context로 encoding한다.
- map, odometer, depth 없이 VLM이 next action을 planning한다.
- continuous environments의 navigation samples와 web data로 학습한다.

## Main Claims

- maps, odometers, depth inputs 없이 state-of-the-art-level navigation performance와 Sim2Real transfer를 보인다고 주장한다.

## Strengths

- SLAM-centric pipeline의 강한 competing baseline이다.
- history representation이 map memory의 대체물로 작동한다.

## Limitations

- explicit map/pose/uncertainty가 없어 SLAM 연구의 hard metric과 직접 비교가 어렵다.
- large-scale training data가 필요하다.

## Relevance to My Research

SLAM-free baseline으로 반드시 비교해야 할 축이다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
