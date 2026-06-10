# Paper Card

## Problem

Zero-shot semantic navigation needs an agent to find unseen object categories without task-specific training, while still choosing useful frontiers in a partially observed environment.

## Core Idea

Build a frontier map whose frontier scores are guided by pretrained vision-language models and open-vocabulary object detection.

## Input / Output

- Input: RGB-D observations, robot pose, language goal.
- Output: navigation actions toward frontiers or detected goal regions.

## Method

The method maintains goal-oriented value maps for navigation and uses a VLM/VLM-derived signal to score unexplored frontiers. A detector can trigger goal approach when the target object is observed.

## Main Claims

- `VLFM` improves zero-shot ObjectNav over prior modular and learning-based baselines.
- Vision-language frontier scoring is useful when the target has not yet been directly detected.

## Strengths

- Strong practical baseline for zero-shot ObjectNav.
- Clear decomposition between exploration frontier scoring and detected-goal approach.
- Includes both simulation and real-world style evaluation.

## Limitations

- Detector evidence can still produce false positives or ambiguous repeated-object candidates.
- Frontier scores are not a complete goal-validity arbitration mechanism.
- It does not explicitly evaluate wrong-goal visit or wasted path as separate failure metrics.

## Relevance to My Research

`VLFM` is a required baseline family for H001 because it turns semantic evidence into exploration/navigation action. H001 should not claim novelty as "use VLM maps for ObjectNav"; the stronger gap is whether semantic uncertainty and map/pose uncertainty can decide when to re-observe rather than directly commit to a detected candidate.

## Follow-up Questions

- Can `VLFM`-style frontier value be adapted into `RandomReobserve` and `FrontierReobserve` baselines?
- Which failures are detector false positives, repeated-instance ambiguity, or insufficient viewpoint evidence?
- Does frontier utility reduce wrong-goal visit, or only improve standard `SR` / `SPL`?
