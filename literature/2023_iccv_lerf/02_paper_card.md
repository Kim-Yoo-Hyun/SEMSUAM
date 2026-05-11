# Paper Card

## Problem

3D radiance field가 geometry/appearance는 잘 표현하지만 open-ended natural language query를 3D에서 직접 ground하기 어렵다.

## Core Idea

NeRF 내부에 multi-scale language field를 학습해 CLIP embeddings를 volume rendering으로 3D에 ground한다.

## Input / Output

Input: posed images and language queries. Output: 3D language relevancy map / localized query response.

## Method

- CLIP embeddings를 training rays along volume rendering으로 supervise한다.
- multi-scale language field를 NeRF 안에 학습한다.
- long-tail text query에 대한 3D relevance를 출력한다.

## Main Claims

- LERF는 open-ended language queries를 3D radiance field에서 localize할 수 있다고 주장한다.

## Strengths

- language-queryable 3D memory의 foundational reference다.
- long-tail query와 multi-view consistency를 다룬다.

## Limitations

- per-scene optimization cost가 크고 online robot SLAM에는 heavy하다.
- navigation success나 active planning metric은 직접 다루지 않는다.

## Relevance to My Research

open-vocabulary memory가 neural field 안에 들어갈 수 있다는 representation reference다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
