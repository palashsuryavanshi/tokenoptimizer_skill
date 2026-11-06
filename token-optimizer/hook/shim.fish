# Token Optimizer Shell Shim — fish
# Source this in your config.fish to enable token tracking

# Configuration
set -gx TOKEN_OPTIMIZER_SOCKET $HOME/.local/share/token-optimizer/daemon.sock
set -gx TOKEN_OPTIMIZER_ESTIMATOR "python3 -c 'import sys; print(len(sys.stdin.read()) // 4)'"
set -gx TOKEN_OPTIMIZER_DAEMON_CMD "token-optimizer daemon start"

# Internal state
set -g _TOKEN_OPTIMIZER_TURN 0

# Estimate tokens from stdin (chars/4 heuristic)
function _token_optimizer_estimate
    set text $argv[1]
    set estimator $TOKEN_OPTIMIZER_ESTIMATOR
    if test -n "$text"
        printf "%s" "$text" | eval $estimator
    else
        echo 0
    end
end

# Send message to daemon
function _token_optimizer_send
    set msg $argv[1]
    set sock $TOKEN_OPTIMIZER_SOCKET
    
    if command -v nc >/dev/null 2>&1
        printf "%s\n" "$msg" | nc -U "$sock" 2>/dev/null; or true
    else if command -v socat >/dev/null 2>&1
        printf "%s\n" "$msg" | socat - "UNIX-CONNECT:$sock" 2>/dev/null; or true
    else if command -v python3 >/dev/null 2>&1
        python3 -c "
import socket, sys
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
" 2>/dev/null; or true
    end
end
end

# Check if command is an agent we should wrap
function _token_optimizer_is_agent
    set cmd $argv[1]
    switch $cmd
        case opencode claude codex aider gemini
            return 0
        case '*'
            return 1
    end
end

# Main wrapper function
function wrap_agent
    if test (count $argv) -eq 0; or not _token_optimizer_is_agent $argv[1]
        command $argv
        return $status
    end
    
    set agent_cmd $argv[1]
    set args $argv[2..-1]
    
    # Ensure daemon is running
    if not pgrep -f "token-optimizer daemon" >/dev/null 2>&1
        eval $TOKEN_OPTIMIZER_DAEMON_CMD >/dev/null 2>&1 &
        sleep 0.5
    end
    
    # Increment turn counter
    set -g _TOKEN_OPTIMIZER_TURN (math $_TOKEN_OPTIMIZER_TURN + 1)
    
    # Estimate input tokens
    set input_text "$agent_cmd $args"
    set input_tokens (_token_optimizer_estimate "$input_text")
    
    # Add environment size
    set env_size (env | wc -c)
    set input_tokens (math $input_tokens + $env_size / 4)
    
    # Send turn start to daemon
    set turn_msg (printf '{"type": "turn", "turn": %d, "input": %d, "output": 0, "sources": {"conversation": %d}}' \
        $_TOKEN_OPTIMIZER_TURN $input_tokens $input_tokens)
    _token_optimizer_send "$turn_msg" >/dev/null
    
    # Run the actual command
    set output ($agent_cmd $args 2>&1 | psub)
    set exit_code $status
    
    # Estimate output tokens
    set output_tokens (_token_optimizer_estimate "$output")
    
    # Send turn completion
    set complete_msg (printf '{"type": "turn", "turn": %d, "input": 0, "output": %d, "sources": {}}' \
        $_TOKEN_OPTIMIZER_TURN $output_tokens)
    set daemon_resp (_token_optimizer_send "$complete_msg")
    
    # Print daemon warnings if any
    if test -n "$daemon_resp"; and test "$daemon_resp" != '{"status": "ok"}'
        echo "$daemon_resp" | grep -o '"warning":"[^"]*"' | cut -d'"' -f4 | while read warn
            printf '\033[33m[TOKEN WARNING]\033[0m %s\n' "$warn" >&2
        end
    end
    
    # Print output
    printf "%s\n" "$output"
    
    return $exit_code
end

# Alias common agents
alias opencode="wrap_agent opencode"
alias claude="wrap_agent claude"
alias codex="wrap_agent codex"
alias aider="wrap_agent aider"
alias gemini="wrap_agent gemini"

# Manual daemon control
function token_optimizer_daemon_start
    eval $TOKEN_OPTIMIZER_DAEMON_CMD &
end

function token_optimizer_daemon_stop
    pkill -f "token-optimizer daemon" 2>/dev/null; or true
end

function token_optimizer_daemon_status
    if pgrep -f "token-optimizer daemon" >/dev/null 2>&1
        echo "running"
    else
        echo "stopped"
    end
end

# TUI trigger
function token_optimizer_tui
    token-optimizer session summary
end