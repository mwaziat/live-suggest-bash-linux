# Self-contained live autosuggestion + dropdown list for Bash (zero external packages)

_BASH_LIVE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_bash_live_launch() {
    local ch="$1"
    local tmpfile
    tmpfile=$(mktemp) || return 1

    local initial="${READLINE_LINE}${ch}"
    python3 "$_BASH_LIVE_DIR/live_edit.py" "$initial" "$tmpfile"
    local rc=$?

    local result=""
    if [[ -f "$tmpfile" ]]; then
        result=$(cat "$tmpfile")
        rm -f "$tmpfile"
    fi

    if [[ $rc -eq 0 ]]; then
        READLINE_LINE="$result"
        READLINE_POINT=${#READLINE_LINE}
    else
        READLINE_LINE=""
        READLINE_POINT=0
    fi
}

if [[ $- == *i* ]] && [[ -t 0 ]]; then
    bind -x '"\C-x\C-l": "_bash_live_launch \"\""'
    for _c in a b c d e f g h i j k l m n o p q r s t u v w x y z; do
        eval "_bash_live_key_${_c}() { _bash_live_launch '${_c}'; }"
        bind -x "\"\C-x_${_c}\": \"_bash_live_key_${_c}\""
        bind "\"${_c}\": \"\C-x_${_c}\C-m\""
    done
    _bash_live_key_dot() { _bash_live_launch '.'; }
    _bash_live_key_slash() { _bash_live_launch '/'; }
    bind -x '"\C-x_dot": "_bash_live_key_dot"'
    bind -x '"\C-x_slash": "_bash_live_key_slash"'
    bind '".": "\C-x_dot\C-m"'
    bind '"/": "\C-x_slash\C-m"'
fi
