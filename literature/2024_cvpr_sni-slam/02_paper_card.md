# Paper Card

## Problem

neural implicit SLAM은 geometry/tracking에 집중하는 경우가 많아 online semantic mapping과 semantic segmentation까지 동시에 처리하는 데 한계가 있다.

## Core Idea

semantic neural implicit representation으로 mapping/tracking accuracy와 semantic segmentation을 함께 수행한다.

## Input / Output

Input: RGB-D stream. Output: camera trajectory, neural implicit map, semantic map/segmentation.

## Method

- neural implicit representation에 semantic prediction을 통합한다.
- tracking, mapping, semantic segmentation을 joint framework로 구성한다.
- Replica와 ScanNet에서 geometry + semantics를 평가한다.

## Main Claims

- recent NeRF-based SLAM methods보다 mapping/tracking accuracy가 좋고 semantic segmentation도 우수하다고 주장한다.

## Strengths

- SLAM backbone과 semantic map을 함께 다룬다.
- Replica/ScanNet standard datasets 사용.

## Limitations

- active exploration과 environment memory reuse는 다루지 않는다.
- open-vocabulary가 아니라 fixed semantic label setting일 가능성이 높다.

## Relevance to My Research

semantic SLAM backbone 후보지만 active decision layer는 별도 설계해야 한다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
