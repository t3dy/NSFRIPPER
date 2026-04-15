---
layout: default
title: ReapNES Studio
---

# ReapNES Studio

NES game music extracted to MIDI with per-frame APU register fidelity.
Each game produces 4-channel MIDI (Pulse 1, Pulse 2, Triangle, Noise)
with CC11 volume envelopes and CC12 duty cycle automation, plus REAPER
projects with the ReapNES synthesizer plugin.

## Game Library

Browse all extracted games below. Each page shows track counts,
note/CC event totals, and duration for every song.

{% assign sorted_games = site.pages | where_exp: "page", "page.dir == '/games/'" | sort: "title" %}

| Game | Tracks |
|------|--------|
{% for page in sorted_games %}| [{{ page.title }}]({{ page.url | relative_url }}) | {{ page.content | split: '|' | size | minus: 10 }} |
{% endfor %}

## What This Is

The NSF emulation pipeline runs each game's original 6502 sound driver,
captures APU register writes per frame (~60 Hz), and converts them to
MIDI with CC automation that preserves the original envelope shapes.

Four driver families have been identified based on CC11/CC12 density
analysis of 271 games (revised 2026-04-14):

| Family | Count | CC11/note | Behavior | Example Games |
|--------|-------|-----------|----------|---------------|
| 1: Sparse Envelope | 156 | 0.0-2.8 | HW decay or set-once | Mega Man, DuckTales, W&W |
| 2: Active Envelope | 79 | 2.8-5.6 | Per-frame volume | Contra, Ninja Gaiden, Zelda II |
| 3: Duty Animators | 20 | any | Volume + duty animation | SMB3, Konami Hyper Soccer |
| 4: Dense Automators | 16 | >5.6 | Obsessive per-frame volume | Metroid, Kid Icarus |

## Repository

Source code, MIDI files, and REAPER projects:
[github.com/t3dy/NSFRIPPER](https://github.com/t3dy/NSFRIPPER)
