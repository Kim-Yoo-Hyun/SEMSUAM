# Insights

## Facts

- `VLFM` is an ICRA 2024 zero-shot semantic navigation method.
- It uses vision-language frontier maps and open-vocabulary object evidence.
- It evaluates ObjectNav-style navigation performance.

## Paper Claims

- Vision-language frontier scoring improves zero-shot semantic navigation.
- Open-vocabulary detection can support goal-directed approach without category-specific training.

## Inferences

- `VLFM` supports H001's baseline side, not the full contribution.
- Its likely weak point for H001 is that object detection and frontier value do not decide whether a candidate is the correct goal instance under repeated-object ambiguity.
- H001 should compare against a `VLFM`-style semantic frontier or direct semantic memory baseline, but the paper claim should target uncertainty-to-reobservation utility.

## Connection to Field Trends

- Supports the trend that open-vocabulary semantic evidence is becoming a navigation utility.
- Supports the trend that standard ObjectNav metrics need additional failure metrics when goal ambiguity is central.

## Possible Contribution Angles

- Add wrong-goal / wasted-path evaluation on top of `VLFM`-style baselines.
- Test whether uncertainty-driven re-observation improves over semantic frontier scoring and detector-triggered approach.
- Separate "object visible" from "ObjectNav goal valid" using post-observation evidence states.

## What Would Change This Assessment

- If exact `VLFM` reproduction already exposes and solves repeated-instance wrong-goal failures, H001 should narrow further toward SLAM/map-pose uncertainty.
- If `VLFM` fails mainly due to detector substrate rather than utility design, H001 should avoid over-claiming semantic uncertainty.
