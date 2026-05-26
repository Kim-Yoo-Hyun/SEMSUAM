# Research3

이 저장소는 석사 연구를 진행하고 최종 논문으로 발전시키기 위한 작업 공간이다.

## Start Here

처음 들어오면 아래 순서로 읽는다.

1. [AGENTS.md](AGENTS.md): 연구 운영 규칙과 에이전트 작업 규칙
2. [TODO.md](TODO.md): 현재 작업 상태, 다음 행동, 완료 이력
3. [docs/index.md](docs/index.md): 문헌 조사, hypothesis, workflow 문서로 이동하는 index
4. [docs/reproducibility.md](docs/reproducibility.md): 데이터, checkpoint, Docker, 재현 명령, artifact/evaluation 요약

## Active Direction

현재 primary direction은 `CAND-01 / H001`이다.

중심 주장은 다음과 같다.

> semantic uncertainty가 active SLAM/navigation utility로 작동해서 ObjectNav 같은 navigation task에서 wrong-goal visit과 wasted path를 줄이고, 확장 단계에서는 map/pose consistency까지 개선할 수 있는지 검증한다.

## Current Status

### 사실

- Date checked: 2026-05-26
- Current gate: diagnose `rival_identity_generalization_v1` unsafe `toilet` commits before any rule revision.
- `h001_dense_conflict_v1` manifest and recall gate are implemented and Docker-verified.
- Host NVIDIA runtime was recovered on 2026-05-23.
- `spatial_nms_p95_k100_d10` and revised `spatial_nms_p90_k200_d5` dense re-export artifacts both failed the final recall gate with primary rows with correct candidate `3/6`; detector/association validation remains blocked for those re-export substrates.
- The existing selected substrate `v3_fresh_spatial_p97_k20` passed the final primary recall gate with `6/6` rows and recall@20 `1.0`.
- Dense conflict detector/association validation was materialized from the existing `v3_fresh` second-stage evidence at `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1`; primary gate passed with detector box `1.0`, SAM2 mask `1.0`, candidate association `0.8`, commit/success/wrong/no-valid `5/5/0/0`, and `uses_gt_for_action false`.
- Secondary-stress held-out `sofa` validation also passed at `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1`; recall rows with correct `2/2`, detector box/SAM2/candidate association `1.0/1.0/1.0`, commit/success/wrong/no-valid `2/2/0/0`, and `uses_gt_for_action false`.
- Broader split design output `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json` selects `scene_disjoint_first_eval_style` as the next paper-facing path.
- Frozen `dense_conflict_generalization_v1` manifest is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_generalization_v1.json`: `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`, and `uses_gt_for_action false`.
- Generalization recall gate passed at `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1`: rows with correct `20/20`, recall@20 `1.0`, recall@5 `0.85`.
- Generalization detector substrate passed at `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1`: detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`, associated rows `7/20`, and `uses_gt_for_action false`.
- Terminal evidence extraction passed GT separation at `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1`: action evidence rows `20`, evaluation label rows `55`, associated/unassociated rows `7/13`, forbidden action key count `0`, and `uses_gt_for_action false`.
- Terminal arbitration v0 is unsafe. `proposed_conservative_v0` commits `7/20` with `3` success and `4` wrong-goal commits.
- `strict_depth_consistency_v1` guard design was Docker-verified at `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1`: commit/success/wrong `3/3/0` on the same diagnostic split, associated commit rate `3/7`, and `uses_gt_for_action false`. This is a fixed-rule validation candidate, not a paper claim.
- Fixed-rule terminal validation was Docker-verified at `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1`: action evidence forbidden key count `0`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`, and `uses_gt_for_action false`. It remains same-split validation, so independent validation is still required before a paper-facing utility claim.
- Independent terminal validation contract is frozen at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_dense_conflict_terminal_independent_v1.json`: primary `v3_fresh_validation_v1` source has `6/6` associated rows across `3` scenes and `2` queries; secondary `sofa` stress source has `2/2` associated rows.
- Independent validation rejects `strict_depth_consistency_v1`: primary output `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1` has commit/success/wrong `6/2/4`; secondary stress output `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1` has `2/0/2`. Both have forbidden action key count `0` and `uses_gt_for_action false`.
- Failure diagnosis output `local_dataset/runs/h001_dense_conflict_terminal_failure_diagnostic_v1` shows wrong rows `6`, with `repeated_wrong_instance_selected_by_saturated_support 5` and `guard_cannot_arbitrate_between_eligible_correct_and_wrong 1`. The next design contract is `rival_identity_confirmation_v1`.
- `rival_identity_confirmation_v1` diagnostic output `local_dataset/runs/h001_dense_conflict_rival_identity_policy_v1` passes the local diagnostic gate: commit/success/wrong `2/2/0`, request identity rows `6`, forbidden action keys `0`, and `uses_gt_for_action false`. This is not yet a paper-facing utility proof.
- Active observation/evaluation contract is frozen at `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_observation_v1.json`: request rows `6`, planner `rival_identity_pair_probe_v1`, and post-observation gate requires zero wrong-goal commits plus at least one newly resolved primary request.
- `rival_identity_pair_probe_v1` observation planner is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/plan_rival_identity_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_plan_v1` passes the plan smoke gate: request rows `6`, planned request rows `6`, plan rows `19`, skipped rows `0`, forbidden action keys `0`, and `uses_gt_for_action false`.
- `rival_identity_pair_probe_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_pair_probe_frames_v1`: rows requested/exported `19/19`, rendered headings `142`, RGB/depth files `142/142`, unique scenes `3`, nonblank RGB sanity pass, and `uses_gt_for_action false`.
- `rival_identity_pair_probe_v1` detector substrate job completed at `local_dataset/runs/h001_rival_identity_pair_probe_detector_substrate_v1`: detector rows `19`, detector box rate `0.8421`, SAM2 mask rate `0.8421`, candidate association rate `0.6316`, rows with candidate association `12/19`, associated candidate heading count `57`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Post-observation evidence/validation contract is frozen in `hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md`: action-time evidence and evaluation labels are separated, label join key is `(episode_key, candidate_id)`, and the fixed rule commits only when exactly one candidate has strong own-view identity evidence.
- `rival_identity_pair_probe_v1` post-observation analyzer is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/analyze_rival_identity_post_observation.py`. Docker output `local_dataset/runs/h001_rival_identity_pair_probe_post_observation_v1` passes the diagnostic gate: request rows `6`, evidence rows `19`, commit/success/wrong/no-label `1/1/0/0`, new primary success `1`, secondary stress wrong-goal `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`.
- Fresh/predeclared validation source design selects `rival_identity_generalization_v1` from the frozen `dense_conflict_generalization_v1` primary action evidence. A design probe at `local_dataset/runs/h001_rival_identity_generalization_policy_design_probe_v1` finds `6` request rows across `3` scenes and `2` queries, excluding the prior diagnostic scenes `DYehNKdT76V`, `7MXmsvcQjpJ`, and `y9hTuugGdiq`.
- `rival_identity_generalization_v1` source miner is implemented at `hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/h001_runtime/build_rival_identity_generalization_manifest.py`. Docker output `local_dataset/runs/h001_rival_identity_generalization_source_v1` freezes `hypothesis/CAND-01/H001_uncertainty-reobservation/manifests/h001_rival_identity_generalization_v1.json` with request rows `6`, scenes `3`, queries `2`, excluded-scene overlap `0`, action evidence forbidden key count `0`, and `uses_gt_for_action false`; verify file reports `ok true`.
- `rival_identity_generalization_v1` observation planner smoke passed at `local_dataset/runs/h001_rival_identity_generalization_plan_v1`: request rows `6`, planned request rows `6`, plan rows `12`, skipped rows `0`, candidate artifact rows/candidates `4/7`, plan gate `true`, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` frame export smoke passed at `local_dataset/runs/h001_rival_identity_generalization_frames_v1`: rows requested/exported `12/12`, rendered headings `72`, RGB/depth files `72/72`, unique scenes `3`, candidate point field `grounded_position`, nonblank RGB sanity passed, and `uses_gt_for_action false`.
- `rival_identity_generalization_v1` detector/SAM2 substrate job completed at `local_dataset/runs/h001_rival_identity_generalization_detector_substrate_v1`: detector rows `12`, detector box rate `1.0`, SAM2 mask rate `1.0`, candidate association rate `1.0`, associated candidate heading count `84`, `uses_gt_for_action false`, and detector substrate gate `true`.
- Frozen post-observation analyzer on `rival_identity_generalization_v1` completed at `local_dataset/runs/h001_rival_identity_generalization_post_observation_v1`: request/evidence/decision rows `6/12/6`, commit/success/wrong/no-label `4/2/2/0`, new primary success `2`, resolved rows `4`, and `uses_gt_for_action false`. The gate failed because two single-candidate `toilet` requests committed wrong goals.
- Cross-machine recovery and Drive backup paths are documented in [docs/reproducibility.md](docs/reproducibility.md).

### 에이전트 추론

The detector/association blocker is lifted for the selected primary and secondary diagnostic substrates, and the broader frozen split now passes candidate recall plus detector substrate. The independent result is a useful negative result: strict depth-consistent support is not sufficient because wrong instances can also be detector-associated and depth-consistent. `rival_identity_confirmation_v1` remains useful as a mechanism-level direction, but fresh-source validation shows that the current post-observation commit rule is unsafe for single false-positive object candidates. The next step is failure diagnosis, not threshold tuning or policy-scale evaluation.

## Key Documents

- Literature overview: [literature/README.md](literature/README.md)
- Paper registry: [literature/PAPER.md](literature/PAPER.md)
- Primary candidate: [literature/CAND-01.md](literature/CAND-01.md)
- Hypothesis index: [hypothesis/README.md](hypothesis/README.md)
- Active hypothesis: [hypothesis/CAND-01/H001_uncertainty-reobservation/README.md](hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)
- Evaluation contract: [07_evaluation_contract.md](hypothesis/CAND-01/H001_uncertainty-reobservation/07_evaluation_contract.md)
- Reproducibility: [docs/reproducibility.md](docs/reproducibility.md)
- Research report summary: [summary.md](summary.md)

## Current Dataset Gates

The current Docker-based dataset gates are open for:

- HM3D v0.2 scene assets
- HM3D semantic annotations
- ObjectNav HM3D v2 episodes
- HM3D-OVON episodes

Runtime scripts, Dockerfiles, and smoke workflow notes live under:

```text
hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/
```

Current data paths, checkpoint paths, Docker images, and reproduction commands are summarized in [docs/reproducibility.md](docs/reproducibility.md).

## Local Assets

Canonical local paths:

```text
local_dataset/data
local_dataset/models
local_dataset/runs
```

Compatibility paths:

```text
/tmp/research3-data
/tmp/research3-models
/tmp/research3-runs
```

Large datasets, model checkpoints, run artifacts, Docker image archives, paper PDFs, and credentials are intentionally not GitHub source-of-truth.

2026-05-23 note: `/tmp/research3-data` was observed as a stale empty directory after reboot, so active jobs should use canonical `local_dataset/` paths until `/tmp` compatibility paths are normalized.

## Repository Rule

The repository root is kept as an entrypoint only.

Root files should stay limited to:

- `AGENTS.md`
- `.gitignore`
- `README.md`
- `summary.md`
- `TODO.md`

Research details, workflow notes, runtime scripts, Dockerfiles, and experiment design documents should live under the relevant workflow or hypothesis folder.

## What Not To Do

- Do not create empty `experiments/`, `paper/`, `results/`, or `decisions/` folders in advance.
- Do not use host Python for smoke tests or implementation experiments.
- Do not treat GT oracle policies as deployable baselines.
- Do not mix facts, paper claims, agent inference, and user decisions in the same section.
