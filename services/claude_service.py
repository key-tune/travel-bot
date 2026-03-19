"""Claude AI assistant service for travel Q&A."""

import os
import logging

import anthropic

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたはフィリピン・セブ旅行の計画アシスタントです。
7人グループで旅行を計画中です。

旅行パラメータ:
- 行き先: セブ (CEB)
- 人数: 7人
- 往路: 確保済み（成田NRT→セブCEB）、1名はセントレアNGO発
- 復路（6人）: セブCEB → 成田NRT or 羽田HND
- 復路（1人）: セブCEB → セントレアNGO
- 帰国日: 未定

セブの観光地、レストラン、アクティビティ、文化、安全情報、
フライト情報、ホテル選びのアドバイスなど、旅行に関する質問に
日本語で答えてください。具体的で実用的なアドバイスを心がけてください。
"""


class ClaudeService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )

    async def ask(self, question: str, context: str = "") -> str:
        """Ask Claude a travel question."""
        messages = []
        if context:
            messages.append({"role": "user", "content": f"[旅程コンテキスト]\n{context}"})
            messages.append({"role": "assistant", "content": "了解しました。この旅程情報を踏まえて回答します。"})
        messages.append({"role": "user", "content": question})

        try:
            resp = await self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=messages,
            )
            return resp.content[0].text
        except Exception as e:
            log.exception("Claude API call failed")
            return f"エラーが発生しました: {e}"
