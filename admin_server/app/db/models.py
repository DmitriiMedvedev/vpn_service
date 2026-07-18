from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    tg_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    uuid = Column(String, unique=True, index=True, default=lambda: str(uuid.uuid4()))
    balance = Column(Float, default=0.0)
    split_tunneling = Column(Boolean, default=True) # True = direct RU, False = all via VPN
    is_active = Column(Boolean, default=True) # Access to VPN
    is_blocked_by_admin = Column(Boolean, default=False)
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="user")

class Node(Base):
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, default=443)
    status = Column(String, default="active") # active, inactive

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False) # deposit, deduction, referral, promo
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")

class PromoCode(Base):
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    activations_left = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
