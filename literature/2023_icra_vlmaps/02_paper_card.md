# Paper Card

## Problem

Pretrained vision-language models can match images to text, but image-level matching is disconnected from geometric mapping. Without spatial grounding, methods such as `CoW` and `LM-Nav` struggle with persistent map use, multi-view object correspondence, spatial goals such as "between the sofa and the TV", and embodiment-specific obstacle reasoning.

## Core Idea

`VLMaps` fuses dense pixel-level visual-language features into a 3D reconstruction and then into a top-down grid map. Each grid cell stores a visual-language feature vector. Text queries are encoded with a text encoder and localized by feature similarity, enabling open-vocabulary landmark indexing, spatial goal navigation, and obstacle map generation from language category lists.

## Input / Output

- Input: RGB-D frames, camera poses / odometry, camera intrinsics, free-form text category or navigation instruction.
- Intermediate representation: top-down visual-language map `M in R^(H x W x C)`.
- Output: landmark masks, target positions, embodiment-specific obstacle maps, executable navigation primitive calls from LLM-generated code.

## Method

- Dense feature extraction: uses `LSeg` visual encoder to produce pixel-level embeddings in the `CLIP` feature space.
- 3D grounding: back-projects RGB-D pixels into the world frame using camera pose and depth.
- Top-down fusion: projects 3D points to a grid map and averages multi-view embeddings per grid cell.
- Landmark indexing: encodes category names with `CLIP` text encoder and computes map-cell to text similarity.
- Obstacle map generation: queries obstacle categories in open vocabulary and intersects semantic obstacle masks with geometric obstacle evidence.
- LLM planning: uses a code-writing language model to translate natural language commands into Python calls such as `move_to_object`, `move_in_between`, `move_north`, `face`, and `move_forward`.
- Navigation: passes target coordinates and obstacle maps to an off-the-shelf navigation stack.

## Main Claims

- `VLMaps` enables natural language indexing of robot maps without additional labeled data or model finetuning.
- It supports spatial goals beyond object-centric navigation, such as relative positions and "in between" goals.
- It can generate different obstacle maps for robots with different embodiments from the same map.
- It outperforms `LM-Nav`, `CoW`, and `CLIP Map` on multi-object and spatial goal navigation in the paper's benchmark.

## Strengths

- It is a foundational open-vocabulary semantic map baseline used by later work such as `CARe` and related semantic-memory navigation systems.
- It exposes a compact and inspectable map representation that can be queried with text.
- Code, project page, and Colab/demo path are available.
- Evaluation includes simulation and real robot experiments.
- Failure modes are relevant to `CAND-01`: noisy fused features, false positives, similar-object ambiguity, depth noise, odometry drift, and action noise.

## Limitations

- It assumes access to odometry or camera poses from RGB-D SLAM / visual odometry.
- It does not model object/node uncertainty explicitly.
- It does not actively choose re-observation viewpoints.
- It is sensitive to 3D reconstruction noise and odometry drift.
- It cannot resolve object ambiguity in cluttered scenes with visually similar objects.
- It does not handle dynamic objects or moving humans; the paper lists this as future work.
- Repository TODO indicates the navigation stack can fail around obstacle corners and narrow passages.

## Relevance to My Research

`VLMaps` is a direct baseline candidate for `CAND-01` Stage 1 because it provides a pre-explored open-vocabulary semantic map and ObjectNav/spatial-goal evaluation code. It supports Step 1 by providing map-cell/category similarity that can become a semantic confidence proxy. It supports Step 2-3 as a map-backed navigation baseline. It is not enough for Step 4-5 because it does not evaluate SLAM uncertainty, `ATE`, `RPE`, pose graph connectivity, or active SLAM utility.

## Follow-up Questions

- Can map-cell text similarity, multi-view feature variance, and disagreement between nearby object categories define an object/node uncertainty score?
- Can active re-observation reduce the false positives that cause wrong-goal navigation in `VLMaps`?
- Can `VLMaps` be run first on the official Matterport3D/Habitat setup, then extended with `CARe` or `DualMap`-style update logic?
- What minimum subset of `VLMaps` is needed for a first experiment: map indexing only, object-goal navigation, or spatial-goal navigation?
