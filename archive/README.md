# archive

## Role

`archive/`는 삭제가 애매하지만 현재 shareable core path에서는 제외한 legacy/raw material을 보존한다.

## Contents

- `moved.md`: archive로 이동한 항목의 짧은 목록
- `logs/root/`: 이전 루트 `logs/` raw logs
- `logs/h001_runtime/`: 이전 H001 runtime raw logs
- `cache/`: 재현에 필요 없는 local cache가 이동될 수 있는 위치

## Rules

- archive의 raw log와 cache는 Git source-of-truth가 아니다.
- 논문 주장에 필요한 결과는 archive raw log가 아니라 `results/`, `docs/reproducibility.md`, 또는 H001 workflow 문서에 요약한다.
- 삭제 여부가 확실해지기 전까지는 archive로 이동하고, 무조건 삭제하지 않는다.
