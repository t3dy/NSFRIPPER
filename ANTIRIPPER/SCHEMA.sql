-- ANTIRIPPER — Agentic Knowledge Base Extended Schema

PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

-- ==========================================
-- 1. ORIGINAL BASE TABLES (From NSFRIPPER)
-- ==========================================

CREATE TABLE IF NOT EXISTS games (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  developer TEXT,
  year INTEGER,
  mapper INTEGER,
  region TEXT CHECK (region IN ('ntsc', 'pal', 'dual') OR region IS NULL),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_files (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  source_type TEXT NOT NULL CHECK (
    source_type IN ('rom','nsf','mesen_trace','disassembly','track_manifest','reference_audio')
  ),
  path TEXT NOT NULL,
  sha256 TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(game_id, source_type, path)
);

CREATE TABLE IF NOT EXISTS track_names (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  track_number INTEGER NOT NULL,
  track_name TEXT NOT NULL,
  game_context TEXT,
  source_url TEXT,
  UNIQUE(game_id, track_number)
);

CREATE TABLE IF NOT EXISTS manifests (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  version TEXT NOT NULL,
  sound_driver TEXT,
  channels_used_json TEXT NOT NULL DEFAULT '[]',
  period_table_json TEXT NOT NULL DEFAULT '[]',
  envelope_model TEXT,
  percussion_type TEXT,
  known_facts_json TEXT NOT NULL DEFAULT '[]',
  hypotheses_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(game_id, version)
);

CREATE TABLE IF NOT EXISTS captures (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  source_file_id INTEGER NOT NULL REFERENCES source_files(id) ON DELETE CASCADE,
  capture_kind TEXT NOT NULL CHECK (capture_kind IN ('nsf_run', 'mesen_trace')),
  track_number INTEGER,
  capture_label TEXT,
  total_frames INTEGER,
  song_start_frame INTEGER,
  song_end_frame INTEGER,
  verification_status TEXT NOT NULL DEFAULT 'needs_review' CHECK (
    verification_status IN ('verified', 'needs_review', 'hypothesis')
  ),
  verification_notes TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS frame_states (
  id INTEGER PRIMARY KEY,
  capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
  frame INTEGER NOT NULL,
  channel TEXT NOT NULL CHECK (
    channel IN ('pulse1', 'pulse2', 'triangle', 'noise', 'dpcm')
  ),
  period INTEGER,
  midi_note INTEGER,
  volume INTEGER CHECK (volume BETWEEN 0 AND 15 OR volume IS NULL),
  duty INTEGER CHECK (duty BETWEEN 0 AND 3 OR duty IS NULL),
  constant_volume INTEGER CHECK (constant_volume IN (0,1) OR constant_volume IS NULL),
  linear_counter INTEGER,
  length_counter INTEGER,
  noise_mode INTEGER CHECK (noise_mode IN (0,1) OR noise_mode IS NULL),
  sounding INTEGER CHECK (sounding IN (0,1) OR sounding IS NULL),
  source_method TEXT NOT NULL DEFAULT 'trace' CHECK (
    source_method IN ('trace', 'nsf_parser', 'hybrid')
  ),
  UNIQUE(capture_id, frame, channel)
);

CREATE TABLE IF NOT EXISTS note_events (
  id INTEGER PRIMARY KEY,
  capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  frame_start INTEGER NOT NULL,
  frame_end INTEGER,
  midi_note INTEGER,
  velocity INTEGER CHECK (velocity BETWEEN 0 AND 127 OR velocity IS NULL),
  source_method TEXT NOT NULL CHECK (
    source_method IN ('trace', 'nsf_parser', 'hybrid')
  ),
  confidence REAL NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS cc_events (
  id INTEGER PRIMARY KEY,
  capture_id INTEGER NOT NULL REFERENCES captures(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  frame INTEGER NOT NULL,
  cc_number INTEGER NOT NULL CHECK (cc_number IN (11, 12)),
  cc_value INTEGER NOT NULL CHECK (cc_value BETWEEN 0 AND 127),
  source_method TEXT NOT NULL CHECK (
    source_method IN ('trace', 'nsf_parser', 'hybrid')
  )
);

CREATE TABLE IF NOT EXISTS output_artifacts (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  capture_id INTEGER REFERENCES captures(id) ON DELETE SET NULL,
  artifact_type TEXT NOT NULL CHECK (
    artifact_type IN ('midi', 'rpp', 'wav', 'sysex_midi', 'report')
  ),
  path TEXT NOT NULL,
  build_tool TEXT,
  synth_mode TEXT NOT NULL DEFAULT 'n/a',
  version TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS validation_runs (
  id INTEGER PRIMARY KEY,
  game_id INTEGER NOT NULL REFERENCES games(id) ON DELETE CASCADE,
  capture_id INTEGER REFERENCES captures(id) ON DELETE SET NULL,
  run_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pass', 'fail', 'warn')),
  summary TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 2. NEW AGENTIC KNOWLEDGE TABLES
-- ==========================================

-- Hardware facts to be queried by agents when writing parsing logic
CREATE TABLE IF NOT EXISTS apu_hardware_facts (
  id INTEGER PRIMARY KEY,
  component TEXT NOT NULL,
  fact TEXT NOT NULL,
  formula TEXT,
  domain TEXT,
  gotchas TEXT
);

-- Domain knowledge about sound drivers for heuristic mapping
CREATE TABLE IF NOT EXISTS driver_families (
  slug TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  cc11_per_note REAL,
  cc12_per_note REAL,
  description TEXT,
  fidelity_concern TEXT,
  examples TEXT
);

-- Repository of previously encountered LLM errors or technical misroutings
CREATE TABLE IF NOT EXISTS blunders (
  id INTEGER PRIMARY KEY,
  game_slug TEXT REFERENCES games(slug),
  symptom TEXT NOT NULL,
  root_cause TEXT NOT NULL,
  fix TEXT NOT NULL,
  category TEXT CHECK (category IN ('synth', 'encoding', 'project_gen', 'mapping', 'methodology')),
  prompts_wasted INTEGER,
  prevention TEXT,
  timestamp TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Derived actionable tasks that agents MUST ingest via semantic query bounds
CREATE TABLE IF NOT EXISTS fix_patterns (
  pattern_id TEXT PRIMARY KEY,
  trigger_condition TEXT NOT NULL,
  action TEXT NOT NULL,
  cost_if_skipped TEXT,
  derived_from_blunder INTEGER REFERENCES blunders(id)
);

-- Bridge for resolving colloquial requests to exact APU definitions
CREATE TABLE IF NOT EXISTS vocabulary_bridges (
  user_term TEXT PRIMARY KEY,
  technical_term TEXT NOT NULL,
  nes_parameter TEXT,
  explanation TEXT
);

-- Agent session tracker for hypothesis modeling and tests
CREATE TABLE IF NOT EXISTS session_hypotheses (
  id INTEGER PRIMARY KEY,
  session_id TEXT NOT NULL,
  game_slug TEXT REFERENCES games(slug),
  hypothesis TEXT NOT NULL,
  status TEXT CHECK (status IN ('proposed', 'testing', 'confirmed', 'rejected')),
  test_method TEXT,
  evidence TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

COMMIT;
