#!/usr/bin/env zsh
set -euo pipefail

ROOT=${ROOT:-/home/yoohyun/research3}
IMAGE=${IMAGE:-research3/openvocab-perception:20260513-owlvit}
MODEL_ID=${MODEL_ID:-google/owlvit-base-patch32}
MODEL_BASE=${MODEL_BASE:-$ROOT/local_dataset/models}
MODEL_DIR=${MODEL_DIR:-$MODEL_BASE/openvocab/owlvit/google_owlvit-base-patch32}
OUT=${OUT:-$ROOT/local_dataset/runs/openvocab_perception_owlvit_setup}
LOG=${LOG:-$ROOT/archive/logs/root/openvocab-perception-owlvit-setup-$(date +%Y%m%d-%H%M%S).log}
STATUS="$OUT/job_status.json"

mkdir -p "$ROOT/archive/logs/root" "$OUT" "$MODEL_DIR"
exec > >(tee -a "$LOG") 2>&1

write_status() {
  local job_state="$1"
  local stage="$2"
  local now
  now="$(date -Is)"
  printf '{"status":"%s","stage":"%s","updated_at":"%s","image":"%s","model_id":"%s","model_dir":"%s","output_root":"%s","log":"%s"}\n' \
    "$job_state" "$stage" "$now" "$IMAGE" "$MODEL_ID" "$MODEL_DIR" "$OUT" "$LOG" > "$STATUS"
}

on_error() {
  local code="$?"
  local now
  now="$(date -Is)"
  printf '{"status":"failed","stage":"%s","failed_at":"%s","exit_code":%s,"image":"%s","model_id":"%s","model_dir":"%s","output_root":"%s","log":"%s"}\n' \
    "${CURRENT_STAGE:-unknown}" "$now" "$code" "$IMAGE" "$MODEL_ID" "$MODEL_DIR" "$OUT" "$LOG" > "$STATUS"
  exit "$code"
}
trap on_error ERR

cd "$ROOT"
echo "started_at=$(date -Is)"
echo "image=$IMAGE"
echo "model_id=$MODEL_ID"
echo "model_dir=$MODEL_DIR"
echo "output_root=$OUT"
echo "log=$LOG"

CURRENT_STAGE=build_image
write_status running "$CURRENT_STAGE"
sg docker -c "docker build \
  -f configs/docker/Dockerfile.openvocab-perception \
  -t $IMAGE \
  ."

CURRENT_STAGE=import_verification
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/models \
  -e HF_HOME=/models/.cache/huggingface \
  -e XDG_CACHE_HOME=/models/.cache \
  -v $MODEL_BASE:/models \
  $IMAGE \
  python -c 'import importlib.util, torch, transformers; mods=[\"torch\",\"torchvision\",\"transformers\",\"cv2\",\"PIL\",\"numpy\"]; [print(\"{}: {}\".format(m, \"available\" if importlib.util.find_spec(m) else \"missing\")) for m in mods]; print(\"torch_version:\", torch.__version__); print(\"transformers_version:\", transformers.__version__); print(\"cuda_available:\", torch.cuda.is_available())'"

CURRENT_STAGE=download_owlvit
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/models \
  -e HF_HOME=/models/.cache/huggingface \
  -e XDG_CACHE_HOME=/models/.cache \
  -v $MODEL_BASE:/models \
  $IMAGE \
  python -c 'from huggingface_hub import snapshot_download; snapshot_download(repo_id=\"$MODEL_ID\", local_dir=\"/models/openvocab/owlvit/google_owlvit-base-patch32\", resume_download=True)'"

CURRENT_STAGE=model_verification
write_status running "$CURRENT_STAGE"
sg docker -c "docker run --rm --ipc=host \
  --user $(id -u):$(id -g) \
  -e HOME=/models \
  -e HF_HOME=/models/.cache/huggingface \
  -e XDG_CACHE_HOME=/models/.cache \
  -e TRANSFORMERS_OFFLINE=1 \
  -e HF_HUB_OFFLINE=1 \
  -v $MODEL_BASE:/models \
  $IMAGE \
  python -c 'from pathlib import Path; from transformers import OwlViTForObjectDetection, OwlViTProcessor; p=Path(\"/models/openvocab/owlvit/google_owlvit-base-patch32\"); assert p.exists(), p; processor=OwlViTProcessor.from_pretrained(str(p), local_files_only=True); model=OwlViTForObjectDetection.from_pretrained(str(p), local_files_only=True); print({\"model_dir\": str(p), \"files\": len(list(p.rglob(\"*\"))), \"model_type\": model.config.model_type, \"processor\": processor.__class__.__name__})'"

CURRENT_STAGE=verified
write_status completed "$CURRENT_STAGE"
echo "completed_at=$(date -Is)"
