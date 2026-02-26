"""
使用 text-embedding-3-large 將文字轉換成向量。
由 ADR-001 決定使用此模型。

來源：第六章 — 調用 OpenAI Embedding API
"""

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils import PreconditionError, PostconditionError


class OpenAIEmbedder:
    """
    使用 text-embedding-3-large 將文字轉換成向量。
    由 ADR-001 決定使用此模型。
    """

    MODEL = "text-embedding-3-large"  # Constitution INV-6：不可在 code 中硬改

    def __init__(self) -> None:
        self.client = openai.OpenAI()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
    )
    def embed(self, text: str) -> list[float]:
        """
        將單一文字嵌入為向量。

        Precondition: len(text.strip()) > 0（不嵌入空文字）
        Postcondition: len(result) == 1536（text-embedding-3-large 的維度）
        """
        if not text.strip():
            raise PreconditionError("不得嵌入空文字（違反 INV-1）")

        response = self.client.embeddings.create(
            model=self.MODEL,
            input=text,
        )
        vector = response.data[0].embedding
        if len(vector) != 1536:
            raise PostconditionError(f"預期 1536 維，得到 {len(vector)} 維")
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批次嵌入（最多 100 個）。
        使用批次 API 降低呼叫次數，節省 token 用量。
        """
        # 過濾空白文字
        valid_texts = [t for t in texts if t.strip()]
        if len(valid_texts) != len(texts):
            raise PreconditionError(
                f"批次中有 {len(texts) - len(valid_texts)} 個空白文字"
            )

        if len(texts) > 100:
            raise PreconditionError("單次批次最多 100 個文字（API 限制）")

        response = self.client.embeddings.create(
            model=self.MODEL,
            input=valid_texts,
        )
        return [item.embedding for item in response.data]
