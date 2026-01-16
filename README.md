# Copy 2.0 (Linux)

Copy 2.0 is a lightweight clipboard history manager for Linux with a simple, fast GUI.  
It tracks your clipboard, lets you browse/search previous copies, pin favorites, and quickly re-copy or combine items.

## Quick start (recommended)

### One-line install
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/MellowsLab/Copy-2.0-Linux/main/install.sh)"
```

After install, run:
```bash
copy2
```

---

## Wayland / Immutable distros (Bazzite, Silverblue, Kinoite, SteamOS)

### Wayland notes
- Clipboard access on Wayland should work when `wl-clipboard` is available.
- **Global hotkeys may be restricted on Wayland** depending on compositor/security policy. The app still works via the GUI and in-app shortcuts.

### Immutable (OSTree) distros
Immutable systems often block traditional package installs on the host OS.
If the installer detects an immutable system, it will print guidance rather than failing.

Recommended options:
1) **Distrobox/Toolbox** (fastest, no reboot)
2) **rpm-ostree install** (host install, requires reboot)

#### Distrobox example (Fedora)
```bash
distrobox create -n copy2 -i fedora:latest
distrobox enter copy2

sudo dnf -y install git python3 python3-pip python3-tkinter wl-clipboard xclip xsel
git clone https://github.com/MellowsLab/Copy-2.0-Linux.git
cd Copy-2.0-Linux

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python3 run_copy2.py
```

---

## Dependencies

Copy 2.0 requires:
- Python 3
- Tkinter (`python3-tk` on Debian/Ubuntu/Kali; `python3-tkinter` on Fedora)
- Clipboard helpers (recommended):
  - Wayland: `wl-clipboard`
  - X11: `xclip` or `xsel`

The installer attempts to install what it can on mutable distros.

---

## Usage

### Run
```bash
copy2
```

### In-app shortcuts (always available)
- `Ctrl+F` focus search
- `Enter` search
- `Ctrl+C` copy selected
- `Delete` delete selected
- `Ctrl+E` export
- `Ctrl+I` import

*(Global hotkeys may not work on Wayland-only systems.)*

---

## Where data is stored

Copy 2.0 stores per-user data (history/config/favorites) under your user data directory (typically under `~/.local/share/copy2/`).

---

## Uninstall

If you installed via the installer script:
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/MellowsLab/Copy-2.0-Linux/main/uninstall.sh)"
```

Manual cleanup (user data):
- Remove the app data folder under `~/.local/share/` (look for `copy2`)
- Remove launcher from `~/.local/bin/` if present

---

## Troubleshooting

### “Nothing happens” / GUI won’t open
Check Tkinter:
```bash
python3 -c "import tkinter; print('tk ok')"
```

If that fails, install Tkinter:
- Debian/Ubuntu/Kali:
  ```bash
  sudo apt-get update && sudo apt-get install -y python3-tk
  ```
- Fedora:
  ```bash
  sudo dnf install -y python3-tkinter
  ```

### Clipboard doesn’t capture on Wayland
Install `wl-clipboard`:
- Debian/Ubuntu/Kali:
  ```bash
  sudo apt-get install -y wl-clipboard
  ```
- Fedora:
  ```bash
  sudo dnf install -y wl-clipboard
  ```

Confirm session type:
```bash
echo $XDG_SESSION_TYPE
```

### Clipboard doesn’t capture on X11
Install `xclip` or `xsel`:
```bash
sudo apt-get install -y xclip xsel
```

### Immutable distro install fails
That is expected on OSTree systems. Use the **Distrobox/Toolbox** instructions above, or install dependencies via your distro’s immutable workflow.

---

## License
MIT
