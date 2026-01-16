# Copy 2.0 (Linux)

This is a Linux-first rebuild of your original clipboard tool in `Copy 2.0.py`.

## Key changes

- Removed Windows-only behavior.
- Added a standalone GUI (Tkinter):
  - Clipboard history + preview
  - Favorites tab
  - Search/filter
  - Reverse-lines copy
  - Combine multiple history items
  - Import/export history
- Changed capture method:
  - Instead of relying on a global "Ctrl+C" hook, it polls the clipboard on a timer.
  - This is more reliable across Linux desktops.
- Optional global hotkeys (best effort):
  - Uses `pynput`.
  - Works on many X11 sessions.
  - Often blocked on Wayland (desktop security restriction).

## Install (recommended)

1. Extract this folder.
2. Run:

## One-command install

```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/MellowsLab/Copy-2.0-Linux/main/install.sh)"

```

3. Launch:

```bash
copy2
```

This installer:
- Installs system packages (Tkinter + clipboard tools) via your distro package manager when possible.
- Creates a local Python venv in this folder and installs pip dependencies.
- Adds a launcher in `~/.local/bin/copy2`.
- Adds a desktop entry (so you can search for "Copy 2.0" in your launcher).

## Uninstall

```bash
./scripts/uninstall.sh
```

Your data remains in:
- `~/.config/Copy2/` (config)
- `~/.local/share/Copy2/` (history)

Delete those folders manually if you want a full wipe.

## Notes about "all Linux flavors"

Linux does not have a single universal clipboard/hotkey API.

- Clipboard history (capture/copy) should work on most desktops once you have:
  - X11: `xclip` (recommended) or `xsel`
  - Wayland: `wl-clipboard`
- Global hotkeys and synthetic paste may not work on Wayland.
  - The app will still copy to clipboard; you can paste manually.

## Running from source (no installer)

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
python run_copy2.py
```
