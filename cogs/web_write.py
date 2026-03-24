"""Write to web app from Discord — add wishes, todos, expenses."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_PLAN, COLOUR_BUDGET, WEB_URL
from services.web_client import WebClient

log = logging.getLogger(__name__)


class WebWriteCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.web = WebClient()

    async def cog_unload(self):
        await self.web.close()

    @app_commands.command(name="want", description="やりたいことをWebページに追加")
    @app_commands.describe(
        title="やりたいこと",
        description="詳細（任意）",
    )
    async def want(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str = "",
    ):
        await interaction.response.defer()
        try:
            result = await self.web.add_wish(title=title, description=description)
            embed = discord.Embed(
                title=f"💛 やりたいこと追加: {title}",
                description=description or "",
                colour=COLOUR_PLAN,
                url=WEB_URL,
            )
            embed.set_footer(text=f"Webページにも反映済み → {WEB_URL}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}")

    @app_commands.command(name="todo", description="TODOをWebページに追加")
    @app_commands.describe(
        title="やること",
    )
    async def todo(
        self,
        interaction: discord.Interaction,
        title: str,
    ):
        await interaction.response.defer()
        try:
            result = await self.web.add_todo(title=title)
            embed = discord.Embed(
                title=f"✅ TODO追加: {title}",
                colour=COLOUR_PLAN,
                url=WEB_URL,
            )
            embed.set_footer(text=f"Webページにも反映済み → {WEB_URL}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}")

    @app_commands.command(name="schedule-add", description="スケジュールをWebページに追加")
    @app_commands.describe(
        day="日目 (1=6/25, 2=6/26, 3=6/27, 4=6/28)",
        time="開始時間 (例: 09:00)",
        title="予定タイトル",
        end_time="終了時間 (例: 12:00)",
        description="詳細（任意）",
    )
    @app_commands.choices(
        day=[
            app_commands.Choice(name="Day1 6/25(木)", value=1),
            app_commands.Choice(name="Day2 6/26(金)", value=2),
            app_commands.Choice(name="Day3 6/27(土)", value=3),
            app_commands.Choice(name="Day4 6/28(日)", value=4),
        ]
    )
    async def schedule_add(
        self,
        interaction: discord.Interaction,
        day: int,
        time: str,
        title: str,
        end_time: str = "",
        description: str = "",
    ):
        await interaction.response.defer()
        all_members = "wako,emura,hachiga,miyabayashi,kusama,masataka,togo"
        DAY_LABELS = {1: "6/25(木)", 2: "6/26(金)", 3: "6/27(土)", 4: "6/28(日)"}
        try:
            result = await self.web.add_schedule(
                day=day, time_slot=time, title=title,
                end_time=end_time, description=description,
                members=all_members,
            )
            time_str = f"{time}〜{end_time}" if end_time else time
            embed = discord.Embed(
                title=f"📅 スケジュール追加: {title}",
                colour=COLOUR_PLAN,
                url=WEB_URL,
            )
            embed.add_field(name="日程", value=DAY_LABELS.get(day, f"Day{day}"), inline=True)
            embed.add_field(name="時間", value=time_str, inline=True)
            if description:
                embed.add_field(name="詳細", value=description, inline=False)
            embed.set_footer(text=f"Webページにも反映済み → {WEB_URL}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}")

    @app_commands.command(name="pay", description="経費をWebページに追加")
    @app_commands.describe(
        title="内容 (例: ホテル代)",
        amount="金額",
        paid_by="立替者のID (wako/emura/hachiga/miyabayashi/kusama/masataka/togo)",
        currency="通貨 (JPY or PHP)",
    )
    @app_commands.choices(
        currency=[
            app_commands.Choice(name="日本円 (JPY)", value="JPY"),
            app_commands.Choice(name="フィリピンペソ (PHP)", value="PHP"),
        ]
    )
    async def pay(
        self,
        interaction: discord.Interaction,
        title: str,
        amount: float,
        paid_by: str,
        currency: str = "JPY",
    ):
        await interaction.response.defer()
        all_members = "wako,emura,hachiga,miyabayashi,kusama,masataka,togo"
        try:
            result = await self.web.add_expense(
                title=title,
                amount=amount,
                currency=currency,
                paid_by=paid_by,
                split_among=all_members,
            )
            symbol = "₱" if currency == "PHP" else "¥"
            from cogs.web_sync import MEMBER_NAMES
            paid_name = MEMBER_NAMES.get(paid_by, paid_by)
            embed = discord.Embed(
                title=f"💸 経費追加: {title}",
                colour=COLOUR_BUDGET,
                url=WEB_URL,
            )
            embed.add_field(name="金額", value=f"{symbol}{amount:,.0f}", inline=True)
            embed.add_field(name="立替", value=paid_name, inline=True)
            embed.add_field(name="割り勘", value="7人全員", inline=True)
            embed.set_footer(text=f"Webページにも反映済み → {WEB_URL}")
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"❌ エラー: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(WebWriteCog(bot))
