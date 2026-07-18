from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from app.db.database import async_session_maker
from app.db.models import User, PromoCode, Transaction

router = Router()

class PromoState(StatesGroup):
    waiting_for_promo = State()

@router.callback_query(F.data == "enter_promo")
async def cb_enter_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Пожалуйста, введите промокод:")
    await state.set_state(PromoState.waiting_for_promo)

@router.message(PromoState.waiting_for_promo)
async def process_promo(message: Message, state: FSMContext):
    code = message.text.strip()
    await state.clear()

    async with async_session_maker() as session:
        user = await session.scalar(select(User).where(User.tg_id == message.from_user.id))
        if not user:
            return

        promo = await session.scalar(select(PromoCode).where(PromoCode.code == code).where(PromoCode.is_active == True))

        if not promo or promo.activations_left <= 0:
            await message.answer("Промокод недействителен или исчерпал лимит.")
            return

        user.balance += promo.amount
        if user.balance >= -50:
            user.is_active = True

        promo.activations_left -= 1
        if promo.activations_left == 0:
            promo.is_active = False

        tx = Transaction(user_id=user.id, amount=promo.amount, type="promo", description=f"Activated promo {code}")
        session.add(tx)

        await session.commit()

    await message.answer(f"✅ Промокод успешно активирован! Ваш баланс пополнен на {promo.amount} RUB.")
