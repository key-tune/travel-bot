"""SerpApi Google Flights client for price monitoring."""

import os
import logging

import httpx

log = logging.getLogger(__name__)

SERPAPI_URL = "https://serpapi.com/search"


class SerpApiClient:
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY", "")
        self._client = httpx.AsyncClient(timeout=30)

    async def search_flights(
        self,
        departure_id: str,
        arrival_id: str,
        outbound_date: str,
        currency: str = "JPY",
        hl: str = "ja",
    ) -> dict:
        """Search Google Flights via SerpApi.

        Returns raw response dict with best_flights, other_flights, etc.
        """
        if not self.api_key:
            log.warning("SERPAPI_KEY not set, skipping search")
            return {}

        params = {
            "engine": "google_flights",
            "departure_id": departure_id,
            "arrival_id": arrival_id,
            "outbound_date": outbound_date,
            "currency": currency,
            "hl": hl,
            "type": "2",  # one-way
            "api_key": self.api_key,
        }

        try:
            resp = await self._client.get(SERPAPI_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            log.error("SerpApi search failed: %s", e.response.text)
            return {}

    def parse_best_price(self, data: dict) -> tuple[float | None, str | None]:
        """Extract cheapest price from SerpApi response."""
        best = None
        airline = None
        for flight_list_key in ("best_flights", "other_flights"):
            for flight in data.get(flight_list_key, []):
                price = flight.get("price")
                if price is not None and (best is None or price < best):
                    best = price
                    legs = flight.get("flights", [])
                    airline = legs[0].get("airline", "??") if legs else None
        return best, airline

    async def close(self):
        await self._client.aclose()
