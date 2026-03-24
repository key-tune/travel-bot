"""Daily tips cog — automated Cebu travel tips until departure."""

import logging
import os
from datetime import datetime, date

import discord
from discord.ext import commands, tasks

from config import COLOUR_DASH

log = logging.getLogger(__name__)

TRIP_START = date(2026, 6, 25)

# 90+ tips covering practical travel info, not generic filler
TIPS = [
    "セブの公用語はセブアノ語と英語。タクシーやレストランでは英語が通じます。簡単なセブアノ語: Salamat (ありがとう)、Oo (はい)、Dili (いいえ)",
    "フィリピン入国にはeTravel登録が必須。出発72時間前からオンラインで登録可能。QRコードを保存しておこう → https://etravel.gov.ph",
    "セブの電圧は220V/60Hz。日本の100V機器はそのまま使えないものがある。スマホやPC充電器は大体対応してるけど、ドライヤーは変圧器が必要",
    "Grabアプリ（東南アジアのUber）を事前にインストール。タクシーより安全で料金も明確。空港からホテルまでも使える",
    "フィリピンペソ(PHP)への両替は現地がお得。空港より市内の両替所の方がレートが良い。SMモールの両替所がおすすめ",
    "水道水は飲めません。ペットボトルの水を買うか、ホテルの浄水を使おう。氷も注意が必要な場合がある",
    "セブのチップ文化: レストランはサービス料込みが多いけど、満足したら20-50ペソ。マッサージは50-100ペソが目安",
    "日焼け止めは必須！セブは赤道に近く紫外線が強い。SPF50+を持っていこう。現地でも買えるけど日本製の方が品質が安定",
    "SIMカードは空港で購入可能。GlobeかSmartがおすすめ。7日間データ無制限で300-500ペソ程度。eSIM対応スマホならAiraloも便利",
    "セブの移動手段: Grab（配車）、ジプニー（激安だけど観光客には難度高め）、バイクタクシー（Angkas）、レンタカー（国際免許必要）",
    "オスロブのジンベエザメツアーは早朝出発（AM3-4時）。前日は早めに就寝を。ツアー予約は現地代理店かKlookで",
    "海外旅行保険は必ず加入。クレカ付帯だけでは不十分な場合も。フィリピンの医療費は安いが、救急搬送は高額になることがある",
    "セブのレストランでは「レチョン」（豚の丸焼き）が名物。Rico's LechonやCNTが有名。7人なら1匹頼んでシェアもあり",
    "マクタン島とセブシティは橋で繋がってる。空港はマクタン島にある。セブシティまでは車で30-60分（渋滞次第）",
    "フィリピンのコンセントはAタイプ（日本と同じ形状）。変換プラグ不要な場合が多いが、念のため確認を",
    "セブの雨季は6-11月。6月下旬はスコール（短時間の豪雨）が多い。折りたたみ傘かレインコートを持参しよう",
    "パスポートのコピー（写真ページ）をスマホに保存しておこう。紛失時に領事館での再発行がスムーズになる",
    "現地での値段交渉は普通。お土産屋やマーケットでは最初の提示額の60-70%くらいが目安",
    "セブのWi-Fi事情: ホテルやカフェにはあるけど速度は日本ほど安定しない。重要な連絡にはSIMデータ通信が確実",
    "アイランドホッピングは7人だとボート1隻チャーターがお得。1隻3,000-5,000ペソで半日楽しめる",
    "セブでのATMキャッシング: 1回の引き出し上限が10,000-20,000ペソと低い。手数料200ペソ/回。まとまった金額は両替所で",
    "蚊対策: デング熱のリスクあり。虫除けスプレー持参。夕方以降は長袖があると安心",
    "フィリピンでは写真撮影前に許可を求めるのがマナー。特に子供や宗教施設では注意",
    "セブのスパ・マッサージは格安。1時間300-500ペソ（約1,000-1,700円）。Nuat Thaiやウェルネスセンターが人気",
    "復路フライトは6/28の朝4:30発。最終日はホテルチェックアウト後、深夜に空港に向かう必要がある。空港近くで時間を潰せる場所を事前にチェック",
    "トイレ事情: ショッピングモールやホテルは綺麗。ローカルな場所ではトイレットペーパーがないことも。ポケットティッシュ持参推奨",
    "フィリピンの法律: 路上飲酒禁止、公共の場での喫煙禁止（罰金あり）。ドゥテルテ以降の厳しい取り締まりが続いてる",
    "セブのショッピング: SMシーサイドモール（巨大）、アヤラセンター（高級寄り）、カルボンマーケット（ローカル・要注意）",
    "深夜のタクシー・ジプニーは避ける。Grabを使うか、ホテルの送迎サービスを利用しよう",
    "クレジットカードは大きなモールやホテルで使えるが、小さな店やローカルレストランは現金のみが多い",
    "在セブ日本国総領事館: (032) 231-7321。緊急時に備えて連絡先を保存しておこう",
]


def _get_tip_for_day(days_left: int) -> str:
    """Get a tip based on days remaining."""
    idx = len(TIPS) - min(days_left, len(TIPS))
    idx = max(0, min(idx, len(TIPS) - 1))
    return TIPS[idx]


class DailyTipsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.daily_tip.start()

    def cog_unload(self):
        self.daily_tip.cancel()

    @tasks.loop(hours=24)
    async def daily_tip(self):
        today = date.today()
        days_left = (TRIP_START - today).days

        if days_left < 0:
            # Trip is over
            self.daily_tip.cancel()
            return

        if days_left > len(TIPS):
            return  # Too far out

        guild_id = os.getenv("DISCORD_GUILD_ID")
        if not guild_id:
            return

        guild = self.bot.get_guild(int(guild_id))
        if not guild:
            return

        # Find お知らせ channel
        target_ch = None
        for ch in guild.text_channels:
            if ch.name == "お知らせ":
                target_ch = ch
                break

        if not target_ch:
            return

        tip = _get_tip_for_day(days_left)

        embed = discord.Embed(colour=COLOUR_DASH)

        if days_left == 0:
            embed.title = "🎉 出発日！いってらっしゃい！"
            embed.description = "準備はOK？パスポート、eTravel QR、充電器、日焼け止め、忘れ物チェック！\nセブで最高の思い出を作ろう！🏝️✈️"
        else:
            embed.title = f"🏝️ セブ旅行まであと **{days_left}日**"
            embed.description = f"💡 **今日のTips**\n{tip}"

        embed.set_footer(text=f"{today.strftime('%Y/%m/%d')} | 出発: 2026/06/25")

        await target_ch.send(embed=embed)
        log.info("Daily tip sent: %d days left", days_left)

    @daily_tip.before_loop
    async def before_daily_tip(self):
        await self.bot.wait_until_ready()
        # Wait until 9:00 AM JST
        now = datetime.now()
        target = now.replace(hour=9, minute=3, second=0, microsecond=0)
        if now >= target:
            # Already past 9 AM today, wait until tomorrow
            from datetime import timedelta
            target += timedelta(days=1)
        wait_seconds = (target - now).total_seconds()
        log.info("Daily tips: waiting %.0f seconds until 9:03 AM", wait_seconds)
        import asyncio
        await asyncio.sleep(wait_seconds)


async def setup(bot: commands.Bot):
    await bot.add_cog(DailyTipsCog(bot))
