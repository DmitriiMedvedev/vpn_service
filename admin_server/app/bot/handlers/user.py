from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.enums import ContentType
from aiogram.filters import CommandStart, Command
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from aiocryptopay import AioCryptoPay
import os

from app.db.database import async_session_maker
from app.db.models import User
from app.bot.keyboards import main_menu_kb, topup_kb, settings_kb

router = Router()
CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "mock_token")
crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network="mainnet")

async def get_or_create_user(tg_id: int, username: str, session: AsyncSession):
    stmt = select(User).where(User.tg_id == tg_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(tg_id=tg_id, username=username)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user

@router.message(CommandStart())
async def cmd_start(message: Message):
    # Handle referral
    invited_by = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            invited_by = int(args[1].replace("ref_", ""))
        except Exception as e:
            print(f"Error handling ref: {e}")

    async with async_session_maker() as session:
        user = await get_or_create_user(message.from_user.id, message.from_user.username, session)

        if invited_by and not user.invited_by and invited_by != message.from_user.id:
            inviter = await session.scalar(select(User).where(User.tg_id == invited_by))
            if inviter:
                user.invited_by = inviter.id
                await session.commit()

    text = "👋 Добро пожаловать в VPN сервис!\n\nИспользуйте меню ниже для управления своим аккаунтом."
    await message.answer(text, reply_markup=main_menu_kb())

@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню", reply_markup=main_menu_kb())

@router.callback_query(F.data == "profile")
async def cb_profile(callback: CallbackQuery):
    async with async_session_maker() as session:
        user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)

        status = "🟢 Активен" if user.is_active else "🔴 Заблокирован"
        if user.is_blocked_by_admin:
            status = "⛔ Забанен администратором"

        bot_username = (await callback.bot.me()).username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user.tg_id}"

        # Admin API runs on same server, we construct the sub link directly using the known base URL
        # Or expose API domain via env
        api_domain = os.getenv("API_DOMAIN", "http://127.0.0.1:8000")
        sub_link = f"{api_domain}/sub/{user.uuid}"

        text = (
            f"👤 <b>Профиль</b>\n\n"
            f"ID: <code>{user.tg_id}</code>\n"
            f"Баланс: <b>{user.balance:.2f} RUB</b>\n"
            f"Статус: {status}\n\n"
            f"🔗 <b>Ваша подписка (вставьте в клиент Happ/v2rayN):</b>\n"
            f"<code>{sub_link}</code>\n\n"
            f"🎁 <b>Реферальная ссылка (вы получаете 10% от пополнений):</b>\n"
            f"<code>{ref_link}</code>"
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")]]), parse_mode="HTML")

@router.callback_query(F.data == "topup")
async def cb_topup(callback: CallbackQuery):
    await callback.message.edit_text("Выберите способ пополнения:", reply_markup=topup_kb())

@router.callback_query(F.data == "pay_crypto")
async def cb_pay_crypto(callback: CallbackQuery):
    # Create invoice via cryptobot
    try:
        invoice = await crypto.create_invoice(asset="USDT", amount=1.0, payload=str(callback.from_user.id))
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатить 1 USDT", url=invoice.bot_invoice_url)],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="topup")]
        ])
        await callback.message.edit_text("Оплатите счет через CryptoBot:", reply_markup=keyboard)
    except Exception as e:
        await callback.answer(f"Ошибка: {e}", show_alert=True)

@router.callback_query(F.data == "settings")
async def cb_settings(callback: CallbackQuery):
    async with async_session_maker() as session:
        user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)
        await callback.message.edit_text("⚙️ Настройки", reply_markup=settings_kb(user.split_tunneling))

@router.callback_query(F.data == "toggle_split")
async def cb_toggle_split(callback: CallbackQuery):
    async with async_session_maker() as session:
        user = await get_or_create_user(callback.from_user.id, callback.from_user.username, session)
        user.split_tunneling = not user.split_tunneling
        await session.commit()
        await callback.message.edit_text("⚙️ Настройки", reply_markup=settings_kb(user.split_tunneling))
