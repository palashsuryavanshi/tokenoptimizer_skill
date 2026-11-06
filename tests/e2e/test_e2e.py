#!/usr/bin/env python3
"""
E2E Test for Token Optimizer Extension
Runs in a disposable container-like environment (temp directory)
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

import pytest


# Compute real home ONCE at module load time, before any test modifies os.environ
REAL_HOME = Path.home()
TOKEN_OPTIMIZER_EXE = REAL_HOME / "AppData" / "Local" / "Packages" / "PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0" / "LocalCache" / "local-packages" / "Python313" / "Scripts" / "token-optimizer.exe"


class E2ETestEnvironment:
    """Isolated test environment for E2E testing."""
    
    def __init__(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="token-optimizer-e2e-"))
        self.home = self.temp_dir / "home"
        self.home.mkdir()
        
        # Use the installed token-optimizer executable directly (computed at module load)
        self.token_optimizer_exe = TOKEN_OPTIMIZER_EXE
        
        # Set up isolated environment variables - also update os.environ for Config.load
        self.env = os.environ.copy()
        self.env.update({
            "HOME": str(self.home),
            "USERPROFILE": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "XDG_DATA_HOME": str(self.home / ".local" / "share"),
            "PATH": os.environ.get("PATH", ""),
        })
        # Also update the current process environment so Config.load uses the test HOME
        os.environ["HOME"] = str(self.home)
        os.environ["USERPROFILE"] = str(self.home)
        
        # Paths
        self.config_dir = self.home / ".config" / "token-optimizer"
        self.data_dir = self.home / ".local" / "share" / "token-optimizer"
        self.bin_dir = self.home / ".local" / "bin"
        self.config_file = self.config_dir / "config.yaml"
        self.socket_path = self.data_dir / "daemon.sock"
        self.sessions_dir = self.data_dir / "sessions"
        
        self.daemon_process: Optional[subprocess.Popen] = None
        self.daemon_port: Optional[int] = None
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        """Clean up test environment."""
        if self.daemon_process:
            self.daemon_process.terminate()
            try:
                self.daemon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()
        
        # Remove temp directory
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass
    
    def run_cli(self, *args, **kwargs) -> subprocess.CompletedProcess:
        """Run token-optimizer CLI command."""
        cmd = [str(self.token_optimizer_exe), *args]
        return subprocess.run(cmd, capture_output=True, text=True, env=self.env, **kwargs)
    
    def start_daemon(self) -> int:
        """Start daemon in background thread, return port."""
        import hashlib
        import threading
        from hook.cli import save_config
        from hook.hook import Config, Daemon
        
        port_hash = int(hashlib.md5(str(self.socket_path).encode()).hexdigest(), 16) % 10000 + 20000
        self.daemon_port = port_hash
        
        # Load and update config
        config = Config.load(str(self.config_file))
        config.daemon_socket = f"127.0.0.1:{port_hash}"
        save_config(config, str(self.config_file))
        
        # Start daemon in background thread
        self.daemon = Daemon(config)
        self.daemon.start()
        
        # Wait for daemon to be ready
        for _ in range(50):
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(0.5)
                test_sock.connect(("127.0.0.1", self.daemon_port))
                test_sock.close()
                break
            except ConnectionRefusedError:
                time.sleep(0.1)
        else:
            raise RuntimeError(f"Daemon port {self.daemon_port} not accepting connections after 5s")
        
        return port_hash
    
    def stop_daemon(self):
        """Stop daemon."""
        if hasattr(self, 'daemon') and self.daemon:
            self.daemon.stop()
            self.daemon = None
        if hasattr(self, 'daemon_proc') and self.daemon_proc:
            self.daemon_proc.terminate()
            self.daemon_proc.join(timeout=5)
            if self.daemon_proc.is_alive():
                self.daemon_proc.kill()
            self.daemon_proc = None
        if self.daemon_process:
            self.daemon_process.terminate()
            try:
                self.daemon_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.daemon_process.kill()
            self.daemon_process = None
    
    def send_turn(self, turn: int, input_tokens: int, output_tokens: int, sources: dict = None):
        """Send a turn message to daemon via socket."""
        if sources is None:
            sources = {}
        
        msg = json.dumps({
            "type": "turn",
            "turn": turn,
            "input": input_tokens,
            "output": output_tokens,
            "sources": sources,
        }) + "\n"
        
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(("127.0.0.1", self.daemon_port))
        client.sendall(msg.encode())
        response = client.recv(4096)
        client.close()
        
        return json.loads(response.decode())
    
    def query_summary(self) -> dict:
        """Query session summary from daemon."""
        msg = json.dumps({"type": "query", "action": "summary"}) + "\n"
        
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(5.0)
        client.connect(("127.0.0.1", self.daemon_port))
        client.sendall(msg.encode())
        response = client.recv(8192)
        client.close()
        
        return json.loads(response.decode())


@pytest.fixture(scope="function")
def e2e_env():
    """Provide isolated E2E test environment."""
    env = E2ETestEnvironment()
    try:
        yield env
    finally:
        env.cleanup()


class TestE2E:
    """End-to-end tests for Token Optimizer extension."""
    
    def test_install_creates_structure(self, e2e_env):
        """Test that install creates expected directory structure."""
        # Run scaffold config
        result = e2e_env.run_cli("config", "scaffold", "--force")
        assert result.returncode == 0
        assert e2e_env.config_file.exists()
        
        # Check config content
        content = e2e_env.config_file.read_text()
        assert "model_context_windows" in content
        assert "thresholds" in content
        assert "daemon_socket" in content
        assert "session_dir" in content
    
    def test_daemon_start_stop(self, e2e_env):
        """Test daemon starts and stops cleanly."""
        # Scaffold config first
        e2e_env.run_cli("config", "scaffold", "--force")
        
        # Start daemon
        port = e2e_env.start_daemon()
        assert port is not None
        
        # Check status via CLI
        result = e2e_env.run_cli("daemon", "status")
        assert result.returncode == 0
        assert "RUNNING" in result.stdout
        
        # Stop daemon
        e2e_env.stop_daemon()
        
        # Check status again
        result = e2e_env.run_cli("daemon", "status")
        assert result.returncode != 0
        assert "STOPPED" in result.stdout or "UNRESPONSIVE" in result.stdout
    
    def test_session_tracking(self, e2e_env):
        """Test session tracking with multiple turns."""
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.start_daemon()
        
        try:
            # Send turn 1
            resp = e2e_env.send_turn(1, 5000, 2000, {"files": {"a.py": 3000}})
            assert resp.get("status") == "ok"
            
            # Send turn 2
            resp = e2e_env.send_turn(2, 3000, 1500, {"files": {"b.py": 2000}})
            assert resp.get("status") == "ok"
            
            # Query summary
            summary = e2e_env.query_summary()
            assert summary["type"] == "summary"
            data = summary["data"]
            
            assert data["turn_count"] == 2
            assert data["total_input"] == 8000
            assert data["total_output"] == 3500
            assert data["total_tokens"] == 11500
            assert data["model"] == "default"
            assert data["context_window"] == 128000
            
            # Check turns in summary
            turns = data.get("turns", [])
            assert len(turns) == 2
            assert turns[0]["turn"] == 1
            assert turns[1]["turn"] == 2
            
        finally:
            e2e_env.stop_daemon()
    
    def test_threshold_warnings(self, e2e_env):
        """Test threshold crossing warnings."""
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.start_daemon()
        
        try:
            # Send turns to cross 60% threshold (76800 tokens for 128k window)
            # Need ~77k tokens
            e2e_env.send_turn(1, 40000, 10000, {})
            e2e_env.send_turn(2, 40000, 10000, {})
            
            summary = e2e_env.query_summary()
            data = summary["data"]
            
            # Should have crossed 60% (0.6)
            assert 0.6 in data["thresholds_crossed"]
            assert 0.8 not in data["thresholds_crossed"]
            
        finally:
            e2e_env.stop_daemon()
    
    def test_stale_file_detection(self, e2e_env):
        """Test stale file detection."""
        # Set stale_turns to 3 for this test
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.run_cli("config", "set", "stale_turns", "3")
        e2e_env.start_daemon()
        
        try:
            # Turn 1: files a.py and b.py
            e2e_env.send_turn(1, 1000, 500, {"files": {"a.py": 600, "b.py": 400}})
            # Turn 2: only a.py
            e2e_env.send_turn(2, 1000, 500, {"files": {"a.py": 600}})
            # Turn 3: only a.py
            e2e_env.send_turn(3, 1000, 500, {"files": {"a.py": 600}})
            # Turn 4: only a.py (b.py should now be stale with stale_turns=3)
            e2e_env.send_turn(4, 1000, 500, {"files": {"a.py": 600}})
            
            # Query stale files
            msg = json.dumps({"type": "query", "action": "stale"}) + "\n"
            client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client.settimeout(5.0)
            client.connect(("127.0.0.1", e2e_env.daemon_port))
            client.sendall(msg.encode())
            response = client.recv(4096)
            client.close()
            
            stale_resp = json.loads(response.decode())
            assert stale_resp["type"] == "stale"
            assert "b.py" in stale_resp["files"]
            assert "a.py" not in stale_resp["files"]
            
        finally:
            e2e_env.stop_daemon()
    
    def test_session_persistence(self, e2e_env):
        """Test JSONL session file persistence."""
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.start_daemon()
        
        try:
            e2e_env.send_turn(1, 1000, 500, {"files": {"a.py": 600}})
            e2e_env.send_turn(2, 2000, 1000, {"files": {"b.py": 1500}})
            
            # Check session file exists
            session_files = list(e2e_env.sessions_dir.glob("*.jsonl"))
            assert len(session_files) == 1
            
            # Read and verify content
            lines = session_files[0].read_text().strip().split("\n")
            assert len(lines) == 2
            
            turn1 = json.loads(lines[0])
            assert turn1["turn"] == 1
            assert turn1["input"] == 1000
            assert turn1["output"] == 500
            assert turn1["sources"]["files"]["a.py"] == 600
            
            turn2 = json.loads(lines[1])
            assert turn2["turn"] == 2
            assert turn2["input"] == 2000
            assert turn2["sources"]["files"]["b.py"] == 1500
            
        finally:
            e2e_env.stop_daemon()
    
    def test_cli_session_commands(self, e2e_env):
        """Test CLI session subcommands."""
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.start_daemon()
        
        try:
            # Send some turns
            e2e_env.send_turn(1, 5000, 2000, {"files": {"a.py": 3000}})
            e2e_env.send_turn(2, 3000, 1500, {})
            
            # Test session summary - total input should be 8000 (5000 + 3000)
            result = e2e_env.run_cli("session", "summary")
            assert result.returncode == 0
            assert "8,000" in result.stdout or "8000" in result.stdout
            assert "3,500" in result.stdout or "3500" in result.stdout
            
            # Test session turns
            result = e2e_env.run_cli("session", "turns")
            assert result.returncode == 0
            assert "5,000" in result.stdout or "5000" in result.stdout
            assert "3,000" in result.stdout or "3000" in result.stdout
            
            # Test session list
            result = e2e_env.run_cli("session", "list")
            assert result.returncode == 0
            
        finally:
            e2e_env.stop_daemon()
    
    def test_cli_config_commands(self, e2e_env):
        """Test CLI config subcommands."""
        e2e_env.run_cli("config", "scaffold", "--force")
        
        # Show config
        result = e2e_env.run_cli("config", "show")
        assert result.returncode == 0
        assert "Thresholds" in result.stdout
        assert "Stale Turns" in result.stdout
        
        # Set config
        result = e2e_env.run_cli("config", "set", "stale_turns", "10")
        assert result.returncode == 0
        assert "Updated stale_turns" in result.stdout
        
        # Verify change
        result = e2e_env.run_cli("config", "show")
        assert "Stale Turns: 10" in result.stdout
        
        # Reset config
        result = e2e_env.run_cli("config", "reset")
        assert result.returncode == 0
        assert "reset to defaults" in result.stdout.lower()
        
        # Verify reset
        result = e2e_env.run_cli("config", "show")
        assert "Stale Turns: 5" in result.stdout
    
    def test_scan_command(self, e2e_env):
        """Test CI scan command."""
        # Create a test file with verbose patterns
        test_file = e2e_env.temp_dir / "test_verbose.py"
        test_file.write_text("""
