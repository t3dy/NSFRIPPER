# Wizards & Warriors Handler Semantics Pass 1

This pass keeps the scope intentionally small:

- use direct ROM handler disassembly
- tie each conclusion to exact RAM locations
- prefer title-local evidence first
- only keep broader soundtrack observations when they help choose the next mystery

## Newly Promoted Facts

### `0x03 -> 0xEF33`

Disassembly:

```text
EF33: INY
EF34: JMP $EEC3
```

Interpretation:

- `0x03` is not an articulation or hidden envelope command.
- It simply skips one parameter byte and returns to the common pointer-save path.
- No other handler-side RAM or register shadow write occurs here.

Promotion:

- status: `verified`
- meaning: one-byte skip / no-op-with-argument

### `0x07 -> 0xEF4A`

Disassembly:

```text
EF4A: INY
EF4B: LDA ($C1),Y
EF4D: STA $07E0,X
EF50: INY
EF51: JMP $EE4E
```

Interpretation:

- `0x07` writes one byte directly into `$07E0,X`.
- This is the per-channel duration mode byte used by the parser/simulator.
- Title evidence matches this: pulse 2 uses `0x07 08`; triangle uses `0x07 20` and `0x07 10`.

Promotion:

- status: `verified`
- meaning: set per-channel duration mode byte

### `0x08 -> 0xEF41`

Disassembly:

```text
EF41: LDA #$FF
EF43: STA $07E0,X
EF46: INY
EF47: JMP $EE4E
```

Interpretation:

- `0x08` is the explicit inline-duration sentinel setter.
- It does not appear to do anything beyond forcing `$07E0,X = $FF`.

Promotion:

- status: `verified`
- meaning: force inline-duration mode

### `0x09 -> 0xEF37`

Disassembly:

```text
EF37: INY
EF38: LDA ($C1),Y
EF3A: STA $059B
EF3D: INY
EF3E: JMP $EE4E
```

Play-loop context:

```text
EE55: DEC $059A
...
EECF: LDA $059A
EED2: BNE $EEDA
EED4: LDA $059B
EED7: STA $059A
```

Interpretation:

- `0x09` writes the global frame-delay reload byte at `$059B`.
- The play loop decrements `$059A` each frame and reloads it from `$059B` when it expires.
- That makes `0x09` a verified global timing/reload command, not just a loose “tempo-ish” hint.

Promotion:

- status: `verified`
- meaning: set global frame-delay reload

### `0x0A -> 0xEF54`

Disassembly:

```text
EF54: INY
EF55: LDA ($C1),Y
EF57: STA $07C0,X
EF5A: INY
EF5B: JMP $EE4E
```

Related `0x04` context:

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

Interpretation:

- `0x0A` is not fully mysterious anymore.
- It is the single-byte sibling of `0x04`, updating only `$07C0,X`.
- `$07C0,X` is the channel control shadow later combined with note data in the common note path.
- What remains open is the musical meaning of each argument family in different songs, not the handler’s basic action.

Promotion:

- status: `partial`
- meaning: write one control byte into `$07C0,X`

## Title-Local Command Evidence

The title itself now gives a cleaner split between solved timing commands and the still-open release problem.

### Pulse 2

- frame `0`: `0x04 [67,10,33]`, then `0x07 [8]`
- frame `512`: `0x08`, then `0x04 [67,10,33]`, then `0x07 [8]`
- frame `2048`: `0x04 [189,10,33]`, then `0x07 [8]`
- frames `2080`, `2112`, `2144`: `0x04` changes to `[185,10,33]`, `[182,10,33]`, `[179,10,33]`

This matches the already-heard stepped softening near the end. The title does not need `0x0A` to explain that ending fade.

### Triangle

- frame `512`: `0x04 [129,135,18]`, then `0x07 [32]`
- frame `960`: `0x07 [16]`
- frame `1024`: `0x08`
- frame `2144`: `0x04 [67,43,18]`

This reinforces that the title’s remaining bass problem is not “unknown duration commands.” The missing piece is still effective release/damping behavior after known control writes.

## Small Broader Survey

In a quick parser-limited scan:

- `0x0A` shows up heavily in:
  - song `8` pulse 2
  - song `13` pulse 1
  - song `15` pulse 1 and pulse 2
- the title does not use `0x0A`

That makes `0x0A` a good next ROM mystery, but not a likely direct explanation for the title bass over-ring.

## Ranked Next Steps

1. `triangle_release`

- still the highest-priority open mystery for the title
- now isolated from `0x03/0x07/0x08/0x09`

2. `0x0A` argument families

- use songs `8`, `13`, and `15`
- correlate argument values with `$07C0` meaning and audible duty/volume changes

3. `0x04`/`0x0A` control-byte decoding

- split `$07C0` into bits that are truly instrument, duty, constant-volume, or other channel-class-specific semantics

## Bottom Line

This pass removed several fake mysteries.

What is now firmly known:

- `0x03` is just a skip-with-argument
- `0x07` and `0x08` are exactly the duration-mode writes they looked like
- `0x09` is the global delay reload command
- `0x0A` writes only `$07C0,X`

What remains genuinely open for the title:

- the frame-level release/damping layer that makes the bass stop ringing when the next short note arrives
