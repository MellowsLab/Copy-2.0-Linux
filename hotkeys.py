from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple


def is_wayland() -> bool:
    return os.environ.get("XDG_SESSION_TYPE", "").lower() == "wayland" or bool(os.environ.get("WAYLAND_DISPLAY"))


def to_pynput_combo(combo: str) -> str:
    """Convert 'ctrl+alt+v' -> '<ctrl>+<alt>+v' for pynput."""
    combo = (combo or "").strip().lower()
    if not combo:
        return combo

    parts = [p.strip() for p in combo.split("+") if p.strip()]
    mapped = []
    for p in parts:
        if p in ("ctrl", "control"):
            mapped.append("<ctrl>")
        elif p == "alt":
            mapped.append("<alt>")
        elif p == "shift":
            mapped.append("<shift>")
        elif p in ("cmd", "win", "super", "meta"):
            mapped.append("<cmd>")
        else:
            special = {
                "up": "<up>",
                "down": "<down>",
                "left": "<left>",
                "right": "<right>",
                "enter": "<enter>",
                "return": "<enter>",
                "esc": "<esc>",
                "escape": "<esc>",
                "space": "<space>",
                "tab": "<tab>",
            }
            mapped.append(special.get(p, p))
    return "+".join(mapped)


@dataclass
class HotkeyManager:
    mapping: Dict[str, Callable[[], None]]
    listener: Optional[object] = None

    def start(self) -> Tuple[bool, Optional[str]]:
        """Start global hotkeys. Returns (ok, error_message)."""
        if is_wayland():
            return False, (
                "Global hotkeys are disabled on Wayland sessions by default.\n\n"
                "Most Wayland compositors block global hotkeys and synthetic key injection for security.\n"
                "Copy2 will still work normally via the GUI.\n\n"
                "Workarounds:\n"
                "- Log into an X11 session (if your distro offers it), OR\n"
                "- Use compositor-specific hotkey tools (e.g., KDE/GNOME shortcuts) to launch Copy2."
            )

        try:
            from pynput import keyboard

            self.listener = keyboard.GlobalHotKeys(self.mapping)
            self.listener.start()
            return True, None
        except Exception as e:
            self.listener = None
            return False, f"Could not register global hotkeys: {e}"

    def stop(self) -> None:
        try:
            if self.listener is not None:
                # pynput listener has stop()
                stop = getattr(self.listener, "stop", None)
                if callable(stop):
                    stop()
        finally:
            self.listener = None


def send_ctrl_v_best_effort() -> Tuple[bool, Optional[str]]:
    """Try to send Ctrl+V keystroke.

    Works on many X11 setups; typically blocked on Wayland.
    """
    if is_wayland():
        return False, (
            "Ctrl+V key injection is blocked on Wayland sessions.\n\n"
            "Use the app's Copy button, or paste manually in the target application."
        )

    try:
        from pynput import keyboard

        controller = keyboard.Controller()
        with controller.pressed(keyboard.Key.ctrl):
            controller.press("v")
            controller.release("v")
        return True, None
    except Exception as e:
        return False, f"Could not inject Ctrl+V: {e}"
