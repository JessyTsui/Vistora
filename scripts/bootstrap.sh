#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT_DIR}"

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is required. Install: https://docs.astral.sh/uv/getting-started/installation/"
  exit 1
fi

uv sync --extra dev --frozen

if [[ "${1:-}" == "--with-models" ]]; then
  uv run vistora setup-models --manifest models/manifest.json --output-dir models/assets
fi

echo "Bootstrap complete. Run commands with: uv run <command>"
