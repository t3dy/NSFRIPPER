#!/usr/bin/env python3
"""Add an audio track to an existing REAPER project, playing a reference WAV.

Useful when: the MIDI synth playback isn't matching the game accurately, but
we have a known-good rendered/captured audio file (e.g. from Zophar's Domain).
Insert the audio track so the project sounds right via the rendered audio,
while the MIDI tracks remain for editing / visual scores / live keyboard play.

Usage:
    python scripts/add_reference_audio_track.py <project.rpp> \
      --audio <reference.wav> [--name "Zophar reference"]
"""
import argparse
import re
import uuid
import sys
from pathlib import Path


def make_guid():
    return "{" + str(uuid.uuid4()).upper() + "}"


def build_audio_track(name, audio_path, length_seconds):
    guid = make_guid()
    item_guid = make_guid()
    # PCMSOURCE with WAV file
    return f"""  <TRACK {guid}
    NAME "{name}"
    PEAKCOL 25600
    BEAT -1
    AUTOMODE 0
    PANLAWFLAGS 3
    VOLPAN 1 0 -1 -1 1
    MUTESOLO 0 0 0
    IPHASE 0
    PLAYOFFS 0 1
    ISBUS 0 0
    BUSCOMP 0 0 0 0 0
    SHOWINMIX 1 0.6667 0.5 1 0.5 0 0 0
    FIXEDLANES 9 0 0 0 0
    SEL 0
    REC 0 0 1 0 0 0 0 0
    VU 2
    TRACKHEIGHT 0 0 0 0 0 0 0
    INQ 0 0 0 0.5 100 0 0 100
    NCHAN 2
    FX 1
    TRACKID {guid}
    PERF 0
    MIDIOUT -1
    MAINSEND 1 0
    <ITEM
      POSITION 0
      LENGTH {length_seconds:.6f}
      LOOP 0
      ALLTAKES 0
      FADEIN 0 0 0 0 0 0 0
      FADEOUT 0 0 0 0 0 0 0
      MUTE 0 0
      SEL 0
      IGUID {item_guid}
      IID 1
      NAME "{Path(audio_path).name}"
      VOLPAN 1 0 1 -1
      SOFFS 0
      PLAYRATE 1 1 0 -1 0 0.0025
      CHANMODE 0
      GUID {make_guid()}
      <SOURCE WAVE
        FILE "{Path(audio_path).resolve().as_posix()}"
      >
    >
  >
"""


def get_audio_length(path):
    from scipy.io import wavfile
    sr, data = wavfile.read(str(path))
    return len(data) / sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rpp', type=Path)
    ap.add_argument('--audio', type=Path, required=True)
    ap.add_argument('--name', default='Reference audio (original game render)')
    ap.add_argument('--out', type=Path)
    args = ap.parse_args()

    if not args.rpp.is_file() or not args.audio.is_file():
        sys.exit(f'missing: {args.rpp} or {args.audio}')

    out = args.out or args.rpp.with_name(args.rpp.stem + "_with_audio.rpp")
    text = args.rpp.read_text(encoding='utf-8')

    # Find insertion point: just BEFORE the first <TRACK
    m = re.search(r'^  <TRACK ', text, re.MULTILINE)
    if not m:
        sys.exit('no TRACK found')

    length = get_audio_length(args.audio)
    track_block = build_audio_track(args.name, args.audio, length)

    new_text = text[:m.start()] + track_block + text[m.start():]
    out.write_text(new_text, encoding='utf-8')
    print(f'Wrote {out}')
    print(f'  audio length: {length:.1f}s')
    print(f'  audio source: {args.audio}')


if __name__ == '__main__':
    main()
