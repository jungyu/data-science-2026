from __future__ import annotations


SYNTHESIS_PROMPT = """你現在扮演 skill：

{skill_name}

## Skill Instructions

{skill_system_prompt}

## User Message

{user_input}

## Recent Conversation

{recent_history}

## Emotion State

{emotion_state}

## Response Mode

{response_mode}

## RAG Context

{rag_context}

## Response Rules

1. 若 RAG Context 有資料，優先引用其內容。
2. 若 RAG Context 不足，明確說明「目前知識庫沒有足夠資料」。
3. 不要假裝查到了沒有查到的東西。
4. 回答要符合 response_mode：
   - brief：短答
   - structured：結構化說明
   - step_by_step：逐步教學
   - decision_support：決策表與風險
   - debugging：問題定位與修復步驟
   - reflection：整理思緒與下一步
5. 若 emotion_state 是 anxious / frustrated：
   - 先降低認知負荷
   - 不要一次丟太多選項
   - 給出一個最小下一步
6. 適合 LINE 閱讀：
   - 段落短
   - 標題清楚
   - 不要過長
"""


def render_synthesis_prompt(
    *,
    skill_name: str,
    skill_system_prompt: str,
    user_input: str,
    recent_history: str,
    emotion_state: str,
    response_mode: str,
    rag_context: str,
) -> str:
    return SYNTHESIS_PROMPT.format(
        skill_name=skill_name,
        skill_system_prompt=skill_system_prompt.strip(),
        user_input=user_input.strip(),
        recent_history=recent_history.strip(),
        emotion_state=emotion_state,
        response_mode=response_mode,
        rag_context=rag_context.strip(),
    )
