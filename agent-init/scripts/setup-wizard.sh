#!/bin/bash
# setup-wizard.sh — Interactive setup wizard for .agent-init placeholder configuration
#
# Walks through required placeholders and replaces them across all files.
# Run this after copying .agent-init/ into your project.
#
# Usage:
#   chmod +x .agent/scripts/setup-wizard.sh
#   .agent/scripts/setup-wizard.sh

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Determine agent directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AGENT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   .agent-init Setup Wizard                   ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""
echo "This wizard will help you fill in the required placeholders."
echo "Press Enter to skip any field (placeholder will be kept for later)."
echo ""

# Helper: replace placeholder in all files under AGENT_DIR
replace_placeholder() {
    local placeholder="$1"
    local value="$2"
    if [ -n "$value" ]; then
        # Use | as delimiter to avoid conflicts with /
        find "$AGENT_DIR" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) \
            -exec sed -i'' -e "s|{{${placeholder}}}|${value}|g" {} +
        echo -e "  ${GREEN}✅ Replaced {{${placeholder}}} → ${value}${NC}"
        return 0
    else
        echo -e "  ${YELLOW}⏭  Skipped {{${placeholder}}}${NC}"
        return 1
    fi
}

# Helper: prompt user for a value
ask() {
    local placeholder="$1"
    local description="$2"
    local example="$3"
    local value

    echo -e "${CYAN}▸ ${description}${NC}"
    if [ -n "$example" ]; then
        echo -e "  Example: ${example}"
    fi
    read -r -p "  > " value
    echo ""
    replace_placeholder "$placeholder" "$value"
}

# Count remaining placeholders
count_placeholders() {
    find "$AGENT_DIR" -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" -o -name "*.json" \) \
        -exec grep -l '{{' {} + 2>/dev/null | wc -l | tr -d ' '
}

BEFORE=$(count_placeholders)

echo "═══════════════════════════════════════════"
echo " STEP 1: Core Project Info"
echo "═══════════════════════════════════════════"
echo ""

ask "PROJECT_NAME" "Project name" "My SaaS App"
ask "TECH_STACK" "Tech stack (comma-separated)" "Next.js 15, PostgreSQL, Tailwind CSS"
ask "DATE" "Today's date (YYYY-MM-DD)" "$(date +%Y-%m-%d)"

echo "═══════════════════════════════════════════"
echo " STEP 2: Directory Structure"
echo "═══════════════════════════════════════════"
echo ""

ask "SRC_DIR" "Source code directory" "src/ or lib/"
ask "API_DIR" "API routes directory" "app/api/ or routes/"
ask "TEST_DIR" "Test directory" "tests/ or __tests__/"
ask "LIB_DIR" "Shared libraries directory" "lib/ or src/lib/"
ask "COMPONENT_DIR" "UI components directory" "components/ or src/components/"
ask "MIGRATION_DIR" "Database migrations directory" "migrations/ or prisma/migrations/"

echo "═══════════════════════════════════════════"
echo " STEP 3: Language & Framework Config"
echo "═══════════════════════════════════════════"
echo ""

ask "LANGUAGE_SPECIFIC" "Language-specific strict mode rules" "tsconfig.json strict: true, noUncheckedIndexedAccess"
ask "LINTER_CONFIG" "Linter config path & tool" "eslint.config.mjs with @typescript-eslint/recommended"
ask "AUTH_FRAMEWORK" "Auth framework rules" "NextAuth v5 middleware protecting /api/ and /dashboard/"

echo "═══════════════════════════════════════════"
echo " STEP 4: Project Structure & Build"
echo "═══════════════════════════════════════════"
echo ""

ask "PROJECT_STRUCTURE" "Brief project structure description" "Next.js 15 App Router. Pages in app/, shared components in components/"
ask "BUILD_COMMANDS" "Build & test commands" "pnpm dev / pnpm build / pnpm test / pnpm lint"
ask "CODING_STYLE" "Coding style summary" "TypeScript strict, PascalCase components, kebab-case files"
ask "MODULE_TAXONOMY" "Module list (name:path:purpose, comma-separated)" "Auth:lib/auth/:認證授權, Core:lib/core/:共用基礎設施"
ask "PROJECT_MODULES" "Module tag list for file naming" "Auth, Core, UI, API"

echo "═══════════════════════════════════════════"
echo " STEP 5: Governance Config"
echo "═══════════════════════════════════════════"
echo ""

ask "GOVERNANCE_ARCHITECTURE_PATH" "Governance architecture doc path" "docs/architecture/GOVERNANCE-ARCHITECTURE.md"
ask "RAPIDLY_EVOLVING_TECH" "Rapidly evolving tech (needs dual anchoring)" "React Native, TailwindCSS v4, tRPC"
ask "CORE_DIRS" "Core directories (deletion triggers L1 review)" "lib/, app/, components/, config/"

echo "═══════════════════════════════════════════"
echo " STEP 6: Style & Tooling Paths"
echo "═══════════════════════════════════════════"
echo ""

ask "STYLE_CANON_PATH" "Style canon document path" "docs/style-canon.md"
ask "CONTRACT_DIR" "API contracts directory" "contracts/ or schemas/"
ask "ADR_DIR" "Architecture Decision Records directory" "docs/adr/"
ask "INTENT_DIR" "Intent map directory" "docs/intent/"
ask "ERROR_TYPE_MODULE" "Centralized error types module" "lib/errors.ts"
ask "LOGGING_UTILITY" "Centralized logging utility" "lib/logger.ts"
ask "CSS_MERGE_UTILITY" "CSS class merge utility" "lib/utils/cn.ts"

# Summary
AFTER=$(count_placeholders)
REPLACED=$((BEFORE - AFTER))

echo ""
echo "═══════════════════════════════════════════"
echo " Setup Complete!"
echo "═══════════════════════════════════════════"
echo ""
echo -e "  Files with placeholders before: ${YELLOW}${BEFORE}${NC}"
echo -e "  Files with placeholders after:  ${GREEN}${AFTER}${NC}"
echo ""

if [ "$AFTER" -gt 0 ]; then
    echo -e "${YELLOW}Remaining placeholders:${NC}"
    grep -rn '{{[A-Z_]*}}' "$AGENT_DIR" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.json" 2>/dev/null \
        | grep -oP '\{\{[A-Z_]+\}\}' | sort -u | while read -r p; do
        echo "  - $p"
    done
    echo ""
    echo "Run this wizard again or manually replace them with:"
    echo "  grep -rn '{{' $AGENT_DIR/"
else
    echo -e "${GREEN}All placeholders have been replaced! 🎉${NC}"
fi

echo ""
echo "Next steps:"
echo "  1. Run: .agent/scripts/setup-agent-links.sh"
echo "  2. Review: .agent/memory/constitution.md"
echo "  3. Start developing with AI governance enabled"
echo ""
