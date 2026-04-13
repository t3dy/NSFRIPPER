# Wizards & Warriors Control Byte Pass 1

This pass answers one narrow question:

- what does `$07C0,X` really represent?
- and does command `0x0A` look like a plausible explanation for the title triangle release problem?

## Direct ROM Evidence

### `0x0A` handler

```text
EF54: INY
EF55: LDA ($C1),Y
EF57: STA $07C0,X
EF5A: INY
EF5B: JMP $EE4E
```

This is a one-byte write into `$07C0,X`.

### `0x04` handler

```text
EF5E: INY
EF5F: LDA ($C1),Y
EF61: STA $07C0,X
EF64: INY
EF65: LDA ($C1),Y
EF67: STA $07C1,X
EF6A: INY
EF6B: LDA ($C1),Y
EF6D: STA $07C3,X
```

This is the multi-byte sibling: it seeds `$07C0/$07C1/$07C3`.

### Melodic note path

```text
EDF7: LDA $07C0,X
EDFA: STA $4000,X
EDFD: LDA $07C1,X
EE00: STA $4001,X
EE03: LDA $EFD9,Y
EE06: STA $07C2,X
EE09: STA $4002,X
EE0C: LDA $07C3,X
EE0F: AND #$F8
EE11: ORA $EFDA,Y
EE14: STA $07C3,X
EE17: STA $4003,X
```

This is the strongest evidence in the pass:

- `$07C0,X` is not a private abstract driver value
- it is the shadow of the APU control byte that gets copied directly into hardware

So for pulse channels, `$07C0,X` corresponds to the usual `$4000/$4004` fields:

- duty
- length-halt / envelope-loop bit
- constant-volume bit
- low 4-bit volume/envelope period

## Fast Argument-Family Read

Observed `0x0A` values in the first quick survey:

- song `8` pulse 2: `0xB1 0xB3 0xBF 0xB5 0xB7 0xB9 0xBB 0xBD`
- song `13` pulse 1: `0x53 0x54 0x56 0x57 0x55 0x53 0x51`
- song `15` pulse 1: `0xC3 0xC4 0xC5 0xC6 0xC8 0xCC`
- song `15` pulse 2: `0x54 0x56 0x57 0x58`

These families look exactly like control-byte edits, not hidden structural commands.

Examples:

- `0xBD -> 0xB9 -> 0xB6 -> 0xB3` matches the title-ending pulse-2 softening pattern already seen in the trace
- `0x53/0x54/0x56/0x57` strongly suggests same upper control bits with low-nibble intensity changes
- `0xC3/0xC4/0xC5/0xC6` suggests another stable duty family with stepping low nibble

## Occurrence Pattern

Quick parser-limited occurrence scan:

- `0x0A` appears only on pulse channels in the current surveyed data
- songs carrying it:
  - song `8` pulse 2
  - song `13` pulse 1
  - song `15` pulse 1 and pulse 2

Notably:

- the title does not use `0x0A`
- triangle does not use `0x0A` in this sweep

## Conclusion

`0x0A` is now much narrower than before.

What is strongly supported:

- it updates the APU control-byte shadow at `$07C0,X`
- on pulse channels, that means duty / halt-loop / constant-volume / low-nibble intensity state
- it is a timbre/level control operation, not a hidden title-only articulation command

What this means for the title bass problem:

- `0x0A` is very unlikely to be the missing explanation for the triangle’s over-sustain
- the title release mystery remains centered on triangle effective gate/damping behavior, not on this command

## Ranked Next Step

1. Work directly on `triangle_release`

- compare title parser/write/trace events against MP3/WAV energy decay
- classify frames as `fresh_attack`, `ring`, `damped`, or `effectively_muted`
- only then decide what extra middle-layer field is needed
