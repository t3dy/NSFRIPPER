# Prompt For New Window

Continue the `Wizards & Warriors` work in `C:\Dev\NSFRIPPER`, but reset the
title triangle interpretation from first principles.

Read first:

- `C:\Dev\NSFRIPPER\WIZARDSWARRIORS_TRIANGLE_RESET_HANDOVER.md`
- `C:\Dev\NSFRIPPER\CLAUDE.md`
- `C:\Dev\NSFRIPPER\EXECUTIONSEMANTICSVALIDATION.md`
- `C:\Dev\NSFRIPPER\.claude\skills\MUSICFINDER_ORCHESTRATOR.md`
- `C:\Dev\NSFRIPPER\.claude\skills\SIMULATORBUILDER.md`
- `C:\Dev\NSFRIPPER\CODEXWIZARDSWARRIORS.md`
- `C:\Dev\NSFRIPPER\extraction\analysis\reconciled\wizards_and_warriors_title_triangle_mismatch_report.md`

Current user-verified contradiction:

- the title triangle is still musically wrong
- the first short bass note after the longer one is barely audible
- the bass note durations are too long
- therefore the current triangle interpretation is not trusted

Non-negotiable rules:

- do not keep patching the old theory just because some local validation matched
- when the heard result contradicts the decode, reopen the interpretation
- use the MP3 as falsification for macro musical shape, not just tail slices
- do not promote a title-specific patch into engine truth

Primary evidence sources to use together:

1. ROM parser events
2. simulator frame-state
3. direct NSF / emulator register state
4. reference MP3 / NSF-derived audio output

Main task:

Figure out what frame-level hardware behavior actually produces the heard title
triangle phrase, then decide the correct export architecture for:

- MIDI
- REAPER project
- synth plugin or plugins
- possible middle layer between MIDI and plugin playback

Important architectural question:

Is plain MIDI too lossy for this triangle articulation?

Evaluate explicitly whether we need a middle layer such as:

- frame-state IR
- SysEx / register replay
- automation / sidecar control data
- plugin input richer than note-on / note-off alone

Required deliverables:

1. fresh triangle audit from first principles
2. ranked hypotheses for the missing articulation layer
3. recommendation on whether a middle layer is needed between MIDI and synth
4. concrete implementation plan for the new architecture
5. only after that, revised title outputs

Style:

- no hand-waving
- no defending the old model
- prove one narrow hypothesis at a time
- if uncertain, give 2-3 ranked candidate interpretations
