# NES Sound Driver Families and Game Profiles

Technical reference for the ReapNES Studio extraction pipeline.
Synthesizes VGMPF driver attribution, NESDev APU hardware research,
FamiTracker source analysis, and CC11/CC12 density survey data.

**Research date:** 2026-04-13
**Games profiled:** 30 (from 65-game survey + ROM parsing sessions)
**Driver families:** 5 (renamed from original survey labels)

---

# NES Sound Driver Families: Technical Reference (Part 1)

A taxonomy of NES sound driver behavior derived from CC11/CC12 density
analysis of 65 games, cross-referenced against VGMPF driver attribution,
NESDev hardware documentation, and ROM disassembly research. The five
families classify games not by publisher but by how aggressively the
sound driver talks to the APU per frame.

The classification axis is straightforward: count the CC11 (volume) and
CC12 (duty cycle) events per note in NSF-extracted MIDI files. CC11
maps to NES volume via `nes_vol = floor(msg3 * 15 / 127)`. CC12 maps
to duty cycle (0-3: 12.5%, 25%, 50%, 75%). These ratios reveal whether
a driver delegates envelope shaping to APU hardware or handles it in
software, frame by frame.

---

## Family 1: Hardware Envelope

**25 games in survey. CC11/note: 0.1--2.8. CC12/note: 0.0--0.6.**

The driver writes volume once (or not at all) and lets the APU's
built-in envelope generator handle decay. This is the most CPU-efficient
approach: the hardware does the work, the driver stays hands-off.

### Technical Signature

- **CC11/note range:** 0.1--2.8. At the low end (Wizards & Warriors,
  0.1), the driver writes volume essentially once per note. At the high
  end (Gargoyle's Quest II, 2.8), a few extra writes occur but nowhere
  near per-frame density.
- **CC12/note range:** 0.0--0.6. Duty is set once per note and left
  static. No timbral animation within sustained notes.
- **$4000 bit 5 behavior:** Often 0 (hardware envelope mode), meaning
  the APU's internal envelope generator produces a linear decay from the
  initial volume to zero, optionally looping. When bit 5 is 1 (constant
  volume mode), the driver sets volume once and does not update it
  per-frame. Both approaches produce the same sparse CC11 output: the
  driver is not actively shaping the envelope in software.
- **APU register write frequency:** $4000/$4004 written once per note
  onset, rarely during sustain. The period registers ($4002/$4003,
  $4006/$4007) change at note boundaries. Between notes, the APU runs
  autonomously.

### Known Sound Drivers

- **Capcom -- Yoshihiro Sakaguchi driver:** The archetype. 30+ games
  from 1942 (1985) through Mega Man 6 (1993). Composers wrote music in
  a custom hexadecimal MML (Music Macro Language), converted from
  keyboard performance. The MML workflow produces clean, structured note
  patterns with fixed envelope settings. Sakaguchi wrote the driver in
  6502 assembly for the RP2A03. Detailed byte-level documentation exists
  for the later variant ("Capcom 6C80 Sound Engine," romhacking.net
  document #274, covering Mega Man 3 onward). An earlier "Sound Engine
  1" document covers pre-MM3 titles. Capcom never used expansion audio
  chips on NES. Make Software replaced the Sakaguchi driver for final
  Capcom NES titles (Kenji Yoshida noted the new tool was easier to use).
- **Rare -- Chris Stamper / Mark Betteridge (early usage):** Rare's
  driver powered approximately 48 games (1987--1993). David Wise composed
  directly in 6502 hex: pitch byte + length byte per note, using the text
  editor Brief. The driver doubled time counters internally. Early Rare
  titles (Wizards & Warriors, R.C. Pro-Am, Marble Madness) show minimal
  envelope automation. Later games by the same driver (Battletoads)
  migrate to Family 2, proving that composer technique determines family
  placement more than driver architecture.
- **Early Konami -- Atsushi Fujio branch:** Some early Konami titles
  show Hardware Envelope behavior. Konami's driver lineage is complex:
  an unknown original programmer (possibly Shigeru Fukutake), then
  Hidenori Maezawa's redesign, then Fujio's parallel branch. The early
  Fujio variants sit in this family before Konami composers adopted
  denser per-frame volume automation.
- **Enix / Chunsoft:** Several Enix-published titles show minimal
  envelope behavior consistent with hardware-delegated volume control.

### Hardware Mechanism

The NES APU envelope generator (documented at nesdev.org/wiki/APU_Envelope)
operates in two modes controlled by $4000 bit 5 (pulse 1) / $4004 bit 5
(pulse 2):

- **Bit 5 = 0: Hardware envelope.** The APU's internal divider decrements
  volume from the initial value (bits 0--3) toward zero at a rate
  controlled by bits 0--3 (which double as the divider period). The frame
  counter (~240 Hz NTSC) clocks this decay. If the loop flag (bit 5 of
  the length counter halt) is set, the envelope loops back to 15 on
  reaching zero. This produces a fixed linear decay shape -- the only
  envelope the hardware can generate autonomously.
- **Bit 5 = 1: Constant volume.** Bits 0--3 set the output volume
  directly. The APU produces this volume indefinitely until the driver
  writes a new value. Hardware Envelope family games use this mode but
  write the register infrequently (once per note, occasionally twice),
  producing the same effect as a single-level sustain.

The FamiTracker source code confirms the period-to-frequency formula used
by NES drivers: `period = (1789773 / freq) - 0.5`, with base frequency
32.7032 Hz (C1). FamiTracker's 5-sequence instrument model (volume,
arpeggio, pitch, hi-pitch, duty) runs per frame -- but Hardware Envelope
games effectively use only 1-sequence instruments (pitch), leaving volume
and duty to initial settings.

Non-linear mixing affects how these sparse envelopes sound in practice.
The pulse mixing formula is `output = 95.88 / ((8128 / (sq1 + sq2)) + 100)`,
meaning two pulse channels interact non-linearly. A pulse channel at
volume 15 with the other at 0 sounds different from both at 7. Hardware
Envelope games, by not actively controlling volume, are more susceptible
to these mixing artifacts than software-controlled families.

### Synth Implications for ReapNES Studio

- **CC11/CC12 handling:** In CC-driven mode (Priority 2), the synth
  receives very few CC11 events per note. The synth must hold the last
  received CC11 value as a constant volume level until the next CC11
  arrives or the note ends. Do not interpolate between sparse CC11
  values -- the hardware does not interpolate; it holds.
- **ADSR keyboard presets:** Hardware Envelope games sound best with a
  simple ADSR preset: short attack (1--2 frames), linear decay to a
  moderate sustain level (vol 6--8 out of 15), no release tail. The
  decay should approximate the APU's hardware linear decay. Avoid
  complex multi-stage envelopes -- they would sound anachronistic for
  this family.
- **Duty cycle:** Set once per note from CC12 (or from a preset default
  if no CC12 data). Typical values: duty 1 (25%) or duty 2 (50%) for
  most Capcom games. No per-frame duty animation needed.
- **SysEx mode (Priority 1):** When register replay is available, the
  synth should expect infrequent $4000/$4004 writes. The hardware
  envelope mode (bit 5 = 0) must be implemented in the synth's
  waveform generator to reproduce the linear decay correctly.

### Validation Expectations

- **MIDI file sizes:** Smallest of all families. Fewer CC events means
  fewer MIDI messages. A typical Hardware Envelope game produces roughly
  40--60% of the MIDI file size of a Family 2 game with similar note
  count.
- **Common failure modes:**
  - Hardware envelope decay not modeled in synth: notes sustain at
    constant volume instead of decaying. Listen for unnaturally flat
    sustains.
  - CC11 events misattributed to noise channel: Hardware Envelope games
    typically have no CC11 on noise (velocity-driven only). If CC11
    events appear on the noise channel, the extraction has a routing bug.
  - Period table mismatch: some early Capcom games use slightly
    non-standard period tables. Verify pitch against game audio.
- **What to check:** Note-on volume matches game audio. Decay shape
  (if audible) is linear, not exponential. Duty cycle is static within
  notes.

### Representative Games

| Game | CC11/note | CC12/note | Driver / Programmer |
|------|-----------|-----------|---------------------|
| Wizards & Warriors | 0.1 | 0.0 | Rare -- Stamper/Betteridge |
| Mega Man 1 | 0.2 | 0.0 | Capcom -- Sakaguchi |
| Ghosts 'n Goblins | ~0.5 | ~0.1 | Capcom -- Sakaguchi (early) |
| 1942 | ~0.5 | ~0.1 | Capcom -- Sakaguchi (early) |
| Commando | ~0.6 | ~0.1 | Capcom -- Sakaguchi |
| Mega Man 2 | 0.8 | 0.0 | Capcom -- Sakaguchi |
| DuckTales | 0.8 | 0.2 | Capcom -- Sakaguchi |
| Strider | 1.0 | 0.0 | Capcom -- Sakaguchi |
| Gargoyle's Quest II | 2.8 | 0.2 | Capcom -- late Sakaguchi / Make Software transition |

---

## Family 2: Standard Envelope

**18 games in survey. CC11/note: 3.5--5.6. CC12/note: < 0.5.**

The driver maintains a software-controlled volume envelope, writing to
$4000/$4004 every frame or every few frames. Duty cycle remains static
within notes. This is the workhorse approach of mid-to-late NES era
sound programming: expressive volume shaping without the CPU cost of
duty animation.

### Technical Signature

- **CC11/note range:** 3.5--5.6. The typical pattern is 4--5 CC11
  updates per note, corresponding to per-frame volume writes from a
  lookup table. Castlevania 1 pulse channels show approximately 4 CC11
  events per note with the characteristic shape: attack at volume 15,
  decay over 3--4 frames, sustain at volume 4--8.
- **CC12/note range:** < 0.5. Duty is set at note onset and held for
  the note's duration. Castlevania 1 uses duty 2 (50%) for Pulse 2 and
  duty 1 (25%) for Pulse 1, but these are per-note settings, not
  per-frame changes.
- **$4000 bit 5 behavior:** Always 1 (constant volume mode). The driver
  writes volume directly each frame using a software envelope table.
  The APU's hardware envelope generator is bypassed entirely. This
  gives the driver full control over envelope shape at the cost of CPU
  cycles per frame.
- **APU register write frequency:** $4000/$4004 written once per frame
  during the active portion of each note (attack and decay phases).
  During sustain, writes may thin to every 2--3 frames. Total: 3--6
  writes per note depending on note duration and envelope complexity.

### Known Sound Drivers

- **Konami -- Hidenori Maezawa branch:** The Maezawa driver variant
  became the de facto standard for Konami NES titles. Maezawa heavily
  rewrote the original Konami driver and his variant was used even in
  games he did not compose. Castlevania 1 (CC11/note 4.3) and Contra
  are signature members. Composers wrote in assembly macros, assembled
  for playback on dev hardware, entered data into a shared mainframe,
  and ran through a sound emulator. Maezawa co-designed the VRC6
  expansion chip. VGMPF documents "an unusually large number of
  customized and one-time variations" across Konami's catalog.
- **Tecmo -- Keiji Yamagishi ("Super Sound Machine"):** Ninja Gaiden I
  and Ninja Gaiden III (CC11/note 5.6) sit at the dense end of this
  family. Yamagishi's driver appears configurable: Ninja Gaiden II
  (CC11/note 10.5) jumps to Family 4, suggesting the driver can be
  tuned for higher density by the composer. Yoshiaki Inose wrote an
  earlier variant (Chester Field, Mighty Bomb Jack).
- **Rare -- Mark Betteridge (Battletoads-era):** Battletoads (CC11/note
  4.1) uses the same Rare driver as Wizards & Warriors (Family 1, 0.1)
  but David Wise's later compositions used far more per-frame volume
  automation. The driver architecture supports per-frame writes; earlier
  games simply did not use that capability. Battletoads also features
  algorithmic PCM drums -- $4011 writes with computed ramp waveforms
  rather than stored DPCM samples, saving ROM space. The engine averages
  482 cycles/frame with 1820 peak.
- **Late Capcom -- Sakaguchi v3+ / Make Software transition:** Some late
  Capcom titles (Mega Man 3--4 at CC11/note 3.7) shift from Family 1
  into this range, possibly reflecting the Make Software driver
  replacement that offered more envelope features.

### Hardware Mechanism

All Family 2 games use constant volume mode ($4000 bit 5 = 1). The
driver maintains an envelope lookup table in ROM -- typically an array
of 4-bit volume values indexed by frame count within the note. On each
call to the PLAY routine (~60 Hz NTSC), the driver:

1. Reads the current index into the envelope table.
2. Writes the corresponding volume to $4000 bits 0--3 (with bit 5 = 1).
3. Increments the index, clamping or looping at the table end.

This produces the characteristic attack-decay-sustain shape visible in
CC11 automation: a spike to 15, a descent over 3--4 frames, then a hold
at the sustain level. The sustain level and decay rate are baked into
the table -- different instruments within the same game can have
different envelope shapes by pointing to different tables.

The Konami Maezawa driver uses DX command bytes to select envelope
parameters. The DX byte count (2 in Castlevania 1, 3 or 1 in Contra)
varies between games -- same opcode, different semantics. This is a
documented source of parser bugs: assuming CV1 format when parsing
Contra wastes multiple debugging rounds.

DPCM usage in this family is primarily percussive: kick and snare drum
samples on the DMC channel. Konami used DPCM for kick/snare and
occasional vocal effects. Rare used DPCM rarely (Pin-Bot sound effects,
Battletoads pause music are notable exceptions).

### Synth Implications for ReapNES Studio

- **CC11/CC12 handling:** CC11 data is the primary envelope source.
  The synth must apply CC11 values directly to channel output level,
  updating per-frame. ADSR must be completely bypassed when CC11 data
  is present -- this is the core contract. CC12 arrives at note onset
  only; apply and hold.
- **ADSR keyboard presets:** Model the attack-decay-sustain shape from
  the CC11 data. Good starting preset: attack 0 frames (instant),
  decay 3--4 frames to sustain at volume 8 (of 15), no release. For
  Battletoads specifically, a slightly longer decay (5--6 frames) with
  lower sustain (vol 4--5) better captures the darker envelope shape.
- **Per-game preset differences:** Castlevania 1 and Contra have
  different envelope shapes despite using the same Maezawa driver
  lineage. CV1 uses a brighter attack with higher sustain; Contra uses
  a sharper decay. Presets should be per-game, not per-driver.
- **Noise channel:** Velocity-driven, no CC11. Noise expects velocity
  on note-on to set initial volume, then self-decay via the synth's
  noise ADSR. Standard drum mapping: kick=36, snare=38, hi-hat=42.

### Validation Expectations

- **MIDI file sizes:** Moderate. Roughly 1.5--2x the size of a
  comparable Hardware Envelope game due to CC11 automation density.
  A typical Castlevania 1 track (Vampire Killer) has approximately
  309 pulse notes with approximately 4 CC11 updates each, producing
  roughly 1200 CC11 events per pulse channel.
- **Common failure modes:**
  - ADSR overriding CC11: the single most common synth bug. If the
    synth's ADSR is active during file playback, it fights the CC11
    data and the envelope sounds wrong. The synth must detect CC11
    presence and disable ADSR.
  - Envelope table misinterpretation in ROM parsing: for games parsed
    from ROM (not NSF), the E8 command means different things in
    different Konami games. Never copy command handling without checking
    the target game's manifest.
  - Note duration truncation by volume: a note can be "silent" for its
    last N frames if CC11 decays to 0 before the period changes. This
    is correct NES behavior. Do not truncate the note at the zero-volume
    point -- duration equals period change, not volume equals zero.
- **What to check:** CC11 envelope shape matches the attack-decay-sustain
  pattern audible in game audio. Sustain level is correct (not clipped
  to 0 or stuck at 15). Duty cycle is static within each note.

### Representative Games

| Game | CC11/note | CC12/note | Driver / Programmer |
|------|-----------|-----------|---------------------|
| Marble Madness | 3.5 | ~0.2 | Rare -- Stamper/Betteridge |
| Mega Man 3 | 3.7 | ~0.2 | Capcom -- late Sakaguchi |
| Battletoads | 4.1 | ~0.2 | Rare -- Betteridge |
| Castlevania 1 | 4.3 | ~0.3 | Konami -- Maezawa |
| Contra | ~4.5 | ~0.3 | Konami -- Maezawa |
| Ninja Gaiden I | ~4.8 | ~0.3 | Tecmo -- Yamagishi |
| Ninja Gaiden III | 5.6 | ~0.3 | Tecmo -- Yamagishi |

---

## Family 3: Duty Animators

**5 games in survey. CC11/note: 3.7--4.9. CC12/note: 0.7--1.0.**

Both volume and duty cycle are animated per note. The duty cycling
creates timbral movement within each note -- brighter attack, mellower
sustain, or oscillating shimmer. This is more CPU-intensive than
Standard Envelope and produces a richer, more harmonically varied sound.

Despite the old name "Capcom Duty Switchers," zero Capcom games appear
in this family. The name was a misnomer from initial analysis before
developer attribution was completed.

### Technical Signature

- **CC11/note range:** 3.7--4.9. Volume automation density overlaps
  with Family 2 (Standard Envelope). The distinguishing feature is not
  CC11 density but CC12 density.
- **CC12/note range:** 0.7--1.0. This is the defining metric: nearly
  one duty cycle change per note. Other families have CC12/note below
  0.5. Duty Animators cross a threshold where duty is no longer a
  static per-note setting but an active part of the timbral envelope.
- **$4000 bit 5 behavior:** Always 1 (constant volume mode). Both the
  volume bits (0--3) and the duty bits (6--7) of $4000/$4004 are written
  per frame, meaning the entire upper byte is rewritten each frame
  rather than just the volume nibble.
- **APU register write frequency:** $4000/$4004 written once per frame
  with both volume and duty fields changing. The full register
  (all 8 bits: duty + loop + constant-volume-flag + volume/envelope)
  is rewritten each frame. Total: 3--5 writes per note for volume,
  plus 0.7--1.0 writes per note for duty.

### Known Sound Drivers

- **Nintendo -- Koji Kondo (SMB1 variant):** Super Mario Bros. 1
  (CC11/note 4.9, CC12/note 0.8) is the best-known member. Kondo
  programmed his own driver variant and wrote music in pure 6502
  assembly. The SMB1 duty animation is subtle but present: pulse
  channels shift duty during the attack phase of notes, creating the
  characteristic bright-to-mellow timbre that defines the Mario sound.
- **HAL Laboratory -- Hiroaki Suga:** Kirby's Adventure (CC11/note 3.7,
  CC12/note 0.7) is the largest game in this family with 78,992 notes
  across 56 songs. The HAL driver is one of the few that actively
  animates duty cycle during sustained notes, producing a shimmering
  timbre effect. HAL later created "Music Maker," a custom MML tool
  replacing raw assembly entry, but the underlying driver maintained
  its duty animation capability. DPCM drum support was added in later
  driver versions.
