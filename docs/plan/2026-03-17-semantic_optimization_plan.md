# Semantic Layer Optimization Plan

**Created**: 2026-03-17
**Status**: Planning
**Priority**: Post-MVP

---

## Current State

✅ **All 5 semantic capabilities implemented and tested:**
1. semantic-signals - Signal extraction from FACT
2. semantic-candidates - Candidate synthesis
3. semantic-recommend - Recommendation with scoring
4. semantic-review - Review decisions and evidence checks
5. semantic-finalize - Final asset generation

**Metrics:**
- 73 tests, all passing
- Complete pipeline: FACT → Semantic Assets
- Deterministic-first implementation

---

## Optimization Priorities

### Phase 1: Critical Improvements (Weeks 1-3)

#### 1. Smart Review Classification ⭐⭐⭐ (Highest Priority)

**Problem:**
- Current review is 1:1 mapping (recommendation → decision)
- No intelligent auto-approval
- All items treated equally

**Solution:**
```python
# Add to apply_review.py
def auto_classify_review(recommendation):
    """
    Auto-approve high-confidence items
    Auto-defer low-priority items
    Flag medium items for human review
    """
    if (recommendation['semantic_validity'] == 'pass' and
        recommendation['priority'] >= 8.0 and
        recommendation['confidence'] == 'high'):
        return 'keep'  # Auto-approve
    elif recommendation['priority'] < 5.0:
        return 'backlog'  # Auto-defer
    else:
        return 'verify_first'  # Needs review
```

**Implementation:**
- Add `--auto-approve` flag to apply_review.py
- Add confidence thresholds configuration
- Test with high/medium/low confidence scenarios

**Expected Impact:**
- Reduce manual review by 80%
- Focus human attention on uncertain cases
- Faster iteration cycles

---

#### 2. Incremental Discovery ⭐⭐⭐ (High Priority)

**Problem:**
- Full scan every time
- Slow for large projects (>10 min)
- Most code unchanged

**Solution:**
```python
# Add to extract_signals.py
def incremental_discover(fact_path, previous_signals_path):
    """
    Only re-analyze changed modules
    Merge with unchanged signals
    """
    # 1. Load previous signals
    previous = load_yaml(previous_signals_path)

    # 2. Detect changes (timestamp or git diff)
    changed_modules = detect_changes(fact_path, previous)

    # 3. Re-analyze only changed parts
    new_signals = extract_signals_for(changed_modules)

    # 4. Merge with unchanged signals
    return merge_signals(previous, new_signals, changed_modules)
```

**Implementation:**
- Add `--incremental` flag to extract_signals.py
- Implement change detection (file timestamps or git diff)
- Implement signal merging logic
- Add tests for incremental updates

**Expected Impact:**
- 10x speedup for small changes
- Lower token costs
- Faster feedback loops

---

#### 3. Validation Mechanism ⭐⭐ (Medium-High Priority)

**Problem:**
- No validation of semantic models
- Don't know if outputs are accurate
- No feedback loop

**Solution:**
```python
# New file: semantic/validate.py
def validate_semantic_assets(domain_map, concept_map, fact_canonical):
    """
    Validate semantic models against facts
    Report inconsistencies
    """
    issues = []

    # Validation 1: Declared modules exist
    for domain in domain_map['domains']:
        for module in domain.get('boundary', {}).get('modules', []):
            if module not in fact_canonical['modules']:
                issues.append({
                    'type': 'missing_module',
                    'domain': domain['name'],
                    'module': module
                })

    # Validation 2: Concept relationships are valid
    concept_names = {c['name'] for c in concept_map['concepts']}
    for concept in concept_map['concepts']:
        for rel in concept.get('relationships', []):
            if rel not in concept_names:
                issues.append({
                    'type': 'invalid_relationship',
                    'concept': concept['name'],
                    'relationship': rel
                })

    return issues
```

**Implementation:**
- Create semantic/validate.py
- Implement basic validation rules
- Integrate into finalize stage
- Add `semantic-validate` command

