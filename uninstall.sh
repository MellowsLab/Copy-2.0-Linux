\
#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/copy2"
LAUNCHER="${HOME}/.local/bin/copy2"

echo "[INFO] Removing ${INSTALL_DIR} ..."
rm -rf "${INSTALL_DIR}"

echo "[INFO] Removing ${LAUNCHER} ..."
rm -f "${LAUNCHER}"

echo "[INFO] Uninstall complete."
