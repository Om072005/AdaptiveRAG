#!/usr/bin/env bash
# The one check run before every ship and in CI: the no framework rule, lint, format,
# types, unit tests and, once web/ exists, the page check.
set -euo pipefail
cd "$(dirname "$0")/.."

# retrieval, routing and the classifier are written by us: no RAG framework or ML library imports
banned='^[[:space:]]*(from|import)[[:space:]]+(langchain|llama_index|haystack|sklearn|scipy|torch)\b'
for dir in adaptiverag bench; do
  if [ -d "$dir" ] && grep -rnE --include='*.py' "$banned" "$dir"; then
    echo "check failed: framework or ML library import found above" >&2
    exit 1
  fi
done

uv run ruff check .
uv run ruff format --check .
uv run mypy adaptiverag
uv run pytest -q -m "not network"

if [ -f web/package.json ]; then
  (cd web && npm run -s check)
fi

echo "check passed"
