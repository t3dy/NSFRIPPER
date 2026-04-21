#!/usr/bin/env python3
"""Tk launcher for the ReapNES live-play UI.

Implements per keyboard_lab/docs/UI_LAUNCHER_DESIGN.md Layers 4-5:

  Transitions:
    - select_game, select_track, select_synth
    - adjust_knob      (stored in-memory; spliced on Open)
    - open_in_reaper   (copies RPP to tmp, splices slider line, opens)
    - revert           (resets knobs to ui_params.json defaults)
    - quit             (persists last-session state)

Inputs:
  keyboard_lab/db/ui_params.json    — Layer 1 primary_12 params
  keyboard_lab/db/ui_library.json   — Layer 2 games / tracks / synths

Rebuild the library via scripts/build_ui_library.py after adding games.

Knobs spliced: the 10 of primary_12 that have a jsfx_slider mapping.
vibrato_depth and intensity_macro are stored but not spliced — they
depend on JSFX Must-do #3 and Should-do #4 per docs/JSFX_LIVE_PRIORITY.md.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
LIBRARY_PATH = ROOT / "keyboard_lab" / "db" / "ui_library.json"
PARAMS_PATH = ROOT / "keyboard_lab" / "db" / "ui_params.json"
STATE_PATH = Path.home() / ".reapnes_launcher.json"
TMP_RPP_DIR = Path(tempfile.gettempdir()) / "reapnes_launcher"

DUTY_LABELS = ["12.5%", "25%", "50%", "75%"]

# Matches a full <JS "..." ...>\n  <slider-values>\n  ...> block for
# a ReapNES JSFX instance.  Group 1 = the slider-values line.
JS_BLOCK_RE = re.compile(
    r'(<JS\s+"[^"]*ReapNES[^"]*"\s*""\s*\n\s*)([^\n]+)(\n)',
    re.IGNORECASE,
)


def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def load_library() -> dict:
    if not LIBRARY_PATH.exists():
        messagebox.showerror(
            "Library missing",
            f"{LIBRARY_PATH} not found.\n"
            f"Run: python scripts/build_ui_library.py"
        )
        sys.exit(1)
    return load_json(LIBRARY_PATH)


def load_params() -> dict:
    if not PARAMS_PATH.exists():
        messagebox.showerror(
            "Params missing",
            f"{PARAMS_PATH} not found."
        )
        sys.exit(1)
    return load_json(PARAMS_PATH)


def load_state() -> dict:
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    try:
        STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as exc:
        print(f"warning: could not persist session state: {exc}", file=sys.stderr)


def format_slider_value(p: dict, value: float) -> str:
    """Format a knob value per param unit for RPP slider lines."""
    unit = p.get("unit", "")
    if unit in ("enum", "int"):
        return str(int(round(value)))
    if unit == "ms":
        return str(int(round(value)))
    if unit == "float":
        return f"{float(value):.6f}"
    if unit == "cents":
        return str(int(round(value)))
    return str(value)


def splice_slider_line(line: str, slider_values: dict[int, str]) -> str:
    """Given an RPP slider-values line and a {1-indexed slider: formatted}
    dict, return the rewritten line.  Tokens beyond the line's length
    are appended.
    """
    tokens = line.split()
    max_idx = max(slider_values) if slider_values else len(tokens)
    # Grow with '-' (default) if needed
    while len(tokens) < max_idx:
        tokens.append("-")
    for slot_1based, formatted in slider_values.items():
        tokens[slot_1based - 1] = formatted
    return " ".join(tokens)


class Launcher:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.library = load_library()
        self.params_doc = load_params()
        self.primary_12 = self.params_doc["primary_12"]
        self.state = load_state()

        self.game_slug: str | None = None
        self.track_idx: int = 0
        self.synth_key: str | None = None

        # state.knobs: param_id -> current value (raw, pre-format)
        self.knobs: dict[str, float] = {
            p["param_id"]: p["default"] for p in self.primary_12
        }
        self.knob_vars: dict[str, tk.Variable] = {}
        self.knob_labels: dict[str, tk.StringVar] = {}

        root.title("ReapNES Launcher")
        root.geometry("760x520")

        self._build_dropdowns(root)
        self._build_knobs(root)
        self._build_footer(root)

        # shortcuts
        root.bind("<Control-o>", lambda _e: self._on_open_in_reaper())
        root.bind("<Control-q>", lambda _e: self._on_quit())
        root.bind("<Control-r>", lambda _e: self._on_revert())
        root.protocol("WM_DELETE_WINDOW", self._on_quit)

        self._restore_selection()

    # ------------------------------------------------------------ UI build
    def _build_dropdowns(self, parent: tk.Misc) -> None:
        top = ttk.LabelFrame(parent, text="Selection", padding=8)
        top.pack(fill=tk.X, padx=8, pady=(8, 4))

        ttk.Label(top, text="Game").grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.dd_game = ttk.Combobox(top, state="readonly", width=60)
        self.dd_game["values"] = [g["display_name"] for g in self.library["games"]]
        self.dd_game.grid(row=0, column=1, sticky="we")
        self.dd_game.bind("<<ComboboxSelected>>", lambda _e: self._on_select_game())

        ttk.Label(top, text="Track").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.dd_track = ttk.Combobox(top, state="readonly", width=60)
        self.dd_track.grid(row=1, column=1, sticky="we", pady=(4, 0))
        self.dd_track.bind("<<ComboboxSelected>>", lambda _e: self._on_select_track())

        ttk.Label(top, text="Synth").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=(4, 0))
        self.dd_synth = ttk.Combobox(top, state="readonly", width=60)
        self.dd_synth["values"] = [self._synth_label(s) for s in self.library["synths"]]
        self.dd_synth.grid(row=2, column=1, sticky="we", pady=(4, 0))
        self.dd_synth.bind("<<ComboboxSelected>>", lambda _e: self._on_select_synth())

        top.columnconfigure(1, weight=1)

    def _build_knobs(self, parent: tk.Misc) -> None:
        frame = ttk.LabelFrame(parent, text="Primary controls", padding=8)
        frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        # 3-column grid of knob widgets
        cols = 3
        for i, p in enumerate(self.primary_12):
            r, c = divmod(i, cols)
            self._build_one_knob(frame, p, r, c)
        for c in range(cols):
            frame.columnconfigure(c, weight=1)

    def _build_one_knob(self, parent: tk.Misc, p: dict, r: int, c: int) -> None:
        pid = p["param_id"]
        pending = p.get("jsfx_slider") == "none"

        cell = ttk.Frame(parent, padding=6)
        cell.grid(row=r, column=c, sticky="nsew")

        name = p["display_name"]
        if pending:
            name += " (!)"
        ttk.Label(cell, text=name).pack(anchor="w")

        rng = p["range"]
        default = p["default"]
        unit = p.get("unit")

        if unit == "enum":
            # ComboBox with labeled values
            var = tk.StringVar(value=DUTY_LABELS[int(default)])
            self.knob_vars[pid] = var
            cb = ttk.Combobox(cell, textvariable=var, state="readonly",
                              values=DUTY_LABELS, width=12)
            cb.pack(fill=tk.X)
            cb.bind("<<ComboboxSelected>>", lambda _e, pid=pid: self._on_adjust_enum(pid))
        else:
            var = tk.DoubleVar(value=float(default))
            self.knob_vars[pid] = var
            val_label = tk.StringVar(value=self._value_display(p, default))
            self.knob_labels[pid] = val_label
            ttk.Label(cell, textvariable=val_label, foreground="#555").pack(anchor="e")
            scale = ttk.Scale(cell, from_=rng[0], to=rng[1], variable=var,
                              orient="horizontal",
                              command=lambda _v, pid=pid: self._on_adjust_scale(pid))
            scale.pack(fill=tk.X)

    def _build_footer(self, parent: tk.Misc) -> None:
        btns = ttk.Frame(parent, padding=(8, 0))
        btns.pack(fill=tk.X)
        self.btn_open = ttk.Button(btns, text="Open in REAPER",
                                   command=self._on_open_in_reaper)
        self.btn_open.pack(side=tk.LEFT)
        ttk.Button(btns, text="Revert",
                   command=self._on_revert).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns, text="Quit",
                   command=self._on_quit).pack(side=tk.RIGHT)

        self.status_var = tk.StringVar(value="Ready.")
        status = ttk.Label(parent, textvariable=self.status_var, relief=tk.SUNKEN,
                           anchor="w", padding=6)
        status.pack(fill=tk.X, side=tk.BOTTOM)

    # --------------------------------------------------------------- helpers
    def _synth_label(self, s: dict) -> str:
        conf = s.get("confidence", "")
        tag = f" [{conf}]" if conf == "low" else ""
        return f"{s.get('kind','?')}: {s['name']}{tag}"

    def _value_display(self, p: dict, val: float) -> str:
        unit = p.get("unit", "")
        if unit == "ms":
            return f"{int(round(val))} ms"
        if unit == "cents":
            return f"{int(round(val))} c"
        if unit == "int":
            return str(int(round(val)))
        if unit == "float":
            return f"{val:.2f}"
        return str(val)

    def _current_game(self) -> dict | None:
        return next((g for g in self.library["games"] if g["slug"] == self.game_slug), None)

    def _current_track(self) -> dict | None:
        g = self._current_game()
        if not g:
            return None
        tracks = self.library["tracks"].get(g["slug"], [])
        return tracks[self.track_idx] if 0 <= self.track_idx < len(tracks) else None

    def _current_synth(self) -> dict | None:
        return next((s for s in self.library["synths"] if s["id"] == self.synth_key), None)

    def _collect_slider_values(self) -> dict[int, str]:
        """Turn self.knobs into {jsfx_slider_1based: formatted_value} for
        params that have a slider binding."""
        out: dict[int, str] = {}
        for p in self.primary_12:
            slot = p.get("jsfx_slider")
            if not isinstance(slot, int):
                continue
            raw = self.knobs[p["param_id"]]
            out[slot] = format_slider_value(p, raw)
        return out

    # ----------------------------------------------------------- transitions
    def _on_select_game(self) -> None:
        idx = self.dd_game.current()
        if idx < 0:
            return
        g = self.library["games"][idx]
        self.game_slug = g["slug"]
        tracks = self.library["tracks"].get(g["slug"], [])
        self.dd_track["values"] = [
            f"{t['track_idx']:02d}  {t['display_name']}" for t in tracks
        ]
        if tracks:
            self.dd_track.current(0)
            self.track_idx = 0
            self._on_select_track(silent=True)
        else:
            self.dd_track.set("")
            self.track_idx = -1
        self.status_var.set(
            f"Game: {g['display_name']} ({len(tracks)} tracks, "
            f"rpp={'yes' if g['has_variant_b_rpp'] else 'generate'})"
        )

    def _on_select_track(self, silent: bool = False) -> None:
        idx = self.dd_track.current()
        if idx < 0:
            return
        self.track_idx = idx
        t = self._current_track()
        if not silent and t:
            self.status_var.set(f"Loaded {self.game_slug} / {t['display_name']}")

    def _on_select_synth(self) -> None:
        idx = self.dd_synth.current()
        if idx < 0:
            return
        s = self.library["synths"][idx]
        self.synth_key = s["id"]
        self.status_var.set(f"Synth: {s['name']}")

    def _on_adjust_scale(self, pid: str) -> None:
        var = self.knob_vars[pid]
        val = float(var.get())
        self.knobs[pid] = val
        p = next(p for p in self.primary_12 if p["param_id"] == pid)
        if pid in self.knob_labels:
            self.knob_labels[pid].set(self._value_display(p, val))

    def _on_adjust_enum(self, pid: str) -> None:
        var = self.knob_vars[pid]
        label = var.get()
        if label in DUTY_LABELS:
            self.knobs[pid] = DUTY_LABELS.index(label)

    def _on_revert(self) -> None:
        for p in self.primary_12:
            pid = p["param_id"]
            default = p["default"]
            self.knobs[pid] = default
            var = self.knob_vars.get(pid)
            if isinstance(var, tk.DoubleVar):
                var.set(float(default))
                if pid in self.knob_labels:
                    self.knob_labels[pid].set(self._value_display(p, default))
            elif isinstance(var, tk.StringVar):
                var.set(DUTY_LABELS[int(default)])
        self.status_var.set("Knobs reverted to defaults.")

    def _on_open_in_reaper(self) -> None:
        game = self._current_game()
        track = self._current_track()
        synth = self._current_synth()
        if not (game and track and synth):
            messagebox.showwarning(
                "Incomplete selection",
                "Pick a game, a track, and a synth before opening."
            )
            return

        src_rpp: Path | None = None
        if track.get("rpp_path"):
            src_rpp = ROOT / track["rpp_path"]
        else:
            src_rpp = self._generate_on_demand(game, track, synth)

        if src_rpp is None or not src_rpp.exists():
            messagebox.showerror("Open failed", "No RPP available.")
            return

        # Splice knob values into a tmp copy so we don't mutate the source.
        TMP_RPP_DIR.mkdir(parents=True, exist_ok=True)
        dest_rpp = TMP_RPP_DIR / f"{game['slug']}_{track['track_idx']:02d}_live.rpp"
        try:
            self._splice_sliders_to(src_rpp, dest_rpp)
        except OSError as exc:
            messagebox.showerror("Splice failed", str(exc))
            return

        try:
            if os.name == "nt":
                os.startfile(str(dest_rpp))
            else:
                subprocess.Popen(["reaper", str(dest_rpp)])
            self.status_var.set(f"Opened: {dest_rpp.name}")
        except OSError as exc:
            messagebox.showerror("Open failed", str(exc))

    def _splice_sliders_to(self, src: Path, dest: Path) -> None:
        text = src.read_text(encoding="utf-8", errors="replace")
        sliders = self._collect_slider_values()

        def repl(match: re.Match) -> str:
            head, slider_line, tail = match.group(1), match.group(2), match.group(3)
            new_line = splice_slider_line(slider_line, sliders)
            return head + new_line + tail

        new_text, n = JS_BLOCK_RE.subn(repl, text)
        if n == 0:
            # No ReapNES blocks matched; copy as-is so the user can still open.
            shutil.copyfile(src, dest)
            self.status_var.set(
                "Warning: no ReapNES JS blocks matched; opened unmodified."
            )
            return
        dest.write_text(new_text, encoding="utf-8")

    def _generate_on_demand(self, game: dict, track: dict, synth: dict) -> Path | None:
        TMP_RPP_DIR.mkdir(parents=True, exist_ok=True)
        synth_cli = self._synth_to_cli(synth)
        midi = ROOT / track["midi_path"]
        rpp = TMP_RPP_DIR / f"{game['slug']}_{track['track_idx']:02d}_{synth_cli}.rpp"
        cmd = [
            sys.executable, str(ROOT / "scripts" / "generate_project.py"),
            "--midi", str(midi),
            "--nes-native",
            "--synth", synth_cli,
            "-o", str(rpp),
        ]
        self.status_var.set(f"Generating RPP: {rpp.name} ...")
        self.root.update_idletasks()
        try:
            res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
        except OSError as exc:
            messagebox.showerror("Generator failed", str(exc))
            return None
        if res.returncode != 0:
            tail = "\n".join(res.stderr.strip().splitlines()[-10:])
            messagebox.showerror(
                "Generator failed",
                f"generate_project.py exited {res.returncode}.\n\n{tail}"
            )
            return None
        return rpp

    @staticmethod
    def _synth_to_cli(synth: dict) -> str:
        name = synth["name"].lower()
        if "console" in name:
            return "console"
        return "apu2"

    # ------------------------------------------------------------- session
    def _restore_selection(self) -> None:
        last = self.state.get("last_game")
        if last:
            for i, g in enumerate(self.library["games"]):
                if g["slug"] == last:
                    self.dd_game.current(i)
                    self._on_select_game()
                    last_idx = self.state.get("last_track_idx", 0)
                    if 0 <= last_idx < len(self.dd_track["values"]):
                        self.dd_track.current(last_idx)
                        self._on_select_track(silent=True)
                    break
        last_synth = self.state.get("last_synth")
        if last_synth:
            for i, s in enumerate(self.library["synths"]):
                if s["id"] == last_synth:
                    self.dd_synth.current(i)
                    self._on_select_synth()
                    return
        for i, s in enumerate(self.library["synths"]):
            if s.get("name", "").endswith("_Priority3_ADSR"):
                self.dd_synth.current(i)
                self._on_select_synth()
                return

    def _on_quit(self) -> None:
        save_state({
            "last_game": self.game_slug,
            "last_track_idx": self.track_idx,
            "last_synth": self.synth_key,
            "last_knobs": self.knobs,
        })
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    Launcher(root)
    root.mainloop()


if __name__ == "__main__":
    main()
