#!/usr/bin/env bash
set -euo pipefail

DATA_ROOT="${DATA_ROOT:-/data}"
mkdir -p "${DATA_ROOT}"

if [[ -z "${MATTERPORT_TOKEN_ID:-}" || -z "${MATTERPORT_TOKEN_SECRET:-}" ]]; then
  echo "MATTERPORT_TOKEN_ID and MATTERPORT_TOKEN_SECRET are required." >&2
  exit 2
fi

python /opt/datasets_download.py \
  --uids hm3d \
  --data-path "${DATA_ROOT}" \
  --username "${MATTERPORT_TOKEN_ID}" \
  --password "${MATTERPORT_TOKEN_SECRET}" \
  --no-replace

mkdir -p "${DATA_ROOT}/datasets/objectnav/hm3d"
curl --fail --location --continue-at - \
  "https://dl.fbaipublicfiles.com/habitat/data/datasets/objectnav/hm3d/v2/objectnav_hm3d_v2.zip" \
  -o "${DATA_ROOT}/datasets/objectnav/hm3d/objectnav_hm3d_v2.zip"

rm -rf "${DATA_ROOT}/datasets/objectnav/hm3d/v2"
mkdir -p "${DATA_ROOT}/datasets/objectnav/hm3d/v2"
unzip -q "${DATA_ROOT}/datasets/objectnav/hm3d/objectnav_hm3d_v2.zip" \
  -d "${DATA_ROOT}/datasets/objectnav/hm3d/v2"

python /opt/check_hm3d.py "${DATA_ROOT}"
