"""Travel configuration — Cebu trip parameters."""

from dataclasses import dataclass, field

# ── Airports ──────────────────────────────────────────────
ORIGIN_CEBU = "CEB"
DEST_NARITA = "NRT"
DEST_HANEDA = "HND"
DEST_CENTRAIR = "NGO"

# ── Return routes ─────────────────────────────────────────
# 6 people: CEB → NRT or HND (cheapest wins)
# 1 person: CEB → NGO
RETURN_ROUTES_MAIN = [
    {"origin": ORIGIN_CEBU, "destination": DEST_NARITA},
    {"origin": ORIGIN_CEBU, "destination": DEST_HANEDA},
]
RETURN_ROUTE_NGO = {"origin": ORIGIN_CEBU, "destination": DEST_CENTRAIR}

GROUP_SIZE = 7
MAIN_GROUP_SIZE = 6  # NRT/HND group
NGO_GROUP_SIZE = 1

# ── Confirmed flights ────────────────────────────────────
RETURN_FLIGHT_MAIN = {
    "flight": "5J5064",
    "airline": "セブパシフィック航空",
    "date": "2026-06-28",
    "departure": "04:30",
    "arrival": "10:40",
    "duration": "5時間10分",
    "origin": "CEB マクタン・セブ国際空港T2",
    "destination": "NRT 成田国際空港T2",
    "price_per_person": 39420,
    "booking_ref": "1385432295606705",
}
# TODO: NGO便の情報が入り次第追加
RETURN_FLIGHT_NGO = None

# ── Trip dates ────────────────────────────────────────────
TRIP_START = "2026-06-25"
RETURN_DATE = "2026-06-28"
TRIP_DAYS = 4  # 3泊4日

# ── Members ───────────────────────────────────────────────
MEMBERS = {
    "wako": "わこ",
    "emura": "えむら",
    "hachiga": "はちが",
    "miyabayashi": "みやばやし",
    "kusama": "くさま",
    "masataka": "まさたか",
    "togo": "とおご",
}

# ── Web app ───────────────────────────────────────────────
WEB_URL = "https://orfevre.xyz/philippines/"

# ── Defaults ──────────────────────────────────────────────
DEFAULT_CURRENCY = "JPY"
DEFAULT_ADULTS = 1

# ── Price monitor ─────────────────────────────────────────
MONITOR_INTERVAL_HOURS = 6

# ── Hotel search areas (lat, lng, radius km) ─────────────
HOTEL_AREAS = {
    "cebu_city": {"lat": 10.3157, "lng": 123.8854, "radius": 5, "label": "セブシティ"},
    "mactan": {"lat": 10.3103, "lng": 123.9494, "radius": 5, "label": "マクタン島"},
    "resort": {"lat": 10.2700, "lng": 123.9600, "radius": 10, "label": "リゾートエリア"},
}

# ── Embed colours ─────────────────────────────────────────
COLOUR_FLIGHT = 0x3498DB
COLOUR_HOTEL = 0x2ECC71
COLOUR_PLAN = 0xF39C12
COLOUR_BUDGET = 0xE74C3C
COLOUR_AI = 0x9B59B6
COLOUR_DASH = 0x1ABC9C
