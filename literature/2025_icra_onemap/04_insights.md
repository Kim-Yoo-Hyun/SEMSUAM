# Insights

## Facts

- `OneMap` is an ICRA 2025 paper on real-time open-vocabulary mapping for zero-shot multi-object navigation.
- It explicitly uses semantic uncertainty in a navigation/exploration setting.

## Paper Claims

- Reusable open-vocabulary maps can improve multi-object navigation.
- Semantic uncertainty can guide exploration in the map.

## Inferences

- This paper confirms that "semantic uncertainty as navigation utility" is not empty novelty by itself.
- H001 needs a more specific gap: uncertainty should trigger active re-observation that reduces wrong-goal commitment and, later, SLAM/map-pose inconsistency.
- The claim should be narrowed away from "semantic uncertainty improves ObjectNav" toward "semantic uncertainty is useful when converted into risk-aware evidence acquisition instead of direct goal commitment."

## Connection to Field Trends

- Strong evidence for pre-explored semantic maps becoming actionable.
- Strong evidence for semantic uncertainty as utility.

## Possible Contribution Angles

- Compare single-map reuse / semantic uncertainty exploration with H001's candidate-specific re-observation utility.
- Add wrong-goal visit and wasted path metrics that standard multi-object efficiency metrics may not expose.
- Extend from semantic utility to semantic-SLAM utility by including map/pose consistency.

## What Would Change This Assessment

- If `OneMap` already evaluates wrong-goal / false-positive object visits and solves them, H001 should move further toward SLAM uncertainty and post-observation arbitration.
- If its uncertainty is only a heuristic score without calibrated failure analysis, H001 can still own the failure-taxonomy and metric side.
