"""Message listener — responds to natural chat in channels."""

import logging

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
    "ai質問", "bot-commands", "雑談",
}


class ListenerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.claude = ClaudeService()

    async def _build_context(self) -> str:
        """Build trip context from DB."""
        lines = [
            "旅行情報:",
            "- 復路(6人): 6/28 CEB 04:30→NRT 10:40 セブパシフィック 5J5064 ¥39,420/人",
            "- 復路(1人): CEB→NGO 未手配",
            "- 往路: 6/25 午後以降発予定（未確定）",
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

            cursor = await db.execute(
                """SELECT h.name, COALESCE(SUM(hv.vote),0) as score
                   FROM hotels h LEFT JOIN hotel_votes hv ON h.id = hv.hotel_id
                   GROUP BY h.id ORDER BY score DESC LIMIT 3"""
            )
            hotels = await cursor.fetchall()
            if hotels:
                lines.append("\nお気に入りホテル:")
                for h in hotels:
                    lines.append(f"  {h['name']} [スコア:{h['score']}]")
        finally:
            await db.close()
        return "\n".join(lines)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Ignore bot messages
        if message.author.bot:
            return

        # Check if in a listened channel
        channel_name = message.channel.name if hasattr(message.channel, 'name') else ""
        if channel_name not in LISTEN_CHANNELS:
            return

        # Respond if bot is mentioned OR if in ai質問 channel
        bot_mentioned = self.bot.user in message.mentions if self.bot.user else False
        is_ai_channel = channel_name == "ai質問"

        if not bot_mentioned and not is_ai_channel:
            # In other channels, only respond to questions (ending with ？or ?)
            # or messages that mention the bot
            content = message.content.strip()
            if not (content.endswith("？") or content.endswith("?")):
                return

        # Show typing indicator
        async with message.channel.typing():
            # Get recent channel context (last 5 messages)
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

            question = message.content.replace(f"<@{self.bot.user.id}>", "").strip() if self.bot.user else message.content
            answer = await self.claude.ask(question, full_context)

            if len(answer) > 2000:
                answer = answer[:2000] + "…"

            await message.reply(answer)


async def setup(bot: commands.Bot):
    await bot.add_cog(ListenerCog(bot))
