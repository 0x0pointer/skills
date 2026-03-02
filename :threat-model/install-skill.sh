#!/bin/bash

# PASTA Threat Modeling Skill Installer for Claude Code
# This script installs the pasta-threat-model skill to Claude Code

set -e

SKILL_NAME="threat-modeling"
SKILL_DIR="$HOME/.claude/skills/$SKILL_NAME"
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🛡️  Installing Threat Modeling Skill for Claude Code..."
echo ""

# Check if Claude Code skills directory exists
if [ ! -d "$HOME/.claude/skills" ]; then
    echo "📁 Creating Claude Code skills directory..."
    mkdir -p "$HOME/.claude/skills"
fi

# Remove existing installation if present
if [ -d "$SKILL_DIR" ]; then
    echo "♻️  Removing existing installation..."
    rm -rf "$SKILL_DIR"
fi

# Create skill directory
echo "📦 Creating skill directory..."
mkdir -p "$SKILL_DIR"

# Copy skill file
echo "📋 Copying skill file..."
cp "$SOURCE_DIR/SKILL.md" "$SKILL_DIR/SKILL.md"

# Verify installation
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    echo ""
    echo "✅ Installation successful!"
    echo ""
    echo "📍 Skill installed to: $SKILL_DIR"
    echo ""
    echo "🚀 Usage:"
    echo "   1. Restart Claude Code (exit and relaunch)"
    echo "   2. Navigate to your project directory"
    echo "   3. Claude will automatically invoke the skill when you ask for threat modeling"
    echo ""
    echo "📖 Example prompts:"
    echo "   'Do a threat model for our payment API'"
    echo "   'Map the attack surface of this application'"
    echo "   'Run a PASTA threat modeling session on this service'"
    echo "   'What security risks does this architecture have?'"
    echo ""
    echo "📄 Outputs produced:"
    echo "   - threat-model-[app].md   (Markdown report)"
    echo "   - threat-model-[app].html (Styled HTML report with Mermaid diagrams)"
    echo ""
    echo "⚠️  IMPORTANT: You MUST restart Claude Code for the skill to appear!"
    echo ""
else
    echo ""
    echo "❌ Installation failed!"
    echo "Please check that the required file exists:"
    echo "  - $SOURCE_DIR/SKILL.md"
    exit 1
fi
