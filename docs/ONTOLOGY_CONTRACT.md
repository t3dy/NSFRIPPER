# ANTIRIPPER Ontology Contract (v2)

This document serves as the foundational law for the Agentic NES Audio Knowledge System. It enforces strict ontological boundaries between observed data, derivations, and agent instructions. Any expansion, agentic prompt, or database migration MUST respect these rules. Collapsing these layers represents a systemic violation.

## 1. Entity Types

The knowledge graph consists strictly of the following formalized entities:

### 1.1 Core Epistemology
- **EvidenceItem**: A raw, immutable observation. Examples: Frame-level traces, extracted metrics JSONs (like CC density), parsed driver outputs, reference audio validations. 
- **Claim**: A derived hypothesis, interpretation, or synthesis of EvidenceItem(s). Claims are human or agent-generated and strictly versioned.
- **DecisionRecord**: A formal logging indicating the pipeline route selected for a given game or condition, containing explicit rationale. 

### 1.2 Agent Control & Governance (Metacognition)
- **PreventionPattern**: An action-oriented rule that prevents known failure modes. It acts as an operational stop-sign triggered by specific context boundaries.
- **HardwareFact**: An immutable technical truth governing NES components. These are write-once.

### 1.3 Pedagogy & Domain Structure
- **ConceptBridge**: Mappings from human musical vocabulary (e.g. "staccato") to low-level APU register mechanics.
- **DriverFamily**: The structural umbrella grouping games with similar sound engine architectures and CC automations.
- **SynthPatch**: The specific JSFX mapping parameters for hardware modeling.

## 2. Allowed Relationships

Inter-entity maps are restricted explicitly to the following graphs to prevent cross-contamination:

- **Claim → EvidenceItem**: [Many-to-Many]. Claims must cite the exact EvidenceItem(s) supporting the assertion. An unsupported Claim is invalid.
- **DecisionRecord → Claim / EvidenceItem**: [One-to-Many]. A Decision must map back to either concrete evidence or a reviewed Claim defining why the decision was taken.
- **PreventionPattern → affected_subsystem**: [One-to-One / Many]. Specifies exactly which system boundary (parser, synth, routing, timing) the rule guards against.

## 3. Mutability Rules

- `HardwareFact`: **Write-Restricted**. Immutable once defined. Updates require explicit human override.
- `Claim`: **Versioned & Confidence-Scored**. Cannot be overwritten; state changes move through append-only lifecycles (`proposed` -> `reviewed` -> `accepted` -> `superseded`).
- `PreventionPattern`: **Append-Only + Refinement**. New patterns can be added, and triggers can be iteratively defined, but the causal root history cannot be deleted.
- `EvidenceItem`: **Immutable**. Derived from execution; once recorded, the underlying hash or metric must remain untouched. 

## 4. Agent Permissions

Agentic execution (via Oracle interaction) operates under a principle of least privilege:

1. **Proposing Knowledge**: Agents MAY propose `Claims` (status strictly defaults to `proposed`).
2. **Recording Actions**: Agents MUST record execution attempts and outcomes via `DecisionRecord` generation when interacting with pipelines.
3. **Hardware Truth**: Agents MAY NOT overwrite or generate `HardwareFacts`.
4. **Validation Bounds**: Agents MAY NOT directly elevate `Claim` confidence vectors or move a claim to `accepted` without cryptographic test coverage mapped or explicit human approval.
5. **Direct Read Access**: Agents MUST NOT query the database directly using raw SQL. All data flows must travel through the approved `agent_oracle.py` interface hooks.
