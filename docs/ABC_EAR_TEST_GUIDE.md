# A/B/C variant ear-test guide

Three REAPER project folders, three different architectures.  Pick any
game from the 10 currently available (ADandD, Balloon Fight, Bards
Tale 1+2, etc.) and open the same song in all three to compare.

## Quick reference

| Folder | Architecture | Live-playable? | MIDI-kbd input? |
|--------|--------------|----------------|-----------------|
| `outputv6_A/` | Stems (audio) + MIDI+JSFX, both unmuted | yes (JSFX path) | yes |
| `outputv6_B/` | MIDI+JSFX only, no stems | yes | yes |
| `outputv6_C/` | Same as B for now; will be JSFX-rendered stems after REAPER automation lands | yes | yes |

Where the audio comes from:

- **A**: you hear both the pre-rendered Python stems AND the real-time
  JSFX output mixed together.  Mute the stems tracks (top 5) to hear
  JSFX only; mute the JSFX tracks (bottom 4-5) to hear stems only.
- **B**: you only hear JSFX.  Mute any JSFX track to isolate a channel
  (e.g. solo Pulse 1 for melody-only listening).
- **C**: identical to B for now.  Will become bit-identical to A once
  the JSFX-offline-render automation lands.

## Suggested test sequence

**Test 1 — "Is it playable?"** (validates the basic JSFX path)

Open `outputv6_B/Balloon_Fight/reaper/01_Song_01.rpp`.  Hit play.  You
should hear NES audio.  Open REAPER's MIDI keyboard (View → Virtual
MIDI Keyboard) and play notes — the JSFX should respond.  This proves
live keyboard input works.

**Test 2 — "Stems vs JSFX side-by-side"** (shows what the fork costs)

Open `outputv6_A/Castlevania/reaper/02_Song_02.rpp` (Vampire Killer).
Unmute everything.  You'll hear both stems and JSFX at once — probably
slightly phased.  Solo the stems tracks (top 5): what Python renders.
Solo the JSFX tracks (bottom 4): what the plugin plays.  They will
sound meaningfully different because:

- JSFX does NOT apply the 14 kHz analog LP or DC blocker that Python
  stems use (Rule 33; intentionally — JSFX optimized for libgme
  parity).
- JSFX pulse synthesis does NOT use bandlimited formula (Rule 35 not
  ported).
- JSFX triangle gate-off DOES now hold the DAC value (Rule 34 just
  landed).

Listen for: pulse grit / aliasing on sustained high notes (more in
JSFX), triangle pops (gone in JSFX now that Rule 34 ported, gone in
stems too).

**Test 3 — "Does it sound like the game?"**

Open `outputv6_B/Battletoads/reaper/01_Song_01.rpp` (pause theme).
Play it.  Compare to your memory of Battletoads' pause music.  This
is the JSFX-only path — if it sounds right here, the JSFX is viable
for live play.

**Test 4 — "Can I edit MIDI?"**

Open any B variant.  Each track has real MIDI events (notes, CC11,
CC12, SysEx).  Edit any MIDI item — the JSFX will play back your
edits in real time.  This is the scoring / arrangement path.

## What to listen for

Going from most audible to least:

1. **Triangle pops / vinyl clicks** — should be ABSENT in A's stems
   and ALSO ABSENT in JSFX now that Rule 34 ported.  If you still
   hear them, tell me which variant and which game.
2. **Pulse grit on sustained high notes** — MORE in JSFX than stems,
   because Rule 35 (bandlimited pulse) isn't ported to JSFX yet.
3. **Overall tonal balance** — JSFX and stems use the same non-linear
   mixer (Rule 27) so gross loudness should match.
4. **Noise drums "wash"** — stems have the $4015 bit-3 gate (Rule 30)
   for Nintendo/Capcom length-counter drivers; JSFX doesn't.  If a
   game's drums sound too continuous in B compared to A, that's the
   rule 30 gap.

## Ear-test protocol

For each game you evaluate, answer:

1. Does B (JSFX-only) sound acceptable as "the game"?  If yes → B is
   a viable product on its own.
2. Is A (stems+JSFX) the winner for that game?  If yes → we keep the
   Python pipeline as the canonical archival path.
3. Any game where stems sound clearly better than JSFX is a candidate
   for future Rule 35 port work.  Write down which ones.

After you've tested 5-10 games, tell me:
- "JSFX is good enough" → I stop porting and we lock in Option A or B
- "JSFX needs the bandlimited pulse" → I spend ~3-4 hours on Rule 35
  polyBLEP port
- "I want bit-identity" → we go Option C route (ReaScript automation)

## Games available for testing RIGHT NOW

All have A/B/C variants already generated:

- ADandD_Dragons_of_Flame
- ADandD_DragonStrike
- Adventures_of_Lolo (1, 2, 3)
- Akumajou_Special_Boku_Dracula_kun
- Balloon_Fight
- Bards_Tale_2_The_Destiny_Knight
- Bards_Tale_Tales_of_the_Unknown

More games land in `outputv6_*/` as the main rebuild progresses.  The
variant generator re-runs automatically when the main rebuild
completes.
