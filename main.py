import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession

from config import BOT_TOKEN
from handlers import create_router
from scheduler import BotScheduler, Delivery
from storage import DataStorage

logger = logging.getLogger(__name__)


async def start_bot():
    logger.info("🤖 Бот 527 запускается на aiogram...")

    bot = Bot(token=BOT_TOKEN, session=AiohttpSession(timeout=60))
    dp = Dispatcher()
    storage = DataStorage()
    delivery = Delivery(bot)
    scheduler = BotScheduler(storage, delivery)

    dp.include_router(create_router(bot, storage, delivery))

    for attempt in range(3):
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            break
        except Exception as e:
            logger.warning(f"delete_webhook attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                await asyncio.sleep(5)

    scheduler_task = asyncio.create_task(scheduler.run())
    logger.info("🚀 Polling started.")

    try:
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
        await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    try:
        asyncio.run(start_bot())
    except (KeyboardInterrupt, SystemExit):
        logger.info("⛔ Бот остановлен.")
