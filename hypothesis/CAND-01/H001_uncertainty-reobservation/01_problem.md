# Problem

## Facts

- `CAND-01`은 pre-explored semantic memory를 robot mobility decision에 재사용해 ObjectNav와 SLAM/map consistency를 개선하는 것을 목표로 한다.
- 현재 H001은 Step 1-5 전체를 다룬다.
- Step 1-3은 first probe이고, Step 4-5의 SLAM uncertainty extension은 같은 H001 안에서 확장한다.

## Paper Claims

- `CARe`는 inaccurate pre-explored semantic map으로 인한 wrong decision을 confidence score와 multi-view consistency로 줄일 수 있다고 주장한다.
- `VLMaps`는 pretrained visual-language feature를 3D map에 fuse하면 language-indexed navigation이 가능하다고 주장한다.
- `ConceptGraphs`는 open-vocabulary 3D scene graph가 perception and planning에 유용하다고 주장한다.
- `SG-Nav`는 online 3D scene graph와 re-perception을 쓰면 zero-shot ObjectNav success가 개선된다고 주장한다.

## Inferences

- Semantic map 기반 navigation은 map candidate가 불확실할 때 "다시 관찰할지"를 명시적인 action decision으로 충분히 다루지 않는다.
- H001의 최종 방향은 semantic uncertainty와 SLAM uncertainty를 결합한 active re-observation이다. first probe는 semantic uncertainty가 navigation failure를 예측하고 줄일 수 있는지 먼저 확인한다.

## Why This Is Not Solved Yet

- Open-vocabulary semantic map은 false positive, false negative, ambiguous category, viewpoint-dependent detection에 취약하다.
- ObjectNav `Success Rate`와 `SPL`만 보면 semantic map error가 어떤 decision failure를 만들었는지 분리하기 어렵다.
- Replanning은 candidate를 바꾸는 행동이고, re-observation은 evidence를 새로 얻는 행동이다. 이 둘은 평가상 분리되어야 한다.

## User Decision Needed

- 첫 probe를 Habitat ObjectNav로 할지, Replica / ScanNet replay로 먼저 할지 결정해야 한다.
- `VLMaps` baseline을 우선할지 `CARe` code reproduction을 우선할지 결정해야 한다.
