"""AI-powered travel research — web search + Claude analysis."""

import os
import logging

import httpx
import anthropic

log = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


class ResearchService:
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY", "")
        self.claude = anthropic.AsyncAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        )
        self._client = httpx.AsyncClient(timeout=30)

    async def web_search(self, query: str, num: int = 10, gl: str = "jp", hl: str = "ja") -> list[dict]:
        """Search Google via SerpApi and return organic results."""
        if not self.serpapi_key:
            return []

        params = {
            "engine": "google",
            "q": query,
            "num": num,
            "gl": gl,
            "hl": hl,
            "api_key": self.serpapi_key,
        }

        try:
            resp = await self._client.get(SERPAPI_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
            results = []
            for r in data.get("organic_results", []):
                results.append({
                    "title": r.get("title", ""),
                    "link": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                })
            return results
        except Exception as e:
            log.error("Web search failed: %s", e)
            return []

    async def research(self, topic: str, search_queries: list[str] | None = None) -> str:
        """
        Do deep research on a topic:
        1. Generate search queries if not provided
        2. Search the web
        3. Analyse results with Claude
        4. Return structured report
        """
        # Step 1: Generate search queries if needed
        if not search_queries:
            search_queries = await self._generate_queries(topic)

        # Step 2: Collect web results
        all_results = []
        for query in search_queries[:3]:  # Max 3 queries to save API calls
            results = await self.web_search(query)
            all_results.extend(results)

        # Step 3: Analyse with Claude
        report = await self._analyse(topic, all_results)
        return report

    async def _generate_queries(self, topic: str) -> list[str]:
        """Ask Claude to generate optimal search queries."""
        resp = await self.claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=300,
            system=(
                "あなたは旅行リサーチの専門家です。"
                "ユーザーのリクエストに対して、Google検索で最も有用な結果が得られる検索クエリを3つ生成してください。"
                "セブ旅行（2026年6月25-28日、7人グループ）に関するリサーチです。"
                "各クエリは1行ずつ、クエリのみを出力してください。"
            ),
            messages=[{"role": "user", "content": topic}],
        )
        text = resp.content[0].text
        queries = [line.strip() for line in text.strip().split("\n") if line.strip()]
        return queries[:3]

    async def _analyse(self, topic: str, search_results: list[dict]) -> str:
        """Analyse search results with Claude and produce a report."""
        if not search_results:
            return "検索結果が得られませんでした。別のキーワードで試してください。"

        # Format results for Claude
        results_text = ""
        for i, r in enumerate(search_results, 1):
            results_text += f"\n{i}. {r['title']}\n   URL: {r['link']}\n   {r['snippet']}\n"

        resp = await self.claude.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system="""\
あなたはフィリピン・セブ旅行のリサーチアシスタントです。
7人グループ（日本人）で2026年6月25-28日（3泊4日）のセブ旅行を計画中です。
復路は6/28 04:30発（早朝）のフライトが確定しています。

Web検索結果を分析して、具体的で実用的なレポートを作成してください。

重要なルール:
- 検索結果に書いてある情報だけを使う。推測や捏造は絶対にしない。
- 価格は検索結果に明記されている場合のみ記載。不明なら「要確認」と書く。
- 場所・アクセス方法は検索結果から確認できる範囲で。
- 7人グループに適しているかの判断
- URLの出典を明記
- 簡潔に。箇条書きを活用して読みやすくする。""",
            messages=[
                {
                    "role": "user",
                    "content": f"リサーチテーマ: {topic}\n\n以下はWeb検索結果です:\n{results_text}\n\nこれらの情報を分析して、具体的で実用的なレポートを作成してください。",
                },
            ],
        )
        return resp.content[0].text

    async def research_hotels(self, area: str = "マクタン島") -> str:
        """Specific hotel research with room plans and pricing."""
        queries = [
            f"セブ {area} ホテル 7人 部屋 おすすめ 2024 2025",
            f"Cebu {area} hotel group room rate booking",
            f"セブ {area} リゾートホテル 料金 比較 ツイン トリプル",
        ]
        return await self.research(
            f"セブ・{area}エリアのホテル（7人グループ向け、部屋構成・料金比較）",
            queries,
        )

    async def research_activities(self) -> str:
        """Research activities and tours with pricing."""
        queries = [
            "セブ アクティビティ ツアー 料金 2024 2025 おすすめ グループ",
            "Cebu island hopping whale shark tour price group",
            "セブ オスロブ ジンベエザメ アイランドホッピング 予約 料金",
        ]
        return await self.research(
            "セブのアクティビティ・ツアー（7人グループ向け、料金比較）",
            queries,
        )

    async def research_restaurants(self) -> str:
        """Research restaurants and food spots."""
        queries = [
            "セブ レストラン おすすめ グループ 予約 2024 2025",
            "Cebu best restaurants group dining Filipino food",
            "セブ マクタン レチョン シーフード レストラン 料金",
        ]
        return await self.research(
            "セブのレストラン・グルメ（7人グループ向け、予算・予約情報）",
            queries,
        )

    async def close(self):
        await self._client.aclose()