- **Konami -- VRC6-aware variant (CV3):** Castlevania 3 US (CC11/note
  4.6, CC12/note 0.8) appears in this family. The Japanese version
  (Akumajou Densetsu) used the VRC6 expansion chip with 2 extra pulse
  channels and a sawtooth wave. The US version lost this hardware and
  had to rearrange music for the standard APU. The CC12 density
  difference (1.0 JP vs 0.8 US) reflects extra channel activity
  captured in the NSF. The VRC6-aware driver variant naturally produces
  more duty data from managing additional pulse waveforms.

### Hardware Mechanism

Duty cycle is encoded in $4000 bits 6--7 (pulse 1) and $4004 bits 6--7
(pulse 2), selecting one of four waveform shapes:

| Value | Duty | Waveform | Character |
|-------|------|----------|-----------|
| 0 | 12.5% | _-------_ | Thin, reedy, nasal |
| 1 | 25% | __------_ | Standard pulse, bright |
| 2 | 50% | ____----_ | Square wave, full, warm |
| 3 | 75% | ______--_ | Inverted 25%, identical timbre to 25% but inverted phase |

In the FamiTracker instrument model, duty is one of five per-frame
sequences (volume, arpeggio, pitch, hi-pitch, duty). Duty Animator games
effectively use 2 or 3 of these sequences (volume + duty, sometimes
arpeggio), versus Hardware Envelope games that use only pitch.

When the driver writes both volume and duty per frame, the entire $4000
register is rewritten. Since bits 4--5 (constant volume flag, length
counter halt) also live in this register, they are re-asserted every
frame. This has a side effect: the length counter cannot expire naturally
because bit 5 is continuously rewritten, keeping the channel alive
indefinitely until the driver explicitly silences it.

The non-linear pulse mixing formula `95.88 / ((8128 / (sq1 + sq2)) + 100)`
means that duty cycle changes affect perceived loudness as well as
timbre. Duty 2 (50%) produces a louder perceived output than duty 0
(12.5%) at the same volume setting, because the waveform spends more
time in its high state. Duty Animator games exploit this: shifting from
duty 0 to duty 2 during a note creates a volume-plus-timbre swell that
is richer than a volume change alone.

### Synth Implications for ReapNES Studio

- **CC11/CC12 handling:** Both CC11 and CC12 must be applied per-frame.
  The synth must update the waveform lookup table index on every CC12
  change, synchronized with CC11 volume changes. CC12 mapping:
  0--31 = duty 0, 32--63 = duty 1, 64--95 = duty 2, 96--127 = duty 3.
  Unlike Families 1 and 2, ignoring CC12 data produces an audibly
  wrong result for Duty Animator games.
- **ADSR keyboard presets:** Must include a duty sequence alongside the
  volume ADSR. For an SMB1 preset: attack at duty 1 (25%, bright),
  shift to duty 2 (50%, warm) after 2--3 frames, hold duty 2 through
  sustain. For Kirby's Adventure: alternate between duty 1 and duty 2
  during sustain to create the shimmer effect.
- **Visual feedback for video recording:** Duty cycle changes should be
  visible on the synth console UI. Since these games actively change
  duty, the duty knob/indicator should animate during playback, making
  the timbral movement visible for YouTube recordings.
- **Channel-specific duty patterns:** Different pulse channels within
  the same game may have different duty animation patterns. Pulse 1
  might animate while Pulse 2 holds static, or vice versa. The synth
  should not assume both channels behave identically.

### Validation Expectations

- **MIDI file sizes:** Moderately larger than Family 2. The additional
  CC12 events add roughly 15--25% to MIDI file size compared to a
  Standard Envelope game with the same note count. Kirby's Adventure
  (56 songs, 78,992 notes) produces one of the largest MIDI collections
  in the pipeline.
- **Common failure modes:**
  - CC12 data ignored: produces correct volume envelope but flat timbre.
    The game sounds "duller" than the original. Always compare both
    volume AND timbre against game audio.
  - CC12 timing misaligned with CC11: if extraction desynchronizes the
    two CC streams, duty changes happen at wrong points in the note.
    Verify that CC11 and CC12 events at the same frame offset arrive
    at the same tick position in MIDI.
  - Duty 3 vs Duty 1 confusion: duty 3 (75%) is acoustically identical
    to duty 1 (25%) -- same timbre, inverted phase. If the extraction
    reports duty 3 where the game uses duty 1 (or vice versa), the
    result sounds identical. This is not a bug.
- **What to check:** Duty cycle changes are present in pulse channels
  (CC12 events exist). Duty animation timing correlates with note
  attack phases. Both CC11 and CC12 are synchronized per-frame.

### Representative Games

| Game | CC11/note | CC12/note | Driver / Programmer |
|------|-----------|-----------|---------------------|
| Kirby's Adventure | 3.7 | 0.7 | HAL -- Suga |
| Castlevania 3 US | 4.6 | 0.8 | Konami -- VRC6-aware variant |
| Super Mario Bros. 1 | 4.9 | 0.8 | Nintendo -- Kondo |

---

## Family 4: Dense Automators

**16 games in survey. CC11/note: 5.1--14.9. CC12/note: 0.0--0.3.**

Per-frame volume writes taken to extremes. These drivers update volume
obsessively -- sometimes multiple times per frame -- while leaving duty
cycle static. The result is a sculpted, dynamic sound with software
envelopes that can produce complex multi-stage shapes, echo effects,
and amplitude modulation impossible with hardware envelopes. This is
software envelope maximalism: every frame is sacred.

### Technical Signature

- **CC11/note range:** 5.1--14.9. The widest range of any family. At
  the low end (Metroid, Kid Icarus, ~5.1), the driver writes volume
  per frame with occasional gaps. At the high end (Final Fantasy, 14.9),
  the driver may write multiple volume values per frame or use very
  short notes that each receive several CC11 updates.
- **CC12/note range:** 0.0--0.3. Duty is static. The Square driver
  (Final Fantasy) has 0.0 CC12/note -- literally zero duty animation
  across the entire game. These drivers pour their CPU budget into
  volume control, not timbre modulation.
- **$4000 bit 5 behavior:** Always 1 (constant volume mode). The driver
  writes volume directly every frame, sometimes multiple times per
  frame for volume ramping effects. The hardware envelope generator is
  entirely unused.
- **APU register write frequency:** $4000/$4004 written every frame,
  sometimes multiple times per frame. The distinction from Family 2 is
  density: Family 2 writes 3--6 times per note (attack-decay-sustain),
  while Family 4 writes 5--15 times per note with continuous volume
  modulation through the sustain phase as well.

### Known Sound Drivers

- **Square -- Toshiaki Imai:** Final Fantasy (CC11/note 14.9, CC12/note
  0.0) is the densest game in the entire 65-game survey. Imai wrote
  Square's first NES sound driver, used for Final Fantasy and Rad
  Racer. Nobuo Uematsu composed on an MSX using MML notation (e.g.,
  "C8" for an 8th note C), and Imai transplanted the music into the
  driver. Hiroshi Nakamura wrote the replacement driver used from
  Final Fantasy II onward. 3-D Battles of WorldRunner (CC11/note 5.4)
  also belongs to this lineage.
- **Sunsoft -- Akito Takeuchi / Shinichi Seya:** The actual Sunsoft
  games (as opposed to the "Sunsoft-style" label applied to Family 2).
  Blaster Master (CC11/note 11.7), Batman (CC11/note 7.9), and Journey
  to Silius (CC11/note 7.8) are core members. Sunsoft's audio is famous
  for two innovations: dense volume automation and DPCM bass (using the
  delta modulation channel for pitched bass notes instead of just drum
  samples). The DPCM bass samples came from an AKAI S700 sampler. This
  freed the triangle channel for melody, giving Sunsoft games an
  unusually full sound with effective 5-voice polyphony. Takeuchi wrote
  the drivers for Blaster Master and Batman. Seya wrote the drivers for
  Journey to Silius and Gimmick!. Seya reprogrammed the driver to use
  MML in the later revision. The Sunsoft 5B chip (YM2149F PSG, 3 extra
  channels) was used only in Gimmick! (1992, Japan-only) -- the rarest
  NES expansion audio chip in commercial releases.
- **Nintendo -- Hirokazu Tanaka:** Metroid and Kid Icarus (CC11/note
  ~5.1) use Tanaka's driver variant, which later adapted to Game Boy.
  Tanaka's approach is at the low end of Dense Automator density --
  per-frame volume writes but not the obsessive multi-write-per-frame
  approach of Square or Sunsoft.
- **Tecmo -- Yamagishi (NG2 variant):** Ninja Gaiden II (CC11/note 10.5)
  jumps from its siblings in Family 2 (NG1 and NG3) into Dense
  Automator territory. This suggests either a driver revision between
  games or a deliberate change in compositional approach. The Tecmo
  driver appears configurable enough to span two families.

### Hardware Mechanism

