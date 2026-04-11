"""
bot.py — LizaPillsBot entry point.

Responsibilities:
  - Instantiate the bot and scheduler
  - Define reminder functions (what to send and when)
  - Register all command and button handlers
  - Start the scheduler and polling loop

All secrets live in .env (loaded by config.py).
All content lives in content.py.
All persistence lives in storage.py.
"""

import logging
import random
from datetime import datetime

import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

from config import (
    ADMIN_CHAT_ID,
    LIZA_CHAT_ID,
    BOT_TOKEN,
    DEFAULT_PILL_INTERVAL,
    DEFAULT_PILL_SCHEDULE,
    DEFAULT_SLEEP_SCHEDULE,
    TIMEZONE,
)
from content import IMAGES, TEXTS
from storage import DataStorage

# =============================================================================
# LOGGING
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# =============================================================================
# CORE INSTANCES
# =============================================================================
bot       = telebot.TeleBot(BOT_TOKEN)
storage   = DataStorage()
scheduler = BackgroundScheduler(timezone=TIMEZONE)

# =============================================================================
# CUSTOM FILTERS
# =============================================================================
class AdminFilter(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_admin'
    @staticmethod
    def check(msg):
        return msg.from_user.id == ADMIN_CHAT_ID

class LizaFilter(telebot.custom_filters.SimpleCustomFilter):
    key = 'is_liza'
    @staticmethod
    def check(msg):
        return msg.from_user.id == LIZA_CHAT_ID

bot.add_custom_filter(AdminFilter())
bot.add_custom_filter(LizaFilter())

# =============================================================================
# HELPERS
# =============================================================================
def get_keyboard() -> types.ReplyKeyboardMarkup:
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    kb.add(
        types.KeyboardButton("✅ Выпила"),
        types.KeyboardButton("❌ Не выпила / Пропустила"),
    )
    kb.add(types.KeyboardButton("📅 График за месяц"))
    return kb


def send_both(text: str = None, photo: str = None, caption: str = None) -> None:
    """
    Send a message/photo to Liza, then mirror a copy to the admin.
    """
    # ── Send to Liza ─────────────────────────────────────────────────────────
    try:
        reply_kb = get_keyboard()
        if photo:
            bot.send_photo(LIZA_CHAT_ID, photo, caption=caption or text, reply_markup=reply_kb)
        else:
            bot.send_message(LIZA_CHAT_ID, text, reply_markup=reply_kb)
    except Exception as e:
        logger.error(f"Failed to message Liza: {e}")
        try:
            bot.send_message(ADMIN_CHAT_ID, f"⚠️ Не смог отправить Лизе сообщение:\n{e}")
        except Exception:
            logger.critical("Also failed to notify admin of the error.")

    # ── Mirror to admin ───────────────────────────────────────────────────────
    try:
        admin_copy = f"📨 [Лизе] {caption or text}"
        if photo:
            bot.send_photo(ADMIN_CHAT_ID, photo, caption=admin_copy)
        else:
            bot.send_message(ADMIN_CHAT_ID, admin_copy)
    except Exception as e:
        logger.warning(f"Failed to send admin copy: {e}")


def parse_schedule(text: str, command: str) -> list[str]:
    """Helper to parse and validate schedule times from a command string."""
    times = text.replace(command, '').strip().split()
    if not times:
        return []
    for t in times:
        datetime.strptime(t, '%H:%M')  # Will raise ValueError if invalid
    return times


# =============================================================================
# REMINDER FUNCTIONS
# =============================================================================
def send_pill_reminder() -> None:
    if storage.data.get('pill_status_today') in ('taken', 'missed'):
        return
    logger.info("Sending scheduled pill reminder.")
    send_both(text=random.choice(TEXTS['pill_reminder']))


def send_persistent() -> None:
    if storage.data.get('pill_status_today') in ('taken', 'missed'):
        return
    now = datetime.now()
    last_scheduled = storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)[-1]
    last_time = datetime.strptime(last_scheduled, '%H:%M').time()
    if now.time() > last_time:
        logger.info("Sending persistent pill reminder.")
        send_both(text=random.choice(TEXTS['persistent']))


