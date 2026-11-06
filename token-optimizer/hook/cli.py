"""Token Optimizer CLI — Command-line interface for daemon, session, and config."""

import argparse
import json
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from hook import Config, Daemon, SessionTracker


# Default paths
DEFAULT_CONFIG = os.path.expanduser("~/.config/token-optimizer/config.yaml")
DEFAULT_SOCKET = os.path.expanduser("~/.local/share/token-optimizer/daemon.sock")
DEFAULT_SESSION_DIR = os.path.expanduser("~/.local/share/token-optimizer/sessions/")


def ensure_dirs() -> None:
    """Ensure config and session directories exist."""
    Path(os.path.dirname(DEFAULT_CONFIG)).mkdir(parents=True, exist_ok=True)
    Path(DEFAULT_SESSION_DIR).mkdir(parents=True, exist_ok=True)
    Path(os.path.dirname(DEFAULT_SOCKET)).mkdir(parents=True, exist_ok=True)


def load_config(config_path: str = DEFAULT_CONFIG) -> Config:
    """Load config from file or create default."""
    ensure_dirs()
    
    if os.path.exists(config_path):
        return Config.load(config_path)
    
    # Create default config
    default_config = Config(
        model_context_windows={
            "claude-3-5-sonnet": 200000,
            "gpt-4o": 128000,
            "default": 128000,
        },
        thresholds=[0.6, 0.8, 0.95],
        stale_turns=5,
        hotkey="C-t",
        daemon_socket=DEFAULT_SOCKET,
        session_dir=DEFAULT_SESSION_DIR,
    )
    save_config(default_config, config_path)
    return default_config


def save_config(config: Config, config_path: str = DEFAULT_CONFIG) -> None:
    """Save config to file."""
    ensure_dirs()
    
    data = {
        "model_context_windows": config.model_context_windows,
        "thresholds": config.thresholds,
        "stale_turns": config.stale_turns,
        "hotkey": config.hotkey,
        "daemon_socket": config.daemon_socket,
        "session_dir": config.session_dir,
    }
    
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False)


def _resolve_daemon_address(config: Config) -> tuple[str, int] | str:
    """Resolve daemon address - returns (host, port) for TCP or path for Unix socket."""
    sock_path = config.daemon_socket
    
    # Check if already a TCP address (host:port format)
    # Must start with IP/hostname and contain exactly one colon for port
    # Windows paths like C:\... have a colon but also backslashes
    is_tcp = False
    if sock_path.startswith("127.0.0.1:"):
        is_tcp = True
    elif ":" in sock_path and not sock_path.startswith("~"):
        # Check if it looks like host:port (no path separators after colon)
        parts = sock_path.split(":", 1)
        if len(parts) == 2 and "/" not in parts[1] and "\\" not in parts[1]:
            is_tcp = True
    
    if is_tcp:
        host, port = sock_path.split(":", 1)
        return host, int(port)
    
    # On Windows, daemon converts Unix socket to TCP
    try:
        import socket as sock_mod
        AF_UNIX = sock_mod.AF_UNIX
        use_unix = True
    except AttributeError:
        use_unix = False
    
    if use_unix:
        return os.path.expanduser(sock_path)
    
    # Windows: compute same port hash as daemon
    import hashlib
    port_hash = int(hashlib.md5(sock_path.encode()).hexdigest(), 16) % 10000 + 20000
    return "127.0.0.1", port_hash


def connect_daemon(config: Config) -> Optional[socket.socket]:
    """Connect to daemon socket."""
    addr = _resolve_daemon_address(config)
    
    try:
        if isinstance(addr, tuple):
            host, port = addr
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.connect((host, port))
        else:
            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.connect(addr)
        client.settimeout(5.0)
        return client
    except Exception as e:
        print(f"Error connecting to daemon: {e}", file=sys.stderr)
        return None


