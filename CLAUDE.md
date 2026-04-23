# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Bot

```bash
source venv/bin/activate
python3 main.py
```

Requires a `.env` file in the root with:
```
BOT_TOKEN=...
ADMIN_CHAT_ID=...   # numeric Telegram user ID
LIZA_CHAT_ID=...    # numeric Telegram user ID
```

## Installing Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Architecture

The bot uses **aiogram 3** (async Telegram framework) with **APScheduler** for cron jobs. All async singletons — `bot`, `dp` (Dispatcher), `scheduler`, and `storage` — are instantiated once in `core.py` and imported everywhere else.

**Data flow:**
- `main.py` — entry point: wires the router, registers all cron jobs, starts polling
- `core.py` — singleton instances (bot, dispatcher, scheduler, storage)
- `handlers.py` — aiogram Router with all command/button handlers; uses `AdminFilter`/`LizaFilter` for access control
- `alarms.py` — scheduled job functions + `send_both()` (sends to Liza and mirrors to Admin)
- `storage.py` — `DataStorage` class that reads/writes `liza_data.json` atomically via a `.tmp` rename pattern
- `config.py` — all constants and `.env` loading; raises `RuntimeError` on missing secrets
- `content.py` — randomized Russian text arrays (`TEXTS`) and Yandex Disk image URL pools (`IMAGES`) split into `day` and `sleep` categories
- `filters.py` — `AdminFilter` and `LizaFilter` aiogram message filters

**Scheduling pattern:** `reload_pill_schedule()` and `reload_sleep_schedule()` in `alarms.py` remove all jobs matching `'pill'` or `'sleep'` in their ID, then re-add them from `storage.data`. Call these functions after mutating the schedule in storage.

**`send_both()`** is the core delivery function — every automated message goes through it so the admin always receives a mirrored `📨 [Лизе]` copy.

**Timezone:** All scheduling runs in `Europe/Moscow` (`config.TIMEZONE`). The system `TZ` env var is also set in `config.py`.

**Persistence:** `liza_data.json` is the runtime database (not in git). The `calendar` key stores `{"YYYY-MM-DD": "taken"|"missed"}` entries.
