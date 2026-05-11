# Paper Card

## Problem

Open-vocabulary 3D semantic mapping은 offline reconstruction / post-processing 중심인 경우가 많다. Robot navigation과 SLAM에서는 RGB-D stream을 받으면서 online으로 3D segment를 유지하고, loop closure 이후에도 semantic map을 수정할 수 있어야 하지만, 이런 end-to-end open-vocabulary online semantic SLAM pipeline은 제한적이다.

## Core Idea

RGB-D keyframe sequence에서 3D segment를 detect/track하고, multi-view visual-language descriptor를 learned CLIP merging으로 통합한다. 이 semantic mapper를 Gaussian-SLAM / ORB-SLAM2 backbone과 결합해 open-vocabulary online semantic map을 만든다.

## Input / Output

- Input: RGB-D frames, camera poses from ground-truth poses or SLAM backbone, 2D masks, CLIP/SigLIP features.
- Output: 3D point map, 3D segment instances, per-segment open-vocabulary descriptors, SLAM trajectory.

## Method

- 3D Segment Mapper: keyframe의 2D segments를 SAM2.1-l로 얻고 map point projection / label voting으로 기존 3D segment와 연결하거나 새 segment를 만든다.
- Open-vocabulary descriptor: full image, masked region, bounding box descriptor를 만들고 neural per-dimension weighted merging으로 multi-view descriptor를 통합한다.
- Loop closure handling: SLAM loop closure / GBA 이후 keyframe point cloud를 갱신하고, centroid distance / descriptor similarity / point proximity 조건으로 instance를 fuse한다.
- SLAM integration: ground-truth pose mapping, Gaussian-SLAM, ORB-SLAM2 variants를 비교한다.

## Main Claims

- Offline open-vocabulary baselines보다 낮은 compute / memory footprint와 competitive 또는 better segmentation metrics를 보인다고 주장한다.
- Neural CLIP merging이 기존 descriptor fusion보다 2D / 3D semantic classification 성능을 높인다고 주장한다.
- SLAM backbone과 결합해 ground-truth pose 없이 online open-vocabulary 3D mapping을 수행할 수 있다고 주장한다.

## Strengths

- open-vocabulary semantic mapping과 SLAM backbone을 직접 연결한다.
- ScanNet++/ScanNetv2/Replica 등 평가 surface가 넓다.
- Loop closure 이후 semantic map fusion을 다루므로 Step 5의 map error / pose error / semantic accuracy 연결에 유용하다.
- Runtime, memory, `ATE RMSE`, semantic segmentation metric을 함께 보고한다.

## Limitations

- Active exploration이나 navigation policy는 중심이 아니다.
- ObjectNav `SR` / `SPL` / wrong-goal visit 같은 downstream behavior metric은 평가하지 않는다.
- Semantic confidence가 active re-observation utility로 직접 쓰이지는 않는다.
- Outdoor large-scale scene, lighting / blur, tracking error가 어려울 수 있다고 논문이 언급한다.
- CLIP merging은 training class bias를 가질 수 있고, unseen class 성능은 별도로 봐야 한다.

## Relevance to My Research

Step 1과 Step 4-5에 직접 연결된다. CAND-01에서 object/node uncertainty를 open-vocabulary semantic map confidence로 만들고, loop closure 이후 semantic map correction과 `ATE` / `RPE` / semantic accuracy 변화를 측정하는 backbone 후보로 쓸 수 있다. 다만 Step 2-3 ObjectNav behavior를 보려면 별도 navigation harness가 필요하다.

## Follow-up Questions

- OVO segment descriptor / mask stability를 CAND-01의 node uncertainty로 정의할 수 있는가?
- Loop closure 전후 semantic map correction을 active SLAM utility로 측정할 수 있는가?
- Replica / ScanNetv2 subset에서 OVO map을 ObjectNav-style query와 연결할 수 있는가?
