#!/usr/bin/env python3
"""Generate V2-versioned REAPER projects for Wizards & Warriors that use
ReapNES_APU2_v2.jsfx (envelope simulator + triangle linear counter).

Strategy: take each existing W&W .rpp, find every <JS "ReapNES Studio/...jsfx"
block, replace the plugin name + slider string. Preserves per-track channel
mode so each track still renders its correct APU channel.

Output: output/Wizards_and_Warriors_v2/reaper/<name>_v2.rpp
Input:  output/Wizards_and_Warriors/reaper/<name>_v1.rpp

Run: python scripts/make_ww_v2_projects.py
"""
import re
import shutil
from pathlib import Path

SRC_DIR = Path("output/Wizards_and_Warriors/reaper")
DST_DIR = Path("output/Wizards_and_Warriors_v2/reaper")
DST_MIDI = Path("output/Wizards_and_Warriors_v2/midi")

OLD_PLUGIN_CONSOLE = 'ReapNES Studio/ReapNES_Console.jsfx'
OLD_PLUGIN_APU2 = 'ReapNES Studio/ReapNES_APU2.jsfx'
NEW_PLUGIN = 'ReapNES Studio/ReapNES_APU2_v2.jsfx'

# Console slider33 (index 32) = channel mode.  Console has 40 sliders total.
# APU2_v2 slider1 (index 0) = channel mode.     APU2_v2 has 21 sliders.
#
# APU2_v2 slider layout:
#   1=ch_mode, 2=kb_mode, 3-8=P1 duty/vol/ADSR, 9-14=P2 duty/vol/ADSR,
#   15-16=Tri ADSR, 17-18=Noise ADSR, 19=master_gain,
#   20=attack_enhancer, 21=enhancer_decay_ms
CONSOLE_CH_MODE_IDX = 32
APU2_V2_TEMPLATE = [
    4,                    # 1: Channel Mode (replaced per track)
    0,                    # 2: Keyboard Mode = OFF for file playback
    2, 15, 0, 80, 10, 100,  # 3-8: P1 duty=50%, vol=15, ADSR
    1, 15, 0, 60, 10, 80,   # 9-14: P2 duty=25%, vol=15, ADSR
    0, 50,                # 15-16: Tri attack=0, release=50ms
    0, 100,               # 17-18: Noise attack=0, decay=100ms
    0.8,                  # 19: Master gain
    0.4,                  # 20: Attack Enhancer (0 = pure hardware fidelity, 1 = max tink)
    20,                   # 21: Enhancer Decay ms
]
# Pad with dashes up to 60 slots (REAPER saves ~60 slider slots)
NUM_PAD_SLOTS = 60


def format_slider_line(ch_mode):
    """Build the slider-values line for a given channel mode (0-4)."""
    vals = list(APU2_V2_TEMPLATE)
    vals[0] = ch_mode
    # Format: ints stay int, floats get .6f
    parts = []
    for v in vals:
        if isinstance(v, int) or (isinstance(v, float) and v == int(v) and v.is_integer() and v <= 100):
            # keep ints as ints, floats that are exactly integer (like 20.0) ambiguous
            if isinstance(v, int):
                parts.append(str(v))
            else:
                parts.append(f"{v:.6f}" if v < 1 else str(int(v)))
        else:
            parts.append(f"{v:.6f}")
    # Explicit: keep 0.8 and 0.4 as floats
    parts[18] = f"{APU2_V2_TEMPLATE[18]:.6f}"  # master gain
    parts[19] = f"{APU2_V2_TEMPLATE[19]:.6f}"  # attack enhancer
    parts[20] = str(int(APU2_V2_TEMPLATE[20]))  # enhancer decay (int ms)
    # Pad remaining slots with dashes
    pad = ['-'] * (NUM_PAD_SLOTS - len(parts))
    return ' '.join(parts + pad)


