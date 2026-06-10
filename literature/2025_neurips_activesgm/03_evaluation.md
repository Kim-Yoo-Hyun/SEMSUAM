# Evaluation

## Dataset / Benchmark

- Replica
- Matterport3D

## Splits

Exact scenes and episode construction need paper/code-level verification before reproduction.

## Metrics

- Map completeness
- Map accuracy
- Semantic understanding / semantic mapping quality
- Robustness indicators reported by the paper

## Baselines

- Geometry-driven active mapping.
- Prior active mapping / NBV baselines.
- Ablations without semantic uncertainty or without geometric uncertainty should be checked in the full paper.

## Main Results

The paper reports improved active mapping quality when semantic and geometric uncertainty are used together for exploration.

## Reproducibility Notes

- Public project page exists.
- H001 can use this as conceptual support for Step 4-5 without reproducing the full system immediately.
- If exact comparison is needed, Docker environment and dataset access must be separately frozen.

## Evaluation Weaknesses

- Not an ObjectNav benchmark.
- Standard mapping metrics may not show whether a wrong navigation goal was avoided.
- If localization is assumed from simulator poses, direct SLAM uncertainty claims need separate evidence.
