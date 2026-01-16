from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Tuple

from pynput import keyboard


def to_pynput_combo(combo: str) -> str:
    """Convert 'ctrl+alt+v' -> '<ctrl>+<alt>+v' for pynput."""
    combo = (combo or "").strip().lower()
    if not combo:
        return combo

    parts = [p.strip() for p in combo.split('+') if p.strip()]
    mapped = []
    for p in parts:
        if p in ("ctrl", "control"):
            mapped.append("<ctrl>")
        elif p in ("alt",):
            mapped.append("<alt>")
        elif p in ("shift",):
            mapped.append("<shift>")
        elif p in ("cmd", "win", "super", "meta"):
            mapped.append("<cmd>")
        else:
            # special keys
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
    listener: Optional[keyboard.GlobalHotKeys] = None

    def start(self) -> Tuple[bool, Optional[str]]:
        """Start global hotkeys. Returns (ok, error_message)."""
        try:
            self.listener = keyboard.GlobalHotKeys(self.mapping)
            self.listener.start()
            return True, None
        except Exception as e:
            self.listener = None
            return False, (
                f"Could not register global hotkeys: {e}\n\n"
                "Linux note: Global hotkeys are often blocked on Wayland sessions, and may require X11."
            )

    def stop(self) -> None:
        try:
            if self.listener:
                self.listener.stop()
        finally:
            self.listener = None


def send_ctrl_v_best_effort() -> Tuple[bool, Optional[str]]:
    """Try to send Ctrl+V keystroke. Works on many X11 setups; may fail on Wayland."""
    try:
        controller = keyboard.Controller()
        with controller.pressed(keyboard.Key.ctrl):
            controller.press('v')
            controller.release('v')
        return True, None
    except Exception as e:
        return False, (
            f"Could not inject Ctrl+V: {e}\n\n"
            "Linux note: Many Wayland desktops block synthetic key injection by default."
        )
