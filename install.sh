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

is_wayland() {
  [[ "${XDG_SESSION_TYPE:-}" == "wayland" ]] || [[ -n "${WAYLAND_DISPLAY:-}" ]]
}

is_immutable_os() {
  # Fedora Atomic / Silverblue / Kinoite / Bazzite and other OSTree systems.
  [[ -f /run/ostree-booted ]] && return 0
  # Some distros ship rpm-ostree only on immutable variants.
  need_cmd rpm-ostree && return 0
  return 1
}

install_system_deps() {
  if is_immutable_os; then
    warn "Immutable / OSTree-based distro detected. Skipping system package install."
    warn "You may need to install deps via rpm-ostree (requires reboot) OR use Distrobox/Toolbox."
    warn "See README for instructions."
    return 0
  fi

  if need_cmd apt-get; then
    info "Detected apt-get (Debian/Ubuntu/Kali). Installing system deps..."
    sudo apt-get update
    sudo apt-get install -y python3 python3-venv python3-tk xclip xsel wl-clipboard curl git || true
  elif need_cmd dnf; then
    info "Detected dnf (Fedora/RHEL). Installing system deps..."
    sudo dnf install -y python3 python3-tkinter xclip xsel wl-clipboard curl git || true
  elif need_cmd pacman; then
    info "Detected pacman (Arch). Installing system deps..."
    sudo pacman -Sy --noconfirm python tk xclip xsel wl-clipboard curl git || true
  elif need_cmd zypper; then
    info "Detected zypper (openSUSE). Installing system deps..."
    sudo zypper install -y python3 python3-tk xclip xsel wl-clipboard curl git || true
  else
    warn "No supported package manager detected. Skipping system deps install."
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

  # Required
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

  if ! need_cmd python3; then
    err "python3 not found. Install Python 3 and re-run."
    exit 1
  fi

  python3 -m venv "${VENV_DIR}" || {
    err "Failed to create venv. Your distro may split python3-venv (or blocks writes)."
    err "If you are on an immutable distro, use Distrobox/Toolbox or install python3-venv via your system method."
    exit 1
  }

  "${VENV_DIR}/bin/python" -m pip install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r "${APP_DIR}/requirements.txt"
}

write_launcher() {
  info "Creating launcher at ${LAUNCHER}..."
  cat > "${LAUNCHER}" <<LAUNCH
#!/usr/bin/env bash
"${VENV_DIR}/bin/python" "${APP_DIR}/run_copy2.py" "\$@"
LAUNCH
  chmod +x "${LAUNCHER}"
}

post_install_checks() {
  # Tkinter check (GUI)
  if ! "${VENV_DIR}/bin/python" -c "import tkinter" >/dev/null 2>&1; then
    warn "Tkinter (python3-tk / python3-tkinter) is missing. The GUI may not start."
    if is_immutable_os; then
      warn "On immutable distros, install it via rpm-ostree (reboot) OR run inside Distrobox/Toolbox."
    fi
  fi

  # Clipboard provider check
  if ! need_cmd wl-copy && ! need_cmd xclip && ! need_cmd xsel; then
    warn "No clipboard helper found (wl-clipboard/xclip/xsel). Clipboard access may fail."
    if is_wayland; then
      warn "Wayland session detected; wl-clipboard is recommended (wl-copy/wl-paste)."
    else
      warn "X11 session detected; xclip is recommended."
    fi
  fi

  # Wayland note for hotkeys
  if is_wayland; then
    warn "Wayland session detected. Many distros block global hotkeys and key injection for security."
    warn "Copy2 will still work, but global hotkeys may be disabled." 
  fi
}

main() {
  ensure_dirs
  install_system_deps
  fetch_app_files
  setup_venv
  write_launcher
  post_install_checks

  info "Install complete."
  info "Run the app with: ${APP_NAME}"
  info "If '${APP_NAME}' is not found, ensure ${BIN_DIR} is on your PATH (or restart your terminal)."
}

main "$@"
