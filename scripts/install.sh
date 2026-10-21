#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -c 'import sys; assert (3,11) <= sys.version_info < (3,14), "Use Python 3.11–3.13 (3.12 recommended)"'
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv
fi
export PIP_CACHE_DIR="${PIP_CACHE_DIR:-$PWD/.runtime/pip-cache}"
mkdir -p "$PIP_CACHE_DIR"
# Install the smaller CPU wheel first so requirements do not pull CUDA libraries.
if [ "$(uname -s)" = Linux ]; then
  .venv/bin/python -m pip install 'torch==2.8.0' --index-url https://download.pytorch.org/whl/cpu
else
  .venv/bin/python -m pip install 'torch==2.8.0'
fi
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
.venv/bin/python scripts/prepare.py
