"""Post confirmed flight info to #お知らせ."""

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
            await client.close()
            return

        announce_cat = discord.utils.get(guild.categories, name="📋 旅行計画")
        if not announce_cat:
            await client.close()
            return
        ch = discord.utils.get(announce_cat.text_channels, name="お知らせ")
        if not ch:
            await client.close()
            return

        embed = discord.Embed(
            title="✈️ フライト確定情報",
            colour=0x3498DB,
        )

        embed.add_field(
            name="🛫 復路（6人）— 確保済み",
            value=(
                "**セブパシフィック航空 5J5064**\n"
                "📅 2026年6月28日\n"
                "🕐 04:30 CEB マクタン・セブ国際空港T2\n"
                "🕙 10:40 NRT 成田国際空港T2\n"
                "⏱️ 5時間10分（直行）\n"
                "💰 ¥39,420/人（6人合計: ¥236,520）\n"
                "📋 予約番号: `1385432295606705`"
            ),
            inline=False,
        )

        embed.add_field(
            name="🛫 復路（1人・NGO）— 未手配",
            value="セブCEB → セントレアNGO\n6/28 or 近い日程で要手配",
            inline=False,
        )

        embed.add_field(
            name="⚠️ 注意事項",
            value=(
                "・帰りは **早朝04:30発** → 前夜の過ごし方要検討\n"
                "・空港には02:30頃到着推奨\n"
                "・最終日のホテルチェックアウト後の荷物管理\n"
                "・フィリピン旅行税について確認が必要"
            ),
            inline=False,
        )

        embed.add_field(
            name="📝 残タスク",
            value=(
                "1. 往路の日程確認・共有\n"
                "2. NGO便の手配（1名）\n"
                "3. ホテル選び\n"
                "4. アクティビティ計画"
            ),
            inline=False,
        )

        msg = await ch.send(embed=embed)
        await msg.pin()
        print("Flight info posted and pinned!")
        await client.close()

    await client.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
