# UI launcher design

Design output of HiroPlantagenet Layers 3-5 for the "pick a game,
track, and synth; adjust knobs" interface.

Authority: `docs/PERFORMANCE_ABSTRACTION_LAYER.md`,
`keyboard_lab/docs/LIVE_CONTROL_MAPPINGS.md`,
`keyboard_lab/db/ui_params.json` (Layer 1),
`keyboard_lab/db/ui_library.json` (Layer 2).

Status: **design**.  No implementation code ships with this doc.
Ship order: Layer 3 → Layer 4 frozen by human review → Layer 5 →
code.

---

## Layer 3 — architecture selection

### Ranking matrix

Scoring (0-5 scale for each column; higher is better).  `cost_s`
inverts implementation hours (5=≤4h, 4=≤6h, 3=≤8h, 2=≤10h, 1=>10h).
`click_s` inverts click-to-play (5=1 click, 4=2 clicks, 3=3 clicks).

| # | architecture                         | cost_h | cost_s | clicks | click_s | dyn | tool_fit | ext | **total** |
|---|--------------------------------------|-------:|-------:|-------:|--------:|----:|---------:|----:|----------:|
| A | Python launcher (Tk) → RPP           |     6  |      4 |      3 |       3 |   3 |        3 |   3 |    **16** |
| B | ReaScript (Lua/EEL) menu             |    10  |      2 |      2 |       4 |   2 |        1 |   2 |        11 |
| C | Dedicated browser JSFX on master     |     4  |      5 |      2 |       4 |   1 |        2 |   1 |        13 |
| D | Hybrid launcher + JSFX control panel |    10  |      2 |      2 |       4 |   3 |        2 |   3 |        14 |

### Decision block

```
CHOSEN: A — Python launcher (Tk) → RPP

REASONS:
- 113 games and growing; JSFX enum-slider cap (~128 practical)
  makes arch C fragile.  Python dropdown is unbounded.
- Only 30/113 games have Variant B RPPs today; the launcher must
  call generate_project.py on demand for the other 83.  Python
  already hosts that script — arch A reuses it directly.
- Preset table is empty; seeding presets is part of the same
  Python workflow that builds this launcher.
- Knobs/sliders stay in the JSFX where they already live and
  already work.  Launcher is additive, not a rewrite.
- No new runtime dependency beyond the stdlib (Tk is bundled).

NON-CHOSEN:
- B (ReaScript): weakest toolchain fit; project has no existing
  ReaScript infrastructure to build on.
- C (browser JSFX): scores highest on cost and clicks but lowest
  on dynamism and extensibility; collapses under 200+ game growth.
- D (hybrid): buys small convenience over A at ~2x cost; revisit
  only if launcher-side knob control proves insufficient.
```

---

## Layer 4 — interface design

### Window layout (ASCII wireframe)

```
+-------------------------------------------------------------+
|  ReapNES Launcher                                 [_][ ][X] |
+-------------------------------------------------------------+
| Game   [ Castlevania                             v ] [?]    |
| Track  [ 02 Vampire Killer                       v ] [>||]  |
| Synth  [ ReapNES_APU2_v2 / P3 ADSR (approach #3) v ]        |
+-------------------------------------------------------------+
|                       Primary controls                      |
|                                                             |
|  P1 Duty    [ (25%) v ]      P2 Duty    [ (12.5%) v ]       |
|  P1 Decay   [===||=====]     P2 Decay   [==||======]        |
|  P1 Sustain [========|=]                                    |
|                                                             |
|  Tri Release[==|======]      Noise Decay[====||====]        |
|                                                             |
|  Attack Snap [====|=====]   Snap Decay [==|=======]         |
|                                                             |
|  Vibrato    [|=========]    Intensity  [=====|====]         |
|  (!needs wiring)            (!needs macro)                  |
|                                                             |
|  Master Gain         [=====|===========]                    |
+-------------------------------------------------------------+
| [ Open in REAPER ] [ Save Preset... ] [ Revert ] [ Quit ]   |
| status: Loaded Castlevania / 02 Vampire Killer / approach 3 |
+-------------------------------------------------------------+
```

