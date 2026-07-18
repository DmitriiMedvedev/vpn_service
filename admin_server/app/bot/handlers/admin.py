from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, update
import os

from app.db.database import async_session_maker
from app.db.models import User

router = Router()
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "123456789").split(",")]

def is_admin(tg_id: int) -> bool:
    return tg_id in ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer("🛠 Панель администратора\n\nКоманды:\n/stats - Статистика\n/addbalance <user_id> <amount> - Начислить баланс\n/block <user_id> - Забанить\n/unblock <user_id> - Разбанить\n/broadcast <text> - Рассылка")

@router.message(Command("stats"))
async def admin_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        active = sum(1 for u in users if u.is_active)
        total_balance = sum(u.balance for u in users)

        text = f"📊 <b>Статистика</b>\n\nВсего пользователей: {len(users)}\nАктивных: {active}\nСумма балансов: {total_balance:.2f} RUB"
        await message.answer(text, parse_mode="HTML")

@router.message(Command("addbalance"))
async def admin_add_balance(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 3:
        await message.answer("Формат: /addbalance <tg_id> <amount>")
        return

    try:
        tg_id = int(args[1])
        amount = float(args[2])
    except ValueError:
        await message.answer("Неверные данные")
        return

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            await message.answer("Пользователь не найден")
            return

        user.balance += amount
        if user.balance >= -50:
            user.is_active = True
        await session.commit()
        await message.answer(f"Баланс пользователя {tg_id} изменен. Текущий: {user.balance:.2f}")

@router.message(Command("block"))
async def admin_block(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 2:
        return

    tg_id = int(args[1])
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.is_blocked_by_admin = True
            await session.commit()
            await message.answer("Заблокирован")

@router.message(Command("unblock"))
async def admin_unblock(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 2:
        return

    tg_id = int(args[1])
    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.is_blocked_by_admin = False
            await session.commit()
            await message.answer("Разблокирован")
