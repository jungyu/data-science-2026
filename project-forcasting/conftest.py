"""pytest 全域設定。"""

import sys
from pathlib import Path

# 確保 src 模組可被匯入
sys.path.insert(0, str(Path(__file__).resolve().parent))
