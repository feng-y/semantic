可以，下面给你一版可直接写进 SPEC.md 的正式文本。
它包含两部分：
    1.  rules / invariants 的定义与生产规范
    2.  为什么它们不应在生成 commit_log 时一起生产

⸻

Rules and Invariants

Purpose

rules and invariants capture the system-semantics view of a semantic unit.

They are not change summaries.
They are not requirement titles.
They are not generic engineering best practices.

They exist to expose the semantic boundaries of the modified object so that future agents can understand:
    •   what relations must not be broken
    •   what properties must remain true
    •   what kinds of semantic repairs are happening repeatedly in the system

⸻

rules

rules are the object-specific semantic constraints around the modified object.

They answer:

while changing this object, what semantic relations or boundaries must not be violated?

Typical examples include:
    •   alignment constraints
    •   compatibility boundaries
    •   boundedness requirements
    •   contract preservation
    •   mapping consistency
    •   subsystem interaction rules

A valid rule must be:
    •   tied to the object subject
    •   semantically meaningful
    •   useful for future similar modifications
    •   more specific than generic engineering hygiene

A rule must not be:
    •   null-check advice
    •   bounds-check advice
    •   exception-handling advice
    •   style advice
    •   a paraphrase of the code action itself

⸻

invariants

invariants are the object-specific semantic properties that must remain true after the change.

They answer:

after modifying this object, what semantic properties must still hold?

Typical examples include:
    •   preserved alignment
    •   preserved compatibility
    •   preserved boundedness
    •   preserved state consistency
    •   preserved externally visible semantic behavior

A valid invariant must be:
    •   tied to the object subject
    •   phrased as a preserved property
    •   useful for future reasoning and validation
    •   independent from generic correctness clichés

An invariant must not be:
    •   “the system should not crash”
    •   “the code should compile”
    •   “tests should pass”
    •   “behavior should be correct”

These are too generic and do not express object semantics.

⸻

Production Principle

rules and invariants must be extracted from the semantic relations visible in the diff, around the identified object subject.

They should be inferred from evidence such as:
    •   restored or preserved alignment relations
    •   compatibility handling
    •   bounded resource control
    •   repaired consistency relations
    •   preserved contracts between subsystems
    •   regression tests that reveal preserved semantics

They must be produced from the same semantic unit as commit_log, but from a different analytical view.

⸻

Why rules / invariants must not be produced together with commit_log

commit_log and rules / invariants must not be generated as one combined output, and rules / invariants must not be treated as a direct extension of commit_log.

This is a structural requirement, not an implementation preference.

1. They answer different questions

commit_log answers:

what code change happened?

It is the change-action view.

rules / invariants answer:

what semantic relations must not be broken, and what semantic properties must remain true?

They are the system-semantics view.

These are different questions, with different output goals.

⸻

2. Producing them together causes view contamination

If rules / invariants are generated together with commit_log, they tend to collapse into action restatements.

Example:
    •   commit_log: 调整 qserver 请求转换逻辑，修正结果组装路径。
    •   bad rules: qserver 请求转换逻辑需要保持正确。
    •   bad invariants: qserver 请求转换行为保持稳定。

These are not real semantic constraints or preserved properties.
They are only weak paraphrases of the change action.

So joint generation creates a strong failure mode:

rules/invariants degenerate into watered-down restatements of the change summary.

⸻

3. commit_log is intentionally compressive, while rules / invariants require relation recovery

A good commit_log must stay:
    •   short
    •   action-oriented
    •   concrete
    •   centered on what changed

Because of that, it necessarily compresses away many semantic relations.

But rules / invariants depend exactly on those relations, for example:
    •   alignment
    •   compatibility
    •   boundedness
    •   mapping consistency
    •   preserved contracts
    •   restored system invariants

These relations may be visible in the diff and in regression evidence, but may disappear once everything is compressed into a short change summary.

So if rules / invariants are generated only after or together with commit_log, the model is forced to recover semantic relations from already-compressed text, which is both lossy and unstable.

⸻

4. They require different optimal output styles

A good commit_log should emphasize:
    •   main object
    •   main action
    •   implementation-facing change

A good rule or invariant should emphasize:
    •   relation
    •   boundary
    •   semantic contract
    •   preserved property

These styles are different.

If one prompt is asked to produce both at once, the output often converges to a vague middle form:
    •   not concrete enough as a change summary
    •   not sharp enough as a semantic rule
    •   not stable enough for downstream reuse

Therefore the system should preserve the distinction between:
    •   change description
    •   semantic boundary extraction

⸻

5. In harness engineering, these are different assets

From a harness-engineering perspective, commit_log and rules / invariants are not just different fields.
They are different reusable assets.

commit_log captures:

how the object was changed

rules / invariants capture:

what must not be broken when changing this object

The first supports:
    •   historical analogy
    •   implementation traceability
    •   action understanding

The second supports:
    •   constraint transfer
    •   bugfix/repair reasoning
    •   future-agent boundary awareness
    •   system rule mining

If they are produced together, these two asset types get blurred into one descriptive layer, which reduces long-term reuse value.

⸻

Required production structure

For each semantic unit, the system must use parallel extraction views:

Change-action view
Produces:
    •   commit_log

System-semantics view
Produces:
    •   rules
    •   invariants
    •   optional internal repair semantics

Only after these two views are independently extracted may the system combine them to support:
    •   issue_text
    •   development_type
    •   downstream pattern compression

This separation is required to preserve both action clarity and semantic-boundary quality.

⸻

Final requirement

rules / invariants must be specified and produced as a separate semantic view, not as a byproduct of commit_log.

A system that generates both together will usually produce:
    •   weaker rules
    •   weaker invariants
    •   more action paraphrases
    •   less reusable harness assets

Therefore:

commit_log and rules / invariants must be extracted separately from the same semantic unit, because they represent different views of the same change: one is about what changed, the other is about what semantic relations must be preserved or restored.
