#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
RUNS_ROOT=${RUNS_ROOT:-/tmp/research3-runs}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
MODEL_ROOT=${MODEL_ROOT:-/tmp/research3-models}
OUT_ROOT=${OUT_ROOT:-${RUNS_ROOT}/h001_dense_backend_recall_y9h_chair_v1}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
VLMAPS_IMG=${VLMAPS_IMG:-research3/vlmaps-hm3d:20260508-timmfix}
TEXT_IMG=${TEXT_IMG:-research3/vlmaps-text:20260508}
CHECKPOINT=${CHECKPOINT:-/models/vlmaps/lseg/checkpoints/demo_e200.ckpt}
SCENE_KEY=${SCENE_KEY:-y9hTuugGdiq}
SCENE_ID=${SCENE_ID:-hm3d_v0.2/val/00808-y9hTuugGdiq/y9hTuugGdiq.basis.glb}
SCENE_REL=${SCENE_REL:-val/00808-y9hTuugGdiq/y9hTuugGdiq.basis.glb}
QUERY=${QUERY:-chair}
MANIFEST=${MANIFEST:-${HYP}/manifests/h001_first_eval_replacement_v1.json}
FOLLOWUP_ROWS=${FOLLOWUP_ROWS:-${RUNS_ROOT}/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_evidence_v5_local_rival_route/external_candidate_followup_evidence_rows.jsonl}
FRAMES=${FRAMES:-256}
WIDTH=${WIDTH:-320}
HEIGHT=${HEIGHT:-240}
CAMERA_HEIGHT=${CAMERA_HEIGHT:-1.5}
HFOV=${HFOV:-90}
DEPTH_SAMPLE_RATE=${DEPTH_SAMPLE_RATE:-8}
SEED=${SEED:-20260521}
HOST_UID=${HOST_UID:-$(id -u)}
HOST_GID=${HOST_GID:-$(id -g)}
STATUS=${STATUS:-${OUT_ROOT}/job_status.json}

mkdir -p "${OUT_ROOT}" "${OUT_ROOT}/embeddings"

write_status() {
  local status="$1"
  local stage="$2"
  python3 - "${STATUS}" "${status}" "${stage}" "${OUT_ROOT}" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
payload = {
    "schema_version": "h001.dense_backend_recall_y9h_chair_job.v1",
    "status": sys.argv[2],
    "stage": sys.argv[3],
    "out_root": sys.argv[4],
    "updated_at": datetime.now(timezone.utc).isoformat(),
}
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
PY
}

json_ok_field() {
  local path="$1"
  python3 - "${path}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
if not path.exists() or path.stat().st_size == 0:
    raise SystemExit(1)
try:
    payload = json.loads(path.read_text(encoding="utf-8"))
except json.JSONDecodeError:
    raise SystemExit(1)
if payload.get("ok") is False:
    raise SystemExit(1)
PY
}

if [[ ! -s "${OUT_ROOT}/embeddings/${QUERY}.npy" ]]; then
  if [[ -s "${RUNS_ROOT}/h001_first_eval_artifacts_spatial_nms_k20_v1/embeddings/${QUERY}.npy" ]]; then
    cp "${RUNS_ROOT}/h001_first_eval_artifacts_spatial_nms_k20_v1/embeddings/${QUERY}.npy" "${OUT_ROOT}/embeddings/${QUERY}.npy"
  else
    write_status running text_embedding
    docker run --rm \
      --user "${HOST_UID}:${HOST_GID}" \
      -e HOME=/models \
      -e XDG_CACHE_HOME=/models/.cache \
      -v "${MODEL_ROOT}:/models" \
      -v "${OUT_ROOT}:/out" \
      "${TEXT_IMG}" \
      python /opt/research3/export_text_embeddings.py \
        --queries "${QUERY}" \
        --out-dir /out/embeddings \
        --device cpu
  fi
fi

write_status running export_hm3d_frames
if ! json_ok_field "${OUT_ROOT}/export/export_summary.json"; then
  docker run --rm --gpus all --ipc=host \
    --user "${HOST_UID}:${HOST_GID}" \
    -e HOME=/tmp \
    -e PYTHONPATH=/workspace/src \
    -v "${ROOT}:/workspace:ro" \
    -v "${DATA_ROOT}:/data:ro" \
    -v "${OUT_ROOT}:/out" \
    "${HABITAT_IMG}" \
    micromamba run -n base python -m h001_runtime.export_hm3d_vlmaps \
      --data-root /data \
      --scene-id "${SCENE_ID}" \
      --out-dir /out/export \
      --frames "${FRAMES}" \
      --width "${WIDTH}" \
      --height "${HEIGHT}" \
      --camera-height "${CAMERA_HEIGHT}" \
      --hfov "${HFOV}" \
      --seed "${SEED}" \
      --trajectory-mode random \
      --trajectory-id "${SCENE_KEY}_dense_backend_recall_v1"
fi

