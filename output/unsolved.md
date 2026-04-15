# Unsolved: Why 46 Games Resist Extraction

## The Problem

46 out of 296 NSF-bearing games produce incomplete output. The emulator
(py65, pure-Python 6502) either hangs during the PLAY routine or produces
silence on most tracks. With the new early-exit heuristic, these games
fail fast instead of timing out, but they still don't produce music.

## Root Cause Analysis

### Failure Pattern: 84% Are Bankswitched

| Category | Games | Bankswitch | Expansion |
|----------|-------|------------|-----------|
| Fully extracted | 250 | 80 (32%) | 12 |
| Partially extracted | 46 | 39 (84%) | 4 |

Bankswitch games fail at **2.6x the rate** of non-bankswitch games.
But 80 bankswitched games DO work, so bankswitch isn't inherently broken.
The issue is **complex bank layouts** that our handler doesn't support.

### Three Distinct Failure Modes

**Mode 1: PLAY routine hangs (30+ games)**

Symptoms: Every track produces exactly 29 frames (stuck detection fires).
The INIT runs, maybe writes one register, then PLAY enters an infinite
loop. The driver jumped to unmapped memory because bankswitch pages
weren't set up correctly.

Examples: Ninja Gaiden (1/65), Legend of Zelda (2/37), Kings Quest V (1/32)

Root cause: The NSF INIT routine does its own bankswitching during startup.
Our emulator loads the initial bank table from the NSF header, but doesn't
properly handle subsequent bankswitch writes during INIT execution. If INIT
swaps page 0 to load music data but our handler doesn't process it, the
PLAY routine reads garbage from the wrong page.

**Mode 2: Some tracks work, others don't (10+ games)**

Symptoms: Track 1 (or a few tracks) produce audio, but switching to other
tracks causes the driver to hang. The INIT routine for song N might swap
to a bank that our handler can't reach.

Examples: Castlevania 3 (19/28), Ganbare Goemon (55/88), Esper Dream 2 (30/36)

Root cause: Multi-bank music data. The driver stores different songs in
different ROM banks. Tracks 1-N might all be in the initially-loaded banks,
but track N+1 requires a bank swap that fails.

**Mode 3: Non-bankswitch failures (7 games)**

Symptoms: Low extraction rate despite no bankswitch flags.

Examples: Contra (2/11), Exciting_Boxing (6/17), Section_Z (19/34),
Mitsume_ga_Tooru (8/14), Tenka_no_Goikenban_Mito_Koumon (3/42)

Root cause varies:
- Contra: INIT expects specific memory state (2A03 warm boot) that our
  cold-start emulator doesn't provide
- Others: undetermined, possibly mapper-specific behavior or self-modifying code

---

## What We Need to Solve

### Problem 1: Bankswitch Fidelity

**Current implementation** (`nsf_to_reaper.py` line 88-134):
- Loads initial bank table from NSF header bytes $70-$77
- Intercepts writes to $5FF8-$5FFF (standard NSF bankswitch registers)
- Swaps 4KB pages at $8000-$FFFF

**What's missing:**
- The handler wraps `__setitem__` on the memory object, but the BankswitchMemory
  wrapper is installed BEFORE CaptureMemory. When CaptureMemory wraps on top,
  writes to $5FF8-$5FFF go through CaptureMemory first, which forwards them
  to the underlying memory but may not trigger the bankswitch handler properly.
  **This is a bug.** The layered memory wrappers may not chain correctly.
- Some NSF files use non-standard bankswitch schemes (FDS NSFs use $5FF6-$5FFF
  for 6 slots instead of 8). Our handler only covers $5FF8-$5FFF.
- The INIT routine's own bankswitch writes during initialization may not be
  captured if they happen before CaptureMemory is installed.

**Solution approach:**
1. Audit the memory wrapper chain — ensure bankswitch writes work through
   CaptureMemory -> BankswitchMemory correctly
2. Extend bankswitch range to $5FF6-$5FFF for FDS NSFs
3. Add debug logging: print every bankswitch during INIT to trace failures
4. Consider using libgme (C library) via subprocess for reliable NSF playback

### Problem 2: Non-Standard NSF Features

Some NSFs rely on features our emulator doesn't support:

| Feature | Impact | Games Affected |
|---------|--------|----------------|
| FDS bankswitch ($5FF6-$5FF7) | 2 extra 4KB slots | FDS expansion games |
| RAM at $6000-$7FFF | Work RAM for drivers | Many bankswitched games |
| Initial register state | Warm boot assumptions | Contra, others |
| IRQ/NMI handling | Timer-based drivers | Rare but possible |
| Illegal opcodes | Some drivers use them | Unknown |

### Problem 3: py65 Limitations

py65 is a pure-Python 6502 emulator. It's accurate but slow (~2-3 seconds
per 30 frames at 50,000 cycles/frame). It also:
- Doesn't support illegal opcodes (some NES games use them)
- Has no cycle-accurate timing (we approximate 1 frame = 1 PLAY call)
- Can't detect infinite loops except by cycle count

**Alternative: libgme via subprocess**

The Game Music Emu (libgme) library is a C library that plays NSF files
with full hardware accuracy. It handles all bankswitch modes, expansion
chips, and edge cases that py65 misses. Available as:
- `gme` Python package (ctypes wrapper)
- Command-line tools (nsf2wav, etc.)
- Integrated into VLC, foobar2000, Audacious