Dense Automators use the same constant volume mode ($4000 bit 5 = 1) as
Families 2 and 3, but push per-frame volume writes to their maximum
density. At 60 Hz NTSC frame rate, 15 CC11 events per note (Final
Fantasy's density) means the driver is updating volume for approximately
every frame of every note, including the sustain phase where Family 2
drivers hold steady.

Sunsoft's DPCM bass technique is a hardware-level innovation specific to
this family. The DPCM channel ($4010--$4013) normally plays stored
1-bit delta-encoded samples at one of 16 fixed rates. Sunsoft stored
5 pitched bass samples (A#, B, C, C#, D) at different fundamental
frequencies and mapped them across the bass range via the APU's sample
rate register ($4010), achieving approximate pitch control over what was
designed as a fixed-pitch sample player. Implementation required careful
sample length and loop point calibration to maintain pitch stability.
The $4011 DMC DAC value affects triangle/noise volume through the
non-linear mixer -- some Dense Automator games (including Sunsoft titles)
exploit this for crude cross-channel volume interaction.

Battletoads (Rare, Family 2 by CC11 density but notable here for
technique) uses a related innovation: algorithmic PCM drums via computed
$4011 writes rather than stored DPCM samples. Ramp-based synthesis with
variable speed/length creates triangular waveforms, saving ROM space
while producing distinctive percussion.

### Synth Implications for ReapNES Studio

- **CC11/CC12 handling:** CC11 is everything. The synth must process
  high-frequency CC11 streams without dropping events or introducing
  latency. At Final Fantasy density (14.9 CC11/note), the synth
  receives a near-continuous stream of volume updates that must all be
  applied in order. CC12 is negligible -- apply once at note onset,
  hold for duration.
- **ADSR keyboard presets:** Dense Automator games have the most complex
  envelope shapes. A single ADSR stage is insufficient to model them
  for keyboard play. Consider multi-stage presets:
  - **Square/FF preset:** Rapid attack, quick decay to moderate sustain,
    then slow fade through sustain phase. The continuous sustain-phase
    fade is the key differentiator from Family 2.
  - **Sunsoft/Batman preset:** Sharp attack, rapid decay, very low
    sustain with subtle amplitude modulation (slight volume oscillation
    during sustain).
  - **Tanaka/Metroid preset:** Moderate attack, smooth decay, stable
    sustain. Less aggressive than Square or Sunsoft.
- **DPCM bass channel:** If the synth supports DPCM playback, Sunsoft
  games should route bass to the DPCM channel with pitched sample
  playback. If not, triangle channel bass is the fallback, but the
  sonic character will differ noticeably.
- **Performance consideration:** High CC11 density means more MIDI
  processing per frame. The synth's MIDI input handler must be
  efficient enough to process 15+ CC events per note without buffer
  overflow or audible latency.

### Validation Expectations

- **MIDI file sizes:** Largest of all families (excluding Family 5's
  single entry). Final Fantasy at 14.9 CC11/note produces MIDI files
  roughly 3--4x the size of comparable Hardware Envelope games.
  Blaster Master and Journey to Silius produce files roughly 2--3x
  the Family 1 baseline.
- **Common failure modes:**
  - CC11 event dropping: if the extraction or synth drops CC11 events
    under high density, the envelope shape is corrupted. Audible as
    sudden volume jumps or missing decay segments.
  - Sustain-phase volume changes mistaken for new notes: Dense
    Automators modulate volume during sustain without changing pitch.
    The MIDI builder must not interpret a CC11 change as a note
    boundary. Note boundaries are defined by period changes, not
    volume changes.
  - DPCM bass misrouted: Sunsoft DPCM bass appears on the DMC channel,
    not triangle. If extraction maps it to triangle, bass notes will
    sound at wrong pitch and the triangle channel will have extra notes.
- **What to check:** CC11 envelope shape is smooth and continuous (no
  gaps or jumps). Volume modulation continues through sustain phase.
  DPCM bass (Sunsoft games) is correctly separated from triangle
  channel. Note count is reasonable for the game's musical complexity.

### Representative Games

| Game | CC11/note | CC12/note | Driver / Programmer |
|------|-----------|-----------|---------------------|
| Metroid | ~5.1 | ~0.1 | Nintendo -- Tanaka |
| Kid Icarus | ~5.1 | ~0.1 | Nintendo -- Tanaka |
| Journey to Silius | 7.8 | ~0.1 | Sunsoft -- Seya |
| Batman (Sunsoft) | 7.9 | ~0.1 | Sunsoft -- Takeuchi |
| Ninja Gaiden II | 10.5 | ~0.1 | Tecmo -- Yamagishi (NG2 variant) |
| Blaster Master | 11.7 | ~0.1 | Sunsoft -- Takeuchi |
| Final Fantasy | 14.9 | 0.0 | Square -- Imai |

---

## Family 5: Full Animation

**1 game in survey. CC11/note: 7.7. CC12/note: 1.3.**

High-density automation on both axes simultaneously. Volume and duty
cycle are both written aggressively every frame, producing the richest
per-frame data stream of any NES game in the survey. This is the
synthesis of Family 3's duty animation and Family 4's volume density,
and only one commercial game achieves it: Super Mario Bros. 3.

### Technical Signature

- **CC11/note range:** 7.7. Higher than any Family 2 or 3 game, in the
  mid-range of Family 4.
- **CC12/note range:** 1.3. Higher than any other game in the survey.
  More than one duty cycle change per note on average, meaning some
  notes receive multiple duty transitions.
- **$4000 bit 5 behavior:** Always 1 (constant volume mode). Both
  volume and duty fields of $4000/$4004 are rewritten every frame.
- **APU register write frequency:** $4000/$4004 rewritten every frame
  with both volume and duty fields actively changing. This is the
  maximum APU register write density observed in any commercial NES
  game: every frame carries both amplitude and timbral information.

### Known Sound Drivers

- **Nintendo -- Koji Kondo (SMB3 variant):** Kondo wrote the driver
  variant for all three Super Mario Bros. games, but each has a
  distinctly different envelope profile. SMB1 (CC11/note 4.9,
  CC12/note 0.8) is a Duty Animator (Family 3). SMB3 (CC11/note 7.7,
  CC12/note 1.3) pushes both metrics higher, achieving the only
  Full Animation profile in the survey. The SMB3 driver represents
  Kondo's most sophisticated NES sound programming. It is unclear
  whether this reflects a driver revision or simply Kondo writing
  more complex instrument definitions within the existing driver
  architecture. SMB2 uses a different engine entirely (the game was
  a reskin of Doki Doki Panic with a different publisher's sound
  driver).

### Hardware Mechanism

Full Animation combines the mechanisms of Family 3 (duty animation) and
Family 4 (dense volume automation) simultaneously. Every frame, the
driver:

1. Reads both volume and duty from per-frame instrument tables.
2. Writes the complete $4000/$4004 register: duty bits (6--7), constant
   volume flag (bit 5 = 1), and volume (bits 0--3).
3. Advances both the volume and duty sequence indices.

The CPU cost is not significantly higher than Family 4 alone (the same
register write carries both values), but the compositional complexity is
far greater. The driver must store and sequence two parallel per-frame
arrays (volume sequence + duty sequence) per instrument, doubling the
ROM space for instrument definitions compared to a volume-only approach.

At CC12/note 1.3, some notes receive 2+ duty transitions. A typical
SMB3 note pattern might be: frame 1 duty 1 (bright attack), frame 2
duty 2 (warm fill), frames 3+ duty 2 (sustain) -- with the transition
occurring within the first 2--3 frames of each note. But unlike Family 3
where this pattern is the maximum complexity, SMB3 occasionally adds a
third duty state within longer notes or modulates duty during the
sustain phase.

The FamiTracker instrument model (5 per-frame sequences: volume,
arpeggio, pitch, hi-pitch, duty) maps directly to Full Animation games.
SMB3 effectively uses 3 of these sequences simultaneously (volume,
duty, and pitch) at maximum frame density. FamiTracker recreations of
SMB3 music are among the most complex FamiTracker instruments in
existence, requiring long duty and volume sequences to match the
original's per-frame behavior.

### Synth Implications for ReapNES Studio

- **CC11/CC12 handling:** Both CC11 and CC12 must be processed at full
  frame rate. The synth must update volume and duty simultaneously on
  each frame tick. Neither can be deferred or batched. CC12 is not a
  "set once" parameter for this family -- it is a continuous stream
  requiring the same attention as CC11.
- **ADSR keyboard presets:** The most complex preset in the library.
  Must include both a multi-stage volume envelope and a multi-stage
  duty sequence. Recommended SMB3 preset:
  - Volume: attack 15, decay to 10 over 2 frames, sustain at 8 with
    slight modulation.
  - Duty: start at 1 (25%), shift to 2 (50%) after 1--2 frames, hold
    through sustain with occasional returns to 1 for accent notes.
  - This produces the warm, singing quality characteristic of SMB3's
    pulse channels.
- **Visual feedback:** Both the volume meter and duty indicator should
  animate during playback. For YouTube recordings, SMB3 provides the
  most visually dynamic display of any game -- both knobs moving
  simultaneously every frame.
- **Reference game:** SMB3 should be the benchmark for synth testing
  at maximum data density. If the synth handles SMB3 correctly, it
  handles everything.

### Validation Expectations

- **MIDI file sizes:** Large, comparable to mid-range Family 4 games.
  The combined CC11 + CC12 density produces files roughly 2.5--3x the
  size of a comparable Hardware Envelope game.
- **Common failure modes:**
  - CC12 treated as static: if the synth applies CC12 once per note
    (appropriate for Families 1, 2, and 4), SMB3 sounds flat. The
    timbral animation is a defining characteristic that must be
    preserved.
  - CC11 and CC12 desynchronization: if the two CC streams drift apart
    by even one frame tick, the combined volume+timbre envelope is
    corrupted. Verification must check that corresponding CC11 and CC12
    events share the same tick position.
  - Comparison against wrong SMB version: SMB1 (Family 3) and SMB3
    (Family 5) have different envelope profiles. Do not use SMB1
    presets or validation criteria for SMB3 or vice versa.
- **What to check:** Both CC11 and CC12 streams are present and dense.
  CC12 changes occur within notes (not just at note onset). Combined
  volume+duty envelope produces the characteristic warm SMB3 tone when
  played through the synth.

### Representative Games

| Game | CC11/note | CC12/note | Driver / Programmer |
|------|-----------|-----------|---------------------|
| Super Mario Bros. 3 | 7.7 | 1.3 | Nintendo -- Kondo (SMB3 variant) |

---

## Cross-Family Summary

| Family | Name | Games | CC11/note | CC12/note | $4000 bit 5 | Envelope Source | CPU Cost |
|--------|------|-------|-----------|-----------|-------------|-----------------|----------|
| 1 | Hardware Envelope | 25 | 0.1--2.8 | 0.0--0.6 | Often 0 (hardware) or set-once 1 | APU hardware decay | Minimal |
| 2 | Standard Envelope | 18 | 3.5--5.6 | < 0.5 | Always 1 (constant) | Software lookup table, per-frame | Moderate |
| 3 | Duty Animators | 5 | 3.7--4.9 | 0.7--1.0 | Always 1 (constant) | Software, volume + duty per-frame | Moderate-high |
| 4 | Dense Automators | 16 | 5.1--14.9 | 0.0--0.3 | Always 1 (constant) | Software, obsessive per-frame volume | High |
| 5 | Full Animation | 1 | 7.7 | 1.3 | Always 1 (constant) | Software, per-frame volume + duty | Highest |

**Key principle:** Company attribution does not predict family membership.
Konami spans Families 1, 2, and 3. Nintendo spans 3, 4, and 5. Tecmo
spans 2 and 4. Rare spans 1 and 2. The CC11/CC12 density metric is a
better predictor of sonic character than publisher name, because driver
architecture sets the ceiling while composer technique determines where
within that ceiling the music lands.

---

# Part 2: Game Profiles

# Part 2: Game Profiles (1-10)

Technical reference profiles for ReapNES Studio. Each profile documents
driver family, hardware, music architecture, pipeline status, known
issues, and synth preset recommendations.

Driver family names use the revised taxonomy:
1. Hardware Envelope (was Minimal)
2. Standard Envelope (was Sunsoft-style)
3. Duty Animators (was Capcom Duty Switchers)
4. Dense Automators
5. Full Animation

---

### 1. Castlevania 1

**Attribution**
- Publisher: Konami, 1986
- Composer: Kinuyo Yamashita (credited as James Banana)
- Driver programmer: Hidenori Maezawa

**Driver Family**
- Family 2: Standard Envelope. CC11/note ~4.3, CC12/note <0.5.
- The Maezawa driver updates volume via software envelope lookup tables,
  writing to $4000/$4004 approximately 4-5 times per note. Attack at
  vol 15, decay over 3-4 frames, sustain at vol 4-8. Duty cycle is set
  per-note but not animated within notes, keeping CC12 density low. This
  places CV1 firmly in the Standard Envelope family: detailed volume
  shaping with static timbre.

**Hardware**
- Mapper 2 (UxROM). 128KB PRG-ROM, 8KB CHR-RAM. No expansion audio.
  Standard NROM-like memory layout with bank switching for PRG only.

**Music Architecture**
- Software envelope via lookup table. The driver maintains per-channel
  volume envelope state and writes constant-volume mode ($4000 bit 4 set)
  each frame. Hardware envelope decay is not used.
- No DPCM usage. All percussion is on the noise channel ($400C-$400F).
- Pulse 1 carries the lead melody with duty=1 (25%). Pulse 2 provides
  harmony/countermelody with duty=2 (50%). Triangle handles bass lines
  with gate-only volume (CC11 always 127). Noise provides kick/snare/
  hi-hat patterns via period index and volume envelope.
- 11 tracks in the NSF (title, stages, bosses, intermissions, endings).
- The DX command in the Maezawa driver reads 2 bytes after the opcode.
  This is a critical distinction from later Konami games.

**Pipeline Status**
- ROM parser exists. Validated at Rung 4 (trusted output).
- 0 pitch mismatches on pulse channels against Mesen trace.
- Proven pipeline: trace -> Frame IR -> MIDI/CC/SysEx/RPP.
- Route: both NSF emulation and trace pipeline available. Trace is
  ground truth; NSF is convenience route for batch production.
- This is the reference game for the entire extraction pipeline. All
  architectural patterns (Frame IR, validation ladder, execution
  semantics gates) were developed and proven on CV1 first.

**Known Issues**
- Early sessions wasted 5+ prompts guessing envelope hypotheses before
  anyone looked at actual trace data. This incident is baked into
  MISTAKEBAKED.md Rule 1: "Dump trace data before modeling."
- The Maezawa driver has many one-off variants across Konami's catalog.
  The same period table does NOT prove the same driver. CV1's command
  format (DX reads 2 bytes) differs from Contra (DX reads 3 bytes) and
  from CV3 (different envelope model entirely). Attempting to run the
  CV1 parser on other Konami ROMs cost 3 prompts (MISTAKEBAKED.md
  Rules 2-3).
- Triangle pitch: the same period value produces a note 1 octave lower
  on triangle than on pulse (32-step vs 16-step sequencer). Changing
  BASE_MIDI_OCTAVE4 once broke triangle pitch and cost 2 prompts
  (MISTAKEBAKED.md Rule 8).
- A labeled disassembly exists on GitHub (josephstevenspgh/
  Castlevania-Labelled-Disassembly), incomplete but useful for
  cross-referencing the Maezawa driver structure.

**Synth Preset**
- Envelope mode: CC11-driven. ADSR must NOT override CC11 when file
  data is present. The synth's three-priority cascade handles this:
  SysEx -> CC11/CC12 -> ADSR. For file playback, CC11 is the envelope.
- Duty behavior: Pulse 1 expects duty=1 (25%), Pulse 2 expects duty=2
  (50%). CC12 values are set per-note but do not animate within notes.
  The synth should hold duty constant between CC12 updates.
- Noise channel: velocity-driven envelope (no CC11). Noise uses period
  index for pitch with the mode bit controlling tonal vs noise mode.
  Map kick=36, snare=38, hi-hat=42.
- Recommended starting point for all Standard Envelope family games.
  CV1's envelope shape (sharp attack, moderate decay, low sustain) is
  the archetype for Family 2.

---

### 2. Contra

**Attribution**
- Publisher: Konami, 1988
- Composers: Kazuki Muraoka, Hidenori Maezawa
- Driver programmer: Hidenori Maezawa (variant)

**Driver Family**
- Family 2: Standard Envelope. CC11/note ~4.5, CC12/note <0.5.
- Uses the same Maezawa driver lineage as CV1, but with significant
  command format differences. Volume envelope behavior is comparable:
  ~4-5 CC11 writes per note, software-controlled decay. Static duty
  per note. The envelope shape is slightly different from CV1 --
  Contra's action-oriented score uses sharper attacks and shorter
  sustains in many tracks.

**Hardware**
- Mapper 2 (UxROM). 128KB PRG-ROM, 8KB CHR-RAM. No expansion audio.
  Same mapper as CV1, but internal ROM layout differs.

**Music Architecture**
- Software envelope via Maezawa driver variant. Constant-volume mode
  with per-frame volume writes from lookup tables.
- DPCM used for kick and snare drums. The DPCM channel ($4010-$4013)
  plays stored delta-modulation samples for percussion hits. This
  supplements the noise channel, giving Contra a punchier drum sound
  than CV1.
- Triangle is 1 octave lower than pulse for the same period value
  (hardware fact, 32-step sequencer). The pitch_to_midi function
  subtracts 12 for triangle.
- The DX command reads 3 bytes after the opcode (not 2 like CV1).
  E8 has different semantics than CV1. EC is unused in CV1 but shifts
  pitch in Contra. These differences mean the CV1 parser cannot be
  used on Contra without modification.

**Pipeline Status**
- ROM parser exists. Validated at Rung 4 (trusted output).
- 0 pitch mismatches on pulse channels against Mesen trace.
- Proven pipeline alongside CV1. Both games serve as the validation
  reference for the Konami/Maezawa driver family.
- Route: both NSF emulation and trace pipeline available.

**Known Issues**
- The most expensive mistake in the project's history: assuming Contra
  used the same command format as CV1 because both are Konami games
  with the same period table. Cost 3+ prompts. The DX byte count
  difference (2 vs 3) broke the parser immediately. This is baked
  into MISTAKEBAKED.md Rules 2-4: "Same driver does not equal same
  ROM layout," "Same period table does not equal same driver," and
  "Read the disassembly before guessing."
- Parser versions v1-v4 had incorrect note splitting that prevented
  the Frame IR from applying correct envelope shaping. Moving all
  temporal shaping to the Frame IR (away from the parser) fixed both
  the volume model and duration accuracy. This led to Architecture
  Rule 1: "Parsers emit full-duration events."
- E8 envelope gate looked correct on Sq1 but was wrong for Sq2. Cost
  2 prompts. Baked into MISTAKEBAKED.md Rule 5: "Check all channels,
  not just one."
- Per-game differences between CV1 and Contra are documented in
  extraction/drivers/konami/spec.md as a comparison table. Future
  Konami games must be added to this table BEFORE writing their parser.

**Synth Preset**
- Envelope mode: CC11-driven. Same cascade priority as CV1.
- Duty behavior: similar to CV1. Per-note duty settings, no
  within-note animation.
- Noise channel: velocity-driven. Contra's noise channel works with
  DPCM drums layered on top -- the synth's noise channel handles the
  APU noise while DPCM samples are a separate concern (not currently
  synthesized by ReapNES Studio).
- DPCM drums are present in the NSF extraction as $4011 writes. The
  synth does not yet reproduce DPCM playback; noise channel
  approximation is used instead.

---

### 3. Wizards & Warriors

**Attribution**
- Publisher: Rare, 1987
- Composer: David Wise
- Driver programmer: Chris Stamper (initial), Mark Betteridge (later
  maintenance)

**Driver Family**
- Family 1: Hardware Envelope. CC11/note 0.1, CC12/note ~0.0.
- The Rare driver in its early configuration barely touches volume
  registers after the initial note-on. CC11/note of 0.1 means the
  driver writes volume approximately once every 10 notes -- essentially
  set-and-forget. The APU's hardware envelope generator handles decay.
  No duty animation. This is the most minimal envelope profile in the
  entire 65-game survey, tied with a handful of other early-era titles.

**Hardware**
- Mapper 1 (MMC1). PRG-ROM bank switching via MMC1 shift register.
  No expansion audio. Standard 5-channel APU.

**Music Architecture**
- Hardware envelope mode. The driver sets $4000/$4004 with the envelope
  decay rate and lets the APU's built-in linear decay generator shape
  the volume. No per-frame software volume writes.
- No DPCM usage. Percussion is entirely on the noise channel.
- David Wise composed in raw 6502 hex using the text editor Brief.
  Pitch and length encoded as hex pairs (e.g., "81,08" = low C,
  length 8). The driver doubles time counters during playback,
  affecting duration calculations.
- 16 songs in the NSF. The full soundtrack covers dungeon themes,
  boss music, and overworld tracks.

**Pipeline Status**
- ROM parser exists. Validated at Rung 2-3 (partial trust).
- All 16 songs validated at Rung 2 for melodic channels (512 frames
  each). Title track validated at Rung 3 against Mesen trace (2169
  frames). 48/48 melodic channel period matches confirmed.
- Noise channel is at Rung 1 only (structural) with partial Rung 2
  on 3 active songs. Noise is a separate semantic domain and requires
  independent investigation.
- Route: both NSF emulation and trace pipeline available. Trace is
  preferred for validation but NSF is sufficient for practical output.

**Known Issues**
- Noise channel semantics proved that noise is a separate domain from
  melodic channels. W&W had 48/48 melodic matches while noise remained
  only partially understood. This experience led to Architecture Rule
  16: "Noise is a separate semantic domain."
- The Rare driver's time counter doubling means raw duration bytes
  must be multiplied by 2 to get actual frame counts. Missing this
  produces notes at half their correct length.
- PAL playback on the Rare driver is a half-step lower than NTSC due
  to the different CPU clock rate. All our extraction assumes NTSC.
- W&W and Battletoads use the same Rare driver but produce radically
  different CC profiles (0.1 vs 4.1 CC11/note). This proves that
  driver family classification by CC density does not map 1:1 to
  driver authorship -- composer technique within the same engine
  determines the envelope density.

**Synth Preset**
- Envelope mode: ADSR. With CC11/note at 0.1, there is almost no CC
  data to drive the synth. ADSR mode (Priority 3 in the cascade) will
  be the primary envelope source for keyboard playback and will
  supplement the sparse CC data during file playback.
- For file playback, the synth should use the few CC11 events that
  exist but fill gaps with a gentle hardware-style linear decay. A
  short attack, moderate decay to ~40% sustain, and medium release
  approximates the APU hardware envelope.
- Duty behavior: static. No CC12 animation expected. Set duty to the
  game's characteristic value and hold.
- Noise channel: period-index percussion. Minimal volume shaping.
  Hardware envelope decay on noise channel.

---

### 4. Battletoads

**Attribution**
- Publisher: Rare, 1991
- Composer: David Wise
- Driver programmer: Mark Betteridge

**Driver Family**
- Family 2: Standard Envelope. CC11/note 4.1 (NSF extraction), ~4.7-4.8
  (trace data). CC12/note <0.5.
- The same Rare driver as Wizards & Warriors, but David Wise's later
  compositional technique uses far more per-frame volume automation.
  The driver was likely enhanced by Betteridge for the Battletoads era,
  or Wise simply used more of the driver's envelope capabilities. The
  jump from 0.1 to 4.1 CC11/note within the same engine lineage is the
  strongest evidence that composer technique, not driver architecture,
  determines family membership.

**Hardware**
- Mapper 7 (AxROM). 256KB PRG-ROM. Single-screen mirroring (switchable).
  No expansion audio. AxROM provides 32KB bank switching, which
  Battletoads uses for its large codebase.

**Music Architecture**
- Software envelope with per-frame volume writes. Standard
  constant-volume mode. The envelope tables produce the characteristic
  Battletoads sound: punchy attacks with rapid decay.
- DPCM drums are ALGORITHMIC, not stored samples. This is confirmed
  by the NESDev forum thread (viewtopic.php?t=15586). The driver
  writes computed ramp waveforms to $4011 (the DMC DAC direct register)
  to generate triangular waveforms at variable speed and length. This
  saves ROM space while producing distinctive percussion that sounds
  unlike any other NES game. The $4011 writes visible in traces are
  computed values, not delta-modulation sample playback.
- CPU performance: the Battletoads engine averages 482 cycles/frame
  with 1820 peak, lower than some alternatives, reducing the risk of
  audio lag during gameplay.
- The arpeggio system is a defining feature of Battletoads' sound:
  rapid pitch cycling within a single note creates chord-like effects.
  This system was entirely unmodeled in parser v3.

**Pipeline Status**
- ROM parser exists. Validated at Rung 1 only (parser-aligned).
  Execution semantics validation is in progress.
- Route: NSF emulation for practical output. Trace pipeline for
  validation. NSF may diverge from actual in-game audio (confirmed
  behavior for Battletoads).
- Current output is hypothesis output, not trusted. Usable for
  practical listening and arrangement work but not claimable as
  verified extraction.

**Known Issues**
- THE CANONICAL EXAMPLE of why zero parse errors does not equal musical
  correctness. Parser v3 achieved zero parse errors with 955 notes
  across all channels. However: duration accounting was off by 1.52x
  (tempo accumulator overflow logic was wrong), and the arpeggio system
  was entirely unmodeled. The parser correctly identified every command
  boundary but the music sounded wrong. This cost 5+ prompts and led
  to Architecture Rules 13-14: "Zero parse errors is not musical
  correctness" and "Execution semantics validation is mandatory."
- Parser output was initially treated as music rather than hypothesis.
  "955 notes, 0 errors" gave false confidence. This experience is
  baked into every validation gate in the project. Parser alignment
  (Gate 1) is structural only; execution semantics (Gate 2) must pass
  before any output is labeled trusted.
- NSF extraction diverges from in-game audio. Mesen trace is required
  for ground truth. The NSF CC11/note (4.1) and trace CC11/note
  (~4.7-4.8) differ, confirming the divergence.
- The algorithmic PCM drum synthesis means the noise/DPCM channel
  cannot be modeled by standard approaches. The $4011 DAC writes
  create waveforms that do not correspond to the DPCM sample playback
  mechanism. This requires custom handling in the synth or acceptance
  that drum reproduction will be approximate.

**Synth Preset**
- Envelope mode: CC11-driven for file playback. The 4.1 CC11/note
  density provides sufficient envelope data.
- Duty behavior: static per note. No within-note duty animation.
- Noise channel: complex. The algorithmic PCM drums write to $4011
  (DMC DAC) rather than using the noise channel ($400C-$400F) or
  DPCM sample playback ($4010-$4013). ReapNES Studio does not
  currently model $4011 DAC synthesis. Expect approximate drum
  reproduction. The noise channel proper may carry additional
  percussion or be silent depending on the track.
- Arpeggio: if/when the arpeggio system is modeled in the parser,
  the synth will need to handle rapid pitch changes (potentially
  every frame) within a single logical note. The synth's note-on/
  note-off mechanism handles this via period-change detection.
- Game-specific preset should use sharper attack and faster decay
  than the CV1 preset to match Battletoads' percussive melodic style.

---

### 5. Super Mario Bros

**Attribution**
- Publisher: Nintendo, 1985
- Composer: Koji Kondo
- Driver programmer: Koji Kondo (wrote his own driver variant in pure
  6502 assembly)

**Driver Family**
- Family 3: Duty Animators. CC11/note 4.9, CC12/note 0.8.
- SMB1 animates both volume AND duty cycle within notes. The CC12/note
  of 0.8 means approximately one duty change per note on average,
  creating timbral movement: brighter attack (higher duty) transitioning
  to mellower sustain (lower duty). This dual-axis animation is the
  defining characteristic of the Duty Animators family.
- Note: SMB1 appears in both Family 3 (v3 extraction, CC11/note 4.9)
  and Family 2 (v2 extraction, CC11/note 4.8, CC12/note 0.8) depending
  on extraction version/parameters. The v3 classification is canonical.

**Hardware**
- Mapper 0 (NROM). 32KB PRG-ROM, 8KB CHR-ROM. No expansion audio.
  No bank switching. The entire game including music fits in 32KB,
  making it one of the smallest NES ROMs with a sophisticated sound
  engine.

**Music Architecture**
- Software envelope with both volume and duty animation. Kondo's driver
  writes to both $4000 (volume/duty) and $4001 (sweep) per frame on
  pulse channels. The duty animation produces the characteristic SMB1
  timbre: each note starts bright and softens.
- No DPCM usage. All sound fits within the 4 standard APU channels.
  Percussion is on the noise channel.
- Kondo composed the music directly in 6502 assembly. No MML, no
  tracker, no intermediate tool. The music data is hand-optimized
  assembly code, which is why the sound engine is tightly coupled to
  the composition.
- Approximately 6 distinct musical pieces (overworld, underground,
  underwater, castle, star, game over/misc).

**Pipeline Status**
- NSF only. No ROM parser exists or is planned.
- No validation rung assigned (NSF-only games bypass the ROM parsing
  validation ladder).
- Route: NSF emulation exclusively. NSF is confirmed to diverge from
  actual in-game audio in some cases, but no Mesen trace pipeline
  exists for SMB1.

**Known Issues**
- NSF divergence from in-game audio is confirmed for Mario titles
  generally. The NSF packages the sound engine code but runs it in a
  different execution context than the actual game. Timing differences
  can produce subtle variations. This finding contributed to the
  project's policy that Mesen trace is ground truth and NSF is
  convenience (MISTAKEBAKED.md context).
- The variation between extraction versions (v2 vs v3 producing
  different family classifications) indicates sensitivity to extraction
  parameters. The CC12/note of 0.8 is consistent across versions; the
  CC11/note varies between 4.8 and 4.9.
- Kondo's driver is poorly documented compared to third-party engines.
  No VGMPF driver page exists with byte-level format documentation.
  The Nintendo-internal driver family is the least understood of the
  major publishers.

**Synth Preset**
- Envelope mode: CC11-driven for file playback. The 4.9 CC11/note
  density provides good envelope resolution.
- Duty behavior: ACTIVE. CC12 automation is present and meaningful.
  The synth must respond to CC12 changes within notes, not just at
  note boundaries. Expect ~1 duty change per note creating a bright-
  to-mellow timbral sweep. CC12 mapping: 0-31->0 (12.5%), 32-63->1
  (25%), 64-95->2 (50%), 96-127->3 (75%).
- Noise channel: velocity-driven percussion. Standard kick/snare/
  hi-hat mapping.
- The SMB1 preset should be the reference for all Duty Animators
  family games. Key difference from Standard Envelope presets: the
  synth must actively animate duty cycle, not hold it static.

---

### 6. Super Mario Bros 2

**Attribution**
- Publisher: Nintendo, 1988
- Composer: Koji Kondo
- Driver programmer: Nintendo internal (possibly Hirokazu Tanaka
  variant or a separate internal driver; attribution uncertain)

**Driver Family**
- Family 4: Dense Automators. CC11/note in the 5.1-7.0 range.
  CC12/note <0.3.
- SMB2 uses a different sound engine from SMB1. The higher CC11
  density and near-zero CC12 density place it in the Dense Automators
  family: obsessive per-frame volume writes with static duty. This
  aligns with the Tanaka driver variant used in other Nintendo titles
  like Metroid and Kid Icarus (both ~5.1 CC11/note).

**Hardware**
- Mapper 4 (MMC3). 128KB PRG-ROM, 128KB CHR-ROM. No expansion audio.
  MMC3 provides IRQ-based scanline counting, but this is irrelevant
  to the sound engine. The larger PRG-ROM accommodates SMB2's more
  complex game code and music data.

**Music Architecture**
- Software envelope with dense per-frame volume automation. The driver
  writes volume every frame (or nearly so), producing smooth volume
  contours. Duty cycle is set per note but not animated within notes.
- No DPCM usage for music. Standard 4-channel APU.
- SMB2 (the US version) is a reskin of Doki Doki Panic (Fuji Television/
  Nintendo, 1987). The music was composed for the original Japanese
  game and reused. The sound engine may therefore be the Doki Doki
  Panic engine rather than a continuation of the SMB1 engine.
- More tracks than SMB1: overworld, underground, multiple boss themes,
  character select, bonus game, ending.

**Pipeline Status**
- NSF only. No ROM parser.
- Route: NSF emulation exclusively.

**Known Issues**
- Driver attribution is uncertain. The sound engine differs from both
  SMB1 (Kondo's personal driver) and SMB3 (Kondo's late variant).
  The Dense Automator profile suggests possible Tanaka influence, but
  this is speculative.
- As a reskinned Doki Doki Panic, the music engine may have different
  provenance than other Nintendo first-party titles. VGMPF does not
  provide definitive driver programmer attribution for this title.

**Synth Preset**
- Envelope mode: CC11-driven. Dense CC11 data provides excellent
  envelope resolution, potentially smoother than Standard Envelope
  family games.
- Duty behavior: static. Set duty per note and hold. No CC12
  animation expected.
- Noise channel: velocity-driven. Standard percussion mapping.
- Preset should use a smoother envelope curve than the CV1/Contra
  Standard Envelope preset, reflecting the denser volume automation
  that produces more gradual attack/decay/release transitions.

---

### 7. Super Mario Bros 3

**Attribution**
- Publisher: Nintendo, 1988
- Composer: Koji Kondo
- Driver programmer: Koji Kondo (late variant of his personal driver)

**Driver Family**
- Family 5: Full Animation. CC11/note 7.7, CC12/note 1.3. THE SOLE
  MEMBER of this family across the entire 65-game survey.
- SMB3 is the only game that achieves high density on BOTH the volume
  axis (CC11) and the duty axis (CC12) simultaneously. Every other
  game in the survey either automates volume heavily with static duty
  (Dense Automators) or animates both axes at moderate density (Duty
  Animators). SMB3 does both at maximum intensity. This represents
  the pinnacle of NES sound programming.

**Hardware**
- Mapper 4 (MMC3). 256KB PRG-ROM, 128KB CHR-ROM. No expansion audio.
  The largest Mario PRG-ROM, providing space for the most sophisticated
  sound engine in the Mario series.

**Music Architecture**
- Software envelope with maximum per-frame automation of both volume
  and duty cycle. The driver writes to $4000/$4004 (volume + duty)
  every frame on pulse channels. CC11/note of 7.7 means approximately
  8 volume writes per note; CC12/note of 1.3 means more than one duty
  change per note on average. This creates constantly shifting timbre
  throughout every sustained note.
- DPCM used for drum samples. The DPCM channel provides kick and
  snare percussion, supplementing the noise channel. This is an
  evolution from SMB1's noise-only percussion.
- The sound engine handles a large number of tracks: world map themes
  (8 worlds), level themes (multiple per world type), boss music,
  minigames, fanfares, and ending sequences. Total track count
  exceeds 30.
- Kondo's late driver variant is among the most sophisticated on the
  platform. The CPU cost of per-frame dual-axis automation is
  significant, but SMB3's optimized engine handles it within the
  NMI timing budget.

**Pipeline Status**
- NSF only. No ROM parser.
- Route: NSF emulation exclusively.
- The Full Animation family's unique density profile makes SMB3 the
  most demanding game for the synth to reproduce accurately. Every
  frame carries meaningful volume AND duty information.

**Known Issues**
- As the sole member of Family 5, there is no other game to
  cross-validate the family's characteristics against. The family
  definition is based entirely on SMB3's profile.
- The high CC12 density means the synth must process duty changes
  within notes at a rate exceeding 1 per note. Any latency in CC12
  processing will produce audible timbre artifacts. The synth's CC12
  mapping (0-31->0, 32-63->1, 64-95->2, 96-127->3) must be applied
  without smoothing or interpolation to preserve the frame-level
  duty switching Kondo intended.
- Like all Mario titles, NSF may diverge from in-game audio. No Mesen
  trace validation has been performed.

**Synth Preset**
- Envelope mode: CC11-driven. The 7.7 CC11/note density provides
  near-frame-level volume resolution. ADSR must not interfere.
- Duty behavior: HIGHLY ACTIVE. CC12/note of 1.3 means duty changes
  more than once per note on average. The synth must apply CC12
  updates immediately on receipt with zero smoothing. This is the
  most duty-active game in the library and the only game where duty
  animation is a primary sonic characteristic rather than a secondary
  effect.
- Noise channel: velocity-driven, supplemented by DPCM drums.
- The SMB3 preset should be the reference for maximum-fidelity CC
  playback. If the synth reproduces SMB3 correctly -- dense volume
  AND dense duty, both frame-accurate -- it can handle any game in
  the library.

---

### 8. Mega Man 1

**Attribution**
- Publisher: Capcom, 1987
- Composer: Manami Matsumae
- Driver programmer: Yoshihiro Sakaguchi

**Driver Family**
- Family 1: Hardware Envelope. CC11/note 0.2, CC12/note ~0.0.
- The Sakaguchi driver sets volume once at note-on and relies on the
  APU's hardware envelope generator for decay. CC11/note of 0.2 means
  the driver writes volume approximately once every 5 notes -- almost
  nothing. No duty animation. This is the minimal-automation archetype:
  the driver trusts the hardware to shape the sound.

**Hardware**
- Mapper 1 (MMC1). 128KB PRG-ROM, 32KB CHR-ROM. No expansion audio.
  Capcom never used expansion audio chips on any NES title, making
  their entire catalog standard-APU-only.

**Music Architecture**
- Hardware envelope mode. The driver writes $4000/$4004 with envelope
  period and decay rate settings at note-on. The APU's built-in
  envelope generator provides linear decay from the initial volume to
  zero (or looping). Per-frame software volume writes are essentially
  absent.
- No DPCM usage. All sound on 4 standard channels. Percussion is
  noise-channel only.
- MML-based composition. Composers wrote music in Capcom's custom
  hexadecimal Music Macro Language, which was then compiled into the
  ROM's music data format. This MML workflow produced clean, structured
  note patterns with fixed envelope settings per instrument.
- Approximately 15 tracks (title, stage select, 6 robot master stages,
  Wily stages, boss, ending, etc.).

**Pipeline Status**
- NSF only. No ROM parser.
- Route: NSF emulation exclusively.
- The Capcom 6C80 Sound Engine documentation on romhacking.net
  (document #274) covers the music data format for Mega Man 3 onward.
  A separate document (#875, "Sound Engine 1") covers earlier Capcom
  titles including Mega Man 1. If ROM parsing is ever needed, these
  are the starting points.

**Known Issues**
- With CC11/note of 0.2, the NSF extraction produces very sparse
  volume automation. The resulting MIDI files have almost no CC11
  data, meaning the synth must rely on ADSR mode or hardware envelope
  emulation to produce musically satisfying playback.
- The sparse CC profile means that small differences in extraction
  parameters can shift the CC11/note count significantly in percentage
  terms (e.g., 0.2 to 0.3 is a 50% increase but still negligible in
  absolute terms).
- Capcom's MML workflow means the music data format is well-documented
  and regular. Byte-level format specs exist. If ROM-level extraction
  is ever needed, Capcom games are among the most tractable targets.

**Synth Preset**
- Envelope mode: ADSR is the primary mode. With CC11/note at 0.2,
  there is insufficient CC data to drive the synth's volume. The ADSR
  envelope must carry the entire note shape.
- Recommended ADSR: moderate attack (~2-3 frames), linear decay to
  ~30% over ~10-15 frames, low sustain, moderate release. This
  approximates the APU hardware envelope's linear decay behavior.
- Duty behavior: static. Set per instrument definition in the MML.
  No within-note animation. Typical Mega Man 1 duty: 50% (duty=2) for
  lead melodies, 25% (duty=1) for secondary voices.
- Noise channel: velocity-driven with hardware envelope decay.
  Standard percussion mapping.
- The Mega Man 1 preset should be the reference for all Hardware
  Envelope family games. The key challenge is making ADSR sound
  musical despite the absence of per-frame volume data.

---

### 9. Mega Man 2

**Attribution**
- Publisher: Capcom, 1988
- Composers: Takashi Tateishi (credited as Ogeretsu Kun), Manami
  Matsumae, Yoshihiro Sakaguchi
- Driver programmer: Yoshihiro Sakaguchi

**Driver Family**
- Family 1: Hardware Envelope. CC11/note 0.8, CC12/note ~0.0.
- Same Sakaguchi driver as Mega Man 1 with slightly more volume
  automation. The CC11/note of 0.8 is 4x higher than MM1's 0.2 but
  still firmly in the Hardware Envelope range (Family 1 spans 0.1-2.8).
  The increase likely reflects minor driver refinements or compositional
  choices that include occasional volume adjustments (e.g., echo effects
  via volume reduction on repeated notes).

**Hardware**
- Mapper 1 (MMC1). 256KB PRG-ROM, 32KB CHR-ROM. No expansion audio.
  Double the PRG-ROM of MM1, accommodating MM2's larger game and more
  music data.

**Music Architecture**
- Primarily hardware envelope mode, same as MM1. The moderate increase
  in CC11/note (0.8 vs 0.2) suggests some notes receive software
  volume adjustments, but the overall approach remains set-volume-and-
  let-hardware-decay.
- No DPCM usage. 4 standard channels only.
- MML-based composition via the Sakaguchi driver. Takashi Tateishi
  composed most of the soundtrack (including the famous Wily Stage 1
  theme) while Matsumae and Sakaguchi contributed additional tracks.
- Approximately 20+ tracks (title, stage select, 8 robot master stages,
  Wily stages, boss, password, ending, etc.).

**Pipeline Status**
- NSF only. No ROM parser.
- Route: NSF emulation exclusively.
- The Capcom 6C80 documentation may cover MM2's format partially,
  though MM2 predates the "6C80" engine revision. Sound Engine 1
  documentation (romhacking.net #875) is more likely applicable.

**Known Issues**
- Despite being one of the most beloved NES soundtracks, MM2's
  Hardware Envelope profile means the synth relies heavily on ADSR
  approximation. The music works despite minimal volume automation
  because the compositional quality carries it -- strong melodies,
  effective use of counterpoint, and rhythmic drive compensate for
  simple envelope shapes.
- The 0.8 CC11/note is borderline. Some notes will have CC11 data
  (and should use it), while most will fall through to ADSR mode. The
  synth's cascade priority system handles this correctly: when CC11
  arrives, it overrides ADSR; when no CC11 is present, ADSR fills in.

**Synth Preset**
- Envelope mode: ADSR primary, CC11 supplementary. Same approach as
  MM1 but slightly more CC11 events will be present.
- Recommended ADSR: same as MM1 preset. Moderate attack, linear decay,
  low sustain. The two games use the same driver and the ADSR
  approximation should be identical.
- Duty behavior: static. Duty=2 (50%) is common for lead voices in
  MM2. Duty=1 (25%) for secondary voices.
- Noise channel: velocity-driven, hardware envelope decay. MM2's
  percussion patterns are more complex than MM1's but use the same
  noise channel mechanism.

---

### 10. DuckTales

**Attribution**
- Publisher: Capcom, 1989
- Composer: Hiroshige Tonomura
- Driver programmer: Yoshihiro Sakaguchi

**Driver Family**
- Family 1: Hardware Envelope. CC11/note 0.8, CC12/note ~0.0.
- Same Sakaguchi driver as Mega Man 1-2. Identical CC11/note to MM2
  (0.8). The Capcom MML workflow produces a consistent envelope profile
  across the company's entire catalog regardless of composer. Tonomura
  composed DuckTales but the driver determines the automation density,
  and Sakaguchi's driver is reliably minimal.

**Hardware**
- Mapper 1 (MMC1). 128KB PRG-ROM, 32KB CHR-ROM. No expansion audio.
  Standard Capcom hardware configuration.

**Music Architecture**
- Hardware envelope mode, identical to MM1/MM2. Volume set at note-on,
  hardware decay handles the rest. Occasional software volume writes
  produce the 0.8 CC11/note average.
- No DPCM usage. 4 standard channels.
- MML-based composition through Sakaguchi's driver. Tonomura's
  compositional approach within the MML framework emphasizes
  arpeggiated bass lines on triangle and call-and-response patterns
  between pulse channels.
- Approximately 10-12 tracks (title, stage select, 5 stages,
  boss, Transylvania/moon/etc., ending).
- The Moon theme is one of the most recognized NES compositions in
  the entire library. Its effectiveness despite minimal envelope
  automation demonstrates that compositional craft can transcend
  driver limitations. The melody's intervallic construction, the
  triangle bass's rhythmic drive, and the pulse channel interplay
  create a complete musical statement using only the barest envelope
  tools.

**Pipeline Status**
- NSF only. No ROM parser.
- Route: NSF emulation exclusively.
- Capcom 6C80 documentation may apply (DuckTales is a 1989 title,
  potentially using the later engine revision). Sound Engine 1
  documentation (#875) is the fallback.

**Known Issues**
- Same sparse-CC challenge as all Sakaguchi-driver games. The synth
  must produce musically satisfying output from minimal volume data.
  ADSR approximation is critical.
- The Moon theme's fame makes it a natural demonstration/test track
  for the synth. If ADSR playback of the Moon theme sounds good, the
  Hardware Envelope family preset is validated for practical use.
- Capcom's consistent driver usage means any preset tuned for MM1/MM2
  should work equally well for DuckTales. The three games are
  effectively identical from the synth's perspective.

**Synth Preset**
- Envelope mode: ADSR primary, same as MM1/MM2. The Sakaguchi driver
  games form a cohesive preset group.
- Recommended ADSR: identical to the Mega Man preset. Moderate attack,
  linear decay to ~30%, low sustain, moderate release. All three games
  use the same driver with the same envelope characteristics.
- Duty behavior: static. No CC12 animation.
- Noise channel: velocity-driven, hardware envelope decay.
- Consider making a single "Capcom (Sakaguchi)" preset that covers
  MM1, MM2, DuckTales, and all other Sakaguchi-driver games. The
  driver's consistency across 30+ titles means one preset serves the
  entire Capcom NES catalog (early-to-mid era).

# NES Game Profiles: Part 2 (Games 11-20)

Technical reference for ReapNES Studio. Each profile documents driver
family, hardware configuration, music architecture, pipeline status,
and synth preset recommendations.

Driver family taxonomy uses renamed families:
- Family 1: Hardware Envelope (formerly Minimal)
- Family 2: Standard Envelope (formerly Sunsoft-style)
- Family 3: Duty Animators (formerly Capcom Duty Switchers)
- Family 4: Dense Automators
- Family 5: Full Animation

---

### 11. Darkwing Duck

**Attribution**
- Publisher: Capcom, 1992. Composer: Yasuaki Fujita (Bun Bun).
  Driver programmer: likely Make Software (late-era Capcom replacement
  for Sakaguchi's driver). VGMPF attributes Capcom's final NES titles
  to the Make Software driver rather than Sakaguchi's original.

**Driver Family**
- Family 1 (Hardware Envelope). Capcom games cluster reliably in
  Family 1 across the entire catalog, from 1942 (1985) through the
  final titles. CC11/note density expected in the 0.8-2.2 range
  consistent with other late Capcom titles (DuckTales 0.8, Strider
  1.0). CC12/note near zero -- Capcom drivers do not animate duty
  cycle per frame.
- Belongs here because the Capcom driver philosophy is fundamentally
  hands-off: set volume via constant-volume mode or hardware envelope
  decay, then let the APU do the work. The MML composition workflow
  produces clean, structured note patterns with minimal per-frame
  register writes.

**Hardware**
- Mapper 4 (MMC3). No expansion audio. Capcom never used expansion
  audio chips on any NES title.

**Music Architecture**
- Hardware envelope with minimal software volume control. The driver
  sets initial volume and duty per note, relying on the APU's built-in
  linear decay or constant-volume mode for sustain behavior.
- No DPCM bass. DPCM channel used for drum samples only (kick, snare).
- Late-era Capcom title -- if using the Make Software driver, the
  composition tool was reportedly more user-friendly than Sakaguchi's
  raw hex MML, but the output envelope behavior remains in the same
  Hardware Envelope family. The Make Software driver did not add dense
  per-frame volume automation.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined). NSF files exist in output directory.
- Route: NSF emulation -> per-frame CC11/CC12 extraction -> MIDI -> REAPER.

**Known Issues**
- The Make Software vs Sakaguchi driver distinction may produce subtle
  differences in envelope shape compared to earlier Capcom titles.
  If extraction shows CC11/note above 3.0, the driver may have been
  revised to include more software envelope control than the original
  Sakaguchi engine.
- Late Capcom titles sometimes have more complex arrangements that
  stress the 4-channel limit, producing rapid note switching that can
  look like higher CC density in extraction.

**Synth Preset**
- Channel Mode: Pulse 1 (0), Pulse 2 (1), Triangle (2), Noise (3).
- ADSR: Short attack (2-5ms), moderate decay (50-80ms), sustain 40-50%,
  release 30ms. Capcom's characteristic clean tone.
- Duty: Pulse 1 at 25% (duty 1), Pulse 2 at 50% (duty 2). Static
  per note -- no per-frame duty animation needed.
- Volume: Let CC11 drive if present; otherwise ADSR shapes the note.

---

### 12. Castlevania III: Dracula's Curse (US)

**Attribution**
- Publisher: Konami, 1989. Composers: Hidenori Maezawa, Jun Funahashi,
  Yukie Morimoto, Yoshinori Sasaki. Driver programmer: Konami internal
  (Maezawa variant). The US version uses a modified Konami driver
  stripped of VRC6 expansion support.

**Driver Family**
- Family 3 (Duty Animators). CC11/note 4.6, CC12/note 0.8.
- The CC12 density of 0.8 per note places this firmly in the Duty
  Animators family. The driver actively switches duty cycle during
  sustained notes, producing timbral movement within each note --
  brighter attack transitioning to mellower sustain. This duty
  animation is not present in most Konami titles (CV1 has near-zero
  CC12/note), making CV3 an outlier within the Konami driver lineage.

**Hardware**
- Mapper 5 (MMC5) in the US release. The Japanese version (Akumajou
  Densetsu) used Mapper 24 (VRC6), adding 2 extra pulse channels and
  1 sawtooth wave channel. The US cartridge uses MMC5 for banking but
  does not use MMC5's extra audio channels.
- No expansion audio in the US version. The VRC6 expansion channels
  from the Japanese release were removed entirely, and the music was
  rearranged for the standard 5-channel APU.

**Music Architecture**
- Software-driven volume envelope with active duty cycle animation.
  The Konami driver writes volume (CC11) approximately 4.6 times per
  note and duty (CC12) approximately 0.8 times per note.
- The duty animation likely originates from the rearrangement process:
  when Konami adapted the VRC6 arrangement (which had 6 melodic
  channels) down to 4 standard channels, they may have used duty
  switching to compensate for the lost timbral variety of the extra
  VRC6 channels.
- DPCM used for kick and snare drums, consistent with standard Konami
  practice.
- The Japanese version (CC12/note 1.0) shows even higher duty
  animation, reflecting the additional VRC6 channel activity captured
  in NSF extraction even though the standard APU channels are the
  primary focus.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.
- A full disassembly exists in the cyneprepou4uk/NES-Games-Disassembly
  GitHub repository (Castlevania III is listed). This could support a
  future ROM parser if NSF fidelity proves insufficient.

**Known Issues**
- The US and Japanese NSF files produce different CC density profiles
  (0.8 vs 1.0 CC12/note). When working with CV3, always verify which
  region's NSF is being extracted.
- The Konami driver has many one-off variants. Do not assume CV1
  parser code will work on CV3 -- the driver was significantly revised
  between games. Pointer table format, command byte counts, and
  envelope semantics all differ.
- The rearrangement from VRC6 to standard APU means the US soundtrack
  is musically different from the Japanese original. Some passages
  that sounded clean with 6 channels become crowded on 4.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: Attack 3-5ms, decay 60-100ms, sustain 50-60%, release 40ms.
  Slightly longer decay than CV1 to accommodate the duty animation.
- Duty: Let CC12 automation drive duty changes. Do not set a static
  duty -- the duty animation is the defining characteristic of this
  game's sound.
- Volume: CC11-driven. The 4.6 CC11/note density provides detailed
  per-frame volume shaping.

---

### 13. Final Fantasy

**Attribution**
- Publisher: Square, 1987. Composer: Nobuo Uematsu. Driver programmer:
  Toshiaki Imai. Uematsu composed on an MSX computer using MML (Music
  Macro Language) notation, writing note data as text strings (e.g.,
  "C8" for an eighth-note C). Imai transplanted the MML data into his
  custom 6502 sound driver for the NES.

**Driver Family**
- Family 4 (Dense Automators). CC11/note 14.9 -- the DENSEST game in
  the entire 65-game survey. CC12/note 0.0 -- zero duty animation.
- This is the crown jewel of Family 4. The Imai driver writes volume
  to the APU almost 15 times per note on average, meaning multiple
  volume updates per frame. Despite this obsessive volume automation,
  the driver never touches the duty cycle register after initial note
  setup. The result is a sound with extraordinary dynamic shaping but
  completely static timbre per note.
- The extreme CC11 density with zero CC12 density is the purest
  expression of the Dense Automator philosophy: every CPU cycle spent
  on volume control, none on duty animation.

**Hardware**
- Mapper 1 (MMC1). No expansion audio. Square never used expansion
  audio on NES.

**Music Architecture**
- Pure software-driven volume envelope with per-frame (and possibly
  sub-frame) volume updates. The driver maintains volume envelope
  tables that are indexed per tick, producing the 14.9 CC11/note
  density. This is constant-volume mode ($4000 bit 4 set) with the
  driver writing the volume nibble directly every frame.
- Zero duty animation. Duty is set once per note and held constant.
  Pulse 1 and Pulse 2 each use a fixed duty cycle for the duration
  of each note.
- No DPCM bass. No DPCM drums. The delta modulation channel appears
  unused or minimally used. All four melodic channels (2 pulse,
  triangle, noise) carry the full arrangement.
- Uematsu's MSX/MML composition workflow explains the musical
  sophistication -- he was composing on a real instrument with a
  text-based notation system, not entering hex bytes directly.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.
- The extreme CC11 density (14.9/note) means extracted MIDI files will
  contain very dense CC11 automation lanes. REAPER projects need to
  handle this without performance degradation.

**Known Issues**
- At 14.9 CC11/note, the volume automation is so dense that the CC11
  lane in MIDI may contain more events than note events. Ensure the
  REAPER project's CC display scales appropriately.
- The zero CC12/note means the synth should use a static duty preset.
  Any duty animation in playback would be an extraction artifact, not
  intentional.
- Square used a different driver programmer (Hiroshi Nakamura) starting
  with Final Fantasy II. Do not assume the Imai driver's behavior
  extends to later Square titles.
- 3-D Battles of WorldRunner (5.4 CC11/note) uses the same Imai driver
  lineage but at much lower density, confirming that even within a
  single driver, the composer's data determines the CC density profile.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: Not applicable for file playback -- CC11 automation IS the
  envelope. For keyboard mode: attack 1-2ms, long decay (150-200ms),
  sustain 30-40%, release 50ms. Simulate the gradual volume sculpting
  characteristic of Uematsu's writing.
- Duty: Static. Pulse 1 at 50% (duty 2), Pulse 2 at 25% (duty 1).
  No CC12 animation to replay.
- Volume: CC11 must drive volume at full density. This game is the
  stress test for the CC11 playback path -- if it sounds right, the
  CC pipeline handles everything.

---

### 14. Blaster Master

**Attribution**
- Publisher: Sunsoft, 1988. Composer: Naoki Kodaka. Driver programmer:
  Akito Takeuchi. Kodaka's score is widely regarded as one of the finest
  on the NES. Takeuchi's driver enabled the DPCM bass technique that
  became Sunsoft's sonic signature.

**Driver Family**
- Family 4 (Dense Automators). CC11/note 11.7 -- second densest in
  the survey after Final Fantasy.
- Belongs in Family 4 due to aggressive per-frame volume automation.
  The Takeuchi driver writes volume nearly 12 times per note, producing
  detailed attack-decay-sustain shapes that give each note a punchy,
  dynamic character. CC12/note is low (near zero), consistent with
  Dense Automator behavior: all CPU effort goes to volume, not duty.

**Hardware**
- Mapper 1 (MMC1). No expansion audio chips.

**Music Architecture**
- Software-driven volume envelope with extremely dense per-frame
  updates. The driver uses constant-volume mode and writes to $4000/$4004
  every frame with computed envelope values.
- DPCM bass -- Sunsoft's signature technique. The delta modulation
  channel ($4010-$4013) plays pitched bass notes using samples from
  an AKAI S700 sampler, optimized for NES memory constraints. The
  implementation uses approximately 5 samples (A#, B, C, C#, D) at
  native pitches, with the DPCM playback rate register ($4010)
  shifting pitch for other notes in the bass range.
- The DPCM bass frees the triangle channel for melody or harmony,
  giving Blaster Master an unusually full sound for a 4-channel system.
  Most NES games dedicate triangle to bass; Sunsoft games effectively
  have a 5th melodic voice.
- DPCM also used for drum hits (kick, snare) alongside the pitched
  bass, requiring careful multiplexing of the single DPCM channel
  between bass notes and percussion.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.
- A Sunsoft audio engine analysis document exists on Romhacking.net
  (document #665). This could support a future ROM parser.

**Known Issues**
- The DPCM bass creates extraction complexity. The delta modulation
  channel does not map cleanly to MIDI note events the way pulse and
  triangle do. DPCM output appears as $4011 DAC writes in traces,
  not as period register changes. NSF extraction handles this through
  emulation, but the resulting MIDI representation of the bass channel
  may be approximate.
- The DPCM channel shares the APU's triangle/noise/DMC mixer DAC.
  DPCM playback affects triangle and noise output levels through
  non-linear mixing. This interaction is captured in NSF emulation
  but is not modeled in the ReapNES synth.
- At 11.7 CC11/note, the volume automation density is very high.
  REAPER projects will have dense CC11 lanes.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 1ms (punchy), fast decay (40-60ms),
  sustain 50-60%, release 20ms. The Sunsoft punch-decay shape is the
  defining sonic characteristic.
- Duty: Pulse 1 at 50% (duty 2), Pulse 2 at 25% (duty 1). Static.
- Volume: CC11-driven. The 11.7/note density provides near-continuous
  volume shaping. The synth must respond to rapid CC11 changes without
  smoothing or latency.
- Note: DPCM bass channel is not reproducible through the current
  ReapNES pulse/triangle/noise synthesis. The bass will either be
  missing or approximated via triangle in REAPER projects.

---

### 15. Journey to Silius

**Attribution**
- Publisher: Sunsoft, 1990. Composer: Naoki Kodaka. Driver programmer:
  Shinichi Seya. Seya reprogrammed the Sunsoft driver to use MML input,
  replacing the earlier assembly-level data entry. The game was
  originally planned as a licensed Terminator title; after the license
  fell through, Sunsoft reworked the game but kept Kodaka's sci-fi
  influenced score.

**Driver Family**
- Family 4 (Dense Automators). CC11/note 7.8.
- Sits in the lower range of Family 4 but clearly above the Standard
  Envelope ceiling of 5.6. The dense volume automation produces the
  aggressive, punchy envelope characteristic of all Sunsoft titles.
  CC12/note near zero -- consistent with Dense Automator behavior.

**Hardware**
- Mapper 1 (MMC1). No expansion audio.

**Music Architecture**
- Software-driven volume envelope with dense per-frame updates via
  constant-volume mode. Same Sunsoft engineering philosophy as Blaster
  Master, though with a different driver programmer (Seya vs Takeuchi).
- DPCM bass -- same technique as Blaster Master. Uses 5 samples at
  different native pitches (A#, B, C, C#, D) with the DPCM rate
  register providing pitch shifting across the bass range. The samples
  originated from an AKAI S700 sampler.
- The DPCM bass again frees the triangle for melodic use. Journey to
  Silius exploits this fully, with triangle carrying counter-melodies
  and harmony parts rather than bass lines.
- Percussion uses DPCM for kicks and snares, multiplexed with the
  bass on the single DPCM channel. The noise channel provides hi-hats
  and cymbal-like sounds.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.

**Known Issues**
- Same DPCM bass extraction issues as Blaster Master. The bass channel
  representation in MIDI is approximate.
- The Seya driver (MML-based) may produce slightly different envelope
  curves than the Takeuchi driver (Blaster Master) despite both being
  Sunsoft titles. Do not copy envelope presets between games without
  verifying against extraction data.
- The sci-fi intensity of the soundtrack means rapid note changes and
  aggressive envelope attacks. Some passages have very short notes
  (2-3 frames) where the 7.8 CC11/note density means only 1-2 volume
  updates per note -- the effective envelope resolution drops for
  staccato passages.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 1ms, fast decay (30-50ms),
  sustain 45-55%, release 15ms. Slightly more aggressive than Blaster
  Master to match the sci-fi intensity.
- Duty: Pulse 1 at 25% (duty 1), Pulse 2 at 50% (duty 2). Static.
- Volume: CC11-driven at 7.8/note density.
- Note: Same DPCM bass limitation as Blaster Master applies.

---

### 16. Batman (Sunsoft)

**Attribution**
- Publisher: Sunsoft, 1989. Composer: Naoki Kodaka. Driver programmer:
  Sunsoft internal, likely Akito Takeuchi (same programmer as Blaster
  Master, released one year earlier). VGMPF attributes the driver to
  the Sunsoft audio team without specifying the individual programmer
  for this title.

**Driver Family**
- Family 4 (Dense Automators). CC11/note 7.9.
- Nearly identical CC11 density to Journey to Silius (7.8), placing
  it squarely in the Dense Automator family. CC12/note near zero.
  The Sunsoft driver's characteristic punch-decay volume envelope is
  applied consistently across the Kodaka-composed trilogy (Blaster
  Master, Batman, Journey to Silius), with density varying by title
  but always within Family 4 range.

**Hardware**
- Mapper 4 (MMC3). No expansion audio.

**Music Architecture**
- Software-driven volume envelope with dense per-frame updates.
  Same constant-volume mode approach as other Sunsoft titles.
- DPCM used for drums (kick, snare), not pitched bass. Batman's DPCM
  usage differs from Blaster Master and Journey to Silius -- the bass
  line is carried by the triangle channel in standard NES fashion
  rather than by DPCM samples. This gives Batman a more conventional
  channel allocation despite using the same driver family.
- The absence of DPCM bass means Batman has a more standard 4-channel
  texture: 2 pulse (melody + harmony), triangle (bass), noise (drums),
  with DPCM providing sampled kick/snare hits.
- The dense volume automation (7.9 CC11/note) provides the punchy,
  dynamic envelope shape that defines the Sunsoft sound even without
  the DPCM bass trick.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined). NSF files and MIDI output exist
  in the output directory (multiple tracks extracted).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.

**Known Issues**
- Despite sharing a composer (Kodaka) and likely driver programmer
  (Takeuchi) with Blaster Master, Batman uses DPCM for drums rather
  than pitched bass. Do not assume all Sunsoft games use the DPCM
  bass technique.
- The output directory contains 11 MIDI files (tracks 01-11). Some
  modified files exist alongside new untracked files, suggesting
  extraction has been run but not validated.
- CC11 density at 7.9/note will produce moderately dense automation
  lanes in REAPER.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 1-2ms, decay 40-70ms, sustain
  45-55%, release 25ms. Standard Sunsoft punch-decay shape.
- Duty: Pulse 1 at 25% (duty 1), Pulse 2 at 50% (duty 2). Static.
- Volume: CC11-driven at 7.9/note density.

---

### 17. Ninja Gaiden

**Attribution**
- Publisher: Tecmo, 1988. Composer: Keiji Yamagishi. Driver programmer:
  Keiji Yamagishi. Yamagishi both composed and programmed the sound
  driver, which he called the "Super Sound Machine." This dual role
  is unusual -- most NES games had separate driver programmers and
  composers.

**Driver Family**
- Family 2 (Standard Envelope). CC11/note in the moderate range,
  consistent with the 3.5-5.6 range that defines Standard Envelope.
- The Tecmo driver sits in Family 2 for the first Ninja Gaiden,
  providing a detailed but not obsessive volume envelope. The driver
  writes volume several times per note via software envelope tables,
  producing a clean attack-decay-sustain shape. CC12/note is low --
  no significant duty animation.
- Yamagishi's driver is notable for spanning multiple families across
  the Ninja Gaiden trilogy. NG1 is Standard Envelope; NG2 jumps to
  Dense Automators; NG3 returns to the upper end of Standard Envelope.
  This suggests the Super Sound Machine was configurable, allowing
  the composer to dial envelope update density up or down per game.

**Hardware**
- Mapper 1 (MMC1). No expansion audio.

**Music Architecture**
- Software-driven volume envelope at moderate density. The driver uses
  constant-volume mode with per-frame updates from envelope lookup
  tables.
- No DPCM bass. DPCM used for drum samples (kick, snare).
- Triangle carries bass lines in standard fashion.
- The Super Sound Machine's distinguishing feature is its flexibility
  rather than any single technique. Yamagishi could adjust envelope
  density, timing resolution, and modulation parameters per game
  without rewriting the driver.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.

**Known Issues**
- The Tecmo driver's cross-family behavior (Family 2 in NG1, Family 4
  in NG2, back to Family 2 in NG3) means synth presets should not be
  shared across the trilogy without verifying CC density per game.
- Yamagishi's dual role as composer and driver programmer means the
  music and driver are tightly coupled. Effects that sound like driver
  features may be compositional choices encoded directly in the data.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 2-4ms, decay 60-90ms, sustain
  50-60%, release 30ms. Clean, balanced envelope.
- Duty: Pulse 1 at 50% (duty 2), Pulse 2 at 25% (duty 1). Static.
- Volume: CC11-driven at Standard Envelope density.

---

### 18. Ninja Gaiden II: The Dark Sword of Chaos

**Attribution**
- Publisher: Tecmo, 1990. Composers: Keiji Yamagishi, Michiharu Hasuya.
  Driver programmer: Tecmo internal (Yamagishi / Hasuya). Hasuya joined
  the sound team for NG2, and the driver was revised to support
  significantly denser volume automation.

**Driver Family**
- Family 4 (Dense Automators). CC11/note 10.5.
- Jumped from Family 2 (NG1) to Family 4 -- a dramatic increase in
  volume automation density. At 10.5 CC11/note, NG2 sits alongside
  Sunsoft's Blaster Master (11.7) in the Dense Automators, despite
  being made by a completely different company with a different driver.
- This cross-family jump between sequels is one of the strongest
  pieces of evidence that CC density is a composer/configuration
  choice, not a fixed property of the driver codebase. The Super
  Sound Machine was revised or reconfigured to support per-frame
  volume writes at roughly double the density of NG1.

**Hardware**
- Mapper 1 (MMC1). No expansion audio.

**Music Architecture**
- Software-driven volume envelope with dense per-frame updates.
  The driver now writes volume approximately 10.5 times per note,
  approaching Sunsoft-level automation density.
- No DPCM bass. DPCM for drums only, same as NG1.
- The increased volume density produces more detailed attack transients
  and more sculpted decay curves than NG1. Notes have a more aggressive,
  punchy quality.
- Whether the density increase came from driver code changes or from
  different data tables is unknown without disassembly. Both the driver
  revision and Hasuya's involvement as co-composer could explain the
  change.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.

**Known Issues**
- The CC11 density at 10.5/note produces very dense automation lanes.
  REAPER projects need to handle high event density without UI lag.
- Do not reuse NG1 synth presets for NG2. The envelope character is
  fundamentally different due to the doubled CC11 density.
- The driver revision between NG1 and NG2 may have changed more than
  just envelope density. Command format, timing semantics, and
  modulation behavior should all be verified independently if a ROM
  parser is ever built.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 1-2ms, fast decay (40-60ms),
  sustain 40-50%, release 20ms. More aggressive than NG1, reflecting
  the denser envelope.
- Duty: Static. Pulse 1 at 50% (duty 2), Pulse 2 at 25% (duty 1).
- Volume: CC11-driven at 10.5/note density. The synth must handle
  rapid CC11 updates faithfully.

---

### 19. Ninja Gaiden III: The Ancient Ship of Doom

**Attribution**
- Publisher: Tecmo, 1991. Composer: Keiji Yamagishi. Driver programmer:
  Tecmo internal (Yamagishi). Yamagishi returned as sole credited
  composer for the final NES installment.

**Driver Family**
- Family 2 (Standard Envelope). CC11/note 5.6 -- at the top boundary
  of Family 2.
- Pulled back from NG2's Dense Automator density (10.5) to the upper
  edge of Standard Envelope. At 5.6 CC11/note, NG3 sits right at the
  Family 2 ceiling, just below the Family 4 threshold.
- The return to Standard Envelope density after NG2's Dense Automator
  excursion is significant. It confirms the Tecmo driver's
  configurability: Yamagishi could choose the envelope update rate
  per game. NG3's positioning at the Family 2/4 boundary suggests
  a deliberate middle-ground choice.

**Hardware**
- Mapper 2 (UNROM). No expansion audio.

**Music Architecture**
- Software-driven volume envelope at moderate-to-high density.
  The driver writes volume approximately 5.6 times per note, providing
  detailed but not obsessive envelope shaping.
- No DPCM bass. DPCM for drums, consistent with the trilogy.
- Triangle carries bass. Standard 4-channel allocation.
- The reduced automation density compared to NG2 does not necessarily
  indicate reduced musical quality. Yamagishi may have opted for longer
  sustained notes with fewer volume updates, producing a smoother
  sound compared to NG2's punchy aggression.

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.

**Known Issues**
- At 5.6 CC11/note, NG3 sits on the exact boundary between Family 2
  and Family 4. Classification is somewhat arbitrary at this threshold.
  The key distinction is behavioral: NG3 sounds more like a Standard
  Envelope game (smooth sustain) than a Dense Automator (punchy decay).
- The trilogy spans three different density profiles (Family 2 -> 4 -> 2).
  Each game needs its own synth preset and its own CC density expectations.
- NG3 uses mapper 2 (UNROM) while NG1 and NG2 use mapper 1 (MMC1).
  This mapper difference does not affect audio but may affect ROM
  parsing if ever attempted.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 2-4ms, decay 70-100ms, sustain
  50-60%, release 35ms. Smoother than NG2, closer to NG1.
- Duty: Static. Pulse 1 at 50% (duty 2), Pulse 2 at 25% (duty 1).
- Volume: CC11-driven at 5.6/note density. Upper Standard Envelope
  range provides good volume detail without extreme density.

---

### 20. Kirby's Adventure

**Attribution**
- Publisher: HAL Laboratory, 1993. Composer: Hirokazu Ando, Jun Ishikawa.
  Driver programmer: Hiroaki Suga. Suga programmed HAL's NES sound
  driver across multiple titles (Adventures of Lolo, Air Fortress,
  Kirby's Adventure). HAL later developed "Music Maker," a custom MML
  tool that replaced raw assembly data entry for music composition.

**Driver Family**
- Family 3 (Duty Animators). CC11/note 3.7, CC12/note 0.7.
- The largest game in Family 3 by note count: 78,992 notes across 56
  songs. The CC12/note density of 0.7 places it firmly in the Duty
  Animators family -- HAL's driver actively animates duty cycle during
  sustained notes.
- The duty animation produces a shimmering timbre effect: the pulse
  waveform cycles through duty settings during held notes, creating
  tonal movement that would be absent with a static duty setting.
  This technique is rare among NES sound drivers and distinguishes
  HAL's engine from the volume-only automation of Dense Automators
  and the hands-off approach of Hardware Envelope games.

**Hardware**
- Mapper 4 (MMC3). No expansion audio. HAL did not use expansion
  chips on NES.

**Music Architecture**
- Software-driven volume envelope at moderate density (3.7 CC11/note)
  combined with active duty cycle animation (0.7 CC12/note). The
  driver uses constant-volume mode with per-frame volume and duty
  writes.
- The duty animation is the defining architectural feature. During
  sustained pulse channel notes, the driver cycles through duty
  register values, producing a characteristic shimmer. This is not
  vibrato (which modulates pitch) or tremolo (which modulates volume)
  but a distinct timbral oscillation unique to the NES pulse channels.
- DPCM drum support was added in later versions of the HAL driver.
  Kirby's Adventure, as a late-era title (1993), likely uses DPCM
  for at least kick and snare drum samples.
- With 56 songs, the game has one of the largest soundtracks on the
  NES. The sheer volume of music data tests the driver's efficiency --
  78,992 notes is significantly more than most NES games.
- Triangle channel carries bass in standard allocation. The moderate
  CC11 density means triangle articulation comes primarily from note
  duration (gate on/off) rather than volume shaping, which is correct
  for triangle (no hardware volume control, only gate).

**Pipeline Status**
- NSF only. No ROM parser. No Mesen trace.
- Validation rung: 0 (Unexamined).
- Route: NSF emulation -> CC11/CC12 extraction -> MIDI -> REAPER.
- With 56 songs, batch extraction will produce a large output set.
  The batch_nsf_all.py pipeline handles this automatically.

**Known Issues**
- The CC12 duty animation is critical to Kirby's sound. If the synth
  ignores CC12 automation, the characteristic shimmer is lost and
  pulse channels sound flat and static. This game is a key test case
  for the CC12 playback path in ReapNES Studio.
- At 78,992 notes across 56 songs, Kirby's Adventure is a stress test
  for the batch extraction pipeline. Expect large MIDI files and
  correspondingly large REAPER projects.
- The HAL driver evolved over time. Do not assume Kirby's Adventure
  driver behavior matches earlier HAL titles (Adventures of Lolo,
  Air Fortress) without verifying CC density profiles per game.
- Late-era NES title (1993) -- the driver may use techniques not
  present in earlier HAL games, including DPCM drums and more
  sophisticated envelope tables.

**Synth Preset**
- Channel Mode: Per-track (P1=0, P2=1, Tri=2, Noise=3).
- ADSR: For keyboard mode -- attack 3-5ms, decay 80-120ms, sustain
  55-65%, release 40ms. The longer decay accommodates the duty
  animation shimmer effect.
- Duty: Let CC12 automation drive duty changes. Do NOT set a static
  duty -- the duty animation is the defining characteristic of this
  game's sound. For keyboard mode, consider cycling duty between
  values 1 and 2 on a timer to approximate the shimmer.
- Volume: CC11-driven at 3.7/note density. Moderate automation
  provides clean volume shaping without extreme density.

## Games 21-30

---

### 21. Ghosts 'n Goblins

**Attribution**
- Publisher: Capcom, 1986. Composer: Ayako Mori. Driver programmer: attribution uncertain -- possibly Kazuo Yagi (Micronics contractor) rather than Yoshihiro Sakaguchi. VGMPF lists Sakaguchi as the Capcom NES driver author, but the earliest Capcom NES titles were outsourced to Micronics, and driver code may have come from their programmer Yagi rather than from Capcom's internal Sakaguchi engine.

**Driver Family**
- Hardware Envelope (Family 1). CC11/note: 0.1, CC12/note: 0.1. Dominant duty: 25%. 3 songs extracted, 1221 total notes. No noise channel detected in extraction. The CC11 density of 0.1 is among the lowest in the entire 65-game survey, tied with Dragon Warrior and Wizards & Warriors. The driver sets volume once per note and relies entirely on APU hardware envelope decay. This places it firmly at the bottom of the Hardware Envelope family.

**Hardware**
- Mapper 0 (NROM). No expansion audio. No bankswitching (load address $8380). Capcom never used expansion audio chips on any NES title.

**Music Architecture**
- Hardware envelope with no per-frame volume automation. The 0.1 CC11/note means the driver writes to $4000/$4004 approximately once every 10 notes -- essentially only at note onset. The APU's built-in linear decay envelope handles all volume shaping. No DPCM usage detected (noise channel absent from extraction). This is consistent with the simplest possible NES sound approach: set duty, set volume/envelope parameters, set period, let hardware do the rest.
- The NSF file contains 39 songs, but only 3 produced extractable melodic content in the survey run. The remaining tracks are likely sound effects or very short jingles. This low song yield is typical of early NES titles where the NSF packages all audio (music + SFX) under one init routine.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/Ghosts_n_Goblins/` with midi, reaper, nsf, rom_capture, and wav directories. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline via `nsf_to_reaper.py`.

**Known Issues**
- The NSF contains 39 tracks but only 3 yielded usable music in the survey. Many tracks may be sound effects that produce no sustained melodic content. A full extraction with `--all` flag should capture more, but SFX-heavy track lists inflate the song count misleadingly.
- No noise channel was detected. This could mean the game genuinely has no percussion in its extracted songs, or it could indicate an extraction issue with the noise channel mapping for this particular NSF.
- Driver attribution is genuinely uncertain. If the driver is Micronics code rather than Sakaguchi's MML engine, the data format may differ from later Capcom titles. This matters only if ROM parsing is ever attempted.

**Synth Preset**
- Channel mode: Pulse 1/2 only (no triangle or noise detected). Keyboard mode on. ADSR: fast attack, medium decay, low sustain (2-3), no release -- mimics hardware envelope linear decay. Duty: 25% fixed. No CC11 automation to replay, so ADSR mode is the primary playback path. Volume envelope should approximate the APU's hardware decay: attack to max, linear ramp to zero over ~8-12 frames.

---

### 22. Chip 'n Dale Rescue Rangers

**Attribution**
- Publisher: Capcom, 1990. Composer: Harumi Fujita. Driver programmer: Yoshihiro Sakaguchi. This is a late-era Capcom title, firmly within the established Sakaguchi MML-based driver workflow. Fujita also composed for Mega Man 3, so the composition style is well-characterized.

**Driver Family**
- Hardware Envelope (Family 1). Not present in the 65-game survey, but classification is inferred from the Capcom Sakaguchi driver lineage. All surveyed Capcom games using the Sakaguchi driver cluster in Family 1 with CC11/note ranging from 0.2 (Mega Man 1) to 2.2 (Abadox). A 1990 Capcom title composed by Fujita in MML would produce similar low-automation output. Expected CC11/note: 0.5-1.5 range based on contemporary Capcom titles (DuckTales at 0.8, Bionic Commando at 0.9).

**Hardware**
- Mapper 1 (MMC1). No expansion audio. Standard Capcom NES cartridge configuration. No bankswitching in NSF required for music.

**Music Architecture**
- Hardware envelope, consistent with the Sakaguchi driver's approach across 30+ Capcom titles. The MML composition workflow means music data is structured as note sequences with instrument definitions (duty, volume, envelope parameters) applied at note onset. Per-frame volume automation is minimal or absent. Duty cycle is set per instrument and rarely changes within a note.
- DPCM usage: likely present for percussion samples (kick, snare) based on contemporary Capcom titles (Mega Man 3-6 era all use DPCM drums). The Sakaguchi driver supports DPCM sample playback.
- Composition style: Fujita's work on Mega Man 3 shows clean melodic lines with distinct pulse 1/pulse 2 voicing and triangle bass. Chip 'n Dale follows the same template.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/Chip_n_Dale_Rescue_Rangers/` with midi, reaper, nsf, and wav directories. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- Not included in the 65-game driver survey, so CC11/CC12 density values are inferred from driver lineage rather than measured. A survey run would confirm family placement.
- The Capcom 6C80 sound engine documentation (Romhacking.net #274) covers the data format for Mega Man 3+ era games. If ROM parsing is ever needed, this document is the starting point.

**Synth Preset**
- Channel mode: per-track (P1, P2, Tri, Noise). Keyboard mode on. ADSR: moderate attack, medium decay, sustain 4-6, short release. Duty: 50% for pulse channels (Capcom default for this era). CC11 automation minimal -- ADSR mode will be primary for keyboard playback. If CC11 data exists in extracted MIDI, it should be honored but will be sparse (sub-1.0 events per note).

---

### 23. Strider

**Attribution**
- Publisher: Capcom, 1989. Composer: Harumi Fujita (arcade version music adapted for NES). Driver programmer: Yoshihiro Sakaguchi. Standard Capcom MML driver.

**Driver Family**
- Hardware Envelope (Family 1). CC11/note: 1.0, CC12/note: 0.0. Dominant duty: 75%. 15 songs extracted, 21,744 total notes. No noise channel switching detected (CC12/note 0.0). The CC11 density of 1.0 means approximately one volume write per note -- slightly more automation than Mega Man 1 (0.2) but still well within the Hardware Envelope family. The driver sets volume at note onset and possibly once more during the note (likely a simple decay step), then lets hardware handle the rest.

**Hardware**
- Mapper 4 (MMC3). No expansion audio. No bankswitching in NSF (load $8000, init $8003, play $8000). Standard Capcom cartridge.

**Music Architecture**
- Hardware envelope with minimal software volume intervention. The 1.0 CC11/note indicates the Sakaguchi driver is writing volume at note onset only, with no per-frame envelope animation. Duty is fixed at 75% across all pulse channels -- this is notable because 75% duty produces the same waveform shape as 25% (they are inversions of each other on the NES APU), but the register value differs. Capcom's choice of 75% vs 25% may reflect a specific instrument definition in the MML data.
- No duty cycling (CC12/note 0.0) -- the timbre is completely static within each note. This is the simplest possible Capcom sound profile: fixed duty, fixed volume, period changes define note boundaries.
- The NES version of Strider is a different game from the arcade version, with substantially different level design, but the music draws from the same source compositions adapted for the APU's 4-channel limitation.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/Strider/` with midi and rom_capture directories (rom_capture contains title screen capture). Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- The 75% dominant duty is unusual for Capcom. Most surveyed Capcom games use 25% or 50%. This may indicate a specific instrument preset choice by the composer rather than a driver-level default. Worth verifying against the actual NSF output to confirm duty values are correctly captured.
- Only 15 songs extracted from the NSF, which is a reasonable count for a Capcom action game of this era.

**Synth Preset**
- Channel mode: per-track. Keyboard mode on. ADSR: sharp attack, fast decay, low sustain (2-3), minimal release. Duty: 75% for pulse channels. The static duty and minimal CC11 automation mean the synth preset is simple: fixed timbre, hardware-style decay envelope. No duty animation to replay.

---

### 24. Metroid

**Attribution**
- Publisher: Nintendo, 1986. Composer and driver programmer: Hirokazu Tanaka. Tanaka is one of the few NES composers who programmed his own driver variant rather than using a shared company driver. He wrote custom driver code for both Metroid and Kid Icarus, producing a distinct sonic signature that differs from Koji Kondo's driver (used for Mario and Zelda).

**Driver Family**
- Dense Automators (Family 4). CC11/note: 5.1, CC12/note: 0.0. Dominant duty: 50%. 11 songs extracted, 9,423 total notes. Noise channel present. The 5.1 CC11/note places Metroid at the low end of the Dense Automators family, just above the Standard Envelope ceiling of ~5.0. The zero CC12 automation means all density is in volume -- Tanaka's driver animates volume per-frame but leaves duty static. Kid Icarus (also Tanaka) shows identical density: 5.1 CC11/note, 0.2 CC12/note. This confirms the Tanaka driver variant as a consistent Dense Automator.

**Hardware**
- Mapper 1 (MMC1). No expansion audio on the NES cartridge version. The original Famicom Disk System release used FDS expansion audio (1 wavetable channel), which added a synthesized bass/pad voice not present in the NES version. NSF files for the NES version capture only the standard 5 APU channels. Bankswitched NSF (load $8000, init $A000, play $B3B4).

**Music Architecture**
- Software envelope with dense per-frame volume automation. The 5.1 CC11/note means Tanaka's driver writes to $4000/$4004 approximately 5 times per note, updating volume every 2-3 frames. This produces smooth, controlled volume contours rather than the staircase decay of hardware envelope games.
- Duty is static at 50% (CC12/note 0.0). Tanaka achieves his atmospheric sound through volume shaping alone, not timbral animation. The sustained, eerie quality of Metroid's soundtrack comes from holding notes at low volume levels with slow, deliberate volume curves -- the dense CC11 automation shapes ambience rather than driving sharp melodic articulation.
- No DPCM bass. Triangle channel handles bass duties. The triangle's gate-only volume (always 127 or 0) combined with Tanaka's sparse melodic writing creates the signature hollow bass sound.
- The FDS version's wavetable channel added a layer of harmonic richness that the NES version lacks. When comparing NSF extractions of the two versions, the FDS version will show an additional channel with wavetable synthesis data.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/Metroid/` with rom_capture directory (title screen capture). Bankswitched NSF requires bank mapping in emulation. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- The FDS vs NES version distinction matters for extraction. The joshw.info archive may contain both versions. The NES NSF is the correct target for our pipeline since ReapNES Studio does not currently support FDS wavetable synthesis.
- Tanaka's driver variant is poorly documented compared to Kondo's or Sakaguchi's. No byte-level format documentation exists on Romhacking.net or NESDev. If ROM parsing is ever needed, the driver would need to be reverse-engineered from scratch.
- The atmospheric, ambient character of Metroid's music means note density is lower than typical action games. Long sustained tones with 5+ CC11 updates per note produce smooth volume curves that the synth must reproduce faithfully -- truncating CC11 automation or substituting ADSR will destroy the intended ambience.

**Synth Preset**
- Channel mode: per-track. Keyboard mode on. ADSR: slow attack (2-3 frames), very slow decay, high sustain (8-10), long release (10+ frames). Duty: 50% fixed. The preset should emphasize sustained tones with gradual volume changes. For file playback, CC11 automation drives volume directly -- do not override with ADSR. For keyboard play, the ADSR should produce slow, atmospheric envelopes: no sharp transients, smooth volume curves, long tails.

---

### 25. The Legend of Zelda

**Attribution**
- Publisher: Nintendo, 1986. Composer and driver programmer: Koji Kondo. Kondo wrote his own driver variant in pure 6502 assembly for Super Mario Bros. and reused/adapted it for Zelda. The VGMPF database identifies Kondo's driver as distinct from Yukio Kaneoka's base Nintendo driver and from Hirokazu Tanaka's variant.

**Driver Family**
- Not precisely classified in the 65-game survey (Zelda 1 was not included; Zelda II is present only in rom_capture data). Family placement is estimated at the border of Standard Envelope (Family 2) and Duty Animators (Family 3), based on Kondo's other measured games. Super Mario Bros. shows CC11/note 4.9 with CC12/note 0.8 -- if Zelda uses the same driver variant, similar density is expected. The CC12/note value is the key discriminator: if Zelda shows duty animation above 0.5, it belongs in the Duty Animators family; below 0.5, it falls into Standard Envelope.

**Hardware**
- Mapper 1 (MMC1) for the NES cartridge version. The original Famicom release was a Famicom Disk System title using FDS expansion audio (1 wavetable channel). The FDS version includes an extra synthesized channel that doubles or harmonizes melodic lines. The NES cartridge version lost this channel entirely. No bankswitching information in the survey (game not included).

**Music Architecture**
- Software envelope driven by Kondo's custom driver. Based on the SMB data (4.9 CC11/note), Kondo's driver writes volume approximately 5 times per note -- a moderate density that produces shaped envelopes with clear attack-decay-sustain contours.
- Duty animation is the distinguishing feature of Kondo's driver. SMB shows 0.8 CC12/note, meaning duty changes within sustained notes to create timbral movement. If Zelda shares this behavior, pulse channels will shift between duty settings (typically 12.5%/25%/50%) during held notes, producing a shimmering or evolving timbre.
- The overworld theme is one of the most recognizable NES compositions. Its march-like rhythm with strong triangle bass and dual-pulse harmony is a template for Kondo's compositional style.
- The FDS version's wavetable channel adds a sustained pad/string voice to several tracks. As with Metroid, this channel is absent from NES NSF extractions.

**Pipeline Status**
- NSF only. No ROM parser. Not yet processed through the batch pipeline (no output directory found in the survey). The NSF is available from joshw.info. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- Not included in the 65-game driver survey. CC11/CC12 density values are unknown and must be measured before definitive family assignment. The SMB comparison provides a reasonable estimate but is not confirmation.
- FDS vs NES version distinction is critical. The joshw.info archive likely has both. The NES version NSF is the correct extraction target. The FDS version would require FDS wavetable support in the synth.
- Kondo's driver is among the least documented commercial NES drivers. No byte-level format specification exists publicly. The NES-Games-Disassembly repository on GitHub contains a Legend of Zelda disassembly that includes sound engine code, but it is not separately documented.
- The game has a relatively small soundtrack (likely under 10 distinct songs plus jingles/fanfares). The NSF track count may be inflated by SFX entries.

**Synth Preset**
- Channel mode: per-track. Keyboard mode on. ADSR: fast attack, moderate decay, sustain 5-7, short release. Duty: 50% default for pulse channels, but expect duty switching if CC12 data is present -- set duty to respond to CC12 automation. Triangle: standard bass voice, 1 octave lower. For keyboard play, a moderate ADSR with slight duty wobble (if supported) would approximate the Zelda sound.

---

### 26. Marble Madness

**Attribution**
- Publisher: Rare (developed by Rare, published by Milton Bradley/Rare), 1989. Composer: David Wise. Driver programmers: Chris Stamper (original), Mark Betteridge (later maintenance). Wise composed directly in 6502 assembly hex using the Brief text editor, encoding pitch and length as hex pairs.

**Driver Family**
- Hardware Envelope / Standard Envelope border (Family 1-2 boundary). CC11/note: 3.5, CC12/note: 0.2. Dominant duty: 50%. 9 songs extracted, 4,224 total notes. No noise channel detected. The 3.5 CC11/note places Marble Madness right at the upper edge of Family 1 (Hardware Envelope, ceiling ~2.8 in the strictest classification) or the lower edge of Family 2 (Standard Envelope, floor ~3.5). It sits at the exact boundary. The Rare driver was transitioning from early minimal usage (Wizards & Warriors at 0.1) toward the more automated approach used in later titles (Battletoads at 4.1). Marble Madness represents the midpoint of this evolution.

**Hardware**
- Mapper 0 (NROM) with bankswitched NSF (load $8000, init $8000, play $801D). No expansion audio. The Rare driver supports only the standard 4 APU channels. DPCM was rarely used in Rare games -- Pin-Bot SFX and Battletoads pause music are the notable exceptions.

**Music Architecture**
- Mixed envelope approach. The 3.5 CC11/note suggests the driver writes volume 3-4 times per note, which is enough for a basic attack-decay-sustain pattern but not the per-frame obsessiveness of Dense Automators. This is consistent with David Wise's evolving compositional technique -- by 1989 he was beginning to use more volume automation than his early work (Wizards & Warriors, 1987) but had not yet reached the density of Battletoads (1991).
- Duty is essentially static (CC12/note 0.2). Timbre does not change within notes. The 50% duty gives a hollow, square-wave sound.
- No noise channel was detected in extraction. Marble Madness has minimal percussion -- the game's audio emphasizes melodic content and ambient textures over rhythmic drive.
- The Rare driver's internal length counter doubling affects duration calculations: a length byte of $06 produces 12 frames of duration, not 6.

**Pipeline Status**
- NSF only. No ROM parser. No output directory found beyond rom_capture data. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- The absence of a noise channel in extraction may be genuine (the game has sparse percussion) or may indicate an extraction issue. Should be verified by listening to the NSF in an emulator and comparing.
- The game has only 9 songs, which is a very small soundtrack. Track metadata (names) may not be available in M3U files.
- Boundary classification (Family 1 vs Family 2) means the synth preset needs to handle both possibilities. If CC11 data is present in the MIDI, honor it; if sparse, fall back to ADSR.

**Synth Preset**
- Channel mode: per-track (P1, P2, Tri only -- no noise). Keyboard mode on. ADSR: moderate attack, moderate decay, sustain 5-6, short release. Duty: 50% fixed. The preset should handle both sparse CC11 automation (3-4 events per note) and ADSR fallback. For file playback, CC11 drives volume with a basic shaped envelope. For keyboard play, a neutral mid-sustain ADSR approximates the Rare sound of this era.

---

### 27. Castlevania III JP (Akumajou Densetsu)

**Attribution**
- Publisher: Konami, 1989. Composers: Hidenori Maezawa, Jun Funahashi, Yukie Morimoto, Yoshinori Sasaki. Driver programmer: Konami internal, VRC6-aware variant of the Maezawa driver. Maezawa helped design the VRC6 expansion chip itself, making this one of the few cases where the sound driver programmer also co-designed the audio hardware.

**Driver Family**
- Duty Animators (Family 3). CC11/note: 3.7, CC12/note: 1.0. Dominant duty: 12.5%. 15 songs extracted, 15,564 total notes. Noise channel present. The 1.0 CC12/note is the key metric -- this is the highest duty animation density in the survey after SMB3 (1.3). The CC11/note of 3.7 is moderate, but the duty cycling pushes it into the Duty Animators family. The US version (Castlevania III: Dracula's Curse) shows CC11/note 4.6 and CC12/note 0.8 -- still in Family 3 but with slightly different density. The JP version's higher CC12/note (1.0 vs 0.8) reflects the additional duty data generated by the VRC6's extra pulse channels.

**Hardware**
- Mapper 24 (VRC6). Expansion audio: VRC6 chip providing 2 additional pulse channels and 1 sawtooth wave channel. This gives the JP version 7 sound channels total (2 standard pulse + triangle + noise + DPCM + 2 VRC6 pulse + 1 VRC6 sawtooth). The VRC6 expansion was Famicom-only hardware -- the NES cartridge version (US/EU) used standard Mapper 5 (MMC5) or Mapper 4 (MMC3) without expansion audio, requiring all music to be rearranged for 5 standard channels.
- Bankswitched NSF (load $8000, init $E0E0, play $E0D0).

**Music Architecture**
- Software envelope with both volume and duty animation. The VRC6 pulse channels have 8-bit duty cycle control (not just the 4 settings of the standard APU), enabling smoother timbral transitions. The standard APU pulse channels in the same NSF still use the 4 discrete duty settings (12.5%, 25%, 50%, 75%).
- The VRC6 sawtooth channel provides a distinctive buzzing bass/lead sound not achievable with the standard APU. In NSF captures, this channel appears as additional data beyond the standard 4 channels.
- The 12.5% dominant duty on standard pulse channels is characteristic of Konami games generally. The narrow pulse width produces a thin, bright timbre that defines the Castlevania sound.
- DPCM is used for percussion (kick and snare samples), consistent with Konami's standard practice.
- The US rearrangement is musically significant: losing 3 channels meant voices had to be combined, parts dropped, or rewritten. The CC density difference (JP 1.0 vs US 0.8 CC12/note) partially reflects this -- fewer channels means less total duty data in the capture.

**Pipeline Status**
- NSF only. No ROM parser. The JP version NSF is available from joshw.info. Output may exist under a variant directory name. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline. Note: ReapNES Studio does not currently support VRC6 expansion synthesis. NSF playback captures the VRC6 channels as register data, but the synth can only reproduce the standard APU channels. The VRC6 channels will be present in the MIDI as additional tracks but will not play back correctly without expansion chip support.

**Known Issues**
- VRC6 expansion audio is not supported by ReapNES Studio. The extra channels will extract but cannot be synthesized. This is a fundamental limitation for the JP version -- the US version (standard APU only) is fully playable.
- The JP and US versions have different NSF files with different init/play addresses and different bank layouts. They must be treated as separate games in the pipeline.
- The VRC6 pulse channels have 8-bit duty resolution vs the standard APU's 2-bit (4-setting) duty. CC12 encoding in MIDI cannot represent the finer VRC6 duty granularity without extension. Current pipeline maps CC12 values 0-3 for standard APU duty. VRC6 duty would need CC12 mapped to 0-127 for full resolution.
- The 12.5% dominant duty may produce aliasing artifacts at low frequencies in the synth. Verify that the synth's pulse waveform generator handles narrow duty widths correctly at all period values.

**Synth Preset**
- For the standard APU channels: Channel mode per-track. Duty: 12.5% default, with CC12 automation active. ADSR: fast attack, moderate decay, sustain 4-6, short release. Volume driven by CC11 automation (3.7 events/note). For the VRC6 channels: no preset available until expansion support is added. For the US version: same preset but expect CC12/note 0.8 and CC11/note 4.6.

---

### 28. Gradius

**Attribution**
- Publisher: Konami, 1986. Composers: Miki Higashino, Sashiko Fukami (credited as S. Fukami). Driver programmer: Konami internal, early variant predating Hidenori Maezawa's major redesign. The Gradius NES port was released early in Konami's NES catalog, and the driver may represent the original Konami sound engine before Maezawa's overhaul.

**Driver Family**
- Data anomaly -- nominally placed in Hardware Envelope (Family 1) by the survey, but CC11/note of 26.2 is a clear outlier. This value is nearly double the next-highest game in the entire survey (Final Fantasy at 14.9) and is inconsistent with any known NES driver behavior. The 26.2 figure likely represents a data artifact: possible causes include NSF extraction error, incorrect frame rate assumption, sound effect data inflating the CC11 count, or the NSF play routine being called at a non-standard rate. The true CC11/note is unknown and needs re-extraction and verification.

**Hardware**
- Mapper 0 (NROM) or Mapper 75 (VRC1). No expansion audio on the NES version. Non-bankswitched NSF (load $EBF0, init $EC48, play $ED30). The high load address ($EBF0) and non-standard init/play addresses suggest the music code sits in the upper ROM bank, which is typical for early Konami titles.

**Music Architecture**
- Unknown due to the data anomaly. If the 26.2 CC11/note is a genuine measurement, it would imply the driver writes to volume registers 26 times per note -- which at 60fps and typical note durations of 6-12 frames would mean multiple volume writes per frame. This is theoretically possible (the CPU can write to APU registers as often as it wants within a frame) but is unprecedented in the commercial NES library. More likely explanations: the NSF contains interleaved sound effect data that inflates CC11 counts, or the extraction misidentified the frame rate.
- The early Konami driver (pre-Maezawa) is poorly documented. No byte-level format specification exists. The actual envelope behavior is uncertain without a clean re-extraction.
- CC12/note of 0.2 suggests minimal duty animation, which would be consistent with early Konami practice.
- 32 songs extracted, 13,415 total notes. Noise channel present.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/Gradius/` with rom_capture data (title screen capture). Validation rung: 0 (Unexamined). Route: NSF emulation pipeline, but re-extraction is recommended before any production use.

**Known Issues**
- The 26.2 CC11/note is almost certainly a data artifact. This is the single largest anomaly in the 65-game survey. Before using Gradius output in any production context, the NSF must be re-extracted with careful attention to: (a) frame rate verification, (b) SFX track filtering, (c) CC11 event counting methodology.
- The early Konami driver may have unusual init/play behavior that confuses the NSF emulator. The non-standard addresses ($EC48/$ED30) and high load address ($EBF0) suggest the NSF was ripped from a ROM region that may include non-music code.
- If the anomaly is due to SFX interleaving, the survey's per-track filtering should be revisited for this specific game. Some Konami NSFs multiplex music and sound effects on the same channels.

**Synth Preset**
- Cannot recommend a reliable preset until the data anomaly is resolved. Tentative: treat as an early Konami game with moderate envelope automation (CC11/note likely 2-5 in reality). ADSR: fast attack, moderate decay, sustain 4-6, short release. Duty: 25% (common Konami default). Re-extract before tuning preset.

---

### 29. 1942

**Attribution**
- Publisher: Capcom, 1985. Composer: Ayako Mori. Driver programmer: attribution uncertain -- this is one of Capcom's earliest NES titles, and the driver may have been written by Micronics programmer Kazuo Yagi rather than Yoshihiro Sakaguchi. VGMPF documents two Capcom NES sound engines: "Sound Engine 1" for early titles and the later "6C80" engine for Mega Man 3 onward. 1942 almost certainly uses Sound Engine 1 or an even earlier precursor.

**Driver Family**
- Hardware Envelope (Family 1). CC11/note: 0.4, CC12/note: 0.4. Dominant duty: 50%. 13 songs extracted, 119 total notes. Noise channel present. The 0.4 CC11/note is near the bottom of the Hardware Envelope family. The extremely low note count (119 total across 13 songs) suggests very short tracks -- likely brief looping phrases typical of early arcade-to-NES ports. The equal CC11 and CC12 densities (both 0.4) are unusual; most games show CC11 significantly higher than CC12. With only 119 notes, the statistical significance of these ratios is low.

**Hardware**
- Mapper 0 (NROM) or early mapper. Bankswitched NSF (load $8000, init $8000, play $C081). No expansion audio. The NSF contains 14 tracks (13 extracted in survey + 1 additional). The bankswitched configuration is notable for an early title -- some of the music data may reside in a separate bank from the main code.

**Music Architecture**
- Hardware envelope with essentially no per-frame automation. The 0.4 CC11/note means volume is written less than once per note on average -- the driver sets envelope parameters at note onset and relies on APU hardware decay. This is the simplest possible NES sound engine behavior.
- The game's music is minimal by design: 1942 is an early vertical shooter port from the arcade, and the NES version's soundtrack consists of short, looping military march and flight themes. The musical ambition is modest compared to later Capcom titles.
- Only 119 notes across 13 songs means an average of ~9 notes per song. These are very short loops, likely 2-4 measures each, repeating indefinitely during gameplay.
- The Romhacking.net "Sound Engine 1" document covers the data format for these early Capcom titles and would be the reference for any ROM parsing attempt.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/1942/` with midi, reaper, nsf, rom_capture, and wav directories. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- The extremely low note count (119) raises questions about extraction completeness. Either the songs are genuinely very short (plausible for a 1985 arcade port), or some tracks failed to extract properly. Compare against the NSF played in an emulator to verify.
- The equal CC11/CC12 density (both 0.4) is statistically unreliable with only 119 notes. Do not draw driver architecture conclusions from this game alone.
- Driver attribution is uncertain. If this is Micronics code rather than Sakaguchi's engine, the ROM data format will differ from later Capcom titles. The "Sound Engine 1" documentation on Romhacking.net (document #875) may or may not cover this specific game.
- 1942 was Capcom's first NES game. The sound engine may be a one-off implementation not reused in later titles.

**Synth Preset**
- Channel mode: per-track. Keyboard mode on. ADSR: fast attack, fast decay, low sustain (1-2), no release -- approximates simple hardware envelope decay. Duty: 50%. The preset is straightforward: minimal automation, simple tones, short loops. No CC11/CC12 complexity to model.

---

### 30. Commando

**Attribution**
- Publisher: Capcom, 1986. Composer: Tamayo Kawamoto. Driver programmer: likely Yoshihiro Sakaguchi, though attribution for early Capcom NES titles (1985-1986) carries uncertainty. By 1986, Sakaguchi's driver was becoming the standard Capcom engine, but some titles from this transitional period may still use Micronics-derived code.

**Driver Family**
- Hardware Envelope (Family 1). Not present in the 65-game driver survey. Classification is inferred from the Capcom Sakaguchi driver lineage and from the game's era. All surveyed Capcom games from 1986-1989 using the Sakaguchi driver show CC11/note between 0.1 (Ghosts 'n Goblins) and 1.0 (Strider). Commando, as a 1986 Capcom military action game, would fall in this range. Expected CC11/note: 0.2-0.8 based on contemporary titles.

**Hardware**
- Mapper 0 (NROM) or Mapper 2 (UNROM). No expansion audio. Standard early Capcom NES cartridge. Capcom never used expansion audio on any NES release.

**Music Architecture**
- Hardware envelope, consistent with early Capcom practice. The Sakaguchi driver (or its predecessor) sets volume and envelope parameters at note onset and relies on APU hardware decay for volume shaping. Per-frame volume automation is minimal or absent.
- The game's soundtrack consists of military march themes and action music adapted from the arcade original. The NES version's audio is constrained by the 4-channel APU versus the arcade's richer sound hardware.
- DPCM usage: uncertain. Early Capcom titles (1985-1986) generally did not use DPCM for drums. The noise channel handles all percussion via tonal noise mode and short-period noise hits.
- Composition style: Kawamoto's work is less documented than Fujita's or Mori's, but the military action genre demands driving rhythms and simple, memorable melodies -- well-suited to the Sakaguchi driver's strengths.

**Pipeline Status**
- NSF only. No ROM parser. Output exists at `output/Commando/` with midi, reaper, nsf, rom_capture, and wav directories. Validation rung: 0 (Unexamined). Route: NSF emulation pipeline.

**Known Issues**
- Not included in the 65-game driver survey. CC11/CC12 density values are unknown and must be measured before definitive family assignment.
- Driver attribution uncertainty for this transitional period (1986) means the data format may differ from later Capcom titles if the engine is Micronics-derived rather than Sakaguchi's.
- The arcade-to-NES music adaptation may produce unusual note patterns if the conversion was done mechanically rather than recomposed for the APU's limitations.

**Synth Preset**
- Channel mode: per-track. Keyboard mode on. ADSR: fast attack, moderate decay, sustain 3-5, short release. Duty: 25% or 50% (typical early Capcom). Minimal CC11 automation expected -- ADSR mode will be the primary playback path for keyboard use. For file playback, any CC11 data present should be honored but will be sparse.

