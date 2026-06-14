# experiments

## Role

`experiments/`는 active hypothesis workspace, experiment workflow, ablation/analysis 기록을 둔다.

## Active Workspaces

- `h001_uncertainty-reobservation/`: semantic uncertainty를 active SLAM/navigation utility로 검증하는 현재 H001 workspace
- `CAND-01.md`: candidate-level summary
- `hypotheses.md`: hypothesis registry

## Rules

- 세부 실험 기록은 가장 가까운 workspace README, numbered document, 또는 runtime workflow에 둔다.
- 핵심 실행 code는 `src/`, 실행 wrapper는 `scripts/`, manifest/config는 `configs/`를 source-of-truth로 둔다.
- generated artifact는 `local_dataset/runs`에 두고 Git에는 올리지 않는다.
