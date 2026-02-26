#!/bin/bash
# check-finish.sh - 檢查完成條件
# 用法: ./check-finish.sh [check-type]
# check-type: all | lint | test (預設: all)

set -e

CHECK_TYPE=${1:-all}

echo "🔍 Checking finish conditions (type: $CHECK_TYPE)..."
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# 函數：執行檢查
run_check() {
  local name=$1
  local cmd=$2
  
  echo "Running: $name"
  if eval "$cmd" > /dev/null 2>&1; then
    echo "  ✅ $name: PASS"
    PASS_COUNT=$((PASS_COUNT + 1))
    return 0
  else
    echo "  ❌ $name: FAIL"
    FAIL_COUNT=$((FAIL_COUNT + 1))
    return 1
  fi
}

# TypeScript 檢查
check_typescript() {
  if command -v npx &> /dev/null && [ -f "tsconfig.json" ]; then
    run_check "TypeScript (tsc --noEmit)" "npx tsc --noEmit"
  else
    echo "  ⏭️  TypeScript: SKIPPED (no tsconfig.json)"
  fi
}

# ESLint 檢查
check_eslint() {
  if command -v npx &> /dev/null && [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f "eslint.config.js" ]; then
    run_check "ESLint" "npx eslint . --ext .ts,.tsx --quiet --max-warnings 0"
  else
    echo "  ⏭️  ESLint: SKIPPED (no config found)"
  fi
}

# 測試檢查
check_tests() {
  if [ -f "package.json" ] && grep -q '"test"' package.json; then
    run_check "Tests (npm test)" "npm test -- --passWithNoTests"
  else
    echo "  ⏭️  Tests: SKIPPED (no test script)"
  fi
}

# 執行檢查
case $CHECK_TYPE in
  all)
    check_typescript
    check_eslint
    check_tests
    ;;
  lint)
    check_typescript
    check_eslint
    ;;
  test)
    check_tests
    ;;
  *)
    echo "❌ Unknown check type: $CHECK_TYPE"
    echo "Usage: check-finish.sh [all|lint|test]"
    exit 1
    ;;
esac

echo ""
echo "────────────────────────────"
echo "Summary: $PASS_COUNT passed, $FAIL_COUNT failed"

if [ $FAIL_COUNT -eq 0 ]; then
  echo "✅ All finish conditions met!"
  exit 0
else
  echo "❌ Some finish conditions not met"
  exit 1
fi
