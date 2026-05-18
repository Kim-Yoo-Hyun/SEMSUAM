#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/hypothesis/CAND-01/H001_uncertainty-reobservation}
RUNTIME=${RUNTIME:-${HYP}/runtime}
OUT_ROOT=${OUT_ROOT:-/tmp/research3-runs/h001_calibration_artifacts_v1}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
MODEL_ROOT=${MODEL_ROOT:-/tmp/research3-models}
ARTIFACT_ID=${ARTIFACT_ID:-random128_v1}
TRAJECTORY_SUFFIX=${TRAJECTORY_SUFFIX:-calib_${ARTIFACT_ID}}

HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
VLMAPS_IMG=${VLMAPS_IMG:-research3/vlmaps-hm3d:20260508-timmfix}
TEXT_IMG=${TEXT_IMG:-research3/vlmaps-text:20260508}

CHECKPOINT=${CHECKPOINT:-/models/vlmaps/lseg/checkpoints/demo_e200.ckpt}
FRAMES=${FRAMES:-128}
WIDTH=${WIDTH:-160}
HEIGHT=${HEIGHT:-120}
CAMERA_HEIGHT=${CAMERA_HEIGHT:-1.5}
HFOV=${HFOV:-90}
TOP_PERCENTILE=${TOP_PERCENTILE:-98.0}
MAX_CANDIDATES=${MAX_CANDIDATES:-5}
CANDIDATE_SELECTION_MODE=${CANDIDATE_SELECTION_MODE:-components}
SPATIAL_NMS_MIN_DISTANCE_CELLS=${SPATIAL_NMS_MIN_DISTANCE_CELLS:-20.0}
MIN_COMPONENT_CELLS=${MIN_COMPONENT_CELLS:-1}
DEPTH_SAMPLE_RATE=${DEPTH_SAMPLE_RATE:-500}
HOST_UID=${HOST_UID:-$(id -u)}
HOST_GID=${HOST_GID:-$(id -g)}

QUERIES=(bed chair plant sofa toilet tv_monitor)

SCENES=(
  "HkseAnWCgqk|hm3d_v0.2/train/00006-HkseAnWCgqk/HkseAnWCgqk.basis.glb|train/00006-HkseAnWCgqk/HkseAnWCgqk.basis.glb|2101"
  "vLpv2VX547B|hm3d_v0.2/train/00009-vLpv2VX547B/vLpv2VX547B.basis.glb|train/00009-vLpv2VX547B/vLpv2VX547B.basis.glb|2102"
  "qk9eeNeR4vw|hm3d_v0.2/train/00016-qk9eeNeR4vw/qk9eeNeR4vw.basis.glb|train/00016-qk9eeNeR4vw/qk9eeNeR4vw.basis.glb|2103"
  "oEPjPNSPmzL|hm3d_v0.2/train/00017-oEPjPNSPmzL/oEPjPNSPmzL.basis.glb|train/00017-oEPjPNSPmzL/oEPjPNSPmzL.basis.glb|2104"
  "XYyR54sxe6b|hm3d_v0.2/train/00020-XYyR54sxe6b/XYyR54sxe6b.basis.glb|train/00020-XYyR54sxe6b/XYyR54sxe6b.basis.glb|2105"
)

if [[ -n "${SCENE_SPECS_FILE:-}" ]]; then
  if [[ ! -f "${SCENE_SPECS_FILE}" ]]; then
    echo "missing SCENE_SPECS_FILE: ${SCENE_SPECS_FILE}" >&2
    exit 1
  fi
  mapfile -t SCENES < <(grep -Ev '^[[:space:]]*(#|$)' "${SCENE_SPECS_FILE}")
  if [[ "${#SCENES[@]}" -eq 0 ]]; then
    echo "SCENE_SPECS_FILE produced no scene specs: ${SCENE_SPECS_FILE}" >&2
    exit 1
  fi
fi

