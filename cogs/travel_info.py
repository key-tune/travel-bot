"""Travel advisory cog — visa, safety, entry requirements, insurance info."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_DASH
from services.research_service import ResearchService

log = logging.getLogger(__name__)


class TravelInfoCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.research = ResearchService()

    async def cog_unload(self):
        await self.research.close()

    @app_commands.command(name="travel-info", description="渡航情報メニュー")
    @app_commands.describe(topic="調べたい情報")
    @app_commands.choices(
        topic=[
            app_commands.Choice(name="入国要件（ビザ・パスポート）", value="entry"),
            app_commands.Choice(name="安全情報・治安", value="safety"),
            app_commands.Choice(name="海外旅行保険", value="insurance"),
            app_commands.Choice(name="持ち物・準備リスト", value="packing"),
            app_commands.Choice(name="通貨・両替・支払い", value="money"),
            app_commands.Choice(name="SIM・Wi-Fi・通信", value="connectivity"),
            app_commands.Choice(name="空港・交通アクセス", value="transport"),
            app_commands.Choice(name="緊急連絡先", value="emergency"),
        ]
    )
    async def travel_info(self, interaction: discord.Interaction, topic: str):
        await interaction.response.defer()

        queries_map = {
            "entry": [
                "フィリピン 入国 日本人 2025 2026 ビザ パスポート 条件",
                "Philippines entry requirements Japanese tourists visa 2025",
                "フィリピン eTravel 登録 入国カード 必要書類",
            ],
            "safety": [
                "セブ 治安 安全 2025 日本人 旅行者 注意点",
                "外務省 フィリピン 安全情報 危険度 セブ",
                "Cebu safety tips tourists 2025 scams",
            ],
            "insurance": [
                "海外旅行保険 フィリピン セブ おすすめ 2025 比較",
                "クレジットカード 海外旅行保険 自動付帯 フィリピン",
                "フィリピン 病院 医療費 日本人 セブ",
            ],
            "packing": [
                "セブ旅行 持ち物リスト 必需品 2025",
                "フィリピン セブ 服装 6月 雨季 準備",
                "海外旅行 持ち物 チェックリスト 東南アジア",
            ],
            "money": [
                "フィリピンペソ 両替 お得 セブ 2025 レート",
                "セブ クレジットカード 使える キャッシュレス チップ",
                "フィリピン 物価 予算 1日 セブ 旅行",
            ],
            "connectivity": [
                "セブ SIMカード 購入 プリペイド 旅行者 2025",
                "フィリピン eSIM おすすめ 旅行 データ通信",
                "セブ Wi-Fi 事情 レンタル ポケットWiFi",
            ],
            "transport": [
                "マクタン セブ空港 市内 移動 タクシー Grab 2025",
                "セブ 交通手段 ジプニー タクシー 料金 旅行者",
                "セブ マクタン 空港 ターミナル2 到着 流れ",
            ],
            "emergency": [
                "フィリピン セブ 緊急連絡先 日本大使館 警察 病院",
                "セブ 日本語 対応 病院 クリニック",
                "フィリピン 日本大使館 領事館 セブ 連絡先",
            ],
        }

        topic_titles = {
            "entry": "🛂 入国要件（ビザ・パスポート）",
            "safety": "⚠️ 安全情報・治安",
            "insurance": "🏥 海外旅行保険",
            "packing": "🧳 持ち物・準備リスト",
            "money": "💱 通貨・両替・支払い",
            "connectivity": "📱 SIM・Wi-Fi・通信",
            "transport": "🚗 空港・交通アクセス",
            "emergency": "🆘 緊急連絡先",
        }

        queries = queries_map.get(topic, [])
        title = topic_titles.get(topic, "渡航情報")

        report = await self.research.research(title, queries)

        # Split if too long
        if len(report) > 4000:
            report = report[:4000] + "…"

        embed = discord.Embed(
            title=title,
            description=report,
            colour=COLOUR_DASH,
        )
        embed.set_footer(text="🔍 AI Web Research — 最新情報は公式サイトで確認してください")

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="emergency", description="緊急連絡先を即表示")
    async def emergency(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🆘 セブ 緊急連絡先",
            colour=0xFF0000,
        )
        embed.add_field(
            name="🚔 緊急通報",
            value=(
                "**警察:** 911 または 166\n"
                "**消防:** 911\n"
                "**救急:** 911"
            ),
            inline=False,
        )
        embed.add_field(
            name="🇯🇵 日本大使館・領事館",
            value=(
                "**在セブ日本国総領事館:**\n"
                "📞 (032) 231-7321 / 231-7322\n"
                "📍 7th Floor, Keppel Center, Samar Loop cor. Cardinal Rosales Ave, Cebu Business Park\n"
                "⏰ 月〜金 8:30-12:00, 13:30-17:00\n\n"
                "**緊急時（時間外）:**\n"
                "📞 (032) 231-7321（留守電→緊急番号案内）"
            ),
            inline=False,
        )
        embed.add_field(
            name="🏥 日本語対応病院",
            value=(
                "**Chong Hua Hospital:**\n"
                "📞 (032) 233-8000\n"
                "📍 Fuente Osmeña, Cebu City\n\n"
                "**Cebu Doctors' University Hospital:**\n"
                "📞 (032) 253-7511\n"
                "📍 Osmeña Blvd, Cebu City"
            ),
            inline=False,
        )
        embed.add_field(
            name="📞 その他",
            value=(
                "**海外旅行保険（例: 損保ジャパン）:** 81-3-3811-8127\n"
                "**クレカ紛失（例: VISA）:** 1-303-967-1096\n"
                "**Grab（配車）:** アプリ内ヘルプ"
            ),
            inline=False,
        )
        embed.set_footer(text="⚠️ この情報は参考です。最新の連絡先は渡航前に確認してください")

        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(TravelInfoCog(bot))
