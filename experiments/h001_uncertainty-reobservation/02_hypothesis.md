# Hypothesis

## Status

Draft

## Hypothesis Sentence

If an agent converts pre-explored semantic map object/node uncertainty into an active SLAM/navigation utility for choosing re-observation viewpoints, then ObjectNav wrong-goal visits and wasted path decrease while map/pose consistency improves, compared with semantic-only replanning and geometry-only exploration baselines.

## Intervention

Use semantic map object/node uncertainty as the primary utility signal, then combine it with SLAM uncertainty to decide whether and where to perform active re-observation before committing to a candidate goal.

## Expected Measurable Effect

- Lower wrong-goal visit rate
- Lower wasted path / extra path length
- Equal or improved `Success Rate`
- `SPL` should not drop beyond an accepted threshold from re-observation cost
- Lower map error or improved semantic accuracy
- Equal or improved ATE/RPE or pose graph connectivity when SLAM-side measurement is available

## Evaluation Target

- Step 1-3 first probe: Habitat ObjectNav subset or one-scene replay with precomputed semantic map candidates
- Step 4-5 extension: replay or simulator with SLAM uncertainty proxy, map error, semantic accuracy, ATE/RPE, pose graph connectivity

## Why This Is Semantic Mapping

The intervention changes how object/node uncertainty from a pre-explored semantic map is used before committing to a goal candidate. H001 must measure both task behavior and semantic map quality.

## Why This Is Active Robotics

The agent does not only re-rank map candidates. It spends robot motion budget to gather additional evidence from a selected re-observation viewpoint, and the final version also accounts for SLAM uncertainty in that mobility decision.

## First Falsification Path

The first probe weakens H001 if high semantic uncertainty does not correlate with wrong-goal visits, or if converting semantic uncertainty into re-observation utility reduces wrong-goal visits but causes enough extra travel cost to reduce `SPL` below the no-reobservation baseline. The Step 4-5 extension weakens H001 if adding SLAM uncertainty does not improve map/pose consistency over semantic-only re-observation.

## User Decision Needed

- First probe environment: Habitat ObjectNav or Replica / ScanNet replay.
- Baseline priority: `CARe` reproduction first or simplified no-reobservation baseline first.
- SLAM-side measurement priority: ATE/RPE first or pose graph connectivity proxy first.
