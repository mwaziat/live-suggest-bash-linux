#!/usr/bin/env python3
"""
Lightweight, zero-dependency live autosuggestion + dropdown list editor for Bash.
Shows inline ghost-text on the right and a live completion list below on every keystroke.
"""

import getpass
import glob
import os
import re
import select
import shutil
import socket
import sys
import termios
import tty


MAX_LIST_ITEMS = 6
HIST_FILE = os.path.expanduser("~/.bash_history")


def load_history():
    """Load deduplicated bash history, most recent first."""
    if not os.path.exists(HIST_FILE):
        return []
    try:
        with open(HIST_FILE, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.rstrip("\n") for line in f if line.strip() and not line.startswith("#")]
    except OSError:
        return []
    seen = set()
    recent = []
    for line in reversed(lines):
        if line not in seen:
            seen.add(line)
            recent.append(line)
    return recent


def load_commands():
    """Load executable command names from PATH."""
    cmds = set()
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if not p or not os.path.isdir(p):
            continue
        try:
            for entry in os.scandir(p):
                if not entry.name.startswith("."):
                    cmds.add(entry.name)
        except OSError:
            continue
    return sorted(cmds)


def get_path_completions(token):
    """Return matching files/directories for the current argument token."""
    if not token:
        pattern = "*"
        prefix_dir = ""
    else:
        expanded = os.path.expanduser(token)
        if token.endswith("/"):
            pattern = os.path.join(expanded, "*")
            prefix_dir = token
        else:
            pattern = expanded + "*"
            prefix_dir = os.path.dirname(token)
            if prefix_dir and not prefix_dir.endswith("/"):
                prefix_dir += "/"

    matches = []
    for m in sorted(glob.glob(pattern)):
        name = os.path.basename(m)
        if os.path.isdir(m):
            name += "/"
        matches.append((prefix_dir + name) if prefix_dir else name)
    return matches


def compute_suggestions(buf, history, commands):
    """
    Return (ghost_suffix, list_items) for the current buffer.
    list_items is a list of full-line replacement strings.
    """
    if not buf:
        return "", []

    items = []
    seen = set()

    # 1. History prefix matches (highest priority)
    for h in history:
        if h.startswith(buf) and h != buf and h not in seen:
            seen.add(h)
            items.append(h)
            if len(items) >= MAX_LIST_ITEMS:
                break

    # 2. If single word (command position), match PATH commands
    if " " not in buf:
        for c in commands:
            if c.startswith(buf) and c != buf and c not in seen:
                seen.add(c)
                items.append(c)
                if len(items) >= MAX_LIST_ITEMS:
                    break
    else:
        # 3. Argument position: complete file/directory path on last token
        parts = buf.rsplit(" ", 1)
        head, token = parts[0] + " ", parts[1]
        for path_match in get_path_completions(token):
            full = head + path_match
            if full != buf and full not in seen:
                seen.add(full)
                items.append(full)
                if len(items) >= MAX_LIST_ITEMS:
                    break

    ghost = ""
    if items and items[0].startswith(buf):
        ghost = items[0][len(buf):]

    return ghost, items


def get_cursor_pos(tty_fd):
    """Query current terminal cursor (row, col) 1-based using DSR."""
    os.write(tty_fd, b"\x1b[6n")
    resp = b""
    while True:
        ch = os.read(tty_fd, 1)
        if not ch:
            break
        resp += ch
        if ch == b"R":
            break
    m = re.search(rb"\x1b\[(\d+);(\d+)R", resp)
    if m:
        return int(m.group(1)), int(m.group(2))
    return 1, 1


def read_key(tty_fd):
    """Read a single keypress or escape sequence from tty_fd."""
    b = os.read(tty_fd, 1)
    if not b:
        return None
    if b == b"\x1b":
        r, _, _ = select.select([tty_fd], [], [], 0.03)
        if not r:
            return "ESC"
        seq = os.read(tty_fd, 2)
        if seq == b"[A":
            return "UP"
        if seq == b"[B":
            return "DOWN"
        if seq == b"[C":
            return "RIGHT"
        if seq == b"[D":
            return "LEFT"
        if seq == b"[3":
            os.read(tty_fd, 1)
            return "DEL"
        return "ESC"
    if b in (b"\r", b"\n"):
        return "ENTER"
    if b == b"\t":
        return "TAB"
    if b in (b"\x7f", b"\x08"):
        return "BACKSPACE"
    if b == b"\x03":
        return "CTRL_C"
    if b == b"\x04":
        return "CTRL_D"
    if b == b"\x15":
        return "CTRL_U"
    if b == b"\x17":
        return "CTRL_W"
    try:
        ch = b.decode("utf-8")
        if ch.isprintable():
            return ch
    except UnicodeDecodeError:
        pass
    return None


def build_prompt():
    """Return (colored_prompt, visible_len) matching standard Ubuntu PS1."""
    user = getpass.getuser()
    host = socket.gethostname().split(".")[0]
    cwd = os.getcwd()
    home = os.path.expanduser("~")
    if cwd == home:
        short_cwd = "~"
    elif cwd.startswith(home + "/"):
        short_cwd = "~" + cwd[len(home):]
    else:
        short_cwd = cwd
    plain = f"{user}@{host}:{short_cwd}$ "
    colored = f"\x1b[01;32m{user}@{host}\x1b[00m:\x1b[01;34m{short_cwd}\x1b[00m$ "
    return colored, len(plain)


