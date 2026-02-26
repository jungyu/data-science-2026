"""
共用工具模組：提供各章節程式碼隱含依賴的工具函式和型別。
"""

import math
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Chunk 資料型別
# ---------------------------------------------------------------------------

@dataclass
class Chunk:
    """文件分塊的基本資料結構，供 chunker 和 retrieval 使用。"""
    text: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Token 操作（簡易實作，以空白字元分詞）
# ---------------------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    """將文字切分為 token 列表（以空白/標點為邊界的簡易分詞）。"""
    def _is_cjk(char: str) -> bool:
        code = ord(char)
        return (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0x20000 <= code <= 0x2A6DF
            or 0x2A700 <= code <= 0x2B73F
            or 0x2B740 <= code <= 0x2B81F
            or 0x2B820 <= code <= 0x2CEAF
            or 0xF900 <= code <= 0xFAFF
        )

    tokens: list[str] = []
    current = ""
    for char in text:
        if char in " \t\n\r":
            if current:
                tokens.append(current)
                current = ""
        elif _is_cjk(char):
            if current:
                tokens.append(current)
                current = ""
            tokens.append(char)
        elif char in "。！？，、；：「」『』（）【】":
            if current:
                tokens.append(current)
                current = ""
            tokens.append(char)
        else:
            current += char
    if current:
        tokens.append(current)
    return tokens


def detokenize(tokens: list[str]) -> str:
    """將 token 列表重新組合為文字。"""
    def _is_cjk_token(token: str) -> bool:
        if len(token) != 1:
            return False
        code = ord(token)
        return (
            0x4E00 <= code <= 0x9FFF
            or 0x3400 <= code <= 0x4DBF
            or 0x20000 <= code <= 0x2A6DF
            or 0x2A700 <= code <= 0x2B73F
            or 0x2B740 <= code <= 0x2B81F
            or 0x2B820 <= code <= 0x2CEAF
            or 0xF900 <= code <= 0xFAFF
        )

    if not tokens:
        return ""
    result = tokens[0]
    for token in tokens[1:]:
        if token in "。！？，、；：」』）】":
            result += token
        elif result and result[-1] in "「『（【":
            result += token
        elif _is_cjk_token(result[-1]) and _is_cjk_token(token):
            result += token
        else:
            result += " " + token
    return result


def get_last_n_tokens(text: str, n: int) -> str:
    """取得文字最後 n 個 token 並重組為字串。"""
    tokens = tokenize(text)
    return detokenize(tokens[-n:]) if len(tokens) > n else text


# ---------------------------------------------------------------------------
# 數學工具
# ---------------------------------------------------------------------------

def cosine_similarity(a: list[float], b: list[float]) -> float:
    """計算兩個向量的餘弦相似度。"""
    if len(a) != len(b):
        raise ValueError(f"向量維度不一致：{len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---------------------------------------------------------------------------
# 自訂例外
# ---------------------------------------------------------------------------

class PreconditionError(ValueError):
    """前置條件違反：呼叫端未滿足函式的輸入合約。"""


class PostconditionError(RuntimeError):
    """後置條件違反：函式執行結果未滿足預期的輸出合約。"""


class ConfigViolationError(RuntimeError):
    """設定違規：違反 Constitution 定義的硬性設定限制。"""


class IngestError(RuntimeError):
    """攝取錯誤：知識攝取過程中發生不可恢復的錯誤。"""


class IngestValidationError(ValueError):
    """攝取驗證錯誤：新版本的知識品質未達標。"""
