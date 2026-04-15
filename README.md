# NSFRIPPER — NES Music Extraction Studio

## [Browse the Game Library](https://t3dy.github.io/NSFRIPPER/)

> 321 games extracted | 8,900+ MIDI files | Per-frame APU fidelity | REAPER projects included

---

## What This Is

A complete pipeline for extracting music from NES games via NSF emulation,
producing 4-channel MIDI with per-frame volume/duty automation, plus REAPER
DAW projects with the ReapNES synthesizer plugin.

**Fully automated.** NSF files are emulated via a 6502 CPU running the
original sound driver. APU register writes are captured at 60 Hz and
converted to MIDI with CC11 (volume) and CC12 (duty cycle) automation
that preserves the original envelope shapes.

## The NES Sound Chip (RP2A03)

5 channels, all synthesized:

| Channel | Waveform | Volume | Special |
|---------|----------|--------|---------|
| **Pulse 1** | Square (4 duty cycles) | 4-bit (0-15) | Sweep unit |
| **Pulse 2** | Square (4 duty cycles) | 4-bit (0-15) | Sweep unit |
| **Triangle** | Fixed triangle | Gate only (on/off) | 1 octave lower than pulse |
| **Noise** | LFSR (2 modes) | 4-bit (0-15) | 16 pitch periods |
| **DMC** | 1-bit delta PCM | 7-bit (0-127) | Sample playback |

## Driver Families

Games are classified by how aggressively their sound driver controls the
APU per frame, measured by CC11/CC12 density in extracted MIDI:

| Family | CC11/note | Example Games | Character |
|--------|-----------|---------------|-----------|
| **Hardware Envelope** | 0.1-2.8 | Mega Man, DuckTales | Clean, simple decay |
| **Standard Envelope** | 3.5-5.6 | Castlevania, Contra, Ninja Gaiden | Expressive per-frame volume |
| **Duty Animators** | 3.7-4.9 | Super Mario Bros, Kirby | Volume + timbral animation |
| **Dense Automators** | 5.1-14.9 | Final Fantasy, Batman | Near-continuous volume stream |
| **Full Animation** | >7.0 both | Super Mario Bros 3 | Both axes at frame rate |

## Pipeline

```
NSF file → 6502 emulation → APU register capture → MIDI + CC automation → REAPER project
```

### Key Commands

```bash
# Batch extract all games
python scripts/batch_nsf_all.py

# Single game
python scripts/nsf_to_reaper.py <nsf> --all -o output/Game/

# Generate REAPER project from MIDI
python scripts/generate_project.py --midi <file> --nes-native -o <out>

# Classify game into driver family
python scripts/driver_survey.py --game <slug>

# Regenerate website
python scripts/generate_site.py
```

### Tools

| Script | Purpose |
|--------|---------|
| `nsf_to_reaper.py` | NSF emulation + MIDI/REAPER extraction |
| `batch_nsf_all.py` | Batch process all games |
| `generate_project.py` | MIDI to REAPER project (canonical RPP builder) |
| `trace_to_midi.py` | Mesen trace to MIDI (ROM-parsed games) |
| `driver_survey.py` | CC density classification into 5 families |
| `generate_site.py` | Rebuild GitHub Pages site |
| `expansion_detect.py` | Scan NSFs for expansion audio chips |

## Extraction Status

321 games with NSF files extracted to MIDI. 278 with REAPER projects.

ROM-parsed games with trace-level validation:

| Game | Status | Validation |
|------|--------|-----------|
| Castlevania 1 | Trusted | 0 pitch mismatches against Mesen trace |
| Contra | Trusted | Full ROM parse, all 11 tracks |
| Wizards & Warriors | Partial | 16 songs structural, title track trace-validated |

## Fidelity Hierarchy

1. **Mesen Trace** — APU register dumps from real gameplay. Ground truth.
2. **SysEx in MIDI** — Lossless register state encoding.
3. **NSF Emulation** — 6502 CPU runs the sound driver. Per-frame CC11/CC12.
4. **CC11/CC12 in MIDI** — Volume + duty envelope. Loses sweep, noise mode.
5. **ADSR Approximation** — Only for live keyboard when no file data exists.

## ANTIRIPPER Knowledge Base

The project includes an oracle-backed knowledge base (`ANTIRIPPER/`)
that tracks extraction decisions, prevention patterns, hardware facts,
and driver family classifications. Pipeline hooks automatically record
evidence and decisions for every extraction run.

## Project History

Started as Battletoads NES music reconstruction, grew into a universal
NES music extraction pipeline. The original work on Castlevania, Contra,
Battletoads, and Wizards & Warriors established the trace validation
methodology and the 5-family driver classification system.
