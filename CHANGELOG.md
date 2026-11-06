# Changelog

All notable changes to this project will be documented in this format.

## [0.1.0] - 2026-11-07

### Added
- **Core skill** (`~/.opencode/skill/token_optimizer.md`) — 590 words, 4 pressure scenarios tested with blind quality gates (3/4 pass, 1 documented loss)
- **Daemon** (`hook.py`) — SessionTracker with turn logging, threshold warnings (60%/80%/95%), stale file detection, JSONL persistence
- **Shell shims** — `shim.sh` (bash/zsh) and `shim.fish` wrapping `opencode`, `claude`, `codex`, `aider`, `gemini`
- **TUI** (`tui.py`) — Textual dashboard with session summary, turns table, stale files, sessions browser, config viewer
- **CLI** (`token-optimizer`) — Subcommands: `daemon`, `session`, `config`, `scan`, `tui`
- **CI gate** (`scan.py`) — Scans for verbose patterns (explanatory preambles, apologetic language, hedging, redundant confirmations, excessive formatting)
- **GitHub Action** (`.github/workflows/token-optimizer.yml`) — Runs scan on PRs, comments results
- **Pre-commit hook** (`.pre-commit-config.yaml`) — Local token-optimizer-scan hook
- **Install script** (`install.sh`) — One-line install with requirements check, package install, config generation, shim setup
- **Uninstall script** (`uninstall.sh`) — Complete removal with confirmation
- **Config scaffold** (`config scaffold`) — Generate default config.yaml

### Changed
- Windows compatibility: Daemon uses TCP fallback (port hash from socket path) since Unix sockets unavailable
- Config schema validation with JSON Schema
- 8 unit tests passing (config, session tracker, daemon)

### Quality Gates
- Core skill: ~25% output reduction (3047→2293 words)
- Blind judges: 3/4 scenarios pass, Scenario 01 (explanation) accepted loss — baseline broader on onboarding depth
- CI scan: Exit code 1 on violations at or above `--severity` threshold

---

## [Unreleased]

### Planned
- E2E test in disposable container (Task 7)
- Release workflow with semantic versioning
- Agent-native integration (Option 2 from design doc)
- Webhook support for external dashboards