from aiogram import Router, F
from aiogram.types import CallbackQuery, PreCheckoutQuery, Message, LabeledPrice
from aiogram.enums import ContentType
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import User, Transaction
import os

router = Router()

PROVIDER_TOKEN = os.getenv("PAYMENT_PROVIDER_TOKEN", "") # Telegram Stars doesn't need provider token, use ""

@router.callback_query(F.data == "pay_stars")
async def cb_pay_stars(callback: CallbackQuery):
    # Telegram Stars amount: minimum is 1 Star = 2 RUB (approx)
    prices = [LabeledPrice(label="Пополнение баланса (100 RUB)", amount=50)] # 50 Stars
    await callback.bot.send_invoice(
        chat_id=callback.from_user.id,
        title="Пополнение VPN",
        description="Пополнение баланса на 100 RUB",
        payload="topup_100",
        provider_token=PROVIDER_TOKEN,
        currency="XTR", # XTR is for Telegram Stars
        prices=prices
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout(pre_checkout_q: PreCheckoutQuery):
    await pre_checkout_q.bot.answer_pre_checkout_query(pre_checkout_q.id, ok=True)

@router.message(F.content_type == ContentType.SUCCESSFUL_PAYMENT)
async def successful_payment(message: Message):
    amount_stars = message.successful_payment.total_amount
    # Convert stars to RUB (e.g. 1 Star = 2 RUB)
    amount_rub = amount_stars * 2.0

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
        if user:
            user.balance += amount_rub
            if user.balance >= -50:
                user.is_active = True

            tx = Transaction(user_id=user.id, amount=amount_rub, type="deposit", description="Telegram Stars Topup")
            session.add(tx)

            # Referral logic
            if user.invited_by:
                inviter = await session.scalar(select(User).where(User.id == user.invited_by))
                if inviter:
                    bonus = amount_rub * 0.10
                    inviter.balance += bonus
                    if inviter.balance >= -50:
                        inviter.is_active = True
                    bonus_tx = Transaction(user_id=inviter.id, amount=bonus, type="referral", description=f"Bonus for inviting {user.tg_id}")
                    session.add(bonus_tx)

            await session.commit()

    await message.answer(f"✅ Успешно! Баланс пополнен на {amount_rub} RUB.")
