#!/usr/bin/env bash
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
HYP=${HYP:-${ROOT}/experiments/h001_uncertainty-reobservation}
OUT_ROOT=${OUT_ROOT:-/tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_p97_k20_v1}
SOURCE_ROOT=${SOURCE_ROOT:-/tmp/research3-runs/h001_first_eval_artifacts_spatial_nms_k20_v1}
DATA_ROOT=${DATA_ROOT:-/tmp/research3-data}
HABITAT_IMG=${HABITAT_IMG:-research3/habitat-h001:20260508-calib-artifacts}
ARTIFACT_ID=${ARTIFACT_ID:-first_eval_spatial_nms_p97_k20_v1}
SCENE_SPECS_FILE=${SCENE_SPECS_FILE:-${HYP}/manifests/first_eval_scenes.txt}
TOP_PERCENTILE=${TOP_PERCENTILE:-97.0}
MAX_CANDIDATES=${MAX_CANDIDATES:-20}
SPATIAL_NMS_MIN_DISTANCE_CELLS=${SPATIAL_NMS_MIN_DISTANCE_CELLS:-20.0}
HOST_UID=${HOST_UID:-$(id -u)}
HOST_GID=${HOST_GID:-$(id -g)}

QUERIES=(bed chair plant sofa toilet tv_monitor)

if [[ ! -f "${SCENE_SPECS_FILE}" ]]; then
  echo "missing SCENE_SPECS_FILE: ${SCENE_SPECS_FILE}" >&2
  exit 1
fi
if [[ ! -d "${SOURCE_ROOT}" ]]; then
  echo "missing SOURCE_ROOT: ${SOURCE_ROOT}" >&2
  exit 1
fi
if [[ ! -s "${SOURCE_ROOT}/embeddings/manifest.json" ]]; then
  echo "missing source embeddings manifest: ${SOURCE_ROOT}/embeddings/manifest.json" >&2
  exit 1
fi

mapfile -t SCENES < <(grep -Ev '^[[:space:]]*(#|$)' "${SCENE_SPECS_FILE}")
if [[ "${#SCENES[@]}" -eq 0 ]]; then
  echo "SCENE_SPECS_FILE produced no scene specs: ${SCENE_SPECS_FILE}" >&2
  exit 1
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

write_status() {
  local status="$1"
  local path="${OUT_ROOT}/job_status.json"
  python - "$path" "$status" "$ARTIFACT_ID" "$SOURCE_ROOT" "$TOP_PERCENTILE" "$MAX_CANDIDATES" "$SPATIAL_NMS_MIN_DISTANCE_CELLS" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
status = sys.argv[2]
artifact_id = sys.argv[3]
source_root = sys.argv[4]
top_percentile = float(sys.argv[5])
max_candidates = int(sys.argv[6])
spatial_nms_min_distance_cells = float(sys.argv[7])
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
    "source_root": source_root,
    "top_percentile": top_percentile,
    "max_candidates": max_candidates,
    "spatial_nms_min_distance_cells": spatial_nms_min_distance_cells,
})
tmp = path.with_suffix(path.suffix + ".tmp")
tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
tmp.replace(path)
PY
}

trap 'write_status failed' ERR

cd "${ROOT}"
mkdir -p "${OUT_ROOT}/scenes"
write_status running

cat > "${OUT_ROOT}/run_contract.txt" <<EOF
artifact_id: ${ARTIFACT_ID}
working_directory: ${ROOT}
source_root: ${SOURCE_ROOT}
output_root: ${OUT_ROOT}
scene_specs_file: ${SCENE_SPECS_FILE}
top_percentile: ${TOP_PERCENTILE}
max_candidates: ${MAX_CANDIDATES}
selection_mode: spatial_nms
spatial_nms_min_distance_cells: ${SPATIAL_NMS_MIN_DISTANCE_CELLS}
expected_files:
  - ${OUT_ROOT}/job_status.json
  - ${OUT_ROOT}/coverage_check.json
  - ${OUT_ROOT}/all_scenes_aligned.jsonl
verification_command:
  cat ${OUT_ROOT}/job_status.json && cat ${OUT_ROOT}/coverage_check.json && wc -l ${OUT_ROOT}/all_scenes_aligned.jsonl
EOF

log_step "verify habitat image"
sg docker -c "docker image inspect ${HABITAT_IMG} >/dev/null"

