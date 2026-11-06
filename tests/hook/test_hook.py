import pytest
import tempfile
import os
import json
from pathlib import Path
import socket

# These imports will fail until we implement hook.py
from hook.hook import SessionTracker, Config, Daemon


def write_temp_yaml(content: str) -> str:
    """Write YAML content to a temp file and return the path. Closes file properly for Windows."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(content)
        path = f.name
    return path


def cleanup_temp_file(path: str):
    """Clean up temp file, handling Windows file locking."""
    try:
        os.unlink(path)
    except PermissionError:
        pass  # Windows may still have a handle; ignore


class TestConfig:
    def test_config_loads_defaults(self):
        path = write_temp_yaml("""
model_context_windows:
  claude-3-5-sonnet: 200000
  gpt-4o: 128000
  default: 128000
thresholds: [0.6, 0.8, 0.95]
stale_turns: 5
hotkey: "C-t"
daemon_socket: "~/.local/share/token-optimizer/daemon.sock"
session_dir: "~/.local/share/token-optimizer/sessions/"
""")
        try:
            config = Config.load(path)
            assert config.model_context_windows["claude-3-5-sonnet"] == 200000
            assert config.thresholds == [0.6, 0.8, 0.95]
            assert config.stale_turns == 5
            assert config.hotkey == "C-t"
        finally:
            cleanup_temp_file(path)

    def test_config_validates_thresholds(self):
        path = write_temp_yaml("""
model_context_windows:
  default: 128000
thresholds: [1.5]  # invalid > 1.0
stale_turns: 5
hotkey: "C-t"
daemon_socket: "/tmp/sock"
session_dir: "/tmp/sessions"
""")
        try:
            with pytest.raises(ValueError):
                Config.load(path)
        finally:
            cleanup_temp_file(path)


class TestSessionTracker:
    def test_turn_logging_and_totals(self):
        tracker = SessionTracker(model="claude-3-5-sonnet", context_window=200000)
        tracker.log_turn(1, input_tokens=5000, output_tokens=2000, sources={"files": 3000, "tools": 1000, "conversation": 1000})
        tracker.log_turn(2, input_tokens=6000, output_tokens=1500, sources={"files": 4000, "tools": 500, "conversation": 1000})
        assert tracker.total_input == 11000
        assert tracker.total_output == 3500
        assert tracker.turn_count == 2

    def test_threshold_warnings(self):
        tracker = SessionTracker(model="gpt-4o", context_window=128000)
        # 60% = 76800
        tracker.log_turn(1, input_tokens=40000, output_tokens=10000, sources={})
        tracker.log_turn(2, input_tokens=40000, output_tokens=10000, sources={})
        warnings = tracker.check_thresholds([0.6, 0.8, 0.95])
        assert 0.6 in warnings
        assert 0.8 not in warnings

    def test_stale_file_detection(self):
        tracker = SessionTracker(stale_turns=3)
        tracker.log_turn(1, input_tokens=1000, output_tokens=500, sources={"files": {"a.py": 600, "b.py": 400}})
        tracker.log_turn(2, input_tokens=1000, output_tokens=500, sources={"files": {"a.py": 600}})
        tracker.log_turn(3, input_tokens=1000, output_tokens=500, sources={"files": {"a.py": 600}})
        tracker.log_turn(4, input_tokens=1000, output_tokens=500, sources={"files": {"a.py": 600}})
        stale = tracker.stale_files()
        assert "b.py" in stale
        assert "a.py" not in stale

    def test_jsonl_persistence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = SessionTracker(session_dir=tmpdir, session_id="test-session")
            tracker.log_turn(1, input_tokens=1000, output_tokens=500, sources={"files": {"a.py": 600}})
            tracker.log_turn(2, input_tokens=2000, output_tokens=1000, sources={"files": {"b.py": 1500}})
            
            session_file = Path(tmpdir) / "test-session.jsonl"
            assert session_file.exists()
            lines = session_file.read_text().strip().split('\n')
            assert len(lines) == 2
            turn1 = json.loads(lines[0])
            assert turn1["turn"] == 1
            assert turn1["input"] == 1000
            assert turn1["sources"]["files"]["a.py"] == 600


class TestDaemon:
    def test_daemon_starts_and_stops(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            config = Config(
                model_context_windows={"default": 128000},
                thresholds=[0.6, 0.8],
                stale_turns=5,
                hotkey="C-t",
                daemon_socket=str(socket_path),
                session_dir=tmpdir
            )
            daemon = Daemon(config)
            daemon.start()
            # On Windows, daemon uses TCP so no socket file is created
            # Just verify daemon is running
            assert daemon.running
            daemon.stop()
            assert not daemon.running

    def test_daemon_handles_turn_message(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            socket_path = Path(tmpdir) / "test.sock"
            config = Config(
                model_context_windows={"default": 128000},
                thresholds=[0.6, 0.8],
                stale_turns=5,
                hotkey="C-t",
                daemon_socket=str(socket_path),
                session_dir=tmpdir
            )
            daemon = Daemon(config)
            daemon.start()
            
            # Connect to daemon (TCP on Windows)
            host, port = "127.0.0.1", 0
            if hasattr(daemon, 'socket_path') and ':' in daemon.socket_path:
                host, port_str = daemon.socket_path.split(':')
                port = int(port_str)
            else:
                # Fallback: compute same hash
                import hashlib
                port_hash = int(hashlib.md5(str(socket_path).encode()).hexdigest(), 16) % 10000 + 20000
                host, port = "127.0.0.1", port_hash
            
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect((host, port))
            client.sendall(b'{"type": "turn", "turn": 1, "input": 5000, "output": 2000, "sources": {"files": 3000}}\n')
            
            # Wait for response to ensure message is processed
            response = client.recv(4096)
            assert b'"status": "ok"' in response
            client.close()
            
            daemon.stop()
            
            # Session file should exist with the turn
            session_files = list(Path(tmpdir).glob("*.jsonl"))
            assert len(session_files) == 1