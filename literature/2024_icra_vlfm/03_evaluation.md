# Evaluation

## Dataset / Benchmark

- Habitat ObjectNav with HM3D and MP3D-style simulator environments.
- Real-world robot demonstrations are reported as supporting evidence.

## Splits

Paper-specific simulation splits should be checked before reproduction. H001 should use its own frozen split discipline and treat exact `VLFM` reproduction as optional unless it becomes a main baseline.

## Metrics

- `Success Rate`
- `SPL`
- Exploration/navigation efficiency metrics reported by the paper

## Baselines

- Prior zero-shot semantic navigation methods.
- Modular map-based baselines and learned ObjectNav baselines.

## Main Results

The paper reports strong zero-shot ObjectNav performance from combining vision-language frontier maps with object detection.

## Reproducibility Notes

- Public code is available.
- H001 should prefer a controlled `VLFM`-style semantic frontier baseline if exact environment alignment is expensive.
- Docker-based reproduction is required for any paper-facing comparison.

## Evaluation Weaknesses

- Wrong-goal visit and wasted path are not first-class metrics.
- Detector confidence and goal-validity uncertainty are not separated enough for H001's current bottleneck.
- Standard ObjectNav `SR` / `SPL` can hide whether the agent visited plausible but wrong candidates.