def send_daemon_message(client: socket.socket, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Send message to daemon and get response."""
    try:
        client.sendall((json.dumps(msg) + "\n").encode())
        response = client.recv(8192)
        return json.loads(response.decode())
    except Exception as e:
        print(f"Error communicating with daemon: {e}", file=sys.stderr)
        return None


# --- Daemon Commands ---

def cmd_daemon_start(args: argparse.Namespace) -> int:
    """Start the daemon."""
    config = load_config(args.config)
    
    # Check if already running
    client = connect_daemon(config)
    if client:
        resp = send_daemon_message(client, {"type": "ping"})
        if resp and resp.get("status") == "pong":
            print("Daemon is already running")
            client.close()
            return 0
        client.close()
    
    # Start daemon in background
    daemon = Daemon(config)
    daemon.start()
    
    print(f"Daemon started on {config.daemon_socket}")
    print(f"Session directory: {config.session_dir}")
    print("Press Ctrl+C to stop")
    
    try:
        # Keep running
        while daemon.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping daemon...")
    finally:
        daemon.stop()
        print("Daemon stopped")
    
    return 0


def cmd_daemon_stop(args: argparse.Namespace) -> int:
    """Stop the daemon."""
    config = load_config(args.config)
    client = connect_daemon(config)
    
    if not client:
        print("Daemon is not running")
        return 1
    
    resp = send_daemon_message(client, {"type": "shutdown"})
    client.close()
    
    if resp and resp.get("status") == "ok":
        print("Daemon stopped")
        return 0
    else:
        print("Failed to stop daemon")
        return 1


def cmd_daemon_status(args: argparse.Namespace) -> int:
    """Check daemon status."""
    config = load_config(args.config)
    client = connect_daemon(config)
    
    if not client:
        print("Daemon: STOPPED")
        return 1
    
    resp = send_daemon_message(client, {"type": "ping"})
    client.close()
    
    if resp and resp.get("status") == "pong":
        print("Daemon: RUNNING")
        return 0
    else:
        print("Daemon: UNRESPONSIVE")
        return 1


# --- Session Commands ---

def cmd_session_summary(args: argparse.Namespace) -> int:
    """Show session summary."""
    config = load_config(args.config)
    client = connect_daemon(config)
    
    if not client:
        print("Daemon not running. Start with: token-optimizer daemon start")
        return 1
    
    resp = send_daemon_message(client, {"type": "query", "action": "summary"})
    client.close()
    
    if not resp or resp.get("type") != "summary":
        print("No active session")
        return 1
    
    data = resp.get("data", {})
    total = data.get("total_tokens", 0)
    window = data.get("context_window", 1)
    ratio = data.get("usage_ratio", 0)
    pct = ratio * 100
    
    print(f"Session: {data.get('session_id', 'N/A')}")
    print(f"Model: {data.get('model', 'N/A')}")
    print(f"Turns: {data.get('turn_count', 0)}")
    print(f"Input:  {data.get('total_input', 0):,} tokens")
    print(f"Output: {data.get('total_output', 0):,} tokens")
    print(f"Total:  {total:,} / {window:,} ({pct:.1f}%)")
    
    crossed = data.get("thresholds_crossed", [])
    if crossed:
        print(f"Thresholds crossed: {', '.join(f'{c*100:.0f}%' for c in crossed)}")
    
    stale = data.get("stale_files", [])
    if stale:
        print(f"Stale files ({len(stale)}):")
        for f in stale[:10]:
            print(f"  {f}")
        if len(stale) > 10:
            print(f"  ... and {len(stale) - 10} more")
    
    return 0


def cmd_session_turns(args: argparse.Namespace) -> int:
    """Show turn-by-turn breakdown."""
    config = load_config(args.config)
    client = connect_daemon(config)
    
    if not client:
        print("Daemon not running")
        return 1
    
    resp = send_daemon_message(client, {"type": "query", "action": "summary"})
    client.close()
    
    if not resp or resp.get("type") != "summary":
        print("No active session")
        return 1
    
    data = resp.get("data", {})
    turns = data.get("turns", [])
    
    if not turns:
        print("No turns recorded")
        return 0
    
    print(f"{'Turn':>4} {'Input':>10} {'Output':>10} {'Total':>10}  Sources")
    print("-" * 60)
    
    for turn in turns:
        sources = turn.get("sources", {})
        source_str = ""
        if isinstance(sources, dict):
            parts = []
            for k, v in sources.items():
                if isinstance(v, dict):
                    parts.append(f"{k}:{len(v)}")
                elif isinstance(v, int):
                    parts.append(f"{k}:{v}")
            source_str = ", ".join(parts)
        
        print(f"{turn.get('turn', 0):>4} {turn.get('input', 0):>10,} {turn.get('output', 0):>10,} "
              f"{turn.get('input', 0) + turn.get('output', 0):>10,}  {source_str}")
    
    return 0


def cmd_session_stale(args: argparse.Namespace) -> int:
    """Show stale files."""
    config = load_config(args.config)
    client = connect_daemon(config)
    
    if not client:
        print("Daemon not running")
        return 1
    
    resp = send_daemon_message(client, {"type": "query", "action": "stale"})
    client.close()
    
    if not resp or resp.get("type") != "stale":
        print("No stale files or no active session")
        return 0
    
    files = resp.get("files", [])
    
    if not files:
        print("No stale files")
        return 0
    
    print(f"Stale files ({len(files)}):")
    for f in files:
        print(f"  {f}")
    
    return 0


def cmd_session_list(args: argparse.Namespace) -> int:
    """List all saved sessions."""
    config = load_config(args.config)
    session_dir = Path(os.path.expanduser(config.session_dir))
    
    if not session_dir.exists():
        print("No sessions found")
        return 0
    
    sessions = sorted(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    
    if not sessions:
        print("No sessions found")
        return 0
    
    print(f"{'Session ID':<30} {'Turns':>6} {'Tokens':>12}  Last Modified")
    print("-" * 70)
    
    for session_file in sessions[:args.limit]:
        try:
            lines = session_file.read_text().strip().split("\n")
            if lines:
                last = json.loads(lines[-1])
                turns = len(lines)
                total = last.get("input", 0) + last.get("output", 0)
                ts = last.get("timestamp", "")
                if ts:
                    try:
                        from datetime import datetime
                        dt = datetime.fromisoformat(ts)
                        ts = dt.strftime("%Y-%m-%d %H:%M")
                    except ValueError:
                        pass
                
                print(f"{session_file.stem:<30} {turns:>6} {total:>12,}  {ts}")
        except Exception:
            pass
    
    return 0


def cmd_session_show(args: argparse.Namespace) -> int:
    """Show details of a specific session."""
    config = load_config(args.config)
    session_dir = Path(os.path.expanduser(config.session_dir))
    session_file = session_dir / f"{args.session_id}.jsonl"
    
    if not session_file.exists():
        print(f"Session not found: {args.session_id}")
        return 1
    
    try:
        lines = session_file.read_text().strip().split("\n")
        
        print(f"Session: {args.session_id}")
        print(f"Turns: {len(lines)}")
        print()
        print(f"{'Turn':>4} {'Input':>10} {'Output':>10} {'Total':>10}  Time")
        print("-" * 55)
        
        for line in lines:
            turn = json.loads(line)
            ts = turn.get("timestamp", "")
            if ts:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(ts)
                    ts = dt.strftime("%H:%M:%S")
                except ValueError:
                    pass
            
            print(f"{turn.get('turn', 0):>4} {turn.get('input', 0):>10,} {turn.get('output', 0):>10,} "
                  f"{turn.get('input', 0) + turn.get('output', 0):>10,}  {ts}")
        
        # Summary
        total_input = sum(t.get("input", 0) for t in (json.loads(l) for l in lines))
        total_output = sum(t.get("output", 0) for t in (json.loads(l) for l in lines))
        print(f"\nTotal Input:  {total_input:,}")
        print(f"Total Output: {total_output:,}")
        print(f"Grand Total:  {total_input + total_output:,}")
        
    except Exception as e:
        print(f"Error reading session: {e}")
        return 1
    
    return 0


def cmd_session_clear(args: argparse.Namespace) -> int:
    """Clear current session."""
    config = load_config(args.config)
    client = connect_daemon(config)
    
    if not client:
        print("Daemon not running")
        return 1
    
    resp = send_daemon_message(client, {"type": "clear"})
    client.close()
    
    if resp and resp.get("status") == "ok":
        print("Session cleared")
        return 0
    else:
        print("Failed to clear session")
        return 1


# --- Config Commands ---

def cmd_config_show(args: argparse.Namespace) -> int:
    """Show current configuration."""
    config = load_config(args.config)
    
    print("Model Context Windows:")
    for model, window in config.model_context_windows.items():
        print(f"  {model}: {window:,}")
    
    print(f"\nThresholds: {', '.join(f'{t*100:.0f}%' for t in config.thresholds)}")
    print(f"Stale Turns: {config.stale_turns}")
    print(f"Hotkey: {config.hotkey}")
    print(f"Daemon Socket: {config.daemon_socket}")
    print(f"Session Dir: {config.session_dir}")
    print(f"Config File: {args.config}")
    
    return 0


def cmd_config_set(args: argparse.Namespace) -> int:
    """Set a configuration value."""
    config = load_config(args.config)
    
    if args.key == "thresholds":
        try:
            values = [float(v.strip()) for v in args.value.split(",")]
            for v in values:
                if not 0.0 <= v <= 1.0:
                    print(f"Threshold {v} must be between 0.0 and 1.0")
                    return 1
            config.thresholds = values
        except ValueError:
            print("Thresholds must be comma-separated numbers (e.g., 0.6,0.8,0.95)")
            return 1
    
    elif args.key == "stale_turns":
        try:
            config.stale_turns = int(args.value)
            if config.stale_turns < 1:
                print("stale_turns must be >= 1")
                return 1
        except ValueError:
            print("stale_turns must be an integer")
            return 1
    
    elif args.key == "hotkey":
        config.hotkey = args.value
    
    elif args.key == "daemon_socket":
        config.daemon_socket = args.value
    
    elif args.key == "session_dir":
        config.session_dir = args.value
    
    elif args.key == "model_context_window":
        # Format: model=value
        if "=" not in args.value:
            print("Format: model=value (e.g., claude-3-5-sonnet=200000)")
            return 1
        model, value = args.value.split("=", 1)
        try:
            config.model_context_windows[model] = int(value)
        except ValueError:
            print("Value must be an integer")
            return 1
    
    else:
        print(f"Unknown config key: {args.key}")
        print("Available: thresholds, stale_turns, hotkey, daemon_socket, session_dir, model_context_window")
        return 1
    
    save_config(config, args.config)
    print(f"Updated {args.key}")
    return 0


def cmd_config_reset(args: argparse.Namespace) -> int:
    """Reset configuration to defaults."""
    default_config = Config(
        model_context_windows={
            "claude-3-5-sonnet": 200000,
            "gpt-4o": 128000,
            "default": 128000,
        },
        thresholds=[0.6, 0.8, 0.95],
        stale_turns=5,
        hotkey="C-t",
        daemon_socket=DEFAULT_SOCKET,
        session_dir=DEFAULT_SESSION_DIR,
    )
    save_config(default_config, args.config)
    print("Configuration reset to defaults")
    return 0


# --- TUI Command ---

def cmd_tui(args: argparse.Namespace) -> int:
    """Launch the TUI dashboard."""
    from tui import run_tui
    run_tui(args.config)
    return 0


# --- Main Entry Point ---

def main() -> int:
    parser = argparse.ArgumentParser(
        prog="token-optimizer",
        description="Token Optimizer — Session tracking and token budget management",
    )
    parser.add_argument(
        "-c", "--config",
        default=DEFAULT_CONFIG,
        help=f"Config file path (default: {DEFAULT_CONFIG})",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # Daemon commands
    daemon_parser = subparsers.add_parser("daemon", help="Daemon management")
    daemon_sub = daemon_parser.add_subparsers(dest="daemon_cmd", required=True)
    
    daemon_sub.add_parser("start", help="Start daemon")
    daemon_sub.add_parser("stop", help="Stop daemon")
    daemon_sub.add_parser("status", help="Check daemon status")
    
    # Session commands
    session_parser = subparsers.add_parser("session", help="Session management")
    session_sub = session_parser.add_subparsers(dest="session_cmd", required=True)
    
    session_sub.add_parser("summary", help="Show current session summary")
    session_sub.add_parser("turns", help="Show turn-by-turn breakdown")
    session_sub.add_parser("stale", help="Show stale files")
    
    list_parser = session_sub.add_parser("list", help="List all saved sessions")
    list_parser.add_argument("-n", "--limit", type=int, default=20, help="Max sessions to show")
    
    show_parser = session_sub.add_parser("show", help="Show specific session details")
    show_parser.add_argument("session_id", help="Session ID to show")
    
    session_sub.add_parser("clear", help="Clear current session")
    
    # Config commands
    config_parser = subparsers.add_parser("config", help="Configuration management")
    config_sub = config_parser.add_subparsers(dest="config_cmd", required=True)
    
    config_sub.add_parser("show", help="Show current configuration")
    
    set_parser = config_sub.add_parser("set", help="Set a configuration value")
    set_parser.add_argument("key", help="Config key to set")
    set_parser.add_argument("value", help="Value to set")
    
    config_sub.add_parser("reset", help="Reset to default configuration")
    
    # TUI command
    subparsers.add_parser("tui", help="Launch TUI dashboard")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Route to command handlers
    if args.command == "daemon":
        if args.daemon_cmd == "start":
            return cmd_daemon_start(args)
        elif args.daemon_cmd == "stop":
            return cmd_daemon_stop(args)
        elif args.daemon_cmd == "status":
            return cmd_daemon_status(args)
    
    elif args.command == "session":
        if args.session_cmd == "summary":
            return cmd_session_summary(args)
        elif args.session_cmd == "turns":
            return cmd_session_turns(args)
        elif args.session_cmd == "stale":
            return cmd_session_stale(args)
        elif args.session_cmd == "list":
            return cmd_session_list(args)
        elif args.session_cmd == "show":
            return cmd_session_show(args)
        elif args.session_cmd == "clear":
            return cmd_session_clear(args)
    
    elif args.command == "config":
        if args.config_cmd == "show":
            return cmd_config_show(args)
        elif args.config_cmd == "set":
            return cmd_config_set(args)
        elif args.config_cmd == "reset":
            return cmd_config_reset(args)
    
    elif args.command == "tui":
        return cmd_tui(args)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())