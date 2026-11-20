#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="$HOME/.local/share/bash-live"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASHRC="$HOME/.bashrc"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: python3 is required but not found." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/live_edit.py" "$INSTALL_DIR/live_edit.py"
cp "$SCRIPT_DIR/init.sh" "$INSTALL_DIR/init.sh"
chmod +x "$INSTALL_DIR/live_edit.py"

MARKER="# live-suggest-bash-linux"
if ! grep -qF "$MARKER" "$BASHRC" 2>/dev/null; then
    cat >> "$BASHRC" <<'EOF'

# live-suggest-bash-linux
if [ -f "$HOME/.local/share/bash-live/init.sh" ]; then
    . "$HOME/.local/share/bash-live/init.sh"
fi
EOF
    echo "Added loader to $BASHRC"
else
    echo "Loader already present in $BASHRC"
fi

echo "Installed to $INSTALL_DIR"
echo "Open a new terminal tab or run: source ~/.bashrc"
