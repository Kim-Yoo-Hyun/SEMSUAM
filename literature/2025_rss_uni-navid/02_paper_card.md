# Paper Card

## Problem

practical navigation agent는 VLN, ObjectNav, EQA, human following 등 다양한 navigation demand를 하나의 framework에서 처리해야 한다.

## Core Idea

video-based VLA model로 embodied navigation tasks의 input/output을 통합하고 mixed long-horizon tasks를 unseen real-world environments에서 처리한다.

## Input / Output

Input: egocentric RGB video and task instruction/query. Output: navigation action sequence.

## Method

- task input/output format을 harmonize한다.
- four essential navigation subtasks의 3.6M samples로 학습한다.
- video context를 통해 multi-task navigation action을 생성한다.

## Main Claims

- unified model로 comprehensive navigation benchmarks에서 SOTA performance를 달성하고 real-world effectiveness를 보인다고 주장한다.

## Strengths

- task-general navigation baseline이다.
- RSS 2025 primary source로 robotics relevance가 높다.

## Limitations

- large-scale data/model training이 필요해 석사 구현에는 heavy하다.
- explicit semantic map이나 SLAM uncertainty를 제공하지 않는다.

## Relevance to My Research

explicit map 없이도 history가 얼마나 충분한지 보는 upper/competing baseline이다.

## Follow-up Questions

- 이 논문의 map/perception representation을 active SLAM 또는 ObjectNav harness에서 어떤 최소 단위로 재현할 수 있는가?
- evaluation metric 중 내 연구의 contribution claim에 직접 연결되는 것은 무엇인가?
- 실패했을 때 semantic memory, localization uncertainty, planner 중 어느 부분의 한계로 분리해서 볼 수 있는가?