for scene_spec in "${SCENES[@]}"; do
  IFS='|' read -r scene_key scene_id scene_rel seed <<<"${scene_spec}"
  source_export="${SOURCE_ROOT}/scenes/${scene_key}/export"
  source_verify="${SOURCE_ROOT}/scenes/${scene_key}/verify_map.json"
  scene_root="${OUT_ROOT}/scenes/${scene_key}"
  raw_dir="${scene_root}/raw"
  scene_raw="${scene_root}/raw.jsonl"
  scene_aligned="${scene_root}/aligned.jsonl"
  scene_summary="${scene_root}/artifact_summary.json"
  scene_container="/data/scene_datasets/hm3d/${scene_rel}"

  for required in \
    "${source_export}/alignment.json" \
    "${source_export}/map/grid_lseg_1.npy" \
    "${source_export}/map/weight_lseg_1.npy" \
    "${source_export}/map/obstacles.npy" \
    "${source_verify}"; do
    if [[ ! -s "${required}" ]]; then
      echo "missing source file for ${scene_key}: ${required}" >&2
      exit 1
    fi
  done

  mkdir -p "${raw_dir}"
  cp "${source_verify}" "${scene_root}/verify_map.json"
  printf '%s\n' "${source_export}" > "${scene_root}/source_export.txt"

  log_step "re-export spatial NMS candidates for ${scene_key}"
  for query in "${QUERIES[@]}"; do
    slug="$(query_slug "${query}")"
    raw_out="${raw_dir}/${query}.jsonl"
    if [[ ! -s "${raw_out}" ]]; then
      sg docker -c "docker run --rm --ipc=host \
        --user ${HOST_UID}:${HOST_GID} \
        -e HOME=/tmp \
        -e PYTHONPATH=/workspace/src \
        -v ${ROOT}:/workspace:ro \
        -v ${SOURCE_ROOT}:/source:ro \
        -v ${OUT_ROOT}:/out \
        ${HABITAT_IMG} \
        micromamba run -n base python -m h001_runtime.export_vlmaps_artifact \
          --scene-dir /source/scenes/${scene_key}/export \
          --scene-id ${scene_id} \
          --query ${query} \
          --query-embedding /source/embeddings/${slug}.npy \
          --out /out/scenes/${scene_key}/raw/${query}.jsonl \
          --grid /source/scenes/${scene_key}/export/map/grid_lseg_1.npy \
          --weight /source/scenes/${scene_key}/export/map/weight_lseg_1.npy \
          --obstacles /source/scenes/${scene_key}/export/map/obstacles.npy \
          --top-percentile ${TOP_PERCENTILE} \
          --selection-mode spatial_nms \
          --spatial-nms-min-distance-cells ${SPATIAL_NMS_MIN_DISTANCE_CELLS} \
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
    -e PYTHONPATH=/workspace/src \
    -v ${ROOT}:/workspace:ro \
    -v ${DATA_ROOT}:/data:ro \
    -v ${SOURCE_ROOT}:/source:ro \
    -v ${OUT_ROOT}:/out \
    ${HABITAT_IMG} \
    micromamba run -n base python -m h001_runtime.align_vlmaps_artifact \
      --artifact /out/scenes/${scene_key}/raw.jsonl \
      --alignment /source/scenes/${scene_key}/export/alignment.json \
      --out /out/scenes/${scene_key}/aligned.jsonl \
      --scene ${scene_container}"

  python - "${scene_aligned}" "${scene_summary}" "${TOP_PERCENTILE}" "${MAX_CANDIDATES}" "${SPATIAL_NMS_MIN_DISTANCE_CELLS}" <<'PY'
import json
import sys
from pathlib import Path

aligned = Path(sys.argv[1])
summary = Path(sys.argv[2])
top_percentile = float(sys.argv[3])
max_candidates = int(sys.argv[4])
spatial_nms_min_distance_cells = float(sys.argv[5])
rows = [json.loads(line) for line in aligned.read_text(encoding="utf-8").splitlines() if line.strip()]
candidate_count = sum(len(row.get("candidates") or [row]) for row in rows)
queries = sorted(str(row.get("query") or row.get("object_category")) for row in rows)
summary.write_text(json.dumps({
    "ok": len(rows) == 6 and candidate_count >= 6,
    "rows": len(rows),
    "candidate_count": candidate_count,
    "queries": queries,
    "aligned": str(aligned),
    "selection_mode": "spatial_nms",
    "top_percentile": top_percentile,
    "max_candidates": max_candidates,
    "spatial_nms_min_distance_cells": spatial_nms_min_distance_cells,
}, indent=2, sort_keys=True), encoding="utf-8")
if len(rows) != 6 or candidate_count < 6:
    raise SystemExit(1)
PY
done

log_step "combine all scene artifacts"
python - "${OUT_ROOT}" "${EXPECTED_QUERY_ROWS}" "${EXPECTED_SCENE_COUNT}" "${TOP_PERCENTILE}" "${MAX_CANDIDATES}" "${SPATIAL_NMS_MIN_DISTANCE_CELLS}" "${SOURCE_ROOT}" <<'PY'
import json
import math
import sys
from pathlib import Path

root = Path(sys.argv[1])
expected_query_rows = int(sys.argv[2])
expected_scene_count = int(sys.argv[3])
top_percentile = float(sys.argv[4])
max_candidates = int(sys.argv[5])
spatial_nms_min_distance_cells = float(sys.argv[6])
source_root = sys.argv[7]
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
    "source_root": source_root,
    "selection_mode": "spatial_nms",
    "top_percentile": top_percentile,
    "max_candidates": max_candidates,
    "spatial_nms_min_distance_cells": spatial_nms_min_distance_cells,
}
(root / "coverage_check.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
print(json.dumps(summary, indent=2, sort_keys=True))
if not summary["ok"]:
    raise SystemExit(1)
PY

write_status completed
log_step "completed first_eval spatial NMS re-export"
