#!/bin/sh
set -eu

repo_url="https://github.com/seungwonme/dtd.page.git"
project_dir="${DTD_PROJECT_DIR:-$HOME/dev/dtd.page}"

if command -v uv >/dev/null 2>&1; then
  uv_bin="$(command -v uv)"
elif test -x /opt/homebrew/bin/uv; then
  uv_bin=/opt/homebrew/bin/uv
else
  /opt/homebrew/bin/brew install uv
  uv_bin=/opt/homebrew/bin/uv
fi

if test -d "$project_dir/.git"; then
  git -C "$project_dir" pull --ff-only
else
  git clone "$repo_url" "$project_dir"
fi

cd "$project_dir"
"$uv_bin" sync
"$uv_bin" run pytest -q
printf '%s\n' "ready: $project_dir"
