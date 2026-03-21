# SPEC — Diff-First Historical Change Reconstruction and Demand Pattern Compression

## 1. Problem

The internal repository history is not organized as clean semantic commits.

In practice, a single historical commit container may contain:

* changes accumulated across multiple days
* changes from multiple people
* multiple independent feature / bugfix / refactor intentions
* missing or low-quality commit title / log
* mixed main logic, tests, configs, flags, wiring, cleanup, and follow-up fixes

This means the repository’s historical “commits” are often not true semantic change units.

As a result, the history is difficult to use for:

* Agent few-shot reuse
* historical retrieval
* requirement analogy
* pattern discovery
* demand-oriented case construction

The core problem is not “how to summarize commits.”

The real problem is:

> **how to reconstruct clean change units from dirty historical diff containers, and then compress them into reusable demand patterns for Agent retrieval and few-shot.**

---

## 2. Primary Consumer

The first and most important downstream consumer is:

> **Agent few-shot / retrieval**

This decision shapes the whole system.

The system is not primarily optimized for:

* human-readable history browsing
* perfect archival fidelity
* commit analytics
* code search
* repository-wide knowledge graph construction

Those may become secondary benefits later, but they are not the first target.

The design must therefore optimize for:

* low-noise retrieval
* reusable historical samples
* stable semantic boundaries
* compact domain pattern space
* object-specific constraint transfer

---

## 3. Core Insight

### 3.1 Raw historical commits are not semantic units

A historical commit in the internal repository is often just a **diff container**, not a requirement unit.

### 3.2 Code diff is the primary trustworthy source

The most reliable input is the actual code diff:

* changed files
* changed code regions
* structural co-change information
* weak supporting signals from tests / config / other touched files

### 3.3 Commit title / log are weak supervision, not source of truth

In some repositories, such as brpc, many commit titles are high quality and can clearly express a main change intent.
But even there, quality is mixed, with weak examples like merge commits or placeholder titles.

Therefore:

> **commit title / log should not be treated as the primary semantic source, but may be used as optional weak supervision and consistency checking signals.**

### 3.4 The system must be two-phase, not one-phase

Because the internal repository history is dirty, the first job is not semantic field extraction.

The first job is:

> **reconstructing clean change units from dirty historical commit containers**

Only after that can semantic extraction be stable.

---

## 4. System Definition

This system is:

> **a diff-first, Agent-first demand pattern compression system**

It works in two phases:

### Phase 1 — Clean Change Unit Reconstruction

Starting from a dirty historical commit container, reconstruct a set of cleaner, semantically coherent change units that resemble well-formed commits in repositories such as brpc.

### Phase 2 — Demand Semantics Extraction and Pattern Compression

For each reconstructed clean change unit:

* extract stable semantic structure
* reconstruct requirement-oriented expressions
* filter low-value noise
* compress many similar cases into a small set of reusable domain patterns

---

## 5. Why This System Exists

Without this system, the internal history remains trapped in a form that is hard for agents to use.

### 5.1 Why raw history is not enough

Raw history may contain useful signals, but they are buried inside:

* large mixed diffs
* missing metadata
* repeated micro-adjustments
* supporting noise
* multiple themes in one container

### 5.2 Why agents need reconstructed cases

Agents do not need raw historical containers. They need:

* a clean main semantic unit
* a clear object of change
* the type of demand change
* constraints that must not be broken
* a few representative prior examples

### 5.3 Why patterns matter

Even after case reconstruction, many historical cases will still be near-duplicates or variations of the same underlying demand pattern.

Without compression:

* retrieval becomes noisy
* few-shot becomes repetitive
* pattern space becomes fragmented
* agents see too many local variants instead of a few representative modes

Therefore the system must not stop at cases.
It must also compress cases into patterns.

---

## 6. Phase 1 — Clean Change Unit Reconstruction

### 6.1 Goal

Transform a dirty historical commit container into one or more **clean change units**.

A clean change unit should be much closer to a well-formed semantic commit:

