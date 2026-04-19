#!/usr/bin/env python3
"""Thin wrapper: invoke the proven generate_project.py with --full-apu,
then swap APU2 -> APU2_v2 plugin name.

Why this exists:
An earlier pass hand-rolled a minimal RPP template here and got bitten
by two separate REAPER parse errors (NOTES block syntax, MASTERNCHAN
token). The existing generate_project.py already emits RPPs that REAPER
accepts without warnings — it has --full-apu mode AND uses the full,
tested REAPER header. Always reuse it instead of rolling new templates.
See .claude/rules/reaper_projects.md rule "RPP template reuse".

Usage:
    python scripts/make_full_apu_rpp.py <input.mid> --out <output.rpp>
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('midi', type=Path, help='source MIDI file')
    ap.add_argument('--out', type=Path, required=True, help='output RPP')
    ap.add_argument('--plugin', default='ReapNES_APU2_v2',
                    help='plugin short name (without .jsfx)')
    args = ap.parse_args()

    if not args.midi.is_file():
        print(f'ERROR: MIDI not found: {args.midi}', file=sys.stderr)
        return 1

    # Step 1: generate the RPP via the proven emitter.
    cmd = [
        sys.executable, 'scripts/generate_project.py',
        '--midi', str(args.midi),
        '--nes-native',
        '--synth', 'apu2',
        '--full-apu',
        '-o', str(args.out),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode

    # Step 2: swap plugin name APU2 -> APU2_v2 so the envelope/linear
    # counter fixes are active.
    args.out.write_text(
        args.out.read_text(encoding='utf-8').replace(
            'ReapNES_APU2.jsfx', args.plugin + '.jsfx'),
        encoding='utf-8',
    )
    print(f'Wrote {args.out} (plugin: {args.plugin})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
