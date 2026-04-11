import random
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core import bot, storage
from filters import AdminFilter, LizaFilter
from alarms import get_keyboard, send_both
from content import IMAGES, TEXTS
from config import DEFAULT_PILL_SCHEDULE, DEFAULT_PILL_INTERVAL, DEFAULT_SLEEP_SCHEDULE

router = Router()

class AdminStates(StatesGroup):
    waiting_for_message = State()

def generate_calendar_text() -> str:
    now   = datetime.now()
    cal   = storage.get_calendar(now.year, now.month)
    stats = storage.get_stats(now.year, now.month)

    text = f"📅 {now.strftime('%B %Y')}\n\n"
    week = []

    first_day = datetime(now.year, now.month, 1).weekday()
    week.extend(["   "] * first_day)

    for day in range(1, len(cal) + 1):
        emoji = {"taken": "✅", "missed": "❌"}.get(cal[day], "❔" if day == now.day else ("➖" if day < now.day else "▫️"))
        week.append(f"{day:2d}{emoji}")
        if (day + first_day) % 7 == 0 or day == len(cal):
            text += " ".join(week) + "\n"
            week = []

    text += f"\n📊\n✅ {stats['taken']}\n❌ {stats['missed']}\n"
    if stats['total'] > 0:
        text += f"📈 {stats['percentage']:.1f}%\n"
    text += f"🔥 {stats['streak']}"
    return text

# --- ADMIN COMMANDS ---
@router.message(Command("start"), AdminFilter())
async def cmd_start_admin(message: Message):
    await message.answer(
        "Привет, Admin! 👨‍💻\n\nТы подключен как админ.\n\n"
        "Доступные команды:\n"
        "/status — статус и настройки\n"
        "/calendar — показать график и статистику Лизы\n"
        "/send_text — отправить произвольное сообщение или картинку Лизе с помощью диалога\n"
        "/send_message_image текст — мгновенно отправить текст со случайной картинкой из папки Day\n"
    )

@router.message(Command("status"), AdminFilter())
async def cmd_status(message: Message):
    now       = datetime.now()
    pill_sch  = ', '.join(storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE))
    pill_int  = storage.data.get('pill_interval', DEFAULT_PILL_INTERVAL)
    sleep_sch = ', '.join(storage.data.get('sleep_schedule', DEFAULT_SLEEP_SCHEDULE))
    await message.answer(
        f"📊 Статус бота 527\n\n"
        f"🕐 {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"📋 Статус: {storage.data.get('pill_status_today', '-')}\n"
        f"🔥 Стрик: {storage.data.get('streak', 0)}\n\n"
        f"💊 Таблетка:\n└ Плановые: {pill_sch}\n└ Навязчивые: каждые {pill_int} мин\n\n"
        f"🌙 Сон:\n└ {sleep_sch}"
    )

@router.message(Command("calendar"), AdminFilter())
async def cmd_calendar_admin(message: Message):
    await message.answer(generate_calendar_text())

@router.message(Command("send_message_image"), AdminFilter())
async def cmd_send_message_image(message: Message):
    text = message.text.replace('/send_message_image', '', 1).strip()
    if not text:
        await message.answer("Пример: /send_message_image Спокойной ночи!")
        return
    try:
        await send_both(photo=random.choice(IMAGES['day']), caption=text)
        await message.answer("✅ Отправлено со случайной картинкой [day]!")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

@router.message(Command("send_text"), AdminFilter())
async def cmd_send_text(message: Message, state: FSMContext):
    await message.answer(
        "Okay, send me the picture and the text and I will resend this to Liza.\n"
        "(You can send just text, or a photo with a caption. Send /cancel to abort.)"
    )
    await state.set_state(AdminStates.waiting_for_message)

@router.message(Command("cancel"), AdminFilter(), AdminStates.waiting_for_message)
async def cmd_cancel_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено.")

@router.message(AdminFilter(), AdminStates.waiting_for_message)
async def process_admin_message(message: Message, state: FSMContext):
    if message.text and message.text.strip().lower() == '/cancel':
        await state.clear()
        await message.answer("Отменено.")
        return

    try:
        if message.photo:
            photo_id = message.photo[-1].file_id
            caption = message.caption
            await send_both(text=caption, photo=photo_id)
        elif message.text:
            await send_both(text=message.text)
        else:
            await message.answer("❌ Поддерживается только текст или фото с подписью.")
            return

        await message.answer("✅ Отправлено Лизе!")
        await state.clear()
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
        await state.clear()

# --- LIZA COMMANDS ---
@router.message(Command("start"), LizaFilter())
async def cmd_start_liza(message: Message):
    await message.answer(
        f"Привет, Лизочка! 💕\n\nЯ - 527, твой личный ассистент!\n\n"
        f"⏰ Таблетка: {', '.join(storage.data.get('pill_schedule', DEFAULT_PILL_SCHEDULE))}\n"
        f"🌙 Сон: {', '.join(storage.data.get('sleep_schedule', DEFAULT_SLEEP_SCHEDULE))}",
        reply_markup=get_keyboard(),
    )

@router.message(F.text == "✅ Выпила", LizaFilter())
async def btn_taken(message: Message):
    if storage.is_locked():
        await message.answer("Уже отмечено сегодня!", reply_markup=get_keyboard())
        return
    if not storage.mark_day('taken'):
        return
    await send_both(photo=random.choice(IMAGES['day']), caption=random.choice(TEXTS['taken']))
    if storage.data.get('streak', 0) > 1:
        await send_both(text=f"🔥 Стрик: {storage.data['streak']} дней!")

@router.message(F.text == "❌ Не выпила / Пропустила", LizaFilter())
async def btn_missed(message: Message):
    if storage.is_locked():
        await message.answer("Уже отмечено сегодня!", reply_markup=get_keyboard())
        return
    if not storage.mark_day('missed'):
        return
    await send_both(photo=random.choice(IMAGES['day']), caption=random.choice(TEXTS['missed']))

@router.message(F.text == "📅 График за месяц", LizaFilter())
async def btn_calendar(message: Message):
    await message.answer(generate_calendar_text(), reply_markup=get_keyboard())

# --- STRANGER ---
@router.message()
async def stranger_handler(message: Message):
    await message.answer("Бот для Лизы.")
