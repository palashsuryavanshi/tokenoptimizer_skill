#!/usr/bin/env bash
# Token Optimizer Shell Shim — bash/zsh
# Source this in your .bashrc or .zshrc to enable token tracking

# Configuration
: "${TOKEN_OPTIMIZER_SOCKET:=${HOME}/.local/share/token-optimizer/daemon.sock}"
: "${TOKEN_OPTIMIZER_ESTIMATOR:=python3 -c \"import sys; print(len(sys.stdin.read()) // 4)\"}"
: "${TOKEN_OPTIMIZER_DAEMON_CMD:=token-optimizer daemon start}"

# Internal state
_TOKEN_OPTIMIZER_TURN=0
_TOKEN_OPTIMIZER_SESSION_ID=""

# Estimate tokens from stdin (chars/4 heuristic)
_token_optimizer_estimate() {
    local text="$1"
    local estimator="${TOKEN_OPTIMIZER_ESTIMATOR}"
    if [[ -n "$text" ]]; then
        printf "%s" "$text" | eval "$estimator"
    else
        echo 0
    fi
}

# Send message to daemon via netcat/socat
_token_optimizer_send() {
    local msg="$1"
    local sock="${TOKEN_OPTIMIZER_SOCKET}"
    
    # Try different socket tools
    if command -v nc >/dev/null 2>&1; then
        printf "%s\n" "$msg" | nc -U "$sock" 2>/dev/null || true
    elif command -v socat >/dev/null 2>&1; then
        printf "%s\n" "$msg" | socat - "UNIX-CONNECT:$sock" 2>/dev/null || true
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "
import socket, sys, json
sock = '$sock'
msg = '''$msg'''
try:
    if sock.startswith('127.0.0.1:'):
        host, port = sock.split(':')
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((host, int(port)))
    else:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(sock)
    s.sendall((msg + '\n').encode())
    s.settimeout(2.0)
    resp = s.recv(4096)
    sys.stdout.write(resp.decode())
    s.close()
except Exception:
    pass
" 2>/dev/null || true
    fi
}

# Check if command is an agent we should wrap
_token_optimizer_is_agent() {
    local cmd="$1"
    case "$cmd" in
        opencode|claude|codex|aider|gemini)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# Main wrapper function
wrap_agent() {
    # If not an agent command, run directly
    if [[ $# -eq 0 ]] || ! _token_optimizer_is_agent "$1"; then
        command "$@"
        return $?
    fi
    
    local agent_cmd="$1"
    shift
    
    # Ensure daemon is running
    if ! pgrep -f "token-optimizer daemon" >/dev/null 2>&1; then
        eval "$TOKEN_OPTIMIZER_DAEMON_CMD" >/dev/null 2>&1 &
        sleep 0.5
    fi
    
    # Increment turn counter
    _TOKEN_OPTIMIZER_TURN=$((_TOKEN_OPTIMIZER_TURN + 1))
    
    # Estimate input tokens from command + args + env
    local input_text="${agent_cmd} $*"
    local input_tokens=$(_token_optimizer_estimate "$input_text")
    
    # Add environment size (rough estimate)
    local env_size=$(env | wc -c)
    input_tokens=$((input_tokens + env_size / 4))
    
    # Send turn start to daemon (with sources placeholder)
    local turn_msg=$(printf '{"type": "turn", "turn": %d, "input": %d, "output": 0, "sources": {"conversation": %d}}' \
        "$_TOKEN_OPTIMIZER_TURN" "$input_tokens" "$input_tokens")
    _token_optimizer_send "$turn_msg" >/dev/null
    
    # Run the actual command, capture output
    local output
    output=$("$agent_cmd" "$@" 2>&1)
    local exit_code=$?
    
    # Estimate output tokens
    local output_tokens=$(_token_optimizer_estimate "$output")
    
    # Send turn completion with output tokens
    local complete_msg=$(printf '{"type": "turn", "turn": %d, "input": 0, "output": %d, "sources": {}}' \
        "$_TOKEN_OPTIMIZER_TURN" "$output_tokens")
    local daemon_resp=$(_token_optimizer_send "$complete_msg")
    
    # Print daemon warnings if any
    if [[ -n "$daemon_resp" ]] && [[ "$daemon_resp" != '{"status": "ok"}' ]]; then
        echo "$daemon_resp" | grep -o '"warning":"[^"]*"' | cut -d'"' -f4 | while read -r warn; do
            printf '\033[33m[TOKEN WARNING]\033[0m %s\n' "$warn" >&2
        done
    fi
    
    # Print the actual command output
    printf "%s\n" "$output"
    
    return $exit_code
}

# Alias common agents
alias opencode='wrap_agent opencode'
alias claude='wrap_agent claude'
alias codex='wrap_agent codex'
alias aider='wrap_agent aider'
alias gemini='wrap_agent gemini'

# Manual daemon control
token_optimizer_daemon_start() {
    eval "$TOKEN_OPTIMIZER_DAEMON_CMD" &
}

token_optimizer_daemon_stop() {
    pkill -f "token-optimizer daemon" 2>/dev/null || true
}

token_optimizer_daemon_status() {
    if pgrep -f "token-optimizer daemon" >/dev/null 2>&1; then
        echo "running"
    else
        echo "stopped"
    fi
}

# TUI trigger
token_optimizer_tui() {
    token-optimizer session summary
}