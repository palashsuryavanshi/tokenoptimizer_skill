"""Token Optimizer TUI — Textual-based session dashboard."""

import json
import os
import socket
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import (
    Button, DataTable, Footer, Header, Label, RichLog, Static, TabbedContent, TabPane
)
from textual.reactive import reactive
from textual.timer import Timer
from textual import on

from hook import Config, Daemon


class SessionSummary(Static):
    """Display session summary stats."""
    
    session_data: reactive[Optional[Dict[str, Any]]] = reactive(None)
    
    def watch_session_data(self, data: Optional[Dict[str, Any]]) -> None:
        if data is None:
            self.update("No active session")
            return
        
        total = data.get("total_tokens", 0)
        window = data.get("context_window", 1)
        ratio = data.get("usage_ratio", 0)
        
        # Progress bar visualization
        bar_width = 30
        filled = int(bar_width * ratio)
        bar = "█" * filled + "░" * (bar_width - filled)
        pct = ratio * 100
        
        # Color based on usage
        if ratio >= 0.95:
            color = "red"
        elif ratio >= 0.8:
            color = "yellow"
        else:
            color = "green"
        
        lines = [
            f"[bold]Session:[/bold] {data.get('session_id', 'N/A')}",
            f"[bold]Model:[/bold] {data.get('model', 'N/A')}",
            f"[bold]Turns:[/bold] {data.get('turn_count', 0)}",
            f"[bold]Input:[/bold] {data.get('total_input', 0):,} tokens",
            f"[bold]Output:[/bold] {data.get('total_output', 0):,} tokens",
            f"[bold]Total:[/bold] {total:,} / {window:,} ([{color}]{pct:.1f}%[/{color}])",
            f"[{color}]{bar}[/{color}]",
        ]
        
        crossed = data.get("thresholds_crossed", [])
        if crossed:
            lines.append(f"[bold]Thresholds crossed:[/bold] {', '.join(f'{c*100:.0f}%' for c in crossed)}")
        
        stale = data.get("stale_files", [])
        if stale:
            lines.append(f"[bold]Stale files ({len(stale)}):[/bold] {', '.join(stale[:5])}{'...' if len(stale) > 5 else ''}")
        
        self.update("\n".join(lines))


class TurnsTable(DataTable):
    """Display turn-by-turn breakdown."""
    
    turns_data: reactive[List[Dict[str, Any]]] = reactive([])
    
    def watch_turns_data(self, turns: List[Dict[str, Any]]) -> None:
        self.clear(columns=True)
        self.add_columns("Turn", "Input", "Output", "Total", "Sources", "Time")
        
        for turn in turns:
            sources = turn.get("sources", {})
            source_str = ""
            if isinstance(sources, dict):
                parts = []
                for k, v in sources.items():
                    if isinstance(v, dict):
                        parts.append(f"{k}:{len(v)} files")
                    elif isinstance(v, int):
                        parts.append(f"{k}:{v}")
                source_str = ", ".join(parts)
            
            ts = turn.get("timestamp", "")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    ts = dt.strftime("%H:%M:%S")
                except ValueError:
                    pass
            
            self.add_row(
                str(turn.get("turn", "")),
                f"{turn.get('input', 0):,}",
                f"{turn.get('output', 0):,}",
                f"{turn.get('input', 0) + turn.get('output', 0):,}",
                source_str,
                ts,
            )


class StaleFilesTable(DataTable):
    """Display stale files with last-seen turn."""
    
    stale_data: reactive[List[Dict[str, Any]]] = reactive([])
    
    def watch_stale_data(self, data: List[Dict[str, Any]]) -> None:
        self.clear(columns=True)
        self.add_columns("File", "Last Seen", "Turns Ago")
        
        current_turn = data[0].get("current_turn", 0) if data else 0
        
        for item in data:
            turns_ago = current_turn - item.get("last_seen", 0)
            self.add_row(
                item.get("file", ""),
                str(item.get("last_seen", "")),
                str(turns_ago),
            )


