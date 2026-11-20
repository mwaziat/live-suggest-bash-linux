#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$HOME/.local/share/bash-live"
BASHRC="$HOME/.bashrc"

rm -rf "$INSTALL_DIR"

if [ -f "$BASHRC" ]; then
    python3 - "$BASHRC" <<'PY'
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

block = '\n# live-suggest-bash-linux\nif [ -f "$HOME/.local/share/bash-live/init.sh" ]; then\n    . "$HOME/.local/share/bash-live/init.sh"\nfi\n'
content = content.replace(block, "\n")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
PY
fi

echo "Uninstalled live-suggest-bash-linux. Open a new terminal tab or restart Bash."
