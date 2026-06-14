#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
SOURCE=${SOURCE:-/tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1}
OUT=${OUT:-/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1}
LOG=${LOG:-$ROOT/archive/logs/root/postview-evidence-v2-1-relaxed-position-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/archive/logs/root" "$OUT"
exec > >(tee -a "$LOG") 2>&1

write_status() {
  local job_state="$1"
  local stage="$2"
  local now
  now="$(date -Is)"
  printf '{"status":"%s","stage":"%s","updated_at":"%s","output_root":"%s","log":"%s"}\n' \
    "$job_state" "$stage" "$now" "$OUT" "$LOG" > "$STATUS"
}

on_error() {
  local code="$?"
  local now
  now="$(date -Is)"
  printf '{"status":"failed","stage":"%s","failed_at":"%s","exit_code":%s,"output_root":"%s","log":"%s"}\n' \
    "${CURRENT_STAGE:-unknown}" "$now" "$code" "$OUT" "$LOG" > "$STATUS"
  exit "$code"
}
trap on_error ERR

cd "$ROOT"
echo "started_at=$(date -Is)"
echo "source_root=$SOURCE"
echo "output_root=$OUT"
echo "log=$LOG"

CURRENT_STAGE=prepare
write_status running "$CURRENT_STAGE"
cp "$SOURCE/postview_frames_v2.jsonl" "$OUT/postview_frames_v2.jsonl"
ln -sfn "../$(basename "$SOURCE")/frames" "$OUT/frames"

python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1")
rows = [json.loads(line) for line in (root / "postview_frames_v2.jsonl").open() if line.strip()]
assert len(rows) == 50, len(rows)
assert (root / "frames").exists(), root / "frames"
assert all(row.get("uses_gt_for_action") is False for row in rows)
print({
    "stage": "prepared",
    "rows": len(rows),
    "frames_link": str((root / "frames").resolve()),
})
PY

CURRENT_STAGE=scoring
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/models \
  -e XDG_CACHE_HOME=/models/.cache \
  -e PYTHONPATH=/workspace/src \
  -v /tmp/research3-models:/models \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/vlmaps-hm3d:20260508-timmfix \
  python -m h001_runtime.score_postview_v2 \
    --frames /runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_frames_v2.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --query-embeddings /runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings \
    --out /runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1/postview_scores.jsonl \
    --device cpu \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --crop-radii-px=12,24,36 \
    --candidate-point-field position \
    --no-strict-depth-check \
    --no-center-fallback-for-action"

python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1")
rows = [json.loads(line) for line in (root / "postview_scores.jsonl").open() if line.strip()]
summary = json.loads((root / "summary.json").read_text())
scoring = summary.get("postview_scoring_v2", {})
assert len(rows) == 50, len(rows)
assert all(row.get("uses_gt_for_action") is False for row in rows)
assert all(
    score.get("center_fallback_used_for_action") is False
    for row in rows
    for score in row.get("candidate_scores", [])
)
assert scoring.get("rows_scored") == 50, scoring
assert float(scoring.get("action_eligible_row_rate") or 0.0) >= 0.70, scoring
print({
    "stage": "scoring_verified",
    "rows": len(rows),
    "candidate_score_count": scoring.get("candidate_score_count"),
    "action_eligible_row_rate": scoring.get("action_eligible_row_rate"),
    "projection_status_counts": scoring.get("projection_status_counts"),
})
PY

CURRENT_STAGE=verified
write_status completed "$CURRENT_STAGE"
echo "completed_at=$(date -Is)"
