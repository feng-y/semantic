# Coding Conventions

**Analysis Date:** 2026-03-24

## Python Style

### Language Version
- **Python 3.10+** minimum
- Modern typing syntax throughout:
  - Built-in generics: `list[str]`, `dict[str, Any]`
  - Union operator: `str | None`
  - `from __future__ import annotations` in most modules

### Naming
- **snake_case**: functions, variables, modules, filenames
- **PascalCase**: classes
- **UPPER_CASE**: module-level constants

### Code Formatting
- **Ruff** configured in `pyproject.toml`:
  - Target: `py310`
  - Line length: 88
  - Rules: E, F only
  - Ignores: E501 (line too long), F811 (backward compat), F841 (unused vars in tests)

### Import Style
```python
from __future__ import annotations

# Standard library
import json
from pathlib import Path
from typing import Any

# Local imports (relative preferred within package)
from . import artifact_validation
from .host_executor import HostExecutor
```

## Typing Patterns

### Two Modeling Styles

**1. Dataclasses for internal/domain records:**
```python
from dataclasses import dataclass, field

@dataclass(slots=True)
class DemandCardBody:
    issue_id: str
    domains: list[str] = field(default_factory=list)
```

**2. Pydantic for validated semantic artifacts:**
```python
from pydantic import BaseModel, Field, model_validator

class Signal(BaseModel):
    type: Literal["domain", "concept", "rule", "demand_pattern"]
    name: str = Field(..., min_length=1)
    evidence: list[str] = Field(default_factory=list)
```

### Common Patterns
- `Literal[...]` for constrained string values
- `Enum` subclasses of `str` for serialized values
- `field(default_factory=list|dict)` for mutable defaults
- `to_dict()` adapters where serialization needed

## Error Handling

### Structured Status Over Exceptions
Orchestration code returns result dicts with explicit status:
```python
return {
    "command": "discover",
    "status": "ok",  # or "error", "validation_failed", etc.
    "artifacts_written": [...],
}
```

Common statuses:
- `ok`, `error`, `validation_failed`, `execution_unavailable`, `version_skew`, `awaiting_confirmation`

### Exceptions at Boundaries
Validation helpers raise at input boundaries:
```python
# Validation raises
raise FileNotFoundError(f"Prompt not found: {path}")
raise ValueError(f"Invalid YAML: {exc}")
```

### CLI Exit Codes
- `0` on success-like status
- `1` on known failure statuses

## Testing Conventions

### Test Layout
```
tests/
├── test_<module>.py           # Unit tests for src/<module>.py
├── <feature>/                 # Feature-specific tests
│   └── test_<feature>_<aspect>.py
└── e2e/                       # End-to-end tests
    └── test_<capability>_e2e.py
```

### Fixtures
- Heavy use of `tmp_path` and temporary workspaces
- `tests/fake_executors.py` provides deterministic stub executors
- `tests/e2e/conftest.py` has shared e2e fixtures

### Mocking Strategy
```python
from unittest.mock import MagicMock, patch

# Patch at import path
with patch("src.discovery_executor.skill_loader.load_all_skills") as mock:
    mock.return_value = {}
    result = dispatcher.dispatch("discover", temp_repo)
```

### Test Patterns
- Unit tests: pure-function assertions, patched dependencies
- E2E tests: temp repos, subprocess invocation, filesystem assertions
- Fake executors return structurally valid placeholder content

## Documentation Conventions

### Docstrings
- Google-style or simple descriptive strings
- Focus on "why" over "what" for non-obvious logic

### Comments
- `# TODO: <description>` for known work
- `# NOTE: <explanation>` for important context
- Inline comments only when logic is non-obvious

## Configuration Conventions

### pyproject.toml Sections
```toml
[build-system]           # setuptools
[project]                # Package metadata
[project.optional-dependencies]  # test, lint, typecheck
[tool.pytest.ini_options]
[tool.ruff]
[tool.mypy]
```

### Skill Definitions (SKILL.md)
YAML frontmatter with:
```yaml
---
name: skill-name
description: What it does
steps:
  - action: run
    target: prompts/discover/repo-facts.prompt
  - action: augment
    target: prompts/discover/evidence-extraction.prompt
---
```

---

*Conventions analysis: 2026-03-24*
