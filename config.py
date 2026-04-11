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

# ── Default schedules (used on first run or after /reset_*) ──────────────────
DEFAULT_PILL_SCHEDULE  = ['13:35', '13:40', '13:45', '13:50']
DEFAULT_PILL_INTERVAL  = 10   # minutes between persistent reminders
DEFAULT_SLEEP_SCHEDULE = ['22:00', '23:00', '23:30', '00:00']
