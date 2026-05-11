# Paper Card

## Problem

RGB-D SLAM에서 tracking과 dense mapping을 high-quality renderable map representation으로 동시에 처리해야 한다.

## Core Idea

3D Gaussian representation을 online tracking and mapping에 직접 사용해 pose tracking, dense map update, rendering quality를 함께 최적화한다.

## Input / Output

Input: RGB-D stream. Output: camera poses and 3D Gaussian map.

## Method

- current RGB-D frame과 accumulated Gaussian map을 사용해 tracking한다.
- color/depth rendering losses로 map을 update한다.
- 3DGS explicit representation을 dense SLAM map으로 사용한다.

## Main Claims

- dense RGB-D SLAM tracking, mapping, rendering accuracy에서 prior dense baselines보다 strong result를 보인다고 주장한다.

## Strengths

- 3DGS를 SLAM backbone으로 쓰는 대표 baseline이다.
- Replica, TUM-RGBD, ScanNet++ 등 standard datasets와 비교한다.

## Limitations

- semantic intelligence와 active planning은 포함하지 않는다.
- RGB-D input과 compute budget에 의존한다.

## Relevance to My Research

3DGS active mapping 계열의 map backbone baseline으로 중요하지만, user research에서는 semantic/action layer를 별도로 얹어야 한다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
