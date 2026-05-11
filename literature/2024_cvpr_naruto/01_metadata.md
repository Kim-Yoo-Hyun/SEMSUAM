# NARUTO: Neural Active Reconstruction from Uncertain Target Observations

- Date checked: 2026-05-07
- Year: 2024
- Venue / status: CVPR 2024, pages 21572-21583
- Authors: Ziyue Feng, Huangying Zhan, Zheng Chen, Qingan Yan, Xiangyu Xu, Changjiang Cai, Bing Li, Qilun Zhu, Yi Xu
- Link: https://openaccess.thecvf.com/content/CVPR2024/html/Feng_NARUTO_Neural_Active_Reconstruction_from_Uncertain_Target_Observations_CVPR_2024_paper.html
- PDF: https://openaccess.thecvf.com/content/CVPR2024/papers/Feng_NARUTO_Neural_Active_Reconstruction_from_Uncertain_Target_Observations_CVPR_2024_paper.pdf
- Local PDF: `paper.pdf`
- PDF version: CVF Open Access accepted version; arXiv v2 last revised 2024-04-16
- PDF downloaded: 2026-05-06
- Code: https://github.com/oppo-us-research/NARUTO
- Project page: https://oppo-us-research.github.io/NARUTO-website/
- Dataset: HabitatSim with Replica and Matterport3D / MP3D
- Tags: neural active reconstruction, uncertainty learning, NBV, path planning, HabitatSim, Replica, MP3D, Co-SLAM, Active Ray Sampling, hybrid neural representation
- Reading status: Read

## Source Checks

### 사실

- arXiv records `arXiv:2402.18771` as submitted on 2024-02-29 and revised to v2 on 2024-04-16.
- arXiv lists the paper as accepted to CVPR 2024 and links the project page and code.
- The project page links paper, arXiv, video, code, and poster.
- The official GitHub repository is public under `oppo-us-research/NARUTO` and describes itself as the official implementation.
- The GitHub repository lists Docker and Anaconda installation paths, uses HabitatSim and Co-SLAM, and provides run scripts for Replica and MP3D.

### 사용자 판단 필요

- Code 실행 검증은 아직 하지 않았다.
- `CAND-01`에서 P05를 implementation baseline으로 쓸지, uncertainty-aware planning reference로만 쓸지 결정해야 한다.
