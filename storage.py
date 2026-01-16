from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from platformdirs import user_config_dir, user_data_dir

APP_NAME = "Copy2"
APP_AUTHOR = "MellowLabs"


def _now_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_dirs() -> Tuple[Path, Path]:
    """Return (config_dir, data_dir) and ensure they exist."""
    cfg_dir = Path(user_config_dir(APP_NAME, APP_AUTHOR))
    data_dir = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    cfg_dir.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    return cfg_dir, data_dir


def config_path() -> Path:
    cfg_dir, _ = get_dirs()
    return cfg_dir / "config.json"


def history_path() -> Path:
    _, data_dir = get_dirs()
    return data_dir / "history.json"


DEFAULT_HOTKEYS: Dict[str, str] = {
    "paste_reversed": "ctrl+alt+v",
    "cycle_back": "ctrl+alt+up",
    "cycle_forward": "ctrl+alt+down",
    "search_focus": "ctrl+alt+s",
    "pause": "ctrl+alt+p",
    "show_hide": "ctrl+alt+w",
}


@dataclass
class Config:
    max_history: int = 20
    poll_interval_ms: int = 500
    enable_hotkeys: bool = False
    send_paste: bool = False
    hotkeys: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_HOTKEYS))
    favorites: List[str] = field(default_factory=list)


def _coerce_int(value: Any, default: int, min_v: int, max_v: int) -> int:
    try:
        v = int(value)
    except Exception:
        return default
    return max(min_v, min(max_v, v))


def load_config() -> Config:
    path = config_path()
    cfg = Config()

    if not path.exists():
        save_config(cfg)
        return cfg

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        save_config(cfg)
        return cfg

    cfg.max_history = _coerce_int(raw.get("max_history", cfg.max_history), cfg.max_history, 1, 500)
    cfg.poll_interval_ms = _coerce_int(raw.get("poll_interval_ms", cfg.poll_interval_ms), cfg.poll_interval_ms, 100, 5000)
    cfg.enable_hotkeys = bool(raw.get("enable_hotkeys", cfg.enable_hotkeys))
    cfg.send_paste = bool(raw.get("send_paste", cfg.send_paste))

    hotkeys = raw.get("hotkeys")
    if isinstance(hotkeys, dict):
        merged = dict(DEFAULT_HOTKEYS)
        for k, v in hotkeys.items():
            if isinstance(k, str) and isinstance(v, str) and v.strip():
                merged[k] = v.strip().lower()
        cfg.hotkeys = merged

    favs = raw.get("favorites")
    if isinstance(favs, list):
        cleaned: List[str] = []
        for f in favs:
            if isinstance(f, str) and f.strip():
                cleaned.append(f)
        cfg.favorites = cleaned

    return cfg


def save_config(cfg: Config) -> None:
    path = config_path()
    data = {
        "max_history": cfg.max_history,
        "poll_interval_ms": cfg.poll_interval_ms,
        "enable_hotkeys": cfg.enable_hotkeys,
        "send_paste": cfg.send_paste,
        "hotkeys": cfg.hotkeys,
        "favorites": cfg.favorites,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_history(max_items: int) -> List[Dict[str, str]]:
    path = history_path()
    if not path.exists():
        return []
    try:
        items = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if not isinstance(items, list):
        return []

    cleaned: List[Dict[str, str]] = []
    for it in items[-max_items:]:
        if isinstance(it, dict) and isinstance(it.get("text"), str):
            cleaned.append({
                "time": str(it.get("time", "")) or _now_ts(),
                "text": it["text"],
            })
    return cleaned


def save_history(items: List[Dict[str, str]]) -> None:
    path = history_path()
    path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")


def make_entry(text: str) -> Dict[str, str]:
    return {"time": _now_ts(), "text": text}
