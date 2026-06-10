# Insights

## Facts

- `ActiveSGM` is a NeurIPS 2025 active semantic mapping paper.
- It evaluates on Replica and Matterport3D.
- It links semantic and geometric uncertainty to active exploration.

## Paper Claims

- Semantic and geometric uncertainty improve active mapping decisions.
- A scene graph map is useful while the agent is still exploring, not only after exploration is done.

## Inferences

- H001's Step 4-5 should be framed as an ObjectNav-oriented extension of this active semantic mapping pattern, not as a first demonstration that semantic uncertainty can guide exploration.
- The novel part must be the coupling with wrong-goal/wasted-path behavior and SLAM/map-pose consistency.

## Connection to Field Trends

- Strong evidence for active semantic mapping.
- Strong evidence that semantic uncertainty can be a motion utility.

## Possible Contribution Angles

- Convert object/node uncertainty into active re-observation utility under ObjectNav ambiguity.
- Add task-side failure metrics to active semantic mapping evidence.
- Add SLAM/map-pose proxy metrics to distinguish semantic-only from semantic-SLAM utility.

## What Would Change This Assessment

- If `ActiveSGM` already couples uncertainty to ObjectNav-like goal validation, H001 must narrow further.
- If its semantic uncertainty is not calibrated or action-time separable, H001 can emphasize harness and failure taxonomy.
