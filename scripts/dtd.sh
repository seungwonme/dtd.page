#!/bin/sh
set -eu
exec uv run python scripts/dtd.py "$@"
