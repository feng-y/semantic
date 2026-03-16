# Installation Guide

## Prerequisites

- Python 3.10+
- pip
- git

## Install Steps

```bash
# Clone the repository
git clone <repo-url>
cd semantic-harness

# Install with test dependencies
pip install -e ".[test]"
```

This installs the single runtime dependency (`pyyaml`) and test tooling (`pytest`).

## Verify Installation

```bash
# Run the full test suite
pytest

# Expected: 108 passed
```

## Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_system.py -v

# Single test category
pytest tests/test_system.py::TestCat1Determinism -v
```

## Project Structure After Install

```
semantic-harness/
  manifest.yaml        # plugin manifest
  skills/              # skill definitions
  prompts/             # prompt templates
  src/                 # runtime modules
  tests/               # test suite
  docs/fact/       # created by init, holds all artifacts
```

## Common Problems

**`ModuleNotFoundError: yaml`**
Run `pip install pyyaml` or `pip install -e ".[test]"`.

**Tests fail with import errors**
Ensure you installed with `-e` (editable mode) so `src/` is on the Python path.

**`docs/fact/` doesn't exist**
Run the `init` command first. The directory is created during workspace initialization, not at install time.
