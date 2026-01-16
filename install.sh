#!/usr/bin/env bash
set -euo pipefail

APP_NAME="copy2"
REPO_OWNER="MellowsLab"
REPO_NAME="Copy-2.0-Linux"
INSTALL_DIR="${HOME}/.local/share/copy2"
VENV_DIR="${INSTALL_DIR}/venv"
APP_DIR="${INSTALL_DIR}/app"
BIN_DIR="${HOME}/.local/bin"
LAUNCHER="${BIN_DIR}/copy2"

need_cmd() { command -v "$1" >/dev/null 2>&1; }

info() { printf '%s\n' "[INFO] $*"; }
warn() { printf '%s\n' "[WARN] $*"; }
err()  { printf '%s\n' "[ERROR] $*" >&2; }

install_system_deps() {
  # Tkinter is usually a system package on many distros.
  # Clipboard tools vary by X11/Wayland.
  if need_cmd apt-get; then
    info "Detected apt-get (Debian/Ubuntu). Installing system deps..."
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
  # Requires either git or curl+tar. Prefer git if available.
  if need_cmd git; then
    info "Fetching latest code via git..."
    tmpdir="$(mktemp -d)"
    git clone --depth 1 "https://github.com/${REPO_OWNER}/${REPO_NAME}.git" "${tmpdir}/${REPO_NAME}"
    cp -r "${tmpdir}/${REPO_NAME}/app/." "${APP_DIR}/"
    rm -rf "${tmpdir}"
  else
    info "Fetching latest code via curl..."
    tmpdir="$(mktemp -d)"
    curl -fsSL "https://github.com/${REPO_OWNER}/${REPO_NAME}/archive/refs/heads/main.tar.gz" -o "${tmpdir}/src.tar.gz"
    tar -xzf "${tmpdir}/src.tar.gz" -C "${tmpdir}"
    srcdir="${tmpdir}/${REPO_NAME}-main"
    cp -r "${srcdir}/app/." "${APP_DIR}/"
    rm -rf "${tmpdir}"
  fi

  if [[ ! -f "${APP_DIR}/copy2_gui.py" ]]; then
    err "Expected ${APP_DIR}/copy2_gui.py not found. Check your repo structure."
    exit 1
  fi
}

setup_venv() {
  info "Setting up Python virtual environment..."
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip

  # Python deps. Keep this minimal; add more only if the app needs them.
  # - pyperclip: clipboard access (fallback if xclip/wl-clipboard missing)
  # - pynput: optional hotkeys/input (X11 best effort; often limited on Wayland)
  "${VENV_DIR}/bin/pip" install --upgrade pyperclip pynput
}

write_launcher() {
  info "Creating launcher at ${LAUNCHER}..."
  cat > "${LAUNCHER}" <<EOF
#!/usr/bin/env bash
set -e
exec "${VENV_DIR}/bin/python" "${APP_DIR}/copy2_gui.py" "\$@"
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
