# ConceptGraphs: Open-Vocabulary 3D Scene Graphs for Perception and Planning

- Date checked: 2026-05-07
- Year: 2024
- Venue / status: ICRA 2024, pages 5021-5028; arXiv preprint also available
- Authors: Qiao Gu, Alihusein Kuwajerwala, Sacha Morin, Krishna Murthy Jatavallabhula, Bipasha Sen, Aditya Agarwal, Corban Rivera, William Paul, Kirsty Ellis, Rama Chellappa, Chuang Gan, Celso Miguel de Melo, Joshua B. Tenenbaum, Antonio Torralba, Florian Shkurti, Liam Paull
- Link: https://concept-graphs.github.io/
- PDF: https://concept-graphs.github.io/assets/pdf/2023-ConceptGraphs.pdf
- Local PDF: `paper.pdf`
- PDF version: project-page PDF / arXiv v1, submitted 2023-09-28
- PDF downloaded: 2026-05-06
- Code: https://github.com/concept-graphs/concept-graphs
- Project page: https://concept-graphs.github.io/
- Dataset: Replica, REAL Lab scan, AI2Thor / ProcThor demo setting, real-world Jackal and Spot demos
- Tags: open-vocabulary 3D scene graph, object-centric semantic map, foundation models, planning, CLIP, SAM, LLaVA, GPT-4, Replica, REAL Lab, Jackal, Spot, AI2Thor
- Reading status: Read

## Source Checks

### 사실

- Project page records the paper as ICRA 2024 and gives pages 5021-5028 in BibTeX.
- arXiv records `arXiv:2309.16650` as submitted on 2023-09-28 and lists the project page / explainer video in comments.
- DBLP records DOI `10.1109/ICRA57147.2024.10610243` and ICRA 2024 pages 5021-5028.
- The local PDF has 11 pages and was created on 2023-09-29 according to PDF metadata.
- Official code is `concept-graphs/concept-graphs`.
- GitHub API check on 2026-05-07 shows the repository is public, default branch `main`, created 2023-09-28, last pushed 2025-10-16, with 842 stars and 120 forks at check time.
- Repository README states the `ali-dev` branch is a refactored real-time implementation supporting RGB-D video from iPhone and Rerun visualization.
- Repository README links separate real-world Jackal mapping/navigation code and notes AI2Thor localization/mapping code is included.

### 사용자 판단 필요

- Citation에는 ICRA 2024 published metadata를 사용한다.
- `CAND-01`에서 full ConceptGraphs reproduction을 할지, node/edge memory representation만 가져올지 결정해야 한다.
