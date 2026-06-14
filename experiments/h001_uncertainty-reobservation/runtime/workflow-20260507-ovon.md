# HM3D-OVON Dataset Workflow

## Purpose

This workflow records how HM3D-OVON episode data is acquired and checked for CAND-01 / H001.

## Linked Research Item

- Candidate: `literature/CAND-01.md`
- Hypothesis: `experiments/h001_uncertainty-reobservation/`
- First experiment: `experiments/h001_uncertainty-reobservation/04_first_experiment.md`

## Facts

- Date checked: 2026-05-07
- Official code source: `naokiyokoyama/ovon`
- Dataset source: Hugging Face `nyokoyama/hm3d_ovon`
- Downloaded archive: `hm3d.tar.gz`
- Host archive path: `/tmp/research3-data/datasets/ovon/hm3d.tar.gz`
- Host extracted path: `/tmp/research3-data/datasets/ovon/hm3d`
- Docker image used for download/check: `research3/hm3d-download:20260507`
- Docker mount path: `/data/datasets/ovon/hm3d`

## Download Command

```bash
sg docker -c 'docker run --rm \
  -v /tmp/research3-data:/data \
  research3/hm3d-download:20260507 \
  bash -lc "set -euo pipefail; \
    mkdir -p /data/datasets/ovon; \
    curl --fail --location --continue-at - \
      https://huggingface.co/datasets/nyokoyama/hm3d_ovon/resolve/main/hm3d.tar.gz \
      -o /data/datasets/ovon/hm3d.tar.gz; \
    rm -rf /data/datasets/ovon/hm3d; \
    tar -xzf /data/datasets/ovon/hm3d.tar.gz -C /data/datasets/ovon; \
    find /data/datasets/ovon/hm3d -name '\''._*'\'' -delete"'
```

## Smoke Check Command

```bash
sg docker -c 'docker run --rm \
  -v /tmp/research3-data:/data:ro \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/hm3d-download:20260507 \
  python /workspace/scripts/h001_tools/check_ovon.py /data'
```

## Smoke Result

```text
status: ok
ovon_path: /data/datasets/ovon/hm3d
total json.gz files: 257
```

Split files:

| Split | total `json.gz` | content `json.gz` | sample content episode count |
| --- | ---: | ---: | ---: |
| `train` | 146 | 145 | 50000 |
| `val_seen` | 37 | 36 | 95 |
| `val_unseen` | 37 | 36 | 121 |
| `val_seen_synonyms` | 37 | 36 | 98 |

## Paper Claims

- HM3D-OVON is designed for open-vocabulary ObjectNav on HM3D.
- The benchmark expands ObjectNav beyond a closed class set and is therefore more aligned with language-indexed semantic map uncertainty.

## Inferences

HM3D-OVON is a better extension target than MP3D for H001 because semantic ambiguity and open-vocabulary candidate ranking are closer to the central claim: semantic uncertainty can be converted into active SLAM/navigation utility.

The next implementation blocker is not dataset access. It is runtime integration: loading HM3D scenes, reading HM3D-OVON episode shards, extracting semantic candidates, and logging wrong-goal / wasted path behavior.

## User Decision Needed

- Decide whether the first probe should use closed-vocabulary `ObjectNav HM3D v2` first, then HM3D-OVON, or start directly from HM3D-OVON after runtime integration.
