"""Amadeus API client with OAuth2 token management."""

import os
import time
import logging
from dataclasses import dataclass

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://test.api.amadeus.com"  # Use test env (free tier)


@dataclass
class FlightOffer:
    airline: str
    price: float
    currency: str
    departure: str
    arrival: str
    duration: str
    stops: int
    segments: list


class AmadeusClient:
    def __init__(self):
        self.api_key = os.getenv("AMADEUS_API_KEY", "")
        self.api_secret = os.getenv("AMADEUS_API_SECRET", "")
        self._token: str | None = None
        self._token_expires: float = 0
        self._client = httpx.AsyncClient(timeout=30)

    async def _ensure_token(self) -> str:
        if self._token and time.time() < self._token_expires - 60:
            return self._token

        resp = await self._client.post(
            f"{BASE_URL}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.api_key,
                "client_secret": self.api_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"]
        log.info("Amadeus token refreshed, expires in %ds", data["expires_in"])
        return self._token

    async def _get(self, path: str, params: dict) -> dict:
        token = await self._ensure_token()
        resp = await self._client.get(
            f"{BASE_URL}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        resp.raise_for_status()
        return resp.json()

    async def search_flights(
        self,
        origin: str,
        destination: str,
        departure_date: str,
        adults: int = 1,
        currency: str = "JPY",
        max_results: int = 5,
    ) -> list[FlightOffer]:
        """Search one-way flights."""
        try:
            data = await self._get(
                "/v2/shopping/flight-offers",
                {
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDate": departure_date,
                    "adults": adults,
                    "currencyCode": currency,
                    "max": max_results,
                    "nonStop": "false",
                },
            )
        except httpx.HTTPStatusError as e:
            log.error("Amadeus flight search failed: %s", e.response.text)
            return []

        offers = []
        for item in data.get("data", []):
            itin = item["itineraries"][0]
            segments = itin["segments"]
            offers.append(
                FlightOffer(
                    airline=segments[0].get("carrierCode", "??"),
                    price=float(item["price"]["total"]),
                    currency=item["price"]["currency"],
                    departure=segments[0]["departure"]["at"],
                    arrival=segments[-1]["arrival"]["at"],
                    duration=itin.get("duration", ""),
                    stops=len(segments) - 1,
                    segments=segments,
                )
            )
        return offers

    async def search_hotels(
        self,
        lat: float,
        lng: float,
        radius: int = 5,
        check_in: str | None = None,
        check_out: str | None = None,
        adults: int = 2,
        currency: str = "JPY",
        max_results: int = 10,
    ) -> list[dict]:
        """Search hotels by geocode."""
        try:
            data = await self._get(
                "/v1/reference-data/locations/hotels/by-geocode",
                {
                    "latitude": lat,
                    "longitude": lng,
                    "radius": radius,
                    "radiusUnit": "KM",
                    "hotelSource": "ALL",
                },
            )
        except httpx.HTTPStatusError as e:
            log.error("Amadeus hotel search failed: %s", e.response.text)
            return []

        hotels = data.get("data", [])[:max_results]
        return hotels

    async def close(self):
        await self._client.aclose()
