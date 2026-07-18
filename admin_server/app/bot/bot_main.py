from aiogram import Bot, Dispatcher
import os
import asyncio
from app.bot.handlers import user

BOT_TOKEN = os.getenv("BOT_TOKEN", "mock_token")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(user.router)
from app.bot.handlers import admin
dp.include_router(admin.router)

async def start_bot():
    if BOT_TOKEN != "mock_token":  # nosec
        await dp.start_polling(bot)

async def stop_bot():
    pass
