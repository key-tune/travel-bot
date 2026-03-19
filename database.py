"""SQLite database initialisation and helpers."""

import aiosqlite
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "travel.db")


async def get_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    return db


async def init_db() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = await get_db()
    try:
        # Price snapshots (flight monitor)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS price_snapshots (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                route       TEXT    NOT NULL,  -- e.g. CEB-NRT
                date        TEXT    NOT NULL,  -- flight date
                price       REAL    NOT NULL,
                currency    TEXT    NOT NULL DEFAULT 'JPY',
                airline     TEXT,
                source      TEXT,              -- amadeus / serpapi
                fetched_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Favourite hotels
        await db.execute("""
            CREATE TABLE IF NOT EXISTS hotels (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                area        TEXT,
                price_per_night REAL,
                currency    TEXT    DEFAULT 'JPY',
                rating      REAL,
                url         TEXT,
                added_by    TEXT,
                added_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Hotel votes
        await db.execute("""
            CREATE TABLE IF NOT EXISTS hotel_votes (
                hotel_id    INTEGER NOT NULL REFERENCES hotels(id),
                user_id     TEXT    NOT NULL,
                vote        INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (hotel_id, user_id)
            )
        """)

        # Itinerary items
        await db.execute("""
            CREATE TABLE IF NOT EXISTS itinerary (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                day_date    TEXT    NOT NULL,
                time_slot   TEXT,
                title       TEXT    NOT NULL,
                description TEXT,
                category    TEXT,
                added_by    TEXT,
                approved    INTEGER NOT NULL DEFAULT 0,
                added_at    TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Itinerary votes
        await db.execute("""
            CREATE TABLE IF NOT EXISTS itinerary_votes (
                item_id     INTEGER NOT NULL REFERENCES itinerary(id),
                user_id     TEXT    NOT NULL,
                vote        INTEGER NOT NULL,  -- 1=approve, -1=reject
                PRIMARY KEY (item_id, user_id)
            )
        """)

        # Budget / expenses
        await db.execute("""
            CREATE TABLE IF NOT EXISTS expenses (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                description TEXT    NOT NULL,
                amount      REAL    NOT NULL,
                currency    TEXT    NOT NULL DEFAULT 'JPY',
                paid_by     TEXT    NOT NULL,
                split_among TEXT    NOT NULL,  -- JSON list of user IDs
                category    TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Monitor watchlist
        await db.execute("""
            CREATE TABLE IF NOT EXISTS monitor_routes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                origin      TEXT    NOT NULL,
                destination TEXT    NOT NULL,
                date_from   TEXT,
                date_to     TEXT,
                active      INTEGER NOT NULL DEFAULT 1,
                channel_id  TEXT,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        await db.commit()
    finally:
        await db.close()
