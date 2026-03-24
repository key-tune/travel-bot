"""Smart listener — natural language interface for all bot features."""

import logging
import re

import discord
from discord.ext import commands

from config import COLOUR_AI
from services.claude_service import ClaudeService
from database import get_db

log = logging.getLogger(__name__)

# Channels where the bot actively listens
LISTEN_CHANNELS = {
    "日程調整", "フライト", "ホテル", "旅程プラン",
    "予算相談", "観光スポット", "グルメ", "ショッピング",
    "ai質問", "bot-commands", "雑談", "一般",
    "機能要望", "バグ報告", "開発ログ", "渡航情報",
    "claude-direct",
}

# Intent detection keywords
RESEARCH_KEYWORDS = ["調べて", "調査", "リサーチ", "検索して", "探して", "比較して", "おすすめ教えて"]
HOTEL_KEYWORDS = ["ホテル", "宿", "リゾート", "泊まる", "宿泊"]
ACTIVITY_KEYWORDS = ["アクティビティ", "ツアー", "観光", "ダイビング", "シュノーケル", "ジンベエ", "アイランドホッピング"]
FOOD_KEYWORDS = ["レストラン", "飯", "ご飯", "食事", "グルメ", "レチョン", "シーフード", "食べ"]
FLIGHT_KEYWORDS = ["フライト", "便", "航空", "飛行機"]
BUDGET_KEYWORDS = ["割り勘", "精算", "経費", "いくら", "お金", "予算"]
SCHEDULE_KEYWORDS = ["スケジュール", "予定", "旅程", "日程"]
TRAVEL_INFO_KEYWORDS = ["渡航", "ビザ", "パスポート", "入国", "保険", "治安", "安全", "両替", "SIM", "持ち物", "緊急"]


def _detect_intent(text: str) -> str | None:
    """Detect what the user wants based on keywords."""
    text_lower = text.lower()
    has_research = any(k in text_lower for k in RESEARCH_KEYWORDS)

    if any(k in text_lower for k in HOTEL_KEYWORDS) and has_research:
        return "research_hotels"
    if any(k in text_lower for k in ACTIVITY_KEYWORDS) and has_research:
        return "research_activities"
    if any(k in text_lower for k in FOOD_KEYWORDS) and has_research:
        return "research_food"
    if any(k in text_lower for k in TRAVEL_INFO_KEYWORDS):
        return "travel_info"
    if any(k in text_lower for k in BUDGET_KEYWORDS):
        return "budget"
    if any(k in text_lower for k in SCHEDULE_KEYWORDS):
        return "schedule"
    if has_research:
        return "research_free"
    return None


class ListenerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.claude = ClaudeService()

    async def _build_context(self) -> str:
        """Build trip context from DB + web."""
        lines = [
            "旅行情報:",
            "- 日程: 2026年6月25日(木)〜6月28日(日) 3泊4日",
            "- 復路(6人): 6/28 CEB 04:30→NRT 10:40 セブパシフィック 5J5064 ¥39,420/人",
            "- 復路(1人): CEB→NGO 未手配",
            "- 往路: 6/25 午後以降発予定（未確定）",
            "- メンバー: わこ、えむら、はちが、みやばやし、くさま、まさたか、とおご",
            "- Webページ: https://orfevre.xyz/philippines/",
        ]
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM itinerary WHERE approved = 1 ORDER BY day_date, time_slot"
            )
            items = await cursor.fetchall()
            if items:
                lines.append("\n承認済み旅程:")
                for it in items:
                    lines.append(f"  {it['day_date']} {it['time_slot'] or ''} - {it['title']}")
        finally:
            await db.close()
        return "\n".join(lines)

    async def _handle_research(self, message: discord.Message, intent: str):
        """Handle research-type requests."""
        research_cog = self.bot.get_cog("ResearchCog")
        if not research_cog:
            await message.reply("リサーチ機能が利用できません")
            return

        async with message.channel.typing():
            if intent == "research_hotels":
                # Extract area if mentioned
                area = "マクタン島"
                if "セブシティ" in message.content or "市内" in message.content:
                    area = "セブシティ"
                elif "モアルボアル" in message.content:
                    area = "モアルボアル"
                report = await research_cog.research.research_hotels(area)
                title = f"🏨 {area} ホテル調査結果"
            elif intent == "research_activities":
                report = await research_cog.research.research_activities()
                title = "🏄 アクティビティ調査結果"
            elif intent == "research_food":
                report = await research_cog.research.research_restaurants()
                title = "🍽️ グルメ調査結果"
            else:
                report = await research_cog.research.research(message.content)
                title = "🔍 リサーチ結果"

            if len(report) > 4000:
                report = report[:4000] + "…"

            embed = discord.Embed(title=title, description=report, colour=COLOUR_AI)
            embed.set_footer(text="🔍 AI Web Research")
            await message.reply(embed=embed)

    async def _handle_budget(self, message: discord.Message):
        """Show budget info from web."""
        web_cog = self.bot.get_cog("WebSyncCog")
        if not web_cog:
            await message.reply("Web連携が利用できません")
            return

        async with message.channel.typing():
            try:
                expenses = await web_cog.web.get_expenses()
                settlements = await web_cog.web.get_settlements()

                if not expenses:
                    await message.reply("まだ経費が登録されていません。Webページから追加してね！\nhttps://orfevre.xyz/philippines/")
                    return

                from cogs.web_sync import MEMBER_NAMES
                lines = []
                total = 0
                for e in expenses:
                    symbol = "₱" if e.get("currency") == "PHP" else "¥"
                    lines.append(f"• {symbol}{e['amount']:,.0f} {e['title']} (立替: {e.get('paid_by_name', '?')})")
                    total += e["amount"]

                text = f"**経費合計: ¥{total:,.0f}** (1人あたり ¥{total/7:,.0f})\n\n"
                text += "\n".join(lines)

                settle_list = settlements.get("settlements", [])
                if settle_list:
                    text += "\n\n**💸 精算:**\n"
                    for s in settle_list:
                        f_name = MEMBER_NAMES.get(s["from"], s["from"])
                        t_name = MEMBER_NAMES.get(s["to"], s["to"])
                        text += f"• {f_name} → {t_name}: ¥{s['amount']:,}\n"

                await message.reply(text)
            except Exception as e:
                await message.reply(f"エラー: {e}")

    async def _handle_schedule(self, message: discord.Message):
        """Show schedule from web."""
        web_cog = self.bot.get_cog("WebSyncCog")
        if not web_cog:
            await message.reply("Web連携が利用できません")
            return

        async with message.channel.typing():
            try:
                schedule = await web_cog.web.get_schedule()
                if not schedule:
                    await message.reply("まだスケジュールがありません。Webページから追加してね！\nhttps://orfevre.xyz/philippines/")
                    return

                DAY_LABELS = {1: "6/25(木)", 2: "6/26(金)", 3: "6/27(土)", 4: "6/28(日)"}
                by_day: dict[int, list] = {}
                for item in schedule:
                    by_day.setdefault(item.get("day", 0), []).append(item)

                text = ""
                for day in sorted(by_day):
                    text += f"\n**{DAY_LABELS.get(day, f'Day{day}')}**\n"
                    for it in sorted(by_day[day], key=lambda x: x.get("time_slot", "")):
                        t = it.get("time_slot", "")
                        end = it.get("end_time", "")
                        time_str = f"{t}〜{end}" if end else t
                        text += f"• {time_str} {it['title']}\n"

                await message.reply(text)
            except Exception as e:
                await message.reply(f"エラー: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        channel_name = message.channel.name if hasattr(message.channel, 'name') else ""
        if channel_name not in LISTEN_CHANNELS:
            return

        content = message.content.strip()
        if not content:
            return

        # claude-direct is handled by MCP Channels (Opus), not this bot
        if channel_name == "claude-direct":
            return

        bot_mentioned = self.bot.user in message.mentions if self.bot.user else False
        has_bot_keyword = "bot" in content.lower() or "ボット" in content or "ぼっと" in content

        if not bot_mentioned and not has_bot_keyword:
            return

        # Clean up message
        if self.bot.user:
            content = content.replace(f"<@{self.bot.user.id}>", "").strip()

        # Detect intent and route
        intent = _detect_intent(content)

        if intent and intent.startswith("research_"):
            await self._handle_research(message, intent)
        elif intent == "travel_info":
            await self._handle_research(message, "research_free")
        elif intent == "budget":
            await self._handle_budget(message)
        elif intent == "schedule":
            await self._handle_schedule(message)
        elif intent == "research_free":
            await self._handle_research(message, "research_free")
        else:
            # Default: Claude AI conversation
            async with message.channel.typing():
                recent = []
                async for msg in message.channel.history(limit=6):
                    if msg.id != message.id and not msg.author.bot:
                        recent.append(f"{msg.author.display_name}: {msg.content}")
                recent.reverse()

                channel_context = "\n".join(recent[-5:]) if recent else ""
                trip_context = await self._build_context()

                full_context = trip_context
                if channel_context:
                    full_context += f"\n\nチャンネル「{channel_name}」の最近の会話:\n{channel_context}"

                answer = await self.claude.ask(content, full_context)

                if len(answer) > 2000:
                    answer = answer[:2000] + "…"

                await message.reply(answer)


async def setup(bot: commands.Bot):
    await bot.add_cog(ListenerCog(bot))