* one main object domain
* one main demand change direction
* supporting changes attached, not dominating
* possible to summarize cleanly

### 6.2 Why this phase is necessary

If the system skips this phase and directly extracts semantics from dirty commit containers, then:

* `commit_log` will be unstable
* `issue_text` will become too wide
* `rules / invariants` will mix unrelated objects
* pattern aggregation will be polluted from the start

### 6.3 Inputs

Primary input:

* code diff from one historical commit container

Optional weak supervision:

* commit title / log if present and non-trivial

### 6.4 Outputs

A set of reconstructed clean change units.

These units are not yet final patterns.
They are the stabilized input layer for semantic extraction.

### 6.5 Reconstruction principle

A dirty diff container may contain multiple semantic themes.
The system must first split it into **semantic clusters**, then turn those clusters into cleaner change units.

---

## 7. Phase 2 — Demand Semantics Extraction and Pattern Compression

### 7.1 Goal

On top of clean change units, reconstruct demand-oriented semantic assets and compress them into reusable patterns.

### 7.2 Outputs

For each valid semantic case, produce:

* `commit_log`
* `rules`
* `invariants`
* `issue_text`
* `development_type`
* `split_suggestion`

Then compress many such cases into:

* a small set of domain patterns
* canonical representative cases
* compact retrieval space for agents

---

## 8. Core Semantic Structure

The system is built on a two-level semantic model:

### 8.1 Object Subject

The object subject is the **domain-level semantic carrier**.

It answers:

> **what domain object is being changed?**

This is not a file path or micro implementation path.
It should be a domain-mapped object such as:

* `qserver`
* `feature extraction`
* `parser`
* `registry`
* `discovery`
* `config system`

The object subject should be:

* concrete enough to support useful retrieval
* coarse enough to avoid pattern explosion
* stable across many historical changes

### 8.2 Action

The action is the **type of demand change applied to the object**.

It answers:

> **what kind of demand change happened on this object?**

Examples:

* add
* fix
* optimize
* refactor
* migrate

Action is not the semantic subject.
It is the change direction on the semantic subject.

### 8.3 Combined Meaning

A semantic case is fundamentally structured as:

> **object subject + action**

This is the minimal semantic skeleton.

Everything else is derived around this skeleton.

---

## 9. Clean Change Unit vs Semantic Case

These are related, but not identical.

### 9.1 Clean Change Unit

A reconstruction artifact from Phase 1.

It is a cleaner historical change unit extracted from a dirty diff container.

### 9.2 Semantic Case

A demand-oriented semantic unit extracted from a clean change unit.

In many cases, a clean change unit may map 1:1 to a semantic case.
But conceptually they differ:

* clean change unit = historical reconstruction layer
* semantic case = demand semantics layer

---

## 10. Semantic Fields

### 10.1 `commit_log`

#### Definition

`commit_log` is the reconstructed **change summary** for a semantic case.

It is not the git-native commit title or message.

It answers:

> **what code change happened in this semantic case?**

It should be built primarily from diff evidence, with optional weak supervision from title/log if present.

#### Role

It is the **fact layer**.

It should express:

* the object subject
* the main change action
* enough implementation-facing signal to ground the case

#### Boundary

It must not become:

* an issue sentence
* a rule
* a human essay
* a copy of commit metadata

---

### 10.2 `rules`

#### Definition

`rules` are the **object-specific semantic constraints** around the modified object.

They answer:

> **what semantic relations must not be broken while changing this object?**

#### Role

They are the **constraint layer**.

They transfer to future similar modifications.

#### Boundary

They are not:

* generic coding hygiene
* null checks
* bounds checks
* exception handling advice
* style advice

They must be tied to the object subject, not to general engineering correctness.

---

### 10.3 `invariants`

#### Definition

`invariants` are the **object-specific semantic properties that must remain true after the change**.

They answer:

> **what semantic properties must still hold after modifying this object?**

#### Role

They are the **preservation layer**.

#### Boundary

They are not:

* “tests pass”
* “system does not crash”
* “code compiles”
* generic correctness clichés

