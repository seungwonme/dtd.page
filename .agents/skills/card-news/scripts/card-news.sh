#!/bin/sh
set -eu

config_dir="${XDG_CONFIG_HOME:-$HOME/.config}/card-news"
config_file="$config_dir/config.env"

usage() {
  printf '%s\n' 'Usage: card-news.sh setup <project-root>'
  printf '%s\n' '       card-news.sh <doctor|templates|extract|compare|render|dry-run|publish|test> [args]'
}

quote_value() {
  escaped="$(printf '%s' "$1" | sed "s/'/'\\\\''/g")"
  printf "'%s'" "$escaped"
}

write_value() {
  printf '%s=' "$1"
  quote_value "$2"
  printf '\n'
}

write_optional() {
  if test -n "$2"; then
    write_value "$1" "$2"
  fi
}

setup_config() {
  if test "$#" -ne 1; then
    usage >&2
    return 2
  fi
  project_root="$(CDPATH= cd -- "$1" 2>/dev/null && pwd)" || {
    printf 'error: project directory not found: %s\n' "$1" >&2
    return 1
  }
  if ! test -x "$project_root/scripts/project.sh"; then
    printf 'error: scripts/project.sh not found or not executable: %s\n' "$project_root" >&2
    return 1
  fi
  if test -f "$config_file"; then
    printf 'exists: %s\n' "$config_file"
    return 0
  fi

  source_file="$project_root/.env.example"
  if test -f "$project_root/.env.local"; then
    source_file="$project_root/.env.local"
  fi
  if ! test -f "$source_file"; then
    printf 'error: no .env.local or .env.example in %s\n' "$project_root" >&2
    return 1
  fi

  set -a
  . "$source_file"
  set +a
  mkdir -p "$config_dir"
  chmod 700 "$config_dir"
  umask 077
  temporary="$config_file.tmp.$$"
  trap 'test ! -e "$temporary" || /bin/rm -f -- "$temporary"' EXIT HUP INT TERM
  {
    write_value CARD_NEWS_PROJECT_ROOT "$project_root"
    write_value CARD_NEWS_DEFAULT_TEMPLATE "${CARD_NEWS_DEFAULT_TEMPLATE:-minimal}"
    write_value DTD_PDF_ROOT "${DTD_PDF_ROOT:-$HOME/Library/Mobile Documents/com~apple~CloudDocs/PDF}"
    write_value DTD_PUBLIC_BASE_URL "${DTD_PUBLIC_BASE_URL:-}"
    write_value DTD_INSTAGRAM_USERNAME "${DTD_INSTAGRAM_USERNAME:-dtd.page}"
    write_value DTD_DISPLAY_NAME "${DTD_DISPLAY_NAME:-DTD}"
    write_value INSTAGRAM_USER_ID "${INSTAGRAM_USER_ID:-}"
    write_value INSTAGRAM_GRAPH_VERSION "${INSTAGRAM_GRAPH_VERSION:-v23.0}"
    write_optional DTD_FONT_PATH "${DTD_FONT_PATH:-}"
    write_optional DTD_PROFILE_IMAGE "${DTD_PROFILE_IMAGE:-}"
  } > "$temporary"
  chmod 600 "$temporary"
  mv "$temporary" "$config_file"
  trap - EXIT HUP INT TERM
  printf 'created: %s\n' "$config_file"
}

load_config() {
  if ! test -f "$config_file"; then
    printf 'error: config not found; run card-news.sh setup <project-root>\n' >&2
    return 1
  fi
  set -a
  . "$config_file"
  set +a
  if test -z "${CARD_NEWS_PROJECT_ROOT:-}" || ! test -x "$CARD_NEWS_PROJECT_ROOT/scripts/project.sh"; then
    printf 'error: CARD_NEWS_PROJECT_ROOT is invalid in %s\n' "$config_file" >&2
    return 1
  fi
}

command_name="${1:-help}"
if test "$#" -gt 0; then
  shift
fi

case "$command_name" in
  setup)
    setup_config "$@"
    ;;
  doctor|templates|extract|compare|render|dry-run|publish|test)
    load_config
    exec "$CARD_NEWS_PROJECT_ROOT/scripts/project.sh" "$command_name" "$@"
    ;;
  help|-h|--help)
    usage
    ;;
  *)
    printf 'error: unknown command: %s\n' "$command_name" >&2
    usage >&2
    exit 2
    ;;
esac
