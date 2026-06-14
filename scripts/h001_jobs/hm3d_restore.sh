#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
IMAGE=${IMAGE:-research3/hm3d-download:20260507}
OUT=${OUT:-/tmp/research3-runs/hm3d_restore}
LOG=${LOG:-$ROOT/archive/logs/root/hm3d-restore-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/archive/logs/root" "$OUT" "$DATA_ROOT"
chmod 777 "$DATA_ROOT" || true
exec > >(tee -a "$LOG") 2>&1

write_status() {
  local job_state="$1"
  local stage="$2"
  local now
  now="$(date -Is)"
  printf '{"status":"%s","stage":"%s","updated_at":"%s","image":"%s","data_root":"%s","output_root":"%s","log":"%s"}\n' \
    "$job_state" "$stage" "$now" "$IMAGE" "$DATA_ROOT" "$OUT" "$LOG" > "$STATUS"
}

on_error() {
  local code="$?"
  write_status failed "${CURRENT_STAGE:-unknown}"
  echo "failed_stage=${CURRENT_STAGE:-unknown}"
  echo "exit_code=$code"
  exit "$code"
}
trap on_error ERR

cd "$ROOT"
echo "started_at=$(date -Is)"
echo "image=$IMAGE"
echo "data_root=$DATA_ROOT"
echo "output_root=$OUT"
echo "log=$LOG"
echo "expected_files=scene_datasets/hm3d, datasets/objectnav/hm3d/v2"
echo "verification_command=python scripts/h001_tools/check_hm3d.py $DATA_ROOT"

if [[ -z "${MATTERPORT_TOKEN_ID:-}" || -z "${MATTERPORT_TOKEN_SECRET:-}" ]]; then
  echo "MATTERPORT_TOKEN_ID and MATTERPORT_TOKEN_SECRET must be provided in the environment." >&2
  exit 2
fi

CURRENT_STAGE=download_hm3d
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm \
  -e MATTERPORT_TOKEN_ID \
  -e MATTERPORT_TOKEN_SECRET \
  -e DATA_ROOT=/data \
  -v $DATA_ROOT:/data \
  $IMAGE"

CURRENT_STAGE=verify
write_status running "$CURRENT_STAGE"
python scripts/h001_tools/check_hm3d.py "$DATA_ROOT" > "$OUT/check_hm3d.json"
cat "$OUT/check_hm3d.json"

CURRENT_STAGE=verified
write_status completed "$CURRENT_STAGE"
echo "completed_at=$(date -Is)"
