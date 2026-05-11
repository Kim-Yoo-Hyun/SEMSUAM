# Evaluation

## Dataset / Metric Table

### 사실

| Evaluation unit | Dataset / scene | Main metrics | Baselines |
| --- | --- | --- | --- |
| OpenMask3D two-shot retrieval | Matterport3D, 10 scans, 214 rooms, 5370 object instances | retrieval success if point-cloud IoU > 0.25 | `No replan`, `Oracle`, `Max confidence`, `Random replan`, `Random from top-k` |
| VLMaps ObjectNav-style replanning | Matterport3D + HabitatSim, 10 scenes and 10 ObjectNav tasks with subtasks/subgoals per scene | replanning subgoal success within 1m | `No replan`, `Max confidence`, `Random replan`, CARe variants |
| Uncertainty / consistency ablation | same candidate sets with top-k confidence/category | classification entropy, channel-average feature standard error, mean pairwise KL divergence, latency | reversed uncertainty direction ablations, top-k variants |

### 에이전트 추론

| CAND-01 use | Useful metric | Missing for thesis harness |
| --- | --- | --- |
| Step 1-3 object/node uncertainty and replanning | entropy, standard error, KL divergence, retrieval/subgoal success | active viewpoint selection, map update after observation, `SPL`, wrong-goal visit, wasted path, `ATE/RPE` |

## Dataset / Benchmark

- OpenMask3D Object Retrieval Benchmark:
  - Matterport3D environment.
  - OpenMask3D map backbone.
  - Two-shot object retrieval task: first retrieval이 실패하면 second retrieval attempt를 허용한다.
  - Matterport raw category vocabulary: `1658` classes.
  - Evaluation scale: `10` scans / houses, `214` rooms, `5370` object instances.
- VLMaps ObjectNav-style Replanning:
  - Matterport3D + HabitatSim simulator.
  - VLMaps map backbone.
  - Following VLMaps setup, `10` scenes, random poses for map construction, and `10` object navigation tasks with subtasks/subgoals per scene.

## Splits

- OpenMask3D:
  - Each room is benchmarked separately.
  - In all baselines, first candidate is retrieved by maximum confidence for the query class.
  - If first attempt fails, CARe or baseline replanning selects a second candidate.
- VLMaps:
  - Maps are built from randomly generated poses and RGB-D observations.
  - If navigation fails, CARe proposes a new position of the specified class and checks whether it is near the correct object.
  - Paper does not report a standard Habitat ObjectNav train/val/test split; it follows VLMaps-style generated scenes/tasks.

## Metrics

- OpenMask3D retrieval success rate:
  - Retrieved object mask and GT mask point-cloud IoU are compared.
  - Success if IoU `> 0.25`.
- VLMaps replanning subgoal success rate:
  - Success if proposed point is within `1 meter` of the nearest specified object.
- Uncertainty signals:
  - classification entropy.
  - channel-average feature standard error.
  - mean pairwise KL divergence.
- Not reported as main metrics:
  - `SR` and `SPL` for full ObjectNav episodes.
  - `wrong-goal visit`, `wasted path`, `ATE`, `RPE`, pose graph connectivity.

## Baselines

- `No replan`: top-1 retrieval / no second attempt.
- `Oracle`: upper bound where any predicted 3D mask matching GT is counted as success.
- `Max confidence`: second-highest / highest unvisited confidence after failure.
- `Random replan`: randomly select from all unvisited candidates.
- `Random from top-k`: randomly select from high-confidence candidate set.
- CARe variants:
  - `Max entropy`.
  - `Min stderr`.
  - `Min pwKL`.
- Candidate selection criteria:
  - `Top-k Confidence`.
  - `Top-k Category`.

## Main Results

- OpenMask3D Object Retrieval:
  - `No replan`: `12.09%`.
  - `Max confidence`: `17.05%`.
  - Best non-Oracle baseline noted by paper: `Random from top-2 confidence`, `17.12%`.
  - Best CARe result: `Min pwKL` with `Top-k Category`, `k=40`, `18.75%`.
  - Other strong CARe entries include `Max entropy` with confidence, peak `18.20%` at `k=8`, and `Min stderr` with category, `18.07%`.
  - Oracle upper bound: `36.40%`, showing substantial remaining map/retrieval gap.
- VLMaps Replanning Subgoal:
  - `No replan`: `54.4%`.
  - `Max confidence`: `67.0%`.
  - `Random replan`: `56.2%`.
  - `Max entropy` with confidence reaches `81.0%` at `k=4`.
  - `Min stderr` with confidence reaches `82.7%` at `k=4`, and remains above `77%` across tested k values.
  - Appendix `Min KL from top-k confidence` reaches `85.2%` at `k=16`, but the paper notes two larger scenes were skipped due to memory limits, so direct comparison is weaker.
- Computational note:
  - Entropy and standard error are `O(n)` in candidate count.
  - Pairwise KL is `O(n^2)` and can be costly.
  - In OpenMask3D timing analysis, retrieval attempts are reported under `15 ms` when object features are precomputed.

## Reproducibility Notes

- Primary sources checked: OpenReview, PMLR proceedings, arXiv v2, project page, official GitHub.
- Local `paper.pdf` hash matches the PMLR and OpenReview PDF checked on 2026-05-07.
- Official GitHub: https://github.com/CARe-maps/CARe_experiments
- GitHub API checked on 2026-05-07:
  - repository is public.
  - MIT License.
  - created 2024-10-03.
  - pushed 2024-10-10.
  - updated 2025-09-11.
- README says the repository contains experiments under the OpenMask3D setting reported in the paper.
- Reproduction flow in README:
  - follow OpenMask3D setup.
  - install CARe requirements.
  - download Matterport3D-derived dataset from Hugging Face link.
  - run `preprocess_mp3d.py`.
  - run `download_om3d_models.sh`.
  - run `extract_mp3d_feature.py`.
  - run `evaluate_mp3d_top_category.py` and `evaluate_mp3d_top_confidence.py`.
- Reproduction risk:
  - Matterport3D / OpenMask3D dependencies are substantial.
  - README mainly documents OpenMask3D experiments, not a full VLMaps/Habitat reproduction path.

## Evaluation Weaknesses

- Full ObjectNav `SR` / `SPL` episode metrics are not the main reported metrics; VLMaps reports subgoal success.
- OpenMask3D evaluation assumes successful path planning and following, focusing on retrieval quality.
- Fixed semantic map only; no active re-observation, online map update, or SLAM correction.
- The method assumes frozen-model bias consistency. If model or map updates online, behavior may change.
- No direct evaluation of localization uncertainty, `ATE`, `RPE`, pose graph connectivity, map error, or real-world robot deployment.
- Pairwise KL has scaling and memory issues, which weakens its practicality for large maps unless precomputed or approximated.
