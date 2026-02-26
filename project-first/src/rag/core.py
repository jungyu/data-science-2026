"""
RAG 核心函式：把問題和檢索到的文件片段一起送給 LLM。

來源：第一章 — RAG 的核心程式碼
"""

import os

import openai
from dotenv import load_dotenv

from src.config.llm_config import LLMConfig

load_dotenv()

client = openai.OpenAI()  # 從環境變數讀取 OPENAI_API_KEY


def rag_answer(
    question: str,
    retrieved_chunks: list[str],
    model: str = "gpt-4o",
    temperature: float = 0.1,
) -> str:
    """
    RAG 核心：把問題和檢索到的文件片段一起送給 LLM

    Args:
        question: 使用者的問題
        retrieved_chunks: 從向量資料庫檢索到的相關文件片段列表

    Returns:
        基於文件的回答
    """
    # Constitution Principle II：驗證 LLM 設定
    LLMConfig.validate(model=model, temperature=temperature)

    # 把多個文件片段合併成一個 context
    context = "\n\n---\n\n".join(retrieved_chunks)

    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是企業內部知識庫助手。"
                    "只根據以下提供的文件內容回答問題。"
                    "如果文件中沒有相關資訊，請明確說明「根據現有文件無法回答」，"
                    "不要自行推測或使用訓練資料填補。"
                    "回答時請引用文件來源。"
                ),
            },
            {
                "role": "user",
                "content": f"相關文件：\n{context}\n\n問題：{question}",
            },
        ],
        temperature=temperature,  # 低溫度 = 更保守、更確定的答案
    )

    return response.choices[0].message.content
