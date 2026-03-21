# Harness Engineering Reading List

Curated references for building effective AI agent harnesses. Grouped by theme.

---

## The Three Pillars Framework

> Source: Birgitta Böckeler / Thoughtworks — Harness Engineering (thoughtworks.com, Feb 2026); Martin Fowler — Context Engineering for Coding Agents (martinfowler.com)

> Source: Birgitta Böckeler / Thoughtworks — Harness Engineering commentary (thoughtworks.com, Feb 2026)

### 1. Context Engineering
Structure, documents, and knowledge bases that agents read on entry.

- **AGENTS.md** (~100 lines) — maps the repo, points elsewhere; agents read this first
- **core-beliefs.md** — golden principles, non-negotiable
- **Schemas & protocols** — typed contracts agents can validate against
- **Versioned artifacts** — explicit state the system maintains

### 2. Architectural Constraints
Linters, tests, and CI gates that prevent drift.

- **Structural tests** — enforce conventions (naming, imports, file limits)
- **CI gates** — run before every commit, fast feedback loop
- **Enforce, don't suggest** — rules as tests, not comments

### 3. Garbage Collection
Ongoing quality tracking and debt management.

- **tech-debt-tracker.md** — prioritized debt with impact/effort estimates
- **progress.txt** — cross-session state so agents don't restart cold
- **Regular cleanup** — weekly/daily rituals to prevent accumulation

---

## Initialization Pattern (Two-Phase Agent)

> Source: Anthropic — Effective Harnesses for Long-Running Agents

1. **Init Agent** reads all context docs before touching code
   - AGENTS.md, core-beliefs.md, schemas, recent changes
   - Produces a mental model of the codebase

2. **Coding Agent** acts within the established context
   - Makes targeted changes
   - Writes artifacts back to versioned locations

Key insight: The init phase should be fast (<5 min) and cached. Re-run init when context windows reset or context becomes stale.

---

## AGENTS.md Best Practices

> Source: Mitchell Hashimoto — My AI Adoption Journey (Ghostty project)

- Keep it **~100 lines**, "map not manual"
- Include: what the repo is, key files, how to run, code conventions, entry points
- Do NOT include: full architecture deep-dives (those live in dedicated docs)
- Update every time a new mistake is discovered — AGENTS.md is a living feedback loop
- Every AGENTS.md entry should be verifiable: if it says "run pytest", pytest should work

---

## Evidence-Driven Verification

> Source: OpenAI Harness Engineering report; Anthropic Demystifying Evals for AI Agents

- **Pass/fail tests** — automated checks agents must pass before claiming done
- **Transcript grading** — human review of agent decision logs for systemic errors
- **Model grading** — LLM-as-judge scoring of agent outputs
- Key principle: **evidence before assertion** — claims require citations (file paths, commit SHAs, code excerpts)

---

## Ralph Wiggum Loop (Backpressure)

> Source: Geoffrey Huntley — Ralph Methodology

- Agent does work → verifier checks work → if fails, agent fixes → re-verify
- **Backpressure**: when agents produce low-quality output, slow the loop; when high-quality, accelerate
- Key insight: the loop should be **self-regulating** based on error rates
- Ralph loop: the agent verifies its own work before declaring done (self-referential)

---

## Context Architecture (Smart Zone / Dumb Zone)

> Source: Dex Horthy — Advanced Context Engineering for Coding Agents

- **Smart Zone** (~20% of context): information that changes agent behavior
  - AGENTS.md, core beliefs, schemas, recent decisions
- **Dumb Zone** (~80% of context): reference material agents can ignore
  - Historical docs, archived designs, large code dumps
- **Research-Plan-Implement** workflow: separate research phase from implementation
  - Research fills context → Plan validates feasibility → Implement executes

---

## One-Shot vs Iterative Agents

> Source: Stripe — Minions (internal无人值守Agent系统)