They must express meaningful object semantics.

---

### 10.4 `issue_text`

#### Definition

`issue_text` is the **compressed requirement-style expression** of the semantic case.

It answers:

> **if this semantic case is compressed into one short demand sentence, what does it become?**

#### Role

It is the **retrieval entry layer**.

This is the field most likely to serve direct matching between a current demand and historical cases.

#### Boundary

It must be:

* short
* single-sentence
* single-subject
* requirement-oriented

It must not:

* include hidden constraints
* include multi-clause expansions
* include supporting noise
* become vague and generic

---

### 10.5 `development_type`

#### Definition

The high-level change type of the case.

Allowed values:

* feature
* bugfix
* refactor
* migration
* optimize

#### Role

It is the normalized action type.

---

### 10.6 `split_suggestion`

#### Definition

A signal indicating whether the current case overflows semantic compression.

It answers:

> **does this candidate case still fit into one short single-subject issue expression, or is it too broad / multi-intent?**

#### Role

It is the semantic overflow guard.

---

## 11. Weak Semantic Signals

Tests, configs, flags, trivial wiring, cleanup, and similar supporting expressions are treated as:

> **weak semantic signals**

They are not the focus of the system.

They may still provide value as:

* supporting context
* bugfix evidence
* semantic-value hints
* confidence support for rules/invariants

But they should not dominate:

* the object subject
* the main action
* the primary pattern space

This system is not centered on tests/configs/supporting edits.
It is centered on main object-level demand changes.

---

## 12. Success Criteria

### 12.1 Phase 1 success

The system can transform dirty commit containers into cleaner change units such that:

* multiple mixed intentions are separated
* supporting edits do not dominate
* resulting units can be meaningfully summarized

### 12.2 Case-layer success

The system can produce semantic cases where:

* the object subject is stable
* the action is stable
* the fact/constraint/compression layers do not contaminate each other

### 12.3 Retrieval success

The produced cases are suitable for Agent few-shot / retrieval:

* high relevance
* low noise
* low repetition
* useful transfer value

### 12.4 Pattern success

Within a domain, the system compresses many cases into a small set of reusable patterns.

Target pattern count:

* `< 10` excellent
* `10–20` acceptable
* `> 20` warning
* `> 30` likely abstraction failure

### 12.5 Noise success

Low-value historical noise does not dominate the main case library.

---

## 13. Failure Modes

The system fails if it does any of the following:

### 13.1 Treats dirty commit containers as clean semantic units

This causes everything downstream to become unstable.

### 13.2 Trusts commit metadata too much

If title/log become the primary semantic source, the system becomes repository-style dependent and fragile.

### 13.3 Uses micro implementation paths as object subjects

This leads to case fragmentation and pattern explosion.

### 13.4 Lets weak semantics dominate

If tests/configs/supporting edits drive the semantic case, the output becomes noisy and low-transfer.

### 13.5 Produces too many patterns in one domain

This usually indicates over-fragmentation or weak compression, not genuine domain diversity.

---

## 14. Decision Preferences

### 14.1 Diff-first

Always treat code diff as the primary semantic evidence.

### 14.2 Commit metadata as weak supervision only

Use title/log only as auxiliary hints or consistency checks.

### 14.3 Domain-level object subject

Use domain-mapped objects such as `qserver` or `feature extraction`, not path-level micro objects.

### 14.4 Object subject first, action second

The system first identifies the object subject, then identifies the action on that object.

### 14.5 Weak semantics are supporting, not primary

Tests/configs/supporting edits may influence judgment, but must not define the main semantic structure.

### 14.6 Compact pattern space is a requirement

If pattern space is too large, assume the abstraction failed rather than assuming the domain is naturally that fragmented.

---

## 15. Final Statement

This system should be understood as:

> **a diff-first, Agent-first demand pattern compression system that reconstructs clean change units from dirty historical commit containers, then extracts demand-oriented semantic cases, and finally compresses them into a small, high-cohesion pattern space for retrieval and few-shot reuse.**
