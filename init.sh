#!/bin/bash
# Init script — Bootstrap development environment for semantic-harness

set -e

echo "=== semantic-harness init ==="

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2 | cut -d'.' -f1,2)
REQUIRED="3.10"
if [ "$(printf '%s\n' "$REQUIRED" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED" ]; then
    echo "Error: Python $REQUIRED+ required, found $PYTHON_VERSION"
    exit 1
fi
echo "Python $PYTHON_VERSION OK"

# Install
echo "Installing..."
pip install -e ".[test]"

# Verify
echo "Verifying installation..."
pytest tests/test_system.py -q --tb=short

# Verify skill loader
echo "Verifying skill loader..."
python3 -c "from src import skill_loader; print('skill_loader OK')"

# Verify dispatcher
echo "Verifying dispatcher..."
python3 -c "from src import dispatcher; print('dispatcher OK')"

echo ""
echo "=== Init complete ==="
echo "Run tests:  pytest tests/test_system.py -q"
echo "Run suite:  pytest"
echo "Skills:     ls skills/"
