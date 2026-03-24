# Testing

**Analysis Date:** 2026-03-24

## Test Framework

- **pytest 8+** — Test runner
- **unittest.mock** — Mocking (patch, MagicMock)
- **pytest fixtures** — Dependency injection for tests

## Test Organization

```
tests/
├── test_*.py                   # General unit tests
├── fake_executors.py           # Test-only stub executors
├── fixtures/                   # Test fixtures and data
├── semantic/                   # Semantic layer tests
├── demand/                     # Demand pipeline tests
└── e2e/                        # End-to-end integration tests
```

## Test Categories

### Unit Tests
**Location:** `tests/test_*.py`, `tests/semantic/test_*.py`, `tests/demand/test_*.py`

**Characteristics:**
- Pure function or small-module assertions
- Deterministic inputs/outputs
- Patched dependencies
- Validation of exact schema/fields

**Examples:**
- `tests/test_dispatcher.py` — Dispatcher routing logic
- `tests/test_cli_exit_codes.py` — CLI exit code verification
- `tests/semantic/test_build_candidates.py` — Candidate building logic
- `tests/demand/test_map_semantics.py` — Semantic mapping

### E2E Tests
**Location:** `tests/e2e/`

**Characteristics:**
- Temp workspace or temp git repo
- Multiple pipeline stages together
- Filesystem artifacts asserted
- Real subprocess invocation for skills/CLI

**Examples:**
- `tests/e2e/test_commit_extract.py` — Commit extraction pipeline
- `tests/e2e/test_commit_semantic.py` — Commit-semantic pipeline
- `tests/e2e/test_pipeline_e2e.py` — Full pipeline integration

## Key Fixtures

### `tmp_path` (pytest built-in)
Creates temporary directories that are cleaned up after tests.

### `tests/fake_executors.py`
Provides `stub_executor()` function that returns structurally valid placeholder artifacts for deterministic testing without real LLM calls.

### `tests/e2e/conftest.py`
Shared e2e fixtures including:
- Temporary git repository setup
- Git config helpers
- Subprocess runners

## Testing Patterns

### Fake Executors Pattern
```python
from tests.fake_executors import stub_executor

def test_discovery_with_fake_executor(temp_repo):
    def mock_executor(prompt, context, **kwargs):
        return stub_executor(prompt, context, artifact_name="repo-facts")

    result = run_discovery(temp_repo, executor=mock_executor)
    assert result.status == "ok"
```

### Subprocess Testing
```python
import subprocess

def test_cli_exit_code(tmp_path):
    result = subprocess.run(
        ["python", "-m", "src.main", "--root", str(tmp_path), "init"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
```

### Mocking with patch
```python
from unittest.mock import patch

def test_dispatcher_forwards_executor(temp_repo):
    mock_executor = MagicMock(spec=HostExecutor)

    with patch("src.discovery_executor.skill_loader.load_all_skills") as mock:
        mock.return_value = {}
        result = dispatcher.dispatch("discover", temp_repo, executor=mock_executor)

    assert result["command"] == "discover"
```

## Running Tests

### Install Test Dependencies
```bash
pip install -e ".[test]"
```

### Run All Tests
```bash
pytest tests -q
```

### Run Specific Test File
```bash
pytest tests/test_system.py -q
```

### Run E2E Tests
```bash
pytest tests/e2e/ -v
```

### Run with Coverage (if configured)
```bash
pytest tests --cov=src --cov-report=term-missing
```

## CI Configuration

**File:** `.github/workflows/ci.yml`

```yaml
test:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - run: pip install -e ".[test]"
    - run: pytest tests/test_system.py -q
```

## Coverage Gaps

Per `CONCERNS.md`:
- CI only runs `tests/test_system.py` in main test job
- Real LLM-driven discover path is not part of automated regression
- Many semantic tests skip when fixture artifacts are absent

## Best Practices

1. **Use fake executors** for deterministic LLM-free tests
2. **Prefer temp_path** over modifying real files
3. **Patch at import path** for reliable mocking
4. **Assert on status codes** and structured results, not just exceptions
5. **Clean up** in finally blocks or use context managers

---

*Testing analysis: 2026-03-24*
