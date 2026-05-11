# Insights

## Facts

- `NaVid: Video-based VLM Plans the Next Step for Vision-and-Language Navigation`는 RSS 2024 / arXiv 2024로 registry에 기록했다.
- Primary source는 https://arxiv.org/abs/2402.15852 이다.
- 현재 note는 primary source abstract / official page / publisher page 기준의 skimmed 정리다.

## Paper Claims

- maps, odometers, depth inputs 없이 state-of-the-art-level navigation performance와 Sim2Real transfer를 보인다고 주장한다.

## Inferences

- SLAM-free baseline으로 반드시 비교해야 할 축이다.
- 석사 연구 관점에서는 full system 재현보다 representation, uncertainty signal, evaluation metric을 작게 분리하는 방식이 현실적이다.

## 사용자 판단 필요

- 이 논문을 implementation baseline으로 둘지, trend evidence로만 둘지 결정해야 한다.
- full read 단계에서 exact dataset split, metric table, code 실행 가능성을 확인해야 한다.

## Connection to Field Trends

- Active perception / environmental perception intelligence / SLAM-navigation coupling 중 하나 이상의 축에 연결된다.
- `literature/README.md`의 Trend Synthesis와 비교해 trend evidence인지 low-confidence insight인지 다시 분류할 필요가 있다.

## Possible Contribution Angles

- semantic memory map vs video-only memory ablation
- SLAM pose noise 조건에서 NaVid-style baseline 비교
- ObjectNav/VLN에서 explicit map의 marginal gain 측정

## What Would Change This Assessment

model weights/code가 공개되어 있으면 baseline 실험 후보가 된다.