class TokenOptimizerTUI(App):
    """Main TUI application."""
    
    CSS = """
    Screen {
        background: $surface;
    }
    
    #summary {
        border: solid $primary;
        padding: 1;
        height: 16;
        margin: 1;
    }
    
    #turns-table, #stale-table {
        height: 1fr;
        margin: 1;
    }
    
    .tab-content {
        padding: 1;
    }
    
    Button {
        margin: 1;
    }
    
    #controls {
        dock: bottom;
        height: 5;
        padding: 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("c", "clear", "Clear Session"),
        ("d", "toggle_daemon", "Daemon"),
    ]
    
    config: Optional[Config] = None
    daemon: Optional[Daemon] = None
    daemon_client: Optional[socket.socket] = None
    refresh_timer: Optional[Timer] = None
    current_session_id: Optional[str] = None
    
    def __init__(self, config_path: Optional[str] = None):
        super().__init__()
        self.config_path = config_path or os.path.expanduser(
            "~/.config/token-optimizer/config.yaml"
        )
        self.load_config()
    
    def load_config(self) -> None:
        try:
            self.config = Config.load(self.config_path)
        except Exception:
            # Create default config
            self.config = Config(
                model_context_windows={"default": 128000},
                thresholds=[0.6, 0.8, 0.95],
                stale_turns=5,
                hotkey="C-t",
                daemon_socket="~/.local/share/token-optimizer/daemon.sock",
                session_dir="~/.local/share/token-optimizer/sessions/",
            )
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        
        with TabbedContent():
            with TabPane("Dashboard", id="tab-dashboard"):
                with Vertical():
                    yield SessionSummary(id="summary")
                    with Horizontal():
                        yield TurnsTable(id="turns-table")
                        yield StaleFilesTable(id="stale-table")
            
            with TabPane("Sessions", id="tab-sessions"):
                yield RichLog(id="sessions-log", markup=True)
            
            with TabPane("Config", id="tab-config"):
                yield RichLog(id="config-log", markup=True)
        
        with Horizontal(id="controls"):
            yield Button("Refresh (R)", id="btn-refresh", variant="primary")
            yield Button("Clear Session (C)", id="btn-clear", variant="warning")
            yield Button("Toggle Daemon (D)", id="btn-daemon", variant="success")
            yield Button("Quit (Q)", id="btn-quit", variant="error")
        
        yield Footer()
    
    def on_mount(self) -> None:
        self.connect_daemon()
        self.refresh_data()
        self.refresh_timer = self.set_interval(2.0, self.refresh_data)
        
        # Load sessions list
        self.load_sessions_list()
        self.load_config_display()
    
    def _resolve_daemon_address(self) -> tuple[str, int] | str:
        """Resolve daemon address - returns (host, port) for TCP or path for Unix socket."""
        if not self.config:
            return ""
        
        sock_path = self.config.daemon_socket
        
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

    def connect_daemon(self) -> None:
        """Connect to the daemon socket."""
        if not self.config:
            return
        
        addr = self._resolve_daemon_address()
        try:
            if isinstance(addr, tuple):
                host, port = addr
                self.daemon_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.daemon_client.connect((host, port))
            else:
                self.daemon_client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.daemon_client.connect(addr)
            self.daemon_client.settimeout(2.0)
        except Exception:
            self.daemon_client = None
    
    def send_daemon_query(self, action: str) -> Optional[Dict[str, Any]]:
        """Send query to daemon and return response."""
        if not self.daemon_client:
            self.connect_daemon()
            if not self.daemon_client:
                return None
        
        try:
            msg = json.dumps({"type": "query", "action": action}) + "\n"
            self.daemon_client.sendall(msg.encode())
            response = self.daemon_client.recv(8192)
            return json.loads(response.decode())
        except Exception:
            self.daemon_client = None
            return None
    
    def refresh_data(self) -> None:
        """Refresh all data from daemon."""
        if not self.config:
            return
        
        # Query summary
        resp = self.send_daemon_query("summary")
        if resp and resp.get("type") == "summary":
            data = resp.get("data", {})
            self.current_session_id = data.get("session_id")
            self.query_one("#summary", SessionSummary).session_data = data
            
            # Update turns table
            turns = data.get("turns", [])
            self.query_one("#turns-table", TurnsTable).turns_data = turns
            
            # Update stale files
            stale_files = data.get("stale_files", [])
            file_last_seen = data.get("file_last_seen", {})
            current_turn = data.get("turn_count", 0)
            stale_data = [
                {"file": f, "last_seen": file_last_seen.get(f, 0), "current_turn": current_turn}
                for f in stale_files
            ]
            self.query_one("#stale-table", StaleFilesTable).stale_data = stale_data
    
    def load_sessions_list(self) -> None:
        """Load and display sessions list."""
        if not self.config:
            return
        
        session_dir = Path(os.path.expanduser(self.config.session_dir))
        if not session_dir.exists():
            return
        
        log = self.query_one("#sessions-log", RichLog)
        log.clear()
        
        sessions = sorted(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
        
        for session_file in sessions[:20]:  # Show last 20
            try:
                lines = session_file.read_text().strip().split("\n")
                if lines:
                    last = json.loads(lines[-1])
                    turns = len(lines)
                    total = last.get("input", 0) + last.get("output", 0)
                    ts = last.get("timestamp", "")
                    if ts:
                        try:
                            dt = datetime.fromisoformat(ts)
                            ts = dt.strftime("%Y-%m-%d %H:%M")
                        except ValueError:
                            pass
                    
                    log.write(
                        f"[bold]{session_file.stem}[/bold] — "
                        f"{turns} turns, {total:,} tokens — {ts}"
                    )
            except Exception:
                pass
    
    def load_config_display(self) -> None:
        """Display current config."""
        if not self.config:
            return
        
        log = self.query_one("#config-log", RichLog)
        log.clear()
        
        log.write("[bold]Model Context Windows:[/bold]")
        for model, window in self.config.model_context_windows.items():
            log.write(f"  {model}: {window:,}")
        
        log.write("\n[bold]Thresholds:[/bold]")
        for t in self.config.thresholds:
            log.write(f"  {t*100:.0f}%")
        
        log.write(f"\n[bold]Stale Turns:[/bold] {self.config.stale_turns}")
        log.write(f"[bold]Hotkey:[/bold] {self.config.hotkey}")
        log.write(f"[bold]Daemon Socket:[/bold] {self.config.daemon_socket}")
        log.write(f"[bold]Session Dir:[/bold] {self.config.session_dir}")
    
    @on(Button.Pressed, "#btn-refresh")
    def on_refresh(self) -> None:
        self.refresh_data()
        self.load_sessions_list()
    
    @on(Button.Pressed, "#btn-clear")
    def on_clear(self) -> None:
        # Send clear session message
        if self.daemon_client:
            try:
                msg = json.dumps({"type": "clear"}) + "\n"
                self.daemon_client.sendall(msg.encode())
            except Exception:
                pass
        self.refresh_data()
    
    @on(Button.Pressed, "#btn-daemon")
    def on_toggle_daemon(self) -> None:
        # This would toggle the daemon - for now just reconnect
        self.daemon_client = None
        self.connect_daemon()
        self.notify("Daemon connection reset")
    
    @on(Button.Pressed, "#btn-quit")
    def on_quit(self) -> None:
        self.action_quit()
    
    def action_refresh(self) -> None:
        self.refresh_data()
    
    def action_clear(self) -> None:
        self.on_clear()
    
    def action_toggle_daemon(self) -> None:
        self.on_toggle_daemon()
    
    def on_unmount(self) -> None:
        if self.refresh_timer:
            self.refresh_timer.stop()
        if self.daemon_client:
            try:
                self.daemon_client.close()
            except Exception:
                pass


def run_tui(config_path: Optional[str] = None) -> None:
    """Entry point for TUI."""
    app = TokenOptimizerTUI(config_path)
    app.run()


if __name__ == "__main__":
    run_tui()