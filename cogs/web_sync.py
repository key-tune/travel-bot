"""Web sync cog — bridge between Discord bot and orfevre.xyz web app."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_DASH, COLOUR_PLAN, COLOUR_BUDGET
from services.web_client import WebClient

log = logging.getLogger(__name__)

# Map web member IDs to display names
MEMBER_NAMES = {
    "wako": "わこ", "emura": "えむら", "hachiga": "はちが",
    "miyabayashi": "みやばやし", "kusama": "くさま",
    "masataka": "まさたか", "togo": "とおご",
}

DAY_LABELS = {1: "6/25 (木) Day1", 2: "6/26 (金) Day2", 3: "6/27 (土) Day3", 4: "6/28 (日) Day4"}


class WebSyncCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.web = WebClient()

    async def cog_unload(self):
        await self.web.close()

    @app_commands.command(name="web-schedule", description="Webページのスケジュールを表示")
    async def web_schedule(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            schedule = await self.web.get_schedule()
        except Exception as e:
            await interaction.followup.send(f"❌ Web接続エラー: {e}")
            return

        embed = discord.Embed(
            title="📅 スケジュール (Webページ連携)",
            colour=COLOUR_PLAN,
            url="https://orfevre.xyz/philippines/",
        )

        if not schedule:
            embed.description = "まだスケジュールがありません"
        else:
            by_day: dict[int, list] = {}
            for item in schedule:
                day = item.get("day", 0)
                by_day.setdefault(day, []).append(item)

            for day in sorted(by_day):
                day_label = DAY_LABELS.get(day, f"Day{day}")
                items = by_day[day]
                items.sort(key=lambda x: x.get("time_slot", ""))
                lines = []
                for it in items:
                    time_str = it.get("time_slot", "")
                    end = it.get("end_time", "")
                    time_range = f"{time_str}〜{end}" if end else time_str
                    members = it.get("members", "")
                    member_count = len(members.split(",")) if members else 0
                    lines.append(f"🕐 {time_range} **{it['title']}** ({member_count}人)")
                embed.add_field(
                    name=f"━━━ {day_label} ━━━",
                    value="\n".join(lines) or "—",
                    inline=False,
                )

        embed.set_footer(text="🔗 https://orfevre.xyz/philippines/")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="web-expenses", description="Webページの経費・割り勘を表示")
    async def web_expenses(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            expenses = await self.web.get_expenses()
            settlements = await self.web.get_settlements()
        except Exception as e:
            await interaction.followup.send(f"❌ Web接続エラー: {e}")
            return

        embed = discord.Embed(
            title="💰 割り勘 (Webページ連携)",
            colour=COLOUR_BUDGET,
            url="https://orfevre.xyz/philippines/",
        )

        if not expenses:
            embed.description = "まだ経費がありません"
        else:
            total = sum(e.get("amount", 0) for e in expenses)
            lines = []
            for e in expenses:
                paid_name = MEMBER_NAMES.get(e.get("paid_by", ""), e.get("paid_by_name", "?"))
                currency = e.get("currency", "JPY")
                symbol = "₱" if currency == "PHP" else "¥"
                lines.append(f"{symbol}{e['amount']:,.0f} {e['title']} (立替: {paid_name})")
            embed.add_field(
                name=f"📝 経費一覧 ({len(expenses)}件)",
                value="\n".join(lines),
                inline=False,
            )

        # Settlements
        settle_list = settlements.get("settlements", [])
        if settle_list:
            settle_lines = []
            for s in settle_list:
                from_name = MEMBER_NAMES.get(s["from"], s["from"])
                to_name = MEMBER_NAMES.get(s["to"], s["to"])
                settle_lines.append(f"{from_name} → {to_name}: **¥{s['amount']:,}**")
            embed.add_field(
                name="💸 精算",
                value="\n".join(settle_lines),
                inline=False,
            )

        embed.set_footer(text="🔗 https://orfevre.xyz/philippines/")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="web-wishes", description="やりたいことリストを表示")
    async def web_wishes(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            wishes = await self.web.get_wishes()
        except Exception as e:
            await interaction.followup.send(f"❌ Web接続エラー: {e}")
            return

        embed = discord.Embed(
            title="💛 やりたいこと (Webページ連携)",
            colour=COLOUR_PLAN,
            url="https://orfevre.xyz/philippines/",
        )

        if not wishes:
            embed.description = "まだ登録されていません。Webページから追加しよう！"
        else:
            for i, w in enumerate(wishes, 1):
                name = MEMBER_NAMES.get(w.get("created_by", ""), "?")
                embed.add_field(
                    name=f"{i}. {w.get('title', '?')}",
                    value=f"{w.get('description', '')} — {name}",
                    inline=False,
                )

        embed.set_footer(text="🔗 https://orfevre.xyz/philippines/")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="web-todos", description="TODOリストを表示")
    async def web_todos(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            todos = await self.web.get_todos()
        except Exception as e:
            await interaction.followup.send(f"❌ Web接続エラー: {e}")
            return

        embed = discord.Embed(
            title="✅ TODO (Webページ連携)",
            colour=COLOUR_DASH,
            url="https://orfevre.xyz/philippines/",
        )

        if not todos:
            embed.description = "TODOなし！Webページから追加しよう！"
        else:
            for t in todos:
                status = "✅" if t.get("done") else "🔘"
                assignee = MEMBER_NAMES.get(t.get("assignee", ""), "")
                embed.add_field(
                    name=f"{status} {t.get('title', '?')}",
                    value=f"担当: {assignee}" if assignee else "—",
                    inline=False,
                )

        embed.set_footer(text="🔗 https://orfevre.xyz/philippines/")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="web-news", description="セブ関連ニュースを表示")
    async def web_news(self, interaction: discord.Interaction):
        await interaction.response.defer()
        try:
            news = await self.web.get_news()
        except Exception as e:
            await interaction.followup.send(f"❌ Web接続エラー: {e}")
            return

        embed = discord.Embed(
            title="📰 セブ関連ニュース",
            colour=COLOUR_DASH,
        )

        if not news:
            embed.description = "ニュースがありません"
        else:
            for i, n in enumerate(news[:5], 1):
                title = n.get("title", "?")
                link = n.get("link", "")
                if len(title) > 100:
                    title = title[:100] + "…"
                embed.add_field(
                    name=f"{i}. {title}",
                    value=f"[記事を読む]({link})" if link else "—",
                    inline=False,
                )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(WebSyncCog(bot))
