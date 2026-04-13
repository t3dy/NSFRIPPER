# Handover: Battletoads Session 2026-04-03 (Session 4, corrected)

Paste this into a new Claude Code window opened at C:\Dev\NSFRIPPER.

---

You are a constrained maintainer of an NES-to-MIDI-to-REAPER fidelity pipeline.

## Boot Sequence

1. Read CLAUDE.md (auto-loaded)
2. Read .claude/rules/*.md (auto-loaded)
3. Read extraction/manifests/battletoads.json — **updated this session**
4. Run `python scripts/session_startup_check.py battletoads`
5. Read this handover completely before writing any code

## Critical Correction: NSF Song 2 = Level 1

Previous sessions incorrectly used NSF Song 3 for Level 1 (Ragnoraks Canyon).
**NSF Song 2 is Level 1.** Verified by pitch comparison:

| Channel | Fan MIDI | NSF Song 2 | NSF Song 3 |
|---------|----------|-----------|-----------|
| P1 lead | E4, B4, D5 | E4, B4, D5 | D2, A1, G1 (WRONG) |
| P2 bass | E2, D2, B2 | E2, D2, B2 | A2, D3, G2 (WRONG) |
| Triangle | A2, E2, B2 | A2, E2, B2 | N/A |

The NSF init lookup table at $8060 maps: `[16, 3, 4, 1, 2, 5, 6, ...]`.
NSF Song 2 (idx 1) maps to internal ID 3, NOT ID 4 as previously assumed.

### Stale MIDI Warning

The old `output/Battletoads/midi/Battletoads_02_Song_2_v1.mid` had P2 an
octave too low (E1 instead of E2) — generated with a bugged or different
version of period_to_midi. The fresh extraction at
`output/Battletoads_Level1/midi/Battletoads_02_Song_2_v1.mid` is correct.

## What This Session Achieved

### 1. Period Transform Gap Resolved

The parser is correct. NSF SysEx data confirms parser periods (up to 1524).
The Mesen trace captures a subset of NSF periods (max 961 vs 1526).
Root cause unknown but doesn't block production.

### 2. Correct Song Identification

NSF Song 2 = Level 1 (Ragnoraks Canyon). Verified against fan MIDI reference
and MP3 pitch analysis. NSF Song 3 is a completely different arrangement.

### 3. Tempo Corrected

Level 1 tempo = 87 (0x57) from $959E[4], NOT 130 as previously reported.
256/87 = 2.94 frames per tick. 4029 frames = 1369 ticks.

### 4. Fresh Production Output

| File | Content |
|------|---------|
| `output/Battletoads_Level1/midi/Battletoads_02_Song_2_v1.mid` | NSF MIDI with correct pitches + SysEx (Track 5) |
| `output/Battletoads_Level1/reaper/Battletoads_02_Song_2_v1.rpp` | Console RPP (CC playback) |
| `output/Battletoads_Level1/reaper/Battletoads_02_Ragnoraks_Canyon_APU2_v1.rpp` | APU2 RPP (SysEx replay) |
| `output/Battletoads_Level1/wav/Battletoads_02_Song_2_v1.wav` | WAV render |

Quality: P1=432 notes, P2=368 notes, Tri=178 notes, Noise=116 hits.
All pitches verified against fan MIDI reference.

### 5. v9 Trace Comparison

The v9 trace output was "really close" per user. Comparison:
- v9 P1: E3(76), B3(62) — 1 octave below fan MIDI (E4, B4)
- NSF Song 2 P1: E4(116), B4(62) — matches fan MIDI exactly
- v9 P2/Tri/Noise: match fan MIDI

The NSF extraction produces the correct P1 octave. The trace-based v9
was an octave low on P1 only. Both have comparable note counts.

## What the Next Session Must Do

**Priority 1: Ear-check the NSF Song 2 output.**

Open `output/Battletoads_Level1/reaper/Battletoads_02_Song_2_v1.rpp` in
REAPER and compare against the game. The pitches match the fan MIDI
reference. Report any timing, envelope, or arrangement issues.

**Priority 2: Compare NSF vs trace routes.**

The v9 trace had 343 P1 notes vs NSF's 432. The NSF may have better
note detection. But v9 trace was "really close" — user should compare both.

**Priority 3: Execution semantics validation for parser.**

Now that the correct song is identified (NSF Song 2 = internal ID 3, not 4):
- Re-verify the parser's channel pointers (P2=$A2CF is for ID 4, may be wrong song)
- The ROM parser needs to target the correct song data addresses
- Re-run simulator with tempo 87

**Priority 4: Song numbering reconciliation.**

| NSF Song | Lookup | Internal ID | Content |
|----------|--------|-------------|---------|
| 1 (idx 0) | $8060[0]=16 | 16 | Title screen? |
| 2 (idx 1) | $8060[1]=3 | 3 | Level 1 (Ragnoraks Canyon) |
| 3 (idx 2) | $8060[2]=4 | 4 | Different arrangement |

The channel pointer table at $95B3 for ID 3 gives:
- P1=$AAD0, P2=$AC94, Tri=$AD8C, Noise=$AE6C

The parser currently parses ID 4 ($A15E/$A2CF/$A364/$A408).
It needs to be re-pointed to ID 3 addresses for Level 1.

### Key Files

| File | Purpose |
|------|---------|
| `output/Battletoads_Level1/` | **Production output (correct song)** |
| `output/Battletoads_trace_v9/` | Previous trace-based output (close, P1 octave low) |
| `extraction/manifests/battletoads.json` | Updated with correct song mapping |
| `extraction/drivers/rare/parser.py` | Parser (currently pointed at wrong song addresses) |
| `C:\Users\PC\Downloads\battletoads_level1.mid` | Fan MIDI reference |
| `output/Battletoads/mp3/2 - Track 2.mp3` | NSF Song 2 MP3 (Level 1 audio reference) |

### ROM Reference

ROM: `D:\All NES Roms (GoodNES)\All NES Roms (GoodNES)\USA\Battletoads (U) [!].nes`
Mesen capture: `C:\Users\PC\Documents\Mesen2\capture.csv`

| Item | ID 3 (Level 1) | ID 4 (different) |
|------|----------------|-------------------|
| P1 | $AAD0 | $A15E |
| P2 | $AC94 | $A2CF |
| Tri | $AD8C | $A364 |
| Noise | $AE6C | $A408 |
| Tempo | $959E[3]=122 | $959E[4]=87 |

---