def render(tty_fd, start_row, prompt_colored, prompt_len, buf, cursor_idx, ghost, items, selected_idx):
    """Render prompt, typed buffer, inline ghost suggestion on right, and dropdown list below."""
    cols, rows = shutil.get_terminal_size((80, 24))
    start_col = prompt_len + 1
    avail_width = max(10, cols - start_col)

    out = [f"\x1b[{start_row};1H\x1b[K{prompt_colored}"]

    visible_buf = buf[:avail_width]
    out.append(visible_buf)

    if ghost and cursor_idx == len(buf):
        rem_width = avail_width - len(visible_buf)
        if rem_width > 0:
            out.append(f"\x1b[90m{ghost[:rem_width]}\x1b[0m")

    out.append("\x1b[J")
    max_rows_below = max(0, rows - start_row)
    show_items = items[: min(len(items), max_rows_below)]

    for i, item in enumerate(show_items):
        row_num = start_row + 1 + i
        display = item[: max(10, cols - 5)]
        if i == selected_idx:
            out.append(f"\x1b[{row_num};1H\x1b[K\x1b[36;1m  > {display}\x1b[0m")
        else:
            out.append(f"\x1b[{row_num};1H\x1b[K\x1b[90m    {display}\x1b[0m")

    cur_col = start_col + cursor_idx
    out.append(f"\x1b[{start_row};{cur_col}H")

    os.write(tty_fd, "".join(out).encode("utf-8", errors="ignore"))


def clear_below_and_finish(tty_fd, start_row):
    """Clear current row and dropdown list so Readline can redraw PS1 cleanly once."""
    out = f"\x1b[{start_row};1H\x1b[K\x1b[J\x1b[{start_row};1H"
    os.write(tty_fd, out.encode("utf-8", errors="ignore"))


def main():
    initial = sys.argv[1] if len(sys.argv) > 1 else ""
    out_file = sys.argv[2] if len(sys.argv) > 2 else ""

    tty_fd = os.open("/dev/tty", os.O_RDWR)
    old_attrs = termios.tcgetattr(tty_fd)

    history = load_history()
    commands = load_commands()
    prompt_colored, prompt_len = build_prompt()

    buf = initial
    cursor_idx = len(buf)
    selected_idx = -1

    try:
        tty.setraw(tty_fd)
        start_row, _ = get_cursor_pos(tty_fd)
        _, rows = shutil.get_terminal_size((80, 24))
        needed_scroll = max(0, (start_row + MAX_LIST_ITEMS) - rows)
        if needed_scroll > 0:
            os.write(tty_fd, (b"\n" * needed_scroll) + f"\x1b[{needed_scroll}A".encode())
            start_row = max(1, start_row - needed_scroll)

        while True:
            ghost, items = compute_suggestions(buf, history, commands)
            if selected_idx >= len(items):
                selected_idx = -1
            if selected_idx >= 0 and items:
                active_item = items[selected_idx]
                ghost = active_item[len(buf):] if active_item.startswith(buf) else ""

            render(tty_fd, start_row, prompt_colored, prompt_len, buf, cursor_idx, ghost, items, selected_idx)
            key = read_key(tty_fd)

            if key is None:
                continue
            if key == "ENTER":
                final_cmd = items[selected_idx] if (0 <= selected_idx < len(items)) else buf
                clear_below_and_finish(tty_fd, start_row)
                if out_file:
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write(final_cmd)
                sys.exit(0)
            elif key in ("CTRL_C", "ESC"):
                clear_below_and_finish(tty_fd, start_row)
                if out_file:
                    with open(out_file, "w", encoding="utf-8") as f:
                        f.write("")
                sys.exit(1)
            elif key == "CTRL_D" and not buf:
                clear_below_and_finish(tty_fd, start_row)
                sys.exit(1)
            elif key == "RIGHT":
                if cursor_idx == len(buf) and ghost:
                    buf += ghost
                    cursor_idx = len(buf)
                    selected_idx = -1
                elif cursor_idx < len(buf):
                    cursor_idx += 1
            elif key == "LEFT":
                if cursor_idx > 0:
                    cursor_idx -= 1
            elif key in ("TAB", "DOWN"):
                if items:
                    selected_idx = (selected_idx + 1) % len(items)
                    if key == "TAB":
                        buf = items[selected_idx]
                        cursor_idx = len(buf)
            elif key == "UP":
                if items and selected_idx > 0:
                    selected_idx -= 1
                elif items and selected_idx == -1:
                    selected_idx = len(items) - 1
            elif key == "BACKSPACE":
                if cursor_idx > 0:
                    buf = buf[: cursor_idx - 1] + buf[cursor_idx:]
                    cursor_idx -= 1
                    selected_idx = -1
            elif key == "CTRL_U":
                buf = ""
                cursor_idx = 0
                selected_idx = -1
            elif key == "CTRL_W":
                left = buf[:cursor_idx].rstrip()
                idx = left.rfind(" ")
                new_left = left[: idx + 1] if idx != -1 else ""
                buf = new_left + buf[cursor_idx:]
                cursor_idx = len(new_left)
                selected_idx = -1
            elif len(key) == 1:
                buf = buf[:cursor_idx] + key + buf[cursor_idx:]
                cursor_idx += 1
                selected_idx = -1
    finally:
        termios.tcsetattr(tty_fd, termios.TCSADRAIN, old_attrs)
        os.close(tty_fd)


if __name__ == "__main__":
    main()
