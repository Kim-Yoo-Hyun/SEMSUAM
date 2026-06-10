# Insights

## Facts

- This is a 2025 arXiv / ECMR paper with open-source code.
- It targets uncertainty-informed active perception for open-vocabulary Object Goal Navigation.

## Paper Claims

- Uncertainty-informed active perception improves open-vocabulary ObjectNav behavior.

## Inferences

- This paper narrows H001's novelty space.
- H001 should not be framed as "we use uncertainty for active perception" because that is already directly claimed here.
- H001 can remain distinct if it focuses on failure taxonomy, candidate validity arbitration, semantic-SLAM utility, and task/map metric coupling.

## Connection to Field Trends

- Direct but non-top-tier support for semantic uncertainty as ObjectNav utility.
- Reinforces that H001 should use `RandomReobserve`, `FrontierReobserve`, and uncertainty-only baselines.

## Possible Contribution Angles

- Treat this method as a close baseline if implementation is feasible.
- Add wrong-goal visit and wasted path as primary metrics.
- Extend uncertainty beyond detector/semantic confidence into map/pose consistency and post-observation state updates.

## What Would Change This Assessment

- If the method already has robust wrong-goal and map/pose evaluation, H001 should shift toward SLAM-side contribution.
- If it is not reproducible or lacks failure taxonomy, H001 can differentiate through harness and reviewer-defense design.
