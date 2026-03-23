"""Travel Planning Discord Bot — entry point."""

import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import init_db

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("travel-bot")

COGS = [
    "cogs.setup",
    "cogs.flights",         # /flights (往路・復路検索)
    "cogs.listener",        # 自然言語応答 (bot呼びかけ時)
    "cogs.web_sync",        # /web-schedule, /web-expenses etc (Web読み取り)
    "cogs.web_write",       # /want, /todo, /pay (Web書き込み)
    "cogs.research",        # /research, /research-hotels etc
    "cogs.menu",            # /menu (ボタンUI)
    "cogs.travel_info",     # /travel-info, /emergency
    "cogs.ask",             # /ask (AI質問)
    "cogs.browse",          # /browse (Webスクショ)
    # 以下はWeb側に機能があるため無効化
    # "cogs.hotels",        # → Web "やりたいこと" + /research-hotels
    # "cogs.planner",       # → Web スケジュール
    # "cogs.budget",        # → Web 割り勘 + /pay
    # "cogs.dashboard",     # → Web ホーム画面
]


class TravelBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        log.info("Initialising database …")
        await init_db()

        for cog in COGS:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog: %s", cog)
            except Exception:
                log.exception("Failed to load cog: %s", cog)

        guild_id = os.getenv("DISCORD_GUILD_ID")
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            log.info("Synced commands to guild %s", guild_id)
        else:
            await self.tree.sync()
            log.info("Synced commands globally")

    async def on_ready(self) -> None:
        log.info("Logged in as %s (ID: %s)", self.user, self.user.id)
        log.info("Ready!")


async def main() -> None:
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN not set in .env")
    bot = TravelBot()

    @bot.tree.command(name="ping", description="動作確認")
    async def ping(interaction: discord.Interaction):
        await interaction.response.send_message(
            f"🏖️ Pong! Latency: {bot.latency*1000:.0f}ms"
        )

    await bot.start(token)


if __name__ == "__main__":
    asyncio.run(main())
