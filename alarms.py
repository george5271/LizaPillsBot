"""
alarms.py — Scheduled job functions and core message delivery for LizaPillsBot.

send_both() is the single delivery function for all automated messages:
  - sends to Liza with keyboard
  - mirrors to Admin with "📨 [Лизе]" prefix
  - retries up to MAX_RETRIES times on failure before notifying Admin

Pill schedule: two planned times (13:35, 13:50), then persistent every 120 min
anchored to the last planned time (i.e. 15:50, 17:50, 19:50...).

Sleep schedule: one random time per night in the 23:30–01:30 window,
re-scheduled daily at 02:00.
"""

import asyncio
import random
import logging
from datetime import datetime, timedelta, date

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger

from core import bot, storage, scheduler
from content import IMAGES, TEXTS
from config import (
    ADMIN_CHAT_ID, LIZA_CHAT_ID,
    DEFAULT_PILL_SCHEDULE, DEFAULT_PILL_INTERVAL,
    SLEEP_WINDOW_START, SLEEP_WINDOW_END,
    TIMEZONE,
)

import pytz

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2.0   # seconds between retries


def get_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Выпила"), KeyboardButton(text="❌ Не выпила / Пропустила")],
            [KeyboardButton(text="📅 График за месяц")]
        ],
        resize_keyboard=True
    )


async def send_both(text: str = None, photo: str = None) -> None:
    """
    Deliver a message to Liza (with keyboard) and mirror it to Admin.

    Pass `text` for plain messages.
    Pass `photo` + `text` to send a photo where `text` is the caption.
    Retries up to MAX_RETRIES times if Liza's delivery fails.
    """
    reply_kb = get_keyboard()
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if photo:
                await bot.send_photo(LIZA_CHAT_ID, photo, caption=text, reply_markup=reply_kb)
            else:
                await bot.send_message(LIZA_CHAT_ID, text, reply_markup=reply_kb)
            last_exc = None
            break
        except Exception as e:
            last_exc = e
            logger.warning(f"Attempt {attempt}/{MAX_RETRIES} to message Liza failed: {e}")
            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY)

    if last_exc is not None:
        logger.error(f"All {MAX_RETRIES} attempts to message Liza failed: {last_exc}")
        try:
            await bot.send_message(
                ADMIN_CHAT_ID,
                f"⚠️ Не смог отправить Лизе сообщение после {MAX_RETRIES} попыток:\n{last_exc}"
            )
        except Exception as e:
            logger.error(f"Failed to notify Admin about delivery failure: {e}")

    try:
        admin_copy = f"📨 [Лизе] {text}"
        if photo:
            await bot.send_photo(ADMIN_CHAT_ID, photo, caption=admin_copy)
        else:
            await bot.send_message(ADMIN_CHAT_ID, admin_copy)
    except Exception as e:
        logger.warning(f"Failed to send admin copy: {e}")


# ── Pill reminders ────────────────────────────────────────────────────────────

async def send_pill_reminder() -> None:
    if storage.data.get('pill_status_today') in ('taken', 'missed'):
        return
    logger.info("Sending scheduled pill reminder.")
    await send_both(photo=random.choice(IMAGES['day']), text=random.choice(TEXTS['pill_reminder']))


async def send_persistent() -> None:
    """Persistent reminder — fires every 120 min after last planned pill time."""
    if storage.data.get('pill_status_today') in ('taken', 'missed'):
        return
    pill_schedule = storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)
    last_scheduled = pill_schedule[-1]
    last_time = datetime.strptime(last_scheduled, '%H:%M').time()
    if datetime.now().time() < last_time:
        # Not yet past the last planned reminder — skip
        return
    logger.info("Sending persistent pill reminder.")
    await send_both(photo=random.choice(IMAGES['day']), text=random.choice(TEXTS['persistent']))


# ── Motivation ────────────────────────────────────────────────────────────────

