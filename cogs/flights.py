"""Flight search and monitor cog."""

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import (
    COLOUR_FLIGHT,
    RETURN_ROUTES_MAIN,
    RETURN_ROUTE_NGO,
    MAIN_GROUP_SIZE,
    NGO_GROUP_SIZE,
)
from services.amadeus_client import AmadeusClient, FlightOffer
from services.price_monitor import PriceMonitor
from database import get_db

log = logging.getLogger(__name__)


def _flight_embed(offers: list[FlightOffer], route: str, count: int) -> discord.Embed:
    embed = discord.Embed(title=f"✈️ {route} — {count}人分", colour=COLOUR_FLIGHT)
    if not offers:
        embed.description = "該当フライトが見つかりませんでした"
        return embed

    for i, o in enumerate(offers[:5], 1):
        stops = "直行" if o.stops == 0 else f"経由{o.stops}回"
        per_person = f"¥{o.price:,.0f}"
        total = f"¥{o.price * count:,.0f}"
        embed.add_field(
            name=f"{i}. {o.airline} — {per_person}/人 ({total}合計)",
            value=(
                f"🕐 {o.departure[:16]} → {o.arrival[:16]}\n"
                f"⏱️ {o.duration}  |  {stops}"
            ),
            inline=False,
        )
    return embed


class FlightsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.amadeus = AmadeusClient()
        self.monitor = PriceMonitor(bot)

    async def cog_unload(self):
        await self.amadeus.close()

    @app_commands.command(name="flights", description="復路フライト検索（CEB→NRT/HND/NGO）")
    @app_commands.describe(
        date="出発日 (YYYY-MM-DD)",
        max_results="表示件数 (デフォルト5)",
    )
    async def flights(
        self,
        interaction: discord.Interaction,
        date: str,
        max_results: int = 5,
    ):
        await interaction.response.defer()

        # Search all 3 routes concurrently
        tasks = []
        for route in RETURN_ROUTES_MAIN:
            tasks.append(
                self.amadeus.search_flights(
                    route["origin"], route["destination"], date, max_results=max_results
                )
            )
        tasks.append(
            self.amadeus.search_flights(
                RETURN_ROUTE_NGO["origin"],
                RETURN_ROUTE_NGO["destination"],
                date,
                max_results=max_results,
            )
        )

        results = await asyncio.gather(*tasks)
        nrt_offers, hnd_offers, ngo_offers = results

        # Find cheapest for main group (NRT vs HND)
        all_main = []
        for o in nrt_offers:
            all_main.append(("CEB→NRT", o))
        for o in hnd_offers:
            all_main.append(("CEB→HND", o))
        all_main.sort(key=lambda x: x[1].price)

        embeds = []

        # Main group embed
        if all_main:
            best_route, best = all_main[0]
            main_embed = discord.Embed(
                title=f"👥 6人グループ最安: {best_route}",
                colour=COLOUR_FLIGHT,
            )
            main_embed.description = (
                f"💰 **¥{best.price:,.0f}/人** (合計 ¥{best.price * MAIN_GROUP_SIZE:,.0f})\n"
                f"✈️ {best.airline}  |  {best.departure[:16]}"
            )
            embeds.append(main_embed)

        embeds.append(_flight_embed(nrt_offers, "CEB→NRT", MAIN_GROUP_SIZE))
        embeds.append(_flight_embed(hnd_offers, "CEB→HND", MAIN_GROUP_SIZE))
        embeds.append(_flight_embed(ngo_offers, "CEB→NGO", NGO_GROUP_SIZE))

        await interaction.followup.send(embeds=embeds)

    @app_commands.command(name="monitor", description="価格監視の開始/停止")
    @app_commands.describe(
        action="start / stop / status",
        date="監視する出発日 (YYYY-MM-DD)",
    )
    @app_commands.choices(
        action=[
            app_commands.Choice(name="start", value="start"),
            app_commands.Choice(name="stop", value="stop"),
            app_commands.Choice(name="status", value="status"),
        ]
    )
    async def monitor_cmd(
        self,
        interaction: discord.Interaction,
        action: str,
        date: str | None = None,
    ):
        await interaction.response.defer()
        db = await get_db()

        try:
            if action == "start":
                if not date:
                    await interaction.followup.send("❌ 日付を指定してください (例: 2026-04-15)")
                    return

                routes = [
                    ("CEB", "NRT"),
                    ("CEB", "HND"),
                    ("CEB", "NGO"),
                ]
                for orig, dest in routes:
                    await db.execute(
                        """INSERT INTO monitor_routes (origin, destination, date_from, channel_id)
                           VALUES (?, ?, ?, ?)""",
                        (orig, dest, date, str(interaction.channel_id)),
                    )
                await db.commit()

                # Start scheduler if not running
                from apscheduler.schedulers.asyncio import AsyncIOScheduler
                if not hasattr(self.bot, "_price_scheduler"):
                    scheduler = AsyncIOScheduler()
                    scheduler.add_job(
                        self.monitor.run_check_and_notify,
                        "interval",
                        hours=6,
                        id="price_check",
                    )
                    scheduler.start()
                    self.bot._price_scheduler = scheduler

                await interaction.followup.send(
                    f"✅ 価格監視を開始しました\n"
                    f"📅 出発日: {date}\n"
                    f"🔄 CEB→NRT, CEB→HND, CEB→NGO を6時間ごとにチェック\n"
                    f"📢 このチャンネルにアラートを送信します"
                )

            elif action == "stop":
                await db.execute("UPDATE monitor_routes SET active = 0 WHERE active = 1")
                await db.commit()

                if hasattr(self.bot, "_price_scheduler"):
                    self.bot._price_scheduler.shutdown(wait=False)
                    del self.bot._price_scheduler

                await interaction.followup.send("⏹️ 価格監視を停止しました")

            elif action == "status":
                cursor = await db.execute(
                    "SELECT * FROM monitor_routes WHERE active = 1"
                )
                routes = await cursor.fetchall()

                if not routes:
                    await interaction.followup.send("📊 アクティブな監視ルートはありません")
                    return

                embed = discord.Embed(title="📊 価格監視ステータス", colour=COLOUR_FLIGHT)
                for r in routes:
                    cursor2 = await db.execute(
                        """SELECT MIN(price) as min_p, MAX(price) as max_p,
                                  COUNT(*) as cnt
                           FROM price_snapshots
                           WHERE route = ? AND date = ?""",
                        (f"{r['origin']}-{r['destination']}", r["date_from"]),
                    )
                    stats = await cursor2.fetchone()
                    info = f"📅 {r['date_from']}"
                    if stats and stats["cnt"] > 0:
                        info += (
                            f"\n💰 最安: ¥{stats['min_p']:,.0f}"
                            f"  |  最高: ¥{stats['max_p']:,.0f}"
                            f"  |  {stats['cnt']}回チェック"
                        )
                    else:
                        info += "\n⏳ データ収集中…"

                    embed.add_field(
                        name=f"{r['origin']}→{r['destination']}",
                        value=info,
                        inline=False,
                    )

                await interaction.followup.send(embed=embed)
        finally:
            await db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(FlightsCog(bot))
