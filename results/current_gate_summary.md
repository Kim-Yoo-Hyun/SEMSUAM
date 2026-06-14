# Current Gate Summary

## 사실

- Date checked: 2026-06-14
- Current gate: `candidate_conditioned_blocker_multi_case_validation_contract`
- Latest verified materializer: `fully_covered_candidate_conditioned_contrast_v1`
- Code: `src/h001_runtime/materialize_fully_covered_candidate_conditioned_contrast.py`
- Manifest: `configs/h001/manifests/h001_fully_covered_candidate_conditioned_contrast_v1.json`
- Verify file: `configs/h001/manifests/h001_fully_covered_candidate_conditioned_contrast_v1.verify.json`
- Output summary: `local_dataset/runs/h001_fully_covered_candidate_conditioned_contrast_v1/fully_covered_candidate_conditioned_contrast_summary.json`
- Docker image: `research3/openvocab-perception:20260513-v3c-gdino-sam2`

## Result Snapshot

- Materializer gate: passed
- Pair / candidate / candidate-role / alternative rows: `2 / 4 / 16 / 7`
- Primary blocker: `multi_case_candidate_conditioned_blocker_validation_required`
- Current blocked claims: terminal utility, policy-scale comparison, paper claim

## Reproduction

```bash
bash scripts/run_fully_covered_contrast.sh

jq '{status, contrast_materializer_gate_passed, primary_blocker, next_task}' \
  local_dataset/runs/h001_fully_covered_candidate_conditioned_contrast_v1/fully_covered_candidate_conditioned_contrast_summary.json
```
