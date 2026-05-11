# Active Semantic Mapping and Pose Graph Spectral Analysis for Robot Exploration

- Date checked: 2026-05-06
- Year: 2024
- Venue / status: IROS 2024, conference paper, pages 13787-13794
- Authors: Rongge Zhang, Haechan Mark Bong, Giovanni Beltrame
- Link: https://arxiv.org/abs/2408.14726
- PDF: https://arxiv.org/pdf/2408.14726
- Local PDF: `paper.pdf`
- PDF version: arXiv v2, last revised 2024-09-02; DOI version: 10.1109/IROS58592.2024.10802821
- PDF downloaded: 2026-05-06
- Code: https://github.com/BohemianRhapsodyz/semantic_exploration
- Project page: none found
- Dataset: Habitat simulator, Matterport3D scenes
- Tags: Active SLAM, metric-semantic SLAM, pose graph spectral analysis, semantic mutual information, exploration, Habitat, Matterport3D
- Reading status: Read

## Source Checks

### 사실

- arXiv records `arXiv:2408.14726` as submitted on 2024-08-27 and revised to v2 on 2024-09-02.
- PolyPublie and dblp list the paper as IROS 2024 with DOI `10.1109/IROS58592.2024.10802821`.
- The paper states that the implementation is publicly available at `BohemianRhapsodyz/semantic_exploration`.
- The GitHub repository is public and lists dependencies including ROS Noetic, OctoMap, PCL, Eigen, OpenCV, and Python3.

### 사용자 판단 필요

- Code reproducibility는 아직 실행 검증 전이다. `CAND-01` Step 4-5 baseline으로 채택하려면 ROS Noetic / Habitat / ORB-SLAM2 dependency를 local environment에서 따로 확인해야 한다.
