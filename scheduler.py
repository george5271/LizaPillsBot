import asyncio
import logging
import random
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from config import (
    ADMIN_CHAT_ID,
    DEFAULT_PILL_INTERVAL,
    DEFAULT_PILL_SCHEDULE,
    LIZA_CHAT_ID,
    SLEEP_WINDOW_END,
    SLEEP_WINDOW_START,
    TIMEZONE,
)
from content import IMAGES, TEXTS
from storage import DataStorage

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2.0
TICK_SECONDS = 30
MOTIVATION_TIMES = {'10:30', '15:30'}
WEEKLY_STATS_TIME = '20:00'


def get_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Выпила"), KeyboardButton(text="❌ Не выпила / Пропустила")],
            [KeyboardButton(text="📅 График за месяц")],
        ],
        resize_keyboard=True,
    )


def choose(items: list[str]) -> str | None:
    return random.choice(items) if items else None


class Delivery:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_both(self, text: str | None = None, photo: str | None = None) -> None:
        reply_kb = get_keyboard()
        last_exc = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                if photo:
                    await self.bot.send_photo(LIZA_CHAT_ID, photo, caption=text, reply_markup=reply_kb)
                elif text:
                    await self.bot.send_message(LIZA_CHAT_ID, text, reply_markup=reply_kb)
                else:
                    return
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
                await self.bot.send_message(
                    ADMIN_CHAT_ID,
                    f"⚠️ Не смог отправить Лизе сообщение после {MAX_RETRIES} попыток:\n{last_exc}",
                )
            except Exception as e:
                logger.error(f"Failed to notify Admin about delivery failure: {e}")

        try:
            admin_copy = f"📨 [Лизе] {text or ''}".strip()
            if photo:
                await self.bot.send_photo(ADMIN_CHAT_ID, photo, caption=admin_copy)
            else:
                await self.bot.send_message(ADMIN_CHAT_ID, admin_copy)
        except Exception as e:
            logger.warning(f"Failed to send admin copy: {e}")

    async def send_day(self, text: str) -> None:
        await self.send_both(text=text, photo=choose(IMAGES['day']))

    async def send_sleep(self, text: str) -> None:
        await self.send_both(text=text, photo=choose(IMAGES['sleep']))


