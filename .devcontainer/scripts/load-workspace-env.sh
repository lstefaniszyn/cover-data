#!/usr/bin/env bash
set -euo pipefail

zshrc="${HOME}/.zshrc"
start_marker="# >>> workspace .env >>>"
end_marker="# <<< workspace .env <<<"

touch "$zshrc"

if ! grep -Fq "$start_marker" "$zshrc"; then
    cat >> "$zshrc" <<'EOF'

# >>> workspace .env >>>
if [ -f /workspaces/app/.env ]; then
    set -a
    . /workspaces/app/.env
    set +a
fi
# <<< workspace .env <<<
EOF
fi
