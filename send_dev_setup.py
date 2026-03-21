"""Create dev channels and post collaboration guide."""

import asyncio
import os

import discord
from dotenv import load_dotenv

load_dotenv()

GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", "0"))
TOKEN = os.getenv("DISCORD_TOKEN", "")


async def main():
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        guild = client.get_guild(GUILD_ID)
        if not guild:
            print("Guild not found")
            await client.close()
            return

        # Create 🛠️ 開発 category with channels
        cat_name = "🛠️ 開発"
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            category = await guild.create_category(cat_name)
            print(f"Created category: {cat_name}")

        dev_channels = [
            {"name": "バグ報告", "topic": "バグや不具合の報告"},
            {"name": "機能要望", "topic": "追加してほしい機能のリクエスト"},
            {"name": "開発ログ", "topic": "開発の進捗や変更履歴"},
        ]

        for ch_info in dev_channels:
            existing = discord.utils.get(category.text_channels, name=ch_info["name"])
            if not existing:
                await category.create_text_channel(
                    name=ch_info["name"],
                    topic=ch_info["topic"],
                )
                print(f"Created channel: #{ch_info['name']}")

        # Post GitHub info to 開発ログ
        dev_log = discord.utils.get(category.text_channels, name="開発ログ")
        if dev_log:
            embed = discord.Embed(
                title="🛠️ 共同開発ガイド",
                colour=0x1ABC9C,
            )
            embed.add_field(
                name="📦 GitHubリポジトリ",
                value=(
                    "**https://github.com/key-tune/travel-bot**\n"
                    "誰でもクローンしてPR出せます。"
                ),
                inline=False,
            )
            embed.add_field(
                name="🚀 セットアップ手順",
                value=(
                    "```bash\n"
                    "git clone https://github.com/key-tune/travel-bot.git\n"
                    "cd travel-bot\n"
                    "cp .env.example .env  # APIキーを設定\n"
                    "uv sync              # 依存パッケージ\n"
                    "uv run python bot.py # 起動\n"
                    "```"
                ),
                inline=False,
            )
            embed.add_field(
                name="🤖 Claude Codeで開発",
                value=(
                    "リポをクローン後、Claude Codeで開けば\n"
                    "CLAUDE.mdを自動認識して旅行Botの\n"
                    "コンテキストで作業できます。\n\n"
                    "```bash\n"
                    "cd travel-bot\n"
                    "claude\n"
                    "```"
                ),
                inline=False,
            )
            embed.add_field(
                name="📂 プロジェクト構成",
                value=(
                    "```\n"
                    "bot.py          — エントリーポイント\n"
                    "config.py       — 旅行設定\n"
                    "database.py     — SQLiteスキーマ\n"
                    "cogs/           — Discordコマンド\n"
                    "  flights.py    — /flights, /monitor\n"
                    "  hotels.py     — /hotels\n"
                    "  planner.py    — /plan, /itinerary\n"
                    "  budget.py     — /expense, /budget\n"
                    "  ask.py        — /ask (Claude AI)\n"
                    "  dashboard.py  — /dashboard\n"
                    "  listener.py   — 自動応答\n"
                    "  setup.py      — /setup\n"
                    "services/       — API連携\n"
                    "```"
                ),
                inline=False,
            )
            embed.add_field(
                name="🔗 Webページ連携",
                value=(
                    "ga11agherのWebページ: https://orfevre.xyz/philippines/\n"
                    "BotのデータとWeb側を連携するAPIも追加予定。"
                ),
                inline=False,
            )
            msg = await dev_log.send(embed=embed)
            await msg.pin()
            print("Posted dev guide")

        # Post to バグ報告
        bug_ch = discord.utils.get(category.text_channels, name="バグ報告")
        if bug_ch:
            embed = discord.Embed(
                title="🐛 バグ報告テンプレート",
                description=(
                    "バグを見つけたら以下の形式で報告してください：\n\n"
                    "**何をしたか：** (例: /flights 2026-04-15 を実行)\n"
                    "**何が起きたか：** (例: エラーメッセージが出た)\n"
                    "**期待する動作：** (例: フライト一覧が表示される)\n"
                    "**スクショ：** (あれば)\n\n"
                    "GitHubのIssueでもOK:\n"
                    "https://github.com/key-tune/travel-bot/issues"
                ),
                colour=0xE74C3C,
            )
            await bug_ch.send(embed=embed)
            print("Posted bug template")

        # Post to 機能要望
        feat_ch = discord.utils.get(category.text_channels, name="機能要望")
        if feat_ch:
            embed = discord.Embed(
                title="💡 機能要望テンプレート",
                description=(
                    "こんな機能がほしい！というリクエストをどうぞ：\n\n"
                    "**やりたいこと：** (例: 天気予報を表示したい)\n"
                    "**どう使いたいか：** (例: /weather で旅行期間の天気)\n"
                    "**優先度：** 高 / 中 / 低\n\n"
                    "GitHubのIssueでもOK:\n"
                    "https://github.com/key-tune/travel-bot/issues"
                ),
                colour=0x3498DB,
            )
            await feat_ch.send(embed=embed)
            print("Posted feature template")

        print("Dev setup complete!")
        await client.close()

    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
