# configs

## Role

`configs/`는 재현에 필요한 Dockerfile, manifest, verify contract, 고정 설정을 둔다.

## Contents

- `docker/`: Docker image build definitions
- `h001/manifests/`: H001 frozen contracts and verify files

## Rules

- dataset, checkpoint, credential, generated run artifact는 이 폴더에 두지 않는다.
- manifest는 실행 전 contract와 gate를 고정하기 위한 source-of-truth로 취급한다.
- Docker image 자체는 GitHub source-of-truth가 아니며, build command와 Dockerfile만 보존한다.
