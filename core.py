import logging
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import BOT_TOKEN, TIMEZONE
from storage import DataStorage

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)

bot = Bot(
    token=BOT_TOKEN,
    session=AiohttpSession(timeout=60),
)
dp = Dispatcher()
storage = DataStorage()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)
