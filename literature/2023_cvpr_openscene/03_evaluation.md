# Evaluation

## Dataset / Benchmark

ScanNet, Matterport3D, 3DSSG; exact task datasets full read 필요.

## Splits

dataset task split full read 필요.

## Metrics

- mIoU
- mAP
- zero-shot semantic segmentation metrics
- retrieval/query relevance metrics 확인 필요

## Baselines

- fully-supervised 3D methods
- open-vocabulary 2D/3D baselines

## Main Results

- CVF source는 dense 3D point-text/image co-embedding으로 open-vocabulary queries를 지원한다고 설명한다.

## Reproducibility Notes

official GitHub and project page available.

## Evaluation Weaknesses

SLAM pose noise와 online incremental mapping에서 성능이 그대로 유지되는지 별도 확인 필요.
