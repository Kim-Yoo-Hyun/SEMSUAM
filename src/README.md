# src

## Role

`src/`는 재현에 필요한 핵심 Python runtime package를 둔다. 현재 source-of-truth package는 `src/h001_runtime/`이다.

## Public Entry Point

- Current gate module: `h001_runtime.materialize_fully_covered_candidate_conditioned_contrast`
- Recommended wrapper: `scripts/run_fully_covered_contrast.sh`

`src/h001_runtime/`에는 현재 gate와 연결된 materializer뿐 아니라 기존 manifest 재현을 위해 참조되는 historical reproducer modules도 포함되어 있다. 새 논문 주장에 사용할 public surface는 README와 `docs/reproducibility.md`에 적힌 command로 제한한다.

## Usage

Docker command에서는 repo를 `/workspace`로 mount하고 `PYTHONPATH=/workspace/src`를 사용한다.

```bash
docker run --rm \
  -e PYTHONPATH=/workspace/src \
  -v "$PWD":/workspace:ro \
  -w /workspace \
  research3/openvocab-perception:20260513-v3c-gdino-sam2 \
  python -B -m h001_runtime.materialize_fully_covered_candidate_conditioned_contrast
```

## Rules

- 논문 주장에 필요한 core materializer, evaluator, utility code만 유지한다.
- 일회성 실행 wrapper는 `scripts/`에 둔다.
- 대용량 artifact, cache, generated output은 이 폴더에 두지 않는다.
