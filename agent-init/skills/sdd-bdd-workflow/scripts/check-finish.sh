#!/bin/bash
# check-finish.sh - 檢查完成條件（多技術棧通用）
# 用法: ./check-finish.sh [check-type]
# check-type: all | lint | test (預設: all)
#
# 自動偵測技術棧：TypeScript, Python, Rust, Go, Java/Kotlin
# 依據 config 檔案存在與否決定執行哪些檢查

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

# ============================================================
# TypeScript / JavaScript
# ============================================================
check_typescript_lint() {
  if [ -f "tsconfig.json" ]; then
    if command -v npx &> /dev/null; then
      run_check "TypeScript (tsc --noEmit)" "npx tsc --noEmit"
    fi
  fi

  # ESLint (flat config or legacy)
  if [ -f "eslint.config.js" ] || [ -f "eslint.config.mjs" ] || [ -f "eslint.config.ts" ] || \
     [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f ".eslintrc.yml" ]; then
    if command -v npx &> /dev/null; then
      run_check "ESLint" "npx eslint . --max-warnings 0"
    fi
  fi

  # Biome (modern alternative to ESLint + Prettier)
  if [ -f "biome.json" ] || [ -f "biome.jsonc" ]; then
    if command -v npx &> /dev/null; then
      run_check "Biome" "npx biome check ."
    fi
  fi
}

check_typescript_test() {
  if [ -f "package.json" ]; then
    if grep -q '"test"' package.json; then
      # Detect package manager
      if [ -f "pnpm-lock.yaml" ]; then
        run_check "Tests (pnpm test)" "pnpm test -- --passWithNoTests 2>/dev/null || pnpm test"
      elif [ -f "yarn.lock" ]; then
        run_check "Tests (yarn test)" "yarn test --passWithNoTests 2>/dev/null || yarn test"
      elif [ -f "bun.lockb" ]; then
        run_check "Tests (bun test)" "bun test"
      else
        run_check "Tests (npm test)" "npm test -- --passWithNoTests 2>/dev/null || npm test"
      fi
    fi
  fi
}

# ============================================================
# Python
# ============================================================
check_python_lint() {
  # Ruff (modern, fast)
  if [ -f "pyproject.toml" ] && grep -q '\[tool.ruff\]' pyproject.toml 2>/dev/null; then
    if command -v ruff &> /dev/null; then
      run_check "Ruff lint" "ruff check ."
    fi
  fi

  # MyPy type checking
  if [ -f "pyproject.toml" ] && grep -q '\[tool.mypy\]' pyproject.toml 2>/dev/null; then
    if command -v mypy &> /dev/null; then
      run_check "MyPy" "mypy ."
    fi
  elif [ -f "mypy.ini" ] || [ -f ".mypy.ini" ]; then
    if command -v mypy &> /dev/null; then
      run_check "MyPy" "mypy ."
    fi
  fi

  # Pyright
  if [ -f "pyrightconfig.json" ]; then
    if command -v pyright &> /dev/null; then
      run_check "Pyright" "pyright"
    fi
  fi

  # Flake8 (legacy, still common)
  if [ -f ".flake8" ] || [ -f "setup.cfg" ] && grep -q '\[flake8\]' setup.cfg 2>/dev/null; then
    if command -v flake8 &> /dev/null; then
      run_check "Flake8" "flake8 ."
    fi
  fi
}

check_python_test() {
  if [ -f "pyproject.toml" ] || [ -f "pytest.ini" ] || [ -f "setup.cfg" ] || [ -d "tests" ]; then
    if command -v pytest &> /dev/null; then
      run_check "Tests (pytest)" "pytest --tb=short -q"
    elif command -v python &> /dev/null && python -m pytest --version &> /dev/null; then
      run_check "Tests (python -m pytest)" "python -m pytest --tb=short -q"
    fi
  fi
}

# ============================================================
# Rust
# ============================================================
check_rust_lint() {
  if [ -f "Cargo.toml" ]; then
    if command -v cargo &> /dev/null; then
      run_check "Cargo check" "cargo check --quiet"
      run_check "Clippy" "cargo clippy --quiet -- -D warnings"
    fi
  fi
}

check_rust_test() {
  if [ -f "Cargo.toml" ]; then
    if command -v cargo &> /dev/null; then
      run_check "Tests (cargo test)" "cargo test --quiet"
    fi
  fi
}

# ============================================================
# Go
# ============================================================
check_go_lint() {
  if [ -f "go.mod" ]; then
    if command -v go &> /dev/null; then
      run_check "Go vet" "go vet ./..."
    fi
    if command -v golangci-lint &> /dev/null; then
      run_check "golangci-lint" "golangci-lint run"
    fi
  fi
}

check_go_test() {
  if [ -f "go.mod" ]; then
    if command -v go &> /dev/null; then
      run_check "Tests (go test)" "go test ./... -count=1"
    fi
  fi
}

# ============================================================
# 技術棧偵測與執行
# ============================================================
DETECTED=""

detect_stacks() {
  [ -f "package.json" ] || [ -f "tsconfig.json" ] && DETECTED="${DETECTED} node"
  [ -f "pyproject.toml" ] || [ -f "setup.py" ] || [ -f "requirements.txt" ] && DETECTED="${DETECTED} python"
  [ -f "Cargo.toml" ] && DETECTED="${DETECTED} rust"
  [ -f "go.mod" ] && DETECTED="${DETECTED} go"

  if [ -z "$DETECTED" ]; then
    echo "⚠️  No recognized tech stack detected. Skipping automated checks."
    echo "   Supported: Node.js/TypeScript, Python, Rust, Go"
    exit 0
  fi

  echo "Detected tech stacks:${DETECTED}"
  echo ""
}

run_lint_checks() {
  [[ "$DETECTED" == *"node"* ]] && check_typescript_lint
  [[ "$DETECTED" == *"python"* ]] && check_python_lint
  [[ "$DETECTED" == *"rust"* ]] && check_rust_lint
  [[ "$DETECTED" == *"go"* ]] && check_go_lint
}

run_test_checks() {
  [[ "$DETECTED" == *"node"* ]] && check_typescript_test
  [[ "$DETECTED" == *"python"* ]] && check_python_test
  [[ "$DETECTED" == *"rust"* ]] && check_rust_test
  [[ "$DETECTED" == *"go"* ]] && check_go_test
}

# 主流程
detect_stacks

case $CHECK_TYPE in
  all)
    run_lint_checks
    run_test_checks
    ;;
  lint)
    run_lint_checks
    ;;
  test)
    run_test_checks
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
