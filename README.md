# live-suggest-bash-linux

Lightweight, zero-dependency **live inline autosuggestion** and **dropdown completion list** for Bash on Linux — built using only **Bash** and **Python 3 standard library** (`termios`, `tty`, `shutil`, `glob`).

No `apt` packages, no `zsh`, no `fish`, and no background daemon required.

## Features

- **Inline ghost-text suggestion** on the right of your cursor as you type.
- **Live dropdown list** (up to 6 matches) rendered directly below the prompt on every keystroke.
- **Multi-source matching:**
  1. Recent commands from `~/.bash_history`
  2. Executable commands in `$PATH`
  3. File & directory path completion for arguments
- **Zero background memory usage:** `live_edit.py` only runs while typing a command and exits immediately on `Enter`, `Esc`, or `Ctrl+C`.

## Requirements

- Linux with **Bash** (interactive shell)
- **Python 3** (standard library only)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/mwaziat/live-suggest-bash-linux.git
cd live-suggest-bash-linux
```

### 2. Run the installer

```bash
chmod +x install.sh
./install.sh
```

### 3. Activate

Open a **new terminal tab** or reload your shell:

```bash
source ~/.bashrc
```

## Keybindings

| Key | Action |
| --- | --- |
| `a-z`, `.`, `/` | Start live suggestion mode and type normally |
| `→` (Right Arrow) | Accept the inline ghost-text suggestion |
| `↓` / `↑` | Navigate the dropdown list below |
| `Tab` | Cycle through the dropdown list and fill the buffer |
| `Backspace` | Delete character before cursor |
| `Ctrl+W` | Delete previous word |
| `Ctrl+U` | Clear entire line |
| `Enter` | Clear dropdown and execute the command in Bash |
| `Esc` / `Ctrl+C` | Cancel and clear the current line |

## Uninstall

```bash
chmod +x uninstall.sh
./uninstall.sh
```

## License

MIT License — see [LICENSE](LICENSE).
