\
#!/usr/bin/env bash
set -euo pipefail

APP_NAME="copy2"
REPO_OWNER="MellowsLab"
REPO_NAME="Copy-2.0-Linux"

INSTALL_DIR="${HOME}/.local/share/copy2"
APP_DIR="${INSTALL_DIR}/app"
VENV_DIR="${INSTALL_DIR}/venv"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/copy2"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

info() { printf '%s\n' "[INFO] $*"; }
warn() { printf '%s\n' "[WARN] $*"; }
err()  { printf '%s\n' "[ERROR] $*" >&2; }

install_system_deps() {
  if need_cmd apt-get; then
    info "Detected apt-get (Debian/Ubuntu/Kali). Installing system deps..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-tk xclip xsel wl-clipboard curl git
  elif need_cmd dnf; then
    info "Detected dnf (Fedora/RHEL). Installing system deps..."
    sudo dnf install -y python3 python3-tkinter xclip xsel wl-clipboard curl git
  elif need_cmd pacman; then
    info "Detected pacman (Arch). Installing system deps..."
    sudo pacman -Sy --noconfirm python tk xclip xsel wl-clipboard curl git
  elif need_cmd zypper; then
    info "Detected zypper (openSUSE). Installing system deps..."
    sudo zypper install -y python3 python3-tk xclip xsel wl-clipboard curl git
  else
    warn "No supported package manager detected. Skipping system deps install."
    warn "You may need: python3, python3-venv, Tkinter, plus xclip/xsel or wl-clipboard."
  fi
}

ensure_dirs() {
  mkdir -p "${INSTALL_DIR}" "${APP_DIR}" "${BIN_DIR}"
}

fetch_app_files() {
  # Repo layout is ROOT-BASED (no app/ folder in repo).
  if need_cmd git; then
    info "Fetching latest code via git..."
    tmpdir="$(mktemp -d)"
    git clone --depth 1 "https://github.com/${REPO_OWNER}/${REPO_NAME}.git" "${tmpdir}/${REPO_NAME}"
    src="${tmpdir}/${REPO_NAME}"
  else
    info "Fetching latest code via curl..."
    tmpdir="$(mktemp -d)"
    curl -fsSL "https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/main.tar.gz" -o "${tmpdir}/src.tar.gz"
    tar -xzf "${tmpdir}/src.tar.gz" -C "${tmpdir}"
    src="${tmpdir}/${REPO_NAME}-main"
  fi

  # Required files
  cp -f "${src}/run_copy2.py" "${APP_DIR}/"
  cp -f "${src}/requirements.txt" "${APP_DIR}/"

  # Optional support modules
  for f in app.py clipboard.py hotkeys.py storage.py __init__.py; do
    if [[ -f "${src}/${f}" ]]; then
      cp -f "${src}/${f}" "${APP_DIR}/"
    fi
  done

  # Optional assets
  if [[ -d "${src}/assets" ]]; then
    rm -rf "${APP_DIR}/assets"
    cp -r "${src}/assets" "${APP_DIR}/assets"
  fi

  rm -rf "${tmpdir}"

  if [[ ! -f "${APP_DIR}/run_copy2.py" ]]; then
    err "Expected ${APP_DIR}/run_copy2.py not found. Check repo structure."
    exit 1
  fi
}

setup_venv() {
  info "Setting up Python virtual environment..."
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
}

write_launcher() {
  info "Creating launcher at ${LAUNCHER}..."
  cat > "${LAUNCHER}" <<EOF
#!/usr/bin/env bash
set -e
exec "${VENV_DIR}/bin/python" "${APP_DIR}/run_copy2.py" "\$@"
EOF
  chmod +x "${LAUNCHER}"
}

post_install() {
  info "Install complete."
  if ! echo "${PATH}" | grep -q "${HOME}/.local/bin"; then
    warn "~/.local/bin is not on your PATH."
    warn "Add this to your shell profile (e.g., ~/.bashrc or ~/.zshrc):"
    printf '%s\n' '  export PATH="$HOME/.local/bin:$PATH"'
  fi
  info "Run the app with: copy2"
}

main() {
  install_system_deps
  ensure_dirs
  fetch_app_files
  setup_venv
  write_launcher
  post_install
}

main "$@"
