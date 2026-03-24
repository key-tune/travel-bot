"""Client for ga11agher's travel web app (orfevre.xyz).
API Reference: C:/Users/wako2/Downloads/API_REFERENCE.md
"""

import os
import logging

import httpx

log = logging.getLogger(__name__)

BASE_URL = "https://orfevre.xyz/philippines"
API_URL = f"{BASE_URL}/api"
SHIORI_URL = f"{API_URL}/shiori"


class WebClient:
    def __init__(self):
        token = os.getenv("WEB_API_TOKEN", "")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        self._client = httpx.AsyncClient(timeout=15, headers=headers)
        self._token = token

    async def _ensure_login(self):
        if self._token:
            return
        resp = await self._client.post(
            f"{API_URL}/login",
            json={
                "member_id": os.getenv("WEB_USER", "wako"),
                "password": os.getenv("WEB_PASSWORD", ""),
            },
        )
        data = resp.json()
        if data.get("ok"):
            self._token = "session"
            log.info("Logged in to web app as %s", data.get("member"))
        else:
            log.error("Web login failed: %s", data)

    # ── Members ──
    async def get_members(self) -> list[dict]:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/members")
        return resp.json()

    # ── Schedule ──
    async def get_schedule(self) -> list[dict]:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/schedule")
        return resp.json()

    async def add_schedule(self, day: int, time_slot: str, title: str,
                           description: str = "", members: str = "",
                           end_time: str = "") -> dict:
        await self._ensure_login()
        # All fields required by server
        resp = await self._client.post(
            f"{SHIORI_URL}/schedule",
            json={
                "day": day,
                "time_slot": time_slot,
                "title": title,
                "description": description,
                "members": members,
                "end_time": end_time,
            },
        )
        return resp.json()

    # ── Wishes ──
    async def get_wishes(self) -> list[dict]:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/wishes")
        return resp.json()

    async def add_wish(self, title: str, description: str = "",
                       image_url: str = "", tags: str = "") -> dict:
        await self._ensure_login()
        payload = {"title": title}
        if description:
            payload["description"] = description
        if image_url:
            payload["image_url"] = image_url
        if tags:
            payload["tags"] = tags
        resp = await self._client.post(f"{SHIORI_URL}/wishes", json=payload)
        return resp.json()

    async def vote_wish(self, wish_id: int) -> dict:
        await self._ensure_login()
        resp = await self._client.post(f"{SHIORI_URL}/wishes/{wish_id}/vote")
        return resp.json()

    # ── Todos ──
    async def get_todos(self) -> list[dict]:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/todos")
        return resp.json()

    async def add_todo(self, title: str, assignee_id: str = "",
                       tags: str = "") -> dict:
        await self._ensure_login()
        payload = {"title": title}
        if assignee_id:
            payload["assignee_id"] = assignee_id
        if tags:
            payload["tags"] = tags
        resp = await self._client.post(f"{SHIORI_URL}/todos", json=payload)
        return resp.json()

    async def toggle_todo(self, todo_id: int) -> dict:
        await self._ensure_login()
        resp = await self._client.patch(f"{SHIORI_URL}/todos/{todo_id}/toggle")
        return resp.json()

    # ── Expenses ──
    async def get_expenses(self) -> list[dict]:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/expenses")
        return resp.json()

    async def add_expense(self, title: str, amount: float, paid_by: str,
                          split_among: str, currency: str = "JPY") -> dict:
        await self._ensure_login()
        resp = await self._client.post(
            f"{SHIORI_URL}/expenses",
            json={
                "title": title,
                "amount": amount,
                "currency": currency,
                "paid_by": paid_by,
                "split_among": split_among,
            },
        )
        return resp.json()

    async def get_settlements(self) -> dict:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/settlements")
        return resp.json()

    # ── Rate ──
    async def get_rate(self) -> dict:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/rate")
        return resp.json()

    # ── News ──
    async def get_news(self) -> list[dict]:
        await self._ensure_login()
        resp = await self._client.get(f"{SHIORI_URL}/news")
        return resp.json()

    async def close(self):
        await self._client.aclose()