def send_motivation() -> None:
    logger.info("Sending motivation.")
    text_pool = TEXTS['motivation'] if random.random() < 0.7 else TEXTS['quotes']
    send_both(photo=random.choice(IMAGES['motivation']), caption=random.choice(text_pool))


def send_sleep_question() -> None:
    logger.info("Sending sleep question.")
    send_both(text=random.choice(TEXTS['sleep_question']))


def send_sleep_reminder() -> None:
    logger.info("Sending sleep reminder.")
    send_both(photo=random.choice(IMAGES['sleep']), caption=random.choice(TEXTS['sleep_reminder']))


def send_weekly_stats() -> None:
    logger.info("Sending weekly stats.")
    now   = datetime.now()
    stats = storage.get_stats(now.year, now.month)
    send_both(text=(
        f"📊 Итоги недели!\n\n"
        f"✅ {stats['taken']}\n"
        f"❌ {stats['missed']}\n"
        f"📈 {stats['percentage']:.1f}%\n"
        f"🔥 {stats['streak']}\n\n"
        f"Ты молодец! 💖"
    ))


# =============================================================================
# SCHEDULER MANAGEMENT
# =============================================================================
def reload_pill_schedule() -> None:
    for job in scheduler.get_jobs():
        if 'pill' in job.id:
            job.remove()

    pill_schedule = storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE)
    for time_str in pill_schedule:
        h, m = map(int, time_str.split(':'))
        scheduler.add_job(
            send_pill_reminder, 'cron',
            hour=h, minute=m,
            id=f'pill_scheduled_{time_str}',
        )

    interval = storage.data.get('pill_interval', DEFAULT_PILL_INTERVAL)
    scheduler.add_job(
        send_persistent, 'cron',
        minute=f'*/{interval}',
        id='pill_persistent',
    )
    logger.info(f"Pill schedule updated: {pill_schedule}, interval every {interval} min.")


def reload_sleep_schedule() -> None:
    for job in scheduler.get_jobs():
        if 'sleep' in job.id:
            job.remove()

    sleep_schedule = storage.data.get('sleep_schedule', DEFAULT_SLEEP_SCHEDULE)
    for i, time_str in enumerate(sleep_schedule):
        h, m = map(int, time_str.split(':'))
        if i == 0:
            scheduler.add_job(
                send_sleep_question, 'cron', hour=h, minute=m, id=f'sleep_question_{time_str}'
            )
        else:
            scheduler.add_job(
                send_sleep_reminder, 'cron', hour=h, minute=m, id=f'sleep_reminder_{time_str}'
            )
    logger.info(f"Sleep schedule updated: {sleep_schedule}.")


# =============================================================================
# ADMIN COMMANDS (Protected by is_admin=True)
# =============================================================================
@bot.message_handler(commands=['start'], is_admin=True)
def cmd_start_admin(msg):
    bot.send_message(
        msg.chat.id,
         "Привет, Admin! 👨‍💻\n\nТы подключен как админ.\n\n"
         "Доступные команды:\n"
         "/status — статус и настройки\n"
         "/set_pill_schedule 13:00 13:30\n"
         "/set_pill_interval 15\n"
         "/set_sleep_schedule 22:00 23:00\n"
         "/reset_pill — сброс таблетки\n"
         "/reset_sleep — сброс сна\n"
         "/send_motivation текст\n"
         "/send_text текст",
    )


@bot.message_handler(commands=['status'], is_admin=True)
def cmd_status(msg):
    now       = datetime.now()
    pill_sch  = ', '.join(storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE))
    pill_int  = storage.data.get('pill_interval', DEFAULT_PILL_INTERVAL)
    sleep_sch = ', '.join(storage.data.get('sleep_schedule', DEFAULT_SLEEP_SCHEDULE))
    bot.send_message(msg.chat.id, (
        f"📊 Статус бота 527\n\n"
        f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📋 Статус: {storage.data.get('pill_status_today', '-')}\n"
        f"🔥 Стрик: {storage.data.get('streak', 0)}\n\n"
        f"💊 Таблетка:\n└ Плановые: {pill_sch}\n└ Навязчивые: каждые {pill_int} мин\n\n"
        f"🌙 Сон:\n└ {sleep_sch}"
    ))


