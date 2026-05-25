# Research Docs

이 문서는 연구 문서의 첫 진입점이다. `docs/` 안의 workflow 문서와 주요 연구 산출물을 빠르게 찾기 위해 사용한다.

## How to Use

1. 현재 작업 상태는 먼저 [TODO.md](../TODO.md)에서 확인한다.
2. 연구 운영 규칙은 [AGENTS.md](../AGENTS.md)를 따른다.
3. 문헌 조사 작업은 [literature.md](literature.md)를 읽고 [literature/README.md](../literature/README.md)와 [literature/PAPER.md](../literature/PAPER.md)로 이동한다.
4. contribution candidate 검토는 [Contribution Candidates.md](../literature/Contribution%20Candidates.md)와 [CAND-01.md](../literature/CAND-01.md)를 본다.
5. hypothesis 작업은 [hypothesis.md](hypothesis.md)를 읽고 [hypothesis/README.md](../hypothesis/README.md)로 이동한다.
6. paper novelty와 top-tier framing은 [paper.md](paper.md)를 따른다.
7. 재현을 위한 데이터, checkpoint, Docker, artifact 위치는 [reproducibility.md](reproducibility.md)에서 확인한다.
8. 현재 연구 보고서 형태의 요약은 [summary.md](../summary.md)에서 확인한다.

## Workflow Docs

| Workflow | Rule Document | Output Location | Role |
| --- | --- | --- | --- |
| Literature | [literature.md](literature.md) | [literature/](../literature/README.md) | field map, paper registry, contribution candidate 관리 |
| Hypothesis | [hypothesis.md](hypothesis.md) | [hypothesis/](../hypothesis/README.md) | candidate를 검증 가능한 hypothesis와 first probe로 압축 |
| Paper | [paper.md](paper.md) | `summary.md`, H001 documents | novelty gate, top-tier framing, paper-ready claim 판단 |
| Reproducibility | [reproducibility.md](reproducibility.md) | `local_dataset/{data,models,runs}` with `/tmp/research3-*` compatibility symlinks | 데이터, checkpoint, Docker, Drive 백업 경로, 재현 명령, artifact/evaluation 요약 |
| Dense Conflict Validation | [workflow-20260521-dense-conflict.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260521-dense-conflict.md) | H001 runtime workflow | wrong/ambiguous positive-support dense validation 설계 |
| Stage 1 Smoke Test | [workflow-20260507-smoke.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-smoke.md) | H001 runtime workflow | `VLMaps` / Habitat smoke test |
| HM3D-OVON | [workflow-20260507-ovon.md](../hypothesis/CAND-01/H001_uncertainty-reobservation/runtime/workflow-20260507-ovon.md) | H001 runtime workflow | HM3D-OVON episode 확보와 mount smoke test |

## Active Research Direction

### 사실

