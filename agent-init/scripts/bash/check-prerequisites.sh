#!/usr/bin/env bash
# check-prerequisites.sh - Verify feature branch prerequisites and output paths
#
# Usage:
#   check-prerequisites.sh --json [--paths-only] [--require-tasks] [--include-tasks]
#
# Options:
#   --json            Output JSON format (required)
#   --paths-only      Only output path information, skip doc availability checks
#   --require-tasks   Fail if tasks.md does not exist
#   --include-tasks   Include tasks.md content summary in output
#
# Output (JSON):
#   FEATURE_DIR, FEATURE_SPEC, IMPL_PLAN, TASKS, AVAILABLE_DOCS list

set -e

# Source common functions
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/common.sh"

# Parse arguments
JSON_MODE=false
PATHS_ONLY=false
REQUIRE_TASKS=false
INCLUDE_TASKS=false

for arg in "$@"; do
    case "$arg" in
        --json) JSON_MODE=true ;;
        --paths-only) PATHS_ONLY=true ;;
        --require-tasks) REQUIRE_TASKS=true ;;
        --include-tasks) INCLUDE_TASKS=true ;;
        *) echo "Unknown option: $arg" >&2; exit 1 ;;
    esac
done

if [ "$JSON_MODE" != "true" ]; then
    echo "ERROR: --json flag is required" >&2
    exit 1
fi

# Get feature paths
eval "$(get_feature_paths)"

# Validate feature branch
if [ "$HAS_GIT" = "true" ]; then
    check_feature_branch "$CURRENT_BRANCH" "$HAS_GIT" || exit 1
fi

# Check feature directory exists
if [ ! -d "$FEATURE_DIR" ]; then
    echo "{\"error\": \"Feature directory not found: $FEATURE_DIR. Run /specify first.\"}"
    exit 1
fi

# Check spec exists
if [ ! -f "$FEATURE_SPEC" ]; then
    echo "{\"error\": \"Spec file not found: $FEATURE_SPEC. Run /specify first.\"}"
    exit 1
fi

# Check tasks if required
if [ "$REQUIRE_TASKS" = "true" ] && [ ! -f "$TASKS" ]; then
    echo "{\"error\": \"tasks.md not found: $TASKS. Run /tasks first.\"}"
    exit 1
fi

# Build available docs list
AVAILABLE_DOCS="[]"
if [ "$PATHS_ONLY" != "true" ]; then
    docs=()
    [ -f "$FEATURE_SPEC" ] && docs+=("\"spec.md\"")
    [ -f "$IMPL_PLAN" ] && docs+=("\"plan.md\"")
    [ -f "$TASKS" ] && docs+=("\"tasks.md\"")
    [ -f "$RESEARCH" ] && docs+=("\"research.md\"")
    [ -f "$DATA_MODEL" ] && docs+=("\"data-model.md\"")
    [ -f "$QUICKSTART" ] && docs+=("\"quickstart.md\"")
    [ -d "$CONTRACTS_DIR" ] && [ -n "$(ls -A "$CONTRACTS_DIR" 2>/dev/null)" ] && docs+=("\"contracts/\"")

    # Join array
    AVAILABLE_DOCS="[$(IFS=,; echo "${docs[*]}")]"
fi

# Output JSON
cat <<EOF
{
  "FEATURE_DIR": "$FEATURE_DIR",
  "FEATURE_SPEC": "$FEATURE_SPEC",
  "IMPL_PLAN": "$IMPL_PLAN",
  "TASKS": "$TASKS",
  "RESEARCH": "$RESEARCH",
  "DATA_MODEL": "$DATA_MODEL",
  "QUICKSTART": "$QUICKSTART",
  "CONTRACTS_DIR": "$CONTRACTS_DIR",
  "BRANCH": "$CURRENT_BRANCH",
  "AVAILABLE_DOCS": $AVAILABLE_DOCS
}
EOF