class BotScheduler:
    def __init__(self, storage: DataStorage, delivery: Delivery):
        self.storage = storage
        self.delivery = delivery
        self.tz = ZoneInfo(TIMEZONE)
        self.current_date: str | None = None
        self.pill_sent_times: set[str] = set()
        self.motivation_sent_times: set[str] = set()
        self.last_persistent_sent: datetime | None = None
        self.weekly_stats_sent_week: int | None = None
        self.sleep_fire_time: datetime | None = None

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def _today_at(self, now: datetime, time_str: str) -> datetime:
        hour, minute = map(int, time_str.split(':'))
        return now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    def _sleep_window_end_for_start(self, start: datetime) -> datetime:
        end = start.replace(
            hour=SLEEP_WINDOW_END[0],
            minute=SLEEP_WINDOW_END[1],
            second=0,
            microsecond=0,
        )
        if end <= start:
            end += timedelta(days=1)
        return end

    def _pick_sleep_time(self, now: datetime, skip_current_window: bool = False) -> datetime:
        today_start = now.replace(
            hour=SLEEP_WINDOW_START[0],
            minute=SLEEP_WINDOW_START[1],
            second=0,
            microsecond=0,
        )
        previous_start = today_start - timedelta(days=1)
        previous_end = self._sleep_window_end_for_start(previous_start)

        if previous_start <= now <= previous_end and not skip_current_window:
            start = now
            end = previous_end
        elif now < today_start:
            start = today_start
            end = self._sleep_window_end_for_start(start)
        else:
            start = today_start + timedelta(days=1)
            end = self._sleep_window_end_for_start(start)

        total_seconds = max(0, int((end - start).total_seconds()))
        return start + timedelta(seconds=random.randint(0, total_seconds))

    def _reset_day_if_needed(self, now: datetime) -> None:
        today = now.strftime('%Y-%m-%d')
        if self.current_date == today:
            return

        self.current_date = today
        self.pill_sent_times.clear()
        self.motivation_sent_times.clear()
        self.last_persistent_sent = None
        self.storage.reset_daily()
        logger.info(f"New day state initialized for {today}.")

    async def send_pill_reminder(self) -> None:
        logger.info("Sending scheduled pill reminder.")
        await self.delivery.send_day(choose(TEXTS['pill_reminder']) or "Пора принять таблетку.")

    async def send_persistent_reminder(self) -> None:
        logger.info("Sending persistent pill reminder.")
        await self.delivery.send_day(choose(TEXTS['persistent']) or "Таблетка все еще ждет.")

    async def send_motivation(self) -> None:
        logger.info("Sending motivation.")
        text_pool = TEXTS['motivation'] if random.random() < 0.7 else TEXTS['quotes']
        await self.delivery.send_day(choose(text_pool) or "Ты справишься.")

    async def send_sleep_reminder(self) -> None:
        logger.info("Sending sleep reminder.")
        await self.delivery.send_sleep(choose(TEXTS['sleep_reminder']) or "Пора спать.")

    async def send_weekly_stats(self) -> None:
        logger.info("Sending weekly stats.")
        now = self.now()
        stats = self.storage.get_stats(now.year, now.month)
        text = (
            f"📊 Итоги недели!\n\n"
            f"✅ {stats['taken']}\n"
            f"❌ {stats['missed']}\n"
            f"📈 {stats['percentage']:.1f}%\n"
            f"🔥 {stats['streak']}\n\n"
            f"Ты молодец! 💖"
        )
        await self.delivery.send_both(text=text)

    async def tick(self) -> None:
        now = self.now()
        self._reset_day_if_needed(now)

        if self.sleep_fire_time is None:
            self.sleep_fire_time = self._pick_sleep_time(now)
            logger.info(f"Next sleep reminder scheduled for {self.sleep_fire_time.strftime('%Y-%m-%d %H:%M:%S')}.")

        hhmm = now.strftime('%H:%M')
        pill_done = self.storage.data.get('pill_status_today') in ('taken', 'missed')

        if not pill_done:
            pill_schedule = self.storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)
            if pill_schedule:
                for time_str in pill_schedule:
                    if hhmm == time_str and time_str not in self.pill_sent_times:
                        self.pill_sent_times.add(time_str)
                        await self.send_pill_reminder()

                last_planned = self._today_at(now, pill_schedule[-1])
                interval = timedelta(minutes=self.storage.data.get('pill_interval', DEFAULT_PILL_INTERVAL))
                first_persistent = last_planned + interval
                if now >= first_persistent:
                    if self.last_persistent_sent is None or now - self.last_persistent_sent >= interval:
                        self.last_persistent_sent = now
                        await self.send_persistent_reminder()

        if hhmm in MOTIVATION_TIMES and hhmm not in self.motivation_sent_times:
            self.motivation_sent_times.add(hhmm)
            await self.send_motivation()

        if now.weekday() == 6 and hhmm == WEEKLY_STATS_TIME:
            week = now.isocalendar().week
            if self.weekly_stats_sent_week != week:
                self.weekly_stats_sent_week = week
                await self.send_weekly_stats()

        if now >= self.sleep_fire_time:
            await self.send_sleep_reminder()
            self.sleep_fire_time = self._pick_sleep_time(now, skip_current_window=True)
            logger.info(f"Next sleep reminder scheduled for {self.sleep_fire_time.strftime('%Y-%m-%d %H:%M:%S')}.")

    async def run(self) -> None:
        logger.info("Simple asyncio scheduler started.")
        while True:
            try:
                await self.tick()
            except Exception:
                logger.exception("Scheduler tick failed.")
            await asyncio.sleep(TICK_SECONDS)
