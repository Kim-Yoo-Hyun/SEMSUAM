# Evaluation

## Dataset / Benchmark

Replica, ScanNet.

## Splits

scene sequence split full read 필요.

## Metrics

- ATE
- mapping accuracy / completion
- completion ratio
- mIoU
- semantic segmentation metrics

## Baselines

- NIDS-SLAM
- Vox-Fusion
- other NeRF-SLAM baselines

## Main Results

- CVF snippet 기준 ScanNet semantic metrics에서 NIDS-SLAM 대비 up to 10% mIoU increase가 언급된다.

## Reproducibility Notes

CVF PDF accessible; code 확인 필요.

## Evaluation Weaknesses

closed-set semantic segmentation 중심이라 open-vocabulary navigation과 직접 연결하려면 추가 layer가 필요하다.
