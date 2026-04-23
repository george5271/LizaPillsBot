"""
storage.py — Persistent data layer for LizaPillsBot.

All read/write operations on liza_data.json go through DataStorage.
Uses an atomic write pattern (write to .tmp → os.replace) to prevent
JSON corruption if the process is killed mid-write.

save() is async (aiofiles) and guarded by asyncio.Lock to prevent
concurrent writes from scheduler jobs and aiogram handlers.
"""

import asyncio
import json
import logging
import os
import aiofiles
from calendar import monthrange
from datetime import datetime

from config import (
    DATA_FILE,
    DEFAULT_PILL_INTERVAL,
    DEFAULT_PILL_SCHEDULE,
)

logger = logging.getLogger(__name__)


class DataStorage:
    def __init__(self):
        self._lock = asyncio.Lock()
        self.data = self._load()

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        """Load data from JSON file, applying defaults for any missing keys."""
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            data.setdefault('pill_schedule', DEFAULT_PILL_SCHEDULE)
            data.setdefault('pill_interval', DEFAULT_PILL_INTERVAL)
            # Remove legacy sleep_schedule key if present
            data.pop('sleep_schedule', None)
            logger.info(f"Data loaded from {DATA_FILE}.")
            return data
        except FileNotFoundError:
            logger.warning(f"{DATA_FILE} not found — starting with fresh state.")
            return {
                'calendar':          {},
                'streak':            0,
                'pill_status_today': None,
                'last_check_date':   None,
                'pill_schedule':     DEFAULT_PILL_SCHEDULE.copy(),
                'pill_interval':     DEFAULT_PILL_INTERVAL,
            }

    async def save(self) -> None:
        """
        Atomically persist data to disk (async, under lock).

        Writes to a .tmp file first, then renames it over the real file.
        asyncio.Lock prevents concurrent writes from racing each other.
        """
        async with self._lock:
            tmp_file = DATA_FILE + '.tmp'
            async with aiofiles.open(tmp_file, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(self.data, ensure_ascii=False, indent=2))
            os.replace(tmp_file, DATA_FILE)
            logger.debug("Data saved.")

    # ── Daily pill tracking ───────────────────────────────────────────────────

    def _today(self) -> str:
        return datetime.now().strftime('%Y-%m-%d')

    def is_locked(self) -> bool:
        """Return True if the pill status has already been recorded for today."""
        return bool(
            self.data.get('pill_status_today')
            and self.data.get('last_check_date') == self._today()
        )

    async def mark_day(self, status: str) -> bool:
        """
        Record today's pill status ('taken' or 'missed').
        Returns False (and does nothing) if status was already set today.
        """
        if self.is_locked():
            return False
        today = self._today()
        self.data['calendar'][today] = status
        self.data['pill_status_today'] = status
        self.data['last_check_date'] = today
        self.data['streak'] = (self.data.get('streak', 0) + 1) if status == 'taken' else 0
        await self.save()
        return True

    async def reset_daily(self) -> None:
        """Called at midnight — clears today's pill status so the day starts fresh."""
        today = self._today()
        if self.data.get('last_check_date') != today:
            logger.info(f"Daily reset for {today}.")
            self.data['pill_status_today'] = None
            self.data['last_check_date'] = today
            await self.save()

    # ── Calendar & stats ─────────────────────────────────────────────────────

    def get_calendar(self, year: int, month: int) -> dict:
        """Return a {day_number: status} dict for every day in the given month."""
        days = monthrange(year, month)[1]
        return {
            day: self.data['calendar'].get(f"{year}-{month:02d}-{day:02d}", 'unknown')
            for day in range(1, days + 1)
        }

    def get_stats(self, year: int, month: int) -> dict:
        cal = self.get_calendar(year, month)
        taken  = sum(1 for v in cal.values() if v == 'taken')
        missed = sum(1 for v in cal.values() if v == 'missed')
        total  = taken + missed
        return {
            'taken':      taken,
            'missed':     missed,
            'total':      total,
            'percentage': (taken / total * 100) if total > 0 else 0,
            'streak':     self.data.get('streak', 0),
        }
