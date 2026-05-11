# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| Semantic loop closure missions | author-collected GPS-denied three-story indoor building | position error, yaw error, error reduction | VOXL VIO, proposed without SLC |
| Autonomous exploration missions | author-collected multi-floor indoor UAV missions | pose covariance trace, semantic landmark covariance trace, trajectory length, CPU utilization | proposed with / without SLC |
| Benchmark SLAM comparison | six author-collected datasets | odometry drift, failure cases under viewpoint change | Kimera, ORB-SLAM3 |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 4-5 semantic SLAM uncertainty | pose / landmark covariance trace, drift, loop closure error reduction | ObjectNav `SR` / `SPL`, semantic accuracy over multiple object classes, active re-observation cost |

## Dataset / Benchmark

- Real-world GPS-denied cluttered multi-floor indoor environment collected by the authors
- Loop closure experiments inside a three-story building
- Autonomous exploration missions in multi-floor indoor environment
- Benchmark comparison on six author-collected datasets against Kimera and ORB-SLAM3

## Splits

논문은 machine learning dataset split 형태의 train/validation/test split을 쓰지 않는다. 평가 단위는 loop closure missions, autonomous exploration missions, benchmark datasets이다.

## Metrics

- Position Error (m)
- Yaw Error (deg)
- Error Reduction (%)
- Average robot pose uncertainty: trace of covariance matrix in semantic factor graph
- Average semantic landmark uncertainty: trace of covariance matrix
- Odometry drift (%)
- CPU utilization (%)
- Trajectory Length (m)

## Baselines

- VOXL VIO / commercial VIO solution
- proposed system without SLC
- Kimera
- ORB-SLAM3

## Main Results

- CPU utilization: full stack 42.2-53.3%; semantic front end around 34%; metric-semantic backend 0.88%; COP module 0.58%; SLC module 0.23%.
- Loop closure experiments: position error reduction 83.78-92.68%; yaw error reduction 39.79-61.82%.
- Autonomous exploration Auto 1: upon SLC, average pose uncertainty reduction 56.67%; with SLC vs without SLC after mission, average pose uncertainty reduction 52.06% and average landmark uncertainty reduction 68.53%; trajectory length 227.47 m.
- Multiple autonomous missions: upon SLC, average pose uncertainty reduction 45.72-56.67%, with one consecutive-SLC case reported as 52.98% and 14.62%.
- Benchmark comparison: Kimera and ORB-SLAM3 fail on some datasets under drastic viewpoint changes; on successful datasets, Kimera drift is 1.93-3.71%, ORB-SLAM3 drift is 0.45-1.51%, while the proposed SLC system reports drift consistently under 0.5%.

## Reproducibility Notes

- Project page and code are available.
- PDF version checked locally: arXiv:2309.06950v4 [cs.RO], 2025-07-21.
- Hardware stack is specific: Falcon 250 UAV, Intel Realsense D435i, VOXL VIO, Intel NUC i7-10710U, YOLOv8m, GTSAM.
- The exact mission datasets and annotations should be checked before assuming full replication is possible.

## Evaluation Weaknesses

- 평가가 standardized public benchmark 중심이 아니라 author-collected real-world missions 중심이다.
- semantic object class가 chair 중심이라 multi-class semantic reliability를 판단하기 어렵다.
- ObjectNav, SPL, semantic search success 같은 downstream navigation metric은 직접 평가하지 않는다.
- dynamic environment, open-vocabulary detection, long-term map change는 평가 범위 밖이다.
- Kimera / ORB-SLAM3 비교는 useful baseline이지만 semantic loop closure의 generality를 충분히 분리해 검증하려면 더 많은 controlled ablation이 필요하다.
