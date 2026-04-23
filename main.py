import asyncio
import logging
import traceback

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject

from core import bot, dp, scheduler, storage
from handlers import router
from alarms import reload_pill_schedule, schedule_tonight_sleep, send_motivation, send_weekly_stats
from config import ADMIN_CHAT_ID

logger = logging.getLogger(__name__)


class ErrorNotifyMiddleware(BaseMiddleware):
    """
    Outer middleware: catches any unhandled exception in a handler,
    notifies Admin, then re-raises so aiogram can log it normally.
    """
    async def __call__(self, handler, event: TelegramObject, data: dict):
        try:
            return await handler(event, data)
        except Exception as e:
            tb = traceback.format_exc()
            logger.error(f"Unhandled handler exception: {e}\n{tb}")
            try:
                await bot.send_message(
                    ADMIN_CHAT_ID,
                    f"🚨 Необработанная ошибка в хендлере:\n<code>{e}</code>\n\n"
                    f"<pre>{tb[-1500:]}</pre>",
                    parse_mode="HTML",
                )
            except Exception:
                pass
            raise


async def start_bot():
    logger.info("🤖 Бот 527 запускается на aiogram...")

    dp.update.outer_middleware(ErrorNotifyMiddleware())
    dp.include_router(router)

    scheduler.add_job(storage.reset_daily, 'cron', hour=0, minute=0, second=5, id='reset_daily')
    # Re-schedule tonight's sleep reminder daily at 02:00 (after the window closes)
    scheduler.add_job(schedule_tonight_sleep, 'cron', hour=2, minute=0, id='reschedule_sleep')

    reload_pill_schedule()
    schedule_tonight_sleep()

    scheduler.add_job(send_motivation, 'cron', hour=10, minute=30, id='motivation_morning')
    scheduler.add_job(send_motivation, 'cron', hour=15, minute=30, id='motivation_afternoon')
    scheduler.add_job(send_weekly_stats, 'cron', day_of_week='sun', hour=20, minute=0, id='weekly_stats')

    scheduler.start()
    logger.info("🚀 AsyncIOScheduler started. Polling...")

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Бот остановлен.")
