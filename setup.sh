#!/bin/bash

# Security Workflows Setup Script
# This script helps you set up the security workflows for Claude Code

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DEFAULT_INSTALL_PATH="$HOME/security-workflows"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║     Security Workflows for Claude Code - Setup           ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Check if already in the correct location
if [ "$SCRIPT_DIR" = "$DEFAULT_INSTALL_PATH" ]; then
    print_success "Already installed in $DEFAULT_INSTALL_PATH"
    ALREADY_INSTALLED=true
else
    ALREADY_INSTALLED=false
fi

echo ""
echo "This script will help you set up security workflows for use with Claude Code."
echo ""

# Ask for installation type
if [ "$ALREADY_INSTALLED" = false ]; then
    echo "Current location: $SCRIPT_DIR"
    echo "Recommended location: $DEFAULT_INSTALL_PATH"
    echo ""
    read -p "Do you want to move this directory to $DEFAULT_INSTALL_PATH? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -d "$DEFAULT_INSTALL_PATH" ]; then
            print_warning "$DEFAULT_INSTALL_PATH already exists"
            read -p "Do you want to backup the existing directory and replace it? (y/n): " -n 1 -r
            echo ""

            if [[ $REPLY =~ ^[Yy]$ ]]; then
                BACKUP_PATH="${DEFAULT_INSTALL_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
                print_info "Backing up to $BACKUP_PATH"
                mv "$DEFAULT_INSTALL_PATH" "$BACKUP_PATH"
                print_success "Backup created"
            else
                print_error "Setup cancelled"
                exit 1
            fi
        fi

        print_info "Moving directory to $DEFAULT_INSTALL_PATH"
        mkdir -p "$(dirname "$DEFAULT_INSTALL_PATH")"
        mv "$SCRIPT_DIR" "$DEFAULT_INSTALL_PATH"
        print_success "Moved to $DEFAULT_INSTALL_PATH"

        # Update script directory reference
        SCRIPT_DIR="$DEFAULT_INSTALL_PATH"
        cd "$SCRIPT_DIR"
    else
        print_info "Keeping current location: $SCRIPT_DIR"
    fi
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Verify directory structure
print_info "Verifying directory structure..."

REQUIRED_FILES=(
    "README.md"
    "cve-analysis/workflow.md"
    "cve-analysis/README.md"
)

ALL_FILES_PRESENT=true
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$SCRIPT_DIR/$file" ]; then
        print_success "$file found"
    else
        print_error "$file missing"
        ALL_FILES_PRESENT=false
    fi
done

if [ "$ALL_FILES_PRESENT" = false ]; then
    print_error "Some required files are missing. Setup incomplete."
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Check if git is initialized
if [ -d "$SCRIPT_DIR/.git" ]; then
    print_success "Git repository detected"

    # Check for remote
    if git -C "$SCRIPT_DIR" remote -v | grep -q "origin"; then
        REMOTE_URL=$(git -C "$SCRIPT_DIR" remote get-url origin)
        print_success "Remote repository: $REMOTE_URL"
    else
        print_warning "No git remote configured"
        echo ""
        read -p "Do you want to add a git remote now? (y/n): " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter git remote URL: " REMOTE_URL
            git -C "$SCRIPT_DIR" remote add origin "$REMOTE_URL"
            print_success "Remote added: $REMOTE_URL"

            read -p "Do you want to push now? (y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git -C "$SCRIPT_DIR" add .
                git -C "$SCRIPT_DIR" commit -m "Initial commit: Security workflows setup" || true
                git -C "$SCRIPT_DIR" push -u origin main || git -C "$SCRIPT_DIR" push -u origin master
                print_success "Pushed to remote"
            fi
        fi
    fi
else
    print_warning "Not a git repository"
    echo ""
    read -p "Do you want to initialize git repository? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git -C "$SCRIPT_DIR" init
        git -C "$SCRIPT_DIR" add .
        git -C "$SCRIPT_DIR" commit -m "Initial commit: Security workflows setup"
        print_success "Git repository initialized"

        read -p "Do you want to add a remote repository? (y/n): " -n 1 -r
        echo ""

        if [[ $REPLY =~ ^[Yy]$ ]]; then
            read -p "Enter git remote URL: " REMOTE_URL
            git -C "$SCRIPT_DIR" remote add origin "$REMOTE_URL"
            print_success "Remote added: $REMOTE_URL"

            read -p "Do you want to push now? (y/n): " -n 1 -r
            echo ""
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git -C "$SCRIPT_DIR" push -u origin main || git -C "$SCRIPT_DIR" push -u origin master
                print_success "Pushed to remote"
            fi
        fi
    fi
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""

# Create convenience aliases
print_info "Creating convenience commands..."

# Detect shell
SHELL_RC=""
if [ -n "$ZSH_VERSION" ]; then
    SHELL_RC="$HOME/.zshrc"
elif [ -n "$BASH_VERSION" ]; then
    SHELL_RC="$HOME/.bashrc"
fi

if [ -n "$SHELL_RC" ]; then
    echo ""
    read -p "Do you want to add a shell alias for quick access? (y/n): " -n 1 -r
    echo ""

    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ALIAS_LINE="alias sec-workflows='cd $SCRIPT_DIR'"

        if grep -q "sec-workflows" "$SHELL_RC"; then
            print_warning "Alias already exists in $SHELL_RC"
        else
            echo "" >> "$SHELL_RC"
            echo "# Security Workflows" >> "$SHELL_RC"
            echo "$ALIAS_LINE" >> "$SHELL_RC"
            print_success "Added alias 'sec-workflows' to $SHELL_RC"
            print_info "Run 'source $SHELL_RC' or restart your terminal to use it"
        fi
    fi
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║                                                           ║"
echo "║                    Setup Complete!                        ║"
echo "║                                                           ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""

print_success "Security workflows installed at: $SCRIPT_DIR"
echo ""

echo "📚 Available Workflows:"
echo "  • CVE Analysis - Analyze dependency vulnerabilities"
echo ""

echo "🚀 Quick Start:"
echo ""
echo "  1. Navigate to any project:"
echo "     cd /path/to/your/project"
echo ""
echo "  2. Start Claude Code:"
echo "     claude"
echo ""
echo "  3. Run a CVE analysis:"
echo "     /analyze-cve <dependency> <version> <cve-url>"
echo ""
echo "  4. Or reference the workflow directly:"
echo "     Use the CVE workflow from $SCRIPT_DIR/cve-analysis/workflow.md"
echo ""

echo "📖 Documentation:"
echo "  • Main README: $SCRIPT_DIR/README.md"
echo "  • CVE Analysis: $SCRIPT_DIR/cve-analysis/README.md"
echo ""

if [ -d "$SCRIPT_DIR/.git" ]; then
    if git -C "$SCRIPT_DIR" remote -v | grep -q "origin"; then
        REMOTE_URL=$(git -C "$SCRIPT_DIR" remote get-url origin)
        echo "🔗 Share with your team:"
        echo "  git clone $REMOTE_URL ~/security-workflows"
        echo "  cd ~/security-workflows"
        echo "  ./setup.sh"
        echo ""
    else
        echo "💡 Tip: Add a git remote to share with your team:"
        echo "  cd $SCRIPT_DIR"
        echo "  git remote add origin <your-repo-url>"
        echo "  git push -u origin main"
        echo ""
    fi
fi

echo "🔄 To update workflows:"
echo "  cd $SCRIPT_DIR && git pull"
echo ""

echo "❓ Need help?"
echo "  Read the documentation in $SCRIPT_DIR/README.md"
echo ""

print_success "You're all set! Happy hunting! 🔒🔍"
echo ""
