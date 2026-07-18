from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import User
from app.bot.bot_main import bot

scheduler = AsyncIOScheduler()

async def check_overdrafts():
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.balance < 0).where(User.is_active == True))
        users = result.scalars().all()

        for user in users:
            if user.balance < -50:
                user.is_active = False
                try:
                    await bot.send_message(user.tg_id, "⚠️ Ваш баланс опустился ниже -50 RUB. Доступ к VPN заблокирован. Пополните баланс для разблокировки.")
                except:
                    pass
            elif user.balance < 0:
                # Warning
                try:
                    await bot.send_message(user.tg_id, f"Внимание! Ваш баланс отрицательный ({user.balance:.2f} RUB). Доступ будет отключен при достижении -50 RUB.")
                except:
                    pass
        await session.commit()

def start_scheduler():
    scheduler.add_job(check_overdrafts, 'interval', minutes=60) # check every hour
    scheduler.start()
