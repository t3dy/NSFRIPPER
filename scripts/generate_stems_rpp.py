#!/usr/bin/env python3
"""Generate a REAPER project with per-channel hardware-accurate AUDIO stems
alongside the editable MIDI tracks.

The audio stems (rendered via scripts/render_channel_stems.py) come from
our Python render_wav() pipeline which matches libgme within 1.3 dB on
all spectral bands.  When played in REAPER, the 5 audio tracks sum
linearly on master -- sounds like the game.

The MIDI tracks remain alongside with the JSFX synth loaded.  User can
mute the audio track to hear the JSFX synth (for live keyboard play),
or mute the JSFX track to hear the hardware-accurate audio stem.

Track layout (top to bottom):
  1. [AUDIO] Pulse 1    (audio stem + optional MIDI track below)
  2. [MIDI]  Pulse 1 MIDI (for editing / keyboard play)
  3. [AUDIO] Pulse 2
  4. [MIDI]  Pulse 2 MIDI
  5. [AUDIO] Triangle
  6. [MIDI]  Triangle MIDI
  7. [AUDIO] Noise
  8. [MIDI]  Noise MIDI

Usage:
    python scripts/generate_stems_rpp.py \
      --midi <source.mid> --stems-dir <stems-folder> \
      --out <out.rpp>
"""
import argparse
import re
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from generate_project import (
    rpp_header, rpp_track, apu2_slider_values, JSFX_PLUGIN_APU2,
    CHANNEL_LABELS, COLORS, analyze_midi, midi_track_to_events,
)
from scipy.io import wavfile


def make_guid():
    return "{" + str(uuid.uuid4()).upper() + "}"


def audio_track(name, audio_path, length_seconds):
    guid = make_guid()
    item_guid = make_guid()
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
    FX 0
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


def get_wav_length(path):
    sr, d = wavfile.read(str(path))
    return len(d) / sr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--midi", type=Path, required=True)
    ap.add_argument("--stems-dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    # Analyze MIDI for tempo + per-channel events
    info = analyze_midi(args.midi)
    tempo = info["tempo_bpm"]
    stats = info["channel_stats"]

    # Stem files: one per channel (DMC optional - only if game uses it)
    stem_map = {
        "pulse1": args.stems_dir / "pulse1.wav",
        "pulse2": args.stems_dir / "pulse2.wav",
        "triangle": args.stems_dir / "triangle.wav",
        "noise": args.stems_dir / "noise.wav",
    }
    for key, path in stem_map.items():
        if not path.is_file():
            sys.exit(f"missing stem: {path}")
    # DMC is optional
    dmc_path = args.stems_dir / "dmc.wav"
    if dmc_path.is_file():
        stem_map["dmc"] = dmc_path
    length = get_wav_length(stem_map["pulse1"])

    # Build RPP
    lines = [rpp_header(tempo=tempo, title=f"{args.midi.stem} - stems+MIDI")]
    import mido as _mido
    mid = _mido.MidiFile(str(args.midi))
    roles = ["pulse1", "pulse2", "triangle", "noise"]
    if "dmc" in stem_map:
        roles.append("dmc")
    nes_ch = {"pulse1": 0, "pulse2": 1, "triangle": 2, "noise": 3, "dmc": 4}

    for role in roles:
        ch_idx = nes_ch[role]
        # 1. Audio track playing the hardware-accurate stem
        audio_name = f"[AUDIO] NES - {CHANNEL_LABELS[role]}"
        lines.append(audio_track(audio_name, stem_map[role], length))

        # 2. MIDI track with the JSFX synth (for editing + keyboard play)
        if ch_idx in stats and stats[ch_idx]["note_count"] > 0:
            # Pull this channel's MIDI events
            target_ch = ch_idx
            ch_track = None
            sysex_trk = None
            for t in mid.tracks:
                if any(hasattr(m, "channel") and m.channel == target_ch for m in t):
                    ch_track = t
                if any(m.type == "sysex" for m in t) and not any(
                    hasattr(m, "type") and m.type == "note_on" and hasattr(m, "channel") for m in t
                ):
                    sysex_trk = t
            events = midi_track_to_events(ch_track, sysex_track=sysex_trk) if ch_track else None

            vals = apu2_slider_values(game="", channel=role)
            # Keep MIDI track's audio muted by default (user hears stem, not JSFX)
            midi_name = f"[MIDI] NES - {CHANNEL_LABELS[role]}"
            midi_block = rpp_track(
                name=midi_name, color=COLORS[role], slider_values=vals,
                midi_length=length,
                armed=False, selected=False,
                jsfx_plugin=JSFX_PLUGIN_APU2,
                midi_events=events, ticks_per_beat=info["ticks_per_beat"],
            )
            # Default-mute the MIDI/JSFX track so user hears the stem audio by default
            midi_block = re.sub(r'    MUTESOLO 0 0 0', '    MUTESOLO 1 0 0', midi_block, count=1)
            lines.append(midi_block)

    lines.append(">")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.out}")
    print(f"  duration: {length:.1f}s, tempo: {tempo:.1f}")
    print(f"  tracks: 4 audio stems + 4 MIDI tracks (muted by default)")


if __name__ == "__main__":
    main()