@bot.message_handler(commands=['set_pill_schedule'], is_admin=True)
def cmd_set_pill_schedule(msg):
    try:
        times = parse_schedule(msg.text, '/set_pill_schedule')
        if not times:
            bot.send_message(msg.chat.id, "Укажи времена: /set_pill_schedule 12:00 12:10 12:20")
            return
        
        storage.data['pill_schedule'] = times
        storage.save()
        reload_pill_schedule()
        bot.send_message(msg.chat.id, f"✅ Расписание таблетки обновлено:\n{', '.join(times)}")
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Неверный формат! Используй: /set_pill_schedule 12:00 12:10 12:20")


@bot.message_handler(commands=['set_pill_interval'], is_admin=True)
def cmd_set_pill_interval(msg):
    try:
        interval = int(msg.text.split()[1])
        if not (1 <= interval <= 60):
            bot.send_message(msg.chat.id, "❌ Интервал должен быть от 1 до 60 минут")
            return
        storage.data['pill_interval'] = interval
        storage.save()
        reload_pill_schedule()
        bot.send_message(msg.chat.id, f"✅ Интервал навязчивых напоминаний: каждые {interval} мин")
    except (ValueError, IndexError):
        bot.send_message(msg.chat.id, "❌ Укажи число: /set_pill_interval 5")


@bot.message_handler(commands=['set_sleep_schedule'], is_admin=True)
def cmd_set_sleep_schedule(msg):
    try:
        times = parse_schedule(msg.text, '/set_sleep_schedule')
        if not times:
            bot.send_message(msg.chat.id, "Укажи времена: /set_sleep_schedule 22:00 23:00 00:00")
            return
        
        storage.data['sleep_schedule'] = times
        storage.save()
        reload_sleep_schedule()
        bot.send_message(
            msg.chat.id,
            f"✅ Расписание сна обновлено:\n{', '.join(times)}\n"
            f"(Первое время — вопрос, остальные — напоминания)",
        )
    except ValueError:
        bot.send_message(msg.chat.id, "❌ Неверный формат! Используй: /set_sleep_schedule 22:00 23:00 00:00")


@bot.message_handler(commands=['reset_pill'], is_admin=True)
def cmd_reset_pill(msg):
    storage.data['pill_schedule'] = DEFAULT_PILL_SCHEDULE.copy()
    storage.data['pill_interval'] = DEFAULT_PILL_INTERVAL
    storage.save()
    reload_pill_schedule()
    bot.send_message(
        msg.chat.id,
        f"✅ Настройки таблетки сброшены к дефолту:\n"
        f"{', '.join(DEFAULT_PILL_SCHEDULE)}\nИнтервал: {DEFAULT_PILL_INTERVAL} мин",
    )


@bot.message_handler(commands=['reset_sleep'], is_admin=True)
def cmd_reset_sleep(msg):
    storage.data['sleep_schedule'] = DEFAULT_SLEEP_SCHEDULE.copy()
    storage.save()
    reload_sleep_schedule()
    bot.send_message(
        msg.chat.id,
        f"✅ Настройки сна сброшены к дефолту:\n{', '.join(DEFAULT_SLEEP_SCHEDULE)}",
    )


@bot.message_handler(commands=['send_motivation'], is_admin=True)
def cmd_send_motivation(msg):
    text = msg.text.replace('/send_motivation', '', 1).strip()
    if not text:
        bot.send_message(msg.chat.id, "Пример: /send_motivation Привет!")
        return
    try:
        bot.send_photo(LIZA_CHAT_ID, random.choice(IMAGES['motivation']), caption=text)
        bot.send_message(msg.chat.id, "✅ Отправлено")
    except Exception as e:
        bot.send_message(msg.chat.id, f"❌ {e}")


@bot.message_handler(commands=['send_text'], is_admin=True)
def cmd_send_text(msg):
    text = msg.text.replace('/send_text', '', 1).strip()
    if not text:
        bot.send_message(msg.chat.id, "Пример: /send_text Люблю!")
        return
    send_both(text=text)
    bot.send_message(msg.chat.id, "✅")


