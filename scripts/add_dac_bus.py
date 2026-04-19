#!/usr/bin/env python3
"""Post-process a generated multi-track NES REAPER project to add a
hardware-accurate NES DAC bus track.

Strategy (avoids master-FX block syntax issues that broke earlier attempts):
  1. Identify the NES channel tracks in the RPP by name (NES - Pulse 1 etc.)
  2. Change each channel's MAINSEND to 0 so it does not bypass the bus
  3. Pan pulses hard LEFT (-1), TND (triangle/noise/DMC) hard RIGHT (+1)
  4. Insert a new "NES DAC Bus" track at the end
  5. Bus track has AUXRECV lines from each channel track, with per-channel
     volume set to match hardware TND DAC weights (pulses vol=1; tri=0.00365;
     noise=0.00245; dmc=0.01122)
  6. Bus track has NES_MasterMixer JSFX + MAINSEND 1 (routes to master)

Result:
  - Channel tracks remain fully editable (mute/solo/FX/automation all work)
  - Bus L input = P1 + P2 linear sum = hardware S/30
  - Bus R input = tri/8227 + noise/12241 + dmc/22638 (thanks to AUXRECV vols)
  - Bus JSFX applies the correct nonlinear DAC transfer per pin
  - Master output = pulse_dac(L) + tnd_dac(R), matching NES two-DAC-pin topology

Usage:
    python scripts/add_dac_bus.py <input.rpp> [--out <output.rpp>]
"""
import argparse
import re
import uuid
from pathlib import Path


CHANNEL_NAME_PATTERNS = {
    "pulse1":   re.compile(r'NAME "NES - Pulse 1', re.IGNORECASE),
    "pulse2":   re.compile(r'NAME "NES - Pulse 2', re.IGNORECASE),
    "triangle": re.compile(r'NAME "NES - Triangle', re.IGNORECASE),
    "noise":    re.compile(r'NAME "NES - (Noise|Drums)', re.IGNORECASE),
    "dmc":      re.compile(r'NAME "NES - DMC', re.IGNORECASE),
}

# Pan per channel (REAPER pan: -1 = hard left, +1 = hard right)
# Pulses -> bus L, TND -> bus R
PAN_MAP = {
    "pulse1": -1.0, "pulse2": -1.0,
    "triangle": 1.0, "noise": 1.0, "dmc": 1.0,
}

# AUXRECV volume = per-channel hardware weight
# Pulses: unweighted. TND: each weighted so their sum represents W exactly.
# Rationale: NES DAC formula is W = tri/8227 + noise/12241 + dmc/22638.
# If each per-channel audio output peaks at 0.5 for NES vol=15 (or dmc=127),
# setting AUXRECV vol = 30/weight for tri/noise (30 = 2*15) and 254/weight
# for dmc (254 = 2*127) makes audio_R equal W in audio units.
WEIGHT_MAP = {
    "pulse1": 1.0, "pulse2": 1.0,
    "triangle": 30.0 / 8227.0,     # 0.00365
    "noise":    30.0 / 12241.0,    # 0.00245
    "dmc":      254.0 / 22638.0,   # 0.01122
}


def make_guid():
    return "{" + str(uuid.uuid4()).upper() + "}"


def find_tracks(rpp_text):
    """Return list of (track_start_pos, track_end_pos, channel_key) for each
    NES channel track found. track_end is position just after closing '>'."""
    tracks = []
    # Find all <TRACK blocks. Can't use simple regex because blocks nest.
    # Walk char-by-char counting < and > within <TRACK ... > structure.
    i = 0
    while True:
        m = re.search(r'^  <TRACK ', rpp_text[i:], re.MULTILINE)
        if not m:
            break
        abs_start = i + m.start()
        # Find matching closing '>' at indent level 2 (2 spaces)
        # Look for next "^  >" at same indent
        end_m = re.search(r'^  >\s*$', rpp_text[abs_start + len(m.group(0)):], re.MULTILINE)
        if not end_m:
            break
        abs_end = abs_start + len(m.group(0)) + end_m.end()
        block = rpp_text[abs_start:abs_end]
        # Identify channel
        key = None
        for k, pat in CHANNEL_NAME_PATTERNS.items():
            if pat.search(block):
                key = k
                break
        tracks.append((abs_start, abs_end, key))
        i = abs_end
    return tracks


def patch_channel_track(block, channel_key):
    """Change MAINSEND 1 -> 0, and pan to L/R based on channel."""
    # Change MAINSEND to 0
    block = re.sub(r'^(\s*)MAINSEND\s+1\s+0\s*$',
                   r'\1MAINSEND 0 0',
                   block, flags=re.MULTILINE)
    # Change VOLPAN: "VOLPAN 1 0 -1 -1 1" -> "VOLPAN 1 <pan> -1 -1 1"
    pan = PAN_MAP.get(channel_key, 0.0)
    block = re.sub(r'^(\s*VOLPAN)\s+\S+\s+\S+(\s+.*)$',
                   fr'\g<1> 1 {pan}\g<2>',
                   block, flags=re.MULTILINE, count=1)
    return block


