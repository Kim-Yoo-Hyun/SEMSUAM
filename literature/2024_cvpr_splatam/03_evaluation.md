# Evaluation

## Dataset / Benchmark

Replica, TUM-RGBD, ScanNet++.

## Splits

dataset별 standard sequence; exact scene list full read 필요.

## Metrics

- ATE / trajectory error
- PSNR
- SSIM
- LPIPS
- depth / reconstruction metrics 확인 필요

## Baselines

- Point-SLAM
- ORB-SLAM3 RGB-D
- other dense SLAM baselines

## Main Results

- CVF snippet 기준 Point-SLAM 대비 trajectory error 개선과 ScanNet++ evaluation이 확인된다.

## Reproducibility Notes

GitHub code가 공개되어 있다.

## Evaluation Weaknesses

closed-loop active navigation에서 collision, exploration cost, semantic success는 평가하지 않는다.
