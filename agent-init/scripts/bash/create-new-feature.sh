#!/usr/bin/env bash
# create-new-feature.sh - Create a new feature branch and initialize spec file
#
# Usage:
#   create-new-feature.sh --json "Feature description text"
#
# Output (JSON):
#   BRANCH_NAME and SPEC_FILE path

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Parse arguments
JSON_MODE=false
FEATURE_DESC=""

for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        *) FEATURE_DESC="$arg" ;;
    esac
done

if [ -z "$FEATURE_DESC" ]; then
    echo "ERROR: Feature description is required" >&2
    echo "Usage: create-new-feature.sh --json \"Feature description\"" >&2
    exit 1
fi

REPO_ROOT=$(get_repo_root)

# Generate branch name from description
# Convert to lowercase, replace spaces/special chars with hyphens, truncate
SLUG=$(echo "$FEATURE_DESC" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//' | cut -c1-50)

# Find next feature number
SPECS_DIR="$REPO_ROOT/specs"
mkdir -p "$SPECS_DIR"

NEXT_NUM=1
if [ -d "$SPECS_DIR" ]; then
    for dir in "$SPECS_DIR"/*/; do
        if [ -d "$dir" ]; then
            dirname=$(basename "$dir")
            if [[ "$dirname" =~ ^([0-9]{3})- ]]; then
                num=$((10#${BASH_REMATCH[1]}))
                if [ "$num" -ge "$NEXT_NUM" ]; then
                    NEXT_NUM=$((num + 1))
                fi
            fi
        fi
    done
fi

BRANCH_NAME=$(printf "%03d-%s" "$NEXT_NUM" "$SLUG")
FEATURE_DIR="$SPECS_DIR/$BRANCH_NAME"
SPEC_FILE="$FEATURE_DIR/spec.md"

# Create feature directory
mkdir -p "$FEATURE_DIR"

# Create and checkout branch (if git available)
if has_git; then
    CURRENT=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")
    if [ "$CURRENT" != "$BRANCH_NAME" ]; then
        # Check if branch already exists
        if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null; then
            git checkout "$BRANCH_NAME"
        else
            git checkout -b "$BRANCH_NAME"
        fi
    fi
fi

# Initialize spec file with minimal header if it doesn't exist
if [ ! -f "$SPEC_FILE" ]; then
    cat > "$SPEC_FILE" <<SPEC
# Feature: $FEATURE_DESC

> Auto-generated spec stub. To be filled by /specify command.

---
SPEC
fi

# Output
if [ "$JSON_MODE" = "true" ]; then
    cat <<EOF
{
  "BRANCH_NAME": "$BRANCH_NAME",
  "SPEC_FILE": "$SPEC_FILE",
  "FEATURE_DIR": "$FEATURE_DIR"
}
EOF
else
    echo "Branch: $BRANCH_NAME"
    echo "Spec: $SPEC_FILE"
fi