# Here is the implementation you requested
def hello():
    # TODO: implement
    print("Hello world")
    
# Sorry for the delay, here are the changes:
def goodbye():
    pass
""")
        
        # Run scan
        result = e2e_env.run_cli("scan", str(test_file), "--severity", "info")
        assert result.returncode == 1  # Violations found
        assert "excessive_explanation" in result.stdout or "apologetic_language" in result.stdout
        
        # Run scan with error severity (should pass if only warnings)
        result = e2e_env.run_cli("scan", str(test_file), "--severity", "error")
        assert result.returncode == 0  # No errors, only warnings
    
    def test_session_clear(self, e2e_env):
        """Test session clear command."""
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.start_daemon()
        
        try:
            # Send turns
            e2e_env.send_turn(1, 5000, 2000, {})
            
            # Verify session exists
            result = e2e_env.run_cli("session", "summary")
            assert result.returncode == 0
            assert "5,000" in result.stdout or "5000" in result.stdout
            
            # Clear session
            result = e2e_env.run_cli("session", "clear")
            assert result.returncode == 0
            assert "cleared" in result.stdout.lower()
            
            # Verify session is gone
            result = e2e_env.run_cli("session", "summary")
            assert result.returncode != 0
            assert "No active session" in result.stdout
            
        finally:
            e2e_env.stop_daemon()
    
    def test_multiple_sessions(self, e2e_env):
        """Test multiple separate sessions create separate JSONL files."""
        e2e_env.run_cli("config", "scaffold", "--force")
        e2e_env.start_daemon()
        
        try:
            # Session 1
            e2e_env.send_turn(1, 1000, 500, {})
            
            # Clear to start new session
            e2e_env.run_cli("session", "clear")
            
            # Session 2
            e2e_env.send_turn(1, 2000, 1000, {})
            
            # Should have 2 session files
            session_files = list(e2e_env.sessions_dir.glob("*.jsonl"))
            assert len(session_files) == 2
            
        finally:
            e2e_env.stop_daemon()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])