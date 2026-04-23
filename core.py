import logging
from aiogram import Bot, Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, TIMEZONE
from storage import DataStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

from aiogram.client.default import DefaultBotProperties
from aiohttp import ClientTimeout

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(),
    session=__import__('aiogram').client.session.aiohttp.AiohttpSession(
        timeout=ClientTimeout(total=60)
    ),
)
dp = Dispatcher()
storage = DataStorage()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)
