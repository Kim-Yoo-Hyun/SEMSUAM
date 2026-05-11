# Paper Card

## Problem

Real-world natural language navigation needs three capabilities at once: open-vocabulary object understanding, efficient online semantic mapping, and navigation under dynamic object changes. Prior open-vocabulary mapping systems such as `ConceptGraphs` and `HOV-SG` can represent language-queryable objects, but the paper argues they are either too expensive for online use or assume static scenes. Dynamic systems such as `Khronos` and `OpenIN` address change, but either lack arbitrary language queries or rely on slower offline mapping/navigation pipelines.

## Core Idea

`DualMap` separates semantic memory into two maps. A detailed online `concrete map` stores object-level geometry, semantic features, class IDs, timestamps, and observations. A lighter `abstract map` retains static anchor objects and the semantic features of volatile objects spatially associated with those anchors. Navigation first uses the abstract map for global candidate selection, then builds a local concrete map online near the candidate to verify the target and update the abstract map if the object has moved.

## Input / Output

- Input: posed RGB-D stream, natural language query, GPT-generated indoor object category list, open-vocabulary segmentation results.
- Output: online concrete semantic map, anchor-based abstract map, global navigation candidate, local target object, updated abstract map after failed or changed observations.
- Robot setup: simulated Habitat agents; real wheeled and quadruped platforms with RGB-D camera and LiDAR-based pose estimation.

## Method

- Hybrid segmentation frontend: `YOLOv8l-world` produces fast object-level detections from a GPT-generated category list, `MobileSAM` generates masks, and `FastSAM` supplements open-set segments outside the YOLO list.
- Semantic feature embedding: object crop CLIP image feature and class-label CLIP text feature are fused with weights 0.7 and 0.3; `MobileCLIP-S2` is used in the main experiments.
- Observation structure: each observation stores point cloud, semantic feature, class ID, and timestamp.
- Object association: observations are matched to map objects by semantic cosine similarity plus 3D point cloud overlap.
- Object status check: stability check removes noisy/short-lived objects; split detection separates under-segmented objects when different class IDs persist at the same timestamps.
- Abstract map: static anchor objects are kept; volatile object features are attached to related anchors, focusing on the `on` relation.
- Candidate retrieval: query embedding is compared with anchor features and attached volatile-object features; the best-scoring anchor becomes the global navigation candidate.
- Navigation: Voronoi-based global path planning goes to the anchor, local concrete mapping verifies candidate objects, and `RRT*` plans the local path to the target.
- Dynamic update: if the target is not found near the selected anchor, the local concrete map updates the abstract map and the system reselects a candidate.

## Main Claims

- `DualMap` is the first compared system in the paper's Table I to support open-vocabulary mapping, online mapping, and dynamic handling together.
- `DualMap` achieves state-of-the-art or best reported results in open-vocabulary 3D semantic segmentation and efficiency on `Replica` and `ScanNet`.
- `DualMap` improves object navigation Success Rate on static and dynamic `HM3D` scenes.
- Real-world wheeled and quadruped experiments show practical applicability in indoor, outdoor, and moved-object cases.

## Strengths

- The abstract/concrete split is directly useful for separating global prior memory from local verification.
- The paper evaluates both mapping quality and navigation behavior, including dynamic moved-object cases.
- The system is online and code is public.
- The real-world evaluation is unusually relevant for this research direction because it includes both wheeled and quadruped platforms.
- Failure modes are quantified for cross-anchor dynamic navigation.

## Limitations

- `DualMap` does not perform camera pose estimation and relies on external localization.
- The paper does not report `ATE`, `RPE`, pose graph connectivity, loop closure, or SLAM uncertainty.
- Navigation uses known poses and planning modules; localization failure is not the central variable.
- Human-object interaction reasoning is not included.
- Outdoor performance degrades due to higher sensor noise.
- Dynamic handling focuses on object relocation, not full long-term world-model staleness or human activity modeling.

## Relevance to My Research

`DualMap` is highly relevant to `CAND-01` Step 1-3 because it provides a concrete mechanism for object status checking, local verification, map update, candidate reselection, and dynamic ObjectNav-style success evaluation. It is also relevant to real-world deploy planning because it uses RGB-D + LiDAR pose estimation and ROS. For Step 4-5, the relevance is indirect: `DualMap` updates semantic memory during navigation, but it does not optimize active SLAM utility or measure SLAM map/pose quality.

## Follow-up Questions

- Can `DualMap`'s stability check, split detection, failed-anchor update, and candidate score be converted into calibrated object/node uncertainty?
- Can active re-observation viewpoints reduce `DualMap`'s false-match failures in cross-anchor relocation?
- Can the same dynamic update loop be extended to measure semantic accuracy plus `ATE`, `RPE`, map error, and pose graph connectivity?
- Is the public `DualMap` code light enough to use as a real-world or Habitat baseline for the first thesis experiment?
