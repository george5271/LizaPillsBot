"""
config.py — Central configuration for LizaPillsBot.

All secrets are loaded from the .env file (never hard-coded).
All tunable constants live here so nothing is scattered across the codebase.
"""

import os
import time
from dotenv import load_dotenv

load_dotenv()

# ── Credentials (loaded from .env) ───────────────────────────────────────────
try:
    BOT_TOKEN: str = os.environ['BOT_TOKEN']
except KeyError:
    raise RuntimeError("BOT_TOKEN is not set. Add it to your .env file.")

try:
    ADMIN_CHAT_ID: int = int(os.environ['ADMIN_CHAT_ID'])
except KeyError:
    raise RuntimeError("ADMIN_CHAT_ID is not set. Add your Telegram numeric user ID to .env.")
except ValueError:
    raise RuntimeError("ADMIN_CHAT_ID must be a valid integer (your Telegram user ID).")

try:
    LIZA_CHAT_ID: int = int(os.environ['LIZA_CHAT_ID'])
except KeyError:
    raise RuntimeError("LIZA_CHAT_ID is not set. Add Liza's Telegram numeric user ID to .env.")
except ValueError:
    raise RuntimeError("LIZA_CHAT_ID must be a valid integer (Liza's Telegram user ID).")

# ── Timezone & persistence ────────────────────────────────────────────────────
TIMEZONE = 'Europe/Moscow'
os.environ['TZ'] = TIMEZONE
time.tzset()

DATA_FILE = 'liza_data.json'

# ── Default schedules ─────────────────────────────────────────────────────────
# Pill: first reminder 13:35, second 13:50, then every 120 min via persistent job
DEFAULT_PILL_SCHEDULE  = ['13:35', '13:50']
DEFAULT_PILL_INTERVAL  = 120   # minutes between persistent reminders after last planned time

# Sleep: one reminder per night at a random time between 23:30 and 01:30 (scheduled at startup)
SLEEP_WINDOW_START = (23, 30)   # (hour, minute) — start of random window
SLEEP_WINDOW_END   = (1, 30)    # (hour, minute) — end (next day)
