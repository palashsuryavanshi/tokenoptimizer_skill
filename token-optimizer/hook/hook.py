"""Token Optimizer Hook — Session tracking daemon with threshold warnings."""

import json
import os
import signal
import socket
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

# Windows compatibility for AF_UNIX
try:
    AF_UNIX = socket.AF_UNIX
except AttributeError:
    AF_UNIX = None  # Windows doesn't have AF_UNIX


@dataclass
class Config:
    model_context_windows: Dict[str, int]
    thresholds: List[float]
    stale_turns: int
    hotkey: str
    daemon_socket: str
    session_dir: str

    @classmethod
    def load(cls, path: str) -> "Config":
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        # Custom expanduser that respects HOME env var (Windows compatibility)
        def expand_user(path_str: str) -> str:
            if path_str.startswith("~"):
                home = os.environ.get("HOME") or os.environ.get("USERPROFILE") or os.path.expanduser("~")
                return path_str.replace("~", home, 1)
            return path_str
        
        # Expand user paths
        data["daemon_socket"] = expand_user(data["daemon_socket"])
        data["session_dir"] = expand_user(data["session_dir"])
        
        # Validate thresholds
        for t in data["thresholds"]:
            if not 0.0 <= t <= 1.0:
                raise ValueError(f"Threshold {t} must be between 0.0 and 1.0")
        
        return cls(**data)

    def context_window_for(self, model: str) -> int:
        return self.model_context_windows.get(model, self.model_context_windows.get("default", 128000))


@dataclass
class SessionTracker:
    config: Optional[Config] = None
    model: str = "default"
    context_window: int = 128000
    session_id: str = field(default_factory=lambda: datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:4])
    session_dir: str = "~/.local/share/token-optimizer/sessions/"
    stale_turns: int = 5
    
    # Runtime state
    turn_count: int = 0
    total_input: int = 0
    total_output: int = 0
    _turns: List[Dict[str, Any]] = field(default_factory=list)
    _file_last_seen: Dict[str, int] = field(default_factory=dict)
    _thresholds_crossed: Set[float] = field(default_factory=set)
    _session_file: Optional[Path] = None

    def __post_init__(self):
        if self.config is not None:
            self.stale_turns = self.config.stale_turns
            self.context_window = self.config.context_window_for(self.model)
        self.session_dir = os.path.expanduser(self.session_dir)
        Path(self.session_dir).mkdir(parents=True, exist_ok=True)
        self._session_file = Path(self.session_dir) / f"{self.session_id}.jsonl"

    def log_turn(self, turn: int, input_tokens: int, output_tokens: int, sources: Dict[str, Any]) -> None:
        self.turn_count = turn
        self.total_input += input_tokens
        self.total_output += output_tokens
        
        # Track file last seen turn
        if "files" in sources and isinstance(sources["files"], dict):
            for file_path in sources["files"]:
                self._file_last_seen[file_path] = turn
        
        turn_data = {
            "turn": turn,
            "input": input_tokens,
            "output": output_tokens,
            "sources": sources,
            "timestamp": datetime.now().isoformat()
        }
        self._turns.append(turn_data)
        
        # Persist to JSONL
        if self._session_file:
            with open(self._session_file, "a") as f:
                f.write(json.dumps(turn_data) + "\n")

    def check_thresholds(self, thresholds: List[float]) -> List[float]:
        """Return list of thresholds newly crossed since last check."""
        if self.context_window == 0:
            return []
        
        usage_ratio = (self.total_input + self.total_output) / self.context_window
        newly_crossed = []
        for t in thresholds:
            if t not in self._thresholds_crossed and usage_ratio >= t:
                newly_crossed.append(t)
                self._thresholds_crossed.add(t)
        return newly_crossed

    def stale_files(self) -> List[str]:
        """Return files not seen in the last stale_turns turns."""
        if self.turn_count == 0:
            return []
        stale_turns = self.config.stale_turns if self.config else self.stale_turns
        cutoff = self.turn_count - stale_turns
        return [f for f, last_seen in self._file_last_seen.items() if last_seen <= cutoff]

    def summary(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "model": self.model,
            "context_window": self.context_window,
            "turn_count": self.turn_count,
            "total_input": self.total_input,
            "total_output": self.total_output,
            "total_tokens": self.total_input + self.total_output,
            "usage_ratio": (self.total_input + self.total_output) / self.context_window if self.context_window else 0,
            "thresholds_crossed": sorted(self._thresholds_crossed),
            "stale_files": self.stale_files(),
            "file_last_seen": self._file_last_seen,
            "turns": self._turns,
        }


