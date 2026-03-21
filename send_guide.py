"""Send usage guide messages to each channel."""

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

        def find_ch(name: str):
            return discord.utils.get(guild.text_channels, name=name)

        # ── #日程調整 ──
        ch = find_ch("日程調整")
        if ch:
            embed = discord.Embed(
                title="📅 まずは帰国日を決めよう！",
                description=(
                    "往路は確保済み。復路の日程を決める必要があります。\n\n"
                    "**候補日を出し合おう：**\n"
                    "例えば「4/13〜4/16のどこか」みたいに書いてね。\n\n"
                    "日程が絞れたら `/flights` で価格を比較できます。"
                ),
                colour=0x3498DB,
            )
            embed.add_field(
                name="💡 ヒント",
                value=(
                    "曜日によって価格が大きく変わるので、\n"
                    "複数日で検索して比較するのがおすすめ！"
                ),
                inline=False,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #フライト ──
        ch = find_ch("フライト")
        if ch:
            embed = discord.Embed(
                title="✈️ フライト検索の使い方",
                colour=0x3498DB,
            )
            embed.add_field(
                name="🔍 フライト検索",
                value=(
                    "```\n"
                    "/flights 2026-04-15\n"
                    "```\n"
                    "CEB→NRT、CEB→HND、CEB→NGO の3ルートを\n"
                    "同時検索して最安を比較します。\n"
                    "6人分(NRT/HND)と1人分(NGO)で合計表示。"
                ),
                inline=False,
            )
            embed.add_field(
                name="📊 価格監視",
                value=(
                    "```\n"
                    "/monitor start 2026-04-15\n"
                    "```\n"
                    "6時間ごとに自動で価格チェック。\n"
                    "過去最安を下回ったら `#price-alerts` に通知！\n\n"
                    "`/monitor status` — 監視状況の確認\n"
                    "`/monitor stop` — 監視停止"
                ),
                inline=False,
            )
            embed.add_field(
                name="🗓️ 複数日を比較するなら",
                value=(
                    "何日か試してみよう：\n"
                    "`/flights 2026-04-13`\n"
                    "`/flights 2026-04-14`\n"
                    "`/flights 2026-04-15`\n"
                    "→ 一番安い日がわかる！"
                ),
                inline=False,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #ホテル ──
        ch = find_ch("ホテル")
        if ch:
            embed = discord.Embed(
                title="🏨 ホテル検索の使い方",
                colour=0x2ECC71,
            )
            embed.add_field(
                name="🔍 エリア別検索",
                value=(
                    "```\n"
                    "/hotels area:マクタン島\n"
                    "/hotels area:セブシティ\n"
                    "/hotels area:リゾートエリア\n"
                    "```\n"
                    "Google Hotelsの検索結果を表示。"
                ),
                inline=False,
            )
            embed.add_field(
                name="⭐ お気に入り管理",
                value=(
                    "良さそうなホテルを見つけたら保存＆投票：\n"
                    "```\n"
                    "/hotel-save name:Crimson Resort area:mactan price:15000 rating:4.5\n"
                    "```\n"
                    "👍/👎 ボタンでみんなで投票！\n"
                    "`/hotel-list` で投票結果ランキング表示"
                ),
                inline=False,
            )
            embed.add_field(
                name="💡 7人の部屋割り",
                value=(
                    "・ツイン3部屋 + シングル1部屋\n"
                    "・4人部屋 + 3人部屋\n"
                    "・大部屋(ドミトリー/ヴィラ)\n"
                    "どの構成がいいか話し合おう！"
                ),
                inline=False,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #旅程プラン ──
        ch = find_ch("旅程プラン")
        if ch:
            embed = discord.Embed(
                title="📋 旅程プランの使い方",
                colour=0xF39C12,
            )
            embed.add_field(
                name="📝 アクティビティを追加",
                value=(
                    "```\n"
                    "/plan date:2026-04-12 title:アイランドホッピング time:09:00 category:activity\n"
                    "/plan date:2026-04-12 title:ランチ（シーフード）time:12:00 category:food\n"
                    "/plan date:2026-04-13 title:ジンベエザメツアー time:05:00 category:activity\n"
                    "```"
                ),
                inline=False,
            )
            embed.add_field(
                name="✅ 投票で決定",
                value=(
                    "追加されたアクティビティに\n"
                    "「賛成 ✅」「反対 ❌」ボタンで投票。\n"
                    "**7人中4人以上の賛成**で自動承認！\n\n"
                    "`/itinerary` — 承認済み旅程の一覧表示"
                ),
                inline=False,
            )
            embed.add_field(
                name="🏄 セブの人気アクティビティ",
                value=(
                    "・🦈 ジンベエザメウォッチング (オスロブ)\n"
                    "・🏝️ アイランドホッピング\n"
                    "・🤿 シュノーケリング / ダイビング\n"
                    "・🏖️ ビーチリゾートでのんびり\n"
                    "・🛍️ SMシーサイドモール\n"
                    "・💆 スパ / マッサージ\n"
                    "・🍖 レチョン（豚の丸焼き）\n"
                    "詳しくは `/ask` でAIに聞こう！"
                ),
                inline=False,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #経費記録 ──
        ch = find_ch("経費記録")
        if ch:
            embed = discord.Embed(
                title="💰 割り勘・経費管理の使い方",
                colour=0xE74C3C,
            )
            embed.add_field(
                name="💸 経費を登録",
                value=(
                    "誰かが立て替えたら記録：\n"
                    "```\n"
                    "/expense description:ホテル代3泊 amount:120000 paid_by:@たろう category:hotel\n"
                    "/expense description:ジンベエツアー amount:35000 paid_by:@はなこ category:activity\n"
                    "/expense description:夕食（焼肉）amount:14000 paid_by:@じろう category:food\n"
                    "```"
                ),
                inline=False,
            )
            embed.add_field(
                name="📊 精算計算",
                value=(
                    "```\n"
                    "/budget\n"
                    "```\n"
                    "カテゴリ別の合計と、\n"
                    "**最小送金回数**で精算方法を自動計算！\n"
                    "「AさんがBさんに¥5,000送る」みたいに表示。"
                ),
                inline=False,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #ai質問 ──
        ch = find_ch("ai質問")
        if ch:
            embed = discord.Embed(
                title="🤖 AI旅行アシスタントの使い方",
                colour=0x9B59B6,
            )
            embed.add_field(
                name="❓ なんでも聞ける",
                value=(
                    "```\n"
                    "/ask セブの治安は？気をつけることは？\n"
                    "/ask マクタン島でおすすめのレストランは？\n"
                    "/ask セブの4月の天気と服装は？\n"
                    "/ask 空港からホテルへの移動手段は？\n"
                    "/ask 7人で楽しめるアクティビティを5つ提案して\n"
                    "/ask フィリピンペソへの両替はどこがお得？\n"
                    "```"
                ),
                inline=False,
            )
            embed.add_field(
                name="💡 特徴",
                value=(
                    "・旅程やホテルのお気に入り情報も考慮して回答\n"
                    "・7人グループ旅行に特化した提案\n"
                    "・日本語で質問→日本語で回答"
                ),
                inline=False,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #dashboard ──
        ch = find_ch("dashboard")
        if ch:
            embed = discord.Embed(
                title="📊 ダッシュボードの使い方",
                colour=0x1ABC9C,
            )
            embed.description = (
                "```\n"
                "/dashboard\n"
                "```\n"
                "旅行計画の全体サマリーを一覧表示：\n\n"
                "✈️ フライト監視状況と最安値\n"
                "🏨 トップ投票ホテル\n"
                "📋 日別の旅程進捗\n"
                "💰 経費合計・1人あたり"
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #雑談 ──
        ch = find_ch("雑談")
        if ch:
            embed = discord.Embed(
                title="🎉 セブ旅行計画スタート！",
                description=(
                    "やること リスト：\n\n"
                    "1️⃣ **帰国日を決める** → `#日程調整` で話し合い\n"
                    "2️⃣ **フライト比較** → `#フライト` で `/flights` 検索\n"
                    "3️⃣ **ホテル選び** → `#ホテル` で検索＆投票\n"
                    "4️⃣ **やりたいこと** → `#旅程プラン` で提案＆投票\n"
                    "5️⃣ **わからないこと** → `#ai質問` でAIに聞く\n\n"
                    "みんなで楽しい旅行にしよう！🏝️✈️"
                ),
                colour=0x1ABC9C,
            )
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        # ── #bot-commands ──
        ch = find_ch("bot-commands")
        if ch:
            embed = discord.Embed(
                title="🤖 全コマンド一覧",
                colour=0x1ABC9C,
            )
            embed.add_field(
                name="✈️ フライト",
                value="`/flights` `/monitor`",
                inline=True,
            )
            embed.add_field(
                name="🏨 ホテル",
                value="`/hotels` `/hotel-save` `/hotel-list`",
                inline=True,
            )
            embed.add_field(
                name="📋 旅程",
                value="`/plan` `/itinerary`",
                inline=True,
            )
            embed.add_field(
                name="💰 経費",
                value="`/expense` `/budget`",
                inline=True,
            )
            embed.add_field(
                name="🤖 AI",
                value="`/ask`",
                inline=True,
            )
            embed.add_field(
                name="📊 その他",
                value="`/dashboard` `/ping`",
                inline=True,
            )
            embed.set_footer(text="このチャンネルでコマンドを試してみよう！")
            await ch.send(embed=embed)
            print(f"Sent to #{ch.name}")

        print("All guides sent!")
        await client.close()

    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
