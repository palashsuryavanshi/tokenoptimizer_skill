#!/bin/bash
# Token Optimizer Extension Uninstaller
# Usage: curl -fsSL https://raw.githubusercontent.com/palashsuryavanshi/tokenoptimizer_skill/main/uninstall.sh | bash

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/token-optimizer"
CONFIG_DIR="${HOME}/.config/token-optimizer"
BIN_DIR="${HOME}/.local/bin"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[uninstall]${NC} $*"; }
warn() { echo -e "${YELLOW}[warn]${NC} $*"; }
error() { echo -e "${RED}[error]${NC} $*" >&2; }
success() { echo -e "${GREEN}[ok]${NC} $*"; }

confirm() {
    local prompt="${1:-Are you sure?}"
    read -r -p "${prompt} [y/N] " response
    case "${response}" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

# Stop daemon if running
stop_daemon() {
    log "Stopping daemon..."
    if command -v token-optimizer &>/dev/null; then
        token-optimizer daemon stop 2>/dev/null || true
    fi
    # Also kill any remaining processes
    pkill -f "token-optimizer daemon" 2>/dev/null || true
    success "Daemon stopped"
}

# Remove Python package
remove_package() {
    log "Removing Python package..."
    python3 -m pip uninstall -y token-optimizer-hook 2>/dev/null || true
    success "Package removed"
}

# Remove shell shims from RC files
remove_shims() {
    log "Removing shell shims from RC files..."
    
    for RC_FILE in "${HOME}/.bashrc" "${HOME}/.zshrc" "${HOME}/.config/fish/config.fish"; do
        if [[ -f "${RC_FILE}" ]]; then
            # Create backup
            cp "${RC_FILE}" "${RC_FILE}.token-optimizer-backup.$(date +%s)"
            
            # Remove token-optimizer lines
            sed -i '/token-optimizer/d' "${RC_FILE}"
            sed -i '/\.local\/share\/token-optimizer/d' "${RC_FILE}"
            sed -i '/\.local\/bin/d' "${RC_FILE}"
            
            # Clean up empty lines at end
            sed -i -e :a -e '/^\n*$/{$d;N;ba' -e '}' "${RC_FILE}" 2>/dev/null || true
            
            success "Cleaned ${RC_FILE}"
        fi
    done
}

# Remove directories
remove_dirs() {
    log "Removing directories..."
    
    if [[ -d "${INSTALL_DIR}" ]]; then
        rm -rf "${INSTALL_DIR}"
        success "Removed ${INSTALL_DIR}"
    fi
    
    if [[ -d "${CONFIG_DIR}" ]]; then
        # Ask before removing config (may have user customizations)
        if confirm "Remove config directory ${CONFIG_DIR}? (contains your settings)"; then
            rm -rf "${CONFIG_DIR}"
            success "Removed ${CONFIG_DIR}"
        else
            log "Kept ${CONFIG_DIR}"
        fi
    fi
    
    # Remove wrapper scripts
    for WRAPPER in "${BIN_DIR}/token-optimizer"; do
        if [[ -f "${WRAPPER}" ]]; then
            rm -f "${WRAPPER}"
            success "Removed ${WRAPPER}"
        fi
    done
}

# Main
main() {
    echo "╔══════════════════════════════════════════════╗"
    echo "║   Token Optimizer Extension Uninstaller     ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    
    if ! confirm "This will remove Token Optimizer completely. Continue?"; then
        log "Cancelled"
        exit 0
    fi
    
    echo ""
    stop_daemon
    remove_package
    remove_shims
    remove_dirs
    
    echo ""
    echo "╔══════════════════════════════════════════════╗"
    echo "║   Uninstall Complete!                       ║"
    echo "╚══════════════════════════════════════════════╝"
    echo ""
    echo "Restart your shell to complete removal: exec \$SHELL"
    echo ""
}

main "$@"