# ANTIRIPPER V2: The Agentic NES Audio Handover Context

**CRITICAL INSTRUCTION TO CLAUDE CODE / AGENTS:** 
You are entering a strictly governed system. This document provides the essential historical, domain, and operational context required to operate effectively within the ANTIRIPPER environment. Read this carefully before touching any code or making any hypotheses.

---

## 1. Project Background & The Domain Goal
We reverse-engineer classic NES games to extract their musical sequences entirely intact, translating them into high-fidelity REAPER multi-track sessions. 
Originally built as **NSFRIPPER**, the system possesses robust scripts (like `nes_rom_capture.py` and `mesen_to_midi.py`) that run headless py65 6502 assembly emulators on NES ROMs, tracing every single write to the APU registers ($4000-$4017) frame-by-frame, and then mapping that register automation into standard MIDI data which drives custom JSFX synthesizers in REAPER.

## 2. Why We Restructured into "ANTIRIPPER"
NSFRIPPER was a powerful, human-operated pipeline, but when we introduced AI agents to crack *new*, undocumented audio drivers (like Battletoads or Konami engines), we encountered massive failures:
1. **The Hallucination Loop:** Agents repeatedly guessed the same incorrect logic for complex driver behavior (e.g. attempting to alter duty cycles during notes when the hardware envelope was locked).
2. **Context Memory Wipes:** An agent would burn 20 prompts figuring out that Castlevania uses a lookup table rather than dynamic CC bounds, but the very next session, a new agent tracking a similar game would forget the lesson and repeat the blunder.
3. **Pipeline Mutation:** Agents would attempt to completely rewrite our stable python extraction mechanisms to suit a specific game instead of recognizing that the pipeline routes decisions.

**The Solution:** We transitioned from a flat execution tracker into a **Governed Agentic Knowledge System (V2)**. We explicitly mapped our historical mistakes into isolated layers to act as "Guardrails" for incoming memory windows. 

## 3. The New Ontology Layers
The system is built on an unbreakable rule: **Data types must not be blended.**
- **Hardware Facts:** Immutable laws governing NES components (e.g. *Triangle channel sits an octave lower than Pulse. It divisor is 32, not 16.*). Agents will never overwrite these.
- **Prevention Patterns / Blunders:** Specific boundaries triggered by context (e.g. *If parsing a Sunsoft driver, do NOT assume CC12 relies on dynamic mapping.*).
- **Driver Families:** Formal mappings classifying games by how they automate their volume and duty cycle (e.g., *Minimal vs. Dense Automators vs. Konami Full Animation*).
- **Evidence vs Claims:** Traces produced by our pipeline represent *Evidence*. Your LLM theories about how strings of code work represent versioned *Claims*.

## 4. The Agent Oracle (Your ONLY Interface)
**DO NOT run raw SQL queries targeting the database.** The core V2 engine operates out of the `ANTIRIPPER/antiripper_v2.db` SQLite file, but you must negotiate with it via the Python API wrapper.

When operating on an extraction task, you must import and use `ANTIRIPPER/agent_oracle.py`:
1. **Pre-flight Check (`get_preflight_context`)**: Call this function *before* you act on a game. It automatically queries the database for the active Driver Family and relevant Prevention Patterns, loading only the high-signal context you need for that specific task.
2. **Declare Intent (`record_attempt`)**: Use this to log your explicit hypothesis before touching pipeline files. It generates a trackable, version-controlled "proposed claim."
3. **Log Finality (`record_outcome`)**: When your script executes, formally record your lessons against the attempt.

*(Note: The old extraction pipelines like `nes_rom_capture.py` have already been modified to automatically generate `EvidenceItems` via our hooks. Do not break these bindings.)*

## 5. Visual Portal
The human supervisor tracks your decisions, hypothesis scores, and the generated driver matrices through a Next.js portal actively running and mapping to the Oracle schema. 

## Your Immediate Directive
Please confirm you have read this layout and you understand the historical boundary issues we are solving through the Oracle. Then, ask the human operator which NES Audio Target they would like you to begin extraction on.
