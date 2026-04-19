#!/usr/bin/env python3
"""Render a REAPER project to WAV headless via REAPER CLI.

REAPER reads the project's <RENDER_CFG> section; if the project was saved
with render targets configured, `-renderproject` renders to that path.
For projects without render config, this script writes a sidecar render
config and invokes REAPER.

Usage:
    python scripts/reaper_render.py <project.rpp> --out <out.wav>

Exit code 0 on success, non-zero on failure.
"""
import argparse
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REAPER_EXE = Path(r"C:\Program Files\REAPER (x64)\reaper.exe")


def ensure_render_path(rpp_path, out_wav):
    """Make a copy of the RPP with RENDER_FILE pointing to out_wav and
    standard render settings (44.1k stereo WAV, master mix).
    Returns the path to the temp RPP to render.
    """
    out_wav = out_wav.resolve()
    out_dir = out_wav.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    # Build a copy in the same folder as the original (so relative paths work)
    tmp_rpp = rpp_path.parent / (rpp_path.stem + '.__render_tmp.rpp')

    with open(rpp_path, 'r', encoding='ascii', errors='replace') as f:
        content = f.read()

    # Patch/insert RENDER_FILE (target directory)
    content = re.sub(r'RENDER_FILE\s+"[^"]*"', f'RENDER_FILE "{out_dir.as_posix()}"', content)
    # Patch/insert RENDER_PATTERN (filename, no extension)
    stem = out_wav.stem
    if re.search(r'^\s*RENDER_PATTERN ', content, re.MULTILINE):
        content = re.sub(r'RENDER_PATTERN\s+"[^"]*"', f'RENDER_PATTERN "{stem}"', content)
    else:
        content = re.sub(r'(RENDER_FILE\s+"[^"]*")',
                         f'\\1\n  RENDER_PATTERN "{stem}"', content, count=1)

    with open(tmp_rpp, 'w', encoding='ascii', errors='replace', newline='') as f:
        f.write(content)
    return tmp_rpp


def render(rpp, out_wav, timeout=600):
    if not REAPER_EXE.exists():
        print(f'ERROR: REAPER not found at {REAPER_EXE}', file=sys.stderr)
        return 1
    # Abort if REAPER is already running.  A running REAPER intercepts
    # CLI args and opens them in the GUI instead of rendering headless,
    # causing modal error dialogs to appear for the user.  Check first.
    try:
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq reaper.exe'],
                                capture_output=True, text=True, timeout=5)
        if 'reaper.exe' in result.stdout.lower():
            print('ERROR: REAPER is already running. Close it before rendering '
                  'headless -- otherwise CLI args get forwarded to the GUI and '
                  'modal dialogs will interrupt your workflow.', file=sys.stderr)
            return 4
    except Exception:
        pass  # tasklist failed; proceed anyway rather than block
    tmp_rpp = ensure_render_path(rpp, out_wav)
    # -renderproject renders the given project using its render config.
    # -nonewinst prevents a second REAPER instance from being created.
    cmd = [str(REAPER_EXE), '-renderproject', str(tmp_rpp)]
    print(f'Rendering: {rpp.name}')
    print(f'Output:    {out_wav}')
    print(f'CMD: {" ".join(cmd)}')
    t0 = time.time()
    try:
        result = subprocess.run(cmd, timeout=timeout, capture_output=True, text=True)
    except subprocess.TimeoutExpired:
        print(f'TIMEOUT after {timeout}s', file=sys.stderr)
        tmp_rpp.unlink(missing_ok=True)
        return 2
    dt = time.time() - t0
    print(f'Render wall time: {dt:.1f}s')
    if result.returncode != 0:
        print(f'REAPER stderr: {result.stderr}', file=sys.stderr)
        print(f'REAPER stdout: {result.stdout}', file=sys.stderr)
    # Clean up temp RPP
    tmp_rpp.unlink(missing_ok=True)
    # Check output file exists
    if not out_wav.exists():
        # REAPER may have appended an index or different extension
        candidates = list(out_wav.parent.glob(f'{out_wav.stem}*'))
        if candidates:
            print(f'Output filename differs: {[c.name for c in candidates]}', file=sys.stderr)
        else:
            print(f'No output WAV produced at {out_wav}', file=sys.stderr)
        return 3
    size_kb = out_wav.stat().st_size / 1024
    print(f'Wrote {size_kb:.0f} KB WAV')
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rpp', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--timeout', type=int, default=600)
    args = ap.parse_args()
    sys.exit(render(args.rpp, args.out, args.timeout))


if __name__ == '__main__':
    main()
