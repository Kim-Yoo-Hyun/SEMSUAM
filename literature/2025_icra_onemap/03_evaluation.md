# Evaluation

## Dataset / Benchmark

- Habitat-based zero-shot multi-object navigation.
- HM3D and MP3D are relevant environment sources.

## Splits

Exact scene split and query protocol need PDF/code-level confirmation before reproduction.

## Metrics

- Navigation success metrics such as `Success Rate` and `SPL`.
- Multi-object search efficiency / path efficiency.
- Semantic map/query quality as used by the paper.

## Baselines

- Zero-shot ObjectNav / multi-object navigation baselines.
- Semantic map reuse baselines.
- Frontier or exploration baselines.

## Main Results

The paper reports that a reusable open-vocabulary map improves multi-object navigation efficiency and supports unseen object queries.

## Reproducibility Notes

- Public code exists.
- H001 should reuse it conceptually first, then decide whether exact reproduction is needed.
- If used in paper experiments, run under Docker and freeze query sequence, map cache, and metrics.

## Evaluation Weaknesses

- It is not designed around H001's wrong-goal visit metric.
- It may not isolate SLAM uncertainty from semantic uncertainty.
- Multi-object navigation can conflate map reuse gains with uncertainty-driven active perception gains.
