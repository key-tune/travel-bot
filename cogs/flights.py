"""Flight search and monitor cog — powered by SerpApi (Google Flights)."""

import asyncio
import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_FLIGHT, MAIN_GROUP_SIZE, NGO_GROUP_SIZE
from services.serpapi_client import SerpApiClient
from services.price_monitor import PriceMonitor
from database import get_db

log = logging.getLogger(__name__)


def _format_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    return f"{h}時間{m}分" if m else f"{h}時間"


def _flight_embed(flights: list[dict], route: str, count: int, max_show: int = 5) -> discord.Embed:
    embed = discord.Embed(title=f"✈️ {route} — {count}人分", colour=COLOUR_FLIGHT)
    if not flights:
        embed.description = "該当フライトが見つかりませんでした"
        return embed

    for i, f in enumerate(flights[:max_show], 1):
        price = f["price"]
        if price is None:
            continue
        stops = "直行" if f["stops"] == 0 else f"経由{f['stops']}回"
        per_person = f"¥{price:,}"
        total = f"¥{price * count:,}"
        duration = _format_duration(f["duration"]) if f["duration"] else "?"

        embed.add_field(
            name=f"{i}. {f['airline']} — {per_person}/人 ({total}合計)",
            value=(
                f"🕐 {f['departure_time']} → {f['arrival_time']}\n"
                f"⏱️ {duration}  |  {stops}"
            ),
            inline=False,
        )
    return embed


class FlightsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.serpapi = SerpApiClient()
        self.monitor = PriceMonitor(bot)

    async def cog_unload(self):
        await self.serpapi.close()

    @app_commands.command(name="flights", description="フライト検索（往路・復路対応）")
    @app_commands.describe(
        date="出発日 (YYYY-MM-DD)",
        direction="往路(日本→セブ) or 復路(セブ→日本)",
        max_results="表示件数 (デフォルト5)",
    )
    @app_commands.choices(
        direction=[
            app_commands.Choice(name="往路（日本→セブ）", value="outbound"),
            app_commands.Choice(name="復路（セブ→日本）", value="return"),
        ]
    )
    async def flights(
        self,
        interaction: discord.Interaction,
        date: str,
        direction: str = "outbound",
        max_results: int = 5,
    ):
        await interaction.response.defer()

        if direction == "outbound":
            # 往路: NRT→CEB, HND→CEB, NGO→CEB
            nrt_task = self.serpapi.search_flights("NRT", "CEB", date)
            hnd_task = self.serpapi.search_flights("HND", "CEB", date)
            ngo_task = self.serpapi.search_flights("NGO", "CEB", date)

            nrt_data, hnd_data, ngo_data = await asyncio.gather(nrt_task, hnd_task, ngo_task)

            nrt_flights = self.serpapi.parse_flights(nrt_data)[:max_results]
            hnd_flights = self.serpapi.parse_flights(hnd_data)[:max_results]
            ngo_flights = self.serpapi.parse_flights(ngo_data)[:max_results]

            all_main = [(f, "NRT→CEB") for f in nrt_flights] + [(f, "HND→CEB") for f in hnd_flights]
            all_main = [(f, r) for f, r in all_main if f["price"] is not None]
            all_main.sort(key=lambda x: x[0]["price"])

            embeds = []
            if all_main:
                best, best_route = all_main[0]
                header = discord.Embed(
                    title=f"🏆 6人グループ最安（往路）: {best_route}",
                    colour=COLOUR_FLIGHT,
                )
                header.description = (
                    f"💰 **¥{best['price']:,}/人** (合計 ¥{best['price'] * MAIN_GROUP_SIZE:,})\n"
                    f"✈️ {best['airline']}  |  {best['departure_time']} → {best['arrival_time']}"
                )
                embeds.append(header)

            embeds.append(_flight_embed(nrt_flights, "NRT→CEB", MAIN_GROUP_SIZE, max_results))
            embeds.append(_flight_embed(hnd_flights, "HND→CEB", MAIN_GROUP_SIZE, max_results))
            embeds.append(_flight_embed(ngo_flights, "NGO→CEB", NGO_GROUP_SIZE, max_results))

        else:
            # 復路: CEB→NRT, CEB→HND, CEB→NGO
            nrt_task = self.serpapi.search_flights("CEB", "NRT", date)
            hnd_task = self.serpapi.search_flights("CEB", "HND", date)
            ngo_task = self.serpapi.search_flights("CEB", "NGO", date)

            nrt_data, hnd_data, ngo_data = await asyncio.gather(nrt_task, hnd_task, ngo_task)

            nrt_flights = self.serpapi.parse_flights(nrt_data)[:max_results]
            hnd_flights = self.serpapi.parse_flights(hnd_data)[:max_results]
            ngo_flights = self.serpapi.parse_flights(ngo_data)[:max_results]

            all_main = [(f, "CEB→NRT") for f in nrt_flights] + [(f, "CEB→HND") for f in hnd_flights]
            all_main = [(f, r) for f, r in all_main if f["price"] is not None]
            all_main.sort(key=lambda x: x[0]["price"])

            embeds = []
            if all_main:
                best, best_route = all_main[0]
                header = discord.Embed(
                    title=f"🏆 6人グループ最安（復路）: {best_route}",
                    colour=COLOUR_FLIGHT,
                )
                header.description = (
                    f"💰 **¥{best['price']:,}/人** (合計 ¥{best['price'] * MAIN_GROUP_SIZE:,})\n"
                    f"✈️ {best['airline']}  |  {best['departure_time']} → {best['arrival_time']}"
                )
                embeds.append(header)

            embeds.append(_flight_embed(nrt_flights, "CEB→NRT", MAIN_GROUP_SIZE, max_results))
            embeds.append(_flight_embed(hnd_flights, "CEB→HND", MAIN_GROUP_SIZE, max_results))
            embeds.append(_flight_embed(ngo_flights, "CEB→NGO", NGO_GROUP_SIZE, max_results))

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

                routes = [("CEB", "NRT"), ("CEB", "HND"), ("CEB", "NGO")]
                for orig, dest in routes:
                    await db.execute(
                        """INSERT INTO monitor_routes (origin, destination, date_from, channel_id)
                           VALUES (?, ?, ?, ?)""",
                        (orig, dest, date, str(interaction.channel_id)),
                    )
                await db.commit()

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
                cursor = await db.execute("SELECT * FROM monitor_routes WHERE active = 1")
                routes = await cursor.fetchall()
                if not routes:
                    await interaction.followup.send("📊 アクティブな監視ルートはありません")
                    return

                embed = discord.Embed(title="📊 価格監視ステータス", colour=COLOUR_FLIGHT)
                for r in routes:
                    cursor2 = await db.execute(
                        """SELECT MIN(price) as min_p, MAX(price) as max_p, COUNT(*) as cnt
                           FROM price_snapshots WHERE route = ? AND date = ?""",
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
