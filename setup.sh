#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODELS_DIR="$ROOT/models"
mkdir -p "$MODELS_DIR"

TARGET_NAME="Muse-Glimmer-30B-KQuant-Dynamic-Q4_K_XL.gguf"
DRAFT_NAME="Muse-Glimmer-30B-DFlash2-Q8_0.gguf"

TARGET_URL="https://huggingface.co/meta-models/Muse-Glimmer-30B-GGUF/resolve/main/${TARGET_NAME}"
DRAFT_URL="https://huggingface.co/incoai/Muse-Glimmer-30B-DFlash2-GGUF/resolve/main/${DRAFT_NAME}"

download() {
  local url=$1
  local dest=$2
  if [[ -f "$dest" && -s "$dest" ]]; then
    echo "✓ $(basename "$dest") already exists ($(du -h "$dest" | cut -f1)), skipping"
    return
  fi
  echo "Downloading $(basename "$dest") to $dest ..."
  echo "Source: $url"
  curl -L --progress-bar -C - -o "$dest" "$url"
  echo "✓ $(basename "$dest") downloaded"
}

echo "Muse Glimmer local setup"
echo "Models directory: $MODELS_DIR"
echo

download "$TARGET_URL" "$MODELS_DIR/$TARGET_NAME"
download "$DRAFT_URL" "$MODELS_DIR/$DRAFT_NAME"

echo
echo "Done. Models are ready in $MODELS_DIR"
echo "Start server with: bin/serve.sh"
