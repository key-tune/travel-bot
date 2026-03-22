"""Server setup cog — creates channels, categories, and welcome message."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_DASH

log = logging.getLogger(__name__)

# Channel structure for the travel server
CATEGORIES = {
    "📋 旅行計画": [
        {"name": "お知らせ", "topic": "重要なお知らせ・決定事項"},
        {"name": "日程調整", "topic": "旅行日程の相談・投票"},
        {"name": "フライト", "topic": "/flights, /monitor でフライト検索・価格監視"},
        {"name": "ホテル", "topic": "/hotels, /hotel-save でホテル検索・お気に入り"},
        {"name": "旅程プラン", "topic": "/plan, /itinerary でアクティビティ計画・投票"},
    ],
    "💰 お金": [
        {"name": "予算相談", "topic": "予算の話し合い"},
        {"name": "経費記録", "topic": "/expense, /budget で経費登録・精算計算"},
    ],
    "🏖️ セブ情報": [
        {"name": "観光スポット", "topic": "行きたい場所を共有"},
        {"name": "グルメ", "topic": "レストラン・カフェ情報"},
        {"name": "ショッピング", "topic": "お土産・買い物情報"},
        {"name": "ai質問", "topic": "/ask でAIに旅行の質問"},
        {"name": "渡航情報", "topic": "/travel-info でビザ・安全・保険・持ち物など"},
    ],
    "🤖 Bot": [
        {"name": "bot-commands", "topic": "Botコマンド実行用"},
        {"name": "price-alerts", "topic": "価格監視アラート（自動通知）"},
        {"name": "dashboard", "topic": "/dashboard で全体サマリー"},
    ],
    "💬 雑談": [
        {"name": "雑談", "topic": "なんでも自由に"},
        {"name": "写真共有", "topic": "旅行中の写真・スクショ共有"},
    ],
}


class SetupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="setup", description="サーバーのチャンネルを旅行計画用に整備")
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        if not guild:
            await interaction.followup.send("❌ サーバー内で実行してください")
            return

        created_channels = []
        created_categories = []

        for cat_name, channels in CATEGORIES.items():
            try:
                # Check if category already exists
                existing_cat = discord.utils.get(guild.categories, name=cat_name)
                if existing_cat:
                    category = existing_cat
                    log.info("Category already exists: %s", cat_name)
                else:
                    category = await guild.create_category(cat_name)
                    created_categories.append(cat_name)
                    log.info("Created category: %s", cat_name)

                for ch_info in channels:
                    ch_name = ch_info["name"]
                    try:
                        existing_ch = discord.utils.get(category.text_channels, name=ch_name)
                        if existing_ch:
                            log.info("Channel already exists: %s", ch_name)
                            continue

                        await category.create_text_channel(
                            name=ch_name,
                            topic=ch_info["topic"],
                        )
                        created_channels.append(f"#{ch_name}")
                        log.info("Created channel: %s", ch_name)
                    except Exception as e:
                        log.error("Failed to create channel %s: %s", ch_name, e)
            except Exception as e:
                log.error("Failed to create category %s: %s", cat_name, e)

        # Send welcome message to お知らせ channel
        announce_cat = discord.utils.get(guild.categories, name="📋 旅行計画")
        if announce_cat:
            announce_ch = discord.utils.get(announce_cat.text_channels, name="お知らせ")
            if announce_ch:
                welcome = discord.Embed(
                    title="🏝️ セブ旅行計画サーバーへようこそ！",
                    description="7人でセブ旅行を計画するためのサーバーです。",
                    colour=COLOUR_DASH,
                )
                welcome.add_field(
                    name="✈️ フライト",
                    value=(
                        "`/flights 2026-04-15` — 復路検索\n"
                        "`/monitor start 2026-04-15` — 価格監視開始"
                    ),
                    inline=False,
                )
                welcome.add_field(
                    name="🏨 ホテル",
                    value=(
                        "`/hotels` — ホテル検索\n"
                        "`/hotel-save <名前>` — お気に入り追加\n"
                        "`/hotel-list` — お気に入り一覧"
                    ),
                    inline=False,
                )
                welcome.add_field(
                    name="📋 旅程",
                    value=(
                        "`/plan <日付> <タイトル>` — アクティビティ追加\n"
                        "`/itinerary` — 旅程一覧\n"
                        "投票ボタンで賛成/反対 → 4人以上で承認"
                    ),
                    inline=False,
                )
                welcome.add_field(
                    name="💰 割り勘",
                    value=(
                        "`/expense <内容> <金額> <立替者>` — 経費登録\n"
                        "`/budget` — 精算計算"
                    ),
                    inline=False,
                )
                welcome.add_field(
                    name="🤖 AI & その他",
                    value=(
                        "`/ask <質問>` — AIに旅行の質問\n"
                        "`/dashboard` — 全体サマリー\n"
                        "`/ping` — Bot動作確認"
                    ),
                    inline=False,
                )
                welcome.set_footer(text="みんなで最高の旅行にしよう！🎉")

                # Pin the welcome message
                msg = await announce_ch.send(embed=welcome)
                await msg.pin()

        # Set bot status
        await self.bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="セブ旅行計画中 🏝️",
            )
        )

        # Summary
        embed = discord.Embed(
            title="✅ サーバーセットアップ完了！",
            colour=COLOUR_DASH,
        )
        if created_categories:
            embed.add_field(
                name="📁 作成したカテゴリ",
                value="\n".join(created_categories),
                inline=False,
            )
        if created_channels:
            embed.add_field(
                name="💬 作成したチャンネル",
                value="\n".join(created_channels),
                inline=False,
            )
        if not created_categories and not created_channels:
            embed.description = "全チャンネルは既に存在しています（topicのみ更新）"
        else:
            embed.description = f"{len(created_categories)}カテゴリ, {len(created_channels)}チャンネルを作成"

        embed.add_field(
            name="💡 次のステップ",
            value=(
                "1. `#bot-commands` でコマンドを試す\n"
                "2. `#フライト` で `/flights` を実行\n"
                "3. 友達をサーバーに招待！"
            ),
            inline=False,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cleanup", description="Bot作成チャンネルを全削除（注意！）")
    @app_commands.default_permissions(administrator=True)
    async def cleanup(self, interaction: discord.Interaction):
        """Remove all bot-created categories and channels."""
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if not guild:
            return

        deleted = 0
        for cat_name in CATEGORIES:
            category = discord.utils.get(guild.categories, name=cat_name)
            if category:
                for ch in category.channels:
                    await ch.delete()
                    deleted += 1
                await category.delete()
                deleted += 1

        await interaction.followup.send(f"🗑️ {deleted}個のチャンネル/カテゴリを削除しました", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(SetupCog(bot))
