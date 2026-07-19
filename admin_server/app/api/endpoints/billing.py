from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from aiocryptopay import AioCryptoPay
from aiocryptopay.models.update import Update
from app.db.database import get_session
from app.db.models import User, Transaction
import os
import json

router = APIRouter()

CRYPTO_PAY_TOKEN = os.getenv("CRYPTO_PAY_TOKEN", "mock_token")
crypto = AioCryptoPay(token=CRYPTO_PAY_TOKEN, network="mainnet")

async def process_payment(session: AsyncSession, tg_id: int, amount: float):
    user = await session.scalar(select(User).where(User.tg_id == tg_id))
    if not user:
        return

    user.balance += amount
    if user.balance >= -50:
        user.is_active = True

    # Add transaction
    tx = Transaction(user_id=user.id, amount=amount, type="deposit", description="CryptoBot Topup")
    session.add(tx)

    # Referral bonus
    if user.invited_by:
        inviter = await session.scalar(select(User).where(User.id == user.invited_by))
        if inviter:
            bonus = amount * 0.10
            inviter.balance += bonus
            if inviter.balance >= -50:
                inviter.is_active = True
            bonus_tx = Transaction(user_id=inviter.id, amount=bonus, type="referral", description=f"Bonus for inviting {user.tg_id}")
            session.add(bonus_tx)

    await session.commit()

@router.post("/cryptobot/webhook")
async def cryptobot_webhook(request: Request, db: AsyncSession = Depends(get_session)):
    # Get CryptoPay signature
    crypto_pay_sig = request.headers.get("crypto-pay-api-signature")
    if not crypto_pay_sig:
        raise HTTPException(status_code=400, detail="Missing signature")

    body = await request.body()
    # Verify signature
    if not crypto.check_signature(crypto_pay_sig, body.decode()):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        data = await request.json()
        update_obj = Update(**data)

        if update_obj.update_type == 'invoice_paid':
            invoice = update_obj.payload
            user_tg_id = int(invoice.payload)
            # Assuming amount is in USDT, and 1 USDT = 100 RUB for simplicity,
            # or if invoice amount is already in RUB, we use it directly.
            # Assuming CryptoBot amount is the exact amount we want to add.
            amount = float(invoice.amount) * 100 # Example conversion for USDT to RUB

            await process_payment(db, user_tg_id, amount)

    except Exception as e:
        print("Webhook error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

    return {"ok": True}
