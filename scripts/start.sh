#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [ ! -x .venv/bin/python ]; then
  echo 'Run bash scripts/install.sh first.' >&2
  exit 1
fi
# One worker owns the in-memory index. SQLite and vectors persist under .runtime/.
exec .venv/bin/python -m uvicorn backend.main:app --host "${POLICYGUARD_HOST:-127.0.0.1}" --port "${POLICYGUARD_PORT:-8000}"
