# Paper Card

## Problem

Open-vocabulary Object Goal Navigation suffers from uncertainty in object detections and semantic map evidence. Agents need to decide when to keep exploring or actively observe before committing.

## Core Idea

Use uncertainty-informed active perception to guide open-vocabulary ObjectNav decisions.

## Input / Output

- Input: RGB-D observations, open-vocabulary object evidence, robot pose / map state.
- Output: navigation or active perception decisions for object-goal search.

## Method

The method uses uncertainty signals from perception/navigation evidence to shape active perception in an open-vocabulary ObjectNav pipeline.

## Main Claims

- Uncertainty-aware active perception improves open-vocabulary ObjectNav compared with baselines that do not use uncertainty in the same way.
- Re-observation/exploration decisions can be made more robust when perception uncertainty is explicit.

## Strengths

- Very direct semantic uncertainty as utility source.
- Open-source code is available.
- Strong conceptual overlap with H001's current active re-observation direction.

## Limitations

- Venue is not in the user's primary top-tier list, so it is supporting evidence rather than anchor novelty evidence.
- Need full paper check to determine whether it evaluates wrong-goal visit and wasted path separately.
- It may focus on perception uncertainty without adding SLAM/map-pose consistency.

## Relevance to My Research

This paper is a direct "already close" warning. H001 must avoid claiming novelty as uncertainty-aware active perception alone. The remaining gap should be semantic-SLAM uncertainty decomposition, post-observation goal-validity arbitration, and wrong-goal/wasted-path evaluation.

## Follow-up Questions

- Does the code expose uncertainty terms that can become a baseline?
- Does it include explicit wrong-goal/false-positive object visit metrics?
- Does it use active re-observation as a terminal risk reducer or only as exploration guidance?
