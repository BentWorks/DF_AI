#!/bin/sh
# Launch the DF_AI MCP server (stdio). Point any MCP client (Claude Code, Codex, Gemini CLI, agent-harness) at this.
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${DFAI_PYTHON:-$HOME/dev/envs/df-ai/bin/python}"
PYTHONPATH="$HERE/src" exec "$PY" -m dfai.server
