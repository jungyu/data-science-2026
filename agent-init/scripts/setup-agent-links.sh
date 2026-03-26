#!/bin/bash

# setup-agent-links.sh
# Creates symlinks for external tools (Github Copilot, Claude, etc.) to point to the unified .agent directory.

set -e

# Base directory (repo root)
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "🔗 Setting up agent symlinks..."

# 1. GitHub Copilot
# Expects: .github/copilot-instructions.md
# Source: .agent/rules/copilot-instructions.md
if [ -d ".github" ]; then
    ln -sf ../.agent/rules/copilot-instructions.md .github/copilot-instructions.md
    echo "✅ Linked .github/copilot-instructions.md"
else
    echo "⚠️ .github directory not found, skipping Copilot link."
fi

# 2. Claude Desktop / Code
# Expects: .claude/commands, .claude/settings.local.json
# Source: .agent/prompts/commands, .agent/config/claude-settings.json
mkdir -p .claude
ln -sf ../.agent/prompts/commands .claude/commands
ln -sf ../.agent/config/claude-settings.json .claude/settings.local.json
echo "✅ Linked .claude/ directories"

# 3. AGENTS.md (GitHub Copilot Coding Agent)
# Expects: .github/AGENTS.md
# Source: .agent/rules/AGENTS.md
if [ -d ".github" ]; then
    ln -sf ../.agent/rules/AGENTS.md .github/AGENTS.md
    echo "✅ Linked .github/AGENTS.md"
else
    echo "⚠️ .github directory not found, skipping AGENTS.md link."
fi

echo "🎉 Agent symlinks setup complete. Tools should now see .agent/ contents correctly."
