# Evaluation

## Dataset / Benchmark

- CoIN benchmark for instance-aware ObjectNav.
- Habitat-Matterport 3D scenes are used by the benchmark.

## Splits

CoIN split details need full benchmark/PDF verification before reproduction.

## Metrics

- Instance-aware navigation success metrics.
- Standard navigation metrics such as `Success Rate` and `SPL` are likely relevant.
- H001 should still add wrong-goal visit and wasted path if not native to the benchmark.

## Baselines

- Instance-aware and object-goal navigation baselines.
- VLM/VLN or zero-shot ObjectNav methods that do not use the same context-driven 3D reasoning.

## Main Results

The paper reports improved instance-aware ObjectNav under contextual and viewpoint-aware reasoning.

## Reproducibility Notes

- CVPR openaccess source is available.
- H001 should inspect whether CoIN can be used after the HM3D ObjectNav path is stable.
- Exact reproduction is not required before using the paper to motivate goal-validity arbitration.

## Evaluation Weaknesses

- It may not separate map uncertainty, semantic uncertainty, and SLAM uncertainty.
- It may evaluate instance goal success without a separate wasted-path decomposition.
- Real-time active re-observation cost should be checked if used as a baseline.
