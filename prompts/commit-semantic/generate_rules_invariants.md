# Generate Rules and Invariants

You are given one `semantic_case` and its `commit_log`.

Your task is to extract:

- `rules`
- `invariants`

You are not rewriting the commit log.
You are not writing an issue sentence.
You are not writing general coding advice.
You must output YAML only.

---

## Goal

Given one `semantic_case`, identify the object-specific semantic constraints and preserved semantic properties of the modified object.

You must output:

- `rules`
- `invariants`

---

## What `rules` mean

`rules` are the object-specific semantic constraints that must be respected while modifying this logic.

They may include:

- business logic constraints
- subsystem contract constraints
- concurrency/resource bounds
- request-response alignment constraints
- data mapping constraints
- compatibility or migration boundaries

A valid `rule` must be strongly related to the modified object of this `semantic_case`.

---

## What `invariants` mean

`invariants` are the object-specific semantic properties that must remain true after the change.

They may include:

- preserved alignment relations
- preserved external behavior relations
- preserved historical compatibility semantics
- preserved subsystem-level semantic stability properties

A valid `invariant` must be strongly related to the modified object of this `semantic_case`.

---

## Core principle

`commit_log` says:

> what was changed

`rules / invariants` say:

> around this modified object, what semantic constraints must not be broken, and what semantic properties must still hold

They are not generic engineering hygiene.

---

## Important exclusion

Do NOT output generic coding advice or development hygiene, such as:

- null checks
- bounds checks
- exception handling
- input validation
- avoiding crashes
- generic thread-safety advice
- code style guidance
- defensive programming clichés

These are NOT valid `rules` or `invariants` for this task.

If you cannot infer stable object-specific semantic constraints, prefer empty arrays.

---

## Core constraints

### 1. Do NOT repeat the commit log
Do not restate what was changed.

### 2. Must be object-specific
The rule or invariant must be tightly tied to the modified object/path/subsystem of this case.

### 3. Must be semantically meaningful
It should reflect a real logic contract, semantic boundary, alignment property, compatibility requirement, concurrency bound, or system-level relation.

### 4. Avoid duplication
Do not write near-identical meanings in both `rules` and `invariants`.

### 5. Empty is allowed
If the case does not support a stable high-value result, output empty arrays.

---

## Good examples

### Example 1: parser compatibility

```yaml
rules:
  - legacy syntax compatibility must be preserved during repair

invariants:
  - historical inputs remain parseable
```

### Example 2: qserver request-response alignment

```yaml
rules:
  - request item filtering must preserve score response alignment

invariants:
  - returned scored items remain aligned with effective request items
```

### Example 3: feature extraction concurrency control

```yaml
rules:
  - feature extraction worker count must remain under configured concurrency bound

invariants:
  - extraction concurrency remains bounded by the current scheduling model
```

### Example 4: discovery backend integration

```yaml
rules:
  - new backend integration must preserve current discovery abstraction contract

invariants:
  - existing discovery behavior remains stable
```

### Example 5: config migration

```yaml
rules:
  - legacy config path must remain readable during transition

invariants:
  - existing config behavior remains available
```

---

## Bad examples

```yaml
rules:
  - check null pointer
  - avoid out of bounds

invariants:
  - system does not crash
```

```yaml
rules:
  - fix parser logic

invariants:
  - parser logic is fixed
```

Why bad:

* generic engineering hygiene
* repeats the code action
* not object-specific semantic constraints

---

## Input

You will receive YAML like this:

```yaml
case_id: ...
commit_id: ...
module: ...

commit_log: ...

files: [...]
diff_chunks: [...]
related_tests: [...]

bugfix_evidence:
  weak: [...]
  medium: [...]
  strong: [...]
```

Only infer from the provided case and `commit_log`.
Do not invent missing semantics.

---

## Output format

You must output YAML only:

```yaml
rules: []
invariants: []
```

---

## Final reminder

Only output object-specific semantic constraints and preserved properties.

Do not output generic coding guidance.
Do not repeat the change action.
Prefer empty arrays over vague filler.
