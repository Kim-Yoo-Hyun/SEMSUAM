# Paper Card

## Problem

Zero-shot ObjectNav에서 existing LLM prompting methods는 주로 nearby object category text를 사용한다. 이 방식은 scene의 room/group/object hierarchy, spatial relation, long-range relation을 충분히 표현하지 못해 goal object가 보이지 않는 상황에서 frontier 선택이 불안정해진다.

## Core Idea

Observed scene을 object / group / room node와 edge가 있는 online 3D scene graph로 유지하고, hierarchical chain-of-thought prompt로 LLM이 goal object와 subgraph/frontier의 관련성을 추론하게 한다. Goal object가 detection되면 graph-based re-perception으로 multi-view evidence를 누적해 false positive goal visit을 줄인다.

## Input / Output

- Input: RGB-D observation, object goal category, online occupancy map, online 3D scene graph, object detections.
- Output: selected frontier / navigation subgoal, goal confirmation decision, re-perception result.

## Method

- Online 3D scene graph: detected object를 node로 추가하고 group / room node를 구성한다.
- Edge construction: 새 node와 기존 node 사이 relation을 batch prompt로 LLM에 묻고, short-range edge는 VLM으로 검증하며, long-range edge는 wall / room relation으로 pruning한다.
- H-CoT prompting: node / edge / subgraph 정보를 LLM prompt로 넣어 goal distance와 reasoning summary를 만들고, subgraph probability를 frontier score로 interpolation한다.
- Navigation: frontier-based exploration과 local policy를 사용해 selected frontier로 이동한다.
- Re-perception: goal object가 보이면 여러 viewpoint에서 관측을 누적하고 credibility score가 threshold를 넘을 때만 success로 확정한다. Threshold를 넘지 못하면 false positive로 보고 exploration을 계속한다.

## Main Claims

- MP3D, HM3D, RoboTHOR에서 zero-shot ObjectNav baselines보다 높은 `SR` / `SPL`을 보인다고 주장한다.
- Scene graph와 re-perception을 함께 쓰면 nearby-object prompt만 쓰는 baseline보다 success가 개선된다고 주장한다.
- MP3D에서 일부 supervised ObjectNav references보다 높은 `SR`을 달성한다고 주장한다.

## Strengths

- Scene graph가 LLM-readable planning interface로 쓰여 environmental perception intelligence를 navigation action으로 연결한다.
- Re-perception mechanism이 object detection uncertainty와 wrong-goal confirmation 문제를 명시적으로 다룬다.
- MP3D, HM3D, RoboTHOR 세 benchmark에서 평가해 ObjectNav metric surface가 비교적 넓다.
- Ablation이 scene graph, re-perception, room/group node, edge, CoT prompting contribution을 분리한다.

## Limitations

- Online 3D instance segmentation, VLM verification, LLM prompt quality에 강하게 의존한다.
- Re-perception은 false positive를 줄이지만 false goal에 접근한 뒤 여러 view를 확인하므로 wasted path가 생길 수 있다.
- SLAM pose uncertainty, pose graph connectivity, map error, semantic map uncertainty는 직접 metric으로 평가하지 않는다.
- ObjectNav 중심이며 ImageNav / VLN / active SLAM까지는 평가하지 않는다.

## Relevance to My Research

Step 1-3에 직접 연결된다. 특히 semantic node confidence, goal credibility, multi-view re-observation, wrong-goal handling을 CAND-01의 first experiment metric으로 가져올 수 있다. 다만 Step 4-5의 SLAM uncertainty까지 보려면 SG-Nav graph를 pose graph / map error metric과 연결하는 추가 설계가 필요하다.

## Follow-up Questions

- `SG-Nav`의 credibility score를 CAND-01의 object/node uncertainty로 변환할 수 있는가?
- Re-perception을 수행하기 전의 uncertainty-aware viewpoint selection을 추가하면 `wrong-goal visit`과 `wasted path`를 줄일 수 있는가?
- LLM reasoning 없이 graph heuristic / confidence-only baseline을 두면 semantic map contribution을 분리할 수 있는가?