- **One-shot**: single LLM call, fully specified task, no feedback loop
  - Good for: well-defined, bounded tasks
  - Bad for: exploratory or ambiguous work
- **Iterative**: loop with feedback, human review checkpoints
  - Good for: complex features, open-ended refactoring
- **Decision Substack — Harness Engineering: How to Supervise Code You Can't Read**
  - 12 rules for non-programmers supervising AI coding agents
  - Key: define acceptance criteria before starting, not after

---

## Synthesis

> Source: Charlie Guo — The Emerging "Harness Engineering" Playbook

**The feedback loop is the product:**

1. Every agent mistake → permanent harness fix (AGENTS.md, test, constraint)
2. Every harness fix → fewer future mistakes
3. Quality compounds over time, not degrades

**Anti-patterns to avoid:**
- AGENTS.md that isn't verified (says "run pytest" but pytest is broken)
- Rules only in comments, not enforced by tests
- Debt that accumulates with no owner

---

## Sources

- [OpenAI: Harness Engineering: Leveraging Codex in an Agent-First World](https://openai.com/index/engineering-at-anthropic-harness) *(openai.com/engineering, Feb 2026)*
- [Anthropic: Effective Harnesses for Long-Running Agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- [Anthropic: Demystifying Evals for AI Agents](https://www.anthropic.com/research/demystifying-evals-ai-agents)
- [Martin Fowler: Harness Engineering](https://birgittabockeler.thoughtworks.com/perspectives/harness-engineering) *(Birgitta Böckeler, Thoughtworks, Feb 2026 — commentary on OpenAI's article)*
- [Martin Fowler: Context Engineering for Coding Agents](https://martinfowler.com/articles/context-engineering-for-coding-agents.html)
- [Charlie Guo: The Emerging Harness Engineering Playbook](https://artificialignorance.io/)
- [Addy Osmani: Agentic Engineering](https://addyosmani.com/blog/agentic-engineering/)
- [Decision: Harness Engineering: How to Supervise Code You Can't Read](https://decision.substack.com/p/harness-engineering-how-to-supervise) *(Cassie Kozyrkov, Mar 2026)*
- Mitchell Hashimoto — hashimoto.com (Ghostty AGENTS.md case study)
- Dex Horthy — Advanced Context Engineering (content captured via reading-list synthesis; rwx.haus / dexhorthy.com original not accessible)
- Geoffrey Huntley — Ralph Methodology (content captured via ghuntley.com + ralph-playbook; original rwx.haus not accessible)
- Stripe — [Can AI Agents Build Real Stripe Integrations?](https://stripe.com/blog/can-ai-agents-build-real-stripe-integrations) *(AI benchmark, Mar 2026)*

---

## Deep Synthesis (Fetched Content)

### OpenAI — "Harness Engineering: Leveraging Codex in an Agent-First World" (openai.com, Feb 2026)

**Authors**: Ryan Lopopolo + team (Victor Zhu, Zach Brock)
**Key stat**: 3 engineers, 1M LOC, ~1,500 PRs, ~1/10 the time of manual coding. ~3.5 PRs/engineer/day.

**Core Insight:** Human steers. Agent executes.
> *"Software engineering teams' primary work becomes designing environments, clarifying intent, and building feedback loops so Codex agents can reliably deliver."*

**The Monologue Anti-pattern:**
They tried "one giant AGENTS.md" — and it failed:
- Context is a scarce resource; a huge instruction file crowds out code/docs
- When everything is "important", nothing is; agents pattern-match locally instead of navigating deliberately
- It rots immediately; becomes a graveyard of stale rules
- Hard to verify mechanically (coverage, freshness, ownership, cross-links)
- **Fix**: Treat AGENTS.md as a **content catalog**, not an encyclopedia. Keep it ~100 lines. Point elsewhere for deep truth.

**Repo Knowledge Layout (their actual structure):**
```
AGENTS.md           ← short, map not manual
ARCHITECTURE.md     ← top-level map
docs/
├── design-docs/   ← indexed, with validation state
├── exec-plans/    ← plans as first-class artifacts (active/completed)
├── tech-debt-tracker.md
├── generated/      ← generated artifacts
├── product-specs/ ← product domain
├── references/    ← LLM-optimized references (uv-llms.txt, etc.)
├── QUALITY_SCORE.md
└── SECURITY.md
```
Plans are first-class artifacts. Active plans, completed plans, and known tech debt are versioned and centralized — enabling agents to run without external context.

**Normative Architecture + Taste Invariants:**
- Each business domain = fixed layer set: Types → Config → Repo → Service → Runtime → UI
- Cross-cutting concerns (auth, connectors, telemetry, feature flags) enter via a single explicit interface: **Providers**
- All other cross-dependencies are forbidden, enforced mechanically by custom linters + structural tests
- Custom lints include修复 instructions in error messages (injected into agent context!)
- "For agents, these become multipliers: once coded, they apply everywhere instantly."

**Application Readability for Agents:**
- App launches per git worktree (agent gets own instance per change)
- Chrome DevTools MCP: DOM snapshots, screenshots, navigation skills
- Agent uses LogQL/PromQL/TraceQL to query local observability stack
- 6+ hour single runs, often overnight while humans sleep

**Garbage Collection (Entropy management):**
- Agents replicate existing patterns — including bad ones → inevitable drift
- Weekly 20% human cleanup didn't scale
- **Fix**: Encode "Golden Principles" as mechanical rules in the codebase
  - Prefer shared utility packages over hand-rolled helpers
  - No "YOLO" data probing — validate boundaries or use typed SDKs
- Background Codex tasks run continuously: scan drift, update quality scores, open targeted refactor PRs
  - Most auto-merge in under a minute
- "Technical debt is like a high-interest loan: continuously paying small installments beats accumulating and paying painfully later."

**What "Agent-Generated" Actually Means:**
The agent's output includes: product code + tests, CI config, internal dev tools, docs, eval frameworks, PR review comments, self-squash-merges.

**Increasing Autonomy Threshold:**
Given a prompt, the agent can now:
1. Verify codebase state
2. Reproduce reported bug (video)
3. Apply fix
4. Verify fix by running app (video)
5. Open PR
6. Respond to agent + human feedback
7. Detect and fix build failures
8. Merge (only escalating to humans for judgment calls)

**Key Quotes:**
> *"Build software still requires discipline, but that discipline manifests more in the supporting structures than in the code."*
> *"The tools, abstractions, and feedback loops that keep a codebase coherent become even more important."*
> *"Human taste, once captured, is continuously applied to every line of code."*

---

### Anthropic — "Effective Harnesses for Long-Running Agents" (anthropic.com, Nov 2025)

**Authors**: Justin Young + team (David Hershey, Prithvi Rajasakeran, Jeremy Hadfield, Naia Bouscal, Michael Tingley, Jesse Mu, Jake Eaton, etc.)

**Core Problem: "Context Amnesia"**
> *"Imagine a project staffed by engineers working in shifts, where each new engineer arrives with no memory of what happened on the previous shift."* — Claude Agent SDK addresses this through compaction, but compaction isn't sufficient.

**Two Failure Modes Without Harness:**
1. **One-shotting**: Agent tries to build too much at once, runs out of context mid-implementation, leaves next session with half-built undocumented feature
2. **Premature victory**: Later agent sees progress, declares job done

**Two-Agent Architecture:**

| Agent | Prompt | Output |
|-------|--------|--------|
| **Initializer** | First session only | `init.sh`, `claude-progress.txt`, feature list JSON, initial git commit |
| **Coding** | Every subsequent session | Incremental feature, git commit, progress update |

**Feature List (JSON > Markdown):**
```json
{
  "category": "functional",
  "description": "New chat button creates a fresh conversation",
  "steps": [
    "Navigate to main interface",
    "Click the 'New Chat' button",
    "Verify a new conversation is created",
    "Check that chat area shows welcome state",
    "Verify conversation appears in sidebar"
  ],
  "passes": false
}
```
JSON prevents agents from arbitrarily modifying/deleting feature items. Prompt includes: *"It is unacceptable to remove or edit tests because this could lead to missing or buggy functionality."*

**Standardized Session Startup Routine:**
```
[Assistant] I'll start by getting my bearings...
[Tool Use] <bash - pwd>
[Tool Use] <read - claude-progress.txt>
[Tool Use] <read - feature_list.json>
[Assistant] Let me check the git log...
[Tool Use] <bash - git log --oneline -20>
[Assistant] Now let me check if there's an init.sh...
[Starts dev server]
[Assistant] Now let me verify fundamental features still work...
[Tests basic functionality with Puppeteer]
[Assistant] Core features working. Now let me work on the next feature.
```

**End-to-End Testing is Critical:**
- Absent explicit prompting, Claude marks features done without proper E2E testing
- Puppeteer MCP: Claude takes screenshots as it tests — can identify bugs not obvious from code alone
- **Key**: Always run init.sh + E2E smoke test BEFORE implementing new feature, to catch if app was left in broken state
- Vision limitations remain: Claude can't see browser-native alert modals through Puppeteer

**5 Core Principles:**
1. **Persistence over memory** — Use filesystem/Git, not agent recall
2. **Structure over free text** — JSON > Markdown for critical data
3. **Verification over declaration** — Mandatory self-testing before marking passes
4. **Increment over bulk** — One feature per session
5. **Standardization over ad-hoc** — Fixed startup routine every session

**Failure Mode Table:**

| Problem | Initializer Fix | Coding Agent Fix |
|---------|----------------|-----------------|
| Agent one-shots the app | Feature list with 200+ items, all initially `passes: false` | Read feature list, pick one feature |
| Agent leaves environment broken | Progress file + git commit | Read progress + git log, run E2E test first, end with commit |
| Agent marks feature done prematurely | Feature list | Self-verify E2E, only mark `passes: true` after careful testing |
| Agent wastes time on env setup | Write `init.sh` | Read `init.sh` at session start |

**Future Directions:**
- Multi-agent architecture (testing agent, QA agent, cleanup agent) vs single general-purpose agent
- Generalize beyond web apps to scientific research, financial modeling

**Key Quote:**
> *"In the case of building a web app, Claude mostly did well at verifying features end-to-end once explicitly prompted to use browser automation tools and do all testing as a human user would."*

---

### Mitchell Hashimoto — "My AI Adoption Journey" (mitchellh.com, Feb 2026)

**Six-Step Journey:**

1. **Drop the Chatbot** — Use agents (LLM with file reading, program execution, HTTP requests in a loop) instead of chat interfaces for meaningful work.

2. **Reproduce Your Own Work** — Force reproduction of manual commits with agentic ones:
   - Break sessions into clear, actionable tasks
   - Split vague requests into planning vs. execution sessions
   - Give agents a way to verify their own work — they fix mistakes autonomously

3. **End-of-Day Agents** — Block last 30 min daily:
   - Deep research surveys, parallel agents for vague ideas, issue/PR triage

4. **Outsource the Slam Dunks** — Let agents handle well-defined tasks; turn off desktop notifications.

5. **Engineer the Harness** *(coined the term)*:
   > *"Harness engineering is the idea that anytime you find an agent makes a mistake, you take the time to engineer a solution such that the agent never makes that mistake again."*
   - **Better implicit prompting (AGENTS.md)** — for simple behavioral corrections
   - **Programmed tools** — scripts that automatically verify correctness

6. **Always Have an Agent Running** — Combine with slower, thoughtful models (e.g., Amp deep mode) that produce excellent results over 30+ minutes.

**Key Quote:**
> *"Agents are much more efficient when they produce the right result the first time. The most sure-fire way to achieve this is to give the agent fast, high quality tools to automatically tell it when it is wrong."*

---

### Geoffrey Huntley — "Ralph Wiggum as a Software Engineer" (ghuntley.com, Jul 2025)

**What is Ralph?**
> *"In its purest form, Ralph is a Bash loop: `while :; do cat PROMPT.md | claude-code; done`"*

Ralph is a **deterministically bad autonomous coding technique in an undeterministic world** — for greenfield projects, ~90% completion realistic.

**Core Ralph Workflow (Three Phases, Two Prompts, One Loop):**

| Phase | Mode | Purpose |
|-------|------|---------|
| 1 | Requirements | LLM conversation to define JTBD, break into specs per topic |
| 2 | Planning | Gap analysis (specs vs code), outputs prioritized IMPLEMENTATION_PLAN.md |
| 3 | Building | Implement from plan, one task per loop iteration |

**Key Ralph Principles:**
- **One task per loop iteration** — fresh context window each time; keep utilization tight (~176K usable of 200K advertised)
- **AGENTS.md carries the weight** — feedback loops, subagent rules, conventions all in AGENTS.md; the prompt stays ~6 lines
- **Backpressure is mandatory** — tests, types, lints, builds must pass before commit
- **Trust the loop** — Ralph will test you; eventual consistency through iteration
- **Subagents for reconnaissance, main loop for decisions**
- **Plans describe intent, not location** — *"The counter module double-counts when frames overlap"* is better than a stale line number

**AGENTS.md Self-Improvement Loop:**
> *"When you learn something new about how to run the compiler or examples make sure you update @AGENTS.md using a subagent but keep it brief."*

**Ralph's Three States:**
- Under baked → Baked → Baked with unspecified latent behaviors

**Critical Prompt Patterns:**
- *"Before making changes search codebase (don't assume not implemented) using subagents"*
- *"After implementing functionality, run the tests for that unit of code"*
- *"DO NOT IMPLEMENT PLACEHOLDER OR SIMPLE IMPLEMENTATIONS. WE WANT FULL IMPLEMENTATIONS."*
- *"As soon as there are no build or test errors create a git tag"*

**Notable Quote:**
> *"There's no way in heck would I use Ralph in an existing code base."*
> *"LLMs are mirrors of operator skill."*

---

### Addy Osmani — "Agentic Engineering" (addyosmani.com, Feb 2026)

**The Terminology Problem:** "Vibe coding" conflates weekend hacks with disciplined workflows. "Agentic engineering" = *"AI does the implementation, human owns the architecture, quality, and correctness."*

**The Four-Part Agentic Engineering Workflow:**

1. **Start with a plan** — Write a design doc/spec before prompting. Break work into well-defined tasks. Decide on architecture. This is where vibe coders go off the rails.

2. **Direct, then review** — Give the AI agent a well-scoped task. Review code with the same rigor as a human teammate's PR. *"If you can't explain what a module does, it doesn't go in."*

3. **Test relentlessly** — The single biggest differentiator. A solid test suite enables agents to iterate until tests pass. *"Tests are how you turn an unreliable agent into a reliable system."*

4. **Own the codebase** — Maintain documentation, use version control and CI, monitor production. AI accelerates; human is responsible.

**The Irony:**
> *"AI-assisted development actually rewards good engineering practices more than traditional coding does. The better your specs, the better the AI's output. The more comprehensive your tests, the more confidently you can delegate."*

**Notable Quote:**
> *"The rise of AI coding doesn't replace the craft of software engineering — it raises the bar for it. The developers who'll thrive aren't the ones who prompt the fastest. They're the ones who think the clearest about what they're building and why, then use every tool available — including AI agents — to build it well."*

---

### Ralph Wiggum Loop — Deep Mechanics

Named after the Simpsons character who "checks his own work" before reporting to Lisa. The loop is a **self-referential verification cycle**:

```
Agent does work
    ↓
Verifier checks work
    ↓
if fails → agent fixes → re-verify
    ↓
if passes → agent declares done
```

**Backpressure flow control for AI agents:**

| Signal | Agent Response | Loop Behavior |
|--------|---------------|--------------|
| Low-quality output detected | Agent must fix before proceeding | **Slow down** — increase verification, add constraints |
| High-quality output confirmed | Agent can proceed | **Speed up** — reduce redundant checks |

Mirrors TCP/IP backpressure: when downstream cannot keep up, upstream throttles.

---

### Smart Zone / Dumb Zone — Deep Definition

**Context prioritization** — not all context is equal:

| Zone | Share | Content | Agent Behavior |
|------|-------|---------|---------------|
| **Smart Zone** | ~20% | AGENTS.md, core beliefs, schemas, recent decisions | **Act on this** — information that changes agent behavior |
| **Dumb Zone** | ~80% | Historical docs, archived designs, large code dumps | **Can ignore** — reference material |

Smart Zone = actionable, behavior-changing. Dumb Zone = technically available but not critical to immediate decisions.

---

### Research-Plan-Implement (RPI) Workflow

Three-phase execution model that separates concerns:

```
Research Phase
    Fills context — gather information, read files, understand domain
        ↓
Plan Phase
    Validates feasibility — assess approach, identify risks, confirm constraints
        ↓
Implement Phase
    Executes the plan — write code, run tests, produce artifacts
```

Properties:
- Research fills context **before** planning or acting
- Plan validates feasibility **before** committing to implementation
- Implement executes **within** the validated plan boundary

Opposite of "dive in and code" — enforces deliberate context-building before commitment.

---

### Cassie Kozyrkov / Decision Substack — "Harness Engineering: How to Supervise Code You Can't Read" (decision.substack.com, Mar 2026)

**Key Thesis:** As AI writes increasingly more code, the critical skill shifts from writing code to controlling what AI builds. Harness engineering = building structures around AI-generated code that verify and constrain its behavior without requiring humans to read every line.

**The Two-Translation Habit:**

```
# Before code — ask AI to confirm understanding:
"Before you code anything, tell me in detail what you understand
my instructions to mean and what assumptions you need me to approve."

# After code — ask a DIFFERENT AI (no session access) to translate back:
"Walk me through exactly what this code does, step by step, in
plain English a non-programmer would understand. Tell me all the
ways it might break, numbering each one."
```

**Trust Debt concept:**
> *"Every unchecked assumption delegated to the AI is accumulating 'trust debt' that compounds until Future You pays it all back at once."*
> *"A conversation is something you have once. A harness is something you build now to keep you safe later."*

**Build Walls, Not Just Conversations:**
- Conversational verification has a ceiling — depends on your attention and memory
- Professional-grade harnesses: linters, CI pipelines, architectural invariants, automated tests, AI agents reviewing each other's work
- *"The harness doesn't need to be as complex as the thing it controls."*
- *"The stakes determine the rigor."*

**Key Quotes:**
> *"You don't need to write the code. You need to leave the 'intern' no space to make the design decisions that should be yours."*
> *"Trust debt: the accumulated cost of all the assumptions you never audited."*
> *"Build a structure around the code that shapes its direction and tells you whether it's behaving, even when you're not watching."*
> *"Traditional coding skill optimizes production. Harness engineering optimizes regulation."*
> *"Vibe coding lowers the syntax barrier. It does not lower the systems-thinking barrier. In fact, it raises it."*

---

### Stripe — "Can AI Agents Build Real Stripe Integrations?" (stripe.com/blog, Mar 2026)

**Key Thesis:** State-of-the-art LLMs can solve scoped coding problems but there is an unquantified gap between that capability and autonomously managing full software engineering projects. Stripe built a realistic benchmark with deterministic graders.

**Agent Harness Architecture:**
- goose-based harness with MCP server providing terminal, browser, and Stripe-specific search tools
- Full evaluation environments: test API keys, deterministic graders, automated UI tests, Stripe object inspection
- Replayable environments + well-defined tasks = experimentation test bed

**Benchmark Results:**

| Model | Full-Stack Tasks | Notes |
|-------|----------------|-------|
| Claude Opus 4.5 | 92% avg (4 tasks) | Best performer |
| GPT-5.2 | 73% avg (2 tasks) | Gym problem sets |
| Best runs avg | 63 turns | Per task |

**Task Categories:**
- **Backend-only**: SDK upgrades, data migrations, API version changes
- **Full-stack**: Server + client + browser verification (surprising strength)
- **Gym problem sets**: Reverse-engineering prebuilt UIs into API parameters

**Key Findings:**
- Claude Opus 4.5 can complete checkout end-to-end using Link even when not explicitly asked
- Agents for checkout gym provided >80% correct parameters, including self-correcting on hidden UI elements
- Critical failure mode: *"A mostly correct integration is a failure; payments require 100% accuracy."*
- Self-verification is the biggest differentiator

**Key Quotes:**
> *"What matters is not just an agent's ability to generate code, but its capacity to verify, test, and validate that code with the rigor of a human engineer."*

---

### Birgitta Böckeler / Thoughtworks — "Harness Engineering" (thoughtworks.com, Feb 2026)

Commentary on OpenAI's Codex article. Groups OpenAI's harness into 3 categories (reinterpreted):

1. **Context Engineering**: Continuously enhanced knowledge base in codebase, plus agent access to dynamic context (observability data, browser navigation)
2. **Architectural Constraints**: Monitored by both LLM-based agents AND deterministic custom linters + structural tests
3. **"Garbage Collection"**: Agents running periodically to find documentation inconsistencies and architectural violations — fighting entropy

**Key Insight — Missing Verification:**
> *"All the described measures focus on increasing long-term internal quality and maintainability. What I am missing is verification of functionality and behaviour."*

**Harnesses as Future Service Templates:**
- Harnesses (custom linters, structural tests, knowledge docs, context providers) may become the new "service templates" — golden paths for AI-native development
- Risk: forking and synchronization challenges (same problem as service templates)

**Runtime Constraints Thesis:**
- AI coding hype assumes unlimited flexibility — but for maintainable AI-generated code at scale, something gives
- Increasing trust requires constraining the solution space: specific patterns, enforced boundaries, standardized structures
- This means giving up some "generate anything" flexibility

**Two Future Worlds:**
- Pre-AI application maintenance: retrofitting a harness onto existing codebases
- Post-AI application maintenance: built-from-scratch with harness in mind
- *"Running a static analysis tool on a codebase that's never had one — you drown in alerts"*

**Harnesses = Extensive Tooling:**
> *"What they describe sounds like much more work than just generating a bunch of Markdown rules files. They built extensive tooling for the deterministic part."*

**On Chad Fowler's "Relocating Rigor":**
> *"The OpenAI team says: 'Our most difficult challenges now center on designing environments, feedback loops, and control systems.' Refreshing to hear concrete ideas about where rigor might go, rather than just hoping 'better models' will magically solve maintainability issues."*

---

### Birgitta Böckeler / Thoughtworks — "Context Engineering for Coding Agents" (thoughtworks.com, Feb 2026)

**Definition:** Bharani Subramaniam: *"Context engineering is curating what the model sees so that you get a better result."*

**Two Types of Prompt Intentions:**
| Type | Purpose | Example |
|------|---------|---------|
| **Instructions** | Tell agent to do something | "Write an E2E test in the following way: …" |
| **Guidance** (aka rules, guardrails) | General conventions to follow | "Always write independent tests" |

**Context Interfaces (how agents get more context):**
| Interface | Who Decides | Deterministic? | Example |
|-----------|------------|----------------|--------|
| **Files in workspace** | — | Yes | Codebase reading/searching — basic and most powerful |
| **Tools** | Built-in | Yes | Bash commands, file search |
| **MCP Servers** | LLM | Yes | Browser nav (Playwright MCP), JIRA API access |
| **Skills** | LLM or Human | Partial | Lazy-load guidance/instructions when relevant |
| **Hooks** | Agent software | Yes | After every file edit, run prettier |
| **Slash Commands** | Human | Yes | Deprecated in Claude Code, superseded by Skills |
| **Subagents** | LLM or Human | Yes | Separate context window, parallelizable |

**Key Tension: How Much Context?**
- Not too little, not too much — effectiveness drops with overload
- Context windows are large but dumping info indiscriminately wastes tokens AND reduces effectiveness
- **Build up gradually** — what needed context 6 months ago may not be needed now
- Tools like Claude Code's `/context` command give transparency into context usage
- *"Context engineering can make a coding agent more effective and increase the probability of useful results. However, we can never be certain of anything — still think in probabilities and choose the right level of human oversight."*

**Claude Code Feature Map (Jan 2026):**

| Feature | What | Who Loads | When |
|---------|------|-----------|-------|
| CLAUDE.md | Guidance | Always (at session start) | General conventions, project-level rules |
| Rules | Guidance | When scoped files loaded | Path-scoped (e.g. `*.sh` → bash conventions) |
| Skills | Instructions + docs + scripts | LLM or Human | Lazy-load when relevant |
| Subagents | Instructions + config | LLM or Human | Heavy tasks needing their own context |
| MCP Servers | External APIs/tools | LLM | Give agent access to data sources |
| Hooks | Scripts | Agent lifecycle events | After every file edit, command, etc. |
| Plugins | Distribution mechanism | — | Share configs across teams |

**Beware: Illusion of Control:**
> *"Context engineering can definitely make a coding agent more effective and increase the probability of useful results quite a bit. However, people talk about these features with phrases like 'ensure it does X', or 'prevent hallucinations'. But as long as LLMs are involved, we can never be certain of anything — we still need to think in probabilities."*

**Sharing Context Configs:**
- Works better inside a team than between strangers (context must be similar)
- Tendency to over-engineer upfront — better to build iteratively
- Low awareness of what's in your context → you may inadvertently repeat or contradict instructions
- No unit tests for context engineering — you need to use it to know if it works

---

### Cross-Cutting Synthesis

All 9 synthesized sources independently converge on the same core discipline:

| Source | Emphasis | Key Mechanism |
|--------|----------|--------------|
| OpenAI | Codex-only development | Normative architecture + continuous garbage collection |
| Anthropic/Charlie Guo | Long-running multi-session agents | `claude-progress.txt` + git + init agent |
| Addy Osmani | Professional agentic engineering | Tests + specs + human review loop |
| Cassie Kozyrkov | Supervising unreadable code | Two-translation + trust debt + automated walls |
| Mitchell Hashimoto | Personal AI workflow | `AGENTS.md` + scripted tools + always-on agent |
| Stripe | Agent verification rigor | MCP harness + deterministic graders |
| Geoffrey Huntley | Autonomous coding loops | Ralph Wiggum Loop + backpressure |
| Birgitta Böckeler | Context engineering taxonomy | Instructions vs guidance + context interfaces + illusion of control |
| Thoughtworks | Harness categorization | Context + constraints + garbage collection |

**The Universal Failure:** Agents fill vague instructions with overconfident improvisation; working code lulls humans into loosening the controls.

**The Universal Cure:** Specify precisely, verify relentlessly, build automated walls.

**Key Insight (Böckeler):** *"Context engineering can make a coding agent more effective. However, as long as LLMs are involved, we can never be certain of anything — still think in probabilities."*

**The Terminology Convergence:** "Vibe coding" vs "agentic engineering" vs "harness engineering" — all describing the same discipline from different angles. The community is converging.

---

### Mitchell Hashimoto — "My AI Adoption Journey" (mitchellh.com, Feb 2026)