class Daemon:
    def __init__(self, config: Config):
        self.config = config
        self.socket_path = config.daemon_socket
        self.server_socket: Optional[socket.socket] = None
        self.running = False
        self.tracker: Optional[SessionTracker] = None
        self._lock = threading.Lock()
        self._use_unix = AF_UNIX is not None
        
        # Setup signal handlers (Windows doesn't have SIGTERM/SIGINT the same way)
        if hasattr(signal, 'SIGTERM'):
            signal.signal(signal.SIGTERM, self._signal_handler)
        if hasattr(signal, 'SIGINT'):
            signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        self.stop()

    def start(self):
        # Clean up any stale socket (only for Unix)
        if self._use_unix and os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass
        
        if self._use_unix:
            self.server_socket = socket.socket(AF_UNIX, socket.SOCK_STREAM)
            self.server_socket.bind(self.socket_path)
        else:
            # Windows: use TCP on localhost
            # If socket_path is already a TCP address (set by test), use it directly
            # Otherwise compute port hash from original Unix socket path
            if self.socket_path.startswith("127.0.0.1:") or (":" in self.socket_path and not self.socket_path.startswith("~")):
                parts = self.socket_path.split(":", 1)
                if len(parts) == 2 and "/" not in parts[1] and "\\" not in parts[1]:
                    host, port = parts
                else:
                    import hashlib
                    port_hash = int(hashlib.md5(self.socket_path.encode()).hexdigest(), 16) % 10000 + 20000
                    host, port = "127.0.0.1", port_hash
            else:
                import hashlib
                port_hash = int(hashlib.md5(self.socket_path.encode()).hexdigest(), 16) % 10000 + 20000
                host, port = "127.0.0.1", port_hash
            
            self.socket_path = f"{host}:{port}"
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((host, int(port)))
        
        self.server_socket.listen(5)
        self.running = True
        
        # Start accept loop in background thread
        self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._accept_thread.start()

    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        # Clean up socket file (only for Unix)
        if self._use_unix and os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError:
                pass

    def _accept_loop(self):
        while self.running:
            try:
                client, _ = self.server_socket.accept()
                client.settimeout(5.0)
                threading.Thread(target=self._handle_client, args=(client,), daemon=True).start()
            except OSError:
                if self.running:
                    raise
                break

    def _handle_client(self, client: socket.socket):
        try:
            data = b""
            while True:
                chunk = client.recv(4096)
                if not chunk:
                    break
                data += chunk
                if b"\n" in data:
                    break
            
            if not data:
                return
            
            lines = data.decode("utf-8").strip().split("\n")
            for line in lines:
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    response = self._process_message(msg)
                    if response:
                        client.sendall((json.dumps(response) + "\n").encode("utf-8"))
                except json.JSONDecodeError:
                    client.sendall(b'{"error": "invalid json"}\n')
        except Exception:
            pass
        finally:
            client.close()

    def _process_message(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        msg_type = msg.get("type")
        
        if msg_type == "turn":
            if self.tracker is None:
                model = msg.get("model", "default")
                self.tracker = SessionTracker(
                    config=self.config,
                    model=model,
                    context_window=self.config.context_window_for(model),
                    session_dir=self.config.session_dir
                )
            
            self.tracker.log_turn(
                turn=msg.get("turn", self.tracker.turn_count + 1),
                input_tokens=msg.get("input", 0),
                output_tokens=msg.get("output", 0),
                sources=msg.get("sources", {})
            )
            
            # Check thresholds after logging turn
            if self.config:
                newly_crossed = self.tracker.check_thresholds(self.config.thresholds)
                if newly_crossed:
                    return {"status": "ok", "thresholds_crossed": newly_crossed}
            
            return {"status": "ok"}
        
        elif msg_type == "query":
            action = msg.get("action")
            if self.tracker is None:
                return {"error": "no active session"}
            
            if action == "summary":
                return {"type": "summary", "data": self.tracker.summary()}
            elif action == "stale":
                return {"type": "stale", "files": self.tracker.stale_files()}
            elif action == "thresholds":
                return {"type": "thresholds", "crossed": sorted(self.tracker._thresholds_crossed)}
            else:
                return {"error": f"unknown query action: {action}"}
        
        elif msg_type == "ping":
            return {"status": "pong"}
        
        elif msg_type == "shutdown":
            # Signal the daemon to stop
            threading.Thread(target=self.stop, daemon=True).start()
            return {"status": "ok"}
        
        elif msg_type == "clear":
            # Clear current session
            self.tracker = None
            return {"status": "ok"}
        
        return {"error": f"unknown message type: {msg_type}"}