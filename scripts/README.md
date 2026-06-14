# scripts

## Role

`scripts/`는 Docker 실행 wrapper와 lightweight helper script를 둔다.

## Key Commands

- `run_fully_covered_contrast.sh`: 현재 H001 gate인 `fully_covered_candidate_conditioned_contrast_v1` materializer 실행 wrapper
- `h001_jobs/`: long-running Docker job wrappers
- `h001_tools/`: dataset check, smoke, export 같은 helper scripts

## Rules

- 논문 본문용 experiment와 smoke test는 Docker 기반으로 실행한다.
- long-running job은 `AGENTS.md`의 background-task rule을 따른다.
- 실행 command, output path, verification command는 `docs/reproducibility.md` 또는 가까운 experiment workflow에 기록한다.
