# results

## Role

`results/`는 공유 가능한 가벼운 결과 요약, table, log summary만 둔다.

## Current Summary

- 최신 H001 gate summary는 `current_gate_summary.md`를 확인한다.
- Raw run artifact는 `local_dataset/runs`에 있고 Git source-of-truth가 아니다.
- Raw logs는 `archive/logs/`에 보존하며, 필요한 핵심 요약만 이 폴더에 둔다.

## Rules

- 대용량 JSONL, frame, mask, checkpoint, cache는 이 폴더에 두지 않는다.
- 논문 표로 승격 가능한 값은 source command와 artifact path를 함께 기록한다.
