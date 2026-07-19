from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from sqlalchemy import select, update
import os
import uuid

from app.db.database import async_session_maker
from app.db.models import User, Transaction, PromoCode


router = Router()
ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "123456789").split(",")]

def is_admin(tg_id: int) -> bool:
    return tg_id in ADMIN_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = (
        "🛠 <b>Панель администратора</b>\n\n"
        "Команды:\n"
        "/stats - Статистика\n"
        "/users - Список всех пользователей\n"
        "/userinfo <tg_id> - Детальная статистика юзера\n"
        "/addbalance <tg_id> <amount> - Начислить баланс\n"
        "/block <tg_id> - Забанить\n"
        "/unblock <tg_id> - Разбанить\n"
        "/broadcast <text> - Массовая рассылка\n"
        "/createpromo <amount> <activations> - Создать промокод"
    )
    await message.answer(text, parse_mode="HTML")

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

@router.message(Command("users"))
async def admin_users(message: Message):
    if not is_admin(message.from_user.id):
        return
    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

        text = "👥 <b>Список пользователей:</b>\n\n"
        for u in users:
            status = "🟢" if u.is_active else ("🔴" if not u.is_blocked_by_admin else "⛔")
            text += f"{status} ID: <code>{u.tg_id}</code> | Баланс: {u.balance:.2f}\n"

        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await message.answer(text[i:i+4000], parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")

@router.message(Command("userinfo"))
async def admin_userinfo(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) != 2:
        await message.answer("Формат: /userinfo <tg_id>")
        return

    try:
        tg_id = int(args[1])
    except ValueError:
        return

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            await message.answer("Пользователь не найден")
            return

        result = await session.execute(select(Transaction).where(Transaction.user_id == user.id).order_by(Transaction.created_at.desc()).limit(5))
        txs = result.scalars().all()

        tx_text = "\n".join([f"- {tx.amount} RUB ({tx.type}): {tx.description}" for tx in txs]) or "Нет транзакций"

        text = (
            f"👤 <b>Детальная статистика:</b>\n\n"
            f"ID: <code>{user.tg_id}</code>\n"
            f"Баланс: {user.balance:.2f} RUB\n"
            f"Статус: {'Активен' if user.is_active else 'Заблокирован'}\n"
            f"Дата регистрации: {user.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Приглашен пользователем: {user.invited_by or 'Нет'}\n\n"
            f"<b>Последние транзакции:</b>\n{tx_text}"
        )
        await message.answer(text, parse_mode="HTML")

@router.message(Command("broadcast"))
async def admin_broadcast(message: Message):
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace("/broadcast ", "", 1).strip()
    if not text or text == "/broadcast":
        await message.answer("Формат: /broadcast <текст рассылки>")
        return

    async with async_session_maker() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    sent = 0
    for user in users:
        try:
            await message.bot.send_message(user.tg_id, f"📢 <b>Рассылка:</b>\n\n{text}", parse_mode="HTML")
            sent += 1
        except Exception:
            pass

    await message.answer(f"Рассылка завершена. Доставлено: {sent}/{len(users)}")

@router.message(Command("createpromo"))
async def admin_create_promo(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) not in [3, 4]:
        await message.answer("Формат: /createpromo <amount> <activations> [code]")
        return

    try:
        amount = float(args[1])
        activations = int(args[2])
        code = args[3] if len(args) == 4 else str(uuid.uuid4())[:8]
    except ValueError:
        await message.answer("Неверные данные")
        return

    async with async_session_maker() as session:
        promo = PromoCode(code=code, amount=amount, activations_left=activations)
        session.add(promo)
        await session.commit()
        await message.answer(f"Промокод создан!\nКод: <code>{code}</code>\nСумма: {amount} RUB\nАктиваций: {activations}", parse_mode="HTML")

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

        tx = Transaction(user_id=user.id, amount=amount, type="admin_add", description="Admin added balance")
        session.add(tx)

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
