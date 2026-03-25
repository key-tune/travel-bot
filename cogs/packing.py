"""Packing list cog — manage travel packing checklist via web app."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_DASH, WEB_URL
from services.web_client import WebClient

log = logging.getLogger(__name__)


class PackingCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.web = WebClient()

    async def cog_unload(self):
        await self.web.close()

    @app_commands.command(name="packing", description="持ち物リストを表示")
    async def packing(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            items = await self.web.get_packing()
            if not items:
                await interaction.followup.send(
                    f"持ち物リストがまだありません。`/packing-add` で追加するか、Webページから追加！\n{WEB_URL}"
                )
                return

            embed = discord.Embed(title="🧳 持ち物リスト", colour=COLOUR_DASH, url=WEB_URL)

            by_cat: dict[str, list] = {}
            for item in items:
                cat = item.get("category", "その他") or "その他"
                by_cat.setdefault(cat, []).append(item)

            for cat, cat_items in by_cat.items():
                lines = []
                for it in cat_items:
                    checked = it.get("checked", False)
                    icon = "✅" if checked else "⬜"
                    lines.append(f"{icon} {it.get('name', '?')}")
                embed.add_field(name=cat, value="\n".join(lines), inline=True)

            checked_count = sum(1 for i in items if i.get("checked"))
            embed.set_footer(text=f"チェック済み: {checked_count}/{len(items)} | {WEB_URL}")

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}")

    @app_commands.command(name="packing-add", description="持ち物を追加")
    @app_commands.describe(
        name="持ち物名",
        category="カテゴリ",
    )
    @app_commands.choices(
        category=[
            app_commands.Choice(name="貴重品", value="貴重品"),
            app_commands.Choice(name="衣類", value="衣類"),
            app_commands.Choice(name="日用品", value="日用品"),
            app_commands.Choice(name="電子機器", value="電子機器"),
            app_commands.Choice(name="薬・衛生", value="薬・衛生"),
            app_commands.Choice(name="その他", value="その他"),
        ]
    )
    async def packing_add(
        self,
        interaction: discord.Interaction,
        name: str,
        category: str = "その他",
    ):
        await interaction.response.defer()
        try:
            await self.web.add_packing(category=category, name=name)
            await interaction.followup.send(f"🧳 追加: **{name}** ({category}) → Webに反映済み")
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(PackingCog(bot))
