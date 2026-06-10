# Evaluation

## Dataset / Benchmark

- Open-vocabulary ObjectNav / Object Goal Navigation simulation.
- Exact dataset split requires full paper/code verification.

## Splits

Not yet verified.

## Metrics

- ObjectNav success metrics such as `Success Rate` and `SPL`.
- Uncertainty / active perception effects as reported by the paper.

## Baselines

- Open-vocabulary ObjectNav baselines.
- Non-uncertainty active perception / exploration baselines.

## Main Results

The paper reports gains from uncertainty-informed active perception in open-vocabulary ObjectNav.

## Reproducibility Notes

- Public code exists.
- Should be inspected as a potential direct baseline or ablation before H001 paper claims are finalized.
- If used for paper comparison, Dockerize separately from H001 Habitat runtime.

## Evaluation Weaknesses

- Need to verify whether false-positive goal commitment is measured directly.
- Need to verify whether semantic uncertainty is calibrated or only heuristic.
- Need to verify whether SLAM/map-pose uncertainty is part of the method.
