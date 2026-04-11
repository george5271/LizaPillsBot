import random
import logging
from datetime import datetime
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from core import bot, storage, scheduler
from content import IMAGES, TEXTS
from config import ADMIN_CHAT_ID, LIZA_CHAT_ID, DEFAULT_PILL_SCHEDULE, DEFAULT_PILL_INTERVAL, DEFAULT_SLEEP_SCHEDULE

logger = logging.getLogger(__name__)

def get_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Выпила"), KeyboardButton(text="❌ Не выпила / Пропустила")],
            [KeyboardButton(text="📅 График за месяц")]
        ],
        resize_keyboard=True
    )

async def send_both(text: str = None, photo: str = None, caption: str = None) -> None:
    reply_kb = get_keyboard()
    try:
        if photo:
            await bot.send_photo(LIZA_CHAT_ID, photo, caption=caption or text, reply_markup=reply_kb)
        else:
            await bot.send_message(LIZA_CHAT_ID, text, reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Failed to message Liza: {e}")
        try:
            await bot.send_message(ADMIN_CHAT_ID, f"⚠️ Не смог отправить Лизе сообщение:\n{e}")
        except Exception:
            pass

    try:
        admin_copy = f"📨 [Лизе] {caption or text}"
        if photo:
            await bot.send_photo(ADMIN_CHAT_ID, photo, caption=admin_copy)
        else:
            await bot.send_message(ADMIN_CHAT_ID, admin_copy)
    except Exception as e:
        logger.warning(f"Failed to send admin copy: {e}")

async def send_pill_reminder() -> None:
    if storage.data.get('pill_status_today') in ('taken', 'missed'):
        return
    logger.info("Sending scheduled pill reminder.")
    await send_both(photo=random.choice(IMAGES['day']), caption=random.choice(TEXTS['pill_reminder']))

async def send_persistent() -> None:
    if storage.data.get('pill_status_today') in ('taken', 'missed'):
        return
    now = datetime.now()
    last_scheduled = storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)[-1]
    last_time = datetime.strptime(last_scheduled, '%H:%M').time()
    if now.time() > last_time:
        logger.info("Sending persistent pill reminder.")
        await send_both(photo=random.choice(IMAGES['day']), caption=random.choice(TEXTS['persistent']))

async def send_motivation() -> None:
    logger.info("Sending motivation.")
    text_pool = TEXTS['motivation'] if random.random() < 0.7 else TEXTS['quotes']
    await send_both(photo=random.choice(IMAGES['day']), caption=random.choice(text_pool))

async def send_sleep_question() -> None:
    logger.info("Sending sleep question.")
    await send_both(photo=random.choice(IMAGES['sleep']), caption=random.choice(TEXTS['sleep_question']))

async def send_sleep_reminder() -> None:
    logger.info("Sending sleep reminder.")
    await send_both(photo=random.choice(IMAGES['sleep']), caption=random.choice(TEXTS['sleep_reminder']))

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

def reload_pill_schedule() -> None:
    for job in scheduler.get_jobs():
        if 'pill' in job.id:
            job.remove()

    pill_schedule = storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)
    for time_str in pill_schedule:
        h, m = map(int, time_str.split(':'))
        scheduler.add_job(send_pill_reminder, 'cron', hour=h, minute=m, id=f'pill_scheduled_{time_str}')

    interval = storage.data.get('pill_interval', DEFAULT_PILL_INTERVAL)
    scheduler.add_job(send_persistent, 'cron', minute=f'*/{interval}', id='pill_persistent')
    logger.info(f"Pill schedule updated: {pill_schedule}, interval every {interval} min.")

def reload_sleep_schedule() -> None:
    for job in scheduler.get_jobs():
        if 'sleep' in job.id:
            job.remove()

    sleep_schedule = storage.data.get('sleep_schedule', DEFAULT_SLEEP_SCHEDULE)
    for i, time_str in enumerate(sleep_schedule):
        h, m = map(int, time_str.split(':'))
        if i == 0:
            scheduler.add_job(send_sleep_question, 'cron', hour=h, minute=m, id=f'sleep_question_{time_str}')
        else:
            scheduler.add_job(send_sleep_reminder, 'cron', hour=h, minute=m, id=f'sleep_reminder_{time_str}')
    logger.info(f"Sleep schedule updated: {sleep_schedule}.")