write_status running vlmaps_map
if ! json_ok_field "${OUT_ROOT}/verify_map.json"; then
  docker run --rm --gpus all --ipc=host \
    -e HOME=/models \
    -e XDG_CACHE_HOME=/models/.cache \
    -e TORCH_HOME=/models/torch \
    -e VLMAPS_CHECKPOINT="${CHECKPOINT}" \
    -v "${OUT_ROOT}/export:/work/scene" \
    -v "${MODEL_ROOT}:/models" \
    "${VLMAPS_IMG}" \
    python /opt/research3/run_vlmaps_map.py \
      --data-dir /work/scene \
      --camera-height "${CAMERA_HEIGHT}" \
      --depth-sample-rate "${DEPTH_SAMPLE_RATE}" \
      --checkpoint "${CHECKPOINT}" \
      --download-checkpoint

  docker run --rm --gpus all --ipc=host \
    -v "${OUT_ROOT}/export:/work/scene:ro" \
    -v "${MODEL_ROOT}:/models:ro" \
    "${VLMAPS_IMG}" \
    python /opt/research3/verify_vlmaps_map.py \
      --scene-dir /work/scene > "${OUT_ROOT}/verify_map.json.tmp"
  mv "${OUT_ROOT}/verify_map.json.tmp" "${OUT_ROOT}/verify_map.json"
fi

variant_export() {
  local name="$1"
  local mode="$2"
  local percentile="$3"
  local max_candidates="$4"
  local nms_distance="$5"
  local min_component_cells="$6"
  local variant_root="${OUT_ROOT}/variants/${name}"
  mkdir -p "${variant_root}/raw"
  if [[ ! -s "${variant_root}/raw/${QUERY}.jsonl" ]]; then
    docker run --rm --ipc=host \
      --user "${HOST_UID}:${HOST_GID}" \
      -e HOME=/tmp \
      -e PYTHONPATH=/workspace/src \
      -v "${ROOT}:/workspace:ro" \
      -v "${OUT_ROOT}:/out" \
      "${HABITAT_IMG}" \
      micromamba run -n base python -m h001_runtime.export_vlmaps_artifact \
        --scene-dir /out/export \
        --scene-id "${SCENE_ID}" \
        --query "${QUERY}" \
        --query-embedding "/out/embeddings/${QUERY}.npy" \
        --out "/out/variants/${name}/raw/${QUERY}.jsonl" \
        --grid /out/export/map/grid_lseg_1.npy \
        --weight /out/export/map/weight_lseg_1.npy \
        --obstacles /out/export/map/obstacles.npy \
        --top-percentile "${percentile}" \
        --selection-mode "${mode}" \
        --spatial-nms-min-distance-cells "${nms_distance}" \
        --min-component-cells "${min_component_cells}" \
        --max-candidates "${max_candidates}" \
        --use-obstacle-mask
  fi
  if [[ ! -s "${variant_root}/aligned.jsonl" ]]; then
    docker run --rm --ipc=host \
      --user "${HOST_UID}:${HOST_GID}" \
      -e HOME=/tmp \
      -e PYTHONPYCACHEPREFIX=/tmp/pycache \
      -e PYTHONPATH=/workspace/src \
      -v "${ROOT}:/workspace:ro" \
      -v "${DATA_ROOT}:/data:ro" \
      -v "${OUT_ROOT}:/out" \
      "${HABITAT_IMG}" \
      micromamba run -n base python -m h001_runtime.align_vlmaps_artifact \
        --artifact "/out/variants/${name}/raw/${QUERY}.jsonl" \
        --alignment /out/export/alignment.json \
        --out "/out/variants/${name}/aligned.jsonl" \
        --scene "/data/scene_datasets/hm3d/${SCENE_REL}"
  fi
}

write_status running dense_candidate_export
variant_export spatial_nms_p95_k100_d10 spatial_nms 95 100 10 1
variant_export spatial_nms_p90_k200_d5 spatial_nms 90 200 5 1
variant_export components_p90_min1_k200 components 90 200 20 1
variant_export components_p80_min1_k200 components 80 200 20 1

write_status running recall_probe
docker run --rm --ipc=host \
  --user "${HOST_UID}:${HOST_GID}" \
  -e HOME=/tmp \
  -e PYTHONDONTWRITEBYTECODE=1 \
  -e PYTHONPYCACHEPREFIX=/tmp/pycache \
  -e PYTHONPATH=/workspace/src \
  -v "${DATA_ROOT}:/data:ro" \
  -v "${RUNS_ROOT}:/runs:ro" \
  -v "${OUT_ROOT}:/out" \
  -v "${ROOT}:/workspace:ro" \
  "${HABITAT_IMG}" \
  micromamba run -n base python -m h001_runtime.probe_dense_backend_recall \
    --data-root /data \
    --manifest "/workspace/configs/h001/manifests/h001_first_eval_replacement_v1.json" \
    --manifest-split first_eval_replacement_v1 \
    --followup-evidence-rows "/runs/h001_first_eval_replacement_pair_objective_v4b_external_candidate_detector_heldout_v1/external_candidate_followup_evidence_v5_local_rival_route/external_candidate_followup_evidence_rows.jsonl" \
    --candidate-artifact "spatial_nms_p95_k100_d10=/out/variants/spatial_nms_p95_k100_d10/aligned.jsonl" \
    --candidate-artifact "spatial_nms_p90_k200_d5=/out/variants/spatial_nms_p90_k200_d5/aligned.jsonl" \
    --candidate-artifact "components_p90_min1_k200=/out/variants/components_p90_min1_k200/aligned.jsonl" \
    --candidate-artifact "components_p80_min1_k200=/out/variants/components_p80_min1_k200/aligned.jsonl" \
    --out-root /out/recall_probe

write_status completed completed