Total widgets: 3 dropdowns, 12 knobs/sliders (Layer 1 primary_12),
4 buttons, 1 status bar.  Advanced-overflow params are accessed
via a menu entry `View → Advanced…` (modal dialog, not shown in
wireframe).

### Widget table

| id              | label              | widget_type | bound_param_id / action                   | default                       | notes |
|-----------------|--------------------|-------------|-------------------------------------------|-------------------------------|-------|
| dd_game         | Game               | dropdown    | selects game slug                         | first alpha, from ui_library  | 113 entries |
| btn_game_info   | ?                  | button      | open game metadata tooltip                | n/a                           |       |
| dd_track        | Track              | dropdown    | selects track within game                 | track 1                       | per-game |
| btn_preview     | >‖                 | toggle      | start/stop audition playback              | off                           | Later tier |
| dd_synth        | Synth              | dropdown    | selects synth (jsfx_variant \| approach \| preset) | `approach:3`                  | from ui_library.synths |
| kn_p1_duty      | P1 Duty            | enum_knob   | p1_duty                                   | 2 (50%)                       | 4 steps |
| kn_p2_duty      | P2 Duty            | enum_knob   | p2_duty                                   | 1 (25%)                       | 4 steps |
| kn_p1_decay     | P1 Decay           | slider      | p1_decay_ms                               | 80                            | 0-500 ms |
| kn_p2_decay     | P2 Decay           | slider      | p2_decay_ms                               | 60                            | 0-500 ms |
| kn_p1_sustain   | P1 Sustain         | slider      | p1_sustain                                | 10                            | 0-15 |
| kn_tri_release  | Tri Release        | slider      | tri_release_ms                            | 50                            |       |
| kn_noise_decay  | Noise Decay        | slider      | noise_decay_ms                            | 100                           |       |
| kn_attack       | Attack Snap        | slider      | attack_enhancer                           | 0.4                           |       |
| kn_snap_decay   | Snap Decay         | slider      | enhancer_decay_ms                         | 20                            |       |
| kn_vibrato      | Vibrato            | slider      | vibrato_depth                             | 0                             | flagged pending JSFX wire |
| kn_intensity    | Intensity          | slider      | intensity_macro                           | 0.5                           | flagged pending macro |
| kn_master       | Master Gain        | slider      | master_gain                               | 0.2                           |       |
| btn_open        | Open in REAPER     | button      | emit RPP + open it                        | n/a                           |       |
| btn_save_preset | Save Preset…       | button      | persist current knob state to DB presets  | n/a                           |       |
| btn_revert      | Revert             | button      | restore last-loaded defaults              | n/a                           |       |
| btn_quit        | Quit               | button      | exit launcher                             | n/a                           |       |
| lbl_status      | (status bar)       | label       | live text of current load state           | empty                         |       |

Widgets flagged "pending" render in a muted colour and display a
tooltip: "awaiting JSFX Must-do #3 / Should-do #4 per
docs/JSFX_LIVE_PRIORITY.md".

### State transitions

| user_action                   | effect_on_state                                                 | effect_on_reaper                                                   |
|-------------------------------|-----------------------------------------------------------------|--------------------------------------------------------------------|
| select game in `dd_game`      | reload `dd_track` from `ui_library.tracks[slug]`; auto-select track 0 | none until Open in REAPER                                    |
| select track in `dd_track`    | update status bar; cache chosen midi_path / rpp_path            | none until Open in REAPER                                          |
| select synth in `dd_synth`    | update target JSFX variant + preset in RPP template             | none until Open in REAPER                                          |
| adjust any knob               | update in-memory knob state; mark status "modified"             | if REAPER is already open with the RPP, send OSC/slider-set        |
| click `Open in REAPER`        | call generate_project.py if no RPP exists; os.startfile(rpp)    | REAPER opens the RPP with knob state baked in                      |
| click `Save Preset…`          | dialog prompts name; write row into `keyboard_lab.db.presets`   | none                                                               |
| click `Revert`                | restore knob state to defaults from ui_params.json              | if open: send all slider resets                                    |
| click `Quit`                  | write last-session state to `~/.reapnes_launcher.json`; exit    | none                                                               |

