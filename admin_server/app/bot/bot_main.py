from aiogram import Bot, Dispatcher
import os
import asyncio
from app.bot.handlers import user
from app.bot.handlers import promo
from app.bot.handlers import payments
from app.bot.handlers import admin
from app.bot.handlers import admin_nodes

BOT_TOKEN = os.getenv("BOT_TOKEN", "mock_token")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

dp.include_router(user.router)
dp.include_router(promo.router)
dp.include_router(payments.router)
dp.include_router(admin.router)
dp.include_router(admin_nodes.router)

async def start_bot():
    if BOT_TOKEN != "mock_token":  # nosec
        await dp.start_polling(bot)

async def stop_bot():
    await bot.session.close()
