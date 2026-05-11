# Multimodal LLM Guided Exploration and Active Mapping using Fisher Information

- Date checked: 2026-05-07
- Year: 2025
- Venue / status: ICCV 2025, pages 5392-5404; arXiv preprint also available
- Authors: Wen Jiang, Boshu Lei, Katrina Ashton, Kostas Daniilidis
- Link: https://openaccess.thecvf.com/content/ICCV2025/html/Jiang_Multimodal_LLM_Guided_Exploration_and_Active_Mapping_using_Fisher_Information_ICCV_2025_paper.html
- PDF: https://openaccess.thecvf.com/content/ICCV2025/papers/Jiang_Multimodal_LLM_Guided_Exploration_and_Active_Mapping_using_Fisher_Information_ICCV_2025_paper.pdf
- Local PDF: `paper.pdf`
- PDF version: CVF open access accepted-version PDF; arXiv v3 last revised 2025-09-05
- PDF downloaded: 2026-05-06
- Code: https://github.com/JiangWenPL/multimodal-active
- Project page: author project listing at https://jiangwenpl.github.io/; no separate dedicated project page found
- Dataset: Gibson, Habitat-Matterport 3D
- Tags: multimodal LLM, active mapping, Fisher Information, 3DGS, localization uncertainty, Expected Information Gain, Habitat simulator, Gibson, HM3D, GPT-4o, Llava-7b
- Reading status: Read

## Source Checks

### 사실

- CVF records the paper as `Multimodal LLM Guided Exploration and Active Mapping using Fisher Information`, ICCV 2025, pages 5392-5404.
- arXiv records `arXiv:2410.17422` as submitted on 2024-10-22 and last revised on 2025-09-05 as v3.
- arXiv lists the comment as `ICCV 2025`.
- The local PDF is the CVF open access PDF with 13 pages.
- The authors' website links to `JiangWenPL/multimodal-active` as code.
- GitHub API check on 2026-05-07 shows `JiangWenPL/multimodal-active` is public, default branch `master`, created 2025-10-07, last pushed 2025-10-21, with 4 commits, 8 stars, and 1 fork at check time.

### 사용자 판단 필요

- Citation에는 CVF/ICCV published title을 사용한다.
- Code README에는 internal cluster paths, `ckpt` symlink, `OPENAI_API_KEY`, custom CUDA extensions, and Habitat data setup assumptions이 남아 있어 direct reproduction baseline으로 둘지 trend evidence로만 둘지 판단이 필요하다.
