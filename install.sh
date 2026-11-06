#!/bin/bash
# Token Optimizer Extension Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/palashsuryavanshi/tokenoptimizer_skill/main/install.sh | bash

set -euo pipefail

REPO="palashsuryavanshi/tokenoptimizer_skill"
BRANCH="main"
INSTALL_DIR="${HOME}/.local/share/token-optimizer"
CONFIG_DIR="${HOME}/.config/token-optimizer"
BIN_DIR="${HOME}/.local/bin"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() { echo -e "${BLUE}[install]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
error() { echo -e "${RED}[error]${NC} $*" >&2; }
success() { echo -e "${GREEN}[ok]${NC} $*"; }

# Check requirements
check_requirements() {
    log "Checking requirements..."
    
    if ! command -v python3 &>/dev/null; then
        error "python3 not found. Please install Python 3.10+"
        exit 1
    fi
    
    PY_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
        error "Python 3.10+ required, found ${PY_VERSION}"
        exit 1
    fi
    
    if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
        error "pip not found. Please install pip"
        exit 1
    fi
    
    success "Requirements satisfied (Python ${PY_VERSION})"
}

# Create directories
create_dirs() {
    log "Creating directories..."
    mkdir -p "${INSTALL_DIR}/sessions"
    mkdir -p "${CONFIG_DIR}"
    mkdir -p "${BIN_DIR}"
    success "Directories created"
}

# Install Python package
install_package() {
    log "Installing token-optimizer-hook..."
    
    # Install from GitHub
    if python3 -m pip install --user -e "git+https://github.com/${REPO}@${BRANCH}#egg=token-optimizer-hook&subdirectory=token-optimizer/hook" 2>&1 | tail -5; then
        success "Package installed"
    else
        error "Failed to install package"
        exit 1
    fi
}

# Generate default config
generate_config() {
    log "Generating default config..."
    
    CONFIG_FILE="${CONFIG_DIR}/config.yaml"
    if [[ -f "${CONFIG_FILE}" ]]; then
        warn "Config already exists at ${CONFIG_FILE}, skipping"
        return
    fi
    
    cat > "${CONFIG_FILE}" <<'EOF'
# Token Optimizer Configuration
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
EOF
    
    success "Config generated at ${CONFIG_FILE}"
}

# Install shell shims
install_shims() {
    log "Installing shell shims..."
    
    # Detect shell
    SHELL_NAME=$(basename "${SHELL}")
    RC_FILE=""
    
    case "${SHELL_NAME}" in
        bash)
            RC_FILE="${HOME}/.bashrc"
            ;;
        zsh)
            RC_FILE="${HOME}/.zshrc"
            ;;
        fish)
            RC_FILE="${HOME}/.config/fish/config.fish"
            ;;
        *)
            warn "Unknown shell: ${SHELL_NAME}. Shim installation skipped."
            warn "Add this to your shell config manually:"
            warn "  source ${INSTALL_DIR}/shim.sh  # for bash/zsh"
            warn "  source ${INSTALL_DIR}/shim.fish  # for fish"
            return
            ;;
    esac
    
    # Copy shim files
    cp "${INSTALL_DIR}/shim.sh" "${INSTALL_DIR}/shim.sh" 2>/dev/null || true
    cp "${INSTALL_DIR}/shim.fish" "${INSTALL_DIR}/shim.fish" 2>/dev/null || true
    
    # Add source line to RC file
    SHIM_LINE=""
    if [[ "${SHELL_NAME}" == "fish" ]]; then
        SHIM_LINE="source ${INSTALL_DIR}/shim.fish"
    else
        SHIM_LINE="source ${INSTALL_DIR}/shim.sh"
    fi
    
    if ! grep -q "token-optimizer/shim" "${RC_FILE}" 2>/dev/null; then
        echo "" >> "${RC_FILE}"
        echo "# Token Optimizer shell shim" >> "${RC_FILE}"
        echo "${SHIM_LINE}" >> "${RC_FILE}"
        success "Added shim to ${RC_FILE}"
    else
        log "Shim already in ${RC_FILE}"
    fi
    
    # Also add bin directory to PATH if not present
    if [[ ":${PATH}:" != *":${BIN_DIR}:"* ]]; then
        echo "" >> "${RC_FILE}"
        echo "# Token Optimizer CLI" >> "${RC_FILE}"
        echo "export PATH=\"${BIN_DIR}:\${PATH}\"" >> "${RC_FILE}"
        success "Added ${BIN_DIR} to PATH in ${RC_FILE}"
    fi
}

# Create wrapper scripts in ~/.local/bin
create_wrappers() {
    log "Creating wrapper scripts..."
    
    # token-optimizer CLI wrapper
    cat > "${BIN_DIR}/token-optimizer" <<'EOF'
#!/bin/bash
# Token Optimizer CLI wrapper
exec python3 -m token_optimizer_hook.cli "$@"
EOF
    chmod +x "${BIN_DIR}/token-optimizer"
    
    success "Wrapper created at ${BIN_DIR}/token-optimizer"
}

# Verify installation
verify_install() {
    log "Verifying installation..."
    
    # Check if token-optimizer command works
    if "${BIN_DIR}/token-optimizer" --help &>/dev/null; then
        success "CLI command works"
    else
        warn "CLI command not working (may need shell restart)"
    fi
    
    # Check config
    if [[ -f "${CONFIG_DIR}/config.yaml" ]]; then
        success "Config file exists"
    else
        warn "Config file missing"
    fi
    
    # Check shims
    if [[ -f "${INSTALL_DIR}/shim.sh" ]]; then
        success "Bash/Zsh shim exists"
    else
        warn "Bash/Zsh shim missing (will be available after package install)"
    fi
    
    if [[ -f "${INSTALL_DIR}/shim.fish" ]]; then
        success "Fish shim exists"
    else
        warn "Fish shim missing (will be available after package install)"
    fi
}

# Main
main() {
    echo "╔══════════════════════════════════════════════╗"
    echo "║   Token Optimizer Extension Installer       ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    
    check_requirements
    create_dirs
    install_package
    generate_config
    install_shims
    create_wrappers
    verify_install
    
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║   Installation Complete!                    ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    echo "Next steps:"
    echo "  1. Restart your shell: exec \$SHELL"
    echo "  2. Start daemon: token-optimizer daemon start"
    echo "  3. Use wrapped agents: opencode, claude, codex, aider, gemini"
    echo "  4. View session: token-optimizer session summary"
    echo "  5. Launch TUI: token-optimizer tui"
    echo ""
    echo "Config: ${CONFIG_DIR}/config.yaml"
    echo "Sessions: ${INSTALL_DIR}/sessions/"
    echo ""
}

main "$@"