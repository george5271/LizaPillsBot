import logging
from aiogram.filters import BaseFilter
from aiogram.types import Message
from config import ADMIN_CHAT_ID, LIZA_CHAT_ID

class AdminFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == ADMIN_CHAT_ID

class LizaFilter(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == LIZA_CHAT_ID
