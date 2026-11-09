#!/bin/sh
set -eu

skill_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
temporary="$(mktemp -d)"
trap '/bin/rm -rf -- "$temporary"' EXIT HUP INT TERM
project="$temporary/project"
config_home="$temporary/config"
mkdir -p "$project/scripts"

cat > "$project/.env.local" <<'EOF'
DTD_PDF_ROOT="$HOME/PDF"
DTD_PUBLIC_BASE_URL="https://example.invalid"
DTD_INSTAGRAM_USERNAME="dtd.page"
DTD_DISPLAY_NAME="DTD"
INSTAGRAM_USER_ID="public-id"
INSTAGRAM_GRAPH_VERSION="v23.0"
INSTAGRAM_ACCESS_TOKEN="must-not-copy"
EOF

cat > "$project/scripts/project.sh" <<'EOF'
#!/bin/sh
set -eu
printf 'delegated=%s default=%s\n' "$1" "${CARD_NEWS_DEFAULT_TEMPLATE:-missing}"
EOF
chmod +x "$project/scripts/project.sh"

XDG_CONFIG_HOME="$config_home" "$skill_root/scripts/card-news.sh" setup "$project" >/dev/null
config="$config_home/card-news/config.env"
test "$(stat -f '%Lp' "$config")" = "600"
rg -q "CARD_NEWS_DEFAULT_TEMPLATE='minimal'" "$config"
if rg -q 'must-not-copy|INSTAGRAM_ACCESS_TOKEN' "$config"; then
  printf '%s\n' 'secret was copied into config' >&2
  exit 1
fi
output="$(XDG_CONFIG_HOME="$config_home" "$skill_root/scripts/card-news.sh" templates)"
test "$output" = "delegated=templates default=minimal"
printf '%s\n' 'ok: card-news wrapper'
