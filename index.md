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

Five driver families have been identified based on CC11/CC12 density:

| Family | CC11/note | Behavior | Example Games |
|--------|-----------|----------|---------------|
| Hardware Envelope | 0.1-2.8 | APU hardware decay | Mega Man, DuckTales |
| Standard Envelope | 3.5-5.6 | Per-frame volume | Castlevania, Contra |
| Duty Animators | 3.7-4.9 | Volume + duty | Super Mario Bros, Kirby |
| Dense Automators | 5.1-14.9 | Obsessive volume | Final Fantasy, Batman |
| Full Animation | >7.0 both | Both axes | Super Mario Bros 3 |

## Repository

Source code, MIDI files, and REAPER projects:
[github.com/t3dy/NSFRIPPER](https://github.com/t3dy/NSFRIPPER)
