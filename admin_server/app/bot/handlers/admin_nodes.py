from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import Node
from app.bot.handlers.admin import is_admin

router = Router()

@router.message(Command("addnode"))
async def admin_add_node(message: Message):
    if not is_admin(message.from_user.id):
        return
    args = message.text.split()
    if len(args) not in [2, 3]:
        await message.answer("Формат: /addnode <ip> [port]")
        return

    ip = args[1]
    port = int(args[2]) if len(args) == 3 else 443

    async with async_session_maker() as session:
        node = await session.scalar(select(Node).where(Node.ip == ip).where(Node.port == port))
        if node:
            await message.answer("Эта нода уже существует в базе!")
            return

        new_node = Node(ip=ip, port=port, status="active")
        session.add(new_node)
        await session.commit()
        await message.answer(f"✅ Нода {ip}:{port} успешно добавлена в систему! Теперь на нее будет выдаваться трафик.")
