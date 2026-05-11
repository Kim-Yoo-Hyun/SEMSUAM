# Paper Card

## Problem

traditional 3D scene understanding은 labeled 3D datasets와 fixed task labels에 의존해 open-vocabulary query에 약하다.

## Core Idea

dense 3D point feature를 CLIP-aligned image/text space에 co-embed하여 arbitrary text query로 3D scene understanding을 수행한다.

## Input / Output

Input: 3D point cloud / RGB-D data and text query. Output: dense 3D relevance/semantic predictions.

## Method

- 2D image/text foundation feature를 3D point feature와 align한다.
- labeled 3D data 없이 open-vocabulary 3D semantic understanding을 수행한다.
- object/material/affordance/activity/room type query를 지원한다.

## Main Claims

- zero-shot 3D semantic segmentation and open-vocabulary scene understanding이 가능하다고 주장한다.

## Strengths

- open-vocabulary 3D semantic map backbone으로 널리 쓰일 수 있다.
- CVPR 2023 + official code.

## Limitations

- offline scene understanding 중심이며 online SLAM/map update는 별도 필요하다.
- navigation metric은 직접 중심이 아니다.

## Relevance to My Research

open-vocabulary semantic landmark/memory representation 후보이다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