**Expected Impact:**
- Catch errors early
- Build trust in semantic models
- Enable continuous improvement

---

### Phase 2: Performance & Integration (Weeks 4-8)

#### 4. Caching Layer ⭐⭐

**Problem:**
- Re-analyze unchanged files
- Duplicate work across runs

**Solution:**
```
.semantic-cache/
├── ast_cache/      # Parsed AST results
├── fact_cache/     # Extracted facts
└── analysis_cache/ # Analysis results
```

**Strategy:**
- File unchanged → use cache
- File changed → re-analyze
- Dependency changed → cascade update

**Expected Impact:**
- 5x speedup for repeated runs
- Lower costs

---

#### 5. Integration with Existing Tools ⭐

**Opportunities:**
- LSP servers (symbol info, type info)
- Static analyzers (pylint, mypy, eslint)
- Documentation tools (OpenAPI, JSDoc)

**Implementation:**
- Add `--use-lsp` flag
- Add `--integrate-linters` flag
- Add `semantic-import` command

**Expected Impact:**
- Reduce duplicate work
- Richer semantic models
- Better accuracy

---

#### 6. Multi-Format Output ⭐

**Current:** YAML + Markdown only

**Add:**
- JSON export (machine-readable)
- GraphQL schema (query interface)
- Visualization (architecture diagrams)

**Implementation:**
```bash
semantic-export --format json
semantic-export --format graphql
semantic-visualize --type architecture
```

**Expected Impact:**
- Better tool integration
- Easier consumption
- Visual understanding

---

### Phase 3: Advanced Features (Months 3-6)

#### 7. Distributed Processing

**For very large projects (>100k LOC):**
```
coordinator
  ↓
├─ worker-1: analyze src/auth/
├─ worker-2: analyze src/api/
├─ worker-3: analyze src/db/
└─ worker-4: analyze src/business/
  ↓
aggregator: merge results
```

**Expected Impact:**
- Handle massive codebases
- Parallel processing
- Scalability

---

#### 8. Plugin Architecture

**Enable community extensions:**
```
plugins/
├── extractors/
│   ├── python_extractor.py
│   ├── typescript_extractor.py
│   └── rust_extractor.py
├── analyzers/
│   ├── domain_analyzer.py
│   └── security_analyzer.py
└── exporters/
    ├── json_exporter.py
    └── neo4j_exporter.py
```

**Expected Impact:**
- Language-specific optimizations
- Community contributions
- Extensibility

---

#### 9. Feedback Loop from Usage

**Learn from agent usage:**
```python
# Track what agents query
# Track what agents use
# Track where agents fail

# Analyze patterns
# Identify gaps
# Auto-improve models
```

**Expected Impact:**
- Continuous improvement
- Self-optimizing system
- Better agent performance

---

## Not Recommended (YAGNI)

### ❌ Over-Engineering to Avoid

1. **Microservices architecture** - Current monolith is fine
2. **Complex plugin system** - 5 capabilities are enough
3. **Real-time streaming** - Batch processing works
4. **ML-based optimization** - Deterministic is better
5. **Distributed consensus** - Single-node is sufficient

---

## Decision Framework

**Before implementing any optimization, ask:**

1. **Is there real pain?** - Do we have usage data showing this is a problem?
2. **What's the ROI?** - How much time/cost saved vs. implementation effort?
3. **Does it add complexity?** - Is the benefit worth the maintenance burden?
4. **Can we measure impact?** - How will we know if it worked?

**Golden Rule:** Optimize based on data, not speculation.

---

## Next Steps

### Immediate (Before Optimization)

1. **Deploy to real project** - Use on 1000-5000 LOC codebase
2. **Collect metrics:**
   - Time per stage
   - Token usage
   - Error rates
   - User pain points
3. **Identify bottlenecks** - Where is the real slowness?
4. **Prioritize based on data** - Not guesses

### When to Start Optimization

**Triggers:**
- discover takes >5 minutes on typical project
- Manual review becomes bottleneck (>50% of time)
- Users report specific pain points
- Cost exceeds budget

