# Token Optimizer Extension

> Session tracking daemon + shell shims + CI token gate for AI coding agents

The core [`token-optimizer` skill](https://github.com/palashsuryavanshi/tokenoptimizer_skill/blob/main/.opencode/skill/token_optimizer.md) (590 words, portable Markdown) reduces token usage by ~25% with blind quality gates. This extension adds:

- **Daemon** (`hook.py`) — Session tracking, threshold warnings, stale file detection, JSONL persistence
- **Shell shims** (`shim.sh`, `shim.fish`) — Wrap `opencode`, `claude`, `codex`, `aider`, `gemini` to auto-report token usage
- **TUI dashboard** (`tui.py`) — Real-time session view with turn breakdown and stale files
- **CLI** (`token-optimizer`) — `daemon`, `session`, `config`, `scan`, `tui` subcommands
- **CI gate** (`scan.py`) — Scans PRs for verbose patterns that waste tokens

---

## Quick Start

```bash
# One-line install (Linux/macOS/WSL)
curl -fsSL https://raw.githubusercontent.com/palashsuryavanshi/tokenoptimizer_skill/main/install.sh | bash

# Restart shell
exec $SHELL

# Start daemon
token-optimizer daemon start

# Use wrapped agents (auto-reports token usage)
opencode "refactor the billing module"
claude "add tests for auth"
codex "optimize database queries"

# View session
token-optimizer session summary

# Launch TUI dashboard
token-optimizer tui
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        User Shell                           │
│  opencode | claude | codex | aider | gemini (aliased)       │
└──────────────────────────┬──────────────────────────────────┘
                           │ wrap_agent() estimates tokens
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Unix Socket / TCP                        │
│  {type:"turn", turn:1, input:5000, output:2000, ...}       │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      token-optimizer daemon                 │
│  • SessionTracker: turns, tokens, sources, thresholds       │
│  • JSONL persistence: ~/.local/share/token-optimizer/sessions/
│  • Threshold warnings at 60%, 80%, 95% context window       │
│  • Stale file detection (not seen in last N turns)          │
└──────────────────────────┬──────────────────────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
    │ token-optimizer    │ token-optimizer │ GitHub Action │
    │ session     │ │ scan        │ │ (CI gate)   │
    │ summary   │ │ --severity  │ │ .github/    │
    │ tui       │ │ warning     │ │ workflows   │
    └─────────────┘ └─────────────┘ └─────────────┘
```

---

## Commands Reference

### Daemon Management
```bash
token-optimizer daemon start      # Start background daemon
token-optimizer daemon stop       # Stop daemon
token-optimizer daemon status     # Check if running
```

### Session Inspection
```bash
token-optimizer session summary   # Current session totals + thresholds
token-optimizer session turns     # Turn-by-turn breakdown
token-optimizer session stale     # Files not seen in last N turns
token-optimizer session list      # All saved sessions
token-optimizer session show ID   # Full session details
token-optimizer session clear     # Reset current session
```

### Configuration
```bash
token-optimizer config show       # View current settings
token-optimizer config set KEY VALUE
token-optimizer config reset      # Restore defaults
token-optimizer config scaffold   # Generate default config.yaml
```

Config keys:
| Key | Example |
|-----|---------|
| `thresholds` | `0.6,0.8,0.95` |
| `stale_turns` | `5` |
| `hotkey` | `C-t` |
| `daemon_socket` | `~/.local/share/token-optimizer/daemon.sock` |
| `session_dir` | `~/.local/share/token-optimizer/sessions/` |
| `model_context_window` | `claude-3-5-sonnet=200000` |

### CI Gate (Token Scan)
```bash
# Scan for verbose patterns
token-optimizer scan                    # Current dir, warning+
token-optimizer scan --severity error  # Only errors
token-optimizer scan --output json     # Machine-readable
token-optimizer scan --output github   # GitHub Actions annotations
```

Patterns detected:
- Explanatory preambles ("Here is the code...", "Below are the changes...")
- Apologetic language ("Sorry, unfortunately...")
- Hedging ("I think, maybe, perhaps...")
- Redundant confirmations ("As requested, per your instruction...")
- Excessive markdown formatting for minimal content

### TUI Dashboard
```bash
token-optimizer tui
```
Real-time dashboard with:
- Session summary with progress bar
- Turn-by-turn table
- Stale files list
- Sessions browser
- Config viewer

---

## Shell Shims

The install script adds shims to your shell RC file:

**bash/zsh** (`~/.bashrc` / `~/.zshrc`):
```bash
source ~/.local/share/token-optimizer/shim.sh
```

**fish** (`~/.config/fish/config.fish`):
```fish
source ~/.local/share/token-optimizer/shim.fish
```

This aliases:
```bash
opencode → wrap_agent opencode
claude   → wrap_agent claude
codex    → wrap_agent codex
aider    → wrap_agent aider
gemini   → wrap_agent gemini
```

Manual control:
```bash
token_optimizer_daemon_start
token_optimizer_daemon_stop
token_optimizer_daemon_status
token_optimizer_tui
```

---

## Configuration

Default config (`~/.config/token-optimizer/config.yaml`):

```yaml
model_context_windows:
  claude-3-5-sonnet: 200000
  gpt-4o: 128000
  gpt-4-turbo: 128000
  default: 128000

thresholds: [0.6, 0.8, 0.95]
stale_turns: 5
hotkey: "C-t"
daemon_socket: "~/.local/share/token-optimizer/daemon.sock"
session_dir: "~/.local/share/token-optimizer/sessions/"
```

On Windows, the daemon uses TCP (port derived from socket path hash) since Unix sockets aren't available.

---

## CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Token Optimizer Scan
  run: |
    pip install -e ./token-optimizer/hook
    token-optimizer scan --severity warning --output github
```

Or use the provided workflow at `.github/workflows/token-optimizer.yml` which:
- Runs scan on every PR
- Comments results on PR
- Runs test suite

Pre-commit hook (`.pre-commit-config.yaml`):
```yaml
- repo: local
  hooks:
    - id: token-optimizer-scan
      entry: token-optimizer scan --severity warning
      language: system
```

---

## Uninstall

```bash
curl -fsSL https://raw.githubusercontent.com/palashsuryavanshi/tokenoptimizer_skill/main/uninstall.sh | bash
```

Removes:
- Python package (`pip uninstall token-optimizer-hook`)
- Shell shims from RC files
- `~/.local/share/token-optimizer/`
- `~/.config/token-optimizer/` (optional)
- `~/.local/bin/token-optimizer`

---

## Development

```bash
# Clone
git clone https://github.com/palashsuryavanshi/tokenoptimizer_skill
cd tokenoptimizer_skill

# Install editable
pip install -e ./token-optimizer/hook[dev]

# Run tests
python -m pytest tests/hook/ -v

# Run scan locally
token-optimizer scan --severity info

# Launch TUI
token-optimizer tui
```

---

## License

MIT — see [LICENSE](LICENSE)