EXPECTED_SCENE_COUNT=${EXPECTED_SCENE_COUNT:-${#SCENES[@]}}
EXPECTED_QUERY_ROWS=${EXPECTED_QUERY_ROWS:-$((EXPECTED_SCENE_COUNT * ${#QUERIES[@]}))}

log_step() {
  printf '\n[%s] %s\n' "$(date -Is)" "$*"
}

query_slug() {
  python - "$1" <<'PY'
import re
import sys
text = sys.argv[1]
value = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
print(value or "query")
PY
}

json_ok_field() {
  python - "$1" <<'PY'
import json
import sys
from pathlib import Path
path = Path(sys.argv[1])
if not path.exists():
    raise SystemExit(1)
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if data.get("ok") is True else 1)
PY
}

write_status() {
  local status="$1"
  local path="${OUT_ROOT}/job_status.json"
  python - "$path" "$status" "$ARTIFACT_ID" "$FRAMES" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
status = sys.argv[2]
artifact_id = sys.argv[3]
frames = int(sys.argv[4])
path.parent.mkdir(parents=True, exist_ok=True)
data = {}
if path.exists() and path.stat().st_size > 0:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
data.update({
    "status": status,
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "output_root": str(path.parent),
    "artifact_id": artifact_id,
    "frames": frames,
})
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
tmp.replace(path)
PY
}

trap 'write_status failed' ERR

cd "${ROOT}"
mkdir -p "${OUT_ROOT}/embeddings" "${OUT_ROOT}/scenes" "${MODEL_ROOT}"
write_status running

log_step "check/build habitat calibration image"
if ! sg docker -c "docker image inspect ${HABITAT_IMG} >/dev/null 2>&1"; then
  sg docker -c "docker build -f ${RUNTIME}/Dockerfile.habitat-h001 -t ${HABITAT_IMG} ${RUNTIME}"
fi

log_step "verify required images"
sg docker -c "docker image inspect ${HABITAT_IMG} ${VLMAPS_IMG} ${TEXT_IMG} >/dev/null"

log_step "export CLIP text embeddings"
if [[ ! -s "${OUT_ROOT}/embeddings/manifest.json" ]]; then
  sg docker -c "docker run --rm \
    --user ${HOST_UID}:${HOST_GID} \
    -e HOME=/models \
    -e XDG_CACHE_HOME=/models/.cache \
    -v ${MODEL_ROOT}:/models \
    -v ${OUT_ROOT}:/out \
    ${TEXT_IMG} \
    python /opt/research3/export_text_embeddings.py \
      --queries ${QUERIES[*]} \
      --out-dir /out/embeddings \
      --device cpu"
fi

for scene_spec in "${SCENES[@]}"; do
  IFS='|' read -r scene_key scene_id scene_rel seed <<<"${scene_spec}"
  scene_root="${OUT_ROOT}/scenes/${scene_key}"
  export_dir="${scene_root}/export"
  raw_dir="${scene_root}/raw"
  scene_raw="${scene_root}/raw.jsonl"
  scene_aligned="${scene_root}/aligned.jsonl"
  scene_summary="${scene_root}/artifact_summary.json"
  scene_container="/data/scene_datasets/hm3d/${scene_rel}"
  trajectory_id="${scene_key}_${TRAJECTORY_SUFFIX}"

  mkdir -p "${export_dir}" "${raw_dir}"

  log_step "export RGB-D/pose for ${scene_key}"
  if ! json_ok_field "${export_dir}/export_summary.json"; then
    sg docker -c "docker run --rm --gpus all --ipc=host \
      --user ${HOST_UID}:${HOST_GID} \
      -e HOME=/tmp \
      -v ${DATA_ROOT}:/data:ro \
      -v ${OUT_ROOT}:/runs \
      ${HABITAT_IMG} \
      micromamba run -n base python -m h001_runtime.export_hm3d_vlmaps \
        --data-root /data \
        --scene-id ${scene_id} \
        --out-dir /runs/scenes/${scene_key}/export \
        --frames ${FRAMES} \
        --width ${WIDTH} \
        --height ${HEIGHT} \
        --camera-height ${CAMERA_HEIGHT} \
        --hfov ${HFOV} \
        --seed ${seed} \
        --trajectory-mode random \
        --trajectory-id ${trajectory_id}"
  fi

  log_step "generate VLMaps map for ${scene_key}"
  if ! json_ok_field "${scene_root}/verify_map.json"; then
    sg docker -c "docker run --rm --gpus all --ipc=host \
      -e HOME=/models \
      -e XDG_CACHE_HOME=/models/.cache \
      -e TORCH_HOME=/models/torch \
      -e VLMAPS_CHECKPOINT=${CHECKPOINT} \
      -v ${export_dir}:/work/scene \
      -v ${MODEL_ROOT}:/models \
      ${VLMAPS_IMG} \
      python /opt/research3/run_vlmaps_map.py \
        --data-dir /work/scene \
        --camera-height ${CAMERA_HEIGHT} \
        --depth-sample-rate ${DEPTH_SAMPLE_RATE} \
        --checkpoint ${CHECKPOINT} \
        --download-checkpoint"

    sg docker -c "docker run --rm --gpus all --ipc=host \
      -v ${export_dir}:/work/scene:ro \
      -v ${MODEL_ROOT}:/models:ro \
      ${VLMAPS_IMG} \
      python /opt/research3/verify_vlmaps_map.py \
        --scene-dir /work/scene" > "${scene_root}/verify_map.json.tmp"
    mv "${scene_root}/verify_map.json.tmp" "${scene_root}/verify_map.json"
  fi

  log_step "export VLMaps candidates for ${scene_key}"
  for query in "${QUERIES[@]}"; do
    slug="$(query_slug "${query}")"
    raw_out="${raw_dir}/${query}.jsonl"
    if [[ ! -s "${raw_out}" ]]; then
      sg docker -c "docker run --rm --ipc=host \
        --user ${HOST_UID}:${HOST_GID} \
        -e HOME=/tmp \
        -e PYTHONPATH=/workspace/hypothesis/CAND-01/H001_uncertainty-reobservation/runtime \
        -v ${ROOT}:/workspace:ro \
        -v ${OUT_ROOT}:/out \
        ${HABITAT_IMG} \
        micromamba run -n base python -m h001_runtime.export_vlmaps_artifact \
          --scene-dir /out/scenes/${scene_key}/export \
          --scene-id ${scene_id} \
          --query ${query} \
          --query-embedding /out/embeddings/${slug}.npy \
          --out /out/scenes/${scene_key}/raw/${query}.jsonl \
          --grid /out/scenes/${scene_key}/export/map/grid_lseg_1.npy \
          --weight /out/scenes/${scene_key}/export/map/weight_lseg_1.npy \
          --obstacles /out/scenes/${scene_key}/export/map/obstacles.npy \
          --top-percentile ${TOP_PERCENTILE} \
          --selection-mode ${CANDIDATE_SELECTION_MODE} \
          --spatial-nms-min-distance-cells ${SPATIAL_NMS_MIN_DISTANCE_CELLS} \
          --min-component-cells ${MIN_COMPONENT_CELLS} \
          --max-candidates ${MAX_CANDIDATES} \
          --use-obstacle-mask"
    fi
  done

  log_step "combine and align candidates for ${scene_key}"
  python - "${raw_dir}" "${scene_raw}" <<'PY'
from pathlib import Path
import sys

raw_dir = Path(sys.argv[1])
out = Path(sys.argv[2])
with out.open("w", encoding="utf-8") as handle:
    for path in sorted(raw_dir.glob("*.jsonl")):
        text = path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        handle.write(text)
PY

  sg docker -c "docker run --rm --ipc=host \
    --user ${HOST_UID}:${HOST_GID} \
    -e HOME=/tmp \
    -v ${DATA_ROOT}:/data:ro \
    -v ${OUT_ROOT}:/out \
    ${HABITAT_IMG} \
    micromamba run -n base python -m h001_runtime.align_vlmaps_artifact \
      --artifact /out/scenes/${scene_key}/raw.jsonl \
      --alignment /out/scenes/${scene_key}/export/alignment.json \
      --out /out/scenes/${scene_key}/aligned.jsonl \
      --scene ${scene_container}"

  python - "${scene_aligned}" "${scene_summary}" <<'PY'
import json
import sys
from pathlib import Path

aligned = Path(sys.argv[1])
summary = Path(sys.argv[2])
rows = [json.loads(line) for line in aligned.read_text(encoding="utf-8").splitlines() if line.strip()]
candidate_count = sum(len(row.get("candidates") or [row]) for row in rows)
queries = sorted(str(row.get("query") or row.get("object_category")) for row in rows)
summary.write_text(json.dumps({
    "ok": len(rows) == 6 and candidate_count >= 6,
    "rows": len(rows),
    "candidate_count": candidate_count,
    "queries": queries,
    "aligned": str(aligned),
}, indent=2, sort_keys=True), encoding="utf-8")
if len(rows) != 6 or candidate_count < 6:
    raise SystemExit(1)
PY
done

log_step "combine all scene artifacts"
python - "${OUT_ROOT}" "${EXPECTED_QUERY_ROWS}" "${EXPECTED_SCENE_COUNT}" <<'PY'
import json
import math
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected_query_rows = int(sys.argv[2])
expected_scene_count = int(sys.argv[3])
aligned_out = root / "all_scenes_aligned.jsonl"
raw_out = root / "all_scenes_raw.jsonl"

aligned_paths = sorted((root / "scenes").glob("*/aligned.jsonl"))
raw_paths = sorted((root / "scenes").glob("*/raw.jsonl"))

with aligned_out.open("w", encoding="utf-8") as handle:
    for path in aligned_paths:
        text = path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        handle.write(text)

with raw_out.open("w", encoding="utf-8") as handle:
    for path in raw_paths:
        text = path.read_text(encoding="utf-8")
        if text and not text.endswith("\n"):
            text += "\n"
        handle.write(text)

rows = [json.loads(line) for line in aligned_out.read_text(encoding="utf-8").splitlines() if line.strip()]
candidate_count = 0
finite_positions = 0
for row in rows:
    candidates = row.get("candidates") or [row]
    candidate_count += len(candidates)
    for cand in candidates:
        values = list(cand.get("position") or []) + list(cand.get("visit_position") or [])
        if values and all(isinstance(v, (int, float)) and math.isfinite(float(v)) for v in values):
            finite_positions += 1

scenes = sorted({Path(str(row.get("scene_id") or row.get("scene"))).name.replace(".basis.glb", "") for row in rows})
queries = sorted({str(row.get("query") or row.get("object_category")) for row in rows})
summary = {
    "ok": len(rows) == expected_query_rows and candidate_count >= expected_query_rows and len(scenes) == expected_scene_count and queries == ["bed", "chair", "plant", "sofa", "toilet", "tv_monitor"],
    "expected_query_rows": expected_query_rows,
    "expected_scene_count": expected_scene_count,
    "rows": len(rows),
    "candidate_count": candidate_count,
    "finite_position_candidates": finite_positions,
    "scenes": scenes,
    "queries": queries,
    "aligned_artifact": str(aligned_out),
    "raw_artifact": str(raw_out),
}
(root / "coverage_check.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
if not summary["ok"]:
    raise SystemExit(1)
PY

write_status completed
log_step "completed calibration artifact generation"
