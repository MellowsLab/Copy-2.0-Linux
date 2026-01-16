#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

rm -f "$HOME/.local/bin/copy2" || true
rm -f "$HOME/.local/share/applications/copy2.desktop" || true
rm -rf "$ROOT_DIR/.venv" || true

echo "Uninstalled launcher + venv from: $ROOT_DIR"
echo "Note: your data remains in ~/.config/Copy2 and ~/.local/share/Copy2 (delete manually if desired)."