async def send_motivation() -> None:
    logger.info("Sending motivation.")
    text_pool = TEXTS['motivation'] if random.random() < 0.7 else TEXTS['quotes']
    await send_both(photo=random.choice(IMAGES['day']), text=random.choice(text_pool))


# ── Sleep reminder ────────────────────────────────────────────────────────────

async def send_sleep_reminder() -> None:
    logger.info("Sending sleep reminder.")
    await send_both(photo=random.choice(IMAGES['sleep']), text=random.choice(TEXTS['sleep_reminder']))


def schedule_tonight_sleep() -> None:
    """
    Pick a random time in the [23:30, 01:30] window for tonight's sleep reminder
    and register a one-shot job. Replaces any existing 'sleep_tonight' job.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)

    # Remove previous one-shot job if it exists (e.g. on restart after midnight)
    for job in scheduler.get_jobs():
        if job.id == 'sleep_tonight':
            job.remove()

    # Build the random fire time
    # Window: 23:30 today → 01:30 tomorrow (120 minutes total = 7200 seconds)
    window_start = now.replace(hour=SLEEP_WINDOW_START[0], minute=SLEEP_WINDOW_START[1],
                                second=0, microsecond=0)
    # If 23:30 has already passed today, shift to next calendar day
    if now >= window_start:
        window_start += timedelta(days=1)

    # 01:30 the day after window_start's calendar day (window_start is always 23:xx)
    window_end = (window_start + timedelta(days=1)).replace(
        hour=SLEEP_WINDOW_END[0], minute=SLEEP_WINDOW_END[1]
    )

    total_seconds = int((window_end - window_start).total_seconds())
    fire_time = window_start + timedelta(seconds=random.randint(0, total_seconds))

    scheduler.add_job(
        send_sleep_reminder,
        DateTrigger(run_date=fire_time, timezone=tz),
        id='sleep_tonight',
    )
    logger.info(f"Tonight's sleep reminder scheduled for {fire_time.strftime('%H:%M')}.")


# ── Weekly stats ──────────────────────────────────────────────────────────────

async def send_weekly_stats() -> None:
    logger.info("Sending weekly stats.")
    now   = datetime.now()
    stats = storage.get_stats(now.year, now.month)
    text = (
        f"📊 Итоги недели!\n\n"
        f"✅ {stats['taken']}\n"
        f"❌ {stats['missed']}\n"
        f"📈 {stats['percentage']:.1f}%\n"
        f"🔥 {stats['streak']}\n\n"
        f"Ты молодец! 💖"
    )
    await send_both(text=text)


# ── Schedule loaders ──────────────────────────────────────────────────────────

def reload_pill_schedule() -> None:
    """
    Remove all pill jobs and re-register them from storage.
    Planned times use cron triggers; persistent reminders use an interval
    trigger anchored to the last planned time so they fire at e.g. 15:50, 17:50...
    """
    for job in scheduler.get_jobs():
        if 'pill_scheduled' in job.id or job.id == 'pill_persistent':
            job.remove()

    pill_schedule = storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)
    for time_str in pill_schedule:
        h, m = map(int, time_str.split(':'))
        scheduler.add_job(
            send_pill_reminder, 'cron',
            hour=h, minute=m,
            id=f'pill_scheduled_{time_str}',
        )

    interval_min = storage.data.get('pill_interval', DEFAULT_PILL_INTERVAL)
    last_h, last_m = map(int, pill_schedule[-1].split(':'))

    tz = pytz.timezone(TIMEZONE)
    today = date.today()
    anchor = tz.localize(datetime(today.year, today.month, today.day, last_h, last_m))

    scheduler.add_job(
        send_persistent,
        IntervalTrigger(minutes=interval_min, start_date=anchor, timezone=tz),
        id='pill_persistent',
    )
    logger.info(
        f"Pill schedule updated: {pill_schedule}, "
        f"persistent every {interval_min} min anchored to {pill_schedule[-1]}."
    )