def extract_ch_mode_from_console_line(line):
    """Parse the Console slider line and extract channel mode (position 33)."""
    # Line looks like:  "        2 15 1 10 ... 0.800000 <CH_MODE> 1 0 0 0 0 - - - ..."
    tokens = line.strip().split()
    if len(tokens) <= CONSOLE_CH_MODE_IDX:
        return 4
    try:
        return int(float(tokens[CONSOLE_CH_MODE_IDX]))
    except (ValueError, IndexError):
        return 4


def extract_ch_mode_from_apu2_line(line):
    """APU2 has ch_mode at slider1 (index 0)."""
    tokens = line.strip().split()
    if not tokens:
        return 4
    try:
        return int(float(tokens[0]))
    except (ValueError, IndexError):
        return 4


def rewrite_rpp(src_path, dst_path):
    """Read src, find JS plugin blocks, rewrite, and save to dst."""
    with open(src_path, 'r', encoding='ascii', errors='replace') as f:
        lines = f.readlines()

    out_lines = []
    i = 0
    plugins_replaced = 0
    while i < len(lines):
        line = lines[i]
        # Look for <JS "ReapNES Studio/XXX.jsfx" "" lines
        m = re.match(r'(\s*)<JS "ReapNES Studio/(ReapNES_\w+)\.jsfx" ""', line)
        if m and i + 1 < len(lines):
            indent = m.group(1)
            old_plugin_name = m.group(2)
            slider_line = lines[i + 1]
            # Extract channel mode
            if 'Console' in old_plugin_name:
                ch_mode = extract_ch_mode_from_console_line(slider_line)
            elif 'APU2' in old_plugin_name:
                ch_mode = extract_ch_mode_from_apu2_line(slider_line)
            else:
                ch_mode = 4
            # Emit new plugin + slider line
            out_lines.append(f'{indent}<JS "{NEW_PLUGIN}" ""\n')
            # Match the original slider line indent
            slider_indent_match = re.match(r'(\s*)', slider_line)
            slider_indent = slider_indent_match.group(1) if slider_indent_match else '        '
            out_lines.append(f'{slider_indent}{format_slider_line(ch_mode)}\n')
            i += 2
            plugins_replaced += 1
        else:
            out_lines.append(line)
            i += 1

    # Update the project title comment if present (optional cosmetic)
    src_name = src_path.stem
    # Rewrite "_v1" filename references in NOTES -> "_v2"
    content = ''.join(out_lines)
    content = content.replace(f'{src_name}', f'{src_name.replace("_v1", "_v2")}')

    with open(dst_path, 'w', encoding='ascii', errors='replace', newline='') as f:
        f.write(content)

    return plugins_replaced


def main():
    if not SRC_DIR.is_dir():
        print(f"ERROR: source not found: {SRC_DIR}")
        return

    DST_DIR.mkdir(parents=True, exist_ok=True)
    DST_MIDI.mkdir(parents=True, exist_ok=True)

    # Copy MIDI files (unchanged) so the v2 project folder is self-contained
    src_midi = Path("output/Wizards_and_Warriors/midi")
    for mf in src_midi.glob('*.mid'):
        new_name = mf.name.replace('_v1.mid', '_v2.mid')
        shutil.copy2(mf, DST_MIDI / new_name)

    rpps = sorted(SRC_DIR.glob('*.rpp'))
    print(f"Processing {len(rpps)} RPP files...")
    total_plugins = 0
    for rpp in rpps:
        new_name = rpp.name.replace('_v1.rpp', '_v2.rpp')
        dst = DST_DIR / new_name
        n = rewrite_rpp(rpp, dst)
        total_plugins += n
        print(f"  {rpp.name} -> {new_name}  ({n} plugins replaced)")

    print(f"\nDone. {len(rpps)} projects, {total_plugins} plugin instances replaced.")
    print(f"\nOpen any file in: {DST_DIR}")
    print(f"Try Song 3 first — has the most triangle overhang (3688 frames killed):")
    print(f"  {DST_DIR / 'Wizards_&_Warriors_03_Song_3_v2.rpp'}")


if __name__ == '__main__':
    main()
