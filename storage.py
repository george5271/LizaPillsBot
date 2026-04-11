"""
storage.py — Persistent data layer for LizaPillsBot.

All read/write operations on liza_data.json go through DataStorage.
Uses an atomic write pattern (write to .tmp → os.replace) to prevent
JSON corruption if the process is killed mid-write.
"""

import json
import logging
import os
from calendar import monthrange
from datetime import datetime

from config import (
    DATA_FILE,
    DEFAULT_PILL_INTERVAL,
    DEFAULT_PILL_SCHEDULE,
    DEFAULT_SLEEP_SCHEDULE,
)

logger = logging.getLogger(__name__)


class DataStorage:
    def __init__(self):
        self.data = self._load()

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load(self) -> dict:
        """Load data from JSON file, applying defaults for any missing keys."""
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # Backfill any keys that were added after first run
            data.setdefault('pill_schedule', DEFAULT_PILL_SCHEDULE)
            data.setdefault('pill_interval', DEFAULT_PILL_INTERVAL)
            data.setdefault('sleep_schedule', DEFAULT_SLEEP_SCHEDULE)
            logger.info(f"Data loaded from {DATA_FILE}.")
            return data
        except FileNotFoundError:
            logger.warning(f"{DATA_FILE} not found — starting with fresh state.")
            return {
                'calendar':         {},
                'streak':           0,
                'pill_status_today': None,
                'last_check_date':  None,
                'pill_schedule':    DEFAULT_PILL_SCHEDULE.copy(),
                'pill_interval':    DEFAULT_PILL_INTERVAL,
                'sleep_schedule':   DEFAULT_SLEEP_SCHEDULE.copy(),
            }

    def save(self) -> None:
        """
        Atomically persist data to disk.

        Writes to a .tmp file first, then renames it over the real file.
        This guarantees the JSON on disk is never half-written — if the
        process crashes mid-write, the previous good file survives.
        """
        tmp_file = DATA_FILE + '.tmp'
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, DATA_FILE)  # atomic on POSIX, near-atomic on Windows
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

    def mark_day(self, status: str) -> bool:
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
        self.save()
        return True

    def reset_daily(self) -> None:
        """Called at midnight — clears today's pill status so the day starts fresh."""
        today = self._today()
        if self.data.get('last_check_date') != today:
            logger.info(f"Daily reset for {today}.")
            self.data['pill_status_today'] = None
            self.data['last_check_date'] = today
            self.save()

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