**Don't optimize if:**
- Current performance is acceptable
- No user complaints
- No clear bottleneck identified

---

## Success Metrics

**Phase 1 Success:**
- [ ] 80% reduction in manual review time
- [ ] 10x speedup for incremental updates
- [ ] <5% validation error rate

**Phase 2 Success:**
- [ ] 5x speedup from caching
- [ ] Integration with 3+ existing tools
- [ ] 3+ export formats supported

**Phase 3 Success:**
- [ ] Handle 100k+ LOC projects
- [ ] 5+ community plugins
- [ ] Self-improving accuracy

---

## References

**Analysis Source:** Deep optimization analysis (2026-03-17)

**Key Insights:**
1. Smart review classification solves biggest bottleneck
2. Incremental discovery solves performance issue
3. Validation enables continuous improvement
4. Don't over-engineer without data

**Principle:** "Premature optimization is the root of all evil" - Donald Knuth

---

## Appendix: Detailed Implementation Specs

### A. Smart Review Classification

**Configuration:**
```yaml
# semantic-review.config.yaml
auto_approve:
  enabled: true
  thresholds:
    high_confidence:
      semantic_validity: pass
      priority_min: 8.0
      confidence: high
      action: keep
    low_priority:
      priority_max: 5.0
      action: backlog
    default:
      action: verify_first
```

**CLI:**
```bash
semantic-review --auto-approve
semantic-review --auto-approve --config custom.yaml
semantic-review --dry-run  # Show what would be auto-approved
```

---

### B. Incremental Discovery

**Change Detection:**
```python
def detect_changes(current_fact, previous_signals):
    """
    Compare timestamps or use git diff
    """
    changed = []

    # Method 1: Timestamp comparison
    for module in current_fact['modules']:
        prev_timestamp = previous_signals.get('metadata', {}).get('module_timestamps', {}).get(module['name'])
        if not prev_timestamp or module['last_modified'] > prev_timestamp:
            changed.append(module['name'])

    # Method 2: Git diff (if available)
    if git_available():
        git_changed = get_changed_files_from_git()
        changed.extend(map_files_to_modules(git_changed))

    return list(set(changed))
```

**Signal Merging:**
```python
def merge_signals(previous, new, changed_modules):
    """
    Keep unchanged signals, replace changed ones
    """
    merged = copy.deepcopy(previous)

    # Remove signals from changed modules
    merged['domain_signals'] = [
        s for s in merged['domain_signals']
        if s.get('source_module') not in changed_modules
    ]

    # Add new signals
    merged['domain_signals'].extend(new['domain_signals'])

    # Update metadata
    merged['metadata']['last_updated'] = datetime.now().isoformat()
    merged['metadata']['incremental'] = True
    merged['metadata']['changed_modules'] = changed_modules

    return merged
```

---

### C. Validation Rules

**Rule Categories:**

1. **Structural Validation:**
   - Declared entities exist
   - References are valid
   - No circular dependencies

2. **Semantic Validation:**
   - Concepts are coherent
   - Relationships make sense
   - Boundaries are clear

3. **Consistency Validation:**
   - No contradictions
   - Naming is consistent
   - Coverage is complete

**Example Rules:**
```python
VALIDATION_RULES = [
    {
        'name': 'module_exists',
        'check': lambda domain, facts: all(
            m in facts['modules']
            for m in domain.get('boundary', {}).get('modules', [])
        ),
        'severity': 'error'
    },
    {
        'name': 'concept_relationships_valid',
        'check': lambda concept, all_concepts: all(
            rel in [c['name'] for c in all_concepts]
            for rel in concept.get('relationships', [])
        ),
        'severity': 'warning'
    },
    {
        'name': 'evidence_refs_exist',
        'check': lambda asset, facts: all(
            ref in facts.get('evidence', [])
            for ref in asset.get('evidence_refs', [])
        ),
        'severity': 'info'
    }
]
```

---

## Version History

- **v1.0** (2026-03-17): Initial optimization plan
- Future versions will track implementation progress

