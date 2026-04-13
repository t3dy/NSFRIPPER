# Wizards & Warriors Evidence DB Guide

Database file: `C:\Dev\NSFRIPPER\extraction\analysis\reconciled\ww_evidence_db.json`

## What it contains

- `sources`: canonical file inputs and artifact paths
- `tracks`: song names and channel stream pointers
- `command_handlers`: command opcodes, handler addresses, and current meaning status
- `known_locations`: ROM/RAM locations with certain or partial meaning
- `mysterious_locations`: unresolved handlers/locations with next-test suggestions
- `title_parser_events`: title parser event stream with frame starts, periods, durations, MIDI notes
- `title_midi_notes`: note spans from the current title MIDI artifact
- `title_articulation_frames`: frame-level attack/retrigger evidence for the title phrase window
- `evidence_notes`: high-level claims worth preserving

## Suggested investigation loop

1. Pick the highest-priority row in `mysterious_locations`.
2. Find matching `command_handlers` or `known_locations` rows by address.
3. Compare affected frames in `title_parser_events` and `title_articulation_frames`.
4. Promote a mystery to `partial` or `verified` only when ROM/parser/write/trace evidence agree.

## Immediate top mysteries

- `triangle_release` at `triangle_gate`: effective release/damping state still missing beyond attack truth (next: infer frame-level release classes from MP3 + write/trace evidence)
- `cmd_0A` at `0xEF54`: single-byte write into the pulse control shadow $07C0,X; current evidence suggests it changes duty/constant-volume/volume nibble without touching sibling shadow bytes (next: decode argument families into specific duty and volume-bit changes, then compare with audible pulse timbre shifts)
- `pulse2_timbre_softening` at `pulse2_output_path`: stepped volume softening is known; remaining softness may need output-stage or articulation details (next: separate output filter effects from attack envelope effects)