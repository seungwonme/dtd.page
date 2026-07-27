#!/bin/sh
set -eu

if command -v uv >/dev/null 2>&1; then
  uv_bin="$(command -v uv)"
elif test -x /opt/homebrew/bin/uv; then
  uv_bin=/opt/homebrew/bin/uv
else
  printf '%s\n' 'error: uv not found' >&2
  exit 127
fi

exec "$uv_bin" run python -m scripts.dtd "$@"
