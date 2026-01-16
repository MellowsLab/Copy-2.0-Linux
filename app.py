from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import ttk

from .clipboard import get_clipboard_text, set_clipboard_text
from .hotkeys import HotkeyManager, send_ctrl_v_best_effort, to_pynput_combo
from .storage import Config, load_config, load_history, make_entry, save_config, save_history


class Copy2App(ttk.Frame):
    def __init__(self, master: tk.Tk):
        super().__init__(master)
        self.master = master

        self.cfg: Config = load_config()
        self.history: List[Dict[str, str]] = load_history(self.cfg.max_history)

        # UI state
        self.paused = tk.BooleanVar(value=False)
        self.session_only = tk.BooleanVar(value=False)
        self.enable_hotkeys = tk.BooleanVar(value=self.cfg.enable_hotkeys)
        self.send_paste = tk.BooleanVar(value=self.cfg.send_paste)
        self.search_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="Ready")

        self._filtered_indexes: List[int] = list(range(len(self.history)))
        self._last_clipboard_text: Optional[str] = None
        self._ignore_clipboard_once = False

        self._hotkeys: Optional[HotkeyManager] = None

        self._build_ui()
        self._refresh_lists()
        self._start_services()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        self.master.title("Copy 2.0 (Linux)")
        self.master.geometry("860x520")

        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=(10, 6))

        ttk.Checkbutton(toolbar, text="Paused", variable=self.paused, command=self._on_pause_toggle).pack(side="left")
        ttk.Checkbutton(toolbar, text="Session only", variable=self.session_only).pack(side="left", padx=(10, 0))

        ttk.Label(toolbar, text="Search:").pack(side="left", padx=(20, 6))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, width=34)
        self.search_entry.pack(side="left")
        self.search_entry.bind("<KeyRelease>", lambda _e: self._refresh_lists())

        ttk.Button(toolbar, text="Settings", command=self._open_settings).pack(side="right")
        ttk.Button(toolbar, text="Help", command=self._show_help).pack(side="right", padx=(0, 8))

        # Main layout
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        self.notebook = ttk.Notebook(main)
        self.notebook.pack(fill="both", expand=True)

        self.tab_history = ttk.Frame(self.notebook)
        self.tab_favs = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_history, text="History")
        self.notebook.add(self.tab_favs, text="Favorites")

        self._build_history_tab(self.tab_history)
        self._build_favs_tab(self.tab_favs)

        # Status bar
        status = ttk.Frame(self)
        status.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Label(status, textvariable=self.status_var, anchor="w").pack(side="left", fill="x", expand=True)

        self.pack(fill="both", expand=True)

        self.master.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_history_tab(self, parent: ttk.Frame) -> None:
        left = ttk.Frame(parent)
        right = ttk.Frame(parent)
        left.pack(side="left", fill="y", padx=(8, 6), pady=8)
        right.pack(side="right", fill="both", expand=True, padx=(6, 8), pady=8)

        # Listbox with scrollbar
        self.history_list = tk.Listbox(left, width=42, height=18, exportselection=False, selectmode=tk.EXTENDED)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.history_list.yview)
        self.history_list.configure(yscrollcommand=sb.set)
        self.history_list.pack(side="left", fill="y")
        sb.pack(side="right", fill="y")
        self.history_list.bind("<<ListboxSelect>>", lambda _e: self._update_preview(from_favorites=False))

        # Buttons
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))

        ttk.Button(btns, text="Copy", command=self._copy_selected).pack(fill="x")
        ttk.Button(btns, text="Reverse lines", command=self._reverse_selected).pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Paste (best effort)", command=lambda: self._paste_selected(best_effort=True)).pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Add to favorites", command=self._add_selected_to_favorites).pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Combine selected", command=self._combine_selected).pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Clear history", command=self._clear_history).pack(fill="x", pady=(6, 0))

        # Preview
        ttk.Label(right, text="Preview").pack(anchor="w")
        self.preview_text = tk.Text(right, wrap="word", height=16)
        self.preview_text.pack(fill="both", expand=True)
        self.preview_text.configure(state="disabled")

        bottom = ttk.Frame(right)
        bottom.pack(fill="x", pady=(8, 0))
        ttk.Button(bottom, text="Export history", command=self._export_history).pack(side="left")
        ttk.Button(bottom, text="Import history", command=self._import_history).pack(side="left", padx=(8, 0))

    def _build_favs_tab(self, parent: ttk.Frame) -> None:
        left = ttk.Frame(parent)
        right = ttk.Frame(parent)
        left.pack(side="left", fill="y", padx=(8, 6), pady=8)
        right.pack(side="right", fill="both", expand=True, padx=(6, 8), pady=8)

        self.favs_list = tk.Listbox(left, width=42, height=18, exportselection=False)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.favs_list.yview)
        self.favs_list.configure(yscrollcommand=sb.set)
        self.favs_list.pack(side="left", fill="y")
        sb.pack(side="right", fill="y")
        self.favs_list.bind("<<ListboxSelect>>", lambda _e: self._update_preview(from_favorites=True))

        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=(8, 0))
        ttk.Button(btns, text="Copy", command=self._copy_favorite).pack(fill="x")
        ttk.Button(btns, text="Paste (best effort)", command=lambda: self._paste_favorite(best_effort=True)).pack(fill="x", pady=(6, 0))
        ttk.Button(btns, text="Remove", command=self._remove_favorite).pack(fill="x", pady=(6, 0))

        ttk.Label(right, text="Preview").pack(anchor="w")
        self.preview_text_favs = tk.Text(right, wrap="word", height=16)
        self.preview_text_favs.pack(fill="both", expand=True)
        self.preview_text_favs.configure(state="disabled")

    # ---------------- Core behavior ----------------
    def _start_services(self) -> None:
        # Seed last clipboard value to avoid immediate duplication
        txt, _err = get_clipboard_text()
        self._last_clipboard_text = txt

        # Clipboard polling
        self.after(self.cfg.poll_interval_ms, self._poll_clipboard)

        # Hotkeys (optional)
        if self.enable_hotkeys.get():
            self._start_hotkeys()

    def _poll_clipboard(self) -> None:
        try:
            if not self.paused.get():
                txt, err = get_clipboard_text()
                if err:
                    # show once every few seconds? keep simple
                    self._set_status("Clipboard backend missing. Open Settings > Help for install hints.")
                else:
                    if isinstance(txt, str):
                        if self._ignore_clipboard_once:
                            self._ignore_clipboard_once = False
                            self._last_clipboard_text = txt
                        elif txt and txt.strip() and txt != self._last_clipboard_text:
                            self._last_clipboard_text = txt
                            self._add_history_entry(txt)
        finally:
            self.after(self.cfg.poll_interval_ms, self._poll_clipboard)

    def _add_history_entry(self, text: str) -> None:
        if self.history and text == self.history[-1].get("text"):
            return

        self.history.append(make_entry(text))
        if len(self.history) > self.cfg.max_history:
            self.history = self.history[-self.cfg.max_history :]

        if not self.session_only.get():
            save_history(self.history)

        self._refresh_lists()
        self._set_status(f"Captured clipboard ({len(text)} chars)")

    # ---------------- Selection helpers ----------------
    def _get_selected_history_indexes(self) -> List[int]:
        sel = list(self.history_list.curselection())
        if not sel:
            return []
        # map visible list index -> actual history index
        actual = []
        for i in sel:
            if 0 <= i < len(self._filtered_indexes):
                actual.append(self._filtered_indexes[i])
        return actual

    def _get_selected_history_text(self) -> Optional[str]:
        idxs = self._get_selected_history_indexes()
        if not idxs:
            return None
        # If multiple selected, use the first for actions like copy/reverse
        return self.history[idxs[0]]["text"]

    def _get_selected_fav_index(self) -> Optional[int]:
        sel = list(self.favs_list.curselection())
        if not sel:
            return None
        return sel[0]

    # ---------------- Actions (History) ----------------
    def _copy_selected(self) -> None:
        text = self._get_selected_history_text()
        if not text:
            self._set_status("No history item selected")
            return
        err = set_clipboard_text(text)
        self._ignore_clipboard_once = True
        if err:
            messagebox.showerror("Clipboard error", err)
            return
        self._set_status("Copied to clipboard")

    def _reverse_selected(self) -> None:
        text = self._get_selected_history_text()
        if not text:
            # fall back to current clipboard
            text, err = get_clipboard_text()
            if err:
                messagebox.showerror("Clipboard error", err)
                return
        if not text:
            self._set_status("Nothing to reverse")
            return
        lines = str(text).splitlines()
        reversed_text = "\n".join(reversed(lines))
        err = set_clipboard_text(reversed_text)
        self._ignore_clipboard_once = True
        if err:
            messagebox.showerror("Clipboard error", err)
            return
        self._set_status("Reversed lines copied to clipboard")

    def _paste_selected(self, best_effort: bool = False) -> None:
        self._copy_selected()
        if best_effort and self.send_paste.get():
            ok, err = send_ctrl_v_best_effort()
            if not ok and err:
                messagebox.showwarning("Paste not available", err)

    def _combine_selected(self) -> None:
        idxs = self._get_selected_history_indexes()
        if not idxs:
            self._set_status("Select one or more history items")
            return
        combined = "\n".join(self.history[i]["text"] for i in idxs)
        err = set_clipboard_text(combined)
        self._ignore_clipboard_once = True
        if err:
            messagebox.showerror("Clipboard error", err)
            return
        self._set_status(f"Combined {len(idxs)} items copied to clipboard")

    def _add_selected_to_favorites(self) -> None:
        text = self._get_selected_history_text()
        if not text:
            self._set_status("No history item selected")
            return
        if text in self.cfg.favorites:
            self._set_status("Already in favorites")
            return
        self.cfg.favorites.append(text)
        save_config(self.cfg)
        self._refresh_lists()
        self._set_status("Added to favorites")

    def _clear_history(self) -> None:
        if not self.history:
            return
        if not messagebox.askyesno("Clear history", "Clear clipboard history?"):
            return
        self.history = []
        if not self.session_only.get():
            save_history(self.history)
        self._refresh_lists()
        self._set_status("History cleared")

    def _export_history(self) -> None:
        if not self.history:
            self._set_status("Nothing to export")
            return
        path = filedialog.asksaveasfilename(
            title="Export history",
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        Path(path).write_text(json.dumps(self.history, ensure_ascii=False, indent=2), encoding="utf-8")
        self._set_status(f"Exported to {path}")

    def _import_history(self) -> None:
        path = filedialog.askopenfilename(
            title="Import history",
            filetypes=[("JSON", "*.json"), ("All", "*")],
        )
        if not path:
            return
        try:
            items = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            messagebox.showerror("Import error", f"Could not read file: {e}")
            return
        if not isinstance(items, list):
            messagebox.showerror("Import error", "Invalid history file")
            return
        cleaned: List[Dict[str, str]] = []
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("text"), str):
                cleaned.append({"time": str(it.get("time", "")) or "", "text": it["text"]})
        self.history = cleaned[-self.cfg.max_history :]
        if not self.session_only.get():
            save_history(self.history)
        self._refresh_lists()
        self._set_status(f"Imported {len(self.history)} items")

    # ---------------- Actions (Favorites) ----------------
    def _copy_favorite(self) -> None:
        idx = self._get_selected_fav_index()
        if idx is None:
            self._set_status("No favorite selected")
            return
        text = self.cfg.favorites[idx]
        err = set_clipboard_text(text)
        self._ignore_clipboard_once = True
        if err:
            messagebox.showerror("Clipboard error", err)
            return
        self._set_status("Copied favorite to clipboard")

    def _paste_favorite(self, best_effort: bool = False) -> None:
        self._copy_favorite()
        if best_effort and self.send_paste.get():
            ok, err = send_ctrl_v_best_effort()
            if not ok and err:
                messagebox.showwarning("Paste not available", err)

    def _remove_favorite(self) -> None:
        idx = self._get_selected_fav_index()
        if idx is None:
            return
        text = self.cfg.favorites[idx]
        if not messagebox.askyesno("Remove favorite", "Remove selected favorite?"):
            return
        self.cfg.favorites = [f for f in self.cfg.favorites if f != text]
        save_config(self.cfg)
        self._refresh_lists()
        self._set_status("Removed favorite")

    # ---------------- Preview & filtering ----------------
    def _refresh_lists(self) -> None:
        term = self.search_var.get().strip().lower()
        if term:
            self._filtered_indexes = [i for i, e in enumerate(self.history) if term in e["text"].lower()]
        else:
            self._filtered_indexes = list(range(len(self.history)))

        # History list
        self.history_list.delete(0, tk.END)
        for i in self._filtered_indexes:
            e = self.history[i]
            ts = (e.get("time") or "").split(" ")[-1][:8]
            snippet = e["text"].replace("\n", "\\n")
            if len(snippet) > 64:
                snippet = snippet[:64] + "…"
            self.history_list.insert(tk.END, f"{ts} | {snippet}")

        # Favorites list
        self.favs_list.delete(0, tk.END)
        for f in self.cfg.favorites:
            snippet = f.replace("\n", "\\n")
            if len(snippet) > 64:
                snippet = snippet[:64] + "…"
            self.favs_list.insert(tk.END, snippet)

        self._update_preview(from_favorites=False)
        self._update_preview(from_favorites=True)

    def _update_preview(self, from_favorites: bool) -> None:
        if from_favorites:
            idx = self._get_selected_fav_index()
            text = self.cfg.favorites[idx] if idx is not None and 0 <= idx < len(self.cfg.favorites) else ""
            w = self.preview_text_favs
        else:
            text = self._get_selected_history_text() or ""
            w = self.preview_text

        w.configure(state="normal")
        w.delete("1.0", tk.END)
        w.insert(tk.END, text)
        w.configure(state="disabled")

    # ---------------- Settings / Help ----------------
    def _open_settings(self) -> None:
        win = tk.Toplevel(self.master)
        win.title("Settings")
        win.geometry("520x520")
        win.transient(self.master)
        win.grab_set()

        frm = ttk.Frame(win, padding=12)
        frm.pack(fill="both", expand=True)

        # Basic
        ttk.Label(frm, text="History size (max items)").grid(row=0, column=0, sticky="w")
        max_var = tk.StringVar(value=str(self.cfg.max_history))
        ttk.Entry(frm, textvariable=max_var, width=10).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Clipboard poll interval (ms)").grid(row=1, column=0, sticky="w", pady=(8, 0))
        poll_var = tk.StringVar(value=str(self.cfg.poll_interval_ms))
        ttk.Entry(frm, textvariable=poll_var, width=10).grid(row=1, column=1, sticky="w", pady=(8, 0))

        ttk.Separator(frm).grid(row=2, column=0, columnspan=2, sticky="ew", pady=12)

        # Hotkeys
        ttk.Checkbutton(frm, text="Enable global hotkeys (best effort)", variable=self.enable_hotkeys).grid(
            row=3, column=0, columnspan=2, sticky="w"
        )
        ttk.Checkbutton(frm, text="Attempt auto-paste (Ctrl+V injection)", variable=self.send_paste).grid(
            row=4, column=0, columnspan=2, sticky="w", pady=(6, 0)
        )

        row = 5
        hk_vars: Dict[str, tk.StringVar] = {}
        for key, label in [
            ("paste_reversed", "Paste reversed"),
            ("cycle_back", "Cycle back"),
            ("cycle_forward", "Cycle forward"),
            ("search_focus", "Focus search"),
            ("pause", "Pause / resume"),
            ("show_hide", "Show / hide window"),
        ]:
            ttk.Label(frm, text=label).grid(row=row, column=0, sticky="w", pady=(6, 0))
            v = tk.StringVar(value=self.cfg.hotkeys.get(key, ""))
            hk_vars[key] = v
            ttk.Entry(frm, textvariable=v, width=24).grid(row=row, column=1, sticky="w", pady=(6, 0))
            row += 1

        ttk.Separator(frm).grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)
        row += 1

        help_text = (
            "Clipboard dependencies:\n"
            "- X11: install xclip (recommended) or xsel\n"
            "- Wayland: install wl-clipboard\n\n"
            "Notes:\n"
            "- Global hotkeys and key injection may not work on Wayland sessions.\n"
            "- If Paste does not work, the item is still copied to your clipboard; paste manually.")
        ttk.Label(frm, text=help_text, justify="left").grid(row=row, column=0, columnspan=2, sticky="w")
        row += 1

        def on_save() -> None:
            # Validate and apply
            self.cfg.max_history = max(1, min(500, int(max_var.get() or self.cfg.max_history)))
            self.cfg.poll_interval_ms = max(100, min(5000, int(poll_var.get() or self.cfg.poll_interval_ms)))
            self.cfg.enable_hotkeys = bool(self.enable_hotkeys.get())
            self.cfg.send_paste = bool(self.send_paste.get())
            for k, v in hk_vars.items():
                if v.get().strip():
                    self.cfg.hotkeys[k] = v.get().strip().lower()
            save_config(self.cfg)

            # Apply runtime changes
            self._restart_hotkeys()
            self._set_status("Settings saved")
            win.destroy()

        btnrow = ttk.Frame(frm)
        btnrow.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        btnrow.columnconfigure(0, weight=1)
        ttk.Button(btnrow, text="Save", command=on_save).pack(side="right")
        ttk.Button(btnrow, text="Cancel", command=win.destroy).pack(side="right", padx=(0, 8))

    def _show_help(self) -> None:
        msg = (
            "Copy 2.0 (Linux build)\n\n"
            "What it does:\n"
            "- Watches your clipboard and keeps a history\n"
            "- Lets you copy any previous item back to clipboard\n"
            "- Reverse-line copy (useful for log blocks, lists, etc.)\n"
            "- Favorites\n\n"
            "Install notes:\n"
            "- Needs Python 3 + Tkinter (python3-tk)\n"
            "- Clipboard helper: xclip/xsel (X11) or wl-clipboard (Wayland)\n\n"
            "Hotkeys (optional):\n"
            "- Can be enabled in Settings. May not work on Wayland.")
        messagebox.showinfo("Help", msg)

    # ---------------- Hotkeys ----------------
    def _restart_hotkeys(self) -> None:
        self._stop_hotkeys()
        if self.cfg.enable_hotkeys:
            self._start_hotkeys()

    def _start_hotkeys(self) -> None:
        def safe(cb):
            self.master.after(0, cb)

        mapping: Dict[str, callable] = {}
        hk = self.cfg.hotkeys

        if hk.get("paste_reversed"):
            mapping[to_pynput_combo(hk["paste_reversed"])] = lambda: safe(self._reverse_selected)
        if hk.get("cycle_back"):
            mapping[to_pynput_combo(hk["cycle_back"])] = lambda: safe(lambda: self._cycle_history(-1))
        if hk.get("cycle_forward"):
            mapping[to_pynput_combo(hk["cycle_forward"])] = lambda: safe(lambda: self._cycle_history(1))
        if hk.get("pause"):
            mapping[to_pynput_combo(hk["pause"])] = lambda: safe(self._toggle_pause_state)
        if hk.get("search_focus"):
            mapping[to_pynput_combo(hk["search_focus"])] = lambda: safe(lambda: self.search_entry.focus_set())
        if hk.get("show_hide"):
            mapping[to_pynput_combo(hk["show_hide"])] = lambda: safe(self._toggle_window_visibility)

        if not mapping:
            self._set_status("No hotkeys configured")
            return

        self._hotkeys = HotkeyManager(mapping=mapping)
        ok, err = self._hotkeys.start()
        if not ok and err:
            messagebox.showwarning("Hotkeys not available", err)
            self._hotkeys = None

    def _stop_hotkeys(self) -> None:
        if self._hotkeys:
            self._hotkeys.stop()
            self._hotkeys = None

    def _cycle_history(self, delta: int) -> None:
        if not self._filtered_indexes:
            return
        sel = list(self.history_list.curselection())
        pos = sel[0] if sel else 0
        pos = (pos + delta) % len(self._filtered_indexes)
        self.history_list.selection_clear(0, tk.END)
        self.history_list.selection_set(pos)
        self.history_list.activate(pos)
        self.history_list.see(pos)
        self._copy_selected()
        if self.send_paste.get():
            ok, _ = send_ctrl_v_best_effort()
            if ok:
                self._set_status("Cycled + pasted (best effort)")

    def _toggle_pause_state(self) -> None:
        self.paused.set(not self.paused.get())
        self._on_pause_toggle()

    def _toggle_window_visibility(self) -> None:
        if self.master.state() == "withdrawn":
            self.master.deiconify()
            self.master.lift()
        else:
            self.master.withdraw()

    # ---------------- Misc ----------------
    def _on_pause_toggle(self) -> None:
        self._set_status("Paused" if self.paused.get() else "Running")

    def _set_status(self, msg: str) -> None:
        self.status_var.set(msg)

    def _on_close(self) -> None:
        try:
            # Persist history unless session-only
            if not self.session_only.get():
                save_history(self.history)
            save_config(self.cfg)
        finally:
            self._stop_hotkeys()
            self.master.destroy()


def main() -> None:
    # Tk needs a display server; this will not run in pure headless shells.
    root = tk.Tk()
    # Improve scaling on HiDPI
    try:
        root.tk.call('tk', 'scaling', 1.0)
    except Exception:
        pass

    app = Copy2App(root)
    app.mainloop()


if __name__ == "__main__":
    main()
