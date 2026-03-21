"""Browser cog — take screenshots and extract data from web pages via Playwright."""

import io
import logging
import os

import discord
from discord import app_commands
from discord.ext import commands
from playwright.async_api import async_playwright

from config import COLOUR_DASH

log = logging.getLogger(__name__)

WEB_URL = "https://orfevre.xyz/philippines/"
WEB_LOGIN_URL = f"{WEB_URL}login"


class BrowseCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._browser = None
        self._context = None
        self._page = None
        self._pw = None
        self._logged_in = False

    async def _ensure_browser(self):
        if self._page and not self._page.is_closed():
            return

        if self._pw is None:
            self._pw = await async_playwright().start()

        self._browser = await self._pw.chromium.launch(headless=True)
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 800},
            locale="ja-JP",
        )
        self._page = await self._context.new_page()
        self._logged_in = False

    async def _ensure_login(self):
        await self._ensure_browser()
        if self._logged_in:
            return

        await self._page.goto(WEB_LOGIN_URL, wait_until="networkidle")

        # Select member
        dropdown = self._page.locator("#memberSelect, [class*=select], div:has-text('メンバーを選択')")
        try:
            await dropdown.first.click(timeout=3000)
            wako_option = self._page.locator("div:has-text('wako')").first
            await wako_option.click(timeout=3000)
        except Exception:
            pass

        # Enter password
        pw_input = self._page.locator("#loginPw")
        await pw_input.fill(os.getenv("WEB_PASSWORD", "zHkb7W5z9j4NHn4"))

        # Click login
        login_btn = self._page.locator("#loginBtn")
        await login_btn.click()

        await self._page.wait_for_load_state("networkidle")
        self._logged_in = True
        log.info("Browser logged in to web app")

    async def _take_screenshot(self) -> bytes:
        return await self._page.screenshot(full_page=False)

    async def cog_unload(self):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    @app_commands.command(name="browse", description="Webページのスクリーンショットを撮影")
    @app_commands.describe(
        page="表示するページ",
    )
    @app_commands.choices(
        page=[
            app_commands.Choice(name="ホーム", value="home"),
            app_commands.Choice(name="スケジュール", value="schedule"),
            app_commands.Choice(name="やりたいこと", value="wishlist"),
            app_commands.Choice(name="TODO", value="todo"),
            app_commands.Choice(name="割り勘", value="warikan"),
            app_commands.Choice(name="持ち物", value="packing"),
            app_commands.Choice(name="基本情報", value="info"),
        ]
    )
    async def browse(
        self,
        interaction: discord.Interaction,
        page: str = "home",
    ):
        await interaction.response.defer()

        try:
            await self._ensure_login()

            # Navigate by clicking bottom nav buttons
            page_map = {
                "home": "ホーム",
                "schedule": "スケジュール",
                "wishlist": "やりたいこと",
                "todo": "TODO",
                "warikan": "割り勘",
                "packing": "持ち物",
                "info": "基本情報",
            }

            nav_text = page_map.get(page, "ホーム")
            nav_btn = self._page.locator(f"button:has-text('{nav_text}')").first
            await nav_btn.click(timeout=5000)
            await self._page.wait_for_load_state("networkidle")
            await self._page.wait_for_timeout(500)

            screenshot = await self._take_screenshot()

            file = discord.File(
                io.BytesIO(screenshot),
                filename=f"web_{page}.png",
            )
            embed = discord.Embed(
                title=f"🌐 Webページ: {nav_text}",
                colour=COLOUR_DASH,
                url=WEB_URL,
            )
            embed.set_image(url=f"attachment://web_{page}.png")
            embed.set_footer(text="🔗 https://orfevre.xyz/philippines/")

            await interaction.followup.send(embed=embed, file=file)

        except Exception as e:
            log.exception("Browse command failed")
            await interaction.followup.send(f"❌ ブラウザエラー: {e}")

    @app_commands.command(name="web-capture", description="任意のURLのスクリーンショット")
    @app_commands.describe(url="スクリーンショットを撮るURL")
    async def web_capture(self, interaction: discord.Interaction, url: str):
        await interaction.response.defer()
        try:
            await self._ensure_browser()
            await self._page.goto(url, wait_until="networkidle", timeout=15000)
            await self._page.wait_for_timeout(1000)

            screenshot = await self._take_screenshot()
            file = discord.File(io.BytesIO(screenshot), filename="capture.png")

            embed = discord.Embed(title="📸 Webキャプチャ", colour=COLOUR_DASH)
            embed.set_image(url="attachment://capture.png")
            embed.add_field(name="URL", value=url, inline=False)

            await interaction.followup.send(embed=embed, file=file)
            self._logged_in = False  # Reset login state since we navigated away
        except Exception as e:
            log.exception("Web capture failed")
            await interaction.followup.send(f"❌ キャプチャエラー: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(BrowseCog(bot))
