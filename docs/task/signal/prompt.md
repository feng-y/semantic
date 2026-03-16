You are working in the root of the existing `semantic` repository.

Current old pipeline:
init -> discover -> review -> refine -> baseline

This old pipeline remains FACT only.

This run is ONLY for implementing the semantic layer capability named:

semantic-signals

Do NOT implement candidates, recommend, review, finalize, or demand in this run.
Do NOT modify old FACT runtime behavior.

==================================================
1. PRIMARY GOAL
==================================================

Implement `semantic-signals` as the first semantic capability.

Its purpose is:

Read FACT inputs and generate semantic signals as structured outputs for later semantic stages.

This run must produce:

- a standard skill entry for `semantic-signals`
- a Python-backed implementation
- canonical YAML output
- markdown view output
- basic tests

==================================================
2. NAMING RULES
==================================================

Do NOT use `step1` naming in:
- skill names
- prompt file names
- core document titles
- implementation-facing naming

Use semantic naming only:

- semantic-signals

Sequence is still important, but sequence should be expressed in contracts and runner logic, not in the capability name.

==================================================
3. REQUIRED FILES TO CREATE OR UPDATE
==================================================

You must create or update these files:

Skill:
- skills/semantic-signals/SKILL.md

Python:
- src/semantic/extract_signals.py
- src/semantic/models.py

Prompt alignment:
- prompts/semantic/semantic_signals.prompt.md

Template:
- templates/semantic/signals.template.yaml

Tests:
- tests/semantic/test_extract_signals.py

You may also update if needed:
- src/semantic/run.py
- src/semantic/stage_registry.py
- docs/semantic-foundation/semantic/semantic_signals_design.md

If an older file like `01_step1_signal_inference.md` exists, do not depend on its old naming as the canonical implementation-facing name.
You may reference it, but semantic-facing naming should prefer `semantic_signals`.

==================================================
4. INPUT CONTRACT
==================================================

Primary hard input:
- docs/semantic-foundation/fact/fact_canonical_sample.yaml

Auxiliary soft input:
- docs/semantic-foundation/fact/fact_working_summary_sample.yaml

Optional reference input:
- docs/fact/baseline/*.md if present

Rules:
- canonical fact is primary
- working summary is guidance only
- if conflict exists, canonical fact wins
- baseline markdown is optional reference only

==================================================
5. OUTPUT CONTRACT
==================================================

Workspace:
- docs/semantic-foundation/semantic/

Canonical output:
- signals.yaml

View output:
- signals.md

Required signal groups:
- domain_signals
- concept_signals
- rule_signals
- demand_pattern_signals

==================================================
6. REQUIRED SKILL BEHAVIOR
==================================================

The `semantic-signals` skill must:

1. clearly declare when to use the skill
2. clearly declare required inputs
3. clearly declare output paths
4. explicitly state this skill only handles semantic signals generation
5. invoke repo Python implementation instead of embedding all logic inside SKILL.md
6. preserve evidence/source traceability
7. not cross into candidates or later stages

==================================================
7. SKILL FILE REQUIREMENTS
==================================================

Create or update:

- skills/semantic-signals/SKILL.md

It must include:

A. standard skill metadata/frontmatter
B. when to use the skill
C. expected inputs
D. expected outputs
E. allowed tools
F. execution instructions that call the Python implementation
G. explicit boundary: semantic-signals only

The skill must be thin:
- orchestration and constraints in SKILL.md
- actual logic in Python

==================================================
8. PYTHON IMPLEMENTATION REQUIREMENTS
==================================================

Implement or improve:

- src/semantic/extract_signals.py

This module must:
- read FACT canonical YAML
- read FACT working summary YAML if present
- read optional baseline markdown if present
- normalize inputs
- extract semantic signals
- write signals.yaml
- write signals.md
- preserve evidence/source refs where possible

If needed, add minimal models in:
- src/semantic/models.py

Suggested minimal model set:
- Signal
- DomainSignal
- ConceptSignal
- RuleSignal
- DemandPatternSignal

Each signal should support at least:
- id
- name
- type
- summary
- evidence_refs
- source_refs

Do not over-engineer.

==================================================
9. PROMPT / TEMPLATE ALIGNMENT
==================================================

Ensure alignment with:

- prompts/semantic/semantic_signals.prompt.md
- templates/semantic/signals.template.yaml

Do not leave skill, code, prompt, and template inconsistent.

If old prompt files with step-based naming exist, do not treat them as canonical naming.
You may reuse content, but the preferred implementation-facing artifact should be:
- semantic_signals.prompt.md

==================================================
10. IMPLEMENTATION STYLE
==================================================

Implementation must be:

1. deterministic-first
- same inputs should produce stable structured outputs

2. contract-driven
- follow semantic/fact contracts
- do not invent new output shapes

3. traceability-preserving
- preserve provenance where available
- do not discard evidence refs unnecessarily

4. minimal but usable
- this is first usable implementation
- not final polished intelligence

5. repo-consistent
- follow existing repo style where reasonable

If no full model integration exists yet:
- implement deterministic extraction logic
- keep future model integration boundaries clear
- do not block on missing model intelligence

==================================================
11. TESTING REQUIREMENTS
==================================================

Create or update:

- tests/semantic/test_extract_signals.py

At minimum test:
- signals.yaml file creation
- YAML structure validity
- all four signal groups exist
- evidence/source traceability preserved where available
- deterministic behavior for same input fixtures

You may add fixtures if needed under:
- tests/semantic/fixtures/

==================================================
12. RUNNER COHERENCE
==================================================

Do NOT fully implement runner orchestration in this run.

But ensure:
- run.py remains coherent
- stage_registry.py can represent `signals` as the first semantic capability
- no contradiction is introduced with semantic runner docs

If useful, you may make `semantic-signals` invocable through a minimal CLI path.
If so, clearly document the limitation.

==================================================
13. STRICT PROHIBITIONS
==================================================

Do NOT:
- implement semantic-candidates or later capabilities
- modify old FACT runtime behavior
- rename unrelated public skills
- change manifest behavior unless absolutely required by repo skill convention
- implement demand
- move core extraction logic into SKILL.md
- ignore current semantic/fact contracts
- output markdown only without canonical YAML

==================================================
14. REQUIRED RESPONSE FORMAT
==================================================

When finished, respond in this order:

1. repo analysis summary for semantic-signals
2. files created or modified
3. what was implemented in SKILL.md
4. what was implemented in extract_signals.py
5. what was added/updated in models.py
6. what was added/updated in semantic_signals.prompt.md
7. tests added or updated
8. how to invoke the skill
9. limitations / deferred improvements
10. explicit confirmation that:
   - only semantic-signals was implemented
   - old FACT runtime behavior was not changed
   - candidates/recommend/review/finalize were not implemented
   - demand was not implemented

==================================================
15. FINAL OBJECTIVE
==================================================

Deliver `semantic-signals` as a standard Claude Code skill backed by repo Python implementation, prompt/template alignment, and tests, so it becomes the first reusable semantic capability in the semantic layer.