# Track naming policy

The stems pipeline produces audio WAVs, MIDI files and REAPER RPPs per
song.  Until today (2026-04-19) the relationship between filename,
rendered audio, and source NSF track number had several silent failure
modes — most famously the off-by-one that made every stem render from
one adjacent NSF track.  This document defines the deterministic rules
now in force.

## Invariants (must not be broken)

1. **NSF track number is the load-bearing integer.**  Every file the
   pipeline emits is attributable to exactly one NSF track number
   (1-indexed, matching NSF convention).
2. **Only 1-indexed values cross process boundaries.**  The `--song N`
   argument to `render_channel_stems.py` and `nsf_to_reaper.py` is
   always 1-indexed.  `play_song()` internally does the single
   `song_num - 1` for the 0-indexed NSF INIT convention.  No caller
   may pre-subtract 1 before passing.
3. **Filenames encode the NSF track number.**  The m3u-position-based
   `{position:02d}_...` convention is kept as the leading sort prefix,
   but the NSF track number must also be recoverable from the filename
   (via `--numeric-labels` mode baking `Song_{nsf_track:02d}`, or via
   the sidecar JSON below).
4. **Every song directory carries a `track.json` sidecar.**  The
   sidecar is the source of truth for audits.  It contains the NSF
   track number, the name source, and the pipeline version that
   produced the stems.
5. **No mixing of name sources.**  For a given song, name comes from
   exactly one of: M3U, NSFe, explicit --names JSON, fallback
   `Song_NN`.  Never two.

## Name source priority (strict, deterministic)

For each song the pipeline assigns a name from the first available
source in this ordered list:

| Priority | Source | Trigger |
|----------|--------|---------|
| 1 | `--names` JSON file | user-supplied override |
| 2 | M3U label for that NSF track | M3U file present next to NSF |
| 3 | NSFe embedded metadata | NSFe track name in NSF header |
| 4 | Fallback `Song_NN` | no metadata available |

The source is recorded in `track.json::name_source` so audits can
distinguish user-authored labels from inferred ones.

## Filename convention

**With `--numeric-labels` (default for rebuild_v6 / render_all_nsfs):**

```
{m3u_position:02d}_Song_{nsf_track:02d}.rpp
```

Example: `03_Song_08.rpp` = M3U position 3, NSF track 8.  Both numbers
are visible so mismatches can be diagnosed from `ls` alone.

**With M3U labels (explicit `--m3u-labels`, not default):**

```
{m3u_position:02d}_{slugified_label}.rpp
```

Example: `03_Cornelia_Castle.rpp` = M3U position 3, NSF track recorded
only in sidecar.

**Without M3U (fallback, `--no-m3u`):**

```
{nsf_track:02d}_Song_{nsf_track:02d}.rpp
```

(Position equals NSF track number in this case.)

## Sidecar format (`track.json`)

Written into every song's stems directory by `batch_stems_project.py`:

```json
{
  "pipeline_version": "v6.2",
  "pipeline_date": "2026-04-19",
  "nsf_file": "Final Fantasy (1987-12-18)(Square).nsf",
  "nsf_track": 16,
  "m3u_position": 16,
  "name": "Battle Scene",
  "name_source": "m3u",
  "m3u_file": "Final Fantasy (1987-12-18)(Square).m3u",
  "m3u_declared_seconds": 87.047,
  "rendered_seconds": 87.0,
  "seconds_cap": 180
}
```

A missing sidecar means the song was rendered by an older (pre-2026-
04-19) pipeline and should be treated as ambiguous during audits.

## Mismatch modes (named for audit)

| Code | Description | Detection | Repair |
|------|-------------|-----------|--------|
| `correct` | sidecar + filename + audio all match M3U | sidecar present, name matches M3U at that position, duration within tolerance | no action |
| `rename_only` | sidecar + audio match M3U, filename name is wrong | sidecar.name ≠ filename.label OR filename from old buggy template | `apply_repairs.py --rename-only` |
| `re_render_required` | sidecar present but audio came from wrong NSF track, OR sidecar absent and filename's claimed track ≠ M3U position | duration mismatch > 10%, OR sidecar.nsf_track ≠ m3u_tracks[position].num | `render_all_nsfs.py --only <game>` with `--force` |
| `truncated` | right track, short render | sidecar present and nsf_track correct, but rendered_seconds < 0.9 * m3u_declared_seconds | `--only <game>` `--force` with larger `--seconds` |
| `m3u_missing` | no M3U file found | `output/<game>/nsf/*.m3u` does not exist | manual (use NSFe or Zophar) |
| `ambiguous` | any other condition where we can't decide | default when two signals disagree | manual review |

## What to NEVER do

- **Never rename based only on filename heuristics.**  Filenames can be
  stale from a pre-fix render; the audio inside can be wrong even if
  the name looks plausible.  Use the sidecar, or re-render.
- **Never mix M3U and NSFe names in one directory.**  If M3U is
  present, M3U names are used for everything.  If only NSFe, only
  NSFe.  Never "some tracks from M3U, others from NSFe."
- **Never assume M3U position == NSF track number.**  Many M3Us (like
  Final Fantasy) reorder tracks for play-order purposes.  Position 3
  could be NSF track 8.
- **Never silently "fix" ambiguity.**  If the audit flags a track as
  ambiguous, leave it.  Ask the user or re-render.
- **Never pre-subtract 1 before passing to `play_song()`.**  The
  function's contract is 1-indexed input; it does the `-1` internally.

## Validation guards (must fail loudly)

`render_channel_stems.py::main()` asserts:
- `args.song >= 1`  (rejects 0 or negative NSF track numbers)

`batch_stems_project.py::main()` asserts:
- Every `t['num']` from `parse_m3u()` is >= 1
- `queue` entries all have `num >= 1`

`nsf_to_reaper.py::NsfEmulator.play_song()` asserts:
- `song_num >= 1`
- `song_num <= self.total_songs`

Any guard failure halts the render and logs to stderr — the user
sees the failure instead of getting a misaligned render.
