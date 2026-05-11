# Paper Card

## Problem

3DGS active mapping에서 candidate viewpoint를 평가하려면 rendering-based information gain을 효율적으로 계산해야 한다.

## Core Idea

GaussianMap의 efficient rendering을 활용해 coarse-to-fine candidate evaluation과 active mapping을 수행한다.

## Input / Output

Input: current Gaussian map, candidate viewpoints, RGB-D rendering losses. Output: selected next view and updated Gaussian map.

## Method

- GaussianMap rendering으로 candidate utility를 빠르게 평가한다.
- coarse-to-fine strategy로 planning 비용을 줄인다.
- color/depth rendering loss로 map optimization을 수행한다.

## Main Claims

- efficient rendering 기반 active Gaussian mapping이 mapping quality와 exploration efficiency를 개선한다고 주장한다.

## Strengths

- CVPR 2025 최신 3DGS active mapping baseline이다.
- viewpoint utility 계산 비용 문제를 직접 다룬다.

## Limitations

- semantic memory나 navigation goal reasoning은 중심이 아니다.
- Replica and MP3D 중심 평가라 real robot localization failure는 별도 검증이 필요하다.

## Relevance to My Research

3DGS backbone을 쓰는 경우 candidate viewpoint scoring baseline으로 유용하다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
