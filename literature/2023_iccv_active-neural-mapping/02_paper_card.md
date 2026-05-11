# Paper Card

## Problem

previously unseen environment에서 agent가 neural scene representation을 online으로 학습하면서 어디를 더 관찰해야 하는지 결정해야 한다.

## Core Idea

continually learned neural field의 weight-space neural variability를 instant map uncertainty로 사용해 traversable path와 target exploration space를 선택한다.

## Input / Output

Input: RGB-D / posed observations, neural map state, candidate paths. Output: next exploration target and updated neural map.

## Method

- coordinate-based implicit neural representation을 online으로 학습한다.
- random weight perturbation에 대한 prediction robustness를 uncertainty로 본다.
- continuous geometry와 uncertainty를 결합해 traversable exploration을 수행한다.

## Main Claims

- online active mapping system으로 neural representation의 uncertainty를 줄이며 효율적으로 환경을 학습한다고 주장한다.
- Gibson과 Matterport3D에서 efficacy를 보인다고 주장한다.

## Strengths

- uncertainty를 planner에 직접 연결한다.
- neural map이 geometry와 uncertainty signal을 동시에 제공한다.

## Limitations

- semantic map이나 navigation goal reasoning은 중심이 아니다.
- NeRF/implicit field 계열 compute cost와 online stability가 석사 구현 리스크다.

## Relevance to My Research

active SLAM에서 map representation uncertainty를 어떻게 planner objective로 넘길지 보는 핵심 참고문헌이다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
