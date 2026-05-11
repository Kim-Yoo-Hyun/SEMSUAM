# Paper Card

## Problem

3DGS 기반 reconstruction에서 autonomous agent가 어떤 viewpoint를 선택해야 high-fidelity scene reconstruction을 빠르게 얻는지 결정해야 한다.

## Core Idea

Gaussian map과 viewpoint selection / path planning을 결합해 active high-fidelity reconstruction을 수행한다.

## Input / Output

Input: current Gaussian map, candidate viewpoints, robot pose/map state. Output: next viewpoint/path and improved Gaussian reconstruction.

## Method

- 3DGS map representation을 active reconstruction backbone으로 사용한다.
- viewpoint selection과 path planning을 결합한다.
- reconstruction fidelity와 exploration efficiency를 함께 본다.

## Main Claims

- ActiveSplat이 high-fidelity scene reconstruction에서 strong performance를 낸다고 주장한다.

## Strengths

- 3DGS를 passive reconstruction에서 active robotics setting으로 옮긴다.
- RA-L 2025 status로 robotics relevance가 높다.

## Limitations

- semantic SLAM, ObjectNav, pre-explored memory reuse는 직접 중심이 아니다.
- datasets와 robot constraints는 full read에서 확인 필요하다.

## Relevance to My Research

3DGS active mapping trend의 robotics-side evidence로 registry에 유지한다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