Using libgme would:
- Fix ALL bankswitch failures (it implements the full NSF spec)
- Handle expansion audio natively (VRC6, VRC7, FDS, etc.)
- Be 100-1000x faster (C vs Python)
- Eliminate the need for our custom emulator entirely

The tradeoff: we'd lose per-register capture (libgme outputs audio, not
register states). But we could still get register-level data by:
1. Using libgme's logging mode (if available)
2. Using Mesen headless mode with APU logging
3. Keeping py65 for register capture on games that work, using libgme
   as fallback for the 46 that don't

### Problem 4: Expansion Audio in Emulation

4 of the 46 partial games have expansion chips:
- Apple_Town (FDS): FDS wavetable requires FDS-specific bankswitch
- CV3 JP (VRC6): VRC6 register mapping may conflict with bankswitch addresses
- Esper_Dream_2 (VRC6): same issue
- Lagrange_Point (VRC7): VRC7 requires FM synthesis that py65 can't do

Our emulator now captures expansion registers (Layer 3), but the expansion
hardware itself isn't emulated. The driver writes to VRC6/VRC7/FDS registers,
we record the writes, but the audio output doesn't reflect them. For games
where the driver checks expansion hardware state (read-back), our emulator
returns wrong values, causing the driver to misbehave.

---

## Recommended Solution Path

### Quick Win: Fix the Memory Wrapper Chain (1 hour)

The BankswitchMemory and CaptureMemory wrappers may not chain correctly.
If bankswitch writes don't propagate through CaptureMemory to the actual
bank-swap logic, that alone explains most failures. Audit and fix this.

### Medium Win: libgme Fallback (2-4 hours)

Install `gme` Python package. For games where py65 fails, use libgme to:
1. Render each track to WAV
2. Parse the WAV for note detection (pitch tracking)
3. Or use libgme's register logging if available

This gives us audio output for ALL NSF files regardless of bankswitch
complexity. We lose register-level data but gain complete coverage.

### Full Solution: Mesen Headless (research needed)

Mesen (the NES emulator used for trace captures) has a headless/scripting
mode. If we can run Mesen from the command line with an NSF file and
capture APU register state per frame, we get:
- Perfect hardware accuracy (all chips, all mappers)
- Register-level data (not just audio)
- Frame-accurate timing
- Expansion audio support

This would replace py65 entirely for NSF extraction and solve all 46 games
plus future games. Research needed on Mesen's command-line API.

---

## Per-Game Status (46 partial)

| Game | Extracted | Total | Bankswitch | Expansion | Failure Mode |
|------|-----------|-------|------------|-----------|-------------|
| Ninja Gaiden | 1 | 65 | Yes | -- | PLAY hangs |
| Ninja Gaiden II | 1 | 84 | Yes | -- | PLAY hangs |
| Ninja Gaiden III | 10 | 93 | Yes | -- | PLAY hangs (some tracks work) |
| Legend of Zelda | 2 | 37 | Yes | -- | PLAY hangs |
| Kings Quest V | 1 | 32 | Yes | -- | PLAY hangs |
| Square no Tom Sawyer | 1 | 30 | Yes | -- | PLAY hangs |
| Mission Impossible | 1 | 26 | Yes | -- | PLAY hangs |
| Castlevania 3 | 19 | 28 | Yes | -- | Multi-bank songs |
| Castlevania 3 JP | 15 | 28 | Yes | VRC6 | Multi-bank + expansion |
| ~~Contra~~ | ~~2~~ | ~~11~~ | No | -- | ~~SOLVED: ROM-parsed in Contra_v8 (11/11)~~ |
| Lagrange Point | 11 | 31 | Yes | VRC7 | Multi-bank + FM |
| Captain Tsubasa II | 42 | 105 | Yes | -- | Timeout (large game) |
| Ganbare Goemon Gaiden 2 | 55 | 88 | Yes | -- | Multi-bank songs |
| Esper Dream 2 | 30 | 36 | Yes | VRC6 | Multi-bank + expansion |
| Double Dribble | 1 | 19 | Yes | -- | PLAY hangs |

(31 more games with similar patterns omitted for brevity)

## Organizational Debt: Duplicate Output Folders

Several early games have multiple output directories from different sessions:

- Contra: 7 directories (Contra/, Contra_v2/ through Contra_v8/, Contra_rom/)
- Castlevania: 9 directories (Castlevania/, Castlevania_I/II/III, _APU2, etc.)

This creates confusion about which version is "best." The BESTOUTPUT folder
addresses this by copying only fully-extracted games, but the underlying
output/ directory still has the mess. ROM-parsed games (Contra, CV1) should
have their best version clearly marked, and older versions archived or deleted.

**Note:** Contra is NOT unsolved. It was ROM-parsed early in the project and
all 11 tracks are in Contra_v8/. The "2/11" showing in the partial list was
from the NSF batch blindly re-extracting over it and getting a worse result.
Same applies to Castlevania (ROM-parsed, fully validated).

## Bottom Line

The core issue is **bankswitch emulation fidelity**. Our py65 wrapper handles
simple cases but fails on complex bank layouts. The fix is either:
1. Debug and fix the memory wrapper chain (quick, partial fix)
2. Use libgme as a fallback emulator (complete fix for audio, loses registers)
3. Use Mesen headless (complete fix for everything, needs research)

Option 2 is the highest-ROI next step. Install libgme, render the 46 failed
games to audio, and we have 100% coverage immediately.
