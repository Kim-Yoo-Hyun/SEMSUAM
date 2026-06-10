# Paper Card

## Problem

Instance-aware ObjectNav requires navigating to a specific object instance, not just any object of a category. Category-level detection can lead to plausible but wrong goals when repeated objects exist.

## Core Idea

Use context-driven exploration and viewpoint-aware 3D spatial reasoning to infer which candidate object instance matches the instruction and its surrounding context.

## Input / Output

- Input: egocentric observations, target instruction / instance-aware goal, candidate objects and contextual scene evidence.
- Output: navigation decisions and candidate validation under instance ambiguity.

## Method

The method combines exploration driven by contextual cues with 3D spatial reasoning over candidate objects and viewpoints. It is designed to handle instance-level ambiguity rather than only category-level detection.

## Main Claims

- Context and viewpoint-aware 3D spatial reasoning improve instance-aware ObjectNav.
- Repeated-object ambiguity needs more than direct object detection.

## Strengths

- Direct top-tier evidence that ObjectNav goal ambiguity is an active current problem.
- Strongly aligned with H001's wrong-goal and goal-validity arbitration bottleneck.
- Uses a benchmark focused on instance-aware goal ambiguity.

## Limitations

- It is not primarily a semantic-SLAM uncertainty paper.
- Need full check for whether it exposes reusable semantic map uncertainty or SLAM/map-pose metrics.
- It may solve instance disambiguation through context reasoning rather than active SLAM utility.

## Relevance to My Research

`Context-Nav` supports the need to narrow H001 toward candidate validity and wrong-goal arbitration. It also warns that H001 must define what is different from context-based verification: H001 should emphasize uncertainty-to-reobservation utility and map/pose consistency, not only contextual object reasoning.

## Follow-up Questions

- Can `Context-Nav` be a conceptual or empirical baseline for goal-validity arbitration?
- Does `CoIN` expose metrics that map to wrong-goal visit and wasted path?
- Which part of H001 remains novel after context-driven instance disambiguation?
