from __future__ import annotations

from typing import Optional, Tuple

import pyperclip


def get_clipboard_text() -> Tuple[Optional[str], Optional[str]]:
    """Return (text, error_message)."""
    try:
        txt = pyperclip.paste()
    except pyperclip.PyperclipException as e:
        return None, _hint(str(e))
    except Exception as e:
        return None, f"Clipboard error: {e}"

    if isinstance(txt, str):
        return txt, None
    return None, None


def set_clipboard_text(text: str) -> Optional[str]:
    """Set clipboard; returns error message if it fails."""
    try:
        pyperclip.copy(text)
        return None
    except pyperclip.PyperclipException as e:
        return _hint(str(e))
    except Exception as e:
        return f"Clipboard error: {e}"


def _hint(msg: str) -> str:
    # pyperclip on Linux requires a clipboard provider. Provide actionable guidance.
    m = msg.lower()
    if "xclip" in m or "xsel" in m or "wl-copy" in m or "wl-clipboard" in m:
        return msg
    return (
        f"{msg}\n\n"
        "Linux note: pyperclip needs a clipboard helper.\n"
        "- X11 desktops: install 'xclip' (recommended) or 'xsel'\n"
        "- Wayland desktops: install 'wl-clipboard'\n"
    )
