import asyncio
import logging

from core import bot, dp, scheduler, storage
from handlers import router
from alarms import reload_pill_schedule, schedule_tonight_sleep, send_motivation, send_weekly_stats

logger = logging.getLogger(__name__)


async def start_bot():
    logger.info("🤖 Бот 527 запускается на aiogram...")

    dp.include_router(router)

    scheduler.add_job(storage.reset_daily, 'cron', hour=0, minute=0, second=5, id='reset_daily')
    scheduler.add_job(schedule_tonight_sleep, 'cron', hour=2, minute=0, id='reschedule_sleep')

    reload_pill_schedule()
    schedule_tonight_sleep()

    scheduler.add_job(send_motivation, 'cron', hour=10, minute=30, id='motivation_morning')
    scheduler.add_job(send_motivation, 'cron', hour=15, minute=30, id='motivation_afternoon')
    scheduler.add_job(send_weekly_stats, 'cron', day_of_week='sun', hour=20, minute=0, id='weekly_stats')

    for attempt in range(3):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            break
        except Exception as e:
            logger.warning(f"delete_webhook attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(5)

    scheduler.start()
    logger.info("🚀 AsyncIOScheduler started. Polling...")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Бот остановлен.")