def build_bus_track(tracks_info, bus_track_idx):
    """Build the NES DAC Bus track block with AUXRECV from each channel."""
    guid = make_guid()
    fxid = make_guid()
    item_guid = make_guid()
    lines = []
    lines.append(f"  <TRACK {guid}")
    lines.append('    NAME "NES DAC Bus (Hardware Mix)"')
    lines.append("    PEAKCOL 11546867")   # distinctive color
    lines.append("    BEAT -1")
    lines.append("    AUTOMODE 0")
    lines.append("    PANLAWFLAGS 3")
    lines.append("    VOLPAN 1 0 -1 -1 1")
    lines.append("    MUTESOLO 0 0 0")
    lines.append("    IPHASE 0")
    lines.append("    PLAYOFFS 0 1")
    lines.append("    ISBUS 0 0")
    lines.append("    BUSCOMP 0 0 0 0 0")
    lines.append("    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0")
    lines.append("    FIXEDLANES 9 0 0 0 0")
    lines.append("    SEL 0")
    lines.append("    REC 0 0 1 0 0 0 0 0")
    # AUXRECV from each channel: src_track_idx, mode=0 (post-fader), vol, pan=0,
    # mute=0, mono=0, midi_src=0, midi_dst=0, auto_mute=0, src_chan=0, dst_chan=0
    for src_idx, key in tracks_info:
        vol = WEIGHT_MAP.get(key, 1.0)
        lines.append(f"    AUXRECV {src_idx} 0 {vol:.6f} 0 0 0 0 0 0 0 0")
    lines.append("    VU 2")
    lines.append("    TRACKHEIGHT 0 0 0 0 0 0 0")
    lines.append("    INQ 0 0 0 0.5 100 0 0 100")
    lines.append("    NCHAN 2")
    lines.append("    FX 1")
    lines.append(f"    TRACKID {guid}")
    lines.append("    PERF 0")
    lines.append("    MIDIOUT -1")
    lines.append("    MAINSEND 1 0")  # bus -> master
    lines.append("    <FXCHAIN")
    lines.append("      WNDRECT 24 52 700 560")
    lines.append("      SHOW 0")
    lines.append("      LASTSEL 0")
    lines.append("      DOCKED 0")
    lines.append("      BYPASS 0 0 0")
    lines.append('      <JS "ReapNES Studio/NES_MasterMixer.jsfx" ""')
    lines.append('        1.500000 1.000000 1.000000 0 1 - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
    lines.append("      >")
    lines.append("      FLOATPOS 0 0 0 0")
    lines.append(f"      FXID {fxid}")
    lines.append("      WAK 0 0")
    lines.append("    >")
    lines.append("  >")
    return "\n".join(lines) + "\n"


def process_rpp(text):
    tracks = find_tracks(text)
    channel_tracks = [(i, t) for i, t in enumerate(tracks) if t[2] is not None]
    if not channel_tracks:
        raise SystemExit("No NES channel tracks found by name. Cannot process.")

    # Build patched text: iterate tracks in order, patch channel tracks inline.
    # Track indices in the final RPP order are the same as their order in
    # the source file (we don't reorder).
    patched = []
    last_end = 0
    tracks_info_for_bus = []  # (track_idx, channel_key) as seen in track order
    for idx, (start, end, key) in enumerate(tracks):
        patched.append(text[last_end:start])
        block = text[start:end]
        if key is not None:
            block = patch_channel_track(block, key)
            tracks_info_for_bus.append((idx, key))
        patched.append(block)
        last_end = end

    # Build bus track and insert after the last track but before the final ">"
    # of the REAPER_PROJECT block
    remaining = text[last_end:]
    # Find the final closing ">" (end of REAPER_PROJECT)
    m = re.search(r'\n>\s*\Z', remaining)
    if m:
        before_close = remaining[:m.start()]
        closing = remaining[m.start():]
    else:
        before_close = remaining
        closing = ""

    bus_track_idx = len(tracks)  # 0-indexed position of the new bus track
    bus = build_bus_track(tracks_info_for_bus, bus_track_idx)
    patched.append(before_close)
    if not before_close.endswith('\n'):
        patched.append('\n')
    patched.append(bus)
    patched.append(closing)
    return "".join(patched)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("rpp", type=Path, help="input RPP (will not be modified)")
    ap.add_argument("--out", type=Path, help="output RPP path (default: <input>_hwbus.rpp)")
    args = ap.parse_args()

    if not args.rpp.is_file():
        raise SystemExit(f"Not found: {args.rpp}")
    out = args.out or args.rpp.with_name(args.rpp.stem + "_hwbus.rpp")
    out.parent.mkdir(parents=True, exist_ok=True)

    text = args.rpp.read_text(encoding="utf-8")
    patched = process_rpp(text)
    out.write_text(patched, encoding="utf-8")

    # Sanity: count AUXRECV lines
    n_aux = patched.count("AUXRECV ")
    print(f"Wrote {out}")
    print(f"  AUXRECV lines: {n_aux}")


if __name__ == "__main__":
    main()
