#!/usr/bin/env python3
"""Token Optimizer Config Scaffold — Generate default config file."""

import argparse
import os
import sys
from pathlib import Path

DEFAULT_CONFIG = """# Token Optimizer Configuration
# See https://github.com/palashsuryavanshi/tokenoptimizer_skill for documentation

model_context_windows:
  claude-3-5-sonnet: 200000
  gpt-4o: 128000
  gpt-4-turbo: 128000
  default: 128000

# Warning thresholds (fractions of context window)
thresholds: [0.6, 0.8, 0.95]

# Turns after which a file is considered "stale"
stale_turns: 5

# Hotkey for TUI (not yet implemented in shell)
hotkey: "C-t"

# Daemon socket (Unix socket on Linux/macOS, TCP on Windows)
daemon_socket: "~/.local/share/token-optimizer/daemon.sock"

# Session storage directory
session_dir: "~/.local/share/token-optimizer/sessions/"
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate default Token Optimizer config")
    parser.add_argument("-o", "--output", help="Output file path")
    parser.add_argument("--force", action="store_true", help="Overwrite existing file")
    
    args = parser.parse_args()
    
    if args.output:
        config_path = Path(args.output).expanduser()
    else:
        config_path = Path(os.environ.get("TOKEN_OPTIMIZER_CONFIG", "~/.config/token-optimizer/config.yaml")).expanduser()
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    if config_path.exists() and not args.force:
        print(f"Config already exists at {config_path}. Use --force to overwrite.")
        return 1
    
    config_path.write_text(DEFAULT_CONFIG)
    print(f"Config written to {config_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())