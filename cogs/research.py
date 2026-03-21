"""AI Research cog — deep travel research with web search + Claude analysis."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_AI
from services.research_service import ResearchService

log = logging.getLogger(__name__)


class ResearchCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.research = ResearchService()

    async def cog_unload(self):
        await self.research.close()

    async def _send_report(self, interaction: discord.Interaction, title: str, report: str):
        """Send a potentially long report split across embeds."""
        # Discord embed description limit is 4096 chars
        chunks = []
        while report:
            if len(report) <= 4000:
                chunks.append(report)
                break
            # Find a good split point
            split_at = report.rfind("\n", 0, 4000)
            if split_at == -1:
                split_at = 4000
            chunks.append(report[:split_at])
            report = report[split_at:].lstrip()

        embeds = []
        for i, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=title if i == 0 else f"{title} (続き {i+1})",
                description=chunk,
                colour=COLOUR_AI,
            )
            if i == 0:
                embed.set_footer(text="🔍 AI Web Research — 検索結果に基づく分析レポート")
            embeds.append(embed)

        await interaction.followup.send(embeds=embeds[:10])  # Discord max 10 embeds

    @app_commands.command(name="research", description="AIがWebを検索して旅行情報を徹底リサーチ")
    @app_commands.describe(topic="調べたいこと（自由入力）")
    async def research_cmd(
        self,
        interaction: discord.Interaction,
        topic: str,
    ):
        await interaction.response.defer()
        report = await self.research.research(topic)
        await self._send_report(interaction, f"🔍 リサーチ: {topic[:50]}", report)

    @app_commands.command(name="research-hotels", description="ホテルを徹底リサーチ（部屋プラン・料金比較）")
    @app_commands.describe(area="エリア（デフォルト: マクタン島）")
    @app_commands.choices(
        area=[
            app_commands.Choice(name="マクタン島", value="マクタン島"),
            app_commands.Choice(name="セブシティ", value="セブシティ"),
            app_commands.Choice(name="モアルボアル", value="モアルボアル"),
            app_commands.Choice(name="オスロブ", value="オスロブ"),
        ]
    )
    async def research_hotels(
        self,
        interaction: discord.Interaction,
        area: str = "マクタン島",
    ):
        await interaction.response.defer()
        report = await self.research.research_hotels(area)
        await self._send_report(interaction, f"🏨 ホテルリサーチ: {area}", report)

    @app_commands.command(name="research-activities", description="アクティビティ・ツアーを徹底リサーチ")
    async def research_activities(self, interaction: discord.Interaction):
        await interaction.response.defer()
        report = await self.research.research_activities()
        await self._send_report(interaction, "🏄 アクティビティリサーチ", report)

    @app_commands.command(name="research-food", description="レストラン・グルメを徹底リサーチ")
    async def research_food(self, interaction: discord.Interaction):
        await interaction.response.defer()
        report = await self.research.research_restaurants()
        await self._send_report(interaction, "🍽️ グルメリサーチ", report)


async def setup(bot: commands.Bot):
    await bot.add_cog(ResearchCog(bot))