# =============================================================================
# LIZA COMMANDS & BUTTONS (Protected by is_liza=True)
# =============================================================================
@bot.message_handler(commands=['start'], is_liza=True)
def cmd_start_liza(msg):
    bot.send_message(
        msg.chat.id,
        f"Привет, Лизочка! 💕\n\nЯ - 527, твой личный ассистент!\n\n"
        f"⏰ Таблетка: {', '.join(storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE))}\n"
        f"🌙 Сон: {', '.join(storage.data.get('sleep_schedule', DEFAULT_SLEEP_SCHEDULE))}",
        reply_markup=get_keyboard(),
    )


@bot.message_handler(func=lambda m: m.text == "✅ Выпила", is_liza=True)
def btn_taken(msg):
    if storage.is_locked():
        bot.send_message(msg.chat.id, "Уже отмечено сегодня!", reply_markup=get_keyboard())
        return
    if not storage.mark_day('taken'):
        return
    send_both(photo=random.choice(IMAGES['taken']), caption=random.choice(TEXTS['taken']))
    if storage.data.get('streak', 0) > 1:
        send_both(text=f"🔥 Стрик: {storage.data['streak']} дней!")


@bot.message_handler(func=lambda m: m.text == "❌ Не выпила / Пропустила", is_liza=True)
def btn_missed(msg):
    if storage.is_locked():
        bot.send_message(msg.chat.id, "Уже отмечено сегодня!", reply_markup=get_keyboard())
        return
    if not storage.mark_day('missed'):
        return
    send_both(photo=random.choice(IMAGES['missed']), caption=random.choice(TEXTS['missed']))


@bot.message_handler(func=lambda m: m.text == "📅 График за месяц", is_liza=True)
def btn_calendar(msg):
    now   = datetime.now()
    cal   = storage.get_calendar(now.year, now.month)
    stats = storage.get_stats(now.year, now.month)

    text = f"📅 {now.strftime('%B %Y')}\n\n"
    week = []

    first_day = datetime(now.year, now.month, 1).weekday()
    week.extend(["   "] * first_day)

    for day in range(1, len(cal) + 1):
        emoji = {"taken": "✅", "missed": "❌"}.get(
            cal[day],
            "❔" if day == now.day else ("➖" if day < now.day else "▫️"),
        )
        week.append(f"{day:2d}{emoji}")
        if (day + first_day) % 7 == 0 or day == len(cal):
            text += " ".join(week) + "\n"
            week = []

    text += f"\n📊\n✅ {stats['taken']}\n❌ {stats['missed']}\n"
    if stats['total'] > 0:
        text += f"📈 {stats['percentage']:.1f}%\n"
    text += f"🔥 {stats['streak']}"

    bot.send_message(msg.chat.id, text, reply_markup=get_keyboard())


# =============================================================================
# STRANGER HANDLER (Catch-all)
# =============================================================================
@bot.message_handler(func=lambda m: True)
def stranger_handler(msg):
    """If they aren't Liza and aren't Admin, ignore them or send a basic message."""
    bot.send_message(msg.chat.id, "Бот для Лизы.")


# =============================================================================
# MAIN
# =============================================================================
def main():
    logger.info("🤖 Бот 527 запускается...")
    logger.info(f"Лиза chat_id: {LIZA_CHAT_ID} (из .env)")
    logger.info(f"Админ chat_id: {ADMIN_CHAT_ID} (из .env)")

    # Midnight reset — clears pill_status_today so the new day starts clean
    scheduler.add_job(storage.reset_daily, 'cron', hour=0, minute=0, second=5, id='reset_daily')

    # Load pill and sleep schedules from persisted data
    reload_pill_schedule()
    reload_sleep_schedule()

    # Motivation — twice a day
    scheduler.add_job(send_motivation, 'cron', hour=10, minute=30, id='motivation_morning')
    scheduler.add_job(send_motivation, 'cron', hour=15, minute=30, id='motivation_afternoon')
    logger.info("Motivation: 10:30 and 15:30.")

    # Weekly recap every Sunday evening
    scheduler.add_job(send_weekly_stats, 'cron', day_of_week='sun', hour=20, minute=0, id='weekly_stats')
    logger.info("Weekly stats: Sunday 20:00.")

    scheduler.start()
    logger.info("🚀 Scheduler started. Polling...")

    try:
        bot.polling(none_stop=True, timeout=20)
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Shutting down...")
        scheduler.shutdown()
        logger.info("✅ Scheduler stopped cleanly.")


if __name__ == "__main__":
    main()