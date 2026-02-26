#!/bin/bash
# validate-spec.sh - 驗證規格文件完整性
# 用法: ./validate-spec.sh <spec-file> [mode]
# mode: lite | standard | full (預設: lite)

set -e

SPEC_FILE=$1
MODE=${2:-lite}

if [ -z "$SPEC_FILE" ]; then
  echo "Usage: validate-spec.sh <spec-file> [mode]"
  echo "  mode: lite | standard | full (default: lite)"
  exit 1
fi

if [ ! -f "$SPEC_FILE" ]; then
  echo "❌ File not found: $SPEC_FILE"
  exit 1
fi

echo "🔍 Validating $SPEC_FILE (mode: $MODE)..."

# 定義各模式的必要區塊
case $MODE in
  lite)
    REQUIRED_SECTIONS=("目的" "介面定義" "行為規格" "錯誤處理")
    ;;
  standard)
    REQUIRED_SECTIONS=("範圍定義" "介面定義" "狀態機" "錯誤分類" "行為情境")
    ;;
  full)
    REQUIRED_SECTIONS=("範圍定義" "狀態機" "錯誤分類" "非功能需求" "關鍵決策")
    ;;
  *)
    echo "❌ Unknown mode: $MODE"
    exit 1
    ;;
esac

MISSING_COUNT=0
EMPTY_COUNT=0

for section in "${REQUIRED_SECTIONS[@]}"; do
  # 檢查區塊標題是否存在
  if grep -q "## $section" "$SPEC_FILE"; then
    # 檢查區塊內容長度 (P1 改進)
    # 計算該 Section 標題後，直到下一個標題或檔尾的行數
    # 排除空行
    SECTION_CONTENT_LINES=$(sed -n "/## $section/,/^## /p" "$SPEC_FILE" | grep -v "^##" | grep -v "^$" | wc -l)
    
    # 至少要有 1 行實質內容
    if [ "$SECTION_CONTENT_LINES" -ge 1 ]; then
      echo "  ✅ Found: $section ($SECTION_CONTENT_LINES lines)"
    else
      echo "  ⚠️  Empty: $section (exists but has no content)"
      EMPTY_COUNT=$((EMPTY_COUNT + 1))
    fi
  else
    echo "  ❌ Missing: $section"
    MISSING_COUNT=$((MISSING_COUNT + 1))
  fi
done

echo ""

if [ $MISSING_COUNT -eq 0 ] && [ $EMPTY_COUNT -eq 0 ]; then
  echo "✅ Spec validation passed ($MODE mode)"
  exit 0
elif [ $MISSING_COUNT -gt 0 ]; then
  echo "❌ Spec validation failed: $MISSING_COUNT missing section(s)"
  exit 1
else 
  echo "❌ Spec validation failed: $EMPTY_COUNT empty section(s)"
  exit 1
fi
