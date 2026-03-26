#!/usr/bin/env bash
# setup-plan.sh - Initialize implementation plan for current feature
#
# Usage:
#   setup-plan.sh --json
#
# Output (JSON):
#   FEATURE_SPEC, IMPL_PLAN, SPECS_DIR, BRANCH paths

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Parse arguments
JSON_MODE=false
for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
    esac
done

# Get feature paths
eval "$(get_feature_paths)"

# Validate
if [ ! -d "$FEATURE_DIR" ]; then
    if [ "$JSON_MODE" = "true" ]; then
        echo "{\"error\": \"Feature directory not found: $FEATURE_DIR. Run /specify first.\"}"
    else
        echo "ERROR: Feature directory not found: $FEATURE_DIR" >&2
    fi
    exit 1
fi

if [ ! -f "$FEATURE_SPEC" ]; then
    if [ "$JSON_MODE" = "true" ]; then
        echo "{\"error\": \"Spec file not found: $FEATURE_SPEC. Run /specify first.\"}"
    else
        echo "ERROR: Spec file not found: $FEATURE_SPEC" >&2
    fi
    exit 1
fi

# Initialize plan file from template if it doesn't exist
REPO_ROOT=$(get_repo_root)
PLAN_TEMPLATE="$REPO_ROOT/.agent/templates/plan-template.md"

if [ ! -f "$IMPL_PLAN" ]; then
    if [ -f "$PLAN_TEMPLATE" ]; then
        cp "$PLAN_TEMPLATE" "$IMPL_PLAN"
    else
        # Create minimal plan stub
        cat > "$IMPL_PLAN" <<PLAN
# Implementation Plan

> Generated for feature: $CURRENT_BRANCH

---
PLAN
    fi
fi

# Output
if [ "$JSON_MODE" = "true" ]; then
    cat <<EOF
{
  "FEATURE_SPEC": "$FEATURE_SPEC",
  "IMPL_PLAN": "$IMPL_PLAN",
  "SPECS_DIR": "$FEATURE_DIR",
  "BRANCH": "$CURRENT_BRANCH",
  "FEATURE_DIR": "$FEATURE_DIR"
}
EOF
else
    echo "Spec: $FEATURE_SPEC"
    echo "Plan: $IMPL_PLAN"
    echo "Dir:  $FEATURE_DIR"
fi
