"""Interactive menu cog — button-based UI for non-technical users."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_DASH, WEB_URL

log = logging.getLogger(__name__)


class MainMenuView(discord.ui.View):
    @discord.ui.button(label="✈️ フライト検索", style=discord.ButtonStyle.primary, row=0)
    async def flights(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = FlightDateView(self.bot)
        await interaction.response.send_message(
            "📅 いつのフライトを検索する？", view=view, ephemeral=True
        )

    @discord.ui.button(label="🏨 ホテル調査", style=discord.ButtonStyle.primary, row=0)
    async def hotels(self, interaction: discord.Interaction, button: discord.ui.Button):
        view = HotelAreaView(self.bot)
        await interaction.response.send_message(
            "🏨 どのエリアのホテルを調べる？", view=view, ephemeral=True
        )

    @discord.ui.button(label="🏄 アクティビティ", style=discord.ButtonStyle.primary, row=0)
    async def activities(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        research_cog = self.bot.get_cog("ResearchCog")
        if research_cog:
            report = await research_cog.research.research_activities()
            if len(report) > 4000:
                report = report[:4000] + "…"
            embed = discord.Embed(title="🏄 アクティビティ調査結果", description=report, colour=COLOUR_DASH)
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send("❌ リサーチ機能が利用できません", ephemeral=True)

    @discord.ui.button(label="🍽️ グルメ調査", style=discord.ButtonStyle.primary, row=1)
    async def food(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        research_cog = self.bot.get_cog("ResearchCog")
        if research_cog:
            report = await research_cog.research.research_restaurants()
            if len(report) > 4000:
                report = report[:4000] + "…"
            embed = discord.Embed(title="🍽️ グルメ調査結果", description=report, colour=COLOUR_DASH)
            await interaction.followup.send(embed=embed, ephemeral=False)
        else:
            await interaction.followup.send("❌ リサーチ機能が利用できません", ephemeral=True)

    @discord.ui.button(label="💰 割り勘確認", style=discord.ButtonStyle.success, row=1)
    async def budget(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        web_cog = self.bot.get_cog("WebSyncCog")
        if web_cog:
            # Reuse web_expenses logic
            try:
                expenses = await web_cog.web.get_expenses()
                settlements = await web_cog.web.get_settlements()

                embed = discord.Embed(title="💰 割り勘状況", colour=COLOUR_DASH)
                if expenses:
                    lines = []
                    for e in expenses:
                        symbol = "₱" if e.get("currency") == "PHP" else "¥"
                        lines.append(f"{symbol}{e['amount']:,.0f} {e['title']} (立替: {e.get('paid_by_name', '?')})")
                    embed.add_field(name="経費一覧", value="\n".join(lines), inline=False)

                settle_list = settlements.get("settlements", [])
                if settle_list:
                    from cogs.web_sync import MEMBER_NAMES
                    settle_lines = [
                        f"{MEMBER_NAMES.get(s['from'], s['from'])} → {MEMBER_NAMES.get(s['to'], s['to'])}: **¥{s['amount']:,}**"
                        for s in settle_list
                    ]
                    embed.add_field(name="💸 精算", value="\n".join(settle_lines), inline=False)

                embed.set_footer(text=f"🔗 {WEB_URL}")
                await interaction.followup.send(embed=embed)
            except Exception as e:
                await interaction.followup.send(f"❌ エラー: {e}", ephemeral=True)
        else:
            await interaction.followup.send("❌ Web連携が利用できません", ephemeral=True)

    @discord.ui.button(label="📊 ダッシュボード", style=discord.ButtonStyle.secondary, row=1)
    async def dashboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        dash_cog = self.bot.get_cog("DashboardCog")
        if dash_cog:
            # Trigger dashboard command
            await dash_cog.dashboard.callback(dash_cog, interaction)
        else:
            await interaction.followup.send("❌ ダッシュボードが利用できません", ephemeral=True)

    # Link button added in __init__ since decorators don't support url param
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(discord.ui.Button(label="🌐 Webページを開く", style=discord.ButtonStyle.link, url=WEB_URL, row=2))


class FlightDateView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)
        self.bot = bot

    @discord.ui.button(label="6/25 (往路)", style=discord.ButtonStyle.primary)
    async def day1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._search(interaction, "2026-06-25", "outbound")

    @discord.ui.button(label="6/26", style=discord.ButtonStyle.secondary)
    async def day2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._search(interaction, "2026-06-26", "outbound")

    @discord.ui.button(label="6/27", style=discord.ButtonStyle.secondary)
    async def day3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._search(interaction, "2026-06-27", "return")

    @discord.ui.button(label="6/28 (復路)", style=discord.ButtonStyle.primary)
    async def day4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._search(interaction, "2026-06-28", "return")

    async def _search(self, interaction: discord.Interaction, date: str, direction: str):
        await interaction.response.defer()
        flights_cog = self.bot.get_cog("FlightsCog")
        if flights_cog:
            # Create a fake interaction-like call
            import asyncio
            from services.serpapi_client import SerpApiClient
            from config import MAIN_GROUP_SIZE, NGO_GROUP_SIZE, COLOUR_FLIGHT

            serpapi = flights_cog.serpapi

            if direction == "outbound":
                routes = [("NRT", "CEB"), ("HND", "CEB"), ("NGO", "CEB")]
                labels = ["NRT→CEB", "HND→CEB", "NGO→CEB"]
            else:
                routes = [("CEB", "NRT"), ("CEB", "HND"), ("CEB", "NGO")]
                labels = ["CEB→NRT", "CEB→HND", "CEB→NGO"]

            tasks = [serpapi.search_flights(o, d, date) for o, d in routes]
            results = await asyncio.gather(*tasks)

            from cogs.flights import _flight_embed
            embeds = []
            for data, label in zip(results, labels):
                flights = serpapi.parse_flights(data)[:5]
                count = NGO_GROUP_SIZE if "NGO" in label else MAIN_GROUP_SIZE
                embeds.append(_flight_embed(flights, label, count))

            await interaction.followup.send(embeds=embeds)
        else:
            await interaction.followup.send("❌ フライト検索が利用できません")


class HotelAreaView(discord.ui.View):
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=60)
        self.bot = bot

    @discord.ui.button(label="🏝️ マクタン島", style=discord.ButtonStyle.primary)
    async def mactan(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._research(interaction, "マクタン島")

    @discord.ui.button(label="🏙️ セブシティ", style=discord.ButtonStyle.secondary)
    async def cebu_city(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._research(interaction, "セブシティ")

    @discord.ui.button(label="🌴 リゾート", style=discord.ButtonStyle.success)
    async def resort(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._research(interaction, "リゾートエリア")

    async def _research(self, interaction: discord.Interaction, area: str):
        await interaction.response.defer()
        research_cog = self.bot.get_cog("ResearchCog")
        if research_cog:
            report = await research_cog.research.research_hotels(area)
            if len(report) > 4000:
                report = report[:4000] + "…"
            embed = discord.Embed(
                title=f"🏨 {area} ホテル調査結果",
                description=report,
                colour=COLOUR_DASH,
            )
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ リサーチ機能が利用できません")


class MenuCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="menu", description="メインメニューを表示")
    async def menu(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🏝️ セブ旅行Bot メニュー",
            description=(
                "ボタンを押すだけで使えます！\n"
                "または、このチャンネルで日本語で話しかけてもOK。\n\n"
                "例: 「マクタンのおすすめホテル教えて？」"
            ),
            colour=COLOUR_DASH,
        )
        embed.add_field(
            name="📅 旅行日程",
            value="6/25 (木) → 6/28 (日) 3泊4日",
            inline=True,
        )
        embed.add_field(
            name="👥 メンバー",
            value="7人",
            inline=True,
        )
        view = MainMenuView(self.bot)
        await interaction.response.send_message(embed=embed, view=view)


async def setup(bot: commands.Bot):
    await bot.add_cog(MenuCog(bot))
