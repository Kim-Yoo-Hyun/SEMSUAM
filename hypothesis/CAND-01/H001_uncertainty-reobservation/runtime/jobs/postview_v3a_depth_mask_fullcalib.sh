#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
SOURCE=${SOURCE:-/tmp/research3-runs/h001_postview_scores_v2_1_relaxed_position_random256_k10_sr1_v1}
OUT=${OUT:-/tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1}
DIAG=${DIAG:-/tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1}
LOG=${LOG:-$ROOT/logs/postview-evidence-v3a-depth-mask-fullcalib-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/logs" "$OUT" "$DIAG"
exec > >(tee -a "$LOG") 2>&1

write_status() {
  local job_state="$1"
  local stage="$2"
  local now
  now="$(date -Is)"
  printf '{"status":"%s","stage":"%s","updated_at":"%s","output_root":"%s","diagnostic_root":"%s","log":"%s"}\n' \
    "$job_state" "$stage" "$now" "$OUT" "$DIAG" "$LOG" > "$STATUS"
}

on_error() {
  local code="$?"
  local now
  now="$(date -Is)"
  printf '{"status":"failed","stage":"%s","failed_at":"%s","exit_code":%s,"output_root":"%s","diagnostic_root":"%s","log":"%s"}\n' \
    "${CURRENT_STAGE:-unknown}" "$now" "$code" "$OUT" "$DIAG" "$LOG" > "$STATUS"
  exit "$code"
}
trap on_error ERR

cd "$ROOT"
echo "started_at=$(date -Is)"
echo "source_root=$SOURCE"
echo "output_root=$OUT"
echo "diagnostic_root=$DIAG"
echo "log=$LOG"

CURRENT_STAGE=prepare
write_status running "$CURRENT_STAGE"
cp "$SOURCE/postview_frames_v2.jsonl" "$OUT/postview_frames_v2.jsonl"
ln -sfn "../h001_postview_scores_v2_random256_k10_sr1_v1/frames" "$OUT/frames"
rm -f "$OUT/postview_scores.jsonl" "$OUT/summary.json"
rm -rf "$OUT/mask_debug"
rm -f "$DIAG/candidate_score_table.jsonl" "$DIAG/row_summary.jsonl" "$DIAG/query_breakdown.json" "$DIAG/threshold_sweep.jsonl" "$DIAG/summary.json"

python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1")
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
  -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
  -v /tmp/research3-models:/models \
  -v /tmp/research3-runs:/runs \
  -v /home/yoohyun/research3:/workspace:ro \
  research3/vlmaps-hm3d:20260508-timmfix \
  python -m h001_runtime.score_postview_v3_depth_mask \
    --frames /runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/postview_frames_v2.jsonl \
    --candidate-artifact /runs/h001_calibration_artifacts_random256_k10_sr1_v1/all_scenes_aligned.jsonl \
    --query-embeddings /runs/h001_calibration_artifacts_random256_k10_sr1_v1/embeddings \
    --out /runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/postview_scores.jsonl \
    --debug-root /runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/mask_debug \
    --device cpu \
    --semantic-tie-band 0.01 \
    --max-candidates-per-frame 5 \
    --candidate-point-field position \
    --mask-search-radius-px 48 \
    --mask-depth-band-m 0.45 \
    --min-mask-area-px 80 \
    --max-mask-area-ratio 0.35 \
    --max-debug-images 240"

CURRENT_STAGE=scoring_verification
write_status running "$CURRENT_STAGE"
python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1")
rows = [json.loads(line) for line in (root / "postview_scores.jsonl").open() if line.strip()]
summary = json.loads((root / "summary.json").read_text())
scoring = summary.get("postview_scoring_v3a_depth_mask", {})
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
    "object_mask_valid_row_rate": scoring.get("object_mask_valid_row_rate"),
    "debug_images_written": scoring.get("debug_images_written"),
    "projection_status_counts": scoring.get("projection_status_counts"),
})
PY

CURRENT_STAGE=diagnostic
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
  python -m h001_runtime.analyze_postview_scores_v2 \
    --postview-scores /runs/h001_postview_scores_v3a_depth_mask_random256_k10_sr1_v1/postview_scores.jsonl \
    --candidate-decisions /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/candidate_decisions.jsonl \
    --episodes /runs/h001_calibration_policy_random256_k10_sr1_v1/policy_revision/episodes.jsonl \
    --out-root /runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1 \
    --expected-rows 50 \
    --baseline-wrong-goal-visible-correct 6 \
    --baseline-wrong-goal-rows 19 \
    --min-wrong-goal-agg-top-correct 1 \
    --min-action-eligible-row-rate 0.70"

CURRENT_STAGE=diagnostic_verification
write_status running "$CURRENT_STAGE"
python - <<'PY'
import json
from pathlib import Path

root = Path("/tmp/research3-runs/h001_postview_score_calibration_v3a_depth_mask_random256_k10_sr1_v1")
expected = [
    "candidate_score_table.jsonl",
    "row_summary.jsonl",
    "query_breakdown.json",
    "threshold_sweep.jsonl",
    "summary.json",
]
for name in expected:
    assert (root / name).exists(), name
summary = json.loads((root / "summary.json").read_text())
assert summary.get("score_rows") == 50, summary
assert summary.get("candidate_score_rows", 0) > 0, summary
print({
    "stage": "diagnostic_verified",
    "score_rows": summary.get("score_rows"),
    "candidate_score_rows": summary.get("candidate_score_rows"),
    "decision_gate": summary.get("decision_gate"),
    "action_eligible_row_rate": summary.get("action_eligible_row_rate"),
    "correct_vs_wrong_auc": summary.get("correct_vs_wrong_auc"),
    "wrong_goal_rows_with_action_eligible_correct_candidate": summary.get("wrong_goal_rows_with_action_eligible_correct_candidate"),
})
PY

CURRENT_STAGE=verified
write_status completed "$CURRENT_STAGE"
echo "completed_at=$(date -Is)"
