"""Itinerary planner and voting cog."""

import logging
import math

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_PLAN, GROUP_SIZE
from database import get_db

log = logging.getLogger(__name__)

APPROVAL_THRESHOLD = math.ceil(GROUP_SIZE / 2)  # 4 of 7


class PlanVoteView(discord.ui.View):
    def __init__(self, item_id: int):
        super().__init__(timeout=None)
        self.item_id = item_id

    @discord.ui.button(label="賛成 ✅", style=discord.ButtonStyle.success, custom_id="plan_approve")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._vote(interaction, 1)

    @discord.ui.button(label="反対 ❌", style=discord.ButtonStyle.danger, custom_id="plan_reject")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._vote(interaction, -1)

    async def _vote(self, interaction: discord.Interaction, vote: int):
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO itinerary_votes (item_id, user_id, vote)
                   VALUES (?, ?, ?)
                   ON CONFLICT(item_id, user_id) DO UPDATE SET vote = excluded.vote""",
                (self.item_id, str(interaction.user.id), vote),
            )

            cursor = await db.execute(
                "SELECT SUM(CASE WHEN vote > 0 THEN 1 ELSE 0 END) as yes_count FROM itinerary_votes WHERE item_id = ?",
                (self.item_id,),
            )
            row = await cursor.fetchone()
            yes_count = row["yes_count"] or 0

            # Auto-approve if majority
            if yes_count >= APPROVAL_THRESHOLD:
                await db.execute(
                    "UPDATE itinerary SET approved = 1 WHERE id = ?",
                    (self.item_id,),
                )

            await db.commit()

            status = f"✅ 承認済み ({yes_count}/{GROUP_SIZE})" if yes_count >= APPROVAL_THRESHOLD else f"投票: {yes_count}/{APPROVAL_THRESHOLD}必要"
            await interaction.response.send_message(
                f"{'賛成' if vote > 0 else '反対'}しました！ {status}",
                ephemeral=True,
            )
        finally:
            await db.close()


class PlannerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="plan", description="旅程にアクティビティを追加")
    @app_commands.describe(
        date="日付 (YYYY-MM-DD)",
        time="時間帯 (例: 09:00, 午後)",
        title="アクティビティ名",
        description="詳細",
        category="カテゴリ: food / activity / transport / shopping / other",
    )
    async def plan(
        self,
        interaction: discord.Interaction,
        date: str,
        title: str,
        time: str = "",
        description: str = "",
        category: str = "other",
    ):
        db = await get_db()
        try:
            cursor = await db.execute(
                """INSERT INTO itinerary (day_date, time_slot, title, description, category, added_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (date, time, title, description, category, str(interaction.user.id)),
            )
            await db.commit()
            item_id = cursor.lastrowid

            category_emoji = {
                "food": "🍽️", "activity": "🏄", "transport": "🚗",
                "shopping": "🛍️", "other": "📌",
            }
            emoji = category_emoji.get(category, "📌")

            embed = discord.Embed(
                title=f"{emoji} {title}",
                description=description or "詳細なし",
                colour=COLOUR_PLAN,
            )
            embed.add_field(name="📅 日付", value=date, inline=True)
            if time:
                embed.add_field(name="🕐 時間", value=time, inline=True)
            embed.add_field(name="カテゴリ", value=category, inline=True)
            embed.set_footer(text=f"投票で{APPROVAL_THRESHOLD}人以上の賛成で承認")

            view = PlanVoteView(item_id)
            await interaction.response.send_message(embed=embed, view=view)
        finally:
            await db.close()

    @app_commands.command(name="itinerary", description="旅程一覧を表示")
    @app_commands.describe(date="特定の日付で絞り込み (YYYY-MM-DD)")
    async def itinerary(self, interaction: discord.Interaction, date: str | None = None):
        db = await get_db()
        try:
            if date:
                cursor = await db.execute(
                    "SELECT * FROM itinerary WHERE day_date = ? ORDER BY time_slot",
                    (date,),
                )
            else:
                cursor = await db.execute(
                    "SELECT * FROM itinerary ORDER BY day_date, time_slot"
                )
            items = await cursor.fetchall()

            if not items:
                await interaction.response.send_message("まだ旅程がありません。`/plan` で追加！")
                return

            embed = discord.Embed(
                title=f"📋 旅程{'(' + date + ')' if date else '全体'}",
                colour=COLOUR_PLAN,
            )

            current_day = None
            for item in items:
                if item["day_date"] != current_day:
                    current_day = item["day_date"]
                    embed.add_field(
                        name=f"━━━ 📅 {current_day} ━━━",
                        value="\u200b",
                        inline=False,
                    )

                status = "✅" if item["approved"] else "🔘"
                time_str = f" {item['time_slot']}" if item["time_slot"] else ""
                embed.add_field(
                    name=f"{status}{time_str} {item['title']}",
                    value=item["description"] or "—",
                    inline=False,
                )

            await interaction.response.send_message(embed=embed)
        finally:
            await db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(PlannerCog(bot))
