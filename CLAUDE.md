# Travel Planning Discord Bot

セブ旅行計画用Discord Bot。7人グループ。

## Tech Stack
- Python 3.12 + discord.py + aiosqlite
- Amadeus API (flights/hotels), SerpApi (Google Flights monitoring)
- Anthropic Claude Sonnet (AI assistant)
- APScheduler (background price checks)

## Commands
- `/ping` — 動作確認
- `/flights <date>` — 復路フライト検索 (CEB→NRT/HND/NGO)
- `/monitor start|stop|status <date>` — 価格監視
- `/hotels [area] [budget]` — ホテル検索
- `/hotel-save`, `/hotel-list` — お気に入りホテル管理
- `/plan <date> <title>` — 旅程追加 (投票付き)
- `/itinerary [date]` — 旅程一覧
- `/expense` — 経費登録
- `/budget` — 精算計算
- `/ask <question>` — AI旅行アシスタント
- `/dashboard` — 全体サマリー

## Running
```
cd C:\Users\wako2\travel-bot
uv run python bot.py
```

## Project Structure
- `bot.py` — entry point
- `config.py` — trip constants
- `database.py` — SQLite schema
- `cogs/` — Discord slash command handlers
- `services/` — API clients (Amadeus, SerpApi, Claude)