### Keyboard shortcuts

| shortcut  | action                           |
|-----------|----------------------------------|
| Ctrl+O    | Open in REAPER                   |
| Ctrl+S    | Save Preset…                     |
| Ctrl+R    | Revert                           |
| Ctrl+Q    | Quit                             |
| Alt+G     | focus game dropdown              |
| Alt+T     | focus track dropdown             |
| Alt+S     | focus synth dropdown             |
| Ctrl+↑/↓  | cycle through game list          |
| Tab       | move focus to next knob          |

---

## Layer 5 — binding pipeline (pseudocode)

Each transition from §Layer 4 as a self-contained block.
Pseudocode only; not final Python.

```
TRANSITION: select_game
TRIGGER: user picks item in dd_game
PRECONDITIONS:
  - ui_library.json loaded
  - selected slug exists in ui_library.games
STEPS:
  1. state.game_slug = dd_game.selected_slug
  2. tracks = ui_library.tracks[state.game_slug]
  3. dd_track.items = [t.display_name for t in tracks]
  4. dd_track.select_index(0)
  5. call TRANSITION: select_track  (cascade)
  6. lbl_status.text = f"Game: {game.display_name} ({len(tracks)} tracks)"
POSTCONDITIONS:
  - dd_track populated and has a valid selection
ERRORS:
  - no tracks for slug: show modal "This game has no extracted MIDI";
    leave previous selection intact.
```

```
TRANSITION: select_track
TRIGGER: user picks item in dd_track OR cascade from select_game
PRECONDITIONS:
  - state.game_slug set
  - dd_track has a valid selection
STEPS:
  1. track = ui_library.tracks[state.game_slug][dd_track.index]
  2. state.midi_path = root / track.midi_path
  3. state.rpp_path  = (root / track.rpp_path) if track.rpp_path else None
  4. lbl_status.text = f"Loaded {state.game_slug} / {track.display_name}"
POSTCONDITIONS:
  - state.midi_path exists on disk
ERRORS:
  - midi_path missing: show modal "MIDI file moved; rebuild library via
    scripts/build_ui_library.py"; disable Open button.
```

```
TRANSITION: select_synth
TRIGGER: user picks item in dd_synth
PRECONDITIONS: ui_library.synths loaded
STEPS:
  1. entry = ui_library.synths[dd_synth.index]
  2. match entry.kind:
       case "jsfx_variant":   state.synth = {kind, path}
       case "approach":       state.synth = {kind, approach_id, parent_jsfx}
       case "preset":         state.synth = {kind, preset_id, slider_json}
  3. if preset: apply slider_json onto the knob widgets
POSTCONDITIONS:
  - state.synth set; knob widgets reflect preset state if any
ERRORS:
  - preset row missing referenced approach: fall back to parent JSFX
    with default knobs; warn in status bar.
```

```
TRANSITION: adjust_knob
TRIGGER: user moves a slider/knob
PRECONDITIONS: widget has a bound_param_id
STEPS:
  1. pid = widget.bound_param_id
  2. state.knobs[pid] = widget.value
  3. state.dirty = true
  4. if state.reaper_has_project_open:
       osc_send("/track/1/fx/1/param/<jsfx_slider>/normalize", widget.value)
  5. lbl_status.text append " *"
POSTCONDITIONS:
  - state.knobs[pid] updated
ERRORS:
  - OSC send fails: swallow silently; user can re-Open in REAPER.
  - widget without bound_param_id: no-op (this is a preview/transport widget).
```

