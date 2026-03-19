"""Dashboard cog — overall trip summary."""

import json
import logging
from collections import defaultdict

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_DASH, GROUP_SIZE
from database import get_db

log = logging.getLogger(__name__)


class DashboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="dashboard", description="旅行計画の全体サマリー")
    async def dashboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        db = await get_db()

        try:
            embeds = []

            # ── Header ──
            header = discord.Embed(
                title="🏝️ セブ旅行ダッシュボード",
                description=f"👥 {GROUP_SIZE}人グループ",
                colour=COLOUR_DASH,
            )

            # ── Flight monitor status ──
            cursor = await db.execute(
                "SELECT * FROM monitor_routes WHERE active = 1"
            )
            routes = await cursor.fetchall()
            if routes:
                flight_lines = []
                for r in routes:
                    route_key = f"{r['origin']}-{r['destination']}"
                    c2 = await db.execute(
                        "SELECT MIN(price) as best FROM price_snapshots WHERE route = ?",
                        (route_key,),
                    )
                    row = await c2.fetchone()
                    best = f"¥{row['best']:,.0f}" if row and row["best"] else "データなし"
                    flight_lines.append(f"✈️ {route_key} ({r['date_from']}): {best}")
                header.add_field(
                    name="📊 フライト監視",
                    value="\n".join(flight_lines),
                    inline=False,
                )
            else:
                header.add_field(
                    name="📊 フライト監視",
                    value="未設定 — `/monitor start` で開始",
                    inline=False,
                )

            # ── Top hotels ──
            cursor = await db.execute(
                """SELECT h.name, COALESCE(SUM(hv.vote),0) as score, h.price_per_night
                   FROM hotels h LEFT JOIN hotel_votes hv ON h.id = hv.hotel_id
                   GROUP BY h.id ORDER BY score DESC LIMIT 3"""
            )
            hotels = await cursor.fetchall()
            if hotels:
                hotel_lines = []
                for h in hotels:
                    icon = '🏆' if h['score'] > 0 else '🏨'
                    price_str = f"¥{h['price_per_night']:,.0f}" if h['price_per_night'] else ''
                    hotel_lines.append(f"{icon} {h['name']} [{h['score']:+d}票] {price_str}")
                header.add_field(
                    name="🏨 トップホテル",
                    value="\n".join(hotel_lines),
                    inline=False,
                )

            # ── Itinerary summary ──
            cursor = await db.execute(
                """SELECT day_date, COUNT(*) as cnt,
                          SUM(CASE WHEN approved THEN 1 ELSE 0 END) as approved_cnt
                   FROM itinerary GROUP BY day_date ORDER BY day_date"""
            )
            days = await cursor.fetchall()
            if days:
                plan_lines = [
                    f"📅 {d['day_date']}: {d['approved_cnt']}✅/{d['cnt']}件"
                    for d in days
                ]
                header.add_field(
                    name="📋 旅程",
                    value="\n".join(plan_lines),
                    inline=False,
                )

            # ── Budget summary ──
            cursor = await db.execute(
                "SELECT SUM(amount) as total, COUNT(*) as cnt FROM expenses"
            )
            budget = await cursor.fetchone()
            if budget and budget["cnt"] > 0:
                per_person = (budget["total"] or 0) / GROUP_SIZE
                header.add_field(
                    name="💰 経費",
                    value=(
                        f"合計: ¥{budget['total']:,.0f}\n"
                        f"1人あたり: ¥{per_person:,.0f}\n"
                        f"{budget['cnt']}件登録"
                    ),
                    inline=False,
                )

            embeds.append(header)
            await interaction.followup.send(embeds=embeds)
        finally:
            await db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(DashboardCog(bot))
