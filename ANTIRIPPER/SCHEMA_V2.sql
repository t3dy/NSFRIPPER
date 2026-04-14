-- ANTIRIPPER — Agentic Knowledge Base Extended Schema (V2 governed)

PRAGMA foreign_keys = ON;
BEGIN TRANSACTION;

-- ==========================================
-- 1. EVIDENCE LAYER
-- ==========================================
CREATE TABLE IF NOT EXISTS evidence_items (
  id INTEGER PRIMARY KEY,
  game_slug TEXT NOT NULL,
  type TEXT NOT NULL CHECK (type IN ('trace', 'nsf', 'vgm', 'parser_output', 'metric')),
  source_path TEXT NOT NULL,
  metrics_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 2. CLAIMS LAYER
-- ==========================================
CREATE TABLE IF NOT EXISTS claims (
  id INTEGER PRIMARY KEY,
  subject_type TEXT NOT NULL CHECK (subject_type IN ('game', 'driver', 'system')),
  subject_id TEXT NOT NULL,
  statement TEXT NOT NULL,
  confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed', 'reviewed', 'accepted', 'superseded')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claim_evidence_links (
  claim_id INTEGER NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
  evidence_id INTEGER NOT NULL REFERENCES evidence_items(id) ON DELETE CASCADE,
  PRIMARY KEY (claim_id, evidence_id)
);

-- ==========================================
-- 3. DECISION LAYER
-- ==========================================
CREATE TABLE IF NOT EXISTS decision_records (
  id INTEGER PRIMARY KEY,
  game_slug TEXT NOT NULL,
  decision_type TEXT NOT NULL CHECK (decision_type IN ('extraction_route', 'validation_method', 'pipeline_action')),
  rationale TEXT NOT NULL,
  outcome TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- 4. SAFEGUARDS LAYER
-- ==========================================
CREATE TABLE IF NOT EXISTS prevention_patterns (
  id INTEGER PRIMARY KEY,
  description TEXT NOT NULL,
  trigger_condition TEXT NOT NULL,
  affected_subsystem TEXT NOT NULL CHECK (affected_subsystem IN ('parser', 'synth', 'routing', 'timing')),
  recommended_action TEXT NOT NULL,
  prompt_cost INTEGER DEFAULT 0,
  example_failure TEXT
);

-- ==========================================
-- 5. HARDWARE FACTS (STRICT)
-- ==========================================
CREATE TABLE IF NOT EXISTS hardware_facts (
  id INTEGER PRIMARY KEY,
  statement TEXT NOT NULL,
  formula TEXT,
  source_reference TEXT,
  relevant_subsystems TEXT NOT NULL DEFAULT 'all',  -- comma-separated: parser,synth,routing,timing,all
  locked BOOLEAN NOT NULL DEFAULT TRUE
);

-- ==========================================
-- 6. CONCEPT BRIDGES (PEDAGOGY ONLY)
-- ==========================================
CREATE TABLE IF NOT EXISTS concept_bridges (
  id INTEGER PRIMARY KEY,
  human_term TEXT NOT NULL,
  nes_equivalent TEXT NOT NULL,
  explanation TEXT NOT NULL
);

-- ==========================================
-- 7. DRIVER FAMILIES (FORMALIZED)
-- ==========================================
CREATE TABLE IF NOT EXISTS driver_families (
  slug TEXT PRIMARY KEY,
  cc11_range TEXT NOT NULL, -- e.g. "0.0 - 0.5"
  cc12_range TEXT NOT NULL,
  uses_hardware_envelope BOOLEAN NOT NULL,
  animates_duty BOOLEAN NOT NULL,
  high_density_volume BOOLEAN NOT NULL,
  validation_implications TEXT NOT NULL,
  nsf_trust_level TEXT NOT NULL
);

-- ==========================================
-- 8. SYNTH PATCHES (VERSIONED)
-- ==========================================
CREATE TABLE IF NOT EXISTS synth_patches (
  id INTEGER PRIMARY KEY,
  target_scope TEXT NOT NULL CHECK (target_scope IN ('game', 'family')),
  parameters_json TEXT NOT NULL DEFAULT '{}',
  provenance TEXT NOT NULL CHECK (provenance IN ('trace-derived', 'ear-matched')),
  confidence REAL NOT NULL CHECK (confidence >= 0.0 AND confidence <= 1.0),
  version INTEGER NOT NULL DEFAULT 1
);

COMMIT;
