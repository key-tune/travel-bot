"""Background price monitor using APScheduler."""

import logging
from datetime import datetime

from database import get_db
from services.serpapi_client import SerpApiClient

log = logging.getLogger(__name__)


class PriceMonitor:
    def __init__(self, bot):
        self.bot = bot
        self.serpapi = SerpApiClient()

    async def check_prices(self) -> list[dict]:
        """Check all active monitor routes and return alerts."""
        db = await get_db()
        alerts = []

        try:
            cursor = await db.execute(
                "SELECT * FROM monitor_routes WHERE active = 1"
            )
            routes = await cursor.fetchall()

            for route in routes:
                origin = route["origin"]
                dest = route["destination"]
                date_from = route["date_from"]
                route_key = f"{origin}-{dest}"

                if not date_from:
                    continue

                data = await self.serpapi.search_flights(
                    departure_id=origin,
                    arrival_id=dest,
                    outbound_date=date_from,
                )
                price, airline = self.serpapi.parse_best_price(data)

                if price is None:
                    continue

                # Save snapshot
                await db.execute(
                    """INSERT INTO price_snapshots
                       (route, date, price, currency, airline, source)
                       VALUES (?, ?, ?, 'JPY', ?, 'serpapi')""",
                    (route_key, date_from, price, airline),
                )

                # Check if this is a new low
                cursor2 = await db.execute(
                    """SELECT MIN(price) as min_price FROM price_snapshots
                       WHERE route = ? AND date = ?
                       AND id != last_insert_rowid()""",
                    (route_key, date_from),
                )
                row = await cursor2.fetchone()
                prev_min = row["min_price"] if row and row["min_price"] else None

                if prev_min is not None and price < prev_min:
                    alerts.append({
                        "route": route_key,
                        "date": date_from,
                        "price": price,
                        "prev_min": prev_min,
                        "airline": airline,
                        "channel_id": route["channel_id"],
                        "drop": prev_min - price,
                    })

            await db.commit()
        finally:
            await db.close()

        return alerts

    async def run_check_and_notify(self):
        """Run price check and send Discord alerts."""
        log.info("Running scheduled price check …")
        try:
            alerts = await self.check_prices()
            for alert in alerts:
                ch_id = alert.get("channel_id")
                if not ch_id:
                    continue
                channel = self.bot.get_channel(int(ch_id))
                if not channel:
                    continue

                await channel.send(
                    f"✈️ **価格アラート** {alert['route']} ({alert['date']})\n"
                    f"💰 ¥{alert['price']:,.0f} ({alert['airline']})\n"
                    f"📉 過去最安より **¥{alert['drop']:,.0f}** 安い！"
                )
        except Exception:
            log.exception("Price monitor check failed")