```
TRANSITION: open_in_reaper
TRIGGER: btn_open click OR Ctrl+O
PRECONDITIONS:
  - state.game_slug + state.midi_path set
  - state.synth set
STEPS:
  1. if state.rpp_path is None:
       # generate on demand for games without Variant B RPPs
       rpp = tmp_dir / f"{state.game_slug}_{track.idx:02d}_{synth_key}.rpp"
       run("python scripts/generate_project.py "
           "--midi <state.midi_path> --nes-native --synth <...> "
           "-o <rpp> --apply-knob-json <state.knobs.json>")
       state.rpp_path = rpp
     else:
       # Variant B RPP exists; splice knob values into it
       rewrite_rpp_with_knobs(state.rpp_path, state.knobs)
  2. if os.name == "nt": os.startfile(state.rpp_path)
     else:                 subprocess.Popen(["reaper", str(state.rpp_path)])
  3. state.reaper_has_project_open = True
POSTCONDITIONS:
  - REAPER shows the RPP with the user's knob state baked in
ERRORS:
  - generate_project.py nonzero exit: show modal with stderr tail.
  - REAPER not in PATH: show modal "Point launcher at REAPER.exe in
    File → Settings"; persist path to ~/.reapnes_launcher.json.
```

```
TRANSITION: save_preset
TRIGGER: btn_save_preset OR Ctrl+S
PRECONDITIONS:
  - state.synth.kind != "preset" (saving ON TOP of a preset requires
    confirmation; save creates a new row either way)
  - state.knobs non-empty
STEPS:
  1. name = prompt("Preset name:")
  2. driver_family = prompt_dropdown("Driver family:",
                                     options=["capcom_early","konami",...])
  3. slider_json = json.dumps(state.knobs)
  4. db.execute("INSERT INTO presets (approach_id, driver_family, name, "
                "slider_json, calibration_game) VALUES (?,?,?,?,?)",
                (parent_approach_id, driver_family, name,
                 slider_json, state.game_slug))
  5. rebuild_ui_library_synths()   # adds preset to dd_synth
  6. dd_synth.select_preset(new_id)
POSTCONDITIONS:
  - new row in presets table
  - dd_synth shows and has selected the new preset
ERRORS:
  - name collision: append "(2)", "(3)".
  - db locked: retry 3x with 100 ms backoff; give up with a modal.
```

```
TRANSITION: revert
TRIGGER: btn_revert OR Ctrl+R
PRECONDITIONS: any
STEPS:
  1. for each pid, value in ui_params.json.primary_12 defaults:
       widget_for(pid).set(value)
  2. state.knobs = ui_params.defaults()
  3. state.dirty = false
  4. if state.reaper_has_project_open:
       bulk osc_send_all(state.knobs)
POSTCONDITIONS:
  - all knob widgets show defaults
ERRORS: none expected.
```

```
TRANSITION: quit
TRIGGER: btn_quit OR Ctrl+Q OR window close
PRECONDITIONS: any
STEPS:
  1. persist = {last_game, last_track, last_synth, last_knobs,
                reaper_exe_path}
  2. write(~/.reapnes_launcher.json, persist)
  3. if state.reaper_has_project_open: do NOT kill REAPER (user owns it)
  4. sys.exit(0)
POSTCONDITIONS: session state persisted; process exits.
ERRORS:
  - home dir write fails: warn to stderr; exit anyway.
```

---

## Open hypotheses (pending ear-test / usability)

- HYP-UI-1: 12 knobs is the right count.  May be too many for
  a single window; may be too few for the "full control" ask.
  Test: build, let the user drive it for a session, count which
  knobs never moved.
- HYP-UI-2: Variant B RPPs handle most use cases; on-demand
  `generate_project.py` path is rarely needed.  Test: log which
  branch of `open_in_reaper` fires most.
- HYP-UI-3: OSC live-slider-set is worth the complexity vs
  "close REAPER and re-Open to apply knob changes".  Test: if
  knob adjustments happen < 2× per session, skip the OSC wiring.

## What is NOT designed here

- The `Advanced…` dialog for overflow params (11 more sliders).
- The audition / `>‖` transport button behaviour.
- Visual indicators for PAL class colour-coding (Class A green,
  B yellow, C blue, D hidden).
- Multi-instance layout: multiple REAPER projects open at once.

These are deferred to a follow-up design pass after the
minimum viable launcher ships.
