# Paper Card

## Problem

Active mapping should build not only geometry but also semantic structure while exploring. Standard exploration often treats semantic understanding as a downstream output instead of a driver of viewpoint selection.

## Core Idea

Use semantic and geometric uncertainty from a scene graph map to select next-best-views that improve both map completeness and semantic understanding.

## Input / Output

- Input: RGB-D observations, pose trajectory, partial map / scene graph state.
- Output: next-best-view decisions and an incrementally improved semantic scene graph / map.

## Method

The method builds an active scene graph mapping framework. It reasons over map uncertainty and semantic uncertainty to guide exploration and update object-level semantic structure.

## Main Claims

- Semantics-driven active mapping improves map completeness, accuracy, and robustness over active mapping baselines.
- Combining semantic and geometric uncertainty gives a better exploration signal than geometry alone.

## Strengths

- Direct top-tier evidence for semantic uncertainty as active mapping utility.
- Uses scene-graph-like structure, which is compatible with H001's object/node uncertainty framing.
- Evaluates on Replica and Matterport3D, which are relevant embodied indoor datasets.

## Limitations

- The target task is active mapping, not ObjectNav wrong-goal arbitration.
- It does not directly evaluate wrong-goal visit, wasted path, or ObjectNav terminal commitment.
- It may not include full SLAM drift / pose graph metrics such as `ATE/RPE`.

## Relevance to My Research

`ActiveSGM` supports H001 Step 4-5: semantic uncertainty can be turned into an active mapping utility. H001's contribution gap is to show whether the same principle helps navigation behavior and map/pose consistency in ObjectNav-like failures.

## Follow-up Questions

- Which uncertainty terms are semantic, geometric, or graph-structural?
- Can an object/node uncertainty term from H001 be mapped onto a scene graph uncertainty term?
- What baseline most fairly separates semantic utility from geometry-only NBV?
