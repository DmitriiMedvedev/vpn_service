"""
SQLAlchemy ORM models defining the PostgreSQL database schema.
Includes Users, Nodes, Transactions, and PromoCodes.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, BigInteger
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.db.database import Base

class User(Base):
    """
    Represents a Telegram user in the system.
    Stores balance, unique UUID for VPN (Xray) authentication, and routing preferences.
    """
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
    """
    Represents a VPN Node server connected to the Master.
    """
    __tablename__ = "nodes"

    id = Column(Integer, primary_key=True, index=True)
    ip = Column(String, nullable=False)
    port = Column(Integer, default=443)
    status = Column(String, default="active") # active, inactive

class Transaction(Base):
    """
    Records balance changes for users (deposits, traffic deductions, promo activations).
    """
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    amount = Column(Float, nullable=False)
    type = Column(String, nullable=False) # deposit, deduction, referral, promo
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="transactions")

class PromoCode(Base):
    """
    Represents promotional codes that users can activate to receive a balance top-up.
    """
    __tablename__ = "promocodes"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    amount = Column(Float, nullable=False)
    activations_left = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