- 현재 primary candidate는 [CAND-01.md](../literature/CAND-01.md)의 `Semantic Uncertainty as Active SLAM/Navigation Utility for Adaptive ObjectNav`이다.
- 현재 active hypothesis는 [H001_uncertainty-reobservation](../hypothesis/CAND-01/H001_uncertainty-reobservation/README.md)에 있다.
- 최종 연구 방향은 Step 5까지 포함한다.
- 현재 implementation gate는 independent dense conflict validation이다. `spatial_nms_p95_k100_d10`과 `spatial_nms_p90_k200_d5` dense re-export recall gate는 모두 primary `3/6`으로 실패했다.
- 기존 selected substrate인 `v3_fresh_spatial_p97_k20`은 final primary recall gate `6/6`, recall@20 `1.0`으로 통과했고, detector/association validation도 `local_dataset/runs/h001_dense_conflict_validation_v3_fresh_spatial_p97_k20_primary_v1`에서 통과했다.
- Secondary-stress held-out `sofa` validation도 `local_dataset/runs/h001_dense_conflict_validation_first_eval_replacement_spatial_p97_k20_secondary_v1`에서 통과했다.
- Broader split design은 `local_dataset/runs/h001_dense_conflict_generalization_design_v1/dense_conflict_generalization_design_summary.json`에 기록됐고, `scene_disjoint_first_eval_style`로 `manifests/h001_dense_conflict_generalization_v1.json`을 freeze했다.
- Frozen `dense_conflict_generalization_v1`은 `20` rows, `9` scenes, `6` queries, correct+wrong candidate rows `20/20`, source-selected-wrong rows `16`, NoReobserve wrong-goal rows `16`이며, recall gate `local_dataset/runs/h001_dense_conflict_recall_gate_generalization_v1`에서 rows with correct `20/20`, recall@20 `1.0`으로 통과했다.
- Generalization detector substrate job은 `local_dataset/runs/h001_dense_conflict_generalization_detector_substrate_v1`에서 완료됐고 detector box rate `0.85`, SAM2 mask rate `0.85`, candidate association rate `0.35`로 substrate gate를 통과했다.
- Terminal evidence extraction output `local_dataset/runs/h001_dense_conflict_generalization_terminal_evidence_v1`은 action evidence와 evaluation labels를 분리했고 forbidden action key count `0`으로 통과했다. 다만 `proposed_conservative_v0`는 `7/20` commit 중 `4` wrong-goal commit을 만들어 reject 상태다.
- Terminal guard design output `local_dataset/runs/h001_dense_conflict_generalization_terminal_guard_design_v1`은 `strict_depth_consistency_v1`을 다음 fixed-rule 후보로 제안한다. 같은 diagnostic split 기준 commit/success/wrong은 `3/3/0`, associated commit rate는 `3/7`, `uses_gt_for_action false`다.
- Fixed-rule terminal validation output `local_dataset/runs/h001_dense_conflict_generalization_terminal_validation_v1`은 action/evaluation 분리 흐름을 재검증했고, forbidden action key count `0`, commit/success/wrong `3/3/0`, associated commit/success/wrong `3/3/0`을 기록했다. Paper claim status는 `same_split_fixed_rule_validation_not_method_claim`이다.
- Independent terminal validation contract `manifests/h001_dense_conflict_terminal_independent_v1.json`은 primary `v3_fresh_validation_v1` source를 선택한다. Primary profile은 `6/6` associated rows, `3` scenes, `2` queries이고, secondary repeated-object stress profile은 `2/2` associated rows다.
- Independent validation은 `strict_depth_consistency_v1`을 reject했다. Primary output `local_dataset/runs/h001_dense_conflict_independent_terminal_validation_v1`은 commit/success/wrong `6/2/4`, secondary stress output `local_dataset/runs/h001_dense_conflict_secondary_terminal_validation_v1`은 `2/0/2`다. 두 결과 모두 forbidden action key count `0`이고 `uses_gt_for_action false`다.
- Google Drive 백업 후보와 Drive 없이 재생성하는 절차는 [reproducibility.md](reproducibility.md)의 `Google Drive Backup Manifest`, `Restore from Drive`, `Rebuild Without Drive`를 따른다.

### 에이전트 추론

Step 1-3은 ObjectNav first probe이고, Step 4-5는 같은 H001 안에서 SLAM uncertainty와 map/pose consistency 평가로 확장한다. Primary와 secondary-stress dense-conflict diagnostic은 positive signal이고, frozen generalization split의 recall 및 detector substrate도 통과했다. 하지만 independent terminal validation은 `strict_depth_consistency_v1`이 wrong instance를 막지 못한다는 negative result를 만들었다. 다음 단계는 threshold tuning이 아니라 wrong-commit row diagnosis와 mechanism-level arbitration revision이다.

## Entry Order

새 작업을 시작하는 에이전트는 아래 순서로 읽는다.

1. `../AGENTS.md`
2. `../TODO.md`
3. `index.md`
4. `literature.md`
5. `hypothesis.md`
6. `paper.md`
7. `reproducibility.md`
8. `../literature/README.md`
9. `../literature/PAPER.md`
10. `../literature/Contribution Candidates.md`
11. `../literature/CAND-01.md`
12. `../hypothesis/README.md`

## Update Rules

- 새 workflow 문서가 생기면 이 파일의 `Workflow Docs`에 추가한다.
- 새 연구 산출물 folder가 생기면 관련 workflow 문서와 이 index에서 함께 연결한다.
- 긴 설명, paper summary, experiment detail은 이 파일에 넣지 않는다.
- 아직 필요하지 않은 `experiments/`, `paper/`, `decisions/` folder는 만들지 않는다.
- 루트에는 `AGENTS.md`, `.gitignore`, `README.md`, `TODO.md`, `summary.md`만 둔다.

## Index Page Convention

### 사실

- Markdown documentation site에서는 `docs/index.md`를 documentation home page로 두는 관례가 있다.
- contents page는 포함하는 문서의 overview와 link를 제공하는 역할을 한다.
- navigation page는 관련 문서로 이동하기 위한 link 중심 문서다.

### 에이전트 추론

이 repo의 `docs/index.md`는 documentation site home, workflow router, current research direction pointer 역할만 한다. 실제 연구 내용은 `literature/`와 `hypothesis/` 아래에 둔다.
