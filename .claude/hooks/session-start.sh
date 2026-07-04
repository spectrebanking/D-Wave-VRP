#!/bin/bash
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# This project pins dwave-ocean-sdk<5.0.0, whose dependency dimod==0.10.17
# requires numpy==1.21.4 (Python <3.11 only), so Python 3.10 is required.
VENV_DIR=".venv"
if [ ! -d "$VENV_DIR" ]; then
  python3.10 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q

pip install -r requirements.txt -q
# dwave-cloud-client==0.9.5 defines pydantic v1-style models (a `__root__`
# field), which breaks under pydantic v2 pulled in transitively.
pip install "pydantic<2" pytest -q

echo "export PATH=\"$CLAUDE_PROJECT_DIR/$VENV_DIR/bin:\$PATH\"" >> "$CLAUDE_ENV_FILE"
