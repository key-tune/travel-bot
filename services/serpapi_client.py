"""SerpApi client for Google Flights and Google Hotels search."""

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
        """Search Google Flights via SerpApi."""
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
            log.error("SerpApi flight search failed: %s", e.response.text)
            return {}

    async def search_hotels(
        self,
        query: str,
        check_in: str = "",
        check_out: str = "",
        adults: int = 2,
        currency: str = "JPY",
        hl: str = "ja",
    ) -> dict:
        """Search Google Hotels via SerpApi."""
        if not self.api_key:
            log.warning("SERPAPI_KEY not set, skipping search")
            return {}

        params = {
            "engine": "google_hotels",
            "q": query,
            "currency": currency,
            "hl": hl,
            "adults": adults,
            "api_key": self.api_key,
        }
        if check_in:
            params["check_in_date"] = check_in
        if check_out:
            params["check_out_date"] = check_out

        try:
            resp = await self._client.get(SERPAPI_URL, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            log.error("SerpApi hotel search failed: %s", e.response.text)
            return {}

    def parse_flights(self, data: dict) -> list[dict]:
        """Parse flight results into a simple list."""
        flights = []
        for key in ("best_flights", "other_flights"):
            for flight in data.get(key, []):
                legs = flight.get("flights", [])
                if not legs:
                    continue
                first = legs[0]
                last = legs[-1]
                flights.append({
                    "price": flight.get("price"),
                    "airline": first.get("airline", "??"),
                    "departure_time": first.get("departure_airport", {}).get("time", ""),
                    "departure_airport": first.get("departure_airport", {}).get("id", ""),
                    "arrival_time": last.get("arrival_airport", {}).get("time", ""),
                    "arrival_airport": last.get("arrival_airport", {}).get("id", ""),
                    "duration": flight.get("total_duration", 0),
                    "stops": len(legs) - 1,
                    "type": key,
                })
        flights.sort(key=lambda x: x["price"] or 999999)
        return flights

    def parse_best_price(self, data: dict) -> tuple[float | None, str | None]:
        """Extract cheapest price from flight response."""
        flights = self.parse_flights(data)
        if flights and flights[0]["price"]:
            return flights[0]["price"], flights[0]["airline"]
        return None, None

    def parse_hotels(self, data: dict) -> list[dict]:
        """Parse hotel results into a simple list."""
        hotels = []
        for prop in data.get("properties", []):
            hotels.append({
                "name": prop.get("name", "不明"),
                "price": prop.get("total_rate", {}).get("extracted_lowest"),
                "rating": prop.get("overall_rating"),
                "reviews": prop.get("reviews"),
                "type": prop.get("type", ""),
                "amenities": prop.get("amenities", [])[:5],
                "thumbnail": prop.get("images", [{}])[0].get("thumbnail") if prop.get("images") else None,
            })
        return hotels

    async def close(self):
        await self._client.aclose()
