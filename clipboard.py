from __future__ import annotations

import subprocess
from typing import Optional, Tuple

import pyperclip


def _cmd_exists(cmd: str) -> bool:
    from shutil import which

    return which(cmd) is not None


def _run_capture(args: list[str]) -> Tuple[Optional[str], Optional[str]]:
    try:
        p = subprocess.run(args, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.stdout, None
    except FileNotFoundError:
        return None, None
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e)).strip()
        return None, msg or "Clipboard helper failed"
    except Exception as e:
        return None, f"Clipboard helper error: {e}"


def _run_input(args: list[str], text: str) -> Optional[str]:
    try:
        subprocess.run(args, check=True, text=True, input=text, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return None
    except FileNotFoundError:
        return None
    except subprocess.CalledProcessError as e:
        msg = (e.stderr or e.stdout or str(e)).strip()
        return msg or "Clipboard helper failed"
    except Exception as e:
        return f"Clipboard helper error: {e}"


def get_clipboard_text() -> Tuple[Optional[str], Optional[str]]:
    """Return (text, error_message).

    Strategy:
    1) pyperclip (preferred when configured)
    2) wl-clipboard (Wayland)
    3) xclip / xsel (X11)
    """
    # 1) pyperclip
    try:
        txt = pyperclip.paste()
        if isinstance(txt, str):
            return txt, None
    except pyperclip.PyperclipException:
        pass
    except Exception as e:
        # Keep going to fallbacks
        last_err = f"Clipboard error: {e}"
    else:
        last_err = None

    # 2) Wayland helper
    if _cmd_exists("wl-paste"):
        out, e = _run_capture(["wl-paste", "-n"])
        if out is not None:
            return out, None
        if e:
            last_err = e

    # 3) X11 helpers
    if _cmd_exists("xclip"):
        out, e = _run_capture(["xclip", "-selection", "clipboard", "-o"])
        if out is not None:
            return out, None
        if e:
            last_err = e

    if _cmd_exists("xsel"):
        out, e = _run_capture(["xsel", "--clipboard", "--output"])
        if out is not None:
            return out, None
        if e:
            last_err = e

    return None, _hint(last_err or "No clipboard backend available")


def set_clipboard_text(text: str) -> Optional[str]:
    """Set clipboard; returns error message if it fails."""
    # 1) pyperclip
    try:
        pyperclip.copy(text)
        return None
    except pyperclip.PyperclipException:
        pass
    except Exception as e:
        last_err = f"Clipboard error: {e}"
    else:
        last_err = None

    # 2) Wayland helper
    if _cmd_exists("wl-copy"):
        e = _run_input(["wl-copy"], text)
        if e is None:
            return None
        last_err = e

    # 3) X11 helpers
    if _cmd_exists("xclip"):
        e = _run_input(["xclip", "-selection", "clipboard"], text)
        if e is None:
            return None
        last_err = e

    if _cmd_exists("xsel"):
        e = _run_input(["xsel", "--clipboard", "--input"], text)
        if e is None:
            return None
        last_err = e

    return _hint(last_err or "No clipboard backend available")


def _hint(msg: str) -> str:
    m = (msg or "").strip()
    base = (
        f"{m}\n\n"
        "Clipboard backend not available. Install one of:\n"
        "- Wayland: wl-clipboard (provides wl-copy/wl-paste)\n"
        "- X11: xclip (recommended) or xsel\n\n"
        "Note: Many immutable distros (e.g., Bazzite/Silverblue) require rpm-ostree installs (reboot)\n"
        "or running this app inside Distrobox/Toolbox."
    )
    return base
