"""AI travel assistant cog using Claude."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_AI
from services.claude_service import ClaudeService
from database import get_db

log = logging.getLogger(__name__)


class AskCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.claude = ClaudeService()

    async def _build_context(self) -> str:
        """Build trip context from DB for Claude."""
        lines = []
        db = await get_db()
        try:
            # Itinerary
            cursor = await db.execute(
                "SELECT * FROM itinerary WHERE approved = 1 ORDER BY day_date, time_slot"
            )
            items = await cursor.fetchall()
            if items:
                lines.append("承認済み旅程:")
                for it in items:
                    lines.append(f"  {it['day_date']} {it['time_slot'] or ''} - {it['title']}: {it['description'] or ''}")

            # Hotels
            cursor = await db.execute(
                """SELECT h.*, COALESCE(SUM(hv.vote),0) as score
                   FROM hotels h LEFT JOIN hotel_votes hv ON h.id = hv.hotel_id
                   GROUP BY h.id ORDER BY score DESC LIMIT 5"""
            )
            hotels = await cursor.fetchall()
            if hotels:
                lines.append("\nお気に入りホテル:")
                for h in hotels:
                    lines.append(f"  {h['name']} ({h['area'] or '?'}) - ¥{h['price_per_night'] or '?'}/泊 [スコア:{h['score']}]")

            # Budget
            cursor = await db.execute("SELECT SUM(amount) as total FROM expenses")
            row = await cursor.fetchone()
            if row and row["total"]:
                lines.append(f"\n現在の経費合計: ¥{row['total']:,.0f}")
        finally:
            await db.close()

        return "\n".join(lines)

    @app_commands.command(name="ask", description="AIに旅行の質問をする")
    @app_commands.describe(question="質問内容")
    async def ask(self, interaction: discord.Interaction, question: str):
        await interaction.response.defer()

        context = await self._build_context()
        answer = await self.claude.ask(question, context)

        # Discord has 4096 char limit for embed description
        if len(answer) > 4000:
            answer = answer[:4000] + "…"

        embed = discord.Embed(
            title="🤖 AI旅行アシスタント",
            description=answer,
            colour=COLOUR_AI,
        )
        embed.set_footer(text=f"Q: {question[:100]}")

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AskCog(bot))
