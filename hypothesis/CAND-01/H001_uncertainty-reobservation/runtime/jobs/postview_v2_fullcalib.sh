#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
OUT=${OUT:-/tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1}
LOG=${LOG:-$ROOT/logs/postview-evidence-v2-fullcalib-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/logs" "$OUT"
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
echo "output_root=$OUT"
echo "log=$LOG"

CURRENT_STAGE=frame_export
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm --gpus all --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/tmp \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-data:/data:ro \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/habitat-h001:20260508-calib-artifacts \
  micromamba run -n base python -m h001_runtime.export_postview_frames_v2 \
    --data-root /data \
    --viewpoint-decisions /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/viewpoint_decisions.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --out-root /runs/h001_postview_scores_v2_random256_k10_sr1_v1 \
    --policy EvidenceGatedSemanticOnly \
    --max-decisions 0 \
    --max-candidates-per-decision 5 \
    --yaw-offsets=-30,0,30"

python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1")
rows = [json.loads(line) for line in (root / "postview_frames_v2.jsonl").open() if line.strip()]
assert len(rows) == 50, len(rows)
assert all(row.get("uses_gt_for_action") is False for row in rows)
assert min(len(row.get("rendered_headings", [])) for row in rows) >= 1
print({
    "stage": "frame_export_verified",
    "rows": len(rows),
    "heading_count": sum(len(row.get("rendered_headings", [])) for row in rows),
})
PY

CURRENT_STAGE=scoring
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/models \
  -e XDG_CACHE_HOME=/models/.cache \
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-models:/models \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/vlmaps-hm3d:20260508-timmfix \
  python -m h001_runtime.score_postview_v2 \
    --frames /runs/h001_postview_scores_v2_random256_k10_sr1_v1/postview_frames_v2.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --query-embeddings /runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings \
    --out /runs/h001_postview_scores_v2_random256_k10_sr1_v1/postview_scores.jsonl \
    --device cpu \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --crop-radii-px=12,24,36 \
    --strict-depth-check \
    --no-center-fallback-for-action"

python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_scores_v2_random256_k10_sr1_v1")
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
print({
    "stage": "scoring_verified",
    "rows": len(rows),
    "candidate_score_count": scoring.get("candidate_score_count"),
    "action_eligible_row_rate": scoring.get("action_eligible_row_rate"),
})
PY

CURRENT_STAGE=verified
write_status completed "$CURRENT_STAGE"
echo "completed_at=$(date -Is)"
