"""Hotel search and favourites cog — powered by SerpApi (Google Hotels)."""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from config import COLOUR_HOTEL, HOTEL_AREAS
from services.serpapi_client import SerpApiClient
from database import get_db

log = logging.getLogger(__name__)


class HotelVoteView(discord.ui.View):
    def __init__(self, hotel_id: int):
        super().__init__(timeout=None)
        self.hotel_id = hotel_id

    @discord.ui.button(label="👍", style=discord.ButtonStyle.success, custom_id="hotel_vote_up")
    async def vote_up(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._cast_vote(interaction, 1)

    @discord.ui.button(label="👎", style=discord.ButtonStyle.danger, custom_id="hotel_vote_down")
    async def vote_down(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._cast_vote(interaction, -1)

    async def _cast_vote(self, interaction: discord.Interaction, vote: int):
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO hotel_votes (hotel_id, user_id, vote)
                   VALUES (?, ?, ?)
                   ON CONFLICT(hotel_id, user_id) DO UPDATE SET vote = excluded.vote""",
                (self.hotel_id, str(interaction.user.id), vote),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT SUM(vote) as total FROM hotel_votes WHERE hotel_id = ?",
                (self.hotel_id,),
            )
            row = await cursor.fetchone()
            total = row["total"] or 0
            await interaction.response.send_message(
                f"投票しました！ 現在のスコア: {total:+d}", ephemeral=True
            )
        finally:
            await db.close()


class HotelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.serpapi = SerpApiClient()

    async def cog_unload(self):
        await self.serpapi.close()

    @app_commands.command(name="hotels", description="セブのホテル検索")
    @app_commands.describe(
        area="エリア: cebu_city / mactan / resort",
        check_in="チェックイン日 (YYYY-MM-DD)",
        check_out="チェックアウト日 (YYYY-MM-DD)",
    )
    @app_commands.choices(
        area=[
            app_commands.Choice(name="セブシティ", value="cebu_city"),
            app_commands.Choice(name="マクタン島", value="mactan"),
            app_commands.Choice(name="リゾートエリア", value="resort"),
        ]
    )
    async def hotels(
        self,
        interaction: discord.Interaction,
        area: str = "mactan",
        check_in: str = "",
        check_out: str = "",
    ):
        await interaction.response.defer()

        area_info = HOTEL_AREAS.get(area, HOTEL_AREAS["mactan"])
        query = f"Hotels in {area_info['label']} Cebu Philippines"

        data = await self.serpapi.search_hotels(
            query=query,
            check_in=check_in,
            check_out=check_out,
            adults=2,
        )
        hotels = self.serpapi.parse_hotels(data)

        embed = discord.Embed(
            title=f"🏨 ホテル検索: {area_info['label']}",
            description=f"7人グループ向け | {len(hotels)}件見つかりました",
            colour=COLOUR_HOTEL,
        )

        if not hotels:
            embed.description = "ホテルが見つかりませんでした"
            await interaction.followup.send(embed=embed)
            return

        for i, h in enumerate(hotels[:10], 1):
            price_str = f"¥{h['price']:,}" if h["price"] else "価格不明"
            rating_str = f"⭐{h['rating']}" if h["rating"] else ""
            reviews_str = f"({h['reviews']}件)" if h["reviews"] else ""
            type_str = h["type"] if h["type"] else ""

            embed.add_field(
                name=f"{i}. {h['name']}",
                value=f"💰 {price_str}  {rating_str} {reviews_str}  {type_str}",
                inline=False,
            )

        embed.set_footer(text="💡 /hotel-save <名前> でお気に入りに追加")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="hotel-save", description="ホテルをお気に入りに保存")
    @app_commands.describe(
        name="ホテル名",
        area="エリア",
        price="1泊あたり価格 (JPY)",
        rating="評価 (1-5)",
        url="予約URL",
    )
    async def hotel_save(
        self,
        interaction: discord.Interaction,
        name: str,
        area: str = "",
        price: float = 0.0,
        rating: float = 0.0,
        url: str = "",
    ):
        db = await get_db()
        try:
            cursor = await db.execute(
                """INSERT INTO hotels (name, area, price_per_night, rating, url, added_by)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, area, price, rating, url, str(interaction.user.id)),
            )
            await db.commit()
            hotel_id = cursor.lastrowid

            embed = discord.Embed(
                title=f"⭐ {name} をお気に入りに追加",
                colour=COLOUR_HOTEL,
            )
            if price:
                embed.add_field(name="💰 1泊", value=f"¥{price:,.0f}")
                embed.add_field(
                    name="💰 7人合計(概算)",
                    value=f"¥{price * 3:,.0f}/泊 (3部屋想定)",
                )
            if rating:
                embed.add_field(name="⭐ 評価", value=f"{rating}/5")

            view = HotelVoteView(hotel_id)
            await interaction.response.send_message(embed=embed, view=view)
        finally:
            await db.close()

    @app_commands.command(name="hotel-list", description="お気に入りホテル一覧")
    async def hotel_list(self, interaction: discord.Interaction):
        db = await get_db()
        try:
            cursor = await db.execute(
                """SELECT h.*, COALESCE(SUM(hv.vote), 0) as score
                   FROM hotels h LEFT JOIN hotel_votes hv ON h.id = hv.hotel_id
                   GROUP BY h.id ORDER BY score DESC"""
            )
            hotels = await cursor.fetchall()

            if not hotels:
                await interaction.response.send_message("まだお気に入りホテルがありません。`/hotel-save` で追加！")
                return

            embed = discord.Embed(title="⭐ お気に入りホテル一覧", colour=COLOUR_HOTEL)
            for h in hotels:
                price_str = f"¥{h['price_per_night']:,.0f}/泊" if h["price_per_night"] else "価格未設定"
                rating_str = f"⭐{h['rating']}" if h["rating"] else ""
                score = h["score"]
                embed.add_field(
                    name=f"{'🏆' if score > 0 else '🏨'} {h['name']} [{score:+d}票]",
                    value=f"{price_str}  {rating_str}  {h['area'] or ''}",
                    inline=False,
                )
            await interaction.response.send_message(embed=embed)
        finally:
            await db.close()


async def setup(bot: commands.Bot):
    await bot.add_cog(HotelsCog(bot))
